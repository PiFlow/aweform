"""Engine-advanced fixtures for the frozen issue #220 candidate matrix."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, cast

import pymunk

MAX_WHEEL_DELTA_RAD = 0.6457718232379019
WHEEL_RADIUS_M = 0.045
TRACK_WIDTH_M = 0.185
BODY_LENGTH_M = 0.180
BODY_WIDTH_M = 0.215
DT_SECONDS = 0.1
ENCODER_QUANTUM_RAD = math.pi / 180.0
FIXTURE_MASS_KG = 1.0
FIXTURE_MOMENT_KG_M2 = FIXTURE_MASS_KG * (BODY_LENGTH_M**2 + BODY_WIDTH_M**2) / 12.0

CandidateId = Literal["C1_MIDPOINT_NOMINAL_SPEED", "C2_MIDPOINT_ARC_AVERAGE"]
CANDIDATES: tuple[CandidateId, ...] = (
    "C1_MIDPOINT_NOMINAL_SPEED",
    "C2_MIDPOINT_ARC_AVERAGE",
)


@dataclass(frozen=True)
class Endpoint:
    position_m: tuple[float, float]
    heading_rad: float
    velocity_m_s: tuple[float, float]
    angular_velocity_rad_s: float
    actual_shaft_deltas_rad: tuple[float, float]
    engine_step_count: int


def parse_wheel_action(action: Sequence[object]) -> tuple[float, float]:
    """Parse exactly two finite numeric signed wheel-delta requests."""
    if isinstance(action, (str, bytes)) or len(action) != 2:
        raise ValueError("action must contain exactly two finite wheel deltas")

    parsed_values: list[float] = []
    for value in action:
        if isinstance(value, (bool, str, bytes)):
            raise ValueError(
                "wheel deltas must be numeric values, not text or booleans"
            )
        try:
            parsed = float(cast(float, value))
        except TypeError, ValueError, OverflowError:
            raise ValueError(
                "action must contain exactly two finite wheel deltas"
            ) from None
        if not math.isfinite(parsed):
            raise ValueError("action must contain exactly two finite wheel deltas")
        parsed_values.append(parsed)
    return parsed_values[0], parsed_values[1]


def clip_wheel_action(
    action: Sequence[object],
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Return finite requests and independently clipped ideal shaft deltas."""
    requested = parse_wheel_action(action)
    limit = MAX_WHEEL_DELTA_RAD
    actual = (
        min(limit, max(-limit, requested[0])),
        min(limit, max(-limit, requested[1])),
    )
    return requested, actual


def quantize_encoder(delta_rad: float) -> float:
    """Quantize to one-degree counts, with exact ties away from zero."""
    if not math.isfinite(delta_rad):
        raise ValueError("encoder input must be finite")
    counts = math.floor(abs(delta_rad) / ENCODER_QUANTUM_RAD + 0.5)
    return math.copysign(counts * ENCODER_QUANTUM_RAD, delta_rad) if counts else 0.0


def sinc(value: float) -> float:
    """Return sin(x)/x with its continuous value at zero."""
    if value == 0.0:
        return 1.0
    return math.sin(value) / value


class PymunkFollowupProbe:
    """Fresh empty-space dynamic body advanced only by ``Space.step``."""

    def __init__(
        self,
        candidate: CandidateId,
        *,
        microsteps: int = 10,
        heading_rad: float = 0.0,
    ) -> None:
        if candidate not in CANDIDATES:
            raise ValueError(f"unknown candidate: {candidate}")
        if microsteps not in (10, 20):
            raise ValueError("microsteps must be 10 or 20")
        if not math.isfinite(heading_rad):
            raise ValueError("initial heading must be finite")

        self.candidate = candidate
        self.microsteps = microsteps
        self.space = pymunk.Space(threaded=False)
        self.space.gravity = (0.0, 0.0)
        self.space.damping = 1.0
        self.space.iterations = 10
        self.space.collision_slop = 0.0001
        self.space.collision_bias = 0.001797010299914434
        self.space.collision_persistence = 3
        self.space.sleep_time_threshold = math.inf
        self.space.idle_speed_threshold = 0.0

        self.body = pymunk.Body(FIXTURE_MASS_KG, FIXTURE_MOMENT_KG_M2)
        self.body.position = (0.0, 0.0)
        self.body.angle = heading_rad
        self.body.velocity = (0.0, 0.0)
        self.body.angular_velocity = 0.0
        self.space.add(self.body)
        self.elapsed_seconds = 0.0
        self.engine_step_count = 0

    def advance(self, action: Sequence[object]) -> Endpoint:
        """Apply one clipped command and let Pymunk advance every microstep."""
        _, actual = clip_wheel_action(action)
        left_distance = WHEEL_RADIUS_M * actual[0]
        right_distance = WHEEL_RADIUS_M * actual[1]
        center_distance = (left_distance + right_distance) / 2.0
        yaw_delta = (right_distance - left_distance) / TRACK_WIDTH_M
        forward_speed = center_distance / DT_SECONDS
        yaw_rate = yaw_delta / DT_SECONDS
        step_seconds = DT_SECONDS / self.microsteps

        for _ in range(self.microsteps):
            angle = float(self.body.angle)
            half_step_yaw = yaw_rate * step_seconds / 2.0
            midpoint_heading = angle + half_step_yaw
            speed_scale = (
                1.0
                if self.candidate == "C1_MIDPOINT_NOMINAL_SPEED"
                else sinc(half_step_yaw)
            )
            midpoint_speed = forward_speed * speed_scale
            self.body.velocity = (
                midpoint_speed * math.cos(midpoint_heading),
                midpoint_speed * math.sin(midpoint_heading),
            )
            self.body.angular_velocity = yaw_rate
            self.space.step(step_seconds)
            self.engine_step_count += 1

        self.elapsed_seconds += DT_SECONDS
        return Endpoint(
            position_m=(float(self.body.position.x), float(self.body.position.y)),
            heading_rad=float(self.body.angle),
            velocity_m_s=(float(self.body.velocity.x), float(self.body.velocity.y)),
            angular_velocity_rad_s=float(self.body.angular_velocity),
            actual_shaft_deltas_rad=actual,
            engine_step_count=self.engine_step_count,
        )
