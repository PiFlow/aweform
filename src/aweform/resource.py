"""A bounded, static, smooth two-dimensional resource field."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

import numpy as np

Coordinate = tuple[float, float]


@dataclass(frozen=True, slots=True)
class ResourceField:
    """Static Gaussian-like resource sources over a bounded 2D world."""

    world_min: Coordinate = (0.0, 0.0)
    world_max: Coordinate = (1.0, 1.0)
    source_positions: tuple[Coordinate, ...] = ((0.5, 0.5),)
    peak_intensity: float = 1.0
    length_scale: float = 0.25

    def __post_init__(self) -> None:
        _validate_bounds(self.world_min, self.world_max)
        try:
            source_positions = tuple(self.source_positions)
        except TypeError as error:
            raise ValueError(
                "source_positions must contain at least one position"
            ) from error
        if not source_positions:
            raise ValueError("source_positions must contain at least one position")
        normalized_positions: list[Coordinate] = []
        for source_position in source_positions:
            _validate_position(source_position, self.world_min, self.world_max)
            normalized_positions.append(
                (float(source_position[0]), float(source_position[1]))
            )
        object.__setattr__(self, "source_positions", tuple(normalized_positions))
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
        resource_count: int = 1,
        peak_intensity: float = 1.0,
        length_scale: float = 0.25,
    ) -> ResourceField:
        """Place static sources deterministically using an explicit generator."""
        _validate_bounds(world_min, world_max)
        _validate_resource_count(resource_count)
        source_positions = tuple(
            _sample_position(rng, world_min=world_min, world_max=world_max)
            for _ in range(resource_count)
        )
        return cls(
            world_min=world_min,
            world_max=world_max,
            source_positions=source_positions,
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

        intensity = max(
            self._intensity_from_source(point, source_position)
            for source_position in self.source_positions
        )
        return max(0.0, min(self.peak_intensity, intensity))

    def _intensity_from_source(
        self,
        point: Coordinate,
        source_position: Coordinate,
    ) -> float:
        dx = point[0] - source_position[0]
        dy = point[1] - source_position[1]
        distance_squared = dx * dx + dy * dy
        return self.peak_intensity * math.exp(
            -0.5 * distance_squared / (self.length_scale * self.length_scale)
        )


def _sample_position(
    rng: np.random.Generator,
    *,
    world_min: Coordinate,
    world_max: Coordinate,
) -> Coordinate:
    source = rng.uniform(
        low=np.asarray(world_min, dtype=float),
        high=np.asarray(world_max, dtype=float),
    )
    return (float(source[0]), float(source[1]))


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
    try:
        valid = len(coordinate) == 2 and all(
            math.isfinite(float(value)) for value in coordinate
        )
    except (TypeError, ValueError):
        valid = False
    if not valid:
        raise ValueError(f"{name} must contain two finite coordinates")


def _require_finite(name: str, value: float) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


def _validate_resource_count(resource_count: int) -> None:
    if (
        isinstance(resource_count, bool)
        or not isinstance(resource_count, int)
        or resource_count <= 0
    ):
        raise ValueError("resource_count must be a positive integer")
