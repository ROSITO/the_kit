"""Stimuli Time / Chrono / Tone — mock + rendu optionnel."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any, Callable

from the_kit.manips.extrapolation.constants import (
    NOMINAL_MASK_S,
    TONE_F0_HZ,
    TONE_RISE_SEMITONES_PER_S,
)
from the_kit.manips.extrapolation.planning import Modality, TrialSpec, expected_side


@dataclass
class TrialOutcome:
    response: str
    rt_ms: float
    stim_params: dict[str, Any]


def _auto_response(modality: Modality, delta_time_s: float, *, rng_offset: float = 0.0) -> TrialOutcome:
    side = expected_side(modality, delta_time_s)
    if side == "exact":
        side = {
            "time": "trop_tot",
            "chrono": "trop_faible",
            "tone": "trop_grave",
        }[modality]
    # RT simulé court pour tests
    rt = 250.0 + (abs(delta_time_s - NOMINAL_MASK_S) * 80.0) + rng_offset
    return TrialOutcome(response=side, rt_ms=round(rt, 1), stim_params={})


def simulate_time_trial(trial: TrialSpec, *, pre_mask_s: float = 0.4) -> TrialOutcome:
    """Time: masquage = DeltaTime (réapparition réelle)."""
    speed = 100.0
    occ_w = speed * trial.delta_time_s
    params = {
        "ball_speed": speed,
        "occulter_width_px": occ_w,
        "pre_mask_s": pre_mask_s,
        "reappear_after_s": trial.delta_time_s,
    }
    # mock: pas d'attente réelle (tests rapides)
    out = _auto_response("time", trial.delta_time_s)
    out.stim_params = params
    return out


def simulate_chrono_trial(
    trial: TrialSpec,
    *,
    initial_value: float = 1000.0,
    increment_per_s: float = 10.0,
    pre_mask_s: float = 1.0,
) -> TrialOutcome:
    """Chrono: masquage fixe ; valeur = V0 + v * DeltaTime."""
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
    }
    out = _auto_response("chrono", trial.delta_time_s)
    out.stim_params = params
    return out


def _tone_hz(f0: float, rise_st_s: float, t_s: float) -> float:
    # f = f0 * 2^(v * t / 12)
    return f0 * (2.0 ** (rise_st_s * t_s / 12.0))


def synthesize_rising_tone(
    *,
    duration_s: float,
    f0_hz: float = TONE_F0_HZ,
    rise_semitones_per_s: float = TONE_RISE_SEMITONES_PER_S,
    sample_rate: int = 44100,
    amplitude: float = 0.2,
) -> tuple[list[float], int]:
    """Génère un ton montant (liste float mono) sans numpy."""
    n = max(1, int(duration_s * sample_rate))
    samples: list[float] = []
    phase = 0.0
    dt = 1.0 / sample_rate
    for i in range(n):
        t = i * dt
        freq = _tone_hz(f0_hz, rise_semitones_per_s, t)
        phase += 2.0 * math.pi * freq * dt
        samples.append(amplitude * math.sin(phase))
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

        sd.play(samples, sample_rate, blocking=True)
        meta["played"] = True
        meta["backend"] = "sounddevice"
    except Exception as exc:
        meta["backend"] = f"mock_fallback:{type(exc).__name__}"
    return meta


def simulate_tone_trial(
    trial: TrialSpec,
    *,
    f0_hz: float = TONE_F0_HZ,
    rise_semitones_per_s: float = TONE_RISE_SEMITONES_PER_S,
    pre_mask_s: float = 1.0,
    mock_audio: bool = True,
) -> TrialOutcome:
    """Tone: silence 1.5 s ; reprise à hauteur équivalente DeltaTime."""
    f_pre = _tone_hz(f0_hz, rise_semitones_per_s, pre_mask_s)
    f_reappear = _tone_hz(f0_hz, rise_semitones_per_s, trial.delta_time_s)
    f_nominal = _tone_hz(f0_hz, rise_semitones_per_s, NOMINAL_MASK_S)
    # synthèse courte pour tests (pre + probe)
    samples_pre, sr = synthesize_rising_tone(
        duration_s=min(pre_mask_s, 0.15) if mock_audio else pre_mask_s,
        f0_hz=f0_hz,
        rise_semitones_per_s=rise_semitones_per_s,
    )
    audio_meta = play_samples_or_mock(samples_pre, sr, mock=mock_audio)
    # probe à f_reappear (ton fixe court)
    probe, sr2 = synthesize_rising_tone(
        duration_s=0.1,
        f0_hz=f_reappear,
        rise_semitones_per_s=0.0,
    )
    probe_meta = play_samples_or_mock(probe, sr2, mock=mock_audio)
    params = {
        "f0_hz": f0_hz,
        "rise_semitones_per_s": rise_semitones_per_s,
        "pre_mask_s": pre_mask_s,
        "mask_duration_s": trial.mask_duration_s,
        "f_pre_hz": f_pre,
        "f_reappear_hz": f_reappear,
        "f_nominal_1_5_hz": f_nominal,
        "audio_pre": audio_meta,
        "audio_probe": probe_meta,
    }
    out = _auto_response("tone", trial.delta_time_s)
    out.stim_params = params
    return out


def run_time_pygame(trial: TrialSpec, *, screen, clock, response_keys: dict[str, int] | None = None) -> TrialOutcome:
    """Essai Time interactif (pygame)."""
    import pygame

    p_speed = 120.0
    w, h = screen.get_size()
    occ_time = float(trial.delta_time_s)
    occ_w = max(40, int(p_speed * occ_time))
    ball_size = 20
    bg = (240, 240, 240)
    ball_c = (0, 0, 220)
    occ_c = (180, 180, 180)
    ball_y = h // 2
    occ_x = w // 2 - occ_w // 2
    occ_rect = pygame.Rect(occ_x, ball_y - 28, occ_w, 56)
    reappear_x = occ_x + occ_w
    time_approach = 0.6
    start_x = occ_x - p_speed * time_approach
    time_to_occ = time_approach
    time_to_reappear = time_to_occ + occ_time
    font = pygame.font.SysFont(None, 28)
    keys = response_keys or {"trop_tot": pygame.K_LEFT, "trop_tard": pygame.K_RIGHT}

    t0 = time.perf_counter()
    response = None
    rt_ms = None
    max_s = time_to_reappear + 4.0
    while response is None and (time.perf_counter() - t0) < max_s:
        t = time.perf_counter() - t0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                response = "abort"
                break
            if event.type == pygame.KEYDOWN and t >= time_to_reappear:
                if event.key == keys["trop_tot"]:
                    response = "trop_tot"
                    rt_ms = (t - time_to_reappear) * 1000.0
                elif event.key == keys["trop_tard"]:
                    response = "trop_tard"
                    rt_ms = (t - time_to_reappear) * 1000.0
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
        stim_params={"ball_speed": p_speed, "occulter_width_px": occ_w, "delta_time_s": occ_time},
    )


def run_chrono_pygame(
    trial: TrialSpec,
    *,
    screen,
    clock,
    initial_value: float = 1000.0,
    increment_per_s: float = 10.0,
    pre_mask_s: float = 1.0,
) -> TrialOutcome:
    """Essai Chrono interactif (affichage compteur)."""
    import pygame

    font = pygame.font.SysFont(None, 72)
    small = pygame.font.SysFont(None, 28)
    w, h = screen.get_size()
    v0 = float(initial_value)
    v = float(increment_per_s)
    t0 = time.perf_counter()
    # phase visible
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
                return TrialOutcome("abort", -1.0, {})
    # masquage
    mask_end = time.perf_counter() + trial.mask_duration_s
    while time.perf_counter() < mask_end:
        screen.fill((15, 15, 20))
        screen.blit(small.render("…", True, (120, 120, 120)), (w // 2 - 10, h // 2))
        pygame.display.flip()
        clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return TrialOutcome("abort", -1.0, {})
    value = int(round(v0 + v * trial.delta_time_s))
    # jugement
    resp = None
    t_resp0 = time.perf_counter()
    while resp is None and (time.perf_counter() - t_resp0) < 4.0:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    resp = "trop_faible"
                elif event.key == pygame.K_RIGHT:
                    resp = "trop_fort"
        screen.fill((15, 15, 20))
        txt = font.render(str(value), True, (230, 230, 230))
        screen.blit(txt, txt.get_rect(center=(w // 2, h // 2)))
        screen.blit(small.render("← trop faible | trop fort →", True, (200, 200, 200)), (40, 40))
        pygame.display.flip()
        clock.tick(60)
    rt = (time.perf_counter() - t_resp0) * 1000.0 if resp else None
    return TrialOutcome(
        response=resp or "timeout",
        rt_ms=round(rt, 1) if rt is not None else -1.0,
        stim_params={
            "initial_value": v0,
            "increment_per_s": v,
            "value_at_reappear": value,
            "delta_time_s": trial.delta_time_s,
        },
    )


def run_tone_interactive(
    trial: TrialSpec,
    *,
    f0_hz: float = TONE_F0_HZ,
    rise_semitones_per_s: float = TONE_RISE_SEMITONES_PER_S,
    pre_mask_s: float = 1.0,
    mock_audio: bool = False,
    wait_keys: Callable[[], str | None] | None = None,
) -> TrialOutcome:
    """Tone: joue audio puis attend jugement (callback clavier ou auto)."""
    base = simulate_tone_trial(
        trial,
        f0_hz=f0_hz,
        rise_semitones_per_s=rise_semitones_per_s,
        pre_mask_s=pre_mask_s,
        mock_audio=mock_audio,
    )
    if wait_keys is None:
        return base
    t0 = time.perf_counter()
    resp = wait_keys()
    if resp:
        base.response = resp
        base.rt_ms = round((time.perf_counter() - t0) * 1000.0, 1)
    return base
