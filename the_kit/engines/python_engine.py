from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING

from the_kit.engines.base import EngineBase
from the_kit.task_api import NodeResult, TaskContext

if TYPE_CHECKING:
    from the_kit.logging.session import SessionLogger
    from the_kit.protocol.models import Node, Protocol


class PythonEngine(EngineBase):
    name = "python"

    @classmethod
    def check_available(cls) -> tuple[bool, str]:
        return True, "ok"

    def run(
        self,
        protocol: Protocol,
        session: SessionLogger,
        nodes: list[Node],
        *,
        dry_run: bool = False,
    ) -> None:
        for node in nodes:
            if node.type == "ni_stim":
                self._run_ni_stim(node, protocol, session, dry_run=dry_run)
                continue
            if node.type != "python_task":
                session.log_event(
                    "error",
                    node_id=node.node_id,
                    payload={"message": f"type non supporté par python: {node.type}"},
                )
                continue
            self._run_python_task(node, protocol, session, dry_run=dry_run)

    def _run_ni_stim(
        self,
        node: Node,
        protocol: Protocol,
        session: SessionLogger,
        *,
        dry_run: bool,
    ) -> None:
        from the_kit.io import nidaqmx_io

        p = node.params
        session.log_event(
            "node_start",
            node_id=node.node_id,
            node_type=node.type,
            node_index=node.index,
            engine=node.engine,
        )
        mode = str(p.get("mode", "square_wave")).lower()
        try:
            if mode == "scalar":
                nidaqmx_io.send_voltage_pulse(
                    int(p.get("channel_index", 0)),
                    float(p.get("voltage", 5.0)),
                    duration_s=float(p.get("duration_s", 0.1)),
                    dry_run=dry_run,
                )
                payload = {"mode": "scalar", "voltage": p.get("voltage")}
            else:
                payload = nidaqmx_io.send_square_wave_stim(
                    direction=str(p.get("direction", "AP")),
                    amplitude=float(p.get("amplitude", 1.0)),
                    frequency=float(p.get("frequency", 0.278)),
                    duration_s=float(p.get("duration_s", 3.6)),
                    sampling_rate=p.get("rate"),
                    dry_run=dry_run,
                )
            session.log_event(
                "ni_stim",
                node_id=node.node_id,
                node_type=node.type,
                node_index=node.index,
                engine=node.engine,
                payload=payload,
            )
        except Exception as exc:
            session.log_event(
                "error",
                node_id=node.node_id,
                payload={"message": str(exc), "ni_stim": True},
            )
            raise
        session.log_event(
            "node_end",
            node_id=node.node_id,
            node_type=node.type,
            node_index=node.index,
            engine=node.engine,
        )

    def _run_python_task(
        self,
        node: Node,
        protocol: Protocol,
        session: SessionLogger,
        *,
        dry_run: bool,
    ) -> None:
        script_cfg = node.params.get("script") or node.raw.get("script") or {}
        rel = script_cfg.get("file") or node.params.get("file")
        if not rel:
            raise ValueError(f"python_task {node.node_id}: script.file manquant")
        path = (protocol.root / rel).resolve()
        if ".." in Path(rel).parts:
            raise ValueError(f"Chemin script non autorisé: {rel}")
        if not path.exists():
            raise FileNotFoundError(f"Script introuvable: {path}")

        spec = importlib.util.spec_from_file_location(f"the_kit_script_{node.node_id}", path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Impossible de charger {path}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        ctx = TaskContext(protocol, node, session, dry_run=dry_run)
        session.log_event(
            "node_start",
            node_id=node.node_id,
            node_type=node.type,
            node_index=node.index,
            engine=node.engine,
        )

        prepare_name = script_cfg.get("prepare", "prepare")
        run_name = script_cfg.get("run", "run")
        if hasattr(mod, prepare_name):
            getattr(mod, prepare_name)(ctx)
        result = None
        if hasattr(mod, run_name):
            result = getattr(mod, run_name)(ctx)
        if isinstance(result, NodeResult):
            for q, a in result.responses.items():
                session.log_response(
                    node_index=node.index,
                    node_type=node.type,
                    node_id=node.node_id,
                    stimulus=node.node_id,
                    response=f"{q}: {a}",
                    rt_ms=result.rt_ms,
                    engine=node.engine,
                )
        if ctx.variables:
            session.log_event(
                "python_variables",
                node_id=node.node_id,
                payload={"variables": dict(ctx.variables)},
            )
        session.log_event(
            "node_end",
            node_id=node.node_id,
            node_type=node.type,
            node_index=node.index,
            engine=node.engine,
        )

    def cleanup(self) -> None:
        pass
