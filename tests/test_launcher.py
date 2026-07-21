from pathlib import Path

from the_kit.cli import build_parser


def test_launch_command_registered():
    parser = build_parser()
    args = parser.parse_args(["launch"])
    assert args.command == "launch"
    assert callable(args.func)


def test_launcher_module_import():
    from the_kit.launcher import run_launcher
    from the_kit.launcher.app import _python_executable

    assert callable(run_launcher)
    assert Path(_python_executable()).name.lower() in ("python", "python.exe", "python3", "python3.exe")
