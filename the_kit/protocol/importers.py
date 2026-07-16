from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from the_kit.protocol.expander import expand_conditions


def import_p19_config(path: str | Path, *, name: str | None = None) -> dict[str, Any]:
    """
    Convertit un config.json manip_psychophysique_json (P1-P9) en protocole The Kit v1.
    """
    path = Path(path).resolve()
    with path.open(encoding="utf-8") as f:
        cfg = json.load(f)

    protocol: dict[str, Any] = {
        "protocol_version": "1.0",
        "name": name or path.stem,
        "loop": 1,
        "subject": cfg.get("subject", {}),
        "display": cfg.get("display", {}),
        "audio_defaults": cfg.get("audio", {}),
        "timing": cfg.get("timing", {}),
        "presentation": cfg.get("presentation", {}),
        "defaults": cfg.get("defaults", {}),
        "conditions": [],
        "instructions": cfg.get("instructions"),
    }

    for cond in cfg.get("conditions", []):
        protocol["conditions"].append(
            {
                "id": cond.get("id", cond.get("label", "cond")),
                "label": cond.get("label"),
                "video": cond.get("video"),
                "audio": cond.get("audio"),
                "repetitions": cond.get("repetitions"),
                "stimulus_duration_s": cond.get(
                    "stimulus_duration_s", cfg.get("defaults", {}).get("stimulus_duration_s")
                ),
            }
        )

    return expand_conditions(protocol, subject_group=protocol["subject"].get("group"))


def import_randomflow_config(path: str | Path) -> dict[str, Any]:
    """Convertit config randomflow (liste configs) en protocole avec un nœud optic_flow."""
    path = Path(path).resolve()
    with path.open(encoding="utf-8") as f:
        cfg = json.load(f)

    configs = cfg.get("configs", [cfg])
    nodes = [
        {
            "id": "flow_session",
            "type": "optic_flow",
            "engine": "pygame",
            "params": {
                **configs[0],
                "duration_s": cfg.get("duration_s", 10),
                "key_noise": cfg.get("key_noise", "b"),
                "key_motion": cfg.get("key_motion", "m"),
            },
        }
    ]
    return {
        "protocol_version": "1.0",
        "name": path.stem,
        "loop": int(cfg.get("loop", 1)),
        "nodes": nodes,
    }
