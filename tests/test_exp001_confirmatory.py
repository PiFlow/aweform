from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pytest

import aweform.exp001_confirmatory as confirmatory
from aweform import (
    CONFIRMATORY_SEEDS,
    Action,
    EXP001Condition,
    EXP001ControllerStep,
    EXP001EpisodeRecord,
    EXP001EvaluatorInitialState,
    EXP001EvaluatorStep,
    EXP001Mode,
    EXP001TransitionRecord,
    run_exp001_c_debug_calibration,
)
from aweform.exp001_seed_policy import (
    FORMAL_CALIBRATION_SEEDS,
    validate_exp001_development_seeds,
)


def _synthetic_episode(
    condition: EXP001Condition,
    seed: int,
    modes: tuple[EXP001Mode, ...] = (EXP001Mode.EXPLORE,),
    *,
    horizon: bool = False,
) -> EXP001EpisodeRecord:
    transitions = tuple(
        EXP001TransitionRecord(
            controller_visible=EXP001ControllerStep(observation=object()),
            privileged_evaluator=EXP001EvaluatorStep(
                step_index=index + 1,
                action=Action.MOVE_FORWARD,
                position=(0.5 + 0.1 * (index + 1), 0.5),
                heading=0.0,
                actual_energy=4.0 - index,
                harvested_energy=0.25,
                basal_cost=0.1,
                action_cost=0.1,
                energy_before=5.0 - index,
                energy_after=4.0 - index,
                terminated=not horizon and index == len(modes) - 1,
                truncated=horizon and index == len(modes) - 1,
                controller_mode=mode,
            ),
        )
        for index, mode in enumerate(modes)
    )
    return EXP001EpisodeRecord(
        condition=condition,
        environment_seed=seed,
        initial_state=EXP001EvaluatorInitialState(
            position=(0.5, 0.5),
            heading=0.0,
            actual_energy=5.0,
            source_positions=((0.25, 0.25),),
        ),
        transitions=transitions,
    )


def _synthetic_formal_artifact(tmp_path: Path) -> tuple[Path, dict[str, object]]:
    rows: list[dict[str, object]] = []
    for seed in CONFIRMATORY_SEEDS:
        for condition, lifespan in (
            (EXP001Condition.A, 5),
            (EXP001Condition.B, 12),
            (EXP001Condition.C, 10),
        ):
            rows.append(
                {
                    "condition": condition.value,
                    "environment_seed": seed,
                    "capped_lifespan": lifespan,
                    "completed_transitions": lifespan,
                    "terminated_viability_failure": True,
                    "horizon_survival": False,
                    "final_normalized_energy": 0.2,
                    "minimum_normalized_energy": 0.1,
                    "total_harvested_energy": 1.0,
                    "total_basal_energy_cost": 0.1 * lifespan,
                    "total_action_energy_cost": 0.1 * lifespan,
                    "total_distance_travelled": 0.05 * lifespan,
                    "explore_action_count": lifespan,
                    "seek_resource_action_count": 0,
                    "charge_action_count": 0,
                    "complete_recharge_cycle_count": 0,
                }
            )
    manifest = confirmatory._build_manifest(
        "a" * 40,
        {
            "tracked_worktree_clean": True,
            "untracked_files_present": False,
            "untracked_file_count": 0,
        },
        run_started_at_utc="2026-08-18T08:00:00+00:00",
    ).to_dict()
    payload: dict[str, object] = {
        "schema_version": confirmatory.EXP001_CONFIRMATORY_ARTIFACT_SCHEMA_VERSION,
        "manifest": manifest,
        "episode_summaries": rows,
    }
    path = tmp_path / "confirmatory.json"
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path, payload


def _synthetic_summary(
    condition: EXP001Condition,
    seed: int,
) -> confirmatory.EXP001EpisodeSummary:
    return confirmatory.EXP001EpisodeSummary(
        condition=condition.value,
        environment_seed=seed,
        capped_lifespan=1,
        completed_transitions=1,
        terminated_viability_failure=True,
        horizon_survival=False,
        final_normalized_energy=0.4,
        minimum_normalized_energy=0.4,
        total_harvested_energy=0.0,
        total_basal_energy_cost=0.1,
        total_action_energy_cost=0.0,
        total_distance_travelled=0.0,
        explore_action_count=1,
        seek_resource_action_count=0,
        charge_action_count=0,
        complete_recharge_cycle_count=0,
    )


def test_formal_gate_and_exact_seed_tuple_fail_before_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False

    def forbidden(*_args: object, **_kwargs: object) -> None:
        nonlocal called
        called = True
        raise AssertionError("formal execution bridge must not be reached")

    monkeypatch.setattr(
        confirmatory, "_execute_exp001_confirmatory_for_repository", forbidden
    )
    with pytest.raises(PermissionError):
        confirmatory.execute_exp001_confirmatory("wrong")
    assert not called

    assert (
        confirmatory.validate_exp001_formal_seeds(CONFIRMATORY_SEEDS)
        == CONFIRMATORY_SEEDS
    )
    for invalid in (
        CONFIRMATORY_SEEDS[:-1],
        tuple(reversed(CONFIRMATORY_SEEDS)),
        (*CONFIRMATORY_SEEDS[:-1], CONFIRMATORY_SEEDS[-2]),
        tuple(range(30000, 31000)),
    ):
        with pytest.raises(ValueError):
            confirmatory.validate_exp001_formal_seeds(invalid)


def test_reserved_ranges_are_rejected_by_development_validation() -> None:
    for seed in (FORMAL_CALIBRATION_SEEDS[0], CONFIRMATORY_SEEDS[0]):
        with pytest.raises(ValueError):
            validate_exp001_development_seeds((seed,))
        with pytest.raises(ValueError):
            run_exp001_c_debug_calibration((seed,))


def test_mocked_formal_routing_is_exactly_3000_matched_a_b_c_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[EXP001Condition, int]] = []

    def fake_run_episode(
        *,
        condition: EXP001Condition,
        environment_seed: int,
        env_config: object,
        development_config: object,
    ) -> EXP001EpisodeRecord:
        del env_config
        calls.append((condition, environment_seed))
        assert development_config == confirmatory._CALIBRATED_C_CONFIG
        return _synthetic_episode(condition, environment_seed)

    monkeypatch.setattr(confirmatory, "_run_episode", fake_run_episode)
    summaries = confirmatory._run_formal_exp001_episodes(CONFIRMATORY_SEEDS)

    assert len(summaries) == 3000
    assert calls[:3] == [
        (EXP001Condition.A, CONFIRMATORY_SEEDS[0]),
        (EXP001Condition.B, CONFIRMATORY_SEEDS[0]),
        (EXP001Condition.C, CONFIRMATORY_SEEDS[0]),
    ]
    assert calls[-3:] == [
        (EXP001Condition.A, CONFIRMATORY_SEEDS[-1]),
        (EXP001Condition.B, CONFIRMATORY_SEEDS[-1]),
        (EXP001Condition.C, CONFIRMATORY_SEEDS[-1]),
    ]
    assert confirmatory.CALIBRATED_C_NAME == "SHORT"
    assert confirmatory.CALIBRATED_C.explore_duration == 10
    assert confirmatory.CALIBRATED_C.charge_duration == 5


def test_summary_uses_frozen_lifespan_energy_distance_modes_and_cycles() -> None:
    episode = _synthetic_episode(
        EXP001Condition.C,
        701,
        (
            EXP001Mode.EXPLORE,
            EXP001Mode.SEEK_RESOURCE,
            EXP001Mode.CHARGE,
            EXP001Mode.EXPLORE,
        ),
    )
    summary = confirmatory.summarize_exp001_confirmatory_episode(episode)

    assert summary.capped_lifespan == summary.completed_transitions == 4
    assert summary.terminated_viability_failure is True
    assert summary.horizon_survival is False
    assert summary.minimum_normalized_energy == pytest.approx(0.1)
    assert summary.total_harvested_energy == pytest.approx(1.0)
    assert summary.total_basal_energy_cost == pytest.approx(0.4)
    assert summary.total_action_energy_cost == pytest.approx(0.4)
    assert summary.total_distance_travelled == pytest.approx(0.4)
    assert summary.explore_action_count == 2
    assert summary.seek_resource_action_count == 1
    assert summary.charge_action_count == 1
    assert summary.complete_recharge_cycle_count == 1


def test_summary_marks_horizon_survival_at_exact_horizon() -> None:
    episode = _synthetic_episode(
        EXP001Condition.A,
        701,
        tuple(EXP001Mode.EXPLORE for _ in range(1000)),
        horizon=True,
    )
    summary = confirmatory.summarize_exp001_confirmatory_episode(episode)
    assert summary.capped_lifespan == 1000
    assert summary.completed_transitions == 1000
    assert summary.terminated_viability_failure is False
    assert summary.horizon_survival is True


def test_confirmatory_artifact_has_compact_rows_and_no_trajectories() -> None:
    artifact = confirmatory.EXP001ConfirmatoryArtifact(
        manifest=confirmatory._build_manifest(
            "a" * 40,
            {
                "tracked_worktree_clean": True,
                "untracked_files_present": False,
                "untracked_file_count": 0,
            },
            run_started_at_utc="2026-08-18T08:00:00+00:00",
        ),
        episode_summaries=(
            confirmatory.summarize_exp001_confirmatory_episode(
                _synthetic_episode(EXP001Condition.A, 701)
            ),
        ),
    )
    payload = artifact.to_dict()
    assert set(payload) == {"schema_version", "manifest", "episode_summaries"}
    assert "raw_trajectories" not in payload
    assert payload["manifest"]["raw_trajectories_persisted"] is False


def test_artifact_validation_rejects_duplicate_missing_and_malformed_pairs(
    tmp_path: Path,
) -> None:
    path, payload = _synthetic_formal_artifact(tmp_path)
    for mutation in ("duplicate", "missing", "malformed"):
        mutated = copy.deepcopy(payload)
        rows = mutated["episode_summaries"]
        assert isinstance(rows, list)
        if mutation == "duplicate":
            rows[-1] = copy.deepcopy(rows[-2])
        elif mutation == "missing":
            rows[-1]["environment_seed"] = CONFIRMATORY_SEEDS[0]
            rows[-1]["condition"] = EXP001Condition.A.value
        else:
            rows[0]["minimum_normalized_energy"] = 2.0
        malformed_path = tmp_path / f"{mutation}.json"
        malformed_path.write_text(json.dumps(mutated), encoding="utf-8")
        with pytest.raises(confirmatory.EXP001ConfirmatoryValidationError):
            confirmatory.analyze_exp001_confirmatory_artifact(malformed_path)
    assert path.exists()


def test_artifact_validation_rejects_wrong_top_level_schema_version(
    tmp_path: Path,
) -> None:
    _path, payload = _synthetic_formal_artifact(tmp_path)
    payload["schema_version"] = "exp-001-confirmatory-invalid"
    mutated_path = tmp_path / "wrong-schema.json"
    mutated_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(confirmatory.EXP001ConfirmatoryValidationError):
        confirmatory.analyze_exp001_confirmatory_artifact(mutated_path)


def test_analysis_records_distinct_execution_and_analysis_numpy_versions(
    tmp_path: Path,
) -> None:
    path, payload = _synthetic_formal_artifact(tmp_path)
    manifest = payload["manifest"]
    assert isinstance(manifest, dict)
    manifest["numpy_version"] = "2.5.2-source-execution"
    path.write_text(json.dumps(payload), encoding="utf-8")

    analysis = confirmatory.analyze_exp001_confirmatory_artifact(path)
    output = analysis.to_dict()
    assert analysis.source_execution_numpy_version == "2.5.2-source-execution"
    assert analysis.analysis_numpy_version == np.__version__
    assert output["source_execution_numpy_version"] == "2.5.2-source-execution"
    assert output["analysis_numpy_version"] == np.__version__
    report = analysis.to_markdown()
    assert "Source execution NumPy: `2.5.2-source-execution`" in report
    assert f"Analysis/bootstrap NumPy: `{np.__version__}`" in report


def test_analysis_is_paired_b_minus_c_a_is_descriptive_only_and_has_no_p_value(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path, _payload = _synthetic_formal_artifact(tmp_path)
    monkeypatch.setattr(
        confirmatory, "_run_episode", lambda **_: pytest.fail("simulator invoked")
    )
    analysis = confirmatory.analyze_exp001_confirmatory_artifact(path)

    assert analysis.mean_difference == pytest.approx(2.0)
    assert analysis.differences == (2.0,) * 1000
    assert analysis.interpretation == confirmatory.INTERPRETATION_B_GREATER
    assert analysis.descriptive_diagnostics["conditions"][EXP001Condition.A.value][
        "status"
    ] == ("descriptive reference only")
    assert "p_value" not in json.dumps(analysis.to_dict())
    assert analysis.to_dict()["artifact_only"] is True
    assert analysis.to_dict()["simulator_executed"] is False


def test_bootstrap_is_golden_pcg64_91001_linear() -> None:
    differences = np.arange(1000, dtype=np.float64)
    lower, upper = confirmatory._paired_percentile_bootstrap(differences)
    assert lower == pytest.approx(481.73695000000004)
    assert upper == pytest.approx(517.1761250000001)
    assert confirmatory.EXP001_BOOTSTRAP_RNG_SEED == 91001
    assert confirmatory.EXP001_BOOTSTRAP_BIT_GENERATOR == "PCG64"
    assert confirmatory.EXP001_BOOTSTRAP_RESAMPLES == 50_000
    assert confirmatory.EXP001_BOOTSTRAP_QUANTILE_METHOD == "linear"


@pytest.mark.parametrize(
    ("lower", "upper", "expected"),
    [
        (0.1, 1.0, "B_GREATER"),
        (-1.0, -0.1, "C_GREATER"),
        (-0.1, 0.1, "UNRESOLVED"),
        (0.0, 0.0, "UNRESOLVED"),
    ],
)
def test_frozen_three_way_interpretation(
    lower: float,
    upper: float,
    expected: str,
) -> None:
    assert confirmatory.interpret_exp001_interval(lower, upper) == expected


def test_reservation_precedes_formal_episode_bridge_and_is_retained_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact_path = tmp_path / "artifacts" / "EXP-001-confirmatory.json"
    seen: list[bool] = []

    monkeypatch.setattr(
        confirmatory,
        "resolve_exp001_git_provenance",
        lambda _path: (
            tmp_path,
            "a" * 40,
            {
                "tracked_worktree_clean": True,
                "untracked_files_present": False,
                "untracked_file_count": 0,
            },
        ),
    )
    monkeypatch.setattr(
        confirmatory, "validate_calibrated_c_against_artifact", lambda _: None
    )

    def fail_after_reservation(_seeds: object) -> tuple[object, ...]:
        reservation = Path(f"{artifact_path}.reservation")
        seen.append(reservation.exists())
        raise RuntimeError("synthetic crash")

    monkeypatch.setattr(
        confirmatory, "_run_formal_exp001_episodes", fail_after_reservation
    )
    with pytest.raises(RuntimeError):
        confirmatory._execute_exp001_confirmatory_for_repository(tmp_path)
    assert seen == [True]
    assert (tmp_path / "artifacts").exists()
    assert Path(f"{artifact_path}.reservation").exists()


def test_formal_start_timestamp_is_captured_before_bridge_and_reused(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact_path = tmp_path / "artifacts" / "EXP-001-confirmatory.json"
    started_at = "2026-08-18T08:30:00+00:00"
    bridge_start: dict[str, str] = {}

    monkeypatch.setattr(
        confirmatory,
        "resolve_exp001_git_provenance",
        lambda _path: (
            tmp_path,
            "a" * 40,
            {
                "tracked_worktree_clean": True,
                "untracked_files_present": False,
                "untracked_file_count": 0,
            },
        ),
    )
    monkeypatch.setattr(
        confirmatory, "validate_calibrated_c_against_artifact", lambda _: None
    )
    monkeypatch.setattr(confirmatory, "_utc_timestamp", lambda: started_at)

    def fake_bridge(seeds: object) -> tuple[confirmatory.EXP001EpisodeSummary, ...]:
        assert seeds == CONFIRMATORY_SEEDS
        reservation = Path(f"{artifact_path}.reservation")
        reservation_payload = json.loads(reservation.read_text(encoding="utf-8"))
        bridge_start["timestamp"] = reservation_payload["started_at_utc"]
        assert reservation_payload["status"] == "reserved"
        return tuple(
            _synthetic_summary(condition, seed)
            for seed in CONFIRMATORY_SEEDS
            for condition in (
                EXP001Condition.A,
                EXP001Condition.B,
                EXP001Condition.C,
            )
        )

    monkeypatch.setattr(confirmatory, "_run_formal_exp001_episodes", fake_bridge)
    receipt = confirmatory._execute_exp001_confirmatory_for_repository(tmp_path)

    manifest = json.loads(receipt.artifact_path.read_text(encoding="utf-8"))["manifest"]
    reservation = json.loads(
        Path(f"{artifact_path}.reservation").read_text(encoding="utf-8")
    )
    assert bridge_start["timestamp"] == started_at
    assert manifest["run_started_at_utc"] == started_at
    assert reservation["started_at_utc"] == started_at
    assert reservation["status"] == "completed"


def test_existing_artifact_or_reservation_blocks_before_episode_bridge(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact_path = tmp_path / "artifacts" / "EXP-001-confirmatory.json"
    artifact_path.parent.mkdir()
    artifact_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        confirmatory,
        "resolve_exp001_git_provenance",
        lambda _path: (tmp_path, "a" * 40, {"tracked_worktree_clean": True}),
    )
    monkeypatch.setattr(
        confirmatory, "validate_calibrated_c_against_artifact", lambda _: None
    )
    monkeypatch.setattr(
        confirmatory,
        "_run_formal_exp001_episodes",
        lambda _seeds: pytest.fail("episode bridge invoked"),
    )
    with pytest.raises(FileExistsError):
        confirmatory._execute_exp001_confirmatory_for_repository(tmp_path)

    artifact_path.unlink()
    reservation = Path(f"{artifact_path}.reservation")
    reservation.write_text("reserved", encoding="utf-8")
    with pytest.raises(FileExistsError):
        confirmatory._execute_exp001_confirmatory_for_repository(tmp_path)


def test_calibrated_c_matches_committed_artifact() -> None:
    confirmatory.validate_calibrated_c_against_artifact(Path(__file__).parents[1])
