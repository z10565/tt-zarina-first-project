# Hardware and wiring

## Supplied photographs

The four 20261017 photos show Tiny VGA v1.2 with cable/AOC monitor; a white TinyTapeout06+ Demoboard with TT.RUN.09 QFN/analog Breakout TT06+v2.0 (existing ASIC); a purple ETR board with FPGA ASIC simulator; breadboard buttons/jumpers; and an unused audio PMOD. The purple FPGA system is the first test target. Visual identification does not verify revision, firmware, electrical continuity or resistor values. No phone/COM port was attached to this machine at inspection.

## Pin contract

| Signal | Connection |
| --- | --- |
| clk | Requested25.2MHz demoboard project clock; measure/report actual rate |
| rst_n | Active-low project reset from board |
| ui_in[0] | Active-high fire: momentary switch to3.3V, ~10kΩ pulldown toGND |
| ui_in[3] | One3.3V UART TX source,1152008N1,idlehigh |
| ui_in[1,2,4..7] | Unused; relay's unused RX ui4 remains input |
| uo_out[0..7] | R1,G1,B1,VSYNC,R0,G0,B0,HSYNC to Tiny VGA OUTPUT PMOD |
| uio[0..7] | Inputs; uio_oe=0,uio_out=0 |
| GND | Board,button and any UART adapter common ground |

Use the [official Tiny VGA mapping](https://tinytapeout.com/specs/pinouts/). No UART TX goes to uo4: that is VGA R0. GPIO indexes are not physical connector pin numbers. Locate labels and pin1 orientation on the exact hardware before connecting; a rotated PMOD can short power.

## Electrical checks

The [official SKY GPIO specifications](https://tinytapeout.com/specs/gpio/) state standard demo-board I/O is **3.3V, not5V tolerant**. Core voltage is different; digital0/1 does not mean0–1V. Never connect RS-232,5V TTL or bare USB data wires to GPIO. Use the Tiny VGA resistor/buffer adapter for analog RGB; do not connect3.3V GPIO directly to analog VGA RGB. Confirm adapter power/orientation and monitor lock physically.

## Existing ETR USB route

Follow [FPGA.md](FPGA.md). The temporary relay verifies its ETR GPIO map, requests25.2MHz and forwards USB CDC binary bytes to UART1 TX GPIO20/ui3. Unused RX GPIO21/ui4 and physical fire ui0 remain inputs. VGA outputs are untouched by serial routing. Confirm simulator/firmware revision before programming; preserve existing firmware/main.py/projects.

Set input DIP switches OFF and remove any other UART driver before relay setup. Connect the fire switch/pulldown to labeled ui0 and3.3V/GND. Verify releasedlow/pressedhigh with a meter first. Existing button boards can have different active polarity/pulls; do not infer wiring from button color.

## Optional external USB-UART

Use only a confirmed3.3V TTL/CMOS adapter: TX -> ui3, GND -> boardGND, RX disconnected (receive-only design). Disable the onboard management driver's ui3 function so only one source drives that net. Leave adapter VCC disconnected on an already-powered board unless its power plan explicitly requires it.

## Bring-up

1. Identify revision/firmware and back up board config; use matching official FPGA constraints.
2. Poweroff: check VGA orientation, button/pulldown, common ground and absence of competing UART drivers.
3. Power through intended board USB. Load only the game bitstream, preserving firmware and other projects.
4. Configure clock/reset and start temporary relay. Check actual clock close to25.2MHz (not a12/50MHz default), within monitor/UART tolerances.
5. Install updated app, authorize USB debugging, forward8765 withADB, enable USBstream, connect host bridge and start capture heldstill for calibration.
6. Verify cyan link indicator, tiltflight, gyroaim, physicalfire, hits/score, collision/restart and amber/frozen disconnect behavior.

Physical FPGA programming, clock/voltage measurements, S21 FE response and VGA monitor operation remain unverified. A future ASIC uses the same logical interface with its own confirmed carrier/board wiring.
