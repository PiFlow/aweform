"""Seed reservations and execution guards for EXP-002 planning."""

from __future__ import annotations

from collections.abc import Sequence
from numbers import Integral

from .exp001_seed_policy import CONFIRMATORY_SEEDS as EXP001_CONFIRMATORY_SEEDS
from .exp001_seed_policy import FORMAL_CALIBRATION_SEEDS as EXP001_CALIBRATION_SEEDS
from .exp002_protocol import EXP002_CALIBRATION_SEEDS, EXP002_CONFIRMATORY_SEEDS


def validate_exp002_development_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    """Reject all formal EXP-001/EXP-002 reservations before execution."""
    if isinstance(seeds, (str, bytes)):
        raise ValueError("seeds must be a non-empty sequence of integers")
    try:
        supplied = tuple(seeds)
    except TypeError as error:
        raise ValueError("seeds must be a non-empty sequence of integers") from error
    if not supplied:
        raise ValueError("seeds must not be empty")

    validated: list[int] = []
    exp001_calibration = set(EXP001_CALIBRATION_SEEDS)
    exp001_confirmatory = set(EXP001_CONFIRMATORY_SEEDS)
    exp002_calibration = set(EXP002_CALIBRATION_SEEDS)
    exp002_confirmatory = set(EXP002_CONFIRMATORY_SEEDS)
    for seed in supplied:
        if isinstance(seed, bool) or not isinstance(seed, Integral) or seed < 0:
            raise ValueError("seeds must contain only non-negative integers")
        value = int(seed)
        if value in exp001_calibration or value in exp001_confirmatory:
            raise ValueError(
                "EXP-002 development cannot reuse an EXP-001 reserved seed"
            )
        if value in exp002_calibration:
            raise ValueError("seed is reserved for EXP-002 calibration")
        if value in exp002_confirmatory:
            raise ValueError("seed is reserved for EXP-002 confirmation")
        validated.append(value)
    return tuple(validated)
