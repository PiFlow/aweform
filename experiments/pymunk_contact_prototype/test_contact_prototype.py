"""Software-contract tests only; no diagnostics or lifetime is executed here."""

from __future__ import annotations

import math
from typing import Sequence, cast

import pytest

pytest.importorskip("pymunk")

from experiments.pymunk_contact_prototype.cases import fixed_cases
from experiments.pymunk_contact_prototype.fixture import (
    MAX_DELTA,
    POST_RADIUS,
    ContactWorld,
    circle_penetration,
    clipped_action,
    corners,
    parse_action,
    wall_penetration,
)
from experiments.pymunk_contact_prototype.organism_lifetime import (
    PymunkPhysiologyAdapter,
)
from experiments.pymunk_contact_prototype.run_diagnostics import (
    validate_action_and_encoder_contract,
)


def test_action_validation_rejects_invalid_and_clips_each_shaft_independently() -> None:
    assert clipped_action((2 * MAX_DELTA, -3 * MAX_DELTA)) == (
        (2 * MAX_DELTA, -3 * MAX_DELTA),
        (MAX_DELTA, -MAX_DELTA),
    )
    for value in (
        (),
        (1,),
        (1, 2, 3),
        "12",
        b"12",
        True,
        1,
        1.0,
        (True, 0),
        ("1", 0),
        (float("nan"), 0),
        (float("inf"), 0),
        (-float("inf"), 0),
    ):
        with pytest.raises(ValueError):
            parse_action(cast(Sequence[object], value))


def test_scalar_action_preflight_rejects_without_physics_steps() -> None:
    result = validate_action_and_encoder_contract()
    assert result["rejected_count"] == result["invalid_count"]
    assert result["invalid_no_step"] is True
    assert result["pass"] is True


def test_rectangle_geometry_and_circle_overlap_are_independent_calculations() -> None:
    assert len(corners((1.5, 1.5), 0.0)) == 4
    assert wall_penetration((1.5, 1.5), 0.0) == 0.0
    assert wall_penetration((0.0, 1.5), 0.0) == pytest.approx(0.09)
    assert circle_penetration((1.5, 1.5), 0.0, (1.5, 1.5), POST_RADIUS) > POST_RADIUS
    assert circle_penetration((0.0, 0.0), 0.0, (1.0, 1.0), POST_RADIUS) == 0.0


def test_frozen_case_inventory_contains_required_wall_and_post_families() -> None:
    cases = fixed_cases()
    ids = {case.case_id for case in cases}
    assert len(ids) == len(cases)
    assert len([case for case in cases if case.family == "calibration"]) == 216
    assert all(
        any(token in case.case_id for token in ("west", "east", "south", "north"))
        for case in cases
        if case.family in {"wall-head-on", "wall-turn", "wall-glance"}
    )
    required = {
        "post-head-on",
        "post-tangent",
        "post-sustained",
        "post-release",
        "post-turn",
        "post-near-miss",
        "post-wall-adjacent",
    }
    assert required <= ids
    assert all(case.microsteps == 10 for case in cases if case.family != "calibration")


def test_reset_constructs_fresh_empty_or_posted_space_without_stepping() -> None:
    empty = ContactWorld(microsteps=10)
    posted = ContactWorld(microsteps=20, posts=((1.5, 1.5),))
    empty.body.velocity = (3.0, -2.0)
    empty.body.angular_velocity = 1.0
    empty.reset((1.0, 1.0), math.pi / 3)
    assert empty.logical_steps == posted.logical_steps == 0
    assert empty.engine_steps == posted.engine_steps == 0
    assert empty.body.velocity == (0.0, 0.0)
    assert empty.body.angular_velocity == 0.0
    assert tuple(empty.body.position) == (1.0, 1.0)
    assert empty.body.angle == math.pi / 3
    assert len(empty.space.shapes) == 5  # hull + four room walls
    assert len(posted.space.shapes) == 6  # plus one fixed circular post
    assert not math.isnan(empty.body.moment)
    assert empty.space.iterations == 10


def test_lifetime_adapter_reset_exposes_only_frozen_observation_contract() -> None:
    adapter = PymunkPhysiologyAdapter()
    observation = adapter.reset()
    assert observation.shape == (8,)
    assert observation.dtype == __import__("numpy").float32
    assert adapter.world.posts == ()
    assert adapter.world.logical_steps == adapter.world.engine_steps == 0
    assert adapter.proposals.decision_count == 0


def test_protocol_keeps_organism_lifetime_obstacle_free_and_gates_one_shot() -> None:
    protocol = __import__("pathlib").Path(__file__).with_name("protocol.md").read_text()
    assert "zero interior obstacles" in protocol
    assert "no Pymunk collision shapes" not in protocol
    assert (
        "same_source_replay"
        in __import__("pathlib")
        .Path(__file__)
        .with_name("run_diagnostics.py")
        .read_text()
    )
    one_shot = (
        __import__("pathlib")
        .Path(__file__)
        .with_name("run_lifetime_once.py")
        .read_text()
    )
    assert "essential_B_pass" in one_shot
    assert "already exists; never rerun" in one_shot
