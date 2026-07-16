"""Lecture audio planifiée via sounddevice (port P1-P9 ScheduledAudioPlayer)."""

from __future__ import annotations

import platform
import time
from pathlib import Path
from typing import Any

import numpy as np
import sounddevice as sd
import soundfile as sf

from the_kit.audio.device_select import choose_device_os_aware, get_hostapi_name


def query_default_output_samplerate(device_index: int | None) -> int | None:
    try:
        if device_index is not None:
            info = sd.query_devices(int(device_index), "output")
        else:
            d = sd.default.device
            if isinstance(d, (list, tuple)) and d[1] is not None and int(d[1]) >= 0:
                info = sd.query_devices(int(d[1]), "output")
            else:
                info = sd.query_devices(kind="output")
        ds = info.get("default_samplerate")
        if ds is not None and float(ds) > 0:
            return int(round(float(ds)))
    except Exception:
        pass
    return None


def resolve_output_stream_samplerate(
    device_idx: int | None, audio_cfg: dict[str, Any]
) -> int | None:
    v = audio_cfg.get("output_sample_rate")
    if v is not None:
        return int(v)
    if platform.system().lower() == "windows":
        ds = query_default_output_samplerate(device_idx)
        if ds is not None:
            return ds
        v = audio_cfg.get("sample_rate")
        if v is not None:
            return int(v)
    return None


def resample_stereo(wave: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    if orig_sr == target_sr:
        return wave.astype(np.float32, copy=False)
    n_out = max(1, int(round(wave.shape[0] * (target_sr / orig_sr))))
    try:
        from scipy import signal

        out = np.empty((n_out, wave.shape[1]), dtype=np.float32)
        for c in range(wave.shape[1]):
            out[:, c] = signal.resample(wave[:, c].astype(np.float64), n_out).astype(np.float32)
        return out
    except ImportError:
        t_old = np.linspace(0.0, 1.0, num=wave.shape[0], endpoint=False, dtype=np.float64)
        t_new = np.linspace(0.0, 1.0, num=n_out, endpoint=False, dtype=np.float64)
        out = np.empty((n_out, wave.shape[1]), dtype=np.float32)
        for c in range(wave.shape[1]):
            out[:, c] = np.interp(t_new, t_old, wave[:, c].astype(np.float64)).astype(np.float32)
        return out


def preload_audio(path: Path, output_sr: int | None) -> tuple[np.ndarray, int]:
    wave, sr = sf.read(str(path), dtype="float32")
    if wave.ndim == 1:
        wave = np.column_stack((wave, wave))
    wave = wave.astype(np.float32)
    sr = int(sr)
    if output_sr is not None and sr != int(output_sr):
        wave = resample_stereo(wave, sr, int(output_sr))
        sr = int(output_sr)
    return wave, sr


def plan_av_onsets(
    offset_ms: float = 0.0,
    scheduling_lead_s: float = 0.3,
    *,
    clock=time.perf_counter,
) -> tuple[float, float, float]:
    now = clock()
    trial_start = now + scheduling_lead_s
    audio_target = trial_start + offset_ms / 1000.0
    return now, trial_start, audio_target


class LowLatencyPlayer:
    """ScheduledAudioPlayer — flux callback persistant."""

    def __init__(self, blocksize: int = 128, device_index: int | None = None):
        self.blocksize = int(blocksize)
        self.device_index = device_index
        self.stream: sd.OutputStream | None = None
        self.sample_rate: int | None = None
        self.channels: int | None = None
        self.state: dict[str, Any] | None = None
        self.audio_actual_start_perf: float | None = None
        self.done = False

    def _callback(self, outdata, frames, _time_info, _status) -> None:
        outdata.fill(0)
        if self.state is None:
            return
        st = self.state
        wave = st["wave"]
        sr = st["sr"]
        target = st["target_start_perf"]
        offset = st["offset"]
        total = st["total"]

        if hasattr(_time_info, "outputBufferDacTime") and hasattr(_time_info, "currentTime"):
            now_perf = time.perf_counter()
            block_start_perf = now_perf + float(
                _time_info.outputBufferDacTime - _time_info.currentTime
            )
        else:
            block_start_perf = time.perf_counter()

        delay_s = target - block_start_perf
        skip = int(np.ceil(delay_s * sr)) if delay_s > 0 else 0
        if skip >= frames:
            return

        write_start = max(0, skip)
        writable = frames - write_start
        remaining = total - offset
        n = min(writable, remaining)
        if n > 0:
            outdata[write_start : write_start + n, :] = wave[offset : offset + n, :]
            st["offset"] = offset + n
            if self.audio_actual_start_perf is None:
                self.audio_actual_start_perf = block_start_perf + (write_start / sr)
        if st["offset"] >= total:
            self.done = True

    def _prepare_stream(self, sample_rate: int, channels: int) -> None:
        if (
            self.stream is not None
            and self.sample_rate == sample_rate
            and self.channels == channels
        ):
            return
        self.stop()
        self.sample_rate = int(sample_rate)
        self.channels = int(channels)
        self.stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            callback=self._callback,
            blocksize=self.blocksize,
            dtype="float32",
            device=self.device_index,
        )
        self.stream.start()

    def schedule_wave(
        self, wave: np.ndarray, sample_rate: int, target_start_perf: float
    ) -> None:
        self._prepare_stream(sample_rate, wave.shape[1])
        self.audio_actual_start_perf = None
        self.done = False
        self.state = {
            "wave": wave.astype(np.float32),
            "sr": float(sample_rate),
            "target_start_perf": float(target_start_perf),
            "offset": 0,
            "total": int(wave.shape[0]),
        }

    def stop(self) -> None:
        self.state = None
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None


def list_output_devices() -> list[dict[str, Any]]:
    devices = sd.query_devices()
    hostapis = sd.query_hostapis()
    out: list[dict[str, Any]] = []
    for i, dev in enumerate(devices):
        if dev.get("max_output_channels", 0) < 1:
            continue
        host_name = get_hostapi_name(int(dev.get("hostapi", -1)))
        out.append(
            {
                "index": i,
                "name": dev.get("name"),
                "hostapi": host_name,
                "default_samplerate": dev.get("default_samplerate"),
            }
        )
    return out


def audio_config_from_protocol(protocol_raw: dict, node: Any) -> dict[str, Any]:
    defaults = protocol_raw.get("audio_defaults") or {}
    node_audio = getattr(node, "raw", {}).get("audio") or node.params.get("audio") or {}
    if isinstance(node_audio, dict):
        merged = {**defaults, **node_audio}
    else:
        merged = dict(defaults)
    for k in ("blocksize", "offset_ms", "scheduling_lead_s", "audio_device_query"):
        if k in node.params and k not in merged:
            merged[k] = node.params[k]
    return merged
