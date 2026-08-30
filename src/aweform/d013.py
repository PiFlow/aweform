"""D-013 full-observation shadow viability consequence learner.

This module attaches a deliberately small shadow learner to the unchanged
D-011 controller.  The controller remains the sole source of physical action
selection.  The learner receives only typed current/next D-011 observations,
the organism's executed action, and its own declared 84 scalar weights.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Sequence

from . import d011
from .d002 import (
    D002_CHARGING_HEAT_PER_OFFERED_ENERGY,
    D002_PASSIVE_COOLING_PER_TRANSITION,
    D002_UPPER_THERMAL_FAILURE_BOUNDARY,
    D002ThermalStationEnv,
)
from .d003 import HOT_DEPART_THRESHOLD
from .env import Action
from .exp003 import (
    EXP003_B50_ENTER_SEEK_THRESHOLD,
    EXP003_CHARGING_RADIUS,
    EXP003StationConfig,
)
from .exp003_seed_policy import validate_exp003_development_seeds

D013_LEARNING_RATE: Final[float] = 0.5
D013_FEATURE_DIMENSION: Final[int] = 7
D013_OUTPUTS: Final[tuple[str, ...]] = (
    "delta_energy",
    "delta_thermal",
    "delta_charging_contact",
)
D013_CHANNELS: Final[tuple[str, ...]] = (
    "energy",
    "beacon.left",
    "beacon.forward",
    "beacon.right",
    "charging_contact",
    "thermal",
)
D013_PLASTIC_STATE_DIMENSION: Final[int] = 84
D013_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = (18344, 18345, 18346)
D013_HORIZON: Final[int] = 1000
D013_WINDOW_SIZE: Final[int] = 250
D013_WINDOW_ENDS: Final[tuple[int, ...]] = (250, 500, 750, 1000)
D013_AUTHORITATIVE_BASE_SHA: Final[str] = (
    "539d91dfaf6b881b398d06c4637eb1c91f7a2174"
)

if len(Action) * len(D013_OUTPUTS) * D013_FEATURE_DIMENSION != (
    D013_PLASTIC_STATE_DIMENSION
):
    raise RuntimeError("D-013 plastic dimension no longer matches its declaration")


@dataclass(frozen=True, slots=True)
class D013Prediction:
    """Pre-update prediction for the physically selected action."""

    predicted_delta_energy: float
    predicted_delta_thermal: float
    predicted_delta_charging_contact: float

    def as_dict(self) -> dict[str, float]:
        """Return a JSON-compatible evaluator copy."""
        return {
            "delta_energy": self.predicted_delta_energy,
            "delta_thermal": self.predicted_delta_thermal,
            "delta_charging_contact": self.predicted_delta_charging_contact,
        }


@dataclass(frozen=True, slots=True)
class D013LearningUpdate:
    """Visible consequence targets and one normalized-LMS update."""

    action: Action
    predicted_delta_energy: float
    predicted_delta_thermal: float
    predicted_delta_charging_contact: float
    observed_delta_energy: float
    observed_delta_thermal: float
    observed_delta_charging_contact: float
    energy_error: float
    thermal_error: float
    charging_contact_error: float
    normalizer: float

    def as_dict(self) -> dict[str, object]:
        """Return a compact JSON-compatible evaluator copy."""
        return {
            "action": self.action.name,
            "predicted_delta_energy": self.predicted_delta_energy,
            "predicted_delta_thermal": self.predicted_delta_thermal,
            "predicted_delta_charging_contact": self.predicted_delta_charging_contact,
            "observed_delta_energy": self.observed_delta_energy,
            "observed_delta_thermal": self.observed_delta_thermal,
            "observed_delta_charging_contact": self.observed_delta_charging_contact,
            "energy_error": self.energy_error,
            "thermal_error": self.thermal_error,
            "charging_contact_error": self.charging_contact_error,
            "normalizer": self.normalizer,
        }


class D013ActionConsequencePredictor:
    """84-scalar full-observation action-conditioned linear predictor.

    The sole retained field is the action/output/feature weight mapping.  It
    has no optimizer state, transient history, buffer, RNG, hidden units, or
    other plastic state.  ``observe_transition`` must be called only after the
    physical transition has produced its typed next observation.
    """

    __slots__ = ("_weights",)

    def __init__(self) -> None:
        self._weights: dict[Action, dict[str, list[float]]] = {}
        self.reset()

    @property
    def weights(self) -> tuple[float, ...]:
        """Return all weights in action, output, feature order."""
        return tuple(
            weight
            for action in Action
            for output in D013_OUTPUTS
            for weight in self._weights[action][output]
        )

    def weight_snapshot(self) -> dict[str, dict[str, list[float]]]:
        """Return the complete learned state in stable output/action order."""
        return {
            output: {
                action.name: list(self._weights[action][output])
                for action in Action
            }
            for output in D013_OUTPUTS
        }

    def reset(self) -> None:
        """Begin a deliberate new lifetime with all 84 weights at zero."""
        self._weights = {
            action: {output: [0.0] * D013_FEATURE_DIMENSION for output in D013_OUTPUTS}
            for action in Action
        }

    def predict(
        self, observation: d011.D011Observation, action: Action
    ) -> D013Prediction:
        """Predict visible deltas before the environment executes ``action``."""
        self._validate_inputs(observation, action)
        features = self._features(observation)
        return D013Prediction(
            predicted_delta_energy=self._dot(
                self._weights[action]["delta_energy"], features
            ),
            predicted_delta_thermal=self._dot(
                self._weights[action]["delta_thermal"], features
            ),
            predicted_delta_charging_contact=self._dot(
                self._weights[action]["delta_charging_contact"], features
            ),
        )

    def observe_transition(
        self,
        observation: d011.D011Observation,
        action: Action,
        next_observation: d011.D011Observation,
    ) -> D013LearningUpdate:
        """Update only the executed action after its consequence is visible."""
        self._validate_inputs(observation, action)
        if not isinstance(next_observation, d011.D011Observation):
            raise ValueError("next_observation must be a D011Observation")

        prediction = self.predict(observation, action)
        observed_delta_energy = next_observation.energy - observation.energy
        observed_delta_thermal = next_observation.thermal - observation.thermal
        observed_delta_charging_contact = float(
            next_observation.charging_contact
        ) - float(observation.charging_contact)
        errors = {
            "delta_energy": (
                observed_delta_energy - prediction.predicted_delta_energy
            ),
            "delta_thermal": (
                observed_delta_thermal - prediction.predicted_delta_thermal
            ),
            "delta_charging_contact": (
                observed_delta_charging_contact
                - prediction.predicted_delta_charging_contact
            ),
        }
        features = self._features(observation)
        normalizer = self._dot(features, features)
        for output in D013_OUTPUTS:
            for index, feature in enumerate(features):
                self._weights[action][output][index] += (
                    D013_LEARNING_RATE * errors[output] * feature / normalizer
                )
        return D013LearningUpdate(
            action=action,
            predicted_delta_energy=prediction.predicted_delta_energy,
            predicted_delta_thermal=prediction.predicted_delta_thermal,
            predicted_delta_charging_contact=(
                prediction.predicted_delta_charging_contact
            ),
            observed_delta_energy=observed_delta_energy,
            observed_delta_thermal=observed_delta_thermal,
            observed_delta_charging_contact=observed_delta_charging_contact,
            energy_error=errors["delta_energy"],
            thermal_error=errors["delta_thermal"],
            charging_contact_error=errors["delta_charging_contact"],
            normalizer=normalizer,
        )

    @staticmethod
    def _validate_inputs(
        observation: d011.D011Observation, action: Action
    ) -> None:
        if not isinstance(observation, d011.D011Observation):
            raise ValueError("observation must be a D011Observation")
        if not isinstance(action, Action):
            raise ValueError("action must be an Action")

    @staticmethod
    def _features(observation: d011.D011Observation) -> tuple[float, ...]:
        return (
            1.0,
            observation.energy,
            observation.beacon.left,
            observation.beacon.forward,
            observation.beacon.right,
            float(observation.charging_contact),
            observation.thermal,
        )

    @staticmethod
    def _dot(left: Sequence[float], right: Sequence[float]) -> float:
        return sum(
            left_value * right_value for left_value, right_value in zip(left, right)
        )


def _validate_d013_development_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    """Apply the canonical guard, then accept only declared D-013 seeds."""
    validated = validate_exp003_development_seeds(seeds)
    unexpected = tuple(
        seed for seed in validated if seed not in D013_DEFAULT_DEVELOPMENT_SEEDS
    )
    if unexpected:
        raise ValueError(
            "D-013 may execute only predeclared development seeds "
            f"{D013_DEFAULT_DEVELOPMENT_SEEDS}; got {unexpected}"
        )
    return validated


@dataclass(slots=True)
class _TargetMetricSums:
    count: int = 0
    learned_absolute_error_sum: float = 0.0
    baseline_absolute_error_sum: float = 0.0

    def record(self, learned_error: float, observed_delta: float) -> None:
        self.count += 1
        self.learned_absolute_error_sum += abs(learned_error)
        self.baseline_absolute_error_sum += abs(observed_delta)

    def as_dict(self) -> dict[str, object]:
        if self.count == 0:
            return {
                "status": "untested",
                "transition_count": 0,
                "learned_mae": None,
                "zero_change_baseline_mae": None,
                "learned_baseline_mae_ratio": None,
            }
        learned_mae = self.learned_absolute_error_sum / self.count
        baseline_mae = self.baseline_absolute_error_sum / self.count
        return {
            "status": "visited",
            "transition_count": self.count,
            "learned_mae": learned_mae,
            "zero_change_baseline_mae": baseline_mae,
            "learned_baseline_mae_ratio": (
                learned_mae / baseline_mae if baseline_mae else None
            ),
        }


@dataclass(slots=True)
class _RangeStats:
    minimum: float | None = None
    maximum: float | None = None

    def record(self, value: float) -> None:
        self.minimum = value if self.minimum is None else min(self.minimum, value)
        self.maximum = value if self.maximum is None else max(self.maximum, value)

    def as_dict(self) -> dict[str, float | None]:
        return {"min": self.minimum, "max": self.maximum}


@dataclass(slots=True)
class _ActionSupport:
    count: int = 0
    current_contact_counts: dict[str, int] = field(
        default_factory=lambda: {"False": 0, "True": 0}
    )
    contact_delta_target_counts: dict[str, int] = field(
        default_factory=lambda: {"-1": 0, "0": 0, "+1": 0}
    )
    overall: dict[str, _TargetMetricSums] = field(
        default_factory=lambda: {
            target: _TargetMetricSums() for target in D013_OUTPUTS
        }
    )
    q4: dict[str, _TargetMetricSums] = field(
        default_factory=lambda: {
            target: _TargetMetricSums() for target in D013_OUTPUTS
        }
    )
    ranges: dict[str, _RangeStats] = field(
        default_factory=lambda: {
            channel: _RangeStats() for channel in D013_CHANNELS
        }
    )

    def record(
        self,
        observation: d011.D011Observation,
        prediction: D013Prediction,
        update: D013LearningUpdate,
        *,
        in_q4: bool,
    ) -> None:
        self.count += 1
        contact_key = str(observation.charging_contact)
        self.current_contact_counts[contact_key] += 1
        delta_key = {
            -1.0: "-1",
            0.0: "0",
            1.0: "+1",
        }.get(update.observed_delta_charging_contact)
        if delta_key is None:
            raise RuntimeError("D-013 contact delta is not -1, 0, or +1")
        self.contact_delta_target_counts[delta_key] += 1
        values = {
            "energy": observation.energy,
            "beacon.left": observation.beacon.left,
            "beacon.forward": observation.beacon.forward,
            "beacon.right": observation.beacon.right,
            "charging_contact": float(observation.charging_contact),
            "thermal": observation.thermal,
        }
        for channel, value in values.items():
            self.ranges[channel].record(value)
        prediction_values = prediction.as_dict()
        observed_values = {
            "delta_energy": update.observed_delta_energy,
            "delta_thermal": update.observed_delta_thermal,
            "delta_charging_contact": update.observed_delta_charging_contact,
        }
        for target in D013_OUTPUTS:
            self.overall[target].record(
                prediction_values[target] - observed_values[target],
                observed_values[target],
            )
            if in_q4:
                self.q4[target].record(
                    prediction_values[target] - observed_values[target],
                    observed_values[target],
                )

    def as_dict(self) -> dict[str, object]:
        return {
            "status": "untested" if self.count == 0 else "visited",
            "execution_count": self.count,
            "current_charging_contact_counts": dict(self.current_contact_counts),
            "observed_contact_delta_target_counts": dict(
                self.contact_delta_target_counts
            ),
            "overall_target_metrics": {
                target: self.overall[target].as_dict() for target in D013_OUTPUTS
            },
            "q4_target_metrics": {
                target: self.q4[target].as_dict() for target in D013_OUTPUTS
            },
            "current_visible_channel_ranges": {
                channel: self.ranges[channel].as_dict() for channel in D013_CHANNELS
            },
        }


def _support_table() -> dict[Action, _ActionSupport]:
    return {action: _ActionSupport() for action in Action}


def _empty_metric_sums() -> dict[str, _TargetMetricSums]:
    return {target: _TargetMetricSums() for target in D013_OUTPUTS}


def _metric_summary(
    sums: dict[str, _TargetMetricSums], *, transition_count: int | None = None
) -> dict[str, object]:
    count = (
        transition_count
        if transition_count is not None
        else max((metrics.count for metrics in sums.values()), default=0)
    )
    return {
        "transition_count": count,
        "targets": {target: sums[target].as_dict() for target in D013_OUTPUTS},
    }


def _record_metrics(
    sums: dict[str, _TargetMetricSums],
    prediction: D013Prediction,
    update: D013LearningUpdate,
) -> None:
    prediction_values = prediction.as_dict()
    observed_values = {
        "delta_energy": update.observed_delta_energy,
        "delta_thermal": update.observed_delta_thermal,
        "delta_charging_contact": update.observed_delta_charging_contact,
    }
    for target in D013_OUTPUTS:
        sums[target].record(
            prediction_values[target] - observed_values[target], observed_values[target]
        )


def _window_name(transition_number: int) -> str:
    return f"Q{((transition_number - 1) // D013_WINDOW_SIZE) + 1}"


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


def _run_seed(seed: int, *, horizon: int) -> dict[str, object]:
    config = EXP003StationConfig(episode_horizon=horizon)
    environment = D002ThermalStationEnv(config=config)
    observation, info = environment.reset(seed=seed)
    if info != {}:
        raise RuntimeError("D-002 reset crossed the information boundary")
    seeded_heading, observation = d011._prepare_post_contact_setup(environment)
    if environment.base_env.random_streams is None:
        raise RuntimeError("D-002 policy RNG is unavailable after reset")

    controller = d011.D011Controller(environment.base_env.random_streams.policy)
    controller.reset()
    predictor = D013ActionConsequencePredictor()
    action_counts = {action.name: 0 for action in Action}
    mode_occupancy = {mode.name: 0 for mode in d011.D011Mode}
    mode_entry_counts = {mode.name: 0 for mode in d011.D011Mode}
    mode_entry_counts[controller.mode.name] = 1
    supports = _support_table()
    context_supports = {
        contact: _support_table() for contact in (False, True)
    }
    overall_sums = _empty_metric_sums()
    window_sums = {
        f"Q{index}": _empty_metric_sums() for index in range(1, 5)
    }
    checkpoints: dict[str, dict[str, dict[str, list[float]]]] = {}

    transitions = 0
    minimum_energy = config.initial_energy
    maximum_energy = config.initial_energy
    minimum_normalized_energy = float(observation[0])
    maximum_normalized_energy = float(observation[0])
    minimum_thermal = float(observation[5])
    maximum_thermal = float(observation[5])
    thermal_departures = 0
    charger_exits = 0
    away_entries = 0
    low_energy_seek_entries = 0
    successful_reacquisitions = 0
    accidental_away_contacts = 0
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
            thermal_departures += 1
            cycle_open = True
            cycle_has_exit = False
            cycle_waiting_for_reacquisition = False
        if mode_before is d011.D011Mode.DEPART and mode_after is d011.D011Mode.AWAY:
            away_entries += 1

        prediction = predictor.predict(current, action)
        observation, reward, terminated, truncated, info = environment.step(action)
        if reward != 0.0 or info != {}:
            raise RuntimeError("D-002 reward or info crossed the boundary")
        next_observation = d011._controller_observation(observation)
        update = predictor.observe_transition(current, action, next_observation)

        # Inherited evaluator-side post-contact setup and seeded geometry were
        # established before the lifetime loop. No per-transition geometry
        # trajectory is collected. Per-transition evaluator telemetry used for
        # summaries is read only after the causal learner update.
        telemetry = environment.last_transition
        body = environment.body
        if telemetry is None or body is None:
            raise RuntimeError("D-013 transition telemetry is unavailable")
        transitions += 1

        _record_metrics(overall_sums, prediction, update)
        window = window_sums.get(_window_name(transitions))
        if window is not None:
            _record_metrics(window, prediction, update)
        supports[action].record(
            current,
            prediction,
            update,
            in_q4=751 <= transitions <= 1000,
        )
        context_supports[current.charging_contact][action].record(
            current,
            prediction,
            update,
            in_q4=751 <= transitions <= 1000,
        )
        if transitions in D013_WINDOW_ENDS:
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
        if (
            mode_before is d011.D011Mode.AWAY
            and mode_after is d011.D011Mode.AWAY
            and telemetry.charging_contact_after
        ):
            accidental_away_contacts += 1

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
        raise RuntimeError("D-013 run ended without final telemetry")
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
        "thermal_triggered_departures": thermal_departures,
        "successful_physical_charger_exits": charger_exits,
        "away_entries": away_entries,
        "low_energy_seek_entries": low_energy_seek_entries,
        "successful_charging_contact_reacquisitions": successful_reacquisitions,
        "completed_autonomous_regulation_cycles": completed_cycles,
        "demonstrated_failed_seek_episodes": int(
            active_seek and terminated and not truncated
        ),
        "horizon_censored_seek_episodes": int(active_seek and truncated),
        "accidental_away_contacts": accidental_away_contacts,
        "prediction_metrics": {
            "windows": {
                name: _metric_summary(sums)
                for name, sums in window_sums.items()
                if sum(metric.count for metric in sums.values()) > 0
            },
            "overall": _metric_summary(
                overall_sums,
                transition_count=transitions,
            ),
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
            "passed_to_learner": False,
        },
    }


def run_d013_probe(
    seeds: Sequence[int] = D013_DEFAULT_DEVELOPMENT_SEEDS,
    *,
    horizon: int = D013_HORIZON,
    executed_commit_sha: str | None = None,
) -> dict[str, object]:
    """Run one uninterrupted shadow-learning D-013 lifetime per seed."""
    development_seeds = _validate_d013_development_seeds(seeds)
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon <= 0:
        raise ValueError("horizon must be a positive integer")
    if executed_commit_sha is not None and re.fullmatch(
        r"[0-9a-f]{40}", executed_commit_sha
    ) is None:
        raise ValueError("executed_commit_sha must be a 40-character lowercase SHA")
    return {
        "schema_version": 1,
        "experiment": "D-013",
        "title": "Full-observation shadow viability consequence learner",
        "authoritative_base_sha": D013_AUTHORITATIVE_BASE_SHA,
        "executed_commit_sha": executed_commit_sha,
        "development_seeds": list(development_seeds),
        "horizon": horizon,
        "lifetime": "one uninterrupted lifetime per seed",
        "seed_policy": {
            "canonical_validator": "validate_exp003_development_seeds",
            "exact_declared_seeds": list(D013_DEFAULT_DEVELOPMENT_SEEDS),
            "formal_reservation_guard_preserved": True,
        },
        "programmed": {
            "controller": "unchanged D011Controller",
            "runner_reuses": [
                "d011._controller_observation",
                "d011._prepare_post_contact_setup",
            ],
            "d011_action_logic_unchanged": True,
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
            "controller_mode_is_learner_input": False,
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
            "type": "action-conditioned linear one-step delta predictor",
            "actions": [action.name for action in Action],
            "outputs": list(D013_OUTPUTS),
            "feature_dimension": D013_FEATURE_DIMENSION,
            "learning_rate": D013_LEARNING_RATE,
            "initial_weights": 0.0,
            "update": (
                "weights += 0.5 * (observed_delta - dot(weights, x)) * x / dot(x, x)"
            ),
            "prediction_scored_before_update": True,
            "plastic_state_dimension": D013_PLASTIC_STATE_DIMENSION,
            "plastic_state_order": "action, output, feature",
            "extra_plastic_state": False,
            "rng": False,
            "history": False,
            "optimizer_state": False,
            "buffer": False,
            "reset": "all 84 weights zero only at deliberate new-lifetime reset",
        },
        "evaluator_only": {
            "metrics": [
                "behavior/viability summaries",
                "pre-update learned and zero-change MAE",
                "action/context support and visible ranges",
                "complete weight checkpoints and final state",
            ],
            "geometry_passed_to_learner": False,
            "mode_passed_to_learner": False,
            "prediction_causal_effect_on_behavior": False,
        },
        "ecology": {
            "environment": "D002ThermalStationEnv",
            "charging_heat_per_offered_energy": D002_CHARGING_HEAT_PER_OFFERED_ENERGY,
            "passive_cooling_per_transition": D002_PASSIVE_COOLING_PER_TRANSITION,
            "thermal_failure_boundary": D002_UPPER_THERMAL_FAILURE_BOUNDARY,
            "charging_radius": EXP003_CHARGING_RADIUS,
            "post_contact_setup": "unchanged D-011 setup",
        },
        "organism_boundary": {"reward": 0.0, "info": {}},
        "results": [_run_seed(seed, horizon=horizon) for seed in development_seeds],
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the D-013 full-observation shadow learner."
    )
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=list(D013_DEFAULT_DEVELOPMENT_SEEDS),
        help="Predeclared D-013 development seeds only.",
    )
    parser.add_argument("--horizon", type=int, default=D013_HORIZON)
    parser.add_argument("--executed-commit-sha")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    """Run D-013 and print or write its machine-readable result."""
    args = _parse_args()
    payload = json.dumps(
        run_d013_probe(
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
        print(f"D-013 result written to {args.output}")


if __name__ == "__main__":
    main()
