"""Isolated direct-Pymunk fixture for the frozen Tranche 1 protocol."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

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


@dataclass(frozen=True)
class Endpoint:
    position: tuple[float, float]
    heading: float
    velocity: tuple[float, float]
    angular_velocity: float
    shaft_deltas: tuple[float, float]


class PymunkProbe:
    """A fresh empty-space dynamic body advanced by ideal commanded twist."""

    def __init__(self, *, microsteps: int = 10) -> None:
        if microsteps not in (10, 20):
            raise ValueError("microsteps must be 10 or 20")
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
        self.body.angle = 0.0
        self.body.velocity = (0.0, 0.0)
        self.body.angular_velocity = 0.0
        self.space.add(self.body)
        self.elapsed_seconds = 0.0

    def advance(
        self, command: Sequence[float], *, heading: float | None = None
    ) -> Endpoint:
        """Advance once; optional heading is only allowed before first action."""
        left, right = parse_command(command)
        if heading is not None:
            if self.elapsed_seconds != 0.0:
                raise ValueError("initial heading can only be set before advancement")
            if not math.isfinite(heading):
                raise ValueError("heading must be finite")
            self.body.angle = heading
        actual = (
            min(MAX_WHEEL_DELTA_RAD, max(-MAX_WHEEL_DELTA_RAD, left)),
            min(MAX_WHEEL_DELTA_RAD, max(-MAX_WHEEL_DELTA_RAD, right)),
        )
        left_distance = WHEEL_RADIUS_M * actual[0]
        right_distance = WHEEL_RADIUS_M * actual[1]
        forward_speed = (left_distance + right_distance) / (2.0 * DT_SECONDS)
        yaw_rate = (right_distance - left_distance) / (TRACK_WIDTH_M * DT_SECONDS)
        step_seconds = DT_SECONDS / self.microsteps
        for _ in range(self.microsteps):
            angle = self.body.angle
            self.body.velocity = (
                forward_speed * math.cos(angle),
                forward_speed * math.sin(angle),
            )
            self.body.angular_velocity = yaw_rate
            self.space.step(step_seconds)
        self.elapsed_seconds += DT_SECONDS
        return Endpoint(
            position=(float(self.body.position.x), float(self.body.position.y)),
            heading=float(self.body.angle),
            velocity=(float(self.body.velocity.x), float(self.body.velocity.y)),
            angular_velocity=float(self.body.angular_velocity),
            shaft_deltas=actual,
        )


def parse_command(command: Sequence[float]) -> tuple[float, float]:
    """Match D-045's exactly-two-finite-values action contract."""
    if isinstance(command, (str, bytes)) or len(command) != 2:
        raise ValueError("action must contain exactly two finite wheel deltas")
    values: list[float] = []
    for value in command:
        if isinstance(value, bool):
            raise ValueError("action must contain exactly two finite wheel deltas")
        try:
            parsed = float(value)
        except TypeError, ValueError, OverflowError:
            raise ValueError(
                "action must contain exactly two finite wheel deltas"
            ) from None
        if not math.isfinite(parsed):
            raise ValueError("action must contain exactly two finite wheel deltas")
        values.append(parsed)
    return values[0], values[1]


def quantize_encoder(delta: float) -> float:
    """One-degree nearest-count quantizer, with ties away from zero."""
    if not math.isfinite(delta):
        raise ValueError("delta must be finite")
    counts = math.floor(abs(delta) / ENCODER_QUANTUM_RAD + 0.5)
    return math.copysign(counts * ENCODER_QUANTUM_RAD, delta) if counts else 0.0
