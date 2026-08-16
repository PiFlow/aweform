import copy
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import pytest

import aweform.confirmatory as confirmatory
import aweform.runner as runner
from aweform import Condition

GIT_SHA = "a" * 40


def _json_config(value: Any) -> Any:
    return json.loads(json.dumps(asdict(value)))


def _payload(
    *,
    lifespan_difference: int = 2,
    b_lifespans: list[int] | None = None,
    c_lifespans: list[int] | None = None,
) -> dict[str, Any]:
    b_values = b_lifespans or [20 + lifespan_difference] * 100
    c_values = c_lifespans or [20] * 100
    summaries: list[dict[str, Any]] = []
    trajectories: list[dict[str, Any]] = []
    for index, seed in enumerate(confirmatory.ACCEPTANCE_SEEDS):
        for condition, lifespan in (
            (Condition.B_HOMEOSTATIC.value, b_values[index]),
            (Condition.C_ENERGY_BLIND.value, c_values[index]),
        ):
            summaries.append(_summary(condition, seed, lifespan))
            trajectories.append(
                {
                    "condition": condition,
                    "environment_seed": seed,
                    "initial_state": {},
                    "transitions": [{} for _ in range(lifespan)],
                }
            )
    return {
        "schema_version": confirmatory.CONFIRMATORY_ARTIFACT_SCHEMA_VERSION,
        "manifest": {
            "schema_version": confirmatory.CONFIRMATORY_MANIFEST_SCHEMA_VERSION,
            "experiment": "EXP-000",
            "purpose": "confirmatory",
            "protocol_revision": "EXP-000-confirmatory-v1",
            "git_commit_sha": GIT_SHA,
            "environment_config": _json_config(confirmatory.CONFIRMATORY_ENV_CONFIG),
            "homeostatic_config": _json_config(
                confirmatory.CONFIRMATORY_HOMEOSTATIC_CONFIG
            ),
            "energy_blind_masked_energy": confirmatory.CONFIRMATORY_MASKED_ENERGY,
            "environment_seeds": list(confirmatory.ACCEPTANCE_SEEDS),
            "conditions": [
                condition.value for condition in confirmatory.CONFIRMATORY_CONDITIONS
            ],
            "analysis_config": confirmatory.CONFIRMATORY_ANALYSIS_CONFIG,
            "python_version": "3.14.7",
            "numpy_version": "2.3.0",
            "gymnasium_version": "1.2.0",
            "aweform_package_version": "0.1.0",
            "platform": {"system": "test"},
            "run_started_at_utc": "2026-08-16T00:00:00+00:00",
        },
        "episode_summaries": summaries,
        "raw_trajectories": trajectories,
    }


def _summary(condition: str, seed: int, lifespan: int) -> dict[str, Any]:
    return {
        "condition": condition,
        "environment_seed": seed,
        "steps_executed": lifespan,
        "terminated_viability_failure": lifespan < 500,
        "truncated_at_horizon": lifespan == 500,
        "horizon_survival": lifespan == 500,
        "initial_normalized_energy": 0.5,
        "final_normalized_energy": 0.4,
        "minimum_normalized_energy": 0.3,
        "total_harvested_energy": 1.0,
        "total_basal_energy_cost": 2.0,
        "total_action_energy_cost": 3.0,
        "total_distance_travelled": 4.0,
        "explore_steps": 1,
        "seek_resource_steps": 2,
        "mode_transitions": 3,
    }


def _write_payload(tmp_path: Path, payload: dict[str, Any]) -> Path:
    path = tmp_path / "confirmatory.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_exact_seed_set_and_frozen_configuration_are_required(tmp_path: Path) -> None:
    payload = _payload()
    payload["manifest"]["environment_seeds"][-1] = 10101
    with pytest.raises(confirmatory.ConfirmatoryValidationError, match="seed set"):
        confirmatory.analyze_confirmatory_artifact(_write_payload(tmp_path, payload))

    for field, value in (
        ("resource_length_scale", 0.45),
        ("episode_horizon", 499),
    ):
        altered = _payload()
        altered["manifest"]["environment_config"][field] = value
        with pytest.raises(confirmatory.ConfirmatoryValidationError):
            confirmatory.analyze_confirmatory_artifact(
                _write_payload(tmp_path, altered)
            )

    altered_controller = _payload()
    altered_controller["manifest"]["homeostatic_config"]["recover"] = 0.8
    with pytest.raises(confirmatory.ConfirmatoryValidationError):
        confirmatory.analyze_confirmatory_artifact(
            _write_payload(tmp_path, altered_controller)
        )

    altered_mask = _payload()
    altered_mask["manifest"]["energy_blind_masked_energy"] = 0.2
    with pytest.raises(confirmatory.ConfirmatoryValidationError):
        confirmatory.analyze_confirmatory_artifact(
            _write_payload(tmp_path, altered_mask)
        )


def test_duplicate_and_missing_pairs_are_rejected(tmp_path: Path) -> None:
    payload = _payload()
    payload["episode_summaries"][2]["environment_seed"] = confirmatory.ACCEPTANCE_SEEDS[
        0
    ]
    with pytest.raises(confirmatory.ConfirmatoryValidationError, match="duplicate"):
        confirmatory.analyze_confirmatory_artifact(_write_payload(tmp_path, payload))

    missing = _payload()
    missing["episode_summaries"].pop()
    with pytest.raises(confirmatory.ConfirmatoryValidationError, match="exactly 200"):
        confirmatory.analyze_confirmatory_artifact(_write_payload(tmp_path, missing))


def test_primary_differences_and_frozen_bootstrap_are_deterministic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = _payload(
        b_lifespans=[21 + (index % 3) for index in range(100)],
        c_lifespans=[20] * 100,
    )
    calls: list[tuple[int, int, tuple[int, int]]] = []
    real_rng = np.random.default_rng

    class SpyRng:
        def integers(self, low: int, high: int, size: tuple[int, int]) -> np.ndarray:
            calls.append((low, high, size))
            return real_rng(0).integers(low, high, size=size)

    monkeypatch.setattr(np.random, "default_rng", lambda seed: SpyRng())
    path = _write_payload(tmp_path, payload)
    first = confirmatory.analyze_confirmatory_artifact(path)
    second = confirmatory.analyze_confirmatory_artifact(path)

    assert first.differences[:5] == (1.0, 2.0, 3.0, 1.0, 2.0)
    assert first.mean_difference == pytest.approx(1.99)
    assert first.ci_lower == second.ci_lower
    assert first.ci_upper == second.ci_upper
    assert calls == [
        (0, 100, (100_000, 100)),
        (0, 100, (100_000, 100)),
    ]


def test_quantile_method_and_expected_interval_are_frozen(tmp_path: Path) -> None:
    payload = _payload(
        b_lifespans=[21 if index % 2 == 0 else 20 for index in range(100)],
        c_lifespans=[20] * 100,
    )
    captured: list[str] = []
    real_quantile = np.quantile

    def spy_quantile(*args: Any, **kwargs: Any) -> Any:
        captured.append(str(kwargs["method"]))
        return real_quantile(*args, **kwargs)

    original = np.quantile
    try:
        np.quantile = spy_quantile
        result = confirmatory.analyze_confirmatory_artifact(
            _write_payload(tmp_path, payload)
        )
    finally:
        np.quantile = original

    expected = real_quantile(
        np.asarray(
            [
                np.asarray([1 if index % 2 == 0 else 0 for index in range(100)])[
                    indices
                ].mean()
                for indices in np.random.default_rng(0).integers(
                    0, 100, size=(100_000, 100)
                )
            ]
        ),
        np.asarray((0.025, 0.975), dtype=np.float64),
        method="linear",
    )
    assert captured == ["linear"]
    assert result.ci_lower == pytest.approx(float(expected[0]))
    assert result.ci_upper == pytest.approx(float(expected[1]))


@pytest.mark.parametrize(
    ("b_lifespans", "c_lifespans", "expected_support"),
    [
        ([25] * 100, [20] * 100, True),
        ([20] * 100, [20] * 100, False),
        ([101] * 99 + [10], [100] * 100, False),
        ([19] * 100, [20] * 100, False),
    ],
)
def test_support_criterion_and_negative_null_reports(
    tmp_path: Path,
    b_lifespans: list[int],
    c_lifespans: list[int],
    expected_support: bool,
) -> None:
    result = confirmatory.analyze_confirmatory_artifact(
        _write_payload(
            tmp_path,
            _payload(b_lifespans=b_lifespans, c_lifespans=c_lifespans),
        )
    )
    assert result.support is expected_support
    assert "Confirmatory support:" in result.to_markdown()


def test_secondary_diagnostics_cannot_change_support(tmp_path: Path) -> None:
    payload = _payload(b_lifespans=[25] * 100, c_lifespans=[20] * 100)
    baseline = confirmatory.analyze_confirmatory_artifact(
        _write_payload(tmp_path, payload)
    )
    altered = copy.deepcopy(payload)
    for summary in altered["episode_summaries"]:
        summary["total_harvested_energy"] = 999999.0
        summary["total_distance_travelled"] = 0.0
        summary["minimum_normalized_energy"] = 0.0
    changed = confirmatory.analyze_confirmatory_artifact(
        _write_payload(tmp_path, altered)
    )
    assert baseline.support is changed.support
    assert baseline.mean_difference == changed.mean_difference


def test_confirmatory_runner_hardcodes_exact_matched_b_c_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[int, Condition, object, object, float]] = []

    def fake_run_episode(**kwargs: Any) -> object:
        calls.append(
            (
                int(kwargs["environment_seed"]),
                kwargs["condition"],
                kwargs["env_config"],
                kwargs["homeostatic_config"],
                float(kwargs["masked_energy"]),
            )
        )
        return object()

    monkeypatch.setattr(confirmatory, "_run_episode", fake_run_episode)
    result = confirmatory.run_confirmatory_batch(GIT_SHA)

    assert len(result.episodes) == 200
    assert [call[0] for call in calls[::2]] == list(confirmatory.ACCEPTANCE_SEEDS)
    assert all(call[1] in confirmatory.CONFIRMATORY_CONDITIONS for call in calls)
    assert all(call[2] is confirmatory.CONFIRMATORY_ENV_CONFIG for call in calls)
    assert all(
        call[3] is confirmatory.CONFIRMATORY_HOMEOSTATIC_CONFIG for call in calls
    )
    assert all(call[4] == 0.5 for call in calls)


def test_confirmatory_writer_never_overwrites(tmp_path: Path) -> None:
    monkeypatched_result = confirmatory.ConfirmatoryBatchResult(
        manifest=confirmatory.ConfirmatoryManifest(
            schema_version=confirmatory.CONFIRMATORY_MANIFEST_SCHEMA_VERSION,
            experiment="EXP-000",
            purpose="confirmatory",
            protocol_revision="EXP-000-confirmatory-v1",
            git_commit_sha=GIT_SHA,
            environment_config={},
            homeostatic_config={},
            energy_blind_masked_energy=0.5,
            environment_seeds=confirmatory.ACCEPTANCE_SEEDS,
            conditions=tuple(
                condition.value for condition in confirmatory.CONFIRMATORY_CONDITIONS
            ),
            analysis_config=confirmatory.CONFIRMATORY_ANALYSIS_CONFIG,
            python_version="3.14.7",
            numpy_version="2.3.0",
            gymnasium_version="1.2.0",
            aweform_package_version="0.1.0",
            platform={},
            run_started_at_utc="2026-08-16T00:00:00+00:00",
        ),
        episodes=(),
    )
    output = tmp_path / "confirmatory.json"
    confirmatory.write_confirmatory_json(monkeypatched_result, output)
    original = output.read_text(encoding="utf-8")
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        confirmatory.write_confirmatory_json(monkeypatched_result, output)
    assert output.read_text(encoding="utf-8") == original


def test_development_runner_still_rejects_acceptance_seeds() -> None:
    with pytest.raises(ValueError, match="reserved acceptance seed"):
        runner.run_development_batch(
            seeds=[10001],
            env_config=confirmatory.CONFIRMATORY_ENV_CONFIG,
            homeostatic_config=confirmatory.CONFIRMATORY_HOMEOSTATIC_CONFIG,
            masked_energy=0.5,
            git_sha="test-sha",
        )
