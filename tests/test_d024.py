from __future__ import annotations

import inspect
import math
from dataclasses import asdict

import numpy as np
import pytest

from aweform import d021, d024
from aweform.d020 import D020Env
from aweform.env import Action
from aweform.exp003_seed_policy import validate_exp003_development_seeds


def _env(environment: D020Env, **options: object) -> D020Env:
    environment.reset(options=options)
    return environment


def test_d024_geometry_and_exact_initial_pose() -> None:
    assert d024.D024_BODY_LENGTH == 0.10
    assert d024.D024_BODY_WIDTH == 0.08
    assert d024.D024_REAR_X == -0.05
    assert d024.D024_CONTACT_LATERAL_OFFSET == 0.025
    assert d024.D024_DOCK_ORIENTATION == 0.0
    assert d024.D024_CONTACT_TOLERANCE == 0.01
    assert d024.body_rear_contacts_world(
        d024.D024_INITIAL_BODY_CENTER, d024.D024_INITIAL_HEADING
    ) == ((0.50, 0.525), (0.50, 0.475))
    assert d024.dock_contacts_world(d024.D024_STATION_CENTER) == (
        (0.50, 0.525),
        (0.50, 0.475),
    )
    environment = d024.D024Env()
    observation, info = environment.reset(
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
    assert observation.shape == (6,)
    assert observation[0] == 1.0
    assert observation[4] == 1.0
    assert observation[5] == pytest.approx(0.2875)


def test_d024_predicate_is_inclusive_and_correspondence_is_not_swappable() -> None:
    for shift, expected in ((0.009999, True), (0.010001, False)):
        body_center = (d024.D024_INITIAL_BODY_CENTER[0] + shift, 0.50)
        assert d024.has_dual_contact(
            body_center, 0.0, d024.D024_STATION_CENTER
        ) is expected

    boundary_body_center = (0.56, 0.50)
    boundary_errors = d024.dual_contact_pair_errors(
        boundary_body_center, 0.0, d024.D024_STATION_CENTER
    )
    assert boundary_errors == pytest.approx((0.01, 0.01))
    assert d024.has_dual_contact(
        boundary_body_center, 0.0, d024.D024_STATION_CENTER
    ) is True

    heading = 0.8
    raw_plus, _ = d024.body_rear_contacts_world((0.0, 0.0), heading)
    dock_plus, _ = d024.dock_contacts_world((0.0, 0.0))
    body_center = (
        dock_plus[0] - raw_plus[0],
        dock_plus[1] - raw_plus[1],
    )
    plus_error, minus_error = d024.dual_contact_pair_errors(
        body_center, heading, (0.0, 0.0)
    )
    assert plus_error == pytest.approx(0.0)
    assert minus_error > d024.D024_CONTACT_TOLERANCE
    assert d024.has_dual_contact(body_center, heading, (0.0, 0.0)) is False


def test_d024_seek_diagnostics_preserve_first_minimum_and_mode_provenance() -> None:
    tied_errors = d024.dual_contact_pair_errors(
        (0.56, 0.50), 0.0, d024.D024_STATION_CENTER
    )
    episode: dict[str, object] = {
        "minimum_rear_plus_pair_error_during_seek": tied_errors[0],
        "minimum_rear_minus_pair_error_during_seek": tied_errors[1],
        "minimum_max_pair_error_during_seek": max(tied_errors),
        "minimum_max_pair_error_during_seek_record": {
            "transition": 7,
        },
        "one_pair_only_tolerance_events": 0,
    }
    d024._update_seek_geometry(
        episode,
        position=(0.56, 0.50),
        heading=0.0,
        station=d024.D024_STATION_CENTER,
        transition_index=8,
    )
    assert episode["minimum_max_pair_error_during_seek_record"] == {
        "transition": 7,
    }

    result = d024._run_d024_seed(18367, horizon=25_000)
    assert result["initial_full_departure_transition"] == 1
    assert result["first_dual_contact_loss_after_departure_transition"] == 1
    dual_entry = result["pair_error_diagnostics"]["dual_contact_entry_records"][0]
    assert dual_entry["controller_mode_before_action"] == "AWAY"
    assert dual_entry["controller_mode_after_action"] == "AWAY"
    assert dual_entry["controller_mode_at_entry"] == "AWAY"
    seek_episode = result["seek_episodes"][0]
    minimum_record = seek_episode["minimum_max_pair_error_during_seek_record"]
    assert minimum_record["transition"] >= seek_episode["seek_entry_transition"]
    assert minimum_record["value"] == seek_episode[
        "minimum_max_pair_error_during_seek"
    ]
    assert set(
        ("body_center", "heading", "rear_plus_pair_error", "rear_minus_pair_error")
    ) <= minimum_record.keys()
    legacy = result["legacy_circular_contact_without_dual"]
    assert legacy["seek_transition_count"] > 0
    assert legacy["seek_entry_records"]
    assert all(
        record["controller_mode_at_entry"] == "SEEK"
        for record in legacy["seek_entry_records"]
    )


def test_first_move_loses_initial_contact_and_preserves_kinematics() -> None:
    environment = d024.D024Env()
    environment.reset(
        options={
            "body_position": d024.D024_INITIAL_BODY_CENTER,
            "station_center": d024.D024_STATION_CENTER,
            "heading": 0.0,
            "battery_j": d024.D024_INITIAL_BATTERY_J,
            "body_temperature_c": 23.0,
        }
    )
    _, reward, terminated, truncated, info = environment.step(Action.MOVE_FORWARD)
    assert (reward, terminated, truncated, info) == (0.0, False, False, {})
    assert environment.last_transition is not None
    transition = environment.last_transition
    assert transition.charging_contact_before is True
    assert transition.charging_contact_after is False
    assert transition.position_after == pytest.approx((0.60, 0.50))
    assert transition.actual_stored_power_w == 0.0

    clamped = _env(
        d024.D024Env(),
        body_position=(0.99, 0.99),
        station_center=(0.1, 0.1),
        heading=math.pi / 4.0,
    )
    clamped.step(Action.MOVE_FORWARD)
    assert clamped.body is not None
    assert clamped.body.position == pytest.approx((1.0, 1.0))


def test_legacy_circular_contact_alone_never_charges_d024() -> None:
    d024_environment = _env(
        d024.D024Env(),
        body_position=d024.D024_STATION_CENTER,
        station_center=d024.D024_STATION_CENTER,
        battery_j=2664.0,
        heading=0.0,
    )
    assert d024.legacy_circular_contact(
        d024.D024_STATION_CENTER, d024.D024_STATION_CENTER, d024_environment.config
    ) is True
    assert d024_environment.charging_contact is False
    d024_environment.step(Action.WAIT)
    assert d024_environment.last_transition is not None
    assert d024_environment.last_transition.actual_stored_power_w == 0.0
    assert d024_environment.last_transition.charge_phase.value == "OFF"


def test_d024_inherits_d020_physics_and_boundary_unchanged_off_dock() -> None:
    first = _env(
        D020Env(), body_position=(0.1, 0.1), station_center=(0.9, 0.9)
    )
    second = _env(
        d024.D024Env(), body_position=(0.1, 0.1), station_center=(0.9, 0.9)
    )
    for action in (
        Action.WAIT,
        Action.TURN_LEFT,
        Action.TURN_RIGHT,
        Action.MOVE_FORWARD,
    ):
        first_observation = first.step(action)
        second_observation = second.step(action)
        assert np.array_equal(first_observation[0], second_observation[0])
        assert first_observation[1:] == second_observation[1:]
        assert first.last_transition is not None
        assert second.last_transition is not None
        assert asdict(first.last_transition) == asdict(second.last_transition)


def test_d024_reuses_actual_d021_controller_without_temperature_influence() -> None:
    assert d024.d021.D021Controller is d021.D021Controller
    source = inspect.getsource(d021.D021Controller)
    assert "D024" not in source
    assert "thermal" not in inspect.getsource(d021.D021Controller.act)
    assert "controller = d021.D021Controller" in inspect.getsource(d024._run_d024_seed)
    assert "dual_contact_pair_errors" not in inspect.getsource(d021.D021Controller)


def test_d024_seed_guard_and_fixed_horizon() -> None:
    assert d024.D024_HORIZON == 70_000
    assert d024.D024_DEFAULT_DEVELOPMENT_SEEDS == (18365, 18366, 18367)
    assert validate_exp003_development_seeds(d024.D024_DEFAULT_DEVELOPMENT_SEEDS) == (
        18365,
        18366,
        18367,
    )
    assert d024._validate_d024_development_seeds(
        d024.D024_DEFAULT_DEVELOPMENT_SEEDS
    ) == d024.D024_DEFAULT_DEVELOPMENT_SEEDS
    with pytest.raises(ValueError, match="requires exactly"):
        d024._validate_d024_development_seeds((18365,))
    with pytest.raises(ValueError, match="reserved for a formal experiment"):
        d024._validate_d024_development_seeds((50001, 50002, 50003))


def test_d024_short_same_seed_replay_and_evaluator_only_diagnostics() -> None:
    first = d024._run_d024_seed(18365, horizon=200)
    second = d024._run_d024_seed(18365, horizon=200)
    assert first == second
    assert first["transitions"] == 200
    assert first["initial_pose"]["initial_dual_contact"] is True
    assert first["failure_and_censoring"]["horizon_truncation"] is True
    assert first["seek_episodes"] == []
    assert first["legacy_circular_contact_without_dual"]["transition_count"] >= 0


def test_d024_public_manifest_declares_six_channels_and_zero_boundary() -> None:
    manifest = d024.run_d024_probe
    assert inspect.signature(manifest).parameters.keys() == {"executed_commit_sha"}
    assert d024.D024_AUTHORITATIVE_BASE_SHA == (
        "c0ce8182d0fba97035d76899e5b188ca7f171b05"
    )
    # Avoid a 210,000-transition test here; the executable manifest is checked
    # by the frozen artifact generation after the implementation commit.
    source = inspect.getsource(d024.run_d024_probe)
    assert "D024_HORIZON" in source
    assert "organism_boundary" in source
