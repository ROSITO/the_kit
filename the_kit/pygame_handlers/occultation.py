"""Occultation classique (port simplifié occultation_experiment.py)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from the_kit.logging.session import SessionLogger
    from the_kit.protocol.models import Node


def run_occultation_node(
    node: Node,
    session: SessionLogger,
    *,
    screen,
    clock,
) -> None:
    import pygame

    p = node.params
    w, h = screen.get_size()
    occulter_height = max(4, int(p.get("occulter_height", 56)))
    ball_size = max(1, int(round(occulter_height * 0.9)))
    occ_time = float(p.get("occultation_time", 1.5)) + float(p.get("variation", 0.0))
    speed = float(p.get("ball_speed", 100))
    occ_w = speed * occ_time
    total_t = float(p.get("total_movement_time", 2.0))
    circle_option = int(p.get("circle_option", 0))
    bg = tuple(p.get("background_color", [240, 240, 240]))
    ball_c = tuple(p.get("ball_color", [0, 0, 255]))
    occ_c = tuple(p.get("occulter_color", [200, 200, 200]))
    ball_y = int(p.get("ball_y", h // 2))

    occ_x = w // 2 - int(occ_w) // 2
    occ_y = h // 2 - occulter_height // 2
    occ_rect = pygame.Rect(occ_x, occ_y, int(occ_w), occulter_height)
    reappear_x = occ_x + int(occ_w)
    time_approach = max(0.05, total_t - occ_time)
    start_x = occ_x - speed * time_approach
    time_to_occ = (occ_x - start_x) / speed
    time_to_reappear = time_to_occ + occ_time
    circle_x = occ_x + int(occ_w) // 2
    font = pygame.font.SysFont(None, 28)

    session.log_event(
        "node_start",
        node_id=node.node_id,
        node_type=node.type,
        node_index=node.index,
        engine=node.engine,
        payload={"circle_option": circle_option, "occ_time": occ_time},
    )
    t0 = time.perf_counter()
    ball_x = start_x
    reappeared = False
    response = None
    running = True
    max_s = float(p.get("max_duration_s", 12))

    while running and (time.perf_counter() - t0) < max_s:
        t = time.perf_counter() - t0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif reappeared:
                    if event.key == pygame.K_LEFT:
                        response = "trop_tot"
                        running = False
                    elif event.key == pygame.K_RIGHT:
                        response = "trop_tard"
                        running = False
        if t < time_to_occ:
            ball_x = start_x + speed * t
        elif t < time_to_reappear:
            speed_occ = occ_w / occ_time if occ_time > 0 else speed
            ball_x = occ_x + speed_occ * (t - time_to_occ)
        else:
            ball_x = reappear_x + speed * (t - time_to_reappear)
            reappeared = True

        screen.fill(bg)
        br = ball_size // 2
        behind = (ball_x - br) < reappear_x and (ball_x + br) > occ_x
        if behind:
            pygame.draw.circle(screen, ball_c, (int(ball_x), ball_y), br)
            pygame.draw.rect(screen, occ_c, occ_rect)
        else:
            pygame.draw.rect(screen, occ_c, occ_rect)
            pygame.draw.circle(screen, ball_c, (int(ball_x), ball_y), br)
        if circle_option == 1:
            pygame.draw.circle(screen, (255, 0, 0), (circle_x, ball_y), br)
        elif circle_option == 2:
            pygame.draw.circle(screen, (0, 255, 0), (circle_x, ball_y), br)
        if reappeared and response is None:
            screen.blit(font.render("← trop tôt | trop tard →", True, (0, 0, 0)), (40, 40))
        pygame.display.flip()
        clock.tick(60)

    if response:
        session.log_response(
            node_index=node.index,
            node_type=node.type,
            node_id=node.node_id,
            stimulus="occultation",
            response=response,
            engine=node.engine,
        )
    session.log_event(
        "node_end",
        node_id=node.node_id,
        node_type=node.type,
        node_index=node.index,
        engine=node.engine,
    )
