"""Constantes partagées — papier manips v2."""

from __future__ import annotations

# DeltaTime (s) — 8 valeurs communes Time / Chrono / Tone
DEFAULT_DELTA_TIMES_S: tuple[float, ...] = (
    0.70,
    0.95,
    1.15,
    1.30,
    1.50,
    1.60,
    1.85,
    2.10,
)

NOMINAL_MASK_S = 1.5

# Tone (papier)
TONE_F0_HZ = 500.0
TONE_RISE_SEMITONES_PER_S = 2.0

TRIAL_CSV_COLUMNS = [
    "subject_id",
    "manip",
    "version",
    "trial_index",
    "delta_time_s",
    "mask_duration_s",
    "zone",
    "repetition",
    "kind",
    "secondary_option",
    "response",
    "rt_ms",
    "expected_side",
    "correct",
    "secondary_responded",
    "secondary_rt_ms",
    "secondary_correct",
    "stim_params_json",
    "mock",
]
