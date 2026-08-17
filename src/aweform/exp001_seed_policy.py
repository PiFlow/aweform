"""Canonical EXP-001 seed reservations and development validation."""

from __future__ import annotations

from collections.abc import Sequence
from numbers import Integral

FORMAL_CALIBRATION_SEEDS = tuple(range(20001, 20201))
CONFIRMATORY_SEEDS = tuple(range(30001, 31001))


def validate_exp001_development_seeds(
    seeds: Sequence[int],
) -> tuple[int, ...]:
    """Validate non-reserved development seeds before any execution starts."""
    validated = _validate_exp001_seed_sequence(seeds)
    for seed in validated:
        if seed in FORMAL_CALIBRATION_SEEDS:
            raise ValueError(
                f"seed {seed} is reserved for formal EXP-001 calibration"
            )
        if seed in CONFIRMATORY_SEEDS:
            raise ValueError(
                f"seed {seed} is reserved for untouched EXP-001 confirmation"
            )
    return validated


def _validate_exp001_seed_sequence(seeds: Sequence[int]) -> tuple[int, ...]:
    if isinstance(seeds, (str, bytes)):
        raise ValueError(
            "seeds must be a non-empty sequence of non-negative integers"
        )
    try:
        supplied = tuple(seeds)
    except TypeError as error:
        raise ValueError(
            "seeds must be a non-empty sequence of non-negative integers"
        ) from error
    if not supplied:
        raise ValueError("seeds must not be empty")
    validated: list[int] = []
    for seed in supplied:
        if isinstance(seed, bool) or not isinstance(seed, Integral) or seed < 0:
            raise ValueError("seeds must contain only non-negative integer values")
        validated.append(int(seed))
    return tuple(validated)
