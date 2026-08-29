"""Focused tests for the D-007 matched common-probe diagnostic."""

from __future__ import annotations

import inspect

import pytest

from aweform import d007
from aweform.d002 import D002_CHARGING_HEAT_PER_OFFERED_ENERGY
from aweform.d003 import D003Mode, D003ThermostaticObservation
from aweform.d005 import PredictiveThermalOvershootController
from aweform.env import Action


def test_d007_coefficient_seam_preserves_historical_defaults() -> None:
    assert D002_CHARGING_HEAT_PER_OFFERED_ENERGY == 0.04
    assert d007.D007_MILD_CHARGING_HEAT_PER_OFFERED_ENERGY == 0.04
    assert d007.D007_STRONG_CHARGING_HEAT_PER_OFFERED_ENERGY == 0.06
    assert (
        d007.D007ThermalStationEnv(0.04)._charging_heat_per_offered_energy(1) == 0.04
    )
    assert (
        d007.D007ThermalStationEnv(0.06)._charging_heat_per_offered_energy(1) == 0.06
    )


def test_d007_keeps_historical_d005_and_d006_constants() -> None:
    from aweform import d006
    from aweform.d005 import (
        D005_ALPHA,
        D005_INITIAL_PREDICTED_DEPARTURE_THERMAL_OVERSHOOT,
    )

    assert D005_ALPHA == 0.5
    assert D005_INITIAL_PREDICTED_DEPARTURE_THERMAL_OVERSHOOT == 0.0
    assert d006.D006_BASELINE_CHARGING_HEAT_PER_OFFERED_ENERGY == 0.04
    assert d006.D006_SHIFTED_CHARGING_HEAT_PER_OFFERED_ENERGY == 0.06


def test_d007_paired_histories_are_matched_and_retain_seven_updates() -> None:
    result = d007.run_d007_probe([18141])
    seed_result = result["results"][0]
    assert seed_result["seed"] == 18141
    setup = seed_result["matched_setup"]
    histories = seed_result["histories"]
    assert setup["initial_prediction"] == 0.0
    assert setup["initial_position"] == [0.5, 0.5]
    assert setup["station_center"] == [0.5, 0.5]
    assert setup["controller_type"] == "PredictiveThermalOvershootController"
    assert histories["mild"]["condition"] == "mild"
    assert histories["strong"]["condition"] == "strong"
    assert histories["mild"]["charging_heat_per_offered_energy"] == 0.04
    assert histories["strong"]["charging_heat_per_offered_energy"] == 0.06
    assert histories["mild"]["seeded_heading"] == setup["seeded_heading"]
    assert histories["strong"]["seeded_heading"] == setup["seeded_heading"]
    for history in histories.values():
        assert history["initial_prediction"] == 0.0
        assert history["learning_update_count"] == 7
        assert len(history["learning_updates"]) == 7
        assert history["probe_ready"] is True
        assert history["transitions_to_probe_ready"] > 0


def test_d007_probe_state_and_observation_no_action_acceptance() -> None:
    result = d007.run_d007_probe([18141])
    assert result["target_learning_updates"] == 7
    assert result["common_probe_observation"] == {
        "thermal": 0.56,
        "charging_contact": True,
    }
    assert result["organism_boundary"] == {"reward": 0.0, "info": {}}
    assert result["plastic_state"]["persistent_fields"] == [
        "predicted_departure_thermal_overshoot"
    ]
    assert result["plastic_state"]["dimension"] == 1

    histories = result["results"][0]["histories"]
    for history in histories.values():
        assert history["mode"] == D003Mode.CHARGE.name
        assert history["turns_remaining"] == 0
        assert history["departure_start_thermal"] is None
        assert history["departure_peak_thermal"] is None
        assert history["learned_prediction"] != history["initial_prediction"]
        probe = history["common_probe"]
        assert probe["observation"] == result["common_probe_observation"]
        assert probe["observation"] == {
            "thermal": 0.56,
            "charging_contact": True,
        }
        assert probe["observe_consequence_called"] is False
        assert probe["environment_transitions_between_observation_and_action"] == 0
        assert probe["action"] in {action.name for action in Action}


def test_d007_history_boundary_preserves_reward_info_and_uses_no_condition_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[D003ThermostaticObservation] = []
    consequence_inputs: list[D003ThermostaticObservation] = []
    original_act = PredictiveThermalOvershootController.act
    original_observe = PredictiveThermalOvershootController.observe_consequence

    def recording_act(
        controller: PredictiveThermalOvershootController,
        observation: D003ThermostaticObservation,
    ) -> d007.Action:
        observed.append(observation)
        return original_act(controller, observation)

    def recording_observe(
        controller: PredictiveThermalOvershootController,
        observation: D003ThermostaticObservation,
    ) -> object:
        consequence_inputs.append(observation)
        return original_observe(controller, observation)

    monkeypatch.setattr(
        PredictiveThermalOvershootController, "act", recording_act
    )
    monkeypatch.setattr(
        PredictiveThermalOvershootController, "observe_consequence", recording_observe
    )
    result = d007.run_d007_probe([18141])

    assert observed
    assert all(isinstance(item, D003ThermostaticObservation) for item in observed)
    assert all(
        isinstance(item, D003ThermostaticObservation) for item in consequence_inputs
    )
    assert all(item.thermal <= 1.0 for item in observed)
    assert result["organism_boundary"] == {"reward": 0.0, "info": {}}
    histories = result["results"][0]["histories"]
    assert sum(
        history["controller_observe_consequence_calls"]
        for history in histories.values()
    ) == len(consequence_inputs)


def test_d007_probe_calls_normal_act_once_per_controller_and_no_probe_update(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    act_calls = 0
    observe_calls = 0
    original_act = PredictiveThermalOvershootController.act
    original_observe = PredictiveThermalOvershootController.observe_consequence

    def recording_act(
        controller: PredictiveThermalOvershootController,
        observation: D003ThermostaticObservation,
    ) -> d007.Action:
        nonlocal act_calls
        act_calls += 1
        return original_act(controller, observation)

    def recording_observe(
        controller: PredictiveThermalOvershootController,
        observation: D003ThermostaticObservation,
    ) -> object:
        nonlocal observe_calls
        observe_calls += 1
        return original_observe(controller, observation)

    monkeypatch.setattr(PredictiveThermalOvershootController, "act", recording_act)
    monkeypatch.setattr(
        PredictiveThermalOvershootController, "observe_consequence", recording_observe
    )
    result = d007.run_d007_probe([18141])

    histories = result["results"][0]["histories"]
    history_transitions = sum(
        history["controller_observe_consequence_calls"]
        for history in histories.values()
    )
    assert observe_calls == history_transitions
    assert act_calls == history_transitions + 2


def test_d007_controller_has_only_declared_d005_causal_state() -> None:
    controller = PredictiveThermalOvershootController()
    assert set(vars(controller)) == {
        "_mode",
        "_turns_remaining",
        "_predicted_departure_thermal_overshoot",
        "_departure_start_thermal",
        "_departure_peak_thermal",
    }
    assert "rng" not in inspect.signature(controller.act).parameters
    assert list(inspect.signature(controller.observe_consequence).parameters) == [
        "observation"
    ]


def test_d007_rejects_reserved_seeds() -> None:
    with pytest.raises(ValueError, match="reserved for a formal experiment"):
        d007.run_d007_probe([10001])

    with pytest.raises(ValueError, match="only predeclared development seeds"):
        d007.run_d007_probe([18144])


def test_d007_same_seed_and_condition_reproduces_result() -> None:
    first = d007.run_d007_probe([18142])
    second = d007.run_d007_probe([18142])
    first_histories = first["results"][0]["histories"]
    second_histories = second["results"][0]["histories"]
    for condition in ("mild", "strong"):
        assert first_histories[condition]["learned_prediction"] == second_histories[
            condition
        ]["learned_prediction"]
        assert first_histories[condition]["common_probe"][
            "action"
        ] == second_histories[condition]["common_probe"]["action"]
