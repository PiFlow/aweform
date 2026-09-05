"""D-027 shadow sensorimotor consequence-learning development probe.

The D-026 controller and D-024 physical environment are executed unchanged.
The only causal addition is a shadow-only, executed-action linear predictor;
its predictions and weights cannot reach action selection or the environment.
All pose, displacement, boundary labels, and outcome metrics are evaluator
data read after the learner update.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from dataclasses import dataclass, field, fields, is_dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Final, Sequence, cast

import numpy as np

from . import d024, d025, d026
from .d020 import D020PhysicalConfig
from .env import Action
from .exp003 import EXP003_B50_ENTER_SEEK_THRESHOLD
from .exp003_seed_policy import validate_exp003_development_seeds
from .rng import RandomStreams

D027_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = tuple(range(18388, 18408))
D027_CANONICAL_VISUALIZATION_SEED: Final[int] = D027_DEFAULT_DEVELOPMENT_SEEDS[0]
D027_HORIZON: Final[int] = 70_000
D027_LEARNING_RATE: Final[float] = 0.5
D027_FEATURE_DIMENSION: Final[int] = 7
D027_OUTPUTS: Final[tuple[str, ...]] = (
    "delta_energy",
    "delta_beacon_left",
    "delta_beacon_forward",
    "delta_beacon_right",
    "delta_charging_contact",
    "delta_thermal",
)
D027_CHANNELS: Final[tuple[str, ...]] = (
    "energy",
    "beacon.left",
    "beacon.forward",
    "beacon.right",
    "charging_contact",
    "thermal",
)
D027_PLASTIC_STATE_DIMENSION: Final[int] = 168
D027_BOUNDARY_TOLERANCE: Final[float] = 1e-12
D027_NOMINAL_MOVE_DISTANCE: Final[float] = 0.05
D027_WINDOW_SIZE: Final[int] = 17_500
D027_WINDOW_NAMES: Final[tuple[str, ...]] = ("Q1", "Q2", "Q3", "Q4")
D027_AUTHORITATIVE_BASE_SHA: Final[str] = "1059b7a02cf7964f1f1bf48c39db20e1f3a1edc9"
D027Observation = d026.D026Observation
D027Mode = d026.D026Mode

if len(Action) * len(D027_OUTPUTS) * D027_FEATURE_DIMENSION != (
    D027_PLASTIC_STATE_DIMENSION
):
    raise RuntimeError("D-027 plastic dimension no longer matches its declaration")


@dataclass(frozen=True, slots=True)
class D027Prediction:
    """The six pre-update predictions for one physically executed action."""

    values: tuple[float, ...]

    def as_dict(self) -> dict[str, float]:
        return dict(zip(D027_OUTPUTS, self.values, strict=True))


@dataclass(frozen=True, slots=True)
class D027LearningUpdate:
    """One post-transition visible-target update."""

    action: Action
    prediction: tuple[float, ...]
    observed_delta: tuple[float, ...]
    errors: tuple[float, ...]
    normalizer: float


class D027ActionConsequencePredictor:
    """Exactly 168 zero-initialized action/output/feature weights."""

    __slots__ = ("_weights",)

    def __init__(self) -> None:
        self._weights: dict[Action, list[list[float]]] = {}
        self.reset()

    @property
    def weights(self) -> tuple[float, ...]:
        return tuple(
            weight
            for action in Action
            for output_weights in self._weights[action]
            for weight in output_weights
        )

    def weight_snapshot(self) -> dict[str, dict[str, list[float]]]:
        return {
            output: {
                action.name: list(self._weights[action][output_index])
                for action in Action
            }
            for output_index, output in enumerate(D027_OUTPUTS)
        }

    def reset(self) -> None:
        self._weights = {
            action: [[0.0] * D027_FEATURE_DIMENSION for _ in D027_OUTPUTS]
            for action in Action
        }

    def predict(
        self, observation: d026.D026Observation, action: Action
    ) -> D027Prediction:
        self._validate_inputs(observation, action)
        features = self._features(observation)
        return D027Prediction(
            tuple(self._dot(weights, features) for weights in self._weights[action])
        )

    def observe_transition(
        self,
        observation: d026.D026Observation,
        action: Action,
        next_observation: d026.D026Observation,
    ) -> D027LearningUpdate:
        self._validate_inputs(observation, action)
        self._validate_inputs(next_observation, action)
        prediction = self.predict(observation, action)
        observed_delta = (
            next_observation.energy - observation.energy,
            next_observation.beacon.left - observation.beacon.left,
            next_observation.beacon.forward - observation.beacon.forward,
            next_observation.beacon.right - observation.beacon.right,
            float(next_observation.charging_contact)
            - float(observation.charging_contact),
            next_observation.thermal - observation.thermal,
        )
        errors = tuple(
            observed - predicted
            for observed, predicted in zip(
                observed_delta, prediction.values, strict=True
            )
        )
        features = self._features(observation)
        normalizer = self._dot(features, features)
        for output_index, error in enumerate(errors):
            for feature_index, feature in enumerate(features):
                self._weights[action][output_index][feature_index] += (
                    D027_LEARNING_RATE * error * feature / normalizer
                )
        return D027LearningUpdate(
            action, prediction.values, observed_delta, errors, normalizer
        )

    @staticmethod
    def _validate_inputs(observation: d026.D026Observation, action: Action) -> None:
        if not isinstance(observation, d026.D026Observation):
            raise ValueError("observation must be a D026Observation")
        if not isinstance(action, Action):
            raise ValueError("action must be an Action")

    @staticmethod
    def _features(observation: d026.D026Observation) -> tuple[float, ...]:
        return (
            1.0,
            observation.energy,
            observation.beacon.left,
            observation.beacon.forward,
            observation.beacon.right,
            float(observation.charging_contact),
            observation.thermal,
        )

    @staticmethod
    def _dot(left: Sequence[float], right: Sequence[float]) -> float:
        return sum(
            left_value * right_value for left_value, right_value in zip(left, right)
        )


@dataclass(slots=True)
class _MetricSums:
    count: int = 0
    learned_abs_error: list[float] | None = None
    baseline_abs_error: list[float] | None = None

    def __post_init__(self) -> None:
        if self.learned_abs_error is None:
            self.learned_abs_error = [0.0] * len(D027_OUTPUTS)
        if self.baseline_abs_error is None:
            self.baseline_abs_error = [0.0] * len(D027_OUTPUTS)

    def record(self, prediction: Sequence[float], observed: Sequence[float]) -> None:
        self.count += 1
        assert self.learned_abs_error is not None
        assert self.baseline_abs_error is not None
        for index, (predicted, actual) in enumerate(
            zip(prediction, observed, strict=True)
        ):
            self.learned_abs_error[index] += abs(predicted - actual)
            self.baseline_abs_error[index] += abs(actual)

    def merge(self, other: _MetricSums) -> None:
        self.count += other.count
        assert self.learned_abs_error is not None
        assert self.baseline_abs_error is not None
        assert other.learned_abs_error is not None
        assert other.baseline_abs_error is not None
        for index in range(len(D027_OUTPUTS)):
            self.learned_abs_error[index] += other.learned_abs_error[index]
            self.baseline_abs_error[index] += other.baseline_abs_error[index]

    def as_dict(self) -> dict[str, object]:
        if self.count == 0:
            return {"status": "untested", "sample_count": 0, "targets": {}}
        assert self.learned_abs_error is not None
        assert self.baseline_abs_error is not None
        targets: dict[str, object] = {}
        for index, target in enumerate(D027_OUTPUTS):
            learned = self.learned_abs_error[index] / self.count
            baseline = self.baseline_abs_error[index] / self.count
            targets[target] = {
                "learned_mae": learned,
                "zero_change_baseline_mae": baseline,
                "learned_baseline_mae_ratio": learned / baseline if baseline else None,
            }
        return {"status": "visited", "sample_count": self.count, "targets": targets}


@dataclass(slots=True)
class _BoundarySums:
    metrics: _MetricSums = field(default_factory=_MetricSums)
    observed_vector: list[float] | None = None
    predicted_vector: list[float] | None = None
    observed_beacon_magnitude: float = 0.0
    predicted_beacon_magnitude: float = 0.0

    def __post_init__(self) -> None:
        if self.observed_vector is None:
            self.observed_vector = [0.0] * len(D027_OUTPUTS)
        if self.predicted_vector is None:
            self.predicted_vector = [0.0] * len(D027_OUTPUTS)

    def record(self, prediction: Sequence[float], observed: Sequence[float]) -> None:
        self.metrics.record(prediction, observed)
        assert self.observed_vector is not None
        assert self.predicted_vector is not None
        for index, (predicted, actual) in enumerate(
            zip(prediction, observed, strict=True)
        ):
            self.observed_vector[index] += actual
            self.predicted_vector[index] += predicted
        self.observed_beacon_magnitude += math.sqrt(
            sum(value * value for value in observed[1:4])
        )
        self.predicted_beacon_magnitude += math.sqrt(
            sum(value * value for value in prediction[1:4])
        )

    def merge(self, other: _BoundarySums) -> None:
        self.metrics.merge(other.metrics)
        assert self.observed_vector is not None
        assert self.predicted_vector is not None
        assert other.observed_vector is not None
        assert other.predicted_vector is not None
        for index in range(len(D027_OUTPUTS)):
            self.observed_vector[index] += other.observed_vector[index]
            self.predicted_vector[index] += other.predicted_vector[index]
        self.observed_beacon_magnitude += other.observed_beacon_magnitude
        self.predicted_beacon_magnitude += other.predicted_beacon_magnitude

    def as_dict(self) -> dict[str, object]:
        result = dict(self.metrics.as_dict())
        count = self.metrics.count
        assert self.observed_vector is not None
        assert self.predicted_vector is not None
        result["mean_observed_delta"] = (
            [value / count for value in self.observed_vector] if count else None
        )
        result["mean_predicted_delta"] = (
            [value / count for value in self.predicted_vector] if count else None
        )
        result["mean_observed_beacon_delta_magnitude"] = (
            self.observed_beacon_magnitude / count if count else None
        )
        result["mean_predicted_beacon_delta_magnitude"] = (
            self.predicted_beacon_magnitude / count if count else None
        )
        return result


def _new_boundary() -> _BoundarySums:
    return _BoundarySums(metrics=_MetricSums())


def _metric_state() -> dict[str, object]:
    return {
        "overall": _MetricSums(),
        "by_action": {action.name: _MetricSums() for action in Action},
        "windows": {name: _MetricSums() for name in D027_WINDOW_NAMES},
    }


def _metric_state_dict(state: dict[str, object]) -> dict[str, object]:
    return {
        "overall": cast(_MetricSums, state["overall"]).as_dict(),
        "by_action": {
            action: metric.as_dict()
            for action, metric in cast(
                dict[str, _MetricSums], state["by_action"]
            ).items()
        },
        "by_quarter": {
            quarter: metric.as_dict()
            for quarter, metric in cast(
                dict[str, _MetricSums], state["windows"]
            ).items()
        },
    }


def _record_metrics(
    state: dict[str, object],
    action: Action,
    transition: int,
    prediction: D027Prediction,
    observed: Sequence[float],
) -> None:
    cast(_MetricSums, state["overall"]).record(prediction.values, observed)
    cast(dict[str, _MetricSums], state["by_action"])[action.name].record(
        prediction.values, observed
    )
    quarter = D027_WINDOW_NAMES[(transition - 1) // D027_WINDOW_SIZE]
    cast(dict[str, _MetricSums], state["windows"])[quarter].record(
        prediction.values, observed
    )


def _jsonable(value: object) -> object:
    if isinstance(value, Enum):
        return value.name
    if is_dataclass(value):
        return {
            field.name: _jsonable(getattr(value, field.name)) for field in fields(value)
        }
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def _trace_digest(trace: Sequence[object]) -> str:
    digest = hashlib.sha256()
    for record in trace:
        encoded = json.dumps(_jsonable(record), sort_keys=True, separators=(",", ":"))
        digest.update(encoded.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _validate_d027_development_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    validated = validate_exp003_development_seeds(seeds)
    if validated != D027_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-027 requires exactly the frozen development seeds "
            f"{D027_DEFAULT_DEVELOPMENT_SEEDS}; got {validated}"
        )
    return validated


def _validate_d027_seed(seed: int) -> None:
    validated = validate_exp003_development_seeds((seed,))
    if validated[0] not in D027_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-027 may execute only predeclared development seeds "
            f"{D027_DEFAULT_DEVELOPMENT_SEEDS}; got {validated}"
        )


def _validate_executed_commit_sha(value: str | None) -> str | None:
    if value is None or re.fullmatch(r"[0-9a-f]{40}", value) is not None:
        return value
    raise ValueError("executed_commit_sha must be a 40-character lowercase SHA")


def _termination_reason(
    environment: d026.D026Env, terminated: bool, truncated: bool
) -> str:
    telemetry = environment.last_transition
    if telemetry is not None and terminated:
        if telemetry.energy_nonviable:
            return "energy_depletion"
        if telemetry.protective_shutdown:
            return "protective_thermal_shutdown"
        if telemetry.emergency_hard_shutdown:
            return "emergency_hard_thermal_shutdown"
    if truncated:
        return "horizon_truncation"
    return "incomplete"


def _classify_forward_displacement(displacement: float) -> str:
    if displacement > D027_NOMINAL_MOVE_DISTANCE + D027_BOUNDARY_TOLERANCE:
        raise RuntimeError(
            f"MOVE_FORWARD displacement exceeded nominal distance: {displacement}"
        )
    if abs(displacement - D027_NOMINAL_MOVE_DISTANCE) <= D027_BOUNDARY_TOLERANCE:
        return "FULL_NOMINAL_FORWARD"
    return "BOUNDARY_CLIPPED_FORWARD"


def _initial_environment(
    horizon: int, seed: int
) -> tuple[d026.D026Env, np.ndarray, RandomStreams]:
    config = D020PhysicalConfig()
    environment = d026.D026Env(replace(config, episode_horizon=horizon))
    streams = RandomStreams.from_seed(seed)
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
        raise RuntimeError("D-027 reset crossed the information boundary")
    if environment.body is None or environment.station_center is None:
        raise RuntimeError("D-027 reset did not initialize evaluator geometry")
    if not environment.charging_contact:
        raise RuntimeError("D-024 exact initial pose is not in dual contact")
    return environment, observation, streams


def _run_lifetime(
    seed: int,
    *,
    horizon: int,
    learning: bool,
) -> tuple[dict[str, object], list[object]]:
    environment, observation, streams = _initial_environment(horizon, seed)
    controller = d026.D026Controller(streams.policy)
    controller.reset()
    learner = D027ActionConsequencePredictor() if learning else None
    trace: list[object] = []
    action_counts = {action.name: 0 for action in Action}
    mode_occupancy = {mode.name: 0 for mode in d026.D026Mode}
    mode_entry_counts = {mode.name: 0 for mode in d026.D026Mode}
    mode_entry_counts[controller.mode.name] = 1
    metrics = _metric_state()
    boundary = {
        "FULL_NOMINAL_FORWARD": {"overall": _new_boundary(), "Q4": _new_boundary()},
        "BOUNDARY_CLIPPED_FORWARD": {"overall": _new_boundary(), "Q4": _new_boundary()},
    }
    current_contact_counts = {action.name: {"False": 0, "True": 0} for action in Action}
    contact_delta_counts = {
        action.name: {"-1": 0, "0": 0, "+1": 0} for action in Action
    }
    transitions = 0
    terminated = False
    truncated = False
    minimum_energy = maximum_energy = float(observation[0])
    minimum_temperature = maximum_temperature = float(observation[5])
    full_departures = charger_exits = seek_entries = reacquisitions = 0
    full_recharges = redepartures = completed_cycles = 0
    active_seek = False
    recharge_active = False
    recharge_ready = False
    cycle_stage = 0
    max_displacement = 0.0
    boundary_counts = {
        name: 0
        for name in (
            "FULL_NOMINAL_FORWARD",
            "BOUNDARY_CLIPPED_FORWARD",
            "FULL_STALL_FORWARD",
        )
    }
    while not (terminated or truncated):
        if environment.body is None or environment.station_center is None:
            raise RuntimeError("D-027 evaluator geometry disappeared")
        current = d025._controller_observation(observation)
        mode_before = controller.mode
        mode_occupancy[mode_before.name] += 1
        action = controller.act(current)
        mode_after = controller.mode
        action_counts[action.name] += 1
        if mode_after is not mode_before:
            mode_entry_counts[mode_after.name] += 1
        transition_index = transitions + 1
        if mode_before is d026.D026Mode.CHARGE and mode_after is d026.D026Mode.DEPART:
            full_departures += 1
            if recharge_ready:
                redepartures += 1
                completed_cycles += 1
                recharge_ready = False
                cycle_stage = 1
            else:
                cycle_stage = 1

        prediction = (
            learner.predict(current, action)
            if learner is not None
            else D027Prediction((0.0,) * 6)
        )
        observation, reward, terminated, truncated, info = environment.step(action)
        if reward != 0.0 or info != {}:
            raise RuntimeError("D-027 reward or info crossed the boundary")
        telemetry = environment.last_transition
        if telemetry is None:
            raise RuntimeError("D-027 transition telemetry is unavailable")
        next_visible = d025._controller_observation(observation)
        update = (
            learner.observe_transition(current, action, next_visible)
            if learner is not None
            else None
        )
        if learning:
            assert update is not None
            observed = update.observed_delta
            _record_metrics(metrics, action, transition_index, prediction, observed)
            current_contact_counts[action.name][str(current.charging_contact)] += 1
            contact_key = {"-1.0": "-1", "0.0": "0", "1.0": "+1"}[str(observed[4])]
            contact_delta_counts[action.name][contact_key] += 1

        record = d025._make_trace(
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
        trace.append(record)
        transitions += 1

        if action is Action.MOVE_FORWARD:
            displacement = math.dist(
                telemetry.position_before, telemetry.position_after
            )
            max_displacement = max(max_displacement, displacement)
            category = _classify_forward_displacement(displacement)
            boundary_counts[category] += 1
            if displacement <= D027_BOUNDARY_TOLERANCE:
                boundary_counts["FULL_STALL_FORWARD"] += 1
            if learning and category in boundary:
                boundary[category]["overall"].record(prediction.values, observed)
                if transition_index > 3 * D027_WINDOW_SIZE:
                    boundary[category]["Q4"].record(prediction.values, observed)

        minimum_energy = min(minimum_energy, float(observation[0]))
        maximum_energy = max(maximum_energy, float(observation[0]))
        minimum_temperature = min(minimum_temperature, float(observation[5]))
        maximum_temperature = max(maximum_temperature, float(observation[5]))
        if telemetry.charging_contact_before and not telemetry.charging_contact_after:
            charger_exits += 1
            if cycle_stage == 1:
                cycle_stage = 2
        entered_seek = (
            mode_before is d026.D026Mode.AWAY
            and mode_after is d026.D026Mode.SEEK
            and current.energy < EXP003_B50_ENTER_SEEK_THRESHOLD
        )
        if entered_seek:
            seek_entries += 1
            active_seek = True
            if cycle_stage == 2:
                cycle_stage = 3
        if (
            active_seek
            and not current.charging_contact
            and telemetry.charging_contact_after
        ):
            active_seek = False
            reacquisitions += 1
            recharge_active = True
            if cycle_stage == 3:
                cycle_stage = 4
        if (
            recharge_active
            and telemetry.battery_after_j >= environment.config.battery_capacity_j
            and telemetry.charger_termination_latched_after
        ):
            recharge_active = False
            recharge_ready = True
            full_recharges += 1
            if cycle_stage == 4:
                cycle_stage = 5

        observation = observation

    if not trace:
        raise RuntimeError("D-027 lifetime produced no transitions")
    result: dict[str, object] = {
        "seed": seed,
        "transitions": transitions,
        "terminated": terminated,
        "truncated": truncated,
        "termination_reason": _termination_reason(environment, terminated, truncated),
        "action_counts": action_counts,
        "mode_occupancy": mode_occupancy,
        "mode_entry_counts": mode_entry_counts,
        "final_mode": controller.mode.name,
        "minimum_normalized_energy": minimum_energy,
        "final_normalized_energy": float(observation[0]),
        "maximum_normalized_energy": maximum_energy,
        "minimum_temperature": minimum_temperature,
        "final_temperature": float(observation[5]),
        "maximum_temperature": maximum_temperature,
        "full_departures": full_departures,
        "physical_charger_exits": charger_exits,
        "low_energy_seek_entries": seek_entries,
        "physical_reacquisitions": reacquisitions,
        "full_recharge_events": full_recharges,
        "post_recharge_redepartures": redepartures,
        "completed_energy_regulation_cycles": completed_cycles,
        "learner": learner,
        "prediction_metrics": _metric_state_dict(metrics),
        "support": {
            "by_action": {
                action: {
                    "sample_count": cast(dict[str, _MetricSums], metrics["by_action"])[
                        action
                    ].count,
                    "current_contact_counts": current_contact_counts[action],
                    "observed_contact_delta_target_counts": contact_delta_counts[
                        action
                    ],
                }
                for action in action_counts
            },
            "move_forward_boundary_counts": boundary_counts,
        },
        "boundary_metrics": {
            category: {
                "overall": values["overall"].as_dict(),
                "Q4": values["Q4"].as_dict(),
            }
            for category, values in boundary.items()
        },
        "boundary_max_realized_displacement": max_displacement,
        "trajectory_digest": _trace_digest(trace),
        "final_weights": learner.weight_snapshot() if learner is not None else None,
        "_metric_state": metrics,
        "_boundary_state": boundary,
    }
    return result, trace


def _merge_states(
    results: Sequence[dict[str, object]],
) -> tuple[dict[str, object], dict[str, dict[str, _BoundarySums]]]:
    metrics = _metric_state()
    boundary = {
        category: {"overall": _new_boundary(), "Q4": _new_boundary()}
        for category in ("FULL_NOMINAL_FORWARD", "BOUNDARY_CLIPPED_FORWARD")
    }
    for result in results:
        source = cast(dict[str, object], result["_metric_state"])
        cast(_MetricSums, metrics["overall"]).merge(
            cast(_MetricSums, source["overall"])
        )
        for action, metric in cast(dict[str, _MetricSums], source["by_action"]).items():
            cast(dict[str, _MetricSums], metrics["by_action"])[action].merge(metric)
        for quarter, metric in cast(dict[str, _MetricSums], source["windows"]).items():
            cast(dict[str, _MetricSums], metrics["windows"])[quarter].merge(metric)
        source_boundary = cast(
            dict[str, dict[str, _BoundarySums]], result["_boundary_state"]
        )
        for category in boundary:
            for window in boundary[category]:
                boundary[category][window].merge(source_boundary[category][window])
    return metrics, boundary


def _pooled_behavior(results: Sequence[dict[str, object]]) -> dict[str, object]:
    def summed(name: str) -> int:
        return sum(cast(int, result[name]) for result in results)

    action_counts = {
        action.name: sum(
            cast(dict[str, int], result["action_counts"])[action.name]
            for result in results
        )
        for action in Action
    }
    mode_occupancy = {
        mode.name: sum(
            cast(dict[str, int], result["mode_occupancy"])[mode.name]
            for result in results
        )
        for mode in d026.D026Mode
    }
    mode_entries = {
        mode.name: sum(
            cast(dict[str, int], result["mode_entry_counts"])[mode.name]
            for result in results
        )
        for mode in d026.D026Mode
    }
    return {
        "transitions": summed("transitions"),
        "terminated_lifetimes": sum(
            int(cast(bool, result["terminated"])) for result in results
        ),
        "truncated_lifetimes": sum(
            int(cast(bool, result["truncated"])) for result in results
        ),
        "action_counts": action_counts,
        "mode_occupancy": mode_occupancy,
        "mode_entry_counts": mode_entries,
        "full_departures": summed("full_departures"),
        "physical_charger_exits": summed("physical_charger_exits"),
        "low_energy_seek_entries": summed("low_energy_seek_entries"),
        "physical_reacquisitions": summed("physical_reacquisitions"),
        "full_recharge_events": summed("full_recharge_events"),
        "post_recharge_redepartures": summed("post_recharge_redepartures"),
        "completed_energy_regulation_cycles": summed(
            "completed_energy_regulation_cycles"
        ),
        "minimum_normalized_energy": min(
            cast(float, result["minimum_normalized_energy"]) for result in results
        ),
        "maximum_normalized_energy": max(
            cast(float, result["maximum_normalized_energy"]) for result in results
        ),
        "maximum_temperature": max(
            cast(float, result["maximum_temperature"]) for result in results
        ),
        "termination_reason_counts": {
            reason: sum(
                int(result["termination_reason"] == reason) for result in results
            )
            for reason in (
                "horizon_truncation",
                "energy_depletion",
                "protective_thermal_shutdown",
                "emergency_hard_thermal_shutdown",
            )
        },
    }


def _run_d027_seed(seed: int, *, horizon: int = D027_HORIZON) -> dict[str, object]:
    _validate_d027_seed(seed)
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon <= 0:
        raise ValueError("horizon must be a positive integer")
    result, _ = _run_lifetime(seed, horizon=horizon, learning=True)
    reference, _ = _run_lifetime(seed, horizon=horizon, learning=False)
    result["shadow_isolation"] = {
        "reference": "identical D-026 controller/environment replay without learner",
        "trajectory_digest": result["trajectory_digest"],
        "reference_trajectory_digest": reference["trajectory_digest"],
        "trajectory_exact_equal": result["trajectory_digest"]
        == reference["trajectory_digest"],
        "behavioral_summary_exact_equal": all(
            result[name] == reference[name]
            for name in (
                "transitions",
                "terminated",
                "truncated",
                "termination_reason",
                "action_counts",
                "mode_occupancy",
                "mode_entry_counts",
                "final_mode",
                "minimum_normalized_energy",
                "final_normalized_energy",
                "maximum_normalized_energy",
                "minimum_temperature",
                "final_temperature",
                "maximum_temperature",
                "full_departures",
                "physical_charger_exits",
                "low_energy_seek_entries",
                "physical_reacquisitions",
                "full_recharge_events",
                "post_recharge_redepartures",
                "completed_energy_regulation_cycles",
            )
        ),
    }
    result.pop("learner")
    return result


def run_d027_probe(
    seeds: Sequence[int] = D027_DEFAULT_DEVELOPMENT_SEEDS,
    *,
    horizon: int = D027_HORIZON,
    executed_commit_sha: str | None = None,
) -> dict[str, object]:
    development_seeds = _validate_d027_development_seeds(seeds)
    if horizon != D027_HORIZON:
        raise ValueError("D-027 requires the frozen 70,000-transition horizon")
    executed_sha = _validate_executed_commit_sha(executed_commit_sha)
    results = [_run_d027_seed(seed, horizon=horizon) for seed in development_seeds]
    pooled_metrics, pooled_boundary = _merge_states(results)
    for result in results:
        result.pop("_metric_state")
        result.pop("_boundary_state")
    return {
        "schema_version": 1,
        "experiment": "D-027",
        "title": "Shadow sensorimotor consequence learning",
        "authoritative_base_sha": D027_AUTHORITATIVE_BASE_SHA,
        "implementation_probe_sha": executed_sha,
        "development_seeds": list(development_seeds),
        "horizon": D027_HORIZON,
        "lifetime": "one uninterrupted causal lifetime per seed",
        "seed_policy": {
            "canonical_validator": "validate_exp003_development_seeds",
            "exact_declared_seeds": list(D027_DEFAULT_DEVELOPMENT_SEEDS),
            "formal_reservation_guard_preserved": True,
        },
        "freeze": {
            "controller": "unchanged D026Controller at delegation probability 1/3",
            "environment": "unchanged D026Env / D024 finite-body dual-contact physics",
            "horizon": D027_HORIZON,
            "features": list(D027_CHANNELS),
            "feature_vector": ["bias=1.0", *D027_CHANNELS],
            "outputs": list(D027_OUTPUTS),
            "learning_rate": D027_LEARNING_RATE,
            "plastic_state_dimension": D027_PLASTIC_STATE_DIMENSION,
            "boundary_tolerance": D027_BOUNDARY_TOLERANCE,
            "nominal_move_distance": D027_NOMINAL_MOVE_DISTANCE,
        },
        "causal_order": [
            "current visible state",
            "unchanged D-026 action",
            "pre-update prediction",
            "real environment step",
            "next visible state",
            "learner update",
            "evaluator diagnostics",
        ],
        "programmed": {
            "actions": [action.name for action in Action],
            "d026_behavior_unchanged": True,
            "model_guided_action": False,
            "counterfactual_action_queries": False,
            "forced_actions": False,
            "reward_driven": False,
        },
        "organism_visible": {
            "observation_type": "D026Observation / six ordinary D-024 channels",
            "channels": list(D027_CHANNELS),
            "learner_inputs": [
                "current six channels",
                "own executed action",
                "actual next six channels",
            ],
            "evaluator_state_as_input": False,
        },
        "learner": {
            "type": "action-conditioned linear one-step visible-delta predictor",
            "actions": [action.name for action in Action],
            "outputs": list(D027_OUTPUTS),
            "feature_dimension": D027_FEATURE_DIMENSION,
            "learning_rate": D027_LEARNING_RATE,
            "initial_weights": 0.0,
            "update": (
                "weights += 0.5 * (observed_delta - dot(weights, x)) * x / dot(x, x)"
            ),
            "prediction_scored_before_update": True,
            "executed_action_only": True,
            "plastic_state_dimension": D027_PLASTIC_STATE_DIMENSION,
            "plastic_state_order": "action, output, feature",
            "extra_plastic_state": False,
            "rng": False,
            "history": False,
            "optimizer_state": False,
            "buffer": False,
            "reset": "168 weights zero at deliberate new-lifetime start only",
        },
        "evaluator_only": {
            "boundary_labels": [
                "FULL_NOMINAL_FORWARD",
                "BOUNDARY_CLIPPED_FORWARD",
                "FULL_STALL_FORWARD",
            ],
            "boundary_definition": (
                "realized centre displacement with tolerance 1e-12; stall is <=1e-12"
            ),
            "zero_change_comparator": True,
            "pose_displacement_labels_passed_to_learner": False,
            "prediction_causal_effect_on_behavior": False,
        },
        "organism_boundary": {"reward": 0.0, "info": {}},
        "pooled_behavior": _pooled_behavior(results),
        "pooled_prediction_metrics": _metric_state_dict(pooled_metrics),
        "pooled_boundary_metrics": {
            category: {
                "overall": values["overall"].as_dict(),
                "Q4": values["Q4"].as_dict(),
            }
            for category, values in pooled_boundary.items()
        },
        "results": results,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the D-027 shadow learner probe.")
    parser.add_argument(
        "--seeds", type=int, nargs="+", default=list(D027_DEFAULT_DEVELOPMENT_SEEDS)
    )
    parser.add_argument("--horizon", type=int, default=D027_HORIZON)
    parser.add_argument("--executed-commit-sha")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    payload = json.dumps(
        run_d027_probe(
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
        print(f"D-027 result written to {args.output}")


if __name__ == "__main__":
    main()
