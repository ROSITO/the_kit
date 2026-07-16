"""Multiple object tracking simplifié (inspiré MOT.py)."""

from __future__ import annotations

import random
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from the_kit.logging.session import SessionLogger
    from the_kit.protocol.models import Node


class _Ball:
    __slots__ = ("x", "y", "vx", "vy", "r", "color")

    def __init__(self, x, y, vx, vy, r):
        self.x, self.y, self.vx, self.vy, self.r = x, y, vx, vy, r
        self.color = (random.randint(80, 255), random.randint(80, 255), 200)


def run_mot_node(
    node: Node,
    session: SessionLogger,
    *,
    screen,
    clock,
) -> None:
    import pygame

    p = node.params
    w, h = screen.get_size()
    n = int(p.get("num_balls", 8))
    speed = float(p.get("uniform_speed", 3.0))
    kh_r = float(p.get("keyhole_radius", 120))
    duration_s = float(p.get("duration_s", 20))

    session.log_event(
        "node_start",
        node_id=node.node_id,
        node_type=node.type,
        node_index=node.index,
        engine=node.engine,
    )
    balls = [
        _Ball(
            random.uniform(50, w - 50),
            random.uniform(50, h - 50),
            random.uniform(-speed, speed),
            random.uniform(-speed, speed),
            int(p.get("ball_size_min", 20)),
        )
        for _ in range(n)
    ]
    t_end = time.perf_counter() + duration_s
    while time.perf_counter() < t_end:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            ):
                session.log_event("node_end", node_id=node.node_id, node_type=node.type, node_index=node.index, engine=node.engine)
                return
        mx, my = pygame.mouse.get_pos()
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 255))
        pygame.draw.circle(surf, (0, 0, 0, 0), (int(mx), int(my)), int(kh_r))
        for b in balls:
            b.x += b.vx
            b.y += b.vy
            if b.x < b.r or b.x > w - b.r:
                b.vx *= -1
            if b.y < b.r or b.y > h - b.r:
                b.vy *= -1
            pygame.draw.circle(surf, b.color, (int(b.x), int(b.y)), b.r)
        screen.blit(surf, (0, 0))
        pygame.display.flip()
        clock.tick(60)
    session.log_event(
        "node_end",
        node_id=node.node_id,
        node_type=node.type,
        node_index=node.index,
        engine=node.engine,
    )
