"""Tests manips extrapolation Time / Chrono / Tone."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from the_kit.manips.extrapolation.constants import DEFAULT_DELTA_TIMES_S
from the_kit.manips.extrapolation.planning import (
    build_chirurgie_trials,
    build_lab_trials,
    expected_side,
)
from the_kit.manips.extrapolation.runner import (
    PAPER_TRIALS_PER_CONDITION,
    _prompt_chirurgie_args,
    _smoke_cap_n,
)
from the_kit.manips.extrapolation.secondary import run_secondary_mock
from the_kit.manips.extrapolation.stimuli import (
    play_samples_or_mock,
    synthesize_pure_tone,
    synthesize_rising_tone,
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


def test_paper_default_n_is_15():
    assert PAPER_TRIALS_PER_CONDITION == 15
    for path in (
        MANIPS / "spatiotemporelle" / "protocol.json",
        MANIPS / "nombre" / "protocol.json",
        MANIPS / "son" / "protocol.json",
    ):
        raw = json.loads(path.read_text(encoding="utf-8"))
        args = raw["nodes"][0]["params"]["script"]["args"]
        assert args["trials_per_condition"] == 15


def test_lab_trials_count_production():
    trials = build_lab_trials(trials_per_condition=15, modality="time")
    assert len(trials) == len(DEFAULT_DELTA_TIMES_S) * 15


def test_smoke_cap():
    assert _smoke_cap_n(15, dry_run=True) == 1
    assert _smoke_cap_n(15, dry_run=False) == 15


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
    assert len(trials) == 8
    assert [t.kind for t in trials[:4]] == ["court", "court", "long", "long"]
    assert [t.zone for t in trials[:4]] == [1, 2, 1, 2]


def test_expected_side_signs():
    assert expected_side("time", 0.7) == "trop_tot"
    assert expected_side("chrono", 0.7) == "trop_faible"
    assert expected_side("tone", 2.1) == "trop_aigu"


def test_secondary_mock_options():
    assert run_secondary_mock(0).responded is False
    s1 = run_secondary_mock(1)
    assert s1.responded and s1.detail.get("task") == "green_circle"
    s2 = run_secondary_mock(2)
    assert s2.detail.get("task") == "change_detection"


def test_tone_synthesis_and_mock_play():
    samples, sr = synthesize_rising_tone(duration_s=0.05, f0_hz=500, rise_semitones_per_s=2.0)
    assert len(samples) == int(0.05 * sr)
    meta = play_samples_or_mock(samples, sr, mock=True)
    assert meta["backend"] == "mock"
    assert meta["played"] is False
    probe, sr2 = synthesize_pure_tone(duration_s=0.02, freq_hz=560.0)
    assert len(probe) > 0 and sr2 == sr


def test_prompt_launch_env(monkeypatch):
    monkeypatch.setenv(
        "THE_KIT_CHIRURGIE_ANSWERS",
        json.dumps(
            {
                "temps_court_s": 0.8,
                "temps_long_s": 2.0,
                "n_zones": 3,
                "n_essais_par_condition": 15,
                "secondary_option": 1,
            }
        ),
    )
    out = _prompt_chirurgie_args({}, interactive=True)
    assert out["temps_court_s"] == 0.8
    assert out["n_zones"] == 3
    assert out["secondary_option"] == 1
    assert out["_source"] == "env"


def test_prompt_launch_interactive_input():
    answers = iter(["0.9", "1.9", "2", "4", "0"])

    def fake_input(_prompt: str) -> str:
        return next(answers)

    out = _prompt_chirurgie_args(
        {"temps_court_s": 0.95, "temps_long_s": 1.85, "n_zones": 1, "n_essais_par_condition": 1},
        interactive=True,
        input_fn=fake_input,
    )
    assert out["temps_court_s"] == 0.9
    assert out["temps_long_s"] == 1.9
    assert out["n_zones"] == 2
    assert out["n_essais_par_condition"] == 4
    assert out["_source"] == "prompt"


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
        session_dir=tmp_path / (path.parent.name + "_" + path.stem),
        dry_run=True,
        export_artifacts=False,
    )
    session_dir = orch.run()
    trials = session_dir / "trials.csv"
    assert trials.exists()
    lines = trials.read_text(encoding="utf-8").strip().splitlines()
    # dry-run smoke → 1 × 8 deltas (lab) or 2 kinds × n_zones (chirurgie capped)
    assert len(lines) >= 2
    assert "subject_id" in lines[0] and "manip" in lines[0]


def test_interactive_pygame_auto_input(tmp_path: Path, monkeypatch):
    pygame = pytest.importorskip("pygame")
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("THE_KIT_EXTRAPOLATION_AUTO_INPUT", "1")
    monkeypatch.delenv("THE_KIT_EXTRAPOLATION_MOCK", raising=False)

    path = MANIPS / "spatiotemporelle" / "protocol.json"
    # force small N via smoke
    monkeypatch.setenv("THE_KIT_EXTRAPOLATION_SMOKE", "1")
    orch = Orchestrator.from_protocol_file(
        path,
        subject_id="AUTO",
        session_dir=tmp_path / "auto_time",
        dry_run=False,
        export_artifacts=False,
    )
    session_dir = orch.run()
    trials = session_dir / "trials.csv"
    assert trials.exists()
    rows = trials.read_text(encoding="utf-8").strip().splitlines()
    assert len(rows) == 1 + len(DEFAULT_DELTA_TIMES_S)  # N smoke=1
    # stim mode pygame
    assert "pygame" in rows[1] or "mock" in rows[1]


def test_tone_real_backend_or_fallback(monkeypatch):
    """Sans dry-run mock_audio=False : tente sounddevice, accepte fallback."""
    samples, sr = synthesize_rising_tone(duration_s=0.02)
    meta = play_samples_or_mock(samples, sr, mock=False)
    assert meta["backend"] in ("sounddevice",) or str(meta["backend"]).startswith("mock_fallback")


def test_secondary_option_in_dry_run(tmp_path: Path):
    path = MANIPS / "nombre" / "protocol.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["nodes"][0]["params"]["script"]["args"]["secondary_option"] = 1
    raw["nodes"][0]["params"]["script"]["args"]["trials_per_condition"] = 15
    p = tmp_path / "nombre_opt1.json"
    p.write_text(json.dumps(raw), encoding="utf-8")
    # protocol root must contain scripts/
    import shutil

    shutil.copytree(MANIPS / "nombre" / "scripts", tmp_path / "scripts")
    orch = Orchestrator.from_protocol_file(
        p,
        subject_id="OPT1",
        session_dir=tmp_path / "sess",
        dry_run=True,
        export_artifacts=False,
    )
    session_dir = orch.run()
    text = (session_dir / "trials.csv").read_text(encoding="utf-8")
    assert "True" in text or "true" in text.lower()  # secondary_responded
