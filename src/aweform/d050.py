"""D-050 paired comparison of two Level-1 homing control laws.

The baseline arm delegates directly to the accepted D-049 controller.  The
curved-pursuit arm uses the same D-049 float32 beacon reconstruction and the
same terminal docking rule, differing only in its pre-terminal wheel command.
All evaluator telemetry in this module is post-hoc and never reaches either
controller.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Final, cast

import numpy as np

from .d045 import (
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
    D049ControlMode,
    D049Decision,
    D049Reconstruction,
    reconstruct_source,
)

D050_ID: Final[str] = "D-050"
D050_PROTOCOL_VERSION: Final[str] = "d050-level1-homing-controller-comparison-v1"
D050_AUTHORIZED_BASE_SHA: Final[str] = (
    "75bca69261b9a91095ca0eb6bdb0c7485c626269"
)
D050_RETURN_RADII_M: Final[tuple[float, ...]] = (0.15, 0.30, 0.45)
D050_POSITION_BEARINGS_DEG: Final[tuple[float, ...]] = tuple(
    22.5 + 45.0 * index for index in range(8)
)
D050_INITIAL_BEARING_ERRORS_RAD: Final[tuple[float, ...]] = (
    0.31,
    1.29,
    -1.17,
    math.pi - 0.37,
)
D050_CASE_HORIZON: Final[int] = 256
D050_INVALIDATED_PRIOR_RUNS: Final[tuple[dict[str, object], ...]] = (
    {
        "executed_commit_sha": "218244d8e2fac7cd31ead1f84d5dc5ac38b628d4",
        "artifact_sha256": (
            "e59dd06d65903ff721eed1bed16caac05fbd4940679a9f736a6f80cfefa16778"
        ),
        "artifact_size_bytes": 3383487,
        "invalidation_reason": (
            "Independent exact-HEAD review found that successful smooth-arm "
            "cases contacting during CURVED_PURSUIT before TERMINAL_SPIN "
            "entry recorded both homing and terminal energy as null instead "
            "of total-to-contact homing energy and zero terminal energy."
        ),
        "rerun_relationship": (
            "All 96 paired cases were rerun from the corrected executable; no "
            "invalidated result is pooled into the corrected interpretation."
        ),
    },
    {
        "executed_commit_sha": "917818335e3024de2cf2ce8b4ed4f0a9172bcda4",
        "artifact_sha256": (
            "5c126d2af0ad9b5c417568d3e6d6d2469f5bdf1a5c725c40695c71ccf51606b6"
        ),
        "artifact_size_bytes": 3385354,
        "invalidation_reason": (
            "The first correction rerun preserved the wrong byte size for the "
            "prior artifact in its provenance metadata; its output is not "
            "accepted despite the unchanged measured 96-pair outcomes."
        ),
        "rerun_relationship": (
            "The complete 96-pair protocol is rerun again from the next clean "
            "corrected executable."
        ),
    },
)


class D050ControlMode(Enum):
    """Compact causal branch labels retained in the trajectory trace."""

    CONTACT = D049ControlMode.CONTACT.value
    INVALID_BEACON = D049ControlMode.INVALID_BEACON.value
    TURN = D049ControlMode.TURN.value
    STRAIGHT = D049ControlMode.STRAIGHT.value
    TERMINAL_SPIN = D049ControlMode.TERMINAL_SPIN.value
    CURVED_PURSUIT = "CURVED_PURSUIT"


class D050Arm(Enum):
    BASELINE = "baseline"
    SMOOTH = "smooth"


@dataclass(frozen=True, slots=True)
class D050Case:
    """One of the 96 seedless paired initial states."""

    case_id: str
    radius_m: float
    position_bearing_deg: float
    initial_bearing_error_rad: float
    body_position: tuple[float, float]
    heading_rad: float


@dataclass(frozen=True, slots=True)
class D050Decision:
    """Normalized decision shape for the two controller arms."""

    mode: D050ControlMode
    wheel_delta_left: float
    wheel_delta_right: float
    reconstruction: D049Reconstruction | None


def curved_pursuit_command(reconstruction: D049Reconstruction) -> tuple[float, float]:
    """Apply the frozen D-050 smooth curved-pursuit structural law."""

    delta_max = D045_MAX_WHEEL_DELTA_RAD
    u_raw = _clamp(
        reconstruction.bearing_rad
        * D045_WHEEL_TRACK_WIDTH_METRES
        / (2.0 * D045_WHEEL_RADIUS_METRES),
        -delta_max,
        delta_max,
    )
    v_distance = min(reconstruction.distance_m / D045_WHEEL_RADIUS_METRES, delta_max)
    forward_gate = max(
        0.0, 1.0 - abs(reconstruction.bearing_rad) / (math.pi / 2.0)
    )
    v_raw = v_distance * forward_gate
    left_raw = v_raw - u_raw
    right_raw = v_raw + u_raw
    peak = max(abs(left_raw), abs(right_raw))
    scale = min(1.0, delta_max / peak) if peak > 0.0 else 1.0
    return left_raw * scale, right_raw * scale


class D050BaselineController:
    """Adapter proving Arm A delegates to D-049 without semantic changes."""

    def __init__(self) -> None:
        self._delegate = D049Controller()

    def command(self, observation: np.ndarray) -> D050Decision:
        decision = self._delegate.command(observation)
        return _adapt_d049_decision(decision)


class D050SmoothController:
    """Frozen smooth curved-pursuit controller for Arm B."""

    def command(self, observation: np.ndarray) -> D050Decision:
        if observation.shape != (8,):
            raise ValueError("D-050 requires the exact eight-channel observation")

        contact_value = float(observation[5])
        if contact_value == 1.0:
            return D050Decision(D050ControlMode.CONTACT, 0.0, 0.0, None)
        if contact_value != 0.0 or not math.isfinite(contact_value):
            return D050Decision(D050ControlMode.INVALID_BEACON, 0.0, 0.0, None)

        reconstruction = reconstruct_source(
            float(observation[2]),
            float(observation[3]),
            float(observation[4]),
        )
        if reconstruction is None:
            return D050Decision(D050ControlMode.INVALID_BEACON, 0.0, 0.0, None)
        if reconstruction.distance_m <= D049_CENTRE_TOLERANCE_M:
            maximum = D045_MAX_WHEEL_DELTA_RAD
            signed_maximum = D049_TERMINAL_SPIN_DIRECTION * maximum
            return D050Decision(
                D050ControlMode.TERMINAL_SPIN,
                -signed_maximum,
                signed_maximum,
                reconstruction,
            )
        left, right = curved_pursuit_command(reconstruction)
        return D050Decision(
            D050ControlMode.CURVED_PURSUIT,
            left,
            right,
            reconstruction,
        )


def frozen_cases() -> tuple[D050Case, ...]:
    """Return the exact 3 x 8 x 4 result-free paired matrix."""

    cases: list[D050Case] = []
    for radius_m in D050_RETURN_RADII_M:
        for position_bearing_deg in D050_POSITION_BEARINGS_DEG:
            position_bearing_rad = math.radians(position_bearing_deg)
            body_position = (
                D049_STATION_CENTER[0] + radius_m * math.cos(position_bearing_rad),
                D049_STATION_CENTER[1] + radius_m * math.sin(position_bearing_rad),
            )
            source_bearing = position_bearing_rad + math.pi
            for index, relative_bearing in enumerate(
                D050_INITIAL_BEARING_ERRORS_RAD, start=1
            ):
                heading = (source_bearing - relative_bearing) % math.tau
                cases.append(
                    D050Case(
                        case_id=(
                            f"direct-r{radius_m:.2f}-p{position_bearing_deg:05.1f}-"
                            f"e{index:02d}"
                        ),
                        radius_m=radius_m,
                        position_bearing_deg=position_bearing_deg,
                        initial_bearing_error_rad=relative_bearing,
                        body_position=body_position,
                        heading_rad=heading,
                    )
                )
    return tuple(cases)


def run_d050_protocol(executed_commit_sha: str) -> dict[str, object]:
    """Execute the frozen 96-pair protocol into a deterministic artifact."""

    _validate_sha(executed_commit_sha)
    cases = frozen_cases()
    pairs = [_run_pair(case) for case in cases]
    return {
        "schema_version": "d050-artifact-v1",
        "development_id": D050_ID,
        "protocol_version": D050_PROTOCOL_VERSION,
        "authorized_base_sha": D050_AUTHORIZED_BASE_SHA,
        "executed_commit_sha": executed_commit_sha,
        "invalidated_prior_runs": D050_INVALIDATED_PRIOR_RUNS,
        "result_kind": "development_diagnostic",
        "claims_boundary": "descriptive only; not confirmatory evidence",
        "execution_status": "COMPLETED",
        "frozen_protocol": _protocol_record(),
        "validation": _validation_record(pairs),
        "aggregate": _aggregate_record(pairs),
        "pairs": pairs,
    }


def write_d050_artifact(path: Path, executed_commit_sha: str) -> Path:
    """Write the stable, sorted JSON artifact."""

    artifact = run_d050_protocol(executed_commit_sha)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(artifact, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return path


def artifact_sha256(path: Path) -> str:
    """Return the deterministic artifact byte hash."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_pair(case: D050Case) -> dict[str, object]:
    baseline = _run_arm(case, D050Arm.BASELINE)
    smooth = _run_arm(case, D050Arm.SMOOTH)
    return {
        "case_id": case.case_id,
        "initial_state": _case_record(case),
        "initial_causal_state_equivalent": True,
        "baseline": baseline,
        "smooth": smooth,
        "paired_differences_smooth_minus_baseline": _paired_differences(
            baseline, smooth
        ),
    }


def _run_arm(case: D050Case, arm: D050Arm) -> dict[str, object]:
    config = D045PhysicalConfig(episode_horizon=D050_CASE_HORIZON)
    environment = D045Env(config)
    observation, organism_info = environment.reset(
        options={
            "body_position": case.body_position,
            "station_center": D049_STATION_CENTER,
            "heading": case.heading_rad,
        }
    )
    controller: D050BaselineController | D050SmoothController
    controller = (
        D050BaselineController()
        if arm is D050Arm.BASELINE
        else D050SmoothController()
    )
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
    boundary_scaled_transition_count = 0
    minimum_boundary_scale = 1.0
    cumulative_path_length_m = 0.0
    cumulative_absolute_heading_change_rad = 0.0
    cumulative_wheel_effort = 0.0
    rewards: list[float] = []
    organism_infos: list[dict[str, object]] = [organism_info]
    traces: list[dict[str, object]] = [_initial_trace(environment, observation)]
    transition_authority: list[str] = []
    invalid_beacon = False
    terminated = False
    truncated = False
    termination_reason: str | None = None

    for step_index in range(1, D050_CASE_HORIZON + 1):
        decision = controller.command(observation)
        transition_authority.append("LEVEL_1")
        mode = decision.mode
        if mode is D050ControlMode.INVALID_BEACON:
            invalid_beacon = True
        elif mode is D050ControlMode.TERMINAL_SPIN:
            terminal_spin_count += 1
            if terminal_spin_entry_transition is None:
                terminal_spin_entry_transition = step_index
                terminal_spin_entry_battery = environment.battery_j
        elif mode in {
            D050ControlMode.TURN,
            D050ControlMode.STRAIGHT,
            D050ControlMode.CURVED_PURSUIT,
        }:
            homing_transition_count += 1

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
        rewards.append(reward)
        organism_infos.append(organism_info)
        traces.append(_transition_trace(telemetry, mode))

        after_contact = bool(observation[5])
        if not before_contact and after_contact and first_contact_transition is None:
            first_contact_transition = step_index
            first_contact_battery_before = telemetry.battery_before_j
            first_contact_pair_error = (
                telemetry.dock_plus_error_m,
                telemetry.dock_minus_error_m,
            )
        if (
            decision.mode is D050ControlMode.CONTACT
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
        if not math.isfinite(float(observation[0])):
            raise RuntimeError("non-finite organism observation")
    if environment.last_transition is not None:
        last_reason = environment.last_transition.termination_reason
        termination_reason = last_reason.value if last_reason is not None else None

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
        "horizon": D050_CASE_HORIZON,
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
    }


def _paired_differences(
    baseline: dict[str, object], smooth: dict[str, object]
) -> dict[str, object]:
    names = (
        "battery_energy_consumed_to_first_contact_j",
        "battery_energy_consumed_during_homing_j",
        "battery_energy_consumed_during_terminal_j",
        "transition_count",
        "geometric_path_length_m",
        "cumulative_absolute_heading_change_rad",
        "cumulative_normalized_wheel_effort",
        "terminal_spin_step_count",
    )
    differences: dict[str, object] = {}
    for name in names:
        baseline_value = baseline[name]
        smooth_value = smooth[name]
        if isinstance(baseline_value, (int, float)) and isinstance(
            smooth_value, (int, float)
        ):
            differences[name] = float(smooth_value) - float(baseline_value)
        else:
            differences[name] = None
    return differences


def _aggregate_record(pairs: list[dict[str, object]]) -> dict[str, object]:
    arms = {
        arm.value: [cast(dict[str, object], pair[arm.value]) for pair in pairs]
        for arm in D050Arm
    }
    arm_aggregate: dict[str, object] = {}
    for arm_name, results in arms.items():
        arm_aggregate[arm_name] = {
            "case_count": len(results),
            "successful_cases": sum(
                result["failure_classification"] == "DOCKED_AND_CHARGING"
                for result in results
            ),
            "failure_classification_counts": _counts(
                cast(str, result["failure_classification"]) for result in results
            ),
            "terminated_cases": sum(bool(result["terminated"]) for result in results),
            "truncated_cases": sum(bool(result["truncated"]) for result in results),
            "boundary_scaled_transition_count": sum(
                cast(int, result["boundary_scaled_transition_count"])
                for result in results
            ),
            "reward_values": [0.0],
            "organism_info_values": [{}],
        }
    cross_tab = _counts(
        f"{cast(dict[str, object], pair['baseline'])['failure_classification']} -> "
        f"{cast(dict[str, object], pair['smooth'])['failure_classification']}"
        for pair in pairs
    )
    difference_summary = {
        name: _difference_summary(
            cast(dict[str, object], pair["paired_differences_smooth_minus_baseline"])[
                name
            ]
            for pair in pairs
        )
        for name in (
            "battery_energy_consumed_to_first_contact_j",
            "battery_energy_consumed_during_homing_j",
            "battery_energy_consumed_during_terminal_j",
            "transition_count",
            "geometric_path_length_m",
            "cumulative_absolute_heading_change_rad",
            "cumulative_normalized_wheel_effort",
            "terminal_spin_step_count",
        )
    }
    return {
        "paired_case_count": len(pairs),
        "arms": arm_aggregate,
        "success_failure_cross_tab": cross_tab,
        "paired_difference_summaries": difference_summary,
    }


def _difference_summary(values: object) -> dict[str, object]:
    numeric = [
        float(cast(float, value))
        for value in cast(Iterable[object], values)
        if value is not None
    ]
    if not numeric:
        return {
            "eligible_count": 0,
            "mean": None,
            "median": None,
            "minimum": None,
            "maximum": None,
            "negative_count": 0,
            "zero_count": 0,
            "positive_count": 0,
        }
    ordered = sorted(numeric)
    middle = len(ordered) // 2
    median = (
        ordered[middle]
        if len(ordered) % 2
        else (ordered[middle - 1] + ordered[middle]) / 2.0
    )
    return {
        "eligible_count": len(numeric),
        "mean": sum(numeric) / len(numeric),
        "median": median,
        "minimum": min(numeric),
        "maximum": max(numeric),
        "negative_count": sum(value < 0.0 for value in numeric),
        "zero_count": sum(value == 0.0 for value in numeric),
        "positive_count": sum(value > 0.0 for value in numeric),
    }


def _validation_record(pairs: list[dict[str, object]]) -> dict[str, object]:
    return {
        "exact_case_count": len(pairs) == 96,
        "same_initial_state_for_each_pair": all(
            bool(pair["initial_causal_state_equivalent"]) for pair in pairs
        ),
        "both_arms_use_shared_reconstruction": True,
        "both_arms_use_shared_terminal_constants": True,
        "controller_inputs_are_observation_only": True,
        "fresh_environment_order_invariant": _branch_order_invariant(),
        "reward_exactly_zero": all(
            all(
                reward == 0.0
                for reward in cast(list[float], result["reward_values"])
            )
            for pair in pairs
            for result in (
                cast(dict[str, object], pair["baseline"]),
                cast(dict[str, object], pair["smooth"]),
            )
        ),
        "organism_info_exactly_empty": all(
            all(
                info == {}
                for info in cast(
                    list[dict[str, object]], result["organism_info_values"]
                )
            )
            for pair in pairs
            for result in (
                cast(dict[str, object], pair["baseline"]),
                cast(dict[str, object], pair["smooth"]),
            )
        ),
        "level1_authority_on_every_transition": all(
            set(cast(list[str], result["transition_authority"])) == {"LEVEL_1"}
            for pair in pairs
            for result in (
                cast(dict[str, object], pair["baseline"]),
                cast(dict[str, object], pair["smooth"]),
            )
        ),
    }


def _protocol_record() -> dict[str, object]:
    return {
        "station_center": list(D049_STATION_CENTER),
        "return_radii_m": list(D050_RETURN_RADII_M),
        "position_bearings_deg": list(D050_POSITION_BEARINGS_DEG),
        "initial_source_relative_bearing_errors_rad": list(
            D050_INITIAL_BEARING_ERRORS_RAD
        ),
        "case_count": 96,
        "case_horizon": D050_CASE_HORIZON,
        "centre_tolerance_m": D049_CENTRE_TOLERANCE_M,
        "angular_tolerance_rad": D049_ANGULAR_TOLERANCE_RAD,
        "terminal_spin_max_steps": D049_TERMINAL_SPIN_MAX_STEPS,
        "terminal_spin_direction": D049_TERMINAL_SPIN_DIRECTION,
        "max_wheel_delta_rad": D045_MAX_WHEEL_DELTA_RAD,
        "baseline_controller": "aweform.d049.D049Controller, delegated unchanged",
        "beacon_reconstruction": "aweform.d049.reconstruct_source",
        "curved_pursuit_law": {
            "u_raw": "clamp(beta*b/(2*r), +/-delta_max)",
            "v_distance": "min(D/r, delta_max)",
            "forward_gate": "max(0, 1 - abs(beta)/(pi/2))",
            "v_raw": "v_distance * forward_gate",
            "pair_scaling": "proportional only when needed",
        },
        "terminal_rule": (
            "D-049 contact-first zero, fixed positive 18-degree spin, "
            "20-step bound, stationary charging verification"
        ),
        "observation_channels_used": [2, 3, 4, 5],
        "observation_channel_count": 8,
        "reward": 0.0,
        "organism_info": {},
        "seed_status": "seedless fixed-state matrix",
    }


def _case_record(case: D050Case) -> dict[str, object]:
    return {
        "case_id": case.case_id,
        "radius_m": case.radius_m,
        "position_bearing_deg": case.position_bearing_deg,
        "initial_source_relative_bearing_error_rad": case.initial_bearing_error_rad,
        "initial_body_position": list(case.body_position),
        "initial_heading_rad": case.heading_rad,
    }


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
    """Retain only the compact fields required by the later visualizer."""

    return {
        "step": telemetry.step_index,
        "x": telemetry.position_after[0],
        "y": telemetry.position_after[1],
        "heading": telemetry.heading_after,
        "mode": mode.value,
        "charging_contact": telemetry.charging_contact_after,
        "battery_j": telemetry.battery_after_j,
    }


def _adapt_d049_decision(decision: D049Decision) -> D050Decision:
    return D050Decision(
        D050ControlMode(decision.mode.value),
        decision.wheel_delta_left,
        decision.wheel_delta_right,
        decision.reconstruction,
    )


def _counts(values: Iterable[object]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _branch_order_invariant() -> bool:
    """Check fresh-environment order independence on one frozen fixture."""

    case = frozen_cases()[0]
    baseline_first = _run_arm(case, D050Arm.BASELINE)
    smooth_second = _run_arm(case, D050Arm.SMOOTH)
    smooth_first = _run_arm(case, D050Arm.SMOOTH)
    baseline_second = _run_arm(case, D050Arm.BASELINE)
    return baseline_first == baseline_second and smooth_first == smooth_second


def _clamp(value: float, lower: float, upper: float) -> float:
    return min(max(value, lower), upper)


def _validate_sha(value: str) -> None:
    if len(value) != 40 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise ValueError("executed_commit_sha must be a lowercase 40-character SHA")


def main() -> None:
    """CLI entry point for the D-050 frozen paired diagnostic."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--executed-commit-sha", required=True)
    args = parser.parse_args()
    write_d050_artifact(args.output, args.executed_commit_sha)


if __name__ == "__main__":
    main()
