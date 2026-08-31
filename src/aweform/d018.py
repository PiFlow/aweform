"""D-018 evaluator-only action-alternative consequence audit.

The unchanged D-014 controller remains the sole source of real actions and the
unchanged D-013 predictor learns only from physically executed transitions.
Evaluator branches are exact deep copies of the live D-002 environment and
are used only to score one-step consequences for all four candidate actions.
"""

from __future__ import annotations

import argparse
import copy
import json
import pickle
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Sequence, cast

from . import d011, d013, d014
from .d002 import D002ThermalStationEnv
from .d003 import HOT_DEPART_THRESHOLD
from .env import Action
from .exp003 import (
    EXP003_B50_ENTER_SEEK_THRESHOLD,
    BeaconObservation,
    EXP003StationConfig,
)
from .exp003_seed_policy import validate_exp003_development_seeds

D018_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = (18359, 18360, 18361)
D018_HORIZON: Final[int] = 1000
D018_AUTHORITATIVE_BASE_SHA: Final[str] = (
    "3ad3d93ad7764f938e16fefc8e1536a414b7d9bc"
)
D018_SUPPORT_CLASSES: Final[tuple[str, ...]] = ("zero", ">=1", ">=2")
D018_CONTACT_TARGETS: Final[tuple[str, ...]] = ("exit", "unchanged", "entry")

VisibleStateKey = tuple[float, float, float, float, bool, float]
StateActionKey = tuple[VisibleStateKey, Action]


def _validate_d018_development_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    """Apply the canonical reservation guard, then D-018's exact guard."""
    validated = validate_exp003_development_seeds(seeds)
    unexpected = tuple(
        seed for seed in validated if seed not in D018_DEFAULT_DEVELOPMENT_SEEDS
    )
    if unexpected:
        raise ValueError(
            "D-018 may execute only predeclared development seeds "
            f"{D018_DEFAULT_DEVELOPMENT_SEEDS}; got {unexpected}"
        )
    return validated


def _visible_state_key(observation: d011.D011Observation) -> VisibleStateKey:
    """Return the complete exact Python-value visible state key."""
    return (
        observation.energy,
        observation.beacon.left,
        observation.beacon.forward,
        observation.beacon.right,
        observation.charging_contact,
        observation.thermal,
    )


class ExactExecutedExperienceRegistry:
    """Evaluator registry containing only prior physically executed pairs."""

    __slots__ = ("_counts",)

    def __init__(self) -> None:
        self._counts: dict[StateActionKey, int] = {}

    def support_count(
        self, observation: d011.D011Observation, action: Action
    ) -> int:
        """Return exact same-visible-state/action prior real support."""
        return self._counts.get((_visible_state_key(observation), action), 0)

    def record(self, observation: d011.D011Observation, action: Action) -> None:
        """Add one physically executed state/action pair."""
        key = (_visible_state_key(observation), action)
        self._counts[key] = self._counts.get(key, 0) + 1

    @property
    def unique_pair_count(self) -> int:
        """Return the number of exact state/action pairs with real support."""
        return len(self._counts)


@dataclass(slots=True)
class _TargetMetricSums:
    count: int = 0
    learned_absolute_error_sum: float = 0.0
    zero_change_absolute_error_sum: float = 0.0

    def record(self, predicted: float, actual: float) -> None:
        self.count += 1
        self.learned_absolute_error_sum += abs(predicted - actual)
        self.zero_change_absolute_error_sum += abs(actual)

    def as_dict(self) -> dict[str, object]:
        if self.count == 0:
            return {
                "status": "untested",
                "raw_count": 0,
                "learned_mae": None,
                "zero_change_baseline_mae": None,
            }
        return {
            "status": "visited",
            "raw_count": self.count,
            "learned_mae": self.learned_absolute_error_sum / self.count,
            "zero_change_baseline_mae": (
                self.zero_change_absolute_error_sum / self.count
            ),
        }


@dataclass(slots=True)
class _MetricCell:
    targets: dict[str, _TargetMetricSums] = field(
        default_factory=lambda: {
            target: _TargetMetricSums() for target in d013.D013_OUTPUTS
        }
    )

    def record(
        self, prediction: d013.D013Prediction, actual: dict[str, float]
    ) -> None:
        predicted = prediction.as_dict()
        for target in d013.D013_OUTPUTS:
            self.targets[target].record(predicted[target], actual[target])

    def as_dict(self) -> dict[str, object]:
        count = max((cell.count for cell in self.targets.values()), default=0)
        return {
            "status": "untested" if count == 0 else "visited",
            "raw_count": count,
            "targets": {
                target: self.targets[target].as_dict() for target in d013.D013_OUTPUTS
            },
        }


class _AuditMetrics:
    """Raw-count-first evaluator metrics across declared one-dimensional splits."""

    __slots__ = ("groups", "support_count_distribution")

    def __init__(self) -> None:
        self.groups: dict[str, dict[str, _MetricCell]] = {
            "executed_vs_unexecuted": {
                "executed": _MetricCell(),
                "unexecuted": _MetricCell(),
            },
            "action": {action.name: _MetricCell() for action in Action},
            "current_contact": {"False": _MetricCell(), "True": _MetricCell()},
            "prior_exact_support": {
                category: _MetricCell() for category in D018_SUPPORT_CLASSES
            },
            "contact_target": {
                category: _MetricCell() for category in D018_CONTACT_TARGETS
            },
        }
        self.support_count_distribution: dict[str, int] = {}

    def record(
        self,
        *,
        action: Action,
        executed: bool,
        current: d011.D011Observation,
        support_count: int,
        contact_target: str,
        prediction: d013.D013Prediction,
        actual: dict[str, float],
    ) -> None:
        if contact_target not in D018_CONTACT_TARGETS:
            raise ValueError(f"unsupported contact target: {contact_target}")
        if support_count < 0:
            raise ValueError("support_count must be non-negative")
        support_class = (
            "zero" if support_count == 0 else ">=2" if support_count >= 2 else ">=1"
        )
        self.groups["executed_vs_unexecuted"][
            "executed" if executed else "unexecuted"
        ].record(prediction, actual)
        self.groups["action"][action.name].record(prediction, actual)
        self.groups["current_contact"][str(current.charging_contact)].record(
            prediction, actual
        )
        self.groups["prior_exact_support"][support_class].record(prediction, actual)
        self.groups["contact_target"][contact_target].record(prediction, actual)
        count_key = str(support_count)
        self.support_count_distribution[count_key] = (
            self.support_count_distribution.get(count_key, 0) + 1
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "metrics_by": {
                dimension: {
                    category: cell.as_dict() for category, cell in categories.items()
                }
                for dimension, categories in self.groups.items()
            },
            "prior_exact_support_count_distribution": dict(
                sorted(
                    self.support_count_distribution.items(),
                    key=lambda item: int(item[0]),
                )
            ),
        }


class _AuditCollector:
    __slots__ = ("metrics", "rows")

    def __init__(self) -> None:
        self.metrics = _AuditMetrics()
        self.rows: list[dict[str, object]] = []

    def record(
        self,
        *,
        seed: int,
        transition_index: int,
        current: d011.D011Observation,
        candidate: Action,
        executed_action: Action,
        support_count: int,
        prediction: d013.D013Prediction,
        next_observation: d011.D011Observation,
        branch_terminated: bool,
        branch_truncated: bool,
    ) -> None:
        actual = {
            "delta_energy": next_observation.energy - current.energy,
            "delta_thermal": next_observation.thermal - current.thermal,
            "delta_charging_contact": float(next_observation.charging_contact)
            - float(current.charging_contact),
        }
        predicted = prediction.as_dict()
        contact_target = _contact_target_class(actual["delta_charging_contact"])
        row: dict[str, object] = {
            "seed": seed,
            "transition_index": transition_index,
            "current_visible_state": _observation_as_dict(current),
            "candidate_action": candidate.name,
            "physically_executed_action": executed_action.name,
            "candidate_was_physically_executed": candidate is executed_action,
            "prior_exact_state_action_support_count": support_count,
            "prior_exact_support_is_zero": support_count == 0,
            "prior_exact_support_at_least_one": support_count >= 1,
            "prior_exact_support_at_least_two": support_count >= 2,
            "predicted_delta_energy": predicted["delta_energy"],
            "actual_delta_energy": actual["delta_energy"],
            "absolute_error_delta_energy": abs(
                predicted["delta_energy"] - actual["delta_energy"]
            ),
            "zero_change_error_delta_energy": abs(actual["delta_energy"]),
            "predicted_delta_thermal": predicted["delta_thermal"],
            "actual_delta_thermal": actual["delta_thermal"],
            "absolute_error_delta_thermal": abs(
                predicted["delta_thermal"] - actual["delta_thermal"]
            ),
            "zero_change_error_delta_thermal": abs(actual["delta_thermal"]),
            "predicted_delta_charging_contact": predicted[
                "delta_charging_contact"
            ],
            "actual_delta_charging_contact": actual["delta_charging_contact"],
            "absolute_error_delta_charging_contact": abs(
                predicted["delta_charging_contact"]
                - actual["delta_charging_contact"]
            ),
            "zero_change_error_delta_charging_contact": abs(
                actual["delta_charging_contact"]
            ),
            "current_charging_contact": current.charging_contact,
            "actual_contact_target_class": contact_target,
            "candidate_branch_terminated": branch_terminated,
            "candidate_branch_truncated": branch_truncated,
        }
        self.rows.append(row)
        self.metrics.record(
            action=candidate,
            executed=candidate is executed_action,
            current=current,
            support_count=support_count,
            contact_target=contact_target,
            prediction=prediction,
            actual=actual,
        )

    def as_dict(self, *, unique_real_pairs: int) -> dict[str, object]:
        return {
            "raw_prediction_count": len(self.rows),
            "metrics": self.metrics.as_dict(),
            "unique_prior_real_state_action_pairs": unique_real_pairs,
            "rows": self.rows,
        }


@dataclass(slots=True)
class _BranchOutcome:
    observation: d011.D011Observation
    terminated: bool
    truncated: bool


@dataclass(slots=True)
class _RunOutcome:
    summary: dict[str, object]
    trace: list[dict[str, object]]
    final_weights: dict[str, dict[str, list[float]]]
    rng_state: tuple[bytes, bytes, bytes]


def _observation_as_dict(observation: d011.D011Observation) -> dict[str, object]:
    return {
        "normalized_energy": observation.energy,
        "beacon_left": observation.beacon.left,
        "beacon_forward": observation.beacon.forward,
        "beacon_right": observation.beacon.right,
        "charging_contact": observation.charging_contact,
        "normalized_thermal": observation.thermal,
    }


def _contact_target_class(delta: float) -> str:
    classes = {-1.0: "exit", 0.0: "unchanged", 1.0: "entry"}
    try:
        return classes[delta]
    except KeyError as error:
        raise RuntimeError(
            f"contact delta is not exact binary change: {delta}"
        ) from error


def _termination_reason(
    *, terminated: bool, truncated: bool, energy: bool, thermal: bool
) -> str:
    if terminated and energy and thermal:
        return "energy_and_thermal_failure"
    if terminated and energy:
        return "energy_failure"
    if terminated and thermal:
        return "thermal_failure"
    if truncated:
        return "horizon_truncation"
    return "incomplete"


def _mode_counts() -> dict[str, int]:
    return {mode.name: 0 for mode in d011.D011Mode}


def _rng_state(environment: D002ThermalStationEnv) -> tuple[bytes, bytes, bytes]:
    streams = environment.base_env.random_streams
    if streams is None:
        raise RuntimeError("D-002 policy/environment RNGs are unavailable")
    return (
        pickle.dumps(streams.environment.bit_generator.state),
        pickle.dumps(streams.policy.bit_generator.state),
        pickle.dumps(environment.base_env.np_random.bit_generator.state),
    )


def _run_seed(
    seed: int, *, horizon: int, counterfactual_audit: bool
) -> _RunOutcome:
    config = EXP003StationConfig(episode_horizon=horizon)
    environment = D002ThermalStationEnv(config=config)
    observation, info = environment.reset(seed=seed)
    if info != {}:
        raise RuntimeError("D-002 reset crossed the information boundary")
    seeded_heading, observation = d011._prepare_post_contact_setup(environment)
    random_streams = environment.base_env.random_streams
    if random_streams is None:
        raise RuntimeError("D-002 policy RNG is unavailable after reset")

    controller = d014.D014Controller(random_streams.policy)
    controller.reset()
    predictor = d013.D013ActionConsequencePredictor()
    registry = ExactExecutedExperienceRegistry()
    collector = _AuditCollector() if counterfactual_audit else None
    action_counts = {action.name: 0 for action in Action}
    mode_occupancy = _mode_counts()
    mode_entry_counts = _mode_counts()
    mode_entry_counts[controller.mode.name] = 1

    transitions = 0
    minimum_energy = config.initial_energy
    maximum_energy = config.initial_energy
    minimum_normalized_energy = float(observation[0])
    maximum_normalized_energy = float(observation[0])
    minimum_thermal = float(observation[5])
    maximum_thermal = float(observation[5])
    charger_departures = 0
    departure_events: list[dict[str, object]] = []
    departure_trigger_counts = {"full_only": 0, "thermal_only": 0, "both": 0}
    charger_exits = 0
    away_entries = 0
    low_energy_seek_entries = 0
    successful_reacquisitions = 0
    completed_cycles = 0
    active_seek = False
    cycle_open = False
    cycle_has_exit = False
    cycle_waiting_for_reacquisition = False
    trace: list[dict[str, object]] = []
    branch_rng_states_unchanged = True
    selected_branch_matches = True

    terminated = False
    truncated = False
    while not (terminated or truncated):
        current = d011._controller_observation(observation)
        mode_before = controller.mode
        mode_occupancy[mode_before.name] += 1
        action = controller.act(current)
        mode_after = controller.mode
        action_counts[action.name] += 1
        if mode_after is not mode_before:
            mode_entry_counts[mode_after.name] += 1
        if mode_before is d011.D011Mode.CHARGE and mode_after is d011.D011Mode.DEPART:
            charger_departures += 1
            full_energy_condition = current.energy >= d014.D014_FULL_ENERGY_THRESHOLD
            hot_thermal_condition = current.thermal >= HOT_DEPART_THRESHOLD
            if full_energy_condition and hot_thermal_condition:
                trigger_category = "both"
            elif full_energy_condition:
                trigger_category = "full_only"
            elif hot_thermal_condition:
                trigger_category = "thermal_only"
            else:
                raise RuntimeError("D-018 departed without a valid trigger")
            departure_trigger_counts[trigger_category] += 1
            departure_events.append(
                {
                    "transition_index": transitions + 1,
                    "decision_index": transitions + 1,
                    "energy": current.energy,
                    "thermal": current.thermal,
                    "charging_contact": current.charging_contact,
                    "full_energy_condition": full_energy_condition,
                    "hot_thermal_condition": hot_thermal_condition,
                    "trigger_category": trigger_category,
                }
            )
            cycle_open = True
            cycle_has_exit = False
            cycle_waiting_for_reacquisition = False
        if mode_before is d011.D011Mode.DEPART and mode_after is d011.D011Mode.AWAY:
            away_entries += 1

        body = environment.body
        if body is None:
            raise RuntimeError("D-018 body is unavailable before transition")
        position_before = body.position
        heading_before = body.heading
        support_counts = {
            candidate: registry.support_count(current, candidate)
            for candidate in Action
        }

        predictions: dict[Action, d013.D013Prediction]
        branches: dict[Action, _BranchOutcome] = {}
        if counterfactual_audit:
            predictions = {
                candidate: predictor.predict(current, candidate) for candidate in Action
            }
            for candidate in Action:
                real_rng_before = _rng_state(environment)
                branch = copy.deepcopy(environment)
                (
                    branch_observation,
                    branch_reward,
                    branch_terminated,
                    branch_truncated,
                    branch_info,
                ) = (
                    branch.step(candidate)
                )
                real_rng_after = _rng_state(environment)
                if real_rng_before != real_rng_after:
                    branch_rng_states_unchanged = False
                if branch_reward != 0.0 or branch_info != {}:
                    raise RuntimeError(
                        "counterfactual branch crossed reward/info boundary"
                    )
                branches[candidate] = _BranchOutcome(
                    observation=d011._controller_observation(branch_observation),
                    terminated=branch_terminated,
                    truncated=branch_truncated,
                )
        else:
            predictions = {action: predictor.predict(current, action)}

        observation, reward, terminated, truncated, info = environment.step(action)
        if reward != 0.0 or info != {}:
            raise RuntimeError("D-002 reward or info crossed the boundary")
        next_observation = d011._controller_observation(observation)
        if counterfactual_audit:
            selected_branch = branches[action]
            selected_branch_matches = selected_branch_matches and (
                selected_branch.observation == next_observation
                and selected_branch.terminated == terminated
                and selected_branch.truncated == truncated
            )
            if not selected_branch_matches:
                raise RuntimeError(
                    "selected evaluator branch did not match the real transition"
                )
        predictor.observe_transition(current, action, next_observation)

        telemetry = environment.last_transition
        body_after = environment.body
        if telemetry is None or body_after is None:
            raise RuntimeError("D-018 transition telemetry is unavailable")
        transitions += 1

        if counterfactual_audit and collector is not None:
            for candidate in Action:
                branch_outcome = branches[candidate]
                collector.record(
                    seed=seed,
                    transition_index=transitions,
                    current=current,
                    candidate=candidate,
                    executed_action=action,
                    support_count=support_counts[candidate],
                    prediction=predictions[candidate],
                    next_observation=branch_outcome.observation,
                    branch_terminated=branch_outcome.terminated,
                    branch_truncated=branch_outcome.truncated,
                )
        registry.record(current, action)

        trace.append(
            {
                "transition_index": transitions,
                "current_visible_state": _observation_as_dict(current),
                "action": action.name,
                "mode_before": mode_before.name,
                "mode_after": mode_after.name,
                "position_before": [position_before[0], position_before[1]],
                "position_after": [body_after.x, body_after.y],
                "heading_before": heading_before,
                "heading_after": body_after.heading,
                "next_visible_state": _observation_as_dict(next_observation),
                "energy_before": telemetry.energy_before,
                "energy_after": telemetry.energy_after,
                "thermal_before": telemetry.thermal_before,
                "thermal_after": telemetry.thermal_after,
                "charging_contact_before": telemetry.charging_contact_before,
                "charging_contact_after": telemetry.charging_contact_after,
                "terminated": terminated,
                "truncated": truncated,
                "reward": reward,
                "info": info,
            }
        )

        minimum_energy = min(minimum_energy, telemetry.energy_after)
        maximum_energy = max(maximum_energy, telemetry.energy_after)
        minimum_normalized_energy = min(
            minimum_normalized_energy, float(observation[0])
        )
        maximum_normalized_energy = max(
            maximum_normalized_energy, float(observation[0])
        )
        minimum_thermal = min(minimum_thermal, float(observation[5]))
        maximum_thermal = max(maximum_thermal, float(observation[5]))

        if telemetry.charging_contact_before and not telemetry.charging_contact_after:
            charger_exits += 1
            cycle_has_exit = True

        entered_low_energy_seek = (
            mode_before is d011.D011Mode.AWAY
            and mode_after is d011.D011Mode.SEEK
            and current.energy < EXP003_B50_ENTER_SEEK_THRESHOLD
        )
        if entered_low_energy_seek:
            low_energy_seek_entries += 1
            active_seek = True
            cycle_waiting_for_reacquisition = (
                cycle_open and cycle_has_exit and not current.charging_contact
            )

        if (
            active_seek
            and not current.charging_contact
            and telemetry.charging_contact_after
        ):
            successful_reacquisitions += 1
            if cycle_waiting_for_reacquisition:
                completed_cycles += 1
                cycle_open = False
                cycle_has_exit = False
                cycle_waiting_for_reacquisition = False
            active_seek = False

    final = environment.last_transition
    if final is None or environment.body is None or environment.station_center is None:
        raise RuntimeError("D-018 run ended without final telemetry")
    if counterfactual_audit and not branch_rng_states_unchanged:
        raise RuntimeError("evaluator branch changed a real RNG state")
    summary: dict[str, object] = {
        "seed": seed,
        "transitions": transitions,
        "terminated": terminated,
        "truncated": truncated,
        "termination_reason": _termination_reason(
            terminated=terminated,
            truncated=truncated,
            energy=final.energy_termination,
            thermal=final.thermal_termination,
        ),
        "energy_termination": final.energy_termination,
        "thermal_termination": final.thermal_termination,
        "minimum_energy": minimum_energy,
        "maximum_energy": maximum_energy,
        "final_energy": environment.body.energy,
        "minimum_normalized_energy": minimum_normalized_energy,
        "maximum_normalized_energy": maximum_normalized_energy,
        "final_normalized_energy": float(observation[0]),
        "minimum_thermal_state": minimum_thermal,
        "maximum_thermal_state": maximum_thermal,
        "final_thermal_state": environment.thermal_state,
        "action_counts": action_counts,
        "mode_occupancy": mode_occupancy,
        "mode_entry_counts": mode_entry_counts,
        "charger_departures": charger_departures,
        "charger_departure_events": departure_events,
        "departure_trigger_counts": departure_trigger_counts,
        "successful_physical_charger_exits": charger_exits,
        "away_entries": away_entries,
        "low_energy_seek_entries": low_energy_seek_entries,
        "successful_charging_contact_reacquisitions": successful_reacquisitions,
        "completed_autonomous_regulation_cycles": completed_cycles,
        "demonstrated_failed_seek_episodes": int(
            active_seek and terminated and not truncated
        ),
        "horizon_censored_seek_episodes": int(active_seek and truncated),
        "evaluator_only": {
            "seeded_heading": seeded_heading,
            "station_position": [
                environment.station_center[0],
                environment.station_center[1],
            ],
            "counterfactual_branches_created": counterfactual_audit,
            "branch_rng_states_unchanged": branch_rng_states_unchanged,
            "selected_branch_matches_real_next_observation": selected_branch_matches,
            "real_action_only_learner_update": True,
            "counterfactual_outcomes_passed_to_controller": False,
            "counterfactual_outcomes_passed_to_learner": False,
            "counterfactual_outcomes_passed_to_policy_rng": False,
            "counterfactual_outcomes_passed_to_real_environment": False,
        },
    }
    if counterfactual_audit and collector is not None:
        summary["audit"] = collector.as_dict(
            unique_real_pairs=registry.unique_pair_count
        )
    return _RunOutcome(
        summary=summary,
        trace=trace,
        final_weights=predictor.weight_snapshot(),
        rng_state=_rng_state(environment),
    )


def _comparison_fields() -> tuple[str, ...]:
    return (
        "transitions",
        "terminated",
        "truncated",
        "termination_reason",
        "energy_termination",
        "thermal_termination",
        "action_counts",
        "mode_occupancy",
        "mode_entry_counts",
        "minimum_energy",
        "maximum_energy",
        "final_energy",
        "minimum_normalized_energy",
        "maximum_normalized_energy",
        "final_normalized_energy",
        "minimum_thermal_state",
        "maximum_thermal_state",
        "final_thermal_state",
        "charger_departures",
        "departure_trigger_counts",
        "successful_physical_charger_exits",
        "away_entries",
        "low_energy_seek_entries",
        "successful_charging_contact_reacquisitions",
        "completed_autonomous_regulation_cycles",
        "demonstrated_failed_seek_episodes",
        "horizon_censored_seek_episodes",
    )


def _validate_executed_commit_sha(value: str | None) -> str | None:
    if value is None:
        return None
    if re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise ValueError("executed_commit_sha must be a 40-character lowercase SHA")
    return value


def run_d018_probe(
    seeds: Sequence[int] = D018_DEFAULT_DEVELOPMENT_SEEDS,
    *,
    horizon: int = D018_HORIZON,
    executed_commit_sha: str | None = None,
) -> dict[str, object]:
    """Run the D-018 audit and its no-branch D-014+D-013 reference."""
    development_seeds = _validate_d018_development_seeds(seeds)
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon <= 0:
        raise ValueError("horizon must be a positive integer")
    executed_sha = _validate_executed_commit_sha(executed_commit_sha)
    outcomes: list[dict[str, object]] = []
    pooled_rows: list[dict[str, object]] = []
    equality_by_seed: dict[str, dict[str, object]] = {}
    all_trajectory_equal = True
    all_weight_equal = True
    all_rng_equal = True
    all_branch_rng_unchanged = True
    all_selected_branch_matches = True
    pooled_unique_real_pairs = 0

    for seed in development_seeds:
        reference = _run_seed(seed, horizon=horizon, counterfactual_audit=False)
        audit = _run_seed(seed, horizon=horizon, counterfactual_audit=True)
        summary = audit.summary
        trace_equal = audit.trace == reference.trace
        weight_equal = audit.final_weights == reference.final_weights
        rng_equal = audit.rng_state == reference.rng_state
        fields_equal = all(
            summary[field] == reference.summary[field] for field in _comparison_fields()
        )
        branch_rng_unchanged = bool(
            summary["evaluator_only"]["branch_rng_states_unchanged"]  # type: ignore[index]
        )
        selected_branch_matches = bool(
            summary["evaluator_only"][
                "selected_branch_matches_real_next_observation"
            ]  # type: ignore[index]
        )
        equality: dict[str, object] = {
            "trajectory_exact_equal": trace_equal,
            "relevant_summary_fields_exact_equal": fields_equal,
            "final_84_weights_exact_equal": weight_equal,
            "real_rng_state_exact_equal": rng_equal,
            "all_alternative_branch_rng_checks_unchanged": branch_rng_unchanged,
            "all_executed_action_clone_checks_match": selected_branch_matches,
            "reference_final_weight_count": (
                len(reference.final_weights)
                * len(d013.D013_OUTPUTS)
                * d013.D013_FEATURE_DIMENSION
            ),
            "audit_final_weight_count": (
                len(audit.final_weights)
                * len(d013.D013_OUTPUTS)
                * d013.D013_FEATURE_DIMENSION
            ),
        }
        equality_by_seed[str(seed)] = equality
        all_trajectory_equal = all_trajectory_equal and trace_equal and fields_equal
        all_weight_equal = all_weight_equal and weight_equal
        all_rng_equal = all_rng_equal and rng_equal
        all_branch_rng_unchanged = all_branch_rng_unchanged and branch_rng_unchanged
        all_selected_branch_matches = (
            all_selected_branch_matches and selected_branch_matches
        )
        audit_rows = summary["audit"]["rows"]  # type: ignore[index]
        if not isinstance(audit_rows, list):
            raise RuntimeError("D-018 audit rows are unavailable")
        pooled_rows.extend(audit_rows)
        audit_data = summary["audit"]
        if not isinstance(audit_data, dict):
            raise RuntimeError("D-018 audit summary is not an object")
        pooled_unique_real_pairs += int(
            cast(int, audit_data["unique_prior_real_state_action_pairs"])
        )
        summary["reference_comparison"] = equality
        summary["final_weights"] = audit.final_weights
        outcomes.append(summary)

    pooled_collector = _AuditCollector()
    for row in pooled_rows:
        if not isinstance(row, dict):
            raise RuntimeError("D-018 pooled row is not an object")
        current_values = cast(dict[str, object], row["current_visible_state"])
        if not isinstance(current_values, dict):
            raise RuntimeError("D-018 row current state is not an object")
        current = d011.D011Observation(
            energy=float(cast(float, current_values["normalized_energy"])),
            beacon=BeaconObservation(
                float(cast(float, current_values["beacon_left"])),
                float(cast(float, current_values["beacon_forward"])),
                float(cast(float, current_values["beacon_right"])),
                bool(current_values["charging_contact"]),
            ),
            thermal=float(cast(float, current_values["normalized_thermal"])),
        )
        action = Action[str(row["candidate_action"])]
        executed_action = Action[str(row["physically_executed_action"])]
        prediction = d013.D013Prediction(
            float(cast(float, row["predicted_delta_energy"])),
            float(cast(float, row["predicted_delta_thermal"])),
            float(cast(float, row["predicted_delta_charging_contact"])),
        )
        actual = {
            "delta_energy": float(cast(float, row["actual_delta_energy"])),
            "delta_thermal": float(cast(float, row["actual_delta_thermal"])),
            "delta_charging_contact": float(
                cast(float, row["actual_delta_charging_contact"])
            ),
        }
        pooled_collector.metrics.record(
            action=action,
            executed=action is executed_action,
            current=current,
            support_count=int(
                cast(int, row["prior_exact_state_action_support_count"])
            ),
            contact_target=str(row["actual_contact_target_class"]),
            prediction=prediction,
            actual=actual,
        )
        pooled_collector.rows.append(row)

    return {
        "schema_version": 1,
        "experiment": "D-018",
        "title": "Evaluator-only action-alternative consequence audit",
        "authoritative_base_sha": D018_AUTHORITATIVE_BASE_SHA,
        "executed_commit_sha": executed_sha,
        "development_seeds": list(development_seeds),
        "horizon": horizon,
        "lifetime": "one uninterrupted lifetime per seed",
        "seed_policy": {
            "canonical_validator": "validate_exp003_development_seeds",
            "exact_declared_seeds": list(D018_DEFAULT_DEVELOPMENT_SEEDS),
            "formal_reservation_guard_preserved": True,
        },
        "programmed": {
            "controller": "unchanged D014Controller",
            "learner": "unchanged d013.D013ActionConsequencePredictor",
            "environment": "unchanged D002ThermalStationEnv / EXP-003 ecology",
            "action_set": [action.name for action in Action],
            "policy_rng": "unchanged D-011 organism-owned policy stream",
            "real_action_selected_before_branch_scoring": True,
            "model_guided_action": False,
            "model_veto": False,
            "planning": False,
            "forced_actions": False,
            "reward_driven": False,
            "no_resets_within_lifetime": True,
        },
        "organism_visible": {
            "observation_type": "D011Observation",
            "fields": [
                "normalized energy",
                "beacon left",
                "beacon forward",
                "beacon right",
                "charging_contact",
                "normalized thermal",
            ],
            "own_physically_executed_action": True,
            "actual_next_observation_after_real_transition": True,
            "no_coordinates_heading_distance_or_extra_sensor": True,
        },
        "learned": {
            "implementation": "d013.D013ActionConsequencePredictor",
            "plastic_state_dimension": d013.D013_PLASTIC_STATE_DIMENSION,
            "weights": "4 actions × 3 outputs × 7 features = 84",
            "learning_rate": d013.D013_LEARNING_RATE,
            "initialization": "zeroed once per lifetime",
            "update": (
                "exactly once from current real observation, real action, "
                "real next observation"
            ),
            "counterfactual_outcomes_used": False,
            "alternative_prediction_calls_mutate_predictor": False,
        },
        "evaluator_only": {
            "counterfactual_isolation": (
                "each candidate action runs exactly once through canonical D002 step "
                "on an isolated deep copy of the current environment"
            ),
            "alternative_outcomes": [
                "delta_energy",
                "delta_thermal",
                "delta_charging_contact",
                "termination/truncation",
            ],
            "support_definition": (
                "exact complete current D011Observation values plus physically "
                "executed action; "
                "no rounding, epsilon, distance, or nearest-neighbour matching"
            ),
            "support_registry_counterfactual_branches_increment": False,
            "metrics": [
                "raw per-candidate rows",
                "executed versus unexecuted",
                "candidate action",
                "current contact",
                "prior exact support zero / >=1 / >=2",
                "contact target exit / unchanged / entry",
                "learned and zero-change comparator errors",
            ],
        },
        "organism_boundary": {"reward": 0.0, "info": {}},
        "real_vs_reference_equality": {
            "all_seeds_trajectory_exact_equal": all_trajectory_equal,
            "all_seeds_relevant_summary_fields_exact_equal": all_trajectory_equal,
            "all_seeds_final_84_weights_exact_equal": all_weight_equal,
            "all_seeds_real_rng_state_exact_equal": all_rng_equal,
            "all_alternative_branch_rng_checks_unchanged": all_branch_rng_unchanged,
            "all_executed_action_clone_checks_match": all_selected_branch_matches,
            "by_seed": equality_by_seed,
        },
        "final_weight_equality": {
            "all_seeds_exact_equal": all_weight_equal,
            "weight_count": d013.D013_PLASTIC_STATE_DIMENSION,
        },
        "aggregates": {
            "pooled": pooled_collector.as_dict(
                unique_real_pairs=pooled_unique_real_pairs
            ),
            "per_seed": {
                str(summary["seed"]): summary["audit"] for summary in outcomes
            },
        },
        "results": outcomes,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the D-018 evaluator-only action-alternative audit."
    )
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=list(D018_DEFAULT_DEVELOPMENT_SEEDS),
        help="Predeclared D-018 development seeds only.",
    )
    parser.add_argument("--horizon", type=int, default=D018_HORIZON)
    parser.add_argument("--executed-commit-sha")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    """Run D-018 and print or write its machine-readable result."""
    args = _parse_args()
    payload = json.dumps(
        run_d018_probe(
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
        print(f"D-018 result written to {args.output}")


if __name__ == "__main__":
    main()
