"""Opt-in ADB device check: enable stream+capture first. Stops app via Home at end."""
import argparse
import subprocess
import sys
import time
from pathlib import Path

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--device', required=True, help='exact authorized ADB serial')
parser.add_argument('--seconds', type=float, default=4)
args = parser.parse_args()
if args.seconds < 2:
    parser.error('at least two seconds needed for calibration')
out = root / 'test/output'
out.mkdir(parents=True, exist_ok=True)
binary = out / 'live-app-controls.bin'
subprocess.run(['adb', '-s', args.device, 'forward', 'tcp:8765', 'tcp:8765'], check=True)
process = subprocess.Popen([sys.executable, str(root/'bridge/flight_bridge.py'),
                            '--tcp', '127.0.0.1:8765', '--output', str(binary)])
try:
    time.sleep(args.seconds)
    subprocess.run(['adb', '-s', args.device, 'shell', 'input', 'keyevent', '3'], check=True)
    process.wait(timeout=5)
finally:
    if process.poll() is None:
        process.terminate()
        process.wait(timeout=5)
assert process.returncode == 0, 'live bridge failed'
sys.path.insert(0, str(root/'bridge'))
from flight_bridge import crc8
raw = binary.read_bytes()
assert raw and len(raw) % 8 == 0
packets = [raw[n:n+8] for n in range(0, len(raw), 8)]
assert all(p[:2] == b'\xa5\x5a' and crc8(p[2:7]) == p[7] for p in packets)
valid = sum(bool(p[6] & 1) for p in packets)
assert valid > 0, 'never calibrated/fresh; check stream and sensors'
assert packets[-1][6] == 0, 'disconnect did not emit invalid controls'
print(f'PASS: actual app -> ADB TCP -> preprocessing -> {len(packets)} CRC packets, '
      f'{valid} valid after calibration, final invalid on background/disconnect')
