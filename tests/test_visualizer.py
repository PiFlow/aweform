from dataclasses import replace

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest

from aweform import (
    AweformEnvConfig,
    Condition,
    ControllerMode,
    HomeostaticConfig,
    build_visualization_figure,
    build_visualization_frames,
    run_development_batch,
    select_seed_records,
)


def _result(*seeds: int, resource_count: int = 1):
    return run_development_batch(
        seeds=seeds,
        env_config=AweformEnvConfig(
            episode_horizon=4,
            resource_count=resource_count,
        ),
        homeostatic_config=HomeostaticConfig(),
        masked_energy=0.2,
        git_sha="test-sha",
    )


def test_select_seed_records_returns_ordered_a_b_c() -> None:
    result = _result(701)

    records = select_seed_records(result, seed=701)

    assert [record.trajectory.condition for record in records] == list(Condition)
    assert [record.trajectory.environment_seed for record in records] == [701] * 3


def test_select_seed_records_rejects_ambiguous_or_missing_seed() -> None:
    result = _result(701, 702)

    with pytest.raises(ValueError, match="seed must be specified"):
        select_seed_records(result)
    with pytest.raises(ValueError, match="missing conditions"):
        select_seed_records(replace(result, episodes=()), seed=701)


def test_frames_include_initial_state_and_pad_shorter_episodes() -> None:
    result = _result(701)
    first_episode = result.episodes[0]
    short_trajectory = replace(
        first_episode.trajectory,
        transitions=first_episode.trajectory.transitions[:1],
    )
    short_episode = replace(first_episode, trajectory=short_trajectory)
    result = replace(result, episodes=(short_episode, *result.episodes[1:]))

    data = build_visualization_frames(result, seed=701)

    assert len(data.frames) == 3
    assert all(len(frames) == 5 for frames in data.frames)
    initial = data.frames[0][0]
    assert initial.step_index == 0
    assert initial.path == (
        (
            first_episode.trajectory.initial_state.x,
            first_episode.trajectory.initial_state.y,
        ),
    )
    assert initial.terminal_status == "running"
    assert len(data.frames[0][1].path) == 2
    assert data.frames[0][2] == data.frames[0][1]
    assert len(data.frames[1][2].path) == 3
    assert data.frames[1][2].step_index == 2


def test_frame_zero_uses_pre_action_controller_mode() -> None:
    data = build_visualization_frames(_result(701), seed=701)

    assert data.frames[0][0].mode is None
    assert data.frames[1][0].mode is ControllerMode.EXPLORE
    assert data.frames[2][0].mode is ControllerMode.EXPLORE
    assert data.frames[2][1].mode is ControllerMode.SEEK_RESOURCE


def test_visualizer_reads_privileged_trajectory_state_separately_from_observation() -> (
    None
):
    result = _result(701)
    record = result.episodes[0]
    data = build_visualization_frames(result, seed=701)

    assert len(record.trajectory.transitions[0].observation) == 4
    assert (data.frames[0][0].x, data.frames[0][0].y) == (
        record.trajectory.initial_state.x,
        record.trajectory.initial_state.y,
    )
    assert data.source_positions == record.trajectory.initial_state.source_positions


def test_multi_source_visualizer_data_and_markers_are_shared_across_panels() -> None:
    result = _result(701, resource_count=3)
    data = build_visualization_frames(result, seed=701)

    assert len(data.source_positions) == 3
    figure, animation = build_visualization_figure(result, seed=701)
    for axis in figure.axes:
        source_lines = [line for line in axis.lines if line.get_marker() == "*"]
        assert len(source_lines) == 1
        assert tuple(zip(source_lines[0].get_xdata(), source_lines[0].get_ydata())) == (
            data.source_positions
        )
    animation._init_draw()
    animation.event_source.stop()
    plt.close(figure)


def test_figure_has_three_condition_panels() -> None:
    result = _result(701)

    figure, animation = build_visualization_figure(result, seed=701)

    assert len(figure.axes) == 3
    assert all(
        condition.value in axis.get_title()
        for condition, axis in zip(Condition, figure.axes)
    )
    animation._init_draw()
    animation.event_source.stop()
    plt.close(figure)
