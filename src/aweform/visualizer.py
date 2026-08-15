"""Development-only evaluator visualisation for EXP-000 trajectories."""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence, cast

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

from .controllers import ControllerMode, HomeostaticConfig
from .env import AweformEnvConfig
from .runner import (
    Condition,
    DevelopmentBatchResult,
    EpisodeRecord,
    EpisodeTrajectory,
    run_development_batch,
)


@dataclass(frozen=True, slots=True)
class VisualizationFrame:
    """One evaluator-side state in the shared animation timeline."""

    step_index: int
    x: float
    y: float
    heading: float
    normalized_energy: float
    path: tuple[tuple[float, float], ...]
    mode: ControllerMode | None
    terminal_status: str


@dataclass(frozen=True, slots=True)
class VisualizationData:
    """All data needed to construct the three-panel development view."""

    seed: int
    world_min: tuple[float, float]
    world_max: tuple[float, float]
    source_positions: tuple[tuple[float, float], ...]
    frames: tuple[tuple[VisualizationFrame, ...], ...]


def select_seed_records(
    result: DevelopmentBatchResult,
    seed: int | None = None,
) -> tuple[EpisodeRecord, ...]:
    """Select exactly one deterministic A/B/C record set for one seed."""
    seed_candidates = result.manifest.environment_seeds + tuple(
        record.trajectory.environment_seed for record in result.episodes
    )
    available_seeds = tuple(dict.fromkeys(seed_candidates))
    if seed is None:
        if not available_seeds:
            raise ValueError("development batch contains no episode records")
        if len(available_seeds) != 1:
            raise ValueError(
                "seed must be specified when the development batch contains "
                "multiple seeds"
            )
        selected_seed = available_seeds[0]
    else:
        if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
            raise ValueError("seed must be a non-negative integer")
        selected_seed = seed

    selected = [
        record
        for record in result.episodes
        if record.trajectory.environment_seed == selected_seed
    ]
    by_condition: dict[Condition, EpisodeRecord] = {}
    for record in selected:
        condition = record.trajectory.condition
        if condition in by_condition:
            raise ValueError(
                f"development batch has duplicate {condition.value} records "
                f"for seed {selected_seed}"
            )
        by_condition[condition] = record

    missing = [
        condition.value for condition in Condition if condition not in by_condition
    ]
    if missing:
        raise ValueError(
            f"development batch is missing conditions for seed {selected_seed}: "
            + ", ".join(missing)
        )
    return tuple(by_condition[condition] for condition in Condition)


def build_visualization_frames(
    result: DevelopmentBatchResult,
    seed: int | None = None,
) -> VisualizationData:
    """Prepare aligned evaluator states without opening a Matplotlib window."""
    records = select_seed_records(result, seed)
    world_min = _coordinate_from_config(result.manifest.environment_config, "world_min")
    world_max = _coordinate_from_config(result.manifest.environment_config, "world_max")
    failure_boundary, maximum_energy = _energy_bounds(
        result.manifest.environment_config
    )

    source_positions = records[0].trajectory.initial_state.source_positions
    if any(
        record.trajectory.initial_state.source_positions != source_positions
        for record in records[1:]
    ):
        raise ValueError("matched conditions do not share resource source positions")

    condition_frames = tuple(
        _record_frames(
            record.trajectory,
            failure_boundary=failure_boundary,
            maximum_energy=maximum_energy,
        )
        for record in records
    )
    maximum_length = max(len(frames) for frames in condition_frames)
    aligned = tuple(
        frames + (frames[-1],) * (maximum_length - len(frames))
        for frames in condition_frames
    )
    return VisualizationData(
        seed=records[0].trajectory.environment_seed,
        world_min=world_min,
        world_max=world_max,
        source_positions=source_positions,
        frames=aligned,
    )


def build_visualization_figure(
    result: DevelopmentBatchResult,
    seed: int | None = None,
) -> tuple[Figure, FuncAnimation]:
    """Build the three-panel animation without showing it."""
    data = build_visualization_frames(result, seed)
    figure, axes = plt.subplots(1, len(Condition), figsize=(13, 4.5), squeeze=False)
    artists: list[tuple[Any, Any, Any, Any]] = []
    labels = {
        Condition.A_PERSISTENT: "A — persistent exploration",
        Condition.B_HOMEOSTATIC: "B — homeostatic",
        Condition.C_ENERGY_BLIND: "C — energy-blind",
    }

    for axis, condition in zip(axes[0], Condition):
        axis.set_xlim(data.world_min[0], data.world_max[0])
        axis.set_ylim(data.world_min[1], data.world_max[1])
        axis.set_aspect("equal", adjustable="box")
        axis.set_xlabel("x (evaluator view)")
        axis.set_ylabel("y (evaluator view)")
        axis.set_title(f"{condition.value}\n{labels[condition]}")
        axis.add_patch(
            Rectangle(
                data.world_min,
                data.world_max[0] - data.world_min[0],
                data.world_max[1] - data.world_min[1],
                fill=False,
                edgecolor="black",
                linewidth=1.0,
            )
        )
        axis.plot(
            [position[0] for position in data.source_positions],
            [position[1] for position in data.source_positions],
            marker="*",
            markersize=10,
            color="black",
            linestyle="None",
        )
        path_line, *_ = axis.plot([], [], color="tab:blue", alpha=0.45)
        position_marker, *_ = axis.plot(
            [], [], marker="o", color="tab:blue", markersize=6, linestyle="None"
        )
        heading_arrow = axis.quiver(
            [], [], [], [], angles="xy", scale_units="xy", scale=5, color="tab:orange"
        )
        summary_text = axis.text(
            0.02,
            0.98,
            "",
            transform=axis.transAxes,
            va="top",
            ha="left",
            fontsize=8,
            family="monospace",
        )
        artists.append((path_line, position_marker, heading_arrow, summary_text))

    def update(frame_index: int) -> tuple[Any, ...]:
        updated: list[Any] = []
        for condition_index, artist_group in enumerate(artists):
            frame = data.frames[condition_index][frame_index]
            path_line, position_marker, heading_arrow, summary_text = artist_group
            path_x, path_y = zip(*frame.path)
            path_line.set_data(path_x, path_y)
            position_marker.set_data([frame.x], [frame.y])
            heading_arrow.set_offsets(np.asarray([[frame.x, frame.y]]))
            heading_arrow.set_UVC(
                np.asarray([math.cos(frame.heading)]),
                np.asarray([math.sin(frame.heading)]),
            )
            mode_text = "" if frame.mode is None else f"\nmode: {frame.mode.value}"
            summary_text.set_text(
                f"step: {frame.step_index}\n"
                f"energy: {frame.normalized_energy:.3f}"
                f"{mode_text}\n"
                f"status: {frame.terminal_status}"
            )
            updated.extend(artist_group)
        return tuple(updated)

    update(0)
    animation = FuncAnimation(
        figure,
        update,
        frames=len(data.frames[0]),
        interval=100,
        repeat=False,
        blit=False,
    )
    figure.suptitle(f"EXP-000 development visualizer — seed {data.seed}")
    figure.tight_layout()
    # Keep the animation alive when the interactive helper returns only Figure.
    setattr(figure, "_aweform_animation", animation)
    return figure, animation


def show_development_visualization(
    result: DevelopmentBatchResult,
    seed: int | None = None,
) -> Figure:
    """Show one selected-seed A/B/C development animation interactively."""
    figure, _animation = build_visualization_figure(result, seed)
    plt.show()
    return figure


def main(argv: Sequence[str] | None = None) -> int:
    """Run one development batch, then open the visualizer."""
    parser = argparse.ArgumentParser(
        description="Run an EXP-000 development visualizer session."
    )
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--masked-energy", type=float, required=True)
    parser.add_argument("--resource-count", type=int, default=1)
    parser.add_argument(
        "--episode-horizon",
        type=_episode_horizon_argument,
        default=100,
        help="episode horizon in steps (1-1000; default: 100)",
    )
    parser.add_argument("--git-sha", required=True)
    args = parser.parse_args(argv)
    result = run_development_batch(
        seeds=[args.seed],
        env_config=AweformEnvConfig(
            resource_count=args.resource_count,
            episode_horizon=args.episode_horizon,
        ),
        homeostatic_config=HomeostaticConfig(),
        masked_energy=args.masked_energy,
        git_sha=args.git_sha,
    )
    show_development_visualization(result, args.seed)
    return 0


def _episode_horizon_argument(value: str) -> int:
    try:
        episode_horizon = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "episode horizon must be an integer"
        ) from error
    if not 1 <= episode_horizon <= 1000:
        raise argparse.ArgumentTypeError("episode horizon must be between 1 and 1000")
    return episode_horizon


def _record_frames(
    trajectory: EpisodeTrajectory,
    *,
    failure_boundary: float,
    maximum_energy: float,
) -> tuple[VisualizationFrame, ...]:
    energy_range = maximum_energy - failure_boundary
    initial = trajectory.initial_state
    initial_mode = (
        None
        if trajectory.condition is Condition.A_PERSISTENT
        else ControllerMode.EXPLORE
    )
    frames = [
        VisualizationFrame(
            step_index=0,
            x=initial.x,
            y=initial.y,
            heading=initial.heading,
            normalized_energy=(initial.energy - failure_boundary) / energy_range,
            path=((initial.x, initial.y),),
            mode=initial_mode,
            terminal_status="running",
        )
    ]
    path = [(initial.x, initial.y)]
    for expected_step, transition in enumerate(trajectory.transitions, start=1):
        if transition.step_index != expected_step:
            raise ValueError(
                "trajectory steps must start at 1 and increase by one; "
                f"got {transition.step_index} at position {expected_step}"
            )
        if transition.terminated and transition.truncated:
            raise ValueError("a transition cannot be both terminated and truncated")
        path.append((transition.x, transition.y))
        status = (
            "terminated"
            if transition.terminated
            else "truncated"
            if transition.truncated
            else "running"
        )
        frames.append(
            VisualizationFrame(
                step_index=transition.step_index,
                x=transition.x,
                y=transition.y,
                heading=transition.heading,
                normalized_energy=(transition.energy - failure_boundary) / energy_range,
                path=tuple(path),
                mode=transition.mode,
                terminal_status=status,
            )
        )
    return tuple(frames)


def _coordinate_from_config(
    config: Mapping[str, Any], field_name: str
) -> tuple[float, float]:
    value = config.get(field_name)
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f"environment_config.{field_name} must contain two values")
    coordinates = tuple(
        _finite_float(item, f"environment_config.{field_name}") for item in value
    )
    return cast(tuple[float, float], coordinates)


def _energy_bounds(config: Mapping[str, Any]) -> tuple[float, float]:
    energy = config.get("energy")
    if not isinstance(energy, Mapping):
        raise ValueError("environment_config.energy must be an object")
    failure_boundary = _finite_float(
        energy.get("failure_boundary"),
        "environment_config.energy.failure_boundary",
    )
    maximum_energy = _finite_float(
        energy.get("maximum_energy"),
        "environment_config.energy.maximum_energy",
    )
    if maximum_energy <= failure_boundary:
        raise ValueError("environment energy bounds must have positive range")
    return failure_boundary, maximum_energy


def _finite_float(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field_name} must be a finite number")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
