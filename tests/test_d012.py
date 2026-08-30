"""Focused tests for the D-012 fixed-controller robustness census."""

from __future__ import annotations

import inspect

import pytest

from aweform import d011, d012
from aweform.exp003_seed_policy import validate_exp003_development_seeds


def test_d012_declares_exactly_200_new_nearby_development_seeds() -> None:
    seeds = d012.D012_DEFAULT_DEVELOPMENT_SEEDS
    assert len(seeds) == d012.D012_SEED_COUNT == 200
    assert seeds == tuple(range(18144, 18344))
    assert d012.D012_DEVELOPMENT_SEED_RANGE == (18144, 18343)
    assert not set(seeds) & set(d011.D011_DEFAULT_DEVELOPMENT_SEEDS)
    assert validate_exp003_development_seeds(seeds) == seeds
    assert d012._validate_d012_development_seeds(seeds) == seeds


def test_d012_rejects_formal_and_non_declared_seed_sets() -> None:
    with pytest.raises(ValueError, match="reserved for a formal experiment"):
        d012.run_d012_census(
            (*d012.D012_DEFAULT_DEVELOPMENT_SEEDS[:-1], 50001), horizon=1
        )
    with pytest.raises(ValueError, match="exact predeclared 200-seed range"):
        d012.run_d012_census((18144,), horizon=1)


def test_d012_small_horizon_preserves_each_d011_record_and_boundary() -> None:
    result = d012.run_d012_census(horizon=2)
    assert result["experiment"] == "D-012"
    assert result["executed_commit_sha"] is None
    assert result["organism_visible"] == {
        "inherited_from_d011": True,
        "no_evaluator_aggregation_passed_to_controller": True,
        "reward": 0.0,
        "info": {},
    }
    records = result["results"]
    assert isinstance(records, list)
    assert len(records) == 200
    first = records[0]
    assert isinstance(first, dict)
    assert first["seed"] == 18144
    assert first["transitions"] == 2
    assert "seek_episodes" in first
    aggregate = result["aggregate"]
    assert isinstance(aggregate, dict)
    assert aggregate["seed_count"] == 200
    assert aggregate["total_transitions"] == 400
    assert aggregate["surviving_to_horizon_count"] == 200


def test_d012_aggregation_is_deterministic_and_nonlearning() -> None:
    first = d012.run_d012_census(horizon=4)
    second = d012.run_d012_census(horizon=4)
    assert first == second
    assert d012.D012_DEFAULT_DEVELOPMENT_SEEDS == tuple(range(18144, 18344))
    assert "d008" not in inspect.getsource(d011.D011Controller).lower()
    assert first["programmed"] == {
        "controller": "unchanged D011Controller",
        "d011_thresholds_and_action_logic_unchanged": True,
        "no_d008": True,
        "no_learning": True,
        "no_model_predictions": True,
        "no_resets_within_lifetime": True,
        "no_reward": True,
        "runner": "reused d011._run_seed",
    }


def test_d012_executed_sha_is_explicitly_validated() -> None:
    with pytest.raises(ValueError, match="40-character lowercase SHA"):
        d012.run_d012_census(horizon=1, executed_commit_sha="not-a-sha")
