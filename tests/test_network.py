"""Network-boundary checks using isolated loopback fixtures, never user models."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import io
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'server'))
from plamo_local.engine import Engine
from plamo_local import service


@contextmanager
def listener(handler):
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=3)


class QuietHandler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass


class NetworkBoundaries(unittest.TestCase):
    def test_inference_ignores_ambient_proxy(self):
        proxy_hits = []; direct_hits = []
        class Proxy(QuietHandler):
            def do_POST(self):
                proxy_hits.append(self.path); self.rfile.read(int(self.headers.get('Content-Length', '0')))
                self.send_response(200); self.end_headers(); self.wfile.write(b'{"proxy":true}')
        class Direct(QuietHandler):
            def do_POST(self):
                direct_hits.append(self.path); self.rfile.read(int(self.headers.get('Content-Length', '0')))
                self.send_response(200); self.end_headers(); self.wfile.write(b'{"local":true}')
        with listener(Proxy) as proxy, listener(Direct) as direct, tempfile.TemporaryDirectory() as data:
            address = f'http://127.0.0.1:{proxy.server_port}'
            env = {'http_proxy': address, 'HTTP_PROXY': address, 'NO_PROXY': '', 'no_proxy': ''}
            with patch.dict(os.environ, env):
                # Prove that the trap is effective for the previous default transport.
                request = urllib.request.Request(f'http://127.0.0.1:{direct.server_port}/completion', data=b'fixture')
                with urllib.request.build_opener().open(request, timeout=3) as response:
                    self.assertTrue(json.load(response)['proxy'])
                self.assertEqual(len(proxy_hits), 1); proxy_hits.clear()
                engine = Engine(ROOT, Path(data)); engine.port = direct.server_port
                with engine._request('/completion', {'prompt': 'synthetic test only'}, timeout=3) as response:
                    self.assertTrue(json.load(response)['local'])
            self.assertEqual(proxy_hits, [])
            self.assertEqual(direct_hits, ['/completion'])

    def test_inference_refuses_redirect_and_arbitrary_destination(self):
        reached = []
        class Sink(QuietHandler):
            def do_GET(self):
                reached.append(True); self.send_response(200); self.end_headers()
        with listener(Sink) as sink:
            class Redirect(QuietHandler):
                def do_GET(self):
                    self.send_response(302)
                    self.send_header('Location', f'http://127.0.0.1:{sink.server_port}/leak')
                    self.end_headers()
            with listener(Redirect) as origin, tempfile.TemporaryDirectory() as data:
                engine = Engine(ROOT, Path(data)); engine.port = origin.server_port
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    engine._request('/health', timeout=3)
                self.assertEqual(caught.exception.code, 302); caught.exception.close()
                with self.assertRaises(ValueError): engine._request('https://example.invalid/steal')
        self.assertEqual(reached, [])

    def test_runtime_starts_offline_without_inherited_agent_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / 'runtime-manifest.json').write_bytes((ROOT / 'runtime-manifest.json').read_bytes())
            data = root / '.data'; data.mkdir()
            runtime = root / '.runtime'; (runtime / 'llama').mkdir(parents=True); (runtime / 'llama/llama-server').touch()
            weights = runtime / 'models' / json.loads((root / 'runtime-manifest.json').read_text())['models']['2b']['file']
            weights.parent.mkdir(parents=True); weights.write_bytes(b'fixture, not model weights')
            fixture_manifest=json.loads((root / 'runtime-manifest.json').read_text())
            fixture_manifest['models']['2b']['bytes']=weights.stat().st_size
            (root / 'runtime-manifest.json').write_text(json.dumps(fixture_manifest))
            process = MagicMock(); process.poll.return_value = None
            response = MagicMock(); response.__enter__.return_value.status = 200
            dangerous = {'LLAMA_ARG_AGENT': '1', 'LLAMA_ARG_MCP_SERVERS_JSON': '{}', 'LLAMA_ARG_MODEL_URL': 'https://example.invalid/model', 'HF_TOKEN': 'fixture-not-a-token', 'HTTP_PROXY': 'http://127.0.0.1:1'}
            with patch.dict(os.environ, dangerous), patch('plamo_local.engine.subprocess.Popen', return_value=process) as spawn:
                engine = Engine(root, data)
                with patch.object(engine, '_request', return_value=response): engine.load('2b')
                args, = spawn.call_args.args; env = spawn.call_args.kwargs['env']
                for flag in ['--offline', '--no-agent', '--no-ui-mcp-proxy', '--no-webui']: self.assertIn(flag, args)
                self.assertEqual(args[args.index('--host') + 1], '127.0.0.1')
                self.assertFalse(any(key.startswith('LLAMA_ARG_') for key in env))
                self.assertNotIn('HF_TOKEN', env); self.assertNotIn('HTTP_PROXY', env)
                self.assertEqual(env['NO_PROXY'], '*')
                self.assertNotIn(engine.api_key, args)
                keyfile=Path(args[args.index('--api-key-file')+1])
                self.assertEqual(keyfile.read_text().strip(),engine.api_key)
                self.assertEqual(keyfile.stat().st_mode & 0o777,0o600)

    def test_api_rejects_foreign_hosts_origins_and_missing_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            app = service.App(ROOT, Path(directory))
            with listener(service.Handler) as server:
                server.app = app
                host = f'127.0.0.1:{server.server_port}'; origin = f'http://{host}'
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                def request(path, headers=None):
                    return opener.open(urllib.request.Request(origin + path, headers=headers or {}), timeout=3)
                with patch.object(service, 'LOCAL_HOSTS', {host}), patch.object(service, 'LOCAL_ORIGINS', {origin}):
                    for headers, status in [({}, 401), ({'Host': 'evil.invalid'}, 403), ({'Origin': 'https://evil.invalid', 'Authorization': 'Bearer ' + app.token}, 403)]:
                        with self.assertRaises(urllib.error.HTTPError) as caught: request('/api/state', headers)
                        self.assertEqual(caught.exception.code, status); caught.exception.close()
                    with self.assertRaises(urllib.error.HTTPError) as caught:
                        request('/api/bootstrap', {'Origin': 'chrome-extension://' + 'a' * 32, 'Sec-Fetch-Site': 'cross-site'})
                    self.assertEqual(caught.exception.code, 403); caught.exception.close()
                    with request('/api/state', {'Authorization': 'Bearer ' + app.token}) as response:
                        self.assertIn('engine', json.load(response))
                    with self.assertRaises(urllib.error.HTTPError) as caught:
                        request('/api/bootstrap', {'Origin': origin, 'Sec-Fetch-Site': 'same-origin'})
                    self.assertEqual(caught.exception.code, 403); caught.exception.close()
            app.shutdown()


if __name__ == '__main__': unittest.main()
