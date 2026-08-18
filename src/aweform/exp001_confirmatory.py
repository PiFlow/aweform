"""Frozen EXP-001 confirmatory execution and artifact-only analysis.

This module is deliberately separate from the historical EXP-000 confirmatory
instrument.  The formal execution path is gated, owns the reserved seed
authorization, persists compact summaries only, and never exposes a public
output-path override.  The analysis path accepts an already-persisted artifact
and does not import or execute the simulator loop.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import re
import statistics
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final, cast

import numpy as np

from .env import AweformEnvConfig
from .exp001 import EXP001Mode
from .exp001_calibration import (
    CALIBRATED_C,
    CALIBRATED_C_NAME,
    EXP001_PROTOCOL_REVISION,
    FROZEN_EXP001_CALIBRATION_ENV_CONFIG,
    FROZEN_EXP001_SHARED_CONTROLLER_CONFIG,
    _count_complete_cycles,
    _normalize_energy,
)
from .exp001_runner import (
    EXP001Condition,
    EXP001EpisodeRecord,
    _run_episode,
)
from .exp001_seed_policy import CONFIRMATORY_SEEDS, _validate_exp001_seed_sequence

EXP001_CONFIRMATORY_EXECUTION_AUTHORIZATION: Final = (
    "EXP-001-confirmatory-execution-001"
)
EXP001_CONFIRMATORY_ARTIFACT_SCHEMA_VERSION: Final = "exp-001-confirmatory-v1"
EXP001_CONFIRMATORY_MANIFEST_SCHEMA_VERSION: Final = "exp-001-confirmatory-manifest-v1"
EXP001_CONFIRMATORY_ANALYSIS_SCHEMA_VERSION: Final = "exp-001-confirmatory-analysis-v1"
EXP001_CONFIRMATORY_ARTIFACT_RELATIVE_PATH: Final = Path(
    "artifacts/EXP-001-confirmatory.json"
)
EXP001_CONFIRMATORY_RESERVATION_SUFFIX: Final = ".reservation"
EXP001_CALIBRATION_ARTIFACT_RELATIVE_PATH: Final = Path(
    "artifacts/EXP-001-formal-calibration-precalibration-003.json"
)
EXP001_CALIBRATION_ARTIFACT_SHA256: Final = (
    "1fe4ce9217d93b70c94a7a81dbe949f971d95401e83d7056b5bd8374696f17e4"
)
EXP001_CONFIRMATORY_HORIZON: Final = 1000
EXP001_CONFIRMATORY_EPISODE_COUNT: Final = 3000
EXP001_CONFIRMATORY_CONDITION_COUNT: Final = 3
EXP001_BOOTSTRAP_RESAMPLES: Final = 50_000
EXP001_BOOTSTRAP_RNG_SEED: Final = 91001
EXP001_BOOTSTRAP_BIT_GENERATOR: Final = "PCG64"
EXP001_BOOTSTRAP_QUANTILE_METHOD: Final = "linear"
EXP001_BOOTSTRAP_CONFIDENCE_LEVEL: Final = 0.95
PRIMARY_ESTIMAND_IDENTIFIER: Final = "mean_paired_capped_lifespan_B_minus_calibrated_C"
INTERPRETATION_B_GREATER: Final = "B_GREATER"
INTERPRETATION_C_GREATER: Final = "C_GREATER"
INTERPRETATION_UNRESOLVED: Final = "UNRESOLVED"

_GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_CALIBRATED_C_CONFIG = FROZEN_EXP001_SHARED_CONTROLLER_CONFIG.for_candidate(
    CALIBRATED_C
)
_FORMAL_CONDITIONS: Final = (
    EXP001Condition.A,
    EXP001Condition.B,
    EXP001Condition.C,
)
_SUMMARY_FIELDS: Final = (
    "condition",
    "environment_seed",
    "capped_lifespan",
    "completed_transitions",
    "terminated_viability_failure",
    "horizon_survival",
    "final_normalized_energy",
    "minimum_normalized_energy",
    "total_harvested_energy",
    "total_basal_energy_cost",
    "total_action_energy_cost",
    "total_distance_travelled",
    "explore_action_count",
    "seek_resource_action_count",
    "charge_action_count",
    "complete_recharge_cycle_count",
)
_BOOLEAN_SUMMARY_FIELDS = frozenset(
    {"terminated_viability_failure", "horizon_survival"}
)
_COUNT_SUMMARY_FIELDS = frozenset(
    {
        "capped_lifespan",
        "completed_transitions",
        "explore_action_count",
        "seek_resource_action_count",
        "charge_action_count",
        "complete_recharge_cycle_count",
    }
)
_ENERGY_SUMMARY_FIELDS = frozenset(
    {"final_normalized_energy", "minimum_normalized_energy"}
)
_NONNEGATIVE_FLOAT_FIELDS = frozenset(
    {
        "total_harvested_energy",
        "total_basal_energy_cost",
        "total_action_energy_cost",
        "total_distance_travelled",
    }
)


class EXP001ConfirmatoryValidationError(ValueError):
    """Raised when an EXP-001 confirmatory artifact is malformed."""


class EXP001ConfirmatoryGitError(ValueError):
    """Raised when formal execution cannot establish Git provenance."""


@dataclass(frozen=True, slots=True)
class EXP001ExecutionReservation:
    """A retained exclusive formal execution reservation."""

    artifact_path: Path
    reservation_path: Path


@dataclass(frozen=True, slots=True)
class EXP001FormalExecutionReceipt:
    """Operational receipt returned only after the artifact is persisted."""

    artifact_path: Path
    artifact_sha256: str
    git_commit_sha: str
    episode_count: int


@dataclass(frozen=True, slots=True)
class EXP001EpisodeSummary:
    """Compact evaluator-side summary for one condition and master seed."""

    condition: str
    environment_seed: int
    capped_lifespan: int
    completed_transitions: int
    terminated_viability_failure: bool
    horizon_survival: bool
    final_normalized_energy: float
    minimum_normalized_energy: float
    total_harvested_energy: float
    total_basal_energy_cost: float
    total_action_energy_cost: float
    total_distance_travelled: float
    explore_action_count: int
    seek_resource_action_count: int
    charge_action_count: int
    complete_recharge_cycle_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class EXP001ConfirmatoryManifest:
    """Complete provenance and frozen analysis configuration."""

    schema_version: str
    experiment: str
    purpose: str
    protocol_revision: str
    execution_authorization: str
    git_commit_sha: str
    tracked_worktree_provenance: Mapping[str, Any]
    python_version: str
    numpy_version: str
    environment_config: Mapping[str, Any]
    shared_controller_config: Mapping[str, Any]
    calibrated_c_name: str
    calibrated_c_explore_duration: int
    calibrated_c_charge_duration: int
    calibration_artifact_sha256: str
    confirmatory_seed_range: Mapping[str, int]
    conditions: tuple[str, ...]
    primary_estimand_identifier: str
    bootstrap_specification: Mapping[str, Any]
    episode_count: int
    raw_trajectories_persisted: bool
    run_started_at_utc: str

    def to_dict(self) -> dict[str, Any]:
        return cast(dict[str, Any], _json_value(asdict(self)))


@dataclass(frozen=True, slots=True)
class EXP001ConfirmatoryArtifact:
    """In-memory result that is safe to serialize: manifest plus summaries."""

    manifest: EXP001ConfirmatoryManifest
    episode_summaries: tuple[EXP001EpisodeSummary, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": EXP001_CONFIRMATORY_ARTIFACT_SCHEMA_VERSION,
            "manifest": self.manifest.to_dict(),
            "episode_summaries": [
                summary.to_dict() for summary in self.episode_summaries
            ],
        }

    def to_json(self) -> str:
        return (
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)
            + "\n"
        )


@dataclass(frozen=True, slots=True)
class EXP001ConfirmatoryAnalysis:
    """Frozen paired primary result and descriptive diagnostics."""

    source_artifact_sha256: str
    git_commit_sha: str
    seeds: tuple[int, ...]
    differences: tuple[float, ...]
    mean_difference: float
    ci_lower: float
    ci_upper: float
    interpretation: str
    descriptive_diagnostics: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": EXP001_CONFIRMATORY_ANALYSIS_SCHEMA_VERSION,
            "source_artifact_sha256": self.source_artifact_sha256,
            "artifact_only": True,
            "simulator_executed": False,
            "experiment": "EXP-001",
            "protocol_revision": EXP001_PROTOCOL_REVISION,
            "git_commit_sha": self.git_commit_sha,
            "primary": {
                "estimand_identifier": PRIMARY_ESTIMAND_IDENTIFIER,
                "mean_paired_difference": self.mean_difference,
                "confidence_interval": {
                    "level": EXP001_BOOTSTRAP_CONFIDENCE_LEVEL,
                    "lower": self.ci_lower,
                    "upper": self.ci_upper,
                    "method": "paired_percentile_bootstrap",
                },
                "n": len(self.seeds),
                "interpretation": self.interpretation,
                "bootstrap": {
                    "replicates": EXP001_BOOTSTRAP_RESAMPLES,
                    "rng": "numpy.random.Generator",
                    "bit_generator": EXP001_BOOTSTRAP_BIT_GENERATOR,
                    "seed": EXP001_BOOTSTRAP_RNG_SEED,
                    "quantile_method": EXP001_BOOTSTRAP_QUANTILE_METHOD,
                },
            },
            "matched_differences": list(self.differences),
            "descriptive_diagnostics": _json_value(self.descriptive_diagnostics),
            "a_status": "descriptive reference only; excluded from primary analysis",
            "inference_boundary": (
                "Inference is restricted to mean capped lifespan within the frozen "
                "1000-transition EXP-001 simulator environment."
            ),
        }

    def to_markdown(self) -> str:
        diagnostics = self.descriptive_diagnostics
        lines = [
            "# EXP-001 Confirmatory Analysis",
            "",
            "This report was generated from an already-persisted confirmatory "
            "artifact. It did not execute the simulator.",
            "",
            f"- Source artifact SHA-256: `{self.source_artifact_sha256}`",
            f"- Git SHA recorded in artifact: `{self.git_commit_sha}`",
            f"- Matched pairs: `n = {len(self.seeds)}`",
            "- A status: descriptive reference only; excluded from the primary "
            "difference, bootstrap, and interpretation",
            "",
            "## Primary endpoint",
            "",
            "The frozen primary estimand is the mean paired "
            "`capped_lifespan_B - capped_lifespan_C` difference.",
            "",
            f"- Mean paired B−C difference: `{self.mean_difference:.6f}` transitions",
            f"- 95% paired percentile-bootstrap interval: "
            f"`[{self.ci_lower:.6f}, {self.ci_upper:.6f}]` transitions",
            f"- Interpretation: `{self.interpretation}`",
            f"- Bootstrap: `{EXP001_BOOTSTRAP_RESAMPLES:,}` paired-difference "
            f"resamples; `Generator(PCG64({EXP001_BOOTSTRAP_RNG_SEED}))`; "
            f"percentile method `{EXP001_BOOTSTRAP_QUANTILE_METHOD}`",
            "- No primary p-value is calculated.",
            "",
            "## Descriptive diagnostics",
            "",
            "The following are descriptive only and cannot replace or reinterpret "
            "the B−C primary endpoint.",
            "",
        ]
        lines.extend(_diagnostic_markdown(diagnostics))
        lines.extend(
            [
                "",
                "Inference is limited to the frozen 1000-transition simulator "
                "environment. It is not evidence about biological organisms, a "
                "physical Aweform, consciousness, or lifetime beyond 1000 "
                "transitions.",
                "",
            ]
        )
        return "\n".join(lines)


def validate_exp001_formal_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    """Require exactly the canonical confirmatory tuple, including order."""
    validated = _validate_exp001_seed_sequence(seeds)
    if validated != CONFIRMATORY_SEEDS:
        raise ValueError(
            "formal EXP-001 confirmation requires exactly CONFIRMATORY_SEEDS "
            "in canonical order"
        )
    return validated


def validate_calibrated_c_against_artifact(repository_path: Path) -> None:
    """Verify code-level SHORT selection against the committed calibration file."""
    artifact_path = repository_path / EXP001_CALIBRATION_ARTIFACT_RELATIVE_PATH
    if _sha256_file(artifact_path) != EXP001_CALIBRATION_ARTIFACT_SHA256:
        raise EXP001ConfirmatoryValidationError(
            "committed EXP-001 calibration artifact SHA-256 does not match the "
            "frozen calibration record"
        )
    try:
        with artifact_path.open(encoding="utf-8") as file:
            payload = json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        raise EXP001ConfirmatoryValidationError(
            "could not read the committed EXP-001 calibration artifact"
        ) from error
    if not isinstance(payload, Mapping):
        raise EXP001ConfirmatoryValidationError("calibration artifact root is invalid")
    if payload.get("selected_candidate") != CALIBRATED_C_NAME:
        raise EXP001ConfirmatoryValidationError(
            "code-level calibrated C disagrees with the committed calibration "
            "artifact selection"
        )
    summaries = payload.get("candidate_summaries")
    if not isinstance(summaries, list):
        raise EXP001ConfirmatoryValidationError(
            "calibration artifact candidate summaries are invalid"
        )
    selected = [
        row
        for row in summaries
        if isinstance(row, Mapping) and row.get("candidate") == CALIBRATED_C_NAME
    ]
    if len(selected) != 1 or (
        selected[0].get("explore_duration") != CALIBRATED_C.explore_duration
        or selected[0].get("charge_duration") != CALIBRATED_C.charge_duration
    ):
        raise EXP001ConfirmatoryValidationError(
            "code-level calibrated C timers disagree with the committed "
            "calibration artifact"
        )


def summarize_exp001_confirmatory_episode(
    episode: EXP001EpisodeRecord,
    environment_config: AweformEnvConfig = FROZEN_EXP001_CALIBRATION_ENV_CONFIG,
) -> EXP001EpisodeSummary:
    """Reduce one raw development episode to the frozen compact schema."""
    if episode.condition not in _FORMAL_CONDITIONS:
        raise ValueError("episode condition is not a formal EXP-001 condition")
    if not episode.transitions:
        raise ValueError("confirmatory episode must contain transitions")
    transitions = episode.transitions
    final_transition = transitions[-1].privileged_evaluator
    terminated = bool(final_transition.terminated)
    truncated = bool(final_transition.truncated)
    if terminated == truncated:
        raise ValueError("episode must terminate by viability failure or horizon")
    lifespan = min(len(transitions), EXP001_CONFIRMATORY_HORIZON)
    mode_sequence = tuple(
        transition.privileged_evaluator.controller_mode for transition in transitions
    )
    energy_values = (
        _normalize_energy(episode.initial_state.actual_energy, environment_config),
        *(
            _normalize_energy(
                transition.privileged_evaluator.actual_energy,
                environment_config,
            )
            for transition in transitions
        ),
    )
    distance = 0.0
    previous_position = episode.initial_state.position
    for transition in transitions:
        position = transition.privileged_evaluator.position
        distance += math.hypot(
            position[0] - previous_position[0], position[1] - previous_position[1]
        )
        previous_position = position
    return EXP001EpisodeSummary(
        condition=episode.condition.value,
        environment_seed=episode.environment_seed,
        capped_lifespan=lifespan,
        completed_transitions=len(transitions),
        terminated_viability_failure=terminated,
        horizon_survival=truncated
        and not terminated
        and lifespan == EXP001_CONFIRMATORY_HORIZON,
        final_normalized_energy=float(energy_values[-1]),
        minimum_normalized_energy=float(min(energy_values)),
        total_harvested_energy=math.fsum(
            transition.privileged_evaluator.harvested_energy
            for transition in transitions
        ),
        total_basal_energy_cost=math.fsum(
            transition.privileged_evaluator.basal_cost for transition in transitions
        ),
        total_action_energy_cost=math.fsum(
            transition.privileged_evaluator.action_cost for transition in transitions
        ),
        total_distance_travelled=distance,
        explore_action_count=sum(mode is EXP001Mode.EXPLORE for mode in mode_sequence),
        seek_resource_action_count=sum(
            mode is EXP001Mode.SEEK_RESOURCE for mode in mode_sequence
        ),
        charge_action_count=sum(mode is EXP001Mode.CHARGE for mode in mode_sequence),
        complete_recharge_cycle_count=_count_complete_cycles(mode_sequence),
    )


def _run_formal_exp001_episodes(
    seeds: Sequence[int],
) -> tuple[EXP001EpisodeSummary, ...]:
    """Run exactly A, B, C per approved seed using the reviewed loop."""
    validated_seeds = validate_exp001_formal_seeds(seeds)
    summaries: list[EXP001EpisodeSummary] = []
    for seed in validated_seeds:
        for condition in _FORMAL_CONDITIONS:
            episode = _run_episode(
                condition=condition,
                environment_seed=seed,
                env_config=FROZEN_EXP001_CALIBRATION_ENV_CONFIG,
                development_config=_CALIBRATED_C_CONFIG,
            )
            summaries.append(summarize_exp001_confirmatory_episode(episode))
    if len(summaries) != EXP001_CONFIRMATORY_EPISODE_COUNT:
        raise RuntimeError("formal EXP-001 execution did not produce 3000 summaries")
    return tuple(summaries)


def resolve_exp001_git_provenance(
    repository_path: Path | None = None,
) -> tuple[Path, str, Mapping[str, Any]]:
    """Return repository, full SHA, and tracked-worktree provenance."""
    working_directory = repository_path or Path.cwd()
    root = Path(_git_stdout(("rev-parse", "--show-toplevel"), working_directory))
    sha = _git_stdout(("rev-parse", "HEAD"), root)
    if not _GIT_SHA_PATTERN.fullmatch(sha):
        raise EXP001ConfirmatoryGitError("Git HEAD is not a full 40-hex SHA")
    for args in (
        ("diff", "--quiet", "--no-ext-diff"),
        ("diff", "--cached", "--quiet"),
    ):
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise EXP001ConfirmatoryGitError(
                "tracked working tree is not clean; formal confirmation aborted"
            )
    untracked_result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    untracked_lines = tuple(
        line for line in untracked_result.stdout.splitlines() if line.startswith("?? ")
    )
    return (
        root,
        sha,
        {
            "tracked_worktree_clean": True,
            "untracked_files_present": bool(untracked_lines),
            "untracked_file_count": len(untracked_lines),
        },
    )


def execute_exp001_confirmatory(
    authorization: str,
) -> EXP001FormalExecutionReceipt:
    """Run once and persist the canonical EXP-001 confirmatory artifact."""
    if authorization != EXP001_CONFIRMATORY_EXECUTION_AUTHORIZATION:
        raise PermissionError(
            "formal EXP-001 confirmation requires authorization "
            f"{EXP001_CONFIRMATORY_EXECUTION_AUTHORIZATION!r}"
        )
    return _execute_exp001_confirmatory_for_repository(Path.cwd())


def _execute_exp001_confirmatory_for_repository(
    repository_path: Path,
) -> EXP001FormalExecutionReceipt:
    repository, git_sha, tracked_provenance = resolve_exp001_git_provenance(
        repository_path
    )
    validate_calibrated_c_against_artifact(repository)
    artifact_path = repository / EXP001_CONFIRMATORY_ARTIFACT_RELATIVE_PATH
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    reservation = _acquire_exp001_reservation(artifact_path, git_sha)
    try:
        summaries = _run_formal_exp001_episodes(CONFIRMATORY_SEEDS)
        manifest = _build_manifest(git_sha, tracked_provenance)
        artifact = EXP001ConfirmatoryArtifact(manifest, summaries)
        artifact_sha = _write_exp001_artifact_atomically(
            artifact_path, artifact.to_json()
        )
        _mark_exp001_reservation_completed(reservation, artifact_sha)
    except BaseException:
        # The marker is intentionally retained for independent review.
        raise
    return EXP001FormalExecutionReceipt(
        artifact_path=artifact_path,
        artifact_sha256=artifact_sha,
        git_commit_sha=git_sha,
        episode_count=len(summaries),
    )


def _acquire_exp001_reservation(
    artifact_path: Path,
    git_sha: str,
) -> EXP001ExecutionReservation:
    reservation_path = Path(f"{artifact_path}{EXP001_CONFIRMATORY_RESERVATION_SUFFIX}")
    if artifact_path.exists():
        raise FileExistsError(
            f"refusing formal rerun: artifact already exists at {artifact_path}"
        )
    descriptor = -1
    try:
        descriptor = os.open(
            reservation_path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o644,
        )
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            descriptor = -1
            file.write(
                "{\n"
                '  "status": "reserved",\n'
                f'  "git_commit_sha": "{git_sha}",\n'
                f'  "pid": {os.getpid()},\n'
                f'  "started_at_utc": "{datetime.now(timezone.utc).isoformat()}"\n'
                "}\n"
            )
    except FileExistsError as error:
        raise FileExistsError(
            f"refusing formal rerun: reservation exists at {reservation_path}"
        ) from error
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        raise
    return EXP001ExecutionReservation(artifact_path, reservation_path)


def _mark_exp001_reservation_completed(
    reservation: EXP001ExecutionReservation,
    artifact_sha256: str,
) -> None:
    payload = (
        f'{{\n  "status": "completed",\n  "artifact_sha256": "{artifact_sha256}"\n}}\n'
    )
    _write_text_atomically(reservation.reservation_path, payload, replace=True)


def _build_manifest(
    git_sha: str,
    tracked_provenance: Mapping[str, Any],
) -> EXP001ConfirmatoryManifest:
    return EXP001ConfirmatoryManifest(
        schema_version=EXP001_CONFIRMATORY_MANIFEST_SCHEMA_VERSION,
        experiment="EXP-001",
        purpose="confirmatory",
        protocol_revision=EXP001_PROTOCOL_REVISION,
        execution_authorization=EXP001_CONFIRMATORY_EXECUTION_AUTHORIZATION,
        git_commit_sha=git_sha,
        tracked_worktree_provenance=tracked_provenance,
        python_version=platform.python_version(),
        numpy_version=np.__version__,
        environment_config=_json_value(asdict(FROZEN_EXP001_CALIBRATION_ENV_CONFIG)),
        shared_controller_config=asdict(FROZEN_EXP001_SHARED_CONTROLLER_CONFIG),
        calibrated_c_name=CALIBRATED_C_NAME,
        calibrated_c_explore_duration=CALIBRATED_C.explore_duration,
        calibrated_c_charge_duration=CALIBRATED_C.charge_duration,
        calibration_artifact_sha256=EXP001_CALIBRATION_ARTIFACT_SHA256,
        confirmatory_seed_range={
            "start": CONFIRMATORY_SEEDS[0],
            "end": CONFIRMATORY_SEEDS[-1],
            "count": len(CONFIRMATORY_SEEDS),
        },
        conditions=tuple(condition.value for condition in _FORMAL_CONDITIONS),
        primary_estimand_identifier=PRIMARY_ESTIMAND_IDENTIFIER,
        bootstrap_specification={
            "resampling_unit": "matched_seed_paired_difference",
            "replicates": EXP001_BOOTSTRAP_RESAMPLES,
            "rng": "numpy.random.Generator",
            "bit_generator": EXP001_BOOTSTRAP_BIT_GENERATOR,
            "seed": EXP001_BOOTSTRAP_RNG_SEED,
            "sample_size": len(CONFIRMATORY_SEEDS),
            "confidence_level": EXP001_BOOTSTRAP_CONFIDENCE_LEVEL,
            "quantile_method": EXP001_BOOTSTRAP_QUANTILE_METHOD,
        },
        episode_count=EXP001_CONFIRMATORY_EPISODE_COUNT,
        raw_trajectories_persisted=False,
        run_started_at_utc=datetime.now(timezone.utc).isoformat(),
    )


def _write_exp001_artifact_atomically(path: Path, serialized: str) -> str:
    _write_text_atomically(path, serialized, replace=False)
    return _sha256_file(path)


def _write_text_atomically(path: Path, content: str, *, replace: bool) -> None:
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as file:
            temporary_path = Path(file.name)
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        if replace:
            os.replace(temporary_path, path)
            temporary_path = None
        else:
            os.link(temporary_path, path)
            temporary_path.unlink()
            temporary_path = None
    except BaseException:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise


def analyze_exp001_confirmatory_artifact(
    artifact_path: str | os.PathLike[str],
) -> EXP001ConfirmatoryAnalysis:
    """Validate and analyze an existing artifact without simulator execution."""
    path = Path(artifact_path)
    try:
        with path.open(encoding="utf-8") as file:
            payload = json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        raise EXP001ConfirmatoryValidationError(
            f"could not read valid EXP-001 confirmatory JSON: {error}"
        ) from error
    root = _mapping(payload, "artifact root")
    if set(root) != {"schema_version", "manifest", "episode_summaries"}:
        raise EXP001ConfirmatoryValidationError(
            "artifact must contain only schema_version, manifest, and "
            "episode_summaries; raw trajectories are forbidden"
        )
    manifest = _validate_manifest(root["manifest"], path)
    rows = _validate_summary_rows(root["episode_summaries"], path)
    row_map = _summary_map(rows)
    expected_keys = {
        (condition.value, seed)
        for seed in CONFIRMATORY_SEEDS
        for condition in _FORMAL_CONDITIONS
    }
    if set(row_map) != expected_keys:
        raise EXP001ConfirmatoryValidationError(
            "artifact must contain exactly one A, B, and C row per canonical seed"
        )
    by_condition = {
        condition.value: tuple(
            row_map[(condition.value, seed)] for seed in CONFIRMATORY_SEEDS
        )
        for condition in _FORMAL_CONDITIONS
    }
    b_lifespans = np.asarray(
        [row["capped_lifespan"] for row in by_condition[EXP001Condition.B.value]],
        dtype=np.float64,
    )
    c_lifespans = np.asarray(
        [row["capped_lifespan"] for row in by_condition[EXP001Condition.C.value]],
        dtype=np.float64,
    )
    differences = b_lifespans - c_lifespans
    ci_lower, ci_upper = _paired_percentile_bootstrap(differences)
    diagnostics = _descriptive_diagnostics(by_condition, differences)
    return EXP001ConfirmatoryAnalysis(
        source_artifact_sha256=_sha256_file(path),
        git_commit_sha=str(manifest["git_commit_sha"]),
        seeds=CONFIRMATORY_SEEDS,
        differences=tuple(float(value) for value in differences),
        mean_difference=float(np.mean(differences)),
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        interpretation=interpret_exp001_interval(ci_lower, ci_upper),
        descriptive_diagnostics=diagnostics,
    )


def _paired_percentile_bootstrap(differences: np.ndarray) -> tuple[float, float]:
    if differences.shape != (len(CONFIRMATORY_SEEDS),):
        raise ValueError("paired bootstrap requires exactly 1000 differences")
    rng = np.random.Generator(np.random.PCG64(EXP001_BOOTSTRAP_RNG_SEED))
    bootstrap_means = np.empty(EXP001_BOOTSTRAP_RESAMPLES, dtype=np.float64)
    for replicate in range(EXP001_BOOTSTRAP_RESAMPLES):
        indices = rng.integers(0, len(CONFIRMATORY_SEEDS), size=len(CONFIRMATORY_SEEDS))
        bootstrap_means[replicate] = np.mean(differences[indices])
    quantiles = np.percentile(
        bootstrap_means,
        np.asarray((2.5, 97.5), dtype=np.float64),
        method=EXP001_BOOTSTRAP_QUANTILE_METHOD,
    )
    return float(quantiles[0]), float(quantiles[1])


def interpret_exp001_interval(ci_lower: float, ci_upper: float) -> str:
    """Apply the frozen three-way interval interpretation."""
    if not math.isfinite(ci_lower) or not math.isfinite(ci_upper):
        raise ValueError("confidence interval bounds must be finite")
    if ci_lower > 0.0:
        return INTERPRETATION_B_GREATER
    if ci_upper < 0.0:
        return INTERPRETATION_C_GREATER
    return INTERPRETATION_UNRESOLVED


def write_exp001_confirmatory_analysis_json(
    analysis: EXP001ConfirmatoryAnalysis,
    output_path: str | os.PathLike[str],
) -> Path:
    """Write an artifact-derived analysis JSON without overwriting."""
    path = Path(output_path)
    _write_text_no_overwrite(
        path, json.dumps(analysis.to_dict(), indent=2, sort_keys=True) + "\n"
    )
    return path


def write_exp001_confirmatory_analysis_markdown(
    analysis: EXP001ConfirmatoryAnalysis,
    output_path: str | os.PathLike[str],
) -> Path:
    """Write an artifact-derived analysis report without overwriting."""
    path = Path(output_path)
    _write_text_no_overwrite(path, analysis.to_markdown())
    return path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the gated EXP-001 confirmatory instrument."
    )
    parser.add_argument("--authorization", required=True)
    args = parser.parse_args(argv)
    try:
        receipt = execute_exp001_confirmatory(args.authorization)
    except (
        EXP001ConfirmatoryGitError,
        EXP001ConfirmatoryValidationError,
        FileExistsError,
        OSError,
        PermissionError,
        ValueError,
    ) as error:
        parser.exit(2, f"EXP-001 confirmatory execution error: {error}\n")
    print(f"artifact_path={receipt.artifact_path}")
    print(f"artifact_sha256={receipt.artifact_sha256}")
    print(f"git_commit_sha={receipt.git_commit_sha}")
    print(f"episode_count={receipt.episode_count}")
    return 0


def analysis_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Analyze an existing EXP-001 confirmatory artifact only."
    )
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args(argv)
    try:
        analysis = analyze_exp001_confirmatory_artifact(args.artifact)
        if args.output is None and args.markdown_output is None:
            sys.stdout.write(analysis.to_markdown())
        if args.output is not None:
            write_exp001_confirmatory_analysis_json(analysis, args.output)
        if args.markdown_output is not None:
            write_exp001_confirmatory_analysis_markdown(analysis, args.markdown_output)
    except (
        EXP001ConfirmatoryValidationError,
        FileExistsError,
        OSError,
        ValueError,
    ) as error:
        parser.exit(2, f"EXP-001 confirmatory analysis error: {error}\n")
    return 0


def _validate_manifest(value: Any, path: Path) -> Mapping[str, Any]:
    manifest = _mapping(value, f"{path}: manifest")
    required = {
        "schema_version",
        "experiment",
        "purpose",
        "protocol_revision",
        "execution_authorization",
        "git_commit_sha",
        "tracked_worktree_provenance",
        "python_version",
        "numpy_version",
        "environment_config",
        "shared_controller_config",
        "calibrated_c_name",
        "calibrated_c_explore_duration",
        "calibrated_c_charge_duration",
        "calibration_artifact_sha256",
        "confirmatory_seed_range",
        "conditions",
        "primary_estimand_identifier",
        "bootstrap_specification",
        "episode_count",
        "raw_trajectories_persisted",
        "run_started_at_utc",
    }
    if set(manifest) != required:
        raise EXP001ConfirmatoryValidationError(
            f"{path}: manifest fields do not match the frozen schema"
        )
    if manifest["schema_version"] != EXP001_CONFIRMATORY_MANIFEST_SCHEMA_VERSION:
        raise EXP001ConfirmatoryValidationError(f"{path}: incorrect manifest schema")
    if manifest["experiment"] != "EXP-001" or manifest["purpose"] != "confirmatory":
        raise EXP001ConfirmatoryValidationError(f"{path}: incorrect experiment purpose")
    if manifest["protocol_revision"] != EXP001_PROTOCOL_REVISION:
        raise EXP001ConfirmatoryValidationError(f"{path}: incorrect protocol revision")
    if (
        manifest["execution_authorization"]
        != EXP001_CONFIRMATORY_EXECUTION_AUTHORIZATION
    ):
        raise EXP001ConfirmatoryValidationError(f"{path}: incorrect execution gate")
    git_sha = manifest["git_commit_sha"]
    if not isinstance(git_sha, str) or not _GIT_SHA_PATTERN.fullmatch(git_sha):
        raise EXP001ConfirmatoryValidationError(f"{path}: invalid Git SHA")
    provenance = _mapping(manifest["tracked_worktree_provenance"], "tracked provenance")
    if provenance.get("tracked_worktree_clean") is not True:
        raise EXP001ConfirmatoryValidationError(
            f"{path}: tracked checkout was not clean"
        )
    if not isinstance(
        provenance.get("untracked_files_present"), bool
    ) or not isinstance(provenance.get("untracked_file_count"), int):
        raise EXP001ConfirmatoryValidationError(f"{path}: invalid tracked provenance")
    if provenance["untracked_file_count"] < 0:
        raise EXP001ConfirmatoryValidationError(f"{path}: invalid untracked file count")
    if manifest["environment_config"] != _json_value(
        asdict(FROZEN_EXP001_CALIBRATION_ENV_CONFIG)
    ):
        raise EXP001ConfirmatoryValidationError(f"{path}: frozen environment differs")
    if manifest["shared_controller_config"] != asdict(
        FROZEN_EXP001_SHARED_CONTROLLER_CONFIG
    ):
        raise EXP001ConfirmatoryValidationError(
            f"{path}: shared controller config differs"
        )
    if (
        manifest["calibrated_c_name"] != CALIBRATED_C_NAME
        or manifest["calibrated_c_explore_duration"] != CALIBRATED_C.explore_duration
        or manifest["calibrated_c_charge_duration"] != CALIBRATED_C.charge_duration
    ):
        raise EXP001ConfirmatoryValidationError(f"{path}: calibrated C differs")
    if manifest["calibration_artifact_sha256"] != EXP001_CALIBRATION_ARTIFACT_SHA256:
        raise EXP001ConfirmatoryValidationError(f"{path}: calibration hash differs")
    if manifest["confirmatory_seed_range"] != {
        "start": CONFIRMATORY_SEEDS[0],
        "end": CONFIRMATORY_SEEDS[-1],
        "count": len(CONFIRMATORY_SEEDS),
    }:
        raise EXP001ConfirmatoryValidationError(f"{path}: seed range differs")
    if manifest["conditions"] != [condition.value for condition in _FORMAL_CONDITIONS]:
        raise EXP001ConfirmatoryValidationError(f"{path}: condition identities differ")
    if manifest["primary_estimand_identifier"] != PRIMARY_ESTIMAND_IDENTIFIER:
        raise EXP001ConfirmatoryValidationError(f"{path}: primary estimand differs")
    expected_bootstrap = {
        "resampling_unit": "matched_seed_paired_difference",
        "replicates": EXP001_BOOTSTRAP_RESAMPLES,
        "rng": "numpy.random.Generator",
        "bit_generator": EXP001_BOOTSTRAP_BIT_GENERATOR,
        "seed": EXP001_BOOTSTRAP_RNG_SEED,
        "sample_size": len(CONFIRMATORY_SEEDS),
        "confidence_level": EXP001_BOOTSTRAP_CONFIDENCE_LEVEL,
        "quantile_method": EXP001_BOOTSTRAP_QUANTILE_METHOD,
    }
    if manifest["bootstrap_specification"] != expected_bootstrap:
        raise EXP001ConfirmatoryValidationError(f"{path}: bootstrap differs")
    if manifest["episode_count"] != EXP001_CONFIRMATORY_EPISODE_COUNT:
        raise EXP001ConfirmatoryValidationError(f"{path}: episode count differs")
    if manifest["raw_trajectories_persisted"] is not False:
        raise EXP001ConfirmatoryValidationError(
            f"{path}: raw trajectories are forbidden"
        )
    for field in ("python_version", "numpy_version", "run_started_at_utc"):
        if not isinstance(manifest[field], str) or not manifest[field]:
            raise EXP001ConfirmatoryValidationError(f"{path}: missing {field}")
    return manifest


def _validate_summary_rows(value: Any, path: Path) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, list) or len(value) != EXP001_CONFIRMATORY_EPISODE_COUNT:
        raise EXP001ConfirmatoryValidationError(
            f"{path}: exactly 3000 summaries required"
        )
    rows: list[Mapping[str, Any]] = []
    allowed_conditions = {condition.value for condition in _FORMAL_CONDITIONS}
    for index, item in enumerate(value):
        row = _mapping(item, f"summary[{index}]")
        if set(row) != set(_SUMMARY_FIELDS):
            raise EXP001ConfirmatoryValidationError(f"{path}: invalid summary fields")
        if row["condition"] not in allowed_conditions:
            raise EXP001ConfirmatoryValidationError(f"{path}: invalid condition")
        seed = row["environment_seed"]
        if (
            isinstance(seed, bool)
            or not isinstance(seed, int)
            or seed not in CONFIRMATORY_SEEDS
        ):
            raise EXP001ConfirmatoryValidationError(
                f"{path}: invalid confirmatory seed"
            )
        for field in _COUNT_SUMMARY_FIELDS:
            field_value = row[field]
            if (
                isinstance(field_value, bool)
                or not isinstance(field_value, int)
                or field_value < 0
            ):
                raise EXP001ConfirmatoryValidationError(
                    f"{path}: invalid count field {field}"
                )
        if row["capped_lifespan"] != row["completed_transitions"]:
            raise EXP001ConfirmatoryValidationError(
                f"{path}: lifespan/transitions mismatch"
            )
        if not 0 < row["capped_lifespan"] <= EXP001_CONFIRMATORY_HORIZON:
            raise EXP001ConfirmatoryValidationError(f"{path}: invalid capped lifespan")
        for field in _BOOLEAN_SUMMARY_FIELDS:
            if not isinstance(row[field], bool):
                raise EXP001ConfirmatoryValidationError(
                    f"{path}: invalid boolean field {field}"
                )
        if row["terminated_viability_failure"] == row["horizon_survival"]:
            raise EXP001ConfirmatoryValidationError(
                f"{path}: invalid termination flags"
            )
        if row["horizon_survival"] != (
            row["capped_lifespan"] == EXP001_CONFIRMATORY_HORIZON
        ):
            raise EXP001ConfirmatoryValidationError(
                f"{path}: invalid horizon semantics"
            )
        if (
            sum(
                row[field]
                for field in _COUNT_SUMMARY_FIELDS
                - {
                    "capped_lifespan",
                    "completed_transitions",
                    "complete_recharge_cycle_count",
                }
            )
            != row["capped_lifespan"]
        ):
            raise EXP001ConfirmatoryValidationError(
                f"{path}: mode counts do not sum to lifespan"
            )
        if row["complete_recharge_cycle_count"] > row["capped_lifespan"]:
            raise EXP001ConfirmatoryValidationError(f"{path}: invalid cycle count")
        for field in _ENERGY_SUMMARY_FIELDS:
            field_value = row[field]
            if (
                isinstance(field_value, bool)
                or not isinstance(field_value, (int, float))
                or not math.isfinite(float(field_value))
                or not 0.0 <= float(field_value) <= 1.0
            ):
                raise EXP001ConfirmatoryValidationError(
                    f"{path}: invalid energy field {field}"
                )
        for field in _NONNEGATIVE_FLOAT_FIELDS:
            field_value = row[field]
            if (
                isinstance(field_value, bool)
                or not isinstance(field_value, (int, float))
                or not math.isfinite(float(field_value))
                or float(field_value) < 0.0
            ):
                raise EXP001ConfirmatoryValidationError(
                    f"{path}: invalid metric field {field}"
                )
        rows.append(row)
    return tuple(rows)


def _summary_map(
    rows: Sequence[Mapping[str, Any]],
) -> dict[tuple[str, int], Mapping[str, Any]]:
    result: dict[tuple[str, int], Mapping[str, Any]] = {}
    for row in rows:
        key = (str(row["condition"]), int(row["environment_seed"]))
        if key in result:
            raise EXP001ConfirmatoryValidationError(f"duplicate summary row for {key}")
        result[key] = row
    return result


def _descriptive_diagnostics(
    by_condition: Mapping[str, Sequence[Mapping[str, Any]]],
    differences: np.ndarray,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "matched_seed_counts": {
            "B_greater_C": int(np.sum(differences > 0)),
            "B_equal_C": int(np.sum(differences == 0)),
            "B_less_C": int(np.sum(differences < 0)),
        },
        "conditions": {},
    }
    for condition in _FORMAL_CONDITIONS:
        rows = by_condition[condition.value]
        result["conditions"][condition.value] = {
            "status": "descriptive reference only"
            if condition is EXP001Condition.A
            else "descriptive only",
            "mean_capped_lifespan": statistics.fmean(
                row["capped_lifespan"] for row in rows
            ),
            "median_capped_lifespan": statistics.median(
                row["capped_lifespan"] for row in rows
            ),
            "horizon_survival_count": sum(
                bool(row["horizon_survival"]) for row in rows
            ),
            "horizon_survival_fraction": statistics.fmean(
                bool(row["horizon_survival"]) for row in rows
            ),
            "mean_final_normalized_energy": statistics.fmean(
                row["final_normalized_energy"] for row in rows
            ),
            "mean_minimum_normalized_energy": statistics.fmean(
                row["minimum_normalized_energy"] for row in rows
            ),
            "mean_total_harvested_energy": statistics.fmean(
                row["total_harvested_energy"] for row in rows
            ),
            "mean_total_basal_energy_cost": statistics.fmean(
                row["total_basal_energy_cost"] for row in rows
            ),
            "mean_total_action_energy_cost": statistics.fmean(
                row["total_action_energy_cost"] for row in rows
            ),
            "mean_total_distance_travelled": statistics.fmean(
                row["total_distance_travelled"] for row in rows
            ),
            "mean_explore_action_count": statistics.fmean(
                row["explore_action_count"] for row in rows
            ),
            "mean_seek_resource_action_count": statistics.fmean(
                row["seek_resource_action_count"] for row in rows
            ),
            "mean_charge_action_count": statistics.fmean(
                row["charge_action_count"] for row in rows
            ),
            "mean_complete_recharge_cycle_count": statistics.fmean(
                row["complete_recharge_cycle_count"] for row in rows
            ),
        }
    return result


def _diagnostic_markdown(diagnostics: Mapping[str, Any]) -> list[str]:
    counts = diagnostics["matched_seed_counts"]
    lines = [
        f"- Matched B>C / B=C / B<C counts: `{counts['B_greater_C']} / "
        f"{counts['B_equal_C']} / {counts['B_less_C']}`",
        "",
        "| Condition | Mean lifespan | Median lifespan | Horizon survivors | "
        "Mean final energy | Mean minimum energy | Mean harvested | Mean basal "
        "cost | Mean action cost | Mean distance | Mean EXPLORE | "
        "Mean SEEK_RESOURCE | Mean CHARGE | Mean complete cycles |",
        "| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | "
        "---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for condition in _FORMAL_CONDITIONS:
        row = diagnostics["conditions"][condition.value]
        lines.append(
            f"| {condition.value} | {row['mean_capped_lifespan']:.3f} | "
            f"{row['median_capped_lifespan']:.3f} | "
            f"{row['horizon_survival_count']} "
            f"({row['horizon_survival_fraction']:.3f}) | "
            f"{row['mean_final_normalized_energy']:.6f} | "
            f"{row['mean_minimum_normalized_energy']:.6f} | "
            f"{row['mean_total_harvested_energy']:.6f} | "
            f"{row['mean_total_basal_energy_cost']:.6f} | "
            f"{row['mean_total_action_energy_cost']:.6f} | "
            f"{row['mean_total_distance_travelled']:.6f} | "
            f"{row['mean_explore_action_count']:.3f} | "
            f"{row['mean_seek_resource_action_count']:.3f} | "
            f"{row['mean_charge_action_count']:.3f} | "
            f"{row['mean_complete_recharge_cycle_count']:.3f} |"
        )
    return lines


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise EXP001ConfirmatoryValidationError(f"{label} must be an object")
    return value


def _json_value(value: object) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    return value


def _git_stdout(arguments: Sequence[str], working_directory: Path) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=working_directory,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        detail = result.stderr.strip() or "git command failed"
        raise EXP001ConfirmatoryGitError(detail)
    return result.stdout.strip()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_text_no_overwrite(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "w", encoding="utf-8") as file:
        file.write(content)


if __name__ == "__main__":
    sys.exit(main())
