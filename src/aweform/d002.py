"""D-002 minimal thermal ecology, composed around EXP-003.

This development-only module adds one thermal viability state to
``LocalizedChargingStationEnv`` without changing the historical EXP-003
environment.  The wrapped environment remains authoritative for movement,
contact, offered charging input, energy accounting, actions, and horizon.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Final, Sequence

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from .body import Body, Coordinate
from .env import Action
from .exp003 import (
    EXP003_HORIZON,
    EXP003StationConfig,
    LocalizedChargingStationEnv,
)
from .exp003_seed_policy import validate_exp003_development_seeds

D002_AMBIENT_THERMAL_STATE: Final[float] = 0.0
D002_INITIAL_THERMAL_STATE: Final[float] = 0.20
D002_UPPER_THERMAL_FAILURE_BOUNDARY: Final[float] = 1.0
D002_CHARGING_HEAT_PER_OFFERED_ENERGY: Final[float] = 0.04
D002_PASSIVE_COOLING_PER_TRANSITION: Final[float] = 0.01
D002_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = (18141, 18142, 18143)


@dataclass(frozen=True, slots=True)
class D002TransitionTelemetry:
    """Evaluator-only telemetry for one D-002 transition."""

    step_index: int
    action: Action
    energy_before: float
    energy_after: float
    stored_energy_delta: float
    action_cost: float
    offered_station_input: float
    thermal_before: float
    thermal_after: float
    thermal_input: float
    passive_cooling: float
    charging_contact_before: bool
    charging_contact_after: bool
    energy_termination: bool
    thermal_termination: bool
    terminated: bool
    truncated: bool

    def as_dict(self) -> dict[str, object]:
        """Return JSON-compatible evaluator telemetry."""
        return {
            "step_index": self.step_index,
            "action": self.action.name,
            "energy_before": self.energy_before,
            "energy_after": self.energy_after,
            "stored_energy_delta": self.stored_energy_delta,
            "offered_station_input": self.offered_station_input,
            "thermal_before": self.thermal_before,
            "thermal_after": self.thermal_after,
            "thermal_input": self.thermal_input,
            "passive_cooling": self.passive_cooling,
            "charging_contact_before": self.charging_contact_before,
            "charging_contact_after": self.charging_contact_after,
            "energy_termination": self.energy_termination,
            "thermal_termination": self.thermal_termination,
            "terminated": self.terminated,
            "truncated": self.truncated,
        }


class D002ThermalStationEnv(gym.Env[np.ndarray, int]):
    """EXP-003 station ecology with one additive thermal viability state."""

    metadata: dict[str, object] = {"render_modes": []}

    def __init__(
        self,
        environment: LocalizedChargingStationEnv | None = None,
        *,
        config: EXP003StationConfig | None = None,
    ) -> None:
        if environment is not None and config is not None:
            raise ValueError("provide either environment or config, not both")
        self.base_env = environment or LocalizedChargingStationEnv(config)
        self.action_space = self.base_env.action_space
        self.observation_space = spaces.Box(
            low=np.zeros(6, dtype=np.float32),
            high=np.ones(6, dtype=np.float32),
            dtype=np.float32,
        )
        self.thermal_state = D002_AMBIENT_THERMAL_STATE
        self._episode_done = True
        self.last_transition: D002TransitionTelemetry | None = None

    @property
    def config(self) -> EXP003StationConfig:
        """Return the unchanged wrapped EXP-003 configuration."""
        return self.base_env.config

    @property
    def body(self) -> Body | None:
        """Return evaluator-side body state for development harnesses."""
        return self.base_env.body

    @property
    def station_center(self) -> Coordinate | None:
        """Return evaluator-side station state for development harnesses."""
        return self.base_env.station_center

    def evaluator_set_geometry_and_observe(
        self,
        *,
        body_position: Coordinate,
        station_center: Coordinate,
        heading: float | None = None,
    ) -> np.ndarray:
        """Set evaluator geometry and return the current six-channel observation.

        This is an evaluator-only development-harness seam. It changes no
        organism state other than the deliberately positioned geometry, does
        not execute a transition, and does not reset or reseed either
        environment state. The wrapped EXP-003 observation implementation is
        intentionally encapsulated here so runners do not reach through its
        private methods.
        """
        body = self.body
        if body is None or self.station_center is None:
            raise RuntimeError("D-002 environment must be reset before setup")
        body.x, body.y = body_position
        if heading is not None:
            body.heading = heading
        self.base_env.station_center = station_center
        return self._with_thermal_signal(self.base_env._observation())

    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict[str, object] | None = None,
    ) -> tuple[np.ndarray, dict[str, object]]:
        """Reset EXP-003 and initialize D-002 thermal state."""
        observation, info = self.base_env.reset(seed=seed, options=options)
        self.thermal_state = D002_INITIAL_THERMAL_STATE
        self._episode_done = False
        self.last_transition = None
        return self._with_thermal_signal(observation), info

    def step(
        self, action: int
    ) -> tuple[np.ndarray, float, bool, bool, dict[str, object]]:
        """Apply EXP-003 first, then update thermal state and viability."""
        if self._episode_done:
            raise RuntimeError("episode is over; call reset() before step()")

        observation, reward, energy_terminated, base_truncated, info = (
            self.base_env.step(action)
        )
        base_transition = self.base_env.last_transition
        if base_transition is None:
            raise RuntimeError("EXP-003 transition telemetry is unavailable")
        if info != {}:
            raise RuntimeError("D-002 base environment crossed the info boundary")
        if reward != 0.0:
            raise RuntimeError("D-002 reward must remain exactly 0.0")

        thermal_before = self.thermal_state
        thermal_input = (
            D002_CHARGING_HEAT_PER_OFFERED_ENERGY * base_transition.harvested_energy
        )
        thermal_raw = (
            thermal_before + thermal_input - D002_PASSIVE_COOLING_PER_TRANSITION
        )
        self.thermal_state = min(
            D002_UPPER_THERMAL_FAILURE_BOUNDARY,
            max(D002_AMBIENT_THERMAL_STATE, thermal_raw),
        )
        thermal_terminated = thermal_raw >= D002_UPPER_THERMAL_FAILURE_BOUNDARY
        terminated = energy_terminated or thermal_terminated
        truncated = base_truncated and not terminated
        self._episode_done = terminated or truncated
        self.last_transition = D002TransitionTelemetry(
            step_index=base_transition.step_index,
            action=base_transition.action,
            energy_before=base_transition.energy_before,
            energy_after=base_transition.energy_after,
            stored_energy_delta=(
                base_transition.energy_after - base_transition.energy_before
            ),
            action_cost=base_transition.action_cost,
            offered_station_input=base_transition.harvested_energy,
            thermal_before=thermal_before,
            thermal_after=self.thermal_state,
            thermal_input=thermal_input,
            passive_cooling=D002_PASSIVE_COOLING_PER_TRANSITION,
            charging_contact_before=base_transition.charging_contact_before,
            charging_contact_after=base_transition.charging_contact_after,
            energy_termination=energy_terminated,
            thermal_termination=thermal_terminated,
            terminated=terminated,
            truncated=truncated,
        )
        return self._with_thermal_signal(observation), 0.0, terminated, truncated, {}

    def _with_thermal_signal(self, observation: np.ndarray) -> np.ndarray:
        if observation.shape != (5,):
            raise RuntimeError("EXP-003 observation must contain five values")
        thermal_signal = (self.thermal_state - D002_AMBIENT_THERMAL_STATE) / (
            D002_UPPER_THERMAL_FAILURE_BOUNDARY - D002_AMBIENT_THERMAL_STATE
        )
        result = np.empty(6, dtype=np.float32)
        result[:5] = observation
        result[5] = thermal_signal
        return result


def _prepare_body_and_station(
    environment: D002ThermalStationEnv,
    *,
    body_position: Coordinate,
    station_center: Coordinate,
    heading: float = 0.0,
) -> None:
    """Apply evaluator-only fixed geometry for a development probe."""
    body = environment.body
    if body is None:
        raise RuntimeError("D-002 probe body is unavailable")
    if environment.base_env.station_center is None:
        raise RuntimeError("D-002 probe station is unavailable")
    body.x, body.y = body_position
    body.heading = heading
    environment.base_env.station_center = station_center


def _run_fixed_schedule(
    seed: int,
    actions: Sequence[Action],
    *,
    setup: str,
    prepare: tuple[Coordinate, Coordinate, float],
    horizon: int = EXP003_HORIZON,
) -> dict[str, object]:
    config = EXP003StationConfig(episode_horizon=horizon)
    environment = D002ThermalStationEnv(config=config)
    observation, info = environment.reset(seed=seed)
    if info != {}:
        raise RuntimeError("D-002 reset crossed the info boundary")
    _prepare_body_and_station(
        environment,
        body_position=prepare[0],
        station_center=prepare[1],
        heading=prepare[2],
    )
    transitions = 0
    minimum_energy = float(observation[0] * config.energy.maximum_energy)
    maximum_thermal = float(observation[5])
    contact_transitions = 0
    action_index = 0
    terminated = False
    truncated = False
    while not (terminated or truncated):
        action = actions[action_index % len(actions)]
        action_index += 1
        observation, reward, terminated, truncated, info = environment.step(action)
        if reward != 0.0 or info != {}:
            raise RuntimeError("D-002 probe crossed the observation/reward boundary")
        telemetry = environment.last_transition
        if telemetry is None:
            raise RuntimeError("D-002 probe telemetry is unavailable")
        transitions += 1
        minimum_energy = min(minimum_energy, telemetry.energy_after)
        maximum_thermal = max(maximum_thermal, telemetry.thermal_after)
        contact_transitions += int(telemetry.charging_contact_after)

    if environment.body is None or environment.last_transition is None:
        raise RuntimeError("D-002 probe ended without final state")
    final = environment.last_transition
    return {
        "seed": seed,
        "setup": setup,
        "transitions": transitions,
        "initial_energy": config.initial_energy,
        "final_energy": environment.body.energy,
        "minimum_energy": minimum_energy,
        "final_thermal_state": environment.thermal_state,
        "maximum_thermal_state": maximum_thermal,
        "contact_transitions": contact_transitions,
        "energy_termination": final.energy_termination,
        "thermal_termination": final.thermal_termination,
        "terminated": terminated,
        "truncated": truncated,
    }


def run_d002_probes(
    seeds: Sequence[int] = D002_DEFAULT_DEVELOPMENT_SEEDS,
    *,
    horizon: int = EXP003_HORIZON,
) -> dict[str, object]:
    """Run deterministic ecology sanity probes on legal development seeds."""
    development_seeds = validate_exp003_development_seeds(seeds)
    alternating_schedule = (
        Action.WAIT,
        Action.WAIT,
        Action.WAIT,
        Action.MOVE_FORWARD,
        Action.MOVE_FORWARD,
        Action.MOVE_FORWARD,
        Action.MOVE_FORWARD,
        Action.TURN_LEFT,
        Action.TURN_LEFT,
        Action.TURN_LEFT,
        Action.TURN_LEFT,
        Action.WAIT,
        Action.WAIT,
        Action.WAIT,
        Action.MOVE_FORWARD,
        Action.MOVE_FORWARD,
        Action.MOVE_FORWARD,
        Action.MOVE_FORWARD,
    )
    results = {
        "permanent_dock_wait": [
            _run_fixed_schedule(
                seed,
                (Action.WAIT,),
                setup="body placed at station center; constant WAIT",
                prepare=((0.5, 0.5), (0.5, 0.5), 0.0),
                horizon=horizon,
            )
            for seed in development_seeds
        ],
        "permanent_off_dock_wait": [
            _run_fixed_schedule(
                seed,
                (Action.WAIT,),
                setup="body and station placed outside charging contact; constant WAIT",
                prepare=((0.8, 0.8), (0.2, 0.2), 0.0),
                horizon=horizon,
            )
            for seed in development_seeds
        ],
        "alternating_open_loop_witness": {
            "schedule": [action.name for action in alternating_schedule],
            "schedule_description": (
                "WAIT x3, MOVE_FORWARD x4, TURN_LEFT x4, WAIT x3, "
                "MOVE_FORWARD x4, repeated"
            ),
            "results": [
                _run_fixed_schedule(
                    seed,
                    alternating_schedule,
                    setup=(
                        "body and station centered; heading 0; open-loop physical "
                        "schedule"
                    ),
                    prepare=((0.5, 0.5), (0.5, 0.5), 0.0),
                    horizon=horizon,
                )
                for seed in development_seeds
            ],
        },
    }
    return {
        "development_seeds": list(development_seeds),
        "horizon": horizon,
        "thermal_constants": {
            "ambient_thermal_state": D002_AMBIENT_THERMAL_STATE,
            "initial_thermal_state": D002_INITIAL_THERMAL_STATE,
            "upper_thermal_failure_boundary": D002_UPPER_THERMAL_FAILURE_BOUNDARY,
            "charging_heat_per_offered_energy": D002_CHARGING_HEAT_PER_OFFERED_ENERGY,
            "passive_cooling_per_transition": D002_PASSIVE_COOLING_PER_TRANSITION,
        },
        "coherence_requirements": [
            "permanent charging contact must eventually fail thermally",
            "permanent non-contact must eventually fail energetically",
            (
                "a physically realizable alternating contact/off-contact schedule "
                "must be viable in principle"
            ),
        ],
        "probes": results,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the D-002 minimal thermal ecology sanity probes."
    )
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=list(D002_DEFAULT_DEVELOPMENT_SEEDS),
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
    """Print the machine-readable D-002 development record."""
    args = _parse_args()
    print(
        json.dumps(
            run_d002_probes(args.seeds, horizon=args.horizon), indent=2, sort_keys=True
        )
    )


if __name__ == "__main__":
    main()
