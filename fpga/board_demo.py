"""Temporary phone-free test of Phone Flight through its real UART input.

Copy board_bridge.py to the board, then mpremote run this file.
No startup/configuration files are changed. Ctrl-C stops the demo safely.
"""


def packet(index):
    # Restart every four seconds; sweep flight vertically and aim through 0..4.
    phase = index % 120
    dy = 255 if phase < 30 else 1 if phase < 60 else 0
    body = bytes((index & 255, 0, dy, (phase // 24), 3 if phase == 0 else 1))
    crc = 0
    for value in body:
        crc ^= value
        for _ in range(8):
            crc = ((crc << 1) ^ (7 if crc & 128 else 0)) & 255
    return b"\xa5\x5a" + body + bytes((crc,))


def send_demo(uart, clock, count=None):
    index = 0
    while count is None or index < count:
        data = packet(index)
        # Eight bytes fit the hardware UART buffer; never ignore a failed write.
        if uart.write(data) != len(data):
            raise RuntimeError("Demo UART write incomplete")
        index += 1
        clock.sleep_ms(33)


def main():
    import machine
    import time
    from ttboard.mode import RPMode
    from board_bridge import configure, get_board

    # mpremote raw-REPL soft reset skips main.py board initialization.
    tt = get_board()
    uart = None
    try:
        uart, actual = configure(tt, machine, RPMode.ASIC_MANUAL_INPUTS)
        print("RTU DEMO: Phone Flight, clock=%s Hz, UART1 GPIO20, ~30 packets/s" % actual)
        print("Phone disconnected. Cyan lamp; plane/enemy/aim animate. FIRE shoots.")
        print("Four-second restart cycle. Ctrl-C stops; no startup files changed.")
        send_demo(uart, time)
    finally:
        tt.reset_project(True)
        if uart is not None:
            uart.deinit()
            machine.Pin(20, machine.Pin.IN)


if __name__ == "__main__":
    main()
