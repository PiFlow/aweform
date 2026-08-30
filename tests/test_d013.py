"""Focused tests for the D-013 full-observation shadow learner."""

from __future__ import annotations

import inspect
from dataclasses import fields

import pytest

from aweform import d011, d013
from aweform.d003 import HOT_DEPART_THRESHOLD
from aweform.env import Action
from aweform.exp003 import BeaconObservation
from aweform.exp003_seed_policy import validate_exp003_development_seeds


def observation(
    energy: float,
    left: float,
    forward: float,
    right: float,
    contact: bool,
    thermal: float,
) -> d011.D011Observation:
    return d011.D011Observation(
        energy=energy,
        beacon=BeaconObservation(left, forward, right, contact),
        thermal=thermal,
    )


def flatten(snapshot: dict[str, dict[str, list[float]]]) -> list[float]:
    return [
        weight
        for action in Action
        for output in d013.D013_OUTPUTS
        for weight in snapshot[output][action.name]
    ]


def test_feature_vector_is_exactly_full_current_d011_observation() -> None:
    current = observation(0.4, 0.2, 0.3, 0.5, True, 0.6)
    assert d013.D013ActionConsequencePredictor._features(current) == (
        1.0,
        0.4,
        0.2,
        0.3,
        0.5,
        1.0,
        0.6,
    )
    assert [field.name for field in fields(d011.D011Observation)] == [
        "energy",
        "beacon",
        "thermal",
    ]
    assert [field.name for field in fields(BeaconObservation)] == [
        "left",
        "forward",
        "right",
        "charging_contact",
    ]


def test_predictor_has_exactly_84_zero_initialized_weights_and_no_extra_state() -> None:
    predictor = d013.D013ActionConsequencePredictor()
    assert d013.D013_FEATURE_DIMENSION == 7
    assert d013.D013_PLASTIC_STATE_DIMENSION == 84
    assert len(predictor.weights) == 84
    assert predictor.weights == (0.0,) * 84
    assert predictor.__slots__ == ("_weights",)
    assert not hasattr(predictor, "rng")
    assert not hasattr(predictor, "history")
    assert not hasattr(predictor, "buffer")
    assert not hasattr(predictor, "optimizer_state")
    assert set(d013.D013_OUTPUTS) == {
        "delta_energy",
        "delta_thermal",
        "delta_charging_contact",
    }


def test_normalized_lms_updates_only_the_executed_action() -> None:
    predictor = d013.D013ActionConsequencePredictor()
    current = observation(0.4, 0.2, 0.3, 0.5, True, 0.6)
    next_observation = observation(0.6, 0.1, 0.4, 0.2, False, 0.8)
    update = predictor.observe_transition(
        current, Action.TURN_LEFT, next_observation
    )
    x = (1.0, 0.4, 0.2, 0.3, 0.5, 1.0, 0.6)
    normalizer = sum(value * value for value in x)
    expected_energy = [0.5 * 0.2 * value / normalizer for value in x]
    expected_thermal = [0.5 * 0.2 * value / normalizer for value in x]
    expected_contact = [0.5 * -1.0 * value / normalizer for value in x]
    snapshot = predictor.weight_snapshot()
    assert update.predicted_delta_energy == 0.0
    assert update.predicted_delta_thermal == 0.0
    assert update.predicted_delta_charging_contact == 0.0
    assert update.normalizer == pytest.approx(normalizer)
    assert snapshot["delta_energy"][Action.TURN_LEFT.name] == pytest.approx(
        expected_energy
    )
    assert snapshot["delta_thermal"][Action.TURN_LEFT.name] == pytest.approx(
        expected_thermal
    )
    assert snapshot["delta_charging_contact"][Action.TURN_LEFT.name] == pytest.approx(
        expected_contact
    )
    for action in Action:
        if action is not Action.TURN_LEFT:
            for output in d013.D013_OUTPUTS:
                assert snapshot[output][action.name] == [0.0] * 7


def test_predictions_are_pre_update_values_used_for_scoring() -> None:
    predictor = d013.D013ActionConsequencePredictor()
    current = observation(0.4, 0.2, 0.3, 0.5, True, 0.6)
    next_observation = observation(0.6, 0.1, 0.4, 0.2, False, 0.8)
    pre_update = predictor.predict(current, Action.WAIT)
    update = predictor.observe_transition(current, Action.WAIT, next_observation)
    assert pre_update == d013.D013Prediction(0.0, 0.0, 0.0)
    assert update.predicted_delta_energy == pre_update.predicted_delta_energy
    assert update.predicted_delta_thermal == pre_update.predicted_delta_thermal
    assert (
        update.predicted_delta_charging_contact
        == pre_update.predicted_delta_charging_contact
    )
    assert predictor.predict(current, Action.WAIT) != pre_update

    sums = d013._empty_metric_sums()
    d013._record_metrics(sums, pre_update, update)
    metrics = d013._metric_summary(sums)
    targets = metrics["targets"]
    assert isinstance(targets, dict)
    assert targets["delta_energy"]["learned_mae"] == pytest.approx(0.2)


def test_learner_interfaces_accept_only_typed_d011_observations() -> None:
    predictor = d013.D013ActionConsequencePredictor()
    assert list(inspect.signature(predictor.predict).parameters) == [
        "observation",
        "action",
    ]
    assert list(inspect.signature(predictor.observe_transition).parameters) == [
        "observation",
        "action",
        "next_observation",
    ]
    current = observation(0.4, 0.2, 0.3, 0.5, True, 0.6)
    with pytest.raises(ValueError, match="D011Observation"):
        predictor.predict(0, Action.WAIT)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="D011Observation"):
        predictor.observe_transition(current, Action.WAIT, 0)  # type: ignore[arg-type]
    assert not hasattr(current, "position")
    assert not hasattr(current, "distance")
    assert not hasattr(current, "heading")
    assert not hasattr(current, "station_position")
    assert not hasattr(current, "seed")
    assert not hasattr(current, "transition_index")
    assert not hasattr(current, "reward")
    assert not hasattr(current, "info")
    assert not hasattr(current, "controller_mode")


def test_runner_preserves_reward_info_and_reports_unvisited_support() -> None:
    result = d013.run_d013_probe((18344,), horizon=2)
    assert result["organism_boundary"] == {"reward": 0.0, "info": {}}
    assert result["development_seeds"] == [18344]
    run = result["results"][0]
    assert isinstance(run, dict)
    assert run["transitions"] == 2
    assert run["action_support"][Action.TURN_RIGHT.name]["status"] == "untested"
    right_metrics = run["action_support"][Action.TURN_RIGHT.name][
        "overall_target_metrics"
    ]
    assert right_metrics["delta_energy"]["status"] == "untested"
    assert right_metrics["delta_energy"]["learned_mae"] is None
    assert (
        run["action_context_support"]["False"][Action.TURN_RIGHT.name]["status"]
        == "untested"
    )
    assert run["checkpoints"] == {}
    assert len(flatten(run["final_weights"])) == 84


def test_development_validator_preserves_canonical_guard_and_declaration() -> None:
    assert d013.D013_DEFAULT_DEVELOPMENT_SEEDS == (18344, 18345, 18346)
    assert validate_exp003_development_seeds(d013.D013_DEFAULT_DEVELOPMENT_SEEDS) == (
        18344,
        18345,
        18346,
    )
    assert d013._validate_d013_development_seeds((18344,)) == (18344,)
    with pytest.raises(ValueError, match="reserved for a formal experiment"):
        d013.run_d013_probe((50001,), horizon=1)
    with pytest.raises(ValueError, match="only predeclared development seeds"):
        d013.run_d013_probe((18144,), horizon=1)


def test_predictions_cannot_change_d011_selected_actions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline = d013.run_d013_probe((18344,), horizon=80)

    def adversarial_predict(
        _predictor: d013.D013ActionConsequencePredictor,
        _observation: d011.D011Observation,
        _action: Action,
    ) -> d013.D013Prediction:
        return d013.D013Prediction(1e9, -1e9, 1e9)

    monkeypatch.setattr(
        d013.D013ActionConsequencePredictor, "predict", adversarial_predict
    )
    adversarial = d013.run_d013_probe((18344,), horizon=80)
    assert adversarial["results"][0]["action_counts"] == baseline["results"][0][
        "action_counts"
    ]


def test_d013_matches_unchanged_d011_behavioral_invariants() -> None:
    d011_run = d011._run_seed(18344, horizon=120)
    d013_run = d013._run_seed(18344, horizon=120)
    for key in (
        "transitions",
        "terminated",
        "truncated",
        "termination_reason",
        "action_counts",
        "mode_occupancy",
        "mode_entry_counts",
        "minimum_normalized_energy",
        "final_normalized_energy",
        "minimum_thermal_state",
        "maximum_thermal_state",
        "thermal_termination",
        "energy_termination",
        "completed_autonomous_regulation_cycles",
        "low_energy_seek_entries",
        "successful_charging_contact_reacquisitions",
    ):
        assert d013_run[key] == d011_run[key]
    assert d013_run["evaluator_only"]["passed_to_learner"] is False


def test_runner_distinguishes_horizon_censored_seek_from_demonstrated_failure() -> None:
    result = d013.run_d013_probe((18346,), horizon=1000)
    run = result["results"][0]
    assert isinstance(run, dict)
    assert run["low_energy_seek_entries"] == 12
    assert run["successful_charging_contact_reacquisitions"] == 11
    assert run["demonstrated_failed_seek_episodes"] == 0
    assert run["horizon_censored_seek_episodes"] == 1


def test_runner_records_all_targets_and_weight_checkpoints() -> None:
    result = d013.run_d013_probe((18344,), horizon=1000)
    run = result["results"][0]
    assert isinstance(run, dict)
    assert set(run["prediction_metrics"]["windows"]) == {"Q1", "Q2", "Q3", "Q4"}
    assert set(run["prediction_metrics"]["overall"]["targets"]) == set(
        d013.D013_OUTPUTS
    )
    assert set(run["checkpoints"]) == {"250", "500", "750", "1000"}
    assert len(flatten(run["final_weights"])) == 84
    assert run["evaluator_only"]["trajectory_geometry_collected"] is False
    assert run["evaluator_only"]["passed_to_learner"] is False
    assert result["organism_visible"]["controller_mode_is_learner_input"] is False
    assert result["organism_visible"]["policy_rng_is_learner_input"] is False
    assert result["organism_visible"]["evaluator_geometry_is_learner_input"] is False
    assert HOT_DEPART_THRESHOLD == 0.60
