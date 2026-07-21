from the_kit.io.gamepad.backends import (
    JOYCON_L_SDL224,
    PygameJoystickBackend,
    SdlGameControllerBackend,
)


def test_button_map_joycon_left():
    m = PygameJoystickBackend._button_map_for_name("Nintendo Switch Joy-Con (L)")
    assert m[2] == "AP"
    assert m[1] == "PA"
    assert m[3] == "LATG"
    assert m[0] == "LATD"


def test_button_map_wireless_gamepad():
    m = PygameJoystickBackend._button_map_for_name("Wireless Gamepad")
    assert m == JOYCON_L_SDL224


def test_direction_from_buttons():
    class FakeJoy:
        def get_numbuttons(self):
            return 4

        def get_button(self, i):
            return i == 2

    backend = PygameJoystickBackend()
    backend._joy = FakeJoy()
    backend._button_map = JOYCON_L_SDL224
    assert backend._direction_from_buttons() == "AP"


def test_sdl_dpad_constants():
    from the_kit.io.gamepad.backends import DPAD_BUTTON_TO_DIRECTION, SDL_DPAD_UP

    assert SDL_DPAD_UP == 11
    assert DPAD_BUTTON_TO_DIRECTION[11] == "AP"


def test_init_gamepad_smoke():
    from the_kit.io.gamepad.core import init_gamepad, poll_direction

    import pygame

    pygame.init()
    init_gamepad(preference="auto")
    assert poll_direction() is None or poll_direction() in ("AP", "PA", "LATG", "LATD")
