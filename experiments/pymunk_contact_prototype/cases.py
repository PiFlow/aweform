"""Immutable fixed-command measurement inventory (not executed at import)."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .fixture import MAX_DELTA

A = MAX_DELTA
H = A / 2
CENTER = (1.5, 1.5)


@dataclass(frozen=True)
class Case:
    case_id: str
    family: str
    start: tuple[float, float, float]
    commands: tuple[tuple[float, float], ...]
    posts: tuple[tuple[float, float], ...] = ()
    microsteps: int = 10


def _repeat(action: tuple[float, float], count: int) -> tuple[tuple[float, float], ...]:
    return (action,) * count


def fixed_cases() -> tuple[Case, ...]:
    cases: list[Case] = []
    vectors = (
        ("zero", (0.0, 0.0)),
        ("forward", (A, A)),
        ("reverse", (-A, -A)),
        ("spin-positive", (-A, A)),
        ("spin-negative", (A, -A)),
        ("arc-negative-yaw", (A, H)),
        ("arc-positive-yaw", (H, A)),
        ("one-wheel-left", (A, 0.0)),
        ("one-wheel-right", (0.0, A)),
    )
    for heading in (0.0, math.pi / 2, -math.pi / 2, math.pi):
        for name, command in vectors:
            for amplitude in (0.25, 0.5, 1.0):
                for n in (10, 20):
                    scaled = (command[0] * amplitude, command[1] * amplitude)
                    cases.append(
                        Case(
                            f"cal-{name}-a{amplitude:.2f}-h{heading:.6f}-n{n}",
                            "calibration",
                            (*CENTER, heading),
                            _repeat(scaled, 1),
                            (),
                            n,
                        )
                    )

    wall_specs = (
        ("west", (0.5, 1.5, math.pi), (0.095, 1.5, 0.0)),
        ("east", (2.5, 1.5, 0.0), (2.905, 1.5, math.pi)),
        ("south", (1.5, 0.5, -math.pi / 2), (1.5, 0.1125, math.pi / 2)),
        ("north", (1.5, 2.5, math.pi / 2), (1.5, 2.8875, -math.pi / 2)),
    )
    for wall, head, flush in wall_specs:
        cases.append(
            Case(f"wall-{wall}-head-on", "wall-head-on", head, _repeat((A, A), 20))
        )
        cases.append(
            Case(
                f"wall-{wall}-release",
                "wall-release",
                head,
                _repeat((A, A), 20) + _repeat((-A, -A), 10),
            )
        )
        cases.append(
            Case(
                f"wall-{wall}-reverse-away", "wall-reverse", head, _repeat((-A, -A), 1)
            )
        )
        turns = ((-A, A), (A, -A), (A, H))
        for index, command in enumerate(turns):
            cases.append(
                Case(
                    f"wall-{wall}-turn-{index}",
                    "wall-turn",
                    flush,
                    _repeat(command, 10),
                )
            )

    glancing = (
        ("south", (1.0, 0.25, math.radians(-65))),
        ("east", (2.75, 1.0, math.radians(25))),
        ("north", (2.0, 2.75, math.radians(115))),
        ("west", (0.25, 2.0, math.radians(205))),
    )
    for wall, start in glancing:
        cases.append(
            Case(f"wall-{wall}-glance", "wall-glance", start, _repeat((A, A), 10))
        )

    corners = (
        ("sw", (0.25, 0.25, 5 * math.pi / 4)),
        ("nw", (0.25, 2.75, 3 * math.pi / 4)),
        ("se", (2.75, 0.25, -math.pi / 4)),
        ("ne", (2.75, 2.75, math.pi / 4)),
    )
    for name, start in corners:
        cases.append(
            Case(
                f"corner-{name}",
                "corner",
                start,
                _repeat((A, A), 10) + _repeat((A, -A), 10),
            )
        )

    center_post = ((1.5, 1.5),)
    cases.extend(
        (
            Case(
                "post-head-on",
                "post-head-on",
                (1.0, 1.5, 0.0),
                _repeat((A, A), 15),
                center_post,
            ),
            Case(
                "post-tangent",
                "post-tangent",
                (1.0, 1.65, 0.0),
                _repeat((A, A), 20),
                center_post,
            ),
            Case(
                "post-sustained",
                "post-sustained",
                (1.0, 1.5, 0.0),
                _repeat((A, A), 20),
                center_post,
            ),
            Case(
                "post-release",
                "post-release",
                (1.0, 1.5, 0.0),
                _repeat((A, A), 20) + _repeat((-A, -A), 10),
                center_post,
            ),
            Case(
                "post-turn",
                "post-turn",
                (1.25, 1.5, 0.0),
                _repeat((-A, A), 10) + _repeat((A, H), 10),
                center_post,
            ),
            Case(
                "post-near-miss",
                "post-near-miss",
                (1.0, 1.82, 0.0),
                _repeat((A, A), 5) + _repeat((0.0, H), 2) + _repeat((A, A), 5),
                center_post,
            ),
            Case(
                "post-wall-adjacent",
                "post-wall-adjacent",
                (0.55, 1.5, math.pi),
                _repeat((A, A), 20),
                ((0.15, 1.5),),
            ),
        )
    )
    return tuple(cases)
