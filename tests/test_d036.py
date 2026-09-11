"""Focused tests for the D-036 evaluator-only shadow audit."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from aweform import d036
from aweform.d026 import D026Mode
from aweform.env import Action


def _data(length: int = 12) -> d036._TraceData:
    visible = np.asarray(
        [[0.4, 0.1, 0.2 + index * 0.01, 0.3, 0.0, 0.5] for index in range(length)]
    )
    actions = np.asarray([index % 4 for index in range(length)], dtype=np.int8)
    return d036._TraceData(
        seed=18468,
        trace_digest="digest",
        visible_before=visible,
        actions=actions,
        visible_after_forward=visible[:, 2] + 0.01,
        reacquisition=np.zeros(length, dtype=bool),
        eligible=np.ones(length, dtype=bool),
        terminated=False,
        truncated=False,
        visible_after=visible
        + np.asarray([0.0, 0.0, 0.01, 0.0, 0.0, 0.0]),
    )


def test_d036_freeze_and_seed_guards() -> None:
    assert d036.D036_DEFAULT_DEVELOPMENT_SEEDS == tuple(range(18468, 18488))
    assert d036.D036_HISTORY_LENGTHS == (1, 4, 8, 16)
    assert d036.D036_TARGET_HORIZONS == (64, 256, 1024)
    assert d036._validate_seeds(list(d036.D036_DEFAULT_DEVELOPMENT_SEEDS)) == (
        tuple(range(18468, 18488))
    )
    with pytest.raises(ValueError, match="exactly"):
        d036._validate_seeds([18468, 18469])
    with pytest.raises(ValueError, match="only the reused"):
        d036._validate_seed(18467)
    with pytest.raises(ValueError, match="exact clean"):
        d036.run_d036_audit(executed_commit_sha=None)


def test_d036_features_exclude_scored_action_and_keep_current_observation() -> None:
    data = _data()
    h1 = d036._feature_matrix(data, 1, np.asarray([3]))
    assert h1.shape == (1, 6)
    assert h1[0].tolist() == pytest.approx(data.visible_before[3].tolist())

    changed_actions = data.actions.copy()
    changed_actions[3] = (changed_actions[3] + 1) % len(Action)
    changed = d036._TraceData(
        seed=data.seed,
        trace_digest=data.trace_digest,
        visible_before=data.visible_before,
        actions=changed_actions,
        visible_after_forward=data.visible_after_forward,
        reacquisition=data.reacquisition,
        eligible=data.eligible,
        terminated=data.terminated,
        truncated=data.truncated,
    )
    np.testing.assert_allclose(d036._feature_matrix(changed, 1, np.asarray([3])), h1)

    with pytest.raises(ValueError, match="unavailable"):
        d036._feature_matrix(data, 4, np.asarray([2]))
    features = d036._feature_matrix(data, 4, np.asarray([4]))
    assert features.shape == (1, 46)
    assert features[0, :6].tolist() == pytest.approx(data.visible_before[4].tolist())
    expected_first_completed = data.visible_before[0].copy()
    expected_first_completed[2] = data.visible_after_forward[0]
    assert features[0, 6:12].tolist() == pytest.approx(
        expected_first_completed.tolist()
    )
    assert features[0, 12:16].tolist() == [1.0, 0.0, 0.0, 0.0]
    assert features[0, -4:].tolist() == [0.0, 0.0, 0.0, 1.0]
    changed_h4_actions = data.actions.copy()
    changed_h4_actions[4] = (changed_h4_actions[4] + 1) % len(Action)
    changed_h4 = d036._TraceData(
        seed=data.seed,
        trace_digest=data.trace_digest,
        visible_before=data.visible_before,
        actions=changed_h4_actions,
        visible_after_forward=data.visible_after_forward,
        reacquisition=data.reacquisition,
        eligible=data.eligible,
        terminated=data.terminated,
        truncated=data.truncated,
    )
    np.testing.assert_allclose(
        d036._feature_matrix(changed_h4, 4, np.asarray([4])), features
    )
    assert d036._feature_dimension(1) == 6
    assert d036._feature_dimension(4) == 46


def test_d036_eligibility_uses_only_pre_action_state() -> None:
    def row(*, mode_after: D026Mode, after_contact: bool) -> object:
        return SimpleNamespace(
            transition_index=0,
            mode_before=D026Mode.SEEK,
            mode_after=mode_after,
            action=Action.WAIT,
            observation_before=(0.4, 0.1, 0.2, 0.3, 0.0, 0.5),
            observation=(0.4, 0.1, 0.2, 0.3, float(after_contact), 0.5),
            telemetry=SimpleNamespace(
                charging_contact_before=False,
                charging_contact_after=after_contact,
                terminated=False,
                truncated=False,
            ),
        )

    baseline = d036._trace_data(
        18468, (row(mode_after=D026Mode.SEEK, after_contact=False),)
    )
    mode_changed = d036._trace_data(
        18468, (row(mode_after=D026Mode.CHARGE, after_contact=False),)
    )
    contact_changed = d036._trace_data(
        18468, (row(mode_after=D026Mode.SEEK, after_contact=True),)
    )

    assert baseline.eligible.tolist() == [True]
    assert mode_changed.eligible.tolist() == baseline.eligible.tolist()
    assert contact_changed.eligible.tolist() == baseline.eligible.tolist()


def test_d036_targets_retain_unavailable_prefix_and_null_status() -> None:
    data = _data(6)
    target = d036._target_data(data, history=4, horizon=2)
    assert target.status_counts["available"] == 1
    assert target.status_counts["null_lifetime_boundary"] == 1
    assert target.indices.tolist() == [4]

    longer_data = _data(7)
    target = d036._target_data(longer_data, history=4, horizon=2)
    assert target.status_counts["available"] == 2
    assert target.status_counts["null_lifetime_boundary"] == 1
    assert target.indices.tolist() == [4, 5]


def test_d036_matching_is_deterministic_and_excludes_anchor_indices() -> None:
    data = _data(12)
    matched = d036._matched_non_anchor_index(data, 4, 4, {4, 5})
    assert matched is not None
    assert matched not in {4, 5}
    assert matched == d036._matched_non_anchor_index(data, 4, 4, {4, 5})
    assert d036._matched_non_anchor_index(data, 4, 4, set(range(12))) is None


def test_d036_bridge_summary_reports_matched_nulls_and_per_seed_comparison() -> None:
    records: list[dict[str, object]] = [
        {
            "seed": 18468,
            "status": "anchor_available",
            "matched_non_anchor_status": "matched",
            "anchor_predicted_future_progress": -0.2,
            "matched_predicted_future_progress": 0.1,
            "anchor_predicted_failure_probability": 0.8,
            "matched_predicted_failure_probability": 0.2,
            "anchor_target_status": "available",
            "matched_target_status": "available",
        },
        {
            "seed": 18469,
            "status": "anchor_available",
            "matched_non_anchor_status": "matched",
            "anchor_predicted_future_progress": -0.1,
            "matched_predicted_future_progress": 0.0,
            "anchor_predicted_failure_probability": None,
            "matched_predicted_failure_probability": None,
            "anchor_target_status": "termination",
            "matched_target_status": "available",
        },
        {"seed": 18470, "status": "anchor_unavailable"},
    ]
    summary = d036._bridge_summary(records)
    assert summary["matching_rule"]
    availability = summary["availability"]
    assert availability["matched_non_anchor_available_count"] == 2
    assert availability["target_null_count"] == 1
    per_seed = summary["per_seed"]
    assert per_seed["18468"]["progress_comparison_count"] == 1
    pooled = summary["pooled"]
    assert pooled["matched_pair_count"] == 2
    assert pooled["high_risk_low_progress_comparison_count"] == 1
    assert pooled["bridge_coherence"] is True


def test_d036_metrics_define_nulls_for_unsupported_binary_metrics() -> None:
    actual = np.asarray([0.0, 0.0])
    probability = np.asarray([0.2, 0.3])
    metrics = d036._binary_metrics(actual, probability)
    assert metrics["brier_score"] == pytest.approx(0.065)
    assert metrics["balanced_accuracy"] is None
    assert metrics["auroc"] is None


def test_d036_ridge_fit_does_not_require_hidden_features() -> None:
    features = np.asarray([[1.0, 0.0], [1.0, 1.0]])
    xx = features.T @ features
    xy = features.T @ np.asarray([0.0, 1.0])
    coefficients = d036._fit_ridge(xx, xy)
    assert coefficients.shape == (2,)
