from the_kit.cli import build_parser


def test_launch_command_registered():
    parser = build_parser()
    args = parser.parse_args(["launch"])
    assert args.command == "launch"
    assert callable(args.func)


def test_launcher_module_import():
    from the_kit.launcher import run_launcher

    assert callable(run_launcher)
