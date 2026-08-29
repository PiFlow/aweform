"""Focused tests for D-008 shadow action-conditioned prediction."""

from __future__ import annotations

import inspect
import json
from dataclasses import fields

import pytest

from aweform import d008
from aweform.d002 import D002ThermalStationEnv
from aweform.d003 import (
    D003ThermostaticObservation,
    ThermostaticShuttleController,
    run_d003_probe,
)
from aweform.env import Action
from aweform.exp003 import EXP003_CHARGING_RADIUS


def observation(thermal: float, contact: bool) -> D003ThermostaticObservation:
    return D003ThermostaticObservation(thermal, contact)


def flatten(snapshot: dict[str, dict[str, list[float]]]) -> list[float]:
    return [
        weight
        for output in ("delta_thermal", "delta_charging_contact")
        for action in Action
        for weight in snapshot[output][action.name]
    ]


def test_d008_uses_unchanged_d003_controller_and_station_radius() -> None:
    assert d008.ThermostaticShuttleController is ThermostaticShuttleController
    assert EXP003_CHARGING_RADIUS == 0.10
    assert D002ThermalStationEnv().config.charging_radius == 0.10


def test_predictor_interface_is_narrow_and_has_exact_plastic_dimension() -> None:
    predictor = d008.D008ActionConsequencePredictor()
    assert list(inspect.signature(predictor.predict).parameters) == [
        "observation",
        "action",
    ]
    assert list(inspect.signature(predictor.observe_transition).parameters) == [
        "observation",
        "action",
        "next_observation",
    ]
    assert [field.name for field in fields(D003ThermostaticObservation)] == [
        "thermal",
        "charging_contact",
    ]
    assert len(Action) == 4
    assert d008.D008_PLASTIC_STATE_DIMENSION == 24
    assert len(predictor.weights) == 24
    assert predictor.weights == (0.0,) * 24
    assert not hasattr(predictor, "rng")


def test_initial_prediction_is_zero_and_only_selected_action_is_read() -> None:
    predictor = d008.D008ActionConsequencePredictor()
    assert predictor.predict(
        observation(0.4, True), Action.WAIT
    ) == d008.D008Prediction(0.0, 0.0)
    predictor.observe_transition(
        observation(0.4, True), Action.WAIT, observation(0.6, False)
    )
    wait_prediction = predictor.predict(observation(0.4, True), Action.WAIT)
    turn_prediction = predictor.predict(observation(0.4, True), Action.TURN_LEFT)
    assert wait_prediction != d008.D008Prediction(0.0, 0.0)
    assert turn_prediction == d008.D008Prediction(0.0, 0.0)


def test_normalized_lms_updates_only_six_executed_action_weights() -> None:
    predictor = d008.D008ActionConsequencePredictor()
    current = observation(0.4, True)
    next_observation = observation(0.6, False)
    update = predictor.observe_transition(current, Action.TURN_LEFT, next_observation)
    x = (1.0, 0.4, 1.0)
    normalizer = sum(value * value for value in x)
    expected_thermal = [0.5 * 0.2 * value / normalizer for value in x]
    expected_contact = [0.5 * -1.0 * value / normalizer for value in x]
    snapshot = predictor.weight_snapshot()
    assert update.observed_delta_thermal == pytest.approx(0.2)
    assert update.observed_delta_contact == -1.0
    assert update.normalizer == pytest.approx(normalizer)
    assert snapshot["delta_thermal"][Action.TURN_LEFT.name] == pytest.approx(
        expected_thermal
    )
    assert snapshot["delta_charging_contact"][Action.TURN_LEFT.name] == pytest.approx(
        expected_contact
    )
    for action in Action:
        if action is not Action.TURN_LEFT:
            assert snapshot["delta_thermal"][action.name] == [0.0, 0.0, 0.0]
            assert snapshot["delta_charging_contact"][action.name] == [0.0, 0.0, 0.0]


def test_plastic_update_uses_only_visible_target_differences() -> None:
    predictor = d008.D008ActionConsequencePredictor()
    with pytest.raises(ValueError):
        predictor.observe_transition(current := observation(0.2, False), Action.WAIT, 0)  # type: ignore[arg-type]
    update = predictor.observe_transition(current, Action.WAIT, observation(0.1, True))
    assert update.observed_delta_thermal == pytest.approx(-0.1)
    assert update.observed_delta_contact == 1.0


def test_reset_is_deliberate_and_checkpoint_snapshot_does_not_reset() -> None:
    predictor = d008.D008ActionConsequencePredictor()
    predictor.observe_transition(
        observation(0.4, False), Action.WAIT, observation(0.5, False)
    )
    before = predictor.weights
    snapshot = predictor.weight_snapshot()
    assert before != (0.0,) * 24
    assert flatten(snapshot) == pytest.approx(list(before))
    assert predictor.weights == before
    predictor.reset()
    assert predictor.weights == (0.0,) * 24


def test_probe_preserves_boundary_support_checkpoints_and_no_full_trace(
    tmp_path,
) -> None:
    first = d008.run_d008_probe((18141,), horizon=500)
    second = d008.run_d008_probe((18141,), horizon=500)
    assert first == second
    assert first["organism_boundary"] == {"reward": 0.0, "info": {}}
    run = first["results"][0]
    assert isinstance(run, dict)
    assert run["transitions"] == 500
    assert run["truncated"] is True
    assert run["terminated"] is False
    assert set(run["action_counts"]) == {action.name for action in Action}
    contexts = run["contact_action_contexts"]
    assert contexts["False"][Action.TURN_RIGHT.name]["count"] == 0
    assert contexts["True"][Action.TURN_RIGHT.name]["count"] == 0
    assert set(run["checkpoints"]) == {"250", "500"}
    assert len(flatten(run["final_weights"])) == 24
    assert set(run["prediction_metrics"]["windows"]) == {"Q1", "Q2"}

    output = tmp_path / "d008.json"
    args = ["--seeds", "18141", "--horizon", "2", "--output", str(output)]
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr("sys.argv", ["d008"] + args)
    try:
        d008.main()
    finally:
        monkeypatch.undo()
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert "trace" not in json.dumps(payload)


def test_probe_rejects_reserved_and_non_predeclared_seeds() -> None:
    with pytest.raises(ValueError, match="reserved for a formal experiment"):
        d008.run_d008_probe((50001,), horizon=1)
    with pytest.raises(ValueError, match="only predeclared development seeds"):
        d008.run_d008_probe((42,), horizon=1)


def test_shadow_predictor_does_not_change_d003_actions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_update = d008.D008ActionConsequencePredictor.observe_transition

    def adversarial_predict(
        self: d008.D008ActionConsequencePredictor,
        observation: D003ThermostaticObservation,
        action: Action,
    ) -> d008.D008Prediction:
        del observation, action
        return d008.D008Prediction(1e9, -1e9)

    def adversarial_update(
        self: d008.D008ActionConsequencePredictor,
        observation: D003ThermostaticObservation,
        action: Action,
        next_observation: D003ThermostaticObservation,
    ) -> d008.D008LearningUpdate:
        return original_update(self, observation, action, next_observation)

    baseline = d008.run_d008_probe((18141,), horizon=50)
    monkeypatch.setattr(
        d008.D008ActionConsequencePredictor, "predict", adversarial_predict
    )
    monkeypatch.setattr(
        d008.D008ActionConsequencePredictor,
        "observe_transition",
        adversarial_update,
    )
    shadow = d008.run_d008_probe((18141,), horizon=50)
    assert (
        shadow["results"][0]["action_counts"]
        == baseline["results"][0]["action_counts"]
    )


def test_d008_action_trajectory_matches_d003_without_shadow_influence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    d003_result = run_d003_probe((18141,), horizon=50, collect_trace=True)
    d003_trace = d003_result["results"][0]["trace"]
    assert isinstance(d003_trace, tuple)
    observed_actions: list[Action] = []
    original_step = D002ThermalStationEnv.step

    def recording_step(
        environment: D002ThermalStationEnv, action: int
    ) -> tuple[object, float, bool, bool, dict[str, object]]:
        observed_actions.append(Action(int(action)))
        return original_step(environment, action)

    monkeypatch.setattr(D002ThermalStationEnv, "step", recording_step)
    d008.run_d008_probe((18141,), horizon=50)
    assert observed_actions == [entry.action for entry in d003_trace]


def test_transition_order_scores_pre_update_and_reads_telemetry_last(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    original_predict = d008.D008ActionConsequencePredictor.predict
    original_update = d008.D008ActionConsequencePredictor.observe_transition
    original_step = D002ThermalStationEnv.step

    def recording_predict(
        predictor: d008.D008ActionConsequencePredictor,
        observation: D003ThermostaticObservation,
        action: Action,
    ) -> d008.D008Prediction:
        events.append("predict")
        return original_predict(predictor, observation, action)

    def recording_update(
        predictor: d008.D008ActionConsequencePredictor,
        observation: D003ThermostaticObservation,
        action: Action,
        next_observation: D003ThermostaticObservation,
    ) -> d008.D008LearningUpdate:
        events.append("update")
        return original_update(predictor, observation, action, next_observation)

    def recording_step(
        environment: D002ThermalStationEnv, action: int
    ) -> tuple[object, float, bool, bool, dict[str, object]]:
        events.append("step")
        return original_step(environment, action)

    class RecordingEnvironment(D002ThermalStationEnv):
        def __getattribute__(self, name: str) -> object:
            if name == "last_transition" and "update" in events:
                events.append("telemetry_read")
            return super().__getattribute__(name)

    monkeypatch.setattr(d008, "D002ThermalStationEnv", RecordingEnvironment)
    monkeypatch.setattr(D002ThermalStationEnv, "step", recording_step)
    monkeypatch.setattr(
        d008.D008ActionConsequencePredictor, "predict", recording_predict
    )
    monkeypatch.setattr(
        d008.D008ActionConsequencePredictor,
        "observe_transition",
        recording_update,
    )
    d008.run_d008_probe((18141,), horizon=1)
    assert events.index("predict") < events.index("step")
    assert events.index("step") < events.index("update")
    assert events.index("update") < events.index("telemetry_read")
