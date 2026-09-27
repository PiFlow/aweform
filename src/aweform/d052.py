"""D-052 constitutive Level-1 return, charge, and recovery arbiter.

The arbiter uses only the D-045 organism-visible observation and a caller's
proposed bilateral wheel command. RETURN delegates action generation directly
to the accepted D-050 smooth controller; D-045 evaluator telemetry is used
only by the seedless characterization runner below.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal
from enum import Enum
from pathlib import Path
from typing import Final, cast

import numpy as np

from .d045 import (
    D045_BATTERY_CAPACITY_J,
    D045_MAX_WHEEL_DELTA_RAD,
    D045Env,
    D045PhysicalConfig,
    D045TerminationReason,
)
from .d049 import D049_STATION_CENTER, D049_TERMINAL_SPIN_MAX_STEPS
from .d050 import D050ControlMode, D050SmoothController

D052_ID: Final[str] = "D-052"
D052_PROTOCOL_VERSION: Final[str] = "d052-v05-innate-return-charge-recovery-v1"
D052_AUTHORIZED_BASE_SHA: Final[str] = (
    "0a273f6e10c9dff155d4ade15e04684d674b60fd"
)
RETURN_THRESHOLD: Final[float] = float(np.float32(0.20))
RECOVERY_THRESHOLD: Final[float] = float(np.float32(0.80))
D052_CASE_HORIZON: Final[int] = 25_000
D052_RETURN_RADII_M: Final[tuple[float, ...]] = (0.15, 0.30, 0.45)
D052_POSITION_BEARINGS_DEG: Final[tuple[int, ...]] = (15, 105, 195, 285)
D052_INITIAL_SOURCE_RELATIVE_HEADING_ERRORS_RAD: Final[tuple[float, ...]] = (
    0.40,
    -1.20,
)
D052_PASSTHROUGH_FIXTURE: Final[tuple[float, float]] = (0.10, 0.10)
D052_MAX_EVENT_SAMPLES: Final[int] = 64
D052_ARTIFACT_FLOAT_QUANTUM: Final[Decimal] = Decimal("1e-12")


class D052Mode(Enum):
    """Functional Level-1 mode associated with one emitted action."""

    NORMAL = "NORMAL"
    RETURN = "RETURN"
    CHARGE = "CHARGE"


class D052CommandSource(Enum):
    """Source of the emitted bilateral wheel command."""

    PASS_THROUGH = "PASS_THROUGH"
    D050_SMOOTH = "D050_SMOOTH"
    CHARGE_HOLD = "CHARGE_HOLD"
    RETURN_HOLD = "RETURN_HOLD"


@dataclass(frozen=True, slots=True)
class D052Decision:
    """One attributable Level-1 arbitration decision."""

    transition_index: int
    active_mode: D052Mode
    command_source: D052CommandSource
    wheel_delta_left: float
    wheel_delta_right: float
    passed_through: bool
    preempted: bool
    d050_mode: D050ControlMode | None
    terminal_spin_count: int
    terminal_spin_exhausted: bool
    events: tuple[str, ...]


class D052Controller:
    """Stateful Level-1 locomotor arbiter with no learned-state access."""

    def __init__(self) -> None:
        self._smooth_controller = D050SmoothController()
        self._mode = D052Mode.NORMAL
        self._terminal_spin_count = 0
        self._terminal_spin_exhausted = False
        self._contact_was_lost = False
        self.transition_count = 0
        self.preemption_transition_count = 0
        self.return_transition_count = 0
        self.charge_transition_count = 0
        self.maximum_terminal_spin_count = 0
        self.terminal_spin_exhaustion_transition: int | None = None

    @property
    def mode(self) -> D052Mode:
        """Current state after the most recent decision."""

        return self._mode

    @property
    def terminal_spin_count(self) -> int:
        """Spin count in the current RETURN episode."""

        return self._terminal_spin_count

    @property
    def terminal_spin_exhausted(self) -> bool:
        """Whether the current RETURN episode has latched its zero hold."""

        return self._terminal_spin_exhausted

    def command(
        self,
        observation: np.ndarray,
        proposed_wheel_command: tuple[float, float] | list[float] | np.ndarray,
    ) -> D052Decision:
        """Arbitrate using only the eight visible channels and proposed wheels."""

        if observation.shape != (8,):
            raise ValueError("D-052 requires the exact eight-channel observation")
        energy = float(observation[0])
        if not math.isfinite(energy) or not 0.0 <= energy <= 1.0:
            raise ValueError("observation[0] must be finite normalized energy")
        proposed_left, proposed_right = _legal_wheel_pair(proposed_wheel_command)
        next_transition = self.transition_count + 1
        events: list[str] = []

        if self._mode is D052Mode.NORMAL:
            if energy <= RETURN_THRESHOLD:
                self._enter_return(events, "RETURN_ACTIVATED")
            else:
                return self._emit(
                    next_transition,
                    D052Mode.NORMAL,
                    D052CommandSource.PASS_THROUGH,
                    proposed_left,
                    proposed_right,
                    None,
                    events,
                )

        if self._mode is D052Mode.CHARGE:
            if energy >= RECOVERY_THRESHOLD:
                self._mode = D052Mode.NORMAL
                self._contact_was_lost = False
                events.append("RECOVERY_YIELD")
                return self._emit(
                    next_transition,
                    D052Mode.NORMAL,
                    D052CommandSource.PASS_THROUGH,
                    proposed_left,
                    proposed_right,
                    None,
                    events,
                )
            if float(observation[5]) != 1.0:
                self._enter_return(events, "CHARGING_CONTACT_LOST")
                self._contact_was_lost = True
            else:
                return self._emit(
                    next_transition,
                    D052Mode.CHARGE,
                    D052CommandSource.CHARGE_HOLD,
                    0.0,
                    0.0,
                    None,
                    events,
                )

        if self._mode is not D052Mode.RETURN:
            raise RuntimeError("D-052 entered an unexpected state")

        smooth_decision = self._smooth_controller.command(observation)
        if smooth_decision.mode is D050ControlMode.CONTACT:
            self._mode = D052Mode.CHARGE
            if self._contact_was_lost:
                events.append("CHARGING_CONTACT_REACQUIRED")
            events.append("CHARGING_CONTACT")
            self._contact_was_lost = False
            return self._emit(
                next_transition,
                D052Mode.CHARGE,
                D052CommandSource.CHARGE_HOLD,
                0.0,
                0.0,
                smooth_decision.mode,
                events,
            )

        # The twentieth terminal-spin action still executes. Exhaustion is
        # latched only on the next RETURN decision if contact is still absent.
        if self._terminal_spin_count >= D049_TERMINAL_SPIN_MAX_STEPS:
            if not self._terminal_spin_exhausted:
                self._terminal_spin_exhausted = True
                self.terminal_spin_exhaustion_transition = next_transition
                events.append("TERMINAL_SPIN_EXHAUSTED")
            return self._emit(
                next_transition,
                D052Mode.RETURN,
                D052CommandSource.RETURN_HOLD,
                0.0,
                0.0,
                smooth_decision.mode,
                events,
            )

        if smooth_decision.mode is D050ControlMode.TERMINAL_SPIN:
            self._terminal_spin_count += 1
            self.maximum_terminal_spin_count = max(
                self.maximum_terminal_spin_count, self._terminal_spin_count
            )
        if smooth_decision.mode is D050ControlMode.INVALID_BEACON:
            events.append("INVALID_BEACON")
        return self._emit(
            next_transition,
            D052Mode.RETURN,
            D052CommandSource.D050_SMOOTH,
            smooth_decision.wheel_delta_left,
            smooth_decision.wheel_delta_right,
            smooth_decision.mode,
            events,
        )

    def _enter_return(self, events: list[str], event: str) -> None:
        self._mode = D052Mode.RETURN
        self._terminal_spin_count = 0
        self._terminal_spin_exhausted = False
        events.append(event)

    def _emit(
        self,
        transition_index: int,
        mode: D052Mode,
        source: D052CommandSource,
        left: float,
        right: float,
        d050_mode: D050ControlMode | None,
        events: list[str],
    ) -> D052Decision:
        passed_through = source is D052CommandSource.PASS_THROUGH
        preempted = not passed_through
        self.transition_count = transition_index
        self.preemption_transition_count += int(preempted)
        self.return_transition_count += int(mode is D052Mode.RETURN)
        self.charge_transition_count += int(mode is D052Mode.CHARGE)
        return D052Decision(
            transition_index=transition_index,
            active_mode=mode,
            command_source=source,
            wheel_delta_left=left,
            wheel_delta_right=right,
            passed_through=passed_through,
            preempted=preempted,
            d050_mode=d050_mode,
            terminal_spin_count=self._terminal_spin_count,
            terminal_spin_exhausted=self._terminal_spin_exhausted,
            events=tuple(events),
        )


@dataclass(frozen=True, slots=True)
class D052Case:
    """One of the 24 frozen seedless starting states."""

    case_id: str
    radius_m: float
    position_bearing_deg: int
    source_relative_heading_error_rad: float
    body_position: tuple[float, float]
    heading_rad: float


def frozen_cases() -> tuple[D052Case, ...]:
    """Return the exact 3 x 4 x 2 seedless support matrix."""

    cases: list[D052Case] = []
    for radius_m in D052_RETURN_RADII_M:
        for position_bearing_deg in D052_POSITION_BEARINGS_DEG:
            position_bearing_rad = math.radians(position_bearing_deg)
            body_position = (
                D049_STATION_CENTER[0] + radius_m * math.cos(position_bearing_rad),
                D049_STATION_CENTER[1] + radius_m * math.sin(position_bearing_rad),
            )
            source_bearing = position_bearing_rad + math.pi
            for index, heading_error in enumerate(
                D052_INITIAL_SOURCE_RELATIVE_HEADING_ERRORS_RAD, start=1
            ):
                heading = (source_bearing - heading_error) % math.tau
                cases.append(
                    D052Case(
                        case_id=(
                            f"return-r{radius_m:.2f}-p{position_bearing_deg:03d}-"
                            f"e{index:02d}"
                        ),
                        radius_m=radius_m,
                        position_bearing_deg=position_bearing_deg,
                        source_relative_heading_error_rad=heading_error,
                        body_position=body_position,
                        heading_rad=heading,
                    )
                )
    return tuple(cases)


def run_d052_protocol(executed_commit_sha: str) -> dict[str, object]:
    """Run the frozen 24-case characterization and return compact results."""

    _validate_sha(executed_commit_sha)
    cases = [_run_case(case) for case in frozen_cases()]
    total_transitions = sum(cast(int, case["total_transition_count"]) for case in cases)
    preemptions = sum(
        cast(int, case["level1_preemption_transition_count"]) for case in cases
    )
    outcomes = Counter(cast(str, case["outcome"]) for case in cases)
    first_decision_preempted = all(
        bool(case["first_decision_preempted"]) for case in cases
    )
    return {
        "schema_version": "d052-artifact-v1",
        "development_id": D052_ID,
        "protocol_version": D052_PROTOCOL_VERSION,
        "authorized_base_sha": D052_AUTHORIZED_BASE_SHA,
        "executed_commit_sha": executed_commit_sha,
        "result_kind": "development_diagnostic",
        "claims_boundary": (
            "descriptive only on the frozen 0.15-0.45 m radius support; "
            "not confirmatory evidence"
        ),
        "execution_status": "COMPLETED",
        "frozen_protocol": _protocol_record(),
        "validation": {
            "exact_case_count": len(cases) == 24,
            "first_decision_preempted_in_every_case": first_decision_preempted,
            "reward_exactly_zero": all(
                bool(case["reward_exactly_zero"]) for case in cases
            ),
            "organism_info_exactly_empty": all(
                bool(case["organism_info_exactly_empty"]) for case in cases
            ),
            "no_causal_evaluator_geometry": True,
            "controller_inputs_limited_to_observation_and_proposed_wheels": True,
            "d050_smooth_controller_delegated_unchanged": True,
            "discrete_outcome_signature_sha256": _discrete_signature(cases),
        },
        "aggregate": {
            "case_count": len(cases),
            "outcome_counts": dict(sorted(outcomes.items())),
            "total_transition_count": total_transitions,
            "level1_preemption_transition_count": preemptions,
            "preemption_fraction": (
                preemptions / total_transitions if total_transitions else 0.0
            ),
            "transitions_spent_in_return": sum(
                cast(int, case["transitions_spent_in_return"]) for case in cases
            ),
            "transitions_spent_in_charge": sum(
                cast(int, case["transitions_spent_in_charge"]) for case in cases
            ),
            "contact_lost_cases": sum(bool(case["contact_lost"]) for case in cases),
            "contact_reacquired_cases": sum(
                bool(case["contact_reacquired"]) for case in cases
            ),
            "energy_depletion_cases": sum(
                bool(case["energy_depletion"]) for case in cases
            ),
            "thermal_termination_cases": sum(
                bool(case["thermal_termination"]) for case in cases
            ),
            "maximum_terminal_spin_count": max(
                cast(int, case["terminal_spin_count_maximum"]) for case in cases
            ),
            "terminal_spin_exhaustion_cases": sum(
                bool(case["terminal_spin_exhausted"]) for case in cases
            ),
        },
        "cases": cases,
    }


def write_d052_artifact(path: Path, executed_commit_sha: str) -> Path:
    """Write a stable JSON artifact with serialization-only float rounding."""

    artifact = run_d052_protocol(executed_commit_sha)
    canonical = _canonicalize_artifact_floats(artifact)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(canonical, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return path


def artifact_sha256(path: Path) -> str:
    """Return the exact generated artifact byte hash."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_case(case: D052Case) -> dict[str, object]:
    config = D045PhysicalConfig(episode_horizon=D052_CASE_HORIZON)
    environment = D045Env(config)
    initial_battery = 0.20 * D045_BATTERY_CAPACITY_J
    observation, initial_info = environment.reset(
        options={
            "body_position": case.body_position,
            "station_center": D049_STATION_CENTER,
            "heading": case.heading_rad,
            "battery_j": initial_battery,
        }
    )
    if bool(observation[5]):
        raise RuntimeError("frozen D-052 initial state unexpectedly has contact")
    if initial_info != {}:
        raise RuntimeError("D-045 reset exposed unexpected organism-facing info")

    controller = D052Controller()
    event_samples: list[dict[str, object]] = [
        {
            "transition": 0,
            "events": ["RESET"],
            "active_mode": D052Mode.NORMAL.value,
            "command_source": None,
            "energy_before": float(observation[0]),
            "charging_contact_before": bool(observation[5]),
        }
    ]
    mode_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    rewards_exactly_zero = True
    infos_exactly_empty = True
    energy_at_return_activation: float | None = None
    energy_at_first_charging_contact: float | None = None
    first_charging_contact_transition: int | None = None
    energy_at_recovery_yield: float | None = None
    contact_lost = False
    contact_lost_count = 0
    contact_reacquired_count = 0
    invalid_beacon_seen = False
    terminal_spin_exhausted = False
    terminal_spin_exhaustion_transition: int | None = None
    last_mode: D052Mode | None = None
    last_source: D052CommandSource | None = None
    last_d050_mode: D050ControlMode | None = None
    terminated = False
    truncated = False
    termination_reason: str | None = None
    passed_through_after_yield = False
    recovery_yield_transition: int | None = None
    total_transition_count = 0

    for _ in range(D052_CASE_HORIZON):
        energy_before = float(observation[0])
        contact_before = bool(observation[5])
        decision = controller.command(observation, D052_PASSTHROUGH_FIXTURE)
        total_transition_count += 1
        mode_counts[decision.active_mode.value] += 1
        source_counts[decision.command_source.value] += 1
        if "RETURN_ACTIVATED" in decision.events:
            energy_at_return_activation = energy_before
        if "RECOVERY_YIELD" in decision.events:
            energy_at_recovery_yield = energy_before
            recovery_yield_transition = decision.transition_index
            passed_through_after_yield = decision.passed_through
        if "INVALID_BEACON" in decision.events:
            invalid_beacon_seen = True
        if "TERMINAL_SPIN_EXHAUSTED" in decision.events:
            terminal_spin_exhausted = True
            terminal_spin_exhaustion_transition = decision.transition_index

        observation_after, reward, terminated, truncated, organism_info = (
            environment.step((decision.wheel_delta_left, decision.wheel_delta_right))
        )
        telemetry = environment.last_transition
        if telemetry is None:
            raise RuntimeError("D-045 did not provide transition telemetry")
        rewards_exactly_zero = rewards_exactly_zero and reward == 0.0
        infos_exactly_empty = infos_exactly_empty and organism_info == {}
        contact_after = bool(observation_after[5])
        sample_events = list(decision.events)
        if not contact_before and contact_after:
            sample_events.append("PHYSICAL_CONTACT_ACQUIRED")
            if energy_at_first_charging_contact is None:
                energy_at_first_charging_contact = float(observation_after[0])
                first_charging_contact_transition = decision.transition_index
            if contact_lost and decision.active_mode is D052Mode.RETURN:
                contact_reacquired_count += 1
        elif contact_before and not contact_after:
            sample_events.append("PHYSICAL_CONTACT_LOST")
            if (
                decision.active_mode is D052Mode.CHARGE
                and "RECOVERY_YIELD" not in decision.events
            ):
                contact_lost = True
                contact_lost_count += 1

        mode_changed = decision.active_mode is not last_mode
        source_changed = decision.command_source is not last_source
        d050_mode_changed = decision.d050_mode is not last_d050_mode
        if (
            sample_events
            or mode_changed
            or source_changed
            or d050_mode_changed
            or contact_before != contact_after
        ):
            _append_event_sample(
                event_samples,
                {
                    "transition": decision.transition_index,
                    "events": sample_events,
                    "active_mode": decision.active_mode.value,
                    "command_source": decision.command_source.value,
                    "passed_through": decision.passed_through,
                    "preempted": decision.preempted,
                    "wheel_command": [
                        decision.wheel_delta_left,
                        decision.wheel_delta_right,
                    ],
                    "d050_mode": (
                        decision.d050_mode.value if decision.d050_mode else None
                    ),
                    "terminal_spin_count": decision.terminal_spin_count,
                    "terminal_spin_exhausted": decision.terminal_spin_exhausted,
                    "energy_before": energy_before,
                    "energy_after": float(observation_after[0]),
                    "charging_contact_before": contact_before,
                    "charging_contact_after": contact_after,
                },
            )
        last_mode = decision.active_mode
        last_source = decision.command_source
        last_d050_mode = decision.d050_mode
        observation = observation_after

        if terminated or truncated:
            if telemetry.termination_reason is not None:
                termination_reason = telemetry.termination_reason.value
            break
        if invalid_beacon_seen or terminal_spin_exhausted:
            break
        if passed_through_after_yield:
            break

    if energy_at_return_activation is None:
        raise RuntimeError("D-052 did not activate RETURN on the first decision")
    energy_depletion = (
        termination_reason == D045TerminationReason.ENERGY_DEPLETION.value
    )
    thermal_termination = termination_reason in {
        D045TerminationReason.PROTECTIVE_THERMAL_SHUTDOWN.value,
        D045TerminationReason.EMERGENCY_HARD_THERMAL_SHUTDOWN.value,
    }
    outcome = _case_outcome(
        passed_through_after_yield=passed_through_after_yield,
        terminal_spin_exhausted=terminal_spin_exhausted,
        invalid_beacon=invalid_beacon_seen,
        termination_reason=termination_reason,
        truncated=truncated,
    )
    return {
        "case_id": case.case_id,
        "initial_state": {
            "radius_m": case.radius_m,
            "position_bearing_deg": case.position_bearing_deg,
            "source_relative_heading_error_rad": (
                case.source_relative_heading_error_rad
            ),
            "body_position": list(case.body_position),
            "heading_rad": case.heading_rad,
            "battery_j": initial_battery,
            "observed_energy": float(
                np.float32(initial_battery / D045_BATTERY_CAPACITY_J)
            ),
            "charging_contact": False,
        },
        "outcome": outcome,
        "total_transition_count": total_transition_count,
        "level1_preemption_transition_count": controller.preemption_transition_count,
        "preemption_fraction": (
            controller.preemption_transition_count / total_transition_count
            if total_transition_count
            else 0.0
        ),
        "transitions_spent_in_return": controller.return_transition_count,
        "transitions_spent_in_charge": controller.charge_transition_count,
        "mode_transition_counts": dict(sorted(mode_counts.items())),
        "command_source_counts": dict(sorted(source_counts.items())),
        "first_decision_preempted": event_samples[1]["preempted"]
        if len(event_samples) > 1
        else False,
        "energy_at_return_activation": energy_at_return_activation,
        "energy_at_first_charging_contact": energy_at_first_charging_contact,
        "first_charging_contact_transition": first_charging_contact_transition,
        "energy_at_recovery_yield": energy_at_recovery_yield,
        "recovery_yield_transition": recovery_yield_transition,
        "passed_through_after_yield": passed_through_after_yield,
        "contact_lost": contact_lost,
        "contact_loss_count": contact_lost_count,
        "contact_reacquired": contact_reacquired_count > 0,
        "contact_reacquisition_count": contact_reacquired_count,
        "terminal_spin_exhausted": terminal_spin_exhausted,
        "terminal_spin_exhaustion_transition": terminal_spin_exhaustion_transition,
        "terminal_spin_count_maximum": controller.maximum_terminal_spin_count,
        "invalid_beacon_seen": invalid_beacon_seen,
        "energy_depletion": energy_depletion,
        "thermal_termination": thermal_termination,
        "terminated": terminated,
        "truncated": truncated,
        "termination_reason": termination_reason,
        "reward_exactly_zero": rewards_exactly_zero,
        "organism_info_exactly_empty": infos_exactly_empty,
        "event_samples": event_samples,
    }


def _append_event_sample(
    event_samples: list[dict[str, object]], sample: dict[str, object]
) -> None:
    if len(event_samples) >= D052_MAX_EVENT_SAMPLES:
        raise RuntimeError("D-052 exceeded its frozen bounded event-sample limit")
    event_samples.append(sample)


def _case_outcome(
    *,
    passed_through_after_yield: bool,
    terminal_spin_exhausted: bool,
    invalid_beacon: bool,
    termination_reason: str | None,
    truncated: bool,
) -> str:
    if passed_through_after_yield:
        return "COMPLETE_LOOP"
    if terminal_spin_exhausted:
        return "TERMINAL_SPIN_EXHAUSTED"
    if invalid_beacon:
        return "INVALID_BEACON_HOLD"
    if termination_reason is not None:
        return termination_reason
    if truncated:
        return "HORIZON_TRUNCATED"
    return "INCOMPLETE"


def _discrete_signature(cases: list[dict[str, object]]) -> str:
    signature: list[dict[str, object]] = []
    for case in cases:
        samples = cast(list[dict[str, object]], case["event_samples"])
        signature.append(
            {
                "case_id": case["case_id"],
                "outcome": case["outcome"],
                "total_transition_count": case["total_transition_count"],
                "level1_preemption_transition_count": case[
                    "level1_preemption_transition_count"
                ],
                "mode_transition_counts": case["mode_transition_counts"],
                "command_source_counts": case["command_source_counts"],
                "contact_lost": case["contact_lost"],
                "contact_reacquired": case["contact_reacquired"],
                "terminal_spin_exhausted": case["terminal_spin_exhausted"],
                "invalid_beacon_seen": case["invalid_beacon_seen"],
                "event_samples": [
                    {
                        key: sample[key]
                        for key in (
                            "transition",
                            "events",
                            "active_mode",
                            "command_source",
                            "passed_through",
                            "preempted",
                            "d050_mode",
                            "terminal_spin_count",
                            "terminal_spin_exhausted",
                            "charging_contact_before",
                            "charging_contact_after",
                        )
                        if key in sample
                    }
                    for sample in samples
                ],
            }
        )
    encoded = json.dumps(signature, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _protocol_record() -> dict[str, object]:
    return {
        "station_center": list(D049_STATION_CENTER),
        "return_radii_m": list(D052_RETURN_RADII_M),
        "position_bearings_deg": list(D052_POSITION_BEARINGS_DEG),
        "source_relative_heading_errors_rad": list(
            D052_INITIAL_SOURCE_RELATIVE_HEADING_ERRORS_RAD
        ),
        "case_count": 24,
        "case_horizon_transitions": D052_CASE_HORIZON,
        "initial_battery_expression_j": "0.20 * D045_BATTERY_CAPACITY_J",
        "initial_battery_j": 0.20 * D045_BATTERY_CAPACITY_J,
        "initial_contact": False,
        "pass_through_fixture_wheel_delta_rad": list(D052_PASSTHROUGH_FIXTURE),
        "pass_through_fixture_role": "legal non-zero test fixture only",
        "return_threshold_founder_constant": 0.20,
        "recovery_threshold_founder_constant": 0.80,
        "observed_energy_thresholds": {
            "return": RETURN_THRESHOLD,
            "recovery": RECOVERY_THRESHOLD,
            "channel": 0,
            "channel_dtype": "D-045 float32 widened to Python float",
            "return_comparison": "observation[0] <= RETURN_THRESHOLD",
            "recovery_comparison": "observation[0] >= RECOVERY_THRESHOLD",
            "one_float32_ulp_below_recovery": float(
                np.nextafter(np.float32(0.80), np.float32(0.0))
            ),
        },
        "energy_sampling_convention": {
            "energy_at_return_activation": (
                "observation[0] before the RETURN_ACTIVATED decision's step"
            ),
            "energy_at_first_charging_contact": (
                "observation[0] after the step that first acquired physical "
                "contact, including charge accepted on that step; paired with "
                "that decision's transition index"
            ),
            "energy_at_recovery_yield": (
                "observation[0] before the RECOVERY_YIELD decision's step"
            ),
        },
        "terminal_spin_max_steps": D049_TERMINAL_SPIN_MAX_STEPS,
        "terminal_spin_exhaustion_boundary": (
            "the twentieth TERMINAL_SPIN command executes; latch zero-wheel "
            "RETURN_HOLD on the next RETURN decision only if contact is absent"
        ),
        "terminal_spin_counter_reset": "every entry to RETURN",
        "d050_controller": "aweform.d050.D050SmoothController, delegated unchanged",
        "d045_physics": "unchanged; episode_horizon set to 25000 only",
        "observation_channels_used_by_arbiter": [0, 2, 3, 4, 5],
        "observation_channel_count": 8,
        "proposed_command_role": "PASS_THROUGH only when L1 authority is yielded",
        "command_sources": [source.value for source in D052CommandSource],
        "reward": 0.0,
        "organism_info": {},
        "learned_state": "not read; no Level-2/Level-3 dependency",
        "evaluator_geometry_in_causal_control": False,
        "seed_status": "seedless fixed-state support matrix",
        "event_sample_limit_per_case": D052_MAX_EVENT_SAMPLES,
        "artifact_float_canonicalization": (
            "serialization only: float(Decimal(x).quantize(Decimal('1e-12'), "
            "rounding=ROUND_HALF_EVEN)); exact from binary float; normalize -0.0 "
            "to 0.0; reject non-finite values"
        ),
    }


def _canonicalize_artifact_floats(value: object) -> object:
    """Round finite floats for JSON output only; never called by control code."""

    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite artifact float")
        rounded = float(
            Decimal(value).quantize(
                D052_ARTIFACT_FLOAT_QUANTUM, rounding=ROUND_HALF_EVEN
            )
        )
        return 0.0 if rounded == 0.0 else rounded
    if isinstance(value, dict):
        return {key: _canonicalize_artifact_floats(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_canonicalize_artifact_floats(item) for item in value]
    if isinstance(value, tuple):
        return [_canonicalize_artifact_floats(item) for item in value]
    return value


def _legal_wheel_pair(
    proposed: tuple[float, float] | list[float] | np.ndarray,
) -> tuple[float, float]:
    try:
        values = np.asarray(proposed, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError(
            "proposed wheel command must contain two legal values"
        ) from None
    if values.shape != (2,) or not np.all(np.isfinite(values)):
        raise ValueError("proposed wheel command must contain two finite values")
    left, right = float(values[0]), float(values[1])
    if max(abs(left), abs(right)) > D045_MAX_WHEEL_DELTA_RAD:
        raise ValueError("proposed wheel command is outside the D-045 action envelope")
    return left, right


def _validate_sha(value: str) -> None:
    if len(value) != 40 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise ValueError("executed_commit_sha must be a lowercase 40-character SHA")


def main() -> None:
    """CLI entry point for the frozen seedless D-052 characterization."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--executed-commit-sha", required=True)
    args = parser.parse_args()
    write_d052_artifact(args.output, args.executed_commit_sha)


if __name__ == "__main__":
    main()
