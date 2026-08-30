"""Focused tests for D-009 support acquisition and provenance."""

from __future__ import annotations

import inspect

import numpy as np
import pytest

from aweform import d008, d009
from aweform.d002 import D002ThermalStationEnv
from aweform.d003 import (
    COOL_RETURN_THRESHOLD,
    D003Mode,
    D003ThermostaticObservation,
    run_d003_probe,
)
from aweform.env import Action
from aweform.exp003 import EXP003_CHARGING_RADIUS


def observation(thermal: float, contact: bool) -> D003ThermostaticObservation:
    return D003ThermostaticObservation(thermal, contact)


def test_reuses_d008_predictor_and_preserves_ecology() -> None:
    assert d009.D008ActionConsequencePredictor is d008.D008ActionConsequencePredictor
    assert EXP003_CHARGING_RADIUS == 0.10
    assert D002ThermalStationEnv().config.charging_radius == 0.10
    assert d009.D009_NOMINAL_OVERLAP_THERMAL == 0.59
    assert d009.D009_OVERLAP_THERMAL == float(np.float32(0.59))
    assert d009.D009_EARLY_DEPART_THRESHOLD == d009.D009_OVERLAP_THERMAL
    assert d009.D009_LATE_DEPART_THRESHOLD == float(np.float32(0.61))


def test_float32_threshold_contrast_is_synthetic_and_executes_no_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_environment(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("synthetic threshold test must not create an environment")

    monkeypatch.setattr(d009, "D002ThermalStationEnv", fail_environment)
    probe = observation(float(np.float32(0.59)), True)
    controller = d009.D009SamplingController()
    assert controller.act(probe) is Action.MOVE_FORWARD
    controller.reset()
    controller.sampling_phase = d009.D009SamplingPhase.LATE
    assert controller.act(probe) is Action.WAIT
    assert d009.D009_OVERLAP_THERMAL == float(np.float32(0.59))


def test_sampling_phase_starts_early_and_toggles_only_on_return_completion() -> None:
    controller = d009.D009SamplingController()
    assert controller.sampling_phase is d009.D009SamplingPhase.EARLY
    assert controller.act(observation(0.2, True)) is Action.WAIT
    assert controller.sampling_phase is d009.D009SamplingPhase.EARLY
    controller.mode = D003Mode.RETURN
    assert controller.act(observation(0.2, False)) is Action.MOVE_FORWARD
    assert controller.sampling_phase is d009.D009SamplingPhase.EARLY
    assert controller.act(observation(0.2, True)) is Action.WAIT
    assert controller.mode is D003Mode.CHARGE
    assert controller.sampling_phase is d009.D009SamplingPhase.LATE


def test_d003_return_completion_semantics_and_no_forced_turn_right() -> None:
    controller = d009.D009SamplingController()
    controller.mode = D003Mode.RETURN
    assert controller.act(observation(0.2, True)) is Action.WAIT
    result = d009.run_d009_probe((18141,), horizon=50)
    run = result["results"][0]["overlap_sampler"]
    assert isinstance(run, dict)
    assert run["action_counts"][Action.TURN_RIGHT.name] == 0
    assert COOL_RETURN_THRESHOLD == 0.30


def test_predictor_interface_remains_narrow_and_phase_is_not_an_input() -> None:
    predictor = d009.D008ActionConsequencePredictor()
    assert list(inspect.signature(predictor.predict).parameters) == [
        "observation",
        "action",
    ]
    assert list(inspect.signature(predictor.observe_transition).parameters) == [
        "observation",
        "action",
        "next_observation",
    ]
    assert len(predictor.weights) == 24
    assert predictor.weights == (0.0,) * 24
    assert not hasattr(predictor, "rng")
    assert "sampling_phase" not in inspect.signature(
        d009.D008ActionConsequencePredictor.predict
    ).parameters


def test_synthetic_overlap_support_counts_and_detects_variability() -> None:
    stats = d009._OverlapStats()
    current = observation(d009.D009_OVERLAP_THERMAL, True)
    stats.add(current, observation(d009.D009_OVERLAP_THERMAL, True))
    stats.add(current, observation(d009.D009_OVERLAP_THERMAL, False))
    summary = stats.as_dict()
    assert summary["sample_count"] == 2
    assert summary["current_thermal"] == d009.D009_OVERLAP_THERMAL
    assert summary["contact_delta_counts"] == {"-1": 1, "0": 1, "+1": 0}
    assert summary["same_visible_state_action_outcome_variability"] is True
    outcomes = summary["distinct_next_visible_outcomes"]
    assert isinstance(outcomes, list)
    assert len(outcomes) == 2


def test_pre_update_prediction_is_what_metrics_score() -> None:
    sums = d009._empty_metric_sums()
    prediction = d008.D008Prediction(0.2, -0.5)
    update = d008.D008LearningUpdate(
        action=Action.WAIT,
        predicted_delta_thermal=999.0,
        predicted_delta_contact=999.0,
        observed_delta_thermal=0.1,
        observed_delta_contact=0.0,
        thermal_error=-998.9,
        contact_error=-999.0,
        normalizer=1.0,
    )
    d009._record_metrics(sums, prediction, update)
    metrics = d009._metric_summary(sums)
    assert metrics["learned_model_thermal_mae"] == pytest.approx(0.1)
    assert metrics["zero_change_baseline_thermal_mae"] == pytest.approx(0.1)
    assert metrics["learned_model_contact_delta_mae"] == pytest.approx(0.5)


def test_baseline_preserves_d003_action_structure_and_predictor_is_shadow_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    d003 = run_d003_probe((18141,), horizon=50)
    baseline = d009.run_d009_probe((18141,), horizon=50)
    d003_run = d003["results"][0]
    baseline_run = baseline["results"][0]["baseline"]
    assert isinstance(d003_run, dict)
    assert isinstance(baseline_run, dict)
    assert baseline_run["action_counts"] == d003_run["action_counts"]

    original_predict = d009.D008ActionConsequencePredictor.predict

    def adversarial_predict(
        self: d008.D008ActionConsequencePredictor,
        current: D003ThermostaticObservation,
        action: Action,
    ) -> d008.D008Prediction:
        del current, action
        return d008.D008Prediction(1e9, -1e9)

    monkeypatch.setattr(
        d009.D008ActionConsequencePredictor, "predict", adversarial_predict
    )
    adversarial = d009.run_d009_probe((18141,), horizon=50)
    assert (
        adversarial["results"][0]["overlap_sampler"]["action_counts"]
        == baseline["results"][0]["overlap_sampler"]["action_counts"]
    )
    monkeypatch.setattr(
        d009.D008ActionConsequencePredictor, "predict", original_predict
    )


def test_transition_order_and_final_query_do_not_step_or_learn_after_lifetime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    original_predict = d009.D008ActionConsequencePredictor.predict
    original_update = d009.D008ActionConsequencePredictor.observe_transition
    original_step = D002ThermalStationEnv.step

    def predict(
        predictor: d008.D008ActionConsequencePredictor,
        current: D003ThermostaticObservation,
        action: Action,
    ) -> d008.D008Prediction:
        events.append("predict")
        return original_predict(predictor, current, action)

    def update(
        predictor: d008.D008ActionConsequencePredictor,
        current: D003ThermostaticObservation,
        action: Action,
        next_observation: D003ThermostaticObservation,
    ) -> d008.D008LearningUpdate:
        events.append("update")
        return original_update(predictor, current, action, next_observation)

    def step(
        environment: D002ThermalStationEnv, action: int
    ) -> tuple[object, float, bool, bool, dict[str, object]]:
        events.append("step")
        return original_step(environment, action)

    class RecordingEnvironment(D002ThermalStationEnv):
        def __getattribute__(self, name: str) -> object:
            if name == "last_transition" and "update" in events:
                events.append("telemetry_read")
            return super().__getattribute__(name)

    monkeypatch.setattr(d009, "D002ThermalStationEnv", RecordingEnvironment)
    monkeypatch.setattr(D002ThermalStationEnv, "step", step)
    monkeypatch.setattr(d009.D008ActionConsequencePredictor, "predict", predict)
    monkeypatch.setattr(
        d009.D008ActionConsequencePredictor, "observe_transition", update
    )
    result = d009.run_d009_probe((18141,), horizon=1)
    assert (
        events.index("predict")
        < events.index("step")
        < events.index("update")
        < events.index("telemetry_read")
    )
    assert events.count("step") == 2
    assert events.count("update") == 2
    # D-008's observe_transition recomputes its pre-update prediction; the
    # two final queries add one prediction per queried action per condition.
    assert events.count("predict") == 8
    for condition in ("baseline", "overlap_sampler"):
        query = result["results"][0][condition]["final_common_model_query"]
        assert isinstance(query, dict)
        assert set(query["actions"]) == {Action.WAIT.name, Action.MOVE_FORWARD.name}


def test_info_reward_seeds_and_compact_result_contract() -> None:
    result = d009.run_d009_probe((18141,), horizon=2)
    assert result["organism_boundary"] == {"reward": 0.0, "info": {}}
    with pytest.raises(ValueError, match="reserved for a formal experiment"):
        d009.run_d009_probe((50001,), horizon=1)
    with pytest.raises(ValueError, match="only predeclared development seeds"):
        d009.run_d009_probe((42,), horizon=1)
    assert "trace" not in str(result)
    run = result["results"][0]["overlap_sampler"]
    assert isinstance(run, dict)
    assert run["sampling"]["starting_phase"] == "EARLY"
    assert run["checkpoints"] == {}
