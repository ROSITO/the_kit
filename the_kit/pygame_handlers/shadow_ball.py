"""Nœud shadow_ball — corridor perspective (shadowi)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from the_kit.pygame_handlers.shadow_ball_scene import (
    MODE_NAMES,
    ShadowBallScene,
    TRIAL_FIXATION,
    TRIAL_MOTION,
)

if TYPE_CHECKING:
    from the_kit.logging.session import SessionLogger
    from the_kit.protocol.models import Node


def run_shadow_ball_node(
    node: Node,
    session: SessionLogger,
    *,
    screen,
    clock,
) -> None:
    import pygame

    p = node.params
    mode_name = str(p.get("shadow_mode", "congruent"))
    fix_s = float(p.get("fixation_duration_s", 3.0))
    traverse_s = float(p.get("ball_traverse_time_s", 1.0))
    max_s = float(
        p.get(
            "max_duration_s",
            fix_s * 2 + traverse_s * 8 + 5,
        )
    )

    w, h = screen.get_size()
    scene = ShadowBallScene(w, h, p)
    scene.begin()

    session.log_event(
        "node_start",
        node_id=node.node_id,
        node_type=node.type,
        node_index=node.index,
        engine=node.engine,
        payload={
            "shadow_mode": mode_name,
            "run_baseline_pair": scene.run_baseline_pair,
            "room_depth": scene.room_depth,
        },
    )

    t0 = time.perf_counter()
    last_phase = -1

    while (time.perf_counter() - t0) < max_s:
        dt = clock.tick(60) / 1000.0
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

        state = scene.update(dt)
        if state.phase != last_phase:
            last_phase = state.phase
            phase_name = "fixation" if state.phase == TRIAL_FIXATION else "motion"
            session.log_event(
                "shadow_ball_phase",
                node_id=node.node_id,
                node_type=node.type,
                node_index=node.index,
                engine=node.engine,
                payload={
                    "phase": phase_name,
                    "shadow_mode": _mode_label(state.shadow_mode),
                    "baseline_subphase": state.baseline_subphase,
                },
            )

        scene.draw(screen)
        pygame.display.flip()

        if state.done:
            break

    session.log_event(
        "node_end",
        node_id=node.node_id,
        node_type=node.type,
        node_index=node.index,
        engine=node.engine,
        payload={
            "crossings": state.center_crossings,
            "shadow_mode": mode_name,
            "condition_mode": _mode_label(scene.condition_mode),
        },
    )


def _mode_label(mode_id: int) -> str:
    for name, mid in MODE_NAMES.items():
        if mid == mode_id:
            return name
    return "unknown"
