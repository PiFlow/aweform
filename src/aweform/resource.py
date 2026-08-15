"""A bounded, static, smooth two-dimensional resource field."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

import numpy as np

Coordinate = tuple[float, float]


@dataclass(frozen=True, slots=True)
class ResourceField:
    """One Gaussian-like resource source over a bounded 2D world."""

    world_min: Coordinate = (0.0, 0.0)
    world_max: Coordinate = (1.0, 1.0)
    source_position: Coordinate = (0.5, 0.5)
    peak_intensity: float = 1.0
    length_scale: float = 0.25

    def __post_init__(self) -> None:
        _validate_bounds(self.world_min, self.world_max)
        _validate_position(self.source_position, self.world_min, self.world_max)
        _require_finite("peak_intensity", self.peak_intensity)
        _require_finite("length_scale", self.length_scale)
        if self.peak_intensity < 0:
            raise ValueError("peak_intensity must be non-negative")
        if self.length_scale <= 0:
            raise ValueError("length_scale must be positive")

    @classmethod
    def from_rng(
        cls,
        rng: np.random.Generator,
        *,
        world_min: Coordinate = (0.0, 0.0),
        world_max: Coordinate = (1.0, 1.0),
        peak_intensity: float = 1.0,
        length_scale: float = 0.25,
    ) -> ResourceField:
        """Place the one source deterministically using an explicit generator."""
        _validate_bounds(world_min, world_max)
        source = rng.uniform(
            low=np.asarray(world_min, dtype=float),
            high=np.asarray(world_max, dtype=float),
        )
        source_position = (float(source[0]), float(source[1]))
        return cls(
            world_min=world_min,
            world_max=world_max,
            source_position=source_position,
            peak_intensity=peak_intensity,
            length_scale=length_scale,
        )

    def intensity(self, position: Sequence[float]) -> float:
        """Return harvestable resource intensity at a valid world position."""
        coordinates = np.asarray(position, dtype=float)
        if coordinates.shape != (2,):
            raise ValueError("position must contain exactly two coordinates")
        point = (float(coordinates[0]), float(coordinates[1]))
        _validate_position(point, self.world_min, self.world_max)

        dx = point[0] - self.source_position[0]
        dy = point[1] - self.source_position[1]
        distance_squared = dx * dx + dy * dy
        return self.peak_intensity * math.exp(
            -0.5 * distance_squared / (self.length_scale * self.length_scale)
        )


def _validate_bounds(world_min: Coordinate, world_max: Coordinate) -> None:
    _validate_coordinate("world_min", world_min)
    _validate_coordinate("world_max", world_max)
    if not all(lower < upper for lower, upper in zip(world_min, world_max)):
        raise ValueError("world_min must be strictly below world_max")


def _validate_position(
    position: Coordinate,
    world_min: Coordinate,
    world_max: Coordinate,
) -> None:
    _validate_coordinate("position", position)
    if not all(
        lower <= value <= upper
        for value, lower, upper in zip(position, world_min, world_max)
    ):
        raise ValueError("position must be within the world bounds")


def _validate_coordinate(name: str, coordinate: Coordinate) -> None:
    if len(coordinate) != 2 or not all(math.isfinite(value) for value in coordinate):
        raise ValueError(f"{name} must contain two finite coordinates")


def _require_finite(name: str, value: float) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
