"""Marqueurs LSL GVS — codes NIRS 1–8 (aligné NIRS_Test / config.json)."""

from __future__ import annotations

from the_kit.io import lsl

# Convention labo NIRS (P1-P9 NIRS_Test) :
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
    "LATG": 4,  # gauche
    "LATD": 5,  # droite
    "CONTROL": 6,
}

GVS_BASELINE = 1
GVS_ITI = 7
GVS_RESPONSE = 8
GVS_BLOCK_START = 1
GVS_BLOCK_END = 1


def push(code: int | float, *, label: str = "") -> bool:
    """Envoie un trigger LSL et l'affiche toujours en console."""
    value = int(code)
    ok = lsl.push_marker(float(value), label=label)
    if ok:
        print(f"🎯 LSL Trigger {value} ({label})")
    else:
        print(f"🔘 [SIMULATION] Trigger {value} ({label})")
    return ok


def trial_start(condition: str, *, trial_index: int) -> None:
    """Début d'essai — même code que la condition (comme NIRS_Test)."""
    code = GVS_CONDITION_CODES.get(condition.upper(), GVS_BASELINE)
    push(code, label=f"trial_start_{condition}_{trial_index}")


def stim_onset(condition: str) -> None:
    code = GVS_CONDITION_CODES.get(condition.upper(), GVS_BASELINE)
    push(code, label=f"stim_onset_{condition}")


def baseline_start() -> None:
    push(GVS_BASELINE, label="baseline_start")


def baseline_end() -> None:
    push(GVS_BASELINE, label="baseline_end")


def stim_offset(condition: str) -> None:
    """Fin stim — même code condition (comme NIRS_Test)."""
    code = GVS_CONDITION_CODES.get(condition.upper(), GVS_BASELINE)
    push(code, label=f"stim_offset_{condition}")


def response_perceived(direction: str, *, correct: bool | None = None) -> None:
    suffix = ""
    if correct is True:
        suffix = "_correct"
    elif correct is False:
        suffix = "_incorrect"
    push(GVS_RESPONSE, label=f"response_{direction}{suffix}")


def iti_start(duration_s: float) -> None:
    push(GVS_ITI, label=f"iti_{duration_s:.2f}s")
