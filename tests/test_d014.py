"""Focused tests for the D-014 full-charge departure correction."""

from __future__ import annotations

import inspect
from dataclasses import fields

import numpy as np
import pytest

from aweform import d011, d013, d014
from aweform.d003 import HOT_DEPART_THRESHOLD
from aweform.development_visualizer import (
    DEVELOPMENT_VISUALIZATION_ADAPTERS,
    build_d014_development_visualization,
    build_development_visualization,
    build_development_visualization_figure,
)
from aweform.env import Action
from aweform.exp003 import (
    EXP003_B50_ENTER_SEEK_THRESHOLD,
    BeaconObservation,
    seek_beacon_action,
)
from aweform.exp003_seed_policy import validate_exp003_development_seeds


def observation(
    energy: float,
    thermal: float,
    left: float = 0.1,
    forward: float = 0.8,
    right: float = 0.2,
    contact: bool = True,
) -> d011.D011Observation:
    return d011.D011Observation(
        energy=energy,
        beacon=BeaconObservation(left, forward, right, contact),
        thermal=thermal,
    )


def controller() -> d014.D014Controller:
    return d014.D014Controller(np.random.default_rng(7))


def test_full_energy_with_contact_starts_departure_below_hot_threshold() -> None:
    item = controller()
    assert item.act(observation(1.0, HOT_DEPART_THRESHOLD - 0.01)) is (
        Action.MOVE_FORWARD
    )
    assert item.mode is d011.D011Mode.DEPART


def test_hot_thermal_with_contact_starts_departure_before_full_energy() -> None:
    item = controller()
    assert item.act(observation(0.9, HOT_DEPART_THRESHOLD)) is Action.MOVE_FORWARD
    assert item.mode is d011.D011Mode.DEPART


def test_below_both_departure_conditions_waits_in_charge() -> None:
    item = controller()
    assert item.act(observation(0.999, HOT_DEPART_THRESHOLD - 0.01)) is Action.WAIT
    assert item.mode is d011.D011Mode.CHARGE


def test_lost_contact_in_charge_preserves_d011_seek_transition() -> None:
    item = controller()
    visible = observation(1.0, HOT_DEPART_THRESHOLD - 0.01, contact=False)
    assert item.act(visible) is seek_beacon_action(visible.beacon)
    assert item.mode is d011.D011Mode.SEEK


def test_departure_behavior_is_inherited_unchanged() -> None:
    item = controller()
    item.mode = d011.D011Mode.DEPART
    assert item.act(observation(0.2, 0.1, contact=True)) is Action.MOVE_FORWARD
    assert item.mode is d011.D011Mode.DEPART
    assert item.act(observation(0.8, 0.1, contact=False)) is not Action.WAIT
    assert item.mode is d011.D011Mode.AWAY


def test_away_behavior_is_inherited_unchanged() -> None:
    d014_item = controller()
    d011_item = d011.D011Controller(np.random.default_rng(7))
    d014_item.mode = d011.D011Mode.AWAY
    d011_item.mode = d011.D011Mode.AWAY
    visible = observation(
        EXP003_B50_ENTER_SEEK_THRESHOLD,
        0.4,
        contact=False,
    )
    assert d014_item.act(visible) is d011_item.act(visible)
    assert d014_item.mode is d011_item.mode is d011.D011Mode.AWAY


def test_seek_behavior_is_inherited_unchanged() -> None:
    d014_item = controller()
    d011_item = d011.D011Controller(np.random.default_rng(7))
    d014_item.mode = d011.D011Mode.SEEK
    d011_item.mode = d011.D011Mode.SEEK
    visible = observation(0.2, 0.4, 0.1, 0.2, 0.9, contact=False)
    assert d014_item.act(visible) is d011_item.act(visible)
    assert d014_item.mode is d011_item.mode is d011.D011Mode.SEEK


def test_d011_observation_has_not_gained_fields() -> None:
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


def test_historical_d011_full_energy_rule_still_waits() -> None:
    item = d011.D011Controller(np.random.default_rng(7))
    assert item.act(observation(1.0, HOT_DEPART_THRESHOLD - 0.01)) is Action.WAIT
    assert item.mode is d011.D011Mode.CHARGE


def test_d014_seed_guard_accepts_only_declared_seeds_after_canonical_guard() -> None:
    seeds = d014.D014_DEFAULT_DEVELOPMENT_SEEDS
    assert seeds == (18347, 18348, 18349)
    assert validate_exp003_development_seeds(seeds) == seeds
    assert d014._validate_d014_development_seeds(seeds) == seeds
    assert d014._validate_d014_development_seeds((18347,)) == (18347,)


@pytest.mark.parametrize("seed", (42, 18141, 18346, 50001, 70001))
def test_d014_seed_guard_rejects_other_and_reserved_seeds(seed: int) -> None:
    with pytest.raises(ValueError):
        d014._validate_d014_development_seeds((seed,))


def test_d014_short_runner_preserves_boundary_and_reports_trigger_context() -> None:
    result = d014.run_d014_probe((18347,), horizon=20)
    assert result["experiment"] == "D-014"
    assert result["organism_boundary"] == {"reward": 0.0, "info": {}}
    assert result["learned"] == {
        "status": "none",
        "learner_prediction_read": False,
    }
    run = result["results"][0]
    assert isinstance(run, dict)
    assert run["transitions"] == 20
    assert run["departure_trigger_counts"] == {
        "full_only": 1,
        "thermal_only": 0,
        "both": 0,
    }
    events = run["charger_departure_events"]
    assert isinstance(events, list)
    assert events[0]["full_energy_condition"] is True
    assert events[0]["hot_thermal_condition"] is False
    assert events[0]["trigger_category"] == "full_only"


def test_d014_does_not_instantiate_d013_predictor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ForbiddenPredictor:
        def __init__(self) -> None:
            raise AssertionError("D-014 must not instantiate D-013 predictor")

    monkeypatch.setattr(d013, "D013ActionConsequencePredictor", ForbiddenPredictor)
    result = d014.run_d014_probe((18347,), horizon=2)
    assert result["programmed"]["learning"] is False


def test_d014_visualizer_is_registered_two_panel_and_has_no_learner() -> None:
    assert DEVELOPMENT_VISUALIZATION_ADAPTERS["d014"] is (
        build_d014_development_visualization
    )
    data = build_development_visualization("d014", seed=18347, horizon=3)
    assert data.source_label.startswith("D-014")
    assert data.consequence_predictions is None
    figure, animation = build_development_visualization_figure(data)
    assert len(figure.axes) == 2
    assert not hasattr(figure, "_aweform_learner_axes") or not getattr(
        figure, "_aweform_learner_axes"
    )
    assert all("SHADOW ONLY" not in axis.get_title() for axis in figure.axes)
    animation.event_source.stop()
    import matplotlib.pyplot as plt

    plt.close(figure)


def test_d014_visualizer_uses_d014_controller_and_rejects_non_d014_seed() -> None:
    with pytest.raises(ValueError):
        build_d014_development_visualization(seed=18346, horizon=1)
    source = inspect.getsource(d014.D014Controller.act)
    assert "D014_FULL_ENERGY_THRESHOLD" in source
