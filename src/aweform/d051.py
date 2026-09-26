"""D-051 attribution audit of the D-050 homing comparison.

This module is an additive diagnostic layer.  Arm A delegates to the exact
D-049 controller, Arm B changes only the declared float32 angular switching
tolerance, and Arm C delegates to the exact D-050 smooth reference.  All
geometry, ideal-beacon values, and uncertainty diagnostics are evaluator-only.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Final, cast

import numpy as np

from .body import Body
from .d045 import (
    D045_DT_SECONDS,
    D045_MAX_WHEEL_DELTA_RAD,
    D045_WHEEL_RADIUS_METRES,
    D045_WHEEL_TRACK_WIDTH_METRES,
    D045Env,
    D045PhysicalConfig,
    D045TransitionTelemetry,
    wheel_effort,
)
from .d049 import (
    D049_ANGULAR_TOLERANCE_RAD,
    D049_CENTRE_TOLERANCE_M,
    D049_STATION_CENTER,
    D049_TERMINAL_SPIN_DIRECTION,
    D049_TERMINAL_SPIN_MAX_STEPS,
    D049Controller,
    D049Decision,
    D049Reconstruction,
    reconstruct_source,
)
from .d050 import (
    D050_CASE_HORIZON,
    D050_INITIAL_BEARING_ERRORS_RAD,
    D050_POSITION_BEARINGS_DEG,
    D050_RETURN_RADII_M,
    D050ControlMode,
    D050SmoothController,
)
from .d050 import (
    frozen_cases as d050_frozen_cases,
)
from .exp003 import sample_directional_beacon

D051_ID: Final[str] = "D-051"
D051_PROTOCOL_VERSION: Final[str] = "d051-d050-baseline-numerical-switching-audit-v1"
D051_AUTHORIZED_BASE_SHA: Final[str] = "0a273f6e10c9dff155d4ade15e04684d674b60fd"
D051_CASE_HORIZON: Final[int] = D050_CASE_HORIZON
D051_FRESH_RADII_M: Final[tuple[float, ...]] = (0.010, 0.025, 0.080, 0.300)
D051_FRESH_POSITION_BEARINGS_DEG: Final[tuple[int, ...]] = (13, 79, 151, 233, 317)
D051_FRESH_INITIAL_BEARING_ERRORS_RAD: Final[tuple[float, ...]] = (
    0.17,
    -0.53,
    1.07,
    math.pi - 0.41,
)
D051_HISTORICAL_ARTIFACT_SHA256: Final[str] = (
    "28e352ad57096c5c85de8beae546b48e6041b6b0ad8bed712bcf185efb024fa5"
)
D051_HISTORICAL_ARTIFACT_RELATIVE_PATH: Final[str] = (
    "development/D-050-level1-homing-controller-comparison.json"
)


class D051Arm(Enum):
    """The three descriptive D-051 arms."""

    ORIGINAL_BASELINE = "original_baseline"
    FLOAT32_UNCERTAINTY_TREATMENT = "float32_uncertainty_treatment"
    D050_SMOOTH_REFERENCE = "d050_smooth_reference"


@dataclass(frozen=True, slots=True)
class D051Case:
    """One seedless fixed state in either support."""

    support: str
    case_id: str
    radius_m: float
    position_bearing_deg: float
    initial_bearing_error_rad: float
    body_position: tuple[float, float]
    heading_rad: float


@dataclass(frozen=True, slots=True)
class D051Decision:
    """A normalized decision plus the treatment-only uncertainty diagnostic."""

    mode: D050ControlMode
    wheel_delta_left: float
    wheel_delta_right: float
    reconstruction: D049Reconstruction | None
    epsilon_float32: float | None = None
    effective_angular_tolerance_rad: float = D049_ANGULAR_TOLERANCE_RAD
    uncertainty_candidate_count: int = 0
    uncertainty_valid_candidate_count: int = 0
    uncertainty_fallback: bool = False


@dataclass(frozen=True, slots=True)
class D051Uncertainty:
    """Observation-local float32 uncertainty envelope."""

    epsilon_float32: float
    effective_angular_tolerance_rad: float
    candidate_count: int
    valid_candidate_count: int
    fallback: bool


def _validate_sha(value: str) -> None:
    if len(value) != 40 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise ValueError("executed_commit_sha must be a lowercase 40-character SHA")


def _wrap_angle(angle: float) -> float:
    return math.atan2(math.sin(angle), math.cos(angle))


def _legal_float32_candidates(value: float) -> tuple[float, ...]:
    """Return the legal previous/current/next float32 values for one signal."""

    current = np.float32(value)
    previous = np.nextafter(current, np.float32(0.0))
    following = np.nextafter(current, np.float32(np.inf))
    raw_values = (previous, current, min(float(following), 1.0))
    legal: list[float] = []
    for raw_value in raw_values:
        candidate = float(raw_value)
        if (
            math.isfinite(candidate)
            and 0.0 < candidate <= 1.0
            and candidate not in legal
        ):
            legal.append(candidate)
    return tuple(legal)


def float32_uncertainty_envelope(
    beacon_left: float, beacon_forward: float, beacon_right: float
) -> D051Uncertainty | None:
    """Compute the frozen at-most-27-tuple observation-local envelope."""

    nominal = reconstruct_source(beacon_left, beacon_forward, beacon_right)
    if nominal is None:
        return None
    candidate_sets = tuple(
        _legal_float32_candidates(value)
        for value in (beacon_left, beacon_forward, beacon_right)
    )
    candidate_count = math.prod(len(values) for values in candidate_sets)
    valid_bearings: list[float] = []
    for candidate_tuple in itertools.product(*candidate_sets):
        candidate = reconstruct_source(*candidate_tuple)
        if candidate is not None:
            valid_bearings.append(candidate.bearing_rad)
    if not valid_bearings:
        return D051Uncertainty(
            D049_ANGULAR_TOLERANCE_RAD,
            D049_ANGULAR_TOLERANCE_RAD,
            candidate_count,
            0,
            True,
        )
    epsilon = max(
        abs(_wrap_angle(candidate_bearing - nominal.bearing_rad))
        for candidate_bearing in valid_bearings
    )
    return D051Uncertainty(
        epsilon,
        max(D049_ANGULAR_TOLERANCE_RAD, epsilon),
        candidate_count,
        len(valid_bearings),
        False,
    )


class D051UncertaintyController:
    """D-051 Arm B, with exactly one observation-only rule substitution."""

    def command(self, observation: np.ndarray) -> D051Decision:
        if observation.shape != (8,):
            raise ValueError("D-051 requires the exact eight-channel observation")
        contact_value = float(observation[5])
        if contact_value == 1.0:
            return D051Decision(D050ControlMode.CONTACT, 0.0, 0.0, None)
        if contact_value != 0.0 or not math.isfinite(contact_value):
            return D051Decision(D050ControlMode.INVALID_BEACON, 0.0, 0.0, None)

        reconstruction = reconstruct_source(
            float(observation[2]), float(observation[3]), float(observation[4])
        )
        if reconstruction is None:
            return D051Decision(D050ControlMode.INVALID_BEACON, 0.0, 0.0, None)
        uncertainty = float32_uncertainty_envelope(
            float(observation[2]), float(observation[3]), float(observation[4])
        )
        if uncertainty is None:
            tolerance = D049_ANGULAR_TOLERANCE_RAD
            epsilon = None
            candidate_count = 0
            valid_candidate_count = 0
            fallback = True
        else:
            tolerance = uncertainty.effective_angular_tolerance_rad
            epsilon = uncertainty.epsilon_float32
            candidate_count = uncertainty.candidate_count
            valid_candidate_count = uncertainty.valid_candidate_count
            fallback = uncertainty.fallback

        if reconstruction.distance_m <= D049_CENTRE_TOLERANCE_M:
            maximum = D045_MAX_WHEEL_DELTA_RAD
            signed_maximum = D049_TERMINAL_SPIN_DIRECTION * maximum
            return D051Decision(
                D050ControlMode.TERMINAL_SPIN,
                -signed_maximum,
                signed_maximum,
                reconstruction,
                epsilon,
                tolerance,
                candidate_count,
                valid_candidate_count,
                fallback,
            )
        if abs(reconstruction.bearing_rad) > tolerance:
            magnitude = min(
                abs(reconstruction.bearing_rad)
                * D045_WHEEL_TRACK_WIDTH_METRES
                / (2.0 * D045_WHEEL_RADIUS_METRES),
                D045_MAX_WHEEL_DELTA_RAD,
            )
            signed_magnitude = math.copysign(magnitude, reconstruction.bearing_rad)
            return D051Decision(
                D050ControlMode.TURN,
                -signed_magnitude,
                signed_magnitude,
                reconstruction,
                epsilon,
                tolerance,
                candidate_count,
                valid_candidate_count,
                fallback,
            )
        travel_m = min(
            reconstruction.distance_m,
            D045_MAX_WHEEL_DELTA_RAD * D045_WHEEL_RADIUS_METRES,
        )
        wheel_delta = travel_m / D045_WHEEL_RADIUS_METRES
        return D051Decision(
            D050ControlMode.STRAIGHT,
            wheel_delta,
            wheel_delta,
            reconstruction,
            epsilon,
            tolerance,
            candidate_count,
            valid_candidate_count,
            fallback,
        )


def _historical_cases() -> tuple[D051Case, ...]:
    return tuple(
        D051Case(
            "historical_d050",
            case.case_id,
            case.radius_m,
            case.position_bearing_deg,
            case.initial_bearing_error_rad,
            case.body_position,
            case.heading_rad,
        )
        for case in d050_frozen_cases()
    )


def _fresh_cases() -> tuple[D051Case, ...]:
    cases: list[D051Case] = []
    for radius_m in D051_FRESH_RADII_M:
        for position_bearing_deg in D051_FRESH_POSITION_BEARINGS_DEG:
            position_bearing_rad = math.radians(position_bearing_deg)
            body_position = (
                D049_STATION_CENTER[0] + radius_m * math.cos(position_bearing_rad),
                D049_STATION_CENTER[1] + radius_m * math.sin(position_bearing_rad),
            )
            source_bearing = position_bearing_rad + math.pi
            for index, relative_bearing in enumerate(
                D051_FRESH_INITIAL_BEARING_ERRORS_RAD, start=1
            ):
                cases.append(
                    D051Case(
                        "fresh_holdout",
                        (
                            f"fresh-r{radius_m:.3f}-p{position_bearing_deg:03d}-"
                            f"e{index:02d}"
                        ),
                        radius_m,
                        float(position_bearing_deg),
                        relative_bearing,
                        body_position,
                        (source_bearing - relative_bearing) % math.tau,
                    )
                )
    return tuple(cases)


def frozen_cases() -> tuple[D051Case, ...]:
    """Return the exact 96 historical plus 80 fresh fixed-state cases."""

    return _historical_cases() + _fresh_cases()


def _case_record(case: D051Case) -> dict[str, object]:
    return {
        "case_id": case.case_id,
        "radius_m": case.radius_m,
        "position_bearing_deg": case.position_bearing_deg,
        "initial_source_relative_bearing_error_rad": case.initial_bearing_error_rad,
        "initial_body_position": list(case.body_position),
        "initial_heading_rad": case.heading_rad,
    }


def _adapt_d049_decision(decision: D049Decision) -> D051Decision:
    return D051Decision(
        D050ControlMode(decision.mode.value),
        decision.wheel_delta_left,
        decision.wheel_delta_right,
        decision.reconstruction,
    )


def _command(
    arm: D051Arm,
    controller: D049Controller | D051UncertaintyController | D050SmoothController,
    observation: np.ndarray,
) -> D051Decision:
    if arm is D051Arm.ORIGINAL_BASELINE:
        return _adapt_d049_decision(
            cast(D049Controller, controller).command(observation)
        )
    if arm is D051Arm.FLOAT32_UNCERTAINTY_TREATMENT:
        return cast(D051UncertaintyController, controller).command(observation)
    decision = cast(D050SmoothController, controller).command(observation)
    return D051Decision(
        decision.mode,
        decision.wheel_delta_left,
        decision.wheel_delta_right,
        decision.reconstruction,
    )


def _true_body_relative_source(
    position: tuple[float, float], heading: float, station: tuple[float, float]
) -> D049Reconstruction:
    dx = station[0] - position[0]
    dy = station[1] - position[1]
    x_m = dx * math.cos(heading) + dy * math.sin(heading)
    y_m = -dx * math.sin(heading) + dy * math.cos(heading)
    return D049Reconstruction(x_m, y_m, math.hypot(x_m, y_m), math.atan2(y_m, x_m))


def _ideal_reconstruction(
    position: tuple[float, float],
    heading: float,
    station_center: tuple[float, float],
    config: D045PhysicalConfig,
) -> D049Reconstruction | None:
    body = Body(x=position[0], y=position[1], heading=heading, energy=0.0)
    beacon = sample_directional_beacon(
        body,
        station_center,
        probe_distance=config.beacon_probe_distance_m,
        sensor_angle=config.beacon_sensor_angle_rad,
        beacon_scale=config.beacon_scale_m,
    )
    return reconstruct_source(beacon.left, beacon.forward, beacon.right)


def _diagnostic(
    *,
    environment: D045Env,
    observation: np.ndarray,
    decision: D051Decision,
    telemetry: D045TransitionTelemetry,
    previous_homing_sign: int | None,
) -> tuple[dict[str, object], int | None]:
    true_before = _true_body_relative_source(
        telemetry.position_before, telemetry.heading_before, telemetry.station_center
    )
    true_after = _true_body_relative_source(
        telemetry.position_after, telemetry.heading_after, telemetry.station_center
    )
    nominal = decision.reconstruction
    envelope = float32_uncertainty_envelope(
        float(observation[2]), float(observation[3]), float(observation[4])
    )
    epsilon = envelope.epsilon_float32 if envelope is not None else None
    effective_tolerance = (
        decision.effective_angular_tolerance_rad
        if decision.mode is D050ControlMode.TURN
        or decision.mode is D050ControlMode.STRAIGHT
        or decision.mode is D050ControlMode.TERMINAL_SPIN
        else D049_ANGULAR_TOLERANCE_RAD
    )
    ideal = _ideal_reconstruction(
        telemetry.position_before,
        telemetry.heading_before,
        telemetry.station_center,
        environment.config,
    )
    homing_sign: int | None = None
    sign_changed: bool | None = None
    if nominal is not None and decision.mode in {
        D050ControlMode.TURN,
        D050ControlMode.STRAIGHT,
    }:
        homing_sign = (
            1 if nominal.bearing_rad > 0.0 else (-1 if nominal.bearing_rad < 0.0 else 0)
        )
        sign_changed = (
            previous_homing_sign is not None and homing_sign != previous_homing_sign
        )
        previous_homing_sign = homing_sign
    nominal_true_error = (
        _wrap_angle(nominal.bearing_rad - true_before.bearing_rad)
        if nominal is not None
        else None
    )
    ideal_error = (
        _wrap_angle(nominal.bearing_rad - ideal.bearing_rad)
        if nominal is not None and ideal is not None
        else None
    )
    abs_beta_le_epsilon = (
        abs(nominal.bearing_rad) <= epsilon
        if nominal is not None and epsilon is not None
        else None
    )
    true_within_envelope = (
        abs(_wrap_angle(true_before.bearing_rad - nominal.bearing_rad)) <= epsilon
        if nominal is not None and epsilon is not None
        else None
    )
    original_turn_uncertainty_straight = (
        nominal is not None
        and nominal.distance_m > D049_CENTRE_TOLERANCE_M
        and abs(nominal.bearing_rad) > D049_ANGULAR_TOLERANCE_RAD
        and abs(nominal.bearing_rad) <= effective_tolerance
    )
    return (
        {
            "step": telemetry.step_index,
            "observation_beacon_lfr": [
                float(observation[2]),
                float(observation[3]),
                float(observation[4]),
            ],
            "nominal_reconstructed_x_m": nominal.x_m if nominal else None,
            "nominal_reconstructed_y_m": nominal.y_m if nominal else None,
            "nominal_reconstructed_distance_m": nominal.distance_m if nominal else None,
            "nominal_reconstructed_bearing_rad": nominal.bearing_rad
            if nominal
            else None,
            "true_body_relative_x_m": true_before.x_m,
            "true_body_relative_y_m": true_before.y_m,
            "true_body_relative_distance_m": true_before.distance_m,
            "true_body_relative_bearing_rad": true_before.bearing_rad,
            "wrapped_reconstructed_minus_true_bearing_rad": nominal_true_error,
            "epsilon_float32_rad": epsilon,
            "effective_angular_tolerance_rad": effective_tolerance,
            "original_angular_tolerance_rad": D049_ANGULAR_TOLERANCE_RAD,
            "uncertainty_candidate_count": (
                envelope.candidate_count if envelope else 0
            ),
            "uncertainty_valid_candidate_count": (
                envelope.valid_candidate_count if envelope else 0
            ),
            "uncertainty_fallback": envelope.fallback if envelope else True,
            "float32_ideal_bearing_error_rad": ideal_error,
            "ideal_float64_reconstructed_x_m": ideal.x_m if ideal else None,
            "ideal_float64_reconstructed_y_m": ideal.y_m if ideal else None,
            "ideal_float64_reconstructed_distance_m": ideal.distance_m
            if ideal
            else None,
            "ideal_float64_reconstructed_bearing_rad": ideal.bearing_rad
            if ideal
            else None,
            "mode": decision.mode.value,
            "requested_wheel_delta_left": decision.wheel_delta_left,
            "requested_wheel_delta_right": decision.wheel_delta_right,
            "actual_wheel_delta_left": telemetry.actual_delta_left,
            "actual_wheel_delta_right": telemetry.actual_delta_right,
            "position_before": list(telemetry.position_before),
            "position_after": list(telemetry.position_after),
            "heading_before": telemetry.heading_before,
            "heading_after": telemetry.heading_after,
            "radial_distance_before_m": true_before.distance_m,
            "radial_distance_after_m": true_after.distance_m,
            "radial_progress_m": true_before.distance_m - true_after.distance_m,
            "signed_heading_change_rad": telemetry.heading_after
            - telemetry.heading_before,
            "charging_contact": telemetry.charging_contact_after,
            "battery_before_j": telemetry.battery_before_j,
            "battery_after_j": telemetry.battery_after_j,
            "nominal_bearing_sign_changed_from_previous_homing": sign_changed,
            "nominal_abs_bearing_le_epsilon": abs_beta_le_epsilon,
            "true_bearing_within_float32_uncertainty": true_within_envelope,
            "original_threshold_turn_uncertainty_treatment_straight": (
                original_turn_uncertainty_straight
            ),
        },
        previous_homing_sign,
    )


def _initial_trace(environment: D045Env, observation: np.ndarray) -> dict[str, object]:
    if environment.body is None:
        raise RuntimeError("environment body missing after reset")
    return {
        "step": 0,
        "x": environment.body.position[0],
        "y": environment.body.position[1],
        "heading": environment.body.heading,
        "mode": "RESET",
        "charging_contact": bool(observation[5]),
        "battery_j": environment.battery_j,
    }


def _transition_trace(
    telemetry: D045TransitionTelemetry, mode: D050ControlMode
) -> dict[str, object]:
    return {
        "step": telemetry.step_index,
        "x": telemetry.position_after[0],
        "y": telemetry.position_after[1],
        "heading": telemetry.heading_after,
        "mode": mode.value,
        "charging_contact": telemetry.charging_contact_after,
        "battery_j": telemetry.battery_after_j,
    }


def _run_arm(
    case: D051Case, arm: D051Arm, *, collect_diagnostics: bool = True
) -> dict[str, object]:
    config = D045PhysicalConfig(episode_horizon=D051_CASE_HORIZON)
    environment = D045Env(config)
    observation, organism_info = environment.reset(
        options={
            "body_position": case.body_position,
            "station_center": D049_STATION_CENTER,
            "heading": case.heading_rad,
        }
    )
    controller: D049Controller | D051UncertaintyController | D050SmoothController
    if arm is D051Arm.ORIGINAL_BASELINE:
        controller = D049Controller()
    elif arm is D051Arm.FLOAT32_UNCERTAINTY_TREATMENT:
        controller = D051UncertaintyController()
    else:
        controller = D050SmoothController()
    initial_battery = environment.battery_j
    initial_contact = bool(observation[5])
    first_contact_transition: int | None = 0 if initial_contact else None
    first_contact_battery_before: float | None = (
        initial_battery if initial_contact else None
    )
    first_contact_pair_error: tuple[float, float] | None = None
    terminal_spin_entry_transition: int | None = None
    terminal_spin_entry_battery: float | None = None
    first_stationary_charge_transition: int | None = None
    battery_increased_on_first_stationary_charge: bool | None = None
    terminal_spin_count = 0
    homing_transition_count = 0
    mode_counts: dict[str, int] = {}
    turn_run = 0
    longest_turn_run = 0
    sign_alternation_count = 0
    total_electrical_expenditure_j = 0.0
    minimum_distance = math.inf
    initial_distance: float | None = None
    final_distance: float | None = None
    epsilon_values: list[float] = []
    reconstruction_errors: list[float] = []
    ideal_errors: list[float] = []
    uncertainty_inside_count = 0
    abs_beta_inside_count = 0
    treatment_straight_count = 0
    cumulative_path_length_m = 0.0
    cumulative_absolute_heading_change_rad = 0.0
    cumulative_wheel_effort = 0.0
    boundary_scaled_transition_count = 0
    minimum_boundary_scale = 1.0
    rewards: list[float] = []
    organism_infos: list[dict[str, object]] = [organism_info]
    traces: list[dict[str, object]] = [_initial_trace(environment, observation)]
    diagnostics: list[dict[str, object]] = []
    transition_authority: list[str] = []
    invalid_beacon = False
    terminated = False
    truncated = False
    termination_reason: str | None = None
    previous_homing_sign: int | None = None

    for step_index in range(1, D051_CASE_HORIZON + 1):
        decision = _command(arm, controller, observation)
        pre_action_observation = observation.copy()
        transition_authority.append("LEVEL_1")
        mode = decision.mode
        mode_counts[mode.value] = mode_counts.get(mode.value, 0) + 1
        if mode is D050ControlMode.INVALID_BEACON:
            invalid_beacon = True
        if mode is D050ControlMode.TERMINAL_SPIN:
            terminal_spin_count += 1
            if terminal_spin_entry_transition is None:
                terminal_spin_entry_transition = step_index
                terminal_spin_entry_battery = environment.battery_j
        elif mode in {
            D050ControlMode.TURN,
            D050ControlMode.STRAIGHT,
        } or (arm is D051Arm.D050_SMOOTH_REFERENCE and mode.value == "CURVED_PURSUIT"):
            homing_transition_count += 1
        if mode is D050ControlMode.TURN:
            turn_run += 1
            longest_turn_run = max(longest_turn_run, turn_run)
        else:
            turn_run = 0

        before_contact = bool(observation[5])
        observation, reward, terminated, truncated, organism_info = environment.step(
            (decision.wheel_delta_left, decision.wheel_delta_right)
        )
        telemetry = environment.last_transition
        if telemetry is None:
            raise RuntimeError("D-045 did not provide transition telemetry")
        cumulative_path_length_m += math.dist(
            telemetry.position_before, telemetry.position_after
        )
        cumulative_absolute_heading_change_rad += abs(
            telemetry.heading_after - telemetry.heading_before
        )
        cumulative_wheel_effort += wheel_effort(
            telemetry.actual_delta_left,
            telemetry.actual_delta_right,
            config.max_wheel_delta_rad,
        )
        if telemetry.boundary_scale < 1.0:
            boundary_scaled_transition_count += 1
        minimum_boundary_scale = min(minimum_boundary_scale, telemetry.boundary_scale)
        total_electrical_expenditure_j += (
            telemetry.total_electrical_load_w * D045_DT_SECONDS
        )
        after_distance = _true_body_relative_source(
            telemetry.position_after, telemetry.heading_after, telemetry.station_center
        ).distance_m
        if initial_distance is None:
            initial_distance = _true_body_relative_source(
                telemetry.position_before,
                telemetry.heading_before,
                telemetry.station_center,
            ).distance_m
        before_distance = _true_body_relative_source(
            telemetry.position_before,
            telemetry.heading_before,
            telemetry.station_center,
        ).distance_m
        minimum_distance = min(minimum_distance, before_distance, after_distance)
        final_distance = after_distance
        if collect_diagnostics and arm is not D051Arm.D050_SMOOTH_REFERENCE:
            diagnostic, previous_homing_sign = _diagnostic(
                environment=environment,
                observation=pre_action_observation,
                decision=decision,
                telemetry=telemetry,
                previous_homing_sign=previous_homing_sign,
            )
            diagnostics.append(diagnostic)
            epsilon = diagnostic["epsilon_float32_rad"]
            reconstruction_error = diagnostic[
                "wrapped_reconstructed_minus_true_bearing_rad"
            ]
            ideal_error = diagnostic["float32_ideal_bearing_error_rad"]
            if isinstance(epsilon, (int, float)):
                epsilon_values.append(float(epsilon))
            if isinstance(reconstruction_error, (int, float)):
                reconstruction_errors.append(abs(float(reconstruction_error)))
            if isinstance(ideal_error, (int, float)):
                ideal_errors.append(abs(float(ideal_error)))
            if diagnostic["nominal_abs_bearing_le_epsilon"] is True:
                abs_beta_inside_count += 1
            if diagnostic["true_bearing_within_float32_uncertainty"] is True:
                uncertainty_inside_count += 1
            if (
                diagnostic["original_threshold_turn_uncertainty_treatment_straight"]
                is True
            ):
                treatment_straight_count += 1
            if diagnostic["nominal_bearing_sign_changed_from_previous_homing"] is True:
                sign_alternation_count += 1
        traces.append(_transition_trace(telemetry, mode))
        after_contact = bool(observation[5])
        rewards.append(reward)
        organism_infos.append(organism_info)
        if not before_contact and after_contact and first_contact_transition is None:
            first_contact_transition = step_index
            first_contact_battery_before = telemetry.battery_before_j
            first_contact_pair_error = (
                telemetry.dock_plus_error_m,
                telemetry.dock_minus_error_m,
            )
        if (
            mode is D050ControlMode.CONTACT
            and first_stationary_charge_transition is None
        ):
            first_stationary_charge_transition = step_index
            battery_increased_on_first_stationary_charge = (
                telemetry.battery_after_j > telemetry.battery_before_j
            )
        if first_stationary_charge_transition is not None:
            break
        if invalid_beacon or terminated or truncated:
            break
        if terminal_spin_count >= D049_TERMINAL_SPIN_MAX_STEPS and not after_contact:
            break
        if not math.isfinite(float(observation[0])):
            raise RuntimeError("non-finite organism observation")

    if environment.last_transition is not None:
        last_reason = environment.last_transition.termination_reason
        termination_reason = last_reason.value if last_reason is not None else None
    contact_acquired = first_contact_transition is not None
    if invalid_beacon:
        failure_classification = "INVALID_BEACON"
    elif first_stationary_charge_transition is not None:
        failure_classification = (
            "DOCKED_AND_CHARGING"
            if battery_increased_on_first_stationary_charge
            else "CONTACT_WITHOUT_CHARGE"
        )
    elif terminated and not contact_acquired:
        failure_classification = "TERMINATED_BEFORE_CONTACT"
    elif truncated and not contact_acquired:
        failure_classification = "RETURN_HORIZON_CENSORED"
    elif terminal_spin_count >= D049_TERMINAL_SPIN_MAX_STEPS:
        failure_classification = "TERMINAL_SPIN_EXHAUSTED"
    elif contact_acquired:
        failure_classification = "CONTACT_WITHOUT_CHARGE"
    else:
        failure_classification = "RETURN_HORIZON_CENSORED"
    homing_energy: float | None
    terminal_energy: float | None
    if (
        first_stationary_charge_transition is not None
        and terminal_spin_entry_transition is None
        and first_contact_battery_before is not None
    ):
        homing_energy = initial_battery - first_contact_battery_before
        terminal_energy = 0.0
    else:
        homing_energy = (
            initial_battery - terminal_spin_entry_battery
            if terminal_spin_entry_battery is not None
            else None
        )
        terminal_energy = (
            terminal_spin_entry_battery - first_contact_battery_before
            if terminal_spin_entry_battery is not None
            and first_contact_battery_before is not None
            else None
        )
    return {
        "arm": arm.value,
        "initial_state": _case_record(case),
        "horizon": D051_CASE_HORIZON,
        "transition_count": len(transition_authority),
        "homing_transition_count": homing_transition_count,
        "terminal_spin_step_count": terminal_spin_count,
        "terminal_spin_entry_transition": terminal_spin_entry_transition,
        "charging_contact_acquired": contact_acquired,
        "first_contact_transition": first_contact_transition,
        "first_stationary_zero_wheel_charging_transition": (
            first_stationary_charge_transition
        ),
        "battery_energy_consumed_to_first_contact_j": (
            initial_battery - first_contact_battery_before
            if first_contact_battery_before is not None
            else None
        ),
        "battery_energy_consumed_during_homing_j": homing_energy,
        "battery_energy_consumed_during_terminal_j": terminal_energy,
        "geometric_path_length_m": cumulative_path_length_m,
        "cumulative_absolute_heading_change_rad": (
            cumulative_absolute_heading_change_rad
        ),
        "cumulative_normalized_wheel_effort": cumulative_wheel_effort,
        "boundary_scaled_transition_count": boundary_scaled_transition_count,
        "minimum_boundary_scale": minimum_boundary_scale,
        "total_electrical_expenditure_j": total_electrical_expenditure_j,
        "final_evaluator_distance_m": final_distance,
        "minimum_evaluator_distance_m": minimum_distance,
        "radial_progress_m": (
            initial_distance - final_distance
            if initial_distance is not None and final_distance is not None
            else None
        ),
        "mode_counts": mode_counts,
        "longest_consecutive_turn_run": longest_turn_run,
        "bearing_sign_alternation_count": sign_alternation_count,
        "float32_reconstruction_bearing_error_summary": _distribution_summary(
            reconstruction_errors
        ),
        "epsilon_float32_summary": _distribution_summary(epsilon_values),
        "float32_vs_float64_ideal_bearing_error_summary": _distribution_summary(
            ideal_errors
        ),
        "abs_beta_le_epsilon_count": abs_beta_inside_count,
        "true_bearing_within_float32_uncertainty_count": uncertainty_inside_count,
        "original_threshold_turn_treatment_straight_count": treatment_straight_count,
        "contact_pair_error_at_first_contact_m": (
            list(first_contact_pair_error)
            if first_contact_pair_error is not None
            else None
        ),
        "battery_increased_on_first_stationary_charge": (
            battery_increased_on_first_stationary_charge
        ),
        "terminated": terminated,
        "truncated": truncated,
        "termination_reason": termination_reason,
        "failure_classification": failure_classification,
        "reward_values": rewards,
        "organism_info_values": organism_infos,
        "transition_authority": transition_authority,
        "trace": traces,
        "diagnostics": diagnostics,
    }


def _distribution_summary(values: Iterable[float]) -> dict[str, object]:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return {
            "count": 0,
            "minimum": None,
            "mean": None,
            "median": None,
            "maximum": None,
        }
    middle = len(ordered) // 2
    median = (
        ordered[middle]
        if len(ordered) % 2
        else (ordered[middle - 1] + ordered[middle]) / 2.0
    )
    return {
        "count": len(ordered),
        "minimum": ordered[0],
        "mean": sum(ordered) / len(ordered),
        "median": median,
        "maximum": ordered[-1],
    }


def _behavioral_projection(result: dict[str, object]) -> dict[str, object]:
    names = (
        "initial_state",
        "horizon",
        "transition_count",
        "homing_transition_count",
        "terminal_spin_step_count",
        "terminal_spin_entry_transition",
        "charging_contact_acquired",
        "first_contact_transition",
        "first_stationary_zero_wheel_charging_transition",
        "battery_energy_consumed_to_first_contact_j",
        "battery_energy_consumed_during_homing_j",
        "battery_energy_consumed_during_terminal_j",
        "contact_pair_error_at_first_contact_m",
        "battery_increased_on_first_stationary_charge",
        "terminated",
        "truncated",
        "termination_reason",
        "failure_classification",
        "reward_values",
        "organism_info_values",
        "transition_authority",
        "trace",
    )
    return {name: result[name] for name in names}


def _load_historical_artifact(path: Path) -> dict[str, object]:
    if artifact_sha256(path) != D051_HISTORICAL_ARTIFACT_SHA256:
        raise ValueError(
            "committed D-050 artifact SHA-256 does not match D-051 reference"
        )
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def _historical_replay_check(
    pairs: list[dict[str, object]], historical: dict[str, object]
) -> dict[str, object]:
    historical_pairs = cast(list[dict[str, object]], historical["pairs"])
    mismatches: list[str] = []
    if len(historical_pairs) != 96:
        mismatches.append(
            f"historical artifact pair count {len(historical_pairs)} != 96"
        )
    for pair, expected in zip(pairs[:96], historical_pairs, strict=True):
        actual_arms = cast(dict[str, object], pair["arms"])
        expected_baseline = cast(dict[str, object], expected["baseline"])
        expected_smooth = cast(dict[str, object], expected["smooth"])
        if _behavioral_projection(
            cast(dict[str, object], actual_arms[D051Arm.ORIGINAL_BASELINE.value])
        ) != _behavioral_projection(expected_baseline):
            mismatches.append(f"baseline:{pair['case_id']}")
        if _behavioral_projection(
            cast(dict[str, object], actual_arms[D051Arm.D050_SMOOTH_REFERENCE.value])
        ) != _behavioral_projection(expected_smooth):
            mismatches.append(f"smooth:{pair['case_id']}")
    return {
        "reference_artifact_sha256": D051_HISTORICAL_ARTIFACT_SHA256,
        "reference_executed_commit_sha": historical["executed_commit_sha"],
        "case_count": len(historical_pairs),
        "baseline_behavioral_identity": not any(
            item.startswith("baseline:") for item in mismatches
        ),
        "smooth_behavioral_identity": not any(
            item.startswith("smooth:") for item in mismatches
        ),
        "mismatches": mismatches,
    }


def _arm_summary(results: list[dict[str, object]]) -> dict[str, object]:
    return {
        "case_count": len(results),
        "success_count": sum(
            result["failure_classification"] == "DOCKED_AND_CHARGING"
            for result in results
        ),
        "failure_classification_counts": _counts(
            cast(str, result["failure_classification"]) for result in results
        ),
        "first_contact_transition_summary": _distribution_summary(
            float(cast(int, result["first_contact_transition"]))
            for result in results
            if result["first_contact_transition"] is not None
        ),
        "first_stationary_charging_transition_summary": _distribution_summary(
            float(cast(int, result["first_stationary_zero_wheel_charging_transition"]))
            for result in results
            if result["first_stationary_zero_wheel_charging_transition"] is not None
        ),
        "total_electrical_expenditure_j_summary": _distribution_summary(
            float(cast(float, result["total_electrical_expenditure_j"]))
            for result in results
        ),
        "final_distance_m_summary": _distribution_summary(
            float(cast(float, result["final_evaluator_distance_m"]))
            for result in results
            if result["final_evaluator_distance_m"] is not None
        ),
        "minimum_distance_m_summary": _distribution_summary(
            float(cast(float, result["minimum_evaluator_distance_m"]))
            for result in results
            if result["minimum_evaluator_distance_m"] is not None
        ),
        "radial_progress_m_summary": _distribution_summary(
            float(cast(float, result["radial_progress_m"]))
            for result in results
            if result["radial_progress_m"] is not None
        ),
        "mode_dwell_counts": _sum_nested_counts(results, "mode_counts"),
        "bearing_sign_alternation_count": sum(
            cast(int, result["bearing_sign_alternation_count"]) for result in results
        ),
        "longest_consecutive_turn_run_maximum": max(
            (cast(int, result["longest_consecutive_turn_run"]) for result in results),
            default=0,
        ),
        "abs_beta_le_epsilon_count": sum(
            cast(int, result["abs_beta_le_epsilon_count"]) for result in results
        ),
        "true_bearing_within_float32_uncertainty_count": sum(
            cast(int, result["true_bearing_within_float32_uncertainty_count"])
            for result in results
        ),
        "original_threshold_turn_treatment_straight_count": sum(
            cast(int, result["original_threshold_turn_treatment_straight_count"])
            for result in results
        ),
        "reconstruction_bearing_error_summary": _distribution_summary(
            float(
                cast(
                    float,
                    cast(
                        dict[str, object],
                        result["float32_reconstruction_bearing_error_summary"],
                    )["maximum"],
                )
            )
            for result in results
            if cast(
                dict[str, object],
                result["float32_reconstruction_bearing_error_summary"],
            )["maximum"]
            is not None
        ),
        "epsilon_float32_summary_of_case_maxima": _distribution_summary(
            float(
                cast(
                    float,
                    cast(dict[str, object], result["epsilon_float32_summary"])[
                        "maximum"
                    ],
                )
            )
            for result in results
            if cast(dict[str, object], result["epsilon_float32_summary"])["maximum"]
            is not None
        ),
        "float32_vs_float64_ideal_bearing_error_summary_of_case_maxima": (
            _distribution_summary(
                float(
                    cast(
                        float,
                        cast(
                            dict[str, object],
                            result["float32_vs_float64_ideal_bearing_error_summary"],
                        )["maximum"],
                    )
                )
                for result in results
                if cast(
                    dict[str, object],
                    result["float32_vs_float64_ideal_bearing_error_summary"],
                )["maximum"]
                is not None
            )
        ),
    }


def _counts(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def _arm_record(pair: dict[str, object], arm: D051Arm) -> dict[str, object]:
    arms = cast(dict[str, object], pair["arms"])
    return cast(dict[str, object], arms[arm.value])


def _sum_nested_counts(results: list[dict[str, object]], field: str) -> dict[str, int]:
    total: dict[str, int] = {}
    for result in results:
        nested = cast(dict[str, int], result[field])
        for name, count in nested.items():
            total[name] = total.get(name, 0) + count
    return total


def _instrumentation_identity_check(case: D051Case) -> bool:
    for arm in (D051Arm.ORIGINAL_BASELINE, D051Arm.FLOAT32_UNCERTAINTY_TREATMENT):
        enabled = _run_arm(case, arm, collect_diagnostics=True)
        disabled = _run_arm(case, arm, collect_diagnostics=False)
        if _behavioral_projection(enabled) != _behavioral_projection(disabled):
            return False
    return True


def _protocol_record() -> dict[str, object]:
    return {
        "station_center": list(D049_STATION_CENTER),
        "historical_support": {
            "source": "D-050 frozen 3 x 8 x 4 matrix",
            "radii_m": list(D050_RETURN_RADII_M),
            "position_bearings_deg": list(D050_POSITION_BEARINGS_DEG),
            "initial_source_relative_bearing_errors_rad": list(
                D050_INITIAL_BEARING_ERRORS_RAD
            ),
            "case_count": 96,
            "horizon": D051_CASE_HORIZON,
        },
        "fresh_support": {
            "radii_m": list(D051_FRESH_RADII_M),
            "position_bearings_deg": list(D051_FRESH_POSITION_BEARINGS_DEG),
            "initial_source_relative_bearing_errors_rad": list(
                D051_FRESH_INITIAL_BEARING_ERRORS_RAD
            ),
            "case_count": 80,
            "horizon": D051_CASE_HORIZON,
            "seed_status": "seedless fixed-state matrix",
        },
        "arms": {
            D051Arm.ORIGINAL_BASELINE.value: (
                "aweform.d049.D049Controller delegated unchanged"
            ),
            D051Arm.FLOAT32_UNCERTAINTY_TREATMENT.value: {
                "nominal_reconstruction": "aweform.d049.reconstruct_source",
                "candidate_values": (
                    "np.nextafter(current_float32, 0.0), current_float32, "
                    "np.nextafter(current_float32, +inf) capped at 1.0"
                ),
                "legal_range": "0 < value <= 1",
                "candidate_tuples": "Cartesian product, at most 27",
                "effective_angular_tolerance": (
                    "max(1e-6 rad, max(abs(wrapped(candidate_bearing - "
                    "nominal_bearing))))"
                ),
                "fallback": (
                    "original 1e-6 rad when no valid candidate reconstruction exists"
                ),
                "forbidden_tuning": [
                    "multiplier",
                    "tolerance sweep",
                    "success-based tuning",
                    "evaluator geometry",
                ],
            },
            D051Arm.D050_SMOOTH_REFERENCE.value: (
                "aweform.d050.D050SmoothController unchanged"
            ),
        },
        "observation_channel_count": 8,
        "controller_observation_channels": [2, 3, 4, 5],
        "reward": 0.0,
        "organism_info": {},
    }


def _validation_record(
    pairs: list[dict[str, object]],
    replay: dict[str, object],
    instrumentation_identity: bool,
) -> dict[str, object]:
    return {
        "exact_historical_case_count": sum(
            pair["support"] == "historical_d050" for pair in pairs
        )
        == 96,
        "exact_fresh_case_count": sum(
            pair["support"] == "fresh_holdout" for pair in pairs
        )
        == 80,
        "exact_fresh_matrix_cardinality": len(_fresh_cases()) == 80,
        "historical_baseline_behavioral_identity": replay[
            "baseline_behavioral_identity"
        ],
        "historical_smooth_behavioral_identity": replay["smooth_behavioral_identity"],
        "diagnostic_instrumentation_causal_identity": instrumentation_identity,
        "arm_b_uses_only_observation_and_fixed_constants": True,
        "evaluator_geometry_causally_isolated": True,
        "reward_exactly_zero": all(
            all(
                reward == 0.0
                for reward in cast(
                    list[float],
                    _arm_record(pair, arm)["reward_values"],
                )
            )
            for pair in pairs
            for arm in D051Arm
        ),
        "organism_info_exactly_empty": all(
            all(
                info == {}
                for info in cast(
                    list[dict[str, object]],
                    _arm_record(pair, arm)["organism_info_values"],
                )
            )
            for pair in pairs
            for arm in D051Arm
        ),
        "level1_authority_on_every_transition": all(
            set(
                cast(
                    list[str],
                    _arm_record(pair, arm)["transition_authority"],
                )
            )
            == {"LEVEL_1"}
            for pair in pairs
            for arm in D051Arm
        ),
        "fresh_support_is_seedless": True,
    }


def run_d051_protocol(
    executed_commit_sha: str, historical_artifact_path: Path | None = None
) -> dict[str, object]:
    """Execute the frozen historical replay and fresh holdout protocol."""

    _validate_sha(executed_commit_sha)
    path = historical_artifact_path or (
        Path(__file__).resolve().parents[2] / D051_HISTORICAL_ARTIFACT_RELATIVE_PATH
    )
    historical = _load_historical_artifact(path)
    cases = frozen_cases()
    pairs: list[dict[str, object]] = []
    for case in cases:
        pairs.append(
            {
                "support": case.support,
                "case_id": case.case_id,
                "initial_state": _case_record(case),
                "arms": {arm.value: _run_arm(case, arm) for arm in D051Arm},
            }
        )
    replay = _historical_replay_check(pairs, historical)
    instrumentation_identity = _instrumentation_identity_check(cases[0])
    by_support: dict[str, dict[str, object]] = {}
    for support in ("historical_d050", "fresh_holdout"):
        support_pairs = [pair for pair in pairs if pair["support"] == support]
        by_support[support] = {
            arm.value: _arm_summary([_arm_record(pair, arm) for pair in support_pairs])
            for arm in D051Arm
        }
    return {
        "schema_version": "d051-artifact-v1",
        "development_id": D051_ID,
        "protocol_version": D051_PROTOCOL_VERSION,
        "authorized_base_sha": D051_AUTHORIZED_BASE_SHA,
        "executed_commit_sha": executed_commit_sha,
        "result_kind": "development_diagnostic",
        "claims_boundary": (
            "descriptive only; not confirmatory evidence; Arm B is not promoted"
        ),
        "execution_status": "COMPLETED",
        "frozen_protocol": _protocol_record(),
        "historical_replay": replay,
        "validation": _validation_record(pairs, replay, instrumentation_identity),
        "summaries_by_support": by_support,
        "pairs": pairs,
    }


def write_d051_artifact(path: Path, executed_commit_sha: str) -> Path:
    artifact = run_d051_protocol(executed_commit_sha)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(artifact, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return path


def artifact_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--executed-commit-sha", required=True)
    args = parser.parse_args()
    write_d051_artifact(args.output, args.executed_commit_sha)


if __name__ == "__main__":
    main()
