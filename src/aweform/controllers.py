"""Transparent programmed controllers for the EXP-000 conditions."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Sequence

import numpy as np

from .env import Action

Observation = tuple[float, float, float, float]


class ControllerMode(Enum):
    """Modes used by the shared homeostatic decision mechanism."""

    EXPLORE = "EXPLORE"
    SEEK_RESOURCE = "SEEK_RESOURCE"


@dataclass(frozen=True, slots=True)
class HomeostaticConfig:
    """Development parameters for the shared homeostatic controller core."""

    enter_seek: float = 0.35
    recover: float = 0.85
    exploration_steps: int = 8

    def __post_init__(self) -> None:
        _validate_normalized_value("enter_seek", self.enter_seek)
        _validate_normalized_value("recover", self.recover)
        if not self.enter_seek < self.recover:
            raise ValueError("enter_seek must be less than recover")
        _validate_positive_int("exploration_steps", self.exploration_steps)


class PersistentExplorationController:
    """Deterministic forward-then-left persistent exploration."""

    def __init__(self, exploration_steps: int = 8) -> None:
        _validate_positive_int("exploration_steps", exploration_steps)
        self.exploration_steps = exploration_steps
        self._phase = 0

    def act(self, observation: Sequence[float]) -> Action:
        """Return the next action after validating the normal observation."""
        validated_observation = _validate_observation(observation)
        return self._act_validated(validated_observation)

    def reset(self) -> None:
        """Return the repeating exploration pattern to its initial phase."""
        self._phase = 0

    def _act_validated(self, observation: Observation) -> Action:
        del observation
        if self._phase < self.exploration_steps:
            action = Action.MOVE_FORWARD
        else:
            action = Action.TURN_LEFT
        self._phase = (self._phase + 1) % (self.exploration_steps + 1)
        return action


class _HomeostaticDecisionCore:
    """Shared mode switching, exploration, and local resource steering."""

    def __init__(self, config: HomeostaticConfig) -> None:
        self.config = config
        self._exploration = PersistentExplorationController(
            exploration_steps=config.exploration_steps
        )
        self._mode = ControllerMode.EXPLORE

    @property
    def mode(self) -> ControllerMode:
        return self._mode

    def act(self, observation: Observation, energy_signal: float) -> Action:
        """Apply the shared homeostatic decision structure."""
        if self._mode is ControllerMode.EXPLORE:
            if energy_signal < self.config.enter_seek:
                self._mode = ControllerMode.SEEK_RESOURCE
        elif energy_signal > self.config.recover:
            self._mode = ControllerMode.EXPLORE
            self._exploration.reset()

        if self._mode is ControllerMode.EXPLORE:
            return self._exploration._act_validated(observation)
        return _seek_resource_action(observation)

    def reset(self) -> None:
        """Reset both the mode and the persistent exploration phase."""
        self._mode = ControllerMode.EXPLORE
        self._exploration.reset()


class HomeostaticController:
    """Programmed controller with informative current-energy interoception."""

    def __init__(self, config: HomeostaticConfig | None = None) -> None:
        self._core = _HomeostaticDecisionCore(config or HomeostaticConfig())

    @property
    def mode(self) -> ControllerMode:
        """Current shared homeostatic mode."""
        return self._core.mode

    def act(self, observation: Sequence[float]) -> Action:
        """Use the actual normalized energy in the four-value observation."""
        validated_observation = _validate_observation(observation)
        return self._core.act(validated_observation, validated_observation[0])

    def reset(self) -> None:
        """Reset mode and exploration state."""
        self._core.reset()


class EnergyBlindController:
    """Homeostatic controller with a fixed, explicitly configured energy mask."""

    def __init__(
        self,
        masked_energy: float,
        config: HomeostaticConfig | None = None,
    ) -> None:
        self.masked_energy = _validate_normalized_value("masked_energy", masked_energy)
        self._core = _HomeostaticDecisionCore(config or HomeostaticConfig())

    @property
    def mode(self) -> ControllerMode:
        """Current shared homeostatic mode."""
        return self._core.mode

    def act(self, observation: Sequence[float]) -> Action:
        """Ignore observation energy and use the configured fixed mask instead."""
        validated_observation = _validate_observation(observation)
        return self._core.act(validated_observation, self.masked_energy)

    def reset(self) -> None:
        """Reset mode and exploration state."""
        self._core.reset()


def _seek_resource_action(observation: Observation) -> Action:
    """Steer using local signals; all-equal readings turn left to resample."""
    left_resource, forward_resource, right_resource = observation[1:]
    if left_resource == forward_resource == right_resource:
        return Action.TURN_LEFT
    if forward_resource >= left_resource and forward_resource >= right_resource:
        return Action.MOVE_FORWARD
    if left_resource > right_resource:
        return Action.TURN_LEFT
    return Action.TURN_RIGHT


def _validate_observation(observation: Sequence[float]) -> Observation:
    try:
        values = np.asarray(observation, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise ValueError("observation must contain four finite values") from error
    if values.shape != (4,):
        raise ValueError("observation must have shape (4,)")
    if not np.all(np.isfinite(values)):
        raise ValueError("observation values must be finite")
    if np.any((values < 0.0) | (values > 1.0)):
        raise ValueError("observation values must be within [0, 1]")
    return (
        float(values[0]),
        float(values[1]),
        float(values[2]),
        float(values[3]),
    )


def _validate_normalized_value(name: str, value: float) -> float:
    try:
        is_finite = math.isfinite(value)
    except TypeError as error:
        raise ValueError(f"{name} must be finite") from error
    if not is_finite or not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be finite and within [0, 1]")
    return value


def _validate_positive_int(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
