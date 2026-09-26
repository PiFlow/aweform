"""Focused tests for the D-051 numerical-switching attribution audit."""

from __future__ import annotations

import math

import numpy as np

from aweform.d049 import D049Controller
from aweform.d050 import (
    D050_INITIAL_BEARING_ERRORS_RAD,
    D050_POSITION_BEARINGS_DEG,
    D050_RETURN_RADII_M,
)
from aweform.d051 import (
    D051_FRESH_INITIAL_BEARING_ERRORS_RAD,
    D051_FRESH_POSITION_BEARINGS_DEG,
    D051_FRESH_RADII_M,
    D051Arm,
    D051UncertaintyController,
    _counterfactual_original_turn_uncertainty_straight,
    _legal_float32_candidates,
    _run_arm,
    artifact_sha256,
    float32_uncertainty_envelope,
    frozen_cases,
    run_d051_protocol,
    write_d051_artifact,
)


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


def test_counterfactual_diagnostic_is_arm_independent() -> None:
    case = next(
        case
        for case in frozen_cases()
        if case.case_id == "direct-r0.15-p022.5-e02"
    )
    baseline = _run_arm(case, D051Arm.ORIGINAL_BASELINE)
    treatment = _run_arm(case, D051Arm.FLOAT32_UNCERTAINTY_TREATMENT)
    baseline_count = baseline["original_threshold_turn_treatment_straight_count"]
    treatment_count = treatment["original_threshold_turn_treatment_straight_count"]
    assert baseline_count == treatment_count == 1


def test_counterfactual_excludes_centre_and_uses_declared_thresholds() -> None:
    observation = _observation(
        0.8697801828384399,
        0.8731265664100647,
        0.8697802424430847,
    )
    baseline = D049Controller().command(observation)
    assert baseline.reconstruction is not None
    envelope = float32_uncertainty_envelope(
        float(observation[2]), float(observation[3]), float(observation[4])
    )
    assert envelope is not None
    assert _counterfactual_original_turn_uncertainty_straight(
        baseline.reconstruction, envelope
    )
    assert not _counterfactual_original_turn_uncertainty_straight(
        baseline.reconstruction.__class__(
            baseline.reconstruction.x_m,
            baseline.reconstruction.y_m,
            1.0e-7,
            baseline.reconstruction.bearing_rad,
        ),
        envelope,
    )


def test_protocol_replays_d050_and_preserves_boundary() -> None:
    artifact = run_d051_protocol("a" * 40)
    validation = artifact["validation"]
    assert validation["exact_historical_case_count"] is True
    assert validation["exact_fresh_case_count"] is True
    assert validation["historical_baseline_behavioral_identity"] is True
    assert validation["historical_smooth_behavioral_identity"] is True, artifact[
        "historical_replay"
    ]["first_mismatch"]
    assert validation["diagnostic_instrumentation_causal_identity"] is True
    assert validation["diagnostic_instrumentation_case_count"] == 2
    assert validation["diagnostic_instrumentation_arm_count"] == 3
    assert validation["fresh_environment_branch_order_causal_identity"] is True
    assert validation["fresh_environment_branch_order_case_count"] == 80
    assert validation["fresh_environment_branch_order_count"] == 2
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
