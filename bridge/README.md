# Phone to UART bridge

The phone has no direct digital sensor-to-chip connection. This implementation uses
**phone app -> loopback TCP over USB ADB -> PC preprocessing -> USB-UART -> chip RX**.
No network listener is exposed to Wi-Fi: the Android listener binds 127.0.0.1 only.
The chip has no USB, Bluetooth or Wi-Fi core. Physical UART adapter/board voltage and
wiring remain unverified; follow [the wiring checklist](../docs/WIRING.md) first.

## Run live

Install the sibling Android app version 0.2.0. Authorize USB debugging on the phone.
Keep the app in the foreground. In a terminal at the chip repository:

```powershell
adb devices
adb forward tcp:8765 tcp:8765
python -m pip install -r bridge/requirements.txt
python bridge/flight_bridge.py --tcp 127.0.0.1:8765 --dry-run
```

Tap **Enable USB stream**, then **Start capture** before starting the bridge CLI
(or enable stream first and start capture as soon as CLI connects). Hold the phone
approximately face-up and still for one second. The bridge calibrates neutral tilt
and gyro bias. The dry run prints hex packets without connecting hardware.
After adapter/board verification, replace `--dry-run` with `--serial COM7` using the
actual detected serial port. `--output controls.bin --vectors controls.hex` can
record the exact emitted UART bytes alongside either mode. Use `--restart` for a
single restart request on the first valid update. No software command fires.

A capture restart creates a new session and recalibrates (aim resets to center).
Leaving the app, saving, stopping capture or disabling streaming closes the socket.
Re-enable streaming and rerun the host command after a disconnect. An app-side
128-event queue drops its oldest entry under backpressure and displays drops;
sensor callbacks only offer immutable accepted recording events, never do socket IO.
The raw session/seq/timestamp are exactly the diagnostic recorder's accepted events.

## Mapping and framing

Raw acceleration includes gravity in Android natural-device axes. The bridge
averages each sensor for at least one sensor-time second and >=10 samples each,
then subtracts calibrated acceleration neutral and gyroscope Z bias. Calibration
requires a stationary phone; no motion/stationarity classifier is implemented.
Start a new capture to recalibrate. The app retains raw values unchanged.

Acceleration X/Y is filtered per event with `filtered = .75*old + .25*(raw-neutral)`.
For each axis, magnitude <=0.6 m/s² maps to zero; otherwise
`ceil((min(abs(value),4.5)-0.6)/1.3)` gives 1..3. Positive X moves right;
positive Y moves up (negative screen dy). The phone orientation is relative to its
calibrated face-up hold, independent of UI rotation. Test which physical tilt feels
natural on the actual S21 FE before changing signs.

For gyro Z, ignore corrected rates <=0.06 rad/s, integrate with sensor dt limited
to 0..0.1 s, clamp angle to +/-0.65 rad. Direction is
`clamp(floor(2-angle/0.325+0.5),0,4)`. Positive Z rotates the cannon upward;
neutral index 2 points right. No floating point reaches the chip.

Emit at 30 Hz, UART115200 8N1 with no flow control. Eight bytes:
`A5 5A seq dx dy aim flags crc`. Signed dx/dy bytes -3..3, aim0..4,
flags bit0 valid, bit1 restart, other bits0. CRC8 polynomial07 init0, no reflection
or xorout, covering seq through flags. Sequence wraps256. See the authoritative
[interface](../docs/INTERFACE.md). The chip applies complete validated packets atomically.

Both sensors need receipt age <=100ms and paired sensor timestamps within100ms.
Calibration, silence and disconnect produce invalid neutral controls (0,0,2).
Repeated live emissions become invalid after100ms even if the TCP connection stays
open. EOF/interrupt/error attempts an invalid update immediately; chip watchdog
also disables controls/fire when updates stop. This bounds disconnect behavior
without requiring feedback pins. Queue latency and USB/device scheduling still
need physical measurement. A restarted session clears all preprocessing state;
duplicate/out-of-order seq, per-sensor timestamp regression, invalid JSON/nonfinite
axes are rejected. CLI input line accumulation is bounded64KiB.

## Deterministic replay and tests

```powershell
python -m unittest discover -s bridge/tests -v
python bridge/flight_bridge.py --replay bridge/fixtures/samples.jsonl --dry-run --output controls.bin --vectors controls.hex
python bridge/flight_bridge.py --replay recording.zip --vectors controls.hex
```

Replay runs in sensor time at30Hz (no real-time sleeps unless serial output selected),
invalid while calibrating and at final EOF. Each `controls.hex` line contains one
complete packet with eight hex bytes separated by spaces; RTL tests transmit these
bytes as115200 8N1. `controls.bin` is their concatenation. Expected controls can be
decoded directly: bytes3/4 signed, byte5 aim, byte6 flags. CRC tests include the
standard `123456789 -> F4` check vector.

`fixtures/samples.jsonl` and `metadata.json` are copied byte-for-byte from the real
Android app v0.1.0 export `rtu-motion-validation.zip`, captured2026-10-17 on a
**Google Android16 x86_64 emulator**, not a physical phone. Metadata records1233
accepted events,617 accelerometer and616 gyroscope, no recorder drops. This is an
actual app sensor/serialization capture, not evidence of S21 FE physical motion or
latency. `fixtures/controls.hex` is its deterministic bridge output. The fixture
unit test compares every replay packet to this checked-in file. It provides a raw
app->preprocessing->RTL test path while synthetic tests cover extreme motion,
malformed data, calibration, stale input and numerical boundaries.

No physical serial hardware was available during implementation. Do not claim USB
UART voltages, firing button wiring, phone USB drivers, or real-chip behavior are
verified from these tests.
