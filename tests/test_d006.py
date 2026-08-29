"""Focused tests for D-006 within-lifetime thermal adaptation."""

from dataclasses import fields
from inspect import signature

import pytest

from aweform import d006
from aweform.d002 import (
    D002_CHARGING_HEAT_PER_OFFERED_ENERGY,
    D002ThermalStationEnv,
)
from aweform.d003 import D003Mode, D003ThermostaticObservation
from aweform.d005 import D005LearningUpdate, PredictiveThermalOvershootController
from aweform.env import Action


def observation(thermal: float, contact: bool) -> D003ThermostaticObservation:
    return D003ThermostaticObservation(thermal, contact)


def test_d002_default_thermal_coefficient_remains_historical() -> None:
    environment = D002ThermalStationEnv()
    environment.reset(seed=18141)
    assert (
        environment._charging_heat_per_offered_energy(1)
        == D002_CHARGING_HEAT_PER_OFFERED_ENERGY
    )
    environment.evaluator_set_geometry_and_observe(
        body_position=(0.5, 0.5), station_center=(0.5, 0.5)
    )
    environment.step(Action.WAIT)
    assert environment.last_transition is not None
    assert environment.last_transition.thermal_input == pytest.approx(0.02)


def test_d006_regime_schedule_is_exact_at_boundary() -> None:
    environment = d006.D006ThermalStationEnv()
    assert (
        environment._charging_heat_per_offered_energy(500)
        == d006.D006_BASELINE_CHARGING_HEAT_PER_OFFERED_ENERGY
    )
    assert (
        environment._charging_heat_per_offered_energy(501)
        == d006.D006_SHIFTED_CHARGING_HEAT_PER_OFFERED_ENERGY
    )
    assert environment._charging_heat_per_offered_energy(1000) == 0.06


def test_d006_observation_has_no_regime_or_clock_channel() -> None:
    result = d006.run_d006_probe((18141,), horizon=1)
    run = result["results"][0]
    assert isinstance(run, dict)
    predictive = run["predictive"]
    assert isinstance(predictive, dict)
    assert predictive["controller_input_fields"] == [
        "thermal_interoception",
        "charging_contact",
    ]
    assert [field.name for field in fields(D003ThermostaticObservation)] == [
        "thermal",
        "charging_contact",
    ]
    assert not hasattr(PredictiveThermalOvershootController(), "transition_index")


def test_d006_learning_state_crosses_regime_boundary_without_reset() -> None:
    result = d006.run_d006_probe((18141,), horizon=1000, collect_trace=True)
    run = result["results"][0]
    predictive = run["predictive"]
    assert isinstance(predictive, dict)
    updates = predictive["learning_updates"]
    assert isinstance(updates, list)
    assert any(
        isinstance(update, dict)
        and update["transition_index"] < d006.D006_REGIME_CHANGE_TRANSITION
        for update in updates
    )
    assert predictive["prediction_before_regime_change"] is not None
    assert predictive["prediction_before_regime_change"] > 0.0


def test_d006_plastic_write_seam_reuses_d005_narrow_contract() -> None:
    parameters = list(
        signature(PredictiveThermalOvershootController.observe_consequence).parameters
    )
    assert parameters == ["self", "observation"]
    controller = PredictiveThermalOvershootController()
    assert controller.act(observation(0.60, True)) is Action.MOVE_FORWARD
    update = controller.observe_consequence(observation(0.66, False))
    assert update is not None
    assert update.prediction_after > update.prediction_before


def test_d006_telemetry_is_read_after_plastic_update(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    original_observe = PredictiveThermalOvershootController.observe_consequence

    def observe(
        self: PredictiveThermalOvershootController,
        observation: D003ThermostaticObservation,
    ) -> D005LearningUpdate | None:
        events.append("plastic_update")
        return original_observe(self, observation)

    class RecordingEnvironment(d006.D006ThermalStationEnv):
        def __getattribute__(self, name: str) -> object:
            if name == "last_transition" and events:
                events.append("telemetry_read")
            return super().__getattribute__(name)

    monkeypatch.setattr(
        PredictiveThermalOvershootController,
        "observe_consequence",
        observe,
    )
    monkeypatch.setattr(d006, "D006ThermalStationEnv", RecordingEnvironment)
    d006.run_d006_probe((18141,), horizon=1)

    assert "plastic_update" in events
    first_update = events.index("plastic_update")
    assert any(
        index > first_update
        for index, event in enumerate(events)
        if event == "telemetry_read"
    )


def test_d006_post_change_consequence_changes_prediction_and_later_charge_reads_it(
) -> None:
    result = d006.run_d006_probe((18141,), horizon=1000, collect_trace=True)
    run = result["results"][0]
    predictive = run["predictive"]
    assert isinstance(predictive, dict)
    trace = predictive["trace"]
    assert isinstance(trace, tuple)
    post_change_updates = [
        entry
        for entry in trace
        if entry.transition_index >= d006.D006_REGIME_CHANGE_TRANSITION
        and entry.update_occurred
    ]
    assert post_change_updates
    assert any(
        entry.prediction_after_consequence != entry.prediction_used
        for entry in post_change_updates
    )
    assert any(
        entry.controller_mode is D003Mode.CHARGE and entry.prediction_used > 0.0
        for entry in trace
    )


def test_d006_comparator_is_matched_and_has_no_learning() -> None:
    result = d006.run_d006_probe((18141,), horizon=1000)
    run = result["results"][0]
    assert isinstance(run, dict)
    comparator = run["comparator"]
    assert isinstance(comparator, dict)
    assert comparator["condition"] == "D-003 thermostatic comparator"
    assert comparator["learning_update_count"] == 0
    assert comparator["final_prediction"] is None
    assert comparator["seeded_heading"] == run["predictive"]["seeded_heading"]


def test_d006_boundary_keeps_reward_zero_and_info_empty() -> None:
    result = d006.run_d006_probe((18141,), horizon=2)
    assert result["organism_boundary"] == {"reward": 0.0, "info": {}}


def test_d006_reserved_seed_guard_remains_effective() -> None:
    with pytest.raises(ValueError):
        d006.run_d006_probe((50001,), horizon=1)


def test_d006_replays_identically_for_same_seed_and_configuration() -> None:
    first = d006.run_d006_probe((18141, 18142, 18143), horizon=1000)
    second = d006.run_d006_probe((18141, 18142, 18143), horizon=1000)
    assert first == second
