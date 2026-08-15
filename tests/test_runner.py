import json

import pytest

import aweform.runner as runner_module
from aweform import (
    Action,
    AweformEnv,
    AweformEnvConfig,
    Condition,
    EnergyConfig,
    HomeostaticConfig,
    run_development_batch,
    write_development_json,
)

TEST_SEED = 701


def _result(
    *,
    seed: int = TEST_SEED,
    env_config: AweformEnvConfig | None = None,
    homeostatic_config: HomeostaticConfig | None = None,
    masked_energy: float = 0.2,
):
    return run_development_batch(
        seeds=[seed],
        env_config=env_config or AweformEnvConfig(episode_horizon=4),
        homeostatic_config=homeostatic_config or HomeostaticConfig(),
        masked_energy=masked_energy,
        git_sha="test-sha",
    )


def test_conditions_have_matched_initial_evaluator_state() -> None:
    result = _result(env_config=AweformEnvConfig(episode_horizon=4, resource_count=3))

    assert [episode.summary.condition for episode in result.episodes] == list(Condition)
    starts = [episode.trajectory.initial_state for episode in result.episodes]
    assert starts[0] == starts[1] == starts[2]
    assert len(starts[0].source_positions) == 3


def test_same_seed_and_configuration_replay_identically() -> None:
    config = AweformEnvConfig(episode_horizon=4, resource_count=3)
    first = _result(env_config=config)
    second = _result(env_config=config)

    assert first.episodes == second.episodes
    first_manifest = first.to_dict()["manifest"]
    second_manifest = second.to_dict()["manifest"]
    assert first_manifest is not None
    assert second_manifest is not None
    assert first_manifest["run_started_at_utc"] != ""
    assert second_manifest["run_started_at_utc"] != ""
    first_manifest.pop("run_started_at_utc")
    second_manifest.pop("run_started_at_utc")
    assert first_manifest == second_manifest


def test_conditions_use_isolated_environment_instances_and_reset_controllers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_environment = runner_module.AweformEnv
    created: list[AweformEnv] = []

    class SpyEnvironment(real_environment):
        def __init__(self, config: AweformEnvConfig) -> None:
            super().__init__(config)
            created.append(self)

    monkeypatch.setattr(runner_module, "AweformEnv", SpyEnvironment)
    result = _result()

    assert len(created) == 3
    assert len({id(environment) for environment in created}) == 3
    assert [environment._step_count for environment in created] == [4, 4, 4]
    assert result.episodes[1].trajectory.transitions[0].mode.value == "EXPLORE"
    assert result.episodes[2].trajectory.transitions[0].mode.value == "SEEK_RESOURCE"


def test_runner_keeps_observation_boundary() -> None:
    result = _result(env_config=AweformEnvConfig(episode_horizon=4, resource_count=3))

    for episode in result.episodes:
        initial_state = episode.trajectory.initial_state
        assert len(initial_state.source_positions) == 3
        for transition in episode.trajectory.transitions:
            assert len(transition.observation) == 4
            assert transition.observation != (
                transition.x,
                transition.y,
                transition.heading,
                transition.energy,
            )

    env = AweformEnv()
    _, reset_info = env.reset(seed=TEST_SEED)
    _, _, _, _, step_info = env.step(Action.WAIT)
    assert reset_info == {}
    assert step_info == {}


def test_transition_accounting_and_horizon_summary() -> None:
    config = AweformEnvConfig(
        world_min=(0.0, 0.0),
        world_max=(100.0, 100.0),
        energy=EnergyConfig(maximum_energy=10.0, basal_cost=0.2),
        initial_energy=5.0,
        movement_distance=0.5,
        movement_cost=0.3,
        turn_cost=0.0,
        wait_cost=0.0,
        harvest_rate=0.0,
        episode_horizon=1,
    )
    result = _result(env_config=config)
    summary = result.episodes[0].summary
    transition = result.episodes[0].trajectory.transitions[0]

    assert transition.action is Action.MOVE_FORWARD
    assert transition.harvested_energy == 0.0
    assert transition.basal_cost == pytest.approx(0.2)
    assert transition.action_cost == pytest.approx(0.3)
    assert transition.energy_before == pytest.approx(5.0)
    assert transition.energy_after == pytest.approx(4.5)
    assert summary.total_harvested_energy == 0.0
    assert summary.total_basal_energy_cost == pytest.approx(0.2)
    assert summary.total_action_energy_cost == pytest.approx(0.3)
    assert summary.total_distance_travelled == pytest.approx(0.5)
    assert summary.terminated_viability_failure is False
    assert summary.truncated_at_horizon is True
    assert summary.horizon_survival is True


def test_death_summary_matches_environment_semantics() -> None:
    config = AweformEnvConfig(
        energy=EnergyConfig(maximum_energy=1.0, basal_cost=0.2),
        initial_energy=0.1,
        harvest_rate=0.0,
        episode_horizon=3,
    )
    result = _result(env_config=config)

    for episode in result.episodes:
        assert episode.summary.steps_executed == 1
        assert episode.summary.terminated_viability_failure is True
        assert episode.summary.truncated_at_horizon is False
        assert episode.summary.horizon_survival is False


def test_homeostatic_modes_are_counted_deterministically() -> None:
    config = AweformEnvConfig(
        energy=EnergyConfig(maximum_energy=10.0, basal_cost=1.6),
        initial_energy=5.0,
        harvest_rate=0.0,
        movement_cost=0.0,
        turn_cost=0.0,
        wait_cost=0.0,
        episode_horizon=3,
    )
    result = _result(
        env_config=config,
        homeostatic_config=HomeostaticConfig(exploration_steps=2),
        masked_energy=0.2,
    )
    summaries = {
        episode.summary.condition: episode.summary for episode in result.episodes
    }

    assert summaries[Condition.A_PERSISTENT].explore_steps is None
    assert summaries[Condition.B_HOMEOSTATIC].explore_steps == 1
    assert summaries[Condition.B_HOMEOSTATIC].seek_resource_steps == 2
    assert summaries[Condition.B_HOMEOSTATIC].mode_transitions == 1
    assert summaries[Condition.C_ENERGY_BLIND].explore_steps == 0
    assert summaries[Condition.C_ENERGY_BLIND].seek_resource_steps == 3
    assert summaries[Condition.C_ENERGY_BLIND].mode_transitions == 1


def test_artifact_is_readable_complete_and_non_overwriting(tmp_path) -> None:
    result = _result(env_config=AweformEnvConfig(episode_horizon=4, resource_count=3))
    output_path = tmp_path / "development-run.json"

    assert write_development_json(result, output_path) == output_path
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "exp-000-development-v2"
    assert payload["manifest"]["schema_version"] == ("exp-000-development-manifest-v2")
    assert payload["manifest"]["purpose"] == "development"
    assert payload["manifest"]["git_commit_sha"] == "test-sha"
    assert payload["manifest"]["environment_seeds"] == [TEST_SEED]
    assert payload["manifest"]["environment_config"]["episode_horizon"] == 4
    assert payload["manifest"]["environment_config"]["resource_count"] == 3
    assert payload["manifest"]["homeostatic_config"]["enter_seek"] == 0.35
    assert len(payload["episode_summaries"]) == 3
    assert len(payload["raw_trajectories"]) == 3
    assert all(
        len(trajectory["initial_state"]["source_positions"]) == 3
        for trajectory in payload["raw_trajectories"]
    )
    assert all(
        "source_positions" not in transition
        for trajectory in payload["raw_trajectories"]
        for transition in trajectory["transitions"]
    )

    original = output_path.read_text(encoding="utf-8")
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        write_development_json(result, output_path)
    assert output_path.read_text(encoding="utf-8") == original


@pytest.mark.parametrize("seeds", [[], [TEST_SEED, -1], [TEST_SEED, 1.5], [True]])
def test_runner_rejects_empty_or_malformed_seeds(seeds: object) -> None:
    with pytest.raises(ValueError):
        run_development_batch(
            seeds,  # type: ignore[arg-type]
            AweformEnvConfig(),
            HomeostaticConfig(),
            0.2,
            "test-sha",
        )
