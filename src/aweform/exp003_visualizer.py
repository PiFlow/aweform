"""Development-only matched FIELD_B50/STATION_B50 visualization."""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass, replace
from typing import Any, Sequence

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation
from matplotlib.figure import Figure
from matplotlib.patches import Circle

from .env import Action, AweformEnvConfig
from .exp001 import EXP001Mode, InteroceptiveObservation
from .exp002_runner import EXP002EpisodeRecord
from .exp003 import EXP003Mode, EXP003StationConfig, beacon_signal
from .exp003_runner import (
    EXP003DevelopmentComparison,
    EXP003EpisodeDiagnostics,
    EXP003EpisodeRecord,
    exp003_coverage_grid_states,
    run_exp003_development_comparison,
)


@dataclass(frozen=True, slots=True)
class EXP003VisualizationFrame:
    """One evaluator state plus the next controller-visible decision."""

    step_index: int
    x: float
    y: float
    heading: float
    path: tuple[tuple[float, float], ...]
    mode: str
    next_action: Action | None
    actual_normalized_energy: float
    controller_visible_energy: float | None
    beacon_left: float | None
    beacon_forward: float | None
    beacon_right: float | None
    charging_contact: bool | None
    visited_cell_count: int
    coverage_fraction: float
    station_distance: float | None
    terminal_status: str
    is_padded: bool = False


@dataclass(frozen=True, slots=True)
class EXP003VisualizationData:
    """All data needed for the aligned two-panel development view."""

    seed: int
    world_min: tuple[float, float]
    world_max: tuple[float, float]
    station_center: tuple[float, float]
    charging_radius: float
    field_frames: tuple[EXP003VisualizationFrame, ...]
    station_frames: tuple[EXP003VisualizationFrame, ...]
    station_diagnostics: EXP003EpisodeDiagnostics


def build_exp003_visualization_frames(
    result: EXP003DevelopmentComparison,
    seed: int | None = None,
) -> EXP003VisualizationData:
    """Build evaluator-side frames without executing or modifying a run."""
    selected_seed = _select_seed(result, seed)
    field_index = result.development_seeds.index(selected_seed)
    field = result.field_b50_episodes[field_index]
    station = result.station_b50_episodes[field_index]
    diagnostics = result.station_b50_diagnostics[field_index]
    return EXP003VisualizationData(
        seed=selected_seed,
        world_min=result.station_environment_config.world_min,
        world_max=result.station_environment_config.world_max,
        station_center=station.initial_state.station_center,
        charging_radius=result.station_environment_config.charging_radius,
        field_frames=_build_field_frames(field, result.field_environment_config),
        station_frames=_build_station_frames(
            station, result.station_environment_config, diagnostics
        ),
        station_diagnostics=diagnostics,
    )


def build_exp003_visualization_figure(
    result: EXP003DevelopmentComparison,
    seed: int | None = None,
) -> tuple[Figure, FuncAnimation]:
    """Create a two-panel animated development/sanity-check figure."""
    data = build_exp003_visualization_frames(result, seed)
    figure, axes = plt.subplots(1, 2, figsize=(13, 6), constrained_layout=True)
    figure.suptitle(
        "EXP-003 DEVELOPMENT VISUALIZATION — FIELD_B50 vs STATION_B50\n"
        "DESCRIPTIVE / SANITY CHECK ONLY — NOT CALIBRATION OR CONFIRMATORY EVIDENCE",
        fontsize=12,
    )
    field_axis, station_axis = axes
    field_axis.set_title("FIELD_B50 — historical EXP-002 B50 reference")
    station_axis.set_title("STATION_B50 — localized charging development")
    for axis in axes:
        axis.set_xlim(data.world_min[0], data.world_max[0])
        axis.set_ylim(data.world_min[1], data.world_max[1])
        axis.set_aspect("equal")
        axis.set_xlabel("x")
        axis.set_ylabel("y")

    field_episode = result.field_b50_episodes[result.development_seeds.index(data.seed)]
    source = field_episode.initial_state.source_positions[0]
    grid = np.linspace(data.world_min[0], data.world_max[0], 50)
    field_values = np.asarray(
        [
            [
                _field_intensity(point, source, result.field_environment_config)
                for point in ((x, y) for x in grid for y in [grid_value])
            ]
            for grid_value in grid
        ],
        dtype=float,
    )
    field_axis.imshow(
        field_values,
        origin="lower",
        extent=(
            data.world_min[0],
            data.world_max[0],
            data.world_min[1],
            data.world_max[1],
        ),
        cmap="YlGn",
        alpha=0.35,
    )
    field_axis.scatter(
        *source, marker="*", s=130, color="darkgreen", label="field source"
    )

    beacon_values = np.asarray(
        [
            [beacon_signal(math.dist((x, y), data.station_center)) for x in grid]
            for y in grid
        ],
        dtype=float,
    )
    station_axis.imshow(
        beacon_values,
        origin="lower",
        extent=(
            data.world_min[0],
            data.world_max[0],
            data.world_min[1],
            data.world_max[1],
        ),
        cmap="Blues",
        alpha=0.18,
    )
    station_axis.add_patch(
        Circle(
            data.station_center,
            data.charging_radius,
            fill=False,
            linewidth=2.0,
            edgecolor="darkorange",
            label="charging zone",
        )
    )
    station_axis.scatter(
        *data.station_center,
        marker="+",
        s=110,
        color="darkorange",
        label="station centre (evaluator)",
    )
    station_axis.text(
        0.02,
        0.02,
        "blue background = SIGNAL field\norange circle = physical charging zone",
        transform=station_axis.transAxes,
        fontsize=8,
        va="bottom",
    )

    (field_line,) = field_axis.plot([], [], color="black", linewidth=1.2)
    (field_body,) = field_axis.plot([], [], "o", color="black")
    (station_line,) = station_axis.plot([], [], color="black", linewidth=1.2)
    (station_body,) = station_axis.plot([], [], "o", color="black")
    station_probe_lines = [
        station_axis.plot([], [], color=color, linewidth=1.0)[0]
        for color in ("#6a3d9a", "#1f78b4", "#e31a1c")
    ]
    field_text = field_axis.text(
        0.02, 0.98, "", transform=field_axis.transAxes, va="top"
    )
    station_text = station_axis.text(
        0.02, 0.98, "", transform=station_axis.transAxes, va="top"
    )
    field_frames = _pad_frames(data.field_frames, len(data.station_frames))
    station_frames = _pad_frames(data.station_frames, len(data.field_frames))
    frame_count = max(len(field_frames), len(station_frames))

    def update(frame_index: int) -> tuple[Any, ...]:
        field_frame = field_frames[frame_index]
        station_frame = station_frames[frame_index]
        _update_body(field_line, field_body, field_frame)
        _update_body(station_line, station_body, station_frame)
        station_frame_geometry = _probe_geometry(station_frame, data)
        for line, endpoint in zip(station_probe_lines, station_frame_geometry):
            line.set_data(
                [station_frame.x, endpoint[0]],
                [station_frame.y, endpoint[1]],
            )
        field_text.set_text(_format_field_frame(field_frame))
        station_text.set_text(_format_station_frame(station_frame))
        return (
            field_line,
            field_body,
            station_line,
            station_body,
            *station_probe_lines,
            field_text,
            station_text,
        )

    animation = FuncAnimation(
        figure,
        update,
        frames=frame_count,
        interval=80,
        blit=False,
        repeat=False,
    )
    field_axis.legend(loc="lower right", fontsize=8)
    station_axis.legend(loc="lower right", fontsize=8)
    return figure, animation


def show_exp003_development_visualization(
    result: EXP003DevelopmentComparison,
    seed: int | None = None,
) -> None:
    """Show the development visualization."""
    build_exp003_visualization_figure(result, seed)
    plt.show()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Visualize EXP-003 development")
    parser.add_argument("--seed", type=_non_negative_int, default=18003)
    args = parser.parse_args(argv)
    result = run_exp003_development_comparison([args.seed])
    show_exp003_development_visualization(result, seed=args.seed)
    return 0


def _build_field_frames(
    episode: EXP002EpisodeRecord,
    config: AweformEnvConfig,
) -> tuple[EXP003VisualizationFrame, ...]:
    path = [episode.initial_state.position]
    frames: list[EXP003VisualizationFrame] = []
    for index in range(len(episode.transitions) + 1):
        if index > 0:
            path.append(
                episode.transitions[index - 1].privileged_evaluator.position_after
            )
        evaluator = (
            None if index == 0 else episode.transitions[index - 1].privileged_evaluator
        )
        next_transition = (
            None if index >= len(episode.transitions) else episode.transitions[index]
        )
        next_observation = (
            None
            if next_transition is None
            else next_transition.controller_visible.observation
        )
        actual_energy = (
            episode.initial_state.actual_energy
            if evaluator is None
            else evaluator.actual_energy_after
        )
        controller_energy = (
            None
            if not isinstance(next_observation, InteroceptiveObservation)
            else next_observation.energy
        )
        mode = EXP001Mode.EXPLORE if evaluator is None else evaluator.controller_mode
        frames.append(
            EXP003VisualizationFrame(
                step_index=index,
                x=path[-1][0],
                y=path[-1][1],
                heading=(
                    episode.initial_state.heading
                    if evaluator is None
                    else evaluator.heading
                ),
                path=tuple(path),
                mode=mode.value,
                next_action=None
                if next_transition is None
                else next_transition.privileged_evaluator.action,
                actual_normalized_energy=_normalized_energy(actual_energy, config),
                controller_visible_energy=controller_energy,
                beacon_left=None,
                beacon_forward=None,
                beacon_right=None,
                charging_contact=None,
                visited_cell_count=0,
                coverage_fraction=0.0,
                station_distance=None,
                terminal_status=_terminal_status(evaluator),
            )
        )
    return tuple(frames)


def _build_station_frames(
    episode: EXP003EpisodeRecord,
    config: EXP003StationConfig,
    diagnostics: EXP003EpisodeDiagnostics,
) -> tuple[EXP003VisualizationFrame, ...]:
    path = [episode.initial_state.position]
    coverage_states = exp003_coverage_grid_states(episode, config)
    frames: list[EXP003VisualizationFrame] = []
    for index in range(len(episode.transitions) + 1):
        if index > 0:
            path.append(
                episode.transitions[index - 1].privileged_evaluator.position_after
            )
        evaluator = (
            None if index == 0 else episode.transitions[index - 1].privileged_evaluator
        )
        next_transition = (
            None if index >= len(episode.transitions) else episode.transitions[index]
        )
        next_observation = (
            None
            if next_transition is None
            else next_transition.controller_visible.observation
        )
        actual_energy = (
            episode.initial_state.actual_energy
            if evaluator is None
            else evaluator.actual_energy_after
        )
        mode = EXP003Mode.EXPLORE if evaluator is None else evaluator.controller_mode
        station_distance = math.dist(path[-1], episode.initial_state.station_center)
        frames.append(
            EXP003VisualizationFrame(
                step_index=index,
                x=path[-1][0],
                y=path[-1][1],
                heading=episode.initial_state.heading
                if evaluator is None
                else evaluator.heading,
                path=tuple(path),
                mode=mode.value,
                next_action=None
                if next_transition is None
                else next_transition.privileged_evaluator.action,
                actual_normalized_energy=_normalized_energy(actual_energy, config),
                controller_visible_energy=None
                if next_observation is None
                else next_observation.energy,
                beacon_left=None
                if next_observation is None
                else next_observation.beacon.left,
                beacon_forward=None
                if next_observation is None
                else next_observation.beacon.forward,
                beacon_right=None
                if next_observation is None
                else next_observation.beacon.right,
                charging_contact=None
                if next_observation is None
                else next_observation.beacon.charging_contact,
                visited_cell_count=coverage_states[index].visited_cell_count,
                coverage_fraction=coverage_states[index].coverage_fraction,
                station_distance=station_distance,
                terminal_status=_terminal_status(evaluator),
            )
        )
    if diagnostics.capped_lifespan != len(episode.transitions):
        raise ValueError("station diagnostics do not match episode transitions")
    return tuple(frames)


def _select_seed(result: EXP003DevelopmentComparison, seed: int | None) -> int:
    if not result.development_seeds:
        raise ValueError("comparison contains no development seeds")
    selected = result.development_seeds[0] if seed is None else seed
    if selected not in result.development_seeds:
        raise ValueError(f"seed {selected} is not present in the comparison")
    return selected


def _field_intensity(
    point: tuple[float, float],
    source: tuple[float, float],
    config: AweformEnvConfig,
) -> float:
    distance_squared = math.dist(point, source) ** 2
    return config.resource_peak_intensity * math.exp(
        -0.5 * distance_squared / config.resource_length_scale**2
    )


def _normalized_energy(
    actual_energy: float, config: AweformEnvConfig | EXP003StationConfig
) -> float:
    return (actual_energy - config.energy.failure_boundary) / (
        config.energy.maximum_energy - config.energy.failure_boundary
    )


def _update_body(line: Any, body: Any, frame: EXP003VisualizationFrame) -> None:
    line.set_data(
        [point[0] for point in frame.path], [point[1] for point in frame.path]
    )
    body.set_data([frame.x], [frame.y])


def _probe_geometry(
    frame: EXP003VisualizationFrame,
    data: EXP003VisualizationData,
) -> tuple[tuple[float, float], ...]:
    del data
    angles = (frame.heading + math.pi / 4, frame.heading, frame.heading - math.pi / 4)
    return tuple(
        (frame.x + 0.1 * math.cos(angle), frame.y + 0.1 * math.sin(angle))
        for angle in angles
    )


def _format_field_frame(frame: EXP003VisualizationFrame) -> str:
    action = "—" if frame.next_action is None else frame.next_action.name
    energy_access = (
        "controller-visible"
        if frame.controller_visible_energy is not None
        else "EVALUATOR ONLY — no next controller observation"
    )
    return (
        f"step {frame.step_index} | mode {frame.mode}\n"
        f"normalized energy: {frame.actual_normalized_energy:.3f} "
        f"[{exp003_energy_visibility_label(frame)}]\n"
        f"next action: {action}\n"
        f"energy access: {energy_access}"
    )


def _format_station_frame(frame: EXP003VisualizationFrame) -> str:
    action = "—" if frame.next_action is None else frame.next_action.name
    contact = "—" if frame.charging_contact is None else str(frame.charging_contact)
    beacon = (
        "— / — / —"
        if frame.beacon_left is None
        else (
            f"{frame.beacon_left:.3f} / {frame.beacon_forward:.3f} / "
            f"{frame.beacon_right:.3f}"
        )
    )
    distance = (
        "—" if frame.station_distance is None else f"{frame.station_distance:.3f}"
    )
    return (
        f"step {frame.step_index} | mode {frame.mode}\n"
        f"normalized energy: {frame.actual_normalized_energy:.3f} "
        f"[{exp003_energy_visibility_label(frame)}]\n"
        f"beacon L/F/R: {beacon}\n"
        f"charging_contact: {contact}\n"
        f"coverage: {frame.visited_cell_count} cells ({frame.coverage_fraction:.3f})\n"
        f"station distance: {distance} [EVALUATOR ONLY]\n"
        f"next action: {action}"
    )


def _terminal_status(evaluator: Any) -> str:
    if evaluator is None:
        return "running"
    if evaluator.terminated and evaluator.truncated:
        raise ValueError("a transition cannot be both terminated and truncated")
    if evaluator.terminated:
        return "terminated"
    if evaluator.truncated:
        return "truncated"
    return "running"


def exp003_energy_visibility_label(frame: EXP003VisualizationFrame) -> str:
    """Label actual energy according to the next-observation boundary."""
    if frame.controller_visible_energy is None:
        return "EVALUATOR ONLY — no next controller observation"
    return "CTRL + EVAL"


def _pad_frames(
    frames: tuple[EXP003VisualizationFrame, ...], maximum_length: int
) -> tuple[EXP003VisualizationFrame, ...]:
    last = frames[-1]
    return frames + tuple(
        replace(
            last,
            is_padded=True,
            next_action=None,
            controller_visible_energy=None,
            beacon_left=None,
            beacon_forward=None,
            beacon_right=None,
            charging_contact=None,
        )
        for _ in range(maximum_length - len(frames))
    )


def _non_negative_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be an integer") from error
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
