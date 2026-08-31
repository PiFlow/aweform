"""D-017 evaluator-only shadow rear-docking pose decomposition audit.

This module executes the unchanged D-014 controller/ecology and evaluates only
the poses at autonomous physical charging-contact entries.  The shadow body,
dock orientations, and all geometry calculations are post-hoc evaluator data;
none is available to the controller or environment.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from statistics import median
from typing import Final, Sequence

from . import d011, d014
from .d002 import D002ThermalStationEnv
from .d003 import HOT_DEPART_THRESHOLD
from .env import Action
from .exp003 import EXP003_B50_ENTER_SEEK_THRESHOLD, EXP003StationConfig
from .exp003_seed_policy import validate_exp003_development_seeds

D017_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = (18356, 18357, 18358)
D017_HORIZON: Final[int] = 1000
D017_AUTHORITATIVE_BASE_SHA: Final[str] = (
    "c291f171da3098737920d7567f3c5ea01aad30a8"
)
D017_BODY_LENGTH: Final[float] = 0.10
D017_BODY_WIDTH: Final[float] = 0.08
D017_REAR_X: Final[float] = -0.05
D017_CONTACT_LATERAL_OFFSET: Final[float] = 0.025
D017_FRONT_X: Final[float] = 0.05
D017_CONTACT_TOLERANCE: Final[float] = 0.01
D017_DOCK_ORIENTATIONS: Final[tuple[float, ...]] = (
    0.0,
    math.pi / 4.0,
    math.pi / 2.0,
    3.0 * math.pi / 4.0,
    math.pi,
    5.0 * math.pi / 4.0,
    3.0 * math.pi / 2.0,
    7.0 * math.pi / 4.0,
)

Coordinate = tuple[float, float]


class _Samples:
    """Small descriptive continuous-distribution accumulator."""

    def __init__(self) -> None:
        self.values: list[float] = []

    def add(self, value: float) -> None:
        self.values.append(float(value))

    def as_dict(self) -> dict[str, object]:
        if not self.values:
            return {
                "status": "untested",
                "count": 0,
                "mean": None,
                "median": None,
                "min": None,
                "max": None,
            }
        return {
            "status": "visited",
            "count": len(self.values),
            "mean": sum(self.values) / len(self.values),
            "median": float(median(self.values)),
            "min": min(self.values),
            "max": max(self.values),
        }


def _rotate(local: Coordinate, heading: float) -> Coordinate:
    cosine = math.cos(heading)
    sine = math.sin(heading)
    return (
        local[0] * cosine - local[1] * sine,
        local[0] * sine + local[1] * cosine,
    )


def _translate(origin: Coordinate, offset: Coordinate) -> Coordinate:
    return (origin[0] + offset[0], origin[1] + offset[1])


def shadow_rear_contacts_world(
    body_center: Coordinate, body_heading: float
) -> tuple[Coordinate, Coordinate]:
    """Return corresponding rear plus/minus contacts in world coordinates."""
    return (
        _translate(
            body_center,
            _rotate((D017_REAR_X, D017_CONTACT_LATERAL_OFFSET), body_heading),
        ),
        _translate(
            body_center,
            _rotate((D017_REAR_X, -D017_CONTACT_LATERAL_OFFSET), body_heading),
        ),
    )


def shadow_front_midpoint_world(
    body_center: Coordinate, body_heading: float
) -> Coordinate:
    """Return the evaluator-only front-face midpoint comparator."""
    return _translate(body_center, _rotate((D017_FRONT_X, 0.0), body_heading))


def shadow_dock_contacts_world(
    station_center: Coordinate, dock_orientation: float
) -> tuple[Coordinate, Coordinate]:
    """Return corresponding plus/minus contacts on one hypothetical dock."""
    lateral_axis = (-math.sin(dock_orientation), math.cos(dock_orientation))
    offset = (
        D017_CONTACT_LATERAL_OFFSET * lateral_axis[0],
        D017_CONTACT_LATERAL_OFFSET * lateral_axis[1],
    )
    return (
        _translate(station_center, offset),
        _translate(station_center, (-offset[0], -offset[1])),
    )


def ideal_rear_docking_pose(
    station_center: Coordinate, dock_orientation: float
) -> tuple[Coordinate, float]:
    """Return the declared exact ideal rear-docking body pose."""
    outward_axis = (math.cos(dock_orientation), math.sin(dock_orientation))
    body_center = _translate(
        station_center,
        (0.05 * outward_axis[0], 0.05 * outward_axis[1]),
    )
    return body_center, dock_orientation


def shadow_pair_errors(
    body_center: Coordinate,
    body_heading: float,
    station_center: Coordinate,
    dock_orientation: float,
) -> tuple[float, float]:
    """Return corresponding rear-plus and rear-minus Euclidean errors."""
    rear_plus, rear_minus = shadow_rear_contacts_world(body_center, body_heading)
    dock_plus, dock_minus = shadow_dock_contacts_world(
        station_center, dock_orientation
    )
    return math.dist(rear_plus, dock_plus), math.dist(rear_minus, dock_minus)


def rear_front_midpoint_errors(
    body_center: Coordinate,
    body_heading: float,
    station_center: Coordinate,
) -> tuple[float, float]:
    """Return rear and front midpoint distances to the station centre."""
    rear_midpoint = _translate(
        body_center, _rotate((D017_REAR_X, 0.0), body_heading)
    )
    front_midpoint = shadow_front_midpoint_world(body_center, body_heading)
    return math.dist(rear_midpoint, station_center), math.dist(
        front_midpoint, station_center
    )


def station_relative_geometry(
    body_center: Coordinate,
    body_heading: float,
    station_center: Coordinate,
) -> tuple[float, float, float, float]:
    """Return radial distance, body-frame x/y, and incidence angle."""
    dx = station_center[0] - body_center[0]
    dy = station_center[1] - body_center[1]
    forward = (math.cos(body_heading), math.sin(body_heading))
    lateral = (-math.sin(body_heading), math.cos(body_heading))
    x_rel = dx * forward[0] + dy * forward[1]
    y_rel = dx * lateral[0] + dy * lateral[1]
    return math.hypot(dx, dy), x_rel, y_rel, math.atan2(y_rel, x_rel)


def _pair_metric(
    body_center: Coordinate,
    body_heading: float,
    station_center: Coordinate,
    dock_orientation: float,
) -> dict[str, object]:
    rear_plus_error, rear_minus_error = shadow_pair_errors(
        body_center, body_heading, station_center, dock_orientation
    )
    max_pair_error = max(rear_plus_error, rear_minus_error)
    return {
        "orientation": dock_orientation,
        "rear_plus_error": rear_plus_error,
        "rear_minus_error": rear_minus_error,
        "max_pair_error": max_pair_error,
        "mean_pair_error": (rear_plus_error + rear_minus_error) / 2.0,
        "both_within_tolerance": (
            rear_plus_error <= D017_CONTACT_TOLERANCE
            and rear_minus_error <= D017_CONTACT_TOLERANCE
        ),
    }


def _entry_record(
    *,
    transition_index: int,
    action: Action,
    body_center: Coordinate,
    body_heading: float,
    station_center: Coordinate,
) -> dict[str, object]:
    radial_distance, x_rel, y_rel, incidence_angle = station_relative_geometry(
        body_center, body_heading, station_center
    )
    rear_error, front_error = rear_front_midpoint_errors(
        body_center, body_heading, station_center
    )
    fixed_metrics = [
        _pair_metric(body_center, body_heading, station_center, orientation)
        for orientation in D017_DOCK_ORIENTATIONS
    ]
    max_errors: list[float] = []
    for metric in fixed_metrics:
        value = metric["max_pair_error"]
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise RuntimeError("max_pair_error is not numeric")
        max_errors.append(float(value))
    minimum_error = min(max_errors)
    minimum_orientations = [
        metric["orientation"]
        for metric in fixed_metrics
        if metric["max_pair_error"] == minimum_error
    ]
    matched_metrics = _pair_metric(
        body_center, body_heading, station_center, body_heading
    )
    return {
        "transition_index": transition_index,
        "action": action.name,
        "body_center": [body_center[0], body_center[1]],
        "body_heading": body_heading,
        "station_center": [station_center[0], station_center[1]],
        "body_center_entry_radius": radial_distance,
        "x_rel": x_rel,
        "y_rel": y_rel,
        "incidence_angle": incidence_angle,
        "station_ahead": x_rel > 0.0,
        "station_behind": x_rel < 0.0,
        "station_exactly_zero": x_rel == 0.0,
        "rear_positional_error": rear_error,
        "front_positional_error": front_error,
        "rear_positional_within_tolerance": rear_error <= D017_CONTACT_TOLERANCE,
        "front_positional_within_tolerance": front_error <= D017_CONTACT_TOLERANCE,
        "fixed_orientation_metrics": fixed_metrics,
        "minimum_fixed_sweep_max_pair_error": minimum_error,
        "minimum_fixed_sweep_orientations": minimum_orientations,
        "orientation_matched": {
            "orientation": body_heading,
            "rear_plus_error": matched_metrics["rear_plus_error"],
            "rear_minus_error": matched_metrics["rear_minus_error"],
            "max_pair_error": matched_metrics["max_pair_error"],
            "mean_pair_error": matched_metrics["mean_pair_error"],
            "both_within_tolerance": matched_metrics["both_within_tolerance"],
        },
    }


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


def _validate_d017_development_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    """Apply the canonical reservation guard, then D-017's exact guard."""
    validated = validate_exp003_development_seeds(seeds)
    unexpected = tuple(
        seed for seed in validated if seed not in D017_DEFAULT_DEVELOPMENT_SEEDS
    )
    if unexpected:
        raise ValueError(
            "D-017 may execute only predeclared development seeds "
            f"{D017_DEFAULT_DEVELOPMENT_SEEDS}; got {unexpected}"
        )
    return validated


def _samples_for_entries(entries: Sequence[dict[str, object]]) -> dict[str, _Samples]:
    names = (
        "body_center_entry_radius",
        "x_rel",
        "y_rel",
        "incidence_angle",
        "rear_positional_error",
        "front_positional_error",
        "orientation_matched_max_pair_error",
        "minimum_fixed_sweep_max_pair_error",
    )
    samples = {name: _Samples() for name in names}
    for entry in entries:
        for name in names[:6]:
            value = entry[name]
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise RuntimeError(f"entry field {name} is not numeric")
            samples[name].add(float(value))
        matched = entry["orientation_matched"]
        if not isinstance(matched, dict):
            raise RuntimeError("orientation_matched is not a mapping")
        for name, field in (
            ("orientation_matched_max_pair_error", "max_pair_error"),
            (
                "minimum_fixed_sweep_max_pair_error",
                "minimum_fixed_sweep_max_pair_error",
            ),
        ):
            value = (
                matched.get(field)
                if name.startswith("orientation")
                else entry[field]
            )
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise RuntimeError(f"entry field {field} is not numeric")
            samples[name].add(float(value))
    return samples


def _aggregate_entries(entries: Sequence[dict[str, object]]) -> dict[str, object]:
    samples = _samples_for_entries(entries)
    fixed_max: dict[str, _Samples] = {
        str(orientation): _Samples() for orientation in D017_DOCK_ORIENTATIONS
    }
    fixed_successes = {str(orientation): 0 for orientation in D017_DOCK_ORIENTATIONS}
    matched_successes = 0
    ahead = behind = exactly_zero = 0
    rear_successes = front_successes = 0
    for entry in entries:
        if bool(entry["station_ahead"]):
            ahead += 1
        if bool(entry["station_behind"]):
            behind += 1
        if bool(entry["station_exactly_zero"]):
            exactly_zero += 1
        rear_successes += int(bool(entry["rear_positional_within_tolerance"]))
        front_successes += int(bool(entry["front_positional_within_tolerance"]))
        matched = entry["orientation_matched"]
        if not isinstance(matched, dict):
            raise RuntimeError("orientation_matched is not a mapping")
        matched_successes += int(bool(matched["both_within_tolerance"]))
        metrics = entry["fixed_orientation_metrics"]
        if not isinstance(metrics, list) or len(metrics) != len(D017_DOCK_ORIENTATIONS):
            raise RuntimeError("fixed orientation metrics are incomplete")
        for metric in metrics:
            if not isinstance(metric, dict):
                raise RuntimeError("fixed orientation metric is not a mapping")
            orientation = metric["orientation"]
            if not isinstance(orientation, (int, float)) or isinstance(
                orientation, bool
            ):
                raise RuntimeError("fixed orientation is not numeric")
            key = str(float(orientation))
            fixed_max[key].add(float(metric["max_pair_error"]))
            fixed_successes[key] += int(bool(metric["both_within_tolerance"]))
    return {
        "autonomous_contact_entries": len(entries),
        "station_ahead_count": ahead,
        "station_behind_count": behind,
        "station_exactly_zero_count": exactly_zero,
        "rear_positional_within_tolerance_count": rear_successes,
        "front_positional_within_tolerance_count": front_successes,
        "orientation_matched_rear_two_contact_success_count": matched_successes,
        "fixed_orientation_two_contact_success_counts": fixed_successes,
        "continuous": {
            name: sample.as_dict() for name, sample in samples.items()
        },
        "fixed_orientation_max_pair_error_distributions": {
            key: sample.as_dict() for key, sample in fixed_max.items()
        },
    }


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

    controller = d014.D014Controller(random_streams.policy)
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
    entries: list[dict[str, object]] = []
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
            full_energy_condition = current.energy >= d014.D014_FULL_ENERGY_THRESHOLD
            hot_thermal_condition = current.thermal >= HOT_DEPART_THRESHOLD
            if full_energy_condition and hot_thermal_condition:
                trigger_category = "both"
            elif full_energy_condition:
                trigger_category = "full_only"
            elif hot_thermal_condition:
                trigger_category = "thermal_only"
            else:
                raise RuntimeError("D-017 departed without a valid trigger")
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
        body = environment.body
        station = environment.station_center
        if telemetry is None or body is None or station is None:
            raise RuntimeError("D-017 transition telemetry is unavailable")
        transitions += 1

        if not telemetry.charging_contact_before and telemetry.charging_contact_after:
            entries.append(
                _entry_record(
                    transition_index=transitions,
                    action=action,
                    body_center=body.position,
                    body_heading=body.heading,
                    station_center=station,
                )
            )

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
                raise RuntimeError("D-017 opened a second SEEK episode")
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
            raise RuntimeError("D-017 ended with an unresolved SEEK episode")
    else:
        demonstrated_failed_seek_episodes = 0
        horizon_censored_seek_episodes = 0

    final = environment.last_transition
    if final is None:
        raise RuntimeError("D-017 run ended without final telemetry")
    aggregate = _aggregate_entries(entries)
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
        "docking_audit": {
            "autonomous_entry_definition": (
                "charging_contact_before == False and "
                "charging_contact_after == True"
            ),
            "initial_post_contact_setup_excluded": True,
            "entries": entries,
            "aggregates": aggregate,
        },
        "evaluator_only": {
            "seeded_heading": seeded_heading,
            "post_contact_setup": {
                "body_position": [0.5, 0.5],
                "station_position": [0.5, 0.5],
                "seeded_heading_preserved": True,
            },
            "shadow_geometry_does_not_control_behavior": True,
            "passed_to_controller": False,
        },
    }


def _validate_executed_commit_sha(value: str | None) -> str | None:
    if value is None:
        return None
    if re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise ValueError("executed_commit_sha must be a 40-character lowercase SHA")
    return value


def run_d017_probe(
    seeds: Sequence[int] = D017_DEFAULT_DEVELOPMENT_SEEDS,
    *,
    horizon: int = D017_HORIZON,
    executed_commit_sha: str | None = None,
) -> dict[str, object]:
    """Run one uninterrupted evaluator-only D-017 lifetime per seed."""
    development_seeds = _validate_d017_development_seeds(seeds)
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon <= 0:
        raise ValueError("horizon must be a positive integer")
    results = [_run_seed(seed, horizon=horizon) for seed in development_seeds]
    all_entries: list[dict[str, object]] = []
    per_seed_aggregates: dict[str, object] = {}
    for result in results:
        audit = result["docking_audit"]
        if not isinstance(audit, dict):
            raise RuntimeError("D-017 docking audit is not a mapping")
        entries = audit["entries"]
        if not isinstance(entries, list):
            raise RuntimeError("D-017 entries are not a list")
        all_entries.extend(entries)
        per_seed_aggregates[str(result["seed"])] = audit["aggregates"]
    return {
        "schema_version": 1,
        "experiment": "D-017",
        "title": "Shadow rear-docking pose decomposition audit",
        "authoritative_base_sha": D017_AUTHORITATIVE_BASE_SHA,
        "executed_commit_sha": _validate_executed_commit_sha(executed_commit_sha),
        "development_seeds": list(development_seeds),
        "horizon": horizon,
        "lifetime": "one uninterrupted lifetime per seed",
        "seed_policy": {
            "canonical_validator": "validate_exp003_development_seeds",
            "exact_declared_seeds": list(D017_DEFAULT_DEVELOPMENT_SEEDS),
            "formal_reservation_guard_preserved": True,
        },
        "programmed": {
            "controller": "D014Controller",
            "ecology": "unchanged D002/EXP003",
            "post_contact_setup": "unchanged D-014 setup",
            "action_set": [action.name for action in Action],
            "shadow_body_length": D017_BODY_LENGTH,
            "shadow_body_width": D017_BODY_WIDTH,
            "shadow_rear_x": D017_REAR_X,
            "shadow_rear_contacts_body_frame": [
                [D017_REAR_X, D017_CONTACT_LATERAL_OFFSET],
                [D017_REAR_X, -D017_CONTACT_LATERAL_OFFSET],
            ],
            "shadow_front_midpoint_body_frame": [D017_FRONT_X, 0.0],
            "dock_contact_lateral_offset": D017_CONTACT_LATERAL_OFFSET,
            "fixed_dock_orientations": list(D017_DOCK_ORIENTATIONS),
            "contact_tolerance": D017_CONTACT_TOLERANCE,
            "geometry_formulas": "evaluator-only rigid-body transforms",
            "no_forced_actions": True,
            "no_learner": True,
            "no_policy_or_environment_rng_in_geometry": True,
        },
        "organism_visible": {
            "observation_type": "D011Observation",
            "channels": [
                "normalized_energy",
                "normalized_thermal",
                "beacon.left",
                "beacon.forward",
                "beacon.right",
                "charging_contact",
            ],
            "own_executed_action_as_history": True,
            "shadow_values_visible": False,
        },
        "learned": {"status": "none", "learner_instantiated": False},
        "evaluator_only": {
            "actual_coordinates": True,
            "actual_heading": True,
            "shadow_body_and_contacts": True,
            "hypothetical_dock_orientations": True,
            "entry_pose_decomposition": True,
            "front_midpoint_comparator": True,
            "pair_errors_and_success_classifications": True,
            "aggregate_metrics": True,
            "passed_to_controller": False,
            "passed_to_environment": False,
            "passed_to_learning": False,
        },
        "ecology": {
            "environment": "D002ThermalStationEnv",
            "station": "unchanged EXP-003 station beacon/contact",
            "charging_semantics_unchanged": True,
        },
        "organism_boundary": {"reward": 0.0, "info": {}},
        "results": results,
        "aggregates": {
            "per_seed": per_seed_aggregates,
            "pooled": _aggregate_entries(all_entries),
        },
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the D-017 shadow rear-docking pose audit."
    )
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=list(D017_DEFAULT_DEVELOPMENT_SEEDS),
        help="Predeclared D-017 development seeds only.",
    )
    parser.add_argument("--horizon", type=int, default=D017_HORIZON)
    parser.add_argument("--executed-commit-sha")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    """Run D-017 and print or write its machine-readable result."""
    args = _parse_args()
    payload = json.dumps(
        run_d017_probe(
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
        print(f"D-017 result written to {args.output}")


if __name__ == "__main__":
    main()
