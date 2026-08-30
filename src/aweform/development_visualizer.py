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
from matplotlib.animation import FuncAnimation
from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Rectangle
from matplotlib.text import Text

Coordinate = tuple[float, float]


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

    def __post_init__(self) -> None:
        if self.transition_index <= 0:
            raise ValueError("transition_index must be positive")
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


@dataclass(frozen=True, slots=True)
class DevelopmentVisualizationData:
    """All neutral data required by the shared development renderer."""

    source_label: str
    seed: int
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

    def __post_init__(self) -> None:
        if not self.source_label:
            raise ValueError("source_label must be non-empty")
        if not self.energy_label:
            raise ValueError("energy_label must be non-empty")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise ValueError("seed must be an integer")
        _validate_coordinate("world_min", self.world_min)
        _validate_coordinate("world_max", self.world_max)
        if not all(
            lower < upper for lower, upper in zip(self.world_min, self.world_max)
        ):
            raise ValueError("world_min must be strictly below world_max")
        if not self.frames:
            raise ValueError("visualization data must contain at least one frame")
        if any(
            frame.transition_index != index
            for index, frame in enumerate(self.frames, start=1)
        ):
            raise ValueError("frames must contain one ordered entry per transition")
        if self.station_center is None:
            if self.charging_radius is not None:
                raise ValueError("charging_radius requires station_center")
        else:
            _validate_coordinate("station_center", self.station_center)
            if self.charging_radius is None or not math.isfinite(self.charging_radius):
                raise ValueError("station visualizations require a finite radius")
            if self.charging_radius < 0:
                raise ValueError("charging_radius must be non-negative")
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

    if data.station_center is not None and data.charging_radius is not None:
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
        world_axis.text(
            0.02,
            0.97,
            "directional probes = idealized beacon display\n(not literal RF beams)",
            transform=world_axis.transAxes,
            va="top",
            fontsize=8,
        )
    world_axis.legend(loc="lower left", fontsize=8)

    diagnostic_axis.set_xlim(0.0, 1.0)
    diagnostic_axis.set_ylim(-0.34, 1.15 if beacon_values_available else 1.0)
    diagnostic_axis.axis("off")
    diagnostic_axis.set_title("EVALUATOR DIAGNOSTICS", loc="left")
    if beacon_values_available:
        top_y = (1.06, 0.99, 0.92, 0.85, 0.78)
        energy_y, thermal_y = 0.61, 0.47
    else:
        top_y = (0.86, 0.79, 0.72, 0.65, 0.58)
        energy_y, thermal_y = 0.41, 0.25
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
            data.thermal_threshold_label,
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
        "ACTION / DECISION MODE: "
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

    player = DevelopmentVisualizationPlayer(len(data.frames))

    def render(frame_index: int) -> tuple[Artist, ...]:
        frame = data.frames[frame_index]
        path = data.frames[: frame_index + 1]
        trajectory_line.set_data([item.x for item in path], [item.y for item in path])
        body_marker.set_data([frame.x], [frame.y])
        heading_arrow.set_offsets([[frame.x, frame.y]])
        heading_arrow.set_UVC([math.cos(frame.heading)], [math.sin(frame.heading)])
        transition_text.set_text(f"transition: {frame.transition_index}")
        action_text.set_text(f"action: {frame.action}")
        mode_text.set_text(f"decision mode: {frame.decision_mode}")
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
        energy_fill.set_width(_gauge_fraction(frame.energy, data.energy_range) * 0.62)
        thermal_fill.set_width(
            _gauge_fraction(frame.thermal, data.thermal_range) * 0.62
        )
        energy_value.set_text(f"{frame.energy:.3f} / {data.energy_range.upper:g}")
        thermal_value.set_text(f"{frame.thermal:.3f} / {data.thermal_range.upper:g}")
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
    figure.suptitle(
        "AWEFORM DEVELOPMENT VISUALIZER\n"
        f"{data.source_label} — seed {data.seed}\n"
        "DEVELOPMENT / EVALUATOR VIEW — NOT CONFIRMATORY EVIDENCE",
        fontsize=12,
    )
    figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.91))
    setattr(figure, "_aweform_player", player)
    setattr(figure, "_aweform_animation", animation)
    return figure, animation


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


def _build_d011_family_development_visualization(
    *,
    seed: int,
    horizon: int,
    source_label: str,
    validate_seed: Callable[[int], None],
) -> DevelopmentVisualizationData:
    """Replay a D-011-compatible lifetime through one shared controller path."""
    from . import d011
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
    controller = d011.D011Controller(random_streams.policy)
    controller.reset()
    if environment.body is None or environment.station_center is None:
        raise RuntimeError("D-011 evaluator geometry is unavailable after setup")

    frames: list[DevelopmentVisualizationFrame] = []
    terminated = False
    truncated = False
    while not (terminated or truncated):
        visible = d011._controller_observation(observation)
        mode_before = controller.mode
        action = controller.act(visible)
        observation, reward, terminated, truncated, info = environment.step(action)
        if reward != 0.0 or info != {}:
            raise RuntimeError("D-011 replay crossed the reward/info boundary")
        telemetry = environment.last_transition
        body = environment.body
        if telemetry is None or body is None:
            raise RuntimeError("D-011 transition telemetry is unavailable")
        next_visible = d011._controller_observation(observation)
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
    )


DevelopmentVisualizationAdapter = Callable[..., DevelopmentVisualizationData]
DEVELOPMENT_VISUALIZATION_ADAPTERS: Final[
    dict[str, DevelopmentVisualizationAdapter]
] = {
    "d003": build_d003_development_visualization,
    "d005": build_d005_development_visualization,
    "d006": build_d006_development_visualization,
    "d011": build_d011_development_visualization,
    "d012": build_d012_development_visualization,
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
