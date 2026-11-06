"""Download pinned official runtimes and models for Linux CUDA and macOS Metal."""
from pathlib import Path
import argparse
import concurrent.futures
import hashlib
import json
import os
import platform
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / '.runtime'
MANIFEST = json.loads((ROOT / 'runtime-manifest.json').read_text())


def download(url, target, digest=''):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and (not digest or sha(target) == digest):
        print('READY', target.name, flush=True)
        return target
    part = target.with_suffix(target.suffix + '.part')
    offset = part.stat().st_size if part.exists() else 0
    request = urllib.request.Request(url, headers={'Range': f'bytes={offset}-'} if offset else {})
    with urllib.request.urlopen(request, timeout=120) as response:
        if response.status != 206:
            offset = 0
        with part.open('ab' if offset else 'wb') as output:
            while chunk := response.read(4 * 1024 * 1024):
                output.write(chunk)
    if digest and sha(part) != digest:
        raise RuntimeError(f'Hash mismatch: {target.name}')
    part.replace(target)
    print('DOWNLOADED', target.name, flush=True)
    return target


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        while data := f.read(8 * 1024 * 1024):
            h.update(data)
    return h.hexdigest()


def unpack(archive, directory):
    directory.mkdir(parents=True, exist_ok=True)
    subprocess.run(['tar', '-xf', str(archive), '-C', str(directory)], check=True)


def target(system=None, machine=None):
    system = system or platform.system()
    machine = machine or platform.machine()
    if system == 'Linux' and machine.lower() in ('x86_64', 'amd64'):
        return 'linux-x64'
    if system == 'Darwin' and machine.lower() in ('arm64', 'aarch64'):
        return 'darwin-arm64'
    if system == 'Darwin' and machine.lower() in ('x86_64', 'amd64'):
        return 'darwin-x64'
    raise RuntimeError('対応環境はLinux x86_64 / WSL2と、macOS arm64 / x86_64です。WindowsではWSL側でセットアップしてください。')


def node():
    variant = target()
    version = MANIFEST['node_version']
    extension = 'tar.xz' if variant == 'linux-x64' else 'tar.gz'
    stem = f'node-{version}-{variant}'
    name = f'{stem}.{extension}'
    sums = urllib.request.urlopen(f'https://nodejs.org/dist/{version}/SHASUMS256.txt', timeout=30).read().decode()
    digest = next(line.split()[0] for line in sums.splitlines() if line.endswith('  ' + name))
    archive = download(f'https://nodejs.org/dist/{version}/{name}', RUNTIME / 'downloads' / name, digest)
    unpack(archive, RUNTIME)
    link = RUNTIME / 'node'
    if link.is_symlink() and link.resolve().name != stem:
        link.unlink()
    if not link.exists():
        link.symlink_to(stem, target_is_directory=True)


def llama(asset):
    archive = download(asset['url'], RUNTIME / 'downloads' / asset['name'], asset['sha256'])
    unpack(archive, RUNTIME / 'llama')


def model(item):
    key, value = item
    base = f"https://huggingface.co/{value['repo']}/resolve/{value['revision']}"
    download(f"{base}/{value['file']}", RUNTIME / 'models' / value['file'], value['sha256'])
    download(f'{base}/chat_template.jinja', RUNTIME / 'models' / f'{key}-chat_template.jinja')


def build_from_source():
    source = download(MANIFEST['source']['url'], RUNTIME / 'downloads' / 'llama-source.tar.gz', MANIFEST['source']['sha256'])
    unpack(source, RUNTIME)
    options = ['-DLLAMA_CURL=OFF', '-DLLAMA_BUILD_TESTS=OFF', '-DLLAMA_BUILD_EXAMPLES=OFF',
               '-DLLAMA_BUILD_UI=OFF', '-DLLAMA_USE_PREBUILT_UI=ON', '-DLLAMA_BUILD_SERVER=ON',
               '-DLLAMA_BUILD_COMMIT=' + MANIFEST['llama_commit'], '-DGGML_BUILD_COMMIT=' + MANIFEST['llama_commit'],
               '-DCMAKE_BUILD_TYPE=Release']
    if target().startswith('darwin-'):
        options += ['-DGGML_CUDA=OFF', '-DGGML_METAL=ON', '-DGGML_METAL_EMBED_LIBRARY=ON']
    else:
        compiler = Path(os.environ.get('PLAMO_CUDA_COMPILER', '/usr/local/cuda-12.6/bin/nvcc'))
        if not compiler.exists():
            raise RuntimeError('配布バイナリがOSと非互換です。CUDA 12.6以降の開発ツールとdocs/SETUP.mdを確認してください。')
        options += ['-DGGML_CUDA=ON', '-DCMAKE_CUDA_COMPILER=' + str(compiler),
                    '-DCMAKE_CUDA_ARCHITECTURES=' + os.environ.get('PLAMO_CUDA_ARCH', '89')]
    subprocess.run(['cmake', '-S', str(RUNTIME / ('llama.cpp-' + MANIFEST['llama_tag'])),
                    '-B', str(RUNTIME / 'llama-build'), *options], check=True)
    subprocess.run(['cmake', '--build', str(RUNTIME / 'llama-build'), '--target', 'llama-server',
                    '-j', str(min(os.cpu_count() or 4, 12))], check=True)


def main():
    parser = argparse.ArgumentParser(description='Set up local runtimes and official models.')
    parser.add_argument('--accept-model-license', action='store_true', help='Confirm the PLaMo model agreement in licenses/.')
    parser.add_argument('--runtime-only', action='store_true', help='Install runtimes without models.')
    parser.add_argument('--models', choices=['all', '2b', '8b'], default='all', help='Models to download (default: all).')
    args = parser.parse_args()
    if not args.runtime_only and not args.accept_model_license:
        parser.error('モデルの利用条件を licenses/PLaMo-Community-License-ja.txt で確認し、同意する場合は --accept-model-license を指定してください。商用利用の登録・条件は別途必要です。')
    variant = target()
    assets = MANIFEST['assets'] if variant == 'linux-x64' else [MANIFEST['macos_assets'][variant]]
    models = [(key, value) for key, value in MANIFEST['models'].items() if args.models == 'all' or key == args.models]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        tasks = [pool.submit(node)] + [pool.submit(llama, asset) for asset in assets]
        if not args.runtime_only:
            tasks += [pool.submit(model, item) for item in models]
        for task in concurrent.futures.as_completed(tasks):
            task.result()
    binary = next((RUNTIME / 'llama').rglob('llama-server'))
    try:
        compatible = subprocess.run([str(binary), '--version'], capture_output=True).returncode == 0
    except OSError:
        compatible = False
    if not compatible:
        build_from_source()
    print('Setup complete (' + variant + ')', flush=True)


if __name__ == '__main__':
    main()
