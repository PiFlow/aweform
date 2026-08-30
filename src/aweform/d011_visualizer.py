"""Development-only visualizer for the merged D-011 controller."""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from typing import Any, Sequence

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation
from matplotlib.figure import Figure
from matplotlib.patches import Circle, Rectangle

from . import d011
from .d002 import D002ThermalStationEnv
from .d003 import HOT_DEPART_THRESHOLD
from .env import Action
from .exp003 import EXP003StationConfig, beacon_signal

_ACTIVE_ANIMATIONS: list[FuncAnimation] = []
_DEFAULT_INTERVAL_MS = 60


@dataclass(frozen=True, slots=True)
class D011VisualizationFrame:
    """One post-controller decision state, with evaluator geometry for drawing."""

    step_index: int
    x: float
    y: float
    heading: float
    path: tuple[tuple[float, float], ...]
    mode: d011.D011Mode
    action: Action | None
    energy: float
    thermal: float
    beacon_left: float
    beacon_forward: float
    beacon_right: float
    charging_contact: bool


@dataclass(frozen=True, slots=True)
class D011VisualizationTrace:
    """Completed D-011 replay plus evaluator-only world geometry."""

    seed: int
    horizon: int
    world_min: tuple[float, float]
    world_max: tuple[float, float]
    station_center: tuple[float, float]
    charging_radius: float
    probe_distance: float
    sensor_angle: float
    beacon_scale: float
    frames: tuple[D011VisualizationFrame, ...]
    actions: tuple[Action, ...]


def build_d011_visualization_trace(
    seed: int = d011.D011_DEFAULT_DEVELOPMENT_SEEDS[0],
    *,
    horizon: int = 1000,
) -> D011VisualizationTrace:
    """Run one legal D-011 development replay and capture its visible trace."""
    d011._validate_d011_development_seeds((seed,))
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon <= 0:
        raise ValueError("horizon must be a positive integer")

    config = EXP003StationConfig(episode_horizon=horizon)
    environment = D002ThermalStationEnv(config=config)
    observation, info = environment.reset(seed=seed)
    if info != {}:
        raise RuntimeError("D-002 reset crossed the information boundary")
    _, observation = d011._prepare_post_contact_setup(environment)
    if environment.base_env.random_streams is None:
        raise RuntimeError("D-002 policy RNG is unavailable after reset")

    controller = d011.D011Controller(environment.base_env.random_streams.policy)
    controller.reset()
    body = environment.body
    station = environment.station_center
    if body is None or station is None:
        raise RuntimeError("D-011 evaluator geometry is unavailable after setup")

    path: list[tuple[float, float]] = [body.position]
    frames: list[D011VisualizationFrame] = []
    actions: list[Action] = []
    terminated = False
    truncated = False
    while not (terminated or truncated):
        visible = d011._controller_observation(observation)
        action = controller.act(visible)
        frames.append(
            _make_frame(
                step_index=len(actions),
                body=body,
                path=path,
                mode=controller.mode,
                action=action,
                visible=visible,
            )
        )
        actions.append(action)
        observation, reward, terminated, truncated, info = environment.step(action)
        if reward != 0.0 or info != {}:
            raise RuntimeError("D-011 replay crossed the reward/info boundary")
        if environment.last_transition is None:
            raise RuntimeError("D-011 transition telemetry is unavailable")
        path.append(body.position)

    terminal_visible = d011._controller_observation(observation)
    frames.append(
        _make_frame(
            step_index=len(actions),
            body=body,
            path=path,
            mode=controller.mode,
            action=None,
            visible=terminal_visible,
        )
    )
    return D011VisualizationTrace(
        seed=seed,
        horizon=horizon,
        world_min=config.world_min,
        world_max=config.world_max,
        station_center=station,
        charging_radius=config.charging_radius,
        probe_distance=config.probe_distance,
        sensor_angle=config.sensor_angle,
        beacon_scale=config.beacon_scale,
        frames=tuple(frames),
        actions=tuple(actions),
    )


def build_d011_visualization_figure(
    trace: D011VisualizationTrace,
    *,
    interval_ms: int = _DEFAULT_INTERVAL_MS,
) -> tuple[Figure, FuncAnimation]:
    """Create the single animated world/status figure from a completed trace."""
    if isinstance(interval_ms, bool) or not isinstance(interval_ms, int):
        raise ValueError("interval_ms must be a positive integer")
    if interval_ms <= 0:
        raise ValueError("interval_ms must be a positive integer")

    figure, (world_axis, status_axis) = plt.subplots(
        1, 2, figsize=(13, 6.5), gridspec_kw={"width_ratios": (1.55, 1)},
        constrained_layout=True,
    )
    figure.suptitle(
        "D-011 DEVELOPMENT VISUALIZATION — descriptive/debug view only",
        fontsize=13,
    )
    figure.text(
        0.5,
        0.01,
        "D-011 DEVELOPMENT VISUALIZATION\n"
        "World geometry is evaluator-only.\n"
        "Controller sees energy + thermal + L/F/R + contact.",
        ha="center",
        va="bottom",
        fontsize=8,
        color="#444444",
    )

    world_axis.set_title("WORLD — evaluator drawing")
    world_axis.set_xlim(trace.world_min[0], trace.world_max[0])
    world_axis.set_ylim(trace.world_min[1], trace.world_max[1])
    world_axis.set_aspect("equal")
    world_axis.set_xlabel("x")
    world_axis.set_ylabel("y")
    world_axis.add_patch(
        Rectangle(
            trace.world_min,
            trace.world_max[0] - trace.world_min[0],
            trace.world_max[1] - trace.world_min[1],
            fill=False,
            edgecolor="#333333",
            linewidth=1.5,
        )
    )

    grid_x = np.linspace(trace.world_min[0], trace.world_max[0], 50)
    grid_y = np.linspace(trace.world_min[1], trace.world_max[1], 50)
    signal_field = np.asarray(
        [
            [
                beacon_signal(
                    math.dist((x, y), trace.station_center), trace.beacon_scale
                )
                for x in grid_x
            ]
            for y in grid_y
        ],
        dtype=float,
    )
    world_axis.imshow(
        signal_field,
        origin="lower",
        extent=(
            trace.world_min[0],
            trace.world_max[0],
            trace.world_min[1],
            trace.world_max[1],
        ),
        cmap="Blues",
        alpha=0.18,
    )
    world_axis.add_patch(
        Circle(
            trace.station_center,
            trace.charging_radius,
            fill=False,
            edgecolor="darkorange",
            linewidth=2.2,
        )
    )
    world_axis.scatter(
        *trace.station_center,
        marker="+",
        s=130,
        color="darkorange",
        label="charging station (evaluator)",
    )
    world_axis.text(
        0.02,
        0.98,
        "blue = idealized beacon field\n"
        "orange circle = physical charging radius\n"
        "probe rays = directional signal display only",
        transform=world_axis.transAxes,
        va="top",
        fontsize=8,
    )

    (path_line,) = world_axis.plot([], [], color="#222222", linewidth=1.2, label="path")
    (body_marker,) = world_axis.plot([], [], "o", color="#111111", markersize=8)
    (heading_line,) = world_axis.plot(
        [], [], color="#111111", linewidth=2.0, marker=">", markevery=[-1]
    )
    probe_lines = [
        world_axis.plot([], [], color=color, linewidth=1.2, label=label)[0]
        for color, label in (
            ("#6a3d9a", "left probe"),
            ("#1f78b4", "forward probe"),
            ("#e31a1c", "right probe"),
        )
    ]
    world_axis.legend(loc="lower right", fontsize=8)

    status_axis.set_title("ORGANISM STATE — current decision state")
    status_axis.set_xlim(0.0, 1.0)
    status_axis.set_ylim(0.0, 1.0)
    status_axis.axis("off")
    mode_text = status_axis.text(0.03, 0.91, "", fontsize=12, weight="bold")
    action_text = status_axis.text(0.03, 0.85, "", fontsize=11)
    contact_text = status_axis.text(0.03, 0.79, "", fontsize=11, weight="bold")
    transition_text = status_axis.text(0.03, 0.96, "", fontsize=9)
    status_axis.text(0.03, 0.72, "ENERGY", fontsize=9, weight="bold")
    status_axis.text(0.03, 0.58, "THERMAL", fontsize=9, weight="bold")
    status_axis.text(0.03, 0.40, "BEACON — idealized directional signals", fontsize=9)
    status_axis.text(
        0.03, 0.09, f"seed: {trace.seed}  |  horizon: {trace.horizon}", fontsize=9
    )
    status_axis.text(
        0.03,
        0.04,
        "All bars are normalized 0–1",
        fontsize=8,
        color="#555555",
    )

    energy_fill = _make_bar(status_axis, 0.25, 0.65, 0.68, "#2ca25f")
    thermal_fill = _make_bar(status_axis, 0.25, 0.51, 0.68, "#fdae61")
    beacon_fills = [
        _make_bar(status_axis, 0.25, y, 0.68, color)
        for y, color in ((0.31, "#6a3d9a"), (0.24, "#1f78b4"), (0.17, "#e31a1c"))
    ]
    threshold_x = 0.25 + 0.68 * HOT_DEPART_THRESHOLD
    status_axis.plot(
        [threshold_x, threshold_x], [0.50, 0.575], color="#b2182b", linewidth=2
    )
    status_axis.text(
        threshold_x,
        0.59,
        "HOT_DEPART_THRESHOLD",
        ha="center",
        va="bottom",
        fontsize=7,
        color="#b2182b",
        rotation=90,
    )
    bar_values = [
        status_axis.text(0.96, 0.68, "", ha="right", va="center", fontsize=10),
        status_axis.text(0.96, 0.54, "", ha="right", va="center", fontsize=10),
        status_axis.text(0.96, 0.34, "", ha="right", va="center", fontsize=9),
        status_axis.text(0.96, 0.27, "", ha="right", va="center", fontsize=9),
        status_axis.text(0.96, 0.20, "", ha="right", va="center", fontsize=9),
    ]
    beacon_labels = [
        status_axis.text(0.20, y + 0.03, label, ha="right", fontsize=8)
        for y, label in ((0.31, "L"), (0.24, "F"), (0.17, "R"))
    ]

    def update(frame_index: int) -> tuple[Any, ...]:
        frame = trace.frames[frame_index]
        path_line.set_data(
            [point[0] for point in frame.path], [point[1] for point in frame.path]
        )
        body_marker.set_data([frame.x], [frame.y])
        heading_endpoint = _heading_endpoint(frame, trace.probe_distance * 0.7)
        heading_line.set_data(
            [frame.x, heading_endpoint[0]], [frame.y, heading_endpoint[1]]
        )
        signals = (frame.beacon_left, frame.beacon_forward, frame.beacon_right)
        endpoints = _probe_endpoints(frame, trace)
        for line, endpoint, signal in zip(probe_lines, endpoints, signals):
            line.set_data([frame.x, endpoint[0]], [frame.y, endpoint[1]])
            line.set_alpha(0.15 + 0.85 * signal)
            line.set_linewidth(0.8 + 2.0 * signal)

        mode_text.set_text(f"MODE: {frame.mode.value}")
        action_text.set_text(
            f"ACTION: {frame.action.name if frame.action is not None else '—'}"
        )
        contact_text.set_text(
            f"CONTACT: {'TRUE' if frame.charging_contact else 'FALSE'}"
        )
        contact_text.set_color("#16803c" if frame.charging_contact else "#b2182b")
        transition_text.set_text(f"transition: {frame.step_index}")
        _set_bar(energy_fill, frame.energy)
        _set_bar(thermal_fill, frame.thermal)
        for fill, value in zip(beacon_fills, signals):
            _set_bar(fill, value)
        bar_values[0].set_text(f"{frame.energy:.3f}")
        bar_values[1].set_text(f"{frame.thermal:.3f}")
        for text, value in zip(bar_values[2:], signals):
            text.set_text(f"{value:.3f}")
        return (
            path_line,
            body_marker,
            heading_line,
            *probe_lines,
            mode_text,
            action_text,
            contact_text,
            transition_text,
            energy_fill,
            thermal_fill,
            *beacon_fills,
            *bar_values,
            *beacon_labels,
        )

    animation = FuncAnimation(
        figure,
        update,
        frames=len(trace.frames),
        interval=interval_ms,
        blit=False,
        repeat=False,
    )
    return figure, animation


def show_d011_visualization(
    trace: D011VisualizationTrace, *, interval_ms: int = _DEFAULT_INTERVAL_MS
) -> None:
    """Show a completed D-011 trace in an interactive Matplotlib window."""
    _, animation = build_d011_visualization_figure(trace, interval_ms=interval_ms)
    _ACTIVE_ANIMATIONS.append(animation)
    try:
        plt.show()
    finally:
        _ACTIVE_ANIMATIONS.remove(animation)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the D-011 development visualizer CLI."""
    parser = argparse.ArgumentParser(description="Visualize D-011 development")
    parser.add_argument(
        "--seed",
        type=int,
        choices=d011.D011_DEFAULT_DEVELOPMENT_SEEDS,
        default=d011.D011_DEFAULT_DEVELOPMENT_SEEDS[0],
    )
    parser.add_argument("--horizon", type=_positive_int, default=1000)
    parser.add_argument(
        "--interval-ms", type=_positive_int, default=_DEFAULT_INTERVAL_MS
    )
    args = parser.parse_args(argv)
    trace = build_d011_visualization_trace(args.seed, horizon=args.horizon)
    show_d011_visualization(trace, interval_ms=args.interval_ms)
    return 0


def _make_frame(
    *,
    step_index: int,
    body: Any,
    path: Sequence[tuple[float, float]],
    mode: d011.D011Mode,
    action: Action | None,
    visible: d011.D011Observation,
) -> D011VisualizationFrame:
    return D011VisualizationFrame(
        step_index=step_index,
        x=body.x,
        y=body.y,
        heading=body.heading,
        path=tuple(path),
        mode=mode,
        action=action,
        energy=visible.energy,
        thermal=visible.thermal,
        beacon_left=visible.beacon.left,
        beacon_forward=visible.beacon.forward,
        beacon_right=visible.beacon.right,
        charging_contact=visible.charging_contact,
    )


def _probe_endpoints(
    frame: D011VisualizationFrame, trace: D011VisualizationTrace
) -> tuple[tuple[float, float], ...]:
    angles = (
        frame.heading + trace.sensor_angle,
        frame.heading,
        frame.heading - trace.sensor_angle,
    )
    return tuple(
        (
            frame.x + trace.probe_distance * math.cos(angle),
            frame.y + trace.probe_distance * math.sin(angle),
        )
        for angle in angles
    )


def _heading_endpoint(
    frame: D011VisualizationFrame, distance: float
) -> tuple[float, float]:
    return (
        frame.x + distance * math.cos(frame.heading),
        frame.y + distance * math.sin(frame.heading),
    )


def _make_bar(
    axis: Any, x: float, y: float, width: float, color: str
) -> Rectangle:
    axis.add_patch(
        Rectangle((x, y), width, 0.055, facecolor="#eeeeee", edgecolor="none")
    )
    fill = Rectangle((x, y), 0.0, 0.055, facecolor=color, edgecolor="none")
    axis.add_patch(fill)
    return fill


def _set_bar(bar: Rectangle, value: float) -> None:
    bar.set_width(max(0.0, min(1.0, value)) * 0.68)


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be an integer") from error
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
