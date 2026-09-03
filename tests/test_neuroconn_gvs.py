from the_kit.io import nidaqmx_io
from the_kit.io.gvs_lsl import GVS_CONDITION_CODES
from the_kit.pygame_handlers.neuroconn_gvs import GVS_CONDITIONS, _build_trial_list


def test_trapezoid_duration():
    wave = nidaqmx_io.generate_trapezoid_ramp(
        1.0, rise_s=3, plateau_s=4, fall_s=3, sampling_rate=400
    )
    assert len(wave) == 4000


def test_control_shuffle_changes_order():
    base = nidaqmx_io.generate_trapezoid_ramp(1.0, rise_s=0.1, plateau_s=0.1, fall_s=0.1, sampling_rate=100)
    shuffled = nidaqmx_io.generate_trapezoid_ramp(
        1.0, rise_s=0.1, plateau_s=0.1, fall_s=0.1, sampling_rate=100, shuffle=True, rng=__import__("random").Random(1)
    )
    assert sorted(base) == sorted(shuffled)
    assert base != shuffled


def test_fifty_trials():
    trials = _build_trial_list(10, seed=1)
    assert len(trials) == 50
    for c in GVS_CONDITIONS:
        assert trials.count(c) == 10


def test_subset_conditions():
    from the_kit.pygame_handlers.neuroconn_gvs import _normalize_conditions

    conds = _normalize_conditions(["AP", "control", "AP"])
    assert conds == ["AP", "CONTROL"]
    trials = _build_trial_list(3, seed=0, conditions=conds)
    assert len(trials) == 6
    assert set(trials) == {"AP", "CONTROL"}
    assert trials.count("AP") == 3


def test_unknown_condition_raises():
    from the_kit.pygame_handlers.neuroconn_gvs import _normalize_conditions
    import pytest

    with pytest.raises(ValueError, match="inconnue"):
        _normalize_conditions(["AP", "FOO"])


def test_lsl_codes():
    assert GVS_CONDITION_CODES["AP"] == 2
    assert GVS_CONDITION_CODES["PA"] == 3
    assert GVS_CONDITION_CODES["LATG"] == 4
    assert GVS_CONDITION_CODES["LATD"] == 5
    assert GVS_CONDITION_CODES["CONTROL"] == 6
    from the_kit.io.gvs_lsl import GVS_RESPONSE

    assert GVS_RESPONSE == 8


def test_trigger_table_defaults():
    from the_kit.io.gvs_lsl import TriggerTable

    t = TriggerTable()
    assert t.resolve("stim_onset", condition="LATG") == (4, "Onset stim gauche (LATG)")
    assert t.resolve("response")[0] == 8
    assert t.resolve("stim_offset", condition="AP")[0] is None


def test_trigger_table_override_latg():
    from the_kit.io.gvs_lsl import TriggerTable

    t = TriggerTable(
        {
            "stim_onset": {
                "LATG": {"code": 11, "why": "Onset gauche protocole alt"},
            },
            "response": 20,
        }
    )
    code, why = t.resolve("stim_onset", condition="LATG")
    assert code == 11
    assert "alt" in why
    assert t.resolve("stim_onset", condition="LATD")[0] == 5
    assert t.resolve("response")[0] == 20


def test_trigger_table_skip_null_code():
    from the_kit.io.gvs_lsl import TriggerTable

    t = TriggerTable({"iti": {"code": None, "why": "pas d'ITI"}})
    assert t.resolve("iti")[0] is None


def test_protocol_json_declares_triggers():
    from pathlib import Path

    from the_kit.protocol.loader import load_protocol

    root = Path(__file__).resolve().parents[1]
    p = load_protocol(root / "examples" / "neuroconn_gvs" / "protocol.json")
    gvs = next(n for n in p.nodes if n.type == "neuroconn_gvs")
    triggers = gvs.params["triggers"]
    assert triggers["stim_onset"]["LATG"]["code"] == 4
    assert triggers["response"]["code"] == 8
    assert "why" in triggers["stim_onset"]["LATG"]



def test_protocol_valid():
    from pathlib import Path

    from the_kit.protocol.loader import load_protocol
    from the_kit.protocol.validator import validate_protocol

    root = Path(__file__).resolve().parents[1]
    p = load_protocol(root / "examples" / "neuroconn_gvs" / "protocol.json")
    validate_protocol(p)
