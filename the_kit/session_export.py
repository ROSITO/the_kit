"""Export session — BIDS-like (F-1605) et rapport HTML (F-1707)."""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


def _safe_bids_label(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "", value) or "unknown"


def load_events(session_dir: Path) -> list[dict[str, Any]]:
    path = session_dir / "events.jsonl"
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            events.append(json.loads(line))
    return events


def load_session_meta(session_dir: Path) -> dict[str, Any]:
    path = session_dir / "session_meta.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _onset_seconds(events: list[dict[str, Any]], ev: dict[str, Any]) -> float:
    t0 = events[0].get("ts_perf", 0.0) if events else 0.0
    return round(float(ev.get("ts_perf", t0)) - float(t0), 6)


def _duration_for_node(events: list[dict[str, Any]], node_id: str) -> float:
    start = end = None
    for ev in events:
        if ev.get("node_id") != node_id:
            continue
        if ev.get("event") == "node_start":
            start = ev.get("ts_perf")
        elif ev.get("event") == "node_end":
            end = ev.get("ts_perf")
    if start is not None and end is not None:
        return round(float(end) - float(start), 6)
    return 0.0


def export_bids(session_dir: str | Path, *, task_name: str | None = None) -> Path:
    """
    Écrit sous ``session_dir/bids/`` :
    - dataset_description.json
    - participants.tsv
    - task-<name>_events.tsv
    """
    session_dir = Path(session_dir).resolve()
    meta = load_session_meta(session_dir)
    events = load_events(session_dir)
    subject_id = meta.get("subject_id", "anonymous")
    sub_label = _safe_bids_label(subject_id)
    protocol_name = meta.get("protocol_name", "thekit")
    task = task_name or re.sub(r"[^a-zA-Z0-9]", "", protocol_name) or "task"

    bids_root = session_dir / "bids"
    bids_root.mkdir(parents=True, exist_ok=True)

    (bids_root / "dataset_description.json").write_text(
        json.dumps(
            {
                "Name": f"The Kit — {protocol_name}",
                "BIDSVersion": "1.9.0",
                "DatasetType": "behavioral",
                "GeneratedBy": [
                    {
                        "Name": "The Kit",
                        "Version": meta.get("the_kit_version", "?"),
                    }
                ],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    participants_path = bids_root / "participants.tsv"
    pcols = ["participant_id", "subject_id", "group", "session_dir"]
    prow = {
        "participant_id": f"sub-{sub_label}",
        "subject_id": subject_id,
        "group": meta.get("subject_group") or "n/a",
        "session_dir": session_dir.name,
    }
    with participants_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=pcols, delimiter="\t")
        w.writeheader()
        w.writerow(prow)

    event_cols = [
        "onset",
        "duration",
        "trial_type",
        "event",
        "node_id",
        "node_index",
        "engine",
        "response_time",
        "value",
        "subject_id",
    ]
    rows: list[dict[str, Any]] = []
    for ev in events:
        payload = ev.get("payload") or {}
        rt = payload.get("rt_ms")
        rows.append(
            {
                "onset": _onset_seconds(events, ev),
                "duration": _duration_for_node(events, ev["node_id"])
                if ev.get("event") == "node_end" and ev.get("node_id")
                else "",
                "trial_type": ev.get("node_type") or ev.get("event"),
                "event": ev.get("event"),
                "node_id": ev.get("node_id", ""),
                "node_index": ev.get("node_index", ""),
                "engine": ev.get("engine", ""),
                "response_time": (float(rt) / 1000.0) if rt is not None else "",
                "value": payload.get("response") or payload.get("status") or "",
                "subject_id": ev.get("subject_id", subject_id),
            }
        )

    events_path = bids_root / f"sub-{sub_label}_task-{task}_events.tsv"

    with events_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=event_cols, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)

    responses_src = session_dir / "responses.csv"
    if responses_src.exists():
        dest = bids_root / f"{events_path.stem.replace('_events', '_responses')}.tsv"
        dest.write_text(
            responses_src.read_text(encoding="utf-8").replace(",", "\t"),
            encoding="utf-8",
        )

    return bids_root


def export_html_report(session_dir: str | Path) -> Path:
    session_dir = Path(session_dir).resolve()
    meta = load_session_meta(session_dir)
    events = load_events(session_dir)
    responses_rows: list[dict[str, str]] = []
    resp_path = session_dir / "responses.csv"
    if resp_path.exists():
        with resp_path.open(encoding="utf-8") as f:
            responses_rows = list(csv.DictReader(f))

    node_rows: list[dict[str, Any]] = []
    for ev in events:
        if ev.get("event") != "node_end":
            continue
        nid = ev.get("node_id", "")
        node_rows.append(
            {
                "node_id": nid,
                "type": ev.get("node_type", ""),
                "engine": ev.get("engine", ""),
                "duration_s": _duration_for_node(events, nid),
                "payload": json.dumps(ev.get("payload") or {}, ensure_ascii=False),
            }
        )

    started = meta.get("started_at_iso", "")
    ended = meta.get("ended_at_iso", "")
    duration = meta.get("duration_s", "")
    protocol = meta.get("protocol_name", "")

    def esc(s: Any) -> str:
        return (
            str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    tr_nodes = "".join(
        f"<tr><td>{esc(r['node_id'])}</td><td>{esc(r['type'])}</td>"
        f"<td>{esc(r['engine'])}</td><td>{r['duration_s']}</td>"
        f"<td><code>{esc(r['payload'])}</code></td></tr>"
        for r in node_rows
    )
    tr_resp = "".join(
        f"<tr><td>{esc(r.get('node_id',''))}</td><td>{esc(r.get('stimulus',''))}</td>"
        f"<td>{esc(r.get('response',''))}</td><td>{esc(r.get('rt_ms',''))}</td></tr>"
        for r in responses_rows
    )

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8"/>
  <title>The Kit — rapport {esc(session_dir.name)}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; background: #111; color: #eee; }}
    h1 {{ color: #7dd3fc; }}
    table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
    th, td {{ border: 1px solid #333; padding: 0.4rem 0.6rem; text-align: left; }}
    th {{ background: #222; }}
    code {{ font-size: 0.85em; word-break: break-all; }}
    .meta dt {{ font-weight: 600; }} .meta dd {{ margin: 0 0 0.5rem 0; }}
  </style>
</head>
<body>
  <h1>Rapport session The Kit</h1>
  <dl class="meta">
    <dt>Dossier</dt><dd>{esc(session_dir)}</dd>
    <dt>Participant</dt><dd>{esc(meta.get('subject_id',''))}</dd>
    <dt>Protocole</dt><dd>{esc(protocol)}</dd>
    <dt>Début / fin</dt><dd>{esc(started)} → {esc(ended)} ({esc(duration)} s)</dd>
    <dt>Statut</dt><dd>{esc(meta.get('status',''))}</dd>
    <dt>Version</dt><dd>{esc(meta.get('the_kit_version',''))}</dd>
  </dl>
  <h2>Nœuds exécutés</h2>
  <table><thead><tr><th>id</th><th>type</th><th>engine</th><th>durée (s)</th><th>payload</th></tr></thead>
  <tbody>{tr_nodes or '<tr><td colspan="5">—</td></tr>'}</tbody></table>
  <h2>Réponses</h2>
  <table><thead><tr><th>node</th><th>stimulus</th><th>response</th><th>rt_ms</th></tr></thead>
  <tbody>{tr_resp or '<tr><td colspan="4">—</td></tr>'}</tbody></table>
  <p><small>Généré {esc(datetime.now().isoformat())}</small></p>
</body>
</html>
"""
    out = session_dir / "session_report.html"
    out.write_text(html, encoding="utf-8")
    return out


def export_session_artifacts(
    session_dir: str | Path,
    *,
    bids: bool = True,
    html: bool = True,
    task_name: str | None = None,
) -> dict[str, Path]:
    session_dir = Path(session_dir).resolve()
    result: dict[str, Path] = {}
    if bids:
        result["bids"] = export_bids(session_dir, task_name=task_name)
    if html:
        result["report"] = export_html_report(session_dir)
    return result
