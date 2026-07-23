"""
Bloc GVS NeuroConn + fNIRS — baseline, rampe 10 s, réponse après consigne audio.

50 essais (10 × 5 conditions), ordre aléatoire.
"""

from __future__ import annotations

import random
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from the_kit.logging.session import SessionLogger
    from the_kit.protocol.models import Node

GVS_CONDITIONS = ("AP", "PA", "LATD", "LATG", "CONTROL")

DEFAULT_SOUNDS = {
    "debut_dexpe": "debut_dexpe.mp3",
    "vous_pouvez_repondre": "vous_pouvez_repondre.mp3",
    "votre_reponse": "Votre_reponse.mp3",
    "fin_du_temps": "fin_du_temps.mp3",
}


def _normalize_conditions(raw: Any) -> list[str]:
    """Valide et normalise la liste de conditions du protocole."""
    if raw is None:
        return list(GVS_CONDITIONS)
    if isinstance(raw, str):
        items = [raw]
    elif isinstance(raw, (list, tuple)):
        items = list(raw)
    else:
        raise ValueError(f"conditions invalides (attendu liste) : {raw!r}")
    if not items:
        raise ValueError("conditions : liste vide")
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        name = str(item).strip().upper()
        if name not in GVS_CONDITIONS:
            raise ValueError(
                f"condition inconnue {item!r} — autorisées : {', '.join(GVS_CONDITIONS)}"
            )
        if name not in seen:
            out.append(name)
            seen.add(name)
    return out


def _build_trial_list(
    reps: int,
    seed: int | None,
    *,
    conditions: list[str] | None = None,
) -> list[str]:
    conds = conditions if conditions is not None else list(GVS_CONDITIONS)
    trials = [c for c in conds for _ in range(reps)]
    rng = random.Random(seed)
    rng.shuffle(trials)
    return trials


def _iti_duration_s(base: float, jitter: tuple[float, float], rng: random.Random) -> float:
    lo, hi = jitter
    return base + rng.uniform(lo, hi)


def _audio_path(session: SessionLogger, p: dict[str, Any], key: str) -> Path:
    sounds = p.get("sounds") or {}
    rel = sounds.get(key, DEFAULT_SOUNDS[key])
    return (session.protocol.root / rel).resolve()


def _draw_fixation(
    screen,
    font,
    w: int,
    h: int,
    *,
    title: str = "",
    hint: str = "",
) -> None:
    import pygame

    screen.fill((0, 0, 0))
    cx, cy = w // 2, h // 2
    pygame.draw.line(screen, (200, 200, 200), (cx - 12, cy), (cx + 12, cy), 2)
    pygame.draw.line(screen, (200, 200, 200), (cx, cy - 12), (cx, cy + 12), 2)
    if title:
        screen.blit(font.render(title, True, (160, 160, 160)), (20, 20))
    if hint:
        screen.blit(font.render(hint, True, (100, 100, 100)), (20, 50))
    pygame.display.flip()


def _pump_events(screen, clock, *, allow_escape: bool = True) -> bool:
    """Retourne True si abort (ESC/QUIT)."""
    import pygame

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return True
        if allow_escape and event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return True
    return False


def _play_cue(
    path: Path,
    screen,
    clock,
    font,
    w: int,
    h: int,
    *,
    hint: str = "",
    audio_cfg: dict[str, Any] | None = None,
    skip: bool = False,
) -> None:
    if skip:
        _draw_fixation(screen, font, w, h, hint=hint or "cue")
        clock.tick(60)
        return
    from the_kit.audio.playback import play_cue_file

    def _on_frame() -> bool:
        if _pump_events(screen, clock):
            return True
        _draw_fixation(screen, font, w, h, hint=hint)
        clock.tick(60)
        return False

    play_cue_file(path, audio_cfg, on_frame=_on_frame)


def _wait_seconds(
    duration_s: float,
    screen,
    clock,
    font,
    w: int,
    h: int,
    *,
    title: str = "",
    hint: str = "",
) -> bool:
    """Attendre avec fixation. Retourne True si abort."""
    end = time.perf_counter() + duration_s
    while time.perf_counter() < end:
        if _pump_events(screen, clock):
            return True
        remaining = max(0.0, end - time.perf_counter())
        _draw_fixation(
            screen,
            font,
            w,
            h,
            title=title,
            hint=hint or f"{remaining:.0f} s",
        )
        clock.tick(60)
    return False


def _run_baseline(
    session: SessionLogger,
    node: Node,
    *,
    duration_s: float,
    screen,
    clock,
    font,
    w: int,
    h: int,
) -> bool:
    from the_kit.io import gvs_lsl

    gvs_lsl.baseline_start()
    session.log_event(
        "gvs_baseline_start",
        node_id=node.node_id,
        node_type=node.type,
        node_index=node.index,
        engine=node.engine,
        payload={"duration_s": duration_s},
    )
    aborted = _wait_seconds(
        duration_s,
        screen,
        clock,
        font,
        w,
        h,
        title="Baseline",
        hint="Fixation",
    )
    gvs_lsl.baseline_end()
    session.log_event(
        "gvs_baseline_end",
        node_id=node.node_id,
        node_type=node.type,
        node_index=node.index,
        engine=node.engine,
        payload={"duration_s": duration_s, "aborted": aborted},
    )
    return aborted


def run_neuroconn_gvs_node(
    node: Node,
    session: SessionLogger,
    *,
    screen,
    clock,
) -> None:
    import pygame

    from the_kit.io import gvs_lsl, nidaqmx_io
    from the_kit.io.gamepad import direction_label, poll_direction

    p = node.params
    amplitude = float(p.get("amplitude", 1.2))
    reps = int(p.get("repetitions_per_condition", 10))
    rise_s = float(p.get("rise_s", 3.0))
    plateau_s = float(p.get("plateau_s", 4.0))
    fall_s = float(p.get("fall_s", 3.0))
    iti_base = float(p.get("iti_base_s", 10.0))
    iti_jitter = tuple(p.get("iti_jitter_s", [1.0, 5.0]))
    baseline_s = float(p.get("baseline_s", 60.0))
    response_window_s = float(p.get("response_window_s", 5.0))
    seed = p.get("random_seed")
    rng = random.Random(seed)
    conditions = _normalize_conditions(p.get("conditions"))
    auto_respond = bool(p.get("auto_respond", False))
    skip_sounds = bool(p.get("skip_sounds", False)) or auto_respond

    trials = _build_trial_list(reps, seed, conditions=conditions)

    def _abort(trial_i: int | None = None) -> None:
        gvs_lsl.push(gvs_lsl.GVS_BLOCK_END, label="aborted")
        session.log_event(
            "node_end",
            node_id=node.node_id,
            node_type=node.type,
            node_index=node.index,
            engine=node.engine,
            payload={"aborted": True, "trial": trial_i},
        )

    from the_kit.audio.playback import audio_config_from_session, resolve_audio_backend
    from the_kit.io.gamepad import init_gamepad, joystick_status

    gamepad_pref = str(p.get("gamepad_backend", "auto"))
    init_gamepad(preference=gamepad_pref)
    pad_status = joystick_status()

    session.log_event(
        "node_start",
        node_id=node.node_id,
        node_type=node.type,
        node_index=node.index,
        engine=node.engine,
        payload={
            "trials": len(trials),
            "amplitude": amplitude,
            "baseline_s": baseline_s,
            "response_window_s": response_window_s,
            "conditions": list(conditions),
            "repetitions_per_condition": reps,
            "gamepad": pad_status,
            "auto_respond": auto_respond,
            "skip_sounds": skip_sounds,
        },
    )
    gvs_lsl.push(gvs_lsl.GVS_BLOCK_START, label="gvs_block_start")

    audio_cfg = audio_config_from_session(session, node)
    if p.get("audio"):
        audio_cfg = {**audio_cfg, **p["audio"]}

    font = pygame.font.SysFont(None, 28)
    w, h = screen.get_size()

    audio_backend = resolve_audio_backend(audio_cfg)
    session.log_event(
        "gvs_audio_backend",
        node_id=node.node_id,
        node_type=node.type,
        node_index=node.index,
        engine=node.engine,
        payload={"backend": audio_backend, "audio_cfg": {k: audio_cfg[k] for k in audio_cfg if k != "audio_device_query"}},
    )

    # Début expérience : son + baseline 60 s (trigger 1 début/fin)
    _play_cue(
        _audio_path(session, p, "debut_dexpe"),
        screen,
        clock,
        font,
        w,
        h,
        hint="Début expérience",
        audio_cfg=audio_cfg,
        skip=skip_sounds,
    )
    if _run_baseline(session, node, duration_s=baseline_s, screen=screen, clock=clock, font=font, w=w, h=h):
        _abort()
        return

    for trial_i, condition in enumerate(trials):
        session.log_event(
            "gvs_trial_start",
            node_id=node.node_id,
            node_type=node.type,
            node_index=node.index,
            engine=node.engine,
            payload={"trial": trial_i, "condition": condition},
        )

        stim_meta: dict[str, Any] = {}
        stim_error: list[Exception] = []

        def _run_stim() -> None:
            try:
                gvs_lsl.stim_onset(condition)
                stim_meta.update(
                    nidaqmx_io.send_ramp_stim(
                        direction=condition,
                        amplitude=amplitude,
                        rise_s=rise_s,
                        plateau_s=plateau_s,
                        fall_s=fall_s,
                    )
                )
            except Exception as exc:
                stim_error.append(exc)

        stim_t0 = time.perf_counter()
        stim_thread = threading.Thread(target=_run_stim, daemon=True)
        stim_thread.start()

        # Phase stim : pas de réponse
        while stim_thread.is_alive():
            if _pump_events(screen, clock):
                _abort(trial_i)
                return
            _draw_fixation(
                screen,
                font,
                w,
                h,
                title=f"Essai {trial_i + 1}/{len(trials)} — {direction_label(condition)}",
                hint="Stimulation en cours…",
            )
            clock.tick(60)
        stim_thread.join()
        if stim_error:
            raise stim_error[0]
        stim_duration_ms = int((time.perf_counter() - stim_t0) * 1000)

        # Consigne réponse puis fenêtre 5 s (décompte après le son)
        _play_cue(
            _audio_path(session, p, "vous_pouvez_repondre"),
            screen,
            clock,
            font,
            w,
            h,
            hint="Vous pouvez répondre",
            audio_cfg=audio_cfg,
            skip=skip_sounds,
        )
        response_t0 = time.perf_counter()
        response_dir: str | None = None
        rt_ms: int | None = None
        if auto_respond:
            # Simulation : réponse correcte (ou aléatoire pour CONTROL)
            if condition == "CONTROL":
                response_dir = rng.choice(["AP", "PA", "LATG", "LATD"])
            else:
                response_dir = condition
            rt_ms = int(rng.uniform(250, 900))
            time.sleep(min(0.05, response_window_s))
            # Trigger 8 immédiat (comme NIRS_experiment), avant le feedback audio
            gvs_lsl.response_perceived(
                response_dir,
                correct=None if condition == "CONTROL" else response_dir == condition,
            )
        else:
            response_end = response_t0 + response_window_s
            while time.perf_counter() < response_end:
                events = pygame.event.get()
                for event in events:
                    if event.type == pygame.QUIT:
                        _abort(trial_i)
                        return
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        _abort(trial_i)
                        return
                polled = poll_direction(events=events)
                if polled is not None:
                    response_dir = polled
                    rt_ms = int((time.perf_counter() - response_t0) * 1000)
                    # Trigger 8 au moment exact de la réponse (pas après le MP3)
                    gvs_lsl.response_perceived(
                        response_dir,
                        correct=None if condition == "CONTROL" else response_dir == condition,
                    )
                    break
                remaining = max(0.0, response_end - time.perf_counter())
                _draw_fixation(
                    screen,
                    font,
                    w,
                    h,
                    title=f"Essai {trial_i + 1}/{len(trials)}",
                    hint=f"Flèches — {remaining:.1f} s restantes",
                )
                clock.tick(60)

        if response_dir is not None:
            _play_cue(
                _audio_path(session, p, "votre_reponse"),
                screen,
                clock,
                font,
                w,
                h,
                audio_cfg=audio_cfg,
                skip=skip_sounds,
            )
        else:
            _play_cue(
                _audio_path(session, p, "fin_du_temps"),
                screen,
                clock,
                font,
                w,
                h,
                audio_cfg=audio_cfg,
                skip=skip_sounds,
            )
        correct = None if condition == "CONTROL" else (response_dir == condition if response_dir else None)
        session.log_response(
            node_index=node.index,
            node_type=node.type,
            node_id=node.node_id,
            stimulus=condition,
            response=response_dir or "",
            rt_ms=rt_ms,
            engine=node.engine,
        )
        session.log_event(
            "gvs_trial_end",
            node_id=node.node_id,
            node_type=node.type,
            node_index=node.index,
            engine=node.engine,
            payload={
                "trial": trial_i,
                "condition": condition,
                "response": response_dir,
                "rt_ms": rt_ms,
                "correct": correct,
                "stim_duration_ms": stim_duration_ms,
                "stim": stim_meta,
                "no_response": response_dir is None,
            },
        )

        if trial_i < len(trials) - 1:
            iti = _iti_duration_s(iti_base, iti_jitter, rng)
            gvs_lsl.iti_start(iti)
            if _wait_seconds(iti, screen, clock, font, w, h, title="Pause", hint="ITI"):
                _abort(trial_i)
                return

    gvs_lsl.push(gvs_lsl.GVS_BLOCK_END, label="gvs_block_end")
    session.log_event(
        "node_end",
        node_id=node.node_id,
        node_type=node.type,
        node_index=node.index,
        engine=node.engine,
        payload={"trials_completed": len(trials)},
    )
