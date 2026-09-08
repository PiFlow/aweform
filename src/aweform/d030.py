"""D-030 bounded learned SEEK-steering causal development probe.

The inherited D-026 controller, D-024 environment, and D-027 learner remain
the only organism mechanisms.  D-030 changes one decision surface: on a
non-delegated false-contact SEEK transition, Arm B selects among the three
steering actions using the learned ``delta_beacon_forward`` prediction and
Arm C uses the fixed cyclic action/prediction permutation.  All branch truth
and outcome measurements are evaluator-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pickle
import statistics
from dataclasses import replace
from pathlib import Path
from typing import Any, Final, Sequence, cast

import numpy as np

from . import d024, d025, d026, d027, d029
from .d020 import D020PhysicalConfig
from .env import Action
from .exp003 import EXP003_B50_ENTER_SEEK_THRESHOLD
from .exp003_seed_policy import validate_exp003_development_seeds
from .rng import RandomStreams

D030_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = tuple(range(18428, 18448))
D030_CANONICAL_VISUALIZATION_SEED: Final[int] = D030_DEFAULT_DEVELOPMENT_SEEDS[0]
D030_HORIZON: Final[int] = 70_000
D030_AUTHORITATIVE_BASE_SHA: Final[str] = "44db3b7750b8b74eb4930ade9ba4c620d0a36ba6"
D030_BASE_TREE_SHA: Final[str] = "6cbad6863b931aec7ac56f8b8094ab2f0ff825c2"
D030_SEEK_DELEGATION_PROBABILITY: Final[float] = d026.D026_SEEK_DELEGATION_PROBABILITY
D030_EXPLORER_HAZARD: Final[float] = 1.0 / 8.0
D030_LEARNING_RATE: Final[float] = d027.D027_LEARNING_RATE
D030_PLASTIC_STATE_DIMENSION: Final[int] = d027.D027_PLASTIC_STATE_DIMENSION
D030_CHANNELS: Final[tuple[str, ...]] = d027.D027_CHANNELS
D030_OUTPUTS: Final[tuple[str, ...]] = d027.D027_OUTPUTS
D030_FORWARD_OUTPUT_INDEX: Final[int] = D030_OUTPUTS.index("delta_beacon_forward")
D030_STEERING_ACTIONS: Final[tuple[Action, ...]] = (
    Action.TURN_LEFT,
    Action.TURN_RIGHT,
    Action.MOVE_FORWARD,
)
D030_ARM_NAMES: Final[tuple[str, ...]] = (
    "REFERENCE_NO_INFLUENCE",
    "LEARNED_FORWARD",
    "PERMUTED_FORWARD",
)
D030_BOUNDARY_CLASSES: Final[tuple[str, ...]] = (
    "FULL_NOMINAL_FORWARD",
    "BOUNDARY_CLIPPED_FORWARD",
    "FULL_STALL_FORWARD",
)
D030_QUARTERS: Final[tuple[str, ...]] = ("Q1", "Q2", "Q3", "Q4")


def _validate_d030_development_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    """Apply the formal reservation guard and exact D-030 seed guard."""
    validated = validate_exp003_development_seeds(seeds)
    if validated != D030_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-030 requires exactly the frozen development seeds "
            f"{D030_DEFAULT_DEVELOPMENT_SEEDS}; got {validated}"
        )
    return validated


def _validate_d030_seed(seed: int) -> None:
    validated = validate_exp003_development_seeds((seed,))
    if validated[0] not in D030_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-030 may execute only predeclared development seeds "
            f"{D030_DEFAULT_DEVELOPMENT_SEEDS}; got {validated}"
        )


def _validate_executed_commit_sha(value: str | None) -> str | None:
    return d027._validate_executed_commit_sha(value)


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
        raise RuntimeError("D-030 reset crossed the information boundary")
    if environment.body is None or environment.station_center is None:
        raise RuntimeError("D-030 reset did not initialize evaluator geometry")
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
        float(next_observation.charging_contact) - float(current.charging_contact),
        next_observation.thermal - current.thermal,
    )


def _query_candidate_predictions(
    learner: d027.D027ActionConsequencePredictor,
    current: d027.D027Observation,
) -> tuple[dict[Action, d027.D027Prediction], bool]:
    """Query exactly the three causal candidate heads, without mutation."""
    before = learner.weights
    predictions = {
        action: learner.predict(current, action) for action in D030_STEERING_ACTIONS
    }
    return predictions, learner.weights == before


def _exact_argmax(scores: dict[Action, float]) -> tuple[Action, ...]:
    maximum = max(scores.values())
    return tuple(
        action for action in D030_STEERING_ACTIONS if scores[action] == maximum
    )


def _choose_steering_action(
    current: d027.D027Observation,
    predictions: dict[Action, d027.D027Prediction],
    greedy_action: Action,
) -> Action:
    """Choose the unique raw forward-delta maximum, else historical greedy."""
    scores = {
        action: current.beacon.forward
        + predictions[action].values[D030_FORWARD_OUTPUT_INDEX]
        for action in D030_STEERING_ACTIONS
    }
    winners = _exact_argmax(scores)
    return winners[0] if len(winners) == 1 else greedy_action


def _permuted_scores(
    predictions: dict[Action, d027.D027Prediction],
) -> dict[Action, float]:
    forward = D030_FORWARD_OUTPUT_INDEX
    return {
        Action.TURN_LEFT: predictions[Action.TURN_RIGHT].values[forward],
        Action.TURN_RIGHT: predictions[Action.MOVE_FORWARD].values[forward],
        Action.MOVE_FORWARD: predictions[Action.TURN_LEFT].values[forward],
    }


def _choose_permuted_action(
    current: d027.D027Observation,
    predictions: dict[Action, d027.D027Prediction],
    greedy_action: Action,
) -> Action:
    scores = {
        action: current.beacon.forward + value
        for action, value in _permuted_scores(predictions).items()
    }
    winners = _exact_argmax(scores)
    return winners[0] if len(winners) == 1 else greedy_action


def _score_margin(scores: dict[Action, float]) -> float:
    values = sorted(scores.values(), reverse=True)
    return values[0] - values[1]


def _evaluate_steering_branches(
    environment: d026.D026Env, current: d027.D027Observation
) -> dict[Action, d029._BranchOutcome]:
    return {
        action: d029._branch(environment, current, action)
        for action in D030_STEERING_ACTIONS
    }


def _digest(value: object) -> str:
    return hashlib.sha256(pickle.dumps(value, protocol=5)).hexdigest()


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


def _termination_reason(
    environment: d026.D026Env, terminated: bool, truncated: bool
) -> str:
    return d027._termination_reason(environment, terminated, truncated)


def _trace_update_digest(trace: Sequence[object]) -> str:
    """Reconstruct the unchanged D-027 update stream from a trace."""
    learner = d027.D027ActionConsequencePredictor()
    digest = hashlib.sha256()
    for item in trace:
        record = cast(d025.D025TransitionTrace, item)
        current = d025._controller_observation(
            np.asarray(record.observation_before, dtype=np.float64)
        )
        next_observation = d025._controller_observation(
            np.asarray(record.observation, dtype=np.float64)
        )
        update = learner.observe_transition(current, record.action, next_observation)
        _update_digest(digest, record.transition_index, record.action, update)
    return digest.hexdigest()


def _mode_counts() -> dict[str, int]:
    return {mode.name: 0 for mode in d026.D026Mode}


def _run_arm(
    seed: int,
    *,
    arm: str,
    horizon: int,
    evaluator_diagnostics: bool,
) -> dict[str, object]:
    if arm not in D030_ARM_NAMES:
        raise ValueError(f"unknown D-030 arm: {arm}")
    _validate_d030_seed(seed)
    environment, observation_array, streams = _initial_environment(horizon, seed)
    controller = d026.D026Controller(streams.policy)
    controller.reset()
    learner = d027.D027ActionConsequencePredictor()
    trace: list[object] = []
    update_digest = hashlib.sha256()
    action_counts = {action.name: 0 for action in Action}
    mode_occupancy = _mode_counts()
    mode_entry_counts = _mode_counts()
    mode_entry_counts[controller.mode.name] = 1
    transitions = 0
    terminated = False
    truncated = False
    current = _next_visible(observation_array)
    initial_temperature = current.thermal
    minimum_energy = maximum_energy = current.energy
    minimum_temperature = maximum_temperature = current.thermal
    full_departures = charger_exits = seek_entries = reacquisitions = 0
    full_recharges = redepartures = completed_cycles = 0
    charge_entries = 0
    active_seek: dict[str, object] | None = None
    recharge_active = False
    recharge_ready = False
    cycle_stage = 0
    seek_episodes: list[dict[str, object]] = []
    arbitration_records: list[dict[str, object]] = []
    decision_records: list[dict[str, object]] = []
    all_prediction_queries_read_only = True
    all_branch_environment_checks_unchanged = True
    all_branch_controller_checks_unchanged = True
    all_branch_rng_checks_unchanged = True
    all_selected_branch_matches = True
    all_real_updates_executed_action_only = True
    prediction_query_count = 0
    branch_evaluation_count = 0

    while not (terminated or truncated):
        if environment.body is None or environment.station_center is None:
            raise RuntimeError("D-030 evaluator geometry disappeared")
        mode_before = controller.mode
        mode_occupancy[mode_before.name] += 1
        historical_action = controller.act(current)
        mode_after = controller.mode
        action = historical_action
        arbitration = controller.last_arbitration
        predictions: dict[Action, d027.D027Prediction] = {}
        learned_action: Action | None = None
        permuted_action: Action | None = None
        branches: dict[Action, d029._BranchOutcome] = {}
        transition_index = transitions + 1

        if mode_after is not mode_before:
            mode_entry_counts[mode_after.name] += 1
        if mode_before is d026.D026Mode.CHARGE and mode_after is d026.D026Mode.DEPART:
            full_departures += 1
            if recharge_ready:
                redepartures += 1
                completed_cycles += 1
                recharge_ready = False
                cycle_stage = 1
            else:
                cycle_stage = 1

        if arbitration is not None:
            if current.charging_contact or mode_after is not d026.D026Mode.SEEK:
                raise RuntimeError("D-030 arbitration used outside false-contact SEEK")
            arbitration_records.append(
                {
                    "transition": transition_index,
                    "greedy_beacon_action": arbitration.greedy_action.name,
                    "historical_action": historical_action.name,
                    "delegation_draw": arbitration.delegation_draw,
                    "delegated": arbitration.delegated,
                }
            )
            if not arbitration.delegated:
                if arm == "REFERENCE_NO_INFLUENCE" and not evaluator_diagnostics:
                    pass
                else:
                    predictions, read_only = _query_candidate_predictions(
                        learner, current
                    )
                    all_prediction_queries_read_only &= read_only
                    prediction_query_count += len(predictions)
                    learned_action = _choose_steering_action(
                        current, predictions, arbitration.greedy_action
                    )
                    permuted_action = _choose_permuted_action(
                        current, predictions, arbitration.greedy_action
                    )
                    if arm == "LEARNED_FORWARD":
                        action = learned_action
                    elif arm == "PERMUTED_FORWARD":
                        action = permuted_action

                if arm == "REFERENCE_NO_INFLUENCE" and evaluator_diagnostics:
                    if learned_action is None or permuted_action is None:
                        raise RuntimeError("D-030 reference prediction query missing")

                if evaluator_diagnostics:
                    if not predictions:
                        raise RuntimeError("D-030 evaluator predictions missing")
                    environment_before = d029._environment_state(environment)
                    controller_before = d029._controller_state(controller)
                    rng_before = d029._rng_state(streams)
                    branches = _evaluate_steering_branches(environment, current)
                    branch_evaluation_count += len(branches)
                    all_branch_environment_checks_unchanged &= (
                        d029._environment_state(environment) == environment_before
                    )
                    all_branch_controller_checks_unchanged &= (
                        d029._controller_state(controller) == controller_before
                    )
                    all_branch_rng_checks_unchanged &= (
                        d029._rng_state(streams) == rng_before
                    )

        action_counts[action.name] += 1
        observation_array, reward, terminated, truncated, info = environment.step(
            action
        )
        if reward != 0.0 or info != {}:
            raise RuntimeError("D-030 real transition crossed the boundary")
        telemetry = environment.last_transition
        if telemetry is None:
            raise RuntimeError("D-030 real transition produced no telemetry")
        next_observation = _next_visible(observation_array)
        selected_branch_consistent = False
        if branches:
            selected = branches[action]
            selected_branch_consistent = (
                selected.observation == next_observation
                and selected.terminated == terminated
                and selected.truncated == truncated
                and selected.telemetry == telemetry
            )
            all_selected_branch_matches &= selected_branch_consistent
        update = learner.observe_transition(current, action, next_observation)
        all_real_updates_executed_action_only &= update.action is action
        _update_digest(update_digest, transition_index, action, update)
        if predictions and action in predictions:
            if update.prediction != predictions[action].values:
                raise RuntimeError("D-030 executed pre-update prediction changed")

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

        if (
            arbitration is not None
            and not arbitration.delegated
            and evaluator_diagnostics
        ):
            actual_forward = {
                candidate.name: branches[candidate].delta[D030_FORWARD_OUTPUT_INDEX]
                for candidate in D030_STEERING_ACTIONS
            }
            truth = _exact_argmax(
                {
                    candidate: branches[candidate].delta[D030_FORWARD_OUTPUT_INDEX]
                    for candidate in D030_STEERING_ACTIONS
                }
            )
            learned_scores = {
                candidate: current.beacon.forward
                + predictions[candidate].values[D030_FORWARD_OUTPUT_INDEX]
                for candidate in D030_STEERING_ACTIONS
            }
            permuted_scores = {
                candidate: current.beacon.forward + score
                for candidate, score in _permuted_scores(predictions).items()
            }
            decision_records.append(
                {
                    "transition": transition_index,
                    "quarter": D030_QUARTERS[
                        (transition_index - 1) // d027.D027_WINDOW_SIZE
                    ],
                    "mode": mode_after.name,
                    "current_contact": current.charging_contact,
                    "greedy_action": arbitration.greedy_action.name,
                    "causal_action": action.name,
                    "learned_action": learned_action.name if learned_action else None,
                    "permuted_action": permuted_action.name
                    if permuted_action
                    else None,
                    "truth_argmax": [candidate.name for candidate in truth],
                    "causal_is_optimal": action in truth,
                    "greedy_is_optimal": arbitration.greedy_action in truth,
                    "learned_is_optimal": learned_action in truth
                    if learned_action
                    else None,
                    "permuted_is_optimal": permuted_action in truth
                    if permuted_action
                    else None,
                    "learned_agrees_greedy": learned_action
                    is arbitration.greedy_action,
                    "permuted_agrees_greedy": permuted_action
                    is arbitration.greedy_action,
                    "actual_delta_beacon_forward": actual_forward,
                    "learned_score_margin": _score_margin(learned_scores),
                    "permuted_score_margin": _score_margin(permuted_scores),
                    "move_forward_boundary": branches[
                        Action.MOVE_FORWARD
                    ].boundary_class,
                    "selected_branch_consistent": (selected_branch_consistent),
                }
            )

        if mode_before is d026.D026Mode.SEEK and mode_after is d026.D026Mode.CHARGE:
            charge_entries += 1
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
            active_seek = d025._new_seek_episode(
                transition_index=transition_index,
                observation=current,
                action=action,
                position=telemetry.position_after,
                heading=telemetry.heading,
                station=telemetry.station_center,
                legacy_contact=d024.legacy_circular_contact(
                    telemetry.position_before,
                    telemetry.station_center,
                    environment.config,
                ),
            )
            seek_episodes.append(active_seek)
            if cycle_stage == 2:
                cycle_stage = 3
        if active_seek is not None:
            d025._update_seek_geometry(
                active_seek,
                position=telemetry.position_after,
                heading=telemetry.heading,
                station=telemetry.station_center,
                transition_index=transition_index,
            )
            if (
                not telemetry.charging_contact_before
                and telemetry.charging_contact_after
            ):
                active_seek["outcome"] = "reacquired"
                active_seek["reacquisition_transition"] = transition_index
                active_seek["transitions_since_seek_entry"] = transition_index - cast(
                    int, active_seek["seek_entry_transition"]
                )
                active_seek["energy_at_reacquisition"] = float(observation_array[0])
                active_seek["temperature_normalized_at_reacquisition"] = float(
                    observation_array[5]
                )
                active_seek["reacquisition_action"] = action.name
                reacquisitions += 1
                recharge_active = True
                if cycle_stage == 3:
                    cycle_stage = 4
                active_seek = None
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

        minimum_energy = min(minimum_energy, next_observation.energy)
        maximum_energy = max(maximum_energy, next_observation.energy)
        minimum_temperature = min(minimum_temperature, next_observation.thermal)
        maximum_temperature = max(maximum_temperature, next_observation.thermal)
        current = next_observation

    if active_seek is not None:
        active_seek["outcome"] = (
            "terminated_before_reacquisition" if terminated else "horizon_censored"
        )
    final_telemetry = environment.last_transition
    if final_telemetry is None:
        raise RuntimeError("D-030 run ended without final telemetry")
    outcome = (
        "FULL_CYCLE"
        if reacquisitions and full_recharges and redepartures
        else "SEEK_REACQUIRED"
        if reacquisitions
        else "HORIZON_CENSORED"
        if truncated
        else "FAILED_SEEK"
    )
    arbitration_summary = {
        "false_contact_seek_decisions": len(arbitration_records),
        "stochastic_delegation_decisions": sum(
            int(cast(bool, record["delegated"])) for record in arbitration_records
        ),
        "one_policy_rng_draw_per_decision": True,
        "delegation_probability": D030_SEEK_DELEGATION_PROBABILITY,
        "delegation_probability_expression": "1.0 / 3.0",
        "explorer_internal_hazard": D030_EXPLORER_HAZARD,
        "explorer_internal_hazard_expression": "1.0 / 8.0",
        "delegated_actions_by_action_type": {
            action.name: sum(
                int(
                    cast(bool, record["delegated"])
                    and record["historical_action"] == action.name
                )
                for record in arbitration_records
            )
            for action in Action
        },
        "effective_perturbations": sum(
            int(record["historical_action"] != record["greedy_beacon_action"])
            for record in arbitration_records
        ),
        "delegated_effective_perturbations": sum(
            int(
                cast(bool, record["delegated"])
                and record["historical_action"] != record["greedy_beacon_action"]
            )
            for record in arbitration_records
        ),
        "greedy_beacon_action_counts": {
            action.name: sum(
                int(record["greedy_beacon_action"] == action.name)
                for record in arbitration_records
            )
            for action in Action
        },
        "historical_action_counts": {
            action.name: sum(
                int(record["historical_action"] == action.name)
                for record in arbitration_records
            )
            for action in Action
        },
        "decision_records_retained": False,
    }
    final_weights = learner.weight_snapshot()
    return {
        "arm": arm,
        "seed": seed,
        "outcome_classification": outcome,
        "transitions": transitions,
        "physical_seconds": transitions * environment.config.dt_seconds,
        "terminated": terminated,
        "truncated": truncated,
        "termination_reason": _termination_reason(environment, terminated, truncated),
        "final_mode": controller.mode.name,
        "action_counts": action_counts,
        "mode_occupancy": mode_occupancy,
        "mode_entry_counts": mode_entry_counts,
        "battery_normalized": {
            "start": d024.D024_INITIAL_BATTERY_J
            / environment.config.battery_capacity_j,
            "minimum": minimum_energy,
            "final": current.energy,
            "maximum": maximum_energy,
        },
        "temperature_normalized": {
            "start": initial_temperature,
            "minimum": minimum_temperature,
            "final": current.thermal,
            "maximum": maximum_temperature,
        },
        "full_departures": full_departures,
        "physical_charger_exits": charger_exits,
        "low_energy_seek_entries": seek_entries,
        "physical_reacquisitions": reacquisitions,
        "charge_entries": charge_entries,
        "full_recharge_events": full_recharges,
        "post_recharge_redepartures": redepartures,
        "completed_energy_regulation_cycles": completed_cycles,
        "seek_episodes": seek_episodes,
        "seek_arbitration": arbitration_summary,
        "prediction_query_count": prediction_query_count,
        "branch_evaluation_count": branch_evaluation_count,
        "diagnostics": _aggregate_diagnostics(decision_records),
        "isolation": {
            "all_prediction_queries_read_only": all_prediction_queries_read_only,
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
            "evaluator_diagnostics_enabled": evaluator_diagnostics,
            "branch_outcomes_causal": False,
        },
        "trajectory_digest": d027._trace_digest(trace),
        "executed_update_digest": update_digest.hexdigest(),
        "final_weights": final_weights,
        "final_weight_digest": _digest(tuple(learner.weights)),
        "final_policy_rng_digest": _digest(streams.policy.bit_generator.state),
        "final_environment_rng_digest": _digest(
            streams.environment.bit_generator.state
        ),
        "_decision_records": decision_records,
        "_weights": tuple(learner.weights),
    }


def _run_lifetime(
    seed: int,
    *,
    arm: str = "REFERENCE_NO_INFLUENCE",
    horizon: int = D030_HORIZON,
    audit: bool = True,
) -> dict[str, object]:
    """Run one uninterrupted D-030 arm, using D-029-compatible naming."""
    return _run_arm(
        seed,
        arm=arm,
        horizon=horizon,
        evaluator_diagnostics=audit,
    )


def _aggregate_diagnostics(records: Sequence[dict[str, object]]) -> dict[str, object]:
    def selection(
        name: str, subset: Sequence[dict[str, object]] = records
    ) -> dict[str, object]:
        usable = [record for record in subset if record.get(name) is not None]
        correct = sum(int(cast(bool, record[name])) for record in usable)
        return {
            "sample_count": len(usable),
            "optimal_count": correct,
            "optimal_fraction": correct / len(usable) if usable else None,
        }

    def agreement(
        name: str, subset: Sequence[dict[str, object]] = records
    ) -> dict[str, int]:
        usable = [record for record in subset if record.get(name) is not None]
        equal = sum(int(cast(bool, record[name])) for record in usable)
        return {
            "sample_count": len(usable),
            "agree_count": equal,
            "disagree_count": len(usable) - equal,
        }

    margins: dict[str, list[float]] = {"learned": [], "permuted": []}
    actual_sums = {action.name: 0.0 for action in D030_STEERING_ACTIONS}
    boundary: dict[str, dict[str, int]] = {
        category: {
            "branch_count": 0,
            "causal_move_forward_count": 0,
            "greedy_move_forward_count": 0,
            "learned_move_forward_count": 0,
            "permuted_move_forward_count": 0,
        }
        for category in D030_BOUNDARY_CLASSES
    }
    for record in records:
        margins["learned"].append(cast(float, record["learned_score_margin"]))
        margins["permuted"].append(cast(float, record["permuted_score_margin"]))
        for action in D030_STEERING_ACTIONS:
            actual_sums[action.name] += cast(
                dict[str, float], record["actual_delta_beacon_forward"]
            )[action.name]
        category = record["move_forward_boundary"]
        if category is not None:
            values = boundary[cast(str, category)]
            values["branch_count"] += 1
            values["causal_move_forward_count"] += int(
                record["causal_action"] == Action.MOVE_FORWARD.name
            )
            values["greedy_move_forward_count"] += int(
                record["greedy_action"] == Action.MOVE_FORWARD.name
            )
            values["learned_move_forward_count"] += int(
                record["learned_action"] == Action.MOVE_FORWARD.name
            )
            values["permuted_move_forward_count"] += int(
                record["permuted_action"] == Action.MOVE_FORWARD.name
            )

    by_quarter = {
        quarter: {
            "causal_choice_fidelity": selection(
                "causal_is_optimal", [r for r in records if r["quarter"] == quarter]
            ),
            "greedy_choice_fidelity": selection(
                "greedy_is_optimal", [r for r in records if r["quarter"] == quarter]
            ),
            "learned_choice_fidelity": selection(
                "learned_is_optimal", [r for r in records if r["quarter"] == quarter]
            ),
            "permuted_choice_fidelity": selection(
                "permuted_is_optimal", [r for r in records if r["quarter"] == quarter]
            ),
        }
        for quarter in D030_QUARTERS
    }
    return {
        "non_delegated_seek_decisions": len(records),
        "causal_choice_fidelity": selection("causal_is_optimal"),
        "greedy_choice_fidelity": selection("greedy_is_optimal"),
        "learned_choice_fidelity": selection("learned_is_optimal"),
        "permuted_choice_fidelity": selection("permuted_is_optimal"),
        "learned_vs_greedy": agreement("learned_agrees_greedy"),
        "permuted_vs_greedy": agreement("permuted_agrees_greedy"),
        "score_margin": {
            name: {
                "mean": statistics.fmean(values) if values else None,
                "minimum": min(values) if values else None,
                "maximum": max(values) if values else None,
            }
            for name, values in margins.items()
        },
        "actual_delta_beacon_forward_mean_by_candidate": {
            action: actual_sums[action] / len(records) if records else None
            for action in actual_sums
        },
        "boundary_class_selection": boundary,
        "by_quarter": by_quarter,
        "selected_action_branch_consistency": {
            "sample_count": len(records),
            "exact_count": sum(
                int(cast(bool, record["selected_branch_consistent"]))
                for record in records
            ),
        },
    }


def _summary_fields(result: dict[str, object]) -> tuple[object, ...]:
    return tuple(
        result[name]
        for name in (
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
            "full_departures",
            "physical_charger_exits",
            "low_energy_seek_entries",
            "physical_reacquisitions",
            "full_recharge_events",
            "post_recharge_redepartures",
            "completed_energy_regulation_cycles",
        )
    )


def _latencies(result: dict[str, object]) -> list[float]:
    return [
        cast(float, episode["transitions_since_seek_entry"])
        for episode in cast(list[dict[str, object]], result["seek_episodes"])
        if episode["outcome"] == "reacquired"
    ]


def _behavior_summary(results: Sequence[dict[str, object]]) -> dict[str, object]:
    latencies = [latency for result in results for latency in _latencies(result)]
    energies = [
        cast(float, episode["energy_at_reacquisition"])
        for result in results
        for episode in cast(list[dict[str, object]], result["seek_episodes"])
        if episode["outcome"] == "reacquired"
    ]
    counts = {
        name: sum(int(result["outcome_classification"] == name) for result in results)
        for name in ("FULL_CYCLE", "SEEK_REACQUIRED", "FAILED_SEEK", "HORIZON_CENSORED")
    }
    return {
        "classification_counts": counts,
        "transitions": sum(cast(int, result["transitions"]) for result in results),
        "resolved_seek_count": len(latencies),
        "resolved_seek_latency": {
            "mean": statistics.fmean(latencies) if latencies else None,
            "median": statistics.median(latencies) if latencies else None,
            "p90_nearest_rank": sorted(latencies)[
                max(0, math.ceil(0.90 * len(latencies)) - 1)
            ]
            if latencies
            else None,
            "p95_nearest_rank": sorted(latencies)[
                max(0, math.ceil(0.95 * len(latencies)) - 1)
            ]
            if latencies
            else None,
            "maximum": max(latencies, default=None),
            "percentile_method": "nearest-rank",
        },
        "energy_at_reacquisition": {
            "mean": statistics.fmean(energies) if energies else None,
            "median": statistics.median(energies) if energies else None,
            "minimum": min(energies, default=None),
        },
        "recharge_events": sum(
            cast(int, result["full_recharge_events"]) for result in results
        ),
        "redeparture_events": sum(
            cast(int, result["post_recharge_redepartures"]) for result in results
        ),
        "energy_or_thermal_termination_count": sum(
            int(
                result["termination_reason"]
                in {
                    "energy_depletion",
                    "protective_thermal_shutdown",
                    "emergency_hard_thermal_shutdown",
                }
            )
            for result in results
        ),
    }


def _paired_latency_summary(
    left: dict[str, object], right: dict[str, object]
) -> dict[str, object]:
    differences = [
        a - b for a, b in zip(_latencies(left), _latencies(right), strict=False)
    ]
    return {
        "paired_episode_count": len(differences),
        "differences": differences,
        "mean": statistics.fmean(differences) if differences else None,
        "median": statistics.median(differences) if differences else None,
        "faster_count": sum(int(value < 0.0) for value in differences),
        "equal_count": sum(int(value == 0.0) for value in differences),
        "slower_count": sum(int(value > 0.0) for value in differences),
        "pairing": (
            "same-seed resolved SEEK episodes in occurrence order; "
            "unmatched episodes excluded"
        ),
    }


def _run_d030_seed(seed: int, *, horizon: int = D030_HORIZON) -> dict[str, object]:
    _validate_d030_seed(seed)
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon <= 0:
        raise ValueError("horizon must be a positive integer")
    enabled = {
        arm: _run_arm(seed, arm=arm, horizon=horizon, evaluator_diagnostics=True)
        for arm in D030_ARM_NAMES
    }
    disabled = {
        arm: _run_arm(seed, arm=arm, horizon=horizon, evaluator_diagnostics=False)
        for arm in ("LEARNED_FORWARD", "PERMUTED_FORWARD")
    }
    ordinary, ordinary_trace = d027._run_lifetime(seed, horizon=horizon, learning=True)
    reference = enabled["REFERENCE_NO_INFLUENCE"]
    ordinary_exact = all(
        reference[name] == ordinary[name]
        for name in (
            "transitions",
            "terminated",
            "truncated",
            "termination_reason",
            "action_counts",
            "mode_occupancy",
            "mode_entry_counts",
            "final_mode",
            "full_departures",
            "physical_charger_exits",
            "low_energy_seek_entries",
            "physical_reacquisitions",
            "full_recharge_events",
            "post_recharge_redepartures",
            "completed_energy_regulation_cycles",
        )
    ) and reference["trajectory_digest"] == d027._trace_digest(ordinary_trace)
    ordinary_update_digest = _trace_update_digest(ordinary_trace)
    ordinary_exact &= reference["executed_update_digest"] == ordinary_update_digest
    ordinary_learner = cast(d027.D027ActionConsequencePredictor, ordinary["learner"])
    ordinary_exact &= reference["_weights"] == tuple(ordinary_learner.weights)
    reference["isolation"]["matched_d027_reference"] = {  # type: ignore[index]
        "real_summary_exact_equal": ordinary_exact,
        "real_visible_trajectory_digest_exact_equal": reference["trajectory_digest"]
        == d027._trace_digest(ordinary_trace),
        "executed_action_update_digest_exact_equal": reference["executed_update_digest"]
        == ordinary_update_digest,
        "final_168_weight_snapshot_exact_equal": reference["_weights"]
        == tuple(ordinary_learner.weights),
    }
    if not ordinary_exact:
        raise RuntimeError("D-030 reference arm did not match ordinary D-027 lifetime")

    for arm, result in enabled.items():
        if arm == "REFERENCE_NO_INFLUENCE":
            continue
        no_branches = disabled[arm]
        exact = all(
            result[name] == no_branches[name]
            for name in (
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
                "full_departures",
                "physical_charger_exits",
                "low_energy_seek_entries",
                "physical_reacquisitions",
                "full_recharge_events",
                "post_recharge_redepartures",
                "completed_energy_regulation_cycles",
                "trajectory_digest",
                "executed_update_digest",
                "_weights",
                "final_policy_rng_digest",
                "final_environment_rng_digest",
            )
        )
        result["isolation"]["matched_branch_disabled"] = {  # type: ignore[index]
            "real_summary_exact_equal": exact,
            "real_visible_trajectory_digest_exact_equal": result["trajectory_digest"]
            == no_branches["trajectory_digest"],
            "executed_update_digest_exact_equal": result["executed_update_digest"]
            == no_branches["executed_update_digest"],
            "final_168_weight_snapshot_exact_equal": result["_weights"]
            == no_branches["_weights"],
            "policy_rng_state_exact_equal": result["final_policy_rng_digest"]
            == no_branches["final_policy_rng_digest"],
            "environment_rng_state_exact_equal": result["final_environment_rng_digest"]
            == no_branches["final_environment_rng_digest"],
        }
        if not exact:
            raise RuntimeError(f"D-030 {arm} evaluator branch isolation failed")

    for result in disabled.values():
        result.pop("_decision_records")
        result.pop("_weights")
    for result in enabled.values():
        result.pop("_weights")
    return {"seed": seed, "arms": enabled, "branch_disabled": disabled}


def _arm_from_seed_result(result: dict[str, object], arm: str) -> dict[str, object]:
    return cast(dict[str, object], cast(dict[str, object], result["arms"])[arm])


def run_d030_probe(
    seeds: Sequence[int] = D030_DEFAULT_DEVELOPMENT_SEEDS,
    *,
    horizon: int = D030_HORIZON,
    executed_commit_sha: str | None = None,
) -> dict[str, object]:
    development_seeds = _validate_d030_development_seeds(seeds)
    if horizon != D030_HORIZON:
        raise ValueError("D-030 requires the frozen 70,000-transition horizon")
    executed_sha = _validate_executed_commit_sha(executed_commit_sha)
    results = [_run_d030_seed(seed, horizon=horizon) for seed in development_seeds]
    arms: dict[str, list[dict[str, object]]] = {
        arm: [_arm_from_seed_result(result, arm) for result in results]
        for arm in D030_ARM_NAMES
    }
    pooled: dict[str, object] = {}
    for arm in D030_ARM_NAMES:
        pooled[arm] = {
            "behavior": _behavior_summary(arms[arm]),
            "diagnostics": _aggregate_diagnostics(
                [
                    record
                    for result in arms[arm]
                    for record in cast(
                        list[dict[str, object]], result["_decision_records"]
                    )
                ]
            ),
        }
    paired = {
        f"LEARNED_FORWARD_minus_{other}": [
            {
                "seed": seed,
                **_paired_latency_summary(
                    _arm_from_seed_result(result, "LEARNED_FORWARD"),
                    _arm_from_seed_result(result, other),
                ),
            }
            for seed, result in zip(development_seeds, results, strict=True)
        ]
        for other in ("REFERENCE_NO_INFLUENCE", "PERMUTED_FORWARD")
    }
    for result in results:
        for arm in D030_ARM_NAMES:
            _arm_from_seed_result(result, arm).pop("_decision_records")
    return {
        "schema_version": 1,
        "experiment": "D-030",
        "title": "Bounded learned SEEK steering causal influence",
        "authoritative_base_sha": D030_AUTHORITATIVE_BASE_SHA,
        "base_tree_sha": D030_BASE_TREE_SHA,
        "implementation_probe_sha": executed_sha,
        "development_seeds": list(development_seeds),
        "horizon": D030_HORIZON,
        "timestep_seconds": D020PhysicalConfig().dt_seconds,
        "simulated_duration_seconds": D030_HORIZON * D020PhysicalConfig().dt_seconds,
        "lifetime": "three separate matched uninterrupted causal lifetimes per seed",
        "seed_policy": {
            "canonical_validator": "validate_exp003_development_seeds",
            "exact_declared_seeds": list(D030_DEFAULT_DEVELOPMENT_SEEDS),
            "formal_reservation_guard_preserved": True,
        },
        "freeze": {
            "controller": (
                "unchanged D026Controller; only non-delegated false-contact "
                "SEEK action may differ"
            ),
            "environment": "unchanged D026Env / D024 finite-body dual-contact physics",
            "horizon": D030_HORIZON,
            "channels": list(D030_CHANNELS),
            "outputs": list(D030_OUTPUTS),
            "learning_rate": D030_LEARNING_RATE,
            "plastic_state_dimension": D030_PLASTIC_STATE_DIMENSION,
            "candidate_actions": [action.name for action in D030_STEERING_ACTIONS],
            "wait_excluded": True,
            "forward_output": "delta_beacon_forward",
            "forward_output_index": D030_FORWARD_OUTPUT_INDEX,
            "prediction_transform": (
                "current_beacon_forward + raw predicted delta_beacon_forward"
            ),
            "tie_rule": (
                "exact floating-point unique maximum; otherwise historical greedy"
            ),
            "permutation": {
                "TURN_LEFT": "TURN_RIGHT prediction",
                "TURN_RIGHT": "MOVE_FORWARD prediction",
                "MOVE_FORWARD": "TURN_LEFT prediction",
            },
            "delegation_probability": D030_SEEK_DELEGATION_PROBABILITY,
            "delegation_probability_expression": "1.0 / 3.0",
            "explorer_internal_hazard": D030_EXPLORER_HAZARD,
            "explorer_internal_hazard_expression": "1.0 / 8.0",
            "one_policy_rng_draw_per_false_contact_seek_decision": True,
            "learned_steering_additional_rng": False,
            "begin_segment": "unchanged D026 semantics",
        },
        "arms": {
            "REFERENCE_NO_INFLUENCE": (
                "unchanged D026 action; predictions are shadow-only"
            ),
            "LEARNED_FORWARD": (
                "raw delta_beacon_forward unique maximum on non-delegated "
                "false-contact SEEK only"
            ),
            "PERMUTED_FORWARD": (
                "same intervention with fixed cyclic prediction relabeling"
            ),
        },
        "causal_order": [
            "current visible six-channel observation",
            "unchanged D026 mode logic and one delegation draw",
            (
                "historical greedy action fixed; candidate predictions queried "
                "for non-delegated false-contact SEEK"
            ),
            "Arm B/C causal action fixed; Arm A remains greedy",
            "evaluator-only isolated three-candidate branches after action selection",
            "real transition",
            "actual next visible observation",
            "unchanged executed-action-only D027 update",
            "evaluator-only diagnostics",
        ],
        "organism_boundary": {
            "reward": 0.0,
            "info": {},
            "evaluator_branch_truth_reaches_controller_or_learner": False,
        },
        "pooled": pooled,
        "paired_latency": paired,
        "results": results,
        "interpretation": {
            "lane": "Development",
            "confirmatory_claim": False,
            "negative_result_rules_frozen": True,
            "exact_revisit_knowledge_claim": False,
            "planning_or_general_counterfactual_claim": False,
        },
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the D-030 causal steering probe.")
    parser.add_argument(
        "--seeds", type=int, nargs="+", default=list(D030_DEFAULT_DEVELOPMENT_SEEDS)
    )
    parser.add_argument("--horizon", type=int, default=D030_HORIZON)
    parser.add_argument("--executed-commit-sha")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    payload = json.dumps(
        run_d030_probe(
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
        print(f"D-030 result written to {args.output}")


if __name__ == "__main__":
    main()
