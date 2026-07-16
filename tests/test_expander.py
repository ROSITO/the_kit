from the_kit.protocol.expander import expand_conditions
from the_kit.protocol.loader import load_protocol


def test_expand_conditions_shuffle():
    data = {
        "protocol_version": "1.0",
        "conditions": [
            {"id": "a", "video": "v1.mp4", "audio": "a1.wav"},
            {"id": "b", "video": "v2.mp4", "audio": "a2.wav"},
        ],
        "presentation": {"randomize_trials": False},
        "timing": {"iti_jitter_s": [0.1, 0.1]},
    }
    out = expand_conditions(data)
    assert len(out["nodes"]) == 4
    types = [n["type"] for n in out["nodes"]]
    assert types.count("av_sync") == 2
    assert types.count("delay") == 2


def test_expand_with_consent():
    data = {
        "consent": {"text": "J'accepte", "key": "space"},
        "conditions": [{"id": "t1", "video": "v.mp4", "audio": "a.wav"}],
        "presentation": {"randomize_trials": False},
    }
    out = expand_conditions(data)
    assert out["nodes"][0]["type"] == "consent"
    assert out["nodes"][1]["type"] == "av_sync"


def test_load_protocol_expands_conditions(tmp_path):
    path = tmp_path / "p.json"
    path.write_text(
        """
        {
          "protocol_version": "1.0",
          "conditions": [
            {"id": "x", "video": "v.mp4", "audio": "a.wav"}
          ],
          "presentation": {"randomize_trials": false}
        }
        """,
        encoding="utf-8",
    )
    p = load_protocol(path)
    assert len(p.nodes) >= 1
    assert p.raw.get("_expanded_from_conditions")
