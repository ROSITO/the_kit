from __future__ import annotations

from typing import Any

_outlet = None
_cfg: dict[str, Any] | None = None


def is_available() -> bool:
    try:
        import pylsl  # noqa: F401

        return True
    except ImportError:
        return False


def init_from_config(cfg: dict[str, Any] | None) -> tuple[bool, str]:
    global _outlet, _cfg
    if not cfg or not cfg.get("enabled", True):
        _outlet = None
        _cfg = None
        return False, "disabled"
    if not is_available():
        return False, "pylsl non installé (uv pip install pylsl)"
    import pylsl

    fmt_name = str(cfg.get("channel_format", "float32")).lower()
    fmt = pylsl.cf_int32 if "int" in fmt_name else pylsl.cf_float32
    info = pylsl.StreamInfo(
        str(cfg.get("stream_name", "TheKit_Markers")),
        str(cfg.get("stream_type", "Markers")),
        int(cfg.get("channel_count", 1)),
        0,
        fmt,
        str(cfg.get("source_id", "the_kit")),
    )
    _outlet = pylsl.StreamOutlet(info)
    _cfg = dict(cfg)
    return True, "ok"


def auto_markers_enabled() -> bool:
    """Si False, seuls les push_marker explicites (ex. gvs_lsl) partent sur LSL."""
    if not _cfg:
        return False
    return bool(_cfg.get("auto_markers", True))


def push_marker(code: float, *, label: str = "") -> bool:
    if _outlet is None:
        return False
    import pylsl

    use_int = bool(_cfg and "int" in str(_cfg.get("channel_format", "")).lower())
    sample = [int(code)] if use_int else [float(code)]
    _outlet.push_sample(sample, pylsl.local_clock())
    return True


def marker_for_event(event: str, node_id: str | None = None) -> float:
    """Codes simples pour LabRecorder / NIRS."""
    base = {
        "session_start": 1.0,
        "session_end": 99.0,
        "node_start": 10.0,
        "node_end": 11.0,
        "trigger": 20.0,
        "response": 30.0,
        "photosonde_flash": 40.0,
        "video_first_flip": 50.0,
        "audio_actual_start": 51.0,
    }
    return base.get(event, 100.0)


def shutdown() -> None:
    global _outlet, _cfg
    _outlet = None
    _cfg = None
