"""Focused tests for D-005 predictive thermal-overshoot adaptation."""

from dataclasses import fields
from inspect import signature

import numpy as np
import pytest

from aweform.d003 import D003Mode, D003ThermostaticObservation
from aweform.d005 import (
    D005_ALPHA,
    D005_INITIAL_PREDICTED_DEPARTURE_THERMAL_OVERSHOOT,
    D005LearningUpdate,
    PredictiveThermalOvershootController,
    run_d005_probe,
)
from aweform.env import Action


def observation(thermal: float, contact: bool) -> D003ThermostaticObservation:
    return D003ThermostaticObservation(thermal, contact)


def complete_return_to_charge(
    controller: PredictiveThermalOvershootController,
) -> None:
    assert controller.act(observation(0.2, False)) is Action.WAIT
    assert controller.mode is D003Mode.COOL
    assert controller.act(observation(0.30, False)) is Action.TURN_LEFT
    for _ in range(3):
        assert controller.act(observation(0.2, False)) is Action.TURN_LEFT
    assert controller.mode is D003Mode.RETURN
    assert controller.act(observation(0.2, False)) is Action.MOVE_FORWARD
    assert controller.act(observation(0.2, True)) is Action.WAIT
    assert controller.mode is D003Mode.CHARGE


def test_initial_prediction_is_exactly_zero_and_read_only() -> None:
    controller = PredictiveThermalOvershootController()
    assert (
        controller.predicted_departure_thermal_overshoot
        == D005_INITIAL_PREDICTED_DEPARTURE_THERMAL_OVERSHOOT
        == 0.0
    )
    with pytest.raises(AttributeError):
        controller.predicted_departure_thermal_overshoot = 0.2  # type: ignore[misc]


def test_valid_departure_experience_uses_declared_update_equation() -> None:
    controller = PredictiveThermalOvershootController()
    assert controller.act(observation(0.60, True)) is Action.MOVE_FORWARD
    update = controller.observe_consequence(observation(0.66, False))

    assert isinstance(update, D005LearningUpdate)
    assert update.departure_start_thermal == pytest.approx(0.60)
    assert update.observed_departure_thermal_overshoot == pytest.approx(0.06)
    assert update.prediction_before == 0.0
    assert update.prediction_after == pytest.approx(
        0.0 + D005_ALPHA * (0.06 - 0.0)
    )
    assert controller.predicted_departure_thermal_overshoot == pytest.approx(0.03)


def test_plastic_update_has_only_narrow_observation_input() -> None:
    parameters = list(signature(
        PredictiveThermalOvershootController.observe_consequence
    ).parameters)
    assert parameters == ["self", "observation"]
    assert [field.name for field in fields(D005LearningUpdate)] == [
        "departure_start_thermal",
        "observed_departure_thermal_overshoot",
        "prediction_before",
        "prediction_after",
    ]

    controller = PredictiveThermalOvershootController()
    assert controller.observe_consequence(observation(0.9, False)) is None
    assert controller.predicted_departure_thermal_overshoot == 0.0


def test_irrelevant_experience_does_not_write_prediction() -> None:
    controller = PredictiveThermalOvershootController()
    assert controller.act(observation(0.2, True)) is Action.WAIT
    assert controller.observe_consequence(observation(0.9, False)) is None
    assert controller.predicted_departure_thermal_overshoot == 0.0


def test_departure_transient_state_tracks_peak_and_clears_on_contact_loss() -> None:
    controller = PredictiveThermalOvershootController()
    controller.act(observation(0.60, True))
    assert controller.departure_start_thermal == pytest.approx(0.60)
    assert controller.departure_peak_thermal == pytest.approx(0.60)
    assert controller.observe_consequence(observation(0.55, True)) is None
    assert controller.departure_peak_thermal == pytest.approx(0.60)
    assert controller.observe_consequence(observation(0.64, True)) is None
    assert controller.departure_peak_thermal == pytest.approx(0.64)
    assert controller.observe_consequence(observation(0.61, False)) is not None
    assert controller.departure_start_thermal is None
    assert controller.departure_peak_thermal is None


def test_controller_reset_starts_a_new_lifetime() -> None:
    controller = PredictiveThermalOvershootController()
    controller.act(observation(0.60, True))
    controller.observe_consequence(observation(0.64, False))
    controller.reset()

    assert controller.mode is D003Mode.CHARGE
    assert controller.turns_remaining == 0
    assert controller.predicted_departure_thermal_overshoot == 0.0
    assert controller.departure_start_thermal is None
    assert controller.departure_peak_thermal is None


def test_prediction_persists_across_a_completed_shuttle_cycle() -> None:
    controller = PredictiveThermalOvershootController()
    controller.act(observation(0.60, True))
    controller.observe_consequence(observation(0.64, False))
    learned_prediction = controller.predicted_departure_thermal_overshoot
    complete_return_to_charge(controller)

    assert controller.predicted_departure_thermal_overshoot == learned_prediction


def test_learning_changes_charge_action_for_same_narrow_observation() -> None:
    initial = PredictiveThermalOvershootController()
    learned = PredictiveThermalOvershootController()
    assert initial.act(observation(0.59, True)) is Action.WAIT
    learned.act(observation(0.60, True))
    learned.observe_consequence(observation(0.64, False))
    complete_return_to_charge(learned)

    assert learned.act(observation(0.59, True)) is Action.MOVE_FORWARD
    assert initial.mode is D003Mode.CHARGE
    assert initial.predicted_departure_thermal_overshoot == 0.0


def test_legal_seed_integration_has_updates_and_later_early_departure() -> None:
    result = run_d005_probe((18141,), horizon=1000, collect_trace=True)
    run = result["results"][0]
    assert isinstance(run, dict)
    assert run["learning_update_count"] >= 1
    updates = run["learning_updates"]
    assert isinstance(updates, list)
    assert updates
    trace = run["trace"]
    assert isinstance(trace, tuple)
    learned_trace = [entry for entry in trace if entry.prediction_used > 0.0]
    assert learned_trace
    assert any(entry.controller_mode is D003Mode.DEPART for entry in learned_trace)
    assert run["final_prediction"] > 0.0


def test_reserved_seed_guard_remains_effective() -> None:
    with pytest.raises(ValueError):
        run_d005_probe((50001,), horizon=1)


def test_reward_info_and_controller_boundary_remain_closed() -> None:
    result = run_d005_probe((18141,), horizon=2)
    run = result["results"][0]
    assert isinstance(run, dict)
    assert run["controller_input_fields"] == [
        "thermal_interoception",
        "charging_contact",
    ]
    assert not any(
        name in {"energy", "position", "station_center", "reward", "info"}
        for name in run["controller_input_fields"]  # type: ignore[union-attr]
    )


def test_observation_is_two_channel_and_no_controller_rng_exists() -> None:
    controller = PredictiveThermalOvershootController()
    item = observation(0.2, True)
    assert [field.name for field in fields(item)] == ["thermal", "charging_contact"]
    assert not hasattr(controller, "rng")
    assert not hasattr(controller, "energy")
    assert not hasattr(controller, "beacon")


def test_d005_probe_observation_projection_rejects_wrong_shape() -> None:
    from aweform.d003 import _controller_observation

    with pytest.raises(ValueError):
        _controller_observation(np.zeros(5, dtype=np.float32))
