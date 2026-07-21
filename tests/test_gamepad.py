from the_kit.io import gamepad


def test_button_map_joycon_left():
    m = gamepad._button_map_for_name("Nintendo Switch Joy-Con (L)")
    assert m[2] == "AP"
    assert m[1] == "PA"
    assert m[3] == "LATG"
    assert m[0] == "LATD"


def test_button_map_wireless_gamepad():
    m = gamepad._button_map_for_name("Wireless Gamepad")
    assert m == gamepad.JOYCON_L_SDL224


def test_direction_from_buttons():
    class FakeJoy:
        def get_numbuttons(self):
            return 4

        def get_button(self, i):
            return i == 2  # Up

    assert gamepad._direction_from_buttons(FakeJoy(), gamepad.JOYCON_L_SDL224) == "AP"


def test_direction_from_button_event_uses_active_map():
    gamepad._button_map = {1: "PA"}
    assert gamepad._direction_from_button_event(1) == "PA"
    gamepad._button_map = {}
