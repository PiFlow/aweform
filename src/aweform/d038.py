"""D-038 evaluator-only combined fine-turn/interpolation/reverse audit.

This module composes the accepted D-035B and D-035C evaluator mechanics.  It
does not add an organism action, sensor, memory, or learner state: reverse is
represented only by a local evaluator label and all turn magnitudes are
applied by temporarily replacing the physical turn angle on a cloned
environment.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import pickle
from collections.abc import Sequence
from pathlib import Path
from typing import Final, cast

from . import d025, d026, d027, d029, d031r1, d033, d035a, d035b, d035c
from .env import Action
from .exp003_seed_policy import validate_exp003_development_seeds

D038_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = tuple(range(18468, 18488))
D038_HORIZON: Final[int] = 70_000
D038_BRANCH_HORIZON: Final[int] = 4_096
D038_ANCHORS: Final[tuple[str, ...]] = (
    "FIRST_FALSE_CONTACT_SEEK",
    "ALT8_ESTABLISHED",
    "FIRST_POST_CONTACT_LOSS",
)
D038_TREATMENTS: Final[tuple[str, ...]] = (
    "T0_BASELINE_B",
    "T1_FINE_5_FIXED",
    "T2_FINE_5_INTERP",
    "T3_FULL_COMBINED_5",
    "T4_FULL_COMBINED_2",
)
D038_CAPS: Final[dict[str, float | None]] = {
    "T0_BASELINE_B": None,
    "T1_FINE_5_FIXED": 5.0,
    "T2_FINE_5_INTERP": 5.0,
    "T3_FULL_COMBINED_5": 5.0,
    "T4_FULL_COMBINED_2": 2.0,
}
D038_LFR_FORMULA: Final[str] = (
    "x=F+cos(pi/4)*(L+R); y=sin(pi/4)*(L-R); "
    "theta_hat=atan2(y,x); zero vector theta_hat=0"
)
D038_PREDICTION_WINDOWS: Final[tuple[tuple[str, int, int], ...]] = (
    ("1..16", 1, 16),
    ("17..64", 17, 64),
    ("65..256", 65, 256),
    ("257..1024", 257, 1024),
    ("1025..4096", 1025, 4096),
)


def _validate_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    validated = validate_exp003_development_seeds(seeds)
    if validated != D038_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-038 requires exactly the reused development seeds "
            f"{D038_DEFAULT_DEVELOPMENT_SEEDS}; got {validated}"
        )
    return validated


def _validate_seed(seed: int) -> None:
    validated = validate_exp003_development_seeds((seed,))
    if validated[0] not in D038_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-038 may execute only the reused development seeds "
            f"{D038_DEFAULT_DEVELOPMENT_SEEDS}; got {validated[0]}"
        )


def _validate_executed_commit_sha(value: str | None) -> str:
    validated = d031r1._validate_executed_commit_sha(value)
    if validated is None:
        raise ValueError("D-038 official output requires an exact clean protocol SHA")
    return validated


def _digest(value: object) -> str:
    return hashlib.sha256(pickle.dumps(value, protocol=5)).hexdigest()


def _lfr_magnitude(
    observation: d027.D027Observation, cap: float, variant: str
) -> float:
    vector = d035b._lfr_vector(observation)
    return d035b._lfr_turn_magnitude(vector, cap_degrees=cap, variant=variant)


def _reverse_selection(
    reductions: dict[str, float],
) -> tuple[bool, float, float, bool]:
    """Return selection, reverse reduction, best canonical reduction, and tie."""
    reverse_reduction = reductions[d035c.D035C_REVERSE_LABEL]
    best_canonical = max(reductions[action.name] for action in Action)
    tie = reverse_reduction == best_canonical
    return reverse_reduction > best_canonical, reverse_reduction, best_canonical, tie


def _candidate_outcomes(
    environment: d026.D026Env,
    current: d027.D027Observation,
    cap: float,
    order: Sequence[str],
) -> tuple[dict[str, d035c._CandidateOutcome], dict[str, object]]:
    labels = tuple(action.name for action in Action) + (d035c.D035C_REVERSE_LABEL,)
    if tuple(sorted(order)) != tuple(sorted(labels)):
        raise ValueError(
            "D-038 candidate order must contain all canonical and reverse candidates"
        )
    before = d029._environment_state(environment)
    outcomes: dict[str, d035c._CandidateOutcome] = {}
    source_body = environment.body
    station = environment.station_center
    if source_body is None or station is None:
        raise RuntimeError("D-038 candidate requires evaluator geometry")
    for label in order:
        branch = d029._clone_environment(environment)
        start = d035c._geometry(source_body.position, source_body.heading, station)
        if label == d035c.D035C_REVERSE_LABEL:
            observation_array, _, terminated, truncated, info = d035c._reverse_step(
                branch
            )
            action = Action.MOVE_FORWARD
        else:
            action = Action[label]
            turn = (
                _lfr_magnitude(current, cap, "LFR_INTERP")
                if action in (Action.TURN_LEFT, Action.TURN_RIGHT)
                else None
            )
            observation_array, _, terminated, truncated, info = (
                d035b._step_with_turn_angle(branch, action, turn)
            )
        if info != {}:
            raise RuntimeError("D-038 candidate crossed the info boundary")
        telemetry = branch.last_transition
        if telemetry is None:
            raise RuntimeError("D-038 candidate produced no telemetry")
        observation = d031r1._next_visible(observation_array)
        end = d035c._geometry(
            telemetry.position_after, telemetry.heading, telemetry.station_center
        )
        displacement = math.dist(telemetry.position_before, telemetry.position_after)
        outcomes[label] = d035c._CandidateOutcome(
            label=label,
            action=action,
            observation=observation,
            terminated=terminated,
            truncated=truncated,
            telemetry=telemetry,
            delta=d035c._observed_delta(current, observation),
            actual_displacement=displacement,
            displacement_class=d035c._displacement_class(displacement),
            start_geometry=start,
            end_geometry=end,
        )
    return outcomes, {
        "source_environment_unchanged": d029._environment_state(environment) == before,
        "candidate_order": list(order),
    }


def _combined_branch(
    anchor: d033._AnchorState,
    treatment: str,
) -> tuple[dict[str, object], tuple[d025.D025TransitionTrace, ...]]:
    cap = cast(float, D038_CAPS[treatment])
    anchor_before = d033._anchor_fingerprint(anchor)
    environment = d029._clone_environment(anchor.environment)
    streams = copy.deepcopy(anchor.streams)
    controller = d033._rewire_controller_rng(anchor.controller, streams.policy)
    learner = d033._learner_from_weights(anchor.learner_weights)
    current = anchor.current
    expected = d033._state_fingerprint(
        anchor.environment,
        d033._rewire_controller_rng(anchor.controller, streams.policy),
        streams,
        learner,
        current,
    )
    start = d033._state_fingerprint(environment, controller, streams, learner, current)
    if start != expected:
        raise RuntimeError("D-038 combined branch clone did not preserve causal state")
    trace: list[d025.D025TransitionTrace] = []
    prediction = d035b._PredictionDiagnostics()
    update_digest = hashlib.sha256()
    update_count = 0
    reverse_count = 0
    false_seek_count = 0
    reverse_records: list[dict[str, object]] = []
    lfr_records: list[dict[str, object]] = []
    actions: list[Action] = []
    proposed_actions: list[str] = []
    geometries: list[dict[str, object]] = []
    energy_values = [current.energy]
    thermal_values = [current.thermal]
    forward_values = [current.beacon.forward]
    path_length = 0.0
    cumulative_signed_angle = 0.0
    cumulative_absolute_angle = 0.0
    entries = exits = 0
    stop_reason = "incomplete"
    terminated = truncated = False
    reacquisition: int | None = None
    reacquisition_geometry: dict[str, object] | None = None
    body = environment.body
    station = environment.station_center
    if body is None or station is None:
        raise RuntimeError("D-038 combined branch lacks geometry")
    geometries.append(d035c._geometry(body.position, body.heading, station))
    previous_turn_side: Action | None = None
    direction_counts = {name: 0 for name in d035c.D035C_CANDIDATES}
    clipping_counts = {
        "FORWARD": {"FULL_NOMINAL": 0, "BOUNDARY_CLIPPED": 0, "FULL_STALL": 0},
        "REVERSE": {"FULL_NOMINAL": 0, "BOUNDARY_CLIPPED": 0, "FULL_STALL": 0},
    }
    isolation = {
        "source_state_immutable": True,
        "candidate_order_invariant": True,
        "policy_rng_unchanged": True,
        "environment_rng_unchanged": True,
        "learner_unchanged_by_candidate_evaluation": True,
        "learner_unchanged_on_reverse_intervention": True,
        "canonical_update_once": True,
        "no_reverse_identity_in_learner": True,
    }
    for local in range(1, D038_BRANCH_HORIZON + 1):
        global_transition = anchor.transition + local - 1
        mode_before = controller.mode
        heading_before = body.heading
        proposed, arbitration = d035c._propose_b_action(controller, learner, current)
        proposed_actions.append(proposed.name)
        physical: Action | str = proposed
        turn_angle: float | None = None
        lfr_record: dict[str, object] | None = None
        false_seek = mode_before is d026.D026Mode.SEEK and not current.charging_contact
        false_seek_count += int(false_seek)
        learner_before = learner.weights
        rng_before = d029._rng_state(streams)
        if arbitration is not None:
            gate, turn_angle, lfr_record, previous_turn_side = d035b._lfr_action(
                current,
                cap_degrees=cap,
                variant="LFR_INTERP",
                environment=environment,
                previous_turn_side=previous_turn_side,
            )
            if gate is not arbitration.greedy_action:
                raise RuntimeError(
                    "D-038 interpolation changed inherited turn direction"
                )
            physical = gate
        if false_seek:
            labels = tuple(action.name for action in Action) + (
                d035c.D035C_REVERSE_LABEL,
            )
            outcomes, first_check = _candidate_outcomes(
                environment, current, cap, labels
            )
            reversed_outcomes, second_check = _candidate_outcomes(
                environment, current, cap, tuple(reversed(labels))
            )
            isolation["source_state_immutable"] &= bool(
                first_check["source_environment_unchanged"]
            )
            isolation["candidate_order_invariant"] &= all(
                d035c._candidate_identity(outcomes[label])
                == d035c._candidate_identity(reversed_outcomes[label])
                for label in labels
            )
            isolation["policy_rng_unchanged"] &= rng_before == d029._rng_state(streams)
            isolation["environment_rng_unchanged"] &= rng_before == d029._rng_state(
                streams
            )
            isolation["learner_unchanged_by_candidate_evaluation"] &= (
                learner.weights == learner_before
            )
            reductions = {
                label: cast(
                    float,
                    d035c._candidate_record(outcome, geometries[-1])[
                        "rear_contact_max_pair_error_reduction"
                    ],
                )
                for label, outcome in outcomes.items()
            }
            selected_reverse, reverse_reduction, best_canonical, tie = (
                _reverse_selection(reductions)
            )
            margin = reverse_reduction - best_canonical
            reverse_records.append(
                {
                    "transition": global_transition,
                    "proposed_canonical_action": proposed.name,
                    "reverse_candidate_pair_error_reduction": reverse_reduction,
                    "best_treated_canonical_pair_error_reduction": best_canonical,
                    "strict_margin": margin,
                    "tie": tie,
                    "reverse_selected": selected_reverse,
                    "reverse_immediately_restored_dual_contact": bool(
                        outcomes[d035c.D035C_REVERSE_LABEL].observation.charging_contact
                    ),
                    "candidate_source_unchanged": bool(
                        first_check["source_environment_unchanged"]
                    ),
                    "candidate_order_invariant": isolation["candidate_order_invariant"],
                }
            )
            if selected_reverse:
                physical = d035c.D035C_REVERSE_LABEL  # evaluator-only label
                reverse_count += 1
        if physical == d035c.D035C_REVERSE_LABEL:
            observation_array, reward, terminated, truncated, info = (
                d035c._reverse_step(environment)
            )
            telemetry = environment.last_transition
            if telemetry is None:
                raise RuntimeError("D-038 reverse transition produced no telemetry")
            isolation["learner_unchanged_on_reverse_intervention"] &= (
                learner.weights == learner_before
            )
            trace_action = Action.MOVE_FORWARD
        else:
            trace_action = cast(Action, physical)
            prediction_values = learner.predict(current, trace_action).values
            observation_array, reward, terminated, truncated, info = (
                d035b._step_with_turn_angle(environment, trace_action, turn_angle)
            )
            telemetry = environment.last_transition
            if telemetry is None:
                raise RuntimeError("D-038 canonical transition produced no telemetry")
            next_observation = d031r1._next_visible(observation_array)
            prediction.record(
                prediction_values,
                d035b._observed_delta(current, next_observation),
                trace_action,
                local,
            )
            update = learner.observe_transition(current, trace_action, next_observation)
            update_count += 1
            isolation["canonical_update_once"] &= update.action is trace_action
            d031r1._update_digest(
                update_digest, global_transition, trace_action, update
            )
        if reward != 0.0 or info != {}:
            raise RuntimeError("D-038 branch crossed reward/info boundary")
        next_observation = d031r1._next_visible(observation_array)
        row = d025._make_trace(
            transition_index=global_transition,
            mode_before=mode_before,
            mode_after=controller.mode,
            action=trace_action,
            current=current,
            observation=observation_array,
            telemetry=telemetry,
            reward=reward,
            info=info,
        )
        trace.append(row)
        actions.append(trace_action)
        direction_counts[physical if isinstance(physical, str) else physical.name] += 1
        displacement = math.dist(telemetry.position_before, telemetry.position_after)
        actual_angle = d035b._wrap_angle(telemetry.heading - heading_before)
        if trace_action is Action.TURN_LEFT:
            cumulative_signed_angle += actual_angle
            cumulative_absolute_angle += abs(actual_angle)
        elif trace_action is Action.TURN_RIGHT:
            cumulative_signed_angle -= actual_angle
            cumulative_absolute_angle += abs(actual_angle)
        if trace_action is Action.MOVE_FORWARD:
            direction = (
                "REVERSE" if physical == d035c.D035C_REVERSE_LABEL else "FORWARD"
            )
            clipping_counts[direction][d035c._displacement_class(displacement)] += 1
        if telemetry.charging_contact_before and not telemetry.charging_contact_after:
            exits += 1
        if not telemetry.charging_contact_before and telemetry.charging_contact_after:
            entries += 1
            reacquisition = local
            reacquisition_geometry = d035c._geometry(
                telemetry.position_after, telemetry.heading, station
            )
        path_length += displacement
        current = next_observation
        energy_values.append(current.energy)
        thermal_values.append(current.thermal)
        forward_values.append(current.beacon.forward)
        geometries.append(
            d035c._geometry(telemetry.position_after, telemetry.heading, station)
        )
        if lfr_record is not None:
            lfr_record.update(
                {
                    "transition": global_transition,
                    "arm_b_would_have_executed_action": proposed.name,
                    "executed_logical_action": trace_action.name,
                    "actual_angular_displacement_radians": actual_angle,
                    "actual_angular_displacement_degrees": math.degrees(actual_angle),
                    "cap_saturated": bool(lfr_record.get("saturated", False)),
                    "reverse_selected": physical == d035c.D035C_REVERSE_LABEL,
                    "visible_beacon_after": {
                        "left": current.beacon.left,
                        "forward": current.beacon.forward,
                        "right": current.beacon.right,
                    },
                    "rear_contact_pair_error_before": geometries[-2],
                    "rear_contact_pair_error_after": geometries[-1],
                }
            )
            lfr_records.append(lfr_record)
        if reacquisition is not None:
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
    if not trace:
        raise RuntimeError("D-038 branch produced no transition")
    final = geometries[-1]
    output: dict[str, object] = {
        "family": treatment,
        "variant": "LFR_INTERP",
        "cap_degrees": cap,
        "cap_radians": math.radians(cap),
        "anchor_type": anchor.anchor_type,
        "anchor_transition": anchor.transition,
        "branch_transition_count": len(trace),
        "reacquired_within_branch_window": reacquisition is not None,
        "reacquisition_transition_from_anchor": reacquisition,
        "reacquisition_latency": reacquisition,
        "stop_reason": stop_reason,
        "terminated": terminated,
        "truncated": truncated,
        "energy": {
            "at_anchor": energy_values[0],
            "minimum": min(energy_values),
            "maximum": max(energy_values),
            "final": energy_values[-1],
            "at_reacquisition": energy_values[-1] if reacquisition else None,
        },
        "thermal": {
            "at_anchor": thermal_values[0],
            "minimum": min(thermal_values),
            "maximum": max(thermal_values),
            "final": thermal_values[-1],
            "at_reacquisition": thermal_values[-1] if reacquisition else None,
        },
        "rear_contact_pair_error_geometry": {
            "start": geometries[0],
            "minimum": min(
                geometries, key=lambda item: cast(float, item["max_pair_error"])
            ),
            "final": final,
            "at_reacquisition": reacquisition_geometry,
        },
        "evaluator_station_distance": {
            "start": geometries[0]["distance_to_station"],
            "minimum": min(cast(float, g["distance_to_station"]) for g in geometries),
            "final": final["distance_to_station"],
        },
        "path_length": path_length,
        "net_displacement": math.dist(
            tuple(cast(list[float], geometries[0]["position"])),
            tuple(cast(list[float], final["position"])),
        ),
        "action_counts": {
            name: sum(1 for action in actions if action.name == name)
            for name in tuple(action.name for action in Action)
        },
        "reverse_intervention_count": reverse_count,
        "reverse_interventions": reverse_records,
        "false_contact_seek_decision_count": false_seek_count,
        "forward_nominal_clipped_stall_counts": clipping_counts,
        "turn_count": sum(
            action in (Action.TURN_LEFT, Action.TURN_RIGHT) for action in actions
        ),
        "cumulative_signed_angle_radians": cumulative_signed_angle,
        "cumulative_absolute_angle_radians": cumulative_absolute_angle,
        "visible_beacon_forward": {
            "start": forward_values[0],
            "maximum": max(forward_values),
            "final": forward_values[-1],
            "change": forward_values[-1] - forward_values[0],
        },
        "contact_events": {
            "charging_contact_entry_count": entries,
            "charging_contact_exit_count": exits,
        },
        "lfr_decision_records": lfr_records,
        "prediction_compatibility": prediction.as_dict(),
        "executed_action_update_count": update_count,
        "executed_action_update_digest": update_digest.hexdigest(),
        "final_learner_state_digest": _digest(tuple(learner.weights)),
        "reverse_candidate_diagnostics": {
            "available": True,
            "records": reverse_records,
            "strict_better_only": True,
            "ties_rejected": True,
        },
        "branch_state": {
            **isolation,
            "branch_start_exact": start == expected,
            "branch_did_not_mutate_anchor": d033._anchor_fingerprint(anchor)
            == anchor_before,
            "reward_zero_every_transition": all(row.reward == 0.0 for row in trace),
            "organism_info_empty_every_transition": all(
                row.info == {} for row in trace
            ),
            "canonical_learner_update_count_matches": update_count
            == len(trace) - reverse_count,
            "logical_actions_existing_enum": all(row.action in Action for row in trace),
            "no_new_rng_stream": streams.policy is controller.policy_rng,
        },
        "provenance": {
            "reverse_is_evaluator_only": True,
            "reverse_has_no_action_enum_identity": True,
            "reverse_did_not_update_d027": True,
            "proposed_actions": proposed_actions,
        },
    }
    if not all(
        cast(bool, value)
        for value in cast(dict[str, object], output["branch_state"]).values()
    ):
        raise RuntimeError("D-038 combined branch isolation guard failed")
    return output, tuple(trace)


def _run_treatment(
    anchor: d033._AnchorState,
    treatment: str,
    full_trace: tuple[d025.D025TransitionTrace, ...],
) -> dict[str, object]:
    if treatment == "T0_BASELINE_B":
        output, _ = d035b._run_branch(
            anchor, family="BASELINE_B", full_b_trace=full_trace
        )
    elif treatment == "T1_FINE_5_FIXED":
        output, _ = d035b._run_branch(
            anchor,
            family="FINE_5_FIXED",
            full_b_trace=full_trace,
            cap_degrees=5.0,
            variant="LFR_FIXED",
        )
    elif treatment == "T2_FINE_5_INTERP":
        output, _ = d035b._run_branch(
            anchor,
            family="FINE_5_INTERP",
            full_b_trace=full_trace,
            cap_degrees=5.0,
            variant="LFR_INTERP",
        )
    else:
        output, _ = _combined_branch(anchor, treatment)
    output["treatment"] = treatment
    return output


def _causal_anchor_projection(record: dict[str, object]) -> dict[str, object]:
    """Project only cloned causal state, excluding a derived action proposal."""
    keys = (
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
        "alternation_eighth_transition",
    )
    return {key: record.get(key) for key in keys}


def _reconstruct_anchors(
    seed: int,
    accepted_d031r1: dict[str, object],
    accepted_d033: dict[str, object],
) -> tuple[
    dict[str, object],
    tuple[d025.D025TransitionTrace, ...],
    dict[str, d033._AnchorState | None],
    dict[str, dict[str, object]],
]:
    trace_list: list[d025.D025TransitionTrace] = []
    arm_b_result = d031r1._run_arm(
        seed,
        arm="LEARNED_NO_DETRAP",
        horizon=D038_HORIZON,
        evaluator_diagnostics=True,
        trace_sink=trace_list,
        seed_validator=_validate_seed,
    )
    replay_gate = d035c._identity_gate(
        seed,
        arm_b_result,
        d033._accepted_arm(accepted_d031r1, seed, "LEARNED_NO_DETRAP"),
    )
    trace = tuple(trace_list)
    anchors: dict[str, d033._AnchorState | None] = {}
    records: dict[str, dict[str, object]] = {}

    def capture(anchor_name: str, transition: int, require_seek: bool) -> None:
        anchor, checks = d035c._capture_anchor(
            seed, anchor_name, transition, arm_b_result, require_seek=require_seek
        )
        anchors[anchor_name] = anchor
        records[anchor_name] = d035c._anchor_record(
            anchor,
            {**checks, "seed": seed, "anchor_transition": transition},
        )

    first = d035c._first_false_contact_seek_transition(trace)
    if first is None:
        anchors[D038_ANCHORS[0]] = None
        records[D038_ANCHORS[0]] = {
            "available": False,
            "seed": seed,
            "status": "anchor_unavailable",
        }
    else:
        capture(D038_ANCHORS[0], first, True)

    alt8 = d033._find_alt8_transition(trace)
    accepted_seed = next(
        row
        for row in cast(list[dict[str, object]], accepted_d033["results"])
        if row["seed"] == seed
    )
    accepted_alt8 = cast(
        dict[str, object],
        cast(dict[str, object], accepted_seed["anchors"])[d033.D033_ANCHOR_B],
    )
    if alt8 is None:
        anchors[D038_ANCHORS[1]] = None
        records[D038_ANCHORS[1]] = {
            "available": False,
            "seed": seed,
            "status": "anchor_unavailable",
            "accepted_d033_anchor_identity_exact": not bool(accepted_alt8["available"]),
        }
    else:
        transition, eighth = alt8
        capture(D038_ANCHORS[1], transition, True)
        record = records[D038_ANCHORS[1]]
        record["alternation_eighth_transition"] = eighth
        record["strict_alternation_length"] = 8
        record["all_actions_false_contact_seek"] = True
        record["no_contact_within_eight_actions"] = True
        record["accepted_d033_anchor_identity_exact"] = _causal_anchor_projection(
            record
        ) == _causal_anchor_projection(accepted_alt8)
        record["accepted_d033_derived_proposal_mismatch"] = record.get(
            "b_proposed_action"
        ) != accepted_alt8.get("b_proposed_action")
        record["accepted_d033_anchor_projection"] = _causal_anchor_projection(
            accepted_alt8
        )
        if not cast(bool, record["accepted_d033_anchor_identity_exact"]):
            raise RuntimeError(f"D-038 ALT8 causal identity diverged for {seed}")

    post_loss = d035c._first_post_contact_loss_transition(trace)
    if post_loss is None:
        anchors[D038_ANCHORS[2]] = None
        records[D038_ANCHORS[2]] = {
            "available": False,
            "seed": seed,
            "status": "anchor_unavailable",
            "contact_loss_not_followed_by_available_pre_action_state": True,
        }
    else:
        capture(D038_ANCHORS[2], post_loss, False)
        records[D038_ANCHORS[2]]["selected_from_contact_loss_transition"] = (
            post_loss - 1
        )
    return replay_gate, trace, anchors, records


def _paired_comparisons(records: Sequence[dict[str, object]]) -> dict[str, object]:
    names = (
        ("T0_BASELINE_B", "T1_FINE_5_FIXED"),
        ("T1_FINE_5_FIXED", "T2_FINE_5_INTERP"),
        ("T2_FINE_5_INTERP", "T3_FULL_COMBINED_5"),
        ("T3_FULL_COMBINED_5", "T4_FULL_COMBINED_2"),
        ("T0_BASELINE_B", "T3_FULL_COMBINED_5"),
        ("T0_BASELINE_B", "T4_FULL_COMBINED_2"),
    )
    result: dict[str, object] = {}
    by_name = {cast(str, row["treatment"]): row for row in records}
    for left, right in names:
        left_row = by_name[left]
        right_row = by_name[right]
        result[f"{left}_vs_{right}"] = {
            "left_reacquired": left_row["reacquired_within_branch_window"],
            "right_reacquired": right_row["reacquired_within_branch_window"],
            "left_latency": left_row["reacquisition_latency"],
            "right_latency": right_row["reacquisition_latency"],
            "reacquisition_difference": int(
                cast(bool, right_row["reacquired_within_branch_window"])
            )
            - int(cast(bool, left_row["reacquired_within_branch_window"])),
        }
    return result


def run_d038_audit(
    *,
    seeds: Sequence[int] = D038_DEFAULT_DEVELOPMENT_SEEDS,
    horizon: int = D038_HORIZON,
    executed_commit_sha: str | None = None,
) -> dict[str, object]:
    validated = _validate_seeds(seeds)
    if horizon != D038_HORIZON:
        raise ValueError("D-038 requires the frozen 70,000-transition replay horizon")
    executed = _validate_executed_commit_sha(executed_commit_sha)
    accepted_d031r1 = d035a._accepted_artifact(d035c.D035C_ACCEPTED_D031R1_ARTIFACT)
    accepted_d033 = d035a._accepted_artifact(d035c.D035C_ACCEPTED_D033_ARTIFACT)
    results: list[dict[str, object]] = []
    for seed in validated:
        replay, trace, anchors, anchor_records = _reconstruct_anchors(
            seed, accepted_d031r1, accepted_d033
        )
        anchor_map: dict[str, object] = {}
        seed_row: dict[str, object] = {
            "seed": seed,
            "accepted_replay": replay,
            "anchors": anchor_map,
        }
        for anchor_name in D038_ANCHORS:
            anchor = anchors[anchor_name]
            if anchor is None:
                anchor_map[anchor_name] = {
                    "available": False,
                    **anchor_records[anchor_name],
                }
                continue
            treatment_rows = [
                _run_treatment(anchor, treatment, trace)
                for treatment in D038_TREATMENTS
            ]
            anchor_map[anchor_name] = {
                "available": True,
                "definition": anchor_records[anchor_name],
                "treatments": treatment_rows,
                "matched_comparisons": _paired_comparisons(treatment_rows),
            }
        results.append(seed_row)
    availability: dict[str, int] = {}
    for availability_anchor in D038_ANCHORS:
        availability[availability_anchor] = sum(
            bool(
                cast(
                    dict[str, object],
                    cast(dict[str, object], row["anchors"])[availability_anchor],
                )["available"]
            )
            for row in results
        )
    summary: dict[str, dict[str, object]] = {}
    for summary_anchor in D038_ANCHORS:
        summary[summary_anchor] = {}
        for treatment in D038_TREATMENTS:
            rows: list[dict[str, object]] = []
            for row in results:
                anchor_record = cast(
                    dict[str, object],
                    cast(dict[str, object], row["anchors"])[summary_anchor],
                )
                if not bool(anchor_record["available"]):
                    continue
                rows.extend(cast(list[dict[str, object]], anchor_record["treatments"]))
            matching = [row for row in rows if cast(str, row["treatment"]) == treatment]
            summary[summary_anchor][treatment] = {
                "available_count": len(matching),
                "reacquisition_count": sum(
                    bool(row["reacquired_within_branch_window"]) for row in matching
                ),
                "reverse_intervention_count": sum(
                    int(cast(int, row.get("reverse_intervention_count", 0)))
                    for row in matching
                ),
            }
    return {
        "schema_version": 1,
        "experiment": "D-038",
        "title": "Combined fine-turn + L/F/R interpolation + reverse sufficiency audit",
        "authoritative_base_sha": "b49531fe29cd5c0f83cec300369d9fd9d0c64700",
        "protocol_only_freeze_sha": executed,
        "implementation_probe_sha": executed,
        "development_seeds": list(validated),
        "horizon": D038_HORIZON,
        "branch_horizon": D038_BRANCH_HORIZON,
        "anchors": list(D038_ANCHORS),
        "treatments": list(D038_TREATMENTS),
        "caps_degrees": D038_CAPS,
        "lfr_formula": D038_LFR_FORMULA,
        "reverse_criterion": (
            "strictly greater rear-contact max-pair-error reduction than every "
            "treated canonical candidate; ties reject"
        ),
        "support": {
            "reused_development_seeds_only": True,
            "fresh_seed_block_allocated": False,
            "fresh_exp_work_started": False,
            "availability_counts": availability,
        },
        "results": results,
        "summary_by_anchor": summary,
        "interpretation": {
            "lane": "Development",
            "confirmatory_claim": False,
            "categories": [
                "joint sufficiency supported descriptively",
                "reverse adds conditional benefit",
                "interpolation adds conditional benefit",
                "fine-turn contribution",
                "2-degree sensitivity only",
                "joint insufficiency",
            ],
            "outcome_dependent_retuning": False,
        },
        "organism_boundary": {
            "actions": [action.name for action in Action],
            "channels": list(d027.D027_CHANNELS),
            "reward": 0.0,
            "info": {},
            "canonical_runtime_unchanged": True,
            "reverse_evaluator_only": True,
            "no_d039_or_exp_work_started": True,
        },
    }


def write_d038_json(path: Path, executed_commit_sha: str | None = None) -> Path:
    path.write_text(
        json.dumps(
            run_d038_audit(executed_commit_sha=executed_commit_sha),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the D-038 combined sufficiency audit."
    )
    parser.add_argument("--executed-commit-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    write_d038_json(args.output, args.executed_commit_sha)
    print(f"D-038 result written to {args.output}")


if __name__ == "__main__":
    main()
