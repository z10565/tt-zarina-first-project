"""Temporary USB-serial -> hardware UART relay for the ETR FabricFox demo board.

Run from the SDK REPL; do not replace main.py. Reset the board to leave relay mode.
This file runs on MicroPython; host unit tests exercise its safety/setup contract.
"""

PROJECT = "tt_um_zarina_phone_flight"
CLOCK_HZ = 25200000
BAUD = 115200


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
            while uart.write(chunk) != len(chunk):
                pass
        elif chunk == b"":
            return


def main():
    import machine
    import micropython
    import sys
    from ttboard.demoboard import DemoBoard
    from ttboard.mode import RPMode

    tt = DemoBoard.get()
    uart = None
    try:
        uart, actual = configure(tt, machine, RPMode.ASIC_MANUAL_INPUTS)
        print("RTU relay ready; actual clock=%s Hz; UART1 TX=GPIO20; reset to exit" % actual)
        # Binary packets can contain 0x03; do not interpret that byte as Ctrl-C.
        micropython.kbd_intr(-1)
        relay(sys.stdin.buffer, uart)
    finally:
        micropython.kbd_intr(3)
        if uart is not None:
            uart.deinit()
            machine.Pin(20, machine.Pin.IN)
            tt.reset_project(True)


if __name__ == "__main__":
    main()
