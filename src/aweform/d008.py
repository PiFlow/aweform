"""D-008 minimal action-conditioned one-step consequence model.

The D-008 predictor is a shadow learner attached to the unchanged D-003
``ThermostaticShuttleController``.  Its organism-visible inputs are exactly
normalized thermal interoception, charging contact, and the organism's own
selected action.  After that action's physical consequence occurs, its
plastic update receives only the next thermal/contact observation and the
retained learned weights.

The complete persistent plastic state is 24 scalar weights: one three-weight
thermal-delta vector and one three-weight charging-contact-delta vector for
each of the four actions.  The predictor has no transient retained state, no
RNG, and no evaluator inputs.  A deliberate ``reset`` starts a new lifetime
and sets all weights to zero; the runner never resets it during a lifetime.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Sequence

from .d002 import (
    D002_CHARGING_HEAT_PER_OFFERED_ENERGY,
    D002_PASSIVE_COOLING_PER_TRANSITION,
    D002_UPPER_THERMAL_FAILURE_BOUNDARY,
    D002ThermalStationEnv,
)
from .d003 import (
    D003ThermostaticObservation,
    ThermostaticShuttleController,
    _controller_observation,
    _prepare_post_contact_setup,
)
from .env import Action
from .exp003 import EXP003_CHARGING_RADIUS, EXP003_HORIZON, EXP003StationConfig
from .exp003_seed_policy import validate_exp003_development_seeds

D008_LEARNING_RATE: Final[float] = 0.5
D008_FEATURE_DIMENSION: Final[int] = 3
D008_PLASTIC_STATE_DIMENSION: Final[int] = 24
D008_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = (18141, 18142, 18143)
D008_WINDOW_SIZE: Final[int] = 250
D008_WINDOW_ENDS: Final[tuple[int, ...]] = (250, 500, 750, 1000)

if len(Action) * 2 * D008_FEATURE_DIMENSION != D008_PLASTIC_STATE_DIMENSION:
    raise RuntimeError("D-008 plastic dimension no longer matches the action space")


@dataclass(frozen=True, slots=True)
class D008Prediction:
    """Pre-update prediction for one selected action."""

    predicted_delta_thermal: float
    predicted_delta_contact: float

    def as_dict(self) -> dict[str, float]:
        """Return a JSON-compatible evaluator copy."""
        return {
            "delta_thermal": self.predicted_delta_thermal,
            "delta_charging_contact": self.predicted_delta_contact,
        }


@dataclass(frozen=True, slots=True)
class D008LearningUpdate:
    """One visible consequence target and normalized LMS plastic update."""

    action: Action
    predicted_delta_thermal: float
    predicted_delta_contact: float
    observed_delta_thermal: float
    observed_delta_contact: float
    thermal_error: float
    contact_error: float
    normalizer: float

    def as_dict(self) -> dict[str, object]:
        """Return a compact JSON-compatible evaluator copy."""
        return {
            "action": self.action.name,
            "predicted_delta_thermal": self.predicted_delta_thermal,
            "predicted_delta_contact": self.predicted_delta_contact,
            "observed_delta_thermal": self.observed_delta_thermal,
            "observed_delta_contact": self.observed_delta_contact,
            "thermal_error": self.thermal_error,
            "contact_error": self.contact_error,
            "normalizer": self.normalizer,
        }


class D008ActionConsequencePredictor:
    """Tiny deterministic action-conditioned one-step delta predictor.

    ``predict`` consumes only a typed current observation and the selected
    ``Action``.  ``observe_transition`` consumes that same observation/action
    pair plus the typed next observation after the action has physically
    occurred.  It updates only the six weights for the executed action.

    Persistent plastic state is exactly 24 scalar weights.  There is no
    transient state, optimizer state, buffer, hidden unit, or RNG.  The
    normalized LMS update is applied independently to thermal and contact
    deltas after the consequence is observed.
    """

    def __init__(self) -> None:
        self._thermal_delta_weights: dict[Action, list[float]] = {}
        self._contact_delta_weights: dict[Action, list[float]] = {}
        self.reset()

    @property
    def weights(self) -> tuple[float, ...]:
        """Return all 24 learned scalars in stable action/output order."""
        return tuple(
            weight
            for action in Action
            for weights in (
                self._thermal_delta_weights[action],
                self._contact_delta_weights[action],
            )
            for weight in weights
        )

    def weight_snapshot(self) -> dict[str, dict[str, list[float]]]:
        """Return complete evaluator-readable learned-state weights."""
        return {
            "delta_thermal": {
                action.name: list(self._thermal_delta_weights[action])
                for action in Action
            },
            "delta_charging_contact": {
                action.name: list(self._contact_delta_weights[action])
                for action in Action
            },
        }

    def reset(self) -> None:
        """Start a deliberate new lifetime with all 24 weights exactly zero."""
        for action in Action:
            self._thermal_delta_weights[action] = [0.0] * D008_FEATURE_DIMENSION
            self._contact_delta_weights[action] = [0.0] * D008_FEATURE_DIMENSION

    def predict(
        self, observation: D003ThermostaticObservation, action: Action
    ) -> D008Prediction:
        """Predict visible one-step consequence deltas before environment.step."""
        self._validate_inputs(observation, action)
        features = self._features(observation)
        return D008Prediction(
            predicted_delta_thermal=self._dot(
                self._thermal_delta_weights[action], features
            ),
            predicted_delta_contact=self._dot(
                self._contact_delta_weights[action], features
            ),
        )

    def observe_transition(
        self,
        observation: D003ThermostaticObservation,
        action: Action,
        next_observation: D003ThermostaticObservation,
    ) -> D008LearningUpdate:
        """Update the executed action from its now-observed consequence.

        The caller must invoke this only after the physical transition has
        produced ``next_observation``.  The returned predictions are the
        pre-update values and are therefore suitable for scoring.
        """
        self._validate_inputs(observation, action)
        if not isinstance(next_observation, D003ThermostaticObservation):
            raise ValueError(
                "next_observation must be a D003ThermostaticObservation"
            )
        prediction = self.predict(observation, action)
        observed_delta_thermal = next_observation.thermal - observation.thermal
        observed_delta_contact = float(next_observation.charging_contact) - float(
            observation.charging_contact
        )
        thermal_error = observed_delta_thermal - prediction.predicted_delta_thermal
        contact_error = observed_delta_contact - prediction.predicted_delta_contact
        features = self._features(observation)
        normalizer = self._dot(features, features)
        for index, feature in enumerate(features):
            self._thermal_delta_weights[action][index] += (
                D008_LEARNING_RATE * thermal_error * feature / normalizer
            )
            self._contact_delta_weights[action][index] += (
                D008_LEARNING_RATE * contact_error * feature / normalizer
            )
        return D008LearningUpdate(
            action=action,
            predicted_delta_thermal=prediction.predicted_delta_thermal,
            predicted_delta_contact=prediction.predicted_delta_contact,
            observed_delta_thermal=observed_delta_thermal,
            observed_delta_contact=observed_delta_contact,
            thermal_error=thermal_error,
            contact_error=contact_error,
            normalizer=normalizer,
        )

    @staticmethod
    def _validate_inputs(
        observation: D003ThermostaticObservation, action: Action
    ) -> None:
        if not isinstance(observation, D003ThermostaticObservation):
            raise ValueError("observation must be a D003ThermostaticObservation")
        if not isinstance(action, Action):
            raise ValueError("action must be an Action")

    @staticmethod
    def _features(observation: D003ThermostaticObservation) -> tuple[float, ...]:
        return (1.0, observation.thermal, float(observation.charging_contact))

    @staticmethod
    def _dot(left: Sequence[float], right: Sequence[float]) -> float:
        return sum(
            left_value * right_value for left_value, right_value in zip(left, right)
        )


def _validate_d008_development_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    """Validate existing reservations and the exact D-008 seed declaration."""
    validated = validate_exp003_development_seeds(seeds)
    unexpected = tuple(
        seed for seed in validated if seed not in D008_DEFAULT_DEVELOPMENT_SEEDS
    )
    if unexpected:
        raise ValueError(
            "D-008 may execute only predeclared development seeds "
            f"{D008_DEFAULT_DEVELOPMENT_SEEDS}; got {unexpected}"
        )
    return validated


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


def _empty_context_summary() -> dict[str, object]:
    return {
        "count": 0,
        "current_thermal_min": None,
        "current_thermal_max": None,
        "contact_delta_target_counts": {"-1": 0, "0": 0, "+1": 0},
        "thermal_delta_min": None,
        "thermal_delta_max": None,
    }


def _context_summaries() -> dict[str, dict[str, dict[str, object]]]:
    return {
        str(contact): {action.name: _empty_context_summary() for action in Action}
        for contact in (False, True)
    }


def _record_context(
    contexts: dict[str, dict[str, dict[str, object]]],
    observation: D003ThermostaticObservation,
    action: Action,
    update: D008LearningUpdate,
) -> None:
    context = contexts[str(observation.charging_contact)][action.name]
    count = context["count"]
    if not isinstance(count, int):
        raise RuntimeError("D-008 context count is not an integer")
    context["count"] = count + 1
    current_min = context["current_thermal_min"]
    current_max = context["current_thermal_max"]
    if current_min is not None and not isinstance(current_min, (int, float)):
        raise RuntimeError("D-008 current thermal minimum is not numeric")
    if current_max is not None and not isinstance(current_max, (int, float)):
        raise RuntimeError("D-008 current thermal maximum is not numeric")
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
    contact_key = {"-1.0": "-1", "0.0": "0", "1.0": "+1"}[str(
        update.observed_delta_contact
    )]
    target_counts = context["contact_delta_target_counts"]
    if not isinstance(target_counts, dict):
        raise RuntimeError("D-008 contact target counts are not a dictionary")
    target_counts[contact_key] += 1
    delta_min = context["thermal_delta_min"]
    delta_max = context["thermal_delta_max"]
    if delta_min is not None and not isinstance(delta_min, (int, float)):
        raise RuntimeError("D-008 thermal delta minimum is not numeric")
    if delta_max is not None and not isinstance(delta_max, (int, float)):
        raise RuntimeError("D-008 thermal delta maximum is not numeric")
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


def _metric_summary(sums: dict[str, float | int]) -> dict[str, object]:
    count = int(sums["transition_count"])
    if count == 0:
        return {"transition_count": 0}
    return {
        "transition_count": count,
        "learned_model_thermal_mae": float(
            sums["thermal_absolute_error_sum"]
        )
        / count,
        "zero_change_baseline_thermal_mae": float(
            sums["thermal_baseline_absolute_error_sum"]
        )
        / count,
        "learned_model_contact_delta_mae": float(
            sums["contact_absolute_error_sum"]
        )
        / count,
        "zero_change_baseline_contact_delta_mae": float(
            sums["contact_baseline_absolute_error_sum"]
        )
        / count,
    }


def _record_metrics(
    sums: dict[str, float | int], update: D008LearningUpdate, prediction: D008Prediction
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


def _window_name(transition_number: int) -> str:
    return f"Q{((transition_number - 1) // D008_WINDOW_SIZE) + 1}"


def _run_seed(seed: int, *, horizon: int) -> dict[str, object]:
    config = EXP003StationConfig(episode_horizon=horizon)
    environment = D002ThermalStationEnv(config=config)
    observation, info = environment.reset(seed=seed)
    if info != {}:
        raise RuntimeError("D-002 reset crossed the information boundary")
    seeded_heading, observation = _prepare_post_contact_setup(environment)

    controller = ThermostaticShuttleController()
    controller.reset()
    predictor = D008ActionConsequencePredictor()
    action_counts = {action.name: 0 for action in Action}
    contexts = _context_summaries()
    window_sums = {f"Q{index}": _empty_metric_sums() for index in range(1, 5)}
    overall_sums = _empty_metric_sums()
    checkpoints: dict[str, dict[str, dict[str, list[float]]]] = {}
    transitions = 0
    minimum_energy = config.initial_energy
    maximum_energy = config.initial_energy
    minimum_thermal = float(observation[5])
    maximum_thermal = float(observation[5])
    terminated = False
    truncated = False

    while not (terminated or truncated):
        current_observation = _controller_observation(observation)
        action = controller.act(current_observation)
        action_counts[action.name] += 1
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
            raise RuntimeError("D-008 transition telemetry is unavailable")
        transitions += 1
        _record_context(contexts, current_observation, action, update)
        _record_metrics(overall_sums, update, prediction)
        window = window_sums.get(_window_name(transitions))
        if window is not None:
            _record_metrics(window, update, prediction)
        if transitions in D008_WINDOW_ENDS:
            checkpoints[str(transitions)] = predictor.weight_snapshot()

        minimum_energy = min(minimum_energy, telemetry.energy_after)
        maximum_energy = max(maximum_energy, telemetry.energy_after)
        minimum_thermal = min(minimum_thermal, telemetry.thermal_after)
        maximum_thermal = max(maximum_thermal, telemetry.thermal_after)

    if environment.last_transition is None or environment.body is None:
        raise RuntimeError("D-008 run ended without final telemetry")
    final = environment.last_transition
    return {
        "seed": seed,
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
        "action_counts": action_counts,
        "contact_action_contexts": contexts,
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
    }


def run_d008_probe(
    seeds: Sequence[int] = D008_DEFAULT_DEVELOPMENT_SEEDS,
    *,
    horizon: int = EXP003_HORIZON,
) -> dict[str, object]:
    """Run one uninterrupted shadow-learning D-008 lifetime per legal seed."""
    development_seeds = _validate_d008_development_seeds(seeds)
    results = [_run_seed(seed, horizon=horizon) for seed in development_seeds]
    return {
        "schema_version": 1,
        "experiment": "D-008",
        "title": "Minimal action-conditioned one-step consequence model",
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
        "behaviour_policy": {
            "controller": "ThermostaticShuttleController",
            "action_selection": "D-003 controller alone selects every action",
            "shadow_predictor_causal_effect": False,
            "forced_actions": False,
        },
        "model": {
            "type": "action-conditioned linear delta predictor",
            "actions": [action.name for action in Action],
            "features": ["bias=1.0", "thermal", "charging_contact"],
            "predicted_consequences": ["delta_thermal", "delta_charging_contact"],
            "learning_rate": D008_LEARNING_RATE,
            "initial_weights": 0.0,
            "update": (
                "weights += 0.5 * (observed_delta - dot(weights, x)) * x / dot(x, x)"
            ),
            "prediction_scored_before_update": True,
        },
        "organism_information_boundary": {
            "predict_inputs": ["thermal", "charging_contact", "own_action"],
            "update_inputs": [
                "current thermal",
                "current charging_contact",
                "own action",
                "next thermal",
                "next charging_contact",
            ],
            "excluded": [
                "energy",
                "coordinates",
                "station_center",
                "distance",
                "heading",
                "controller_mode",
                "transition_index",
                "clock",
                "horizon",
                "seed_identity",
                "reward",
                "info",
                "evaluator_telemetry",
                "offered_station_energy",
                "stored_energy_delta",
                "thermal_input_truth",
                "termination_metrics",
            ],
        },
        "plastic_state": {
            "dimension": D008_PLASTIC_STATE_DIMENSION,
            "persistent_fields": [
                "delta_thermal_weights[action][bias, thermal, charging_contact]",
                (
                    "delta_charging_contact_weights[action]"
                    "[bias, thermal, charging_contact]"
                ),
            ],
            "transient_fields": [],
            "rng": False,
            "reset": "all weights zero only at deliberate new-lifetime reset",
        },
        "summary_windows": {
            "Q1": "transitions 1-250",
            "Q2": "transitions 251-500",
            "Q3": "transitions 501-750",
            "Q4": "transitions 751-1000",
        },
        "organism_boundary": {"reward": 0.0, "info": {}},
        "results": results,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the D-008 shadow action-conditioned consequence probe."
    )
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=list(D008_DEFAULT_DEVELOPMENT_SEEDS),
        help="Predeclared D-008 development seeds only.",
    )
    parser.add_argument(
        "--horizon",
        type=int,
        default=EXP003_HORIZON,
        help="Finite D-008 lifetime horizon.",
    )
    parser.add_argument(
        "--output", type=Path, help="Write the machine-readable result directly here."
    )
    return parser.parse_args()


def main() -> None:
    """Run D-008 and print or directly write its compact result."""
    args = _parse_args()
    payload = json.dumps(
        run_d008_probe(tuple(args.seeds), horizon=args.horizon),
        indent=2,
        sort_keys=True,
    )
    if args.output is None:
        print(payload)
    else:
        args.output.write_text(payload + "\n", encoding="utf-8")
        print(f"D-008 result written to {args.output}")


if __name__ == "__main__":
    main()
