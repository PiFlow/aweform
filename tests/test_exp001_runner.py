from __future__ import annotations

import copy
import math

import numpy as np
import pytest

import aweform.exp001_runner as runner_module
from aweform import (
    Action,
    AweformEnv,
    AweformEnvConfig,
    EXP001AController,
    EXP001BController,
    EXP001CController,
    EXP001Condition,
    EXP001DevelopmentConfig,
    EXP001Mode,
    ExternalObservation,
    InteroceptiveObservation,
    exp001_controller_observation,
    policy_rng_from_seed,
    run_exp001_development_batch,
)


def _development_config() -> EXP001DevelopmentConfig:
    return EXP001DevelopmentConfig(
        resource_contact_threshold=0.8,
        blind_explore_duration=3,
        blind_charge_duration=2,
    )


def _environment_config(**kwargs: object) -> AweformEnvConfig:
    values: dict[str, object] = {"episode_horizon": 4, **kwargs}
    return AweformEnvConfig(**values)  # type: ignore[arg-type]


def test_adapter_and_actual_runner_path_keep_controller_boundary_typed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, list[object]] = {"A": [], "B": [], "C": []}
    original_a = EXP001AController.act
    original_b = EXP001BController.act
    original_c = EXP001CController.act

    def spy_a(self: EXP001AController, observation: object) -> Action:
        seen["A"].append(observation)
        return original_a(self, observation)  # type: ignore[arg-type]

    def spy_b(self: EXP001BController, observation: object) -> Action:
        seen["B"].append(observation)
        return original_b(self, observation)  # type: ignore[arg-type]

    def spy_c(self: EXP001CController, observation: object) -> Action:
        seen["C"].append(observation)
        return original_c(self, observation)  # type: ignore[arg-type]

    monkeypatch.setattr(EXP001AController, "act", spy_a)
    monkeypatch.setattr(EXP001BController, "act", spy_b)
    monkeypatch.setattr(EXP001CController, "act", spy_c)

    result = run_exp001_development_batch(
        seeds=[701],
        env_config=_environment_config(),
        development_config=_development_config(),
    )

    assert isinstance(seen["A"][0], ExternalObservation)
    assert isinstance(seen["B"][0], InteroceptiveObservation)
    assert isinstance(seen["C"][0], ExternalObservation)
    assert all(
        not isinstance(observation, np.ndarray)
        for values in seen.values()
        for observation in values
    )

    episodes = {episode.condition: episode for episode in result.episodes}
    assert isinstance(
        episodes[EXP001Condition.A].transitions[0].controller_visible.observation,
        ExternalObservation,
    )
    assert isinstance(
        episodes[EXP001Condition.B].transitions[0].controller_visible.observation,
        InteroceptiveObservation,
    )
    assert isinstance(
        episodes[EXP001Condition.C].transitions[0].controller_visible.observation,
        ExternalObservation,
    )


def test_adapter_gives_b_actual_energy_and_c_remains_energy_blind() -> None:
    low = np.asarray([0.2, 0.1, 0.7, 0.2], dtype=np.float32)
    high = np.asarray([0.9, 0.1, 0.7, 0.2], dtype=np.float32)

    b_observation = exp001_controller_observation(EXP001Condition.B, low)
    assert isinstance(b_observation, InteroceptiveObservation)
    assert b_observation.energy == pytest.approx(0.2)

    c_low = exp001_controller_observation(EXP001Condition.C, low)
    c_high = exp001_controller_observation(EXP001Condition.C, high)
    assert isinstance(c_low, ExternalObservation)
    assert c_low == c_high

    first_c = EXP001CController(policy_rng_from_seed(702), _development_config())
    second_c = EXP001CController(policy_rng_from_seed(702), _development_config())
    first_action = runner_module._controller_action(first_c, c_low)
    second_action = runner_module._controller_action(second_c, c_high)
    assert first_action is second_action


def test_matched_environments_and_external_signals_are_identical() -> None:
    result = run_exp001_development_batch(
        seeds=[703],
        env_config=_environment_config(resource_count=3),
        development_config=_development_config(),
    )
    episodes = {episode.condition: episode for episode in result.episodes}
    starts = [episode.initial_state for episode in episodes.values()]
    assert starts[0] == starts[1] == starts[2]

    a_external = episodes[
        EXP001Condition.A
    ].transitions[0].controller_visible.observation
    b_observation = episodes[
        EXP001Condition.B
    ].transitions[0].controller_visible.observation
    c_external = episodes[
        EXP001Condition.C
    ].transitions[0].controller_visible.observation
    assert isinstance(a_external, ExternalObservation)
    assert isinstance(b_observation, InteroceptiveObservation)
    assert isinstance(c_external, ExternalObservation)
    assert a_external == b_observation.external == c_external
    assert b_observation.energy == pytest.approx(
        starts[1].actual_energy
        / _environment_config(resource_count=3).energy.maximum_energy
    )


def test_policy_stream_consumption_does_not_advance_environment_stream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_environment = runner_module.AweformEnv
    created: list[AweformEnv] = []

    class SpyEnvironment(real_environment):
        def __init__(self, config: AweformEnvConfig) -> None:
            super().__init__(config)
            created.append(self)

    config = _environment_config(episode_horizon=8, resource_count=3)
    monkeypatch.setattr(runner_module, "AweformEnv", SpyEnvironment)
    run_exp001_development_batch(
        seeds=[709],
        env_config=config,
        development_config=_development_config(),
    )

    expected_environment = real_environment(config)
    expected_environment.reset(seed=709)
    assert expected_environment.random_streams is not None
    expected_draws = expected_environment.random_streams.environment.random(16)
    assert len(created) == 3
    for environment in created:
        assert environment.random_streams is not None
        np.testing.assert_array_equal(
            environment.random_streams.environment.random(16),
            expected_draws,
        )


def test_policy_rngs_are_fresh_equivalent_and_independent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[np.random.Generator] = []
    initial_states: list[dict[str, object]] = []
    original_policy_rng_from_seed = runner_module.policy_rng_from_seed

    def capture_policy_rng(seed: int) -> np.random.Generator:
        rng = original_policy_rng_from_seed(seed)
        captured.append(rng)
        initial_states.append(copy.deepcopy(rng.bit_generator.state))
        return rng

    monkeypatch.setattr(runner_module, "policy_rng_from_seed", capture_policy_rng)
    run_exp001_development_batch(
        seeds=[704],
        env_config=_environment_config(episode_horizon=1),
        development_config=_development_config(),
    )

    assert len(captured) == 3
    assert len({id(rng) for rng in captured}) == 3
    assert initial_states[0] == initial_states[1] == initial_states[2]

    b_state = copy.deepcopy(captured[1].bit_generator.state)
    c_state = copy.deepcopy(captured[2].bit_generator.state)
    captured[0].random(32)
    b_expected = np.random.default_rng()
    b_expected.bit_generator.state = b_state
    c_expected = np.random.default_rng()
    c_expected.bit_generator.state = c_state
    np.testing.assert_array_equal(captured[1].random(8), b_expected.random(8))
    np.testing.assert_array_equal(captured[2].random(8), c_expected.random(8))


def test_same_seed_replays_exact_runner_records() -> None:
    kwargs = {
        "seeds": [705],
        "env_config": _environment_config(resource_count=3),
        "development_config": _development_config(),
    }
    first = run_exp001_development_batch(**kwargs)
    second = run_exp001_development_batch(**kwargs)
    assert first.episodes == second.episodes


def test_returning_to_explore_starts_a_new_rng_segment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class CountingPolicyRNG:
        def __init__(self) -> None:
            self.geometric_calls = 0

        def geometric(self, probability: float) -> int:
            assert probability == 1.0 / 8.0
            self.geometric_calls += 1
            return 3 if self.geometric_calls == 1 else 1

        def random(self) -> float:
            return 0.1

    class ScriptedEnvironment(AweformEnv):
        script = (
            (0.9, 0.0, 0.0, 0.0),
            (0.2, 1.0, 0.0, 0.0),
            (0.2, 0.0, 0.0, 0.0),
            (0.9, 0.0, 0.0, 0.0),
            (0.9, 0.0, 0.0, 0.0),
        )

        def __init__(self, config: AweformEnvConfig) -> None:
            self.script_index = 0
            super().__init__(config)

        def reset(
            self,
            *,
            seed: int | None = None,
            options: dict[str, object] | None = None,
        ):
            self.script_index = 0
            return super().reset(seed=seed, options=options)

        def step(self, action: int):
            self.script_index += 1
            return super().step(action)

        def _observation(self) -> np.ndarray:
            return np.asarray(self.script[self.script_index], dtype=np.float32)

    rngs: list[CountingPolicyRNG] = []

    def fake_policy_rng(_seed: int) -> CountingPolicyRNG:
        rng = CountingPolicyRNG()
        rngs.append(rng)
        return rng

    monkeypatch.setattr(runner_module, "AweformEnv", ScriptedEnvironment)
    monkeypatch.setattr(runner_module, "policy_rng_from_seed", fake_policy_rng)

    result = run_exp001_development_batch(
        seeds=[706],
        env_config=_environment_config(episode_horizon=4),
        development_config=_development_config(),
    )

    b_episode = next(
        episode for episode in result.episodes if episode.condition is EXP001Condition.B
    )
    b_modes = [
        transition.privileged_evaluator.controller_mode
        for transition in b_episode.transitions
    ]
    assert b_modes == [
        EXP001Mode.EXPLORE,
        EXP001Mode.CHARGE,
        EXP001Mode.CHARGE,
        EXP001Mode.EXPLORE,
    ]
    assert rngs[1].geometric_calls == 2


def test_turn_angle_contract_is_checked_before_execution() -> None:
    with pytest.raises(ValueError, match="turn_angle == math.pi / 4"):
        run_exp001_development_batch(
            seeds=[707],
            env_config=_environment_config(turn_angle=math.pi / 2),
            development_config=_development_config(),
        )

    accepted = run_exp001_development_batch(
        seeds=[707],
        env_config=_environment_config(turn_angle=math.pi / 4.0, episode_horizon=1),
        development_config=_development_config(),
    )
    assert len(accepted.episodes) == 3


@pytest.mark.parametrize("seeds", [[], [-1], [1.5], [True], "701"])
def test_runner_rejects_malformed_development_seeds(seeds: object) -> None:
    with pytest.raises(ValueError):
        run_exp001_development_batch(
            seeds=seeds,  # type: ignore[arg-type]
            env_config=_environment_config(),
            development_config=_development_config(),
        )


def test_records_keep_privileged_telemetry_out_of_controller_observation() -> None:
    result = run_exp001_development_batch(
        seeds=[708],
        env_config=_environment_config(),
        development_config=_development_config(),
    )
    for episode in result.episodes:
        for transition in episode.transitions:
            visible = transition.controller_visible.observation
            privileged = transition.privileged_evaluator
            assert privileged.actual_energy >= 0.0
            assert not hasattr(visible, "actual_energy")
            assert not hasattr(visible, "position")
            assert not hasattr(visible, "harvested_energy")
