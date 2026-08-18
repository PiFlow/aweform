from __future__ import annotations

import copy
from dataclasses import replace

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest

import aweform.exp002_runner as exp002_runner
import aweform.exp002_visualizer as visualizer
from aweform import FROZEN_EXP001_CALIBRATION_ENV_CONFIG
from aweform.exp001_runner import EXP001Condition
from aweform.exp002_protocol import EXP002BCandidate
from aweform.exp002_runner import (
    exp002_coverage_grid_for_episode,
    exp002_coverage_grid_states,
    run_exp002_development_batch,
    summarize_exp002_episode,
)


@pytest.fixture(scope="module")
def result():
    return run_exp002_development_batch(
        seeds=[18011],
        env_config=FROZEN_EXP001_CALIBRATION_ENV_CONFIG,
        candidate=EXP002BCandidate.B45,
    )


def test_cli_candidate_mapping_is_exact_and_uses_frozen_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_run(**kwargs: object) -> object:
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(visualizer, "run_exp002_development_batch", fake_run)
    monkeypatch.setattr(
        visualizer,
        "show_exp002_development_visualization",
        lambda *_args: None,
    )

    expected = {
        "B35": 0.35,
        "B40": 0.40,
        "B45": 0.45,
        "B50": 0.50,
    }
    for name, threshold in expected.items():
        assert visualizer.main(["--seed", "18012", "--candidate", name]) == 0
        assert captured["seeds"] == [18012]
        assert captured["env_config"] is FROZEN_EXP001_CALIBRATION_ENV_CONFIG
        candidate = captured["candidate"]
        assert isinstance(candidate, EXP002BCandidate)
        assert candidate.value == name
        assert candidate.enter_seek == threshold


@pytest.mark.parametrize("seed", [20001, 30001, 40001, 40200, 50001, 51000])
def test_cli_rejects_every_reserved_seed_before_environment_construction(
    monkeypatch: pytest.MonkeyPatch,
    seed: int,
) -> None:
    constructions = 0
    real_environment = exp002_runner.AweformEnv

    class SpyEnvironment(real_environment):
        def __init__(self, config: object) -> None:
            nonlocal constructions
            constructions += 1
            super().__init__(config)  # type: ignore[arg-type]

    monkeypatch.setattr(exp002_runner, "AweformEnv", SpyEnvironment)
    with pytest.raises(SystemExit):
        visualizer.main(["--seed", str(seed), "--candidate", "B35"])
    assert constructions == 0


def test_visualized_coverage_is_the_canonical_grid_and_matches_diagnostics(
    result: object,
) -> None:
    data = visualizer.build_exp002_visualization_frames(result, seed=18011)  # type: ignore[arg-type]
    records = visualizer.select_exp002_seed_records(result, seed=18011)  # type: ignore[arg-type]

    for condition_index, record in enumerate(records):
        states = exp002_coverage_grid_states(record)
        frames = data.frames[condition_index]
        for frame, grid in zip(frames[: len(states)], states):
            assert frame.visited_cells == grid.visited_cells
            assert frame.visited_cell_count == grid.visited_cell_count
            assert frame.coverage_fraction == grid.coverage_fraction
        canonical = exp002_coverage_grid_for_episode(record)
        diagnostic = data.diagnostics[condition_index]
        assert set(frames[len(states) - 1].visited_cells) == set(
            canonical.visited_cells
        )
        assert diagnostic.visited_cell_count == canonical.visited_cell_count
        assert diagnostic.remaining_cell_count == canonical.remaining_cell_count
        assert diagnostic.coverage_fraction == canonical.coverage_fraction


def test_visualization_consumes_no_rng(result: object) -> None:
    rng = np.random.default_rng(18013)
    state_before = copy.deepcopy(rng.bit_generator.state)
    visualizer.build_exp002_visualization_frames(result, seed=18011)  # type: ignore[arg-type]
    state_after = copy.deepcopy(rng.bit_generator.state)
    assert state_after == state_before


def test_b_source_distance_is_evaluator_only_and_a_c_energy_is_labeled(
    result: object,
) -> None:
    data = visualizer.build_exp002_visualization_frames(result, seed=18011)  # type: ignore[arg-type]
    b_frame = data.frames[1][0]
    b_episode = visualizer.select_exp002_seed_records(  # type: ignore[arg-type]
        result,
        seed=18011,
    )[1]
    assert b_frame.controller_visible_energy is not None
    assert not hasattr(b_frame, "nearest_source_distance")
    assert not hasattr(
        b_episode.transitions[0].controller_visible.observation,
        "nearest_source_distance_at_onset",
    )
    b_text = visualizer.format_exp002_diagnostic_text(
        b_frame,
        EXP001Condition.B,
        EXP002BCandidate.B45,
    )
    assert "nearest-source distance [EVALUATOR-ONLY]" in b_text
    assert "actual normalized energy: " in b_text
    attempts = data.diagnostics[1].seek_attempts
    assert attempts
    latest_attempt = attempts[-1]
    b_final = data.frames[1][-1]
    assert b_final.most_recent_seek_onset_energy == pytest.approx(
        latest_attempt.normalized_energy_at_onset
    )
    assert b_final.most_recent_seek_distance == pytest.approx(
        latest_attempt.nearest_source_distance_at_onset
    )
    assert b_final.most_recent_seek_reached_charge is latest_attempt.reached_charge
    for condition_index in (0, 2):
        text = visualizer.format_exp002_diagnostic_text(
            data.frames[condition_index][0],
            tuple(EXP001Condition)[condition_index],
            EXP002BCandidate.B45,
        )
        assert "[EVAL ONLY]" in text


def test_energy_visibility_rule_covers_live_final_padded_and_a_c_frames(
    result: object,
) -> None:
    data = visualizer.build_exp002_visualization_frames(  # type: ignore[arg-type]
        result,
        seed=18011,
    )
    records = visualizer.select_exp002_seed_records(  # type: ignore[arg-type]
        result,
        seed=18011,
    )
    b_record = records[1]
    live_b = data.frames[1][0]
    final_b = data.frames[1][len(b_record.transitions)]

    assert live_b.controller_visible_energy is not None
    assert visualizer.exp002_energy_visibility_label(
        live_b,
        EXP001Condition.B,
    ) == "CTRL + EVAL"
    assert "[CTRL + EVAL]" in visualizer.format_exp002_diagnostic_text(
        live_b,
        EXP001Condition.B,
        EXP002BCandidate.B45,
    )

    assert final_b.controller_visible_energy is None
    assert visualizer.exp002_energy_visibility_label(
        final_b,
        EXP001Condition.B,
    ) == "EVAL ONLY"
    assert "[EVAL ONLY]" in visualizer.format_exp002_diagnostic_text(
        final_b,
        EXP001Condition.B,
        EXP002BCandidate.B45,
    )

    episodes = list(result.episodes)  # type: ignore[union-attr]
    diagnostics = list(result.diagnostics)  # type: ignore[union-attr]
    first_b_transition = b_record.transitions[0]
    terminal_evaluator = replace(
        first_b_transition.privileged_evaluator,
        terminated=True,
        truncated=False,
    )
    short_b = replace(
        b_record,
        transitions=(
            replace(
                first_b_transition,
                privileged_evaluator=terminal_evaluator,
            ),
        ),
    )
    episodes[1] = short_b
    diagnostics[1] = summarize_exp002_episode(short_b)
    padded_result = replace(
        result,  # type: ignore[arg-type]
        episodes=tuple(episodes),
        diagnostics=tuple(diagnostics),
    )
    padded_data = visualizer.build_exp002_visualization_frames(
        padded_result,
        seed=18011,
    )
    padded_b = padded_data.frames[1][-1]
    assert padded_b.is_padded
    assert padded_b.controller_visible_energy is None
    assert visualizer.exp002_energy_visibility_label(
        padded_b,
        EXP001Condition.B,
    ) == "EVAL ONLY"

    assert visualizer.exp002_energy_visibility_label(
        data.frames[0][0],
        EXP001Condition.A,
    ) == "EVAL ONLY"
    assert visualizer.exp002_energy_visibility_label(
        data.frames[2][0],
        EXP001Condition.C,
    ) == "EVAL ONLY"


def test_energy_bar_uses_the_same_visibility_rule_as_text(
    result: object,
) -> None:
    data = visualizer.build_exp002_visualization_frames(  # type: ignore[arg-type]
        result,
        seed=18011,
    )
    records = visualizer.select_exp002_seed_records(  # type: ignore[arg-type]
        result,
        seed=18011,
    )
    figure, animation = visualizer.build_exp002_visualization_figure(  # type: ignore[arg-type]
        result,
        seed=18011,
    )
    b_energy_label = next(
        text for text in figure.axes[1].texts if text.get_rotation() == 90
    )
    live_b = data.frames[1][0]
    assert b_energy_label.get_text() == visualizer.exp002_energy_visibility_label(
        live_b,
        EXP001Condition.B,
    )
    final_index = len(records[1].transitions)
    animation._func(final_index)
    assert b_energy_label.get_text() == visualizer.exp002_energy_visibility_label(
        data.frames[1][final_index],
        EXP001Condition.B,
    )
    assert b_energy_label.get_text() == "EVAL ONLY"
    animation._init_draw()
    animation.event_source.stop()
    plt.close(figure)


def test_figure_is_structural_three_panel_sanity_check(result: object) -> None:
    figure, animation = visualizer.build_exp002_visualization_figure(  # type: ignore[arg-type]
        result,
        seed=18011,
    )
    assert len(figure.axes) == 3
    assert figure._suptitle is not None
    assert "EXP-002 DEVELOPMENT VISUALIZATION" in figure._suptitle.get_text()
    assert "DESCRIPTIVE / SANITY CHECK ONLY" in figure._suptitle.get_text()
    assert "NOT CALIBRATION OR CONFIRMATORY EVIDENCE" in (
        figure._suptitle.get_text()
    )
    for axis in figure.axes:
        assert any(
            collection.get_offsets().shape == (1024, 2)
            for collection in axis.collections
        )
    assert "B45" in figure.axes[1].get_title()
    animation._init_draw()
    animation.event_source.stop()
    plt.close(figure)
