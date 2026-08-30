"""Focused headless tests for the D-011 development visualizer."""

from __future__ import annotations

import math
import sys
from collections import Counter
from dataclasses import fields

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest

from aweform import d011
from aweform.d011_visualizer import (
    D011VisualizationFrame,
    _probe_endpoints,
    build_d011_visualization_figure,
    build_d011_visualization_trace,
)
from aweform.env import Action


def test_trace_captures_position_heading_and_six_visible_channels() -> None:
    trace = build_d011_visualization_trace(18141, horizon=40)

    assert trace.seed == 18141
    assert len(trace.frames) == len(trace.actions) + 1
    frame_fields = {field.name for field in fields(D011VisualizationFrame)}
    assert {"x", "y", "heading", "path"} <= frame_fields
    assert {
        "energy",
        "thermal",
        "beacon_left",
        "beacon_forward",
        "beacon_right",
        "charging_contact",
    } <= frame_fields
    assert all(0.0 <= frame.energy <= 1.0 for frame in trace.frames)
    assert all(0.0 <= frame.thermal <= 1.0 for frame in trace.frames)


def test_geometry_is_visualization_state_not_d011_observation_state() -> None:
    assert {field.name for field in fields(d011.D011Observation)} == {
        "energy",
        "beacon",
        "thermal",
    }
    trace = build_d011_visualization_trace(18141, horizon=2)
    frame = trace.frames[0]
    assert not hasattr(d011.D011Observation, "x")
    assert not hasattr(d011.D011Observation, "heading")
    assert not hasattr(d011.D011Observation, "station_center")
    assert isinstance(frame.x, float)
    assert isinstance(frame.heading, float)
    assert trace.station_center == (0.5, 0.5)


def test_selected_actions_are_returned_by_d011_controller(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected: list[Action] = []
    original_act = d011.D011Controller.act

    def recording_act(
        controller: d011.D011Controller, observation: d011.D011Observation
    ) -> Action:
        action = original_act(controller, observation)
        selected.append(action)
        return action

    monkeypatch.setattr(d011.D011Controller, "act", recording_act)
    trace = build_d011_visualization_trace(18141, horizon=40)
    assert tuple(selected) == trace.actions


def test_visualization_replay_matches_d011_probe_behaviour() -> None:
    trace = build_d011_visualization_trace(18141, horizon=80)
    result = d011.run_d011_probe((18141,), horizon=80)
    run = result["results"][0]
    assert isinstance(run, dict)
    expected_counts = run["action_counts"]
    assert isinstance(expected_counts, dict)
    assert dict(Counter(action.name for action in trace.actions)) == expected_counts
    assert trace.frames[-1].energy == pytest.approx(run["final_normalized_energy"])
    assert trace.frames[-1].thermal == pytest.approx(run["final_thermal_state"])


def test_probe_geometry_uses_heading_and_existing_station_configuration() -> None:
    trace = build_d011_visualization_trace(18141, horizon=2)
    frame = trace.frames[0]
    endpoints = _probe_endpoints(frame, trace)
    for endpoint, angle in zip(
        endpoints,
        (
            frame.heading + trace.sensor_angle,
            frame.heading,
            frame.heading - trace.sensor_angle,
        ),
    ):
        assert endpoint == pytest.approx(
            (
                frame.x + trace.probe_distance * math.cos(angle),
                frame.y + trace.probe_distance * math.sin(angle),
            )
        )
    assert trace.probe_distance == pytest.approx(0.1)
    assert trace.sensor_angle == pytest.approx(math.pi / 4.0)


def test_figure_constructs_on_noninteractive_backend() -> None:
    trace = build_d011_visualization_trace(18141, horizon=4)
    figure, animation = build_d011_visualization_figure(trace, interval_ms=73)
    try:
        assert figure.canvas is not None
        assert animation.event_source is not None
        assert animation.event_source.interval == 73
    finally:
        plt.close(figure)


@pytest.mark.parametrize("seed", (50001, 42, 18144))
def test_invalid_reserved_and_non_d011_seeds_are_rejected(seed: int) -> None:
    with pytest.raises(ValueError):
        build_d011_visualization_trace(seed, horizon=1)


def test_d008_or_learner_state_cannot_affect_visualization_actions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline = build_d011_visualization_trace(18141, horizon=40)

    class ForbiddenPrediction:
        def __getattribute__(self, name: str) -> object:
            raise AssertionError(f"forbidden learner read: {name}")

    monkeypatch.setitem(sys.modules, "aweform.d008", ForbiddenPrediction())
    adversarial = build_d011_visualization_trace(18141, horizon=40)
    assert adversarial.actions == baseline.actions


def test_trace_does_not_add_a_learner_or_reward_channel() -> None:
    trace = build_d011_visualization_trace(18141, horizon=2)
    assert not hasattr(trace, "reward")
    assert not hasattr(trace, "prediction")
    assert not hasattr(trace.frames[0], "reward")
    assert not hasattr(trace.frames[0], "prediction")
