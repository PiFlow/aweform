"""D-028 evaluator-only residual-attribution audit.

This module replays the unchanged D-027 causal lifetime and performs all new
work after each completed replay from its evaluator trace.  The alias census,
batch regressions, geometry reconstruction, and privileged oracles therefore
have no path to the D-027 controller, learner, RNG, or environment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Sequence, cast

import numpy as np

from . import d016, d024, d025, d026, d027
from .body import Body
from .d020 import D020PhysicalConfig
from .env import Action
from .exp003 import beacon_signal, sample_directional_beacon
from .exp003_seed_policy import validate_exp003_development_seeds
from .rng import RandomStreams

D028_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = tuple(range(18388, 18408))
D028_HORIZON: Final[int] = 70_000
D028_AUTHORITATIVE_BASE_SHA: Final[str] = "19cb4ebd8c6f2df7013865087689cff3d3803a33"
D028_D027_ARTIFACT_SHA256: Final[str] = (
    "4433e5abee35c1d6fbf58d266c8d486bdfb34fcf07e7b38bf379f2968143bf52"
)
D028_LINEAR_FEATURE_DIMENSION: Final[int] = 7
D028_QUADRATIC_FEATURE_DIMENSION: Final[int] = 28
D028_BOUNDARY_TOLERANCE: Final[float] = d027.D027_BOUNDARY_TOLERANCE
D028_GEOMETRY_TOLERANCE: Final[float] = d016.D016_GEOMETRY_NUMERICAL_TOLERANCE
D028_BOUNDARY_LABELS: Final[tuple[str, ...]] = (
    "FULL_NOMINAL_FORWARD",
    "BOUNDARY_CLIPPED_FORWARD",
    "FULL_STALL_FORWARD",
)
D028_PARITY_FOLDS: Final[dict[str, tuple[int, ...]]] = {
    "EVEN": tuple(range(18388, 18408, 2)),
    "ODD": tuple(range(18389, 18408, 2)),
}

if tuple(sorted(D028_PARITY_FOLDS["EVEN"] + D028_PARITY_FOLDS["ODD"])) != (
    D028_DEFAULT_DEVELOPMENT_SEEDS
):
    raise RuntimeError("D-028 parity folds no longer cover the exact seed block")


def _reference_artifact_path() -> Path:
    return Path(__file__).resolve().parents[2] / (
        "development/D-027-shadow-sensorimotor-consequence-learning.json"
    )


def _validate_d028_development_seeds(
    seeds: Sequence[int],
) -> tuple[int, ...]:
    validated = validate_exp003_development_seeds(seeds)
    if validated != D028_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-028 requires exactly the frozen development seeds "
            f"{D028_DEFAULT_DEVELOPMENT_SEEDS}; got {validated}"
        )
    return validated


def _validate_d028_seed(seed: int) -> None:
    validated = validate_exp003_development_seeds((seed,))
    if validated[0] not in D028_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-028 may execute only the frozen D-027 development seeds "
            f"{D028_DEFAULT_DEVELOPMENT_SEEDS}; got {validated}"
        )


def _validate_executed_commit_sha(value: str | None) -> str | None:
    if value is None:
        return None
    if len(value) != 40 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise ValueError("executed_commit_sha must be a 40-character lowercase SHA")
    return value


def _linear_features(values: np.ndarray) -> np.ndarray:
    if values.ndim != 2 or values.shape[1] != 6:
        raise ValueError("visible values must have shape (rows, 6)")
    result = np.empty((values.shape[0], D028_LINEAR_FEATURE_DIMENSION), dtype=float)
    result[:, 0] = 1.0
    result[:, 1:] = values
    return result


def quadratic_features(
    values: Sequence[float] | np.ndarray,
) -> tuple[float, ...] | np.ndarray:
    """Return the frozen bias, six linear, and 21 lexicographic products."""
    array = np.asarray(values, dtype=float)
    if array.ndim == 1:
        if array.shape != (6,):
            raise ValueError("one visible value must contain six channels")
        result: list[float] = [1.0, *[float(value) for value in array]]
        for left in range(6):
            for right in range(left, 6):
                result.append(float(array[left] * array[right]))
        if len(result) != D028_QUADRATIC_FEATURE_DIMENSION:
            raise RuntimeError("quadratic basis dimension changed")
        return tuple(result)
    if array.ndim != 2 or array.shape[1] != 6:
        raise ValueError("visible values must have shape (rows, 6)")
    result_array = np.empty(
        (array.shape[0], D028_QUADRATIC_FEATURE_DIMENSION), dtype=float
    )
    result_array[:, 0] = 1.0
    result_array[:, 1:7] = array
    column = 7
    for left in range(6):
        for right in range(left, 6):
            result_array[:, column] = array[:, left] * array[:, right]
            column += 1
    return result_array


def _metric_dict(targets: Sequence[float], count: int) -> dict[str, object]:
    if count == 0:
        return {"status": "untested", "sample_count": 0, "targets": {}}
    return {
        "status": "visited",
        "sample_count": count,
        "targets": {
            target: {"mae": float(value) / count}
            for target, value in zip(d027.D027_OUTPUTS, targets, strict=True)
        },
    }


@dataclass(slots=True)
class _MetricSums:
    count: int = 0
    absolute_errors: list[float] = field(
        default_factory=lambda: [0.0] * len(d027.D027_OUTPUTS)
    )

    def add(self, predictions: np.ndarray, targets: np.ndarray) -> None:
        if predictions.shape != targets.shape or predictions.ndim != 2:
            raise ValueError(
                "prediction and target arrays must have equal rank-2 shapes"
            )
        if predictions.shape[1] != len(d027.D027_OUTPUTS):
            raise ValueError("prediction and target arrays must contain six outputs")
        self.count += int(predictions.shape[0])
        errors = np.abs(predictions - targets).sum(axis=0)
        self.absolute_errors = [
            old + float(new)
            for old, new in zip(self.absolute_errors, errors, strict=True)
        ]

    def merge(self, other: _MetricSums) -> None:
        self.count += other.count
        self.absolute_errors = [
            left + right
            for left, right in zip(
                self.absolute_errors, other.absolute_errors, strict=True
            )
        ]

    def as_dict(self) -> dict[str, object]:
        return _metric_dict(self.absolute_errors, self.count)


@dataclass(slots=True)
class _Metrics:
    overall: _MetricSums = field(default_factory=_MetricSums)
    by_action: dict[str, _MetricSums] = field(
        default_factory=lambda: {action.name: _MetricSums() for action in Action}
    )
    by_quarter: dict[str, _MetricSums] = field(
        default_factory=lambda: {f"Q{index}": _MetricSums() for index in range(1, 5)}
    )
    boundary: dict[str, _MetricSums] = field(
        default_factory=lambda: {label: _MetricSums() for label in D028_BOUNDARY_LABELS}
    )
    boundary_by_quarter: dict[str, dict[str, _MetricSums]] = field(
        default_factory=lambda: {
            label: {f"Q{index}": _MetricSums() for index in range(1, 5)}
            for label in D028_BOUNDARY_LABELS
        }
    )
    contact_delta: dict[str, _MetricSums] = field(
        default_factory=lambda: {
            "-1": _MetricSums(),
            "0": _MetricSums(),
            "+1": _MetricSums(),
        }
    )

    def add(
        self,
        action: Action,
        predictions: np.ndarray,
        targets: np.ndarray,
        quarters: np.ndarray,
        boundary_codes: np.ndarray,
        contact_codes: np.ndarray,
    ) -> None:
        if not (
            len(predictions)
            == len(targets)
            == len(quarters)
            == len(boundary_codes)
            == len(contact_codes)
        ):
            raise ValueError("metric metadata lengths do not match predictions")
        self.overall.add(predictions, targets)
        self.by_action[action.name].add(predictions, targets)
        for quarter in range(4):
            mask = quarters == quarter
            self.by_quarter[f"Q{quarter + 1}"].add(predictions[mask], targets[mask])
        if action is Action.MOVE_FORWARD:
            for code, label in (
                (1, "FULL_NOMINAL_FORWARD"),
                (2, "BOUNDARY_CLIPPED_FORWARD"),
                (3, "FULL_STALL_FORWARD"),
            ):
                mask = boundary_codes == code
                self.boundary[label].add(predictions[mask], targets[mask])
                for quarter in range(4):
                    mask = (boundary_codes == code) & (quarters == quarter)
                    self.boundary_by_quarter[label][f"Q{quarter + 1}"].add(
                        predictions[mask], targets[mask]
                    )
        for code, label in ((-1, "-1"), (0, "0"), (1, "+1")):
            mask = contact_codes == code
            self.contact_delta[label].add(predictions[mask], targets[mask])

    def merge(self, other: _Metrics) -> None:
        self.overall.merge(other.overall)
        for name in self.by_action:
            self.by_action[name].merge(other.by_action[name])
        for name in self.by_quarter:
            self.by_quarter[name].merge(other.by_quarter[name])
        for name in self.boundary:
            self.boundary[name].merge(other.boundary[name])
            for quarter in self.boundary_by_quarter[name]:
                self.boundary_by_quarter[name][quarter].merge(
                    other.boundary_by_quarter[name][quarter]
                )
        for name in self.contact_delta:
            self.contact_delta[name].merge(other.contact_delta[name])

    def as_dict(self) -> dict[str, object]:
        return {
            "overall": self.overall.as_dict(),
            "by_action": {
                name: value.as_dict() for name, value in self.by_action.items()
            },
            "by_quarter": {
                name: value.as_dict() for name, value in self.by_quarter.items()
            },
            "move_forward_boundary": {
                name: {
                    "overall": self.boundary[name].as_dict(),
                    "by_quarter": {
                        quarter: value.as_dict()
                        for quarter, value in self.boundary_by_quarter[name].items()
                    },
                }
                for name in self.boundary
            },
            "charging_contact_delta": {
                name: value.as_dict() for name, value in self.contact_delta.items()
            },
        }


@dataclass(slots=True)
class _AliasRecord:
    outcomes: dict[tuple[float, ...], int] = field(default_factory=dict)


VisibleKey = tuple[float, float, float, float, float, float, str]


def _record_alias(
    aliases: dict[VisibleKey, _AliasRecord],
    key: VisibleKey,
    outcome: tuple[float, ...],
) -> None:
    record = aliases.setdefault(key, _AliasRecord())
    record.outcomes[outcome] = record.outcomes.get(outcome, 0) + 1


def _merge_aliases(
    target: dict[VisibleKey, _AliasRecord],
    source: dict[VisibleKey, _AliasRecord],
) -> None:
    for key, source_record in source.items():
        target_record = target.setdefault(key, _AliasRecord())
        for outcome, count in source_record.outcomes.items():
            target_record.outcomes[outcome] = (
                target_record.outcomes.get(outcome, 0) + count
            )


def alias_census(
    aliases: dict[VisibleKey, _AliasRecord],
) -> dict[str, object]:
    """Summarize exact visible-key/action records; singletons stay untested."""
    transitions = sum(sum(record.outcomes.values()) for record in aliases.values())
    repeated = {
        key: record
        for key, record in aliases.items()
        if sum(record.outcomes.values()) >= 2
    }
    singleton_count = len(aliases) - len(repeated)
    aliased = {
        key: record for key, record in repeated.items() if len(record.outcomes) > 1
    }
    records: list[dict[str, object]] = []
    for key in sorted(aliased, key=lambda value: tuple(str(item) for item in value)):
        record = aliases[key]
        count = sum(record.outcomes.values())
        key_values = key[:6]
        record_payload: dict[str, object] = {
            "energy": key_values[0],
            "beacon_left": key_values[1],
            "beacon_forward": key_values[2],
            "beacon_right": key_values[3],
            "charging_contact": bool(key_values[4]),
            "thermal": key_values[5],
            "executed_action": key[6],
            "sample_count": count,
            "repeated": count >= 2,
            "aliasing_status": (
                "untested"
                if count == 1
                else "aliased"
                if len(record.outcomes) > 1
                else "no_alias"
            ),
            "next_visible_outcomes": [
                {"delta": list(outcome), "count": outcome_count}
                for outcome, outcome_count in sorted(record.outcomes.items())
            ],
        }
        records.append(record_payload)
    repeated_transitions = sum(
        sum(record.outcomes.values()) for record in repeated.values()
    )
    return {
        "key_definition": (
            "exact Python floats from the six float32 visible channels plus "
            "the exact executed action; no rounding or hidden state"
        ),
        "next_visible_consequence": "exact six-channel delta",
        "transitions": transitions,
        "unique_keys": len(aliases),
        "repeated_keys": len(repeated),
        "singleton_keys": singleton_count,
        "transitions_in_repeated_keys": repeated_transitions,
        "repeated_key_coverage": (
            repeated_transitions / transitions if transitions else None
        ),
        "aliased_repeated_keys": len(aliased),
        "serialized_record_scope": "aliased_repeated_keys_only",
        "omitted_non_aliased_key_records": len(aliases) - len(aliased),
        "records": records,
    }


@dataclass(slots=True)
class _SeedRows:
    seed: int
    current: dict[Action, np.ndarray]
    target: dict[Action, np.ndarray]
    online: dict[Action, np.ndarray]
    quarters: dict[Action, np.ndarray]
    boundary_codes: dict[Action, np.ndarray]
    contact_codes: dict[Action, np.ndarray]


def _boundary_code(action: Action, displacement: float) -> int:
    if action is not Action.MOVE_FORWARD:
        return 0
    label = d027._classify_forward_displacement(displacement)
    if displacement <= D028_BOUNDARY_TOLERANCE:
        return 3
    return 1 if label == "FULL_NOMINAL_FORWARD" else 2


def _contact_code(current: bool, next_value: bool) -> int:
    if current and not next_value:
        return -1
    if not current and next_value:
        return 1
    return 0


def _beacon_from_relative(
    geometry: d016.RelativeGeometry, config: D020PhysicalConfig
) -> tuple[float, float, float]:
    angles = (config.sensor_angle, 0.0, -config.sensor_angle)
    signals = tuple(
        beacon_signal(
            math.hypot(
                geometry.x - config.probe_distance * math.cos(angle),
                geometry.y - config.probe_distance * math.sin(angle),
            ),
            config.beacon_scale,
        )
        for angle in angles
    )
    return cast(tuple[float, float, float], signals)


def _rotate(vector: tuple[float, float], heading: float) -> tuple[float, float]:
    return (
        vector[0] * math.cos(heading) - vector[1] * math.sin(heading),
        vector[0] * math.sin(heading) + vector[1] * math.cos(heading),
    )


def _pose_from_relative(
    geometry: d016.RelativeGeometry,
    heading: float,
    station: tuple[float, float],
) -> tuple[float, float]:
    station_vector = _rotate((geometry.x, geometry.y), heading)
    return station[0] - station_vector[0], station[1] - station_vector[1]


def _apply_known_action(
    position: tuple[float, float],
    heading: float,
    action: Action,
    config: D020PhysicalConfig,
) -> tuple[tuple[float, float], float, float]:
    next_heading = heading
    if action is Action.TURN_LEFT:
        next_heading = (heading + config.turn_angle) % math.tau
    elif action is Action.TURN_RIGHT:
        next_heading = (heading - config.turn_angle) % math.tau
    proposed = position
    if action is Action.MOVE_FORWARD:
        proposed = (
            position[0] + config.movement_distance_world_units * math.cos(heading),
            position[1] + config.movement_distance_world_units * math.sin(heading),
        )
        proposed = (
            min(config.world_max[0], max(config.world_min[0], proposed[0])),
            min(config.world_max[1], max(config.world_min[1], proposed[1])),
        )
    return proposed, next_heading, math.dist(position, proposed)


@dataclass(slots=True)
class _VectorStats:
    count: int = 0
    sums: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    maxima: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])

    def add(self, values: Sequence[float]) -> None:
        self.count += 1
        self.sums = [
            total + abs(float(value))
            for total, value in zip(self.sums, values, strict=True)
        ]
        self.maxima = [
            max(current, abs(float(value)))
            for current, value in zip(self.maxima, values, strict=True)
        ]

    def merge(self, other: _VectorStats) -> None:
        self.count += other.count
        self.sums = [
            left + right for left, right in zip(self.sums, other.sums, strict=True)
        ]
        self.maxima = [
            max(left, right)
            for left, right in zip(self.maxima, other.maxima, strict=True)
        ]

    def as_dict(self, names: Sequence[str]) -> dict[str, object]:
        if not self.count:
            return {"status": "untested", "sample_count": 0}
        return {
            "status": "visited",
            "sample_count": self.count,
            "mean_absolute_error": {
                name: total / self.count
                for name, total in zip(names, self.sums, strict=True)
            },
            "max_absolute_error": {
                name: maximum for name, maximum in zip(names, self.maxima, strict=True)
            },
        }


@dataclass(slots=True)
class _OracleStats:
    beacon_error: _VectorStats = field(default_factory=_VectorStats)
    contact_count: int = 0
    contact_errors: int = 0
    boundary_actual: dict[str, int] = field(
        default_factory=lambda: {label: 0 for label in D028_BOUNDARY_LABELS}
    )
    boundary_predicted: dict[str, int] = field(
        default_factory=lambda: {label: 0 for label in D028_BOUNDARY_LABELS}
    )
    boundary_confusion: dict[str, dict[str, int]] = field(default_factory=dict)
    displacement_count: int = 0
    displacement_absolute_error: float = 0.0
    displacement_max_absolute_error: float = 0.0

    def add_beacon(self, prediction: Sequence[float], actual: Sequence[float]) -> None:
        self.beacon_error.add(
            [
                predicted - observed
                for predicted, observed in zip(prediction, actual, strict=True)
            ]
        )

    def add_contact(self, predicted: bool, actual: bool) -> None:
        self.contact_count += 1
        self.contact_errors += int(predicted != actual)

    def add_boundary(self, predicted: str, actual: str) -> None:
        self.boundary_predicted[predicted] += 1
        self.boundary_actual[actual] += 1
        self.boundary_confusion.setdefault(
            actual, {label: 0 for label in D028_BOUNDARY_LABELS}
        )[predicted] += 1

    def add_displacement(self, predicted: float, actual: float) -> None:
        error = abs(predicted - actual)
        self.displacement_count += 1
        self.displacement_absolute_error += error
        self.displacement_max_absolute_error = max(
            self.displacement_max_absolute_error, error
        )

    def merge(self, other: _OracleStats) -> None:
        self.beacon_error.count += other.beacon_error.count
        self.beacon_error.sums = [
            left + right
            for left, right in zip(
                self.beacon_error.sums, other.beacon_error.sums, strict=True
            )
        ]
        self.beacon_error.maxima = [
            max(left, right)
            for left, right in zip(
                self.beacon_error.maxima, other.beacon_error.maxima, strict=True
            )
        ]
        self.contact_count += other.contact_count
        self.contact_errors += other.contact_errors
        for label in D028_BOUNDARY_LABELS:
            self.boundary_actual[label] += other.boundary_actual[label]
            self.boundary_predicted[label] += other.boundary_predicted[label]
        for actual, row in other.boundary_confusion.items():
            target_row = self.boundary_confusion.setdefault(
                actual, {label: 0 for label in D028_BOUNDARY_LABELS}
            )
            for predicted, count in row.items():
                target_row[predicted] += count
        self.displacement_count += other.displacement_count
        self.displacement_absolute_error += other.displacement_absolute_error
        self.displacement_max_absolute_error = max(
            self.displacement_max_absolute_error,
            other.displacement_max_absolute_error,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "beacon_mae": self.beacon_error.as_dict(
                ("beacon.left", "beacon.forward", "beacon.right")
            ),
            "charging_contact": {
                "sample_count": self.contact_count,
                "errors": self.contact_errors,
                "error_rate": (
                    self.contact_errors / self.contact_count
                    if self.contact_count
                    else None
                ),
                "exact_agreement": self.contact_count - self.contact_errors,
            },
            "predicted_boundary_counts": self.boundary_predicted,
            "actual_boundary_counts": self.boundary_actual,
            "boundary_confusion": self.boundary_confusion,
            "realized_displacement": {
                "sample_count": self.displacement_count,
                "mean_absolute_error": (
                    self.displacement_absolute_error / self.displacement_count
                    if self.displacement_count
                    else None
                ),
                "max_absolute_error": self.displacement_max_absolute_error,
            },
        }


def _actual_boundary_label(code: int) -> str:
    return D028_BOUNDARY_LABELS[code - 1]


def _load_d027_artifact() -> dict[int, dict[str, object]]:
    path = _reference_artifact_path()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != D028_D027_ARTIFACT_SHA256:
        raise RuntimeError(
            "D-027 reference artifact SHA-256 changed; refusing D-028 replay"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    results = cast(list[dict[str, object]], payload["results"])
    return {cast(int, result["seed"]): result for result in results}


def _weight_digest(weights: object) -> str:
    encoded = json.dumps(weights, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _policy_rng_digest(seed: int, trace: Sequence[d025.D025TransitionTrace]) -> str:
    """Replay the exact D-026 policy decisions and hash the final RNG state."""
    streams = RandomStreams.from_seed(seed)
    controller = d026.D026Controller(streams.policy)
    controller.reset()
    for record in trace:
        current = d025._controller_observation(
            np.asarray(record.observation_before, dtype=np.float32)
        )
        if controller.mode is not record.mode_before:
            raise RuntimeError(f"D-027 policy mode replay failed for seed {seed}")
        action = controller.act(current)
        if action is not record.action or controller.mode is not record.mode_after:
            raise RuntimeError(f"D-027 policy action replay failed for seed {seed}")
    state = d027._jsonable(streams.policy.bit_generator.state)
    encoded = json.dumps(state, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _evaluator_integer(result: dict[str, object], name: str) -> int:
    evaluator = cast(dict[str, object], result["evaluator"])
    return cast(int, evaluator[name])


def _alias_by_action(
    aliases: dict[VisibleKey, _AliasRecord],
) -> dict[str, dict[str, object]]:
    return {
        action.name: alias_census(
            {key: record for key, record in aliases.items() if key[6] == action.name}
        )
        for action in Action
    }


def _replay_seed(
    seed: int, reference: dict[str, object]
) -> tuple[dict[str, object], _SeedRows, dict[str, object]]:
    """Replay D-027, then calculate all per-seed evaluator-only raw summaries."""
    _validate_d028_seed(seed)
    learned_result, raw_trace = d027._run_lifetime(
        seed, horizon=D028_HORIZON, learning=True
    )
    reference_result, raw_reference_trace = d027._run_lifetime(
        seed, horizon=D028_HORIZON, learning=False
    )
    trace = cast(list[d025.D025TransitionTrace], raw_trace)
    reference_trace = cast(list[d025.D025TransitionTrace], raw_reference_trace)
    if learned_result["trajectory_digest"] != reference_result["trajectory_digest"]:
        raise RuntimeError(f"D-027 trajectory isolation failed for seed {seed}")
    if learned_result["final_weights"] is None:
        raise RuntimeError("D-027 replay did not retain final weights")
    comparable = (
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
    if any(learned_result[name] != reference_result[name] for name in comparable):
        raise RuntimeError(f"D-027 behavioral isolation failed for seed {seed}")
    if len(trace) != len(reference_trace):
        raise RuntimeError(f"D-027 trace length isolation failed for seed {seed}")
    expected_digest = reference.get("trajectory_digest")
    expected_weights = reference.get("final_weights")
    if learned_result["trajectory_digest"] != expected_digest:
        raise RuntimeError(f"D-027 artifact trajectory mismatch for seed {seed}")
    if learned_result["final_weights"] != expected_weights:
        raise RuntimeError(f"D-027 artifact final-weight mismatch for seed {seed}")
    learned_policy_rng_digest = _policy_rng_digest(seed, trace)
    reference_policy_rng_digest = _policy_rng_digest(seed, reference_trace)
    if learned_policy_rng_digest != reference_policy_rng_digest:
        raise RuntimeError(f"D-027 policy RNG isolation failed for seed {seed}")

    current_lists: dict[Action, list[tuple[float, ...]]] = {
        action: [] for action in Action
    }
    target_lists: dict[Action, list[tuple[float, ...]]] = {
        action: [] for action in Action
    }
    online_lists: dict[Action, list[tuple[float, ...]]] = {
        action: [] for action in Action
    }
    quarter_lists: dict[Action, list[int]] = {action: [] for action in Action}
    boundary_lists: dict[Action, list[int]] = {action: [] for action in Action}
    contact_lists: dict[Action, list[int]] = {action: [] for action in Action}
    online_metrics = _Metrics()
    zero_metrics = _Metrics()
    aliases: dict[VisibleKey, _AliasRecord] = {}
    geometry_error = _VectorStats()
    nominal_oracles = {label: _OracleStats() for label in D028_BOUNDARY_LABELS}
    wall_oracle = _OracleStats()
    geometry_consistency_failures = 0
    oracle_consistency_failures = 0
    heading_before = d024.D024_INITIAL_HEADING
    config = D020PhysicalConfig(episode_horizon=D028_HORIZON)
    replay_predictor = d027.D027ActionConsequencePredictor()
    for trace_record in trace:
        current_values = tuple(
            float(value) for value in trace_record.observation_before
        )
        next_values = tuple(float(value) for value in trace_record.observation)
        action = trace_record.action
        current = d025._controller_observation(
            np.asarray(current_values, dtype=np.float32)
        )
        next_visible = d025._controller_observation(
            np.asarray(next_values, dtype=np.float32)
        )
        # Reconstruct the exact D-027 online sequence from the completed trace.
        prediction = replay_predictor.predict(current, action)
        observed = tuple(
            next_value - current_value
            for next_value, current_value in zip(
                next_values, current_values, strict=True
            )
        )
        update = replay_predictor.observe_transition(current, action, next_visible)
        if update.observed_delta != observed or update.prediction != prediction.values:
            raise RuntimeError(f"D-027 predictor reconstruction failed for seed {seed}")
        displacement = math.dist(
            trace_record.telemetry.position_before,
            trace_record.telemetry.position_after,
        )
        boundary_code = _boundary_code(action, displacement)
        contact_code = _contact_code(bool(current_values[4]), bool(next_values[4]))
        transition_index = trace_record.transition_index
        quarter = (transition_index - 1) // (D028_HORIZON // 4)
        if quarter not in range(4):
            raise RuntimeError(
                "D-028 quarter classifier received an invalid transition"
            )
        target_array = np.asarray([observed], dtype=float)
        online_array = np.asarray([prediction.values], dtype=float)
        zero_array = np.zeros_like(target_array)
        online_metrics.add(
            action,
            online_array,
            target_array,
            np.asarray([quarter]),
            np.asarray([boundary_code]),
            np.asarray([contact_code]),
        )
        zero_metrics.add(
            action,
            zero_array,
            target_array,
            np.asarray([quarter]),
            np.asarray([boundary_code]),
            np.asarray([contact_code]),
        )
        key = (
            current_values[0],
            current_values[1],
            current_values[2],
            current_values[3],
            current_values[4],
            current_values[5],
            action.name,
        )
        _record_alias(aliases, key, observed)

        beacon = current.beacon
        decoded = d016.reconstruct_relative_geometry(
            beacon,
            beacon_scale=config.beacon_scale,
            probe_distance=config.probe_distance,
            sensor_angle=config.sensor_angle,
        )
        actual_geometry = d016._world_to_body_frame(  # evaluator-only scoring transform
            trace_record.telemetry.position_before,
            trace_record.telemetry.station_center,
            heading_before,
        )
        geometry_differences = (
            decoded.x - actual_geometry.x,
            decoded.y - actual_geometry.y,
            decoded.radial_distance - actual_geometry.radial_distance,
        )
        geometry_error.add(geometry_differences)
        if (
            max(abs(value) for value in geometry_differences[:2])
            > D028_GEOMETRY_TOLERANCE
        ):
            geometry_consistency_failures += 1

        if action is Action.MOVE_FORWARD:
            nominal_geometry = d016.RelativeGeometry(
                decoded.x - config.movement_distance_world_units, decoded.y
            )
            nominal_beacon = _beacon_from_relative(nominal_geometry, config)
            actual_beacon = next_values[1:4]
            nominal_label = _actual_boundary_label(boundary_code)
            nominal_oracles[nominal_label].add_beacon(nominal_beacon, actual_beacon)

        current_pose = _pose_from_relative(
            decoded, heading_before, trace_record.telemetry.station_center
        )
        predicted_pose, predicted_heading, predicted_displacement = _apply_known_action(
            current_pose, heading_before, action, config
        )
        predicted_body = Body(
            predicted_pose[0], predicted_pose[1], predicted_heading, energy=0.0
        )
        predicted_beacon_observation = sample_directional_beacon(
            predicted_body,
            trace_record.telemetry.station_center,
            probe_distance=config.probe_distance,
            sensor_angle=config.sensor_angle,
            beacon_scale=config.beacon_scale,
        )
        predicted_contact = d024.has_dual_contact(
            predicted_pose, predicted_heading, trace_record.telemetry.station_center
        )
        wall_oracle.add_beacon(
            predicted_beacon_observation.as_tuple(), next_values[1:4]
        )
        wall_oracle.add_contact(predicted_contact, bool(next_values[4]))
        if action is Action.MOVE_FORWARD:
            predicted_code = _boundary_code(action, predicted_displacement)
            wall_oracle.add_boundary(
                _actual_boundary_label(predicted_code),
                _actual_boundary_label(boundary_code),
            )
            actual_pose_displacement = displacement
            wall_oracle.add_displacement(
                predicted_displacement, actual_pose_displacement
            )
            if (
                abs(predicted_displacement - actual_pose_displacement)
                > D028_GEOMETRY_TOLERANCE
            ):
                oracle_consistency_failures += 1
        heading_before = trace_record.telemetry.heading

        current_lists[action].append(current_values)
        target_lists[action].append(observed)
        online_lists[action].append(prediction.values)
        quarter_lists[action].append(quarter)
        boundary_lists[action].append(boundary_code)
        contact_lists[action].append(contact_code)
    if not trace:
        raise RuntimeError(f"D-027 replay produced no trace for seed {seed}")
    if replay_predictor.weight_snapshot() != learned_result["final_weights"]:
        raise RuntimeError(f"D-027 final-weight replay failed for seed {seed}")
    rows = _SeedRows(
        seed=seed,
        current={
            action: np.asarray(current_lists[action], dtype=float) for action in Action
        },
        target={
            action: np.asarray(target_lists[action], dtype=float) for action in Action
        },
        online={
            action: np.asarray(online_lists[action], dtype=float) for action in Action
        },
        quarters={
            action: np.asarray(quarter_lists[action], dtype=np.int8)
            for action in Action
        },
        boundary_codes={
            action: np.asarray(boundary_lists[action], dtype=np.int8)
            for action in Action
        },
        contact_codes={
            action: np.asarray(contact_lists[action], dtype=np.int8)
            for action in Action
        },
    )
    for action in Action:
        expected_count = int(
            cast(dict[str, int], learned_result["action_counts"])[action.name]
        )
        if len(rows.current[action]) != expected_count:
            raise RuntimeError(
                f"D-028 row support mismatch for seed {seed}, {action.name}"
            )
    evaluator = {
        "support": {
            "transitions": len(trace),
            "all_four_actions_visited": all(
                len(rows.current[action]) > 0 for action in Action
            ),
            "action_counts": {
                action.name: len(rows.current[action]) for action in Action
            },
            "contact_delta_counts": {
                label: int(
                    np.count_nonzero(
                        np.concatenate(list(rows.contact_codes.values())) == code
                    )
                )
                for label, code in (("-1", -1), ("0", 0), ("+1", 1))
            },
            "move_forward_boundary_counts": {
                label: int(
                    np.count_nonzero(rows.boundary_codes[Action.MOVE_FORWARD] == code)
                )
                for label, code in zip(D028_BOUNDARY_LABELS, (1, 2, 3), strict=True)
            },
        },
        "alias_census": alias_census(aliases),
        "alias_census_by_action": _alias_by_action(aliases),
        "geometry_reconstruction": geometry_error.as_dict(("x", "y", "radial")),
        "geometry_consistency_failures": geometry_consistency_failures,
        "nominal_beacon_oracle": {
            label: value.as_dict() for label, value in nominal_oracles.items()
        },
        "heading_augmented_wall_aware_oracle": wall_oracle.as_dict(),
        "oracle_consistency_failures": oracle_consistency_failures,
        "d027_online_metrics": online_metrics.as_dict(),
        "zero_change_metrics": zero_metrics.as_dict(),
    }
    d027_isolation = {
        "trajectory_digest": learned_result["trajectory_digest"],
        "reference_trajectory_digest": reference_result["trajectory_digest"],
        "trajectory_exact_equal": True,
        "behavioral_summary_exact_equal": True,
        "policy_rng_state_digest": learned_policy_rng_digest,
        "reference_policy_rng_state_digest": reference_policy_rng_digest,
        "policy_rng_exact_equal": True,
        "d027_artifact_trajectory_exact_equal": True,
        "d027_artifact_final_weights_exact_equal": True,
        "final_weight_count": len(
            cast(dict[str, dict[str, list[float]]], learned_result["final_weights"])[
                d027.D027_OUTPUTS[0]
            ][Action.WAIT.name]
        ),
        "final_weights_digest": _weight_digest(learned_result["final_weights"]),
    }
    output = {
        "seed": seed,
        "d027_isolation": d027_isolation,
        "behavior": {key: learned_result[key] for key in comparable},
        "final_weights": learned_result["final_weights"],
        "evaluator": evaluator,
    }
    return (
        output,
        rows,
        {
            "aliases": aliases,
            "nominal_oracles": nominal_oracles,
            "wall_oracle": wall_oracle,
            "geometry_error": geometry_error,
        },
    )


@dataclass(slots=True)
class _Fit:
    coefficients: np.ndarray
    rank: int
    singular_values: np.ndarray
    sample_count: int

    def as_dict(self) -> dict[str, object]:
        smallest = float(self.singular_values[-1]) if len(self.singular_values) else 0.0
        largest = float(self.singular_values[0]) if len(self.singular_values) else 0.0
        return {
            "sample_count": self.sample_count,
            "feature_dimension": int(self.coefficients.shape[0]),
            "output_dimension": int(self.coefficients.shape[1]),
            "rank": self.rank,
            "singular_values": [float(value) for value in self.singular_values],
            "condition_number": largest / smallest if smallest else None,
            "coefficients": self.coefficients.tolist(),
        }


def _fit_cross_seed(
    rows: Sequence[_SeedRows],
    train_seeds: frozenset[int],
    quadratic: bool,
) -> dict[Action, _Fit]:
    fits: dict[Action, _Fit] = {}
    for action in Action:
        selected = [row for row in rows if row.seed in train_seeds]
        matrices = [
            quadratic_features(row.current[action])
            if quadratic
            else _linear_features(row.current[action])
            for row in selected
        ]
        x = np.concatenate([cast(np.ndarray, matrix) for matrix in matrices], axis=0)
        y = np.concatenate([row.target[action] for row in selected], axis=0)
        coefficients, _, rank, singular_values = np.linalg.lstsq(x, y, rcond=None)
        fits[action] = _Fit(
            coefficients=coefficients,
            rank=int(rank),
            singular_values=singular_values,
            sample_count=int(x.shape[0]),
        )
    return fits


def _score_fit(
    rows: _SeedRows,
    fits: dict[Action, _Fit],
    quadratic: bool,
) -> _Metrics:
    metrics = _Metrics()
    for action in Action:
        matrix = (
            quadratic_features(rows.current[action])
            if quadratic
            else _linear_features(rows.current[action])
        )
        predictions = cast(np.ndarray, matrix) @ fits[action].coefficients
        metrics.add(
            action,
            predictions,
            rows.target[action],
            rows.quarters[action],
            rows.boundary_codes[action],
            rows.contact_codes[action],
        )
    return metrics


def run_d028_probe(
    seeds: Sequence[int] = D028_DEFAULT_DEVELOPMENT_SEEDS,
    *,
    horizon: int = D028_HORIZON,
    executed_commit_sha: str | None = None,
) -> dict[str, object]:
    """Run the frozen D-028 replay and all evaluator-only diagnostics."""
    development_seeds = _validate_d028_development_seeds(seeds)
    if horizon != D028_HORIZON:
        raise ValueError("D-028 requires the frozen 70,000-transition horizon")
    executed_sha = _validate_executed_commit_sha(executed_commit_sha)
    artifact = _load_d027_artifact()
    per_seed: list[dict[str, object]] = []
    rows: list[_SeedRows] = []
    alias_pooled: dict[VisibleKey, _AliasRecord] = {}
    online_pooled = _Metrics()
    zero_pooled = _Metrics()
    geometry_pooled = _VectorStats()
    nominal_pooled = {label: _OracleStats() for label in D028_BOUNDARY_LABELS}
    wall_pooled = _OracleStats()
    for seed in development_seeds:
        result, seed_rows, typed = _replay_seed(seed, artifact[seed])
        per_seed.append(result)
        rows.append(seed_rows)
        _merge_aliases(
            alias_pooled, cast(dict[VisibleKey, _AliasRecord], typed["aliases"])
        )
        evaluator = cast(dict[str, object], result["evaluator"])
        del evaluator
        # Recreate typed aggregate state from each compact row collection.
        seed_online = _Metrics()
        seed_zero = _Metrics()
        for action in Action:
            seed_online.add(
                action,
                seed_rows.online[action],
                seed_rows.target[action],
                seed_rows.quarters[action],
                seed_rows.boundary_codes[action],
                seed_rows.contact_codes[action],
            )
            seed_zero.add(
                action,
                np.zeros_like(seed_rows.target[action]),
                seed_rows.target[action],
                seed_rows.quarters[action],
                seed_rows.boundary_codes[action],
                seed_rows.contact_codes[action],
            )
        online_pooled.merge(seed_online)
        zero_pooled.merge(seed_zero)
        geometry_pooled.merge(cast(_VectorStats, typed["geometry_error"]))
        typed_nominal = cast(dict[str, _OracleStats], typed["nominal_oracles"])
        for label in D028_BOUNDARY_LABELS:
            nominal_pooled[label].merge(typed_nominal[label])
        wall_pooled.merge(cast(_OracleStats, typed["wall_oracle"]))

    model_fits: dict[str, dict[str, dict[Action, _Fit]]] = {
        "linear": {},
        "quadratic": {},
    }
    model_metrics_per_seed: dict[str, dict[int, _Metrics]] = {
        "linear": {},
        "quadratic": {},
    }
    model_metrics_pooled = {"linear": _Metrics(), "quadratic": _Metrics()}
    for model_name, quadratic in (("linear", False), ("quadratic", True)):
        for fold_name, training_seeds in (
            ("EVEN", D028_PARITY_FOLDS["EVEN"]),
            ("ODD", D028_PARITY_FOLDS["ODD"]),
        ):
            heldout_seeds = frozenset(D028_DEFAULT_DEVELOPMENT_SEEDS) - frozenset(
                training_seeds
            )
            fits = _fit_cross_seed(rows, frozenset(training_seeds), quadratic)
            model_fits[model_name][fold_name] = fits
            for seed_rows in rows:
                if seed_rows.seed not in heldout_seeds:
                    continue
                scored = _score_fit(seed_rows, fits, quadratic)
                if seed_rows.seed not in model_metrics_per_seed[model_name]:
                    model_metrics_per_seed[model_name][seed_rows.seed] = _Metrics()
                model_metrics_per_seed[model_name][seed_rows.seed].merge(scored)
                model_metrics_pooled[model_name].merge(scored)

    for result in per_seed:
        seed = cast(int, result["seed"])
        evaluator = cast(dict[str, object], result["evaluator"])
        evaluator["batch_linear_metrics"] = model_metrics_per_seed["linear"][
            seed
        ].as_dict()
        evaluator["quadratic_metrics"] = model_metrics_per_seed["quadratic"][
            seed
        ].as_dict()

    fits_payload = {
        model_name: {
            fold: {action.name: fit.as_dict() for action, fit in fold_fits.items()}
            for fold, fold_fits in fold_payload.items()
        }
        for model_name, fold_payload in model_fits.items()
    }
    pooled_evaluator = {
        "support": {
            "transitions": sum(
                cast(
                    int,
                    cast(
                        dict[str, object],
                        cast(dict[str, object], result["evaluator"])["support"],
                    )["transitions"],
                )
                for result in per_seed
            ),
            "all_four_actions_visited": True,
            "action_counts": {
                action.name: sum(len(seed_rows.current[action]) for seed_rows in rows)
                for action in Action
            },
            "contact_delta_counts": {
                label: sum(
                    int(
                        np.count_nonzero(
                            np.concatenate(
                                [seed_rows.contact_codes[action] for action in Action]
                            )
                            == code
                        )
                    )
                    for seed_rows in rows
                )
                for label, code in (("-1", -1), ("0", 0), ("+1", 1))
            },
            "move_forward_boundary_counts": {
                label: sum(
                    int(
                        np.count_nonzero(
                            seed_rows.boundary_codes[Action.MOVE_FORWARD] == code
                        )
                    )
                    for seed_rows in rows
                )
                for label, code in zip(D028_BOUNDARY_LABELS, (1, 2, 3), strict=True)
            },
        },
        "alias_census": alias_census(alias_pooled),
        "alias_census_by_action": _alias_by_action(alias_pooled),
        "geometry_reconstruction": geometry_pooled.as_dict(("x", "y", "radial")),
        "geometry_consistency_failures": sum(
            _evaluator_integer(result, "geometry_consistency_failures")
            for result in per_seed
        ),
        "nominal_beacon_oracle": {
            label: value.as_dict() for label, value in nominal_pooled.items()
        },
        "heading_augmented_wall_aware_oracle": wall_pooled.as_dict(),
        "oracle_consistency_failures": sum(
            _evaluator_integer(result, "oracle_consistency_failures")
            for result in per_seed
        ),
        "d027_online_metrics": online_pooled.as_dict(),
        "zero_change_metrics": zero_pooled.as_dict(),
        "batch_linear_metrics": model_metrics_pooled["linear"].as_dict(),
        "quadratic_metrics": model_metrics_pooled["quadratic"].as_dict(),
    }
    return {
        "schema_version": 1,
        "experiment": "D-028",
        "title": "D-027 residual-attribution audit",
        "authoritative_base_sha": D028_AUTHORITATIVE_BASE_SHA,
        "executed_commit_sha": executed_sha,
        "development_seeds": list(development_seeds),
        "horizon": D028_HORIZON,
        "lifetime": "one uninterrupted D-027 causal lifetime per seed",
        "seed_policy": {
            "canonical_validator": "validate_exp003_development_seeds",
            "exact_declared_seeds": list(D028_DEFAULT_DEVELOPMENT_SEEDS),
            "formal_reservation_guard_preserved": True,
            "development_seed_reuse_is_not_fresh_evidence": True,
        },
        "d027_reference": {
            "artifact": str(
                _reference_artifact_path().relative_to(
                    Path(__file__).resolve().parents[2]
                )
            ),
            "artifact_sha256": D028_D027_ARTIFACT_SHA256,
            "accepted_executable_sha": artifact[18388].get(
                "implementation_probe_sha", "ad6b8abff0beb9812a510cbe53e652105d8b0bed"
            ),
            "causal_source_reused_without_modification": True,
        },
        "freeze": {
            "causal_scaffold": "exact D-027 replay; diagnostics after completed traces",
            "actions": [action.name for action in Action],
            "visible_channels": list(d027.D027_CHANNELS),
            "outputs": list(d027.D027_OUTPUTS),
            "linear_basis": ["1.0", *d027.D027_CHANNELS],
            "linear_feature_dimension": D028_LINEAR_FEATURE_DIMENSION,
            "quadratic_basis": "bias, v[0..5], v[i]*v[j] for 0<=i<=j<6 lexicographic",
            "quadratic_feature_dimension": D028_QUADRATIC_FEATURE_DIMENSION,
            "parity_folds": {
                name: list(values) for name, values in D028_PARITY_FOLDS.items()
            },
            "fit": {
                "method": "numpy.linalg.lstsq",
                "rcond": None,
                "regularization": False,
                "weighting": False,
                "randomness": False,
            },
            "boundary_tolerance": D028_BOUNDARY_TOLERANCE,
            "geometry_tolerance": D028_GEOMETRY_TOLERANCE,
            "nominal_move_distance": d027.D027_NOMINAL_MOVE_DISTANCE,
            "contact_tolerance": d024.D024_CONTACT_TOLERANCE,
            "interpretation_order": [
                "online-learning-dynamics",
                "linear-representation",
                "omitted-state-partial-observability",
                "unresolved",
            ],
        },
        "causal_order": [
            "unchanged D-027 action selection",
            "unchanged D-027 pre-update online prediction",
            "unchanged real environment transition",
            "unchanged D-027 learner update",
            "evaluator-only trace analysis",
        ],
        "organism_boundary": {"reward": 0.0, "info": {}, "observation_channels": 6},
        "evaluator_only": {
            "alias_key": "exact six visible float values plus executed action",
            "singleton_alias_status": "untested",
            "fits_and_oracles_causally_inert": True,
            "post_action_truth_used_only_for_scoring": True,
            "heading_oracle_uses_current_pre_action_heading_only": True,
            "alternative_action_queries": False,
        },
        "fits": fits_payload,
        "pooled": pooled_evaluator,
        "results": per_seed,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the D-028 residual-attribution audit."
    )
    parser.add_argument(
        "--seeds", type=int, nargs="+", default=list(D028_DEFAULT_DEVELOPMENT_SEEDS)
    )
    parser.add_argument("--horizon", type=int, default=D028_HORIZON)
    parser.add_argument("--executed-commit-sha")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    payload = json.dumps(
        run_d028_probe(
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
        print(f"D-028 result written to {args.output}")


if __name__ == "__main__":
    main()
