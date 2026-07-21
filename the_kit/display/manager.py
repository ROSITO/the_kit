from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from the_kit.logging.session import SessionLogger


class DisplayManager:
    """Handoff entre moteurs d'affichage (fermeture / pause inter-nœud)."""

    def __init__(self, session: SessionLogger, *, blank_ms: int = 300):
        self.session = session
        self.blank_ms = blank_ms
        self._last_engine: str | None = None
        self._cleanup_callbacks: list = []

    def register_cleanup(self, callback) -> None:
        self._cleanup_callbacks.append(callback)

    def handoff(self, from_engine: str | None, to_engine: str) -> None:
        if from_engine is not None and from_engine != to_engine:
            self.session.log_event(
                "engine_handoff",
                payload={"from": from_engine, "to": to_engine},
            )
            self._run_cleanups()
            time.sleep(self.blank_ms / 1000.0)
        self._last_engine = to_engine

    def _run_cleanups(self) -> None:
        for cb in self._cleanup_callbacks:
            try:
                cb()
            except Exception as exc:
                self.session.log_event("error", payload={"handoff_cleanup": str(exc)})
        self._cleanup_callbacks.clear()

    def shutdown_all(self) -> None:
        self._run_cleanups()
