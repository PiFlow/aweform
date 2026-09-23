"""Focused D-046 protocol and causal-isolation tests."""

from __future__ import annotations

import math

import pytest

from aweform.d045 import D045Env
from aweform.d046 import (
    D046_BLOCK_DEFINITIONS,
    D046_CALIBRATION_TRANSITIONS,
    D046_DEFAULT_SEEDS,
    D046_FEATURE_DIMENSION,
    D046_MAX_WHEEL_DELTA_RAD,
    D046_QUARTER_SIZE,
    D046_WEIGHT_COUNT,
    D046ConsequencePredictor,
    _evaluate_heldout,
    _evaluate_rollouts,
    _run_lifetime,
    build_d046_curriculum,
    model_state_from_observation,
    quadratic_feature_map,
    validate_d046_development_seeds,
)


def _initial_observation() -> tuple[float, ...]:
    environment = D045Env()
    observation, info = environment.reset(
        options={
            "body_position": (0.50, 0.50),
            "station_center": (0.50, 0.50),
            "heading": 0.0,
            "battery_j": 2664.0,
            "body_temperature_c": 23.0,
            "charger_termination_latched": False,
        }
    )
    assert info == {}
    return tuple(float(value) for value in observation)


def test_d046_predictor_has_exact_zero_initialized_state() -> None:
    predictor = D046ConsequencePredictor()

    assert len(predictor.weights) == D046_WEIGHT_COUNT == 528
    assert predictor.weights == (0.0,) * D046_WEIGHT_COUNT
    assert predictor.weight_summary() == {
        "count": 528,
        "finite": True,
        "l2_norm": 0.0,
        "min": 0.0,
        "max": 0.0,
    }


def test_generic_quadratic_feature_map_has_declared_order_and_size() -> None:
    state = tuple(float(index) / 10.0 for index in range(8))
    action = (0.25 * D046_MAX_WHEEL_DELTA_RAD, -0.5 * D046_MAX_WHEEL_DELTA_RAD)
    features = quadratic_feature_map(state, action)
    x = (*state, 0.25, -0.5)

    assert len(features) == D046_FEATURE_DIMENSION == 66
    assert features[:11] == (1.0, *x)
    assert features[11:] == tuple(
        x[i] * x[j] for i in range(10) for j in range(i, 10)
    )


def test_state_only_comparator_ignores_action_coordinates() -> None:
    observation = _initial_observation()
    environment = D045Env()
    environment.reset(
        options={
            "body_position": (0.50, 0.50),
            "station_center": (0.50, 0.50),
            "heading": 0.0,
            "battery_j": 2664.0,
            "body_temperature_c": 23.0,
            "charger_termination_latched": False,
        }
    )
    next_observation, *_ = environment.step(
        (0.25 * D046_MAX_WHEEL_DELTA_RAD, 0.0)
    )
    next_values = tuple(float(value) for value in next_observation)
    predictor = D046ConsequencePredictor(state_only=True)
    pre_a = predictor.predict(observation, (0.0, 0.0))
    pre_b = predictor.predict(observation, (D046_MAX_WHEEL_DELTA_RAD, 0.0))
    predictor.update_from_transition(observation, (0.0, 0.0), next_values, pre_a)
    post_a = predictor.predict(observation, (0.0, 0.0))
    post_b = predictor.predict(observation, (D046_MAX_WHEEL_DELTA_RAD, 0.0))

    assert pre_a == pre_b
    assert post_a == post_b


def test_curriculum_is_exactly_once_and_seed_shuffled_only_by_block() -> None:
    first = build_d046_curriculum(21046)
    second = build_d046_curriculum(21046)

    assert first == second
    assert len(first.steps) == D046_CALIBRATION_TRANSITIONS == 564
    assert len(first.block_order) == 72
    assert len(set(first.block_order)) == 72
    assert all(step.command == (0.0, 0.0) for step in first.steps[:16])
    assert all(step.command == (0.0, 0.0) for step in first.steps[-8:])
    assert all(
        abs(value) <= D046_MAX_WHEEL_DELTA_RAD
        for step in first.steps
        for value in step.command
    )
    nonzero_steps = [step for step in first.steps if step.command != (0.0, 0.0)]
    assert len(nonzero_steps) == 540
    for block_index in first.block_order:
        block_steps = [
            step for step in first.steps if step.block_index == block_index
        ]
        command, _, length = D046_BLOCK_DEFINITIONS[block_index]
        assert tuple(step.command for step in block_steps) == (
            (command,) * length + ((-command[0], -command[1]),) * length
        )
    other_seed = build_d046_curriculum(21047)
    assert first.block_order != other_seed.block_order
    assert first.sequence_sha256 != other_seed.sequence_sha256


def test_seed_guard_requires_exact_official_block_and_rejects_reserved_seed() -> None:
    assert validate_d046_development_seeds(D046_DEFAULT_SEEDS) == D046_DEFAULT_SEEDS
    with pytest.raises(ValueError, match="exactly seeds"):
        validate_d046_development_seeds(D046_DEFAULT_SEEDS[:-1])
    with pytest.raises(ValueError, match="reserved"):
        validate_d046_development_seeds(tuple(range(50001, 51001)))
    with pytest.raises(ValueError, match="authorized seeds"):
        build_d046_curriculum(21066)


def test_lifetime_has_exact_support_and_shadow_trajectory_identity() -> None:
    result = _run_lifetime(21046)
    payload = result.payload()
    support = result.support

    assert support.transitions == D046_CALIBRATION_TRANSITIONS
    assert sum(support.amplitude_counts.values()) == 564
    assert support.amplitude_counts == {"0": 24, "0.25": 180, "0.5": 180, "1": 180}
    assert all(
        result.prequential.quarters[key].count == D046_QUARTER_SIZE
        for key in ("Q1", "Q2", "Q3", "Q4")
    )
    assert payload["trajectory_identity_equal"] is True
    assert result.learner_digest == result.matched_no_learner_digest
    assert len(result.predictor.weights) == 528
    assert all(math.isfinite(value) for value in result.predictor.weights)


def test_holdout_and_rollouts_are_read_only_and_have_fixed_support() -> None:
    result = _run_lifetime(21046)
    before = result.predictor.weights
    state_before = result.state_only_predictor.weights

    heldout, heldout_count = _evaluate_heldout(
        result.predictor, result.state_only_predictor
    )
    rollouts, lengths = _evaluate_rollouts(
        result.predictor, result.state_only_predictor
    )

    assert heldout_count == 81
    assert heldout.groups["overall"].models["organism_full"].count == 81
    assert heldout.groups["overall"].models["state_only"].count == 81
    assert heldout.groups["overall"].models["zero_change"].count == 81
    assert lengths == {"R0": 10, "R1": 10, "R2": 10, "R3": 8}
    assert set(rollouts.groups["R0"]) == {"1", "2", "4", "8", "final"}
    assert set(rollouts.groups["R3"]) == {"1", "2", "4", "8", "final"}
    assert result.predictor.weights == before
    assert result.state_only_predictor.weights == state_before


def test_model_state_normalizes_only_wheel_channels() -> None:
    observation = _initial_observation()
    state = model_state_from_observation(observation)

    assert state[:6] == observation[:6]
    assert state[6] == observation[6] / D046_MAX_WHEEL_DELTA_RAD
    assert state[7] == observation[7] / D046_MAX_WHEEL_DELTA_RAD
