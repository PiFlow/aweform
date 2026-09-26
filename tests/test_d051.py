"""Focused tests for the D-051 numerical-switching attribution audit."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Callable

import numpy as np
import pytest

from aweform.d045 import (
    D045_WHEEL_RADIUS_METRES,
    D045_WHEEL_TRACK_WIDTH_METRES,
    D045Env,
    D045PhysicalConfig,
    _body_contact_point,
)
from aweform.d049 import D049_STATION_CENTER, D049Controller, reconstruct_source
from aweform.d050 import (
    D050_INITIAL_BEARING_ERRORS_RAD,
    D050_POSITION_BEARINGS_DEG,
    D050_RETURN_RADII_M,
    D050Arm,
    D050SmoothController,
)
from aweform.d050 import _run_arm as _run_d050_arm
from aweform.d050 import frozen_cases as d050_frozen_cases
from aweform.d051 import (
    D051_FRESH_INITIAL_BEARING_ERRORS_RAD,
    D051_FRESH_POSITION_BEARINGS_DEG,
    D051_FRESH_RADII_M,
    D051Arm,
    D051UncertaintyController,
    _legal_float32_candidates,
    _original_threshold_turn_uncertainty_treatment_straight,
    artifact_sha256,
    float32_uncertainty_envelope,
    frozen_cases,
    run_d051_protocol,
    write_d051_artifact,
)
from aweform.d051 import _run_arm as _run_d051_arm


def _observation(
    left: float, forward: float, right: float, contact: float = 0.0
) -> np.ndarray:
    return np.asarray(
        [0.5, 0.2875, left, forward, right, contact, 0.0, 0.0],
        dtype=np.float32,
    )


def test_frozen_supports_are_exactly_96_historical_and_80_fresh_cases() -> None:
    cases = frozen_cases()
    assert len(cases) == 176
    historical = [case for case in cases if case.support == "historical_d050"]
    fresh = [case for case in cases if case.support == "fresh_holdout"]
    assert len(historical) == 96
    assert len(fresh) == 80
    assert {case.radius_m for case in historical} == set(D050_RETURN_RADII_M)
    assert {case.position_bearing_deg for case in historical} == set(
        D050_POSITION_BEARINGS_DEG
    )
    assert {case.initial_bearing_error_rad for case in historical} == set(
        D050_INITIAL_BEARING_ERRORS_RAD
    )
    assert {case.radius_m for case in fresh} == set(D051_FRESH_RADII_M)
    assert {case.position_bearing_deg for case in fresh} == set(
        D051_FRESH_POSITION_BEARINGS_DEG
    )
    assert {case.initial_bearing_error_rad for case in fresh} == set(
        D051_FRESH_INITIAL_BEARING_ERRORS_RAD
    )


def test_float32_candidate_sets_use_actual_previous_current_next_values() -> None:
    current = np.float32(0.5)
    candidates = _legal_float32_candidates(float(current))
    assert len(candidates) == 3
    assert candidates[0] == float(np.nextafter(current, np.float32(0.0)))
    assert candidates[1] == float(current)
    assert candidates[2] == float(np.nextafter(current, np.float32(np.inf)))
    assert all(0.0 < value <= 1.0 for value in candidates)
    assert _legal_float32_candidates(1.0)[-1] == 1.0
    assert _legal_float32_candidates(0.0) == (
        float(np.nextafter(np.float32(0.0), np.float32(np.inf))),
    )


def test_uncertainty_envelope_is_wrapped_and_at_most_27_candidates() -> None:
    envelope = float32_uncertainty_envelope(
        0.8697801828384399,
        0.8731265664100647,
        0.8697802424430847,
    )
    assert envelope is not None
    assert envelope.candidate_count <= 27
    assert envelope.valid_candidate_count <= envelope.candidate_count
    assert envelope.effective_angular_tolerance_rad >= 1.0e-6
    assert not envelope.fallback
    assert math.isfinite(envelope.epsilon_float32)


def test_arm_b_changes_only_the_declared_switching_decision() -> None:
    observation = _observation(
        0.8697801828384399,
        0.8731265664100647,
        0.8697802424430847,
    )
    baseline = D049Controller().command(observation)
    treatment = D051UncertaintyController().command(observation)
    assert baseline.mode.value == "TURN"
    assert treatment.mode.value == "STRAIGHT"
    assert treatment.effective_angular_tolerance_rad > abs(
        baseline.reconstruction.bearing_rad  # type: ignore[union-attr]
    )
    epsilon = treatment.epsilon_float32
    assert epsilon is not None
    assert _original_threshold_turn_uncertainty_treatment_straight(
        baseline.reconstruction, epsilon
    ) is True


def test_counterfactual_treatment_uses_uncertainty_in_arm_a_too() -> None:
    observation = _observation(
        0.8697801828384399,
        0.8731265664100647,
        0.8697802424430847,
    )
    baseline = D049Controller().command(observation)
    reconstruction = reconstruct_source(*map(float, observation[2:5]))
    assert baseline.mode.value == "TURN"
    assert reconstruction is not None
    assert abs(reconstruction.bearing_rad) > 1.0e-6
    assert _original_threshold_turn_uncertainty_treatment_straight(
        reconstruction, 7.406479158013211e-6
    ) is True
    assert _original_threshold_turn_uncertainty_treatment_straight(
        reconstruction, 1.0e-6
    ) is False


def _arm_c_first_contact_diagnostic(
    actual_artifact: dict[str, object],
) -> str:
    reference_path = (
        Path(__file__).resolve().parents[1]
        / "development/D-050-level1-homing-controller-comparison.json"
    )
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    expected_pair = reference["pairs"][0]
    expected_arm = expected_pair["smooth"]
    expected_trace = {entry["step"]: entry for entry in expected_arm["trace"]}
    actual_pair = actual_artifact["pairs"][0]
    actual_arm = actual_pair["arms"][D051Arm.D050_SMOOTH_REFERENCE.value]
    actual_trace = {entry["step"]: entry for entry in actual_arm["trace"]}
    first_trace_difference = None
    for step, expected in expected_trace.items():
        actual = actual_trace[step]
        differing = {
            key: {"expected": expected[key], "actual": actual[key]}
            for key in ("x", "y", "heading", "charging_contact")
            if expected[key] != actual[key]
        }
        if differing:
            first_trace_difference = {"step": step, "fields": differing}
            break

    case = frozen_cases()[0]
    environment = D045Env(D045PhysicalConfig(episode_horizon=256))
    observation, _ = environment.reset(
        options={
            "body_position": case.body_position,
            "station_center": D049_STATION_CENTER,
            "heading": case.heading_rad,
        }
    )
    controller = D050SmoothController()
    contact_capture: dict[str, object] | None = None
    for _ in range(256):
        decision = controller.command(observation)
        observation, _, _, _, _ = environment.step(
            (decision.wheel_delta_left, decision.wheel_delta_right)
        )
        telemetry = environment.last_transition
        assert telemetry is not None
        if telemetry.charging_contact_after and not telemetry.charging_contact_before:
            plus_point = _body_contact_point(
                telemetry.position_after, telemetry.heading_after, (0.0, 0.05)
            )
            minus_point = _body_contact_point(
                telemetry.position_after, telemetry.heading_after, (0.0, -0.05)
            )
            plus_station = (D049_STATION_CENTER[0], D049_STATION_CENTER[1] + 0.05)
            minus_station = (D049_STATION_CENTER[0], D049_STATION_CENTER[1] - 0.05)
            wheel_left_distance = (
                D045_WHEEL_RADIUS_METRES * telemetry.actual_delta_left
            )
            wheel_right_distance = (
                D045_WHEEL_RADIUS_METRES * telemetry.actual_delta_right
            )
            d_s = (wheel_left_distance + wheel_right_distance) / 2.0
            d_theta = (
                wheel_right_distance - wheel_left_distance
            ) / D045_WHEEL_TRACK_WIDTH_METRES
            contact_capture = {
                "step": telemetry.step_index,
                "expected_contact_pair_error_m": expected_arm[
                    "contact_pair_error_at_first_contact_m"
                ],
                "expected_contact_pair_error_hex": [
                    float(value).hex()
                    for value in expected_arm[
                        "contact_pair_error_at_first_contact_m"
                    ]
                ],
                "actual_plus_contact_error_raw_m": telemetry.dock_plus_error_m,
                "actual_minus_contact_error_raw_m": telemetry.dock_minus_error_m,
                "actual_contact_pair_error_raw_m": [
                    telemetry.dock_plus_error_m,
                    telemetry.dock_minus_error_m,
                ],
                "actual_contact_pair_error_hex": [
                    telemetry.dock_plus_error_m.hex(),
                    telemetry.dock_minus_error_m.hex(),
                ],
                "pose_before": {
                    "position": telemetry.position_before,
                    "position_hex": [v.hex() for v in telemetry.position_before],
                    "heading": telemetry.heading_before,
                    "heading_hex": telemetry.heading_before.hex(),
                },
                "pose_after": {
                    "position": telemetry.position_after,
                    "position_hex": [v.hex() for v in telemetry.position_after],
                    "heading": telemetry.heading_after,
                    "heading_hex": telemetry.heading_after.hex(),
                },
                "requested_wheels": [
                    decision.wheel_delta_left,
                    decision.wheel_delta_right,
                ],
                "actual_wheels": [
                    telemetry.actual_delta_left,
                    telemetry.actual_delta_right,
                ],
                "actual_wheels_hex": [
                    telemetry.actual_delta_left.hex(),
                    telemetry.actual_delta_right.hex(),
                ],
                "boundary_scale": telemetry.boundary_scale,
                "arc_intermediates": {
                    "wheel_left_distance": wheel_left_distance,
                    "wheel_right_distance": wheel_right_distance,
                    "d_s": d_s,
                    "d_theta": d_theta,
                    "next_heading": telemetry.heading_before + d_theta,
                    "sin_heading_before": math.sin(telemetry.heading_before),
                    "cos_heading_before": math.cos(telemetry.heading_before),
                    "sin_heading_after": math.sin(telemetry.heading_after),
                    "cos_heading_after": math.cos(telemetry.heading_after),
                },
                "arc_intermediates_hex": {
                    key: value.hex()
                    for key, value in {
                        "wheel_left_distance": wheel_left_distance,
                        "wheel_right_distance": wheel_right_distance,
                        "d_s": d_s,
                        "d_theta": d_theta,
                        "next_heading": telemetry.heading_before + d_theta,
                        "sin_heading_before": math.sin(telemetry.heading_before),
                        "cos_heading_before": math.cos(telemetry.heading_before),
                        "sin_heading_after": math.sin(telemetry.heading_after),
                        "cos_heading_after": math.cos(telemetry.heading_after),
                    }.items()
                },
                "contact_points_raw": {
                    "plus": plus_point,
                    "minus": minus_point,
                    "station_plus": plus_station,
                    "station_minus": minus_station,
                },
            }
            break

    if contact_capture is None:
        return "Arm-C diagnostic failed to reach first contact"
    return json.dumps(
        {
            "first_trace_difference": first_trace_difference,
            "first_contact_transition": contact_capture,
            "first_replay_mismatch": actual_artifact["historical_replay"][
                "mismatches"
            ][0],
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _run_with_step_capture(
    monkeypatch: pytest.MonkeyPatch,
    runner: Callable[[], dict[str, object]],
) -> tuple[dict[str, object], list[dict[str, object]]]:
    captured: list[dict[str, object]] = []
    original_step = D045Env.step

    def capture_step(
        environment: D045Env, action: tuple[float, float]
    ) -> tuple[np.ndarray, float, bool, bool, dict[str, object]]:
        observation_before = environment._observation().as_array()
        result = original_step(environment, action)
        telemetry = environment.last_transition
        assert telemetry is not None
        captured.append(
            {
                "step": telemetry.step_index,
                "observation_before": [float(value) for value in observation_before],
                "observation_before_hex": [
                    float(value).hex() for value in observation_before
                ],
                "requested_wheels": list(action),
                "requested_wheels_hex": [value.hex() for value in action],
                "actual_wheels": [
                    telemetry.actual_delta_left,
                    telemetry.actual_delta_right,
                ],
                "actual_wheels_hex": [
                    telemetry.actual_delta_left.hex(),
                    telemetry.actual_delta_right.hex(),
                ],
                "position_before": telemetry.position_before,
                "position_after": telemetry.position_after,
                "position_after_hex": [
                    value.hex() for value in telemetry.position_after
                ],
                "heading_before": telemetry.heading_before,
                "heading_after": telemetry.heading_after,
                "heading_after_hex": telemetry.heading_after.hex(),
                "charging_contact_after": telemetry.charging_contact_after,
                "contact_errors_raw": (
                    telemetry.dock_plus_error_m,
                    telemetry.dock_minus_error_m,
                ),
                "contact_errors_hex": (
                    telemetry.dock_plus_error_m.hex(),
                    telemetry.dock_minus_error_m.hex(),
                ),
            }
        )
        return result

    with monkeypatch.context() as patch:
        patch.setattr(D045Env, "step", capture_step)
        result = runner()
    return result, captured


def _first_step_record_difference(
    first: list[dict[str, object]], second: list[dict[str, object]]
) -> dict[str, object] | None:
    for index, (first_step, second_step) in enumerate(zip(first, second)):
        for field in first_step:
            if first_step[field] != second_step[field]:
                return {
                    "index": index,
                    "step": first_step["step"],
                    "field": field,
                    "d050": first_step[field],
                    "d051": second_step[field],
                }
    if len(first) != len(second):
        return {"length_d050": len(first), "length_d051": len(second)}
    return None


def _d050_vs_d051_runner_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
) -> str:
    reference_path = (
        Path(__file__).resolve().parents[1]
        / "development/D-050-level1-homing-controller-comparison.json"
    )
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    expected_arm = reference["pairs"][0]["smooth"]
    d050_case = d050_frozen_cases()[0]
    d051_case = frozen_cases()[0]
    d050_result, d050_steps = _run_with_step_capture(
        monkeypatch, lambda: _run_d050_arm(d050_case, D050Arm.SMOOTH)
    )
    d051_result, d051_steps = _run_with_step_capture(
        monkeypatch,
        lambda: _run_d051_arm(
            d051_case, D051Arm.D050_SMOOTH_REFERENCE, collect_diagnostics=False
        ),
    )

    def value_record(value: float) -> dict[str, object]:
        return {"repr": repr(value), "hex": value.hex()}

    expected_step_two_y = float(expected_arm["trace"][2]["y"])
    d050_step_two_y = float(d050_result["trace"][2]["y"])
    d051_step_two_y = float(d051_result["trace"][2]["y"])
    expected_contact = expected_arm["contact_pair_error_at_first_contact_m"]
    d050_contact = d050_result["contact_pair_error_at_first_contact_m"]
    d051_contact = d051_result["contact_pair_error_at_first_contact_m"]
    return json.dumps(
        {
            "case_id": expected_arm["initial_state"]["case_id"],
            "d050_own_runner_vs_committed_artifact": {
                "trace_step_2_y": {
                    "expected": value_record(expected_step_two_y),
                    "actual": value_record(d050_step_two_y),
                },
                "contact_pair_errors": {
                    "expected": [
                        value_record(float(value)) for value in expected_contact
                    ],
                    "actual": [value_record(float(value)) for value in d050_contact],
                },
            },
            "d051_arm_c_vs_d050_own_runner": {
                "first_step_observation_command_wheel_or_pose_difference": (
                    _first_step_record_difference(d050_steps, d051_steps)
                ),
                "trace_step_2_y": {
                    "d050": value_record(d050_step_two_y),
                    "d051": value_record(d051_step_two_y),
                },
                "contact_pair_errors": {
                    "d050": [value_record(float(value)) for value in d050_contact],
                    "d051": [value_record(float(value)) for value in d051_contact],
                },
            },
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def test_d050_and_d051_arm_c_case_runner_paths_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    diagnostic = json.loads(_d050_vs_d051_runner_diagnostic(monkeypatch))
    comparison = diagnostic["d051_arm_c_vs_d050_own_runner"]
    assert comparison["first_step_observation_command_wheel_or_pose_difference"] is None


def test_protocol_replays_d050_and_preserves_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact = run_d051_protocol("a" * 40)
    validation = artifact["validation"]
    assert validation["exact_historical_case_count"] is True
    assert validation["exact_fresh_case_count"] is True
    assert validation["historical_baseline_behavioral_identity"] is True
    assert validation["historical_smooth_behavioral_identity"] is True, (
        _arm_c_first_contact_diagnostic(artifact)
        + " D050-vs-D051="
        + _d050_vs_d051_runner_diagnostic(monkeypatch)
    )
    assert validation["diagnostic_instrumentation_causal_identity"] is True
    assert validation["diagnostic_instrumentation_check_count"] == 6
    assert validation["branch_order_causal_identity"] is True
    assert validation["branch_order_check_count"] == 6
    assert validation["reward_exactly_zero"] is True
    assert validation["organism_info_exactly_empty"] is True
    assert validation["level1_authority_on_every_transition"] is True
    pairs = artifact["pairs"]
    assert len(pairs) == 176
    first = pairs[0]["arms"]
    assert len(first[D051Arm.ORIGINAL_BASELINE.value]["diagnostics"]) > 0
    assert len(first[D051Arm.FLOAT32_UNCERTAINTY_TREATMENT.value]["diagnostics"]) > 0
    assert first[D051Arm.D050_SMOOTH_REFERENCE.value]["diagnostics"] == []


def test_artifact_regeneration_is_byte_identical(tmp_path: object) -> None:
    path_one = tmp_path / "one.json"  # type: ignore[union-attr]
    path_two = tmp_path / "two.json"  # type: ignore[union-attr]
    write_d051_artifact(path_one, "b" * 40)
    write_d051_artifact(path_two, "b" * 40)
    assert path_one.read_bytes() == path_two.read_bytes()  # type: ignore[union-attr]
    assert artifact_sha256(path_one) == artifact_sha256(path_two)
