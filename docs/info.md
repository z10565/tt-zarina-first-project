<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works

Phone Flight is a compact 2D game using procedural graphics, one enemy and one projectile. Phone tilt controls flight, gyro Z aims a five-direction cannon, and a separate physical button fires. Hits increase a two-digit score up to 99. Player collision produces game over; release and press fire to restart.

One 25.2 MHz clock drives 640x480 VGA (800x525 raster, negative sync, 60 Hz). Gameplay updates only at vertical blank; logical 160x120 graphics are enlarged four times. No framebuffer or machine learning is used.

The Android app's raw JSONL reaches a PC over USB ADB localhost forwarding. The PC calibrates, filters and quantizes it into CRC-protected UART packets. The RTL receives 115200 8N1 on ui3 and a synchronized/debounced active-high physical fire input on ui0. Missing valid controls for 15 frames freezes movement/projectiles/enemies and inhibits firing. See docs/INTERFACE.md and bridge/README.md for exact protocol and mapping.

All eight dedicated outputs follow Tiny VGA: R1,G1,B1,VSYNC,R0,G0,B0,HSYNC. No UART TX shares those outputs. All uio outputs are disabled. The repository deliberately migrates from Wokwi to the matching official SKY Verilog template, retaining sky130A/ttsky26d checks and original attribution. Standard footprint 1x2 uses two of the group's three-tile budget; 3x2 would use six tiles. Event/shuttle confirmation remains required before submission.

## How to test

Run `bash scripts/run_checks.sh` for UART/parser, debounce, gameplay, exhaustive VGA and captured-app replay checks plus five Verilog-generated preview frames. Run `cd test && make && python -m cocotb_tools.check_results results.xml` for top-level cocotb tests; the official action also runs gate-level tests. Run `python -m unittest discover -s bridge/tests -v` for preprocessing/transport tests.

Use the ETR FPGA ASIC simulator first, following docs/FPGA.md. The existing TT.RUN.09 ASIC cannot be reprogrammed. Install RTU Motion v0.2, enable USB stream, forward port8765 with ADB, start the PC bridge, and hold the phone approximately face-up/stationary during initial calibration. Verify flight, aiming, physical firing, score/collision/restart and freeze on disconnect. Start a new capture to recalibrate. Actual results/limits are in docs/VERIFICATION.md; green GDS alone is not gameplay evidence or manufacturing submission.

The checked-in capture is 1,233 actual Android-emulator records, with371 expected UART packets, explicitly not physical S21 FE data. Preview pixels are produced by the game/renderer RTL, not an app software simulation.

## External hardware

Photographed equipment: purple Tiny Tapeout ETR demoboard and FPGA ASIC simulator, Tiny VGA v1.2 adapter/cable, AOC VGA monitor, physical buttons, Galaxy S21 FE and USB host PC. Exact board/firmware revision and wiring must be verified. Audio PMOD and the existing white-board TT.RUN.09 ASIC are unused.

Tiny VGA connects to OUTPUT PMOD. Standard board I/O is3.3V and not5V tolerant; digital1 does not mean1V. Use common ground and the correct VGA resistor adapter. The guarded ETR management-controller relay forwards USB CDC to hardware UART1 TX GPIO20/ui3; unused RX GPIO21/ui4 remains an input, never a VGA output. Alternatively use a confirmed3.3V TTL USB-UART TX with no competing driver. Physical fire is ui0, switch to3.3V with external pulldown. Never connect RS-232,5V UART or bare USB wires to GPIO. See docs/WIRING.md for setup and safety details; no physical hardware test has yet run.
