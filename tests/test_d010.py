"""Focused tests for the D-010 exact-key census and provenance."""

from __future__ import annotations

import inspect

import numpy as np
import pytest

from aweform import d008, d009, d010
from aweform.d003 import D003ThermostaticObservation
from aweform.env import Action


def observation(thermal: float, contact: bool) -> D003ThermostaticObservation:
    return D003ThermostaticObservation(thermal, contact)


def key_record(
    census: d010.ExactConsequenceCensus,
) -> dict[str, object]:
    records = census.as_dict()["keys"]
    assert isinstance(records, list)
    assert len(records) == 1
    record = records[0]
    assert isinstance(record, dict)
    return record


def test_identical_consequence_is_repeated_but_not_aliased() -> None:
    census = d010.ExactConsequenceCensus()
    current = observation(float(np.float32(0.59)), True)
    consequence = observation(float(np.float32(0.60)), True)
    census.add(current, Action.WAIT, consequence)
    census.add(current, Action.WAIT, consequence)

    record = key_record(census)
    assert record["sample_count"] == 2
    assert record["repeated"] is True
    assert record["aliasing_tested"] is True
    assert record["aliased"] is False
    assert record["distinct_next_visible_outcome_count"] == 1


def test_two_consequences_for_one_key_are_aliased() -> None:
    census = d010.ExactConsequenceCensus()
    current = observation(float(np.float32(0.59)), True)
    census.add(
        current,
        Action.MOVE_FORWARD,
        observation(float(np.float32(0.60)), True),
    )
    census.add(
        current,
        Action.MOVE_FORWARD,
        observation(float(np.float32(0.60)), False),
    )

    record = key_record(census)
    assert record["sample_count"] == 2
    assert record["repeated"] is True
    assert record["aliased"] is True
    assert record["distinct_next_visible_outcome_count"] == 2
    outcomes = record["next_visible_outcomes"]
    assert isinstance(outcomes, list)
    assert [outcome["count"] for outcome in outcomes] == [1, 1]


def test_same_visible_state_with_different_actions_has_separate_keys() -> None:
    census = d010.ExactConsequenceCensus()
    current = observation(0.59, True)
    next_observation = observation(0.60, True)
    census.add(current, Action.WAIT, next_observation)
    census.add(current, Action.MOVE_FORWARD, next_observation)

    result = census.as_dict()["keys"]
    assert isinstance(result, list)
    assert len(result) == 2
    assert {record["action"] for record in result} == {"WAIT", "MOVE_FORWARD"}
    summary = census.as_dict()["summary"]
    assert isinstance(summary, dict)
    per_action = summary["per_action"]
    assert isinstance(per_action, dict)
    assert per_action["WAIT"]["transition_count"] == 1
    assert per_action["MOVE_FORWARD"]["transition_count"] == 1


def test_distinct_float32_visible_thermal_values_have_separate_keys() -> None:
    census = d010.ExactConsequenceCensus()
    first = float(np.float32(0.59))
    second = float(np.nextafter(np.float32(0.59), np.float32(1.0)))
    assert first != second
    census.add(observation(first, True), Action.WAIT, observation(0.60, True))
    census.add(observation(second, True), Action.WAIT, observation(0.60, True))

    summary = census.as_dict()["summary"]
    assert isinstance(summary, dict)
    assert summary["total_unique_exact_keys"] == 2


def test_singleton_is_untested_not_evidence_of_stability() -> None:
    census = d010.ExactConsequenceCensus()
    census.add(observation(0.42, False), Action.WAIT, observation(0.41, False))

    record = key_record(census)
    assert record["sample_count"] == 1
    assert record["repeated"] is False
    assert record["aliasing_tested"] is False
    assert record["aliased"] is False
    summary = census.as_dict()["summary"]
    assert isinstance(summary, dict)
    assert summary["repeated_exact_keys"] == 0
    assert summary["singleton_exact_keys"] == 1


def test_pooled_census_detects_cross_lifetime_aliasing() -> None:
    first_lifetime = d010.ExactConsequenceCensus()
    second_lifetime = d010.ExactConsequenceCensus()
    pooled = d010.ExactConsequenceCensus()
    current = observation(float(np.float32(0.59)), True)
    first_outcome = observation(float(np.float32(0.60)), True)
    second_outcome = observation(float(np.float32(0.60)), False)

    first_lifetime.add(current, Action.MOVE_FORWARD, first_outcome)
    second_lifetime.add(current, Action.MOVE_FORWARD, second_outcome)
    pooled.add(current, Action.MOVE_FORWARD, first_outcome)
    pooled.add(current, Action.MOVE_FORWARD, second_outcome)

    assert key_record(first_lifetime)["aliasing_tested"] is False
    assert key_record(second_lifetime)["aliasing_tested"] is False
    pooled_record = key_record(pooled)
    assert pooled_record["sample_count"] == 2
    assert pooled_record["aliased"] is True


def test_d010_uses_d009_sampler_and_d008_shadow_only() -> None:
    assert d010.D009SamplingController is d009.D009SamplingController
    assert d010.D008ActionConsequencePredictor is d008.D008ActionConsequencePredictor
    result = d010.run_d010_probe((18141,), horizon=10)
    assert result["condition"] == "overlap_sampler"
    run = result["results"][0]
    assert isinstance(run, dict)
    assert run["condition"] == "overlap_sampler"
    assert run["shadow_predictor"]["causal_effect_on_action_choice"] is False
    assert run["sampling"]["starting_phase"] == "EARLY"


def test_adversarial_shadow_predictions_do_not_change_sampler_actions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline = d010.run_d010_probe((18141,), horizon=50)

    def adversarial_predict(
        self: d008.D008ActionConsequencePredictor,
        current: D003ThermostaticObservation,
        action: Action,
    ) -> d008.D008Prediction:
        del self, current, action
        return d008.D008Prediction(1e9, -1e9)

    monkeypatch.setattr(
        d010.D008ActionConsequencePredictor, "predict", adversarial_predict
    )
    adversarial = d010.run_d010_probe((18141,), horizon=50)
    assert adversarial["results"][0]["action_counts"] == baseline["results"][0][
        "action_counts"
    ]


def test_census_is_not_in_learning_interfaces() -> None:
    predictor = d010.D008ActionConsequencePredictor()
    assert list(inspect.signature(predictor.predict).parameters) == [
        "observation",
        "action",
    ]
    assert list(inspect.signature(predictor.observe_transition).parameters) == [
        "observation",
        "action",
        "next_observation",
    ]
    assert "ExactConsequenceCensus" not in str(
        inspect.signature(d008.D008ActionConsequencePredictor.predict).return_annotation
    )


def test_reward_info_and_seed_boundaries_are_preserved() -> None:
    result = d010.run_d010_probe((18141,), horizon=2)
    assert result["organism_boundary"] == {"reward": 0.0, "info": {}}
    with pytest.raises(ValueError, match="reserved for a formal experiment"):
        d010.run_d010_probe((50001,), horizon=1)
    with pytest.raises(ValueError, match="only predeclared development seeds"):
        d010.run_d010_probe((42,), horizon=1)
