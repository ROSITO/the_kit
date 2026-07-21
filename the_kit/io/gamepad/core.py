"""API publique gamepad — sélection automatique du backend."""

from __future__ import annotations

from typing import Any

from the_kit.io.gamepad.backends import (
    GamepadBackend,
    KeyboardBackend,
    PyJoyConBackend,
    PygameJoystickBackend,
    SdlGameControllerBackend,
)

_active_backend: GamepadBackend | None = None
_keyboard = KeyboardBackend()


def _backend_chain(preference: str) -> list[GamepadBackend]:
    pref = (preference or "auto").lower()
    chain: list[GamepadBackend] = []
    if pref in ("pyjoycon", "joycon", "hid"):
        chain.append(PyJoyConBackend())
    if pref in ("auto", "pygame", "joystick"):
        chain.append(PygameJoystickBackend())
    if pref in ("auto", "sdl", "gamecontroller", "portaudio"):
        chain.append(SdlGameControllerBackend())
    if pref == "auto":
        chain.append(PyJoyConBackend())
    return chain


def init_gamepad(*, preference: str = "auto") -> int:
    """
    Ouvre le meilleur backend disponible.
    Retourne le nombre de joysticks SDL détectés (0 si aucun).
    """
    global _active_backend
    close_gamepad()

    import pygame

    if pygame.joystick.get_init():
        count = pygame.joystick.get_count()
    else:
        pygame.joystick.init()
        count = pygame.joystick.get_count()

    for backend in _backend_chain(preference):
        if backend.open():
            _active_backend = backend
            print(f"   → backend actif : {backend.name}")
            return count

    print("🎮 Aucune manette — clavier uniquement")
    _active_backend = None
    return count


def close_gamepad() -> None:
    global _active_backend
    if _active_backend is not None:
        _active_backend.close()
        _active_backend = None


def joystick_status() -> dict[str, Any]:
    import pygame

    status: dict[str, Any] = {
        "connected": _active_backend is not None and _active_backend.name != "keyboard",
        "sdl_joystick_count": pygame.joystick.get_count() if pygame.joystick.get_init() else 0,
    }
    if _active_backend is not None:
        status.update(_active_backend.status())
    else:
        status["backend"] = "none"
    return status


def poll_direction(*, events: list[Any] | None = None) -> str | None:
    """Clavier + manette active. Priorité : événement clavier, puis manette."""
    d = _keyboard.poll(events)
    if d:
        return d
    if _active_backend is not None:
        return _active_backend.poll(events)
    return None


def direction_label(direction: str) -> str:
    return {
        "AP": "avant",
        "PA": "arrière",
        "LATD": "droite",
        "LATG": "gauche",
        "CONTROL": "contrôle",
    }.get(direction.upper(), direction)
