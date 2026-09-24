"""Options secondaires 0 / 1 / 2 (papier).

0 — désactivée
1 — cercle vert pendant le masquage / occultation (RT)
2 — flash 4 carrés (500 ms) avant l'essai, puis change-detection après le jugement principal
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SecondaryResult:
    responded: bool = False
    rt_ms: float | None = None
    correct: bool | None = None
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChangeDetectionState:
    """État entre pré-flash et post-jugement (option 2)."""

    colors: list[tuple[int, int, int]]
    positions: list[tuple[int, int]]
    changed_index: int


def run_secondary_mock(option: int, *, rng: random.Random | None = None) -> SecondaryResult:
    opt = int(option)
    rng = rng or random.Random(0)
    if opt == 0:
        return SecondaryResult()
    if opt == 1:
        rt = 180.0 + rng.random() * 220.0
        return SecondaryResult(
            responded=True,
            rt_ms=round(rt, 1),
            correct=True,
            detail={"task": "green_circle", "mode": "mock"},
        )
    if opt == 2:
        ok = rng.random() > 0.25
        rt = 400.0 + rng.random() * 600.0
        return SecondaryResult(
            responded=True,
            rt_ms=round(rt, 1),
            correct=ok,
            detail={"task": "change_detection", "n_squares": 4, "mode": "mock"},
        )
    return SecondaryResult(detail={"task": "unknown_option", "option": opt})


def run_green_circle_during(screen, clock, *, duration_s: float) -> SecondaryResult:
    """Option 1 standalone (masquage Chrono / Tone)."""
    import pygame

    w, h = screen.get_size()
    font = pygame.font.SysFont(None, 32)
    t0 = time.perf_counter()
    end = t0 + max(0.05, float(duration_s))
    responded = False
    rt_ms = None
    while time.perf_counter() < end:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN and event.key != pygame.K_ESCAPE:
                if not responded:
                    responded = True
                    rt_ms = (time.perf_counter() - t0) * 1000.0
        screen.fill((30, 30, 30))
        pygame.draw.circle(screen, (0, 220, 0), (w // 2, h // 2), 40)
        screen.blit(font.render("Cercle vert — appuyez (option 1)", True, (220, 220, 220)), (40, 40))
        pygame.display.flip()
        clock.tick(60)
    return SecondaryResult(
        responded=responded,
        rt_ms=rt_ms,
        correct=True if responded else False,
        detail={"task": "green_circle"},
    )


def run_change_detection_pre(screen, clock, *, flash_s: float = 0.5) -> ChangeDetectionState:
    """Option 2 — flash initial 500 ms."""
    import pygame

    w, h = screen.get_size()
    colors = [(220, 60, 60), (60, 120, 220), (220, 200, 60), (60, 200, 120)]
    positions = [
        (w // 3 - 30, h // 3 - 30),
        (2 * w // 3 - 30, h // 3 - 30),
        (w // 3 - 30, 2 * h // 3 - 30),
        (2 * w // 3 - 30, 2 * h // 3 - 30),
    ]
    flash_end = time.perf_counter() + flash_s
    while time.perf_counter() < flash_end:
        screen.fill((20, 20, 20))
        for pos, col in zip(positions, colors):
            pygame.draw.rect(screen, col, (*pos, 60, 60))
        pygame.display.flip()
        clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                break
    changed = int(time.time() * 1000) % 4
    return ChangeDetectionState(colors=colors, positions=positions, changed_index=changed)


def run_change_detection_post(
    screen,
    clock,
    state: ChangeDetectionState,
    *,
    timeout_s: float = 3.0,
    auto: bool = False,
) -> SecondaryResult:
    """Option 2 — présentation post-essai (1 couleur changée)."""
    import pygame

    font = pygame.font.SysFont(None, 28)
    new_colors = list(state.colors)
    new_colors[state.changed_index] = (180, 180, 180)
    if auto:
        return SecondaryResult(
            responded=True,
            rt_ms=15.0,
            correct=True,
            detail={
                "task": "change_detection",
                "changed_index": state.changed_index,
                "choice": state.changed_index,
                "mode": "auto",
            },
        )

    t0 = time.perf_counter()
    choice = None
    rt_ms = None
    deadline = t0 + timeout_s
    mapping = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2, pygame.K_4: 3}
    while time.perf_counter() < deadline and choice is None:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN and event.key in mapping:
                choice = mapping[event.key]
                rt_ms = (time.perf_counter() - t0) * 1000.0
        screen.fill((20, 20, 20))
        for i, (pos, col) in enumerate(zip(state.positions, new_colors)):
            pygame.draw.rect(screen, col, (*pos, 60, 60))
            screen.blit(font.render(str(i + 1), True, (255, 255, 255)), (pos[0] + 20, pos[1] + 70))
        screen.blit(font.render("Quel carré a changé ? (1-4)", True, (220, 220, 220)), (40, 20))
        pygame.display.flip()
        clock.tick(60)

    correct = choice == state.changed_index if choice is not None else False
    return SecondaryResult(
        responded=choice is not None,
        rt_ms=rt_ms,
        correct=correct,
        detail={
            "task": "change_detection",
            "changed_index": state.changed_index,
            "choice": choice,
        },
    )


def run_secondary_pygame(
    option: int,
    *,
    screen,
    clock,
    mask_duration_s: float,
) -> SecondaryResult:
    """Compat : option 1 pendant mask ; option 2 enchaîne pre+post (sans essai principal)."""
    opt = int(option)
    if opt == 0:
        return SecondaryResult()
    try:
        import pygame  # noqa: F401
    except ImportError:
        return run_secondary_mock(opt)
    if opt == 1:
        return run_green_circle_during(screen, clock, duration_s=mask_duration_s)
    if opt == 2:
        state = run_change_detection_pre(screen, clock)
        return run_change_detection_post(screen, clock, state)
    return run_secondary_mock(opt)
