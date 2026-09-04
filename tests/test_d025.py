"""Focused tests for the D-025 bounded stochastic SEEK probe."""

from __future__ import annotations

import inspect

import numpy as np
import pytest

from aweform import d021, d024, d025
from aweform.exp003 import BeaconObservation, seek_beacon_action
from aweform.exp003_seed_policy import validate_exp003_development_seeds


def observation(
    *,
    energy: float = 0.25,
    left: float = 0.1,
    forward: float = 0.8,
    right: float = 0.2,
    contact: bool = False,
    thermal: float = 0.2875,
) -> d025.D025Observation:
    return d025.D025Observation(
        energy=energy,
        beacon=BeaconObservation(left, forward, right, contact),
        thermal=thermal,
    )


def test_d025_freeze_and_seed_guard() -> None:
    assert d025.D025_HORIZON == 70_000
    assert d025.D025_SEEK_DELEGATION_PROBABILITY == 1.0 / 8.0
    assert d025.D025_DEFAULT_DEVELOPMENT_SEEDS == (18365, 18366, 18367)
    assert validate_exp003_development_seeds(d025.D025_DEFAULT_DEVELOPMENT_SEEDS) == (
        18365,
        18366,
        18367,
    )
    assert d025._validate_d025_development_seeds(
        d025.D025_DEFAULT_DEVELOPMENT_SEEDS
    ) == d025.D025_DEFAULT_DEVELOPMENT_SEEDS
    with pytest.raises(ValueError, match="requires exactly"):
        d025._validate_d025_development_seeds((18365,))
    with pytest.raises(ValueError, match="reserved for a formal experiment"):
        d025._validate_d025_development_seeds((50001, 50002, 50003))


def test_d025_initial_state_reuses_d024_exact_dual_contact() -> None:
    environment = d025.D025Env()
    observation_value, info = environment.reset(
        options={
            "body_position": d024.D024_INITIAL_BODY_CENTER,
            "station_center": d024.D024_STATION_CENTER,
            "heading": d024.D024_INITIAL_HEADING,
            "battery_j": d024.D024_INITIAL_BATTERY_J,
            "body_temperature_c": d024.D024_INITIAL_TEMPERATURE_C,
            "charger_termination_latched": False,
        }
    )
    assert info == {}
    assert environment.charging_contact is True
    assert observation_value.shape == (6,)
    assert observation_value[4] == 1.0


def test_d025_non_seek_behaviour_matches_d021_and_seek_defaults_to_greedy() -> None:
    d021_controller = d021.D021Controller(np.random.default_rng(17))
    d025_controller = d025.D025Controller(np.random.default_rng(17))
    charge = observation(energy=0.9, contact=True)
    assert d025_controller.act(charge) is d021_controller.act(charge)
    assert d025_controller.mode is d021_controller.mode

    seek = observation()
    actual = d025_controller.act(seek)
    assert d025_controller.mode is d025.D025Mode.SEEK
    assert d025_controller.last_arbitration is not None
    if not d025_controller.last_arbitration.delegated:
        assert actual is seek_beacon_action(seek.beacon)
    assert d025_controller.seek_segment_starts == 1


def test_d025_begin_segment_does_not_reseed_or_consume_rng() -> None:
    first = np.random.default_rng(91)
    second = np.random.default_rng(91)
    controller = d025.D025Controller(first)
    controller.explorer.begin_segment()
    assert first.random() == second.random()


def test_d025_short_replay_is_deterministic_and_keeps_boundary() -> None:
    first = d025._run_d025_seed(18365, horizon=200)
    second = d025._run_d025_seed(18365, horizon=200)
    assert first == second
    assert first["transitions"] == 200
    assert first["initial_dual_contact_valid"] is True
    assert first["seek_arbitration"]["false_contact_seek_decisions"] == 0
    assert first["pre_seek_prefix_validation"]["validated"] is True


def test_d025_controller_uses_only_existing_visible_observation() -> None:
    source = inspect.getsource(d025.D025Controller)
    assert "position" not in source
    assert "heading" not in source
    assert "D024" not in source
    assert "seek_beacon_action" in source
    assert "StochasticPersistentExplorer" in source
