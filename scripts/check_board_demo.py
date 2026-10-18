"""Replay the exact board-generated diagnostic packets through production UART RTL."""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "fpga"))
from board_demo import packet

out = root / "test/output"
packets = [packet(i) for i in range(300)]  # includes restart cycles and sequence wrap
(out / "replay.mem").write_text("\n".join(f"{b:02x}" for p in packets for b in p) + "\n")
exe = out / "board-demo.vvp"
subprocess.run(["iverilog", "-g2012", "-s", "tb_replay", "-Ptb_replay.BIT_CYCLES=219",
                "-Ptb_replay.PACKET_COUNT=300", "-o", str(exe), "src/uart_rx.v",
                "src/control_packet.v", "test/tb_replay.v"], cwd=root, check=True)
subprocess.run(["vvp", str(exe)], cwd=root, check=True)
print("PASS: 300 board demo packets at production baud, restarts, all aims and sequence wrap")
