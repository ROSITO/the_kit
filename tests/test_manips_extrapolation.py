"""Tests manips extrapolation Time / Chrono / Tone."""

from __future__ import annotations

from pathlib import Path

import pytest

from the_kit.manips.extrapolation.constants import DEFAULT_DELTA_TIMES_S
from the_kit.manips.extrapolation.planning import (
    build_chirurgie_trials,
    build_lab_trials,
    expected_side,
)
from the_kit.orchestrator import Orchestrator
from the_kit.protocol.loader import load_protocol
from the_kit.protocol.validator import validate_protocol

ROOT = Path(__file__).resolve().parents[1]
MANIPS = ROOT / "examples" / "manips"

PAPER_PROTOCOLS = [
    MANIPS / "spatiotemporelle" / "protocol.json",
    MANIPS / "spatiotemporelle" / "protocol_chirurgie.json",
    MANIPS / "nombre" / "protocol.json",
    MANIPS / "nombre" / "protocol_chirurgie.json",
    MANIPS / "son" / "protocol.json",
    MANIPS / "son" / "protocol_chirurgie.json",
]

LAB_STUBS = [
    "arome",
    "p1_p9_av_sync",
    "audi_visuel",
    "randomflow",
    "shadowi",
    "occultation",
    "occultation_ttc",
    "mot",
    "shadow_corridor_mot",
    "neuroconn_gvs",
    "ni_stim_alba",
    "looming_av",
    "calibration_photosonde",
]


def test_lab_trials_count():
    trials = build_lab_trials(trials_per_condition=2, modality="time")
    assert len(trials) == len(DEFAULT_DELTA_TIMES_S) * 2
    assert trials[0].mask_duration_s == trials[0].delta_time_s


def test_chrono_mask_fixed():
    trials = build_lab_trials(trials_per_condition=1, modality="chrono")
    assert all(t.mask_duration_s == 1.5 for t in trials)


def test_chirurgie_order():
    trials = build_chirurgie_trials(
        temps_court_s=0.95,
        temps_long_s=1.85,
        n_zones=2,
        n_essais_par_condition=2,
        modality="time",
    )
    assert len(trials) == 2 * 2 * 2  # zones * (court+long) * reps
    # first block: court zone1, court zone2, long zone1, long zone2
    assert [t.kind for t in trials[:4]] == ["court", "court", "long", "long"]
    assert [t.zone for t in trials[:4]] == [1, 2, 1, 2]


def test_expected_side_signs():
    assert expected_side("time", 0.7) == "trop_tot"
    assert expected_side("chrono", 0.7) == "trop_faible"
    assert expected_side("tone", 2.1) == "trop_aigu"


@pytest.mark.parametrize("path", PAPER_PROTOCOLS, ids=lambda p: p.parent.name + "/" + p.name)
def test_paper_protocols_validate(path: Path):
    assert path.exists()
    p = load_protocol(path)
    validate_protocol(p)


@pytest.mark.parametrize("name", LAB_STUBS)
def test_lab_stub_exists_and_validates(name: str):
    path = MANIPS / name / "protocol.json"
    assert path.exists(), f"stub manquant (ne pas supprimer): {path}"
    p = load_protocol(path)
    validate_protocol(p)


@pytest.mark.parametrize("path", PAPER_PROTOCOLS, ids=lambda p: p.parent.name + "/" + p.name)
def test_paper_dry_run_writes_trials_csv(path: Path, tmp_path: Path):
    orch = Orchestrator.from_protocol_file(
        path,
        subject_id="TEST",
        session_dir=tmp_path / path.parent.name,
        dry_run=True,
        export_artifacts=False,
    )
    session_dir = orch.run()
    trials = session_dir / "trials.csv"
    assert trials.exists()
    lines = trials.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 2  # header + ≥1 trial
    assert "subject_id" in lines[0]
    assert "manip" in lines[0]
