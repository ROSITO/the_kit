"""Manette Nintendo Switch (Bluetooth) + clavier secours."""

from __future__ import annotations

from typing import Any

# Mapping utilisateur : ↑ avant, ↓ arrière, ← gauche, → droite
KEY_TO_DIRECTION: dict[int, str] = {}

HAT_TO_DIRECTION: dict[tuple[int, int], str] = {
    (0, 1): "AP",
    (0, -1): "PA",
    (-1, 0): "LATG",
    (1, 0): "LATD",
}


def _ensure_pygame_keys() -> None:
    global KEY_TO_DIRECTION
    if KEY_TO_DIRECTION:
        return
    import pygame

    KEY_TO_DIRECTION = {
        pygame.K_UP: "AP",
        pygame.K_DOWN: "PA",
        pygame.K_LEFT: "LATG",
        pygame.K_RIGHT: "LATD",
    }


def init_joystick() -> int:
    """Retourne le nombre de manettes détectées."""
    import pygame

    pygame.joystick.init()
    return pygame.joystick.get_count()


def _direction_from_hat(joy) -> str | None:
    if joy.get_numhats() < 1:
        return None
    hat = joy.get_hat(0)
    return HAT_TO_DIRECTION.get(hat)


def _direction_from_axes(joy, *, threshold: float = 0.5) -> str | None:
    if joy.get_numaxes() < 2:
        return None
    x, y = joy.get_axis(0), joy.get_axis(1)
    if abs(x) < threshold and abs(y) < threshold:
        return None
    if abs(y) >= abs(x):
        return "AP" if y < -threshold else "PA" if y > threshold else None
    return "LATG" if x < -threshold else "LATD" if x > threshold else None


def poll_direction(*, events: list[Any] | None = None) -> str | None:
    """
    Lit une direction (↑↓←→). Clavier prioritaire si plusieurs touches.
    """
    import pygame

    _ensure_pygame_keys()
    if events:
        for event in events:
            if event.type == pygame.KEYDOWN and event.key in KEY_TO_DIRECTION:
                return KEY_TO_DIRECTION[event.key]
            if event.type == pygame.JOYHATMOTION:
                d = HAT_TO_DIRECTION.get(event.value)
                if d:
                    return d
            if event.type == pygame.JOYBUTTONDOWN:
                pass

    pressed = pygame.key.get_pressed()
    for key, direction in KEY_TO_DIRECTION.items():
        if pressed[key]:
            return direction

    if pygame.joystick.get_count() > 0:
        joy = pygame.joystick.Joystick(0)
        if not joy.get_init():
            joy.init()
        d = _direction_from_hat(joy) or _direction_from_axes(joy)
        if d:
            return d
    return None


def direction_label(direction: str) -> str:
    return {
        "AP": "avant",
        "PA": "arrière",
        "LATD": "droite",
        "LATG": "gauche",
        "CONTROL": "contrôle",
    }.get(direction.upper(), direction)
