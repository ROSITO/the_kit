from __future__ import annotations

import random
import time
from typing import Any, Protocol

from the_kit.pygame_handlers.scene.context import SceneContext
from the_kit.pygame_handlers.shadow_ball import run_shadow_ball_node
from the_kit.pygame_handlers.shadow_ball_scene import ShadowBallScene, TRIAL_FIXATION


class Stimulus(Protocol):
    def setup(self, ctx: SceneContext, params: dict[str, Any]) -> None: ...

    def update(self, ctx: SceneContext, dt: float) -> bool: ...

    def draw(self, ctx: SceneContext) -> None: ...

    def finished(self) -> bool: ...


class MotStimulus:
    """MOT par-dessus le fond (sans écran noir plein)."""

    def setup(self, ctx: SceneContext, params: dict[str, Any]) -> None:
        import pygame

        p = params
        w, h = ctx.width, ctx.height
        self._duration_s = float(p.get("duration_s", 20))
        self._t_end = time.perf_counter() + self._duration_s
        self._kh_r = float(p.get("keyhole_radius", 120))
        self._use_keyhole = bool(p.get("keyhole", True))
        speed = float(p.get("uniform_speed", 3.0))
        n = int(p.get("num_balls", 8))
        r = int(p.get("ball_size_min", 20))
        self._balls = []
        for _ in range(n):
            self._balls.append(
                {
                    "x": random.uniform(50, w - 50),
                    "y": random.uniform(50, h - 50),
                    "vx": random.uniform(-speed, speed),
                    "vy": random.uniform(-speed, speed),
                    "r": r,
                    "color": (
                        random.randint(80, 255),
                        random.randint(80, 255),
                        random.randint(200),
                    ),
                }
            )
        self._overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        self._done = False

    def update(self, ctx: SceneContext, dt: float) -> bool:
        w, h = ctx.width, ctx.height
        if time.perf_counter() >= self._t_end:
            self._done = True
            return False
        for b in self._balls:
            b["x"] += b["vx"]
            b["y"] += b["vy"]
            if b["x"] < b["r"] or b["x"] > w - b["r"]:
                b["vx"] *= -1
            if b["y"] < b["r"] or b["y"] > h - b["r"]:
                b["vy"] *= -1
        return True

    def draw(self, ctx: SceneContext) -> None:
        import pygame

        w, h = ctx.width, ctx.height
        self._overlay.fill((0, 0, 0, 0))
        for b in self._balls:
            pygame.draw.circle(
                self._overlay,
                b["color"],
                (int(b["x"]), int(b["y"])),
                b["r"],
            )
        if self._use_keyhole:
            dim = pygame.Surface((w, h), pygame.SRCALPHA)
            dim.fill((0, 0, 0, 200))
            mx, my = pygame.mouse.get_pos()
            pygame.draw.circle(dim, (0, 0, 0, 0), (int(mx), int(my)), int(self._kh_r))
            ctx.screen.blit(dim, (0, 0))
        ctx.screen.blit(self._overlay, (0, 0))

    def finished(self) -> bool:
        return self._done


class OpticFlowStimulus:
    def setup(self, ctx: SceneContext, params: dict[str, Any]) -> None:
        from the_kit.pygame_handlers.optic_flow import _create_dots, _parse_params

        self._cfg = _parse_params(params)
        self._dots = _create_dots(
            ctx.width,
            ctx.height,
            self._cfg["dot_number"],
            self._cfg["dot_coherence"],
            self._cfg["dot_speed"],
            self._cfg["spawn_radius"],
            self._cfg["noise_mode"],
        )
        self._duration_s = float(params.get("duration_s", self._cfg["duration_s"]))
        self._t_end = time.perf_counter() + self._duration_s
        self._done = False
        for _ in range(self._cfg["warmup_loops"]):
            self._step(ctx)

    def _step(self, ctx: SceneContext) -> None:
        cx, cy = ctx.width / 2, ctx.height / 2
        for d in self._dots:
            d.update(
                ctx.width,
                ctx.height,
                cx,
                cy,
                self._cfg["spawn_radius"],
                self._cfg["brownian_sigma"],
                self._cfg["noise_mode"],
            )

    def update(self, ctx: SceneContext, dt: float) -> bool:
        if time.perf_counter() >= self._t_end:
            self._done = True
            return False
        self._step(ctx)
        return True

    def draw(self, ctx: SceneContext) -> None:
        for d in self._dots:
            d.draw(ctx.screen, self._cfg["dot_color"], self._cfg["dot_size"])

    def finished(self) -> bool:
        return self._done


class ShadowBallStimulus:
    """Balle + ombre sur le corridor (réutilise ShadowBallScene)."""

    def setup(self, ctx: SceneContext, params: dict[str, Any]) -> None:
        existing = ctx.variables.get("shadow_scene")
        if existing is not None and isinstance(existing, ShadowBallScene):
            self._scene = ShadowBallScene(ctx.width, ctx.height, params)
        else:
            self._scene = ShadowBallScene(ctx.width, ctx.height, params)
            ctx.variables["shadow_scene"] = self._scene
        self._scene.begin()
        self._scene.trial_phase = TRIAL_FIXATION
        self._scene.phase_time = 0.0

    def update(self, ctx: SceneContext, dt: float) -> bool:
        self._scene.update(dt)
        return not self._scene.done

    def draw(self, ctx: SceneContext) -> None:
        self._scene.draw_ball_and_shadow(ctx.screen)

    def finished(self) -> bool:
        return self._scene.done


class ShadowBallTrialStimulus:
    """Essai shadow_ball complet (fixation + mouvement) — équivalent nœud shadow_ball."""

    def setup(self, ctx: SceneContext, params: dict[str, Any]) -> None:
        self._params = params
        self._ran = False

    def update(self, ctx: SceneContext, dt: float) -> bool:
        if self._ran:
            return False
        run_shadow_ball_node(
            ctx.node,
            ctx.session,
            screen=ctx.screen,
            clock=ctx.clock,
        )
        self._ran = True
        return False

    def draw(self, ctx: SceneContext) -> None:
        pass

    def finished(self) -> bool:
        return self._ran


STIMULI: dict[str, type[Stimulus]] = {
    "mot": MotStimulus,
    "optic_flow": OpticFlowStimulus,
    "flow": OpticFlowStimulus,
    "shadow_ball": ShadowBallStimulus,
    "ball": ShadowBallStimulus,
    "shadow_ball_trial": ShadowBallTrialStimulus,
}


def create_stimulus(name: str) -> Stimulus:
    key = (name or "").lower().replace("-", "_")
    cls = STIMULI.get(key)
    if cls is None:
        raise ValueError(f"stimulus inconnu: {name!r} (disponibles: {', '.join(STIMULI)})")
    return cls()
