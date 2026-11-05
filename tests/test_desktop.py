"""Controller integration tests with isolated fixture servers, not model inference."""
from pathlib import Path
import importlib.util
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from desktop import controller_bridge as bridge

FIXTURE = '''
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json,os,secrets,signal,threading
data=Path(os.environ['PLAMO_DATA_DIR']);data.mkdir(exist_ok=True)
key=secrets.token_urlsafe(32);(data/'token').write_text(key)
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_GET(self):
  if self.path=='/api/health': value={'ok':True,'version':'fixture'}
  elif self.headers.get('Authorization')=='Bearer '+key:value={'ok':True}
  else:self.send_error(401);return
  self.send_response(200);self.end_headers();self.wfile.write(json.dumps(value).encode())
server=ThreadingHTTPServer(('127.0.0.1',int(os.environ['PLAMO_API_PORT'])),Handler)
signal.signal(signal.SIGTERM,lambda *_:threading.Thread(target=server.shutdown,daemon=True).start())
server.serve_forever(poll_interval=.05);server.server_close()
'''


def unused_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class ControllerIntegration(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='plamo-controller-test-')
        self.root = Path(self.temp.name) / "論文 draft & notes'"
        for name in ['scripts/start.py', 'scripts/stop.py', 'runtime-manifest.json', 'server/plamo_local/__init__.py']:
            path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('{}')
        (self.root / 'server/plamo_local/service.py').write_text(FIXTURE)
        self.port = unused_port()

    def call(self, action, root=None):
        return bridge.execute(action, str(root or self.root), self.port, unused_port())

    def tearDown(self):
        pid = bridge.owner_pid(self.root.resolve(), self.port)
        if pid:
            self.call('stop')
        self.temp.cleanup()

    def test_lifecycle_and_key_is_explicit(self):
        self.assertEqual(self.call('status')['state'], 'stopped')
        with self.assertRaises(bridge.ControlError) as error:
            self.call('key')
        self.assertEqual(error.exception.code, 'not_running')
        started = self.call('start'); self.assertNotIn('key', started)
        pid = bridge.owner_pid(self.root.resolve(), self.port); self.assertIsNotNone(pid)
        self.assertEqual(self.call('start')['state'], 'running')
        self.assertEqual(bridge.owner_pid(self.root.resolve(), self.port), pid)
        result = self.call('key'); self.assertGreaterEqual(len(result['key']), 32)
        self.assertNotIn(result['key'], (self.root / '.data/api.log').read_text())
        self.assertNotIn('key', self.call('status'))
        self.assertEqual(self.call('stop')['state'], 'stopped')
        self.assertFalse(bridge.port_open(self.port))
        self.assertTrue((self.root / '.data/token').is_file())
        self.assertEqual(self.call('stop')['state'], 'stopped')

    def test_foreign_listener_is_not_reused_or_stopped(self):
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', self.port)); listener.listen()
            (self.root / '.data').mkdir()
            (self.root / '.data/api.pid').write_text(str(os.getpid()))
            for action in ['start', 'stop', 'key']:
                with self.assertRaises(bridge.ControlError) as error: self.call(action)
                self.assertEqual(error.exception.code, 'port_in_use')
            self.assertTrue(bridge.port_open(self.port))

    def test_other_checkout_is_not_touched(self):
        self.call('start')
        other = self.root.parent / 'other'
        for name in ['scripts/start.py', 'scripts/stop.py', 'runtime-manifest.json', 'server/plamo_local/service.py']:
            path = other / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('{}')
        for action in ['start', 'stop', 'key']:
            with self.assertRaises(bridge.ControlError) as error: self.call(action, other)
            self.assertEqual(error.exception.code, 'port_in_use')
        self.assertEqual(self.call('status')['state'], 'running')

    def test_invalid_token_is_never_returned(self):
        self.call('start')
        (self.root / '.data/token').write_text('incorrect-test-key-1234567890')
        with self.assertRaises(bridge.ControlError) as error: self.call('key')
        self.assertEqual(error.exception.code, 'key_unavailable')
        self.assertNotIn('incorrect-test-key', str(error.exception))

    def test_lock_and_invalid_path(self):
        with bridge.operation_lock(self.port):
            with self.assertRaises(bridge.ControlError) as error: self.call('start')
            self.assertEqual(error.exception.code, 'busy')
        with self.assertRaises(bridge.ControlError): self.call('start', self.root.parent)

    def test_platform_mapping(self):
        spec = importlib.util.spec_from_file_location('setup_runtime', ROOT / 'scripts/setup_runtime.py')
        setup = importlib.util.module_from_spec(spec); spec.loader.exec_module(setup)
        self.assertEqual(setup.target('Darwin', 'arm64'), 'darwin-arm64')
        self.assertEqual(setup.target('Darwin', 'x86_64'), 'darwin-x64')
        self.assertEqual(setup.target('Linux', 'x86_64'), 'linux-x64')
        with self.assertRaises(RuntimeError): setup.target('Windows', 'AMD64')


if __name__ == '__main__':
    unittest.main()
