"""D-011 fixed non-learning thermal-beacon reacquisition baseline.

This module composes the already-authorized D-002 thermal/energy ecology with
the existing EXP-003 directional beacon and charging-contact interface.  The
controller is deliberately fixed and does not import or consult D-008.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Final, Sequence

import numpy as np

from .d002 import D002_UPPER_THERMAL_FAILURE_BOUNDARY, D002ThermalStationEnv
from .d003 import HOT_DEPART_THRESHOLD
from .env import Action
from .exp001 import ExternalObservation, StochasticPersistentExplorer
from .exp003 import (
    EXP003_B50_ENTER_SEEK_THRESHOLD,
    EXP003_CHARGING_RADIUS,
    EXP003_HORIZON,
    BeaconObservation,
    EXP003StationConfig,
    seek_beacon_action,
)
from .exp003_seed_policy import validate_exp003_development_seeds

D011_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = (18141, 18142, 18143)
D011_AUTHORITATIVE_BASE_SHA: Final[str] = (
    "e4e5dbf776bbd9bb72420b8bd60d3e8ba1468b58"
)


class D011Mode(Enum):
    """Minimal controller phases for one uninterrupted organism lifetime."""

    CHARGE = "CHARGE"
    DEPART = "DEPART"
    AWAY = "AWAY"
    SEEK = "SEEK"


@dataclass(frozen=True, slots=True)
class D011Observation:
    """The complete D-011 organism-visible observation.

    ``BeaconObservation`` contains exactly the L/F/R beacon values and the
    physical charging-contact bit.  No evaluator geometry or telemetry is
    represented by this type.
    """

    energy: float
    beacon: BeaconObservation
    thermal: float

    def __post_init__(self) -> None:
        _validate_normalized("energy", self.energy)
        _validate_normalized("thermal", self.thermal)
        if not isinstance(self.beacon, BeaconObservation):
            raise ValueError("beacon must be a BeaconObservation")

    @property
    def charging_contact(self) -> bool:
        """Return the controller-visible physical contact channel."""
        return self.beacon.charging_contact


class D011Controller:
    """Fixed four-phase controller with no learned or model-guided action."""

    def __init__(self, policy_rng: np.random.Generator) -> None:
        self.explorer = StochasticPersistentExplorer(policy_rng)
        self.mode = D011Mode.CHARGE

    def reset(self) -> None:
        """Reset only this controller's own lifetime state."""
        self.mode = D011Mode.CHARGE
        self.explorer.begin_segment()

    def act(self, observation: D011Observation) -> Action:
        """Select one action from D-011-visible values and own phase state."""
        if not isinstance(observation, D011Observation):
            raise ValueError("observation must be a D011Observation")

        if self.mode is D011Mode.CHARGE:
            if not observation.charging_contact:
                self.mode = D011Mode.SEEK
            elif observation.thermal < HOT_DEPART_THRESHOLD:
                return Action.WAIT
            else:
                self.mode = D011Mode.DEPART
                return Action.MOVE_FORWARD

        if self.mode is D011Mode.DEPART:
            if observation.charging_contact:
                return Action.MOVE_FORWARD
            self.mode = D011Mode.AWAY

        if self.mode is D011Mode.AWAY:
            if observation.energy < EXP003_B50_ENTER_SEEK_THRESHOLD:
                self.mode = D011Mode.SEEK
            else:
                # An accidental contact is not a docking transition.  The
                # persistent explorer continues its declared run/turn policy.
                return self._explore_action(observation.beacon)

        if self.mode is D011Mode.SEEK:
            if observation.charging_contact:
                self.mode = D011Mode.CHARGE
                return Action.WAIT
            return seek_beacon_action(observation.beacon)

        raise RuntimeError(f"unsupported D-011 controller mode: {self.mode}")

    def _explore_action(self, beacon: BeaconObservation) -> Action:
        """Reuse the historical persistent-exploration primitive exactly."""
        return self.explorer.act(
            ExternalObservation(beacon.left, beacon.forward, beacon.right)
        )


def _controller_observation(observation: np.ndarray) -> D011Observation:
    """Project only the six current D-002 channels into D-011."""
    if observation.shape != (6,):
        raise ValueError("D-002 observation must contain six values")
    contact_signal = float(observation[4])
    if contact_signal not in (0.0, 1.0):
        raise ValueError("D-002 charging contact channel must be binary")
    return D011Observation(
        energy=float(observation[0]),
        beacon=BeaconObservation(
            left=float(observation[1]),
            forward=float(observation[2]),
            right=float(observation[3]),
            charging_contact=bool(contact_signal),
        ),
        thermal=float(observation[5]),
    )


def _prepare_post_contact_setup(
    environment: D002ThermalStationEnv,
    *,
    position: tuple[float, float] = (0.5, 0.5),
    station_center: tuple[float, float] = (0.5, 0.5),
) -> tuple[float, np.ndarray]:
    """Place body/station on contact while preserving the seeded heading."""
    body = environment.body
    if body is None or environment.station_center is None:
        raise RuntimeError("D-002 environment must be reset before setup")
    seeded_heading = body.heading
    observation = environment.evaluator_set_geometry_and_observe(
        body_position=position,
        station_center=station_center,
    )
    return seeded_heading, observation


def _mode_counts() -> dict[str, int]:
    return {mode.name: 0 for mode in D011Mode}


def _distance(position: tuple[float, float], station: tuple[float, float]) -> float:
    return math.dist(position, station)


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


def _validate_d011_development_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    """Reject formal reservations and seeds outside this D-011 declaration."""
    validated = validate_exp003_development_seeds(seeds)
    unexpected = tuple(
        seed for seed in validated if seed not in D011_DEFAULT_DEVELOPMENT_SEEDS
    )
    if unexpected:
        raise ValueError(
            "D-011 may execute only predeclared development seeds "
            f"{D011_DEFAULT_DEVELOPMENT_SEEDS}; got {unexpected}"
        )
    return validated


def _run_seed(seed: int, *, horizon: int) -> dict[str, object]:
    config = EXP003StationConfig(episode_horizon=horizon)
    environment = D002ThermalStationEnv(config=config)
    observation, info = environment.reset(seed=seed)
    if info != {}:
        raise RuntimeError("D-002 reset crossed the information boundary")
    seeded_heading, observation = _prepare_post_contact_setup(environment)
    if environment.base_env.random_streams is None:
        raise RuntimeError("D-002 policy RNG is unavailable after reset")

    controller = D011Controller(environment.base_env.random_streams.policy)
    controller.reset()
    mode_occupancy = _mode_counts()
    mode_entry_counts = _mode_counts()
    mode_entry_counts[controller.mode.name] = 1
    action_counts = {action.name: 0 for action in Action}
    transitions = 0
    minimum_energy = config.initial_energy
    maximum_energy = config.initial_energy
    minimum_normalized_energy = float(observation[0])
    maximum_normalized_energy = float(observation[0])
    minimum_thermal = float(observation[5])
    maximum_thermal = float(observation[5])
    thermal_departures = 0
    charger_exits = 0
    away_entries = 0
    low_energy_seek_entries = 0
    successful_reacquisitions = 0
    accidental_away_contacts = 0
    seek_distance_trajectory: list[dict[str, object]] = []
    seek_episodes: list[dict[str, object]] = []
    active_seek_episode: dict[str, object] | None = None
    completed_cycles = 0
    cycle_open = False
    cycle_has_exit = False
    cycle_waiting_for_reacquisition = False

    terminated = False
    truncated = False
    while not (terminated or truncated):
        current = _controller_observation(observation)
        mode_before = controller.mode
        mode_occupancy[mode_before.name] += 1
        action = controller.act(current)
        mode_after = controller.mode
        action_counts[action.name] += 1

        if mode_after is not mode_before:
            mode_entry_counts[mode_after.name] += 1
        if mode_before is D011Mode.CHARGE and mode_after is D011Mode.DEPART:
            thermal_departures += 1
            cycle_open = True
            cycle_has_exit = False
            cycle_waiting_for_reacquisition = False
        if mode_before is D011Mode.DEPART and mode_after is D011Mode.AWAY:
            away_entries += 1

        # Evaluator-only geometry is read after action selection and after the
        # physical transition.  It is never passed back to the controller.
        observation, reward, terminated, truncated, info = environment.step(action)
        if reward != 0.0 or info != {}:
            raise RuntimeError("D-002 reward or info crossed the boundary")
        telemetry = environment.last_transition
        body = environment.body
        station = environment.station_center
        if telemetry is None or body is None or station is None:
            raise RuntimeError("D-011 transition telemetry is unavailable")
        transitions += 1

        minimum_energy = min(minimum_energy, telemetry.energy_after)
        maximum_energy = max(maximum_energy, telemetry.energy_after)
        minimum_normalized_energy = min(
            minimum_normalized_energy, float(observation[0])
        )
        maximum_normalized_energy = max(
            maximum_normalized_energy, float(observation[0])
        )
        minimum_thermal = min(minimum_thermal, float(observation[5]))
        maximum_thermal = max(maximum_thermal, float(observation[5]))
        position_after = body.position
        true_distance = _distance(position_after, station)

        if (
            telemetry.charging_contact_before
            and not telemetry.charging_contact_after
        ):
            charger_exits += 1
            cycle_has_exit = True
        if (
            mode_before is D011Mode.AWAY
            and mode_after is D011Mode.AWAY
            and telemetry.charging_contact_after
        ):
            accidental_away_contacts += 1

        entered_low_energy_seek = (
            mode_before is D011Mode.AWAY
            and mode_after is D011Mode.SEEK
            and current.energy < EXP003_B50_ENTER_SEEK_THRESHOLD
        )
        if entered_low_energy_seek:
            low_energy_seek_entries += 1
            if active_seek_episode is not None:
                active_seek_episode["failed"] = True
            active_seek_episode = {
                "entry_transition": transitions,
                "energy_at_entry": current.energy,
                "physical_energy_at_entry": telemetry.energy_before,
                "thermal_at_entry": current.thermal,
                "contact_at_entry": current.charging_contact,
                "distance_at_entry": true_distance,
                "reacquisition_transition": None,
                "transitions_to_reacquisition": None,
                "energy_at_reacquisition": None,
                "physical_energy_at_reacquisition": None,
                "thermal_at_reacquisition": None,
                "failed": False,
            }
            seek_episodes.append(active_seek_episode)
            cycle_waiting_for_reacquisition = (
                cycle_open and cycle_has_exit and not current.charging_contact
            )

        if mode_before is D011Mode.SEEK or mode_after is D011Mode.SEEK:
            seek_distance_trajectory.append(
                {
                    "transition": transitions,
                    "mode_before": mode_before.name,
                    "mode_after": mode_after.name,
                    "position": [position_after[0], position_after[1]],
                    "station_position": [station[0], station[1]],
                    "true_distance": true_distance,
                    "heading": body.heading,
                }
            )

        if (
            active_seek_episode is not None
            and not bool(active_seek_episode["contact_at_entry"])
            and telemetry.charging_contact_after
            and active_seek_episode["reacquisition_transition"] is None
        ):
            active_seek_episode["reacquisition_transition"] = transitions
            entry_transition = active_seek_episode["entry_transition"]
            if not isinstance(entry_transition, int):
                raise RuntimeError("SEEK entry transition is not an integer")
            active_seek_episode["transitions_to_reacquisition"] = (
                transitions - entry_transition
            )
            active_seek_episode["energy_at_reacquisition"] = float(observation[0])
            active_seek_episode["physical_energy_at_reacquisition"] = (
                telemetry.energy_after
            )
            active_seek_episode["thermal_at_reacquisition"] = telemetry.thermal_after
            active_seek_episode["failed"] = False
            successful_reacquisitions += 1
            if cycle_waiting_for_reacquisition:
                completed_cycles += 1
                cycle_open = False
                cycle_has_exit = False
                cycle_waiting_for_reacquisition = False
            active_seek_episode = None

        if terminated or truncated:
            break

    if (
        active_seek_episode is not None
        and active_seek_episode["reacquisition_transition"] is None
    ):
        active_seek_episode["failed"] = True

    final = environment.last_transition
    if final is None or environment.body is None or environment.station_center is None:
        raise RuntimeError("D-011 run ended without final telemetry")
    failed_seek_episodes = sum(
        1 for episode in seek_episodes if bool(episode["failed"])
    )
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
        "minimum_energy": minimum_energy,
        "maximum_energy": maximum_energy,
        "final_energy": environment.body.energy,
        "minimum_normalized_energy": minimum_normalized_energy,
        "maximum_normalized_energy": maximum_normalized_energy,
        "final_normalized_energy": float(observation[0]),
        "minimum_thermal_state": minimum_thermal,
        "maximum_thermal_state": maximum_thermal,
        "final_thermal_state": environment.thermal_state,
        "action_counts": action_counts,
        "mode_occupancy": mode_occupancy,
        "mode_entry_counts": mode_entry_counts,
        "thermal_triggered_departures": thermal_departures,
        "successful_physical_charger_exits": charger_exits,
        "away_entries": away_entries,
        "low_energy_seek_entries": low_energy_seek_entries,
        "successful_charging_contact_reacquisitions": successful_reacquisitions,
        "completed_autonomous_regulation_cycles": completed_cycles,
        "seek_episodes": seek_episodes,
        "failed_seek_episodes": failed_seek_episodes,
        "accidental_away_contacts": accidental_away_contacts,
        "evaluator_only_navigation": {
            "station_position": [
                environment.station_center[0],
                environment.station_center[1],
            ],
            "seeded_heading": seeded_heading,
            "distance_at_seek_entry": [
                episode["distance_at_entry"] for episode in seek_episodes
            ],
            "seek_distance_trajectory": seek_distance_trajectory,
            "passed_to_controller": False,
        },
        "initial_setup": {
            "body_position": [0.5, 0.5],
            "station_position": [0.5, 0.5],
            "seeded_heading_preserved": True,
        },
    }


def run_d011_probe(
    seeds: Sequence[int] = D011_DEFAULT_DEVELOPMENT_SEEDS,
    *,
    horizon: int = EXP003_HORIZON,
) -> dict[str, object]:
    """Run D-011 once per legal seed as one continuous lifetime."""
    development_seeds = _validate_d011_development_seeds(seeds)
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon <= 0:
        raise ValueError("horizon must be a positive integer")
    return {
        "schema_version": 1,
        "experiment": "D-011",
        "title": "Fixed non-learning thermal-beacon autonomous reacquisition",
        "authoritative_base_sha": D011_AUTHORITATIVE_BASE_SHA,
        "executed_commit_sha": None,
        "development_seeds": list(development_seeds),
        "horizon": horizon,
        "lifetime": "one uninterrupted lifetime per seed",
        "programmed": {
            "controller": "D011Controller",
            "modes": [mode.name for mode in D011Mode],
            "hot_depart_threshold": HOT_DEPART_THRESHOLD,
            "low_energy_seek_threshold": EXP003_B50_ENTER_SEEK_THRESHOLD,
            "beacon_navigation": "existing seek_beacon_action",
            "exploration": "existing StochasticPersistentExplorer",
            "policy_rng": "organism-owned policy stream derived from seed",
            "model_guided_action": False,
            "reward_driven": False,
        },
        "organism_visible": {
            "observation_fields": [
                "energy",
                "beacon.left",
                "beacon.forward",
                "beacon.right",
                "charging_contact",
                "thermal",
            ],
            "own_phase_state": True,
            "own_policy_rng_state": True,
            "no_coordinates_or_evaluator_telemetry": True,
        },
        "learned": {
            "status": "none",
            "learner_prediction_read": False,
        },
        "evaluator_only": {
            "fields": [
                "body_position",
                "station_position",
                "true_distance",
                "heading",
                "distance_at_seek_entry",
                "seek_distance_trajectory",
                "mode/cycle summaries",
            ],
            "passed_to_controller": False,
        },
        "cycle_definition": (
            "a thermal-triggered CHARGE departure, a physical off-contact "
            "interval, a later low-energy SEEK entry while off-contact, and "
            "a subsequent post-action physical charging-contact reacquisition; "
            "beacon strength alone never counts"
        ),
        "seek_latency_definition": (
            "transitions_to_reacquisition is reacquisition transition index "
            "minus low-energy SEEK entry transition index; immediate entry "
            "action contact is latency 0"
        ),
        "ecology": {
            "environment": "D002ThermalStationEnv",
            "charging_radius": EXP003_CHARGING_RADIUS,
            "thermal_failure_boundary": D002_UPPER_THERMAL_FAILURE_BOUNDARY,
            "post_contact_setup": (
                "body and station at (0.5, 0.5), seeded heading preserved"
            ),
        },
        "organism_boundary": {"reward": 0.0, "info": {}},
        "results": [
            _run_seed(seed, horizon=horizon) for seed in development_seeds
        ],
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the D-011 fixed thermal-beacon reacquisition baseline."
    )
    parser.add_argument(
        "--seeds", type=int, nargs="+", default=list(D011_DEFAULT_DEVELOPMENT_SEEDS)
    )
    parser.add_argument("--horizon", type=int, default=EXP003_HORIZON)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    """Run D-011 and print or write its machine-readable result."""
    args = _parse_args()
    payload = json.dumps(
        run_d011_probe(tuple(args.seeds), horizon=args.horizon),
        indent=2,
        sort_keys=True,
    )
    if args.output is None:
        print(payload)
    else:
        args.output.write_text(payload + "\n", encoding="utf-8")
        print(f"D-011 result written to {args.output}")


def _validate_normalized(name: str, value: float) -> None:
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be finite and between 0.0 and 1.0")


if __name__ == "__main__":
    main()
