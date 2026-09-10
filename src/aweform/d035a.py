"""D-035A evaluator-only turn-granularity attribution audit.

The accepted D-031R1 Arm-B organism is replayed unchanged.  From two
evaluator-selected pre-action Arm-B anchors, this module clones the complete
causal continuation state and changes only the physical turn angle in an
isolated counterfactual environment.  The action identities, controller,
learner, observations, reward, information boundary, RNG timing, and all
canonical D-020 semantics remain unchanged.
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
from dataclasses import dataclass, fields, replace
from pathlib import Path
from typing import Final, cast

from . import d024, d025, d026, d027, d029, d031r1, d032, d033
from .d020 import D020PhysicalConfig, D020TransitionTelemetry
from .env import Action
from .exp003_seed_policy import validate_exp003_development_seeds
from .rng import RandomStreams

D035A_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = tuple(
    range(18468, 18488)
)
D035A_HORIZON: Final[int] = 70_000
D035A_BRANCH_HORIZON: Final[int] = 4_096
D035A_FIRST_ANCHOR: Final[str] = "FIRST_FALSE_CONTACT_SEEK"
D035A_ALT8_ANCHOR: Final[str] = "ALT8_ESTABLISHED"
D035A_ANCHORS: Final[tuple[str, ...]] = (
    D035A_FIRST_ANCHOR,
    D035A_ALT8_ANCHOR,
)
D035A_CONDITIONS: Final[tuple[str, ...]] = (
    "TURN_45_CONTROL",
    "TURN_5",
    "TURN_2",
    "TURN_1",
)
D035A_TURN_45_CONTROL_ANGLE: Final[float] = math.pi / 4.0
D035A_TURN_5_ANGLE: Final[float] = math.pi / 36.0
D035A_TURN_2_ANGLE: Final[float] = math.pi / 90.0
D035A_TURN_1_ANGLE: Final[float] = math.pi / 180.0
D035A_TURN_ANGLES: Final[dict[str, float]] = {
    "TURN_45_CONTROL": D035A_TURN_45_CONTROL_ANGLE,
    "TURN_5": D035A_TURN_5_ANGLE,
    "TURN_2": D035A_TURN_2_ANGLE,
    "TURN_1": D035A_TURN_1_ANGLE,
}
D035A_TURN_ANGLE_EXPRESSIONS: Final[dict[str, str]] = {
    "TURN_45_CONTROL": "math.pi / 4.0",
    "TURN_5": "math.pi / 36.0",
    "TURN_2": "math.pi / 90.0",
    "TURN_1": "math.pi / 180.0",
}
D035A_AUTHORITATIVE_BASE_SHA: Final[str] = (
    "d40681d25cd4cc67e359004ffcd63819e40b42a4"
)
D035A_BASE_TREE_SHA: Final[str] = "50510ba772a1d53960f7f5870feb6b7b510cacf4"
D035A_ACCEPTED_D031R1_ARTIFACT: Final[str] = d032.D032_ACCEPTED_D031R1_ARTIFACT
D035A_ACCEPTED_D033_ARTIFACT: Final[str] = (
    "development/D-033-short-horizon-sequence-sufficiency-audit.json"
)
D035A_STEERING_ACTIONS: Final[tuple[Action, ...]] = d031r1.D031R1_STEERING_ACTIONS
D035A_CHANNELS: Final[tuple[str, ...]] = d027.D027_CHANNELS
D035A_OUTPUTS: Final[tuple[str, ...]] = d027.D027_OUTPUTS

_ACTION_NAMES: Final[tuple[str, ...]] = tuple(action.name for action in Action)
_TURN_ACTIONS: Final[frozenset[Action]] = frozenset(
    (Action.TURN_LEFT, Action.TURN_RIGHT)
)
_CAUSAL_IDENTITY_FIELDS: Final[tuple[str, ...]] = d032._CAUSAL_IDENTITY_FIELDS
_WINDOWS: Final[tuple[tuple[str, int, int], ...]] = (
    ("1..16", 1, 16),
    ("17..64", 17, 64),
    ("65..256", 65, 256),
    ("257..1024", 257, 1024),
    ("1025..4096", 1025, 4096),
)


def _validate_d035a_development_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    validated = validate_exp003_development_seeds(seeds)
    if validated != D035A_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-035A requires exactly the reused development seeds "
            f"{D035A_DEFAULT_DEVELOPMENT_SEEDS}; got {validated}"
        )
    return validated


def _validate_d035a_seed(seed: int) -> None:
    validated = validate_exp003_development_seeds((seed,))
    if validated[0] not in D035A_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-035A may execute only the reused development seeds "
            f"{D035A_DEFAULT_DEVELOPMENT_SEEDS}; got {validated[0]}"
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


def _empty_action_counts() -> dict[str, int]:
    return {name: 0 for name in _ACTION_NAMES}


def _angle_difference(left: float, right: float) -> float:
    return abs((right - left + math.pi) % (2.0 * math.pi) - math.pi)


def _forward_boundary(telemetry: D020TransitionTelemetry, action: Action) -> str | None:
    if action is not Action.MOVE_FORWARD:
        return None
    displacement = math.dist(telemetry.position_before, telemetry.position_after)
    if displacement <= d027.D027_BOUNDARY_TOLERANCE:
        return "FULL_STALL_FORWARD"
    return d027._classify_forward_displacement(displacement)


def _is_false_contact_seek_decision(row: d025.D025TransitionTrace) -> bool:
    """Use only the pre-action Arm-B SEEK/contact state for this metric."""
    return (
        row.mode_before is d026.D026Mode.SEEK
        and row.observation_before[4] == 0.0
    )


def _strict_alternation(actions: Sequence[Action]) -> bool:
    return len(actions) >= 2 and all(
        left in _TURN_ACTIONS and right in _TURN_ACTIONS and left is not right
        for left, right in zip(actions, actions[1:], strict=False)
    )


def _alternation_run_lengths(actions: Sequence[Action]) -> list[int]:
    return d032._left_right_alternation_runs(list(actions))


def _geometry_snapshot(
    position: tuple[float, float], heading: float, station: tuple[float, float]
) -> dict[str, object]:
    plus_error, minus_error = d024.dual_contact_pair_errors(
        position, heading, station
    )
    return {
        "position": list(position),
        "heading": heading,
        "distance_to_station": math.dist(position, station),
        "rear_plus_pair_error": plus_error,
        "rear_minus_pair_error": minus_error,
    }


def _config_diff_fields(
    reference: D020PhysicalConfig, candidate: D020PhysicalConfig
) -> tuple[str, ...]:
    return tuple(
        field.name
        for field in fields(D020PhysicalConfig)
        if getattr(reference, field.name) != getattr(candidate, field.name)
    )


@dataclass(frozen=True, slots=True)
class _PredictionRecord:
    local_transition: int
    action: Action
    prediction: tuple[float, ...]
    observed: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class _TruthRecord:
    action: Action
    truth_argmax: tuple[Action, ...]
    truth_scores: tuple[float, ...]
    predicted_forward_delta: float
    actual_forward_delta: float
    learned_score_margin: float
    truth_score_margin: float


@dataclass(slots=True)
class _BranchRun:
    output: dict[str, object]
    trace: tuple[d025.D025TransitionTrace, ...]
    prediction_records: tuple[_PredictionRecord, ...]
    truth_records: tuple[_TruthRecord, ...]


def _scalar_error_summary(values: Sequence[float]) -> dict[str, object]:
    return {
        **_number_summary(values),
        "absolute_error_sum": sum(values),
        "mae": statistics.fmean(values) if values else None,
    }


def _prediction_metrics(
    records: Sequence[_PredictionRecord],
) -> dict[str, object]:
    def all_six(items: Sequence[_PredictionRecord]) -> dict[str, object]:
        by_output = {
            output: _scalar_error_summary(
                [
                    abs(item.observed[index] - item.prediction[index])
                    for item in items
                ]
            )
            for index, output in enumerate(D035A_OUTPUTS)
        }
        errors = [
            abs(item.observed[index] - item.prediction[index])
            for item in items
            for index in range(len(D035A_OUTPUTS))
        ]
        return {
            "transition_count": len(items),
            "scalar_count": len(errors),
            "mae": statistics.fmean(errors) if errors else None,
            "absolute_error_sum": sum(errors),
            "mae_by_output": by_output,
        }

    turn_items = [item for item in records if item.action in _TURN_ACTIONS]
    left_items = [item for item in records if item.action is Action.TURN_LEFT]
    right_items = [item for item in records if item.action is Action.TURN_RIGHT]
    forward_index = D035A_OUTPUTS.index("delta_beacon_forward")

    def forward(items: Sequence[_PredictionRecord]) -> dict[str, object]:
        return _scalar_error_summary(
            [
                abs(item.observed[forward_index] - item.prediction[forward_index])
                for item in items
            ]
        )

    return {
        "executed_transition_count": len(records),
        "all_six_outputs": all_six(records),
        "turn_actions": all_six(turn_items),
        "delta_beacon_forward": {
            "all_executed_actions": forward(records),
            "TURN_LEFT": forward(left_items),
            "TURN_RIGHT": forward(right_items),
        },
    }


def _window_prediction_metrics(
    records: Sequence[_PredictionRecord], branch_length: int
) -> dict[str, object]:
    fixed: dict[str, object] = {}
    for name, lower, upper in _WINDOWS:
        fixed[name] = _prediction_metrics(
            [
                item
                for item in records
                if lower <= item.local_transition <= upper
            ]
        )
    midpoint = (branch_length + 1) // 2
    return {
        "fixed_post_anchor_windows": fixed,
        "branch_halves": {
            "first_half": _prediction_metrics(
                [item for item in records if item.local_transition <= midpoint]
            ),
            "second_half": _prediction_metrics(
                [item for item in records if item.local_transition > midpoint]
            ),
        },
        "half_split_definition": "first 1..ceil(branch_transitions/2), then remainder",
    }


def _truth_metrics(records: Sequence[_TruthRecord]) -> dict[str, object]:
    forward_values = [record.actual_forward_delta for record in records]
    predicted_values = [record.predicted_forward_delta for record in records]
    margins = [record.truth_score_margin for record in records]
    learned_margins = [record.learned_score_margin for record in records]
    by_action: dict[str, dict[str, object]] = {}
    for action in D035A_STEERING_ACTIONS:
        selected = [record for record in records if record.action is action]
        actual = [record.actual_forward_delta for record in selected]
        predicted = [record.predicted_forward_delta for record in selected]
        by_action[action.name] = {
            "sample_count": len(selected),
            "actual_forward_delta": _number_summary(actual),
            "predicted_forward_delta": _number_summary(predicted),
            "actual_minus_predicted_forward_delta": _number_summary(
                [a - p for a, p in zip(actual, predicted, strict=True)]
            ),
        }
    optimal = sum(
        int(record.action in record.truth_argmax) for record in records
    )
    return {
        "decision_count": len(records),
        "causal_action_in_one_step_truth_argmax_count": optimal,
        "causal_action_in_one_step_truth_argmax_fraction": (
            optimal / len(records) if records else None
        ),
        "truth_score_margin": _number_summary(margins),
        "learned_score_margin": _number_summary(learned_margins),
        "actual_forward_delta": _number_summary(forward_values),
        "predicted_forward_delta": _number_summary(predicted_values),
        "actual_minus_predicted_forward_delta": _number_summary(
            [a - p for a, p in zip(forward_values, predicted_values, strict=True)]
        ),
        "by_causal_action": by_action,
    }


def _accepted_artifact(path: str) -> dict[str, object]:
    root = Path(__file__).resolve().parents[2]
    artifact_path = root / path
    if not artifact_path.is_file():
        raise RuntimeError(f"accepted artifact is missing: {artifact_path}")
    return cast(
        dict[str, object], json.loads(artifact_path.read_text(encoding="utf-8"))
    )


def _artifact_sha256(path: str) -> str:
    root = Path(__file__).resolve().parents[2]
    return hashlib.sha256((root / path).read_bytes()).hexdigest()


def _accepted_arm(
    artifact: dict[str, object], seed: int, arm: str
) -> dict[str, object]:
    return d033._accepted_arm(artifact, seed, arm)


def _identity_gate(
    seed: int,
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
        "zero_false_contact_seek_explorer_calls": isolation[
            "no_false_contact_seek_explorer_call"
        ],
        "one_legacy_arbitration_draw_per_false_contact_seek_decision": isolation[
            "one_legacy_arbitration_draw_per_false_contact_seek_decision"
        ],
        "real_updates_executed_action_only": isolation[
            "real_updates_executed_action_only"
        ],
    }
    if not all(cast(bool, value) for value in required.values()):
        raise RuntimeError(f"D-035A accepted Arm-B replay gate failed for seed {seed}")
    return {
        "seed": seed,
        "arm": "LEARNED_NO_DETRAP",
        "all_identity_fields_exact": comparison["all_identity_fields_exact"],
        "checked_identity_fields": comparison["checked_fields"],
        "mismatched_identity_fields": comparison["mismatched_fields"],
        "required_isolation_checks": required,
    }


def _anchor_record(
    anchor: d033._AnchorState | None,
    checks: dict[str, object],
    *,
    unavailable_reason: str | None = None,
) -> dict[str, object]:
    record = dict(checks)
    record["available"] = anchor is not None
    if unavailable_reason is not None:
        record["unavailable_reason"] = unavailable_reason
    if anchor is None:
        return record
    body = anchor.environment.body
    station = anchor.environment.station_center
    if body is None or station is None:
        raise RuntimeError("D-035A anchor lacks evaluator geometry")
    record.update(
        {
            "anchor_type": anchor.anchor_type,
            "seed": anchor.seed,
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
            "anchor_evaluator_position": list(body.position),
            "anchor_evaluator_heading": body.heading,
            "anchor_pair_errors": list(
                d024.dual_contact_pair_errors(
                    body.position, body.heading, station
                )
            ),
            "anchor_policy_rng_digest": _rng_digests(anchor.streams)[0],
            "anchor_environment_rng_digest": _rng_digests(anchor.streams)[1],
            "anchor_learner_state_digest": _digest(anchor.learner_weights),
            "anchor_learner_weight_count": len(anchor.learner_weights),
            "anchor_update_prefix_digest": anchor.update_prefix_digest,
            "b_proposed_action": anchor.proposed_action.name,
            "anchor_controller_state_digest": _digest(
                d029._controller_state(anchor.controller)
            ),
            "anchor_environment_state_digest": _digest(
                d029._environment_state(anchor.environment)
            ),
        }
    )
    return record


def _first_false_contact_seek_transition(
    trace: Sequence[d025.D025TransitionTrace],
) -> int | None:
    for row in trace:
        if _is_false_contact_seek_decision(row):
            return row.transition_index
    return None


def _anchor_projection(record: dict[str, object]) -> dict[str, object]:
    return {
        key: record.get(key)
        for key in (
            "available",
            "transition",
            "anchor_state_digest",
            "current_observation",
            "anchor_energy",
            "anchor_evaluator_position",
            "anchor_policy_rng_digest",
            "anchor_environment_rng_digest",
            "anchor_learner_state_digest",
            "anchor_update_prefix_digest",
            "b_proposed_action",
            "alternation_eighth_transition",
        )
    }


def _capture_anchor(
    seed: int,
    anchor_type: str,
    transition: int,
    arm_b_result: dict[str, object],
) -> tuple[d033._AnchorState, dict[str, object]]:
    captured_result, trace, instrumentation = d033._run_capture(
        seed,
        role="B",
        horizon=D035A_HORIZON,
        target_transition=transition,
        seed_validator=_validate_d035a_seed,
    )
    comparison = d032._compare_identity_fields(
        captured_result,
        arm_b_result,
        include_private_weights=True,
    )
    if not comparison["all_identity_fields_exact"]:
        raise RuntimeError(
            "D-035A anchor capture replay diverged for "
            f"{seed}/{anchor_type}: {comparison['mismatched_fields']}"
        )
    capture = instrumentation.capture
    if capture is None or capture.proposed_action is None:
        raise RuntimeError(f"D-035A anchor capture missing for {seed}/{anchor_type}")
    if transition < 1 or transition > len(trace):
        raise RuntimeError("D-035A anchor transition is outside the replay trace")
    row = trace[transition - 1]
    current_values = (
        capture.current.energy,
        capture.current.beacon.left,
        capture.current.beacon.forward,
        capture.current.beacon.right,
        float(capture.current.charging_contact),
        capture.current.thermal,
    )
    if current_values != row.observation_before:
        raise RuntimeError(
            f"D-035A anchor observation mismatch for {seed}/{anchor_type}"
        )
    anchor = d033._anchor_from_capture(seed, anchor_type, capture)
    checks = {
        "status": anchor_type,
        "target_capture_replay_exact": comparison["all_identity_fields_exact"],
        "target_capture_checked_identity_fields": comparison["checked_fields"],
        "target_capture_mismatched_identity_fields": comparison["mismatched_fields"],
        "pre_action_false_contact": not anchor.current.charging_contact,
        "pre_action_seek_mode": anchor.controller.mode is d026.D026Mode.SEEK,
        "complete_learner_state_captured": len(anchor.learner_weights)
        == d027.D027_PLASTIC_STATE_DIMENSION,
    }
    if not (
        cast(bool, checks["target_capture_replay_exact"])
        and cast(bool, checks["pre_action_false_contact"])
        and cast(bool, checks["pre_action_seek_mode"])
        and cast(bool, checks["complete_learner_state_captured"])
    ):
        raise RuntimeError(
            f"D-035A anchor state checks failed for {seed}/{anchor_type}"
        )
    return anchor, checks


def _replay_and_anchors(
    seed: int,
    accepted_d031r1: dict[str, object],
    accepted_d033: dict[str, object],
) -> tuple[
    dict[str, object],
    tuple[d025.D025TransitionTrace, ...],
    dict[str, d033._AnchorState | None],
    dict[str, dict[str, object]],
]:
    arm_b_trace: list[d025.D025TransitionTrace] = []
    arm_b_result = d031r1._run_arm(
        seed,
        arm="LEARNED_NO_DETRAP",
        horizon=D035A_HORIZON,
        evaluator_diagnostics=True,
        trace_sink=arm_b_trace,
        seed_validator=_validate_d035a_seed,
    )
    replay_gate = _identity_gate(
        seed,
        arm_b_result,
        _accepted_arm(accepted_d031r1, seed, "LEARNED_NO_DETRAP"),
    )
    checks: dict[str, dict[str, object]] = {}
    anchors: dict[str, d033._AnchorState | None] = {}

    first_transition = _first_false_contact_seek_transition(arm_b_trace)
    if first_transition is None:
        if cast(dict[str, object], arm_b_result["seek_arbitration"])[
            "false_contact_seek_decisions"
        ] != 0:
            raise RuntimeError(
                f"D-035A first false-contact anchor unexpectedly missing for {seed}"
            )
        anchors[D035A_FIRST_ANCHOR] = None
        checks[D035A_FIRST_ANCHOR] = {
            "status": "anchor_unavailable",
            "seed": seed,
            "available": False,
            "terminated_before_false_contact_seek": True,
        }
    else:
        first_anchor, first_checks = _capture_anchor(
            seed, D035A_FIRST_ANCHOR, first_transition, arm_b_result
        )
        anchors[D035A_FIRST_ANCHOR] = first_anchor
        checks[D035A_FIRST_ANCHOR] = _anchor_record(
            first_anchor,
            {
                **first_checks,
                "seed": seed,
                "anchor_transition": first_transition,
            },
        )

    alt8 = d033._find_alt8_transition(tuple(arm_b_trace))
    expected_seed_record = next(
        record
        for record in cast(list[dict[str, object]], accepted_d033["results"])
        if record["seed"] == seed
    )
    expected_alt8 = cast(
        dict[str, object],
        cast(dict[str, object], expected_seed_record["anchors"])[
            d033.D033_ANCHOR_B
        ],
    )
    expected_available = bool(expected_alt8["available"])
    if (alt8 is None) != (not expected_available):
        raise RuntimeError(f"D-035A ALT8 availability diverged from D-033 for {seed}")
    if alt8 is None:
        anchors[D035A_ALT8_ANCHOR] = None
        checks[D035A_ALT8_ANCHOR] = {
            "status": "anchor_unavailable",
            "seed": seed,
            "available": False,
            "accepted_d033_anchor_identity_exact": _anchor_projection(
                {"available": False}
            )
            == _anchor_projection(expected_alt8),
            "accepted_d033_anchor_projection": _anchor_projection(expected_alt8),
        }
        if not cast(
            bool,
            checks[D035A_ALT8_ANCHOR]["accepted_d033_anchor_identity_exact"],
        ):
            raise RuntimeError(
                f"D-035A unavailable ALT8 identity diverged for {seed}"
            )
    else:
        alt_transition, eighth_transition = alt8
        alt_anchor, alt_checks = _capture_anchor(
            seed, D035A_ALT8_ANCHOR, alt_transition, arm_b_result
        )
        alt_record = _anchor_record(
            alt_anchor,
            {
                **alt_checks,
                "seed": seed,
                "anchor_transition": alt_transition,
                "alternation_eighth_transition": eighth_transition,
                "strict_alternation_length": 8,
                "all_actions_false_contact_seek": True,
                "no_contact_within_eight_actions": True,
            },
        )
        d033_projection = _anchor_projection(alt_record)
        expected_projection = _anchor_projection(expected_alt8)
        alt_record["accepted_d033_anchor_identity_exact"] = (
            d033_projection == expected_projection
        )
        alt_record["accepted_d033_anchor_projection"] = expected_projection
        if not alt_record["accepted_d033_anchor_identity_exact"]:
            raise RuntimeError(f"D-035A ALT8 identity diverged from D-033 for {seed}")
        anchors[D035A_ALT8_ANCHOR] = alt_anchor
        checks[D035A_ALT8_ANCHOR] = alt_record

    return (
        {"arm_b": replay_gate},
        tuple(arm_b_trace),
        anchors,
        checks,
    )


def _propose_b_action(
    controller: d026.D026Controller,
    learner: d027.D027ActionConsequencePredictor,
    current: d027.D027Observation,
) -> tuple[
    Action,
    d025.D025Arbitration | None,
    dict[Action, d027.D027Prediction],
]:
    historical = controller.act(current)
    arbitration = controller.last_arbitration
    predictions: dict[Action, d027.D027Prediction] = {}
    proposed = historical
    if arbitration is not None:
        if current.charging_contact or controller.mode is not d026.D026Mode.SEEK:
            raise RuntimeError("D-035A arbitration occurred outside false-contact SEEK")
        predictions, read_only = d031r1._query_candidate_predictions(learner, current)
        if not read_only:
            raise RuntimeError("D-035A prediction query changed learner state")
        proposed = d031r1._choose_steering_action(
            current, predictions, arbitration.greedy_action
        )
    return proposed, arbitration, predictions


def _truth_branches(
    environment: d026.D026Env,
    current: d027.D027Observation,
) -> tuple[
    dict[Action, d029._BranchOutcome],
    bool,
]:
    before_environment = d029._environment_state(environment)
    outcomes = {
        action: d029._branch(environment, current, action)
        for action in D035A_STEERING_ACTIONS
    }
    after_environment = d029._environment_state(environment)
    reversed_outcomes = {
        action: d029._branch(environment, current, action)
        for action in reversed(D035A_STEERING_ACTIONS)
    }
    order_invariant = outcomes == reversed_outcomes
    if before_environment != after_environment:
        raise RuntimeError("D-035A truth branch mutated its source environment")
    return outcomes, order_invariant


def _run_branch(
    anchor: d033._AnchorState,
    *,
    condition: str,
) -> _BranchRun:
    if condition not in D035A_CONDITIONS:
        raise ValueError(f"unknown D-035A condition: {condition}")
    angle = D035A_TURN_ANGLES[condition]
    anchor_before = d033._anchor_fingerprint(anchor)
    environment = d029._clone_environment(anchor.environment)
    canonical_config = environment.config
    environment.config = replace(canonical_config, turn_angle=angle)
    changed_fields = _config_diff_fields(canonical_config, environment.config)
    if changed_fields not in ((), ("turn_angle",)):
        raise RuntimeError("D-035A treatment changed more than turn_angle")
    streams = copy.deepcopy(anchor.streams)
    controller = d033._rewire_controller_rng(anchor.controller, streams.policy)
    if not isinstance(controller, d031r1.D031R1NoDetrapController):
        raise RuntimeError("D-035A anchor controller is not accepted Arm-B")
    learner = d033._learner_from_weights(anchor.learner_weights)
    current = anchor.current
    start_fingerprint = d033._state_fingerprint(
        environment, controller, streams, learner, current
    )
    expected_start = d033._state_fingerprint(
        anchor.environment,
        d033._rewire_controller_rng(anchor.controller, streams.policy),
        streams,
        learner,
        current,
    )
    if start_fingerprint != expected_start:
        raise RuntimeError("D-035A branch clone did not preserve causal start state")

    anchor_body = environment.body
    station = environment.station_center
    if anchor_body is None or station is None:
        raise RuntimeError("D-035A anchor lacks evaluator geometry")
    anchor_position = anchor_body.position
    anchor_heading = anchor_body.heading
    initial_geometry = _geometry_snapshot(anchor_position, anchor_heading, station)
    minimum_geometry = dict(initial_geometry)
    minimum_distance = cast(float, initial_geometry["distance_to_station"])
    previous_heading = anchor_heading
    trace: list[d025.D025TransitionTrace] = []
    prediction_records: list[_PredictionRecord] = []
    truth_records: list[_TruthRecord] = []
    false_contact_rows: list[d025.D025TransitionTrace] = []
    action_counts = Counter[str]()
    boundary_counts = Counter[str]()
    forward_nominal = forward_clipped = forward_stall = 0
    energy_values = [current.energy]
    temperature_values = [current.thermal]
    visible_forward_values = [current.beacon.forward]
    path_length = 0.0
    cumulative_heading_change = 0.0
    signed_commanded_angle = 0.0
    absolute_commanded_angle = 0.0
    charging_contact_entries = 0
    charging_contact_exits = 0
    truth_isolation_environment = True
    truth_isolation_controller = True
    truth_isolation_rng = True
    truth_isolation_learner = True
    truth_branch_order_invariant = True
    arbitration_count = 0
    update_count = 0
    update_digest = hashlib.sha256()
    terminated = False
    truncated = False
    stop_reason: str | None = None
    reacquisition_transition: int | None = None
    reacquisition_geometry: dict[str, object] | None = None
    initial_explorer_calls = controller.false_contact_seek_explorer_calls

    for local_transition in range(1, D035A_BRANCH_HORIZON + 1):
        global_transition = anchor.transition + local_transition - 1
        mode_before = controller.mode
        proposed, arbitration, candidate_predictions = _propose_b_action(
            controller, learner, current
        )
        if arbitration is not None:
            arbitration_count += 1
        action_prediction = learner.predict(current, proposed)
        if arbitration is not None:
            before_environment = d029._environment_state(environment)
            before_controller = d029._controller_state(controller)
            before_rng = d029._rng_state(streams)
            before_weights = learner.weights
            truth, branch_order_invariant = _truth_branches(environment, current)
            truth_isolation_environment &= (
                before_environment == d029._environment_state(environment)
            )
            truth_isolation_controller &= (
                before_controller == d029._controller_state(controller)
            )
            truth_isolation_rng &= before_rng == d029._rng_state(streams)
            truth_isolation_learner &= before_weights == learner.weights
            truth_branch_order_invariant &= branch_order_invariant
            truth_scores = tuple(
                truth[action].delta[d035a_forward_index]
                for action in D035A_STEERING_ACTIONS
            )
            maximum = max(truth_scores)
            truth_argmax = tuple(
                action
                for action in D035A_STEERING_ACTIONS
                if truth[action].delta[d035a_forward_index] == maximum
            )
            learned_scores = tuple(
                current.beacon.forward
                + candidate_predictions[action].values[d035a_forward_index]
                for action in D035A_STEERING_ACTIONS
            )
            truth_records.append(
                _TruthRecord(
                    action=proposed,
                    truth_argmax=truth_argmax,
                    truth_scores=truth_scores,
                    predicted_forward_delta=action_prediction.values[
                        d035a_forward_index
                    ],
                    actual_forward_delta=truth[proposed].delta[
                        d035a_forward_index
                    ],
                    learned_score_margin=_score_margin(learned_scores),
                    truth_score_margin=_score_margin(truth_scores),
                )
            )

        observation_array, reward, terminated, truncated, info = environment.step(
            proposed
        )
        if reward != 0.0 or info != {}:
            raise RuntimeError("D-035A branch crossed reward/info boundary")
        telemetry = environment.last_transition
        if telemetry is None:
            raise RuntimeError("D-035A branch produced no telemetry")
        next_observation = d031r1._next_visible(observation_array)
        update = learner.observe_transition(current, proposed, next_observation)
        if update.prediction != action_prediction.values:
            raise RuntimeError("D-035A pre-update prediction changed before update")
        if update.action is not proposed:
            raise RuntimeError("D-035A learner update did not use executed action")
        update_count += 1
        d031r1._update_digest(update_digest, global_transition, proposed, update)
        row = d025._make_trace(
            transition_index=global_transition,
            mode_before=mode_before,
            mode_after=controller.mode,
            action=proposed,
            current=current,
            observation=observation_array,
            telemetry=telemetry,
            reward=reward,
            info=info,
        )
        trace.append(row)
        prediction_records.append(
            _PredictionRecord(
                local_transition=local_transition,
                action=proposed,
                prediction=update.prediction,
                observed=update.observed_delta,
            )
        )
        action_counts[proposed.name] += 1
        boundary = _forward_boundary(telemetry, proposed)
        if boundary == "FULL_NOMINAL_FORWARD":
            forward_nominal += 1
        elif boundary == "BOUNDARY_CLIPPED_FORWARD":
            forward_clipped += 1
        elif boundary == "FULL_STALL_FORWARD":
            forward_stall += 1
        if boundary is not None:
            boundary_counts[boundary] += 1
        if _is_false_contact_seek_decision(row):
            false_contact_rows.append(row)
        if proposed is Action.TURN_LEFT:
            signed_commanded_angle += angle
            absolute_commanded_angle += angle
        elif proposed is Action.TURN_RIGHT:
            signed_commanded_angle -= angle
            absolute_commanded_angle += angle
        if telemetry.charging_contact_before and not telemetry.charging_contact_after:
            charging_contact_exits += 1
        if not telemetry.charging_contact_before and telemetry.charging_contact_after:
            charging_contact_entries += 1
            reacquisition_transition = local_transition
            reacquisition_geometry = _geometry_snapshot(
                telemetry.position_after, telemetry.heading, station
            )
        path_length += math.dist(telemetry.position_before, telemetry.position_after)
        cumulative_heading_change += _angle_difference(
            previous_heading, telemetry.heading
        )
        previous_heading = telemetry.heading
        distance = math.dist(telemetry.position_after, station)
        if distance < minimum_distance:
            minimum_distance = distance
            minimum_geometry = _geometry_snapshot(
                telemetry.position_after, telemetry.heading, station
            )
        energy_values.append(next_observation.energy)
        temperature_values.append(next_observation.thermal)
        visible_forward_values.append(next_observation.beacon.forward)
        current = next_observation
        if reacquisition_transition is not None:
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
    final_body = environment.body
    if final_body is None:
        raise RuntimeError("D-035A branch lost evaluator body")
    final_geometry = _geometry_snapshot(
        final_body.position, final_body.heading, station
    )
    final_explorer_calls = controller.false_contact_seek_explorer_calls
    branch_explorer_calls = final_explorer_calls - initial_explorer_calls
    policy_rng_digest, environment_rng_digest = _rng_digests(streams)
    final_trace = tuple(trace)
    false_contact_actions = [row.action for row in false_contact_rows]
    alternation_runs = _alternation_run_lengths(false_contact_actions)
    opposite_follow_count = 0
    eligible_follow_count = 0
    for index, row in enumerate(false_contact_rows[:-1]):
        if row.action not in _TURN_ACTIONS:
            continue
        next_action = false_contact_rows[index + 1].action
        if next_action not in _TURN_ACTIONS:
            continue
        eligible_follow_count += 1
        opposite_follow_count += int(next_action is not row.action)

    reversal_counts = {
        "unambiguous_preference_count": 0,
        "sign_flip_count": 0,
        "no_sign_flip_count": 0,
        "post_turn_tie_count": 0,
        "pre_turn_tie_count": 0,
    }
    turn_observations: dict[str, list[tuple[float, float, float]]] = {
        "TURN_LEFT": [],
        "TURN_RIGHT": [],
    }
    for row in final_trace:
        if row.action not in _TURN_ACTIONS:
            continue
        before_difference = row.observation_before[1] - row.observation_before[3]
        after_difference = row.observation[1] - row.observation[3]
        turn_observations[row.action.name].append(
            (
                row.observation_before[2],
                row.observation[2],
                row.observation[2] - row.observation_before[2],
            )
        )
        if before_difference == 0.0:
            reversal_counts["pre_turn_tie_count"] += 1
        else:
            reversal_counts["unambiguous_preference_count"] += 1
            if before_difference * after_difference < 0.0:
                reversal_counts["sign_flip_count"] += 1
            else:
                reversal_counts["no_sign_flip_count"] += 1
            if after_difference == 0.0:
                reversal_counts["post_turn_tie_count"] += 1

    branch_state = {
        "initial_causal_state_digest": start_fingerprint,
        "anchor_causal_state_digest": anchor_before,
        "branch_start_exact": start_fingerprint == expected_start,
        "branch_did_not_mutate_anchor": d033._anchor_fingerprint(anchor)
        == anchor_before,
        "reward_zero_every_transition": all(row.reward == 0.0 for row in final_trace),
        "organism_info_empty_every_transition": all(
            row.info == {} for row in final_trace
        ),
        "executed_action_only_updates": update_count == len(final_trace),
        "exactly_one_d027_update_per_transition": update_count == len(final_trace),
        "one_policy_rng_draw_per_false_contact_seek_decision": (
            arbitration_count == len(false_contact_rows)
        ),
        "zero_false_contact_seek_explorer_calls": branch_explorer_calls == 0,
        "truth_branch_environment_read_only": truth_isolation_environment,
        "truth_branch_controller_read_only": truth_isolation_controller,
        "truth_branch_rng_read_only": truth_isolation_rng,
        "truth_branch_learner_read_only": truth_isolation_learner,
        "truth_branch_order_invariant": truth_branch_order_invariant,
        "no_reseed_or_new_rng_stream": streams.policy is controller.policy_rng
        and streams.policy is controller.explorer.policy_rng,
        "only_turn_angle_config_field_changed": changed_fields in (
            (),
            ("turn_angle",),
        ),
        "canonical_turn_energy_and_time_unchanged": (
            environment.config.turn_actuator_electrical_power_w
            == canonical_config.turn_actuator_electrical_power_w
            and environment.config.dt_seconds == canonical_config.dt_seconds
        ),
    }
    if not all(cast(bool, value) for value in branch_state.values()):
        raise RuntimeError(
            f"D-035A branch isolation failed for {anchor.seed}/{condition}"
        )

    output: dict[str, object] = {
        "seed": anchor.seed,
        "condition": condition,
        "turn_angle_radians": angle,
        "turn_angle_degrees": math.degrees(angle),
        "turn_angle_expression": D035A_TURN_ANGLE_EXPRESSIONS[condition],
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
            "minimum": min(energy_values),
            "maximum": max(energy_values),
            "final_or_stop": current.energy,
            "at_reacquisition": (
                current.energy if reacquisition_transition is not None else None
            ),
        },
        "temperature_normalized": {
            "at_anchor": anchor.current.thermal,
            "minimum": min(temperature_values),
            "maximum": max(temperature_values),
            "final_or_stop": current.thermal,
            "at_reacquisition": (
                current.thermal if reacquisition_transition is not None else None
            ),
        },
        "path_length": path_length,
        "net_displacement_from_anchor": {
            "vector": [
                final_body.position[0] - anchor_position[0],
                final_body.position[1] - anchor_position[1],
            ],
            "magnitude": math.dist(anchor_position, final_body.position),
        },
        "visible_beacon_forward": {
            "start": visible_forward_values[0],
            "maximum": max(visible_forward_values),
            "final": visible_forward_values[-1],
            "change": visible_forward_values[-1] - visible_forward_values[0],
        },
        "evaluator_geometry": {
            "start": initial_geometry,
            "minimum_distance": minimum_geometry,
            "final": final_geometry,
            "at_reacquisition": reacquisition_geometry,
            "geometry_is_evaluator_only": True,
        },
        "evaluator_heading_change": {
            "start": anchor_heading,
            "final": final_body.heading,
            "net_wrapped_change": (
                (final_body.heading - anchor_heading + math.pi) % (2.0 * math.pi)
                - math.pi
            ),
            "cumulative_absolute_change": cumulative_heading_change,
        },
        "action_counts": {name: action_counts[name] for name in _ACTION_NAMES},
        "false_contact_seek": {
            "decision_count": len(false_contact_rows),
            "action_counts": {
                name: Counter(row.action.name for row in false_contact_rows)[name]
                for name in _ACTION_NAMES
            },
            "strict_left_right_alternation_run_count": len(alternation_runs),
            "strict_left_right_alternation_run_lengths": alternation_runs,
            "longest_strict_left_right_alternation_run": max(
                alternation_runs, default=0
            ),
            "turn_followed_by_next_eligible_decision": {
                "eligible_turn_count": eligible_follow_count,
                "opposite_turn_count": opposite_follow_count,
                "opposite_turn_fraction": (
                    opposite_follow_count / eligible_follow_count
                    if eligible_follow_count
                    else None
                ),
            },
        },
        "visible_side_reversal_after_turn": reversal_counts,
        "turn_observations": {
            action: {
                "turn_count": len(values),
                "beacon_forward_before": _number_summary(
                    [value[0] for value in values]
                ),
                "beacon_forward_after": _number_summary(
                    [value[1] for value in values]
                ),
                "signed_beacon_forward_change": _number_summary(
                    [value[2] for value in values]
                ),
            }
            for action, values in turn_observations.items()
        },
        "forward_boundary_counts": {
            "FULL_NOMINAL_FORWARD": forward_nominal,
            "BOUNDARY_CLIPPED_FORWARD": forward_clipped,
            "FULL_STALL_FORWARD": forward_stall,
        },
        "charging_contact_events": {
            "entry_count": charging_contact_entries,
            "exit_count": charging_contact_exits,
        },
        "turn_exposure": {
            "turn_action_count": sum(
                action_counts[action.name] for action in _TURN_ACTIONS
            ),
            "cumulative_commanded_signed_angle_radians": signed_commanded_angle,
            "cumulative_commanded_absolute_angle_radians": absolute_commanded_angle,
            "cumulative_turn_time_seconds": sum(
                action_counts[action.name] for action in _TURN_ACTIONS
            )
            * environment.config.dt_seconds,
            "cumulative_turn_actuator_energy_j": sum(
                action_counts[action.name] for action in _TURN_ACTIONS
            )
            * environment.config.turn_actuator_electrical_power_w
            * environment.config.dt_seconds,
            "turn_energy_and_time_not_scaled_by_angle": True,
        },
        "prediction_diagnostics": {
            "prequential": _prediction_metrics(prediction_records),
            "by_post_anchor_window": _window_prediction_metrics(
                prediction_records, len(final_trace)
            ),
        },
        "one_step_truth_diagnostics": _truth_metrics(truth_records),
        "executed_action_update_count": update_count,
        "executed_action_update_digest": update_digest.hexdigest(),
        "final_learner_state_digest": _digest(tuple(learner.weights)),
        "final_policy_rng_digest": policy_rng_digest,
        "final_environment_rng_digest": environment_rng_digest,
        "false_contact_seek_explorer_calls_in_branch": branch_explorer_calls,
        "false_contact_seek_arbitration_draw_count": arbitration_count,
        "branch_state": branch_state,
        "provenance": {
            "source_anchor_state_immutable": branch_state[
                "branch_did_not_mutate_anchor"
            ],
            "config_diff_fields_from_canonical": list(changed_fields),
            "treatment_changes_only_physical_turn_displacement": True,
            "canonical_action_and_sensor_semantics_unchanged": True,
        },
    }
    return _BranchRun(
        output=output,
        trace=final_trace,
        prediction_records=tuple(prediction_records),
        truth_records=tuple(truth_records),
    )


d035a_forward_index: Final[int] = D035A_OUTPUTS.index("delta_beacon_forward")


def _score_margin(scores: Sequence[float]) -> float:
    ordered = sorted(scores, reverse=True)
    return ordered[0] - ordered[1]


def _control_identity(
    control: _BranchRun,
    baseline: d033._BranchRun,
) -> dict[str, object]:
    output = control.output
    expected = baseline.output
    fields_to_compare = (
        "branch_transition_count",
        "reacquired_within_branch_window",
        "reacquisition_transition_from_anchor",
        "reacquisition_latency",
        "terminated",
        "truncated",
        "stop_reason",
        "termination_reason",
        "path_length",
        "net_displacement_from_anchor",
        "action_counts",
        "forward_boundary_counts",
        "executed_action_update_count",
        "executed_action_update_digest",
        "final_learner_state_digest",
        "final_policy_rng_digest",
        "final_environment_rng_digest",
    )
    mapped = {
        "branch_transition_count": "branch_transition_count",
        "reacquired_within_branch_window": "reacquired_within_branch_window",
        "reacquisition_transition_from_anchor": "reacquisition_transition_from_anchor",
        "reacquisition_latency": "reacquisition_latency",
        "terminated": "terminated",
        "truncated": "truncated",
        "stop_reason": "stop_reason",
        "termination_reason": "termination_reason",
        "path_length": "path_length",
        "net_displacement_from_anchor": "net_displacement_from_anchor",
        "visible_beacon_forward": "visible_beacon_forward",
        "action_counts": "action_counts_total",
        "forward_boundary_counts": "forward_boundary_counts_total",
        "executed_action_update_count": "executed_action_update_count",
        "executed_action_update_digest": "executed_action_update_digest",
        "final_learner_state_digest": "final_branch_learner_state_digest",
        "final_policy_rng_digest": "final_policy_rng_digest",
        "final_environment_rng_digest": "final_environment_rng_digest",
    }
    field_matches = {
        field: output[field] == expected[mapped[field]] for field in fields_to_compare
    }
    visible = cast(dict[str, object], output["visible_beacon_forward"])
    field_matches["visible_beacon_forward"] = (
        visible["change"] == expected["visible_beacon_forward_change"]
        and visible["maximum"] == expected["maximum_visible_beacon_forward"]
    )
    return {
        "trace_exact": control.trace == baseline.trace,
        "checked_fields": list(fields_to_compare),
        "field_matches": field_matches,
        "all_causal_fields_exact": control.trace == baseline.trace
        and all(field_matches.values()),
    }


def _run_anchor_conditions(
    anchor: d033._AnchorState,
    *,
    full_b_trace: tuple[d025.D025TransitionTrace, ...],
) -> tuple[dict[str, object], dict[str, _BranchRun]]:
    anchor_before = d033._anchor_fingerprint(anchor)
    baseline = d033._run_branch(
        anchor,
        family="BASELINE_B",
        requested_length=0,
        sequence=(),
    )
    runs: dict[str, _BranchRun] = {}
    for condition in D035A_CONDITIONS:
        runs[condition] = _run_branch(anchor, condition=condition)
    control = runs["TURN_45_CONTROL"]
    expected_trace = d033._expected_baseline_trace(full_b_trace, anchor.transition)
    control_identity = _control_identity(control, baseline)
    control_identity["expected_d033_baseline_trace_exact"] = (
        control.trace == expected_trace
    )
    if not control_identity["all_causal_fields_exact"] or not control_identity[
        "expected_d033_baseline_trace_exact"
    ]:
        raise RuntimeError(
            f"D-035A TURN_45_CONTROL equivalence failed for "
            f"{anchor.seed}/{anchor.anchor_type}"
        )

    reverse_runs = {
        condition: _run_branch(anchor, condition=condition)
        for condition in reversed(D035A_CONDITIONS)
    }
    order_invariant = all(
        runs[condition].trace == reverse_runs[condition].trace
        and _branch_identity(runs[condition].output)
        == _branch_identity(reverse_runs[condition].output)
        for condition in D035A_CONDITIONS
    )
    if not order_invariant or d033._anchor_fingerprint(anchor) != anchor_before:
        raise RuntimeError(
            f"D-035A condition branch order changed results for {anchor.seed}"
        )
    for condition in D035A_CONDITIONS:
        runs[condition].output["branch_order_invariant"] = order_invariant
        runs[condition].output["turn_45_control_equivalence"] = (
            control_identity if condition == "TURN_45_CONTROL" else None
        )
    summary = {
        "anchor_type": anchor.anchor_type,
        "seed": anchor.seed,
        "available": True,
        "turn_45_control_equivalence": control_identity,
        "branch_order_invariance": order_invariant,
        "conditions": [runs[condition].output for condition in D035A_CONDITIONS],
    }
    return summary, runs


def _branch_identity(output: dict[str, object]) -> dict[str, object]:
    return {
        key: value
        for key, value in output.items()
        if key not in {"branch_order_invariant", "turn_45_control_equivalence"}
    }


def _pooled_summary(
    anchor_type: str,
    runs: Sequence[_BranchRun],
) -> dict[str, object]:
    def values(path: str) -> list[float]:
        result: list[float] = []
        for run in runs:
            value: object = run.output
            for part in path.split("."):
                value = cast(dict[str, object], value)[part]
            if value is not None:
                result.append(float(cast(float, value)))
        return result

    pooled: dict[str, object] = {
        "anchor_type": anchor_type,
        "condition": runs[0].output["condition"] if runs else None,
        "available_seed_count": len(runs),
        "reacquisition_count": sum(
            int(cast(bool, run.output["reacquired_within_branch_window"]))
            for run in runs
        ),
        "reacquisition_latency": _number_summary(
            [
                float(cast(int, run.output["reacquisition_latency"]))
                for run in runs
                if run.output["reacquisition_latency"] is not None
            ]
        ),
        "energy_at_reacquisition": _number_summary(
            values("energy.at_reacquisition")
        ),
        "temperature_at_reacquisition": _number_summary(
            values("temperature_normalized.at_reacquisition")
        ),
        "path_length": _number_summary(values("path_length")),
        "minimum_evaluator_distance": _number_summary(
            values("evaluator_geometry.minimum_distance.distance_to_station")
        ),
        "action_counts": {
            name: sum(
                cast(dict[str, int], run.output["action_counts"])[name]
                for run in runs
            )
            for name in _ACTION_NAMES
        },
        "false_contact_seek_decisions": sum(
            cast(dict[str, int], run.output["false_contact_seek"])["decision_count"]
            for run in runs
        ),
        "turn_action_count": sum(
            cast(
                int,
                cast(dict[str, object], run.output["turn_exposure"])[
                    "turn_action_count"
                ],
            )
            for run in runs
        ),
        "cumulative_commanded_absolute_angle_radians": sum(
            cast(
                float,
                cast(dict[str, object], run.output["turn_exposure"])[
                    "cumulative_commanded_absolute_angle_radians"
                ],
            )
            for run in runs
        ),
        "alternation_run_count": sum(
            cast(
                int,
                cast(dict[str, object], run.output["false_contact_seek"])[
                    "strict_left_right_alternation_run_count"
                ],
            )
            for run in runs
        ),
        "longest_alternation_run": max(
            (
                cast(
                    int,
                    cast(dict[str, object], run.output["false_contact_seek"])[
                        "longest_strict_left_right_alternation_run"
                    ],
                )
                for run in runs
            ),
            default=0,
        ),
        "prediction_diagnostics": _prediction_metrics(
            [record for run in runs for record in run.prediction_records]
        ),
        "prediction_windows": _window_prediction_metrics(
            [record for run in runs for record in run.prediction_records],
            max((len(run.trace) for run in runs), default=0),
        ),
        "one_step_truth_diagnostics": _truth_metrics(
            [record for run in runs for record in run.truth_records]
        ),
        "termination_reason_counts": {
            "reacquisition_or_not_terminated": sum(
                int(run.output["termination_reason"] is None) for run in runs
            ),
            "horizon_truncation": sum(
                int(run.output["termination_reason"] == "horizon_truncation")
                for run in runs
            ),
            "energy_depletion": sum(
                int(run.output["termination_reason"] == "energy_depletion")
                for run in runs
            ),
            "protective_thermal_shutdown": sum(
                int(
                    run.output["termination_reason"]
                    == "protective_thermal_shutdown"
                )
                for run in runs
            ),
            "emergency_hard_thermal_shutdown": sum(
                int(
                    run.output["termination_reason"]
                    == "emergency_hard_thermal_shutdown"
                )
                for run in runs
            ),
        },
        "seed_lists": {
            "reacquired": [
                cast(int, run.output["seed"])
                for run in runs
                if cast(bool, run.output["reacquired_within_branch_window"])
            ],
            "not_reacquired": [
                cast(int, run.output["seed"])
                for run in runs
                if not cast(bool, run.output["reacquired_within_branch_window"])
            ],
        },
        "outlier_handling": {
            "discarded_seed_count": 0,
            "statement": (
                "All available per-seed outcomes are retained; no outliers are "
                "discarded."
            ),
        },
    }
    return pooled


def _interpretation(
    pooled: dict[str, dict[str, dict[str, object]]],
) -> dict[str, object]:
    return {
        "lane": "Development",
        "confirmatory_claim": False,
        "predeclared_readings": [
            (
                "Finer branches reducing oscillation and restoring reacquisition "
                "support coarse turn quantization as a causal contributor, without "
                "authorizing canonical action changes."
            ),
            (
                "Lower turn-action prequential error or improved one-step truth "
                "fidelity supports easier local prediction for the unchanged learner."
            ),
            (
                "Behaviour improvement without prediction improvement supports a "
                "geometric/kinematic rather than learner-representation account."
            ),
            (
                "Prediction improvement without reacquisition shows that easier "
                "local prediction is not sufficient for docking under the current "
                "controller."
            ),
            (
                "Only very fine angles helping requires explicit accounting of "
                "action/time/energy exposure."
            ),
            (
                "No finer angle helping leaves coarse turn quantization insufficient "
                "on this support and returns the question to learned-state/history/"
                "scaffold-recruitment explanations."
            ),
            (
                "Failure of any 45-degree control identity invalidates treatment "
                "interpretation."
            ),
        ],
        "observed_reacquisition_counts": {
            anchor: {
                condition: pooled[anchor][condition]["reacquisition_count"]
                for condition in D035A_CONDITIONS
            }
            for anchor in D035A_ANCHORS
        },
        "descriptive_observations_only": True,
        "no_universal_pass_threshold": True,
        "no_canonical_turn_semantics_change": True,
        "no_successor_authorized": True,
    }


def run_d035a_audit(
    seeds: Sequence[int] = D035A_DEFAULT_DEVELOPMENT_SEEDS,
    *,
    horizon: int = D035A_HORIZON,
    executed_commit_sha: str | None = None,
) -> dict[str, object]:
    """Run the complete frozen D-035A protocol on the reused support."""
    validated = _validate_d035a_development_seeds(seeds)
    if horizon != D035A_HORIZON:
        raise ValueError("D-035A requires the frozen 70,000-transition horizon")
    executed_sha = _validate_executed_commit_sha(executed_commit_sha)
    if executed_sha is None:
        raise ValueError("D-035A requires an exact clean executable SHA")
    accepted_d031r1 = _accepted_artifact(D035A_ACCEPTED_D031R1_ARTIFACT)
    accepted_d033 = _accepted_artifact(D035A_ACCEPTED_D033_ARTIFACT)
    seed_records: list[dict[str, object]] = []
    all_runs: dict[str, dict[str, list[_BranchRun]]] = {
        anchor: {condition: [] for condition in D035A_CONDITIONS}
        for anchor in D035A_ANCHORS
    }
    for seed in validated:
        replay, b_trace, anchors, anchor_records = _replay_and_anchors(
            seed, accepted_d031r1, accepted_d033
        )
        serial_anchors: dict[str, dict[str, object]] = {}
        for anchor_type in D035A_ANCHORS:
            anchor = anchors[anchor_type]
            record = dict(anchor_records[anchor_type])
            if anchor is None:
                serial_anchors[anchor_type] = record
                continue
            summary, runs = _run_anchor_conditions(anchor, full_b_trace=b_trace)
            record.update(summary)
            serial_anchors[anchor_type] = record
            for condition, run in runs.items():
                all_runs[anchor_type][condition].append(run)
        seed_records.append(
            {
                "seed": seed,
                "replay": replay,
                "anchors": serial_anchors,
            }
        )
    pooled = {
        anchor: {
            condition: _pooled_summary(anchor, all_runs[anchor][condition])
            for condition in D035A_CONDITIONS
        }
        for anchor in D035A_ANCHORS
    }
    return {
        "schema_version": 1,
        "experiment": "D-035A",
        "title": "Evaluator-only turn-granularity attribution audit",
        "authoritative_base_sha": D035A_AUTHORITATIVE_BASE_SHA,
        "base_tree_sha": D035A_BASE_TREE_SHA,
        "implementation_probe_sha": executed_sha,
        "protocol_only_freeze_sha": executed_sha,
        "development_seeds": list(validated),
        "horizon": D035A_HORIZON,
        "branch_horizon": D035A_BRANCH_HORIZON,
        "timestep_seconds": D020PhysicalConfig().dt_seconds,
        "support": {
            "source": "accepted D-031R1/D-032/D-033/D-034 Development support",
            "accepted_d031r1_artifact": D035A_ACCEPTED_D031R1_ARTIFACT,
            "accepted_d031r1_artifact_sha256": _artifact_sha256(
                D035A_ACCEPTED_D031R1_ARTIFACT
            ),
            "accepted_d033_artifact": D035A_ACCEPTED_D033_ARTIFACT,
            "accepted_d033_artifact_sha256": _artifact_sha256(
                D035A_ACCEPTED_D033_ARTIFACT
            ),
            "fresh_seed_block_allocated": False,
            "fresh_seed_block_inspected": False,
        },
        "freeze": {
            "anchors": list(D035A_ANCHORS),
            "first_anchor_definition": (
                "first Arm-B pre-action state with controller mode SEEK and false "
                "charging contact before ordinary no-de-trap arbitration"
            ),
            "alt8_anchor_definition": (
                "exact accepted D-033 first pre-action state after eight completed "
                "strict alternating false-contact SEEK left/right actions"
            ),
            "conditions": list(D035A_CONDITIONS),
            "turn_angles_radians": {
                condition: D035A_TURN_ANGLES[condition]
                for condition in D035A_CONDITIONS
            },
            "turn_angle_expressions": dict(D035A_TURN_ANGLE_EXPRESSIONS),
            "only_physical_turn_displacement_changes": True,
            "turn_timestep_and_energy_accounting_scaled_by_angle": False,
            "candidate_actions": [action.name for action in D035A_STEERING_ACTIONS],
            "channels": list(D035A_CHANNELS),
            "outputs": list(D035A_OUTPUTS),
            "branch_horizon": D035A_BRANCH_HORIZON,
            "stop_rules": [
                "dual-contact reacquisition",
                "inherited energy or thermal termination",
                "inherited episode truncation",
                "4096 transitions from anchor",
            ],
            "complete_causal_state_clone": [
                "environment and physical state",
                "current six-channel observation",
                "controller mode/transient/explorer state",
                "complete 168-weight D-027 learner state",
                "policy and environment RNG state",
                "transition index and inherited horizon",
                "executed-update provenance digest",
            ],
            "no_interpolation_or_continuous_action": True,
            "no_canonical_environment_or_controller_change": True,
        },
        "causal_order": [
            "exact accepted Arm-B replay and evaluator-only anchor selection",
            "clone complete Arm-B causal continuation state",
            "unchanged Arm-B controller/action-selection pipeline",
            "read-only evaluator one-step truth branches",
            "one physical transition under the condition's isolated turn angle",
            "actual next six-channel observation",
            "one unchanged executed-action D-027 update",
            "post-hoc evaluator metrics only",
        ],
        "organism_boundary": {
            "channels": list(D035A_CHANNELS),
            "actions": [action.name for action in Action],
            "reward": 0.0,
            "info": {},
            "canonical_turn_angle_unchanged": True,
            "sensor_geometry_unchanged": True,
            "turn_energy_and_time_accounting_unchanged": True,
            "evaluator_truth_geometry_heading_oscillation_outcomes_not_exposed": True,
            "new_rng_stream_or_reseed": False,
        },
        "replay_gate": {
            "all_seeds_exact_arm_b_replay": True,
            "checked_identity_fields": list(_CAUSAL_IDENTITY_FIELDS) + ["_weights"],
            "zero_false_contact_seek_explorer_calls_required": True,
            "one_legacy_policy_rng_draw_per_false_contact_seek_decision_required": True,
            "complete_168_weight_state_required": True,
            "accepted_d033_alt8_anchor_identity_required": True,
        },
        "results": seed_records,
        "pooled": pooled,
        "interpretation": _interpretation(pooled),
    }


def write_d035a_json(path: Path, executed_commit_sha: str | None = None) -> Path:
    path.write_text(
        json.dumps(
            run_d035a_audit(executed_commit_sha=executed_commit_sha),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the D-035A turn audit.")
    parser.add_argument("--executed-commit-sha")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.output is None:
        print(
            json.dumps(
                run_d035a_audit(executed_commit_sha=args.executed_commit_sha),
                indent=2,
                sort_keys=True,
            )
        )
    else:
        write_d035a_json(args.output, args.executed_commit_sha)
        print(f"D-035A result written to {args.output}")


if __name__ == "__main__":
    main()
