"""Renderer-only development visualization for EXP-002.

This module consumes the existing matched EXP-002 development runner output.
It does not execute experiments, alter controller observations, or define a
calibration/confirmatory workflow.
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
from .exp001_calibration import FROZEN_EXP001_CALIBRATION_ENV_CONFIG
from .exp001_runner import (
    EXP001Condition,
)
from .exp001_visualizer import (
    _clamp_normalized,
    _frame_geometry,
    build_exp001_resource_field_visualization,
)
from .exp002_protocol import (
    EXP002_COVERAGE_GRID_HEIGHT,
    EXP002_COVERAGE_GRID_WIDTH,
    EXP002BCandidate,
)
from .exp002_runner import (
    EXP002DevelopmentBatchResult,
    EXP002EpisodeDiagnostics,
    EXP002EpisodeRecord,
    exp002_coverage_grid_states,
    run_exp002_development_batch,
)
from .exp002_seed_policy import validate_exp002_development_seeds


@dataclass(frozen=True, slots=True)
class EXP002VisualizationFrame:
    """One evaluator-side state and its next recorded controller decision."""

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
    visited_cells: tuple[tuple[int, int], ...]
    visited_cell_count: int
    remaining_cell_count: int
    coverage_fraction: float
    most_recent_seek_onset_energy: float | None
    most_recent_seek_distance: float | None
    seek_attempt_active: bool
    most_recent_seek_reached_charge: bool | None
    terminal_status: str
    is_padded: bool = False


@dataclass(frozen=True, slots=True)
class EXP002VisualizationData:
    """All evaluator-side data needed for the aligned A/B/C view."""

    seed: int
    candidate: EXP002BCandidate
    world_min: tuple[float, float]
    world_max: tuple[float, float]
    source_positions: tuple[tuple[float, float], ...]
    resource_field: Any
    diagnostics: tuple[EXP002EpisodeDiagnostics, ...]
    frames: tuple[tuple[EXP002VisualizationFrame, ...], ...]


@dataclass(frozen=True, slots=True)
class _SeekViewState:
    onset_energy: float | None
    distance: float | None
    active: bool
    reached_charge: bool | None


def select_exp002_seed_records(
    result: EXP002DevelopmentBatchResult,
    seed: int | None = None,
) -> tuple[EXP002EpisodeRecord, ...]:
    """Select exactly one ordered A/B/C record set for one seed."""

    available_seeds = tuple(dict.fromkeys(result.environment_seeds))
    if seed is None:
        if len(available_seeds) != 1:
            raise ValueError(
                "seed must be specified when the EXP-002 batch does not contain "
                "exactly one seed"
            )
        selected_seed = available_seeds[0]
    else:
        if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
            raise ValueError("seed must be a non-negative integer")
        selected_seed = seed

    selected = tuple(
        record
        for record in result.episodes
        if record.environment_seed == selected_seed
    )
    by_condition: dict[EXP001Condition, EXP002EpisodeRecord] = {}
    for record in selected:
        if record.condition in by_condition:
            raise ValueError(
                f"EXP-002 batch has duplicate {record.condition.value} records "
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
            f"EXP-002 batch is missing conditions for seed {selected_seed}: "
            + ", ".join(missing)
        )
    return tuple(by_condition[condition] for condition in EXP001Condition)


def build_exp002_visualization_frames(
    result: EXP002DevelopmentBatchResult,
    seed: int | None = None,
) -> EXP002VisualizationData:
    """Prepare aligned renderer state without rerunning the development batch."""

    records = select_exp002_seed_records(result, seed)
    diagnostics_by_condition = {
        (episode.environment_seed, episode.condition): diagnostic
        for episode, diagnostic in zip(result.episodes, result.diagnostics)
    }
    diagnostics = tuple(
        diagnostics_by_condition[(record.environment_seed, record.condition)]
        for record in records
    )
    source_positions = records[0].initial_state.source_positions
    if any(
        record.initial_state.source_positions != source_positions
        for record in records[1:]
    ):
        raise ValueError("matched conditions do not share resource source positions")

    condition_frames = tuple(
        _record_frames(record, diagnostic, result.environment_config)
        for record, diagnostic in zip(records, diagnostics)
    )
    maximum_length = max(len(frames) for frames in condition_frames)
    aligned = tuple(
        _pad_terminal_frames(frames, maximum_length)
        for frames in condition_frames
    )
    return EXP002VisualizationData(
        seed=records[0].environment_seed,
        candidate=result.candidate,
        world_min=result.environment_config.world_min,
        world_max=result.environment_config.world_max,
        source_positions=source_positions,
        resource_field=build_exp001_resource_field_visualization(
            result.environment_config,
            source_positions,
        ),
        diagnostics=diagnostics,
        frames=aligned,
    )


def format_exp002_diagnostic_text(
    frame: EXP002VisualizationFrame,
    condition: EXP001Condition,
    candidate: EXP002BCandidate,
) -> str:
    """Format controller-visible and evaluator-only panel diagnostics."""

    energy_access_label = exp002_energy_visibility_label(frame, condition)
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
    coverage_text = (
        f"coverage [EVALUATOR-ONLY]: {frame.visited_cell_count} / 1024 "
        f"({100.0 * frame.coverage_fraction:.2f}%), "
        f"remaining {frame.remaining_cell_count}"
    )
    lines = [
        f"step: {frame.step_index}",
        f"mode: {frame.mode.value}",
        f"next action: {action_text}",
        f"sense L/F/R: {sense_text}",
        energy_text,
        coverage_text,
    ]
    if condition is EXP001Condition.B:
        onset_energy = (
            "—"
            if frame.most_recent_seek_onset_energy is None
            else f"{frame.most_recent_seek_onset_energy:.3f}"
        )
        onset_distance = (
            "—"
            if frame.most_recent_seek_distance is None
            else f"{frame.most_recent_seek_distance:.3f}"
        )
        if frame.seek_attempt_active:
            reached_charge = "PENDING"
        elif frame.most_recent_seek_reached_charge is None:
            reached_charge = "—"
        else:
            reached_charge = (
                "YES" if frame.most_recent_seek_reached_charge else "NO"
            )
        lines.extend(
            (
                f"candidate: {candidate.value} threshold {candidate.enter_seek:.2f}",
                f"most recent SEEK onset energy [EVALUATOR-ONLY]: {onset_energy}",
                "most recent SEEK onset nearest-source distance "
                f"[EVALUATOR-ONLY]: {onset_distance}",
                "SEEK reached CHARGE: " + reached_charge,
            )
        )
    lines.append(f"status: {frame.terminal_status}{held_text}")
    return "\n".join(lines)


def exp002_energy_visibility_label(
    frame: EXP002VisualizationFrame,
    condition: EXP001Condition,
) -> str:
    """Return the canonical renderer energy-visibility label for one frame."""

    if condition is EXP001Condition.B and frame.controller_visible_energy is not None:
        return "CTRL + EVAL"
    return "EVAL ONLY"


def build_exp002_visualization_figure(
    result: EXP002DevelopmentBatchResult,
    seed: int | None = None,
) -> tuple[Figure, FuncAnimation]:
    """Build the three-panel EXP-002 animation without showing it."""

    data = build_exp002_visualization_frames(result, seed)
    figure, axes = plt.subplots(
        1,
        len(EXP001Condition),
        figsize=(20, 7.4),
        squeeze=False,
    )
    artists: list[dict[str, Any]] = []
    labels = {
        EXP001Condition.A: (
            "A — stochastic explorer",
            "Unchanged EXP-001 A; energy is not controller-visible",
        ),
        EXP001Condition.B: (
            f"B — interoceptive closed-loop ({data.candidate.value})",
            "Only SEEK-entry threshold varies in EXP-002",
        ),
        EXP001Condition.C: (
            "C — calibrated energy-blind open-loop",
            "Unchanged EXP-001 C: SHORT EXPLORE 10 / CHARGE 5",
        ),
    }
    resource_field = data.resource_field
    cell_centers = _coverage_cell_centers(data.world_min, data.world_max)

    for axis, condition in zip(axes[0], EXP001Condition):
        axis.set_xlim(data.world_min[0], data.world_max[0])
        axis.set_ylim(data.world_min[1], data.world_max[1])
        axis.set_aspect("equal", adjustable="box")
        axis.set_xlabel("x (evaluator view)")
        axis.set_ylabel("y (evaluator view)")
        title, mechanism_note = labels[condition]
        axis.set_title(f"{title}\n{mechanism_note}")
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
            zorder=4,
        )
        coverage_scatter = axis.scatter(
            [center[0] for center in cell_centers],
            [center[1] for center in cell_centers],
            s=7,
            marker=".",
            color="#d1d5db",
            alpha=0.38,
            linewidths=0,
            zorder=2,
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
        energy_label = axis.text(
            0.9575,
            0.75,
            "",
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
            fontsize=7.5,
            family="monospace",
            zorder=10,
        )
        axis.text(
            0.02,
            0.02,
            "resource field + source coordinates: EVALUATOR-ONLY\n"
            "coverage cells and path: EVALUATOR-ONLY",
            transform=axis.transAxes,
            va="bottom",
            ha="left",
            fontsize=6.5,
            color="dimgray",
            zorder=10,
        )
        artists.append(
            {
                "coverage_scatter": coverage_scatter,
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
            coverage_scatter = artist_group["coverage_scatter"]
            path_x, path_y = zip(*frame.path)
            path_line.set_data(path_x, path_y)
            position_marker.set_data([frame.x], [frame.y])
            heading_arrow.set_offsets(np.asarray([[frame.x, frame.y]]))
            heading_arrow.set_UVC(
                np.asarray([frame.heading_vector[0]]),
                np.asarray([frame.heading_vector[1]]),
            )
            for probe_line, endpoint in zip(probe_lines, frame.probe_endpoints):
                probe_line.set_data([frame.x, endpoint[0]], [frame.y, endpoint[1]])
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
            energy_label.set_text(exp002_energy_visibility_label(frame, condition))
            summary_text.set_text(
                format_exp002_diagnostic_text(frame, condition, data.candidate)
            )
            coverage_scatter.set_facecolors(
                _coverage_colors(frame.visited_cells, EXP002_COVERAGE_GRID_WIDTH)
            )
            updated.extend(
                (
                    coverage_scatter,
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
        "EXP-002 DEVELOPMENT VISUALIZATION\n"
        "DESCRIPTIVE / SANITY CHECK ONLY — NOT CALIBRATION OR CONFIRMATORY EVIDENCE\n"
        f"seed {data.seed} — candidate {data.candidate.value}; "
        "evaluator-side renderer of matched A/B/C development episodes\n"
        "Evaluator-only source coordinates, source distances, coverage, and A/C "
        "energy are not controller-visible."
    )
    figure.tight_layout(rect=(0, 0, 1, 0.86))
    setattr(figure, "_aweform_animation", animation)
    return figure, animation


def show_exp002_development_visualization(
    result: EXP002DevelopmentBatchResult,
    seed: int | None = None,
) -> Figure:
    """Show one selected-seed A/B/C EXP-002 animation interactively."""

    figure, _animation = build_exp002_visualization_figure(result, seed)
    plt.show()
    return figure


def main(argv: Sequence[str] | None = None) -> int:
    """Run one ordinary development episode and open the renderer."""

    parser = argparse.ArgumentParser(
        description=(
            "Open the EXP-002 development-only evaluator visualizer. "
            "This is not calibration or scientific analysis."
        )
    )
    parser.add_argument("--seed", type=_non_negative_int, required=True)
    parser.add_argument(
        "--candidate",
        choices=tuple(candidate.value for candidate in EXP002BCandidate),
        required=True,
    )
    args = parser.parse_args(argv)
    try:
        validated_seed = validate_exp002_development_seeds((args.seed,))[0]
    except ValueError as error:
        parser.error(str(error))
    candidate = EXP002BCandidate(args.candidate)
    result = run_exp002_development_batch(
        seeds=[validated_seed],
        env_config=FROZEN_EXP001_CALIBRATION_ENV_CONFIG,
        candidate=candidate,
    )
    show_exp002_development_visualization(result, validated_seed)
    return 0


def _record_frames(
    record: EXP002EpisodeRecord,
    diagnostic: EXP002EpisodeDiagnostics,
    environment_config: AweformEnvConfig,
) -> tuple[EXP002VisualizationFrame, ...]:
    failure_boundary = environment_config.energy.failure_boundary
    energy_range = (
        environment_config.energy.maximum_energy - failure_boundary
    )
    initial = record.initial_state
    coverage_states = exp002_coverage_grid_states(record)
    seek_states = _seek_view_states(record)
    if len(coverage_states) != len(record.transitions) + 1:
        raise ValueError("coverage state count does not match EXP-002 trajectory")
    if len(seek_states) != len(record.transitions) + 1:
        raise ValueError("SEEK diagnostic state count does not match trajectory")
    if coverage_states[-1].visited_cell_count != diagnostic.visited_cell_count:
        raise ValueError("visualized coverage disagrees with evaluator diagnostics")
    if coverage_states[-1].remaining_cell_count != diagnostic.remaining_cell_count:
        raise ValueError("visualized remaining coverage disagrees with diagnostics")
    if coverage_states[-1].coverage_fraction != diagnostic.coverage_fraction:
        raise ValueError("visualized coverage fraction disagrees with diagnostics")

    frames: list[EXP002VisualizationFrame] = []
    path = [initial.position]
    for transition_index, transition in enumerate(record.transitions):
        evaluator = transition.privileged_evaluator
        expected_step = transition_index + 1
        if evaluator.step_index != expected_step:
            raise ValueError(
                "EXP-002 transition steps must start at 1 and increase by one; "
                f"got {evaluator.step_index} at position {expected_step}"
            )
        if transition_index == 0:
            position = initial.position
            heading = initial.heading
            actual_energy = initial.actual_energy
        else:
            previous = record.transitions[transition_index - 1].privileged_evaluator
            position = previous.position_after
            heading = previous.heading
            actual_energy = previous.actual_energy_after
        frame = _frame_base(
            position=position,
            heading=heading,
            actual_energy=actual_energy,
            path=path,
            mode=evaluator.controller_mode,
            coverage=coverage_states[transition_index],
            seek_state=seek_states[transition_index],
            environment_config=environment_config,
            failure_boundary=failure_boundary,
            energy_range=energy_range,
        )
        observation = transition.controller_visible.observation
        if isinstance(observation, InteroceptiveObservation):
            external = observation.external
            controller_energy = observation.energy
        else:
            assert isinstance(observation, ExternalObservation)
            external = observation
            controller_energy = None
        frames.append(
            replace(
                frame,
                next_action=evaluator.action,
                left_resource=external.left_resource,
                forward_resource=external.forward_resource,
                right_resource=external.right_resource,
                controller_visible_energy=controller_energy,
            )
        )
        path.append(evaluator.position_after)

    final_transition = record.transitions[-1] if record.transitions else None
    final_evaluator = (
        None
        if final_transition is None
        else final_transition.privileged_evaluator
    )
    final_position = path[-1]
    final_heading = (
        initial.heading
        if final_evaluator is None
        else final_evaluator.heading
    )
    final_energy = (
        initial.actual_energy
        if final_evaluator is None
        else final_evaluator.actual_energy_after
    )
    final_mode = (
        EXP001Mode.EXPLORE
        if final_evaluator is None
        else final_evaluator.controller_mode
    )
    final_frame = _frame_base(
        position=final_position,
        heading=final_heading,
        actual_energy=final_energy,
        path=path,
        mode=final_mode,
        coverage=coverage_states[-1],
        seek_state=seek_states[-1],
        environment_config=environment_config,
        failure_boundary=failure_boundary,
        energy_range=energy_range,
    )
    frames.append(
        replace(
            final_frame,
            step_index=len(record.transitions),
            terminal_status=_terminal_status(final_evaluator),
        )
    )
    return tuple(frames)


def _frame_base(
    *,
    position: tuple[float, float],
    heading: float,
    actual_energy: float,
    path: list[tuple[float, float]],
    mode: EXP001Mode,
    coverage: Any,
    seek_state: _SeekViewState,
    environment_config: AweformEnvConfig,
    failure_boundary: float,
    energy_range: float,
) -> EXP002VisualizationFrame:
    heading_vector, probe_endpoints = _frame_geometry(
        position,
        heading,
        environment_config,
    )
    return EXP002VisualizationFrame(
        step_index=len(path) - 1,
        x=position[0],
        y=position[1],
        heading=heading,
        heading_vector=heading_vector,
        probe_endpoints=probe_endpoints,
        actual_normalized_energy=(actual_energy - failure_boundary) / energy_range,
        path=tuple(path),
        mode=mode,
        next_action=None,
        left_resource=None,
        forward_resource=None,
        right_resource=None,
        controller_visible_energy=None,
        visited_cells=coverage.visited_cells,
        visited_cell_count=coverage.visited_cell_count,
        remaining_cell_count=coverage.remaining_cell_count,
        coverage_fraction=coverage.coverage_fraction,
        most_recent_seek_onset_energy=seek_state.onset_energy,
        most_recent_seek_distance=seek_state.distance,
        seek_attempt_active=seek_state.active,
        most_recent_seek_reached_charge=seek_state.reached_charge,
        terminal_status="running",
    )


def _seek_view_states(record: EXP002EpisodeRecord) -> tuple[_SeekViewState, ...]:
    states = [_SeekViewState(None, None, False, None)]
    onset_energy: float | None = None
    distance: float | None = None
    active = False
    reached_charge: bool | None = None
    for transition in record.transitions:
        evaluator = transition.privileged_evaluator
        if _entered_seek(record, evaluator):
            onset_energy = _normalized_energy(evaluator.actual_energy_before)
            distance = min(
                math.dist(evaluator.position_before, source)
                for source in record.initial_state.source_positions
            )
            active = True
            reached_charge = False
        if active and evaluator.controller_mode is EXP001Mode.CHARGE:
            active = False
            reached_charge = True
        elif active and (evaluator.terminated or evaluator.truncated):
            active = False
            reached_charge = False
        states.append(
            _SeekViewState(onset_energy, distance, active, reached_charge)
        )
    return tuple(states)


def _entered_seek(record: EXP002EpisodeRecord, evaluator: Any) -> bool:
    return (
        record.condition is EXP001Condition.B
        and evaluator.controller_mode_before_action is EXP001Mode.EXPLORE
        and evaluator.controller_mode
        in (EXP001Mode.SEEK_RESOURCE, EXP001Mode.CHARGE)
        and _normalized_energy(evaluator.actual_energy_before)
        < record.candidate.enter_seek
    )


def _normalized_energy(actual_energy: float) -> float:
    energy = FROZEN_EXP001_CALIBRATION_ENV_CONFIG.energy
    return (actual_energy - energy.failure_boundary) / (
        energy.maximum_energy - energy.failure_boundary
    )


def _coverage_cell_centers(
    world_min: tuple[float, float],
    world_max: tuple[float, float],
) -> tuple[tuple[float, float], ...]:
    cell_width = (world_max[0] - world_min[0]) / EXP002_COVERAGE_GRID_WIDTH
    cell_height = (world_max[1] - world_min[1]) / EXP002_COVERAGE_GRID_HEIGHT
    return tuple(
        (
            world_min[0] + (column + 0.5) * cell_width,
            world_min[1] + (row + 0.5) * cell_height,
        )
        for row in range(EXP002_COVERAGE_GRID_HEIGHT)
        for column in range(EXP002_COVERAGE_GRID_WIDTH)
    )


def _coverage_colors(
    visited_cells: tuple[tuple[int, int], ...],
    width: int,
) -> np.ndarray:
    visited_indices = {row * width + column for row, column in visited_cells}
    colors = np.zeros((EXP002_COVERAGE_GRID_WIDTH * EXP002_COVERAGE_GRID_HEIGHT, 4))
    for index in range(len(colors)):
        if index in visited_indices:
            colors[index] = (0.09, 0.64, 0.31, 0.75)
        else:
            colors[index] = (0.82, 0.84, 0.87, 0.32)
    return colors


def _pad_terminal_frames(
    frames: tuple[EXP002VisualizationFrame, ...],
    maximum_length: int,
) -> tuple[EXP002VisualizationFrame, ...]:
    if not frames:
        raise ValueError("EXP-002 episode produced no visualization frames")
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
