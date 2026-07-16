"""python_task — calibration EyeLink (dummy ou tracker réel)."""


def prepare(ctx):
    ctx.variables["eyelink_ready"] = False


def run(ctx):
    from the_kit.io import eyelink

    cfg = ctx.node.params.get("eyelink", ctx.node.params)
    dummy = bool(cfg.get("dummy_mode", True))
    code = str(cfg.get("participant_code", ctx.subject_id))
    w = int(cfg.get("screen_width", 1920))
    h = int(cfg.get("screen_height", 1080))
    if not eyelink.is_available():
        ctx.log.event("eyelink_skip", reason="pylink missing")
        return None
    tracker = eyelink.connect(dummy=dummy, participant_code=code)
    eyelink.calibrate_hv5(tracker, w, h)
    eyelink.send_message(tracker, f"the_kit block {cfg.get('block_index', 0)}")
    ctx.variables["eyelink_ready"] = True
    ctx.log.event("eyelink_calibrated", dummy=dummy, participant=code)
    if cfg.get("shutdown_after", True):
        eyelink.shutdown(tracker)
    return None
