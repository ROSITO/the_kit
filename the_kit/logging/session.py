from __future__ import annotations

import csv
import hashlib
import json
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from the_kit import __version__
from the_kit.logging.events import build_event, iso_now, perf_now
from the_kit.environment import write_environment
from the_kit.protocol.models import Protocol


RESPONSE_COLUMNS = [
    "timestamp_iso",
    "timestamp_ms",
    "subject_id",
    "node_index",
    "node_type",
    "node_id",
    "stimulus",
    "response",
    "rt_ms",
    "engine",
]


class SessionLogger:
    def __init__(
        self,
        protocol: Protocol,
        session_dir: Path,
        *,
        lsl_enabled: bool = False,
        export_artifacts: bool = True,
    ):
        self.protocol = protocol
        self.session_dir = session_dir
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.subject_id = protocol.subject.id
        self._session_start_perf = perf_now()
        self._session_start_wall = time.time()
        self.events_path = session_dir / "events.jsonl"
        self.responses_path = session_dir / "responses.csv"
        self._events_file = self.events_path.open("a", encoding="utf-8")
        self._lsl_enabled = lsl_enabled
        self._export_artifacts = export_artifacts
        self._init_responses_csv()
        self._write_session_meta()

    def _init_responses_csv(self) -> None:
        with self.responses_path.open("w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=RESPONSE_COLUMNS).writeheader()

    def _write_session_meta(self) -> None:
        meta = {
            "the_kit_version": __version__,
            "protocol_version": self.protocol.protocol_version,
            "protocol_name": self.protocol.name,
            "protocol_path": str(self.protocol.path),
            "protocol_hash": self._hash_file(self.protocol.path),
            "subject_id": self.subject_id,
            "subject_group": self.protocol.subject.group,
            "started_at_iso": iso_now(),
        }
        (self.session_dir / "session_meta.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        shutil.copy2(self.protocol.path, self.session_dir / "protocol_executed.json")
        write_environment(self.protocol, self.session_dir)

    @staticmethod
    def _hash_file(path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()[:16]

    def log_event(
        self,
        event: str,
        *,
        node_id: str | None = None,
        node_type: str | None = None,
        node_index: int | None = None,
        engine: str | None = None,
        timing_mode: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        row = build_event(
            event,
            node_id=node_id,
            node_type=node_type,
            node_index=node_index,
            engine=engine,
            timing_mode=timing_mode,
            subject_id=self.subject_id,
            payload=payload,
        )
        self._events_file.write(json.dumps(row, ensure_ascii=False) + "\n")
        self._events_file.flush()
        if self._lsl_enabled:
            from the_kit.io import lsl

            if lsl.auto_markers_enabled():
                lsl.push_marker(lsl.marker_for_event(event), label=node_id or event)

    def log_response(
        self,
        *,
        node_index: int,
        node_type: str,
        node_id: str,
        stimulus: str,
        response: str,
        rt_ms: int | None = None,
        engine: str = "qt",
    ) -> None:
        now = datetime.now(timezone.utc).astimezone()
        ts_ms = int((time.time() - self._session_start_wall) * 1000)
        row = {
            "timestamp_iso": now.isoformat(),
            "timestamp_ms": ts_ms,
            "subject_id": self.subject_id,
            "node_index": node_index,
            "node_type": node_type,
            "node_id": node_id,
            "stimulus": stimulus,
            "response": response,
            "rt_ms": rt_ms if rt_ms is not None else "",
            "engine": engine,
        }
        with self.responses_path.open("a", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=RESPONSE_COLUMNS).writerow(row)
        self.log_event(
            "response",
            node_id=node_id,
            node_type=node_type,
            node_index=node_index,
            engine=engine,
            payload={"stimulus": stimulus, "response": response, "rt_ms": rt_ms},
        )

    def close(self, status: str = "completed") -> None:
        if getattr(self, "_closed", False):
            return
        self._closed = True
        self.log_event("session_end", payload={"status": status})
        self._events_file.close()
        ended = {
            "ended_at_iso": iso_now(),
            "duration_s": round(perf_now() - self._session_start_perf, 3),
            "status": status,
        }
        meta_path = self.session_dir / "session_meta.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta.update(ended)
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        if self._export_artifacts:
            try:
                from the_kit.session_export import export_session_artifacts

                paths = export_session_artifacts(self.session_dir)
                bids = paths.get("bids")
                report = paths.get("report")
                if bids is not None:
                    print(f"BIDS: {bids}")
                if report is not None:
                    print(f"report: {report}")
            except Exception as exc:
                # Ne pas perdre la session si l'export échoue ; signaler clairement.
                print(f"[export] Échec export BIDS/rapport: {exc}")

    @classmethod
    def create_default_dir(
        cls, protocol: Protocol, base: Path | None = None
    ) -> Path:
        base = Path(base) if base is not None else Path.cwd() / "sessions"
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_subject = "".join(c if c.isalnum() or c in "-_" else "_" for c in protocol.subject.id)
        return base / f"{stamp}_{safe_subject}"
