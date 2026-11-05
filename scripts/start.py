import os
"""Start the loopback API. Run --quiet for automation, otherwise show pairing key locally."""
from pathlib import Path
import argparse, json, os, subprocess, sys, time, urllib.request
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'.data'
parser=argparse.ArgumentParser();parser.add_argument('--quiet',action='store_true');args=parser.parse_args()
DATA.mkdir(exist_ok=True,mode=0o700)
def healthy():
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get("PLAMO_API_PORT","8765")}/api/health',timeout=1) as r:return json.load(r).get('version')=='0.1.2'
    except Exception:return False
if not healthy():
    env=os.environ.copy();env['PYTHONPATH']=str(ROOT/'server')
    with (DATA/'api.log').open('ab') as log:
        process=subprocess.Popen([sys.executable,'-m','plamo_local.service'],cwd=ROOT,env=env,stdout=log,stderr=log,start_new_session=True)
    (DATA/'api.pid').write_text(str(process.pid))
    for _ in range(50):
        if healthy():break
        if process.poll() is not None:raise SystemExit('起動に失敗しました。.data/api.logを確認してください。')
        time.sleep(.1)
    else:raise SystemExit('APIの起動待ちがタイムアウトしました。')
print(f'PLaMo Local: http://127.0.0.1:{os.environ.get("PLAMO_API_PORT","8765")}/app.html')
if not args.quiet:print('拡張の接続設定に貼り付けるキー（公開しないでください）: '+(DATA/'token').read_text())
