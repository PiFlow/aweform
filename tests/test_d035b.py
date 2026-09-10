"""Focused pre-freeze tests for the D-035B evaluator-only LFR audit."""

from __future__ import annotations

from typing import cast

import pytest

from aweform import d030, d033, d035b
from aweform.d027 import D027Observation
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
    directional = cast(dict[str, object], interp["directional_interpolation"])
    assert cast(int, directional["decision_count"]) > 0


def test_d035b_requires_clean_executable_sha_for_official_output() -> None:
    with pytest.raises(ValueError, match="exact clean executable"):
        d035b.run_d035b_audit(
            seeds=d035b.D035B_DEFAULT_DEVELOPMENT_SEEDS,
            executed_commit_sha=None,
        )
