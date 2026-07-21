"""Manette Nintendo Switch / Joy-Con (Bluetooth) + clavier secours."""

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

# Joy-Con (L) — croix en boutons (0 hat). Indices varient selon SDL.
# Réf. pygame 2.x / SDL 2.24+ : Up=2 Down=1 Left=3 Right=0
JOYCON_L_SDL224: dict[int, str] = {2: "AP", 1: "PA", 3: "LATG", 0: "LATD"}
# Ancien mapping pygame / SDL < 2.24
JOYCON_L_LEGACY: dict[int, str] = {0: "AP", 1: "PA", 2: "LATG", 3: "LATD"}
# Paire L+R fusionnée — d-pad haut du châssis
JOYCON_PAIR_DPAD: dict[int, str] = {11: "AP", 12: "PA", 13: "LATG", 14: "LATD"}

_active_index: int | None = None
_button_map: dict[int, str] = {}


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


def _button_map_for_name(name: str) -> dict[int, str]:
    lower = name.lower()
    if "joy-con" in lower and "(r)" in lower:
        # Joy-Con droit : stick + parfois axes ; pas de croix — garder vide ici
        return {}
    if "joy-con" in lower and "(l)" in lower:
        return dict(JOYCON_L_SDL224)
    if "joy-con" in lower or "wireless gamepad" in lower:
        return dict(JOYCON_L_SDL224)
    if "switch" in lower or "pro controller" in lower:
        return dict(JOYCON_PAIR_DPAD)
    return {}


def _merge_button_profiles(profiles: list[dict[int, str]]) -> dict[int, str]:
    merged: dict[int, str] = {}
    for profile in profiles:
        merged.update(profile)
    return merged


def _pick_joystick_index() -> int | None:
    import pygame

    count = pygame.joystick.get_count()
    if count == 0:
        return None
    preferred: list[int] = []
    fallback: list[int] = []
    for i in range(count):
        joy = pygame.joystick.Joystick(i)
        if not joy.get_init():
            joy.init()
        name = joy.get_name().lower()
        if any(k in name for k in ("joy-con", "switch", "nintendo", "wireless gamepad")):
            preferred.append(i)
        else:
            fallback.append(i)
    if preferred:
        return preferred[0]
    return fallback[0] if fallback else None


def init_joystick() -> int:
    """Initialise les manettes ; retourne le nombre détecté."""
    global _active_index, _button_map
    import pygame

    pygame.joystick.init()
    count = pygame.joystick.get_count()
    _active_index = _pick_joystick_index()
    _button_map = {}
    if _active_index is not None:
        joy = pygame.joystick.Joystick(_active_index)
        if not joy.get_init():
            joy.init()
        name = joy.get_name()
        _button_map = _button_map_for_name(name)
        if not _button_map and joy.get_numhats() == 0:
            # Joy-Con non reconnu par nom — essayer les profils connus
            _button_map = _merge_button_profiles(
                [JOYCON_L_SDL224, JOYCON_L_LEGACY, JOYCON_PAIR_DPAD]
            )
        print(
            f"🎮 Manette [{_active_index}] {name} — "
            f"hats={joy.get_numhats()} buttons={joy.get_numbuttons()} "
            f"axes={joy.get_numaxes()}"
        )
        if _button_map:
            print(f"   mapping boutons actif ({len(_button_map)} entrées)")
    else:
        print("🎮 Aucune manette détectée — clavier uniquement")
    return count


def joystick_status() -> dict[str, Any]:
    import pygame

    if _active_index is None:
        return {"connected": False, "count": pygame.joystick.get_count()}
    joy = pygame.joystick.Joystick(_active_index)
    return {
        "connected": True,
        "index": _active_index,
        "name": joy.get_name(),
        "buttons": joy.get_numbuttons(),
        "hats": joy.get_numhats(),
        "axes": joy.get_numaxes(),
        "button_map": dict(_button_map),
    }


def _active_joystick():
    import pygame

    if _active_index is None:
        return None
    joy = pygame.joystick.Joystick(_active_index)
    if not joy.get_init():
        joy.init()
    return joy


def _direction_from_hat(joy) -> str | None:
    if joy.get_numhats() < 1:
        return None
    return HAT_TO_DIRECTION.get(joy.get_hat(0))


def _direction_from_buttons(joy, button_map: dict[int, str]) -> str | None:
    for btn, direction in button_map.items():
        if btn < joy.get_numbuttons() and joy.get_button(btn):
            return direction
    return None


def _direction_from_axes(joy, *, threshold: float = 0.55) -> str | None:
    if joy.get_numaxes() < 2:
        return None
    x, y = joy.get_axis(0), joy.get_axis(1)
    if abs(x) < threshold and abs(y) < threshold:
        return None
    if abs(y) >= abs(x):
        return "AP" if y < -threshold else "PA" if y > threshold else None
    return "LATG" if x < -threshold else "LATD" if x > threshold else None


def _direction_from_button_event(button: int) -> str | None:
    return _button_map.get(button)


def poll_direction(*, events: list[Any] | None = None) -> str | None:
    """
    Lit une direction (↑↓←→). Clavier, hat, boutons Joy-Con, stick analogique.
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
                d = _direction_from_button_event(event.button)
                if d:
                    return d
            if event.type == pygame.JOYAXISMOTION and event.axis in (0, 1):
                joy = _active_joystick()
                if joy is not None:
                    d = _direction_from_axes(joy)
                    if d:
                        return d

    pressed = pygame.key.get_pressed()
    for key, direction in KEY_TO_DIRECTION.items():
        if pressed[key]:
            return direction

    joy = _active_joystick()
    if joy is None:
        return None
    return (
        _direction_from_hat(joy)
        or _direction_from_buttons(joy, _button_map)
        or _direction_from_axes(joy)
    )


def direction_label(direction: str) -> str:
    return {
        "AP": "avant",
        "PA": "arrière",
        "LATD": "droite",
        "LATG": "gauche",
        "CONTROL": "contrôle",
    }.get(direction.upper(), direction)
