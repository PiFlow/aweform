"""Evaluator-side EXP-002 matched execution and diagnostic derivation.

The runner reuses the existing EXP-001 A/B/C controller implementations. Its
additional state is captured around environment transitions and is never sent
through the controller observation adapter.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

import numpy as np

from .env import Action, AweformEnv, AweformEnvConfig
from .exp001 import (
    EXP001AController,
    EXP001BController,
    EXP001CController,
    EXP001Mode,
    ExternalObservation,
    InteroceptiveObservation,
    policy_rng_from_seed,
)
from .exp001_calibration import FROZEN_EXP001_CALIBRATION_ENV_CONFIG
from .exp001_runner import (
    ControllerObservation,
    EXP001Condition,
    exp001_controller_observation,
)
from .exp002_coverage import CoverageGrid
from .exp002_protocol import (
    EXP002_B_CANDIDATES,
    EXP002_COVERAGE_GRID_HEIGHT,
    EXP002_COVERAGE_GRID_WIDTH,
    EXP002_HORIZON,
    EXP002BCandidate,
    EXP002SharedControllerValues,
)
from .exp002_seed_policy import validate_exp002_development_seeds

EXP002Controller = EXP001AController | EXP001BController | EXP001CController


@dataclass(frozen=True, slots=True)
class EXP002EvaluatorInitialState:
    """Privileged evaluator state captured before the first action."""

    position: tuple[float, float]
    heading: float
    actual_energy: float
    source_positions: tuple[tuple[float, float], ...]


@dataclass(frozen=True, slots=True)
class EXP002ControllerStep:
    """The observation actually handed to one controller."""

    observation: ControllerObservation


@dataclass(frozen=True, slots=True)
class EXP002EvaluatorStep:
    """Privileged telemetry for one transition, including pre/post position."""

    step_index: int
    action: Action
    position_before: tuple[float, float]
    position_after: tuple[float, float]
    heading: float
    actual_energy_before: float
    actual_energy_after: float
    harvested_energy: float
    basal_cost: float
    action_cost: float
    controller_mode_before_action: EXP001Mode
    controller_mode: EXP001Mode
    terminated: bool
    truncated: bool


@dataclass(frozen=True, slots=True)
class EXP002TransitionRecord:
    """Controller-visible and evaluator-only sides of one action."""

    controller_visible: EXP002ControllerStep
    privileged_evaluator: EXP002EvaluatorStep


@dataclass(frozen=True, slots=True)
class EXP002EpisodeRecord:
    """Raw evaluator trajectory for one matched EXP-002 episode."""

    condition: EXP001Condition
    candidate: EXP002BCandidate
    environment_seed: int
    initial_state: EXP002EvaluatorInitialState
    transitions: tuple[EXP002TransitionRecord, ...]


@dataclass(frozen=True, slots=True)
class EXP002SeekAttempt:
    """Evaluator-only return-reserve data for one B SEEK attempt."""

    onset_step: int
    normalized_energy_at_onset: float
    nearest_source_distance_at_onset: float
    reached_charge: bool
    minimum_normalized_energy: float


@dataclass(frozen=True, slots=True)
class EXP002EpisodeDiagnostics:
    """Descriptive evaluator metrics derived from one raw trajectory."""

    capped_lifespan: int
    horizon_survivor: bool
    visited_cell_count: int
    remaining_cell_count: int
    coverage_fraction: float
    explore_action_count: int
    distance_travelled_during_explore: float
    explore_unique_cell_count: int
    coverage_efficiency_per_100_explore_actions: float
    complete_recharge_cycle_count: int
    seek_attempts: tuple[EXP002SeekAttempt, ...]


@dataclass(frozen=True, slots=True)
class EXP002DevelopmentBatchResult:
    """Matched raw episodes plus evaluator-only diagnostic summaries."""

    environment_config: AweformEnvConfig
    candidate: EXP002BCandidate
    environment_seeds: tuple[int, ...]
    episodes: tuple[EXP002EpisodeRecord, ...]
    diagnostics: tuple[EXP002EpisodeDiagnostics, ...]


def exp002_coverage_grid_for_episode(
    episode: EXP002EpisodeRecord,
) -> CoverageGrid:
    """Replay one episode's evaluator-only coverage into its canonical grid."""
    states = exp002_coverage_grid_states(episode)
    return states[-1]


def exp002_coverage_grid_states(
    episode: EXP002EpisodeRecord,
) -> tuple[CoverageGrid, ...]:
    """Return canonical coverage-grid snapshots before and after each action."""
    environment_config = FROZEN_EXP001_CALIBRATION_ENV_CONFIG
    coverage = CoverageGrid(
        width=EXP002_COVERAGE_GRID_WIDTH,
        height=EXP002_COVERAGE_GRID_HEIGHT,
        world_min=environment_config.world_min,
        world_max=environment_config.world_max,
    )
    coverage.mark_position(episode.initial_state.position)
    states = [coverage.copy()]
    for transition in episode.transitions:
        evaluator = transition.privileged_evaluator
        if evaluator.action is Action.MOVE_FORWARD:
            coverage.mark_movement(
                evaluator.position_before,
                evaluator.position_after,
            )
        else:
            coverage.mark_position(evaluator.position_after)
        states.append(coverage.copy())
    return tuple(states)


def run_exp002_development_batch(
    seeds: Sequence[int],
    env_config: AweformEnvConfig,
    candidate: EXP002BCandidate,
) -> EXP002DevelopmentBatchResult:
    """Execute matched debug episodes for one B threshold candidate.

    This is instrumentation only. Formal calibration and confirmatory seed
    execution are intentionally not implemented here.
    """
    validated_seeds = validate_exp002_development_seeds(seeds)
    _validate_inputs(env_config, candidate)
    episodes: list[EXP002EpisodeRecord] = []
    for seed in validated_seeds:
        for condition in EXP001Condition:
            episodes.append(
                _run_episode(
                    condition=condition,
                    environment_seed=seed,
                    env_config=env_config,
                    candidate=candidate,
                )
            )
    episode_tuple = tuple(episodes)
    return EXP002DevelopmentBatchResult(
        environment_config=env_config,
        candidate=candidate,
        environment_seeds=validated_seeds,
        episodes=episode_tuple,
        diagnostics=tuple(
            summarize_exp002_episode(episode) for episode in episode_tuple
        ),
    )


def summarize_exp002_episode(
    episode: EXP002EpisodeRecord,
) -> EXP002EpisodeDiagnostics:
    """Derive evaluator-only coverage, reserve, and descriptive metrics."""
    if not episode.transitions:
        raise ValueError("episode must contain at least one transition")

    coverage = exp002_coverage_grid_for_episode(episode)
    explore_coverage = CoverageGrid()
    explore_coverage.mark_position(episode.initial_state.position)

    explore_action_count = 0
    distance_travelled_during_explore = 0.0
    event_modes: list[EXP001Mode] = [EXP001Mode.EXPLORE]
    seek_attempts: list[EXP002SeekAttempt] = []
    active_attempt: dict[str, float | int | bool] | None = None

    for transition in episode.transitions:
        evaluator = transition.privileged_evaluator
        mode = evaluator.controller_mode
        if mode is EXP001Mode.EXPLORE:
            explore_action_count += 1
            if evaluator.action is Action.MOVE_FORWARD:
                explore_coverage.mark_movement(
                    evaluator.position_before,
                    evaluator.position_after,
                )
                distance_travelled_during_explore += math.dist(
                    evaluator.position_before,
                    evaluator.position_after,
                )
            else:
                explore_coverage.mark_position(evaluator.position_after)

        if _entered_seek(episode, evaluator):
            active_attempt = {
                "onset_step": evaluator.step_index,
                "normalized_energy_at_onset": _episode_normalized_energy(
                    evaluator.actual_energy_before
                ),
                "nearest_source_distance_at_onset": _nearest_source_distance(
                    evaluator.position_before,
                    episode.initial_state.source_positions,
                ),
                "reached_charge": False,
                "minimum_normalized_energy": _episode_normalized_energy(
                    evaluator.actual_energy_before
                ),
            }

        if active_attempt is not None:
            normalized_after = _episode_normalized_energy(
                evaluator.actual_energy_after
            )
            active_attempt["minimum_normalized_energy"] = min(
                float(active_attempt["minimum_normalized_energy"]), normalized_after
            )
            if mode is EXP001Mode.CHARGE:
                active_attempt["reached_charge"] = True
                seek_attempts.append(_freeze_seek_attempt(active_attempt))
                active_attempt = None
            elif evaluator.terminated or evaluator.truncated:
                seek_attempts.append(_freeze_seek_attempt(active_attempt))
                active_attempt = None

        _append_mode_events(event_modes, episode, evaluator)

    if active_attempt is not None:
        seek_attempts.append(_freeze_seek_attempt(active_attempt))

    capped_lifespan = len(episode.transitions)
    terminal = episode.transitions[-1].privileged_evaluator
    return EXP002EpisodeDiagnostics(
        capped_lifespan=min(capped_lifespan, EXP002_HORIZON),
        horizon_survivor=(
            capped_lifespan == EXP002_HORIZON
            and terminal.truncated
            and not terminal.terminated
        ),
        visited_cell_count=coverage.visited_cell_count,
        remaining_cell_count=coverage.remaining_cell_count,
        coverage_fraction=coverage.coverage_fraction,
        explore_action_count=explore_action_count,
        distance_travelled_during_explore=distance_travelled_during_explore,
        explore_unique_cell_count=explore_coverage.visited_cell_count,
        coverage_efficiency_per_100_explore_actions=(
            100.0 * explore_coverage.visited_cell_count / explore_action_count
            if explore_action_count
            else 0.0
        ),
        complete_recharge_cycle_count=_count_complete_recharge_cycles(event_modes),
        seek_attempts=tuple(seek_attempts),
    )


def _run_episode(
    *,
    condition: EXP001Condition,
    environment_seed: int,
    env_config: AweformEnvConfig,
    candidate: EXP002BCandidate,
) -> EXP002EpisodeRecord:
    environment = AweformEnv(env_config)
    raw_observation, info = environment.reset(seed=environment_seed)
    if info != {}:
        raise RuntimeError("EXP-002 reset crossed the evaluator information boundary")
    policy_rng = policy_rng_from_seed(environment_seed)
    controller = _make_controller(condition, policy_rng, candidate)
    controller.reset()
    initial_state = _initial_state(environment)
    transitions: list[EXP002TransitionRecord] = []

    terminated = False
    truncated = False
    while not (terminated or truncated):
        if environment.body is None:
            raise RuntimeError("EXP-002 environment body disappeared before action")
        position_before = environment.body.position
        mode_before_action = controller.mode
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
            raise RuntimeError("EXP-002 reward must remain exactly 0.0")
        if step_info != {}:
            raise RuntimeError(
                "EXP-002 step crossed the evaluator information boundary"
            )
        telemetry = environment.last_transition
        if telemetry is None or environment.body is None:
            raise RuntimeError("EXP-002 transition telemetry is unavailable")
        if telemetry.action is not action:
            raise RuntimeError("EXP-002 telemetry action disagrees with controller")
        evaluator_step = EXP002EvaluatorStep(
            step_index=telemetry.step_index,
            action=telemetry.action,
            position_before=position_before,
            position_after=environment.body.position,
            heading=environment.body.heading,
            actual_energy_before=telemetry.energy_before,
            actual_energy_after=telemetry.energy_after,
            harvested_energy=telemetry.harvested_energy,
            basal_cost=telemetry.basal_cost,
            action_cost=telemetry.action_cost,
            controller_mode_before_action=mode_before_action,
            controller_mode=mode,
            terminated=telemetry.terminated,
            truncated=telemetry.truncated,
        )
        transitions.append(
            EXP002TransitionRecord(
                controller_visible=EXP002ControllerStep(
                    observation=controller_observation,
                ),
                privileged_evaluator=evaluator_step,
            )
        )
        raw_observation = next_raw_observation

    return EXP002EpisodeRecord(
        condition=condition,
        candidate=candidate,
        environment_seed=environment_seed,
        initial_state=initial_state,
        transitions=tuple(transitions),
    )


def _make_controller(
    condition: EXP001Condition,
    policy_rng: np.random.Generator,
    candidate: EXP002BCandidate,
) -> EXP002Controller:
    shared = EXP002SharedControllerValues()
    if condition is EXP001Condition.A:
        return EXP001AController(policy_rng, shared.for_a_or_c())
    if condition is EXP001Condition.B:
        return EXP001BController(policy_rng, shared.for_b_candidate(candidate))
    return EXP001CController(policy_rng, shared.for_a_or_c())


def _controller_action(
    controller: EXP002Controller,
    observation: ControllerObservation,
) -> Action:
    if isinstance(controller, EXP001BController):
        if not isinstance(observation, InteroceptiveObservation):
            raise RuntimeError("EXP-002 B did not receive interoceptive observation")
        return controller.act(observation)
    if not isinstance(observation, ExternalObservation):
        raise RuntimeError("EXP-002 A/C did not receive external observation")
    return controller.act(observation)


def _initial_state(environment: AweformEnv) -> EXP002EvaluatorInitialState:
    if environment.body is None or environment.resource_field is None:
        raise RuntimeError("EXP-002 environment did not initialize evaluator state")
    return EXP002EvaluatorInitialState(
        position=environment.body.position,
        heading=environment.body.heading,
        actual_energy=environment.body.energy,
        source_positions=environment.resource_field.source_positions,
    )


def _entered_seek(
    episode: EXP002EpisodeRecord,
    evaluator: EXP002EvaluatorStep,
) -> bool:
    if episode.condition is not EXP001Condition.B:
        return False
    return (
        evaluator.controller_mode_before_action is EXP001Mode.EXPLORE
        and evaluator.controller_mode
        in (EXP001Mode.SEEK_RESOURCE, EXP001Mode.CHARGE)
        and _episode_normalized_energy(evaluator.actual_energy_before)
        < episode.candidate.enter_seek
    )


def _append_mode_events(
    event_modes: list[EXP001Mode],
    episode: EXP002EpisodeRecord,
    evaluator: EXP002EvaluatorStep,
) -> None:
    if (
        _entered_seek(episode, evaluator)
        and evaluator.controller_mode is EXP001Mode.CHARGE
    ):
        event_modes.append(EXP001Mode.SEEK_RESOURCE)
    event_modes.append(evaluator.controller_mode)


def _count_complete_recharge_cycles(modes: Sequence[EXP001Mode]) -> int:
    compressed: list[EXP001Mode] = []
    for mode in modes:
        if not compressed or compressed[-1] is not mode:
            compressed.append(mode)
    return sum(
        compressed[index : index + 4]
        == [
            EXP001Mode.EXPLORE,
            EXP001Mode.SEEK_RESOURCE,
            EXP001Mode.CHARGE,
            EXP001Mode.EXPLORE,
        ]
        for index in range(max(0, len(compressed) - 3))
    )


def _freeze_seek_attempt(values: dict[str, float | int | bool]) -> EXP002SeekAttempt:
    return EXP002SeekAttempt(
        onset_step=int(values["onset_step"]),
        normalized_energy_at_onset=float(values["normalized_energy_at_onset"]),
        nearest_source_distance_at_onset=float(
            values["nearest_source_distance_at_onset"]
        ),
        reached_charge=bool(values["reached_charge"]),
        minimum_normalized_energy=float(values["minimum_normalized_energy"]),
    )


def _nearest_source_distance(
    position: tuple[float, float],
    sources: tuple[tuple[float, float], ...],
) -> float:
    return min(math.dist(position, source) for source in sources)


def _episode_normalized_energy(
    actual_energy: float,
) -> float:
    energy_config = FROZEN_EXP001_CALIBRATION_ENV_CONFIG.energy
    energy_range = energy_config.maximum_energy - energy_config.failure_boundary
    return (actual_energy - energy_config.failure_boundary) / energy_range


def _validate_inputs(
    env_config: AweformEnvConfig,
    candidate: EXP002BCandidate,
) -> None:
    if not isinstance(env_config, AweformEnvConfig):
        raise ValueError("env_config must be an AweformEnvConfig")
    if env_config != FROZEN_EXP001_CALIBRATION_ENV_CONFIG:
        raise ValueError(
            "EXP-002 requires env_config to equal the frozen EXP-001 "
            "environment exactly"
        )
    if not isinstance(candidate, EXP002BCandidate):
        raise ValueError("candidate must be an EXP002BCandidate")
    if env_config.turn_angle != math.pi / 4.0:
        raise ValueError("EXP-002 requires env_config.turn_angle == math.pi / 4")
    if env_config.episode_horizon != EXP002_HORIZON:
        raise ValueError("EXP-002 requires a 1000-transition horizon")
    if tuple(EXP002BCandidate) != EXP002_B_CANDIDATES:
        raise RuntimeError("EXP-002 candidate registry is inconsistent")
