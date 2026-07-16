"""Exemple python_task — prepare / run."""


def prepare(ctx):
    ctx.variables["trial_label"] = "demo_phase1"


def run(ctx):
    ctx.variables["greeting"] = f"hello_{ctx.subject_id}"
    ctx.log.event("python_hello", message=ctx.variables["greeting"])
    return None
