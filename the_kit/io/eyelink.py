from __future__ import annotations

from typing import Any

_tracker = None


def is_available() -> bool:
    try:
        import pylink  # noqa: F401

        return True
    except ImportError:
        return False


def connect(*, dummy: bool = True, participant_code: str = "S001"):
    global _tracker
    if not is_available():
        raise RuntimeError("pylink non installé (SR Research EyeLink SDK)")
    import pylink

    _tracker = pylink.EyeLink(None) if dummy else pylink.EyeLink()
    _tracker.openDataFile(f"{participant_code}.edf")
    return _tracker


def setup_screen(tracker, width: int, height: int) -> None:
    tracker.sendCommand(f"screen_pixel_coords = 0 0 {width - 1} {height - 1}")
    tracker.sendCommand(f"screen_phys_coords = 0 0 {width - 1} {height - 1}")


def calibrate_hv5(tracker, width: int, height: int) -> None:
    import pylink

    setup_screen(tracker, width, height)
    pylink.openGraphics((width, height), "rgb")
    tracker.setCalibrationType("HV5")
    tracker.doTrackerSetup()
    pylink.closeGraphics()


def send_message(tracker, text: str) -> None:
    tracker.sendMessage(text)


def send_trigger(tracker, code: int) -> None:
    tracker.sendMessage(f"TRIGGER {int(code)}")


def get_tracker():
    return _tracker


def shutdown(tracker=None) -> None:
    global _tracker
    t = tracker or _tracker
    if t is not None:
        try:
            t.stopRecording()
            t.closeDataFile()
            t.close()
        except Exception:
            pass
    _tracker = None
