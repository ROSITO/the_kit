"""SpatioTemporelle (Time) — bloc labo."""

from the_kit.manips.extrapolation import run_lab_block
from the_kit.task_api import NodeResult


def prepare(ctx):
    args = ctx.node.params.get("script", {}).get("args", {})
    ctx.variables["modality"] = "time"
    ctx.variables["secondary_option"] = int(args.get("secondary_option", 0))


def run(ctx) -> NodeResult:
    return run_lab_block(ctx, modality="time")
