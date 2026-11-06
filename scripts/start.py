"""Start this checkout's loopback API, without reusing another installation."""
from pathlib import Path
import argparse
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from desktop.controller_bridge import execute, ControlError


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()
    port = int(os.environ.get('PLAMO_API_PORT', '8765'))
    inference = int(os.environ.get('PLAMO_INFERENCE_PORT', '8766'))
    data = os.environ.get('PLAMO_DATA_DIR')
    try:
        execute('start', str(ROOT), port, inference, data)
        print(f'PLaMo Local: http://127.0.0.1:{port}/app.html')
        if not args.quiet:
            key = execute('key', str(ROOT), port, inference, data)['key']
            print('拡張の接続設定に貼り付けるキー（公開しないでください）: ' + key)
    except ControlError as error:
        raise SystemExit(error.message)


if __name__ == '__main__':
    main()
