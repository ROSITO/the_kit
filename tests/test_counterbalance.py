from the_kit.protocol.counterbalance import (
    apply_latin_square_to_trials,
    balanced_latin_square,
    order_for_subject,
)
from the_kit.protocol.expander import expand_conditions


def test_balanced_latin_square_4():
    g = balanced_latin_square(4)
    assert len(g) == 4
    for row in g:
        assert sorted(row) == [0, 1, 2, 3]


def test_order_differs_by_subject():
    a = order_for_subject(4, "S001", subject_number=0)
    b = order_for_subject(4, "S002", subject_number=1)
    assert sorted(a) == [0, 1, 2, 3]
    assert a != b or 4 == 1


def test_expand_with_latin_square():
    data = {
        "conditions": [
            {"id": "A", "type": "delay", "params": {"duration_s": 0.01}},
            {"id": "B", "type": "delay", "params": {"duration_s": 0.01}},
            {"id": "C", "type": "delay", "params": {"duration_s": 0.01}},
            {"id": "D", "type": "delay", "params": {"duration_s": 0.01}},
        ],
        "presentation": {
            "counterbalance": "latin_square",
            "randomize_trials": False,
        },
    }
    out = expand_conditions(data, subject_id="S003", subject_number=2)
    ids = [n["id"] for n in out["nodes"]]
    assert ids[0] in ("A", "B", "C", "D")
    assert "_counterbalance" in out


def test_apply_latin_square_trials():
    trials = [{"id": f"T{i}"} for i in range(4)]
    ordered = apply_latin_square_to_trials(trials, subject_id="P1", subject_number=1)
    assert sorted(t["id"] for t in ordered) == ["T0", "T1", "T2", "T3"]
    assert [t["id"] for t in ordered] != ["T0", "T1", "T2", "T3"]
