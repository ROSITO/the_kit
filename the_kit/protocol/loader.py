from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from the_kit.protocol.expander import expand_conditions
from the_kit.protocol.models import Node, Protocol, SubjectInfo

AROME_V0_TYPES = frozenset({"video", "questionnaire", "trigger", "wait_key", "delay"})


def _is_arome_v0(data: dict[str, Any]) -> bool:
    if data.get("protocol_version"):
        return False
    nodes = data.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        return False
    return all(isinstance(n, dict) and "type" in n for n in nodes)


def migrate_arome_v0(data: dict[str, Any]) -> dict[str, Any]:
    """Convertit un protocole Arôme v0 vers protocol v1.0."""
    out = dict(data)
    out["protocol_version"] = "1.0"
    out.setdefault("name", data.get("name", "arome_import"))
    out.setdefault("loop", data.get("loop", 1))
    migrated_nodes: list[dict[str, Any]] = []
    for i, node in enumerate(data.get("nodes", [])):
        n = dict(node)
        n.setdefault("engine", "qt")
        n.setdefault("timing_mode", "standard")
        n.setdefault("id", f"node_{i:03d}")
        ntype = n.get("type")
        params = dict(n.get("params") or {})
        if ntype == "video":
            if "file" in n and "file" not in params:
                params["file"] = n["file"]
            if "time" in n and "duration_s" not in params:
                params["duration_s"] = n["time"]
        elif ntype == "questionnaire":
            for k, v in n.items():
                if k.startswith("question") or k == "echelle":
                    params.setdefault(k, v)
        elif ntype == "wait_key":
            for k in ("key", "message"):
                if k in n:
                    params.setdefault(k, n[k])
        elif ntype == "trigger":
            for k in ("port", "value"):
                if k in n:
                    params.setdefault(k, n[k])
        elif ntype == "delay":
            if "duration_s" in n:
                params.setdefault("duration_s", n["duration_s"])
        n["params"] = params
        migrated_nodes.append(n)
    out["nodes"] = migrated_nodes
    return out


def _node_from_dict(index: int, raw: dict[str, Any]) -> Node:
    params = dict(raw.get("params") or {})
    ntype = raw["type"]
    if ntype == "video":
        params.setdefault("file", raw.get("file"))
        params.setdefault("duration_s", raw.get("time"))
    elif ntype == "questionnaire":
        for k, v in raw.items():
            if k.startswith("question") or k == "echelle":
                params.setdefault(k, v)
    elif ntype == "wait_key":
        params.setdefault("key", raw.get("key", "t"))
        params.setdefault("message", raw.get("message", ""))
    elif ntype == "trigger":
        params.setdefault("port", raw.get("port", "COM4"))
        params.setdefault("value", raw.get("value", 1))
    elif ntype == "delay":
        params.setdefault("duration_s", raw.get("duration_s", raw.get("time", 1)))
    return Node(
        index=index,
        type=ntype,
        engine=raw.get("engine", "qt"),
        timing_mode=raw.get("timing_mode", "standard"),
        id=raw.get("id"),
        params={k: v for k, v in params.items() if v is not None},
        raw=raw,
    )


def load_protocol(
    path: str | Path,
    *,
    subject_id: str | None = None,
    subject_group: str | None = None,
) -> Protocol:
    path = Path(path).resolve()
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if _is_arome_v0(data):
        data = migrate_arome_v0(data)
    subject_raw = data.get("subject") or {}
    subj_id = subject_id or subject_raw.get("id", "anonymous")
    subj_grp = subject_group or subject_raw.get("group")
    subj_num = subject_raw.get("number")
    data = expand_conditions(
        data,
        subject_group=subj_grp,
        subject_id=subj_id,
        subject_number=int(subj_num) if subj_num is not None else None,
    )
    subject = SubjectInfo(id=subj_id, group=subj_grp)
    nodes = [_node_from_dict(i, n) for i, n in enumerate(data.get("nodes", []))]
    return Protocol(
        protocol_version=data.get("protocol_version", "1.0"),
        name=data.get("name", path.stem),
        loop=int(data.get("loop", 1)),
        nodes=nodes,
        path=path,
        root=path.parent,
        subject=subject,
        randomize_blocks=bool(data.get("randomize_blocks", False)),
        raw=data,
    )
