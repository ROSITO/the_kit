"""Export CSV un essai / ligne."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from the_kit.manips.extrapolation.constants import TRIAL_CSV_COLUMNS


def init_trials_csv(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=TRIAL_CSV_COLUMNS).writeheader()


def append_trial_row(path: Path, row: dict[str, Any]) -> None:
    out = {k: row.get(k, "") for k in TRIAL_CSV_COLUMNS}
    stim = out.get("stim_params_json")
    if isinstance(stim, dict):
        out["stim_params_json"] = json.dumps(stim, ensure_ascii=False)
    with path.open("a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=TRIAL_CSV_COLUMNS).writerow(out)
