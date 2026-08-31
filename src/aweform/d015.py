"""D-015 D-014 shadow consequence-support diagnostic.

The corrected D-014 controller remains the sole source of physical actions.
The unchanged D-013 predictor observes only the executed action's one-step
visible consequence and has no causal influence on the trajectory.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Sequence

from . import d011, d013, d014
from .d002 import D002ThermalStationEnv
from .d003 import HOT_DEPART_THRESHOLD
from .env import Action
from .exp003 import (
    EXP003_B50_ENTER_SEEK_THRESHOLD,
    EXP003_CHARGING_RADIUS,
    EXP003StationConfig,
)
from .exp003_seed_policy import validate_exp003_development_seeds

D015_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = (18350, 18351, 18352)
D015_HORIZON: Final[int] = 1000
D015_AUTHORITATIVE_BASE_SHA: Final[str] = (
    "3208f9df1b3045db080913b6c06ea859f19c73ca"
)
D015_CONTACT_EVENT_CLASSES: Final[tuple[str, ...]] = (
    "contact_exit",
    "contact_unchanged",
    "contact_entry",
)


def _validate_d015_development_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    """Apply the canonical reservation guard, then D-015's exact guard."""
    validated = validate_exp003_development_seeds(seeds)
    unexpected = tuple(
        seed for seed in validated if seed not in D015_DEFAULT_DEVELOPMENT_SEEDS
    )
    if unexpected:
        raise ValueError(
            "D-015 may execute only predeclared development seeds "
            f"{D015_DEFAULT_DEVELOPMENT_SEEDS}; got {unexpected}"
        )
    return validated


def contact_event_class(observed_delta: float) -> str:
    """Classify the exact visible binary contact consequence."""
    classes = {-1.0: "contact_exit", 0.0: "contact_unchanged", 1.0: "contact_entry"}
    try:
        return classes[observed_delta]
    except KeyError as error:
        raise ValueError(
            "observed contact delta must be exactly -1.0, 0.0, or +1.0"
        ) from error


@dataclass(slots=True)
class _ContactEventMetrics:
    count: int = 0
    learned_absolute_error_sum: float = 0.0
    baseline_absolute_error_sum: float = 0.0
    predicted_delta_sum: float = 0.0

    def record(self, predicted_delta: float, observed_delta: float) -> None:
        self.count += 1
        self.learned_absolute_error_sum += abs(predicted_delta - observed_delta)
        self.baseline_absolute_error_sum += abs(observed_delta)
        self.predicted_delta_sum += predicted_delta

    def as_dict(self) -> dict[str, object]:
        if self.count == 0:
            return {
                "status": "untested",
                "transition_count": 0,
                "learned_mae": None,
                "zero_change_baseline_mae": None,
                "mean_predicted_delta_charging_contact": None,
            }
        return {
            "status": "visited",
            "transition_count": self.count,
            "learned_mae": self.learned_absolute_error_sum / self.count,
            "zero_change_baseline_mae": self.baseline_absolute_error_sum
            / self.count,
            "mean_predicted_delta_charging_contact": self.predicted_delta_sum
            / self.count,
        }


def _contact_event_table() -> dict[str, _ContactEventMetrics]:
    return {
        event_class: _ContactEventMetrics()
        for event_class in D015_CONTACT_EVENT_CLASSES
    }


def _record_contact_event(
    table: dict[str, _ContactEventMetrics],
    predicted_delta: float,
    observed_delta: float,
) -> None:
    table[contact_event_class(observed_delta)].record(predicted_delta, observed_delta)


@dataclass(slots=True)
class _ContactGroupingMetrics:
    count: int = 0
    learned_absolute_error_sum: float = 0.0
    baseline_absolute_error_sum: float = 0.0
    predicted_delta_sum: float = 0.0

    def record(self, predicted_delta: float, observed_delta: float) -> None:
        self.count += 1
        self.learned_absolute_error_sum += abs(predicted_delta - observed_delta)
        self.baseline_absolute_error_sum += abs(observed_delta)
        self.predicted_delta_sum += predicted_delta

    def as_dict(self) -> dict[str, object]:
        return {
            "status": "visited" if self.count else "untested",
            "transition_count": self.count,
            "learned_mae": (
                self.learned_absolute_error_sum / self.count if self.count else None
            ),
            "zero_change_baseline_mae": (
                self.baseline_absolute_error_sum / self.count if self.count else None
            ),
            "mean_predicted_delta_charging_contact": (
                self.predicted_delta_sum / self.count if self.count else None
            ),
        }


def _contact_grouping_table() -> dict[str, _ContactGroupingMetrics]:
    return {
        "contact_changed": _ContactGroupingMetrics(),
        "contact_unchanged": _ContactGroupingMetrics(),
    }


def _record_contact_grouping(
    table: dict[str, _ContactGroupingMetrics],
    predicted_delta: float,
    observed_delta: float,
) -> None:
    key = "contact_changed" if abs(observed_delta) == 1.0 else "contact_unchanged"
    if observed_delta not in (-1.0, 0.0, 1.0):
        raise ValueError("observed contact delta must be exact binary contact change")
    table[key].record(predicted_delta, observed_delta)


def _metric_summary(
    sums: dict[str, d013._TargetMetricSums], *, transition_count: int | None = None
) -> dict[str, object]:
    return d013._metric_summary(sums, transition_count=transition_count)


def _record_metrics(
    sums: dict[str, d013._TargetMetricSums],
    prediction: d013.D013Prediction,
    update: d013.D013LearningUpdate,
) -> None:
    d013._record_metrics(sums, prediction, update)


def _contact_metrics_summary(
    event_metrics: dict[str, _ContactEventMetrics],
    grouping_metrics: dict[str, _ContactGroupingMetrics],
) -> dict[str, object]:
    return {
        "exact_event_classes": {
            event_class: event_metrics[event_class].as_dict()
            for event_class in D015_CONTACT_EVENT_CLASSES
        },
        "changed_unchanged_groupings": {
            grouping: grouping_metrics[grouping].as_dict()
            for grouping in ("contact_changed", "contact_unchanged")
        },
    }


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


def _run_seed(seed: int, *, horizon: int) -> dict[str, object]:
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
    action_counts = {action.name: 0 for action in Action}
    mode_occupancy = _mode_counts()
    mode_entry_counts = _mode_counts()
    mode_entry_counts[controller.mode.name] = 1
    supports = d013._support_table()
    context_supports = {contact: d013._support_table() for contact in (False, True)}
    overall_sums = d013._empty_metric_sums()
    window_sums = {f"Q{index}": d013._empty_metric_sums() for index in range(1, 5)}
    overall_contact_events = _contact_event_table()
    q4_contact_events = _contact_event_table()
    overall_contact_groups = _contact_grouping_table()
    q4_contact_groups = _contact_grouping_table()
    checkpoints: dict[str, dict[str, dict[str, list[float]]]] = {}

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
                raise RuntimeError("D-015 departed without a valid trigger")
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

        # The prediction is formed before the physical transition and is never
        # passed to the controller or environment.
        prediction = predictor.predict(current, action)
        observation, reward, terminated, truncated, info = environment.step(action)
        if reward != 0.0 or info != {}:
            raise RuntimeError("D-002 reward or info crossed the boundary")
        next_observation = d011._controller_observation(observation)
        update = predictor.observe_transition(current, action, next_observation)

        # Event labels and all diagnostics are evaluator-side and deliberately
        # collected only after the ordinary D-013 learner update.
        telemetry = environment.last_transition
        body = environment.body
        if telemetry is None or body is None:
            raise RuntimeError("D-015 transition telemetry is unavailable")
        transitions += 1
        _record_metrics(overall_sums, prediction, update)
        window = window_sums.get(d013._window_name(transitions))
        if window is not None:
            _record_metrics(window, prediction, update)
        in_q4 = 751 <= transitions <= 1000
        supports[action].record(current, prediction, update, in_q4=in_q4)
        context_supports[current.charging_contact][action].record(
            current, prediction, update, in_q4=in_q4
        )
        observed_contact_delta = update.observed_delta_charging_contact
        _record_contact_event(
            overall_contact_events,
            prediction.predicted_delta_charging_contact,
            observed_contact_delta,
        )
        _record_contact_grouping(
            overall_contact_groups,
            prediction.predicted_delta_charging_contact,
            observed_contact_delta,
        )
        if in_q4:
            _record_contact_event(
                q4_contact_events,
                prediction.predicted_delta_charging_contact,
                observed_contact_delta,
            )
            _record_contact_grouping(
                q4_contact_groups,
                prediction.predicted_delta_charging_contact,
                observed_contact_delta,
            )
        if transitions in d013.D013_WINDOW_ENDS:
            checkpoints[str(transitions)] = predictor.weight_snapshot()

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
        raise RuntimeError("D-015 run ended without final telemetry")
    return {
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
        "prediction_metrics": {
            "windows": {
                name: _metric_summary(sums)
                for name, sums in window_sums.items()
                if sum(metric.count for metric in sums.values()) > 0
            },
            "overall": _metric_summary(overall_sums, transition_count=transitions),
        },
        "contact_event_metrics": {
            "overall": _contact_metrics_summary(
                overall_contact_events, overall_contact_groups
            ),
            "q4": _contact_metrics_summary(q4_contact_events, q4_contact_groups),
        },
        "action_support": {
            action.name: supports[action].as_dict() for action in Action
        },
        "action_context_support": {
            str(contact): {
                action.name: context_supports[contact][action].as_dict()
                for action in Action
            }
            for contact in (False, True)
        },
        "final_weights": predictor.weight_snapshot(),
        "checkpoints": checkpoints,
        "evaluator_only": {
            "trajectory_geometry_collected": False,
            "seeded_heading": seeded_heading,
            "station_position": [
                environment.station_center[0],
                environment.station_center[1],
            ],
            "contact_event_classification_after_learner_update": True,
            "event_class_passed_to_learner": False,
            "passed_to_controller": False,
        },
    }


def _validate_executed_commit_sha(value: str | None) -> str | None:
    if value is None:
        return None
    if re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise ValueError("executed_commit_sha must be a 40-character lowercase SHA")
    return value


def run_d015_probe(
    seeds: Sequence[int] = D015_DEFAULT_DEVELOPMENT_SEEDS,
    *,
    horizon: int = D015_HORIZON,
    executed_commit_sha: str | None = None,
) -> dict[str, object]:
    """Run one uninterrupted D-015 shadow-learning lifetime per seed."""
    development_seeds = _validate_d015_development_seeds(seeds)
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon <= 0:
        raise ValueError("horizon must be a positive integer")
    return {
        "schema_version": 1,
        "experiment": "D-015",
        "title": "D-014 shadow consequence support diagnostic",
        "authoritative_base_sha": D015_AUTHORITATIVE_BASE_SHA,
        "executed_commit_sha": _validate_executed_commit_sha(executed_commit_sha),
        "development_seeds": list(development_seeds),
        "horizon": horizon,
        "lifetime": "one uninterrupted lifetime per seed",
        "seed_policy": {
            "canonical_validator": "validate_exp003_development_seeds",
            "exact_declared_seeds": list(D015_DEFAULT_DEVELOPMENT_SEEDS),
            "formal_reservation_guard_preserved": True,
        },
        "programmed": {
            "controller": "D014Controller",
            "inherits": "D011Controller",
            "runner_reuses": [
                "d011._controller_observation",
                "d011._prepare_post_contact_setup",
                "D002ThermalStationEnv",
            ],
            "d014_action_logic_unchanged": True,
            "hot_depart_threshold": HOT_DEPART_THRESHOLD,
            "low_energy_seek_threshold": EXP003_B50_ENTER_SEEK_THRESHOLD,
            "charging_radius": EXP003_CHARGING_RADIUS,
            "policy_rng": "unchanged D-011 organism-owned policy stream",
            "model_guided_action": False,
            "counterfactual_action_selection": False,
            "forced_actions": False,
            "reward_driven": False,
            "no_resets_within_lifetime": True,
        },
        "organism_visible": {
            "observation_type": "D011Observation",
            "feature_vector": [
                "bias=1.0",
                "energy",
                "beacon.left",
                "beacon.forward",
                "beacon.right",
                "float(charging_contact)",
                "thermal",
            ],
            "executed_action": True,
            "actual_next_observation_after_transition": True,
            "controller_mode_is_learner_input": False,
            "event_class_is_learner_input": False,
            "policy_rng_is_learner_input": False,
            "evaluator_geometry_is_learner_input": False,
            "future_observation_is_learner_input": False,
        },
        "prediction_targets": [
            "next.energy - current.energy",
            "next.thermal - current.thermal",
            "float(next.charging_contact) - float(current.charging_contact)",
        ],
        "learner": {
            "implementation": "d013.D013ActionConsequencePredictor",
            "type": "action-conditioned linear one-step delta predictor",
            "actions": [action.name for action in Action],
            "outputs": list(d013.D013_OUTPUTS),
            "feature_dimension": d013.D013_FEATURE_DIMENSION,
            "learning_rate": d013.D013_LEARNING_RATE,
            "initial_weights": 0.0,
            "plastic_state_dimension": d013.D013_PLASTIC_STATE_DIMENSION,
            "plastic_state_order": "action, output, feature",
            "prediction_scored_before_update": True,
            "extra_plastic_state": False,
            "rng": False,
            "history": False,
            "optimizer_state": False,
            "buffer": False,
            "reset": "all 84 weights zero only at deliberate new-lifetime reset",
        },
        "evaluator_only": {
            "metrics": [
                "D-014 viability/behaviour/cycle summaries",
                "pre-update learned and zero-change MAE overall and Q1-Q4",
                "exact -1/0/+1 contact event class summaries overall and Q4",
                "contact changed/unchanged grouping summaries",
                "action/context support and contact target counts",
                "complete weight checkpoints and final state",
            ],
            "event_classification": (
                "exact observed one-step contact delta classified after the "
                "ordinary D-013 update; never passed to plasticity or action selection"
            ),
            "geometry_passed_to_learner": False,
            "mode_passed_to_learner": False,
            "prediction_causal_effect_on_behavior": False,
        },
        "ecology": {
            "environment": "D002ThermalStationEnv",
            "post_contact_setup": "unchanged D-011 setup",
        },
        "organism_boundary": {"reward": 0.0, "info": {}},
        "results": [_run_seed(seed, horizon=horizon) for seed in development_seeds],
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the D-015 D-014 shadow consequence-support diagnostic."
    )
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=list(D015_DEFAULT_DEVELOPMENT_SEEDS),
        help="Predeclared D-015 development seeds only.",
    )
    parser.add_argument("--horizon", type=int, default=D015_HORIZON)
    parser.add_argument("--executed-commit-sha")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    """Run D-015 and print or write its machine-readable result."""
    args = _parse_args()
    payload = json.dumps(
        run_d015_probe(
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
        print(f"D-015 result written to {args.output}")


if __name__ == "__main__":
    main()
