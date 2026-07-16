from the_kit.protocol.loader import load_protocol
from the_kit.protocol.validator import validate_protocol
from the_kit.pygame_handlers.scene.backgrounds import BACKGROUNDS, create_background
from the_kit.pygame_handlers.scene.stimuli import STIMULI, create_stimulus

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]


def test_preset_shadow_mot_valid():
    p = load_protocol(ROOT / "examples" / "presets" / "shadow_corridor_mot.json")
    validate_protocol(p)
    assert p.nodes[0].type == "pygame_scene"
    assert p.nodes[0].params["background"] == "shadow_corridor"


def test_registry_names():
    assert "shadow_corridor" in BACKGROUNDS
    assert "mot" in STIMULI
    assert "optic_flow" in STIMULI
    create_background("plain")
    create_stimulus("mot")
