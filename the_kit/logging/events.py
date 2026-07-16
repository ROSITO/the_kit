from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any


def perf_now() -> float:
    return time.perf_counter()


def iso_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def build_event(
    event: str,
    *,
    node_id: str | None = None,
    node_type: str | None = None,
    node_index: int | None = None,
    engine: str | None = None,
    timing_mode: str | None = None,
    subject_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "ts_perf": perf_now(),
        "ts_iso": iso_now(),
        "event": event,
    }
    if node_id is not None:
        row["node_id"] = node_id
    if node_type is not None:
        row["node_type"] = node_type
    if node_index is not None:
        row["node_index"] = node_index
    if engine is not None:
        row["engine"] = engine
    if timing_mode is not None:
        row["timing_mode"] = timing_mode
    if subject_id is not None:
        row["subject_id"] = subject_id
    if payload:
        row["payload"] = payload
    return row
