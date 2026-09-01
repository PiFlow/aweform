from __future__ import annotations

import math
from dataclasses import replace

import numpy as np
import pytest

from aweform import (
    Action,
    ChargePhase,
    D020Env,
    D020PhysicalConfig,
    D020TerminationReason,
    classify_thermal_safety,
    run_d020_probe_suite,
)


def _env(**options: object) -> D020Env:
    environment = D020Env()
    environment.reset(options=options)
    return environment


def test_default_freeze_is_exact() -> None:
    config = D020PhysicalConfig()

    assert config.dt_seconds == 0.1
    assert config.world_scale_metres_per_unit == 1.0
    assert config.movement_distance_world_units == 0.05
    assert config.turn_angle == math.pi / 4.0
    assert config.battery_capacity_j == 5328.0
    assert config.initial_battery_j == 2664.0
    assert config.electronics_electrical_power_w == 0.15
    assert config.electronics_body_heat_w == 0.15
    assert config.wait_actuator_electrical_power_w == 0.0
    assert config.move_actuator_electrical_power_w == 1.0
    assert config.turn_actuator_electrical_power_w == 0.65
    assert config.wait_actuator_body_heat_w == 0.0
    assert config.move_actuator_body_heat_w == 0.0
    assert config.turn_actuator_body_heat_w == 0.0
    assert config.charge_efficiency == 0.90
    assert config.bulk_charge_power_w == 1.85
    assert config.taper_1_charge_power_w == 0.925
    assert config.taper_2_charge_power_w == 0.37
    assert (config.bulk_soc_upper, config.taper_1_soc_upper) == (0.90, 0.95)
    assert config.resume_soc == 0.98
    assert config.thermal_capacitance_j_per_k == 180.0
    assert config.thermal_conductance_w_per_k == 0.25
    assert config.ambient_temperature_c == 23.0
    assert config.initial_body_temperature_c == 23.0
    assert (
        config.preferred_operating_ceiling_c,
        config.protective_shutdown_c,
        config.hard_shutdown_c,
    ) == (45.0, 60.0, 65.0)
    assert (config.visible_temperature_min_c, config.visible_temperature_max_c) == (
        0.0,
        80.0,
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"dt_seconds": 0.0},
        {"battery_capacity_j": 0.0},
        {"initial_battery_j": -1.0},
        {"initial_battery_j": 5329.0},
        {"charge_efficiency": 0.0},
        {"charge_efficiency": 1.01},
        {"thermal_capacitance_j_per_k": 0.0},
        {"thermal_conductance_w_per_k": -0.1},
        {"taper_1_soc_upper": 0.90},
        {"resume_soc": 0.95},
        {"visible_temperature_max_c": 0.0},
        {"protective_shutdown_c": 45.0},
    ],
)
def test_invalid_physical_configuration_is_rejected(changes: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        replace(D020PhysicalConfig(), **changes)


def test_off_dock_wait_matches_analytic_accounting() -> None:
    environment = _env(body_position=(0.1, 0.1), station_center=(0.9, 0.9))
    _, reward, terminated, truncated, info = environment.step(Action.WAIT)

    assert (reward, terminated, truncated, info) == (0.0, False, False, {})
    assert environment.last_transition is not None
    transition = environment.last_transition
    assert transition.total_electrical_load_w == pytest.approx(0.15)
    assert transition.battery_after_j == pytest.approx(2663.985)
    assert transition.total_body_heat_w == pytest.approx(0.15)
    assert transition.environmental_exchange_power_w == pytest.approx(0.0)
    assert transition.body_temperature_after_c == pytest.approx(23.00008333333333)


def test_off_dock_move_uses_electrical_load_but_no_default_actuator_heat() -> None:
    environment = _env(body_position=(0.1, 0.1), station_center=(0.9, 0.9))
    environment.step(Action.MOVE_FORWARD)

    assert environment.last_transition is not None
    transition = environment.last_transition
    assert transition.total_electrical_load_w == pytest.approx(1.15)
    assert transition.battery_after_j == pytest.approx(2663.885)
    assert transition.actuator_body_heat_w == 0.0
    assert transition.body_temperature_after_c == pytest.approx(23.00008333333333)


def test_turns_are_symmetric() -> None:
    left = _env(body_position=(0.1, 0.1), station_center=(0.9, 0.9))
    right = _env(body_position=(0.1, 0.1), station_center=(0.9, 0.9))
    left.step(Action.TURN_LEFT)
    right.step(Action.TURN_RIGHT)

    assert left.last_transition is not None
    assert right.last_transition is not None
    assert left.last_transition.total_electrical_load_w == pytest.approx(0.80)
    assert left.last_transition.battery_after_j == pytest.approx(2663.920)
    assert right.last_transition.battery_after_j == pytest.approx(2663.920)
    assert left.last_transition.body_temperature_after_c == pytest.approx(
        right.last_transition.body_temperature_after_c
    )


def test_test_only_actuator_heat_is_separate_from_battery_ledger() -> None:
    config = replace(
        D020PhysicalConfig(),
        dt_seconds=1.0,
        battery_capacity_j=20.0,
        initial_battery_j=10.0,
        electronics_electrical_power_w=0.0,
        electronics_body_heat_w=0.0,
        move_actuator_electrical_power_w=1.0,
        move_actuator_body_heat_w=2.0,
        thermal_capacitance_j_per_k=1.0,
        thermal_conductance_w_per_k=0.0,
    )
    environment = D020Env(config)
    environment.reset(
        options={"body_position": (0.1, 0.1), "station_center": (0.9, 0.9)}
    )
    environment.step(Action.MOVE_FORWARD)

    assert environment.last_transition is not None
    assert environment.last_transition.actuator_body_heat_w == 2.0
    assert environment.last_transition.battery_after_j == pytest.approx(9.0)
    assert environment.body_temperature_c == pytest.approx(25.0)


def test_post_action_contact_controls_same_transition_charge() -> None:
    entering = _env(body_position=(0.26, 0.5), station_center=(0.5, 0.5), heading=0.0)
    entering.step(Action.MOVE_FORWARD)
    entering.step(Action.MOVE_FORWARD)
    entering.step(Action.MOVE_FORWARD)
    assert entering.last_transition is not None
    assert entering.last_transition.charging_contact_before is False
    assert entering.last_transition.charging_contact_after is True
    assert entering.last_transition.actual_stored_power_w == pytest.approx(1.85)

    leaving = _env(body_position=(0.59, 0.5), station_center=(0.5, 0.5), heading=0.0)
    leaving.step(Action.MOVE_FORWARD)
    assert leaving.last_transition is not None
    assert leaving.last_transition.charging_contact_before is True
    assert leaving.last_transition.charging_contact_after is False
    assert leaving.last_transition.charge_phase is ChargePhase.OFF
    assert leaving.last_transition.actual_stored_power_w == 0.0


@pytest.mark.parametrize(
    ("battery", "phase", "power"),
    [
        (2664.0, ChargePhase.BULK, 1.85),
        (5328.0 * 0.92, ChargePhase.TAPER_1, 0.925),
        (5328.0 * 0.97, ChargePhase.TAPER_2, 0.37),
    ],
)
def test_charge_phases_match_frozen_piecewise_rule(
    battery: float, phase: ChargePhase, power: float
) -> None:
    environment = _env(
        body_position=(0.5, 0.5), station_center=(0.5, 0.5), battery_j=battery
    )
    environment.step(Action.WAIT)

    assert environment.last_transition is not None
    transition = environment.last_transition
    assert transition.charge_phase is phase
    assert transition.requested_stored_power_w == pytest.approx(power)
    assert transition.actual_stored_power_w == pytest.approx(power)
    assert transition.battery_after_j == pytest.approx(battery + (power - 0.15) * 0.1)


def test_near_full_headroom_cap_and_next_transition_standby() -> None:
    config = D020PhysicalConfig()
    environment = D020Env(config)
    environment.reset(
        options={
            "body_position": (0.5, 0.5),
            "station_center": (0.5, 0.5),
            "battery_j": config.battery_capacity_j - 0.005,
        }
    )
    environment.step(Action.WAIT)

    assert environment.last_transition is not None
    first = environment.last_transition
    assert first.charge_phase is ChargePhase.TAPER_2
    assert first.actual_stored_power_w == pytest.approx(0.2)
    assert first.battery_after_j == pytest.approx(config.battery_capacity_j)
    assert first.charging_body_heat_w == pytest.approx(0.2 / 0.9 - 0.2)
    assert first.charger_termination_latched_after is True

    environment.step(Action.WAIT)
    assert environment.last_transition is not None
    second = environment.last_transition
    assert second.charge_phase is ChargePhase.STANDBY
    assert second.actual_stored_power_w == 0.0
    assert second.charging_body_heat_w == 0.0
    assert second.battery_after_j == pytest.approx(config.battery_capacity_j - 0.015)


def test_full_contact_standby_restart_hysteresis_and_contact_loss() -> None:
    full = _env(body_position=(0.5, 0.5), station_center=(0.5, 0.5), battery_j=5328.0)
    full.step(Action.WAIT)
    assert full.last_transition is not None
    assert full.last_transition.charge_phase is ChargePhase.STANDBY
    assert full.last_transition.charging_body_heat_w == 0.0
    assert full.last_transition.charger_termination_latched_after is True

    restart = _env(
        body_position=(0.5, 0.5),
        station_center=(0.5, 0.5),
        battery_j=5328.0 * 0.98,
        charger_termination_latched=True,
    )
    restart.step(Action.WAIT)
    assert restart.last_transition is not None
    assert restart.last_transition.charge_phase is ChargePhase.TAPER_2
    assert restart.last_transition.actual_stored_power_w > 0.0

    lost = _env(
        body_position=(0.59, 0.5),
        station_center=(0.5, 0.5),
        heading=0.0,
        charger_termination_latched=True,
    )
    lost.step(Action.MOVE_FORWARD)
    assert lost.last_transition is not None
    assert lost.last_transition.charge_phase is ChargePhase.OFF
    assert lost.charger_termination_latched is False


@pytest.mark.parametrize(
    ("temperature", "exchange", "next_temperature"),
    [(30.0, -7.0, 23.0), (16.0, 7.0, 23.0), (23.0, 0.0, 23.0)],
)
def test_signed_passive_exchange(
    temperature: float, exchange: float, next_temperature: float
) -> None:
    config = replace(
        D020PhysicalConfig(),
        dt_seconds=1.0,
        electronics_body_heat_w=0.0,
        thermal_capacitance_j_per_k=1.0,
        thermal_conductance_w_per_k=1.0,
    )
    environment = D020Env(config)
    environment.reset(
        options={
            "body_position": (0.1, 0.1),
            "station_center": (0.9, 0.9),
            "body_temperature_c": temperature,
        }
    )
    environment.step(Action.WAIT)

    assert environment.last_transition is not None
    assert environment.last_transition.environmental_exchange_power_w == pytest.approx(
        exchange
    )
    assert environment.body_temperature_c == pytest.approx(next_temperature)


@pytest.mark.parametrize(
    ("temperature", "expected"),
    [
        (45.0, None),
        (59.999, None),
        (60.0, D020TerminationReason.PROTECTIVE_THERMAL_SHUTDOWN),
        (65.0, D020TerminationReason.EMERGENCY_HARD_THERMAL_SHUTDOWN),
    ],
)
def test_thermal_threshold_semantics(
    temperature: float, expected: D020TerminationReason | None
) -> None:
    protective, emergency, reason = classify_thermal_safety(temperature)
    assert reason is expected
    assert protective is (expected is D020TerminationReason.PROTECTIVE_THERMAL_SHUTDOWN)
    assert emergency is (
        expected is D020TerminationReason.EMERGENCY_HARD_THERMAL_SHUTDOWN
    )


def test_temperature_normalization_and_clamping() -> None:
    config = D020PhysicalConfig()
    environment = D020Env(config)
    for temperature, expected in (
        (23.0, 0.2875),
        (45.0, 0.5625),
        (60.0, 0.75),
        (65.0, 0.8125),
        (80.0, 1.0),
        (-1.0, 0.0),
        (100.0, 1.0),
    ):
        observation, _ = environment.reset(
            options={
                "body_position": (0.1, 0.1),
                "station_center": (0.9, 0.9),
                "body_temperature_c": temperature,
            }
        )
        assert observation[5] == pytest.approx(expected)


def test_simultaneous_viability_flags_use_emergency_precedence() -> None:
    config = replace(
        D020PhysicalConfig(),
        dt_seconds=1.0,
        battery_capacity_j=10.0,
        initial_battery_j=0.05,
        electronics_electrical_power_w=0.5,
        electronics_body_heat_w=43.0,
        thermal_capacitance_j_per_k=1.0,
        thermal_conductance_w_per_k=0.0,
    )
    environment = D020Env(config)
    environment.reset(
        options={"body_position": (0.1, 0.1), "station_center": (0.9, 0.9)}
    )
    environment.step(Action.WAIT)

    assert environment.last_transition is not None
    transition = environment.last_transition
    assert transition.energy_nonviable is True
    assert transition.emergency_hard_shutdown is True
    assert transition.protective_shutdown is False
    assert (
        transition.termination_reason
        is D020TerminationReason.EMERGENCY_HARD_THERMAL_SHUTDOWN
    )


def test_observation_closure_reward_info_and_terminal_observation() -> None:
    config = replace(
        D020PhysicalConfig(),
        dt_seconds=1.0,
        initial_battery_j=0.1,
        electronics_electrical_power_w=1.0,
    )
    environment = D020Env(config)
    observation, reset_info = environment.reset(
        options={"body_position": (0.1, 0.1), "station_center": (0.9, 0.9)}
    )
    next_observation, reward, terminated, truncated, info = environment.step(
        Action.WAIT
    )

    assert observation.shape == (6,)
    assert next_observation.shape == (6,)
    assert reset_info == {}
    assert reward == 0.0
    assert info == {}
    assert terminated is True
    assert truncated is False
    assert np.all((0.0 <= next_observation) & (next_observation <= 1.0))
    assert environment.last_transition is not None
    assert "termination_reason" not in info


def test_probe_suite_is_seedless_and_deterministic() -> None:
    first = run_d020_probe_suite()
    second = run_d020_probe_suite()
    assert first == second
    assert first["seed_status"] == "seedless fixed-state evaluator probes"
    probes = first["probes"]
    assert isinstance(probes, dict)
    assert set(probes) == {
        "DOCKED_WAIT_CHARGE",
        "OFF_DOCK_MOVE_ENERGY",
        "MIXED_ACTION_CAUSAL_ACCOUNTING",
    }
