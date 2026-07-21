"""Diagnostic interactif manette — `the_kit check-gamepad`."""

from __future__ import annotations

import sys
import time


def run_gamepad_check(*, duration_s: float = 30.0) -> int:
    import pygame

    from the_kit.io.gamepad.backends import (
        DPAD_BUTTON_TO_DIRECTION,
        PyJoyConBackend,
        PygameJoystickBackend,
        SdlGameControllerBackend,
        ensure_sdl_hints,
    )

    ensure_sdl_hints()
    pygame.init()
    pygame.joystick.init()
    try:
        from pygame._sdl2 import controller as ctl

        if not ctl.get_init():
            ctl.init()
    except ImportError:
        ctl = None

    print("=== The Kit — diagnostic manette ===\n")
    print(f"Joysticks SDL : {pygame.joystick.get_count()}")
    for i in range(pygame.joystick.get_count()):
        j = pygame.joystick.Joystick(i)
        j.init()
        print(
            f"  [{i}] {j.get_name()} | buttons={j.get_numbuttons()} "
            f"hats={j.get_numhats()} axes={j.get_numaxes()}"
        )
        if j.get_numhats():
            print(f"      hat0={j.get_hat(0)}")
        pressed = [b for b in range(j.get_numbuttons()) if j.get_button(b)]
        if pressed:
            print(f"      boutons actifs : {pressed}")

    if ctl is not None:
        print(f"\nGameControllers SDL : {ctl.get_count()}")
        for i in range(ctl.get_count()):
            name = ctl.name_forindex(i) or "?"
            is_gc = ctl.is_controller(i)
            print(f"  [{i}] {name} | is_controller={is_gc}")
            if is_gc:
                c = ctl.Controller(i)
                c.init()
                dpad = {
                    d: c.get_button(b)
                    for b, d in DPAD_BUTTON_TO_DIRECTION.items()
                    if c.get_button(b)
                }
                if dpad:
                    print(f"      d-pad actif : {dpad}")
                raw = [b for b in range(20) if c.get_button(b)]
                if raw:
                    print(f"      boutons SDL (0-19) actifs : {raw}")
                c.quit()

    print("\n--- Test backends The Kit ---")
    for backend_cls in (SdlGameControllerBackend, PygameJoystickBackend, PyJoyConBackend):
        b = backend_cls()
        ok = b.open()
        print(f"  {backend_cls.name}: {'OK' if ok else 'indisponible'} — {b.status()}")
        if ok:
            b.close()

    print(f"\nAppuyez sur la croix / flèches ({duration_s:.0f} s). Ctrl+C pour quitter.\n")
    from the_kit.io.gamepad.core import init_gamepad, poll_direction

    init_gamepad(preference="auto")
    end = time.perf_counter() + duration_s
    try:
        while time.perf_counter() < end:
            pygame.event.pump()
            events = pygame.event.get()
            d = poll_direction(events=events)
            if d:
                print(f"  → {d}")
            time.sleep(0.02)
    except KeyboardInterrupt:
        print("\n(interrompu)")
    print("\nTerminé.")
    return 0


def main() -> int:
    duration = 30.0
    if len(sys.argv) > 1:
        try:
            duration = float(sys.argv[1])
        except ValueError:
            pass
    return run_gamepad_check(duration_s=duration)
