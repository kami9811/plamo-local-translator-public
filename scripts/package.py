from pathlib import Path
import hashlib, json, shutil, zipfile
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'artifacts';out.mkdir(exist_ok=True)
manifest=json.loads((ROOT/'dist/manifest.json').read_text());version=manifest['version']
file=out/f'plamo-local-translator-extension-{version}.zip'
with zipfile.ZipFile(file,'w',zipfile.ZIP_DEFLATED) as z:
    for item in sorted((ROOT/'dist').rglob('*')):
        if item.is_file():z.write(item,item.relative_to(ROOT/'dist'))
with zipfile.ZipFile(file) as z:
    assert 'manifest.json' in z.namelist()
    assert all(not any(part in {'.data','.runtime','token','state.sqlite3','.env'} for part in Path(n).parts) for n in z.namelist())
file.with_suffix('.zip.sha256').write_text(hashlib.sha256(file.read_bytes()).hexdigest()+'  '+file.name+'\n')
print(file)
