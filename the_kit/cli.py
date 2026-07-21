from __future__ import annotations

import argparse
import sys
from pathlib import Path

from the_kit import __version__
from the_kit.engines.registry import check_engines
from the_kit.orchestrator import Orchestrator
from the_kit.protocol.loader import load_protocol, migrate_arome_v0
from the_kit.protocol.validator import ProtocolValidationError, validate_protocol, validate_protocol_file


def _the_kit_root() -> Path:
    return Path(__file__).resolve().parents[1]


def cmd_run(args: argparse.Namespace) -> int:
    session_dir = Path(args.session_dir) if args.session_dir else None
    try:
        orch = Orchestrator.from_protocol_file(
            args.protocol,
            subject_id=args.subject,
            subject_group=args.group,
            session_dir=session_dir,
            dry_run=args.dry_run,
            check_media=args.check_media,
            project_root=_the_kit_root(),
            export_artifacts=args.export_session,
        )
        out = orch.run()
        print(f"Session terminée : {out}")
        return 0
    except ProtocolValidationError as e:
        print("Protocole invalide :", file=sys.stderr)
        for err in e.errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Erreur : {e}", file=sys.stderr)
        return 1


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        protocol = validate_protocol_file(
            args.protocol, check_media=args.check_media
        )
        print(f"OK — {protocol.name} ({len(protocol.nodes)} nœuds, v{protocol.protocol_version})")
        if args.verbose:
            for n in protocol.nodes:
                print(f"  [{n.index}] {n.node_id} {n.type} engine={n.engine}")
        return 0
    except ProtocolValidationError as e:
        print("Invalide :", file=sys.stderr)
        for err in e.errors:
            print(f"  - {err}", file=sys.stderr)
        return 1


def cmd_check_engines(_args: argparse.Namespace) -> int:
    results = check_engines()
    required = ("qt", "python")
    for name, (available, msg) in results.items():
        status = "ok" if available else "missing"
        tag = "" if name in required else " (optionnel)"
        print(f"  {name}: {status}{tag} — {msg}")
    ok = all(results[n][0] for n in required)
    if not results["psychopy"][0]:
        print("  → PsychoPy (av_sync) : uv pip install 'psychopy==2023.2.3' moviepy")
    return 0 if ok else 1


def cmd_check_audio(_args: argparse.Namespace) -> int:
    try:
        import sounddevice as sd
    except ImportError:
        print("sounddevice non installé (uv sync --extra lowlatency)", file=sys.stderr)
        return 1
    from the_kit.audio.device_select import choose_device_os_aware
    from the_kit.audio.low_latency import list_output_devices

    idx, hostapi = choose_device_os_aware({})
    print(f"Périphérique sélectionné : index={idx} hostapi={hostapi}")
    if idx is not None:
        dev = sd.query_devices(idx)
        print(f"  Nom : {dev.get('name')}")
        print(f"  Taux par défaut : {dev.get('default_samplerate')} Hz")
    print("\nSorties disponibles :")
    for d in list_output_devices()[:8]:
        print(f"  [{d['index']}] {d['name']} ({d['hostapi']})")
    if "bluetooth" in str(hostapi).lower() or any(
        "bluetooth" in (d.get("name") or "").lower() for d in list_output_devices()
    ):
        print("\n⚠ Bluetooth détecté — éviter pour essais sync A/V.")
    return 0


def cmd_export_zip(args: argparse.Namespace) -> int:
    from the_kit.export import export_protocol_zip

    out = export_protocol_zip(args.protocol, args.output)
    print(f"Export : {out}")
    return 0


def cmd_import_p19(args: argparse.Namespace) -> int:
    from the_kit.protocol.importers import import_p19_config

    data = import_p19_config(args.config, name=args.name)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    import json

    out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Protocole écrit : {out} ({len(data.get('nodes', []))} nœuds)")
    return 0


def cmd_check_lsl(_args: argparse.Namespace) -> int:
    from the_kit.io import lsl

    if not lsl.is_available():
        print("pylsl non installé : uv pip install pylsl", file=sys.stderr)
        return 1
    ok, msg = lsl.init_from_config(
        {
            "enabled": True,
            "stream_name": "TheKit_Test",
            "stream_type": "Markers",
            "channel_count": 1,
            "channel_format": "float32",
            "source_id": "the_kit_check",
        }
    )
    print(f"LSL : {msg}")
    if ok:
        lsl.push_marker(99.0, label="check")
        print("Marqueur test 99.0 envoyé")
    lsl.shutdown()
    return 0 if ok else 1


def cmd_check_ni(_args: argparse.Namespace) -> int:
    from the_kit.io import nidaqmx_io

    ok, msg = nidaqmx_io.init_from_config(
        {
            "enabled": True,
            "simulation_mode": True,
            "device": "Dev1",
            "channels": ["ao0", "ao1"],
        },
        dry_run=True,
    )
    print(f"NI-DAQ : {msg}")
    if not nidaqmx_io.is_available():
        print("  nidaqmx non installé — uv sync --extra ni (Driver NI requis sur le poste)")
    nidaqmx_io.send_square_wave_stim(
        direction="AP",
        amplitude=0.8,
        duration_s=0.01,
        dry_run=True,
    )
    print("Onde test AP envoyée (simulation)")
    nidaqmx_io.shutdown()
    return 0 if ok else 1


def cmd_export_session(args: argparse.Namespace) -> int:
    from the_kit.session_export import export_session_artifacts

    paths = export_session_artifacts(
        args.session_dir,
        bids=True,
        html=True,
        task_name=args.task_name,
    )
    for kind, path in paths.items():
        print(f"{kind}: {path}")
    return 0


def cmd_launch(_args: argparse.Namespace) -> int:
    from the_kit.launcher.app import run_launcher

    return run_launcher() or 0


def cmd_design(args: argparse.Namespace) -> int:
    from the_kit.designer.app import run_designer

    return run_designer(args.protocol) or 0


def cmd_migrate_preview(args: argparse.Namespace) -> int:
    import json

    with open(args.protocol, encoding="utf-8") as f:
        data = json.load(f)
    migrated = migrate_arome_v0(data)
    print(json.dumps(migrated, indent=2, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="the_kit",
        description="The Kit — orchestrateur de manipulations psychophysiques",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Exécuter un protocole")
    p_run.add_argument("--protocol", "-p", required=True, help="Chemin protocol.json")
    p_run.add_argument("--subject", "-s", default="anonymous", help="ID participant")
    p_run.add_argument("--group", "-g", default=None, help="Groupe participant")
    p_run.add_argument("--session-dir", default=None, help="Dossier session de sortie")
    p_run.add_argument(
        "--dry-run",
        action="store_true",
        help="Simuler les triggers série (pas d'écriture COM)",
    )
    p_run.add_argument(
        "--check-media",
        action="store_true",
        help="Vérifier que les fichiers médias existent",
    )
    p_run.add_argument(
        "--export-session",
        action="store_true",
        help="Générer bids/ + session_report.html à la fin",
    )
    p_run.set_defaults(func=cmd_run)

    p_exs = sub.add_parser(
        "export-session",
        help="Exporter BIDS-like + rapport HTML d'une session existante",
    )
    p_exs.add_argument("--session-dir", "-d", required=True)
    p_exs.add_argument("--task-name", default=None)
    p_exs.set_defaults(func=cmd_export_session)

    p_val = sub.add_parser("validate", help="Valider un protocole sans l'exécuter")
    p_val.add_argument("--protocol", "-p", required=True)
    p_val.add_argument("--check-media", action="store_true")
    p_val.add_argument("-v", "--verbose", action="store_true")
    p_val.set_defaults(func=cmd_validate)

    p_ce = sub.add_parser("check-engines", help="Vérifier les moteurs installés")
    p_ce.set_defaults(func=cmd_check_engines)

    p_ca = sub.add_parser("check-audio", help="Vérifier PortAudio / WASAPI / Core Audio")
    p_ca.set_defaults(func=cmd_check_audio)

    p_mig = sub.add_parser(
        "migrate-preview",
        help="Afficher la migration Arôme v0 → v1 (debug)",
    )
    p_mig.add_argument("--protocol", "-p", required=True)
    p_mig.set_defaults(func=cmd_migrate_preview)

    p_exp = sub.add_parser("export-zip", help="Exporter protocole + assets en zip")
    p_exp.add_argument("--protocol", "-p", required=True)
    p_exp.add_argument("--output", "-o", required=True)
    p_exp.set_defaults(func=cmd_export_zip)

    p_imp = sub.add_parser("import-p19", help="Importer config P1-P9 → protocol.json")
    p_imp.add_argument("--config", "-c", required=True)
    p_imp.add_argument("--output", "-o", required=True)
    p_imp.add_argument("--name", default=None)
    p_imp.set_defaults(func=cmd_import_p19)

    p_launch = sub.add_parser("launch", help="Ouvrir le lanceur Qt (choix protocole + run)")
    p_launch.set_defaults(func=cmd_launch)

    p_des = sub.add_parser("design", help="Ouvrir le concepteur Qt")
    p_des.add_argument("--protocol", "-p", default=None)
    p_des.set_defaults(func=cmd_design)

    p_lsl = sub.add_parser("check-lsl", help="Tester stream LSL marqueurs")
    p_lsl.set_defaults(func=cmd_check_lsl)

    p_ni = sub.add_parser("check-ni", help="Tester module NI-DAQ (simulation)")
    p_ni.set_defaults(func=cmd_check_ni)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
