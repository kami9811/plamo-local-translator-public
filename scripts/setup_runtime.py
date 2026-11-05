"""Download pinned official runtimes and models, with resumable transfers and hashes."""
from pathlib import Path
import argparse
import concurrent.futures, hashlib, json, os, subprocess, sys, tarfile, urllib.request
ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / '.runtime'
MANIFEST = json.loads((ROOT / 'runtime-manifest.json').read_text())
def download(url, target, digest=''):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and (not digest or sha(target) == digest):
        print('READY', target.name, flush=True); return target
    part = target.with_suffix(target.suffix + '.part')
    offset = part.stat().st_size if part.exists() else 0
    request = urllib.request.Request(url, headers={'Range': f'bytes={offset}-'} if offset else {})
    with urllib.request.urlopen(request, timeout=120) as response:
        if response.status != 206: offset = 0
        with part.open('ab' if offset else 'wb') as output:
            while chunk := response.read(4 * 1024 * 1024): output.write(chunk)
    if digest and sha(part) != digest: raise RuntimeError(f'Hash mismatch: {target.name}')
    part.replace(target); print('DOWNLOADED', target.name, flush=True); return target
def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        while data := f.read(8 * 1024 * 1024): h.update(data)
    return h.hexdigest()
def unpack(archive, directory):
    directory.mkdir(parents=True, exist_ok=True)
    subprocess.run(['tar', '-xf', str(archive), '-C', str(directory)], check=True)
def node():
    version = MANIFEST['node_version']; name = f'node-{version}-linux-x64.tar.xz'
    sums = urllib.request.urlopen(f'https://nodejs.org/dist/{version}/SHASUMS256.txt').read().decode()
    digest = next(line.split()[0] for line in sums.splitlines() if line.endswith('  '+name))
    archive = download(f'https://nodejs.org/dist/{version}/{name}', RUNTIME / 'downloads' / name, digest)
    unpack(archive, RUNTIME)
    link = RUNTIME / 'node'
    if not link.exists(): link.symlink_to(f'node-{version}-linux-x64', target_is_directory=True)
def llama(asset):
    archive = download(asset['url'], RUNTIME / 'downloads' / asset['name'], asset['sha256'])
    unpack(archive, RUNTIME / 'llama')
def model(item):
    key, m = item
    download(f"https://huggingface.co/{m['repo']}/resolve/{m['revision']}/{m['file']}", RUNTIME / 'models' / m['file'], m['sha256'])
    download(f"https://huggingface.co/{m['repo']}/resolve/{m['revision']}/chat_template.jinja", RUNTIME / 'models' / f'{key}-chat_template.jinja')
if __name__ == '__main__':
    parser=argparse.ArgumentParser(description='Set up local runtimes and official models.')
    parser.add_argument('--accept-model-license',action='store_true',help='Confirm agreement to licenses/PLaMo-Community-License-ja.txt and -en.txt')
    parser.add_argument('--runtime-only',action='store_true',help='Install runtimes without downloading models')
    args=parser.parse_args()
    if not args.runtime_only and not args.accept_model_license:
        parser.error('モデルの利用条件を licenses/PLaMo-Community-License-ja.txt で確認し、同意する場合は --accept-model-license を指定してください。商用利用の登録・条件は別途必要です。')
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        tasks = [pool.submit(node)] + [pool.submit(llama, a) for a in MANIFEST['assets']] + ([] if args.runtime_only else [pool.submit(model, item) for item in MANIFEST['models'].items()])
        for task in concurrent.futures.as_completed(tasks): task.result()
    binary = next((RUNTIME / 'llama').rglob('llama-server'))
    check = subprocess.run([str(binary), '--version'], capture_output=True)
    if check.returncode:
        source = download(MANIFEST['source']['url'], RUNTIME / 'downloads' / 'llama-source.tar.gz', MANIFEST['source']['sha256'])
        unpack(source, RUNTIME)
        compiler = Path(os.environ.get('PLAMO_CUDA_COMPILER','/usr/local/cuda-12.6/bin/nvcc'))
        if not compiler.exists():
            raise SystemExit('配布バイナリがOSと非互換です。CUDA 12.6以降の開発ツールを用意し、docs/SETUP.mdのビルド手順をご確認ください。')
        subprocess.run(['cmake','-S',str(RUNTIME / ('llama.cpp-'+MANIFEST['llama_tag'])),'-B',str(RUNTIME/'llama-build'),'-DGGML_CUDA=ON','-DCMAKE_CUDA_COMPILER='+str(compiler),'-DCMAKE_CUDA_ARCHITECTURES='+os.environ.get('PLAMO_CUDA_ARCH','89'),'-DLLAMA_CURL=OFF','-DLLAMA_BUILD_TESTS=OFF','-DLLAMA_BUILD_EXAMPLES=OFF','-DLLAMA_BUILD_UI=OFF','-DLLAMA_USE_PREBUILT_UI=ON','-DLLAMA_BUILD_SERVER=ON','-DLLAMA_BUILD_COMMIT='+MANIFEST['llama_commit'],'-DGGML_BUILD_COMMIT='+MANIFEST['llama_commit'],'-DCMAKE_BUILD_TYPE=Release'],check=True)
        subprocess.run(['cmake','--build',str(RUNTIME/'llama-build'),'--target','llama-server','-j','12'],check=True)
    print('Setup complete', flush=True)
