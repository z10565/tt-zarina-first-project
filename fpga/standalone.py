"""Explicit opt-in startup hook. Importing this module never installs anything."""

MAIN = "main.py"
BACKUP = "main.py.rtu-backup"
ENABLED = "rtu-standalone.enabled"
DISABLED = "rtu-standalone.disabled"
HOOK = b"\n# RTU standalone opt-in hook\nimport standalone\nstandalone.start()\n"


def exists(path):
    try:
        with open(path, "rb"):
            return True
    except OSError:
        return False


def install():
    """Run explicitly on the board after backups; never silently replace backups."""
    if exists(BACKUP):
        raise RuntimeError("Backup already exists; inspect/restore it before reinstalling")
    with open(MAIN, "rb") as source:
        original = source.read(65537)
    if len(original) > 65536 or b"RTU standalone opt-in hook" in original:
        raise RuntimeError("Unexpected main.py; install refused")
    with open(BACKUP, "wb") as target:
        target.write(original)
    # Verify the saved copy before changing startup.
    with open(BACKUP, "rb") as saved:
        if saved.read() != original:
            raise RuntimeError("Backup verification failed; main.py unchanged")
    with open(MAIN, "ab") as target:
        target.write(HOOK)
    with open(ENABLED, "wb") as target:
        target.write(b"1\n")
    return "Installed; cold reset to start. Hold physical FIRE during startup to bypass."


def enable():
    """Install once or re-enable an exact, verified existing RTU hook."""
    import os
    with open(MAIN, "rb") as source:
        current = source.read(65537)
    if HOOK in current:
        with open(BACKUP, "rb") as source:
            original = source.read(65537)
        if len(current) > 65536 or len(original) > 65536 or current != original + HOOK:
            raise RuntimeError("Startup differs from saved backup + RTU hook; inspect manually")
        with open(ENABLED, "wb") as target:
            target.write(b"1\n")
    else:
        install()  # Retains all original refusal/backup protections.
    if exists(DISABLED):
        os.remove(DISABLED)
    return "Phone relay enabled. Disconnect laptop, then power board from phone."


def uninstall():
    """Restore exact previous main.py, leaving backup for inspection."""
    import os
    with open(BACKUP, "rb") as source:
        original = source.read(65537)
    if len(original) > 65536:
        raise RuntimeError("Invalid backup size")
    with open(MAIN, "wb") as target:
        target.write(original)
    if exists(ENABLED):
        os.remove(ENABLED)
    return "Original main.py restored; backup retained. Reset board."


def start(tt=None, machine=None, clock=None, run=None):
    if not exists(ENABLED) or exists(DISABLED):
        return False
    if tt is None:
        from ttboard.demoboard import DemoBoard
        tt = DemoBoard.get()
    if tt.pins.ui_in0.gpio_num != 17 or tt.pins.ui_in3.gpio_num != 20:
        raise RuntimeError("Standalone requires the validated ETR GPIO mapping")
    if machine is None:
        import machine
    if clock is None:
        import time as clock
    if run is None:
        import board_bridge
        run = board_bridge.main
    fire = machine.Pin(17, machine.Pin.IN, machine.Pin.PULL_DOWN)
    print("RTU standalone: hold physical FIRE to bypass (2 seconds)")
    # Ctrl-C remains enabled throughout this startup escape window.
    for _ in range(100):
        if fire.value():
            print("RTU bypass: normal SDK REPL retained")
            return False
        clock.sleep_ms(20)
    run(require_handshake=True)
    return True
