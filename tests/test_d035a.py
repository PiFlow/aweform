"""Focused pre-freeze tests for the D-035A evaluator-only turn audit."""

from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import pytest

from aweform import d030, d033, d035a
from aweform.d026 import D026Mode
from aweform.env import Action


def test_d035a_freeze_angles_and_seed_guard() -> None:
    assert d035a.D035A_HORIZON == 70_000
    assert d035a.D035A_BRANCH_HORIZON == 4_096
    assert d035a.D035A_DEFAULT_DEVELOPMENT_SEEDS == tuple(range(18468, 18488))
    assert d035a.D035A_CONDITIONS == (
        "TURN_45_CONTROL",
        "TURN_5",
        "TURN_2",
        "TURN_1",
    )
    assert d035a.D035A_TURN_45_CONTROL_ANGLE == pytest.approx(3.141592653589793 / 4)
    assert d035a.D035A_TURN_5_ANGLE == pytest.approx(3.141592653589793 / 36)
    assert d035a.D035A_TURN_2_ANGLE == pytest.approx(3.141592653589793 / 90)
    assert d035a.D035A_TURN_1_ANGLE == pytest.approx(3.141592653589793 / 180)
    assert d035a.D020PhysicalConfig().turn_angle == d035a.D035A_TURN_45_CONTROL_ANGLE
    assert (
        d035a._validate_d035a_development_seeds(
            d035a.D035A_DEFAULT_DEVELOPMENT_SEEDS
        )
        == d035a.D035A_DEFAULT_DEVELOPMENT_SEEDS
    )
    with pytest.raises(ValueError, match="exactly"):
        d035a._validate_d035a_development_seeds((18468, 18469))
    with pytest.raises(ValueError, match="reserved"):
        d035a._validate_d035a_development_seeds((50001, 50002))
    with pytest.raises(ValueError, match="only the reused"):
        d035a._validate_d035a_seed(18467)
    with pytest.raises(ValueError, match="exact clean executable SHA"):
        d035a.run_d035a_audit(
            seeds=d035a.D035A_DEFAULT_DEVELOPMENT_SEEDS,
            executed_commit_sha=None,
        )


def test_d035a_first_anchor_requires_pre_action_seek_and_false_contact() -> None:
    rows = [
        SimpleNamespace(
            mode_before=D026Mode.AWAY,
            observation_before=(0.2, 0.1, 0.1, 0.1, 0.0, 0.3),
        ),
        SimpleNamespace(
            mode_before=D026Mode.SEEK,
            observation_before=(0.2, 0.1, 0.1, 0.1, 0.0, 0.3),
            transition_index=2,
        ),
    ]
    assert d035a._first_false_contact_seek_transition(rows) == 2
    contact_rows = [
        SimpleNamespace(
            mode_before=D026Mode.SEEK,
            observation_before=(0.2, 0.1, 0.1, 0.1, 1.0, 0.3),
            transition_index=1,
        )
    ]
    assert d035a._first_false_contact_seek_transition(contact_rows) is None


def test_d035a_prediction_metrics_preserve_support_and_turn_strata() -> None:
    records = (
        d035a._PredictionRecord(
            1, Action.TURN_LEFT, (1, 2, 3, 4, 5, 6), (0, 1, 2, 3, 4, 5)
        ),
        d035a._PredictionRecord(
            2, Action.TURN_RIGHT, (0, 0, 0, 0, 0, 0), (1, 1, 1, 1, 1, 1)
        ),
        d035a._PredictionRecord(
            3, Action.WAIT, (0, 0, 0, 0, 0, 0), (0, 0, 0, 0, 0, 0)
        ),
    )
    metrics = d035a._prediction_metrics(records)
    assert metrics["executed_transition_count"] == 3
    all_six = cast(dict[str, object], metrics["all_six_outputs"])
    assert all_six["transition_count"] == 3
    assert all_six["scalar_count"] == 18
    turns = cast(dict[str, object], metrics["turn_actions"])
    assert turns["transition_count"] == 2
    forward = cast(dict[str, object], metrics["delta_beacon_forward"])
    assert cast(dict[str, object], forward["TURN_LEFT"])["sample_count"] == 1
    assert cast(dict[str, object], forward["TURN_RIGHT"])["sample_count"] == 1


def test_d035a_bounded_branch_changes_only_isolated_turn_angle() -> None:
    # D-030 support is intentionally used for this bounded mechanics test; it
    # does not execute or inspect official D-035A treatment outcomes.
    result, trace, instrumentation = d033._run_capture(
        18428,
        role="B",
        horizon=20,
        target_transition=1,
        seed_validator=d030._validate_d030_seed,
    )
    del result
    capture = instrumentation.capture
    assert capture is not None
    anchor = d033._anchor_from_capture(18428, "PRE_FREEZE", capture)
    run = d035a._run_branch(anchor, condition="TURN_5")
    assert len(run.trace) == len(trace) == 20
    assert run.output["turn_angle_expression"] == "math.pi / 36.0"
    assert run.output["turn_angle_degrees"] == pytest.approx(5.0)
    branch_state = cast(dict[str, object], run.output["branch_state"])
    assert branch_state["branch_start_exact"] is True
    assert branch_state["branch_did_not_mutate_anchor"] is True
    assert branch_state["reward_zero_every_transition"] is True
    assert branch_state["organism_info_empty_every_transition"] is True
    assert branch_state["exactly_one_d027_update_per_transition"] is True
    assert branch_state["truth_branch_order_invariant"] is True
    assert branch_state["only_turn_angle_config_field_changed"] is True
    assert branch_state["canonical_turn_energy_and_time_unchanged"] is True


def test_d035a_control_matches_reused_d033_baseline() -> None:
    result, trace, instrumentation = d033._run_capture(
        18428,
        role="B",
        horizon=20,
        target_transition=1,
        seed_validator=d030._validate_d030_seed,
    )
    del result
    capture = instrumentation.capture
    assert capture is not None
    anchor = d033._anchor_from_capture(18428, "PRE_FREEZE", capture)
    control = d035a._run_branch(anchor, condition="TURN_45_CONTROL")
    baseline = d033._run_branch(
        anchor,
        family="BASELINE_B",
        requested_length=0,
        sequence=(),
    )
    identity = d035a._control_identity(control, baseline)
    assert identity["trace_exact"] is True
    assert identity["all_causal_fields_exact"] is True


def test_d035a_fine_angle_is_applied_only_to_turn_displacement() -> None:
    # This is a bounded non-official D-030 support check at an actual SEEK
    # state, so it exercises angular displacement without official output.
    result, _, instrumentation = d033._run_capture(
        18428,
        role="B",
        horizon=70_000,
        target_transition=24_326,
        seed_validator=d030._validate_d030_seed,
    )
    del result
    capture = instrumentation.capture
    assert capture is not None
    anchor = d033._anchor_from_capture(18428, "PRE_FREEZE", capture)
    assert anchor.controller.mode is D026Mode.SEEK
    assert anchor.current.charging_contact is False
    control = d035a._run_branch(anchor, condition="TURN_45_CONTROL")
    fine = d035a._run_branch(anchor, condition="TURN_5")
    assert control.output["action_counts"] != fine.output["action_counts"]
    control_exposure = cast(dict[str, object], control.output["turn_exposure"])
    fine_exposure = cast(dict[str, object], fine.output["turn_exposure"])
    assert control_exposure["turn_action_count"] == 4080
    assert fine_exposure["turn_action_count"] == 4096
    assert control_exposure["cumulative_turn_time_seconds"] == pytest.approx(408.0)
    assert fine_exposure["cumulative_turn_time_seconds"] == pytest.approx(409.6)
    assert fine_exposure["cumulative_turn_actuator_energy_j"] == pytest.approx(
        4096 * 0.65 * 0.1
    )
