"""Independent oriented-hull clearance audit for the frozen room geometry."""

from __future__ import annotations

import math

from .geometry import (
    ARC_CENTERLINE_RADIUS_M,
    ARC_HALF_THICKNESS_M,
    ARCS,
    POST_RADIUS_M,
    POSTS,
    ROOM_SIDE_M,
    SEGMENT_HALF_THICKNESS_M,
    SEGMENTS,
)

ARC_AUDIT_ERROR_M = 1e-12
KINEMATIC_PATH_SAMPLES_PER_COMMAND = 64
WHEEL_RADIUS_M = 0.045
WHEEL_TRACK_M = 0.185

ARC_COLLISION_APPROX_ERROR_M = ARC_CENTERLINE_RADIUS_M * (
    1.0 - math.cos(math.radians(2.0))
)
CLEARANCE_ERROR_M = ARC_AUDIT_ERROR_M + ARC_COLLISION_APPROX_ERROR_M


def hull_corners(
    position: tuple[float, float], angle: float
) -> tuple[tuple[float, float], ...]:
    c, s = math.cos(angle), math.sin(angle)
    local = ((-0.09, -0.1075), (-0.09, 0.1075), (0.09, 0.1075), (0.09, -0.1075))
    return tuple(
        (position[0] + x * c - y * s, position[1] + x * s + y * c) for x, y in local
    )


def _point_segment_distance(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    dx, dy = end[0] - start[0], end[1] - start[1]
    length_sq = dx * dx + dy * dy
    if length_sq == 0.0:
        return math.dist(point, start)
    t = max(
        0.0,
        min(1.0, ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / length_sq),
    )
    return math.hypot(point[0] - (start[0] + t * dx), point[1] - (start[1] + t * dy))


def _orientation(
    a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]
) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _segments_intersect(
    a: tuple[float, float],
    b: tuple[float, float],
    c: tuple[float, float],
    d: tuple[float, float],
) -> bool:
    o1, o2 = _orientation(a, b, c), _orientation(a, b, d)
    o3, o4 = _orientation(c, d, a), _orientation(c, d, b)
    eps = 1e-14

    def on_segment(
        start: tuple[float, float],
        end: tuple[float, float],
        point: tuple[float, float],
    ) -> bool:
        return (
            min(start[0], end[0]) - eps <= point[0] <= max(start[0], end[0]) + eps
            and min(start[1], end[1]) - eps <= point[1] <= max(start[1], end[1]) + eps
        )

    return (
        (o1 > eps and o2 < -eps or o1 < -eps and o2 > eps)
        and (o3 > eps and o4 < -eps or o3 < -eps and o4 > eps)
    ) or any(
        abs(value) <= eps and on_segment(first, second, point)
        for value, first, second, point in (
            (o1, a, b, c),
            (o2, a, b, d),
            (o3, c, d, a),
            (o4, c, d, b),
        )
    )


def _point_rect_distance(
    point: tuple[float, float], corners: tuple[tuple[float, float], ...]
) -> float:
    signs = [_orientation(corners[i], corners[(i + 1) % 4], point) for i in range(4)]
    if all(value >= -1e-14 for value in signs) or all(
        value <= 1e-14 for value in signs
    ):
        return 0.0
    return min(
        _point_segment_distance(point, corners[i], corners[(i + 1) % 4])
        for i in range(4)
    )


def _segment_rect_distance(
    start: tuple[float, float],
    end: tuple[float, float],
    corners: tuple[tuple[float, float], ...],
) -> float:
    edges = tuple((corners[i], corners[(i + 1) % 4]) for i in range(4))
    if any(_segments_intersect(start, end, a, b) for a, b in edges):
        return 0.0
    return min(
        _point_rect_distance(start, corners),
        _point_rect_distance(end, corners),
        *(_point_segment_distance(corner, start, end) for corner in corners),
    )


def _angle_in_sweep(angle_deg: float, start_deg: float, end_deg: float) -> bool:
    angle = angle_deg % 360.0
    start, end = start_deg % 360.0, end_deg % 360.0
    return start <= angle <= end if start <= end else angle >= start or angle <= end


def _point_arc_distance(
    point: tuple[float, float],
    center: tuple[float, float],
    start_deg: float,
    end_deg: float,
    radius: float,
) -> float:
    dx, dy = point[0] - center[0], point[1] - center[1]
    angle = math.degrees(math.atan2(dy, dx))
    if _angle_in_sweep(angle, start_deg, end_deg):
        return abs(math.hypot(dx, dy) - radius)
    return min(
        math.dist(
            point,
            (
                center[0] + radius * math.cos(math.radians(endpoint)),
                center[1] + radius * math.sin(math.radians(endpoint)),
            ),
        )
        for endpoint in (start_deg, end_deg)
    )


def _arc_rect_distance(
    center: tuple[float, float],
    start_deg: float,
    end_deg: float,
    radius: float,
    corners: tuple[tuple[float, float], ...],
) -> float:
    endpoints = tuple(
        (
            center[0] + radius * math.cos(math.radians(angle)),
            center[1] + radius * math.sin(math.radians(angle)),
        )
        for angle in (start_deg, end_deg)
    )
    edges = tuple((corners[i], corners[(i + 1) % 4]) for i in range(4))
    candidates = [
        _point_arc_distance(point, center, start_deg, end_deg, radius)
        for point in corners
    ]
    candidates.extend(_point_rect_distance(point, corners) for point in endpoints)
    for first, second in edges:
        dx, dy = second[0] - first[0], second[1] - first[1]
        length_sq = dx * dx + dy * dy
        if length_sq:
            t = max(
                0.0,
                min(
                    1.0,
                    ((center[0] - first[0]) * dx + (center[1] - first[1]) * dy)
                    / length_sq,
                ),
            )
            foot = (first[0] + t * dx, first[1] + t * dy)
            candidates.append(
                _point_arc_distance(foot, center, start_deg, end_deg, radius)
            )
        fx, fy = first[0] - center[0], first[1] - center[1]
        aa = dx * dx + dy * dy
        bb = 2.0 * (fx * dx + fy * dy)
        cc = fx * fx + fy * fy - radius * radius
        discriminant = bb * bb - 4.0 * aa * cc
        if aa and discriminant >= 0.0:
            root = math.sqrt(discriminant)
            for t in ((-bb - root) / (2.0 * aa), (-bb + root) / (2.0 * aa)):
                if 0.0 <= t <= 1.0:
                    point = (first[0] + t * dx, first[1] + t * dy)
                    angle = math.degrees(
                        math.atan2(point[1] - center[1], point[0] - center[0])
                    )
                    if _angle_in_sweep(angle, start_deg, end_deg):
                        return 0.0
    return min(candidates)


def clearances_by_object(
    position: tuple[float, float], angle: float
) -> dict[str, float]:
    """Independent signed gaps; negative indicates hull/object overlap.

    Segment and circle gaps use exact rectangle-feature distances. Arc gap uses
    the analytic finite-circle-arc/rectangle distance, then subtracts the exact
    maximum 4° Pymunk chord sagitta plus 1e-12 m arithmetic allowance. Thus the
    reported lower bound is conservative against both the true strip and the
    implemented capsule chain.
    """
    corners = hull_corners(position, angle)
    result = {
        "wall_west": min(x for x, _ in corners),
        "wall_east": min(ROOM_SIDE_M - x for x, _ in corners),
        "wall_south": min(y for _, y in corners),
        "wall_north": min(ROOM_SIDE_M - y for _, y in corners),
    }
    for segment in SEGMENTS:
        result[segment.name] = (
            _segment_rect_distance(segment.start, segment.end, corners)
            - SEGMENT_HALF_THICKNESS_M
        )
    for post in POSTS:
        result[post.name] = _point_rect_distance(post.center, corners) - POST_RADIUS_M
    for arc in ARCS:
        result[arc.name] = (
            _arc_rect_distance(
                arc.center,
                arc.start_deg,
                arc.end_deg,
                ARC_CENTERLINE_RADIUS_M,
                corners,
            )
            - ARC_HALF_THICKNESS_M
            - CLEARANCE_ERROR_M
        )
    return result


def free_path_minimum_clearances(
    start: tuple[float, float, float],
    commands: tuple[tuple[float, float], ...],
) -> dict[str, float]:
    """Sample the exact unimpeded differential-drive path, without a Space.

    This is a premeasurement reachability check, not a collision simulation.
    It uses the frozen clipped wheel commands and exact constant-curvature
    kinematics, then the independent analytic geometry auditor.
    """
    x, y, angle = start
    minima = {name: math.inf for name in clearances_by_object((x, y), angle)}
    for left, right in commands:
        distance = WHEEL_RADIUS_M * (left + right) / 2.0
        yaw = WHEEL_RADIUS_M * (right - left) / WHEEL_TRACK_M
        for sample in range(KINEMATIC_PATH_SAMPLES_PER_COMMAND + 1):
            fraction = sample / KINEMATIC_PATH_SAMPLES_PER_COMMAND
            partial_yaw = yaw * fraction
            arc_length = distance * fraction
            half_yaw = partial_yaw / 2.0
            sinc = 1.0 if half_yaw == 0.0 else math.sin(half_yaw) / half_yaw
            travel = arc_length * sinc
            pose = (
                x + travel * math.cos(angle + half_yaw),
                y + travel * math.sin(angle + half_yaw),
                angle + partial_yaw,
            )
            for name, clearance in clearances_by_object(pose[:2], pose[2]).items():
                minima[name] = min(minima[name], clearance)
        half_yaw = yaw / 2.0
        travel = distance * (1.0 if half_yaw == 0.0 else math.sin(half_yaw) / half_yaw)
        x += travel * math.cos(angle + half_yaw)
        y += travel * math.sin(angle + half_yaw)
        angle += yaw
    return minima


def swept_crossing(
    start_clearances: dict[str, float],
    middle_clearances: dict[str, float],
    end_clearances: dict[str, float],
) -> bool:
    """Flag a clear-to-clear substep that intersects a solid at midpoint."""
    return any(
        start_clearances[name] >= 0.0
        and end_clearances[name] >= 0.0
        and middle_clearances[name] < 0.0
        for name in start_clearances
    )
