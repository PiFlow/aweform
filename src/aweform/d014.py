"""D-014 full-charge-or-thermal departure scaffold correction.

This module keeps the D-011 controller and ecology historical while changing
one programmed CHARGE departure condition: full organism-visible normalized
energy now departs before the hot-thermal threshold when it is reached first.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Final, Sequence

from . import d011
from .d002 import D002ThermalStationEnv
from .d003 import HOT_DEPART_THRESHOLD
from .env import Action
from .exp003 import (
    EXP003_B50_ENTER_SEEK_THRESHOLD,
    EXP003StationConfig,
)
from .exp003_seed_policy import validate_exp003_development_seeds

D014_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = (18347, 18348, 18349)
D014_HORIZON: Final[int] = 1000
D014_FULL_ENERGY_THRESHOLD: Final[float] = 1.0
D014_AUTHORITATIVE_BASE_SHA: Final[str] = (
    "8a62f0931de40dc85d26ec1ddbd3c1003fa1b723"
)


class D014Controller(d011.D011Controller):
    """D-011 controller with only the full-energy CHARGE correction."""

    def act(self, observation: d011.D011Observation) -> Action:
        """Depart on full normalized energy, otherwise use D-011 exactly."""
        if not isinstance(observation, d011.D011Observation):
            raise ValueError("observation must be a D011Observation")
        if (
            self.mode is d011.D011Mode.CHARGE
            and observation.charging_contact
            and observation.energy >= D014_FULL_ENERGY_THRESHOLD
        ):
            self.mode = d011.D011Mode.DEPART
            return Action.MOVE_FORWARD
        return super().act(observation)


def _validate_d014_development_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    """Apply the canonical guard, then accept only D-014's three seeds."""
    validated = validate_exp003_development_seeds(seeds)
    unexpected = tuple(
        seed for seed in validated if seed not in D014_DEFAULT_DEVELOPMENT_SEEDS
    )
    if unexpected:
        raise ValueError(
            "D-014 may execute only predeclared development seeds "
            f"{D014_DEFAULT_DEVELOPMENT_SEEDS}; got {unexpected}"
        )
    return validated


def _termination_reason(
    *, terminated: bool, truncated: bool, energy: bool, thermal: bool
) -> str:
    if terminated and energy and thermal:
        return "energy_and_thermal_failure"
    if terminated and energy:
        return "energy_failure"
    if terminated and thermal:
        return "thermal_failure"
    if truncated:
        return "horizon_truncation"
    return "incomplete"


def _mode_counts() -> dict[str, int]:
    return {mode.name: 0 for mode in d011.D011Mode}


def _run_seed(seed: int, *, horizon: int) -> dict[str, object]:
    config = EXP003StationConfig(episode_horizon=horizon)
    environment = D002ThermalStationEnv(config=config)
    observation, info = environment.reset(seed=seed)
    if info != {}:
        raise RuntimeError("D-002 reset crossed the information boundary")
    seeded_heading, observation = d011._prepare_post_contact_setup(environment)
    random_streams = environment.base_env.random_streams
    if random_streams is None:
        raise RuntimeError("D-002 policy RNG is unavailable after reset")

    controller = D014Controller(random_streams.policy)
    controller.reset()
    action_counts = {action.name: 0 for action in Action}
    mode_occupancy = _mode_counts()
    mode_entry_counts = _mode_counts()
    mode_entry_counts[controller.mode.name] = 1
    transitions = 0
    minimum_energy = float(observation[0])
    final_energy = minimum_energy
    maximum_thermal = float(observation[5])
    final_thermal = maximum_thermal
    departure_events: list[dict[str, object]] = []
    trigger_counts = {"full_only": 0, "thermal_only": 0, "both": 0}
    charger_exits = 0
    away_entries = 0
    low_energy_seek_entries = 0
    successful_reacquisitions = 0
    completed_cycles = 0
    active_seek_entry: int | None = None
    active_seek_contact_at_entry = False
    active_seek_reacquired = False
    cycle_open = False
    cycle_has_exit = False
    cycle_waiting_for_reacquisition = False

    terminated = False
    truncated = False
    while not (terminated or truncated):
        current = d011._controller_observation(observation)
        mode_before = controller.mode
        mode_occupancy[mode_before.name] += 1
        action = controller.act(current)
        mode_after = controller.mode
        action_counts[action.name] += 1
        if mode_after is not mode_before:
            mode_entry_counts[mode_after.name] += 1

        if mode_before is d011.D011Mode.CHARGE and mode_after is d011.D011Mode.DEPART:
            full_energy_condition = current.energy >= D014_FULL_ENERGY_THRESHOLD
            hot_thermal_condition = current.thermal >= HOT_DEPART_THRESHOLD
            if full_energy_condition and hot_thermal_condition:
                trigger_category = "both"
            elif full_energy_condition:
                trigger_category = "full_only"
            elif hot_thermal_condition:
                trigger_category = "thermal_only"
            else:
                raise RuntimeError("D-014 departed without a valid trigger")
            trigger_counts[trigger_category] += 1
            departure_events.append(
                {
                    "transition_index": transitions + 1,
                    "decision_index": transitions + 1,
                    "energy": current.energy,
                    "thermal": current.thermal,
                    "charging_contact": current.charging_contact,
                    "full_energy_condition": full_energy_condition,
                    "hot_thermal_condition": hot_thermal_condition,
                    "trigger_category": trigger_category,
                }
            )
            cycle_open = True
            cycle_has_exit = False
            cycle_waiting_for_reacquisition = False
        if mode_before is d011.D011Mode.DEPART and mode_after is d011.D011Mode.AWAY:
            away_entries += 1

        observation, reward, terminated, truncated, info = environment.step(action)
        if reward != 0.0 or info != {}:
            raise RuntimeError("D-002 reward or info crossed the boundary")
        telemetry = environment.last_transition
        if telemetry is None:
            raise RuntimeError("D-014 transition telemetry is unavailable")
        transitions += 1
        final_energy = float(observation[0])
        minimum_energy = min(minimum_energy, final_energy)
        final_thermal = float(observation[5])
        maximum_thermal = max(maximum_thermal, final_thermal)

        if telemetry.charging_contact_before and not telemetry.charging_contact_after:
            charger_exits += 1
            cycle_has_exit = True

        entered_low_energy_seek = (
            mode_before is d011.D011Mode.AWAY
            and mode_after is d011.D011Mode.SEEK
            and current.energy < EXP003_B50_ENTER_SEEK_THRESHOLD
        )
        if entered_low_energy_seek:
            if active_seek_entry is not None and not active_seek_reacquired:
                raise RuntimeError("D-014 opened a second SEEK episode")
            low_energy_seek_entries += 1
            active_seek_entry = transitions
            active_seek_contact_at_entry = current.charging_contact
            active_seek_reacquired = False
            cycle_waiting_for_reacquisition = (
                cycle_open and cycle_has_exit and not current.charging_contact
            )

        if (
            active_seek_entry is not None
            and not active_seek_contact_at_entry
            and telemetry.charging_contact_after
            and not active_seek_reacquired
        ):
            active_seek_reacquired = True
            successful_reacquisitions += 1
            if cycle_waiting_for_reacquisition:
                completed_cycles += 1
                cycle_open = False
                cycle_has_exit = False
                cycle_waiting_for_reacquisition = False

        if active_seek_reacquired:
            active_seek_entry = None
            active_seek_reacquired = False

    if active_seek_entry is not None:
        if terminated and not truncated:
            demonstrated_failed_seek_episodes = 1
            horizon_censored_seek_episodes = 0
        elif truncated:
            demonstrated_failed_seek_episodes = 0
            horizon_censored_seek_episodes = 1
        else:
            raise RuntimeError("D-014 ended with an unresolved SEEK episode")
    else:
        demonstrated_failed_seek_episodes = 0
        horizon_censored_seek_episodes = 0

    final = environment.last_transition
    if final is None:
        raise RuntimeError("D-014 run ended without final telemetry")
    return {
        "seed": seed,
        "transitions": transitions,
        "terminated": terminated,
        "truncated": truncated,
        "termination_reason": _termination_reason(
            terminated=terminated,
            truncated=truncated,
            energy=final.energy_termination,
            thermal=final.thermal_termination,
        ),
        "energy_termination": final.energy_termination,
        "thermal_termination": final.thermal_termination,
        "minimum_normalized_energy": minimum_energy,
        "final_normalized_energy": final_energy,
        "maximum_thermal_state": maximum_thermal,
        "final_thermal_state": final_thermal,
        "action_counts": action_counts,
        "mode_occupancy": mode_occupancy,
        "mode_entry_counts": mode_entry_counts,
        "charger_departure_events": departure_events,
        "departure_trigger_counts": trigger_counts,
        "successful_physical_charger_exits": charger_exits,
        "away_entries": away_entries,
        "low_energy_seek_entries": low_energy_seek_entries,
        "successful_charging_contact_reacquisitions": successful_reacquisitions,
        "completed_autonomous_regulation_cycles": completed_cycles,
        "demonstrated_failed_seek_episodes": demonstrated_failed_seek_episodes,
        "horizon_censored_seek_episodes": horizon_censored_seek_episodes,
        "evaluator_only": {
            "seeded_heading": seeded_heading,
            "post_contact_setup": {
                "body_position": [0.5, 0.5],
                "station_position": [0.5, 0.5],
                "seeded_heading_preserved": True,
            },
            "departure_event_context_is_evaluator_only": True,
            "passed_to_controller": False,
        },
    }


def _validate_executed_commit_sha(value: str | None) -> str | None:
    if value is None:
        return None
    if re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise ValueError("executed_commit_sha must be a 40-character lowercase SHA")
    return value


def run_d014_probe(
    seeds: Sequence[int] = D014_DEFAULT_DEVELOPMENT_SEEDS,
    *,
    horizon: int = D014_HORIZON,
    executed_commit_sha: str | None = None,
) -> dict[str, object]:
    """Run one uninterrupted D-014 lifetime per declared seed."""
    development_seeds = _validate_d014_development_seeds(seeds)
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon <= 0:
        raise ValueError("horizon must be a positive integer")
    executed_sha = _validate_executed_commit_sha(executed_commit_sha)
    return {
        "schema_version": 1,
        "experiment": "D-014",
        "title": "Full-charge-or-thermal departure scaffold correction",
        "authoritative_base_sha": D014_AUTHORITATIVE_BASE_SHA,
        "executed_commit_sha": executed_sha,
        "development_seeds": list(development_seeds),
        "horizon": horizon,
        "lifetime": "one uninterrupted lifetime per seed",
        "seed_policy": {
            "canonical_validator": "validate_exp003_development_seeds",
            "exact_declared_seeds": list(D014_DEFAULT_DEVELOPMENT_SEEDS),
            "formal_reservation_guard_preserved": True,
        },
        "programmed": {
            "controller": "D014Controller",
            "inherits": "D011Controller",
            "full_energy_threshold": D014_FULL_ENERGY_THRESHOLD,
            "hot_depart_threshold": HOT_DEPART_THRESHOLD,
            "low_energy_seek_threshold": EXP003_B50_ENTER_SEEK_THRESHOLD,
            "departure_rule": "full normalized energy OR hot thermal, whichever first",
            "d011_remainder_unchanged": True,
            "ecology_unchanged": True,
            "model_guided_action": False,
            "learning": False,
            "no_resets_within_lifetime": True,
        },
        "organism_visible": {
            "observation_type": "D011Observation",
            "observation_fields": [
                "energy",
                "beacon.left",
                "beacon.forward",
                "beacon.right",
                "charging_contact",
                "thermal",
            ],
            "controller_departure_inputs": [
                "energy",
                "charging_contact",
                "thermal",
            ],
            "learned": "none",
        },
        "learned": {"status": "none", "learner_prediction_read": False},
        "evaluator_only": {
            "fields": [
                "run summaries",
                "departure event summaries",
                "termination/censoring classifications",
            ],
            "departure_event_context_passed_to_controller": False,
        },
        "organism_boundary": {"reward": 0.0, "info": {}},
        "results": [_run_seed(seed, horizon=horizon) for seed in development_seeds],
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the D-014 full-charge-or-thermal departure scaffold."
    )
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=list(D014_DEFAULT_DEVELOPMENT_SEEDS),
        help="Predeclared D-014 development seeds only.",
    )
    parser.add_argument("--horizon", type=int, default=D014_HORIZON)
    parser.add_argument("--executed-commit-sha")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    """Run D-014 and print or write its machine-readable result."""
    args = _parse_args()
    payload = json.dumps(
        run_d014_probe(
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
        print(f"D-014 result written to {args.output}")


if __name__ == "__main__":
    main()
