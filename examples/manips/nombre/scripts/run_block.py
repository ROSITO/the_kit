"""Chrono (Nombre) — bloc labo."""

from the_kit.manips.extrapolation import run_lab_block
from the_kit.task_api import NodeResult


def prepare(ctx):
    ctx.variables["modality"] = "chrono"


def run(ctx) -> NodeResult:
    return run_lab_block(ctx, modality="chrono")
