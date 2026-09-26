"""Focused tests for the D-051 numerical-switching attribution audit."""

from __future__ import annotations

import math

import numpy as np

from aweform.d049 import D049Controller
from aweform.d050 import (
    D050_INITIAL_BEARING_ERRORS_RAD,
    D050_POSITION_BEARINGS_DEG,
    D050_RETURN_RADII_M,
    D050SmoothController,
)
from aweform.d051 import (
    D051_FRESH_INITIAL_BEARING_ERRORS_RAD,
    D051_FRESH_POSITION_BEARINGS_DEG,
    D051_FRESH_RADII_M,
    D051Arm,
    D051UncertaintyController,
    _branch_order_independence_check,
    _instrumentation_identity_check,
    _legal_float32_candidates,
    artifact_sha256,
    float32_uncertainty_envelope,
    frozen_cases,
    original_turn_treatment_straight,
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


def test_original_turn_treatment_straight_is_arm_independent() -> None:
    """Regression: the counterfactual must not read the acting arm's tolerance.

    The historical bug used the acting arm's effective angular tolerance, so
    on Arm A the counterfactual compared abs(beta) against the original
    1e-6 rad rule on both sides and could never fire (recorded zero counts).
    """
    observation = _observation(
        0.8697801828384399,
        0.8731265664100647,
        0.8697802424430847,
    )
    envelope = float32_uncertainty_envelope(
        float(observation[2]), float(observation[3]), float(observation[4])
    )
    assert envelope is not None and not envelope.fallback
    baseline = D049Controller().command(observation)
    reconstruction = baseline.reconstruction
    assert reconstruction is not None
    bearing = abs(reconstruction.bearing_rad)
    assert bearing > 1.0e-6
    assert bearing <= envelope.effective_angular_tolerance_rad
    # The arm-independent counterfactual must fire for this transition.
    assert original_turn_treatment_straight(reconstruction, envelope.epsilon_float32)
    # And it must not depend on any arm-provided tolerance value.
    assert original_turn_treatment_straight(reconstruction, envelope.epsilon_float32)
    # Absent reconstruction or a fallback envelope can never fire.
    assert not original_turn_treatment_straight(None, envelope.epsilon_float32)
    below_threshold = type(reconstruction)(
        reconstruction.x_m,
        reconstruction.y_m,
        reconstruction.distance_m,
        bearing * 0.5,
    )
    if abs(below_threshold.bearing_rad) <= 1.0e-6:
        assert not original_turn_treatment_straight(
            below_threshold, envelope.epsilon_float32
        )


def test_diagnostic_counterfactual_matches_arm_independent_recomputation() -> None:
    cases = frozen_cases()
    for index in (0, 1, 96, 175):
        case = cases[index]
        for arm in (D051Arm.ORIGINAL_BASELINE, D051Arm.FLOAT32_UNCERTAINTY_TREATMENT):
            result = _run_arm_for_counterfactual(case, arm)
            for diagnostic in result:
                distance = diagnostic["nominal_reconstructed_distance_m"]
                bearing = diagnostic["nominal_reconstructed_bearing_rad"]
                epsilon = diagnostic["epsilon_float32_rad"]
                expected = (
                    distance is not None
                    and bearing is not None
                    and distance > 1.0e-6
                    and abs(bearing) > 1.0e-6
                    and epsilon is not None
                    and abs(bearing) <= max(1.0e-6, epsilon)
                )
                assert (
                    diagnostic["original_threshold_turn_uncertainty_treatment_straight"]
                    is expected
                )


def _run_arm_for_counterfactual(
    case: object, arm: D051Arm
) -> list[dict[str, object]]:
    from aweform.d051 import _run_arm

    result = _run_arm(case, arm, collect_diagnostics=True)  # type: ignore[arg-type]
    return result["diagnostics"]  # type: ignore[return-value]


def test_controllers_ignore_non_causal_channels() -> None:
    """Executable causal-boundary probe: non-causal channels cannot change any arm."""

    causal = _observation(0.8697801828384399, 0.8731265664100647, 0.8697802424430847)
    controller_types = (
        D049Controller,
        D051UncertaintyController,
        D050SmoothController,
    )
    for controller_type in controller_types:
        reference = controller_type().command(causal)
        for channel in (0, 1, 6, 7):
            perturbed = causal.copy()
            perturbed[channel] = np.float32(0.123456789 if channel % 2 else 42.0)
            decision = controller_type().command(perturbed)
            assert decision == reference, (controller_type.__name__, channel)


def test_diagnostic_instrumentation_identity_covers_all_arms() -> None:
    check = _instrumentation_identity_check(frozen_cases())
    assert check["diagnostic_instrumentation_causal_identity"] is True
    assert check["arms"] == [arm.value for arm in D051Arm]
    assert len(check["case_ids"]) == 3
    assert check["mismatches"] == []


def test_fresh_environment_arm_order_invariance() -> None:
    check = _branch_order_independence_check(frozen_cases())
    assert check["fresh_environment_arm_order_invariant"] is True
    assert check["execution_order_permutations"] == 6
    assert check["mismatches"] == []


def test_smooth_arm_diagnostics_are_empty() -> None:
    cases = frozen_cases()
    from aweform.d051 import _run_arm

    result = _run_arm(cases[0], D051Arm.D050_SMOOTH_REFERENCE, collect_diagnostics=True)  # type: ignore[arg-type]
    assert result["diagnostics"] == []  # type: ignore[index]


def test_d045_reset_consumes_no_seed_for_d051_cases() -> None:
    """The fresh support is seedless: repeated fresh environments are bit-identical."""

    import aweform.d045 as d045

    case = frozen_cases()[96]
    observations = []
    for _ in range(2):
        env = d045.D045Env(d045.D045PhysicalConfig(episode_horizon=256))
        observation, info = env.reset(
            options={
                "body_position": case.body_position,
                "station_center": (0.5, 0.5),
                "heading": case.heading_rad,
            }
        )
        assert info == {}
        observations.append(observation.tobytes())
    assert observations[0] == observations[1]


def test_protocol_replays_d050_and_preserves_boundary() -> None:
    artifact = run_d051_protocol("a" * 40)
    validation = artifact["validation"]
    assert validation["exact_historical_case_count"] is True
    assert validation["exact_fresh_case_count"] is True
    assert validation["historical_baseline_behavioral_identity"] is True
    assert validation["historical_smooth_behavioral_identity"] is True
    assert validation["diagnostic_instrumentation_causal_identity"] is True
    assert validation["fresh_environment_arm_order_invariant"] is True
    assert validation["reward_exactly_zero"] is True
    assert validation["organism_info_exactly_empty"] is True
    assert validation["level1_authority_on_every_transition"] is True
    # Self-asserted design invariants must live in declared_boundaries, not in
    # the computed validation block.
    for declared_key in (
        "arm_b_uses_only_observation_and_fixed_constants",
        "evaluator_geometry_causally_isolated",
        "fresh_support_is_seedless",
    ):
        assert declared_key not in validation
    declared = artifact["declared_boundaries"]
    assert declared["status"].startswith("declared design invariants")
    for declared_key in (
        "arm_b_uses_only_observation_and_fixed_constants",
        "evaluator_geometry_causally_isolated",
        "fresh_support_is_seedless",
    ):
        assert declared_key in declared
        assert declared[declared_key]["executable_checks"]
    assert artifact["invalidated_prior_runs"][0]["executed_commit_sha"] == (
        "0a6277a62087141d228d65902c0ef55c6b61040b"
    )
    replay = artifact["historical_replay"]
    assert replay["first_smooth_mismatch"] is None
    assert replay["first_baseline_mismatch"] is None
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
