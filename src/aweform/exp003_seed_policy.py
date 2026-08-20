"""EXP-003 development-seed guard and future reservations."""

from __future__ import annotations

from collections.abc import Sequence
from numbers import Integral

from .exp001_seed_policy import (
    CONFIRMATORY_SEEDS as EXP001_CONFIRMATORY_SEEDS,
)
from .exp001_seed_policy import (
    FORMAL_CALIBRATION_SEEDS as EXP001_CALIBRATION_SEEDS,
)
from .exp002_protocol import EXP002_CALIBRATION_SEEDS, EXP002_CONFIRMATORY_SEEDS

EXP003_CALIBRATION_SEEDS = tuple(range(60001, 60201))
EXP003_CONFIRMATORY_SEEDS = tuple(range(70001, 71001))


def validate_exp003_development_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    """Reject every existing or newly reserved formal seed range."""
    if isinstance(seeds, (str, bytes)):
        raise ValueError("seeds must be a non-empty sequence of integers")
    try:
        supplied = tuple(seeds)
    except TypeError as error:
        raise ValueError("seeds must be a non-empty sequence of integers") from error
    if not supplied:
        raise ValueError("seeds must not be empty")

    reserved = frozenset(
        (
            *EXP001_CALIBRATION_SEEDS,
            *EXP001_CONFIRMATORY_SEEDS,
            *EXP002_CALIBRATION_SEEDS,
            *EXP002_CONFIRMATORY_SEEDS,
            *EXP003_CALIBRATION_SEEDS,
            *EXP003_CONFIRMATORY_SEEDS,
        )
    )
    validated: list[int] = []
    for seed in supplied:
        if isinstance(seed, bool) or not isinstance(seed, Integral) or seed < 0:
            raise ValueError("seeds must contain only non-negative integers")
        value = int(seed)
        if value in reserved:
            raise ValueError(f"seed {value} is reserved for a formal experiment")
        validated.append(value)
    return tuple(validated)
