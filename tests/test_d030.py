"""Focused tests for the D-030 bounded learned SEEK-steering probe."""

from __future__ import annotations

import pytest

from aweform import d027, d030
from aweform.env import Action
from aweform.exp003 import BeaconObservation
from aweform.exp003_seed_policy import validate_exp003_development_seeds


def observation() -> d027.D027Observation:
    return d027.D027Observation(
        energy=0.25,
        beacon=BeaconObservation(0.1, 0.2, 0.3, False),
        thermal=0.2875,
    )


def prediction(forward_delta: float) -> d027.D027Prediction:
    values = [0.0] * len(d030.D030_OUTPUTS)
    values[d030.D030_FORWARD_OUTPUT_INDEX] = forward_delta
    return d027.D027Prediction(tuple(values))


def test_d030_freeze_and_exact_seed_guard() -> None:
    assert d030.D030_HORIZON == 70_000
    assert d030.D030_DEFAULT_DEVELOPMENT_SEEDS == tuple(range(18428, 18448))
    assert validate_exp003_development_seeds(d030.D030_DEFAULT_DEVELOPMENT_SEEDS) == (
        d030.D030_DEFAULT_DEVELOPMENT_SEEDS
    )
    assert (
        d030._validate_d030_development_seeds(d030.D030_DEFAULT_DEVELOPMENT_SEEDS)
        == d030.D030_DEFAULT_DEVELOPMENT_SEEDS
    )
    with pytest.raises(ValueError, match="requires exactly"):
        d030._validate_d030_development_seeds((18428,))
    with pytest.raises(ValueError, match="reserved"):
        d030._validate_d030_development_seeds((50001, 50002))


def test_only_three_steering_actions_and_raw_forward_output_are_used() -> None:
    current = observation()
    predictions = {
        Action.TURN_LEFT: prediction(0.01),
        Action.TURN_RIGHT: prediction(0.03),
        Action.MOVE_FORWARD: prediction(0.02),
    }
    assert d030.D030_STEERING_ACTIONS == (
        Action.TURN_LEFT,
        Action.TURN_RIGHT,
        Action.MOVE_FORWARD,
    )
    assert Action.WAIT not in d030.D030_STEERING_ACTIONS
    assert (
        d030._choose_steering_action(current, predictions, Action.TURN_LEFT)
        is Action.TURN_RIGHT
    )


def test_exact_prediction_tie_falls_back_to_historical_greedy() -> None:
    current = observation()
    predictions = {action: prediction(0.0) for action in d030.D030_STEERING_ACTIONS}
    assert (
        d030._choose_steering_action(current, predictions, Action.MOVE_FORWARD)
        is Action.MOVE_FORWARD
    )
    assert (
        d030._choose_permuted_action(current, predictions, Action.TURN_RIGHT)
        is Action.TURN_RIGHT
    )


def test_permutation_is_fixed_cyclic_relabeling() -> None:
    predictions = {
        Action.TURN_LEFT: prediction(1.0),
        Action.TURN_RIGHT: prediction(2.0),
        Action.MOVE_FORWARD: prediction(3.0),
    }
    scores = d030._permuted_scores(predictions)
    assert scores == {
        Action.TURN_LEFT: 2.0,
        Action.TURN_RIGHT: 3.0,
        Action.MOVE_FORWARD: 1.0,
    }


def test_short_matched_replay_is_deterministic_and_branch_disabled_is_exact() -> None:
    first = d030._run_d030_seed(18428, horizon=20)
    second = d030._run_d030_seed(18428, horizon=20)
    assert first == second
    for arm in d030.D030_ARM_NAMES:
        result = first["arms"][arm]
        assert isinstance(result, dict)
        assert result["transitions"] == 20
        assert result["isolation"]["real_updates_executed_action_only"] is True
    for arm in ("LEARNED_FORWARD", "PERMUTED_FORWARD"):
        result = first["arms"][arm]
        control = first["branch_disabled"][arm]
        assert isinstance(result, dict)
        assert isinstance(control, dict)
        assert (
            result["isolation"]["matched_branch_disabled"]["real_summary_exact_equal"]
            is True
        )
        assert result["branch_evaluation_count"] == 0
        assert control["branch_evaluation_count"] == 0


def test_complete_lifetime_exercises_three_candidate_branches() -> None:
    result = d030._run_arm(
        18428,
        arm="LEARNED_FORWARD",
        horizon=d030.D030_HORIZON,
        evaluator_diagnostics=True,
    )
    assert result["prediction_query_count"] > 0
    assert result["prediction_query_count"] == result["branch_evaluation_count"]
    assert (
        result["prediction_query_count"]
        == 3 * result["diagnostics"]["non_delegated_seek_decisions"]
    )
    isolation = result["isolation"]
    assert isolation["all_prediction_queries_read_only"] is True
    assert isolation["all_alternative_branch_environment_checks_unchanged"] is True
    assert isolation["all_alternative_branch_controller_checks_unchanged"] is True
    assert isolation["all_alternative_branch_rng_checks_unchanged"] is True
    assert isolation["selected_action_branch_matches_real_transition"] is True
