"""Stop only this checkout's verified API process; preserve documents/settings."""
from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from desktop.controller_bridge import execute, ControlError


if __name__ == '__main__':
    try:
        result = execute('stop', str(ROOT), int(os.environ.get('PLAMO_API_PORT', '8765')),
                         int(os.environ.get('PLAMO_INFERENCE_PORT', '8766')),
                         os.environ.get('PLAMO_DATA_DIR'))
        print(result['message'])
    except ControlError as error:
        raise SystemExit(error.message)
