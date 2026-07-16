from the_kit.protocol.loader import load_protocol
from the_kit.protocol.validator import validate_protocol

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]


def test_demo_phase3_valid():
    p = load_protocol(ROOT / "examples" / "demo_phase3" / "protocol.json")
    validate_protocol(p)
    types = {n.type for n in p.nodes}
    assert "occultation" in types
    assert "shadow_ball" in types
    assert "mot" in types


def test_preset_occultation():
    p = load_protocol(ROOT / "examples" / "presets" / "occultation_classic.json")
    validate_protocol(p)
    assert p.nodes[0].type == "occultation"
