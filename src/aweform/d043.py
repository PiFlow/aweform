"""D-043 fresh-seed repeated-cycle characterization of the D-042 embodiment.

This module is an evaluator-only adapter around the unchanged D-042
environment and D-030/D-027 organism.  It adds no observation, action, reward,
controller, learner, RNG, or physical mechanism.  Event records are created
after each canonical transition and never reach the organism.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Final, Sequence, cast

from . import d026, d027, d030, d042
from .env import Action
from .exp003 import EXP003_B50_ENTER_SEEK_THRESHOLD
from .exp003_seed_policy import validate_exp003_development_seeds

D043_AUTHORITATIVE_BASE_SHA: Final[str] = (
    "1cec3df44ff74995f10f270577d6d8aa1d08d025"
)
D043_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = tuple(range(19045, 19065))
D043_HORIZON: Final[int] = 140_000
D043_DT_SECONDS: Final[float] = d042.D042_DT_SECONDS


def _validate_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    validated = validate_exp003_development_seeds(seeds)
    if validated != D043_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-043 requires exactly the declared fresh seeds "
            f"{D043_DEFAULT_DEVELOPMENT_SEEDS}; got {validated}"
        )
    return validated


def _new_seek_episode(
    *, transition: int, action: Action, energy: float, thermal: float
) -> dict[str, object]:
    return {
        "seek_entry_transition": transition,
        "seek_entry_physical_seconds": transition * D043_DT_SECONDS,
        "entry_action": action.name,
        "energy_at_entry": energy,
        "temperature_normalized_at_entry": thermal,
        "outcome": "unresolved",
        "reacquisition_transition": None,
        "reacquisition_physical_seconds": None,
        "transitions_since_seek_entry": None,
        "physical_seconds_since_seek_entry": None,
        "reacquisition_action": None,
        "energy_at_reacquisition": None,
        "temperature_normalized_at_reacquisition": None,
    }


def _run_d043_seed(seed: int, *, horizon: int = D043_HORIZON) -> dict[str, object]:
    """Run one uninterrupted canonical D-042 lifetime with evaluator telemetry."""
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon <= 0:
        raise ValueError("horizon must be a positive integer")
    if seed not in D043_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(f"seed {seed} is not a declared D-043 seed")
    environment, observation_array, streams = d042._initial_environment(seed, horizon)
    controller = d026.D026Controller(streams.policy)
    controller.reset()
    learner = d027.D027ActionConsequencePredictor()
    current = d042._controller_observation(observation_array)

    action_counts = {action.name: 0 for action in Action}
    mode_occupancy = {mode.name: 0 for mode in d026.D026Mode}
    mode_entry_counts = {mode.name: 0 for mode in d026.D026Mode}
    mode_entry_counts[controller.mode.name] = 1
    contact_entries: list[dict[str, object]] = []
    contact_exits: list[dict[str, object]] = []
    seek_episodes: list[dict[str, object]] = []
    recharge_events: list[dict[str, object]] = []
    reacquisition_transitions: list[int] = []
    recharge_transitions: list[int] = []
    active_seek: dict[str, object] | None = None
    recharge_active = False
    recharge_ready_for_departure = False
    completed_cycles = 0
    post_recharge_departures: list[dict[str, object]] = []
    turn_count = 0
    signed_turns = 0
    absolute_turns = 0
    turn_energy_j = 0.0
    transitions = 0
    terminated = False
    truncated = False
    initial_energy = current.energy
    minimum_energy = maximum_energy = current.energy
    initial_battery_j = d042.D042_INITIAL_BATTERY_J
    minimum_battery_j = maximum_battery_j = initial_battery_j
    initial_temperature = current.thermal
    minimum_temperature = maximum_temperature = current.thermal
    maximum_temperature_c = d042.D042_INITIAL_TEMPERATURE_C

    while not (terminated or truncated):
        mode_before = controller.mode
        mode_occupancy[mode_before.name] += 1
        historical_action = controller.act(current)
        mode_after = controller.mode
        if mode_after is not mode_before:
            mode_entry_counts[mode_after.name] += 1

        # This is the unchanged D-030 arbitration used by D-042.
        action = historical_action
        arbitration = controller.last_arbitration
        if arbitration is not None and not arbitration.delegated:
            predictions, read_only = d030._query_candidate_predictions(
                learner, current
            )
            if not read_only:
                raise RuntimeError("D-030 prediction query mutated learner state")
            action = d030._choose_steering_action(
                current, predictions, arbitration.greedy_action
            )
        action_counts[action.name] += 1
        if action is Action.TURN_LEFT:
            turn_count += 1
            signed_turns += 1
            absolute_turns += 1
        elif action is Action.TURN_RIGHT:
            turn_count += 1
            signed_turns -= 1
            absolute_turns += 1

        entered_seek = (
            mode_before is d026.D026Mode.AWAY
            and mode_after is d026.D026Mode.SEEK
            and current.energy < EXP003_B50_ENTER_SEEK_THRESHOLD
        )
        transition = transitions + 1
        if entered_seek:
            if active_seek is not None:
                raise RuntimeError("overlapping D-043 SEEK episodes")
            active_seek = _new_seek_episode(
                transition=transition,
                action=action,
                energy=current.energy,
                thermal=current.thermal,
            )
            seek_episodes.append(active_seek)

        observation_array, reward, terminated, truncated, info = environment.step(
            action
        )
        if reward != 0.0 or info != {}:
            raise RuntimeError("D-043 transition crossed the reward/info boundary")
        telemetry = environment.last_transition
        if telemetry is None:
            raise RuntimeError("D-043 transition telemetry is unavailable")
        if action in (Action.TURN_LEFT, Action.TURN_RIGHT):
            turn_energy_j += (
                telemetry.actuator_electrical_power_w * environment.config.dt_seconds
            )
        next_observation = d042._controller_observation(observation_array)
        update = learner.observe_transition(current, action, next_observation)
        if update.action is not action:
            raise RuntimeError("D-027 learner update did not use executed action")
        transitions = transition

        if not telemetry.charging_contact_before and telemetry.charging_contact_after:
            contact_entries.append(
                {
                    "transition": transition,
                    "physical_seconds": transition * D043_DT_SECONDS,
                    "action": action.name,
                    "mode_before": mode_before.name,
                    "mode_after": mode_after.name,
                }
            )
        if telemetry.charging_contact_before and not telemetry.charging_contact_after:
            contact_exits.append(
                {
                    "transition": transition,
                    "physical_seconds": transition * D043_DT_SECONDS,
                    "action": action.name,
                    "mode_before": mode_before.name,
                    "mode_after": mode_after.name,
                }
            )

        if active_seek is not None and (
            not telemetry.charging_contact_before and telemetry.charging_contact_after
        ):
            latency = transition - cast(int, active_seek["seek_entry_transition"])
            active_seek.update(
                {
                    "outcome": "reacquired",
                    "reacquisition_transition": transition,
                    "reacquisition_physical_seconds": transition * D043_DT_SECONDS,
                    "transitions_since_seek_entry": latency,
                    "physical_seconds_since_seek_entry": latency * D043_DT_SECONDS,
                    "reacquisition_action": action.name,
                    "energy_at_reacquisition": next_observation.energy,
                    "temperature_normalized_at_reacquisition": next_observation.thermal,
                }
            )
            reacquisition_transitions.append(transition)
            active_seek = None
            recharge_active = True

        if (
            recharge_active
            and telemetry.battery_after_j >= environment.config.battery_capacity_j
            and telemetry.charger_termination_latched_after
        ):
            recharge_events.append(
                {
                    "transition": transition,
                    "physical_seconds": transition * D043_DT_SECONDS,
                    "energy_j": telemetry.battery_after_j,
                    "reacquisition_transition": (
                        reacquisition_transitions[-1]
                        if reacquisition_transitions
                        else None
                    ),
                }
            )
            recharge_transitions.append(transition)
            recharge_active = False
            recharge_ready_for_departure = True

        if mode_before is d026.D026Mode.CHARGE and mode_after is d026.D026Mode.DEPART:
            if recharge_ready_for_departure:
                post_recharge_departures.append(
                    {
                        "transition": transition,
                        "physical_seconds": transition * D043_DT_SECONDS,
                    }
                )
                completed_cycles += 1
                recharge_ready_for_departure = False

        minimum_energy = min(minimum_energy, next_observation.energy)
        maximum_energy = max(maximum_energy, next_observation.energy)
        minimum_battery_j = min(minimum_battery_j, telemetry.battery_after_j)
        maximum_battery_j = max(maximum_battery_j, telemetry.battery_after_j)
        maximum_temperature = max(maximum_temperature, next_observation.thermal)
        minimum_temperature = min(minimum_temperature, next_observation.thermal)
        maximum_temperature_c = max(
            maximum_temperature_c, telemetry.body_temperature_after_c
        )
        current = next_observation

    if active_seek is not None:
        active_seek["outcome"] = (
            "terminated_before_reacquisition" if terminated else "horizon_censored"
        )
    if environment.last_transition is None:
        raise RuntimeError("D-043 lifetime produced no transition")
    termination_reason = d042._termination_reason(environment, terminated, truncated)
    unresolved = sum(
        int(episode["outcome"] in ("unresolved", "horizon_censored"))
        for episode in seek_episodes
    )
    if terminated and active_seek is not None:
        unresolved = 1
    horizon_censored_seek_episodes = sum(
        int(episode["outcome"] == "horizon_censored")
        for episode in seek_episodes
    )
    terminated_unresolved_seek_episodes = sum(
        int(episode["outcome"] == "terminated_before_reacquisition")
        for episode in seek_episodes
    )
    if completed_cycles:
        outcome = "REPEATED_CYCLE" if completed_cycles >= 2 else "FULL_CYCLE"
    elif recharge_events:
        outcome = "RECHARGED_NOT_DEPARTED"
    elif seek_episodes:
        outcome = "SEEK_REACQUIRED" if reacquisition_transitions else (
            "SEEK_UNRESOLVED"
        )
    else:
        outcome = "HORIZON_CENSORED" if truncated else "INITIAL_LIFETIME_ONLY"
    return {
        "seed": seed,
        "outcome": outcome,
        "transitions": transitions,
        "physical_seconds": transitions * D043_DT_SECONDS,
        "terminated": terminated,
        "truncated": truncated,
        "termination_reason": termination_reason,
        "action_counts": action_counts,
        "mode_occupancy": mode_occupancy,
        "mode_entry_counts": mode_entry_counts,
        "initial_dual_contact": True,
        "contact_entries": contact_entries,
        "contact_exits": contact_exits,
        "low_energy_seek_entries": len(seek_episodes),
        "seek_episodes": seek_episodes,
        "unresolved_seek_episodes": unresolved,
        "horizon_censored_seek_episodes": horizon_censored_seek_episodes,
        "terminated_unresolved_seek_episodes": terminated_unresolved_seek_episodes,
        "physical_reacquisitions": len(reacquisition_transitions),
        "full_recharge_events": len(recharge_events),
        "recharge_events": recharge_events,
        "post_recharge_redepartures": len(post_recharge_departures),
        "post_recharge_departure_events": post_recharge_departures,
        "completed_autonomous_recharge_cycles": completed_cycles,
        "reacquisition_transition_spacing": [
            right - left
            for left, right in zip(
                reacquisition_transitions, reacquisition_transitions[1:], strict=False
            )
        ],
        "recharge_transition_spacing": [
            right - left
            for left, right in zip(
                recharge_transitions, recharge_transitions[1:], strict=False
            )
        ],
        "turns": {
            "count": turn_count,
            "signed_count": signed_turns,
            "absolute_count": absolute_turns,
            "commanded_signed_angle_radians": signed_turns * d042.D042_TURN_ANGLE,
            "commanded_absolute_angle_radians": absolute_turns * d042.D042_TURN_ANGLE,
            "electrical_energy_j": turn_energy_j,
            "timestep_seconds": turn_count * D043_DT_SECONDS,
        },
        "battery_j": {
            "start": initial_battery_j,
            "minimum": minimum_battery_j,
            "final": environment.battery_j,
            "maximum": maximum_battery_j,
        },
        "battery_normalized": {
            "start": initial_energy,
            "minimum": minimum_energy,
            "final": current.energy,
            "maximum": maximum_energy,
        },
        "temperature_normalized": {
            "start": initial_temperature,
            "minimum": minimum_temperature,
            "maximum": maximum_temperature,
            "final": current.thermal,
        },
        "max_body_temperature_c": maximum_temperature_c,
    }


def _nearest_rank(values: Sequence[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(1, math.ceil(percentile * len(ordered))) - 1]


def _aggregate(results: Sequence[dict[str, object]]) -> dict[str, object]:
    seek_episodes = [
        episode
        for result in results
        for episode in cast(list[dict[str, object]], result["seek_episodes"])
    ]
    latencies = [
        cast(float, episode["transitions_since_seek_entry"])
        for episode in seek_episodes
        if episode["outcome"] == "reacquired"
    ]
    termination_failures = sum(
        int(
            result["termination_reason"]
            in {
                "energy_depletion",
                "protective_thermal_shutdown",
                "emergency_hard_thermal_shutdown",
            }
        )
        for result in results
    )
    return {
        "lifetime_count": len(results),
        "seed_count_entering_seek": sum(
            int(cast(int, result["low_energy_seek_entries"]) > 0)
            for result in results
        ),
        "seed_count_reacquiring_at_least_once": sum(
            int(cast(int, result["physical_reacquisitions"]) > 0)
            for result in results
        ),
        "seed_count_full_recharge_after_reacquisition": sum(
            int(cast(int, result["full_recharge_events"]) > 0)
            for result in results
        ),
        "seed_count_at_least_two_autonomous_cycles": sum(
            int(cast(int, result["completed_autonomous_recharge_cycles"]) >= 2)
            for result in results
        ),
        "total_seek_episodes": len(seek_episodes),
        "total_physical_reacquisitions": sum(
            cast(int, result["physical_reacquisitions"]) for result in results
        ),
        "total_full_recharge_events": sum(
            cast(int, result["full_recharge_events"]) for result in results
        ),
        "total_completed_autonomous_recharge_cycles": sum(
            cast(int, result["completed_autonomous_recharge_cycles"])
            for result in results
        ),
        "unresolved_seek_episodes_at_horizon": sum(
            cast(int, result["horizon_censored_seek_episodes"])
            for result in results
        ),
        "unresolved_seek_episodes_at_termination": sum(
            cast(int, result["terminated_unresolved_seek_episodes"])
            for result in results
        ),
        "termination_reason_counts": {
            reason: sum(
                int(result["termination_reason"] == reason) for result in results
            )
            for reason in (
                "energy_depletion",
                "protective_thermal_shutdown",
                "emergency_hard_thermal_shutdown",
                "horizon_truncation",
            )
        },
        "energy_or_thermal_failure_lifetimes": termination_failures,
        "reacquisition_latency_transitions": {
            "count": len(latencies),
            "minimum": min(latencies, default=None),
            "maximum": max(latencies, default=None),
            "mean": statistics.fmean(latencies) if latencies else None,
            "median": statistics.median(latencies) if latencies else None,
            "p90_nearest_rank": _nearest_rank(latencies, 0.90),
            "percentile_method": "nearest-rank",
        },
        "outcome_counts": {
            outcome: sum(int(result["outcome"] == outcome) for result in results)
            for outcome in (
                "REPEATED_CYCLE",
                "FULL_CYCLE",
                "RECHARGED_NOT_DEPARTED",
                "SEEK_REACQUIRED",
                "SEEK_UNRESOLVED",
                "HORIZON_CENSORED",
                "INITIAL_LIFETIME_ONLY",
            )
        },
    }


def run_d043_probe(
    seeds: Sequence[int] = D043_DEFAULT_DEVELOPMENT_SEEDS,
    *,
    horizon: int = D043_HORIZON,
    executed_commit_sha: str | None = None,
) -> dict[str, object]:
    """Run exactly the frozen D-043 Development lifetimes."""
    validated_seeds = _validate_seeds(seeds)
    if horizon != D043_HORIZON:
        raise ValueError("D-043 characterization requires the frozen horizon")
    executed_sha = d042._validate_executed_commit_sha(executed_commit_sha)
    results = [_run_d043_seed(seed, horizon=horizon) for seed in validated_seeds]
    return {
        "schema_version": 1,
        "experiment": "D-043",
        "title": "Fresh-seed repeated-cycle robustness of accepted D-042 embodiment",
        "authoritative_base_sha": D043_AUTHORITATIVE_BASE_SHA,
        "implementation_probe_sha": executed_sha,
        "development_seeds": list(validated_seeds),
        "horizon": horizon,
        "timestep_seconds": D043_DT_SECONDS,
        "lifetime": "one uninterrupted causal lifetime per seed",
        "seed_policy": {
            "canonical_validator": "validate_exp003_development_seeds",
            "formal_reservation_guard_preserved": True,
            "formal_reserved_ranges_excluded": True,
            "fresh_declared_support": True,
        },
        "embodiment": {
            "source": "src/aweform/d042.py",
            "turn_angle_radians": d042.D042_TURN_ANGLE,
            "turn_angle_degrees": d042.D042_TURN_ANGLE_DEGREES,
            "turn_angle_expression": "pi / 36",
            "turn_action_seconds": D043_DT_SECONDS,
            "turn_actuator_electrical_power_w": 0.65,
            "body_front_contacts_body_frame": [
                [d042.D042_FRONT_X, d042.D042_CONTACT_LATERAL_OFFSET],
                [d042.D042_FRONT_X, -d042.D042_CONTACT_LATERAL_OFFSET],
            ],
            "dock_orientation": d042.D042_DOCK_ORIENTATION,
            "dock_contacts_station_offsets": [
                [0.0, d042.D042_CONTACT_LATERAL_OFFSET],
                [0.0, -d042.D042_CONTACT_LATERAL_OFFSET],
            ],
            "contact_tolerance_inclusive": d042.D042_CONTACT_TOLERANCE,
        },
        "canonical_organism": {
            "controller": "unchanged d026.D026Controller / D-030 semantics",
            "learner": "unchanged d027.D027ActionConsequencePredictor",
            "de_trap": "unchanged D-026 delegation and explorer streams",
            "actions": [action.name for action in Action],
            "visible_channels": list(d027.D027_CHANNELS),
            "reward": 0.0,
            "info": {},
        },
        "organism_boundary": {
            "coordinates_heading_and_contact_errors_visible": False,
            "evaluator_geometry_and_event_diagnostics": True,
        },
        "interpretation": (
            "Descriptive Development characterization only; no universal pass "
            "threshold, statistical generalization, or Evidence-lane claim."
        ),
        "results": results,
        "aggregate": _aggregate(results),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--executed-commit-sha", required=True)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    args.output.write_text(
        json.dumps(
            run_d043_probe(executed_commit_sha=args.executed_commit_sha),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
