"""Export session — BIDS-like générique (F-1605) et rapport HTML (F-1707)."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

EVENT_COLUMNS = [
    "onset",
    "duration",
    "trial_type",
    "event",
    "node_id",
    "node_index",
    "engine",
    "timing_mode",
    "stimulus",
    "response",
    "response_time",
    "value",
    "payload_json",
]

BEH_COLUMNS = [
    "trial_type",
    "node_id",
    "node_index",
    "node_type",
    "stimulus",
    "response",
    "response_time",
    "engine",
]

_DEFAULT_AUTHORS = ["CerCo / ROSITO", "The Kit"]
_DEFAULT_LICENSE = "CC0-1.0"
_DEFAULT_INSTITUTION = "CerCo (CNRS / Université Toulouse)"
_DEFAULT_DEPARTMENT = "Laboratoire CerCo"

_VALUE_KEYS = ("status", "label", "code", "value", "direction", "condition")
_CONSUMED_PAYLOAD_KEYS = frozenset(
    {"stimulus", "response", "rt_ms", "status", "label", "code", "value", "direction", "condition"}
)


def _safe_bids_label(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "", str(value)) or "unknown"


def _task_label(protocol_name: str, task_name: str | None = None) -> str:
    if task_name:
        return _safe_bids_label(task_name)
    return _safe_bids_label(protocol_name) or "task"


def _ses_label(session_dir: Path, meta: dict[str, Any]) -> str:
    """Dérive ses-<id> du nom de dossier (YYYYMMDD_HHMMSS_*) ou de started_at_iso."""
    name = session_dir.name
    m = re.match(r"^(\d{8})_(\d{6})", name)
    if m:
        return f"{m.group(1)}{m.group(2)}"
    started = str(meta.get("started_at_iso") or "")
    digits = re.sub(r"\D", "", started)[:14]
    if len(digits) >= 14:
        return digits[:14]
    return _safe_bids_label(name)[:32] or "unknown"


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


def _t0(events: list[dict[str, Any]]) -> float:
    return float(events[0].get("ts_perf", 0.0)) if events else 0.0


def _onset_seconds(events: list[dict[str, Any]], ev: dict[str, Any]) -> float:
    return round(float(ev.get("ts_perf", _t0(events))) - _t0(events), 6)


def _pair_key(ev: dict[str, Any]) -> tuple[Any, ...]:
    payload = ev.get("payload") or {}
    return (
        ev.get("node_id"),
        payload.get("trial") if "trial" in payload else None,
    )


def _matching_start_name(end_name: str) -> str | None:
    if end_name == "node_end":
        return "node_start"
    if end_name.endswith("_end"):
        return end_name[: -len("_end")] + "_start"
    return None


def _duration_for_event(
    events: list[dict[str, Any]],
    ev: dict[str, Any],
    *,
    index: int,
) -> str:
    """Durée générique : paire *_start → *_end / node_start → node_end."""
    name = str(ev.get("event") or "")
    start_name = _matching_start_name(name)
    if start_name is None:
        return "n/a"
    key = _pair_key(ev)
    end_t = ev.get("ts_perf")
    if end_t is None:
        return "n/a"
    for j in range(index - 1, -1, -1):
        prev = events[j]
        if prev.get("event") != start_name:
            continue
        if _pair_key(prev) != key:
            continue
        start_t = prev.get("ts_perf")
        if start_t is None:
            return "n/a"
        return f"{round(float(end_t) - float(start_t), 6)}"
    return "n/a"


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


def _scalar_value(payload: dict[str, Any]) -> str:
    for key in _VALUE_KEYS:
        if key in payload and payload[key] is not None and key != "response":
            val = payload[key]
            if isinstance(val, (str, int, float, bool)):
                return str(val)
    return ""


def _remaining_payload(payload: dict[str, Any]) -> str:
    rest = {k: v for k, v in payload.items() if k not in _CONSUMED_PAYLOAD_KEYS}
    if not rest:
        return ""
    return json.dumps(rest, ensure_ascii=False, separators=(",", ":"))


def _na(value: Any) -> str:
    """BIDS missing values as ``n/a`` (never empty string)."""
    if value is None:
        return "n/a"
    s = str(value).strip()
    return s if s != "" else "n/a"


def _task_sidecar_common(*, task: str, version: str, protocol_name: str) -> dict[str, Any]:
    return {
        "TaskName": task,
        "TaskDescription": (
            f"Behavioral session exported from The Kit protocol '{protocol_name}'."
        ),
        "Instructions": "See protocol documentation for participant instructions.",
        "InstitutionName": _DEFAULT_INSTITUTION,
        "InstitutionAddress": "Toulouse, France",
        "InstitutionalDepartmentName": _DEFAULT_DEPARTMENT,
        "StimulusPresentation": {
            "SoftwareName": "The Kit",
            "SoftwareVersion": version,
        },
        "GeneratedBy": [{"Name": "The Kit", "Version": version}],
    }


def _events_sidecar(*, task: str, version: str, protocol_name: str) -> dict[str, Any]:
    # BIDS: each TSV column is a top-level key in the sidecar (not nested under Columns).
    return {
        **_task_sidecar_common(task=task, version=version, protocol_name=protocol_name),
        "onset": {
            "Description": "Event onset in seconds from session start (first events.jsonl ts_perf).",
            "Units": "s",
        },
        "duration": {
            "Description": (
                "Duration in seconds when a matching *_start / node_start exists; else n/a."
            ),
            "Units": "s",
        },
        "trial_type": {"Description": "Node type or event name"},
        "event": {"Description": "The Kit event name from events.jsonl"},
        "node_id": {"Description": "Protocol node id"},
        "node_index": {"Description": "Node index in protocol"},
        "engine": {"Description": "Engine that ran the node"},
        "timing_mode": {"Description": "standard or low_latency when logged"},
        "stimulus": {"Description": "Stimulus label from event payload if present"},
        "response": {"Description": "Response value from event payload if present"},
        "response_time": {"Description": "Reaction time from payload.rt_ms", "Units": "s"},
        "value": {"Description": "Generic scalar payload (status, label, code, …)"},
        "payload_json": {"Description": "Remaining payload as compact JSON"},
    }


def _beh_sidecar(*, task: str, version: str, protocol_name: str) -> dict[str, Any]:
    return {
        **_task_sidecar_common(task=task, version=version, protocol_name=protocol_name),
        "trial_type": {"Description": "Node type"},
        "node_id": {"Description": "Protocol node id"},
        "node_index": {"Description": "Node index"},
        "node_type": {"Description": "Node type"},
        "stimulus": {"Description": "Stimulus label"},
        "response": {"Description": "Participant response"},
        "response_time": {"Description": "Reaction time", "Units": "s"},
        "engine": {"Description": "Engine that collected the response"},
    }


def _participants_sidecar() -> dict[str, Any]:
    return {
        "participant_id": {"Description": "BIDS participant label (sub-<id>)"},
        "subject_id": {"Description": "Original The Kit subject id"},
        "group": {"Description": "Subject group if provided"},
    }


def _sessions_sidecar() -> dict[str, Any]:
    return {
        "session_id": {"Description": "BIDS session label (ses-<id>)"},
        "session_dir": {"Description": "Original The Kit session folder name"},
        "protocol_name": {"Description": "Protocol name for this session"},
    }


def _dataset_description(*, name: str, version: str) -> dict[str, Any]:
    return {
        "Name": name,
        "BIDSVersion": "1.9.0",
        "DatasetType": "raw",
        "License": _DEFAULT_LICENSE,
        "Authors": list(_DEFAULT_AUTHORS),
        "GeneratedBy": [{"Name": "The Kit", "Version": version}],
    }


def _ensure_readme(bids_root: Path, *, protocol_name: str) -> None:
    path = bids_root / "README"
    if path.exists():
        return
    path.write_text(
        (
            f"The Kit behavioral dataset\n"
            f"==========================\n\n"
            f"Protocol: {protocol_name}\n\n"
            f"This dataset was exported by The Kit (psychophysics orchestrator).\n"
            f"It contains behavioral task events (`*_events.tsv`) and response tables\n"
            f"(`*_beh.tsv`) under `beh/`. Timing uses session-relative onsets from\n"
            f"`events.jsonl` (`ts_perf`).\n\n"
            f"Lab: {_DEFAULT_INSTITUTION}\n"
        ),
        encoding="utf-8",
    )


def _cleanup_legacy_root_files(bids_root: Path) -> None:
    """Remove pre-hierarchy flat files that break the BIDS validator."""
    for pattern in ("sub-*_task-*.tsv", "sub-*_task-*.json"):
        for path in bids_root.glob(pattern):
            if path.is_file():
                path.unlink()


def _write_tsv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        for row in rows:
            cleaned = {k: _na(row.get(k)) for k in fieldnames}
            w.writerow(cleaned)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _build_event_rows(
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, ev in enumerate(events):
        payload = ev.get("payload") or {}
        if not isinstance(payload, dict):
            payload = {}
        rt = payload.get("rt_ms")
        stimulus = payload.get("stimulus", "")
        if stimulus == "" and "condition" in payload:
            stimulus = payload.get("condition", "")
        response = payload.get("response", "")
        rows.append(
            {
                "onset": _onset_seconds(events, ev),
                "duration": _duration_for_event(events, ev, index=i),
                "trial_type": ev.get("node_type") or ev.get("event") or "",
                "event": ev.get("event", ""),
                "node_id": ev.get("node_id", ""),
                "node_index": "" if ev.get("node_index") is None else ev.get("node_index"),
                "engine": ev.get("engine", ""),
                "timing_mode": ev.get("timing_mode", ""),
                "stimulus": "" if stimulus is None else stimulus,
                "response": "" if response is None else response,
                "response_time": (float(rt) / 1000.0) if rt is not None else "n/a",
                "value": _scalar_value(payload),
                "payload_json": _remaining_payload(payload),
            }
        )
    return rows


def _build_beh_rows(
    session_dir: Path,
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    resp_path = session_dir / "responses.csv"
    if not resp_path.exists():
        return []
    with resp_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows_in = list(reader)
    out: list[dict[str, Any]] = []
    for r in rows_in:
        rt = r.get("rt_ms") or ""
        try:
            rt_s = f"{float(rt) / 1000.0:.6f}" if rt != "" else "n/a"
        except ValueError:
            rt_s = "n/a"
        out.append(
            {
                "trial_type": r.get("node_type", ""),
                "node_id": r.get("node_id", ""),
                "node_index": r.get("node_index", ""),
                "node_type": r.get("node_type", ""),
                "stimulus": r.get("stimulus", ""),
                "response": r.get("response", ""),
                "response_time": rt_s,
                "engine": r.get("engine", ""),
            }
        )
    return out


def _ensure_dataset_root(
    bids_root: Path,
    *,
    protocol_name: str,
    version: str,
    force_description: bool = False,
) -> None:
    desc_path = bids_root / "dataset_description.json"
    if force_description or not desc_path.exists():
        _write_json(
            desc_path,
            _dataset_description(name=f"The Kit — {protocol_name}", version=version),
        )
    else:
        # Keep existing Name if present, but enforce allowed DatasetType / Authors / License.
        try:
            existing = json.loads(desc_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            existing = {}
        merged = _dataset_description(
            name=str(existing.get("Name") or f"The Kit — {protocol_name}"),
            version=version,
        )
        if existing.get("Authors"):
            merged["Authors"] = existing["Authors"]
        if existing.get("License"):
            merged["License"] = existing["License"]
        _write_json(desc_path, merged)
    _ensure_readme(bids_root, protocol_name=protocol_name)


def _upsert_participant(
    bids_root: Path,
    *,
    sub_label: str,
    subject_id: str,
    group: str,
    ses_label: str,
    session_dir_name: str,
    protocol_name: str,
) -> None:
    """BIDS: unique participant_id; sessions in ``sub-*/sub-*_sessions.tsv``."""
    participant_id = f"sub-{sub_label}"
    session_id = f"ses-{ses_label}"

    participants_path = bids_root / "participants.tsv"
    part_fields = ["participant_id", "subject_id", "group"]
    part_rows: list[dict[str, str]] = []
    if participants_path.exists():
        with participants_path.open(encoding="utf-8") as f:
            part_rows = list(csv.DictReader(f, delimiter="\t"))
    part_rows = [r for r in part_rows if r.get("participant_id") != participant_id]
    part_rows.append(
        {
            "participant_id": participant_id,
            "subject_id": subject_id,
            "group": group or "n/a",
        }
    )
    part_rows.sort(key=lambda r: r.get("participant_id") or "")
    _write_tsv(participants_path, part_fields, part_rows)
    _write_json(bids_root / "participants.json", _participants_sidecar())

    # Remove legacy root-level sessions.tsv (invalid BIDS location).
    for legacy in ("sessions.tsv", "sessions.json"):
        p = bids_root / legacy
        if p.exists():
            p.unlink()

    sub_dir = bids_root / participant_id
    sub_dir.mkdir(parents=True, exist_ok=True)
    sessions_path = sub_dir / f"{participant_id}_sessions.tsv"
    ses_fields = ["session_id", "session_dir", "protocol_name"]
    ses_rows: list[dict[str, str]] = []
    if sessions_path.exists():
        with sessions_path.open(encoding="utf-8") as f:
            ses_rows = list(csv.DictReader(f, delimiter="\t"))
    ses_rows = [r for r in ses_rows if r.get("session_id") != session_id]
    ses_rows.append(
        {
            "session_id": session_id,
            "session_dir": session_dir_name,
            "protocol_name": protocol_name,
        }
    )
    ses_rows.sort(key=lambda r: r.get("session_id") or "")
    _write_tsv(sessions_path, ses_fields, ses_rows)
    _write_json(sub_dir / f"{participant_id}_sessions.json", _sessions_sidecar())


def export_bids(
    session_dir: str | Path,
    *,
    task_name: str | None = None,
    bids_root: str | Path | None = None,
    ses_id: str | None = None,
) -> Path:
    """
    Export BIDS-like générique sous ``bids_root`` (défaut ``session_dir/bids``) :

    ``sub-<id>/ses-<id>/beh/*_events.tsv`` (+ sidecars) et ``*_beh.tsv``.
    """
    session_dir = Path(session_dir).resolve()
    meta = load_session_meta(session_dir)
    events = load_events(session_dir)
    subject_id = str(meta.get("subject_id", "anonymous"))
    sub_label = _safe_bids_label(subject_id)
    protocol_name = str(meta.get("protocol_name", "thekit"))
    task = _task_label(protocol_name, task_name)
    ses_label = ses_id or _ses_label(session_dir, meta)
    version = str(meta.get("the_kit_version", "?"))

    root = Path(bids_root).resolve() if bids_root else session_dir / "bids"
    root.mkdir(parents=True, exist_ok=True)
    _cleanup_legacy_root_files(root)

    _ensure_dataset_root(root, protocol_name=protocol_name, version=version)
    _upsert_participant(
        root,
        sub_label=sub_label,
        subject_id=subject_id,
        group=str(meta.get("subject_group") or "n/a"),
        ses_label=ses_label,
        session_dir_name=session_dir.name,
        protocol_name=protocol_name,
    )

    beh_dir = root / f"sub-{sub_label}" / f"ses-{ses_label}" / "beh"
    beh_dir.mkdir(parents=True, exist_ok=True)
    stem = f"sub-{sub_label}_ses-{ses_label}_task-{task}"

    event_rows = _build_event_rows(events)
    events_path = beh_dir / f"{stem}_events.tsv"
    _write_tsv(events_path, EVENT_COLUMNS, event_rows)
    _write_json(
        beh_dir / f"{stem}_events.json",
        _events_sidecar(task=task, version=version, protocol_name=protocol_name),
    )

    # Always write beh.tsv: events.tsv requires a corresponding data file in BIDS.
    beh_rows = _build_beh_rows(session_dir, events)
    _write_tsv(beh_dir / f"{stem}_beh.tsv", BEH_COLUMNS, beh_rows)
    _write_json(
        beh_dir / f"{stem}_beh.json",
        _beh_sidecar(task=task, version=version, protocol_name=protocol_name),
    )

    return root


def discover_session_dirs(input_dir: str | Path) -> list[Path]:
    """Dossiers session = sous-dossiers avec session_meta.json + events.jsonl."""
    root = Path(input_dir).resolve()
    if not root.is_dir():
        return []
    found: list[Path] = []
    # direct session
    if (root / "session_meta.json").exists() and (root / "events.jsonl").exists():
        found.append(root)
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        if (child / "session_meta.json").exists() and (child / "events.jsonl").exists():
            found.append(child)
    return found


def export_dataset(
    input_dir: str | Path,
    output_dir: str | Path,
    *,
    task_name: str | None = None,
) -> Path:
    """Agrège plusieurs sessions The Kit dans un dataset BIDS unique."""
    sessions = discover_session_dirs(input_dir)
    if not sessions:
        raise FileNotFoundError(f"Aucune session The Kit trouvée dans {input_dir}")
    out = Path(output_dir).resolve()
    if out.exists():
        # rewrite participants from scratch for a clean aggregate
        for name in (
            "participants.tsv",
            "participants.json",
            "sessions.tsv",
            "sessions.json",
            "dataset_description.json",
            "README",
        ):
            p = out / name
            if p.exists():
                p.unlink()
        _cleanup_legacy_root_files(out)
    out.mkdir(parents=True, exist_ok=True)

    protocol_names: list[str] = []
    versions: list[str] = []
    for sess in sessions:
        meta = load_session_meta(sess)
        protocol_names.append(str(meta.get("protocol_name", "thekit")))
        versions.append(str(meta.get("the_kit_version", "?")))
        export_bids(sess, task_name=task_name, bids_root=out)

    # Refresh dataset_description with aggregate name
    uniq_protocols = sorted(set(protocol_names))
    name = "The Kit dataset" if len(uniq_protocols) > 1 else f"The Kit — {uniq_protocols[0]}"
    version = versions[-1] if versions else "?"
    _write_json(out / "dataset_description.json", _dataset_description(name=name, version=version))
    _ensure_readme(out, protocol_name=", ".join(uniq_protocols))
    return out


def export_html_report(session_dir: str | Path) -> Path:
    session_dir = Path(session_dir).resolve()
    meta = load_session_meta(session_dir)
    events = load_events(session_dir)
    responses_rows: list[dict[str, str]] = []
    resp_path = session_dir / "responses.csv"
    if resp_path.exists():
        with resp_path.open(encoding="utf-8") as f:
            responses_rows = list(csv.DictReader(f))

    counts = Counter(str(ev.get("event") or "") for ev in events)
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
    bids_rel = "bids/" if (session_dir / "bids").is_dir() else ""

    def esc(s: Any) -> str:
        return (
            str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    tr_counts = "".join(
        f"<tr><td>{esc(k)}</td><td>{v}</td></tr>" for k, v in sorted(counts.items())
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
    a {{ color: #7dd3fc; }}
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
    <dt>BIDS</dt><dd>{f'<a href="{esc(bids_rel)}">{esc(bids_rel)}</a>' if bids_rel else '—'}</dd>
  </dl>
  <h2>Compteurs d'événements</h2>
  <table><thead><tr><th>event</th><th>n</th></tr></thead>
  <tbody>{tr_counts or '<tr><td colspan="2">—</td></tr>'}</tbody></table>
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
