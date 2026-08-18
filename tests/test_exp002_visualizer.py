from __future__ import annotations

import copy

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
        assert "[EVALUATOR-ONLY]" in text


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
