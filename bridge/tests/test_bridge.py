import json
import sys
import unittest
import socket
import subprocess
import tempfile
import threading
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from flight_bridge import Controls, crc8, movement, packet, parse_record, replay


def record(seq, sensor, t, x=0, y=0, z=0, session='test'):
    return json.dumps(dict(v=1, session=session, seq=seq, sensor=sensor, t_ns=str(t), x=x, y=y, z=z))


def calibrated():
    c = Controls()
    for n in range(52):
        for i, sensor in enumerate(('accelerometer', 'gyroscope')):
            c.accept(record(n * 2 + i, sensor, n * 20_000_000, z=9.8 if i == 0 else .01))
    return c


class BridgeTests(unittest.TestCase):
    def test_crc_known_vector(self):
        self.assertEqual(crc8(b'123456789'), 0xf4)
        self.assertEqual(packet(255, -3, 3, 4, True)[:7], bytes.fromhex('a5 5a ff fd 03 04 01'))
        self.assertEqual(packet(256)[2], 0)
        self.assertRaises(ValueError, packet, 0, 4)

    def test_deadzone_saturation(self):
        for value, expected in [(0, 0), (.6, 0), (.601, 1), (1.9, 1), (2, 2), (4.5, 3), (100, 3), (-100, -3)]:
            self.assertEqual(movement(value), expected)

    def test_calibration_stale_and_axes(self):
        c = calibrated()
        self.assertEqual(c.output(1_020_000_000), (0, 0, 2, True))
        self.assertFalse(c.output(1_120_000_001)[3])
        for n in range(40):
            stamp = 1_040_000_000 + n * 20_000_000
            c.accept(record(104 + n * 2, 'accelerometer', stamp, x=100, y=100, z=9.8))
            c.accept(record(105 + n * 2, 'gyroscope', stamp, z=100))
        self.assertEqual(c.output(stamp), (3, -3, 0, True))
        self.assertEqual(c.angle, .65)

    def test_bias_and_deadzone(self):
        c = calibrated()
        c.accept(record(104, 'gyroscope', 1_040_000_000, z=.05))
        self.assertEqual(c.angle, 0)
        self.assertAlmostEqual(c.bias, .01)

    def test_session_reset_and_regressions(self):
        c = calibrated()
        self.assertRaises(ValueError, c.accept, record(1, 'gyroscope', 0))
        self.assertRaises(ValueError, c.accept, record(200, 'gyroscope', 0))
        c.accept(record(0, 'accelerometer', 0, session='next'))
        self.assertFalse(c.output(0)[3])
        self.assertIsNone(c.neutral)

    def test_bad_json_and_nonfinite(self):
        for line in ('{}', 'garbage', record(0, 'gyro', 0), record(0, 'gyroscope', 0, x=float('nan'))):
            self.assertRaises((ValueError, KeyError), parse_record, line)

    def test_replay_deterministic_and_crc(self):
        lines = [record(n * 2 + i, sensor, n * 20_000_000, z=9.8 if i == 0 else 0)
                 for n in range(70) for i, sensor in enumerate(('accelerometer', 'gyroscope'))]
        frames = list(replay(lines))
        self.assertEqual(frames, list(replay(lines)))
        self.assertTrue(any(frame[6] == 1 for frame in frames))
        self.assertEqual(frames[-1][6], 0)
        self.assertTrue(all(len(f) == 8 and crc8(f[2:7]) == f[7] for f in frames))

    def test_live_partial_reads_stale_and_disconnect(self):
        listener = socket.socket()
        listener.bind(('127.0.0.1', 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        def phone():
            with listener:
                connection, _ = listener.accept()
                with connection:
                    raw = ('bad JSON\n' + '\n'.join(record(n * 2 + i, sensor, n * 20_000_000,
                         z=9.8 if i == 0 else 0) for n in range(70)
                         for i, sensor in enumerate(('accelerometer', 'gyroscope'))) + '\n').encode()
                    for start in range(0, len(raw), 77):
                        connection.sendall(raw[start:start + 77])
                    time.sleep(.25)
        thread = threading.Thread(target=phone)
        thread.start()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'packets.bin'
            result = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / 'flight_bridge.py'),
                '--tcp', f'127.0.0.1:{port}', '--output', str(output)], capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            data = output.read_bytes()
            frames = [data[n:n+8] for n in range(0, len(data), 8)]
            self.assertTrue(any(frame[6] == 1 for frame in frames))
            self.assertTrue(len(frames) > 3)
            self.assertEqual(frames[-1][6], 0)
            self.assertEqual(frames[-2][6], 0)
        thread.join(2)

    def test_real_app_fixture(self):
        path = Path(__file__).resolve().parents[1] / 'fixtures' / 'samples.jsonl'
        lines = path.read_text().splitlines()
        self.assertEqual(len(lines), 1233)
        frames = list(replay(lines))
        expected = (path.parent / 'controls.hex').read_text().splitlines()
        self.assertEqual([frame.hex(' ') for frame in frames], expected)


if __name__ == '__main__':
    unittest.main()
