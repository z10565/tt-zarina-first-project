import importlib.util
import io
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location("board_bridge", Path(__file__).with_name("board_bridge.py"))
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class BoardBridgeTests(unittest.TestCase):
    def fixture(self):
        pins = SimpleNamespace(ui_in3=SimpleNamespace(gpio_num=20),
                               ui_in4=SimpleNamespace(gpio_num=21),
                               ui_in0=SimpleNamespace(gpio_num=17, mode=None))
        design = SimpleNamespace(enable=Mock())
        tt = SimpleNamespace(pins=pins, shuttle=SimpleNamespace(**{bridge.PROJECT: design}),
                             reset_project=Mock(), clock_project_PWM=Mock(return_value=object()),
                             auto_clocking_freq=25200000)
        pin = Mock(side_effect=lambda number: number)
        pin.IN = "input"
        machine = SimpleNamespace(Pin=pin, UART=Mock())
        return tt, machine, design

    def test_etr_uses_uart1_and_only_input_pins(self):
        tt, machine, design = self.fixture()
        bridge.configure(tt, machine, "manual")
        design.enable.assert_called_once()
        machine.UART.assert_called_once_with(1, baudrate=115200, bits=8, parity=None,
                                            stop=1, tx=20, rx=21, timeout=20)
        self.assertEqual(tt.pins.ui_in0.mode, "input")
        self.assertEqual(tt.mode, "manual")
        self.assertEqual([call.args for call in tt.reset_project.call_args_list], [(True,), (False,)])

    def test_wrong_board_fails_before_enabling(self):
        tt, machine, design = self.fixture()
        tt.pins.ui_in3.gpio_num = 15
        with self.assertRaises(RuntimeError):
            bridge.configure(tt, machine, "manual")
        design.enable.assert_not_called()
        machine.UART.assert_not_called()

    def test_wrong_clock_holds_reset_and_never_enables_uart(self):
        tt, machine, _ = self.fixture()
        tt.auto_clocking_freq = 50000000
        with self.assertRaises(RuntimeError):
            bridge.configure(tt, machine, "manual")
        machine.UART.assert_not_called()
        tt.reset_project.assert_called_once_with(True)

    def test_relay_preserves_every_binary_byte_including_ctrl_c(self):
        payload = bytes(range(256))
        uart = Mock()
        uart.write.side_effect = len
        bridge.relay(io.BytesIO(payload), uart)
        self.assertEqual(b"".join(call.args[0] for call in uart.write.call_args_list), payload)

    def packet(self, seq=3, dx=0, dy=0, aim=2, flags=1):
        data = bytearray((165, 90, seq, dx, dy, aim, flags))
        crc = 0
        for value in data[2:]:
            crc ^= value
            for _ in range(8):
                crc = ((crc << 1) ^ (7 if crc & 128 else 0)) & 255
        return bytes(data + bytes((crc,)))

    def feed(self, session, data):
        results = [session.feed(value) for value in data]
        return [packet for packet, _ in results if packet], [reply for _, reply in results if reply]

    def test_handshake_gate_and_query_not_forwarded(self):
        session = bridge.Session()
        packet = self.packet()
        self.assertEqual(self.feed(session, packet), ([], []))
        self.assertEqual(self.feed(session, bridge.QUERY), ([], [bridge.READY]))
        self.assertEqual(self.feed(session, packet), ([packet], []))

    def test_all371_app_golden_packets_survive_standalone_framing(self):
        # The Android Kotlin tests independently reproduce these same bytes.
        lines = (Path(__file__).parents[1] / "bridge/fixtures/controls.hex").read_text().splitlines()
        packets = [bytes.fromhex(line) for line in lines if line.strip()]
        self.assertEqual(len(packets), 371)
        session = bridge.Session()
        forwarded = []
        for index, packet in enumerate(packets):
            if index % 30 == 0:
                self.assertEqual(self.feed(session, bridge.QUERY), ([], [bridge.READY]))
            result, replies = self.feed(session, packet)
            forwarded.extend(result)
            self.assertEqual(replies, [])
        self.assertEqual(forwarded, packets)

    def test_query_recovers_partial_packet_and_expired_connection(self):
        session = bridge.Session()
        self.feed(session, self.packet()[:4])
        self.assertEqual(self.feed(session, bridge.QUERY), ([], [bridge.READY]))
        self.assertEqual(self.feed(session, self.packet())[0], [self.packet()])
        session.expire()
        self.assertEqual(self.feed(session, self.packet())[0], [])
        self.assertEqual(self.feed(session, bridge.QUERY)[1], [bridge.READY])

    def test_corrupt_and_out_of_range_controls_are_dropped(self):
        session = bridge.Session(False)
        corrupt = bytearray(self.packet())
        corrupt[-1] ^= 1
        for bad in (corrupt, self.packet(dx=4), self.packet(dy=252),
                    self.packet(aim=5), self.packet(flags=4)):
            self.assertEqual(self.feed(session, bad)[0], [])
        good = self.packet(dx=253, dy=3, aim=4)
        self.assertEqual(self.feed(session, good)[0], [good])

    def test_partial_and_stalled_writes_are_bounded(self):
        output = Mock()
        output.write.side_effect = [2, 3, 3]
        self.assertTrue(bridge.write_bounded(output, b"12345678"))
        self.assertEqual([c.args[0] for c in output.write.call_args_list],
                         [b"12345678", b"345678", b"678"])
        for result in (0, None):
            output = Mock()
            output.write.return_value = result
            self.assertFalse(bridge.write_bounded(output, b"12345678"))
            output.write.assert_called_once()

    def test_hup_does_not_read_or_forward_or_spin_without_sleep(self):
        source, sink, uart = Mock(), Mock(), Mock()
        poller = Mock()
        poller.poll.side_effect = [[(source, 16)], RuntimeError("stop test")]
        clock = SimpleNamespace(ticks_ms=Mock(return_value=0),
                                ticks_diff=lambda a, b: a-b, sleep_ms=Mock())
        with self.assertRaisesRegex(RuntimeError, "stop test"):
            bridge.poll_relay(source, sink, uart, poller, clock)
        source.read.assert_not_called()
        uart.write.assert_not_called()
        clock.sleep_ms.assert_called_with(10)

    def test_backlog_is_discarded_until_quiet_then_fresh_query_works(self):
        source = io.BytesIO(bridge.QUERY + self.packet() * 10)
        sink, uart = Mock(), Mock()
        sink.write.side_effect = len
        uart.write.side_effect = len
        calls = [0]
        def poll(_timeout):
            calls[0] += 1
            if calls[0] > 120:
                raise RuntimeError("stop test")
            return [(source, 1)] if source.tell() < len(source.getvalue()) else []
        clock = SimpleNamespace(ticks_ms=lambda: 0, ticks_diff=lambda a,b: a-b,
                                sleep_ms=Mock())
        with self.assertRaisesRegex(RuntimeError, "stop test"):
            bridge.poll_relay(source, sink, uart, SimpleNamespace(poll=poll), clock)
        uart.write.assert_not_called()

    def test_idle_timeout_drains_old_packet_and_reconnect_requires_query(self):
        source, sink, uart = Mock(), Mock(), Mock()
        sink.write.side_effect = len
        uart.write.side_effect = len
        pending = bytearray()
        state = {"time": 0, "turn": 0}
        def read(_size):
            value = bytes(pending[:1])
            del pending[:1]
            return value
        source.read.side_effect = read
        packet = self.packet()
        def poll(timeout):
            if timeout:
                state["turn"] += 1
                if state["turn"] == 1:
                    pending.extend(bridge.QUERY + packet)
                elif state["turn"] == 2:
                    state["time"] = 400  # scheduler/USB pause with queued controls
                    pending.extend(packet)
                elif state["turn"] == 3:
                    pending.extend(packet)  # no fresh query: must remain disarmed
                elif state["turn"] == 4:
                    pending.extend(bridge.QUERY + packet)
                else:
                    raise RuntimeError("stop test")
            return [(source, 1)] if pending else []
        clock = SimpleNamespace(ticks_ms=lambda: state["time"],
                                ticks_diff=lambda a,b: a-b, sleep_ms=Mock())
        with self.assertRaisesRegex(RuntimeError, "stop test"):
            bridge.poll_relay(source, sink, uart, SimpleNamespace(poll=poll), clock)
        self.assertEqual(uart.write.call_count, 2)  # first session and fresh-query session only
        self.assertEqual(sink.write.call_count, 2)


if __name__ == "__main__":
    unittest.main()
