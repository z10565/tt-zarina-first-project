# Test first on the ETR FPGA simulator

Photos identify two different systems: the white TinyTapeout06+ demoboard carries an existing TT.RUN.09 ASIC, which cannot receive our new logic; the purple ETR demoboard with FPGA ASIC simulator is the FPGA target. Tiny VGA v1.2 and the AOC VGA monitor provide the display. Audio PMOD is unused. Confirm the FPGA daughterboard revision and firmware before programming: these are visual identifications, not electrical validation.

The [official simulator guide](https://tinytapeout.com/guides/fpga-breakout/) distinguishes classic and ETR FabricFox constraints. Our official ICE40 workflow pins [support tools 01d5d2814fa9dd61e9d211e0b235a4a592a9316a](https://github.com/TinyTapeout/tt-support-tools/tree/01d5d2814fa9dd61e9d211e0b235a4a592a9316a), whose default fabricfox target uses `tt_fpga_fabricfoxv2.pcf`. Do not load this artifact on an unidentified or classic simulator.

## Build and artifact

Every push now runs the official FPGA action. Download `fpga_bitstream` from the final tested SHA. Programming file: `build/tt_um_zarina_phone_flight.bin`. Inspect included Yosys/nextpnr logs for utilization and timing. `TT_FPGA_FREQ=25.2` checks the intended frequency instead of the tool's default 12 MHz. Generation alone does not verify hardware.

Equivalent local commands, with OSS CAD Suite activated:

```sh
git clone https://github.com/TinyTapeout/tt-support-tools.git tt
git -C tt checkout 01d5d2814fa9dd61e9d211e0b235a4a592a9316a
python -m pip install -r tt/requirements.txt
python tt/tt_tool.py --create-user-config
TT_FPGA_FREQ=25.2 python tt/tt_fpga.py harden --breakout-target fabricfox
```

The official wrapper uses the external project clock directly, with no PLL or oscillator. Request 25.2 MHz on the ETR; SDK PWM can approximate it. The relay prints the reported actual rate and refuses errors above 0.5%. Measure it where possible and check monitor lock/UART reliability. Do not retain a 12 or 50 MHz default.

## Load and preserve the board

Use the [ETR quickstart](https://tinytapeout.com/guides/get-started-demoboard-etr/). Close Commander before another program opens the USB serial port. Back up board files before any firmware upgrade, which erases them. This project does not replace firmware or main.py automatically.

Download the artifact's build directory into the repository. From native Windows PowerShell, replacing COM7 with the ETR management port:

```powershell
python -m pip install -r tt/requirements.txt
python tt/tt_fpga.py configure --port COM7 --upload --name tt_um_zarina_phone_flight
python -m pip install mpremote
mpremote connect COM7 fs ls
mpremote connect COM7 fs cp :config.ini fpga/board-config.backup.ini
```

The uploader installs our named bitstream under /bitstreams; do not use `--set-default` during initial testing. Optionally merge [config-fragment.ini](../fpga/config-fragment.ini) into the backed-up config.ini, preserving other projects. Its requested RP system frequency is not proof of exact output frequency. The temporary relay sets the clock itself, so the config edit is optional.

At the SDK REPL, `tt.shuttle.tt_um_zarina_phone_flight.enable()` loads this FPGA design. The same command does not add a project to the old TT.RUN.09 ASIC.

## Onboard USB-to-UART relay

An extra USB-UART adapter is unnecessary for this ETR route. [board_bridge.py](../fpga/board_bridge.py) accepts PC USB CDC binary bytes, then uses hardware UART1 at 115200 8N1 to GPIO20 = ui3. GPIO21 = ui4 is unused UART RX and remains an input. UART never uses uo4, which carries VGA R0. The relay first checks SDK mapping ui0=17, ui3=20, ui4=21 and aborts on incompatible hardware. References: [official GPIO map](https://github.com/TinyTapeout/tt-micropython-firmware/blob/main/src/ttboard/pins/gpio_map_dbv3.py) and [pin API](https://github.com/TinyTapeout/tt-micropython-firmware/blob/main/src/ttboard/pins/standard.py).

Remove any external UART driver and set input DIP switches OFF before setup. GPIO20 must not face another driven source. Connect a 3.3 V physical fire button and pulldown to ui0, leaving the RP pin as input; see WIRING.md. Tiny VGA belongs on OUTPUT PMOD. All uio and other unused pins remain inputs.

Install under a new filename and enter the REPL:

```powershell
mpremote connect COM7 fs cp fpga/board_bridge.py :board_bridge.py
mpremote connect COM7 repl
```

At the displayed prompt type:

```python
import board_bridge
board_bridge.main()
```

Wait for `RTU relay ready` and its clock report. Press **Ctrl-]** to detach mpremote while leaving the program running; see [official mpremote documentation](https://docs.micropython.org/en/latest/reference/mpremote.html). Close all other terminals using COM7. Further mpremote actions normally reset the running program, so do not use them during streaming.

Run the existing PC bridge against the ETR USB port; the phone remains separately attached over ADB:

```powershell
adb forward tcp:8765 tcp:8765
python -m pip install -r bridge/requirements.txt
python bridge/flight_bridge.py --tcp 127.0.0.1:8765 --serial COM7 --output controls.bin --vectors controls.hex
```

Enable USB stream and capture in the phone app, then hold still for calibration. See bridge/README.md for controls. USB CDC baud settings do not determine USB packet timing; the board's UART is explicitly 115200. The script disables Ctrl-C interpretation because binary packets can contain 0x03, and provides no software fire signal.

Stop the host with Ctrl-C, then management-reset or power-cycle the ETR to leave relay mode. Project reset alone does not stop its management script. Existing main.py and startup project stay untouched. After reset, optionally remove our file with `mpremote connect COM7 fs rm :board_bridge.py`. A disconnected host stops control packets, invoking RTL timeout and inhibiting firing.

## Verification limits

`python -m unittest discover -s fpga -p 'test*.py' -v` tests board guards, UART routing, input mode, reset order, wrong-clock refusal and every binary byte using mocked SDK objects. It is not execution on MicroPython hardware. CI separately builds the real bitstream. Still unverified: exact board/firmware compatibility, USB CDC behavior, clock measurement, VGA lock/colors, physical phone controls/latency, button wiring and complete gameplay on hardware. Record those results before silicon submission.
