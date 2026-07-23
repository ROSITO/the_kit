from pathlib import Path
import json

from the_kit.cli import build_parser
from the_kit.session_export import (
    discover_session_dirs,
    export_bids,
    export_dataset,
    export_html_report,
    export_session_artifacts,
)

ROOT = Path(__file__).resolve().parents[1]
SESSION = ROOT / "sessions" / "20260522_164848_DEMO3"


def _write_session(sess: Path, *, subject: str = "T1", protocol: str = "demo") -> None:
    sess.mkdir(parents=True, exist_ok=True)
    (sess / "session_meta.json").write_text(
        "{"
        f'"subject_id":"{subject}","protocol_name":"{protocol}","the_kit_version":"0.5.0a0",'
        '"started_at_iso":"2026-01-01T10:00:00","status":"completed","subject_group":"A"'
        "}",
        encoding="utf-8",
    )
    (sess / "events.jsonl").write_text(
        '{"ts_perf":1.0,"event":"session_start","subject_id":"%s"}\n'
        '{"ts_perf":2.0,"event":"node_start","node_id":"n1","node_type":"delay",'
        '"node_index":0,"engine":"qt","timing_mode":"standard","subject_id":"%s"}\n'
        '{"ts_perf":2.5,"event":"gvs_trial_start","node_id":"n1","node_type":"neuroconn_gvs",'
        '"node_index":0,"engine":"pygame","subject_id":"%s",'
        '"payload":{"trial":0,"condition":"AP"}}\n'
        '{"ts_perf":3.5,"event":"gvs_trial_end","node_id":"n1","node_type":"neuroconn_gvs",'
        '"node_index":0,"engine":"pygame","subject_id":"%s",'
        '"payload":{"trial":0,"condition":"AP","response":"AP","rt_ms":320,'
        '"stimulus":"AP","extra":{"stim_duration_ms":10000}}}\n'
        '{"ts_perf":4.0,"event":"node_end","node_id":"n1","node_type":"delay",'
        '"node_index":0,"engine":"qt","subject_id":"%s"}\n'
        '{"ts_perf":5.0,"event":"session_end","subject_id":"%s",'
        '"payload":{"status":"completed"}}\n'
        % (subject, subject, subject, subject, subject, subject),
        encoding="utf-8",
    )
    (sess / "responses.csv").write_text(
        "timestamp_iso,timestamp_ms,subject_id,node_index,node_type,node_id,"
        "stimulus,response,rt_ms,engine\n"
        f"2026-01-01T10:00:03,3000,{subject},0,neuroconn_gvs,n1,AP,AP,320,pygame\n",
        encoding="utf-8",
    )


def test_export_bids_hierarchy(tmp_path: Path):
    sess = tmp_path / "20260101_100000_T1"
    _write_session(sess)
    bids = export_bids(sess, task_name="demo")
    desc = json.loads((bids / "dataset_description.json").read_text(encoding="utf-8"))
    assert desc["DatasetType"] == "raw"
    assert desc["Authors"]
    assert desc["License"]
    assert (bids / "README").exists()
    assert (bids / "participants.tsv").exists()
    assert (bids / "participants.json").exists()
    assert (bids / "sessions.tsv").exists() is False
    parts = (bids / "participants.tsv").read_text(encoding="utf-8").strip().splitlines()
    assert len(parts) == 2  # header + unique subject
    assert "session_id" not in parts[0]
    sub_sessions = bids / "sub-T1" / "sub-T1_sessions.tsv"
    assert sub_sessions.exists()
    ses_header = sub_sessions.read_text(encoding="utf-8").splitlines()[0]
    assert ses_header.startswith("session_id")
    assert "session_dir" in ses_header
    assert (bids / "sub-T1" / "sub-T1_sessions.json").exists()
    beh = bids / "sub-T1" / "ses-20260101100000" / "beh"
    assert beh.is_dir()
    events = list(beh.glob("*_events.tsv"))
    assert len(events) == 1
    events_json = beh / events[0].name.replace("_events.tsv", "_events.json")
    assert events_json.exists()
    sidecar = json.loads(events_json.read_text(encoding="utf-8"))
    assert "Columns" not in sidecar
    assert "event" in sidecar and "Description" in sidecar["event"]
    assert "TaskDescription" in sidecar
    text = events[0].read_text(encoding="utf-8")
    assert "onset" in text
    assert "payload_json" in text
    assert "gvs_trial_end" in text
    # duration for node_end and gvs_trial_end
    lines = text.strip().splitlines()
    header = lines[0].split("\t")
    dur_i = header.index("duration")
    by_event = {row.split("\t")[header.index("event")]: row.split("\t") for row in lines[1:]}
    assert by_event["node_end"][dur_i] == "2.0"
    assert by_event["gvs_trial_end"][dur_i] == "1.0"
    assert by_event["session_start"][dur_i] == "n/a"
    beh_tsv = list(beh.glob("*_beh.tsv"))
    assert len(beh_tsv) == 1
    beh_header = beh_tsv[0].read_text(encoding="utf-8").splitlines()[0]
    assert "response_time" in beh_header
    assert "onset" not in beh_header.split("\t")
    assert "duration" not in beh_header.split("\t")


def test_export_html_report_counts(tmp_path: Path):
    sess = tmp_path / "20260101_100000_T1"
    _write_session(sess)
    export_bids(sess)
    report = export_html_report(sess)
    html = report.read_text(encoding="utf-8")
    assert "Compteurs d'événements" in html
    assert "gvs_trial_end" in html
    assert 'href="bids/"' in html


def test_export_session_artifacts(tmp_path: Path):
    sess = tmp_path / "20260101_100000_T1"
    _write_session(sess)
    paths = export_session_artifacts(sess)
    assert paths["bids"].is_dir()
    assert paths["report"].is_file()


def test_run_cli_exports_bids_by_default():
    parser = build_parser()
    args = parser.parse_args(
        ["run", "-p", "examples/demo_phase3/protocol.json", "-s", "S001"]
    )
    assert args.export_session is True
    args_off = parser.parse_args(
        [
            "run",
            "-p",
            "examples/demo_phase3/protocol.json",
            "-s",
            "S001",
            "--no-export-session",
        ]
    )
    assert args_off.export_session is False


def test_export_bids_empty_responses_still_valid(tmp_path: Path):
    """Toute session The Kit doit produire un BIDS complet même sans réponses."""
    sess = tmp_path / "20260101_100000_NR"
    sess.mkdir(parents=True)
    (sess / "session_meta.json").write_text(
        '{"subject_id":"NR","protocol_name":"blank","the_kit_version":"0.5.0a0",'
        '"started_at_iso":"2026-01-01T10:00:00","status":"completed"}',
        encoding="utf-8",
    )
    (sess / "events.jsonl").write_text(
        '{"ts_perf":1.0,"event":"session_start","subject_id":"NR"}\n'
        '{"ts_perf":2.0,"event":"session_end","subject_id":"NR",'
        '"payload":{"status":"completed"}}\n',
        encoding="utf-8",
    )
    (sess / "responses.csv").write_text(
        "timestamp_iso,timestamp_ms,subject_id,node_index,node_type,node_id,"
        "stimulus,response,rt_ms,engine\n",
        encoding="utf-8",
    )
    bids = export_bids(sess)
    desc = json.loads((bids / "dataset_description.json").read_text(encoding="utf-8"))
    assert desc["DatasetType"] == "raw"
    assert (bids / "README").exists()
    beh = list((bids / "sub-NR").glob("ses-*/beh/*_events.tsv"))
    assert len(beh) == 1
    assert list((bids / "sub-NR").glob("ses-*/beh/*_beh.tsv"))
    assert (bids / "sub-NR" / "sub-NR_sessions.tsv").exists()


def test_export_dataset_multi_session(tmp_path: Path):
    sessions = tmp_path / "sessions"
    _write_session(sessions / "20260101_100000_S01", subject="S01", protocol="demo")
    _write_session(sessions / "20260102_110000_S02", subject="S02", protocol="demo")
    out = tmp_path / "bids_dataset"
    root = export_dataset(sessions, out, task_name="demo")
    assert root == out.resolve()
    parts = (out / "participants.tsv").read_text(encoding="utf-8").strip().splitlines()
    assert len(parts) == 3  # header + 2
    assert (out / "sub-S01" / "ses-20260101100000" / "beh").is_dir()
    assert (out / "sub-S02" / "ses-20260102110000" / "beh").is_dir()


def test_discover_session_dirs(tmp_path: Path):
    sessions = tmp_path / "sessions"
    _write_session(sessions / "a", subject="A")
    (sessions / "noise").mkdir()
    found = discover_session_dirs(sessions)
    assert len(found) == 1


def test_export_dataset_command_registered():
    parser = build_parser()
    args = parser.parse_args(["export-dataset", "-i", "sessions", "-o", "out"])
    assert args.command == "export-dataset"


def test_export_bids_from_demo_session():
    if not SESSION.exists():
        return
    bids = export_bids(SESSION, task_name="demo")
    assert (bids / "participants.tsv").exists()
    assert list(bids.glob("sub-*/ses-*/beh/*_events.tsv"))
