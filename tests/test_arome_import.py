from pathlib import Path

import pytest

from the_kit.protocol.loader import load_protocol, migrate_arome_v0

AROME_DIR = Path.home() / "Documents" / "Projet_Arome_ANAELLE" / "Projet_Arome_ANAELLE"


@pytest.mark.skipif(
    not (AROME_DIR / "experiment1_notrig.json").exists(),
    reason="Projet Arôme non présent sur cette machine",
)
def test_load_arome_experiment1_notrig():
    path = AROME_DIR / "experiment1_notrig.json"
    raw = __import__("json").loads(path.read_text(encoding="utf-8"))
    migrated = migrate_arome_v0(raw)
    assert migrated["protocol_version"] == "1.0"
    assert all(n.get("engine") == "qt" for n in migrated["nodes"])
    p = load_protocol(path, subject_id="REGTEST")
    assert len(p.nodes) > 0
    assert p.nodes[0].engine == "qt"
