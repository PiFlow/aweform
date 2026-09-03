"""Focused tests for the canonical post-hoc development visualizer."""

import math
import sys
from collections import Counter
from dataclasses import fields, replace

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest
from matplotlib.backend_bases import KeyEvent

import aweform.development_visualizer as development_visualizer_module
from aweform import d011, d012, d013, d015, d018, d021, d023
from aweform.d003 import run_d003_probe
from aweform.d005 import run_d005_probe
from aweform.d006 import run_d006_probe
from aweform.d021 import D021TransitionTrace, run_d021_lifetime_trace
from aweform.development_visualizer import (
    DEVELOPMENT_VISUALIZATION_ADAPTERS,
    DevelopmentActionAlternative,
    DevelopmentConsequencePredictionFrame,
    DevelopmentVisualizationData,
    DevelopmentVisualizationFrame,
    DevelopmentVisualizationPlayer,
    DevelopmentVisualizationRange,
    DevelopmentVisualizationVisibility,
    adapt_d003_trace,
    adapt_d005_trace,
    adapt_d006_trace,
    build_d003_development_visualization,
    build_d005_development_visualization,
    build_d006_development_visualization,
    build_d011_development_visualization,
    build_d012_development_visualization,
    build_d013_development_visualization,
    build_d013_reference_development_visualization,
    build_d015_development_visualization,
    build_d015_reference_development_visualization,
    build_d018_development_visualization,
    build_d020_development_visualization,
    build_d021_development_visualization,
    build_d023_development_visualization,
    build_development_visualization,
    build_development_visualization_figure,
    d021_replay_event_steps,
    select_d021_replay_indices,
)
from aweform.env import Action


def _synthetic_consequence_data() -> DevelopmentVisualizationData:
    """Build small exact-value data for renderer MAE and scale assertions."""
    frames = tuple(
        DevelopmentVisualizationFrame(
            transition_index=index,
            x=0.5,
            y=0.5,
            heading=0.0,
            action="WAIT",
            decision_mode="CHARGE",
            energy=0.5,
            thermal=0.2,
            charging_contact=True,
            terminated=False,
            truncated=index == 3,
        )
        for index in range(1, 4)
    )
    predictions = tuple(
        DevelopmentConsequencePredictionFrame(
            transition_index=index,
            predicted_delta_energy=predicted_energy,
            observed_delta_energy=observed_energy,
            predicted_delta_thermal=0.0,
            observed_delta_thermal=observed_thermal,
            predicted_delta_charging_contact=0.0,
            observed_delta_charging_contact=0.0,
        )
        for index, (predicted_energy, observed_energy, observed_thermal) in enumerate(
            ((0.2, 0.1, 0.001), (-0.1, -0.4, -0.003), (0.4, 0.2, 0.002)),
            start=1,
        )
    )
    return DevelopmentVisualizationData(
        source_label="synthetic consequence MAE",
        seed=1,
        world_min=(0.0, 0.0),
        world_max=(1.0, 1.0),
        station_center=(0.5, 0.5),
        charging_radius=0.1,
        energy_range=DevelopmentVisualizationRange(0.0, 1.0),
        thermal_range=DevelopmentVisualizationRange(0.0, 1.0),
        frames=frames,
        visibility=DevelopmentVisualizationVisibility(
            position_heading="SYNTHETIC EVALUATOR",
            station_location="SYNTHETIC EVALUATOR",
            energy="SYNTHETIC ORGANISM",
            thermal="SYNTHETIC ORGANISM",
            charging_contact="SYNTHETIC ORGANISM",
            action_decision_mode="SYNTHETIC CONTROLLER STATE",
        ),
        consequence_predictions=predictions,
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


def test_d005_adapter_preserves_completed_trace_fields() -> None:
    result = run_d005_probe((18141,), horizon=5, collect_trace=True)
    run = result["results"][0]
    assert isinstance(run, dict)
    trace = run["trace"]
    assert isinstance(trace, tuple)

    data = adapt_d005_trace(run)

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


def test_d005_visualization_runs_lifetime_before_adaptation() -> None:
    data = build_d005_development_visualization(seed=18141, horizon=3)
    assert data.source_label.startswith("D-005")
    assert data.visibility.thermal == "CTRL + EVAL"
    assert data.visibility.charging_contact == "CTRL + EVAL"


def test_d006_adapter_preserves_completed_trace_fields() -> None:
    result = run_d006_probe((18141,), horizon=5, collect_trace=True)
    runs = result["results"]
    assert isinstance(runs, list)
    run = runs[0]
    assert isinstance(run, dict)
    predictive = run["predictive"]
    assert isinstance(predictive, dict)
    trace = predictive["trace"]
    assert isinstance(trace, tuple)

    data = adapt_d006_trace(predictive)

    assert len(data.frames) == 5
    for frame, entry in zip(data.frames, trace):
        assert frame.transition_index == entry.transition_index
        assert (frame.x, frame.y) == entry.position
        assert frame.heading == entry.heading
        assert frame.energy == entry.energy
        assert frame.thermal == entry.thermal
        assert frame.charging_contact == entry.charging_contact
        assert frame.action == entry.action.name
        assert frame.decision_mode == entry.controller_mode.value


def test_d006_visualization_uses_shared_post_hoc_renderer() -> None:
    data = build_d006_development_visualization(seed=18141, horizon=3)
    assert data.source_label.startswith("D-006")
    assert data.visibility.position_heading == "EVALUATOR ONLY"
    assert data.visibility.thermal == "CTRL + EVAL"


def test_d011_is_registered_and_builds_neutral_beacon_data() -> None:
    assert DEVELOPMENT_VISUALIZATION_ADAPTERS["d011"] is (
        build_d011_development_visualization
    )
    data = build_development_visualization("d011", seed=18141, horizon=40)

    assert data.source_label.startswith("D-011")
    assert len(data.frames) == 40
    assert data.probe_distance == pytest.approx(0.1)
    assert data.sensor_angle == pytest.approx(0.7853981633974483)
    assert data.energy_range.lower == pytest.approx(0.0)
    assert data.energy_range.upper == pytest.approx(1.0)
    assert data.energy_label == "ENERGY (NORMALIZED)"
    assert data.thermal_threshold == pytest.approx(0.60)
    assert data.visibility.energy == "CTRL + EVAL"
    assert all(
        None not in (frame.beacon_left, frame.beacon_forward, frame.beacon_right)
        for frame in data.frames
    )


def test_d012_is_registered_and_builds_one_declared_seed() -> None:
    assert DEVELOPMENT_VISUALIZATION_ADAPTERS["d012"] is (
        build_d012_development_visualization
    )
    data = build_development_visualization("d012", seed=18144, horizon=2)

    assert data.source_label.startswith("D-012")
    assert data.seed == 18144
    assert data.energy_range == DevelopmentVisualizationRange(0.0, 1.0)
    assert data.energy_label == "ENERGY (NORMALIZED)"


def test_d012_visualization_uses_shared_d011_controller_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected: list[str] = []
    original_act = d011.D011Controller.act

    def recording_act(
        controller: d011.D011Controller, observation: d011.D011Observation
    ) -> Action:
        action = original_act(controller, observation)
        selected.append(action.name)
        return action

    monkeypatch.setattr(d011.D011Controller, "act", recording_act)
    data = build_d012_development_visualization(seed=18144, horizon=20)

    assert selected == [frame.action for frame in data.frames]


def test_d012_visualization_does_not_call_exact_census_validator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        d012,
        "_validate_d012_development_seeds",
        lambda _seeds: (_ for _ in ()).throw(
            AssertionError(
                "single-seed visualization must not run the census validator"
            )
        ),
    )

    data = build_d012_development_visualization(seed=18144, horizon=1)
    assert data.seed == 18144


def test_d013_sources_are_registered_and_reference_has_no_learner() -> None:
    assert DEVELOPMENT_VISUALIZATION_ADAPTERS["d013-reference"] is (
        build_d013_reference_development_visualization
    )
    assert DEVELOPMENT_VISUALIZATION_ADAPTERS["d013"] is (
        build_d013_development_visualization
    )
    reference = build_development_visualization(
        "d013-reference", seed=18344, horizon=3
    )
    shadow = build_development_visualization("d013", seed=18344, horizon=3)

    assert reference.source_label == (
        "D-013 reference — unchanged D-011 controller, no shadow learner"
    )
    assert reference.consequence_predictions is None
    assert shadow.consequence_predictions is not None
    assert len(shadow.consequence_predictions) == len(shadow.frames) == 3
    reference_figure, reference_animation = build_development_visualization_figure(
        reference
    )
    assert len(reference_figure.axes) == 2
    assert not any(
        "SHADOW ONLY" in axis.get_title() for axis in reference_figure.axes
    )
    reference_animation.event_source.stop()
    plt.close(reference_figure)


@pytest.mark.parametrize("seed", (18344, 18345, 18346))
def test_d013_sources_accept_only_declared_development_seeds(seed: int) -> None:
    for source in ("d013-reference", "d013"):
        data = build_development_visualization(source, seed=seed, horizon=1)
        assert data.seed == seed


@pytest.mark.parametrize("seed", (18144, 50001))
def test_d013_sources_reject_non_d013_and_reserved_seeds(seed: int) -> None:
    for builder in (
        build_d013_reference_development_visualization,
        build_d013_development_visualization,
    ):
        with pytest.raises(ValueError):
            builder(seed=seed, horizon=1)


def test_d013_prediction_frames_are_aligned_and_first_prediction_is_zero() -> None:
    data = build_d013_development_visualization(seed=18344, horizon=5)
    predictions = data.consequence_predictions
    assert predictions is not None
    assert [item.transition_index for item in predictions] == [1, 2, 3, 4, 5]
    first = predictions[0]
    assert (
        first.predicted_delta_energy,
        first.predicted_delta_thermal,
        first.predicted_delta_charging_contact,
    ) == (0.0, 0.0, 0.0)


def test_d013_prediction_diagnostics_use_the_executed_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executed_actions: list[Action] = []
    original_observe = d013.D013ActionConsequencePredictor.observe_transition

    def recording_observe(
        predictor: d013.D013ActionConsequencePredictor,
        observation: d011.D011Observation,
        action: Action,
        next_observation: d011.D011Observation,
    ) -> d013.D013LearningUpdate:
        executed_actions.append(action)
        return original_observe(predictor, observation, action, next_observation)

    monkeypatch.setattr(
        d013.D013ActionConsequencePredictor,
        "observe_transition",
        recording_observe,
    )
    data = build_d013_development_visualization(seed=18344, horizon=8)

    assert executed_actions == [Action[frame.action] for frame in data.frames]


def test_d013_shadow_predictions_cannot_change_behavior(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reference = build_d013_reference_development_visualization(
        seed=18344, horizon=40
    )

    def absurd_predict(
        _predictor: d013.D013ActionConsequencePredictor,
        _observation: d011.D011Observation,
        _action: Action,
    ) -> d013.D013Prediction:
        return d013.D013Prediction(1e9, -1e9, 1e9)

    monkeypatch.setattr(d013.D013ActionConsequencePredictor, "predict", absurd_predict)
    adversarial = build_d013_development_visualization(seed=18344, horizon=40)

    assert [
        (
            frame.x,
            frame.y,
            frame.heading,
            frame.action,
            frame.decision_mode,
            frame.energy,
            frame.thermal,
            frame.charging_contact,
            frame.terminated,
            frame.truncated,
        )
        for frame in adversarial.frames
    ] == [
        (
            frame.x,
            frame.y,
            frame.heading,
            frame.action,
            frame.decision_mode,
            frame.energy,
            frame.thermal,
            frame.charging_contact,
            frame.terminated,
            frame.truncated,
        )
        for frame in reference.frames
    ]


def test_d013_reference_and_shadow_have_identical_per_frame_behavior() -> None:
    reference = build_d013_reference_development_visualization(
        seed=18344, horizon=120
    )
    shadow = build_d013_development_visualization(seed=18344, horizon=120)

    def physical_frame(frame: DevelopmentVisualizationFrame) -> tuple[object, ...]:
        return (
            frame.transition_index,
            frame.x,
            frame.y,
            frame.heading,
            frame.action,
            frame.decision_mode,
            frame.energy,
            frame.thermal,
            frame.charging_contact,
            frame.terminated,
            frame.truncated,
        )

    assert [physical_frame(frame) for frame in shadow.frames] == [
        physical_frame(frame) for frame in reference.frames
    ]


def test_d013_learner_state_is_not_added_to_d011_observation() -> None:
    assert {field.name for field in fields(d011.D011Observation)} == {
        "energy",
        "beacon",
        "thermal",
    }
    assert not any(
        "prediction" in field.name or "consequence" in field.name
        for field in fields(d011.D011Observation)
    )


def test_d013_renderer_shows_three_targets_and_only_playback_prefix() -> None:
    data = build_d013_development_visualization(seed=18344, horizon=5)
    figure, animation = build_development_visualization_figure(data)
    assert len(figure.axes) == 5
    rendered_text = "\n".join(
        [text.get_text() for axis in figure.axes for text in axis.texts]
        + [axis.get_title() for axis in figure.axes]
    )
    assert "SHADOW ONLY — ZERO BEHAVIOURAL INFLUENCE" in rendered_text
    assert "cumulative pre-update MAE through current transition" in rendered_text
    assert all(
        target in rendered_text
        for target in ("ENERGY Δ", "THERMAL Δ", "CONTACT Δ")
    )
    assert "learned MAE:" in rendered_text
    assert "zero-change baseline MAE:" in rendered_text
    assert "current predicted Δ:" in rendered_text
    assert "current observed Δ:" in rendered_text

    learner_lines = getattr(figure, "_aweform_learner_lines")
    assert all(len(line.get_xdata()) == 1 for pair in learner_lines for line in pair)
    player = getattr(figure, "_aweform_player")
    player.play()
    animation._func(0)
    assert all(len(line.get_xdata()) == 2 for pair in learner_lines for line in pair)
    assert all(max(line.get_xdata()) <= 2 for pair in learner_lines for line in pair)

    animation.event_source.stop()
    plt.close(figure)


def test_d015_sources_use_corrected_controller_and_matched_layouts() -> None:
    reference = build_d015_reference_development_visualization(
        seed=18350, horizon=5
    )
    shadow = build_d015_development_visualization(seed=18350, horizon=5)
    assert reference.source_label.startswith("D-015 reference")
    assert shadow.source_label.startswith("D-015 shadow learner")
    assert reference.consequence_predictions is None
    assert shadow.consequence_predictions is not None
    reference_figure, reference_animation = build_development_visualization_figure(
        reference
    )
    shadow_figure, shadow_animation = build_development_visualization_figure(shadow)
    assert len(reference_figure.axes) == 2
    assert len(shadow_figure.axes) == 5
    shadow_text = "\n".join(
        [text.get_text() for axis in shadow_figure.axes for text in axis.texts]
        + [axis.get_title() for axis in shadow_figure.axes]
    )
    assert "SHADOW ONLY — ZERO BEHAVIOURAL INFLUENCE" in shadow_text
    reference_animation.event_source.stop()
    shadow_animation.event_source.stop()
    plt.close(reference_figure)
    plt.close(shadow_figure)


def test_d015_reference_and_shadow_have_exact_same_physical_frames() -> None:
    reference = build_d015_reference_development_visualization(
        seed=18350, horizon=120
    )
    shadow = build_d015_development_visualization(seed=18350, horizon=120)
    assert [
        (
            frame.transition_index,
            frame.x,
            frame.y,
            frame.heading,
            frame.action,
            frame.decision_mode,
            frame.energy,
            frame.thermal,
            frame.charging_contact,
            frame.terminated,
            frame.truncated,
        )
        for frame in reference.frames
    ] == [
        (
            frame.transition_index,
            frame.x,
            frame.y,
            frame.heading,
            frame.action,
            frame.decision_mode,
            frame.energy,
            frame.thermal,
            frame.charging_contact,
            frame.terminated,
            frame.truncated,
        )
        for frame in shadow.frames
    ]


def test_d015_adversarial_predictions_cannot_change_physical_frames(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reference = build_d015_reference_development_visualization(
        seed=18350, horizon=40
    )

    def absurd_predict(
        _predictor: d013.D013ActionConsequencePredictor,
        _observation: d011.D011Observation,
        _action: Action,
    ) -> d013.D013Prediction:
        return d013.D013Prediction(1e9, -1e9, 1e9)

    monkeypatch.setattr(d013.D013ActionConsequencePredictor, "predict", absurd_predict)
    adversarial = build_d015_development_visualization(seed=18350, horizon=40)
    assert [
        (
            frame.x,
            frame.y,
            frame.heading,
            frame.action,
            frame.decision_mode,
            frame.energy,
            frame.thermal,
            frame.charging_contact,
            frame.terminated,
            frame.truncated,
        )
        for frame in adversarial.frames
    ] == [
        (
            frame.x,
            frame.y,
            frame.heading,
            frame.action,
            frame.decision_mode,
            frame.energy,
            frame.thermal,
            frame.charging_contact,
            frame.terminated,
            frame.truncated,
        )
        for frame in reference.frames
    ]


@pytest.mark.parametrize("seed", (18350, 18351, 18352))
def test_d015_visualization_sources_accept_only_d015_seeds(seed: int) -> None:
    assert build_d015_reference_development_visualization(
        seed=seed, horizon=1
    ).seed == seed
    assert build_d015_development_visualization(seed=seed, horizon=1).seed == seed


@pytest.mark.parametrize("seed", (18349, 50001))
def test_d015_visualization_sources_reject_non_d015_and_reserved_seeds(
    seed: int,
) -> None:
    for builder in (
        build_d015_reference_development_visualization,
        build_d015_development_visualization,
    ):
        with pytest.raises(ValueError):
            builder(seed=seed, horizon=1)


def test_d018_source_is_registered_and_builds_four_action_groups() -> None:
    assert DEVELOPMENT_VISUALIZATION_ADAPTERS["d018"] is (
        build_d018_development_visualization
    )
    for seed in (18359, 18360, 18361):
        data = build_d018_development_visualization(seed=seed, horizon=3)
        assert data.action_alternatives is not None
        assert len(data.action_alternatives) == 3
        for frame, alternatives in zip(
            data.frames, data.action_alternatives, strict=True
        ):
            assert len(alternatives) == 4
            assert all(
                isinstance(alternative, DevelopmentActionAlternative)
                for alternative in alternatives
            )
            assert sum(
                alternative.physically_executed for alternative in alternatives
            ) == 1
            executed = next(
                alternative
                for alternative in alternatives
                if alternative.physically_executed
            )
            assert executed.action == frame.action


@pytest.mark.parametrize("seed", (18358, 50001))
def test_d018_visualization_sources_reject_undeclared_and_reserved_seeds(
    seed: int,
) -> None:
    with pytest.raises(ValueError):
        build_d018_development_visualization(seed=seed, horizon=1)


def test_d018_visualization_preserves_real_trace_and_evaluator_rows() -> None:
    data = build_d018_development_visualization(seed=18361, horizon=40)
    audit = d018._run_seed(18361, horizon=40, counterfactual_audit=True)
    reference = d015._run_seed(18361, horizon=40)
    alternatives = data.action_alternatives
    assert alternatives is not None
    audit_rows = audit.summary["audit"]
    assert isinstance(audit_rows, dict)
    rows = audit_rows["rows"]
    assert isinstance(rows, list)
    assert len(rows) == len(data.frames) * 4
    rows_by_transition: dict[int, list[dict[str, object]]] = {}
    for row in rows:
        assert isinstance(row, dict)
        rows_by_transition.setdefault(row["transition_index"], []).append(row)

    for frame, record, group in zip(
        data.frames, audit.trace, alternatives, strict=True
    ):
        assert frame.transition_index == record["transition_index"]
        assert frame.action == record["action"]
        assert frame.decision_mode == record["mode_before"]
        assert (frame.x, frame.y) == tuple(record["position_after"])
        assert frame.heading == record["heading_after"]
        next_state = record["next_visible_state"]
        assert isinstance(next_state, dict)
        assert frame.energy == next_state["normalized_energy"]
        assert frame.thermal == next_state["normalized_thermal"]
        assert frame.charging_contact == next_state["charging_contact"]
        assert frame.beacon_left == next_state["beacon_left"]
        assert frame.beacon_forward == next_state["beacon_forward"]
        assert frame.beacon_right == next_state["beacon_right"]
        assert frame.terminated == record["terminated"]
        assert frame.truncated == record["truncated"]
        transition_rows = rows_by_transition[frame.transition_index]
        assert [alternative.action for alternative in group] == [
            row["candidate_action"] for row in transition_rows
        ]
        for alternative, row in zip(group, transition_rows, strict=True):
            assert alternative.physically_executed == (
                row["candidate_action"] == frame.action
            )
            assert alternative.prior_exact_support_count == row[
                "prior_exact_state_action_support_count"
            ]
            assert alternative.predicted_delta_energy == row["predicted_delta_energy"]
            assert alternative.actual_delta_energy == row["actual_delta_energy"]
            assert alternative.predicted_delta_thermal == row[
                "predicted_delta_thermal"
            ]
            assert alternative.actual_delta_thermal == row["actual_delta_thermal"]
            assert alternative.predicted_delta_charging_contact == row[
                "predicted_delta_charging_contact"
            ]
            assert alternative.actual_delta_charging_contact == row[
                "actual_delta_charging_contact"
            ]
    assert all(
        alternative.prior_exact_support_count == 0
        for alternative in alternatives[0]
    )
    assert audit.final_weights == reference["final_weights"]


def test_d018_alternative_panel_is_headless_and_controls_remain_display_only() -> None:
    data = build_d018_development_visualization(seed=18361, horizon=3)
    figure, animation = build_development_visualization_figure(data)
    assert len(figure.axes) == 3
    alternative_axis = getattr(figure, "_aweform_alternative_axis")
    assert alternative_axis is figure.axes[2]
    rendered_text = "\n".join(
        [text.get_text() for axis in figure.axes for text in axis.texts]
        + [axis.get_title() for axis in figure.axes]
    )
    assert "EVALUATOR-ONLY ACTION ALTERNATIVES" in rendered_text
    assert "D-014 CHOSE THE REAL ACTION BEFORE SCORING" in rendered_text
    assert "GHOST OUTCOMES DO NOT AFFECT BEHAVIOUR OR LEARNING" in rendered_text
    assert "D-013 PRE-UPDATE PREDICTION" in rendered_text
    assert "REAL / EXECUTED" in rendered_text
    assert "GHOST / UNEXECUTED" in rendered_text
    assert all(
        label in rendered_text
        for label in ("WAIT", "TURN_LEFT", "TURN_RIGHT", "MOVE_FORWARD")
    )

    player = getattr(figure, "_aweform_player")
    assert player.frame_index == 0
    event = KeyEvent("key_press_event", figure.canvas, key="right")
    figure.canvas.callbacks.process("key_press_event", event)
    assert player.frame_index == 1
    event = KeyEvent("key_press_event", figure.canvas, key="r")
    figure.canvas.callbacks.process("key_press_event", event)
    assert player.frame_index == 0

    animation.event_source.stop()
    plt.close(figure)


def test_d018_layout_makes_world_primary_and_keeps_annotations_outside_world() -> None:
    data = build_d018_development_visualization(seed=18361, horizon=3)
    figure, animation = build_development_visualization_figure(data)
    figure.canvas.draw()
    world_axis, diagnostic_axis, alternative_axis = figure.axes
    renderer = figure.canvas.get_renderer()
    world_position = world_axis.get_position()
    usable_width = figure.subplotpars.right - figure.subplotpars.left

    assert world_axis.get_aspect() == pytest.approx(1.0)
    assert world_position.width / usable_width >= 0.30
    assert diagnostic_axis.get_title(loc="left").startswith(
        "EVALUATOR DIAGNOSTICS"
    )
    assert alternative_axis.get_title(loc="left").startswith("ACTION ALTERNATIVES")
    assert len(figure.legends) == 1

    world_rectangle = world_axis.get_window_extent(renderer)
    world_legend = figure.legends[0].get_window_extent(renderer)
    assert not world_legend.overlaps(world_rectangle)
    assert not world_legend.overlaps(
        world_axis.xaxis.label.get_window_extent(renderer)
    )
    assert all(
        not world_legend.overlaps(tick_label.get_window_extent(renderer))
        for tick_label in world_axis.get_xticklabels()
        if tick_label.get_visible()
    )

    probe_caption = next(
        text
        for text in figure.texts
        if "directional probes = idealized beacon display" in text.get_text()
    )
    assert not probe_caption.get_window_extent(renderer).overlaps(world_rectangle)
    assert not probe_caption.get_window_extent(renderer).overlaps(
        world_axis.title.get_window_extent(renderer)
    )

    animation.event_source.stop()
    plt.close(figure)


def test_d018_axes_geometry_is_fixed_when_playback_labels_change() -> None:
    data = build_d018_development_visualization(seed=18361, horizon=120)
    figure, animation = build_development_visualization_figure(data)
    figure.canvas.draw()
    initial_positions = tuple(
        tuple(float(value) for value in axis.get_position().bounds)
        for axis in figure.axes
    )

    player = getattr(figure, "_aweform_player")
    for _ in range(99):
        player.step_forward()
    animation._func(0)
    figure.canvas.draw()
    later_positions = tuple(
        tuple(float(value) for value in axis.get_position().bounds)
        for axis in figure.axes
    )

    for later, initial in zip(later_positions, initial_positions, strict=True):
        assert later == pytest.approx(initial, abs=1.0e-12)
    animation.event_source.stop()
    plt.close(figure)


def test_renderer_plots_cumulative_mae_and_matches_displayed_statistics() -> None:
    data = _synthetic_consequence_data()
    figure, animation = build_development_visualization_figure(data)
    learner_lines = getattr(figure, "_aweform_learner_lines")
    learner_axes = getattr(figure, "_aweform_learner_axes")
    player = getattr(figure, "_aweform_player")

    player.step_forward()
    player.step_forward()
    animation._func(0)

    expected_learned = ((0.1, 0.2, 0.2), (0.001, 0.002, 0.002), (0.0, 0.0, 0.0))
    expected_baseline = (
        (0.1, 0.25, 0.23333333333333334),
        (0.001, 0.002, 0.002),
        (0.0, 0.0, 0.0),
    )
    for axis, (learned_line, baseline_line), learned, baseline in zip(
        learner_axes,
        learner_lines,
        expected_learned,
        expected_baseline,
        strict=True,
    ):
        assert tuple(learned_line.get_xdata()) == (1, 2, 3)
        assert tuple(baseline_line.get_xdata()) == (1, 2, 3)
        assert tuple(learned_line.get_ydata()) == pytest.approx(learned)
        assert tuple(baseline_line.get_ydata()) == pytest.approx(baseline)
        stats = next(
            text
            for text in axis.texts
            if text.get_text().startswith("learned MAE:")
        ).get_text().splitlines()
        displayed_learned = float(stats[0].split(": ", 1)[1])
        displayed_baseline = float(stats[1].split(": ", 1)[1])
        assert round(learned_line.get_ydata()[-1], 5) == displayed_learned
        assert round(baseline_line.get_ydata()[-1], 5) == displayed_baseline

    animation.event_source.stop()
    plt.close(figure)


def test_renderer_uses_independent_cumulative_mae_scales_without_one_floor() -> None:
    data = _synthetic_consequence_data()
    figure, animation = build_development_visualization_figure(data)
    learner_axes = getattr(figure, "_aweform_learner_axes")

    assert learner_axes[0].get_ylim() == pytest.approx((0.0, 0.275))
    assert learner_axes[1].get_ylim() == pytest.approx((0.0, 0.0022))
    assert learner_axes[1].get_ylim()[1] < 0.01
    assert learner_axes[2].get_ylim() == pytest.approx((0.0, 1.0e-6))

    animation.event_source.stop()
    plt.close(figure)


def test_consequence_diagnostics_validate_alignment_and_finite_values() -> None:
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
    prediction = DevelopmentConsequencePredictionFrame(
        transition_index=1,
        predicted_delta_energy=0.0,
        observed_delta_energy=0.1,
        predicted_delta_thermal=0.0,
        observed_delta_thermal=0.01,
        predicted_delta_charging_contact=0.0,
        observed_delta_charging_contact=-1.0,
    )
    with pytest.raises(ValueError, match="align"):
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
            consequence_predictions=(replace(prediction, transition_index=2),),
            visibility=DevelopmentVisualizationVisibility(
                position_heading="SYNTHETIC EVALUATOR",
                station_location="SYNTHETIC EVALUATOR",
                energy="SYNTHETIC ORGANISM",
                thermal="SYNTHETIC ORGANISM + EVALUATOR",
                charging_contact="SYNTHETIC ORGANISM + EVALUATOR",
                action_decision_mode="SYNTHETIC CONTROLLER STATE",
            ),
        )


def test_d011_adapter_actions_are_selected_by_d011_controller(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected: list[str] = []
    original_act = d011.D011Controller.act

    def recording_act(
        controller: d011.D011Controller, observation: d011.D011Observation
    ) -> Action:
        action = original_act(controller, observation)
        selected.append(action.name)
        return action

    monkeypatch.setattr(d011.D011Controller, "act", recording_act)
    data = build_d011_development_visualization(seed=18141, horizon=40)

    assert selected == [frame.action for frame in data.frames]


def test_d011_replay_matches_merged_probe_invariants() -> None:
    data = build_d011_development_visualization(seed=18141, horizon=80)
    result = d011.run_d011_probe((18141,), horizon=80)
    run = result["results"][0]
    assert isinstance(run, dict)
    action_counts = run["action_counts"]
    assert isinstance(action_counts, dict)

    assert Counter(frame.action for frame in data.frames) == action_counts
    assert data.frames[-1].energy == pytest.approx(run["final_normalized_energy"])
    assert data.frames[-1].thermal == pytest.approx(run["final_thermal_state"])


def test_d011_geometry_stays_outside_organism_observation() -> None:
    assert {field.name for field in fields(d011.D011Observation)} == {
        "energy",
        "beacon",
        "thermal",
    }
    data = build_d011_development_visualization(seed=18141, horizon=2)
    assert data.station_center == (0.5, 0.5)
    assert not hasattr(d011.D011Observation, "station_center")
    assert not hasattr(d011.D011Observation, "true_distance")
    assert isinstance(data.frames[0].x, float)
    assert isinstance(data.frames[0].heading, float)


@pytest.mark.parametrize("seed", (50001, 42, 18144))
def test_d011_rejects_reserved_and_non_d011_seeds(seed: int) -> None:
    with pytest.raises(ValueError):
        build_d011_development_visualization(seed=seed, horizon=1)


@pytest.mark.parametrize("seed", (18141, 50001))
def test_d012_rejects_non_d012_and_reserved_seeds(seed: int) -> None:
    with pytest.raises(ValueError):
        build_d012_development_visualization(seed=seed, horizon=1)


def test_d011_replay_does_not_read_d008_prediction_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline = build_d011_development_visualization(seed=18141, horizon=20)

    class ForbiddenPrediction:
        def __getattribute__(self, name: str) -> object:
            raise AssertionError(f"forbidden learner read: {name}")

    monkeypatch.setitem(sys.modules, "aweform.d008", ForbiddenPrediction())
    adversarial = build_d011_development_visualization(seed=18141, horizon=20)
    assert [frame.action for frame in adversarial.frames] == [
        frame.action for frame in baseline.frames
    ]


def test_shared_renderer_draws_beacons_and_preserves_non_beacon_sources() -> None:
    beacon_data = build_d011_development_visualization(seed=18141, horizon=3)
    beacon_figure, beacon_animation = build_development_visualization_figure(
        beacon_data
    )
    beacon_text = "\n".join(
        text.get_text() for axis in beacon_figure.axes for text in axis.texts
    )
    assert "BEACON L — CTRL + EVAL" in beacon_text
    assert "BEACON F — CTRL + EVAL" in beacon_text
    assert "BEACON R — CTRL + EVAL" in beacon_text
    assert "HOT DEPART = 0.60" in beacon_text
    assert "DEVELOPMENT / EVALUATOR VIEW" not in beacon_text
    assert "not literal RF beams" in beacon_text
    assert beacon_data.visibility.energy == "CTRL + EVAL"
    frame = beacon_data.frames[0]
    expected_signals = (
        frame.beacon_left,
        frame.beacon_forward,
        frame.beacon_right,
    )
    assert all(signal is not None for signal in expected_signals)
    beacon_fill_y_positions = (0.30 - 0.025, 0.20 - 0.025, 0.10 - 0.025)
    for y, signal in zip(beacon_fill_y_positions, expected_signals, strict=True):
        if signal is None:
            raise AssertionError("expected a beacon signal")
        matching = [
            patch
            for patch in beacon_figure.axes[1].patches
            if patch.get_y() == pytest.approx(y)
            and patch.get_facecolor() != pytest.approx((0.88, 0.88, 0.88, 1.0))
        ]
        assert len(matching) == 1
        assert matching[0].get_width() == pytest.approx(0.62 * signal)
        assert f"{signal:.3f}" in [
            text.get_text() for text in beacon_figure.axes[1].texts
        ]
    assert sum(
        line.get_label().endswith("directional probe")
        for line in beacon_figure.axes[0].lines
    ) == 3
    beacon_animation.event_source.stop()
    plt.close(beacon_figure)

    for builder in (
        build_d003_development_visualization,
        build_d005_development_visualization,
        build_d006_development_visualization,
    ):
        data = builder(seed=18141, horizon=1)
        assert all(
            frame.beacon_left is None
            and frame.beacon_forward is None
            and frame.beacon_right is None
            for frame in data.frames
        )
        figure, animation = build_development_visualization_figure(data)
        assert not any(
            "BEACON" in text.get_text()
            for axis in figure.axes
            for text in axis.texts
        )
        animation.event_source.stop()
        plt.close(figure)


def test_d006_renderer_does_not_rerun_after_adaptation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = build_d006_development_visualization(seed=18141, horizon=3)
    monkeypatch.setattr(
        "aweform.d006.run_d006_probe",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("rendering must not rerun D-006")
        ),
    )
    figure, animation = build_development_visualization_figure(data)
    player = getattr(figure, "_aweform_player")
    player.step_forward()
    animation._func(1)
    animation.event_source.stop()
    plt.close(figure)


def test_d011_normalized_energy_renders_as_normalized_gauge_and_text() -> None:
    data = build_d011_development_visualization(seed=18141, horizon=1)
    data = replace(
        data,
        frames=(replace(data.frames[0], energy=0.86),),
    )
    figure, animation = build_development_visualization_figure(data)
    diagnostic_axis = figure.axes[1]
    rendered_text = "\n".join(text.get_text() for text in diagnostic_axis.texts)

    assert "ENERGY (NORMALIZED) — CTRL + EVAL" in rendered_text
    assert "0.860 / 1" in rendered_text
    energy_fills = [
        patch
        for patch in diagnostic_axis.patches
        if patch.get_y() == pytest.approx(0.57 - 0.025)
        and patch.get_facecolor() != pytest.approx((0.88, 0.88, 0.88, 1.0))
    ]
    assert len(energy_fills) == 1
    assert energy_fills[0].get_width() == pytest.approx(0.62 * 0.86)

    animation.event_source.stop()
    plt.close(figure)


def test_renderer_keeps_provenance_header_once_and_separates_diagnostics() -> None:
    data = build_d011_development_visualization(seed=18141, horizon=1)
    figure, animation = build_development_visualization_figure(data)
    warning = "DEVELOPMENT / EVALUATOR VIEW"
    assert sum(warning in text.get_text() for text in figure.texts) == 1
    assert warning not in "\n".join(
        text.get_text() for text in figure.axes[1].texts
    )

    diagnostic_texts = {text.get_text(): text for text in figure.axes[1].texts}
    top_labels = (
        "transition: 1",
        "action: ",
        "decision mode: ",
        "charging contact: ",
        "status: ",
    )
    top_positions = [
        next(
            text.get_position()[1]
            for label, text in diagnostic_texts.items()
            if label.startswith(prefix)
        )
        for prefix in top_labels
    ]
    assert all(
        first - second >= 0.06
        for first, second in zip(top_positions, top_positions[1:])
    )
    metadata = next(
        text
        for text in figure.axes[1].texts
        if text.get_text().startswith("POSITION /")
    )
    footer = next(
        text for text in figure.axes[1].texts if text.get_text().startswith("SPACE ")
    )
    assert metadata.get_position()[1] - footer.get_position()[1] >= 0.20

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
        build_development_visualization("d999", seed=18141, horizon=1)


def test_d006_is_registered() -> None:
    data = build_development_visualization("d006", seed=18141, horizon=1)
    assert data.source_label.startswith("D-006")


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


def test_d020_visualization_is_seedless_and_keeps_seeded_title_semantics() -> None:
    d020 = build_d020_development_visualization()
    assert d020.seed is None
    figure, animation = build_development_visualization_figure(d020)
    title = figure._suptitle.get_text()  # type: ignore[union-attr]
    assert "seedless fixed-state" in title
    assert "seed None" not in title
    assert "seed 0" not in title
    animation.event_source.stop()
    plt.close(figure)

    seeded = build_d003_development_visualization(seed=18141, horizon=1)
    seeded_figure, seeded_animation = build_development_visualization_figure(seeded)
    seeded_title = seeded_figure._suptitle.get_text()  # type: ignore[union-attr]
    assert "seed 18141" in seeded_title
    assert "seedless fixed-state" not in seeded_title
    seeded_animation.event_source.stop()
    plt.close(seeded_figure)


def test_d020_visualization_replays_exact_frozen_mixed_action_trace() -> None:
    data = build_d020_development_visualization()

    assert len(data.frames) == 11
    assert [frame.action for frame in data.frames] == [
        "WAIT",
        "TURN_LEFT",
        "TURN_RIGHT",
        "MOVE_FORWARD",
        "MOVE_FORWARD",
        "MOVE_FORWARD",
        "WAIT",
        "MOVE_FORWARD",
        "MOVE_FORWARD",
        "MOVE_FORWARD",
        "MOVE_FORWARD",
    ]
    assert [frame.charging_contact for frame in data.frames] == [
        False,
        False,
        False,
        False,
        False,
        True,
        True,
        True,
        True,
        True,
        False,
    ]
    assert [frame.decision_mode for frame in data.frames] == [
        "EVALUATOR CHARGER: OFF",
        "EVALUATOR CHARGER: OFF",
        "EVALUATOR CHARGER: OFF",
        "EVALUATOR CHARGER: OFF",
        "EVALUATOR CHARGER: OFF",
        "EVALUATOR CHARGER: BULK",
        "EVALUATOR CHARGER: BULK",
        "EVALUATOR CHARGER: BULK",
        "EVALUATOR CHARGER: BULK",
        "EVALUATOR CHARGER: BULK",
        "EVALUATOR CHARGER: OFF",
    ]
    assert all(frame.terminated is False for frame in data.frames)
    assert all(frame.truncated is False for frame in data.frames)


def test_d020_visualization_preserves_boundary_and_physical_display_semantics() -> None:
    data = build_d020_development_visualization()

    assert data.energy_range == DevelopmentVisualizationRange(0.0, 1.0)
    assert data.energy_label == "BATTERY (NORMALIZED)"
    assert all(0.0 <= frame.energy <= 1.0 for frame in data.frames)
    assert data.frames[-1].energy == pytest.approx(0.4999868618618622, abs=2e-7)
    assert data.frames[-1].energy != pytest.approx(2663.9300000000017)
    assert data.thermal_range == DevelopmentVisualizationRange(0.0, 80.0)
    assert data.frames[-1].thermal == pytest.approx(23.001486780144614)
    assert data.thermal_threshold == 45.0
    assert data.thermal_threshold_label == "PREFERRED 45°C — EVALUATOR ONLY"
    assert all(
        None not in (frame.beacon_left, frame.beacon_forward, frame.beacon_right)
        and all(
            0.0 <= value <= 1.0
            for value in (frame.beacon_left, frame.beacon_forward, frame.beacon_right)
            if value is not None
        )
        for frame in data.frames
    )

    assert data.visibility.position_heading == "EVALUATOR ONLY"
    assert data.visibility.station_location == "EVALUATOR ONLY"
    assert data.visibility.energy == "ORGANISM-VISIBLE + EVALUATOR"
    assert data.visibility.charging_contact == "ORGANISM-VISIBLE + EVALUATOR"
    assert "EVALUATOR °C" in data.visibility.thermal
    assert "NORMALIZED OWN TEMPERATURE" in data.visibility.thermal
    assert data.visibility.action_decision_mode == "EVALUATOR ONLY — NO CONTROLLER"
    assert data.mode_display_label == "charger phase"


def test_d020_visualization_builds_headless_from_unchanged_neutral_trace() -> None:
    data = build_d020_development_visualization()
    original_frames = data.frames
    figure, animation = build_development_visualization_figure(data)

    assert figure.axes[0].get_title() == "2D EVALUATOR WORLD"
    assert figure.axes[1].get_title(loc="left") == "EVALUATOR DIAGNOSTICS"
    rendered_text = "\n".join(
        text.get_text() for axis in figure.axes for text in axis.texts
    )
    assert "ACTION / CHARGER PHASE: EVALUATOR ONLY — NO CONTROLLER" in rendered_text
    assert "PREFERRED 45°C — EVALUATOR ONLY" in rendered_text
    assert "BATTERY (NORMALIZED) — ORGANISM-VISIBLE + EVALUATOR" in rendered_text
    assert data.frames is original_frames
    animation.event_source.stop()
    plt.close(figure)


def test_d020_visualization_adapter_is_post_hoc_and_deterministic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def renderer_must_not_run(_data: object) -> object:
        raise AssertionError("D-020 adapter must finish before rendering")

    monkeypatch.setattr(
        development_visualizer_module,
        "build_development_visualization_figure",
        renderer_must_not_run,
    )
    first = build_d020_development_visualization()
    second = build_d020_development_visualization()
    assert first == second


@pytest.fixture(scope="module")
def d021_visualization_data() -> DevelopmentVisualizationData:
    return build_d021_development_visualization()


@pytest.fixture(scope="module")
def d021_lifetime_trace() -> tuple[D021TransitionTrace, ...]:
    return run_d021_lifetime_trace()


def test_d021_adapter_builds_fixed_canonical_lifetime(
    d021_visualization_data: DevelopmentVisualizationData,
) -> None:
    assert d021_visualization_data.seed == 18365
    assert d021_visualization_data.frames
    assert d021_visualization_data.frames[0].transition_index == 0
    assert d021_visualization_data.frames[0].action == "INITIAL"
    assert d021_visualization_data.frames[-1].transition_index == 70_000


def test_d021_adapter_is_deterministic() -> None:
    assert build_d021_development_visualization() == (
        build_d021_development_visualization()
    )


def test_d021_replay_is_deterministically_downsampled_and_event_preserving(
    d021_visualization_data: DevelopmentVisualizationData,
    d021_lifetime_trace: tuple[D021TransitionTrace, ...],
) -> None:
    assert 400 <= len(d021_visualization_data.frames) <= 900
    assert len(d021_visualization_data.frames) < 70_000
    event_steps = d021_replay_event_steps(d021_lifetime_trace)
    selected_steps = {
        frame.transition_index for frame in d021_visualization_data.frames
    }
    assert set(event_steps.values()) <= selected_steps
    assert selected_steps == {
        0,
        *select_d021_replay_indices(d021_lifetime_trace),
    }


def test_d021_replay_frame_count_and_event_steps_are_frozen(
    d021_visualization_data: DevelopmentVisualizationData,
    d021_lifetime_trace: tuple[D021TransitionTrace, ...],
) -> None:
    assert len(d021_visualization_data.frames) == 733
    assert d021_replay_event_steps(d021_lifetime_trace) == {
        "first_departure": 1,
        "first_charger_exit": 3,
        "first_seek_entry": 24570,
        "first_reacquisition": 24575,
        "first_charge_entry": 24576,
        "first_full_recharge": 52659,
        "first_redeparture": 52660,
        "final": 70000,
        "representative_away_contact": 478,
    }


def test_d021_nonconsecutive_sampled_transitions_remain_one_continuous_trajectory(
    d021_visualization_data: DevelopmentVisualizationData,
) -> None:
    frame_pairs = zip(
        d021_visualization_data.frames,
        d021_visualization_data.frames[1:],
    )
    sampled_gaps = [
        (previous, frame)
        for previous, frame in frame_pairs
        if frame.transition_index != previous.transition_index + 1
    ]

    assert sampled_gaps
    assert all(not frame.trajectory_break_before for _, frame in sampled_gaps)


def test_d021_consecutive_event_window_transitions_remain_connected(
    d021_visualization_data: DevelopmentVisualizationData,
    d021_lifetime_trace: tuple[D021TransitionTrace, ...],
) -> None:
    frame_by_step = {
        frame.transition_index: frame for frame in d021_visualization_data.frames
    }
    selected_event_window_pairs = [
        (frame_by_step[step], frame_by_step[step + 1])
        for event_step in d021_replay_event_steps(d021_lifetime_trace).values()
        for step in (event_step - 2, event_step - 1, event_step, event_step + 1)
        if step in frame_by_step and step + 1 in frame_by_step
    ]

    assert selected_event_window_pairs
    assert all(
        not frame.trajectory_break_before
        for _, frame in selected_event_window_pairs
    )


def test_trajectory_break_geometry_has_no_synthetic_intermediate_positions(
    d021_visualization_data: DevelopmentVisualizationData,
) -> None:
    frames = d021_visualization_data.frames
    x_values, y_values = development_visualizer_module._trajectory_line_coordinates(
        frames
    )

    assert len(x_values) == len(y_values)
    assert sum(math.isfinite(value) for value in x_values) == len(frames)
    assert sum(math.isfinite(value) for value in y_values) == len(frames)
    assert [
        (x, y)
        for x, y in zip(x_values, y_values, strict=True)
        if math.isfinite(x) and math.isfinite(y)
    ] == [(frame.x, frame.y) for frame in frames]
    assert all(
        math.isnan(x) and math.isnan(y)
        for x, y in zip(x_values, y_values, strict=True)
        if not math.isfinite(x)
    )

    break_index = 5
    replay_frames = tuple(
        replace(frame, trajectory_break_before=index == break_index)
        for index, frame in enumerate(frames[:12])
    )
    replay_data = replace(d021_visualization_data, frames=replay_frames)
    figure, animation = build_development_visualization_figure(replay_data)
    player = getattr(figure, "_aweform_player")
    for _ in range(break_index):
        player.step_forward()
    animation._func(0)
    trajectory_line = next(
        line for line in figure.axes[0].lines if line.get_label() == "trajectory"
    )
    rendered_x, rendered_y = trajectory_line.get_data()
    expected_x, expected_y = (
        development_visualizer_module._trajectory_line_coordinates(
            replay_data.frames[: break_index + 1]
        )
    )
    assert len(rendered_x) == len(expected_x)
    assert len(rendered_y) == len(expected_y)
    for actual, expected in zip(
        rendered_x, expected_x, strict=True
    ):
        if math.isnan(expected):
            assert math.isnan(actual)
        else:
            assert actual == expected
    for actual, expected in zip(
        rendered_y, expected_y, strict=True
    ):
        if math.isnan(expected):
            assert math.isnan(actual)
        else:
            assert actual == expected
    animation.event_source.stop()
    plt.close(figure)


def test_historical_visualization_frames_default_to_continuous_trajectory() -> None:
    historical_data = (
        build_d003_development_visualization(seed=18141, horizon=4),
        build_d005_development_visualization(seed=18141, horizon=4),
        build_d006_development_visualization(seed=18141, horizon=4),
        build_d020_development_visualization(),
    )

    for data in historical_data:
        assert all(not frame.trajectory_break_before for frame in data.frames)
        x_values, y_values = development_visualizer_module._trajectory_line_coordinates(
            data.frames
        )
        assert all(math.isfinite(value) for value in (*x_values, *y_values))


def test_d021_replay_displays_modes_phases_and_valid_sensors(
    d021_visualization_data: DevelopmentVisualizationData,
) -> None:
    frames = d021_visualization_data.frames
    assert {frame.decision_mode for frame in frames} == {
        "AWAY",
        "SEEK",
        "CHARGE",
        "DEPART",
    }
    assert {frame.charger_phase for frame in frames} == {
        "OFF",
        "BULK",
        "TAPER_1",
        "TAPER_2",
        "STANDBY",
    }
    for frame in frames:
        assert frame.simulated_seconds == pytest.approx(
            frame.transition_index * 0.1
        )
        assert 0.0 <= frame.energy <= 1.0
        assert frame.thermal_normalized is not None
        assert 0.0 <= frame.thermal_normalized <= 1.0
        assert frame.thermal_absolute_c is not None
        assert frame.charging_contact_before is not None
        assert all(
            value is not None and 0.0 <= value <= 1.0
            for value in (
                frame.beacon_left,
                frame.beacon_forward,
                frame.beacon_right,
            )
        )


def test_d021_replay_preserves_reward_info_and_observation_boundary(
    d021_lifetime_trace: tuple[D021TransitionTrace, ...],
) -> None:
    for record in d021_lifetime_trace:
        assert len(record.observation) == 6
        assert record.reward == 0.0
        assert record.info == {}


def test_d021_replay_uses_evaluator_only_temperature_and_charger_display(
    d021_visualization_data: DevelopmentVisualizationData,
) -> None:
    assert d021_visualization_data.energy_range == DevelopmentVisualizationRange(
        0.0, 1.0
    )
    assert d021_visualization_data.thermal_range == DevelopmentVisualizationRange(
        0.0, 80.0
    )
    assert d021_visualization_data.thermal_threshold == 45.0
    assert d021_visualization_data.thermal_threshold_label == (
        "PREFERRED 45°C — EVALUATOR ONLY"
    )
    assert "EVALUATOR ABSOLUTE °C" in d021_visualization_data.visibility.thermal
    assert "CHARGER PHASE EVALUATOR ONLY" in (
        d021_visualization_data.visibility.action_decision_mode
    )


def test_d021_replay_builds_headless_from_unchanged_neutral_trace(
    d021_visualization_data: DevelopmentVisualizationData,
) -> None:
    original_frames = d021_visualization_data.frames
    figure, animation = build_development_visualization_figure(
        d021_visualization_data
    )
    assert len(figure.axes) == 2
    rendered_text = "\n".join(
        text.get_text() for axis in figure.axes for text in axis.texts
    )
    assert "controller mode: CHARGE" in rendered_text
    assert "charger phase: STANDBY" in rendered_text
    assert "PREFERRED 45°C — EVALUATOR ONLY" in rendered_text
    assert "norm /" in rendered_text
    assert "°C" in rendered_text
    assert d021_visualization_data.frames is original_frames
    animation.event_source.stop()
    plt.close(figure)


def test_d021_diagnostic_rows_do_not_overlap_at_default_figure_size(
    d021_visualization_data: DevelopmentVisualizationData,
) -> None:
    figure, animation = build_development_visualization_figure(
        d021_visualization_data
    )
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    diagnostic_texts = getattr(figure, "_aweform_diagnostic_texts")
    boxes = [text.get_window_extent(renderer) for text in diagnostic_texts]

    assert all(
        not first.overlaps(second)
        for index, first in enumerate(boxes)
        for second in boxes[index + 1 :]
    )
    assert diagnostic_texts[4].get_text().startswith("status: ")
    assert diagnostic_texts[5].get_text().startswith("charger phase: ")
    assert diagnostic_texts[4].get_position()[1] > diagnostic_texts[5].get_position()[1]
    animation.event_source.stop()
    plt.close(figure)


def test_d023_adapter_is_registered_and_enforces_exact_horizon_and_seed_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert DEVELOPMENT_VISUALIZATION_ADAPTERS["d023"] is (
        build_d023_development_visualization
    )
    assert d023.D023_HORIZON == 210_000
    assert build_d023_development_visualization.__kwdefaults__["horizon"] == 210_000

    with pytest.raises(ValueError, match="210,000"):
        build_d023_development_visualization(seed=18365, horizon=1)
    for seed in (18364, 50001):
        with pytest.raises(ValueError):
            build_d023_development_visualization(seed=seed, horizon=210_000)

    calls: list[tuple[int, int, int]] = []
    sentinel = object()

    def fake_run_seed(
        seed: int, *, horizon: int, trace: list[object]
    ) -> dict[str, object]:
        calls.append((seed, horizon, len(trace)))
        trace.extend([sentinel] * horizon)
        return {}

    adapted = _synthetic_consequence_data()
    adapted_calls: list[tuple[int, int]] = []

    def fake_adapt(
        trace: tuple[object, ...], *, seed: int
    ) -> DevelopmentVisualizationData:
        adapted_calls.append((len(trace), seed))
        return adapted

    monkeypatch.setattr(d021, "_run_seed", fake_run_seed)
    monkeypatch.setattr(development_visualizer_module, "adapt_d023_trace", fake_adapt)
    result = build_d023_development_visualization(seed=18366, horizon=210_000)

    assert result is adapted
    assert calls == [(18366, 210_000, 0)]
    assert adapted_calls == [(210_000, 18366)]
