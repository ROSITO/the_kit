"""Corridor shadow_ball (port shadowi/main.py — perspective, damiers, ombres)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Tuple

import pygame

# Modes (shadowi)
BASELINE = 0
SHADOW_CONGRUENT = 1
SHADOW_CONGRUENT_LEVIT = 2
SHADOW_INCONGRUENT_BLACK = 3
SHADOW_INCONGRUENT_WHITE = 4

MODE_NAMES = {
    "baseline": BASELINE,
    "congruent": SHADOW_CONGRUENT,
    "congruent_levit": SHADOW_CONGRUENT_LEVIT,
    "incongruent_black": SHADOW_INCONGRUENT_BLACK,
    "incongruent_white": SHADOW_INCONGRUENT_WHITE,
}

TRIAL_FIXATION = 0
TRIAL_MOTION = 1

BG_COLOR = (0, 0, 0)
CHECKER_COLOR_A = (154, 154, 154)
CHECKER_COLOR_B = (100, 100, 100)
BACK_WALL_COLOR = (70, 70, 70)
BALL_COLOR = (240, 0, 0)
BALL_SHADE_COLOR = (100, 0, 0)
FIXATION_COLOR = (255, 255, 255)

ROOM_DEPTH_INIT = 2.2
CHECKER_LAST_ROW_RATIO = 0.695
CHECKER_ROWS_FLOOR = 7
CHECKER_COLS = 8
CHECKER_ROWS_CEIL = 7
_SHADOW_SCALE_Y = 0.35
_SHADOW_UNDER_BALL_RATIO = 0.55
_SHADOW_MAX_ALPHA = 130
_ANTI_SHADOW_MAX_ALPHA = 130
_ANTI_SHADOW_COLOR = (255, 255, 255)
_BALL_RADIUS_RATIO = 0.0625
_SHADOW_SOFTNESS_RATIO = 0.023
_SHADOW_ELLIPSE_FLOOR_RATIO = 0.60
_FIXATION_CROSS_HALF_RATIO = 0.012

AR_CROSSINGS = 2


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def quad_at(
    surf: pygame.Surface,
    color: Tuple[int, int, int],
    pts: List[Tuple[float, float]],
) -> None:
    pygame.draw.polygon(surf, color, [(int(p[0]), int(p[1])) for p in pts])


def make_soft_shadow(
    radius: float,
    *,
    max_alpha: int = 120,
    softness: int = 16,
    scale_y: float = 0.35,
    color: tuple = (0, 0, 0),
) -> pygame.Surface:
    pad = softness * 2
    w = int(radius * 2) + pad
    h = int(radius * 2 * scale_y) + pad
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    cx, cy = w // 2, h // 2
    base_w = radius * 2
    base_h = radius * 2 * scale_y
    for i in range(softness, -1, -1):
        t = i / max(1, softness)
        alpha = int(max_alpha * (1.0 - t) ** 2)
        dw, dh = i * 2, int(i * 2 * scale_y)
        rect = pygame.Rect(0, 0, base_w + dw, base_h + dh)
        rect.center = (cx, cy)
        pygame.draw.ellipse(surf, (*color, alpha), rect)
    return surf


@dataclass
class ShadowBallState:
    phase: int
    shadow_mode: int
    baseline_subphase: bool
    center_crossings: int
    done: bool
    ball_x: float
    ball_y: int


class ShadowBallScene:
    """Une présentation : corridor 3D + balle + ombre selon le mode."""

    def __init__(self, width: int, height: int, params: dict) -> None:
        self.width = width
        self.height = height
        self.room_depth = float(params.get("room_depth", ROOM_DEPTH_INIT))
        self.fixation_duration_s = float(params.get("fixation_duration_s", 3.0))
        self.ball_traverse_time_s = float(params.get("ball_traverse_time_s", 1.0))
        self.shadow_ellipse_period_s = 2.0 * self.ball_traverse_time_s
        self.center_crossings_required = int(
            params.get("center_crossings", AR_CROSSINGS)
        )
        self.run_baseline_pair = bool(params.get("run_baseline_pair", True))
        self.viewing_distance_ratio = float(params.get("viewing_distance_ratio", 0.45))
        mode_name = str(params.get("shadow_mode", "congruent"))
        self.condition_mode = MODE_NAMES.get(mode_name, SHADOW_CONGRUENT)

        checker_a = params.get("checker_color_a", CHECKER_COLOR_A)
        checker_b = params.get("checker_color_b", CHECKER_COLOR_B)
        self.checker_a = tuple(checker_a[:3])
        self.checker_b = tuple(checker_b[:3])
        self.back_wall_color = tuple(params.get("back_wall_color", BACK_WALL_COLOR)[:3])

        self.trial_phase = TRIAL_FIXATION
        self.phase_time = 0.0
        self.shadow_mode = BASELINE
        self.baseline_subphase = True
        self.center_crossings = 0
        self.previous_x = 0.0
        self.first_fixation = True
        self.done = False

        self._init_geometry()
        self._rebuild_surfaces()

    def _init_geometry(self) -> None:
        w, h = self.width, self.height
        self.vp_x = w / 2.0
        self.vp_y = h / 2.0
        self.floor_bottom_y = h - 1
        self.ceil_top_y = 0
        vd_init = int(w * self.viewing_distance_ratio)
        self._update_scene_from_depth(self.room_depth, vd_init)

        self.ball_radius = int(h * _BALL_RADIUS_RATIO)
        self.shadow_softness = int(h * _SHADOW_SOFTNESS_RATIO)
        self.fixation_cross_half = int(h * _FIXATION_CROSS_HALF_RATIO)
        sh = int(self.ball_radius * 1.05 * 2 * _SHADOW_SCALE_Y) + self.shadow_softness * 2
        self.shadow_offset_y = (
            int(self.ball_radius - sh / 2 + _SHADOW_UNDER_BALL_RATIO * sh) + 1
        )
        self.shadow_offset_y_levit = self.shadow_offset_y + int(h * 0.228)

        self._recompute_ball_track()

    def _update_scene_from_depth(self, room_depth: float, viewing_distance_px: int) -> None:
        depth_ratio = 1.0 - 1.0 / room_depth
        zoom = viewing_distance_px / max(1, int(self.width * 0.45))
        floor_extent = (self.floor_bottom_y - self.vp_y) * depth_ratio * zoom
        self.floor_top_y = int(self.floor_bottom_y - floor_extent)
        ceil_extent = self.vp_y * depth_ratio * zoom
        self.ceil_bottom_y = int(self.ceil_top_y + ceil_extent)
        self.floor_top_y = min(self.floor_top_y, self.floor_bottom_y - 2)
        self.ceil_bottom_y = max(self.ceil_bottom_y, self.ceil_top_y + 2)

    def _screen_x_left(self, y: float, is_floor: bool) -> float:
        if is_floor:
            denom = self.vp_y - self.floor_bottom_y
            if abs(denom) < 1e-6:
                return 0.0
            t = (y - self.floor_bottom_y) / denom
            return self.vp_x * t
        denom = self.vp_y - self.ceil_top_y
        if abs(denom) < 1e-6:
            return 0.0
        t = (y - self.ceil_top_y) / denom
        return self.vp_x * t

    def _screen_x_right(self, y: float, is_floor: bool) -> float:
        if is_floor:
            denom = self.vp_y - self.floor_bottom_y
            if abs(denom) < 1e-6:
                return float(self.width)
            t = (y - self.floor_bottom_y) / denom
            return self.width + (self.vp_x - self.width) * t
        denom = self.vp_y - self.ceil_top_y
        if abs(denom) < 1e-6:
            return float(self.width)
        t = (y - self.ceil_top_y) / denom
        return self.width + (self.vp_x - self.width) * t

    @staticmethod
    def _row_depths(nrows: int, last_ratio: float, front_is_row_0: bool) -> List[float]:
        if nrows <= 1:
            return [1.0] * max(1, nrows)
        if front_is_row_0:
            return [lerp(1.0, last_ratio, i / (nrows - 1)) for i in range(nrows)]
        return [lerp(last_ratio, 1.0, i / (nrows - 1)) for i in range(nrows)]

    def _ball_params_last_floor_row(self) -> Tuple[int, int, int]:
        nrows = CHECKER_ROWS_FLOOR
        depths = self._row_depths(nrows, CHECKER_LAST_ROW_RATIO, front_is_row_0=False)
        total = sum(depths)
        v_front_last = depths[0] / total
        y_floor = self.floor_top_y + (self.floor_bottom_y - self.floor_top_y) * v_front_last
        ball_y = int(y_floor + self.ball_radius * (-0.5))
        x_left = self._screen_x_left(y_floor, True)
        x_right = self._screen_x_right(y_floor, True)
        ball_x_min = int(x_left + self.ball_radius * 2)
        ball_x_max = int(x_right - self.ball_radius * 2)
        return ball_y, ball_x_min, ball_x_max

    def _shadow_ellipse_params(self, _ball_y: int) -> Tuple[float, float, float, float]:
        x_lt = self._screen_x_left(float(self.floor_top_y), True)
        x_rt = self._screen_x_right(float(self.floor_top_y), True)
        x_lb = self._screen_x_left(float(self.floor_bottom_y), True)
        x_rb = self._screen_x_right(float(self.floor_bottom_y), True)
        cx = ((x_lt + x_rt) / 2 + (x_lb + x_rb) / 2) / 2
        cy = (self.floor_top_y + self.floor_bottom_y) / 2
        floor_depth = self.floor_bottom_y - self.floor_top_y
        floor_width_avg = ((x_rt - x_lt) + (x_rb - x_lb)) / 2
        a = _SHADOW_ELLIPSE_FLOOR_RATIO * (floor_width_avg / 2)
        b = _SHADOW_ELLIPSE_FLOOR_RATIO * (floor_depth / 2)
        return cx, cy, a, b

    def _recompute_ball_track(self) -> None:
        self.ball_y, self.ball_x_min, self.ball_x_max = self._ball_params_last_floor_row()
        self.ball_center = (self.ball_x_min + self.ball_x_max) / 2.0
        self.ball_amplitude = (self.ball_x_max - self.ball_x_min) / 2.0
        self.cx_ellipse, self.cy_ellipse, self.a_ellipse, self.b_ellipse = (
            self._shadow_ellipse_params(self.ball_y)
        )
        self.previous_x = self.ball_center

    def _build_floor_surface(self) -> pygame.Surface:
        surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        h0, h1 = self.floor_top_y, self.floor_bottom_y
        if h1 <= h0:
            return surf
        nrows, ncols = CHECKER_ROWS_FLOOR, CHECKER_COLS
        depths = self._row_depths(nrows, CHECKER_LAST_ROW_RATIO, front_is_row_0=False)
        total = sum(depths)
        cumul = [0.0] + [sum(depths[: i + 1]) / total for i in range(nrows)]
        for row in range(nrows):
            for col in range(ncols):
                v0, v1 = cumul[row], cumul[row + 1]
                u0, u1 = col / ncols, (col + 1) / ncols
                y0, y1 = lerp(h0, h1, v0), lerp(h0, h1, v1)
                x00 = lerp(self._screen_x_left(y0, True), self._screen_x_right(y0, True), u0)
                x01 = lerp(self._screen_x_left(y0, True), self._screen_x_right(y0, True), u1)
                x10 = lerp(self._screen_x_left(y1, True), self._screen_x_right(y1, True), u0)
                x11 = lerp(self._screen_x_left(y1, True), self._screen_x_right(y1, True), u1)
                color = self.checker_a if (row + col) % 2 == 0 else self.checker_b
                quad_at(surf, color, [(x00, y0), (x01, y0), (x11, y1), (x10, y1)])
        return surf

    def _build_ceiling_surface(self) -> pygame.Surface:
        surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        h0, h1 = self.ceil_top_y, self.ceil_bottom_y
        if h1 <= h0:
            return surf
        nrows, ncols = CHECKER_ROWS_CEIL, CHECKER_COLS
        depths = self._row_depths(nrows, CHECKER_LAST_ROW_RATIO, front_is_row_0=True)
        total = sum(depths)
        cumul = [0.0] + [sum(depths[: i + 1]) / total for i in range(nrows)]
        for row in range(nrows):
            for col in range(ncols):
                v0, v1 = cumul[row], cumul[row + 1]
                u0, u1 = col / ncols, (col + 1) / ncols
                y0, y1 = lerp(h0, h1, v0), lerp(h0, h1, v1)
                x00 = lerp(self._screen_x_left(y0, False), self._screen_x_right(y0, False), u0)
                x01 = lerp(self._screen_x_left(y0, False), self._screen_x_right(y0, False), u1)
                x10 = lerp(self._screen_x_left(y1, False), self._screen_x_right(y1, False), u0)
                x11 = lerp(self._screen_x_left(y1, False), self._screen_x_right(y1, False), u1)
                color = self.checker_b if (row + col) % 2 == 0 else self.checker_a
                quad_at(surf, color, [(x00, y0), (x01, y0), (x11, y1), (x10, y1)])
        return surf

    def _rebuild_surfaces(self) -> None:
        self.floor_surf = self._build_floor_surface()
        self.ceiling_surf = self._build_ceiling_surface()
        self.shadow_surf = make_soft_shadow(
            float(self.ball_radius) * 1.05,
            max_alpha=_SHADOW_MAX_ALPHA,
            softness=self.shadow_softness,
            scale_y=_SHADOW_SCALE_Y,
            color=(0, 0, 0),
        )
        self.anti_shadow_surf = make_soft_shadow(
            float(self.ball_radius) * 1.05,
            max_alpha=_ANTI_SHADOW_MAX_ALPHA,
            softness=self.shadow_softness,
            scale_y=_SHADOW_SCALE_Y,
            color=_ANTI_SHADOW_COLOR,
        )
        self.shadow_w, self.shadow_h = self.shadow_surf.get_size()
        self._recompute_ball_track()

    def _lerp_color(self, c1, c2, t):
        return (
            int(c1[0] + (c2[0] - c1[0]) * t),
            int(c1[1] + (c2[1] - c1[1]) * t),
            int(c1[2] + (c2[2] - c1[2]) * t),
        )

    def _draw_ball(self, screen: pygame.Surface, x: float, y: float, show_fixation: bool) -> None:
        r = self.ball_radius
        ix, iy, ri = int(x), int(y), int(r)
        for dy in range(-ri, ri + 1):
            hw_sq = r * r - dy * dy
            if hw_sq <= 0:
                continue
            hw = int(hw_sq**0.5)
            t = max(0.0, min(1.0, (dy + r) / (2.0 * r)))
            color = self._lerp_color(BALL_COLOR, BALL_SHADE_COLOR, t)
            pygame.draw.line(screen, color, (ix - hw, iy + dy), (ix + hw, iy + dy), 1)
        if show_fixation:
            h = self.fixation_cross_half
            pygame.draw.line(screen, FIXATION_COLOR, (ix - h, iy), (ix + h, iy), 3)
            pygame.draw.line(screen, FIXATION_COLOR, (ix, iy - h), (ix, iy + h), 3)

    def _ball_and_shadow_xy(self) -> Tuple[float, float, float, float]:
        if self.trial_phase == TRIAL_FIXATION:
            cycle_u = 0.0
        else:
            cycle_u = (
                4.0
                * (self.phase_time % self.shadow_ellipse_period_s)
                / self.shadow_ellipse_period_s
            )
        phase = (math.pi / 2.0) * cycle_u
        x = self.ball_center + self.ball_amplitude * math.sin(phase)
        sx, sy = x, self.ball_y

        if self.shadow_mode == SHADOW_CONGRUENT:
            sx, sy = x, self.ball_y + self.shadow_offset_y
        elif self.shadow_mode == SHADOW_CONGRUENT_LEVIT:
            sx, sy = x, self.cy_ellipse + self.b_ellipse
        elif self.shadow_mode in (SHADOW_INCONGRUENT_BLACK, SHADOW_INCONGRUENT_WHITE):
            cx_b = self.ball_center
            a_b = self.ball_amplitude
            if a_b <= 0:
                sx, sy = x, self.cy_ellipse
            else:
                arg = max(0.0, min(1.0, 1.0 - ((x - cx_b) ** 2) / (a_b * a_b)))
                rad = self.b_ellipse * math.sqrt(arg)
                u = cycle_u % 4.0
                use_bottom = (u < 1.0) or (u >= 3.0)
                sy = self.cy_ellipse + rad if use_bottom else self.cy_ellipse - rad
                sx = x
        return x, self.ball_y, sx, sy

    def begin(self) -> None:
        if self.condition_mode == BASELINE:
            self.shadow_mode = BASELINE
            self.run_baseline_pair = False
        elif self.run_baseline_pair:
            self.shadow_mode = BASELINE
            self.baseline_subphase = True
        else:
            self.shadow_mode = self.condition_mode
            self.baseline_subphase = False

    def update(self, dt: float) -> ShadowBallState:
        if self.done:
            return self._state()

        x, ball_y, _, _ = self._ball_and_shadow_xy()

        if self.trial_phase == TRIAL_FIXATION:
            fix_dur = self.fixation_duration_s if self.first_fixation else 0.0
            if self.phase_time >= fix_dur:
                self.trial_phase = TRIAL_MOTION
                self.phase_time = 0.0
                self.center_crossings = 0
                self.previous_x = self.ball_center
                self.first_fixation = False
        elif self.trial_phase == TRIAL_MOTION:
            if (self.previous_x < self.ball_center and x >= self.ball_center) or (
                self.previous_x > self.ball_center and x <= self.ball_center
            ):
                self.center_crossings += 1
            self.previous_x = x
            required = self.center_crossings_required
            if self.center_crossings >= required:
                self._advance_after_crossings()

        self.phase_time += dt
        return self._state(ball_x=x, ball_y=ball_y)

    def _advance_after_crossings(self) -> None:
        if self.run_baseline_pair and self.baseline_subphase:
            self.baseline_subphase = False
            self.shadow_mode = self.condition_mode
            self.trial_phase = TRIAL_FIXATION
            self.phase_time = 0.0
            self.center_crossings = 0
            self.previous_x = self.ball_center
            return
        self.done = True

    def _state(self, *, ball_x: float = 0.0, ball_y: int = 0) -> ShadowBallState:
        return ShadowBallState(
            phase=self.trial_phase,
            shadow_mode=self.shadow_mode,
            baseline_subphase=self.baseline_subphase,
            center_crossings=self.center_crossings,
            done=self.done,
            ball_x=ball_x,
            ball_y=ball_y,
        )

    def draw_corridor(self, screen: pygame.Surface) -> None:
        """Mur + damiers sol/plafond (sans balle ni ombre)."""
        screen.fill(BG_COLOR)
        x_left_ceil = self._screen_x_left(float(self.ceil_bottom_y), False)
        x_right_ceil = self._screen_x_right(float(self.ceil_bottom_y), False)
        x_left_floor = self._screen_x_left(float(self.floor_top_y), True)
        x_right_floor = self._screen_x_right(float(self.floor_top_y), True)
        quad_at(
            screen,
            self.back_wall_color,
            [
                (x_left_ceil, self.ceil_bottom_y),
                (x_right_ceil, self.ceil_bottom_y),
                (x_right_floor, self.floor_top_y),
                (x_left_floor, self.floor_top_y),
            ],
        )
        screen.blit(self.ceiling_surf, (0, 0))
        screen.blit(self.floor_surf, (0, 0))

    def draw_ball_and_shadow(self, screen: pygame.Surface) -> None:
        x, ball_y, sx, sy = self._ball_and_shadow_xy()
        if self.shadow_mode != BASELINE:
            surf = (
                self.anti_shadow_surf
                if self.shadow_mode == SHADOW_INCONGRUENT_WHITE
                else self.shadow_surf
            )
            screen.blit(surf, (int(sx - self.shadow_w / 2), int(sy - self.shadow_h / 2)))

        show_fix = self.trial_phase == TRIAL_FIXATION
        self._draw_ball(screen, x, ball_y, show_fixation=show_fix)

    def draw(self, screen: pygame.Surface) -> None:
        self.draw_corridor(screen)
        self.draw_ball_and_shadow(screen)
