"""D-031R1 learned SEEK scaffold-displacement development probe.

D-031R1 keeps the merged D-030 learned steering intervention and disables only
the false-contact SEEK stochastic delegation in the two no-de-trapping arms.
The retained policy-RNG arbitration draw, inherited AWAY explorer, D-027
learner, D-024 contact geometry, and D-020 physical transition remain shared
with the earlier development stages.  Branch truth and all outcome metrics are
evaluator-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pickle
import statistics
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any, Final, Sequence, cast

import numpy as np

from . import d024, d025, d026, d027, d029, d030
from .d020 import D020PhysicalConfig
from .env import Action
from .exp001 import ExternalObservation, StochasticPersistentExplorer
from .exp003 import EXP003_B50_ENTER_SEEK_THRESHOLD
from .exp003_seed_policy import validate_exp003_development_seeds
from .rng import RandomStreams

D031R1_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = tuple(range(18468, 18488))
D031R1_CANONICAL_VISUALIZATION_SEED: Final[int] = D031R1_DEFAULT_DEVELOPMENT_SEEDS[0]
D031R1_HORIZON: Final[int] = 70_000
D031R1_AUTHORITATIVE_BASE_SHA: Final[str] = (
    "b05d1ee094d999c0acf13126b7374ed11966e3f9"
)
D031R1_BASE_TREE_SHA: Final[str] = "ceed52790b1fa3726fe2e44a28c6c56f10272258"
D031R1_SEEK_DELEGATION_PROBABILITY: Final[float] = d026.D026_SEEK_DELEGATION_PROBABILITY
D031R1_NO_DETRAP_DELEGATION_PROBABILITY: Final[float] = 0.0
D031R1_EXPLORER_HAZARD: Final[float] = 1.0 / 8.0
D031R1_LEARNING_RATE: Final[float] = d027.D027_LEARNING_RATE
D031R1_PLASTIC_STATE_DIMENSION: Final[int] = d027.D027_PLASTIC_STATE_DIMENSION
D031R1_CHANNELS: Final[tuple[str, ...]] = d027.D027_CHANNELS
D031R1_OUTPUTS: Final[tuple[str, ...]] = d027.D027_OUTPUTS
D031R1_FORWARD_OUTPUT_INDEX: Final[int] = D031R1_OUTPUTS.index("delta_beacon_forward")
D031R1_STEERING_ACTIONS: Final[tuple[Action, ...]] = (
    Action.TURN_LEFT,
    Action.TURN_RIGHT,
    Action.MOVE_FORWARD,
)
D031R1_ARM_NAMES: Final[tuple[str, ...]] = (
    "LEARNED_WITH_DETRAP",
    "LEARNED_NO_DETRAP",
    "GREEDY_NO_DETRAP",
)
D031R1_NO_DETRAP_ARMS: Final[tuple[str, ...]] = (
    "LEARNED_NO_DETRAP",
    "GREEDY_NO_DETRAP",
)
D031R1_BOUNDARY_CLASSES: Final[tuple[str, ...]] = (
    "FULL_NOMINAL_FORWARD",
    "BOUNDARY_CLIPPED_FORWARD",
    "FULL_STALL_FORWARD",
)
D031R1_QUARTERS: Final[tuple[str, ...]] = ("Q1", "Q2", "Q3", "Q4")


def _validate_d031r1_development_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    """Apply the canonical reservation guard and exact D-031R1 seed guard."""
    validated = validate_exp003_development_seeds(seeds)
    if validated != D031R1_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-031R1 requires exactly the frozen development seeds "
            f"{D031R1_DEFAULT_DEVELOPMENT_SEEDS}; got {validated}"
        )
    return validated


def _validate_d031r1_seed(seed: int) -> None:
    validated = validate_exp003_development_seeds((seed,))
    if validated[0] not in D031R1_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-031R1 may execute only predeclared development seeds "
            f"{D031R1_DEFAULT_DEVELOPMENT_SEEDS}; got {validated}"
        )


def _validate_executed_commit_sha(value: str | None) -> str | None:
    return d027._validate_executed_commit_sha(value)


class D031R1NoDetrapController(d026.D026Controller):
    """D-026 controller with only false-contact SEEK delegation disabled."""

    seek_delegation_probability = D031R1_NO_DETRAP_DELEGATION_PROBABILITY

    def __init__(self, policy_rng: np.random.Generator) -> None:
        super().__init__(policy_rng)
        self.false_contact_seek_explorer_calls = 0
        self.explorer = _D031R1CountingExplorer(policy_rng, self)


class _D031R1CountingExplorer(StochasticPersistentExplorer):
    """Evaluator counter proving the no-de-trapping SEEK path is unreachable."""

    def __init__(
        self, policy_rng: np.random.Generator, owner: D031R1NoDetrapController
    ) -> None:
        super().__init__(policy_rng)
        self.owner = owner

    def act(self, observation: ExternalObservation) -> Action:
        if self.owner.mode is d026.D026Mode.SEEK:
            self.owner.false_contact_seek_explorer_calls += 1
        return super().act(observation)


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
        raise RuntimeError("D-031R1 reset crossed the information boundary")
    if environment.body is None or environment.station_center is None:
        raise RuntimeError("D-031R1 reset did not initialize evaluator geometry")
    if not environment.charging_contact:
        raise RuntimeError("D-024 exact initial pose is not in dual contact")
    return environment, observation, streams


def _next_visible(observation: np.ndarray) -> d027.D027Observation:
    return d025._controller_observation(observation)


def _query_candidate_predictions(
    learner: d027.D027ActionConsequencePredictor,
    current: d027.D027Observation,
) -> tuple[dict[Action, d027.D027Prediction], bool]:
    """Query exactly the three steering heads without changing the learner."""
    before = learner.weights
    predictions = {
        action: learner.predict(current, action) for action in D031R1_STEERING_ACTIONS
    }
    return predictions, learner.weights == before


def _choose_steering_action(
    current: d027.D027Observation,
    predictions: dict[Action, d027.D027Prediction],
    greedy_action: Action,
) -> Action:
    """Reuse D-030's raw forward-delta maximum and tie fallback exactly."""
    return d030._choose_steering_action(current, predictions, greedy_action)


def _exact_argmax(scores: dict[Action, float]) -> tuple[Action, ...]:
    maximum = max(scores.values())
    return tuple(
        action for action in D031R1_STEERING_ACTIONS if scores[action] == maximum
    )


def _score_margin(scores: dict[Action, float]) -> float:
    values = sorted(scores.values(), reverse=True)
    return values[0] - values[1]


def _evaluate_steering_branches(
    environment: d026.D026Env, current: d027.D027Observation
) -> dict[Action, d029._BranchOutcome]:
    return {
        action: d029._branch(environment, current, action)
        for action in D031R1_STEERING_ACTIONS
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
    return d030._trace_update_digest(trace)


def _mode_counts() -> dict[str, int]:
    return {mode.name: 0 for mode in d026.D026Mode}


def _run_arm(
    seed: int,
    *,
    arm: str,
    horizon: int,
    evaluator_diagnostics: bool,
    trace_sink: list[d025.D025TransitionTrace] | None = None,
    seed_validator: Callable[[int], None] | None = None,
) -> dict[str, object]:
    if arm not in D031R1_ARM_NAMES:
        raise ValueError(f"unknown D-031R1 arm: {arm}")
    if seed_validator is None:
        _validate_d031r1_seed(seed)
    else:
        seed_validator(seed)
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon <= 0:
        raise ValueError("horizon must be a positive integer")

    environment, observation_array, streams = _initial_environment(horizon, seed)
    controller: d026.D026Controller
    if arm in D031R1_NO_DETRAP_ARMS:
        controller = D031R1NoDetrapController(streams.policy)
    else:
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
            raise RuntimeError("D-031R1 evaluator geometry disappeared")
        mode_before = controller.mode
        mode_occupancy[mode_before.name] += 1
        historical_action = controller.act(current)
        mode_after = controller.mode
        action = historical_action
        arbitration = controller.last_arbitration
        predictions: dict[Action, d027.D027Prediction] = {}
        learned_action: Action | None = None
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
                raise RuntimeError(
                    "D-031R1 arbitration used outside false-contact SEEK"
                )
            arbitration_records.append(
                {
                    "transition": transition_index,
                    "greedy_beacon_action": arbitration.greedy_action.name,
                    "historical_action": historical_action.name,
                    "delegation_draw": arbitration.delegation_draw,
                    "delegated": arbitration.delegated,
                }
            )
            # Arms A and B use predictions causally.  Arm C fixes the historical
            # greedy action first and queries predictions only for diagnostics.
            if not arbitration.delegated and (
                arm in ("LEARNED_WITH_DETRAP", "LEARNED_NO_DETRAP")
                or evaluator_diagnostics
            ):
                predictions, read_only = _query_candidate_predictions(learner, current)
                all_prediction_queries_read_only &= read_only
                prediction_query_count += len(predictions)
                learned_action = _choose_steering_action(
                    current, predictions, arbitration.greedy_action
                )
                if arm in ("LEARNED_WITH_DETRAP", "LEARNED_NO_DETRAP"):
                    action = learned_action

            if not arbitration.delegated and evaluator_diagnostics:
                if not predictions or learned_action is None:
                    raise RuntimeError("D-031R1 evaluator prediction query missing")
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
            raise RuntimeError("D-031R1 real transition crossed the boundary")
        telemetry = environment.last_transition
        if telemetry is None:
            raise RuntimeError("D-031R1 real transition produced no telemetry")
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
        if (
            arm != "GREEDY_NO_DETRAP"
            and predictions
            and action in predictions
            and update.prediction != predictions[action].values
        ):
            raise RuntimeError("D-031R1 executed pre-update prediction changed")

        record = d025._make_trace(
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
        trace.append(record)
        if trace_sink is not None:
            trace_sink.append(record)
        transitions += 1

        if (
            arbitration is not None
            and not arbitration.delegated
            and evaluator_diagnostics
        ):
            actual_forward = {
                candidate.name: branches[candidate].delta[D031R1_FORWARD_OUTPUT_INDEX]
                for candidate in D031R1_STEERING_ACTIONS
            }
            truth = _exact_argmax(
                {
                    candidate: branches[candidate].delta[D031R1_FORWARD_OUTPUT_INDEX]
                    for candidate in D031R1_STEERING_ACTIONS
                }
            )
            learned_scores = {
                candidate: current.beacon.forward
                + predictions[candidate].values[D031R1_FORWARD_OUTPUT_INDEX]
                for candidate in D031R1_STEERING_ACTIONS
            }
            decision_records.append(
                {
                    "transition": transition_index,
                    "quarter": D031R1_QUARTERS[
                        (transition_index - 1) // d027.D027_WINDOW_SIZE
                    ],
                    "mode": mode_after.name,
                    "current_contact": current.charging_contact,
                    "greedy_action": arbitration.greedy_action.name,
                    "causal_action": action.name,
                    "learned_action": learned_action.name if learned_action else None,
                    "truth_argmax": [candidate.name for candidate in truth],
                    "causal_is_optimal": action in truth,
                    "greedy_is_optimal": arbitration.greedy_action in truth,
                    "learned_is_optimal": learned_action in truth
                    if learned_action
                    else None,
                    "learned_agrees_greedy": learned_action
                    is arbitration.greedy_action,
                    "causal_agrees_greedy": action is arbitration.greedy_action,
                    "actual_delta_beacon_forward": actual_forward,
                    "learned_score_margin": _score_margin(learned_scores),
                    "move_forward_boundary": branches[
                        Action.MOVE_FORWARD
                    ].boundary_class,
                    "selected_branch_consistent": selected_branch_consistent,
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
    if environment.last_transition is None:
        raise RuntimeError("D-031R1 run ended without final telemetry")
    outcome = (
        "FULL_CYCLE"
        if reacquisitions and full_recharges and redepartures
        else "SEEK_REACQUIRED"
        if reacquisitions
        else "HORIZON_CENSORED"
        if truncated
        else "FAILED_SEEK"
    )
    no_detrap_explorer_calls = (
        controller.false_contact_seek_explorer_calls
        if isinstance(controller, D031R1NoDetrapController)
        else 0
    )
    delegation_summary = {
        "false_contact_seek_decisions": len(arbitration_records),
        "stochastic_delegation_decisions": sum(
            int(cast(bool, record["delegated"])) for record in arbitration_records
        ),
        "delegation_probability": (
            D031R1_SEEK_DELEGATION_PROBABILITY
            if arm == "LEARNED_WITH_DETRAP"
            else D031R1_NO_DETRAP_DELEGATION_PROBABILITY
        ),
        "delegation_probability_expression": (
            "1.0 / 3.0" if arm == "LEARNED_WITH_DETRAP" else "0.0"
        ),
        "explorer_internal_hazard": D031R1_EXPLORER_HAZARD,
        "explorer_internal_hazard_expression": "1.0 / 8.0",
        "one_policy_rng_draw_per_decision": True,
        "legacy_arbitration_draw_count": len(arbitration_records),
        "false_contact_seek_explorer_calls": no_detrap_explorer_calls,
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
        "seek_arbitration": delegation_summary,
        "seek_segment_starts": controller.seek_segment_starts,
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
            "zero_false_contact_seek_delegation": (
                arm in D031R1_NO_DETRAP_ARMS
                and delegation_summary["stochastic_delegation_decisions"] == 0
            ),
            "one_legacy_arbitration_draw_per_false_contact_seek_decision": (
                delegation_summary["legacy_arbitration_draw_count"]
                == delegation_summary["false_contact_seek_decisions"]
            ),
            "no_false_contact_seek_explorer_call": (
                arm not in D031R1_NO_DETRAP_ARMS or no_detrap_explorer_calls == 0
            ),
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


def _selection(
    records: Sequence[dict[str, object]], field: str
) -> dict[str, object]:
    usable = [record for record in records if record.get(field) is not None]
    optimal_count = sum(cast(bool, record[field]) for record in usable)
    return {
        "sample_count": len(usable),
        "optimal_count": optimal_count,
        "optimal_fraction": optimal_count / len(usable) if usable else None,
    }


def _agreement(
    records: Sequence[dict[str, object]], field: str
) -> dict[str, int]:
    usable = [record for record in records if record.get(field) is not None]
    agree_count = sum(cast(bool, record[field]) for record in usable)
    return {
        "sample_count": len(usable),
        "agree_count": agree_count,
        "disagree_count": len(usable) - agree_count,
    }


def _aggregate_diagnostics(records: Sequence[dict[str, object]]) -> dict[str, object]:
    actual_sums = {action.name: 0.0 for action in D031R1_STEERING_ACTIONS}
    margins: list[float] = []
    boundary: dict[str, dict[str, int]] = {
        category: {
            "branch_count": 0,
            "causal_move_forward_count": 0,
            "greedy_move_forward_count": 0,
            "learned_move_forward_count": 0,
        }
        for category in D031R1_BOUNDARY_CLASSES
    }
    for record in records:
        margins.append(cast(float, record["learned_score_margin"]))
        actual = cast(dict[str, float], record["actual_delta_beacon_forward"])
        for action in D031R1_STEERING_ACTIONS:
            actual_sums[action.name] += actual[action.name]
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

    by_quarter = {
        quarter: {
            "causal_choice_fidelity": _selection(
                [record for record in records if record["quarter"] == quarter],
                "causal_is_optimal",
            ),
            "greedy_choice_fidelity": _selection(
                [record for record in records if record["quarter"] == quarter],
                "greedy_is_optimal",
            ),
            "learned_choice_fidelity": _selection(
                [record for record in records if record["quarter"] == quarter],
                "learned_is_optimal",
            ),
            "learned_vs_greedy": _agreement(
                [record for record in records if record["quarter"] == quarter],
                "learned_agrees_greedy",
            ),
        }
        for quarter in D031R1_QUARTERS
    }
    by_boundary = {
        category: {
            "causal_choice_fidelity": _selection(
                [
                    record
                    for record in records
                    if record["move_forward_boundary"] == category
                ],
                "causal_is_optimal",
            ),
            "greedy_choice_fidelity": _selection(
                [
                    record
                    for record in records
                    if record["move_forward_boundary"] == category
                ],
                "greedy_is_optimal",
            ),
            "learned_choice_fidelity": _selection(
                [
                    record
                    for record in records
                    if record["move_forward_boundary"] == category
                ],
                "learned_is_optimal",
            ),
            "learned_vs_greedy": _agreement(
                [
                    record
                    for record in records
                    if record["move_forward_boundary"] == category
                ],
                "learned_agrees_greedy",
            ),
        }
        for category in D031R1_BOUNDARY_CLASSES
    }
    return {
        "non_delegated_seek_decisions": len(records),
        "causal_choice_fidelity": _selection(records, "causal_is_optimal"),
        "greedy_choice_fidelity": _selection(records, "greedy_is_optimal"),
        "learned_choice_fidelity": _selection(records, "learned_is_optimal"),
        "learned_vs_greedy": _agreement(records, "learned_agrees_greedy"),
        "causal_vs_greedy": _agreement(records, "causal_agrees_greedy"),
        "score_margin": {
            "learned": {
                "mean": statistics.fmean(margins) if margins else None,
                "minimum": min(margins) if margins else None,
                "maximum": max(margins) if margins else None,
            }
        },
        "actual_delta_beacon_forward_mean_by_candidate": {
            action: actual_sums[action] / len(records) if records else None
            for action in actual_sums
        },
        "boundary_class_selection": boundary,
        "by_quarter": by_quarter,
        "by_boundary": by_boundary,
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


def _reacquisition_energies(result: dict[str, object]) -> list[float]:
    return [
        cast(float, episode["energy_at_reacquisition"])
        for episode in cast(list[dict[str, object]], result["seek_episodes"])
        if episode["outcome"] == "reacquired"
    ]


def _nearest_rank(values: Sequence[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(percentile * len(ordered)))
    return ordered[rank - 1]


def _behavior_summary(results: Sequence[dict[str, object]]) -> dict[str, object]:
    latencies = [latency for result in results for latency in _latencies(result)]
    energies = [
        energy for result in results for energy in _reacquisition_energies(result)
    ]
    classifications = (
        "FULL_CYCLE",
        "SEEK_REACQUIRED",
        "FAILED_SEEK",
        "HORIZON_CENSORED",
    )
    return {
        "classification_counts": {
            name: sum(
                int(result["outcome_classification"] == name) for result in results
            )
            for name in classifications
        },
        "transitions": sum(cast(int, result["transitions"]) for result in results),
        "resolved_seek_count": len(latencies),
        "resolved_seek_latency": {
            "mean": statistics.fmean(latencies) if latencies else None,
            "median": statistics.median(latencies) if latencies else None,
            "p90_nearest_rank": _nearest_rank(latencies, 0.90),
            "p95_nearest_rank": _nearest_rank(latencies, 0.95),
            "maximum": max(latencies, default=None),
            "percentile_method": "nearest-rank",
        },
        "energy_at_reacquisition": {
            "mean": statistics.fmean(energies) if energies else None,
            "median": statistics.median(energies) if energies else None,
            "minimum": min(energies, default=None),
        },
        "reacquisition_count": sum(
            cast(int, result["physical_reacquisitions"]) for result in results
        ),
        "full_recharge_count": sum(
            cast(int, result["full_recharge_events"]) for result in results
        ),
        "redeparture_count": sum(
            cast(int, result["post_recharge_redepartures"]) for result in results
        ),
        "completed_cycle_count": sum(
            cast(int, result["completed_energy_regulation_cycles"])
            for result in results
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
        "minimum_normalized_energy": min(
            cast(dict[str, float], result["battery_normalized"])["minimum"]
            for result in results
        ),
        "maximum_normalized_temperature": max(
            cast(dict[str, float], result["temperature_normalized"])["maximum"]
            for result in results
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


def _paired_summary(
    left: dict[str, object], right: dict[str, object]
) -> dict[str, object]:
    left_latencies = _latencies(left)
    right_latencies = _latencies(right)
    latency_differences = [
        a - b for a, b in zip(left_latencies, right_latencies, strict=False)
    ]
    left_energies = _reacquisition_energies(left)
    right_energies = _reacquisition_energies(right)
    energy_differences = [
        a - b for a, b in zip(left_energies, right_energies, strict=False)
    ]

    def stats(differences: Sequence[float]) -> dict[str, object]:
        return {
            "paired_episode_count": len(differences),
            "differences": list(differences),
            "mean": statistics.fmean(differences) if differences else None,
            "median": statistics.median(differences) if differences else None,
            "faster_or_lower_count": sum(value < 0.0 for value in differences),
            "equal_count": sum(value == 0.0 for value in differences),
            "slower_or_higher_count": sum(value > 0.0 for value in differences),
        }

    return {
        "latency": stats(latency_differences),
        "reacquisition_energy": stats(energy_differences),
        "pairing": (
            "same-seed resolved SEEK episodes in occurrence order; "
            "unmatched episodes excluded"
        ),
    }


def _compare_branch_disabled(
    enabled: dict[str, object], disabled: dict[str, object]
) -> dict[str, object]:
    exact = all(
        enabled[name] == disabled[name]
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
    return {
        "real_summary_exact_equal": exact,
        "real_visible_trajectory_digest_exact_equal": (
            enabled["trajectory_digest"] == disabled["trajectory_digest"]
        ),
        "executed_action_update_digest_exact_equal": (
            enabled["executed_update_digest"] == disabled["executed_update_digest"]
        ),
        "final_168_weight_snapshot_exact_equal": (
            enabled["_weights"] == disabled["_weights"]
        ),
        "policy_rng_state_exact_equal": (
            enabled["final_policy_rng_digest"] == disabled["final_policy_rng_digest"]
        ),
        "environment_rng_state_exact_equal": (
            enabled["final_environment_rng_digest"]
            == disabled["final_environment_rng_digest"]
        ),
    }


def _run_d031r1_seed(seed: int, *, horizon: int = D031R1_HORIZON) -> dict[str, object]:
    _validate_d031r1_seed(seed)
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon <= 0:
        raise ValueError("horizon must be a positive integer")
    enabled = {
        arm: _run_arm(seed, arm=arm, horizon=horizon, evaluator_diagnostics=True)
        for arm in D031R1_ARM_NAMES
    }
    disabled = {
        arm: _run_arm(seed, arm=arm, horizon=horizon, evaluator_diagnostics=False)
        for arm in D031R1_NO_DETRAP_ARMS
    }
    for arm in D031R1_NO_DETRAP_ARMS:
        comparison = _compare_branch_disabled(enabled[arm], disabled[arm])
        enabled[arm]["isolation"]["matched_branch_disabled"] = comparison  # type: ignore[index]
        if not comparison["real_summary_exact_equal"]:
            raise RuntimeError(f"D-031R1 {arm} evaluator branch isolation failed")

    comparisons: dict[str, list[int]] = {
        "lost_seeds": [],
        "learned_rescue_seeds": [],
        "all_three_success_seeds": [],
        "all_no_detrap_arms_failed_seeds": [],
    }
    arm_results = enabled

    def successful(result: dict[str, object]) -> bool:
        return result["outcome_classification"] in {
            "FULL_CYCLE",
            "SEEK_REACQUIRED",
        }

    if successful(arm_results["LEARNED_WITH_DETRAP"]) and not successful(
        arm_results["LEARNED_NO_DETRAP"]
    ):
        comparisons["lost_seeds"].append(seed)
    if successful(arm_results["LEARNED_NO_DETRAP"]) and not successful(
        arm_results["GREEDY_NO_DETRAP"]
    ):
        comparisons["learned_rescue_seeds"].append(seed)
    if all(successful(arm_results[arm]) for arm in D031R1_ARM_NAMES):
        comparisons["all_three_success_seeds"].append(seed)
    if not successful(arm_results["LEARNED_NO_DETRAP"]) and not successful(
        arm_results["GREEDY_NO_DETRAP"]
    ):
        comparisons["all_no_detrap_arms_failed_seeds"].append(seed)

    for result in enabled.values():
        result.pop("_weights")
    for result in disabled.values():
        result.pop("_weights")
    return {
        "seed": seed,
        "arms": enabled,
        "branch_disabled": disabled,
        "comparisons": comparisons,
    }


def _pooled_comparisons(
    results: Sequence[dict[str, object]],
) -> dict[str, object]:
    names = (
        "lost_seeds",
        "learned_rescue_seeds",
        "all_three_success_seeds",
        "all_no_detrap_arms_failed_seeds",
    )
    lists = {
        name: [
            cast(int, result["seed"])
            for result in results
            if cast(int, result["seed"])
            in cast(list[int], cast(dict[str, object], result["comparisons"])[name])
        ]
        for name in names
    }
    return {
        **lists,
        "lost_seed_count": len(lists["lost_seeds"]),
        "learned_rescue_seed_count": len(lists["learned_rescue_seeds"]),
        "all_three_success_seed_count": len(lists["all_three_success_seeds"]),
        "all_no_detrap_arms_failed_seed_count": len(
            lists["all_no_detrap_arms_failed_seeds"]
        ),
    }


def run_d031r1_probe(
    seeds: Sequence[int] = D031R1_DEFAULT_DEVELOPMENT_SEEDS,
    *,
    horizon: int = D031R1_HORIZON,
    executed_commit_sha: str | None = None,
) -> dict[str, object]:
    """Run exactly the frozen three-arm D-031R1 development protocol."""
    development_seeds = _validate_d031r1_development_seeds(seeds)
    if horizon != D031R1_HORIZON:
        raise ValueError("D-031R1 requires the frozen 70,000-transition horizon")
    executed_sha = _validate_executed_commit_sha(executed_commit_sha)
    results = [_run_d031r1_seed(seed, horizon=horizon) for seed in development_seeds]

    arms: dict[str, list[dict[str, object]]] = {
        arm: [
            cast(dict[str, object], cast(dict[str, object], result["arms"])[arm])
            for result in results
        ]
        for arm in D031R1_ARM_NAMES
    }
    pooled: dict[str, object] = {}
    for arm in D031R1_ARM_NAMES:
        arm_results = arms[arm]
        pooled[arm] = {
            "behavior": _behavior_summary(arm_results),
            "diagnostics": _aggregate_diagnostics(
                [
                    record
                    for result in arm_results
                    for record in cast(
                        list[dict[str, object]], result["_decision_records"]
                    )
                ]
            ),
            "false_contact_seek": {
                "decisions": sum(
                    cast(dict[str, int], result["seek_arbitration"])[
                        "false_contact_seek_decisions"
                    ]
                    for result in arm_results
                ),
                "delegated": sum(
                    cast(dict[str, int], result["seek_arbitration"])[
                        "stochastic_delegation_decisions"
                    ]
                    for result in arm_results
                ),
                "legacy_arbitration_draws": sum(
                    cast(dict[str, int], result["seek_arbitration"])[
                        "legacy_arbitration_draw_count"
                    ]
                    for result in arm_results
                ),
                "explorer_calls": sum(
                    cast(dict[str, int], result["seek_arbitration"])[
                        "false_contact_seek_explorer_calls"
                    ]
                    for result in arm_results
                ),
                "effective_perturbations": sum(
                    cast(dict[str, int], result["seek_arbitration"])[
                        "effective_perturbations"
                    ]
                    for result in arm_results
                ),
                "delegated_effective_perturbations": sum(
                    cast(dict[str, int], result["seek_arbitration"])[
                        "delegated_effective_perturbations"
                    ]
                    for result in arm_results
                ),
                "delegated_actions_by_action_type": {
                    action.name: sum(
                        cast(
                            dict[str, int],
                            cast(dict[str, object], result["seek_arbitration"])[
                                "delegated_actions_by_action_type"
                            ],
                        )[action.name]
                        for result in arm_results
                    )
                    for action in Action
                },
            },
        }

    paired_latency: dict[str, list[dict[str, object]]] = {}
    paired_energy: dict[str, list[dict[str, object]]] = {}
    paired_summary: dict[str, dict[str, object]] = {}
    for other in ("LEARNED_WITH_DETRAP", "GREEDY_NO_DETRAP"):
        key = f"LEARNED_NO_DETRAP_minus_{other}"
        per_seed: list[dict[str, object]] = []
        for seed, result in zip(development_seeds, results, strict=True):
            seed_arm_results = cast(dict[str, dict[str, object]], result["arms"])
            contrast = _paired_summary(
                seed_arm_results["LEARNED_NO_DETRAP"], seed_arm_results[other]
            )
            per_seed.append({"seed": seed, **contrast})
        paired_latency[key] = [
            {
                "seed": item["seed"],
                **cast(dict[str, object], item["latency"]),
            }
            for item in per_seed
        ]
        paired_energy[key] = [
            {
                "seed": item["seed"],
                **cast(dict[str, object], item["reacquisition_energy"]),
            }
            for item in per_seed
        ]
        latency_differences = [
            value
            for item in per_seed
            for value in cast(
                list[float], cast(dict[str, object], item["latency"])["differences"]
            )
        ]
        energy_differences = [
            value
            for item in per_seed
            for value in cast(
                list[float],
                cast(dict[str, object], item["reacquisition_energy"])["differences"],
            )
        ]
        paired_summary[key] = {
            "latency": _paired_values_summary(latency_differences),
            "reacquisition_energy": _paired_values_summary(energy_differences),
        }

    for arm_result_list in arms.values():
        for result in arm_result_list:
            result.pop("_decision_records")
    for result in results:
        for arm_result in cast(
            dict[str, dict[str, object]], result["branch_disabled"]
        ).values():
            arm_result.pop("_decision_records")

    return {
        "schema_version": 1,
        "experiment": "D-031R1",
        "title": "Learned SEEK scaffold displacement",
        "authoritative_base_sha": D031R1_AUTHORITATIVE_BASE_SHA,
        "base_tree_sha": D031R1_BASE_TREE_SHA,
        "implementation_probe_sha": executed_sha,
        "development_seeds": list(development_seeds),
        "horizon": D031R1_HORIZON,
        "timestep_seconds": D020PhysicalConfig().dt_seconds,
        "simulated_duration_seconds": D031R1_HORIZON * D020PhysicalConfig().dt_seconds,
        "lifetime": "three separate matched uninterrupted causal lifetimes per seed",
        "seed_policy": {
            "canonical_validator": "validate_exp003_development_seeds",
            "exact_declared_seeds": list(D031R1_DEFAULT_DEVELOPMENT_SEEDS),
            "formal_reservation_guard_preserved": True,
            "exact_d031r1_guard": True,
        },
        "freeze": {
            "controller": (
                "D-026 mode semantics; only false-contact SEEK delegation differs "
                "between the declared arms"
            ),
            "environment": "unchanged D026Env / D024 finite-body dual-contact physics",
            "horizon": D031R1_HORIZON,
            "channels": list(D031R1_CHANNELS),
            "outputs": list(D031R1_OUTPUTS),
            "feature_vector": ["bias=1.0", *D031R1_CHANNELS],
            "learning_rate": D031R1_LEARNING_RATE,
            "plastic_state_dimension": D031R1_PLASTIC_STATE_DIMENSION,
            "candidate_actions": [action.name for action in D031R1_STEERING_ACTIONS],
            "wait_excluded": True,
            "forward_output": "delta_beacon_forward",
            "forward_output_index": D031R1_FORWARD_OUTPUT_INDEX,
            "prediction_transform": (
                "current_beacon_forward + raw predicted delta_beacon_forward"
            ),
            "tie_rule": (
                "exact floating-point unique maximum; otherwise historical greedy"
            ),
            "delegation_probability_arm_a": D031R1_SEEK_DELEGATION_PROBABILITY,
            "delegation_probability_arm_b_c": D031R1_NO_DETRAP_DELEGATION_PROBABILITY,
            "delegation_probability_arm_b_c_expression": "0.0",
            "explorer_internal_hazard": D031R1_EXPLORER_HAZARD,
            "explorer_internal_hazard_expression": "1.0 / 8.0",
            "one_policy_rng_draw_per_false_contact_seek_decision": True,
            "learned_steering_additional_rng": False,
            "begin_segment": "unchanged D026 semantics; once on SEEK entry",
        },
        "arms": {
            "LEARNED_WITH_DETRAP": (
                "merged D-030 learned forward steering with 1/3 delegation"
            ),
            "LEARNED_NO_DETRAP": (
                "D-030 learned forward steering with zero SEEK delegation and "
                "one retained legacy arbitration draw"
            ),
            "GREEDY_NO_DETRAP": (
                "historical greedy SEEK action with zero SEEK delegation and "
                "one retained legacy arbitration draw; learner is shadow-only"
            ),
        },
        "causal_order": [
            "current visible six-channel observation",
            "inherited D026 mode logic and one policy-RNG arbitration draw",
            "historical greedy action computed",
            "Arm A/B learned action selection or Arm C greedy action fixed",
            "evaluator-only predictions and isolated steering branches after selection",
            "real transition",
            "actual next visible observation",
            "unchanged executed-action-only D027 update",
            "evaluator-only diagnostics",
        ],
        "programmed": {
            "actions": [action.name for action in Action],
            "d026_non_seek_behavior_unchanged": True,
            "away_explorer_unchanged": True,
            "seek_delegation_arm_a": "1/3",
            "seek_delegation_arm_b_c": "0.0",
            "no_tuned_or_adaptive_delegation": True,
        },
        "organism_visible": {
            "observation_type": "D026Observation / six ordinary D-024 channels",
            "channels": list(D031R1_CHANNELS),
            "learner_inputs": [
                "current six channels",
                "own executed action",
                "actual next six channels",
            ],
            "evaluator_state_as_input": False,
        },
        "learned": {
            "type": (
                "unchanged D-027 action-conditioned linear one-step "
                "visible-delta predictor"
            ),
            "weight_count": D031R1_PLASTIC_STATE_DIMENSION,
            "initialization": "zero once per lifetime",
            "update": "unchanged normalized LMS after every real transition",
            "arm_a_b_c_update_once_from_executed_action": True,
            "arm_c_causal_influence": False,
        },
        "evaluator_only": {
            "fields": [
                "pose, heading, station/dock geometry",
                "branch actual deltas and exact argmax set",
                "boundary classes and lifetime-quarter labels",
                "termination, cycle, latency, and reacquisition-energy metrics",
                "isolation digests and delegation labels",
            ],
            "passed_to_controller_or_learner": False,
            "branch_truth_reaches_action_selection_or_plasticity": False,
        },
        "organism_boundary": {
            "reward": 0.0,
            "info": {},
            "evaluator_branch_truth_reaches_controller_or_learner": False,
        },
        "pooled": pooled,
        "paired_latency": paired_latency,
        "paired_reacquisition_energy": paired_energy,
        "paired_summary": paired_summary,
        "comparisons": _pooled_comparisons(results),
        "results": results,
        "interpretation": {
            "lane": "Development",
            "confirmatory_claim": False,
            "negative_result_rules_frozen": True,
            "success_definition": (
                "FULL_CYCLE or SEEK_REACQUIRED for descriptive reacquisition "
                "comparisons; full-cycle viability remains separately reported"
            ),
            "lost_seed_rule": "Arm A successful and Arm B not successful",
            "learned_rescue_rule": "Arm B successful and Arm C not successful",
            "exact_revisit_knowledge_claim": False,
            "planning_or_general_counterfactual_claim": False,
            "success_authorizes_successor": False,
        },
    }


def _paired_values_summary(differences: Sequence[float]) -> dict[str, object]:
    return {
        "paired_episode_count": len(differences),
        "mean": statistics.fmean(differences) if differences else None,
        "median": statistics.median(differences) if differences else None,
        "faster_or_lower_count": sum(value < 0.0 for value in differences),
        "equal_count": sum(value == 0.0 for value in differences),
        "slower_or_higher_count": sum(value > 0.0 for value in differences),
    }


def run_d031r1_lifetime_trace(
    seed: int = D031R1_CANONICAL_VISUALIZATION_SEED,
    *,
    arm: str = "LEARNED_WITH_DETRAP",
    horizon: int = D031R1_HORIZON,
) -> tuple[d025.D025TransitionTrace, ...]:
    """Run one branch-disabled D-031R1 arm and retain its causal trace."""
    _validate_d031r1_seed(seed)
    if arm not in D031R1_ARM_NAMES:
        raise ValueError(f"unknown D-031R1 arm: {arm}")
    if horizon != D031R1_HORIZON:
        raise ValueError(
            "D-031R1 lifetime traces require the frozen 70,000-transition horizon"
        )
    trace: list[d025.D025TransitionTrace] = []
    result = _run_arm(
        seed,
        arm=arm,
        horizon=horizon,
        evaluator_diagnostics=False,
        trace_sink=trace,
    )
    if not trace or result["transitions"] != len(trace):
        raise RuntimeError("D-031R1 lifetime trace disagrees with the run")
    final_telemetry = trace[-1].telemetry
    naturally_terminated = (
        len(trace) < horizon
        and final_telemetry.terminated
        and not final_telemetry.truncated
    )
    horizon_censored = (
        len(trace) == horizon
        and not final_telemetry.terminated
        and final_telemetry.truncated
    )
    if not naturally_terminated and not horizon_censored:
        raise RuntimeError("D-031R1 lifetime trace has an invalid terminal state")
    return tuple(trace)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the D-031R1 scaffold probe.")
    parser.add_argument(
        "--seeds", type=int, nargs="+", default=list(D031R1_DEFAULT_DEVELOPMENT_SEEDS)
    )
    parser.add_argument("--horizon", type=int, default=D031R1_HORIZON)
    parser.add_argument("--executed-commit-sha")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    payload = json.dumps(
        run_d031r1_probe(
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
        print(f"D-031R1 result written to {args.output}")


if __name__ == "__main__":
    main()
