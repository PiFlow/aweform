from __future__ import annotations

from pathlib import Path

import pytest

from aweform import vis_d059


def _trace() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index in range(201):
        rows.append(
            {
                "transition": index,
                "events": ["RESET"]
                if index == 0
                else (["RETURN_ACTIVATED"] if index == 100 else []),
                "active_mode": "NORMAL" if index < 100 else "RETURN",
                "command_source": "PASS_THROUGH" if index < 100 else "BEACON",
                "symbolic_proposal": "FORWARD",
                "d050_mode": None,
                "x": 0.5,
                "y": 0.5,
                "heading": 0.0,
                "energy": 0.8 - index / 1000,
                "thermal": 0.2,
                "charging_contact": False,
                "charging_contact_before": False if index else None,
                "energy_after": 0.8 - index / 1000,
                "charging_contact_after": False,
                "simulated_seconds": index * 0.1,
                "cycle_index": 1 if index >= 100 else 0,
                "terminated": False,
                "truncated": index == 200,
                "boundary_scale": 0.5 if index == 101 else 1.0,
                "wall_interaction": index == 101,
            }
        )
    return rows


def test_allowlist_accepts_only_exact_tuples() -> None:
    for seed, substrate, arm in vis_d059.VIS_D059_TUPLES:
        vis_d059.validate_allowlisted_tuple(seed, substrate, arm)
    with pytest.raises(ValueError, match="not allowlisted"):
        vis_d059.validate_allowlisted_tuple(26052, "D045_1M", "C")
    with pytest.raises(ValueError, match="not allowlisted"):
        vis_d059.validate_allowlisted_tuple(26320, "D045_1M", "U")
    with pytest.raises(ValueError, match="not allowlisted"):
        vis_d059.validate_allowlisted_tuple(26052.0, "D045_1M", "U")  # type: ignore[arg-type]


def test_sampler_keeps_stride_and_return_window() -> None:
    indices = vis_d059.select_vis_d059_replay_indices(_trace())
    assert 0 in indices
    assert 100 in indices
    assert 150 in indices
    assert 200 in indices


def test_adapter_adds_wall_interaction_without_anatomy_claim() -> None:
    data = vis_d059.adapt_vis_d059_trace(
        _trace(), seed=26052, substrate="D045_1M", arm="U"
    )
    wall_frames = [frame for frame in data.frames if frame.transition_index == 101]
    assert wall_frames
    assert "WALL ANATOMY UNKNOWN" in str(wall_frames[0].event_label)
    assert data.energy_thresholds == ((0.20, "RETURN 20%"), (0.80, "RECOVERY 80%"))
    assert any(frame.cycle_index == 1 for frame in data.frames)


def test_candidate_label_and_html_warning_are_present_and_deterministic() -> None:
    data = vis_d059.adapt_vis_d059_trace(
        _trace(), seed=26051, substrate="D045_1M", arm="C"
    )
    assert all("D055 STALL-TURN CANDIDATE" in frame.action for frame in data.frames)
    first = vis_d059.build_vis_d059_html([data])
    second = vis_d059.build_vis_d059_html([data])
    assert first == second
    assert first.count(vis_d059.VIS_D059_WARNING) >= 2
    assert "Previous event" in first and "Next event" in first


def test_export_does_not_write_on_digest_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "must-not-exist.html"
    expected = {
        key: {
            "trajectory_digest_sha256": "expected",
            "final_causal_state_digest_sha256": "expected",
        }
        for key in vis_d059.VIS_D059_TUPLES
    }
    monkeypatch.setattr(vis_d059, "_accepted_digest_rows", lambda _path: expected)

    def fail_replay(*_args: object, **_kwargs: object) -> object:
        raise vis_d059.ReplayMismatchError(
            "trajectory digest mismatch for seed=26052, substrate=D045_1M, arm=U"
        )

    monkeypatch.setattr(vis_d059, "_replay_lifetime", fail_replay)
    with pytest.raises(vis_d059.ReplayMismatchError, match="seed=26052"):
        vis_d059.export_vis_d059_html(output_path=output)
    assert not output.exists()
