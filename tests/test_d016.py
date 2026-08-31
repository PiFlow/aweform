"""Focused tests for the D-016 current-beacon observability audit."""

from __future__ import annotations

import inspect
from dataclasses import fields

import numpy as np
import pytest

from aweform import d011, d013, d014, d015, d016
from aweform.d003 import HOT_DEPART_THRESHOLD
from aweform.env import Action
from aweform.exp003 import (
    EXP003_BEACON_SCALE,
    BeaconObservation,
    EXP003StationConfig,
    beacon_signal,
)
from aweform.exp003_seed_policy import validate_exp003_development_seeds


def beacon_for_geometry(x: float, y: float) -> BeaconObservation:
    config = EXP003StationConfig()
    cosine = np.cos(config.sensor_angle)
    sine = np.sin(config.sensor_angle)

    def signal(probe_x: float, probe_y: float) -> float:
        return beacon_signal(
            float(np.hypot(x - probe_x, y - probe_y)),
            EXP003_BEACON_SCALE,
        )

    return BeaconObservation(
        left=signal(config.probe_distance * cosine, config.probe_distance * sine),
        forward=signal(config.probe_distance, 0.0),
        right=signal(config.probe_distance * cosine, -config.probe_distance * sine),
        charging_contact=False,
    )


def observation(contact: bool = True) -> d011.D011Observation:
    return d011.D011Observation(
        energy=0.4,
        beacon=BeaconObservation(0.2, 0.3, 0.5, contact),
        thermal=0.6,
    )


def test_d016_seed_declaration_and_exact_guards() -> None:
    seeds = d016.D016_DEFAULT_DEVELOPMENT_SEEDS
    assert seeds == (18353, 18354, 18355)
    assert validate_exp003_development_seeds(seeds) == seeds
    assert d016._validate_d016_development_seeds(seeds) == seeds
    with pytest.raises(ValueError, match="only predeclared development seeds"):
        d016._validate_d016_development_seeds((18352,))
    with pytest.raises(ValueError, match="reserved for a formal experiment"):
        d016._validate_d016_development_seeds((50001,))


def test_d016_uses_only_d014_controller_and_no_d013_or_d015_learner() -> None:
    assert issubclass(d014.D014Controller, d011.D011Controller)
    assert "d013" not in d016.__dict__
    assert "d015" not in d016.__dict__
    result = d016.run_d016_probe((18353,), horizon=1)
    assert result["programmed"]["controller"] == "D014Controller"
    assert result["learned"] == {
        "status": "none",
        "learner_instantiated": False,
    }


def test_d016_does_not_instantiate_any_historical_learner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ForbiddenPredictor:
        def __init__(self) -> None:
            raise AssertionError("D-016 must not instantiate a learner")

    monkeypatch.setattr(d013, "D013ActionConsequencePredictor", ForbiddenPredictor)
    result = d016.run_d016_probe((18353,), horizon=2)
    assert result["organism_boundary"] == {"reward": 0.0, "info": {}}


def test_d016_preserves_reward_info_and_exact_observation_contract() -> None:
    result = d016.run_d016_probe((18353,), horizon=2)
    assert result["organism_boundary"] == {"reward": 0.0, "info": {}}
    assert result["development_seeds"] == [18353]
    run = result["results"][0]
    assert run["transitions"] == 2
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


@pytest.mark.parametrize("position", ((0.2, 0.3), (-0.2, 0.3), (0.3, -0.2)))
def test_analytic_inverse_reconstructs_known_geometry_and_signs(
    position: tuple[float, float],
) -> None:
    geometry = d016.reconstruct_relative_geometry(
        beacon_for_geometry(*position),
        beacon_scale=0.25,
        probe_distance=0.1,
        sensor_angle=np.pi / 4.0,
    )
    assert geometry.x == pytest.approx(position[0], abs=1e-12)
    assert geometry.y == pytest.approx(position[1], abs=1e-12)


def test_inverse_has_no_evaluator_coordinate_inputs() -> None:
    parameters = inspect.signature(d016.reconstruct_relative_geometry).parameters
    assert tuple(parameters) == (
        "beacon",
        "beacon_scale",
        "probe_distance",
        "sensor_angle",
    )
    assert not any(
        name in parameters
        for name in ("position", "body_position", "station_position", "heading")
    )


def test_nominal_wait_and_turns_preserve_contact() -> None:
    geometry = d016.RelativeGeometry(0.1, 0.0)
    for action in (Action.WAIT, Action.TURN_LEFT, Action.TURN_RIGHT):
        assert d016.predict_nominal_next_contact(
            geometry,
            True,
            action,
            movement_distance=0.05,
            charging_radius=0.1,
        ) is True
        assert d016.predict_nominal_next_contact(
            geometry,
            False,
            action,
            movement_distance=0.05,
            charging_radius=0.1,
        ) is False


@pytest.mark.parametrize(
    ("x", "current_contact", "expected"),
    ((0.14, False, True), (-0.08, True, False), (0.08, False, True)),
)
def test_nominal_move_entry_exit_and_persistence(
    x: float, current_contact: bool, expected: bool
) -> None:
    assert d016.predict_nominal_next_contact(
        d016.RelativeGeometry(x, 0.0),
        current_contact,
        Action.MOVE_FORWARD,
        movement_distance=0.05,
        charging_radius=0.1,
    ) is expected


def test_nominal_move_persistence_inside_case() -> None:
    assert d016.predict_nominal_next_contact(
        d016.RelativeGeometry(0.02, 0.0),
        True,
        Action.MOVE_FORWARD,
        movement_distance=0.05,
        charging_radius=0.1,
    ) is True


def test_prediction_is_formed_before_actual_contact_is_read() -> None:
    prediction_formed = False
    original_predict = d016.predict_nominal_next_contact
    original_step = d016.D002ThermalStationEnv.step

    def predict(
        geometry: d016.RelativeGeometry,
        current_contact: bool,
        action: Action,
        *,
        movement_distance: float,
        charging_radius: float,
    ) -> bool:
        nonlocal prediction_formed
        prediction_formed = True
        return original_predict(
            geometry,
            current_contact,
            action,
            movement_distance=movement_distance,
            charging_radius=charging_radius,
        )

    def step(
        environment: d016.D002ThermalStationEnv, action: int
    ) -> tuple[np.ndarray, float, bool, bool, dict[str, object]]:
        assert prediction_formed
        return original_step(environment, action)

    # The wrapper only observes call order; it does not provide any diagnostic
    # to the controller or alter the physical transition.
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(d016, "predict_nominal_next_contact", predict)
    monkeypatch.setattr(d016.D002ThermalStationEnv, "step", step)
    try:
        d016.run_d016_probe((18353,), horizon=1)
    finally:
        monkeypatch.undo()


def test_clipped_motion_classification_uses_only_engineering_tolerance() -> None:
    assert d016._is_reduced_move(0.0499999999999, 0.05) is False
    assert d016._is_reduced_move(0.049, 0.05) is True


def test_runner_reports_clipped_moves_without_changing_d014_behavior() -> None:
    result = d016._run_seed(18353, horizon=120)
    motion = result["observability"]["realized_motion"]
    assert motion["clipped_reduced_moves"] > 0
    assert motion["full_nominal_moves"] + motion["clipped_reduced_moves"] == (
        result["action_counts"][Action.MOVE_FORWARD.name]
    )
    for record in result["observability"]["mismatch_diagnostics"]["records"]:
        assert "realized_forward_displacement" in record
        assert "achieved_displacement_prediction" in record


def test_d016_behavior_matches_d014_exactly_for_same_seed_and_horizon() -> None:
    reference = d014._run_seed(18353, horizon=120)
    diagnostic = d016._run_seed(18353, horizon=120)
    for key in (
        "transitions",
        "terminated",
        "truncated",
        "termination_reason",
        "energy_termination",
        "thermal_termination",
        "minimum_normalized_energy",
        "final_normalized_energy",
        "maximum_thermal_state",
        "final_thermal_state",
        "action_counts",
        "mode_occupancy",
        "mode_entry_counts",
        "successful_physical_charger_exits",
        "low_energy_seek_entries",
        "successful_charging_contact_reacquisitions",
        "completed_autonomous_regulation_cycles",
    ):
        assert diagnostic[key] == reference[key]


def test_d016_does_not_change_d013_or_d015_contracts() -> None:
    assert d013.D013_PLASTIC_STATE_DIMENSION == 84
    assert d015.D015_DEFAULT_DEVELOPMENT_SEEDS == (18350, 18351, 18352)
    controller = d014.D014Controller(np.random.default_rng(7))
    assert controller.act(
        d011.D011Observation(
            energy=1.0,
            beacon=BeaconObservation(0.2, 0.3, 0.5, True),
            thermal=HOT_DEPART_THRESHOLD - 0.01,
        )
    ) is Action.MOVE_FORWARD
