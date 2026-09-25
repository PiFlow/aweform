"""D-049 constitutive Level-1 direct return and contact-seeking dock.

The causal controller in this module is deliberately stateless with respect to
learning.  It receives the exact float32 D-045 observation array and uses only
the three beacon channels, the current contact bit, and fixed V0.5 constants.
The D-045 environment and its evaluator telemetry are used only by the
seedless diagnostic runner below.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Final, cast

import numpy as np

from .d045 import (
    D045_BEACON_PROBE_DISTANCE_METRES,
    D045_BEACON_SCALE_METRES,
    D045_BEACON_SENSOR_ANGLE_RAD,
    D045_CONTACT_OFFSET_METRES,
    D045_CONTACT_TOLERANCE_METRES,
    D045_MAX_WHEEL_DELTA_RAD,
    D045_WHEEL_RADIUS_METRES,
    D045_WHEEL_TRACK_WIDTH_METRES,
    D045Env,
    D045PhysicalConfig,
)

D049_ID: Final[str] = "D-049"
D049_PROTOCOL_VERSION: Final[str] = "d049-level1-direct-return-v1"
D049_AUTHORIZED_BASE_SHA: Final[str] = (
    "a375de54722c3bfc09634a3685c4558a7a9f917f"
)
D049_STATION_CENTER: Final[tuple[float, float]] = (0.50, 0.50)
D049_RETURN_RADII_M: Final[tuple[float, ...]] = (0.10, 0.25, 0.40)
D049_POSITION_BEARINGS_DEG: Final[tuple[int, ...]] = tuple(range(0, 360, 45))

# These are source-relative body-frame bearing offsets.  They were frozen as
# explicit non-special angles before the official matrix was executed.
D049_INITIAL_HEADING_CLASSES: Final[tuple[tuple[str, float], ...]] = (
    ("source_facing", 0.137),
    ("substantial_left", 1.083),
    ("substantial_right", -0.971),
    ("approximately_reversed", math.pi - 0.217),
)
D049_TERMINAL_HEADINGS_RAD: Final[tuple[float, ...]] = (
    0.137,
    0.193,
    0.247,
    1.209,
    math.pi - 0.173,
    2.387,
    4.119,
    5.711,
)
D049_CASE_HORIZON: Final[int] = 128

# The current float32 L/F/R revalidation grid has maximum coordinate and
# bearing errors below 3.3e-7 in this substrate.  These tolerances are a
# predeclared numerical margin above that inverse-precision result, not a
# docking-success threshold.
D049_CENTRE_TOLERANCE_M: Final[float] = 1.0e-6
D049_ANGULAR_TOLERANCE_RAD: Final[float] = 1.0e-6
D049_INVERSE_COORDINATE_LIMIT_M: Final[float] = 1.0e-6
D049_INVERSE_DISTANCE_LIMIT_M: Final[float] = 1.0e-6
D049_INVERSE_BEARING_LIMIT_RAD: Final[float] = 1.0e-6
D049_TERMINAL_SPIN_MAX_STEPS: Final[int] = 20
D049_TERMINAL_SPIN_DIRECTION: Final[int] = 1


class D049ControlMode(Enum):
    """Controller branch labels used for attribution and diagnostics."""

    CONTACT = "CONTACT"
    INVALID_BEACON = "INVALID_BEACON"
    TURN = "TURN"
    STRAIGHT = "STRAIGHT"
    TERMINAL_SPIN = "TERMINAL_SPIN"


@dataclass(frozen=True, slots=True)
class D049Reconstruction:
    """Body-relative source reconstruction from organism-visible L/F/R."""

    x_m: float
    y_m: float
    distance_m: float
    bearing_rad: float


@dataclass(frozen=True, slots=True)
class D049Decision:
    """One Level-1 decision and its optional beacon reconstruction."""

    mode: D049ControlMode
    wheel_delta_left: float
    wheel_delta_right: float
    reconstruction: D049Reconstruction | None


@dataclass(frozen=True, slots=True)
class D049Case:
    """One frozen seedless initial state."""

    case_id: str
    case_group: str
    radius_m: float
    position_bearing_deg: int | None
    initial_heading_class: str
    body_position: tuple[float, float]
    heading_rad: float


@dataclass(frozen=True, slots=True)
class D049InverseSummary:
    """Result of the pre-behaviour current-path inverse revalidation."""

    valid_cases: int
    invalid_cases: int
    max_coordinate_error_m: float
    max_distance_error_m: float
    max_bearing_error_rad: float
    within_frozen_limits: bool


def reconstruct_source(
    beacon_left: float,
    beacon_forward: float,
    beacon_right: float,
    *,
    beacon_scale_m: float = D045_BEACON_SCALE_METRES,
    probe_distance_m: float = D045_BEACON_PROBE_DISTANCE_METRES,
    sensor_angle_rad: float = D045_BEACON_SENSOR_ANGLE_RAD,
) -> D049Reconstruction | None:
    """Invert the current D-045 float32 beacon values, or fail safely.

    The caller supplies values read from the organism-visible observation.  No
    evaluator body, heading, station, or contact geometry is consulted here.
    """

    signals = (beacon_left, beacon_forward, beacon_right)
    if not all(math.isfinite(value) and 0.0 < value <= 1.0 for value in signals):
        return None
    if (
        not math.isfinite(beacon_scale_m)
        or beacon_scale_m <= 0.0
        or not math.isfinite(probe_distance_m)
        or probe_distance_m <= 0.0
        or not math.isfinite(sensor_angle_rad)
        or not 0.0 < sensor_angle_rad < math.pi
    ):
        return None

    squared_distances: list[float] = []
    for signal in signals:
        term = 1.0 / signal - 1.0
        if not math.isfinite(term) or term < 0.0:
            return None
        distance = beacon_scale_m * math.sqrt(term)
        if not math.isfinite(distance):
            return None
        squared_distances.append(distance * distance)

    left_squared, forward_squared, right_squared = squared_distances
    sine = math.sin(sensor_angle_rad)
    cosine = math.cos(sensor_angle_rad)
    denominator_y = 4.0 * probe_distance_m * sine
    denominator_x = 2.0 * probe_distance_m * (1.0 - cosine)
    if denominator_y == 0.0 or denominator_x == 0.0:
        return None
    y_m = (right_squared - left_squared) / denominator_y
    x_m = (
        ((left_squared + right_squared) / 2.0) - forward_squared
    ) / denominator_x
    distance_m = math.hypot(x_m, y_m)
    bearing_rad = math.atan2(y_m, x_m)
    values = (x_m, y_m, distance_m, bearing_rad)
    if not all(math.isfinite(value) for value in values):
        return None
    return D049Reconstruction(x_m, y_m, distance_m, bearing_rad)


class D049Controller:
    """Stateless-with-respect-to-learning Level-1 return controller.

    ``terminal_spin_steps`` is diagnostic bookkeeping only; it never changes
    the fixed command or any branch of the causal routine.
    """

    def __init__(self) -> None:
        self.terminal_spin_steps = 0

    def command(self, observation: np.ndarray) -> D049Decision:
        """Choose one existing continuous bilateral wheel command."""

        if observation.shape != (8,):
            raise ValueError("D-049 requires the exact eight-channel observation")

        contact_value = float(observation[5])
        if contact_value == 1.0:
            return D049Decision(D049ControlMode.CONTACT, 0.0, 0.0, None)
        if contact_value != 0.0 or not math.isfinite(contact_value):
            return D049Decision(D049ControlMode.INVALID_BEACON, 0.0, 0.0, None)

        reconstruction = reconstruct_source(
            float(observation[2]),
            float(observation[3]),
            float(observation[4]),
        )
        if reconstruction is None:
            return D049Decision(D049ControlMode.INVALID_BEACON, 0.0, 0.0, None)

        if reconstruction.distance_m <= D049_CENTRE_TOLERANCE_M:
            self.terminal_spin_steps += 1
            maximum = D045_MAX_WHEEL_DELTA_RAD
            signed_maximum = D049_TERMINAL_SPIN_DIRECTION * maximum
            return D049Decision(
                D049ControlMode.TERMINAL_SPIN,
                -signed_maximum,
                signed_maximum,
                reconstruction,
            )

        bearing = reconstruction.bearing_rad
        if abs(bearing) > D049_ANGULAR_TOLERANCE_RAD:
            magnitude = min(
                abs(bearing)
                * D045_WHEEL_TRACK_WIDTH_METRES
                / (2.0 * D045_WHEEL_RADIUS_METRES),
                D045_MAX_WHEEL_DELTA_RAD,
            )
            signed_magnitude = math.copysign(magnitude, bearing)
            return D049Decision(
                D049ControlMode.TURN,
                -signed_magnitude,
                signed_magnitude,
                reconstruction,
            )

        travel_m = min(
            reconstruction.distance_m,
            D045_MAX_WHEEL_DELTA_RAD * D045_WHEEL_RADIUS_METRES,
        )
        wheel_delta = travel_m / D045_WHEEL_RADIUS_METRES
        return D049Decision(
            D049ControlMode.STRAIGHT,
            wheel_delta,
            wheel_delta,
            reconstruction,
        )


def frozen_cases() -> tuple[D049Case, ...]:
    """Return the complete result-free seedless fixed-state matrix."""

    cases: list[D049Case] = []
    for radius_m in D049_RETURN_RADII_M:
        for position_bearing_deg in D049_POSITION_BEARINGS_DEG:
            position_bearing_rad = math.radians(position_bearing_deg)
            body_position = (
                D049_STATION_CENTER[0] + radius_m * math.cos(position_bearing_rad),
                D049_STATION_CENTER[1] + radius_m * math.sin(position_bearing_rad),
            )
            source_bearing = position_bearing_rad + math.pi
            for class_name, relative_bearing in D049_INITIAL_HEADING_CLASSES:
                heading = (source_bearing - relative_bearing) % math.tau
                case_id = (
                    f"direct-r{radius_m:.2f}-p{position_bearing_deg:03d}-"
                    f"{class_name}"
                )
                cases.append(
                    D049Case(
                        case_id,
                        "direct_return",
                        radius_m,
                        position_bearing_deg,
                        class_name,
                        body_position,
                        heading,
                    )
                )
    for index, heading in enumerate(D049_TERMINAL_HEADINGS_RAD, start=1):
        cases.append(
            D049Case(
                f"terminal-centre-h{index:02d}",
                "terminal_only",
                0.0,
                None,
                f"terminal_heading_{index:02d}",
                D049_STATION_CENTER,
                heading,
            )
        )
    return tuple(cases)


def run_inverse_revalidation(
    *, config: D045PhysicalConfig | None = None
) -> D049InverseSummary:
    """Revalidate D-016's inverse through the exact D-045 float32 path."""

    physical = config or D045PhysicalConfig(episode_horizon=D049_CASE_HORIZON)
    valid_cases = 0
    invalid_cases = 0
    max_coordinate_error = 0.0
    max_distance_error = 0.0
    max_bearing_error = 0.0
    for case in frozen_cases():
        env = D045Env(physical)
        observation, _ = env.reset(
            options={
                "body_position": case.body_position,
                "station_center": D049_STATION_CENTER,
                "heading": case.heading_rad,
            }
        )
        reconstruction = reconstruct_source(
            float(observation[2]),
            float(observation[3]),
            float(observation[4]),
        )
        actual_x, actual_y = _actual_body_relative_source(case, D049_STATION_CENTER)
        actual_distance = math.hypot(actual_x, actual_y)
        if reconstruction is None:
            invalid_cases += 1
            continue
        valid_cases += 1
        max_coordinate_error = max(
            max_coordinate_error,
            abs(reconstruction.x_m - actual_x),
            abs(reconstruction.y_m - actual_y),
        )
        max_distance_error = max(
            max_distance_error, abs(reconstruction.distance_m - actual_distance)
        )
        if actual_distance <= D049_CENTRE_TOLERANCE_M:
            bearing_error = 0.0
        else:
            actual_bearing = math.atan2(actual_y, actual_x)
            bearing_error = abs(
                math.atan2(
                    math.sin(reconstruction.bearing_rad - actual_bearing),
                    math.cos(reconstruction.bearing_rad - actual_bearing),
                )
            )
        max_bearing_error = max(max_bearing_error, bearing_error)
    within_limits = (
        invalid_cases == 0
        and max_coordinate_error <= D049_INVERSE_COORDINATE_LIMIT_M
        and max_distance_error <= D049_INVERSE_DISTANCE_LIMIT_M
        and max_bearing_error <= D049_INVERSE_BEARING_LIMIT_RAD
    )
    return D049InverseSummary(
        len(frozen_cases()) - invalid_cases,
        invalid_cases,
        max_coordinate_error,
        max_distance_error,
        max_bearing_error,
        within_limits,
    )


def run_d049_protocol(executed_commit_sha: str) -> dict[str, object]:
    """Execute the frozen matrix and return a deterministic compact artifact."""

    if len(executed_commit_sha) != 40 or any(
        character not in "0123456789abcdef" for character in executed_commit_sha
    ):
        raise ValueError("executed_commit_sha must be a lowercase 40-character SHA")
    inverse_summary = run_inverse_revalidation()
    inverse_ok = inverse_summary.within_frozen_limits
    cases = (
        [_run_case(case, executed_commit_sha) for case in frozen_cases()]
        if inverse_ok
        else []
    )
    successful = sum(
        case_result["failure_classification"] == "DOCKED_AND_CHARGING"
        for case_result in cases
    )
    total_transitions = sum(
        cast(int, case_result["transition_count"]) for case_result in cases
    )
    level1_transitions = sum(
        cast(int, case_result["level1_authority_transition_count"])
        for case_result in cases
    )
    return {
        "schema_version": "d049-artifact-v1",
        "development_id": D049_ID,
        "protocol_version": D049_PROTOCOL_VERSION,
        "authorized_base_sha": D049_AUTHORIZED_BASE_SHA,
        "executed_commit_sha": executed_commit_sha,
        "result_kind": "development_diagnostic",
        "claims_boundary": "descriptive only; not confirmatory evidence",
        "execution_status": "READY" if inverse_ok else "INVERSE_REVALIDATION_FAILED",
        "behavioral_execution_permitted": inverse_ok,
        "inverse_revalidation": _as_json_record(inverse_summary),
        "frozen_protocol": _protocol_record(),
        "aggregate": {
            "case_count": len(cases),
            "successful_cases": successful,
            "failed_cases": len(cases) - successful,
            "total_transitions": total_transitions,
            "level1_authority_transition_count": level1_transitions,
            "level1_authority_fraction": (
                level1_transitions / total_transitions if total_transitions else 0.0
            ),
            "reward_values": [0.0],
            "organism_info_values": [{}],
        },
        "cases": cases,
    }


def write_d049_artifact(path: Path, executed_commit_sha: str) -> Path:
    """Write the deterministic JSON artifact with stable formatting."""

    artifact = run_d049_protocol(executed_commit_sha)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(artifact, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return path


def artifact_sha256(path: Path) -> str:
    """Return the byte hash used by the completed D-record."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_case(case: D049Case, executed_commit_sha: str) -> dict[str, object]:
    del executed_commit_sha  # provenance is retained at artifact level
    config = D045PhysicalConfig(episode_horizon=D049_CASE_HORIZON)
    env = D045Env(config)
    observation, organism_info = env.reset(
        options={
            "body_position": case.body_position,
            "station_center": D049_STATION_CENTER,
            "heading": case.heading_rad,
        }
    )
    controller = D049Controller()
    initial_battery = env.battery_j
    initial_contact = bool(observation[5])
    first_contact_transition: int | None = 0 if initial_contact else None
    first_contact_battery_before: float | None = (
        initial_battery if initial_contact else None
    )
    first_contact_pair_error: tuple[float, float] | None = None
    center_reached_transition: int | None = None
    turn_count = 0
    straight_count = 0
    straight_command_distance = 0.0
    straight_actual_distance = 0.0
    terminal_spin_count = 0
    transition_authority: list[str] = []
    action_trace: list[tuple[float, float]] = []
    rewards: list[float] = []
    organism_infos: list[dict[str, object]] = [organism_info]
    termination_reason: str | None = None
    first_stationary_charge_transition: int | None = None
    battery_increased_on_first_stationary_charge: bool | None = None
    invalid_beacon = False
    terminated = False
    truncated = False

    for step_index in range(1, D049_CASE_HORIZON + 1):
        decision = controller.command(observation)
        transition_authority.append("LEVEL_1")
        action_trace.append(
            (decision.wheel_delta_left, decision.wheel_delta_right)
        )
        if decision.mode is D049ControlMode.INVALID_BEACON:
            invalid_beacon = True
        if decision.mode is D049ControlMode.TURN:
            turn_count += 1
        elif decision.mode is D049ControlMode.STRAIGHT:
            straight_count += 1
            if decision.reconstruction is not None:
                straight_command_distance += decision.reconstruction.distance_m
        elif decision.mode is D049ControlMode.TERMINAL_SPIN:
            terminal_spin_count += 1
            if center_reached_transition is None:
                center_reached_transition = step_index - 1

        before_position = env.body.position if env.body is not None else None
        before_contact = bool(observation[5])
        observation, reward, terminated, truncated, organism_info = env.step(
            (decision.wheel_delta_left, decision.wheel_delta_right)
        )
        telemetry = env.last_transition
        if telemetry is None or before_position is None:
            raise RuntimeError("D-045 did not provide transition telemetry")
        if decision.mode is D049ControlMode.STRAIGHT:
            straight_actual_distance += math.dist(
                telemetry.position_before, telemetry.position_after
            )
        rewards.append(reward)
        organism_infos.append(organism_info)

        after_contact = bool(observation[5])
        if not before_contact and after_contact and first_contact_transition is None:
            first_contact_transition = step_index
            first_contact_battery_before = telemetry.battery_before_j
            first_contact_pair_error = (
                telemetry.dock_plus_error_m,
                telemetry.dock_minus_error_m,
            )
        elif (
            first_contact_transition == 0
            and first_contact_pair_error is None
        ):
            first_contact_pair_error = (
                telemetry.dock_plus_error_m,
                telemetry.dock_minus_error_m,
            )
        if (
            decision.mode is D049ControlMode.CONTACT
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
        if (
            terminal_spin_count >= D049_TERMINAL_SPIN_MAX_STEPS
            and not after_contact
        ):
            break

    transition_count = len(transition_authority)
    contact_acquired = first_contact_transition is not None
    if invalid_beacon:
        failure_classification = "INVALID_BEACON"
    elif first_stationary_charge_transition is not None:
        if battery_increased_on_first_stationary_charge:
            failure_classification = "DOCKED_AND_CHARGING"
        else:
            failure_classification = "CONTACT_WITHOUT_CHARGE"
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

    return {
        "case_id": case.case_id,
        "case_group": case.case_group,
        "radius_m": case.radius_m,
        "position_bearing_deg": case.position_bearing_deg,
        "initial_heading_class": case.initial_heading_class,
        "initial_body_position": list(case.body_position),
        "initial_heading_rad": case.heading_rad,
        "horizon": D049_CASE_HORIZON,
        "transition_count": transition_count,
        "level1_authority_transition_count": transition_count,
        "level1_authority_fraction": 1.0 if transition_count else 0.0,
        "beacon_reconstruction_valid": not invalid_beacon,
        "coarse_return_step_count": turn_count + straight_count,
        "turn_count": turn_count,
        "straight_command_distance_m": straight_command_distance,
        "straight_actual_distance_m": straight_actual_distance,
        "reconstructed_centre_reached": center_reached_transition is not None,
        "centre_reached_transition": center_reached_transition,
        "terminal_spin_step_count": terminal_spin_count,
        "charging_contact_acquired": contact_acquired,
        "first_contact_transition": first_contact_transition,
        "battery_energy_consumed_before_first_contact_j": (
            initial_battery - first_contact_battery_before
            if first_contact_battery_before is not None
            else None
        ),
        "contact_pair_error_at_first_contact_m": (
            list(first_contact_pair_error)
            if first_contact_pair_error is not None
            else None
        ),
        "first_stationary_zero_wheel_charging_transition": (
            first_stationary_charge_transition
        ),
        "battery_increased_on_first_stationary_charge": (
            battery_increased_on_first_stationary_charge
        ),
        "terminated": terminated,
        "truncated": truncated,
        "termination_reason": (
            telemetry.termination_reason.value
            if (telemetry := env.last_transition) is not None
            and telemetry.termination_reason is not None
            else termination_reason
        ),
        "failure_classification": failure_classification,
        "reward_values": rewards,
        "organism_info_values": organism_infos,
        "transition_authority": transition_authority,
        "action_trace": [list(action) for action in action_trace],
    }


def _protocol_record() -> dict[str, object]:
    return {
        "station_center": list(D049_STATION_CENTER),
        "return_radii_m": list(D049_RETURN_RADII_M),
        "position_bearings_deg": list(D049_POSITION_BEARINGS_DEG),
        "initial_heading_classes": [
            {"name": name, "source_relative_bearing_rad": relative}
            for name, relative in D049_INITIAL_HEADING_CLASSES
        ],
        "terminal_headings_rad": list(D049_TERMINAL_HEADINGS_RAD),
        "case_horizon": D049_CASE_HORIZON,
        "centre_tolerance_m": D049_CENTRE_TOLERANCE_M,
        "angular_tolerance_rad": D049_ANGULAR_TOLERANCE_RAD,
        "terminal_spin_max_steps": D049_TERMINAL_SPIN_MAX_STEPS,
        "terminal_spin_direction": D049_TERMINAL_SPIN_DIRECTION,
        "max_in_place_turn_degrees": math.degrees(
            2.0
            * D045_WHEEL_RADIUS_METRES
            * D045_MAX_WHEEL_DELTA_RAD
            / D045_WHEEL_TRACK_WIDTH_METRES
        ),
        "centred_contact_half_window_degrees": math.degrees(
            2.0
            * math.asin(
                D045_CONTACT_TOLERANCE_METRES
                / (2.0 * D045_CONTACT_OFFSET_METRES)
            )
        ),
        "observation_channels_used": [2, 3, 4, 5],
        "observation_channel_count": 8,
        "return_activation": "diagnostic harness at reset",
        "learned_state": "absent",
        "reward": 0.0,
        "organism_info": {},
    }


def _actual_body_relative_source(
    case: D049Case, station_center: tuple[float, float]
) -> tuple[float, float]:
    dx = station_center[0] - case.body_position[0]
    dy = station_center[1] - case.body_position[1]
    cosine = math.cos(case.heading_rad)
    sine = math.sin(case.heading_rad)
    return (cosine * dx + sine * dy, -sine * dx + cosine * dy)


def _as_json_record(value: object) -> dict[str, object]:
    if isinstance(value, D049InverseSummary):
        return {
            "valid_cases": value.valid_cases,
            "invalid_cases": value.invalid_cases,
            "max_coordinate_error_m": value.max_coordinate_error_m,
            "max_distance_error_m": value.max_distance_error_m,
            "max_bearing_error_rad": value.max_bearing_error_rad,
            "within_frozen_limits": value.within_frozen_limits,
        }
    raise TypeError(f"unsupported record type: {type(value).__name__}")


def main() -> None:
    """CLI entry point for the official frozen D-049 diagnostic."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--executed-commit-sha", required=True)
    args = parser.parse_args()
    write_d049_artifact(args.output, args.executed_commit_sha)


if __name__ == "__main__":
    main()
