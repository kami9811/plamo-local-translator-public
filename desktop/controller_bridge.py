"""Desktop controller bridge. Python stdlib; Linux/WSL and macOS.

The bridge uses argv, never a shell, and will only operate on an API whose
listening socket, module name and working directory belong to this checkout.
Keys are returned only for the explicit `key` action and never written to logs.
"""
from __future__ import annotations

import contextlib
import fcntl
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request


class ControlError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(message)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def local_opener():
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())


def owned_process(root, pid):
    if sys.platform == 'darwin':
        command = mac_command(['/bin/ps', '-p', str(pid), '-o', 'command='])
        if not re.search(r'(?:^|\s)-m\s+plamo_local\.service(?:\s|$)', command):
            return False
        cwd = mac_command(['/usr/sbin/lsof', '-a', '-p', str(pid), '-d', 'cwd', '-Fn'])
        return any(line.startswith('n') and Path(line[1:]).resolve() == root for line in cwd.splitlines())
    try:
        proc = Path('/proc') / str(pid)
        return (b'plamo_local.service' in (proc / 'cmdline').read_bytes().split(b'\0')
                and (proc / 'cwd').resolve() == root)
    except (OSError, RuntimeError):
        return False


def mac_command(args):
    try:
        result = subprocess.run(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, timeout=3)
        return result.stdout.decode('utf-8', errors='replace')
    except (OSError, subprocess.TimeoutExpired):
        return ''


def project(value):
    root = Path(value).expanduser().resolve()
    required = ("scripts/start.py", "scripts/stop.py", "runtime-manifest.json",
                "server/plamo_local/service.py")
    if not root.is_dir() or any(not (root / name).is_file() for name in required):
        raise ControlError("invalid_project", "実行先を確認してください。scripts/start.py があるプロジェクトのフォルダーを指定します。")
    return root


def port_open(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.4):
            return True
    except OSError:
        return False


def listener_inodes(port):
    result = set()
    for name in ("tcp", "tcp6"):
        try:
            lines = Path("/proc/net", name).read_text().splitlines()[1:]
        except OSError:
            continue
        for line in lines:
            fields = line.split()
            if len(fields) > 9 and fields[3] == "0A" and int(fields[1].rsplit(":", 1)[1], 16) == port:
                result.add("socket:[" + fields[9] + "]")
    return result


def owner_pid(root, port):
    if sys.platform == 'darwin':
        output = mac_command(['/usr/sbin/lsof', '-nP', '-iTCP:%d' % port, '-sTCP:LISTEN', '-t'])
        for value in output.split():
            if value.isdigit() and owned_process(root, int(value)):
                return int(value)
        return None
    sockets = listener_inodes(port)
    if not sockets:
        return None
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            args = (proc / "cmdline").read_bytes().split(b"\0")
            if b"plamo_local.service" not in args or (proc / "cwd").resolve() != root:
                continue
            for fd in (proc / "fd").iterdir():
                try:
                    if os.readlink(fd) in sockets:
                        return int(proc.name)
                except OSError:
                    continue
        except (OSError, RuntimeError):
            continue
    return None


def health(port):
    try:
        # Proxies are irrelevant for loopback; never send a key to a proxy.
        opener = local_opener()
        with opener.open("http://127.0.0.1:%d/api/health" % port, timeout=1.5) as response:
            data = json.loads(response.read(65536))
        return data if data.get("ok") and isinstance(data.get("version"), str) else None
    except (OSError, ValueError):
        return None


@contextlib.contextmanager
def operation_lock(port):
    path = Path(tempfile.gettempdir()) / ("plamo-controller-%d-%d.lock" % (os.getuid(), port))
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        if os.fstat(fd).st_uid != os.getuid():
            raise ControlError("lock_error", "操作用のロックを確認できませんでした。")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ControlError("busy", "別の起動・停止操作が進行中です。少し待ってから操作してください。")
        yield
    finally:
        os.close(fd)


def foreign_port():
    raise ControlError("port_in_use", "8765番は別の場所から起動したAPI、または別のアプリが使用しています。実行先を確認し、先に起動した側で停止してください。")


def snapshot(root, port):
    pid = owner_pid(root, port)
    if port_open(port) and pid is None:
        foreign_port()
    data = health(port) if pid is not None else None
    if pid is not None and data is None:
        raise ControlError("not_ready", "選択したAPIはまだ応答していません。少し待って確認してください。")
    if pid is None:
        try:
            recorded = int((root / '.data/api.pid').read_text())
        except (OSError, ValueError):
            recorded = None
        if recorded and owned_process(root, recorded):
            raise ControlError('not_ready', '選択したAPIは起動または停止の処理中です。少し待ってから操作してください。')
    return pid, data


def execute(action, location, port=8765, inference_port=8766, data_dir=None):
    if action not in ("start", "stop", "key", "status"):
        raise ControlError("invalid_action", "操作を確認できませんでした。")
    root = project(location)
    data_dir = Path(data_dir).resolve() if data_dir is not None else root / '.data'
    with operation_lock(port):
        pid, state = snapshot(root, port)
        if action == "start":
            if pid is None:
                env = os.environ.copy()
                env.update(PLAMO_API_PORT=str(port), PLAMO_INFERENCE_PORT=str(inference_port),
                           PLAMO_DATA_DIR=str(data_dir), PYTHONIOENCODING="utf-8",
                           PYTHONPATH=str(root / 'server'))
                data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
                try:
                    with (data_dir / 'api.log').open('ab') as log:
                        process = subprocess.Popen([sys.executable, '-m', 'plamo_local.service'],
                                                   cwd=root, env=env, stdin=subprocess.DEVNULL,
                                                   stdout=log, stderr=log, start_new_session=True)
                    (data_dir / 'api.pid').write_text(str(process.pid))
                    for _ in range(150):
                        state = health(port)
                        if state and owner_pid(root, port) == process.pid:
                            pid = process.pid
                            break
                        if process.poll() is not None:
                            break
                        time.sleep(0.1)
                except OSError:
                    raise ControlError('start_failed', '起動処理を実行できませんでした。Pythonと保存フォルダーを確認してください。')
                if pid is None:
                    raise ControlError("start_failed", "起動に失敗しました。実行先の .data/api.log と、初回セットアップが完了しているかを確認してください。")
                message = "起動しました。Chrome拡張から翻訳できます。"
            else:
                message = "選択した実行先のAPIは、すでに起動しています。"
        elif action == "stop":
            if pid is None:
                return {"ok": True, "state": "stopped", "message": "選択したAPIは停止しています。"}
            # Open the verified process before signalling, avoiding PID-reuse races.
            pidfd = None
            try:
                if hasattr(os, "pidfd_open") and hasattr(signal, "pidfd_send_signal"):
                    pidfd = os.pidfd_open(pid)
                    if not owned_process(root, pid):
                        raise ControlError("state_changed", "実行状態が変わりました。もう一度確認してください。")
                    signal.pidfd_send_signal(pidfd, signal.SIGTERM)
                else:
                    if owner_pid(root, port) != pid:
                        raise ControlError("state_changed", "実行状態が変わりました。もう一度確認してください。")
                    os.kill(pid, signal.SIGTERM)
                for _ in range(300):
                    if not owned_process(root, pid):
                        break
                    time.sleep(0.1)
                else:
                    raise ControlError("stop_timeout", "停止処理が続いています。少し待ってから確認してください。")
            finally:
                if pidfd is not None:
                    os.close(pidfd)
            return {"ok": True, "state": "stopped", "message": "APIとモデルを停止しました。保存した原稿と設定は残っています。"}
        elif action == "key":
            if pid is None:
                raise ControlError("not_running", "先に「起動」を押してください。キー表示だけでAPIが起動することはありません。")
            try:
                key = (data_dir / "token").read_text().strip()
                if not 16 <= len(key) <= 512 or any(c.isspace() for c in key):
                    raise ValueError()
                request = urllib.request.Request("http://127.0.0.1:%d/api/state" % port,
                                                 headers={"Authorization": "Bearer " + key})
                opener = local_opener()
                with opener.open(request, timeout=2) as response:
                    if response.status != 200:
                        raise ValueError()
            except (OSError, ValueError):
                raise ControlError("key_unavailable", "起動中APIの接続キーを確認できません。「停止」してから、同じ実行先で起動し直してください。")
            return {"ok": True, "state": "running", "key": key, "version": state["version"],
                    "message": "接続キーを表示しました。拡張側の「接続と設定」に登録してください。"}
        else:
            return {"ok": True, "state": "running" if pid else "stopped",
                    "version": state["version"] if state else "", "message": "実行状態を確認しました。"}
        return {"ok": True, "state": "running", "version": state["version"], "message": message}


def main():
    try:
        if len(sys.argv) != 3:
            raise ControlError("invalid_arguments", "実行先と操作を指定してください。")
        result = execute(sys.argv[1], sys.argv[2])
    except ControlError as error:
        result = {"ok": False, "state": "unknown", "error": error.code, "message": error.message}
    except Exception:
        # Do not copy exceptions or subprocess output: they may contain a key.
        result = {"ok": False, "state": "unknown", "error": "operation_failed",
                  "message": "操作に失敗しました。実行先とWSL環境を確認してください。"}
    print(json.dumps(result, ensure_ascii=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
