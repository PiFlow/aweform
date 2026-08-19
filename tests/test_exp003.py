from __future__ import annotations

import copy
import math
from dataclasses import fields, replace

import matplotlib.pyplot as plt
import numpy as np
import pytest

from aweform import (
    EXP003_CALIBRATION_SEEDS,
    EXP003_CHARGE_RATE,
    EXP003_CHARGING_RADIUS,
    EXP003_CONFIRMATORY_SEEDS,
    FROZEN_EXP001_CALIBRATION_ENV_CONFIG,
    Action,
    BeaconObservation,
    EXP003Mode,
    EXP003StationConfig,
    ExternalObservation,
    LocalizedChargingStationEnv,
    StationB50Controller,
    StationObservation,
    StochasticPersistentExplorer,
    beacon_signal,
    exp003_controller_observation,
    run_exp003_development_comparison,
    sample_directional_beacon,
    validate_exp003_development_seeds,
)
from aweform.exp001 import policy_rng_from_seed
from aweform.exp002_protocol import (
    EXP002BCandidate,
)
from aweform.exp002_runner import run_exp002_development_batch
from aweform.exp003_runner import _run_station_episode, summarize_exp003_episode
from aweform.exp003_visualizer import (
    _format_field_frame,
    _format_station_frame,
    build_exp003_visualization_figure,
    build_exp003_visualization_frames,
    exp003_energy_visibility_label,
)


def _station_observation(
    energy: float,
    *,
    beacon: tuple[float, float, float] = (0.1, 0.9, 0.2),
    contact: bool = False,
) -> StationObservation:
    return StationObservation(
        energy=energy,
        beacon=BeaconObservation(*beacon, charging_contact=contact),
    )


def _manual_env(**kwargs: object) -> LocalizedChargingStationEnv:
    config = EXP003StationConfig(episode_horizon=4, **kwargs)
    env = LocalizedChargingStationEnv(config)
    env.reset(seed=18003)
    assert env.body is not None
    assert env.station_center is not None
    return env


def test_exp003_development_values_and_fresh_reservations_are_exact() -> None:
    config = EXP003StationConfig()

    assert config.charging_radius == EXP003_CHARGING_RADIUS == 0.10
    assert config.charge_rate == EXP003_CHARGE_RATE == 0.5
    assert config.beacon_scale == 0.25
    assert config.episode_horizon == 1000
    assert EXP003_CALIBRATION_SEEDS == tuple(range(60001, 60201))
    assert EXP003_CONFIRMATORY_SEEDS == tuple(range(70001, 71001))
    assert not set(EXP003_CALIBRATION_SEEDS) & set(EXP003_CONFIRMATORY_SEEDS)


@pytest.mark.parametrize(
    "seed",
    [
        20001,
        30001,
        40001,
        50001,
        60001,
        70001,
    ],
)
def test_no_existing_or_exp003_reserved_seed_enters_development(seed: int) -> None:
    with pytest.raises(ValueError):
        validate_exp003_development_seeds([seed])


def test_station_center_is_inside_valid_rectangle_and_not_initially_on_charger(
) -> None:
    env = LocalizedChargingStationEnv()
    env.reset(seed=18003)

    assert env.body is not None
    assert env.station_center is not None
    x, y = env.station_center
    assert EXP003_CHARGING_RADIUS <= x <= 1.0 - EXP003_CHARGING_RADIUS
    assert EXP003_CHARGING_RADIUS <= y <= 1.0 - EXP003_CHARGING_RADIUS
    assert math.dist(env.body.position, env.station_center) > 0.20
    assert env.charging_contact is False


def test_outside_charger_has_exactly_zero_harvest() -> None:
    env = _manual_env()
    assert env.body is not None
    assert env.station_center is not None
    env.body.x, env.body.y = 0.1, 0.1
    env.station_center = (0.8, 0.8)

    _, _, _, _, _ = env.step(Action.WAIT)

    assert env.last_transition is not None
    assert env.last_transition.harvested_energy == 0.0
    assert env.body.energy == pytest.approx(4.9)


def test_inside_charger_gets_fixed_input_and_ordinary_costs_apply() -> None:
    env = _manual_env()
    assert env.body is not None
    env.body.x, env.body.y = 0.5, 0.5
    env.station_center = (0.5, 0.5)

    env.step(Action.WAIT)

    assert env.last_transition is not None
    assert env.last_transition.charging_contact_after is True
    assert env.last_transition.harvested_energy == 0.5
    assert env.body.energy == pytest.approx(5.4)


def test_outside_to_inside_move_charges_on_the_same_transition() -> None:
    env = _manual_env(movement_distance=0.1)
    assert env.body is not None
    env.body.x, env.body.y, env.body.heading = 0.1, 0.5, 0.0
    env.station_center = (0.25, 0.5)
    assert env.charging_contact is False

    env.step(Action.MOVE_FORWARD)

    assert env.body.position == pytest.approx((0.2, 0.5))
    assert env.last_transition is not None
    assert env.last_transition.charging_contact_before is False
    assert env.last_transition.charging_contact_after is True
    assert env.last_transition.harvested_energy == 0.5


def test_outside_pass_through_move_ends_outside_without_harvest() -> None:
    env = _manual_env(movement_distance=0.3)
    assert env.body is not None
    env.body.x, env.body.y, env.body.heading = 0.1, 0.5, 0.0
    env.station_center = (0.25, 0.5)
    assert env.charging_contact is False

    env.step(Action.MOVE_FORWARD)

    assert env.body.position == pytest.approx((0.4, 0.5))
    assert env.last_transition is not None
    assert env.last_transition.charging_contact_before is False
    assert env.last_transition.charging_contact_after is False
    assert env.last_transition.harvested_energy == 0.0


def test_beacon_is_deterministic_monotonic_and_rng_free() -> None:
    assert beacon_signal(0.0) == 1.0
    assert beacon_signal(0.1) > beacon_signal(0.2) > beacon_signal(0.3)
    first = np.random.default_rng(18003)
    second = np.random.default_rng(18003)
    state = copy.deepcopy(first.bit_generator.state)
    body = LocalizedChargingStationEnv().reset(seed=18003)
    del body
    env = LocalizedChargingStationEnv()
    env.reset(seed=18003)
    assert env.body is not None
    sample_directional_beacon(
        env.body,
        (0.5, 0.5),
        probe_distance=0.1,
        sensor_angle=math.pi / 4,
    )
    assert first.bit_generator.state == state
    np.testing.assert_array_equal(first.random(8), second.random(8))


def test_charging_contact_matches_closed_physical_zone_boundary() -> None:
    env = _manual_env()
    assert env.body is not None
    env.station_center = (0.5, 0.5)
    env.body.x, env.body.y = 0.6, 0.5
    assert env.charging_contact is True
    env.body.x = 0.600001
    assert env.charging_contact is False


def test_controller_boundary_contains_only_energy_beacon_and_contact() -> None:
    observation = exp003_controller_observation(
        np.asarray([0.4, 0.1, 0.2, 0.3, 1.0], dtype=np.float32)
    )
    expected = _station_observation(0.4, beacon=(0.1, 0.2, 0.3), contact=True)
    assert observation.energy == pytest.approx(expected.energy)
    assert observation.beacon.charging_contact is expected.beacon.charging_contact
    assert observation.beacon.left == pytest.approx(expected.beacon.left)
    assert observation.beacon.forward == pytest.approx(expected.beacon.forward)
    assert observation.beacon.right == pytest.approx(expected.beacon.right)
    assert {field.name for field in fields(StationObservation)} == {
        "energy",
        "beacon",
    }
    assert {field.name for field in fields(BeaconObservation)} == {
        "left",
        "forward",
        "right",
        "charging_contact",
    }
    assert not any(
        name in repr(observation)
        for name in ("station_center", "distance", "coverage")
    )


def test_controller_thresholds_and_contact_docking_semantics() -> None:
    controller = StationB50Controller(policy_rng_from_seed(18003))
    controller.act(_station_observation(0.50))
    assert controller.mode is EXP003Mode.EXPLORE
    controller.act(_station_observation(0.499, beacon=(1.0, 1.0, 1.0)))
    assert controller.mode is EXP003Mode.SEEK
    controller.act(_station_observation(0.499, beacon=(1.0, 1.0, 1.0)))
    assert controller.mode is EXP003Mode.SEEK
    controller.act(_station_observation(0.499, beacon=(0.0, 1.0, 0.0), contact=True))
    assert controller.mode is EXP003Mode.CHARGE


def test_controller_lost_contact_returns_to_seek_and_recovery_is_strictly_above(
) -> None:
    controller = StationB50Controller(policy_rng_from_seed(18004))
    controller.act(_station_observation(0.4))
    controller.act(_station_observation(0.4, contact=True))
    assert controller.mode is EXP003Mode.CHARGE
    controller.act(_station_observation(0.85, contact=True))
    assert controller.mode is EXP003Mode.CHARGE
    controller.act(_station_observation(0.85, contact=False))
    assert controller.mode is EXP003Mode.SEEK
    controller.act(_station_observation(0.851, contact=True))
    assert controller.mode is EXP003Mode.CHARGE


def test_exploration_primitive_actions_match_historical_primitive() -> None:
    historical = StochasticPersistentExplorer(policy_rng_from_seed(18005))
    station = StationB50Controller(policy_rng_from_seed(18005))
    external = ExternalObservation(0.2, 0.4, 0.1)
    beacon = _station_observation(
        0.9,
        beacon=(
            external.left_resource,
            external.forward_resource,
            external.right_resource,
        ),
    )
    assert [historical.act(external) for _ in range(128)] == [
        station.act(beacon) for _ in range(128)
    ]


def test_environment_and_policy_rngs_are_independent() -> None:
    first = LocalizedChargingStationEnv()
    second = LocalizedChargingStationEnv()
    first.reset(seed=18006)
    second.reset(seed=18006)
    assert first.random_streams is not None
    assert second.random_streams is not None
    expected = second.random_streams.policy.random(8)
    first.step(Action.MOVE_FORWARD)
    actual = first.random_streams.policy.random(8)
    np.testing.assert_array_equal(actual, expected)


def test_repeated_ordinary_seed_reproduces_full_comparison_and_diagnostics() -> None:
    first = run_exp003_development_comparison([18007])
    second = run_exp003_development_comparison([18007])
    assert first == second


def test_evaluator_diagnostics_do_not_change_recorded_controller_actions() -> None:
    episode = _run_station_episode(18008, EXP003StationConfig(episode_horizon=40))
    before = tuple(
        transition.privileged_evaluator.action for transition in episode.transitions
    )
    summarize_exp003_episode(episode, EXP003StationConfig(episode_horizon=40))
    after = tuple(
        transition.privileged_evaluator.action for transition in episode.transitions
    )
    assert after == before


def test_successful_acquisition_energy_is_before_charge_input() -> None:
    config = EXP003StationConfig(episode_horizon=1000)
    episode = _run_station_episode(18011, config)
    diagnostics = summarize_exp003_episode(episode, config)

    successful = [
        attempt
        for attempt in diagnostics.seek_attempts
        if attempt.reached_charging_contact
    ]
    assert successful
    for attempt in successful:
        assert attempt.transitions_to_charging_contact is not None
        acquisition_index = (
            attempt.onset_step
            - 1
            + attempt.transitions_to_charging_contact
            - 1
        )
        evaluator = episode.transitions[acquisition_index].privileged_evaluator
        expected_before = (
            evaluator.actual_energy_before - config.energy.failure_boundary
        ) / (config.energy.maximum_energy - config.energy.failure_boundary)
        assert attempt.normalized_energy_before_acquisition == pytest.approx(
            expected_before
        )
        assert evaluator.charging_contact_after is True
        assert evaluator.harvested_energy == 0.5
        assert evaluator.actual_energy_after > evaluator.actual_energy_before


def test_visualizer_background_extents_are_explicit_xy_bounds() -> None:
    result = run_exp003_development_comparison([18012])
    figure, animation = build_exp003_visualization_figure(result, seed=18012)
    try:
        assert figure.axes[0].images[0].get_extent() == [0.0, 1.0, 0.0, 1.0]
        assert figure.axes[1].images[0].get_extent() == [0.0, 1.0, 0.0, 1.0]
    finally:
        animation.event_source.stop()
        plt.close(figure)


def test_visualizer_terminal_and_padded_energy_are_evaluator_only() -> None:
    result = run_exp003_development_comparison([18013])
    data = build_exp003_visualization_frames(result, seed=18013)
    ordinary = data.station_frames[0]
    terminal = data.station_frames[-1]
    padded = replace(terminal, is_padded=True)

    assert ordinary.controller_visible_energy is not None
    assert exp003_energy_visibility_label(ordinary) == "CTRL + EVAL"
    assert terminal.controller_visible_energy is None
    assert (
        exp003_energy_visibility_label(terminal)
        == "EVALUATOR ONLY — no next controller observation"
    )
    assert (
        exp003_energy_visibility_label(padded)
        == "EVALUATOR ONLY — no next controller observation"
    )
    assert "EVALUATOR ONLY — no next controller observation" in (
        _format_station_frame(terminal)
    )
    assert "EVALUATOR ONLY — no next controller observation" in (
        _format_field_frame(data.field_frames[-1])
    )
    assert "station distance:" in _format_station_frame(terminal)
    assert "[EVALUATOR ONLY]" in _format_station_frame(terminal)


def test_field_b50_reference_uses_unchanged_historical_exp002_path() -> None:
    seed = 18009
    historical = run_exp002_development_batch(
        [seed], FROZEN_EXP001_CALIBRATION_ENV_CONFIG, EXP002BCandidate.B50
    )
    historical_b = next(
        episode
        for episode in historical.episodes
        if episode.condition.value == "B_INTEROCEPTIVE_HOMEOSTASIS"
    )
    comparison = run_exp003_development_comparison([seed])
    assert comparison.field_environment_config == FROZEN_EXP001_CALIBRATION_ENV_CONFIG
    assert comparison.field_b50_episodes == (historical_b,)
    assert comparison.field_b50_episodes[0].initial_state.position == (
        comparison.station_b50_episodes[0].initial_state.position
    )
    assert comparison.field_b50_episodes[0].initial_state.heading == (
        comparison.station_b50_episodes[0].initial_state.heading
    )


def test_station_runner_exposes_evaluator_metrics_but_empty_info_boundary() -> None:
    comparison = run_exp003_development_comparison([18010])
    episode = comparison.station_b50_episodes[0]
    assert episode.initial_state.station_center
    assert episode.transitions
    visible = episode.transitions[0].controller_visible.observation
    assert isinstance(visible, StationObservation)
    evaluator = episode.transitions[0].privileged_evaluator
    assert hasattr(evaluator, "position_before")
    assert hasattr(evaluator, "charging_contact_after")
    assert not hasattr(visible, "station_center")
    assert not hasattr(visible, "coverage_fraction")
