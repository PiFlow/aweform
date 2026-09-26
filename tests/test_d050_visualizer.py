"""Focused headless checks for the read-only D-050 visualizer."""

from __future__ import annotations

import hashlib
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest
from matplotlib.backend_bases import KeyEvent

from aweform.development_visualizer import (
    D050_ARTIFACT_BYTES,
    D050_ARTIFACT_PATH,
    D050_ARTIFACT_SHA256,
    build_d050_overview_figure,
    build_development_visualization_pair_figure,
    load_d050_visualization_pairs,
    select_d050_disagreements,
)


def test_d050_loader_verifies_the_committed_artifact_and_exact_matrix() -> None:
    artifact_bytes = D050_ARTIFACT_PATH.read_bytes()
    assert len(artifact_bytes) == D050_ARTIFACT_BYTES
    assert hashlib.sha256(artifact_bytes).hexdigest() == D050_ARTIFACT_SHA256

    pairs = load_d050_visualization_pairs()
    assert len(pairs) == 96
    assert pairs[0].baseline_label.startswith("BASELINE")
    assert pairs[0].smooth_label.startswith("SMOOTH")
    assert pairs[0].baseline.world_min == pairs[0].smooth.world_min
    assert pairs[0].baseline.world_max == pairs[0].smooth.world_max


def test_d050_pairs_preserve_starts_and_derive_sixteen_disagreements() -> None:
    pairs = load_d050_visualization_pairs()
    assert all(
        (
            pair.baseline.frames[0].x,
            pair.baseline.frames[0].y,
            pair.baseline.frames[0].heading,
        )
        == (
            pair.smooth.frames[0].x,
            pair.smooth.frames[0].y,
            pair.smooth.frames[0].heading,
        )
        for pair in pairs
    )

    disagreements = select_d050_disagreements(pairs)
    assert len(disagreements) == 16
    assert all(
        pair.baseline_outcome == "RETURN_HORIZON_CENSORED"
        and pair.smooth_outcome == "DOCKED_AND_CHARGING"
        for pair in disagreements
    )


def test_d050_pair_replay_is_synchronized_and_freezes_short_arm_display_only() -> None:
    pair = load_d050_visualization_pairs()[0]
    original_smooth_frames = pair.smooth.frames
    figure, animation = build_development_visualization_pair_figure(pair, interval_ms=1)
    player = getattr(figure, "_aweform_pair_player")
    diagnostic_texts = getattr(figure, "_aweform_pair_diagnostic_texts")

    assert player.frame_count == max(
        len(pair.baseline.frames), len(pair.smooth.frames)
    )
    assert len(figure.axes) == 4
    assert figure.axes[0].get_xlim() == figure.axes[1].get_xlim()
    assert figure.axes[0].get_ylim() == figure.axes[1].get_ylim()

    while player.frame_index < player.frame_count - 1:
        player.step_forward()
    animation._func(0)
    assert "FROZEN AFTER ARM TRACE COMPLETION" in diagnostic_texts[1].get_text()
    assert pair.smooth.frames == original_smooth_frames

    player.restart()
    figure.canvas.callbacks.process(
        "key_press_event", KeyEvent("key_press_event", figure.canvas, key="right")
    )
    assert player.frame_index == 1
    figure.canvas.callbacks.process(
        "key_press_event", KeyEvent("key_press_event", figure.canvas, key="r")
    )
    assert player.frame_index == 0
    animation.event_source.stop()
    plt.close(figure)


def test_d050_overview_and_disagreement_figures_construct_headlessly() -> None:
    pairs = load_d050_visualization_pairs()
    disagreements = select_d050_disagreements(pairs)
    overview = build_d050_overview_figure(
        pairs,
        title="ALL 96 PAIRED HOMING CASES",
    )
    focused = build_d050_overview_figure(
        disagreements,
        title="16 BASELINE-CENSORED / SMOOTH-DOCKED DISAGREEMENTS",
    )
    assert len(overview.axes) == 96
    assert len(focused.axes) == 16
    overview.canvas.draw()
    focused.canvas.draw()
    plt.close(overview)
    plt.close(focused)


def test_d050_artifact_integrity_mismatch_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "tampered.json"
    path.write_bytes(D050_ARTIFACT_PATH.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="artifact integrity mismatch"):
        load_d050_visualization_pairs(path)
