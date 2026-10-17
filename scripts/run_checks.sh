#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p test/output
sources=(src/project.v src/uart_rx.v src/control_packet.v src/fire_button.v src/vga_timing.v src/flight_game.v src/pixel_renderer.v)
iverilog -g2012 -s tb_unit -o test/output/unit.vvp "${sources[@]}" test/tb_unit.v
vvp test/output/unit.vvp
iverilog -g2012 -s tb_vga -o test/output/vga.vvp src/vga_timing.v test/tb_vga.v
vvp test/output/vga.vvp
python3 scripts/check_metadata.py
python3 scripts/check_replay.py
iverilog -g2012 -s tb_render -o test/output/render.vvp src/flight_game.v src/pixel_renderer.v test/tb_render.v
vvp test/output/render.vvp
python3 scripts/render_frames.py
