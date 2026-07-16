import json
import zipfile
from pathlib import Path

from the_kit.export import export_protocol_zip


def test_export_zip(tmp_path):
    proto = tmp_path / "protocol.json"
    vid = tmp_path / "clip.mp4"
    vid.write_bytes(b"fake")
    proto.write_text(
        json.dumps(
            {
                "protocol_version": "1.0",
                "nodes": [
                    {
                        "type": "video",
                        "engine": "qt",
                        "params": {"file": "clip.mp4", "duration_s": 1},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    zpath = tmp_path / "out.zip"
    export_protocol_zip(proto, zpath)
    with zipfile.ZipFile(zpath) as zf:
        names = zf.namelist()
    assert "protocol.json" in names
    assert "clip.mp4" in names
