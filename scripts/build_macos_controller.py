"""Build a universal macOS AppKit controller. Run on macOS with Xcode tools."""
from pathlib import Path
import argparse
import hashlib
import platform
import plistlib
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.1.1'


def build(tests=False):
    if platform.system() != 'Darwin':
        raise SystemExit('macOSとXcode Command Line Toolsが必要です。')
    out = ROOT / 'artifacts/macos-controller'
    out.mkdir(parents=True, exist_ok=True)
    sources = ROOT / 'desktop/macos'
    common = ['xcrun', 'swiftc', '-swift-version', '5', '-O', '-framework', 'AppKit']
    if tests:
        result = out / 'ControllerTests'
        subprocess.run([*common, *[str(sources / name) for name in ['Core.swift', 'App.swift', 'Tests.swift']], '-o', str(result)], check=True)
        return result
    app = out / 'PLaMo Local Controller.app'
    if app.exists():
        shutil.rmtree(app)
    contents = app / 'Contents'
    resources = contents / 'Resources'
    binary = contents / 'MacOS/PLaMoLocalController'
    resources.mkdir(parents=True)
    binary.parent.mkdir()
    for arch in ['arm64', 'x86_64']:
        subprocess.run([*common, '-target', arch + '-apple-macos12.0',
                        *[str(sources / name) for name in ['Core.swift', 'App.swift', 'Main.swift']],
                        '-o', str(out / arch)], check=True)
    subprocess.run(['lipo', '-create', str(out / 'arm64'), str(out / 'x86_64'), '-output', str(binary)], check=True)
    info = dict(CFBundleName='PLaMo Local Controller', CFBundleDisplayName='PLaMo Local コントローラー',
                CFBundleIdentifier='io.github.kami9811.plamo-local-controller', CFBundleExecutable=binary.name,
                CFBundleVersion='2', CFBundleIconFile='Controller.icns', CFBundleShortVersionString=VERSION, CFBundlePackageType='APPL',
                LSMinimumSystemVersion='12.0', NSHighResolutionCapable=True,
                NSHumanReadableCopyright='MIT · Built with PLaMo · 非公式ツール')
    (contents / 'Info.plist').write_bytes(plistlib.dumps(info))
    shutil.copyfile(ROOT / 'desktop/controller_bridge.py', resources / 'controller_bridge.py')
    shutil.copyfile(ROOT / 'desktop/assets/controller.icns', resources / 'Controller.icns')
    shutil.copyfile(ROOT / 'desktop/assets/controller-128.png', resources / 'controller-128.png')
    shutil.copyfile(ROOT / 'desktop/MACOS-README.txt', resources / 'はじめに.txt')
    for name in ['LICENSE', 'NOTICE.md']:
        if (ROOT / name).is_file():
            shutil.copyfile(ROOT / name, resources / name)
    shutil.copytree(ROOT / 'licenses', resources / 'licenses')
    subprocess.run(['codesign', '--force', '--deep', '--sign', '-', str(app)], check=True)
    subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True)
    archive = ROOT / 'artifacts' / ('plamo-local-controller-macos-' + VERSION + '.zip')
    archive.unlink(missing_ok=True)
    subprocess.run(['ditto', '-c', '-k', '--keepParent', str(app), str(archive)], check=True)
    archive.with_suffix('.zip.sha256').write_text(hashlib.sha256(archive.read_bytes()).hexdigest() + '  ' + archive.name + '\n')
    print(archive)
    return app


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--tests', action='store_true')
    arguments = parser.parse_args()
    print(build(arguments.tests))
