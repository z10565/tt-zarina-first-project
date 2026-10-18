# Phone directly to ETR USB: opt-in standalone startup

## Switch from the working board demo to phone controls

On 2026-10-18 the user reported that the independent VGA animation and the Phone Flight UART demo both animate on the mentor's board. The phone-to-board USB connection, power and readiness exchange remain pending. Stop the demo with Ctrl-C. From the mentor's `tt-fpga` directory, using the diagnostic branch already checked out:

```powershell
git -C projects/tt-zarina-first-project pull --ff-only
$Backup = "phone-board-backup-" + (Get-Date -Format "yyyyMMdd-HHmmss-fff")
New-Item -ItemType Directory $Backup
mpremote connect COM3 fs cp :main.py "$Backup/main.py"
mpremote connect COM3 fs cp :config.ini "$Backup/config.ini"
```

Check both backups succeeded before continuing. Copy the helpers and explicitly enable startup:

```powershell
mpremote connect COM3 fs cp projects/tt-zarina-first-project/fpga/board_bridge.py :board_bridge.py
mpremote connect COM3 fs cp projects/tt-zarina-first-project/fpga/standalone.py :standalone.py
mpremote connect COM3 exec "import standalone; print(standalone.enable())"
```

Expect `Phone relay enabled`. `enable()` installs the existing reversible hook on first use, or re-enables a previously installed hook only when main.py exactly matches its saved backup plus our hook. It removes our diagnostic disable marker. Modified startup or orphaned backups cause a refusal; retain the error and inspect rather than deleting backups to force installation. config.ini, other images and firmware remain unchanged. This replaces only our two helper files; preserve mentor modifications if present. No new bitstream is needed after the working game demo.

Disconnect board USB from the laptop and connect it to the phone with an OTG-capable data connection; this cold start runs the installed relay. Keep VGA attached. Leave FIRE released during normal startup. In RTU Motion choose **Connect ETR USB**, grant permission and tap Connect again if asked. Then **Start capture**, hold approximately face-up and still for one second, and tilt/rotate. The indicator becomes cyan when valid controls arrive; physical FIRE shoots. Use **Restart game** after game over. No four-second demo restart is active in phone mode.

If it fails, record the app's exact direct-USB status (board not found, permission, waiting for readiness, or connected) and the VGA lamp color. Those distinguish USB enumeration/power from relay startup and sensor calibration. Do not treat a visible but paused game as proof that the phone connected. This transition still requires physical testing.

This uses the purple ETR demo board and FabricFox FPGA simulator identified in the photos, with Tiny VGA on OUTPUT PMOD. The existing white TT.RUN.09 ASIC board cannot run a newly uploaded FPGA design. The phone is USB host through an OTG/data cable; the ETR management MCU's existing USB CDC interface receives bytes and forwards UART1 TX to FPGA ui3. No PC is needed during play after setup. Exact OTG compatibility, USB power budget, ETR firmware and hardware operation remain unverified.

Use the Android build with **direct USB control**, not the older ADB-only stream. The existing PC/ADB bridge and temporary REPL launch remain available; opt-in installation below does not change their default configuration. The temporary `board_bridge.main()` accepts existing binary packets; the installed `standalone.start()` explicitly requests handshake gating.

## Safety and protocol

After USB permission and CDC configuration, Android sends ASCII `RTU?\n` and waits for exact `RTU READY 1\n` before sending controls. Retry the query at most 250 ms apart until readiness. Repeat on every connection/session, after a scheduling stall of at least150ms, and once per second to recover a disarmed relay. This is a versioned relay handshake, not Python code, and the app never uploads or executes REPL commands. READY is emitted only after correct ETR mapping, bitstream loading, clock check and UART setup succeed. Host closes/stops control transmission when paused or detached.

The relay consumes the query, cancels partial packet state, and forwards only complete eight-byte CRC/range-valid control packets. Query recognition also cancels an interrupted binary packet. The existing FPGA packet format, update rate and watchdog are unchanged. USB silence for 300 ms disarms standalone reception; Android must perform another query before sending valid controls. FPGA's ~250 ms watchdog independently inhibits movement/firing. Disconnection/HUP does not drop into the REPL or spin without sleeping.

Polling reads at most 64 bytes per turn. More traffic is treated as old backlog and discarded until an idle boundary; the next fresh query must rearm it. Within a turn only the newest complete packet is forwarded. Stalled writes get bounded attempts, preserving partial-write offsets, and never create a retained TX queue. A UART write failure disarms reception. After such an error or sustained burst, disconnect/reconnect in the app to re-handshake. These rules intentionally favor stopping over replaying delayed controls. Individual USB driver writes retain firmware-defined blocking limits, so actual USB latency still needs measurement.

Ctrl-C processing is disabled while binary traffic is accepted, since 0x03 is a legal byte. A relay-loop exception holds project reset and stops forwarding in a maintenance-safe loop; it never exposes a Python REPL to remaining binary traffic. Management reset and the bypass below recover access. DTR behavior varies by installed firmware: if opening CDC reboots the ETR, wait through startup and retry the query; do not assume DTR reset or a particular USB VID/PID from the photos.

## One-time installation, explicitly requested on the board

First follow [FPGA setup](FPGA.md) to build/upload `build/tt_um_zarina_phone_flight.bin`. Verify the installed board SDK version and GPIO map. Read [wiring](WIRING.md): 3.3 V only, input DIP switches OFF, no external UART driver, physical active-high fire on ui0 with pulldown. Ensure adequate power when the phone supplies USB host power; do not connect conflicting 5 V supplies. Power/USB hub selection remains a hardware check.

Keep an independent PC copy of the existing files. Commands below are examples with `COM7` replaced by the ETR port; close Commander and other serial clients first:

```powershell
python -m pip install mpremote
mpremote connect COM7 fs ls
mpremote connect COM7 fs cp :main.py fpga/board-main.original.py
mpremote connect COM7 fs cp :config.ini fpga/board-config.original.ini
mpremote connect COM7 fs cp fpga/board_bridge.py :board_bridge.py
mpremote connect COM7 fs cp fpga/standalone.py :standalone.py
mpremote connect COM7 repl
```

At the SDK REPL, only after inspecting those backups:

```python
import standalone
standalone.install()
```

Import alone changes nothing. `install()` refuses an existing `main.py.rtu-backup`, oversized main.py or an already present hook. It saves and verifies a byte-for-byte board-local backup, then appends a small call to the existing SDK main.py and creates `rtu-standalone.enabled`. It does not replace the existing SDK body, config.ini, firmware or other bitstreams. Backups are retained rather than silently overwritten. A power failure during filesystem writes remains a recovery risk; the independent PC backup is essential.

Cold reset/power-cycle the ETR. The original SDK initializes first, then our hook offers a two-second bypass window before loading the FPGA relay. Connect the phone, grant USB permission and start direct USB control. The app's readiness exchange confirms relay mode instead of relying on a serial-open event. Calibrate with the phone still. Physical fire remains the only firing input.

## Bypass and restore

For maintenance, hold physical FIRE **during the announced two-second hook window after SDK initialization**. Release afterward. The hook returns to the normal SDK REPL. Holding inputs high during initial SDK board detection can interfere with older firmware; the hook window comes after that detection. This escape depends on the specified button wiring and must be tested on the actual board before relying on unattended startup.

At a maintenance REPL, disable startup by creating `rtu-standalone.disabled`:

```python
open('rtu-standalone.disabled', 'w').close()
```

The hook then returns immediately on subsequent starts. Remove that marker to re-enable. Remove `rtu-standalone.enabled` to disable as well. To restore the original main.py exactly:

```python
import standalone
standalone.uninstall()
```

Reset afterward. The backup remains for inspection; config.ini and all bitstreams remain intact. Do not delete or overwrite the backup casually to force reinstall. To reinstall, inspect/retain an independent copy and explicitly remove the obsolete backup after successful restoration.

Alternative recovery: [MicroPython documents](https://docs.micropython.org/en/latest/reference/reset_boot.html) that raw-REPL soft resets skip main.py. `mpremote` normally enters raw REPL and soft-resets for filesystem commands, but the running relay deliberately disables Ctrl-C, so entry can require the physical startup bypass or precisely timed management reset. Do not promise that mpremote can interrupt an active relay. Do not use UF2/BOOTSEL reflashing as the normal escape: firmware upgrades can erase board files. If the hook or original main.py is damaged, recover through raw REPL with the saved PC main.py when available; consult the official board guide before any destructive firmware recovery.

## Evidence and remaining verification

Local verification on2026-10-18:17 relay/startup host tests and10 PC-bridge tests passed. The Android app's34 JVM tests and7 Android16 emulator tests passed with build/lint. Its Kotlin converter matches all371 captured-app and145 synthetic Python packets; the board parser independently forwards all371 fixture packets byte-for-byte. No RTL, tile allocation, VGA mapping, process or physical-build constraints changed for standalone transport.

Host tests: `python -m unittest discover -s fpga -p 'test*.py' -v`. They cover framing/CRC/ranges, handshake, reconnect state, stalled/partial writes, HUP, backlog, exact startup backup/restore, disabled markers, wrong-board refusal and fire bypass using mocked SDK objects. They do not prove MicroPython USB polling, physical fire, power delivery, CDC DTR behavior, Android USB enumeration or FPGA VGA/gameplay on the real boards.

The startup approach follows the [official SDK main.py](https://github.com/TinyTapeout/tt-micropython-firmware/blob/d485c7a9986336024e35d790568fca33be1c5665/src/main.py), which completes board detection and SDK initialization before returning. Poll behavior follows [MicroPython select](https://docs.micropython.org/en/latest/library/select.html). No files were installed on physical hardware during development, and no manufacturing submission occurs here.
