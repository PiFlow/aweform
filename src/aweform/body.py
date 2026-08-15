"""Minimal bounded body state and movement for the V0.1 environment."""

from __future__ import annotations

import math
from dataclasses import dataclass

Coordinate = tuple[float, float]


@dataclass(slots=True)
class Body:
    """Simulator-side body state.

    Position, heading, and energy are simulator state. Only the explicitly
    defined observation assembled by :class:`AweformEnv` crosses the agent
    boundary.
    """

    x: float
    y: float
    heading: float
    energy: float

    def __post_init__(self) -> None:
        _require_finite("x", self.x)
        _require_finite("y", self.y)
        _require_finite("heading", self.heading)
        _require_finite("energy", self.energy)
        self.heading %= math.tau

    @property
    def position(self) -> Coordinate:
        """Return the body's simulator-side position."""
        return (self.x, self.y)

    def turn(self, angle: float) -> None:
        """Turn by ``angle`` radians, wrapping heading to ``[0, 2π)``."""
        _require_finite("angle", angle)
        self.heading = (self.heading + angle) % math.tau

    def move_forward(
        self,
        distance: float,
        *,
        world_min: Coordinate,
        world_max: Coordinate,
    ) -> None:
        """Move forward and clamp the resulting position to world bounds."""
        _require_finite("distance", distance)
        if distance < 0:
            raise ValueError("distance must be non-negative")
        _validate_bounds(world_min, world_max)

        proposed_x = self.x + distance * math.cos(self.heading)
        proposed_y = self.y + distance * math.sin(self.heading)
        self.x = min(world_max[0], max(world_min[0], proposed_x))
        self.y = min(world_max[1], max(world_min[1], proposed_y))


def _validate_bounds(world_min: Coordinate, world_max: Coordinate) -> None:
    _require_coordinate("world_min", world_min)
    _require_coordinate("world_max", world_max)
    if not all(lower < upper for lower, upper in zip(world_min, world_max)):
        raise ValueError("world_min must be strictly below world_max")


def _require_coordinate(name: str, coordinate: Coordinate) -> None:
    if len(coordinate) != 2 or not all(math.isfinite(value) for value in coordinate):
        raise ValueError(f"{name} must contain two finite coordinates")


def _require_finite(name: str, value: float) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
