"""Options secondaires 0 / 1 / 2 (papier)."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class SecondaryResult:
    responded: bool = False
    rt_ms: float | None = None
    correct: bool | None = None
    detail: dict[str, Any] | None = None


def run_secondary_mock(option: int, *, rng: random.Random | None = None) -> SecondaryResult:
    """Simulation headless des options secondaires."""
    opt = int(option)
    rng = rng or random.Random(0)
    if opt == 0:
        return SecondaryResult()
    if opt == 1:
        # cercle vert pendant masquage — RT simulé
        rt = 180.0 + rng.random() * 220.0
        return SecondaryResult(responded=True, rt_ms=round(rt, 1), correct=True, detail={"task": "green_circle"})
    if opt == 2:
        # change-detection 4 carrés
        ok = rng.random() > 0.25
        rt = 400.0 + rng.random() * 600.0
        return SecondaryResult(
            responded=True,
            rt_ms=round(rt, 1),
            correct=ok,
            detail={"task": "change_detection", "n_squares": 4},
        )
    return SecondaryResult(detail={"task": "unknown_option", "option": opt})


def run_secondary_pygame(
    option: int,
    *,
    screen,
    clock,
    mask_duration_s: float,
) -> SecondaryResult:
    """Exécution pygame minimale des options 1/2 (sinon mock)."""
    opt = int(option)
    if opt == 0:
        return SecondaryResult()
    try:
        import pygame
    except ImportError:
        return run_secondary_mock(opt)

    w, h = screen.get_size()
    font = pygame.font.SysFont(None, 32)
    t0 = time.perf_counter()
    responded = False
    rt_ms = None
    correct = None
    detail: dict[str, Any] = {}

    if opt == 1:
        detail["task"] = "green_circle"
        end = t0 + max(0.2, float(mask_duration_s))
        while time.perf_counter() < end and not responded:
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN and event.key != pygame.K_ESCAPE:
                    responded = True
                    rt_ms = (time.perf_counter() - t0) * 1000.0
                    correct = True
            screen.fill((30, 30, 30))
            pygame.draw.circle(screen, (0, 220, 0), (w // 2, h // 2), 40)
            screen.blit(font.render("Cercle vert — appuyez (option 1)", True, (220, 220, 220)), (40, 40))
            pygame.display.flip()
            clock.tick(60)
        return SecondaryResult(responded=responded, rt_ms=rt_ms, correct=correct, detail=detail)

    if opt == 2:
        detail["task"] = "change_detection"
        colors = [(220, 60, 60), (60, 120, 220), (220, 200, 60), (60, 200, 120)]
        positions = [(w // 3, h // 3), (2 * w // 3, h // 3), (w // 3, 2 * h // 3), (2 * w // 3, 2 * h // 3)]
        # flash 500 ms
        flash_end = time.perf_counter() + 0.5
        while time.perf_counter() < flash_end:
            screen.fill((20, 20, 20))
            for i, (pos, col) in enumerate(zip(positions, colors)):
                pygame.draw.rect(screen, col, (*pos, 60, 60))
            pygame.display.flip()
            clock.tick(60)
        changed = int(time.time() * 1000) % 4
        new_colors = list(colors)
        new_colors[changed] = (180, 180, 180)
        # attente réponse
        deadline = time.perf_counter() + 3.0
        choice = None
        while time.perf_counter() < deadline and choice is None:
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    mapping = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2, pygame.K_4: 3}
                    if event.key in mapping:
                        choice = mapping[event.key]
                        rt_ms = (time.perf_counter() - t0) * 1000.0
            screen.fill((20, 20, 20))
            for i, (pos, col) in enumerate(zip(positions, new_colors)):
                pygame.draw.rect(screen, col, (*pos, 60, 60))
                screen.blit(font.render(str(i + 1), True, (255, 255, 255)), (pos[0] + 20, pos[1] + 70))
            screen.blit(font.render("Quel carré a changé ? (1-4)", True, (220, 220, 220)), (40, 20))
            pygame.display.flip()
            clock.tick(60)
        correct = choice == changed if choice is not None else False
        detail["changed_index"] = changed
        detail["choice"] = choice
        return SecondaryResult(responded=choice is not None, rt_ms=rt_ms, correct=correct, detail=detail)

    return run_secondary_mock(opt)
