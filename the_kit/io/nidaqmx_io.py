"""Sorties NI-DAQ (nidaqmx) — port Alba_Eyelink_NiDAQmxVers.py."""

from __future__ import annotations

import math
import time
from typing import Any

_task = None
_cfg: dict[str, Any] | None = None
_dry_run = False


def is_available() -> bool:
    try:
        import nidaqmx  # noqa: F401

        return True
    except ImportError:
        return False


def init_from_config(
    cfg: dict[str, Any] | None,
    *,
    dry_run: bool = False,
) -> tuple[bool, str]:
    """Ouvre une tâche AO persistante (ao0 + ao1 par défaut, style Alba)."""
    global _task, _cfg, _dry_run
    shutdown()
    _dry_run = dry_run
    if not cfg or not cfg.get("enabled", True):
        return False, "disabled"
    if dry_run or cfg.get("simulation_mode", False):
        _cfg = dict(cfg)
        return True, "simulation"
    if not is_available():
        return False, "nidaqmx non installé (uv sync --extra ni)"
    import nidaqmx

    device = str(cfg.get("device", "Dev1"))
    channels = cfg.get("channels") or ["ao0", "ao1"]
    rate = float(cfg.get("rate", 400))
    min_val = float(cfg.get("min_val", -10.0))
    max_val = float(cfg.get("max_val", 10.0))
    try:
        task = nidaqmx.Task()
        for ch in channels:
            physical = ch if "/" in str(ch) else f"{device}/{ch}"
            task.ao_channels.add_ao_voltage_chan(
                physical, min_val=min_val, max_val=max_val
            )
        samps = int(cfg.get("samps_per_chan", max(4000, int(rate * 12))))
        task.timing.cfg_samp_clk_timing(
            rate=rate,
            sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
            samps_per_chan=samps,
        )
        _task = task
        _cfg = dict(cfg)
        return True, "ok"
    except Exception as exc:
        shutdown()
        return False, str(exc)


def shutdown() -> None:
    global _task, _cfg, _dry_run
    if _task is not None:
        try:
            _task.stop()
            _task.close()
        except Exception:
            pass
    _task = None
    _cfg = None
    _dry_run = False


def generate_1way_square_wave(
    frequency: float = 0.5,
    duration: float = 2.0,
    amplitude: float = 1.0,
    sampling_rate: float = 400.0,
) -> list[float]:
    """Onde carrée 0 → amplitude (Alba)."""
    n = max(1, int(sampling_rate * duration))
    out: list[float] = []
    for i in range(n):
        t = i / sampling_rate
        sq = amplitude * (math.copysign(1.0, math.sin(2 * math.pi * frequency * t)) + 1.0) / 2.0
        if amplitude < 0:
            sq = -sq
        out.append(sq)
    return out


def _direction_channels(
    square_wave: list[float],
    direction: str,
) -> tuple[list[float], list[float]]:
    d = direction.upper()
    ch0 = list(square_wave)
    ch1 = list(square_wave)
    if d == "PA":
        ch0 = [-v for v in ch0]
        ch1 = [-v for v in ch1]
    elif d == "LATD":
        ch0 = [-v for v in ch0]
    elif d == "LATG":
        ch1 = [-v for v in ch1]
    return ch0, ch1


def generate_trapezoid_ramp(
    amplitude: float,
    *,
    rise_s: float = 3.0,
    plateau_s: float = 4.0,
    fall_s: float = 3.0,
    sampling_rate: float = 400.0,
    shuffle: bool = False,
    rng: Any = None,
) -> list[float]:
    """Rampe trapézoïdale 3+4+3 s (montée, plateau, descente)."""
    rate = sampling_rate
    n_rise = max(1, int(rise_s * rate))
    n_plat = max(1, int(plateau_s * rate))
    n_fall = max(1, int(fall_s * rate))
    rise = [amplitude * i / (n_rise - 1) if n_rise > 1 else amplitude for i in range(n_rise)]
    plat = [amplitude] * n_plat
    fall = [
        amplitude * (1.0 - i / (n_fall - 1)) if n_fall > 1 else 0.0
        for i in range(n_fall)
    ]
    wave = rise + plat + fall
    if shuffle:
        import random

        r = rng if rng is not None else random
        r.shuffle(wave)
    return wave


def _write_waveform_to_task(
    ch0: list[float],
    ch1: list[float],
    *,
    rate: float,
    dry_run: bool,
) -> float:
    """Écrit le waveform sur la tâche AO. Retourne la durée (s)."""
    duration_s = len(ch0) / rate
    if dry_run or _task is None:
        print(
            f"[ni-dry-run] ramp {len(ch0)} samples "
            f"dur={duration_s:.2f}s rate={rate}"
        )
        time.sleep(min(duration_s, 0.05) if dry_run else duration_s)
        return duration_s

    n = len(ch0)
    _task.timing.cfg_samp_clk_timing(
        rate=rate,
        sample_mode=__import__("nidaqmx").constants.AcquisitionType.FINITE,
        samps_per_chan=n,
    )
    data = [ch0, ch1]
    if len(_task.ao_channels.channel_names) == 1:
        data = [ch0]
    _task.write(data, auto_start=True)
    _task.wait_until_done(timeout=duration_s + 10.0)
    _task.stop()
    return duration_s


def send_ramp_stim(
    *,
    direction: str,
    amplitude: float = 1.0,
    rise_s: float = 3.0,
    plateau_s: float = 4.0,
    fall_s: float = 3.0,
    sampling_rate: float | None = None,
    shuffle: bool = False,
    dry_run: bool | None = None,
) -> dict[str, Any]:
    """
    Rampe galvanique NeuroConn (Alba).
    direction: AP, PA, LATD, LATG ; CONTROL => shuffle=True automatique.
    """
    d = direction.upper()
    rate = float(sampling_rate or (_cfg or {}).get("rate", 400))
    use_dry = _dry_run if dry_run is None else dry_run
    do_shuffle = shuffle or d == "CONTROL"
    wave = generate_trapezoid_ramp(
        amplitude,
        rise_s=rise_s,
        plateau_s=plateau_s,
        fall_s=fall_s,
        sampling_rate=rate,
        shuffle=do_shuffle,
    )
    stim_dir = "AP" if d == "CONTROL" else d
    ch0, ch1 = _direction_channels(wave, stim_dir)

    duration_s = _write_waveform_to_task(ch0, ch1, rate=rate, dry_run=use_dry)
    return {
        "direction": d,
        "stim_direction": stim_dir,
        "amplitude": amplitude,
        "rise_s": rise_s,
        "plateau_s": plateau_s,
        "fall_s": fall_s,
        "duration_s": duration_s,
        "rate": rate,
        "shuffled": do_shuffle,
        "dry_run": use_dry,
    }


def send_square_wave_stim(
    *,
    direction: str = "AP",
    amplitude: float = 1.0,
    frequency: float = 0.278,
    duration_s: float = 3.6,
    sampling_rate: float | None = None,
    dry_run: bool | None = None,
) -> dict[str, Any]:
    """
    Envoie l'onde carrée bidirectionnelle sur AO0/AO1 (manip Alba).
    Directions : AP, PA, LATD, LATG.
    """
    rate = float(sampling_rate or (_cfg or {}).get("rate", 400))
    use_dry = _dry_run if dry_run is None else dry_run
    wave = generate_1way_square_wave(frequency, duration_s, amplitude, rate)
    ch0, ch1 = _direction_channels(wave, direction)

    meta = {
        "direction": direction.upper(),
        "amplitude": amplitude,
        "frequency": frequency,
        "duration_s": duration_s,
        "rate": rate,
        "dry_run": use_dry,
    }

    if use_dry or _task is None:
        print(
            f"[ni-dry-run] square_wave {direction} amp={amplitude} "
            f"dur={duration_s}s rate={rate}"
        )
        time.sleep(min(duration_s, 0.05) if use_dry else duration_s)
        return meta

    n = len(ch0)
    _task.timing.cfg_samp_clk_timing(
        rate=rate,
        sample_mode=__import__("nidaqmx").constants.AcquisitionType.FINITE,
        samps_per_chan=n,
    )
    data = [ch0, ch1]
    if len(_task.ao_channels.channel_names) == 1:
        data = [ch0]
    _task.write(data, auto_start=True)
    _task.wait_until_done(timeout=duration_s + 5.0)
    _task.stop()
    return meta


def send_voltage_pulse(
    channel_index: int,
    voltage: float,
    *,
    duration_s: float = 0.1,
    dry_run: bool | None = None,
) -> None:
    """Pulse scalaire court sur un canal AO (debug / TTL analogique)."""
    use_dry = _dry_run if dry_run is None else dry_run
    if use_dry or _task is None:
        print(f"[ni-dry-run] scalar ch{channel_index}={voltage}V {duration_s}s")
        return
    n = max(2, int((_cfg or {}).get("rate", 400) * duration_s))
    samples = [float(voltage)] * n
    if channel_index == 0:
        data = [samples]
        if len(_task.ao_channels.channel_names) > 1:
            data = [samples, [0.0] * n]
    else:
        data = [[0.0] * n, samples]
    _task.write(data, auto_start=True)
    _task.wait_until_done(timeout=duration_s + 2.0)
    _task.stop()
