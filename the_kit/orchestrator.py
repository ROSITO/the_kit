from __future__ import annotations

from pathlib import Path

from the_kit.display.manager import DisplayManager
from the_kit.engines.registry import get_engine
from the_kit.logging.session import SessionLogger
from the_kit.protocol.loader import load_protocol
from the_kit.protocol.models import Node, Protocol
from the_kit.protocol.validator import validate_protocol


def _group_nodes_by_engine(nodes: list[Node]) -> list[tuple[str, list[Node]]]:
    groups: list[tuple[str, list[Node]]] = []
    current_engine: str | None = None
    batch: list[Node] = []
    for node in nodes:
        if current_engine is not None and node.engine != current_engine:
            groups.append((current_engine, batch))
            batch = []
        current_engine = node.engine
        batch.append(node)
    if batch and current_engine:
        groups.append((current_engine, batch))
    return groups


class Orchestrator:
    def __init__(
        self,
        protocol: Protocol,
        session_dir: Path | None = None,
        *,
        dry_run: bool = False,
        project_root: Path | None = None,
        export_artifacts: bool = True,
    ):
        self.protocol = protocol
        self.dry_run = dry_run
        self.project_root = project_root
        base = project_root or Path.cwd()
        if session_dir is None:
            session_dir = SessionLogger.create_default_dir(protocol, base=base / "sessions")
        self.session_dir = session_dir
        from the_kit.io import lsl

        lsl_cfg = protocol.raw.get("lsl")
        lsl_ok, _ = lsl.init_from_config(lsl_cfg if isinstance(lsl_cfg, dict) else None)
        from the_kit.io import nidaqmx_io

        ni_cfg = protocol.raw.get("ni_daq")
        ni_ok, ni_msg = nidaqmx_io.init_from_config(
            ni_cfg if isinstance(ni_cfg, dict) else None,
            dry_run=dry_run,
        )
        if ni_cfg and isinstance(ni_cfg, dict) and ni_cfg.get("enabled", True):
            print(f"NI-DAQ init: ok={ni_ok} msg={ni_msg}")
        self.session = SessionLogger(
            protocol,
            self.session_dir,
            lsl_enabled=lsl_ok,
            export_artifacts=export_artifacts,
        )

    @classmethod
    def from_protocol_file(
        cls,
        path: str | Path,
        *,
        subject_id: str | None = None,
        subject_group: str | None = None,
        session_dir: Path | None = None,
        dry_run: bool = False,
        check_media: bool = False,
        project_root: Path | None = None,
        export_artifacts: bool = True,
    ) -> Orchestrator:
        protocol = load_protocol(
            path, subject_id=subject_id, subject_group=subject_group
        )
        validate_protocol(protocol, check_media=check_media)
        return cls(
            protocol,
            session_dir=session_dir,
            dry_run=dry_run,
            project_root=project_root,
            export_artifacts=export_artifacts,
        )

    def run(self) -> Path:
        display = DisplayManager(self.session)
        prev_engine: str | None = None
        try:
            for _ in range(self.protocol.loop):
                for engine_name, batch in _group_nodes_by_engine(self.protocol.nodes):
                    display.handoff(prev_engine, engine_name)
                    engine_cls = get_engine(engine_name)
                    engine = engine_cls()
                    display.register_cleanup(engine.cleanup)
                    engine.run(
                        self.protocol,
                        self.session,
                        batch,
                        dry_run=self.dry_run,
                    )
                    prev_engine = engine_name
        finally:
            display.shutdown_all()
            self.session.close("completed")
            from the_kit.io import lsl

            lsl.shutdown()
            from the_kit.io import nidaqmx_io

            nidaqmx_io.shutdown()
        return self.session_dir
