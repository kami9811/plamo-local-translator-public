from pathlib import Path
import os,signal,time
root=Path(__file__).resolve().parents[1];pidfile=root/'.data/api.pid'
if pidfile.exists():
    pid=int(pidfile.read_text());cmd=Path(f'/proc/{pid}/cmdline')
    if cmd.exists() and b'plamo_local.service' in cmd.read_bytes():
        os.kill(pid,signal.SIGTERM)
        for _ in range(200):
            if not cmd.exists() or b'plamo_local.service' not in cmd.read_bytes():break
            time.sleep(.1)
        else:raise SystemExit('停止を待っています。処理状態を確認してください。')
        print('ローカルAPIとモデルを停止しました。')
    else:print('APIは停止済みです。')
else:print('APIは起動していません。')
