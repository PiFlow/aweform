"""D-033 evaluator-only short-horizon sequence sufficiency audit.

This module keeps the accepted D-031R1/D-032 organism unchanged.  It captures
complete pre-action Arm-B continuation states from evaluator instrumentation,
clones those states, and overrides only the physical action for a bounded
counterfactual branch.  Controller selection, policy-RNG timing, environment
physics, and the executed-action D-027 update remain causal in every branch.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import pickle
import statistics
from collections import Counter
from collections.abc import Callable, Sequence
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, Final, cast
from unittest.mock import patch

import numpy as np

from . import d025, d026, d027, d029, d031r1, d032
from .d020 import D020PhysicalConfig, D020TransitionTelemetry
from .env import Action
from .exp003 import EXP003_B50_ENTER_SEEK_THRESHOLD
from .exp003_seed_policy import validate_exp003_development_seeds
from .rng import RandomStreams

D033_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = tuple(range(18468, 18488))
D033_HORIZON: Final[int] = 70_000
D033_BRANCH_HORIZON: Final[int] = 4096
D033_LENGTHS: Final[tuple[int, ...]] = (2, 4, 8, 16)
D033_ANCHOR_A: Final[str] = "MATCHED_FIRST_DELEGATION"
D033_ANCHOR_B: Final[str] = "ALT8_ESTABLISHED"
D033_SEQUENCE_FAMILIES: Final[tuple[str, ...]] = (
    "REPEAT_B_PROPOSED",
    "TURN_LEFT_RUN",
    "TURN_RIGHT_RUN",
    "MOVE_FORWARD_RUN",
    "WAIT_RUN",
    "ALTERNATE_LR",
    "ALTERNATE_RL",
)
D033_A_REFERENCE_FAMILY: Final[str] = "REPEAT_A_FIRST"
D033_AUTHORITATIVE_BASE_SHA: Final[str] = "0e6fae6201ea7e36c04d4319bfbe536523c9f066"
D033_BASE_TREE_SHA: Final[str] = "cc5bf1fc86c29c5910c7bb9d840485957ee6c6f7"
D033_ACCEPTED_D031R1_ARTIFACT: Final[str] = d032.D032_ACCEPTED_D031R1_ARTIFACT
D033_STEERING_ACTIONS: Final[tuple[Action, ...]] = d031r1.D031R1_STEERING_ACTIONS
D033_BOUNDARY_CLASSES: Final[tuple[str, ...]] = d031r1.D031R1_BOUNDARY_CLASSES

_ACTION_NAMES: Final[tuple[str, ...]] = tuple(action.name for action in Action)
_TURN_ACTIONS: Final[frozenset[Action]] = frozenset(
    (Action.TURN_LEFT, Action.TURN_RIGHT)
)
_CAUSAL_IDENTITY_FIELDS: Final[tuple[str, ...]] = d032._CAUSAL_IDENTITY_FIELDS


def _validate_d033_development_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    """Require exactly the reused D-031R1/D-032 development support."""
    validated = validate_exp003_development_seeds(seeds)
    if validated != D033_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-033 requires exactly the reused development seeds "
            f"{D033_DEFAULT_DEVELOPMENT_SEEDS}; got {validated}"
        )
    return validated


def _validate_d033_seed(seed: int) -> None:
    validated = validate_exp003_development_seeds((seed,))
    if validated[0] not in D033_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-033 may execute only the reused development seeds "
            f"{D033_DEFAULT_DEVELOPMENT_SEEDS}; got {validated}"
        )


def _validate_executed_commit_sha(value: str | None) -> str | None:
    return d031r1._validate_executed_commit_sha(value)


def _digest(value: object) -> str:
    return hashlib.sha256(pickle.dumps(value, protocol=5)).hexdigest()


def _rng_digests(streams: RandomStreams) -> tuple[str, str]:
    return (
        _digest(streams.policy.bit_generator.state),
        _digest(streams.environment.bit_generator.state),
    )


def _empty_action_counts() -> dict[str, int]:
    return {name: 0 for name in _ACTION_NAMES}


def _empty_boundary_counts() -> dict[str, int]:
    return {name: 0 for name in D033_BOUNDARY_CLASSES}


def _number_summary(values: Sequence[float]) -> dict[str, object]:
    if not values:
        return {
            "sample_count": 0,
            "minimum": None,
            "maximum": None,
            "mean": None,
            "median": None,
        }
    return {
        "sample_count": len(values),
        "minimum": min(values),
        "maximum": max(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
    }


def _angle_difference(left: float, right: float) -> float:
    return abs((right - left + math.pi) % (2.0 * math.pi) - math.pi)


def _forward_boundary(telemetry: D020TransitionTelemetry, action: Action) -> str | None:
    if action is not Action.MOVE_FORWARD:
        return None
    displacement = math.dist(telemetry.position_before, telemetry.position_after)
    if displacement <= d027.D027_BOUNDARY_TOLERANCE:
        return "FULL_STALL_FORWARD"
    return d027._classify_forward_displacement(displacement)


def _strict_alternation(actions: Sequence[Action]) -> bool:
    return len(actions) >= 2 and all(
        left in _TURN_ACTIONS and right in _TURN_ACTIONS and left is not right
        for left, right in zip(actions, actions[1:], strict=False)
    )


def _has_strict_alt8(actions: Sequence[Action]) -> bool:
    return len(actions) >= 8 and _strict_alternation(actions[-8:])


def _alternation_run_lengths(actions: Sequence[Action]) -> list[int]:
    """Use the accepted D-032 maximal alternating-run definition."""
    return d032._left_right_alternation_runs(list(actions))


def _clone_controller_template(
    controller: d026.D026Controller,
) -> d026.D026Controller:
    """Copy controller/transient explorer state without sharing mutable fields."""
    cloned = copy.copy(controller)
    cloned.explorer = copy.copy(controller.explorer)
    return cloned


def _rewire_controller_rng(
    controller: d026.D026Controller, policy_rng: np.random.Generator
) -> d026.D026Controller:
    cloned = _clone_controller_template(controller)
    cloned.policy_rng = policy_rng
    cloned.explorer.policy_rng = policy_rng
    if isinstance(cloned, d031r1.D031R1NoDetrapController) and isinstance(
        cloned.explorer, d031r1._D031R1CountingExplorer
    ):
        cloned.explorer.owner = cloned
    return cloned


def _learner_from_weights(
    weights: Sequence[float],
) -> d027.D027ActionConsequencePredictor:
    if len(weights) != d027.D027_PLASTIC_STATE_DIMENSION:
        raise ValueError(
            "D-033 learner clone requires the complete 168-weight D-027 state"
        )
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


def _state_fingerprint(
    environment: d026.D026Env,
    controller: d026.D026Controller,
    streams: RandomStreams,
    learner: d027.D027ActionConsequencePredictor,
    current: d027.D027Observation,
) -> str:
    return _digest(
        (
            d029._environment_state(environment),
            d029._controller_state(controller),
            d029._rng_state(streams),
            tuple(learner.weights),
            current,
        )
    )


@dataclass(slots=True)
class _CapturedPreAction:
    transition: int
    current: d027.D027Observation
    environment: d026.D026Env
    controller: d026.D026Controller
    streams: RandomStreams
    learner_weights: tuple[float, ...]
    update_prefix_digest: str
    historical_action: Action
    mode_before: d026.D026Mode
    mode_after: d026.D026Mode
    greedy_action: Action | None
    delegated: bool | None
    delegation_draw: float | None
    proposed_action: Action | None = None


class _CaptureInstrumentation:
    def __init__(
        self,
        role: str,
        *,
        target_transition: int | None = None,
        capture_first_delegation: bool = False,
    ) -> None:
        self.role = role
        self.target_transition = target_transition
        self.capture_first_delegation = capture_first_delegation
        self.environment: d026.D026Env | None = None
        self.streams: RandomStreams | None = None
        self.learner: _CaptureLearner | None = None
        self.transition_count = 0
        self.update_count = 0
        self.update_digest = hashlib.sha256()
        self.pending_pre: _CapturedPreAction | None = None
        self.capture: _CapturedPreAction | None = None


class _CaptureLearner(d027.D027ActionConsequencePredictor):
    instrumentation: ClassVar[_CaptureInstrumentation | None] = None

    def __init__(self) -> None:
        super().__init__()
        instrumentation = type(self).instrumentation
        if instrumentation is None:
            raise RuntimeError("D-033 learner instrumentation was not initialized")
        instrumentation.learner = self

    def observe_transition(
        self,
        observation: d027.D027Observation,
        action: Action,
        next_observation: d027.D027Observation,
    ) -> d027.D027LearningUpdate:
        instrumentation = type(self).instrumentation
        if instrumentation is None:
            raise RuntimeError("D-033 learner instrumentation was not initialized")
        update = super().observe_transition(observation, action, next_observation)
        transition = instrumentation.update_count + 1
        d031r1._update_digest(instrumentation.update_digest, transition, action, update)
        instrumentation.update_count = transition
        return update


def _potential_false_contact_seek(
    controller: d026.D026Controller,
    observation: d027.D027Observation,
) -> bool:
    return not observation.charging_contact and (
        controller.mode is d026.D026Mode.SEEK
        or (
            controller.mode is d026.D026Mode.AWAY
            and observation.energy < EXP003_B50_ENTER_SEEK_THRESHOLD
        )
    )


def _capture_pre(
    instrumentation: _CaptureInstrumentation,
    controller: d026.D026Controller,
    observation: d027.D027Observation,
    transition: int,
) -> _CapturedPreAction:
    environment = instrumentation.environment
    streams = instrumentation.streams
    learner = instrumentation.learner
    if environment is None or streams is None or learner is None:
        raise RuntimeError("D-033 capture instrumentation was not initialized")
    return _CapturedPreAction(
        transition=transition,
        current=observation,
        environment=d029._clone_environment(environment),
        controller=_clone_controller_template(controller),
        streams=copy.deepcopy(streams),
        learner_weights=learner.weights,
        update_prefix_digest=instrumentation.update_digest.hexdigest(),
        historical_action=Action.WAIT,
        mode_before=controller.mode,
        mode_after=controller.mode,
        greedy_action=None,
        delegated=None,
        delegation_draw=None,
    )


def _finish_capture(
    instrumentation: _CaptureInstrumentation,
    controller: d026.D026Controller,
    action: Action,
    pre: _CapturedPreAction | None,
) -> None:
    if pre is None:
        return
    arbitration = controller.last_arbitration
    pre.historical_action = action
    pre.mode_after = controller.mode
    pre.greedy_action = arbitration.greedy_action if arbitration is not None else None
    pre.delegated = arbitration.delegated if arbitration is not None else None
    pre.delegation_draw = (
        arbitration.delegation_draw if arbitration is not None else None
    )
    if (
        instrumentation.role == "A"
        and arbitration is not None
        and arbitration.delegated
        and instrumentation.capture is None
    ):
        pre.proposed_action = action
        instrumentation.capture = pre
    elif (
        instrumentation.target_transition is not None
        and pre.transition == instrumentation.target_transition
    ):
        pre.proposed_action = action
        instrumentation.capture = pre


def _instrumented_act(
    instrumentation: _CaptureInstrumentation,
    controller: d026.D026Controller,
    observation: d027.D027Observation,
    action_call: Callable[[], Action],
) -> Action:
    transition = instrumentation.transition_count + 1
    needs_capture = instrumentation.target_transition == transition or (
        instrumentation.role == "A"
        and instrumentation.capture_first_delegation
        and instrumentation.capture is None
        and _potential_false_contact_seek(controller, observation)
    )
    instrumentation.pending_pre = (
        _capture_pre(instrumentation, controller, observation, transition)
        if needs_capture
        else None
    )
    action = action_call()
    _finish_capture(instrumentation, controller, action, instrumentation.pending_pre)
    instrumentation.pending_pre = None
    instrumentation.transition_count = transition
    return action


class _CaptureController(d026.D026Controller):
    instrumentation: ClassVar[_CaptureInstrumentation | None] = None

    def act(self, observation: d027.D027Observation) -> Action:
        instrumentation = type(self).instrumentation
        if instrumentation is None:
            raise RuntimeError("D-033 controller instrumentation was not initialized")
        return _instrumented_act(
            instrumentation,
            self,
            observation,
            lambda: super(_CaptureController, self).act(observation),
        )


class _CaptureNoDetrapController(d031r1.D031R1NoDetrapController):
    instrumentation: ClassVar[_CaptureInstrumentation | None] = None

    def act(self, observation: d027.D027Observation) -> Action:
        instrumentation = type(self).instrumentation
        if instrumentation is None:
            raise RuntimeError("D-033 controller instrumentation was not initialized")
        return _instrumented_act(
            instrumentation,
            self,
            observation,
            lambda: super(_CaptureNoDetrapController, self).act(observation),
        )


def _run_capture(
    seed: int,
    *,
    role: str,
    horizon: int,
    target_transition: int | None = None,
    capture_first_delegation: bool = False,
    seed_validator: Callable[[int], None] | None = None,
) -> tuple[
    dict[str, object],
    tuple[d025.D025TransitionTrace, ...],
    _CaptureInstrumentation,
]:
    if role not in {"A", "B"}:
        raise ValueError("D-033 capture role must be A or B")
    instrumentation = _CaptureInstrumentation(
        role,
        target_transition=target_transition,
        capture_first_delegation=capture_first_delegation,
    )
    trace: list[d025.D025TransitionTrace] = []
    original_initial_environment = d031r1._initial_environment
    original_query = d031r1._query_candidate_predictions
    _CaptureController.instrumentation = instrumentation
    _CaptureNoDetrapController.instrumentation = instrumentation
    _CaptureLearner.instrumentation = instrumentation

    def initial_environment(
        requested_horizon: int, requested_seed: int
    ) -> tuple[d026.D026Env, np.ndarray, RandomStreams]:
        result = original_initial_environment(requested_horizon, requested_seed)
        instrumentation.environment = result[0]
        instrumentation.streams = result[2]
        return result

    def query(
        learner: d027.D027ActionConsequencePredictor,
        current: d027.D027Observation,
    ) -> tuple[dict[Action, d027.D027Prediction], bool]:
        result = original_query(learner, current)
        capture = instrumentation.capture
        if (
            capture is not None
            and instrumentation.target_transition == instrumentation.transition_count
            and instrumentation.role == "B"
        ):
            capture.proposed_action = d031r1._choose_steering_action(
                current,
                result[0],
                cast(Action, capture.greedy_action),
            )
        return result

    with ExitStack() as stack:
        stack.enter_context(
            patch.object(d031r1, "_initial_environment", initial_environment)
        )
        stack.enter_context(patch.object(d031r1, "_query_candidate_predictions", query))
        stack.enter_context(patch.object(d026, "D026Controller", _CaptureController))
        stack.enter_context(
            patch.object(d031r1, "D031R1NoDetrapController", _CaptureNoDetrapController)
        )
        stack.enter_context(
            patch.object(d027, "D027ActionConsequencePredictor", _CaptureLearner)
        )
        result = d031r1._run_arm(
            seed,
            arm=("LEARNED_WITH_DETRAP" if role == "A" else "LEARNED_NO_DETRAP"),
            horizon=horizon,
            evaluator_diagnostics=True,
            trace_sink=trace,
            seed_validator=seed_validator,
        )
    if instrumentation.update_count != result["transitions"]:
        raise RuntimeError("D-033 capture update count diverged")
    if instrumentation.transition_count != result["transitions"]:
        raise RuntimeError("D-033 capture transition count diverged")
    if (
        target_transition is not None or capture_first_delegation
    ) and instrumentation.capture is None:
        raise RuntimeError("D-033 requested capture was not observed")
    if (
        instrumentation.capture is not None
        and instrumentation.capture.proposed_action is None
    ):
        raise RuntimeError("D-033 captured action proposal is missing")
    return result, tuple(trace), instrumentation


def _accepted_artifact() -> dict[str, object]:
    root = Path(__file__).resolve().parents[2]
    path = root / D033_ACCEPTED_D031R1_ARTIFACT
    if not path.is_file():
        raise RuntimeError(f"accepted D-031R1 artifact is missing: {path}")
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def _accepted_artifact_sha256() -> str:
    root = Path(__file__).resolve().parents[2]
    return hashlib.sha256(
        (root / D033_ACCEPTED_D031R1_ARTIFACT).read_bytes()
    ).hexdigest()


def _accepted_arm(
    artifact: dict[str, object], seed: int, arm: str
) -> dict[str, object]:
    for result in cast(list[dict[str, object]], artifact["results"]):
        if result["seed"] == seed:
            return cast(dict[str, object], cast(dict[str, object], result["arms"])[arm])
    raise RuntimeError(f"accepted D-031R1 artifact has no seed {seed}")


def _flatten_final_weights(arm: dict[str, object]) -> tuple[float, ...]:
    final_weights = cast(dict[str, dict[str, list[float]]], arm["final_weights"])
    return tuple(
        weight
        for action in Action
        for output in d027.D027_OUTPUTS
        for weight in final_weights[output][action.name]
    )


def _replay_gate(
    seed: int,
    accepted: dict[str, object],
    replay: dict[str, object],
) -> dict[str, object]:
    accepted_with_private_weights = dict(accepted)
    accepted_with_private_weights["_weights"] = _flatten_final_weights(accepted)
    comparison = d032._compare_identity_fields(
        replay, accepted_with_private_weights, include_private_weights=True
    )
    replay_summary = {
        "accepted_artifact_arm": "LEARNED_NO_DETRAP",
        "all_identity_fields_exact": comparison["all_identity_fields_exact"],
        "checked_identity_fields": comparison["checked_fields"],
        "mismatched_identity_fields": comparison["mismatched_fields"],
        "zero_false_contact_seek_delegation": cast(
            dict[str, object], replay["isolation"]
        )["zero_false_contact_seek_delegation"],
        "zero_false_contact_seek_explorer_calls": cast(
            dict[str, object], replay["isolation"]
        )["no_false_contact_seek_explorer_call"],
        "one_legacy_arbitration_draw_per_false_contact_seek_decision": cast(
            dict[str, object], replay["isolation"]
        )["one_legacy_arbitration_draw_per_false_contact_seek_decision"],
        "seed": seed,
    }
    if not all(
        bool(replay_summary[key])
        for key in (
            "all_identity_fields_exact",
            "zero_false_contact_seek_delegation",
            "zero_false_contact_seek_explorer_calls",
            "one_legacy_arbitration_draw_per_false_contact_seek_decision",
        )
    ):
        raise RuntimeError(f"D-033 Arm-B replay gate failed for seed {seed}")
    return replay_summary


def _anchor_from_capture(
    seed: int,
    anchor_type: str,
    capture: _CapturedPreAction,
) -> _AnchorState:
    if capture.proposed_action is None:
        raise RuntimeError("D-033 anchor capture has no B proposed action")
    return _AnchorState(
        seed=seed,
        anchor_type=anchor_type,
        transition=capture.transition,
        current=capture.current,
        environment=capture.environment,
        controller=capture.controller,
        streams=capture.streams,
        learner_weights=capture.learner_weights,
        update_prefix_digest=capture.update_prefix_digest,
        proposed_action=capture.proposed_action,
        greedy_action=capture.greedy_action,
        delegated=capture.delegated,
        delegation_draw=capture.delegation_draw,
    )


@dataclass(slots=True)
class _AnchorState:
    seed: int
    anchor_type: str
    transition: int
    current: d027.D027Observation
    environment: d026.D026Env
    controller: d026.D026Controller
    streams: RandomStreams
    learner_weights: tuple[float, ...]
    update_prefix_digest: str
    proposed_action: Action
    greedy_action: Action | None
    delegated: bool | None
    delegation_draw: float | None


def _anchor_fingerprint(anchor: _AnchorState) -> str:
    return _state_fingerprint(
        anchor.environment,
        anchor.controller,
        anchor.streams,
        _learner_from_weights(anchor.learner_weights),
        anchor.current,
    )


def _match_anchor_a(
    seed: int,
    a_trace: tuple[d025.D025TransitionTrace, ...],
    a_capture: _CapturedPreAction,
    b_trace: tuple[d025.D025TransitionTrace, ...],
    b_capture: _CapturedPreAction,
    b_result: dict[str, object],
) -> tuple[_AnchorState | None, dict[str, object]]:
    if a_capture.transition != b_capture.transition:
        checks: dict[str, bool] = {"same_transition_index": False}
    else:
        checks = {
            "completed_real_trajectory_prefix": a_trace[: a_capture.transition - 1]
            == b_trace[: b_capture.transition - 1],
            "current_six_channel_observation": a_capture.current == b_capture.current,
            "physical_environment_state": d029._environment_state(a_capture.environment)
            == d029._environment_state(b_capture.environment),
            "controller_state_before_treatment": d029._controller_state(
                a_capture.controller
            )
            == d029._controller_state(b_capture.controller),
            "learner_weights": a_capture.learner_weights == b_capture.learner_weights,
            "learner_state_digest": _digest(a_capture.learner_weights)
            == _digest(b_capture.learner_weights),
            "policy_rng_state_before_delegation_draw": d029._rng_state(
                a_capture.streams
            )[1]
            == d029._rng_state(b_capture.streams)[1],
            "environment_rng_state": d029._rng_state(a_capture.streams)[0]
            == d029._rng_state(b_capture.streams)[0],
            "executed_update_prefix_digest": a_capture.update_prefix_digest
            == b_capture.update_prefix_digest,
            "same_transition_index": True,
        }
    b_isolation = cast(dict[str, object], b_result["isolation"])
    treatment_checks = {
        "delegation_draw_exact_equal": a_capture.delegation_draw
        == b_capture.delegation_draw,
        "arm_a_delegated": a_capture.delegated is True,
        "arm_b_not_delegated": b_capture.delegated is False,
        "arm_b_false_contact_explorer_calls_zero": b_isolation[
            "no_false_contact_seek_explorer_call"
        ],
        "arm_b_one_policy_draw_per_decision": b_isolation[
            "one_legacy_arbitration_draw_per_false_contact_seek_decision"
        ],
    }
    all_checks = {**checks, **treatment_checks}
    if not all(all_checks.values()):
        return None, {
            "status": "BLOCKED_PRE_TREATMENT_MISMATCH",
            "seed": seed,
            "transition": a_capture.transition,
            "pre_treatment_match": False,
            "pre_treatment_checks": checks,
            "treatment_checks": treatment_checks,
            "all_checks": all_checks,
        }
    return _anchor_from_capture(seed, D033_ANCHOR_A, b_capture), {
        "status": "MATCHED_TREATMENT_ONSET",
        "seed": seed,
        "transition": a_capture.transition,
        "pre_treatment_match": True,
        "pre_treatment_checks": checks,
        "treatment_checks": treatment_checks,
        "arm_a_first_delegated_action": cast(Action, a_capture.proposed_action).name,
        "arm_b_proposed_action": cast(Action, b_capture.proposed_action).name,
        "historical_greedy_action": (
            b_capture.greedy_action.name
            if b_capture.greedy_action is not None
            else None
        ),
        "anchor_state_digest": _anchor_fingerprint(
            _anchor_from_capture(seed, D033_ANCHOR_A, b_capture)
        ),
    }


def _find_alt8_transition(
    trace: tuple[d025.D025TransitionTrace, ...],
) -> tuple[int, int] | None:
    for end in range(7, len(trace)):
        rows = trace[end - 7 : end + 1]
        actions = [row.action for row in rows]
        if not _strict_alternation(actions):
            continue
        if any(
            row.mode_before is not d026.D026Mode.SEEK
            or row.mode_after is not d026.D026Mode.SEEK
            or row.observation_before[4] != 0.0
            or row.telemetry.charging_contact_before
            or row.telemetry.charging_contact_after
            for row in rows
        ):
            continue
        last_transition = rows[-1].transition_index
        next_transition = last_transition + 1
        if next_transition > len(trace):
            return None
        return next_transition, last_transition
    return None


def _anchor_record(
    anchor: _AnchorState | None,
    checks: dict[str, object],
    *,
    alt8_last_transition: int | None = None,
) -> dict[str, object]:
    result = dict(checks)
    if anchor is None:
        result.setdefault("status", "anchor_unavailable")
        result["available"] = False
        if alt8_last_transition is not None:
            result["alternation_eighth_transition"] = alt8_last_transition
        return result
    result.update(
        {
            "available": True,
            "transition": anchor.transition,
            "anchor_state_digest": _anchor_fingerprint(anchor),
            "current_observation": [
                anchor.current.energy,
                anchor.current.beacon.left,
                anchor.current.beacon.forward,
                anchor.current.beacon.right,
                float(anchor.current.charging_contact),
                anchor.current.thermal,
            ],
            "anchor_energy": anchor.current.energy,
            "anchor_evaluator_position": list(
                cast(Any, anchor.environment.body).position
            ),
            "anchor_policy_rng_digest": _rng_digests(anchor.streams)[0],
            "anchor_environment_rng_digest": _rng_digests(anchor.streams)[1],
            "anchor_learner_state_digest": _digest(anchor.learner_weights),
            "anchor_update_prefix_digest": anchor.update_prefix_digest,
            "b_proposed_action": anchor.proposed_action.name,
        }
    )
    if alt8_last_transition is not None:
        result["alternation_eighth_transition"] = alt8_last_transition
    return result


def _sequence(
    family: str,
    length: int,
    *,
    b_proposed: Action,
    a_first: Action | None,
) -> tuple[Action, ...]:
    if length not in D033_LENGTHS:
        raise ValueError(f"D-033 sequence length must be one of {D033_LENGTHS}")
    if family == "REPEAT_B_PROPOSED":
        return (b_proposed,) * length
    if family == "REPEAT_A_FIRST":
        if a_first is None:
            raise ValueError("REPEAT_A_FIRST requires the matched Arm-A action")
        return (a_first,) * length
    if family == "TURN_LEFT_RUN":
        return (Action.TURN_LEFT,) * length
    if family == "TURN_RIGHT_RUN":
        return (Action.TURN_RIGHT,) * length
    if family == "MOVE_FORWARD_RUN":
        return (Action.MOVE_FORWARD,) * length
    if family == "WAIT_RUN":
        return (Action.WAIT,) * length
    if family == "ALTERNATE_LR":
        return tuple(
            Action.TURN_LEFT if index % 2 == 0 else Action.TURN_RIGHT
            for index in range(length)
        )
    if family == "ALTERNATE_RL":
        return tuple(
            Action.TURN_RIGHT if index % 2 == 0 else Action.TURN_LEFT
            for index in range(length)
        )
    raise ValueError(f"unknown D-033 sequence family: {family}")


def _propose_b_action(
    controller: d026.D026Controller,
    learner: d027.D027ActionConsequencePredictor,
    current: d027.D027Observation,
) -> tuple[Action, d025.D025Arbitration | None]:
    historical = controller.act(current)
    arbitration = controller.last_arbitration
    proposed = historical
    if arbitration is not None:
        if current.charging_contact or controller.mode is not d026.D026Mode.SEEK:
            raise RuntimeError(
                "D-033 B arbitration occurred outside false-contact SEEK"
            )
        predictions, read_only = d031r1._query_candidate_predictions(learner, current)
        if not read_only:
            raise RuntimeError("D-033 B prediction query changed learner state")
        proposed = d031r1._choose_steering_action(
            current, predictions, arbitration.greedy_action
        )
    return proposed, arbitration


@dataclass(slots=True)
class _BranchRun:
    output: dict[str, object]
    trace: tuple[d025.D025TransitionTrace, ...]


def _run_branch(
    anchor: _AnchorState,
    *,
    family: str,
    requested_length: int,
    sequence: Sequence[Action],
) -> _BranchRun:
    if requested_length not in (0, 1, *D033_LENGTHS):
        raise ValueError("D-033 requested length is not frozen")
    if requested_length != len(sequence):
        raise ValueError("D-033 sequence length and requested length disagree")
    anchor_before = _anchor_fingerprint(anchor)
    environment = d029._clone_environment(anchor.environment)
    streams = copy.deepcopy(anchor.streams)
    controller = _rewire_controller_rng(anchor.controller, streams.policy)
    learner = _learner_from_weights(anchor.learner_weights)
    current = anchor.current
    start_fingerprint = _state_fingerprint(
        environment, controller, streams, learner, current
    )
    expected_start = _state_fingerprint(
        anchor.environment,
        anchor.controller,
        anchor.streams,
        learner,
        anchor.current,
    )
    if start_fingerprint != expected_start:
        raise RuntimeError("D-033 branch clone did not preserve causal start state")

    trace: list[d025.D025TransitionTrace] = []
    forced_proposed: list[Action] = []
    forced_executed: list[Action] = []
    forced_policy_rng_before: list[str] = []
    forced_policy_rng_after: list[str] = []
    released_actions: list[Action] = []
    all_actions: list[Action] = []
    update_digest = hashlib.sha256()
    arbitration_count = 0
    update_count = 0
    terminated = False
    truncated = False
    stop_reason: str | None = None
    reacquisition_transition: int | None = None
    minimum_energy = current.energy
    minimum_distance = math.inf
    maximum_displacement = 0.0
    path_length = 0.0
    cumulative_heading_change = 0.0
    visible_forward_values = [current.beacon.forward]
    energy_values = [current.energy]
    anchor_body = environment.body
    if anchor_body is None or environment.station_center is None:
        raise RuntimeError("D-033 anchor lacks evaluator geometry")
    anchor_position = anchor_body.position
    previous_heading = anchor_body.heading
    station = environment.station_center
    initial_distance = math.dist(anchor_position, station)
    minimum_distance = initial_distance
    initial_false_contact_explorer_calls = getattr(
        controller, "false_contact_seek_explorer_calls", 0
    )

    for local_transition in range(1, D033_BRANCH_HORIZON + 1):
        global_transition = anchor.transition + local_transition - 1
        mode_before = controller.mode
        if local_transition <= len(sequence):
            forced_policy_rng_before.append(_rng_digests(streams)[0])
        proposed, arbitration = _propose_b_action(controller, learner, current)
        if local_transition <= len(sequence):
            forced_policy_rng_after.append(_rng_digests(streams)[0])
        if arbitration is not None:
            arbitration_count += 1
        forcing = local_transition <= len(sequence)
        physical_action = sequence[local_transition - 1] if forcing else proposed
        if forcing:
            forced_proposed.append(proposed)
            forced_executed.append(physical_action)
        else:
            released_actions.append(physical_action)
        all_actions.append(physical_action)

        observation_array, reward, terminated, truncated, info = environment.step(
            physical_action
        )
        if reward != 0.0 or info != {}:
            raise RuntimeError("D-033 forced branch crossed reward/info boundary")
        telemetry = environment.last_transition
        if telemetry is None:
            raise RuntimeError("D-033 forced branch produced no telemetry")
        next_observation = d031r1._next_visible(observation_array)
        update = learner.observe_transition(current, physical_action, next_observation)
        update_count += 1
        if update.action is not physical_action:
            raise RuntimeError("D-033 learner update did not use executed action")
        d031r1._update_digest(update_digest, global_transition, physical_action, update)
        trace.append(
            d025._make_trace(
                transition_index=global_transition,
                mode_before=mode_before,
                mode_after=controller.mode,
                action=physical_action,
                current=current,
                observation=observation_array,
                telemetry=telemetry,
                reward=reward,
                info=info,
            )
        )
        path_length += math.dist(telemetry.position_before, telemetry.position_after)
        cumulative_heading_change += _angle_difference(
            previous_heading, telemetry.heading
        )
        previous_heading = telemetry.heading
        distance = math.dist(telemetry.position_after, station)
        minimum_distance = min(minimum_distance, distance)
        maximum_displacement = max(
            maximum_displacement, math.dist(anchor_position, telemetry.position_after)
        )
        visible_forward_values.append(next_observation.beacon.forward)
        energy_values.append(next_observation.energy)
        minimum_energy = min(minimum_energy, next_observation.energy)
        current = next_observation

        if not telemetry.charging_contact_before and telemetry.charging_contact_after:
            reacquisition_transition = local_transition
            stop_reason = "reacquisition"
            break
        if terminated:
            stop_reason = "inherited_termination"
            break
        if truncated:
            stop_reason = "inherited_truncation"
            break
    else:
        stop_reason = "branch_horizon"

    if stop_reason is None:
        stop_reason = "incomplete"
    final_position = trace[-1].telemetry.position_after if trace else anchor_position
    final_energy = current.energy
    action_counts_total = Counter(action.name for action in all_actions)
    action_counts_released = Counter(action.name for action in released_actions)
    boundary_counts = Counter(
        boundary
        for row in trace
        if (boundary := _forward_boundary(row.telemetry, row.action)) is not None
    )
    alternation_runs = _alternation_run_lengths(released_actions)
    first_recurrence_latency: int | None = None
    for index in range(7, len(released_actions)):
        if _strict_alternation(released_actions[index - 7 : index + 1]):
            first_recurrence_latency = len(sequence) + index + 1
            break
    final_explorer_calls = getattr(controller, "false_contact_seek_explorer_calls", 0)
    branch_explorer_calls = final_explorer_calls - initial_false_contact_explorer_calls
    policy_rng_digest, environment_rng_digest = _rng_digests(streams)
    output: dict[str, object] = {
        "anchor_type": anchor.anchor_type,
        "anchor_transition": anchor.transition,
        "intervention_family": family,
        "requested_length": requested_length,
        "branch_transition_count": len(trace),
        "actual_forced_steps": len(forced_executed),
        "forced_step_proposed_actions": [action.name for action in forced_proposed],
        "forced_step_executed_actions": [action.name for action in forced_executed],
        "forced_step_policy_rng_before_digests": forced_policy_rng_before,
        "forced_step_policy_rng_after_digests": forced_policy_rng_after,
        "reacquired_within_branch_window": reacquisition_transition is not None,
        "reacquisition_transition_from_anchor": reacquisition_transition,
        "reacquisition_latency": reacquisition_transition,
        "reacquired_during_intervention": (
            reacquisition_transition is not None
            and reacquisition_transition <= len(sequence)
        ),
        "reacquired_after_release": (
            reacquisition_transition is not None
            and reacquisition_transition > len(sequence)
        ),
        "terminated": terminated,
        "truncated": truncated,
        "stop_reason": stop_reason,
        "termination_reason": (
            d031r1._termination_reason(environment, terminated, truncated)
            if terminated or truncated
            else None
        ),
        "energy": {
            "at_anchor": anchor.current.energy,
            "minimum": minimum_energy,
            "final_or_stop": final_energy,
            "at_reacquisition": (
                final_energy if reacquisition_transition is not None else None
            ),
            "change": final_energy - anchor.current.energy,
        },
        "path_length": path_length,
        "net_displacement_from_anchor": {
            "vector": [
                final_position[0] - anchor_position[0],
                final_position[1] - anchor_position[1],
            ],
            "magnitude": math.dist(anchor_position, final_position),
        },
        "initial_evaluator_distance_to_station": initial_distance,
        "final_evaluator_distance_to_station": math.dist(final_position, station),
        "minimum_evaluator_distance_to_station": minimum_distance,
        "maximum_displacement_from_anchor": maximum_displacement,
        "visible_beacon_forward_change": (
            visible_forward_values[-1] - visible_forward_values[0]
        ),
        "maximum_visible_beacon_forward": max(visible_forward_values),
        "cumulative_absolute_heading_change": cumulative_heading_change,
        "action_counts_after_release": {
            name: action_counts_released[name] for name in _ACTION_NAMES
        },
        "action_counts_total": {
            name: action_counts_total[name] for name in _ACTION_NAMES
        },
        "forward_boundary_counts_total": {
            name: boundary_counts[name] for name in D033_BOUNDARY_CLASSES
        },
        "left_right_alternation_run_count_after_release": len(alternation_runs),
        "left_right_alternation_run_lengths_after_release": alternation_runs,
        "longest_left_right_alternation_run_after_release": max(
            alternation_runs, default=0
        ),
        "strict_alternation_8_reappeared_after_release": (
            first_recurrence_latency is not None
        ),
        "first_strict_alternation_8_latency_after_release": first_recurrence_latency,
        "executed_action_update_count": update_count,
        "executed_action_update_digest": update_digest.hexdigest(),
        "final_branch_learner_state_digest": _digest(tuple(learner.weights)),
        "final_policy_rng_digest": policy_rng_digest,
        "final_environment_rng_digest": environment_rng_digest,
        "false_contact_seek_explorer_calls_in_branch": branch_explorer_calls,
        "false_contact_seek_arbitration_draw_count": arbitration_count,
        "branch_state": {
            "initial_causal_state_digest": start_fingerprint,
            "anchor_causal_state_digest": anchor_before,
            "branch_start_exact": start_fingerprint == expected_start,
            "branch_did_not_mutate_anchor": _anchor_fingerprint(anchor)
            == anchor_before,
            "reward_zero_every_transition": all(row.reward == 0.0 for row in trace),
            "organism_info_empty_every_transition": all(
                row.info == {} for row in trace
            ),
            "executed_action_only_updates": update_count == len(trace),
            "forced_pipeline_executed_once_per_forced_step": (
                len(forced_policy_rng_before) == len(forced_executed)
                and len(forced_policy_rng_after) == len(forced_executed)
            ),
            "no_false_contact_seek_explorer_call": branch_explorer_calls == 0,
            "one_policy_rng_draw_per_false_contact_seek_decision": (
                arbitration_count
                == sum(
                    int(
                        row.mode_after is d026.D026Mode.SEEK
                        and not row.observation_before[4]
                    )
                    for row in trace
                )
            ),
        },
    }
    return _BranchRun(output, tuple(trace))


def _expected_baseline_trace(
    trace: tuple[d025.D025TransitionTrace, ...],
    anchor_transition: int,
) -> tuple[d025.D025TransitionTrace, ...]:
    rows: list[d025.D025TransitionTrace] = []
    for row in trace[
        anchor_transition - 1 : anchor_transition - 1 + D033_BRANCH_HORIZON
    ]:
        rows.append(row)
        if (
            (
                not row.telemetry.charging_contact_before
                and row.telemetry.charging_contact_after
            )
            or row.telemetry.terminated
            or row.telemetry.truncated
        ):
            break
    return tuple(rows)


def _attach_baseline_fields(
    branch: _BranchRun,
    baseline: _BranchRun,
    *,
    full_b_trace: tuple[d025.D025TransitionTrace, ...],
    anchor: _AnchorState,
) -> None:
    baseline_action = baseline.trace[0].action if baseline.trace else None
    branch.output["first_physical_action_matches_baseline"] = (
        bool(branch.trace)
        and baseline_action is not None
        and branch.trace[0].action is baseline_action
    )
    branch.output["baseline_continuation_exact"] = (
        (baseline.trace == _expected_baseline_trace(full_b_trace, anchor.transition))
        if branch.output["intervention_family"] == "BASELINE_B"
        else None
    )


def _branch_identity(output: dict[str, object]) -> dict[str, object]:
    """Compare branch results without order-only annotations."""
    return {
        key: value
        for key, value in output.items()
        if key not in {"branch_order_invariant", "equivalence_regression_passed"}
    }


def _causal_branch_identity(output: dict[str, object]) -> dict[str, object]:
    """Compare a one-step equivalence by causal continuation, not labels."""
    excluded = {
        "anchor_type",
        "anchor_transition",
        "intervention_family",
        "requested_length",
        "actual_forced_steps",
        "forced_step_proposed_actions",
        "forced_step_executed_actions",
        "forced_step_policy_rng_before_digests",
        "forced_step_policy_rng_after_digests",
        "first_physical_action_matches_baseline",
        "baseline_continuation_exact",
        "action_counts_after_release",
        "left_right_alternation_run_count_after_release",
        "left_right_alternation_run_lengths_after_release",
        "longest_left_right_alternation_run_after_release",
        "strict_alternation_8_reappeared_after_release",
        "first_strict_alternation_8_latency_after_release",
        "branch_order_invariant",
        "equivalence_regression_passed",
    }
    comparable = {key: value for key, value in output.items() if key not in excluded}
    branch_state = dict(cast(dict[str, object], comparable.get("branch_state", {})))
    branch_state.pop("forced_pipeline_executed_once_per_forced_step", None)
    comparable["branch_state"] = branch_state
    return comparable


def _equivalence_regression(
    anchor: _AnchorState,
    baseline: _BranchRun,
) -> dict[str, object]:
    one_step = _run_branch(
        anchor,
        family="REPEAT_B_PROPOSED_EQUIVALENCE",
        requested_length=1,
        sequence=(anchor.proposed_action,),
    )
    return {
        "family": "REPEAT_B_PROPOSED_EQUIVALENCE",
        "requested_length": 1,
        "all_causal_trace_fields_exact": one_step.trace == baseline.trace,
        "branch_output_exact": _causal_branch_identity(one_step.output)
        == _causal_branch_identity(baseline.output),
        "passed": one_step.trace == baseline.trace
        and _causal_branch_identity(one_step.output)
        == _causal_branch_identity(baseline.output),
    }


def _replay_and_anchor_for_seed(
    seed: int,
    accepted: dict[str, object],
) -> tuple[
    dict[str, object],
    tuple[d025.D025TransitionTrace, ...],
    _AnchorState | None,
    dict[str, object],
    _AnchorState | None,
    dict[str, object],
]:
    replay = d031r1._run_arm(
        seed,
        arm="LEARNED_NO_DETRAP",
        horizon=D033_HORIZON,
        evaluator_diagnostics=True,
        seed_validator=_validate_d033_seed,
    )
    replay_gate = _replay_gate(
        seed, _accepted_arm(accepted, seed, "LEARNED_NO_DETRAP"), replay
    )
    b_result, b_trace, _ = _run_capture(
        seed,
        role="B",
        horizon=D033_HORIZON,
        seed_validator=_validate_d033_seed,
    )
    instrumented_comparison = d032._compare_identity_fields(
        b_result, replay, include_private_weights=True
    )
    if not instrumented_comparison["all_identity_fields_exact"]:
        raise RuntimeError(f"D-033 instrumented B replay diverged for seed {seed}")
    a_result, a_trace, a_instrumentation = _run_capture(
        seed,
        role="A",
        horizon=D033_HORIZON,
        capture_first_delegation=True,
        seed_validator=_validate_d033_seed,
    )
    del a_result
    a_capture = a_instrumentation.capture
    if a_capture is None:
        raise RuntimeError(f"D-033 Arm-A first delegation missing for seed {seed}")
    a_transition = a_capture.transition
    b_a_result, b_a_trace, b_a_instrumentation = _run_capture(
        seed,
        role="B",
        horizon=D033_HORIZON,
        target_transition=a_transition,
        seed_validator=_validate_d033_seed,
    )
    b_a_capture = b_a_instrumentation.capture
    if b_a_capture is None:
        raise RuntimeError(f"D-033 matched B anchor missing for seed {seed}")
    if b_a_trace != b_trace:
        raise RuntimeError(
            f"D-033 matched-anchor B replay instrumentation changed seed {seed}"
        )
    anchor_a, anchor_a_checks = _match_anchor_a(
        seed, a_trace, a_capture, b_a_trace, b_a_capture, b_a_result
    )

    alt8 = _find_alt8_transition(b_trace)
    if alt8 is None:
        anchor_b = None
        anchor_b_checks: dict[str, object] = {
            "status": "anchor_unavailable",
            "seed": seed,
            "blocker": (
                "no completed eight-action strict L/R alternation before lifetime end"
            ),
        }
    else:
        b_transition, last_transition = alt8
        b_b_result, b_b_trace, b_b_instrumentation = _run_capture(
            seed,
            role="B",
            horizon=D033_HORIZON,
            target_transition=b_transition,
            seed_validator=_validate_d033_seed,
        )
        if b_b_trace != b_trace:
            raise RuntimeError(f"D-033 ALT8 capture changed B replay for seed {seed}")
        b_b_capture = b_b_instrumentation.capture
        if b_b_capture is None:
            raise RuntimeError(f"D-033 ALT8 pre-action capture missing for seed {seed}")
        anchor_b_checks = {
            "status": "ALT8_ESTABLISHED",
            "seed": seed,
            "alternation_eighth_transition": last_transition,
            "strict_alternation_length": 8,
            "all_actions_false_contact_seek": True,
            "no_contact_within_eight_actions": True,
            "anchor_transition": b_transition,
            "target_capture_replay_exact": d032._compare_identity_fields(
                b_b_result, replay, include_private_weights=True
            )["all_identity_fields_exact"],
        }
        anchor_b = _anchor_from_capture(seed, D033_ANCHOR_B, b_b_capture)
        anchor_b_checks.update(
            {
                "anchor_state_digest": _anchor_fingerprint(anchor_b),
                "b_proposed_action": anchor_b.proposed_action.name,
            }
        )
    return (
        {
            "seed": seed,
            "accepted_replay": replay_gate,
            "instrumented_replay_exact": instrumented_comparison,
        },
        b_trace,
        anchor_a,
        anchor_a_checks,
        anchor_b,
        anchor_b_checks,
    )


def _branch_set_for_anchor(
    anchor: _AnchorState,
    *,
    full_b_trace: tuple[d025.D025TransitionTrace, ...],
    a_first: Action | None,
) -> tuple[dict[str, object], dict[str, _BranchRun]]:
    baseline = _run_branch(
        anchor,
        family="BASELINE_B",
        requested_length=0,
        sequence=(),
    )
    expected = _expected_baseline_trace(full_b_trace, anchor.transition)
    baseline.output["baseline_continuation_exact"] = baseline.trace == expected
    _attach_baseline_fields(
        baseline, baseline, full_b_trace=full_b_trace, anchor=anchor
    )
    if not baseline.output["baseline_continuation_exact"]:
        raise RuntimeError(
            "D-033 BASELINE_B continuation diverged at "
            f"{anchor.seed}/{anchor.anchor_type}"
        )
    runs: dict[str, _BranchRun] = {"BASELINE_B": baseline}
    ordered_specs: list[tuple[str, int]] = [
        (family, length) for family in D033_SEQUENCE_FAMILIES for length in D033_LENGTHS
    ]
    if anchor.anchor_type == D033_ANCHOR_A:
        ordered_specs.extend(
            (D033_A_REFERENCE_FAMILY, length) for length in D033_LENGTHS
        )
    for family, length in ordered_specs:
        run = _run_branch(
            anchor,
            family=family,
            requested_length=length,
            sequence=_sequence(
                family,
                length,
                b_proposed=anchor.proposed_action,
                a_first=a_first,
            ),
        )
        _attach_baseline_fields(run, baseline, full_b_trace=full_b_trace, anchor=anchor)
        runs[f"{family}:{length}"] = run

    equivalence = _equivalence_regression(anchor, baseline)
    if not equivalence["passed"]:
        raise RuntimeError(
            f"D-033 one-step equivalence failed at {anchor.seed}/{anchor.anchor_type}"
        )
    baseline_fingerprint = _anchor_fingerprint(anchor)
    reverse_runs: dict[str, _BranchRun] = {}
    reverse_specs = list(reversed(ordered_specs))
    for family, length in reverse_specs:
        reverse_run = _run_branch(
            anchor,
            family=family,
            requested_length=length,
            sequence=_sequence(
                family,
                length,
                b_proposed=anchor.proposed_action,
                a_first=a_first,
            ),
        )
        _attach_baseline_fields(
            reverse_run, baseline, full_b_trace=full_b_trace, anchor=anchor
        )
        reverse_runs[f"{family}:{length}"] = reverse_run
    baseline_again = _run_branch(
        anchor,
        family="BASELINE_B",
        requested_length=0,
        sequence=(),
    )
    _attach_baseline_fields(
        baseline_again,
        baseline_again,
        full_b_trace=full_b_trace,
        anchor=anchor,
    )
    baseline_creation_order_invariant = (
        baseline_again.trace == baseline.trace
        and _branch_identity(baseline_again.output) == _branch_identity(baseline.output)
    )
    order_invariant = (
        all(
            _branch_identity(runs[key].output)
            == _branch_identity(reverse_runs[key].output)
            for key in reverse_runs
        )
        and _anchor_fingerprint(anchor) == baseline_fingerprint
    )
    order_invariant = order_invariant and baseline_creation_order_invariant
    for run in runs.values():
        run.output["branch_order_invariant"] = order_invariant
        run.output["baseline_creation_order_invariant"] = (
            baseline_creation_order_invariant
        )
        run.output["equivalence_regression_passed"] = equivalence["passed"]
    summary = {
        "anchor_type": anchor.anchor_type,
        "seed": anchor.seed,
        "available": True,
        "baseline": baseline.output,
        "equivalence_regression": equivalence,
        "branch_order_invariance": order_invariant,
        "baseline_creation_order_invariance": baseline_creation_order_invariant,
        "branches": [
            runs[f"{family}:{length}"].output for family, length in ordered_specs
        ],
    }
    return summary, runs


def _seed_anchor_record(
    seed_record: dict[str, object], anchor_type: str
) -> dict[str, object]:
    return cast(
        dict[str, object], cast(dict[str, object], seed_record["anchors"])[anchor_type]
    )


def _pooled_summary(
    seed_records: Sequence[dict[str, object]],
    anchor_type: str,
) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    for seed_record in seed_records:
        anchor = _seed_anchor_record(seed_record, anchor_type)
        if not anchor.get("available"):
            continue
        rows.append(anchor)
    available = len(rows)
    keys: list[tuple[str, int]] = [("BASELINE_B", 0)] + [
        (family, length) for family in D033_SEQUENCE_FAMILIES for length in D033_LENGTHS
    ]
    if anchor_type == D033_ANCHOR_A:
        keys.extend((D033_A_REFERENCE_FAMILY, length) for length in D033_LENGTHS)
    summaries: dict[str, object] = {}
    for family, length in keys:
        branches: list[dict[str, object]] = []
        for row in rows:
            branch = (
                cast(dict[str, object], row["baseline"])
                if family == "BASELINE_B"
                else next(
                    item
                    for item in cast(list[dict[str, object]], row["branches"])
                    if item["intervention_family"] == family
                    and item["requested_length"] == length
                )
            )
            branches.append(branch)
        latencies = [
            cast(float, branch["reacquisition_latency"])
            for branch in branches
            if branch["reacquisition_latency"] is not None
        ]
        reacq_energy = [
            cast(
                float,
                cast(dict[str, object], branch["energy"])["at_reacquisition"],
            )
            for branch in branches
            if cast(dict[str, object], branch["energy"])["at_reacquisition"] is not None
        ]
        pooled = {
            "intervention_family": family,
            "requested_length": length,
            "available_seed_count": available,
            "reacquisition_count": sum(
                int(cast(bool, branch["reacquired_within_branch_window"]))
                for branch in branches
            ),
            "reacquisition_latency": _number_summary(latencies),
            "energy_at_reacquisition": _number_summary(reacq_energy),
            "reacquired_during_intervention_count": sum(
                int(cast(bool, branch["reacquired_during_intervention"]))
                for branch in branches
            ),
            "reacquired_after_release_count": sum(
                int(cast(bool, branch["reacquired_after_release"]))
                for branch in branches
            ),
            "path_length": _number_summary(
                [float(cast(float, branch["path_length"])) for branch in branches]
            ),
            "net_displacement_magnitude": _number_summary(
                [
                    cast(
                        float,
                        cast(dict[str, object], branch["net_displacement_from_anchor"])[
                            "magnitude"
                        ],
                    )
                    for branch in branches
                ]
            ),
            "minimum_evaluator_distance": _number_summary(
                [
                    cast(float, branch["minimum_evaluator_distance_to_station"])
                    for branch in branches
                ]
            ),
            "energy_change": _number_summary(
                [
                    cast(float, cast(dict[str, object], branch["energy"])["change"])
                    for branch in branches
                ]
            ),
            "alternation_recurrence_count": sum(
                int(cast(bool, branch["strict_alternation_8_reappeared_after_release"]))
                for branch in branches
            ),
            "alternation_recurrence_latency": _number_summary(
                [
                    cast(
                        float,
                        branch["first_strict_alternation_8_latency_after_release"],
                    )
                    for branch in branches
                    if branch["first_strict_alternation_8_latency_after_release"]
                    is not None
                ]
            ),
            "seed_lists": {
                "baseline_fail_intervention_reacquire": [],
                "baseline_and_intervention_both_fail": [],
            },
            "outlier_handling": {
                "discarded_seed_count": 0,
                "statement": (
                    "All available per-seed outcomes are retained; no outliers "
                    "are discarded."
                ),
            },
        }
        if family != "BASELINE_B":
            available_records = [
                seed_record
                for seed_record in seed_records
                if _seed_anchor_record(seed_record, anchor_type).get("available")
            ]
            baseline_by_seed = {
                cast(int, seed_record["seed"]): cast(
                    dict[str, object],
                    _seed_anchor_record(seed_record, anchor_type)["baseline"],
                )
                for seed_record in available_records
            }
            intervention_by_seed = {
                cast(int, seed_record["seed"]): branch
                for seed_record, branch in zip(
                    available_records,
                    branches,
                    strict=True,
                )
            }
            baseline_fail_intervention = [
                seed
                for seed, baseline_branch in baseline_by_seed.items()
                if not baseline_branch["reacquired_within_branch_window"]
                and intervention_by_seed[seed]["reacquired_within_branch_window"]
            ]
            both_fail = [
                seed
                for seed, baseline_branch in baseline_by_seed.items()
                if not baseline_branch["reacquired_within_branch_window"]
                and not intervention_by_seed[seed]["reacquired_within_branch_window"]
            ]
            pooled["seed_lists"] = {
                "baseline_fail_intervention_reacquire": baseline_fail_intervention,
                "baseline_and_intervention_both_fail": both_fail,
            }
            matched = []
            for seed, baseline_branch in baseline_by_seed.items():
                intervention = intervention_by_seed[seed]
                baseline_latency = cast(
                    float | None, baseline_branch["reacquisition_latency"]
                )
                intervention_latency = cast(
                    float | None, intervention["reacquisition_latency"]
                )
                latency_difference = (
                    intervention_latency - baseline_latency
                    if baseline_latency is not None and intervention_latency is not None
                    else None
                )
                matched.append(
                    {
                        "seed": seed,
                        "baseline_reacquired": baseline_branch[
                            "reacquired_within_branch_window"
                        ],
                        "intervention_reacquired": intervention[
                            "reacquired_within_branch_window"
                        ],
                        "reacquisition_sign": (
                            "intervention_only"
                            if not baseline_branch["reacquired_within_branch_window"]
                            and intervention["reacquired_within_branch_window"]
                            else "baseline_only"
                            if baseline_branch["reacquired_within_branch_window"]
                            and not intervention["reacquired_within_branch_window"]
                            else "both"
                            if baseline_branch["reacquired_within_branch_window"]
                            and intervention["reacquired_within_branch_window"]
                            else "neither"
                        ),
                        "latency_difference_intervention_minus_baseline": (
                            latency_difference
                        ),
                        "latency_sign": (
                            "lower"
                            if latency_difference is not None and latency_difference < 0
                            else "equal"
                            if latency_difference == 0
                            else "higher"
                            if latency_difference is not None
                            else None
                        ),
                    }
                )
            pooled["matched_repeat_b_proposed_minus_baseline"] = matched
        summaries[f"{family}:{length}"] = pooled
    return {
        "anchor_type": anchor_type,
        "available_seed_count": available,
        "families": summaries,
    }


def _interpretation(
    seed_records: Sequence[dict[str, object]],
) -> dict[str, object]:
    def count(anchor_type: str, family: str) -> int:
        total = 0
        for seed_record in seed_records:
            anchor = _seed_anchor_record(seed_record, anchor_type)
            if not anchor.get("available"):
                continue
            branches = cast(list[dict[str, object]], anchor["branches"])
            total += sum(
                int(
                    cast(str, branch["intervention_family"]) == family
                    and cast(bool, branch["reacquired_within_branch_window"])
                )
                for branch in branches
            )
        return total

    return {
        "lane": "Development",
        "confirmatory_claim": False,
        "observed": {
            "reacquisition_counts_by_anchor_and_family": {
                anchor: {
                    family: count(anchor, family)
                    for family in (*D033_SEQUENCE_FAMILIES, D033_A_REFERENCE_FAMILY)
                    if not (
                        anchor == D033_ANCHOR_B and family == D033_A_REFERENCE_FAMILY
                    )
                }
                for anchor in (D033_ANCHOR_A, D033_ANCHOR_B)
            }
        },
        "decision_patterns": [
            (
                "REPEAT_B_PROPOSED materially above BASELINE_B with alternating "
                "controls poor supports a bounded persistence component at those "
                "states."
            ),
            (
                "Fixed repeated turns or forward runs succeeding while "
                "REPEAT_B_PROPOSED does not supports action-direction specificity "
                "more than generic persistence."
            ),
            (
                "REPEAT_A_FIRST is a hindsight scaffold-action reference only, "
                "never an organism policy."
            ),
            (
                "Relapse after release supports a continuing "
                "sequence-generation/stateful scaffold role rather than a "
                "one-off perturbation."
            ),
            (
                "Similar mostly failing simple families do not demonstrate "
                "short simple sequence sufficiency."
            ),
            (
                "Same-first-action family differences may motivate a future "
                "evaluator-only multi-step audit but do not authorize one."
            ),
        ],
        "supported_inference": (
            "Descriptive only; no universal threshold or weighted sequence "
            "score is used."
        ),
        "unresolved_hypotheses": [
            (
                "the separate causal contributions of persistence, symmetry "
                "breaking, non-myopic benefit, and learned action selection"
            ),
            (
                "whether richer sequence structure is needed when simple "
                "commitments relapse"
            ),
        ],
        "no_behavior_change_authorized": True,
        "no_successor_authorized": True,
    }


def run_d033_audit(
    seeds: Sequence[int] = D033_DEFAULT_DEVELOPMENT_SEEDS,
    *,
    horizon: int = D033_HORIZON,
    executed_commit_sha: str | None = None,
) -> dict[str, object]:
    """Run the complete frozen D-033 protocol on the reused support."""
    validated = _validate_d033_development_seeds(seeds)
    if horizon != D033_HORIZON:
        raise ValueError("D-033 requires the frozen 70,000-transition horizon")
    executed_sha = _validate_executed_commit_sha(executed_commit_sha)
    accepted = _accepted_artifact()
    seed_records: list[dict[str, object]] = []
    for seed in validated:
        replay, b_trace, anchor_a, anchor_a_checks, anchor_b, anchor_b_checks = (
            _replay_and_anchor_for_seed(seed, accepted)
        )
        a_record = _anchor_record(anchor_a, anchor_a_checks)
        b_record = _anchor_record(
            anchor_b,
            anchor_b_checks,
            alt8_last_transition=cast(
                int | None, anchor_b_checks.get("alternation_eighth_transition")
            ),
        )
        if anchor_a is not None:
            a_summary, _ = _branch_set_for_anchor(
                anchor_a,
                full_b_trace=b_trace,
                a_first=Action[
                    cast(str, anchor_a_checks["arm_a_first_delegated_action"])
                ],
            )
            a_record.update(a_summary)
        if anchor_b is not None:
            b_summary, _ = _branch_set_for_anchor(
                anchor_b,
                full_b_trace=b_trace,
                a_first=None,
            )
            b_record.update(b_summary)
        seed_records.append(
            {
                "seed": seed,
                "replay": replay,
                "anchors": {
                    D033_ANCHOR_A: a_record,
                    D033_ANCHOR_B: b_record,
                },
            }
        )
    return {
        "schema_version": 1,
        "experiment": "D-033",
        "title": "Short-horizon sequence sufficiency audit",
        "authoritative_base_sha": D033_AUTHORITATIVE_BASE_SHA,
        "base_tree_sha": D033_BASE_TREE_SHA,
        "implementation_probe_sha": executed_sha,
        "protocol_only_freeze_sha": executed_sha,
        "development_seeds": list(validated),
        "horizon": D033_HORIZON,
        "branch_horizon": D033_BRANCH_HORIZON,
        "timestep_seconds": D020PhysicalConfig().dt_seconds,
        "simulated_duration_seconds": D033_HORIZON * D020PhysicalConfig().dt_seconds,
        "support": {
            "source": "accepted D-031R1/D-032 Development support",
            "accepted_artifact": D033_ACCEPTED_D031R1_ARTIFACT,
            "accepted_artifact_sha256": _accepted_artifact_sha256(),
            "fresh_seed_block_allocated": False,
            "fresh_seed_block_inspected": False,
        },
        "freeze": {
            "underlying_arm": "LEARNED_NO_DETRAP",
            "anchors": [D033_ANCHOR_A, D033_ANCHOR_B],
            "lengths": list(D033_LENGTHS),
            "sequence_families": list(D033_SEQUENCE_FAMILIES),
            "matched_anchor_reference_family": D033_A_REFERENCE_FAMILY,
            "branch_horizon": D033_BRANCH_HORIZON,
            "stop_rules": [
                "dual-contact reacquisition",
                "inherited energy or thermal termination",
                "inherited episode truncation",
                "4096 branch transitions",
            ],
            "physical_action_override_only": True,
            "controller_selection_pipeline_unchanged": True,
            "learner_update_once_from_executed_action_and_actual_next_observation": (
                True
            ),
            "no_organism_boundary_change": True,
        },
        "causal_order": [
            "capture exact pre-action B causal state",
            "clone environment/controller/RNG/168-weight learner",
            "unchanged B controller/action-selection pipeline",
            "evaluator-only physical-action replacement during requested prefix",
            "one unchanged real transition",
            "actual next six-channel observation",
            "one unchanged executed-action D-027 update",
            "release to unchanged B after requested prefix",
            "post-hoc evaluator metrics only",
        ],
        "organism_boundary": {
            "channels": list(d027.D027_CHANNELS),
            "actions": [action.name for action in Action],
            "reward": 0.0,
            "info": {},
            "evaluator_state_reaches_controller_or_learner": False,
            "organism_history_or_persistence_added": False,
            "new_sensor_or_physics_added": False,
            "world_model_or_planning_added": False,
        },
        "replay_gate": {
            "all_seeds_exact_arm_b_replay": True,
            "checked_identity_fields": list(_CAUSAL_IDENTITY_FIELDS) + ["_weights"],
            "zero_false_contact_seek_explorer_calls_required": True,
            "one_legacy_policy_rng_draw_per_false_contact_seek_decision_required": True,
        },
        "results": seed_records,
        "pooled": {
            D033_ANCHOR_A: _pooled_summary(seed_records, D033_ANCHOR_A),
            D033_ANCHOR_B: _pooled_summary(seed_records, D033_ANCHOR_B),
        },
        "interpretation": _interpretation(seed_records),
    }


def write_d033_json(path: Path, executed_commit_sha: str | None = None) -> Path:
    path.write_text(
        json.dumps(
            run_d033_audit(executed_commit_sha=executed_commit_sha),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the D-033 sequence audit.")
    parser.add_argument("--executed-commit-sha")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.output is None:
        print(
            json.dumps(
                run_d033_audit(executed_commit_sha=args.executed_commit_sha),
                indent=2,
                sort_keys=True,
            )
        )
    else:
        write_d033_json(args.output, args.executed_commit_sha)
        print(f"D-033 result written to {args.output}")


if __name__ == "__main__":
    main()
