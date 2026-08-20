"""Matched EXP-003 development execution and evaluator diagnostics."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence, cast

import numpy as np

from .env import Action, AweformEnvConfig
from .exp001_calibration import FROZEN_EXP001_CALIBRATION_ENV_CONFIG
from .exp001_runner import EXP001Condition
from .exp002_coverage import CoverageGrid
from .exp002_protocol import EXP002BCandidate
from .exp002_runner import (
    EXP002EpisodeDiagnostics,
    EXP002EpisodeRecord,
    summarize_exp002_episode,
)
from .exp002_runner import (
    _run_episode as run_historical_b50_episode,
)
from .exp003 import (
    EXP003_COVERAGE_GRID_HEIGHT,
    EXP003_COVERAGE_GRID_WIDTH,
    EXP003Mode,
    EXP003StationConfig,
    LocalizedChargingStationEnv,
    StationB50Controller,
    StationObservation,
)
from .exp003_seed_policy import validate_exp003_development_seeds
from .rng import RandomStreams


@dataclass(frozen=True, slots=True)
class EXP003EvaluatorInitialState:
    """Privileged station-side state captured before the first action."""

    position: tuple[float, float]
    heading: float
    actual_energy: float
    station_center: tuple[float, float]


@dataclass(frozen=True, slots=True)
class EXP003ControllerStep:
    """The typed observation handed to STATION_B50."""

    observation: StationObservation


@dataclass(frozen=True, slots=True)
class EXP003EvaluatorStep:
    """Privileged telemetry for one station transition."""

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
    charging_contact_before: bool
    charging_contact_after: bool
    controller_mode_before_action: EXP003Mode
    controller_mode: EXP003Mode
    terminated: bool
    truncated: bool


@dataclass(frozen=True, slots=True)
class EXP003TransitionRecord:
    """Controller-visible and evaluator-only sides of one transition."""

    controller_visible: EXP003ControllerStep
    privileged_evaluator: EXP003EvaluatorStep


@dataclass(frozen=True, slots=True)
class EXP003EpisodeRecord:
    """Raw STATION_B50 evaluator trajectory."""

    environment_seed: int
    initial_state: EXP003EvaluatorInitialState
    transitions: tuple[EXP003TransitionRecord, ...]


@dataclass(frozen=True, slots=True)
class EXP003SeekAttempt:
    """Evaluator-only diagnostics for one SEEK attempt.

    ``normalized_energy_before_acquisition`` is sampled from
    ``actual_energy_before`` on the first transition whose post-transition
    contact is true. It therefore excludes that transition's charging input.
    """

    onset_step: int
    normalized_energy_at_onset: float
    station_distance_at_onset: float
    reached_charging_contact: bool
    transitions_to_charging_contact: int | None
    normalized_energy_before_acquisition: float | None
    minimum_normalized_energy: float


@dataclass(frozen=True, slots=True)
class EXP003EpisodeDiagnostics:
    """Evaluator-only descriptive metrics for one station episode."""

    capped_lifespan: int
    horizon_survivor: bool
    final_normalized_energy: float
    minimum_normalized_energy: float
    total_charged_energy: float
    total_distance_travelled: float
    visited_cell_count: int
    remaining_cell_count: int
    coverage_fraction: float
    explore_action_count: int
    explore_distance_travelled: float
    recharge_cycle_count: int
    station_entry_count: int
    transitions_on_charger: int
    seek_attempts: tuple[EXP003SeekAttempt, ...]
    energy_when_seek_begins: tuple[float, ...]
    station_distance_when_seek_begins: tuple[float, ...]
    energy_before_successful_charger_acquisition: tuple[float, ...]
    seek_attempt_count: int
    seek_attempts_reaching_charger: int
    seek_attempts_reaching_charger_fraction: float
    transitions_from_seek_to_successful_acquisition: tuple[int, ...]
    minimum_energy_during_seek_attempts: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class EXP003DevelopmentComparison:
    """Matched ordinary-seed FIELD_B50 and STATION_B50 development output."""

    development_seeds: tuple[int, ...]
    field_environment_config: AweformEnvConfig
    station_environment_config: EXP003StationConfig
    field_b50_episodes: tuple[EXP002EpisodeRecord, ...]
    field_b50_diagnostics: tuple[EXP002EpisodeDiagnostics, ...]
    station_b50_episodes: tuple[EXP003EpisodeRecord, ...]
    station_b50_diagnostics: tuple[EXP003EpisodeDiagnostics, ...]


def exp003_controller_observation(raw_observation: object) -> StationObservation:
    """Adapt the five-value simulator array without crossing evaluator truth."""
    try:
        values = np.asarray(raw_observation, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise ValueError("observation must contain five finite values") from error
    if values.shape != (5,) or not np.all(np.isfinite(values)):
        raise ValueError("observation must contain five finite values")
    if np.any((values[:4] < 0.0) | (values[:4] > 1.0)):
        raise ValueError("energy and beacon values must be within [0, 1]")
    if values[4] not in (0.0, 1.0):
        raise ValueError("charging_contact must be encoded as exactly 0.0 or 1.0")
    from .exp003 import BeaconObservation

    return StationObservation(
        energy=float(values[0]),
        beacon=BeaconObservation(
            left=float(values[1]),
            forward=float(values[2]),
            right=float(values[3]),
            charging_contact=bool(values[4]),
        ),
    )


def run_exp003_development_comparison(
    seeds: Sequence[int],
    station_config: EXP003StationConfig | None = None,
) -> EXP003DevelopmentComparison:
    """Run matched FIELD_B50 and STATION_B50 episodes on ordinary seeds only."""
    development_seeds = validate_exp003_development_seeds(seeds)
    config = station_config or EXP003StationConfig()
    field_episodes = tuple(
        run_historical_b50_episode(
            condition=EXP001Condition.B,
            environment_seed=seed,
            env_config=FROZEN_EXP001_CALIBRATION_ENV_CONFIG,
            candidate=EXP002BCandidate.B50,
        )
        for seed in development_seeds
    )
    station_episodes = tuple(
        _run_station_episode(seed, config) for seed in development_seeds
    )
    return EXP003DevelopmentComparison(
        development_seeds=development_seeds,
        field_environment_config=FROZEN_EXP001_CALIBRATION_ENV_CONFIG,
        station_environment_config=config,
        field_b50_episodes=field_episodes,
        field_b50_diagnostics=tuple(
            summarize_exp002_episode(episode) for episode in field_episodes
        ),
        station_b50_episodes=station_episodes,
        station_b50_diagnostics=tuple(
            summarize_exp003_episode(episode, config) for episode in station_episodes
        ),
    )


def summarize_exp003_episode(
    episode: EXP003EpisodeRecord,
    config: EXP003StationConfig | None = None,
) -> EXP003EpisodeDiagnostics:
    """Derive all requested station diagnostics from recorded telemetry."""
    if not episode.transitions:
        raise ValueError("episode must contain at least one transition")
    environment_config = config or EXP003StationConfig()
    coverage = exp003_coverage_grid_for_episode(episode, environment_config)
    explore_coverage = CoverageGrid(
        width=EXP003_COVERAGE_GRID_WIDTH,
        height=EXP003_COVERAGE_GRID_HEIGHT,
        world_min=environment_config.world_min,
        world_max=environment_config.world_max,
    )
    explore_coverage.mark_position(episode.initial_state.position)
    modes: list[EXP003Mode] = [EXP003Mode.EXPLORE]
    seek_attempts: list[EXP003SeekAttempt] = []
    active: dict[str, float | int | bool | None] | None = None
    total_distance = 0.0
    explore_actions = 0
    explore_distance = 0.0
    total_charged = 0.0
    station_entries = 0
    transitions_on_charger = 0
    minimum_energy = _normalized_energy(
        episode.initial_state.actual_energy, environment_config
    )

    for transition in episode.transitions:
        evaluator = transition.privileged_evaluator
        total_distance += math.dist(evaluator.position_before, evaluator.position_after)
        total_charged += evaluator.harvested_energy
        normalized_before = _normalized_energy(
            evaluator.actual_energy_before, environment_config
        )
        normalized_after = _normalized_energy(
            evaluator.actual_energy_after, environment_config
        )
        minimum_energy = min(minimum_energy, normalized_before, normalized_after)
        if evaluator.charging_contact_after:
            transitions_on_charger += 1
        if not evaluator.charging_contact_before and evaluator.charging_contact_after:
            station_entries += 1

        if evaluator.controller_mode is EXP003Mode.EXPLORE:
            explore_actions += 1
            if evaluator.action is Action.MOVE_FORWARD:
                explore_coverage.mark_movement(
                    evaluator.position_before, evaluator.position_after
                )
                distance = math.dist(
                    evaluator.position_before, evaluator.position_after
                )
                explore_distance += distance
            else:
                explore_coverage.mark_position(evaluator.position_after)

        entered_seek = (
            evaluator.controller_mode_before_action is EXP003Mode.EXPLORE
            and evaluator.controller_mode in (EXP003Mode.SEEK, EXP003Mode.CHARGE)
            and normalized_before < 0.50
        )
        if entered_seek:
            active = {
                "onset_step": evaluator.step_index,
                "normalized_energy_at_onset": normalized_before,
                "station_distance_at_onset": math.dist(
                    evaluator.position_before, episode.initial_state.station_center
                ),
                "reached_charging_contact": False,
                "transitions_to_charging_contact": None,
                "normalized_energy_before_acquisition": None,
                "minimum_normalized_energy": normalized_before,
            }

        if active is not None:
            active["minimum_normalized_energy"] = min(
                cast(float, active["minimum_normalized_energy"]),
                normalized_before,
                normalized_after,
            )
            if evaluator.charging_contact_after and not bool(
                active["reached_charging_contact"]
            ):
                active["reached_charging_contact"] = True
                active["transitions_to_charging_contact"] = (
                    evaluator.step_index - cast(int, active["onset_step"]) + 1
                )
                # Acquisition is the start of this atomic transition. The
                # charging input is applied after this pre-transition reading.
                active["normalized_energy_before_acquisition"] = normalized_before
                seek_attempts.append(_freeze_seek_attempt(active))
                active = None
            elif evaluator.terminated or evaluator.truncated:
                seek_attempts.append(_freeze_seek_attempt(active))
                active = None

        modes.append(evaluator.controller_mode)

    if active is not None:
        seek_attempts.append(_freeze_seek_attempt(active))
    capped_lifespan = min(len(episode.transitions), environment_config.episode_horizon)
    final_energy = _normalized_energy(
        episode.transitions[-1].privileged_evaluator.actual_energy_after,
        environment_config,
    )
    energy_before_success = tuple(
        float(attempt.normalized_energy_before_acquisition)
        for attempt in seek_attempts
        if attempt.normalized_energy_before_acquisition is not None
    )
    transitions_to_success = tuple(
        int(attempt.transitions_to_charging_contact)
        for attempt in seek_attempts
        if attempt.transitions_to_charging_contact is not None
    )
    reached_count = sum(attempt.reached_charging_contact for attempt in seek_attempts)
    return EXP003EpisodeDiagnostics(
        capped_lifespan=capped_lifespan,
        horizon_survivor=capped_lifespan == environment_config.episode_horizon
        and not episode.transitions[-1].privileged_evaluator.terminated,
        final_normalized_energy=final_energy,
        minimum_normalized_energy=minimum_energy,
        total_charged_energy=total_charged,
        total_distance_travelled=total_distance,
        visited_cell_count=coverage.visited_cell_count,
        remaining_cell_count=coverage.remaining_cell_count,
        coverage_fraction=coverage.coverage_fraction,
        explore_action_count=explore_actions,
        explore_distance_travelled=explore_distance,
        recharge_cycle_count=_count_recharge_cycles(modes),
        station_entry_count=station_entries,
        transitions_on_charger=transitions_on_charger,
        seek_attempts=tuple(seek_attempts),
        energy_when_seek_begins=tuple(
            attempt.normalized_energy_at_onset for attempt in seek_attempts
        ),
        station_distance_when_seek_begins=tuple(
            attempt.station_distance_at_onset for attempt in seek_attempts
        ),
        energy_before_successful_charger_acquisition=energy_before_success,
        seek_attempt_count=len(seek_attempts),
        seek_attempts_reaching_charger=reached_count,
        seek_attempts_reaching_charger_fraction=(
            reached_count / len(seek_attempts) if seek_attempts else 0.0
        ),
        transitions_from_seek_to_successful_acquisition=transitions_to_success,
        minimum_energy_during_seek_attempts=tuple(
            attempt.minimum_normalized_energy for attempt in seek_attempts
        ),
    )


def exp003_coverage_grid_for_episode(
    episode: EXP003EpisodeRecord,
    config: EXP003StationConfig | None = None,
) -> CoverageGrid:
    """Replay actual station trajectory into the evaluator-only grid."""
    states = exp003_coverage_grid_states(episode, config)
    return states[-1]


def exp003_coverage_grid_states(
    episode: EXP003EpisodeRecord,
    config: EXP003StationConfig | None = None,
) -> tuple[CoverageGrid, ...]:
    environment_config = config or EXP003StationConfig()
    coverage = CoverageGrid(
        width=EXP003_COVERAGE_GRID_WIDTH,
        height=EXP003_COVERAGE_GRID_HEIGHT,
        world_min=environment_config.world_min,
        world_max=environment_config.world_max,
    )
    coverage.mark_position(episode.initial_state.position)
    states = [coverage.copy()]
    for transition in episode.transitions:
        evaluator = transition.privileged_evaluator
        if evaluator.action is Action.MOVE_FORWARD:
            coverage.mark_movement(evaluator.position_before, evaluator.position_after)
        else:
            coverage.mark_position(evaluator.position_after)
        states.append(coverage.copy())
    return tuple(states)


def _run_station_episode(
    environment_seed: int,
    config: EXP003StationConfig,
) -> EXP003EpisodeRecord:
    environment = LocalizedChargingStationEnv(config)
    raw_observation, info = environment.reset(seed=environment_seed)
    if info != {}:
        raise RuntimeError("EXP-003 reset crossed the evaluator boundary")
    policy_rng = RandomStreams.from_seed(environment_seed).policy
    controller = StationB50Controller(policy_rng)
    controller.reset()
    if environment.body is None or environment.station_center is None:
        raise RuntimeError("EXP-003 environment did not initialize evaluator state")
    initial_state = EXP003EvaluatorInitialState(
        position=environment.body.position,
        heading=environment.body.heading,
        actual_energy=environment.body.energy,
        station_center=environment.station_center,
    )
    transitions: list[EXP003TransitionRecord] = []
    terminated = False
    truncated = False
    while not (terminated or truncated):
        controller_observation = exp003_controller_observation(raw_observation)
        mode_before_action = controller.mode
        action = controller.act(controller_observation)
        mode = controller.mode
        if environment.body is None:
            raise RuntimeError("EXP-003 body disappeared before transition")
        position_before = environment.body.position
        next_raw, reward, terminated, truncated, step_info = environment.step(action)
        if reward != 0.0:
            raise RuntimeError("EXP-003 reward must remain exactly 0.0")
        if step_info != {}:
            raise RuntimeError("EXP-003 step crossed the evaluator boundary")
        telemetry = environment.last_transition
        if telemetry is None:
            raise RuntimeError("EXP-003 transition telemetry is unavailable")
        if environment.body is None or telemetry.action is not action:
            raise RuntimeError("EXP-003 telemetry disagrees with controller action")
        transitions.append(
            EXP003TransitionRecord(
                controller_visible=EXP003ControllerStep(controller_observation),
                privileged_evaluator=EXP003EvaluatorStep(
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
                    charging_contact_before=telemetry.charging_contact_before,
                    charging_contact_after=telemetry.charging_contact_after,
                    controller_mode_before_action=mode_before_action,
                    controller_mode=mode,
                    terminated=telemetry.terminated,
                    truncated=telemetry.truncated,
                ),
            )
        )
        raw_observation = next_raw
    return EXP003EpisodeRecord(
        environment_seed=environment_seed,
        initial_state=initial_state,
        transitions=tuple(transitions),
    )


def _normalized_energy(actual_energy: float, config: EXP003StationConfig) -> float:
    energy = config.energy
    return (actual_energy - energy.failure_boundary) / (
        energy.maximum_energy - energy.failure_boundary
    )


def _freeze_seek_attempt(
    values: dict[str, float | int | bool | None],
) -> EXP003SeekAttempt:
    return EXP003SeekAttempt(
        onset_step=cast(int, values["onset_step"]),
        normalized_energy_at_onset=cast(
            float, values["normalized_energy_at_onset"]
        ),
        station_distance_at_onset=cast(
            float, values["station_distance_at_onset"]
        ),
        reached_charging_contact=bool(values["reached_charging_contact"]),
        transitions_to_charging_contact=(
            None
            if values["transitions_to_charging_contact"] is None
            else cast(int, values["transitions_to_charging_contact"])
        ),
        normalized_energy_before_acquisition=(
            None
            if values["normalized_energy_before_acquisition"] is None
            else cast(float, values["normalized_energy_before_acquisition"])
        ),
        minimum_normalized_energy=cast(
            float, values["minimum_normalized_energy"]
        ),
    )


def _count_recharge_cycles(modes: Sequence[EXP003Mode]) -> int:
    compressed: list[EXP003Mode] = []
    for mode in modes:
        if not compressed or compressed[-1] is not mode:
            compressed.append(mode)
    pattern = [
        EXP003Mode.EXPLORE,
        EXP003Mode.SEEK,
        EXP003Mode.CHARGE,
        EXP003Mode.EXPLORE,
    ]
    return sum(
        compressed[index : index + len(pattern)] == pattern
        for index in range(max(0, len(compressed) - len(pattern) + 1))
    )
