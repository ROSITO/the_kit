"""Nœud composable : fond (background) + calques stimuli."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from the_kit.pygame_handlers.scene.backgrounds import create_background
from the_kit.pygame_handlers.scene.context import SceneContext
from the_kit.pygame_handlers.scene.stimuli import create_stimulus

if TYPE_CHECKING:
    from the_kit.logging.session import SessionLogger
    from the_kit.protocol.models import Node


def _parse_stimuli_list(params: dict[str, Any]) -> list[dict[str, Any]]:
    raw = params.get("stimuli") or params.get("layers") or []
    if not raw:
        return []
    if isinstance(raw, dict):
        return [raw]
    return list(raw)


def run_pygame_scene_node(
    node: Node,
    session: SessionLogger,
    *,
    screen,
    clock,
) -> None:
    import pygame

    p = node.params
    w, h = screen.get_size()
    bg_name = p.get("background") or p.get("scene") or "plain"
    bg_params = dict(p.get("background_params") or p.get("scene_params") or {})
    if bg_name in ("shadow_corridor", "shadow") and not bg_params:
        bg_params = {k: v for k, v in p.items() if k not in ("background", "scene", "stimuli", "layers", "duration_s")}

    duration_s = float(p.get("duration_s", 0))
    max_s = float(p.get("max_duration_s", duration_s or 300))

    ctx = SceneContext(
        node=node,
        session=session,
        screen=screen,
        clock=clock,
        width=w,
        height=h,
    )

    background = create_background(str(bg_name))
    background.setup(ctx, bg_params)

    stimuli_specs = _parse_stimuli_list(p)
    stimuli = []
    for spec in stimuli_specs:
        stype = spec.get("type") or spec.get("stimulus")
        if not stype:
            continue
        st = create_stimulus(str(stype))
        st.setup(ctx, spec.get("params", spec))
        stimuli.append(st)

    session.log_event(
        "node_start",
        node_id=node.node_id,
        node_type=node.type,
        node_index=node.index,
        engine=node.engine,
        payload={
            "background": bg_name,
            "stimuli": [s.get("type", s.get("stimulus")) for s in stimuli_specs],
        },
    )

    t0 = time.perf_counter()
    running = True
    while running and (time.perf_counter() - t0) < max_s:
        dt = clock.tick(60) / 1000.0
        ctx.elapsed_s = time.perf_counter() - t0

        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            ):
                session.log_event(
                    "node_end",
                    node_id=node.node_id,
                    node_type=node.type,
                    node_index=node.index,
                    engine=node.engine,
                    payload={"aborted": True},
                )
                return

        for st in stimuli:
            st.update(ctx, dt)

        background.draw(ctx)
        for st in stimuli:
            st.draw(ctx)
        pygame.display.flip()

        if duration_s > 0 and ctx.elapsed_s >= duration_s:
            break
        if stimuli and all(s.finished() for s in stimuli):
            break

    session.log_event(
        "node_end",
        node_id=node.node_id,
        node_type=node.type,
        node_index=node.index,
        engine=node.engine,
        payload={"elapsed_s": round(ctx.elapsed_s, 3), "background": bg_name},
    )
