"""Focused tests for the D-027 shadow sensorimotor learner."""

from __future__ import annotations

import inspect

import pytest

from aweform import d027
from aweform.env import Action
from aweform.exp003 import BeaconObservation
from aweform.exp003_seed_policy import validate_exp003_development_seeds


def observation(
    *,
    energy: float = 0.25,
    left: float = 0.1,
    forward: float = 0.8,
    right: float = 0.2,
    contact: bool = False,
    thermal: float = 0.2875,
) -> d027.D027Observation:
    return d027.D027Observation(
        energy=energy,
        beacon=BeaconObservation(left, forward, right, contact),
        thermal=thermal,
    )


def test_d027_freeze_and_seed_guard() -> None:
    assert d027.D027_HORIZON == 70_000
    assert d027.D027_LEARNING_RATE == 0.5
    assert d027.D027_DEFAULT_DEVELOPMENT_SEEDS == tuple(range(18388, 18408))
    assert d027.D027_PLASTIC_STATE_DIMENSION == 168
    assert validate_exp003_development_seeds(d027.D027_DEFAULT_DEVELOPMENT_SEEDS) == (
        d027.D027_DEFAULT_DEVELOPMENT_SEEDS
    )
    assert (
        d027._validate_d027_development_seeds(d027.D027_DEFAULT_DEVELOPMENT_SEEDS)
        == d027.D027_DEFAULT_DEVELOPMENT_SEEDS
    )
    with pytest.raises(ValueError, match="requires exactly"):
        d027._validate_d027_development_seeds((18388,))
    with pytest.raises(ValueError, match="reserved for a formal experiment"):
        d027._validate_d027_development_seeds((50001, 50002, 50003))


def test_predictor_has_exactly_168_zero_weights_and_no_extra_state() -> None:
    predictor = d027.D027ActionConsequencePredictor()
    assert len(predictor.weights) == 168
    assert predictor.weights == (0.0,) * 168
    assert predictor.__slots__ == ("_weights",)
    assert not hasattr(predictor, "rng")
    assert not hasattr(predictor, "history")
    assert not hasattr(predictor, "buffer")
    assert not hasattr(predictor, "optimizer_state")
    assert d027.D027ActionConsequencePredictor._features(observation()) == (
        1.0,
        0.25,
        0.1,
        0.8,
        0.2,
        0.0,
        0.2875,
    )


def test_normalized_lms_updates_only_executed_action_and_all_six_outputs() -> None:
    predictor = d027.D027ActionConsequencePredictor()
    current = observation()
    next_value = observation(
        energy=0.3,
        left=0.2,
        forward=0.7,
        right=0.25,
        contact=True,
        thermal=0.4,
    )
    update = predictor.observe_transition(current, Action.TURN_LEFT, next_value)
    assert update.prediction == (0.0,) * 6
    assert update.observed_delta == pytest.approx((0.05, 0.1, -0.1, 0.05, 1.0, 0.1125))
    assert update.normalizer == pytest.approx(
        1.0 + 0.25**2 + 0.1**2 + 0.8**2 + 0.2**2 + 0.2875**2
    )
    snapshot = predictor.weight_snapshot()
    for output in d027.D027_OUTPUTS:
        assert snapshot[output][Action.WAIT.name] == [0.0] * 7
        assert snapshot[output][Action.TURN_RIGHT.name] == [0.0] * 7
        assert snapshot[output][Action.MOVE_FORWARD.name] == [0.0] * 7
        assert any(value != 0.0 for value in snapshot[output][Action.TURN_LEFT.name])


def test_prediction_is_pre_update_and_features_are_typed() -> None:
    predictor = d027.D027ActionConsequencePredictor()
    current = observation()
    before = predictor.predict(current, Action.WAIT)
    update = predictor.observe_transition(current, Action.WAIT, observation(energy=0.3))
    assert update.prediction == before.values
    assert predictor.predict(current, Action.WAIT).values != before.values
    with pytest.raises(ValueError, match="D026Observation"):
        predictor.predict(0, Action.WAIT)  # type: ignore[arg-type]


def test_boundary_classifier_uses_declared_tolerance_and_rejects_overshoot() -> None:
    assert d027._classify_forward_displacement(0.05) == "FULL_NOMINAL_FORWARD"
    assert d027._classify_forward_displacement(0.05 + 0.5e-12) == "FULL_NOMINAL_FORWARD"
    assert (
        d027._classify_forward_displacement(0.05 - 2e-12) == "BOUNDARY_CLIPPED_FORWARD"
    )
    assert d027._classify_forward_displacement(0.0) == "BOUNDARY_CLIPPED_FORWARD"
    with pytest.raises(RuntimeError, match="exceeded nominal"):
        d027._classify_forward_displacement(0.05 + 2e-12)


def test_short_replay_is_deterministic_and_exactly_isolated() -> None:
    first = d027._run_d027_seed(18388, horizon=200)
    second = d027._run_d027_seed(18388, horizon=200)
    assert first == second
    isolation = first["shadow_isolation"]
    assert isinstance(isolation, dict)
    assert isolation["trajectory_exact_equal"] is True
    assert isolation["behavioral_summary_exact_equal"] is True
    assert first["transitions"] == 200
    assert len(first["final_weights"][d027.D027_OUTPUTS[0]][Action.WAIT.name]) == 7  # type: ignore[index]


def test_extreme_shadow_predictions_cannot_change_trajectory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline = d027._run_d027_seed(18388, horizon=80)

    def extreme_predict(
        _self: d027.D027ActionConsequencePredictor,
        _observation: d027.D027Observation,
        _action: Action,
    ) -> d027.D027Prediction:
        return d027.D027Prediction((1e300, -1e300, 1e300, -1e300, 1e300, -1e300))

    monkeypatch.setattr(d027.D027ActionConsequencePredictor, "predict", extreme_predict)
    adversarial = d027._run_d027_seed(18388, horizon=80)
    assert adversarial["trajectory_digest"] == baseline["trajectory_digest"]
    assert adversarial["shadow_isolation"]["trajectory_exact_equal"] is True  # type: ignore[index]


def test_runner_does_not_put_evaluator_state_in_learner_or_controller() -> None:
    source = inspect.getsource(d027.D027ActionConsequencePredictor)
    assert "position" not in source
    assert "heading" not in source
    assert "displacement" not in source
    assert "rng" not in source
    assert "unexecuted" not in source
