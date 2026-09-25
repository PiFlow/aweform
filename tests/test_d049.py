"""Focused tests for the frozen D-049 Level-1 return core."""

from __future__ import annotations

import math

import numpy as np
import pytest

from aweform.d045 import (
    D045_MAX_WHEEL_DELTA_RAD,
    D045_WHEEL_RADIUS_METRES,
    D045_WHEEL_TRACK_WIDTH_METRES,
    D045Env,
    D045PhysicalConfig,
)
from aweform.d049 import (
    D049_INVERSE_BEARING_LIMIT_RAD,
    D049_INVERSE_COORDINATE_LIMIT_M,
    D049_INVERSE_DISTANCE_LIMIT_M,
    D049_TERMINAL_SPIN_MAX_STEPS,
    D049Controller,
    D049ControlMode,
    artifact_sha256,
    frozen_cases,
    reconstruct_source,
    run_d049_protocol,
    run_inverse_revalidation,
    write_d049_artifact,
)


def _observation(
    left: float,
    forward: float,
    right: float,
    contact: float = 0.0,
) -> np.ndarray:
    return np.asarray(
        [0.5, 0.2875, left, forward, right, contact, 0.0, 0.0],
        dtype=np.float32,
    )


def test_frozen_matrix_has_direct_and_terminal_cases() -> None:
    cases = frozen_cases()
    assert len(cases) == 3 * 8 * 4 + 8
    assert sum(case.case_group == "direct_return" for case in cases) == 96
    assert sum(case.case_group == "terminal_only" for case in cases) == 8
    assert {case.radius_m for case in cases if case.case_group == "direct_return"} == {
        0.10,
        0.25,
        0.40,
    }


def test_inverse_revalidation_uses_current_float32_path() -> None:
    summary = run_inverse_revalidation()
    assert summary.invalid_cases == 0
    assert summary.within_frozen_limits
    assert summary.max_coordinate_error_m <= D049_INVERSE_COORDINATE_LIMIT_M
    assert summary.max_distance_error_m <= D049_INVERSE_DISTANCE_LIMIT_M
    assert summary.max_bearing_error_rad <= D049_INVERSE_BEARING_LIMIT_RAD


def test_inverse_reconstructs_exact_center_from_float32_observation() -> None:
    env = D045Env()
    observation, _ = env.reset(
        options={
            "body_position": (0.5, 0.5),
            "station_center": (0.5, 0.5),
            "heading": 0.247,
        }
    )
    reconstruction = reconstruct_source(
        float(observation[2]), float(observation[3]), float(observation[4])
    )
    assert reconstruction is not None
    assert reconstruction.distance_m <= 1.0e-6
    assert abs(reconstruction.bearing_rad) <= 1.0e-12


@pytest.mark.parametrize(
    "signals",
    [
        (0.0, 0.5, 0.5),
        (-0.1, 0.5, 0.5),
        (math.nan, 0.5, 0.5),
        (1.1, 0.5, 0.5),
    ],
)
def test_invalid_beacon_reconstruction_fails_safe(signals: tuple[float, ...]) -> None:
    assert reconstruct_source(*signals) is None
    decision = D049Controller().command(_observation(*signals))
    assert decision.mode is D049ControlMode.INVALID_BEACON
    assert (decision.wheel_delta_left, decision.wheel_delta_right) == (0.0, 0.0)


def test_contact_first_rule_commands_zero_without_reading_beacon() -> None:
    decision = D049Controller().command(_observation(0.0, math.nan, 2.0, 1.0))
    assert decision.mode is D049ControlMode.CONTACT
    assert (decision.wheel_delta_left, decision.wheel_delta_right) == (0.0, 0.0)


def test_turn_command_is_smallest_bounded_in_place_command() -> None:
    # A body-relative source bearing of roughly +0.2 rad is reconstructed from
    # this asymmetric L/F/R triple and must turn left (negative L, positive R).
    decision = D049Controller().command(_observation(0.8, 0.85, 0.79))
    assert decision.mode is D049ControlMode.TURN
    assert decision.wheel_delta_left < 0.0 < decision.wheel_delta_right
    assert abs(decision.wheel_delta_left) == pytest.approx(
        abs(decision.wheel_delta_right)
    )
    expected = abs(decision.reconstruction.bearing_rad) * (
        D045_WHEEL_TRACK_WIDTH_METRES / (2.0 * D045_WHEEL_RADIUS_METRES)
    )
    assert abs(decision.wheel_delta_left) == pytest.approx(expected)


def test_straight_command_scales_distance_and_caps_existing_envelope() -> None:
    # Symmetric values reconstruct a forward source; a far source must saturate.
    decision = D049Controller().command(_observation(0.2, 0.5, 0.2))
    assert decision.mode is D049ControlMode.STRAIGHT
    assert decision.wheel_delta_left == decision.wheel_delta_right
    assert abs(decision.wheel_delta_left) == pytest.approx(
        D045_MAX_WHEEL_DELTA_RAD
    )
    # A nearer forward source should use a smaller continuous command.
    near = D049Controller().command(_observation(0.9, 0.92, 0.9))
    assert near.mode is D049ControlMode.STRAIGHT
    assert 0.0 < near.wheel_delta_left < D045_MAX_WHEEL_DELTA_RAD


def test_max_in_place_command_is_exactly_eighteen_degrees() -> None:
    _, turn = integrate_differential_drive_for_test()
    assert math.degrees(turn) == pytest.approx(18.0)


def integrate_differential_drive_for_test() -> tuple[tuple[float, float], float]:
    from aweform.d045 import integrate_differential_drive

    position, heading = integrate_differential_drive(
        (0.5, 0.5),
        0.0,
        -D045_MAX_WHEEL_DELTA_RAD,
        D045_MAX_WHEEL_DELTA_RAD,
    )
    return position, heading


def test_centered_terminal_spin_contacts_within_frozen_twenty_steps() -> None:
    max_steps = 0
    for case in frozen_cases():
        if case.case_group != "terminal_only":
            continue
        env = D045Env(D045PhysicalConfig(episode_horizon=64))
        observation, _ = env.reset(
            options={
                "body_position": case.body_position,
                "station_center": (0.5, 0.5),
                "heading": case.heading_rad,
            }
        )
        controller = D049Controller()
        steps = 0
        while not bool(observation[5]) and steps < 64:
            decision = controller.command(observation)
            assert decision.mode in {
                D049ControlMode.TERMINAL_SPIN,
                D049ControlMode.CONTACT,
            }
            observation, _, _, _, _ = env.step(
                (decision.wheel_delta_left, decision.wheel_delta_right)
            )
            steps += 1
        assert bool(observation[5])
        max_steps = max(max_steps, steps)
    assert max_steps <= D049_TERMINAL_SPIN_MAX_STEPS


def test_official_protocol_is_deterministic_and_preserves_reward_info() -> None:
    first = run_d049_protocol("a" * 40)
    second = run_d049_protocol("a" * 40)
    assert first == second
    assert first["aggregate"]["case_count"] == 104
    assert first["aggregate"]["successful_cases"] == 104
    for case in first["cases"]:
        assert set(case["reward_values"]) == {0.0}
        assert (
            set(tuple(sorted(info.items())) for info in case["organism_info_values"])
            == {tuple()}
        )
        assert set(case["transition_authority"]) == {"LEVEL_1"}


def test_artifact_bytes_regenerate_identically(tmp_path: object) -> None:
    path_one = tmp_path / "one.json"  # type: ignore[union-attr]
    path_two = tmp_path / "two.json"  # type: ignore[union-attr]
    write_d049_artifact(path_one, "b" * 40)
    write_d049_artifact(path_two, "b" * 40)
    assert path_one.read_bytes() == path_two.read_bytes()
    assert artifact_sha256(path_one) == artifact_sha256(path_two)
