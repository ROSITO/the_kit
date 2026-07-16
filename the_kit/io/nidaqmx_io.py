"""Sorties NI-DAQ (nidaqmx) — aligné Alba_Eyelink_NiDAQmxVers.py → NeuroConn."""

from __future__ import annotations

import math
import time
from typing import Any

_task = None
_cfg: dict[str, Any] | None = None
_dry_run = False
_status = "uninitialized"


def is_available() -> bool:
    try:
        import nidaqmx  # noqa: F401

        return True
    except ImportError:
        return False


def status() -> str:
    return _status


def init_from_config(
    cfg: dict[str, Any] | None,
    *,
    dry_run: bool = False,
) -> tuple[bool, str]:
    """
    Connexion carte NI (AO0 + AO1), comme ``connect_to_NI`` d'Alba.

    - ``simulation_mode: true`` ou ``--dry-run`` → pas d'écriture hardware
    - sinon ouvre ``Dev1/ao0`` + ``Dev1/ao1`` (rate 400 Hz)
    """
    global _task, _cfg, _dry_run, _status
    shutdown()
    _dry_run = dry_run
    if not cfg or not cfg.get("enabled", True):
        _status = "disabled"
        print("NI-DAQ : disabled (pas de section ni_daq / enabled=false)")
        return False, "disabled"

    if dry_run or cfg.get("simulation_mode", False):
        _cfg = dict(cfg)
        _status = "simulation"
        reason = "--dry-run" if dry_run else "simulation_mode=true"
        print(f"NI-DAQ : SIMULATION ({reason}) — aucune tension sur la carte")
        return True, "simulation"

    if not is_available():
        _status = "missing_nidaqmx"
        print("NI-DAQ : nidaqmx non installé (pip install nidaqmx)")
        return False, "nidaqmx non installé"

    ok, msg = _open_task(cfg)
    if ok:
        _cfg = dict(cfg)
        _status = "connected"
        print(f"NI-DAQ : connecté — {msg}")
        return True, "ok"
    _status = f"error:{msg}"
    print(f"NI-DAQ : ÉCHEC connexion — {msg}")
    return False, msg


def _open_task(cfg: dict[str, Any]) -> tuple[bool, str]:
    """Équivalent Alba ``connect_to_NI(simulation_mode=False)``."""
    global _task
    import nidaqmx

    device = str(cfg.get("device", "Dev1"))
    channels = cfg.get("channels") or ["ao0", "ao1"]
    rate = float(cfg.get("rate", 400))
    min_val = float(cfg.get("min_val", -10.0))
    max_val = float(cfg.get("max_val", 10.0))
    # Alba : samps_per_chan=800 au connect ; on recalcule avant chaque write
    samps = int(cfg.get("samps_per_chan", 800))
    try:
        task = nidaqmx.Task()
        names = []
        for ch in channels:
            physical = ch if "/" in str(ch) else f"{device}/{ch}"
            task.ao_channels.add_ao_voltage_chan(
                physical, min_val=min_val, max_val=max_val
            )
            names.append(physical)
        task.timing.cfg_samp_clk_timing(
            rate=rate,
            sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
            samps_per_chan=samps,
        )
        _task = task
        return True, f"{', '.join(names)} @ {rate} Hz"
    except Exception as exc:
        _close_task_only()
        return False, str(exc)


def _close_task_only() -> None:
    global _task
    if _task is not None:
        try:
            _task.stop()
        except Exception:
            pass
        try:
            _task.close()
        except Exception:
            pass
    _task = None


def shutdown() -> None:
    global _task, _cfg, _dry_run, _status
    _close_task_only()
    _cfg = None
    _dry_run = False
    _status = "shutdown"


def generate_1way_square_wave(
    frequency: float = 0.5,
    duration: float = 2.0,
    amplitude: float = 1.0,
    sampling_rate: float = 400.0,
) -> list[float]:
    """Onde carrée 0 → amplitude (Alba ``generate_1way_square_wave``)."""
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
    """Mapping AO0/AO1 comme Alba ``send_sin_wave_to_NI``."""
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
    # AP / CONTROL : ch0 = ch1 = wave
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
    """Rampe 3+4+3 s (protocole GVS The Kit — pas dans Alba historique)."""
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


def _ao_matrix(ch0: list[float], ch1: list[float]):
    """Matrice (2, N) comme Alba ``ao_data = np.zeros((2, len(...)))``."""
    try:
        import numpy as np

        return np.asarray([ch0, ch1], dtype=float)
    except ImportError:
        return [ch0, ch1]


def _write_waveform_to_task(
    ch0: list[float],
    ch1: list[float],
    *,
    rate: float,
    dry_run: bool,
    label: str = "stim",
) -> float:
    """
    Écriture Alba-like : reconfigure FINITE sur N samples, ``task.write(..., auto_start=True)``,
    attend, ``task.stop()``.
    """
    duration_s = len(ch0) / rate
    if dry_run or _status == "simulation" or _task is None:
        print(
            f"[ni-sim] {label} {len(ch0)} samples "
            f"dur={duration_s:.2f}s rate={rate} status={_status}"
        )
        # En sim : attendre la durée réelle pour caler la tâche / NIRS
        time.sleep(duration_s if not dry_run else min(duration_s, 0.05))
        return duration_s

    import nidaqmx

    n = len(ch0)
    ao_data = _ao_matrix(ch0, ch1)
    try:
        # Recréer le timing pour N samples (Alba fixait 800 ; on adapte à la rampe)
        _task.stop()
    except Exception:
        pass
    try:
        _task.timing.cfg_samp_clk_timing(
            rate=rate,
            sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
            samps_per_chan=n,
        )
    except Exception:
        # Certaines cartes : il faut recréer la tâche après stop
        cfg = _cfg or {}
        _close_task_only()
        ok, msg = _open_task({**cfg, "samps_per_chan": n, "rate": rate})
        if not ok:
            raise RuntimeError(f"NI re-open failed: {msg}")

    print(
        f"NI write {label}: N={n} dur={duration_s:.2f}s "
        f"amp≈{max(abs(v) for v in ch0):.3f}V → carte"
    )
    _task.write(ao_data, auto_start=True)
    # Alba utilise sleep(duration) ; wait_until_done est plus précis
    try:
        _task.wait_until_done(timeout=duration_s + 10.0)
    except Exception:
        time.sleep(duration_s)
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
    """Rampe GVS NeuroConn (directions Alba AP/PA/LATD/LATG + CONTROL)."""
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

    duration_s = _write_waveform_to_task(
        ch0, ch1, rate=rate, dry_run=use_dry, label=f"ramp_{d}"
    )
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
        "ni_status": _status,
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
    """Onde carrée Alba (``send_sin_wave_to_NI`` malgré le nom)."""
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
        "ni_status": _status,
    }
    _write_waveform_to_task(
        ch0, ch1, rate=rate, dry_run=use_dry, label=f"square_{direction}"
    )
    return meta


def send_voltage_pulse(
    channel_index: int,
    voltage: float,
    *,
    duration_s: float = 0.1,
    dry_run: bool | None = None,
) -> None:
    """Pulse scalaire court (debug)."""
    use_dry = _dry_run if dry_run is None else dry_run
    rate = float((_cfg or {}).get("rate", 400))
    n = max(2, int(rate * duration_s))
    samples = [float(voltage)] * n
    zeros = [0.0] * n
    if channel_index == 0:
        ch0, ch1 = samples, zeros
    else:
        ch0, ch1 = zeros, samples
    _write_waveform_to_task(
        ch0, ch1, rate=rate, dry_run=use_dry, label=f"pulse_ch{channel_index}"
    )
