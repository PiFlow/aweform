"""Focused tests for the D-029 evaluator-only readiness audit."""

from __future__ import annotations

import copy

import pytest

from aweform import d027, d029
from aweform.env import Action
from aweform.exp003_seed_policy import validate_exp003_development_seeds


def test_d029_freeze_and_exact_seed_guard() -> None:
    assert d029.D029_HORIZON == 70_000
    assert d029.D029_DEFAULT_DEVELOPMENT_SEEDS == tuple(range(18408, 18428))
    assert validate_exp003_development_seeds(d029.D029_DEFAULT_DEVELOPMENT_SEEDS) == (
        d029.D029_DEFAULT_DEVELOPMENT_SEEDS
    )
    assert (
        d029._validate_d029_development_seeds(d029.D029_DEFAULT_DEVELOPMENT_SEEDS)
        == d029.D029_DEFAULT_DEVELOPMENT_SEEDS
    )
    with pytest.raises(ValueError, match="requires exactly"):
        d029._validate_d029_development_seeds((18408,))
    with pytest.raises(ValueError, match="reserved"):
        d029._validate_d029_development_seeds((50001, 50002))


def test_exact_support_registry_contains_only_prior_real_pairs() -> None:
    environment, observation_array, _streams = d029._initial_environment(4, 18408)
    del environment
    observation = d029._next_visible(observation_array)
    registry = d029.ExactExecutedExperienceRegistry()
    assert registry.support_count(observation, Action.WAIT) == 0
    registry.record(observation, Action.WAIT)
    assert registry.support_count(observation, Action.WAIT) == 1
    assert registry.support_count(observation, Action.MOVE_FORWARD) == 0
    assert registry.unique_pair_count == 1


def test_all_four_predictions_and_branches_are_non_mutating() -> None:
    environment, observation_array, streams = d029._initial_environment(4, 18408)
    observation = d029._next_visible(observation_array)
    predictor = d029.d027.D027ActionConsequencePredictor()
    before_weights = predictor.weights
    before_environment = d029._environment_state(environment)
    before_rng = d029._rng_state(streams)
    branches = d029._evaluate_branches(environment, observation, order=tuple(Action))
    predictions = {
        action: predictor.predict(observation, action) for action in Action
    }
    assert set(branches) == set(Action)
    assert len(predictions) == 4
    assert predictor.weights == before_weights
    assert d029._environment_state(environment) == before_environment
    assert d029._rng_state(streams) == before_rng


def test_fast_environment_clone_matches_full_deepcopy_state() -> None:
    environment, _observation, _streams = d029._initial_environment(4, 18408)
    fast = d029._clone_environment(environment)
    full = copy.deepcopy(environment)
    assert d029._environment_state(fast) == d029._environment_state(full)
    fast.step(Action.MOVE_FORWARD)
    full.step(Action.MOVE_FORWARD)
    assert d029._environment_state(fast) == d029._environment_state(full)


def test_selected_branch_matches_real_transition_and_only_real_action_updates() -> None:
    result = d029._run_lifetime(18408, horizon=2, audit=True)
    isolation = result["isolation"]
    assert isinstance(isolation, dict)
    assert isolation["all_four_prediction_queries_read_only"] is True
    assert isolation["all_alternative_branch_environment_checks_unchanged"] is True
    assert isolation["all_alternative_branch_controller_checks_unchanged"] is True
    assert isolation["all_alternative_branch_rng_checks_unchanged"] is True
    assert isolation["selected_action_branch_matches_real_transition"] is True
    assert isolation["real_updates_executed_action_only"] is True
    assert result["support"]["sample_count"] == 8  # type: ignore[index]
    assert result["transitions"] == 2


def test_real_lifetime_matches_unchanged_d027_path() -> None:
    audited = d029._run_lifetime(18408, horizon=12, audit=True)
    _reference, reference_trace = d027._run_lifetime(
        18408, horizon=12, learning=True
    )
    assert audited["trajectory_digest"] == d027._trace_digest(reference_trace)
    assert audited["_weights"] == _reference["learner"].weights  # type: ignore[index]


def test_branch_order_invariance_and_deterministic_replay() -> None:
    forward = d029._run_d029_seed(18408, horizon=4)
    reverse = d029._run_d029_seed(
        18408, horizon=4, branch_order=tuple(reversed(tuple(Action)))
    )
    replay = d029._run_d029_seed(18408, horizon=4)
    for field in (
        "trajectory_digest",
        "executed_update_digest",
        "final_weight_digest",
        "metrics",
        "pairwise_contrasts",
        "support",
    ):
        assert forward[field] == reverse[field] == replay[field]
    assert (
        forward["isolation"]["selected_action_branch_matches_real_transition"]
        is True
    )  # type: ignore[index]


def test_pairwise_contrast_tracks_ties_and_signs_per_output() -> None:
    diagnostics = d029._PairMetric()
    diagnostics.record(
        (1.0, -1.0, 0.0, 0.0, 1.0, -1.0),
        (1.0, 1.0, 0.0, -1.0, 1.0, -1.0),
    )
    result = diagnostics.as_dict()
    assert result["sample_count"] == 1
    assert result["actual_tie_count"] == [0, 0, 1, 0, 0, 0]
    assert result["non_tie_count"] == [1, 1, 0, 1, 1, 1]
    assert result["non_tie_sign_agreement_count"] == [1, 0, 0, 0, 1, 1]


def test_d029_does_not_add_visible_channels_or_learner_state() -> None:
    predictor = d029.d027.D027ActionConsequencePredictor()
    assert len(predictor.weights) == 168
    assert predictor.__slots__ == ("_weights",)
    assert d029.D029_CHANNELS == (
        "energy",
        "beacon.left",
        "beacon.forward",
        "beacon.right",
        "charging_contact",
        "thermal",
    )
    assert d029.D029_OUTPUTS == (
        "delta_energy",
        "delta_beacon_left",
        "delta_beacon_forward",
        "delta_beacon_right",
        "delta_charging_contact",
        "delta_thermal",
    )
