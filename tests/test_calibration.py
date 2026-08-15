import copy
import json
from dataclasses import asdict
from pathlib import Path

import pytest

from aweform import AweformEnvConfig, HomeostaticConfig
from aweform.calibration import (
    ARTIFACT_SCHEMA_VERSION,
    CALIBRATION_SEEDS,
    CalibrationValidationError,
    summarize_calibration_artifacts,
)
from aweform.runner import MANIFEST_SCHEMA_VERSION, Condition


def _artifact_payload(
    length_scale: float,
    *,
    c_lifespan: int,
    b_recovery_seed_count: int = 6,
    b_lifespan: int = 2,
    git_sha: str = "calibration-test-sha",
) -> dict[str, object]:
    environment_config = asdict(
        AweformEnvConfig(
            episode_horizon=500,
            resource_count=1,
            resource_length_scale=length_scale,
        )
    )
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "experiment": "EXP-000",
        "purpose": "development",
        "git_commit_sha": git_sha,
        "environment_config": environment_config,
        "homeostatic_config": asdict(HomeostaticConfig()),
        "energy_blind_masked_energy": 0.5,
        "environment_seeds": list(CALIBRATION_SEEDS),
        "conditions": [condition.value for condition in Condition],
        "python_version": "fixture",
        "numpy_version": "fixture",
        "gymnasium_version": "fixture",
        "aweform_package_version": "fixture",
        "platform": {"system": "fixture"},
        "run_started_at_utc": "2026-01-01T00:00:00+00:00",
        "metadata": {},
    }
    summaries: list[dict[str, object]] = []
    trajectories: list[dict[str, object]] = []
    for seed in CALIBRATION_SEEDS:
        for condition in Condition:
            if (
                condition is Condition.A_PERSISTENT
                or condition is Condition.C_ENERGY_BLIND
            ):
                lifespan = c_lifespan
            else:
                lifespan = b_lifespan
            recovery = (
                condition is Condition.B_HOMEOSTATIC
                and seed < 1001 + b_recovery_seed_count
            )
            summaries.append(_summary(condition, seed, lifespan, recovery=recovery))
            trajectories.append(
                _trajectory(condition, seed, lifespan, recovery=recovery)
            )
    return {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "manifest": manifest,
        "episode_summaries": summaries,
        "raw_trajectories": trajectories,
    }


def _summary(
    condition: Condition,
    seed: int,
    lifespan: int,
    *,
    recovery: bool,
) -> dict[str, object]:
    mode_fields: dict[str, int | None]
    if condition is Condition.B_HOMEOSTATIC:
        mode_fields = {
            "explore_steps": lifespan - 1 if recovery else lifespan,
            "seek_resource_steps": 1 if recovery else 0,
            "mode_transitions": 1 if recovery else 0,
        }
    else:
        mode_fields = {
            "explore_steps": None,
            "seek_resource_steps": None,
            "mode_transitions": None,
        }
    return {
        "condition": condition.value,
        "environment_seed": seed,
        "steps_executed": lifespan,
        "terminated_viability_failure": not lifespan == 500,
        "truncated_at_horizon": lifespan == 500,
        "horizon_survival": lifespan == 500,
        "initial_normalized_energy": 0.5,
        "final_normalized_energy": 0.5,
        "minimum_normalized_energy": 0.4,
        "total_harvested_energy": 2.0,
        "total_basal_energy_cost": 1.0,
        "total_action_energy_cost": 3.0,
        "total_distance_travelled": 4.0,
        **mode_fields,
    }


def _trajectory(
    condition: Condition,
    seed: int,
    lifespan: int,
    *,
    recovery: bool,
) -> dict[str, object]:
    transitions: list[dict[str, object]] = []
    for step in range(lifespan):
        if condition is Condition.A_PERSISTENT:
            mode: str | None = None
        elif recovery and step == 0:
            mode = "SEEK_RESOURCE"
        else:
            mode = "EXPLORE"
        transitions.append(
            {
                "step_index": step + 1,
                "x": 0.1 + step * 0.001,
                "y": 0.2,
                "heading": 0.3,
                "energy": 5.0,
                "action": 3,
                "observation": [0.5, 0.0, 0.0, 0.0],
                "harvested_energy": 0.2,
                "basal_cost": 0.1,
                "action_cost": 0.1,
                "energy_before": 5.0,
                "energy_after": 5.0,
                "terminated": lifespan != 500 and step == lifespan - 1,
                "truncated": lifespan == 500 and step == lifespan - 1,
                "mode": mode,
            }
        )
    return {
        "condition": condition.value,
        "environment_seed": seed,
        "initial_state": {
            "x": 0.1,
            "y": 0.2,
            "heading": 0.3,
            "energy": 5.0,
            "source_positions": [[0.5, 0.5]],
        },
        "transitions": transitions,
    }


def _write_artifacts(
    tmp_path: Path,
    payloads: list[dict[str, object]],
) -> list[Path]:
    paths: list[Path] = []
    for index, payload in enumerate(payloads):
        path = tmp_path / f"calibration-{index}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        paths.append(path)
    return paths


@pytest.fixture(scope="module")
def valid_payloads() -> list[dict[str, object]]:
    return [
        _artifact_payload(0.15, c_lifespan=100),
        _artifact_payload(0.20, c_lifespan=250),
        _artifact_payload(0.25, c_lifespan=400),
    ]


def test_accepts_valid_set_and_computes_frozen_diagnostics(
    tmp_path: Path, valid_payloads: list[dict[str, object]]
) -> None:
    summary = summarize_calibration_artifacts(
        _write_artifacts(tmp_path, copy.deepcopy(valid_payloads))
    )

    assert summary.selected_candidate is not None
    assert summary.selected_candidate.resource_length_scale == pytest.approx(0.20)
    candidate = summary.candidates[1]
    c = candidate.by_condition[Condition.C_ENERGY_BLIND.value]
    assert c.episode_count == 30
    assert c.mean_lifespan == pytest.approx(250.0)
    assert c.median_lifespan == pytest.approx(250.0)
    assert c.minimum_lifespan == 250
    assert c.maximum_lifespan == 250
    assert c.horizon_survival_count == 0
    assert c.horizon_survival_fraction == pytest.approx(0.0)
    assert candidate.b_recovery_seed_count == 6
    assert candidate.b_total_recoveries == 6
    assert candidate.a_c_identical_seed_count == 30
    assert candidate.a_c_divergent_seed_count == 0
    assert candidate.c_distance_from_midpoint == pytest.approx(0.0)


@pytest.mark.parametrize(
    "mutation, message",
    [
        (lambda payloads: payloads.pop(), "exactly three"),
        (
            lambda payloads: payloads.__setitem__(1, copy.deepcopy(payloads[0])),
            "duplicate",
        ),
        (
            lambda payloads: payloads[0]["manifest"].__setitem__(
                "environment_seeds", [10001] + list(CALIBRATION_SEEDS[1:])
            ),
            "1001",
        ),
        (
            lambda payloads: payloads[0]["manifest"].__setitem__(
                "energy_blind_masked_energy", 0.2
            ),
            "0.5",
        ),
        (
            lambda payloads: payloads[0]["manifest"]["environment_config"].__setitem__(
                "resource_count", 2
            ),
            "resource_count",
        ),
        (
            lambda payloads: payloads[0]["manifest"]["environment_config"].__setitem__(
                "episode_horizon", 100
            ),
            "episode_horizon",
        ),
        (
            lambda payloads: payloads[1]["manifest"].__setitem__(
                "git_commit_sha", "other-sha"
            ),
            "Git commit SHA",
        ),
        (
            lambda payloads: payloads[1]["manifest"]["environment_config"].__setitem__(
                "movement_distance", 0.06
            ),
            "formal protocol",
        ),
        (
            lambda payloads: payloads[0].__setitem__("schema_version", "unsupported"),
            "schema version",
        ),
    ],
)
def test_rejects_invalid_calibration_artifacts(
    tmp_path: Path,
    valid_payloads: list[dict[str, object]],
    mutation: object,
    message: str,
) -> None:
    payloads = copy.deepcopy(valid_payloads)
    mutation(payloads)  # type: ignore[operator]
    with pytest.raises(CalibrationValidationError, match=message):
        summarize_calibration_artifacts(_write_artifacts(tmp_path, payloads))


def test_rejects_a_c_divergence_and_reports_it_when_valid(
    tmp_path: Path, valid_payloads: list[dict[str, object]]
) -> None:
    payloads = copy.deepcopy(valid_payloads)
    trajectory = payloads[0]["raw_trajectories"][0]
    trajectory["transitions"][0]["action"] = 1
    summary = summarize_calibration_artifacts(_write_artifacts(tmp_path, payloads))

    candidate = summary.candidates[0]
    assert candidate.a_c_identical_seed_count == 29
    assert candidate.a_c_divergent_seed_count == 1
    assert "Protocol-selected candidate" in summary.to_markdown()


def test_selection_uses_c_difficulty_and_smaller_scale_tie_break_only(
    tmp_path: Path,
) -> None:
    payloads = [
        _artifact_payload(0.15, c_lifespan=200, b_lifespan=2),
        _artifact_payload(0.20, c_lifespan=300, b_lifespan=400),
        _artifact_payload(0.25, c_lifespan=500, b_lifespan=1),
    ]
    summary = summarize_calibration_artifacts(_write_artifacts(tmp_path, payloads))

    assert summary.selected_candidate is not None
    assert summary.selected_candidate.resource_length_scale == pytest.approx(0.15)


def test_returns_no_acceptable_candidate_without_suggesting_new_values(
    tmp_path: Path,
) -> None:
    payloads = [
        _artifact_payload(0.15, c_lifespan=99, b_recovery_seed_count=5),
        _artifact_payload(0.20, c_lifespan=401, b_recovery_seed_count=5),
        _artifact_payload(0.25, c_lifespan=500, b_recovery_seed_count=5),
    ]
    summary = summarize_calibration_artifacts(_write_artifacts(tmp_path, payloads))

    assert summary.selected_candidate is None
    assert (
        "No calibration candidate satisfies the frozen selection rule."
        in summary.to_markdown()
    )


def test_b_outcomes_cannot_change_selection_when_c_rule_is_fixed(
    tmp_path: Path, valid_payloads: list[dict[str, object]]
) -> None:
    payloads = copy.deepcopy(valid_payloads)
    for payload in payloads:
        for summary in payload["episode_summaries"]:
            if summary["condition"] == Condition.B_HOMEOSTATIC.value:
                summary["total_harvested_energy"] = 999.0
                summary["final_normalized_energy"] = 0.99
    result = summarize_calibration_artifacts(_write_artifacts(tmp_path, payloads))

    assert result.selected_candidate is not None
    assert result.selected_candidate.resource_length_scale == pytest.approx(0.20)
