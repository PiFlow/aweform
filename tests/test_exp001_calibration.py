from __future__ import annotations

import copy
import dataclasses
import json
import math
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

import aweform.exp001_calibration as calibration_module
import aweform.exp001_runner as runner_module
from aweform import (
    CONFIRMATORY_SEEDS,
    EXP001_CALIBRATION_HORIZON,
    EXP001_PROTOCOL_REVISION,
    FORMAL_CALIBRATION_SEEDS,
    FORMAL_CANDIDATES,
    FROZEN_EXP001_CALIBRATION_ENV_CONFIG,
    FROZEN_EXP001_SHARED_CONTROLLER_CONFIG,
    Action,
    EXP001CalibrationResult,
    EXP001CandidateSummary,
    EXP001Condition,
    EXP001ControllerStep,
    EXP001DevelopmentConfig,
    EXP001EpisodeRecord,
    EXP001EvaluatorInitialState,
    EXP001EvaluatorStep,
    EXP001Mode,
    EXP001TransitionRecord,
    ExternalObservation,
    frozen_exp001_calibration_environment_config,
    run_exp001_c_debug_calibration,
    run_exp001_formal_calibration,
    select_exp001_candidate,
    summarize_exp001_c_episode,
    write_exp001_calibration_json,
)

DEBUG_SEEDS = (18001, 18002, 18003, 18004, 18005, 18006, 18007, 18008)


def _candidate_config(candidate_name: str) -> EXP001DevelopmentConfig:
    candidate = next(
        candidate for candidate in FORMAL_CANDIDATES
        if candidate.candidate == candidate_name
    )
    return EXP001DevelopmentConfig(
        resource_contact_threshold=0.8,
        blind_explore_duration=candidate.explore_duration,
        blind_charge_duration=candidate.charge_duration,
        enter_seek=0.35,
        recover=0.85,
    )


def _synthetic_transition(
    step: int,
    mode: EXP001Mode,
    *,
    energy_before: float = 5.0,
    energy_after: float = 5.0,
    harvested_energy: float = 0.0,
    terminated: bool = False,
    truncated: bool = False,
) -> EXP001TransitionRecord:
    return EXP001TransitionRecord(
        controller_visible=EXP001ControllerStep(
            observation=ExternalObservation(0.0, 0.0, 0.0),
        ),
        privileged_evaluator=EXP001EvaluatorStep(
            step_index=step,
            action=Action.WAIT,
            position=(0.5, 0.5),
            heading=0.0,
            actual_energy=energy_after,
            harvested_energy=harvested_energy,
            basal_cost=0.1,
            action_cost=0.0,
            energy_before=energy_before,
            energy_after=energy_after,
            terminated=terminated,
            truncated=truncated,
            controller_mode=mode,
        ),
    )


def _synthetic_episode(
    modes: list[EXP001Mode],
    *,
    energies: list[float] | None = None,
    harvested: list[float] | None = None,
    final_truncated: bool = False,
    final_terminated: bool = False,
) -> EXP001EpisodeRecord:
    if energies is None:
        energies = [5.0] * len(modes)
    if harvested is None:
        harvested = [0.0] * len(modes)
    assert len(energies) == len(modes)
    assert len(harvested) == len(modes)
    transitions = tuple(
        _synthetic_transition(
            index + 1,
            mode,
            energy_before=5.0 if index == 0 else energies[index - 1],
            energy_after=energies[index],
            harvested_energy=harvested[index],
            terminated=final_terminated and index == len(modes) - 1,
            truncated=final_truncated and index == len(modes) - 1,
        )
        for index, mode in enumerate(modes)
    )
    return EXP001EpisodeRecord(
        condition=EXP001Condition.C,
        environment_seed=DEBUG_SEEDS[0],
        initial_state=EXP001EvaluatorInitialState(
            position=(0.5, 0.5),
            heading=0.0,
            actual_energy=5.0,
            source_positions=((0.5, 0.5),),
        ),
        transitions=transitions,
    )


def _summary(
    candidate: str,
    *,
    mean_lifespan: float = 1.0,
    survival_count: int = 0,
    mean_minimum_energy: float = 0.1,
) -> EXP001CandidateSummary:
    return EXP001CandidateSummary(
        candidate=candidate,
        explore_duration=10,
        charge_duration=5,
        episode_count=2,
        mean_capped_lifespan=mean_lifespan,
        median_capped_lifespan=mean_lifespan,
        minimum_capped_lifespan=int(mean_lifespan),
        maximum_capped_lifespan=int(mean_lifespan),
        horizon_survival_count=survival_count,
        horizon_survival_fraction=survival_count / 2,
        mean_final_normalized_energy=0.5,
        mean_minimum_normalized_energy=mean_minimum_energy,
        mean_total_harvested_energy=1.0,
        mean_explore_actions=1.0,
        mean_seek_resource_actions=1.0,
        mean_charge_actions=1.0,
        mean_complete_cycle_count=0.0,
    )


def test_frozen_formal_configuration_is_exact() -> None:
    config = frozen_exp001_calibration_environment_config()
    assert config == FROZEN_EXP001_CALIBRATION_ENV_CONFIG
    assert [
        (candidate.candidate, candidate.explore_duration, candidate.charge_duration)
        for candidate in FORMAL_CANDIDATES
    ] == [("SHORT", 10, 5), ("CURRENT", 20, 10), ("LONG", 30, 15)]
    assert config.world_min == (0.0, 0.0)
    assert config.world_max == (1.0, 1.0)
    assert config.energy.maximum_energy == 10.0
    assert config.energy.failure_boundary == 0.0
    assert config.energy.basal_cost == 0.1
    assert config.initial_energy == 5.0
    assert config.movement_distance == 0.05
    assert config.turn_angle == math.pi / 4.0
    assert config.wait_cost == 0.0
    assert config.turn_cost == 0.02
    assert config.movement_cost == 0.1
    assert config.probe_distance == 0.1
    assert config.sensor_angle == math.pi / 4.0
    assert config.harvest_rate == 0.5
    assert config.episode_horizon == 1000
    assert config.resource_peak_intensity == 1.0
    assert config.resource_length_scale == 0.25
    assert config.resource_count == 1


def test_calibration_path_instantiates_and_executes_only_c(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("calibration must not instantiate A or B")

    monkeypatch.setattr(runner_module.EXP001AController, "__init__", forbidden)
    monkeypatch.setattr(runner_module.EXP001BController, "__init__", forbidden)
    result = run_exp001_c_debug_calibration([DEBUG_SEEDS[0]])
    assert result.executed_seed_count == 1
    assert len(result.candidate_summaries) == 3


def test_calibration_c_receives_only_external_observation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[object] = []
    original = runner_module.EXP001CController.act

    def spy(self: object, observation: object) -> Action:
        seen.append(observation)
        return original(self, observation)  # type: ignore[arg-type]

    monkeypatch.setattr(runner_module.EXP001CController, "act", spy)
    run_exp001_c_debug_calibration([DEBUG_SEEDS[1]])
    assert seen
    assert all(isinstance(observation, ExternalObservation) for observation in seen)


@pytest.mark.parametrize(
    "reserved_seed",
    [FORMAL_CALIBRATION_SEEDS[0], CONFIRMATORY_SEEDS[0]],
)
def test_debug_reserved_seed_guard_rejects_before_environment_construction(
    monkeypatch: pytest.MonkeyPatch,
    reserved_seed: int,
) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("reserved seed reached environment construction")

    monkeypatch.setattr(runner_module, "AweformEnv", forbidden)
    with pytest.raises(ValueError, match="reserved"):
        run_exp001_c_debug_calibration([reserved_seed])


@pytest.mark.parametrize(
    "seeds,purpose",
    [
        ((FORMAL_CALIBRATION_SEEDS[0],), "debug"),
        ((CONFIRMATORY_SEEDS[0],), "debug"),
        (CONFIRMATORY_SEEDS, "calibration"),
        (FORMAL_CALIBRATION_SEEDS[:-1], "calibration"),
        (FORMAL_CALIBRATION_SEEDS[::-1], "calibration"),
        (FORMAL_CALIBRATION_SEEDS + (FORMAL_CALIBRATION_SEEDS[-1],), "calibration"),
    ],
)
def test_lowest_calibration_layer_rejects_reserved_or_noncanonical_requests(
    monkeypatch: pytest.MonkeyPatch,
    seeds: tuple[int, ...],
    purpose: str,
) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError(
            "invalid calibration request reached environment construction"
        )

    monkeypatch.setattr(runner_module, "AweformEnv", forbidden)
    with pytest.raises(ValueError):
        calibration_module._run_c_calibration(seeds=seeds, purpose=purpose)


def test_same_debug_seed_has_matched_initial_environment_state() -> None:
    records = [
        runner_module._run_exp001_c_episode(
            environment_seed=DEBUG_SEEDS[2],
            env_config=FROZEN_EXP001_CALIBRATION_ENV_CONFIG,
            development_config=_candidate_config(candidate.candidate),
        )
        for candidate in FORMAL_CANDIDATES
    ]
    assert (
        records[0].initial_state
        == records[1].initial_state
        == records[2].initial_state
    )


def test_each_candidate_gets_a_fresh_equivalent_policy_rng(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[np.random.Generator] = []
    original = runner_module.policy_rng_from_seed

    def capture(seed: int) -> np.random.Generator:
        rng = original(seed)
        captured.append(rng)
        return rng

    monkeypatch.setattr(runner_module, "policy_rng_from_seed", capture)
    run_exp001_c_debug_calibration([DEBUG_SEEDS[3]])

    assert len(captured) == 3
    assert len({id(rng) for rng in captured}) == 3
    states = [copy.deepcopy(rng.bit_generator.state) for rng in captured]
    captured[0].random(16)
    expected = []
    for state in states[1:]:
        rng = np.random.default_rng()
        rng.bit_generator.state = state
        expected.append(rng.random(8))
    np.testing.assert_array_equal(captured[1].random(8), expected[0])
    np.testing.assert_array_equal(captured[2].random(8), expected[1])


def test_repeated_debug_calibration_is_exactly_deterministic() -> None:
    first = run_exp001_c_debug_calibration(DEBUG_SEEDS[4:6])
    second = run_exp001_c_debug_calibration(DEBUG_SEEDS[4:6])
    assert first == second
    assert first.to_json() == second.to_json()


def test_episode_diagnostics_cap_lifespan_and_require_true_horizon_survival() -> None:
    over_horizon = _synthetic_episode(
        [EXP001Mode.EXPLORE] * (EXP001_CALIBRATION_HORIZON + 1),
        final_truncated=True,
    )
    capped = summarize_exp001_c_episode(over_horizon)
    assert capped.capped_lifespan == EXP001_CALIBRATION_HORIZON
    assert not capped.horizon_survivor

    horizon_survivor = _synthetic_episode(
        [EXP001Mode.EXPLORE] * EXP001_CALIBRATION_HORIZON,
        final_truncated=True,
    )
    assert summarize_exp001_c_episode(horizon_survivor).horizon_survivor

    terminal_at_horizon = _synthetic_episode(
        [EXP001Mode.EXPLORE] * EXP001_CALIBRATION_HORIZON,
        final_terminated=True,
    )
    assert not summarize_exp001_c_episode(terminal_at_horizon).horizon_survivor


def test_energy_harvest_mode_and_cycle_diagnostics_use_recorded_transitions() -> None:
    episode = _synthetic_episode(
        [
            EXP001Mode.EXPLORE,
            EXP001Mode.EXPLORE,
            EXP001Mode.SEEK_RESOURCE,
            EXP001Mode.SEEK_RESOURCE,
            EXP001Mode.CHARGE,
            EXP001Mode.CHARGE,
            EXP001Mode.EXPLORE,
            EXP001Mode.EXPLORE,
            EXP001Mode.SEEK_RESOURCE,
            EXP001Mode.CHARGE,
            EXP001Mode.EXPLORE,
        ],
        energies=[2.0, 8.0] + [5.0] * 9,
        harvested=[0.1, 0.2] + [0.0] * 9,
    )
    diagnostics = summarize_exp001_c_episode(episode)
    assert diagnostics.final_normalized_energy == 0.5
    assert diagnostics.minimum_normalized_energy == 0.2
    assert diagnostics.total_harvested_energy == pytest.approx(0.3)
    assert diagnostics.explore_actions == 5
    assert diagnostics.seek_resource_actions == 3
    assert diagnostics.charge_actions == 3
    assert diagnostics.complete_cycle_count == 2

    partial = _synthetic_episode(
        [EXP001Mode.EXPLORE, EXP001Mode.SEEK_RESOURCE, EXP001Mode.CHARGE]
    )
    assert summarize_exp001_c_episode(partial).complete_cycle_count == 0


def test_candidate_summaries_have_only_protocol_diagnostics() -> None:
    result = run_exp001_c_debug_calibration([DEBUG_SEEDS[6]])
    expected_fields = {
        "candidate",
        "explore_duration",
        "charge_duration",
        "episode_count",
        "mean_capped_lifespan",
        "median_capped_lifespan",
        "minimum_capped_lifespan",
        "maximum_capped_lifespan",
        "horizon_survival_count",
        "horizon_survival_fraction",
        "mean_final_normalized_energy",
        "mean_minimum_normalized_energy",
        "mean_total_harvested_energy",
        "mean_explore_actions",
        "mean_seek_resource_actions",
        "mean_charge_actions",
        "mean_complete_cycle_count",
    }
    for summary in result.candidate_summaries:
        assert {field.name for field in dataclasses.fields(summary)} == expected_fields
        assert not any(
            forbidden in field.name.lower()
            for field in dataclasses.fields(summary)
            for forbidden in ("a_", "b_", "effect", "significance", "composite")
        )


def test_result_schema_contains_aggregate_rows_only() -> None:
    result = run_exp001_c_debug_calibration([DEBUG_SEEDS[7]])
    payload = result.to_dict()
    assert isinstance(result, EXP001CalibrationResult)
    assert payload["schema_version"] == "exp-001-calibration-v1"
    assert payload["manifest"]["experiment"] == "EXP-001"
    assert payload["manifest"]["shared_controller_config"] == {
        "resource_contact_threshold": 0.8,
        "enter_seek": 0.35,
        "recover": 0.85,
    }
    assert payload["manifest"]["shared_controller_config"] == dataclasses.asdict(
        FROZEN_EXP001_SHARED_CONTROLLER_CONFIG
    )
    assert "unused by C's energy-blind policy" in payload["manifest"][
        "c_energy_blind_config_note"
    ]
    assert payload["manifest"]["result_classification"].endswith(
        "not confirmatory evidence"
    )
    assert "episodes" not in payload
    assert "trajectories" not in payload
    assert "per_seed" not in json.dumps(payload).lower()
    assert payload["manifest"]["formal_calibration_seed_range"] == {
        "start": 20001,
        "end": 20200,
        "count": 200,
    }


def test_artifact_serialization_is_deterministic_and_non_overwriting(
    tmp_path: Path,
) -> None:
    result = run_exp001_c_debug_calibration([DEBUG_SEEDS[0]])
    output = tmp_path / "exp001-debug.json"
    assert write_exp001_calibration_json(result, output) == output
    assert json.loads(output.read_text(encoding="utf-8")) == result.to_dict()
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        write_exp001_calibration_json(result, output)


def test_formal_execution_requires_exact_authorization_before_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("formal calibration should not start")

    monkeypatch.setattr(calibration_module, "_run_c_calibration", forbidden)
    with pytest.raises(PermissionError, match="requires authorization"):
        run_exp001_formal_calibration("not-authorized")


def test_formal_wrapper_routes_only_fixed_formal_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_executor(*, seeds: tuple[int, ...], purpose: str) -> object:
        captured["seeds"] = seeds
        captured["purpose"] = purpose
        return object()

    monkeypatch.setattr(calibration_module, "_run_c_calibration", fake_executor)
    monkeypatch.setattr(calibration_module, "_current_git_sha", lambda: "a" * 40)
    run_exp001_formal_calibration(EXP001_PROTOCOL_REVISION)
    assert captured == {
        "seeds": FORMAL_CALIBRATION_SEEDS,
        "purpose": "calibration",
    }


def test_formal_calibration_reaches_private_c_executor_when_fully_mocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[int, int, int]] = []

    def forbidden_environment(*_args: object, **_kwargs: object) -> None:
        raise AssertionError(
            "mocked formal calibration must not construct an environment"
        )

    def fake_executor(
        *,
        environment_seed: int,
        env_config: object,
        development_config: EXP001DevelopmentConfig,
    ) -> EXP001EpisodeRecord:
        del env_config
        calls.append(
            (
                environment_seed,
                development_config.blind_explore_duration,
                development_config.blind_charge_duration,
            )
        )
        return _synthetic_episode([EXP001Mode.EXPLORE])

    monkeypatch.setattr(calibration_module, "_run_exp001_c_episode", fake_executor)
    monkeypatch.setattr(calibration_module, "_current_git_sha", lambda: "a" * 40)
    monkeypatch.setattr(runner_module, "AweformEnv", forbidden_environment)

    result = run_exp001_formal_calibration(EXP001_PROTOCOL_REVISION)

    assert len(calls) == len(FORMAL_CALIBRATION_SEEDS) * len(FORMAL_CANDIDATES)
    assert calls[0][0] == FORMAL_CALIBRATION_SEEDS[0]
    assert calls[-1][0] == FORMAL_CALIBRATION_SEEDS[-1]
    assert {call[1:] for call in calls} == {(10, 5), (20, 10), (30, 15)}
    assert result.executed_seed_count == len(FORMAL_CALIBRATION_SEEDS)


def test_formal_git_provenance_uses_source_checkout_and_ignores_untracked_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = Path("/aweform/source-checkout")
    calls: list[tuple[list[str], Path]] = []

    def fake_run(args: list[str], **kwargs: object) -> SimpleNamespace:
        calls.append((args, kwargs["cwd"]))  # type: ignore[arg-type]
        if args[1] == "rev-parse":
            return SimpleNamespace(stdout="a" * 40 + "\n")
        return SimpleNamespace(stdout="")

    monkeypatch.setattr(
        calibration_module,
        "_resolve_aweform_checkout",
        lambda: repository,
    )
    monkeypatch.setattr(calibration_module.subprocess, "run", fake_run)
    assert calibration_module._current_git_sha() == "a" * 40
    assert calls == [
        (["git", "rev-parse", "HEAD"], repository),
        (["git", "status", "--porcelain", "--untracked-files=no"], repository),
    ]


def test_formal_git_provenance_rejects_tracked_dirty_checkout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = Path("/aweform/source-checkout")

    def fake_run(args: list[str], **_kwargs: object) -> SimpleNamespace:
        if args[1] == "rev-parse":
            return SimpleNamespace(stdout="b" * 40 + "\n")
        return SimpleNamespace(stdout=" M src/aweform/exp001.py\n")

    monkeypatch.setattr(
        calibration_module,
        "_resolve_aweform_checkout",
        lambda: repository,
    )
    monkeypatch.setattr(calibration_module.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match="tracked Aweform source checkout is dirty"):
        calibration_module._current_git_sha()


def test_formal_git_provenance_fails_closed_without_source_checkout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def no_checkout() -> Path:
        raise RuntimeError("no checkout")

    monkeypatch.setattr(calibration_module, "_resolve_aweform_checkout", no_checkout)
    with pytest.raises(RuntimeError, match="no checkout"):
        calibration_module._current_git_sha()


def test_selection_rule_covers_all_frozen_tie_cases() -> None:
    assert select_exp001_candidate(
        [
            _summary("SHORT", mean_lifespan=1),
            _summary("CURRENT", mean_lifespan=3),
            _summary("LONG", mean_lifespan=2),
        ]
    ) == "CURRENT"
    assert select_exp001_candidate(
        [
            _summary("SHORT", mean_lifespan=3, survival_count=2),
            _summary("CURRENT", mean_lifespan=3, survival_count=1),
            _summary("LONG", mean_lifespan=1),
        ]
    ) == "SHORT"
    assert select_exp001_candidate(
        [
            _summary(
                "SHORT",
                mean_lifespan=3,
                survival_count=1,
                mean_minimum_energy=0.5,
            ),
            _summary(
                "CURRENT",
                mean_lifespan=3,
                survival_count=1,
                mean_minimum_energy=0.4,
            ),
            _summary("LONG", mean_lifespan=1),
        ]
    ) == "SHORT"
    assert select_exp001_candidate(
        [_summary("SHORT"), _summary("CURRENT"), _summary("LONG", mean_lifespan=0)]
    ) == "CURRENT"
    assert select_exp001_candidate(
        [_summary("SHORT", mean_lifespan=0), _summary("CURRENT"), _summary("LONG")]
    ) == "CURRENT"
    assert select_exp001_candidate(
        [_summary("SHORT"), _summary("CURRENT", mean_lifespan=0), _summary("LONG")]
    ) == "SHORT"
    assert select_exp001_candidate(
        [_summary("SHORT"), _summary("CURRENT"), _summary("LONG")]
    ) == "CURRENT"


def test_selection_uses_exact_full_values_without_rounding() -> None:
    selected = select_exp001_candidate(
        [
            _summary("SHORT", mean_lifespan=1.0),
            _summary("CURRENT", mean_lifespan=1.0 + 1e-12),
            _summary("LONG", mean_lifespan=1.0),
        ]
    )
    assert selected == "CURRENT"


def test_selection_rejects_incomplete_candidate_summaries() -> None:
    with pytest.raises(ValueError, match="exactly SHORT"):
        select_exp001_candidate([_summary("SHORT"), _summary("CURRENT")])


def test_exp001_development_runner_remains_three_condition_runner() -> None:
    result = runner_module.run_exp001_development_batch(
        seeds=[DEBUG_SEEDS[0]],
        env_config=replace(FROZEN_EXP001_CALIBRATION_ENV_CONFIG, episode_horizon=1),
        development_config=EXP001DevelopmentConfig(
            resource_contact_threshold=0.8,
            blind_explore_duration=10,
            blind_charge_duration=5,
        ),
    )
    assert {episode.condition for episode in result.episodes} == set(EXP001Condition)
