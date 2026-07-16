"""Réponse clavier simple (pygame)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from the_kit.logging.session import SessionLogger
    from the_kit.protocol.models import Node


def run_keyboard_response_node(
    node: Node,
    session: SessionLogger,
    *,
    screen,
    clock,
) -> None:
    import pygame

    params = node.params
    duration_s = float(params.get("duration_s", 3.0))
    valid_keys = [str(k).lower() for k in params.get("keys", ["b", "m"])]
    prompt = params.get("prompt", "Appuyez sur une touche")
    font = pygame.font.SysFont(None, 28)
    end_at = time.perf_counter() + duration_s
    session.log_event(
        "node_start",
        node_id=node.node_id,
        node_type=node.type,
        node_index=node.index,
        engine=node.engine,
    )
    responded = False
    while time.perf_counter() < end_at and not responded:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return
                if event.unicode and event.unicode.lower() in valid_keys:
                    session.log_response(
                        node_index=node.index,
                        node_type=node.type,
                        node_id=node.node_id,
                        stimulus=prompt,
                        response=event.unicode.lower(),
                        engine=node.engine,
                    )
                    responded = True
        screen.fill((0, 0, 0))
        surf = font.render(prompt, True, (220, 220, 220))
        screen.blit(surf, surf.get_rect(center=screen.get_rect().center))
        pygame.display.flip()
        clock.tick(60)
    session.log_event(
        "node_end",
        node_id=node.node_id,
        node_type=node.type,
        node_index=node.index,
        engine=node.engine,
    )
