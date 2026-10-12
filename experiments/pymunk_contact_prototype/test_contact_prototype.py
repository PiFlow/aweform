"""Contract tests; the fixed corpus and organism lifetime are never run here."""

from __future__ import annotations

import hashlib
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
from experiments.pymunk_contact_prototype.run_contact_check_v3 import (
    EXPECTED_NO_CONTACT,
    compare_resolutions,
    expected_contacts_pass,
    planned_engine_steps,
    validate_stage1_result,
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
from experiments.pymunk_contact_prototype.run_lifetime_v3 import (
    MAX_PYMUNK_ENGINE_STEPS,
    MAX_TRANSITIONS,
    PRIMARY_MICROSTEPS,
    summarize_charging,
    validate_pymunk_transition,
    validate_reference_transition,
    validate_supervisor_approval,
    validate_v3_b_result,
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


def test_v3_fixture_accepts_frozen_resolutions_and_rejects_other_values() -> None:
    assert ContactWorld(microsteps=400).microsteps == 400
    assert ContactWorld(microsteps=800).microsteps == 800
    with pytest.raises(ValueError, match="400, or 800"):
        ContactWorld(microsteps=401)


def test_v3_fixture_contact_interface_at_400_substeps() -> None:
    world = ContactWorld(microsteps=400)
    world.body.position = (0.11, 1.5)
    world.body.angle = math.pi
    record = world.advance((MAX_DELTA, MAX_DELTA))
    assert record.step_count == 400
    assert world.engine_steps == 400
    assert record.contact_seen
    assert any(
        event.shape_pair == ("hull", "wall_west")
        for event in record.contact_events
    )


def test_v3_step_budget_is_frozen_without_running_cases() -> None:
    cases = fixed_cases()
    assert planned_engine_steps(cases, (400, 800)) == 956_400
    assert planned_engine_steps(cases, (400, 800)) * 2 == 1_912_800
    selected = tuple(
        next(case for case in cases if case.case_id == case_id)
        for case_id in (
            "wall-west-head-on",
            "wall-west-turn-0",
            "wall-south-turn-0",
            "wall-south-glance",
            "corner-se",
            "post-wall-adjacent",
            "post-tangent",
        )
    )
    assert planned_engine_steps(selected, (400, 800)) == 132_000


def test_v3_expected_contact_repair_classifies_no_contact_controls() -> None:
    controls = [
        {
            "case_id": case_id,
            "family": "wall-turn",
            "any_contact": False,
            "minimum_trajectory_clearance_m": 0.005,
        }
        for case_id in EXPECTED_NO_CONTACT
    ]
    assert expected_contacts_pass(controls, require_no_contact_controls=True)
    controls[0]["any_contact"] = True
    assert not expected_contacts_pass(controls, require_no_contact_controls=True)
    assert not expected_contacts_pass(
        [
            {
                "case_id": "wall-west-turn-0",
                "family": "wall-turn",
                "any_contact": False,
                "minimum_trajectory_clearance_m": 0.005,
            }
        ],
        require_no_contact_controls=False,
    )


def test_v3_contact_state_convergence_is_independent_of_clearance() -> None:
    case400 = {
        "case_id": "wall-case",
        "final_position_m": [1.0, 1.0],
        "final_yaw_rad": 0.0,
        "minimum_trajectory_clearance_by_shape_m": {"wall_west": 0.001},
        "steps": [
            {
                "contact_identities": ["hull|wall_west"],
                "minimum_trajectory_clearance_by_shape_m": {"wall_west": 0.001},
            }
        ],
    }
    case800 = {
        **case400,
        "minimum_trajectory_clearance_by_shape_m": {"wall_west": 0.002},
        "steps": [
            {
                **cast(list[dict[str, object]], case400["steps"])[0],
                "minimum_trajectory_clearance_by_shape_m": {"wall_west": 0.002},
            }
        ],
    }
    comparisons, contact_pass, clearance_pass = compare_resolutions(
        [case400], [case800]
    )
    assert contact_pass is True
    assert comparisons[0]["contact_state_pass"] is True
    assert clearance_pass is False
    assert comparisons[0]["per_shape_clearance_pass"] is False


def test_v3_existing_focused_output_refuses_before_runner_work(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import experiments.pymunk_contact_prototype.run_contact_check_v3 as runner

    output = tmp_path / "focused-probe"
    output.mkdir()
    monkeypatch.setattr(runner, "FOCUSED_OUTPUT", output)

    def unexpected_execution() -> str:
        raise AssertionError("source/physics work must not begin")

    monkeypatch.setattr(runner, "check_frozen_tree", unexpected_execution)
    with pytest.raises(FileExistsError):
        runner.run_focused(output)


def test_v3_replay_and_full_stage_require_valid_stage1_result(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="completed saved Stage 1"):
        validate_stage1_result(tmp_path, "candidate")

    import experiments.pymunk_contact_prototype.run_contact_check_v3 as runner

    result_dir = tmp_path / "saved-stage1"
    result_dir.mkdir()
    (result_dir / "MEASUREMENT_STARTED").write_text(
        "head=candidate\ncompleted=1\n", encoding="ascii"
    )
    saved = {
        "executable_sha": "candidate",
        "protocol_sha256": hashlib.sha256(
            runner.PROTOCOL.read_bytes()
        ).hexdigest(),
        "actual_engine_steps": 132_000,
        "full_stage2_authorized_by_probe": True,
        "gates": {"essential_stage1": "PASS"},
    }
    (result_dir / "focused-results.json").write_text(json.dumps(saved))
    assert validate_stage1_result(result_dir, "candidate") == saved
    saved["gates"] = {"essential_stage1": "FAIL"}
    (result_dir / "focused-results.json").write_text(json.dumps(saved))
    with pytest.raises(RuntimeError, match="do not authorize Stage 2"):
        validate_stage1_result(result_dir, "candidate")


def test_lifetime_adapter_reset_exposes_only_frozen_observation_contract() -> None:
    default_adapter = PymunkPhysiologyAdapter()
    assert default_adapter.world.microsteps == 10
    adapter = PymunkPhysiologyAdapter(microsteps=PRIMARY_MICROSTEPS)
    observation = adapter.reset()
    assert adapter.world.microsteps == 400
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


def test_lifetime_plan_has_exact_one_pair_ceiling() -> None:
    assert MAX_TRANSITIONS == 100_000
    assert PRIMARY_MICROSTEPS == 400
    assert MAX_PYMUNK_ENGINE_STEPS == 40_000_000


def test_lifetime_preflight_consumes_committed_v3_pass_without_running_it() -> None:
    from experiments.pymunk_contact_prototype import run_lifetime_v3 as runner

    result_path = runner.V3_B_RESULTS
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    validate_v3_b_result(
        payload, result_sha256=hashlib.sha256(result_path.read_bytes()).hexdigest()
    )


def test_lifetime_output_refusal_precedes_candidate_or_world_work(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from experiments.pymunk_contact_prototype import run_lifetime_v3 as runner

    output = tmp_path / "already-used"
    output.mkdir()

    def unexpected_work() -> str:
        raise AssertionError("candidate/runtime/world preflight must not begin")

    monkeypatch.setattr(runner, "EXPECTED_OUTPUT", output)
    monkeypatch.setattr(runner, "_assert_frozen_candidate", unexpected_work)
    with pytest.raises(FileExistsError, match="refuse before constructing a world"):
        runner.preflight(output)


def test_lifetime_approval_is_bound_to_exact_candidate_and_protocol() -> None:
    receipt = "a" * 64
    assert validate_supervisor_approval(
        candidate_head="candidate",
        protocol_sha256="protocol",
        approved_head="candidate",
        approved_protocol_sha256="protocol",
        approval_receipt_sha256=receipt,
    ) == receipt
    with pytest.raises(RuntimeError, match="does not bind"):
        validate_supervisor_approval(
            candidate_head="candidate",
            protocol_sha256="protocol",
            approved_head="other",
            approved_protocol_sha256="protocol",
            approval_receipt_sha256=receipt,
        )


def _synthetic_lifetime_row() -> dict[str, object]:
    return {
        "transition": 1,
        "engine_steps": 400,
        "observation": [0.5, 0.2, 0.3, 0.4, 0.3, 0.0, 0.0, 0.0],
        "reward": 0.0,
        "info": {},
        "max_penetration_m": 0.0,
        "end_penetration_m": 0.0,
        "crossed_wall_or_post": False,
        "clearance_sampling_bound_m": 0.000001,
        "impulse": 0.0,
        "contact_events": [],
        "paired_dock_contact_before": False,
        "paired_dock_contact_after": False,
        "dock_plus_error_m": 0.5,
        "dock_minus_error_m": 0.5,
        "contact": False,
        "charge_phase": "OFF",
        "charge_requested_stored_power_w": 0.0,
        "charge_stored_energy_j": 0.0,
        "charge_actual_stored_power_w": 0.0,
        "battery_before_j": 2664.0,
        "battery_after_j": 2663.985,
        "load_energy_j": 0.015,
        "charger_latch_before": False,
        "charger_latch_after": False,
    }


def test_lifetime_transition_safety_and_frozen_charge_accounting() -> None:
    row = _synthetic_lifetime_row()
    validate_pymunk_transition(row)
    reference = {**row, "engine_steps": 0, "truncated": False}
    validate_reference_transition(reference)
    unsafe = {**row, "max_penetration_m": 0.0011}
    with pytest.raises(RuntimeError, match="safety gate"):
        validate_pymunk_transition(unsafe)


def test_charging_summary_separates_proximity_contact_and_energy_transfer() -> None:
    no_contact = {
        **_synthetic_lifetime_row(),
        "station_distance_after_m": 0.25,
    }
    summary = summarize_charging([no_contact])
    assert summary["classification"] == "charging_not_exercised_no_paired_dock_contact"
    assert summary["paired_dock_contact_transition_count"] == 0
    assert summary["closest_station_center_distance_m"] == 0.25

    contacted = {
        **no_contact,
        "transition": 2,
        "paired_dock_contact_after": True,
        "contact": True,
        "dock_plus_error_m": 0.005,
        "dock_minus_error_m": 0.005,
        "charge_phase": "BULK",
        "charge_requested_stored_power_w": 20.0,
        "charge_actual_stored_power_w": 20.0,
        "charge_stored_energy_j": 2.0,
        "charger_latch_after": True,
        "battery_before_j": 2664.0,
        "battery_after_j": 2665.985,
        "load_energy_j": 0.015,
    }
    summary = summarize_charging([no_contact, contacted])
    assert summary["classification"] == "energy_transfer_observed"
    assert summary["paired_dock_contact_transition_count"] == 1
    assert summary["energy_transfer_transition_count"] == 1
    assert summary["charge_stored_energy_total_j"] == 2.0
    assert summary["charger_latch_transition_count"] == 1
