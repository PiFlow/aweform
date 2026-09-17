"""D-040 evaluator-only causal validity and problem-identification audit.

The module deliberately owns the validity-critical replay machinery.  It uses
the accepted low-level environment, controller, and learner primitives, but
does not import any of the later audit modules.  In particular, anchor
selection, state cloning, branch execution, target construction, and the
headline causal contrasts are local to this module.

No function in this module changes the canonical organism.  All treatment
branches are evaluator-only clones of a pre-action state and retain reward
``0.0`` and organism-facing ``info == {}``.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import pickle
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Final, cast

import numpy as np

from . import d024, d025, d026, d027
from .d020 import D020PhysicalConfig
from .env import Action
from .exp001 import ExternalObservation, StochasticPersistentExplorer
from .exp003 import EXP003_B50_ENTER_SEEK_THRESHOLD, seek_beacon_action
from .exp003_seed_policy import validate_exp003_development_seeds
from .rng import RandomStreams

D040_AUTHORITATIVE_BASE_SHA: Final[str] = "833beeabd0d50ad94e1c265873b1c024634c87e4"
D040_D031R1_ACCEPTED_ARTIFACT_SHA256: Final[str] = (
    "ae5095135f4a9618fb81b815bd201312a7c2bc979eca88499f7b097dc8905b61"
)
D040_D034_ACCEPTED_ARTIFACT_SHA256: Final[str] = (
    "e0d5cbdffc4e3fb429eddcbcf5af0ff4f6772eaca0368459acc1e90ed6680e1d"
)
D040_INVALIDATED_PROVENANCE: Final[tuple[dict[str, object], ...]] = (
    {
        "executable_sha": "db2facbb29a295fd00f02e5e91371bf001ed19da",
        "reused_artifact_sha256": (
            "88cf8d0872f966e4f867ab236e9b991c6508c9489d25e8d100c1dec3ca96d113"
        ),
        "reused_artifact_size_bytes": 162_684_976,
        "holdout_artifact_sha256": (
            "05da0c2728e7c009520a0b1d5002a8cc021ae2a90b30423c00858f991b9052c5"
        ),
        "holdout_artifact_size_bytes": 324_675_921,
        "status": "invalidated_by_Sol",
        "reason": "six bounded Sol-requested D-040 protocol corrections",
        "interpret_as_valid_d040_output": False,
    },
    {
        "executable_sha": "c9b017e63d4f4b01f32afa55efab257153d1d7bb",
        "reused_artifact_sha256": (
            "a28fa81cdd6f00665b162ead6e25dc5ad3ffd8a01924d4147406f1d228bf457f"
        ),
        "reused_artifact_size_bytes": 168_791_151,
        "holdout_artifact_sha256": (
            "2458da4a3d09f86a362a6c3910d6b3bf8dd3d3ce28ac62f77f81211e9351be41"
        ),
        "holdout_artifact_size_bytes": 336_622_010,
        "status": "invalidated_by_Sol",
        "reason": "D-040 artifact contract was not compact or independently reviewable",
        "interpret_as_valid_d040_output": False,
    },
)
D040_REUSED_SEEDS: Final[tuple[int, ...]] = tuple(range(18468, 18488))
D040_HOLDOUT_SEEDS: Final[tuple[int, ...]] = tuple(range(18488, 18508))
D040_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = D040_REUSED_SEEDS
D040_HORIZON: Final[int] = 70_000
D040_BRANCH_HORIZON: Final[int] = 4_096
D040_HORIZONS: Final[tuple[int, ...]] = (64, 256, 1024, 4096)
D040_ANCHOR_OFFSETS: Final[tuple[int, ...]] = (
    0,
    1,
    3,
    7,
    15,
    31,
    63,
    127,
    255,
    511,
    1023,
    2047,
    4095,
    8191,
)
D040_D034_LENGTHS: Final[tuple[int, ...]] = (4, 8, 16)
D040_D034_FAMILIES: Final[tuple[str, ...]] = (
    "ALT",
    "NO_FORWARD_PROGRESS",
)
D040_TRAJECTORY_WINDOWS: Final[tuple[int, ...]] = (16, 64, 256, 1024)
D040_READOUT_ALPHA: Final[float] = 0.01
D040_FEATURE_FAMILIES: Final[tuple[str, ...]] = (
    "F0_S0",
    "F1_S0_H4",
    "F1_S0_H8",
    "F1_S0_H16",
    "F2_S0_D027",
    "F3_S0_h",
    "F4_CLOSURE_TIMING",
    "F5_PRIVILEGED_GEOMETRY",
)
D040_BRANCHES: Final[tuple[str, ...]] = ("DETRAP_OFF", "DETRAP_ON")
D040_COMPARABLE_FIELDS: Final[tuple[str, ...]] = (
    "trajectory_digest",
    "executed_update_digest",
    "outcome_classification",
    "transitions",
    "terminated",
    "truncated",
    "termination_reason",
    "action_counts",
    "mode_occupancy",
    "mode_entry_counts",
    "seek_arbitration",
    "final_policy_rng_digest",
    "final_environment_rng_digest",
    "final_weight_digest",
    "reward_zero_every_transition",
    "organism_info_empty_every_transition",
)
D040_D034_EXPECTED: Final[dict[str, dict[str, int]]] = {
    "ALT_4": {"available": 18, "off_reacquired": 0, "on_reacquired": 18},
    "ALT_8": {"available": 17, "off_reacquired": 0, "on_reacquired": 17},
    "ALT_16": {"available": 17, "off_reacquired": 0, "on_reacquired": 16},
    "NO_FORWARD_PROGRESS_4": {
        "available": 20,
        "off_reacquired": 0,
        "on_reacquired": 20,
    },
    "NO_FORWARD_PROGRESS_8": {
        "available": 20,
        "off_reacquired": 0,
        "on_reacquired": 20,
    },
    "NO_FORWARD_PROGRESS_16": {
        "available": 20,
        "off_reacquired": 0,
        "on_reacquired": 20,
    },
}
_TURN_ACTIONS: Final[frozenset[Action]] = frozenset(
    (Action.TURN_LEFT, Action.TURN_RIGHT)
)
_STEERING_ACTIONS: Final[tuple[Action, ...]] = (
    Action.TURN_LEFT,
    Action.TURN_RIGHT,
    Action.MOVE_FORWARD,
)
_ACTION_NAMES: Final[tuple[str, ...]] = tuple(action.name for action in Action)


def _digest(value: object) -> str:
    return hashlib.sha256(pickle.dumps(value, protocol=5)).hexdigest()


def _canonical_json_digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def _validate_seed_block(
    seeds: Sequence[int], expected: tuple[int, ...], label: str
) -> tuple[int, ...]:
    validated = validate_exp003_development_seeds(seeds)
    if validated != expected:
        raise ValueError(
            f"D-040 requires exactly the {label} seeds {expected}; got {validated}"
        )
    return validated


def _validate_reused_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    return _validate_seed_block(seeds, D040_REUSED_SEEDS, "reused")


def _validate_holdout_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    return _validate_seed_block(seeds, D040_HOLDOUT_SEEDS, "fresh holdout")


def _validate_seed(seed: int, *, holdout: bool = False) -> None:
    expected = D040_HOLDOUT_SEEDS if holdout else D040_REUSED_SEEDS
    validated = validate_exp003_development_seeds((seed,))
    if validated[0] not in expected:
        label = "fresh holdout" if holdout else "reused"
        raise ValueError(f"D-040 {label} seed is outside the declared block: {seed}")


def _validate_executed_commit_sha(value: str | None) -> str:
    if (
        value is None
        or len(value) != 40
        or any(c not in "0123456789abcdef" for c in value)
    ):
        raise ValueError("D-040 requires an exact clean executable SHA")
    return value


def _initial_environment(
    horizon: int, seed: int
) -> tuple[d026.D026Env, np.ndarray, RandomStreams]:
    environment = d026.D026Env(replace(D020PhysicalConfig(), episode_horizon=horizon))
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
    if info != {} or environment.body is None or environment.station_center is None:
        raise RuntimeError("D-040 reset crossed the accepted environment boundary")
    if not environment.charging_contact:
        raise RuntimeError("D-040 exact initial pose is not in dual contact")
    return environment, observation, streams


def _next_visible(observation: np.ndarray) -> d027.D027Observation:
    return d025._controller_observation(observation)


def _is_false_contact_seek(row: d025.D025TransitionTrace) -> bool:
    """Return the pre-action eligibility predicate for a trace row.

    Both sides of the transition are part of the accepted D-034 eligibility
    semantics.  This keeps a contact or mode transition from closing a
    history window while still preventing any branch outcome from entering
    anchor selection.
    """
    return (
        row.mode_before is d026.D026Mode.SEEK
        and row.mode_after is d026.D026Mode.SEEK
        and row.observation_before[4] == 0.0
        and row.observation[4] == 0.0
    )


def _is_eligible_current(
    controller: d026.D026Controller, current: d027.D027Observation
) -> bool:
    """Pre-action form used before a transition has been executed."""
    return controller.mode is d026.D026Mode.SEEK and not current.charging_contact


def _strict_alternation(actions: Sequence[Action]) -> bool:
    return len(actions) >= 2 and all(
        left in _TURN_ACTIONS and right in _TURN_ACTIONS and left is not right
        for left, right in zip(actions, actions[1:], strict=False)
    )


@dataclass(frozen=True, slots=True)
class _TriggerSelection:
    family: str
    length: int
    transition: int
    last_transition: int
    rows: tuple[d025.D025TransitionTrace, ...]
    starting_forward: float


def _trigger_matches(
    family: str, rows: Sequence[d025.D025TransitionTrace]
) -> tuple[bool, float]:
    if not rows or not all(_is_false_contact_seek(row) for row in rows):
        return False, 0.0
    starting_forward = rows[0].observation_before[2]
    if family == "ALT":
        return _strict_alternation([row.action for row in rows]), starting_forward
    if family == "NO_FORWARD_PROGRESS":
        return max(
            row.observation[2] for row in rows
        ) <= starting_forward, starting_forward
    raise ValueError(f"unknown D-040 trigger family: {family}")


def _find_d034_trigger(
    trace: Sequence[d025.D025TransitionTrace], family: str, length: int
) -> _TriggerSelection | None:
    if family not in D040_D034_FAMILIES:
        raise ValueError(f"unknown D-034 trigger family: {family}")
    if length not in D040_D034_LENGTHS:
        raise ValueError(f"D-034 history length must be one of {D040_D034_LENGTHS}")
    for end in range(length - 1, len(trace)):
        rows = tuple(trace[end - length + 1 : end + 1])
        matches, starting_forward = _trigger_matches(family, rows)
        if matches:
            last_transition = rows[-1].transition_index
            next_transition = last_transition + 1
            if next_transition > len(trace):
                return None
            return _TriggerSelection(
                family,
                length,
                next_transition,
                last_transition,
                rows,
                starting_forward,
            )
    return None


def _find_prefix_trigger(
    trace: Sequence[d025.D025TransitionTrace], family: str, length: int
) -> _TriggerSelection | None:
    """Find a trigger whose next transition is the current prefix boundary."""
    if family not in D040_D034_FAMILIES:
        raise ValueError(f"unknown D-034 trigger family: {family}")
    if length not in D040_D034_LENGTHS:
        raise ValueError(f"D-034 history length must be one of {D040_D034_LENGTHS}")
    for end in range(length - 1, len(trace)):
        rows = tuple(trace[end - length + 1 : end + 1])
        matches, starting_forward = _trigger_matches(family, rows)
        if matches:
            last_transition = rows[-1].transition_index
            return _TriggerSelection(
                family,
                length,
                last_transition + 1,
                last_transition,
                rows,
                starting_forward,
            )
    return None


def _log_spaced_offsets() -> tuple[int, ...]:
    return D040_ANCHOR_OFFSETS


def _trigger_history(selection: _TriggerSelection) -> dict[str, object]:
    rows = [
        {
            "transition": row.transition_index,
            "action": row.action.name,
            "observation_before": list(row.observation_before),
            "observation_after": list(row.observation),
        }
        for row in selection.rows
    ]
    return {
        "family": selection.family,
        "length": selection.length,
        "last_completed_transition": selection.last_transition,
        "anchor_transition": selection.transition,
        "starting_beacon_forward": selection.starting_forward,
        "completed_actions": [row["action"] for row in rows],
        "completed_observation_count": len(rows),
        "closure_valid_history_digest": _digest(rows),
        "uses_only_executed_actions_and_six_channel_observations": True,
        "hidden_geometry_or_future_outcome_used": False,
    }


def _environment_state(environment: d026.D026Env) -> tuple[object, ...]:
    return (
        copy.deepcopy(environment.body),
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


def _rng_state(streams: RandomStreams) -> tuple[object, object]:
    return (
        copy.deepcopy(streams.environment.bit_generator.state),
        copy.deepcopy(streams.policy.bit_generator.state),
    )


def _clone_environment(environment: d026.D026Env) -> d026.D026Env:
    branch = copy.copy(environment)
    branch.body = copy.deepcopy(environment.body)
    branch.last_transition = environment.last_transition
    return branch


def _clone_streams(streams: RandomStreams) -> RandomStreams:
    result = RandomStreams.from_seed(0)
    result.environment.bit_generator.state = copy.deepcopy(
        streams.environment.bit_generator.state
    )
    result.policy.bit_generator.state = copy.deepcopy(
        streams.policy.bit_generator.state
    )
    return result


def _learner_from_weights(
    weights: Sequence[float],
) -> d027.D027ActionConsequencePredictor:
    if len(weights) != d027.D027_PLASTIC_STATE_DIMENSION:
        raise ValueError("D-040 requires the complete 168-weight D-027 state")
    learner = d027.D027ActionConsequencePredictor()
    iterator = iter(weights)
    private = cast(Any, learner)
    private._weights = {
        action: [
            [float(next(iterator)) for _ in range(d027.D027_FEATURE_DIMENSION)]
            for _ in d027.D027_OUTPUTS
        ]
        for action in Action
    }
    return learner


def _query_steering_predictions(
    learner: d027.D027ActionConsequencePredictor,
    current: d027.D027Observation,
) -> tuple[dict[Action, d027.D027Prediction], bool]:
    before = learner.weights
    values = {action: learner.predict(current, action) for action in _STEERING_ACTIONS}
    return values, values is not None and learner.weights == before


def _choose_steering_action(
    current: d027.D027Observation,
    predictions: dict[Action, d027.D027Prediction],
    greedy_action: Action,
) -> Action:
    scores = {
        action: current.beacon.forward + predictions[action].values[2]
        for action in _STEERING_ACTIONS
    }
    maximum = max(scores.values())
    winners = tuple(action for action in _STEERING_ACTIONS if scores[action] == maximum)
    return winners[0] if len(winners) == 1 else greedy_action


def _update_digest_item(
    digest: Any, transition: int, action: Action, update: d027.D027LearningUpdate
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


def _state_digest(
    environment: d026.D026Env,
    controller: d026.D026Controller,
    streams: RandomStreams,
    learner: d027.D027ActionConsequencePredictor,
    current: d027.D027Observation,
) -> str:
    return _digest(
        (
            _environment_state(environment),
            _controller_state(controller),
            _rng_state(streams),
            learner.weights,
            current,
        )
    )


@dataclass(slots=True)
class _Anchor:
    seed: int
    anchor_id: str
    transition: int
    ordinal: int | None
    current: d027.D027Observation
    environment: d026.D026Env
    controller: d026.D026Controller
    streams: RandomStreams
    learner_weights: tuple[float, ...]
    prefix: tuple[d025.D025TransitionTrace, ...]
    h_before: float
    trigger: dict[str, object] | None = None

    @property
    def state_digest(self) -> str:
        learner = _learner_from_weights(self.learner_weights)
        return _state_digest(
            self.environment, self.controller, self.streams, learner, self.current
        )


def _capture_anchor(
    seed: int,
    anchor_id: str,
    transition: int,
    ordinal: int | None,
    current: d027.D027Observation,
    environment: d026.D026Env,
    controller: d026.D026Controller,
    streams: RandomStreams,
    learner: d027.D027ActionConsequencePredictor,
    trace: Sequence[d025.D025TransitionTrace],
    h_before: float,
    trigger: dict[str, object] | None = None,
) -> _Anchor:
    controller_copy = copy.copy(controller)
    controller_copy.explorer = copy.copy(controller.explorer)
    if hasattr(controller_copy.explorer, "owner"):
        controller_copy.explorer.owner = controller_copy
    return _Anchor(
        seed,
        anchor_id,
        transition,
        ordinal,
        current,
        _clone_environment(environment),
        controller_copy,
        _clone_streams(streams),
        tuple(learner.weights),
        tuple(trace),
        h_before,
        trigger,
    )


class _CountingExplorer(StochasticPersistentExplorer):
    """Local evaluator counter; it does not alter explorer behaviour."""

    def __init__(self, policy_rng: np.random.Generator, owner: object) -> None:
        super().__init__(policy_rng)
        self.owner = owner

    def act(self, observation: ExternalObservation) -> Action:
        if getattr(self.owner, "mode") is d026.D026Mode.SEEK:
            calls = int(getattr(self.owner, "false_contact_seek_explorer_calls", 0))
            setattr(self.owner, "false_contact_seek_explorer_calls", calls + 1)
        return super().act(observation)


class _IndependentController(d026.D026Controller):
    """Task-local no-de-trap controller, independently defined from D-031R1."""

    seek_delegation_probability = 0.0

    def __init__(self, policy_rng: np.random.Generator) -> None:
        super().__init__(policy_rng)
        self.false_contact_seek_explorer_calls = 0
        self.explorer = _CountingExplorer(policy_rng, self)


class _DetrapController(d026.D026Controller):
    """Task-local ON controller changing only the inherited probability."""

    seek_delegation_probability = d026.D026_SEEK_DELEGATION_PROBABILITY

    def __init__(self, policy_rng: np.random.Generator) -> None:
        super().__init__(policy_rng)
        self.false_contact_seek_explorer_calls = 0
        self.explorer = _CountingExplorer(policy_rng, self)


def _controller_clone_for_branch(
    anchor: _Anchor, condition: str, streams: RandomStreams
) -> d026.D026Controller:
    if condition == "DETRAP_OFF":
        controller: d026.D026Controller = _IndependentController(streams.policy)
    elif condition == "DETRAP_ON":
        controller = _DetrapController(streams.policy)
    else:
        raise ValueError(f"unknown D-040 branch condition: {condition}")
    controller.mode = anchor.controller.mode
    controller.seek_segment_starts = anchor.controller.seek_segment_starts
    controller.last_arbitration = anchor.controller.last_arbitration
    controller.explorer = copy.copy(anchor.controller.explorer)
    controller.explorer.policy_rng = streams.policy
    if hasattr(controller.explorer, "owner"):
        controller.explorer.owner = controller
    return controller


def _one_step_truth(
    environment: d026.D026Env,
    current: d027.D027Observation,
    action: Action,
) -> float:
    """Evaluator-only forward consequence for one cloned candidate step."""
    branch = _clone_environment(environment)
    observation, reward, terminated, truncated, info = branch.step(action)
    if reward != 0.0 or info != {}:
        raise RuntimeError("D-040 truth branch crossed the organism boundary")
    del terminated, truncated
    next_visible = _next_visible(observation)
    return next_visible.beacon.forward - current.beacon.forward


def _run_branch(
    anchor: _Anchor,
    *,
    condition: str,
    horizon: int = D040_BRANCH_HORIZON,
) -> tuple[dict[str, object], tuple[d025.D025TransitionTrace, ...]]:
    if condition not in D040_BRANCHES:
        raise ValueError(f"unknown D-040 branch condition: {condition}")
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon <= 0:
        raise ValueError("branch horizon must be a positive integer")
    environment = _clone_environment(anchor.environment)
    streams = _clone_streams(anchor.streams)
    controller = _controller_clone_for_branch(anchor, condition, streams)
    learner = _learner_from_weights(anchor.learner_weights)
    current = anchor.current
    trace: list[d025.D025TransitionTrace] = []
    update_digest = hashlib.sha256()
    actions = {name: 0 for name in _ACTION_NAMES}
    mode_counts = {mode.name: 0 for mode in d026.D026Mode}
    mode_entries = {mode.name: 0 for mode in d026.D026Mode}
    mode_entries[controller.mode.name] = 1
    terminated = truncated = False
    reacquisition: int | None = None
    first_delegation: int | None = None
    first_delegated_action: str | None = None
    first_delegation_truth: dict[str, object] | None = None
    delegation_count = 0
    max_alternation = 0
    alternation_run = 0
    reward_zero = True
    info_empty = True
    d027_summaries: list[dict[str, object]] = []
    for local in range(1, horizon + 1):
        mode_before = controller.mode
        mode_counts[mode_before.name] += 1
        proposed = controller.act(current)
        mode_after = controller.mode
        if mode_after is not mode_before:
            mode_entries[mode_after.name] += 1
        action = proposed
        arbitration = controller.last_arbitration
        if arbitration is not None:
            predictions, read_only = _query_steering_predictions(learner, current)
            if not read_only:
                raise RuntimeError("D-040 prediction query mutated D-027 state")
            if not arbitration.delegated:
                action = _choose_steering_action(
                    current, predictions, arbitration.greedy_action
                )
            elif first_delegation is None:
                first_delegation = local
                first_delegated_action = action.name
                truth = {
                    candidate.name: _one_step_truth(environment, current, candidate)
                    for candidate in _STEERING_ACTIONS
                }
                first_delegation_truth = {
                    "action_forward_delta": truth[action.name],
                    "candidate_forward_deltas": truth,
                    "truth_best_actions": [
                        name
                        for name, value in truth.items()
                        if value == max(truth.values())
                    ],
                    "delegated_action_truth_best": truth[action.name]
                    == max(truth.values()),
                }
            delegation_count += int(arbitration.delegated)
        observation_array, reward, terminated, truncated, info = environment.step(
            action
        )
        reward_zero &= reward == 0.0
        info_empty &= info == {}
        telemetry = environment.last_transition
        if telemetry is None:
            raise RuntimeError("D-040 branch produced no telemetry")
        next_observation = _next_visible(observation_array)
        update = learner.observe_transition(current, action, next_observation)
        _update_digest_item(update_digest, local, action, update)
        d027_summaries.append(
            {
                "transition": local,
                "action": action.name,
                "prediction_forward": update.prediction[2],
                "observed_delta_forward": update.observed_delta[2],
                "error_forward": update.errors[2],
                "normalizer": update.normalizer,
                "update_l2_norm": float(
                    np.linalg.norm(np.asarray(update.errors, dtype=float))
                ),
            }
        )
        row = d025._make_trace(
            transition_index=anchor.transition + local - 1,
            mode_before=mode_before,
            mode_after=mode_after,
            action=action,
            current=current,
            observation=observation_array,
            telemetry=telemetry,
            reward=reward,
            info=info,
        )
        trace.append(row)
        actions[action.name] += 1
        if (
            telemetry.charging_contact_before is False
            and telemetry.charging_contact_after is True
            and reacquisition is None
        ):
            reacquisition = local
        if _is_false_contact_seek(row):
            if (
                alternation_run
                and len(trace) > 1
                and trace[-2].action in _TURN_ACTIONS
                and action in _TURN_ACTIONS
                and trace[-2].action is not action
            ):
                alternation_run += 1
            else:
                alternation_run = 1 if action in _TURN_ACTIONS else 0
        else:
            alternation_run = 0
        max_alternation = max(max_alternation, alternation_run)
        current = next_observation
        if reacquisition is not None or terminated or truncated:
            break
    reason = d027._termination_reason(environment, terminated, truncated)
    result = {
        "seed": anchor.seed,
        "anchor_id": anchor.anchor_id,
        "condition": condition,
        "transitions": len(trace),
        "terminated": terminated,
        "truncated": truncated,
        "termination_reason": reason,
        "final_mode": controller.mode.name,
        "reacquired": reacquisition is not None,
        "reacquisition_latency": reacquisition,
        "first_delegation": first_delegation,
        "first_delegated_action": first_delegated_action,
        "first_delegation_truth": first_delegation_truth,
        "action_counts": actions,
        "mode_occupancy": mode_counts,
        "mode_entry_counts": mode_entries,
        "longest_strict_alternation": max_alternation,
        "seek_arbitration": {
            "false_contact_seek_decisions": sum(
                int(_is_false_contact_seek(row)) for row in trace
            ),
            "stochastic_delegation_decisions": delegation_count,
            "legacy_arbitration_draw_count": sum(
                int(_is_false_contact_seek(row)) for row in trace
            ),
            "false_contact_seek_explorer_calls": getattr(
                controller, "false_contact_seek_explorer_calls", 0
            ),
            "one_policy_rng_draw_per_decision": True,
        },
        "trajectory_digest": d027._trace_digest(trace),
        "executed_update_digest": update_digest.hexdigest(),
        "final_weight_digest": _digest(learner.weights),
        "final_policy_rng_digest": _digest(streams.policy.bit_generator.state),
        "final_environment_rng_digest": _digest(
            streams.environment.bit_generator.state
        ),
        "reward_zero_every_transition": reward_zero,
        "organism_info_empty_every_transition": info_empty,
        # Retained only for evaluator-side window summaries below; this is
        # deliberately not part of the branch artifact or any causal input.
        "_d027_summaries": d027_summaries,
        "evaluator_only": True,
        "organism_state_changed": False,
    }
    return result, tuple(trace)


def _current_alternation_run(trace: Sequence[d025.D025TransitionTrace]) -> int:
    actions: list[Action] = []
    for row in reversed(trace):
        if not _is_false_contact_seek(row):
            break
        actions.append(row.action)
    actions.reverse()
    return len(actions) if _strict_alternation(actions) else 0


def _independent_arm_b(
    seed: int,
    *,
    horizon: int = D040_HORIZON,
    capture_anchors: bool = True,
) -> tuple[
    dict[str, object], tuple[d025.D025TransitionTrace, ...], dict[str, _Anchor | None]
]:
    """Run Arm-B sequencing without any later audit helper."""
    _validate_seed(seed, holdout=seed in D040_HOLDOUT_SEEDS)
    environment, observation_array, streams = _initial_environment(horizon, seed)
    controller = _IndependentController(streams.policy)
    controller.reset()
    learner = d027.D027ActionConsequencePredictor()
    current = _next_visible(observation_array)
    trace: list[d025.D025TransitionTrace] = []
    update_digest = hashlib.sha256()
    actions = {name: 0 for name in _ACTION_NAMES}
    mode_counts = {mode.name: 0 for mode in d026.D026Mode}
    mode_entries = {mode.name: 0 for mode in d026.D026Mode}
    mode_entries[controller.mode.name] = 1
    arbitration_digest = hashlib.sha256()
    arbitration_count = 0
    anchors: dict[str, _Anchor | None] = {
        f"OFFSET_{offset}": None for offset in D040_ANCHOR_OFFSETS
    }
    anchors.update(
        {
            f"{family}_{length}": None
            for family in D040_D034_FAMILIES
            for length in D040_D034_LENGTHS
        }
    )
    anchors["OSCILLATION_ONSET"] = None
    ordinal = 0
    h = 0.0
    terminated = truncated = False
    reward_zero = True
    info_empty = True
    full_departures = charger_exits = reacquisitions = 0
    full_recharges = redepartures = completed_cycles = 0
    recharge_active = recharge_ready = False
    cycle_stage = 0
    active_seek = False
    first_episode_started = False
    first_episode_complete = False
    alternation_run = 0
    oscillation_run_start: _Anchor | None = None
    while not (terminated or truncated) and len(trace) < horizon:
        # Every capture happens before controller.act and therefore cannot see
        # this transition's action, consequence, branch result, or outcome.
        pre_action_oscillation_candidate: _Anchor | None = None
        if (
            capture_anchors
            and not first_episode_complete
            and _is_eligible_current(controller, current)
        ):
            # The action may later prove to be the first action of a run.  Keep
            # the exact pre-action state so a run that reaches H16 can point
            # back to its first action without looking into the future.
            pre_action_oscillation_candidate = _capture_anchor(
                seed,
                "_OSCILLATION_CANDIDATE",
                len(trace) + 1,
                None,
                current,
                environment,
                controller,
                streams,
                learner,
                trace,
                h,
            )
        for offset in D040_ANCHOR_OFFSETS:
            if (
                ordinal == offset
                and not first_episode_complete
                and capture_anchors
                and controller.mode is d026.D026Mode.SEEK
                and not current.charging_contact
            ):
                anchors[f"OFFSET_{offset}"] = _capture_anchor(
                    seed,
                    f"OFFSET_{offset}",
                    len(trace) + 1,
                    ordinal,
                    current,
                    environment,
                    controller,
                    streams,
                    learner,
                    trace,
                    h,
                )
        for family in D040_D034_FAMILIES:
            for length in D040_D034_LENGTHS:
                key = f"{family}_{length}"
                if (
                    anchors[key] is None
                    and trace
                    and capture_anchors
                    and not first_episode_complete
                    and controller.mode is d026.D026Mode.SEEK
                    and not current.charging_contact
                ):
                    selection = _find_prefix_trigger(trace, family, length)
                    if selection is not None and selection.transition == len(trace) + 1:
                        anchors[key] = _capture_anchor(
                            seed,
                            key,
                            len(trace) + 1,
                            None,
                            current,
                            environment,
                            controller,
                            streams,
                            learner,
                            trace,
                            h,
                            _trigger_history(selection),
                        )
        mode_before = controller.mode
        if _is_eligible_current(controller, current):
            first_episode_started = True
        mode_counts[mode_before.name] += 1
        proposed = controller.act(current)
        mode_after = controller.mode
        if mode_after is not mode_before:
            mode_entries[mode_after.name] += 1
        if mode_before is d026.D026Mode.CHARGE and mode_after is d026.D026Mode.DEPART:
            full_departures += 1
            if recharge_ready:
                redepartures += 1
                completed_cycles += 1
                recharge_ready = False
                cycle_stage = 1
            else:
                cycle_stage = 1
        action = proposed
        arbitration = controller.last_arbitration
        if arbitration is not None:
            predictions, read_only = _query_steering_predictions(learner, current)
            if not read_only:
                raise RuntimeError("D-040 independent prediction query mutated learner")
            action = _choose_steering_action(
                current, predictions, arbitration.greedy_action
            )
            arbitration_record = {
                "transition": len(trace) + 1,
                "greedy_action": arbitration.greedy_action.name,
                "action": action.name,
                "draw": arbitration.delegation_draw,
                "delegated": arbitration.delegated,
            }
            arbitration_digest.update(
                (
                    json.dumps(
                        arbitration_record,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    + "\n"
                ).encode()
            )
            arbitration_count += 1
        observation_array, reward, terminated, truncated, info = environment.step(
            action
        )
        reward_zero &= reward == 0.0
        info_empty &= info == {}
        telemetry = environment.last_transition
        if telemetry is None:
            raise RuntimeError("D-040 independent runner produced no telemetry")
        if telemetry.charging_contact_before and not telemetry.charging_contact_after:
            charger_exits += 1
            if cycle_stage == 1:
                cycle_stage = 2
        if (
            mode_before is d026.D026Mode.AWAY
            and mode_after is d026.D026Mode.SEEK
            and current.energy < EXP003_B50_ENTER_SEEK_THRESHOLD
        ):
            active_seek = True
            cycle_stage = 3
        next_observation = _next_visible(observation_array)
        update = learner.observe_transition(current, action, next_observation)
        _update_digest_item(update_digest, len(trace) + 1, action, update)
        predicted = update.prediction[2]
        observed = next_observation.beacon.forward - current.beacon.forward
        h = h + d027.D027_LEARNING_RATE * (observed - (predicted + h))
        row = d025._make_trace(
            transition_index=len(trace) + 1,
            mode_before=mode_before,
            mode_after=mode_after,
            action=action,
            current=current,
            observation=observation_array,
            telemetry=telemetry,
            reward=reward,
            info=info,
        )
        trace.append(row)
        actions[action.name] += 1
        continues_alternation = (
            alternation_run > 0
            and len(trace) > 1
            and _is_false_contact_seek(trace[-2])
            and trace[-2].action in _TURN_ACTIONS
            and action in _TURN_ACTIONS
            and trace[-2].action is not action
        )
        if _is_false_contact_seek(row):
            if continues_alternation:
                alternation_run += 1
            else:
                alternation_run = 1 if action in _TURN_ACTIONS else 0
                oscillation_run_start = (
                    pre_action_oscillation_candidate
                    if action in _TURN_ACTIONS
                    else None
                )
        else:
            alternation_run = 0
            oscillation_run_start = None
        ordinal += int(_is_false_contact_seek(row))
        current = next_observation
        if (
            anchors["OSCILLATION_ONSET"] is None
            and alternation_run >= 16
            and oscillation_run_start is not None
        ):
            completed = tuple(trace[-alternation_run:])
            anchors["OSCILLATION_ONSET"] = replace(
                oscillation_run_start,
                anchor_id="OSCILLATION_ONSET",
                trigger={
                    "run_start_transition": oscillation_run_start.transition,
                    "completion_transition": row.transition_index,
                    "run_length": alternation_run,
                    "completed_actions": [item.action.name for item in completed],
                    "eligible_mode_and_contact_semantics": (
                        "mode_before=SEEK, mode_after=SEEK, "
                        "pre_contact=false, post_contact=false"
                    ),
                    "uses_only_completed_actions_and_visible_observations": True,
                    "hidden_geometry_or_future_outcome_used": False,
                },
            )
        if (
            telemetry.charging_contact_before is False
            and telemetry.charging_contact_after
        ):
            if active_seek:
                reacquisitions += 1
                if first_episode_started:
                    first_episode_complete = True
                recharge_active = True
                if cycle_stage == 3:
                    cycle_stage = 4
                active_seek = False
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
    outcome = (
        "FULL_CYCLE"
        if reacquisitions and full_recharges and redepartures
        else "SEEK_REACQUIRED"
        if reacquisitions
        else "HORIZON_CENSORED"
        if truncated
        else "FAILED_SEEK"
    )
    result: dict[str, object] = {
        "arm": "LEARNED_NO_DETRAP",
        "seed": seed,
        "outcome_classification": outcome,
        "transitions": len(trace),
        "terminated": terminated,
        "truncated": truncated,
        "termination_reason": d027._termination_reason(
            environment, terminated, truncated
        ),
        "final_mode": controller.mode.name,
        "action_counts": actions,
        "mode_occupancy": mode_counts,
        "mode_entry_counts": mode_entries,
        "physical_charger_exits": charger_exits,
        "physical_reacquisitions": reacquisitions,
        "full_departures": full_departures,
        "full_recharge_events": full_recharges,
        "post_recharge_redepartures": redepartures,
        "completed_energy_regulation_cycles": completed_cycles,
        "seek_arbitration": {
            "false_contact_seek_decisions": arbitration_count,
            "stochastic_delegation_decisions": 0,
            "delegation_probability": 0.0,
            "explorer_internal_hazard": 1.0 / 8.0,
            "one_policy_rng_draw_per_decision": True,
            "legacy_arbitration_draw_count": arbitration_count,
            "false_contact_seek_explorer_calls": (
                controller.false_contact_seek_explorer_calls
            ),
            "decision_record_count": arbitration_count,
            "decision_records_digest": arbitration_digest.hexdigest(),
        },
        "trajectory_digest": d027._trace_digest(trace),
        "executed_update_digest": update_digest.hexdigest(),
        "final_weight_digest": _digest(learner.weights),
        "final_policy_rng_digest": _digest(streams.policy.bit_generator.state),
        "final_environment_rng_digest": _digest(
            streams.environment.bit_generator.state
        ),
        "reward_zero_every_transition": reward_zero,
        "organism_info_empty_every_transition": info_empty,
        "isolation": {
            "zero_false_contact_seek_delegation": True,
            "one_legacy_arbitration_draw_per_false_contact_seek_decision": True,
            "no_false_contact_seek_explorer_call": (
                controller.false_contact_seek_explorer_calls == 0
            ),
            "evaluator_diagnostics_enabled": True,
            "branch_outcomes_causal": False,
        },
        "_weights": tuple(learner.weights),
    }
    return result, tuple(trace), anchors


def compare_identity_fields(
    left: dict[str, object], right: dict[str, object]
) -> dict[str, object]:
    def projection(result: dict[str, object]) -> dict[str, object]:
        arbitration = cast(dict[str, object], result.get("seek_arbitration", {}))
        return {
            "trajectory_digest": result.get("trajectory_digest"),
            "executed_update_digest": result.get("executed_update_digest"),
            "outcome_classification": result.get("outcome_classification"),
            "transitions": result.get("transitions"),
            "terminated": result.get("terminated"),
            "truncated": result.get("truncated"),
            "termination_reason": result.get("termination_reason"),
            "final_mode": result.get("final_mode"),
            "action_counts": result.get("action_counts"),
            "mode_occupancy": result.get("mode_occupancy"),
            "mode_entry_counts": result.get("mode_entry_counts"),
            "seek_arbitration": {
                key: arbitration.get(key)
                for key in (
                    "false_contact_seek_decisions",
                    "stochastic_delegation_decisions",
                    "delegation_probability",
                    "legacy_arbitration_draw_count",
                    "false_contact_seek_explorer_calls",
                    "one_policy_rng_draw_per_decision",
                )
            },
            "final_policy_rng_digest": result.get("final_policy_rng_digest"),
            "final_environment_rng_digest": result.get("final_environment_rng_digest"),
            "final_weight_digest": result.get("final_weight_digest"),
            "reward_zero_every_transition": result.get(
                "reward_zero_every_transition", True
            ),
            "organism_info_empty_every_transition": result.get(
                "organism_info_empty_every_transition", True
            ),
        }

    left_projection = projection(left)
    right_projection = projection(right)
    mismatches = {
        field: (left_projection[field], right_projection[field])
        for field in left_projection
        if left_projection[field] != right_projection[field]
    }
    return {
        "all_identity_fields_exact": not mismatches,
        "mismatches": mismatches,
        "fields": list(left_projection),
    }


def _load_accepted_json(filename: str, expected_sha256: str) -> dict[str, object]:
    """Load a repository fixture only after verifying its frozen digest."""
    path = Path(__file__).resolve().parents[2] / "development" / filename
    encoded = path.read_bytes()
    if hashlib.sha256(encoded).hexdigest() != expected_sha256:
        raise RuntimeError(f"D-040 accepted fixture digest changed: {filename}")
    return cast(dict[str, object], json.loads(encoded.decode("utf-8")))


def _accepted_d034_anchor_identity() -> dict[int, dict[str, dict[str, object]]]:
    artifact = _load_accepted_json(
        "D-034-history-triggered-detrap-recruitment-audit.json",
        D040_D034_ACCEPTED_ARTIFACT_SHA256,
    )
    expected: dict[int, dict[str, dict[str, object]]] = {}
    for seed_result in cast(list[dict[str, object]], artifact["results"]):
        seed = int(cast(int, seed_result["seed"]))
        expected[seed] = {
            anchor_id: {
                "available": bool(anchor["available"]),
                "transition": anchor.get("transition"),
            }
            for anchor_id, anchor in cast(
                dict[str, dict[str, object]], seed_result["anchors"]
            ).items()
        }
    return expected


def _d034_anchor_identity_control(
    results: Sequence[dict[str, object]],
) -> dict[str, object]:
    """Compare every reused-seed anchor status and transition to D-034."""
    expected = _accepted_d034_anchor_identity()
    observed: dict[int, dict[str, dict[str, object]]] = {}
    mismatches: dict[str, object] = {}
    for seed_result in results:
        seed = int(cast(int, seed_result["seed"]))
        anchors = cast(dict[str, object], seed_result["anchor_grid"])
        observed[seed] = {}
        for anchor_id, expected_anchor in expected[seed].items():
            anchor = anchors.get(anchor_id)
            actual = {
                "available": anchor is not None,
                "transition": (
                    None
                    if anchor is None
                    else cast(dict[str, object], anchor).get("transition")
                ),
            }
            observed[seed][anchor_id] = actual
            if actual != expected_anchor:
                mismatches[f"{seed}:{anchor_id}"] = {
                    "expected": expected_anchor,
                    "observed": actual,
                }
    return {
        "fixture": "accepted D-034 artifact",
        "fixture_sha256": D040_D034_ACCEPTED_ARTIFACT_SHA256,
        "observed": observed,
        "mismatches": mismatches,
        "all_per_seed_anchor_identities_exact": not mismatches,
    }


def _arm_identity_gate(
    independent_results: Sequence[dict[str, object]],
) -> dict[str, object]:
    """Run the canonical D-031R1 comparator over the complete support."""
    # This import is intentionally local: the validity-critical runner above
    # remains independent of the later audit stack.  D-031R1 is a comparator,
    # never the implementation of D-040's causal path.
    from . import d031r1

    accepted = _load_accepted_json(
        "D-031R1-learned-seek-scaffold-displacement-clean-rerun.json",
        D040_D031R1_ACCEPTED_ARTIFACT_SHA256,
    )
    accepted_by_seed = {
        int(cast(int, row["seed"])): cast(dict[str, object], row["arms"])[
            "LEARNED_NO_DETRAP"
        ]
        for row in cast(list[dict[str, object]], accepted["results"])
    }
    per_seed: dict[int, dict[str, object]] = {}
    for independent in independent_results:
        seed = int(cast(int, independent["seed"]))
        is_holdout = seed in D040_HOLDOUT_SEEDS
        canonical = d031r1._run_arm(
            seed,
            arm="LEARNED_NO_DETRAP",
            horizon=D040_HORIZON,
            evaluator_diagnostics=False,
            seed_validator=lambda value: _validate_seed(
                value, holdout=value in D040_HOLDOUT_SEEDS
            ),
        )
        canonical_identity = compare_identity_fields(independent, canonical)
        accepted_identity: dict[str, object] | None = None
        if not is_holdout:
            accepted_result = dict(
                cast(dict[str, object], accepted_by_seed[seed])
            )
            # The accepted artifact predates explicit organism-boundary
            # booleans; its replay has the same frozen zero/info semantics.
            accepted_result["reward_zero_every_transition"] = True
            accepted_result["organism_info_empty_every_transition"] = True
            accepted_identity = compare_identity_fields(canonical, accepted_result)
        isolation = {
            "zero_explorer_calls": cast(
                dict[str, object], independent["seek_arbitration"]
            )["false_contact_seek_explorer_calls"]
            == 0,
            "zero_delegation": cast(
                dict[str, object], independent["seek_arbitration"]
            )["stochastic_delegation_decisions"]
            == 0,
            "one_legacy_draw_per_decision": cast(
                dict[str, object], independent["seek_arbitration"]
            )["legacy_arbitration_draw_count"]
            == cast(dict[str, object], independent["seek_arbitration"])[
                "false_contact_seek_decisions"
            ],
            "reward_zero": independent["reward_zero_every_transition"] is True,
            "info_empty": independent["organism_info_empty_every_transition"] is True,
        }
        per_seed[seed] = {
            "seed_role": "fresh_holdout" if is_holdout else "reused_accepted",
            "horizon_configured": D040_HORIZON,
            "independent_vs_canonical": canonical_identity,
            "canonical_vs_accepted": accepted_identity,
            "passed": bool(canonical_identity["all_identity_fields_exact"])
            and all(isolation.values())
            and (
                accepted_identity is None
                or bool(accepted_identity["all_identity_fields_exact"])
            ),
            "required_independent_isolation": isolation,
        }
    passed = all(bool(row["passed"]) for row in per_seed.values())
    return {
        "canonical_runner": "d031r1._run_arm comparator only",
        "accepted_artifact_sha256": D040_D031R1_ACCEPTED_ARTIFACT_SHA256,
        "per_seed": per_seed,
        "all_seeds_exact": passed,
    }


def _branch_identity(
    off_a: dict[str, object], off_b: dict[str, object]
) -> dict[str, object]:
    return compare_identity_fields(off_a, off_b)


def _available_anchor_grid(
    anchors: dict[str, _Anchor | None],
) -> dict[str, dict[str, object]]:
    return {
        key: (
            {"status": "unavailable"}
            if anchor is None
            else {
                "status": "available",
                "transition": anchor.transition,
                "state_digest": anchor.state_digest,
            }
        )
        for key, anchor in anchors.items()
    }


def _paired_effect(off: dict[str, object], on: dict[str, object]) -> dict[str, object]:
    off_latency = cast(int | None, off["reacquisition_latency"])
    on_latency = cast(int | None, on["reacquisition_latency"])
    return {
        "off_reacquired": off["reacquired"],
        "on_reacquired": on["reacquired"],
        "classification": (
            "ON_ONLY"
            if on["reacquired"] and not off["reacquired"]
            else "OFF_ONLY"
            if off["reacquired"] and not on["reacquired"]
            else "BOTH"
            if off["reacquired"] and on["reacquired"]
            else "NEITHER"
        ),
        "latency_difference_on_minus_off": None
        if off_latency is None or on_latency is None
        else on_latency - off_latency,
    }


def _feature_row(anchor: _Anchor, family: str) -> tuple[float, ...] | None:
    if family not in D040_FEATURE_FAMILIES:
        raise ValueError(f"unknown D-040 feature family: {family}")
    current = anchor.current
    s0 = (
        current.energy,
        current.beacon.left,
        current.beacon.forward,
        current.beacon.right,
        float(current.charging_contact),
        current.thermal,
    )
    if family == "F0_S0":
        return s0
    history_lengths = {
        "F1_S0_H4": 4,
        "F1_S0_H8": 8,
        "F1_S0_H16": 16,
    }
    if family in history_lengths:
        history_length = history_lengths[family]
        history = anchor.prefix[-history_length:]
        if len(history) < history_length:
            return None
        values: list[float] = list(s0)
        for row in history:
            values.extend(row.observation)
            values.extend(1.0 if row.action is action else 0.0 for action in Action)
        return tuple(values)
    learner = _learner_from_weights(anchor.learner_weights)
    if family == "F2_S0_D027":
        values = list(s0)
        predictions = {
            action: learner.predict(current, action) for action in _STEERING_ACTIONS
        }
        greedy = seek_beacon_action(current.beacon)
        chosen = _choose_steering_action(current, predictions, greedy)
        forward = [predictions[action].values[2] for action in _STEERING_ACTIONS]
        ordered = sorted(forward, reverse=True)
        tensor = np.asarray(learner.weights, dtype=float).reshape(
            (len(Action), len(d027.D027_OUTPUTS), d027.D027_FEATURE_DIMENSION)
        )
        selected = tensor[[list(Action).index(action) for action in _STEERING_ACTIONS]]
        values.extend(
            (
                predictions[chosen].values[2],
                max(forward),
                ordered[0] - ordered[1],
                float(np.std(forward)),
                float(
                    np.linalg.norm(
                        np.asarray(
                            [predictions[action].values for action in _STEERING_ACTIONS]
                        )
                        - np.mean(
                            [
                                predictions[action].values
                                for action in _STEERING_ACTIONS
                            ],
                            axis=0,
                        )
                    )
                ),
                float(np.linalg.norm(selected)),
            )
        )
        return tuple(values)
    if family == "F3_S0_h":
        return (*s0, anchor.h_before)
    if family == "F4_CLOSURE_TIMING":
        false_rows = [row for row in anchor.prefix if _is_false_contact_seek(row)]
        alt = _current_alternation_run(anchor.prefix)
        no_progress = 0
        for row in reversed(false_rows):
            if row.observation[2] <= row.observation_before[2]:
                no_progress += 1
            else:
                break
        return (*s0, float(len(false_rows)), float(alt), float(no_progress))
    if anchor.environment.body is None or anchor.environment.station_center is None:
        return None
    body = anchor.environment.body
    position = body.position
    station = anchor.environment.station_center
    clearance = min(
        position[0] - anchor.environment.config.world_min[0],
        anchor.environment.config.world_max[0] - position[0],
        position[1] - anchor.environment.config.world_min[1],
        anchor.environment.config.world_max[1] - position[1],
    )
    pair_errors = d024.dual_contact_pair_errors(position, body.heading, station)
    return (
        *s0,
        body.heading,
        position[0] - station[0],
        position[1] - station[1],
        clearance,
        pair_errors[0],
        pair_errors[1],
    )


def feature_families(anchor: _Anchor) -> dict[str, tuple[float, ...] | None]:
    """Return transparent pre-action features; F5 is explicitly privileged."""
    return {family: _feature_row(anchor, family) for family in D040_FEATURE_FAMILIES}


def _action_counts(trace: Sequence[d025.D025TransitionTrace]) -> dict[str, int]:
    counts = {name: 0 for name in _ACTION_NAMES}
    for row in trace:
        counts[row.action.name] += 1
    return counts


def _horizon_summary(
    anchor: _Anchor,
    result: dict[str, object],
    trace: Sequence[d025.D025TransitionTrace],
    horizon: int,
) -> dict[str, object]:
    latency = cast(int | None, result["reacquisition_latency"])
    defined = len(trace) >= horizon or (latency is not None and latency <= horizon)
    rows = tuple(trace[:horizon]) if defined else tuple(trace)
    if not defined or not rows:
        return {
            "status": "null",
            "null_reason": "branch_ended_before_horizon_without_reacquisition",
            "stop_reason": (
                "termination"
                if result["terminated"]
                else "truncation"
                if result["truncated"]
                else "unknown"
            ),
            "transitions": len(rows),
        }
    last = rows[-1]
    first_position = (
        anchor.environment.body.position if anchor.environment.body else None
    )
    final_position = last.telemetry.position_after
    net_displacement = None
    if first_position is not None:
        net_displacement = float(
            np.hypot(
                final_position[0] - first_position[0],
                final_position[1] - first_position[1],
            )
        )
    path_length = float(
        sum(
            np.hypot(
                row.telemetry.position_after[0] - row.telemetry.position_before[0],
                row.telemetry.position_after[1] - row.telemetry.position_before[1],
            )
            for row in rows
        )
    )
    heading_change = float(
        last.telemetry.heading
        - (anchor.environment.body.heading if anchor.environment.body else 0.0)
    )
    cumulative_heading = float(
        sum(
            abs(
                row.telemetry.heading
                - (
                    rows[index - 1].telemetry.heading
                    if index
                    else anchor.environment.body.heading
                    if anchor.environment.body
                    else 0.0
                )
            )
            for index, row in enumerate(rows)
        )
    )
    stopped_early = len(trace) < horizon
    return {
        "status": "reacquired"
        if latency is not None and latency <= horizon
        else "available",
        "stop_reason": "reacquisition" if latency is not None else None,
        "stopped_before_requested_horizon": stopped_early,
        "reacquired": latency is not None and latency <= horizon,
        "reacquisition_latency": latency
        if latency is not None and latency <= horizon
        else None,
        "visible_beacon_forward_progress": last.observation[2]
        - anchor.current.beacon.forward,
        "net_displacement": net_displacement,
        "path_displacement": path_length,
        "heading_change": heading_change,
        "cumulative_absolute_heading_change": cumulative_heading,
        "energy_change": last.observation[0] - anchor.current.energy,
        "thermal_change": last.observation[5] - anchor.current.thermal,
        "action_counts": _action_counts(rows),
        "longest_strict_alternation": _current_alternation_run(rows),
        "boundary_interaction_count": sum(
            int(row.telemetry.position_after == row.telemetry.position_before)
            for row in rows
        ),
        "transitions": len(rows),
    }


def _window_summary(
    rows: Sequence[d025.D025TransitionTrace],
    start: int,
    width: int,
    d027_rows: Sequence[dict[str, object]] = (),
) -> dict[str, object] | None:
    window = tuple(rows[start : start + width])
    if not window:
        return None
    visible = np.asarray([row.observation for row in window], dtype=float)
    summary: dict[str, object] = {
        "transitions": len(window),
        "action_counts": _action_counts(window),
        "longest_strict_alternation": _current_alternation_run(window),
        "cumulative_absolute_heading_change": float(
            sum(
                abs(row.telemetry.heading - window[index - 1].telemetry.heading)
                for index, row in enumerate(window)
                if index
            )
        ),
        "net_displacement": float(
            np.hypot(
                window[-1].telemetry.position_after[0]
                - window[0].telemetry.position_before[0],
                window[-1].telemetry.position_after[1]
                - window[0].telemetry.position_before[1],
            )
        ),
        "path_length": float(
            sum(
                np.hypot(
                    row.telemetry.position_after[0] - row.telemetry.position_before[0],
                    row.telemetry.position_after[1] - row.telemetry.position_before[1],
                )
                for row in window
            )
        ),
        "visible_channel_variance_mean": float(np.var(visible, axis=0).mean()),
    }
    if d027_rows:
        update_window = tuple(d027_rows[start : start + len(window)])
        if update_window:
            summary["d027_prediction_update_summary"] = {
                "transitions": len(update_window),
                "prediction_forward_mean": float(
                    np.asarray(
                        [
                            cast(float, row["prediction_forward"])
                            for row in update_window
                        ],
                        dtype=np.float64,
                    ).mean()
                ),
                "observed_delta_forward_mean": float(
                    np.asarray(
                        [
                            cast(float, row["observed_delta_forward"])
                            for row in update_window
                        ],
                        dtype=np.float64,
                    ).mean()
                ),
                "error_forward_mean": float(
                    np.asarray(
                        [cast(float, row["error_forward"]) for row in update_window],
                        dtype=np.float64,
                    ).mean()
                ),
                "normalizer_mean": float(
                    np.asarray(
                        [cast(float, row["normalizer"]) for row in update_window],
                        dtype=np.float64,
                    ).mean()
                ),
                "update_l2_norm_mean": float(
                    np.asarray(
                        [
                            cast(float, row["update_l2_norm"])
                            for row in update_window
                        ],
                        dtype=np.float64,
                    ).mean()
                ),
                "digest": _digest(update_window),
                "evaluator_only": True,
            }
    return summary


def _trajectory_distribution_pair(
    off: Sequence[d025.D025TransitionTrace],
    on: Sequence[d025.D025TransitionTrace],
    first_delegation: int | None,
    off_d027: Sequence[dict[str, object]] = (),
    on_d027: Sequence[dict[str, object]] = (),
) -> dict[str, object]:
    if first_delegation is None:
        return {"status": "no_on_delegation"}
    index = first_delegation - 1
    result: dict[str, object] = {
        "status": "available",
        "first_delegation": first_delegation,
    }
    for width in D040_TRAJECTORY_WINDOWS:
        result[f"before_{width}"] = {
            "off": _window_summary(
                off, max(0, index - width), width, off_d027
            ),
            "on": _window_summary(on, max(0, index - width), width, on_d027),
        }
        result[f"after_{width}"] = {
            "off": _window_summary(off, index, width, off_d027),
            "on": _window_summary(on, index, width, on_d027),
        }
    return result


def _anchor_pair(anchor: _Anchor) -> dict[str, object]:
    off, off_trace = _run_branch(anchor, condition="DETRAP_OFF")
    on, on_trace = _run_branch(anchor, condition="DETRAP_ON")
    effects: dict[str, object] = {}
    for horizon in D040_HORIZONS:
        off_summary = _horizon_summary(anchor, off, off_trace, horizon)
        on_summary = _horizon_summary(anchor, on, on_trace, horizon)
        off_ok = off_summary.get("status") in ("reacquired", "available")
        on_ok = on_summary.get("status") in ("reacquired", "available")
        off_reacquired = bool(off_summary.get("reacquired", False))
        on_reacquired = bool(on_summary.get("reacquired", False))
        effect: dict[str, object] = {
            "off": off_summary,
            "on": on_summary,
            "classification": (
                "ON_ONLY"
                if on_reacquired and not off_reacquired
                else "OFF_ONLY"
                if off_reacquired and not on_reacquired
                else "BOTH"
                if on_reacquired and off_reacquired
                else "NEITHER"
            )
            if off_ok and on_ok
            else None,
            "forward_progress_difference_on_minus_off": (
                cast(float, on_summary["visible_beacon_forward_progress"])
                - cast(float, off_summary["visible_beacon_forward_progress"])
            )
            if off_ok
            and on_ok
            and "visible_beacon_forward_progress" in off_summary
            and "visible_beacon_forward_progress" in on_summary
            else None,
            "reacquisition_latency_difference_on_minus_off": (
                cast(int, on_summary.get("reacquisition_latency"))
                - cast(int, off_summary.get("reacquisition_latency"))
            )
            if on_reacquired and off_reacquired
            else None,
        }
        effects[str(horizon)] = effect
    first = cast(int | None, on["first_delegation"])
    if first is not None and first <= len(on_trace):
        off_action = (
            off_trace[first - 1].action.name if first <= len(off_trace) else None
        )
        truth = cast(dict[str, object] | None, on.get("first_delegation_truth"))
        if truth is not None:
            truth["off_action_at_same_local_index"] = off_action
            truth["on_action_locally_differs_from_off"] = (
                on_trace[first - 1].action.name != off_action
            )
            truth["long_horizon_4096_classification"] = cast(
                dict[str, object], effects["4096"]
            ).get("classification")
    return {
        "branches": {
            "DETRAP_OFF": {
                key: value for key, value in off.items() if not key.startswith("_")
            },
            "DETRAP_ON": {
                key: value for key, value in on.items() if not key.startswith("_")
            },
        },
        "effects_by_horizon": effects,
        "trajectory_distribution_diagnostics": _trajectory_distribution_pair(
            off_trace,
            on_trace,
            first,
            cast(Sequence[dict[str, object]], off["_d027_summaries"]),
            cast(Sequence[dict[str, object]], on["_d027_summaries"]),
        ),
        "one_step_truth_around_first_on_delegation": on.get("first_delegation_truth"),
    }


def _anchor_record(anchor: _Anchor) -> dict[str, object]:
    pair = _anchor_pair(anchor)
    features = {
        family: None if row is None else list(row)
        for family, row in feature_families(anchor).items()
    }
    return {
        "anchor_id": anchor.anchor_id,
        "transition": anchor.transition,
        "ordinal": anchor.ordinal,
        "state_digest": anchor.state_digest,
        "trigger": anchor.trigger,
        "features": features,
        "pair": pair,
    }


def _seed_audit(seed: int, *, horizon: int = D040_HORIZON) -> dict[str, object]:
    result, trace, anchors = _independent_arm_b(seed, horizon=horizon)
    rendered = {
        key: None if anchor is None else _anchor_record(anchor)
        for key, anchor in anchors.items()
    }
    result = dict(result)
    result.pop("_weights", None)
    result["anchor_grid"] = rendered
    result["trace_digest"] = d027._trace_digest(trace)
    return result


def _d034_control(results: Sequence[dict[str, object]]) -> dict[str, object]:
    observed: dict[str, dict[str, int]] = {}
    for anchor_id in D040_D034_EXPECTED:
        available = off_reacquired = on_reacquired = 0
        for seed_result in results:
            anchor = cast(
                dict[str, object] | None,
                cast(dict[str, object], seed_result["anchor_grid"]).get(anchor_id),
            )
            if anchor is None:
                continue
            available += 1
            effects = cast(
                dict[str, object],
                cast(dict[str, object], anchor["pair"])["effects_by_horizon"],
            )["4096"]
            effects = cast(dict[str, object], effects)
            off_reacquired += int(
                bool(cast(dict[str, object], effects["off"]).get("reacquired", False))
            )
            on_reacquired += int(
                bool(cast(dict[str, object], effects["on"]).get("reacquired", False))
            )
        observed[anchor_id] = {
            "available": available,
            "off_reacquired": off_reacquired,
            "on_reacquired": on_reacquired,
        }
    return {
        "expected_historical_d034": D040_D034_EXPECTED,
        "observed": observed,
        "passed": observed == D040_D034_EXPECTED,
        "fixture": "accepted D-034 artifact; not D-040 output",
    }


def _sigmoid(value: float) -> float:
    return float(1.0 / (1.0 + np.exp(-np.clip(value, -40.0, 40.0))))


def _readout(
    seed_results: Sequence[dict[str, object]],
    *,
    training_results: Sequence[dict[str, object]] | None = None,
) -> dict[str, object]:
    training = list(seed_results if training_results is None else training_results)
    by_seed = {int(cast(int, row["seed"])): row for row in training}
    held_out_results = list(seed_results) if training_results is not None else training
    targets = (
        "binary_on_only_4096",
        "forward_difference_4096",
        "latency_difference_4096",
    )
    output: dict[str, object] = {}
    for family in D040_FEATURE_FAMILIES:
        family_output: dict[str, object] = {}
        for target_name in targets:

            def rows_for(
                rows: Sequence[dict[str, object]],
            ) -> list[tuple[int, list[float], float]]:
                selected: list[tuple[int, list[float], float]] = []
                for seed_row in rows:
                    for anchor in cast(
                        dict[str, object], seed_row["anchor_grid"]
                    ).values():
                        if anchor is None:
                            continue
                        anchor = cast(dict[str, object], anchor)
                        feature = cast(dict[str, object], anchor["features"]).get(
                            family
                        )
                        effect = cast(
                            dict[str, object],
                            cast(dict[str, object], anchor["pair"])[
                                "effects_by_horizon"
                            ],
                        )["4096"]
                        effect = cast(dict[str, object], effect)
                        value: object
                        if target_name == "binary_on_only_4096":
                            value = (
                                None
                                if effect["classification"] is None
                                else int(effect["classification"] == "ON_ONLY")
                            )
                        elif target_name == "forward_difference_4096":
                            value = effect["forward_progress_difference_on_minus_off"]
                        else:
                            value = effect[
                                "reacquisition_latency_difference_on_minus_off"
                            ]
                        if feature is not None and value is not None:
                            selected.append(
                                (
                                    int(cast(int, seed_row["seed"])),
                                    list(cast(list[float], feature)),
                                    float(cast(float, value)),
                                )
                            )
                return selected

            if training_results is None:
                folds: list[dict[str, object]] = []
                for held_seed in sorted(by_seed):
                    train = rows_for(
                        [
                            row
                            for row in training
                            if int(cast(int, row["seed"])) != held_seed
                        ]
                    )
                    test = rows_for([by_seed[held_seed]])
                    fold: dict[str, object] = {
                        "held_out_seed": held_seed,
                        "training_count": len(train),
                        "test_count": len(test),
                    }
                    if not train or not test:
                        fold["status"] = "insufficient_support"
                    elif (
                        target_name == "binary_on_only_4096"
                        and len({row[2] for row in train}) < 2
                    ):
                        fold["status"] = "untestable_one_class_training_support"
                    else:
                        beta = _fit_fixed_ridge(train, D040_READOUT_ALPHA)
                        predictions = [
                            _sigmoid(float(np.dot([1.0, *x], beta)))
                            if target_name == "binary_on_only_4096"
                            else float(np.dot([1.0, *x], beta))
                            for _, x, _ in test
                        ]
                        actual = [y for _, _, y in test]
                        fold["status"] = "fit"
                        fold["mae"] = float(
                            np.mean(np.abs(np.asarray(predictions) - actual))
                        )
                        fold["predictions"] = predictions
                        fold["actual"] = actual
                    folds.append(fold)
                family_output[target_name] = {
                    "fit_mode": "leave_one_seed_out",
                    "folds": folds,
                }
            else:
                train = rows_for(training)
                test = rows_for(held_out_results)
                record: dict[str, object] = {
                    "fit_mode": "reused_training_scored_on_holdout",
                    "training_count": len(train),
                    "test_count": len(test),
                }
                if (
                    not train
                    or not test
                    or (
                        target_name == "binary_on_only_4096"
                        and len({row[2] for row in train}) < 2
                    )
                ):
                    record["status"] = "insufficient_support"
                else:
                    beta = _fit_fixed_ridge(train, D040_READOUT_ALPHA)
                    predictions = [
                        _sigmoid(float(np.dot([1.0, *x], beta)))
                        if target_name == "binary_on_only_4096"
                        else float(np.dot([1.0, *x], beta))
                        for _, x, _ in test
                    ]
                    actual = [y for _, _, y in test]
                    record.update(
                        {
                            "status": "fit",
                            "mae": float(
                                np.mean(np.abs(np.asarray(predictions) - actual))
                            ),
                            "predictions": predictions,
                            "actual": actual,
                        }
                    )
                family_output[target_name] = record
        output[family] = family_output
    return output


def _fit_fixed_ridge(
    rows: Sequence[tuple[int, list[float], float]], alpha: float
) -> np.ndarray:
    matrix = np.asarray([[1.0, *row[1]] for row in rows], dtype=float)
    target = np.asarray([row[2] for row in rows], dtype=float)
    penalty = np.eye(matrix.shape[1], dtype=float) * alpha
    penalty[0, 0] = 0.0
    return np.linalg.solve(matrix.T @ matrix + penalty, matrix.T @ target)


def _ridge_fit_predict(
    train_x: Sequence[Sequence[float]],
    train_y: Sequence[float],
    test_x: Sequence[float],
) -> float:
    if not train_x:
        raise ValueError("cannot fit a readout with no training rows")
    matrix = np.asarray([[1.0, *row] for row in train_x], dtype=float)
    target = np.asarray(train_y, dtype=float)
    penalty = np.eye(matrix.shape[1], dtype=float) * D040_READOUT_ALPHA
    penalty[0, 0] = 0.0
    coefficients = np.linalg.solve(matrix.T @ matrix + penalty, matrix.T @ target)
    return float(np.asarray([1.0, *test_x], dtype=float) @ coefficients)


def _compact_seek_arbitration(value: dict[str, object]) -> None:
    """Replace raw per-decision records with auditable fixed-size metadata."""
    records = value.pop("decision_records", None)
    if records is not None:
        if not isinstance(records, list):
            raise TypeError("D-040 decision_records must be a list")
        value["decision_record_count"] = len(records)
        value["decision_records_digest"] = _canonical_json_digest(records)


def _compact_trigger(value: dict[str, object]) -> None:
    """Keep history identity while removing repeated raw observation rows."""
    observations = value.pop("completed_observations", None)
    if observations is not None:
        if not isinstance(observations, list):
            raise TypeError("D-040 completed_observations must be a list")
        value["completed_observation_count"] = len(observations)
        value.setdefault(
            "completed_observations_digest", _canonical_json_digest(observations)
        )


def _compact_seed_result(result: dict[str, object]) -> dict[str, object]:
    """Copy one result while retaining only fixed summaries and digests."""
    compact = copy.deepcopy(result)

    def visit(value: object) -> None:
        if not isinstance(value, dict):
            if isinstance(value, list):
                for item in value:
                    visit(item)
            return
        arbitration = value.get("seek_arbitration")
        if isinstance(arbitration, dict):
            _compact_seek_arbitration(arbitration)
        trigger = value.get("trigger")
        if isinstance(trigger, dict):
            _compact_trigger(trigger)
        for item in value.values():
            visit(item)

    visit(compact)
    return compact


def _compact_readouts(readouts: dict[str, object]) -> dict[str, object]:
    """Remove repeated prediction/actual vectors but retain metric provenance."""
    compact = copy.deepcopy(readouts)

    def visit(value: object) -> None:
        if isinstance(value, dict):
            predictions = value.pop("predictions", None)
            actual = value.pop("actual", None)
            if predictions is not None:
                value["predictions_digest"] = _canonical_json_digest(predictions)
            if actual is not None:
                value["actual_digest"] = _canonical_json_digest(actual)
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(compact)
    return compact


def _compact_support(support: dict[str, object] | None) -> dict[str, object] | None:
    """Return a deterministic support section with no raw high-volume records."""
    if support is None:
        return None
    compact = copy.deepcopy(support)
    results = compact.get("results")
    if isinstance(results, list):
        compact["results"] = [
            _compact_seed_result(cast(dict[str, object], result))
            for result in results
        ]
    readouts = compact.get("readouts")
    if isinstance(readouts, dict):
        compact["readouts"] = _compact_readouts(readouts)
    return compact


def _reused_support_reference(support: dict[str, object]) -> dict[str, object]:
    """Link a holdout artifact to reused training without embedding reused rows."""
    compact = _compact_support(support)
    if compact is None:
        raise ValueError("D-040 holdout support requires reused support training")
    return {
        "seed_role": "reused_development_support_training_only",
        "seeds": compact.get("seeds", []),
        "support_results_digest": _canonical_json_digest(compact.get("results", [])),
        "support_readouts_digest": _canonical_json_digest(
            compact.get("readouts", {})
        ),
        "embedded": False,
        "separate_artifact_required": True,
    }


def build_compact_artifact(
    reused: dict[str, object] | None,
    holdout: dict[str, object] | None,
    *,
    executed_commit_sha: str,
    invalidated: Sequence[dict[str, object]] = (),
    reused_support_reference: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build deterministic metadata without serializing raw audit records."""
    return {
        "schema_version": 2,
        "experiment": "D-040",
        "title": "Causal problem-identification and test-validity audit",
        "protocol_version": "D040-1",
        "authorized_base_sha": D040_AUTHORITATIVE_BASE_SHA,
        "clean_executable_protocol_sha": _validate_executed_commit_sha(
            executed_commit_sha
        ),
        "reused_support": _compact_support(reused),
        "fresh_holdout_support": _compact_support(holdout),
        "reused_support_reference": reused_support_reference,
        "invalidated_provenance": [*D040_INVALIDATED_PROVENANCE, *invalidated],
        "working_tree_clean_at_execution": True,
        "compact_artifact_contract": {
            "raw_transition_records": False,
            "raw_arbitration_records": False,
            "raw_trigger_observations": False,
            "raw_readout_predictions_and_actuals": False,
            "retained_replacements": (
                "per-seed counters, canonical digests, fixed summaries, "
                "per-anchor state/effect/readout records, and null reasons"
            ),
            "compaction_digest_algorithm": "SHA-256 over canonical sorted JSON",
        },
        "command_template": (
            "uv run python -m aweform.d040 --support {support} "
            "--executed-commit-sha {clean_sha} --output {artifact}"
        ),
        "seed_role": "Development; reused and fresh holdout are kept separate",
        "lifetime_horizon": D040_HORIZON,
        "branch_horizon": D040_BRANCH_HORIZON,
        "anchor_offsets": list(D040_ANCHOR_OFFSETS),
        "comparison_anchor_definitions": {
            "D034": {
                "families": list(D040_D034_FAMILIES),
                "lengths": list(D040_D034_LENGTHS),
                "eligibility": (
                    "mode_before=SEEK, mode_after=SEEK, "
                    "pre_contact=false, post_contact=false"
                ),
                "accepted_artifact_sha256": D040_D034_ACCEPTED_ARTIFACT_SHA256,
            },
            "OSCILLATION_ONSET": (
                "first action of first contiguous eligible strict L/R run "
                "reaching length 16"
            ),
        },
        "branch_horizons": list(D040_HORIZONS),
        "branch_stop_semantics": (
            "stop at first reacquisition, termination, or truncation; "
            "later horizon summaries retain explicit stop/null metadata"
        ),
        "arm_identity_gate_definition": {
            "configured_horizon": D040_HORIZON,
            "reused": "independent_vs_canonical_and_canonical_vs_accepted",
            "holdout": "independent_vs_canonical",
            "accepted_artifact_sha256": D040_D031R1_ACCEPTED_ARTIFACT_SHA256,
            "comparable_fields": list(D040_COMPARABLE_FIELDS),
        },
        "feature_families": list(D040_FEATURE_FAMILIES),
        "readout_alpha": D040_READOUT_ALPHA,
        "readout_definition": (
            "fixed ridge alpha 0.01; LOSO on reused, reused-fit holdout score"
        ),
        "source_artifacts": {
            "D031R1": (
                "ae5095135f4a9618fb81b815bd201312a7c2bc979eca88499f7b097dc8905b61"
            ),
            "D034": "e0d5cbdffc4e3fb429eddcbcf5af0ff4f6772eaca0368459acc1e90ed6680e1d",
        },
        "interpretation_categories": [
            "validation_contradiction_prior_interpretation_blocked",
            "scaffold_benefit_early_widespread",
            "scaffold_benefit_late_regime_localized",
            "organism_available_state_history_predicts_benefit",
            "privileged_geometry_dominates_partial_observability_remains_plausible",
            "trajectory_distribution_diversification_role_supported_descriptively",
            "static_recruitment_formulation_unsupported",
            "no_stable_scaffold_benefit_structure_on_tested_support",
            "ambiguous_multiple_bottlenecks_remain",
        ],
        "evaluator_only": True,
        "organism_changes": False,
        "reward": 0.0,
        "info": {},
    }


def write_d040_json(
    path: Path,
    payload: dict[str, object],
    *,
    executed_commit_sha: str,
) -> Path:
    _validate_executed_commit_sha(executed_commit_sha)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path


def run_d040_replay(seed: int, *, horizon: int = D040_HORIZON) -> dict[str, object]:
    """Run one bounded structural replay; official support requires frozen SHA."""
    result, trace, anchors = _independent_arm_b(seed, horizon=horizon)
    result = dict(result)
    result["anchor_grid"] = _available_anchor_grid(anchors)
    result["trace_digest"] = d027._trace_digest(trace)
    return result


def run_d040_audit(
    *,
    seeds: Sequence[int] = D040_REUSED_SEEDS,
    holdout_seeds: Sequence[int] | None = None,
    horizon: int = D040_HORIZON,
    executed_commit_sha: str | None = None,
    support: str = "reused",
) -> dict[str, object]:
    """Execute the frozen audit only when an exact clean protocol SHA is supplied."""
    sha = _validate_executed_commit_sha(executed_commit_sha)
    reused = _validate_reused_seeds(seeds)
    holdout = None if holdout_seeds is None else _validate_holdout_seeds(holdout_seeds)
    if horizon != D040_HORIZON:
        raise ValueError(
            f"D-040 requires the frozen {D040_HORIZON:,}-transition horizon"
        )
    if support not in ("reused", "holdout"):
        raise ValueError("D-040 support must be 'reused' or 'holdout'")
    reused_results = [_seed_audit(seed, horizon=horizon) for seed in reused]
    holdout_results = (
        None
        if support == "reused"
        else [
            _seed_audit(seed, horizon=horizon)
            for seed in (holdout or D040_HOLDOUT_SEEDS)
        ]
    )
    identity = _arm_identity_gate(
        reused_results
        if holdout_results is None
        else (*reused_results, *holdout_results)
    )
    if not identity["all_seeds_exact"]:
        raise RuntimeError("D-040 Arm-B identity gate failed")
    control = _d034_control(reused_results)
    anchor_identity = _d034_anchor_identity_control(reused_results)
    if not control["passed"] or not anchor_identity[
        "all_per_seed_anchor_identities_exact"
    ]:
        raise RuntimeError(
            "D-040 independent D-034 positive control contradicted the accepted support"
        )
    reused_support: dict[str, object] = {
        "seed_role": "reused_development_support",
        "seeds": list(reused),
        "results": reused_results,
        "readouts": _readout(reused_results),
    }
    holdout_support: dict[str, object] | None = (
        None
        if holdout_results is None
        else {
            "seed_role": "fresh_development_holdout",
            "seeds": list(holdout or D040_HOLDOUT_SEEDS),
            "results": holdout_results,
            "readouts": _readout(holdout_results, training_results=reused_results),
        }
    )
    payload = build_compact_artifact(
        reused_support if support == "reused" else None,
        holdout_support,
        executed_commit_sha=sha,
        reused_support_reference=(
            None
            if support == "reused"
            else _reused_support_reference(reused_support)
        ),
    )
    payload["support_executed"] = support
    payload["control_results_and_control_gate"] = {
        "aggregate": control,
        "per_seed_anchor_identity": anchor_identity,
        "arm_b_identity": identity,
    }
    return payload


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the D-040 causal validity audit")
    parser.add_argument("--executed-commit-sha", required=True)
    parser.add_argument("--support", choices=("reused", "holdout"), default="reused")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    payload = run_d040_audit(
        executed_commit_sha=args.executed_commit_sha, support=args.support
    )
    encoded = json.dumps(payload, indent=2, sort_keys=True)
    if args.output is None:
        print(encoded)
    else:
        write_d040_json(
            args.output, payload, executed_commit_sha=args.executed_commit_sha
        )
        print(f"D-040 result written to {args.output}")


if __name__ == "__main__":
    main()
