"""Regenerate the original SVG icon's PNG / Windows ICO / macOS ICNS assets.

Requires ImageMagick (`convert`); application builds use the checked-in assets.
No fonts, model output, or third-party logo artwork are used.
"""
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'desktop/assets'


def build():
    images = {}
    for size in [16, 24, 32, 48, 64, 128, 256, 512, 1024]:
        path = ASSETS / ('controller-' + str(size) + '.png')
        subprocess.run(['convert', '-background', 'none', str(ASSETS / 'controller.svg'),
                        '-resize', f'{size}x{size}', '-strip', 'PNG32:' + str(path)], check=True)
        images[size] = path.read_bytes()
    sizes = [16, 24, 32, 48, 64, 128, 256]
    header = struct.pack('<HHH', 0, 1, len(sizes)); offset = 6 + 16 * len(sizes)
    entries = []
    for size in sizes:
        data = images[size]
        entries.append(struct.pack('<BBBBHHII', size % 256, size % 256, 0, 0, 1, 32, len(data), offset))
        offset += len(data)
    (ASSETS / 'controller.ico').write_bytes(header + b''.join(entries) + b''.join(images[s] for s in sizes))
    chunks = []
    for kind, size in [('icp4', 16), ('icp5', 32), ('icp6', 64), ('ic07', 128), ('ic08', 256), ('ic09', 512), ('ic10', 1024)]:
        data = images[size]; chunks.append(kind.encode('ascii') + struct.pack('>I', len(data) + 8) + data)
    body = b''.join(chunks)
    (ASSETS / 'controller.icns').write_bytes(b'icns' + struct.pack('>I', len(body) + 8) + body)


if __name__ == '__main__':
    build()
