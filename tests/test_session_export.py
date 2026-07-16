from pathlib import Path

from the_kit.session_export import export_bids, export_html_report, export_session_artifacts

ROOT = Path(__file__).resolve().parents[1]
SESSION = ROOT / "sessions" / "20260522_164848_DEMO3"


def test_export_bids_from_demo_session():
    if not SESSION.exists():
        return
    bids = export_bids(SESSION, task_name="demo")
    assert (bids / "participants.tsv").exists()
    events = list(bids.glob("*_events.tsv"))
    assert events


def test_export_html_report():
    if not SESSION.exists():
        return
    report = export_html_report(SESSION)
    assert report.name == "session_report.html"
    assert "Rapport session" in report.read_text(encoding="utf-8")


def test_export_session_artifacts(tmp_path):
    sess = tmp_path / "sess"
    sess.mkdir()
    (sess / "session_meta.json").write_text(
        '{"subject_id":"T1","protocol_name":"t","the_kit_version":"0.5.0a0",'
        '"started_at_iso":"2026-01-01T00:00:00","status":"completed"}',
        encoding="utf-8",
    )
    (sess / "events.jsonl").write_text(
        '{"ts_perf":1.0,"event":"session_start","subject_id":"T1"}\n'
        '{"ts_perf":2.0,"event":"node_start","node_id":"n1","node_type":"delay",'
        '"node_index":0,"engine":"qt","subject_id":"T1"}\n'
        '{"ts_perf":3.0,"event":"node_end","node_id":"n1","node_type":"delay",'
        '"node_index":0,"engine":"qt","subject_id":"T1"}\n'
        '{"ts_perf":4.0,"event":"session_end","subject_id":"T1",'
        '"payload":{"status":"completed"}}\n',
        encoding="utf-8",
    )
    (sess / "responses.csv").write_text(
        "timestamp_iso,timestamp_ms,subject_id,node_index,node_type,node_id,"
        "stimulus,response,rt_ms,engine\n",
        encoding="utf-8",
    )
    paths = export_session_artifacts(sess)
    assert paths["bids"].is_dir()
    assert paths["report"].is_file()
