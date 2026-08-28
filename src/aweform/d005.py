"""D-005 minimal predictive thermal-overshoot adaptation.

This module retains the D-003 post-contact shuttle and adds one bounded,
deterministic lifetime-plastic scalar.  The controller receives only the
normalized thermal interoception and charging-contact observation.  Evaluator
telemetry is used only by the development harness after execution; it is not
passed to the controller or to its consequence update.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Final, Sequence

from .body import Coordinate
from .d002 import D002ThermalStationEnv
from .d003 import (
    COOL_RETURN_THRESHOLD,
    HOT_DEPART_THRESHOLD,
    RETURN_HALF_TURN_STEPS,
    D003Mode,
    D003ThermostaticObservation,
    _controller_observation,
    _prepare_post_contact_setup,
)
from .env import Action
from .exp003 import EXP003_HORIZON, EXP003StationConfig
from .exp003_seed_policy import validate_exp003_development_seeds

D005_ALPHA: Final[float] = 0.5
D005_INITIAL_PREDICTED_DEPARTURE_THERMAL_OVERSHOOT: Final[float] = 0.0
D005_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = (18141, 18142, 18143)


@dataclass(frozen=True, slots=True)
class D005LearningUpdate:
    """One organism-visible departure consequence and plastic update."""

    departure_start_thermal: float
    observed_departure_thermal_overshoot: float
    prediction_before: float
    prediction_after: float

    def as_dict(self) -> dict[str, float]:
        """Return a compact JSON-compatible diagnostic copy."""
        return {
            "departure_start_thermal": self.departure_start_thermal,
            "observed_departure_thermal_overshoot": (
                self.observed_departure_thermal_overshoot
            ),
            "prediction_before": self.prediction_before,
            "prediction_after": self.prediction_after,
        }


@dataclass(frozen=True, slots=True)
class D005TraceEntry:
    """Evaluator-only diagnostics captured after one D-005 transition."""

    transition_index: int
    action: Action
    position: Coordinate
    heading: float
    energy: float
    thermal: float
    charging_contact: bool
    controller_mode: D003Mode
    terminated: bool
    truncated: bool
    prediction_used: float
    prediction_after_consequence: float
    update_occurred: bool
    observed_overshoot: float | None


class PredictiveThermalOvershootController:
    """D-003 shuttle with one causal lifetime-plastic departure predictor.

    Persistent causal state is only ``predicted_departure_thermal_overshoot``.
    It is initialized to zero and retained for this deliberate lifetime until
    :meth:`reset` starts a new lifetime.  During an active DEPART bout,
    ``departure_start_thermal`` and ``departure_peak_thermal`` are transient
    organism-owned state derived only from current thermal observations and
    the controller's own phase/action sequence.  They are cleared immediately
    when contact loss is first observed and the update is applied.
    """

    def __init__(self) -> None:
        self.reset()

    @property
    def mode(self) -> D003Mode:
        """Return the current D-003-compatible controller phase."""
        return self._mode

    @property
    def turns_remaining(self) -> int:
        """Return the bounded return-turn counter."""
        return self._turns_remaining

    @property
    def predicted_departure_thermal_overshoot(self) -> float:
        """Return the read-only persistent learned scalar."""
        return self._predicted_departure_thermal_overshoot

    @property
    def departure_start_thermal(self) -> float | None:
        """Return transient bout state, or ``None`` outside DEPART."""
        return self._departure_start_thermal

    @property
    def departure_peak_thermal(self) -> float | None:
        """Return transient bout state, or ``None`` outside DEPART."""
        return self._departure_peak_thermal

    def reset(self) -> None:
        """Start a deliberate new lifetime and clear all causal state."""
        self._mode = D003Mode.CHARGE
        self._turns_remaining = 0
        self._predicted_departure_thermal_overshoot = (
            D005_INITIAL_PREDICTED_DEPARTURE_THERMAL_OVERSHOOT
        )
        self._departure_start_thermal: float | None = None
        self._departure_peak_thermal: float | None = None

    def act(self, observation: D003ThermostaticObservation) -> Action:
        """Choose one action from the narrow current observation and state."""
        if not isinstance(observation, D003ThermostaticObservation):
            raise ValueError("observation must be a D003ThermostaticObservation")

        if self._mode is D003Mode.CHARGE:
            if (
                observation.thermal
                + self._predicted_departure_thermal_overshoot
                < HOT_DEPART_THRESHOLD
            ):
                return Action.WAIT
            self._departure_start_thermal = observation.thermal
            self._departure_peak_thermal = observation.thermal
            self._mode = D003Mode.DEPART
            return Action.MOVE_FORWARD

        if self._mode is D003Mode.DEPART:
            if observation.charging_contact:
                return Action.MOVE_FORWARD
            self._mode = D003Mode.COOL
            return Action.WAIT

        if self._mode is D003Mode.COOL:
            if observation.thermal > COOL_RETURN_THRESHOLD:
                return Action.WAIT
            self._turns_remaining = RETURN_HALF_TURN_STEPS
            self._mode = D003Mode.TURN_RETURN
            self._turns_remaining -= 1
            return Action.TURN_LEFT

        if self._mode is D003Mode.TURN_RETURN:
            if self._turns_remaining <= 0:
                raise RuntimeError("return turn counter exhausted before RETURN")
            self._turns_remaining -= 1
            if self._turns_remaining == 0:
                self._mode = D003Mode.RETURN
            return Action.TURN_LEFT

        if self._mode is D003Mode.RETURN:
            if observation.charging_contact:
                self._mode = D003Mode.CHARGE
                return Action.WAIT
            return Action.MOVE_FORWARD

        raise RuntimeError(f"unsupported controller mode: {self._mode}")

    def observe_consequence(
        self, observation: D003ThermostaticObservation
    ) -> D005LearningUpdate | None:
        """Process the next narrow observation after the selected action.

        This method is the only plastic-write seam.  It consumes no telemetry:
        the target is formed from the newly observed thermal value, contact,
        and the controller's own active departure state.  It must be called
        after each environment transition and before the next :meth:`act`.
        """
        if not isinstance(observation, D003ThermostaticObservation):
            raise ValueError("observation must be a D003ThermostaticObservation")
        if self._departure_start_thermal is None:
            return None
        if self._departure_peak_thermal is None:
            raise RuntimeError("departure peak is missing during an active bout")

        self._departure_peak_thermal = max(
            self._departure_peak_thermal, observation.thermal
        )
        if observation.charging_contact:
            return None

        observed_overshoot = max(
            0.0,
            self._departure_peak_thermal - self._departure_start_thermal,
        )
        prediction_before = self._predicted_departure_thermal_overshoot
        prediction_after = prediction_before + D005_ALPHA * (
            observed_overshoot - prediction_before
        )
        update = D005LearningUpdate(
            departure_start_thermal=self._departure_start_thermal,
            observed_departure_thermal_overshoot=observed_overshoot,
            prediction_before=prediction_before,
            prediction_after=prediction_after,
        )
        self._predicted_departure_thermal_overshoot = prediction_after
        self._departure_start_thermal = None
        self._departure_peak_thermal = None
        return update


def _mode_counts() -> dict[str, int]:
    return {mode.name: 0 for mode in D003Mode}


def _run_seed(
    seed: int,
    *,
    horizon: int,
    trace: list[D005TraceEntry] | None = None,
) -> dict[str, object]:
    config = EXP003StationConfig(episode_horizon=horizon)
    environment = D002ThermalStationEnv(config=config)
    observation, info = environment.reset(seed=seed)
    if info != {}:
        raise RuntimeError("D-002 reset crossed the information boundary")
    seeded_heading, observation = _prepare_post_contact_setup(environment)

    controller = PredictiveThermalOvershootController()
    controller.reset()
    initial_prediction = controller.predicted_departure_thermal_overshoot
    mode_occupancy = _mode_counts()
    mode_entry_counts = _mode_counts()
    mode_entry_counts[controller.mode.name] = 1
    action_counts = {action.name: 0 for action in Action}
    departure_start_thermal_values: list[float] = []
    learning_updates: list[dict[str, float]] = []
    transitions = 0
    minimum_energy = config.initial_energy
    maximum_energy = config.initial_energy
    minimum_thermal_state = float(observation[5])
    maximum_thermal_state = float(observation[5])
    charging_contact_transitions = 0
    off_contact_transitions = 0
    completed_shuttle_cycles = 0
    terminated = False
    truncated = False

    while not (terminated or truncated):
        mode_before = controller.mode
        mode_occupancy[mode_before.name] += 1
        controller_observation = _controller_observation(observation)
        prediction_used = controller.predicted_departure_thermal_overshoot
        action = controller.act(controller_observation)
        if mode_before is D003Mode.CHARGE and controller.mode is D003Mode.DEPART:
            if controller.departure_start_thermal is None:
                raise RuntimeError("departure start was not captured")
            departure_start_thermal_values.append(controller.departure_start_thermal)
        action_counts[action.name] += 1
        if controller.mode is not mode_before:
            mode_entry_counts[controller.mode.name] += 1
            if mode_before is D003Mode.RETURN and controller.mode is D003Mode.CHARGE:
                completed_shuttle_cycles += 1

        observation, reward, terminated, truncated, info = environment.step(action)
        if reward != 0.0 or info != {}:
            raise RuntimeError("D-002 reward or info crossed the boundary")
        next_controller_observation = _controller_observation(observation)
        update = controller.observe_consequence(next_controller_observation)
        if update is not None:
            learning_updates.append(update.as_dict())
        telemetry = environment.last_transition
        if telemetry is None or environment.body is None:
            raise RuntimeError("D-005 transition telemetry is unavailable")
        transitions += 1
        minimum_energy = min(minimum_energy, telemetry.energy_after)
        maximum_energy = max(maximum_energy, telemetry.energy_after)
        minimum_thermal_state = min(minimum_thermal_state, telemetry.thermal_after)
        maximum_thermal_state = max(maximum_thermal_state, telemetry.thermal_after)
        if telemetry.charging_contact_after:
            charging_contact_transitions += 1
        else:
            off_contact_transitions += 1
        if trace is not None:
            trace.append(
                D005TraceEntry(
                    transition_index=telemetry.step_index,
                    action=telemetry.action,
                    position=environment.body.position,
                    heading=environment.body.heading,
                    energy=telemetry.energy_after,
                    thermal=telemetry.thermal_after,
                    charging_contact=telemetry.charging_contact_after,
                    controller_mode=mode_before,
                    terminated=terminated,
                    truncated=truncated,
                    prediction_used=prediction_used,
                    prediction_after_consequence=(
                        controller.predicted_departure_thermal_overshoot
                    ),
                    update_occurred=update is not None,
                    observed_overshoot=(
                        update.observed_departure_thermal_overshoot
                        if update is not None
                        else None
                    ),
                )
            )

    if environment.last_transition is None or environment.body is None:
        raise RuntimeError("D-005 run ended without final telemetry")
    final = environment.last_transition
    return {
        "seed": seed,
        "transitions": transitions,
        "terminated": terminated,
        "truncated": truncated,
        "energy_termination": final.energy_termination,
        "thermal_termination": final.thermal_termination,
        "minimum_energy": minimum_energy,
        "maximum_energy": maximum_energy,
        "final_energy": environment.body.energy,
        "minimum_thermal_state": minimum_thermal_state,
        "maximum_thermal_state": maximum_thermal_state,
        "final_thermal_state": environment.thermal_state,
        "completed_shuttle_cycles": completed_shuttle_cycles,
        "charging_contact_transitions": charging_contact_transitions,
        "off_contact_transitions": off_contact_transitions,
        "mode_occupancy": mode_occupancy,
        "mode_entry_counts": mode_entry_counts,
        "action_counts": action_counts,
        "initial_position": [0.5, 0.5],
        "station_center": [0.5, 0.5],
        "seeded_heading": seeded_heading,
        "controller_input_fields": [
            "thermal_interoception",
            "charging_contact",
        ],
        "initial_prediction": initial_prediction,
        "final_prediction": controller.predicted_departure_thermal_overshoot,
        "learning_update_count": len(learning_updates),
        "learning_updates": learning_updates,
        "departure_start_thermal_values": departure_start_thermal_values,
        **({"trace": tuple(trace)} if trace is not None else {}),
    }


def run_d005_probe(
    seeds: Sequence[int] = D005_DEFAULT_DEVELOPMENT_SEEDS,
    *,
    horizon: int = EXP003_HORIZON,
    collect_trace: bool = False,
) -> dict[str, object]:
    """Run one uninterrupted D-005 lifetime per legal development seed."""
    development_seeds = validate_exp003_development_seeds(seeds)
    results: list[dict[str, object]] = []
    for seed in development_seeds:
        trace: list[D005TraceEntry] | None = [] if collect_trace else None
        results.append(_run_seed(seed, horizon=horizon, trace=trace))
    return {
        "development_seeds": list(development_seeds),
        "horizon": horizon,
        "controller_constants": {
            "hot_depart_threshold": HOT_DEPART_THRESHOLD,
            "cool_return_threshold": COOL_RETURN_THRESHOLD,
            "return_half_turn_steps": RETURN_HALF_TURN_STEPS,
            "alpha": D005_ALPHA,
            "initial_predicted_departure_thermal_overshoot": (
                D005_INITIAL_PREDICTED_DEPARTURE_THERMAL_OVERSHOOT
            ),
        },
        "controller_input_fields": [
            "thermal_interoception",
            "charging_contact",
        ],
        "cycle_definition": (
            "return to CHARGE after completing DEPART -> COOL -> TURN_RETURN -> RETURN"
        ),
        "results": results,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the D-005 predictive thermal-overshoot development probe."
    )
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=list(D005_DEFAULT_DEVELOPMENT_SEEDS),
        help="Legal development seeds only.",
    )
    parser.add_argument(
        "--horizon",
        type=int,
        default=EXP003_HORIZON,
        help="Finite development-probe horizon.",
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Include the full evaluator-only transition trace.",
    )
    return parser.parse_args()


def main() -> None:
    """Print the machine-readable D-005 development result."""
    args = _parse_args()
    print(
        json.dumps(
            run_d005_probe(
                tuple(args.seeds), horizon=args.horizon, collect_trace=args.trace
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
