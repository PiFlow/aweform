"""D-016 evaluator-only current-beacon contact observability audit.

The organism and its D-014 controller are unchanged.  This module reconstructs
station-relative geometry from the existing organism-visible L/F/R beacon only,
forms a nominal contact-transition prediction before the environment step, and
uses evaluator telemetry after the step to measure representation and realized-
motion limits.  No reconstructed value is passed to the controller, learner,
policy RNG, or environment.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Final, Sequence

from . import d011, d014
from .d002 import D002ThermalStationEnv
from .d003 import HOT_DEPART_THRESHOLD
from .env import Action
from .exp003 import (
    EXP003_B50_ENTER_SEEK_THRESHOLD,
    EXP003_CHARGING_RADIUS,
    BeaconObservation,
    EXP003StationConfig,
)
from .exp003_seed_policy import validate_exp003_development_seeds

D016_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = (18353, 18354, 18355)
D016_HORIZON: Final[int] = 1000
D016_AUTHORITATIVE_BASE_SHA: Final[str] = (
    "185c480f34bea3db536fd80a95dea9603f5e0d1f"
)
# These are engineering comparison tolerances, not scientific bins or
# acceptance thresholds.  The motion tolerance distinguishes exact nominal
# floating-point motion from deterministic boundary-reduced motion; the
# geometry tolerance identifies a beacon inverse that is accurate to the
# expected float32 observation representation.
D016_MOTION_TOLERANCE: Final[float] = 1e-12
D016_GEOMETRY_NUMERICAL_TOLERANCE: Final[float] = 1e-6


@dataclass(frozen=True, slots=True)
class RelativeGeometry:
    """Evaluator-side station position in the current body frame."""

    x: float
    y: float

    @property
    def radial_distance(self) -> float:
        return math.hypot(self.x, self.y)


def _is_reduced_move(actual_displacement: float, nominal_distance: float) -> bool:
    """Classify deterministic boundary reduction using engineering tolerance."""
    if not math.isfinite(actual_displacement) or not math.isfinite(nominal_distance):
        raise ValueError("displacements must be finite")
    if nominal_distance < 0.0 or actual_displacement < 0.0:
        raise ValueError("displacements must be non-negative")
    if actual_displacement > nominal_distance + D016_MOTION_TOLERANCE:
        raise RuntimeError("realized movement exceeded its nominal distance")
    return actual_displacement < nominal_distance - D016_MOTION_TOLERANCE


def _require_positive_finite(name: str, value: float) -> None:
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError(f"{name} must be finite and positive")


def _distance_from_signal(signal: float, beacon_scale: float) -> float:
    if not math.isfinite(signal) or not 0.0 < signal <= 1.0:
        raise ValueError("beacon signal must be finite and in (0, 1]")
    return beacon_scale * math.sqrt((1.0 / signal) - 1.0)


def reconstruct_relative_geometry(
    beacon: BeaconObservation,
    *,
    beacon_scale: float,
    probe_distance: float,
    sensor_angle: float,
) -> RelativeGeometry:
    """Invert the current L/F/R beacon into evaluator-only body-frame geometry.

    The function accepts no evaluator coordinates.  It uses only the three
    current beacon signals and fixed declared EXP-003 sensor constants.
    """
    if not isinstance(beacon, BeaconObservation):
        raise ValueError("beacon must be a BeaconObservation")
    _require_positive_finite("beacon_scale", beacon_scale)
    _require_positive_finite("probe_distance", probe_distance)
    if not math.isfinite(sensor_angle):
        raise ValueError("sensor_angle must be finite")
    sine = math.sin(sensor_angle)
    cosine = math.cos(sensor_angle)
    denominator_y = 4.0 * probe_distance * sine
    denominator_x = 2.0 * probe_distance * (1.0 - cosine)
    if abs(denominator_y) <= D016_MOTION_TOLERANCE:
        raise ValueError("sensor_angle is degenerate for left/right recovery")
    if abs(denominator_x) <= D016_MOTION_TOLERANCE:
        raise ValueError("sensor_angle is degenerate for forward recovery")

    d_left = _distance_from_signal(beacon.left, beacon_scale)
    d_forward = _distance_from_signal(beacon.forward, beacon_scale)
    d_right = _distance_from_signal(beacon.right, beacon_scale)
    left_squared = d_left * d_left
    forward_squared = d_forward * d_forward
    right_squared = d_right * d_right
    y = (right_squared - left_squared) / denominator_y
    x = (((left_squared + right_squared) / 2.0) - forward_squared) / denominator_x
    return RelativeGeometry(x=x, y=y)


def _relative_geometry_after_forward(
    geometry: RelativeGeometry, forward_distance: float
) -> RelativeGeometry:
    return RelativeGeometry(geometry.x - forward_distance, geometry.y)


def predict_nominal_next_contact(
    geometry: RelativeGeometry,
    current_contact: bool,
    action: Action,
    *,
    movement_distance: float,
    charging_radius: float,
) -> bool:
    """Predict next contact using nominal unclipped current EXP-003 motion."""
    _require_positive_finite("charging_radius", charging_radius)
    if not math.isfinite(movement_distance) or movement_distance < 0.0:
        raise ValueError("movement_distance must be finite and non-negative")
    if action is not Action.MOVE_FORWARD:
        return current_contact
    return (
        _relative_geometry_after_forward(geometry, movement_distance).radial_distance
        <= charging_radius
    )


def _world_to_body_frame(
    body_position: tuple[float, float],
    station_position: tuple[float, float],
    heading: float,
) -> RelativeGeometry:
    """Evaluator-only scoring transform; never used by the decoder."""
    dx = station_position[0] - body_position[0]
    dy = station_position[1] - body_position[1]
    return RelativeGeometry(
        x=dx * math.cos(heading) + dy * math.sin(heading),
        y=-dx * math.sin(heading) + dy * math.cos(heading),
    )


class _Samples:
    def __init__(self) -> None:
        self.values: list[float] = []

    def add(self, value: float) -> None:
        self.values.append(float(value))

    def as_dict(self) -> dict[str, object]:
        if not self.values:
            return {
                "status": "untested",
                "count": 0,
                "min": None,
                "mean": None,
                "median": None,
                "max": None,
            }
        return {
            "status": "visited",
            "count": len(self.values),
            "min": min(self.values),
            "mean": sum(self.values) / len(self.values),
            "median": float(median(self.values)),
            "max": max(self.values),
        }


def _contact_event(current: bool, next_contact: bool) -> str:
    if current and not next_contact:
        return "contact_exit"
    if not current and next_contact:
        return "contact_entry"
    return "contact_unchanged"


def _new_prediction_counts() -> dict[str, object]:
    return {
        "total": 0,
        "correct": 0,
        "errors": 0,
        "accuracy": None,
        "actual_event_counts": {
            "contact_entry": 0,
            "contact_exit": 0,
            "contact_unchanged": 0,
        },
        "predicted_event_counts": {
            "contact_entry": 0,
            "contact_exit": 0,
            "contact_unchanged": 0,
        },
        "confusion": {
            actual: {
                predicted: 0
                for predicted in (
                    "contact_entry",
                    "contact_exit",
                    "contact_unchanged",
                )
            }
            for actual in (
                "contact_entry",
                "contact_exit",
                "contact_unchanged",
            )
        },
        "false_entry_predictions": 0,
        "missed_entries": 0,
        "false_exit_predictions": 0,
        "missed_exits": 0,
    }


def _counter_value(table: dict[str, object], key: str) -> int:
    value = table.get(key)
    if not isinstance(value, int):
        raise RuntimeError(f"invalid integer counter for {key}")
    return value


def _record_prediction(
    counts: dict[str, object], actual: str, predicted: str
) -> None:
    total = _counter_value(counts, "total")
    correct = _counter_value(counts, "correct")
    errors = _counter_value(counts, "errors")
    actual_counts = counts["actual_event_counts"]
    predicted_counts = counts["predicted_event_counts"]
    confusion = counts["confusion"]
    if not isinstance(total, int) or not isinstance(correct, int):
        raise RuntimeError("invalid prediction counters")
    if not isinstance(errors, int):
        raise RuntimeError("invalid prediction error counter")
    if not isinstance(actual_counts, dict) or not isinstance(predicted_counts, dict):
        raise RuntimeError("invalid prediction event counters")
    if not isinstance(confusion, dict):
        raise RuntimeError("invalid prediction confusion table")
    counts["total"] = total + 1
    if actual == predicted:
        counts["correct"] = correct + 1
    else:
        counts["errors"] = errors + 1
    actual_counts[actual] = _counter_value(actual_counts, actual) + 1
    predicted_counts[predicted] = _counter_value(predicted_counts, predicted) + 1
    row = confusion[actual]
    if not isinstance(row, dict):
        raise RuntimeError("invalid prediction confusion row")
    row[predicted] = _counter_value(row, predicted) + 1
    if predicted == "contact_entry" and actual != "contact_entry":
        counts["false_entry_predictions"] = (
            _counter_value(counts, "false_entry_predictions") + 1
        )
    if actual == "contact_entry" and predicted != "contact_entry":
        counts["missed_entries"] = _counter_value(counts, "missed_entries") + 1
    if predicted == "contact_exit" and actual != "contact_exit":
        counts["false_exit_predictions"] = (
            _counter_value(counts, "false_exit_predictions") + 1
        )
    if actual == "contact_exit" and predicted != "contact_exit":
        counts["missed_exits"] = _counter_value(counts, "missed_exits") + 1


def _finish_prediction_counts(counts: dict[str, object]) -> None:
    total = _counter_value(counts, "total")
    counts["accuracy"] = _counter_value(counts, "correct") / total if total else None


def _empty_geometry_metrics() -> dict[str, _Samples]:
    return {name: _Samples() for name in ("x", "y", "radial")}


def _geometry_metrics_as_dict(
    metrics: dict[str, _Samples], event_metrics: dict[str, dict[str, _Samples]]
) -> dict[str, object]:
    return {
        "overall": {name: sample.as_dict() for name, sample in metrics.items()},
        "by_actual_event": {
            event: {name: sample.as_dict() for name, sample in values.items()}
            for event, values in event_metrics.items()
        },
    }


def _empty_event_samples() -> dict[str, _Samples]:
    return {
        "contact_entry": _Samples(),
        "contact_exit": _Samples(),
        "contact_unchanged": _Samples(),
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


def _validate_d016_development_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    """Apply the canonical reservation guard, then D-016's exact guard."""
    validated = validate_exp003_development_seeds(seeds)
    unexpected = tuple(
        seed for seed in validated if seed not in D016_DEFAULT_DEVELOPMENT_SEEDS
    )
    if unexpected:
        raise ValueError(
            "D-016 may execute only predeclared development seeds "
            f"{D016_DEFAULT_DEVELOPMENT_SEEDS}; got {unexpected}"
        )
    return validated


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
    context_predictions = {
        str(contact): {action.name: _new_prediction_counts() for action in Action}
        for contact in (False, True)
    }
    overall_predictions = _new_prediction_counts()
    geometry_metrics = _empty_geometry_metrics()
    event_geometry_metrics = {
        event: _empty_geometry_metrics()
        for event in ("contact_entry", "contact_exit", "contact_unchanged")
    }
    margin_metrics = _empty_event_samples()
    move_displacements = _Samples()
    move_forward_displacements = _Samples()
    alias_outcomes: dict[tuple[float, float, float, bool, str], dict[bool, int]] = {}
    mismatch_records: list[dict[str, object]] = []
    mismatch_with_clipping = 0
    mismatch_without_clipping = 0
    reconstruction_numerical_mismatches = 0
    other_cause_mismatches = 0
    achieved_displacement_resolved = 0
    full_nominal_moves = 0
    clipped_moves = 0

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
        body = environment.body
        station = environment.station_center
        if body is None or station is None:
            raise RuntimeError("D-016 evaluator geometry is unavailable")
        heading_before = body.heading
        mode_before = controller.mode
        mode_occupancy[mode_before.name] += 1
        action = controller.act(current)
        mode_after = controller.mode
        action_counts[action.name] += 1
        if mode_after is not mode_before:
            mode_entry_counts[mode_after.name] += 1

        # Prediction is completed while only the current organism-visible
        # observation and declared constants are available, before env.step.
        decoded = reconstruct_relative_geometry(
            current.beacon,
            beacon_scale=config.beacon_scale,
            probe_distance=config.probe_distance,
            sensor_angle=config.sensor_angle,
        )
        nominal_contact = predict_nominal_next_contact(
            decoded,
            current.charging_contact,
            action,
            movement_distance=config.movement_distance,
            charging_radius=config.charging_radius,
        )
        nominal_post_geometry = _relative_geometry_after_forward(
            decoded,
            config.movement_distance if action is Action.MOVE_FORWARD else 0.0,
        )
        nominal_margin = nominal_post_geometry.radial_distance - config.charging_radius

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
                raise RuntimeError("D-016 departed without a valid trigger")
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
        base_telemetry = environment.base_env.last_transition
        body_after = environment.body
        station_after = environment.station_center
        if (
            telemetry is None
            or base_telemetry is None
            or body_after is None
            or station_after is None
        ):
            raise RuntimeError("D-016 transition telemetry is unavailable")
        transitions += 1
        next_current = d011._controller_observation(observation)
        actual_event = _contact_event(
            current.charging_contact, next_current.charging_contact
        )
        _record_prediction(overall_predictions, actual_event, _contact_event(
            current.charging_contact, nominal_contact
        ))
        _record_prediction(
            context_predictions[str(current.charging_contact)][action.name],
            actual_event,
            _contact_event(current.charging_contact, nominal_contact),
        )
        margin_metrics[actual_event].add(nominal_margin)

        actual_geometry = _world_to_body_frame(
            base_telemetry.position_before,
            station_after,
            heading_before,
        )
        geometry_metrics["x"].add(abs(decoded.x - actual_geometry.x))
        geometry_metrics["y"].add(abs(decoded.y - actual_geometry.y))
        geometry_metrics["radial"].add(
            abs(decoded.radial_distance - actual_geometry.radial_distance)
        )
        event_geometry_metrics[actual_event]["x"].add(
            abs(decoded.x - actual_geometry.x)
        )
        event_geometry_metrics[actual_event]["y"].add(
            abs(decoded.y - actual_geometry.y)
        )
        event_geometry_metrics[actual_event]["radial"].add(
            abs(decoded.radial_distance - actual_geometry.radial_distance)
        )

        alias_key = (
            current.beacon.left,
            current.beacon.forward,
            current.beacon.right,
            current.charging_contact,
            action.name,
        )
        outcomes = alias_outcomes.setdefault(alias_key, {})
        outcomes[next_current.charging_contact] = (
            outcomes.get(next_current.charging_contact, 0) + 1
        )

        actual_displacement = math.dist(
            base_telemetry.position_before, base_telemetry.position_after
        )
        actual_forward_displacement = (
            (base_telemetry.position_after[0] - base_telemetry.position_before[0])
            * math.cos(heading_before)
            + (base_telemetry.position_after[1] - base_telemetry.position_before[1])
            * math.sin(heading_before)
        )
        clipped = False
        if action is Action.MOVE_FORWARD:
            move_displacements.add(actual_displacement)
            move_forward_displacements.add(actual_forward_displacement)
            if _is_reduced_move(actual_displacement, config.movement_distance):
                clipped = True
                clipped_moves += 1
            else:
                full_nominal_moves += 1

        actual_nominal_contact = predict_nominal_next_contact(
            actual_geometry,
            current.charging_contact,
            action,
            movement_distance=config.movement_distance,
            charging_radius=config.charging_radius,
        )
        achieved_contact = predict_nominal_next_contact(
            decoded,
            current.charging_contact,
            action,
            movement_distance=actual_forward_displacement
            if action is Action.MOVE_FORWARD
            else 0.0,
            charging_radius=config.charging_radius,
        )
        prediction_mismatch = nominal_contact != next_current.charging_contact
        if prediction_mismatch:
            if clipped:
                mismatch_with_clipping += 1
            else:
                mismatch_without_clipping += 1
            reconstruction_numerical = (
                nominal_contact != actual_nominal_contact
                and max(
                    abs(decoded.x - actual_geometry.x),
                    abs(decoded.y - actual_geometry.y),
                )
                <= D016_GEOMETRY_NUMERICAL_TOLERANCE
            )
            if reconstruction_numerical:
                reconstruction_numerical_mismatches += 1
            resolved = achieved_contact == next_current.charging_contact
            if resolved:
                achieved_displacement_resolved += 1
            if clipped and resolved:
                attribution = "clipped_realized_motion"
            elif reconstruction_numerical:
                attribution = "reconstruction_numerical_error"
            else:
                attribution = "other_cause"
                other_cause_mismatches += 1
            mismatch_records.append(
                {
                    "transition": transitions,
                    "action": action.name,
                    "current_charging_contact": current.charging_contact,
                    "predicted_next_contact": nominal_contact,
                    "actual_next_contact": next_current.charging_contact,
                    "actual_event": actual_event,
                    "nominal_margin": nominal_margin,
                    "clipped_reduced_movement": clipped,
                    "realized_displacement": actual_displacement,
                    "realized_forward_displacement": actual_forward_displacement,
                    "actual_geometry_nominal_prediction": actual_nominal_contact,
                    "achieved_displacement_prediction": achieved_contact,
                    "achieved_displacement_resolves_mismatch": resolved,
                    "reconstruction_numerical_error": reconstruction_numerical,
                    "attribution": attribution,
                }
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
                raise RuntimeError("D-016 opened a second SEEK episode")
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
            raise RuntimeError("D-016 ended with an unresolved SEEK episode")
    else:
        demonstrated_failed_seek_episodes = 0
        horizon_censored_seek_episodes = 0

    final = environment.last_transition
    if final is None or environment.body is None or environment.station_center is None:
        raise RuntimeError("D-016 run ended without final telemetry")
    _finish_prediction_counts(overall_predictions)
    for contact_predictions in context_predictions.values():
        for counts in contact_predictions.values():
            _finish_prediction_counts(counts)

    alias_records: list[dict[str, object]] = []
    for key, outcomes in alias_outcomes.items():
        if len(outcomes) <= 1:
            continue
        alias_records.append(
            {
                "beacon_left": key[0],
                "beacon_forward": key[1],
                "beacon_right": key[2],
                "current_charging_contact": key[3],
                "action": key[4],
                "sample_count": sum(outcomes.values()),
                "next_contact_counts": {
                    str(contact): count for contact, count in outcomes.items()
                },
            }
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
        "observability": {
            "beacon_reconstruction": _geometry_metrics_as_dict(
                geometry_metrics, event_geometry_metrics
            ),
            "nominal_next_contact_prediction": overall_predictions,
            "action_current_contact_breakdown": context_predictions,
            "signed_boundary_margin_by_actual_event": {
                event: samples.as_dict() for event, samples in margin_metrics.items()
            },
            "realized_motion": {
                "nominal_movement_distance": config.movement_distance,
                "actual_displacement": move_displacements.as_dict(),
                "actual_forward_displacement": move_forward_displacements.as_dict(),
                "full_nominal_moves": full_nominal_moves,
                "clipped_reduced_moves": clipped_moves,
            },
            "mismatch_diagnostics": {
                "total_nominal_prediction_mismatches": len(mismatch_records),
                "mismatches_with_clipping": mismatch_with_clipping,
                "mismatches_without_clipping": mismatch_without_clipping,
                "reconstruction_numerical_error_mismatches": (
                    reconstruction_numerical_mismatches
                ),
                "other_cause_mismatches": other_cause_mismatches,
                "achieved_displacement_substitution_resolves": (
                    achieved_displacement_resolved
                ),
                "records": mismatch_records,
            },
            "exact_visible_state_aliasing": {
                "key_definition": "exact float L/F/R + bool contact + action",
                "unique_keys": len(alias_outcomes),
                "repeated_keys": sum(
                    1
                    for outcomes in alias_outcomes.values()
                    if sum(outcomes.values()) > 1
                ),
                "aliased_keys": len(alias_records),
                "records": alias_records,
            },
            "evaluator_only": True,
        },
        "evaluator_only": {
            "seeded_heading": seeded_heading,
            "post_contact_setup": {
                "body_position": [0.5, 0.5],
                "station_position": [0.5, 0.5],
                "seeded_heading_preserved": True,
            },
            "coordinates_used_after_beacon_reconstruction_only": True,
            "passed_to_controller": False,
        },
    }


def _validate_executed_commit_sha(value: str | None) -> str | None:
    if value is None:
        return None
    if re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise ValueError("executed_commit_sha must be a 40-character lowercase SHA")
    return value


def run_d016_probe(
    seeds: Sequence[int] = D016_DEFAULT_DEVELOPMENT_SEEDS,
    *,
    horizon: int = D016_HORIZON,
    executed_commit_sha: str | None = None,
) -> dict[str, object]:
    """Run one uninterrupted evaluator-only D-016 audit per declared seed."""
    development_seeds = _validate_d016_development_seeds(seeds)
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon <= 0:
        raise ValueError("horizon must be a positive integer")
    return {
        "schema_version": 1,
        "experiment": "D-016",
        "title": "Current-beacon contact-transition observability audit",
        "authoritative_base_sha": D016_AUTHORITATIVE_BASE_SHA,
        "executed_commit_sha": _validate_executed_commit_sha(executed_commit_sha),
        "development_seeds": list(development_seeds),
        "horizon": horizon,
        "lifetime": "one uninterrupted lifetime per seed",
        "seed_policy": {
            "canonical_validator": "validate_exp003_development_seeds",
            "exact_declared_seeds": list(D016_DEFAULT_DEVELOPMENT_SEEDS),
            "formal_reservation_guard_preserved": True,
        },
        "programmed": {
            "controller": "D014Controller",
            "inherits": "D011Controller",
            "ecology": "unchanged D002/EXP003",
            "beacon_transformation": "unchanged EXP003 directional beacon",
            "analytic_inverse": "evaluator-only L/F/R algebraic reconstruction",
            "contact_decoder": "evaluator-only nominal kinematic decoder",
            "metric_definitions": "pre-action prediction, post-action scoring",
            "movement_tolerance": D016_MOTION_TOLERANCE,
            "geometry_numerical_tolerance": D016_GEOMETRY_NUMERICAL_TOLERANCE,
            "model_guided_action": False,
            "counterfactual_action_selection": False,
            "forced_actions": False,
            "no_learner": True,
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
            "own_executed_action": True,
            "analytic_decoder_uses_energy_or_thermal": False,
            "coordinates_or_evaluator_telemetry": False,
        },
        "learned": {"status": "none", "learner_instantiated": False},
        "evaluator_only": {
            "reconstructed_relative_geometry": True,
            "actual_coordinates_for_reconstruction_scoring_only": True,
            "actual_displacement": True,
            "clipping_classification": True,
            "actual_next_contact_event_label": True,
            "confusion_and_error_metrics": True,
            "viability_and_cycle_summaries": True,
            "post_hoc_achieved_displacement_check": True,
            "passed_to_controller": False,
            "passed_to_learner": False,
        },
        "ecology": {
            "environment": "D002ThermalStationEnv",
            "post_contact_setup": "unchanged D-011 setup",
            "charging_radius": EXP003_CHARGING_RADIUS,
        },
        "organism_boundary": {"reward": 0.0, "info": {}},
        "results": [_run_seed(seed, horizon=horizon) for seed in development_seeds],
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the D-016 current-beacon observability audit."
    )
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=list(D016_DEFAULT_DEVELOPMENT_SEEDS),
        help="Predeclared D-016 development seeds only.",
    )
    parser.add_argument("--horizon", type=int, default=D016_HORIZON)
    parser.add_argument("--executed-commit-sha")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    """Run D-016 and print or write its machine-readable result."""
    args = _parse_args()
    payload = json.dumps(
        run_d016_probe(
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
        print(f"D-016 result written to {args.output}")


if __name__ == "__main__":
    main()
