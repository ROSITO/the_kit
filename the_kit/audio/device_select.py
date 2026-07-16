"""Sélection périphérique PortAudio (WASAPI / Core Audio / ALSA)."""

from __future__ import annotations

import platform
from typing import Any

import sounddevice as sd


def get_hostapi_name(host_idx: int) -> str:
    try:
        hostapis = sd.query_hostapis()
        if 0 <= host_idx < len(hostapis):
            return str(hostapis[host_idx].get("name", "unknown"))
    except Exception:
        pass
    return "unknown"


def choose_device_os_aware(cfg: dict[str, Any]) -> tuple[int | None, str]:
    idx = cfg.get("audio_device_index")
    if idx is not None:
        chosen = int(idx)
        try:
            dev = sd.query_devices(chosen)
            return chosen, get_hostapi_name(int(dev.get("hostapi", -1)))
        except Exception:
            return chosen, "unknown"

    devices = sd.query_devices()
    hostapis = sd.query_hostapis()
    output_devices: list[tuple[int, dict, str]] = []
    for i, dev in enumerate(devices):
        if dev.get("max_output_channels", 0) >= 1:
            output_devices.append(
                (i, dev, str(hostapis[dev.get("hostapi", 0)].get("name", "")))
            )

    query = str(cfg.get("audio_device_query", "")).strip().lower()
    if query:
        for i, dev, host_name in output_devices:
            label = f"{dev.get('name', '')} {host_name}".lower()
            if query in label:
                return i, host_name

    os_name = platform.system().lower()
    if os_name == "darwin":
        preferred = ["core audio"]
    elif os_name == "windows":
        preferred = ["wasapi", "wdm-ks", "mme", "directsound"]
    elif os_name == "linux":
        preferred = ["jack", "alsa", "pulse"]
    else:
        preferred = []

    for host_pref in preferred:
        for h_idx, host in enumerate(hostapis):
            host_name = str(host.get("name", ""))
            if host_pref in host_name.lower():
                default_out = int(host.get("default_output_device", -1))
                if default_out >= 0:
                    return default_out, host_name
                for i, dev, hname in output_devices:
                    if int(dev.get("hostapi", -1)) == h_idx:
                        return i, hname

    try:
        default_out = sd.default.device[1] if isinstance(sd.default.device, (list, tuple)) else None
        if default_out is not None and int(default_out) >= 0:
            dev = sd.query_devices(int(default_out))
            return int(default_out), get_hostapi_name(int(dev.get("hostapi", -1)))
    except Exception:
        pass

    if output_devices:
        return output_devices[0][0], output_devices[0][2]
    return None, "unknown"
