"""Recompute the app fixture and replay actual bytes through synthesized RTL sources."""
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'bridge'))
import flight_bridge as bridge

fixture = root / 'bridge/fixtures/controls.hex'
packets = [bytes.fromhex(line) for line in fixture.read_text().splitlines() if line.strip()]
assert packets and all(len(p) == 8 and bridge.crc8(p[2:7]) == p[7] for p in packets)
out = root / 'test/output'
out.mkdir(parents=True, exist_ok=True)
(out / 'replay.mem').write_text('\n'.join(f'{b:02x}' for p in packets for b in p) + '\n')
for divider, count in [(8, len(packets)), (219, 34)]:
    executable = out / f'replay-{divider}.vvp'
    subprocess.run(['iverilog', '-g2012', '-s', 'tb_replay',
                    f'-Ptb_replay.BIT_CYCLES={divider}', f'-Ptb_replay.PACKET_COUNT={count}',
                    '-o', str(executable), 'src/uart_rx.v', 'src/control_packet.v', 'test/tb_replay.v'],
                   cwd=root, check=True)
    # Use a correctly sized memory for the short production-divider regression.
    (out / 'replay.mem').write_text('\n'.join(f'{b:02x}' for p in packets[:count] for b in p) + '\n')
    subprocess.run(['vvp', str(executable)], cwd=root, check=True)
