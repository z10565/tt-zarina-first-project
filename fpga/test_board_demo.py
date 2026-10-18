import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bridge"))
import flight_bridge

spec = importlib.util.spec_from_file_location("board_demo", Path(__file__).with_name("board_demo.py"))
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


class DemoTests(unittest.TestCase):
    def test_packets_match_production_encoder_including_sequence_wrap(self):
        for index in range(600):
            phase = index % 120
            expected = flight_bridge.packet(index, dy=-1 if phase < 30 else 1 if phase < 60 else 0,
                                           aim=phase // 24, valid=True, restart=phase == 0)
            self.assertEqual(demo.packet(index), expected)

    def test_hardware_writes_and_rate(self):
        uart = SimpleNamespace(write=Mock(side_effect=len))
        clock = SimpleNamespace(sleep_ms=Mock())
        demo.send_demo(uart, clock, count=121)
        self.assertEqual([c.args[0] for c in uart.write.call_args_list], [demo.packet(i) for i in range(121)])
        self.assertEqual(clock.sleep_ms.call_count, 121)
        clock.sleep_ms.assert_called_with(33)

    def test_failed_write_stops(self):
        uart = SimpleNamespace(write=Mock(return_value=4))
        clock = SimpleNamespace(sleep_ms=Mock())
        with self.assertRaises(RuntimeError):
            demo.send_demo(uart, clock, count=2)
        clock.sleep_ms.assert_not_called()
