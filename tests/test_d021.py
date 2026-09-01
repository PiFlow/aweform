"""Focused tests for the D-021 fixed V0.4 energy-regulation baseline."""

from __future__ import annotations

import inspect
import math

import numpy as np
import pytest

from aweform import d011, d021
from aweform.d020 import D020Env, D020PhysicalConfig, D020TerminationReason
from aweform.env import Action
from aweform.exp003 import (
    BeaconObservation,
    seek_beacon_action,
)
from aweform.exp003_seed_policy import validate_exp003_development_seeds
from aweform.rng import RandomStreams


def observation(
    *,
    energy: float = 0.75,
    left: float = 0.1,
    forward: float = 0.8,
    right: float = 0.2,
    contact: bool = False,
    thermal: float = 0.2875,
) -> d011.D011Observation:
    return d011.D011Observation(
        energy=energy,
        beacon=BeaconObservation(left, forward, right, contact),
        thermal=thermal,
    )


def controller() -> d021.D021Controller:
    return d021.D021Controller(np.random.default_rng(7))


def test_exact_frozen_thresholds_and_seed_guard() -> None:
    assert d021.D021_FULL_ENERGY_THRESHOLD == 1.0
    assert d021.EXP003_B50_ENTER_SEEK_THRESHOLD == 0.50
    assert d021.D021_DEFAULT_DEVELOPMENT_SEEDS == (18365, 18366, 18367)
    assert validate_exp003_development_seeds(d021.D021_DEFAULT_DEVELOPMENT_SEEDS) == (
        18365,
        18366,
        18367,
    )
    assert d021._validate_d021_development_seeds(
        d021.D021_DEFAULT_DEVELOPMENT_SEEDS
    ) == (
        18365,
        18366,
        18367,
    )
    with pytest.raises(ValueError, match="only predeclared development seeds"):
        d021._validate_d021_development_seeds((18364,))
    with pytest.raises(ValueError, match="reserved for a formal experiment"):
        d021._validate_d021_development_seeds((50001,))


def test_charge_below_full_waits_and_stays_in_charge() -> None:
    item = controller()
    assert item.act(observation(energy=0.999, contact=True)) is Action.WAIT
    assert item.mode is d021.D021Mode.CHARGE


def test_full_contact_departure_uses_exact_full_threshold() -> None:
    item = controller()
    assert item.act(observation(energy=1.0, contact=True)) is Action.MOVE_FORWARD
    assert item.mode is d021.D021Mode.DEPART


def test_charge_without_contact_transitions_to_seek_using_beacon() -> None:
    item = controller()
    visible = observation(energy=1.0, contact=False)
    assert item.act(visible) is seek_beacon_action(visible.beacon)
    assert item.mode is d021.D021Mode.SEEK


def test_depart_while_contact_moves_and_after_exit_enters_away_same_decision() -> None:
    item = controller()
    item.mode = d021.D021Mode.DEPART
    assert item.act(observation(contact=True)) is Action.MOVE_FORWARD
    assert item.mode is d021.D021Mode.DEPART
    action = item.act(observation(energy=0.75, contact=False))
    assert action is not Action.WAIT
    assert item.mode is d021.D021Mode.AWAY


def test_away_threshold_is_strictly_below_half() -> None:
    item = controller()
    item.mode = d021.D021Mode.AWAY
    assert item.act(observation(energy=0.50)) is Action.MOVE_FORWARD
    assert item.mode is d021.D021Mode.AWAY

    item = controller()
    item.mode = d021.D021Mode.AWAY
    visible = observation(energy=0.499999, contact=False, forward=0.1, left=0.9)
    assert item.act(visible) is seek_beacon_action(visible.beacon)
    assert item.mode is d021.D021Mode.SEEK


def test_seek_without_contact_uses_beacon_and_contact_returns_wait() -> None:
    item = controller()
    item.mode = d021.D021Mode.SEEK
    visible = observation(energy=0.2, contact=False, forward=0.1, right=0.9)
    assert item.act(visible) is seek_beacon_action(visible.beacon)
    assert item.mode is d021.D021Mode.SEEK
    assert item.act(observation(energy=0.2, contact=True)) is Action.WAIT
    assert item.mode is d021.D021Mode.CHARGE


@pytest.mark.parametrize(
    "mode, visible",
    [
        (d021.D021Mode.CHARGE, observation(energy=0.4, contact=True)),
        (d021.D021Mode.CHARGE, observation(energy=1.0, contact=True)),
        (d021.D021Mode.AWAY, observation(energy=0.8, contact=False)),
        (d021.D021Mode.SEEK, observation(energy=0.2, contact=False)),
        (d021.D021Mode.SEEK, observation(energy=0.2, contact=True)),
    ],
)
def test_temperature_has_zero_behavioral_influence(
    mode: d021.D021Mode, visible: d011.D011Observation
) -> None:
    thermal_values = (0.0, 0.2875, 0.5625, 0.75, 0.8125, 1.0)
    outcomes: list[tuple[Action, d021.D021Mode]] = []
    for thermal in thermal_values:
        item = d021.D021Controller(np.random.default_rng(123))
        item.mode = mode
        changed = d011.D011Observation(
            energy=visible.energy,
            beacon=visible.beacon,
            thermal=thermal,
        )
        outcomes.append((item.act(changed), item.mode))
    assert outcomes == [outcomes[0]] * len(outcomes)
    assert "thermal" not in inspect.getsource(d021.D021Controller.act)


def test_controller_api_contains_no_evaluator_inputs() -> None:
    fields = {
        field.name for field in d021.D021Observation.__dataclass_fields__.values()
    }
    assert fields == {"energy", "beacon", "thermal"}
    beacon_fields = set(d021.BeaconObservation.__dataclass_fields__)
    assert beacon_fields == {"left", "forward", "right", "charging_contact"}
    source = inspect.getsource(d021.D021Controller)
    for forbidden in (
        "position",
        "station_center",
        "distance",
        "joule",
        "temperature_c",
        "charger_termination",
        "shutdown",
    ):
        assert forbidden not in source


def test_runner_uses_frozen_full_contact_setup_and_boundary() -> None:
    result = d021.run_d021_probe((18365,), horizon=1)
    assert result["authoritative_base_sha"] == d021.D021_AUTHORITATIVE_BASE_SHA
    assert result["organism_boundary"] == {"reward": 0.0, "info": {}}
    run = result["results"][0]
    assert isinstance(run, dict)
    assert run["transitions"] == 1
    assert run["full_departures"] == 1
    assert run["initial_full_departures"] == 1
    assert run["physical_seconds"] == 0.1
    assert run["battery_normalized"]["start"] == 1.0
    assert run["temperature_normalized"]["start"] == pytest.approx(0.2875)


def test_heading_comes_from_environment_stream_only() -> None:
    seed = 18365
    expected_streams = RandomStreams.from_seed(seed)
    expected_heading = float(expected_streams.environment.uniform(0.0, math.tau))
    result = d021.run_d021_probe((seed,), horizon=1)
    run = result["results"][0]
    assert isinstance(run, dict)
    assert run["seeded_heading"] == expected_heading


def test_d020_post_action_contact_and_termination_boundaries_remain_physical() -> None:
    environment = D020Env(D020PhysicalConfig())
    environment.reset(
        options={
            "body_position": (0.26, 0.5),
            "station_center": (0.5, 0.5),
            "heading": 0.0,
            "battery_j": 2.0,
        }
    )
    for _ in range(3):
        _, reward, terminated, truncated, info = environment.step(Action.MOVE_FORWARD)
        if terminated or truncated:
            break
    assert reward == 0.0
    assert info == {}
    assert environment.last_transition is not None
    assert environment.last_transition.charging_contact_after is True
    assert environment.last_transition.termination_reason is None

    depleted = D020Env(D020PhysicalConfig())
    depleted.reset(
        options={
            "body_position": (0.1, 0.1),
            "station_center": (0.9, 0.9),
            "battery_j": 0.01,
        }
    )
    _, reward, terminated, truncated, info = depleted.step(Action.WAIT)
    assert (reward, terminated, truncated, info) == (0.0, True, False, {})
    assert depleted.last_transition is not None
    assert depleted.last_transition.termination_reason is (
        D020TerminationReason.ENERGY_DEPLETION
    )


def test_d020_thermal_shutdown_is_not_overridden_by_d021() -> None:
    config = D020PhysicalConfig(
        electronics_body_heat_w=100.0,
        thermal_capacitance_j_per_k=1.0,
        thermal_conductance_w_per_k=0.0,
        initial_body_temperature_c=59.0,
    )
    environment = D020Env(config)
    environment.reset(
        options={"body_position": (0.1, 0.1), "station_center": (0.9, 0.9)}
    )
    _, reward, terminated, truncated, info = environment.step(Action.WAIT)
    assert (reward, terminated, truncated, info) == (0.0, True, False, {})
    assert environment.last_transition is not None
    assert environment.last_transition.termination_reason is (
        D020TerminationReason.EMERGENCY_HARD_THERMAL_SHUTDOWN
    )


def test_unresolved_seek_at_horizon_is_censoring_not_failure() -> None:
    assert d021._classify_unresolved_seek(terminated=False, truncated=True) == {
        "demonstrated_failed_seek_episodes": 0,
        "horizon_censored_seek_episodes": 1,
    }
    assert d021._classify_unresolved_seek(terminated=True, truncated=False) == {
        "demonstrated_failed_seek_episodes": 1,
        "horizon_censored_seek_episodes": 0,
    }


def test_same_seed_reproduces_heading_and_compact_event_summary() -> None:
    first = d021.run_d021_probe((18365,), horizon=200)
    second = d021.run_d021_probe((18365,), horizon=200)
    assert first == second
    assert isinstance(first["results"][0]["seek_episodes"], list)


def test_cli_sha_validation() -> None:
    with pytest.raises(ValueError, match="40-character lowercase SHA"):
        d021.run_d021_probe((18365,), horizon=1, executed_commit_sha="bad")
