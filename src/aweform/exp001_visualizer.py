"""Development-only evaluator visualisation for EXP-001 trajectories.

This module deliberately has its own frame schema.  EXP-001 controller
observations and mode semantics are not interchangeable with EXP-000's
trajectory or energy-access visualisation.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass, replace
from typing import Any, Sequence

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

from .env import Action, AweformEnvConfig
from .exp001 import (
    EXP001Mode,
    ExternalObservation,
    InteroceptiveObservation,
)
from .exp001_calibration import (
    CALIBRATED_C,
    FROZEN_EXP001_CALIBRATION_ENV_CONFIG,
    FROZEN_EXP001_SHARED_CONTROLLER_CONFIG,
)
from .exp001_runner import (
    EXP001Condition,
    EXP001DevelopmentBatchResult,
    EXP001EpisodeRecord,
    EXP001TransitionRecord,
    run_exp001_development_batch,
)
from .exp001_seed_policy import validate_exp001_development_seeds
from .resource import ResourceField

RESOURCE_FIELD_GRID_SIZE = 80


@dataclass(frozen=True, slots=True)
class EXP001VisualizationFrame:
    """One evaluator-side state and its next controller decision, if any."""

    step_index: int
    x: float
    y: float
    heading: float
    heading_vector: tuple[float, float]
    probe_endpoints: tuple[
        tuple[float, float],
        tuple[float, float],
        tuple[float, float],
    ]
    actual_normalized_energy: float
    path: tuple[tuple[float, float], ...]
    mode: EXP001Mode
    next_action: Action | None
    left_resource: float | None
    forward_resource: float | None
    right_resource: float | None
    controller_visible_energy: float | None
    terminal_status: str
    is_padded: bool = False


@dataclass(frozen=True, slots=True)
class EXP001ResourceFieldVisualization:
    """Evaluator-side samples of the environment's renewable resource field."""

    x_coordinates: tuple[float, ...]
    y_coordinates: tuple[float, ...]
    intensities: tuple[tuple[float, ...], ...]
    peak_intensity: float


@dataclass(frozen=True, slots=True)
class EXP001VisualizationData:
    """All data needed to construct the aligned three-panel view."""

    seed: int
    world_min: tuple[float, float]
    world_max: tuple[float, float]
    source_positions: tuple[tuple[float, float], ...]
    resource_field: EXP001ResourceFieldVisualization
    frames: tuple[tuple[EXP001VisualizationFrame, ...], ...]


def select_exp001_seed_records(
    result: EXP001DevelopmentBatchResult,
    seed: int | None = None,
) -> tuple[EXP001EpisodeRecord, ...]:
    """Select exactly one ordered A/B/C record set for one seed."""

    available_seeds = tuple(dict.fromkeys(result.environment_seeds))
    if seed is None:
        if not available_seeds:
            raise ValueError("EXP-001 development batch contains no seeds")
        if len(available_seeds) != 1:
            raise ValueError(
                "seed must be specified when the EXP-001 batch contains "
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
        if record.environment_seed == selected_seed
    ]
    by_condition: dict[EXP001Condition, EXP001EpisodeRecord] = {}
    for record in selected:
        if record.condition in by_condition:
            raise ValueError(
                f"EXP-001 batch has duplicate {record.condition.value} records "
                f"for seed {selected_seed}"
            )
        by_condition[record.condition] = record

    missing = [
        condition.value
        for condition in EXP001Condition
        if condition not in by_condition
    ]
    if missing:
        raise ValueError(
            f"EXP-001 batch is missing conditions for seed {selected_seed}: "
            + ", ".join(missing)
        )
    return tuple(by_condition[condition] for condition in EXP001Condition)


def build_exp001_visualization_frames(
    result: EXP001DevelopmentBatchResult,
    seed: int | None = None,
) -> EXP001VisualizationData:
    """Prepare aligned evaluator states without executing the simulator."""

    records = select_exp001_seed_records(result, seed)
    environment_config = result.environment_config
    source_positions = records[0].initial_state.source_positions
    if any(
        record.initial_state.source_positions != source_positions
        for record in records[1:]
    ):
        raise ValueError("matched conditions do not share resource source positions")

    condition_frames = tuple(
        _record_frames(record, environment_config) for record in records
    )
    maximum_length = max(len(frames) for frames in condition_frames)
    aligned = tuple(
        _pad_terminal_frames(frames, maximum_length)
        for frames in condition_frames
    )
    return EXP001VisualizationData(
        seed=records[0].environment_seed,
        world_min=environment_config.world_min,
        world_max=environment_config.world_max,
        source_positions=source_positions,
        resource_field=build_exp001_resource_field_visualization(
            environment_config,
            source_positions,
        ),
        frames=aligned,
    )


def build_exp001_resource_field_visualization(
    environment_config: AweformEnvConfig,
    source_positions: tuple[tuple[float, float], ...],
    *,
    grid_size: int = RESOURCE_FIELD_GRID_SIZE,
) -> EXP001ResourceFieldVisualization:
    """Sample the actual resource field for an evaluator-only heatmap.

    The visualizer deliberately delegates each sample to :class:`ResourceField`
    so the display uses the same max-of-sources Gaussian field as the
    environment.  This function has no effect on simulation state.
    """

    if isinstance(grid_size, bool) or not isinstance(grid_size, int):
        raise ValueError("grid_size must be a positive integer")
    if grid_size <= 0:
        raise ValueError("grid_size must be a positive integer")
    field = ResourceField(
        world_min=environment_config.world_min,
        world_max=environment_config.world_max,
        source_positions=source_positions,
        peak_intensity=environment_config.resource_peak_intensity,
        length_scale=environment_config.resource_length_scale,
    )
    x_coordinates = tuple(
        float(value)
        for value in np.linspace(
            environment_config.world_min[0],
            environment_config.world_max[0],
            grid_size,
        )
    )
    y_coordinates = tuple(
        float(value)
        for value in np.linspace(
            environment_config.world_min[1],
            environment_config.world_max[1],
            grid_size,
        )
    )
    intensities = tuple(
        tuple(field.intensity((x, y)) for x in x_coordinates)
        for y in y_coordinates
    )
    return EXP001ResourceFieldVisualization(
        x_coordinates=x_coordinates,
        y_coordinates=y_coordinates,
        intensities=intensities,
        peak_intensity=field.peak_intensity,
    )


def format_exp001_diagnostic_text(
    frame: EXP001VisualizationFrame,
    condition: EXP001Condition,
) -> str:
    """Format controller/evaluator diagnostics for one panel."""

    if condition is EXP001Condition.B and frame.next_action is None:
        energy_access_label = "EVALUATOR ONLY — no next controller observation"
    elif _controller_can_see_energy(frame, condition):
        energy_access_label = "CONTROLLER + EVALUATOR"
    else:
        energy_access_label = "EVALUATOR ONLY"
    energy_text = (
        f"actual normalized energy: {frame.actual_normalized_energy:.3f} "
        f"[{energy_access_label}]"
    )
    if frame.next_action is None:
        sense_text = "— / — / —"
        action_text = "—"
    else:
        assert frame.left_resource is not None
        assert frame.forward_resource is not None
        assert frame.right_resource is not None
        sense_text = (
            f"{frame.left_resource:.3f} / "
            f"{frame.forward_resource:.3f} / "
            f"{frame.right_resource:.3f}"
        )
        action_text = frame.next_action.name
    held_text = " (held)" if frame.is_padded else ""
    return (
        f"step: {frame.step_index}\n"
        f"mode: {frame.mode.value}\n"
        f"next action: {action_text}\n"
        f"sense L/F/R: {sense_text}\n"
        f"{energy_text}\n"
        f"status: {frame.terminal_status}{held_text}"
    )


def format_exp001_energy_visibility_label(
    frame: EXP001VisualizationFrame,
    condition: EXP001Condition,
) -> str:
    """Return the concise evaluator-side label for the graphical energy bar."""

    return (
        "CTRL + EVAL" if _controller_can_see_energy(frame, condition) else "EVAL ONLY"
    )


def build_exp001_visualization_figure(
    result: EXP001DevelopmentBatchResult,
    seed: int | None = None,
) -> tuple[Figure, FuncAnimation]:
    """Build the three-panel EXP-001 animation without showing it."""

    data = build_exp001_visualization_frames(result, seed)
    figure, axes = plt.subplots(
        1,
        len(EXP001Condition),
        figsize=(16, 6.8),
        squeeze=False,
    )
    artists: list[dict[str, Any]] = []
    labels = {
        EXP001Condition.A: (
            "A — stochastic explorer",
            "External sensing only; no energy sensor",
        ),
        EXP001Condition.B: (
            "B — interoceptive closed-loop",
            "Actual internal energy controls seek/recharge timing",
        ),
        EXP001Condition.C: (
            "C — calibrated energy-blind open-loop",
            "SHORT: EXPLORE 10 / CHARGE 5; no energy sensor",
        ),
    }

    for axis, condition in zip(axes[0], EXP001Condition):
        axis.set_xlim(data.world_min[0], data.world_max[0])
        axis.set_ylim(data.world_min[1], data.world_max[1])
        axis.set_aspect("equal", adjustable="box")
        axis.set_xlabel("x (evaluator view)")
        axis.set_ylabel("y (evaluator view)")
        title, mechanism_note = labels[condition]
        axis.set_title(f"{title}\n{mechanism_note}")
        resource_field = data.resource_field
        axis.imshow(
            np.asarray(resource_field.intensities),
            extent=(
                data.world_min[0],
                data.world_max[0],
                data.world_min[1],
                data.world_max[1],
            ),
            origin="lower",
            interpolation="bilinear",
            cmap="Greys",
            vmin=0.0,
            vmax=resource_field.peak_intensity,
            alpha=0.28,
            zorder=0,
        )
        axis.add_patch(
            Rectangle(
                data.world_min,
                data.world_max[0] - data.world_min[0],
                data.world_max[1] - data.world_min[1],
                fill=False,
                edgecolor="black",
                linewidth=1.0,
                zorder=8,
            )
        )
        axis.plot(
            [position[0] for position in data.source_positions],
            [position[1] for position in data.source_positions],
            marker="*",
            markersize=10,
            color="black",
            linestyle="None",
            label="resource source",
            zorder=4,
        )
        path_line, *_ = axis.plot([], [], color="tab:blue", alpha=0.45)
        position_marker, *_ = axis.plot(
            [],
            [],
            marker="o",
            markerfacecolor="white",
            markeredgecolor="tab:blue",
            markeredgewidth=2.0,
            markersize=11,
            linestyle="None",
            zorder=7,
        )
        heading_arrow = axis.quiver(
            [],
            [],
            [],
            [],
            angles="xy",
            scale_units="xy",
            scale=8,
            color="tab:orange",
            width=0.008,
            zorder=8,
        )
        probe_lines = tuple(
            axis.plot(
                [],
                [],
                color=color,
                alpha=0.85,
                linestyle=(0, (2, 2)),
                linewidth=1.3,
                zorder=6,
            )[0]
            for color in ("tab:purple", "tab:green", "tab:red")
        )
        mode_badge = axis.text(
            0.02,
            0.96,
            "",
            transform=axis.transAxes,
            va="top",
            ha="left",
            fontsize=10,
            fontweight="bold",
            color="white",
            zorder=10,
        )
        energy_bar_background = Rectangle(
            (0.94, 0.78),
            0.035,
            0.18,
            transform=axis.transAxes,
            facecolor="white",
            edgecolor="black",
            linewidth=0.8,
            zorder=8,
        )
        energy_bar = Rectangle(
            (0.94, 0.78),
            0.035,
            0.0,
            transform=axis.transAxes,
            facecolor="tab:green",
            edgecolor="none",
            zorder=9,
        )
        axis.add_patch(energy_bar_background)
        axis.add_patch(energy_bar)
        energy_access_label = (
            "CTRL + EVAL" if condition is EXP001Condition.B else "EVAL ONLY"
        )
        energy_label = axis.text(
            0.9575,
            0.75,
            energy_access_label,
            transform=axis.transAxes,
            va="top",
            ha="center",
            fontsize=6,
            fontweight="bold",
            rotation=90,
            zorder=10,
        )
        summary_text = axis.text(
            0.02,
            0.82,
            "",
            transform=axis.transAxes,
            va="top",
            ha="left",
            fontsize=8,
            family="monospace",
            zorder=10,
        )
        axis.text(
            0.02,
            0.02,
            "probe rays: L / F / R",
            transform=axis.transAxes,
            va="bottom",
            ha="left",
            fontsize=7,
            color="dimgray",
            zorder=10,
        )
        artists.append(
            {
                "path_line": path_line,
                "position_marker": position_marker,
                "heading_arrow": heading_arrow,
                "probe_lines": probe_lines,
                "mode_badge": mode_badge,
                "energy_bar": energy_bar,
                "energy_label": energy_label,
                "summary_text": summary_text,
            }
        )

    mode_colors = {
        EXP001Mode.EXPLORE: "#2563eb",
        EXP001Mode.SEEK_RESOURCE: "#d97706",
        EXP001Mode.CHARGE: "#16a34a",
    }

    def update(frame_index: int) -> tuple[Any, ...]:
        updated: list[Any] = []
        for condition_index, artist_group in enumerate(artists):
            frame = data.frames[condition_index][frame_index]
            condition = tuple(EXP001Condition)[condition_index]
            path_line = artist_group["path_line"]
            position_marker = artist_group["position_marker"]
            heading_arrow = artist_group["heading_arrow"]
            probe_lines = artist_group["probe_lines"]
            mode_badge = artist_group["mode_badge"]
            energy_bar = artist_group["energy_bar"]
            energy_label = artist_group["energy_label"]
            summary_text = artist_group["summary_text"]
            path_x, path_y = zip(*frame.path)
            path_line.set_data(path_x, path_y)
            position_marker.set_data([frame.x], [frame.y])
            heading_arrow.set_offsets(np.asarray([[frame.x, frame.y]]))
            heading_arrow.set_UVC(
                np.asarray([frame.heading_vector[0]]),
                np.asarray([frame.heading_vector[1]]),
            )
            for probe_line, endpoint in zip(probe_lines, frame.probe_endpoints):
                probe_line.set_data(
                    [frame.x, endpoint[0]],
                    [frame.y, endpoint[1]],
                )
            mode_badge.set_text(f"MODE  {frame.mode.value}")
            mode_badge.set_bbox(
                {
                    "boxstyle": "round,pad=0.3",
                    "facecolor": mode_colors[frame.mode],
                    "edgecolor": "none",
                    "alpha": 0.95,
                }
            )
            energy_bar.set_height(
                0.18 * _clamp_normalized(frame.actual_normalized_energy)
            )
            energy_label.set_text(
                format_exp001_energy_visibility_label(frame, condition)
            )
            summary_text.set_text(format_exp001_diagnostic_text(frame, condition))
            updated.extend(
                (
                    path_line,
                    position_marker,
                    heading_arrow,
                    *probe_lines,
                    mode_badge,
                    energy_bar,
                    energy_label,
                    summary_text,
                )
            )
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
    figure.suptitle(
        "EXP-001 calibrated development visualization "
        f"— seed {data.seed}\n"
        "DESCRIPTIVE / DEVELOPMENT VIEW — NOT CONFIRMATORY EVIDENCE\n"
        "Displayed information is not necessarily "
        "controller-visible\n"
        "Energy shown for A and C is privileged evaluator information and is not "
        "available to those controllers. Heatmap and probe rays are also "
        "evaluator-side annotations."
    )
    figure.tight_layout(rect=(0, 0, 1, 0.84))
    setattr(figure, "_aweform_animation", animation)
    return figure, animation


def show_exp001_development_visualization(
    result: EXP001DevelopmentBatchResult,
    seed: int | None = None,
) -> Figure:
    """Show one selected-seed A/B/C EXP-001 animation interactively."""

    figure, _animation = build_exp001_visualization_figure(result, seed)
    plt.show()
    return figure


def main(argv: Sequence[str] | None = None) -> int:
    """Run one calibrated EXP-001 development batch, then open the visualizer."""

    parser = argparse.ArgumentParser(
        description=(
            "Open the EXP-001 development-only evaluator visualizer. "
            "This is not calibration or scientific analysis."
        )
    )
    parser.add_argument("--seed", type=_non_negative_int, required=True)
    args = parser.parse_args(argv)
    try:
        validated_seed = validate_exp001_development_seeds((args.seed,))[0]
    except ValueError as error:
        parser.error(str(error))
    result = run_exp001_development_batch(
        seeds=[validated_seed],
        env_config=FROZEN_EXP001_CALIBRATION_ENV_CONFIG,
        development_config=FROZEN_EXP001_SHARED_CONTROLLER_CONFIG.for_candidate(
            CALIBRATED_C
        ),
    )
    show_exp001_development_visualization(result, validated_seed)
    return 0


def _record_frames(
    record: EXP001EpisodeRecord,
    environment_config: AweformEnvConfig,
) -> tuple[EXP001VisualizationFrame, ...]:
    failure_boundary = environment_config.energy.failure_boundary
    energy_range = (
        environment_config.energy.maximum_energy
        - environment_config.energy.failure_boundary
    )
    initial = record.initial_state
    final_mode = EXP001Mode.EXPLORE
    frames: list[EXP001VisualizationFrame] = []
    path = [initial.position]

    for transition_index, transition in enumerate(record.transitions):
        expected_step = transition_index + 1
        if transition.privileged_evaluator.step_index != expected_step:
            raise ValueError(
                "EXP-001 transition steps must start at 1 and increase by one; "
                f"got {transition.privileged_evaluator.step_index} at position "
                f"{expected_step}"
            )
        frame_state = _frame_state(
            record,
            transition_index,
            path,
            transition.privileged_evaluator.controller_mode,
            failure_boundary,
            energy_range,
            environment_config,
        )
        frames.append(
            _with_decision_diagnostics(
                frame_state,
                transition,
            )
        )
        path.append(transition.privileged_evaluator.position)
        final_mode = transition.privileged_evaluator.controller_mode

    final_position = path[-1]
    final_energy = (
        record.initial_state.actual_energy
        if not record.transitions
        else record.transitions[-1].privileged_evaluator.actual_energy
    )
    final_transition = record.transitions[-1] if record.transitions else None
    final_heading = (
        record.initial_state.heading
        if final_transition is None
        else final_transition.privileged_evaluator.heading
    )
    final_heading_vector, final_probe_endpoints = _frame_geometry(
        final_position,
        final_heading,
        environment_config,
    )
    final_status = _terminal_status(
        None
        if final_transition is None
        else final_transition.privileged_evaluator
    )
    frames.append(
        EXP001VisualizationFrame(
            step_index=len(record.transitions),
            x=final_position[0],
            y=final_position[1],
            heading=final_heading,
            heading_vector=final_heading_vector,
            probe_endpoints=final_probe_endpoints,
            actual_normalized_energy=(
                final_energy - environment_config.energy.failure_boundary
            )
            / energy_range,
            path=tuple(path),
            mode=final_mode,
            next_action=None,
            left_resource=None,
            forward_resource=None,
            right_resource=None,
            controller_visible_energy=None,
            terminal_status=final_status,
        )
    )
    return tuple(frames)


def _frame_state(
    record: EXP001EpisodeRecord,
    transition_index: int,
    path: list[tuple[float, float]],
    mode: EXP001Mode,
    failure_boundary: float,
    energy_range: float,
    environment_config: AweformEnvConfig,
) -> EXP001VisualizationFrame:
    if transition_index == 0:
        position = record.initial_state.position
        heading = record.initial_state.heading
        actual_energy = record.initial_state.actual_energy
    else:
        previous = record.transitions[transition_index - 1].privileged_evaluator
        position = previous.position
        heading = previous.heading
        actual_energy = previous.actual_energy
    heading_vector, probe_endpoints = _frame_geometry(
        position,
        heading,
        environment_config,
    )
    return EXP001VisualizationFrame(
        step_index=transition_index,
        x=position[0],
        y=position[1],
        heading=heading,
        heading_vector=heading_vector,
        probe_endpoints=probe_endpoints,
        actual_normalized_energy=(actual_energy - failure_boundary)
        / energy_range,
        path=tuple(path),
        mode=mode,
        next_action=None,
        left_resource=None,
        forward_resource=None,
        right_resource=None,
        controller_visible_energy=None,
        terminal_status="running",
    )


def _frame_geometry(
    position: tuple[float, float],
    heading: float,
    environment_config: AweformEnvConfig,
) -> tuple[
    tuple[float, float],
    tuple[tuple[float, float], tuple[float, float], tuple[float, float]],
]:
    heading_vector = (math.cos(heading), math.sin(heading))
    probe_endpoints = (
        _probe_endpoint(
            position,
            heading + environment_config.sensor_angle,
            environment_config.probe_distance,
        ),
        _probe_endpoint(
            position,
            heading,
            environment_config.probe_distance,
        ),
        _probe_endpoint(
            position,
            heading - environment_config.sensor_angle,
            environment_config.probe_distance,
        ),
    )
    return heading_vector, probe_endpoints


def _probe_endpoint(
    position: tuple[float, float],
    direction: float,
    distance: float,
) -> tuple[float, float]:
    return (
        position[0] + distance * math.cos(direction),
        position[1] + distance * math.sin(direction),
    )


def _clamp_normalized(value: float) -> float:
    return max(0.0, min(1.0, value))


def _controller_can_see_energy(
    frame: EXP001VisualizationFrame,
    condition: EXP001Condition,
) -> bool:
    return condition is EXP001Condition.B and frame.next_action is not None


def _with_decision_diagnostics(
    frame: EXP001VisualizationFrame,
    transition: EXP001TransitionRecord,
) -> EXP001VisualizationFrame:
    observation = transition.controller_visible.observation
    if isinstance(observation, InteroceptiveObservation):
        external = observation.external
        controller_energy = observation.energy
    else:
        assert isinstance(observation, ExternalObservation)
        external = observation
        controller_energy = None
    evaluator = transition.privileged_evaluator
    return replace(
        frame,
        next_action=evaluator.action,
        left_resource=external.left_resource,
        forward_resource=external.forward_resource,
        right_resource=external.right_resource,
        controller_visible_energy=controller_energy,
    )


def _pad_terminal_frames(
    frames: tuple[EXP001VisualizationFrame, ...],
    maximum_length: int,
) -> tuple[EXP001VisualizationFrame, ...]:
    if not frames:
        raise ValueError("EXP-001 episode produced no visualization frames")
    last = frames[-1]
    padding = tuple(
        replace(
            last,
            is_padded=True,
            next_action=None,
            left_resource=None,
            forward_resource=None,
            right_resource=None,
            controller_visible_energy=None,
        )
        for _ in range(maximum_length - len(frames))
    )
    return frames + padding


def _terminal_status(transition: Any) -> str:
    if transition is None:
        return "running"
    if transition.terminated and transition.truncated:
        raise ValueError("a transition cannot be both terminated and truncated")
    if transition.terminated:
        return "terminated"
    if transition.truncated:
        return "truncated"
    return "running"


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
