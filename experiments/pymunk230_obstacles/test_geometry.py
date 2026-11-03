# ruff: noqa: E402

from __future__ import annotations

import math

import pytest

pymunk = pytest.importorskip("pymunk")

from experiments.pymunk230_obstacles.audit import (
    ARC_AUDIT_ERROR_M,
    ARC_COLLISION_APPROX_ERROR_M,
    _segment_rect_distance,
    clearances_by_object,
    free_path_minimum_clearances,
)
from experiments.pymunk230_obstacles.cases import (
    OBSTACLE_LOGICAL_COMMANDS,
    PRIMARY_CASES,
    PRIMARY_ENGINE_STEPS,
    PRIMARY_LOGICAL_COMMANDS,
    TOTAL_ENGINE_STEPS_WITH_REPLAY,
)
from experiments.pymunk230_obstacles.geometry import (
    ARC_MAX_SAGITTA_M,
    ARC_MAX_STEP_DEG,
    ARCS,
    POSTS,
    SEGMENTS,
    _arc_neighbor_points,
    _link_arc_segments,
    add_arena,
    arc_vertices,
)
from experiments.pymunk230_obstacles.world import ObstacleContactWorld


def test_frozen_layout_and_arc_approximation_bound() -> None:
    assert [(arc.center, arc.start_deg, arc.end_deg) for arc in ARCS] == [
        ((1.50, 2.00), 30.0, 150.0),
        ((2.75, 1.50), 135.0, 225.0),
        ((0.40, 2.60), 270.0, 360.0),
    ]
    assert [(segment.start, segment.end) for segment in SEGMENTS] == [
        ((1.175, 0.55), (1.825, 0.55)),
        ((0.55, 1.10), (0.55, 1.75)),
    ]
    assert [(post.center) for post in POSTS] == [(2.35, 0.60), (2.45, 2.45)]
    assert ARC_MAX_STEP_DEG == 4.0
    assert ARC_MAX_SAGITTA_M < 0.00025
    for arc in ARCS:
        points = arc_vertices(arc)
        assert all(math.dist(a, b) > 0 for a, b in zip(points, points[1:]))
        assert len(points) - 1 == math.ceil((arc.end_deg - arc.start_deg) / 4.0)


def test_arc_neighbors_join_internal_chords_without_extending_physical_ends() -> None:
    points = ((0.0, 0.0), (1.0, 1.0), (2.0, 1.0), (3.0, 0.0))
    assert _arc_neighbor_points(points, 0) == (points[0], points[2])
    assert _arc_neighbor_points(points, 1) == (points[0], points[3])
    assert _arc_neighbor_points(points, 2) == (points[1], points[3])
    with pytest.raises(IndexError):
        _arc_neighbor_points(points, -1)
    with pytest.raises(IndexError):
        _arc_neighbor_points(points, 3)


def test_arc_linker_calls_neighbor_api_with_chain_vertices() -> None:
    class FakeSegment:
        def __init__(self) -> None:
            self.neighbors: tuple[object, object] | None = None

        def set_neighbors(self, previous: object, following: object) -> None:
            self.neighbors = previous, following

    points = ((0.0, 0.0), (1.0, 1.0), (2.0, 1.0), (3.0, 0.0))
    shapes = (FakeSegment(), FakeSegment(), FakeSegment())
    _link_arc_segments(points, shapes)  # type: ignore[arg-type]
    assert [shape.neighbors for shape in shapes] == [
        (pymunk.Vec2d(*points[0]), pymunk.Vec2d(*points[2])),
        (pymunk.Vec2d(*points[0]), pymunk.Vec2d(*points[3])),
        (pymunk.Vec2d(*points[1]), pymunk.Vec2d(*points[3])),
    ]


def test_arena_contains_seven_named_immovable_objects() -> None:
    space = pymunk.Space()
    groups = add_arena(space)
    assert set(groups) == {
        "wall_west",
        "wall_east",
        "wall_south",
        "wall_north",
        "A1",
        "A2",
        "A3",
        "S1",
        "S2",
        "P1",
        "P2",
    }
    assert sum(len(groups[name]) for name in ("A1", "A2", "A3")) == 76
    assert all(
        shape.body is space.static_body
        for shapes in groups.values()
        for shape in shapes
    )
    assert all(
        shape.radius == 0.025 for name in ("A1", "A2", "A3") for shape in groups[name]
    )
    assert all(groups[name][0].radius == 0.025 for name in ("S1", "S2"))
    assert all(groups[name][0].radius == 0.05 for name in ("P1", "P2"))


def test_world_reuses_single_inherited_room_wall_set() -> None:
    world = ObstacleContactWorld(microsteps=400)
    assert len(world.space.shapes) == 85
    assert len(world.obstacle_shapes["A1"]) == 30
    assert len(world.obstacle_shapes["A2"]) == 23
    assert len(world.obstacle_shapes["A3"]) == 23


def test_case_inventory_and_start_clearance_are_frozen() -> None:
    assert len(PRIMARY_CASES) == 38
    assert OBSTACLE_LOGICAL_COMMANDS == 307
    assert PRIMARY_LOGICAL_COMMANDS == 318
    assert PRIMARY_ENGINE_STEPS == 381_600
    assert PRIMARY_LOGICAL_COMMANDS * 400 == 127_200
    assert PRIMARY_LOGICAL_COMMANDS * 800 == 254_400
    assert TOTAL_ENGINE_STEPS_WITH_REPLAY == 763_200
    push_release = next(
        case for case in PRIMARY_CASES if case.case_id == "P1-sustained-push-release"
    )
    assert (
        push_release.commands[:20] == ((0.6457718232379019, 0.6457718232379019),) * 20
    )
    assert (
        push_release.commands[20:] == ((-0.6457718232379019, -0.6457718232379019),) * 9
    )


def test_audit_error_bound_and_frozen_case_start_clearance() -> None:
    assert ARC_AUDIT_ERROR_M < 0.000016
    assert ARC_COLLISION_APPROX_ERROR_M < 0.00025
    for case in PRIMARY_CASES:
        x, y, angle = case.start
        gaps = clearances_by_object((x, y), angle)
        assert min(gaps.values()) > 0.0, case.case_id
        path_minima = free_path_minimum_clearances(case.start, case.commands)
        if case.expect_contact:
            assert any(path_minima[name] <= 0.0 for name in case.expected_objects), (
                case.case_id
            )
    square = ((0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0))
    assert _segment_rect_distance((-1.0, 0.5), (2.0, 0.5), square) == 0.0
    assert _segment_rect_distance((-1.0, 2.0), (2.0, 2.0), square) == 1.0


@pytest.mark.skip(reason="behavioral reset stepping belongs only to frozen acceptance")
def test_reset_rebinds_contact_callback_and_restores_arena() -> None:
    world = ObstacleContactWorld(microsteps=400)
    world.reset((0.11, 1.5), math.pi)
    record = world.advance((0.6457718232379019, 0.6457718232379019))
    assert record.contact_seen
    assert record.contact_events
    assert all("wall_west" in event.shape_pair for event in record.contact_events)
    assert world.logical_steps == 1
    assert world.engine_steps == 400
    assert set(world.obstacle_shapes) >= {"A1", "A2", "A3", "S1", "S2", "P1", "P2"}
    assert world._contact_seen_this_command
