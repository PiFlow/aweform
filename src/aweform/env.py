"""Minimal Gymnasium environment for EXP-000."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from .body import Body, Coordinate
from .energy import EnergyConfig, advance_energy
from .resource import ResourceField
from .rng import RandomStreams
from .sensing import sample_directional_resources


class Action(IntEnum):
    """The complete V0.1 action set."""

    WAIT = 0
    TURN_LEFT = 1
    TURN_RIGHT = 2
    MOVE_FORWARD = 3


@dataclass(frozen=True, slots=True)
class TransitionTelemetry:
    """Evaluator-only quantities from one completed environment transition.

    This record is deliberately not returned by :meth:`AweformEnv.step`.
    Controllers continue to receive only the four-value observation and
    Gymnasium ``info`` remains empty.
    """

    step_index: int
    action: Action
    energy_before: float
    harvested_energy: float
    basal_cost: float
    action_cost: float
    energy_after: float
    terminated: bool
    truncated: bool


@dataclass(frozen=True, slots=True)
class AweformEnvConfig:
    """Configurable development parameters for :class:`AweformEnv`."""

    world_min: Coordinate = (0.0, 0.0)
    world_max: Coordinate = (1.0, 1.0)
    energy: EnergyConfig = field(
        default_factory=lambda: EnergyConfig(maximum_energy=10.0, basal_cost=0.1)
    )
    initial_energy: float = 5.0
    movement_distance: float = 0.05
    turn_angle: float = math.pi / 4.0
    wait_cost: float = 0.0
    turn_cost: float = 0.02
    movement_cost: float = 0.1
    probe_distance: float = 0.1
    sensor_angle: float = math.pi / 4.0
    harvest_rate: float = 0.5
    episode_horizon: int = 100
    resource_peak_intensity: float = 1.0
    resource_length_scale: float = 0.25

    def __post_init__(self) -> None:
        _validate_bounds(self.world_min, self.world_max)
        _require_finite("initial_energy", self.initial_energy)
        if not (
            self.energy.failure_boundary
            < self.initial_energy
            <= self.energy.maximum_energy
        ):
            raise ValueError(
                "initial_energy must be above failure_boundary and "
                "at most maximum_energy"
            )
        _require_non_negative("movement_distance", self.movement_distance)
        _require_non_negative("turn_angle", self.turn_angle)
        _require_non_negative("wait_cost", self.wait_cost)
        _require_non_negative("turn_cost", self.turn_cost)
        _require_non_negative("movement_cost", self.movement_cost)
        _require_non_negative("probe_distance", self.probe_distance)
        _require_non_negative("sensor_angle", self.sensor_angle)
        _require_non_negative("harvest_rate", self.harvest_rate)
        _require_non_negative("resource_peak_intensity", self.resource_peak_intensity)
        _require_finite("resource_length_scale", self.resource_length_scale)
        if self.resource_length_scale <= 0:
            raise ValueError("resource_length_scale must be positive")
        if (
            isinstance(self.episode_horizon, bool)
            or not isinstance(self.episode_horizon, int)
            or self.episode_horizon <= 0
        ):
            raise ValueError("episode_horizon must be a positive integer")


class AweformEnv(gym.Env[np.ndarray, int]):
    """Bounded body, local sensing, harvesting, and viability dynamics.

    Observations are four float32 values in ``[0, 1]``: normalised internal
    energy followed by normalised left, forward, and right resource signals.
    Simulator position, heading, and resource-source data remain hidden.
    """

    metadata: dict[str, Any] = {"render_modes": []}

    def __init__(self, config: AweformEnvConfig | None = None) -> None:
        self.config = config or AweformEnvConfig()
        self.action_space = spaces.Discrete(len(Action))
        self.observation_space = spaces.Box(
            low=np.zeros(4, dtype=np.float32),
            high=np.ones(4, dtype=np.float32),
            dtype=np.float32,
        )
        self.body: Body | None = None
        self.resource_field: ResourceField | None = None
        self.random_streams: RandomStreams | None = None
        self._step_count = 0
        self._episode_done = True
        self.last_transition: TransitionTelemetry | None = None

    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """Create a seeded resource field and body, then return its observation."""
        del options
        super().reset(seed=seed)
        environment_seed = (
            int(self.np_random.integers(0, np.iinfo(np.uint64).max, dtype=np.uint64))
            if seed is None
            else seed
        )
        self.random_streams = RandomStreams.from_seed(environment_seed)
        environment_rng = self.random_streams.environment
        self.resource_field = ResourceField.from_rng(
            environment_rng,
            world_min=self.config.world_min,
            world_max=self.config.world_max,
            peak_intensity=self.config.resource_peak_intensity,
            length_scale=self.config.resource_length_scale,
        )
        position = environment_rng.uniform(
            low=np.asarray(self.config.world_min, dtype=float),
            high=np.asarray(self.config.world_max, dtype=float),
        )
        self.body = Body(
            x=float(position[0]),
            y=float(position[1]),
            heading=float(environment_rng.uniform(0.0, math.tau)),
            energy=self.config.initial_energy,
        )
        self._step_count = 0
        self._episode_done = False
        self.last_transition = None
        return self._observation(), {}

    def step(self, action: int) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        """Apply one action and advance body energy and viability."""
        if self._episode_done:
            raise RuntimeError("episode is over; call reset() before step()")
        if not self.action_space.contains(action):
            raise ValueError(f"action must be one of {list(Action)}")
        if self.body is None or self.resource_field is None:
            raise RuntimeError("environment must be reset before step()")

        selected_action = Action(int(action))
        energy_before = self.body.energy
        if selected_action is Action.TURN_LEFT:
            self.body.turn(self.config.turn_angle)
            action_cost = self.config.turn_cost
        elif selected_action is Action.TURN_RIGHT:
            self.body.turn(-self.config.turn_angle)
            action_cost = self.config.turn_cost
        elif selected_action is Action.MOVE_FORWARD:
            self.body.move_forward(
                self.config.movement_distance,
                world_min=self.config.world_min,
                world_max=self.config.world_max,
            )
            action_cost = self.config.movement_cost
        else:
            action_cost = self.config.wait_cost

        harvested_energy = self.config.harvest_rate * self.resource_field.intensity(
            self.body.position
        )
        next_energy = advance_energy(
            self.body.energy,
            harvested_energy=harvested_energy,
            config=self.config.energy,
            action_cost=action_cost,
        )
        self.body.energy = next_energy.energy
        self._step_count += 1

        terminated = not next_energy.viable
        truncated = not terminated and self._step_count >= self.config.episode_horizon
        self._episode_done = terminated or truncated
        self.last_transition = TransitionTelemetry(
            step_index=self._step_count,
            action=selected_action,
            energy_before=energy_before,
            harvested_energy=harvested_energy,
            basal_cost=self.config.energy.basal_cost,
            action_cost=action_cost,
            energy_after=next_energy.energy,
            terminated=terminated,
            truncated=truncated,
        )
        return self._observation(), 0.0, terminated, truncated, {}

    def _observation(self) -> np.ndarray:
        if self.body is None or self.resource_field is None:
            raise RuntimeError("environment must be reset before observing")
        energy_range = (
            self.config.energy.maximum_energy - self.config.energy.failure_boundary
        )
        energy_signal = (
            self.body.energy - self.config.energy.failure_boundary
        ) / energy_range
        signals = sample_directional_resources(
            self.body,
            self.resource_field,
            probe_distance=self.config.probe_distance,
            sensor_angle=self.config.sensor_angle,
        )
        peak = self.resource_field.peak_intensity
        resource_signals = (
            (0.0, 0.0, 0.0)
            if peak == 0.0
            else tuple(signal / peak for signal in signals.as_tuple())
        )
        return np.asarray((energy_signal, *resource_signals), dtype=np.float32)


def _validate_bounds(world_min: Coordinate, world_max: Coordinate) -> None:
    _require_coordinate("world_min", world_min)
    _require_coordinate("world_max", world_max)
    if not all(lower < upper for lower, upper in zip(world_min, world_max)):
        raise ValueError("world_min must be strictly below world_max")


def _require_coordinate(name: str, coordinate: Coordinate) -> None:
    if len(coordinate) != 2 or not all(math.isfinite(value) for value in coordinate):
        raise ValueError(f"{name} must contain two finite coordinates")


def _require_finite(name: str, value: float) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


def _require_non_negative(name: str, value: float) -> None:
    _require_finite(name, value)
    if value < 0:
        raise ValueError(f"{name} must be non-negative")
