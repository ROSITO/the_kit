"""Counterbalancing — grilles Latin square (F-1105)."""

from __future__ import annotations

import hashlib
from typing import Any


def balanced_latin_square(n: int) -> list[list[int]]:
    """Grille Latin square équilibrée (n pair, design Williams)."""
    if n < 2 or n % 2 != 0:
        raise ValueError(f"latin square équilibré : n pair >= 2 requis, reçu {n}")
    rows: list[list[int]] = []
    for i in range(n):
        row: list[int] = []
        for j in range(n):
            if i % 2 == 0:
                row.append((j + i // 2) % n)
            else:
                row.append((n - 1 - j + i // 2) % n)
        rows.append(row)
    return rows


def latin_square_odd(n: int) -> list[list[int]]:
    """n impair : carré latin cyclique simple."""
    if n < 1:
        raise ValueError("n >= 1 requis")
    return [[(i + j) % n for j in range(n)] for i in range(n)]


def latin_square_grid(n: int) -> list[list[int]]:
    if n % 2 == 0:
        return balanced_latin_square(n)
    return latin_square_odd(n)


def participant_row_index(subject_id: str, n_rows: int, *, explicit: int | None = None) -> int:
    if explicit is not None:
        return int(explicit) % n_rows
    digits = "".join(c for c in subject_id if c.isdigit())
    if digits:
        return int(digits) % n_rows
    h = int(hashlib.sha256(subject_id.encode()).hexdigest()[:8], 16)
    return h % n_rows


def order_for_subject(
    n_conditions: int,
    subject_id: str,
    *,
    subject_number: int | None = None,
    grid: list[list[int]] | None = None,
) -> list[int]:
    """Ordre des indices de conditions 0..n-1 pour ce participant."""
    if n_conditions <= 1:
        return [0]
    g = grid if grid is not None else latin_square_grid(n_conditions)
    row = participant_row_index(
        subject_id, len(g), explicit=subject_number
    )
    return list(g[row])


def apply_latin_square_to_trials(
    trials: list[dict[str, Any]],
    *,
    subject_id: str,
    subject_number: int | None = None,
    grid: list[list[int]] | None = None,
) -> list[dict[str, Any]]:
    """Réordonne une liste d'essais uniques selon la ligne Latin square du sujet."""
    n = len(trials)
    if n <= 1:
        return trials
    order = order_for_subject(n, subject_id, subject_number=subject_number, grid=grid)
    by_id: dict[int, dict[str, Any]] = {}
    for i, t in enumerate(trials):
        by_id[i] = t
    return [by_id[i] for i in order]


def parse_counterbalance_config(
    cb: dict[str, Any] | str | None,
) -> dict[str, Any] | None:
    if not cb:
        return None
    if isinstance(cb, str):
        if cb.lower() in ("latin_square", "latin", "williams"):
            return {"method": "latin_square"}
        return None
    if isinstance(cb, dict) and cb.get("method", "latin_square") == "latin_square":
        return cb
    return None
