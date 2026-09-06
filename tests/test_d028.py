"""Focused tests for the D-028 evaluator-only residual audit."""

from __future__ import annotations

import numpy as np
import pytest

from aweform import d027, d028
from aweform.env import Action
from aweform.exp003_seed_policy import validate_exp003_development_seeds


def _synthetic_rows(seed: int, quadratic: bool) -> d028._SeedRows:
    generator = np.random.default_rng(seed)
    values = generator.random((40, 6))
    values[:, 4] = np.arange(40, dtype=float) % 2.0
    features = (
        d028.quadratic_features(values) if quadratic else d028._linear_features(values)
    )
    assert isinstance(features, np.ndarray)
    coefficients = (
        np.arange(features.shape[1] * 6, dtype=float).reshape(features.shape[1], 6)
        / 100.0
    )
    targets = features @ coefficients
    return d028._SeedRows(
        seed=seed,
        current={action: values.copy() for action in Action},
        target={action: targets.copy() for action in Action},
        online={action: np.zeros_like(targets) for action in Action},
        quarters={action: np.arange(40, dtype=np.int8) % 4 for action in Action},
        boundary_codes={action: np.zeros(40, dtype=np.int8) for action in Action},
        contact_codes={
            action: np.asarray([0, 1, -1] * 13 + [0], dtype=np.int8)
            for action in Action
        },
    )


def test_d028_freeze_and_exact_seed_guard() -> None:
    assert d028.D028_HORIZON == 70_000
    assert d028.D028_DEFAULT_DEVELOPMENT_SEEDS == tuple(range(18388, 18408))
    assert d028.D028_LINEAR_FEATURE_DIMENSION == 7
    assert d028.D028_QUADRATIC_FEATURE_DIMENSION == 28
    assert validate_exp003_development_seeds(d028.D028_DEFAULT_DEVELOPMENT_SEEDS) == (
        d028.D028_DEFAULT_DEVELOPMENT_SEEDS
    )
    assert (
        d028._validate_d028_development_seeds(d028.D028_DEFAULT_DEVELOPMENT_SEEDS)
        == d028.D028_DEFAULT_DEVELOPMENT_SEEDS
    )
    with pytest.raises(ValueError, match="requires exactly"):
        d028._validate_d028_development_seeds((18388,))
    with pytest.raises(ValueError, match="reserved"):
        d028._validate_d028_development_seeds((50001, 50002))


def test_quadratic_basis_has_exact_frozen_order() -> None:
    values = (1.0, 2.0, 3.0, 4.0, 0.0, 5.0)
    basis = d028.quadratic_features(values)
    assert isinstance(basis, tuple)
    assert len(basis) == 28
    assert basis[:7] == (1.0, *values)
    assert basis[7:] == tuple(
        values[left] * values[right] for left in range(6) for right in range(left, 6)
    )


def test_alias_census_separates_action_and_marks_singletons_untested() -> None:
    aliases: dict[d028.VisibleKey, d028._AliasRecord] = {}
    key = (0.1, 0.2, 0.3, 0.4, 0.0, 0.5, Action.WAIT.name)
    d028._record_alias(aliases, key, (0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    d028._record_alias(aliases, key, (0.0, 0.0, 0.0, 0.0, 1.0, 0.0))
    singleton = (0.2, 0.2, 0.3, 0.4, 0.0, 0.5, Action.MOVE_FORWARD.name)
    d028._record_alias(aliases, singleton, (0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    census = d028.alias_census(aliases)
    assert census["transitions"] == 3
    assert census["unique_keys"] == 2
    assert census["repeated_keys"] == 1
    assert census["singleton_keys"] == 1
    assert census["aliased_repeated_keys"] == 1
    records = census["records"]
    assert isinstance(records, list)
    statuses = {
        record["executed_action"]: record["aliasing_status"] for record in records
    }
    assert statuses[Action.WAIT.name] == "aliased"
    assert statuses[Action.MOVE_FORWARD.name] == "untested"


def test_batch_ols_recovers_fixed_linear_and_quadratic_mappings_without_leakage() -> (
    None
):
    linear_rows = [_synthetic_rows(seed, quadratic=False) for seed in (2, 4, 1, 3)]
    linear_fits = d028._fit_cross_seed(
        linear_rows[:2], frozenset((2, 4)), quadratic=False
    )
    for fit in linear_fits.values():
        assert fit.coefficients.shape == (7, 6)
        assert fit.rank == 7
    linear_score = d028._score_fit(linear_rows[2], linear_fits, quadratic=False)
    assert linear_score.overall.count == 160
    assert linear_score.overall.absolute_errors == pytest.approx([0.0] * 6, abs=1e-12)

    quadratic_rows = [_synthetic_rows(seed, quadratic=True) for seed in (2, 4, 1, 3)]
    quadratic_fits = d028._fit_cross_seed(
        quadratic_rows[:2], frozenset((2, 4)), quadratic=True
    )
    for fit in quadratic_fits.values():
        assert fit.coefficients.shape == (28, 6)
        # The fixed binary contact channel makes v[4] and v[4]**2
        # algebraically dependent; preserve, rather than repair, that rank.
        assert fit.rank == 27
    quadratic_score = d028._score_fit(quadratic_rows[2], quadratic_fits, quadratic=True)
    assert quadratic_score.overall.count == 160
    assert quadratic_score.overall.absolute_errors == pytest.approx(
        [0.0] * 6, abs=1e-10
    )


def test_oracle_pose_clamps_full_clip_and_stall_deterministically() -> None:
    config = d027.D020PhysicalConfig()
    full, _, full_distance = d028._apply_known_action(
        (0.5, 0.5), 0.0, Action.MOVE_FORWARD, config
    )
    clipped, _, clipped_distance = d028._apply_known_action(
        (0.98, 0.5), 0.0, Action.MOVE_FORWARD, config
    )
    stalled, _, stalled_distance = d028._apply_known_action(
        (1.0, 0.5), 0.0, Action.MOVE_FORWARD, config
    )
    assert full == pytest.approx((0.55, 0.5))
    assert full_distance == pytest.approx(0.05)
    assert clipped == pytest.approx((1.0, 0.5))
    assert clipped_distance == pytest.approx(0.02)
    assert stalled == pytest.approx((1.0, 0.5))
    assert stalled_distance == pytest.approx(0.0)
