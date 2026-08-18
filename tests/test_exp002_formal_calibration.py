from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace

import pytest

import aweform.exp002_calibration as calibration
import aweform.exp002_runner as runner
from aweform import (
    Action,
    EXP001Condition,
    EXP001Mode,
    ExternalObservation,
)
from aweform.exp002_protocol import (
    EXP002_B_CANDIDATES,
    EXP002_CALIBRATION_SEEDS,
    EXP002_CONFIRMATORY_SEEDS,
    EXP002_HORIZON,
    EXP002_PROTOCOL_FILE_SHA256,
    EXP002BCandidate,
)
from aweform.exp002_runner import (
    EXP002ControllerStep,
    EXP002EpisodeDiagnostics,
    EXP002EpisodeRecord,
    EXP002EvaluatorInitialState,
    EXP002EvaluatorStep,
    EXP002TransitionRecord,
)


def _summary(
    candidate: EXP002BCandidate,
    *,
    survival: int = 0,
    coverage: float = 10.0,
) -> calibration.EXP002CandidateSummary:
    return calibration.EXP002CandidateSummary(
        candidate=candidate.value,
        enter_seek=candidate.enter_seek,
        n=200,
        horizon_survival_count=survival,
        horizon_survival_fraction=survival / 200,
        mean_visited_cell_count=coverage,
        mean_coverage_fraction=coverage / 1024,
        mean_capped_lifespan=500.0,
        median_capped_lifespan=500.0,
        min_capped_lifespan=1,
        max_capped_lifespan=1000,
        mean_explore_action_count=10.0,
        mean_distance_travelled_during_explore=0.5,
        mean_explore_unique_cell_count=5.0,
        mean_coverage_efficiency_per_100_explore_actions=50.0,
        mean_complete_recharge_cycle_count=2.0,
        total_seek_attempt_count=0,
        seek_attempt_reached_charge_count=0,
        seek_attempt_reached_charge_fraction=None,
        mean_seek_onset_normalized_energy=None,
        mean_nearest_source_distance_at_seek_onset=None,
        mean_minimum_normalized_energy_during_seek_attempt=None,
    )


def _summaries(
    *,
    survivals: tuple[int, int, int, int] = (0, 0, 0, 0),
    coverages: tuple[float, float, float, float] = (10.0, 20.0, 30.0, 40.0),
) -> tuple[calibration.EXP002CandidateSummary, ...]:
    return tuple(
        _summary(candidate, survival=survival, coverage=coverage)
        for candidate, survival, coverage in zip(
            EXP002_B_CANDIDATES, survivals, coverages, strict=True
        )
    )


def _minimal_episode(candidate: EXP002BCandidate, seed: int) -> object:
    return SimpleNamespace(condition=EXP001Condition.B, candidate=candidate, seed=seed)


def _minimal_diagnostic() -> EXP002EpisodeDiagnostics:
    return EXP002EpisodeDiagnostics(
        capped_lifespan=1000,
        horizon_survivor=True,
        visited_cell_count=10,
        remaining_cell_count=1014,
        coverage_fraction=10 / 1024,
        explore_action_count=10,
        distance_travelled_during_explore=0.5,
        explore_unique_cell_count=5,
        coverage_efficiency_per_100_explore_actions=50.0,
        complete_recharge_cycle_count=2,
        seek_attempts=(),
    )


def test_exact_formal_seed_tuple_is_accepted_without_simulation() -> None:
    assert calibration.validate_exp002_formal_seeds(tuple(range(40001, 40201))) == (
        tuple(range(40001, 40201))
    )


def test_scientific_contract_and_protocol_fingerprints_are_frozen() -> None:
    assert (
        calibration.exp002_scientific_contract_sha256()
        == calibration.EXP002_SCIENTIFIC_CONTRACT_SHA256
        == "cc982be0da525aafdab478442d753a3132bf6b006ee524e40e9f740a720637c6"
    )
    protocol_path = (
        calibration._repository_root()
        / "experiments"
        / "EXP-002-interoceptive-seek-threshold.md"
    )
    assert calibration._sha256_file(protocol_path) == EXP002_PROTOCOL_FILE_SHA256
    assert (
        calibration._sha256_file(protocol_path)
        == "18875e9e97221db0dcb7acb1ee50d9dc6546dd619d9f871430801335455f77d1"
    )


@pytest.mark.parametrize(
    "seeds",
    [
        EXP002_CALIBRATION_SEEDS[:-1],
        EXP002_CALIBRATION_SEEDS + (40201,),
        EXP002_CALIBRATION_SEEDS[::-1],
        EXP002_CALIBRATION_SEEDS[:10] + (EXP002_CALIBRATION_SEEDS[9],),
        EXP002_CONFIRMATORY_SEEDS,
        (18021,),
    ],
)
def test_formal_seed_validator_rejects_noncanonical_requests(
    seeds: tuple[int, ...],
) -> None:
    with pytest.raises(ValueError):
        calibration.validate_exp002_formal_seeds(seeds)


def test_wrong_authorization_is_rejected_before_simulator_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        calibration,
        "_run_episode",
        lambda **_: pytest.fail("simulator execution was reached"),
    )
    monkeypatch.setattr(
        calibration,
        "_formal_preflight",
        lambda _: pytest.fail("preflight should follow authorization"),
    )
    with pytest.raises(PermissionError):
        calibration.run_exp002_formal_calibration("wrong")


def test_formal_batches_are_b_only_matched_and_exactly_800_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[EXP001Condition, int, object, EXP002BCandidate]] = []
    diagnostic = _minimal_diagnostic()

    def fake_run_episode(**kwargs: object) -> object:
        condition = kwargs["condition"]
        seed = kwargs["environment_seed"]
        config = kwargs["env_config"]
        candidate = kwargs["candidate"]
        assert isinstance(condition, EXP001Condition)
        assert isinstance(seed, int)
        assert isinstance(candidate, EXP002BCandidate)
        calls.append((condition, seed, config, candidate))
        return _minimal_episode(candidate, seed)

    monkeypatch.setattr(calibration, "_run_episode", fake_run_episode)
    monkeypatch.setattr(calibration, "summarize_exp002_episode", lambda _: diagnostic)
    result = calibration._run_formal_batches(
        seeds=calibration.validate_exp002_formal_seeds(EXP002_CALIBRATION_SEEDS),
        git_commit_sha="a" * 40,
        started_at="test",
    )

    assert len(calls) == 4 * 200
    assert {call[0] for call in calls} == {EXP001Condition.B}
    for index, candidate in enumerate(EXP002_B_CANDIDATES):
        candidate_calls = calls[index * 200 : (index + 1) * 200]
        assert [call[1] for call in candidate_calls] == list(EXP002_CALIBRATION_SEEDS)
        assert {call[2] for call in candidate_calls} == {
            calibration.FROZEN_EXP001_CALIBRATION_ENV_CONFIG
        }
        assert {call[3] for call in candidate_calls} == {candidate}
        assert candidate.enter_seek in {0.35, 0.40, 0.45, 0.50}
    assert [summary.n for summary in result.candidate_summaries] == [200] * 4


@pytest.mark.parametrize(
    ("survivals", "coverages", "expected", "path"),
    [
        ((180, 179, 179, 179), (10, 99, 98, 97), "B35", "eligible_max_coverage"),
        ((180, 181, 180, 180), (10, 99, 98, 97), "B40", "eligible_max_coverage"),
        ((179, 178, 177, 176), (10, 20, 30, 40), "B35", "fallback_max_survival"),
        ((180, 180, 180, 180), (10, 20, 30, 30), "B45", "eligible_max_coverage"),
    ],
)
def test_frozen_candidate_selection_rule(
    survivals: tuple[int, int, int, int],
    coverages: tuple[float, float, float, float],
    expected: str,
    path: str,
) -> None:
    selection = calibration.select_exp002_candidate(
        _summaries(survivals=survivals, coverages=coverages)
    )
    assert selection.selected_candidate == expected
    assert selection.selection_path == path


def test_exact_180_is_eligible_and_179_is_not() -> None:
    selection = calibration.select_exp002_candidate(
        _summaries(survivals=(180, 179, 0, 0))
    )
    assert selection.viability_eligible_candidates == ("B35",)


def _terminal_episode(*, terminated: bool, truncated: bool) -> EXP002EpisodeRecord:
    visible = ExternalObservation(0.0, 0.0, 0.0)
    transitions = tuple(
        EXP002TransitionRecord(
            controller_visible=EXP002ControllerStep(visible),
            privileged_evaluator=EXP002EvaluatorStep(
                step_index=index,
                action=Action.WAIT,
                position_before=(0.5, 0.5),
                position_after=(0.5, 0.5),
                heading=0.0,
                actual_energy_before=5.0,
                actual_energy_after=4.9,
                harvested_energy=0.0,
                basal_cost=0.1,
                action_cost=0.0,
                controller_mode_before_action=EXP001Mode.EXPLORE,
                controller_mode=EXP001Mode.EXPLORE,
                terminated=terminated and index == EXP002_HORIZON,
                truncated=truncated and index == EXP002_HORIZON,
            ),
        )
        for index in range(1, EXP002_HORIZON + 1)
    )
    return EXP002EpisodeRecord(
        condition=EXP001Condition.B,
        candidate=EXP002BCandidate.B35,
        environment_seed=18021,
        initial_state=EXP002EvaluatorInitialState(
            position=(0.5, 0.5),
            heading=0.0,
            actual_energy=5.0,
            source_positions=((0.5, 0.5),),
        ),
        transitions=transitions,
    )


def test_exact_horizon_viability_failure_is_not_a_horizon_survivor() -> None:
    diagnostics = runner.summarize_exp002_episode(
        _terminal_episode(terminated=True, truncated=False)
    )
    assert diagnostics.capped_lifespan == EXP002_HORIZON
    assert not diagnostics.horizon_survivor


def test_artifact_is_aggregate_only_and_selection_is_recomputable() -> None:
    summaries = _summaries(survivals=(180, 181, 180, 180))
    result = calibration.EXP002FormalCalibrationResult(
        git_commit_sha="b" * 40,
        run_started_at_utc="2026-08-19T00:00:00+00:00",
        candidate_summaries=summaries,
        selection=calibration.select_exp002_candidate(summaries),
    )
    payload = result.to_dict()
    assert payload["schema_version"] == "exp-002-formal-calibration-v1"
    assert payload["identity"]["episode_count"] == 800
    assert payload["identity"]["raw_trajectories_persisted"] is False
    assert (
        payload["identity"]["scientific_contract_sha256"]
        == calibration.EXP002_SCIENTIFIC_CONTRACT_SHA256
    )
    assert payload["identity"]["shared_controller_values"] == asdict(
        calibration.EXP002_SHARED_CONTROLLER_VALUES
    )
    assert "transitions" not in json.dumps(payload)
    persisted_summaries = tuple(
        calibration.EXP002CandidateSummary(**row)
        for row in payload["candidate_summaries"]
    )
    assert calibration.select_exp002_candidate(persisted_summaries) == result.selection


def test_artifact_writer_is_non_overwriting_and_returns_sha256(tmp_path: Path) -> None:
    summaries = _summaries()
    result = calibration.EXP002FormalCalibrationResult(
        git_commit_sha="c" * 40,
        run_started_at_utc="test",
        candidate_summaries=summaries,
        selection=calibration.select_exp002_candidate(summaries),
    )
    path = tmp_path / "result.json"
    artifact_sha = calibration.write_exp002_calibration_json(result, path)
    assert artifact_sha == hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(FileExistsError):
        calibration.write_exp002_calibration_json(result, path)


def test_reservation_precedes_first_mocked_episode_and_completes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    artifact_path = tmp_path / "result.json"
    reservation_path = Path(f"{artifact_path}.reservation")
    monkeypatch.setattr(calibration, "FORMAL_ARTIFACT_PATH", artifact_path)
    monkeypatch.setattr(calibration, "_formal_preflight", lambda _: "d" * 40)
    monkeypatch.setattr(
        calibration,
        "summarize_exp002_episode",
        lambda _: _minimal_diagnostic(),
    )
    calls = 0

    def fake_run_episode(**kwargs: object) -> object:
        nonlocal calls
        calls += 1
        assert reservation_path.exists()
        assert "status=in_progress" in reservation_path.read_text()
        candidate = kwargs["candidate"]
        seed = kwargs["environment_seed"]
        return _minimal_episode(candidate, seed)  # type: ignore[arg-type]

    monkeypatch.setattr(calibration, "_run_episode", fake_run_episode)
    receipt = calibration.run_exp002_formal_calibration(
        calibration.FORMAL_EXECUTION_AUTHORIZATION
    )
    assert calls == 800
    assert receipt.artifact_path == artifact_path
    reservation_text = reservation_path.read_text()
    assert "status=completed" in reservation_text
    assert "git_commit_sha=" + "d" * 40 in reservation_text
    assert "git_status=tracked_clean" in reservation_text
    assert "pid=" in reservation_text
    assert "started_at_utc=" in reservation_text
    assert receipt.artifact_sha256 in reservation_text


def test_existing_artifact_and_reservation_block_before_simulation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    artifact_path = tmp_path / "result.json"
    monkeypatch.setattr(calibration, "FORMAL_ARTIFACT_PATH", artifact_path)
    monkeypatch.setattr(calibration, "_resolve_clean_git_sha", lambda _: "e" * 40)
    monkeypatch.setattr(
        calibration,
        "_run_episode",
        lambda **_: pytest.fail("simulator execution was reached"),
    )
    artifact_path.write_text("existing")
    with pytest.raises(FileExistsError):
        calibration.run_exp002_formal_calibration(
            calibration.FORMAL_EXECUTION_AUTHORIZATION
        )
    artifact_path.unlink()
    reservation_path = Path(f"{artifact_path}.reservation")
    reservation_path.write_text("existing reservation")
    with pytest.raises(FileExistsError):
        calibration.run_exp002_formal_calibration(
            calibration.FORMAL_EXECUTION_AUTHORIZATION
        )


@pytest.mark.parametrize(
    "drift",
    [
        pytest.param(
            lambda module: setattr(
                module,
                "FROZEN_EXP001_CALIBRATION_ENV_CONFIG",
                replace(
                    module.FROZEN_EXP001_CALIBRATION_ENV_CONFIG,
                    resource_length_scale=0.20,
                ),
            ),
            id="environment-parameter",
        ),
        pytest.param(
            lambda module: setattr(
                module,
                "EXP002_SHARED_CONTROLLER_VALUES",
                replace(module.EXP002_SHARED_CONTROLLER_VALUES, recover=0.84),
            ),
            id="shared-controller-value",
        ),
        pytest.param(
            lambda module: setattr(
                module,
                "EXP002_B_CANDIDATES",
                tuple(
                    SimpleNamespace(
                        value=candidate.value,
                        enter_seek=(
                            0.36
                            if candidate is EXP002BCandidate.B35
                            else candidate.enter_seek
                        ),
                    )
                    for candidate in module.EXP002_B_CANDIDATES
                ),
            ),
            id="candidate-threshold",
        ),
        pytest.param(
            lambda module: setattr(
                module,
                "EXP002_CALIBRATION_SEEDS",
                tuple(range(40002, 40202)),
            ),
            id="calibration-seed-reservation",
        ),
        pytest.param(
            lambda module: setattr(module, "EXP002_COVERAGE_GRID_WIDTH", 31),
            id="coverage-dimension",
        ),
    ],
)
def test_scientific_contract_drift_is_rejected_before_simulator_construction(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    drift: object,
) -> None:
    artifact_path = tmp_path / "result.json"
    reservation_path = Path(f"{artifact_path}.reservation")
    monkeypatch.setattr(calibration, "FORMAL_ARTIFACT_PATH", artifact_path)
    monkeypatch.setattr(calibration, "_resolve_clean_git_sha", lambda _: "1" * 40)
    monkeypatch.setattr(
        calibration,
        "_run_episode",
        lambda **_: pytest.fail("scientific-contract drift reached simulator"),
    )
    assert callable(drift)
    drift(calibration)

    with pytest.raises(RuntimeError, match="scientific contract fingerprint"):
        calibration.run_exp002_formal_calibration(
            calibration.FORMAL_EXECUTION_AUTHORIZATION
        )
    assert not artifact_path.exists()
    assert not reservation_path.exists()


def test_failure_after_reservation_retains_marker_and_blocks_rerun(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    artifact_path = tmp_path / "result.json"
    reservation_path = Path(f"{artifact_path}.reservation")
    monkeypatch.setattr(calibration, "FORMAL_ARTIFACT_PATH", artifact_path)
    monkeypatch.setattr(calibration, "_formal_preflight", lambda _: "f" * 40)

    def fail_once(**_: object) -> object:
        raise RuntimeError("synthetic formal failure")

    monkeypatch.setattr(calibration, "_run_episode", fail_once)
    with pytest.raises(RuntimeError, match="synthetic formal failure"):
        calibration.run_exp002_formal_calibration(
            calibration.FORMAL_EXECUTION_AUTHORIZATION
        )
    assert reservation_path.exists()
    assert "status=in_progress" in reservation_path.read_text()

    monkeypatch.setattr(
        calibration,
        "_run_episode",
        lambda **_: pytest.fail("automatic retry reached simulator"),
    )
    with pytest.raises(FileExistsError):
        calibration.run_exp002_formal_calibration(
            calibration.FORMAL_EXECUTION_AUTHORIZATION
        )


def test_confirmatory_seed_cannot_enter_formal_batch() -> None:
    with pytest.raises(ValueError):
        calibration._run_formal_batches(
            seeds=EXP002_CONFIRMATORY_SEEDS,
            git_commit_sha="1" * 40,
            started_at="test",
        )
