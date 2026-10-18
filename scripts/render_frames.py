"""Convert RTL-produced PPM pixels to PNG with stdlib only; no software game renderer."""
import struct
import zlib
from pathlib import Path


def chunk(kind, body):
    return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body))


out = Path(__file__).resolve().parents[1] / 'test/output'
for ppm in sorted(out.glob('*.ppm')):
    tokens = ppm.read_text().split()
    assert tokens[:4] == ['P3', '160', '120', '255']
    values = bytes(map(int, tokens[4:]))
    assert len(values) == 160 * 120 * 3
    rows = []
    for y in range(120):
        row = b''.join(values[(y*160+x)*3:(y*160+x+1)*3] * 4 for x in range(160))
        rows.extend([b'\x00' + row] * 4)
    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', 640, 480, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(b''.join(rows), 9)) + chunk(b'IEND', b'')
    ppm.with_suffix('.png').write_bytes(png)
    print(f'RTL preview: {ppm.with_suffix(".png").relative_to(out.parent.parent)}')
