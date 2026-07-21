from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from the_kit.engines.base import EngineBase
from the_kit.pygame_handlers import HANDLERS

if TYPE_CHECKING:
    from the_kit.logging.session import SessionLogger
    from the_kit.protocol.models import Node, Protocol


class PygameEngine(EngineBase):
    name = "pygame"
    _screen = None
    _clock = None

    @classmethod
    def check_available(cls) -> tuple[bool, str]:
        try:
            import pygame  # noqa: F401

            return True, "ok"
        except ImportError:
            return False, "pygame non installé (uv sync --extra pygame)"

    def run(
        self,
        protocol: Protocol,
        session: SessionLogger,
        nodes: list[Node],
        *,
        dry_run: bool = False,
    ) -> None:
        import os
        import sys

        import pygame

        if sys.platform == "win32":
            os.environ.setdefault("SDL_VIDEODRIVER", "windows")

        try:
            from PyQt6.QtWidgets import QApplication

            qt_app = QApplication.instance()
            if qt_app is not None:
                qt_app.quit()
                qt_app.processEvents()
        except ImportError:
            pass

        if not pygame.get_init():
            pygame.init()
        info = pygame.display.Info()
        size = (
            int(protocol.raw.get("display", {}).get("width", info.current_w // 2)),
            int(protocol.raw.get("display", {}).get("height", info.current_h // 2)),
        )
        fullscreen = bool(protocol.raw.get("display", {}).get("fullscreen", False))
        flags = pygame.FULLSCREEN if fullscreen else pygame.RESIZABLE
        PygameEngine._screen = pygame.display.set_mode(size, flags)
        PygameEngine._clock = pygame.time.Clock()

        for node in nodes:
            handler = HANDLERS.get(node.type)
            if handler is None:
                session.log_event(
                    "error",
                    node_id=node.node_id,
                    payload={"message": f"type pygame inconnu: {node.type}"},
                )
                continue
            handler(
                node,
                session,
                screen=PygameEngine._screen,
                clock=PygameEngine._clock,
            )

    def cleanup(self) -> None:
        import pygame

        if pygame.get_init():
            pygame.display.quit()
            pygame.quit()
        PygameEngine._screen = None
        PygameEngine._clock = None
