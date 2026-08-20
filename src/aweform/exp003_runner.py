"""Matched EXP-003 development execution and evaluator diagnostics."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence

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


class EXP003SeekOutcome(str, Enum):
    """Evaluator-only outcome classification for one SEEK attempt."""

    ACQUIRED = "ACQUIRED"
    TERMINATED_BEFORE_ACQUISITION = "TERMINATED_BEFORE_ACQUISITION"
    HORIZON_CENSORED = "HORIZON_CENSORED"


@dataclass(frozen=True, slots=True)
class EXP003SeekFeasibilityMetrics:
    """Evaluator-only charge-aware optimistic SEEK metrics."""

    distance_to_charging_boundary: float
    optimistic_minimum_forward_transitions: int
    optimistic_onset_reserve_threshold: float
    available_onset_energy_above_failure: float
    optimistic_reserve_margin: float

    @property
    def optimistically_feasible(self) -> bool:
        """Return feasibility under the strict optimistic approximation."""
        return (
            self.available_onset_energy_above_failure
            > self.optimistic_onset_reserve_threshold
        )


@dataclass(frozen=True, slots=True)
class _EXP003SeekBeaconMetrics:
    """Evaluator-side summaries of recorded controller-visible beacon data."""

    onset_beacon_left: float
    onset_beacon_forward: float
    onset_beacon_right: float
    onset_max_beacon_signal: float
    onset_mean_beacon_signal: float
    onset_beacon_directional_contrast: float
    pre_seek_beacon_observation_count: int
    pre_seek_recent_mean_beacon_signal: float | None
    pre_seek_recent_max_beacon_signal: float | None
    pre_seek_beacon_strength_trend: float | None


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
    outcome: EXP003SeekOutcome
    transitions_elapsed: int
    reached_charging_contact: bool
    transitions_to_charging_contact: int | None
    normalized_energy_before_acquisition: float | None
    minimum_normalized_energy: float
    boundary_clamp_count: int
    had_boundary_clamp: bool
    longest_boundary_clamp_streak: int
    station_distance_at_termination: float | None
    station_distance_at_horizon: float | None
    distance_to_charging_boundary: float
    optimistic_minimum_forward_transitions: int
    optimistic_onset_reserve_threshold: float
    available_onset_energy_above_failure: float
    optimistic_reserve_margin: float
    move_forward_count: int
    turn_left_count: int
    turn_right_count: int
    wait_count: int
    nominal_basal_cost_sum: float
    nominal_action_cost_sum: float
    nominal_total_cost_sum: float
    realized_forward_distance: float
    turn_count: int
    turn_fraction: float
    actual_forward_to_ideal_transition_ratio: float | None
    realized_path_to_onset_boundary_ratio: float | None
    station_distance_trajectory: tuple[float, ...]
    net_radial_progress_toward_station: float
    cumulative_inward_radial_progress: float
    cumulative_outward_radial_movement: float
    forward_actions_reducing_station_distance: int
    forward_actions_increasing_station_distance: int
    forward_inward_progress_fraction: float | None
    forward_outward_progress_fraction: float | None
    max_consecutive_transitions_without_net_progress_toward_station: int
    idealized_nominal_straight_line_cost_demand: float
    nominal_cost_demand_overhead: float
    realized_transition_demand_overhead: int
    onset_beacon_left: float
    onset_beacon_forward: float
    onset_beacon_right: float
    onset_max_beacon_signal: float
    onset_mean_beacon_signal: float
    onset_beacon_directional_contrast: float
    pre_seek_beacon_observation_count: int
    pre_seek_recent_mean_beacon_signal: float | None
    pre_seek_recent_max_beacon_signal: float | None
    pre_seek_beacon_strength_trend: float | None
    pass_through_count: int
    had_pass_through: bool


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
    acquired_count: int
    terminated_before_acquisition_count: int
    horizon_censored_count: int
    acquisition_fraction_among_resolved_attempts: float | None
    transitions_from_seek_to_successful_acquisition: tuple[int, ...]
    minimum_energy_during_seek_attempts: tuple[float, ...]
    boundary_clamped_move_forward_count: int
    clamped_move_forward_fraction: float
    longest_clamped_forward_streak: int
    clamped_move_forward_counts_by_mode: tuple[tuple[EXP003Mode, int], ...]
    pass_through_count: int
    explore_station_entry_count: int
    explore_harvested_energy: float


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


@dataclass(slots=True)
class _ActiveSeekAttempt:
    onset_step: int
    normalized_energy_at_onset: float
    station_distance_at_onset: float
    minimum_normalized_energy: float
    transitions_elapsed: int = 0
    outcome: EXP003SeekOutcome | None = None
    normalized_energy_before_acquisition: float | None = None
    boundary_clamp_count: int = 0
    current_boundary_clamp_streak: int = 0
    longest_boundary_clamp_streak: int = 0
    station_distance_at_termination: float | None = None
    station_distance_at_horizon: float | None = None
    distance_to_charging_boundary: float = 0.0
    optimistic_minimum_forward_transitions: int = 0
    optimistic_onset_reserve_threshold: float = 0.0
    available_onset_energy_above_failure: float = 0.0
    optimistic_reserve_margin: float = 0.0
    move_forward_count: int = 0
    turn_left_count: int = 0
    turn_right_count: int = 0
    wait_count: int = 0
    nominal_basal_cost_sum: float = 0.0
    nominal_action_cost_sum: float = 0.0
    realized_forward_distance: float = 0.0
    station_distances: list[float] = field(default_factory=list)
    cumulative_inward_radial_progress: float = 0.0
    cumulative_outward_radial_movement: float = 0.0
    forward_actions_reducing_station_distance: int = 0
    forward_actions_increasing_station_distance: int = 0
    current_nonprogress_streak: int = 0
    max_nonprogress_streak: int = 0
    idealized_nominal_straight_line_cost_demand: float = 0.0
    onset_beacon_left: float = 0.0
    onset_beacon_forward: float = 0.0
    onset_beacon_right: float = 0.0
    onset_max_beacon_signal: float = 0.0
    onset_mean_beacon_signal: float = 0.0
    onset_beacon_directional_contrast: float = 0.0
    pre_seek_beacon_observation_count: int = 0
    pre_seek_recent_mean_beacon_signal: float | None = None
    pre_seek_recent_max_beacon_signal: float | None = None
    pre_seek_beacon_strength_trend: float | None = None
    pass_through_count: int = 0


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
    controller_observation_history: list[StationObservation] = []
    seek_attempts: list[EXP003SeekAttempt] = []
    active: _ActiveSeekAttempt | None = None
    total_distance = 0.0
    explore_actions = 0
    explore_distance = 0.0
    total_charged = 0.0
    station_entries = 0
    explore_station_entries = 0
    explore_harvested_energy = 0.0
    transitions_on_charger = 0
    move_forward_actions = 0
    boundary_clamped_move_forward_count = 0
    boundary_clamp_streak = 0
    longest_boundary_clamp_streak = 0
    clamped_move_forward_counts_by_mode = {
        mode: 0 for mode in EXP003Mode
    }
    pass_through_count = 0
    minimum_energy = _normalized_energy(
        episode.initial_state.actual_energy, environment_config
    )

    for transition in episode.transitions:
        controller_observation = transition.controller_visible.observation
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
        boundary_clamped = _is_boundary_clamped(evaluator, environment_config)
        if evaluator.action is Action.MOVE_FORWARD:
            move_forward_actions += 1
        if boundary_clamped:
            boundary_clamped_move_forward_count += 1
            boundary_clamp_streak += 1
            longest_boundary_clamp_streak = max(
                longest_boundary_clamp_streak, boundary_clamp_streak
            )
            clamped_move_forward_counts_by_mode[evaluator.controller_mode] += 1
        else:
            boundary_clamp_streak = 0
        pass_through = _is_outside_pass_through(
            evaluator, episode.initial_state.station_center, environment_config
        )
        if pass_through:
            if evaluator.harvested_energy != 0.0:
                raise ValueError("charger pass-through must harvest exactly zero")
            pass_through_count += 1
        if evaluator.charging_contact_after:
            transitions_on_charger += 1
        if not evaluator.charging_contact_before and evaluator.charging_contact_after:
            station_entries += 1
            if evaluator.controller_mode is EXP003Mode.EXPLORE:
                explore_station_entries += 1

        if evaluator.controller_mode is EXP003Mode.EXPLORE:
            explore_actions += 1
            explore_harvested_energy += evaluator.harvested_energy
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
            station_distance_at_onset = math.dist(
                evaluator.position_before, episode.initial_state.station_center
            )
            feasibility = _seek_feasibility_metrics(
                actual_energy_at_onset=evaluator.actual_energy_before,
                station_distance_at_onset=station_distance_at_onset,
                config=environment_config,
            )
            beacon_metrics = _seek_beacon_metrics(
                controller_observation,
                controller_observation_history,
            )
            idealized_nominal_cost_demand = (
                feasibility.optimistic_minimum_forward_transitions
                * (
                    environment_config.energy.basal_cost
                    + environment_config.movement_cost
                )
            )
            active = _ActiveSeekAttempt(
                onset_step=evaluator.step_index,
                normalized_energy_at_onset=normalized_before,
                station_distance_at_onset=station_distance_at_onset,
                minimum_normalized_energy=normalized_before,
                distance_to_charging_boundary=(
                    feasibility.distance_to_charging_boundary
                ),
                optimistic_minimum_forward_transitions=(
                    feasibility.optimistic_minimum_forward_transitions
                ),
                optimistic_onset_reserve_threshold=(
                    feasibility.optimistic_onset_reserve_threshold
                ),
                available_onset_energy_above_failure=(
                    feasibility.available_onset_energy_above_failure
                ),
                optimistic_reserve_margin=feasibility.optimistic_reserve_margin,
                station_distances=[station_distance_at_onset],
                idealized_nominal_straight_line_cost_demand=(
                    idealized_nominal_cost_demand
                ),
                onset_beacon_left=beacon_metrics.onset_beacon_left,
                onset_beacon_forward=beacon_metrics.onset_beacon_forward,
                onset_beacon_right=beacon_metrics.onset_beacon_right,
                onset_max_beacon_signal=beacon_metrics.onset_max_beacon_signal,
                onset_mean_beacon_signal=beacon_metrics.onset_mean_beacon_signal,
                onset_beacon_directional_contrast=(
                    beacon_metrics.onset_beacon_directional_contrast
                ),
                pre_seek_beacon_observation_count=(
                    beacon_metrics.pre_seek_beacon_observation_count
                ),
                pre_seek_recent_mean_beacon_signal=(
                    beacon_metrics.pre_seek_recent_mean_beacon_signal
                ),
                pre_seek_recent_max_beacon_signal=(
                    beacon_metrics.pre_seek_recent_max_beacon_signal
                ),
                pre_seek_beacon_strength_trend=(
                    beacon_metrics.pre_seek_beacon_strength_trend
                ),
            )

        if active is not None:
            active.transitions_elapsed = (
                evaluator.step_index - active.onset_step + 1
            )
            active.nominal_basal_cost_sum += evaluator.basal_cost
            active.nominal_action_cost_sum += evaluator.action_cost
            station_distance_before = math.dist(
                evaluator.position_before, episode.initial_state.station_center
            )
            station_distance_after = math.dist(
                evaluator.position_after, episode.initial_state.station_center
            )
            radial_progress = station_distance_before - station_distance_after
            active.station_distances.append(station_distance_after)
            active.cumulative_inward_radial_progress += max(
                0.0, radial_progress
            )
            active.cumulative_outward_radial_movement += max(
                0.0, -radial_progress
            )
            if radial_progress <= 0.0:
                active.current_nonprogress_streak += 1
                active.max_nonprogress_streak = max(
                    active.max_nonprogress_streak,
                    active.current_nonprogress_streak,
                )
            else:
                active.current_nonprogress_streak = 0
            if evaluator.action is Action.MOVE_FORWARD:
                active.move_forward_count += 1
                active.realized_forward_distance += math.dist(
                    evaluator.position_before, evaluator.position_after
                )
                if radial_progress > 0.0:
                    active.forward_actions_reducing_station_distance += 1
                elif radial_progress < 0.0:
                    active.forward_actions_increasing_station_distance += 1
            elif evaluator.action is Action.TURN_LEFT:
                active.turn_left_count += 1
            elif evaluator.action is Action.TURN_RIGHT:
                active.turn_right_count += 1
            elif evaluator.action is Action.WAIT:
                active.wait_count += 1
            if pass_through:
                active.pass_through_count += 1
            active.minimum_normalized_energy = min(
                active.minimum_normalized_energy, normalized_before, normalized_after
            )
            if boundary_clamped:
                active.boundary_clamp_count += 1
                active.current_boundary_clamp_streak += 1
                active.longest_boundary_clamp_streak = max(
                    active.longest_boundary_clamp_streak,
                    active.current_boundary_clamp_streak,
                )
            else:
                active.current_boundary_clamp_streak = 0
            if evaluator.charging_contact_after:
                active.outcome = EXP003SeekOutcome.ACQUIRED
                # Acquisition is the start of this atomic transition. The
                # charging input is applied after this pre-transition reading.
                active.normalized_energy_before_acquisition = normalized_before
                seek_attempts.append(_freeze_seek_attempt(active))
                active = None
            elif evaluator.terminated:
                active.outcome = EXP003SeekOutcome.TERMINATED_BEFORE_ACQUISITION
                active.station_distance_at_termination = math.dist(
                    evaluator.position_after, episode.initial_state.station_center
                )
                seek_attempts.append(_freeze_seek_attempt(active))
                active = None
            elif evaluator.truncated:
                active.outcome = EXP003SeekOutcome.HORIZON_CENSORED
                active.station_distance_at_horizon = math.dist(
                    evaluator.position_after, episode.initial_state.station_center
                )
                seek_attempts.append(_freeze_seek_attempt(active))
                active = None

        modes.append(evaluator.controller_mode)
        controller_observation_history.append(controller_observation)

    if active is not None:
        last_evaluator = episode.transitions[-1].privileged_evaluator
        if last_evaluator.terminated or not last_evaluator.truncated:
            raise ValueError(
                "active SEEK attempt ended without genuine horizon truncation"
            )
        active.outcome = EXP003SeekOutcome.HORIZON_CENSORED
        last_position = last_evaluator.position_after
        active.station_distance_at_horizon = math.dist(
            last_position, episode.initial_state.station_center
        )
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
    acquired_count = sum(
        attempt.outcome is EXP003SeekOutcome.ACQUIRED for attempt in seek_attempts
    )
    terminated_count = sum(
        attempt.outcome is EXP003SeekOutcome.TERMINATED_BEFORE_ACQUISITION
        for attempt in seek_attempts
    )
    censored_count = sum(
        attempt.outcome is EXP003SeekOutcome.HORIZON_CENSORED
        for attempt in seek_attempts
    )
    resolved_count = acquired_count + terminated_count
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
        seek_attempts_reaching_charger=acquired_count,
        seek_attempts_reaching_charger_fraction=(
            acquired_count / len(seek_attempts) if seek_attempts else 0.0
        ),
        acquired_count=acquired_count,
        terminated_before_acquisition_count=terminated_count,
        horizon_censored_count=censored_count,
        acquisition_fraction_among_resolved_attempts=(
            acquired_count / resolved_count if resolved_count else None
        ),
        transitions_from_seek_to_successful_acquisition=transitions_to_success,
        minimum_energy_during_seek_attempts=tuple(
            attempt.minimum_normalized_energy for attempt in seek_attempts
        ),
        boundary_clamped_move_forward_count=boundary_clamped_move_forward_count,
        clamped_move_forward_fraction=(
            boundary_clamped_move_forward_count / move_forward_actions
            if move_forward_actions
            else 0.0
        ),
        longest_clamped_forward_streak=longest_boundary_clamp_streak,
        clamped_move_forward_counts_by_mode=tuple(
            (mode, count)
            for mode, count in clamped_move_forward_counts_by_mode.items()
            if count
        ),
        pass_through_count=pass_through_count,
        explore_station_entry_count=explore_station_entries,
        explore_harvested_energy=explore_harvested_energy,
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


def _seek_beacon_metrics(
    observation: StationObservation,
    prior_observations: Sequence[StationObservation],
) -> _EXP003SeekBeaconMetrics:
    """Summarize only recorded controller-visible beacon observations."""
    onset_signals = observation.beacon.as_tuple()
    onset_max = max(onset_signals)
    onset_mean = sum(onset_signals) / len(onset_signals)
    recent = tuple(prior_observations[-5:])
    recent_strengths = tuple(
        sum(previous.beacon.as_tuple()) / 3.0 for previous in recent
    )
    recent_maxima = tuple(max(previous.beacon.as_tuple()) for previous in recent)
    recent_count = len(recent)
    if recent_count:
        recent_mean = sum(recent_strengths) / recent_count
        recent_max = max(recent_maxima)
    else:
        recent_mean = None
        recent_max = None
    trend = (
        (recent_strengths[-1] - recent_strengths[0]) / (recent_count - 1)
        if recent_count >= 2
        else None
    )
    return _EXP003SeekBeaconMetrics(
        onset_beacon_left=observation.beacon.left,
        onset_beacon_forward=observation.beacon.forward,
        onset_beacon_right=observation.beacon.right,
        onset_max_beacon_signal=onset_max,
        onset_mean_beacon_signal=onset_mean,
        onset_beacon_directional_contrast=onset_max - min(onset_signals),
        pre_seek_beacon_observation_count=recent_count,
        pre_seek_recent_mean_beacon_signal=recent_mean,
        pre_seek_recent_max_beacon_signal=recent_max,
        pre_seek_beacon_strength_trend=trend,
    )


def _seek_feasibility_metrics(
    *,
    actual_energy_at_onset: float,
    station_distance_at_onset: float,
    config: EXP003StationConfig,
) -> EXP003SeekFeasibilityMetrics:
    """Calculate an evaluator-only optimistic charge-aware SEEK bound.

    This idealized geometric bound assumes perfect straight-line progress,
    ignores turning and steering inefficiency, and includes the existing
    same-transition acquisition charge on the final forward transition. A
    positive margin does not prove that the real controller will acquire.
    """
    distance_to_boundary = max(
        0.0, station_distance_at_onset - config.charging_radius
    )
    if distance_to_boundary == 0.0:
        minimum_forward_transitions = 0
    else:
        if config.movement_distance <= 0.0:
            raise ValueError(
                "movement_distance must be positive for SEEK feasibility metrics"
            )
        minimum_forward_transitions = math.ceil(
            distance_to_boundary / config.movement_distance
        )
    q = config.energy.basal_cost + config.movement_cost
    h = config.charge_rate
    if minimum_forward_transitions == 0:
        optimistic_onset_reserve_threshold = 0.0
    else:
        optimistic_onset_reserve_threshold = (
            (minimum_forward_transitions - 1) * q + max(0.0, q - h)
        )
    available_energy = actual_energy_at_onset - config.energy.failure_boundary
    return EXP003SeekFeasibilityMetrics(
        distance_to_charging_boundary=distance_to_boundary,
        optimistic_minimum_forward_transitions=minimum_forward_transitions,
        optimistic_onset_reserve_threshold=optimistic_onset_reserve_threshold,
        available_onset_energy_above_failure=available_energy,
        optimistic_reserve_margin=(
            available_energy - optimistic_onset_reserve_threshold
        ),
    )


def _freeze_seek_attempt(values: _ActiveSeekAttempt) -> EXP003SeekAttempt:
    if values.outcome is None:
        raise ValueError("SEEK attempt outcome is required")
    turn_count = values.turn_left_count + values.turn_right_count
    ideal_forward_transitions = values.optimistic_minimum_forward_transitions
    idealized_cost_demand = values.idealized_nominal_straight_line_cost_demand
    station_distance_trajectory = tuple(values.station_distances)
    if not station_distance_trajectory:
        raise ValueError("SEEK station-distance trajectory is required")
    onset_boundary_distance = values.distance_to_charging_boundary
    move_forward_count = values.move_forward_count
    return EXP003SeekAttempt(
        onset_step=values.onset_step,
        normalized_energy_at_onset=values.normalized_energy_at_onset,
        station_distance_at_onset=values.station_distance_at_onset,
        outcome=values.outcome,
        transitions_elapsed=values.transitions_elapsed,
        reached_charging_contact=values.outcome is EXP003SeekOutcome.ACQUIRED,
        transitions_to_charging_contact=(
            values.transitions_elapsed
            if values.outcome is EXP003SeekOutcome.ACQUIRED
            else None
        ),
        normalized_energy_before_acquisition=(
            values.normalized_energy_before_acquisition
            if values.outcome is EXP003SeekOutcome.ACQUIRED
            else None
        ),
        minimum_normalized_energy=values.minimum_normalized_energy,
        boundary_clamp_count=values.boundary_clamp_count,
        had_boundary_clamp=values.boundary_clamp_count > 0,
        longest_boundary_clamp_streak=values.longest_boundary_clamp_streak,
        station_distance_at_termination=values.station_distance_at_termination,
        station_distance_at_horizon=values.station_distance_at_horizon,
        distance_to_charging_boundary=values.distance_to_charging_boundary,
        optimistic_minimum_forward_transitions=(
            values.optimistic_minimum_forward_transitions
        ),
        optimistic_onset_reserve_threshold=(
            values.optimistic_onset_reserve_threshold
        ),
        available_onset_energy_above_failure=(
            values.available_onset_energy_above_failure
        ),
        optimistic_reserve_margin=values.optimistic_reserve_margin,
        move_forward_count=values.move_forward_count,
        turn_left_count=values.turn_left_count,
        turn_right_count=values.turn_right_count,
        wait_count=values.wait_count,
        nominal_basal_cost_sum=values.nominal_basal_cost_sum,
        nominal_action_cost_sum=values.nominal_action_cost_sum,
        nominal_total_cost_sum=(
            values.nominal_basal_cost_sum + values.nominal_action_cost_sum
        ),
        realized_forward_distance=values.realized_forward_distance,
        turn_count=turn_count,
        turn_fraction=(turn_count / values.transitions_elapsed),
        actual_forward_to_ideal_transition_ratio=(
            move_forward_count / ideal_forward_transitions
            if ideal_forward_transitions
            else None
        ),
        realized_path_to_onset_boundary_ratio=(
            values.realized_forward_distance / onset_boundary_distance
            if onset_boundary_distance > 0.0
            else None
        ),
        station_distance_trajectory=station_distance_trajectory,
        net_radial_progress_toward_station=(
            station_distance_trajectory[0] - station_distance_trajectory[-1]
        ),
        cumulative_inward_radial_progress=(
            values.cumulative_inward_radial_progress
        ),
        cumulative_outward_radial_movement=(
            values.cumulative_outward_radial_movement
        ),
        forward_actions_reducing_station_distance=(
            values.forward_actions_reducing_station_distance
        ),
        forward_actions_increasing_station_distance=(
            values.forward_actions_increasing_station_distance
        ),
        forward_inward_progress_fraction=(
            values.forward_actions_reducing_station_distance / move_forward_count
            if move_forward_count
            else None
        ),
        forward_outward_progress_fraction=(
            values.forward_actions_increasing_station_distance / move_forward_count
            if move_forward_count
            else None
        ),
        max_consecutive_transitions_without_net_progress_toward_station=(
            values.max_nonprogress_streak
        ),
        idealized_nominal_straight_line_cost_demand=idealized_cost_demand,
        nominal_cost_demand_overhead=(
            values.nominal_basal_cost_sum
            + values.nominal_action_cost_sum
            - idealized_cost_demand
        ),
        realized_transition_demand_overhead=(
            values.transitions_elapsed - ideal_forward_transitions
        ),
        onset_beacon_left=values.onset_beacon_left,
        onset_beacon_forward=values.onset_beacon_forward,
        onset_beacon_right=values.onset_beacon_right,
        onset_max_beacon_signal=values.onset_max_beacon_signal,
        onset_mean_beacon_signal=values.onset_mean_beacon_signal,
        onset_beacon_directional_contrast=values.onset_beacon_directional_contrast,
        pre_seek_beacon_observation_count=values.pre_seek_beacon_observation_count,
        pre_seek_recent_mean_beacon_signal=(
            values.pre_seek_recent_mean_beacon_signal
        ),
        pre_seek_recent_max_beacon_signal=values.pre_seek_recent_max_beacon_signal,
        pre_seek_beacon_strength_trend=values.pre_seek_beacon_strength_trend,
        pass_through_count=values.pass_through_count,
        had_pass_through=values.pass_through_count > 0,
    )


def _is_boundary_clamped(
    evaluator: EXP003EvaluatorStep,
    config: EXP003StationConfig,
) -> bool:
    """Classify a forward step whose unconstrained endpoint left the world."""
    if evaluator.action is not Action.MOVE_FORWARD:
        return False
    proposed = (
        evaluator.position_before[0]
        + config.movement_distance * math.cos(evaluator.heading),
        evaluator.position_before[1]
        + config.movement_distance * math.sin(evaluator.heading),
    )
    outside = any(
        proposed_coordinate < lower or proposed_coordinate > upper
        for proposed_coordinate, lower, upper in zip(
            proposed, config.world_min, config.world_max
        )
    )
    if not outside:
        return False
    return proposed != evaluator.position_after


def _is_outside_pass_through(
    evaluator: EXP003EvaluatorStep,
    station_center: tuple[float, float],
    config: EXP003StationConfig,
) -> bool:
    """Classify an outside-to-outside forward segment crossing the charger."""
    if (
        evaluator.action is not Action.MOVE_FORWARD
        or evaluator.charging_contact_before
        or evaluator.charging_contact_after
    ):
        return False
    start = evaluator.position_before
    end = evaluator.position_after
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    denominator = dx * dx + dy * dy
    if denominator == 0.0:
        return False
    projection = (
        (station_center[0] - start[0]) * dx
        + (station_center[1] - start[1]) * dy
    ) / denominator
    projection = min(1.0, max(0.0, projection))
    closest = (
        start[0] + projection * dx,
        start[1] + projection * dy,
    )
    return math.dist(closest, station_center) <= config.charging_radius


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
