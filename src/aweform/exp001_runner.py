"""Development-only matched execution for EXP-001.

The generic environment exposes four values, but those values are not the
EXP-001 controller contract.  This module owns the only transformation from
the simulator observation to the typed A/B/C controller observations.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from numbers import Integral
from typing import Sequence

import numpy as np

from .env import Action, AweformEnv, AweformEnvConfig, TransitionTelemetry
from .exp001 import (
    EXP001AController,
    EXP001BController,
    EXP001CController,
    EXP001DevelopmentConfig,
    EXP001Mode,
    ExternalObservation,
    InteroceptiveObservation,
    policy_rng_from_seed,
)


class EXP001Condition(Enum):
    """The matched development conditions in execution order."""

    A = "A_PERSISTENT_EXPLORATION"
    B = "B_INTEROCEPTIVE_HOMEOSTASIS"
    C = "C_ENERGY_BLIND_HOMEOSTASIS"


ControllerObservation = ExternalObservation | InteroceptiveObservation
EXP001Controller = EXP001AController | EXP001BController | EXP001CController


@dataclass(frozen=True, slots=True)
class EXP001EvaluatorInitialState:
    """Privileged simulator state captured before the first action."""

    position: tuple[float, float]
    heading: float
    actual_energy: float
    source_positions: tuple[tuple[float, float], ...]


@dataclass(frozen=True, slots=True)
class EXP001ControllerStep:
    """The observation actually handed to one controller."""

    observation: ControllerObservation


@dataclass(frozen=True, slots=True)
class EXP001EvaluatorStep:
    """Privileged evaluator telemetry for one completed transition."""

    step_index: int
    action: Action
    position: tuple[float, float]
    heading: float
    actual_energy: float
    harvested_energy: float
    basal_cost: float
    action_cost: float
    energy_before: float
    energy_after: float
    terminated: bool
    truncated: bool
    controller_mode: EXP001Mode


@dataclass(frozen=True, slots=True)
class EXP001TransitionRecord:
    """One action with controller-visible and evaluator-only sides separated."""

    controller_visible: EXP001ControllerStep
    privileged_evaluator: EXP001EvaluatorStep


@dataclass(frozen=True, slots=True)
class EXP001EpisodeRecord:
    """Initial evaluator state and the raw matched trajectory."""

    condition: EXP001Condition
    environment_seed: int
    initial_state: EXP001EvaluatorInitialState
    transitions: tuple[EXP001TransitionRecord, ...]


@dataclass(frozen=True, slots=True)
class EXP001DevelopmentBatchResult:
    """Deterministic development output without scientific summaries."""

    environment_config: AweformEnvConfig
    development_config: EXP001DevelopmentConfig
    environment_seeds: tuple[int, ...]
    episodes: tuple[EXP001EpisodeRecord, ...]


def exp001_controller_observation(
    condition: EXP001Condition,
    raw_observation: object,
) -> ControllerObservation:
    """Adapt one generic four-value environment observation at the boundary.

    The raw observation is validated and consumed here.  A and C receive a
    new :class:`ExternalObservation`; only B receives the actual normalized
    energy value as an :class:`InteroceptiveObservation`.
    """

    if not isinstance(condition, EXP001Condition):
        raise ValueError("condition must be an EXP001Condition")
    energy, left, forward, right = _validate_raw_observation(raw_observation)
    external = ExternalObservation(
        left_resource=left,
        forward_resource=forward,
        right_resource=right,
    )
    if condition is EXP001Condition.B:
        return InteroceptiveObservation(energy=energy, external=external)
    return external


def run_exp001_development_batch(
    seeds: Sequence[int],
    env_config: AweformEnvConfig,
    development_config: EXP001DevelopmentConfig,
) -> EXP001DevelopmentBatchResult:
    """Execute fresh, matched A/B/C development episodes for each seed.

    This is an execution instrument only.  It has no acceptance seed set,
    inferential analysis, or scientific decision rule.
    """

    validated_seeds = _validate_seeds(seeds)
    _validate_exp001_inputs(env_config, development_config)

    episodes: list[EXP001EpisodeRecord] = []
    for seed in validated_seeds:
        for condition in EXP001Condition:
            episodes.append(
                _run_episode(
                    condition=condition,
                    environment_seed=seed,
                    env_config=env_config,
                    development_config=development_config,
                )
            )
    return EXP001DevelopmentBatchResult(
        environment_config=env_config,
        development_config=development_config,
        environment_seeds=validated_seeds,
        episodes=tuple(episodes),
    )


def run_exp001_c_episode(
    environment_seed: int,
    env_config: AweformEnvConfig,
    development_config: EXP001DevelopmentConfig,
) -> EXP001EpisodeRecord:
    """Execute exactly one fresh, energy-blind C episode.

    This narrow wrapper exists for EXP-001 calibration.  It delegates to the
    same episode machinery as the development runner while making condition C
    the only possible execution path.
    """
    validated_seed = _validate_seeds((environment_seed,))[0]
    _validate_exp001_inputs(env_config, development_config)
    return _run_episode(
        condition=EXP001Condition.C,
        environment_seed=validated_seed,
        env_config=env_config,
        development_config=development_config,
    )


def _run_episode(
    *,
    condition: EXP001Condition,
    environment_seed: int,
    env_config: AweformEnvConfig,
    development_config: EXP001DevelopmentConfig,
) -> EXP001EpisodeRecord:
    environment = AweformEnv(env_config)
    raw_observation, info = environment.reset(seed=environment_seed)
    if info != {}:
        raise RuntimeError(
            "EXP-001 environment reset crossed the evaluator information boundary"
        )

    # This is a fresh mutable generator for this condition.  It is derived
    # from the same master seed as the other conditions but is never shared.
    policy_rng = policy_rng_from_seed(environment_seed)
    controller = _make_controller(condition, policy_rng, development_config)
    controller.reset()
    initial_state = _initial_state(environment)
    transitions: list[EXP001TransitionRecord] = []

    terminated = False
    truncated = False
    while not (terminated or truncated):
        controller_observation = exp001_controller_observation(
            condition,
            raw_observation,
        )
        action = _controller_action(controller, controller_observation)
        mode = controller.mode

        (
            next_raw_observation,
            reward,
            terminated,
            truncated,
            step_info,
        ) = environment.step(action)
        if reward != 0.0:
            raise RuntimeError("EXP-001 reward must remain exactly 0.0")
        if step_info != {}:
            raise RuntimeError(
                "EXP-001 environment step crossed the evaluator information boundary"
            )
        telemetry = environment.last_transition
        if telemetry is None:
            raise RuntimeError(
                "EXP-001 environment did not expose evaluator transition telemetry"
            )
        if telemetry.action is not action:
            raise RuntimeError(
                "EXP-001 telemetry action disagrees with controller action"
            )
        evaluator_step = _evaluator_step(environment, telemetry, mode)
        transitions.append(
            EXP001TransitionRecord(
                controller_visible=EXP001ControllerStep(
                    observation=controller_observation,
                ),
                privileged_evaluator=evaluator_step,
            )
        )
        raw_observation = next_raw_observation

    return EXP001EpisodeRecord(
        condition=condition,
        environment_seed=environment_seed,
        initial_state=initial_state,
        transitions=tuple(transitions),
    )


def _make_controller(
    condition: EXP001Condition,
    policy_rng: np.random.Generator,
    development_config: EXP001DevelopmentConfig,
) -> EXP001Controller:
    if condition is EXP001Condition.A:
        return EXP001AController(policy_rng, development_config)
    if condition is EXP001Condition.B:
        return EXP001BController(policy_rng, development_config)
    return EXP001CController(policy_rng, development_config)


def _controller_action(
    controller: EXP001Controller,
    observation: ControllerObservation,
) -> Action:
    if isinstance(controller, EXP001BController):
        if not isinstance(observation, InteroceptiveObservation):
            raise RuntimeError("EXP-001 B did not receive an interoceptive observation")
        return controller.act(observation)
    if not isinstance(observation, ExternalObservation):
        raise RuntimeError("EXP-001 A/C did not receive an external observation")
    return controller.act(observation)


def _initial_state(environment: AweformEnv) -> EXP001EvaluatorInitialState:
    if environment.body is None or environment.resource_field is None:
        raise RuntimeError("EXP-001 environment did not initialize evaluator state")
    return EXP001EvaluatorInitialState(
        position=environment.body.position,
        heading=environment.body.heading,
        actual_energy=environment.body.energy,
        source_positions=environment.resource_field.source_positions,
    )


def _evaluator_step(
    environment: AweformEnv,
    telemetry: TransitionTelemetry,
    controller_mode: EXP001Mode,
) -> EXP001EvaluatorStep:
    if environment.body is None:
        raise RuntimeError("EXP-001 environment body disappeared during execution")
    return EXP001EvaluatorStep(
        step_index=telemetry.step_index,
        action=telemetry.action,
        position=environment.body.position,
        heading=environment.body.heading,
        actual_energy=environment.body.energy,
        harvested_energy=telemetry.harvested_energy,
        basal_cost=telemetry.basal_cost,
        action_cost=telemetry.action_cost,
        energy_before=telemetry.energy_before,
        energy_after=telemetry.energy_after,
        terminated=telemetry.terminated,
        truncated=telemetry.truncated,
        controller_mode=controller_mode,
    )


def _validate_raw_observation(
    raw_observation: object,
) -> tuple[float, float, float, float]:
    try:
        values = np.asarray(raw_observation, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise ValueError(
            "EXP-001 environment observation must contain four finite values"
        ) from error
    if values.shape != (4,):
        raise ValueError(
            "EXP-001 environment observation must have shape (4,)"
        )
    if not np.all(np.isfinite(values)):
        raise ValueError("EXP-001 environment observation values must be finite")
    if np.any((values < 0.0) | (values > 1.0)):
        raise ValueError(
            "EXP-001 environment observation values must be within [0, 1]"
        )
    return tuple(float(value) for value in values)  # type: ignore[return-value]


def _validate_exp001_inputs(
    env_config: AweformEnvConfig,
    development_config: EXP001DevelopmentConfig,
) -> None:
    if not isinstance(env_config, AweformEnvConfig):
        raise ValueError("env_config must be an AweformEnvConfig")
    if not isinstance(development_config, EXP001DevelopmentConfig):
        raise ValueError(
            "development_config must be an EXP001DevelopmentConfig"
        )
    if env_config.turn_angle != math.pi / 4.0:
        raise ValueError(
            "EXP-001 requires env_config.turn_angle == math.pi / 4"
        )


def _validate_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    if isinstance(seeds, (str, bytes)):
        raise ValueError("seeds must be a non-empty sequence of non-negative integers")
    try:
        supplied_seeds = tuple(seeds)
    except TypeError as error:
        raise ValueError(
            "seeds must be a non-empty sequence of non-negative integers"
        ) from error
    if not supplied_seeds:
        raise ValueError("seeds must not be empty")
    validated: list[int] = []
    for seed in supplied_seeds:
        if isinstance(seed, bool) or not isinstance(seed, Integral) or seed < 0:
            raise ValueError("seeds must contain only non-negative integer values")
        validated.append(int(seed))
    return tuple(validated)
