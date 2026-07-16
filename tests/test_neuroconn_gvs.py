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


def test_lsl_codes():
    assert GVS_CONDITION_CODES["AP"] == 2
    assert GVS_CONDITION_CODES["PA"] == 3
    assert GVS_CONDITION_CODES["LATG"] == 4
    assert GVS_CONDITION_CODES["LATD"] == 5
    assert GVS_CONDITION_CODES["CONTROL"] == 6
    from the_kit.io.gvs_lsl import GVS_RESPONSE

    assert GVS_RESPONSE == 8


def test_protocol_valid():
    from pathlib import Path

    from the_kit.protocol.loader import load_protocol
    from the_kit.protocol.validator import validate_protocol

    root = Path(__file__).resolve().parents[1]
    p = load_protocol(root / "examples" / "neuroconn_gvs" / "protocol.json")
    validate_protocol(p)
