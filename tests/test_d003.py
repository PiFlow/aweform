"""Focused tests for the D-003 fixed thermostatic shuttle."""

from dataclasses import fields

import numpy as np
import pytest

from aweform.d002 import (
    D002_AMBIENT_THERMAL_STATE,
    D002_CHARGING_HEAT_PER_OFFERED_ENERGY,
    D002_INITIAL_THERMAL_STATE,
    D002_PASSIVE_COOLING_PER_TRANSITION,
    D002ThermalStationEnv,
)
from aweform.d003 import (
    COOL_RETURN_THRESHOLD,
    HOT_DEPART_THRESHOLD,
    RETURN_HALF_TURN_STEPS,
    D003Mode,
    D003ThermostaticObservation,
    ThermostaticShuttleController,
    _controller_observation,
    _prepare_post_contact_setup,
    _refresh_observation,
    run_d003_probe,
)
from aweform.env import Action
from aweform.exp003 import LocalizedChargingStationEnv


def observation(thermal: float, contact: bool) -> D003ThermostaticObservation:
    return D003ThermostaticObservation(thermal, contact)


def test_observation_is_immutable_and_has_only_two_fields() -> None:
    assert [field.name for field in fields(D003ThermostaticObservation)] == [
        "thermal",
        "charging_contact",
    ]
    item = observation(0.2, True)
    with pytest.raises((AttributeError, TypeError)):
        item.thermal = 0.3  # type: ignore[misc]


def test_observation_validates_thermal_and_contact() -> None:
    with pytest.raises(ValueError):
        observation(-0.01, True)
    with pytest.raises(ValueError):
        observation(1.01, True)
    with pytest.raises(ValueError):
        observation(float("nan"), True)
    with pytest.raises(ValueError):
        D003ThermostaticObservation(0.2, 1)  # type: ignore[arg-type]


def test_controller_rejects_non_typed_observation() -> None:
    controller = ThermostaticShuttleController()
    with pytest.raises(ValueError):
        controller.act((0.2, True))  # type: ignore[arg-type]


def test_projection_uses_only_d002_thermal_and_contact_channels() -> None:
    projected = _controller_observation(
        np.asarray((0.91, 0.8, 0.7, 0.6, 1.0, 0.2), dtype=np.float32)
    )
    assert projected.thermal == pytest.approx(0.2)
    assert projected.charging_contact is True
    with pytest.raises(ValueError):
        _controller_observation(np.zeros(5, dtype=np.float32))


def test_charge_thresholds_are_exact() -> None:
    controller = ThermostaticShuttleController()
    assert controller.act(observation(0.599999, True)) is Action.WAIT
    assert controller.mode is D003Mode.CHARGE
    assert (
        controller.act(observation(HOT_DEPART_THRESHOLD, True)) is Action.MOVE_FORWARD
    )
    assert controller.mode is D003Mode.DEPART

    controller = ThermostaticShuttleController()
    controller.mode = D003Mode.COOL
    assert (
        controller.act(observation(COOL_RETURN_THRESHOLD + 0.000001, False))
        is Action.WAIT
    )
    assert controller.mode is D003Mode.COOL
    assert controller.act(observation(COOL_RETURN_THRESHOLD, False)) is Action.TURN_LEFT
    assert controller.mode is D003Mode.TURN_RETURN


def test_departure_waits_until_contact_is_lost() -> None:
    controller = ThermostaticShuttleController()
    controller.mode = D003Mode.DEPART
    assert controller.act(observation(0.9, True)) is Action.MOVE_FORWARD
    assert controller.mode is D003Mode.DEPART
    assert controller.act(observation(0.9, False)) is Action.WAIT
    assert controller.mode is D003Mode.COOL


def test_half_turn_emits_exactly_four_left_turns() -> None:
    controller = ThermostaticShuttleController()
    controller.mode = D003Mode.COOL
    actions = [controller.act(observation(0.3, False))]
    actions.extend(
        controller.act(observation(0.2, False))
        for _ in range(RETURN_HALF_TURN_STEPS - 1)
    )
    assert actions == [Action.TURN_LEFT] * RETURN_HALF_TURN_STEPS
    assert controller.mode is D003Mode.RETURN
    assert controller.turns_remaining == 0


def test_return_moves_until_contact_then_reenters_charge() -> None:
    controller = ThermostaticShuttleController()
    controller.mode = D003Mode.RETURN
    assert controller.act(observation(0.2, False)) is Action.MOVE_FORWARD
    assert controller.mode is D003Mode.RETURN
    assert controller.act(observation(0.2, True)) is Action.WAIT
    assert controller.mode is D003Mode.CHARGE


def test_reset_clears_only_controller_phase_state() -> None:
    controller = ThermostaticShuttleController()
    controller.mode = D003Mode.TURN_RETURN
    controller.turns_remaining = 2
    controller.reset()
    assert controller.mode is D003Mode.CHARGE
    assert controller.turns_remaining == 0
    assert not hasattr(controller, "rng")
    assert not hasattr(controller, "energy")
    assert not hasattr(controller, "beacon")


def test_ecology_contracts_remain_unchanged() -> None:
    environment = D002ThermalStationEnv()
    observation_value, _ = environment.reset(seed=18141)
    assert observation_value.shape == (6,)
    assert environment.observation_space.shape == (6,)
    assert D002_AMBIENT_THERMAL_STATE == 0.0
    assert D002_INITIAL_THERMAL_STATE == 0.20
    assert D002_CHARGING_HEAT_PER_OFFERED_ENERGY == 0.04
    assert D002_PASSIVE_COOLING_PER_TRANSITION == 0.01

    historical = LocalizedChargingStationEnv()
    historical_observation, _ = historical.reset(seed=18141)
    assert historical_observation.shape == (5,)
    _, reward, _, _, _ = environment.step(Action.WAIT)
    assert reward == 0.0


def test_harness_places_body_and_station_but_preserves_heading() -> None:
    environment = D002ThermalStationEnv()
    environment.reset(seed=18141)
    assert environment.body is not None
    initial_heading = environment.body.heading
    returned_heading = _prepare_post_contact_setup(environment)
    assert returned_heading == initial_heading
    assert environment.body.position == (0.5, 0.5)
    assert environment.body.heading == initial_heading
    assert environment.station_center == (0.5, 0.5)
    projected = _controller_observation(_refresh_observation(environment))
    assert projected.thermal == pytest.approx(D002_INITIAL_THERMAL_STATE)
    assert projected.charging_contact is True
    assert not hasattr(projected, "heading")


def test_seed_guard_accepts_development_and_rejects_reserved_seed() -> None:
    result = run_d003_probe((18141,), horizon=1)
    assert result["development_seeds"] == [18141]
    with pytest.raises(ValueError):
        run_d003_probe((50001,), horizon=1)


def test_probe_reports_required_telemetry_without_exposing_it_to_controller() -> None:
    result = run_d003_probe((18141,), horizon=1)
    run = result["results"][0]
    assert isinstance(run, dict)
    for key in (
        "seed",
        "transitions",
        "terminated",
        "truncated",
        "energy_termination",
        "thermal_termination",
        "minimum_energy",
        "maximum_energy",
        "final_energy",
        "minimum_thermal_state",
        "maximum_thermal_state",
        "final_thermal_state",
        "completed_shuttle_cycles",
        "charging_contact_transitions",
        "off_contact_transitions",
        "mode_occupancy",
    ):
        assert key in run
    assert run["controller_input_fields"] == [
        "thermal_interoception",
        "charging_contact",
    ]
    assert run["initial_position"] == [0.5, 0.5]
    assert run["station_center"] == [0.5, 0.5]
