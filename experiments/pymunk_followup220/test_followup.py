"""Frozen tests for the issue #220 corrected calibration diagnostic."""

from __future__ import annotations

import math
import sys
from typing import cast

import pytest

pytest.importorskip("pymunk")

from experiments.pymunk_followup220.oracle import differential_drive_arc
from experiments.pymunk_followup220.probe import (
    CANDIDATES,
    DT_SECONDS,
    ENCODER_QUANTUM_RAD,
    MAX_WHEEL_DELTA_RAD,
    CandidateId,
    PymunkFollowupProbe,
    clip_wheel_action,
    quantize_encoder,
)
from experiments.pymunk_followup220.run_diagnostic import (
    HISTORICAL_GATE_STATUS,
    evaluate_candidate,
    evaluate_encoder_checks,
    evaluate_invalid_checks,
    evaluate_preservation_gate,
    experiment_production_imports,
    historical_c0_record,
    independent_clipped_action,
    runtime_source_violations,
)


@pytest.mark.parametrize("candidate_id", CANDIDATES)
def test_frozen_candidate_matrix_and_every_new_gate_pass(
    candidate_id: CandidateId,
) -> None:
    result = evaluate_candidate(candidate_id)
    assert len(result.cases) == 216
    assert all(case.status == "PASS" for case in result.cases)
    assert all(gate.status == "PASS" for gate in result.gates)
    assert all(check.status == "PASS" for check in result.metamorphic_checks)
    assert all(check.status == "PASS" for check in result.known_vector_checks)
    assert all(check.status == "PASS" for check in result.clipping_checks)
    assert all(check.status == "PASS" for check in result.tiny_input_checks)
    assert all(check.status == "PASS" for check in result.invalid_input_checks)
    assert all(check.status == "PASS" for check in result.encoder_checks)
    assert all(check.status == "PASS" for check in result.convergence_checks)
    assert result.repeatability.byte_identical


def test_known_vectors_are_independent_of_free_space_aggregate() -> None:
    expected_distance = 0.045 * MAX_WHEEL_DELTA_RAD
    expected_yaw = 0.045 * (2.0 * MAX_WHEEL_DELTA_RAD) / 0.185
    position, heading = differential_drive_arc(
        (0.0, 0.0), 0.0, MAX_WHEEL_DELTA_RAD, MAX_WHEEL_DELTA_RAD
    )
    assert position == pytest.approx((expected_distance, 0.0), abs=1e-15)
    assert heading == pytest.approx(0.0, abs=1e-15)
    _, positive_spin = differential_drive_arc(
        (0.0, 0.0), 0.0, -MAX_WHEEL_DELTA_RAD, MAX_WHEEL_DELTA_RAD
    )
    _, negative_spin = differential_drive_arc(
        (0.0, 0.0), 0.0, MAX_WHEEL_DELTA_RAD, -MAX_WHEEL_DELTA_RAD
    )
    assert positive_spin == pytest.approx(expected_yaw, abs=1e-15)
    assert negative_spin == pytest.approx(-expected_yaw, abs=1e-15)
    assert expected_yaw == pytest.approx(math.pi / 10.0, abs=1e-15)


def test_invalid_inputs_reject_without_advancing_either_candidate() -> None:
    for candidate_id in CANDIDATES:
        checks = evaluate_invalid_checks(candidate_id)
        assert len(checks) == 14
        assert all(check.status == "PASS" for check in checks)


def test_independent_clipping_and_tiny_inputs_remain_signed() -> None:
    over_range = (2 * MAX_WHEEL_DELTA_RAD, -3 * MAX_WHEEL_DELTA_RAD)
    request, actual = clip_wheel_action(over_range)
    assert request == (2 * MAX_WHEEL_DELTA_RAD, -3 * MAX_WHEEL_DELTA_RAD)
    assert actual == (MAX_WHEEL_DELTA_RAD, -MAX_WHEEL_DELTA_RAD)
    assert independent_clipped_action(over_range) == (
        MAX_WHEEL_DELTA_RAD,
        -MAX_WHEEL_DELTA_RAD,
    )
    for candidate_id in CANDIDATES:
        probe = PymunkFollowupProbe(candidate_id)
        endpoint = probe.advance((1e-15, -1e-15))
        assert endpoint.actual_shaft_deltas_rad == (1e-15, -1e-15)
        assert endpoint.engine_step_count == 10
        assert probe.elapsed_seconds == DT_SECONDS


def test_encoder_half_quantum_ties_round_away_from_zero() -> None:
    q = ENCODER_QUANTUM_RAD
    inputs = (
        math.nextafter(0.5 * q, 0.0),
        math.nextafter(0.5 * q, math.inf),
        0.5 * q,
        math.nextafter(-0.5 * q, 0.0),
        math.nextafter(-0.5 * q, -math.inf),
        -0.5 * q,
    )
    expected = (0.0, q, q, 0.0, -q, -q)
    assert tuple(quantize_encoder(value) for value in inputs) == expected
    for candidate_id in CANDIDATES:
        checks = evaluate_encoder_checks(candidate_id)
        assert len(checks) == 6
        assert all(check.status == "PASS" for check in checks)


def test_historical_c0_remains_a_recorded_fail_not_a_rerun() -> None:
    record = historical_c0_record()
    assert record["candidate_id"] == "C0_T1_HISTORICAL"
    assert record["rerun"] is False
    assert record["recorded_gates"] == HISTORICAL_GATE_STATUS
    assert record["case_count"] == 92
    assert record["case_failures"] == 24
    suite_discrepancy = cast(dict[str, str], record["suite_count_discrepancy"])
    assert suite_discrepancy["status"] == "UNKNOWN_UNRECONCILED"
    preservation = evaluate_preservation_gate(record)
    assert preservation.status == "PASS"


def test_candidate_types_are_frozen_and_pymunk_is_headless() -> None:
    assert CANDIDATES == (
        "C1_MIDPOINT_NOMINAL_SPEED",
        "C2_MIDPOINT_ARC_AVERAGE",
    )
    assert "pygame" not in sys.modules


def test_source_is_headless_and_isolated_from_production() -> None:
    assert runtime_source_violations() == ()
    assert experiment_production_imports() == ()
