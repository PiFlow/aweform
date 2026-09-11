"""D-035C evaluator-only reverse-translation sufficiency audit.

The accepted D-031R1 Arm-B organism is replayed without modification.  This
module evaluates a hypothetical reverse displacement only in cloned
evaluator state.  Reverse has no :class:`~aweform.env.Action` identity, is
never selected by the controller, and never receives a D-027 learner update.
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
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

import numpy as np

from . import d020, d024, d025, d026, d027, d029, d031r1, d032, d033, d035a
from .d020 import D020TransitionTelemetry
from .env import Action
from .exp003_seed_policy import validate_exp003_development_seeds
from .rng import RandomStreams

D035C_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = tuple(range(18468, 18488))
D035C_HORIZON: Final[int] = 70_000
D035C_BRANCH_HORIZON: Final[int] = 256
D035C_AUTHORITATIVE_BASE_SHA: Final[str] = "f694d47eb2c94cf3afbf07f327036234faceacea"
D035C_BASE_TREE_SHA: Final[str] = "c28b9debd8f666937fd57c0e3864d48be5135417"
D035C_ACCEPTED_D031R1_ARTIFACT: Final[str] = d032.D032_ACCEPTED_D031R1_ARTIFACT
D035C_ACCEPTED_D033_ARTIFACT: Final[str] = (
    "development/D-033-short-horizon-sequence-sufficiency-audit.json"
)
D035C_FIRST_ANCHOR: Final[str] = "FIRST_FALSE_CONTACT_SEEK"
D035C_ALT8_ANCHOR: Final[str] = "ALT8_ESTABLISHED"
D035C_POST_LOSS_ANCHOR: Final[str] = "FIRST_POST_CONTACT_LOSS"
D035C_ANCHORS: Final[tuple[str, ...]] = (
    D035C_FIRST_ANCHOR,
    D035C_ALT8_ANCHOR,
    D035C_POST_LOSS_ANCHOR,
)
D035C_CANDIDATES: Final[tuple[str, ...]] = (
    "WAIT",
    "TURN_LEFT",
    "TURN_RIGHT",
    "MOVE_FORWARD",
    "REVERSE_TRANSLATION",
)
D035C_CANONICAL_CANDIDATES: Final[tuple[Action, ...]] = tuple(Action)
D035C_REVERSE_LABEL: Final[str] = "REVERSE_TRANSLATION"
D035C_OUTPUTS: Final[tuple[str, ...]] = d027.D027_OUTPUTS
D035C_CHANNELS: Final[tuple[str, ...]] = d027.D027_CHANNELS
D035C_NOMINAL_REVERSE_DISTANCE: Final[float] = d027.D027_NOMINAL_MOVE_DISTANCE


def _validate_d035c_development_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    validated = validate_exp003_development_seeds(seeds)
    if validated != D035C_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-035C requires exactly the reused development seeds "
            f"{D035C_DEFAULT_DEVELOPMENT_SEEDS}; got {validated}"
        )
    return validated


def _validate_d035c_seed(seed: int) -> None:
    validated = validate_exp003_development_seeds((seed,))
    if validated[0] not in D035C_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-035C may execute only the reused development seeds "
            f"{D035C_DEFAULT_DEVELOPMENT_SEEDS}; got {validated[0]}"
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


def _visible(observation: d027.D027Observation) -> tuple[float, ...]:
    return (
        observation.energy,
        observation.beacon.left,
        observation.beacon.forward,
        observation.beacon.right,
        float(observation.charging_contact),
        observation.thermal,
    )


def _observed_delta(
    current: d027.D027Observation, next_observation: d027.D027Observation
) -> tuple[float, ...]:
    return tuple(
        right - left
        for left, right in zip(
            _visible(current), _visible(next_observation), strict=True
        )
    )


def _geometry(
    position: tuple[float, float], heading: float, station: tuple[float, float]
) -> dict[str, object]:
    plus, minus = d024.dual_contact_pair_errors(position, heading, station)
    return {
        "position": list(position),
        "heading": heading,
        "distance_to_station": math.dist(position, station),
        "rear_plus_pair_error": plus,
        "rear_minus_pair_error": minus,
        "max_pair_error": max(plus, minus),
    }


def _clamp(value: float, lower: float, upper: float) -> float:
    return min(upper, max(lower, value))


def _apply_reverse_translation(environment: d026.D026Env) -> float:
    """Apply the frozen inverse displacement and return actual displacement."""
    body = environment.body
    if body is None:
        raise RuntimeError("reverse candidate requires a reset environment")
    before = body.position
    distance = environment.config.movement_distance_world_units
    body.x = _clamp(
        body.x - distance * math.cos(body.heading),
        environment.config.world_min[0],
        environment.config.world_max[0],
    )
    body.y = _clamp(
        body.y - distance * math.sin(body.heading),
        environment.config.world_min[1],
        environment.config.world_max[1],
    )
    return math.dist(before, body.position)


def _reverse_step(
    environment: d026.D026Env,
) -> tuple[np.ndarray, float, bool, bool, dict[str, object]]:
    """Run one reverse candidate with canonical MOVE_FORWARD accounting.

    This is deliberately local to the evaluator.  The copied bookkeeping is
    the D-020 step equation with only the displacement sign changed; the
    telemetry action remains ``MOVE_FORWARD`` because reverse has no logical
    action identity.
    """
    if environment._episode_done:
        raise RuntimeError("episode is over; call reset() before reverse step")
    if (
        environment.body is None
        or environment.station_center is None
        or environment.body_temperature_c is None
    ):
        raise RuntimeError("environment must be reset before reverse step")
    body = environment.body
    config = environment.config
    selected_action = Action.MOVE_FORWARD
    position_before = body.position
    battery_before = environment._battery_j
    temperature_before = environment.body_temperature_c
    contact_before = environment.charging_contact
    energy_before = d020_normalize(battery_before, 0.0, config.battery_capacity_j)
    temperature_normalized_before = d020_normalize(
        temperature_before,
        config.visible_temperature_min_c,
        config.visible_temperature_max_c,
    )
    _apply_reverse_translation(environment)
    contact_after = environment.charging_contact
    actuator_electrical = config.move_actuator_electrical_power_w
    actuator_body_heat = config.move_actuator_body_heat_w
    total_electrical = config.electronics_electrical_power_w + actuator_electrical
    load_energy = total_electrical * config.dt_seconds
    charge = environment._charge_decision(contact_after, battery_before)
    requested_charge_energy = charge.requested_stored_power_w * config.dt_seconds
    max_accepted_charge_energy = max(
        0.0, config.battery_capacity_j - battery_before + load_energy
    )
    actual_charge_energy = min(requested_charge_energy, max_accepted_charge_energy)
    actual_stored_power = actual_charge_energy / config.dt_seconds
    battery_after = min(
        config.battery_capacity_j,
        max(0.0, battery_before + actual_charge_energy - load_energy),
    )
    termination_latched_after = charge.termination_latched_after
    if (
        charge.phase
        in (d020.ChargePhase.BULK, d020.ChargePhase.TAPER_1, d020.ChargePhase.TAPER_2)
        and battery_after >= config.battery_capacity_j
    ):
        termination_latched_after = True
    charger_input = (
        actual_stored_power / config.charge_efficiency
        if actual_stored_power > 0.0
        else 0.0
    )
    charging_heat = (
        charger_input - actual_stored_power if actual_stored_power > 0.0 else 0.0
    )
    total_body_heat = (
        config.electronics_body_heat_w + actuator_body_heat + charging_heat
    )
    environmental_exchange = config.thermal_conductance_w_per_k * (
        config.ambient_temperature_c - temperature_before
    )
    temperature_after = temperature_before + (
        config.dt_seconds
        * (total_body_heat + environmental_exchange)
        / config.thermal_capacitance_j_per_k
    )
    environment._battery_j = battery_after
    environment.body_temperature_c = temperature_after
    environment._charger_termination_latched = termination_latched_after
    energy_nonviable = battery_after <= 0.0
    protective = (
        temperature_after >= config.protective_shutdown_c
        and temperature_after < config.hard_shutdown_c
    )
    emergency = temperature_after >= config.hard_shutdown_c
    reason = d020._termination_reason(
        emergency=emergency, protective=protective, energy_nonviable=energy_nonviable
    )
    terminated = reason is not None
    environment._step_count += 1
    truncated = not terminated and environment._step_count >= config.episode_horizon
    environment._episode_done = terminated or truncated
    energy_after = d020_normalize(battery_after, 0.0, config.battery_capacity_j)
    temperature_normalized_after = d020_normalize(
        temperature_after,
        config.visible_temperature_min_c,
        config.visible_temperature_max_c,
    )
    environment.last_transition = D020TransitionTelemetry(
        step_index=environment._step_count,
        action=selected_action,
        position_before=position_before,
        position_after=body.position,
        heading=body.heading,
        station_center=environment.station_center,
        battery_before_j=battery_before,
        battery_after_j=battery_after,
        energy_normalized_before=energy_before,
        energy_normalized_after=energy_after,
        body_temperature_before_c=temperature_before,
        body_temperature_after_c=temperature_after,
        temperature_normalized_before=temperature_normalized_before,
        temperature_normalized_after=temperature_normalized_after,
        charging_contact_before=contact_before,
        charging_contact_after=contact_after,
        electronics_electrical_power_w=config.electronics_electrical_power_w,
        actuator_electrical_power_w=actuator_electrical,
        total_electrical_load_w=total_electrical,
        charge_phase=charge.phase,
        requested_stored_power_w=charge.requested_stored_power_w,
        actual_stored_power_w=actual_stored_power,
        charger_input_power_w=charger_input,
        charging_body_heat_w=charging_heat,
        electronics_body_heat_w=config.electronics_body_heat_w,
        actuator_body_heat_w=actuator_body_heat,
        total_body_heat_w=total_body_heat,
        environmental_exchange_power_w=environmental_exchange,
        charger_termination_latched_after=termination_latched_after,
        preferred_ceiling_crossed=(
            temperature_before
            < config.preferred_operating_ceiling_c
            <= temperature_after
        ),
        above_preferred_ceiling=temperature_after
        >= config.preferred_operating_ceiling_c,
        energy_nonviable=energy_nonviable,
        protective_shutdown=protective,
        emergency_hard_shutdown=emergency,
        terminated=terminated,
        truncated=truncated,
        termination_reason=reason,
    )
    return environment._observation().as_array(), 0.0, terminated, truncated, {}


def d020_normalize(value: float, lower: float, upper: float) -> float:
    return (value - lower) / (upper - lower)


@dataclass(frozen=True, slots=True)
class _CandidateOutcome:
    label: str
    action: Action
    observation: d027.D027Observation
    terminated: bool
    truncated: bool
    telemetry: D020TransitionTelemetry
    delta: tuple[float, ...]
    actual_displacement: float
    displacement_class: str
    start_geometry: dict[str, object]
    end_geometry: dict[str, object]


def _displacement_class(displacement: float) -> str:
    if displacement <= d027.D027_BOUNDARY_TOLERANCE:
        return "FULL_STALL"
    if (
        abs(displacement - D035C_NOMINAL_REVERSE_DISTANCE)
        <= d027.D027_BOUNDARY_TOLERANCE
    ):
        return "FULL_NOMINAL"
    return "BOUNDARY_CLIPPED"


def _candidate(
    environment: d026.D026Env,
    current: d027.D027Observation,
    label: str,
) -> _CandidateOutcome:
    source_body = environment.body
    source_station = environment.station_center
    if source_body is None or source_station is None:
        raise RuntimeError("D-035C candidate requires evaluator geometry")
    start = _geometry(source_body.position, source_body.heading, source_station)
    branch = d029._clone_environment(environment)
    if label == D035C_REVERSE_LABEL:
        observation_array, _, terminated, truncated, info = _reverse_step(branch)
        action = Action.MOVE_FORWARD
    else:
        action = Action[label]
        observation_array, _, terminated, truncated, info = branch.step(action)
    if info != {}:
        raise RuntimeError("D-035C candidate crossed the info boundary")
    telemetry = branch.last_transition
    if telemetry is None:
        raise RuntimeError("D-035C candidate produced no telemetry")
    observation = d031r1._next_visible(observation_array)
    station = telemetry.station_center
    end = _geometry(telemetry.position_after, telemetry.heading, station)
    displacement = math.dist(telemetry.position_before, telemetry.position_after)
    return _CandidateOutcome(
        label=label,
        action=action,
        observation=observation,
        terminated=terminated,
        truncated=truncated,
        telemetry=telemetry,
        delta=_observed_delta(current, observation),
        actual_displacement=displacement,
        displacement_class=_displacement_class(displacement),
        start_geometry=start,
        end_geometry=end,
    )


def _candidate_identity(outcome: _CandidateOutcome) -> dict[str, object]:
    return {
        "label": outcome.label,
        "observation": _visible(outcome.observation),
        "terminated": outcome.terminated,
        "truncated": outcome.truncated,
        "telemetry": outcome.telemetry,
        "delta": outcome.delta,
        "actual_displacement": outcome.actual_displacement,
        "displacement_class": outcome.displacement_class,
    }


def _candidate_outcomes(
    environment: d026.D026Env,
    current: d027.D027Observation,
    order: Sequence[str] = D035C_CANDIDATES,
    streams: RandomStreams | None = None,
) -> tuple[dict[str, _CandidateOutcome], dict[str, object]]:
    if tuple(sorted(order)) != tuple(sorted(D035C_CANDIDATES)):
        raise ValueError("D-035C candidate order must contain all five candidates")
    before_environment = d029._environment_state(environment)
    before_rng = d029._rng_state(streams) if streams is not None else None
    outcomes = {label: _candidate(environment, current, label) for label in order}
    after_environment = d029._environment_state(environment)
    if before_environment != after_environment:
        raise RuntimeError("D-035C candidate evaluation mutated source environment")
    rng_unchanged = True if streams is None else before_rng == d029._rng_state(streams)
    return outcomes, {
        "source_environment_unchanged": before_environment == after_environment,
        "candidate_order": list(order),
        "policy_environment_rng_unchanged": rng_unchanged,
    }


def _candidate_record(
    outcome: _CandidateOutcome, start: dict[str, object]
) -> dict[str, object]:
    end = outcome.end_geometry
    return {
        "label": outcome.label,
        "canonical_action": outcome.action.name,
        "is_evaluator_reverse": outcome.label == D035C_REVERSE_LABEL,
        "change_station_distance": cast(float, end["distance_to_station"])
        - cast(float, start["distance_to_station"]),
        "change_rear_plus_pair_error": cast(float, end["rear_plus_pair_error"])
        - cast(float, start["rear_plus_pair_error"]),
        "change_rear_minus_pair_error": cast(float, end["rear_minus_pair_error"])
        - cast(float, start["rear_minus_pair_error"]),
        "change_rear_contact_max_pair_error": cast(float, end["max_pair_error"])
        - cast(float, start["max_pair_error"]),
        "rear_contact_max_pair_error_reduction": cast(float, start["max_pair_error"])
        - cast(float, end["max_pair_error"]),
        "resulting_charging_contact": outcome.observation.charging_contact,
        "resulting_dual_contact": outcome.observation.charging_contact,
        "visible_delta": list(outcome.delta),
        "beacon_forward_change": outcome.delta[2],
        "actual_displacement": outcome.actual_displacement,
        "nominal_displacement": D035C_NOMINAL_REVERSE_DISTANCE,
        "displacement_class": outcome.displacement_class,
        "clipping_or_stall": outcome.displacement_class != "FULL_NOMINAL",
        "energy_change": outcome.telemetry.energy_normalized_after
        - outcome.telemetry.energy_normalized_before,
        "thermal_change": outcome.telemetry.temperature_normalized_after
        - outcome.telemetry.temperature_normalized_before,
        "terminated": outcome.terminated,
        "truncated": outcome.truncated,
    }


def _one_step_attribution(
    environment: d026.D026Env,
    current: d027.D027Observation,
    streams: RandomStreams,
) -> dict[str, object]:
    body = environment.body
    station = environment.station_center
    if body is None or station is None:
        raise RuntimeError("D-035C anchor lacks evaluator geometry")
    start = _geometry(body.position, body.heading, station)
    fingerprint = d029._environment_state(environment)
    first, first_checks = _candidate_outcomes(environment, current, streams=streams)
    reverse_order = tuple(reversed(D035C_CANDIDATES))
    second, second_checks = _candidate_outcomes(
        environment, current, reverse_order, streams
    )
    order_invariant = all(
        _candidate_identity(first[label]) == _candidate_identity(second[label])
        for label in D035C_CANDIDATES
    )
    if not order_invariant or d029._environment_state(environment) != fingerprint:
        raise RuntimeError("D-035C candidate branch order changed source state/results")
    records = {
        label: _candidate_record(first[label], start) for label in D035C_CANDIDATES
    }
    reductions = {
        label: cast(float, record["rear_contact_max_pair_error_reduction"])
        for label, record in records.items()
    }
    reverse_reduction = reductions[D035C_REVERSE_LABEL]
    canonical_reductions = {
        action.name: reductions[action.name] for action in D035C_CANONICAL_CANDIDATES
    }
    best_all = max(reductions.values())
    best_canonical = max(canonical_reductions.values())
    best_all_labels = [
        label for label, value in reductions.items() if value == best_all
    ]
    reverse_contact = bool(records[D035C_REVERSE_LABEL]["resulting_dual_contact"])
    canonical_contact_labels = [
        action.name
        for action in D035C_CANONICAL_CANDIDATES
        if bool(records[action.name]["resulting_dual_contact"])
    ]
    records[D035C_REVERSE_LABEL]["unique_best_over_all_candidates"] = (
        best_all_labels == [D035C_REVERSE_LABEL]
    )
    records[D035C_REVERSE_LABEL]["unique_best_over_canonical_candidates"] = (
        reverse_reduction > best_canonical
    )
    records[D035C_REVERSE_LABEL]["unique_dual_contact_restoration"] = (
        reverse_contact and not canonical_contact_labels
    )
    return {
        "start_geometry": start,
        "current_visible_observation": list(_visible(current)),
        "candidates": records,
        "best_candidate_labels": best_all_labels,
        "best_canonical_candidate_labels": [
            label
            for label, value in canonical_reductions.items()
            if value == best_canonical
        ],
        "reverse_reduction_margin_vs_best_canonical": reverse_reduction
        - best_canonical,
        "reverse_unique_best_candidate": best_all_labels == [D035C_REVERSE_LABEL],
        "reverse_unique_best_over_canonical": reverse_reduction > best_canonical,
        "reverse_unique_dual_contact_restoration": (
            reverse_contact and not canonical_contact_labels
        ),
        "ties_preserved": {
            "best_all": best_all_labels,
            "best_canonical": [
                label
                for label, value in canonical_reductions.items()
                if value == best_canonical
            ],
        },
        "source_state_immutable": d029._environment_state(environment) == fingerprint,
        "branch_order_invariant": order_invariant,
        "candidate_evaluation_rng_unchanged": first_checks[
            "policy_environment_rng_unchanged"
        ]
        and second_checks["policy_environment_rng_unchanged"],
    }


def _identity_gate(
    seed: int, replay: dict[str, object], accepted: dict[str, object]
) -> dict[str, object]:
    accepted_with_weights = dict(accepted)
    accepted_with_weights["_weights"] = d033._flatten_final_weights(accepted)
    comparison = d032._compare_identity_fields(
        replay, accepted_with_weights, include_private_weights=True
    )
    isolation = cast(dict[str, object], replay["isolation"])
    result = {
        "seed": seed,
        "arm": "LEARNED_NO_DETRAP",
        "all_identity_fields_exact": comparison["all_identity_fields_exact"],
        "checked_identity_fields": comparison["checked_fields"],
        "mismatched_identity_fields": comparison["mismatched_fields"],
        "zero_false_contact_seek_delegation": isolation[
            "zero_false_contact_seek_delegation"
        ],
        "zero_false_contact_seek_explorer_calls": isolation[
            "no_false_contact_seek_explorer_call"
        ],
        "one_policy_rng_draw_per_false_contact_seek_decision": isolation[
            "one_legacy_arbitration_draw_per_false_contact_seek_decision"
        ],
    }
    if not all(
        bool(result[key])
        for key in (
            "all_identity_fields_exact",
            "zero_false_contact_seek_delegation",
            "zero_false_contact_seek_explorer_calls",
            "one_policy_rng_draw_per_false_contact_seek_decision",
        )
    ):
        raise RuntimeError(f"D-035C accepted Arm-B replay gate failed for seed {seed}")
    return result


def _first_false_contact_seek_transition(
    trace: Sequence[d025.D025TransitionTrace],
) -> int | None:
    for row in trace:
        if row.mode_before is d026.D026Mode.SEEK and row.observation_before[4] == 0.0:
            return row.transition_index
    return None


def _first_post_contact_loss_transition(
    trace: Sequence[d025.D025TransitionTrace],
) -> int | None:
    for row in trace:
        if (
            row.telemetry.charging_contact_before
            and not row.telemetry.charging_contact_after
        ):
            target = row.transition_index + 1
            if target <= len(trace):
                return target
            return None
    return None


def _anchor_record(
    anchor: d033._AnchorState | None,
    checks: dict[str, object],
    *,
    unavailable_reason: str | None = None,
) -> dict[str, object]:
    result = dict(checks)
    result["available"] = anchor is not None
    if unavailable_reason is not None:
        result["unavailable_reason"] = unavailable_reason
    if anchor is None:
        return result
    body = anchor.environment.body
    station = anchor.environment.station_center
    if body is None or station is None:
        raise RuntimeError("D-035C anchor lacks geometry")
    result.update(
        {
            "anchor_type": anchor.anchor_type,
            "seed": anchor.seed,
            "transition": anchor.transition,
            "anchor_state_digest": d033._anchor_fingerprint(anchor),
            "current_observation": list(_visible(anchor.current)),
            "anchor_energy": anchor.current.energy,
            "anchor_thermal": anchor.current.thermal,
            "anchor_charging_contact": anchor.current.charging_contact,
            "anchor_mode": anchor.controller.mode.name,
            "anchor_evaluator_position": list(body.position),
            "anchor_evaluator_heading": body.heading,
            "anchor_pair_errors": list(
                d024.dual_contact_pair_errors(body.position, body.heading, station)
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
    return result


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
    *,
    require_seek: bool,
) -> tuple[d033._AnchorState, dict[str, object]]:
    captured_result, trace, instrumentation = d033._run_capture(
        seed,
        role="B",
        horizon=D035C_HORIZON,
        target_transition=transition,
        seed_validator=_validate_d035c_seed,
    )
    comparison = d032._compare_identity_fields(
        captured_result, arm_b_result, include_private_weights=True
    )
    capture = instrumentation.capture
    if capture is None or capture.proposed_action is None:
        raise RuntimeError(f"D-035C anchor capture missing for {seed}/{anchor_type}")
    if transition < 1 or transition > len(trace):
        raise RuntimeError("D-035C anchor transition outside trace")
    row = trace[transition - 1]
    if _visible(capture.current) != row.observation_before:
        raise RuntimeError(
            f"D-035C anchor observation mismatch for {seed}/{anchor_type}"
        )
    if capture.current.charging_contact:
        raise RuntimeError(
            f"D-035C anchor unexpectedly has contact for {seed}/{anchor_type}"
        )
    if require_seek and capture.mode_before is not d026.D026Mode.SEEK:
        raise RuntimeError(f"D-035C anchor is not SEEK for {seed}/{anchor_type}")
    anchor = d033._anchor_from_capture(seed, anchor_type, capture)
    checks: dict[str, object] = {
        "status": anchor_type,
        "target_capture_replay_exact": comparison["all_identity_fields_exact"],
        "target_capture_checked_identity_fields": comparison["checked_fields"],
        "target_capture_mismatched_identity_fields": comparison["mismatched_fields"],
        "pre_action_false_contact": True,
        "pre_action_seek_mode": capture.mode_before is d026.D026Mode.SEEK,
        "complete_learner_state_captured": len(anchor.learner_weights)
        == d027.D027_PLASTIC_STATE_DIMENSION,
    }
    if not cast(bool, checks["target_capture_replay_exact"]):
        raise RuntimeError(f"D-035C anchor replay mismatch for {seed}/{anchor_type}")
    if not cast(bool, checks["complete_learner_state_captured"]):
        raise RuntimeError(f"D-035C learner state incomplete for {seed}/{anchor_type}")
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
    trace_list: list[d025.D025TransitionTrace] = []
    arm_b_result = d031r1._run_arm(
        seed,
        arm="LEARNED_NO_DETRAP",
        horizon=D035C_HORIZON,
        evaluator_diagnostics=True,
        trace_sink=trace_list,
        seed_validator=_validate_d035c_seed,
    )
    replay = _identity_gate(
        seed,
        arm_b_result,
        d033._accepted_arm(accepted_d031r1, seed, "LEARNED_NO_DETRAP"),
    )
    trace = tuple(trace_list)
    anchors: dict[str, d033._AnchorState | None] = {}
    records: dict[str, dict[str, object]] = {}

    first = _first_false_contact_seek_transition(trace)
    if first is None:
        anchors[D035C_FIRST_ANCHOR] = None
        records[D035C_FIRST_ANCHOR] = {
            "status": "anchor_unavailable",
            "seed": seed,
            "available": False,
            "terminated_before_false_contact_seek": True,
        }
    else:
        anchor, checks = _capture_anchor(
            seed, D035C_FIRST_ANCHOR, first, arm_b_result, require_seek=True
        )
        anchors[D035C_FIRST_ANCHOR] = anchor
        records[D035C_FIRST_ANCHOR] = _anchor_record(
            anchor, {**checks, "seed": seed, "anchor_transition": first}
        )

    alt8 = d033._find_alt8_transition(trace)
    accepted_seed = next(
        record
        for record in cast(list[dict[str, object]], accepted_d033["results"])
        if record["seed"] == seed
    )
    expected_alt8 = cast(
        dict[str, object],
        cast(dict[str, object], accepted_seed["anchors"])[d033.D033_ANCHOR_B],
    )
    if (alt8 is None) != (not bool(expected_alt8["available"])):
        raise RuntimeError(f"D-035C ALT8 availability diverged for {seed}")
    if alt8 is None:
        anchors[D035C_ALT8_ANCHOR] = None
        unavailable = {
            "status": "anchor_unavailable",
            "seed": seed,
            "available": False,
            "accepted_d033_anchor_identity_exact": _anchor_projection(
                {"available": False}
            )
            == _anchor_projection(expected_alt8),
            "accepted_d033_anchor_projection": _anchor_projection(expected_alt8),
        }
        if not cast(bool, unavailable["accepted_d033_anchor_identity_exact"]):
            raise RuntimeError(f"D-035C unavailable ALT8 identity diverged for {seed}")
        records[D035C_ALT8_ANCHOR] = unavailable
    else:
        alt_transition, eighth_transition = alt8
        anchor, checks = _capture_anchor(
            seed, D035C_ALT8_ANCHOR, alt_transition, arm_b_result, require_seek=True
        )
        record = _anchor_record(
            anchor,
            {
                **checks,
                "seed": seed,
                "anchor_transition": alt_transition,
                "alternation_eighth_transition": eighth_transition,
                "strict_alternation_length": 8,
                "all_actions_false_contact_seek": True,
                "no_contact_within_eight_actions": True,
            },
        )
        record["accepted_d033_anchor_identity_exact"] = _anchor_projection(
            record
        ) == _anchor_projection(expected_alt8)
        record["accepted_d033_anchor_projection"] = _anchor_projection(expected_alt8)
        if not cast(bool, record["accepted_d033_anchor_identity_exact"]):
            raise RuntimeError(f"D-035C ALT8 identity diverged for {seed}")
        anchors[D035C_ALT8_ANCHOR] = anchor
        records[D035C_ALT8_ANCHOR] = record

    post_loss = _first_post_contact_loss_transition(trace)
    if post_loss is None:
        anchors[D035C_POST_LOSS_ANCHOR] = None
        records[D035C_POST_LOSS_ANCHOR] = {
            "status": "anchor_unavailable",
            "seed": seed,
            "available": False,
            "contact_loss_not_followed_by_available_pre_action_state": True,
        }
    else:
        anchor, checks = _capture_anchor(
            seed,
            D035C_POST_LOSS_ANCHOR,
            post_loss,
            arm_b_result,
            require_seek=False,
        )
        anchors[D035C_POST_LOSS_ANCHOR] = anchor
        records[D035C_POST_LOSS_ANCHOR] = _anchor_record(
            anchor,
            {
                **checks,
                "seed": seed,
                "anchor_transition": post_loss,
                "selected_from_contact_loss_transition": post_loss - 1,
            },
        )
    return replay, trace, anchors, records


def _propose_b_action(
    controller: d026.D026Controller,
    learner: d027.D027ActionConsequencePredictor,
    current: d027.D027Observation,
) -> tuple[Action, d025.D025Arbitration | None]:
    historical = controller.act(current)
    arbitration = controller.last_arbitration
    if arbitration is None:
        return historical, None
    if current.charging_contact or controller.mode is not d026.D026Mode.SEEK:
        raise RuntimeError("D-035C arbitration occurred outside false-contact SEEK")
    predictions, read_only = d031r1._query_candidate_predictions(learner, current)
    if not read_only:
        raise RuntimeError("D-035C prediction query changed learner state")
    return d031r1._choose_steering_action(
        current, predictions, arbitration.greedy_action
    ), arbitration


def _branch_metric_summary(
    anchor: d033._AnchorState,
    environment: d026.D026Env,
    current: d027.D027Observation,
    trace: Sequence[d025.D025TransitionTrace],
    *,
    reverse_count: int,
    proposed_actions: Sequence[str],
    reverse_records: Sequence[dict[str, object]],
    update_count: int,
    update_digest: hashlib._Hash,
    learner: d027.D027ActionConsequencePredictor,
    branch_start_fingerprint: str,
    candidate_checks: dict[str, bool],
    final_policy_digest: str,
    final_environment_digest: str,
    stop_reason: str,
    terminated: bool,
    truncated: bool,
    reacquisition_transition: int | None,
    reacquisition_geometry: dict[str, object] | None,
    energy_values: Sequence[float],
    temperature_values: Sequence[float],
    visible_values: Sequence[tuple[float, float, float, float]],
    geometries: Sequence[dict[str, object]],
    path_length: float,
    direction_counts: dict[str, int],
    clipping_counts: dict[str, dict[str, int]],
    charging_entries: int,
    charging_exits: int,
) -> dict[str, object]:
    final = geometries[-1]
    minimum_geometry = min(
        geometries, key=lambda item: cast(float, item["max_pair_error"])
    )
    final_position = cast(list[float], final["position"])
    anchor_position = cast(list[float], geometries[0]["position"])
    visible_start = visible_values[0]
    visible_final = visible_values[-1]
    return {
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
            "at_anchor": energy_values[0],
            "minimum": min(energy_values),
            "maximum": max(energy_values),
            "final_or_stop": energy_values[-1],
            "at_reacquisition": energy_values[-1]
            if reacquisition_transition is not None
            else None,
        },
        "temperature_normalized": {
            "at_anchor": temperature_values[0],
            "minimum": min(temperature_values),
            "maximum": max(temperature_values),
            "final_or_stop": temperature_values[-1],
            "at_reacquisition": temperature_values[-1]
            if reacquisition_transition is not None
            else None,
        },
        "evaluator_geometry": {
            "start": geometries[0],
            "minimum_max_pair_error": minimum_geometry,
            "final": final,
            "at_reacquisition": reacquisition_geometry,
            "geometry_is_evaluator_only": True,
        },
        "station_distance": {
            "start": geometries[0]["distance_to_station"],
            "minimum": min(
                cast(float, item["distance_to_station"]) for item in geometries
            ),
            "final": final["distance_to_station"],
        },
        "visible_lfr": {
            "start": list(visible_start[:3]),
            "final": list(visible_final[:3]),
            "beacon_forward_max": max(value[2] for value in visible_values),
        },
        "path_length": path_length,
        "net_displacement_from_anchor": {
            "vector": [
                final_position[0] - anchor_position[0],
                final_position[1] - anchor_position[1],
            ],
            "magnitude": math.dist(tuple(anchor_position), tuple(final_position)),
        },
        "translation_and_turn_counts": {
            **direction_counts,
            "turn_count": sum(
                direction_counts.get(action.name, 0)
                for action in (Action.TURN_LEFT, Action.TURN_RIGHT)
            ),
        },
        "clipping_stall_counts_by_translation_direction": clipping_counts,
        "charging_contact_events": {
            "entry_count": charging_entries,
            "exit_count": charging_exits,
        },
        "reverse_intervention_count": reverse_count,
        "false_contact_seek_decision_count": len(proposed_actions),
        "reverse_intervention_fraction": (
            reverse_count / len(proposed_actions) if proposed_actions else None
        ),
        "reverse_interventions": list(reverse_records),
        "learner_update_count": update_count,
        "executed_action_update_digest": update_digest.hexdigest(),
        "final_learner_state_digest": _digest(tuple(learner.weights)),
        "final_policy_rng_digest": final_policy_digest,
        "final_environment_rng_digest": final_environment_digest,
        "candidate_isolation": candidate_checks,
        "provenance": {
            "reverse_is_evaluator_only": True,
            "reverse_has_no_action_enum_identity": True,
            "reverse_did_not_update_d027": True,
            "proposed_actions": list(proposed_actions),
            "branch_start_fingerprint": branch_start_fingerprint,
        },
    }


def _run_continuation(
    anchor: d033._AnchorState, *, oracle: bool
) -> tuple[dict[str, object], tuple[d025.D025TransitionTrace, ...]]:
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
        d033._rewire_controller_rng(anchor.controller, streams.policy),
        streams,
        learner,
        current,
    )
    if start_fingerprint != expected_start:
        raise RuntimeError("D-035C branch clone did not preserve causal start state")
    trace: list[d025.D025TransitionTrace] = []
    proposed_actions: list[str] = []
    reverse_records: list[dict[str, object]] = []
    update_digest = hashlib.sha256()
    update_count = 0
    reverse_count = 0
    terminated = False
    truncated = False
    stop_reason = "incomplete"
    reacquisition_transition: int | None = None
    reacquisition_geometry: dict[str, object] | None = None
    energy_values = [current.energy]
    temperature_values = [current.thermal]
    visible_values = [
        (
            current.beacon.left,
            current.beacon.forward,
            current.beacon.right,
            current.energy,
        )
    ]
    body = environment.body
    station = environment.station_center
    if body is None or station is None:
        raise RuntimeError("D-035C continuation lacks evaluator geometry")
    geometries = [_geometry(body.position, body.heading, station)]
    path_length = 0.0
    direction_counts = {label: 0 for label in D035C_CANDIDATES}
    clipping_counts = {
        "FORWARD": {"FULL_NOMINAL": 0, "BOUNDARY_CLIPPED": 0, "FULL_STALL": 0},
        "REVERSE": {"FULL_NOMINAL": 0, "BOUNDARY_CLIPPED": 0, "FULL_STALL": 0},
    }
    charging_entries = charging_exits = 0
    candidate_checks = {
        "source_state_immutable": True,
        "branch_order_invariant": True,
        "policy_rng_unchanged": True,
        "environment_rng_unchanged": True,
        "learner_unchanged_by_candidate_evaluation": True,
        "learner_unchanged_on_reverse_intervention": True,
        "canonical_update_once": True,
        "no_reverse_identity_in_learner": True,
    }

    for local_transition in range(1, D035C_BRANCH_HORIZON + 1):
        global_transition = anchor.transition + local_transition - 1
        mode_before = controller.mode
        proposed, _arbitration = _propose_b_action(controller, learner, current)
        proposed_actions.append(proposed.name)
        physical_label = proposed.name
        candidates: dict[str, _CandidateOutcome] = {}
        if (
            oracle
            and mode_before is d026.D026Mode.SEEK
            and not current.charging_contact
        ):
            learner_before = learner.weights
            rng_before = d029._rng_state(streams)
            candidates, checks = _candidate_outcomes(
                environment, current, streams=streams
            )
            reversed_candidates, reversed_checks = _candidate_outcomes(
                environment,
                current,
                tuple(reversed(D035C_CANDIDATES)),
                streams,
            )
            candidate_checks["source_state_immutable"] &= bool(
                checks["source_environment_unchanged"]
            ) and bool(reversed_checks["source_environment_unchanged"])
            candidate_checks["policy_rng_unchanged"] &= rng_before == d029._rng_state(
                streams
            )
            candidate_checks["environment_rng_unchanged"] &= (
                rng_before[0] == d029._rng_state(streams)[0]
            )
            candidate_checks["branch_order_invariant"] &= all(
                _candidate_identity(candidates[label])
                == _candidate_identity(reversed_candidates[label])
                for label in D035C_CANDIDATES
            )
            candidate_checks["learner_unchanged_by_candidate_evaluation"] &= (
                learner.weights == learner_before
            )
            reductions = {
                label: cast(
                    float,
                    _candidate_record(outcome, geometries[-1])[
                        "rear_contact_max_pair_error_reduction"
                    ],
                )
                for label, outcome in candidates.items()
            }
            best_canonical = max(
                reductions[action.name] for action in D035C_CANONICAL_CANDIDATES
            )
            reverse_wins = reductions[D035C_REVERSE_LABEL] > best_canonical
            if reverse_wins:
                physical_label = D035C_REVERSE_LABEL
                reverse_count += 1
                reverse_records.append(
                    {
                        "transition": global_transition,
                        "proposed_canonical_action": proposed.name,
                        "reverse_reduction": reductions[D035C_REVERSE_LABEL],
                        "best_canonical_reduction": best_canonical,
                        "strict_margin": reductions[D035C_REVERSE_LABEL]
                        - best_canonical,
                        "learner_update_performed": False,
                    }
                )
        if physical_label == D035C_REVERSE_LABEL:
            observation_array, reward, terminated, truncated, info = _reverse_step(
                environment
            )
            telemetry = environment.last_transition
            if telemetry is None:
                raise RuntimeError("D-035C reverse transition produced no telemetry")
            candidate_checks["learner_unchanged_on_reverse_intervention"] &= (
                learner.weights == learner_before
            )
            candidate_checks["no_reverse_identity_in_learner"] &= True
            trace_action = Action.MOVE_FORWARD
        else:
            trace_action = Action[physical_label]
            observation_array, reward, terminated, truncated, info = environment.step(
                trace_action
            )
            telemetry = environment.last_transition
            if telemetry is None:
                raise RuntimeError("D-035C canonical transition produced no telemetry")
            next_observation = d031r1._next_visible(observation_array)
            update = learner.observe_transition(current, trace_action, next_observation)
            update_count += 1
            d031r1._update_digest(
                update_digest, global_transition, trace_action, update
            )
            candidate_checks["canonical_update_once"] &= update.action is trace_action
        if reward != 0.0 or info != {}:
            raise RuntimeError("D-035C branch crossed reward/info boundary")
        next_observation = d031r1._next_visible(observation_array)
        if physical_label == D035C_REVERSE_LABEL:
            # No learner prediction or update is performed for the evaluator
            # branch, because no canonical reverse feature row exists.
            pass
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
        if physical_label == D035C_REVERSE_LABEL:
            direction_counts[D035C_REVERSE_LABEL] += 1
            clipping_counts["REVERSE"][
                _displacement_class(
                    math.dist(telemetry.position_before, telemetry.position_after)
                )
            ] += 1
        else:
            direction_counts[physical_label] += 1
            if trace_action is Action.MOVE_FORWARD:
                clipping_counts["FORWARD"][
                    _displacement_class(
                        math.dist(telemetry.position_before, telemetry.position_after)
                    )
                ] += 1
        if telemetry.charging_contact_before and not telemetry.charging_contact_after:
            charging_exits += 1
        if not telemetry.charging_contact_before and telemetry.charging_contact_after:
            charging_entries += 1
            reacquisition_transition = local_transition
            reacquisition_geometry = _geometry(
                telemetry.position_after, telemetry.heading, station
            )
        path_length += math.dist(telemetry.position_before, telemetry.position_after)
        current = next_observation
        energy_values.append(current.energy)
        temperature_values.append(current.thermal)
        visible_values.append(
            (
                current.beacon.left,
                current.beacon.forward,
                current.beacon.right,
                current.energy,
            )
        )
        geometries.append(
            _geometry(telemetry.position_after, telemetry.heading, station)
        )
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

    final_policy, final_environment = _rng_digests(streams)
    output = _branch_metric_summary(
        anchor,
        environment,
        current,
        trace,
        reverse_count=reverse_count,
        proposed_actions=proposed_actions,
        reverse_records=reverse_records,
        update_count=update_count,
        update_digest=update_digest,
        learner=learner,
        branch_start_fingerprint=start_fingerprint,
        candidate_checks=candidate_checks,
        final_policy_digest=_rng_digests(streams)[0],
        final_environment_digest=_rng_digests(streams)[1],
        stop_reason=stop_reason,
        terminated=terminated,
        truncated=truncated,
        reacquisition_transition=reacquisition_transition,
        reacquisition_geometry=reacquisition_geometry,
        energy_values=energy_values,
        temperature_values=temperature_values,
        visible_values=visible_values,
        geometries=geometries,
        path_length=path_length,
        direction_counts=direction_counts,
        clipping_counts=clipping_counts,
        charging_entries=charging_entries,
        charging_exits=charging_exits,
    )
    output["oracle_mode"] = oracle
    output["final_policy_rng_digest"] = final_policy
    output["final_environment_rng_digest"] = final_environment
    output["branch_state"] = {
        **candidate_checks,
        "branch_start_exact": start_fingerprint == expected_start,
        "branch_did_not_mutate_anchor": d033._anchor_fingerprint(anchor)
        == anchor_before,
        "reward_zero_every_transition": all(row.reward == 0.0 for row in trace),
        "organism_info_empty_every_transition": all(row.info == {} for row in trace),
        "canonical_learner_update_count_matches": update_count
        == len(trace) - reverse_count,
        "reverse_intervention_steps_do_not_update_learner": candidate_checks[
            "learner_unchanged_on_reverse_intervention"
        ],
    }
    branch_state = cast(dict[str, object], output["branch_state"])
    if not all(cast(bool, value) for value in branch_state.values()):
        raise RuntimeError(
            f"D-035C branch isolation failed for {anchor.seed}/{anchor.anchor_type}"
        )
    return output, tuple(trace)


def _branch_identity(output: dict[str, object]) -> dict[str, object]:
    return {
        key: value
        for key, value in output.items()
        if key
        not in {
            "branch_state",
            "final_policy_rng_digest",
            "final_environment_rng_digest",
        }
    }


def _baseline_expected_trace(
    full_trace: Sequence[d025.D025TransitionTrace], anchor_transition: int
) -> tuple[d025.D025TransitionTrace, ...]:
    rows: list[d025.D025TransitionTrace] = []
    for row in full_trace[
        anchor_transition - 1 : anchor_transition - 1 + D035C_BRANCH_HORIZON
    ]:
        rows.append(row)
        if (
            row.telemetry.charging_contact_after
            or row.telemetry.terminated
            or row.telemetry.truncated
        ):
            break
    return tuple(rows)


def _run_anchor(
    anchor: d033._AnchorState,
    full_trace: Sequence[d025.D025TransitionTrace],
) -> dict[str, object]:
    baseline, baseline_trace = _run_continuation(anchor, oracle=False)
    # Reconstruct the baseline trace once with the same continuation engine;
    # the accepted replay identity is checked by the source trace comparison.
    # The compact output carries the exact expected trace digest and count.
    expected = _baseline_expected_trace(full_trace, anchor.transition)
    baseline["baseline_continuation_exact"] = baseline_trace == expected
    if not cast(bool, baseline["baseline_continuation_exact"]):
        raise RuntimeError(
            f"D-035C BASELINE_B length diverged at {anchor.seed}/{anchor.anchor_type}"
        )
    oracle, _ = _run_continuation(anchor, oracle=True)
    one_step = _one_step_attribution(anchor.environment, anchor.current, anchor.streams)
    return {
        "anchor_type": anchor.anchor_type,
        "seed": anchor.seed,
        "available": True,
        "one_step_attribution": one_step,
        "baseline_b": baseline,
        "reverse_available_oracle": oracle,
        "exact_baseline_comparable_transition_count": len(expected),
        "exact_baseline_expected_trace_digest": _digest(expected),
        "branch_order_invariance": bool(one_step["branch_order_invariant"]),
    }


def _number_values(runs: Sequence[dict[str, object]], path: str) -> list[float]:
    values: list[float] = []
    for run in runs:
        value: object = run
        for part in path.split("."):
            value = cast(dict[str, object], value)[part]
        if value is not None:
            values.append(float(cast(float, value)))
    return values


def _pooled_summary(
    anchor_type: str, records: Sequence[dict[str, object]]
) -> dict[str, object]:
    baseline = [cast(dict[str, object], record["baseline_b"]) for record in records]
    oracle = [
        cast(dict[str, object], record["reverse_available_oracle"])
        for record in records
    ]
    one_step = [
        cast(dict[str, object], record["one_step_attribution"]) for record in records
    ]
    unique_best = sum(
        int(cast(bool, item["reverse_unique_best_candidate"])) for item in one_step
    )
    unique_dual = sum(
        int(cast(bool, item["reverse_unique_dual_contact_restoration"]))
        for item in one_step
    )
    return {
        "anchor_type": anchor_type,
        "available_seed_count": len(records),
        "baseline_reacquisition_count": sum(
            int(cast(bool, item["reacquired_within_branch_window"]))
            for item in baseline
        ),
        "oracle_reacquisition_count": sum(
            int(cast(bool, item["reacquired_within_branch_window"])) for item in oracle
        ),
        "baseline_reacquisition_latency": _number_summary(
            _number_values(baseline, "reacquisition_latency")
        ),
        "oracle_reacquisition_latency": _number_summary(
            _number_values(oracle, "reacquisition_latency")
        ),
        "oracle_reverse_intervention_count": sum(
            int(cast(int, item["reverse_intervention_count"])) for item in oracle
        ),
        "oracle_reverse_intervention_fraction": _number_summary(
            _number_values(oracle, "reverse_intervention_fraction")
        ),
        "one_step_unique_best_reverse_count": unique_best,
        "one_step_unique_best_reverse_fraction": unique_best / len(one_step)
        if one_step
        else None,
        "one_step_unique_reverse_dual_contact_restoration_count": unique_dual,
        "one_step_unique_reverse_dual_contact_restoration_fraction": unique_dual
        / len(one_step)
        if one_step
        else None,
        "one_step_reverse_margin_vs_best_canonical": _number_summary(
            [
                float(cast(float, item["reverse_reduction_margin_vs_best_canonical"]))
                for item in one_step
            ]
        ),
        "baseline_pair_error_start_min_final": {
            "start": _number_values(
                baseline, "evaluator_geometry.start.max_pair_error"
            ),
            "minimum": _number_values(
                baseline, "evaluator_geometry.minimum_max_pair_error.max_pair_error"
            ),
            "final": _number_values(
                baseline, "evaluator_geometry.final.max_pair_error"
            ),
        },
        "oracle_pair_error_start_min_final": {
            "start": _number_values(oracle, "evaluator_geometry.start.max_pair_error"),
            "minimum": _number_values(
                oracle, "evaluator_geometry.minimum_max_pair_error.max_pair_error"
            ),
            "final": _number_values(oracle, "evaluator_geometry.final.max_pair_error"),
        },
        "baseline_station_distance_start_min_final": {
            "start": _number_values(baseline, "station_distance.start"),
            "minimum": _number_values(baseline, "station_distance.minimum"),
            "final": _number_values(baseline, "station_distance.final"),
        },
        "oracle_station_distance_start_min_final": {
            "start": _number_values(oracle, "station_distance.start"),
            "minimum": _number_values(oracle, "station_distance.minimum"),
            "final": _number_values(oracle, "station_distance.final"),
        },
        "baseline_forward_reverse_turn_counts": {
            "forward": sum(
                int(
                    cast(dict[str, int], item["translation_and_turn_counts"])[
                        "MOVE_FORWARD"
                    ]
                )
                for item in baseline
            ),
            "reverse": 0,
            "turns": sum(
                cast(
                    int,
                    cast(dict[str, object], item["translation_and_turn_counts"])[
                        "turn_count"
                    ],
                )
                for item in baseline
            ),
        },
        "oracle_forward_reverse_turn_counts": {
            "forward": sum(
                int(
                    cast(dict[str, int], item["translation_and_turn_counts"])[
                        "MOVE_FORWARD"
                    ]
                )
                for item in oracle
            ),
            "reverse": sum(
                int(
                    cast(dict[str, int], item["translation_and_turn_counts"])[
                        D035C_REVERSE_LABEL
                    ]
                )
                for item in oracle
            ),
            "turns": sum(
                cast(
                    int,
                    cast(dict[str, object], item["translation_and_turn_counts"])[
                        "turn_count"
                    ],
                )
                for item in oracle
            ),
        },
        "baseline_energy": _number_summary(
            _number_values(baseline, "energy.final_or_stop")
        ),
        "oracle_energy": _number_summary(
            _number_values(oracle, "energy.final_or_stop")
        ),
        "baseline_thermal": _number_summary(
            _number_values(baseline, "temperature_normalized.final_or_stop")
        ),
        "oracle_thermal": _number_summary(
            _number_values(oracle, "temperature_normalized.final_or_stop")
        ),
        "seed_lists": {
            "baseline_reacquired": [
                record["seed"]
                for index, record in enumerate(records)
                if baseline[index]["reacquired_within_branch_window"]
            ],
            "oracle_reacquired": [
                record["seed"]
                for index, record in enumerate(records)
                if oracle[index]["reacquired_within_branch_window"]
            ],
        },
        "nulls_preserved": True,
        "discarded_seed_count": 0,
    }


def _interpretation(pooled: dict[str, dict[str, object]]) -> dict[str, object]:
    return {
        "lane": "Development",
        "confirmatory_claim": False,
        "predeclared_readings": [
            (
                "Reverse frequently uniquely improving geometry and/or materially "
                "improving oracle reacquisition supports reverse physical capacity "
                "as a candidate future question, without authorizing a canonical "
                "reverse action."
            ),
            (
                "One-step geometry improvement without behavioural improvement "
                "indicates local kinematic benefit is insufficient under the "
                "current sequence/control structure."
            ),
            (
                "Oracle-only improvement indicates physical capacity may matter "
                "while the organism lacks an observable recruitment mechanism."
            ),
            (
                "Rare or absent unique reverse benefit does not support missing "
                "reverse translation as sufficient to explain failure on this "
                "support."
            ),
            (
                "Any baseline identity or isolation failure invalidates treatment "
                "interpretation."
            ),
        ],
        "pooled_observed_reacquisition": {
            anchor: {
                "baseline": pooled[anchor]["baseline_reacquisition_count"],
                "oracle": pooled[anchor]["oracle_reacquisition_count"],
            }
            for anchor in D035C_ANCHORS
        },
        "descriptive_observations_only": True,
        "no_universal_pass_threshold": True,
        "no_canonical_reverse_authorized": True,
        "no_d035b_synthesis": True,
    }


def run_d035c_audit(
    seeds: Sequence[int] = D035C_DEFAULT_DEVELOPMENT_SEEDS,
    *,
    horizon: int = D035C_HORIZON,
    executed_commit_sha: str | None = None,
) -> dict[str, object]:
    validated = _validate_d035c_development_seeds(seeds)
    if horizon != D035C_HORIZON:
        raise ValueError("D-035C requires the frozen 70,000-transition horizon")
    executed_sha = _validate_executed_commit_sha(executed_commit_sha)
    if executed_sha is None:
        raise ValueError("D-035C requires an exact clean executable SHA")
    accepted_d031r1 = d035a._accepted_artifact(D035C_ACCEPTED_D031R1_ARTIFACT)
    accepted_d033 = d035a._accepted_artifact(D035C_ACCEPTED_D033_ARTIFACT)
    results: list[dict[str, object]] = []
    pooled_runs: dict[str, list[dict[str, object]]] = {
        anchor: [] for anchor in D035C_ANCHORS
    }
    for seed in validated:
        replay, trace, anchors, anchor_records = _replay_and_anchors(
            seed, accepted_d031r1, accepted_d033
        )
        serial_anchors: dict[str, dict[str, object]] = {}
        for anchor_type in D035C_ANCHORS:
            anchor = anchors[anchor_type]
            record = dict(anchor_records[anchor_type])
            if anchor is not None:
                run = _run_anchor(anchor, trace)
                record.update(run)
                pooled_runs[anchor_type].append(run)
            serial_anchors[anchor_type] = record
        results.append({"seed": seed, "replay": replay, "anchors": serial_anchors})
    pooled = {
        anchor: _pooled_summary(anchor, pooled_runs[anchor]) for anchor in D035C_ANCHORS
    }
    return {
        "schema_version": 1,
        "experiment": "D-035C",
        "title": "Evaluator-only reverse-translation sufficiency audit",
        "authoritative_base_sha": D035C_AUTHORITATIVE_BASE_SHA,
        "base_tree_sha": D035C_BASE_TREE_SHA,
        "implementation_probe_sha": executed_sha,
        "protocol_only_freeze_sha": executed_sha,
        "development_seeds": list(validated),
        "horizon": D035C_HORIZON,
        "branch_horizon": D035C_BRANCH_HORIZON,
        "support": {
            "source": "accepted Arm-B LEARNED_NO_DETRAP replay and D-033 anchors only",
            "accepted_d031r1_artifact": D035C_ACCEPTED_D031R1_ARTIFACT,
            "accepted_d031r1_artifact_sha256": d035a._artifact_sha256(
                D035C_ACCEPTED_D031R1_ARTIFACT
            ),
            "accepted_d033_artifact": D035C_ACCEPTED_D033_ARTIFACT,
            "accepted_d033_artifact_sha256": d035a._artifact_sha256(
                D035C_ACCEPTED_D033_ARTIFACT
            ),
            "fresh_development_seeds": False,
            "fresh_evidence_seeds": False,
            "d035b_code_or_results_used": False,
        },
        "freeze": {
            "anchors": list(D035C_ANCHORS),
            "first_anchor_definition": (
                "first Arm-B pre-action SEEK state with false contact immediately "
                "before ordinary no-de-trap arbitration/action selection"
            ),
            "alt8_anchor_definition": (
                "exact accepted D-033 first pre-action state after eight completed "
                "strict alternating false-contact SEEK actions"
            ),
            "post_contact_loss_definition": (
                "first Arm-B pre-action state immediately after an accepted causal "
                "dual-contact-to-false-contact transition; unavailable at lifetime "
                "boundary"
            ),
            "candidate_actions": list(D035C_CANDIDATES),
            "canonical_candidate_actions": [action.name for action in Action],
            "reverse_operation": {
                "nominal_distance": D035C_NOMINAL_REVERSE_DISTANCE,
                "displacement": "negative current body-forward axis",
                "heading_unchanged": True,
                "mirrored_world_boundary_clipping": True,
                "same_timestep_as_move_forward": True,
                "same_move_forward_actuator_energy_and_thermal_accounting": True,
                "no_rng_draw": True,
                "reward": 0.0,
                "organism_info": {},
            },
            "oracle_rule": (
                "select reverse only when its rear-contact max-pair-error reduction "
                "is strictly greater than every canonical candidate; ties never "
                "select reverse"
            ),
            "branch_horizon": D035C_BRANCH_HORIZON,
            "stop_rules": [
                "dual-contact reacquisition",
                "inherited termination/truncation",
                "256 transitions from anchor",
            ],
            "no_reverse_action_enum_or_learner_row": True,
        },
        "causal_order": [
            "exact accepted Arm-B replay and frozen anchor reconstruction",
            "isolated five-candidate one-step evaluator branches",
            "exact BASELINE_B continuation",
            "ordinary Arm-B oracle decision pipeline",
            "read-only five-candidate geometry test at false-contact SEEK decisions",
            "reverse-only evaluator displacement or canonical physical transition",
            "canonical D-027 update only for canonical physical actions",
            "post-hoc evaluator metrics",
        ],
        "organism_boundary": {
            "actions": [action.name for action in Action],
            "channels": list(D035C_CHANNELS),
            "reward": 0.0,
            "info": {},
            "reverse_exposed_to_organism": False,
            "reverse_in_d027": False,
            "canonical_runtime_unchanged": True,
            "d035b_used": False,
        },
        "replay_gate": {
            "all_seeds_exact_arm_b_replay": all(
                cast(
                    bool,
                    cast(dict[str, object], result["replay"])[
                        "all_identity_fields_exact"
                    ],
                )
                for result in results
            ),
            "checked_identity_fields": list(d032._CAUSAL_IDENTITY_FIELDS)
            + ["_weights"],
            "zero_false_contact_seek_explorer_calls_required": True,
            "one_policy_rng_draw_per_false_contact_seek_decision_required": True,
            "complete_168_weight_state_required": True,
            "accepted_d033_alt8_anchor_identity_required": True,
        },
        "results": results,
        "pooled": pooled,
        "interpretation": _interpretation(pooled),
    }


def write_d035c_json(path: Path, executed_commit_sha: str | None = None) -> Path:
    path.write_text(
        json.dumps(
            run_d035c_audit(executed_commit_sha=executed_commit_sha),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the D-035C reverse audit.")
    parser.add_argument("--executed-commit-sha")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.output is None:
        print(
            json.dumps(
                run_d035c_audit(executed_commit_sha=args.executed_commit_sha),
                indent=2,
                sort_keys=True,
            )
        )
    else:
        write_d035c_json(args.output, args.executed_commit_sha)
        print(f"D-035C result written to {args.output}")


if __name__ == "__main__":
    main()
