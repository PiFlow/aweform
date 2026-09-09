"""Focused tests for the D-032 evaluator-only attribution audit."""

from __future__ import annotations

from typing import cast

import pytest

from aweform import d032


def test_d032_freeze_and_reused_seed_guard() -> None:
    assert d032.D032_HORIZON == 70_000
    assert d032.D032_WINDOWS == (1, 4, 16, 64, 256, 1024, 4096)
    assert d032.D032_DEFAULT_DEVELOPMENT_SEEDS == tuple(range(18468, 18488))
    assert (
        d032._validate_d032_development_seeds(d032.D032_DEFAULT_DEVELOPMENT_SEEDS)
        == d032.D032_DEFAULT_DEVELOPMENT_SEEDS
    )
    with pytest.raises(ValueError, match="requires exactly"):
        d032._validate_d032_development_seeds((18468, 18469))
    with pytest.raises(ValueError, match="reserved"):
        d032._validate_d032_development_seeds((50001, 50002))
    with pytest.raises(ValueError, match="predeclared development seeds"):
        d032._validate_d032_seed(18467)
    with pytest.raises(ValueError, match="70,000"):
        d032.run_d032_audit(seeds=d032.D032_DEFAULT_DEVELOPMENT_SEEDS, horizon=1)


def test_d032_first_delegation_is_exactly_matched_and_causally_inert() -> None:
    result = d032._seed_result(
        18468,
        d032.D032_HORIZON,
        d032._accepted_artifact(),
    )
    onset = cast(dict[str, object], result["first_delegation_onset"])
    assert onset["status"] == "MATCHED_TREATMENT_ONSET"
    assert onset["pre_treatment_match"] is True
    assert all(cast(dict[str, bool], onset["pre_treatment_checks"]).values())
    assert all(cast(dict[str, bool], onset["treatment_checks"]).values())
    assert set(cast(dict[str, object], onset["windows"])) == {
        str(window) for window in d032.D032_WINDOWS
    }

    one_step = cast(dict[str, object], onset["immediate_one_step"])
    assert one_step["branch_environment_unchanged"] is True
    assert one_step["predictions_a_b_exact_equal"] is True
    assert set(cast(dict[str, float], one_step["actual_delta_beacon_forward"])) == {
        action.name for action in d032.D032_STEERING_ACTIONS
    }
    assert all(
        cast(dict[str, object], result["replay_equivalence"])[arm][
            "diagnostic_vs_direct_d031r1"
        ]["all_identity_fields_exact"]
        for arm in d032.D032_ARM_NAMES
    )


def test_d032_run_length_distribution_preserves_exact_action_runs() -> None:
    from aweform.env import Action

    distribution = d032._run_length_distribution(
        [
            Action.TURN_LEFT,
            Action.TURN_LEFT,
            Action.MOVE_FORWARD,
            Action.MOVE_FORWARD,
            Action.MOVE_FORWARD,
            Action.TURN_RIGHT,
        ]
    )
    assert distribution == {
        "MOVE_FORWARD:3": 1,
        "TURN_LEFT:2": 1,
        "TURN_RIGHT:1": 1,
    }
