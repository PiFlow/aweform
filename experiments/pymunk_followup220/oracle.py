"""Independent constant-curvature and body-frame metamorphic calculations."""

from __future__ import annotations

import math

Coordinate = tuple[float, float]


def sinc(value: float) -> float:
    """Return sin(x)/x with its continuous value at zero."""
    if value == 0.0:
        return 1.0
    return math.sin(value) / value


def differential_drive_arc(
    position_m: Coordinate,
    heading_rad: float,
    actual_left_rad: float,
    actual_right_rad: float,
    *,
    wheel_radius_m: float = 0.045,
    track_width_m: float = 0.185,
) -> tuple[Coordinate, float]:
    """Integrate signed wheel path lengths as an independent SE(2) arc."""
    left_distance = wheel_radius_m * actual_left_rad
    right_distance = wheel_radius_m * actual_right_rad
    center_distance = (left_distance + right_distance) / 2.0
    yaw_delta = (right_distance - left_distance) / track_width_m

    half_yaw = yaw_delta / 2.0
    local_forward = center_distance * sinc(half_yaw) * math.cos(half_yaw)
    local_lateral = center_distance * sinc(half_yaw) * math.sin(half_yaw)
    dx = local_forward * math.cos(heading_rad) - local_lateral * math.sin(heading_rad)
    dy = local_forward * math.sin(heading_rad) + local_lateral * math.cos(heading_rad)
    return (position_m[0] + dx, position_m[1] + dy), heading_rad + yaw_delta


def body_frame_displacement(
    start_heading_rad: float, displacement_m: Coordinate
) -> Coordinate:
    """Rotate a world displacement into its fixed initial body frame."""
    cosine = math.cos(start_heading_rad)
    sine = math.sin(start_heading_rad)
    return (
        displacement_m[0] * cosine + displacement_m[1] * sine,
        -displacement_m[0] * sine + displacement_m[1] * cosine,
    )


def rotate_displacement(angle_rad: float, displacement_m: Coordinate) -> Coordinate:
    """Rotate a world vector counter-clockwise by ``angle_rad``."""
    cosine = math.cos(angle_rad)
    sine = math.sin(angle_rad)
    return (
        displacement_m[0] * cosine - displacement_m[1] * sine,
        displacement_m[0] * sine + displacement_m[1] * cosine,
    )
