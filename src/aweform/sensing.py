"""Local directional resource sensing."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .body import Body, Coordinate
from .resource import ResourceField


@dataclass(frozen=True, slots=True)
class DirectionalSignals:
    """Resource intensities sampled to the body's left, front, and right."""

    left: float
    forward: float
    right: float

    def as_tuple(self) -> tuple[float, float, float]:
        """Return signals in observation order."""
        return (self.left, self.forward, self.right)


def sample_directional_resources(
    body: Body,
    field: ResourceField,
    *,
    probe_distance: float,
    sensor_angle: float,
) -> DirectionalSignals:
    """Sample three nearby points relative to the body's heading.

    A probe outside the world returns zero. No coordinate or source metadata is
    returned by this function.
    """
    _require_finite("probe_distance", probe_distance)
    _require_finite("sensor_angle", sensor_angle)
    if probe_distance < 0:
        raise ValueError("probe_distance must be non-negative")

    left = _sample(
        body,
        field,
        body.heading + sensor_angle,
        probe_distance,
    )
    forward = _sample(body, field, body.heading, probe_distance)
    right = _sample(
        body,
        field,
        body.heading - sensor_angle,
        probe_distance,
    )
    return DirectionalSignals(left=left, forward=forward, right=right)


def _sample(
    body: Body,
    field: ResourceField,
    direction: float,
    distance: float,
) -> float:
    point = (
        body.x + distance * math.cos(direction),
        body.y + distance * math.sin(direction),
    )
    if not _within_bounds(point, field.world_min, field.world_max):
        return 0.0
    return field.intensity(point)


def _within_bounds(
    point: Coordinate,
    world_min: Coordinate,
    world_max: Coordinate,
) -> bool:
    return all(
        lower <= value <= upper
        for value, lower, upper in zip(point, world_min, world_max)
    )


def _require_finite(name: str, value: float) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
