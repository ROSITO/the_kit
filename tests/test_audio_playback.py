import platform
from pathlib import Path
from unittest import mock

from the_kit.audio.playback import is_portaudio_available, resolve_audio_backend


def test_resolve_audio_backend_pygame_explicit():
    assert resolve_audio_backend({"backend": "pygame"}) == "pygame"


def test_resolve_audio_backend_auto_without_sounddevice():
    with mock.patch("the_kit.audio.playback.is_portaudio_available", return_value=False):
        assert resolve_audio_backend({"backend": "auto"}) == "pygame"


def test_resolve_audio_backend_auto_windows_with_sounddevice():
    with (
        mock.patch("the_kit.audio.playback.is_portaudio_available", return_value=True),
        mock.patch("the_kit.audio.playback.platform.system", return_value="Windows"),
    ):
        assert resolve_audio_backend({"backend": "auto"}) == "portaudio"


def test_play_cue_missing_file(capsys):
    from the_kit.audio.playback import play_cue_file

    meta = play_cue_file(Path("/nonexistent/file.mp3"))
    assert meta.get("missing") is True
    assert "missing file" in capsys.readouterr().out


def test_is_portaudio_available():
    # smoke — dépend de l'environnement de test
    assert isinstance(is_portaudio_available(), bool)
