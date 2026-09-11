"""Focused pre-freeze tests for the D-035B evaluator-only LFR audit."""

from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import pytest

from aweform import d025, d027, d030, d033, d035b
from aweform.d027 import D027Observation
from aweform.env import Action
from aweform.exp003 import BeaconObservation


def _observation(left: float, forward: float, right: float) -> D027Observation:
    return D027Observation(
        energy=0.5,
        beacon=BeaconObservation(
            left=left,
            forward=forward,
            right=right,
            charging_contact=False,
        ),
        thermal=0.3,
    )


def test_d035b_freeze_seed_and_cap_guards() -> None:
    assert d035b.D035B_HORIZON == 70_000
    assert d035b.D035B_BRANCH_HORIZON == 4096
    assert d035b.D035B_CAPS_DEGREES == (5.0, 2.0, 1.0)
    assert d035b.D035B_DEFAULT_DEVELOPMENT_SEEDS == tuple(range(18468, 18488))
    assert (
        d035b._validate_d035b_development_seeds(
            d035b.D035B_DEFAULT_DEVELOPMENT_SEEDS
        )
        == d035b.D035B_DEFAULT_DEVELOPMENT_SEEDS
    )
    with pytest.raises(ValueError, match="exactly"):
        d035b._validate_d035b_development_seeds((18468, 18469))
    with pytest.raises(ValueError, match="reserved"):
        d035b._validate_d035b_development_seeds((50001, 50002))
    with pytest.raises(ValueError, match="only the reused"):
        d035b._validate_d035b_seed(18467)
    with pytest.raises(ValueError, match="70,000"):
        d035b.run_d035b_audit(
            seeds=d035b.D035B_DEFAULT_DEVELOPMENT_SEEDS,
            horizon=1,
            executed_commit_sha="0" * 40,
        )


def test_lfr_formula_zero_vector_and_interpolated_cap_are_exact() -> None:
    vector = d035b._lfr_vector(_observation(1.0, 0.0, 0.0))
    assert vector.x == pytest.approx(2**0.5 / 2.0)
    assert vector.y == pytest.approx(2**0.5 / 2.0)
    assert vector.theta_hat == pytest.approx(0.25 * 3.141592653589793)
    assert vector.zero_vector is False

    zero = d035b._lfr_vector(_observation(0.0, 0.0, 0.0))
    assert zero.x == 0.0
    assert zero.y == 0.0
    assert zero.theta_hat == 0.0
    assert zero.zero_vector is True

    assert d035b._lfr_turn_magnitude(
        vector,
        cap_degrees=5.0,
        variant="LFR_FIXED",
    ) == pytest.approx(5.0 * 3.141592653589793 / 180.0)
    assert d035b._lfr_turn_magnitude(
        vector,
        cap_degrees=5.0,
        variant="LFR_INTERP",
    ) == pytest.approx(5.0 * 3.141592653589793 / 180.0)
    shallow = d035b._lfr_vector(_observation(0.99, 1.0, 1.0))
    assert d035b._lfr_turn_magnitude(
        shallow,
        cap_degrees=5.0,
        variant="LFR_INTERP",
    ) < 5.0 * 3.141592653589793 / 180.0


def test_visible_side_reversal_is_a_visible_left_right_sign_flip() -> None:
    assert d035b._left_right_sign(0.8, 0.2) == 1
    assert d035b._left_right_sign(0.2, 0.8) == -1
    assert d035b._visible_side_reversal(Action.TURN_LEFT, 1, -1) is True
    assert d035b._visible_side_reversal(Action.TURN_RIGHT, -1, 1) is True
    assert d035b._visible_side_reversal(Action.TURN_LEFT, 1, 1) is False
    assert d035b._visible_side_reversal(Action.MOVE_FORWARD, 1, -1) is False
    assert d035b._visible_side_reversal(Action.TURN_LEFT, 0, -1) is False


def test_opposite_turn_fraction_keeps_non_turn_successors_in_denominator() -> None:
    summary = d035b._opposite_turn_summary(
        (Action.TURN_LEFT, Action.MOVE_FORWARD, Action.TURN_RIGHT)
    )
    assert summary["eligible_prior_turn_decision_count"] == 1
    assert summary["opposite_turn_count"] == 0
    assert summary["opposite_turn_next_eligible_seek_fraction"] == 0.0

    summary = d035b._opposite_turn_summary(
        (Action.TURN_LEFT, Action.TURN_RIGHT, Action.WAIT)
    )
    assert summary["eligible_prior_turn_decision_count"] == 2
    assert summary["opposite_turn_count"] == 1
    assert summary["opposite_turn_next_eligible_seek_fraction"] == 0.5


def test_first_false_contact_seek_is_pre_action_seek_not_away_entry() -> None:
    def row(
        transition: int,
        mode_before: d027.D027Mode,
        mode_after: d027.D027Mode,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            transition_index=transition,
            mode_before=mode_before,
            mode_after=mode_after,
            observation_before=(0.2, 0.0, 0.0, 0.0, 0.0, 0.3),
            observation=(0.2, 0.0, 0.0, 0.0, 0.0, 0.3),
            telemetry=SimpleNamespace(
                charging_contact_before=False,
                charging_contact_after=False,
            ),
        )

    trace = cast(
        tuple[d025.D025TransitionTrace, ...],
        (
            row(1, d027.D027Mode.AWAY, d027.D027Mode.SEEK),
            row(2, d027.D027Mode.SEEK, d027.D027Mode.SEEK),
        ),
    )
    assert d035b._first_false_contact_seek_transition(trace) == 2

    # Verify the same issue-defined identity on a bounded non-official replay.
    _, replay_trace, _ = d033._run_capture(
        18428,
        role="B",
        horizon=70_000,
        seed_validator=d030._validate_d030_seed,
    )
    transition = d035b._first_false_contact_seek_transition(replay_trace)
    assert transition is not None
    _, _, instrumentation = d033._run_capture(
        18428,
        role="B",
        horizon=70_000,
        target_transition=transition,
        seed_validator=d030._validate_d030_seed,
    )
    capture = instrumentation.capture
    assert capture is not None
    assert capture.mode_before is d027.D027Mode.SEEK
    assert capture.current.charging_contact is False
    assert capture.environment.charging_contact is False
    assert capture.delegated is False
    assert capture.greedy_action is not None


def test_prediction_strata_and_exact_post_anchor_windows() -> None:
    diagnostics = d035b._PredictionDiagnostics()
    vector = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6)
    rows = (
        (1, Action.WAIT),
        (16, Action.TURN_LEFT),
        (17, Action.TURN_RIGHT),
        (64, Action.MOVE_FORWARD),
        (65, Action.TURN_LEFT),
        (256, Action.TURN_RIGHT),
        (257, Action.WAIT),
        (1024, Action.TURN_LEFT),
        (1025, Action.TURN_RIGHT),
        (4096, Action.TURN_LEFT),
    )
    for transition, action in rows:
        diagnostics.record(vector, vector, action, transition)
    result = diagnostics.as_dict()
    all_actions = cast(dict[str, object], result["all_actions"])
    turn_only = cast(dict[str, object], result["turn_only"])
    assert all_actions["sample_count"] == 10
    assert turn_only["sample_count"] == 7
    assert set(cast(dict[str, object], all_actions["targets"])) == set(
        d027.D027_OUTPUTS
    )
    assert cast(dict[str, object], result["turn_left"])["sample_count"] == 4
    assert cast(dict[str, object], result["turn_right"])["sample_count"] == 3
    for window, expected_support in zip(
        ("1..16", "17..64", "65..256", "257..1024", "1025..4096"),
        (2, 2, 2, 2, 2),
        strict=True,
    ):
        record = cast(
            dict[str, object],
            cast(dict[str, object], result["post_anchor_windows"])[window],
        )
        assert record["support_count"] == expected_support
        assert cast(dict[str, object], record["all_actions"])[
            "sample_count"
        ] == expected_support
        assert set(
            cast(dict[str, object], cast(dict[str, object], record["all_actions"])[
                "targets"
            ])
        ) == set(d027.D027_OUTPUTS)
    left_targets = cast(
        dict[str, object],
        cast(dict[str, object], result["turn_left"])["targets"],
    )
    assert set(left_targets) == {"delta_beacon_forward"}
    right_targets = cast(
        dict[str, object],
        cast(dict[str, object], result["turn_right"])["targets"],
    )
    assert set(right_targets) == {"delta_beacon_forward"}


def test_lfr_branch_preserves_existing_logical_action_and_update_contract() -> None:
    # This uses a historical non-D-035B development seed and bounded branch
    # mechanics only; it does not execute or inspect the authorized D-035B seed
    # block or official output.
    result, trace, instrumentation = d033._run_capture(
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
    baseline, baseline_trace = d035b._run_branch(
        anchor,
        family="BASELINE_B",
        full_b_trace=trace,
    )
    interp, interp_trace = d035b._run_branch(
        anchor,
        family="LFR_INTERP_5DEG",
        full_b_trace=trace,
        cap_degrees=5.0,
        variant="LFR_INTERP",
    )
    assert baseline["baseline_continuation_exact"] is True
    assert len(baseline_trace) == 4096
    assert 1 <= len(interp_trace) <= 4096
    state = cast(dict[str, object], interp["branch_state"])
    assert state["branch_start_exact"] is True
    assert state["branch_did_not_mutate_anchor"] is True
    assert state["reward_zero_every_transition"] is True
    assert state["organism_info_empty_every_transition"] is True
    assert state["executed_action_only_updates"] is True
    assert state["logical_actions_existing_enum"] is True
    assert state["turn_time_energy_canonical"] is True
    assert state["no_false_contact_seek_explorer_call"] is True
    assert cast(int, interp["lfr_decision_count"]) > 0
    assert interp["lfr_decision_records_retained"] is True
    records = cast(list[dict[str, object]], interp["lfr_decision_records"])
    assert len(records) == interp["lfr_decision_count"]
    assert {
        "lfr_left",
        "lfr_forward",
        "lfr_right",
        "theta_hat_radians",
        "seek_action",
        "arm_b_would_have_executed_action",
        "executed_logical_action",
        "actual_angular_displacement_radians",
        "saturated",
        "beacon_forward_change_signed",
        "beacon_forward_change_absolute",
        "visible_left_right_sign_before",
        "visible_left_right_sign_after",
        "visible_side_reversal",
        "true_evaluator_station_bearing_radians",
        "directional_error_radians",
        "heading_change_radians",
        "rear_contact_pair_error_geometry",
    } <= set(records[0])
    compact = d035b._compact_lfr_decision_records(records)
    assert compact["record_count"] == len(records)
    decoded = d035b._decode_compact_lfr_decision_records(compact)
    assert decoded[0]["lfr_left"] == records[0]["lfr_left"]
    assert decoded[0]["seek_action"] == records[0]["seek_action"]
    assert decoded[0]["visible_side_reversal"] == records[0][
        "visible_side_reversal"
    ]
    assert decoded[0]["heading_change_radians"] == decoded[0][
        "actual_angular_displacement_radians"
    ]
    assert decoded[0]["beacon_forward_change_absolute"] == pytest.approx(
        abs(cast(float, decoded[0]["beacon_forward_change_signed"]))
    )
    assert decoded[0]["max_pair_error_after"] == cast(
        dict[str, object],
        cast(
            dict[str, object],
            cast(dict[str, object], records[0]["rear_contact_pair_error_geometry"])[
                "after"
            ],
        ),
    )["max_pair_error"]
    directional = cast(dict[str, object], interp["directional_interpolation"])
    assert cast(int, directional["decision_count"]) > 0
    assert directional["angular_error_support_count"] == len(records)
    assert directional["side_reversal_support_count"] == directional[
        "turn_decision_count"
    ]
    assert directional["saturation_rate"] == directional[
        "saturation_fraction_among_turns"
    ]
    assert {
        "FULL_NOMINAL_FORWARD",
        "BOUNDARY_CLIPPED_FORWARD",
        "FULL_STALL_FORWARD",
    } == set(cast(dict[str, object], interp["forward_boundary_counts"]))
    assert {
        "forward_nominal_count",
        "forward_clipped_count",
        "forward_stall_count",
    } <= set(interp)
    assert "opposite_turn_next_eligible_seek_fraction" in interp
    assert {
        "cumulative_commanded_signed_angle_radians",
        "cumulative_commanded_absolute_angle_radians",
        "turn_count",
        "turn_exposure",
        "cumulative_turn_time_seconds",
        "cumulative_turn_electrical_energy_j",
    } <= set(interp)
    turn_exposure = cast(dict[str, object], interp["turn_exposure"])
    assert turn_exposure["turn_count"] == interp["turn_count"]
    assert turn_exposure["canonical_turn_time_seconds"] == interp[
        "cumulative_turn_time_seconds"
    ]
    assert turn_exposure["canonical_turn_electrical_energy_j"] == interp[
        "cumulative_turn_electrical_energy_j"
    ]
    energy = cast(dict[str, object], interp["energy"])
    thermal = cast(dict[str, object], interp["thermal"])
    assert {"at_anchor", "minimum", "maximum", "final", "at_reacquisition"} <= set(
        energy
    )
    assert {"at_anchor", "minimum", "maximum", "final", "at_reacquisition"} <= set(
        thermal
    )
    geometry = cast(
        dict[str, object], interp["rear_contact_pair_error_geometry"]
    )
    assert {"start", "minimum", "final", "at_reacquisition"} <= set(geometry)
    contacts = cast(dict[str, object], interp["contact_events"])
    assert {"charging_contact_entry_count", "dual_contact_entry_count"} <= set(
        contacts
    )


def test_d035b_requires_clean_executable_sha_for_official_output() -> None:
    with pytest.raises(ValueError, match="exact clean executable"):
        d035b.run_d035b_audit(
            seeds=d035b.D035B_DEFAULT_DEVELOPMENT_SEEDS,
            executed_commit_sha=None,
        )


def test_d035b_rejects_nonexistent_executable_commit_sha() -> None:
    with pytest.raises(ValueError, match="existing Git commit"):
        d035b._validate_executed_commit_sha(
            "7fb0846f4f7f3d6c52785b5a7c96c1e99784a33f"
        )
