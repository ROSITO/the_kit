"""Exécution blocs labo / chirurgie pour Time, Chrono, Tone."""

from __future__ import annotations

import json
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
from the_kit.manips.extrapolation.secondary import (
    SecondaryResult,
    run_change_detection_post,
    run_change_detection_pre,
    run_secondary_mock,
)
from the_kit.manips.extrapolation.stimuli import (
    auto_input_enabled,
    run_chrono_pygame,
    run_time_pygame,
    run_tone_pygame,
    run_tone_trial,
    simulate_chrono_trial,
    simulate_time_trial,
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

# Papier : N=15 essais / condition unique
PAPER_TRIALS_PER_CONDITION = 15


def _use_mock(ctx: TaskContext) -> bool:
    if ctx.dry_run:
        return True
    if os.environ.get("THE_KIT_EXTRAPOLATION_MOCK", "").strip().lower() in ("1", "true", "yes"):
        return True
    return False


def _smoke_cap_n(n: int, *, dry_run: bool) -> int:
    """Dry-run / SMOKE : plafonne N pour tests rapides ; production = 15."""
    if os.environ.get("THE_KIT_EXTRAPOLATION_FULL_N", "").strip().lower() in ("1", "true", "yes"):
        return max(1, n)
    if dry_run or os.environ.get("THE_KIT_EXTRAPOLATION_SMOKE", "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        return 1
    return max(1, n)


def _want_pygame(ctx: TaskContext) -> bool:
    if _use_mock(ctx) and not auto_input_enabled():
        # mock pur sans auto-input → pas de pygame
        if os.environ.get("THE_KIT_EXTRAPOLATION_FORCE_PYGAME", "").strip() not in ("1", "true"):
            return False
    try:
        import pygame  # noqa: F401

        return True
    except ImportError:
        return False


def _script_args(ctx: TaskContext) -> dict[str, Any]:
    return dict(ctx.node.params.get("script", {}).get("args") or {})


def _prompt_chirurgie_args(
    args: dict[str, Any],
    *,
    interactive: bool,
    input_fn=None,
) -> dict[str, Any]:
    """Questions lancement chirurgie.

    - interactive + TTY : input()
    - THE_KIT_CHIRURGIE_ANSWERS='{"temps_court_s":0.9,...}' pour tests / batch
    """
    out = {
        "temps_court_s": float(args.get("temps_court_s", 0.95)),
        "temps_long_s": float(args.get("temps_long_s", 1.85)),
        "n_zones": int(args.get("n_zones", 2)),
        "n_essais_par_condition": int(args.get("n_essais_par_condition", PAPER_TRIALS_PER_CONDITION)),
        "secondary_option": int(args.get("secondary_option", 0)),
    }
    env_raw = os.environ.get("THE_KIT_CHIRURGIE_ANSWERS", "").strip()
    if env_raw:
        try:
            payload = json.loads(env_raw)
            for k in out:
                if k in payload:
                    out[k] = type(out[k])(payload[k])
            out["_source"] = "env"
            return out
        except json.JSONDecodeError:
            pass

    if not interactive:
        out["_source"] = "protocol_args"
        return out

    ask = input_fn or input
    print("=== Chirurgie éveillée — paramètres de lancement ===")
    for key, cast, label in (
        ("temps_court_s", float, "Temps court (s)"),
        ("temps_long_s", float, "Temps long (s)"),
        ("n_zones", int, "Nombre de zones stimulées"),
        ("n_essais_par_condition", int, "Essais par condition"),
        ("secondary_option", int, "Option secondaire (0/1/2)"),
    ):
        raw = ask(f"{label} [{out[key]}]: ").strip()
        if raw:
            out[key] = cast(raw)
    out["_source"] = "prompt"
    return out


def _init_pygame():
    import pygame

    if not pygame.get_init():
        # headless : SDL_VIDEODRIVER=dummy
        if not os.environ.get("SDL_VIDEODRIVER"):
            # ne force pas dummy si un vrai display peut exister
            pass
        try:
            pygame.init()
        except pygame.error:
            os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
            pygame.init()
    info = pygame.display.Info()
    w = min(960, getattr(info, "current_w", 960) or 960)
    h = min(540, getattr(info, "current_h", 540) or 540)
    if w <= 0 or h <= 0:
        w, h = 960, 540
    screen = pygame.display.set_mode((w, h))
    pygame.display.set_caption("The Kit — extrapolation")
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
    use_pg = pygame_state is not None and (not mock or auto_input_enabled())
    secondary = SecondaryResult()
    cd_state = None

    # Option 2 pré-flash
    if trial.secondary_option == 2:
        if use_pg:
            _pg, screen, clock = pygame_state
            flash = 0.05 if auto_input_enabled() or mock else 0.5
            cd_state = run_change_detection_pre(screen, clock, flash_s=flash)
        else:
            secondary = run_secondary_mock(2, rng=random.Random(trial.trial_index))

    play_audio = bool(args.get("play_audio", True)) and not mock and not ctx.dry_run

    if modality == "time":
        if use_pg:
            _pg, screen, clock = pygame_state
            outcome = run_time_pygame(trial, screen=screen, clock=clock)
            if trial.secondary_option == 1 and outcome.secondary:
                secondary = outcome.secondary
        else:
            if trial.secondary_option == 1:
                secondary = run_secondary_mock(1, rng=random.Random(trial.trial_index))
            outcome = simulate_time_trial(trial, secondary=secondary)
    elif modality == "chrono":
        if use_pg:
            _pg, screen, clock = pygame_state
            outcome = run_chrono_pygame(
                trial,
                screen=screen,
                clock=clock,
                initial_value=float(args.get("initial_value", 1000)),
                increment_per_s=float(args.get("increment_per_s", 10)),
                pre_mask_s=float(args.get("pre_mask_s", 1.0)),
            )
            if trial.secondary_option == 1 and outcome.secondary:
                secondary = outcome.secondary
        else:
            if trial.secondary_option == 1:
                secondary = run_secondary_mock(1, rng=random.Random(trial.trial_index))
            outcome = simulate_chrono_trial(
                trial,
                initial_value=float(args.get("initial_value", 1000)),
                increment_per_s=float(args.get("increment_per_s", 10)),
                pre_mask_s=float(args.get("pre_mask_s", 1.0)),
                secondary=secondary,
            )
    else:  # tone
        if use_pg:
            _pg, screen, clock = pygame_state
            if trial.secondary_option == 1:
                from the_kit.manips.extrapolation.secondary import run_green_circle_during

                dur = 0.05 if (auto_input_enabled() or mock) else float(trial.mask_duration_s)
                secondary = run_green_circle_during(screen, clock, duration_s=dur)
            outcome = run_tone_pygame(
                trial,
                screen=screen,
                clock=clock,
                f0_hz=float(args.get("f0_hz", TONE_F0_HZ)),
                rise_semitones_per_s=float(args.get("rise_semitones_per_s", TONE_RISE_SEMITONES_PER_S)),
                pre_mask_s=float(args.get("pre_mask_s", 1.0)),
                mock_audio=not play_audio,
                secondary=secondary,
            )
        else:
            if trial.secondary_option == 1:
                secondary = run_secondary_mock(1, rng=random.Random(trial.trial_index))
            outcome = run_tone_trial(
                trial,
                f0_hz=float(args.get("f0_hz", TONE_F0_HZ)),
                rise_semitones_per_s=float(args.get("rise_semitones_per_s", TONE_RISE_SEMITONES_PER_S)),
                pre_mask_s=float(args.get("pre_mask_s", 1.0)),
                mock_audio=not play_audio,
                secondary=secondary,
            )

    # Option 2 post
    if trial.secondary_option == 2 and cd_state is not None and use_pg:
        _pg, screen, clock = pygame_state
        secondary = run_change_detection_post(
            screen,
            clock,
            cd_state,
            auto=auto_input_enabled() or mock,
        )

    if outcome.secondary and trial.secondary_option == 1:
        secondary = outcome.secondary

    exp = expected_side(modality, trial.delta_time_s)
    correct = None if exp == "exact" else (outcome.response == exp)
    return {
        "outcome": outcome,
        "secondary": secondary,
        "expected_side": exp,
        "correct": correct,
        "mock": mock and not use_pg,
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
        secondary_responded=secondary.responded,
        mock=result["mock"],
    )


def run_lab_block(ctx: TaskContext, *, modality: Modality) -> NodeResult:
    args = _script_args(ctx)
    deltas = args.get("delta_times_s") or list(DEFAULT_DELTA_TIMES_S)
    n_req = int(args.get("trials_per_condition", PAPER_TRIALS_PER_CONDITION))
    n = _smoke_cap_n(n_req, dry_run=ctx.dry_run)
    ctx.variables["trials_per_condition_requested"] = n_req
    ctx.variables["trials_per_condition_effective"] = n
    trials = build_lab_trials(
        delta_times_s=list(deltas),
        trials_per_condition=n,
        secondary_option=int(args.get("secondary_option", 0)),
        mask_duration_s=float(args.get("mask_duration_s", NOMINAL_MASK_S)),
        modality=modality,
    )
    return _execute_trials(ctx, modality=modality, version="lab", trials=trials, args=args)


def run_chirurgie_block(ctx: TaskContext, *, modality: Modality) -> NodeResult:
    args = _script_args(ctx)
    # prompt_launch défaut True pour chirurgie ; dry-run / mock → args JSON ou env
    want_prompt = bool(args.get("prompt_launch", True))
    interactive = want_prompt and not ctx.dry_run and not _use_mock(ctx)
    carg = _prompt_chirurgie_args(args, interactive=interactive)
    args.update(carg)
    n_req = int(carg["n_essais_par_condition"])
    n = _smoke_cap_n(n_req, dry_run=ctx.dry_run)
    carg["n_essais_par_condition"] = n
    trials = build_chirurgie_trials(
        temps_court_s=float(carg["temps_court_s"]),
        temps_long_s=float(carg["temps_long_s"]),
        n_zones=int(carg["n_zones"]),
        n_essais_par_condition=n,
        secondary_option=int(carg.get("secondary_option", args.get("secondary_option", 0))),
        modality=modality,
        mask_duration_s=float(args.get("mask_duration_s", NOMINAL_MASK_S)),
    )
    ctx.variables["chirurgie_params"] = {k: v for k, v in carg.items() if not str(k).startswith("_")}
    ctx.variables["chirurgie_prompt_source"] = carg.get("_source")
    ctx.variables["chirurgie_plan"] = [t.as_dict() for t in trials]
    ctx.variables["trials_per_condition_requested"] = n_req
    ctx.variables["trials_per_condition_effective"] = n
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
    want_pg = _want_pygame(ctx)
    # Tone aussi via pygame pour jugement écran
    pygame_state = None
    if want_pg:
        try:
            pygame_state = _init_pygame()
        except Exception as exc:
            ctx.log.event("extrapolation_pygame_fallback", error=str(exc))
            pygame_state = None

    trials_path = Path(ctx.session.session_dir) / "trials.csv"
    init_trials_csv(trials_path)
    ctx.variables["manip"] = MANIP_LABELS[modality]
    ctx.variables["version"] = version
    ctx.variables["n_trials"] = len(trials)
    ctx.variables["trials_csv"] = str(trials_path)
    ctx.variables["mock"] = mock and pygame_state is None

    ctx.log.event(
        "extrapolation_block_start",
        manip=MANIP_LABELS[modality],
        version=version,
        n_trials=len(trials),
        mock=ctx.variables["mock"],
        pygame=pygame_state is not None,
        auto_input=auto_input_enabled(),
        args={k: args[k] for k in args if k != "delta_times_s"},
        delta_times_s=args.get("delta_times_s") or list(DEFAULT_DELTA_TIMES_S),
    )

    for trial in trials:
        result = _run_one_trial(
            ctx,
            modality=modality,
            trial=trial,
            args=args,
            mock=mock,
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
