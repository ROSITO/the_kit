"""
Bloc GVS NeuroConn + fNIRS — rampe 10 s, réponse manette, ITI jitteré.

50 essais (10 × 5 conditions), ordre aléatoire.
"""

from __future__ import annotations

import random
import threading
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from the_kit.logging.session import SessionLogger
    from the_kit.protocol.models import Node

GVS_CONDITIONS = ("AP", "PA", "LATD", "LATG", "CONTROL")


def _build_trial_list(reps: int, seed: int | None) -> list[str]:
    trials = [c for c in GVS_CONDITIONS for _ in range(reps)]
    rng = random.Random(seed)
    rng.shuffle(trials)
    return trials


def _iti_duration_s(base: float, jitter: tuple[float, float], rng: random.Random) -> float:
    lo, hi = jitter
    return base + rng.uniform(lo, hi)


def run_neuroconn_gvs_node(
    node: Node,
    session: SessionLogger,
    *,
    screen,
    clock,
) -> None:
    import pygame

    from the_kit.io import gvs_lsl, nidaqmx_io
    from the_kit.io.gamepad import direction_label, init_joystick, poll_direction

    p = node.params
    amplitude = float(p.get("amplitude", 1.2))
    reps = int(p.get("repetitions_per_condition", 10))
    rise_s = float(p.get("rise_s", 3.0))
    plateau_s = float(p.get("plateau_s", 4.0))
    fall_s = float(p.get("fall_s", 3.0))
    iti_base = float(p.get("iti_base_s", 10.0))
    iti_jitter = tuple(p.get("iti_jitter_s", [1.0, 5.0]))
    seed = p.get("random_seed")
    rng = random.Random(seed)

    trials = _build_trial_list(reps, seed)
    ramp_duration_s = rise_s + plateau_s + fall_s

    session.log_event(
        "node_start",
        node_id=node.node_id,
        node_type=node.type,
        node_index=node.index,
        engine=node.engine,
        payload={
            "trials": len(trials),
            "amplitude": amplitude,
            "conditions": list(GVS_CONDITIONS),
        },
    )
    gvs_lsl.push(gvs_lsl.GVS_BLOCK_START, label="gvs_block_start")

    init_joystick()
    font = pygame.font.SysFont(None, 28)
    w, h = screen.get_size()

    for trial_i, condition in enumerate(trials):
        session.log_event(
            "gvs_trial_start",
            node_id=node.node_id,
            node_type=node.type,
            node_index=node.index,
            engine=node.engine,
            payload={"trial": trial_i, "condition": condition},
        )

        stim_meta: dict[str, Any] = {}
        stim_error: list[Exception] = []

        def _run_stim() -> None:
            try:
                gvs_lsl.stim_onset(condition)
                stim_meta.update(
                    nidaqmx_io.send_ramp_stim(
                        direction=condition,
                        amplitude=amplitude,
                        rise_s=rise_s,
                        plateau_s=plateau_s,
                        fall_s=fall_s,
                    )
                )
            except Exception as exc:
                stim_error.append(exc)

        stim_t0 = time.perf_counter()
        stim_thread = threading.Thread(target=_run_stim, daemon=True)
        response_dir: str | None = None
        stim_thread.start()

        while True:
            clock.tick(60)
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT or (
                    event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
                ):
                    gvs_lsl.push(gvs_lsl.GVS_BLOCK_END, label="aborted")
                    session.log_event(
                        "node_end",
                        node_id=node.node_id,
                        node_type=node.type,
                        node_index=node.index,
                        engine=node.engine,
                        payload={"aborted": True, "trial": trial_i},
                    )
                    return

            if response_dir is None:
                response_dir = poll_direction(events=events)

            screen.fill((0, 0, 0))
            cx, cy = w // 2, h // 2
            pygame.draw.line(screen, (200, 200, 200), (cx - 12, cy), (cx + 12, cy), 2)
            pygame.draw.line(screen, (200, 200, 200), (cx, cy - 12), (cx, cy + 12), 2)
            label = font.render(
                f"Essai {trial_i + 1}/{len(trials)} — {direction_label(condition)}",
                True,
                (160, 160, 160),
            )
            screen.blit(label, (20, 20))
            if response_dir:
                hint = font.render(
                    f"Réponse : {direction_label(response_dir)}",
                    True,
                    (120, 220, 120),
                )
                screen.blit(hint, (20, 50))
            else:
                hint = font.render("Flèches manette / clavier", True, (100, 100, 100))
                screen.blit(hint, (20, 50))
            pygame.display.flip()

            stim_thread.join(timeout=0)
            if stim_error:
                raise stim_error[0]
            if not stim_thread.is_alive() and response_dir is not None:
                break

        rt_ms = int((time.perf_counter() - stim_t0) * 1000)
        correct = None if condition == "CONTROL" else response_dir == condition
        gvs_lsl.response_perceived(response_dir or "?", correct=correct)
        session.log_response(
            node_index=node.index,
            node_type=node.type,
            node_id=node.node_id,
            stimulus=condition,
            response=response_dir or "",
            rt_ms=rt_ms,
            engine=node.engine,
        )
        session.log_event(
            "gvs_trial_end",
            node_id=node.node_id,
            node_type=node.type,
            node_index=node.index,
            engine=node.engine,
            payload={
                "trial": trial_i,
                "condition": condition,
                "response": response_dir,
                "rt_ms": rt_ms,
                "correct": correct,
                "stim": stim_meta,
            },
        )

        if trial_i < len(trials) - 1:
            iti = _iti_duration_s(iti_base, iti_jitter, rng)
            iti_end = time.perf_counter() + iti
            while time.perf_counter() < iti_end:
                clock.tick(60)
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        return
                screen.fill((0, 0, 0))
                pygame.display.flip()

    gvs_lsl.push(gvs_lsl.GVS_BLOCK_END, label="gvs_block_end")
    session.log_event(
        "node_end",
        node_id=node.node_id,
        node_type=node.type,
        node_index=node.index,
        engine=node.engine,
        payload={"trials_completed": len(trials)},
    )
