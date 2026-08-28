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

    position_heading: str = "EVALUATOR ONLY"
    station_location: str = "EVALUATOR ONLY"
    energy: str = "EVALUATOR ONLY"
    thermal: str = "CTRL + EVAL"
    charging_contact: str = "CTRL + EVAL"
    action_decision_mode: str = "ORGANISM-OWNED / CONTROLLER STATE SHOWN BY EVALUATOR"


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
    visibility: DevelopmentVisualizationVisibility = (
        DevelopmentVisualizationVisibility()
    )

    def __post_init__(self) -> None:
        if not self.source_label:
            raise ValueError("source_label must be non-empty")
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
    world_axis.legend(loc="lower left", fontsize=8)

    diagnostic_axis.set_xlim(0.0, 1.0)
    diagnostic_axis.set_ylim(0.0, 1.0)
    diagnostic_axis.axis("off")
    diagnostic_axis.set_title("EVALUATOR DIAGNOSTICS", loc="left")
    diagnostic_axis.text(
        0.02,
        0.97,
        "DEVELOPMENT / EVALUATOR VIEW\nNOT CONFIRMATORY EVIDENCE",
        va="top",
        fontsize=10,
        color="tab:red",
        weight="bold",
    )
    transition_text = diagnostic_axis.text(
        0.02, 0.82, "", family="monospace", fontsize=11
    )
    action_text = diagnostic_axis.text(0.02, 0.76, "", family="monospace", fontsize=11)
    mode_text = diagnostic_axis.text(0.02, 0.70, "", family="monospace", fontsize=11)
    contact_text = diagnostic_axis.text(0.02, 0.64, "", family="monospace", fontsize=11)
    status_text = diagnostic_axis.text(0.02, 0.58, "", family="monospace", fontsize=11)

    energy_background, energy_fill, energy_value = _make_gauge(
        diagnostic_axis,
        y=0.44,
        label="ENERGY",
        visibility=data.visibility.energy,
        value_range=data.energy_range,
    )
    thermal_background, thermal_fill, thermal_value = _make_gauge(
        diagnostic_axis,
        y=0.30,
        label="THERMAL",
        visibility=data.visibility.thermal,
        value_range=data.thermal_range,
    )
    del energy_background, thermal_background
    diagnostic_axis.text(
        0.02,
        0.16,
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
        0.02,
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
        return (
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
        )

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
        facecolor="tab:blue" if label == "ENERGY" else "tab:orange",
        edgecolor="none",
    )
    axis.add_patch(background)
    axis.add_patch(fill)
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
        visibility=DevelopmentVisualizationVisibility(),
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


DevelopmentVisualizationAdapter = Callable[..., DevelopmentVisualizationData]
DEVELOPMENT_VISUALIZATION_ADAPTERS: Final[
    dict[str, DevelopmentVisualizationAdapter]
] = {
    "d003": build_d003_development_visualization,
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
