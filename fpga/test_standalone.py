import importlib.util
from pathlib import Path
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location("standalone", Path(__file__).with_name("standalone.py"))
startup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(startup)


class StandaloneTests(unittest.TestCase):
    def setUp(self):
        self.original_dir = os.getcwd()
        self.temp = tempfile.TemporaryDirectory()
        os.chdir(self.temp.name)
        self.original = b"# existing board startup\r\nprint('normal SDK')\r\n"
        Path("main.py").write_bytes(self.original)

    def tearDown(self):
        os.chdir(self.original_dir)
        self.temp.cleanup()

    def fixture(self, pressed=False):
        tt = SimpleNamespace(pins=SimpleNamespace(ui_in0=SimpleNamespace(gpio_num=17),
                                                 ui_in3=SimpleNamespace(gpio_num=20)))
        pin = Mock(return_value=SimpleNamespace(value=lambda: pressed))
        pin.IN, pin.PULL_DOWN = 0, 1
        return tt, SimpleNamespace(Pin=pin), SimpleNamespace(sleep_ms=Mock()), Mock()

    def test_import_and_disabled_start_do_nothing(self):
        self.assertEqual(Path("main.py").read_bytes(), self.original)
        self.assertFalse(startup.start())
        self.assertFalse(Path(startup.BACKUP).exists())

    def test_explicit_install_and_restore_exact_original(self):
        Path("config.ini").write_bytes(b"keep config")
        startup.install()
        self.assertEqual(Path(startup.BACKUP).read_bytes(), self.original)
        self.assertEqual(Path("main.py").read_bytes(), self.original + startup.HOOK)
        self.assertTrue(Path(startup.ENABLED).exists())
        with self.assertRaises(RuntimeError):
            startup.install()
        startup.uninstall()
        self.assertEqual(Path("main.py").read_bytes(), self.original)
        self.assertEqual(Path("config.ini").read_bytes(), b"keep config")
        self.assertFalse(Path(startup.ENABLED).exists())

    def test_disable_marker_and_fire_escape_never_run_relay(self):
        startup.install()
        args = self.fixture(True)
        self.assertFalse(startup.start(*args))
        args[-1].assert_not_called()
        Path(startup.DISABLED).write_bytes(b"")
        self.assertFalse(startup.start())

    def test_normal_start_has_escape_window_and_requires_handshake(self):
        startup.install()
        args = self.fixture()
        self.assertTrue(startup.start(*args))
        self.assertEqual(args[2].sleep_ms.call_count, 100)
        args[-1].assert_called_once_with(require_handshake=True)

    def test_wrong_board_fails_before_touching_pins(self):
        startup.install()
        args = self.fixture()
        args[0].pins.ui_in3.gpio_num = 15
        with self.assertRaises(RuntimeError):
            startup.start(*args)
        args[1].Pin.assert_not_called()
