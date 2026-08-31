"""Focused tests for the D-015 D-014 shadow consequence diagnostic."""

from __future__ import annotations

from dataclasses import fields

import numpy as np
import pytest

from aweform import d011, d013, d014, d015
from aweform.env import Action
from aweform.exp003 import BeaconObservation
from aweform.exp003_seed_policy import validate_exp003_development_seeds


def observation(
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


def test_d015_seed_declaration_and_guards() -> None:
    assert d015.D015_DEFAULT_DEVELOPMENT_SEEDS == (18350, 18351, 18352)
    assert validate_exp003_development_seeds(d015.D015_DEFAULT_DEVELOPMENT_SEEDS) == (
        18350,
        18351,
        18352,
    )
    assert d015._validate_d015_development_seeds((18350,)) == (18350,)
    with pytest.raises(ValueError, match="only predeclared development seeds"):
        d015._validate_d015_development_seeds((42,))
    with pytest.raises(ValueError, match="reserved for a formal experiment"):
        d015._validate_d015_development_seeds((50001,))


def test_d015_uses_d014_controller_and_d013_predictor() -> None:
    assert issubclass(d014.D014Controller, d011.D011Controller)
    result = d015.run_d015_probe((18350,), horizon=1)
    assert result["programmed"]["controller"] == "D014Controller"
    assert result["learner"]["implementation"] == (
        "d013.D013ActionConsequencePredictor"
    )


def test_reused_predictor_is_exactly_zero_initialized_84_scalar_state() -> None:
    predictor = d013.D013ActionConsequencePredictor()
    assert predictor.weights == (0.0,) * 84
    assert len(predictor.weights) == d013.D013_PLASTIC_STATE_DIMENSION == 84
    assert predictor.predict(observation(), Action.WAIT) == d013.D013Prediction(
        0.0, 0.0, 0.0
    )
    assert predictor.__slots__ == ("_weights",)


def test_reused_predictor_updates_only_executed_action_and_keeps_exact_features(
) -> None:
    current = observation()
    next_observation = observation(0.6, 0.1, 0.4, 0.2, False, 0.8)
    predictor = d013.D013ActionConsequencePredictor()
    update = predictor.observe_transition(current, Action.TURN_LEFT, next_observation)
    features = (1.0, 0.4, 0.2, 0.3, 0.5, 1.0, 0.6)
    normalizer = sum(value * value for value in features)
    assert d013.D013ActionConsequencePredictor._features(current) == features
    assert update.predicted_delta_charging_contact == 0.0
    assert predictor.weight_snapshot()["delta_energy"][
        Action.TURN_LEFT.name
    ] == pytest.approx(
        [0.5 * 0.2 * value / normalizer for value in features]
    )
    for action in Action:
        if action is not Action.TURN_LEFT:
            assert predictor.weight_snapshot()["delta_energy"][action.name] == [0.0] * 7


def test_d015_learner_boundary_has_no_extra_observation_fields_or_state() -> None:
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
    predictor = d013.D013ActionConsequencePredictor()
    assert not any(
        hasattr(predictor, name)
        for name in ("history", "seed", "horizon", "event_class")
    )
    assert not any(
        hasattr(observation(), name)
        for name in (
            "controller_mode",
            "departure_event",
            "seed",
            "transition_index",
            "horizon",
            "reward",
            "info",
            "position",
            "heading",
            "station_position",
        )
    )


def test_d015_runner_preserves_reward_info_and_boundaries() -> None:
    result = d015.run_d015_probe((18350,), horizon=2)
    assert result["organism_boundary"] == {"reward": 0.0, "info": {}}
    assert result["development_seeds"] == [18350]
    assert result["results"][0]["transitions"] == 2
    assert result["evaluator_only"]["event_classification"].startswith(
        "exact observed"
    )


@pytest.mark.parametrize(
    ("delta", "expected"),
    ((-1.0, "contact_exit"), (0.0, "contact_unchanged"), (1.0, "contact_entry")),
)
def test_exact_contact_event_classification(delta: float, expected: str) -> None:
    assert d015.contact_event_class(delta) == expected


def test_contact_event_aggregation_and_zero_change_baseline_are_exact() -> None:
    events = d015._contact_event_table()
    groups = d015._contact_grouping_table()
    for delta in (-1.0, 0.0, 1.0):
        d015._record_contact_event(events, 0.25, delta)
        d015._record_contact_grouping(groups, 0.25, delta)
    summary = d015._contact_metrics_summary(events, groups)
    exact = summary["exact_event_classes"]
    assert exact["contact_exit"]["transition_count"] == 1
    assert exact["contact_exit"]["learned_mae"] == pytest.approx(1.25)
    assert exact["contact_exit"]["zero_change_baseline_mae"] == pytest.approx(1.0)
    assert exact["contact_unchanged"]["learned_mae"] == pytest.approx(0.25)
    assert exact["contact_unchanged"]["zero_change_baseline_mae"] == pytest.approx(0.0)
    assert exact["contact_entry"]["learned_mae"] == pytest.approx(0.75)
    assert exact["contact_entry"]["zero_change_baseline_mae"] == pytest.approx(1.0)
    grouping = summary["changed_unchanged_groupings"]
    assert grouping["contact_changed"]["transition_count"] == 2
    assert grouping["contact_unchanged"]["transition_count"] == 1


def test_zero_support_is_reported_untested() -> None:
    events = d015._contact_event_table()
    summary = d015._contact_metrics_summary(events, d015._contact_grouping_table())
    entry = summary["exact_event_classes"]["contact_entry"]
    assert entry == {
        "status": "untested",
        "transition_count": 0,
        "learned_mae": None,
        "zero_change_baseline_mae": None,
        "mean_predicted_delta_charging_contact": None,
    }


def test_d015_short_probe_contains_q4_and_action_context_support_at_full_horizon(
) -> None:
    result = d015.run_d015_probe((18350,), horizon=1000)
    run = result["results"][0]
    assert set(run["prediction_metrics"]["windows"]) == {"Q1", "Q2", "Q3", "Q4"}
    assert set(run["contact_event_metrics"]) == {"overall", "q4"}
    assert set(run["action_context_support"]) == {"False", "True"}
    assert len(run["final_weights"]["delta_energy"][Action.WAIT.name]) == 7


def test_d015_shadow_matches_d014_physical_summaries() -> None:
    reference = d014._run_seed(18350, horizon=120)
    shadow = d015._run_seed(18350, horizon=120)
    for key in (
        "transitions",
        "terminated",
        "truncated",
        "termination_reason",
        "energy_termination",
        "thermal_termination",
        "action_counts",
        "mode_occupancy",
        "mode_entry_counts",
        "minimum_normalized_energy",
        "final_normalized_energy",
        "maximum_thermal_state",
        "final_thermal_state",
        "successful_physical_charger_exits",
        "low_energy_seek_entries",
        "successful_charging_contact_reacquisitions",
        "completed_autonomous_regulation_cycles",
    ):
        assert shadow[key] == reference[key]
    assert shadow["evaluator_only"]["passed_to_controller"] is False


def test_adversarial_shadow_predictions_cannot_change_behavior(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline = d015._run_seed(18350, horizon=80)

    def absurd_predict(
        _predictor: d013.D013ActionConsequencePredictor,
        _observation: d011.D011Observation,
        _action: Action,
    ) -> d013.D013Prediction:
        return d013.D013Prediction(1e9, -1e9, 1e9)

    monkeypatch.setattr(d013.D013ActionConsequencePredictor, "predict", absurd_predict)
    adversarial = d015._run_seed(18350, horizon=80)
    for key in (
        "action_counts",
        "mode_occupancy",
        "mode_entry_counts",
        "minimum_normalized_energy",
        "final_normalized_energy",
        "maximum_thermal_state",
        "final_thermal_state",
        "termination_reason",
    ):
        assert adversarial[key] == baseline[key]


def test_d015_does_not_modify_d014_controller_contract() -> None:
    controller = d014.D014Controller(np.random.default_rng(7))
    assert controller.act(observation(1.0, 0.59)) is Action.MOVE_FORWARD
    assert controller.mode is d011.D011Mode.DEPART
