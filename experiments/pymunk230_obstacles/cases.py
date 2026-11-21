"""Frozen one-shot fixed-command physics corpus; importing performs no steps."""

from __future__ import annotations

import math
from dataclasses import dataclass

MAX_DELTA = 0.6457718232379019
FORWARD = (MAX_DELTA, MAX_DELTA)
REVERSE = (-MAX_DELTA, -MAX_DELTA)
SPIN_CW = (MAX_DELTA, -MAX_DELTA)
SPIN_CCW = (-MAX_DELTA, MAX_DELTA)


@dataclass(frozen=True)
class PhysicsCase:
    case_id: str
    start: tuple[float, float, float]
    commands: tuple[tuple[float, float], ...]
    expect_contact: bool
    expected_objects: tuple[str, ...] = ()
    reset_count: int = 0
    identity_pair: str | None = None


def _repeat(
    command: tuple[float, float], count: int
) -> tuple[tuple[float, float], ...]:
    return (command,) * count


def frozen_cases() -> tuple[PhysicsCase, ...]:
    """Return fixed poses, action streams, and expected event classes."""
    cases = [
        PhysicsCase("empty-free", (1.0, 1.0, 0.0), _repeat(FORWARD, 1), False),
        PhysicsCase(
            "reset-repeat-wall-release",
            (0.11, 1.5, math.pi),
            _repeat(FORWARD, 5) + _repeat(REVERSE, 5),
            True,
            ("wall_west",),
            reset_count=2,
            identity_pair="reset-wall",
        ),
        PhysicsCase(
            "constructed-wall-release-control",
            (0.11, 1.5, math.pi),
            _repeat(FORWARD, 5) + _repeat(REVERSE, 5),
            True,
            ("wall_west",),
            identity_pair="reset-wall",
        ),
        PhysicsCase(
            "west-wall-head-release",
            (0.11, 1.5, math.pi),
            _repeat(FORWARD, 5) + _repeat(REVERSE, 5),
            True,
            ("wall_west",),
        ),
        PhysicsCase(
            "east-wall-head-release",
            (2.89, 1.5, 0.0),
            _repeat(FORWARD, 5) + _repeat(REVERSE, 5),
            True,
            ("wall_east",),
        ),
        PhysicsCase(
            "south-wall-head-release",
            (1.5, 0.11, -math.pi / 2),
            _repeat(FORWARD, 5) + _repeat(REVERSE, 5),
            True,
            ("wall_south",),
        ),
        PhysicsCase(
            "north-wall-head-release",
            (1.5, 2.89, math.pi / 2),
            _repeat(FORWARD, 5) + _repeat(REVERSE, 5),
            True,
            ("wall_north",),
        ),
        # Concave and convex arc faces, plus both rounded physical end caps.
        PhysicsCase(
            "A1-concave-face",
            (1.5, 2.25, math.pi / 2),
            _repeat(FORWARD, 8),
            True,
            ("A1",),
        ),
        PhysicsCase(
            "A1-convex-face",
            (1.5, 2.52, -math.pi / 2),
            _repeat(FORWARD, 8),
            True,
            ("A1",),
        ),
        PhysicsCase(
            "A1-start-cap",
            (1.965, 2.2325, math.radians(210)),
            _repeat(FORWARD, 8),
            True,
            ("A1",),
        ),
        PhysicsCase(
            "A1-end-cap",
            (1.035, 2.2325, math.radians(330)),
            _repeat(FORWARD, 8),
            True,
            ("A1",),
        ),
        PhysicsCase(
            "A2-concave-face", (2.55, 1.5, math.pi), _repeat(FORWARD, 8), True, ("A2",)
        ),
        PhysicsCase(
            "A2-convex-face", (2.18, 1.5, 0.0), _repeat(FORWARD, 4), True, ("A2",)
        ),
        PhysicsCase(
            "A2-start-cap",
            (2.290380592228744, 1.959619407771256, math.radians(315)),
            _repeat(FORWARD, 8),
            True,
            ("A2",),
        ),
        PhysicsCase(
            "A2-end-cap",
            (2.290380592228744, 1.040380592228744, math.radians(45)),
            _repeat(FORWARD, 8),
            True,
            ("A2",),
        ),
        PhysicsCase(
            "A3-concave-face",
            (0.5414213562373095, 2.4585786437626905, math.radians(315)),
            _repeat(FORWARD, 8),
            True,
            ("A3",),
        ),
        PhysicsCase(
            "A3-convex-face",
            (0.768, 2.232, math.radians(135)),
            _repeat(FORWARD, 3),
            True,
            ("A3",),
        ),
        PhysicsCase(
            "A3-start-cap",
            (0.40, 2.065, math.radians(90)),
            _repeat(FORWARD, 8),
            True,
            ("A3",),
        ),
        PhysicsCase(
            "A3-end-cap", (0.935, 2.60, math.pi), _repeat(FORWARD, 8), True, ("A3",)
        ),
        # S1/S2 faces and rounded ends, in both approach orientations.
        PhysicsCase(
            "S1-south-face",
            (1.5, 0.40, math.pi / 2),
            _repeat(FORWARD, 8),
            True,
            ("S1",),
        ),
        PhysicsCase(
            "S1-north-face",
            (1.5, 0.70, -math.pi / 2),
            _repeat(FORWARD, 8),
            True,
            ("S1",),
        ),
        PhysicsCase(
            "S1-west-cap", (1.05, 0.66, 0.0), _repeat(FORWARD, 4), True, ("S1",)
        ),
        PhysicsCase(
            "S1-east-cap", (1.95, 0.66, math.pi), _repeat(FORWARD, 4), True, ("S1",)
        ),
        PhysicsCase(
            "S2-west-face", (0.40, 1.425, 0.0), _repeat(FORWARD, 8), True, ("S2",)
        ),
        PhysicsCase(
            "S2-east-face", (0.70, 1.425, math.pi), _repeat(FORWARD, 8), True, ("S2",)
        ),
        PhysicsCase(
            "S2-south-cap",
            (0.66, 0.975, math.pi / 2),
            _repeat(FORWARD, 4),
            True,
            ("S2",),
        ),
        PhysicsCase(
            "S2-north-cap",
            (0.66, 1.875, -math.pi / 2),
            _repeat(FORWARD, 4),
            True,
            ("S2",),
        ),
        PhysicsCase(
            "P1-west-face", (2.19, 0.60, 0.0), _repeat(FORWARD, 8), True, ("P1",)
        ),
        PhysicsCase(
            "P1-east-face", (2.51, 0.60, math.pi), _repeat(FORWARD, 8), True, ("P1",)
        ),
        PhysicsCase(
            "P2-west-face", (2.29, 2.45, 0.0), _repeat(FORWARD, 8), True, ("P2",)
        ),
        PhysicsCase(
            "P2-east-face", (2.61, 2.45, math.pi), _repeat(FORWARD, 8), True, ("P2",)
        ),
        # Oblique motion, sustained pushing, reverse release, and contact spin.
        PhysicsCase(
            "A1-oblique-slide",
            (1.5, 2.24, math.radians(70)),
            _repeat(FORWARD, 8),
            True,
            ("A1",),
        ),
        PhysicsCase(
            "S1-oblique-slide",
            (1.30, 0.39, math.radians(20)),
            _repeat(FORWARD, 12),
            True,
            ("S1",),
        ),
        PhysicsCase(
            "P1-sustained-push-release",
            (2.19, 0.60, 0.0),
            _repeat(FORWARD, 20) + _repeat(REVERSE, 9),
            True,
            ("P1",),
        ),
        PhysicsCase(
            "S2-spin-contact",
            (0.67, 1.42, 0.0),
            _repeat(SPIN_CW, 8) + _repeat(SPIN_CCW, 8),
            True,
            ("S2",),
        ),
        PhysicsCase(
            "A1-pocket-two-corner",
            (1.5, 2.24, 0.0),
            _repeat(FORWARD, 12),
            True,
            ("A1",),
        ),
        # Close but clear geometric controls near a wall and an arc pocket.
        PhysicsCase(
            "wall-near-clear", (0.20, 0.50, math.pi), _repeat((0.0, 0.0), 1), False
        ),
        PhysicsCase(
            "A1-pocket-near-clear", (1.5, 2.17, 0.0), _repeat((0.0, 0.0), 1), False
        ),
    ]
    return tuple(cases)


PRIMARY_CASES = frozen_cases()
OBSTACLE_LOGICAL_COMMANDS = sum(len(case.commands) for case in PRIMARY_CASES)
EMPTY_FREE_COMMANDS = _repeat(FORWARD, 1)
EMPTY_WALL_COMMANDS = _repeat(FORWARD, 5) + _repeat(REVERSE, 5)
EMPTY_CONTROL_LOGICAL_COMMANDS = len(EMPTY_FREE_COMMANDS) + len(EMPTY_WALL_COMMANDS)
PRIMARY_LOGICAL_COMMANDS = OBSTACLE_LOGICAL_COMMANDS + EMPTY_CONTROL_LOGICAL_COMMANDS
PRIMARY_ENGINE_STEPS = PRIMARY_LOGICAL_COMMANDS * (400 + 800)
TOTAL_ENGINE_STEPS_WITH_REPLAY = PRIMARY_ENGINE_STEPS * 2
