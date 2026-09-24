"""SpatioTemporelle (Time) — chirurgie éveillée."""

from the_kit.manips.extrapolation import run_chirurgie_block
from the_kit.task_api import NodeResult


def prepare(ctx):
    ctx.variables["modality"] = "time"


def run(ctx) -> NodeResult:
    return run_chirurgie_block(ctx, modality="time")
