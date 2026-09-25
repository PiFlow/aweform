"""D-048 extended-exposure shadow consequence-learning curve.

This module repeats the unchanged D-046 curriculum inside one continuous
V0.5 lifetime.  The predictors remain shadow-only.  Checkpoint evaluation
uses fresh evaluator branches and read-only weight snapshots; it never
touches the live environment or learners.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

import numpy as np

from .d045 import D045Env, D045PhysicalConfig
from .d046 import (
    D046_CALIBRATION_TRANSITIONS,
    D046_CHANNELS,
    D046_DEFAULT_SEEDS,
    D046_HOLDOUT_ACTIONS,
    D046_HOLDOUT_POSES,
    D046_INITIAL_OPTIONS,
    D046_MODEL_LOWER,
    D046_MODEL_UPPER,
    D046_WEIGHT_COUNT,
    D046ConsequencePredictor,
    _ComparisonAccumulator,
    build_d046_curriculum,
    model_state_from_observation,
    quadratic_feature_map,
    validate_d046_development_seeds,
)

D048_TASK_ID: Final[str] = "D-048"
D048_AUTHORIZED_BASE_SHA: Final[str] = (
    "c401aaa0c6a60bf3cc13840c40951957854ef2ef"
)
D048_SCHEMA_VERSION: Final[str] = "D048-1"
D048_DEFAULT_SEEDS: Final[tuple[int, ...]] = D046_DEFAULT_SEEDS
D048_PASS_COUNT: Final[int] = 8
D048_TRANSITIONS_PER_PASS: Final[int] = D046_CALIBRATION_TRANSITIONS
D048_TOTAL_TRANSITIONS: Final[int] = D048_PASS_COUNT * D048_TRANSITIONS_PER_PASS
D048_CHECKPOINTS: Final[tuple[int, ...]] = (0, 1, 2, 4, 8)
D048_HOLDOUT_CANDIDATE_COUNT: Final[int] = 9 * 9
D048_HOLDOUT_PAIR_COUNT: Final[int] = 9 * 36
D048_CHANNELS: Final[tuple[str, ...]] = D046_CHANNELS


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _validate_sha(value: str) -> str:
    if len(value) != 40 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise ValueError("executed_commit_sha must be a 40-character lowercase SHA")
    return value


def _observation_tuple(observation: np.ndarray[Any, Any]) -> tuple[float, ...]:
    return tuple(float(value) for value in observation)


def _zero_state_prediction(
    state: Sequence[float],
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    current = tuple(float(value) for value in state)
    if len(current) != len(D048_CHANNELS):
        raise ValueError("model state must contain exactly eight values")
    return (0.0,) * len(D048_CHANNELS), current


@dataclass(frozen=True, slots=True)
class _FrozenPredictor:
    """Read-only snapshot with the exact D-046 prediction arithmetic."""

    weights: tuple[float, ...]
    state_only: bool

    def __post_init__(self) -> None:
        if len(self.weights) != D046_WEIGHT_COUNT:
            raise ValueError("D-046 snapshot must contain exactly 528 weights")
        if not all(math.isfinite(value) for value in self.weights):
            raise ValueError("D-046 snapshot weights must all be finite")

    @property
    def digest(self) -> str:
        return _sha256(_canonical_json(list(self.weights)))

    @property
    def summary(self) -> dict[str, object]:
        values = np.asarray(self.weights, dtype=np.float64)
        return {
            "count": len(self.weights),
            "finite": bool(np.isfinite(values).all()),
            "l2_norm": float(np.linalg.norm(values)),
            "min": min(self.weights),
            "max": max(self.weights),
        }

    def predict(
        self, observation: Sequence[float], action: Sequence[float]
    ) -> tuple[tuple[float, ...], tuple[float, ...]]:
        state = model_state_from_observation(observation)
        effective_action = (0.0, 0.0) if self.state_only else tuple(action)
        features = quadratic_feature_map(state, effective_action)
        matrix = np.asarray(self.weights, dtype=np.float64).reshape(66, 8)
        raw_delta = np.asarray(features, dtype=np.float64) @ matrix
        delta = tuple(float(value) for value in raw_delta)
        next_state = tuple(
            min(
                max(state[index] + delta[index], D046_MODEL_LOWER[index]),
                D046_MODEL_UPPER[index],
            )
            for index in range(len(D048_CHANNELS))
        )
        return delta, next_state


def _snapshot(
    predictor: D046ConsequencePredictor, *, state_only: bool
) -> _FrozenPredictor:
    return _FrozenPredictor(tuple(predictor.weights), state_only)


def _weight_diagnostics_with_change(
    predictor: D046ConsequencePredictor,
    previous_weights: tuple[float, ...] | None,
) -> dict[str, object]:
    values = predictor.weights
    if len(values) != D046_WEIGHT_COUNT or not all(
        math.isfinite(value) for value in values
    ):
        raise RuntimeError("D-046 learner weight state is invalid")
    digest = predictor.weight_digest()
    array = np.asarray(values, dtype=np.float64)
    return {
        "digest": digest,
        "count": len(values),
        "finite": True,
        "l2_norm": float(np.linalg.norm(array)),
        "l2_change_from_previous_checkpoint": (
            float(
                np.linalg.norm(
                    array - np.asarray(previous_weights, dtype=np.float64)
                )
            )
            if previous_weights is not None
            else 0.0
        ),
    }


def _environment_fingerprint(environment: D045Env) -> str:
    if environment.body is None or environment.station_center is None:
        raise RuntimeError("environment must be reset before fingerprinting")
    observation = _observation_tuple(environment._observation().as_array())
    payload = {
        "observation": observation,
        "body_position": environment.body.position,
        "heading": environment.body.heading,
        "station_center": environment.station_center,
        "battery_j": environment.battery_j,
        "body_temperature_c": environment.body_temperature_c,
        "charger_termination_latched": environment.charger_termination_latched,
        "previous_wheel_delta": environment._previous_wheel_delta,
        "step_count": environment._step_count,
        "episode_done": environment._episode_done,
        "last_transition": repr(environment.last_transition),
    }
    return _sha256(_canonical_json(payload))


@dataclass(slots=True)
class _PrequentialMetric:
    count: int = 0
    absolute_error: dict[str, list[float]] = field(
        default_factory=lambda: {
            "organism_full": [0.0] * len(D048_CHANNELS),
            "state_only": [0.0] * len(D048_CHANNELS),
            "zero_change": [0.0] * len(D048_CHANNELS),
        }
    )

    def add(
        self,
        current: Sequence[float],
        predictions: dict[str, tuple[float, ...]],
        actual: Sequence[float],
    ) -> None:
        current_values = tuple(float(value) for value in current)
        actual_values = tuple(float(value) for value in actual)
        actual_delta = tuple(
            actual_values[index] - current_values[index]
            for index in range(len(D048_CHANNELS))
        )
        self.count += 1
        for model, predicted in predictions.items():
            for index in range(len(D048_CHANNELS)):
                self.absolute_error[model][index] += abs(
                    predicted[index] - actual_delta[index]
                )

    def merge(self, other: _PrequentialMetric) -> None:
        self.count += other.count
        for model in self.absolute_error:
            for index in range(len(D048_CHANNELS)):
                self.absolute_error[model][index] += other.absolute_error[model][index]

    def payload(self) -> dict[str, object]:
        return {
            "support": self.count,
            "prequential_mae": {
                model: {
                    channel: (
                        self.absolute_error[model][index] / self.count
                        if self.count
                        else None
                    )
                    for index, channel in enumerate(D048_CHANNELS)
                }
                for model in self.absolute_error
            },
        }


@dataclass(slots=True)
class _PassDiagnostics:
    pass_index: int
    metric: _PrequentialMetric = field(default_factory=_PrequentialMetric)
    contact_event: _PrequentialMetric = field(default_factory=_PrequentialMetric)
    contact_non_event: _PrequentialMetric = field(
        default_factory=_PrequentialMetric
    )
    transitions: int = 0
    contact_entry: int = 0
    contact_exit: int = 0
    charging_positive: int = 0
    boundary_event: int = 0
    complete: bool = False

    def add(
        self,
        current: Sequence[float],
        predictions: dict[str, tuple[float, ...]],
        actual: Sequence[float],
        *,
        charging_positive: bool,
        boundary_event: bool,
    ) -> None:
        current_contact = current[5]
        actual_contact = actual[5]
        event = current_contact != actual_contact
        self.metric.add(current, predictions, actual)
        (self.contact_event if event else self.contact_non_event).add(
            current, predictions, actual
        )
        self.transitions += 1
        self.contact_entry += int(current_contact == 0.0 and actual_contact == 1.0)
        self.contact_exit += int(current_contact == 1.0 and actual_contact == 0.0)
        self.charging_positive += int(charging_positive)
        self.boundary_event += int(boundary_event)

    def payload(self) -> dict[str, object]:
        return {
            "pass_index": self.pass_index,
            "transition_count": self.transitions,
            "complete": self.complete,
            "overall": self.metric.payload(),
            "contact_strata": {
                "contact_event": self.contact_event.payload(),
                "contact_non_event": self.contact_non_event.payload(),
            },
            "support": {
                "contact_entry": self.contact_entry,
                "contact_exit": self.contact_exit,
                "charging_positive": self.charging_positive,
                "boundary_event": self.boundary_event,
            },
        }


@dataclass(slots=True)
class _ContrastAggregate:
    support: int = 0
    absolute_error_sum: float = 0.0
    sign_agreement: int = 0
    actual_ties: int = 0
    predicted_ties: int = 0
    non_tie_support: int = 0
    non_tie_sign_agreement: int = 0

    def add(self, predicted: float, actual: float) -> None:
        self.support += 1
        self.absolute_error_sum += abs(predicted - actual)
        predicted_sign = (predicted > 0.0) - (predicted < 0.0)
        actual_sign = (actual > 0.0) - (actual < 0.0)
        self.sign_agreement += int(predicted_sign == actual_sign)
        self.actual_ties += int(actual_sign == 0)
        self.predicted_ties += int(predicted_sign == 0)
        if actual_sign != 0:
            self.non_tie_support += 1
            self.non_tie_sign_agreement += int(predicted_sign == actual_sign)

    def merge(self, other: _ContrastAggregate) -> None:
        self.support += other.support
        self.absolute_error_sum += other.absolute_error_sum
        self.sign_agreement += other.sign_agreement
        self.actual_ties += other.actual_ties
        self.predicted_ties += other.predicted_ties
        self.non_tie_support += other.non_tie_support
        self.non_tie_sign_agreement += other.non_tie_sign_agreement

    def payload(self) -> dict[str, int | float | None]:
        return {
            "contrast_mae": self.absolute_error_sum / self.support
            if self.support
            else None,
            "exact_three_way_sign_agreement_rate": (
                self.sign_agreement / self.support if self.support else None
            ),
            "actual_tie_count": self.actual_ties,
            "predicted_tie_count": self.predicted_ties,
            "non_tie_sign_agreement_rate": (
                self.non_tie_sign_agreement / self.non_tie_support
                if self.non_tie_support
                else None
            ),
            "non_tie_support": self.non_tie_support,
            "support": self.support,
        }


def _new_contrast_groups() -> dict[str, dict[str, dict[str, _ContrastAggregate]]]:
    return {
        name: {}
        for name in ("pooled", "seed", "action_pair", "pose", "boundary", "contact")
    }


def _add_contrast(
    groups: dict[str, dict[str, dict[str, _ContrastAggregate]]],
    *,
    seed: int,
    pose: str,
    pair: str,
    boundary: str,
    contact: str,
    predicted: Sequence[float],
    actual: Sequence[float],
) -> None:
    dimensions = (
        ("pooled", "overall"),
        ("seed", str(seed)),
        ("action_pair", pair),
        ("pose", pose),
        ("boundary", boundary),
        ("contact", contact),
    )
    for index, channel in enumerate(D048_CHANNELS):
        for dimension, key in dimensions:
            groups[dimension].setdefault(key, {}).setdefault(
                channel, _ContrastAggregate()
            ).add(predicted[index], actual[index])


def _merge_contrast_groups(
    destination: dict[str, dict[str, dict[str, _ContrastAggregate]]],
    source: dict[str, dict[str, dict[str, _ContrastAggregate]]],
) -> None:
    for dimension, keyed_channels in source.items():
        for key, channels in keyed_channels.items():
            for channel, metric in channels.items():
                destination[dimension].setdefault(key, {}).setdefault(
                    channel, _ContrastAggregate()
                ).merge(metric)


def _contrast_payload(
    groups: dict[str, dict[str, dict[str, _ContrastAggregate]]]
) -> dict[str, dict[str, dict[str, dict[str, int | float | None]]]]:
    return {
        dimension: {
            key: {
                channel: metric.payload()
                for channel, metric in sorted(channels.items())
            }
            for key, channels in sorted(keyed_channels.items())
        }
        for dimension, keyed_channels in groups.items()
    }


@dataclass(frozen=True, slots=True)
class _Candidate:
    action_id: str
    full_delta: tuple[float, ...]
    state_delta: tuple[float, ...]
    full_next: tuple[float, ...]
    state_next: tuple[float, ...]
    actual: tuple[float, ...]
    boundary: bool
    contact_transition: bool
    outcome_digest: str


@dataclass(slots=True)
class _CheckpointEvaluation:
    seed: int
    candidate_count: int = 0
    pair_count: int = 0
    absolute: dict[str, _ComparisonAccumulator] = field(default_factory=dict)
    full_contrast: dict[str, dict[str, dict[str, _ContrastAggregate]]] = field(
        default_factory=_new_contrast_groups
    )
    state_contrast: _ContrastAggregate = field(default_factory=_ContrastAggregate)
    zero_contrast: _ContrastAggregate = field(default_factory=_ContrastAggregate)
    branch_order_invariant: bool = True
    identical_starts: bool = True
    reward_exactly_zero: bool = True
    organism_info_exactly_empty: bool = True

    def add_absolute(
        self,
        group_names: Sequence[str],
        current: Sequence[float],
        actual: Sequence[float],
        candidate: _Candidate,
    ) -> None:
        zero_delta, zero_next = _zero_state_prediction(current)
        predictions = {
            "organism_full": candidate.full_delta,
            "state_only": candidate.state_delta,
            "zero_change": zero_delta,
        }
        predicted_states = {
            "organism_full": candidate.full_next,
            "state_only": candidate.state_next,
            "zero_change": zero_next,
        }
        for group_name in group_names:
            self.absolute.setdefault(group_name, _ComparisonAccumulator()).add_row(
                current, actual, predictions, predicted_states
            )

    def merge(self, other: _CheckpointEvaluation) -> None:
        self.candidate_count += other.candidate_count
        self.pair_count += other.pair_count
        for group, accumulator in other.absolute.items():
            self.absolute.setdefault(group, _ComparisonAccumulator()).merge(accumulator)
        _merge_contrast_groups(self.full_contrast, other.full_contrast)
        self.state_contrast.merge(other.state_contrast)
        self.zero_contrast.merge(other.zero_contrast)
        self.branch_order_invariant &= other.branch_order_invariant
        self.identical_starts &= other.identical_starts
        self.reward_exactly_zero &= other.reward_exactly_zero
        self.organism_info_exactly_empty &= other.organism_info_exactly_empty

    def payload(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "support": {
                "candidate_action_evaluations": self.candidate_count,
                "unordered_action_pair_comparisons": self.pair_count,
                "channel_expanded_pair_comparisons": self.pair_count
                * len(D048_CHANNELS),
            },
            "absolute_one_step": {
                group: accumulator.payload()
                for group, accumulator in sorted(self.absolute.items())
            },
            "action_pair_discrimination": {
                "full_learner": _contrast_payload(self.full_contrast),
                "action_indifferent_comparators": {
                    "state_only": {
                        "contrast": "structural zero",
                        "pooled_by_channel": {
                            channel: self.state_contrast.payload()
                            for channel in D048_CHANNELS
                        },
                    },
                    "zero_change": {
                        "contrast": "structural zero",
                        "pooled_by_channel": {
                            channel: self.zero_contrast.payload()
                            for channel in D048_CHANNELS
                        },
                    },
                },
            },
            "causal_isolation": {
                "branch_order_invariant": self.branch_order_invariant,
                "candidate_start_observation_identical_within_seed_pose": (
                    self.identical_starts
                ),
                "source_state_unchanged_by_branches": True,
                "learner_updates": 0,
                "reward_exactly_zero": self.reward_exactly_zero,
                "organism_info_exactly_empty": self.organism_info_exactly_empty,
                "heldout_outcomes_feed_training": False,
                "evaluator_metadata_reaches_model_input": False,
            },
        }


def _evaluator_options(
    position: tuple[float, float], heading: float
) -> dict[str, object]:
    options = dict(D046_INITIAL_OPTIONS)
    options["body_position"] = position
    options["heading"] = heading
    return options


def _candidate(
    full: _FrozenPredictor,
    state_only: _FrozenPredictor,
    pose: tuple[str, float, float, float],
    action: tuple[str, float, float],
) -> tuple[tuple[float, ...], _Candidate]:
    pose_id, x, y, heading = pose
    action_id, left, right = action
    environment = D045Env(D045PhysicalConfig())
    raw_observation, reset_info = environment.reset(
        options=_evaluator_options((x, y), heading)
    )
    if reset_info != {}:
        raise RuntimeError("D-045 holdout reset exposed organism info")
    observation = _observation_tuple(raw_observation)
    full_delta, full_next = full.predict(observation, (left, right))
    state_delta, state_next = state_only.predict(observation, (left, right))
    raw_next, reward, terminated, truncated, info = environment.step((left, right))
    if reward != 0.0 or info != {} or terminated or truncated:
        raise RuntimeError("D-045 holdout violated the read-only boundary")
    next_observation = _observation_tuple(raw_next)
    current_state = model_state_from_observation(observation)
    actual_state = model_state_from_observation(next_observation)
    actual = tuple(
        actual_state[index] - current_state[index]
        for index in range(len(D048_CHANNELS))
    )
    telemetry = environment.last_transition
    if telemetry is None:
        raise RuntimeError("D-045 holdout transition telemetry missing")
    outcome = {
        "pose": pose_id,
        "action": action_id,
        "start_observation": observation,
        "next_observation": next_observation,
        "actual": actual,
        "boundary_scale": telemetry.boundary_scale,
        "contact_before": telemetry.charging_contact_before,
        "contact_after": telemetry.charging_contact_after,
    }
    return observation, _Candidate(
        action_id,
        full_delta,
        state_delta,
        full_next,
        state_next,
        actual,
        telemetry.boundary_scale < 1.0,
        telemetry.charging_contact_before != telemetry.charging_contact_after,
        _sha256(_canonical_json(outcome)),
    )


def _evaluate_checkpoint(
    seed: int,
    full: _FrozenPredictor,
    state_only: _FrozenPredictor,
) -> _CheckpointEvaluation:
    evaluation = _CheckpointEvaluation(seed)
    for pose in D046_HOLDOUT_POSES:
        forward = [
            _candidate(full, state_only, pose, action)
            for action in D046_HOLDOUT_ACTIONS
        ]
        reverse = [
            _candidate(full, state_only, pose, action)
            for action in reversed(D046_HOLDOUT_ACTIONS)
        ]
        reverse_by_id = {candidate.action_id: candidate for _, candidate in reverse}
        starts = [start for start, _ in forward]
        evaluation.identical_starts &= all(start == starts[0] for start in starts)
        evaluation.candidate_count += len(forward)
        evaluation.reward_exactly_zero &= len(forward) == len(D046_HOLDOUT_ACTIONS)
        candidates = [candidate for _, candidate in forward]
        evaluation.branch_order_invariant &= all(
            candidate.outcome_digest
            == reverse_by_id[candidate.action_id].outcome_digest
            and candidate.full_delta == reverse_by_id[candidate.action_id].full_delta
            and candidate.state_delta
            == reverse_by_id[candidate.action_id].state_delta
            for candidate in candidates
        )
        for candidate in candidates:
            boundary_key = (
                "boundary" if candidate.boundary else "non_boundary"
            )
            contact_key = (
                "contact_event"
                if candidate.contact_transition
                else "contact_non_event"
            )
            evaluation.add_absolute(
                (
                    "overall",
                    f"by_seed:{seed}",
                    f"by_start_pose:{pose[0]}",
                    f"by_action:{candidate.action_id}",
                    boundary_key,
                    contact_key,
                ),
                starts[0],
                tuple(
                    starts[0][index] + candidate.actual[index]
                    for index in range(len(D048_CHANNELS))
                ),
                candidate,
            )
        for index, first in enumerate(candidates):
            for second in candidates[index + 1 :]:
                evaluation.pair_count += 1
                pair = f"{first.action_id}-{second.action_id}"
                boundary_key = (
                    "boundary_involved"
                    if first.boundary or second.boundary
                    else "non_boundary"
                )
                contact_key = (
                    "contact_transition_involved"
                    if first.contact_transition or second.contact_transition
                    else "no_contact_transition"
                )
                predicted = tuple(
                    first.full_delta[channel] - second.full_delta[channel]
                    for channel in range(len(D048_CHANNELS))
                )
                actual = tuple(
                    first.actual[channel] - second.actual[channel]
                    for channel in range(len(D048_CHANNELS))
                )
                _add_contrast(
                    evaluation.full_contrast,
                    seed=seed,
                    pose=pose[0],
                    pair=pair,
                    boundary=boundary_key,
                    contact=contact_key,
                    predicted=predicted,
                    actual=actual,
                )
                for channel in range(len(D048_CHANNELS)):
                    evaluation.state_contrast.add(0.0, actual[channel])
                    evaluation.zero_contrast.add(0.0, actual[channel])
    if evaluation.candidate_count != D048_HOLDOUT_CANDIDATE_COUNT:
        raise RuntimeError("D-048 held-out candidate support changed")
    if evaluation.pair_count != D048_HOLDOUT_PAIR_COUNT:
        raise RuntimeError("D-048 held-out pair support changed")
    if not evaluation.branch_order_invariant or not evaluation.identical_starts:
        raise RuntimeError("D-048 branch-order or identical-start control failed")
    return evaluation


def _record_transition(
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
class _SeedExecution:
    seed: int
    curriculum_sha256: str
    pass_payloads: list[dict[str, object]]
    checkpoint_evaluations: dict[int, _CheckpointEvaluation]
    checkpoint_payloads: list[dict[str, object]]
    trajectory_digest: str
    full_digest: str
    state_only_digest: str
    final_environment_fingerprint: str
    completed_passes: int
    transitions: int
    terminated: bool
    truncated: bool
    termination_reason: str | None
    environment_reset_count: int


def _execute_seed(seed: int, *, evaluate_checkpoints: bool) -> _SeedExecution:
    curriculum = build_d046_curriculum(seed)
    environment = D045Env(D045PhysicalConfig())
    full = D046ConsequencePredictor()
    state_only = D046ConsequencePredictor(state_only=True)
    raw_observation, reset_info = environment.reset(options=dict(D046_INITIAL_OPTIONS))
    if reset_info != {}:
        raise RuntimeError("D-045 reset exposed organism info")
    observation = _observation_tuple(raw_observation)
    trajectory = hashlib.sha256()
    passes: list[dict[str, object]] = []
    checkpoint_evaluations: dict[int, _CheckpointEvaluation] = {}
    checkpoint_payloads: list[dict[str, object]] = []
    previous_full: tuple[float, ...] | None = None
    previous_state: tuple[float, ...] | None = None

    def checkpoint(pass_count: int) -> None:
        nonlocal previous_full, previous_state
        before_full_digest = full.weight_digest()
        before_state_digest = state_only.weight_digest()
        before_environment = _environment_fingerprint(environment)
        full_snapshot = _snapshot(full, state_only=False)
        state_snapshot = _snapshot(state_only, state_only=True)
        evaluation = _evaluate_checkpoint(seed, full_snapshot, state_snapshot)
        after_full_digest = full.weight_digest()
        after_state_digest = state_only.weight_digest()
        after_environment = _environment_fingerprint(environment)
        if before_full_digest != after_full_digest:
            raise RuntimeError("checkpoint evaluation changed the full learner")
        if before_state_digest != after_state_digest:
            raise RuntimeError("checkpoint evaluation changed the state-only learner")
        if before_environment != after_environment:
            raise RuntimeError("checkpoint evaluation changed live environment state")
        full_values = full.weights
        state_values = state_only.weights
        checkpoint_evaluations[pass_count] = evaluation
        checkpoint_payloads.append(
            {
                "exposure_passes": pass_count,
                "exposure_transitions": pass_count * D048_TRANSITIONS_PER_PASS,
                "weights": {
                    "full": _weight_diagnostics_with_change(full, previous_full),
                    "state_only": _weight_diagnostics_with_change(
                        state_only, previous_state
                    ),
                },
                "evaluation": evaluation.payload(),
                "causal_isolation": {
                    "live_environment_digest_before": before_environment,
                    "live_environment_digest_after": after_environment,
                    "live_environment_unchanged": True,
                    "full_digest_before": before_full_digest,
                    "full_digest_after": after_full_digest,
                    "full_digest_unchanged": True,
                    "state_only_digest_before": before_state_digest,
                    "state_only_digest_after": after_state_digest,
                    "state_only_digest_unchanged": True,
                    "heldout_evaluation_updates_live_learners": False,
                    "heldout_outcomes_feed_future_training": False,
                },
            }
        )
        previous_full = full_values
        previous_state = state_values

    if evaluate_checkpoints:
        checkpoint(0)

    completed_passes = 0
    transitions = 0
    terminated = False
    truncated = False
    termination_reason: str | None = None
    for pass_index in range(D048_PASS_COUNT):
        diagnostics = _PassDiagnostics(pass_index=pass_index + 1)
        for step in curriculum.steps:
            current_state = model_state_from_observation(observation)
            full_prediction = full.predict(observation, step.command)
            state_prediction = state_only.predict(observation, step.command)
            raw_next, reward, terminated, truncated, info = environment.step(
                step.command
            )
            next_observation = _observation_tuple(raw_next)
            full_update = full.update_from_transition(
                observation, step.command, next_observation, full_prediction
            )
            state_update = state_only.update_from_transition(
                observation, step.command, next_observation, state_prediction
            )
            next_state = model_state_from_observation(next_observation)
            telemetry = environment.last_transition
            if telemetry is None:
                raise RuntimeError("D-045 omitted transition telemetry")
            diagnostics.add(
                current_state,
                {
                    "organism_full": full_update.prediction.delta,
                    "state_only": state_update.prediction.delta,
                    "zero_change": (0.0,) * len(D048_CHANNELS),
                },
                next_state,
                charging_positive=telemetry.actual_stored_power_w > 0.0,
                boundary_event=telemetry.boundary_scale < 1.0,
            )
            _record_transition(
                trajectory,
                step.command,
                next_observation,
                reward,
                terminated,
                truncated,
                info,
            )
            observation = next_observation
            transitions += 1
            if reward != 0.0 or info != {}:
                raise RuntimeError("D-045 reward/info boundary changed")
            if terminated or truncated:
                termination_reason = (
                    telemetry.termination_reason.value
                    if telemetry.termination_reason is not None
                    else None
                )
                break
        diagnostics.complete = not terminated and not truncated
        passes.append(diagnostics.payload())
        if terminated or truncated:
            break
        completed_passes += 1
        if evaluate_checkpoints and completed_passes in D048_CHECKPOINTS:
            checkpoint(completed_passes)

    if completed_passes == D048_PASS_COUNT and transitions != D048_TOTAL_TRANSITIONS:
        raise RuntimeError("D-048 completed lifetime transition count changed")
    return _SeedExecution(
        seed=seed,
        curriculum_sha256=curriculum.sequence_sha256,
        pass_payloads=passes,
        checkpoint_evaluations=checkpoint_evaluations,
        checkpoint_payloads=checkpoint_payloads,
        trajectory_digest=trajectory.hexdigest(),
        full_digest=full.weight_digest(),
        state_only_digest=state_only.weight_digest(),
        final_environment_fingerprint=_environment_fingerprint(environment),
        completed_passes=completed_passes,
        transitions=transitions,
        terminated=terminated,
        truncated=truncated,
        termination_reason=termination_reason,
        environment_reset_count=1,
    )


def _seed_payload(
    execution: _SeedExecution,
    control: _SeedExecution,
) -> dict[str, object]:
    compact_checkpoints: list[dict[str, object]] = []
    checkpoint_controls: dict[str, object] = {}
    for row in execution.checkpoint_payloads:
        evaluation = row["evaluation"]
        if not isinstance(evaluation, dict):
            raise RuntimeError("checkpoint evaluation payload is not a mapping")
        absolute = evaluation["absolute_one_step"]
        discrimination = evaluation["action_pair_discrimination"]
        causal_isolation = row["causal_isolation"]
        if not isinstance(absolute, dict) or not isinstance(discrimination, dict):
            raise RuntimeError("checkpoint metric payload is not a mapping")
        compact_evaluation = {
            "support": evaluation["support"],
            "absolute_one_step": {"overall": absolute["overall"]},
            "action_pair_discrimination": {
                "full_learner": {
                    "pooled": discrimination["full_learner"]["pooled"]
                },
                "action_indifferent_comparators": discrimination[
                    "action_indifferent_comparators"
                ],
            },
            "causal_isolation": causal_isolation,
        }
        compact_row = {
            "exposure_passes": row["exposure_passes"],
            "exposure_transitions": row["exposure_transitions"],
            "weights": row["weights"],
            "evaluation": compact_evaluation,
        }
        compact_checkpoints.append(compact_row)
        checkpoint_controls[str(row["exposure_passes"])] = causal_isolation
    return {
        "seed": execution.seed,
        "curriculum_sequence_sha256": execution.curriculum_sha256,
        "transition_count": execution.transitions,
        "completed_passes": execution.completed_passes,
        "pass_diagnostics": execution.pass_payloads,
        "checkpoints": compact_checkpoints,
        "termination": {
            "terminated": execution.terminated,
            "truncated": execution.truncated,
            "reason": execution.termination_reason,
        },
        "lifetime_controls": {
            "fresh_zero_initialized_full_learner": True,
            "fresh_zero_initialized_state_only_learner": True,
            "environment_reset_count": execution.environment_reset_count,
            "single_continuous_environment": execution.environment_reset_count == 1,
            "single_continuous_learner": True,
            "reward_exactly_zero": True,
            "organism_info_exactly_empty": True,
            "predictions_shadow_only": True,
            "predictions_never_select_actions": True,
            "instrumented_vs_uninstrumented": {
                "trajectory_digest_equal": execution.trajectory_digest
                == control.trajectory_digest,
                "full_learner_digest_equal": execution.full_digest
                == control.full_digest,
                "state_only_learner_digest_equal": execution.state_only_digest
                == control.state_only_digest,
                "final_environment_fingerprint_equal": (
                    execution.final_environment_fingerprint
                    == control.final_environment_fingerprint
                ),
                "checkpoint_controls": checkpoint_controls,
            },
        },
    }


def _aggregate_checkpoint(
    checkpoint: int,
    evaluations: Sequence[_CheckpointEvaluation],
) -> dict[str, object]:
    if not evaluations:
        raise ValueError("checkpoint must contain at least one evaluation")
    pooled = _CheckpointEvaluation(seed=-1)
    for evaluation in evaluations:
        pooled.merge(evaluation)
    payload = pooled.payload()
    payload.pop("seed", None)
    payload["checkpoint"] = checkpoint
    payload["seed_count"] = len(evaluations)
    return payload


def run_d048_official(
    *,
    executed_commit_sha: str,
    seeds: Sequence[int] = D048_DEFAULT_SEEDS,
) -> dict[str, object]:
    """Run the complete deterministic D-048 development protocol."""
    validated_seeds = validate_d046_development_seeds(seeds)
    _validate_sha(executed_commit_sha)
    seed_results: list[dict[str, object]] = []
    evaluations_by_checkpoint: dict[int, list[_CheckpointEvaluation]] = {
        checkpoint: [] for checkpoint in D048_CHECKPOINTS
    }
    seed_checkpoint_support: dict[int, list[dict[str, object]]] = {
        checkpoint: [] for checkpoint in D048_CHECKPOINTS
    }
    for seed in validated_seeds:
        execution = _execute_seed(seed, evaluate_checkpoints=True)
        control = _execute_seed(seed, evaluate_checkpoints=False)
        seed_results.append(_seed_payload(execution, control))
        for checkpoint, evaluation in execution.checkpoint_evaluations.items():
            evaluations_by_checkpoint[checkpoint].append(evaluation)
            seed_checkpoint_support[checkpoint].append(
                {"seed": seed, "support": evaluation.payload()["support"]}
            )
    if any(
        len(evaluations_by_checkpoint[checkpoint]) != len(validated_seeds)
        for checkpoint in D048_CHECKPOINTS
    ):
        raise RuntimeError("D-048 did not reach every planned checkpoint")
    return {
        "artifact_schema_version": D048_SCHEMA_VERSION,
        "task_id": D048_TASK_ID,
        "authorized_base_sha": D048_AUTHORIZED_BASE_SHA,
        "executed_commit_sha": executed_commit_sha,
        "development_seeds": list(validated_seeds),
        "protocol": {
            "exposure_passes": D048_PASS_COUNT,
            "transitions_per_pass": D048_TRANSITIONS_PER_PASS,
            "transitions_per_completed_seed": D048_TOTAL_TRANSITIONS,
            "checkpoints_in_passes": list(D048_CHECKPOINTS),
            "checkpoints_in_transitions": [
                checkpoint * D048_TRANSITIONS_PER_PASS
                for checkpoint in D048_CHECKPOINTS
            ],
            "curriculum": (
                "exact D-046 seed-specific 564-step sequence repeated unchanged"
            ),
            "curriculum_rng": "D-046 random.Random(seed), block order only",
            "visible_channels": list(D048_CHANNELS),
            "heldout_poses": [list(pose) for pose in D046_HOLDOUT_POSES],
            "heldout_actions": [list(action) for action in D046_HOLDOUT_ACTIONS],
            "heldout_candidate_evaluations_per_seed_checkpoint": (
                D048_HOLDOUT_CANDIDATE_COUNT
            ),
            "heldout_pair_comparisons_per_seed_checkpoint": D048_HOLDOUT_PAIR_COUNT,
            "pair_orientation": "ascending action ID",
            "state_only_comparator": "action-indifferent structural zero",
            "zero_change_comparator": "action-indifferent structural zero",
            "evaluation": "fresh isolated one-step D-045 branches; no lived trajectory",
        },
        "causal_isolation": {
            "fresh_lifetime_per_seed": True,
            "fresh_zero_initialized_learners": True,
            "one_continuous_environment_per_seed": True,
            "one_continuous_learner_per_seed": True,
            "checkpoint_evaluation_read_only": True,
            "heldout_outcomes_feed_learning": False,
            "predictions_shadow_only": True,
            "predictions_never_select_actions": True,
            "reward_exactly_zero": True,
            "organism_info_exactly_empty": True,
            "evaluator_metadata_reaches_model_input": False,
            "formal_reserved_seed_used": False,
        },
        "checkpoints": {
            str(checkpoint): {
                "per_seed_support": seed_checkpoint_support[checkpoint],
                "pooled": _aggregate_checkpoint(
                    checkpoint, evaluations_by_checkpoint[checkpoint]
                ),
            }
            for checkpoint in D048_CHECKPOINTS
        },
        "per_seed": seed_results,
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "platform": platform.platform(),
        },
        "generation_command": (
            "python -m aweform.d048 --executed-commit-sha " + executed_commit_sha
        ),
    }


def write_artifact(payload: dict[str, object], output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(_canonical_json(payload) + b"\n")
    return output


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executed-commit-sha", required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "development/D-048-v05-extended-exposure-shadow-learning-curve.json"
        ),
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    payload = run_d048_official(executed_commit_sha=args.executed_commit_sha)
    write_artifact(payload, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
