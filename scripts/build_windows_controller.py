"""Build the small WPF controller using the Windows .NET Framework compiler."""
from pathlib import Path
import argparse
import gzip
import hashlib
import os
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.1.0'


def windows_path(path):
    if os.name == 'nt':
        return str(path.resolve())
    return subprocess.check_output(['wslpath', '-w', str(path.resolve())], text=True).strip()


def build(tests=False):
    if os.name == 'nt':
        framework = Path(os.environ.get('WINDIR', r'C:\Windows')) / 'Microsoft.NET/Framework64/v4.0.30319'
    else:
        framework = Path('/mnt/c/Windows/Microsoft.NET/Framework64/v4.0.30319')
    compiler = framework / 'csc.exe'
    if not compiler.exists():
        raise SystemExit('Windows / WSL上で実行してください。.NET FrameworkのC#コンパイラーが必要です。')
    source = ROOT / 'desktop/windows'
    out = ROOT / 'artifacts/windows-controller'
    out.mkdir(parents=True, exist_ok=True)
    resource = out / 'controller-bridge.py.gz'
    resource.write_bytes(gzip.compress((ROOT / 'desktop/controller_bridge.py').read_bytes(), mtime=0))
    references = [framework / name for name in ['System.dll', 'System.Core.dll', 'System.Web.Extensions.dll']]
    references += [framework / 'WPF' / name for name in ['WindowsBase.dll', 'PresentationCore.dll', 'PresentationFramework.dll', 'System.Xaml.dll', 'UIAutomationTypes.dll']]
    # System.Xaml is beside the framework assemblies on some installations.
    references = [(framework / r.name) if not r.exists() else r for r in references]
    executable = out / ('ControllerTests.exe' if tests else 'PLaMoLocalController.exe')
    args = [str(compiler), '/nologo', '/codepage:65001', '/optimize+', '/debug-', '/platform:anycpu',
            '/target:' + ('exe' if tests else 'winexe'), '/out:' + windows_path(executable),
            '/resource:' + windows_path(resource) + ',controller.bridge.py.gz',
            '/win32manifest:' + windows_path(source / 'app.manifest')]
    args += ['/reference:' + windows_path(r) for r in references]
    args += [windows_path(source / name) for name in ['Core.cs', 'Window.cs', 'Program.cs']]
    if tests:
        args += ['/main:PlamoLocalController.ControllerTests', windows_path(source / 'Tests.cs')]
    subprocess.run(args, check=True)
    executable.chmod(0o755)
    if tests:
        return executable
    package = ROOT / 'artifacts' / ('plamo-local-controller-windows-' + VERSION)
    package.mkdir(exist_ok=True)
    shutil.copyfile(executable, package / executable.name)
    (package / 'PLaMoLocalController.exe.config').write_text('<?xml version="1.0"?><configuration><startup><supportedRuntime version="v4.0" sku=".NETFramework,Version=v4.7.2"/></startup></configuration>\n')
    shutil.copyfile(ROOT / 'desktop/WINDOWS-README.txt', package / 'はじめに.txt')
    license_source = ROOT / 'LICENSE'
    if license_source.exists():
        shutil.copyfile(license_source, package / 'LICENSE')
    if (ROOT / 'NOTICE.md').exists():
        shutil.copyfile(ROOT / 'NOTICE.md', package / 'NOTICE.md')
    licenses = package / 'licenses'
    licenses.mkdir(exist_ok=True)
    for name in ['PLaMo-Community-License-ja.txt', 'PLaMo-Community-License-en.txt']:
        shutil.copyfile(ROOT / 'licenses' / name, licenses / name)
    archive = package.with_suffix('.zip')
    # with_suffix would trim .0 from the version; preserve the entire basename.
    archive = Path(str(package) + '.zip')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for file in sorted(package.rglob('*')):
            if file.is_file():
                z.write(file, file.relative_to(package))
    archive.with_suffix('.zip.sha256').write_text(hashlib.sha256(archive.read_bytes()).hexdigest() + '  ' + archive.name + '\n')
    print(archive)
    return executable


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--tests', action='store_true')
    args = parser.parse_args()
    build(args.tests)
