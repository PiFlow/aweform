import numpy as np
import pytest
from gymnasium.utils.env_checker import check_env

from aweform import Action, AweformEnv, AweformEnvConfig, EnergyConfig


def test_spaces_and_checker_are_valid() -> None:
    env = AweformEnv()
    assert env.action_space.n == 4
    assert env.observation_space.shape == (4,)
    assert env.observation_space.dtype == np.float32
    check_env(env, skip_render_check=True)


def test_reward_is_exactly_zero_and_observation_has_no_privileged_state() -> None:
    env = AweformEnv()
    observation, info = env.reset(seed=11)
    next_observation, reward, _, _, step_info = env.step(Action.WAIT)

    assert observation.shape == (4,)
    assert next_observation.shape == (4,)
    assert reward == 0.0
    assert info == {}
    assert step_info == {}
    assert not any(key in info for key in ("x", "y", "heading", "source_position"))


def test_harvest_offsets_cost_and_basal_energy_loss() -> None:
    config = AweformEnvConfig(
        energy=EnergyConfig(maximum_energy=10.0, basal_cost=0.2),
        initial_energy=5.0,
        harvest_rate=1.0,
        movement_distance=0.0,
        movement_cost=0.3,
        episode_horizon=10,
    )
    env = AweformEnv(config)
    env.reset(seed=12)
    assert env.body is not None
    assert env.resource_field is not None
    env.resource_field = type(env.resource_field)(
        world_min=config.world_min,
        world_max=config.world_max,
        source_position=env.body.position,
        peak_intensity=1.0,
        length_scale=0.1,
    )

    _, _, terminated, _, _ = env.step(Action.MOVE_FORWARD)

    assert terminated is False
    assert env.body.energy == pytest.approx(5.5)


def test_failure_terminates_and_cannot_revive() -> None:
    config = AweformEnvConfig(
        energy=EnergyConfig(maximum_energy=1.0, basal_cost=0.2),
        initial_energy=0.1,
        harvest_rate=0.0,
        episode_horizon=10,
    )
    env = AweformEnv(config)
    env.reset(seed=13)

    _, reward, terminated, truncated, _ = env.step(Action.WAIT)

    assert reward == 0.0
    assert terminated is True
    assert truncated is False
    with pytest.raises(RuntimeError, match="episode is over"):
        env.step(Action.WAIT)


def test_horizon_truncates_a_viable_episode() -> None:
    config = AweformEnvConfig(
        energy=EnergyConfig(maximum_energy=10.0, basal_cost=0.0),
        initial_energy=5.0,
        episode_horizon=2,
    )
    env = AweformEnv(config)
    env.reset(seed=14)

    _, _, terminated_first, truncated_first, _ = env.step(Action.WAIT)
    _, _, terminated_second, truncated_second, _ = env.step(Action.WAIT)

    assert (terminated_first, truncated_first) == (False, False)
    assert (terminated_second, truncated_second) == (False, True)
    with pytest.raises(RuntimeError, match="episode is over"):
        env.step(Action.WAIT)


def test_same_seed_and_actions_reproduce_trajectory() -> None:
    first = AweformEnv()
    second = AweformEnv()
    first_observation, _ = first.reset(seed=15)
    second_observation, _ = second.reset(seed=15)
    np.testing.assert_array_equal(first_observation, second_observation)

    for action in (Action.MOVE_FORWARD, Action.TURN_LEFT, Action.WAIT):
        first_result = first.step(action)
        second_result = second.step(action)
        np.testing.assert_array_equal(first_result[0], second_result[0])
        assert first_result[1:] == second_result[1:]


def test_different_seeds_change_generated_world_or_body_start() -> None:
    first = AweformEnv()
    second = AweformEnv()
    first.reset(seed=17)
    second.reset(seed=18)

    assert first.body is not None
    assert second.body is not None
    assert first.resource_field is not None
    assert second.resource_field is not None
    assert (
        first.resource_field.source_position != second.resource_field.source_position
        or first.body.position != second.body.position
        or first.body.heading != second.body.heading
    )


def test_environment_dynamics_do_not_consume_policy_stream() -> None:
    env = AweformEnv()
    env.reset(seed=16)
    assert env.random_streams is not None
    expected = env.random_streams.policy.random(8)

    other = AweformEnv()
    other.reset(seed=16)
    assert other.random_streams is not None
    other.step(Action.MOVE_FORWARD)
    actual = other.random_streams.policy.random(8)

    np.testing.assert_array_equal(actual, expected)
