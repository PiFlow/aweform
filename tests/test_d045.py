"""Focused D-045 deterministic substrate tests."""

from __future__ import annotations

import math

import numpy as np
import pytest
from gymnasium import spaces

from aweform import (
    D045ChargePhase,
    D045Env,
    D045PhysicalConfig,
    D045TerminationReason,
    integrate_differential_drive,
    quantize_wheel_delta,
    run_d045_probe_suite,
    wheel_effort,
)


def _env(**options: object) -> D045Env:
    environment = D045Env()
    environment.reset(options=options)
    return environment


def test_d045_freeze_and_exact_eight_channel_spaces() -> None:
    config = D045PhysicalConfig()
    environment = D045Env(config)

    assert config.dt_seconds == 0.1
    assert config.wheel_track_width_m == 0.185
    assert config.wheel_radius_m == 0.045
    assert config.max_wheel_delta_rad == 0.6457718232379019
    assert config.encoder_quantum_rad == math.pi / 180.0
    assert environment.action_space.shape == (2,)
    assert environment.observation_space.shape == (8,)
    assert isinstance(environment.observation_space, spaces.Box)
    assert np.all(environment.observation_space.low[:6] == 0.0)
    assert np.all(environment.observation_space.high[:6] == 1.0)


def test_reset_has_zero_completed_wheel_delta_and_no_info() -> None:
    environment = _env(body_position=(0.4, 0.4), station_center=(0.9, 0.9))

    observation, info = environment.reset(
        options={"body_position": (0.4, 0.4), "station_center": (0.9, 0.9)}
    )

    assert info == {}
    assert observation.shape == (8,)
    assert tuple(observation[6:]) == (0.0, 0.0)


def test_zero_command_has_zero_actuator_power_and_exact_public_boundary() -> None:
    environment = _env(body_position=(0.4, 0.4), station_center=(0.9, 0.9))

    observation, reward, terminated, truncated, info = environment.step((0.0, 0.0))

    assert reward == 0.0
    assert not terminated
    assert not truncated
    assert info == {}
    assert environment.last_transition is not None
    assert environment.last_transition.actuator_electrical_power_w == 0.0
    assert environment.last_transition.actuator_body_heat_w == 0.0
    assert tuple(observation[6:]) == (0.0, 0.0)


def test_exact_straight_line_integration() -> None:
    position, heading = integrate_differential_drive((0.2, 0.3), 0.0, 0.4, 0.4)

    expected_distance = 0.045 * 0.4
    assert position == pytest.approx((0.2 + expected_distance, 0.3))
    assert heading == pytest.approx(0.0)


def test_exact_arc_integration_matches_radius_equations() -> None:
    delta_left = 0.4
    delta_right = 0.2
    position, heading = integrate_differential_drive(
        (0.2, 0.3), 0.0, delta_left, delta_right
    )
    d_left = 0.045 * delta_left
    d_right = 0.045 * delta_right
    d_s = (d_left + d_right) / 2.0
    d_theta = (d_right - d_left) / 0.185
    radius = d_s / d_theta
    assert heading == pytest.approx(d_theta)
    assert position == pytest.approx(
        (
            0.2 + radius * math.sin(d_theta),
            0.3 - radius * (math.cos(d_theta) - 1.0),
        )
    )


def test_over_range_commands_are_independently_clamped() -> None:
    environment = _env(body_position=(0.4, 0.4), station_center=(0.9, 0.9))

    observation, *_ = environment.step((2.0, -2.0))

    assert environment.last_transition is not None
    transition = environment.last_transition
    assert transition.clamped_delta_left == D045PhysicalConfig().max_wheel_delta_rad
    assert transition.clamped_delta_right == -D045PhysicalConfig().max_wheel_delta_rad
    assert transition.actual_delta_left == pytest.approx(
        D045PhysicalConfig().max_wheel_delta_rad
    )
    assert observation[6] == pytest.approx(-observation[7])


def test_boundary_reduction_preserves_ratio_and_does_not_reflect() -> None:
    environment = _env(
        body_position=(0.99, 0.5), station_center=(0.5, 0.5), heading=0.0
    )

    environment.step((0.6, 0.3))

    assert environment.last_transition is not None
    transition = environment.last_transition
    assert 0.0 < transition.boundary_scale < 1.0
    assert transition.actual_delta_left == pytest.approx(
        2.0 * transition.actual_delta_right
    )
    assert transition.position_after[0] == pytest.approx(1.0)
    assert transition.position_after[0] >= transition.position_before[0]
    assert not hasattr(transition, "collision")


@pytest.mark.parametrize(
    ("position", "heading", "expected"),
    [
        ((0.5, 0.5), 0.0, True),
        ((0.5099, 0.5), 0.0, True),
        ((0.5101, 0.5), 0.0, False),
        ((0.5, 0.5), math.pi, False),
    ],
)
def test_centred_dual_contact_is_corresponding_and_inclusive(
    position: tuple[float, float], heading: float, expected: bool
) -> None:
    environment = _env(
        body_position=position,
        station_center=(0.5, 0.5),
        heading=heading,
    )

    environment.step((0.0, 0.0))

    assert environment.last_transition is not None
    assert environment.last_transition.charging_contact_after is expected


def test_quantization_is_signed_and_half_away_from_zero() -> None:
    quantum = math.pi / 180.0

    assert quantize_wheel_delta(0.49 * quantum, quantum) == 0.0
    assert quantize_wheel_delta(0.5 * quantum, quantum) == pytest.approx(quantum)
    assert quantize_wheel_delta(-0.5 * quantum, quantum) == pytest.approx(-quantum)
    assert quantize_wheel_delta(-1.49 * quantum, quantum) == pytest.approx(-quantum)
    assert quantize_wheel_delta(-1.5 * quantum, quantum) == pytest.approx(
        -2.0 * quantum
    )


def test_visible_beacon_and_contact_order_is_not_evaluator_telemetry() -> None:
    environment = _env(body_position=(0.4, 0.4), station_center=(0.9, 0.9))
    observation, reward, terminated, truncated, info = environment.step(
        (math.pi / 180.0, -math.pi / 180.0)
    )

    assert observation.shape == (8,)
    assert environment.observation_space.contains(observation)
    assert np.all(np.isfinite(observation))
    assert (reward, terminated, truncated, info) == (0.0, False, False, {})
    assert environment.last_transition is not None
    assert not hasattr(observation, "position")
    assert not hasattr(observation, "heading")
    assert not hasattr(observation, "dock_plus_error_m")


def test_wheel_effort_is_continuous_symmetric_and_swap_invariant() -> None:
    maximum = D045PhysicalConfig().max_wheel_delta_rad

    assert wheel_effort(0.0, 0.0, maximum) == 0.0
    assert wheel_effort(maximum, maximum, maximum) == 1.0
    assert wheel_effort(maximum, 0.0, maximum) == 0.5
    assert wheel_effort(-maximum, -maximum, maximum) == 1.0
    assert wheel_effort(maximum, 0.0, maximum) == wheel_effort(0.0, maximum, maximum)


def test_wheel_bookkeeping_and_retained_charger_causal_order() -> None:
    environment = _env(
        body_position=(0.5, 0.5),
        station_center=(0.5, 0.5),
        battery_j=2664.0,
        body_temperature_c=23.0,
    )

    environment.step((0.0, 0.0))

    assert environment.last_transition is not None
    transition = environment.last_transition
    assert transition.charge_phase is D045ChargePhase.BULK
    assert transition.battery_after_j == pytest.approx(2664.17)
    assert transition.charging_body_heat_w == pytest.approx(1.85 / 0.9 - 1.85)
    assert transition.body_temperature_after_c == pytest.approx(
        23.0 + 0.1 * (0.15 + 1.85 / 0.9 - 1.85) / 180.0
    )


def test_temperature_shutdown_precedence_is_retained() -> None:
    config = D045PhysicalConfig(
        initial_body_temperature_c=65.0,
        ambient_temperature_c=65.0,
        electronics_power_w=0.0,
        electronics_body_heat_w=0.0,
    )
    environment = D045Env(config)
    environment.reset(options={"body_temperature_c": 65.0, "battery_j": 100.0})
    environment.step((0.0, 0.0))

    assert environment.last_transition is not None
    assert environment.last_transition.emergency_hard_shutdown
    assert (
        environment.last_transition.termination_reason
        is D045TerminationReason.EMERGENCY_HARD_THERMAL_SHUTDOWN
    )


def test_reset_seed_does_not_change_deterministic_actuator_trace() -> None:
    commands = ((0.2, -0.1), (0.0, 0.4), (-0.3, 0.2))
    traces: list[list[tuple[float, ...]]] = []
    for seed in (1, 999):
        environment = D045Env()
        environment.reset(
            seed=seed,
            options={"body_position": (0.4, 0.4), "station_center": (0.9, 0.9)},
        )
        trace: list[tuple[float, ...]] = []
        for command in commands:
            environment.step(command)
            assert environment.last_transition is not None
            trace.append(
                (
                    environment.last_transition.actual_delta_left,
                    environment.last_transition.actual_delta_right,
                    environment.last_transition.position_after[0],
                    environment.last_transition.position_after[1],
                )
            )
        traces.append(trace)
    assert traces[0] == traces[1]


def test_structural_feasibility_and_replay_probe_are_positive() -> None:
    artifact = run_d045_probe_suite()
    probes = artifact["probes"]
    assert isinstance(probes, dict)
    structural = probes["structural_feasibility"]
    replay = probes["deterministic_replay"]
    assert isinstance(structural, dict)
    assert isinstance(replay, dict)
    assert structural["feasible"] is True
    assert replay["byte_identical_trace"] is True
