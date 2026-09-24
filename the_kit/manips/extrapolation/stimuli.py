"""Stimuli Time / Chrono / Tone — mock + interactif pygame / PortAudio."""

from __future__ import annotations

import math
import os
import time
from dataclasses import dataclass
from typing import Any, Callable

from the_kit.manips.extrapolation.constants import (
    NOMINAL_MASK_S,
    TONE_F0_HZ,
    TONE_RISE_SEMITONES_PER_S,
)
from the_kit.manips.extrapolation.planning import Modality, TrialSpec, expected_side
from the_kit.manips.extrapolation.secondary import (
    SecondaryResult,
    run_change_detection_post,
    run_change_detection_pre,
    run_green_circle_during,
    run_secondary_mock,
)


@dataclass
class TrialOutcome:
    response: str
    rt_ms: float
    stim_params: dict[str, Any]
    secondary: SecondaryResult | None = None


def auto_input_enabled() -> bool:
    """CI / headless : injecte une réponse sans attendre le clavier."""
    return os.environ.get("THE_KIT_EXTRAPOLATION_AUTO_INPUT", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _auto_response(modality: Modality, delta_time_s: float, *, rng_offset: float = 0.0) -> TrialOutcome:
    side = expected_side(modality, delta_time_s)
    if side == "exact":
        side = {
            "time": "trop_tot",
            "chrono": "trop_faible",
            "tone": "trop_grave",
        }[modality]
    rt = 250.0 + (abs(delta_time_s - NOMINAL_MASK_S) * 80.0) + rng_offset
    return TrialOutcome(response=side, rt_ms=round(rt, 1), stim_params={})


def simulate_time_trial(
    trial: TrialSpec,
    *,
    pre_mask_s: float = 0.4,
    secondary: SecondaryResult | None = None,
) -> TrialOutcome:
    speed = 100.0
    occ_w = speed * trial.delta_time_s
    params = {
        "ball_speed": speed,
        "occulter_width_px": occ_w,
        "pre_mask_s": pre_mask_s,
        "reappear_after_s": trial.delta_time_s,
        "mode": "mock",
    }
    out = _auto_response("time", trial.delta_time_s)
    out.stim_params = params
    out.secondary = secondary
    return out


def simulate_chrono_trial(
    trial: TrialSpec,
    *,
    initial_value: float = 1000.0,
    increment_per_s: float = 10.0,
    pre_mask_s: float = 1.0,
    secondary: SecondaryResult | None = None,
) -> TrialOutcome:
    v0 = float(initial_value)
    v = float(increment_per_s)
    value_at_reappear = int(round(v0 + v * trial.delta_time_s))
    value_nominal = int(round(v0 + v * NOMINAL_MASK_S))
    params = {
        "initial_value": v0,
        "increment_per_s": v,
        "pre_mask_s": pre_mask_s,
        "mask_duration_s": trial.mask_duration_s,
        "value_at_reappear": value_at_reappear,
        "value_nominal_1_5": value_nominal,
        "mode": "mock",
    }
    out = _auto_response("chrono", trial.delta_time_s)
    out.stim_params = params
    out.secondary = secondary
    return out


def _tone_hz(f0: float, rise_st_s: float, t_s: float) -> float:
    return f0 * (2.0 ** (rise_st_s * t_s / 12.0))


def synthesize_rising_tone(
    *,
    duration_s: float,
    f0_hz: float = TONE_F0_HZ,
    rise_semitones_per_s: float = TONE_RISE_SEMITONES_PER_S,
    sample_rate: int = 44100,
    amplitude: float = 0.2,
    start_t_s: float = 0.0,
) -> tuple[list[float], int]:
    """Ton montant : f(t) = f0 * 2^(v*(start_t+t)/12)."""
    n = max(1, int(max(duration_s, 0.001) * sample_rate))
    samples: list[float] = []
    phase = 0.0
    dt = 1.0 / sample_rate
    for i in range(n):
        t = start_t_s + i * dt
        freq = _tone_hz(f0_hz, rise_semitones_per_s, t)
        phase += 2.0 * math.pi * freq * dt
        samples.append(amplitude * math.sin(phase))
    return samples, sample_rate


def synthesize_pure_tone(
    *,
    duration_s: float,
    freq_hz: float,
    sample_rate: int = 44100,
    amplitude: float = 0.2,
) -> tuple[list[float], int]:
    n = max(1, int(max(duration_s, 0.001) * sample_rate))
    samples: list[float] = []
    phase = 0.0
    dt = 1.0 / sample_rate
    omega = 2.0 * math.pi * float(freq_hz)
    for _ in range(n):
        samples.append(amplitude * math.sin(phase))
        phase += omega * dt
    return samples, sample_rate


def play_samples_or_mock(samples: list[float], sample_rate: int, *, mock: bool) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "n_samples": len(samples),
        "sample_rate": sample_rate,
        "duration_s": len(samples) / sample_rate if sample_rate else 0.0,
        "played": False,
        "backend": "mock",
    }
    if mock:
        return meta
    try:
        import sounddevice as sd

        # sounddevice attend array-like ; liste float OK
        sd.play(samples, sample_rate, blocking=True)
        meta["played"] = True
        meta["backend"] = "sounddevice"
    except Exception as exc:
        meta["backend"] = f"mock_fallback:{type(exc).__name__}"
        meta["error"] = str(exc)
    return meta


def run_tone_trial(
    trial: TrialSpec,
    *,
    f0_hz: float = TONE_F0_HZ,
    rise_semitones_per_s: float = TONE_RISE_SEMITONES_PER_S,
    pre_mask_s: float = 1.0,
    mock_audio: bool = True,
    wait_response: Callable[[], tuple[str, float]] | None = None,
    secondary: SecondaryResult | None = None,
) -> TrialOutcome:
    """Tone complet : montée → silence mask → probe à f(DeltaTime) → jugement."""
    f_pre = _tone_hz(f0_hz, rise_semitones_per_s, pre_mask_s)
    f_reappear = _tone_hz(f0_hz, rise_semitones_per_s, trial.delta_time_s)
    f_nominal = _tone_hz(f0_hz, rise_semitones_per_s, NOMINAL_MASK_S)

    pre_dur = min(pre_mask_s, 0.12) if mock_audio else pre_mask_s
    probe_dur = 0.08 if mock_audio else 0.4
    samples_pre, sr = synthesize_rising_tone(
        duration_s=pre_dur,
        f0_hz=f0_hz,
        rise_semitones_per_s=rise_semitones_per_s,
    )
    audio_pre = play_samples_or_mock(samples_pre, sr, mock=mock_audio)

    # silence = mask (réel seulement si audio live)
    if not mock_audio:
        time.sleep(float(trial.mask_duration_s))

    probe, sr2 = synthesize_pure_tone(duration_s=probe_dur, freq_hz=f_reappear)
    audio_probe = play_samples_or_mock(probe, sr2, mock=mock_audio)

    params = {
        "f0_hz": f0_hz,
        "rise_semitones_per_s": rise_semitones_per_s,
        "pre_mask_s": pre_mask_s,
        "mask_duration_s": trial.mask_duration_s,
        "f_pre_hz": f_pre,
        "f_reappear_hz": f_reappear,
        "f_nominal_1_5_hz": f_nominal,
        "audio_pre": audio_pre,
        "audio_probe": audio_probe,
        "mode": "mock" if mock_audio else "portaudio",
    }

    if wait_response is not None:
        resp, rt = wait_response()
        out = TrialOutcome(response=resp, rt_ms=rt, stim_params=params, secondary=secondary)
        return out

    out = _auto_response("tone", trial.delta_time_s)
    out.stim_params = params
    out.secondary = secondary
    return out


# alias rétrocompat
simulate_tone_trial = run_tone_trial


def _poll_judgment_keys(pygame_mod, mapping: dict[int, str], *, auto: bool, modality: Modality, delta: float) -> str | None:
    if auto:
        side = expected_side(modality, delta)
        if side == "exact":
            return next(iter(mapping.values()))
        # map expected label to first matching value
        for _k, v in mapping.items():
            if v == side:
                return v
        return next(iter(mapping.values()))
    for event in pygame_mod.event.get():
        if event.type == pygame_mod.QUIT:
            return "abort"
        if event.type == pygame_mod.KEYDOWN and event.key in mapping:
            return mapping[event.key]
    return None


def run_time_pygame(
    trial: TrialSpec,
    *,
    screen,
    clock,
    response_keys: dict[str, int] | None = None,
    auto: bool | None = None,
) -> TrialOutcome:
    """Essai Time interactif ; option 1 = cercle vert pendant occultation."""
    import pygame

    auto = auto_input_enabled() if auto is None else auto
    p_speed = 120.0
    w, h = screen.get_size()
    # En auto/CI : compresser le timing pour tests rapides (jugement inchangé)
    occ_time = 0.05 if auto else float(trial.delta_time_s)
    occ_w = max(40, int(p_speed * max(occ_time, 0.05)))
    ball_size = 20
    bg = (240, 240, 240)
    ball_c = (0, 0, 220)
    occ_c = (180, 180, 180)
    ball_y = h // 2
    occ_x = w // 2 - occ_w // 2
    occ_rect = pygame.Rect(occ_x, ball_y - 28, occ_w, 56)
    reappear_x = occ_x + occ_w
    time_approach = 0.02 if auto else 0.6
    start_x = occ_x - p_speed * time_approach
    time_to_occ = time_approach
    time_to_reappear = time_to_occ + occ_time
    font = pygame.font.SysFont(None, 28)
    keys = response_keys or {"trop_tot": pygame.K_LEFT, "trop_tard": pygame.K_RIGHT}
    key_map = {v: k for k, v in keys.items()}

    secondary = SecondaryResult()
    sec_t0: float | None = None
    if trial.secondary_option == 1:
        sec_t0 = None  # set when entering occultation

    t0 = time.perf_counter()
    response = None
    rt_ms = None
    max_s = time_to_reappear + (0.05 if auto else 4.0)

    while response is None and (time.perf_counter() - t0) < max_s:
        t = time.perf_counter() - t0
        in_occ = time_to_occ <= t < time_to_reappear

        if trial.secondary_option == 1 and in_occ:
            if sec_t0 is None:
                sec_t0 = time.perf_counter()
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN and event.key != pygame.K_ESCAPE:
                    if not secondary.responded:
                        secondary = SecondaryResult(
                            responded=True,
                            rt_ms=(time.perf_counter() - sec_t0) * 1000.0,
                            correct=True,
                            detail={"task": "green_circle", "during": "occultation"},
                        )
                if event.type == pygame.QUIT:
                    response = "abort"
        else:
            got = _poll_judgment_keys(
                pygame, key_map, auto=False, modality="time", delta=occ_time
            )
            if got == "abort":
                response = "abort"
            elif got is not None and t >= time_to_reappear:
                response = got
                rt_ms = (t - time_to_reappear) * 1000.0

        if auto and t >= time_to_reappear:
            response = _poll_judgment_keys(
                pygame, key_map, auto=True, modality="time", delta=occ_time
            )
            rt_ms = 12.0
            if trial.secondary_option == 1 and not secondary.responded:
                secondary = run_secondary_mock(1)

        if t < time_to_occ:
            ball_x = start_x + p_speed * t
        elif t < time_to_reappear:
            ball_x = occ_x + (occ_w / occ_time) * (t - time_to_occ) if occ_time > 0 else occ_x
        else:
            ball_x = reappear_x + p_speed * (t - time_to_reappear)

        screen.fill(bg)
        behind = (ball_x - ball_size) < reappear_x and (ball_x + ball_size) > occ_x
        if behind:
            pygame.draw.circle(screen, ball_c, (int(ball_x), ball_y), ball_size)
            pygame.draw.rect(screen, occ_c, occ_rect)
        else:
            pygame.draw.rect(screen, occ_c, occ_rect)
            pygame.draw.circle(screen, ball_c, (int(ball_x), ball_y), ball_size)
        if in_occ and trial.secondary_option == 1:
            pygame.draw.circle(screen, (0, 220, 0), (occ_x + occ_w // 2, ball_y), 28)
            screen.blit(font.render("Cercle vert — appuyez !", True, (0, 100, 0)), (40, 40))
        if t >= time_to_reappear:
            screen.blit(font.render("← trop tôt | trop tard →", True, (0, 0, 0)), (40, 40))
        pygame.display.flip()
        clock.tick(60)

    if response is None:
        response = "timeout"
        rt_ms = None
    return TrialOutcome(
        response=response,
        rt_ms=round(rt_ms, 1) if rt_ms is not None else -1.0,
        stim_params={
            "ball_speed": p_speed,
            "occulter_width_px": occ_w,
            "delta_time_s": occ_time,
            "mode": "pygame",
            "auto_input": auto,
        },
        secondary=secondary if trial.secondary_option == 1 else SecondaryResult(),
    )


def run_chrono_pygame(
    trial: TrialSpec,
    *,
    screen,
    clock,
    initial_value: float = 1000.0,
    increment_per_s: float = 10.0,
    pre_mask_s: float = 1.0,
    auto: bool | None = None,
) -> TrialOutcome:
    """Essai Chrono interactif ; option 1 pendant masquage."""
    import pygame

    auto = auto_input_enabled() if auto is None else auto
    # shorten phases in auto/CI
    if auto:
        pre_mask_s = min(pre_mask_s, 0.05)
        mask_s = min(float(trial.mask_duration_s), 0.05)
    else:
        mask_s = float(trial.mask_duration_s)

    font = pygame.font.SysFont(None, 72)
    small = pygame.font.SysFont(None, 28)
    w, h = screen.get_size()
    v0 = float(initial_value)
    v = float(increment_per_s)
    secondary = SecondaryResult()

    t0 = time.perf_counter()
    while time.perf_counter() - t0 < pre_mask_s:
        t = time.perf_counter() - t0
        val = int(round(v0 + v * t))
        screen.fill((15, 15, 20))
        txt = font.render(str(val), True, (230, 230, 230))
        screen.blit(txt, txt.get_rect(center=(w // 2, h // 2)))
        pygame.display.flip()
        clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return TrialOutcome("abort", -1.0, {}, secondary)

    # masquage (+ option 1)
    if trial.secondary_option == 1 and not auto:
        secondary = run_green_circle_during(screen, clock, duration_s=mask_s)
    else:
        mask_end = time.perf_counter() + mask_s
        sec_t0 = time.perf_counter()
        while time.perf_counter() < mask_end:
            screen.fill((15, 15, 20))
            if trial.secondary_option == 1:
                pygame.draw.circle(screen, (0, 220, 0), (w // 2, h // 2), 40)
                screen.blit(small.render("Cercle vert — appuyez", True, (180, 255, 180)), (40, 40))
            else:
                screen.blit(small.render("…", True, (120, 120, 120)), (w // 2 - 10, h // 2))
            pygame.display.flip()
            clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return TrialOutcome("abort", -1.0, {}, secondary)
                if trial.secondary_option == 1 and event.type == pygame.KEYDOWN:
                    if not secondary.responded:
                        secondary = SecondaryResult(
                            responded=True,
                            rt_ms=(time.perf_counter() - sec_t0) * 1000.0,
                            correct=True,
                            detail={"task": "green_circle"},
                        )
        if auto and trial.secondary_option == 1:
            secondary = run_secondary_mock(1)

    value = int(round(v0 + v * trial.delta_time_s))
    key_map = {pygame.K_LEFT: "trop_faible", pygame.K_RIGHT: "trop_fort"}
    resp = None
    t_resp0 = time.perf_counter()
    deadline = 0.05 if auto else 4.0
    while resp is None and (time.perf_counter() - t_resp0) < deadline:
        if auto:
            resp = _poll_judgment_keys(
                pygame, key_map, auto=True, modality="chrono", delta=trial.delta_time_s
            )
            break
        got = _poll_judgment_keys(
            pygame, key_map, auto=False, modality="chrono", delta=trial.delta_time_s
        )
        if got:
            resp = got
        screen.fill((15, 15, 20))
        txt = font.render(str(value), True, (230, 230, 230))
        screen.blit(txt, txt.get_rect(center=(w // 2, h // 2)))
        screen.blit(small.render("← trop faible | trop fort →", True, (200, 200, 200)), (40, 40))
        pygame.display.flip()
        clock.tick(60)
    rt = 12.0 if auto else ((time.perf_counter() - t_resp0) * 1000.0 if resp else None)
    return TrialOutcome(
        response=resp or "timeout",
        rt_ms=round(rt, 1) if rt is not None else -1.0,
        stim_params={
            "initial_value": v0,
            "increment_per_s": v,
            "value_at_reappear": value,
            "delta_time_s": trial.delta_time_s,
            "mode": "pygame",
            "auto_input": auto,
        },
        secondary=secondary,
    )


def run_tone_pygame(
    trial: TrialSpec,
    *,
    screen,
    clock,
    f0_hz: float = TONE_F0_HZ,
    rise_semitones_per_s: float = TONE_RISE_SEMITONES_PER_S,
    pre_mask_s: float = 1.0,
    mock_audio: bool = False,
    auto: bool | None = None,
    secondary: SecondaryResult | None = None,
) -> TrialOutcome:
    """Tone + écran de jugement (← trop grave | trop aigu →)."""
    import pygame

    auto = auto_input_enabled() if auto is None else auto
    small = pygame.font.SysFont(None, 32)
    w, h = screen.get_size()

    def wait_response() -> tuple[str, float]:
        key_map = {pygame.K_LEFT: "trop_grave", pygame.K_RIGHT: "trop_aigu"}
        if auto:
            side = expected_side("tone", trial.delta_time_s)
            if side == "exact":
                side = "trop_grave"
            return side, 12.0
        t0 = time.perf_counter()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "abort", -1.0
                if event.type == pygame.KEYDOWN and event.key in key_map:
                    return key_map[event.key], (time.perf_counter() - t0) * 1000.0
            screen.fill((10, 10, 18))
            screen.blit(small.render("← trop grave | trop aigu →", True, (220, 220, 220)), (40, h // 2))
            pygame.display.flip()
            clock.tick(60)

    # feedback pendant lecture
    screen.fill((10, 10, 18))
    screen.blit(small.render("Écoute…", True, (180, 180, 200)), (40, 40))
    pygame.display.flip()

    return run_tone_trial(
        trial,
        f0_hz=f0_hz,
        rise_semitones_per_s=rise_semitones_per_s,
        pre_mask_s=min(pre_mask_s, 0.1) if auto or mock_audio else pre_mask_s,
        mock_audio=mock_audio,
        wait_response=wait_response,
        secondary=secondary,
    )


# re-export helpers used by runner for option 2
__all__ = [
    "TrialOutcome",
    "auto_input_enabled",
    "simulate_time_trial",
    "simulate_chrono_trial",
    "simulate_tone_trial",
    "run_tone_trial",
    "run_time_pygame",
    "run_chrono_pygame",
    "run_tone_pygame",
    "synthesize_rising_tone",
    "synthesize_pure_tone",
    "play_samples_or_mock",
    "run_change_detection_pre",
    "run_change_detection_post",
]
