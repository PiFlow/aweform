"""Focused tests for the D-002 minimal thermal ecology."""

from math import pi

import numpy as np
import pytest

from aweform.d002 import (
    D002_AMBIENT_THERMAL_STATE,
    D002_CHARGING_HEAT_PER_OFFERED_ENERGY,
    D002_INITIAL_THERMAL_STATE,
    D002_PASSIVE_COOLING_PER_TRANSITION,
    D002ThermalStationEnv,
)
from aweform.env import Action
from aweform.exp003 import EXP003StationConfig, LocalizedChargingStationEnv


def _docked_env(**kwargs: object) -> D002ThermalStationEnv:
    config = EXP003StationConfig(**kwargs)
    environment = D002ThermalStationEnv(config=config)
    environment.reset(seed=18141)
    assert environment.body is not None
    assert environment.station_center is not None
    environment.body.x, environment.body.y = environment.station_center
    return environment


def _set_geometry(
    environment: D002ThermalStationEnv,
    *,
    body_position: tuple[float, float],
    station_center: tuple[float, float],
    heading: float = 0.0,
) -> None:
    assert environment.body is not None
    environment.body.x, environment.body.y = body_position
    environment.body.heading = heading
    environment.base_env.station_center = station_center


def test_exp003_contract_remains_five_channels() -> None:
    environment = LocalizedChargingStationEnv()
    observation, _ = environment.reset(seed=18141)

    assert environment.observation_space.shape == (5,)
    assert observation.shape == (5,)


def test_d002_exposes_six_normalized_channels_and_initial_thermal_signal() -> None:
    environment = D002ThermalStationEnv()
    observation, info = environment.reset(seed=18141)

    assert info == {}
    assert environment.observation_space.shape == (6,)
    assert observation.shape == (6,)
    assert np.all(observation >= 0.0)
    assert np.all(observation <= 1.0)
    assert observation[5] == pytest.approx(D002_INITIAL_THERMAL_STATE)


def test_d002_first_five_observation_values_match_standalone_exp003() -> None:
    d002 = D002ThermalStationEnv()
    exp003 = LocalizedChargingStationEnv()
    d002_observation, _ = d002.reset(seed=18141)
    exp003_observation, _ = exp003.reset(seed=18141)

    assert np.array_equal(d002_observation[:5], exp003_observation)
    for action in (Action.WAIT, Action.TURN_LEFT, Action.MOVE_FORWARD):
        d002_observation, _, d002_terminated, _, _ = d002.step(action)
        exp003_observation, _, exp003_terminated, _, _ = exp003.step(action)
        assert np.array_equal(d002_observation[:5], exp003_observation)
        assert d002.base_env.last_transition is not None
        assert exp003.last_transition is not None
        assert d002.base_env.last_transition.energy_after == pytest.approx(
            exp003.last_transition.energy_after
        )
        if d002_terminated or exp003_terminated:
            break


def test_off_contact_passively_cools_to_ambient_without_lower_failure() -> None:
    environment = D002ThermalStationEnv(config=EXP003StationConfig(episode_horizon=30))
    environment.reset(seed=18141)
    _set_geometry(
        environment,
        body_position=(0.8, 0.8),
        station_center=(0.2, 0.2),
    )

    for _ in range(30):
        _, _, terminated, truncated, _ = environment.step(Action.WAIT)
        assert not terminated
        if truncated:
            break
    assert environment.thermal_state == pytest.approx(D002_AMBIENT_THERMAL_STATE)
    assert environment.last_transition is not None
    assert not environment.last_transition.thermal_termination


def test_permanent_contact_reaches_upper_boundary_and_terminates() -> None:
    environment = _docked_env()

    while True:
        _, _, terminated, truncated, _ = environment.step(Action.WAIT)
        assert not truncated
        if terminated:
            break

    assert environment.thermal_state == pytest.approx(1.0)
    assert environment.last_transition is not None
    assert environment.last_transition.thermal_termination
    assert environment.last_transition.terminated


def test_offered_input_heats_even_when_full_energy_clips() -> None:
    environment = _docked_env(initial_energy=10.0)
    thermal_before = environment.thermal_state

    _, reward, terminated, truncated, info = environment.step(Action.WAIT)

    assert reward == 0.0
    assert not terminated
    assert not truncated
    assert info == {}
    assert environment.last_transition is not None
    telemetry = environment.last_transition
    assert telemetry.offered_station_input == pytest.approx(0.5)
    assert telemetry.energy_before == pytest.approx(10.0)
    assert telemetry.energy_after == pytest.approx(10.0)
    assert telemetry.stored_energy_delta == pytest.approx(0.0)
    assert telemetry.thermal_before == pytest.approx(thermal_before)
    assert telemetry.thermal_after > telemetry.thermal_before
    assert telemetry.thermal_input == pytest.approx(
        D002_CHARGING_HEAT_PER_OFFERED_ENERGY * 0.5
    )


def test_entering_contact_heats_on_same_post_action_transition() -> None:
    environment = D002ThermalStationEnv(
        config=EXP003StationConfig(movement_distance=0.05)
    )
    environment.reset(seed=18141)
    _set_geometry(
        environment,
        body_position=(0.61, 0.5),
        station_center=(0.5, 0.5),
        heading=pi,
    )
    environment.step(Action.MOVE_FORWARD)

    assert environment.last_transition is not None
    telemetry = environment.last_transition
    assert not telemetry.charging_contact_before
    assert telemetry.charging_contact_after
    assert telemetry.offered_station_input == pytest.approx(0.5)
    assert telemetry.thermal_after == pytest.approx(D002_INITIAL_THERMAL_STATE + 0.01)


def test_leaving_contact_does_not_heat_from_prior_contact() -> None:
    environment = _docked_env()
    _set_geometry(
        environment,
        body_position=(0.09, 0.5),
        station_center=(0.0, 0.5),
        heading=0.0,
    )
    environment.step(Action.MOVE_FORWARD)

    assert environment.last_transition is not None
    telemetry = environment.last_transition
    assert telemetry.charging_contact_before
    assert not telemetry.charging_contact_after
    assert telemetry.offered_station_input == pytest.approx(0.0)
    assert telemetry.thermal_input == pytest.approx(0.0)
    assert telemetry.thermal_after == pytest.approx(
        D002_INITIAL_THERMAL_STATE - D002_PASSIVE_COOLING_PER_TRANSITION
    )


def test_energy_dynamics_action_cost_and_capacity_are_unchanged() -> None:
    d002 = _docked_env(initial_energy=5.0)
    exp003 = LocalizedChargingStationEnv(EXP003StationConfig())
    exp003.reset(seed=18141)
    assert exp003.body is not None
    assert exp003.station_center is not None
    exp003.body.x, exp003.body.y = exp003.station_center

    for action in (Action.WAIT, Action.TURN_LEFT, Action.MOVE_FORWARD):
        d002.step(action)
        if d002.last_transition is None:
            raise AssertionError("missing D-002 telemetry")
        _, _, exp003_terminated, _, _ = exp003.step(action)
        assert exp003.last_transition is not None
        assert d002.last_transition.energy_after == pytest.approx(
            exp003.last_transition.energy_after
        )
        assert d002.last_transition.action_cost == pytest.approx(
            exp003.last_transition.action_cost
        )
        if exp003_terminated:
            break
    assert d002.config.energy.maximum_energy == 10.0


def test_thermal_termination_wins_over_horizon_truncation() -> None:
    environment = _docked_env(episode_horizon=1)

    _, _, terminated, truncated, _ = environment.step(Action.WAIT)

    assert not terminated
    assert truncated

    environment = _docked_env(episode_horizon=1)
    environment.thermal_state = 0.999
    _, _, terminated, truncated, _ = environment.step(Action.WAIT)

    assert terminated
    assert not truncated
    assert environment.last_transition is not None
    assert environment.last_transition.thermal_termination


def test_energy_and_thermal_termination_are_both_preserved() -> None:
    environment = _docked_env(
        initial_energy=0.05,
        wait_cost=0.5,
        episode_horizon=1,
    )
    environment.thermal_state = 0.999

    _, reward, terminated, truncated, info = environment.step(Action.WAIT)

    assert reward == 0.0
    assert terminated
    assert not truncated
    assert info == {}
    assert environment.last_transition is not None
    assert environment.last_transition.energy_termination
    assert environment.last_transition.thermal_termination


def test_evaluator_telemetry_does_not_enter_observation_or_info() -> None:
    environment = _docked_env()
    observation, reward, _, _, info = environment.step(Action.WAIT)

    assert observation.shape == (6,)
    assert reward == 0.0
    assert info == {}
    assert environment.last_transition is not None
    assert not any(
        name in {"position", "station_center", "thermal_input"}
        for name in environment.observation_space.__dict__
    )
