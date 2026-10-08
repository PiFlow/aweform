"""First-principles differential-drive oracle, independent of Pymunk updates."""

from __future__ import annotations

import math

Coordinate = tuple[float, float]


def differential_drive_arc(
    position: Coordinate,
    heading: float,
    delta_left: float,
    delta_right: float,
    *,
    wheel_radius_m: float = 0.045,
    track_width_m: float = 0.185,
) -> tuple[Coordinate, float]:
    """Return the exact constant-curvature pose from wheel path lengths."""
    left_distance = wheel_radius_m * delta_left
    right_distance = wheel_radius_m * delta_right
    center_distance = (left_distance + right_distance) / 2.0
    yaw_delta = (right_distance - left_distance) / track_width_m
    if abs(yaw_delta) < 1e-15:
        dx = center_distance * math.cos(heading)
        dy = center_distance * math.sin(heading)
    else:
        radius = center_distance / yaw_delta
        next_heading = heading + yaw_delta
        dx = radius * (math.sin(next_heading) - math.sin(heading))
        dy = -radius * (math.cos(next_heading) - math.cos(heading))
    return (position[0] + dx, position[1] + dy), heading + yaw_delta
