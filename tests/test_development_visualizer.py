"""Focused tests for the canonical post-hoc development visualizer."""

import sys
from collections import Counter
from dataclasses import fields, replace

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest
from matplotlib.backend_bases import KeyEvent

from aweform import d011, d012, d013
from aweform.d003 import run_d003_probe
from aweform.d005 import run_d005_probe
from aweform.d006 import run_d006_probe
from aweform.development_visualizer import (
    DEVELOPMENT_VISUALIZATION_ADAPTERS,
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
    build_development_visualization,
    build_development_visualization_figure,
)
from aweform.env import Action


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
        if patch.get_y() == pytest.approx(0.61 - 0.025)
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
