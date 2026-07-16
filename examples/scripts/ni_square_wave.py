"""python_task — stimulation NI via ctx.ni_square_wave (Alba)."""


def run(ctx):
    return ctx.ni_square_wave(
        direction=ctx.node.params.get("direction", "AP"),
        amplitude=float(ctx.node.params.get("amplitude", 0.8)),
        frequency=float(ctx.node.params.get("frequency", 0.278)),
        duration_s=float(ctx.node.params.get("duration_s", 3.6)),
    )
