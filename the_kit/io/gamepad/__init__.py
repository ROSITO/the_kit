"""Entrées manette — SDL GameController, pygame joystick, pyjoycon (optionnel)."""

from the_kit.io.gamepad.core import (
    direction_label,
    init_gamepad,
    joystick_status,
    poll_direction,
)

# Rétrocompatibilité
init_joystick = init_gamepad

__all__ = [
    "direction_label",
    "init_gamepad",
    "init_joystick",
    "joystick_status",
    "poll_direction",
]
