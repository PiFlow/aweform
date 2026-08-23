from __future__ import annotations

import copy
from dataclasses import replace

import matplotlib.pyplot as plt
import pytest

import aweform.exp003_trend_visualizer as visualizer
import aweform.exp003_visualizer as existing_visualizer
from aweform import (
    Action,
    BeaconObservation,
    EXP003ControllerDecision,
    EXP003ControllerStep,
    EXP003EpisodeRecord,
    EXP003EvaluatorInitialState,
    EXP003EvaluatorStep,
    EXP003Mode,
    EXP003SeekTrigger,
    EXP003StationConfig,
    EXP003StationTrendComparison,
    EXP003TransitionRecord,
    StationObservation,
    build_exp003_trend_visualization_figure,
    build_exp003_trend_visualization_frames,
    run_exp003_development_comparison,
    run_exp003_station_trend_comparison,
)
from aweform.exp003_runner import summarize_exp003_episode


def _observation(
    energy: float,
    beacon: tuple[float, float, float],
) -> StationObservation:
    return StationObservation(
        energy=energy,
        beacon=BeaconObservation(*beacon, charging_contact=False),
    )


def _transition(
    step: int,
    observation: StationObservation,
    decision: EXP003ControllerDecision,
    *,
    mode_before: EXP003Mode,
    mode_after: EXP003Mode,
    truncated: bool = False,
) -> EXP003TransitionRecord:
    return EXP003TransitionRecord(
        controller_visible=EXP003ControllerStep(observation, decision),
        privileged_evaluator=EXP003EvaluatorStep(
            step_index=step,
            action=Action.WAIT,
            position_before=(0.8 - (step - 1) * 0.05, 0.5),
            position_after=(0.8 - step * 0.05, 0.5),
            heading=0.0,
            actual_energy_before=5.0,
            actual_energy_after=4.9,
            harvested_energy=0.0,
            basal_cost=0.1,
            action_cost=0.0,
            charging_contact_before=False,
            charging_contact_after=False,
            controller_mode_before_action=mode_before,
            controller_mode=mode_after,
            terminated=False,
            truncated=truncated,
        ),
    )


def _episode(
    transitions: tuple[EXP003TransitionRecord, ...],
) -> EXP003EpisodeRecord:
    return EXP003EpisodeRecord(
        environment_seed=18031,
        initial_state=EXP003EvaluatorInitialState(
            position=(0.8, 0.5),
            heading=0.0,
            actual_energy=5.0,
            station_center=(0.5, 0.5),
        ),
        transitions=transitions,
    )


def _synthetic_comparison() -> EXP003StationTrendComparison:
    config = EXP003StationConfig(episode_horizon=2)
    historical = _episode(
        (
            _transition(
                1,
                _observation(0.49, (0.08, 0.08, 0.08)),
                EXP003ControllerDecision(EXP003SeekTrigger.HISTORICAL_ENERGY),
                mode_before=EXP003Mode.EXPLORE,
                mode_after=EXP003Mode.SEEK,
                truncated=True,
            ),
        )
    )
    trend = _episode(
        (
            _transition(
                1,
                _observation(0.60, (0.09, 0.09, 0.09)),
                EXP003ControllerDecision(),
                mode_before=EXP003Mode.EXPLORE,
                mode_after=EXP003Mode.EXPLORE,
            ),
            _transition(
                2,
                _observation(0.60, (0.07, 0.07, 0.07)),
                EXP003ControllerDecision(
                    seek_trigger=EXP003SeekTrigger.ANTICIPATORY_TREND,
                    anticipatory_current_max_beacon=0.07,
                    anticipatory_previous_max_beacon=0.09,
                ),
                mode_before=EXP003Mode.EXPLORE,
                mode_after=EXP003Mode.SEEK,
                truncated=True,
            ),
        )
    )
    return EXP003StationTrendComparison(
        development_seeds=(18031,),
        station_environment_config=config,
        station_b50_episodes=(historical,),
        station_b50_diagnostics=(summarize_exp003_episode(historical, config),),
        station_b50_trend_episodes=(trend,),
        station_b50_trend_diagnostics=(summarize_exp003_episode(trend, config),),
    )


def test_matched_visualizer_uses_same_seed_and_environment() -> None:
    config = EXP003StationConfig(episode_horizon=4)
    comparison = run_exp003_station_trend_comparison([18024], config)
    data = build_exp003_trend_visualization_frames(comparison, seed=18024)

    historical = comparison.station_b50_episodes[0]
    trend = comparison.station_b50_trend_episodes[0]
    assert data.seed == 18024
    assert historical.environment_seed == trend.environment_seed == data.seed
    assert historical.initial_state == trend.initial_state
    assert data.world_min == config.world_min
    assert data.world_max == config.world_max
    assert data.charging_radius == config.charging_radius


def test_trend_figure_has_exactly_two_left_right_policy_panels() -> None:
    comparison = _synthetic_comparison()
    figure, animation = build_exp003_trend_visualization_figure(comparison)

    assert len(figure.axes) == 2
    assert figure.axes[0].get_title().startswith("LEFT — STATION_B50")
    assert figure.axes[1].get_title().startswith("RIGHT — STATION_B50_TREND")
    assert "STATION_B50 vs STATION_B50_TREND" in figure._suptitle.get_text()
    assert "NOT CALIBRATION OR CONFIRMATORY EVIDENCE" in figure._suptitle.get_text()
    animation.event_source.stop()
    plt.close(figure)


def test_trend_figure_uses_configured_beacon_scale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configured_scale = 0.5
    comparison = replace(
        _synthetic_comparison(),
        station_environment_config=EXP003StationConfig(
            episode_horizon=2,
            beacon_scale=configured_scale,
        ),
    )
    seen_scales: list[float] = []

    def record_beacon_scale(distance: float, beacon_scale: float) -> float:
        seen_scales.append(beacon_scale)
        return 0.0

    monkeypatch.setattr(visualizer, "beacon_signal", record_beacon_scale)
    figure, animation = build_exp003_trend_visualization_figure(comparison)

    assert seen_scales
    assert set(seen_scales) == {configured_scale}
    animation.event_source.stop()
    plt.close(figure)


def test_trend_frame_uses_recorded_previous_and_current_beacon_maxima() -> None:
    comparison = _synthetic_comparison()
    data = build_exp003_trend_visualization_frames(comparison)
    first, anticipatory, terminal = data.trend_frames
    recorded_decision = comparison.station_b50_trend_episodes[0].transitions[
        1
    ].controller_visible.decision

    assert first.current_beacon_max == pytest.approx(0.09)
    assert first.previous_explore_beacon_max is None
    assert first.beacon_delta is None
    assert anticipatory.current_beacon_max == pytest.approx(0.07)
    assert anticipatory.previous_explore_beacon_max == pytest.approx(0.09)
    assert anticipatory.beacon_delta == pytest.approx(-0.02)
    assert anticipatory.seek_trigger is EXP003SeekTrigger.ANTICIPATORY_TREND
    assert (
        anticipatory.current_beacon_max
        == recorded_decision.anticipatory_current_max_beacon
    )
    assert (
        anticipatory.previous_explore_beacon_max
        == recorded_decision.anticipatory_previous_max_beacon
    )


def test_anticipatory_trigger_label_is_visible_on_recorded_decision() -> None:
    data = build_exp003_trend_visualization_frames(_synthetic_comparison())
    text = visualizer._format_frame(data.trend_frames[1], history_enabled=True)

    assert "SEEK trigger: ANTICIPATORY_TREND" in text


def test_historical_energy_trigger_and_no_inferred_history_are_visible() -> None:
    data = build_exp003_trend_visualization_frames(_synthetic_comparison())
    frame = data.historical_frames[0]
    text = visualizer._format_frame(frame, history_enabled=False)

    assert frame.previous_explore_beacon_max is None
    assert "previous beacon: n/a" in text
    assert "SEEK trigger: HISTORICAL_ENERGY" in text


def test_terminal_and_padded_frames_clear_stale_decision_diagnostics() -> None:
    data = build_exp003_trend_visualization_frames(_synthetic_comparison())
    historical_terminal = data.historical_frames[-1]
    trend_terminal = data.trend_frames[-1]
    historical_padded = visualizer._pad_frames(
        data.historical_frames, len(data.trend_frames)
    )[-1]

    for frame in (historical_terminal, trend_terminal, historical_padded):
        assert frame.next_action is None
        assert frame.controller_visible_energy is None
        assert frame.current_beacon_max is None
        assert frame.previous_explore_beacon_max is None
        assert frame.beacon_delta is None
        assert frame.seek_trigger is None
    assert historical_padded.is_padded


def test_station_distance_is_evaluator_only_and_recording_is_unchanged() -> None:
    comparison = _synthetic_comparison()
    before = copy.deepcopy(comparison)
    data = build_exp003_trend_visualization_frames(comparison)

    assert comparison == before
    assert data.trend_frames[0].station_distance is not None
    observation = comparison.station_b50_trend_episodes[0].transitions[
        0
    ].controller_visible.observation
    assert not hasattr(observation, "station_distance")
    assert "[EVALUATOR ONLY]" in visualizer._format_frame(
        data.trend_frames[0], history_enabled=True
    )


def test_existing_field_station_visualizer_remains_unchanged() -> None:
    comparison = run_exp003_development_comparison([18025])
    figure, animation = existing_visualizer.build_exp003_visualization_figure(
        comparison, seed=18025
    )

    assert len(figure.axes) == 2
    assert "FIELD_B50 vs STATION_B50" in figure._suptitle.get_text()
    animation.event_source.stop()
    plt.close(figure)


def test_visualizer_build_does_not_open_gui(monkeypatch: pytest.MonkeyPatch) -> None:
    comparison = _synthetic_comparison()

    def fail_show() -> None:
        raise AssertionError("visualizer tests must not open a GUI")

    monkeypatch.setattr(visualizer.plt, "show", fail_show)
    build_exp003_trend_visualization_frames(comparison)
    figure, animation = build_exp003_trend_visualization_figure(comparison)
    animation.event_source.stop()
    plt.close(figure)


def test_visualizer_cli_delegates_without_opening_gui(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    comparison = _synthetic_comparison()
    seen: list[int] = []
    monkeypatch.setattr(
        visualizer,
        "run_exp003_station_trend_comparison",
        lambda seeds: seen.extend(seeds) or comparison,
    )
    shown: list[int | None] = []
    monkeypatch.setattr(
        visualizer,
        "show_exp003_trend_visualization",
        lambda result, seed=None: shown.append(seed),
    )

    assert visualizer.main(["--seed", "18031"]) == 0
    assert seen == [18031]
    assert shown == [18031]
