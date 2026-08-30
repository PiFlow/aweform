"""D-010 visited-support consequence-aliasing census.

This diagnostic runs only the unchanged D-009 overlap sampler around the
unchanged D-002 ecology and D-008 shadow learner.  The census is evaluator
state: its exact keys and outcome counts are never passed to either the
controller or the learner.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Sequence

from .d002 import (
    D002_UPPER_THERMAL_FAILURE_BOUNDARY,
    D002ThermalStationEnv,
)
from .d003 import (
    D003Mode,
    D003ThermostaticObservation,
    _controller_observation,
    _prepare_post_contact_setup,
)
from .d008 import D008ActionConsequencePredictor
from .d009 import D009SamplingController, D009SamplingPhase
from .env import Action
from .exp003 import EXP003_CHARGING_RADIUS, EXP003_HORIZON, EXP003StationConfig
from .exp003_seed_policy import validate_exp003_development_seeds

D010_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = (18141, 18142, 18143)
D010_AUTHORITATIVE_BASE_SHA: Final[str] = (
    "e7e3fc0d5245d08c1c297ce96cb3a6b501d42da4"
)

_ExactOutcome = tuple[float, bool]
_ExactKey = tuple[float, bool, Action]


@dataclass(slots=True)
class _ExactKeyRecord:
    """Evaluator counts for one exact current-visible state/action key."""

    current_thermal: float
    current_charging_contact: bool
    action: Action
    sample_count: int = 0
    outcomes: Counter[_ExactOutcome] = field(default_factory=Counter)

    def add(self, next_observation: D003ThermostaticObservation) -> None:
        self.sample_count += 1
        self.outcomes[
            (next_observation.thermal, next_observation.charging_contact)
        ] += 1

    def as_dict(self) -> dict[str, object]:
        outcomes = [
            {
                "next_thermal": next_thermal,
                "next_charging_contact": next_contact,
                "count": count,
            }
            for (next_thermal, next_contact), count in sorted(
                self.outcomes.items(), key=lambda item: (item[0][0], item[0][1])
            )
        ]
        distinct_next_thermal = {
            next_thermal for next_thermal, _ in self.outcomes
        }
        distinct_next_contact = {
            next_contact for _, next_contact in self.outcomes
        }
        distinct_outcomes = len(outcomes)
        return {
            "current_thermal": self.current_thermal,
            "current_charging_contact": self.current_charging_contact,
            "action": self.action.name,
            "sample_count": self.sample_count,
            "repeated": self.sample_count >= 2,
            "aliasing_tested": self.sample_count >= 2,
            "distinct_next_visible_outcome_count": distinct_outcomes,
            "next_visible_outcomes": outcomes,
            "distinct_next_thermal_count": len(distinct_next_thermal),
            "distinct_next_contact_count": len(distinct_next_contact),
            "aliased": distinct_outcomes > 1,
        }


class ExactConsequenceCensus:
    """Complete exact-key consequence census held only by the evaluator."""

    def __init__(self) -> None:
        self._records: dict[_ExactKey, _ExactKeyRecord] = {}

    def add(
        self,
        observation: D003ThermostaticObservation,
        action: Action,
        next_observation: D003ThermostaticObservation,
    ) -> None:
        key = (observation.thermal, observation.charging_contact, action)
        record = self._records.get(key)
        if record is None:
            record = _ExactKeyRecord(
                current_thermal=observation.thermal,
                current_charging_contact=observation.charging_contact,
                action=action,
            )
            self._records[key] = record
        record.add(next_observation)

    def records(self) -> list[dict[str, object]]:
        return [
            self._records[key].as_dict()
            for key in sorted(
                self._records,
                key=lambda item: (item[0], item[1], item[2].value),
            )
        ]

    def summary(self) -> dict[str, object]:
        return _census_summary(tuple(self._records.values()))

    def as_dict(self) -> dict[str, object]:
        return {
            "summary": _full_summary(self),
            "keys": self.records(),
            "classification_rule": {
                "exact_key_fields": [
                    "current_thermal",
                    "current_charging_contact",
                    "action",
                ],
                "exact_outcome_fields": [
                    "next_thermal",
                    "next_charging_contact",
                ],
                "repeated_requires_sample_count_at_least": 2,
                "aliased_requires_distinct_next_visible_outcome_count_greater_than": 1,
                "singleton_keys_are_not_stability_evidence": True,
            },
        }


def _census_summary(records: Sequence[_ExactKeyRecord]) -> dict[str, object]:
    transition_count = sum(record.sample_count for record in records)
    repeated_records = [record for record in records if record.sample_count >= 2]
    singleton_records = [record for record in records if record.sample_count == 1]
    transitions_in_repeated = sum(
        record.sample_count for record in repeated_records
    )
    return {
        "transition_count": transition_count,
        "total_unique_exact_keys": len(records),
        "repeated_exact_keys": len(repeated_records),
        "singleton_exact_keys": len(singleton_records),
        "transitions_belonging_to_repeated_keys": transitions_in_repeated,
        "fraction_of_transitions_belonging_to_repeated_keys": (
            transitions_in_repeated / transition_count if transition_count else 0.0
        ),
        "aliased_exact_keys": sum(len(record.outcomes) > 1 for record in records),
    }


def _grouped_summary(
    records: Sequence[_ExactKeyRecord],
    group: Action | bool,
) -> dict[str, object]:
    if isinstance(group, Action):
        selected = [record for record in records if record.action is group]
    else:
        selected = [
            record
            for record in records
            if record.current_charging_contact is group
        ]
    return _census_summary(selected)


def _full_summary(census: ExactConsequenceCensus) -> dict[str, object]:
    records = tuple(census._records.values())
    return {
        **_census_summary(records),
        "per_action": {
            action.name: _grouped_summary(records, action) for action in Action
        },
        "by_current_charging_contact": {
            str(contact): _grouped_summary(records, contact)
            for contact in (False, True)
        },
    }


def _census_as_dict(census: ExactConsequenceCensus) -> dict[str, object]:
    return census.as_dict()


def _run_sampler(
    seed: int,
    *,
    horizon: int,
    pooled_census: ExactConsequenceCensus | None = None,
) -> dict[str, object]:
    """Run one D-009 overlap-sampler lifetime with evaluator-only census."""
    config = EXP003StationConfig(episode_horizon=horizon)
    environment = D002ThermalStationEnv(config=config)
    observation, info = environment.reset(seed=seed)
    if info != {}:
        raise RuntimeError("D-002 reset crossed the information boundary")
    seeded_heading, observation = _prepare_post_contact_setup(environment)

    controller = D009SamplingController()
    controller.reset()
    predictor = D008ActionConsequencePredictor()
    census = ExactConsequenceCensus()
    action_counts = {action.name: 0 for action in Action}
    mode_occupancy = {mode.name: 0 for mode in D003Mode}
    mode_entry_counts = {mode.name: 0 for mode in D003Mode}
    mode_entry_counts[controller.mode.name] = 1
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
                completed_phase = (
                    D009SamplingPhase.LATE
                    if controller.sampling_phase is D009SamplingPhase.EARLY
                    else D009SamplingPhase.EARLY
                )
                if completed_phase is D009SamplingPhase.EARLY:
                    early_cycle_count += 1
                else:
                    late_cycle_count += 1

        # Keep the unchanged D-008 learner in the same shadow-only causal
        # order as D-009.  Its prediction cannot reach the controller.
        predictor.predict(current_observation, action)
        observation, reward, terminated, truncated, info = environment.step(action)
        if reward != 0.0 or info != {}:
            raise RuntimeError("D-002 reward or info crossed the boundary")
        next_observation = _controller_observation(observation)
        predictor.observe_transition(current_observation, action, next_observation)

        # Evaluator telemetry and census are read only after the plastic write.
        telemetry = environment.last_transition
        if telemetry is None or environment.body is None:
            raise RuntimeError("D-010 transition telemetry is unavailable")
        census.add(current_observation, action, next_observation)
        if pooled_census is not None:
            pooled_census.add(current_observation, action, next_observation)
        transitions += 1
        minimum_energy = min(minimum_energy, telemetry.energy_after)
        maximum_energy = max(maximum_energy, telemetry.energy_after)
        minimum_thermal = min(minimum_thermal, telemetry.thermal_after)
        maximum_thermal = max(maximum_thermal, telemetry.thermal_after)
        if telemetry.charging_contact_after:
            charging_contact_transitions += 1
        else:
            off_contact_transitions += 1

    if environment.last_transition is None or environment.body is None:
        raise RuntimeError("D-010 run ended without final telemetry")
    final = environment.last_transition
    return {
        "seed": seed,
        "condition": "overlap_sampler",
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
        "charging_contact_transitions": charging_contact_transitions,
        "off_contact_transitions": off_contact_transitions,
        "completed_shuttle_cycles": completed_shuttle_cycles,
        "early_cycle_count": early_cycle_count,
        "late_cycle_count": late_cycle_count,
        "mode_occupancy": mode_occupancy,
        "mode_entry_counts": mode_entry_counts,
        "sampling": {
            "starting_phase": D009SamplingPhase.EARLY.name,
            "final_phase": controller.sampling_phase.name,
        },
        "census": _census_as_dict(census),
        "shadow_predictor": {
            "type": "D008ActionConsequencePredictor",
            "causal_effect_on_action_choice": False,
            "causal_inputs": [
                "current thermal",
                "current charging_contact",
                "own action",
                "next thermal",
                "next charging_contact",
            ],
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


def _validate_d010_development_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    """Reject formal reservations and non-predeclared D-010 seeds."""
    validated = validate_exp003_development_seeds(seeds)
    unexpected = tuple(
        seed for seed in validated if seed not in D010_DEFAULT_DEVELOPMENT_SEEDS
    )
    if unexpected:
        raise ValueError(
            "D-010 may execute only predeclared development seeds "
            f"{D010_DEFAULT_DEVELOPMENT_SEEDS}; got {unexpected}"
        )
    return validated


def run_d010_probe(
    seeds: Sequence[int] = D010_DEFAULT_DEVELOPMENT_SEEDS,
    *,
    horizon: int = EXP003_HORIZON,
) -> dict[str, object]:
    """Run the D-009 overlap sampler and return per-seed plus pooled census."""
    development_seeds = _validate_d010_development_seeds(seeds)
    if horizon <= 0:
        raise ValueError("horizon must be positive")
    pooled_census = ExactConsequenceCensus()
    results = [
        _run_sampler(seed, horizon=horizon, pooled_census=pooled_census)
        for seed in development_seeds
    ]
    return {
        "schema_version": 1,
        "experiment": "D-010",
        "title": "Visited-support consequence-aliasing census",
        "authoritative_base_sha": D010_AUTHORITATIVE_BASE_SHA,
        "development_seeds": list(development_seeds),
        "horizon": horizon,
        "condition": "overlap_sampler",
        "ecology": {
            "environment": "D002ThermalStationEnv",
            "charging_radius": EXP003_CHARGING_RADIUS,
            "thermal_failure_boundary": D002_UPPER_THERMAL_FAILURE_BOUNDARY,
            "post_contact_setup": "D-003 evaluator-side setup",
        },
        "programmed": {
            "controller": "unchanged D009SamplingController",
            "sampling_phases": ["EARLY", "LATE"],
            "phase_start": "EARLY",
            "phase_toggle": "natural RETURN completion only",
            "forced_actions": False,
        },
        "learned": {
            "learner": "unchanged D008ActionConsequencePredictor",
            "shadow_only": True,
            "prediction_influences_action_choice": False,
            "plasticity_inputs": [
                "current thermal",
                "current charging_contact",
                "own action",
                "next thermal",
                "next charging_contact",
            ],
        },
        "evaluator_only": {
            "census": True,
            "exact_key_identity": True,
            "repeat_counts": True,
            "aliasing_classification": True,
            "pooled_across_seeds": True,
            "passed_to_controller_or_learner": False,
        },
        "organism_boundary": {"reward": 0.0, "info": {}},
        "results": results,
        "pooled_census": _census_as_dict(pooled_census),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the D-010 visited-support consequence-aliasing census."
    )
    parser.add_argument(
        "--seeds", type=int, nargs="+", default=list(D010_DEFAULT_DEVELOPMENT_SEEDS)
    )
    parser.add_argument("--horizon", type=int, default=EXP003_HORIZON)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    """Run D-010 and print or write its complete machine-readable result."""
    args = _parse_args()
    payload = json.dumps(
        run_d010_probe(tuple(args.seeds), horizon=args.horizon),
        indent=2,
        sort_keys=True,
    )
    if args.output is None:
        print(payload)
    else:
        args.output.write_text(payload + "\n", encoding="utf-8")
        print(f"D-010 result written to {args.output}")


if __name__ == "__main__":
    main()
