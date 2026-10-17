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


if __name__ == "__main__":
    unittest.main()
