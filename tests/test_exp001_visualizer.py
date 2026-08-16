from __future__ import annotations

from dataclasses import replace

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest

import aweform.exp001_visualizer as visualizer
from aweform import (
    Action,
    AweformEnvConfig,
    EXP001Condition,
    EXP001DevelopmentConfig,
    EXP001Mode,
    ExternalObservation,
    InteroceptiveObservation,
    build_exp001_visualization_figure,
    build_exp001_visualization_frames,
    format_exp001_diagnostic_text,
    run_exp001_development_batch,
    select_exp001_seed_records,
)


def _result(seed: int = 701, episode_horizon: int = 4):
    return run_exp001_development_batch(
        seeds=[seed],
        env_config=AweformEnvConfig(episode_horizon=episode_horizon),
        development_config=EXP001DevelopmentConfig(
            resource_contact_threshold=0.8,
            blind_explore_duration=3,
            blind_charge_duration=2,
        ),
    )


def test_select_exp001_seed_records_returns_ordered_a_b_c() -> None:
    result = _result()

    records = select_exp001_seed_records(result, seed=701)

    assert [record.condition for record in records] == list(EXP001Condition)
    assert [record.environment_seed for record in records] == [701] * 3


def test_matched_source_positions_are_required() -> None:
    result = _result()
    records = list(result.episodes)
    changed_state = replace(
        records[1].initial_state,
        source_positions=((0.25, 0.75),),
    )
    changed_episode = replace(records[1], initial_state=changed_state)
    changed_result = replace(
        result,
        episodes=(records[0], changed_episode, records[2]),
    )

    with pytest.raises(ValueError, match="source positions"):
        build_exp001_visualization_frames(changed_result, seed=701)


def test_frames_preserve_position_path_heading_and_recorded_decisions() -> None:
    result = _result()
    data = build_exp001_visualization_frames(result, seed=701)
    record = select_exp001_seed_records(result, seed=701)[0]
    first_transition = record.transitions[0].privileged_evaluator
    second_transition = record.transitions[1].privileged_evaluator

    initial = data.frames[0][0]
    after_first = data.frames[0][1]
    assert (initial.x, initial.y) == record.initial_state.position
    assert initial.heading == record.initial_state.heading
    assert initial.path == (record.initial_state.position,)
    assert initial.mode is first_transition.controller_mode
    assert initial.next_action is first_transition.action
    assert (after_first.x, after_first.y) == first_transition.position
    assert after_first.heading == first_transition.heading
    assert after_first.path == (
        record.initial_state.position,
        first_transition.position,
    )
    assert after_first.mode is second_transition.controller_mode
    assert after_first.next_action is second_transition.action


def test_energy_diagnostics_keep_a_c_blind_and_b_interoceptive() -> None:
    result = _result()
    data = build_exp001_visualization_frames(result, seed=701)

    a_frame = data.frames[0][0]
    b_frame = data.frames[1][0]
    c_frame = data.frames[2][0]
    b_observation = result.episodes[1].transitions[0].controller_visible.observation

    assert isinstance(a_frame.next_action, Action)
    assert a_frame.controller_visible_energy is None
    assert c_frame.controller_visible_energy is None
    assert isinstance(b_observation, InteroceptiveObservation)
    assert b_frame.controller_visible_energy == b_observation.energy
    assert "EVALUATOR ONLY" in format_exp001_diagnostic_text(
        a_frame, EXP001Condition.A
    )
    assert "EVALUATOR ONLY" in format_exp001_diagnostic_text(
        c_frame, EXP001Condition.C
    )
    assert "CONTROLLER + EVALUATOR" in format_exp001_diagnostic_text(
        b_frame, EXP001Condition.B
    )
    b_final_text = format_exp001_diagnostic_text(
        data.frames[1][-1], EXP001Condition.B
    )
    assert "EVALUATOR ONLY — no next controller observation" in b_final_text
    assert "MASKED" not in format_exp001_diagnostic_text(
        c_frame, EXP001Condition.C
    )


def test_shorter_completed_episode_is_padded_without_decisions() -> None:
    result = _result()
    first_episode = result.episodes[0]
    first_transition = first_episode.transitions[0]
    terminal_evaluator = replace(
        first_transition.privileged_evaluator,
        terminated=True,
        truncated=False,
    )
    terminal_transition = replace(
        first_transition,
        privileged_evaluator=terminal_evaluator,
    )
    short_episode = replace(
        first_episode,
        transitions=(terminal_transition,),
    )
    short_result = replace(
        result,
        episodes=(short_episode, *result.episodes[1:]),
    )

    data = build_exp001_visualization_frames(short_result, seed=701)

    assert len(data.frames[0]) == 5
    assert data.frames[0][0].terminal_status == "running"
    assert data.frames[0][1].terminal_status == "terminated"
    assert data.frames[0][2].is_padded
    assert data.frames[0][2].next_action is None
    assert data.frames[0][2].terminal_status == "terminated"


def test_building_data_does_not_rerun_or_mutate_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _result()
    original_episodes = result.episodes

    def fail_if_called(*args: object, **kwargs: object) -> object:
        raise AssertionError("visualizer must not rerun the EXP-001 runner")

    monkeypatch.setattr(visualizer, "run_exp001_development_batch", fail_if_called)
    build_exp001_visualization_frames(result, seed=701)

    assert result.episodes == original_episodes


def test_figure_has_three_exp001_panels_and_boundary_note() -> None:
    result = _result()

    figure, animation = build_exp001_visualization_figure(result, seed=701)

    assert len(figure.axes) == 3
    assert "A — stochastic exploration" in figure.axes[0].get_title()
    assert "B — interoceptive closed-loop" in figure.axes[1].get_title()
    assert "C — fixed-timer open-loop" in figure.axes[2].get_title()
    assert "EVALUATOR VIEW" in figure._suptitle.get_text()
    assert "not available to those controllers" in figure._suptitle.get_text()
    animation._init_draw()
    animation.event_source.stop()
    plt.close(figure)


def test_cli_requires_explicit_unfrozen_demo_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_run(**kwargs: object) -> object:
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(visualizer, "run_exp001_development_batch", fake_run)
    monkeypatch.setattr(
        visualizer,
        "show_exp001_development_visualization",
        lambda *_args: None,
    )

    assert visualizer.main(
        [
            "--seed",
            "42",
            "--resource-contact-threshold",
            "0.8",
            "--blind-explore-duration",
            "20",
            "--blind-charge-duration",
            "10",
            "--episode-horizon",
            "100",
        ]
    ) == 0
    assert captured["seeds"] == [42]
    assert captured["env_config"].episode_horizon == 100  # type: ignore[union-attr]
    assert captured["development_config"].resource_contact_threshold == 0.8  # type: ignore[union-attr]
    assert captured["development_config"].blind_explore_duration == 20  # type: ignore[union-attr]
    assert captured["development_config"].blind_charge_duration == 10  # type: ignore[union-attr]
    assert captured["development_config"].enter_seek == 0.35  # type: ignore[union-attr]
    assert captured["development_config"].recover == 0.85  # type: ignore[union-attr]


def test_exp001_modes_are_used_not_exp000_modes() -> None:
    result = _result()
    data = build_exp001_visualization_frames(result, seed=701)

    assert all(frame.mode in EXP001Mode for panel in data.frames for frame in panel)
    assert all(
        isinstance(frame, visualizer.EXP001VisualizationFrame)
        for panel in data.frames
        for frame in panel
    )
    assert all(
        isinstance(
            record.transitions[0].controller_visible.observation,
            ExternalObservation,
        )
        for record in (result.episodes[0], result.episodes[2])
    )


def test_mode_changing_decisions_align_mode_and_action_from_same_record() -> None:
    result = run_exp001_development_batch(
        seeds=[42],
        env_config=AweformEnvConfig(episode_horizon=100),
        development_config=EXP001DevelopmentConfig(
            resource_contact_threshold=0.8,
            blind_explore_duration=20,
            blind_charge_duration=10,
        ),
    )
    data = build_exp001_visualization_frames(result, seed=42)
    records = select_exp001_seed_records(result, seed=42)

    for panel_frames, record in zip(data.frames, records):
        for index, transition in enumerate(record.transitions):
            evaluator = transition.privileged_evaluator
            assert panel_frames[index].mode is evaluator.controller_mode
            assert panel_frames[index].next_action is evaluator.action
        assert panel_frames[-1].mode is (
            record.transitions[-1].privileged_evaluator.controller_mode
        )

    b_record = records[1]
    b_frames = data.frames[1]
    seek_index = next(
        index
        for index, transition in enumerate(b_record.transitions)
        if transition.privileged_evaluator.controller_mode
        is EXP001Mode.SEEK_RESOURCE
    )
    assert b_frames[seek_index].mode is (
        b_record.transitions[seek_index].privileged_evaluator.controller_mode
    )
    assert b_frames[seek_index].next_action is (
        b_record.transitions[seek_index].privileged_evaluator.action
    )

    recover_index = next(
        index
        for index, transition in enumerate(b_record.transitions)
        if index > 0
        and b_record.transitions[index - 1].privileged_evaluator.controller_mode
        is EXP001Mode.CHARGE
        and transition.privileged_evaluator.controller_mode is EXP001Mode.EXPLORE
    )
    assert b_frames[recover_index].mode is EXP001Mode.EXPLORE
    assert b_frames[recover_index].next_action is (
        b_record.transitions[recover_index].privileged_evaluator.action
    )

    c_record = records[2]
    c_frames = data.frames[2]
    c_seek_index = next(
        index
        for index, transition in enumerate(c_record.transitions)
        if transition.privileged_evaluator.controller_mode
        is EXP001Mode.SEEK_RESOURCE
    )
    assert c_frames[c_seek_index].mode is (
        c_record.transitions[c_seek_index].privileged_evaluator.controller_mode
    )
    assert c_frames[c_seek_index].next_action is (
        c_record.transitions[c_seek_index].privileged_evaluator.action
    )
