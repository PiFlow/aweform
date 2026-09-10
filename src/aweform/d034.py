"""D-034 evaluator-only history-triggered de-trap recruitment audit.

D-034 replays the accepted D-031R1 Arm-A/Arm-B lifetimes, reconstructs
closure-valid post-hoc Arm-B history anchors, and runs matched evaluator
branches from cloned Arm-B causal state.  The organism controller, learner,
observations, actions, reward, and physical environment are unchanged.
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
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, cast

from . import d025, d026, d027, d029, d031r1, d032, d033
from .d020 import D020PhysicalConfig
from .env import Action
from .exp003_seed_policy import validate_exp003_development_seeds
from .rng import RandomStreams

D034_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = tuple(range(18468, 18488))
D034_HORIZON: Final[int] = 70_000
D034_BRANCH_HORIZON: Final[int] = 4096
D034_LENGTHS: Final[tuple[int, ...]] = (4, 8, 16)
D034_TRIGGER_FAMILIES: Final[tuple[str, ...]] = (
    "ALT",
    "NO_FORWARD_PROGRESS",
)
D034_AUTHORITATIVE_BASE_SHA: Final[str] = "594a8a26a7c0e220c51f44fd1a3d477956d99414"
D034_BASE_TREE_SHA: Final[str] = "b8fb30224c3bf881fa4c4685926c29bcbf31b8b3"
D034_ACCEPTED_D031R1_ARTIFACT: Final[str] = d032.D032_ACCEPTED_D031R1_ARTIFACT
D034_SEEK_DELEGATION_PROBABILITY: Final[float] = (
    d031r1.D031R1_SEEK_DELEGATION_PROBABILITY
)
D034_NO_DETRAP_DELEGATION_PROBABILITY: Final[float] = (
    d031r1.D031R1_NO_DETRAP_DELEGATION_PROBABILITY
)
D034_EXPLORER_HAZARD: Final[float] = d031r1.D031R1_EXPLORER_HAZARD

_ACTION_NAMES: Final[tuple[str, ...]] = tuple(action.name for action in Action)
_TURN_ACTIONS: Final[frozenset[Action]] = frozenset(
    (Action.TURN_LEFT, Action.TURN_RIGHT)
)
_CAUSAL_IDENTITY_FIELDS: Final[tuple[str, ...]] = d032._CAUSAL_IDENTITY_FIELDS
_ANCHOR_REFERENCE: Final[str] = "MATCHED_FIRST_DELEGATION"


def _validate_d034_development_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    """Require exactly the reused D-031R1/D-032/D-033 support."""
    validated = validate_exp003_development_seeds(seeds)
    if validated != D034_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-034 requires exactly the reused development seeds "
            f"{D034_DEFAULT_DEVELOPMENT_SEEDS}; got {validated}"
        )
    return validated


def _validate_d034_seed(seed: int) -> None:
    validated = validate_exp003_development_seeds((seed,))
    if validated[0] not in D034_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-034 may execute only the reused development seeds "
            f"{D034_DEFAULT_DEVELOPMENT_SEEDS}; got {validated[0]}"
        )


def _validate_executed_commit_sha(value: str | None) -> str | None:
    return d031r1._validate_executed_commit_sha(value)


def _digest(value: object) -> str:
    return hashlib.sha256(pickle.dumps(value, protocol=5)).hexdigest()


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


def _rng_digests(streams: RandomStreams) -> tuple[str, str]:
    return (
        _digest(streams.policy.bit_generator.state),
        _digest(streams.environment.bit_generator.state),
    )


def _empty_action_counts() -> dict[str, int]:
    return {name: 0 for name in _ACTION_NAMES}


def _is_false_contact_seek(row: d025.D025TransitionTrace) -> bool:
    """Check the frozen false-contact SEEK eligibility domain.

    Trigger predicates themselves use only completed actions and the six
    visible observation channels.  The mode/contact checks restrict the
    window to the already-defined false-contact SEEK domain; no geometry,
    distance, heading, outcome, or evaluator branch state is consulted.
    """
    return (
        row.mode_before is d026.D026Mode.SEEK
        and row.mode_after is d026.D026Mode.SEEK
        and row.observation_before[4] == 0.0
        and row.observation[4] == 0.0
    )


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
        experienced_forward = [row.observation[2] for row in rows]
        return max(experienced_forward) <= starting_forward, starting_forward
    raise ValueError(f"unknown D-034 trigger family: {family}")


def _find_trigger(
    trace: Sequence[d025.D025TransitionTrace], family: str, length: int
) -> _TriggerSelection | None:
    if family not in D034_TRIGGER_FAMILIES:
        raise ValueError(f"unknown D-034 trigger family: {family}")
    if length not in D034_LENGTHS:
        raise ValueError(f"D-034 history length must be one of {D034_LENGTHS}")
    for end in range(length - 1, len(trace)):
        rows = tuple(trace[end - length + 1 : end + 1])
        matches, starting_forward = _trigger_matches(family, rows)
        if not matches:
            continue
        last_transition = rows[-1].transition_index
        next_transition = last_transition + 1
        if next_transition > len(trace):
            return None
        return _TriggerSelection(
            family=family,
            length=length,
            transition=next_transition,
            last_transition=last_transition,
            rows=rows,
            starting_forward=starting_forward,
        )
    return None


def _trigger_history(selection: _TriggerSelection) -> dict[str, object]:
    values = [
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
        "completed_actions": [row.action.name for row in selection.rows],
        "completed_observations": values,
        "closure_valid_history_digest": _digest(values),
        "uses_only_executed_actions_and_six_channel_observations": True,
        "hidden_geometry_or_future_outcome_used": False,
    }


def _accepted_artifact() -> dict[str, object]:
    return d033._accepted_artifact()


def _accepted_artifact_sha256() -> str:
    return d033._accepted_artifact_sha256()


def _accepted_arm(
    artifact: dict[str, object], seed: int, arm: str
) -> dict[str, object]:
    return d033._accepted_arm(artifact, seed, arm)


def _identity_gate(
    seed: int,
    arm: str,
    replay: dict[str, object],
    accepted: dict[str, object],
) -> dict[str, object]:
    accepted_with_private_weights = dict(accepted)
    accepted_with_private_weights["_weights"] = d033._flatten_final_weights(accepted)
    comparison = d032._compare_identity_fields(
        replay, accepted_with_private_weights, include_private_weights=True
    )
    isolation = cast(dict[str, object], replay["isolation"])
    required = {
        "all_identity_fields_exact": comparison["all_identity_fields_exact"],
        "zero_false_contact_seek_explorer_calls": (
            isolation["no_false_contact_seek_explorer_call"]
            if arm == "LEARNED_NO_DETRAP"
            else True
        ),
        "one_legacy_arbitration_draw_per_false_contact_seek_decision": isolation[
            "one_legacy_arbitration_draw_per_false_contact_seek_decision"
        ],
        "real_updates_executed_action_only": isolation[
            "real_updates_executed_action_only"
        ],
    }
    if not all(cast(bool, value) for value in required.values()):
        raise RuntimeError(f"D-034 accepted {arm} replay gate failed for seed {seed}")
    return {
        "seed": seed,
        "arm": arm,
        "all_identity_fields_exact": comparison["all_identity_fields_exact"],
        "checked_identity_fields": comparison["checked_fields"],
        "mismatched_identity_fields": comparison["mismatched_fields"],
        "required_isolation_checks": required,
    }


def _anchor_record(
    anchor: d033._AnchorState | None,
    *,
    selection: _TriggerSelection | None,
    status: str,
    checks: dict[str, object],
) -> dict[str, object]:
    record = dict(checks)
    record["status"] = status
    record["available"] = anchor is not None and selection is not None
    if selection is not None:
        record["trigger_history"] = _trigger_history(selection)
    if anchor is None or selection is None:
        return record
    record.update(
        {
            "transition": anchor.transition,
            "anchor_state_digest": d033._anchor_fingerprint(anchor),
            "current_observation": [
                anchor.current.energy,
                anchor.current.beacon.left,
                anchor.current.beacon.forward,
                anchor.current.beacon.right,
                float(anchor.current.charging_contact),
                anchor.current.thermal,
            ],
            "anchor_energy": anchor.current.energy,
            "anchor_thermal": anchor.current.thermal,
            "anchor_charging_contact": anchor.current.charging_contact,
            "anchor_mode": anchor.controller.mode.name,
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
    return record


def _reference_replay_for_seed(
    seed: int,
    accepted: dict[str, object],
) -> tuple[
    dict[str, object],
    tuple[d025.D025TransitionTrace, ...],
    tuple[d025.D025TransitionTrace, ...],
    d033._AnchorState,
    dict[str, object],
]:
    """Run exact A/B replay and reconstruct the D-032 matched first onset."""
    arm_a = d031r1._run_arm(
        seed,
        arm="LEARNED_WITH_DETRAP",
        horizon=D034_HORIZON,
        evaluator_diagnostics=True,
        seed_validator=_validate_d034_seed,
    )
    arm_b = d031r1._run_arm(
        seed,
        arm="LEARNED_NO_DETRAP",
        horizon=D034_HORIZON,
        evaluator_diagnostics=True,
        seed_validator=_validate_d034_seed,
    )
    replay: dict[str, object] = {
        "arm_a": _identity_gate(
            seed,
            "LEARNED_WITH_DETRAP",
            arm_a,
            _accepted_arm(accepted, seed, "LEARNED_WITH_DETRAP"),
        ),
        "arm_b": _identity_gate(
            seed,
            "LEARNED_NO_DETRAP",
            arm_b,
            _accepted_arm(accepted, seed, "LEARNED_NO_DETRAP"),
        ),
    }

    b_result, b_trace, _ = d033._run_capture(
        seed,
        role="B",
        horizon=D034_HORIZON,
        seed_validator=_validate_d034_seed,
    )
    b_instrumented = d032._compare_identity_fields(
        b_result, arm_b, include_private_weights=True
    )
    if not b_instrumented["all_identity_fields_exact"]:
        raise RuntimeError(f"D-034 instrumented Arm-B replay diverged for seed {seed}")
    a_result, a_trace, a_instrumentation = d033._run_capture(
        seed,
        role="A",
        horizon=D034_HORIZON,
        capture_first_delegation=True,
        seed_validator=_validate_d034_seed,
    )
    a_instrumented = d032._compare_identity_fields(
        a_result, arm_a, include_private_weights=True
    )
    if not a_instrumented["all_identity_fields_exact"]:
        raise RuntimeError(f"D-034 instrumented Arm-A replay diverged for seed {seed}")
    a_capture = a_instrumentation.capture
    if a_capture is None:
        raise RuntimeError(f"D-034 Arm-A first delegation missing for seed {seed}")
    b_at_a_result, b_at_a_trace, b_at_a_instrumentation = d033._run_capture(
        seed,
        role="B",
        horizon=D034_HORIZON,
        target_transition=a_capture.transition,
        seed_validator=_validate_d034_seed,
    )
    b_at_a_capture = b_at_a_instrumentation.capture
    if b_at_a_capture is None:
        raise RuntimeError(f"D-034 matched Arm-B reference missing for seed {seed}")
    if b_at_a_trace != b_trace:
        raise RuntimeError(f"D-034 matched Arm-B capture changed seed {seed}")
    matched_anchor, reference_checks = d033._match_anchor_a(
        seed,
        a_trace,
        a_capture,
        b_trace,
        b_at_a_capture,
        b_at_a_result,
    )
    if matched_anchor is None:
        raise RuntimeError(f"D-034 matched first-delegation reference failed: {seed}")
    reference_checks["arm_a_replay_exact"] = True
    reference_checks["arm_b_replay_exact"] = True
    reference_checks["instrumented_arm_a_replay_exact"] = True
    reference_checks["instrumented_arm_b_replay_exact"] = True
    return replay, a_trace, b_trace, matched_anchor, reference_checks


def _capture_trigger_anchor(
    seed: int,
    selection: _TriggerSelection,
    arm_b: dict[str, object],
) -> tuple[d033._AnchorState, dict[str, object]]:
    result, trace, instrumentation = d033._run_capture(
        seed,
        role="B",
        horizon=D034_HORIZON,
        target_transition=selection.transition,
        seed_validator=_validate_d034_seed,
    )
    accepted_with_private_weights = dict(arm_b)
    accepted_with_private_weights["_weights"] = d033._flatten_final_weights(arm_b)
    comparison = d032._compare_identity_fields(
        result, accepted_with_private_weights, include_private_weights=True
    )
    if not comparison["all_identity_fields_exact"]:
        raise RuntimeError(
            "D-034 trigger capture replay diverged for seed "
            f"{seed}/{selection.family}_{selection.length}"
        )
    capture = instrumentation.capture
    if capture is None:
        raise RuntimeError(
            "D-034 trigger anchor capture missing for seed "
            f"{seed}/{selection.family}_{selection.length}"
        )
    if trace[selection.transition - 1].transition_index != selection.transition:
        raise RuntimeError("D-034 trigger capture transition index diverged")
    anchor = d033._anchor_from_capture(
        seed, f"{selection.family}_{selection.length}", capture
    )
    return anchor, {
        "target_capture_replay_exact": comparison["all_identity_fields_exact"],
        "target_capture_checked_identity_fields": comparison["checked_fields"],
        "target_capture_mismatched_identity_fields": comparison["mismatched_fields"],
    }


def _set_branch_condition(
    anchor: d033._AnchorState,
    streams: RandomStreams,
    condition: str,
) -> d031r1.D031R1NoDetrapController:
    if condition not in {"DETRAP_OFF", "DETRAP_ON"}:
        raise ValueError(f"unknown D-034 branch condition: {condition}")
    controller = d033._rewire_controller_rng(anchor.controller, streams.policy)
    if not isinstance(controller, d031r1.D031R1NoDetrapController):
        raise RuntimeError(
            "D-034 anchor controller is not the accepted Arm-B controller"
        )
    if controller.mode is not d026.D026Mode.SEEK:
        raise RuntimeError("D-034 trigger anchor is not in false-contact SEEK")
    if condition == "DETRAP_ON":
        # The only intervention is the inherited eligibility probability.  The
        # controller and explorer object/state remain the cloned Arm-B objects.
        controller.seek_delegation_probability = D034_SEEK_DELEGATION_PROBABILITY
    else:
        controller.seek_delegation_probability = D034_NO_DETRAP_DELEGATION_PROBABILITY
    return controller


def _angle_difference(left: float, right: float) -> float:
    return abs((right - left + math.pi) % (2.0 * math.pi) - math.pi)


def _forward_boundary(row: d025.D025TransitionTrace) -> str | None:
    if row.action is not Action.MOVE_FORWARD:
        return None
    displacement = math.dist(
        row.telemetry.position_before, row.telemetry.position_after
    )
    if displacement <= d027.D027_BOUNDARY_TOLERANCE:
        return "FULL_STALL_FORWARD"
    return d027._classify_forward_displacement(displacement)


def _explorer_state(controller: d026.D026Controller) -> tuple[object, ...]:
    explorer = controller.explorer
    return (
        explorer._forward_actions_remaining,
        explorer._turn_action,
        explorer._turn_actions_remaining,
    )


def _propose_action(
    controller: d026.D026Controller,
    learner: d027.D027ActionConsequencePredictor,
    current: d027.D027Observation,
) -> tuple[Action, d025.D025Arbitration | None]:
    """Run the inherited B selection pipeline without overriding ON explorer actions."""
    historical = controller.act(current)
    arbitration = controller.last_arbitration
    proposed = historical
    if arbitration is not None and not arbitration.delegated:
        if current.charging_contact or controller.mode is not d026.D026Mode.SEEK:
            raise RuntimeError("D-034 arbitration occurred outside false-contact SEEK")
        predictions, read_only = d031r1._query_candidate_predictions(learner, current)
        if not read_only:
            raise RuntimeError("D-034 prediction query changed learner state")
        proposed = d031r1._choose_steering_action(
            current, predictions, arbitration.greedy_action
        )
    return proposed, arbitration


def _run_branch(
    anchor: d033._AnchorState,
    *,
    condition: str,
    full_b_trace: tuple[d025.D025TransitionTrace, ...],
    reference_a_trace: tuple[d025.D025TransitionTrace, ...] | None = None,
) -> tuple[dict[str, object], tuple[d025.D025TransitionTrace, ...]]:
    """Run one complete matched OFF or ON continuation from an Arm-B clone."""
    anchor_before = d033._anchor_fingerprint(anchor)
    environment = d029._clone_environment(anchor.environment)
    streams = copy.deepcopy(anchor.streams)
    controller = _set_branch_condition(anchor, streams, condition)
    learner = d033._learner_from_weights(anchor.learner_weights)
    current = anchor.current
    start_fingerprint = d033._state_fingerprint(
        environment, controller, streams, learner, current
    )
    expected_start = d033._state_fingerprint(
        environment,
        d033._rewire_controller_rng(anchor.controller, streams.policy),
        streams,
        learner,
        current,
    )
    if start_fingerprint != expected_start:
        raise RuntimeError("D-034 branch clone did not preserve causal start state")

    initial_explorer_state = _explorer_state(controller)
    anchor_explorer_state = _explorer_state(anchor.controller)
    initial_seek_segment_starts = controller.seek_segment_starts
    initial_explorer_calls = controller.false_contact_seek_explorer_calls
    trace: list[d025.D025TransitionTrace] = []
    update_digest = hashlib.sha256()
    arbitration_count = 0
    delegated_count = 0
    delegated_effective_count = 0
    delegated_actions: Counter[str] = Counter()
    first_delegation_latency: int | None = None
    update_count = 0
    terminated = False
    truncated = False
    stop_reason: str | None = None
    reacquisition_transition: int | None = None
    minimum_energy = current.energy
    energy_values = [current.energy]
    visible_forward_values = [current.beacon.forward]
    path_length = 0.0
    cumulative_heading_change = 0.0
    anchor_body = environment.body
    station = environment.station_center
    if anchor_body is None or station is None:
        raise RuntimeError("D-034 anchor lacks evaluator geometry")
    anchor_position = anchor_body.position
    previous_heading = anchor_body.heading
    initial_distance = math.dist(anchor_position, station)
    minimum_distance = initial_distance
    maximum_displacement = 0.0

    for local_transition in range(1, D034_BRANCH_HORIZON + 1):
        global_transition = anchor.transition + local_transition - 1
        mode_before = controller.mode
        proposed = _propose_action(controller, learner, current)
        arbitration = controller.last_arbitration
        if arbitration is not None:
            arbitration_count += 1
            if arbitration.delegated:
                delegated_count += 1
                delegated_actions[arbitration.actual_action.name] += 1
                if arbitration.actual_action is not arbitration.greedy_action:
                    delegated_effective_count += 1
                if first_delegation_latency is None:
                    first_delegation_latency = local_transition
        physical_action = proposed[0]
        observation_array, reward, terminated, truncated, info = environment.step(
            physical_action
        )
        if reward != 0.0 or info != {}:
            raise RuntimeError("D-034 branch crossed the reward/info boundary")
        telemetry = environment.last_transition
        if telemetry is None:
            raise RuntimeError("D-034 branch produced no telemetry")
        next_observation = d031r1._next_visible(observation_array)
        update = learner.observe_transition(current, physical_action, next_observation)
        update_count += 1
        if update.action is not physical_action:
            raise RuntimeError("D-034 learner update did not use executed action")
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
    action_counts = Counter(row.action.name for row in trace)
    boundary_counts = Counter(
        boundary for row in trace if (boundary := _forward_boundary(row)) is not None
    )
    actions = [row.action for row in trace]
    alternation_runs = d032._left_right_alternation_runs(actions)
    final_explorer_calls = controller.false_contact_seek_explorer_calls
    branch_explorer_calls = final_explorer_calls - initial_explorer_calls
    policy_rng_digest, environment_rng_digest = _rng_digests(streams)
    final_trace = tuple(trace)
    output: dict[str, object] = {
        "condition": condition,
        "anchor_type": anchor.anchor_type,
        "anchor_transition": anchor.transition,
        "branch_transition_count": len(final_trace),
        "reacquired_within_branch_window": reacquisition_transition is not None,
        "reacquisition_transition_from_anchor": reacquisition_transition,
        "reacquisition_latency": reacquisition_transition,
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
            "final_or_stop": current.energy,
            "at_reacquisition": (
                current.energy if reacquisition_transition is not None else None
            ),
            "change": current.energy - anchor.current.energy,
        },
        "thermal": {
            "at_anchor": anchor.current.thermal,
            "final_or_stop": current.thermal,
            "minimum": min(row.observation[5] for row in final_trace)
            if final_trace
            else anchor.current.thermal,
            "maximum": max(row.observation[5] for row in final_trace)
            if final_trace
            else anchor.current.thermal,
        },
        "path_length": path_length,
        "net_displacement_from_anchor": {
            "vector": [
                final_position[0] - anchor_position[0],
                final_position[1] - anchor_position[1],
            ],
            "magnitude": math.dist(anchor_position, final_position),
        },
        "evaluator_distance": {
            "start": initial_distance,
            "minimum": minimum_distance,
            "final": math.dist(final_position, station),
        },
        "visible_beacon_forward": {
            "start": visible_forward_values[0],
            "maximum": max(visible_forward_values),
            "final": visible_forward_values[-1],
            "change": visible_forward_values[-1] - visible_forward_values[0],
        },
        "cumulative_absolute_heading_change": cumulative_heading_change,
        "action_counts": {name: action_counts[name] for name in _ACTION_NAMES},
        "forward_boundary_counts": {
            name: boundary_counts[name] for name in d031r1.D031R1_BOUNDARY_CLASSES
        },
        "strict_alternation_run_count_after_anchor": len(alternation_runs),
        "strict_alternation_run_lengths_after_anchor": alternation_runs,
        "longest_strict_alternation_run_after_anchor": max(alternation_runs, default=0),
        "delegation": {
            "false_contact_seek_decision_count": arbitration_count,
            "delegated_decision_count": delegated_count,
            "effective_delegated_perturbation_count": delegated_effective_count,
            "delegated_action_counts": {
                name: delegated_actions[name] for name in _ACTION_NAMES
            },
            "first_delegation_latency_after_anchor": first_delegation_latency,
            "explorer_call_count": branch_explorer_calls,
            "delegation_probability": (
                D034_SEEK_DELEGATION_PROBABILITY
                if condition == "DETRAP_ON"
                else D034_NO_DETRAP_DELEGATION_PROBABILITY
            ),
            "explorer_internal_hazard": D034_EXPLORER_HAZARD,
            "one_policy_rng_draw_per_decision": True,
        },
        "executed_action_update_count": update_count,
        "executed_action_update_digest": update_digest.hexdigest(),
        "final_learner_state_digest": _digest(tuple(learner.weights)),
        "final_policy_rng_digest": policy_rng_digest,
        "final_environment_rng_digest": environment_rng_digest,
        "branch_state": {
            "initial_causal_state_digest": start_fingerprint,
            "anchor_causal_state_digest": anchor_before,
            "branch_start_exact": start_fingerprint == expected_start,
            "branch_did_not_mutate_anchor": d033._anchor_fingerprint(anchor)
            == anchor_before,
            "reward_zero_every_transition": all(
                row.reward == 0.0 for row in final_trace
            ),
            "organism_info_empty_every_transition": all(
                row.info == {} for row in final_trace
            ),
            "executed_action_only_updates": update_count == len(final_trace),
            "one_policy_rng_draw_per_false_contact_seek_decision": (
                arbitration_count
                == sum(
                    int(
                        row.mode_after is d026.D026Mode.SEEK
                        and not row.observation_before[4]
                    )
                    for row in final_trace
                )
            ),
            "no_false_contact_seek_explorer_call": branch_explorer_calls == 0
            if condition == "DETRAP_OFF"
            else True,
            "explorer_state_inherited": initial_explorer_state == anchor_explorer_state,
            "no_begin_segment_at_trigger": (
                controller.seek_segment_starts == initial_seek_segment_starts
            ),
            "no_reseed_or_new_rng_stream": streams.policy is controller.policy_rng
            and streams.policy is controller.explorer.policy_rng,
        },
        "seek_segment_starts_at_anchor": initial_seek_segment_starts,
        "seek_segment_starts_final": controller.seek_segment_starts,
        "reference_arm_a_trace_exact": (
            final_trace
            == d033._expected_baseline_trace(reference_a_trace, anchor.transition)
            if (
                condition == "DETRAP_ON"
                and anchor.anchor_type == _ANCHOR_REFERENCE
                and reference_a_trace is not None
            )
            else None
        ),
        "off_arm_b_continuation_exact": (
            final_trace
            == d033._expected_baseline_trace(full_b_trace, anchor.transition)
            if condition == "DETRAP_OFF"
            else None
        ),
    }
    return output, final_trace


def _branch_identity(output: dict[str, object]) -> dict[str, object]:
    return {
        key: value
        for key, value in output.items()
        if key not in {"branch_order_invariant"}
    }


def _paired_sign(value: float | None) -> str | None:
    if value is None:
        return None
    return "on_lower" if value < 0.0 else "equal" if value == 0.0 else "on_higher"


def _paired_branches(
    seed: int,
    anchor_record: dict[str, object],
    off: dict[str, object],
    on: dict[str, object],
) -> dict[str, object]:
    off_reacquired = bool(off["reacquired_within_branch_window"])
    on_reacquired = bool(on["reacquired_within_branch_window"])
    off_latency = cast(float | None, off["reacquisition_latency"])
    on_latency = cast(float | None, on["reacquisition_latency"])
    off_energy = cast(
        float | None, cast(dict[str, object], off["energy"])["at_reacquisition"]
    )
    on_energy = cast(
        float | None, cast(dict[str, object], on["energy"])["at_reacquisition"]
    )
    off_path = cast(float, off["path_length"])
    on_path = cast(float, on["path_length"])
    off_distance = cast(
        float, cast(dict[str, object], off["evaluator_distance"])["final"]
    )
    on_distance = cast(
        float, cast(dict[str, object], on["evaluator_distance"])["final"]
    )
    return {
        "seed": seed,
        "anchor_transition": anchor_record.get("transition"),
        "on_reacquired": on_reacquired,
        "off_reacquired": off_reacquired,
        "reacquisition_sign": (
            "on_only"
            if on_reacquired and not off_reacquired
            else "off_only"
            if off_reacquired and not on_reacquired
            else "both"
            if on_reacquired and off_reacquired
            else "neither"
        ),
        "on_minus_off_latency": (
            on_latency - off_latency
            if on_latency is not None and off_latency is not None
            else None
        ),
        "latency_sign": _paired_sign(
            on_latency - off_latency
            if on_latency is not None and off_latency is not None
            else None
        ),
        "on_minus_off_energy_at_reacquisition": (
            on_energy - off_energy
            if on_energy is not None and off_energy is not None
            else None
        ),
        "energy_sign": _paired_sign(
            on_energy - off_energy
            if on_energy is not None and off_energy is not None
            else None
        ),
        "on_minus_off_path_length": on_path - off_path,
        "path_length_sign": _paired_sign(on_path - off_path),
        "on_minus_off_final_evaluator_distance": on_distance - off_distance,
        "final_distance_sign": _paired_sign(on_distance - off_distance),
    }


def _run_branch_pair(
    anchor: d033._AnchorState,
    *,
    full_b_trace: tuple[d025.D025TransitionTrace, ...],
    reference_a_trace: tuple[d025.D025TransitionTrace, ...] | None,
) -> tuple[dict[str, object], dict[str, object], bool]:
    off, off_trace = _run_branch(
        anchor,
        condition="DETRAP_OFF",
        full_b_trace=full_b_trace,
        reference_a_trace=reference_a_trace,
    )
    on, on_trace = _run_branch(
        anchor,
        condition="DETRAP_ON",
        full_b_trace=full_b_trace,
        reference_a_trace=reference_a_trace,
    )
    if not bool(off["off_arm_b_continuation_exact"]):
        raise RuntimeError(f"D-034 OFF continuation diverged at {anchor.anchor_type}")
    if anchor.anchor_type == _ANCHOR_REFERENCE and not bool(
        on["reference_arm_a_trace_exact"]
    ):
        raise RuntimeError("D-034 matched-reference ON continuation failed")

    reverse_on, reverse_on_trace = _run_branch(
        anchor,
        condition="DETRAP_ON",
        full_b_trace=full_b_trace,
        reference_a_trace=reference_a_trace,
    )
    reverse_off, reverse_off_trace = _run_branch(
        anchor,
        condition="DETRAP_OFF",
        full_b_trace=full_b_trace,
        reference_a_trace=reference_a_trace,
    )
    order_invariant = (
        off_trace == reverse_off_trace
        and on_trace == reverse_on_trace
        and _branch_identity(off) == _branch_identity(reverse_off)
        and _branch_identity(on) == _branch_identity(reverse_on)
    )
    if not order_invariant:
        raise RuntimeError(
            f"D-034 branch-order invariance failed at {anchor.anchor_type}"
        )
    off["branch_order_invariant"] = order_invariant
    on["branch_order_invariant"] = order_invariant
    return off, on, order_invariant


def _seed_anchor_key(family: str, length: int) -> str:
    return f"{family}_{length}"


def _seed_record(
    seed: int,
    accepted: dict[str, object],
) -> dict[str, object]:
    replay, a_trace, b_trace, reference_anchor, reference_checks = (
        _reference_replay_for_seed(seed, accepted)
    )
    reference_pair_off, reference_pair_on, reference_order = _run_branch_pair(
        reference_anchor,
        full_b_trace=b_trace,
        reference_a_trace=a_trace,
    )
    reference_record: dict[str, object] = {
        "available": True,
        "anchor_type": _ANCHOR_REFERENCE,
        "transition": reference_anchor.transition,
        "anchor_state_digest": d033._anchor_fingerprint(reference_anchor),
        "pre_treatment_reference_checks": reference_checks,
        "off": reference_pair_off,
        "on": reference_pair_on,
        "branch_order_invariant": reference_order,
        "on_reproduces_accepted_arm_a": reference_pair_on[
            "reference_arm_a_trace_exact"
        ],
        "off_reproduces_accepted_arm_b": reference_pair_off[
            "off_arm_b_continuation_exact"
        ],
    }

    arm_b_accepted = _accepted_arm(accepted, seed, "LEARNED_NO_DETRAP")
    anchors: dict[str, dict[str, object]] = {}
    for family in D034_TRIGGER_FAMILIES:
        for length in D034_LENGTHS:
            key = _seed_anchor_key(family, length)
            selection = _find_trigger(b_trace, family, length)
            if selection is None:
                anchors[key] = {
                    "status": "anchor_unavailable",
                    "available": False,
                    "family": family,
                    "length": length,
                    "reason": (
                        "no first closure-valid history window with a following "
                        "pre-action state before lifetime end"
                    ),
                    "uses_only_executed_actions_and_six_channel_observations": True,
                    "hidden_geometry_or_future_outcome_used": False,
                }
                continue
            anchor, capture_checks = _capture_trigger_anchor(
                seed, selection, arm_b_accepted
            )
            record = _anchor_record(
                anchor,
                selection=selection,
                status="anchor_available",
                checks=capture_checks,
            )
            off, on, order_invariant = _run_branch_pair(
                anchor,
                full_b_trace=b_trace,
                reference_a_trace=None,
            )
            record.update(
                {
                    "off": off,
                    "on": on,
                    "branch_order_invariant": order_invariant,
                    "paired_on_minus_off": _paired_branches(seed, record, off, on),
                }
            )
            anchors[key] = record
    return {
        "seed": seed,
        "accepted_replay": replay,
        "reference": reference_record,
        "anchors": anchors,
    }


def _pooled_summary(
    seed_records: Sequence[dict[str, object]], family: str, length: int
) -> dict[str, object]:
    key = _seed_anchor_key(family, length)
    available: list[tuple[int, dict[str, object]]] = []
    unavailable: list[int] = []
    for seed_record in seed_records:
        anchor = cast(
            dict[str, object], cast(dict[str, object], seed_record["anchors"])[key]
        )
        if bool(anchor.get("available")):
            available.append((cast(int, seed_record["seed"]), anchor))
        else:
            unavailable.append(cast(int, seed_record["seed"]))
    off_rows = [cast(dict[str, object], row["off"]) for _, row in available]
    on_rows = [cast(dict[str, object], row["on"]) for _, row in available]
    paired = [
        cast(dict[str, object], row["paired_on_minus_off"]) for _, row in available
    ]

    def values(rows: Sequence[dict[str, object]], path: str) -> list[float]:
        return [cast(float, row[path]) for row in rows if row[path] is not None]

    def nested_values(
        rows: Sequence[dict[str, object]], outer: str, inner: str
    ) -> list[float]:
        return [
            cast(float, cast(dict[str, object], row[outer])[inner])
            for row in rows
            if cast(dict[str, object], row[outer])[inner] is not None
        ]

    def sign_counts(field: str) -> dict[str, int]:
        return dict(
            Counter(cast(str, row[field]) for row in paired if row[field] is not None)
        )

    return {
        "family": family,
        "length": length,
        "available_seed_count": len(available),
        "available_seeds": [seed for seed, _ in available],
        "unavailable_seeds": unavailable,
        "off_reacquisition_count": sum(
            int(cast(bool, row["reacquired_within_branch_window"])) for row in off_rows
        ),
        "on_reacquisition_count": sum(
            int(cast(bool, row["reacquired_within_branch_window"])) for row in on_rows
        ),
        "off_reacquisition_latency": _number_summary(
            values(off_rows, "reacquisition_latency")
        ),
        "on_reacquisition_latency": _number_summary(
            values(on_rows, "reacquisition_latency")
        ),
        "off_energy_at_reacquisition": _number_summary(
            nested_values(off_rows, "energy", "at_reacquisition")
        ),
        "on_energy_at_reacquisition": _number_summary(
            nested_values(on_rows, "energy", "at_reacquisition")
        ),
        "off_path_length": _number_summary(values(off_rows, "path_length")),
        "on_path_length": _number_summary(values(on_rows, "path_length")),
        "off_final_evaluator_distance": _number_summary(
            nested_values(off_rows, "evaluator_distance", "final")
        ),
        "on_final_evaluator_distance": _number_summary(
            nested_values(on_rows, "evaluator_distance", "final")
        ),
        "on_delegated_decision_count": sum(
            cast(
                int,
                cast(dict[str, object], row["delegation"])["delegated_decision_count"],
            )
            for row in on_rows
        ),
        "on_effective_delegated_perturbation_count": sum(
            cast(
                int,
                cast(dict[str, object], row["delegation"])[
                    "effective_delegated_perturbation_count"
                ],
            )
            for row in on_rows
        ),
        "on_explorer_call_count": sum(
            cast(
                int,
                cast(dict[str, object], row["delegation"])["explorer_call_count"],
            )
            for row in on_rows
        ),
        "paired_on_minus_off": paired,
        "paired_sign_counts": {
            "reacquisition_sign": sign_counts("reacquisition_sign"),
            "latency_sign": sign_counts("latency_sign"),
            "energy_sign": sign_counts("energy_sign"),
            "path_length_sign": sign_counts("path_length_sign"),
            "final_distance_sign": sign_counts("final_distance_sign"),
        },
        "outlier_handling": {
            "discarded_seed_count": 0,
            "statement": (
                "All available and unavailable anchors are retained; no outliers "
                "are discarded."
            ),
        },
    }


def _interpretation(seed_records: Sequence[dict[str, object]]) -> dict[str, object]:
    pooled = {
        _seed_anchor_key(family, length): _pooled_summary(seed_records, family, length)
        for family in D034_TRIGGER_FAMILIES
        for length in D034_LENGTHS
    }

    def on_exceeds_off(key: str) -> bool:
        row = pooled[key]
        return cast(int, row["on_reacquisition_count"]) > cast(
            int, row["off_reacquisition_count"]
        )

    alt_any = any(
        on_exceeds_off(_seed_anchor_key("ALT", length)) for length in D034_LENGTHS
    )
    progress_any = any(
        on_exceeds_off(_seed_anchor_key("NO_FORWARD_PROGRESS", length))
        for length in D034_LENGTHS
    )
    no_delayed_recovery = not (alt_any or progress_any)
    reference_passed = all(
        bool(
            cast(dict[str, object], record["reference"])["on_reproduces_accepted_arm_a"]
        )
        and bool(
            cast(dict[str, object], record["reference"])[
                "off_reproduces_accepted_arm_b"
            ]
        )
        for record in seed_records
    )
    timing_pattern = any(
        on_exceeds_off(_seed_anchor_key("ALT", earlier))
        and not on_exceeds_off(_seed_anchor_key("ALT", later))
        for earlier, later in ((4, 8), (8, 16))
    ) or any(
        on_exceeds_off(_seed_anchor_key("NO_FORWARD_PROGRESS", earlier))
        and not on_exceeds_off(_seed_anchor_key("NO_FORWARD_PROGRESS", later))
        for earlier, later in ((4, 8), (8, 16))
    )
    return {
        "lane": "Development",
        "confirmatory_claim": False,
        "reference_equivalence_passed": reference_passed,
        "categories": {
            "broad_delayed_recruitment_sufficiency": {
                "rule": (
                    "At least one frozen trigger family/length has more ON than "
                    "OFF reacquisitions; no universal threshold is applied."
                ),
                "observed_pattern": alt_any or progress_any,
            },
            "action_pattern_specific_sufficiency": {
                "rule": (
                    "ALT has an ON-over-OFF reacquisition pattern while "
                    "NO_FORWARD_PROGRESS does not."
                ),
                "observed_pattern": alt_any and not progress_any,
            },
            "visible_progress_sufficiency": {
                "rule": (
                    "At least one NO_FORWARD_PROGRESS length has more ON than "
                    "OFF reacquisitions."
                ),
                "observed_pattern": progress_any,
            },
            "timing_sensitivity": {
                "rule": (
                    "An earlier frozen length has an ON-over-OFF pattern while a "
                    "later frozen length in the same family does not."
                ),
                "observed_pattern": timing_pattern,
            },
            "no_delayed_trigger_sufficient": {
                "rule": (
                    "No frozen delayed trigger has more ON than OFF reacquisitions "
                    "while the matched reference passes."
                ),
                "observed_pattern": no_delayed_recovery and reference_passed,
            },
            "reference_equivalence_failure": {
                "rule": (
                    "Any failure of exact accepted replay or matched-reference "
                    "branch identity invalidates delayed-trigger interpretation."
                ),
                "observed_pattern": not reference_passed,
            },
        },
        "observed_pooled_keys": sorted(pooled),
        "no_protocol_tuning_from_outputs": True,
        "organism_trigger_not_demonstrated": True,
        "descriptive_observation_not_causal_learning_claim": True,
    }


def run_d034_audit(
    seeds: Sequence[int] = D034_DEFAULT_DEVELOPMENT_SEEDS,
    *,
    horizon: int = D034_HORIZON,
    executed_commit_sha: str | None = None,
) -> dict[str, object]:
    """Run the complete frozen D-034 protocol on the reused support."""
    validated = _validate_d034_development_seeds(seeds)
    if horizon != D034_HORIZON:
        raise ValueError("D-034 requires the frozen 70,000-transition horizon")
    executed_sha = _validate_executed_commit_sha(executed_commit_sha)
    if executed_sha is None:
        raise ValueError(
            "D-034 official output requires the exact clean executable protocol SHA"
        )
    accepted = _accepted_artifact()
    records = [_seed_record(seed, accepted) for seed in validated]
    return {
        "schema_version": 1,
        "experiment": "D-034",
        "title": "Closure-valid history-triggered de-trap recruitment audit",
        "authoritative_base_sha": D034_AUTHORITATIVE_BASE_SHA,
        "base_tree_sha": D034_BASE_TREE_SHA,
        "implementation_probe_sha": executed_sha,
        "protocol_only_freeze_sha": executed_sha,
        "development_seeds": list(validated),
        "horizon": D034_HORIZON,
        "branch_horizon": D034_BRANCH_HORIZON,
        "timestep_seconds": D020PhysicalConfig().dt_seconds,
        "simulated_duration_seconds": D034_HORIZON * D020PhysicalConfig().dt_seconds,
        "support": {
            "source": "accepted D-031R1/D-032/D-033 Development support",
            "accepted_artifact": D034_ACCEPTED_D031R1_ARTIFACT,
            "accepted_artifact_sha256": _accepted_artifact_sha256(),
            "fresh_seed_block_allocated": False,
            "fresh_seed_block_inspected": False,
        },
        "freeze": {
            "history_lengths": list(D034_LENGTHS),
            "trigger_families": list(D034_TRIGGER_FAMILIES),
            "underlying_arm": "LEARNED_NO_DETRAP",
            "branches": ["DETRAP_OFF", "DETRAP_ON"],
            "on_delegation_probability": D034_SEEK_DELEGATION_PROBABILITY,
            "off_delegation_probability": D034_NO_DETRAP_DELEGATION_PROBABILITY,
            "explorer_internal_hazard": D034_EXPLORER_HAZARD,
            "no_begin_segment_at_trigger": True,
            "no_reseed_or_new_rng_stream": True,
            "stop_rules": [
                "dual-contact reacquisition",
                "inherited energy or thermal termination",
                "inherited episode truncation",
                "4096 branch transitions",
            ],
            "reward": 0.0,
            "organism_info": {},
            "learner_update": (
                "exactly once from executed action and actual next six-channel "
                "observation"
            ),
            "no_organism_boundary_change": True,
        },
        "causal_order": [
            "replay accepted Arm A and Arm B",
            "reconstruct D-032 matched first-delegation reference",
            "detect first frozen closure-valid Arm-B history anchor post-hoc",
            "clone complete Arm-B causal continuation state",
            "change only false-contact SEEK delegation eligibility for ON",
            "execute ordinary real transitions with unchanged D-027 update",
            "retain evaluator-only metrics and paired contrasts",
        ],
        "organism_boundary": {
            "channels": list(d027.D027_CHANNELS),
            "actions": [action.name for action in Action],
            "reward": 0.0,
            "info": {},
            "evaluator_state_reaches_controller_or_learner": False,
            "organism_history_or_trigger_state_added": False,
            "new_sensor_or_physics_added": False,
            "larger_learner_or_world_model_added": False,
        },
        "replay_gate": {
            "all_seeds_exact_arm_a_replay": True,
            "all_seeds_exact_arm_b_replay": True,
            "checked_identity_fields": list(_CAUSAL_IDENTITY_FIELDS) + ["_weights"],
            "matched_first_delegation_reference_required": True,
        },
        "results": records,
        "pooled": {
            _seed_anchor_key(family, length): _pooled_summary(records, family, length)
            for family in D034_TRIGGER_FAMILIES
            for length in D034_LENGTHS
        },
        "interpretation": _interpretation(records),
    }


def write_d034_json(path: Path, executed_commit_sha: str | None = None) -> Path:
    path.write_text(
        json.dumps(
            run_d034_audit(executed_commit_sha=executed_commit_sha),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the D-034 history audit.")
    parser.add_argument("--executed-commit-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    write_d034_json(args.output, args.executed_commit_sha)
    print(f"D-034 result written to {args.output}")


if __name__ == "__main__":
    main()
