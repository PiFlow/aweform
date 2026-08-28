"""D-003 fixed non-learning thermostatic shuttle development probe."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from enum import Enum
from typing import Final

import numpy as np

from .body import Coordinate
from .d002 import D002ThermalStationEnv
from .env import Action
from .exp003 import EXP003_HORIZON, EXP003StationConfig
from .exp003_seed_policy import validate_exp003_development_seeds

HOT_DEPART_THRESHOLD: Final[float] = 0.60
COOL_RETURN_THRESHOLD: Final[float] = 0.30
RETURN_HALF_TURN_STEPS: Final[int] = 4
D003_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = (18141, 18142, 18143)


class D003Mode(Enum):
    """Fixed phases of the D-003 thermostatic shuttle."""

    CHARGE = "CHARGE"
    DEPART = "DEPART"
    COOL = "COOL"
    TURN_RETURN = "TURN_RETURN"
    RETURN = "RETURN"


@dataclass(frozen=True, slots=True)
class D003ThermostaticObservation:
    """The complete observation accepted by the D-003 controller."""

    thermal: float
    charging_contact: bool

    def __post_init__(self) -> None:
        if not math.isfinite(self.thermal) or not 0.0 <= self.thermal <= 1.0:
            raise ValueError("thermal must be finite and between 0.0 and 1.0")
        if not isinstance(self.charging_contact, bool):
            raise ValueError("charging_contact must be a bool")


class ThermostaticShuttleController:
    """Deterministic fixed feedback controller for post-contact regulation."""

    def __init__(self) -> None:
        self.mode = D003Mode.CHARGE
        self.turns_remaining = 0

    def reset(self) -> None:
        """Start a deliberate new lifetime with no retained phase state."""
        self.mode = D003Mode.CHARGE
        self.turns_remaining = 0

    def act(self, observation: D003ThermostaticObservation) -> Action:
        """Choose one action from the narrow D-003 observation."""
        if not isinstance(observation, D003ThermostaticObservation):
            raise ValueError("observation must be a D003ThermostaticObservation")

        if self.mode is D003Mode.CHARGE:
            if observation.thermal < HOT_DEPART_THRESHOLD:
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
                return Action.WAIT
            return Action.MOVE_FORWARD

        raise RuntimeError(f"unsupported controller mode: {self.mode}")


def _controller_observation(observation: np.ndarray) -> D003ThermostaticObservation:
    """Project one D-002 observation into the D-003 information boundary."""
    if observation.shape != (6,):
        raise ValueError("D-002 observation must contain six values")
    charging_contact_signal = float(observation[4])
    if charging_contact_signal not in (0.0, 1.0):
        raise ValueError("D-002 charging contact channel must be binary")
    return D003ThermostaticObservation(
        thermal=float(observation[5]),
        charging_contact=bool(charging_contact_signal),
    )


def _prepare_post_contact_setup(
    environment: D002ThermalStationEnv,
    *,
    position: Coordinate = (0.5, 0.5),
    station_center: Coordinate = (0.5, 0.5),
) -> float:
    """Place body and station for the probe while preserving seeded heading."""
    body = environment.body
    if body is None or environment.station_center is None:
        raise RuntimeError("D-002 environment must be reset before setup")
    seeded_heading = body.heading
    body.x, body.y = position
    environment.base_env.station_center = station_center
    return seeded_heading


def _refresh_observation(environment: D002ThermalStationEnv) -> np.ndarray:
    """Read the positioned D-002 state without exposing it to the controller."""
    return environment._with_thermal_signal(environment.base_env._observation())


def _mode_counts() -> dict[str, int]:
    return {mode.name: 0 for mode in D003Mode}


def _run_seed(seed: int, *, horizon: int) -> dict[str, object]:
    config = EXP003StationConfig(episode_horizon=horizon)
    environment = D002ThermalStationEnv(config=config)
    observation, info = environment.reset(seed=seed)
    if info != {}:
        raise RuntimeError("D-002 reset crossed the information boundary")
    seeded_heading = _prepare_post_contact_setup(environment)
    observation = _refresh_observation(environment)

    controller = ThermostaticShuttleController()
    controller.reset()
    mode_occupancy = _mode_counts()
    mode_entry_counts = _mode_counts()
    mode_entry_counts[controller.mode.name] = 1
    action_counts = {action.name: 0 for action in Action}
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
        action_counts[action.name] += 1
        if controller.mode is not mode_before:
            mode_entry_counts[controller.mode.name] += 1
            if mode_before is D003Mode.RETURN and controller.mode is D003Mode.CHARGE:
                completed_shuttle_cycles += 1

        observation, reward, terminated, truncated, info = environment.step(action)
        if reward != 0.0 or info != {}:
            raise RuntimeError("D-002 reward or info crossed the boundary")
        telemetry = environment.last_transition
        if telemetry is None or environment.body is None:
            raise RuntimeError("D-003 transition telemetry is unavailable")
        transitions += 1
        minimum_energy = min(minimum_energy, telemetry.energy_after)
        maximum_energy = max(maximum_energy, telemetry.energy_after)
        minimum_thermal_state = min(minimum_thermal_state, telemetry.thermal_after)
        maximum_thermal_state = max(maximum_thermal_state, telemetry.thermal_after)
        if telemetry.charging_contact_after:
            charging_contact_transitions += 1
        else:
            off_contact_transitions += 1

    if environment.last_transition is None or environment.body is None:
        raise RuntimeError("D-003 run ended without final telemetry")
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
        "controller_input_fields": ["thermal_interoception", "charging_contact"],
    }


def run_d003_probe(
    seeds: tuple[int, ...] = D003_DEFAULT_DEVELOPMENT_SEEDS,
    *,
    horizon: int = EXP003_HORIZON,
) -> dict[str, object]:
    """Run the single descriptive D-003 probe on legal development seeds."""
    development_seeds = validate_exp003_development_seeds(seeds)
    return {
        "development_seeds": list(development_seeds),
        "horizon": horizon,
        "controller_constants": {
            "hot_depart_threshold": HOT_DEPART_THRESHOLD,
            "cool_return_threshold": COOL_RETURN_THRESHOLD,
            "return_half_turn_steps": RETURN_HALF_TURN_STEPS,
        },
        "controller_input_fields": [
            "thermal_interoception",
            "charging_contact",
        ],
        "cycle_definition": (
            "return to CHARGE after completing DEPART -> COOL -> TURN_RETURN -> RETURN"
        ),
        "results": [_run_seed(seed, horizon=horizon) for seed in development_seeds],
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the D-003 fixed thermostatic shuttle probe."
    )
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=list(D003_DEFAULT_DEVELOPMENT_SEEDS),
        help="Legal development seeds only.",
    )
    parser.add_argument(
        "--horizon",
        type=int,
        default=EXP003_HORIZON,
        help="Finite development-probe horizon.",
    )
    return parser.parse_args()


def main() -> None:
    """Print the machine-readable D-003 development result."""
    args = _parse_args()
    print(json.dumps(run_d003_probe(tuple(args.seeds), horizon=args.horizon), indent=2))


if __name__ == "__main__":
    main()
