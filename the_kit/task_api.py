from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from the_kit.logging.session import SessionLogger
    from the_kit.protocol.models import Node, Protocol


@dataclass
class NodeResult:
    status: str = "ok"
    data: dict[str, Any] = field(default_factory=dict)
    responses: dict[str, str] = field(default_factory=dict)
    rt_ms: int | None = None


class TaskContext:
    """API exposée aux scripts `python_task` (type OpenSesame)."""

    def __init__(
        self,
        protocol: Protocol,
        node: Node,
        session: SessionLogger,
        *,
        dry_run: bool = False,
    ):
        self.protocol = protocol
        self.node = node
        self.session = session
        self.dry_run = dry_run
        self.variables: dict[str, Any] = {}
        self._protocol_root = protocol.root

    @property
    def subject_id(self) -> str:
        return self.protocol.subject.id

    @property
    def protocol_root(self) -> Path:
        return self._protocol_root

    class _Log:
        def __init__(self, session: SessionLogger, node: Node):
            self._session = session
            self._node = node

        def event(self, name: str, **payload: Any) -> None:
            self._session.log_event(
                name,
                node_id=self._node.node_id,
                node_type=self._node.type,
                node_index=self._node.index,
                engine=self._node.engine,
                payload=payload or None,
            )

        def marker(self, code: str, t_perf: float | None = None) -> None:
            self.event("marker", code=code, t_perf=t_perf)

    @property
    def log(self) -> _Log:
        return self._Log(self.session, self.node)

    def trigger_serial(self, port: str, value: int) -> None:
        from the_kit.io.serial_trigger import send_serial_trigger

        send_serial_trigger(port, value, dry_run=self.dry_run)
        self.log.event("trigger", port=port, value=value, dry_run=self.dry_run)

    def lsl_marker(self, code: float, *, label: str = "") -> None:
        from the_kit.io import lsl

        lsl.push_marker(code, label=label)
        self.log.event("lsl_marker", code=code, label=label)

    def ni_square_wave(
        self,
        *,
        direction: str = "AP",
        amplitude: float = 1.0,
        frequency: float = 0.278,
        duration_s: float = 3.6,
    ) -> dict:
        from the_kit.io import nidaqmx_io

        meta = nidaqmx_io.send_square_wave_stim(
            direction=direction,
            amplitude=amplitude,
            frequency=frequency,
            duration_s=duration_s,
            dry_run=self.dry_run,
        )
        self.log.event("ni_stim", **meta)
        return meta

    def eyelink_message(self, text: str) -> None:
        from the_kit.io import eyelink

        tracker = eyelink.get_tracker()
        if tracker is not None:
            eyelink.send_message(tracker, text)
        self.log.event("eyelink_message", text=text)
