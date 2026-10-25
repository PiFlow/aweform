"""ADR-0020 seven-object layout as static Pymunk geometry only.

This module deliberately defines no collision response law, controller, or
organism-facing signal. Arc center-lines are approximated by joined Pymunk
capsule segments; internal neighbors suppress seam artifacts while the physical
arc-end caps remain rounded.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import pymunk

ROOM_SIDE_M = 3.0
WALL_THICKNESS_M = 0.01
ARC_CENTERLINE_RADIUS_M = 0.40
ARC_HALF_THICKNESS_M = 0.025
SEGMENT_HALF_THICKNESS_M = 0.025
POST_RADIUS_M = 0.05
ARC_MAX_STEP_DEG = 4.0
ARC_MAX_SAGITTA_M = ARC_CENTERLINE_RADIUS_M * (
    1.0 - math.cos(math.radians(ARC_MAX_STEP_DEG / 2.0))
)


@dataclass(frozen=True)
class ArcSpec:
    name: str
    center: tuple[float, float]
    start_deg: float
    end_deg: float


@dataclass(frozen=True)
class SegmentSpec:
    name: str
    start: tuple[float, float]
    end: tuple[float, float]


@dataclass(frozen=True)
class PostSpec:
    name: str
    center: tuple[float, float]


ARCS = (
    ArcSpec("A1", (1.50, 2.00), 30.0, 150.0),
    ArcSpec("A2", (2.75, 1.50), 135.0, 225.0),
    ArcSpec("A3", (0.40, 2.60), 270.0, 360.0),
)
SEGMENTS = (
    SegmentSpec("S1", (1.175, 0.55), (1.825, 0.55)),
    SegmentSpec("S2", (0.55, 1.10), (0.55, 1.75)),
)
POSTS = (
    PostSpec("P1", (2.35, 0.60)),
    PostSpec("P2", (2.45, 2.45)),
)


def arc_vertices(spec: ArcSpec) -> tuple[tuple[float, float], ...]:
    """Return deterministic center-line vertices with <=4° angular intervals."""
    count = math.ceil((spec.end_deg - spec.start_deg) / ARC_MAX_STEP_DEG)
    return tuple(
        (
            spec.center[0]
            + ARC_CENTERLINE_RADIUS_M
            * math.cos(math.radians(_angle_at(spec, i, count))),
            spec.center[1]
            + ARC_CENTERLINE_RADIUS_M
            * math.sin(math.radians(_angle_at(spec, i, count))),
        )
        for i in range(count + 1)
    )


def _angle_at(spec: ArcSpec, index: int, count: int) -> float:
    return spec.start_deg + (spec.end_deg - spec.start_deg) * index / count


def _arc_neighbor_points(
    points: tuple[tuple[float, float], ...], index: int
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Return joined center-line neighbors, leaving physical arc ends open."""
    if not 0 <= index < len(points) - 1:
        raise IndexError("arc segment index out of range")
    previous = points[index - 1] if index > 0 else points[index]
    following = points[index + 2] if index + 2 < len(points) else points[index + 1]
    return previous, following


def _link_arc_segments(
    points: tuple[tuple[float, float], ...], shapes: Sequence[pymunk.Segment]
) -> None:
    """Link each arc chord to its adjacent center-line vertices."""
    if len(shapes) != len(points) - 1:
        raise ValueError("arc segment count must match center-line intervals")
    for index, shape in enumerate(shapes):
        previous, following = _arc_neighbor_points(points, index)
        shape.set_neighbors(pymunk.Vec2d(*previous), pymunk.Vec2d(*following))


def add_arena(
    space: pymunk.Space, *, include_walls: bool = True
) -> dict[str, tuple[pymunk.Shape, ...]]:
    """Add room walls and the exact seven fixed objects; return named shapes.

    Arcs are a union of joined capsule segments. Their maximum center-line
    chord deviation is ARC_MAX_SAGITTA_M (<0.25 mm); neighbor metadata joins
    internal chord junctions while retaining rounded physical arc-end caps.
    Posts and line segments are static-body shapes. No shape is organism-visible.
    """
    static = space.static_body
    groups: dict[str, tuple[pymunk.Shape, ...]] = {}
    wall_specs = {
        "wall_west": ((-0.01, -0.01), (0.0, -0.01), (0.0, 3.01), (-0.01, 3.01)),
        "wall_east": ((3.0, -0.01), (3.01, -0.01), (3.01, 3.01), (3.0, 3.01)),
        "wall_south": ((0.0, -0.01), (3.0, -0.01), (3.0, 0.0), (0.0, 0.0)),
        "wall_north": ((0.0, 3.0), (3.0, 3.0), (3.0, 3.01), (0.0, 3.01)),
    }
    if include_walls:
        for wall_name, vertices in wall_specs.items():
            shape: pymunk.Shape = pymunk.Poly(static, vertices)
            shape.friction = shape.elasticity = 0.0
            groups[wall_name] = (shape,)
            space.add(shape)

    for arc_spec in ARCS:
        points = arc_vertices(arc_spec)
        shapes: tuple[pymunk.Shape, ...] = tuple(
            pymunk.Segment(static, a, b, ARC_HALF_THICKNESS_M)
            for a, b in zip(points, points[1:])
        )
        for shape in shapes:
            shape.friction = shape.elasticity = 0.0
        _link_arc_segments(points, shapes)
        groups[arc_spec.name] = shapes
        space.add(*shapes)

    for segment_spec in SEGMENTS:
        segment_shape: pymunk.Shape = pymunk.Segment(
            static,
            segment_spec.start,
            segment_spec.end,
            SEGMENT_HALF_THICKNESS_M,
        )
        segment_shape.friction = segment_shape.elasticity = 0.0
        groups[segment_spec.name] = (segment_shape,)
        space.add(segment_shape)

    for post_spec in POSTS:
        post_shape: pymunk.Shape = pymunk.Circle(
            static, POST_RADIUS_M, post_spec.center
        )
        post_shape.friction = post_shape.elasticity = 0.0
        groups[post_spec.name] = (post_shape,)
        space.add(post_shape)
    return groups
