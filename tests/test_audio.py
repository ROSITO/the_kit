from the_kit.audio.low_latency import plan_av_onsets


def test_plan_av_onsets_ordering():
    now, trial, audio = plan_av_onsets(offset_ms=-10, scheduling_lead_s=0.3, clock=lambda: 1000.0)
    assert now == 1000.0
    assert trial == 1000.3
    assert audio == 1000.29
