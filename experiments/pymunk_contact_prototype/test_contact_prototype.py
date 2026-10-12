"""Contract tests; the fixed corpus and organism lifetime are never run here."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Sequence, cast

import pytest

pytest.importorskip("pymunk")

from experiments.pymunk_contact_prototype.cases import fixed_cases
from experiments.pymunk_contact_prototype.fixture import (
    MAX_DELTA,
    POST_RADIUS,
    WALL_GEOMETRY,
    ContactWorld,
    circle_penetration,
    clearances_by_shape,
    clipped_action,
    corners,
    parse_action,
    wall_penetration,
)
from experiments.pymunk_contact_prototype.organism_lifetime import (
    PymunkPhysiologyAdapter,
)
from experiments.pymunk_contact_prototype.run_corrected_contact_check import (
    _contact_state_comparisons,
    _finite_values,
    _safe_canonical,
    measure,
    preflight_output,
)
from experiments.pymunk_contact_prototype.run_diagnostics import (
    validate_action_and_encoder_contract,
)
from experiments.pymunk_contact_prototype.run_lifetime_once import (
    validate_lifetime_gate,
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
    assert clearances_by_shape((0.09, 1.5), 0.0)["wall_west"] == pytest.approx(0.0)
    post_clearance = clearances_by_shape(
        (1.5, 1.5), 0.0, ((1.5, 1.5),)
    )["post_0"]
    assert post_clearance == pytest.approx(-0.14)


def test_frozen_case_inventory_contains_required_wall_and_post_families() -> None:
    cases = fixed_cases()
    ids = {case.case_id for case in cases}
    assert len(ids) == len(cases) == 255
    assert sum(len(case.commands) for case in cases) == 797
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


def test_reset_constructs_fresh_empty_or_posted_space() -> None:
    empty = ContactWorld(microsteps=10)
    posted = ContactWorld(microsteps=20, posts=((1.5, 1.5),))
    old_space, old_body = empty.space, empty.body
    empty.body.velocity = (3.0, -2.0)
    empty.body.angular_velocity = 1.0
    empty.reset((1.0, 1.0), math.pi / 3)
    assert empty.space is not old_space
    assert empty.body is not old_body
    assert empty.logical_steps == posted.logical_steps == 0
    assert empty.engine_steps == posted.engine_steps == 0
    assert empty.body.velocity == (0.0, 0.0)
    assert empty.body.angular_velocity == 0.0
    assert tuple(empty.body.position) == (1.0, 1.0)
    assert empty.body.angle == math.pi / 3
    assert empty.wall_geometry == WALL_GEOMETRY
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


def test_contact_callback_and_reset_behavior() -> None:
    world = ContactWorld(microsteps=10)
    world.body.position = (0.11, 1.5)
    world.body.angle = math.pi
    previous_space = world.space
    record = world.advance((MAX_DELTA, MAX_DELTA))
    assert record.contact_seen
    assert any(
        event.shape_pair == ("hull", "wall_west")
        for event in record.contact_events
    )
    world.reset((0.11, 1.5), math.pi)
    assert world.space is not previous_space
    assert world._contact_events == []
    assert world.logical_steps == world.engine_steps == 0


def test_existing_output_is_refused_before_measurement(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import experiments.pymunk_contact_prototype.run_corrected_contact_check as runner

    output = tmp_path / "already-created"
    output.mkdir()
    monkeypatch.setattr(runner, "EXPECTED_OUTPUT", output)

    def unexpected_execution() -> str:
        raise AssertionError("frozen-tree/measurement work must not begin")

    monkeypatch.setattr(runner, "check_frozen_tree", unexpected_execution)
    with pytest.raises(FileExistsError):
        preflight_output(output)
    with pytest.raises(FileExistsError):
        measure(output)


def test_resolution_comparison_enforces_clearance_and_contact_tolerance() -> None:
    base = {
        "case_id": "wall_case",
        "final_position_m": [0.1, 1.5],
        "final_yaw_rad": 0.0,
        "minimum_trajectory_clearance_by_shape_m": {"wall_west": 0.0002},
        "steps": [
            {
                "contact_identities": ["hull|wall_west"],
                "minimum_trajectory_clearance_by_shape_m": {"wall_west": 0.0002},
            }
        ],
    }
    base_step = cast(list[dict[str, object]], base["steps"])[0]
    near_contact = {
        **base,
        "steps": [{**base_step, "contact_identities": []}],
    }
    comparisons, passed = _contact_state_comparisons([base], [near_contact])
    assert passed
    assert comparisons[0]["contact_state_pass"] is True
    assert comparisons[0]["per_shape_clearance_pass"] is True

    distant_contact = {
        **near_contact,
        "steps": [
            {
                **cast(list[dict[str, object]], near_contact["steps"])[0],
                "minimum_trajectory_clearance_by_shape_m": {"wall_west": 0.001},
            }
        ],
        "minimum_trajectory_clearance_by_shape_m": {"wall_west": 0.001},
    }
    comparisons, passed = _contact_state_comparisons([base], [distant_contact])
    assert not passed
    assert comparisons[0]["per_shape_clearance_pass"] is False
    assert comparisons[0]["contact_state_pass"] is True

    far_contact = {
        **base,
        "minimum_trajectory_clearance_by_shape_m": {"wall_west": 0.001},
        "steps": [
            {
                **base_step,
                "minimum_trajectory_clearance_by_shape_m": {"wall_west": 0.001},
            }
        ],
    }
    far_no_contact = {
        **far_contact,
        "steps": [
            {
                **cast(list[dict[str, object]], far_contact["steps"])[0],
                "contact_identities": [],
            }
        ],
    }
    comparisons, passed = _contact_state_comparisons([far_contact], [far_no_contact])
    assert not passed
    assert comparisons[0]["per_shape_clearance_pass"] is True
    assert comparisons[0]["contact_state_pass"] is False


def test_replay_worker_refuses_without_an_active_primary_marker(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import experiments.pymunk_contact_prototype.run_corrected_contact_check as runner

    output_dir = tmp_path / "contact-check"
    output_dir.mkdir()
    output = output_dir / "fresh-process-replay.json"
    monkeypatch.setattr(runner, "EXPECTED_OUTPUT", output_dir)
    monkeypatch.setattr(runner, "REPLAY_PATH", output)

    def unexpected_execution(*, allow_output: bool = False) -> str:
        raise AssertionError("frozen-tree/measurement work must not begin")

    monkeypatch.setattr(runner, "check_frozen_tree", unexpected_execution)
    with pytest.raises(RuntimeError, match="active primary run"):
        runner.replay_worker(output, "candidate")


def test_nonfinite_measurements_are_serializable_but_fail_the_gate() -> None:
    payload = {"value": float("inf"), "nested": [float("nan")]}
    assert not _finite_values(payload)
    serialized = json.loads(_safe_canonical(payload))
    assert serialized == {"value": "Infinity", "nested": ["NaN"]}


def test_failed_contact_gate_refuses_lifetime_before_execution() -> None:
    with pytest.raises(RuntimeError, match="STOP before lifetime"):
        validate_lifetime_gate(
            {"executable_sha": "candidate", "essential_B_pass": False},
            "candidate",
        )
