"""Temporary USB-serial -> hardware UART relay for the ETR FabricFox demo board.

Run from the SDK REPL; do not replace main.py. Reset the board to leave relay mode.
This file runs on MicroPython; host unit tests exercise its safety/setup contract.
"""

PROJECT = "tt_um_zarina_phone_flight"
CLOCK_HZ = 25200000
BAUD = 115200
QUERY = b"RTU?\n"
READY = b"RTU READY 1\n"
SESSION_MS = 300


def valid_packet(packet):
    if len(packet) != 8 or packet[:2] != b"\xa5\x5a":
        return False
    if packet[3] not in (0, 1, 2, 3, 253, 254, 255) or packet[4] not in (0, 1, 2, 3, 253, 254, 255):
        return False
    if packet[5] > 4 or packet[6] & 252:
        return False
    crc = 0
    for value in packet[2:7]:
        crc ^= value
        for _ in range(8):
            crc = ((crc << 1) ^ (7 if crc & 128 else 0)) & 255
    return crc == packet[7]


class Session:
    """Bounded USB framing; query text never enters the FPGA UART."""
    def __init__(self, require_handshake=True):
        self.required = require_handshake
        self.armed = not require_handshake
        self.packet = bytearray()
        self.query = bytearray()

    def expire(self):
        self.armed = not self.required
        self.packet = bytearray()
        self.query = bytearray()

    def feed(self, value):
        # A query also cancels a packet interrupted by a previous connection.
        if value == QUERY[len(self.query)]:
            self.query.append(value)
            if len(self.query) == len(QUERY):
                self.query = bytearray()
                self.packet = bytearray()
                self.armed = True
                return None, READY
        else:
            self.query = bytearray(b"R") if value == ord("R") else bytearray()
        if self.packet:
            self.packet.append(value)
            if len(self.packet) == 2 and value != 0x5a:
                self.packet = bytearray(b"\xa5") if value == 0xa5 else bytearray()
            elif len(self.packet) == 8:
                packet = bytes(self.packet)
                self.packet = bytearray()
                if self.armed and valid_packet(packet):
                    return packet, None
            return None, None
        if value == 0xa5:
            self.packet.append(value)
        return None, None


def write_bounded(stream, data, attempts=4):
    """No unbounded retry or retained TX backlog on a stalled/disconnected sink."""
    offset = 0
    for _ in range(attempts):
        count = stream.write(data[offset:])
        if count is None or count <= 0:
            return False
        offset += count
        if offset == len(data):
            return True
    return False


def poll_relay(source, sink, uart, poller, clock, require_handshake=True):
    session = Session(require_handshake)
    last = clock.ticks_ms()
    draining = False
    while True:
        now = clock.ticks_ms()
        if clock.ticks_diff(now, last) >= SESSION_MS:
            session.expire()
            draining = True
            last = now
        if draining:
            for _ in range(64):
                pending = poller.poll(0)
                if not pending:
                    draining = False
                    break
                if not any(event[1] & 1 for event in pending):
                    break
                source.read(1)
            clock.sleep_ms(1)
            continue
        events = poller.poll(10)
        now = clock.ticks_ms()
        if clock.ticks_diff(now, last) >= SESSION_MS:
            session.expire()
            draining = True
            last = now
            continue
        if not events:
            continue
        # HUP/ERR must not cause an immediate busy loop or return to a binary REPL.
        if any(event[1] & 24 for event in events):
            session.expire()
            clock.sleep_ms(10)
            continue
        latest = None
        for _ in range(64):
            pending = poller.poll(0)
            if not pending:
                break
            if any(event[1] & 24 for event in pending):
                session.expire()
                latest = None
                clock.sleep_ms(10)
                break
            if not any(event[1] & 1 for event in pending):
                break
            value = source.read(1)
            if not value:
                session.expire()
                clock.sleep_ms(10)
                break
            packet, reply = session.feed(value[0])
            last = clock.ticks_ms()
            if reply:
                latest = None
                if not write_bounded(sink, reply):
                    session.expire()
            if packet:
                latest = packet
        else:
            # More than 64 bytes in one polling turn is backlog, not live 30Hz.
            # Disarm and discard it; Android must query again after draining.
            session.expire()
            latest = None
            draining = True
        if latest is not None and not write_bounded(uart, latest):
            session.expire()


def configure(tt, machine, manual_mode):
    # Refuse old/classic boards and unknown SDK mappings before touching pins.
    for name, expected in (("ui_in3", 20), ("ui_in4", 21), ("ui_in0", 17)):
        actual = getattr(tt.pins, name).gpio_num
        if actual != expected:
            raise RuntimeError("ETR GPIO mapping required: %s=%s (expected %s)" %
                               (name, actual, expected))
    getattr(tt.shuttle, PROJECT).enable()
    tt.mode = manual_mode
    # Manual mode leaves physical fire and remaining project inputs undriven.
    tt.pins.ui_in0.mode = machine.Pin.IN
    tt.reset_project(True)
    pwm = tt.clock_project_PWM(CLOCK_HZ)
    actual = tt.auto_clocking_freq
    if pwm is None or abs(actual - CLOCK_HZ) > CLOCK_HZ // 200:
        raise RuntimeError("Project clock outside +/-0.5%%: %s" % actual)
    # RX is unused GPIO21/ui4, deliberately never uo4 (which carries VGA R0).
    uart = machine.UART(1, baudrate=BAUD, bits=8, parity=None, stop=1,
                        tx=machine.Pin(20), rx=machine.Pin(21), timeout=20)
    tt.reset_project(False)
    return uart, actual


def relay(source, uart):
    # One byte avoids buffered USB reads waiting for an entire chunk indefinitely.
    # At 30*8 bytes/s this is small; UART hardware supplies precise bit timing.
    while True:
        chunk = source.read(1)
        if chunk:
            if not write_bounded(uart, chunk):
                return
        elif chunk == b"":
            return


def get_board():
    """Initialize SDK when raw REPL skipped main.py; preserve an existing SDK."""
    from ttboard.boot.demoboard_detect import DemoboardDetect, DemoboardVersion
    from ttboard.demoboard import DemoBoard
    if DemoboardDetect.PCB == DemoboardVersion.UNKNOWN:
        if not DemoboardDetect.probe():
            raise RuntimeError("No supported ETR carrier detected")
    return DemoBoard.get()


def main(require_handshake=False):
    import machine
    import micropython
    import sys
    import select
    import time
    from ttboard.mode import RPMode

    tt = get_board()
    uart = None
    try:
        uart, actual = configure(tt, machine, RPMode.ASIC_MANUAL_INPUTS)
        print("RTU relay ready; actual clock=%s Hz; UART1 TX=GPIO20; reset to exit" % actual)
        # Binary packets can contain 0x03; do not interpret that byte as Ctrl-C.
        micropython.kbd_intr(-1)
        poller = select.poll()
        poller.register(sys.stdin.buffer, select.POLLIN)
        try:
            poll_relay(sys.stdin.buffer, sys.stdout.buffer, uart, poller, time,
                       require_handshake=require_handshake)
        except Exception:
            # Never expose a Python REPL to binary traffic after READY on failure.
            # Management reset, then the startup FIRE escape, restores maintenance.
            tt.reset_project(True)
            uart.deinit()
            machine.Pin(20, machine.Pin.IN)
            while True:
                time.sleep_ms(100)
    finally:
        micropython.kbd_intr(3)
        if uart is not None:
            uart.deinit()
            machine.Pin(20, machine.Pin.IN)
            tt.reset_project(True)


if __name__ == "__main__":
    main()
