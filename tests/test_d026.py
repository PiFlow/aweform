"""Focused tests for the D-026 one-third SEEK delegation probe."""

from __future__ import annotations

import inspect

import numpy as np
import pytest

from aweform import d024, d025, d026
from aweform.exp001 import EXP001_EXPLORER_HAZARD
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
) -> d026.D026Observation:
    return d026.D026Observation(
        energy=energy,
        beacon=BeaconObservation(left, forward, right, contact),
        thermal=thermal,
    )


def test_d026_freeze_and_seed_guard() -> None:
    assert d026.D026_HORIZON == 70_000
    assert d026.D026_SEEK_DELEGATION_PROBABILITY == 1.0 / 3.0
    assert d026.D026_DEFAULT_DEVELOPMENT_SEEDS == tuple(range(18368, 18388))
    assert validate_exp003_development_seeds(d026.D026_DEFAULT_DEVELOPMENT_SEEDS) == (
        tuple(range(18368, 18388))
    )
    assert d026._validate_d026_development_seeds(
        d026.D026_DEFAULT_DEVELOPMENT_SEEDS
    ) == d026.D026_DEFAULT_DEVELOPMENT_SEEDS
    with pytest.raises(ValueError, match="requires exactly"):
        d026._validate_d026_development_seeds((18368,))
    with pytest.raises(ValueError, match="reserved for a formal experiment"):
        d026._validate_d026_development_seeds((50001, 50002, 50003))


def test_d026_initial_state_and_boundary_match_d024() -> None:
    environment = d026.D026Env()
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
    assert EXP001_EXPLORER_HAZARD == 1.0 / 8.0


def test_d026_only_changes_seek_delegation_rate() -> None:
    d025_controller = d025.D025Controller(np.random.default_rng(17))
    d026_controller = d026.D026Controller(np.random.default_rng(17))
    charge = observation(energy=0.9, contact=True)
    assert d026_controller.act(charge) is d025_controller.act(charge)
    seek = observation()
    d026_action = d026_controller.act(seek)
    assert d026_controller.mode is d026.D026Mode.SEEK
    assert d026_controller.last_arbitration is not None
    if not d026_controller.last_arbitration.delegated:
        assert d026_action is seek_beacon_action(seek.beacon)
    assert d026_controller.seek_segment_starts == 1
    assert d026_controller.seek_delegation_probability == 1.0 / 3.0
    assert d025_controller.seek_delegation_probability == 1.0 / 8.0


def test_d026_begin_segment_does_not_reseed_or_consume_rng() -> None:
    first = np.random.default_rng(91)
    second = np.random.default_rng(91)
    controller = d026.D026Controller(first)
    controller.explorer.begin_segment()
    assert first.random() == second.random()


def test_d026_short_replay_is_deterministic_and_keeps_boundary() -> None:
    first = d026._run_d026_seed(18368, horizon=200)
    second = d026._run_d026_seed(18368, horizon=200)
    assert first == second
    assert first["transitions"] == 200
    assert first["initial_dual_contact_valid"] is True
    arbitration = first["seek_arbitration"]
    assert isinstance(arbitration, dict)
    assert arbitration["false_contact_seek_decisions"] == 0
    assert arbitration["delegation_probability"] == 1.0 / 3.0
    assert arbitration["decision_records_retained"] is False
    assert first["pre_seek_prefix_validation"]["validated"] is True  # type: ignore[index]


def test_d026_controller_uses_only_existing_visible_observation() -> None:
    source = inspect.getsource(d026.D026Controller)
    assert "position" not in source
    assert "heading" not in source
    assert "D024" not in source
    assert "seek_beacon_action" in inspect.getsource(d025.D025Controller)
    assert "StochasticPersistentExplorer" in inspect.getsource(d025.D025Controller)
