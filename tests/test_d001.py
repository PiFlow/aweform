"""Tests for the D-001 current-ecology degeneracy probe."""

import math

import pytest

from aweform.d001 import (
    D001_DEFAULT_DEVELOPMENT_SEEDS,
    D001Policy,
    d001_contact_net_energy,
    run_d001_probe,
)
from aweform.exp003 import EXP003StationConfig


def test_d001_contact_arithmetic_is_positive_for_both_constant_policies() -> None:
    config = EXP003StationConfig()
    net_energy = d001_contact_net_energy(config)

    assert math.isclose(net_energy[D001Policy.DOCK_WAIT], 0.4)
    assert math.isclose(net_energy[D001Policy.DOCK_TURN_LEFT], 0.38)


def test_d001_docked_constant_policies_survive_and_reach_full_energy() -> None:
    results = run_d001_probe((18141,), horizon=50)

    assert tuple(result.policy for result in results) == tuple(D001Policy)
    for result in results:
        assert result.environment_seed == 18141
        assert result.transitions == 50
        assert result.initial_energy == 5.0
        assert result.minimum_energy == 5.0
        assert result.final_energy == 10.0
        assert result.charging_contact_preserved
        assert result.position_preserved
        assert not result.terminated
        assert result.truncated

    by_policy = {result.policy: result for result in results}
    assert by_policy[D001Policy.DOCK_WAIT].first_full_energy_step == 13
    assert by_policy[D001Policy.DOCK_TURN_LEFT].first_full_energy_step == 14


def test_d001_default_development_seeds_are_accepted() -> None:
    results = run_d001_probe(D001_DEFAULT_DEVELOPMENT_SEEDS, horizon=1)

    assert len(results) == 2 * len(D001_DEFAULT_DEVELOPMENT_SEEDS)
    assert all(result.truncated for result in results)


def test_d001_rejects_formally_reserved_seed() -> None:
    with pytest.raises(ValueError, match="reserved for a formal experiment"):
        run_d001_probe((50001,), horizon=1)
