"""D-007 matched common-probe history-divergence development probe.

D-007 runs two fresh D-005 controllers per development seed.  The histories
have identical evaluator setup and differ only in the fixed D-007 charging
heat coefficient.  After exactly seven D-005 consequence updates, the actual
controllers receive one identical typed observation at an evaluator-only
controller-level common probe.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Final, Literal, Sequence

from .d002 import D002_CHARGING_HEAT_PER_OFFERED_ENERGY, D002ThermalStationEnv
from .d003 import (
    COOL_RETURN_THRESHOLD,
    HOT_DEPART_THRESHOLD,
    RETURN_HALF_TURN_STEPS,
    D003Mode,
    D003ThermostaticObservation,
    _controller_observation,
    _prepare_post_contact_setup,
)
from .d005 import (
    D005_ALPHA,
    D005_INITIAL_PREDICTED_DEPARTURE_THERMAL_OVERSHOOT,
    PredictiveThermalOvershootController,
)
from .exp003 import EXP003_HORIZON, EXP003StationConfig
from .exp003_seed_policy import validate_exp003_development_seeds

D007_MILD_CHARGING_HEAT_PER_OFFERED_ENERGY: Final[float] = 0.04
D007_STRONG_CHARGING_HEAT_PER_OFFERED_ENERGY: Final[float] = 0.06
D007_TARGET_LEARNING_UPDATES: Final[int] = 7
D007_COMMON_PROBE_THERMAL: Final[float] = 0.56
D007_COMMON_PROBE_CHARGING_CONTACT: Final[bool] = True
D007_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = (18141, 18142, 18143)
HistoryCondition = Literal["mild", "strong"]

if D007_MILD_CHARGING_HEAT_PER_OFFERED_ENERGY != D002_CHARGING_HEAT_PER_OFFERED_ENERGY:
    raise RuntimeError("D-007 mild history must retain the D-002 coefficient")


class D007ThermalStationEnv(D002ThermalStationEnv):
    """D-002 thermal ecology with one fixed D-007 history coefficient."""

    def __init__(
        self,
        charging_heat_per_offered_energy: float,
        *,
        config: EXP003StationConfig | None = None,
    ) -> None:
        if not math.isfinite(charging_heat_per_offered_energy):
            raise ValueError("D-007 charging heat coefficient must be finite")
        if charging_heat_per_offered_energy not in (
            D007_MILD_CHARGING_HEAT_PER_OFFERED_ENERGY,
            D007_STRONG_CHARGING_HEAT_PER_OFFERED_ENERGY,
        ):
            raise ValueError("D-007 coefficient must be exactly 0.04 or 0.06")
        super().__init__(config=config)
        self._d007_charging_heat_per_offered_energy = (
            charging_heat_per_offered_energy
        )

    def _charging_heat_per_offered_energy(self, transition_index: int) -> float:
        """Return the fixed evaluator-side coefficient for this history."""
        del transition_index
        return self._d007_charging_heat_per_offered_energy


def _coefficient_for_condition(condition: HistoryCondition) -> float:
    if condition == "mild":
        return D007_MILD_CHARGING_HEAT_PER_OFFERED_ENERGY
    if condition == "strong":
        return D007_STRONG_CHARGING_HEAT_PER_OFFERED_ENERGY
    raise ValueError(f"unsupported D-007 history condition: {condition}")


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


def _validate_d007_development_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    """Validate the exact predeclared D-007 development seed set."""
    validated = validate_exp003_development_seeds(seeds)
    unexpected = tuple(
        seed for seed in validated if seed not in D007_DEFAULT_DEVELOPMENT_SEEDS
    )
    if unexpected:
        raise ValueError(
            "D-007 may execute only predeclared development seeds "
            f"{D007_DEFAULT_DEVELOPMENT_SEEDS}; got {unexpected}"
        )
    return validated


def _probe_ready(controller: PredictiveThermalOvershootController) -> bool:
    return (
        controller.mode is D003Mode.CHARGE
        and controller.turns_remaining == 0
        and controller.departure_start_thermal is None
        and controller.departure_peak_thermal is None
    )


def _run_history(
    seed: int,
    condition: HistoryCondition,
    *,
    horizon: int,
) -> dict[str, object]:
    coefficient = _coefficient_for_condition(condition)
    environment = D007ThermalStationEnv(
        coefficient, config=EXP003StationConfig(episode_horizon=horizon)
    )
    observation, info = environment.reset(seed=seed)
    if info != {}:
        raise RuntimeError("D-007 reset crossed the information boundary")
    seeded_heading, observation = _prepare_post_contact_setup(environment)

    controller = PredictiveThermalOvershootController()
    initial_prediction = controller.predicted_departure_thermal_overshoot
    learning_updates: list[dict[str, object]] = []
    transitions = 0
    terminated = False
    truncated = False

    while not (terminated or truncated):
        # The update count is evaluator stop logic only.  A ready CHARGE state
        # is checked before act(), so no post-target departure can begin.
        if len(learning_updates) == D007_TARGET_LEARNING_UPDATES and _probe_ready(
            controller
        ):
            break

        action = controller.act(_controller_observation(observation))
        observation, reward, terminated, truncated, info = environment.step(action)
        if reward != 0.0 or info != {}:
            raise RuntimeError("D-007 history crossed the reward/info boundary")

        next_controller_observation = _controller_observation(observation)
        update = controller.observe_consequence(next_controller_observation)
        telemetry = environment.last_transition
        if telemetry is None or environment.body is None:
            raise RuntimeError("D-007 history telemetry is unavailable")
        if update is not None:
            if len(learning_updates) >= D007_TARGET_LEARNING_UPDATES:
                raise RuntimeError("D-007 history exceeded the target update count")
            learning_updates.append(
                {
                    "transition_index": telemetry.step_index,
                    **update.as_dict(),
                }
            )
        transitions += 1

        # This permits the final RETURN action to enter CHARGE, then stops
        # before any new CHARGE departure decision is made.
        if len(learning_updates) == D007_TARGET_LEARNING_UPDATES and _probe_ready(
            controller
        ):
            break

    final = environment.last_transition
    if final is None or environment.body is None:
        raise RuntimeError("D-007 history ended without final evaluator state")

    ready = len(learning_updates) == D007_TARGET_LEARNING_UPDATES and _probe_ready(
        controller
    )
    termination_reason = (
        "probe_ready_after_target_updates"
        if ready
        else _termination_reason(
            terminated=terminated,
            truncated=truncated,
            energy=final.energy_termination,
            thermal=final.thermal_termination,
        )
    )
    history: dict[str, object] = {
        "condition": condition,
        "charging_heat_per_offered_energy": coefficient,
        "seeded_heading": seeded_heading,
        "initial_prediction": initial_prediction,
        "learning_update_count": len(learning_updates),
        "learning_updates": learning_updates,
        "transitions_to_probe_ready": transitions if ready else None,
        "probe_ready": ready,
        "mode": controller.mode.name,
        "turns_remaining": controller.turns_remaining,
        "departure_start_thermal": controller.departure_start_thermal,
        "departure_peak_thermal": controller.departure_peak_thermal,
        "learned_prediction": controller.predicted_departure_thermal_overshoot,
        "terminated": terminated,
        "truncated": truncated,
        "termination_reason": termination_reason,
        "evaluator_only_final_state": {
            "energy": environment.body.energy,
            "thermal": environment.thermal_state,
        },
        "controller_observe_consequence_calls": transitions,
    }

    if ready:
        common_observation = D003ThermostaticObservation(
            thermal=D007_COMMON_PROBE_THERMAL,
            charging_contact=D007_COMMON_PROBE_CHARGING_CONTACT,
        )
        probe_mode_before = controller.mode
        probe_action = controller.act(common_observation)
        history["common_probe"] = {
            "observation": {
                "thermal": common_observation.thermal,
                "charging_contact": common_observation.charging_contact,
            },
            "mode_before": probe_mode_before.name,
            "action": probe_action.name,
            "mode_after": controller.mode.name,
            "action_changed_mode": controller.mode is not probe_mode_before,
            "observe_consequence_called": False,
            "environment_transitions_between_observation_and_action": 0,
        }
    else:
        history["common_probe"] = None
    return history


def run_d007_probe(
    seeds: Sequence[int] = D007_DEFAULT_DEVELOPMENT_SEEDS,
    *,
    horizon: int = EXP003_HORIZON,
) -> dict[str, object]:
    """Run paired D-007 histories and their one-step common probes."""
    development_seeds = _validate_d007_development_seeds(seeds)
    results: list[dict[str, object]] = []
    for seed in development_seeds:
        mild_history = _run_history(seed, "mild", horizon=horizon)
        strong_history = _run_history(seed, "strong", horizon=horizon)
        mild_heading = mild_history["seeded_heading"]
        strong_heading = strong_history["seeded_heading"]
        if mild_heading != strong_heading:
            raise RuntimeError(
                "D-007 paired histories did not preserve matched heading"
            )
        results.append(
            {
                "seed": seed,
                "matched_setup": {
                    "initial_prediction": (
                        D005_INITIAL_PREDICTED_DEPARTURE_THERMAL_OVERSHOOT
                    ),
                    "initial_position": [0.5, 0.5],
                    "station_center": [0.5, 0.5],
                    "seeded_heading": mild_heading,
                    "controller_type": "PredictiveThermalOvershootController",
                    "controller_input_fields": [
                        "thermal_interoception",
                        "charging_contact",
                    ],
                },
                "histories": {
                    "mild": mild_history,
                    "strong": strong_history,
                },
            }
        )

    return {
        "schema_version": 1,
        "development_seeds": list(development_seeds),
        "horizon": horizon,
        "target_learning_updates": D007_TARGET_LEARNING_UPDATES,
        "common_probe_observation": {
            "thermal": D007_COMMON_PROBE_THERMAL,
            "charging_contact": D007_COMMON_PROBE_CHARGING_CONTACT,
        },
        "organism_boundary": {"reward": 0.0, "info": {}},
        "controller_type": "PredictiveThermalOvershootController",
        "controller_rng": False,
        "controller_input_fields": [
            "thermal_interoception",
            "charging_contact",
        ],
        "plastic_state": {
            "persistent_fields": ["predicted_departure_thermal_overshoot"],
            "dimension": 1,
            "initial_value": D005_INITIAL_PREDICTED_DEPARTURE_THERMAL_OVERSHOOT,
            "alpha": D005_ALPHA,
            "update_inputs": [
                "organism-visible thermal/contact consequence",
                "retained departure state",
                "current learned prediction",
            ],
        },
        "controller_constants": {
            "hot_depart_threshold": HOT_DEPART_THRESHOLD,
            "cool_return_threshold": COOL_RETURN_THRESHOLD,
            "return_half_turn_steps": RETURN_HALF_TURN_STEPS,
        },
        "history_conditions": {
            "mild": D007_MILD_CHARGING_HEAT_PER_OFFERED_ENERGY,
            "strong": D007_STRONG_CHARGING_HEAT_PER_OFFERED_ENERGY,
        },
        "results": results,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the D-007 matched common-probe history divergence probe."
    )
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=list(D007_DEFAULT_DEVELOPMENT_SEEDS),
        help="Legal development seeds only.",
    )
    parser.add_argument(
        "--horizon",
        type=int,
        default=EXP003_HORIZON,
        help="Finite development-probe horizon.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write the exact machine-readable result directly to this file.",
    )
    return parser.parse_args()


def main() -> None:
    """Run D-007 and print or directly write its compact result."""
    args = _parse_args()
    payload = json.dumps(
        run_d007_probe(tuple(args.seeds), horizon=args.horizon),
        indent=2,
        sort_keys=True,
    )
    if args.output is None:
        print(payload)
    else:
        args.output.write_text(payload + "\n", encoding="utf-8")
        print(f"D-007 result written to {args.output}")


if __name__ == "__main__":
    main()
