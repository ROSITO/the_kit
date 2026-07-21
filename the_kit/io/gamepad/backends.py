"""Chaîne de backends gamepad."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any

# Indices SDL_GameControllerButton (SDL 2.x) — indépendants du matériel
SDL_DPAD_UP = 11
SDL_DPAD_DOWN = 12
SDL_DPAD_LEFT = 13
SDL_DPAD_RIGHT = 14

DPAD_BUTTON_TO_DIRECTION: dict[int, str] = {
    SDL_DPAD_UP: "AP",
    SDL_DPAD_DOWN: "PA",
    SDL_DPAD_LEFT: "LATG",
    SDL_DPAD_RIGHT: "LATD",
}

HAT_TO_DIRECTION: dict[tuple[int, int], str] = {
    (0, 1): "AP",
    (0, -1): "PA",
    (-1, 0): "LATG",
    (1, 0): "LATD",
}

KEY_TO_DIRECTION: dict[int, str] = {}

JOYCON_L_SDL224: dict[int, str] = {2: "AP", 1: "PA", 3: "LATG", 0: "LATD"}
JOYCON_L_LEGACY: dict[int, str] = {0: "AP", 1: "PA", 2: "LATG", 3: "LATD"}
JOYCON_PAIR_DPAD: dict[int, str] = {11: "AP", 12: "PA", 13: "LATG", 14: "LATD"}


def ensure_sdl_hints() -> None:
    os.environ.setdefault("SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS", "1")
    os.environ.setdefault("SDL_JOYSTICK_HIDAPI", "1")


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


class GamepadBackend(ABC):
    name: str = "base"

    @abstractmethod
    def open(self) -> bool:
        """Tente d'ouvrir le périphérique."""

    @abstractmethod
    def close(self) -> None:
        pass

    @abstractmethod
    def poll(self, events: list[Any] | None) -> str | None:
        pass

    @abstractmethod
    def status(self) -> dict[str, Any]:
        pass


class KeyboardBackend(GamepadBackend):
    name = "keyboard"

    def open(self) -> bool:
        _ensure_pygame_keys()
        return True

    def close(self) -> None:
        return

    def poll(self, events: list[Any] | None) -> str | None:
        import pygame

        _ensure_pygame_keys()
        if events:
            for event in events:
                if event.type == pygame.KEYDOWN and event.key in KEY_TO_DIRECTION:
                    return KEY_TO_DIRECTION[event.key]
        pressed = pygame.key.get_pressed()
        for key, direction in KEY_TO_DIRECTION.items():
            if pressed[key]:
                return direction
        return None

    def status(self) -> dict[str, Any]:
        return {"backend": self.name}


class SdlGameControllerBackend(GamepadBackend):
    """API SDL GameController — d-pad sémantique (recommandé Joy-Con / Switch)."""

    name = "sdl_gamecontroller"

    def __init__(self) -> None:
        self._controller = None
        self._device_id: int | None = None
        self._device_name = ""

    def open(self) -> bool:
        ensure_sdl_hints()
        try:
            from pygame._sdl2 import controller as ctl
        except ImportError:
            return False

        if not ctl.get_init():
            ctl.init()
        import pygame

        if not pygame.joystick.get_init():
            pygame.joystick.init()

        for device_id in range(ctl.get_count()):
            if not ctl.is_controller(device_id):
                continue
            name = ctl.name_forindex(device_id) or ""
            lower = name.lower()
            if any(k in lower for k in ("joy-con", "switch", "nintendo", "wireless gamepad", "pro controller")):
                return self._open_device(device_id, name)
        for device_id in range(ctl.get_count()):
            if ctl.is_controller(device_id):
                return self._open_device(device_id, ctl.name_forindex(device_id) or f"controller_{device_id}")
        return False

    def _open_device(self, device_id: int, name: str) -> bool:
        from pygame._sdl2 import controller as ctl

        try:
            controller = ctl.Controller(device_id)
            controller.init()
        except Exception:
            return False
        self._controller = controller
        self._device_id = device_id
        self._device_name = name
        print(f"🎮 SDL GameController [{device_id}] {name}")
        return True

    def close(self) -> None:
        if self._controller is not None:
            try:
                self._controller.quit()
            except Exception:
                pass
        self._controller = None

    def poll(self, events: list[Any] | None) -> str | None:
        if self._controller is None:
            return None
        try:
            from pygame._sdl2 import controller as ctl

            ctl.update()
        except Exception:
            pass
        for btn, direction in DPAD_BUTTON_TO_DIRECTION.items():
            try:
                if self._controller.get_button(btn):
                    return direction
            except Exception:
                continue
        return None

    def status(self) -> dict[str, Any]:
        return {
            "backend": self.name,
            "device_id": self._device_id,
            "name": self._device_name,
            "connected": self._controller is not None,
        }


class PygameJoystickBackend(GamepadBackend):
    name = "pygame_joystick"

    def __init__(self) -> None:
        self._joy = None
        self._index: int | None = None
        self._button_map: dict[int, str] = {}

    def open(self) -> bool:
        ensure_sdl_hints()
        import pygame

        if not pygame.joystick.get_init():
            pygame.joystick.init()
        index = self._pick_index()
        if index is None:
            return False
        joy = pygame.joystick.Joystick(index)
        if not joy.get_init():
            joy.init()
        self._joy = joy
        self._index = index
        name = joy.get_name()
        self._button_map = self._button_map_for_name(name)
        if not self._button_map and joy.get_numhats() == 0:
            self._button_map = {**JOYCON_L_SDL224, **JOYCON_L_LEGACY, **JOYCON_PAIR_DPAD}
        print(
            f"🎮 pygame joystick [{index}] {name} — "
            f"hats={joy.get_numhats()} buttons={joy.get_numbuttons()} axes={joy.get_numaxes()}"
        )
        return True

    def _pick_index(self) -> int | None:
        import pygame

        count = pygame.joystick.get_count()
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

    @staticmethod
    def _button_map_for_name(name: str) -> dict[int, str]:
        lower = name.lower()
        if "joy-con" in lower and "(l)" in lower:
            return dict(JOYCON_L_SDL224)
        if "joy-con" in lower or "wireless gamepad" in lower:
            return dict(JOYCON_L_SDL224)
        if "switch" in lower or "pro controller" in lower:
            return dict(JOYCON_PAIR_DPAD)
        return {}

    def close(self) -> None:
        self._joy = None
        self._index = None

    def poll(self, events: list[Any] | None) -> str | None:
        import pygame

        if self._joy is None:
            return None
        if events:
            for event in events:
                if event.type == pygame.JOYHATMOTION:
                    d = HAT_TO_DIRECTION.get(event.value)
                    if d:
                        return d
                if event.type == pygame.JOYBUTTONDOWN:
                    d = self._button_map.get(event.button)
                    if d:
                        return d
        d = self._direction_from_hat()
        if d:
            return d
        d = self._direction_from_buttons()
        if d:
            return d
        return self._direction_from_axes()

    def _direction_from_hat(self) -> str | None:
        assert self._joy is not None
        if self._joy.get_numhats() < 1:
            return None
        return HAT_TO_DIRECTION.get(self._joy.get_hat(0))

    def _direction_from_buttons(self) -> str | None:
        assert self._joy is not None
        for btn, direction in self._button_map.items():
            if btn < self._joy.get_numbuttons() and self._joy.get_button(btn):
                return direction
        return None

    def _direction_from_axes(self, *, threshold: float = 0.55) -> str | None:
        assert self._joy is not None
        if self._joy.get_numaxes() < 2:
            return None
        x, y = self._joy.get_axis(0), self._joy.get_axis(1)
        if abs(x) < threshold and abs(y) < threshold:
            return None
        if abs(y) >= abs(x):
            return "AP" if y < -threshold else "PA" if y > threshold else None
        return "LATG" if x < -threshold else "LATD" if x > threshold else None

    def status(self) -> dict[str, Any]:
        if self._joy is None:
            return {"backend": self.name, "connected": False}
        return {
            "backend": self.name,
            "connected": True,
            "index": self._index,
            "name": self._joy.get_name(),
            "buttons": self._joy.get_numbuttons(),
            "hats": self._joy.get_numhats(),
            "axes": self._joy.get_numaxes(),
            "button_map": dict(self._button_map),
        }


class PyJoyConBackend(GamepadBackend):
    """Driver HID Nintendo (pip install joycon-python hidapi)."""

    name = "pyjoycon"

    def __init__(self, *, side: str = "auto") -> None:
        self._side = side
        self._button_event = None
        self._device_name = ""

    def open(self) -> bool:
        try:
            from pyjoycon.device import get_L_id, get_R_id
            from pyjoycon.event import ButtonEventJoyCon
        except ImportError:
            return False

        joycon_id = None
        if self._side == "left":
            joycon_id = get_L_id()
        elif self._side == "right":
            joycon_id = get_R_id()
        else:
            joycon_id = get_L_id() or get_R_id()
        if not joycon_id or joycon_id[0] is None:
            return False
        try:
            self._button_event = ButtonEventJoyCon(*joycon_id)
            self._device_name = f"pyjoycon {joycon_id}"
            print(f"🎮 pyjoycon HID — {self._device_name}")
            return True
        except Exception as exc:
            print(f"⚠ pyjoycon : {exc}")
            return False

    def close(self) -> None:
        if self._button_event is not None:
            try:
                self._button_event.disconnect()
            except Exception:
                pass
        self._button_event = None

    def poll(self, events: list[Any] | None) -> str | None:
        if self._button_event is None:
            return None
        for event_type, status in self._button_event.events():
            if status:
                d = self._map_pyjoycon_event(str(event_type))
                if d:
                    return d
        return self._map_pyjoycon_held(self._button_event)

    @staticmethod
    def _map_pyjoycon_event(event_type: str) -> str | None:
        return {
            "up": "AP",
            "down": "PA",
            "left": "LATG",
            "right": "LATD",
        }.get(event_type.lower())

    @staticmethod
    def _map_pyjoycon_held(joycon) -> str | None:
        if joycon.up:
            return "AP"
        if joycon.down:
            return "PA"
        if joycon.left:
            return "LATG"
        if joycon.right:
            return "LATD"
        return None

    def status(self) -> dict[str, Any]:
        return {
            "backend": self.name,
            "connected": self._button_event is not None,
            "name": self._device_name,
        }
