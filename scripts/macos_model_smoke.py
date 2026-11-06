"""Real-model smoke check, exclusively for an isolated GitHub-hosted macOS runner."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import platform
import re
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from desktop.controller_bridge import execute, local_opener, port_open


def main(models, output):
    if platform.system() != 'Darwin' or os.environ.get('GITHUB_ACTIONS') != 'true':
        raise SystemExit('この実モデル検証は、隔離されたmacOS CI専用です。')
    results = []
    manifest=json.loads((ROOT/'runtime-manifest.json').read_text())
    downloaded=[]
    for model in models:
        item=manifest['models'][model]
        for name,digest in [(item['file'],item['sha256']),(f'{model}-chat_template.jinja',item['template_sha256'])]:
            path=ROOT/'.runtime/models'/name
            check=hashlib.sha256()
            with path.open('rb') as source_file:
                while chunk:=source_file.read(8*1024*1024):check.update(chunk)
            assert check.hexdigest()==digest, 'download digest mismatch: '+name
            downloaded.append({'model':model,'file':name,'revision':item['revision'],'bytes':path.stat().st_size,'sha256':digest,'verified':True})
    try:
        execute('start', str(ROOT))
        token = execute('key', str(ROOT))['key']
        opener = local_opener()
        def request(path, body=None):
            data = None if body is None else json.dumps(body).encode()
            headers = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}
            with opener.open(urllib.request.Request('http://127.0.0.1:8765' + path, data=data, headers=headers), timeout=30) as response:
                return json.load(response)
        for model in models:
            source = 'This study evaluates the accuracy of the proposed method.'
            started = time.perf_counter()
            task = request('/api/translations', {'text': source, 'options': {'model': model, 'source_lang': 'en', 'target_lang': 'ja'}})
            task_id = task['id']
            deadline = time.monotonic() + 420
            while time.monotonic() < deadline:
                result = request('/api/translations/' + task_id)
                if result['status'] in ['done', 'error', 'cancelled']: break
                time.sleep(.5)
            assert result['status'] == 'done', 'real translation failed: ' + result.get('error', result['status'])
            assert re.search('[ぁ-んァ-ン一-龯]', result['translation']), 'Japanese translation was not produced'
            state = request('/api/state')
            assert state['engine']['model'] == model, 'selected model differs from loaded model'
            results.append({'model': model, 'source': source, 'translation': result['translation'], 'seconds': round(time.perf_counter() - started, 3),
                            'engine': state['engine'], 'metrics': result.get('metrics', {}), 'provenance':result.get('model', {})})
    finally:
        execute('stop', str(ROOT))
    assert not port_open(8765) and not port_open(8766), 'API or inference server was left running'
    report = {'platform': platform.platform(), 'machine': platform.machine(), 'mode': 'CPU (PLAMO_GPU_LAYERS=0)',
              'downloads':downloaded,'real_models': True, 'model_switch_verified': len(models) > 1, 'api_and_model_stopped': True, 'results': results}
    output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'models': models, 'real_translation_verified': True, 'stopped': True}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--models', nargs='+', choices=['2b', '8b'], required=True)
    parser.add_argument('--output', type=Path, required=True); args = parser.parse_args(); main(args.models, args.output)
