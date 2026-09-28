"""D-055 Development-only RETURN stall-turn candidate and paired harness."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Sequence, cast

import numpy as np

from . import d053, d054
from .d045 import (
    D045_AMBIENT_TEMPERATURE_C,
    D045_BATTERY_CAPACITY_J,
    D045_DT_SECONDS,
    D045_ENCODER_QUANTUM_RAD,
    D045Env,
    D045PhysicalConfig,
)
from .d049 import D049_STATION_CENTER
from .d050 import D050ControlMode
from .d052 import D052CommandSource, D052Controller, D052Decision, D052Mode
from .d053 import (
    D053_HORIZON,
    D053Lifetime,
    D053RoamingFixture,
    _bounded_samples,
    _trace_reset,
)
from .exp003_seed_policy import validate_exp003_development_seeds

D055_ID: Final = "D-055"
D055_HORIZON: Final = 140_000
D055_SUPPORT_SEEDS: Final = (22053, 22054, 22055, 22056, 22057)
D055_FRESH_SEEDS: Final = tuple(range(22550, 22570))
D055_TEST_SEED: Final = 22570
STALL_COMMAND_FLOOR: Final = D045_ENCODER_QUANTUM_RAD
D055_INVALIDATED_PRIOR_RUNS: Final = (
    {
        "executed_commit_sha": "1a5bc2aecf708288ae55aa3da4529baaa96a4385",
        "artifact_sha256": (
            "12059a2b9d2e61b25dae0ec708b8c8626a688863c5b01975137bf5c002b23b17"
        ),
        "artifact_size_bytes": 1_722_930,
        "invalidation_reason": (
            "The frozen runner reversed the U_ONLY_FAIL/C_ONLY_FAIL labels "
            "relative to issue 191; this run is not pooled into interpretation."
        ),
        "rerun_relationship": (
            "The complete official protocol is rerun from the corrected "
            "result-free freeze; the invalidated output is preserved separately."
        ),
    },
)


class D055CommandSource:
    """Candidate-only command-source label."""

    value = "STALL_TURN"


@dataclass(frozen=True, slots=True)
class D055Decision:
    """D-052-compatible emitted decision with candidate attribution."""

    decision: D052Decision
    command_source: D052CommandSource | D055CommandSource
    wheels: tuple[float, float]
    stall_detected: bool
    stall_turned: bool

    def __getattr__(self, name: str) -> Any:
        return getattr(self.decision, name)

    @property
    def wheel_delta_left(self) -> float:
        return self.wheels[0]

    @property
    def wheel_delta_right(self) -> float:
        return self.wheels[1]


class D055StallTurnCandidate:
    """One-decision organism-efference stall detector; observation only."""

    def __init__(self, controller: D052Controller | None = None) -> None:
        self.controller = controller or D052Controller()
        self.prior_return_command: tuple[float, float] | None = None
        self.stall_detected_count = 0
        self.stall_turn_count = 0
        self.stall_detected_non_pursuit_count = 0
        self.first_stall_turn_transition: int | None = None

    @property
    def mode(self) -> D052Mode:
        return self.controller.mode

    @property
    def preemption_transition_count(self) -> int:
        return self.controller.preemption_transition_count

    @property
    def terminal_spin_count(self) -> int:
        return self.controller.terminal_spin_count

    def command(
        self,
        observation: np.ndarray,
        proposal: tuple[float, float] | list[float] | np.ndarray,
    ) -> D055Decision:
        decision = self.controller.command(observation, proposal)
        prior = self.prior_return_command
        detected = (
            prior is not None
            and max(abs(prior[0]), abs(prior[1])) >= STALL_COMMAND_FLOOR
            and float(observation[6]) == 0.0
            and float(observation[7]) == 0.0
        )
        wheels = (decision.wheel_delta_left, decision.wheel_delta_right)
        turned = bool(
            detected
            and decision.active_mode is D052Mode.RETURN
            and decision.command_source is D052CommandSource.D050_SMOOTH
            and decision.d050_mode is D050ControlMode.CURVED_PURSUIT
        )
        if detected:
            self.stall_detected_count += 1
        if turned:
            u = (decision.wheel_delta_right - decision.wheel_delta_left) / 2.0
            wheels = (-u, u)
            self.stall_turn_count += 1
            if self.first_stall_turn_transition is None:
                self.first_stall_turn_transition = decision.transition_index
        elif detected:
            self.stall_detected_non_pursuit_count += 1
        self.prior_return_command = (
            wheels if decision.active_mode is D052Mode.RETURN else None
        )
        source_label = D055CommandSource() if turned else decision.command_source
        return D055Decision(decision, source_label, wheels, bool(detected), turned)


def _reset_case(
    position: tuple[float, float], heading: float, horizon: int
) -> tuple[D045Env, np.ndarray]:
    env = D045Env(D045PhysicalConfig(episode_horizon=horizon))
    obs, info = env.reset(
        options={
            "body_position": position,
            "station_center": D049_STATION_CENTER,
            "heading": heading,
            "battery_j": 0.20 * D045_BATTERY_CAPACITY_J,
            "body_temperature_c": D045_AMBIENT_TEMPERATURE_C,
            "charger_termination_latched": False,
        }
    )
    if info != {} or env.body is None:
        raise RuntimeError("D-045 reset contract changed")
    env.body.heading = heading
    return env, env._observation().as_array()


def first_return_pair_class(u_docked: bool | None, c_docked: bool | None) -> str:
    """Classify whether the first paired RETURN episode reached contact."""
    if u_docked is None or c_docked is None:
        return "NO_RETURN"
    if u_docked and c_docked:
        return "BOTH_DOCK"
    if not u_docked and c_docked:
        return "U_ONLY_FAIL"
    if u_docked and not c_docked:
        return "C_ONLY_FAIL"
    return "BOTH_FAIL"


def _prefix_identical(
    baseline: Sequence[object], candidate: Sequence[object], stop_before: int | None
) -> bool:
    """Compare traces through the decision immediately before intervention."""
    limit = min(len(baseline), len(candidate))
    if stop_before is not None:
        limit = min(limit, max(0, stop_before - 1))
    if len(baseline) < limit or len(candidate) < limit:
        return False
    return list(baseline[:limit]) == list(candidate[:limit])


def run_matrix_case(
    case: d054.D054Case,
    candidate: bool,
    horizon: int = 1000,
    trace_out: list[tuple[object, ...]] | None = None,
) -> dict[str, object]:
    env, obs = _reset_case(case.position, case.heading, horizon)
    base = D052Controller()
    wrapped = D055StallTurnCandidate(base) if candidate else None
    transitions = boundary_count = 0
    first_boundary: int | None = None
    minimum_scale = 1.0
    path = energy = 0.0
    scales_by_transition: dict[int, float] = {}
    centres: list[tuple[float, float]] = []
    outcome = "HORIZON_CENSORED"
    detected_scales: list[float] = []
    missed = 0
    previous_command: tuple[float, float] | None = None
    previous_scale: float | None = None
    while transitions < horizon:
        emitted = wrapped.command(obs, (0.0, 0.0)) if wrapped else None
        decision = emitted.decision if emitted else base.command(obs, (0.0, 0.0))
        if transitions == 0 and "RETURN_ACTIVATED" not in decision.events:
            raise RuntimeError("RETURN activation control failed")
        if (
            transitions > 0
            and decision.active_mode is not D052Mode.RETURN
            and "CHARGING_CONTACT" not in decision.events
        ):
            raise RuntimeError("unexpected non-RETURN decision in Part A")
        wheels = (
            emitted.wheels
            if emitted
            else (decision.wheel_delta_left, decision.wheel_delta_right)
        )
        if (
            transitions > 0
            and decision.active_mode is D052Mode.RETURN
            and previous_command is not None
            and max(abs(x) for x in previous_command) >= STALL_COMMAND_FLOOR
            and previous_scale is not None
            and previous_scale <= 1e-9
            and (emitted is None or not emitted.stall_detected)
        ):
            missed += 1
        if decision.command_source is D052CommandSource.RETURN_HOLD:
            outcome = "TERMINAL_SPIN_EXHAUSTED"
            transitions += 1
            break
        if decision.command_source is D052CommandSource.CHARGE_HOLD:
            outcome = "DOCKED"
            break
        before_pose = (
            (env.body.x, env.body.y, env.body.heading)
            if env.body is not None
            else (0.0, 0.0, 0.0)
        )
        obs_after, reward, terminated, truncated, info = env.step(wheels)
        telemetry = env.last_transition
        if telemetry is None or reward != 0.0 or info != {}:
            raise RuntimeError("D-045 transition contract changed")
        transitions += 1
        if trace_out is not None:
            trace_out.append(
                (
                    *wheels,
                    *before_pose,
                    *telemetry.position_after,
                    telemetry.heading_after,
                )
            )
        scales_by_transition[transitions] = telemetry.boundary_scale
        centres.append(telemetry.position_after)
        path += math.dist(telemetry.position_before, telemetry.position_after)
        energy += telemetry.actuator_electrical_power_w * D045_DT_SECONDS
        minimum_scale = min(minimum_scale, telemetry.boundary_scale)
        if telemetry.boundary_scale < 1.0:
            boundary_count += 1
            if first_boundary is None:
                first_boundary = transitions
        if emitted and emitted.stall_detected and transitions > 1:
            detected_scales.append(scales_by_transition[transitions - 1])
        previous_command = wheels if decision.active_mode is D052Mode.RETURN else None
        previous_scale = telemetry.boundary_scale
        obs = obs_after
        if obs[5] == 1.0:
            outcome = "DOCKED"
        elif decision.d050_mode is D050ControlMode.INVALID_BEACON:
            outcome = "INVALID_BEACON"
        elif terminated:
            outcome = "TERMINATED_" + (
                telemetry.termination_reason.value
                if telemetry.termination_reason
                else "UNKNOWN"
            )
        elif truncated:
            outcome = "HORIZON_CENSORED"
        if outcome != "HORIZON_CENSORED":
            break
    position = env.body.position if env.body else case.position
    heading = env.body.heading if env.body else case.heading
    pinned = (
        min(position[0], position[1], 1 - position[0], 1 - position[1])
        <= d054.D054_BOUNDARY_TOLERANCE_M
    )
    tail = centres[-101:]
    tail_path = sum(math.dist(a, b) for a, b in zip(tail, tail[1:]))
    record: dict[str, object] = {
        "case_id": case.case_id,
        "inset_m": case.inset,
        "boundary_class": case.boundary_class,
        "outcome": outcome,
        "outcome_transition": transitions,
        "first_boundary_scaled_transition": first_boundary,
        "boundary_scaled_transition_count": boundary_count,
        "minimum_boundary_scale": minimum_scale,
        "path_length_m": path,
        "actuator_energy_j": energy,
        "final_position": list(position),
        "final_heading": heading,
        "wall_pinned_at_end": pinned,
        "final_100_centre_path_m": tail_path,
        "WEDGED": outcome != "DOCKED" and pinned and tail_path <= 1e-9,
    }
    if wrapped:
        record.update(
            {
                "stall_detected_count": wrapped.stall_detected_count,
                "stall_turn_count": wrapped.stall_turn_count,
                "stall_detected_non_pursuit_count": (
                    wrapped.stall_detected_non_pursuit_count
                ),
                "first_stall_turn_transition": wrapped.first_stall_turn_transition,
                "detected_boundary_scales": detected_scales,
                "missed_stall_count": missed,
            }
        )
    env.close()
    return record


def run_d055_lifetime(
    seed: int, *, horizon: int = D053_HORIZON, initial_battery_fraction: float = 0.80
) -> D053Lifetime:
    """Run continuously to genuine D-045 termination or truncation.

    Non-default horizon/initial energy are explicitly test-only variants.
    """
    if seed < 0 or isinstance(seed, bool):
        raise ValueError("seed must be a non-negative integer")
    if horizon <= 0:
        raise ValueError("horizon must be positive")
    if not 0.0 <= initial_battery_fraction <= 1.0:
        raise ValueError("initial_battery_fraction must be in [0, 1]")
    config = D045PhysicalConfig(episode_horizon=horizon)
    env = D045Env(config)
    observation, reset_info = env.reset(
        options={
            "body_position": D049_STATION_CENTER,
            "station_center": D049_STATION_CENTER,
            "heading": 0.0,
            "battery_j": initial_battery_fraction * D045_BATTERY_CAPACITY_J,
            "body_temperature_c": config.ambient_temperature_c,
            "charger_termination_latched": False,
        }
    )
    if reset_info != {}:
        raise RuntimeError("D-045 reset info must be empty")
    controller = D055StallTurnCandidate()
    fixture = D053RoamingFixture(seed)
    modes: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    all_events: list[dict[str, object]] = []
    trace: list[dict[str, object]] = []
    cycles: list[dict[str, object]] = []
    current_cycle: dict[str, object] | None = None
    normal_roam_since_yield = 0
    incidental_acquisitions: list[dict[str, object]] = []
    incidental_contact_steps = 0
    # The initial physical contact is a starting condition, never an acquisition.
    initial_min_observation = float(observation[0])
    min_observation = initial_min_observation
    min_battery_j = env.battery_j
    boundary_scaled = 0
    invalid_beacon_count = 0
    exhausted_transitions: list[int] = []
    spin_max = 0
    return_starts: list[dict[str, object]] = []
    terminated = truncated = False
    termination_reason: str | None = None
    rewards_zero = True
    infos_empty = True
    previous_mode: D052Mode | None = None
    previous_source: D052CommandSource | D055CommandSource | None = None
    previous_d050_mode: D050ControlMode | None = None
    stall_detected_by_cycle: Counter[int] = Counter()

    trace.append(_trace_reset(env, observation))
    for _ in range(horizon):
        energy_before = float(observation[0])
        contact_before = bool(observation[5])
        proposal = (
            fixture.propose()
        )  # exactly once every decision, even while preempted
        decision = controller.command(observation, proposal.wheel_command)
        modes[decision.active_mode.value] += 1
        sources[decision.command_source.value] += 1
        spin_max = max(spin_max, decision.terminal_spin_count)
        if "INVALID_BEACON" in decision.events:
            invalid_beacon_count += 1
        if "TERMINAL_SPIN_EXHAUSTED" in decision.events:
            exhausted_transitions.append(decision.transition_index)
        if (
            current_cycle is None
            and decision.active_mode is D052Mode.NORMAL
            and "RECOVERY_YIELD" not in decision.events
        ):
            normal_roam_since_yield += 1
        if "RETURN_ACTIVATED" in decision.events:
            position = (
                env.body.position if env.body is not None else D049_STATION_CENTER
            )
            dx = D049_STATION_CENTER[0] - position[0]
            dy = D049_STATION_CENTER[1] - position[1]
            current_cycle = {
                "cycle_index": len(cycles) + 1,
                "start_transition": decision.transition_index,
                "normal_roam_length": normal_roam_since_yield,
                "return_length": 0,
                "charge_length": 0,
                "energy_at_return_activation": energy_before,
                "energy_after_first_charging_contact": None,
                "energy_at_recovery_yield": None,
                "maximum_terminal_spin_count": 0,
                "outcome": None,
            }
            normal_roam_since_yield = 0
            return_starts.append(
                {
                    "transition": decision.transition_index,
                    "station_distance_m": math.hypot(dx, dy),
                    "station_bearing_rad": math.atan2(dy, dx),
                }
            )
            cycles.append(current_cycle)
        if current_cycle is not None:
            if decision.active_mode is D052Mode.RETURN:
                current_cycle["return_length"] = (
                    cast(int, current_cycle["return_length"]) + 1
                )
            elif decision.active_mode is D052Mode.CHARGE:
                current_cycle["charge_length"] = (
                    cast(int, current_cycle["charge_length"]) + 1
                )
            elif "RECOVERY_YIELD" not in decision.events:
                current_cycle["normal_roam_length"] = (
                    cast(int, current_cycle["normal_roam_length"]) + 1
                )
            current_cycle["maximum_terminal_spin_count"] = max(
                cast(int, current_cycle["maximum_terminal_spin_count"]),
                decision.terminal_spin_count,
            )
            if "RECOVERY_YIELD" in decision.events:
                current_cycle["energy_at_recovery_yield"] = energy_before
                current_cycle["end_transition"] = decision.transition_index
                current_cycle["outcome"] = "YIELDED"
                current_cycle = None
                normal_roam_since_yield = 0

        observation_after, reward, terminated, truncated, info = env.step(
            (decision.wheel_delta_left, decision.wheel_delta_right)
        )
        telemetry = env.last_transition
        if telemetry is None:
            raise RuntimeError("missing D-045 transition telemetry")
        rewards_zero = rewards_zero and reward == 0.0
        infos_empty = infos_empty and info == {}
        min_observation = min(min_observation, float(observation_after[0]))
        min_battery_j = min(min_battery_j, telemetry.battery_after_j)
        boundary_scaled += int(telemetry.boundary_scale < 1.0)
        contact_after = bool(observation_after[5])
        events = list(decision.events)
        if not contact_before and contact_after:
            events.append("PHYSICAL_CONTACT_ACQUIRED")
            if (
                decision.active_mode is D052Mode.RETURN
                and current_cycle is not None
                and current_cycle["energy_after_first_charging_contact"] is None
            ):
                current_cycle["energy_after_first_charging_contact"] = float(
                    observation_after[0]
                )
                current_cycle["first_charging_contact_transition"] = (
                    decision.transition_index
                )
            elif (
                decision.command_source is D052CommandSource.PASS_THROUGH
                and decision.active_mode is D052Mode.NORMAL
            ):
                incidental_acquisitions.append(
                    {
                        "transition": decision.transition_index,
                        "energy": float(observation_after[0]),
                    }
                )
        elif contact_before and not contact_after:
            events.append("PHYSICAL_CONTACT_LOST")
        if decision.active_mode is D052Mode.NORMAL and contact_after:
            incidental_contact_steps += 1
        if telemetry.terminated or telemetry.truncated:
            events.append("TERMINATED" if telemetry.terminated else "TRUNCATED")
            termination_reason = (
                telemetry.termination_reason.value
                if telemetry.termination_reason
                else None
            )
            if current_cycle is not None:
                current_cycle["end_transition"] = decision.transition_index
                current_cycle["outcome"] = (
                    f"TERMINATED_{termination_reason}"
                    if terminated
                    else f"TRUNCATED_IN_{decision.active_mode.value}"
                )
        sample = {
            "transition": decision.transition_index,
            "events": events,
            "active_mode": decision.active_mode.value,
            "command_source": decision.command_source.value,
            "passed_through": decision.passed_through,
            "preempted": decision.preempted,
            "wheel_command": [decision.wheel_delta_left, decision.wheel_delta_right],
            "proposed_wheel_command": list(proposal.wheel_command),
            "symbolic_proposal": proposal.symbolic_action.name,
            "d050_mode": decision.d050_mode.value if decision.d050_mode else None,
            "terminal_spin_count": decision.terminal_spin_count,
            "terminal_spin_exhausted": decision.terminal_spin_exhausted,
            "energy_before": energy_before,
            "energy_after": float(observation_after[0]),
            "battery_before_j": telemetry.battery_before_j,
            "battery_after_j": telemetry.battery_after_j,
            "charging_contact_before": contact_before,
            "charging_contact_after": contact_after,
            "x": telemetry.position_after[0],
            "y": telemetry.position_after[1],
            "heading": telemetry.heading_after,
            "thermal": float(observation_after[1]),
            "boundary_scale": telemetry.boundary_scale,
            "simulated_seconds": decision.transition_index * D045_DT_SECONDS,
            "cycle_index": len(cycles)
            if current_cycle is None
            else cast(int, current_cycle["cycle_index"]),
            "terminated": terminated,
            "truncated": truncated,
        }
        trace.append(sample)
        if decision.stall_detected:
            stall_detected_by_cycle[cast(int, sample["cycle_index"])] += 1
        if (
            events
            or decision.active_mode is not previous_mode
            or decision.command_source is not previous_source
            or decision.d050_mode is not previous_d050_mode
            or contact_before != contact_after
        ):
            all_events.append(
                {
                    key: sample[key]
                    for key in (
                        "transition",
                        "events",
                        "active_mode",
                        "command_source",
                        "passed_through",
                        "preempted",
                        "wheel_command",
                        "proposed_wheel_command",
                        "symbolic_proposal",
                        "d050_mode",
                        "terminal_spin_count",
                        "terminal_spin_exhausted",
                        "energy_before",
                        "energy_after",
                        "charging_contact_before",
                        "charging_contact_after",
                    )
                }
            )
        previous_mode, previous_source = decision.active_mode, decision.command_source
        previous_d050_mode = decision.d050_mode
        observation = observation_after
        if terminated or truncated:
            break
    if current_cycle is not None and current_cycle["outcome"] is None:
        current_cycle["outcome"] = f"TRUNCATED_IN_{controller.mode.value}"
        current_cycle["end_transition"] = len(trace) - 1
    reset_sample: dict[str, object] = {
        "transition": 0,
        "events": ["RESET"],
        "active_mode": D052Mode.NORMAL.value,
        "command_source": None,
        "energy_before": trace[0]["energy"],
        "charging_contact_before": trace[0]["charging_contact"],
    }
    samples = _bounded_samples([reset_sample, *all_events])
    counts = {mode.value: modes[mode.value] for mode in D052Mode}
    source_counts = {
        source.value: sources[source.value] for source in D052CommandSource
    }
    total = sum(modes.values())
    summary: dict[str, object] = {
        "seed": seed,
        "total_transitions": total,
        "termination_reason": termination_reason,
        "terminated": terminated,
        "truncated": truncated,
        "final_mode": controller.mode.value,
        "final_cycle_index": len(cycles),
        "mode_transition_counts": counts,
        "command_source_counts": source_counts,
        "level1_preemption_count": controller.preemption_transition_count,
        "level1_preemption_fraction": controller.preemption_transition_count / total
        if total
        else 0.0,
        "pass_through_count": sources[D052CommandSource.PASS_THROUGH.value],
        "return_activated_count": sum(
            "RETURN_ACTIVATED" in cast(list[str], item["events"]) for item in all_events
        ),
        "return_dock_acquisition_count": sum(
            "CHARGING_CONTACT" in cast(list[str], item["events"]) for item in all_events
        ),
        "completed_recovery_yield_count": sum(
            "RECOVERY_YIELD" in cast(list[str], item["events"]) for item in all_events
        ),
        "contact_lost_count": sum(
            "CHARGING_CONTACT_LOST" in cast(list[str], item["events"])
            for item in all_events
        ),
        "contact_reacquired_count": sum(
            "CHARGING_CONTACT_REACQUIRED" in cast(list[str], item["events"])
            for item in all_events
        ),
        "invalid_beacon_decision_count": invalid_beacon_count,
        "terminal_spin_maximum": spin_max,
        "terminal_spin_exhaustion_count": len(exhausted_transitions),
        "terminal_spin_exhaustion_transitions": exhausted_transitions,
        "incidental_normal_contact_acquisition_count": len(incidental_acquisitions),
        "incidental_normal_contact_acquisitions": incidental_acquisitions,
        "normal_transitions_in_contact": incidental_contact_steps,
        "minimum_observed_energy": min_observation,
        "minimum_battery_j": min_battery_j,
        "boundary_scaled_transition_count": boundary_scaled,
        "return_start_pose_evaluator_only": return_starts,
        "cycles": cycles,
        "event_row_count": len(all_events) + 1,
        "retained_sample_count": len(samples),
        "samples_truncated": len(samples) < len(all_events) + 1,
        "event_samples": samples,
        "reward_exactly_zero": rewards_zero,
        "organism_info_exactly_empty": infos_empty,
    }
    if (
        sum(counts.values()) != total
        or controller.preemption_transition_count
        + sources[D052CommandSource.PASS_THROUGH.value]
        != total
    ):
        raise RuntimeError("D-053 lifetime counters are inconsistent")
    summary["stall_turn_count"] = controller.stall_turn_count
    summary["stall_detected_count"] = controller.stall_detected_count
    summary["first_stall_turn_transition"] = controller.first_stall_turn_transition
    summary["stall_counts_by_cycle"] = [
        {
            "cycle_index": cycle["cycle_index"],
            "stall_turn_count": sum(
                1
                for row in trace
                if row.get("command_source") == "STALL_TURN"
                and row.get("cycle_index") == cycle["cycle_index"]
            ),
            "stall_detected_count": stall_detected_by_cycle[
                cast(int, cycle["cycle_index"])
            ],
        }
        for cycle in cycles
    ]
    cast(dict[str, int], summary["command_source_counts"])["STALL_TURN"] = (
        controller.stall_turn_count
    )
    return D053Lifetime(seed, summary, tuple(trace))


def validate_fresh_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    checked = validate_exp003_development_seeds(seeds)
    if checked != D055_FRESH_SEEDS:
        raise ValueError("fresh seed block must equal 22550-22569")
    return checked


def run_d055_protocol(executed_commit_sha: str) -> dict[str, object]:
    """Execute frozen official D-055 matrix and lifetime comparison."""
    if len(executed_commit_sha) != 40 or any(
        c not in "0123456789abcdef" for c in executed_commit_sha
    ):
        raise ValueError("invalid commit SHA")
    repo = Path(__file__).resolve().parents[2]
    prior_a = json.loads(
        (repo / "development/D-054-v05-return-boundary-wedge-diagnosis.json").read_text(
            encoding="utf-8"
        )
    )["part_c"]["per_run"]
    prior_smooth = {row["case_id"]: row for row in prior_a if row["arm"] == "S"}
    cases = d054.frozen_cases()
    if len(cases) != 768:
        raise RuntimeError("D-054 support cardinality changed")
    arm_u: list[dict[str, object]] = []
    arm_c: list[dict[str, object]] = []
    for case in cases:
        u_trace: list[tuple[object, ...]] = []
        c_trace: list[tuple[object, ...]] = []
        u_record = run_matrix_case(case, False, trace_out=u_trace)
        c_record = run_matrix_case(case, True, trace_out=c_trace)
        turn_transition = cast(int | None, c_record["first_stall_turn_transition"])
        if not _prefix_identical(u_trace, c_trace, turn_transition):
            raise RuntimeError("Part A prefix identity failed")
        if turn_transition is None and u_trace != c_trace:
            raise RuntimeError("Part A no-intervention identity failed")
        arm_u.append(u_record)
        arm_c.append(c_record)
    fields = (
        "case_id",
        "inset_m",
        "boundary_class",
        "outcome_transition",
        "first_boundary_scaled_transition",
        "boundary_scaled_transition_count",
        "minimum_boundary_scale",
        "path_length_m",
        "actuator_energy_j",
        "final_position",
        "final_heading",
    )
    u_docked = {r["case_id"] for r in arm_u if r["outcome"] == "DOCKED"}
    d054_docked = {
        key for key, row in prior_smooth.items() if row["outcome"] == "DOCKED"
    }
    if u_docked != d054_docked or len(u_docked) != 640:
        raise RuntimeError("D-054 identity DOCKED set control failed")
    for row in arm_u:
        old = prior_smooth[row["case_id"]]
        if row["outcome"] == "DOCKED":
            if d053._canonicalize({k: row[k] for k in fields}) != d053._canonicalize(
                {k: old[k] for k in fields}
            ):
                raise RuntimeError("D-054 compact-record identity failed")
    paired: Counter[tuple[str, str]] = Counter()
    for u, c in zip(arm_u, arm_c):
        paired[(cast(str, u["outcome"]), cast(str, c["outcome"]))] += 1
        if c["stall_turn_count"] == 0 and d053._canonicalize(
            {k: c[k] for k in fields}
        ) != d053._canonicalize({k: u[k] for k in fields}):
            raise RuntimeError("no-intervention identity failed")
    rescued = sum(
        u["outcome"] != "DOCKED" and c["outcome"] == "DOCKED"
        for u, c in zip(arm_u, arm_c)
    )
    harmed = sum(
        u["outcome"] == "DOCKED" and c["outcome"] != "DOCKED"
        for u, c in zip(arm_u, arm_c)
    )
    support = validate_exp003_development_seeds(D055_SUPPORT_SEEDS)
    fresh = validate_fresh_seeds(D055_FRESH_SEEDS)
    prior_b = json.loads(
        (
            repo
            / "development/D-053-v05-continuous-lifetime-return-charge-recovery.json"
        ).read_text(encoding="utf-8")
    )
    old_summaries = {row["seed"]: row for row in prior_b["seeds"]}
    pairs: list[dict[str, object]] = []
    prefix_pass = True
    for seed in (*support, *fresh):
        u_lifetime = d053.run_d053_lifetime(seed)
        c_lifetime = run_d055_lifetime(seed)
        if seed in support and d053._canonicalize(
            u_lifetime.summary
        ) != d053._canonicalize(old_summaries[seed]):
            raise RuntimeError("D-053 identity control failed")
        first_turn = c_lifetime.summary["first_stall_turn_transition"]
        prefix_len = (
            len(u_lifetime.trace) if first_turn is None else cast(int, first_turn)
        )
        if u_lifetime.trace[:prefix_len] != c_lifetime.trace[:prefix_len]:
            prefix_pass = False
        if c_lifetime.summary["stall_turn_count"] == 0:
            extra = {
                "stall_turn_count",
                "stall_detected_count",
                "first_stall_turn_transition",
                "stall_counts_by_cycle",
            }
            reduced = {k: v for k, v in c_lifetime.summary.items() if k not in extra}
            reduced["command_source_counts"] = {
                k: v
                for k, v in cast(
                    dict[str, object], reduced["command_source_counts"]
                ).items()
                if k != "STALL_TURN"
            }
            if d053._canonicalize(reduced) != d053._canonicalize(u_lifetime.summary):
                raise RuntimeError("zero-turn lifetime identity failed")
        u_cycles = cast(list[dict[str, object]], u_lifetime.summary["cycles"])
        c_cycles = cast(list[dict[str, object]], c_lifetime.summary["cycles"])
        uc = next((cy for cy in u_cycles if cy["outcome"] is not None), None)
        cc = next((cy for cy in c_cycles if cy["outcome"] is not None), None)
        u_first_docked = (
            None
            if uc is None
            else uc["energy_after_first_charging_contact"] is not None
        )
        c_first_docked = (
            None
            if cc is None
            else cc["energy_after_first_charging_contact"] is not None
        )
        pair_class = first_return_pair_class(u_first_docked, c_first_docked)
        pairs.append(
            {
                "seed": seed,
                "arm_u": u_lifetime.summary,
                "arm_c": c_lifetime.summary,
                "paired_class": pair_class,
            }
        )
    if not prefix_pass:
        raise RuntimeError("prefix identity control failed")

    def class_counts(block: Sequence[dict[str, object]]) -> dict[str, int]:
        counts = Counter(cast(str, r["paired_class"]) for r in block)
        return {
            key: counts[key]
            for key in (
                "NO_RETURN",
                "BOTH_DOCK",
                "U_ONLY_FAIL",
                "C_ONLY_FAIL",
                "BOTH_FAIL",
            )
        }

    def outcome_counts(rows: Sequence[dict[str, object]]) -> dict[str, int]:
        counts = Counter(cast(str, r["outcome"]) for r in rows)
        return dict(sorted(counts.items()))

    scales = [
        x for r in arm_c for x in cast(list[float], r["detected_boundary_scales"])
    ]
    u_wedged = sum(bool(r["WEDGED"]) for r in arm_u)
    c_wedged = sum(bool(r["WEDGED"]) for r in arm_c)
    grouped_non_docked: dict[str, dict[str, int]] = {}
    paired_dock_deltas: list[int] = []
    for u, c in zip(arm_u, arm_c):
        group = f"inset={u['inset_m']:.2f}|{u['boundary_class']}"
        if u["outcome"] != "DOCKED" or c["outcome"] != "DOCKED":
            counts = grouped_non_docked.setdefault(
                group, {"U_not_docked": 0, "C_not_docked": 0}
            )
            counts["U_not_docked"] += int(u["outcome"] != "DOCKED")
            counts["C_not_docked"] += int(c["outcome"] != "DOCKED")
        if (
            u["outcome"] == "DOCKED"
            and c["outcome"] == "DOCKED"
            and cast(int, c["stall_turn_count"]) > 0
        ):
            paired_dock_deltas.append(
                cast(int, c["outcome_transition"]) - cast(int, u["outcome_transition"])
            )
    paired_dock_deltas.sort()

    def quantile(values: list[int], fraction: float) -> float | None:
        if not values:
            return None
        index = (len(values) - 1) * fraction
        low, high = math.floor(index), math.ceil(index)
        return values[low] + (values[high] - values[low]) * (index - low)

    part_a = {
        "per_run": [{"arm": "U", **r} for r in arm_u]
        + [{"arm": "C", **r} for r in arm_c],
        "aggregates": {
            "U_docked": sum(r["outcome"] == "DOCKED" for r in arm_u),
            "C_docked": sum(r["outcome"] == "DOCKED" for r in arm_c),
            "U_wedged": u_wedged,
            "C_wedged": c_wedged,
            "rescued": rescued,
            "harmed": harmed,
            "outcome_counts_by_arm": {
                "U": outcome_counts(arm_u),
                "C": outcome_counts(arm_c),
            },
            "paired_outcomes": {
                f"{u} x {c}": n for (u, c), n in sorted(paired.items())
            },
            "non_docked_by_inset_boundary_class": grouped_non_docked,
            "both_docked_intervened_transition_delta": {
                "count": len(paired_dock_deltas),
                "minimum": min(paired_dock_deltas) if paired_dock_deltas else None,
                "median": quantile(paired_dock_deltas, 0.5),
                "maximum": max(paired_dock_deltas) if paired_dock_deltas else None,
            },
            "stall_turn_count": sum(cast(int, r["stall_turn_count"]) for r in arm_c),
            "detector_audit": {
                "detected_count": len(scales),
                "maximum_boundary_scale": max(scales, default=None),
                "scale_zero_count": sum(x == 0.0 for x in scales),
                "scale_positive_to_1e-9_count": sum(0.0 < x <= 1e-9 for x in scales),
                "scale_above_1e-9_count": sum(x > 1e-9 for x in scales),
                "missed_stall_count": sum(
                    cast(int, r["missed_stall_count"]) for r in arm_c
                ),
            },
        },
        "controls": {"D054_identity": "PASS", "no_intervention_identity": "PASS"},
    }
    support_pairs = [r for r in pairs if r["seed"] in support]
    fresh_pairs = [r for r in pairs if r["seed"] in fresh]
    signature = {
        "A_WEDGE_RESOLUTION": "ALL"
        if rescued == 128
        else "PARTIAL"
        if rescued
        else "NONE",
        "A_HARM": "SOME" if harmed else "NONE",
        "B_SUPPORT": class_counts(support_pairs),
        "B_FRESH": class_counts(fresh_pairs),
    }
    return {
        "schema_version": "d055-artifact-v1",
        "development_id": D055_ID,
        "protocol_version": "d055-v05-return-proprioceptive-stall-turn-candidate-v1",
        "authorized_base_sha": "f16a676bd60e0f92cbfaee36b54c6145b0d85706",
        "execution_base_sha": "45e946fb295b594954542e5f31fd54b9d15ec107",
        "executed_commit_sha": executed_commit_sha,
        "invalidated_prior_runs": D055_INVALIDATED_PRIOR_RUNS,
        "result_kind": "development_causal_candidate_intervention",
        "claims_boundary": (
            "descriptive Development only; no promotion or confirmatory claim"
        ),
        "execution_status": "COMPLETED",
        "frozen_protocol": {
            "matrix_states": 768,
            "horizon": 1000,
            "stall_command_floor_rad": STALL_COMMAND_FLOOR,
            "seeds_support": list(support),
            "seeds_fresh": list(fresh),
            "lifetime_horizon": D055_HORIZON,
            "reward": 0.0,
            "organism_info": {},
        },
        "part_a": part_a,
        "part_b": {
            "pairs": pairs,
            "controls": {"D053_identity": "PASS", "prefix_identity": "PASS"},
            "class_counts_support": class_counts(support_pairs),
            "class_counts_fresh": class_counts(fresh_pairs),
        },
        "discrete_signature": signature,
    }


def write_artifact(path: Path, executed_commit_sha: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            d053._canonicalize(run_d055_protocol(executed_commit_sha)),
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--executed-commit-sha", required=True)
    args = parser.parse_args(argv)
    write_artifact(args.output, args.executed_commit_sha)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
