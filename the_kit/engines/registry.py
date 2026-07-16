from __future__ import annotations

from the_kit.engines.base import EngineBase


def get_engine(name: str) -> type[EngineBase]:
    if name == "qt":
        from the_kit.engines.qt_engine import QtEngine

        return QtEngine
    if name == "pygame":
        from the_kit.engines.pygame_engine import PygameEngine

        return PygameEngine
    if name == "psychopy":
        from the_kit.engines.psychopy_engine import PsychoPyEngine

        return PsychoPyEngine
    if name == "python":
        from the_kit.engines.python_engine import PythonEngine

        return PythonEngine
    raise ValueError(f"Moteur inconnu ou non installé: {name}")


def check_engines() -> dict[str, tuple[bool, str]]:
    from the_kit.engines.pygame_engine import PygameEngine
    from the_kit.engines.psychopy_engine import PsychoPyEngine
    from the_kit.engines.python_engine import PythonEngine
    from the_kit.engines.qt_engine import QtEngine

    return {
        "qt": QtEngine.check_available(),
        "pygame": PygameEngine.check_available(),
        "psychopy": PsychoPyEngine.check_available(),
        "python": PythonEngine.check_available(),
    }
