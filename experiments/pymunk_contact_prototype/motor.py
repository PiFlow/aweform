"""Persistent ideal differential-drive force law for successor adapters."""

from __future__ import annotations

import math
from typing import Protocol


class _Body(Protocol):
    angle: float
    mass: float
    velocity: tuple[float, float]
    angular_velocity: float
    force: tuple[float, float]


def begin_wheel_command(
    body: _Body, linear_speed_m_s: float, yaw_rate_rad_s: float, heading_rad: float
) -> None:
    """Set the requested differential-drive twist once at a logical boundary."""
    body.velocity = (
        linear_speed_m_s * math.cos(heading_rad),
        linear_speed_m_s * math.sin(heading_rad),
    )
    body.angular_velocity = yaw_rate_rad_s


def apply_persistent_curvature_force(body: _Body, yaw_rate_rad_s: float) -> None:
    """Apply the centripetal force for held wheel curvature, without resetting v.

    For a constant differential-drive twist, acceleration is ``omega * J(v)``.
    Applying ``m * omega * J(v)`` as an ordinary body force lets Pymunk's
    integrator and contact solver evolve velocity. The command's wheel-derived
    yaw rate is fixed at the logical boundary; this force law uses the current
    solver-evolved velocity and never observes contact flags or reassigns it.
    It introduces no new fitted gain, geometry, or solver parameter.
    """
    vx, vy = body.velocity
    body.force = (
        -body.mass * yaw_rate_rad_s * vy,
        body.mass * yaw_rate_rad_s * vx,
    )
