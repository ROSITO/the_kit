from the_kit.display.manager import DisplayManager


class _FakeSession:
    def __init__(self):
        self.events = []

    def log_event(self, event, **kwargs):
        self.events.append((event, kwargs))


def test_handoff_runs_cleanup_between_engines():
    session = _FakeSession()
    dm = DisplayManager(session, blank_ms=0)
    calls = []

    dm.register_cleanup(lambda: calls.append("qt"))
    dm.handoff("qt", "pygame")

    assert calls == ["qt"]
    assert dm._cleanup_callbacks == []


def test_handoff_same_engine_keeps_cleanup():
    session = _FakeSession()
    dm = DisplayManager(session, blank_ms=0)
    calls = []

    dm.register_cleanup(lambda: calls.append("pygame"))
    dm.handoff("pygame", "pygame")

    assert calls == []
    assert len(dm._cleanup_callbacks) == 1
