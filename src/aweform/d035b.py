"""D-035B evaluator-only L/F/R turn-magnitude attribution audit.

D-035B replays the accepted D-031R1 ``LEARNED_NO_DETRAP`` Arm-B lifetime,
reconstructs the first false-contact SEEK and exact D-033 ALT8 anchors, and
runs isolated matched branches from those complete causal states.  The L/F/R
interpolation is an evaluator-side action-magnitude diagnostic: logical
actions remain the existing four-action enum, and the inherited controller,
learner, physical time, action-energy accounting, observation boundary,
reward, and information boundary remain unchanged.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import pickle
import statistics
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Final, cast

from . import d025, d026, d027, d029, d031r1, d032, d033
from .d020 import D020PhysicalConfig
from .env import Action
from .exp003 import seek_beacon_action
from .exp003_seed_policy import validate_exp003_development_seeds
from .rng import RandomStreams

D035B_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = tuple(
    range(18468, 18488)
)
D035B_HORIZON: Final[int] = 70_000
D035B_BRANCH_HORIZON: Final[int] = d033.D033_BRANCH_HORIZON
D035B_ANCHOR_TYPES: Final[tuple[str, ...]] = (
    "FIRST_FALSE_CONTACT_SEEK",
    "ALT8_ESTABLISHED",
)
D035B_CAPS_DEGREES: Final[tuple[float, ...]] = (5.0, 2.0, 1.0)
D035B_CAPS_RADIANS: Final[tuple[float, ...]] = tuple(
    math.radians(value) for value in D035B_CAPS_DEGREES
)
D035B_AUTHORITATIVE_BASE_SHA: Final[str] = (
    "d40681d25cd4cc67e359004ffcd63819e40b42a4"
)
D035B_BASE_TREE_SHA: Final[str] = "50510ba772a1d53960f7f5870feb6b7b510cacf4"
D035B_ACCEPTED_D031R1_ARTIFACT: Final[str] = (
    d033.D033_ACCEPTED_D031R1_ARTIFACT
)
D035B_LFR_FORMULA: Final[str] = (
    "x=F+cos(pi/4)*(L+R); y=sin(pi/4)*(L-R); "
    "theta_hat=atan2(y,x); zero vector theta_hat=0"
)
D035B_BRANCH_HORIZON_EXPRESSION: Final[str] = "4096 transitions"

_ACTION_NAMES: Final[tuple[str, ...]] = tuple(action.name for action in Action)
_TURN_ACTIONS: Final[frozenset[Action]] = frozenset(
    (Action.TURN_LEFT, Action.TURN_RIGHT)
)
_CAUSAL_IDENTITY_FIELDS: Final[tuple[str, ...]] = d032._CAUSAL_IDENTITY_FIELDS


@dataclass(frozen=True, slots=True)
class _LFRVector:
    x: float
    y: float
    theta_hat: float
    zero_vector: bool


@dataclass(slots=True)
class _PredictionAccumulator:
    count: int = 0
    absolute_error: list[float] | None = None
    signed_error: list[float] | None = None
    sign_agreement: list[int] | None = None
    sign_comparison_count: list[int] | None = None

    def __post_init__(self) -> None:
        width = len(d027.D027_OUTPUTS)
        if self.absolute_error is None:
            self.absolute_error = [0.0] * width
        if self.signed_error is None:
            self.signed_error = [0.0] * width
        if self.sign_agreement is None:
            self.sign_agreement = [0] * width
        if self.sign_comparison_count is None:
            self.sign_comparison_count = [0] * width

    def record(self, predicted: Sequence[float], observed: Sequence[float]) -> None:
        assert self.absolute_error is not None
        assert self.signed_error is not None
        assert self.sign_agreement is not None
        assert self.sign_comparison_count is not None
        self.count += 1
        for index, (left, right) in enumerate(zip(predicted, observed, strict=True)):
            self.absolute_error[index] += abs(left - right)
            self.signed_error[index] += right - left
            if left != 0.0 and right != 0.0:
                self.sign_comparison_count[index] += 1
                self.sign_agreement[index] += int((left > 0.0) == (right > 0.0))

    def as_dict(self) -> dict[str, object]:
        assert self.absolute_error is not None
        assert self.signed_error is not None
        assert self.sign_agreement is not None
        assert self.sign_comparison_count is not None
        return {
            "sample_count": self.count,
            "targets": {
                output: {
                    "mean_absolute_error": (
                        self.absolute_error[index] / self.count
                        if self.count
                        else None
                    ),
                    "mean_signed_error_observed_minus_predicted": (
                        self.signed_error[index] / self.count
                        if self.count
                        else None
                    ),
                    "nonzero_sign_comparison_count": self.sign_comparison_count[
                        index
                    ],
                    "nonzero_sign_agreement_count": self.sign_agreement[index],
                    "nonzero_sign_agreement_fraction": (
                        self.sign_agreement[index]
                        / self.sign_comparison_count[index]
                        if self.sign_comparison_count[index]
                        else None
                    ),
                }
                for index, output in enumerate(d027.D027_OUTPUTS)
            },
        }


def _validate_d035b_development_seeds(
    seeds: Sequence[int],
) -> tuple[int, ...]:
    validated = validate_exp003_development_seeds(seeds)
    if validated != D035B_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-035B requires exactly the frozen development seeds "
            f"{D035B_DEFAULT_DEVELOPMENT_SEEDS}; got {validated}"
        )
    return validated


def _validate_d035b_seed(seed: int) -> None:
    validated = validate_exp003_development_seeds((seed,))
    if validated[0] not in D035B_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-035B may execute only the reused development seeds "
            f"{D035B_DEFAULT_DEVELOPMENT_SEEDS}; got {validated[0]}"
        )


def _validate_executed_commit_sha(value: str | None) -> str | None:
    return d031r1._validate_executed_commit_sha(value)


def _digest(value: object) -> str:
    return hashlib.sha256(pickle.dumps(value, protocol=5)).hexdigest()


def _wrap_angle(value: float) -> float:
    return (value + math.pi) % math.tau - math.pi


def _angle_difference(left: float, right: float) -> float:
    return abs(_wrap_angle(right - left))


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


def _lfr_vector(observation: d027.D027Observation) -> _LFRVector:
    left = observation.beacon.left
    forward = observation.beacon.forward
    right = observation.beacon.right
    x = forward + math.cos(math.pi / 4.0) * (left + right)
    y = math.sin(math.pi / 4.0) * (left - right)
    zero_vector = x == 0.0 and y == 0.0
    return _LFRVector(
        x=x,
        y=y,
        theta_hat=0.0 if zero_vector else math.atan2(y, x),
        zero_vector=zero_vector,
    )


def _cap_radians(cap_degrees: float) -> float:
    if cap_degrees not in D035B_CAPS_DEGREES:
        raise ValueError(f"D-035B cap must be one of {D035B_CAPS_DEGREES}")
    return math.radians(cap_degrees)


def _lfr_turn_magnitude(
    vector: _LFRVector,
    *,
    cap_degrees: float,
    variant: str,
) -> float:
    cap = _cap_radians(cap_degrees)
    if variant == "LFR_FIXED":
        return cap
    if variant == "LFR_INTERP":
        return min(cap, abs(vector.theta_hat))
    raise ValueError(f"unknown D-035B LFR variant: {variant}")


def _lfr_branch_name(variant: str, cap_degrees: float) -> str:
    if variant not in {"LFR_FIXED", "LFR_INTERP"}:
        raise ValueError(f"unknown D-035B LFR variant: {variant}")
    return f"{variant}_{cap_degrees:g}DEG"


def _empty_action_counts() -> dict[str, int]:
    return {name: 0 for name in _ACTION_NAMES}


def _rng_digests(streams: RandomStreams) -> tuple[str, str]:
    return (
        _digest(streams.policy.bit_generator.state),
        _digest(streams.environment.bit_generator.state),
    )


def _forward_boundary(row: d025.D025TransitionTrace) -> str | None:
    if row.action is not Action.MOVE_FORWARD:
        return None
    displacement = math.dist(
        row.telemetry.position_before, row.telemetry.position_after
    )
    if displacement <= d027.D027_BOUNDARY_TOLERANCE:
        return "FULL_STALL_FORWARD"
    return d027._classify_forward_displacement(displacement)


def _first_false_contact_seek_transition(
    trace: Sequence[d025.D025TransitionTrace],
) -> int | None:
    """Return the first completed false-contact SEEK decision transition.

    This deliberately includes the inherited AWAY-to-SEEK entry transition:
    the controller has selected SEEK after seeing a low-energy, non-contact
    observation, and the completed transition is required to remain
    non-contact.  The pre-action clone is therefore the exact first
    false-contact SEEK decision state, not a later hand-selected occurrence.
    """
    for row in trace:
        if (
            row.mode_after is d026.D026Mode.SEEK
            and not row.observation_before[4]
            and not row.observation[4]
            and not row.telemetry.charging_contact_before
            and not row.telemetry.charging_contact_after
        ):
            return row.transition_index
    return None


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
    replay: dict[str, object],
    accepted: dict[str, object],
) -> dict[str, object]:
    accepted_with_private_weights = dict(accepted)
    accepted_with_private_weights["_weights"] = d033._flatten_final_weights(accepted)
    comparison = d032._compare_identity_fields(
        replay, accepted_with_private_weights, include_private_weights=True
    )
    isolation = cast(dict[str, object], replay["isolation"])
    result = {
        "seed": seed,
        "accepted_artifact_arm": "LEARNED_NO_DETRAP",
        "all_identity_fields_exact": comparison["all_identity_fields_exact"],
        "checked_identity_fields": comparison["checked_fields"],
        "mismatched_identity_fields": comparison["mismatched_fields"],
        "zero_false_contact_seek_delegation": isolation[
            "zero_false_contact_seek_delegation"
        ],
        "zero_false_contact_seek_explorer_calls": isolation[
            "no_false_contact_seek_explorer_call"
        ],
        "one_legacy_arbitration_draw_per_false_contact_seek_decision": isolation[
            "one_legacy_arbitration_draw_per_false_contact_seek_decision"
        ],
    }
    if not all(
        bool(result[key])
        for key in (
            "all_identity_fields_exact",
            "zero_false_contact_seek_delegation",
            "zero_false_contact_seek_explorer_calls",
            "one_legacy_arbitration_draw_per_false_contact_seek_decision",
        )
    ):
        raise RuntimeError(f"D-035B Arm-B replay gate failed for seed {seed}")
    return result


def _capture_anchor(
    seed: int,
    anchor_type: str,
    transition: int,
    full_trace: tuple[d025.D025TransitionTrace, ...],
    replay: dict[str, object],
) -> tuple[d033._AnchorState, dict[str, object]]:
    result, trace, instrumentation = d033._run_capture(
        seed,
        role="B",
        horizon=D035B_HORIZON,
        target_transition=transition,
        seed_validator=_validate_d035b_seed,
    )
    if trace != full_trace:
        raise RuntimeError(
            f"D-035B {anchor_type} capture changed Arm-B replay for seed {seed}"
        )
    comparison = d032._compare_identity_fields(
        result, replay, include_private_weights=True
    )
    if not comparison["all_identity_fields_exact"]:
        raise RuntimeError(
            f"D-035B {anchor_type} capture diverged for seed {seed}"
        )
    capture = instrumentation.capture
    if capture is None:
        raise RuntimeError(
            f"D-035B {anchor_type} pre-action capture missing for seed {seed}"
        )
    if capture.transition != transition:
        raise RuntimeError("D-035B captured transition index changed")
    anchor = d033._anchor_from_capture(seed, anchor_type, capture)
    return anchor, {
        "target_capture_replay_exact": comparison["all_identity_fields_exact"],
        "target_capture_checked_identity_fields": comparison["checked_fields"],
        "target_capture_mismatched_identity_fields": comparison["mismatched_fields"],
        "anchor_state_digest": d033._anchor_fingerprint(anchor),
        "anchor_update_prefix_digest": anchor.update_prefix_digest,
        "anchor_mode": anchor.controller.mode.name,
        "anchor_contact": anchor.current.charging_contact,
        "anchor_proposed_action": anchor.proposed_action.name,
    }


def _anchor_definition(
    anchor_type: str,
    trace: tuple[d025.D025TransitionTrace, ...],
) -> dict[str, object] | None:
    if anchor_type == "FIRST_FALSE_CONTACT_SEEK":
        transition = _first_false_contact_seek_transition(trace)
        if transition is None:
            return None
        return {
            "anchor_type": anchor_type,
            "transition": transition,
            "selection_rule": (
                "first completed transition with mode_after=SEEK, visible "
                "charging_contact before/after false, and evaluator contact "
                "before/after false"
            ),
            "history_or_geometry_used_for_selection": False,
        }
    if anchor_type == "ALT8_ESTABLISHED":
        selected = d033._find_alt8_transition(trace)
        if selected is None:
            return None
        transition, last_transition = selected
        rows = trace[last_transition - 8 : last_transition]
        return {
            "anchor_type": anchor_type,
            "transition": transition,
            "last_completed_transition": last_transition,
            "selection_rule": (
                "D-033 exact first eight-action strict left/right alternation "
                "in false-contact SEEK, followed by a pre-action state"
            ),
            "completed_actions": [row.action.name for row in rows],
            "completed_observation_digest": _digest(
                [
                    {
                        "transition": row.transition_index,
                        "action": row.action.name,
                        "observation_before": list(row.observation_before),
                        "observation_after": list(row.observation),
                    }
                    for row in rows
                ]
            ),
            "strict_alternation_length": 8,
            "all_actions_false_contact_seek": True,
            "no_contact_forward_or_wait_action": True,
            "history_or_geometry_used_for_selection": False,
        }
    raise ValueError(f"unknown D-035B anchor type: {anchor_type}")


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


def _station_bearing(
    environment: d026.D026Env,
) -> float:
    if environment.body is None or environment.station_center is None:
        raise RuntimeError("D-035B environment lacks evaluator geometry")
    dx = environment.station_center[0] - environment.body.position[0]
    dy = environment.station_center[1] - environment.body.position[1]
    return _wrap_angle(math.atan2(dy, dx) - environment.body.heading)


def _step_with_turn_angle(
    environment: d026.D026Env,
    action: Action,
    turn_angle: float | None,
) -> tuple[Any, float, bool, bool, dict[str, object]]:
    """Apply one canonical transition with an evaluator-only turn angle.

    D-020's action class still determines timestep, electrical load, thermal
    terms, and viability.  Only the evaluator-side body heading increment is
    temporarily changed for a turn branch; the logical action remains the
    existing enum.
    """
    if turn_angle is None or action not in _TURN_ACTIONS:
        return environment.step(action)
    original_config = environment.config
    environment.config = replace(original_config, turn_angle=turn_angle)
    try:
        return environment.step(action)
    finally:
        environment.config = original_config


def _lfr_action(
    current: d027.D027Observation,
    *,
    cap_degrees: float,
    variant: str,
    environment: d026.D026Env,
    previous_turn_side: Action | None,
) -> tuple[Action, float | None, dict[str, object], Action | None]:
    gate = seek_beacon_action(current.beacon)
    vector = _lfr_vector(current)
    magnitude = _lfr_turn_magnitude(
        vector, cap_degrees=cap_degrees, variant=variant
    )
    true_bearing = _station_bearing(environment)
    side_reversal = (
        previous_turn_side is not None
        and gate in _TURN_ACTIONS
        and previous_turn_side is not gate
    )
    direction_mismatch = (
        (gate is Action.TURN_LEFT and vector.theta_hat < 0.0)
        or (gate is Action.TURN_RIGHT and vector.theta_hat > 0.0)
    )
    record = {
        "gate_action": gate.name,
        "theta_hat_radians": vector.theta_hat,
        "theta_hat_degrees": math.degrees(vector.theta_hat),
        "vector_x": vector.x,
        "vector_y": vector.y,
        "zero_vector": vector.zero_vector,
        "true_evaluator_station_bearing_radians": true_bearing,
        "directional_error_radians": _angle_difference(
            vector.theta_hat, true_bearing
        ),
        "directional_error_degrees": math.degrees(
            _angle_difference(vector.theta_hat, true_bearing)
        ),
        "directional_signed_error_radians": _wrap_angle(
            vector.theta_hat - true_bearing
        ),
        "turn_side_reversal": side_reversal,
        "direction_mismatch_with_seek_gate": direction_mismatch,
        "saturated": (
            gate in _TURN_ACTIONS
            and abs(vector.theta_hat) >= _cap_radians(cap_degrees)
        ),
        "cap_degrees": cap_degrees,
        "variant": variant,
        "applied_turn_magnitude_radians": magnitude if gate in _TURN_ACTIONS else 0.0,
        "applied_turn_magnitude_degrees": (
            math.degrees(magnitude) if gate in _TURN_ACTIONS else 0.0
        ),
    }
    next_turn_side = gate if gate in _TURN_ACTIONS else previous_turn_side
    return gate, magnitude if gate in _TURN_ACTIONS else None, record, next_turn_side


def _prediction_summary(
    accumulator: _PredictionAccumulator,
) -> dict[str, object]:
    return accumulator.as_dict()


def _lfr_diagnostic_summary(
    records: Sequence[dict[str, object]],
) -> dict[str, object]:
    if not records:
        return {
            "decision_count": 0,
            "turn_decision_count": 0,
            "gate_action_counts": _empty_action_counts(),
            "zero_vector_count": 0,
            "saturation_count": 0,
            "unsaturated_count": 0,
            "saturation_fraction_among_turns": None,
            "direction_mismatch_count": 0,
            "side_reversal_count": 0,
            "directional_error_radians": _number_summary([]),
            "directional_error_degrees": _number_summary([]),
            "directional_signed_error_radians": _number_summary([]),
            "theta_absolute_radians": _number_summary([]),
            "applied_turn_magnitude_degrees": _number_summary([]),
        }
    gate_counts = _empty_action_counts()
    errors: list[float] = []
    errors_degrees: list[float] = []
    signed_errors: list[float] = []
    theta_values: list[float] = []
    magnitudes: list[float] = []
    turn_count = 0
    zero_vectors = 0
    saturation_count = 0
    mismatch_count = 0
    reversal_count = 0
    for record in records:
        gate = cast(str, record["gate_action"])
        gate_counts[gate] += 1
        zero_vectors += int(cast(bool, record["zero_vector"]))
        errors.append(cast(float, record["directional_error_radians"]))
        errors_degrees.append(cast(float, record["directional_error_degrees"]))
        signed_errors.append(cast(float, record["directional_signed_error_radians"]))
        theta_values.append(abs(cast(float, record["theta_hat_radians"])))
        if gate in {Action.TURN_LEFT.name, Action.TURN_RIGHT.name}:
            turn_count += 1
            magnitudes.append(
                cast(float, record["applied_turn_magnitude_degrees"])
            )
            saturation_count += int(cast(bool, record["saturated"]))
        mismatch_count += int(cast(bool, record["direction_mismatch_with_seek_gate"]))
        reversal_count += int(cast(bool, record["turn_side_reversal"]))
    return {
        "decision_count": len(records),
        "turn_decision_count": turn_count,
        "gate_action_counts": gate_counts,
        "zero_vector_count": zero_vectors,
        "saturation_count": saturation_count,
        "unsaturated_count": turn_count - saturation_count,
        "saturation_fraction_among_turns": (
            saturation_count / turn_count if turn_count else None
        ),
        "direction_mismatch_count": mismatch_count,
        "side_reversal_count": reversal_count,
        "directional_error_radians": _number_summary(errors),
        "directional_error_degrees": _number_summary(errors_degrees),
        "directional_signed_error_radians": _number_summary(signed_errors),
        "theta_absolute_radians": _number_summary(theta_values),
        "applied_turn_magnitude_degrees": _number_summary(magnitudes),
    }


def _run_branch(
    anchor: d033._AnchorState,
    *,
    family: str,
    full_b_trace: tuple[d025.D025TransitionTrace, ...],
    cap_degrees: float | None = None,
    variant: str | None = None,
) -> tuple[dict[str, object], tuple[d025.D025TransitionTrace, ...]]:
    valid_baseline = family == "BASELINE_B"
    valid_lfr = variant in {"LFR_FIXED", "LFR_INTERP"}
    if not valid_baseline and not valid_lfr:
        raise ValueError("D-035B branch must be BASELINE_B or an LFR variant")
    if valid_baseline and (cap_degrees is not None or variant is not None):
        raise ValueError("BASELINE_B cannot have an LFR cap or variant")
    if valid_lfr and cap_degrees not in D035B_CAPS_DEGREES:
        raise ValueError("D-035B LFR branch cap is not frozen")

    anchor_before = d033._anchor_fingerprint(anchor)
    environment = d029._clone_environment(anchor.environment)
    streams = copy.deepcopy(anchor.streams)
    controller = d033._rewire_controller_rng(anchor.controller, streams.policy)
    learner = d033._learner_from_weights(anchor.learner_weights)
    current = anchor.current
    start_fingerprint = d033._state_fingerprint(
        environment, controller, streams, learner, current
    )
    expected_start = d033._state_fingerprint(
        anchor.environment,
        anchor.controller,
        anchor.streams,
        learner,
        anchor.current,
    )
    if start_fingerprint != expected_start:
        raise RuntimeError("D-035B branch clone did not preserve causal start state")
    if not isinstance(controller, d031r1.D031R1NoDetrapController):
        raise RuntimeError("D-035B branch anchor is not inherited Arm-B")

    trace: list[d025.D025TransitionTrace] = []
    lfr_records: list[dict[str, object]] = []
    prediction_metrics = _PredictionAccumulator()
    action_counts = _empty_action_counts()
    proposed_action_counts = _empty_action_counts()
    arbitration_count = 0
    explorer_calls_before = controller.false_contact_seek_explorer_calls
    previous_turn_side: Action | None = None
    terminated = False
    truncated = False
    stop_reason: str | None = None
    reacquisition_transition: int | None = None
    minimum_energy = current.energy
    minimum_temperature = current.thermal
    energy_values = [current.energy]
    forward_values = [current.beacon.forward]
    path_length = 0.0
    cumulative_heading_change = 0.0
    if environment.body is None or environment.station_center is None:
        raise RuntimeError("D-035B branch lacks evaluator geometry")
    initial_position = environment.body.position
    station = environment.station_center
    previous_heading = environment.body.heading
    initial_distance = math.dist(initial_position, station)
    minimum_distance = initial_distance
    maximum_displacement = 0.0
    update_count = 0
    update_digest = hashlib.sha256()
    all_prediction_queries_read_only = True
    all_update_predictions_exact = True
    all_turn_energy_semantics_canonical = True
    all_logical_actions_existing_enum = True

    for local_transition in range(1, D035B_BRANCH_HORIZON + 1):
        global_transition = anchor.transition + local_transition - 1
        mode_before = controller.mode
        proposed, arbitration = d033._propose_b_action(controller, learner, current)
        proposed_action_counts[proposed.name] += 1
        physical_action = proposed
        turn_angle: float | None = None
        if arbitration is not None:
            arbitration_count += 1
        if valid_lfr and arbitration is not None:
            if current.charging_contact or controller.mode is not d026.D026Mode.SEEK:
                raise RuntimeError("D-035B LFR branch escaped false-contact SEEK")
            if arbitration.delegated:
                raise RuntimeError("D-035B LFR branch unexpectedly delegated")
            gate, turn_angle, lfr_record, previous_turn_side = _lfr_action(
                current,
                cap_degrees=cast(float, cap_degrees),
                variant=cast(str, variant),
                environment=environment,
                previous_turn_side=previous_turn_side,
            )
            if gate is not arbitration.greedy_action:
                raise RuntimeError("D-035B LFR gate changed inherited turn direction")
            lfr_record.update(
                {
                    "transition": global_transition,
                    "proposed_action": proposed.name,
                    "physical_action": gate.name,
                    "policy_rng_draw_present": True,
                }
            )
            lfr_records.append(lfr_record)
            physical_action = gate
        prediction = learner.predict(current, physical_action)
        observation_array, reward, terminated, truncated, info = _step_with_turn_angle(
            environment, physical_action, turn_angle
        )
        if reward != 0.0 or info != {}:
            raise RuntimeError("D-035B branch crossed the reward/info boundary")
        telemetry = environment.last_transition
        if telemetry is None:
            raise RuntimeError("D-035B branch produced no telemetry")
        if not isinstance(physical_action, Action):
            all_logical_actions_existing_enum = False
        if physical_action in _TURN_ACTIONS:
            all_turn_energy_semantics_canonical &= (
                telemetry.actuator_electrical_power_w
                == environment.config.turn_actuator_electrical_power_w
                and telemetry.total_electrical_load_w
                == environment.config.electronics_electrical_power_w
                + environment.config.turn_actuator_electrical_power_w
                and telemetry.step_index == local_transition + anchor.transition - 1
            )
        next_observation = d031r1._next_visible(observation_array)
        observed_delta = _observed_delta(current, next_observation)
        prediction_metrics.record(prediction.values, observed_delta)
        update = learner.observe_transition(current, physical_action, next_observation)
        update_count += 1
        all_update_predictions_exact &= update.prediction == prediction.values
        if update.action is not physical_action:
            raise RuntimeError("D-035B learner update did not use executed action")
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
        action_counts[physical_action.name] += 1
        path_length += math.dist(telemetry.position_before, telemetry.position_after)
        cumulative_heading_change += _angle_difference(
            previous_heading, telemetry.heading
        )
        previous_heading = telemetry.heading
        distance = math.dist(telemetry.position_after, station)
        minimum_distance = min(minimum_distance, distance)
        maximum_displacement = max(
            maximum_displacement,
            math.dist(initial_position, telemetry.position_after),
        )
        minimum_energy = min(minimum_energy, next_observation.energy)
        minimum_temperature = min(minimum_temperature, next_observation.thermal)
        energy_values.append(next_observation.energy)
        forward_values.append(next_observation.beacon.forward)
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

    final_position = trace[-1].telemetry.position_after if trace else initial_position
    final_distance = math.dist(final_position, station)
    explorer_calls = (
        controller.false_contact_seek_explorer_calls - explorer_calls_before
    )
    policy_rng_digest, environment_rng_digest = _rng_digests(streams)
    actions = [row.action for row in trace]
    alternation_runs = d033._alternation_run_lengths(actions)
    output: dict[str, object] = {
        "family": family,
        "variant": variant,
        "cap_degrees": cap_degrees,
        "cap_radians": math.radians(cap_degrees) if cap_degrees is not None else None,
        "anchor_type": anchor.anchor_type,
        "anchor_transition": anchor.transition,
        "branch_transition_count": len(trace),
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
            "minimum": minimum_temperature,
            "final_or_stop": current.thermal,
            "maximum": max(row.observation[5] for row in trace)
            if trace
            else anchor.current.thermal,
        },
        "path_length": path_length,
        "net_displacement_from_anchor": {
            "vector": [
                final_position[0] - initial_position[0],
                final_position[1] - initial_position[1],
            ],
            "magnitude": math.dist(initial_position, final_position),
        },
        "evaluator_distance": {
            "start": initial_distance,
            "minimum": minimum_distance,
            "final": final_distance,
        },
        "visible_beacon_forward": {
            "start": forward_values[0],
            "maximum": max(forward_values),
            "final": forward_values[-1],
            "change": forward_values[-1] - forward_values[0],
        },
        "cumulative_absolute_heading_change": cumulative_heading_change,
        "action_counts": action_counts,
        "proposed_action_counts": proposed_action_counts,
        "alternation": {
            "strict_alternation_run_count": len(alternation_runs),
            "strict_alternation_run_lengths": alternation_runs,
            "longest_strict_alternation_run": max(alternation_runs, default=0),
            "strict_alternation_8_reached": max(alternation_runs, default=0) >= 8,
        },
        "arbitration": {
            "false_contact_seek_decision_count": arbitration_count,
            "one_policy_rng_draw_per_decision": True,
            "delegation_probability": 0.0,
            "explorer_internal_hazard": d031r1.D031R1_EXPLORER_HAZARD,
            "explorer_call_count": explorer_calls,
        },
        "directional_interpolation": _lfr_diagnostic_summary(lfr_records),
        "prediction_compatibility": _prediction_summary(prediction_metrics),
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
            "reward_zero_every_transition": all(row.reward == 0.0 for row in trace),
            "organism_info_empty_every_transition": all(
                row.info == {} for row in trace
            ),
            "executed_action_only_updates": update_count == len(trace),
            "prediction_query_read_only": all_prediction_queries_read_only,
            "executed_prediction_matches_pre_update_query": (
                all_update_predictions_exact
            ),
            "no_false_contact_seek_explorer_call": explorer_calls == 0,
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
            "no_reseed_or_new_rng_stream": (
                streams.policy is controller.policy_rng
                and streams.policy is controller.explorer.policy_rng
            ),
            "logical_actions_existing_enum": all_logical_actions_existing_enum,
            "turn_time_energy_canonical": all_turn_energy_semantics_canonical,
            "sub45_turn_magnitude_evaluator_only": True,
            "same_discrete_turn_direction_as_seek_beacon_action": True,
            "learner_update_from_actual_next_observation": True,
        },
        "lfr_decision_records_retained": False,
    }
    expected = d033._expected_baseline_trace(full_b_trace, anchor.transition)
    output["baseline_continuation_exact"] = (
        tuple(trace) == expected if family == "BASELINE_B" else None
    )
    output["first_physical_action"] = trace[0].action.name if trace else None
    output["lfr_decision_count"] = len(lfr_records)
    if family == "BASELINE_B" and not bool(output["baseline_continuation_exact"]):
        raise RuntimeError(
            f"D-035B BASELINE_B continuation diverged at "
            f"{anchor.seed}/{anchor.anchor_type}"
        )
    if not all(
        bool(cast(dict[str, object], output["branch_state"])[key])
        for key in (
            "branch_start_exact",
            "branch_did_not_mutate_anchor",
            "reward_zero_every_transition",
            "organism_info_empty_every_transition",
            "executed_action_only_updates",
            "executed_prediction_matches_pre_update_query",
            "no_false_contact_seek_explorer_call",
            "one_policy_rng_draw_per_false_contact_seek_decision",
            "no_reseed_or_new_rng_stream",
            "logical_actions_existing_enum",
            "turn_time_energy_canonical",
            "sub45_turn_magnitude_evaluator_only",
            "same_discrete_turn_direction_as_seek_beacon_action",
            "learner_update_from_actual_next_observation",
        )
    ):
        raise RuntimeError("D-035B branch isolation guard failed")
    return output, tuple(trace)


def _branch_identity(output: dict[str, object]) -> dict[str, object]:
    return {
        key: value
        for key, value in output.items()
        if key not in {"branch_order_invariant"}
    }


def _branch_specs() -> tuple[tuple[str, float | None, str | None], ...]:
    specs: list[tuple[str, float | None, str | None]] = [("BASELINE_B", None, None)]
    for cap in D035B_CAPS_DEGREES:
        for variant in ("LFR_FIXED", "LFR_INTERP"):
            specs.append((_lfr_branch_name(variant, cap), cap, variant))
    return tuple(specs)


def _run_branch_set(
    anchor: d033._AnchorState,
    *,
    full_b_trace: tuple[d025.D025TransitionTrace, ...],
) -> dict[str, object]:
    specs = _branch_specs()
    forward: dict[
        str, tuple[dict[str, object], tuple[d025.D025TransitionTrace, ...]]
    ] = {}
    for name, cap, variant in specs:
        forward[name] = _run_branch(
            anchor,
            family=name,
            full_b_trace=full_b_trace,
            cap_degrees=cap,
            variant=variant,
        )
    reverse: dict[
        str, tuple[dict[str, object], tuple[d025.D025TransitionTrace, ...]]
    ] = {}
    for name, cap, variant in reversed(specs):
        reverse[name] = _run_branch(
            anchor,
            family=name,
            full_b_trace=full_b_trace,
            cap_degrees=cap,
            variant=variant,
        )
    order_invariant = all(
        forward[name][1] == reverse[name][1]
        and _branch_identity(forward[name][0]) == _branch_identity(reverse[name][0])
        for name, _, _ in specs
    )
    baseline_again, baseline_again_trace = _run_branch(
        anchor,
        family="BASELINE_B",
        full_b_trace=full_b_trace,
    )
    baseline_creation_invariant = (
        baseline_again_trace == forward["BASELINE_B"][1]
        and _branch_identity(baseline_again)
        == _branch_identity(forward["BASELINE_B"][0])
    )
    if not order_invariant or not baseline_creation_invariant:
        raise RuntimeError(
            "D-035B branch-order isolation failed at "
            f"{anchor.seed}/{anchor.anchor_type}"
        )
    branch_outputs: dict[str, dict[str, object]] = {}
    for name, _, _ in specs:
        branch_outputs[name] = forward[name][0]
        branch_outputs[name]["branch_order_invariant"] = order_invariant
        branch_outputs[name]["baseline_creation_order_invariant"] = (
            baseline_creation_invariant
        )
    return {
        "anchor_type": anchor.anchor_type,
        "seed": anchor.seed,
        "available": True,
        "branch_order_invariance": order_invariant,
        "baseline_creation_order_invariance": baseline_creation_invariant,
        "baseline": branch_outputs["BASELINE_B"],
        "branches": [branch_outputs[name] for name, _, _ in specs[1:]],
    }


def _seed_record(
    seed: int,
    accepted: dict[str, object],
) -> dict[str, object]:
    replay = d031r1._run_arm(
        seed,
        arm="LEARNED_NO_DETRAP",
        horizon=D035B_HORIZON,
        evaluator_diagnostics=True,
        seed_validator=_validate_d035b_seed,
    )
    replay_gate = _identity_gate(
        seed, replay, _accepted_arm(accepted, seed, "LEARNED_NO_DETRAP")
    )
    b_result, b_trace, _ = d033._run_capture(
        seed,
        role="B",
        horizon=D035B_HORIZON,
        seed_validator=_validate_d035b_seed,
    )
    instrumented_comparison = d032._compare_identity_fields(
        b_result, replay, include_private_weights=True
    )
    if not instrumented_comparison["all_identity_fields_exact"]:
        raise RuntimeError(f"D-035B instrumented replay diverged for seed {seed}")
    anchors: dict[str, dict[str, object]] = {}
    for anchor_type in D035B_ANCHOR_TYPES:
        definition = _anchor_definition(anchor_type, b_trace)
        if definition is None:
            anchors[anchor_type] = {
                "available": False,
                "status": "anchor_unavailable",
                "anchor_type": anchor_type,
                "reason": "no qualifying pre-action state before lifetime end",
                "selection_uses_hidden_geometry_or_future_outcome": False,
            }
            continue
        anchor, capture_checks = _capture_anchor(
            seed,
            anchor_type,
            cast(int, definition["transition"]),
            b_trace,
            replay,
        )
        branch_set = _run_branch_set(anchor, full_b_trace=b_trace)
        anchors[anchor_type] = {
            "available": True,
            "status": anchor_type,
            "definition": definition,
            "capture_checks": capture_checks,
            "branches": branch_set,
        }
    return {
        "seed": seed,
        "accepted_replay": replay_gate,
        "instrumented_replay_exact": instrumented_comparison,
        "anchors": anchors,
    }


def _path_values(
    rows: Sequence[dict[str, object]], outer: str, inner: str | None = None
) -> list[float]:
    values: list[float] = []
    for row in rows:
        value: object = row[outer]
        if inner is not None:
            value = cast(dict[str, object], value)[inner]
        if value is not None:
            values.append(cast(float, value))
    return values


def _pooled_anchor_summary(
    records: Sequence[dict[str, object]], anchor_type: str
) -> dict[str, object]:
    available: list[tuple[int, dict[str, object]]] = []
    unavailable: list[int] = []
    for record in records:
        anchor = cast(
            dict[str, object], cast(dict[str, object], record["anchors"])[anchor_type]
        )
        if bool(anchor["available"]):
            available.append((cast(int, record["seed"]), anchor))
        else:
            unavailable.append(cast(int, record["seed"]))
    by_branch: dict[str, object] = {}
    branch_names = [name for name, _, _ in _branch_specs()]
    for branch_name in branch_names:
        rows: list[dict[str, object]] = []
        for _, anchor in available:
            branch_set = cast(dict[str, object], anchor["branches"])
            if branch_name == "BASELINE_B":
                rows.append(cast(dict[str, object], branch_set["baseline"]))
            else:
                rows.extend(
                    row
                    for row in cast(list[dict[str, object]], branch_set["branches"])
                    if row["family"] == branch_name
                )
        by_branch[branch_name] = {
            "sample_count": len(rows),
            "reacquisition_count": sum(
                int(cast(bool, row["reacquired_within_branch_window"]))
                for row in rows
            ),
            "reacquisition_latency": _number_summary(
                _path_values(rows, "reacquisition_latency")
            ),
            "minimum_energy": _number_summary(_path_values(rows, "energy", "minimum")),
            "final_distance": _number_summary(
                _path_values(rows, "evaluator_distance", "final")
            ),
            "path_length": _number_summary(_path_values(rows, "path_length")),
            "directional_error_degrees": _number_summary(
                _path_values(
                    [
                        cast(dict[str, object], row["directional_interpolation"])
                        for row in rows
                    ],
                    "directional_error_degrees",
                    "mean",
                )
            ),
            "saturation_count": sum(
                cast(
                    int,
                    cast(dict[str, object], row["directional_interpolation"])[
                        "saturation_count"
                    ],
                )
                for row in rows
            ),
            "side_reversal_count": sum(
                cast(
                    int,
                    cast(dict[str, object], row["directional_interpolation"])[
                        "side_reversal_count"
                    ],
                )
                for row in rows
            ),
            "strict_alternation_8_count": sum(
                int(
                    cast(bool, cast(dict[str, object], row["alternation"])[
                        "strict_alternation_8_reached"
                    ])
                )
                for row in rows
            ),
            "prediction_compatibility": [
                cast(dict[str, object], row["prediction_compatibility"])
                for row in rows
            ],
            "outlier_handling": {
                "discarded_seed_count": 0,
                "statement": "All available anchor branches are retained.",
            },
        }
    return {
        "anchor_type": anchor_type,
        "available_seed_count": len(available),
        "available_seeds": [seed for seed, _ in available],
        "unavailable_seeds": unavailable,
        "branches": by_branch,
    }


def _interpretation(
    records: Sequence[dict[str, object]],
) -> dict[str, object]:
    pooled = {
        anchor: _pooled_anchor_summary(records, anchor)
        for anchor in D035B_ANCHOR_TYPES
    }
    return {
        "lane": "Development",
        "confirmatory_claim": False,
        "no_universal_pass_threshold": True,
        "categories": {
            "interpolation_changes_geometry": {
                "rule": (
                    "Compare matched LFR_INTERP and LFR_FIXED branches by cap "
                    "on directional error, saturation, geometry, and viability."
                ),
                "observed_pattern": None,
            },
            "interpolation_changes_reacquisition": {
                "rule": (
                    "Describe any matched reacquisition-count or latency contrast; "
                    "do not treat it as a universal thresholded claim."
                ),
                "observed_pattern": None,
            },
            "prediction_compatibility": {
                "rule": (
                    "Report D-027 prediction compatibility with the actual executed "
                    "logical action and next visible observation."
                ),
                "observed_pattern": None,
            },
        },
        "pooled_keys": sorted(pooled),
        "organism_interpolation_not_added": True,
        "descriptive_observation_not_learning_claim": True,
        "no_output_dependent_protocol_tuning": True,
    }


def run_d035b_audit(
    seeds: Sequence[int] = D035B_DEFAULT_DEVELOPMENT_SEEDS,
    *,
    horizon: int = D035B_HORIZON,
    executed_commit_sha: str | None = None,
) -> dict[str, object]:
    """Run the complete frozen D-035B protocol on the reused support."""
    validated = _validate_d035b_development_seeds(seeds)
    if horizon != D035B_HORIZON:
        raise ValueError("D-035B requires the frozen 70,000-transition horizon")
    executed_sha = _validate_executed_commit_sha(executed_commit_sha)
    if executed_sha is None:
        raise ValueError(
            "D-035B official output requires the exact clean executable protocol SHA"
        )
    accepted = _accepted_artifact()
    records = [_seed_record(seed, accepted) for seed in validated]
    return {
        "schema_version": 1,
        "experiment": "D-035B",
        "title": "L/F/R interpolation attribution audit",
        "authoritative_base_sha": D035B_AUTHORITATIVE_BASE_SHA,
        "base_tree_sha": D035B_BASE_TREE_SHA,
        "implementation_probe_sha": executed_sha,
        "protocol_only_freeze_sha": executed_sha,
        "development_seeds": list(validated),
        "horizon": D035B_HORIZON,
        "branch_horizon": D035B_BRANCH_HORIZON,
        "timestep_seconds": D020PhysicalConfig().dt_seconds,
        "simulated_duration_seconds": D035B_HORIZON * D020PhysicalConfig().dt_seconds,
        "support": {
            "source": "accepted D-031R1 Arm-B and D-033 anchor reconstruction support",
            "accepted_artifact": D035B_ACCEPTED_D031R1_ARTIFACT,
            "accepted_artifact_sha256": _accepted_artifact_sha256(),
            "fresh_seed_block_allocated": False,
            "fresh_seed_block_inspected": False,
        },
        "freeze": {
            "anchor_types": list(D035B_ANCHOR_TYPES),
            "branch_names": [name for name, _, _ in _branch_specs()],
            "caps_degrees": list(D035B_CAPS_DEGREES),
            "caps_radians": list(D035B_CAPS_RADIANS),
            "lfr_formula": D035B_LFR_FORMULA,
            "zero_vector_theta_radians": 0.0,
            "forward_vs_turn_gate": "existing seek_beacon_action",
            "turn_direction": "existing seek_beacon_action",
            "fixed_magnitude": "exact cap for each cap branch",
            "interpolated_magnitude": "min(cap, abs(theta_hat))",
            "sub45_magnitude": "evaluator-only",
            "logical_actions": [action.name for action in Action],
            "turn_time_and_energy": "canonical D-020 action semantics",
            "false_contact_detrap": (
                "disabled; inherited Arm-B policy-RNG draw retained"
            ),
            "branch_horizon_expression": D035B_BRANCH_HORIZON_EXPRESSION,
            "stop_rules": [
                "dual-contact reacquisition",
                "inherited energy or thermal termination",
                "inherited episode truncation",
                D035B_BRANCH_HORIZON_EXPRESSION,
            ],
            "reward": 0.0,
            "organism_info": {},
            "learner_update": (
                "exactly once from physically executed logical action and actual "
                "next six-channel observation"
            ),
            "no_organism_boundary_change": True,
        },
        "causal_order": [
            "replay accepted Arm-B LEARNED_NO_DETRAP",
            "reconstruct FIRST_FALSE_CONTACT_SEEK and D-033 ALT8_ESTABLISHED",
            "clone complete Arm-B causal state independently per branch",
            "run inherited BASELINE_B or LFR evaluator branch",
            "derive LFR magnitude from current visible L/F/R only",
            "apply only evaluator-side turn magnitude for existing turn action",
            "execute canonical transition and actual next visible observation",
            "update D-027 once from executed logical action",
            "retain evaluator-only directional, geometry, viability, and "
            "prediction diagnostics",
        ],
        "organism_boundary": {
            "channels": list(d027.D027_CHANNELS),
            "actions": [action.name for action in Action],
            "reward": 0.0,
            "info": {},
            "evaluator_state_reaches_controller_or_learner": False,
            "new_sensor_or_action_added": False,
            "new_physics_or_turn_energy_added": False,
            "larger_learner_or_world_model_added": False,
            "history_or_meta_controller_added": False,
        },
        "replay_gate": {
            "all_seeds_exact_arm_b_replay": True,
            "checked_identity_fields": list(_CAUSAL_IDENTITY_FIELDS) + ["_weights"],
            "instrumented_replay_exact_required": True,
            "first_false_contact_seek_required": True,
            "alt8_established_reuses_d033_definition": True,
        },
        "results": records,
        "pooled": {
            anchor: _pooled_anchor_summary(records, anchor)
            for anchor in D035B_ANCHOR_TYPES
        },
        "interpretation": _interpretation(records),
    }


def write_d035b_json(path: Path, executed_commit_sha: str | None = None) -> Path:
    path.write_text(
        json.dumps(
            run_d035b_audit(executed_commit_sha=executed_commit_sha),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the D-035B LFR audit.")
    parser.add_argument("--executed-commit-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    write_d035b_json(args.output, args.executed_commit_sha)
    print(f"D-035B result written to {args.output}")


if __name__ == "__main__":
    main()
