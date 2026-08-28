"""Focused tests for the canonical post-hoc development visualizer."""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest
from matplotlib.backend_bases import KeyEvent

from aweform.d003 import run_d003_probe
from aweform.development_visualizer import (
    DevelopmentVisualizationData,
    DevelopmentVisualizationFrame,
    DevelopmentVisualizationPlayer,
    DevelopmentVisualizationRange,
    DevelopmentVisualizationVisibility,
    adapt_d003_trace,
    build_d003_development_visualization,
    build_development_visualization,
    build_development_visualization_figure,
)


def test_d003_adapter_preserves_completed_trace_fields() -> None:
    result = run_d003_probe((18141,), horizon=5, collect_trace=True)
    run = result["results"][0]
    assert isinstance(run, dict)
    trace = run["trace"]
    assert isinstance(trace, tuple)

    data = adapt_d003_trace(run)

    assert len(data.frames) == 5
    assert data.station_center == (0.5, 0.5)
    for frame, entry in zip(data.frames, trace):
        assert frame.transition_index == entry.transition_index
        assert (frame.x, frame.y) == entry.position
        assert frame.heading == entry.heading
        assert frame.energy == entry.energy
        assert frame.thermal == entry.thermal
        assert frame.charging_contact == entry.charging_contact
        assert frame.action == entry.action.name
        assert frame.decision_mode == entry.controller_mode.value
        assert frame.terminated == entry.terminated
        assert frame.truncated == entry.truncated


def test_renderer_consumes_only_neutral_data_and_does_not_show(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = build_d003_development_visualization(seed=18141, horizon=3)
    monkeypatch.setattr(
        plt,
        "show",
        lambda: (_ for _ in ()).throw(AssertionError("must not show")),
    )
    figure, animation = build_development_visualization_figure(data)
    player = getattr(figure, "_aweform_player")
    assert player.frame_index == 0
    player.step_forward()
    assert player.frame_index == 1
    player.play()
    animation._func(0)
    assert player.frame_index == 2
    animation.event_source.stop()
    plt.close(figure)


def test_renderer_does_not_call_execution_apis_after_adaptation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = build_d003_development_visualization(seed=18141, horizon=3)
    monkeypatch.setattr(
        "aweform.d003.run_d003_probe",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("rendering must not rerun D-003")
        ),
    )
    figure, animation = build_development_visualization_figure(data)
    player = getattr(figure, "_aweform_player")
    player.step_forward()
    animation._func(1)
    animation.event_source.stop()
    plt.close(figure)


def test_visibility_labels_are_explicit() -> None:
    data = build_d003_development_visualization(seed=18141, horizon=1)
    assert data.visibility.position_heading == "EVALUATOR ONLY"
    assert data.visibility.station_location == "EVALUATOR ONLY"
    assert data.visibility.energy == "EVALUATOR ONLY"
    assert data.visibility.thermal == "CTRL + EVAL"
    assert data.visibility.charging_contact == "CTRL + EVAL"

    figure, animation = build_development_visualization_figure(data)
    rendered_text = "\n".join(
        text.get_text() for axis in figure.axes for text in axis.texts
    )
    assert "ENERGY — EVALUATOR ONLY" in rendered_text
    assert "THERMAL — CTRL + EVAL" in rendered_text
    assert "POSITION / HEADING: EVALUATOR ONLY" in rendered_text
    assert "STATION LOCATION: EVALUATOR ONLY" in rendered_text
    animation.event_source.stop()
    plt.close(figure)


def test_seed_guard_and_unknown_source() -> None:
    with pytest.raises(ValueError):
        build_development_visualization("d003", seed=50001, horizon=1)
    with pytest.raises(ValueError, match="unknown development visualization source"):
        build_development_visualization("d005", seed=18141, horizon=1)


def test_player_controls_and_bounds() -> None:
    player = DevelopmentVisualizationPlayer(3)
    assert not player.playing
    assert player.step_backward() == 0
    assert player.step_forward() == 1
    assert player.step_forward() == 2
    assert player.step_forward() == 2
    assert player.step_backward() == 1
    assert player.toggle_play_pause()
    assert player.playing
    assert player.step_forward() == 2
    assert not player.toggle_play_pause()
    assert player.restart() == 0


def test_neutral_model_and_figure_construction_are_headless() -> None:
    frame = DevelopmentVisualizationFrame(
        transition_index=1,
        x=0.5,
        y=0.5,
        heading=0.0,
        action="WAIT",
        decision_mode="CHARGE",
        energy=5.0,
        thermal=0.2,
        charging_contact=True,
        terminated=False,
        truncated=True,
    )
    data = DevelopmentVisualizationData(
        source_label="synthetic",
        seed=1,
        world_min=(0.0, 0.0),
        world_max=(1.0, 1.0),
        station_center=(0.5, 0.5),
        charging_radius=0.1,
        energy_range=DevelopmentVisualizationRange(0.0, 10.0),
        thermal_range=DevelopmentVisualizationRange(0.0, 1.0),
        frames=(frame,),
        visibility=DevelopmentVisualizationVisibility(
            position_heading="SYNTHETIC EVALUATOR",
            station_location="SYNTHETIC EVALUATOR",
            energy="SYNTHETIC ORGANISM",
            thermal="SYNTHETIC ORGANISM + EVALUATOR",
            charging_contact="SYNTHETIC ORGANISM + EVALUATOR",
            action_decision_mode="SYNTHETIC CONTROLLER STATE",
        ),
    )
    figure, animation = build_development_visualization_figure(data)
    assert len(figure.axes) == 2
    animation.event_source.stop()
    plt.close(figure)


def test_neutral_model_requires_explicit_visibility() -> None:
    frame = DevelopmentVisualizationFrame(
        transition_index=1,
        x=0.5,
        y=0.5,
        heading=0.0,
        action="WAIT",
        decision_mode="CHARGE",
        energy=5.0,
        thermal=0.2,
        charging_contact=True,
        terminated=False,
        truncated=True,
    )
    with pytest.raises(TypeError):
        DevelopmentVisualizationData(
            source_label="synthetic",
            seed=1,
            world_min=(0.0, 0.0),
            world_max=(1.0, 1.0),
            station_center=(0.5, 0.5),
            charging_radius=0.1,
            energy_range=DevelopmentVisualizationRange(0.0, 10.0),
            thermal_range=DevelopmentVisualizationRange(0.0, 1.0),
            frames=(frame,),
        )


def test_figure_keyboard_controls_drive_only_the_display_player() -> None:
    data = build_d003_development_visualization(seed=18141, horizon=3)
    figure, animation = build_development_visualization_figure(data)
    player = getattr(figure, "_aweform_player")

    def press(key: str) -> None:
        event = KeyEvent("key_press_event", figure.canvas, key=key)
        figure.canvas.callbacks.process("key_press_event", event)

    press("right")
    assert player.frame_index == 1
    press("left")
    assert player.frame_index == 0
    press(" ")
    assert player.playing
    press(" ")
    assert not player.playing
    press("right")
    press("r")
    assert player.frame_index == 0

    animation.event_source.stop()
    plt.close(figure)
