"""D-032 evaluator-only attribution audit for the D-031R1 de-trap scaffold.

This module deliberately does not define a new controller or environment.  It
temporarily wraps the existing D-031R1 runner so that evaluator diagnostics can
observe action-selection onset, learner state, and hidden geometry without
changing any causal call, RNG stream, observation, update, reward, or action.
The wrapper is checked against an uninstrumented D-031R1 replay and the
committed D-031R1 artifact before any diagnostic result is accepted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pickle
import statistics
from collections import Counter
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, Final, Sequence, cast
from unittest.mock import patch

from . import d024, d025, d026, d027, d029, d031r1
from .d020 import D020PhysicalConfig, D020TransitionTelemetry
from .env import Action
from .exp003 import EXP003_B50_ENTER_SEEK_THRESHOLD

D032_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = (
    18468,
    18469,
    18470,
    18471,
    18472,
    18473,
    18474,
    18475,
    18476,
    18477,
    18478,
    18479,
    18480,
    18481,
    18482,
    18483,
    18484,
    18485,
    18486,
    18487,
)
D032_HORIZON: Final[int] = 70_000
D032_WINDOWS: Final[tuple[int, ...]] = (1, 4, 16, 64, 256, 1024, 4096)
D032_ARM_NAMES: Final[tuple[str, ...]] = d031r1.D031R1_ARM_NAMES
D032_STEERING_ACTIONS: Final[tuple[Action, ...]] = d031r1.D031R1_STEERING_ACTIONS
D032_BOUNDARY_CLASSES: Final[tuple[str, ...]] = d031r1.D031R1_BOUNDARY_CLASSES
D032_AUTHORITATIVE_BASE_SHA: Final[str] = "b25fe711549ba4e98f9759f8358316b94712ca64"
D032_BASE_TREE_SHA: Final[str] = "4940d5fcaf82ef498db6fc58d8eadc23f5724d0c"
D032_ACCEPTED_D031R1_ARTIFACT: Final[str] = (
    "development/D-031R1-learned-seek-scaffold-displacement-clean-rerun.json"
)

_ACTION_NAMES: Final[tuple[str, ...]] = tuple(action.name for action in Action)
_CAUSAL_IDENTITY_FIELDS: Final[tuple[str, ...]] = (
    "outcome_classification",
    "transitions",
    "physical_seconds",
    "terminated",
    "truncated",
    "termination_reason",
    "final_mode",
    "action_counts",
    "mode_occupancy",
    "mode_entry_counts",
    "battery_normalized",
    "temperature_normalized",
    "full_departures",
    "physical_charger_exits",
    "low_energy_seek_entries",
    "physical_reacquisitions",
    "charge_entries",
    "full_recharge_events",
    "post_recharge_redepartures",
    "completed_energy_regulation_cycles",
    "seek_episodes",
    "seek_arbitration",
    "seek_segment_starts",
    "trajectory_digest",
    "executed_update_digest",
    "final_weights",
    "final_weight_digest",
    "final_policy_rng_digest",
    "final_environment_rng_digest",
)


def _validate_d032_development_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    validated = d031r1._validate_d031r1_development_seeds(seeds)
    if validated != D032_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-032 requires exactly the reused D-031R1 seeds "
            f"{D032_DEFAULT_DEVELOPMENT_SEEDS}; got {validated}"
        )
    return validated


def _validate_d032_seed(seed: int) -> None:
    d031r1._validate_d031r1_seed(seed)
    if seed not in D032_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-032 may execute only the reused D-031R1 seeds "
            f"{D032_DEFAULT_DEVELOPMENT_SEEDS}; got {seed}"
        )


def _validate_executed_commit_sha(value: str | None) -> str | None:
    return d031r1._validate_executed_commit_sha(value)


def _digest(value: object) -> str:
    return hashlib.sha256(pickle.dumps(value, protocol=5)).hexdigest()


def _json_number_summary(values: list[float]) -> dict[str, object]:
    if not values:
        return {
            "sample_count": 0,
            "minimum": None,
            "maximum": None,
            "mean": None,
            "median": None,
        }
    ordered = sorted(values)
    return {
        "sample_count": len(values),
        "minimum": min(values),
        "maximum": max(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "p10_nearest_rank": ordered[max(1, math.ceil(0.10 * len(ordered))) - 1],
        "p25_nearest_rank": ordered[max(1, math.ceil(0.25 * len(ordered))) - 1],
        "p75_nearest_rank": ordered[max(1, math.ceil(0.75 * len(ordered))) - 1],
        "p90_nearest_rank": ordered[max(1, math.ceil(0.90 * len(ordered))) - 1],
        "p95_nearest_rank": ordered[max(1, math.ceil(0.95 * len(ordered))) - 1],
        "p99_nearest_rank": ordered[max(1, math.ceil(0.99 * len(ordered))) - 1],
    }


def _counter_dict(counter: Counter[str]) -> dict[str, int]:
    return {key: counter[key] for key in sorted(counter)}


def _environment_identity_state(
    environment: d026.D026Env,
) -> tuple[object, ...]:
    """Capture the mutable environment state as immutable evaluator values."""
    body = environment.body
    if body is None:
        raise RuntimeError("D-032 evaluator geometry disappeared")
    return (
        (body.x, body.y, body.heading, body.energy),
        environment.station_center,
        environment.body_temperature_c,
        environment.battery_j,
        environment.charger_termination_latched,
        environment._step_count,
        environment._episode_done,
        environment.last_transition,
    )


def _empty_action_counts() -> dict[str, int]:
    return {name: 0 for name in _ACTION_NAMES}


def _empty_boundary_counts() -> dict[str, int]:
    return {name: 0 for name in D032_BOUNDARY_CLASSES}


def _angle_difference(left: float, right: float) -> float:
    difference = (right - left + math.pi) % (2.0 * math.pi) - math.pi
    return abs(difference)


def _forward_boundary(telemetry: D020TransitionTelemetry, action: Action) -> str | None:
    if action is not Action.MOVE_FORWARD:
        return None
    displacement = math.dist(telemetry.position_before, telemetry.position_after)
    if displacement <= d027.D027_BOUNDARY_TOLERANCE:
        return "FULL_STALL_FORWARD"
    return d027._classify_forward_displacement(displacement)


@dataclass(slots=True)
class _CapturedDecision:
    transition: int
    current: d027.D027Observation
    action: Action
    mode_before: d026.D026Mode
    mode_after: d026.D026Mode
    greedy_action: Action | None
    delegated: bool | None
    delegation_draw: float | None
    environment_state: tuple[object, ...]
    controller_state_before: tuple[object, ...]
    policy_rng_before: bytes
    environment_rng_before: bytes
    learner_weights: tuple[float, ...]
    learner_digest: str
    update_prefix_digest: str
    environment_snapshot: d026.D026Env | None
    predictions: dict[Action, tuple[float, ...]] | None = None
    prediction_query_read_only: bool | None = None


class _Instrumentation:
    def __init__(self, arm: str, target_transition: int | None = None) -> None:
        self.arm = arm
        self.target_transition = target_transition
        self.environment: d026.D026Env | None = None
        self.streams: Any = None
        self.learner: _InstrumentedLearner | None = None
        self.events: list[_CapturedDecision] = []
        self.current_event: _CapturedDecision | None = None
        self.update_digest = hashlib.sha256()
        self.update_count = 0
        self.transition_count = 0
        self.controller_state_before: tuple[object, ...] | None = None
        self.policy_rng_before: bytes | None = None


class _InstrumentedLearner(d027.D027ActionConsequencePredictor):
    """D-027 learner with an evaluator-only update-prefix digest."""

    instrumentation: ClassVar[_Instrumentation | None] = None

    def __init__(self) -> None:
        super().__init__()
        instrumentation = type(self).instrumentation
        if instrumentation is None:
            raise RuntimeError("D-032 learner instrumentation was not initialized")
        instrumentation.learner = self

    def observe_transition(
        self,
        observation: d026.D026Observation,
        action: Action,
        next_observation: d026.D026Observation,
    ) -> d027.D027LearningUpdate:
        instrumentation = type(self).instrumentation
        if instrumentation is None:
            raise RuntimeError("D-032 learner instrumentation was not initialized")
        update = super().observe_transition(observation, action, next_observation)
        transition = instrumentation.update_count + 1
        value = {
            "transition": transition,
            "action": action.name,
            "prediction": update.prediction,
            "observed_delta": update.observed_delta,
            "errors": update.errors,
            "normalizer": update.normalizer,
        }
        instrumentation.update_digest.update(
            (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
        )
        instrumentation.update_count = transition
        return update


def _capture_controller_act(
    instrumentation: _Instrumentation,
    controller: d026.D026Controller,
    current: d027.D027Observation,
    action: Action,
) -> None:
    environment = instrumentation.environment
    streams = instrumentation.streams
    learner = instrumentation.learner
    if environment is None or streams is None or learner is None:
        raise RuntimeError("D-032 instrumentation was not initialized")
    event_controller_state_before = instrumentation.controller_state_before
    event_policy_rng_before = instrumentation.policy_rng_before
    arbitration = controller.last_arbitration
    event_delegated = arbitration.delegated if arbitration is not None else False
    should_keep = (
        instrumentation.arm == "LEARNED_WITH_DETRAP" and event_delegated
    ) or instrumentation.target_transition == instrumentation.transition_count
    if not should_keep:
        return
    first_arm_a_delegation = (
        instrumentation.arm == "LEARNED_WITH_DETRAP"
        and event_delegated
        and not any(item.delegated for item in instrumentation.events)
    )
    full_onset_capture = first_arm_a_delegation or (
        instrumentation.target_transition == instrumentation.transition_count
    )
    if full_onset_capture:
        if event_controller_state_before is None or event_policy_rng_before is None:
            raise RuntimeError("D-032 action-selection state was not captured")
    else:
        event_controller_state_before = ()
        event_policy_rng_before = b""
    if environment.body is None or environment.station_center is None:
        raise RuntimeError("D-032 evaluator geometry disappeared before action")
    environment_rng = d029._rng_state(streams)[0]
    event = _CapturedDecision(
        transition=instrumentation.transition_count,
        current=current,
        action=action,
        mode_before=(
            cast(d026.D026Mode, event_controller_state_before[0])
            if full_onset_capture
            else controller.mode
        ),
        mode_after=controller.mode,
        greedy_action=arbitration.greedy_action if arbitration is not None else None,
        delegated=arbitration.delegated if arbitration is not None else None,
        delegation_draw=arbitration.delegation_draw
        if arbitration is not None
        else None,
        environment_state=(
            _environment_identity_state(environment) if full_onset_capture else ()
        ),
        controller_state_before=(
            event_controller_state_before if full_onset_capture else ()
        ),
        policy_rng_before=event_policy_rng_before if full_onset_capture else b"",
        environment_rng_before=environment_rng if full_onset_capture else b"",
        learner_weights=learner.weights if full_onset_capture else (),
        learner_digest=_digest(learner.weights) if full_onset_capture else "",
        update_prefix_digest=(
            instrumentation.update_digest.hexdigest() if full_onset_capture else ""
        ),
        environment_snapshot=(
            d029._clone_environment(environment) if first_arm_a_delegation else None
        ),
    )
    instrumentation.events.append(event)
    instrumentation.current_event = event
    if (
        instrumentation.arm == "LEARNED_WITH_DETRAP"
        and event.delegated
        and first_arm_a_delegation
    ):
        before = learner.weights
        event.predictions = {
            candidate: learner.predict(current, candidate).values
            for candidate in D032_STEERING_ACTIONS
        }
        event.prediction_query_read_only = learner.weights == before


class _InstrumentedController(d026.D026Controller):
    instrumentation: ClassVar[_Instrumentation | None] = None

    def act(self, observation: d027.D027Observation) -> Action:
        instrumentation = type(self).instrumentation
        if instrumentation is None or instrumentation.streams is None:
            raise RuntimeError("D-032 instrumentation was not initialized")
        instrumentation.current_event = None
        transition = instrumentation.transition_count + 1
        needs_pre_capture = _needs_pre_capture(
            instrumentation, self, observation, transition
        )
        instrumentation.controller_state_before = (
            d029._controller_state(self) if needs_pre_capture else None
        )
        instrumentation.policy_rng_before = (
            d029._rng_state(instrumentation.streams)[1] if needs_pre_capture else None
        )
        action = super().act(observation)
        instrumentation.transition_count = transition
        _capture_controller_act(instrumentation, self, observation, action)
        return action


class _InstrumentedNoDetrapController(d031r1.D031R1NoDetrapController):
    instrumentation: ClassVar[_Instrumentation | None] = None

    def act(self, observation: d027.D027Observation) -> Action:
        instrumentation = type(self).instrumentation
        if instrumentation is None or instrumentation.streams is None:
            raise RuntimeError("D-032 instrumentation was not initialized")
        instrumentation.current_event = None
        transition = instrumentation.transition_count + 1
        needs_pre_capture = _needs_pre_capture(
            instrumentation, self, observation, transition
        )
        instrumentation.controller_state_before = (
            d029._controller_state(self) if needs_pre_capture else None
        )
        instrumentation.policy_rng_before = (
            d029._rng_state(instrumentation.streams)[1] if needs_pre_capture else None
        )
        action = super().act(observation)
        instrumentation.transition_count = transition
        _capture_controller_act(instrumentation, self, observation, action)
        return action


def _needs_pre_capture(
    instrumentation: _Instrumentation,
    controller: d026.D026Controller,
    observation: d027.D027Observation,
    transition: int,
) -> bool:
    if instrumentation.target_transition == transition:
        return True
    if instrumentation.arm != "LEARNED_WITH_DETRAP" or observation.charging_contact:
        return False
    return controller.mode in {
        d026.D026Mode.CHARGE,
        d026.D026Mode.SEEK,
    } or (
        controller.mode is d026.D026Mode.AWAY
        and observation.energy < EXP003_B50_ENTER_SEEK_THRESHOLD
    )


def _run_instrumented(
    seed: int, arm: str, horizon: int, target_transition: int | None = None
) -> tuple[dict[str, object], tuple[d025.D025TransitionTrace, ...], _Instrumentation]:
    instrumentation = _Instrumentation(arm, target_transition)
    trace: list[d025.D025TransitionTrace] = []
    original_initial_environment = d031r1._initial_environment
    original_query = d031r1._query_candidate_predictions
    _InstrumentedController.instrumentation = instrumentation
    _InstrumentedNoDetrapController.instrumentation = instrumentation
    _InstrumentedLearner.instrumentation = instrumentation

    def initial_environment(
        requested_horizon: int, requested_seed: int
    ) -> tuple[d026.D026Env, Any, Any]:
        result = original_initial_environment(requested_horizon, requested_seed)
        instrumentation.environment = result[0]
        instrumentation.streams = result[2]
        return result

    def query(
        learner: d027.D027ActionConsequencePredictor,
        current: d027.D027Observation,
    ) -> tuple[dict[Action, d027.D027Prediction], bool]:
        result = original_query(learner, current)
        event = instrumentation.current_event
        if event is not None:
            event.predictions = {
                action: prediction.values for action, prediction in result[0].items()
            }
            event.prediction_query_read_only = result[1]
        return result

    with ExitStack() as stack:
        stack.enter_context(
            patch.object(d031r1, "_initial_environment", initial_environment)
        )
        stack.enter_context(patch.object(d031r1, "_query_candidate_predictions", query))
        stack.enter_context(
            patch.object(d026, "D026Controller", _InstrumentedController)
        )
        stack.enter_context(
            patch.object(
                d031r1, "D031R1NoDetrapController", _InstrumentedNoDetrapController
            )
        )
        stack.enter_context(
            patch.object(d027, "D027ActionConsequencePredictor", _InstrumentedLearner)
        )
        result = d031r1._run_arm(
            seed,
            arm=arm,
            horizon=horizon,
            evaluator_diagnostics=True,
            trace_sink=trace,
        )
    if instrumentation.update_count != result["transitions"]:
        raise RuntimeError("D-032 instrumentation update count diverged")
    if instrumentation.transition_count != result["transitions"]:
        raise RuntimeError("D-032 instrumentation transition count diverged")
    return result, tuple(trace), instrumentation


def _compare_identity_fields(
    left: dict[str, object], right: dict[str, object], *, include_private_weights: bool
) -> dict[str, object]:
    fields = list(_CAUSAL_IDENTITY_FIELDS)
    if include_private_weights:
        fields.append("_weights")
    mismatches = [field for field in fields if left.get(field) != right.get(field)]
    return {
        "all_identity_fields_exact": not mismatches,
        "checked_fields": fields,
        "mismatched_fields": mismatches,
    }


def _accepted_artifact() -> dict[str, object]:
    root = Path(__file__).resolve().parents[2]
    path = root / D032_ACCEPTED_D031R1_ARTIFACT
    if not path.is_file():
        raise RuntimeError(f"accepted D-031R1 artifact is missing: {path}")
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def _accepted_artifact_sha256() -> str:
    root = Path(__file__).resolve().parents[2]
    path = root / D032_ACCEPTED_D031R1_ARTIFACT
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _accepted_arm(
    artifact: dict[str, object], seed: int, arm: str
) -> dict[str, object]:
    results = cast(list[dict[str, object]], artifact["results"])
    for result in results:
        if result["seed"] == seed:
            return cast(dict[str, object], cast(dict[str, object], result["arms"])[arm])
    raise RuntimeError(f"accepted D-031R1 artifact has no seed {seed}")


def _trace_map(
    trace: tuple[d025.D025TransitionTrace, ...],
) -> dict[int, d025.D025TransitionTrace]:
    return {record.transition_index: record for record in trace}


def _seek_ranges(result: dict[str, object]) -> list[tuple[int, int, dict[str, object]]]:
    total = cast(int, result["transitions"])
    ranges: list[tuple[int, int, dict[str, object]]] = []
    for episode in cast(list[dict[str, object]], result["seek_episodes"]):
        start = cast(int, episode["seek_entry_transition"])
        reacquisition = episode.get("reacquisition_transition")
        end = cast(int, reacquisition) if reacquisition is not None else total
        ranges.append((start, end, episode))
    return ranges


def _range_for_transition(
    ranges: list[tuple[int, int, dict[str, object]]], transition: int
) -> tuple[int, int, dict[str, object]] | None:
    return next((item for item in ranges if item[0] <= transition <= item[1]), None)


def _heading_before(
    trace_map: dict[int, d025.D025TransitionTrace], transition: int
) -> float:
    if transition <= 1:
        return d024.D024_INITIAL_HEADING
    return trace_map[transition - 1].telemetry.heading


def _motion_metrics(
    trace: tuple[d025.D025TransitionTrace, ...],
    start_transition: int,
    requested_window: int,
    origin_position: tuple[float, float],
    origin_observation: tuple[float, ...],
    stop_transition: int | None = None,
    trace_map: dict[int, d025.D025TransitionTrace] | None = None,
) -> dict[str, object]:
    trace_map = trace_map if trace_map is not None else _trace_map(trace)
    if start_transition not in trace_map:
        return {"status": "unavailable", "requested_transitions": requested_window}
    final_transition = min(
        start_transition + requested_window - 1,
        len(trace),
        stop_transition if stop_transition is not None else len(trace),
    )
    rows = [trace_map[index] for index in range(start_transition, final_transition + 1)]
    positions = [row.telemetry.position_after for row in rows]
    distances = [
        math.dist(position, rows[0].telemetry.station_center) for position in positions
    ]
    forward_values = [origin_observation[2], *(row.observation[2] for row in rows)]
    actions = Counter(row.action.name for row in rows)
    boundaries = Counter(
        boundary
        for row in rows
        if (boundary := _forward_boundary(row.telemetry, row.action)) is not None
    )
    path_length = sum(
        math.dist(row.telemetry.position_before, row.telemetry.position_after)
        for row in rows
    )
    heading = _heading_before(trace_map, start_transition)
    cumulative_heading_change = 0.0
    for row in rows:
        cumulative_heading_change += _angle_difference(heading, row.telemetry.heading)
        heading = row.telemetry.heading
    endpoint = positions[-1]
    net_vector = (endpoint[0] - origin_position[0], endpoint[1] - origin_position[1])
    contact_transition = next(
        (
            row.transition_index
            for row in rows
            if not row.telemetry.charging_contact_before
            and row.telemetry.charging_contact_after
        ),
        None,
    )
    energies = [origin_observation[0], *(row.observation[0] for row in rows)]
    return {
        "status": "observed",
        "requested_transitions": requested_window,
        "observed_transitions": len(rows),
        "stopped_early": len(rows) < requested_window,
        "net_body_center_displacement": {
            "vector": list(net_vector),
            "magnitude": math.dist(origin_position, endpoint),
        },
        "total_path_length": path_length,
        "change_in_evaluator_distance_to_station": distances[-1]
        - math.dist(origin_position, rows[0].telemetry.station_center),
        "minimum_evaluator_distance_to_station": min(distances),
        "visible_beacon_forward_change": forward_values[-1] - origin_observation[2],
        "maximum_visible_beacon_forward_reached": max(forward_values),
        "cumulative_absolute_heading_change": cumulative_heading_change,
        "action_counts": {name: actions[name] for name in _ACTION_NAMES},
        "forward_boundary_counts": {
            name: boundaries[name] for name in D032_BOUNDARY_CLASSES
        },
        "charging_contact_or_reacquisition": contact_transition is not None,
        "reacquisition_transition": contact_transition,
        "energy_change": energies[-1] - origin_observation[0],
        "minimum_energy": min(energies),
    }


def _first_delegation_event(
    events: list[_CapturedDecision],
) -> _CapturedDecision | None:
    return next((event for event in events if event.delegated), None)


def _first_onset(
    seed: int,
    a_result: dict[str, object],
    a_trace: tuple[d025.D025TransitionTrace, ...],
    a_instrumentation: _Instrumentation,
    b_result: dict[str, object],
    b_trace: tuple[d025.D025TransitionTrace, ...],
    b_instrumentation: _Instrumentation,
) -> dict[str, object]:
    a_event = _first_delegation_event(a_instrumentation.events)
    if a_event is None:
        return {
            "status": "BLOCKED_NO_ARM_A_DELEGATION",
            "seed": seed,
            "pre_treatment_match": False,
            "blocker": "Arm A had no delegated false-contact SEEK decision",
            "windows": {},
        }
    b_event = next(
        (
            event
            for event in b_instrumentation.events
            if event.transition == a_event.transition
        ),
        None,
    )
    if b_event is None:
        return {
            "status": "BLOCKED_NO_MATCHING_ARM_B_DECISION",
            "seed": seed,
            "treatment_transition": a_event.transition,
            "pre_treatment_match": False,
            "blocker": "Arm B had no corresponding transition",
            "windows": {},
        }
    a_prefix = a_trace[: a_event.transition - 1]
    b_prefix = b_trace[: b_event.transition - 1]
    match_checks = {
        "completed_real_trajectory_prefix": a_prefix == b_prefix,
        "current_six_channel_observation": a_event.current == b_event.current,
        "physical_environment_state": a_event.environment_state
        == b_event.environment_state,
        "controller_state_before_treatment": a_event.controller_state_before
        == b_event.controller_state_before,
        "learner_weights": a_event.learner_weights == b_event.learner_weights,
        "learner_state_digest": a_event.learner_digest == b_event.learner_digest,
        "policy_rng_state_before_delegation_draw": a_event.policy_rng_before
        == b_event.policy_rng_before,
        "environment_rng_state": a_event.environment_rng_before
        == b_event.environment_rng_before,
        "executed_update_prefix_digest": a_event.update_prefix_digest
        == b_event.update_prefix_digest,
        "same_transition_index": a_event.transition == b_event.transition,
    }
    pre_treatment_match = all(match_checks.values())
    treatment_checks = {
        "delegation_draw_exact_equal": a_event.delegation_draw
        == b_event.delegation_draw,
        "arm_a_delegated": a_event.delegated is True,
        "arm_b_not_delegated": b_event.delegated is False,
        "arm_b_learned_predictions_captured": b_event.predictions is not None,
        "arm_b_false_contact_explorer_calls_zero": cast(
            int,
            cast(dict[str, object], b_result["seek_arbitration"])[
                "false_contact_seek_explorer_calls"
            ],
        )
        == 0,
    }
    if not pre_treatment_match:
        return {
            "status": "BLOCKED_PRE_TREATMENT_MISMATCH",
            "seed": seed,
            "treatment_transition": a_event.transition,
            "pre_treatment_match": False,
            "pre_treatment_checks": match_checks,
            "treatment_checks": treatment_checks,
            "prefix_transition_count": len(a_prefix),
            "prefix_trace_digest_arm_a": d027._trace_digest(a_prefix),
            "prefix_trace_digest_arm_b": d027._trace_digest(b_prefix),
            "windows": {},
        }

    if a_event.environment_snapshot is None:
        raise RuntimeError("D-032 first-treatment snapshot is missing")
    origin_position = a_event.environment_snapshot.body
    if origin_position is None:
        raise RuntimeError("D-032 first-treatment snapshot has no body")
    origin = origin_position.position
    origin_observation = tuple(
        (
            a_event.current.energy,
            a_event.current.beacon.left,
            a_event.current.beacon.forward,
            a_event.current.beacon.right,
            float(a_event.current.charging_contact),
            a_event.current.thermal,
        )
    )
    branch_before = d029._environment_state(a_event.environment_snapshot)
    branches = d031r1._evaluate_steering_branches(
        a_event.environment_snapshot, a_event.current
    )
    branch_after = d029._environment_state(a_event.environment_snapshot)
    actual = {
        action.name: branches[action].delta[d031r1.D031R1_FORWARD_OUTPUT_INDEX]
        for action in D032_STEERING_ACTIONS
    }
    truth = d031r1._exact_argmax(
        {
            action: branches[action].delta[d031r1.D031R1_FORWARD_OUTPUT_INDEX]
            for action in D032_STEERING_ACTIONS
        }
    )
    if b_event.predictions is None or a_event.predictions is None:
        raise RuntimeError("D-032 first-treatment predictions were not captured")
    predicted_a = {
        action.name: a_event.predictions[action][d031r1.D031R1_FORWARD_OUTPUT_INDEX]
        for action in D032_STEERING_ACTIONS
    }
    predicted_b = {
        action.name: b_event.predictions[action][d031r1.D031R1_FORWARD_OUTPUT_INDEX]
        for action in D032_STEERING_ACTIONS
    }
    learned_scores = {
        action.name: a_event.current.beacon.forward + predicted_a[action.name]
        for action in D032_STEERING_ACTIONS
    }
    b_action = d031r1._choose_steering_action(
        b_event.current,
        {
            action: d027.D027Prediction(b_event.predictions[action])
            for action in D032_STEERING_ACTIONS
        },
        cast(Action, b_event.greedy_action),
    )
    first_episode = _range_for_transition(_seek_ranges(a_result), a_event.transition)
    if first_episode is None:
        raise RuntimeError("D-032 first delegation is outside all SEEK episodes")
    stop_transition = first_episode[1]
    windows: dict[str, dict[str, object]] = {}
    b_episode = _range_for_transition(_seek_ranges(b_result), b_event.transition)
    for window in D032_WINDOWS:
        windows[str(window)] = {
            "arm_a": _motion_metrics(
                a_trace,
                a_event.transition,
                window,
                origin,
                origin_observation,
                stop_transition,
            ),
            "arm_b": _motion_metrics(
                b_trace,
                b_event.transition,
                window,
                origin,
                origin_observation,
                b_episode[1] if b_episode is not None else None,
            ),
        }
    return {
        "status": "MATCHED_TREATMENT_ONSET",
        "seed": seed,
        "treatment_transition": a_event.transition,
        "pre_treatment_match": True,
        "pre_treatment_checks": match_checks,
        "treatment_checks": treatment_checks,
        "prefix_transition_count": len(a_prefix),
        "prefix_trace_digest_arm_a": d027._trace_digest(a_prefix),
        "prefix_trace_digest_arm_b": d027._trace_digest(b_prefix),
        "common_current_observation": list(origin_observation),
        "common_evaluator_position": list(origin),
        "immediate_one_step": {
            "arm_a_explorer_selected_action": a_event.action.name,
            "arm_b_learned_selected_action": b_action.name,
            "historical_greedy_action": cast(Action, a_event.greedy_action).name,
            "actual_delta_beacon_forward": actual,
            "exact_one_step_truth_argmax": [action.name for action in truth],
            "arm_a_action_in_truth_argmax": a_event.action in truth,
            "arm_b_action_in_truth_argmax": b_action in truth,
            "d027_predicted_delta_beacon_forward_arm_a": predicted_a,
            "d027_predicted_delta_beacon_forward_arm_b": predicted_b,
            "d030_learned_score_arm_a": learned_scores,
            "prediction_error_actual_minus_predicted": {
                "arm_a_action": actual[a_event.action.name]
                - predicted_a[a_event.action.name],
                "arm_b_action": actual[b_action.name] - predicted_b[b_action.name],
            },
            "absolute_prediction_error": {
                "arm_a_action": abs(
                    actual[a_event.action.name] - predicted_a[a_event.action.name]
                ),
                "arm_b_action": abs(actual[b_action.name] - predicted_b[b_action.name]),
            },
            "behaviorally_effective": a_event.action is not b_action,
            "branch_environment_unchanged": branch_before == branch_after,
            "predictions_a_b_exact_equal": predicted_a == predicted_b,
        },
        "windows": windows,
    }


def _run_length_distribution(actions: list[Action]) -> dict[str, int]:
    runs: Counter[str] = Counter()
    if not actions:
        return {}
    current = actions[0]
    length = 1
    for action in actions[1:]:
        if action is current:
            length += 1
        else:
            runs[f"{current.name}:{length}"] += 1
            current = action
            length = 1
    runs[f"{current.name}:{length}"] += 1
    return _counter_dict(runs)


def _seek_diagnostics(
    result: dict[str, object], trace: tuple[d025.D025TransitionTrace, ...]
) -> dict[str, object]:
    trace_map = _trace_map(trace)
    all_actions: list[Action] = []
    forward_displacements: list[float] = []
    distances: list[float] = []
    paths: list[float] = []
    net_displacements: list[float] = []
    max_displacements: list[float] = []
    heading_changes: list[float] = []
    final_distances: list[float] = []
    boundary_counts = Counter[str]()
    action_counts = Counter[str]()
    action_transitions = Counter[str]()
    run_lengths = Counter[str]()
    longest_move = 0
    turn_sign_reversals = 0
    episode_summaries: list[dict[str, object]] = []
    for start, end, episode in _seek_ranges(result):
        rows = [trace_map[index] for index in range(start, end + 1)]
        actions = [row.action for row in rows]
        all_actions.extend(actions)
        action_counts.update(action.name for action in actions)
        for left, right in zip(actions, actions[1:], strict=False):
            action_transitions[f"{left.name}->{right.name}"] += 1
            if left is Action.TURN_LEFT and right is Action.TURN_RIGHT:
                turn_sign_reversals += 1
            if left is Action.TURN_RIGHT and right is Action.TURN_LEFT:
                turn_sign_reversals += 1
        run_lengths.update(_run_length_distribution(actions))
        move_run = 0
        longest_episode_move = 0
        for action in actions:
            move_run = move_run + 1 if action is Action.MOVE_FORWARD else 0
            longest_episode_move = max(longest_episode_move, move_run)
        longest_move = max(longest_move, longest_episode_move)
        positions = [row.telemetry.position_after for row in rows]
        entry_position = rows[0].telemetry.position_before
        station = rows[0].telemetry.station_center
        episode_distances = [math.dist(position, station) for position in positions]
        episode_path = sum(
            math.dist(row.telemetry.position_before, row.telemetry.position_after)
            for row in rows
        )
        episode_net = math.dist(entry_position, positions[-1])
        episode_max_displacement = max(
            math.dist(entry_position, position) for position in positions
        )
        episode_heading_change = 0.0
        heading = _heading_before(trace_map, start)
        for row in rows:
            episode_heading_change += _angle_difference(heading, row.telemetry.heading)
            heading = row.telemetry.heading
        episode_boundaries = Counter(
            boundary
            for row in rows
            if (boundary := _forward_boundary(row.telemetry, row.action)) is not None
        )
        boundary_counts.update(episode_boundaries)
        for row in rows:
            if row.action is Action.MOVE_FORWARD:
                forward_displacements.append(
                    math.dist(
                        row.telemetry.position_before, row.telemetry.position_after
                    )
                )
        distances.extend(episode_distances)
        final_distances.append(episode_distances[-1])
        paths.append(episode_path)
        net_displacements.append(episode_net)
        max_displacements.append(episode_max_displacement)
        heading_changes.append(episode_heading_change)
        episode_summaries.append(
            {
                "seek_entry_transition": start,
                "end_transition": end,
                "outcome": episode["outcome"],
                "boundary_counts": {
                    name: episode_boundaries[name] for name in D032_BOUNDARY_CLASSES
                },
                "action_counts": {
                    name: actions.count(Action[name]) for name in _ACTION_NAMES
                },
                "path_length": episode_path,
                "net_displacement": episode_net,
                "maximum_displacement_from_seek_entry": episode_max_displacement,
                "distance_to_station": _json_number_summary(episode_distances),
                "cumulative_absolute_heading_change": episode_heading_change,
                "reacquisition_transition": episode.get("reacquisition_transition"),
            }
        )
    return {
        "seek_episode_count": len(episode_summaries),
        "boundary_counts": {
            name: boundary_counts[name] for name in D032_BOUNDARY_CLASSES
        },
        "boundary_fractions_of_forward_actions": {
            name: boundary_counts[name] / sum(boundary_counts.values())
            if sum(boundary_counts.values())
            else None
            for name in D032_BOUNDARY_CLASSES
        },
        "realized_forward_displacement_distribution": _json_number_summary(
            forward_displacements
        ),
        "path_length_distribution": _json_number_summary(paths),
        "net_displacement_distribution": _json_number_summary(net_displacements),
        "minimum_median_final_evaluator_distance_to_station": {
            "minimum": min(distances) if distances else None,
            "median": statistics.median(distances) if distances else None,
            "final_by_episode": final_distances,
        },
        "maximum_displacement_from_seek_entry_distribution": _json_number_summary(
            max_displacements
        ),
        "exact_same_action_run_length_distribution": _counter_dict(run_lengths),
        "longest_consecutive_move_forward_run": longest_move,
        "action_to_action_transition_matrix": {
            left: {
                right: action_transitions[f"{left}->{right}"] for right in _ACTION_NAMES
            }
            for left in _ACTION_NAMES
        },
        "cumulative_absolute_heading_change_distribution": _json_number_summary(
            heading_changes
        ),
        "consecutive_turn_heading_sign_reversals": turn_sign_reversals,
        "action_counts": {name: action_counts[name] for name in _ACTION_NAMES},
        "episode_summaries": episode_summaries,
        "trace_transition_count": len(all_actions),
        "_raw_distributions": {
            "forward_displacements": forward_displacements,
            "distances": distances,
            "paths": paths,
            "net_displacements": net_displacements,
            "maximum_displacements": max_displacements,
            "heading_changes": heading_changes,
            "final_distances": final_distances,
        },
    }


def _merge_nested_counts(destination: dict[str, int], source: dict[str, int]) -> None:
    for key, value in source.items():
        destination[key] = destination.get(key, 0) + value


def _pooled_seek_diagnostics(items: list[dict[str, object]]) -> dict[str, object]:
    boundary_counts: dict[str, int] = {}
    run_lengths: dict[str, int] = {}
    action_counts: dict[str, int] = {}
    transition_matrix = {
        left: {right: 0 for right in _ACTION_NAMES} for left in _ACTION_NAMES
    }
    forward: list[float] = []
    paths: list[float] = []
    net: list[float] = []
    max_displacement: list[float] = []
    heading: list[float] = []
    distances: list[float] = []
    final_distances: list[float] = []
    episode_count = 0
    longest_move = 0
    reversals = 0
    for item in items:
        episode_count += cast(int, item["seek_episode_count"])
        _merge_nested_counts(
            boundary_counts, cast(dict[str, int], item["boundary_counts"])
        )
        _merge_nested_counts(
            run_lengths,
            cast(dict[str, int], item["exact_same_action_run_length_distribution"]),
        )
        _merge_nested_counts(action_counts, cast(dict[str, int], item["action_counts"]))
        raw = cast(dict[str, list[float]], item["_raw_distributions"])
        forward.extend(raw["forward_displacements"])
        paths.extend(raw["paths"])
        net.extend(raw["net_displacements"])
        max_displacement.extend(raw["maximum_displacements"])
        heading.extend(raw["heading_changes"])
        distances.extend(raw["distances"])
        final_distances.extend(raw["final_distances"])
        for left in _ACTION_NAMES:
            matrix = cast(
                dict[str, dict[str, int]], item["action_to_action_transition_matrix"]
            )
            row = matrix[left]
            _merge_nested_counts(transition_matrix[left], row)
        longest_move = max(
            longest_move, cast(int, item["longest_consecutive_move_forward_run"])
        )
        reversals += cast(int, item["consecutive_turn_heading_sign_reversals"])
    return {
        "seek_episode_count": episode_count,
        "boundary_counts": {
            name: boundary_counts.get(name, 0) for name in D032_BOUNDARY_CLASSES
        },
        "boundary_fractions_of_forward_actions": {
            name: boundary_counts.get(name, 0) / sum(boundary_counts.values())
            if sum(boundary_counts.values())
            else None
            for name in D032_BOUNDARY_CLASSES
        },
        "realized_forward_displacement_distribution": _json_number_summary(forward),
        "path_length_distribution": _json_number_summary(paths),
        "net_displacement_distribution": _json_number_summary(net),
        "minimum_median_final_evaluator_distance_to_station": {
            "minimum": min(distances) if distances else None,
            "median": statistics.median(distances) if distances else None,
            "final_by_episode": final_distances,
        },
        "maximum_displacement_from_seek_entry_distribution": _json_number_summary(
            max_displacement
        ),
        "exact_same_action_run_length_distribution": run_lengths,
        "longest_consecutive_move_forward_run": longest_move,
        "action_to_action_transition_matrix": transition_matrix,
        "cumulative_absolute_heading_change_distribution": _json_number_summary(
            heading
        ),
        "consecutive_turn_heading_sign_reversals": reversals,
        "action_counts": {name: action_counts.get(name, 0) for name in _ACTION_NAMES},
    }


def _event_timing(
    result: dict[str, object], events: list[_CapturedDecision]
) -> dict[str, object]:
    by_episode: list[dict[str, object]] = []
    all_first_to_reacquisition: list[float] = []
    all_last_effective_to_reacquisition: list[float] = []
    total_delegated = 0
    total_effective = 0
    delegated_action_counts: Counter[str] = Counter()
    effective_action_counts: Counter[str] = Counter()
    for start, end, episode in _seek_ranges(result):
        episode_events = [
            event
            for event in events
            if start <= event.transition <= end and event.delegated
        ]
        effective = [
            event for event in episode_events if event.action is not event.greedy_action
        ]
        total_delegated += len(episode_events)
        total_effective += len(effective)
        delegated_action_counts.update(event.action.name for event in episode_events)
        effective_action_counts.update(event.action.name for event in effective)
        reacquisition = episode.get("reacquisition_transition")
        first_to_reacquisition = (
            cast(int, reacquisition) - episode_events[0].transition
            if reacquisition is not None and episode_events
            else None
        )
        last_effective_to_reacquisition = (
            cast(int, reacquisition) - effective[-1].transition
            if reacquisition is not None and effective
            else None
        )
        if first_to_reacquisition is not None:
            all_first_to_reacquisition.append(float(first_to_reacquisition))
        if last_effective_to_reacquisition is not None:
            all_last_effective_to_reacquisition.append(
                float(last_effective_to_reacquisition)
            )
        by_episode.append(
            {
                "seek_entry_transition": start,
                "end_transition": end,
                "outcome": episode["outcome"],
                "delegated_count_before_end": len(episode_events),
                "effective_delegated_count_before_end": len(effective),
                "first_delegation_transition": episode_events[0].transition
                if episode_events
                else None,
                "last_effective_delegation_transition": effective[-1].transition
                if effective
                else None,
                "time_from_first_delegation_to_reacquisition": first_to_reacquisition,
                "time_from_last_effective_delegation_to_reacquisition": (
                    last_effective_to_reacquisition
                ),
            }
        )
    return {
        "delegated_decision_count": total_delegated,
        "delegated_effective_perturbation_count": total_effective,
        "delegated_action_counts": {
            name: delegated_action_counts[name] for name in _ACTION_NAMES
        },
        "effective_delegated_action_counts": {
            name: effective_action_counts[name] for name in _ACTION_NAMES
        },
        "time_from_first_delegation_to_reacquisition": _json_number_summary(
            all_first_to_reacquisition
        ),
        "time_from_last_effective_delegation_to_reacquisition": _json_number_summary(
            all_last_effective_to_reacquisition
        ),
        "per_seek_episode": by_episode,
    }


def _aggregate_event_metrics(
    metrics: list[dict[str, object]], window: int
) -> dict[str, object]:
    keys = (
        "total_path_length",
        "change_in_evaluator_distance_to_station",
        "minimum_evaluator_distance_to_station",
        "visible_beacon_forward_change",
        "maximum_visible_beacon_forward_reached",
        "cumulative_absolute_heading_change",
        "energy_change",
        "minimum_energy",
    )
    numeric: dict[str, list[float]] = {key: [] for key in keys}
    action_counts = {name: 0 for name in _ACTION_NAMES}
    boundary_counts = {name: 0 for name in D032_BOUNDARY_CLASSES}
    reacquisition_count = 0
    for metric in metrics:
        if metric.get("status") != "observed":
            continue
        for key in keys:
            numeric[key].append(cast(float, metric[key]))
        _merge_nested_counts(
            action_counts, cast(dict[str, int], metric["action_counts"])
        )
        _merge_nested_counts(
            boundary_counts, cast(dict[str, int], metric["forward_boundary_counts"])
        )
        reacquisition_count += int(metric["charging_contact_or_reacquisition"] is True)
    return {
        "requested_transitions": window,
        "event_count": len(metrics),
        "observed_window_count": sum(
            int(metric.get("status") == "observed") for metric in metrics
        ),
        "metrics": {
            key: _json_number_summary(values) for key, values in numeric.items()
        },
        "action_counts": action_counts,
        "forward_boundary_counts": boundary_counts,
        "reacquisition_count": reacquisition_count,
    }


def _delegated_event_diagnostics(
    result: dict[str, object],
    trace: tuple[d025.D025TransitionTrace, ...],
    events: list[_CapturedDecision],
) -> dict[str, object]:
    trace_map = _trace_map(trace)
    classified: dict[str, list[_CapturedDecision]] = {
        "effective": [],
        "ineffective": [],
    }
    for event in events:
        if not event.delegated:
            continue
        if _range_for_transition(_seek_ranges(result), event.transition) is None:
            continue
        label = (
            "effective" if event.action is not event.greedy_action else "ineffective"
        )
        classified[label].append(event)
    by_effectiveness: dict[str, object] = {}
    ranges = _seek_ranges(result)
    for label, selected in classified.items():
        windows: dict[str, object] = {}
        for window in D032_WINDOWS:
            values: list[dict[str, object]] = []
            for event in selected:
                episode = _range_for_transition(ranges, event.transition)
                if episode is None or event.transition not in trace_map:
                    continue
                origin_position = trace_map[event.transition].telemetry.position_before
                origin_observation = (
                    event.current.energy,
                    event.current.beacon.left,
                    event.current.beacon.forward,
                    event.current.beacon.right,
                    float(event.current.charging_contact),
                    event.current.thermal,
                )
                values.append(
                    _motion_metrics(
                        trace,
                        event.transition,
                        window,
                        origin_position,
                        origin_observation,
                        episode[1],
                        trace_map=trace_map,
                    )
                )
            windows[str(window)] = _aggregate_event_metrics(values, window)
        by_effectiveness[label] = {
            "event_count": len(selected),
            "state_confounded": True,
            "windows": windows,
        }
    return by_effectiveness


def _one_step_fidelity(
    result: dict[str, object], onset_transition: int | None
) -> dict[str, object]:
    records = cast(list[dict[str, object]], result["_decision_records"])
    output: dict[str, object] = {
        "whole_seek": d031r1._aggregate_diagnostics(records),
        "by_post_treatment_window": {},
    }
    if onset_transition is not None:
        output["by_post_treatment_window"] = {
            str(window): d031r1._aggregate_diagnostics(
                [
                    record
                    for record in records
                    if onset_transition
                    <= cast(int, record["transition"])
                    < onset_transition + window
                ]
            )
            for window in D032_WINDOWS
        }
    return output


def _seed_result(
    seed: int, horizon: int, artifact: dict[str, object]
) -> dict[str, object]:
    _validate_d032_seed(seed)
    if horizon != D032_HORIZON:
        raise ValueError("D-032 requires the frozen 70,000-transition horizon")
    runs: dict[str, dict[str, object]] = {}
    traces: dict[str, tuple[d025.D025TransitionTrace, ...]] = {}
    instrumentation: dict[str, _Instrumentation] = {}
    replays: dict[str, object] = {}
    for arm in D032_ARM_NAMES:
        target_transition = None
        if arm == "LEARNED_NO_DETRAP" and "LEARNED_WITH_DETRAP" in instrumentation:
            first = _first_delegation_event(
                instrumentation["LEARNED_WITH_DETRAP"].events
            )
            target_transition = first.transition if first is not None else None
        diagnostic, trace, captured = _run_instrumented(
            seed, arm, horizon, target_transition
        )
        control = d031r1._run_arm(
            seed, arm=arm, horizon=horizon, evaluator_diagnostics=False
        )
        diagnostic_vs_control = _compare_identity_fields(
            diagnostic, control, include_private_weights=True
        )
        if not cast(bool, diagnostic_vs_control["all_identity_fields_exact"]):
            raise RuntimeError(
                f"D-032 causal replay diverged for {arm}, seed {seed}: "
                f"{diagnostic_vs_control['mismatched_fields']}"
            )
        accepted = _accepted_arm(artifact, seed, arm)
        control_vs_accepted = _compare_identity_fields(
            control, accepted, include_private_weights=False
        )
        if not cast(bool, control_vs_accepted["all_identity_fields_exact"]):
            raise RuntimeError(
                f"D-031R1 accepted replay diverged for {arm}, seed {seed}: "
                f"{control_vs_accepted['mismatched_fields']}"
            )
        runs[arm] = diagnostic
        traces[arm] = trace
        instrumentation[arm] = captured
        replays[arm] = {
            "diagnostic_vs_direct_d031r1": diagnostic_vs_control,
            "direct_d031r1_vs_accepted_artifact": control_vs_accepted,
        }
    onset = _first_onset(
        seed,
        runs["LEARNED_WITH_DETRAP"],
        traces["LEARNED_WITH_DETRAP"],
        instrumentation["LEARNED_WITH_DETRAP"],
        runs["LEARNED_NO_DETRAP"],
        traces["LEARNED_NO_DETRAP"],
        instrumentation["LEARNED_NO_DETRAP"],
    )
    onset_transition = onset.get("treatment_transition")
    onset_index = cast(int, onset_transition) if onset_transition is not None else None
    arm_diagnostics: dict[str, object] = {}
    for arm in D032_ARM_NAMES:
        arm_diagnostics[arm] = {
            "whole_seek": _seek_diagnostics(runs[arm], traces[arm]),
            "detrap_event_timing": _event_timing(
                runs[arm], instrumentation[arm].events
            ),
            "delegated_event_centered": _delegated_event_diagnostics(
                runs[arm], traces[arm], instrumentation[arm].events
            ),
            "one_step_fidelity": _one_step_fidelity(runs[arm], onset_index),
        }
    return {
        "seed": seed,
        "replay_equivalence": replays,
        "first_delegation_onset": onset,
        "arms": {
            arm: {
                key: value
                for key, value in runs[arm].items()
                if key not in {"_decision_records", "_weights", "final_weights"}
            }
            for arm in D032_ARM_NAMES
        },
        "diagnostics": arm_diagnostics,
        "_one_step_records": {
            arm: runs[arm]["_decision_records"] for arm in D032_ARM_NAMES
        },
    }


def _pooled_fidelity(
    seed_results: list[dict[str, object]], arm: str
) -> dict[str, object]:
    records: list[dict[str, object]] = []
    window_records: dict[int, list[dict[str, object]]] = {
        window: [] for window in D032_WINDOWS
    }
    for item in seed_results:
        raw_records = cast(
            dict[str, list[dict[str, object]]], item["_one_step_records"]
        )
        records.extend(raw_records[arm])
        onset = cast(dict[str, object], item["first_delegation_onset"])
        transition = onset.get("treatment_transition")
        if transition is None:
            continue
        onset_transition = cast(int, transition)
        for window in D032_WINDOWS:
            window_records[window].extend(
                record
                for record in raw_records[arm]
                if onset_transition
                <= cast(int, record["transition"])
                < onset_transition + window
            )
    return {
        "whole_seek": d031r1._aggregate_diagnostics(records),
        "by_post_treatment_window": {
            str(window): d031r1._aggregate_diagnostics(window_records[window])
            for window in D032_WINDOWS
        },
        "per_seed_count": len(seed_results),
    }


def _pooled_onset_windows(seed_results: list[dict[str, object]]) -> dict[str, object]:
    pooled: dict[str, dict[str, list[dict[str, object]]]] = {
        str(window): {"arm_a": [], "arm_b": []} for window in D032_WINDOWS
    }
    for item in seed_results:
        onset = cast(dict[str, object], item["first_delegation_onset"])
        if onset.get("status") != "MATCHED_TREATMENT_ONSET":
            continue
        for window in D032_WINDOWS:
            values = cast(
                dict[str, object],
                cast(dict[str, object], onset["windows"])[str(window)],
            )
            pooled[str(window)]["arm_a"].append(
                cast(dict[str, object], values["arm_a"])
            )
            pooled[str(window)]["arm_b"].append(
                cast(dict[str, object], values["arm_b"])
            )
    return {
        str(window): {
            "matched_seed_count": len(pooled[str(window)]["arm_a"]),
            "arm_a": _aggregate_event_metrics(pooled[str(window)]["arm_a"], window),
            "arm_b": _aggregate_event_metrics(pooled[str(window)]["arm_b"], window),
        }
        for window in D032_WINDOWS
    }


def _seed_whole_seek(seed_result: dict[str, object], arm: str) -> dict[str, object]:
    diagnostics = cast(dict[str, dict[str, object]], seed_result["diagnostics"])
    return cast(dict[str, object], diagnostics[arm]["whole_seek"])


def run_d032_audit(
    seeds: tuple[int, ...] = D032_DEFAULT_DEVELOPMENT_SEEDS,
    *,
    horizon: int = D032_HORIZON,
    executed_commit_sha: str | None = None,
) -> dict[str, object]:
    """Run the exact reused-seed D-032 evaluator audit."""
    validated_seeds = _validate_d032_development_seeds(seeds)
    if horizon != D032_HORIZON:
        raise ValueError("D-032 requires the frozen 70,000-transition horizon")
    executed_sha = _validate_executed_commit_sha(executed_commit_sha)
    artifact = _accepted_artifact()
    seed_results = [_seed_result(seed, horizon, artifact) for seed in validated_seeds]
    match_statuses = [
        cast(dict[str, object], item["first_delegation_onset"]) for item in seed_results
    ]
    blockers = [
        item for item in match_statuses if item.get("pre_treatment_match") is not True
    ]
    whole_seek_by_arm: dict[str, list[dict[str, object]]] = {
        arm: [_seed_whole_seek(item, arm) for item in seed_results]
        for arm in D032_ARM_NAMES
    }
    pooled_whole_seek = {
        arm: _pooled_seek_diagnostics(whole_seek_by_arm[arm]) for arm in D032_ARM_NAMES
    }
    first_onset_summary = {
        "seed_count": len(seed_results),
        "matched_seed_count": sum(
            int(item.get("pre_treatment_match") is True) for item in match_statuses
        ),
        "blocker_count": len(blockers),
        "blockers": [
            {
                "seed": item.get("seed"),
                "status": item.get("status"),
                "blocker": item.get("blocker"),
            }
            for item in blockers
        ],
        "pooled_fixed_window_motion": _pooled_onset_windows(seed_results),
    }
    for item in seed_results:
        item.pop("_one_step_records")
        diagnostics = cast(dict[str, dict[str, object]], item["diagnostics"])
        for arm in D032_ARM_NAMES:
            cast(dict[str, object], diagnostics[arm]["whole_seek"]).pop(
                "_raw_distributions", None
            )
    return {
        "schema_version": 1,
        "experiment": "D-032",
        "title": "D-031R1 false-contact SEEK de-trap function attribution audit",
        "authoritative_base_sha": D032_AUTHORITATIVE_BASE_SHA,
        "base_tree_sha": D032_BASE_TREE_SHA,
        "implementation_probe_sha": executed_sha,
        "development_seeds": list(validated_seeds),
        "horizon": D032_HORIZON,
        "timestep_seconds": D020PhysicalConfig().dt_seconds,
        "simulated_duration_seconds": D032_HORIZON * D020PhysicalConfig().dt_seconds,
        "support": {
            "source": "accepted D-031R1 Development result",
            "accepted_artifact": D032_ACCEPTED_D031R1_ARTIFACT,
            "fresh_seed_block_allocated": False,
            "fresh_seed_block_inspected": False,
        },
        "freeze": {
            "causal_runner": "direct D-031R1 _run_arm reuse",
            "arms": list(D032_ARM_NAMES),
            "windows": list(D032_WINDOWS),
            "horizon": D032_HORIZON,
            "causal_behavior_changed": False,
            "organism_visible_channels_changed": False,
            "learner_changed": False,
            "reward": 0.0,
            "new_physics": False,
        },
        "causal_order": [
            "unchanged D-031R1 action selection",
            "evaluator-only onset capture after selection",
            "evaluator-only isolated one-step branch truth",
            "unchanged real transition and D-027 update",
            "post-hoc trace and geometry summaries",
        ],
        "organism_boundary": {
            "observation_action_history_added": False,
            "recurrence_added": False,
            "new_sensor_added": False,
            "reward_or_value_added": False,
            "evaluator_state_reaches_controller_or_learner": False,
        },
        "replay_equivalence": {
            "all_seeds_all_arms_exact": True,
            "checked_identity_fields": list(_CAUSAL_IDENTITY_FIELDS),
            "accepted_d031r1_artifact_sha256": _accepted_artifact_sha256(),
        },
        "first_delegation_analysis": first_onset_summary,
        "whole_seek_diagnostics": pooled_whole_seek,
        "one_step_fidelity": {
            "per_seed": {
                str(item["seed"]): {
                    arm: cast(
                        dict[str, object],
                        cast(dict[str, object], item["diagnostics"])[arm],
                    )["one_step_fidelity"]
                    for arm in D032_ARM_NAMES
                }
                for item in seed_results
            },
            "pooled": {
                arm: _pooled_fidelity(seed_results, arm) for arm in D032_ARM_NAMES
            },
        },
        "arm_a_delegated_event_diagnostics": {
            str(item["seed"]): cast(
                dict[str, object],
                cast(dict[str, object], item["diagnostics"])["LEARNED_WITH_DETRAP"],
            )["detrap_event_timing"]
            for item in seed_results
        },
        "results": seed_results,
        "interpretation": {
            "lane": "Development",
            "confirmatory_claim": False,
            "observed": (
                "direct trajectory, action, evaluator geometry, branch-truth, and "
                "replay-equivalence measurements"
            ),
            "supported_inference": (
                "candidate functions may be directionally consistent with the "
                "fixed-window and one-step contrasts, without a forced winner"
            ),
            "unresolved_hypotheses": [
                "boundary/stall escape",
                "temporal persistence / sequence generation",
                "symmetry breaking / oscillation escape",
                "prediction/selection deficiency",
                "non-myopic benefit",
                "experience diversification",
            ],
            "state_confounded_event_comparisons": True,
            "no_behavior_change_authorized": True,
            "no_successor_authorized": True,
        },
    }


def write_d032_json(path: Path, executed_commit_sha: str | None = None) -> Path:
    payload = run_d032_audit(executed_commit_sha=executed_commit_sha)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the D-032 attribution audit.")
    parser.add_argument("--executed-commit-sha")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.output is None:
        print(
            json.dumps(
                run_d032_audit(executed_commit_sha=args.executed_commit_sha),
                indent=2,
                sort_keys=True,
            )
        )
    else:
        write_d032_json(args.output, args.executed_commit_sha)
        print(f"D-032 result written to {args.output}")


if __name__ == "__main__":
    main()
