from the_kit.pygame_handlers.shadow_ball_scene import (
    BASELINE,
    SHADOW_CONGRUENT,
    ShadowBallScene,
    TRIAL_MOTION,
)


def test_shadow_scene_builds_corridor():
    scene = ShadowBallScene(1280, 720, {"shadow_mode": "congruent"})
    assert scene.floor_surf.get_width() == 1280
    assert scene.ceiling_surf.get_height() == 720
    assert scene.ball_amplitude > 0


def test_shadow_scene_baseline_then_condition():
    scene = ShadowBallScene(
        1280,
        720,
        {
            "shadow_mode": "congruent",
            "fixation_duration_s": 0.0,
            "run_baseline_pair": True,
            "center_crossings": 1,
        },
    )
    scene.begin()
    assert scene.shadow_mode == BASELINE
    scene.trial_phase = TRIAL_MOTION
    scene.phase_time = 0.0
    scene.shadow_ellipse_period_s = 0.05
    for _ in range(500):
        state = scene.update(0.02)
        if state.done:
            break
    assert scene.condition_mode == SHADOW_CONGRUENT
