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
from aweform.exp003_runner import (
    EXP003ControllerStep,
    EXP003EpisodeRecord,
    EXP003EvaluatorInitialState,
    EXP003EvaluatorStep,
    EXP003SeekOutcome,
    EXP003TransitionRecord,
    _run_station_episode,
    _seek_feasibility_metrics,
    summarize_exp003_episode,
)
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


def _synthetic_transition(
    step: int,
    *,
    action: Action,
    position_before: tuple[float, float],
    position_after: tuple[float, float],
    heading: float = 0.0,
    energy_before: float = 4.9,
    energy_after: float = 4.8,
    harvested_energy: float = 0.0,
    basal_cost: float = 0.1,
    action_cost: float = 0.0,
    charging_contact_before: bool = False,
    charging_contact_after: bool = False,
    controller_mode_before_action: EXP003Mode = EXP003Mode.SEEK,
    controller_mode: EXP003Mode = EXP003Mode.SEEK,
    visible_observation: StationObservation | None = None,
    terminated: bool = False,
    truncated: bool = False,
) -> EXP003TransitionRecord:
    evaluator = EXP003EvaluatorStep(
        step_index=step,
        action=action,
        position_before=position_before,
        position_after=position_after,
        heading=heading,
        actual_energy_before=energy_before,
        actual_energy_after=energy_after,
        harvested_energy=harvested_energy,
        basal_cost=basal_cost,
        action_cost=action_cost,
        charging_contact_before=charging_contact_before,
        charging_contact_after=charging_contact_after,
        controller_mode_before_action=controller_mode_before_action,
        controller_mode=controller_mode,
        terminated=terminated,
        truncated=truncated,
    )
    return EXP003TransitionRecord(
        controller_visible=EXP003ControllerStep(
            visible_observation or _station_observation(0.49)
        ),
        privileged_evaluator=evaluator,
    )


def _synthetic_episode(
    transitions: tuple[EXP003TransitionRecord, ...],
    *,
    station_center: tuple[float, float] = (0.5, 0.5),
) -> EXP003EpisodeRecord:
    first = transitions[0].privileged_evaluator
    return EXP003EpisodeRecord(
        environment_seed=18003,
        initial_state=EXP003EvaluatorInitialState(
            position=first.position_before,
            heading=first.heading,
            actual_energy=5.0,
            station_center=station_center,
        ),
        transitions=transitions,
    )


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
    assert _run_station_episode(
        18008, EXP003StationConfig(episode_horizon=40)
    ) == episode


def test_seek_feasibility_bound_is_charge_aware_and_strict() -> None:
    config = EXP003StationConfig(movement_distance=0.3)
    negative = _seek_feasibility_metrics(
        actual_energy_at_onset=0.15,
        station_distance_at_onset=0.55,
        config=config,
    )
    assert negative.distance_to_charging_boundary == pytest.approx(0.45)
    assert negative.optimistic_minimum_forward_transitions == 2
    assert negative.optimistic_onset_reserve_threshold == pytest.approx(0.2)
    assert negative.available_onset_energy_above_failure == pytest.approx(0.15)
    assert negative.optimistic_reserve_margin == pytest.approx(-0.05)
    assert not negative.optimistically_feasible

    positive = _seek_feasibility_metrics(
        actual_energy_at_onset=1.0,
        station_distance_at_onset=0.2,
        config=config,
    )
    assert positive.distance_to_charging_boundary == pytest.approx(0.1)
    assert positive.optimistic_minimum_forward_transitions == 1
    assert positive.optimistic_onset_reserve_threshold == pytest.approx(0.0)
    assert positive.available_onset_energy_above_failure == pytest.approx(1.0)
    assert positive.optimistic_reserve_margin == pytest.approx(1.0)
    assert positive.optimistically_feasible

    zero_margin = _seek_feasibility_metrics(
        actual_energy_at_onset=0.2,
        station_distance_at_onset=0.55,
        config=config,
    )
    assert zero_margin.optimistic_reserve_margin == pytest.approx(0.0)
    assert not zero_margin.optimistically_feasible

    already_inside = _seek_feasibility_metrics(
        actual_energy_at_onset=0.35,
        station_distance_at_onset=0.05,
        config=config,
    )
    assert already_inside.distance_to_charging_boundary == pytest.approx(0.0)
    assert already_inside.optimistic_minimum_forward_transitions == 0
    assert already_inside.optimistic_onset_reserve_threshold == pytest.approx(0.0)
    assert already_inside.available_onset_energy_above_failure == pytest.approx(
        0.35
    )
    assert already_inside.optimistic_reserve_margin == pytest.approx(0.35)


def test_charge_aware_one_forward_acquisition_is_viable_below_nominal_cost() -> None:
    config = EXP003StationConfig(initial_energy=0.01, episode_horizon=1)
    environment = LocalizedChargingStationEnv(config)
    environment.reset(seed=18014)
    assert environment.body is not None
    environment.body.x = 0.45
    environment.body.y = 0.5
    environment.body.heading = 0.0
    environment.body.energy = 0.01
    environment.station_center = (0.60, 0.5)

    metrics = _seek_feasibility_metrics(
        actual_energy_at_onset=environment.body.energy,
        station_distance_at_onset=math.dist(
            environment.body.position, environment.station_center
        ),
        config=config,
    )
    assert metrics.optimistic_minimum_forward_transitions == 1
    assert metrics.available_onset_energy_above_failure < (
        config.energy.basal_cost + config.movement_cost
    )
    assert metrics.optimistically_feasible

    _, reward, terminated, truncated, _ = environment.step(Action.MOVE_FORWARD)
    assert reward == 0.0
    assert terminated is False
    assert truncated is True
    assert environment.last_transition is not None
    assert environment.last_transition.charging_contact_after is True
    assert environment.last_transition.harvested_energy == pytest.approx(0.5)
    assert environment.last_transition.energy_after == pytest.approx(0.31)


def test_seek_attempt_records_action_counts_and_nominal_cost_sums() -> None:
    diagnostics = summarize_exp003_episode(
        _synthetic_episode(
            (
                _synthetic_transition(
                    1,
                    action=Action.TURN_LEFT,
                    position_before=(0.2, 0.5),
                    position_after=(0.2, 0.5),
                    action_cost=0.02,
                    controller_mode_before_action=EXP003Mode.EXPLORE,
                    controller_mode=EXP003Mode.SEEK,
                ),
                _synthetic_transition(
                    2,
                    action=Action.MOVE_FORWARD,
                    position_before=(0.2, 0.5),
                    position_after=(0.25, 0.5),
                    action_cost=0.1,
                ),
                _synthetic_transition(
                    3,
                    action=Action.TURN_RIGHT,
                    position_before=(0.25, 0.5),
                    position_after=(0.25, 0.5),
                    action_cost=0.02,
                ),
                _synthetic_transition(
                    4,
                    action=Action.WAIT,
                    position_before=(0.25, 0.5),
                    position_after=(0.25, 0.5),
                    energy_before=0.2,
                    energy_after=0.0,
                    terminated=True,
                ),
            )
        )
    )
    attempt = diagnostics.seek_attempts[0]
    assert attempt.transitions_elapsed == 4
    assert attempt.move_forward_count == 1
    assert attempt.turn_left_count == 1
    assert attempt.turn_right_count == 1
    assert attempt.wait_count == 1
    assert attempt.nominal_basal_cost_sum == pytest.approx(0.4)
    assert attempt.nominal_action_cost_sum == pytest.approx(0.14)
    assert attempt.nominal_total_cost_sum == pytest.approx(0.54)
    assert attempt.pass_through_count == 0


def test_seek_realized_path_progress_and_nominal_overhead_diagnostics() -> None:
    diagnostics = summarize_exp003_episode(
        _synthetic_episode(
            (
                _synthetic_transition(
                    1,
                    action=Action.TURN_LEFT,
                    position_before=(0.79, 0.5),
                    position_after=(0.79, 0.5),
                    action_cost=0.02,
                    controller_mode_before_action=EXP003Mode.EXPLORE,
                    controller_mode=EXP003Mode.SEEK,
                ),
                _synthetic_transition(
                    2,
                    action=Action.MOVE_FORWARD,
                    position_before=(0.79, 0.5),
                    position_after=(0.74, 0.5),
                    action_cost=0.1,
                ),
                _synthetic_transition(
                    3,
                    action=Action.TURN_RIGHT,
                    position_before=(0.74, 0.5),
                    position_after=(0.74, 0.5),
                    action_cost=0.02,
                ),
                _synthetic_transition(
                    4,
                    action=Action.MOVE_FORWARD,
                    position_before=(0.74, 0.5),
                    position_after=(0.79, 0.5),
                    action_cost=0.1,
                ),
                _synthetic_transition(
                    5,
                    action=Action.TURN_LEFT,
                    position_before=(0.79, 0.5),
                    position_after=(0.79, 0.5),
                    action_cost=0.02,
                ),
                _synthetic_transition(
                    6,
                    action=Action.MOVE_FORWARD,
                    position_before=(0.79, 0.5),
                    position_after=(0.69, 0.5),
                    action_cost=0.1,
                ),
                _synthetic_transition(
                    7,
                    action=Action.WAIT,
                    position_before=(0.69, 0.5),
                    position_after=(0.69, 0.5),
                    energy_before=0.1,
                    energy_after=0.0,
                    terminated=True,
                ),
            ),
        )
    )
    attempt = diagnostics.seek_attempts[0]
    assert attempt.optimistic_minimum_forward_transitions == 4
    assert attempt.move_forward_count == 3
    assert attempt.realized_forward_distance == pytest.approx(0.2)
    assert attempt.transitions_elapsed == 7
    assert attempt.turn_count == 3
    assert attempt.turn_fraction == pytest.approx(3 / 7)
    assert attempt.actual_forward_to_ideal_transition_ratio == pytest.approx(0.75)
    assert attempt.realized_path_to_onset_boundary_ratio == pytest.approx(
        0.2 / 0.19
    )
    assert attempt.station_distance_trajectory == pytest.approx(
        (0.29, 0.29, 0.24, 0.24, 0.29, 0.29, 0.19, 0.19)
    )
    assert attempt.net_radial_progress_toward_station == pytest.approx(0.1)
    assert attempt.cumulative_inward_radial_progress == pytest.approx(0.15)
    assert attempt.cumulative_outward_radial_movement == pytest.approx(0.05)
    assert attempt.forward_actions_reducing_station_distance == 2
    assert attempt.forward_actions_increasing_station_distance == 1
    assert attempt.forward_inward_progress_fraction == pytest.approx(2 / 3)
    assert attempt.forward_outward_progress_fraction == pytest.approx(1 / 3)
    assert (
        attempt.max_consecutive_transitions_without_net_progress_toward_station
        == 3
    )
    assert attempt.idealized_nominal_straight_line_cost_demand == pytest.approx(0.8)
    assert attempt.nominal_total_cost_sum == pytest.approx(1.06)
    assert attempt.nominal_cost_demand_overhead == pytest.approx(0.26)
    assert attempt.realized_transition_demand_overhead == 3


def test_seek_path_ratios_and_forward_fractions_use_none_for_zero_denominators(
) -> None:
    diagnostics = summarize_exp003_episode(
        _synthetic_episode(
            (
                _synthetic_transition(
                    1,
                    action=Action.TURN_LEFT,
                    position_before=(0.55, 0.5),
                    position_after=(0.55, 0.5),
                    action_cost=0.02,
                    controller_mode_before_action=EXP003Mode.EXPLORE,
                    controller_mode=EXP003Mode.SEEK,
                    terminated=True,
                ),
            )
        )
    )
    attempt = diagnostics.seek_attempts[0]
    assert attempt.optimistic_minimum_forward_transitions == 0
    assert attempt.actual_forward_to_ideal_transition_ratio is None
    assert attempt.realized_path_to_onset_boundary_ratio is None
    assert attempt.forward_inward_progress_fraction is None
    assert attempt.forward_outward_progress_fraction is None
    assert attempt.realized_forward_distance == 0.0
    assert attempt.idealized_nominal_straight_line_cost_demand == 0.0


def test_seek_beacon_diagnostics_use_onset_and_previous_five_visible_observations(
) -> None:
    pre_values = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6)
    pre_transitions = tuple(
        _synthetic_transition(
            step,
            action=Action.WAIT,
            position_before=(0.8, 0.5),
            position_after=(0.8, 0.5),
            controller_mode_before_action=EXP003Mode.EXPLORE,
            controller_mode=EXP003Mode.EXPLORE,
            visible_observation=_station_observation(
                0.49, beacon=(value, value, value)
            ),
        )
        for step, value in enumerate(pre_values, start=1)
    )
    diagnostics = summarize_exp003_episode(
        _synthetic_episode(
            pre_transitions
            + (
                _synthetic_transition(
                    7,
                    action=Action.TURN_LEFT,
                    position_before=(0.8, 0.5),
                    position_after=(0.8, 0.5),
                    action_cost=0.02,
                    controller_mode_before_action=EXP003Mode.EXPLORE,
                    controller_mode=EXP003Mode.SEEK,
                    visible_observation=_station_observation(
                        0.49, beacon=(0.6, 0.4, 0.2)
                    ),
                ),
                _synthetic_transition(
                    8,
                    action=Action.WAIT,
                    position_before=(0.8, 0.5),
                    position_after=(0.8, 0.5),
                    energy_before=0.1,
                    energy_after=0.0,
                    terminated=True,
                ),
            )
        )
    )
    attempt = diagnostics.seek_attempts[0]
    assert attempt.onset_beacon_left == pytest.approx(0.6)
    assert attempt.onset_beacon_forward == pytest.approx(0.4)
    assert attempt.onset_beacon_right == pytest.approx(0.2)
    assert attempt.onset_max_beacon_signal == pytest.approx(0.6)
    assert attempt.onset_mean_beacon_signal == pytest.approx(0.4)
    assert attempt.onset_beacon_directional_contrast == pytest.approx(0.4)
    assert attempt.pre_seek_beacon_observation_count == 5
    assert attempt.pre_seek_recent_mean_beacon_signal == pytest.approx(0.4)
    assert attempt.pre_seek_recent_max_beacon_signal == pytest.approx(0.6)
    assert attempt.pre_seek_beacon_strength_trend == pytest.approx(0.1)


def test_feasibility_diagnostics_are_evaluator_only() -> None:
    diagnostics = summarize_exp003_episode(
        _synthetic_episode(
            (
                _synthetic_transition(
                    1,
                    action=Action.TURN_LEFT,
                    position_before=(0.2, 0.5),
                    position_after=(0.2, 0.5),
                    energy_before=0.1,
                    energy_after=0.1,
                    controller_mode_before_action=EXP003Mode.EXPLORE,
                    controller_mode=EXP003Mode.SEEK,
                ),
                _synthetic_transition(
                    2,
                    action=Action.MOVE_FORWARD,
                    position_before=(0.2, 0.5),
                    position_after=(0.2, 0.5),
                    energy_before=0.1,
                    energy_after=0.0,
                    terminated=True,
                ),
            )
        )
    )
    attempt = diagnostics.seek_attempts[0]
    visible = _synthetic_episode(
        (
            _synthetic_transition(
                1,
                action=Action.WAIT,
                position_before=(0.2, 0.5),
                position_after=(0.2, 0.5),
                truncated=True,
            ),
        )
    ).transitions[0].controller_visible.observation
    assert attempt.optimistic_reserve_margin < 0.0
    assert not hasattr(visible, "optimistic_reserve_margin")
    assert not hasattr(visible, "station_distance_at_onset")


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


def test_seek_outcomes_classify_acquisition_termination_and_censoring() -> None:
    acquired = summarize_exp003_episode(
        _synthetic_episode(
            (
                _synthetic_transition(
                    1,
                    action=Action.TURN_LEFT,
                    position_before=(0.2, 0.5),
                    position_after=(0.2, 0.5),
                    controller_mode_before_action=EXP003Mode.EXPLORE,
                    controller_mode=EXP003Mode.SEEK,
                ),
                _synthetic_transition(
                    2,
                    action=Action.MOVE_FORWARD,
                    position_before=(0.2, 0.5),
                    position_after=(0.5, 0.5),
                    charging_contact_after=True,
                    harvested_energy=0.5,
                ),
            )
        )
    )
    assert acquired.seek_attempts[0].outcome is EXP003SeekOutcome.ACQUIRED
    assert acquired.acquired_count == 1
    assert acquired.terminated_before_acquisition_count == 0
    assert acquired.horizon_censored_count == 0

    terminated = summarize_exp003_episode(
        _synthetic_episode(
            (
                _synthetic_transition(
                    1,
                    action=Action.TURN_LEFT,
                    position_before=(0.2, 0.5),
                    position_after=(0.2, 0.5),
                    controller_mode_before_action=EXP003Mode.EXPLORE,
                    controller_mode=EXP003Mode.SEEK,
                ),
                _synthetic_transition(
                    2,
                    action=Action.MOVE_FORWARD,
                    position_before=(0.2, 0.5),
                    position_after=(0.25, 0.5),
                    energy_before=0.1,
                    energy_after=0.0,
                    terminated=True,
                ),
            )
        )
    )
    assert (
        terminated.seek_attempts[0].outcome
        is EXP003SeekOutcome.TERMINATED_BEFORE_ACQUISITION
    )
    assert terminated.seek_attempts[0].station_distance_at_termination == pytest.approx(
        0.25
    )

    censored = summarize_exp003_episode(
        _synthetic_episode(
            (
                _synthetic_transition(
                    1,
                    action=Action.TURN_LEFT,
                    position_before=(0.2, 0.5),
                    position_after=(0.2, 0.5),
                    controller_mode_before_action=EXP003Mode.EXPLORE,
                    controller_mode=EXP003Mode.SEEK,
                ),
                _synthetic_transition(
                    2,
                    action=Action.MOVE_FORWARD,
                    position_before=(0.2, 0.5),
                    position_after=(0.25, 0.5),
                    truncated=True,
                ),
            )
        )
    )
    assert censored.seek_attempts[0].outcome is EXP003SeekOutcome.HORIZON_CENSORED
    assert censored.seek_attempts[0].station_distance_at_horizon == pytest.approx(
        0.25
    )
    assert censored.acquisition_fraction_among_resolved_attempts is None


def test_zero_resolved_attempts_have_undefined_acquisition_fraction() -> None:
    no_seek = summarize_exp003_episode(
        _synthetic_episode(
            (
                _synthetic_transition(
                    1,
                    action=Action.WAIT,
                    position_before=(0.2, 0.5),
                    position_after=(0.2, 0.5),
                    controller_mode_before_action=EXP003Mode.EXPLORE,
                    controller_mode=EXP003Mode.EXPLORE,
                    truncated=True,
                ),
            )
        )
    )
    assert no_seek.seek_attempt_count == 0
    assert no_seek.acquisition_fraction_among_resolved_attempts is None


def test_partial_record_with_active_seek_fails_without_horizon_truncation() -> None:
    with pytest.raises(
        ValueError,
        match="active SEEK attempt ended without genuine horizon truncation",
    ):
        summarize_exp003_episode(
            _synthetic_episode(
                (
                    _synthetic_transition(
                        1,
                        action=Action.TURN_LEFT,
                        position_before=(0.2, 0.5),
                        position_after=(0.2, 0.5),
                        controller_mode_before_action=EXP003Mode.EXPLORE,
                        controller_mode=EXP003Mode.SEEK,
                    ),
                )
            )
        )


def test_censored_attempts_are_excluded_from_resolved_acquisition_fraction() -> None:
    diagnostics = summarize_exp003_episode(
        _synthetic_episode(
            (
                _synthetic_transition(
                    1,
                    action=Action.TURN_LEFT,
                    position_before=(0.2, 0.5),
                    position_after=(0.2, 0.5),
                    controller_mode_before_action=EXP003Mode.EXPLORE,
                    controller_mode=EXP003Mode.SEEK,
                ),
                _synthetic_transition(
                    2,
                    action=Action.MOVE_FORWARD,
                    position_before=(0.2, 0.5),
                    position_after=(0.5, 0.5),
                    charging_contact_after=True,
                    harvested_energy=0.5,
                ),
                _synthetic_transition(
                    3,
                    action=Action.WAIT,
                    position_before=(0.5, 0.5),
                    position_after=(0.5, 0.5),
                    energy_before=9.0,
                    energy_after=8.9,
                    charging_contact_before=True,
                    charging_contact_after=True,
                    controller_mode_before_action=EXP003Mode.CHARGE,
                    controller_mode=EXP003Mode.EXPLORE,
                ),
                _synthetic_transition(
                    4,
                    action=Action.TURN_LEFT,
                    position_before=(0.8, 0.5),
                    position_after=(0.8, 0.5),
                    controller_mode_before_action=EXP003Mode.EXPLORE,
                    controller_mode=EXP003Mode.SEEK,
                ),
                _synthetic_transition(
                    5,
                    action=Action.MOVE_FORWARD,
                    position_before=(0.8, 0.5),
                    position_after=(0.8, 0.5),
                    charging_contact_before=False,
                    charging_contact_after=False,
                    truncated=True,
                ),
            )
        )
    )
    assert diagnostics.acquired_count == 1
    assert diagnostics.terminated_before_acquisition_count == 0
    assert diagnostics.horizon_censored_count == 1
    assert diagnostics.acquisition_fraction_among_resolved_attempts == pytest.approx(
        1.0
    )


def test_boundary_clamps_include_ordinary_diagonal_and_attempt_streaks() -> None:
    diagnostics = summarize_exp003_episode(
        _synthetic_episode(
            (
                _synthetic_transition(
                    1,
                    action=Action.TURN_LEFT,
                    position_before=(0.1, 0.1),
                    position_after=(0.1, 0.1),
                    controller_mode_before_action=EXP003Mode.EXPLORE,
                    controller_mode=EXP003Mode.SEEK,
                ),
                _synthetic_transition(
                    2,
                    action=Action.MOVE_FORWARD,
                    position_before=(0.0, 0.5),
                    position_after=(0.0, 0.5),
                    heading=math.pi,
                ),
                _synthetic_transition(
                    3,
                    action=Action.MOVE_FORWARD,
                    position_before=(0.0, 0.0),
                    position_after=(0.0, 0.0),
                    heading=5 * math.pi / 4,
                ),
                _synthetic_transition(
                    4,
                    action=Action.MOVE_FORWARD,
                    position_before=(0.2, 0.5),
                    position_after=(0.25, 0.5),
                    charging_contact_after=True,
                    harvested_energy=0.5,
                ),
            ),
            station_center=(0.25, 0.5),
        )
    )
    assert diagnostics.boundary_clamped_move_forward_count == 2
    assert diagnostics.clamped_move_forward_fraction == pytest.approx(2 / 3)
    assert diagnostics.longest_clamped_forward_streak == 2
    attempt = diagnostics.seek_attempts[0]
    assert attempt.boundary_clamp_count == 2
    assert attempt.had_boundary_clamp is True
    assert attempt.longest_boundary_clamp_streak == 2


def test_pass_through_is_classified_and_has_zero_harvest() -> None:
    diagnostics = summarize_exp003_episode(
        _synthetic_episode(
            (
                _synthetic_transition(
                    1,
                    action=Action.MOVE_FORWARD,
                    position_before=(0.1, 0.5),
                    position_after=(0.4, 0.5),
                    heading=0.0,
                    controller_mode_before_action=EXP003Mode.EXPLORE,
                    controller_mode=EXP003Mode.EXPLORE,
                    truncated=True,
                ),
            ),
            station_center=(0.25, 0.5),
        ),
        EXP003StationConfig(episode_horizon=1, movement_distance=0.3),
    )
    assert diagnostics.pass_through_count == 1
    assert diagnostics.total_charged_energy == 0.0


def test_explore_entry_and_harvest_are_classified_separately() -> None:
    diagnostics = summarize_exp003_episode(
        _synthetic_episode(
            (
                _synthetic_transition(
                    1,
                    action=Action.MOVE_FORWARD,
                    position_before=(0.1, 0.5),
                    position_after=(0.25, 0.5),
                    heading=0.0,
                    harvested_energy=0.5,
                    charging_contact_after=True,
                    controller_mode_before_action=EXP003Mode.EXPLORE,
                    controller_mode=EXP003Mode.EXPLORE,
                ),
                _synthetic_transition(
                    2,
                    action=Action.WAIT,
                    position_before=(0.25, 0.5),
                    position_after=(0.25, 0.5),
                    energy_before=5.4,
                    energy_after=5.8,
                    charging_contact_before=True,
                    charging_contact_after=True,
                    harvested_energy=0.5,
                    controller_mode_before_action=EXP003Mode.EXPLORE,
                    controller_mode=EXP003Mode.EXPLORE,
                    truncated=True,
                ),
            ),
            station_center=(0.25, 0.5),
        ),
        EXP003StationConfig(episode_horizon=2, movement_distance=0.15),
    )
    assert diagnostics.explore_station_entry_count == 1
    assert diagnostics.explore_harvested_energy == pytest.approx(1.0)


def test_charge_to_explore_recovery_harvest_counts_as_explore_energy() -> None:
    diagnostics = summarize_exp003_episode(
        _synthetic_episode(
            (
                _synthetic_transition(
                    1,
                    action=Action.WAIT,
                    position_before=(0.25, 0.5),
                    position_after=(0.25, 0.5),
                    energy_before=8.6,
                    energy_after=9.0,
                    harvested_energy=0.5,
                    charging_contact_before=True,
                    charging_contact_after=True,
                    controller_mode_before_action=EXP003Mode.CHARGE,
                    controller_mode=EXP003Mode.EXPLORE,
                    truncated=True,
                ),
            ),
            station_center=(0.25, 0.5),
        ),
        EXP003StationConfig(episode_horizon=1),
    )
    assert diagnostics.explore_station_entry_count == 0
    assert diagnostics.explore_harvested_energy == pytest.approx(0.5)


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
    field_ordinary_text = _format_field_frame(data.field_frames[0])
    field_terminal_text = _format_field_frame(data.field_frames[-1])
    field_padded_text = _format_field_frame(
        replace(data.field_frames[-1], is_padded=True)
    )
    assert "energy access: controller-visible" in field_ordinary_text
    assert "[CTRL + EVAL]" in field_ordinary_text
    for field_text in (field_terminal_text, field_padded_text):
        assert "EVALUATOR ONLY — no next controller observation" in field_text
        assert "controller-visible" not in field_text
        assert "CTRL + EVAL" not in field_text
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
