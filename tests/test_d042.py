from __future__ import annotations

import inspect
import math

import numpy as np
import pytest

from aweform import d020, d024, d026, d027, d042
from aweform.env import Action


def _environment(**options: object) -> d042.D042Env:
    environment = d042.D042Env()
    environment.reset(options=options)
    return environment


def test_d042_canonical_turn_is_five_degrees_without_scaling_time_or_power() -> None:
    assert d042.D042_TURN_ANGLE == math.pi / 36.0
    assert d042.D042_TURN_ANGLE_DEGREES == 5.0
    environment = _environment(body_position=(0.1, 0.1), station_center=(0.9, 0.9))

    environment.step(Action.TURN_LEFT)
    assert environment.body is not None
    assert environment.body.heading == pytest.approx(math.pi / 36.0)
    assert environment.last_transition is not None
    transition = environment.last_transition
    assert transition.step_index == 1
    assert transition.actuator_electrical_power_w == pytest.approx(0.65)
    assert transition.total_electrical_load_w == pytest.approx(0.80)
    assert transition.battery_after_j == pytest.approx(2663.920)


def test_nine_turns_preserve_one_action_per_point_one_second_accounting() -> None:
    environment = _environment(body_position=(0.1, 0.1), station_center=(0.9, 0.9))
    electrical_energy = 0.0
    for _ in range(9):
        environment.step(Action.TURN_LEFT)
        assert environment.last_transition is not None
        electrical_energy += (
            environment.last_transition.actuator_electrical_power_w
            * environment.config.dt_seconds
        )

    assert environment.body is not None
    assert environment.body.heading == pytest.approx(math.pi / 4.0)
    assert environment.last_transition is not None
    assert environment.last_transition.step_index == 9
    assert electrical_energy == pytest.approx(9 * 0.65 * 0.1)
    assert environment.last_transition.battery_after_j == pytest.approx(
        2664.0 - 9 * (0.15 + 0.65) * 0.1
    )


def test_front_contact_coordinates_rotate_and_translate_in_body_frame() -> None:
    contacts = d042.body_front_contacts_world((0.1, 0.2), math.pi / 2.0)
    assert contacts[0] == pytest.approx((0.075, 0.25))
    assert contacts[1] == pytest.approx((0.125, 0.25))


def test_exact_front_docked_pose_has_both_corresponding_contacts() -> None:
    assert d042.body_front_contacts_world(
        d042.D042_INITIAL_BODY_CENTER, d042.D042_INITIAL_HEADING
    ) == ((0.50, 0.525), (0.50, 0.475))
    assert d042.dock_contacts_world(d042.D042_STATION_CENTER) == (
        (0.50, 0.525),
        (0.50, 0.475),
    )
    assert d042.has_dual_contact(
        d042.D042_INITIAL_BODY_CENTER,
        d042.D042_INITIAL_HEADING,
        d042.D042_STATION_CENTER,
    ) is True
    environment = _environment(
        body_position=d042.D042_INITIAL_BODY_CENTER,
        station_center=d042.D042_STATION_CENTER,
        heading=d042.D042_INITIAL_HEADING,
        battery_j=d042.D042_INITIAL_BATTERY_J,
        body_temperature_c=d042.D042_INITIAL_TEMPERATURE_C,
    )
    assert environment.charging_contact is True


def test_front_contact_requires_both_pairs_and_preserves_correspondence() -> None:
    raw_plus, _ = d042.body_front_contacts_world((0.0, 0.0), 0.8)
    dock_plus, _ = d042.dock_contacts_world((0.0, 0.0))
    body_center = (dock_plus[0] - raw_plus[0], dock_plus[1] - raw_plus[1])
    plus_error, minus_error = d042.dual_contact_pair_errors(
        body_center, 0.8, (0.0, 0.0)
    )
    assert plus_error == pytest.approx(0.0)
    assert minus_error > d042.D042_CONTACT_TOLERANCE
    assert d042.has_dual_contact(body_center, 0.8, (0.0, 0.0)) is False

    swapped_body_contacts = d042.body_front_contacts_world(
        (0.55, 0.50), math.pi
    )
    dock_contacts = d042.dock_contacts_world((0.50, 0.50))
    assert swapped_body_contacts[0] == pytest.approx(dock_contacts[1])
    assert swapped_body_contacts[1] == pytest.approx(dock_contacts[0])
    assert d042.has_dual_contact((0.55, 0.50), math.pi, (0.50, 0.50)) is False


def test_front_contact_tolerance_is_inclusive_and_rejects_outside_and_rear_pose(
) -> None:
    assert d042._within_contact_tolerance(d042.D042_CONTACT_TOLERANCE) is True
    just_outside = math.nextafter(d042.D042_CONTACT_TOLERANCE, math.inf)
    assert d042._within_contact_tolerance(just_outside) is False

    almost_boundary_center = (
        math.nextafter(math.nextafter(0.46, -math.inf), -math.inf),
        0.50,
    )
    assert d042.has_dual_contact(
        almost_boundary_center, 0.0, d042.D042_STATION_CENTER
    ) is True

    outside_center = (
        d042.D042_INITIAL_BODY_CENTER[0] + d042.D042_CONTACT_TOLERANCE + 0.000001,
        0.50,
    )
    assert d042.has_dual_contact(outside_center, 0.0, d042.D042_STATION_CENTER) is False
    assert d042.has_dual_contact((0.55, 0.50), 0.0, d042.D042_STATION_CENTER) is False


def test_beacon_and_observation_reward_info_contracts_are_unchanged() -> None:
    options = {
        "body_position": (0.25, 0.37),
        "station_center": (0.72, 0.61),
        "heading": 0.41,
    }
    d020_environment = d020.D020Env()
    d042_environment = d042.D042Env()
    d020_observation, d020_info = d020_environment.reset(options=options)
    d042_observation, d042_info = d042_environment.reset(options=options)
    assert np.array_equal(d020_observation[:4], d042_observation[:4])
    assert d020_info == d042_info == {}
    assert d042_observation.shape == (6,)
    assert d042_environment.observation_space.shape == (6,)

    next_observation, reward, terminated, truncated, info = d042_environment.step(
        Action.WAIT
    )
    assert next_observation.shape == (6,)
    assert (reward, terminated, truncated, info) == (0.0, False, False, {})


def test_canonical_controller_learner_and_rng_contracts_are_reused() -> None:
    assert d042.d026.D026Controller is d026.D026Controller
    assert (
        d042.d027.D027ActionConsequencePredictor
        is d027.D027ActionConsequencePredictor
    )
    assert "front_beacon_receptors" not in inspect.getsource(d042)
    first = d042._run_d042_seed(19042, horizon=200)
    second = d042._run_d042_seed(19042, horizon=200)
    assert first == second
    assert first["transitions"] == 200
    assert first["truncated"] is True
    assert first["initial_dual_contact"] is True


def test_historical_d024_replay_and_rear_defaults_remain_untouched() -> None:
    assert d020.D020PhysicalConfig().turn_angle == math.pi / 4.0
    assert d024.D024_REAR_X == -0.05
    assert d024.D024_INITIAL_BODY_CENTER == (0.55, 0.50)
    historical_first = d024._run_d024_seed(18365, horizon=200)
    historical_second = d024._run_d024_seed(18365, horizon=200)
    assert historical_first == historical_second
    assert historical_first["initial_pose"]["initial_dual_contact"] is True
    assert historical_first["initial_pose"]["body_center"] == [0.55, 0.5]
