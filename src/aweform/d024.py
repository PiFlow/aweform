"""D-024 causal finite-body dual-contact docking probe.

The environment changes only D-020's physical charging-contact predicate.
Energy, thermal, movement, action, observation, reward, and info semantics
are inherited unchanged from :mod:`aweform.d020`.  The runner reuses the
actual fixed :class:`aweform.d021.D021Controller`; all geometry diagnostics
remain evaluator-only.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import replace
from pathlib import Path
from typing import Final, Sequence, cast

from . import d021
from .body import Coordinate
from .d020 import (
    D020Env,
    D020PhysicalConfig,
    D020TerminationReason,
)
from .env import Action
from .exp003 import EXP003_B50_ENTER_SEEK_THRESHOLD, _charging_contact
from .exp003_seed_policy import validate_exp003_development_seeds
from .rng import RandomStreams

D024_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = (18365, 18366, 18367)
D024_HORIZON: Final[int] = 70_000
D024_AUTHORITATIVE_BASE_SHA: Final[str] = (
    "c0ce8182d0fba97035d76899e5b188ca7f171b05"
)
D024_BODY_LENGTH: Final[float] = 0.10
D024_BODY_WIDTH: Final[float] = 0.08
D024_REAR_X: Final[float] = -0.05
D024_CONTACT_LATERAL_OFFSET: Final[float] = 0.025
D024_DOCK_ORIENTATION: Final[float] = 0.0
D024_CONTACT_TOLERANCE: Final[float] = 0.01
D024_STATION_CENTER: Final[Coordinate] = (0.50, 0.50)
D024_INITIAL_BODY_CENTER: Final[Coordinate] = (0.55, 0.50)
D024_INITIAL_HEADING: Final[float] = 0.0
D024_INITIAL_BATTERY_J: Final[float] = 5328.0
D024_INITIAL_TEMPERATURE_C: Final[float] = 23.0


def _rotate(offset: Coordinate, heading: float) -> Coordinate:
    cosine = math.cos(heading)
    sine = math.sin(heading)
    return (
        offset[0] * cosine - offset[1] * sine,
        offset[0] * sine + offset[1] * cosine,
    )


def _translate(origin: Coordinate, offset: Coordinate) -> Coordinate:
    return (origin[0] + offset[0], origin[1] + offset[1])


def body_rear_contacts_world(
    body_center: Coordinate, body_heading: float
) -> tuple[Coordinate, Coordinate]:
    """Return corresponding rear-plus and rear-minus body contacts."""
    return (
        _translate(
            body_center,
            _rotate((D024_REAR_X, D024_CONTACT_LATERAL_OFFSET), body_heading),
        ),
        _translate(
            body_center,
            _rotate((D024_REAR_X, -D024_CONTACT_LATERAL_OFFSET), body_heading),
        ),
    )


def dock_contacts_world(
    station_center: Coordinate,
) -> tuple[Coordinate, Coordinate]:
    """Return fixed corresponding dock contacts at ``phi == 0``."""
    return (
        _translate(
            station_center,
            _rotate((0.0, D024_CONTACT_LATERAL_OFFSET), D024_DOCK_ORIENTATION),
        ),
        _translate(
            station_center,
            _rotate((0.0, -D024_CONTACT_LATERAL_OFFSET), D024_DOCK_ORIENTATION),
        ),
    )


def dual_contact_pair_errors(
    body_center: Coordinate,
    body_heading: float,
    station_center: Coordinate,
) -> tuple[float, float]:
    """Return plus/plus and minus/minus Euclidean errors without swapping."""
    body_plus, body_minus = body_rear_contacts_world(body_center, body_heading)
    dock_plus, dock_minus = dock_contacts_world(station_center)
    return math.dist(body_plus, dock_plus), math.dist(body_minus, dock_minus)


def has_dual_contact(
    body_center: Coordinate,
    body_heading: float,
    station_center: Coordinate,
) -> bool:
    """Return the inclusive corresponding two-pair D-024 contact predicate."""
    plus_error, minus_error = dual_contact_pair_errors(
        body_center, body_heading, station_center
    )
    return (
        _within_contact_tolerance(plus_error)
        and _within_contact_tolerance(minus_error)
    )


def _within_contact_tolerance(error: float) -> bool:
    """Apply the literal inclusive contact tolerance."""
    return error <= D024_CONTACT_TOLERANCE


class D024Env(D020Env):
    """D-020 physical environment with only causal D-024 contact changed."""

    @property
    def charging_contact(self) -> bool:
        if self.body is None or self.station_center is None:
            raise RuntimeError("environment must be reset before observing")
        return has_dual_contact(
            self.body.position,
            self.body.heading,
            self.station_center,
        )


def legacy_circular_contact(
    body_center: Coordinate,
    station_center: Coordinate,
    config: D020PhysicalConfig,
) -> bool:
    """Return the evaluator-only historical circular-contact diagnostic."""
    return _charging_contact(
        body_center,
        station_center,
        config.charging_radius,
    )


def _validate_d024_development_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    """Apply the canonical reservation guard and exact D-024 seed guard."""
    validated = validate_exp003_development_seeds(seeds)
    if validated != D024_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-024 requires exactly the frozen development seeds "
            f"{D024_DEFAULT_DEVELOPMENT_SEEDS}; got {validated}"
        )
    return validated


def _validate_d024_seed(seed: int) -> None:
    """Apply the canonical guard and accept one member of the frozen set."""
    validated = validate_exp003_development_seeds((seed,))
    if validated[0] not in D024_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-024 may execute only predeclared development seeds "
            f"{D024_DEFAULT_DEVELOPMENT_SEEDS}; got {validated}"
        )


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
    return {mode.name: 0 for mode in d021.D021Mode}


def _distance(position: Coordinate, station: Coordinate) -> float:
    return math.dist(position, station)


def _geometry_metrics(
    position: Coordinate,
    heading: float,
    station: Coordinate,
) -> dict[str, float | bool]:
    plus_error, minus_error = dual_contact_pair_errors(position, heading, station)
    return {
        "rear_plus_pair_error": plus_error,
        "rear_minus_pair_error": minus_error,
        "max_pair_error": max(plus_error, minus_error),
        "one_pair_only_within_tolerance": (
            _within_contact_tolerance(plus_error)
            != _within_contact_tolerance(minus_error)
        ),
    }


def _pair_error_record(
    metrics: dict[str, float | bool],
    *,
    transition_index: int,
    position: Coordinate,
    heading: float,
) -> dict[str, object]:
    """Record one deterministic SEEK minimum candidate."""
    return {
        "value": metrics["max_pair_error"],
        "transition": transition_index,
        "body_center": list(position),
        "heading": heading,
        "rear_plus_pair_error": metrics["rear_plus_pair_error"],
        "rear_minus_pair_error": metrics["rear_minus_pair_error"],
    }


def _new_seek_episode(
    *,
    transition_index: int,
    observation: d021.D021Observation,
    action: Action,
    position: Coordinate,
    heading: float,
    station: Coordinate,
    legacy_contact: bool,
) -> dict[str, object]:
    metrics = _geometry_metrics(position, heading, station)
    return {
        "seek_entry_transition": transition_index,
        "entry_action": action.name,
        "energy_at_entry": observation.energy,
        "temperature_normalized_at_entry": observation.thermal,
        "charging_contact_at_entry": observation.charging_contact,
        "legacy_circular_contact_at_entry": legacy_contact,
        "evaluator_distance_at_entry": _distance(position, station),
        "minimum_rear_plus_pair_error_during_seek": metrics[
            "rear_plus_pair_error"
        ],
        "minimum_rear_minus_pair_error_during_seek": metrics[
            "rear_minus_pair_error"
        ],
        "minimum_max_pair_error_during_seek": metrics["max_pair_error"],
        "minimum_max_pair_error_during_seek_record": _pair_error_record(
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
    position: Coordinate,
    heading: float,
    station: Coordinate,
    transition_index: int,
) -> None:
    metrics = _geometry_metrics(position, heading, station)
    previous_max = cast(float, episode["minimum_max_pair_error_during_seek"])
    current_max = cast(float, metrics["max_pair_error"])
    for key, metric_key in (
        (
            "minimum_rear_plus_pair_error_during_seek",
            "rear_plus_pair_error",
        ),
        (
            "minimum_rear_minus_pair_error_during_seek",
            "rear_minus_pair_error",
        ),
        ("minimum_max_pair_error_during_seek", "max_pair_error"),
    ):
        previous = cast(float, episode[key])
        episode[key] = min(previous, cast(float, metrics[metric_key]))
    # Strictly-less-than preserves the first transition on an exact tie.
    if current_max < previous_max:
        episode["minimum_max_pair_error_during_seek_record"] = _pair_error_record(
            metrics,
            transition_index=transition_index,
            position=position,
            heading=heading,
        )
    if bool(metrics["one_pair_only_within_tolerance"]):
        episode["one_pair_only_tolerance_events"] = (
            cast(int, episode["one_pair_only_tolerance_events"]) + 1
        )


def _run_d024_seed(seed: int, *, horizon: int = D024_HORIZON) -> dict[str, object]:
    """Run one exact-pose, uninterrupted D-024 lifetime."""
    _validate_d024_seed(seed)
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon <= 0:
        raise ValueError("horizon must be a positive integer")

    config = D020PhysicalConfig()
    run_config = replace(config, episode_horizon=horizon)
    streams = RandomStreams.from_seed(seed)
    environment = D024Env(run_config)
    observation, info = environment.reset(
        options={
            "body_position": D024_INITIAL_BODY_CENTER,
            "station_center": D024_STATION_CENTER,
            "heading": D024_INITIAL_HEADING,
            "battery_j": D024_INITIAL_BATTERY_J,
            "body_temperature_c": D024_INITIAL_TEMPERATURE_C,
            "charger_termination_latched": False,
        }
    )
    if info != {}:
        raise RuntimeError("D-024 reset crossed the information boundary")
    if environment.body is None or environment.station_center is None:
        raise RuntimeError("D-024 reset did not initialize evaluator geometry")
    if not environment.charging_contact:
        raise RuntimeError("D-024 exact initial pose is not in dual contact")

    controller = d021.D021Controller(streams.policy)
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
    minimum_battery_j = D024_INITIAL_BATTERY_J
    maximum_battery_j = D024_INITIAL_BATTERY_J
    initial_temperature = float(observation[5])
    maximum_temperature = initial_temperature
    final_temperature = initial_temperature
    maximum_temperature_c = D024_INITIAL_TEMPERATURE_C
    final_temperature_c = D024_INITIAL_TEMPERATURE_C

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
    terminated = False
    truncated = False

    while not (terminated or truncated):
        if environment.body is None or environment.station_center is None:
            raise RuntimeError("D-024 evaluator geometry disappeared")
        current = d021._controller_observation(observation)
        mode_before = controller.mode
        mode_occupancy[mode_before.name] += 1
        action = controller.act(current)
        mode_after = controller.mode
        action_counts[action.name] += 1
        if mode_after is not mode_before:
            mode_entry_counts[mode_after.name] += 1

        transition_index = transitions + 1
        if mode_before is d021.D021Mode.CHARGE and mode_after is d021.D021Mode.DEPART:
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
        if mode_before is d021.D021Mode.SEEK and mode_after is d021.D021Mode.CHARGE:
            charge_entries += 1

        observation, reward, terminated, truncated, info = environment.step(action)
        if reward != 0.0 or info != {}:
            raise RuntimeError("D-024 reward or info crossed the boundary")
        telemetry = environment.last_transition
        if telemetry is None:
            raise RuntimeError("D-024 transition telemetry is unavailable")
        transitions += 1

        dual_after = telemetry.charging_contact_after
        legacy_after = legacy_circular_contact(
            telemetry.position_after, telemetry.station_center, run_config
        )
        if not telemetry.charging_contact_before and dual_after:
            dual_contact_entries += 1
            pair_errors = dual_contact_pair_errors(
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

        if legacy_after and not dual_after and mode_after is d021.D021Mode.SEEK:
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
            mode_before is d021.D021Mode.AWAY
            and mode_after is d021.D021Mode.SEEK
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
                legacy_contact=legacy_circular_contact(
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
            mode_before is d021.D021Mode.AWAY
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
                active_seek["evaluator_distance_at_reacquisition"] = _distance(
                    telemetry.position_after, telemetry.station_center
                )
                active_seek["reacquisition_action"] = action.name
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
        raise RuntimeError("D-024 run ended without final telemetry")
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
    return {
        "seed": seed,
        "initial_pose": {
            "station_center": list(D024_STATION_CENTER),
            "body_center": list(D024_INITIAL_BODY_CENTER),
            "heading": D024_INITIAL_HEADING,
            "initial_dual_contact": True,
            "initial_battery_j": D024_INITIAL_BATTERY_J,
            "initial_temperature_c": D024_INITIAL_TEMPERATURE_C,
            "initial_latch": False,
            "initial_controller_mode": d021.D021Mode.CHARGE.name,
        },
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
            "start": D024_INITIAL_BATTERY_J,
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
        "dual_contact_entries": dual_contact_entries,
        "charge_entries": charge_entries,
        "full_recharge_events": full_recharge_events,
        "post_recharge_redepartures": post_recharge_redepartures,
        "completed_energy_regulation_cycles": completed_cycles,
        "accidental_away_contacts": accidental_away_contacts,
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
            "unresolved_seek_at_termination": int(
                terminated and unresolved_seek > 0
            ),
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


def run_d024_probe(executed_commit_sha: str | None = None) -> dict[str, object]:
    """Run the three frozen D-024 development lifetimes."""
    seeds = _validate_d024_development_seeds(D024_DEFAULT_DEVELOPMENT_SEEDS)
    executed_sha = _validate_executed_commit_sha(executed_commit_sha)
    return {
        "schema_version": 1,
        "experiment": "D-024",
        "title": "Causal finite-body dual-contact docking probe",
        "authoritative_base_sha": D024_AUTHORITATIVE_BASE_SHA,
        "implementation_probe_sha": executed_sha,
        "development_seeds": list(seeds),
        "horizon": D024_HORIZON,
        "timestep_seconds": D020PhysicalConfig().dt_seconds,
        "simulated_duration_seconds": (
            D024_HORIZON * D020PhysicalConfig().dt_seconds
        ),
        "lifetime": "one uninterrupted causal lifetime per seed",
        "seed_policy": {
            "canonical_validator": "validate_exp003_development_seeds",
            "exact_declared_seeds": list(D024_DEFAULT_DEVELOPMENT_SEEDS),
            "formal_reservation_guard_preserved": True,
        },
        "freeze": {
            "controller": "actual D021Controller unchanged",
            "physical_config": "D020PhysicalConfig unchanged except episode_horizon",
            "horizon": D024_HORIZON,
            "initial_station_center": list(D024_STATION_CENTER),
            "initial_body_center": list(D024_INITIAL_BODY_CENTER),
            "initial_heading": D024_INITIAL_HEADING,
            "initial_battery_j": D024_INITIAL_BATTERY_J,
            "initial_temperature_c": D024_INITIAL_TEMPERATURE_C,
            "initial_latch": False,
            "initial_controller_mode": d021.D021Mode.CHARGE.name,
            "body_length": D024_BODY_LENGTH,
            "body_width": D024_BODY_WIDTH,
            "body_rear_contacts_body_frame": [
                [D024_REAR_X, D024_CONTACT_LATERAL_OFFSET],
                [D024_REAR_X, -D024_CONTACT_LATERAL_OFFSET],
            ],
            "dock_orientation": D024_DOCK_ORIENTATION,
            "dock_contacts_station_offsets": [
                [0.0, D024_CONTACT_LATERAL_OFFSET],
                [0.0, -D024_CONTACT_LATERAL_OFFSET],
            ],
            "contact_tolerance_inclusive": D024_CONTACT_TOLERANCE,
            "legacy_circular_contact_is_diagnostic_only": True,
        },
        "programmed": {
            "controller_modes": [mode.name for mode in d021.D021Mode],
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
                "charging_contact as binary dual-contact predicate",
                "normalized own body temperature",
            ],
            "temperature_used_for_behavior": False,
        },
        "evaluator_only": {
            "fields": [
                "body and dock geometry",
                "x/y/heading and station location",
                "true distance",
                "battery joules and absolute Celsius",
                "charger phase/latch and D-020 telemetry",
                "dual-contact pair errors",
                "legacy circular contact diagnostics",
                "mode/action/SEEK/recharge/termination summaries",
            ],
            "passed_to_controller": False,
        },
        "learned": {"status": "none"},
        "organism_boundary": {"reward": 0.0, "info": {}},
        "interpretation": {
            "full_cycle": (
                "full docked departure -> low-energy SEEK -> valid dual-contact "
                "charging -> full recharge -> post-recharge re-departure"
            ),
            "contact_already_true_at_seek_entry": (
                "report provenance; do not claim SEEK solved docking"
            ),
            "partial_diagnostics": (
                "one-pair tolerance, small pair error, or legacy circular contact "
                "without dual contact are near-approach diagnostics only"
            ),
            "censoring": (
                "unresolved at transition 70,000 is horizon-censored, not failure"
            ),
        },
        "results": [
            _run_d024_seed(seed, horizon=D024_HORIZON) for seed in seeds
        ],
    }


def write_d024_json(path: Path, executed_commit_sha: str | None = None) -> Path:
    """Write the compact D-024 result artifact."""
    path.write_text(
        json.dumps(
            run_d024_probe(executed_commit_sha=executed_commit_sha),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the D-024 causal dual-contact docking probe."
    )
    parser.add_argument("--executed-commit-sha")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.output is None:
        print(
            json.dumps(
                run_d024_probe(args.executed_commit_sha), indent=2, sort_keys=True
            )
        )
    else:
        write_d024_json(args.output, args.executed_commit_sha)
        print(f"D-024 result written to {args.output}")


if __name__ == "__main__":
    main()
