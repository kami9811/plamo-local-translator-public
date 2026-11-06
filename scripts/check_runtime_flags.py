"""Validate fixed llama.cpp options without loading a model or starting an API."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
binary = next((ROOT / '.runtime/llama').rglob('llama-server'))
env = {k: v for k, v in os.environ.items() if not k.startswith('LLAMA_ARG_')}
for key in ['LLAMA_API_KEY', 'HF_TOKEN', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy']:
    env.pop(key, None)
env['NO_PROXY'] = env['no_proxy'] = '*'
variable = 'DYLD_LIBRARY_PATH' if sys.platform == 'darwin' else 'LD_LIBRARY_PATH'
pattern = '*.dylib' if sys.platform == 'darwin' else '*.so*'
env[variable] = ':'.join(sorted({str(p.parent) for p in (ROOT / '.runtime/llama').rglob(pattern)}))
flags = ['--offline', '--no-agent', '--no-ui-mcp-proxy', '--no-webui']
with tempfile.TemporaryDirectory() as directory:
    key = Path(directory) / 'test.key'; key.write_text('synthetic-runtime-check-only\n'); key.chmod(0o600)
    result = subprocess.run([str(binary), *flags, '--api-key-file', str(key), '--help'], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45)
    if result.returncode != 0:
        raise SystemExit('Official runtime did not accept offline options; no model was loaded.')
report = {'runtime': json.loads((ROOT / 'runtime-manifest.json').read_text())['llama_tag'],
          'accepted_flags': flags + ['--api-key-file'], 'real_models_started': False, 'api_started': False}
out = ROOT / 'artifacts/desktop-validation/runtime-flags-tests.json'; out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, indent=2) + '\n')
print('Official runtime accepts offline options. No API/model was started.')
