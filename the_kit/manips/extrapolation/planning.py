"""Planification des essais labo et chirurgie."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from the_kit.manips.extrapolation.constants import DEFAULT_DELTA_TIMES_S, NOMINAL_MASK_S

Modality = Literal["time", "chrono", "tone"]


@dataclass
class TrialSpec:
    trial_index: int
    delta_time_s: float
    mask_duration_s: float
    zone: int | None = None
    repetition: int | None = None
    kind: str | None = None  # "court" | "long" | None (lab)
    secondary_option: int = 0

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_lab_trials(
    *,
    delta_times_s: list[float] | tuple[float, ...] | None = None,
    trials_per_condition: int = 1,
    secondary_option: int = 0,
    mask_duration_s: float | None = None,
    modality: Modality = "time",
) -> list[TrialSpec]:
    """8 DeltaTime × N essais. Time: mask=DeltaTime ; Chrono/Tone: mask fixe 1.5 s."""
    deltas = list(delta_times_s) if delta_times_s is not None else list(DEFAULT_DELTA_TIMES_S)
    n = max(1, int(trials_per_condition))
    opt = int(secondary_option)
    trials: list[TrialSpec] = []
    idx = 0
    for _rep in range(n):
        for dt in deltas:
            idx += 1
            if modality == "time":
                mask = float(dt)
            else:
                mask = float(mask_duration_s if mask_duration_s is not None else NOMINAL_MASK_S)
            trials.append(
                TrialSpec(
                    trial_index=idx,
                    delta_time_s=float(dt),
                    mask_duration_s=mask,
                    secondary_option=opt,
                )
            )
    return trials


def build_chirurgie_trials(
    *,
    temps_court_s: float,
    temps_long_s: float,
    n_zones: int,
    n_essais_par_condition: int,
    secondary_option: int = 0,
    modality: Modality = "time",
    mask_duration_s: float | None = None,
) -> list[TrialSpec]:
    """Ordre papier: pour chaque rep — X×court (zones) puis X×long (zones)."""
    n_z = max(1, int(n_zones))
    n_e = max(1, int(n_essais_par_condition))
    opt = int(secondary_option)
    fixed_mask = float(mask_duration_s if mask_duration_s is not None else NOMINAL_MASK_S)
    trials: list[TrialSpec] = []
    idx = 0
    for rep in range(1, n_e + 1):
        for kind, t_val in (("court", float(temps_court_s)), ("long", float(temps_long_s))):
            for zone in range(1, n_z + 1):
                idx += 1
                if modality == "time":
                    mask = t_val
                else:
                    mask = fixed_mask
                trials.append(
                    TrialSpec(
                        trial_index=idx,
                        delta_time_s=t_val,
                        mask_duration_s=mask,
                        zone=zone,
                        repetition=rep,
                        kind=kind,
                        secondary_option=opt,
                    )
                )
    return trials


def expected_side(modality: Modality, delta_time_s: float, nominal: float = NOMINAL_MASK_S) -> str:
    """Côté « correct » si le sujet compare à la dynamique nominale 1.5 s."""
    if modality == "time":
        # trop tôt si réapparition avant 1.5
        return "trop_tot" if delta_time_s < nominal else ("trop_tard" if delta_time_s > nominal else "exact")
    if modality == "chrono":
        return "trop_faible" if delta_time_s < nominal else ("trop_fort" if delta_time_s > nominal else "exact")
    # tone
    return "trop_grave" if delta_time_s < nominal else ("trop_aigu" if delta_time_s > nominal else "exact")
