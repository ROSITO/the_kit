"""Flux optique (port simplifié randomflow/optical_flow.py)."""

from __future__ import annotations

import math
import random
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from the_kit.logging.session import SessionLogger
    from the_kit.protocol.models import Node


def _parse_color(color) -> tuple[int, int, int]:
    if isinstance(color, (list, tuple)) and len(color) >= 3:
        return (int(color[0]), int(color[1]), int(color[2]))
    return (255, 255, 255)


def _parse_params(params: dict[str, Any]) -> dict[str, Any]:
    noise_mode = str(params.get("noise_mode", "brownian")).lower()
    if noise_mode not in ("brownian", "reverse"):
        noise_mode = "brownian"
    return {
        "dot_size": int(params.get("dot_size", 4)),
        "dot_speed": float(params.get("dot_speed", 2.0)),
        "dot_color": _parse_color(params.get("dot_color", [255, 255, 255])),
        "dot_number": int(params.get("dot_number", 200)),
        "dot_coherence": max(0.0, min(1.0, float(params.get("dot_coherence", 0.8)))),
        "spawn_radius": max(1.0, float(params.get("spawn_radius", 80))),
        "brownian_sigma": max(0.0, float(params.get("brownian_sigma", 1.2))),
        "noise_mode": noise_mode,
        "warmup_loops": max(0, int(params.get("warmup_loops", 60))),
        "duration_s": float(params.get("duration_s", 5.0)),
        "key_noise": str(params.get("key_noise", "b")).lower()[:1] or "b",
        "key_motion": str(params.get("key_motion", "m")).lower()[:1] or "m",
    }


class _Dot:
    __slots__ = ("x", "y", "vx", "vy", "moving", "angle", "speed")

    def __init__(self, x, y, moving, angle, speed):
        self.x, self.y = x, y
        self.moving = moving
        self.angle = angle
        self.speed = speed
        if moving:
            self.vx = speed * math.cos(angle)
            self.vy = speed * math.sin(angle)
        else:
            self.vx = self.vy = 0.0

    def update(self, w, h, cx, cy, spawn_r, sigma, noise_mode) -> bool:
        import random as rnd

        if not self.moving:
            if noise_mode == "reverse":
                self.x += self.vx
                self.y += self.vy
                dx, dy = self.x - cx, self.y - cy
                if dx * dx + dy * dy <= spawn_r * spawn_r:
                    self._edge_spawn(w, h, cx, cy)
                return True
            self.x += rnd.gauss(0, sigma)
            self.y += rnd.gauss(0, sigma)
            self.x %= w
            self.y %= h
            return True
        self.x += self.vx
        self.y += self.vy
        if self.x < 0 or self.x > w or self.y < 0 or self.y > h:
            ang = rnd.uniform(0, 2 * math.pi)
            r = math.sqrt(rnd.uniform(0, 1)) * spawn_r
            self.x = cx + r * math.cos(ang)
            self.y = cy + r * math.sin(ang)
            self.angle = math.atan2(self.y - cy, self.x - cx)
            self.vx = self.speed * math.cos(self.angle)
            self.vy = self.speed * math.sin(self.angle)
        return True

    def _edge_spawn(self, w, h, cx, cy) -> None:
        side = random.randint(0, 3)
        if side == 0:
            self.x, self.y = random.uniform(0, w), 0.0
        elif side == 1:
            self.x, self.y = random.uniform(0, w), float(h)
        elif side == 2:
            self.x, self.y = 0.0, random.uniform(0, h)
        else:
            self.x, self.y = float(w), random.uniform(0, h)
        self.angle = math.atan2(cy - self.y, cx - self.x)
        self.vx = self.speed * math.cos(self.angle)
        self.vy = self.speed * math.sin(self.angle)

    def draw(self, screen, color, size) -> None:
        import pygame

        pygame.draw.circle(screen, color, (int(self.x), int(self.y)), size)


def _create_dots(w, h, n, coherence, speed, spawn_r, noise_mode) -> list[_Dot]:
    cx, cy = w / 2, h / 2
    n_moving = max(0, min(n, int(round(n * coherence))))
    dots: list[_Dot] = []
    for i in range(n):
        x = random.uniform(0, w)
        y = random.uniform(0, h)
        moving = i < n_moving
        if moving:
            ang = math.atan2(y - cy, x - cx)
            dots.append(_Dot(x, y, True, ang, speed))
        elif noise_mode == "reverse":
            side = random.randint(0, 3)
            if side == 0:
                ex, ey = random.uniform(0, w), 0.0
            elif side == 1:
                ex, ey = random.uniform(0, w), float(h)
            elif side == 2:
                ex, ey = 0.0, random.uniform(0, h)
            else:
                ex, ey = float(w), random.uniform(0, h)
            ang = math.atan2(cy - ey, cx - ex)
            d = _Dot(ex, ey, False, ang, speed)
            d.vx = speed * math.cos(ang)
            d.vy = speed * math.sin(ang)
            dots.append(d)
        else:
            dots.append(_Dot(x, y, False, 0.0, speed))
    random.shuffle(dots)
    return dots


def run_optic_flow_node(
    node: Node,
    session: SessionLogger,
    *,
    screen,
    clock,
) -> None:
    import pygame

    params = _parse_params(node.params)
    w, h = screen.get_size()
    dots = _create_dots(
        w,
        h,
        params["dot_number"],
        params["dot_coherence"],
        params["dot_speed"],
        params["spawn_radius"],
        params["noise_mode"],
    )
    cx, cy = w / 2, h / 2
    for _ in range(params["warmup_loops"]):
        for d in dots:
            d.update(w, h, cx, cy, params["spawn_radius"], params["brownian_sigma"], params["noise_mode"])

    end_at = time.perf_counter() + params["duration_s"]
    kn, km = params["key_noise"], params["key_motion"]
    session.log_event(
        "node_start",
        node_id=node.node_id,
        node_type=node.type,
        node_index=node.index,
        engine=node.engine,
        payload={"dot_coherence": params["dot_coherence"], "dot_number": params["dot_number"]},
    )
    running = True
    while running and time.perf_counter() < end_at:
        for event in pygame.event.get():
            if event.type in (pygame.QUIT, pygame.KEYDOWN) and (
                event.type == pygame.QUIT
                or event.key == pygame.K_ESCAPE
            ):
                running = False
                break
            if event.type == pygame.KEYDOWN and event.unicode:
                u = event.unicode.lower()
                if u == kn:
                    session.log_response(
                        node_index=node.index,
                        node_type=node.type,
                        node_id=node.node_id,
                        stimulus="optic_flow",
                        response="noise",
                        engine=node.engine,
                    )
                    running = False
                elif u == km:
                    session.log_response(
                        node_index=node.index,
                        node_type=node.type,
                        node_id=node.node_id,
                        stimulus="optic_flow",
                        response="motion",
                        engine=node.engine,
                    )
                    running = False
        screen.fill((20, 20, 25))
        for d in dots:
            d.update(
                w,
                h,
                cx,
                cy,
                params["spawn_radius"],
                params["brownian_sigma"],
                params["noise_mode"],
            )
            d.draw(screen, params["dot_color"], params["dot_size"])
        pygame.display.flip()
        clock.tick(60)
    session.log_event(
        "node_end",
        node_id=node.node_id,
        node_type=node.type,
        node_index=node.index,
        engine=node.engine,
    )
