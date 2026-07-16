import json
from pathlib import Path

import pytest

from the_kit.protocol.loader import load_protocol, migrate_arome_v0
from the_kit.protocol.validator import ProtocolValidationError, validate_protocol

ROOT = Path(__file__).resolve().parents[1]
MINIMAL = ROOT / "examples" / "arome_import" / "minimal_protocol.json"


def test_load_minimal_v1():
    p = load_protocol(MINIMAL, subject_id="T01")
    assert p.protocol_version == "1.0"
    assert p.name == "minimal_demo"
    assert len(p.nodes) == 3
    assert p.subject.id == "T01"
    assert p.nodes[0].type == "wait_key"
    assert p.nodes[0].engine == "qt"


def test_migrate_arome_v0():
    raw = {
        "loop": 2,
        "nodes": [
            {"type": "video", "file": "v.mp4", "time": 10},
            {"type": "trigger", "port": "COM4", "value": 3},
        ],
    }
    migrated = migrate_arome_v0(raw)
    assert migrated["protocol_version"] == "1.0"
    assert migrated["nodes"][0]["engine"] == "qt"
    assert migrated["nodes"][0]["params"]["file"] == "v.mp4"
    assert migrated["nodes"][0]["params"]["duration_s"] == 10


def test_load_auto_migrate(tmp_path: Path):
    path = tmp_path / "legacy.json"
    path.write_text(
        json.dumps(
            {
                "nodes": [
                    {
                        "type": "questionnaire",
                        "question1": "Q1",
                        "echelle": ["a", "b"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    p = load_protocol(path)
    assert p.protocol_version == "1.0"
    assert p.nodes[0].params["question1"] == "Q1"


def test_validate_minimal():
    p = load_protocol(MINIMAL)
    validate_protocol(p)


def test_validate_rejects_unknown_type():
    path = Path(__file__).parent / "fixtures" / "bad_type.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "protocol_version": "1.0",
                "nodes": [{"type": "eyetracker_foo", "engine": "pygame"}],
            }
        ),
        encoding="utf-8",
    )
    p = load_protocol(path)
    with pytest.raises(ProtocolValidationError) as exc:
        validate_protocol(p)
    assert "eyetracker_foo" in str(exc.value)
