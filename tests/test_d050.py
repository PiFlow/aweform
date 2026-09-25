"""Focused tests for the frozen D-050 paired homing comparison."""

from __future__ import annotations

import math

import numpy as np
import pytest

from aweform.d045 import (
    D045_MAX_WHEEL_DELTA_RAD,
    D045_WHEEL_RADIUS_METRES,
    D045_WHEEL_TRACK_WIDTH_METRES,
    D045Env,
)
from aweform.d049 import (
    D049Controller,
    reconstruct_source,
)
from aweform.d050 import (
    D050_CASE_HORIZON,
    D050_INITIAL_BEARING_ERRORS_RAD,
    D050_POSITION_BEARINGS_DEG,
    D050_RETURN_RADII_M,
    D050Arm,
    D050BaselineController,
    D050ControlMode,
    D050SmoothController,
    artifact_sha256,
    curved_pursuit_command,
    frozen_cases,
    run_d050_protocol,
    write_d050_artifact,
)


def _observation(
    left: float, forward: float, right: float, contact: float = 0.0
) -> np.ndarray:
    return np.asarray(
        [0.5, 0.2875, left, forward, right, contact, 0.0, 0.0],
        dtype=np.float32,
    )


def test_frozen_matrix_is_exactly_the_authorized_96_pairs() -> None:
    cases = frozen_cases()
    assert len(cases) == 96
    assert {case.radius_m for case in cases} == set(D050_RETURN_RADII_M)
    assert {case.position_bearing_deg for case in cases} == set(
        D050_POSITION_BEARINGS_DEG
    )
    assert {case.initial_bearing_error_rad for case in cases} == set(
        D050_INITIAL_BEARING_ERRORS_RAD
    )
    assert D050_CASE_HORIZON == 256


def test_baseline_is_a_direct_d049_decision_adapter() -> None:
    fixtures = (
        _observation(0.8, 0.85, 0.79),
        _observation(0.2, 0.5, 0.2),
        _observation(0.9, 0.92, 0.9),
        _observation(0.5, 0.5, 0.5),
        _observation(0.5, 0.5, 0.5, 1.0),
    )
    for observation in fixtures:
        expected = D049Controller().command(observation)
        actual = D050BaselineController().command(observation)
        assert actual.mode.value == expected.mode.value
        assert actual.wheel_delta_left == expected.wheel_delta_left
        assert actual.wheel_delta_right == expected.wheel_delta_right
        assert actual.reconstruction == expected.reconstruction


def test_curved_law_has_expected_units_sign_and_forward_gate() -> None:
    positive = reconstruct_source(0.8, 0.85, 0.79)
    negative = reconstruct_source(0.79, 0.85, 0.8)
    assert positive is not None and negative is not None
    left, right = curved_pursuit_command(positive)
    assert left < right
    left_negative, right_negative = curved_pursuit_command(negative)
    assert left_negative > right_negative

    behind = reconstruct_source(0.5, 0.2, 0.5)
    assert behind is not None
    assert abs(behind.bearing_rad) >= math.pi / 2.0
    behind_left, behind_right = curved_pursuit_command(behind)
    assert behind_left == pytest.approx(-behind_right)


def test_curved_law_scales_only_when_wheel_envelope_is_exceeded() -> None:
    reconstruction = reconstruct_source(0.2, 0.5, 0.2)
    assert reconstruction is not None
    left, right = curved_pursuit_command(reconstruction)
    assert max(abs(left), abs(right)) <= D045_MAX_WHEEL_DELTA_RAD
    assert max(abs(left), abs(right)) == pytest.approx(D045_MAX_WHEEL_DELTA_RAD)


def test_smooth_arm_combines_forward_and_differential_motion() -> None:
    decision = D050SmoothController().command(_observation(0.8, 0.85, 0.79))
    assert decision.mode is D050ControlMode.CURVED_PURSUIT
    assert decision.wheel_delta_left < decision.wheel_delta_right
    assert decision.wheel_delta_left + decision.wheel_delta_right > 0.0


def test_terminal_and_contact_rules_match_d049() -> None:
    centered = _observation(0.5, 0.5, 0.5)
    contact = _observation(0.0, math.nan, 2.0, 1.0)
    for controller in (D050BaselineController(), D050SmoothController()):
        centered_decision = controller.command(centered)
        assert centered_decision.mode is D050ControlMode.TERMINAL_SPIN
        assert centered_decision.wheel_delta_left == -D045_MAX_WHEEL_DELTA_RAD
        assert centered_decision.wheel_delta_right == D045_MAX_WHEEL_DELTA_RAD
        contact_decision = controller.command(contact)
        assert contact_decision.mode is D050ControlMode.CONTACT
        assert (
            contact_decision.wheel_delta_left,
            contact_decision.wheel_delta_right,
        ) == (
            0.0,
            0.0,
        )


def test_initial_pair_states_are_field_equivalent() -> None:
    case = frozen_cases()[17]
    observations = []
    for _ in D050Arm:
        env = D045Env()
        observation, info = env.reset(
            options={
                "body_position": case.body_position,
                "station_center": (0.5, 0.5),
                "heading": case.heading_rad,
            }
        )
        assert info == {}
        assert env.body is not None
        observations.append(
            (observation.tobytes(), env.body.position, env.body.heading)
        )
    assert observations[0] == observations[1]


def test_protocol_is_deterministic_and_preserves_boundary() -> None:
    first = run_d050_protocol("a" * 40)
    second = run_d050_protocol("a" * 40)
    assert first == second
    assert first["validation"]["exact_case_count"] is True
    assert first["validation"]["fresh_environment_order_invariant"] is True
    assert first["aggregate"]["paired_case_count"] == 96
    for pair in first["pairs"]:
        for arm_name in ("baseline", "smooth"):
            result = pair[arm_name]
            assert set(result["reward_values"]) == {0.0}
            assert all(info == {} for info in result["organism_info_values"])
            assert set(result["transition_authority"]) == {"LEVEL_1"}
            assert len(result["trace"]) == result["transition_count"] + 1


def test_artifact_bytes_regenerate_identically(tmp_path: object) -> None:
    path_one = tmp_path / "one.json"  # type: ignore[union-attr]
    path_two = tmp_path / "two.json"  # type: ignore[union-attr]
    write_d050_artifact(path_one, "b" * 40)
    write_d050_artifact(path_two, "b" * 40)
    assert path_one.read_bytes() == path_two.read_bytes()
    assert artifact_sha256(path_one) == artifact_sha256(path_two)


def test_d045_kinematics_constants_are_the_law_constants() -> None:
    assert D045_WHEEL_RADIUS_METRES > 0.0
    assert D045_WHEEL_TRACK_WIDTH_METRES > 0.0
