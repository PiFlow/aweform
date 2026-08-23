"""Development-only matched STATION_B50/STATION_B50_TREND visualization."""

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

from .exp003 import EXP003Mode, EXP003SeekTrigger, beacon_signal
from .exp003_runner import (
    EXP003EpisodeRecord,
    EXP003StationTrendComparison,
    EXP003TransitionRecord,
    run_exp003_station_trend_comparison,
)
from .exp003_visualizer import (
    EXP003VisualizationFrame,
    _build_station_frames,
    _pad_frames,
)

_ACTIVE_ANIMATIONS: list[FuncAnimation] = []

# The shared frame type carries optional trend diagnostics. This alias keeps
# the separate visualizer's public data names self-describing while preserving
# one implementation of path, coverage, terminal, and energy frame building.
EXP003TrendVisualizationFrame = EXP003VisualizationFrame


@dataclass(frozen=True, slots=True)
class EXP003TrendVisualizationData:
    """All data needed for the aligned two-panel station-policy view."""

    seed: int
    world_min: tuple[float, float]
    world_max: tuple[float, float]
    station_center: tuple[float, float]
    charging_radius: float
    beacon_scale: float
    probe_distance: float
    sensor_angle: float
    historical_frames: tuple[EXP003VisualizationFrame, ...]
    trend_frames: tuple[EXP003VisualizationFrame, ...]


def build_exp003_trend_visualization_frames(
    result: EXP003StationTrendComparison,
    seed: int | None = None,
) -> EXP003TrendVisualizationData:
    """Build paired frames from recorded trajectories without rerunning them."""
    selected_seed = _select_seed(result, seed)
    index = result.development_seeds.index(selected_seed)
    historical = result.station_b50_episodes[index]
    trend = result.station_b50_trend_episodes[index]
    if historical.environment_seed != trend.environment_seed:
        raise ValueError("matched station episodes must use the same environment seed")
    if historical.initial_state != trend.initial_state:
        raise ValueError("matched station episodes must share the same initial state")

    config = result.station_environment_config
    historical_frames = _record_temporal_frames(
        _build_station_frames(
            historical,
            config,
            result.station_b50_diagnostics[index],
        ),
        historical,
        history_enabled=False,
    )
    trend_frames = _record_temporal_frames(
        _build_station_frames(
            trend,
            config,
            result.station_b50_trend_diagnostics[index],
        ),
        trend,
        history_enabled=True,
    )
    return EXP003TrendVisualizationData(
        seed=selected_seed,
        world_min=config.world_min,
        world_max=config.world_max,
        station_center=historical.initial_state.station_center,
        charging_radius=config.charging_radius,
        beacon_scale=config.beacon_scale,
        probe_distance=config.probe_distance,
        sensor_angle=config.sensor_angle,
        historical_frames=historical_frames,
        trend_frames=trend_frames,
    )


def build_exp003_trend_visualization_figure(
    result: EXP003StationTrendComparison,
    seed: int | None = None,
) -> tuple[Figure, FuncAnimation]:
    """Create the matched STATION_B50/STATION_B50_TREND animation."""
    data = build_exp003_trend_visualization_frames(result, seed)
    figure, axes = plt.subplots(1, 2, figsize=(15, 7), constrained_layout=True)
    figure.suptitle(
        "EXP-003 DEVELOPMENT VISUALIZATION — STATION_B50 vs "
        "STATION_B50_TREND\n"
        "DESCRIPTIVE / SANITY CHECK ONLY — NOT CALIBRATION OR "
        "CONFIRMATORY EVIDENCE",
        fontsize=12,
    )
    historical_axis, trend_axis = axes
    historical_axis.set_title("LEFT — STATION_B50 (historical)")
    trend_axis.set_title("RIGHT — STATION_B50_TREND (one-step visible beacon history)")
    for axis in axes:
        axis.set_xlim(data.world_min[0], data.world_max[0])
        axis.set_ylim(data.world_min[1], data.world_max[1])
        axis.set_aspect("equal")
        axis.set_xlabel("x")
        axis.set_ylabel("y")

    grid = np.linspace(data.world_min[0], data.world_max[0], 50)
    beacon_values = np.asarray(
        [
            [
                beacon_signal(
                    math.dist((x, y), data.station_center), data.beacon_scale
                )
                for x in grid
            ]
            for y in grid
        ],
        dtype=float,
    )
    for axis in axes:
        axis.imshow(
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
        axis.add_patch(
            Circle(
                data.station_center,
                data.charging_radius,
                fill=False,
                linewidth=2.0,
                edgecolor="darkorange",
                label="charging radius",
            )
        )
        axis.scatter(
            *data.station_center,
            marker="+",
            s=110,
            color="darkorange",
            label="station centre (EVALUATOR ONLY)",
        )
        axis.text(
            0.02,
            0.02,
            "blue = beacon signal field\n"
            "orange = physical charging radius\n"
            "station centre = EVALUATOR ONLY",
            transform=axis.transAxes,
            fontsize=7,
            va="bottom",
        )

    historical_artists = _make_dynamic_artists(historical_axis)
    trend_artists = _make_dynamic_artists(trend_axis)
    historical_text = historical_axis.text(
        0.02, 0.98, "", transform=historical_axis.transAxes, va="top", fontsize=7.5
    )
    trend_text = trend_axis.text(
        0.02, 0.98, "", transform=trend_axis.transAxes, va="top", fontsize=7.5
    )
    historical_frames = _pad_trend_frames(
        data.historical_frames, len(data.trend_frames)
    )
    trend_frames = _pad_trend_frames(data.trend_frames, len(data.historical_frames))
    frame_count = max(len(historical_frames), len(trend_frames))

    def update(frame_index: int) -> tuple[Any, ...]:
        historical_frame = historical_frames[frame_index]
        trend_frame = trend_frames[frame_index]
        _update_dynamic_artists(*historical_artists, historical_frame, data)
        _update_dynamic_artists(*trend_artists, trend_frame, data)
        historical_text.set_text(_format_frame(historical_frame, history_enabled=False))
        trend_text.set_text(_format_frame(trend_frame, history_enabled=True))
        return (*historical_artists, *trend_artists, historical_text, trend_text)

    animation = FuncAnimation(
        figure,
        update,
        frames=frame_count,
        interval=80,
        blit=False,
        repeat=False,
    )
    historical_axis.legend(loc="lower right", fontsize=7)
    trend_axis.legend(loc="lower right", fontsize=7)
    return figure, animation


def show_exp003_trend_visualization(
    result: EXP003StationTrendComparison,
    seed: int | None = None,
) -> None:
    """Show the matched station-policy development visualization."""
    _, animation = build_exp003_trend_visualization_figure(result, seed)
    _ACTIVE_ANIMATIONS.append(animation)
    try:
        plt.show()
    finally:
        _ACTIVE_ANIMATIONS.remove(animation)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Visualize matched EXP-003 station policies"
    )
    parser.add_argument("--seed", type=_non_negative_int, default=18141)
    args = parser.parse_args(argv)
    result = run_exp003_station_trend_comparison([args.seed])
    show_exp003_trend_visualization(result, seed=args.seed)
    return 0


def _record_temporal_frames(
    frames: tuple[EXP003VisualizationFrame, ...],
    episode: EXP003EpisodeRecord,
    *,
    history_enabled: bool,
) -> tuple[EXP003VisualizationFrame, ...]:
    previous_explore_beacon_max: float | None = None
    recorded_frames: list[EXP003VisualizationFrame] = []
    for index, frame in enumerate(frames):
        if index > 0:
            previous_explore_beacon_max = _advance_explore_history(
                episode.transitions[index - 1],
                previous_explore_beacon_max,
                history_enabled=history_enabled,
            )
        transition = (
            None if index >= len(episode.transitions) else episode.transitions[index]
        )
        current, previous, delta, trigger = _next_decision_trace(
            transition,
            previous_explore_beacon_max,
            history_enabled=history_enabled,
        )
        recorded_frames.append(
            replace(
                frame,
                current_beacon_max=current,
                previous_explore_beacon_max=previous,
                beacon_delta=delta,
                seek_trigger=trigger,
            )
        )
    return tuple(recorded_frames)


def _advance_explore_history(
    transition: EXP003TransitionRecord,
    previous_explore_beacon_max: float | None,
    *,
    history_enabled: bool,
) -> float | None:
    if not history_enabled:
        return None
    evaluator = transition.privileged_evaluator
    if evaluator.controller_mode_before_action is EXP003Mode.EXPLORE:
        decision = transition.controller_visible.decision
        if decision.seek_trigger is None:
            return max(transition.controller_visible.observation.beacon.as_tuple())
        return None
    if (
        evaluator.controller_mode_before_action is EXP003Mode.CHARGE
        and evaluator.controller_mode is EXP003Mode.EXPLORE
    ):
        return None
    return previous_explore_beacon_max


def _next_decision_trace(
    transition: EXP003TransitionRecord | None,
    previous_explore_beacon_max: float | None,
    *,
    history_enabled: bool,
) -> tuple[
    float | None,
    float | None,
    float | None,
    EXP003SeekTrigger | None,
]:
    if transition is None:
        return None, None, None, None
    observation = transition.controller_visible.observation
    current_max = max(observation.beacon.as_tuple())
    evaluator = transition.privileged_evaluator
    if evaluator.controller_mode_before_action is not EXP003Mode.EXPLORE:
        return current_max, None, None, None
    previous_max = previous_explore_beacon_max if history_enabled else None
    decision = transition.controller_visible.decision
    delta = None if previous_max is None else current_max - previous_max
    return current_max, previous_max, delta, decision.seek_trigger


def _select_seed(result: EXP003StationTrendComparison, seed: int | None) -> int:
    if not result.development_seeds:
        raise ValueError("comparison contains no development seeds")
    selected = result.development_seeds[0] if seed is None else seed
    if selected not in result.development_seeds:
        raise ValueError(f"seed {selected} is not present in the comparison")
    return selected


def _make_dynamic_artists(axis: Any) -> tuple[Any, Any, Any, list[Any]]:
    (line,) = axis.plot([], [], color="black", linewidth=1.2)
    (body,) = axis.plot([], [], "o", color="black")
    (heading,) = axis.plot([], [], color="#111111", linewidth=2.0)
    probes = [
        axis.plot([], [], color=color, linewidth=1.0, label=f"probe {label}")[0]
        for label, color in zip(
            ("L", "F", "R"), ("#6a3d9a", "#1f78b4", "#e31a1c")
        )
    ]
    return line, body, heading, probes


def _update_dynamic_artists(
    line: Any,
    body: Any,
    heading: Any,
    probes: list[Any],
    frame: EXP003VisualizationFrame,
    data: EXP003TrendVisualizationData,
) -> None:
    line.set_data(
        [point[0] for point in frame.path], [point[1] for point in frame.path]
    )
    body.set_data([frame.x], [frame.y])
    heading_endpoint = (
        frame.x + 0.08 * math.cos(frame.heading),
        frame.y + 0.08 * math.sin(frame.heading),
    )
    heading.set_data([frame.x, heading_endpoint[0]], [frame.y, heading_endpoint[1]])
    angles = (
        frame.heading + data.sensor_angle,
        frame.heading,
        frame.heading - data.sensor_angle,
    )
    for probe, angle in zip(probes, angles):
        endpoint = (
            frame.x + data.probe_distance * math.cos(angle),
            frame.y + data.probe_distance * math.sin(angle),
        )
        probe.set_data([frame.x, endpoint[0]], [frame.y, endpoint[1]])


def _format_frame(
    frame: EXP003VisualizationFrame,
    *,
    history_enabled: bool,
) -> str:
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
    current = (
        "—" if frame.current_beacon_max is None else f"{frame.current_beacon_max:.3f}"
    )
    if history_enabled:
        previous = (
            "—"
            if frame.previous_explore_beacon_max is None
            else f"{frame.previous_explore_beacon_max:.3f}"
        )
        delta = "—" if frame.beacon_delta is None else f"{frame.beacon_delta:+.3f}"
    else:
        previous = "n/a"
        delta = "—"
    trigger = "—" if frame.seek_trigger is None else frame.seek_trigger.name
    distance = (
        "—" if frame.station_distance is None else f"{frame.station_distance:.3f}"
    )
    status = "FROZEN/PADDED" if frame.is_padded else frame.terminal_status.upper()
    return (
        f"step {frame.step_index} | mode {frame.mode}\n"
        f"heading: {math.degrees(frame.heading):.1f}° | next action: {action}\n"
        f"actual normalized energy: {frame.actual_normalized_energy:.3f}\n"
        "controller-visible normalized energy: "
        f"{_optional(frame.controller_visible_energy)}\n"
        f"beacon L/F/R: {beacon}\n"
        f"current max beacon: {current}\n"
        f"previous beacon: {previous}\n"
        f"delta = current - previous: {delta}\n"
        f"SEEK trigger: {trigger}\n"
        f"charging_contact: {contact}\n"
        f"coverage: {frame.visited_cell_count} cells ({frame.coverage_fraction:.3f})\n"
        f"station distance: {distance} [EVALUATOR ONLY]\n"
        f"terminal/horizon status: {status}"
    )


def _optional(value: float | None) -> str:
    return "—" if value is None else f"{value:.3f}"


def _pad_trend_frames(
    frames: tuple[EXP003VisualizationFrame, ...],
    maximum_length: int,
) -> tuple[EXP003VisualizationFrame, ...]:
    padded = _pad_frames(frames, maximum_length)
    return tuple(
        replace(
            frame,
            current_beacon_max=None,
            previous_explore_beacon_max=None,
            beacon_delta=None,
            seek_trigger=None,
        )
        if frame.is_padded
        else frame
        for frame in padded
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
