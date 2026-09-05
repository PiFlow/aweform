"""D-025 bounded stochastic SEEK de-trapping development probe.

This module inherits D-024's causal finite-body environment and exact initial
state.  It changes only false-contact SEEK arbitration: the historical greedy
beacon action remains the default, while one in eight decisions delegates to
the existing :class:`StochasticPersistentExplorer` using the existing policy
RNG.  All geometry, action counterfactuals, and RNG diagnostics are
evaluator-only.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Final, Sequence, cast

import numpy as np

from . import d021, d024
from .d020 import D020PhysicalConfig, D020TransitionTelemetry
from .env import Action
from .exp001 import ExternalObservation, StochasticPersistentExplorer
from .exp003 import (
    EXP003_B50_ENTER_SEEK_THRESHOLD,
    BeaconObservation,
    seek_beacon_action,
)
from .exp003_seed_policy import validate_exp003_development_seeds
from .rng import RandomStreams

D025_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = (18365, 18366, 18367)
D025_CANONICAL_VISUALIZATION_SEED: Final[int] = D025_DEFAULT_DEVELOPMENT_SEEDS[0]
D025_HORIZON: Final[int] = 70_000
D025_SEEK_DELEGATION_PROBABILITY: Final[float] = 1.0 / 8.0
D025_AUTHORITATIVE_BASE_SHA: Final[str] = (
    "d661029e2c9be63274cb9109a7bb6d685bc29751"
)
D024_COMPARATOR_IMPLEMENTATION_SHA: Final[str] = (
    "2b71596683b444c1fa841e1bb56f0611cc23232d"
)

D025Mode = d021.D021Mode
D025Observation = d021.D021Observation
D025TransitionTrace = d021.D021TransitionTrace


@dataclass(frozen=True, slots=True)
class D025Arbitration:
    """One evaluator-only false-contact SEEK arbitration decision."""

    greedy_action: Action
    actual_action: Action
    delegation_draw: float
    delegated: bool

    @property
    def effective_perturbation(self) -> bool:
        return self.actual_action is not self.greedy_action


class D025Controller:
    """D-021 controller with only the authorized SEEK arbitration change."""

    seek_delegation_probability = D025_SEEK_DELEGATION_PROBABILITY

    def __init__(self, policy_rng: np.random.Generator) -> None:
        self.policy_rng = policy_rng
        self.explorer = StochasticPersistentExplorer(policy_rng)
        self.mode = D025Mode.CHARGE
        self.seek_segment_starts = 0
        self.last_arbitration: D025Arbitration | None = None

    def reset(self) -> None:
        """Reset controller state for a new uninterrupted lifetime."""
        self.mode = D025Mode.CHARGE
        self.seek_segment_starts = 0
        self.last_arbitration = None
        self.explorer.begin_segment()

    def act(self, observation: D025Observation) -> Action:
        """Select an action from exactly D-021's six-channel observation."""
        if not isinstance(observation, D025Observation):
            raise ValueError("observation must be a D011Observation")
        mode_before = self.mode
        self.last_arbitration = None

        if self.mode is D025Mode.CHARGE:
            if not observation.charging_contact:
                self.mode = D025Mode.SEEK
            elif observation.energy >= d021.D021_FULL_ENERGY_THRESHOLD:
                self.mode = D025Mode.DEPART
                return Action.MOVE_FORWARD
            else:
                return Action.WAIT

        if self.mode is D025Mode.DEPART:
            if observation.charging_contact:
                return Action.MOVE_FORWARD
            self.mode = D025Mode.AWAY

        if self.mode is D025Mode.AWAY:
            if observation.energy < EXP003_B50_ENTER_SEEK_THRESHOLD:
                self.mode = D025Mode.SEEK
            else:
                return self._explore_action(observation.beacon)

        if self.mode is D025Mode.SEEK:
            if observation.charging_contact:
                self.mode = D025Mode.CHARGE
                return Action.WAIT
            if mode_before is not D025Mode.SEEK:
                self.explorer.begin_segment()
                self.seek_segment_starts += 1
            greedy_action = seek_beacon_action(observation.beacon)
            delegation_draw = float(self.policy_rng.random())
            delegated = delegation_draw < self.seek_delegation_probability
            if delegated:
                actual_action = self.explorer.act(
                    ExternalObservation(
                        observation.beacon.left,
                        observation.beacon.forward,
                        observation.beacon.right,
                    )
                )
            else:
                actual_action = greedy_action
            self.last_arbitration = D025Arbitration(
                greedy_action=greedy_action,
                actual_action=actual_action,
                delegation_draw=delegation_draw,
                delegated=delegated,
            )
            return actual_action

        raise RuntimeError(f"unsupported D-025 controller mode: {self.mode}")

    def _explore_action(self, beacon: BeaconObservation) -> Action:
        return self.explorer.act(
            ExternalObservation(beacon.left, beacon.forward, beacon.right)
        )


class D025Env(d024.D024Env):
    """D-024 environment alias documenting unchanged physical semantics."""


def _validate_d025_development_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    """Apply the canonical reservation guard and exact D-025 seed guard."""
    validated = validate_exp003_development_seeds(seeds)
    if validated != D025_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-025 requires exactly the frozen development seeds "
            f"{D025_DEFAULT_DEVELOPMENT_SEEDS}; got {validated}"
        )
    return validated


def _validate_d025_seed(seed: int) -> None:
    validated = validate_exp003_development_seeds((seed,))
    if validated[0] not in D025_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-025 may execute only predeclared development seeds "
            f"{D025_DEFAULT_DEVELOPMENT_SEEDS}; got {validated}"
        )


def _validate_executed_commit_sha(value: str | None) -> str | None:
    if value is None:
        return None
    if re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise ValueError("executed_commit_sha must be a 40-character lowercase SHA")
    return value


def _controller_observation(observation: np.ndarray) -> D025Observation:
    """Use the unchanged D-021 projection and reject boundary drift."""
    return d021._controller_observation(observation)


def _mode_counts() -> dict[str, int]:
    return {mode.name: 0 for mode in D025Mode}


def _termination_reason(
    *, terminated: bool, truncated: bool, reason: object | None
) -> str:
    if terminated and getattr(reason, "value", None) == "energy_depletion":
        return "energy_depletion"
    if (
        terminated
        and getattr(reason, "value", None) == "protective_thermal_shutdown"
    ):
        return "protective_thermal_shutdown"
    if (
        terminated
        and getattr(reason, "value", None) == "emergency_hard_thermal_shutdown"
    ):
        return "emergency_hard_thermal_shutdown"
    if truncated:
        return "horizon_truncation"
    return "incomplete"


def _new_seek_episode(
    *,
    transition_index: int,
    observation: D025Observation,
    action: Action,
    position: tuple[float, float],
    heading: float,
    station: tuple[float, float],
    legacy_contact: bool,
) -> dict[str, object]:
    metrics = d024._geometry_metrics(position, heading, station)
    return {
        "seek_entry_transition": transition_index,
        "entry_action": action.name,
        "energy_at_entry": observation.energy,
        "temperature_normalized_at_entry": observation.thermal,
        "charging_contact_at_entry": observation.charging_contact,
        "legacy_circular_contact_at_entry": legacy_contact,
        "evaluator_distance_at_entry": math.dist(position, station),
        "minimum_rear_plus_pair_error_during_seek": metrics["rear_plus_pair_error"],
        "minimum_rear_minus_pair_error_during_seek": metrics["rear_minus_pair_error"],
        "minimum_max_pair_error_during_seek": metrics["max_pair_error"],
        "minimum_max_pair_error_during_seek_record": d024._pair_error_record(
            metrics,
            transition_index=transition_index,
            position=position,
            heading=heading,
        ),
        "one_pair_only_tolerance_events": 0,
        "outcome": "unresolved",
        "reacquisition_transition": None,
        "transitions_since_seek_entry": None,
        "energy_at_reacquisition": None,
        "temperature_normalized_at_reacquisition": None,
        "evaluator_distance_at_reacquisition": None,
        "reacquisition_action": None,
    }


def _update_seek_geometry(
    episode: dict[str, object],
    *,
    position: tuple[float, float],
    heading: float,
    station: tuple[float, float],
    transition_index: int,
) -> None:
    d024._update_seek_geometry(
        episode,
        position=position,
        heading=heading,
        station=station,
        transition_index=transition_index,
    )


def _arbitration_summary(
    decisions: Sequence[dict[str, object]],
) -> dict[str, object]:
    greedy_counts = {action.name: 0 for action in Action}
    actual_counts = {action.name: 0 for action in Action}
    delegated_counts = {action.name: 0 for action in Action}
    pair_counts = {
        f"{greedy.name}->{actual.name}": 0
        for greedy in Action
        for actual in Action
    }
    for decision in decisions:
        greedy = str(decision["greedy_beacon_action"])
        actual = str(decision["actual_action"])
        greedy_counts[greedy] += 1
        actual_counts[actual] += 1
        pair_counts[f"{greedy}->{actual}"] += 1
        if bool(decision["delegated"]):
            delegated_counts[actual] += 1
    return {
        "false_contact_seek_decisions": len(decisions),
        "stochastic_delegation_decisions": sum(
            int(bool(decision["delegated"])) for decision in decisions
        ),
        "delegated_actions_by_action_type": delegated_counts,
        "effective_perturbations": sum(
            int(bool(decision["effective_perturbation"])) for decision in decisions
        ),
        "greedy_beacon_action_counts": greedy_counts,
        "actual_executed_action_counts": actual_counts,
        "greedy_to_actual_action_counts": pair_counts,
        "decision_records": list(decisions),
    }


def _make_trace(
    *,
    transition_index: int,
    mode_before: D025Mode,
    mode_after: D025Mode,
    action: Action,
    current: D025Observation,
    observation: np.ndarray,
    telemetry: D020TransitionTelemetry,
    reward: float,
    info: dict[str, object],
) -> D025TransitionTrace:
    return D025TransitionTrace(
        transition_index=transition_index,
        mode_before=mode_before,
        mode_after=mode_after,
        action=action,
        observation_before=(
            current.energy,
            current.beacon.left,
            current.beacon.forward,
            current.beacon.right,
            float(current.charging_contact),
            current.thermal,
        ),
        observation=tuple(float(value) for value in observation),
        telemetry=telemetry,
        reward=reward,
        info=info,
    )


def _validate_pre_seek_prefix(
    seed: int,
    prefix: Sequence[D025TransitionTrace],
    first_seek_decision: int | None,
    horizon: int,
    comparator_seed_validator: Callable[[int], None] | None = None,
) -> dict[str, object]:
    """Compare D-025 with a deterministic D-024 replay before SEEK."""
    if horizon == D025_HORIZON:
        comparator_trace = d024.run_d024_lifetime_trace(
            seed,
            horizon=D025_HORIZON,
            seed_validator=comparator_seed_validator,
        )
    else:
        comparator_trace_list: list[D025TransitionTrace] = []
        d024._run_d024_seed(
            seed,
            horizon=horizon,
            trace=comparator_trace_list,
            seed_validator=comparator_seed_validator,
        )
        comparator_trace = tuple(comparator_trace_list)
    expected_count = (
        first_seek_decision - 1 if first_seek_decision is not None else len(prefix)
    )
    if len(prefix) != expected_count:
        raise RuntimeError(
            "D-025 prefix capture did not reach the transition before first SEEK"
        )
    if len(comparator_trace) < expected_count:
        raise RuntimeError("D-024 comparator ended before the D-025 prefix")
    for actual, expected in zip(prefix, comparator_trace[:expected_count], strict=True):
        if actual != expected:
            raise RuntimeError(
                "D-025 pre-SEEK prefix diverged from the D-024 comparator at "
                f"transition {actual.transition_index}"
            )
    return {
        "validated": True,
        "comparator": "D-024 deterministic replay",
        "comparator_implementation_probe_sha": D024_COMPARATOR_IMPLEMENTATION_SHA,
        "compared_through_completed_away_transition": expected_count,
        "first_seek_decision_transition": first_seek_decision,
        "policy_rng_provenance": (
            "RandomStreams.from_seed(seed).policy; continuous from lifetime start"
        ),
    }


def _run_d025_seed(
    seed: int,
    *,
    horizon: int = D025_HORIZON,
    trace: list[D025TransitionTrace] | None = None,
    seed_validator: Callable[[int], None] | None = None,
    controller_factory: Callable[[np.random.Generator], D025Controller]
    | None = None,
    comparator_seed_validator: Callable[[int], None] | None = None,
) -> dict[str, object]:
    """Run one exact-pose, uninterrupted D-025 lifetime."""
    if seed_validator is None:
        _validate_d025_seed(seed)
    else:
        seed_validator(seed)
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon <= 0:
        raise ValueError("horizon must be a positive integer")

    config = D020PhysicalConfig()
    run_config = replace(config, episode_horizon=horizon)
    streams = RandomStreams.from_seed(seed)
    environment = D025Env(run_config)
    observation, info = environment.reset(
        options={
            "body_position": d024.D024_INITIAL_BODY_CENTER,
            "station_center": d024.D024_STATION_CENTER,
            "heading": d024.D024_INITIAL_HEADING,
            "battery_j": d024.D024_INITIAL_BATTERY_J,
            "body_temperature_c": d024.D024_INITIAL_TEMPERATURE_C,
            "charger_termination_latched": False,
        }
    )
    if info != {}:
        raise RuntimeError("D-025 reset crossed the information boundary")
    if environment.body is None or environment.station_center is None:
        raise RuntimeError("D-025 reset did not initialize evaluator geometry")
    if not environment.charging_contact:
        raise RuntimeError("D-024 exact initial pose is not in dual contact")

    if controller_factory is None:
        controller = D025Controller(streams.policy)
    else:
        controller = controller_factory(streams.policy)
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
    minimum_battery_j = d024.D024_INITIAL_BATTERY_J
    maximum_battery_j = d024.D024_INITIAL_BATTERY_J
    initial_temperature = float(observation[5])
    maximum_temperature = initial_temperature
    final_temperature = initial_temperature
    maximum_temperature_c = d024.D024_INITIAL_TEMPERATURE_C
    final_temperature_c = d024.D024_INITIAL_TEMPERATURE_C

    full_departures = 0
    initial_full_departures = 0
    initial_full_departure_transition: int | None = None
    first_dual_contact_loss_after_departure_transition: int | None = None
    post_recharge_redepartures = 0
    charger_exits = 0
    low_energy_seek_entries = 0
    physical_reacquisitions = 0
    dual_contact_entries = 0
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
    legacy_without_dual_transitions = 0
    legacy_without_dual_entries = 0
    legacy_without_dual_active = False
    legacy_without_dual_entry_records: list[dict[str, object]] = []
    seek_legacy_without_dual_transitions = 0
    seek_legacy_without_dual_entries = 0
    seek_legacy_without_dual_active = False
    seek_legacy_without_dual_entry_records: list[dict[str, object]] = []
    dual_entry_records: list[dict[str, object]] = []
    arbitration_decisions: list[dict[str, object]] = []
    first_effective_perturbation: dict[str, object] | None = None
    prefix_trace: list[D025TransitionTrace] = []
    first_seek_decision: int | None = None
    terminated = False
    truncated = False

    while not (terminated or truncated):
        if environment.body is None or environment.station_center is None:
            raise RuntimeError("D-025 evaluator geometry disappeared")
        current = _controller_observation(observation)
        mode_before = controller.mode
        mode_occupancy[mode_before.name] += 1
        action = controller.act(current)
        mode_after = controller.mode
        action_counts[action.name] += 1
        if mode_after is not mode_before:
            mode_entry_counts[mode_after.name] += 1

        transition_index = transitions + 1
        arbitration = controller.last_arbitration
        if arbitration is not None:
            if current.charging_contact or mode_after is not D025Mode.SEEK:
                raise RuntimeError(
                    "D-025 arbitration was used outside false-contact SEEK"
                )
            if first_seek_decision is None:
                first_seek_decision = transition_index
            decision = {
                "transition": transition_index,
                "greedy_beacon_action": arbitration.greedy_action.name,
                "actual_action": arbitration.actual_action.name,
                "delegation_draw": arbitration.delegation_draw,
                "delegated": arbitration.delegated,
                "effective_perturbation": arbitration.effective_perturbation,
            }
            arbitration_decisions.append(decision)

        if mode_before is D025Mode.CHARGE and mode_after is D025Mode.DEPART:
            if (
                not current.charging_contact
                or current.energy < d021.D021_FULL_ENERGY_THRESHOLD
            ):
                mode_event_inconsistencies.append(
                    "full_departure_without_full_contact"
                )
            full_departures += 1
            if recharge_ready_for_departure and cycle_stage == 5:
                post_recharge_redepartures += 1
                completed_cycles += 1
                recharge_ready_for_departure = False
                recharge_episode_active = False
                cycle_stage = 1
            elif cycle_stage == 0:
                initial_full_departures += 1
                initial_full_departure_transition = transition_index
                cycle_stage = 1
            else:
                mode_event_inconsistencies.append("unexpected_full_departure_stage")
        if mode_before is D025Mode.SEEK and mode_after is D025Mode.CHARGE:
            charge_entries += 1

        observation, reward, terminated, truncated, info = environment.step(action)
        if reward != 0.0 or info != {}:
            raise RuntimeError("D-025 reward or info crossed the boundary")
        telemetry = environment.last_transition
        if telemetry is None:
            raise RuntimeError("D-025 transition telemetry is unavailable")
        transitions += 1
        record = _make_trace(
            transition_index=transition_index,
            mode_before=mode_before,
            mode_after=mode_after,
            action=action,
            current=current,
            observation=observation,
            telemetry=telemetry,
            reward=reward,
            info=info,
        )
        if trace is not None:
            trace.append(record)
        if first_seek_decision is None:
            prefix_trace.append(record)

        if (
            first_effective_perturbation is None
            and arbitration is not None
            and arbitration.effective_perturbation
        ):
            pair_errors = d024.dual_contact_pair_errors(
                telemetry.position_after,
                telemetry.heading,
                telemetry.station_center,
            )
            first_effective_perturbation = {
                **arbitration_decisions[-1],
                "body_center": list(telemetry.position_after),
                "heading": telemetry.heading,
                "rear_plus_pair_error": pair_errors[0],
                "rear_minus_pair_error": pair_errors[1],
                "max_pair_error": max(pair_errors),
                "charging_contact_after": telemetry.charging_contact_after,
                "controller_mode_before_action": mode_before.name,
                "controller_mode_after_action": mode_after.name,
            }

        dual_after = telemetry.charging_contact_after
        legacy_after = d024.legacy_circular_contact(
            telemetry.position_after, telemetry.station_center, run_config
        )
        if not telemetry.charging_contact_before and dual_after:
            dual_contact_entries += 1
            pair_errors = d024.dual_contact_pair_errors(
                telemetry.position_after,
                telemetry.heading,
                telemetry.station_center,
            )
            dual_entry_records.append(
                {
                    "transition": transition_index,
                    "action": action.name,
                    "rear_plus_pair_error": pair_errors[0],
                    "rear_minus_pair_error": pair_errors[1],
                    "max_pair_error": max(pair_errors),
                    "legacy_circular_contact": legacy_after,
                    "controller_mode_before_action": mode_before.name,
                    "controller_mode_after_action": mode_after.name,
                    "controller_mode_at_entry": mode_after.name,
                }
            )
        if (
            first_dual_contact_loss_after_departure_transition is None
            and initial_full_departure_transition is not None
            and telemetry.charging_contact_before
            and not telemetry.charging_contact_after
        ):
            first_dual_contact_loss_after_departure_transition = transition_index
        if legacy_after and not dual_after:
            legacy_without_dual_transitions += 1
            if not legacy_without_dual_active:
                legacy_without_dual_entries += 1
                legacy_without_dual_entry_records.append(
                    {
                        "transition": transition_index,
                        "action": action.name,
                        "body_center": list(telemetry.position_after),
                        "heading": telemetry.heading,
                        "controller_mode_before_action": mode_before.name,
                        "controller_mode_after_action": mode_after.name,
                        "controller_mode_at_entry": mode_after.name,
                    }
                )
            legacy_without_dual_active = True
        else:
            legacy_without_dual_active = False

        if legacy_after and not dual_after and mode_after is D025Mode.SEEK:
            seek_legacy_without_dual_transitions += 1
            if not seek_legacy_without_dual_active:
                seek_legacy_without_dual_entries += 1
                seek_legacy_without_dual_entry_records.append(
                    {
                        "transition": transition_index,
                        "action": action.name,
                        "body_center": list(telemetry.position_after),
                        "heading": telemetry.heading,
                        "controller_mode_before_action": mode_before.name,
                        "controller_mode_after_action": mode_after.name,
                        "controller_mode_at_entry": mode_after.name,
                        "legacy_circular_contact": True,
                        "dual_contact": False,
                    }
                )
            seek_legacy_without_dual_active = True
        else:
            seek_legacy_without_dual_active = False

        entered_seek = (
            mode_before is D025Mode.AWAY
            and mode_after is D025Mode.SEEK
            and current.energy < EXP003_B50_ENTER_SEEK_THRESHOLD
        )
        if entered_seek:
            if active_seek is not None:
                mode_event_inconsistencies.append("overlapping_seek_episodes")
            active_seek = _new_seek_episode(
                transition_index=transition_index,
                observation=current,
                action=action,
                position=telemetry.position_after,
                heading=telemetry.heading,
                station=telemetry.station_center,
                legacy_contact=d024.legacy_circular_contact(
                    telemetry.position_before, telemetry.station_center, run_config
                ),
            )
            seek_episodes.append(active_seek)
            low_energy_seek_entries += 1
            if cycle_stage == 2 and not current.charging_contact:
                cycle_stage = 3
            elif cycle_stage != 3:
                mode_event_inconsistencies.append("seek_entry_outside_exit_stage")

        if (
            mode_before is D025Mode.AWAY
            and current.energy >= EXP003_B50_ENTER_SEEK_THRESHOLD
            and not telemetry.charging_contact_before
            and telemetry.charging_contact_after
        ):
            accidental_away_contacts += 1

        if active_seek is not None:
            _update_seek_geometry(
                active_seek,
                position=telemetry.position_after,
                heading=telemetry.heading,
                station=telemetry.station_center,
                transition_index=transition_index,
            )
            if bool(active_seek["charging_contact_at_entry"]):
                active_seek["outcome"] = "contact_already_true_at_entry"
                active_seek["transitions_since_seek_entry"] = (
                    transition_index - cast(int, active_seek["seek_entry_transition"])
                )
                active_seek = None
            elif (
                not telemetry.charging_contact_before
                and telemetry.charging_contact_after
            ):
                physical_reacquisitions += 1
                active_seek["outcome"] = "reacquired"
                active_seek["reacquisition_transition"] = transition_index
                active_seek["transitions_since_seek_entry"] = (
                    transition_index - cast(int, active_seek["seek_entry_transition"])
                )
                active_seek["energy_at_reacquisition"] = float(observation[0])
                active_seek["temperature_normalized_at_reacquisition"] = float(
                    observation[5]
                )
                active_seek["evaluator_distance_at_reacquisition"] = math.dist(
                    telemetry.position_after, telemetry.station_center
                )
                active_seek["reacquisition_action"] = action.name
                pair_errors = d024.dual_contact_pair_errors(
                    telemetry.position_after,
                    telemetry.heading,
                    telemetry.station_center,
                )
                active_seek["reacquisition_body_center"] = list(
                    telemetry.position_after
                )
                active_seek["reacquisition_heading"] = telemetry.heading
                active_seek["reacquisition_rear_plus_pair_error"] = pair_errors[0]
                active_seek["reacquisition_rear_minus_pair_error"] = pair_errors[1]
                active_seek["reacquisition_max_pair_error"] = max(pair_errors)
                recharge_episode_active = True
                if cycle_stage == 3:
                    cycle_stage = 4
                active_seek = None

        if telemetry.charging_contact_before and not telemetry.charging_contact_after:
            charger_exits += 1
            if cycle_stage == 1:
                cycle_stage = 2

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
                mode_event_inconsistencies.append(
                    "full_recharge_outside_reacquisition_stage"
                )

        final_energy = float(observation[0])
        minimum_energy = min(minimum_energy, final_energy)
        maximum_energy = max(maximum_energy, final_energy)
        final_temperature = float(observation[5])
        maximum_temperature = max(maximum_temperature, final_temperature)
        final_temperature_c = telemetry.body_temperature_after_c
        maximum_temperature_c = max(maximum_temperature_c, final_temperature_c)
        minimum_battery_j = min(minimum_battery_j, telemetry.battery_after_j)
        maximum_battery_j = max(maximum_battery_j, telemetry.battery_after_j)

    if active_seek is not None:
        if terminated:
            active_seek["outcome"] = "terminated_before_reacquisition"
        elif truncated:
            active_seek["outcome"] = "horizon_censored"
        else:
            mode_event_inconsistencies.append("unresolved_seek_without_termination")

    final_telemetry = environment.last_transition
    if final_telemetry is None:
        raise RuntimeError("D-025 run ended without final telemetry")
    unresolved_seek = int(active_seek is not None)
    failed_seek_episodes = sum(
        int(item["outcome"] == "terminated_before_reacquisition")
        for item in seek_episodes
    )
    horizon_censored_seek_episodes = sum(
        int(item["outcome"] == "horizon_censored") for item in seek_episodes
    )
    contact_already_true_at_entry = sum(
        int(item["outcome"] == "contact_already_true_at_entry")
        for item in seek_episodes
    )
    minimum_seek_max_pair_error = min(
        (
            cast(float, item["minimum_max_pair_error_during_seek"])
            for item in seek_episodes
        ),
        default=None,
    )
    if physical_reacquisitions:
        outcome = (
            "FULL_CYCLE"
            if full_recharge_events and post_recharge_redepartures
            else "SEEK_REACQUIRED"
        )
    elif truncated:
        outcome = "HORIZON_CENSORED"
    else:
        outcome = "FAILED_SEEK"
    prefix_validation = _validate_pre_seek_prefix(
        seed,
        prefix_trace,
        first_seek_decision,
        horizon,
        comparator_seed_validator=comparator_seed_validator,
    )
    arbitration_diagnostics = _arbitration_summary(arbitration_decisions)
    arbitration_diagnostics["first_effective_perturbation"] = (
        first_effective_perturbation
    )
    arbitration_diagnostics["policy_rng"] = (
        "RandomStreams.from_seed(seed).policy, continuous; no reseed or new stream"
    )
    return {
        "seed": seed,
        "outcome_classification": outcome,
        "initial_pose": {
            "station_center": list(d024.D024_STATION_CENTER),
            "body_center": list(d024.D024_INITIAL_BODY_CENTER),
            "heading": d024.D024_INITIAL_HEADING,
            "initial_dual_contact": True,
            "initial_battery_j": d024.D024_INITIAL_BATTERY_J,
            "initial_temperature_c": d024.D024_INITIAL_TEMPERATURE_C,
            "initial_latch": False,
            "initial_controller_mode": D025Mode.CHARGE.name,
        },
        "initial_dual_contact_valid": True,
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
            "start": d024.D024_INITIAL_BATTERY_J,
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
        "initial_full_departure_transition": initial_full_departure_transition,
        "first_dual_contact_loss_after_departure_transition": (
            first_dual_contact_loss_after_departure_transition
        ),
        "physical_charger_exits": charger_exits,
        "low_energy_seek_entries": low_energy_seek_entries,
        "physical_reacquisitions": physical_reacquisitions,
        "charge_entries": charge_entries,
        "full_recharge_events": full_recharge_events,
        "post_recharge_redepartures": post_recharge_redepartures,
        "completed_energy_regulation_cycles": completed_cycles,
        "accidental_away_contacts": accidental_away_contacts,
        "explorer_seek_segment_starts": controller.seek_segment_starts,
        "pre_seek_prefix_validation": prefix_validation,
        "seek_arbitration": arbitration_diagnostics,
        "seek_episodes": seek_episodes,
        "pair_error_diagnostics": {
            "dual_contact_entry_records": dual_entry_records,
            "minimum_max_pair_error_during_any_seek": minimum_seek_max_pair_error,
            "one_pair_only_tolerance_events": sum(
                cast(int, item["one_pair_only_tolerance_events"])
                for item in seek_episodes
            ),
        },
        "legacy_circular_contact_without_dual": {
            "transition_count": legacy_without_dual_transitions,
            "entry_count": legacy_without_dual_entries,
            "entry_records": legacy_without_dual_entry_records,
            "seek_transition_count": seek_legacy_without_dual_transitions,
            "seek_entry_count": seek_legacy_without_dual_entries,
            "seek_entry_records": seek_legacy_without_dual_entry_records,
        },
        "failure_and_censoring": {
            "energy_depletion": final_telemetry.energy_nonviable,
            "protective_thermal_shutdown": final_telemetry.protective_shutdown,
            "emergency_hard_thermal_shutdown": final_telemetry.emergency_hard_shutdown,
            "horizon_truncation": truncated,
            "unresolved_seek_at_termination": int(terminated and unresolved_seek > 0),
            "unresolved_seek_at_horizon": int(truncated and unresolved_seek > 0),
            "demonstrated_failed_seek_episodes": failed_seek_episodes,
            "horizon_censored_seek_episodes": horizon_censored_seek_episodes,
            "seek_contact_already_true_at_entry": contact_already_true_at_entry,
            "reacquisition_followed_by_termination_before_full_recharge": int(
                terminated and recharge_episode_active
            ),
            "full_recharge_without_redeparture_before_horizon": int(
                truncated and recharge_ready_for_departure
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


def run_d025_lifetime_trace(
    seed: int = D025_CANONICAL_VISUALIZATION_SEED,
    *,
    horizon: int = D025_HORIZON,
) -> tuple[D025TransitionTrace, ...]:
    """Run one exact-horizon D-025 lifetime for canonical replay."""
    _validate_d025_seed(seed)
    if horizon != D025_HORIZON:
        raise ValueError(
            "D-025 visualization requires the frozen 70,000-transition horizon"
        )
    trace: list[D025TransitionTrace] = []
    _run_d025_seed(seed, horizon=horizon, trace=trace)
    if not trace:
        raise RuntimeError("D-025 lifetime trace contains no completed transitions")
    return tuple(trace)


def run_d025_probe(executed_commit_sha: str | None = None) -> dict[str, object]:
    """Run the exactly three frozen D-025 development lifetimes."""
    seeds = _validate_d025_development_seeds(D025_DEFAULT_DEVELOPMENT_SEEDS)
    executed_sha = _validate_executed_commit_sha(executed_commit_sha)
    return {
        "schema_version": 1,
        "experiment": "D-025",
        "title": "Bounded stochastic SEEK de-trapping",
        "authoritative_base_sha": D025_AUTHORITATIVE_BASE_SHA,
        "implementation_probe_sha": executed_sha,
        "development_seeds": list(seeds),
        "horizon": D025_HORIZON,
        "timestep_seconds": D020PhysicalConfig().dt_seconds,
        "simulated_duration_seconds": D025_HORIZON * D020PhysicalConfig().dt_seconds,
        "lifetime": "one uninterrupted causal lifetime per seed",
        "seed_policy": {
            "canonical_validator": "validate_exp003_development_seeds",
            "exact_declared_seeds": list(D025_DEFAULT_DEVELOPMENT_SEEDS),
            "formal_reservation_guard_preserved": True,
        },
        "freeze": {
            "controller": (
                "D021Controller semantics outside authorized false-contact "
                "SEEK arbitration"
            ),
            "environment": "D024Env and D-024 exact initial state unchanged",
            "horizon": D025_HORIZON,
            "initial_station_center": list(d024.D024_STATION_CENTER),
            "initial_body_center": list(d024.D024_INITIAL_BODY_CENTER),
            "initial_heading": d024.D024_INITIAL_HEADING,
            "initial_battery_j": d024.D024_INITIAL_BATTERY_J,
            "initial_temperature_c": d024.D024_INITIAL_TEMPERATURE_C,
            "initial_latch": False,
            "initial_controller_mode": D025Mode.CHARGE.name,
            "body_length": d024.D024_BODY_LENGTH,
            "body_width": d024.D024_BODY_WIDTH,
            "body_rear_contacts_body_frame": [
                [d024.D024_REAR_X, d024.D024_CONTACT_LATERAL_OFFSET],
                [d024.D024_REAR_X, -d024.D024_CONTACT_LATERAL_OFFSET],
            ],
            "dock_orientation": d024.D024_DOCK_ORIENTATION,
            "dock_contacts_station_offsets": [
                [0.0, d024.D024_CONTACT_LATERAL_OFFSET],
                [0.0, -d024.D024_CONTACT_LATERAL_OFFSET],
            ],
            "contact_tolerance_inclusive": d024.D024_CONTACT_TOLERANCE,
            "delegation_probability": D025_SEEK_DELEGATION_PROBABILITY,
            "delegation_probability_reuse": (
                "engineering reuse of EXP001_EXPLORER_HAZARD; not a biological claim"
            ),
            "one_policy_rng_draw_per_false_contact_seek_decision": True,
            "policy_rng": (
                "RandomStreams.from_seed(seed).policy, continuous; "
                "no reseed/new stream"
            ),
            "begin_segment": "once on SEEK entry; no reseed and no RNG consumption",
            "event_definitions_frozen": True,
        },
        "programmed": {
            "controller_modes": [mode.name for mode in D025Mode],
            "controller": (
                "fixed non-learning D-021 controller with D-025 SEEK "
                "arbitration"
            ),
            "non_seek_behavior": "D-021 unchanged",
            "greedy_default": "existing seek_beacon_action",
            "delegation": (
                "false-contact SEEK only; existing StochasticPersistentExplorer"
            ),
            "learning": False,
        },
        "organism_visible": {
            "observation_type": "D011Observation projection of D020's six channels",
            "channels": [
                "normalized own battery energy",
                "beacon left",
                "beacon forward",
                "beacon right",
                "charging_contact as binary dual-contact predicate",
                "normalized own body temperature",
            ],
            "temperature_used_for_behavior": False,
        },
        "evaluator_only": {
            "fields": [
                "pose, heading, station/dock geometry, pair errors",
                "greedy and actual arbitration labels and RNG draws",
                "delegation/effective-perturbation labels",
                "charger telemetry and event classifications",
                "prefix comparisons and scientific metrics",
            ],
            "passed_to_controller_except_visible_beacon_and_policy_rng": False,
        },
        "learned": {"status": "none"},
        "inferred": {
            "interpretation": "descriptive bounded-development observation only",
            "no_pass_threshold": True,
            "no_claim_of_robustness_or_general_sufficiency": True,
        },
        "organism_boundary": {"reward": 0.0, "info": {}},
        "results": [
            _run_d025_seed(seed, horizon=D025_HORIZON)
            for seed in seeds
        ],
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the D-025 bounded stochastic SEEK de-trapping probe."
    )
    parser.add_argument("--executed-commit-sha")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    payload = json.dumps(
        run_d025_probe(executed_commit_sha=args.executed_commit_sha),
        indent=2,
        sort_keys=True,
    )
    if args.output is None:
        print(payload)
    else:
        args.output.write_text(payload + "\n", encoding="utf-8")
        print(f"D-025 result written to {args.output}")


if __name__ == "__main__":
    main()
