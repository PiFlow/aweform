"""Focused tests for the D-011 fixed thermal-beacon baseline."""

from __future__ import annotations

import inspect
from dataclasses import fields

import numpy as np
import pytest

from aweform import d011
from aweform.d003 import HOT_DEPART_THRESHOLD
from aweform.env import Action
from aweform.exp003 import (
    EXP003_B50_ENTER_SEEK_THRESHOLD,
    BeaconObservation,
    seek_beacon_action,
)


def observation(
    energy: float,
    thermal: float,
    left: float,
    forward: float,
    right: float,
    contact: bool,
) -> d011.D011Observation:
    return d011.D011Observation(
        energy=energy,
        beacon=BeaconObservation(
            float(left), float(forward), float(right), contact
        ),
        thermal=thermal,
    )


def test_observation_contains_exactly_d011_visible_values() -> None:
    assert [field.name for field in fields(d011.D011Observation)] == [
        "energy",
        "beacon",
        "thermal",
    ]
    assert [field.name for field in fields(BeaconObservation)] == [
        "left",
        "forward",
        "right",
        "charging_contact",
    ]
    item = observation(0.5, 0.2, 0.1, 0.2, 0.3, True)
    assert item.charging_contact is True
    with pytest.raises((AttributeError, TypeError)):
        item.energy = 0.3  # type: ignore[misc]


def test_projection_rejects_geometry_and_telemetry_and_uses_only_six_channels() -> None:
    projected = d011._controller_observation(
        np.asarray((0.91, 0.8, 0.7, 0.6, 1.0, 0.2), dtype=np.float32)
    )
    assert projected.energy == pytest.approx(0.91)
    assert projected.beacon.left == pytest.approx(0.8)
    assert projected.beacon.forward == pytest.approx(0.7)
    assert projected.beacon.right == pytest.approx(0.6)
    assert projected.charging_contact is True
    assert projected.thermal == pytest.approx(0.2)
    assert not hasattr(projected, "position")
    assert not hasattr(projected, "distance")
    assert not hasattr(projected, "heading")
    assert not hasattr(projected, "seed")
    assert not hasattr(projected, "telemetry")
    with pytest.raises(ValueError):
        d011._controller_observation(np.zeros(5, dtype=np.float32))


def controller() -> d011.D011Controller:
    return d011.D011Controller(np.random.default_rng(7))


def test_charge_below_hot_threshold_waits_and_threshold_starts_departure() -> None:
    item = controller()
    assert item.act(
        observation(0.5, HOT_DEPART_THRESHOLD - 0.0001, 0, 1, 0, True)
    ) is Action.WAIT
    assert item.mode is d011.D011Mode.CHARGE
    assert item.act(
        observation(0.5, HOT_DEPART_THRESHOLD, 0, 1, 0, True)
    ) is Action.MOVE_FORWARD
    assert item.mode is d011.D011Mode.DEPART


def test_departure_continues_forward_until_physical_contact_is_lost() -> None:
    item = controller()
    item.mode = d011.D011Mode.DEPART
    assert item.act(observation(0.5, 0.8, 0, 1, 0, True)) is Action.MOVE_FORWARD
    assert item.mode is d011.D011Mode.DEPART
    assert item.act(observation(0.5, 0.8, 0.1, 0.2, 0.9, False)) is not Action.WAIT
    assert item.mode is d011.D011Mode.AWAY


def test_away_above_threshold_explores_even_with_strong_beacon() -> None:
    item = controller()
    item.mode = d011.D011Mode.AWAY
    strong = observation(
        EXP003_B50_ENTER_SEEK_THRESHOLD, 0.4, 0.1, 1.0, 0.1, False
    )
    assert item.act(strong) is Action.MOVE_FORWARD
    assert item.mode is d011.D011Mode.AWAY


def test_away_below_threshold_enters_seek() -> None:
    item = controller()
    item.mode = d011.D011Mode.AWAY
    visible = observation(
        EXP003_B50_ENTER_SEEK_THRESHOLD - 0.0001, 0.4, 0.1, 0.2, 0.9, False
    )
    assert item.act(visible) is seek_beacon_action(visible.beacon)
    assert item.mode is d011.D011Mode.SEEK


@pytest.mark.parametrize(
    ("left", "forward", "right"),
    [(0.1, 0.8, 0.2), (0.9, 0.1, 0.2), (0.1, 0.2, 0.9), (0.5, 0.5, 0.5)],
)
def test_seek_reuses_exact_historical_beacon_action(
    left: float, forward: float, right: float
) -> None:
    item = controller()
    item.mode = d011.D011Mode.SEEK
    visible = observation(0.2, 0.4, left, forward, right, False)
    assert item.act(visible) is seek_beacon_action(visible.beacon)
    assert item.mode is d011.D011Mode.SEEK


def test_seek_requires_physical_contact_not_beacon_strength() -> None:
    item = controller()
    item.mode = d011.D011Mode.SEEK
    assert item.act(observation(0.2, 0.4, 1.0, 1.0, 1.0, False)) is Action.TURN_LEFT
    assert item.mode is d011.D011Mode.SEEK
    assert item.act(observation(0.2, 0.4, 1.0, 1.0, 1.0, True)) is Action.WAIT
    assert item.mode is d011.D011Mode.CHARGE


def test_no_d008_prediction_is_read_by_controller() -> None:
    source = inspect.getsource(d011)
    assert "d008" not in source.lower()
    assert "prediction" not in inspect.getsource(d011.D011Controller.act).lower()


def test_runner_preserves_reward_info_and_reports_nonlearning_boundary() -> None:
    result = d011.run_d011_probe((18141,), horizon=2)
    assert result["learned"] == {"status": "none", "learner_prediction_read": False}
    assert result["organism_boundary"] == {"reward": 0.0, "info": {}}
    run = result["results"][0]
    assert isinstance(run, dict)
    assert run["transitions"] == 2


def test_development_seed_restrictions_are_enforced() -> None:
    with pytest.raises(ValueError, match="reserved for a formal experiment"):
        d011.run_d011_probe((50001,), horizon=1)
    with pytest.raises(ValueError, match="only predeclared development seeds"):
        d011.run_d011_probe((42,), horizon=1)


def test_geometry_diagnostics_are_post_action_and_not_controller_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline = d011.run_d011_probe((18141,), horizon=80)
    monkeypatch.setattr(d011, "_distance", lambda _position, _station: 1e9)
    adversarial = d011.run_d011_probe((18141,), horizon=80)
    baseline_run = baseline["results"][0]
    adversarial_run = adversarial["results"][0]
    assert isinstance(baseline_run, dict)
    assert isinstance(adversarial_run, dict)
    assert adversarial_run["action_counts"] == baseline_run["action_counts"]
    assert adversarial_run["mode_entry_counts"] == baseline_run["mode_entry_counts"]
    diagnostics = adversarial_run["evaluator_only_navigation"]
    assert isinstance(diagnostics, dict)
    assert diagnostics["passed_to_controller"] is False


def test_adversarial_d008_prediction_cannot_change_actions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline = d011.run_d011_probe((18141,), horizon=80)

    class ForbiddenPrediction:
        def __getattribute__(self, name: str) -> object:
            raise AssertionError(f"D-011 attempted to read forbidden learner: {name}")

    monkeypatch.setitem(
        __import__("sys").modules, "aweform.d008", ForbiddenPrediction()
    )
    adversarial = d011.run_d011_probe((18141,), horizon=80)
    assert adversarial["results"][0]["action_counts"] == baseline["results"][0][
        "action_counts"
    ]
