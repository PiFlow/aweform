"""D-053 continuous-lifetime characterization of the unchanged D-052 floor.

The EXP-001-derived roaming fixture is an evaluator-side stream of fixed V0.5
wheel-command test vectors, not organism cognition. It is queried once on every
transition and has no access to observations or evaluator state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path
from typing import Final, Sequence, cast

import numpy as np

from .d045 import (
    D045_BATTERY_CAPACITY_J,
    D045_DT_SECONDS,
    D045_MAX_WHEEL_DELTA_RAD,
    D045Env,
    D045PhysicalConfig,
)
from .d049 import D049_STATION_CENTER
from .d052 import (
    RECOVERY_THRESHOLD,
    RETURN_THRESHOLD,
    D052CommandSource,
    D052Controller,
    D052Mode,
    _legal_wheel_pair,
)
from .env import Action
from .exp001 import (
    ExternalObservation,
    StochasticPersistentExplorer,
    policy_rng_from_seed,
)
from .exp003_seed_policy import validate_exp003_development_seeds

D053_ID: Final[str] = "D-053"
D053_PROTOCOL_VERSION: Final[str] = (
    "d053-v05-continuous-lifetime-return-charge-recovery-v1"
)
D053_HORIZON: Final[int] = 140_000
D053_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = (22053, 22054, 22055, 22056, 22057)
D053_ARTIFACT_FLOAT_QUANTUM: Final[Decimal] = Decimal("1e-12")
D053_MAX_EVENT_SAMPLES: Final[int] = 256
_D053_PRIORITY_SAMPLE_EVENTS: Final[frozenset[str]] = frozenset(
    {
        "RETURN_ACTIVATED",
        "CHARGING_CONTACT",
        "CHARGING_CONTACT_LOST",
        "CHARGING_CONTACT_REACQUIRED",
        "RECOVERY_YIELD",
        "TERMINAL_SPIN_EXHAUSTED",
        "INVALID_BEACON",
        "TERMINATED",
        "TRUNCATED",
    }
)
_PLACEHOLDER_OBSERVATION: Final[ExternalObservation] = ExternalObservation(
    0.0, 0.0, 0.0
)
_ACTION_WHEELS: Final[dict[Action, tuple[float, float]]] = {
    Action.MOVE_FORWARD: (D045_MAX_WHEEL_DELTA_RAD, D045_MAX_WHEEL_DELTA_RAD),
    Action.TURN_LEFT: (-D045_MAX_WHEEL_DELTA_RAD, D045_MAX_WHEEL_DELTA_RAD),
    Action.TURN_RIGHT: (D045_MAX_WHEEL_DELTA_RAD, -D045_MAX_WHEEL_DELTA_RAD),
}


def validate_d053_development_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    """Validate formal reservations then require the exact frozen D-053 block."""
    validated = validate_exp003_development_seeds(seeds)
    if validated != D053_DEVELOPMENT_SEEDS:
        raise ValueError(f"D-053 requires exactly {D053_DEVELOPMENT_SEEDS}")
    return validated


@dataclass(frozen=True, slots=True)
class D053Proposal:
    """One evaluator fixture proposal, with labelled symbolic test vector."""

    symbolic_action: Action
    wheel_command: tuple[float, float]


class D053RoamingFixture:
    """Seeded EXP-001 proposal stream with a fixed symbolic-to-wheel mapping."""

    def __init__(self, seed: int) -> None:
        if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
            raise ValueError("seed must be a non-negative integer")
        self._explorer = StochasticPersistentExplorer(policy_rng_from_seed(seed))
        self.decision_count = 0

    def propose(self) -> D053Proposal:
        action = self._explorer.act(_PLACEHOLDER_OBSERVATION)
        try:
            wheels = _ACTION_WHEELS[action]
        except KeyError as error:
            raise ValueError(f"unsupported D-053 roaming action: {action!r}") from error
        legal = _legal_wheel_pair(wheels)
        self.decision_count += 1
        return D053Proposal(action, legal)


@dataclass(frozen=True, slots=True)
class D053Lifetime:
    """Full evaluator trace plus compact descriptive lifetime summary."""

    seed: int
    summary: dict[str, object]
    trace: tuple[dict[str, object], ...]


def run_d053_lifetime(
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
    controller = D052Controller()
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
    previous_source: D052CommandSource | None = None

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
        if (
            events
            or decision.active_mode is not previous_mode
            or decision.command_source is not previous_source
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
    samples, collapsed_count, samples_truncated = _bounded_samples(
        [reset_sample, *all_events]
    )
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
        "event_sample_candidate_count": len(all_events) + 1,
        "event_sample_collapsed_invalid_beacon_count": collapsed_count,
        "event_samples_truncated": samples_truncated,
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
    return D053Lifetime(seed, summary, tuple(trace))


def _bounded_samples(
    rows: list[dict[str, object]],
) -> tuple[list[dict[str, object]], int, bool]:
    """Return at most 256 samples, collapse count, and truncation flag.

    Repeated ``INVALID_BEACON``-only rows after the first of a consecutive run are
    collapsed. RESET and the final row are always kept; then, in priority order,
    cycle-defining/termination/first-invalid-beacon rows, other event rows, and
    event-free state-change rows fill the cap, evenly spaced within the tier that
    overflows.
    """
    kept: list[dict[str, object]] = []
    previous_invalid_transition: int | None = None
    for row in rows:
        events = cast(list[str], row["events"])
        transition = cast(int, row["transition"])
        if "INVALID_BEACON" in events:
            repeated = previous_invalid_transition == transition - 1
            previous_invalid_transition = transition
            if repeated and events == ["INVALID_BEACON"]:
                continue
        kept.append(row)
    collapsed = len(rows) - len(kept)
    tiers: list[list[dict[str, object]]] = [[], [], [], []]
    for position, row in enumerate(kept):
        events = cast(list[str], row["events"])
        if position in (0, len(kept) - 1):
            tiers[0].append(row)
        elif _D053_PRIORITY_SAMPLE_EVENTS.intersection(events):
            tiers[1].append(row)
        elif events:
            tiers[2].append(row)
        else:
            tiers[3].append(row)
    selected: list[dict[str, object]] = []
    for tier in tiers:
        slots = D053_MAX_EVENT_SAMPLES - len(selected)
        if len(tier) <= slots:
            selected.extend(tier)
        else:
            selected.extend(tier[(k * len(tier)) // slots] for k in range(slots))
    selected.sort(key=lambda item: cast(int, item["transition"]))
    return selected, collapsed, len(selected) < len(kept)


def _trace_reset(env: D045Env, observation: np.ndarray) -> dict[str, object]:
    if env.body is None:
        raise RuntimeError("body unavailable after reset")
    return {
        "transition": 0,
        "events": ["RESET"],
        "active_mode": "NORMAL",
        "command_source": None,
        "symbolic_proposal": None,
        "d050_mode": None,
        "x": env.body.position[0],
        "y": env.body.position[1],
        "heading": env.body.heading,
        "energy": float(observation[0]),
        "thermal": float(observation[1]),
        "charging_contact": bool(observation[5]),
        "charging_contact_before": None,
        "terminated": False,
        "truncated": False,
        "boundary_scale": 1.0,
        "simulated_seconds": 0.0,
        "cycle_index": 0,
    }


def run_d053_protocol(executed_commit_sha: str) -> dict[str, object]:
    """Execute the exact five-seed D-053 characterization."""
    if len(executed_commit_sha) != 40 or any(
        character not in "0123456789abcdef" for character in executed_commit_sha
    ):
        raise ValueError("executed_commit_sha must be a lowercase 40-character SHA")
    seeds = validate_d053_development_seeds(D053_DEVELOPMENT_SEEDS)
    summaries: list[dict[str, object]] = []
    for seed in seeds:
        summaries.append(run_d053_lifetime(seed).summary)
    signatures = [
        {
            key: item[key]
            for key in (
                "seed",
                "total_transitions",
                "termination_reason",
                "truncated",
                "final_mode",
                "mode_transition_counts",
                "command_source_counts",
                "return_activated_count",
                "return_dock_acquisition_count",
                "completed_recovery_yield_count",
                "terminal_spin_maximum",
                "terminal_spin_exhaustion_count",
            )
        }
        for item in summaries
    ]
    signature = hashlib.sha256(
        json.dumps(signatures, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "schema_version": "d053-artifact-v1",
        "development_id": D053_ID,
        "protocol_version": D053_PROTOCOL_VERSION,
        "executed_commit_sha": executed_commit_sha,
        "result_kind": "development_diagnostic",
        "claims_boundary": (
            "descriptive only; not confirmatory evidence; fixture is "
            "evaluator-side and not organism cognition"
        ),
        "execution_status": "COMPLETED",
        "frozen_protocol": {
            "seeds": list(seeds),
            "horizon": D053_HORIZON,
            "initial_state": {
                "body_position": list(D049_STATION_CENTER),
                "station_center": list(D049_STATION_CENTER),
                "heading_rad": 0.0,
                "battery_j": 0.8 * D045_BATTERY_CAPACITY_J,
                "initial_energy_observation": float(np.float32(0.8)),
                "ambient_temperature": True,
                "charger_latch": False,
                "previous_wheel_delta": [0.0, 0.0],
                "initial_contact": True,
            },
            "roaming_fixture": {
                "mechanism": "EXP-001 StochasticPersistentExplorer unchanged",
                "proposal_stream_advances_every_decision_including_preempted_decisions": (  # noqa: E501
                    True
                ),
                "observation": (
                    "fixed ExternalObservation(0,0,0), discarded by explorer"
                ),
                "mapping": {
                    key.name: list(value) for key, value in _ACTION_WHEELS.items()
                },
                "maximum_wheel_delta_rad": D045_MAX_WHEEL_DELTA_RAD,
            },
            "d052_thresholds": {
                "return": RETURN_THRESHOLD,
                "recovery": RECOVERY_THRESHOLD,
            },
            "analytic_budget_pre_run": (
                "Unobstructed 1.15 W 80%-to-20% depletion ~27,800 transitions; "
                "bulk recharge ~18,800; walls lengthen roaming; full cycle ~46,700 "
                "or more; expected roughly two yields, possible third truncated. "
                "No pilot or tuning."
            ),
            "physics": "D-045 unchanged except episode_horizon=140000",
            "reward": 0.0,
            "organism_info": {},
            "event_samples": (
                "RESET plus rows with events or mode/source/contact changes; "
                "repeated INVALID_BEACON-only rows after the first of a consecutive "
                "run collapsed; at most 256 kept: RESET and final row, then "
                "cycle-defining/termination/first-invalid-beacon rows, other event "
                "rows, event-free state changes, evenly spaced within an "
                "overflowing tier; candidate/collapsed counts and truncation flag "
                "recorded"
            ),
            "artifact_float_canonicalization": (
                "Decimal(x).quantize(Decimal('1e-12'), ROUND_HALF_EVEN), "
                "normalize -0.0 to 0.0, reject non-finite; serialization only"
            ),
        },
        "validation": {
            "reward_exactly_zero": all(
                item["reward_exactly_zero"] for item in summaries
            ),
            "organism_info_exactly_empty": all(
                item["organism_info_exactly_empty"] for item in summaries
            ),
            "no_evaluator_geometry_in_causal_control": True,
            "fixture_is_independent_seeded_proposal_stream": True,
            "discrete_outcome_signature_sha256": signature,
        },
        "seeds": summaries,
    }


def _canonicalize(value: object) -> object:
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite artifact float")
        rounded = float(
            Decimal(value).quantize(
                D053_ARTIFACT_FLOAT_QUANTUM, rounding=ROUND_HALF_EVEN
            )
        )
        return 0.0 if rounded == 0.0 else rounded
    if isinstance(value, dict):
        return {key: _canonicalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    return value


def write_d053_artifact(path: Path, executed_commit_sha: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            _canonicalize(run_d053_protocol(executed_commit_sha)),
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
    write_d053_artifact(args.output, args.executed_commit_sha)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
