"""Canonical post-hoc visualizer for Aweform development traces.

The renderer in this module consumes only :class:`DevelopmentVisualizationData`.
Development-specific runners are deliberately kept behind small adapters that
turn completed evaluator traces into that neutral model before any Matplotlib
objects are created.
"""

from __future__ import annotations

import argparse
import itertools
import math
from dataclasses import dataclass
from typing import Callable, Final, Mapping, Sequence

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation
from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Polygon, Rectangle
from matplotlib.text import Text

from . import d011
from .d021 import D021Mode, D021TransitionTrace

Coordinate = tuple[float, float]


def _cumulative_mean_series(values: Sequence[float]) -> tuple[float, ...]:
    """Return the prefix mean at each position in a non-empty sequence."""
    if not values:
        raise ValueError("cumulative mean series requires at least one value")
    total = 0.0
    means: list[float] = []
    for index, value in enumerate(values, start=1):
        total += value
        means.append(total / index)
    return tuple(means)


def _mae_axis_upper_bound(
    learned_mae: Sequence[float], baseline_mae: Sequence[float]
) -> float:
    """Return a target-specific MAE upper bound with modest headroom."""
    largest_mae = max((*learned_mae, *baseline_mae), default=0.0)
    if largest_mae == 0.0:
        return 1.0e-6
    return largest_mae * 1.1


@dataclass(frozen=True, slots=True)
class DevelopmentVisualizationRange:
    """Inclusive numeric range used by a diagnostic gauge."""

    lower: float
    upper: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.lower) or not math.isfinite(self.upper):
            raise ValueError("visualization ranges must be finite")
        if self.lower >= self.upper:
            raise ValueError("visualization range lower bound must be below upper")


@dataclass(frozen=True, slots=True)
class DevelopmentVisualizationVisibility:
    """Evaluator/organism visibility labels shown by the shared renderer."""

    position_heading: str
    station_location: str
    energy: str
    thermal: str
    charging_contact: str
    action_decision_mode: str


@dataclass(frozen=True, slots=True)
class DevelopmentVisualizationFrame:
    """One completed-transition state in a neutral evaluator display trace."""

    transition_index: int
    x: float
    y: float
    heading: float
    action: str
    decision_mode: str
    energy: float
    thermal: float
    charging_contact: bool
    terminated: bool
    truncated: bool
    beacon_left: float | None = None
    beacon_forward: float | None = None
    beacon_right: float | None = None
    thermal_normalized: float | None = None
    thermal_absolute_c: float | None = None
    charger_phase: str | None = None
    simulated_seconds: float | None = None
    charging_contact_before: bool | None = None
    trajectory_break_before: bool = False

    def __post_init__(self) -> None:
        if self.transition_index < 0:
            raise ValueError("transition_index must be non-negative")
        for name in ("x", "y", "heading", "energy", "thermal"):
            if not math.isfinite(getattr(self, name)):
                raise ValueError(f"{name} must be finite")
        if not self.action or not self.decision_mode:
            raise ValueError("action and decision_mode labels must be non-empty")
        if not isinstance(self.charging_contact, bool):
            raise ValueError("charging_contact must be a bool")
        if not isinstance(self.terminated, bool) or not isinstance(
            self.truncated, bool
        ):
            raise ValueError("termination flags must be bools")
        beacon_values = (self.beacon_left, self.beacon_forward, self.beacon_right)
        if any(value is not None for value in beacon_values) and not all(
            value is not None for value in beacon_values
        ):
            raise ValueError("directional beacon values must be complete or absent")
        for value in beacon_values:
            if value is not None and (
                not math.isfinite(value) or not 0.0 <= value <= 1.0
            ):
                raise ValueError("directional beacon values must be in [0.0, 1.0]")
        if self.thermal_normalized is not None and (
            not math.isfinite(self.thermal_normalized)
            or not 0.0 <= self.thermal_normalized <= 1.0
        ):
            raise ValueError("thermal_normalized must be finite and in [0.0, 1.0]")
        if self.thermal_absolute_c is not None and not math.isfinite(
            self.thermal_absolute_c
        ):
            raise ValueError("thermal_absolute_c must be finite")
        if self.charger_phase is not None and not self.charger_phase:
            raise ValueError("charger_phase must be non-empty")
        if self.simulated_seconds is not None and (
            not math.isfinite(self.simulated_seconds) or self.simulated_seconds < 0.0
        ):
            raise ValueError("simulated_seconds must be finite and non-negative")
        if self.charging_contact_before is not None and not isinstance(
            self.charging_contact_before, bool
        ):
            raise ValueError("charging_contact_before must be a bool")
        if not isinstance(self.trajectory_break_before, bool):
            raise ValueError("trajectory_break_before must be a bool")


@dataclass(frozen=True, slots=True)
class DevelopmentConsequencePredictionFrame:
    """Evaluator-only one-step prediction and observed consequence values."""

    transition_index: int
    predicted_delta_energy: float
    observed_delta_energy: float
    predicted_delta_thermal: float
    observed_delta_thermal: float
    predicted_delta_charging_contact: float
    observed_delta_charging_contact: float

    def __post_init__(self) -> None:
        if self.transition_index <= 0:
            raise ValueError("transition_index must be positive")
        for name in (
            "predicted_delta_energy",
            "observed_delta_energy",
            "predicted_delta_thermal",
            "observed_delta_thermal",
            "predicted_delta_charging_contact",
            "observed_delta_charging_contact",
        ):
            if not math.isfinite(getattr(self, name)):
                raise ValueError(f"{name} must be finite")


@dataclass(frozen=True, slots=True)
class DevelopmentActionAlternative:
    """Evaluator-only one-step consequence for one candidate action."""

    transition_index: int
    action: str
    physically_executed: bool
    prior_exact_support_count: int
    predicted_delta_energy: float
    actual_delta_energy: float
    predicted_delta_thermal: float
    actual_delta_thermal: float
    predicted_delta_charging_contact: float
    actual_delta_charging_contact: float

    def __post_init__(self) -> None:
        if self.transition_index <= 0:
            raise ValueError("transition_index must be positive")
        if not self.action:
            raise ValueError("action must be non-empty")
        if not isinstance(self.physically_executed, bool):
            raise ValueError("physically_executed must be a bool")
        if (
            isinstance(self.prior_exact_support_count, bool)
            or not isinstance(self.prior_exact_support_count, int)
            or self.prior_exact_support_count < 0
        ):
            raise ValueError("prior_exact_support_count must be a non-negative int")
        for name in (
            "predicted_delta_energy",
            "actual_delta_energy",
            "predicted_delta_thermal",
            "actual_delta_thermal",
            "predicted_delta_charging_contact",
            "actual_delta_charging_contact",
        ):
            if not math.isfinite(getattr(self, name)):
                raise ValueError(f"{name} must be finite")
@dataclass(frozen=True, slots=True)
class DevelopmentShadowGeometry:
    """Optional evaluator-only shadow morphology for a shared replay."""

    body_length: float
    body_width: float
    rear_contact_plus: Coordinate
    rear_contact_minus: Coordinate
    front_midpoint: Coordinate
    dock_orientation: float
    dock_contact_plus: Coordinate
    dock_contact_minus: Coordinate

    def __post_init__(self) -> None:
        for name in ("body_length", "body_width"):
            value = getattr(self, name)
            if not math.isfinite(value) or value <= 0.0:
                raise ValueError(f"{name} must be finite and positive")
        if not math.isfinite(self.dock_orientation):
            raise ValueError("dock_orientation must be finite")
        for name in (
            "rear_contact_plus",
            "rear_contact_minus",
            "front_midpoint",
            "dock_contact_plus",
            "dock_contact_minus",
        ):
            _validate_coordinate(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class DevelopmentCausalGeometry:
    """Causal evaluator geometry for a development replay."""

    body_length: float
    body_width: float
    rear_contact_plus: Coordinate
    rear_contact_minus: Coordinate
    front_midpoint: Coordinate
    dock_orientation: float
    dock_contact_plus: Coordinate
    dock_contact_minus: Coordinate
    contact_tolerance: float

    def __post_init__(self) -> None:
        for name in ("body_length", "body_width", "contact_tolerance"):
            value = getattr(self, name)
            if not math.isfinite(value) or value <= 0.0:
                raise ValueError(f"{name} must be finite and positive")
        if not math.isfinite(self.dock_orientation):
            raise ValueError("dock_orientation must be finite")
        for name in (
            "rear_contact_plus",
            "rear_contact_minus",
            "front_midpoint",
            "dock_contact_plus",
            "dock_contact_minus",
        ):
            _validate_coordinate(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class DevelopmentVisualizationData:
    """All neutral data required by the shared development renderer."""

    source_label: str
    seed: int | None
    world_min: Coordinate
    world_max: Coordinate
    station_center: Coordinate | None
    charging_radius: float | None
    energy_range: DevelopmentVisualizationRange
    thermal_range: DevelopmentVisualizationRange
    frames: tuple[DevelopmentVisualizationFrame, ...]
    visibility: DevelopmentVisualizationVisibility
    probe_distance: float | None = None
    sensor_angle: float | None = None
    thermal_threshold: float | None = None
    thermal_threshold_label: str | None = None
    energy_label: str = "ENERGY"
    mode_display_label: str = "decision mode"
    consequence_predictions: (
        tuple[DevelopmentConsequencePredictionFrame, ...] | None
    ) = None
    action_alternatives: (
        tuple[tuple[DevelopmentActionAlternative, ...], ...] | None
    ) = None
    action_alternative_warning: str | None = None
    action_alternative_provenance: str | None = None
    shadow_geometry: DevelopmentShadowGeometry | None = None
    causal_geometry: DevelopmentCausalGeometry | None = None

    def __post_init__(self) -> None:
        if not self.source_label:
            raise ValueError("source_label must be non-empty")
        if not self.energy_label:
            raise ValueError("energy_label must be non-empty")
        if self.seed is not None and (
            isinstance(self.seed, bool) or not isinstance(self.seed, int)
        ):
            raise ValueError("seed must be an integer or None")
        if not self.mode_display_label:
            raise ValueError("mode_display_label must be non-empty")
        _validate_coordinate("world_min", self.world_min)
        _validate_coordinate("world_max", self.world_max)
        if not all(
            lower < upper for lower, upper in zip(self.world_min, self.world_max)
        ):
            raise ValueError("world_min must be strictly below world_max")
        if not self.frames:
            raise ValueError("visualization data must contain at least one frame")
        if any(
            frame.transition_index < 0
            or (
                index > 0
                and frame.transition_index <= self.frames[index - 1].transition_index
            )
            for index, frame in enumerate(self.frames)
        ):
            raise ValueError("frames must contain strictly increasing transitions")
        if self.consequence_predictions is not None:
            if len(self.consequence_predictions) != len(self.frames):
                raise ValueError(
                    "consequence predictions must align one-to-one with frames"
                )
            if any(
                prediction.transition_index != frame.transition_index
                for prediction, frame in zip(
                    self.consequence_predictions, self.frames, strict=True
                )
            ):
                raise ValueError(
                    "consequence prediction indices must align with frames"
                )
        if self.action_alternatives is not None:
            if len(self.action_alternatives) != len(self.frames):
                raise ValueError(
                    "action alternatives must align one-to-one with frames"
                )
            for frame, alternatives in zip(
                self.frames, self.action_alternatives, strict=True
            ):
                if len(alternatives) != 4:
                    raise ValueError(
                        "each action alternative group must contain four candidates"
                    )
                if sum(
                    alternative.physically_executed for alternative in alternatives
                ) != 1:
                    raise ValueError(
                        "each action alternative group needs exactly one executed"
                    )
                executed = next(
                    alternative
                    for alternative in alternatives
                    if alternative.physically_executed
                )
                if executed.action != frame.action:
                    raise ValueError(
                        "executed action alternative must match the real frame action"
                    )
                if any(
                    alternative.transition_index != frame.transition_index
                    for alternative in alternatives
                ):
                    raise ValueError(
                        "action alternative indices must align with frames"
                    )
                if len({alternative.action for alternative in alternatives}) != 4:
                    raise ValueError(
                        "action alternatives must have four unique actions"
                    )
            for name in ("action_alternative_warning", "action_alternative_provenance"):
                value = getattr(self, name)
                if not isinstance(value, str) or not value:
                    raise ValueError(
                        f"{name} is required when action alternatives are present"
                    )
        if self.station_center is None:
            if self.charging_radius is not None:
                raise ValueError("charging_radius requires station_center")
        else:
            _validate_coordinate("station_center", self.station_center)
            if (
                self.charging_radius is None
                and self.causal_geometry is None
            ) or (
                self.charging_radius is not None
                and not math.isfinite(self.charging_radius)
            ):
                raise ValueError("station visualizations require a finite radius")
            if self.charging_radius is not None and self.charging_radius < 0:
                raise ValueError("charging_radius must be non-negative")
        if self.shadow_geometry is not None and self.station_center is None:
            raise ValueError("shadow geometry requires station_center")
        if self.causal_geometry is not None and self.station_center is None:
            raise ValueError("causal geometry requires station_center")
        if self.shadow_geometry is not None and self.causal_geometry is not None:
            raise ValueError("shadow and causal geometry cannot be combined")
        if (self.probe_distance is None) != (self.sensor_angle is None):
            raise ValueError("probe_distance and sensor_angle must be paired")
        for name in ("probe_distance", "sensor_angle"):
            value = getattr(self, name)
            if value is not None and (not math.isfinite(value) or value < 0.0):
                raise ValueError(f"{name} must be finite and non-negative")
        if self.thermal_threshold is not None:
            if not math.isfinite(self.thermal_threshold):
                raise ValueError("thermal_threshold must be finite")
            if not self.thermal_range.lower <= self.thermal_threshold <= (
                self.thermal_range.upper
            ):
                raise ValueError("thermal_threshold must be inside thermal_range")
            if not self.thermal_threshold_label:
                raise ValueError("thermal_threshold_label is required with threshold")
        elif self.thermal_threshold_label is not None:
            raise ValueError("thermal_threshold_label requires thermal_threshold")


class DevelopmentVisualizationPlayer:
    """Pure display state for replaying a completed visualization trace."""

    def __init__(self, frame_count: int) -> None:
        if isinstance(frame_count, bool) or not isinstance(frame_count, int):
            raise ValueError("frame_count must be an integer")
        if frame_count <= 0:
            raise ValueError("frame_count must be positive")
        self._frame_count = frame_count
        self._frame_index = 0
        self._playing = False

    @property
    def frame_count(self) -> int:
        return self._frame_count

    @property
    def frame_index(self) -> int:
        return self._frame_index

    @property
    def playing(self) -> bool:
        return self._playing

    def toggle_play_pause(self) -> bool:
        """Toggle playback and return the new playback state."""
        self._playing = not self._playing
        return self._playing

    def play(self) -> None:
        self._playing = True

    def pause(self) -> None:
        self._playing = False

    def step_forward(self) -> int:
        """Advance one frame, clamped at the final recorded frame."""
        self._frame_index = min(self._frame_index + 1, self._frame_count - 1)
        return self._frame_index

    def step_backward(self) -> int:
        """Move back one frame, clamped at the first recorded frame."""
        if not self._playing:
            self._frame_index = max(self._frame_index - 1, 0)
        return self._frame_index

    def restart(self) -> int:
        """Return the display to the first recorded frame."""
        self._frame_index = 0
        return self._frame_index


def _trajectory_line_coordinates(
    frames: Sequence[DevelopmentVisualizationFrame],
) -> tuple[list[float], list[float]]:
    """Return displayed coordinates with explicit breaks between source gaps."""
    x_values: list[float] = []
    y_values: list[float] = []
    for frame in frames:
        if frame.trajectory_break_before:
            x_values.append(math.nan)
            y_values.append(math.nan)
        x_values.append(frame.x)
        y_values.append(frame.y)
    return x_values, y_values


def build_development_visualization_figure(
    data: DevelopmentVisualizationData,
    *,
    interval_ms: int = 90,
) -> tuple[Figure, FuncAnimation]:
    """Build a replay figure without executing a runner or opening a GUI."""
    if isinstance(interval_ms, bool) or not isinstance(interval_ms, int):
        raise ValueError("interval_ms must be an integer")
    if interval_ms <= 0:
        raise ValueError("interval_ms must be positive")

    has_action_alternatives = data.action_alternatives is not None
    has_consequence_predictions = data.consequence_predictions is not None
    alternative_axis: Axes | None = None
    learner_axes: list[Axes] = []
    if has_action_alternatives:
        # Keep this evaluator-heavy layout deterministic. Constrained layout
        # measures text artists on every draw, so changing frame labels can
        # resize/reposition the axes during playback.
        figure = plt.figure(figsize=(20, 8))
        figure.subplots_adjust(
            left=0.03,
            right=0.99,
            bottom=0.12,
            top=0.90,
            wspace=0.18,
        )
        grid = figure.add_gridspec(
            1,
            3,
            width_ratios=(1.30, 0.92, 1.35),
        )
        world_axis = figure.add_subplot(grid[0, 0])
        diagnostic_axis = figure.add_subplot(grid[0, 1])
        alternative_axis = figure.add_subplot(grid[0, 2])
    elif has_consequence_predictions:
        figure = plt.figure(figsize=(18, 8), constrained_layout=True)
        grid = figure.add_gridspec(
            3,
            3,
            width_ratios=(1.35, 0.85, 1.25),
            hspace=0.85,
            wspace=0.35,
        )
        world_axis = figure.add_subplot(grid[:, 0])
        diagnostic_axis = figure.add_subplot(grid[:, 1])
        learner_axes = [figure.add_subplot(grid[index, 2]) for index in range(3)]
    else:
        figure, axes = plt.subplots(
            1,
            2,
            figsize=(13, 7),
            gridspec_kw={"width_ratios": (1.35, 0.85)},
        )
        world_axis, diagnostic_axis = axes
    world_axis.set_xlim(data.world_min[0], data.world_max[0])
    world_axis.set_ylim(data.world_min[1], data.world_max[1])
    world_axis.set_aspect("equal", adjustable="box")
    if has_action_alternatives:
        world_axis.set_anchor("NW")
    world_axis.set_xlabel("x (evaluator view)")
    world_axis.set_ylabel("y (evaluator view)")
    world_axis.set_title("2D EVALUATOR WORLD")
    world_axis.add_patch(
        Rectangle(
            data.world_min,
            data.world_max[0] - data.world_min[0],
            data.world_max[1] - data.world_min[1],
            fill=False,
            edgecolor="black",
            linewidth=1.2,
            label="world boundary",
        )
    )

    if data.station_center is not None:
        if data.charging_radius is not None:
            world_axis.add_patch(
                Circle(
                    data.station_center,
                    data.charging_radius,
                    facecolor="tab:green",
                    edgecolor="tab:green",
                    alpha=0.15,
                    linewidth=1.5,
                    label="charging radius",
                )
            )
        world_axis.plot(
            [data.station_center[0]],
            [data.station_center[1]],
            marker="*",
            markersize=14,
            color="tab:green",
            linestyle="None",
            label="station centre",
        )

    geometry = data.causal_geometry or data.shadow_geometry
    geometry_body: Polygon | None = None
    geometry_front_direction: Line2D | None = None
    geometry_rear_contacts: Line2D | None = None
    geometry_front_midpoint: Line2D | None = None
    geometry_dock_contacts: Line2D | None = None
    geometry_dock_axis: Line2D | None = None
    geometry_overlay_label: Text | None = None
    if geometry is not None:
        if data.station_center is None:
            raise RuntimeError("geometry has no station center")
        causal = data.causal_geometry is not None
        geometry_body = Polygon(
            _shadow_body_corners(
                (0.0, 0.0), 0.0, geometry.body_length, geometry.body_width
            ),
            closed=True,
            facecolor="tab:purple",
            edgecolor="tab:purple",
            alpha=0.18,
            linewidth=1.5,
            label=(
                "causal finite-body footprint" if causal else "shadow body footprint"
            ),
        )
        world_axis.add_patch(geometry_body)
        geometry_front_direction = world_axis.plot(
            [], [], color="tab:orange", linewidth=2.0,
            label=("causal body heading" if causal else "shadow front direction"),
        )[0]
        geometry_rear_contacts = world_axis.plot(
            [], [], marker="s", markersize=5, linestyle="None", color="tab:red",
            label=("causal rear contacts" if causal else "shadow rear contacts"),
        )[0]
        geometry_front_midpoint = world_axis.plot(
            [], [], marker="x", markersize=7, linestyle="None", color="#e377c2",
            label=("causal front midpoint" if causal else "front midpoint comparator"),
        )[0]
        geometry_dock_contacts = world_axis.plot(
            [geometry.dock_contact_plus[0], geometry.dock_contact_minus[0]],
            [geometry.dock_contact_plus[1], geometry.dock_contact_minus[1]],
            marker="D",
            markersize=4,
            color="tab:green",
            linewidth=2.0,
            label=(
                "fixed causal dock contacts"
                if causal
                else "one audit orientation dock contacts"
            ),
        )[0]
        geometry_dock_axis = world_axis.plot(
            [
                data.station_center[0],
                data.station_center[0]
                + 0.07 * math.cos(geometry.dock_orientation),
            ],
            [
                data.station_center[1],
                data.station_center[1]
                + 0.07 * math.sin(geometry.dock_orientation),
            ],
            color="tab:green",
            linestyle="--",
            linewidth=1.2,
            label=(
                "fixed causal dock outward axis"
                if causal
                else "one audit orientation outward axis"
            ),
        )[0]
        if causal:
            causal_geometry = data.causal_geometry
            if causal_geometry is None:
                raise RuntimeError("causal geometry disappeared")
            geometry_text = (
                "CAUSAL D-024 FINITE-BODY DUAL-CONTACT GEOMETRY\n"
                "CONTROLS THE BINARY CHARGING CONTACT PREDICATE\n"
                f"FIXED DOCK: phi={geometry.dock_orientation:g}; "
                f"PAIR TOLERANCE <= {causal_geometry.contact_tolerance:g}\n"
                "GEOMETRY IS EVALUATOR-ONLY; ORGANISM SEES BINARY CONTACT"
            )
        else:
            geometry_text = (
                "EVALUATOR-ONLY SHADOW MORPHOLOGY\n"
                "DOES NOT CONTROL CHARGING OR BEHAVIOUR\n"
                f"ONE AUDIT ORIENTATION: phi={geometry.dock_orientation:g}"
            )
        if has_action_alternatives:
            geometry_overlay_label = figure.text(
                0.03,
                0.965,
                geometry_text,
                va="top",
                fontsize=8,
                color=("tab:blue" if causal else "tab:purple"),
                bbox={
                    "facecolor": "white",
                    "alpha": 0.8,
                    "edgecolor": ("tab:blue" if causal else "tab:purple"),
                },
            )
        else:
            geometry_overlay_label = world_axis.text(
                0.02,
                0.03,
                geometry_text,
                transform=world_axis.transAxes,
                va="bottom",
                fontsize=8,
                color=("tab:blue" if causal else "tab:purple"),
                bbox={
                    "facecolor": "white",
                    "alpha": 0.8,
                    "edgecolor": ("tab:blue" if causal else "tab:purple"),
                },
            )
        if not has_action_alternatives:
            world_axis.legend(loc="lower left", fontsize=8)

    trajectory_line, *_ = world_axis.plot(
        [], [], color="tab:blue", alpha=0.5, linewidth=1.8, label="trajectory"
    )
    body_marker, *_ = world_axis.plot(
        [],
        [],
        marker="o",
        color="tab:blue",
        markersize=8,
        linestyle="None",
        label="body",
    )
    heading_arrow = world_axis.quiver(
        [], [], [], [], angles="xy", scale_units="xy", scale=5, color="tab:orange"
    )
    beacon_values_available = _has_directional_beacon(data)
    probe_lines: list[Line2D] = []
    if beacon_values_available and data.probe_distance is not None:
        probe_lines = [
            world_axis.plot([], [], color=color, linewidth=1.2, label=label)[0]
            for color, label in (
                ("#6a3d9a", "left directional probe"),
                ("#1f78b4", "forward directional probe"),
                ("#e31a1c", "right directional probe"),
            )
        ]
        if has_action_alternatives:
            figure.text(
                0.03,
                0.965,
                "directional probes = idealized beacon display\n"
                "(not literal RF beams)",
                va="top",
                fontsize=8,
            )
        else:
            world_axis.text(
                0.02,
                0.97,
                "directional probes = idealized beacon display\n"
                "(not literal RF beams)",
                transform=world_axis.transAxes,
                va="top",
                fontsize=8,
            )
    if not has_action_alternatives:
        world_axis.legend(loc="lower left", fontsize=8)
    else:
        legend_handles, legend_labels = world_axis.get_legend_handles_labels()
        figure.legend(
            legend_handles,
            legend_labels,
            loc="lower left",
            bbox_to_anchor=(0.03, 0.0, 0.31, 0.08),
            mode="expand",
            ncols=3,
            borderaxespad=0.0,
            fontsize=7,
            framealpha=0.85,
        )

    diagnostic_axis.set_xlim(0.0, 1.0)
    diagnostic_axis.set_ylim(-0.34, 1.15 if beacon_values_available else 1.0)
    diagnostic_axis.axis("off")
    diagnostic_axis.set_title("EVALUATOR DIAGNOSTICS", loc="left")
    if beacon_values_available:
        top_y = (1.06, 0.99, 0.92, 0.85, 0.78, 0.71)
        energy_y, thermal_y = 0.57, 0.43
    else:
        top_y = (0.86, 0.79, 0.72, 0.65, 0.58, 0.51)
        energy_y, thermal_y = 0.37, 0.21
    transition_text = diagnostic_axis.text(
        0.02, top_y[0], "", family="monospace", fontsize=11
    )
    action_text = diagnostic_axis.text(
        0.02, top_y[1], "", family="monospace", fontsize=11
    )
    mode_text = diagnostic_axis.text(
        0.02, top_y[2], "", family="monospace", fontsize=11
    )
    contact_text = diagnostic_axis.text(
        0.02, top_y[3], "", family="monospace", fontsize=11
    )
    status_text = diagnostic_axis.text(
        0.02, top_y[4], "", family="monospace", fontsize=11
    )
    charger_phase_text = diagnostic_axis.text(
        0.02, top_y[5], "", family="monospace", fontsize=11
    )

    energy_background, energy_fill, energy_value = _make_gauge(
        diagnostic_axis,
        y=energy_y,
        label=data.energy_label,
        visibility=data.visibility.energy,
        value_range=data.energy_range,
        color="tab:blue",
        label_above_bar=data.energy_label != "ENERGY",
    )
    thermal_background, thermal_fill, thermal_value = _make_gauge(
        diagnostic_axis,
        y=thermal_y,
        label="THERMAL",
        visibility=data.visibility.thermal,
        value_range=data.thermal_range,
    )
    del energy_background, thermal_background
    beacon_gauges: list[tuple[Rectangle, Rectangle, Text]] = []
    beacon_range = DevelopmentVisualizationRange(0.0, 1.0)
    if beacon_values_available:
        beacon_gauges = [
            _make_gauge(
                diagnostic_axis,
                y=y,
                label=label,
                visibility="CTRL + EVAL",
                value_range=beacon_range,
                color=color,
            )
            for y, label, color in (
                (0.30, "BEACON L", "#6a3d9a"),
                (0.20, "BEACON F", "#1f78b4"),
                (0.10, "BEACON R", "#e31a1c"),
            )
        ]
    threshold_marker: Line2D | None = None
    if data.thermal_threshold is not None:
        threshold_label = data.thermal_threshold_label
        if threshold_label is None:
            raise RuntimeError("thermal threshold label is missing")
        threshold_x = 0.30 + _gauge_fraction(
            data.thermal_threshold, data.thermal_range
        ) * 0.62
        threshold_marker = diagnostic_axis.plot(
            [threshold_x, threshold_x],
            [thermal_y - 0.055, thermal_y + 0.055],
            color="tab:red",
            linewidth=1.5,
        )[0]
        diagnostic_axis.text(
            threshold_x,
            thermal_y + 0.08,
            threshold_label,
            ha="center",
            va="bottom",
            fontsize=7,
            color="tab:red",
        )
    metadata_y = -0.04
    diagnostic_axis.text(
        0.02,
        metadata_y,
        "POSITION / HEADING: "
        f"{data.visibility.position_heading}\n"
        "STATION LOCATION: "
        f"{data.visibility.station_location}\n"
        "CHARGING CONTACT: "
        f"{data.visibility.charging_contact}\n"
        "ACTION / "
        f"{data.mode_display_label.upper()}: "
        f"{data.visibility.action_decision_mode}",
        va="top",
        fontsize=8,
        family="monospace",
    )
    diagnostic_axis.text(
        0.02,
        -0.28,
        "SPACE play/pause   ←/→ step while paused   R restart",
        fontsize=8,
        color="0.35",
    )

    learner_lines: list[tuple[Line2D, Line2D]] = []
    learner_stats: list[Text] = []
    if learner_axes:
        predictions = data.consequence_predictions
        if predictions is None:
            raise RuntimeError("learner axes require consequence predictions")
        target_specs: tuple[
            tuple[
                str,
                Callable[[DevelopmentConsequencePredictionFrame], float],
                Callable[[DevelopmentConsequencePredictionFrame], float],
            ],
            ...,
        ] = (
            (
                "ENERGY Δ",
                lambda item: item.predicted_delta_energy,
                lambda item: item.observed_delta_energy,
            ),
            (
                "THERMAL Δ",
                lambda item: item.predicted_delta_thermal,
                lambda item: item.observed_delta_thermal,
            ),
            (
                "CONTACT Δ",
                lambda item: item.predicted_delta_charging_contact,
                lambda item: item.observed_delta_charging_contact,
            ),
        )
        cumulative_mae_series: list[tuple[tuple[float, ...], tuple[float, ...]]] = []
        for index, (axis, (title, predicted_value, observed_value)) in enumerate(
            zip(learner_axes, target_specs, strict=True)
        ):
            learned_errors = tuple(
                abs(predicted_value(item) - observed_value(item))
                for item in predictions
            )
            baseline_errors = tuple(
                abs(observed_value(item)) for item in predictions
            )
            learned_mae = _cumulative_mean_series(learned_errors)
            baseline_mae = _cumulative_mean_series(baseline_errors)
            cumulative_mae_series.append((learned_mae, baseline_mae))
            axis.set_xlim(0.5, max(1.5, len(predictions) + 0.5))
            axis.set_ylim(0.0, _mae_axis_upper_bound(learned_mae, baseline_mae))
            axis.grid(True, alpha=0.25)
            axis.set_ylabel("MAE", fontsize=8)
            axis.set_xlabel("transition", fontsize=8)
            if index == 0:
                axis.set_title(
                    "SHADOW ONLY — ZERO BEHAVIOURAL INFLUENCE\n" + title,
                    fontsize=9,
                )
                axis.text(
                    0.0,
                    1.08,
                    "cumulative pre-update MAE through current transition",
                    transform=axis.transAxes,
                    fontsize=7,
                    va="bottom",
                )
            else:
                axis.set_title(title, fontsize=9)
            learned_line = axis.plot(
                [], [], color="tab:blue", linewidth=1.5, label="learned MAE"
            )[0]
            baseline_line = axis.plot(
                [],
                [],
                color="0.35",
                linestyle="--",
                linewidth=1.2,
                label="zero-change baseline MAE",
            )[0]
            axis.legend(fontsize=7, loc="lower right", framealpha=0.75)
            stats = axis.text(
                0.02,
                0.97,
                "",
                transform=axis.transAxes,
                va="top",
                fontsize=7,
                family="monospace",
                bbox={"facecolor": "white", "alpha": 0.75, "edgecolor": "none"},
            )
            learner_lines.append((learned_line, baseline_line))
            learner_stats.append(stats)

    alternative_rows: list[Text] = []
    alternative_warning: Text | None = None
    if alternative_axis is not None:
        alternative_axis.set_xlim(0.0, 1.0)
        alternative_axis.set_ylim(0.0, 1.0)
        alternative_axis.axis("off")
        alternative_axis.set_title(
            "ACTION ALTERNATIVES — EVALUATOR ONLY", loc="left", fontsize=11
        )
        if (
            data.action_alternative_warning is None
            or data.action_alternative_provenance is None
        ):
            raise RuntimeError(
                "action alternative display metadata is incomplete"
            )
        alternative_warning = alternative_axis.text(
            0.02,
            0.96,
            data.action_alternative_warning,
            va="top",
            fontsize=8.5,
            family="monospace",
            color="tab:red",
            bbox={
                "facecolor": "#fff4f4",
                "edgecolor": "tab:red",
                "linewidth": 1.0,
            },
        )
        alternative_axis.text(
            0.02,
            0.66,
            data.action_alternative_provenance,
            va="top",
            fontsize=8,
            family="monospace",
        )
        alternative_rows = [
            alternative_axis.text(
                0.02,
                y,
                "",
                va="top",
                fontsize=8.5,
                family="monospace",
                bbox={"facecolor": "white", "edgecolor": "0.7"},
            )
            for y in (0.54, 0.40, 0.26, 0.12)
        ]

    player = DevelopmentVisualizationPlayer(len(data.frames))

    def render(frame_index: int) -> tuple[Artist, ...]:
        frame = data.frames[frame_index]
        path = data.frames[: frame_index + 1]
        trajectory_line.set_data(*_trajectory_line_coordinates(path))
        body_marker.set_data([frame.x], [frame.y])
        heading_arrow.set_offsets([[frame.x, frame.y]])
        heading_arrow.set_UVC([math.cos(frame.heading)], [math.sin(frame.heading)])
        transition_label = f"transition: {frame.transition_index}"
        if frame.simulated_seconds is not None:
            transition_label += f"   simulated time: {frame.simulated_seconds:.1f} s"
        transition_text.set_text(transition_label)
        action_text.set_text(f"action: {frame.action}")
        mode_text.set_text(f"{data.mode_display_label}: {frame.decision_mode}")
        contact_text.set_text(
            "charging contact: " + ("YES" if frame.charging_contact else "NO")
        )
        status = (
            "TERMINATED"
            if frame.terminated
            else "TRUNCATED"
            if frame.truncated
            else "RUNNING"
        )
        status_text.set_text(f"status: {status}")
        charger_phase_text.set_text(
            "charger phase: "
            + (
                f"{frame.charger_phase} (EVALUATOR ONLY)"
                if frame.charger_phase is not None
                else "UNAVAILABLE (EVALUATOR ONLY)"
            )
        )
        energy_fill.set_width(_gauge_fraction(frame.energy, data.energy_range) * 0.62)
        thermal_fill.set_width(
            _gauge_fraction(frame.thermal, data.thermal_range) * 0.62
        )
        energy_value.set_text(f"{frame.energy:.3f} / {data.energy_range.upper:g}")
        if frame.thermal_normalized is not None:
            absolute = frame.thermal_absolute_c
            if absolute is None:
                absolute = frame.thermal
            thermal_value.set_text(
                f"{frame.thermal_normalized:.3f} norm / {absolute:.3f} °C"
            )
        else:
            thermal_value.set_text(
                f"{frame.thermal:.3f} / {data.thermal_range.upper:g}"
            )
        beacon_signals = (
            frame.beacon_left,
            frame.beacon_forward,
            frame.beacon_right,
        )
        if beacon_gauges:
            for (_background, fill, value), signal in zip(
                beacon_gauges, beacon_signals, strict=True
            ):
                if signal is None:
                    raise RuntimeError("beacon gauge requires a directional signal")
                fill.set_width(_gauge_fraction(signal, beacon_range) * 0.62)
                value.set_text(f"{signal:.3f}")
        rendered: list[Artist] = [
            trajectory_line,
            body_marker,
            heading_arrow,
            transition_text,
            action_text,
            mode_text,
            contact_text,
            status_text,
            charger_phase_text,
            energy_fill,
            thermal_fill,
            energy_value,
            thermal_value,
        ]
        if probe_lines:
            if data.probe_distance is None or data.sensor_angle is None:
                raise RuntimeError("directional probes require neutral probe metadata")
            endpoints = _probe_endpoints(frame, data)
            signals = beacon_signals
            if any(signal is None for signal in signals):
                raise RuntimeError("directional probe lines require beacon values")
            for line, endpoint, signal in zip(
                probe_lines, endpoints, signals, strict=True
            ):
                if signal is None:
                    raise RuntimeError("directional probe signal unexpectedly absent")
                line.set_data([frame.x, endpoint[0]], [frame.y, endpoint[1]])
                line.set_alpha(0.15 + 0.85 * signal)
                line.set_linewidth(0.8 + 2.0 * signal)
                rendered.append(line)
        for background, fill, value in beacon_gauges:
            del background
            rendered.extend((fill, value))
        if threshold_marker is not None:
            rendered.append(threshold_marker)
        if geometry is not None:
            if (
                geometry_body is None
                or geometry_front_direction is None
                or geometry_rear_contacts is None
                or geometry_front_midpoint is None
                or geometry_dock_contacts is None
                or geometry_dock_axis is None
            ):
                raise RuntimeError("geometry artists are incomplete")
            geometry_body.set_xy(
                _shadow_body_corners(
                    (frame.x, frame.y),
                    frame.heading,
                    geometry.body_length,
                    geometry.body_width,
                )
            )
            front = _translate_and_rotate(
                (frame.x, frame.y), frame.heading, geometry.front_midpoint
            )
            rear_plus = _translate_and_rotate(
                (frame.x, frame.y), frame.heading, geometry.rear_contact_plus
            )
            rear_minus = _translate_and_rotate(
                (frame.x, frame.y), frame.heading, geometry.rear_contact_minus
            )
            geometry_front_direction.set_data(
                [frame.x, frame.x + 0.07 * math.cos(frame.heading)],
                [frame.y, frame.y + 0.07 * math.sin(frame.heading)],
            )
            geometry_rear_contacts.set_data(
                [rear_plus[0], rear_minus[0]], [rear_plus[1], rear_minus[1]]
            )
            geometry_front_midpoint.set_data([front[0]], [front[1]])
            rendered.extend(
                (
                    geometry_body,
                    geometry_front_direction,
                    geometry_rear_contacts,
                    geometry_front_midpoint,
                    geometry_dock_contacts,
                    geometry_dock_axis,
                )
            )
            if geometry_overlay_label is not None:
                rendered.append(geometry_overlay_label)
        if learner_axes:
            predictions = data.consequence_predictions
            if predictions is None:
                raise RuntimeError("learner axes require consequence predictions")
            visible_predictions = predictions[: frame_index + 1]
            transition_numbers = [
                item.transition_index for item in visible_predictions
            ]
            for (learned_line, baseline_line), stats, (
                learned_mae_series,
                baseline_mae_series,
            ), (_title, predicted_value, observed_value) in zip(
                learner_lines,
                learner_stats,
                cumulative_mae_series,
                target_specs,
                strict=True,
            ):
                visible_learned_mae = learned_mae_series[: frame_index + 1]
                visible_baseline_mae = baseline_mae_series[: frame_index + 1]
                current = visible_predictions[-1]
                learned_line.set_data(transition_numbers, visible_learned_mae)
                baseline_line.set_data(transition_numbers, visible_baseline_mae)
                stats.set_text(
                    f"learned MAE: {visible_learned_mae[-1]:.5f}\n"
                    "zero-change baseline MAE: "
                    f"{visible_baseline_mae[-1]:.5f}\n"
                    f"current predicted Δ: {predicted_value(current):.5f}\n"
                    f"current observed Δ: {observed_value(current):.5f}"
                )
                rendered.extend((learned_line, baseline_line, stats))
        if alternative_axis is not None:
            alternatives = data.action_alternatives
            if alternatives is None:
                raise RuntimeError("alternative axis requires action alternatives")
            current_alternatives = alternatives[frame_index]
            for text_artist, alternative in zip(
                alternative_rows, current_alternatives, strict=True
            ):
                status = (
                    "REAL / EXECUTED"
                    if alternative.physically_executed
                    else "GHOST / UNEXECUTED"
                )
                text_artist.set_text(
                    f"{alternative.action:<13} {status}\n"
                    "prior exact real support: "
                    f"{alternative.prior_exact_support_count}\n"
                    f"E  pred {alternative.predicted_delta_energy:+.5f}"
                    f"  actual {alternative.actual_delta_energy:+.5f}\n"
                    f"T  pred {alternative.predicted_delta_thermal:+.5f}"
                    f"  actual {alternative.actual_delta_thermal:+.5f}\n"
                    f"C  pred {alternative.predicted_delta_charging_contact:+.5f}"
                    f"  actual {alternative.actual_delta_charging_contact:+.5f}"
                )
                text_artist.set_color(
                    "#155724" if alternative.physically_executed else "#444444"
                )
                text_artist.set_bbox({
                    "facecolor": (
                        "#e8f5e9" if alternative.physically_executed else "#f4f4f4"
                    ),
                    "edgecolor": (
                        "tab:green" if alternative.physically_executed else "0.7"
                    ),
                    "linewidth": 1.5 if alternative.physically_executed else 0.8,
                })
                rendered.append(text_artist)
            if alternative_warning is not None:
                rendered.append(alternative_warning)
        return tuple(rendered)

    render(0)

    def animate(_tick: int) -> tuple[Artist, ...]:
        if player.playing:
            player.step_forward()
            if player.frame_index == player.frame_count - 1:
                player.pause()
                _set_animation_running(animation, False)
        return render(player.frame_index)

    animation = FuncAnimation(
        figure,
        animate,
        frames=itertools.count(),
        interval=interval_ms,
        repeat=False,
        cache_frame_data=False,
    )
    # Render once so headless teardown does not emit Matplotlib's warning about
    # an animation being deleted before it has drawn anything.
    figure.canvas.draw()
    _set_animation_running(animation, False)

    def on_key(event: object) -> None:
        key = getattr(event, "key", None)
        if not isinstance(key, str):
            return
        normalized_key = key.lower()
        if normalized_key == " ":
            if player.toggle_play_pause():
                _set_animation_running(animation, True)
            else:
                _set_animation_running(animation, False)
        elif normalized_key in {"right", "arrowright"} and not player.playing:
            player.step_forward()
            render(player.frame_index)
            figure.canvas.draw_idle()
        elif normalized_key in {"left", "arrowleft"} and not player.playing:
            player.step_backward()
            render(player.frame_index)
            figure.canvas.draw_idle()
        elif normalized_key == "r":
            player.restart()
            render(player.frame_index)
            figure.canvas.draw_idle()

    figure.canvas.mpl_connect("key_press_event", on_key)
    suptitle = (
        "AWEFORM DEVELOPMENT VISUALIZER\n"
        f"{data.source_label} — "
        f"{'seedless fixed-state' if data.seed is None else f'seed {data.seed}'}\n"
        "DEVELOPMENT / EVALUATOR VIEW — NOT CONFIRMATORY EVIDENCE"
    )
    if has_action_alternatives:
        figure.suptitle(suptitle, y=0.995, fontsize=11, linespacing=1.0)
    else:
        figure.suptitle(suptitle, fontsize=12)
    if not learner_axes and alternative_axis is None:
        figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.91))
    setattr(figure, "_aweform_player", player)
    setattr(figure, "_aweform_animation", animation)
    setattr(figure, "_aweform_learner_axes", tuple(learner_axes))
    setattr(figure, "_aweform_learner_lines", tuple(learner_lines))
    setattr(figure, "_aweform_alternative_axis", alternative_axis)
    setattr(figure, "_aweform_alternative_rows", tuple(alternative_rows))
    setattr(
        figure,
        "_aweform_diagnostic_texts",
        (transition_text, action_text, mode_text, contact_text, status_text,
         charger_phase_text),
    )
    return figure, animation


def _translate_and_rotate(
    origin: Coordinate, heading: float, local: Coordinate
) -> Coordinate:
    """Transform one body-frame point into world coordinates for display."""
    return (
        origin[0] + local[0] * math.cos(heading) - local[1] * math.sin(heading),
        origin[1] + local[0] * math.sin(heading) + local[1] * math.cos(heading),
    )


def _shadow_body_corners(
    center: Coordinate, heading: float, length: float, width: float
) -> list[Coordinate]:
    """Return display corners in the current body frame."""
    local_corners = (
        (-length / 2.0, -width / 2.0),
        (length / 2.0, -width / 2.0),
        (length / 2.0, width / 2.0),
        (-length / 2.0, width / 2.0),
    )
    return [_translate_and_rotate(center, heading, point) for point in local_corners]


def _set_animation_running(animation: FuncAnimation, running: bool) -> None:
    """Start or stop a Matplotlib animation after checking its event source."""
    event_source = animation.event_source
    if event_source is None:
        raise RuntimeError("Matplotlib animation has no event source")
    if running:
        event_source.start()  # type: ignore[no-untyped-call]  # Matplotlib stub gap.
    else:
        event_source.stop()  # type: ignore[no-untyped-call]  # Matplotlib stub gap.


def _make_gauge(
    axis: Axes,
    *,
    y: float,
    label: str,
    visibility: str,
    value_range: DevelopmentVisualizationRange,
    color: str | None = None,
    label_above_bar: bool = False,
) -> tuple[Rectangle, Rectangle, Text]:
    """Create a gauge using display coordinates normalized to the diagnostic axis."""
    background = Rectangle(
        (0.30, y - 0.025),
        0.62,
        0.055,
        facecolor="0.88",
        edgecolor="0.45",
    )
    fill = Rectangle(
        (0.30, y - 0.025),
        0.0,
        0.055,
        facecolor=(
            color
            if color is not None
            else "tab:blue"
            if label == "ENERGY"
            else "tab:orange"
        ),
        edgecolor="none",
    )
    axis.add_patch(background)
    axis.add_patch(fill)
    if label_above_bar:
        axis.text(
            0.02,
            y + 0.085,
            f"{label} — {visibility}",
            va="bottom",
            fontsize=9,
            family="monospace",
        )
        axis.text(
            0.02,
            y - 0.015,
            f"{value_range.lower:g} → {value_range.upper:g}",
            va="top",
            fontsize=9,
            family="monospace",
        )
    else:
        axis.text(
            0.02,
            y + 0.015,
            f"{label} — {visibility}\n{value_range.lower:g} → {value_range.upper:g}",
            va="center",
            fontsize=9,
            family="monospace",
        )
    value = axis.text(
        0.94,
        y + 0.015,
        "",
        ha="right",
        va="center",
        fontsize=9,
        family="monospace",
    )
    return background, fill, value


def _gauge_fraction(value: float, value_range: DevelopmentVisualizationRange) -> float:
    return min(
        1.0,
        max(
            0.0,
            (value - value_range.lower) / (value_range.upper - value_range.lower),
        ),
    )


def _has_directional_beacon(data: DevelopmentVisualizationData) -> bool:
    """Return whether every neutral frame carries optional L/F/R values."""
    return bool(data.frames) and all(
        frame.beacon_left is not None
        and frame.beacon_forward is not None
        and frame.beacon_right is not None
        for frame in data.frames
    )


def _probe_endpoints(
    frame: DevelopmentVisualizationFrame, data: DevelopmentVisualizationData
) -> tuple[Coordinate, Coordinate, Coordinate]:
    """Return idealized directional probe endpoints for evaluator drawing."""
    if data.probe_distance is None or data.sensor_angle is None:
        raise ValueError("directional probe metadata is unavailable")
    angles = (
        frame.heading + data.sensor_angle,
        frame.heading,
        frame.heading - data.sensor_angle,
    )
    return tuple(
        (
            frame.x + data.probe_distance * math.cos(angle),
            frame.y + data.probe_distance * math.sin(angle),
        )
        for angle in angles
    )  # type: ignore[return-value]


def adapt_d003_trace(
    run: Mapping[str, object],
    *,
    source_label: str = "D-003 thermostatic shuttle",
) -> DevelopmentVisualizationData:
    """Adapt one completed D-003 evaluator result into the neutral model."""
    from .d002 import (
        D002_AMBIENT_THERMAL_STATE,
        D002_UPPER_THERMAL_FAILURE_BOUNDARY,
    )
    from .exp003 import EXP003StationConfig

    seed = _require_int(run, "seed")
    raw_trace = run.get("trace")
    if not isinstance(raw_trace, tuple) or not raw_trace:
        raise ValueError("D-003 result must contain a non-empty tuple trace")
    config = EXP003StationConfig(episode_horizon=len(raw_trace))
    station_center = _coordinate_from_sequence(
        run.get("station_center"), "station_center"
    )
    frames: list[DevelopmentVisualizationFrame] = []
    for entry in raw_trace:
        transition_index = _require_int_attribute(entry, "transition_index")
        position = getattr(entry, "position", None)
        x, y = _coordinate_from_sequence(position, "trace position")
        action = getattr(getattr(entry, "action", None), "name", None)
        decision_mode = getattr(getattr(entry, "controller_mode", None), "value", None)
        if not isinstance(action, str) or not isinstance(decision_mode, str):
            raise ValueError("D-003 trace action and controller mode must be labelled")
        frames.append(
            DevelopmentVisualizationFrame(
                transition_index=transition_index,
                x=x,
                y=y,
                heading=_require_float_attribute(entry, "heading"),
                action=action,
                decision_mode=decision_mode,
                energy=_require_float_attribute(entry, "energy"),
                thermal=_require_float_attribute(entry, "thermal"),
                charging_contact=_require_bool_attribute(entry, "charging_contact"),
                terminated=_require_bool_attribute(entry, "terminated"),
                truncated=_require_bool_attribute(entry, "truncated"),
            )
        )
    return DevelopmentVisualizationData(
        source_label=source_label,
        seed=seed,
        world_min=config.world_min,
        world_max=config.world_max,
        station_center=station_center,
        charging_radius=config.charging_radius,
        energy_range=DevelopmentVisualizationRange(
            config.energy.failure_boundary, config.energy.maximum_energy
        ),
        thermal_range=DevelopmentVisualizationRange(
            D002_AMBIENT_THERMAL_STATE, D002_UPPER_THERMAL_FAILURE_BOUNDARY
        ),
        frames=tuple(frames),
        visibility=DevelopmentVisualizationVisibility(
            position_heading="EVALUATOR ONLY",
            station_location="EVALUATOR ONLY",
            energy="EVALUATOR ONLY",
            thermal="CTRL + EVAL",
            charging_contact="CTRL + EVAL",
            action_decision_mode=(
                "ORGANISM-OWNED / CONTROLLER STATE SHOWN BY EVALUATOR"
            ),
        ),
    )


def build_d003_development_visualization(
    *,
    seed: int,
    horizon: int = 1000,
) -> DevelopmentVisualizationData:
    """Run one complete D-003 lifetime, then adapt its evaluator trace."""
    from .d003 import run_d003_probe

    result = run_d003_probe((seed,), horizon=horizon, collect_trace=True)
    runs = result.get("results")
    if not isinstance(runs, list) or len(runs) != 1 or not isinstance(runs[0], dict):
        raise ValueError("D-003 probe returned an unexpected result shape")
    return adapt_d003_trace(runs[0])


def adapt_d005_trace(
    run: Mapping[str, object],
    *,
    source_label: str = "D-005 predictive thermal-overshoot adaptation",
) -> DevelopmentVisualizationData:
    """Adapt one completed D-005 evaluator result into the neutral model."""
    from .d002 import (
        D002_AMBIENT_THERMAL_STATE,
        D002_UPPER_THERMAL_FAILURE_BOUNDARY,
    )
    from .exp003 import EXP003StationConfig

    seed = _require_int(run, "seed")
    raw_trace = run.get("trace")
    if not isinstance(raw_trace, tuple) or not raw_trace:
        raise ValueError("D-005 result must contain a non-empty tuple trace")
    config = EXP003StationConfig(episode_horizon=len(raw_trace))
    station_center = _coordinate_from_sequence(
        run.get("station_center"), "station_center"
    )
    frames: list[DevelopmentVisualizationFrame] = []
    for entry in raw_trace:
        transition_index = _require_int_attribute(entry, "transition_index")
        position = getattr(entry, "position", None)
        x, y = _coordinate_from_sequence(position, "trace position")
        action = getattr(getattr(entry, "action", None), "name", None)
        decision_mode = getattr(getattr(entry, "controller_mode", None), "value", None)
        if not isinstance(action, str) or not isinstance(decision_mode, str):
            raise ValueError("D-005 trace action and controller mode must be labelled")
        frames.append(
            DevelopmentVisualizationFrame(
                transition_index=transition_index,
                x=x,
                y=y,
                heading=_require_float_attribute(entry, "heading"),
                action=action,
                decision_mode=decision_mode,
                energy=_require_float_attribute(entry, "energy"),
                thermal=_require_float_attribute(entry, "thermal"),
                charging_contact=_require_bool_attribute(entry, "charging_contact"),
                terminated=_require_bool_attribute(entry, "terminated"),
                truncated=_require_bool_attribute(entry, "truncated"),
            )
        )
    return DevelopmentVisualizationData(
        source_label=source_label,
        seed=seed,
        world_min=config.world_min,
        world_max=config.world_max,
        station_center=station_center,
        charging_radius=config.charging_radius,
        energy_range=DevelopmentVisualizationRange(
            config.energy.failure_boundary, config.energy.maximum_energy
        ),
        thermal_range=DevelopmentVisualizationRange(
            D002_AMBIENT_THERMAL_STATE, D002_UPPER_THERMAL_FAILURE_BOUNDARY
        ),
        frames=tuple(frames),
        visibility=DevelopmentVisualizationVisibility(
            position_heading="EVALUATOR ONLY",
            station_location="EVALUATOR ONLY",
            energy="EVALUATOR ONLY",
            thermal="CTRL + EVAL",
            charging_contact="CTRL + EVAL",
            action_decision_mode=(
                "ORGANISM-OWNED / CONTROLLER STATE SHOWN BY EVALUATOR"
            ),
        ),
    )


def build_d005_development_visualization(
    *,
    seed: int,
    horizon: int = 1000,
) -> DevelopmentVisualizationData:
    """Run one complete D-005 lifetime, then adapt its evaluator trace."""
    from .d005 import run_d005_probe

    result = run_d005_probe((seed,), horizon=horizon, collect_trace=True)
    runs = result.get("results")
    if not isinstance(runs, list) or len(runs) != 1 or not isinstance(runs[0], dict):
        raise ValueError("D-005 probe returned an unexpected result shape")
    return adapt_d005_trace(runs[0])


def adapt_d006_trace(
    run: Mapping[str, object],
    *,
    source_label: str = "D-006 within-lifetime thermal adaptation",
) -> DevelopmentVisualizationData:
    """Adapt one completed D-006 predictive evaluator trace.

    Regime and prediction diagnostics remain in the trace/result record.  The
    shared renderer intentionally displays only the existing neutral fields.
    """
    from .d002 import (
        D002_AMBIENT_THERMAL_STATE,
        D002_UPPER_THERMAL_FAILURE_BOUNDARY,
    )
    from .exp003 import EXP003StationConfig

    seed = _require_int(run, "seed")
    raw_trace = run.get("trace")
    if not isinstance(raw_trace, tuple) or not raw_trace:
        raise ValueError("D-006 result must contain a non-empty tuple trace")
    config = EXP003StationConfig(episode_horizon=len(raw_trace))
    station_center = _coordinate_from_sequence(
        run.get("station_center"), "station_center"
    )
    frames: list[DevelopmentVisualizationFrame] = []
    for entry in raw_trace:
        transition_index = _require_int_attribute(entry, "transition_index")
        position = getattr(entry, "position", None)
        x, y = _coordinate_from_sequence(position, "trace position")
        action = getattr(getattr(entry, "action", None), "name", None)
        decision_mode = getattr(getattr(entry, "controller_mode", None), "value", None)
        if not isinstance(action, str) or not isinstance(decision_mode, str):
            raise ValueError("D-006 trace action and controller mode must be labelled")
        frames.append(
            DevelopmentVisualizationFrame(
                transition_index=transition_index,
                x=x,
                y=y,
                heading=_require_float_attribute(entry, "heading"),
                action=action,
                decision_mode=decision_mode,
                energy=_require_float_attribute(entry, "energy"),
                thermal=_require_float_attribute(entry, "thermal"),
                charging_contact=_require_bool_attribute(entry, "charging_contact"),
                terminated=_require_bool_attribute(entry, "terminated"),
                truncated=_require_bool_attribute(entry, "truncated"),
            )
        )
    return DevelopmentVisualizationData(
        source_label=source_label,
        seed=seed,
        world_min=config.world_min,
        world_max=config.world_max,
        station_center=station_center,
        charging_radius=config.charging_radius,
        energy_range=DevelopmentVisualizationRange(
            config.energy.failure_boundary, config.energy.maximum_energy
        ),
        thermal_range=DevelopmentVisualizationRange(
            D002_AMBIENT_THERMAL_STATE, D002_UPPER_THERMAL_FAILURE_BOUNDARY
        ),
        frames=tuple(frames),
        visibility=DevelopmentVisualizationVisibility(
            position_heading="EVALUATOR ONLY",
            station_location="EVALUATOR ONLY",
            energy="EVALUATOR ONLY",
            thermal="CTRL + EVAL",
            charging_contact="CTRL + EVAL",
            action_decision_mode=(
                "ORGANISM-OWNED / CONTROLLER STATE SHOWN BY EVALUATOR"
            ),
        ),
    )


def build_d006_development_visualization(
    *,
    seed: int,
    horizon: int = 1000,
) -> DevelopmentVisualizationData:
    """Run one D-006 lifetime, then adapt its completed predictive trace."""
    from .d006 import run_d006_probe

    result = run_d006_probe((seed,), horizon=horizon, collect_trace=True)
    runs = result.get("results")
    if not isinstance(runs, list) or len(runs) != 1 or not isinstance(runs[0], dict):
        raise ValueError("D-006 probe returned an unexpected result shape")
    predictive = runs[0].get("predictive")
    if not isinstance(predictive, dict):
        raise ValueError("D-006 predictive result was not a mapping")
    return adapt_d006_trace(predictive)


def _validate_d011_visualization_seed(seed: int) -> None:
    from . import d011

    d011._validate_d011_development_seeds((seed,))


def _validate_d012_visualization_seed(seed: int) -> None:
    """Validate one D-012 visualization seed without invoking its census guard."""
    from .d012 import D012_DEFAULT_DEVELOPMENT_SEEDS
    from .exp003_seed_policy import validate_exp003_development_seeds

    validate_exp003_development_seeds((seed,))
    if seed not in D012_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-012 visualization requires a seed from its declared development "
            f"range {D012_DEFAULT_DEVELOPMENT_SEEDS[0]}–"
            f"{D012_DEFAULT_DEVELOPMENT_SEEDS[-1]}; got {seed}"
        )


def _validate_d013_visualization_seed(seed: int) -> None:
    """Validate one D-013 visualization seed against both seed guards."""
    from .d013 import D013_DEFAULT_DEVELOPMENT_SEEDS
    from .exp003_seed_policy import validate_exp003_development_seeds

    validate_exp003_development_seeds((seed,))
    if seed not in D013_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-013 visualization requires one of its declared development "
            f"seeds {D013_DEFAULT_DEVELOPMENT_SEEDS}; got {seed}"
        )


def _validate_d014_visualization_seed(seed: int) -> None:
    """Validate one D-014 visualization seed against both seed guards."""
    from .d014 import _validate_d014_development_seeds

    _validate_d014_development_seeds((seed,))


def _validate_d015_visualization_seed(seed: int) -> None:
    """Validate one D-015 visualization seed against both seed guards."""
    from .d015 import _validate_d015_development_seeds

    _validate_d015_development_seeds((seed,))


def _build_d011_family_development_visualization(
    *,
    seed: int,
    horizon: int,
    source_label: str,
    validate_seed: Callable[[int], None],
    controller_factory: Callable[
        [np.random.Generator], d011.D011Controller
    ] = d011.D011Controller,
    with_shadow_learner: bool = False,
    with_d017_shadow: bool = False,
) -> DevelopmentVisualizationData:
    """Replay a D-011-compatible lifetime through one shared controller path."""
    from . import d011, d013
    from .d002 import (
        D002_AMBIENT_THERMAL_STATE,
        D002_UPPER_THERMAL_FAILURE_BOUNDARY,
        D002ThermalStationEnv,
    )
    from .d003 import HOT_DEPART_THRESHOLD
    from .exp003 import EXP003StationConfig

    validate_seed(seed)
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon <= 0:
        raise ValueError("horizon must be a positive integer")

    config = EXP003StationConfig(episode_horizon=horizon)
    environment = D002ThermalStationEnv(config=config)
    observation, info = environment.reset(seed=seed)
    if info != {}:
        raise RuntimeError("D-002 reset crossed the information boundary")
    _, observation = d011._prepare_post_contact_setup(environment)
    random_streams = environment.base_env.random_streams
    if random_streams is None:
        raise RuntimeError("D-002 policy RNG is unavailable after reset")
    controller = controller_factory(random_streams.policy)
    controller.reset()
    predictor = (
        d013.D013ActionConsequencePredictor() if with_shadow_learner else None
    )
    if environment.body is None or environment.station_center is None:
        raise RuntimeError("D-011 evaluator geometry is unavailable after setup")
    shadow_geometry: DevelopmentShadowGeometry | None = None
    if with_d017_shadow:
        from . import d017

        dock_plus, dock_minus = d017.shadow_dock_contacts_world(
            environment.station_center, 0.0
        )
        shadow_geometry = DevelopmentShadowGeometry(
            body_length=d017.D017_BODY_LENGTH,
            body_width=d017.D017_BODY_WIDTH,
            rear_contact_plus=(
                d017.D017_REAR_X,
                d017.D017_CONTACT_LATERAL_OFFSET,
            ),
            rear_contact_minus=(
                d017.D017_REAR_X,
                -d017.D017_CONTACT_LATERAL_OFFSET,
            ),
            front_midpoint=(d017.D017_FRONT_X, 0.0),
            dock_orientation=0.0,
            dock_contact_plus=dock_plus,
            dock_contact_minus=dock_minus,
        )

    frames: list[DevelopmentVisualizationFrame] = []
    consequence_predictions: list[DevelopmentConsequencePredictionFrame] = []
    terminated = False
    truncated = False
    while not (terminated or truncated):
        visible = d011._controller_observation(observation)
        mode_before = controller.mode
        action = controller.act(visible)
        prediction = (
            predictor.predict(visible, action) if predictor is not None else None
        )
        observation, reward, terminated, truncated, info = environment.step(action)
        if reward != 0.0 or info != {}:
            raise RuntimeError("D-011 replay crossed the reward/info boundary")
        next_visible = d011._controller_observation(observation)
        update = (
            predictor.observe_transition(visible, action, next_visible)
            if predictor is not None
            else None
        )
        telemetry = environment.last_transition
        body = environment.body
        if telemetry is None or body is None:
            raise RuntimeError("D-011 transition telemetry is unavailable")
        if predictor is not None and prediction is not None and update is not None:
            consequence_predictions.append(
                DevelopmentConsequencePredictionFrame(
                    transition_index=telemetry.step_index,
                    predicted_delta_energy=prediction.predicted_delta_energy,
                    observed_delta_energy=update.observed_delta_energy,
                    predicted_delta_thermal=prediction.predicted_delta_thermal,
                    observed_delta_thermal=update.observed_delta_thermal,
                    predicted_delta_charging_contact=(
                        prediction.predicted_delta_charging_contact
                    ),
                    observed_delta_charging_contact=(
                        update.observed_delta_charging_contact
                    ),
                )
            )
        frames.append(
            DevelopmentVisualizationFrame(
                transition_index=telemetry.step_index,
                x=body.x,
                y=body.y,
                heading=body.heading,
                action=action.name,
                decision_mode=mode_before.value,
                energy=next_visible.energy,
                thermal=next_visible.thermal,
                charging_contact=next_visible.charging_contact,
                terminated=terminated,
                truncated=truncated,
                beacon_left=next_visible.beacon.left,
                beacon_forward=next_visible.beacon.forward,
                beacon_right=next_visible.beacon.right,
            )
        )

    return DevelopmentVisualizationData(
        source_label=source_label,
        seed=seed,
        world_min=config.world_min,
        world_max=config.world_max,
        station_center=environment.station_center,
        charging_radius=config.charging_radius,
        energy_range=DevelopmentVisualizationRange(
            0.0, 1.0
        ),
        thermal_range=DevelopmentVisualizationRange(
            D002_AMBIENT_THERMAL_STATE,
            D002_UPPER_THERMAL_FAILURE_BOUNDARY,
        ),
        frames=tuple(frames),
        visibility=DevelopmentVisualizationVisibility(
            position_heading="EVALUATOR ONLY",
            station_location="EVALUATOR ONLY",
            energy="CTRL + EVAL",
            thermal="CTRL + EVAL",
            charging_contact="CTRL + EVAL",
            action_decision_mode=(
                "ORGANISM-OWNED / CONTROLLER STATE SHOWN BY EVALUATOR"
            ),
        ),
        probe_distance=config.probe_distance,
        sensor_angle=config.sensor_angle,
        thermal_threshold=HOT_DEPART_THRESHOLD,
        thermal_threshold_label="HOT DEPART = 0.60",
        energy_label="ENERGY (NORMALIZED)",
        consequence_predictions=(
            tuple(consequence_predictions) if predictor is not None else None
        ),
        shadow_geometry=shadow_geometry,
    )


def build_d011_development_visualization(
    *,
    seed: int,
    horizon: int = 1000,
) -> DevelopmentVisualizationData:
    """Replay one legal D-011 lifetime into the neutral visualization model."""
    return _build_d011_family_development_visualization(
        seed=seed,
        horizon=horizon,
        source_label="D-011 fixed thermal-beacon reacquisition",
        validate_seed=_validate_d011_visualization_seed,
        controller_factory=d011.D011Controller,
    )


def build_d012_development_visualization(
    *,
    seed: int,
    horizon: int = 1000,
) -> DevelopmentVisualizationData:
    """Replay one legal D-012 seed using the unchanged D-011 controller path."""
    return _build_d011_family_development_visualization(
        seed=seed,
        horizon=horizon,
        source_label="D-012 D-011 thermal-beacon reacquisition",
        validate_seed=_validate_d012_visualization_seed,
        controller_factory=d011.D011Controller,
    )


def build_d013_reference_development_visualization(
    *,
    seed: int,
    horizon: int = 1000,
) -> DevelopmentVisualizationData:
    """Replay D-011 unchanged as an evaluator-side D-013 reference."""
    return _build_d011_family_development_visualization(
        seed=seed,
        horizon=horizon,
        source_label=(
            "D-013 reference — unchanged D-011 controller, no shadow learner"
        ),
        validate_seed=_validate_d013_visualization_seed,
        controller_factory=d011.D011Controller,
    )


def build_d013_development_visualization(
    *,
    seed: int,
    horizon: int = 1000,
) -> DevelopmentVisualizationData:
    """Replay D-011 with D-013's evaluator-only causal shadow learner."""
    return _build_d011_family_development_visualization(
        seed=seed,
        horizon=horizon,
        source_label="D-013 shadow learner — evaluator-only consequences",
        validate_seed=_validate_d013_visualization_seed,
        controller_factory=d011.D011Controller,
        with_shadow_learner=True,
    )


def build_d014_development_visualization(
    *,
    seed: int,
    horizon: int = 1000,
) -> DevelopmentVisualizationData:
    """Replay one legal D-014 lifetime with the corrected controller."""
    from . import d014

    return _build_d011_family_development_visualization(
        seed=seed,
        horizon=horizon,
        source_label="D-014 full-charge-or-thermal departure scaffold",
        validate_seed=_validate_d014_visualization_seed,
        controller_factory=d014.D014Controller,
    )


def build_d015_reference_development_visualization(
    *,
    seed: int,
    horizon: int = 1000,
) -> DevelopmentVisualizationData:
    """Replay the corrected D-014 controller without a shadow learner."""
    from . import d014

    return _build_d011_family_development_visualization(
        seed=seed,
        horizon=horizon,
        source_label=(
            "D-015 reference — D-014Controller, no shadow learner"
        ),
        validate_seed=_validate_d015_visualization_seed,
        controller_factory=d014.D014Controller,
    )


def build_d015_development_visualization(
    *,
    seed: int,
    horizon: int = 1000,
) -> DevelopmentVisualizationData:
    """Replay D-014 with D-013's evaluator-only causal shadow learner."""
    from . import d014

    return _build_d011_family_development_visualization(
        seed=seed,
        horizon=horizon,
        source_label=(
            "D-015 shadow learner — SHADOW ONLY — ZERO BEHAVIOURAL INFLUENCE"
        ),
        validate_seed=_validate_d015_visualization_seed,
        controller_factory=d014.D014Controller,
        with_shadow_learner=True,
    )


def _validate_d017_visualization_seed(seed: int) -> None:
    """Validate one D-017 visualization seed against both seed guards."""
    from .d017 import _validate_d017_development_seeds

    _validate_d017_development_seeds((seed,))


def build_d017_development_visualization(
    *,
    seed: int,
    horizon: int = 1000,
) -> DevelopmentVisualizationData:
    """Replay D-014 with the optional evaluator-only D-017 shadow overlay."""
    from . import d014

    return _build_d011_family_development_visualization(
        seed=seed,
        horizon=horizon,
        source_label=(
            "D-017 rear-docking pose audit — "
            "EVALUATOR-ONLY SHADOW MORPHOLOGY"
        ),
        validate_seed=_validate_d017_visualization_seed,
        controller_factory=d014.D014Controller,
        with_d017_shadow=True,
    )


def _validate_d018_visualization_seed(seed: int) -> None:
    """Validate one D-018 visualization seed against both seed guards."""
    from .d018 import _validate_d018_development_seeds

    _validate_d018_development_seeds((seed,))


def _d018_mapping_value(
    mapping: Mapping[str, object], name: str
) -> object:
    if name not in mapping:
        raise ValueError(f"D-018 visualization field {name!r} is missing")
    return mapping[name]


def _d018_string(mapping: Mapping[str, object], name: str) -> str:
    value = _d018_mapping_value(mapping, name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"D-018 visualization field {name!r} must be non-empty text")
    return value


def _d018_float(mapping: Mapping[str, object], name: str) -> float:
    value = _d018_mapping_value(mapping, name)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"D-018 visualization field {name!r} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"D-018 visualization field {name!r} must be finite")
    return number


def _d018_int(mapping: Mapping[str, object], name: str) -> int:
    value = _d018_mapping_value(mapping, name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"D-018 visualization field {name!r} must be an integer")
    return value


def _d018_bool(mapping: Mapping[str, object], name: str) -> bool:
    value = _d018_mapping_value(mapping, name)
    if not isinstance(value, bool):
        raise ValueError(f"D-018 visualization field {name!r} must be a bool")
    return value


def build_d018_development_visualization(
    *,
    seed: int,
    horizon: int = 1000,
) -> DevelopmentVisualizationData:
    """Replay D-018 into a display-only real trace and alternative panel."""
    from . import d018
    from .d002 import (
        D002_AMBIENT_THERMAL_STATE,
        D002_UPPER_THERMAL_FAILURE_BOUNDARY,
    )
    from .d003 import HOT_DEPART_THRESHOLD
    from .env import Action
    from .exp003 import EXP003StationConfig

    _validate_d018_visualization_seed(seed)
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon <= 0:
        raise ValueError("horizon must be a positive integer")

    # This is the accepted D-018 runner's completed evaluator trace.  It is
    # deliberately built before any Matplotlib object is created.
    outcome = d018._run_seed(seed, horizon=horizon, counterfactual_audit=True)
    trace = outcome.trace
    if not trace:
        raise RuntimeError("D-018 visualization replay produced no real transitions")

    frames: list[DevelopmentVisualizationFrame] = []
    for record in trace:
        next_state_object = _d018_mapping_value(record, "next_visible_state")
        if not isinstance(next_state_object, dict):
            raise RuntimeError("D-018 next visible state is not an object")
        next_state = next_state_object
        position = _coordinate_from_sequence(
            _d018_mapping_value(record, "position_after"), "D-018 position_after"
        )
        frames.append(
            DevelopmentVisualizationFrame(
                transition_index=_d018_int(record, "transition_index"),
                x=position[0],
                y=position[1],
                heading=_d018_float(record, "heading_after"),
                action=_d018_string(record, "action"),
                decision_mode=_d018_string(record, "mode_before"),
                energy=_d018_float(next_state, "normalized_energy"),
                thermal=_d018_float(next_state, "normalized_thermal"),
                charging_contact=_d018_bool(next_state, "charging_contact"),
                terminated=_d018_bool(record, "terminated"),
                truncated=_d018_bool(record, "truncated"),
                beacon_left=_d018_float(next_state, "beacon_left"),
                beacon_forward=_d018_float(next_state, "beacon_forward"),
                beacon_right=_d018_float(next_state, "beacon_right"),
            )
        )

    audit_object = outcome.summary.get("audit")
    if not isinstance(audit_object, dict):
        raise RuntimeError("D-018 visualization audit rows are unavailable")
    rows_object = audit_object.get("rows")
    if not isinstance(rows_object, list):
        raise RuntimeError("D-018 visualization candidate rows are unavailable")
    rows_by_transition: dict[int, list[dict[str, object]]] = {}
    for row_object in rows_object:
        if not isinstance(row_object, dict):
            raise RuntimeError("D-018 candidate row is not an object")
        row = row_object
        transition_index = _d018_int(row, "transition_index")
        rows_by_transition.setdefault(transition_index, []).append(row)

    action_order = tuple(action.name for action in Action)
    alternatives: list[tuple[DevelopmentActionAlternative, ...]] = []
    for frame in frames:
        transition_rows = rows_by_transition.get(frame.transition_index, [])
        if len(transition_rows) != len(action_order):
            raise RuntimeError(
                "D-018 visualization requires one row for each candidate action"
            )
        try:
            ordered_rows = sorted(
                transition_rows,
                key=lambda row: action_order.index(
                    _d018_string(row, "candidate_action")
                ),
            )
        except ValueError as error:
            raise RuntimeError(
                "D-018 row contains an unknown candidate action"
            ) from error
        alternatives.append(
            tuple(
                DevelopmentActionAlternative(
                    transition_index=_d018_int(row, "transition_index"),
                    action=_d018_string(row, "candidate_action"),
                    physically_executed=(
                        _d018_string(row, "candidate_action") == frame.action
                    ),
                    prior_exact_support_count=_d018_int(
                        row, "prior_exact_state_action_support_count"
                    ),
                    predicted_delta_energy=_d018_float(
                        row, "predicted_delta_energy"
                    ),
                    actual_delta_energy=_d018_float(row, "actual_delta_energy"),
                    predicted_delta_thermal=_d018_float(
                        row, "predicted_delta_thermal"
                    ),
                    actual_delta_thermal=_d018_float(row, "actual_delta_thermal"),
                    predicted_delta_charging_contact=_d018_float(
                        row, "predicted_delta_charging_contact"
                    ),
                    actual_delta_charging_contact=_d018_float(
                        row, "actual_delta_charging_contact"
                    ),
                )
                for row in ordered_rows
            )
        )

    config = EXP003StationConfig(episode_horizon=horizon)
    evaluator_object = outcome.summary.get("evaluator_only")
    if not isinstance(evaluator_object, dict):
        raise RuntimeError("D-018 evaluator metadata is unavailable")
    station = _coordinate_from_sequence(
        _d018_mapping_value(evaluator_object, "station_position"),
        "D-018 station_position",
    )
    return DevelopmentVisualizationData(
        source_label=(
            "D-018 evaluator-only action alternatives — real D-014 trajectory"
        ),
        seed=seed,
        world_min=config.world_min,
        world_max=config.world_max,
        station_center=station,
        charging_radius=config.charging_radius,
        energy_range=DevelopmentVisualizationRange(0.0, 1.0),
        thermal_range=DevelopmentVisualizationRange(
            D002_AMBIENT_THERMAL_STATE,
            D002_UPPER_THERMAL_FAILURE_BOUNDARY,
        ),
        frames=tuple(frames),
        visibility=DevelopmentVisualizationVisibility(
            position_heading="EVALUATOR ONLY",
            station_location="EVALUATOR ONLY",
            energy="CTRL + EVAL",
            thermal="CTRL + EVAL",
            charging_contact="CTRL + EVAL",
            action_decision_mode=(
                "ORGANISM-OWNED / CONTROLLER STATE SHOWN BY EVALUATOR"
            ),
        ),
        probe_distance=config.probe_distance,
        sensor_angle=config.sensor_angle,
        thermal_threshold=HOT_DEPART_THRESHOLD,
        thermal_threshold_label="HOT DEPART = 0.60",
        energy_label="ENERGY (NORMALIZED)",
        action_alternatives=tuple(alternatives),
        action_alternative_warning=(
            "EVALUATOR-ONLY ACTION ALTERNATIVES\n"
            "D-014 CHOSE THE REAL ACTION BEFORE SCORING\n"
            "GHOST OUTCOMES DO NOT AFFECT BEHAVIOUR OR LEARNING"
        ),
        action_alternative_provenance=(
            "D-013 PRE-UPDATE PREDICTION  vs  D-018 ISOLATED BRANCH ACTUAL\n"
            "E/T/C = Δenergy / Δthermal / Δcharging contact"
        ),
    )


def build_d020_development_visualization() -> DevelopmentVisualizationData:
    """Replay the frozen, seedless D-020 mixed-action probe post-hoc."""
    from .d020 import (
        D020_MIXED_ACTIONS,
        D020Env,
        D020PhysicalConfig,
        D020TransitionTelemetry,
    )

    config = D020PhysicalConfig()
    environment = D020Env(config)
    reset_observation, reset_info = environment.reset(
        options={
            "body_position": (0.26, 0.5),
            "station_center": (0.5, 0.5),
            "heading": 0.0,
            "battery_j": 2664.0,
            "body_temperature_c": 23.0,
        }
    )
    if reset_info != {} or reset_observation.shape != (6,):
        raise RuntimeError("D-020 reset crossed the ordinary observation boundary")

    completed_trace: list[tuple[np.ndarray, D020TransitionTelemetry]] = []
    for transition_number, action in enumerate(D020_MIXED_ACTIONS, start=1):
        observation, reward, terminated, truncated, info = environment.step(action)
        if reward != 0.0 or info != {}:
            raise RuntimeError("D-020 replay crossed the reward/info boundary")
        if observation.shape != (6,):
            raise RuntimeError("D-020 observation must contain exactly six channels")
        telemetry = environment.last_transition
        if telemetry is None:
            raise RuntimeError("D-020 replay did not expose transition telemetry")
        if telemetry.step_index != transition_number:
            raise RuntimeError("D-020 transition indices are not sequential")
        if telemetry.terminated != terminated or telemetry.truncated != truncated:
            raise RuntimeError("D-020 telemetry flags disagree with returned flags")
        if (terminated or truncated) and transition_number != len(D020_MIXED_ACTIONS):
            raise RuntimeError("D-020 mixed probe ended before all actions ran")
        completed_trace.append((observation, telemetry))

    if len(completed_trace) != len(D020_MIXED_ACTIONS):
        raise RuntimeError("D-020 mixed replay did not complete all transitions")
    if environment.station_center is None:
        raise RuntimeError("D-020 station geometry is unavailable")

    # The neutral trace is built only after the complete evaluator replay has
    # finished.  No renderer or GUI state participates in this accounting.
    frames = tuple(
        DevelopmentVisualizationFrame(
            transition_index=telemetry.step_index,
            x=telemetry.position_after[0],
            y=telemetry.position_after[1],
            heading=telemetry.heading,
            action=telemetry.action.name,
            decision_mode=f"EVALUATOR CHARGER: {telemetry.charge_phase.value}",
            energy=float(observation[0]),
            thermal=telemetry.body_temperature_after_c,
            charging_contact=telemetry.charging_contact_after,
            terminated=telemetry.terminated,
            truncated=telemetry.truncated,
            beacon_left=float(observation[1]),
            beacon_forward=float(observation[2]),
            beacon_right=float(observation[3]),
        )
        for observation, telemetry in completed_trace
    )
    return DevelopmentVisualizationData(
        source_label=(
            "D-020 V0.4 physical bookkeeping — mixed-action causal replay"
        ),
        seed=None,
        world_min=config.world_min,
        world_max=config.world_max,
        station_center=environment.station_center,
        charging_radius=config.charging_radius,
        energy_range=DevelopmentVisualizationRange(0.0, 1.0),
        thermal_range=DevelopmentVisualizationRange(0.0, 80.0),
        frames=frames,
        visibility=DevelopmentVisualizationVisibility(
            position_heading="EVALUATOR ONLY",
            station_location="EVALUATOR ONLY",
            energy="ORGANISM-VISIBLE + EVALUATOR",
            thermal=(
                "EVALUATOR °C; ORGANISM SEES NORMALIZED OWN TEMPERATURE"
            ),
            charging_contact="ORGANISM-VISIBLE + EVALUATOR",
            action_decision_mode="EVALUATOR ONLY — NO CONTROLLER",
        ),
        probe_distance=config.probe_distance,
        sensor_angle=config.sensor_angle,
        thermal_threshold=45.0,
        thermal_threshold_label="PREFERRED 45°C — EVALUATOR ONLY",
        energy_label="BATTERY (NORMALIZED)",
        mode_display_label="charger phase",
    )


def d021_replay_event_steps(
    trace: Sequence[D021TransitionTrace],
) -> dict[str, int]:
    """Return the frozen event steps used by the D-021 replay selector."""
    from .d020 import D020PhysicalConfig

    if not trace:
        raise ValueError("D-021 replay trace must not be empty")
    battery_capacity_j = D020PhysicalConfig().battery_capacity_j

    departures = [
        record.transition_index
        for record in trace
        if record.mode_before is D021Mode.CHARGE
        and record.mode_after is D021Mode.DEPART
    ]
    charger_exits = [
        record.transition_index
        for record in trace
        if record.telemetry.charging_contact_before
        and not record.telemetry.charging_contact_after
    ]
    seek_entries = [
        record.transition_index
        for record in trace
        if record.mode_before is D021Mode.AWAY
        and record.mode_after is D021Mode.SEEK
    ]
    reacquisitions = [
        record.transition_index
        for record in trace
        if record.mode_before is D021Mode.SEEK
        and not record.telemetry.charging_contact_before
        and record.telemetry.charging_contact_after
    ]
    charge_entries = [
        record.transition_index
        for record in trace
        if record.mode_before is D021Mode.SEEK
        and record.mode_after is D021Mode.CHARGE
    ]
    full_recharges = [
        record.transition_index
        for record in trace
        if record.telemetry.charger_termination_latched_after
        and record.telemetry.battery_after_j >= battery_capacity_j
    ]
    if len(departures) < 2:
        raise RuntimeError("D-021 replay did not contain two full departures")
    required = {
        "first_departure": departures[0],
        "first_charger_exit": _first_or_raise(charger_exits, "charger exit"),
        "first_seek_entry": _first_or_raise(seek_entries, "SEEK entry"),
        "first_reacquisition": _first_or_raise(reacquisitions, "reacquisition"),
        "first_charge_entry": _first_or_raise(charge_entries, "CHARGE entry"),
        "first_full_recharge": _first_or_raise(full_recharges, "full recharge"),
        "first_redeparture": departures[1],
        "final": trace[-1].transition_index,
    }
    incidental_contacts = [
        record.transition_index
        for record in trace
        if record.mode_before is D021Mode.AWAY
        and not record.telemetry.charging_contact_before
        and record.telemetry.charging_contact_after
    ]
    if incidental_contacts:
        required["representative_away_contact"] = incidental_contacts[0]
    return required


def _first_or_raise(values: Sequence[int], label: str) -> int:
    if not values:
        raise RuntimeError(f"D-021 replay did not contain a {label}")
    return values[0]


def select_d021_replay_indices(
    trace: Sequence[D021TransitionTrace],
) -> tuple[int, ...]:
    """Select actual D-021 steps with deterministic event-preserving sampling."""
    if not trace:
        raise ValueError("D-021 replay trace must not be empty")
    event_steps = d021_replay_event_steps(trace)
    trace_by_step = {record.transition_index: record for record in trace}
    selected = set(event_steps.values())
    for step in event_steps.values():
        selected.update(
            candidate
            for candidate in range(step - 2, step + 3)
            if candidate in trace_by_step
        )

    run_start = 0
    while run_start < len(trace):
        run_end = run_start
        mode = trace[run_start].mode_before
        while (
            run_end + 1 < len(trace)
            and trace[run_end + 1].mode_before is mode
        ):
            run_end += 1
        selected.add(trace[(run_start + run_end) // 2].transition_index)
        run_start = run_end + 1

    stride = (len(trace) + 699) // 700
    selected.update(record.transition_index for record in trace[::stride])
    selected.add(trace[-1].transition_index)
    return tuple(sorted(selected))


def adapt_d021_trace(
    trace: Sequence[D021TransitionTrace],
    *,
    source_label: str = "D-021 V0.4 autonomous energy-regulation lifetime",
    seed: int = 18365,
) -> DevelopmentVisualizationData:
    """Convert one completed D-021 evaluator trace to neutral replay data."""
    from .d020 import D020PhysicalConfig

    if not trace:
        raise ValueError("D-021 replay trace must not be empty")
    config = D020PhysicalConfig()
    selected_steps = select_d021_replay_indices(trace)
    by_step = {record.transition_index: record for record in trace}
    frames: list[DevelopmentVisualizationFrame] = []
    initial = trace[0]
    initial_observation = initial.observation_before
    if len(initial_observation) != 6:
        raise RuntimeError("D-021 initial observation must contain six channels")
    frames.append(
        DevelopmentVisualizationFrame(
            transition_index=0,
            x=initial.telemetry.position_before[0],
            y=initial.telemetry.position_before[1],
            heading=initial.telemetry.heading,
            action="INITIAL",
            decision_mode=initial.mode_before.value,
            energy=initial_observation[0],
            thermal=initial.telemetry.body_temperature_before_c,
            charging_contact=bool(initial_observation[4]),
            terminated=False,
            truncated=False,
            beacon_left=initial_observation[1],
            beacon_forward=initial_observation[2],
            beacon_right=initial_observation[3],
            thermal_normalized=initial_observation[5],
            thermal_absolute_c=initial.telemetry.body_temperature_before_c,
            charger_phase=initial.telemetry.charge_phase.value,
            simulated_seconds=0.0,
            charging_contact_before=initial.telemetry.charging_contact_before,
        )
    )
    for step in selected_steps:
        record = by_step[step]
        if len(record.observation) != 6:
            raise RuntimeError("D-021 observation must contain exactly six channels")
        if record.reward != 0.0 or record.info != {}:
            raise RuntimeError("D-021 replay crossed the reward/info boundary")
        observation = record.observation
        telemetry = record.telemetry
        frames.append(
            DevelopmentVisualizationFrame(
                transition_index=record.transition_index,
                x=telemetry.position_after[0],
                y=telemetry.position_after[1],
                heading=telemetry.heading,
                action=record.action.name,
                decision_mode=record.mode_before.value,
                energy=observation[0],
                thermal=telemetry.body_temperature_after_c,
                charging_contact=bool(observation[4]),
                terminated=telemetry.terminated,
                truncated=telemetry.truncated,
                beacon_left=observation[1],
                beacon_forward=observation[2],
                beacon_right=observation[3],
                thermal_normalized=observation[5],
                thermal_absolute_c=telemetry.body_temperature_after_c,
                charger_phase=telemetry.charge_phase.value,
                simulated_seconds=record.transition_index * config.dt_seconds,
                charging_contact_before=telemetry.charging_contact_before,
            )
        )
    return DevelopmentVisualizationData(
        source_label=source_label,
        seed=seed,
        world_min=config.world_min,
        world_max=config.world_max,
        station_center=trace[0].telemetry.station_center,
        charging_radius=config.charging_radius,
        energy_range=DevelopmentVisualizationRange(0.0, 1.0),
        thermal_range=DevelopmentVisualizationRange(0.0, 80.0),
        frames=tuple(frames),
        visibility=DevelopmentVisualizationVisibility(
            position_heading="EVALUATOR ONLY",
            station_location="EVALUATOR ONLY",
            energy="ORGANISM-VISIBLE NORMALIZED + EVALUATOR",
            thermal=(
                "ORGANISM-VISIBLE NORMALIZED OWN TEMPERATURE + "
                "EVALUATOR ABSOLUTE °C"
            ),
            charging_contact="ORGANISM-VISIBLE + EVALUATOR",
            action_decision_mode=(
                "CONTROLLER MODE SHOWN; CHARGER PHASE EVALUATOR ONLY"
            ),
        ),
        probe_distance=config.probe_distance,
        sensor_angle=config.sensor_angle,
        thermal_threshold=config.preferred_operating_ceiling_c,
        thermal_threshold_label="PREFERRED 45°C — EVALUATOR ONLY",
        energy_label="BATTERY (NORMALIZED)",
        mode_display_label="controller mode",
    )


def build_d021_development_visualization(
    *,
    seed: int = 18365,
    horizon: int = 70_000,
) -> DevelopmentVisualizationData:
    """Run the fixed canonical D-021 lifetime before building neutral data."""
    from .d021 import run_d021_lifetime_trace

    if seed != 18365:
        raise ValueError("D-021 visualization is fixed to canonical seed 18365")
    trace = run_d021_lifetime_trace(seed, horizon=horizon)
    return adapt_d021_trace(trace, seed=seed)


def _validate_d023_visualization_seed(seed: int) -> None:
    """Validate one D-023 seed without requiring the full three-seed probe."""
    from .d023 import D023_DEFAULT_DEVELOPMENT_SEEDS
    from .exp003_seed_policy import validate_exp003_development_seeds

    validate_exp003_development_seeds((seed,))
    if seed not in D023_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-023 visualization requires a seed from its exact declared "
            f"development set {D023_DEFAULT_DEVELOPMENT_SEEDS}; got {seed}"
        )


def adapt_d023_trace(
    trace: Sequence[D021TransitionTrace],
    *,
    seed: int,
    source_label: str = "D-023 V0.4 repeated-cycle energy-regulation lifetime",
) -> DevelopmentVisualizationData:
    """Adapt one completed D-023 trace using the shared D-021 replay model."""
    _validate_d023_visualization_seed(seed)
    return adapt_d021_trace(trace, source_label=source_label, seed=seed)


def build_d023_development_visualization(
    *,
    seed: int = 18365,
    horizon: int = 210_000,
) -> DevelopmentVisualizationData:
    """Run one complete D-023 lifetime, then adapt its evaluator trace."""
    from . import d021, d023

    _validate_d023_visualization_seed(seed)
    if horizon != d023.D023_HORIZON:
        raise ValueError(
            "D-023 visualization requires the frozen 210,000-transition horizon"
        )
    trace: list[D021TransitionTrace] = []
    d021._run_seed(seed, horizon=d023.D023_HORIZON, trace=trace)
    if len(trace) != d023.D023_HORIZON:
        raise RuntimeError("D-023 lifetime trace did not reach the frozen horizon")
    return adapt_d023_trace(tuple(trace), seed=seed)


def _validate_d024_visualization_seed(seed: int) -> None:
    """Validate one D-024 visualization seed against its frozen set."""
    from .d024 import _validate_d024_seed

    _validate_d024_seed(seed)


def d024_replay_event_steps(
    trace: Sequence[D021TransitionTrace],
) -> dict[str, int]:
    """Return available causal D-024 events for display-only replay sampling."""
    from . import d024
    from .d020 import D020PhysicalConfig

    if not trace:
        raise ValueError("D-024 replay trace must not be empty")
    config = D020PhysicalConfig()
    events: dict[str, int] = {"final": trace[-1].transition_index}
    candidates: dict[str, list[int]] = {
        "first_departure": [
            record.transition_index
            for record in trace
            if record.mode_before is D021Mode.CHARGE
            and record.mode_after is D021Mode.DEPART
        ],
        "first_charger_exit": [
            record.transition_index
            for record in trace
            if record.telemetry.charging_contact_before
            and not record.telemetry.charging_contact_after
        ],
        "first_seek_entry": [
            record.transition_index
            for record in trace
            if record.mode_before is D021Mode.AWAY
            and record.mode_after is D021Mode.SEEK
        ],
        "first_dual_contact_entry": [
            record.transition_index
            for record in trace
            if not record.telemetry.charging_contact_before
            and record.telemetry.charging_contact_after
        ],
        "first_legacy_without_dual_entry": [
            record.transition_index
            for record in trace
            if d024.legacy_circular_contact(
                record.telemetry.position_after,
                record.telemetry.station_center,
                config,
            )
            and not record.telemetry.charging_contact_after
        ],
    }
    for name, values in candidates.items():
        if values:
            events[name] = values[0]
    return events


def select_d024_replay_indices(
    trace: Sequence[D021TransitionTrace],
) -> tuple[int, ...]:
    """Select actual D-024 steps with deterministic event-preserving sampling."""
    if not trace:
        raise ValueError("D-024 replay trace must not be empty")
    event_steps = d024_replay_event_steps(trace)
    trace_by_step = {record.transition_index: record for record in trace}
    selected = set(event_steps.values())
    for step in event_steps.values():
        selected.update(
            candidate
            for candidate in range(step - 2, step + 3)
            if candidate in trace_by_step
        )
    run_start = 0
    while run_start < len(trace):
        run_end = run_start
        mode = trace[run_start].mode_before
        while run_end + 1 < len(trace) and trace[run_end + 1].mode_before is mode:
            run_end += 1
        selected.add(trace[(run_start + run_end) // 2].transition_index)
        run_start = run_end + 1
    stride = (len(trace) + 699) // 700
    selected.update(record.transition_index for record in trace[::stride])
    selected.add(trace[-1].transition_index)
    return tuple(sorted(selected))


def adapt_d024_trace(
    trace: Sequence[D021TransitionTrace],
    *,
    seed: int,
    source_label: str = "D-024 causal finite-body dual-contact lifetime",
) -> DevelopmentVisualizationData:
    """Convert one completed causal D-024 trace to neutral replay data."""
    from . import d024
    from .d020 import D020PhysicalConfig

    _validate_d024_visualization_seed(seed)
    if not trace:
        raise ValueError("D-024 replay trace must not be empty")
    config = D020PhysicalConfig()
    selected_steps = select_d024_replay_indices(trace)
    by_step = {record.transition_index: record for record in trace}
    initial = trace[0]
    if len(initial.observation_before) != 6:
        raise RuntimeError("D-024 initial observation must contain six channels")
    initial_observation = initial.observation_before
    frames: list[DevelopmentVisualizationFrame] = [
        DevelopmentVisualizationFrame(
            transition_index=0,
            x=initial.telemetry.position_before[0],
            y=initial.telemetry.position_before[1],
            heading=initial.telemetry.heading,
            action="INITIAL",
            decision_mode=initial.mode_before.value,
            energy=initial_observation[0],
            thermal=initial.telemetry.body_temperature_before_c,
            charging_contact=bool(initial_observation[4]),
            terminated=False,
            truncated=False,
            beacon_left=initial_observation[1],
            beacon_forward=initial_observation[2],
            beacon_right=initial_observation[3],
            thermal_normalized=initial_observation[5],
            thermal_absolute_c=initial.telemetry.body_temperature_before_c,
            charger_phase=initial.telemetry.charge_phase.value,
            simulated_seconds=0.0,
            charging_contact_before=initial.telemetry.charging_contact_before,
        )
    ]
    for step in selected_steps:
        record = by_step[step]
        if len(record.observation) != 6:
            raise RuntimeError("D-024 observation must contain exactly six channels")
        if record.reward != 0.0 or record.info != {}:
            raise RuntimeError("D-024 replay crossed the reward/info boundary")
        observation = record.observation
        telemetry = record.telemetry
        frames.append(
            DevelopmentVisualizationFrame(
                transition_index=record.transition_index,
                x=telemetry.position_after[0],
                y=telemetry.position_after[1],
                heading=telemetry.heading,
                action=record.action.name,
                decision_mode=record.mode_before.value,
                energy=observation[0],
                thermal=telemetry.body_temperature_after_c,
                charging_contact=bool(observation[4]),
                terminated=telemetry.terminated,
                truncated=telemetry.truncated,
                beacon_left=observation[1],
                beacon_forward=observation[2],
                beacon_right=observation[3],
                thermal_normalized=observation[5],
                thermal_absolute_c=telemetry.body_temperature_after_c,
                charger_phase=telemetry.charge_phase.value,
                simulated_seconds=record.transition_index * config.dt_seconds,
                charging_contact_before=telemetry.charging_contact_before,
            )
        )
    dock_plus, dock_minus = d024.dock_contacts_world(d024.D024_STATION_CENTER)
    return DevelopmentVisualizationData(
        source_label=source_label,
        seed=seed,
        world_min=config.world_min,
        world_max=config.world_max,
        station_center=trace[0].telemetry.station_center,
        charging_radius=None,
        energy_range=DevelopmentVisualizationRange(0.0, 1.0),
        thermal_range=DevelopmentVisualizationRange(0.0, 80.0),
        frames=tuple(frames),
        visibility=DevelopmentVisualizationVisibility(
            position_heading="EVALUATOR ONLY — CAUSAL BODY GEOMETRY",
            station_location="EVALUATOR ONLY",
            energy="ORGANISM-VISIBLE NORMALIZED + EVALUATOR",
            thermal=(
                "ORGANISM-VISIBLE NORMALIZED OWN TEMPERATURE + "
                "EVALUATOR ABSOLUTE °C"
            ),
            charging_contact="ORGANISM-VISIBLE BINARY DUAL CONTACT + EVALUATOR",
            action_decision_mode=(
                "CONTROLLER MODE SHOWN; CHARGER PHASE EVALUATOR ONLY"
            ),
        ),
        probe_distance=config.probe_distance,
        sensor_angle=config.sensor_angle,
        thermal_threshold=config.preferred_operating_ceiling_c,
        thermal_threshold_label="PREFERRED 45°C — EVALUATOR ONLY",
        energy_label="BATTERY (NORMALIZED)",
        mode_display_label="controller mode",
        causal_geometry=DevelopmentCausalGeometry(
            body_length=d024.D024_BODY_LENGTH,
            body_width=d024.D024_BODY_WIDTH,
            rear_contact_plus=(
                d024.D024_REAR_X,
                d024.D024_CONTACT_LATERAL_OFFSET,
            ),
            rear_contact_minus=(
                d024.D024_REAR_X,
                -d024.D024_CONTACT_LATERAL_OFFSET,
            ),
            front_midpoint=(d024.D024_BODY_LENGTH / 2.0, 0.0),
            dock_orientation=d024.D024_DOCK_ORIENTATION,
            dock_contact_plus=dock_plus,
            dock_contact_minus=dock_minus,
            contact_tolerance=d024.D024_CONTACT_TOLERANCE,
        ),
    )


def build_d024_development_visualization(
    *,
    seed: int = 18365,
    horizon: int = 70_000,
) -> DevelopmentVisualizationData:
    """Run one exact D-024 lifetime, then adapt its evaluator trace."""
    from . import d024

    _validate_d024_visualization_seed(seed)
    if horizon != d024.D024_HORIZON:
        raise ValueError(
            "D-024 visualization requires the frozen 70,000-transition horizon"
        )
    trace = d024.run_d024_lifetime_trace(seed, horizon=horizon)
    return adapt_d024_trace(trace, seed=seed)


DevelopmentVisualizationAdapter = Callable[..., DevelopmentVisualizationData]
DEVELOPMENT_VISUALIZATION_ADAPTERS: Final[
    dict[str, DevelopmentVisualizationAdapter]
] = {
    "d003": build_d003_development_visualization,
    "d005": build_d005_development_visualization,
    "d006": build_d006_development_visualization,
    "d011": build_d011_development_visualization,
    "d012": build_d012_development_visualization,
    "d013-reference": build_d013_reference_development_visualization,
    "d013": build_d013_development_visualization,
    "d014": build_d014_development_visualization,
    "d015-reference": build_d015_reference_development_visualization,
    "d015": build_d015_development_visualization,
    "d017": build_d017_development_visualization,
    "d018": build_d018_development_visualization,
    "d021": build_d021_development_visualization,
    "d023": build_d023_development_visualization,
    "d024": build_d024_development_visualization,
}


def build_development_visualization(
    source: str,
    *,
    seed: int,
    horizon: int = 1000,
) -> DevelopmentVisualizationData:
    """Build neutral data through the explicitly registered source adapter."""
    try:
        adapter = DEVELOPMENT_VISUALIZATION_ADAPTERS[source]
    except KeyError as error:
        supported = ", ".join(sorted(DEVELOPMENT_VISUALIZATION_ADAPTERS))
        raise ValueError(
            f"unknown development visualization source {source!r}; "
            f"supported: {supported}"
        ) from error
    return adapter(seed=seed, horizon=horizon)


def show_development_visualization(
    data: DevelopmentVisualizationData,
    *,
    interval_ms: int = 90,
) -> Figure:
    """Build and show a completed-trace visualization."""
    figure, _animation = build_development_visualization_figure(
        data, interval_ms=interval_ms
    )
    plt.show()
    return figure


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Replay a canonical post-hoc Aweform development trace."
    )
    parser.add_argument(
        "--source", required=True, help="Registered source adapter, e.g. d003."
    )
    parser.add_argument(
        "--seed", type=int, required=True, help="Legal development seed."
    )
    parser.add_argument("--horizon", type=_positive_int, default=1000)
    parser.add_argument("--interval-ms", type=_positive_int, default=90)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run one source adapter to completion and open the replay window."""
    args = _parse_args(argv)
    try:
        data = build_development_visualization(
            args.source, seed=args.seed, horizon=args.horizon
        )
    except ValueError as error:
        raise SystemExit(str(error)) from error
    show_development_visualization(data, interval_ms=args.interval_ms)
    return 0


def d020_main(argv: Sequence[str] | None = None) -> int:
    """Open the exact D-020 mixed-action visualization."""
    parser = argparse.ArgumentParser(
        description="Replay the seedless D-020 mixed-action causal probe."
    )
    parser.add_argument("--interval-ms", type=_positive_int, default=650)
    args = parser.parse_args(argv)
    data = build_d020_development_visualization()
    show_development_visualization(data, interval_ms=args.interval_ms)
    return 0


def d021_main(argv: Sequence[str] | None = None) -> int:
    """Open the fixed canonical D-021 autonomous lifetime visualization."""
    parser = argparse.ArgumentParser(
        description="Replay the canonical D-021 seed 18365 lifetime."
    )
    parser.add_argument("--interval-ms", type=_positive_int, default=90)
    args = parser.parse_args(argv)
    data = build_d021_development_visualization()
    show_development_visualization(data, interval_ms=args.interval_ms)
    return 0


def d024_main(argv: Sequence[str] | None = None) -> int:
    """Open one exact-horizon D-024 causal docking visualization."""
    from .d024 import D024_DEFAULT_DEVELOPMENT_SEEDS

    parser = argparse.ArgumentParser(
        description="Replay one frozen D-024 causal dual-contact lifetime."
    )
    parser.add_argument(
        "--seed",
        type=int,
        choices=D024_DEFAULT_DEVELOPMENT_SEEDS,
        default=D024_DEFAULT_DEVELOPMENT_SEEDS[0],
    )
    parser.add_argument("--interval-ms", type=_positive_int, default=90)
    args = parser.parse_args(argv)
    data = build_d024_development_visualization(seed=args.seed, horizon=70_000)
    show_development_visualization(data, interval_ms=args.interval_ms)
    return 0


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("value must be an integer") from error
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def _validate_coordinate(name: str, coordinate: Coordinate) -> None:
    if len(coordinate) != 2 or not all(math.isfinite(value) for value in coordinate):
        raise ValueError(f"{name} must contain two finite coordinates")


def _coordinate_from_sequence(value: object, name: str) -> Coordinate:
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise ValueError(f"{name} must contain two coordinates")
    if not all(
        isinstance(item, (int, float)) and not isinstance(item, bool) for item in value
    ):
        raise ValueError(f"{name} must contain numeric coordinates")
    coordinate = (float(value[0]), float(value[1]))
    _validate_coordinate(name, coordinate)
    return coordinate


def _require_int(mapping: Mapping[str, object], name: str) -> int:
    value = mapping.get(name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"D-003 result field {name!r} must be an integer")
    return value


def _require_int_attribute(value: object, name: str) -> int:
    field = getattr(value, name, None)
    if isinstance(field, bool) or not isinstance(field, int):
        raise ValueError(f"trace field {name!r} must be an integer")
    return field


def _require_float_attribute(value: object, name: str) -> float:
    field = getattr(value, name, None)
    if not isinstance(field, (int, float)) or isinstance(field, bool):
        raise ValueError(f"trace field {name!r} must be numeric")
    number = float(field)
    if not math.isfinite(number):
        raise ValueError(f"trace field {name!r} must be finite")
    return number


def _require_bool_attribute(value: object, name: str) -> bool:
    field = getattr(value, name, None)
    if not isinstance(field, bool):
        raise ValueError(f"trace field {name!r} must be a bool")
    return field
