"""D-021 fixed V0.4 autonomous energy-regulation baseline.

This module couples a small fixed four-mode controller to ``D020Env``.  It
does not reuse D-014's historical thermal departure rule and does not add a
learner, reward, evaluator input, or new physical mechanism.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import replace
from pathlib import Path
from typing import Final, Sequence, cast

import numpy as np

from . import d011
from .d020 import D020Env, D020PhysicalConfig, D020TerminationReason
from .env import Action
from .exp001 import ExternalObservation, StochasticPersistentExplorer
from .exp003 import (
    EXP003_B50_ENTER_SEEK_THRESHOLD,
    BeaconObservation,
    seek_beacon_action,
)
from .exp003_seed_policy import validate_exp003_development_seeds
from .rng import RandomStreams

D021_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = (18365, 18366, 18367)
D021_HORIZON: Final[int] = 70_000
D021_FULL_ENERGY_THRESHOLD: Final[float] = 1.0
D021_AUTHORITATIVE_BASE_SHA: Final[str] = (
    "eb632767bc2fedf2465e8b24b6b3395841b9b54a"
)

D021Mode = d011.D011Mode
D021Observation = d011.D011Observation


class D021Controller:
    """Fixed four-mode energy controller with historical exploration only."""

    def __init__(self, policy_rng: np.random.Generator) -> None:
        self.explorer = StochasticPersistentExplorer(policy_rng)
        self.mode = D021Mode.CHARGE

    def reset(self) -> None:
        """Reset this controller's state for a new uninterrupted lifetime."""
        self.mode = D021Mode.CHARGE
        self.explorer.begin_segment()

    def act(self, observation: D021Observation) -> Action:
        """Select an action using only the current six-channel projection."""
        if not isinstance(observation, D021Observation):
            raise ValueError("observation must be a D011Observation")

        if self.mode is D021Mode.CHARGE:
            if not observation.charging_contact:
                self.mode = D021Mode.SEEK
            elif observation.energy >= D021_FULL_ENERGY_THRESHOLD:
                self.mode = D021Mode.DEPART
                return Action.MOVE_FORWARD
            else:
                return Action.WAIT

        if self.mode is D021Mode.DEPART:
            if observation.charging_contact:
                return Action.MOVE_FORWARD
            self.mode = D021Mode.AWAY

        if self.mode is D021Mode.AWAY:
            if observation.energy < EXP003_B50_ENTER_SEEK_THRESHOLD:
                self.mode = D021Mode.SEEK
            else:
                return self._explore_action(observation.beacon)

        if self.mode is D021Mode.SEEK:
            if observation.charging_contact:
                self.mode = D021Mode.CHARGE
                return Action.WAIT
            return seek_beacon_action(observation.beacon)

        raise RuntimeError(f"unsupported D-021 controller mode: {self.mode}")

    def _explore_action(self, beacon: BeaconObservation) -> Action:
        return self.explorer.act(
            ExternalObservation(beacon.left, beacon.forward, beacon.right)
        )


def _controller_observation(observation: np.ndarray) -> D021Observation:
    """Project exactly D-020's six ordinary channels into the controller."""
    if observation.shape != (6,):
        raise ValueError("D-020 observation must contain six values")
    contact_signal = float(observation[4])
    if contact_signal not in (0.0, 1.0):
        raise ValueError("D-020 charging contact channel must be binary")
    return D021Observation(
        energy=float(observation[0]),
        beacon=BeaconObservation(
            left=float(observation[1]),
            forward=float(observation[2]),
            right=float(observation[3]),
            charging_contact=bool(contact_signal),
        ),
        thermal=float(observation[5]),
    )


def _validate_d021_development_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    """Apply the canonical guard, then accept only the frozen D-021 seeds."""
    validated = validate_exp003_development_seeds(seeds)
    unexpected = tuple(
        seed for seed in validated if seed not in D021_DEFAULT_DEVELOPMENT_SEEDS
    )
    if unexpected:
        raise ValueError(
            "D-021 may execute only predeclared development seeds "
            f"{D021_DEFAULT_DEVELOPMENT_SEEDS}; got {unexpected}"
        )
    return validated


def _validate_executed_commit_sha(value: str | None) -> str | None:
    if value is None:
        return None
    if re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise ValueError("executed_commit_sha must be a 40-character lowercase SHA")
    return value


def _termination_reason(
    *, terminated: bool, truncated: bool, reason: D020TerminationReason | None
) -> str:
    if terminated and reason is D020TerminationReason.ENERGY_DEPLETION:
        return "energy_depletion"
    if terminated and reason is D020TerminationReason.PROTECTIVE_THERMAL_SHUTDOWN:
        return "protective_thermal_shutdown"
    if terminated and reason is D020TerminationReason.EMERGENCY_HARD_THERMAL_SHUTDOWN:
        return "emergency_hard_thermal_shutdown"
    if truncated:
        return "horizon_truncation"
    return "incomplete"


def _mode_counts() -> dict[str, int]:
    return {mode.name: 0 for mode in D021Mode}


def _distance(position: tuple[float, float], station: tuple[float, float]) -> float:
    return math.dist(position, station)


def _new_seek_episode(
    *,
    transition_index: int,
    observation: D021Observation,
    action: Action,
    distance: float,
) -> dict[str, object]:
    return {
        "seek_entry_transition": transition_index,
        "energy_at_entry": observation.energy,
        "temperature_normalized_at_entry": observation.thermal,
        "charging_contact_at_entry": observation.charging_contact,
        "entry_action": action.name,
        "evaluator_distance_at_entry": distance,
        "outcome": "unresolved",
        "reacquisition_transition": None,
        "transitions_since_seek_entry": None,
        "energy_at_reacquisition": None,
        "temperature_normalized_at_reacquisition": None,
        "evaluator_distance_at_reacquisition": None,
        "reacquisition_action": None,
    }


def _classify_unresolved_seek(*, terminated: bool, truncated: bool) -> dict[str, int]:
    """Classify one unresolved SEEK without converting censoring into failure."""
    return {
        "demonstrated_failed_seek_episodes": int(terminated and not truncated),
        "horizon_censored_seek_episodes": int(truncated and not terminated),
    }


def _run_seed(seed: int, *, horizon: int) -> dict[str, object]:
    config = D020PhysicalConfig()
    run_config = replace(config, episode_horizon=horizon)
    streams = RandomStreams.from_seed(seed)
    seeded_heading = float(streams.environment.uniform(0.0, math.tau))
    environment = D020Env(run_config)
    observation, info = environment.reset(
        options={
            "body_position": (0.5, 0.5),
            "station_center": (0.5, 0.5),
            "heading": seeded_heading,
            "battery_j": config.battery_capacity_j,
            "body_temperature_c": 23.0,
            "charger_termination_latched": False,
        }
    )
    if info != {}:
        raise RuntimeError("D-020 reset crossed the information boundary")
    if environment.body is None or environment.station_center is None:
        raise RuntimeError("D-020 reset did not initialize evaluator geometry")

    controller = D021Controller(streams.policy)
    controller.reset()
    action_counts = {action.name: 0 for action in Action}
    mode_occupancy = _mode_counts()
    mode_entry_counts = _mode_counts()
    mode_entry_counts[controller.mode.name] = 1
    transitions = 0
    initial_energy = float(observation[0])
    minimum_energy = initial_energy
    maximum_energy = initial_energy
    final_energy = initial_energy
    minimum_battery_j = config.battery_capacity_j
    maximum_battery_j = config.battery_capacity_j
    initial_temperature = float(observation[5])
    maximum_temperature = initial_temperature
    final_temperature = initial_temperature
    maximum_temperature_c = 23.0
    final_temperature_c = 23.0

    full_departures = 0
    initial_full_departures = 0
    post_recharge_redepartures = 0
    charger_exits = 0
    low_energy_seek_entries = 0
    physical_reacquisitions = 0
    charge_entries = 0
    full_recharge_events = 0
    completed_cycles = 0
    accidental_away_contacts = 0
    mode_event_inconsistencies: list[str] = []
    seek_episodes: list[dict[str, object]] = []
    active_seek: dict[str, object] | None = None
    recharge_ready_for_departure = False
    recharge_episode_active = False
    cycle_stage = 0
    terminated = False
    truncated = False

    while not (terminated or truncated):
        if environment.body is None or environment.station_center is None:
            raise RuntimeError("D-020 evaluator geometry disappeared")
        current = _controller_observation(observation)
        mode_before = controller.mode
        mode_occupancy[mode_before.name] += 1
        action = controller.act(current)
        mode_after = controller.mode
        action_counts[action.name] += 1
        if mode_after is not mode_before:
            mode_entry_counts[mode_after.name] += 1

        transition_index = transitions + 1
        if mode_before is D021Mode.CHARGE and mode_after is D021Mode.DEPART:
            if (
                not current.charging_contact
                or current.energy < D021_FULL_ENERGY_THRESHOLD
            ):
                mode_event_inconsistencies.append("full_departure_without_full_contact")
            full_departures += 1
            if recharge_ready_for_departure and cycle_stage == 5:
                post_recharge_redepartures += 1
                completed_cycles += 1
                recharge_ready_for_departure = False
                recharge_episode_active = False
                cycle_stage = 1
            elif cycle_stage == 0:
                initial_full_departures += 1
                cycle_stage = 1
            else:
                mode_event_inconsistencies.append("unexpected_full_departure_stage")
        if mode_before is D021Mode.SEEK and mode_after is D021Mode.CHARGE:
            charge_entries += 1

        observation, reward, terminated, truncated, info = environment.step(action)
        if reward != 0.0 or info != {}:
            raise RuntimeError("D-020 reward or info crossed the boundary")
        telemetry = environment.last_transition
        if telemetry is None:
            raise RuntimeError("D-020 transition telemetry is unavailable")
        transitions += 1

        final_energy = float(observation[0])
        minimum_energy = min(minimum_energy, final_energy)
        maximum_energy = max(maximum_energy, final_energy)
        final_temperature = float(observation[5])
        maximum_temperature = max(maximum_temperature, final_temperature)
        final_temperature_c = telemetry.body_temperature_after_c
        maximum_temperature_c = max(maximum_temperature_c, final_temperature_c)
        minimum_battery_j = min(minimum_battery_j, telemetry.battery_after_j)
        maximum_battery_j = max(maximum_battery_j, telemetry.battery_after_j)

        if telemetry.charging_contact_before and not telemetry.charging_contact_after:
            charger_exits += 1
            if cycle_stage == 1:
                cycle_stage = 2

        entered_seek = (
            mode_before is D021Mode.AWAY
            and mode_after is D021Mode.SEEK
            and current.energy < EXP003_B50_ENTER_SEEK_THRESHOLD
        )
        if entered_seek:
            if active_seek is not None:
                mode_event_inconsistencies.append("overlapping_seek_episodes")
            distance = _distance(environment.body.position, environment.station_center)
            active_seek = _new_seek_episode(
                transition_index=transition_index,
                observation=current,
                action=action,
                distance=distance,
            )
            seek_episodes.append(active_seek)
            low_energy_seek_entries += 1
            if cycle_stage == 2 and not current.charging_contact:
                cycle_stage = 3
            elif cycle_stage != 3:
                mode_event_inconsistencies.append("seek_entry_outside_exit_stage")

        if (
            mode_before is D021Mode.AWAY
            and current.energy >= EXP003_B50_ENTER_SEEK_THRESHOLD
            and not telemetry.charging_contact_before
            and telemetry.charging_contact_after
        ):
            accidental_away_contacts += 1

        if (
            active_seek is not None
            and not bool(active_seek["charging_contact_at_entry"])
            and telemetry.charging_contact_before is False
            and telemetry.charging_contact_after
        ):
            physical_reacquisitions += 1
            active_seek["outcome"] = "reacquired"
            active_seek["reacquisition_transition"] = transition_index
            active_seek["transitions_since_seek_entry"] = (
                transition_index
                - cast(int, active_seek["seek_entry_transition"])
            )
            active_seek["energy_at_reacquisition"] = float(observation[0])
            active_seek["temperature_normalized_at_reacquisition"] = float(
                observation[5]
            )
            active_seek["evaluator_distance_at_reacquisition"] = _distance(
                environment.body.position, environment.station_center
            )
            active_seek["reacquisition_action"] = action.name
            recharge_episode_active = True
            if cycle_stage == 3:
                cycle_stage = 4
            active_seek = None
        elif (
            active_seek is not None
            and bool(active_seek["charging_contact_at_entry"])
            and telemetry.charging_contact_after
        ):
            active_seek["outcome"] = "contact_already_true_at_entry"
            active_seek["transitions_since_seek_entry"] = (
                transition_index
                - cast(int, active_seek["seek_entry_transition"])
            )
            active_seek = None

        if (
            recharge_episode_active
            and telemetry.battery_after_j >= run_config.battery_capacity_j
            and telemetry.charger_termination_latched_after
        ):
            full_recharge_events += 1
            recharge_episode_active = False
            recharge_ready_for_departure = True
            if cycle_stage == 4:
                cycle_stage = 5
            else:
                mode_event_inconsistencies.append("full_recharge_outside_reacquisition_stage")

    if active_seek is not None:
        if terminated:
            active_seek["outcome"] = "terminated_before_reacquisition"
        elif truncated:
            active_seek["outcome"] = "horizon_censored"
        else:
            mode_event_inconsistencies.append("unresolved_seek_without_termination")

    unresolved_seek_at_termination = int(terminated and active_seek is not None)
    unresolved_seek_at_horizon = int(truncated and active_seek is not None)
    seek_classification = _classify_unresolved_seek(
        terminated=terminated,
        truncated=truncated,
    )
    failed_seek_episodes = int(
        active_seek is not None
        and seek_classification["demonstrated_failed_seek_episodes"]
        and not bool(active_seek["charging_contact_at_entry"])
    )
    horizon_censored_seek_episodes = int(
        active_seek is not None
        and seek_classification["horizon_censored_seek_episodes"]
    )
    reacquisition_terminated_before_full_recharge = int(
        terminated and recharge_episode_active
    )
    full_recharge_without_redeparture = int(truncated and recharge_ready_for_departure)
    final_telemetry = environment.last_transition
    if final_telemetry is None:
        raise RuntimeError("D-021 run ended without final telemetry")

    return {
        "seed": seed,
        "seeded_heading": seeded_heading,
        "transitions": transitions,
        "physical_seconds": transitions * run_config.dt_seconds,
        "terminated": terminated,
        "truncated": truncated,
        "termination_reason": _termination_reason(
            terminated=terminated,
            truncated=truncated,
            reason=final_telemetry.termination_reason,
        ),
        "final_mode": controller.mode.name,
        "action_counts": action_counts,
        "mode_occupancy": mode_occupancy,
        "mode_entry_counts": mode_entry_counts,
        "battery_normalized": {
            "start": initial_energy,
            "minimum": minimum_energy,
            "final": final_energy,
            "maximum": maximum_energy,
        },
        "battery_j": {
            "start": run_config.battery_capacity_j,
            "minimum": minimum_battery_j,
            "final": environment.battery_j,
            "maximum": maximum_battery_j,
        },
        "temperature_normalized": {
            "start": initial_temperature,
            "maximum": maximum_temperature,
            "final": final_temperature,
        },
        "temperature_c": {
            "maximum": maximum_temperature_c,
            "final": final_temperature_c,
        },
        "full_departures": full_departures,
        "initial_full_departures": initial_full_departures,
        "physical_charger_exits": charger_exits,
        "low_energy_seek_entries": low_energy_seek_entries,
        "physical_reacquisitions": physical_reacquisitions,
        "charge_entries": charge_entries,
        "full_recharge_events": full_recharge_events,
        "post_recharge_redepartures": post_recharge_redepartures,
        "completed_energy_regulation_cycles": completed_cycles,
        "accidental_away_contacts": accidental_away_contacts,
        "seek_episodes": seek_episodes,
        "failure_and_censoring": {
            "energy_depletion": final_telemetry.energy_nonviable,
            "protective_thermal_shutdown": final_telemetry.protective_shutdown,
            "emergency_hard_thermal_shutdown": final_telemetry.emergency_hard_shutdown,
            "horizon_truncation": truncated,
            "unresolved_seek_at_termination": unresolved_seek_at_termination,
            "unresolved_seek_at_horizon": unresolved_seek_at_horizon,
            "demonstrated_failed_seek_episodes": failed_seek_episodes,
            "horizon_censored_seek_episodes": horizon_censored_seek_episodes,
            "reacquisition_followed_by_termination_before_full_recharge": (
                reacquisition_terminated_before_full_recharge
            ),
            "full_recharge_without_redeparture_before_horizon": (
                full_recharge_without_redeparture
            ),
            "mode_event_inconsistencies": mode_event_inconsistencies,
        },
        "thermal_diagnostics": {
            "starting_temperature_normalized": initial_temperature,
            "maximum_temperature_normalized": maximum_temperature,
            "final_temperature_normalized": final_temperature,
            "maximum_temperature_c": maximum_temperature_c,
            "final_temperature_c": final_temperature_c,
            "preferred_45_c_reached": (
                maximum_temperature_c >= run_config.preferred_operating_ceiling_c
            ),
            "protective_60_c_occurred": final_telemetry.protective_shutdown,
            "emergency_65_c_occurred": final_telemetry.emergency_hard_shutdown,
        },
    }

def run_d021_probe(
    seeds: Sequence[int] = D021_DEFAULT_DEVELOPMENT_SEEDS,
    *,
    horizon: int = D021_HORIZON,
    executed_commit_sha: str | None = None,
) -> dict[str, object]:
    """Run one continuous fixed-controller lifetime for each frozen seed."""
    development_seeds = _validate_d021_development_seeds(seeds)
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon <= 0:
        raise ValueError("horizon must be a positive integer")
    executed_sha = _validate_executed_commit_sha(executed_commit_sha)
    return {
        "schema_version": 1,
        "experiment": "D-021",
        "title": "Minimal autonomous V0.4 energy-regulation baseline",
        "authoritative_base_sha": D021_AUTHORITATIVE_BASE_SHA,
        "implementation_probe_sha": executed_sha,
        "development_seeds": list(development_seeds),
        "horizon": horizon,
        "timestep_seconds": D020PhysicalConfig().dt_seconds,
        "simulated_duration_seconds": horizon * D020PhysicalConfig().dt_seconds,
        "lifetime": "one uninterrupted lifetime per seed",
        "seed_policy": {
            "canonical_validator": "validate_exp003_development_seeds",
            "exact_declared_seeds": list(D021_DEFAULT_DEVELOPMENT_SEEDS),
            "formal_reservation_guard_preserved": True,
        },
        "freeze": {
            "controller": "D021Controller",
            "full_energy_threshold": D021_FULL_ENERGY_THRESHOLD,
            "low_energy_seek_threshold": EXP003_B50_ENTER_SEEK_THRESHOLD,
            "exploration_hazard": 1.0 / 8.0,
            "initial_body_position": [0.5, 0.5],
            "initial_station_center": [0.5, 0.5],
            "initial_battery": "D020PhysicalConfig.battery_capacity_j",
            "initial_body_temperature_c": 23.0,
            "initial_charger_termination_latched": False,
            "initial_heading": (
                "RandomStreams.from_seed(seed).environment.uniform(0.0, 2*pi)"
            ),
            "physical_config": "D020PhysicalConfig unchanged except episode_horizon",
            "event_definitions_frozen": True,
        },
        "programmed": {
            "controller_modes": [mode.name for mode in D021Mode],
            "controller": "fixed non-learning D021Controller",
            "full_departure_rule": "CHARGE contact and normalized energy >= 1.0",
            "low_energy_seek_rule": "AWAY normalized energy < inherited 0.50 threshold",
            "exploration": "StochasticPersistentExplorer with EXP001 hazard 1/8",
            "seek": "existing seek_beacon_action",
            "thermal_behavioral_influence": "zero",
            "learning": False,
        },
        "organism_visible": {
            "observation_type": "D011Observation projection of D020's six channels",
            "channels": [
                "normalized own battery energy",
                "beacon left",
                "beacon forward",
                "beacon right",
                "charging_contact",
                "normalized own body temperature",
            ],
            "temperature_used_for_behavior": False,
        },
        "evaluator_only": {
            "fields": [
                "x/y/heading after initial setup",
                "station location",
                "true distance",
                "battery joules",
                "absolute Celsius",
                "charger phase/latch",
                "telemetry and event summaries",
                "shutdown reason",
            ],
            "passed_to_controller": False,
        },
        "learned": {"status": "none"},
        "organism_boundary": {"reward": 0.0, "info": {}},
        "results": [_run_seed(seed, horizon=horizon) for seed in development_seeds],
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the D-021 fixed V0.4 energy-regulation baseline."
    )
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=list(D021_DEFAULT_DEVELOPMENT_SEEDS),
        help="Predeclared D-021 development seeds only.",
    )
    parser.add_argument("--horizon", type=int, default=D021_HORIZON)
    parser.add_argument("--executed-commit-sha")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    payload = json.dumps(
        run_d021_probe(
            tuple(args.seeds),
            horizon=args.horizon,
            executed_commit_sha=args.executed_commit_sha,
        ),
        indent=2,
        sort_keys=True,
    )
    if args.output is None:
        print(payload)
    else:
        args.output.write_text(payload + "\n", encoding="utf-8")
        print(f"D-021 result written to {args.output}")


if __name__ == "__main__":
    main()
