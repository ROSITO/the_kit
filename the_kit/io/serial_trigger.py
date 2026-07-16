from __future__ import annotations

import time


def send_serial_trigger(port: str, value: int, *, dry_run: bool = False) -> None:
    if dry_run:
        print(f"[dry-run] trigger port={port} value={value}")
        return
    import serial

    ser = serial.Serial(port, 115200, timeout=1)
    try:
        time.sleep(0.5)
        ser.write(bytes([int(value) & 0xFF]))
        print(f"Trigger {value} envoyé sur {port}")
    finally:
        ser.close()
