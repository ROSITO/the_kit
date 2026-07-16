from __future__ import annotations

import hashlib
import json
import platform
import sys
from pathlib import Path
from typing import Any

from the_kit import __version__
from the_kit.protocol.models import Protocol


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_media_hashes(protocol: Protocol) -> dict[str, str]:
    """Hash SHA-256 des médias référencés dans le protocole."""
    hashes: dict[str, str] = {}
    keys = ("file", "video", "audio")
    for node in protocol.nodes:
        for key in keys:
            rel = node.params.get(key)
            if not rel or not isinstance(rel, str):
                continue
            if ".." in Path(rel).parts:
                continue
            p = (protocol.root / rel).resolve()
            if p.is_file():
                hashes[str(rel)] = _hash_file(p)[:16]
    return hashes


def write_environment(
    protocol: Protocol,
    session_dir: Path,
    *,
    extra: dict[str, Any] | None = None,
) -> Path:
    env: dict[str, Any] = {
        "the_kit_version": __version__,
        "python_version": sys.version,
        "platform": platform.platform(),
        "protocol_name": protocol.name,
        "protocol_hash": _hash_file(protocol.path),
        "subject_id": protocol.subject.id,
        "subject_group": protocol.subject.group,
        "engines_requested": sorted({n.engine for n in protocol.nodes}),
        "node_count": len(protocol.nodes),
        "media_hashes": collect_media_hashes(protocol),
        "expanded_from_conditions": bool(protocol.raw.get("_expanded_from_conditions")),
    }
    if extra:
        env.update(extra)
    path = session_dir / "environment.json"
    path.write_text(json.dumps(env, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
