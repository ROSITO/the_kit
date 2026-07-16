from __future__ import annotations

import json
import zipfile
from pathlib import Path

from the_kit.protocol.loader import load_protocol
from the_kit.protocol.models import Protocol


def _collect_asset_paths(protocol: Protocol) -> list[Path]:
    paths: list[Path] = []
    seen: set[Path] = set()
    for node in protocol.nodes:
        for key in ("file", "video", "audio"):
            rel = node.params.get(key)
            if not rel or not isinstance(rel, str):
                continue
            if ".." in Path(rel).parts:
                continue
            p = (protocol.root / rel).resolve()
            if p.is_file() and p not in seen:
                seen.add(p)
                paths.append(p)
        script = node.params.get("script") or {}
        if isinstance(script, dict) and script.get("file"):
            rel = script["file"]
            p = (protocol.root / rel).resolve()
            if p.is_file() and p not in seen:
                seen.add(p)
                paths.append(p)
    return paths


def export_protocol_zip(
    protocol_path: str | Path,
    output_zip: str | Path,
    *,
    subject_id: str | None = None,
) -> Path:
    protocol = load_protocol(protocol_path, subject_id=subject_id or "export")
    output_zip = Path(output_zip).resolve()
    output_zip.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "protocol.json",
            json.dumps(protocol.raw, indent=2, ensure_ascii=False),
        )
        for asset in _collect_asset_paths(protocol):
            arcname = asset.relative_to(protocol.root)
            zf.write(asset, arcname.as_posix())
    return output_zip
