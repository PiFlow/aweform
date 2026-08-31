"""Focused tests for the D-018 evaluator-only counterfactual audit."""

from __future__ import annotations

import copy

import pytest

from aweform import d011, d013, d014, d015, d018
from aweform.d002 import D002ThermalStationEnv
from aweform.env import Action
from aweform.exp003 import BeaconObservation, EXP003StationConfig
from aweform.exp003_seed_policy import validate_exp003_development_seeds


def _observation(
    *,
    energy: float = 0.4,
    left: float = 0.2,
    forward: float = 0.3,
    right: float = 0.5,
    contact: bool = True,
    thermal: float = 0.6,
) -> d011.D011Observation:
    return d011.D011Observation(
        energy=energy,
        beacon=BeaconObservation(left, forward, right, contact),
        thermal=thermal,
    )


def test_d018_seed_guard_is_exact_and_preserves_canonical_reservations() -> None:
    seeds = d018.D018_DEFAULT_DEVELOPMENT_SEEDS
    assert seeds == (18359, 18360, 18361)
    assert validate_exp003_development_seeds(seeds) == seeds
    assert d018._validate_d018_development_seeds(seeds) == seeds
    with pytest.raises(ValueError, match="only predeclared development seeds"):
        d018._validate_d018_development_seeds((18358,))
    with pytest.raises(ValueError, match="reserved for a formal experiment"):
        d018._validate_d018_development_seeds((50001,))


def test_alternative_predict_calls_are_non_mutating() -> None:
    predictor = d013.D013ActionConsequencePredictor()
    current = _observation()
    before = predictor.weights
    predictions = [predictor.predict(current, action) for action in Action]
    assert len(predictions) == len(Action)
    assert predictor.weights == before


def test_exact_support_registry_counts_only_prior_real_experience() -> None:
    registry = d018.ExactExecutedExperienceRegistry()
    current = _observation()
    nearly_same = _observation(energy=0.4 + 1e-15)
    assert registry.support_count(current, Action.WAIT) == 0
    registry.record(current, Action.WAIT)
    assert registry.support_count(current, Action.WAIT) == 1
    assert registry.support_count(current, Action.MOVE_FORWARD) == 0
    assert registry.support_count(nearly_same, Action.WAIT) == 0
    registry.record(current, Action.WAIT)
    assert registry.support_count(current, Action.WAIT) == 2
    assert registry.unique_pair_count == 1


def test_isolated_branch_does_not_mutate_real_environment_or_rng() -> None:
    environment = D002ThermalStationEnv(
        config=EXP003StationConfig(episode_horizon=20)
    )
    environment.reset(seed=18359)
    d011._prepare_post_contact_setup(environment)
    assert environment.body is not None
    before_body = copy.deepcopy(environment.body)
    before_thermal = environment.thermal_state
    before_transition = environment.last_transition
    before_rng = d018._rng_state(environment)
    branch = copy.deepcopy(environment)
    branch.step(Action.MOVE_FORWARD)
    assert environment.body == before_body
    assert environment.thermal_state == before_thermal
    assert environment.last_transition == before_transition
    assert d018._rng_state(environment) == before_rng


def test_d018_checks_executed_clone_fidelity_and_boundary() -> None:
    result = d018.run_d018_probe((18359,), horizon=2)
    assert result["organism_boundary"] == {"reward": 0.0, "info": {}}
    assert result["real_vs_reference_equality"][  # type: ignore[index]
        "all_executed_action_clone_checks_match"
    ] is True
    assert result["real_vs_reference_equality"][  # type: ignore[index]
        "all_alternative_branch_rng_checks_unchanged"
    ] is True
    run = result["results"][0]
    assert isinstance(run, dict)
    assert run["evaluator_only"][  # type: ignore[index]
        "selected_branch_matches_real_next_observation"
    ] is True
    assert run["audit"]["raw_prediction_count"] == 8  # type: ignore[index]


def test_only_physically_executed_action_updates_learner() -> None:
    result = d018.run_d018_probe((18359,), horizon=1)
    run = result["results"][0]
    assert isinstance(run, dict)
    assert run["action_counts"] == {  # type: ignore[index]
        "WAIT": 1,
        "TURN_LEFT": 0,
        "TURN_RIGHT": 0,
        "MOVE_FORWARD": 0,
    }
    weights = run["final_weights"]  # type: ignore[index]
    assert weights["delta_energy"]["WAIT"] != [0.0] * 7  # type: ignore[index]
    assert weights["delta_energy"]["MOVE_FORWARD"] == [0.0] * 7  # type: ignore[index]
    assert weights["delta_thermal"]["TURN_LEFT"] == [0.0] * 7  # type: ignore[index]
    assert weights["delta_charging_contact"]["TURN_RIGHT"] == [0.0] * 7  # type: ignore[index]


def test_counterfactual_outcomes_never_enter_plasticity() -> None:
    result = d018.run_d018_probe((18359,), horizon=30)
    run = result["results"][0]
    assert isinstance(run, dict)
    reference = d015._run_seed(18359, horizon=30)
    assert run["final_weights"] == reference["final_weights"]  # type: ignore[index]
    assert run["evaluator_only"][  # type: ignore[index]
        "counterfactual_outcomes_passed_to_learner"
    ] is False


def test_d018_real_trajectory_and_final_weights_equal_reference() -> None:
    result = d018.run_d018_probe((18359, 18360), horizon=40)
    equality = result["real_vs_reference_equality"]
    assert isinstance(equality, dict)
    assert equality["all_seeds_trajectory_exact_equal"] is True
    assert equality["all_seeds_relevant_summary_fields_exact_equal"] is True
    assert equality["all_seeds_final_84_weights_exact_equal"] is True
    assert equality["all_seeds_real_rng_state_exact_equal"] is True
    assert result["final_weight_equality"] == {
        "all_seeds_exact_equal": True,
        "weight_count": 84,
    }


def test_audit_records_all_actions_and_exact_support_flags() -> None:
    result = d018.run_d018_probe((18359,), horizon=3)
    run = result["results"][0]
    assert isinstance(run, dict)
    rows = run["audit"]["rows"]  # type: ignore[index]
    assert len(rows) == 12
    first_transition = [row for row in rows if row["transition_index"] == 1]
    assert len(first_transition) == 4
    assert all(
        row["prior_exact_state_action_support_count"] == 0
        for row in first_transition
    )
    assert all(row["prior_exact_support_is_zero"] for row in first_transition)
    assert all("zero_change_error_delta_energy" in row for row in rows)
    assert all("candidate_branch_terminated" in row for row in rows)


def test_empty_support_and_contact_event_cells_are_untested() -> None:
    result = d018.run_d018_probe((18359,), horizon=1)
    run = result["results"][0]
    assert isinstance(run, dict)
    metrics = run["audit"]["metrics"]["metrics_by"]  # type: ignore[index]
    assert metrics["prior_exact_support"]["zero"]["raw_count"] == 4  # type: ignore[index]
    assert metrics["prior_exact_support"][">=1"]["status"] == "untested"  # type: ignore[index]
    assert metrics["contact_target"]["exit"]["status"] == "untested"  # type: ignore[index]
    assert metrics["contact_target"]["entry"]["status"] == "untested"  # type: ignore[index]


def test_d018_does_not_add_visible_fields_or_learner_state() -> None:
    current = _observation()
    predictor = d013.D013ActionConsequencePredictor()
    assert not hasattr(current, "position")
    assert not hasattr(current, "heading")
    assert predictor.__slots__ == ("_weights",)
    assert d018.D018_DEFAULT_DEVELOPMENT_SEEDS == (18359, 18360, 18361)
    assert d018.D018_AUTHORITATIVE_BASE_SHA == (
        "3ad3d93ad7764f938e16fefc8e1536a414b7d9bc"
    )


def test_d018_uses_d014_controller_and_unchanged_action_set() -> None:
    assert issubclass(d014.D014Controller, d011.D011Controller)
    assert tuple(Action) == (
        Action.WAIT,
        Action.TURN_LEFT,
        Action.TURN_RIGHT,
        Action.MOVE_FORWARD,
    )
    result = d018.run_d018_probe((18359,), horizon=1)
    assert result["programmed"]["controller"] == "unchanged D014Controller"  # type: ignore[index]
