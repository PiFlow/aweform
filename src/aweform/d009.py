"""D-009 bounded overlapping action-experience acquisition.

This module changes only the data-acquisition controller around the unchanged
D-002 ecology and D-008 shadow learner.  The EARLY/LATE bit is programmed
controller state; it is never passed to the predictor and the predictor never
affects action selection.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Final, Sequence

import numpy as np

from .d002 import (
    D002_CHARGING_HEAT_PER_OFFERED_ENERGY,
    D002_PASSIVE_COOLING_PER_TRANSITION,
    D002_UPPER_THERMAL_FAILURE_BOUNDARY,
    D002ThermalStationEnv,
)
from .d003 import (
    COOL_RETURN_THRESHOLD,
    RETURN_HALF_TURN_STEPS,
    D003Mode,
    D003ThermostaticObservation,
    ThermostaticShuttleController,
    _controller_observation,
    _prepare_post_contact_setup,
)
from .d008 import (
    D008ActionConsequencePredictor,
    D008LearningUpdate,
    D008Prediction,
)
from .env import Action
from .exp003 import EXP003_CHARGING_RADIUS, EXP003_HORIZON, EXP003StationConfig
from .exp003_seed_policy import validate_exp003_development_seeds

D009_NOMINAL_OVERLAP_THERMAL: Final[float] = 0.59
D009_OVERLAP_THERMAL: Final[float] = float(np.float32(D009_NOMINAL_OVERLAP_THERMAL))
D009_NOMINAL_LATE_DEPART_THERMAL: Final[float] = 0.61
D009_LATE_DEPART_THRESHOLD: Final[float] = float(
    np.float32(D009_NOMINAL_LATE_DEPART_THERMAL)
)
D009_EARLY_DEPART_THRESHOLD: Final[float] = D009_OVERLAP_THERMAL
D009_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = (18141, 18142, 18143)
D009_WINDOW_SIZE: Final[int] = 250
D009_WINDOW_ENDS: Final[tuple[int, ...]] = (250, 500, 750, 1000)


class D009SamplingPhase(Enum):
    """Programmed phase used only to alternate charging departure timing."""

    EARLY = "EARLY"
    LATE = "LATE"


class D009SamplingController:
    """D-003 shuttle with a bounded alternating EARLY/LATE charge phase."""

    def __init__(self) -> None:
        self.mode = D003Mode.CHARGE
        self.turns_remaining = 0
        self.sampling_phase = D009SamplingPhase.EARLY

    def reset(self) -> None:
        """Start one lifetime in the declared EARLY phase."""
        self.mode = D003Mode.CHARGE
        self.turns_remaining = 0
        self.sampling_phase = D009SamplingPhase.EARLY

    def act(self, observation: D003ThermostaticObservation) -> Action:
        """Select an action using only the D-003 observation and own state."""
        if not isinstance(observation, D003ThermostaticObservation):
            raise ValueError("observation must be a D003ThermostaticObservation")

        if self.mode is D003Mode.CHARGE:
            threshold = (
                D009_EARLY_DEPART_THRESHOLD
                if self.sampling_phase is D009SamplingPhase.EARLY
                else D009_LATE_DEPART_THRESHOLD
            )
            if observation.thermal < threshold:
                return Action.WAIT
            self.mode = D003Mode.DEPART
            return Action.MOVE_FORWARD

        if self.mode is D003Mode.DEPART:
            if observation.charging_contact:
                return Action.MOVE_FORWARD
            self.mode = D003Mode.COOL
            return Action.WAIT

        if self.mode is D003Mode.COOL:
            if observation.thermal > COOL_RETURN_THRESHOLD:
                return Action.WAIT
            self.turns_remaining = RETURN_HALF_TURN_STEPS
            self.mode = D003Mode.TURN_RETURN
            self.turns_remaining -= 1
            return Action.TURN_LEFT

        if self.mode is D003Mode.TURN_RETURN:
            if self.turns_remaining <= 0:
                raise RuntimeError("return turn counter exhausted before RETURN")
            self.turns_remaining -= 1
            if self.turns_remaining == 0:
                self.mode = D003Mode.RETURN
            return Action.TURN_LEFT

        if self.mode is D003Mode.RETURN:
            if observation.charging_contact:
                self.mode = D003Mode.CHARGE
                self.sampling_phase = (
                    D009SamplingPhase.LATE
                    if self.sampling_phase is D009SamplingPhase.EARLY
                    else D009SamplingPhase.EARLY
                )
                return Action.WAIT
            return Action.MOVE_FORWARD

        raise RuntimeError(f"unsupported controller mode: {self.mode}")


@dataclass(slots=True)
class _OverlapStats:
    """Mutable evaluator accumulator for one exact-state action support set."""

    sample_count: int = 0
    next_thermal: list[float] | None = None
    next_contact: list[bool] | None = None
    delta_thermal: list[float] | None = None
    delta_contact: list[float] | None = None
    outcomes: Counter[tuple[float, bool]] | None = None

    def __post_init__(self) -> None:
        self.next_thermal = []
        self.next_contact = []
        self.delta_thermal = []
        self.delta_contact = []
        self.outcomes = Counter()

    def add(
        self,
        observation: D003ThermostaticObservation,
        next_observation: D003ThermostaticObservation,
    ) -> None:
        assert self.next_thermal is not None
        assert self.next_contact is not None
        assert self.delta_thermal is not None
        assert self.delta_contact is not None
        assert self.outcomes is not None
        delta_thermal = next_observation.thermal - observation.thermal
        delta_contact = float(next_observation.charging_contact) - float(
            observation.charging_contact
        )
        self.sample_count += 1
        self.next_thermal.append(next_observation.thermal)
        self.next_contact.append(next_observation.charging_contact)
        self.delta_thermal.append(delta_thermal)
        self.delta_contact.append(delta_contact)
        self.outcomes[
            (next_observation.thermal, next_observation.charging_contact)
        ] += 1

    def as_dict(self) -> dict[str, object]:
        assert self.next_thermal is not None
        assert self.next_contact is not None
        assert self.delta_thermal is not None
        assert self.delta_contact is not None
        assert self.outcomes is not None
        distinct_thermal = sorted(set(self.next_thermal))
        distinct_contact = sorted(set(self.next_contact))
        distinct_delta_thermal = sorted(set(self.delta_thermal))
        distinct_delta_contact = sorted(set(self.delta_contact))
        counts = {
            "-1": sum(value == -1.0 for value in self.delta_contact),
            "0": sum(value == 0.0 for value in self.delta_contact),
            "+1": sum(value == 1.0 for value in self.delta_contact),
        }
        outcome_records = [
            {
                "next_thermal": thermal,
                "next_charging_contact": contact,
                "count": count,
            }
            for (thermal, contact), count in sorted(
                self.outcomes.items(), key=lambda item: (item[0][0], item[0][1])
            )
        ]
        return {
            "sample_count": self.sample_count,
            "current_thermal": D009_OVERLAP_THERMAL,
            "next_thermal_values": distinct_thermal,
            "next_charging_contact_values": distinct_contact,
            "delta_thermal_values": distinct_delta_thermal,
            "delta_contact_values": distinct_delta_contact,
            "thermal_delta_min": min(self.delta_thermal, default=None),
            "thermal_delta_max": max(self.delta_thermal, default=None),
            "mean_delta_thermal": (
                sum(self.delta_thermal) / self.sample_count
                if self.sample_count
                else None
            ),
            "contact_delta_counts": counts,
            "mean_delta_contact": (
                sum(self.delta_contact) / self.sample_count
                if self.sample_count
                else None
            ),
            "distinct_next_visible_outcomes": outcome_records,
            "same_visible_state_action_outcome_variability": len(outcome_records) > 1,
        }


def _new_overlap_stats() -> dict[str, _OverlapStats]:
    return {action.name: _OverlapStats() for action in Action}


def _empty_context() -> dict[str, object]:
    return {
        "count": 0,
        "current_thermal_min": None,
        "current_thermal_max": None,
        "contact_delta_target_counts": {"-1": 0, "0": 0, "+1": 0},
        "thermal_delta_min": None,
        "thermal_delta_max": None,
    }


def _new_contexts() -> dict[str, dict[str, dict[str, object]]]:
    return {
        str(contact): {action.name: _empty_context() for action in Action}
        for contact in (False, True)
    }


def _record_context(
    contexts: dict[str, dict[str, dict[str, object]]],
    observation: D003ThermostaticObservation,
    update: D008LearningUpdate,
) -> None:
    context = contexts[str(observation.charging_contact)][update.action.name]
    count = context["count"]
    if not isinstance(count, int):
        raise RuntimeError("context count is not an integer")
    context["count"] = count + 1
    current_min = context["current_thermal_min"]
    current_max = context["current_thermal_max"]
    if current_min is not None and not isinstance(current_min, (int, float)):
        raise RuntimeError("context thermal minimum is not numeric")
    if current_max is not None and not isinstance(current_max, (int, float)):
        raise RuntimeError("context thermal maximum is not numeric")
    context["current_thermal_min"] = (
        observation.thermal
        if current_min is None
        else min(float(current_min), observation.thermal)
    )
    context["current_thermal_max"] = (
        observation.thermal
        if current_max is None
        else max(float(current_max), observation.thermal)
    )
    contact_key = {"-1.0": "-1", "0.0": "0", "1.0": "+1"}[
        str(update.observed_delta_contact)
    ]
    target_counts = context["contact_delta_target_counts"]
    if not isinstance(target_counts, dict):
        raise RuntimeError("context contact counts are not a dictionary")
    target_count = target_counts[contact_key]
    if not isinstance(target_count, int):
        raise RuntimeError("context contact count is not an integer")
    target_counts[contact_key] = target_count + 1
    delta_min = context["thermal_delta_min"]
    delta_max = context["thermal_delta_max"]
    if delta_min is not None and not isinstance(delta_min, (int, float)):
        raise RuntimeError("context thermal delta minimum is not numeric")
    if delta_max is not None and not isinstance(delta_max, (int, float)):
        raise RuntimeError("context thermal delta maximum is not numeric")
    context["thermal_delta_min"] = (
        update.observed_delta_thermal
        if delta_min is None
        else min(float(delta_min), update.observed_delta_thermal)
    )
    context["thermal_delta_max"] = (
        update.observed_delta_thermal
        if delta_max is None
        else max(float(delta_max), update.observed_delta_thermal)
    )


def _empty_metric_sums() -> dict[str, float | int]:
    return {
        "transition_count": 0,
        "thermal_absolute_error_sum": 0.0,
        "thermal_baseline_absolute_error_sum": 0.0,
        "contact_absolute_error_sum": 0.0,
        "contact_baseline_absolute_error_sum": 0.0,
    }


def _record_metrics(
    sums: dict[str, float | int],
    prediction: D008Prediction,
    update: D008LearningUpdate,
) -> None:
    sums["transition_count"] += 1
    sums["thermal_absolute_error_sum"] += abs(
        prediction.predicted_delta_thermal - update.observed_delta_thermal
    )
    sums["thermal_baseline_absolute_error_sum"] += abs(update.observed_delta_thermal)
    sums["contact_absolute_error_sum"] += abs(
        prediction.predicted_delta_contact - update.observed_delta_contact
    )
    sums["contact_baseline_absolute_error_sum"] += abs(update.observed_delta_contact)


def _metric_summary(sums: dict[str, float | int]) -> dict[str, object]:
    count = int(sums["transition_count"])
    if count == 0:
        return {"transition_count": 0}
    return {
        "transition_count": count,
        "learned_model_thermal_mae": float(sums["thermal_absolute_error_sum"]) / count,
        "zero_change_baseline_thermal_mae": float(
            sums["thermal_baseline_absolute_error_sum"]
        )
        / count,
        "learned_model_contact_delta_mae": float(sums["contact_absolute_error_sum"])
        / count,
        "zero_change_baseline_contact_delta_mae": float(
            sums["contact_baseline_absolute_error_sum"]
        )
        / count,
    }


def _window_name(transition_number: int) -> str:
    return f"Q{((transition_number - 1) // D009_WINDOW_SIZE) + 1}"


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


def _finalize_support(stats: dict[str, _OverlapStats]) -> dict[str, object]:
    return {
        "target_observation": {
            "thermal_nominal_decimal": D009_NOMINAL_OVERLAP_THERMAL,
            "thermal_organism_visible": D009_OVERLAP_THERMAL,
            "charging_contact": True,
        },
        "actions": {
            Action.WAIT.name: stats[Action.WAIT.name].as_dict(),
            Action.MOVE_FORWARD.name: stats[Action.MOVE_FORWARD.name].as_dict(),
        },
    }


def _run_condition(
    seed: int, *, horizon: int, sampler: bool
) -> dict[str, object]:
    config = EXP003StationConfig(episode_horizon=horizon)
    environment = D002ThermalStationEnv(config=config)
    observation, info = environment.reset(seed=seed)
    if info != {}:
        raise RuntimeError("D-002 reset crossed the information boundary")
    seeded_heading, observation = _prepare_post_contact_setup(environment)

    controller: ThermostaticShuttleController | D009SamplingController
    if sampler:
        controller = D009SamplingController()
    else:
        controller = ThermostaticShuttleController()
    controller.reset()
    predictor = D008ActionConsequencePredictor()
    action_counts = {action.name: 0 for action in Action}
    contexts = _new_contexts()
    overlap_stats = _new_overlap_stats()
    window_sums = {f"Q{index}": _empty_metric_sums() for index in range(1, 5)}
    overall_sums = _empty_metric_sums()
    checkpoints: dict[str, dict[str, dict[str, list[float]]]] = {}
    mode_entry_counts = {mode.name: 0 for mode in D003Mode}
    mode_entry_counts[controller.mode.name] = 1
    mode_occupancy = {mode.name: 0 for mode in D003Mode}
    transitions = 0
    minimum_energy = config.initial_energy
    maximum_energy = config.initial_energy
    minimum_thermal = float(observation[5])
    maximum_thermal = float(observation[5])
    charging_contact_transitions = 0
    off_contact_transitions = 0
    completed_shuttle_cycles = 0
    early_cycle_count = 0
    late_cycle_count = 0
    terminated = False
    truncated = False

    while not (terminated or truncated):
        mode_before = controller.mode
        mode_occupancy[mode_before.name] += 1
        current_observation = _controller_observation(observation)
        action = controller.act(current_observation)
        action_counts[action.name] += 1
        if controller.mode is not mode_before:
            mode_entry_counts[controller.mode.name] += 1
            if mode_before is D003Mode.RETURN and controller.mode is D003Mode.CHARGE:
                completed_shuttle_cycles += 1
                if sampler:
                    assert isinstance(controller, D009SamplingController)
                    completed_phase = (
                        D009SamplingPhase.LATE
                        if controller.sampling_phase is D009SamplingPhase.EARLY
                        else D009SamplingPhase.EARLY
                    )
                    if completed_phase is D009SamplingPhase.EARLY:
                        early_cycle_count += 1
                    else:
                        late_cycle_count += 1

        # This is intentionally before the physical transition and before any
        # evaluator telemetry can be read.
        prediction = predictor.predict(current_observation, action)
        observation, reward, terminated, truncated, info = environment.step(action)
        if reward != 0.0 or info != {}:
            raise RuntimeError("D-002 reward or info crossed the boundary")
        next_observation = _controller_observation(observation)
        update = predictor.observe_transition(
            current_observation, action, next_observation
        )

        # Evaluator telemetry is intentionally read only after the plastic write.
        telemetry = environment.last_transition
        if telemetry is None or environment.body is None:
            raise RuntimeError("D-009 transition telemetry is unavailable")
        transitions += 1
        _record_context(contexts, current_observation, update)
        _record_metrics(overall_sums, prediction, update)
        window = window_sums.get(_window_name(transitions))
        if window is not None:
            _record_metrics(window, prediction, update)
        if (
            current_observation.thermal == D009_OVERLAP_THERMAL
            and current_observation.charging_contact
        ):
            overlap_stats[action.name].add(current_observation, next_observation)
        if transitions in D009_WINDOW_ENDS:
            checkpoints[str(transitions)] = predictor.weight_snapshot()

        minimum_energy = min(minimum_energy, telemetry.energy_after)
        maximum_energy = max(maximum_energy, telemetry.energy_after)
        minimum_thermal = min(minimum_thermal, telemetry.thermal_after)
        maximum_thermal = max(maximum_thermal, telemetry.thermal_after)
        if telemetry.charging_contact_after:
            charging_contact_transitions += 1
        else:
            off_contact_transitions += 1

    if environment.last_transition is None or environment.body is None:
        raise RuntimeError("D-009 run ended without final telemetry")
    final = environment.last_transition
    common_observation = D003ThermostaticObservation(
        thermal=D009_OVERLAP_THERMAL,
        charging_contact=True,
    )
    weights_before_query = predictor.weights
    wait_prediction = predictor.predict(common_observation, Action.WAIT)
    move_prediction = predictor.predict(common_observation, Action.MOVE_FORWARD)
    if predictor.weights != weights_before_query:
        raise RuntimeError("final query changed learned weights")
    support = _finalize_support(overlap_stats)
    action_support = support["actions"]
    if not isinstance(action_support, dict):
        raise RuntimeError("support actions are not a dictionary")
    final_query: dict[str, object] = {
        "observation": {
            "thermal_nominal_decimal": D009_NOMINAL_OVERLAP_THERMAL,
            "thermal_organism_visible": D009_OVERLAP_THERMAL,
            "charging_contact": True,
        },
        "actions": {},
    }
    query_actions = final_query["actions"]
    if not isinstance(query_actions, dict):
        raise RuntimeError("query actions are not a dictionary")
    for action, prediction_value in (
        (Action.WAIT, wait_prediction),
        (Action.MOVE_FORWARD, move_prediction),
    ):
        action_result = action_support[action.name]
        if not isinstance(action_result, dict):
            raise RuntimeError("action support result is not a dictionary")
        count = int(action_result["sample_count"])
        query_actions[action.name] = {
            **prediction_value.as_dict(),
            "direct_support_at_query_state": count > 0,
            "exact_state_support_count": count,
            "support_label": None if count > 0 else "UNSUPPORTED AT QUERY STATE",
        }

    result: dict[str, object] = {
        "seed": seed,
        "condition": "overlap_sampler" if sampler else "baseline",
        "seeded_heading": seeded_heading,
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
        "minimum_thermal_state": minimum_thermal,
        "maximum_thermal_state": maximum_thermal,
        "final_thermal_state": environment.thermal_state,
        "viability": {
            "energy_failure": final.energy_termination,
            "thermal_failure": final.thermal_termination,
            "survived_horizon": truncated and not terminated,
        },
        "initial_position": [0.5, 0.5],
        "station_center": [0.5, 0.5],
        "action_counts": action_counts,
        "contact_action_counts": contexts,
        "charging_contact_transitions": charging_contact_transitions,
        "off_contact_transitions": off_contact_transitions,
        "completed_shuttle_cycles": completed_shuttle_cycles,
        "mode_occupancy": mode_occupancy,
        "mode_entry_counts": mode_entry_counts,
        "exact_overlap_support": support,
        "same_visible_state_action_variability": {
            action: bool(
                action_support[action][
                    "same_visible_state_action_outcome_variability"
                ]
            )
            for action in (Action.WAIT.name, Action.MOVE_FORWARD.name)
        },
        "prediction_metrics": {
            "windows": {
                name: _metric_summary(sums)
                for name, sums in window_sums.items()
                if int(sums["transition_count"]) > 0
            },
            "overall": _metric_summary(overall_sums),
        },
        "final_weights": predictor.weight_snapshot(),
        "checkpoints": checkpoints,
        "final_common_model_query": final_query,
        "controller_input_fields": ["thermal_interoception", "charging_contact"],
        "predictor_causal_inputs": [
            "current thermal",
            "current charging_contact",
            "own action",
            "next thermal",
            "next charging_contact",
        ],
    }
    if sampler:
        assert isinstance(controller, D009SamplingController)
        result["sampling"] = {
            "starting_phase": D009SamplingPhase.EARLY.name,
            "final_phase": controller.sampling_phase.name,
            "early_cycle_count": early_cycle_count,
            "late_cycle_count": late_cycle_count,
        }
    return result


def _validate_d009_development_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    """Reject formal reservations and non-predeclared D-009 seeds."""
    validated = validate_exp003_development_seeds(seeds)
    unexpected = tuple(
        seed for seed in validated if seed not in D009_DEFAULT_DEVELOPMENT_SEEDS
    )
    if unexpected:
        raise ValueError(
            "D-009 may execute only predeclared development seeds "
            f"{D009_DEFAULT_DEVELOPMENT_SEEDS}; got {unexpected}"
        )
    return validated


def run_d009_probe(
    seeds: Sequence[int] = D009_DEFAULT_DEVELOPMENT_SEEDS,
    *,
    horizon: int = EXP003_HORIZON,
) -> dict[str, object]:
    """Run matched baseline and sampler lifetimes for each legal seed."""
    development_seeds = _validate_d009_development_seeds(seeds)
    if horizon <= 0:
        raise ValueError("horizon must be positive")
    results = [
        {
            "seed": seed,
            "baseline": _run_condition(seed, horizon=horizon, sampler=False),
            "overlap_sampler": _run_condition(seed, horizon=horizon, sampler=True),
        }
        for seed in development_seeds
    ]
    return {
        "schema_version": 1,
        "experiment": "D-009",
        "title": "Bounded overlapping action-experience acquisition",
        "authoritative_base_sha": "dd37b551fc6310b189193d34340719ef98776f06",
        "thermal_constants": {
            "nominal_overlap_thermal": D009_NOMINAL_OVERLAP_THERMAL,
            "organism_visible_overlap_thermal": D009_OVERLAP_THERMAL,
            "early_depart_threshold": D009_EARLY_DEPART_THRESHOLD,
            "nominal_late_depart_thermal": D009_NOMINAL_LATE_DEPART_THERMAL,
            "late_depart_threshold": D009_LATE_DEPART_THRESHOLD,
        },
        "development_seeds": list(development_seeds),
        "horizon": horizon,
        "ecology": {
            "environment": "D002ThermalStationEnv",
            "charging_heat_per_offered_energy": D002_CHARGING_HEAT_PER_OFFERED_ENERGY,
            "passive_cooling_per_transition": D002_PASSIVE_COOLING_PER_TRANSITION,
            "thermal_failure_boundary": D002_UPPER_THERMAL_FAILURE_BOUNDARY,
            "charging_radius": EXP003_CHARGING_RADIUS,
            "post_contact_setup": "D-003 evaluator-side setup",
        },
        "behaviour_conditions": {
            "baseline": {
                "controller": "ThermostaticShuttleController",
                "predictor": "D008ActionConsequencePredictor",
                "shadow_predictor_causal_effect": False,
                "forced_actions": False,
            },
            "overlap_sampler": {
                "controller": "D009SamplingController",
                "predictor": "D008ActionConsequencePredictor",
                "sampling_phases": ["EARLY", "LATE"],
                "shadow_predictor_causal_effect": False,
                "forced_actions": False,
            },
        },
        "model": {
            "type": "unchanged D-008 action-conditioned linear delta predictor",
            "actions": [action.name for action in Action],
            "features": ["bias=1.0", "thermal", "charging_contact"],
            "predicted_consequences": ["delta_thermal", "delta_charging_contact"],
            "learning_rate": 0.5,
            "plastic_state_dimension": 24,
            "initial_weights": 0.0,
            "optimizer_buffer_recurrent_state": False,
            "rng": False,
            "prediction_scored_before_update": True,
        },
        "organism_visible_plasticity_boundary": {
            "predict_inputs": [
                "current thermal",
                "current charging_contact",
                "own action",
            ],
            "update_inputs": [
                "current thermal",
                "current charging_contact",
                "own action",
                "next thermal",
                "next charging_contact",
            ],
            "excluded": [
                "EARLY/LATE sampling phase",
                "controller mode",
                "energy",
                "coordinates",
                "station_center",
                "distance",
                "heading",
                "charging-zone-edge distance",
                "transition number",
                "clock",
                "horizon",
                "seed",
                "condition identity",
                "reward",
                "info",
                "evaluator telemetry",
                "offered charger energy",
                "stored energy delta",
                "thermal-input truth",
                "success/failure label",
                "future observations",
            ],
            "phase_is_programmed_not_learned": True,
        },
        "organism_boundary": {"reward": 0.0, "info": {}},
        "cycle_definition": (
            "return to CHARGE after completing DEPART -> COOL -> TURN_RETURN -> RETURN"
        ),
        "mae_interpretation": (
            "Overall and quarter MAE values across baseline and sampler conditions "
            "are descriptive only and must not be interpreted as a matched "
            "model-performance comparison because action/state visitation differs "
            "between conditions by design."
        ),
        "results": results,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the D-009 bounded overlapping action-experience probe."
    )
    parser.add_argument(
        "--seeds", type=int, nargs="+", default=list(D009_DEFAULT_DEVELOPMENT_SEEDS)
    )
    parser.add_argument("--horizon", type=int, default=EXP003_HORIZON)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    """Run D-009 and print or write its compact machine-readable result."""
    args = _parse_args()
    payload = json.dumps(
        run_d009_probe(tuple(args.seeds), horizon=args.horizon),
        indent=2,
        sort_keys=True,
    )
    if args.output is None:
        print(payload)
    else:
        args.output.write_text(payload + "\n", encoding="utf-8")
        print(f"D-009 result written to {args.output}")


if __name__ == "__main__":
    main()
