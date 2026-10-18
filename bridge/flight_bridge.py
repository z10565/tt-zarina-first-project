"""RTU raw JSONL to bounded UART controls. Python 3.10+, stdlib except serial output."""
import argparse
import json
import math
import socket
import time
import zipfile
from pathlib import Path

PERIOD_NS = 1_000_000_000 // 30
STALE_NS = 100_000_000


def crc8(data):
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ (7 if crc & 128 else 0)) & 255
    return crc


def packet(seq, dx=0, dy=0, aim=2, valid=False, restart=False):
    if not (-3 <= dx <= 3 and -3 <= dy <= 3 and 0 <= aim <= 4):
        raise ValueError('out-of-range control')
    body = bytes((seq & 255, dx & 255, dy & 255, aim, int(valid) | (2 if valid and restart else 0)))
    return b'\xa5\x5a' + body + bytes((crc8(body),))


def movement(value):
    """Zero through 0.6; ceil into three equal bins, saturating at 4.5."""
    magnitude = abs(value)
    if magnitude <= .6:
        return 0
    level = min(3, math.ceil((min(4.5, magnitude) - .6) / 1.3))
    return level if value > 0 else -level


def parse_record(line):
    obj = json.loads(line)
    if (not isinstance(obj, dict) or obj.get('v') != 1 or not isinstance(obj.get('session'), str) or not obj['session']
            or type(obj.get('seq')) is not int or obj['seq'] < 0
            or obj.get('sensor') not in ('accelerometer', 'gyroscope')
            or not isinstance(obj.get('t_ns'), str) or not obj['t_ns'].isdigit()):
        raise ValueError('invalid raw record')
    axes = tuple(obj.get(k) for k in ('x', 'y', 'z'))
    if not all(type(v) in (int, float) and math.isfinite(v) for v in axes):
        raise ValueError('invalid axes')
    return obj['session'], obj['seq'], obj['sensor'], int(obj['t_ns']), axes


class Controls:
    def __init__(self):
        self.session = None
        self.reset()

    def reset(self):
        self.latest = {}
        self.received = {}
        self.count = {'accelerometer': 0, 'gyroscope': 0}
        self.sums = {'accelerometer': [0., 0., 0.], 'gyroscope': [0., 0., 0.]}
        self.neutral = None
        self.bias = 0.
        self.angle = 0.
        self.filtered = [0., 0.]
        self.start_ns = None
        self.seq = -1

    def accept(self, line, receipt_ns=None):
        session, seq, sensor, stamp, axes = parse_record(line)
        if session != self.session:
            self.reset()
            self.session = session
        if seq <= self.seq or (sensor in self.latest and stamp < self.latest[sensor][0]):
            raise ValueError('sequence/timestamp regression')
        self.seq = seq
        if self.start_ns is None:
            self.start_ns = stamp
        previous = self.latest.get(sensor)
        self.latest[sensor] = (stamp, axes)
        self.received[sensor] = stamp if receipt_ns is None else receipt_ns
        if self.neutral is None:
            self.count[sensor] += 1
            self.sums[sensor] = [a + b for a, b in zip(self.sums[sensor], axes)]
            if stamp - self.start_ns >= 1_000_000_000 and min(self.count.values()) >= 10:
                self.neutral = [v / self.count['accelerometer'] for v in self.sums['accelerometer']]
                self.bias = self.sums['gyroscope'][2] / self.count['gyroscope']
            return stamp
        if sensor == 'accelerometer':
            # Fixed event-domain alpha: expected phone stream requests 50 Hz per sensor.
            self.filtered = [.75 * old + .25 * (value - neutral)
                             for old, value, neutral in zip(self.filtered, axes, self.neutral)]
        elif previous is not None:
            dt = min(.1, max(0., (stamp - previous[0]) / 1e9))
            rate = axes[2] - self.bias
            if abs(rate) > .06:
                self.angle = max(-.65, min(.65, self.angle + rate * dt))
        return stamp

    def output(self, now_ns):
        valid = (self.neutral is not None and len(self.received) == 2
                 and all(0 <= now_ns - t <= STALE_NS for t in self.received.values())
                 and max(v[0] for v in self.latest.values()) - min(v[0] for v in self.latest.values()) <= STALE_NS)
        if not valid:
            return 0, 0, 2, False
        # Positive gyro Z rotates counter-clockwise: cannon points upward (index 0).
        aim = max(0, min(4, math.floor(2 - self.angle / .325 + .5)))
        return movement(self.filtered[0]), -movement(self.filtered[1]), aim, True


def lines_from(path):
    if str(path).lower().endswith('.zip'):
        with zipfile.ZipFile(path) as archive:
            yield from archive.read('samples.jsonl').decode('utf-8').splitlines()
    else:
        with open(path, encoding='utf-8') as source:
            yield from source


def replay(lines):
    controls = Controls()
    next_tick = None
    previous_session = None
    sequence = 0
    for line in lines:
        if not line.strip():
            continue
        try:
            session, _, _, stamp, _ = parse_record(line)
            if session != previous_session:
                controls = Controls()  # Never expose previous-session controls at a new epoch.
                next_tick = stamp
                previous_session = session
            while next_tick < stamp:
                yield packet(sequence, *controls.output(next_tick))
                sequence += 1
                next_tick += PERIOD_NS
            controls.accept(line)
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            continue
    yield packet(sequence)  # Deterministic immediate disconnect safety.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--replay', type=Path, help='app samples.jsonl or diagnostic ZIP')
    source.add_argument('--tcp', help='ADB forwarded HOST:PORT (127.0.0.1:8765)')
    parser.add_argument('--serial', help='confirmed UART adapter COM port or /dev/ttyUSB0')
    parser.add_argument('--dry-run', action='store_true', help='print packet hex without UART')
    parser.add_argument('--output', type=Path, help='record binary UART packets')
    parser.add_argument('--vectors', type=Path, help='record one packet per hex line for RTL tests')
    parser.add_argument('--restart', action='store_true', help='request restart on first VALID update')
    args = parser.parse_args()
    if not any((args.serial, args.dry_run, args.output, args.vectors)):
        parser.error('choose --serial, --dry-run, --output, or --vectors')
    serial_port = None
    if args.serial:
        try:
            import serial
        except ImportError:
            parser.error('serial output needs python -m pip install -r bridge/requirements.txt')
        serial_port = serial.Serial(args.serial, 115200, bytesize=8, parity='N', stopbits=1,
                                    timeout=0, write_timeout=.1, xonxoff=False, rtscts=False, dsrdtr=False)
    binary = args.output.open('wb') if args.output else None
    vectors = args.vectors.open('w', encoding='ascii') if args.vectors else None
    restart_pending = args.restart
    def send(frame):
        nonlocal restart_pending
        if restart_pending and frame[6] & 1:
            frame = packet(frame[2], int.from_bytes(frame[3:4], signed=True),
                           int.from_bytes(frame[4:5], signed=True), frame[5], True, True)
            restart_pending = False
        if serial_port:
            serial_port.write(frame)
        if binary:
            binary.write(frame)
        if vectors:
            vectors.write(frame.hex(' ') + '\n')
        if args.dry_run:
            print(frame.hex(' '))
    try:
        if args.replay:
            for frame in replay(lines_from(args.replay)):
                send(frame)
                if serial_port:
                    time.sleep(1 / 30)
        else:
            host, port = args.tcp.rsplit(':', 1)
            controls = Controls()
            seq = 0
            buffer = b''
            with socket.create_connection((host, int(port)), timeout=3) as connection:
                connection.settimeout(.005)
                next_send = time.monotonic()
                while True:
                    try:
                        data = connection.recv(8192)
                        if not data:
                            break
                        buffer += data
                        if len(buffer) > 65536:
                            raise ValueError('oversized input')
                        while b'\n' in buffer:
                            line, buffer = buffer.split(b'\n', 1)
                            try:
                                controls.accept(line, time.monotonic_ns())
                            except (ValueError, KeyError, TypeError, UnicodeDecodeError):
                                pass
                    except socket.timeout:
                        pass
                    now = time.monotonic()
                    if now >= next_send:
                        send(packet(seq, *controls.output(time.monotonic_ns())))
                        seq = (seq + 1) & 255
                        next_send = now + 1 / 30
            send(packet(seq))
    except KeyboardInterrupt:
        if 'seq' in locals():
            send(packet(seq))
    finally:
        if args.tcp and 'seq' in locals():
            try:
                send(packet(seq))
            except OSError:
                pass  # Chip watchdog also inhibits movement/fire after host/serial failure.
        if serial_port:
            serial_port.close()
        if binary:
            binary.close()
        if vectors:
            vectors.close()


if __name__ == '__main__':
    main()
