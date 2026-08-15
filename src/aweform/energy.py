"""Pure bounded energy accounting for simulated viability."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EnergyConfig:
    """Engineering parameters for one energy transition."""

    maximum_energy: float
    basal_cost: float
    failure_boundary: float = 0.0

    def __post_init__(self) -> None:
        _require_finite("maximum_energy", self.maximum_energy)
        _require_finite("basal_cost", self.basal_cost)
        _require_finite("failure_boundary", self.failure_boundary)
        if self.maximum_energy <= self.failure_boundary:
            raise ValueError("maximum_energy must exceed failure_boundary")
        if self.basal_cost < 0:
            raise ValueError("basal_cost must be non-negative")


@dataclass(frozen=True, slots=True)
class EnergyState:
    """Energy after a transition and whether it remains viable."""

    energy: float
    viable: bool


def advance_energy(
    current_energy: float,
    harvested_energy: float,
    config: EnergyConfig,
    action_cost: float = 0.0,
) -> EnergyState:
    """Apply harvest and costs, then return bounded energy and viability."""
    _require_finite("current_energy", current_energy)
    _require_finite("harvested_energy", harvested_energy)
    _require_finite("action_cost", action_cost)
    if not config.failure_boundary <= current_energy <= config.maximum_energy:
        raise ValueError("current_energy must be within the configured bounds")
    if harvested_energy < 0:
        raise ValueError("harvested_energy must be non-negative")
    if action_cost < 0:
        raise ValueError("action_cost must be non-negative")

    unbounded_energy = (
        current_energy + harvested_energy - config.basal_cost - action_cost
    )
    next_energy = min(
        config.maximum_energy,
        max(config.failure_boundary, unbounded_energy),
    )
    return EnergyState(
        energy=next_energy,
        viable=next_energy > config.failure_boundary,
    )


def _require_finite(name: str, value: float) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
