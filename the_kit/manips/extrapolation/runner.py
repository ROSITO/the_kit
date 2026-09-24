"""Exécution blocs labo / chirurgie pour Time, Chrono, Tone."""

from __future__ import annotations

import os
import random
from pathlib import Path
from typing import Any, TYPE_CHECKING

from the_kit.manips.extrapolation.constants import (
    DEFAULT_DELTA_TIMES_S,
    NOMINAL_MASK_S,
    TONE_F0_HZ,
    TONE_RISE_SEMITONES_PER_S,
)
from the_kit.manips.extrapolation.planning import (
    Modality,
    TrialSpec,
    build_chirurgie_trials,
    build_lab_trials,
    expected_side,
)
from the_kit.manips.extrapolation.secondary import run_secondary_mock, run_secondary_pygame
from the_kit.manips.extrapolation.stimuli import (
    run_chrono_pygame,
    run_time_pygame,
    simulate_chrono_trial,
    simulate_time_trial,
    simulate_tone_trial,
)
from the_kit.manips.extrapolation.trials_csv import append_trial_row, init_trials_csv
from the_kit.task_api import NodeResult

if TYPE_CHECKING:
    from the_kit.task_api import TaskContext

MANIP_LABELS = {
    "time": "spatiotemporel",
    "chrono": "nombre",
    "tone": "son",
}


def _use_mock(ctx: TaskContext) -> bool:
    if ctx.dry_run:
        return True
    if os.environ.get("THE_KIT_EXTRAPOLATION_MOCK", "").strip() in ("1", "true", "yes"):
        return True
    if os.environ.get("SDL_VIDEODRIVER", "").lower() == "dummy":
        # dummy OK for pygame; still allow interactive path if pygame present
        pass
    return False


def _want_pygame(ctx: TaskContext) -> bool:
    if _use_mock(ctx):
        return False
    if os.environ.get("THE_KIT_EXTRAPOLATION_MOCK", "").strip() in ("1", "true", "yes"):
        return False
    try:
        import pygame  # noqa: F401

        return True
    except ImportError:
        return False


def _script_args(ctx: TaskContext) -> dict[str, Any]:
    return dict(ctx.node.params.get("script", {}).get("args") or {})


def _prompt_chirurgie_args(args: dict[str, Any], *, interactive: bool) -> dict[str, Any]:
    """Questions lancement chirurgie — interactif si demandé, sinon JSON args."""
    out = {
        "temps_court_s": float(args.get("temps_court_s", 0.95)),
        "temps_long_s": float(args.get("temps_long_s", 1.85)),
        "n_zones": int(args.get("n_zones", 2)),
        "n_essais_par_condition": int(args.get("n_essais_par_condition", 1)),
        "secondary_option": int(args.get("secondary_option", 0)),
    }
    if not interactive:
        return out
    print("=== Chirurgie éveillée — paramètres ===")
    for key, cast, label in (
        ("temps_court_s", float, "Temps court (s)"),
        ("temps_long_s", float, "Temps long (s)"),
        ("n_zones", int, "Nombre de zones stimulées"),
        ("n_essais_par_condition", int, "Essais par condition"),
    ):
        raw = input(f"{label} [{out[key]}]: ").strip()
        if raw:
            out[key] = cast(raw)
    return out


def _init_pygame():
    import os

    import pygame

    if not pygame.get_init():
        # headless CI: allow SDL_VIDEODRIVER=dummy
        os.environ.setdefault("SDL_VIDEODRIVER", os.environ.get("SDL_VIDEODRIVER", "dummy"))
        try:
            pygame.init()
        except pygame.error:
            pygame.init()
    info = pygame.display.Info()
    w = min(960, getattr(info, "current_w", 960) or 960)
    h = min(540, getattr(info, "current_h", 540) or 540)
    screen = pygame.display.set_mode((w, h))
    clock = pygame.time.Clock()
    return pygame, screen, clock


def _run_one_trial(
    ctx: TaskContext,
    *,
    modality: Modality,
    trial: TrialSpec,
    args: dict[str, Any],
    mock: bool,
    pygame_state: tuple | None,
) -> dict[str, Any]:
    use_pg = pygame_state is not None and not mock
    secondary = None
    if use_pg and trial.secondary_option in (1, 2):
        _pygame, screen, clock = pygame_state
        secondary = run_secondary_pygame(
            trial.secondary_option,
            screen=screen,
            clock=clock,
            mask_duration_s=trial.mask_duration_s,
        )
    else:
        secondary = run_secondary_mock(trial.secondary_option, rng=random.Random(trial.trial_index))

    if modality == "time":
        if use_pg:
            _pygame, screen, clock = pygame_state
            outcome = run_time_pygame(trial, screen=screen, clock=clock)
        else:
            outcome = simulate_time_trial(trial)
    elif modality == "chrono":
        if use_pg:
            _pygame, screen, clock = pygame_state
            outcome = run_chrono_pygame(
                trial,
                screen=screen,
                clock=clock,
                initial_value=float(args.get("initial_value", 1000)),
                increment_per_s=float(args.get("increment_per_s", 10)),
                pre_mask_s=float(args.get("pre_mask_s", 1.0)),
            )
        else:
            outcome = simulate_chrono_trial(
                trial,
                initial_value=float(args.get("initial_value", 1000)),
                increment_per_s=float(args.get("increment_per_s", 10)),
                pre_mask_s=float(args.get("pre_mask_s", 1.0)),
            )
    else:
        outcome = simulate_tone_trial(
            trial,
            f0_hz=float(args.get("f0_hz", TONE_F0_HZ)),
            rise_semitones_per_s=float(args.get("rise_semitones_per_s", TONE_RISE_SEMITONES_PER_S)),
            pre_mask_s=float(args.get("pre_mask_s", 1.0)),
            mock_audio=mock or not bool(args.get("play_audio", False)),
        )

    exp = expected_side(modality, trial.delta_time_s)
    correct = None if exp == "exact" else (outcome.response == exp)
    return {
        "outcome": outcome,
        "secondary": secondary,
        "expected_side": exp,
        "correct": correct,
        "mock": mock or not use_pg,
    }


def _write_and_log_trial(
    ctx: TaskContext,
    *,
    modality: Modality,
    version: str,
    trial: TrialSpec,
    result: dict[str, Any],
    trials_path: Path,
) -> None:
    outcome = result["outcome"]
    secondary = result["secondary"]
    manip = MANIP_LABELS[modality]
    row = {
        "subject_id": ctx.subject_id,
        "manip": manip,
        "version": version,
        "trial_index": trial.trial_index,
        "delta_time_s": trial.delta_time_s,
        "mask_duration_s": trial.mask_duration_s,
        "zone": trial.zone if trial.zone is not None else "",
        "repetition": trial.repetition if trial.repetition is not None else "",
        "kind": trial.kind or "",
        "secondary_option": trial.secondary_option,
        "response": outcome.response,
        "rt_ms": outcome.rt_ms,
        "expected_side": result["expected_side"],
        "correct": result["correct"],
        "secondary_responded": secondary.responded,
        "secondary_rt_ms": secondary.rt_ms if secondary.rt_ms is not None else "",
        "secondary_correct": secondary.correct if secondary.correct is not None else "",
        "stim_params_json": outcome.stim_params,
        "mock": result["mock"],
    }
    append_trial_row(trials_path, row)
    ctx.session.log_response(
        node_index=ctx.node.index,
        node_type=ctx.node.type,
        node_id=ctx.node.node_id,
        stimulus=f"{manip}:{trial.delta_time_s}",
        response=outcome.response,
        rt_ms=int(outcome.rt_ms) if outcome.rt_ms is not None and outcome.rt_ms >= 0 else None,
        engine="python",
    )
    ctx.log.event(
        "extrapolation_trial",
        manip=manip,
        version=version,
        trial_index=trial.trial_index,
        delta_time_s=trial.delta_time_s,
        response=outcome.response,
        rt_ms=outcome.rt_ms,
        secondary_option=trial.secondary_option,
        mock=result["mock"],
    )


def run_lab_block(ctx: TaskContext, *, modality: Modality) -> NodeResult:
    args = _script_args(ctx)
    deltas = args.get("delta_times_s") or list(DEFAULT_DELTA_TIMES_S)
    trials = build_lab_trials(
        delta_times_s=list(deltas),
        trials_per_condition=int(args.get("trials_per_condition", 1)),
        secondary_option=int(args.get("secondary_option", 0)),
        mask_duration_s=float(args.get("mask_duration_s", NOMINAL_MASK_S)),
        modality=modality,
    )
    return _execute_trials(ctx, modality=modality, version="lab", trials=trials, args=args)


def run_chirurgie_block(ctx: TaskContext, *, modality: Modality) -> NodeResult:
    args = _script_args(ctx)
    interactive = bool(args.get("prompt_launch", False)) and not ctx.dry_run and not _use_mock(ctx)
    carg = _prompt_chirurgie_args(args, interactive=interactive)
    args.update(carg)
    trials = build_chirurgie_trials(
        temps_court_s=float(carg["temps_court_s"]),
        temps_long_s=float(carg["temps_long_s"]),
        n_zones=int(carg["n_zones"]),
        n_essais_par_condition=int(carg["n_essais_par_condition"]),
        secondary_option=int(carg.get("secondary_option", args.get("secondary_option", 0))),
        modality=modality,
        mask_duration_s=float(args.get("mask_duration_s", NOMINAL_MASK_S)),
    )
    ctx.variables["chirurgie_params"] = carg
    ctx.variables["chirurgie_plan"] = [t.as_dict() for t in trials]
    return _execute_trials(ctx, modality=modality, version="chirurgie_eveillee", trials=trials, args=args)


def _execute_trials(
    ctx: TaskContext,
    *,
    modality: Modality,
    version: str,
    trials: list[TrialSpec],
    args: dict[str, Any],
) -> NodeResult:
    mock = _use_mock(ctx)
    # force mock if few resources
    want_pg = _want_pygame(ctx) and modality in ("time", "chrono")
    pygame_state = None
    if want_pg and not mock:
        try:
            pygame_state = _init_pygame()
        except Exception as exc:
            ctx.log.event("extrapolation_pygame_fallback", error=str(exc))
            mock = True
            pygame_state = None

    trials_path = Path(ctx.session.session_dir) / "trials.csv"
    init_trials_csv(trials_path)
    ctx.variables["manip"] = MANIP_LABELS[modality]
    ctx.variables["version"] = version
    ctx.variables["n_trials"] = len(trials)
    ctx.variables["trials_csv"] = str(trials_path)
    ctx.variables["mock"] = mock or pygame_state is None

    ctx.log.event(
        "extrapolation_block_start",
        manip=MANIP_LABELS[modality],
        version=version,
        n_trials=len(trials),
        mock=ctx.variables["mock"],
        args={k: args[k] for k in args if k != "delta_times_s"},
        delta_times_s=args.get("delta_times_s") or list(DEFAULT_DELTA_TIMES_S),
    )

    for trial in trials:
        result = _run_one_trial(
            ctx,
            modality=modality,
            trial=trial,
            args=args,
            mock=ctx.variables["mock"],
            pygame_state=pygame_state,
        )
        _write_and_log_trial(
            ctx,
            modality=modality,
            version=version,
            trial=trial,
            result=result,
            trials_path=trials_path,
        )

    if pygame_state is not None:
        try:
            import pygame

            pygame.display.quit()
        except Exception:
            pass

    ctx.log.event(
        "extrapolation_block_end",
        manip=MANIP_LABELS[modality],
        version=version,
        n_trials=len(trials),
        trials_csv=str(trials_path),
    )
    return NodeResult(
        status="ok",
        data={
            "n_trials": len(trials),
            "trials_csv": str(trials_path),
            "manip": MANIP_LABELS[modality],
            "version": version,
            "mock": ctx.variables["mock"],
        },
    )
