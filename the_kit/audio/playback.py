"""Lecture bloquante de fichiers audio — PortAudio (WASAPI / Core Audio) ou pygame."""

from __future__ import annotations

import platform
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np

FrameCallback = Callable[[], bool]  # retourne True pour interrompre


def is_portaudio_available() -> bool:
    try:
        import sounddevice  # noqa: F401

        return True
    except ImportError:
        return False


def resolve_audio_backend(audio_cfg: dict[str, Any]) -> str:
    """Retourne ``portaudio`` ou ``pygame``."""
    explicit = str(audio_cfg.get("backend", audio_cfg.get("audio_backend", "auto"))).lower()
    if explicit in ("portaudio", "low_latency", "wasapi", "sounddevice"):
        return "portaudio" if is_portaudio_available() else "pygame"
    if explicit == "pygame":
        return "pygame"
    # auto : Windows → WASAPI si dispo ; sinon portaudio partout si installé
    if is_portaudio_available():
        if platform.system().lower() == "windows":
            return "portaudio"
        return "portaudio"
    return "pygame"


def _load_wave(path: Path, output_sr: int | None) -> tuple[np.ndarray, int]:
    from the_kit.audio.low_latency import preload_audio

    return preload_audio(path, output_sr)


def _play_portaudio(
    path: Path,
    audio_cfg: dict[str, Any],
    *,
    on_frame: FrameCallback | None = None,
) -> dict[str, Any]:
    import sounddevice as sd

    from the_kit.audio.device_select import choose_device_os_aware
    from the_kit.audio.low_latency import resolve_output_stream_samplerate

    device_idx, hostapi = choose_device_os_aware(audio_cfg)
    stream_sr = resolve_output_stream_samplerate(device_idx, audio_cfg)
    wave, sr = _load_wave(path, stream_sr)

    sd.play(wave, samplerate=sr, device=device_idx)
    aborted = False
    while True:
        stream = sd.get_stream()
        if stream is None or not stream.active:
            break
        if on_frame and on_frame():
            sd.stop()
            aborted = True
            break
        time.sleep(0.005)

    meta = {
        "backend": "portaudio",
        "audio_hostapi": hostapi,
        "device_index": device_idx,
        "sample_rate": sr,
        "duration_s": len(wave) / sr,
        "aborted": aborted,
    }
    if "wasapi" in hostapi.lower():
        print(f"🔊 WASAPI — {path.name} ({meta['duration_s']:.2f}s)")
    else:
        print(f"🔊 {hostapi} — {path.name} ({meta['duration_s']:.2f}s)")
    return meta


def _play_pygame(
    path: Path,
    *,
    on_frame: FrameCallback | None = None,
) -> dict[str, Any]:
    import pygame

    if not pygame.mixer.get_init():
        pygame.mixer.init()
    pygame.mixer.music.load(str(path))
    pygame.mixer.music.play()
    aborted = False
    while pygame.mixer.music.get_busy():
        if on_frame and on_frame():
            pygame.mixer.music.stop()
            aborted = True
            break
        time.sleep(0.005)
    pygame.mixer.music.stop()
    print(f"🔊 pygame.mixer — {path.name}")
    return {"backend": "pygame", "aborted": aborted}


def play_cue_file(
    path: Path,
    audio_cfg: dict[str, Any] | None = None,
    *,
    on_frame: FrameCallback | None = None,
) -> dict[str, Any]:
    """
    Joue un fichier audio (WAV/MP3/FLAC…) en bloquant jusqu'à la fin.

    Sous Windows, ``backend: auto`` utilise PortAudio → WASAPI si ``sounddevice``
    est installé (``uv sync --extra lowlatency``).
    """
    if not path.is_file():
        print(f"⚠ audio manquant : {path}")
        return {"backend": "none", "aborted": False, "missing": True}

    cfg = dict(audio_cfg or {})
    backend = resolve_audio_backend(cfg)
    if backend == "portaudio":
        try:
            return _play_portaudio(path, cfg, on_frame=on_frame)
        except Exception as exc:
            print(f"⚠ PortAudio ({path.name}) : {exc} — repli pygame.mixer")
    return _play_pygame(path, on_frame=on_frame)


def audio_config_from_session(session: Any, node: Any) -> dict[str, Any]:
    """Fusionne ``audio_defaults`` protocole + ``params.audio`` nœud."""
    from the_kit.audio.low_latency import audio_config_from_protocol

    return audio_config_from_protocol(session.protocol.raw, node)
