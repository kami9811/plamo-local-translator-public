from pathlib import Path
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'server'))
from plamo_local.engine import Engine

spec = importlib.util.spec_from_file_location('setup_runtime_under_test', ROOT / 'scripts/setup_runtime.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class Response:
    def __init__(self, data, status=200):
        self.data, self.status = data, status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self, size):
        result, self.data = self.data[:size], self.data[size:]
        return result


class ModelDownloads(unittest.TestCase):
    def test_current_model_and_template_use_the_same_immutable_revision(self):
        for key, value in setup.MANIFEST['models'].items():
            with self.subTest(model=key), patch.object(setup, 'download') as download:
                setup.model((key, value))
                calls = download.call_args_list
                self.assertEqual(len(calls), 2)
                prefix = f"https://huggingface.co/{value['repo']}/resolve/{value['revision']}/"
                self.assertEqual(calls[0].args[0], prefix + value['file'])
                self.assertEqual(calls[0].args[2], value['sha256'])
                self.assertEqual(calls[1].args[0], prefix + 'chat_template.jinja')
                self.assertEqual(calls[1].args[2], value['template_sha256'])
                self.assertRegex(value['revision'], r'^[a-f0-9]{40}$')
                self.assertRegex(value['template_sha256'], r'^[a-f0-9]{64}$')

    def test_old_partial_file_is_not_appended_to_a_new_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'model.gguf'
            target.with_suffix('.gguf.part').write_bytes(b'old revision partial')
            data = b'new official model'
            digest = hashlib.sha256(data).hexdigest()
            with patch.object(setup.urllib.request, 'urlopen', return_value=Response(data)) as opening:
                setup.download('https://example.invalid/model.gguf', target, digest)
            self.assertIsNone(opening.call_args.args[0].get_header('Range'))
            self.assertEqual(target.read_bytes(), data)
            self.assertEqual(target.with_suffix('.gguf.part').read_bytes(), b'old revision partial')

    def test_failed_digest_does_not_replace_installed_model(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'model.gguf'
            target.write_bytes(b'installed model')
            with patch.object(setup.urllib.request, 'urlopen', return_value=Response(b'wrong download')):
                with self.assertRaisesRegex(RuntimeError, 'Hash mismatch'):
                    setup.download('https://example.invalid/model.gguf', target, '0' * 64)
            self.assertEqual(target.read_bytes(), b'installed model')

    def test_existing_template_is_updated_when_its_hash_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / '2b-chat_template.jinja'
            target.write_bytes(b'old template')
            new = b'official current template'
            with patch.object(setup.urllib.request, 'urlopen', return_value=Response(new)):
                setup.download('https://example.invalid/chat_template.jinja', target, hashlib.sha256(new).hexdigest())
            self.assertEqual(target.read_bytes(), new)

    def test_legacy_model_keeps_its_revision_and_cache_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            current = {'repo': 'pfnet/example', 'revision': 'new', 'file': 'model.gguf', 'bytes': 8, 'sha256': 'new-sha'}
            legacy = {**current, 'revision': 'old', 'bytes': 4, 'sha256': 'old-sha'}
            current['compatible_artifacts'] = [legacy]
            (root / 'runtime-manifest.json').write_text(json.dumps({'llama_tag': 'test', 'models': {'2b': current}}))
            engine = Engine(root, root)
            path = root / '.runtime/models/model.gguf'
            path.parent.mkdir(parents=True)
            self.assertFalse(engine.status()['models'][0]['available'])
            path.write_bytes(b'old!')
            old_provenance = engine.provenance('2b')
            self.assertTrue(engine.status()['models'][0]['available'])
            self.assertEqual(old_provenance['revision'], 'old')
            self.assertEqual(old_provenance['sha256'], 'old-sha')
            self.assertNotIn('compatible_artifacts', old_provenance)
            path.write_bytes(b'new data')
            self.assertEqual(engine.provenance('2b')['revision'], 'new')
            self.assertNotEqual(engine.provenance('2b'), old_provenance)
            path.write_bytes(b'incomplete')
            self.assertFalse(engine.status()['models'][0]['available'])


if __name__ == '__main__':
    unittest.main()
