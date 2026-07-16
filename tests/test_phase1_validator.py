from the_kit.protocol.loader import load_protocol
from the_kit.protocol.validator import validate_protocol

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "demo_multi_engine" / "protocol.json"


def test_demo_multi_engine_valid():
    p = load_protocol(DEMO)
    validate_protocol(p)
    engines = {n.engine for n in p.nodes}
    assert engines == {"qt", "python", "pygame"}
