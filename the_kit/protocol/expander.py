from __future__ import annotations

import random
from copy import deepcopy
from typing import Any

from the_kit.protocol.counterbalance import (
    apply_latin_square_to_trials,
    parse_counterbalance_config,
)


def _iti_duration_s(timing: dict[str, Any], rng: random.Random) -> float:
    iti = timing.get("iti_jitter_s") or timing.get("iti_s")
    if iti is None:
        return 0.0
    if isinstance(iti, (int, float)):
        return float(iti)
    if isinstance(iti, list) and len(iti) >= 2:
        return rng.uniform(float(iti[0]), float(iti[1]))
    if isinstance(iti, list) and len(iti) == 1:
        return float(iti[0])
    return 0.5


def _trial_nodes_from_condition(
    cond: dict[str, Any],
    *,
    defaults: dict[str, Any],
    index: int,
) -> list[dict[str, Any]]:
    """Construit les nœuds d'un essai à partir d'une condition."""
    cid = cond.get("id", f"trial_{index:03d}")
    nodes: list[dict[str, Any]] = []

    if cond.get("video") and cond.get("audio"):
        nodes.append(
            {
                "id": cid,
                "type": "av_sync",
                "engine": "psychopy",
                "timing_mode": cond.get("timing_mode", "low_latency"),
                "params": {
                    "video": cond["video"],
                    "audio": cond["audio"],
                    "stimulus_duration_s": cond.get(
                        "stimulus_duration_s",
                        defaults.get("stimulus_duration_s", 2.0),
                    ),
                    "label": cond.get("label", cid),
                    "offset_ms": cond.get("offset_ms"),
                },
            }
        )
    elif cond.get("video"):
        nodes.append(
            {
                "id": f"{cid}_video",
                "type": "video",
                "engine": "qt",
                "params": {
                    "file": cond["video"],
                    "duration_s": cond.get(
                        "stimulus_duration_s", defaults.get("stimulus_duration_s", 30)
                    ),
                },
            }
        )
    elif cond.get("type"):
        n = deepcopy(cond)
        n.setdefault("id", cid)
        n.setdefault("engine", TYPE_DEFAULT_ENGINE.get(n["type"], "qt"))
        nodes.append(n)
    return nodes


TYPE_DEFAULT_ENGINE = {
    "av_sync": "psychopy",
    "video": "qt",
    "optic_flow": "pygame",
    "questionnaire": "qt",
    "delay": "qt",
    "blank": "psychopy",
    "photosonde_square": "psychopy",
}


def expand_conditions(
    data: dict[str, Any],
    *,
    subject_group: str | None = None,
    subject_id: str | None = None,
    subject_number: int | None = None,
) -> dict[str, Any]:
    """
    Déploie `conditions[]` en `nodes[]` (essais × répétitions, shuffle, ITI).
    Si `nodes` est déjà non vide, retourne data inchangé.
    """
    conditions = data.get("conditions") or []
    if not conditions:
        return data
    if data.get("nodes"):
        return data

    presentation = data.get("presentation") or {}
    timing = data.get("timing") or {}
    defaults = data.get("defaults") or {}
    reps_default = int(defaults.get("condition_repetitions", 1))

    seed = presentation.get("random_seed")
    rng = random.Random(seed) if seed is not None else random.Random()

    trials: list[dict[str, Any]] = []
    for cond in conditions:
        groups = cond.get("groups")
        if groups and subject_group and subject_group not in groups:
            continue
        reps = int(cond.get("repetitions", reps_default))
        for _ in range(reps):
            trials.append(deepcopy(cond))

    cb_cfg = parse_counterbalance_config(
        presentation.get("counterbalance") or data.get("counterbalance")
    )
    if cb_cfg and len(trials) > 1:
        grid = cb_cfg.get("grid")
        trials = apply_latin_square_to_trials(
            trials,
            subject_id=subject_id or "anonymous",
            subject_number=subject_number
            if subject_number is not None
            else cb_cfg.get("subject_number"),
            grid=grid,
        )
        out_cb = {
            "method": "latin_square",
            "subject_id": subject_id,
            "order": [t.get("id", i) for i, t in enumerate(trials)],
        }
    else:
        out_cb = None

    if presentation.get("randomize_trials", True) and not cb_cfg:
        rng.shuffle(trials)

    nodes: list[dict[str, Any]] = []

    if data.get("consent"):
        c = data["consent"]
        nodes.append(
            {
                "id": "consent",
                "type": "consent",
                "engine": "qt",
                "params": {
                    "text": c if isinstance(c, str) else c.get("text", ""),
                    "file": c.get("file") if isinstance(c, dict) else None,
                    "key": c.get("key", "space") if isinstance(c, dict) else "space",
                },
            }
        )

    instr = data.get("instructions")
    if instr:
        text = instr if isinstance(instr, str) else instr.get("text", "")
        nodes.append(
            {
                "id": "instructions",
                "type": "instructions",
                "engine": "qt",
                "params": {"text": text, "duration_s": 30, "key": "space"},
            }
        )

    for i, cond in enumerate(trials):
        nodes.extend(_trial_nodes_from_condition(cond, defaults=defaults, index=i))
        iti_s = _iti_duration_s(timing, rng)
        if iti_s > 0:
            nodes.append(
                {
                    "id": f"iti_{i:03d}",
                    "type": "delay",
                    "engine": "qt",
                    "params": {"duration_s": iti_s},
                }
            )

    if data.get("debrief"):
        d = data["debrief"]
        nodes.append(
            {
                "id": "debrief",
                "type": "debrief",
                "engine": "qt",
                "params": {
                    "text": d if isinstance(d, str) else d.get("text", ""),
                    "file": d.get("file") if isinstance(d, dict) else None,
                },
            }
        )

    out = deepcopy(data)
    out["nodes"] = nodes
    out["_expanded_from_conditions"] = True
    if out_cb is not None:
        out["_counterbalance"] = out_cb
    return out
