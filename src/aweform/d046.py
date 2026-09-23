"""D-046 one-time calibration and shadow V0.5 consequence learning.

The only causal addition in this module is a fresh, shadow-only predictor.  A
calibration command is selected by the evaluator and is passed directly to
the unchanged D-045 environment.  Predictor output never participates in
command selection, termination, reward, or observation construction.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final, cast

import numpy as np

from .d045 import (
    D045_MAX_WHEEL_DELTA_RAD,
    D045Env,
    D045PhysicalConfig,
)
from .exp003_seed_policy import validate_exp003_development_seeds

D046_TASK_ID: Final[str] = "D-046"
D046_AUTHORIZED_BASE_SHA: Final[str] = "4b32e49997cba6b223057b7e1946a97ba6fe9235"
D046_DEFAULT_SEEDS: Final[tuple[int, ...]] = tuple(range(21046, 21066))
D046_DT_SECONDS: Final[float] = 0.1
D046_MAX_WHEEL_DELTA_RAD: Final[float] = D045_MAX_WHEEL_DELTA_RAD
D046_NLMS_STEP: Final[float] = 0.5
D046_VISIBLE_DIMENSION: Final[int] = 8
D046_ACTION_DIMENSION: Final[int] = 2
D046_INPUT_DIMENSION: Final[int] = 10
D046_FEATURE_DIMENSION: Final[int] = 66
D046_WEIGHT_COUNT: Final[int] = 528
D046_CALIBRATION_TRANSITIONS: Final[int] = 564
D046_ZERO_PREFIX_TRANSITIONS: Final[int] = 16
D046_ZERO_SUFFIX_TRANSITIONS: Final[int] = 8
D046_BLOCK_COUNT: Final[int] = 72
D046_BLOCK_NONZERO_TRANSITIONS: Final[int] = 540
D046_QUARTER_SIZE: Final[int] = D046_CALIBRATION_TRANSITIONS // 4
D046_CHANNELS: Final[tuple[str, ...]] = (
    "energy",
    "temperature",
    "beacon_left",
    "beacon_forward",
    "beacon_right",
    "charging_contact",
    "wheel_delta_left",
    "wheel_delta_right",
)
D046_TARGETS: Final[tuple[str, ...]] = tuple(
    f"delta_{channel}" for channel in D046_CHANNELS
)
D046_AMPLITUDES: Final[tuple[float, ...]] = (0.0, 0.25, 0.5, 1.0)
D046_MODEL_LOWER: Final[tuple[float, ...]] = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -1.0, -1.0)
D046_MODEL_UPPER: Final[tuple[float, ...]] = (1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0)
D046_INITIAL_OPTIONS: Final[dict[str, object]] = {
    "body_position": (0.50, 0.50),
    "station_center": (0.50, 0.50),
    "heading": 0.0,
    "battery_j": 2664.0,
    "body_temperature_c": 23.0,
    "charger_termination_latched": False,
}

D046_HOLDOUT_POSES: Final[tuple[tuple[str, float, float, float], ...]] = (
    ("H0", 0.50, 0.50, 0.0),
    ("H1", 0.50, 0.50, math.pi),
    ("H2", 0.515, 0.50, 0.0),
    ("H3", 0.30, 0.50, 0.0),
    ("H4", 0.70, 0.50, math.pi),
    ("H5", 0.50, 0.30, math.pi / 2.0),
    ("H6", 0.65, 0.65, -3.0 * math.pi / 4.0),
    ("H7", 0.99, 0.50, 0.0),
    ("H8", 0.99, 0.99, math.pi / 4.0),
)
D046_HOLDOUT_ACTIONS: Final[tuple[tuple[str, float, float], ...]] = (
    ("A0", 0.0, 0.0),
    ("A1", math.pi / 180.0, math.pi / 180.0),
    ("A2", 0.25 * D046_MAX_WHEEL_DELTA_RAD, 0.25 * D046_MAX_WHEEL_DELTA_RAD),
    ("A3", D046_MAX_WHEEL_DELTA_RAD, D046_MAX_WHEEL_DELTA_RAD),
    ("A4", -D046_MAX_WHEEL_DELTA_RAD, -D046_MAX_WHEEL_DELTA_RAD),
    ("A5", -D046_MAX_WHEEL_DELTA_RAD, D046_MAX_WHEEL_DELTA_RAD),
    ("A6", D046_MAX_WHEEL_DELTA_RAD, 0.0),
    ("A7", 0.0, D046_MAX_WHEEL_DELTA_RAD),
    ("A8", 0.37 * D046_MAX_WHEEL_DELTA_RAD, -0.61 * D046_MAX_WHEEL_DELTA_RAD),
)
D046_ROLLOUTS: Final[dict[str, tuple[tuple[float, float], ...]]] = {
    "R0": tuple(
        (0.70 * D046_MAX_WHEEL_DELTA_RAD, 0.70 * D046_MAX_WHEEL_DELTA_RAD)
        for _ in range(10)
    ),
    "R1": tuple(
        (0.70 * D046_MAX_WHEEL_DELTA_RAD, 0.70 * D046_MAX_WHEEL_DELTA_RAD)
        for _ in range(10)
    ),
    "R2": tuple(
        (0.60 * D046_MAX_WHEEL_DELTA_RAD, 0.40 * D046_MAX_WHEEL_DELTA_RAD)
        for _ in range(10)
    ),
    "R3": tuple(
        (0.70 * D046_MAX_WHEEL_DELTA_RAD, 0.70 * D046_MAX_WHEEL_DELTA_RAD)
        for _ in range(8)
    ),
}
D046_ROLLOUT_STARTS: Final[dict[str, tuple[float, float, float]]] = {
    "R0": (0.30, 0.50, 0.0),
    "R1": (0.50, 0.30, math.pi / 2.0),
    "R2": (0.65, 0.65, -3.0 * math.pi / 4.0),
    "R3": (0.96, 0.50, 0.0),
}


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _clip(value: float, lower: float, upper: float) -> float:
    return min(max(value, lower), upper)


def _validate_vector(
    name: str, values: Sequence[float], expected: int
) -> tuple[float, ...]:
    if len(values) != expected:
        raise ValueError(f"{name} must contain exactly {expected} values")
    result = tuple(float(value) for value in values)
    if not all(math.isfinite(value) for value in result):
        raise ValueError(f"{name} must contain only finite values")
    return result


def _observation_tuple(observation: np.ndarray[Any, Any]) -> tuple[float, ...]:
    return tuple(float(value) for value in observation)


def _validate_action(action: Sequence[float]) -> tuple[float, float]:
    values = _validate_vector("action", action, D046_ACTION_DIMENSION)
    if any(abs(value) > D046_MAX_WHEEL_DELTA_RAD + 1e-15 for value in values):
        raise ValueError("action exceeds the D-045 wheel-command envelope")
    return cast(tuple[float, float], values)


def model_state_from_observation(observation: Sequence[float]) -> tuple[float, ...]:
    """Map the exact eight D-045 visible channels into learner model space."""
    visible = _validate_vector("observation", observation, D046_VISIBLE_DIMENSION)
    result = (
        *visible[:6],
        visible[6] / D046_MAX_WHEEL_DELTA_RAD,
        visible[7] / D046_MAX_WHEEL_DELTA_RAD,
    )
    for index, value in enumerate(result):
        if not D046_MODEL_LOWER[index] <= value <= D046_MODEL_UPPER[index]:
            raise ValueError("observation is outside the declared model bounds")
    return result


def quadratic_feature_map(
    model_state: Sequence[float], action: Sequence[float]
) -> tuple[float, ...]:
    """Return [1, x_i, x_i*x_j for i <= j] for ten model inputs."""
    state = _validate_vector("model_state", model_state, D046_VISIBLE_DIMENSION)
    command = _validate_action(action)
    x = (
        *state,
        command[0] / D046_MAX_WHEEL_DELTA_RAD,
        command[1] / D046_MAX_WHEEL_DELTA_RAD,
    )
    quadratic = tuple(
        x[i] * x[j]
        for i in range(D046_INPUT_DIMENSION)
        for j in range(i, D046_INPUT_DIMENSION)
    )
    features = (1.0, *x, *quadratic)
    if len(features) != D046_FEATURE_DIMENSION:
        raise RuntimeError("D-046 quadratic feature dimension changed")
    return features


@dataclass(frozen=True, slots=True)
class D046Prediction:
    """Pre-update bounded next-state prediction and its raw delta."""

    delta: tuple[float, ...]
    next_state: tuple[float, ...]
    features: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class D046LearningUpdate:
    """Post-consequence normalized-LMS update diagnostics."""

    prediction: D046Prediction
    observed_delta: tuple[float, ...]
    errors: tuple[float, ...]
    normalizer: float


class D046ConsequencePredictor:
    """Fresh 66 x 8 shadow predictor with exactly 528 learned scalars."""

    __slots__ = ("_weights", "_state_only")

    def __init__(self, *, state_only: bool = False) -> None:
        self._weights = np.zeros(
            (D046_FEATURE_DIMENSION, D046_VISIBLE_DIMENSION), dtype=np.float64
        )
        self._state_only = state_only
        if self._weights.size != D046_WEIGHT_COUNT:
            raise RuntimeError("D-046 weight count changed")

    @property
    def state_only(self) -> bool:
        return self._state_only

    @property
    def weights(self) -> tuple[float, ...]:
        return tuple(float(value) for value in self._weights.ravel(order="C"))

    def weight_snapshot(self) -> list[float]:
        return list(self.weights)

    def weight_summary(self) -> dict[str, object]:
        values = self.weights
        if not all(math.isfinite(value) for value in values):
            raise ValueError("D-046 weights contain a non-finite value")
        return {
            "count": len(values),
            "finite": True,
            "l2_norm": float(np.linalg.norm(self._weights)),
            "min": min(values),
            "max": max(values),
        }

    def weight_digest(self) -> str:
        """Return a deterministic digest of the complete learned state."""
        return hashlib.sha256(_canonical_json(list(self.weights))).hexdigest()

    def predict(
        self, observation: Sequence[float], action: Sequence[float]
    ) -> D046Prediction:
        return self.predict_model_state(
            model_state_from_observation(observation), action
        )

    def predict_model_state(
        self, model_state: Sequence[float], action: Sequence[float]
    ) -> D046Prediction:
        state = _validate_vector("model_state", model_state, D046_VISIBLE_DIMENSION)
        effective_action = (0.0, 0.0) if self._state_only else _validate_action(action)
        features = quadratic_feature_map(state, effective_action)
        raw_delta = np.asarray(features, dtype=np.float64) @ self._weights
        delta = tuple(float(value) for value in raw_delta)
        next_state = tuple(
            _clip(
                state[index] + delta[index],
                D046_MODEL_LOWER[index],
                D046_MODEL_UPPER[index],
            )
            for index in range(D046_VISIBLE_DIMENSION)
        )
        return D046Prediction(delta, next_state, features)

    def update_from_transition(
        self,
        observation: Sequence[float],
        action: Sequence[float],
        next_observation: Sequence[float],
        prediction: D046Prediction,
    ) -> D046LearningUpdate:
        current = model_state_from_observation(observation)
        next_state = model_state_from_observation(next_observation)
        expected = self.predict_model_state(current, action)
        if expected != prediction:
            raise ValueError("prediction was not made from the current model state")
        observed_delta = tuple(
            next_state[index] - current[index]
            for index in range(D046_VISIBLE_DIMENSION)
        )
        errors = tuple(
            observed_delta[index] - prediction.delta[index]
            for index in range(D046_VISIBLE_DIMENSION)
        )
        feature_array = np.asarray(prediction.features, dtype=np.float64)
        error_array = np.asarray(errors, dtype=np.float64)
        normalizer = float(np.dot(feature_array, feature_array))
        self._weights += (
            D046_NLMS_STEP
            * np.outer(feature_array, error_array)
            / max(normalizer, 1e-12)
        )
        return D046LearningUpdate(prediction, observed_delta, errors, normalizer)


@dataclass(frozen=True, slots=True)
class D046CurriculumStep:
    """Evaluator-side command metadata; none of this is passed to the learner."""

    command: tuple[float, float]
    amplitude: float
    block_index: int | None


@dataclass(frozen=True, slots=True)
class D046Curriculum:
    seed: int
    block_order: tuple[int, ...]
    steps: tuple[D046CurriculumStep, ...]
    sequence_sha256: str


def _block_definitions() -> tuple[tuple[tuple[float, float], float, int], ...]:
    patterns = (
        (1.0, 1.0),
        (-1.0, 1.0),
        (1.0, 0.0),
        (0.0, 1.0),
        (1.0, 0.5),
        (0.5, 1.0),
    )
    return tuple(
        (
            (
                scale * pattern[0] * D046_MAX_WHEEL_DELTA_RAD,
                scale * pattern[1] * D046_MAX_WHEEL_DELTA_RAD,
            ),
            scale,
            length,
        )
        for pattern in patterns
        for scale in (0.25, 0.50, 1.00)
        for length in (1, 2, 4, 8)
    )


D046_BLOCK_DEFINITIONS: Final[tuple[tuple[tuple[float, float], float, int], ...]] = (
    _block_definitions()
)


def validate_d046_development_seed(seed: int) -> int:
    """Validate one D-046 development seed against all formal reservations."""
    validated = validate_exp003_development_seeds((seed,))
    if validated[0] not in D046_DEFAULT_SEEDS:
        raise ValueError(
            "D-046 may execute only the authorized seeds 21046..21065"
        )
    return validated[0]


def validate_d046_development_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    """Require exactly the authorized 20-seed D-046 development block."""
    validated = validate_exp003_development_seeds(seeds)
    if validated != D046_DEFAULT_SEEDS:
        raise ValueError("D-046 official execution requires exactly seeds 21046..21065")
    return validated


def build_d046_curriculum(seed: int) -> D046Curriculum:
    """Build the one-time external raw-command curriculum for one seed."""
    validated_seed = validate_d046_development_seed(seed)
    order = list(range(len(D046_BLOCK_DEFINITIONS)))
    random.Random(validated_seed).shuffle(order)
    steps: list[D046CurriculumStep] = [
        D046CurriculumStep((0.0, 0.0), 0.0, None)
        for _ in range(D046_ZERO_PREFIX_TRANSITIONS)
    ]
    for block_index in order:
        command, amplitude, length = D046_BLOCK_DEFINITIONS[block_index]
        steps.extend(
            D046CurriculumStep(command, amplitude, block_index) for _ in range(length)
        )
        inverse = (-command[0], -command[1])
        steps.extend(
            D046CurriculumStep(inverse, amplitude, block_index) for _ in range(length)
        )
    steps.extend(
        D046CurriculumStep((0.0, 0.0), 0.0, None)
        for _ in range(D046_ZERO_SUFFIX_TRANSITIONS)
    )
    if len(steps) != D046_CALIBRATION_TRANSITIONS:
        raise RuntimeError("D-046 curriculum length changed")
    if any(
        abs(value) > D046_MAX_WHEEL_DELTA_RAD + 1e-15
        for step in steps
        for value in step.command
    ):
        raise RuntimeError("D-046 curriculum exceeds the D-045 action envelope")
    digest_payload = {
        "seed": validated_seed,
        "block_order": order,
        "steps": [
            {"command": list(step.command), "amplitude": step.amplitude}
            for step in steps
        ],
    }
    sequence_sha256 = hashlib.sha256(_canonical_json(digest_payload)).hexdigest()
    return D046Curriculum(validated_seed, tuple(order), tuple(steps), sequence_sha256)


@dataclass(slots=True)
class _MetricAccumulator:
    count: int = 0
    absolute_error: list[float] = field(
        default_factory=lambda: [0.0] * D046_VISIBLE_DIMENSION
    )
    zero_absolute_error: list[float] = field(
        default_factory=lambda: [0.0] * D046_VISIBLE_DIMENSION
    )
    contact_brier: float = 0.0
    zero_contact_brier: float = 0.0

    def add(
        self,
        predicted_delta: Sequence[float],
        zero_delta: Sequence[float],
        actual_delta: Sequence[float],
        predicted_contact: float,
        zero_contact: float,
        actual_contact: float,
    ) -> None:
        predicted = _validate_vector("predicted_delta", predicted_delta, 8)
        zero = _validate_vector("zero_delta", zero_delta, 8)
        actual = _validate_vector("actual_delta", actual_delta, 8)
        self.count += 1
        for index in range(D046_VISIBLE_DIMENSION):
            self.absolute_error[index] += abs(predicted[index] - actual[index])
            self.zero_absolute_error[index] += abs(zero[index] - actual[index])
        self.contact_brier += (predicted_contact - actual_contact) ** 2
        self.zero_contact_brier += (zero_contact - actual_contact) ** 2

    def merge(self, other: _MetricAccumulator) -> None:
        self.count += other.count
        for index in range(D046_VISIBLE_DIMENSION):
            self.absolute_error[index] += other.absolute_error[index]
            self.zero_absolute_error[index] += other.zero_absolute_error[index]
        self.contact_brier += other.contact_brier
        self.zero_contact_brier += other.zero_contact_brier

    def payload(self) -> dict[str, object]:
        def means(values: Sequence[float]) -> dict[str, float | None]:
            return {
                target: (values[index] / self.count if self.count else None)
                for index, target in enumerate(D046_TARGETS)
            }

        learned = means(self.absolute_error)
        zero = means(self.zero_absolute_error)
        difference: dict[str, float | None] = {}
        for target in D046_TARGETS:
            learned_value = learned[target]
            zero_value = zero[target]
            difference[target] = (
                learned_value - zero_value
                if learned_value is not None and zero_value is not None
                else None
            )
        return {
            "support": self.count,
            "learned_mae": learned,
            "zero_change_mae": zero,
            "learned_minus_zero_change_mae": difference,
            "learned_contact_brier": (
                self.contact_brier / self.count if self.count else None
            ),
            "zero_change_contact_brier": (
                self.zero_contact_brier / self.count if self.count else None
            ),
        }


class _PrequentialMetrics:
    def __init__(self) -> None:
        self.overall = _MetricAccumulator()
        self.quarters = {f"Q{index}": _MetricAccumulator() for index in range(1, 5)}
        self.contact_strata = {
            "contact_event": _MetricAccumulator(),
            "contact_non_event": _MetricAccumulator(),
        }
        self.amplitude_strata = {
            _amplitude_key(amplitude): _MetricAccumulator()
            for amplitude in D046_AMPLITUDES
        }

    def add(
        self,
        transition_index: int,
        amplitude: float,
        current_state: Sequence[float],
        predicted: D046Prediction,
        actual_state: Sequence[float],
    ) -> None:
        current = _validate_vector("current_state", current_state, 8)
        actual = _validate_vector("actual_state", actual_state, 8)
        actual_delta = tuple(actual[index] - current[index] for index in range(8))
        zero_delta = (0.0,) * 8
        accumulator_values: list[_MetricAccumulator] = [
            self.overall,
            self.quarters[f"Q{min(3, transition_index // D046_QUARTER_SIZE) + 1}"],
            self.amplitude_strata[_amplitude_key(amplitude)],
        ]
        event_key = "contact_event" if current[5] != actual[5] else "contact_non_event"
        accumulator_values.append(self.contact_strata[event_key])
        for accumulator in accumulator_values:
            accumulator.add(
                predicted.delta,
                zero_delta,
                actual_delta,
                predicted.next_state[5],
                current[5],
                actual[5],
            )

    def merge(self, other: _PrequentialMetrics) -> None:
        self.overall.merge(other.overall)
        for key in self.quarters:
            self.quarters[key].merge(other.quarters[key])
        for key in self.contact_strata:
            self.contact_strata[key].merge(other.contact_strata[key])
        for key in self.amplitude_strata:
            self.amplitude_strata[key].merge(other.amplitude_strata[key])

    def payload(self) -> dict[str, object]:
        return {
            "overall": self.overall.payload(),
            "quarters": {key: value.payload() for key, value in self.quarters.items()},
            "contact_strata": {
                key: value.payload() for key, value in self.contact_strata.items()
            },
            "amplitude_strata": {
                key: value.payload() for key, value in self.amplitude_strata.items()
            },
        }


def _amplitude_key(amplitude: float) -> str:
    return str(amplitude).rstrip("0").rstrip(".") if amplitude else "0"


@dataclass(slots=True)
class _CalibrationSupport:
    transitions: int = 0
    contact_on: int = 0
    contact_off: int = 0
    contact_entry: int = 0
    contact_exit: int = 0
    charging_positive: int = 0
    amplitude_counts: dict[str, int] = field(
        default_factory=lambda: {_amplitude_key(value): 0 for value in D046_AMPLITUDES}
    )
    left_values: set[float] = field(default_factory=set)
    right_values: set[float] = field(default_factory=set)
    pair_values: set[tuple[float, float]] = field(default_factory=set)
    left_min: float = math.inf
    left_max: float = -math.inf
    right_min: float = math.inf
    right_max: float = -math.inf
    within_envelope: bool = True
    rewards_zero: bool = True
    infos_empty: bool = True

    def add(
        self,
        step: D046CurriculumStep,
        current_state: Sequence[float],
        next_state: Sequence[float],
        charging_positive: bool,
        reward: float,
        info: dict[str, object],
    ) -> None:
        left, right = step.command
        current_contact = bool(current_state[5])
        next_contact = bool(next_state[5])
        self.transitions += 1
        self.contact_on += int(current_contact)
        self.contact_off += int(not current_contact)
        self.contact_entry += int(not current_contact and next_contact)
        self.contact_exit += int(current_contact and not next_contact)
        self.charging_positive += int(charging_positive)
        amplitude = _amplitude_key(step.amplitude)
        self.amplitude_counts[amplitude] += 1
        self.left_values.add(left)
        self.right_values.add(right)
        self.pair_values.add((left, right))
        self.left_min = min(self.left_min, left)
        self.left_max = max(self.left_max, left)
        self.right_min = min(self.right_min, right)
        self.right_max = max(self.right_max, right)
        self.within_envelope = self.within_envelope and all(
            abs(value) <= D046_MAX_WHEEL_DELTA_RAD + 1e-15 for value in (left, right)
        )
        self.rewards_zero = self.rewards_zero and reward == 0.0
        self.infos_empty = self.infos_empty and info == {}

    def merge(self, other: _CalibrationSupport) -> None:
        self.transitions += other.transitions
        self.contact_on += other.contact_on
        self.contact_off += other.contact_off
        self.contact_entry += other.contact_entry
        self.contact_exit += other.contact_exit
        self.charging_positive += other.charging_positive
        for key, value in other.amplitude_counts.items():
            self.amplitude_counts[key] += value
        self.left_values.update(other.left_values)
        self.right_values.update(other.right_values)
        self.pair_values.update(other.pair_values)
        self.left_min = min(self.left_min, other.left_min)
        self.left_max = max(self.left_max, other.left_max)
        self.right_min = min(self.right_min, other.right_min)
        self.right_max = max(self.right_max, other.right_max)
        self.within_envelope = self.within_envelope and other.within_envelope
        self.rewards_zero = self.rewards_zero and other.rewards_zero
        self.infos_empty = self.infos_empty and other.infos_empty

    def payload(self) -> dict[str, object]:
        return {
            "transitions": self.transitions,
            "contact_on_transitions": self.contact_on,
            "contact_off_transitions": self.contact_off,
            "contact_entry_transitions": self.contact_entry,
            "contact_exit_transitions": self.contact_exit,
            "charging_positive_transitions": self.charging_positive,
            "action_amplitude_transition_counts": dict(self.amplitude_counts),
            "action_values": {
                "left": {
                    "min": self.left_min,
                    "max": self.left_max,
                    "support": len(self.left_values),
                },
                "right": {
                    "min": self.right_min,
                    "max": self.right_max,
                    "support": len(self.right_values),
                },
                "pair_support": len(self.pair_values),
            },
            "raw_commands_within_d045_envelope": self.within_envelope,
            "reward_exactly_zero": self.rewards_zero,
            "organism_info_exactly_empty": self.infos_empty,
        }


def _record_digest(
    digest: hashlib._Hash,
    command: tuple[float, float],
    observation: Sequence[float],
    reward: float,
    terminated: bool,
    truncated: bool,
    info: dict[str, object],
) -> None:
    digest.update(
        _canonical_json(
            {
                "command": list(command),
                "observation": [float(value) for value in observation],
                "reward": reward,
                "terminated": terminated,
                "truncated": truncated,
                "info": info,
            }
        )
    )
    digest.update(b"\n")


@dataclass(slots=True)
class _LifetimeResult:
    seed: int
    curriculum: D046Curriculum
    support: _CalibrationSupport
    prequential: _PrequentialMetrics
    predictor: D046ConsequencePredictor
    state_only_predictor: D046ConsequencePredictor
    learner_digest: str
    matched_no_learner_digest: str

    def payload(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "curriculum_block_order": list(self.curriculum.block_order),
            "curriculum_sequence_sha256": self.curriculum.sequence_sha256,
            "transition_count": self.support.transitions,
            "support": self.support.payload(),
            "prequential": self.prequential.payload(),
            "final_weights": self.predictor.weight_snapshot(),
            "final_weight_sha256": self.predictor.weight_digest(),
            "final_weight_summary": self.predictor.weight_summary(),
            "state_only_final_weight_summary": (
                self.state_only_predictor.weight_summary()
            ),
            "state_only_final_weight_sha256": self.state_only_predictor.weight_digest(),
            "trajectory_digest": self.learner_digest,
            "matched_no_learner_trajectory_digest": self.matched_no_learner_digest,
            "trajectory_identity_equal": self.learner_digest
            == self.matched_no_learner_digest,
        }


def _new_d045_environment() -> D045Env:
    return D045Env(D045PhysicalConfig())


def _replay_curriculum_without_learner(curriculum: D046Curriculum) -> str:
    environment = _new_d045_environment()
    _, reset_info = environment.reset(options=dict(D046_INITIAL_OPTIONS))
    if reset_info != {}:
        raise RuntimeError("D-045 replay reset exposed organism info")
    digest = hashlib.sha256()
    for step in curriculum.steps:
        raw_observation, reward, terminated, truncated, info = environment.step(
            step.command
        )
        observation = _observation_tuple(raw_observation)
        _record_digest(
            digest, step.command, observation, reward, terminated, truncated, info
        )
        if terminated or truncated:
            raise RuntimeError("D-045 terminated during the D-046 replay")
    return digest.hexdigest()


def _run_lifetime(seed: int) -> _LifetimeResult:
    curriculum = build_d046_curriculum(seed)
    environment = _new_d045_environment()
    learner = D046ConsequencePredictor()
    state_only = D046ConsequencePredictor(state_only=True)
    prequential = _PrequentialMetrics()
    support = _CalibrationSupport()
    digest = hashlib.sha256()
    raw_observation, reset_info = environment.reset(options=dict(D046_INITIAL_OPTIONS))
    observation = _observation_tuple(raw_observation)
    if reset_info != {}:
        raise RuntimeError("D-045 reset exposed organism info")
    for transition_index, step in enumerate(curriculum.steps):
        current_state = model_state_from_observation(observation)
        learner_prediction = learner.predict(observation, step.command)
        state_prediction = state_only.predict(observation, step.command)
        raw_next_observation, reward, terminated, truncated, info = environment.step(
            step.command
        )
        next_observation = _observation_tuple(raw_next_observation)
        learner_update = learner.update_from_transition(
            observation, step.command, next_observation, learner_prediction
        )
        state_only.update_from_transition(
            observation, step.command, next_observation, state_prediction
        )
        next_state = model_state_from_observation(next_observation)
        prequential.add(
            transition_index,
            step.amplitude,
            current_state,
            learner_update.prediction,
            next_state,
        )
        telemetry = environment.last_transition
        if telemetry is None:
            raise RuntimeError("D-045 did not expose evaluator transition telemetry")
        support.add(
            step,
            current_state,
            next_state,
            telemetry.actual_stored_power_w > 0.0,
            reward,
            info,
        )
        _record_digest(
            digest,
            step.command,
            next_observation,
            reward,
            terminated,
            truncated,
            info,
        )
        if terminated or truncated:
            raise RuntimeError("D-045 terminated during the D-046 calibration")
        observation = next_observation
    if support.transitions != D046_CALIBRATION_TRANSITIONS:
        raise RuntimeError("D-046 calibration transition count changed")
    if len(learner.weights) != D046_WEIGHT_COUNT:
        raise RuntimeError("D-046 learner weight count changed")
    learner_digest = digest.hexdigest()
    return _LifetimeResult(
        seed,
        curriculum,
        support,
        prequential,
        learner,
        state_only,
        learner_digest,
        _replay_curriculum_without_learner(curriculum),
    )


class _ComparisonAccumulator:
    def __init__(self) -> None:
        self.models = {
            "organism_full": _MetricAccumulator(),
            "state_only": _MetricAccumulator(),
            "zero_change": _MetricAccumulator(),
        }

    def add_row(
        self,
        current_state: Sequence[float],
        actual_state: Sequence[float],
        predictions: dict[str, tuple[float, ...]],
        predicted_states: dict[str, tuple[float, ...]],
    ) -> None:
        current = _validate_vector("current_state", current_state, 8)
        actual = _validate_vector("actual_state", actual_state, 8)
        actual_delta = tuple(actual[index] - current[index] for index in range(8))
        zero_delta = (0.0,) * 8
        for name, accumulator in self.models.items():
            accumulator.add(
                predictions[name],
                zero_delta,
                actual_delta,
                predicted_states[name][5],
                current[5],
                actual[5],
            )

    def merge(self, other: _ComparisonAccumulator) -> None:
        for key in self.models:
            self.models[key].merge(other.models[key])

    def payload(self) -> dict[str, object]:
        return {key: value.payload() for key, value in self.models.items()}


class _HeldoutMetrics:
    def __init__(self) -> None:
        self.groups: dict[str, _ComparisonAccumulator] = {}

    def add_row(
        self,
        group_names: Sequence[str],
        current_state: Sequence[float],
        actual_state: Sequence[float],
        predictions: dict[str, tuple[float, ...]],
        predicted_states: dict[str, tuple[float, ...]],
    ) -> None:
        for group_name in group_names:
            accumulator = self.groups.setdefault(group_name, _ComparisonAccumulator())
            accumulator.add_row(
                current_state, actual_state, predictions, predicted_states
            )

    def merge(self, other: _HeldoutMetrics) -> None:
        for key, value in other.groups.items():
            self.groups.setdefault(key, _ComparisonAccumulator()).merge(value)

    def payload(self) -> dict[str, object]:
        return {key: value.payload() for key, value in self.groups.items()}


def _zero_prediction(model_state: Sequence[float]) -> D046Prediction:
    state = _validate_vector("model_state", model_state, 8)
    return D046Prediction((0.0,) * 8, state, ())


def _evaluator_options(
    position: tuple[float, float], heading: float
) -> dict[str, object]:
    options = dict(D046_INITIAL_OPTIONS)
    options["body_position"] = position
    options["heading"] = heading
    return options


def _evaluate_heldout(
    learner: D046ConsequencePredictor, state_only: D046ConsequencePredictor
) -> tuple[_HeldoutMetrics, int]:
    metrics = _HeldoutMetrics()
    count = 0
    for pose_name, x, y, heading in D046_HOLDOUT_POSES:
        for action_name, left, right in D046_HOLDOUT_ACTIONS:
            action = (left, right)
            environment = _new_d045_environment()
            raw_observation, reset_info = environment.reset(
                options=_evaluator_options((x, y), heading)
            )
            observation = _observation_tuple(raw_observation)
            if reset_info != {}:
                raise RuntimeError("D-045 holdout reset exposed info")
            current_state = model_state_from_observation(observation)
            full_prediction = learner.predict(observation, action)
            state_prediction = state_only.predict(observation, action)
            raw_next_observation, reward, terminated, truncated, info = (
                environment.step(action)
            )
            next_observation = _observation_tuple(raw_next_observation)
            actual_state = model_state_from_observation(next_observation)
            zero_prediction = _zero_prediction(current_state)
            predictions = {
                "organism_full": full_prediction.delta,
                "state_only": state_prediction.delta,
                "zero_change": zero_prediction.delta,
            }
            predicted_states = {
                "organism_full": full_prediction.next_state,
                "state_only": state_prediction.next_state,
                "zero_change": zero_prediction.next_state,
            }
            telemetry = environment.last_transition
            if telemetry is None:
                raise RuntimeError("D-045 holdout transition telemetry missing")
            boundary_key = (
                "boundary" if telemetry.boundary_scale < 1.0 else "non_boundary"
            )
            contact_key = (
                "contact_event"
                if current_state[5] != actual_state[5]
                else "contact_non_event"
            )
            metrics.add_row(
                (
                    "overall",
                    f"by_start_pose:{pose_name}",
                    f"by_action:{action_name}",
                    boundary_key,
                    contact_key,
                ),
                current_state,
                actual_state,
                predictions,
                predicted_states,
            )
            if reward != 0.0 or info != {} or terminated or truncated:
                raise RuntimeError("D-045 holdout violated the read-only boundary")
            count += 1
    if count != 81:
        raise RuntimeError("D-046 held-out matrix is not 81 transitions")
    return metrics, count


class _StateMetricAccumulator:
    def __init__(self) -> None:
        self.count = 0
        self.absolute_error = [0.0] * D046_VISIBLE_DIMENSION
        self.contact_brier = 0.0
        self.contact_absolute_error = 0.0
        self.finite_count = 0
        self.bounded_count = 0

    def add(self, predicted: Sequence[float], actual: Sequence[float]) -> None:
        prediction = _validate_vector("rollout_prediction", predicted, 8)
        target = _validate_vector("rollout_target", actual, 8)
        self.count += 1
        self.finite_count += int(all(math.isfinite(value) for value in prediction))
        self.bounded_count += int(
            all(
                D046_MODEL_LOWER[index] <= prediction[index] <= D046_MODEL_UPPER[index]
                for index in range(8)
            )
        )
        for index in range(8):
            self.absolute_error[index] += abs(prediction[index] - target[index])
        self.contact_brier += (prediction[5] - target[5]) ** 2
        self.contact_absolute_error += abs(prediction[5] - target[5])

    def merge(self, other: _StateMetricAccumulator) -> None:
        self.count += other.count
        self.finite_count += other.finite_count
        self.bounded_count += other.bounded_count
        for index in range(8):
            self.absolute_error[index] += other.absolute_error[index]
        self.contact_brier += other.contact_brier
        self.contact_absolute_error += other.contact_absolute_error

    def payload(self) -> dict[str, object]:
        return {
            "support": self.count,
            "channel_mae": {
                channel: (
                    self.absolute_error[index] / self.count if self.count else None
                )
                for index, channel in enumerate(D046_CHANNELS)
            },
            "contact_brier": self.contact_brier / self.count if self.count else None,
            "contact_absolute_error": (
                self.contact_absolute_error / self.count if self.count else None
            ),
            "finite_prediction_support": self.finite_count,
            "bounded_prediction_support": self.bounded_count,
        }


class _RolloutComparison:
    def __init__(self) -> None:
        self.models = {
            "organism_full": _StateMetricAccumulator(),
            "state_only": _StateMetricAccumulator(),
            "zero_change": _StateMetricAccumulator(),
        }

    def add(
        self,
        predicted: dict[str, tuple[float, ...]],
        actual: Sequence[float],
    ) -> None:
        for key, accumulator in self.models.items():
            accumulator.add(predicted[key], actual)

    def merge(self, other: _RolloutComparison) -> None:
        for key in self.models:
            self.models[key].merge(other.models[key])

    def payload(self) -> dict[str, object]:
        return {key: value.payload() for key, value in self.models.items()}


class _RolloutMetrics:
    def __init__(self) -> None:
        self.groups: dict[str, dict[str, _RolloutComparison]] = {}

    def add(
        self,
        rollout_name: str,
        horizon: str,
        predicted: dict[str, tuple[float, ...]],
        actual: Sequence[float],
    ) -> None:
        route = self.groups.setdefault(rollout_name, {})
        route.setdefault(horizon, _RolloutComparison()).add(predicted, actual)
        all_route = self.groups.setdefault("all_rollouts", {})
        all_route.setdefault(horizon, _RolloutComparison()).add(predicted, actual)

    def merge(self, other: _RolloutMetrics) -> None:
        for route, horizons in other.groups.items():
            destination = self.groups.setdefault(route, {})
            for horizon, comparison in horizons.items():
                destination.setdefault(horizon, _RolloutComparison()).merge(comparison)

    def payload(self) -> dict[str, object]:
        return {
            "by_rollout": {
                route: {
                    horizon: comparison.payload()
                    for horizon, comparison in horizons.items()
                }
                for route, horizons in self.groups.items()
            }
        }


def _evaluate_rollouts(
    learner: D046ConsequencePredictor, state_only: D046ConsequencePredictor
) -> tuple[_RolloutMetrics, dict[str, int]]:
    metrics = _RolloutMetrics()
    lengths: dict[str, int] = {}
    for rollout_name, commands in D046_ROLLOUTS.items():
        x, y, heading = D046_ROLLOUT_STARTS[rollout_name]
        environment = _new_d045_environment()
        raw_observation, reset_info = environment.reset(
            options=_evaluator_options((x, y), heading)
        )
        observation = _observation_tuple(raw_observation)
        if reset_info != {}:
            raise RuntimeError("D-045 rollout reset exposed info")
        full_state = model_state_from_observation(observation)
        state_only_state = full_state
        zero_state = full_state
        lengths[rollout_name] = len(commands)
        for step_index, command in enumerate(commands, start=1):
            full_prediction = learner.predict_model_state(full_state, command)
            state_prediction = state_only.predict_model_state(state_only_state, command)
            zero_prediction = _zero_prediction(zero_state)
            raw_next_observation, reward, terminated, truncated, info = (
                environment.step(command)
            )
            next_observation = _observation_tuple(raw_next_observation)
            actual_state = model_state_from_observation(next_observation)
            predictions = {
                "organism_full": full_prediction.next_state,
                "state_only": state_prediction.next_state,
                "zero_change": zero_prediction.next_state,
            }
            if step_index in (1, 2, 4, 8):
                metrics.add(rollout_name, str(step_index), predictions, actual_state)
            if step_index == len(commands):
                metrics.add(rollout_name, "final", predictions, actual_state)
            if reward != 0.0 or info != {} or terminated or truncated:
                raise RuntimeError("D-045 rollout violated the read-only boundary")
            full_state = full_prediction.next_state
            state_only_state = state_prediction.next_state
            zero_state = zero_prediction.next_state
    return metrics, lengths


def _heldout_direction(metrics: _HeldoutMetrics) -> dict[str, str | None]:
    overall = metrics.groups["overall"]
    full = overall.models["organism_full"].payload()["learned_mae"]
    state = overall.models["state_only"].payload()["learned_mae"]
    if not isinstance(full, dict) or not isinstance(state, dict):
        raise RuntimeError("invalid held-out metric payload")
    result: dict[str, str | None] = {}
    for target in D046_TARGETS:
        full_value = cast(float | None, full[target])
        state_value = cast(float | None, state[target])
        if full_value is None or state_value is None:
            result[target] = None
        elif full_value < state_value:
            result[target] = "organism_full_lower_mae"
        elif full_value > state_value:
            result[target] = "state_only_lower_mae"
        else:
            result[target] = "equal_mae"
    return result


def run_d046_official(
    *,
    executed_commit_sha: str,
    seeds: Sequence[int] = D046_DEFAULT_SEEDS,
) -> dict[str, object]:
    """Run the frozen official 20-lifetime D-046 protocol once."""
    validated_seeds = validate_d046_development_seeds(seeds)
    if len(executed_commit_sha) != 40 or any(
        character not in "0123456789abcdef" for character in executed_commit_sha
    ):
        raise ValueError("executed_commit_sha must be a 40-character lowercase SHA")
    pooled_support = _CalibrationSupport()
    pooled_prequential = _PrequentialMetrics()
    pooled_heldout = _HeldoutMetrics()
    pooled_rollouts = _RolloutMetrics()
    lifetime_payloads: list[dict[str, object]] = []
    heldout_payloads: list[dict[str, object]] = []
    rollout_payloads: list[dict[str, object]] = []
    rollout_lengths: dict[str, int] = {}
    for seed in validated_seeds:
        lifetime = _run_lifetime(seed)
        pooled_support.merge(lifetime.support)
        pooled_prequential.merge(lifetime.prequential)
        heldout, heldout_count = _evaluate_heldout(
            lifetime.predictor, lifetime.state_only_predictor
        )
        rollouts, lengths = _evaluate_rollouts(
            lifetime.predictor, lifetime.state_only_predictor
        )
        pooled_heldout.merge(heldout)
        pooled_rollouts.merge(rollouts)
        rollout_lengths = lengths
        lifetime_payloads.append(lifetime.payload())
        heldout_payloads.append(
            {
                "seed": seed,
                "transition_count": heldout_count,
                "metrics": heldout.payload(),
                "organism_full_vs_state_only_direction": _heldout_direction(heldout),
                "weights_unchanged_during_evaluation": True,
            }
        )
        rollout_payloads.append(
            {
                "seed": seed,
                "sequence_lengths": lengths,
                "metrics": rollouts.payload(),
                "weights_unchanged_during_evaluation": True,
            }
        )
    return {
        "artifact_schema_version": "D046-1",
        "task_id": D046_TASK_ID,
        "authorized_base_sha": D046_AUTHORIZED_BASE_SHA,
        "executed_commit_sha": executed_commit_sha,
        "development_seeds": list(validated_seeds),
        "protocol": {
            "dt_seconds": D046_DT_SECONDS,
            "max_wheel_delta_rad": D046_MAX_WHEEL_DELTA_RAD,
            "nlms_step": D046_NLMS_STEP,
            "feature_map": {
                "input_scalars": 10,
                "features": 66,
                "weights": 528,
                "quadratic_order": "constant, linear x_i, x_i*x_j for i<=j",
                "output_targets": list(D046_TARGETS),
            },
            "visible_channels": list(D046_CHANNELS),
            "initial_state": dict(D046_INITIAL_OPTIONS),
            "calibration": {
                "zero_prefix_transitions": D046_ZERO_PREFIX_TRANSITIONS,
                "inverse_paired_blocks": D046_BLOCK_COUNT,
                "nonzero_command_transitions": D046_BLOCK_NONZERO_TRANSITIONS,
                "zero_suffix_transitions": D046_ZERO_SUFFIX_TRANSITIONS,
                "total_transitions": D046_CALIBRATION_TRANSITIONS,
                "block_definitions": [
                    {
                        "block_index": index,
                        "raw_command": list(command),
                        "amplitude": amplitude,
                        "length": length,
                    }
                    for index, (command, amplitude, length) in enumerate(
                        D046_BLOCK_DEFINITIONS
                    )
                ],
                "external_curriculum_rng": "random.Random(seed), block order only",
            },
            "heldout": {
                "transitions_per_frozen_learner": 81,
                "poses": [list(pose) for pose in D046_HOLDOUT_POSES],
                "actions": [list(action) for action in D046_HOLDOUT_ACTIONS],
            },
            "rollouts": {
                "horizons": [1, 2, 4, 8, "final"],
                "starts": {
                    key: list(value) for key, value in D046_ROLLOUT_STARTS.items()
                },
                "sequence_lengths": rollout_lengths,
                "commands": {
                    key: [list(command) for command in value]
                    for key, value in D046_ROLLOUTS.items()
                },
            },
        },
        "causal_isolation": {
            "learner_shadow_only": True,
            "predictions_never_select_actions": True,
            "plastic_inputs_only_current_action_and_visible_current_next": True,
            "curriculum_provenance_evaluator_side": True,
            "heldout_and_rollouts_read_only": True,
            "no_new_learner_rng": True,
            "d045_trajectory_identity_checked_against_no_learner_replay": True,
            "formal_reserved_seed_used": False,
            "reward_exactly_zero_and_info_empty": pooled_support.rewards_zero
            and pooled_support.infos_empty,
        },
        "calibration": {
            "per_seed": lifetime_payloads,
            "pooled": {
                "support": pooled_support.payload(),
                "prequential": pooled_prequential.payload(),
            },
        },
        "heldout_one_step": {
            "per_seed": heldout_payloads,
            "pooled": pooled_heldout.payload(),
        },
        "short_rollouts": {
            "per_seed": rollout_payloads,
            "pooled": pooled_rollouts.payload(),
        },
    }


def write_d046_artifact(payload: dict[str, object], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_json(payload) + b"\n")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executed-commit-sha", required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "development/D-046-v05-calibration-shadow-consequence-learning.json"
        ),
    )
    args = parser.parse_args()
    payload = run_d046_official(executed_commit_sha=args.executed_commit_sha)
    write_d046_artifact(payload, args.output)


if __name__ == "__main__":
    main()
