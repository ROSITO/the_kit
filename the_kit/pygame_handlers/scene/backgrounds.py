from __future__ import annotations

from typing import Any, Protocol

from the_kit.pygame_handlers.scene.context import SceneContext
from the_kit.pygame_handlers.shadow_ball_scene import ShadowBallScene


class Background(Protocol):
    def setup(self, ctx: SceneContext, params: dict[str, Any]) -> None: ...
    def draw(self, ctx: SceneContext) -> None: ...


class PlainBackground:
    def setup(self, ctx: SceneContext, params: dict[str, Any]) -> None:
        self._color = tuple(params.get("color", [0, 0, 0])[:3])

    def draw(self, ctx: SceneContext) -> None:
        ctx.screen.fill(self._color)


class ShadowCorridorBackground:
    def setup(self, ctx: SceneContext, params: dict[str, Any]) -> None:
        self._scene = ShadowBallScene(ctx.width, ctx.height, params)
        ctx.variables["shadow_scene"] = self._scene

    def draw(self, ctx: SceneContext) -> None:
        self._scene.draw_corridor(ctx.screen)


BACKGROUNDS: dict[str, type[Background]] = {
    "plain": PlainBackground,
    "black": PlainBackground,
    "shadow_corridor": ShadowCorridorBackground,
    "shadow": ShadowCorridorBackground,
}


def create_background(name: str) -> Background:
    key = (name or "plain").lower().replace("-", "_")
    cls = BACKGROUNDS.get(key)
    if cls is None:
        raise ValueError(f"fond inconnu: {name!r} (disponibles: {', '.join(BACKGROUNDS)})")
    return cls()
