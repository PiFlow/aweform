"""D-006 within-lifetime thermal consequence-shift adaptation.

D-006 keeps the D-002/D-003 ecology and the D-005 predictive controller,
changing only the environment-side charging-heat coefficient at transition
501.  The controller receives the same two-field observation as D-005 and
never receives the regime, transition index, or evaluator telemetry.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Final, Sequence

from .body import Coordinate
from .d002 import D002_CHARGING_HEAT_PER_OFFERED_ENERGY, D002ThermalStationEnv
from .d003 import (
    COOL_RETURN_THRESHOLD,
    HOT_DEPART_THRESHOLD,
    RETURN_HALF_TURN_STEPS,
    D003Mode,
    D003ThermostaticObservation,
    ThermostaticShuttleController,
    _controller_observation,
    _prepare_post_contact_setup,
)
from .d005 import (
    D005_ALPHA,
    D005_INITIAL_PREDICTED_DEPARTURE_THERMAL_OVERSHOOT,
    PredictiveThermalOvershootController,
)
from .env import Action
from .exp003 import EXP003_HORIZON, EXP003StationConfig
from .exp003_seed_policy import validate_exp003_development_seeds

D006_BASELINE_CHARGING_HEAT_PER_OFFERED_ENERGY: Final[float] = 0.04
D006_SHIFTED_CHARGING_HEAT_PER_OFFERED_ENERGY: Final[float] = 0.06
D006_REGIME_CHANGE_TRANSITION: Final[int] = 501
D006_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = (18141, 18142, 18143)


if (
    D006_BASELINE_CHARGING_HEAT_PER_OFFERED_ENERGY
    != D002_CHARGING_HEAT_PER_OFFERED_ENERGY
):
    raise RuntimeError("D-006 baseline must retain the D-002 charging heat")


class D006ThermalStationEnv(D002ThermalStationEnv):
    """D-002 thermal ecology with one D-006-only coefficient schedule."""

    def _charging_heat_per_offered_energy(self, transition_index: int) -> float:
        """Return the predeclared coefficient for this physical transition."""
        if transition_index < D006_REGIME_CHANGE_TRANSITION:
            return D006_BASELINE_CHARGING_HEAT_PER_OFFERED_ENERGY
        return D006_SHIFTED_CHARGING_HEAT_PER_OFFERED_ENERGY


@dataclass(frozen=True, slots=True)
class D006TraceEntry:
    """Evaluator-only diagnostics captured after one D-006 transition."""

    transition_index: int
    thermal_regime: str
    charging_heat_per_offered_energy: float
    action: Action
    position: Coordinate
    heading: float
    energy: float
    thermal: float
    charging_contact: bool
    controller_mode: D003Mode
    terminated: bool
    truncated: bool
    prediction_used: float | None
    prediction_after_consequence: float | None
    update_occurred: bool
    observed_overshoot: float | None


def _mode_counts() -> dict[str, int]:
    return {mode.name: 0 for mode in D003Mode}


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


def _common_result(
    *,
    seed: int,
    environment: D006ThermalStationEnv,
    seeded_heading: float,
    transitions: int,
    terminated: bool,
    truncated: bool,
    mode_occupancy: dict[str, int],
    mode_entry_counts: dict[str, int],
    action_counts: dict[str, int],
    minimum_energy: float,
    maximum_energy: float,
    minimum_thermal_state: float,
    maximum_thermal_state: float,
    charging_contact_transitions: int,
    off_contact_transitions: int,
    completed_shuttle_cycles: int,
) -> dict[str, object]:
    if environment.last_transition is None or environment.body is None:
        raise RuntimeError("D-006 run ended without final telemetry")
    final = environment.last_transition
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
        "thermal_regime_change_transition": D006_REGIME_CHANGE_TRANSITION,
    }


def _update_evaluator_departure_diagnostic(
    *,
    observation: D003ThermostaticObservation,
    departure_start: float | None,
    departure_peak: float | None,
    observed_overshoots: list[float],
) -> tuple[float | None, float | None]:
    """Track comparator-only overshoots without writing controller state."""
    if departure_start is None:
        return None, None
    if departure_peak is None:
        raise RuntimeError("evaluator departure peak is missing")
    departure_peak = max(departure_peak, observation.thermal)
    if observation.charging_contact:
        return departure_start, departure_peak
    observed_overshoots.append(max(0.0, departure_peak - departure_start))
    return None, None


def _run_predictive_seed(
    seed: int,
    *,
    horizon: int,
    trace: list[D006TraceEntry] | None,
) -> dict[str, object]:
    config = EXP003StationConfig(episode_horizon=horizon)
    environment = D006ThermalStationEnv(config=config)
    observation, info = environment.reset(seed=seed)
    if info != {}:
        raise RuntimeError("D-006 reset crossed the information boundary")
    seeded_heading, observation = _prepare_post_contact_setup(environment)

    controller = PredictiveThermalOvershootController()
    initial_prediction = controller.predicted_departure_thermal_overshoot
    mode_occupancy = _mode_counts()
    mode_entry_counts = _mode_counts()
    mode_entry_counts[controller.mode.name] = 1
    action_counts = {action.name: 0 for action in Action}
    departure_start_thermal_values: list[float] = []
    learning_updates: list[dict[str, object]] = []
    post_change_prediction_trajectory: list[dict[str, float | int]] = []
    transitions = 0
    minimum_energy = config.initial_energy
    maximum_energy = config.initial_energy
    minimum_thermal_state = float(observation[5])
    maximum_thermal_state = float(observation[5])
    charging_contact_transitions = 0
    off_contact_transitions = 0
    completed_shuttle_cycles = 0
    prediction_before_regime_change: float | None = None
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
            raise RuntimeError("D-006 reward or info crossed the boundary")
        next_controller_observation = _controller_observation(observation)
        update = controller.observe_consequence(next_controller_observation)

        # The telemetry read is deliberately after the only plastic-write seam.
        telemetry = environment.last_transition
        if telemetry is None or environment.body is None:
            raise RuntimeError("D-006 transition telemetry is unavailable")
        coefficient = environment._charging_heat_per_offered_energy(
            telemetry.step_index
        )
        if telemetry.step_index == D006_REGIME_CHANGE_TRANSITION:
            prediction_before_regime_change = prediction_used
        if update is not None:
            learning_updates.append(
                {
                    "transition_index": telemetry.step_index,
                    **update.as_dict(),
                }
            )
        if telemetry.step_index >= D006_REGIME_CHANGE_TRANSITION:
            post_change_prediction_trajectory.append(
                {
                    "transition_index": telemetry.step_index,
                    "prediction": controller.predicted_departure_thermal_overshoot,
                }
            )

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
                D006TraceEntry(
                    transition_index=telemetry.step_index,
                    thermal_regime=(
                        "baseline"
                        if telemetry.step_index < D006_REGIME_CHANGE_TRANSITION
                        else "shifted"
                    ),
                    charging_heat_per_offered_energy=coefficient,
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

    result = _common_result(
        seed=seed,
        environment=environment,
        seeded_heading=seeded_heading,
        transitions=transitions,
        terminated=terminated,
        truncated=truncated,
        mode_occupancy=mode_occupancy,
        mode_entry_counts=mode_entry_counts,
        action_counts=action_counts,
        minimum_energy=minimum_energy,
        maximum_energy=maximum_energy,
        minimum_thermal_state=minimum_thermal_state,
        maximum_thermal_state=maximum_thermal_state,
        charging_contact_transitions=charging_contact_transitions,
        off_contact_transitions=off_contact_transitions,
        completed_shuttle_cycles=completed_shuttle_cycles,
    )
    result.update(
        {
            "condition": "D-006 predictive",
            "initial_prediction": initial_prediction,
            "final_prediction": controller.predicted_departure_thermal_overshoot,
            "prediction_before_regime_change": prediction_before_regime_change,
            "learning_update_count": len(learning_updates),
            "learning_updates": learning_updates,
            "departure_start_thermal_values": departure_start_thermal_values,
            "post_change_prediction_trajectory": post_change_prediction_trajectory,
            "evaluator_observed_departure_thermal_overshoots": [
                update["observed_departure_thermal_overshoot"]
                for update in learning_updates
            ],
        }
    )
    if trace is not None:
        result["trace"] = tuple(trace)
    return result


def _run_comparator_seed(
    seed: int,
    *,
    horizon: int,
    trace: list[D006TraceEntry] | None,
) -> dict[str, object]:
    config = EXP003StationConfig(episode_horizon=horizon)
    environment = D006ThermalStationEnv(config=config)
    observation, info = environment.reset(seed=seed)
    if info != {}:
        raise RuntimeError("D-006 comparator reset crossed the information boundary")
    seeded_heading, observation = _prepare_post_contact_setup(environment)

    controller = ThermostaticShuttleController()
    mode_occupancy = _mode_counts()
    mode_entry_counts = _mode_counts()
    mode_entry_counts[controller.mode.name] = 1
    action_counts = {action.name: 0 for action in Action}
    departure_start_thermal_values: list[float] = []
    observed_overshoots: list[float] = []
    evaluator_departure_start: float | None = None
    evaluator_departure_peak: float | None = None
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
        action = controller.act(controller_observation)
        if mode_before is D003Mode.CHARGE and controller.mode is D003Mode.DEPART:
            departure_start_thermal_values.append(controller_observation.thermal)
            evaluator_departure_start = controller_observation.thermal
            evaluator_departure_peak = controller_observation.thermal
        action_counts[action.name] += 1
        if controller.mode is not mode_before:
            mode_entry_counts[controller.mode.name] += 1
            if mode_before is D003Mode.RETURN and controller.mode is D003Mode.CHARGE:
                completed_shuttle_cycles += 1

        observation, reward, terminated, truncated, info = environment.step(action)
        if reward != 0.0 or info != {}:
            raise RuntimeError("D-006 comparator reward or info crossed the boundary")
        next_controller_observation = _controller_observation(observation)
        evaluator_departure_start, evaluator_departure_peak = (
            _update_evaluator_departure_diagnostic(
                observation=next_controller_observation,
                departure_start=evaluator_departure_start,
                departure_peak=evaluator_departure_peak,
                observed_overshoots=observed_overshoots,
            )
        )

        telemetry = environment.last_transition
        if telemetry is None or environment.body is None:
            raise RuntimeError("D-006 comparator telemetry is unavailable")
        coefficient = environment._charging_heat_per_offered_energy(
            telemetry.step_index
        )
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
                D006TraceEntry(
                    transition_index=telemetry.step_index,
                    thermal_regime=(
                        "baseline"
                        if telemetry.step_index < D006_REGIME_CHANGE_TRANSITION
                        else "shifted"
                    ),
                    charging_heat_per_offered_energy=coefficient,
                    action=telemetry.action,
                    position=environment.body.position,
                    heading=environment.body.heading,
                    energy=telemetry.energy_after,
                    thermal=telemetry.thermal_after,
                    charging_contact=telemetry.charging_contact_after,
                    controller_mode=mode_before,
                    terminated=terminated,
                    truncated=truncated,
                    prediction_used=None,
                    prediction_after_consequence=None,
                    update_occurred=False,
                    observed_overshoot=None,
                )
            )

    result = _common_result(
        seed=seed,
        environment=environment,
        seeded_heading=seeded_heading,
        transitions=transitions,
        terminated=terminated,
        truncated=truncated,
        mode_occupancy=mode_occupancy,
        mode_entry_counts=mode_entry_counts,
        action_counts=action_counts,
        minimum_energy=minimum_energy,
        maximum_energy=maximum_energy,
        minimum_thermal_state=minimum_thermal_state,
        maximum_thermal_state=maximum_thermal_state,
        charging_contact_transitions=charging_contact_transitions,
        off_contact_transitions=off_contact_transitions,
        completed_shuttle_cycles=completed_shuttle_cycles,
    )
    result.update(
        {
            "condition": "D-003 thermostatic comparator",
            "initial_prediction": None,
            "final_prediction": None,
            "prediction_before_regime_change": None,
            "learning_update_count": 0,
            "learning_updates": [],
            "departure_start_thermal_values": departure_start_thermal_values,
            "evaluator_observed_departure_thermal_overshoots": observed_overshoots,
            "post_change_prediction_trajectory": [],
        }
    )
    if trace is not None:
        result["trace"] = tuple(trace)
    return result


def run_d006_probe(
    seeds: Sequence[int] = D006_DEFAULT_DEVELOPMENT_SEEDS,
    *,
    horizon: int = EXP003_HORIZON,
    collect_trace: bool = False,
) -> dict[str, object]:
    """Run matched D-006 predictive and D-003 comparator lifetimes."""
    development_seeds = validate_exp003_development_seeds(seeds)
    results: list[dict[str, object]] = []
    for seed in development_seeds:
        predictive_trace: list[D006TraceEntry] | None = [] if collect_trace else None
        comparator_trace: list[D006TraceEntry] | None = [] if collect_trace else None
        results.append(
            {
                "seed": seed,
                "predictive": _run_predictive_seed(
                    seed, horizon=horizon, trace=predictive_trace
                ),
                "comparator": _run_comparator_seed(
                    seed, horizon=horizon, trace=comparator_trace
                ),
            }
        )
    return {
        "development_seeds": list(development_seeds),
        "horizon": horizon,
        "organism_boundary": {"reward": 0.0, "info": {}},
        "thermal_regime_schedule": {
            "baseline_charging_heat_per_offered_energy": (
                D006_BASELINE_CHARGING_HEAT_PER_OFFERED_ENERGY
            ),
            "shifted_charging_heat_per_offered_energy": (
                D006_SHIFTED_CHARGING_HEAT_PER_OFFERED_ENERGY
            ),
            "baseline_through_transition": D006_REGIME_CHANGE_TRANSITION - 1,
            "shifted_beginning_transition": D006_REGIME_CHANGE_TRANSITION,
        },
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
        description="Run the D-006 within-lifetime thermal adaptation probe."
    )
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=list(D006_DEFAULT_DEVELOPMENT_SEEDS),
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
        help="Include full evaluator-only transition traces.",
    )
    return parser.parse_args()


def main() -> None:
    """Print the machine-readable D-006 development result."""
    args = _parse_args()
    print(
        json.dumps(
            run_d006_probe(
                tuple(args.seeds), horizon=args.horizon, collect_trace=args.trace
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
