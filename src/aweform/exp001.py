"""Transparent development controllers for EXP-001.

This module is intentionally separate from the historical EXP-000 controller
and runner.  Its controller-facing observations make the EXP-001 information
boundary explicit: only B receives an interoceptive energy value.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

import numpy as np

from .env import Action
from .rng import RandomStreams


@dataclass(frozen=True, slots=True)
class ExternalObservation:
    """The complete controller-facing EXP-001 external observation."""

    left_resource: float
    forward_resource: float
    right_resource: float

    def __post_init__(self) -> None:
        for name in ("left_resource", "forward_resource", "right_resource"):
            _validate_normalized_value(name, getattr(self, name))

    def as_tuple(self) -> tuple[float, float, float]:
        """Return only the externally sensed resource signals."""
        return (self.left_resource, self.forward_resource, self.right_resource)


@dataclass(frozen=True, slots=True)
class InteroceptiveObservation:
    """B's observation: actual energy plus the same external observation."""

    energy: float
    external: ExternalObservation

    def __post_init__(self) -> None:
        _validate_normalized_value("energy", self.energy)
        if not isinstance(self.external, ExternalObservation):
            raise ValueError("external must be an ExternalObservation")


@dataclass(frozen=True, slots=True)
class EXP001DevelopmentConfig:
    """Unfrozen EXP-001 development parameters.

    Timer and contact values are required rather than defaulted so that a
    future protocol cannot accidentally inherit arbitrary scientific values.
    The B thresholds are inherited EXP-000 development values only.
    """

    resource_contact_threshold: float
    blind_explore_duration: int
    blind_charge_duration: int
    explorer_hazard: float = 1.0 / 8.0
    enter_seek: float = 0.35
    recover: float = 0.85

    def __post_init__(self) -> None:
        _validate_normalized_value(
            "resource_contact_threshold", self.resource_contact_threshold
        )
        _validate_probability("explorer_hazard", self.explorer_hazard)
        _validate_normalized_value("enter_seek", self.enter_seek)
        _validate_normalized_value("recover", self.recover)
        if not self.enter_seek < self.recover:
            raise ValueError("enter_seek must be less than recover")
        _validate_positive_int(
            "blind_explore_duration", self.blind_explore_duration
        )
        _validate_positive_int("blind_charge_duration", self.blind_charge_duration)


class EXP001Mode(Enum):
    """Modes used by the EXP-001 homeostatic controllers."""

    EXPLORE = "EXPLORE"
    SEEK_RESOURCE = "SEEK_RESOURCE"
    CHARGE = "CHARGE"


def policy_rng_from_seed(master_seed: int) -> np.random.Generator:
    """Return a fresh EXP-001 policy generator derived from ``master_seed``."""
    if isinstance(master_seed, bool) or not isinstance(master_seed, int):
        raise ValueError("master_seed must be an integer")
    return RandomStreams.from_seed(master_seed).policy


class StochasticPersistentExplorer:
    """Run-and-turn exploration driven by an independent policy generator.

    The primitive is only biologically inspired.  It is not a quantitative
    model of E. coli or any other organism.
    """

    def __init__(
        self,
        policy_rng: np.random.Generator,
        *,
        hazard: float = 1.0 / 8.0,
    ) -> None:
        _validate_probability("hazard", hazard)
        self.policy_rng = policy_rng
        self.hazard = hazard
        self._forward_actions_remaining = 0
        self._turn_action: Action | None = None
        self._turn_actions_remaining = 0

    def act(self, observation: ExternalObservation) -> Action:
        """Return the next exploration action; resource signals are ignored."""
        if not isinstance(observation, ExternalObservation):
            raise ValueError("observation must be an ExternalObservation")
        del observation

        if self._turn_actions_remaining > 0:
            if self._turn_action is None:
                raise RuntimeError("turn action state is incomplete")
            action = self._turn_action
            self._turn_actions_remaining -= 1
            if self._turn_actions_remaining == 0:
                self._turn_action = None
            return action

        if self._forward_actions_remaining == 0:
            self._forward_actions_remaining = self._sample_run_length()
        self._forward_actions_remaining -= 1
        if self._forward_actions_remaining == 0:
            self._prepare_reorientation()
        return Action.MOVE_FORWARD

    def begin_segment(self) -> None:
        """Start a new run segment without reseeding or advancing the RNG."""
        self._forward_actions_remaining = 0
        self._turn_action = None
        self._turn_actions_remaining = 0

    reset = begin_segment

    def _sample_run_length(self) -> int:
        run_length = int(self.policy_rng.geometric(self.hazard))
        if run_length < 1:
            raise RuntimeError("policy RNG returned an invalid run length")
        return run_length

    def _prepare_reorientation(self) -> None:
        direction = (
            Action.TURN_LEFT
            if self.policy_rng.random() < 0.5
            else Action.TURN_RIGHT
        )
        self._turn_action = direction
        self._turn_actions_remaining = 1 if self.policy_rng.random() < 0.5 else 2


def has_resource_contact(
    observation: ExternalObservation,
    threshold: float,
) -> bool:
    """Return contact using only external L/F/R sensing."""
    if not isinstance(observation, ExternalObservation):
        raise ValueError("observation must be an ExternalObservation")
    _validate_normalized_value("threshold", threshold)
    return max(observation.as_tuple()) >= threshold


def seek_resource_action(observation: ExternalObservation) -> Action:
    """Steer using local resource signals with the EXP-000 tie convention."""
    if not isinstance(observation, ExternalObservation):
        raise ValueError("observation must be an ExternalObservation")
    left, forward, right = observation.as_tuple()
    if left == forward == right:
        return Action.TURN_LEFT
    if forward >= left and forward >= right:
        return Action.MOVE_FORWARD
    if left > right:
        return Action.TURN_LEFT
    return Action.TURN_RIGHT


class EXP001AController:
    """Stochastic persistent exploration reference."""

    def __init__(
        self,
        policy_rng: np.random.Generator,
        config: EXP001DevelopmentConfig,
    ) -> None:
        self.explorer = StochasticPersistentExplorer(
            policy_rng,
            hazard=config.explorer_hazard,
        )

    @property
    def mode(self) -> EXP001Mode:
        return EXP001Mode.EXPLORE

    def act(self, observation: ExternalObservation) -> Action:
        return self.explorer.act(observation)

    def reset(self) -> None:
        self.explorer.begin_segment()


class EXP001BController:
    """Interoceptive closed-loop homeostasis."""

    def __init__(
        self,
        policy_rng: np.random.Generator,
        config: EXP001DevelopmentConfig,
    ) -> None:
        self.config = config
        self.explorer = StochasticPersistentExplorer(
            policy_rng,
            hazard=config.explorer_hazard,
        )
        self._mode = EXP001Mode.EXPLORE

    @property
    def mode(self) -> EXP001Mode:
        return self._mode

    def act(self, observation: InteroceptiveObservation) -> Action:
        if not isinstance(observation, InteroceptiveObservation):
            raise ValueError("observation must be an InteroceptiveObservation")

        if self._mode is EXP001Mode.EXPLORE:
            if observation.energy < self.config.enter_seek:
                self._mode = EXP001Mode.SEEK_RESOURCE
                return self._seek_or_charge(observation.external)
            return self.explorer.act(observation.external)

        if self._mode is EXP001Mode.SEEK_RESOURCE:
            return self._seek_or_charge(observation.external)

        if observation.energy > self.config.recover:
            self._mode = EXP001Mode.EXPLORE
            self.explorer.begin_segment()
            return self.explorer.act(observation.external)
        return Action.WAIT

    def reset(self) -> None:
        self._mode = EXP001Mode.EXPLORE
        self.explorer.begin_segment()

    def _seek_or_charge(self, observation: ExternalObservation) -> Action:
        if has_resource_contact(
            observation,
            self.config.resource_contact_threshold,
        ):
            self._mode = EXP001Mode.CHARGE
            return Action.WAIT
        return seek_resource_action(observation)


class EXP001CController:
    """Energy-blind open-loop homeostasis with external resource sensing."""

    def __init__(
        self,
        policy_rng: np.random.Generator,
        config: EXP001DevelopmentConfig,
    ) -> None:
        self.config = config
        self.explorer = StochasticPersistentExplorer(
            policy_rng,
            hazard=config.explorer_hazard,
        )
        self._mode = EXP001Mode.EXPLORE
        self._mode_actions = 0

    @property
    def mode(self) -> EXP001Mode:
        return self._mode

    @property
    def mode_actions(self) -> int:
        """Number of actions counted in the current timed mode."""
        return self._mode_actions

    def act(self, observation: ExternalObservation) -> Action:
        if not isinstance(observation, ExternalObservation):
            raise ValueError("observation must be an ExternalObservation")

        if self._mode is EXP001Mode.EXPLORE:
            if self._mode_actions >= self.config.blind_explore_duration:
                self._mode = EXP001Mode.SEEK_RESOURCE
                self._mode_actions = 0
                return self._seek_or_charge(observation)
            self._mode_actions += 1
            return self.explorer.act(observation)

        if self._mode is EXP001Mode.SEEK_RESOURCE:
            return self._seek_or_charge(observation)

        if self._mode_actions >= self.config.blind_charge_duration:
            self._mode = EXP001Mode.EXPLORE
            self.explorer.begin_segment()
            action = self.explorer.act(observation)
            self._mode_actions = 1
            return action
        self._mode_actions += 1
        return Action.WAIT

    def reset(self) -> None:
        self._mode = EXP001Mode.EXPLORE
        self._mode_actions = 0
        self.explorer.begin_segment()

    def _seek_or_charge(self, observation: ExternalObservation) -> Action:
        if has_resource_contact(
            observation,
            self.config.resource_contact_threshold,
        ):
            self._mode = EXP001Mode.CHARGE
            self._mode_actions = 1
            return Action.WAIT
        return seek_resource_action(observation)


def _validate_normalized_value(name: str, value: float) -> float:
    try:
        is_finite = math.isfinite(value)
    except TypeError as error:
        raise ValueError(f"{name} must be finite") from error
    if not is_finite or not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be finite and within [0, 1]")
    return value


def _validate_probability(name: str, value: float) -> float:
    _validate_normalized_value(name, value)
    if value == 0.0:
        raise ValueError(f"{name} must be greater than zero")
    return value


def _validate_positive_int(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
