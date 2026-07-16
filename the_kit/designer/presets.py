from __future__ import annotations

import json
from pathlib import Path

PRESETS_DIR = Path(__file__).resolve().parents[2] / "examples" / "presets"


def list_presets() -> list[str]:
    if not PRESETS_DIR.exists():
        return []
    return sorted(p.stem for p in PRESETS_DIR.glob("*.json"))


def load_preset(name: str) -> dict:
    path = PRESETS_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Preset introuvable: {name}")
    with path.open(encoding="utf-8") as f:
        return json.load(f)
