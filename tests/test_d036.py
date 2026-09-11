"""Focused tests for the D-036 evaluator-only shadow audit."""

from __future__ import annotations

import numpy as np
import pytest

from aweform import d036


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


def test_d036_features_are_flattened_visible_history_and_one_hot_action() -> None:
    data = _data()
    with pytest.raises(ValueError, match="unavailable"):
        d036._feature_matrix(data, 4, np.asarray([2]))
    features = d036._feature_matrix(data, 4, np.asarray([3]))
    assert features.shape == (1, 40)
    assert features[0, :6].tolist() == pytest.approx(data.visible_before[0].tolist())
    assert features[0, 6:10].tolist() == [1.0, 0.0, 0.0, 0.0]
    assert features[0, -4:].tolist() == [0.0, 0.0, 0.0, 1.0]


def test_d036_targets_retain_unavailable_prefix_and_null_status() -> None:
    data = _data(6)
    target = d036._target_data(data, history=4, horizon=2)
    assert target.status_counts["available"] == 1
    assert target.status_counts["null_lifetime_boundary"] == 2
    assert target.indices.tolist() == [3]


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
