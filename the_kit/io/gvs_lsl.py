"""Marqueurs LSL GVS — codes par défaut NIRS 1–8, surchargeables dans le protocole."""

from __future__ import annotations

from typing import Any

from the_kit.io import lsl

# Convention labo NIRS (P1-P9 NIRS_Test) — défauts si le protocole n'en déclare pas.
#   1 = baseline / début bloc
#   2 = avant (AP)
#   3 = arrière (PA)
#   4 = gauche (LATG)
#   5 = droite (LATD)
#   6 = contrôle
#   7 = inter-stimulus (ITI)
#   8 = réponse
GVS_CONDITION_CODES: dict[str, int] = {
    "AP": 2,
    "PA": 3,
    "LATG": 4,
    "LATD": 5,
    "CONTROL": 6,
}

GVS_BASELINE = 1
GVS_ITI = 7
GVS_RESPONSE = 8
GVS_BLOCK_START = 1
GVS_BLOCK_END = 1

DEFAULT_TRIGGER_WHY = {
    "block_start": "Debut bloc GVS",
    "block_end": "Fin bloc GVS",
    "aborted": "Bloc interrompu",
    "baseline_start": "Debut baseline",
    "baseline_end": "Fin baseline",
    "stim_onset": {
        "AP": "Onset stim avant (AP)",
        "PA": "Onset stim arriere (PA)",
        "LATG": "Onset stim gauche (LATG)",
        "LATD": "Onset stim droite (LATD)",
        "CONTROL": "Onset stim controle",
    },
    "stim_offset": {
        "AP": "Offset stim avant (AP)",
        "PA": "Offset stim arriere (PA)",
        "LATG": "Offset stim gauche (LATG)",
        "LATD": "Offset stim droite (LATD)",
        "CONTROL": "Offset stim controle",
    },
    "response": "Reponse sujet",
    "iti": "Intervalle inter-essai",
}


def push(code: int | float, *, label: str = "") -> bool:
    """Envoie un trigger LSL et l'affiche toujours en console."""
    value = int(code)
    ok = lsl.push_marker(float(value), label=label)
    if ok:
        print(f"[lsl] Trigger {value} ({label})")
    else:
        print(f"[lsl] [SIMULATION] Trigger {value} ({label})")
    return ok


def _as_code(raw: Any) -> int | None:
    if raw is None or raw is False:
        return None
    if isinstance(raw, bool):
        return None
    return int(raw)


def _normalize_entry(
    raw: Any,
    *,
    default_code: int | None,
    default_why: str,
    present: bool,
) -> dict[str, Any]:
    """Accepte ``8``, ``{"code": 8, "why": "..."}`` ou ``null`` (pas d'envoi)."""
    if not present:
        return {"code": default_code, "why": default_why}
    if raw is None:
        return {"code": None, "why": default_why}
    if isinstance(raw, (int, float)):
        return {"code": int(raw), "why": default_why}
    if not isinstance(raw, dict):
        raise ValueError(f"trigger invalide (attendu int ou objet): {raw!r}")
    if "code" not in raw:
        code = default_code
    else:
        code = _as_code(raw.get("code"))
    why = raw.get("why") or raw.get("label") or default_why
    return {"code": code, "why": str(why)}


def _default_condition_map(stage: str) -> dict[str, dict[str, Any]]:
    if stage == "stim_onset":
        why = DEFAULT_TRIGGER_WHY["stim_onset"]
        return {
            cond: {"code": code, "why": why[cond]}
            for cond, code in GVS_CONDITION_CODES.items()
        }
    if stage == "stim_offset":
        # Désactivé par défaut (The Kit n'envoyait pas d'offset) — activer dans le JSON.
        why = DEFAULT_TRIGGER_WHY["stim_offset"]
        return {cond: {"code": None, "why": why[cond]} for cond in GVS_CONDITION_CODES}
    return {}


class TriggerTable:
    """Table de triggers d'un nœud GVS — codes + motif (why), surcharge JSON."""

    STAGES = (
        "block_start",
        "block_end",
        "aborted",
        "baseline_start",
        "baseline_end",
        "response",
        "iti",
    )
    CONDITION_STAGES = ("stim_onset", "stim_offset")

    def __init__(self, raw: dict[str, Any] | None = None) -> None:
        src = raw if isinstance(raw, dict) else {}
        self.simple: dict[str, dict[str, Any]] = {}
        simple_defaults = {
            "block_start": (GVS_BLOCK_START, DEFAULT_TRIGGER_WHY["block_start"]),
            "block_end": (GVS_BLOCK_END, DEFAULT_TRIGGER_WHY["block_end"]),
            "aborted": (GVS_BLOCK_END, DEFAULT_TRIGGER_WHY["aborted"]),
            "baseline_start": (GVS_BASELINE, DEFAULT_TRIGGER_WHY["baseline_start"]),
            "baseline_end": (GVS_BASELINE, DEFAULT_TRIGGER_WHY["baseline_end"]),
            "response": (GVS_RESPONSE, DEFAULT_TRIGGER_WHY["response"]),
            "iti": (GVS_ITI, DEFAULT_TRIGGER_WHY["iti"]),
        }
        for stage, (code, why) in simple_defaults.items():
            self.simple[stage] = _normalize_entry(
                src.get(stage),
                default_code=code,
                default_why=why,
                present=stage in src,
            )
        self.by_condition: dict[str, dict[str, dict[str, Any]]] = {}
        for stage in self.CONDITION_STAGES:
            defaults = _default_condition_map(stage)
            override = src.get(stage)
            merged = dict(defaults)
            if isinstance(override, dict):
                for cond, entry in override.items():
                    key = str(cond).strip().upper()
                    base = defaults.get(key, {"code": None, "why": f"{stage}_{key}"})
                    merged[key] = _normalize_entry(
                        entry,
                        default_code=base["code"],
                        default_why=str(base["why"]),
                        present=True,
                    )
            self.by_condition[stage] = merged

    def resolve(self, stage: str, *, condition: str | None = None) -> tuple[int | None, str]:
        if stage in self.by_condition:
            if not condition:
                return None, stage
            key = condition.upper()
            entry = self.by_condition[stage].get(key)
            if entry is None:
                return None, f"{stage}_{key}"
            return entry["code"], str(entry["why"])
        entry = self.simple.get(stage)
        if entry is None:
            return None, stage
        return entry["code"], str(entry["why"])

    def push(
        self,
        stage: str,
        *,
        condition: str | None = None,
        extra: str = "",
    ) -> tuple[int | None, str]:
        """Envoie le trigger si ``code`` n'est pas null. Retourne (code, why)."""
        code, why = self.resolve(stage, condition=condition)
        if code is None:
            return None, why
        label = why if not extra else f"{why} | {extra}"
        push(code, label=label)
        return code, why

    def as_payload(self) -> dict[str, Any]:
        """Dump JSON-friendly pour session / BIDS."""
        out: dict[str, Any] = {k: dict(v) for k, v in self.simple.items()}
        for stage, mapping in self.by_condition.items():
            out[stage] = {cond: dict(entry) for cond, entry in mapping.items()}
        return out


def load_trigger_table(params: dict[str, Any] | None) -> TriggerTable:
    raw = (params or {}).get("triggers")
    return TriggerTable(raw if isinstance(raw, dict) else None)


def trial_start(condition: str, *, trial_index: int, table: TriggerTable | None = None) -> None:
    """Début d'essai — même code que l'onset stim par défaut."""
    tbl = table or TriggerTable()
    tbl.push("stim_onset", condition=condition, extra=f"trial_start_{trial_index}")


def stim_onset(condition: str, table: TriggerTable | None = None) -> None:
    (table or TriggerTable()).push("stim_onset", condition=condition)


def baseline_start(table: TriggerTable | None = None) -> None:
    (table or TriggerTable()).push("baseline_start")


def baseline_end(table: TriggerTable | None = None) -> None:
    (table or TriggerTable()).push("baseline_end")


def stim_offset(condition: str, table: TriggerTable | None = None) -> None:
    (table or TriggerTable()).push("stim_offset", condition=condition)


def response_perceived(
    direction: str,
    *,
    correct: bool | None = None,
    table: TriggerTable | None = None,
) -> None:
    suffix = direction
    if correct is True:
        suffix += "_correct"
    elif correct is False:
        suffix += "_incorrect"
    (table or TriggerTable()).push("response", extra=suffix)


def iti_start(duration_s: float, table: TriggerTable | None = None) -> None:
    (table or TriggerTable()).push("iti", extra=f"{duration_s:.2f}s")
