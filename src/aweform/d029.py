"""D-029 evaluator-only action-alternative readiness audit.

The D-026 controller, D-024 environment, and D-027 executed-action learner
remain causal.  D-029 queries every existing learner head read-only and
evaluates every candidate action in a deep-copied one-step environment.  The
branch results are aggregate evaluator diagnostics only.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import pickle
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Final, Sequence, cast

import numpy as np

from . import d024, d025, d026, d027
from .d020 import D020PhysicalConfig, D020TransitionTelemetry
from .env import Action
from .exp003 import EXP003_B50_ENTER_SEEK_THRESHOLD
from .exp003_seed_policy import validate_exp003_development_seeds
from .rng import RandomStreams

D029_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = tuple(range(18408, 18428))
D029_HORIZON: Final[int] = 70_000
D029_AUTHORITATIVE_BASE_SHA: Final[str] = (
    "91342dc68144dc2364f90b4c3847d79a4e3e7a8d"
)
D029_BASE_TREE_SHA: Final[str] = "6d91c5ce67b138298b9e416ba557a66f07b37f42"
D029_SUPPORT_CLASSES: Final[tuple[str, ...]] = ("0", ">=1", ">=2")
D029_QUARTERS: Final[tuple[str, ...]] = ("Q1", "Q2", "Q3", "Q4")
D029_BOUNDARY_CLASSES: Final[tuple[str, ...]] = (
    "FULL_NOMINAL_FORWARD",
    "BOUNDARY_CLIPPED_FORWARD",
    "FULL_STALL_FORWARD",
)
D029_OUTPUTS: Final[tuple[str, ...]] = d027.D027_OUTPUTS
D029_CHANNELS: Final[tuple[str, ...]] = d027.D027_CHANNELS
D029_ACTION_PAIRS: Final[tuple[tuple[Action, Action], ...]] = tuple(
    (left, right)
    for index, left in enumerate(Action)
    for right in tuple(Action)[index + 1 :]
)

VisibleStateKey = tuple[float, float, float, float, bool, float]
StateActionKey = tuple[VisibleStateKey, Action]


def _validate_d029_development_seeds(
    seeds: Sequence[int],
) -> tuple[int, ...]:
    """Apply the formal reservation guard and D-029's exact seed guard."""
    validated = validate_exp003_development_seeds(seeds)
    if validated != D029_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-029 requires exactly the frozen development seeds "
            f"{D029_DEFAULT_DEVELOPMENT_SEEDS}; got {validated}"
        )
    return validated


def _validate_d029_seed(seed: int) -> None:
    validated = validate_exp003_development_seeds((seed,))
    if validated[0] not in D029_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-029 may execute only predeclared development seeds "
            f"{D029_DEFAULT_DEVELOPMENT_SEEDS}; got {validated}"
        )


def _visible_state_key(observation: d027.D027Observation) -> VisibleStateKey:
    """Use exact Python values from the ordinary float32 visible channels."""
    return (
        observation.energy,
        observation.beacon.left,
        observation.beacon.forward,
        observation.beacon.right,
        observation.charging_contact,
        observation.thermal,
    )


class ExactExecutedExperienceRegistry:
    """Evaluator registry containing only prior real state/action pairs."""

    __slots__ = ("_counts",)

    def __init__(self) -> None:
        self._counts: dict[StateActionKey, int] = {}

    def support_count(
        self, observation: d027.D027Observation, action: Action
    ) -> int:
        return self._counts.get((_visible_state_key(observation), action), 0)

    def record(self, observation: d027.D027Observation, action: Action) -> None:
        key = (_visible_state_key(observation), action)
        self._counts[key] = self._counts.get(key, 0) + 1

    @property
    def unique_pair_count(self) -> int:
        return len(self._counts)


@dataclass(slots=True)
class _MetricSums:
    count: int = 0
    learned_abs_error: list[float] = field(
        default_factory=lambda: [0.0] * len(D029_OUTPUTS)
    )
    baseline_abs_error: list[float] = field(
        default_factory=lambda: [0.0] * len(D029_OUTPUTS)
    )

    def record(self, predicted: Sequence[float], actual: Sequence[float]) -> None:
        self.count += 1
        for index, (left, right) in enumerate(zip(predicted, actual, strict=True)):
            self.learned_abs_error[index] += abs(left - right)
            self.baseline_abs_error[index] += abs(right)

    def merge(self, other: _MetricSums) -> None:
        self.count += other.count
        for index in range(len(D029_OUTPUTS)):
            self.learned_abs_error[index] += other.learned_abs_error[index]
            self.baseline_abs_error[index] += other.baseline_abs_error[index]

    def as_dict(self) -> dict[str, object]:
        if self.count == 0:
            return {"status": "untested", "sample_count": 0, "targets": {}}
        targets: dict[str, object] = {}
        for index, output in enumerate(D029_OUTPUTS):
            learned = self.learned_abs_error[index] / self.count
            baseline = self.baseline_abs_error[index] / self.count
            targets[output] = {
                "learned_mae": learned,
                "zero_change_baseline_mae": baseline,
                "learned_baseline_mae_ratio": learned / baseline
                if baseline
                else None,
            }
        return {"status": "visited", "sample_count": self.count, "targets": targets}


def _new_metric_groups() -> dict[str, dict[str, _MetricSums]]:
    return {
        "all_candidates": {"all": _MetricSums()},
        "executed_vs_unexecuted": {
            "executed": _MetricSums(),
            "unexecuted": _MetricSums(),
        },
        "candidate_action": {action.name: _MetricSums() for action in Action},
        "quarter": {quarter: _MetricSums() for quarter in D029_QUARTERS},
        "prior_exact_support": {
            category: _MetricSums() for category in D029_SUPPORT_CLASSES
        },
        "current_contact": {"False": _MetricSums(), "True": _MetricSums()},
        "candidate_contact_delta": {
            "-1": _MetricSums(),
            "0": _MetricSums(),
            "+1": _MetricSums(),
        },
        "candidate_termination": {},
        "move_forward_boundary": {
            category: _MetricSums() for category in D029_BOUNDARY_CLASSES
        },
        "move_forward_boundary_Q4": {
            category: _MetricSums() for category in D029_BOUNDARY_CLASSES
        },
    }


def _record_metric(
    groups: dict[str, dict[str, _MetricSums]],
    *,
    candidate: Action,
    executed: bool,
    quarter: str,
    current: d027.D027Observation,
    support_count: int,
    contact_delta: str,
    termination_class: str,
    boundary_class: str | None,
    predicted: Sequence[float],
    actual: Sequence[float],
) -> None:
    dimensions = (
        ("all_candidates", "all"),
        ("executed_vs_unexecuted", "executed" if executed else "unexecuted"),
        ("candidate_action", candidate.name),
        ("quarter", quarter),
        ("current_contact", str(current.charging_contact)),
        ("candidate_contact_delta", contact_delta),
        ("candidate_termination", termination_class),
    )
    if support_count == 0:
        dimensions += (("prior_exact_support", "0"),)
    if support_count >= 1:
        dimensions += (("prior_exact_support", ">=1"),)
    if support_count >= 2:
        dimensions += (("prior_exact_support", ">=2"),)
    if boundary_class is not None:
        dimensions += (("move_forward_boundary", boundary_class),)
        if quarter == "Q4":
            dimensions += (("move_forward_boundary_Q4", boundary_class),)
    for dimension, category in dimensions:
        groups[dimension].setdefault(category, _MetricSums()).record(predicted, actual)


def _metric_groups_as_dict(
    groups: dict[str, dict[str, _MetricSums]],
) -> dict[str, object]:
    return {
        dimension: {
            category: metric.as_dict() for category, metric in categories.items()
        }
        for dimension, categories in groups.items()
    }


def _metric_groups_merge(
    destination: dict[str, dict[str, _MetricSums]],
    source: dict[str, dict[str, _MetricSums]],
) -> None:
    for dimension, categories in source.items():
        for category, metric in categories.items():
            destination[dimension].setdefault(category, _MetricSums()).merge(metric)


@dataclass(slots=True)
class _PairMetric:
    count: int = 0
    absolute_error_sum: list[float] = field(
        default_factory=lambda: [0.0] * len(D029_OUTPUTS)
    )
    sign_agreement_by_actual_sign: list[dict[str, int]] = field(
        default_factory=lambda: [
            {"negative": 0, "zero": 0, "positive": 0}
            for _ in D029_OUTPUTS
        ]
    )
    actual_tie_count: list[int] = field(
        default_factory=lambda: [0] * len(D029_OUTPUTS)
    )
    non_tie_count: list[int] = field(default_factory=lambda: [0] * len(D029_OUTPUTS))
    non_tie_sign_agreement_count: list[int] = field(
        default_factory=lambda: [0] * len(D029_OUTPUTS)
    )

    def record(self, predicted: Sequence[float], actual: Sequence[float]) -> None:
        self.count += 1
        for index, (predicted_value, actual_value) in enumerate(
            zip(predicted, actual, strict=True)
        ):
            self.absolute_error_sum[index] += abs(predicted_value - actual_value)
            actual_sign = _sign_name(actual_value)
            if _sign_name(predicted_value) == actual_sign:
                self.sign_agreement_by_actual_sign[index][actual_sign] += 1
            if actual_value == 0.0:
                self.actual_tie_count[index] += 1
            else:
                self.non_tie_count[index] += 1
                if _sign_name(predicted_value) == actual_sign:
                    self.non_tie_sign_agreement_count[index] += 1

    def merge(self, other: _PairMetric) -> None:
        self.count += other.count
        for index in range(len(D029_OUTPUTS)):
            self.absolute_error_sum[index] += other.absolute_error_sum[index]
        for index in range(len(D029_OUTPUTS)):
            for sign in self.sign_agreement_by_actual_sign[index]:
                self.sign_agreement_by_actual_sign[index][sign] += (
                    other.sign_agreement_by_actual_sign[index][sign]
                )
            self.actual_tie_count[index] += other.actual_tie_count[index]
            self.non_tie_count[index] += other.non_tie_count[index]
            self.non_tie_sign_agreement_count[index] += (
                other.non_tie_sign_agreement_count[index]
            )

    def as_dict(self) -> dict[str, object]:
        return {
            "sample_count": self.count,
            "pairwise_contrast_mae": [
                value / self.count if self.count else None
                for value in self.absolute_error_sum
            ],
            "exact_sign_agreement_by_actual_sign": self.sign_agreement_by_actual_sign,
            "actual_tie_count": self.actual_tie_count,
            "non_tie_count": self.non_tie_count,
            "non_tie_sign_agreement_count": self.non_tie_sign_agreement_count,
            "non_tie_sign_agreement_rate": [
                agreements / count if count else None
                for agreements, count in zip(
                    self.non_tie_sign_agreement_count,
                    self.non_tie_count,
                    strict=True,
                )
            ],
        }


class _PairwiseDiagnostics:
    __slots__ = ("overall", "by_quarter", "by_pair")

    def __init__(self) -> None:
        self.overall = _PairMetric()
        self.by_quarter = {quarter: _PairMetric() for quarter in D029_QUARTERS}
        self.by_pair = {
            _pair_name(left, right): _PairMetric()
            for left, right in D029_ACTION_PAIRS
        }

    def record(
        self,
        *,
        quarter: str,
        left: Action,
        right: Action,
        predicted: Sequence[float],
        actual: Sequence[float],
    ) -> None:
        self.overall.record(predicted, actual)
        self.by_quarter[quarter].record(predicted, actual)
        self.by_pair[_pair_name(left, right)].record(predicted, actual)

    def merge(self, other: _PairwiseDiagnostics) -> None:
        self.overall.merge(other.overall)
        for quarter in D029_QUARTERS:
            self.by_quarter[quarter].merge(other.by_quarter[quarter])
        for pair in self.by_pair:
            self.by_pair[pair].merge(other.by_pair[pair])

    def as_dict(self) -> dict[str, object]:
        return {
            "outputs": list(D029_OUTPUTS),
            "overall": self.overall.as_dict(),
            "by_quarter": {
                quarter: self.by_quarter[quarter].as_dict()
                for quarter in D029_QUARTERS
            },
            "by_action_pair": {
                pair: self.by_pair[pair].as_dict() for pair in self.by_pair
            },
        }


def _sign_name(value: float) -> str:
    if value < 0.0:
        return "negative"
    if value > 0.0:
        return "positive"
    return "zero"


def _pair_name(left: Action, right: Action) -> str:
    return f"{left.name}__vs__{right.name}"


def _contact_delta_class(delta: float) -> str:
    if delta == -1.0:
        return "-1"
    if delta == 0.0:
        return "0"
    if delta == 1.0:
        return "+1"
    raise RuntimeError(f"contact delta is not binary: {delta!r}")


def _quarter(transition: int) -> str:
    return D029_QUARTERS[(transition - 1) // d027.D027_WINDOW_SIZE]


def _termination_class(
    environment: d026.D026Env, terminated: bool, truncated: bool
) -> str:
    return d027._termination_reason(environment, terminated, truncated)


def _classify_branch_boundary(
    telemetry: D020TransitionTelemetry, action: Action
) -> tuple[str | None, bool]:
    if action is not Action.MOVE_FORWARD:
        return None, False
    displacement = math.dist(telemetry.position_before, telemetry.position_after)
    category = d027._classify_forward_displacement(displacement)
    return category, displacement <= d027.D027_BOUNDARY_TOLERANCE


@dataclass(frozen=True, slots=True)
class _BranchOutcome:
    observation: d027.D027Observation
    terminated: bool
    truncated: bool
    telemetry: D020TransitionTelemetry
    delta: tuple[float, ...]
    termination_class: str
    boundary_class: str | None
    full_stall: bool


def _environment_state(environment: d026.D026Env) -> tuple[object, ...]:
    return (
        environment.body,
        environment.station_center,
        environment.body_temperature_c,
        environment.battery_j,
        environment.charger_termination_latched,
        environment._step_count,
        environment._episode_done,
        environment.last_transition,
    )


def _controller_state(controller: d026.D026Controller) -> tuple[object, ...]:
    explorer = controller.explorer
    return (
        controller.mode,
        controller.seek_segment_starts,
        controller.last_arbitration,
        explorer._forward_actions_remaining,
        explorer._turn_action,
        explorer._turn_actions_remaining,
    )


def _digest(value: object) -> str:
    return hashlib.sha256(pickle.dumps(value, protocol=5)).hexdigest()


def _rng_state(streams: RandomStreams) -> tuple[bytes, bytes]:
    return (
        pickle.dumps(streams.environment.bit_generator.state, protocol=5),
        pickle.dumps(streams.policy.bit_generator.state, protocol=5),
    )


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
        raise RuntimeError("D-029 reset crossed the information boundary")
    if environment.body is None or environment.station_center is None:
        raise RuntimeError("D-029 reset did not initialize evaluator geometry")
    if not environment.charging_contact:
        raise RuntimeError("D-024 exact initial pose is not in dual contact")
    return environment, observation, streams


def _next_visible(observation: np.ndarray) -> d027.D027Observation:
    return d025._controller_observation(observation)


def _observed_delta(
    current: d027.D027Observation, next_observation: d027.D027Observation
) -> tuple[float, ...]:
    return (
        next_observation.energy - current.energy,
        next_observation.beacon.left - current.beacon.left,
        next_observation.beacon.forward - current.beacon.forward,
        next_observation.beacon.right - current.beacon.right,
        float(next_observation.charging_contact)
        - float(current.charging_contact),
        next_observation.thermal - current.thermal,
    )


def _branch(
    environment: d026.D026Env,
    current: d027.D027Observation,
    action: Action,
) -> _BranchOutcome:
    branch = copy.deepcopy(environment)
    observation, reward, terminated, truncated, info = branch.step(action)
    if reward != 0.0 or info != {}:
        raise RuntimeError("D-029 branch crossed the reward/info boundary")
    telemetry = branch.last_transition
    if telemetry is None:
        raise RuntimeError("D-029 branch produced no telemetry")
    next_observation = _next_visible(observation)
    boundary_class, full_stall = _classify_branch_boundary(telemetry, action)
    return _BranchOutcome(
        observation=next_observation,
        terminated=terminated,
        truncated=truncated,
        telemetry=telemetry,
        delta=_observed_delta(current, next_observation),
        termination_class=_termination_class(branch, terminated, truncated),
        boundary_class=boundary_class,
        full_stall=full_stall,
    )


def _evaluate_branches(
    environment: d026.D026Env,
    current: d027.D027Observation,
    *,
    order: Sequence[Action],
) -> dict[Action, _BranchOutcome]:
    if tuple(order) != tuple(Action) and set(order) != set(Action):
        raise ValueError("branch order must contain each Action exactly once")
    if len(tuple(order)) != len(tuple(Action)):
        raise ValueError("branch order must contain each Action exactly once")
    return {action: _branch(environment, current, action) for action in order}


def _update_digest(
    digest: Any,
    transition: int,
    action: Action,
    update: d027.D027LearningUpdate,
) -> None:
    value = {
        "transition": transition,
        "action": action.name,
        "prediction": update.prediction,
        "observed_delta": update.observed_delta,
        "errors": update.errors,
        "normalizer": update.normalizer,
    }
    digest.update(
        (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    )


def _trace_digest(trace: Sequence[object]) -> str:
    return d027._trace_digest(trace)


def _run_lifetime(
    seed: int,
    *,
    horizon: int,
    audit: bool,
    branch_order: Sequence[Action] = tuple(Action),
) -> dict[str, object]:
    _validate_d029_seed(seed)
    environment, observation_array, streams = _initial_environment(horizon, seed)
    controller = d026.D026Controller(streams.policy)
    controller.reset()
    learner = d027.D027ActionConsequencePredictor()
    registry = ExactExecutedExperienceRegistry()
    metrics = _new_metric_groups()
    pairwise = _PairwiseDiagnostics()
    trace: list[object] = []
    update_digest = hashlib.sha256()
    action_counts = {action.name: 0 for action in Action}
    mode_occupancy = {mode.name: 0 for mode in d026.D026Mode}
    mode_entry_counts = {mode.name: 0 for mode in d026.D026Mode}
    mode_entry_counts[controller.mode.name] = 1
    transitions = 0
    terminated = False
    truncated = False
    current = d025._controller_observation(observation_array)
    minimum_energy = maximum_energy = current.energy
    minimum_temperature = maximum_temperature = current.thermal
    full_departures = charger_exits = seek_entries = reacquisitions = 0
    full_recharges = redepartures = completed_cycles = 0
    active_seek = False
    recharge_active = False
    recharge_ready = False
    cycle_stage = 0
    boundary_counts = {category: 0 for category in D029_BOUNDARY_CLASSES}
    support_distribution: dict[str, int] = {}
    all_prediction_queries_read_only = True
    all_branch_environment_checks_unchanged = True
    all_branch_controller_checks_unchanged = True
    all_branch_rng_checks_unchanged = True
    all_selected_branch_matches = True
    all_real_updates_executed_action_only = True

    while not (terminated or truncated):
        if environment.body is None or environment.station_center is None:
            raise RuntimeError("D-029 evaluator geometry disappeared")
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

        support_counts = {
            candidate: registry.support_count(current, candidate)
            for candidate in Action
        }
        weights_before = learner.weights
        predictions = {
            candidate: learner.predict(current, candidate) for candidate in Action
        }
        all_prediction_queries_read_only &= learner.weights == weights_before

        environment_before = _environment_state(environment)
        controller_before = _controller_state(controller)
        rng_before = _rng_state(streams)
        if audit:
            branches = _evaluate_branches(
                environment, current, order=branch_order
            )
            all_branch_environment_checks_unchanged &= (
                _environment_state(environment) == environment_before
            )
            all_branch_controller_checks_unchanged &= (
                _controller_state(controller) == controller_before
            )
            all_branch_rng_checks_unchanged &= _rng_state(streams) == rng_before
        else:
            branches = {}

        observation_array, reward, terminated, truncated, info = environment.step(
            action
        )
        if reward != 0.0 or info != {}:
            raise RuntimeError("D-029 real transition crossed the boundary")
        telemetry = environment.last_transition
        if telemetry is None:
            raise RuntimeError("D-029 real transition produced no telemetry")
        next_observation = d025._controller_observation(observation_array)
        if audit:
            selected = branches[action]
            all_selected_branch_matches &= (
                selected.observation == next_observation
                and selected.terminated == terminated
                and selected.truncated == truncated
                and selected.telemetry == telemetry
            )

        update = learner.observe_transition(current, action, next_observation)
        all_real_updates_executed_action_only &= update.action is action
        _update_digest(update_digest, transition_index, action, update)
        if update.prediction != predictions[action].values:
            raise RuntimeError("D-029 executed pre-update prediction changed")

        trace.append(
            d025._make_trace(
                transition_index=transition_index,
                mode_before=mode_before,
                mode_after=mode_after,
                action=action,
                current=current,
                observation=observation_array,
                telemetry=telemetry,
                reward=reward,
                info=info,
            )
        )
        transitions += 1

        if audit:
            for candidate in Action:
                branch_result = branches[candidate]
                actual = branch_result.delta
                support_key = str(support_counts[candidate])
                support_distribution[support_key] = (
                    support_distribution.get(support_key, 0) + 1
                )
                boundary_class = branch_result.boundary_class
                if boundary_class is not None:
                    boundary_counts[boundary_class] += 1
                    if branch_result.full_stall:
                        boundary_counts["FULL_STALL_FORWARD"] += 1
                _record_metric(
                    metrics,
                    candidate=candidate,
                    executed=candidate is action,
                    quarter=_quarter(transition_index),
                    current=current,
                    support_count=support_counts[candidate],
                    contact_delta=_contact_delta_class(actual[4]),
                    termination_class=branch_result.termination_class,
                    boundary_class=boundary_class,
                    predicted=predictions[candidate].values,
                    actual=actual,
                )
            for left, right in D029_ACTION_PAIRS:
                predicted_contrast = tuple(
                    left_value - right_value
                    for left_value, right_value in zip(
                        predictions[left].values,
                        predictions[right].values,
                        strict=True,
                    )
                )
                actual_contrast = tuple(
                    left_value - right_value
                    for left_value, right_value in zip(
                        branches[left].delta,
                        branches[right].delta,
                        strict=True,
                    )
                )
                pairwise.record(
                    quarter=_quarter(transition_index),
                    left=left,
                    right=right,
                    predicted=predicted_contrast,
                    actual=actual_contrast,
                )

        registry.record(current, action)
        minimum_energy = min(minimum_energy, next_observation.energy)
        maximum_energy = max(maximum_energy, next_observation.energy)
        minimum_temperature = min(minimum_temperature, next_observation.thermal)
        maximum_temperature = max(maximum_temperature, next_observation.thermal)
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
        current = next_observation

    if not trace:
        raise RuntimeError("D-029 lifetime produced no transitions")
    final_weights = learner.weight_snapshot()
    return {
        "seed": seed,
        "transitions": transitions,
        "terminated": terminated,
        "truncated": truncated,
        "termination_reason": d027._termination_reason(
            environment, terminated, truncated
        ),
        "action_counts": action_counts,
        "mode_occupancy": mode_occupancy,
        "mode_entry_counts": mode_entry_counts,
        "final_mode": controller.mode.name,
        "minimum_normalized_energy": minimum_energy,
        "final_normalized_energy": current.energy,
        "maximum_normalized_energy": maximum_energy,
        "minimum_temperature": minimum_temperature,
        "final_temperature": current.thermal,
        "maximum_temperature": maximum_temperature,
        "full_departures": full_departures,
        "physical_charger_exits": charger_exits,
        "low_energy_seek_entries": seek_entries,
        "physical_reacquisitions": reacquisitions,
        "full_recharge_events": full_recharges,
        "post_recharge_redepartures": redepartures,
        "completed_energy_regulation_cycles": completed_cycles,
        "trajectory_digest": _trace_digest(trace),
        "executed_update_digest": update_digest.hexdigest(),
        "final_weights": final_weights,
        "final_weight_digest": _digest(tuple(learner.weights)),
        "final_policy_rng_digest": _digest(streams.policy.bit_generator.state),
        "final_environment_rng_digest": _digest(
            streams.environment.bit_generator.state
        ),
        "metrics": _metric_groups_as_dict(metrics),
        "pairwise_contrasts": pairwise.as_dict(),
        "support": {
            "unique_prior_real_state_action_pairs": registry.unique_pair_count,
            "prior_physically_executed_update_count_by_candidate": dict(
                action_counts
            ),
            "prior_exact_support_count_distribution": dict(
                sorted(support_distribution.items(), key=lambda item: int(item[0]))
            ),
            "sample_count": sum(
                metric.count for metric in metrics["all_candidates"].values()
            ),
        },
        "isolation": {
            "all_four_prediction_queries_read_only": all_prediction_queries_read_only,
            "all_alternative_branch_environment_checks_unchanged": (
                all_branch_environment_checks_unchanged
            ),
            "all_alternative_branch_controller_checks_unchanged": (
                all_branch_controller_checks_unchanged
            ),
            "all_alternative_branch_rng_checks_unchanged": (
                all_branch_rng_checks_unchanged
            ),
            "selected_action_branch_matches_real_transition": (
                all_selected_branch_matches
            ),
            "real_updates_executed_action_only": all_real_updates_executed_action_only,
            "branch_order": [action.name for action in branch_order],
        },
        "_trace": trace,
        "_support_registry": registry,
        "_weights": tuple(learner.weights),
        "_metric_groups": metrics,
        "_pairwise": pairwise,
    }


def _summary_fields(result: dict[str, object]) -> tuple[object, ...]:
    return tuple(
        result[name]
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
    )


def _run_d029_seed(
    seed: int,
    *,
    horizon: int = D029_HORIZON,
    branch_order: Sequence[Action] = tuple(Action),
) -> dict[str, object]:
    audited = _run_lifetime(
        seed, horizon=horizon, audit=True, branch_order=branch_order
    )
    reference = _run_lifetime(seed, horizon=horizon, audit=False)
    exact_summary = _summary_fields(audited) == _summary_fields(reference)
    exact_trace = audited["trajectory_digest"] == reference["trajectory_digest"]
    exact_weights = audited["_weights"] == reference["_weights"]
    exact_updates = audited["executed_update_digest"] == reference[
        "executed_update_digest"
    ]
    exact_rng = audited["final_policy_rng_digest"] == reference[
        "final_policy_rng_digest"
    ]
    metric_groups = audited.pop("_metric_groups")
    pairwise = audited.pop("_pairwise")
    audited.pop("_trace")
    audited.pop("_support_registry")
    audited.pop("_weights")
    audited["isolation"]["matched_d027_reference"] = {  # type: ignore[index]
        "reference": "unbranched ordinary D-027-compatible lifetime",
        "real_transition_summary_exact_equal": exact_summary,
        "real_visible_trajectory_digest_exact_equal": exact_trace,
        "final_168_weight_snapshot_exact_equal": exact_weights,
        "executed_action_pre_update_prediction_update_digest_exact_equal": (
            exact_updates
        ),
        "policy_rng_state_exact_equal": exact_rng,
        "reference_final_weight_digest": reference["final_weight_digest"],
        "reference_policy_rng_digest": reference["final_policy_rng_digest"],
        "reference_environment_rng_digest": reference["final_environment_rng_digest"],
    }
    audited["_metric_groups"] = metric_groups
    audited["_pairwise"] = pairwise
    if not all(
        (exact_summary, exact_trace, exact_weights, exact_updates, exact_rng)
    ):
        raise RuntimeError("D-029 matched ordinary lifetime isolation failed")
    return audited


def _pooled_behavior(results: Sequence[dict[str, object]]) -> dict[str, object]:
    def summed(name: str) -> int:
        return sum(cast(int, result[name]) for result in results)

    return {
        "transitions": summed("transitions"),
        "terminated_lifetimes": sum(int(cast(bool, r["terminated"])) for r in results),
        "truncated_lifetimes": sum(int(cast(bool, r["truncated"])) for r in results),
        "action_counts": {
            action.name: sum(
                cast(dict[str, int], result["action_counts"])[action.name]
                for result in results
            )
            for action in Action
        },
        "mode_occupancy": {
            mode.name: sum(
                cast(dict[str, int], result["mode_occupancy"])[mode.name]
                for result in results
            )
            for mode in d026.D026Mode
        },
        "mode_entry_counts": {
            mode.name: sum(
                cast(dict[str, int], result["mode_entry_counts"])[mode.name]
                for result in results
            )
            for mode in d026.D026Mode
        },
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


def _merge_seed_results(
    results: Sequence[dict[str, object]],
) -> tuple[dict[str, object], dict[str, object], dict[str, int]]:
    pooled_metrics = _new_metric_groups()
    pooled_pairwise = _PairwiseDiagnostics()
    pooled_support: dict[str, int] = {}
    for result in results:
        _metric_groups_merge(
            pooled_metrics,
            cast(dict[str, dict[str, _MetricSums]], result["_metric_groups"]),
        )
        pooled_pairwise.merge(cast(_PairwiseDiagnostics, result["_pairwise"]))
        for count, value in cast(
            dict[str, int],
            cast(dict[str, object], result["support"])[
                "prior_exact_support_count_distribution"
            ],
        ).items():
            pooled_support[count] = pooled_support.get(count, 0) + value
    return (
        _metric_groups_as_dict(pooled_metrics),
        pooled_pairwise.as_dict(),
        dict(sorted(pooled_support.items(), key=lambda item: int(item[0]))),
    )


def run_d029_probe(
    seeds: Sequence[int] = D029_DEFAULT_DEVELOPMENT_SEEDS,
    *,
    horizon: int = D029_HORIZON,
    executed_commit_sha: str | None = None,
) -> dict[str, object]:
    development_seeds = _validate_d029_development_seeds(seeds)
    if horizon != D029_HORIZON:
        raise ValueError("D-029 requires the frozen 70,000-transition horizon")
    if executed_commit_sha is not None and (
        len(executed_commit_sha) != 40
        or any(character not in "0123456789abcdef" for character in executed_commit_sha)
    ):
        raise ValueError("executed_commit_sha must be a 40-character lowercase SHA")
    results = [
        _run_d029_seed(seed, horizon=horizon) for seed in development_seeds
    ]
    pooled_metrics, pooled_pairwise, pooled_support = _merge_seed_results(results)
    compact_results: list[dict[str, object]] = []
    for result in results:
        result.pop("_metric_groups")
        result.pop("_pairwise")
        compact_results.append(result)
    return {
        "schema_version": 1,
        "experiment": "D-029",
        "title": "Action-alternative consequence readiness audit",
        "authoritative_base_sha": D029_AUTHORITATIVE_BASE_SHA,
        "base_tree_sha": D029_BASE_TREE_SHA,
        "implementation_probe_sha": executed_commit_sha,
        "development_seeds": list(development_seeds),
        "horizon": D029_HORIZON,
        "lifetime": "one uninterrupted causal lifetime per seed",
        "seed_policy": {
            "canonical_validator": "validate_exp003_development_seeds",
            "exact_declared_seeds": list(D029_DEFAULT_DEVELOPMENT_SEEDS),
            "formal_reservation_guard_preserved": True,
        },
        "freeze": {
            "controller": "unchanged D026Controller; false-contact SEEK delegation 1/3",
            "environment": "unchanged D026Env / D024 finite-body dual-contact physics",
            "horizon": D029_HORIZON,
            "actions": [action.name for action in Action],
            "channels": list(D029_CHANNELS),
            "outputs": list(D029_OUTPUTS),
            "learner": "unchanged D027 168-weight normalized-LMS predictor",
            "learning_rate": d027.D027_LEARNING_RATE,
            "branch_order": [action.name for action in Action],
            "support_key": (
                "exact float32-derived six-channel visible state plus action"
            ),
            "support_categories": list(D029_SUPPORT_CLASSES),
            "boundary_tolerance": d027.D027_BOUNDARY_TOLERANCE,
            "nominal_move_distance": d027.D027_NOMINAL_MOVE_DISTANCE,
        },
        "causal_order": [
            "current typed six-channel observation",
            "unchanged D026 action",
            "all four read-only D027 predictions",
            "four isolated one-step evaluator branches",
            "one real environment transition",
            "actual real next observation",
            "one unchanged D027 executed-action learner update",
            "evaluator-only aggregate diagnostics",
        ],
        "programmed": {
            "d027_scaffold_unchanged": True,
            "model_guided_action": False,
            "counterfactual_control": False,
            "new_sensor": False,
            "new_learner": False,
            "reward_driven": False,
        },
        "organism_visible": {
            "channels": list(D029_CHANNELS),
            "reward": 0.0,
            "info": {},
            "predictions_reach_controller": False,
            "branch_results_reach_learner": False,
        },
        "evaluator_only": {
            "branch_outcomes": True,
            "prior_real_support_registry": True,
            "pairwise_contrasts": True,
            "boundary_and_termination_labels": True,
            "compact_aggregate_only": True,
        },
        "pooled_behavior": _pooled_behavior(compact_results),
        "pooled_support": {
            "prior_exact_support_count_distribution": pooled_support,
            "sample_count": sum(pooled_support.values()),
            "unique_prior_real_state_action_pairs": sum(
                cast(dict[str, object], result["support"])[
                    "unique_prior_real_state_action_pairs"
                ]
                for result in compact_results
            ),
        },
        "pooled_prediction_metrics": pooled_metrics,
        "pooled_pairwise_contrasts": pooled_pairwise,
        "results": compact_results,
        "interpretation_boundary": {
            "binary_pass_threshold": False,
            "control_authorized": False,
            "success_would_only_motivate": "D-030 pre-development review",
        },
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the D-029 readiness audit.")
    parser.add_argument(
        "--seeds", type=int, nargs="+", default=list(D029_DEFAULT_DEVELOPMENT_SEEDS)
    )
    parser.add_argument("--horizon", type=int, default=D029_HORIZON)
    parser.add_argument("--executed-commit-sha")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    payload = json.dumps(
        run_d029_probe(
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
        print(f"D-029 result written to {args.output}")


if __name__ == "__main__":
    main()
