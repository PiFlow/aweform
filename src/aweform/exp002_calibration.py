"""Formal, one-shot B-only calibration for EXP-002.

This module is deliberately separate from the development runner.  The public
formal entry point has no seed, candidate, threshold, horizon, environment,
or output-path controls.  It can only execute the exact frozen calibration
workload after the procedural authorization and preflight gates pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import statistics
import subprocess
import tempfile
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

import numpy as np

from .exp001_calibration import FROZEN_EXP001_CALIBRATION_ENV_CONFIG
from .exp001_runner import EXP001Condition
from .exp002_protocol import (
    EXP002_B_CANDIDATES,
    EXP002_CALIBRATION_SEEDS,
    EXP002_CONFIRMATORY_SEEDS,
    EXP002_COVERAGE_GRID_HEIGHT,
    EXP002_COVERAGE_GRID_WIDTH,
    EXP002_HORIZON,
    EXP002_PROTOCOL_FILE_SHA256,
    EXP002_PROTOCOL_REVISION,
    EXP002_SELECTION_RULE,
    EXP002_SELECTION_RULE_IDENTIFIER,
    EXP002BCandidate,
)
from .exp002_runner import (
    EXP002EpisodeDiagnostics,
    _run_episode,
    summarize_exp002_episode,
)

FORMAL_EXECUTION_AUTHORIZATION: Final = "EXP-002-calibration-execution-001"
EXP002_CALIBRATION_ARTIFACT_SCHEMA_VERSION: Final = "exp-002-formal-calibration-v1"
EXP002_CALIBRATION_EPISODE_COUNT: Final = 4 * 200
EXP002_CALIBRATION_EPISODES_PER_CANDIDATE: Final = 200
EXP002_CALIBRATION_ARTIFACT_FILENAME: Final = (
    "EXP-002-formal-calibration-precalibration-001.json"
)
EXP002_CALIBRATION_RESERVATION_SUFFIX: Final = ".reservation"


def _repository_root() -> Path:
    module_path = Path(__file__).resolve()
    for parent in (module_path.parent, *module_path.parents):
        if (parent / "pyproject.toml").is_file() and (parent / ".git").exists():
            return parent
    raise RuntimeError("could not resolve the Aweform source checkout")


FORMAL_ARTIFACT_PATH: Final = (
    _repository_root() / "artifacts" / EXP002_CALIBRATION_ARTIFACT_FILENAME
)
FORMAL_RESERVATION_PATH: Final = Path(
    f"{FORMAL_ARTIFACT_PATH}{EXP002_CALIBRATION_RESERVATION_SUFFIX}"
)


@dataclass(frozen=True, slots=True)
class EXP002CandidateSummary:
    """Aggregate evaluator diagnostics retained for one B candidate."""

    candidate: str
    enter_seek: float
    n: int
    horizon_survival_count: int
    horizon_survival_fraction: float
    mean_visited_cell_count: float
    mean_coverage_fraction: float
    mean_capped_lifespan: float
    median_capped_lifespan: float
    min_capped_lifespan: int
    max_capped_lifespan: int
    mean_explore_action_count: float
    mean_distance_travelled_during_explore: float
    mean_explore_unique_cell_count: float
    mean_coverage_efficiency_per_100_explore_actions: float
    mean_complete_recharge_cycle_count: float
    total_seek_attempt_count: int
    seek_attempt_reached_charge_count: int
    seek_attempt_reached_charge_fraction: float | None
    mean_seek_onset_normalized_energy: float | None
    mean_nearest_source_distance_at_seek_onset: float | None
    mean_minimum_normalized_energy_during_seek_attempt: float | None


@dataclass(frozen=True, slots=True)
class EXP002Selection:
    """Machine-readable output of the frozen candidate-selection rule."""

    selected_candidate: str
    selected_enter_seek: float
    viability_eligible_candidates: tuple[str, ...]
    selection_path: str


@dataclass(frozen=True, slots=True)
class EXP002FormalCalibrationResult:
    """Aggregate-only formal result; no trajectories or per-step records."""

    git_commit_sha: str
    run_started_at_utc: str
    candidate_summaries: tuple[EXP002CandidateSummary, ...]
    selection: EXP002Selection

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": EXP002_CALIBRATION_ARTIFACT_SCHEMA_VERSION,
            "identity": {
                "experiment": "EXP-002",
                "purpose": "calibration",
                "protocol_revision": EXP002_PROTOCOL_REVISION,
                "protocol_file": "experiments/EXP-002-interoceptive-seek-threshold.md",
                "protocol_file_sha256": EXP002_PROTOCOL_FILE_SHA256,
                "formal_authorization": FORMAL_EXECUTION_AUTHORIZATION,
                "git_commit_sha": self.git_commit_sha,
                "python_version": platform.python_version(),
                "numpy_version": np.__version__,
                "run_started_at_utc": self.run_started_at_utc,
                "calibration_seed_range": {
                    "start": EXP002_CALIBRATION_SEEDS[0],
                    "end": EXP002_CALIBRATION_SEEDS[-1],
                    "count": len(EXP002_CALIBRATION_SEEDS),
                    "values": list(EXP002_CALIBRATION_SEEDS),
                },
                "episode_count": EXP002_CALIBRATION_EPISODE_COUNT,
                "candidates": [
                    {"candidate": candidate.value, "enter_seek": candidate.enter_seek}
                    for candidate in EXP002_B_CANDIDATES
                ],
                "environment_config": _json_value(
                    asdict(FROZEN_EXP001_CALIBRATION_ENV_CONFIG)
                ),
                "coverage_definition": {
                    "grid_width": EXP002_COVERAGE_GRID_WIDTH,
                    "grid_height": EXP002_COVERAGE_GRID_HEIGHT,
                    "cell_count": EXP002_COVERAGE_GRID_WIDTH
                    * EXP002_COVERAGE_GRID_HEIGHT,
                    "world_min": list(FROZEN_EXP001_CALIBRATION_ENV_CONFIG.world_min),
                    "world_max": list(FROZEN_EXP001_CALIBRATION_ENV_CONFIG.world_max),
                    "canonical_quantity": "visited_cell_count",
                },
                "raw_trajectories_persisted": False,
            },
            "candidate_summaries": [
                asdict(summary) for summary in self.candidate_summaries
            ],
            "selection": {
                "selected_candidate": self.selection.selected_candidate,
                "selected_enter_seek": self.selection.selected_enter_seek,
                "viability_eligible_candidates": list(
                    self.selection.viability_eligible_candidates
                ),
                "selection_path": self.selection.selection_path,
                "eligibility_rule": "horizon_survival_count >= 180",
                "selection_rule_identifier": EXP002_SELECTION_RULE_IDENTIFIER,
                "selection_rule": EXP002_SELECTION_RULE,
            },
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"


@dataclass(frozen=True, slots=True)
class EXP002FormalExecutionReceipt:
    artifact_path: Path
    artifact_sha256: str
    git_commit_sha: str
    episode_count: int


def validate_exp002_formal_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    """Accept only the exact ordered EXP-002 calibration tuple."""
    if isinstance(seeds, (str, bytes)):
        raise ValueError("formal seeds must be the exact ordered calibration tuple")
    try:
        supplied = tuple(seeds)
    except TypeError as error:
        raise ValueError(
            "formal seeds must be the exact ordered calibration tuple"
        ) from error
    if supplied != EXP002_CALIBRATION_SEEDS:
        raise ValueError(
            "formal EXP-002 calibration requires exactly tuple(range(40001, 40201))"
        )
    if set(supplied) & set(EXP002_CONFIRMATORY_SEEDS):
        raise ValueError("formal calibration cannot accept confirmatory seeds")
    return supplied


def select_exp002_candidate(
    summaries: Sequence[EXP002CandidateSummary],
) -> EXP002Selection:
    """Apply the frozen eligibility, coverage, survival, and tie-break rules."""
    candidates = tuple(summaries)
    _validate_summaries(candidates)
    eligible = tuple(
        summary
        for summary in candidates
        if summary.horizon_survival_count >= 180
    )
    if eligible:
        selected = max(
            eligible,
            key=lambda summary: (
                summary.mean_visited_cell_count,
                -summary.enter_seek,
            ),
        )
        path = "eligible_max_coverage"
    else:
        selected = max(
            candidates,
            key=lambda summary: (
                summary.horizon_survival_count,
                summary.mean_visited_cell_count,
                -summary.enter_seek,
            ),
        )
        path = "fallback_max_survival"
    return EXP002Selection(
        selected_candidate=selected.candidate,
        selected_enter_seek=selected.enter_seek,
        viability_eligible_candidates=tuple(summary.candidate for summary in eligible),
        selection_path=path,
    )


def run_exp002_formal_calibration(
    authorization: str,
) -> EXP002FormalExecutionReceipt:
    """Execute the one-shot formal B-only calibration after all preflight gates."""
    if authorization != FORMAL_EXECUTION_AUTHORIZATION:
        raise PermissionError(
            "formal EXP-002 calibration requires authorization "
            f"{FORMAL_EXECUTION_AUTHORIZATION!r}"
        )
    seeds = validate_exp002_formal_seeds(EXP002_CALIBRATION_SEEDS)
    started_at = datetime.now(timezone.utc).isoformat()
    git_commit_sha = _formal_preflight(started_at)
    artifact_path = FORMAL_ARTIFACT_PATH
    reservation_path = _acquire_reservation(
        artifact_path=artifact_path,
        git_commit_sha=git_commit_sha,
        started_at=started_at,
    )
    try:
        result = _run_formal_batches(
            seeds=seeds,
            git_commit_sha=git_commit_sha,
            started_at=started_at,
        )
        artifact_sha256 = write_exp002_calibration_json(result, artifact_path)
        _mark_reservation_completed(
            reservation_path,
            artifact_sha256,
            git_commit_sha=git_commit_sha,
            started_at=started_at,
        )
    except BaseException:
        # Retain the in-progress marker for independent review.  In particular,
        # do not delete it or retry after a failed formal execution.
        raise
    return EXP002FormalExecutionReceipt(
        artifact_path=artifact_path,
        artifact_sha256=artifact_sha256,
        git_commit_sha=git_commit_sha,
        episode_count=EXP002_CALIBRATION_EPISODE_COUNT,
    )


def write_exp002_calibration_json(
    result: EXP002FormalCalibrationResult,
    output_path: str | os.PathLike[str],
) -> str:
    """Write an aggregate artifact atomically and without overwriting."""
    if not isinstance(result, EXP002FormalCalibrationResult):
        raise ValueError("result must be an EXP002FormalCalibrationResult")
    path = Path(output_path)
    serialized = result.to_json().encode("utf-8")
    _write_non_overwriting_atomic(path, serialized)
    return hashlib.sha256(serialized).hexdigest()


def _formal_preflight(started_at: str) -> str:
    repository = _repository_root()
    git_commit_sha = _resolve_clean_git_sha(repository)
    protocol_path = (
        repository / "experiments" / "EXP-002-interoceptive-seek-threshold.md"
    )
    if EXP002_PROTOCOL_REVISION != "EXP-002-precalibration-001":
        raise RuntimeError("EXP-002 protocol revision is not the frozen revision")
    if _sha256_file(protocol_path) != EXP002_PROTOCOL_FILE_SHA256:
        raise RuntimeError("EXP-002 frozen protocol file identity does not match")
    if tuple(EXP002_B_CANDIDATES) != (
        EXP002BCandidate.B35,
        EXP002BCandidate.B40,
        EXP002BCandidate.B45,
        EXP002BCandidate.B50,
    ):
        raise RuntimeError("EXP-002 candidate registry is not the frozen registry")
    if FROZEN_EXP001_CALIBRATION_ENV_CONFIG.episode_horizon != EXP002_HORIZON:
        raise RuntimeError("EXP-002 frozen environment horizon does not match")
    if FORMAL_ARTIFACT_PATH.exists():
        raise FileExistsError(
            "refusing formal calibration: artifact already exists at "
            f"{FORMAL_ARTIFACT_PATH}"
        )
    FORMAL_ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not started_at:
        raise RuntimeError("formal calibration start timestamp is empty")
    return git_commit_sha


def _run_formal_batches(
    *,
    seeds: Sequence[int],
    git_commit_sha: str,
    started_at: str,
) -> EXP002FormalCalibrationResult:
    validated_seeds = validate_exp002_formal_seeds(seeds)
    summaries: list[EXP002CandidateSummary] = []
    for candidate in EXP002_B_CANDIDATES:
        diagnostics: list[EXP002EpisodeDiagnostics] = []
        for seed in validated_seeds:
            episode = _run_episode(
                condition=EXP001Condition.B,
                environment_seed=seed,
                env_config=FROZEN_EXP001_CALIBRATION_ENV_CONFIG,
                candidate=candidate,
            )
            if episode.condition is not EXP001Condition.B:
                raise RuntimeError(
                    "formal EXP-002 calibration executed a non-B episode"
                )
            if episode.candidate is not candidate:
                raise RuntimeError("formal EXP-002 episode candidate mismatch")
            diagnostics.append(summarize_exp002_episode(episode))
        summaries.append(_summarize_candidate(candidate, diagnostics))
    immutable_summaries = tuple(summaries)
    if (
        sum(summary.n for summary in immutable_summaries)
        != EXP002_CALIBRATION_EPISODE_COUNT
    ):
        raise RuntimeError(
            "formal EXP-002 calibration did not execute exactly 800 episodes"
        )
    return EXP002FormalCalibrationResult(
        git_commit_sha=git_commit_sha,
        run_started_at_utc=started_at,
        candidate_summaries=immutable_summaries,
        selection=select_exp002_candidate(immutable_summaries),
    )


def _summarize_candidate(
    candidate: EXP002BCandidate,
    diagnostics: Sequence[EXP002EpisodeDiagnostics],
) -> EXP002CandidateSummary:
    if len(diagnostics) != EXP002_CALIBRATION_EPISODES_PER_CANDIDATE:
        raise ValueError("formal candidate requires exactly 200 episode diagnostics")
    lifespans = tuple(diagnostic.capped_lifespan for diagnostic in diagnostics)
    seek_attempts = tuple(
        attempt
        for diagnostic in diagnostics
        for attempt in diagnostic.seek_attempts
    )
    reached_charge_count = sum(attempt.reached_charge for attempt in seek_attempts)
    return EXP002CandidateSummary(
        candidate=candidate.value,
        enter_seek=candidate.enter_seek,
        n=len(diagnostics),
        horizon_survival_count=sum(
            diagnostic.horizon_survivor for diagnostic in diagnostics
        ),
        horizon_survival_fraction=sum(
            diagnostic.horizon_survivor for diagnostic in diagnostics
        )
        / len(diagnostics),
        mean_visited_cell_count=_mean(
            diagnostic.visited_cell_count for diagnostic in diagnostics
        ),
        mean_coverage_fraction=_mean(
            diagnostic.coverage_fraction for diagnostic in diagnostics
        ),
        mean_capped_lifespan=_mean(lifespans),
        median_capped_lifespan=float(statistics.median(lifespans)),
        min_capped_lifespan=min(lifespans),
        max_capped_lifespan=max(lifespans),
        mean_explore_action_count=_mean(
            diagnostic.explore_action_count for diagnostic in diagnostics
        ),
        mean_distance_travelled_during_explore=_mean(
            diagnostic.distance_travelled_during_explore for diagnostic in diagnostics
        ),
        mean_explore_unique_cell_count=_mean(
            diagnostic.explore_unique_cell_count for diagnostic in diagnostics
        ),
        mean_coverage_efficiency_per_100_explore_actions=_mean(
            diagnostic.coverage_efficiency_per_100_explore_actions
            for diagnostic in diagnostics
        ),
        mean_complete_recharge_cycle_count=_mean(
            diagnostic.complete_recharge_cycle_count for diagnostic in diagnostics
        ),
        total_seek_attempt_count=len(seek_attempts),
        seek_attempt_reached_charge_count=reached_charge_count,
        seek_attempt_reached_charge_fraction=(
            reached_charge_count / len(seek_attempts) if seek_attempts else None
        ),
        mean_seek_onset_normalized_energy=_optional_mean(
            attempt.normalized_energy_at_onset for attempt in seek_attempts
        ),
        mean_nearest_source_distance_at_seek_onset=_optional_mean(
            attempt.nearest_source_distance_at_onset for attempt in seek_attempts
        ),
        mean_minimum_normalized_energy_during_seek_attempt=_optional_mean(
            attempt.minimum_normalized_energy for attempt in seek_attempts
        ),
    )


def _validate_summaries(summaries: Sequence[EXP002CandidateSummary]) -> None:
    if tuple(summary.candidate for summary in summaries) != tuple(
        candidate.value for candidate in EXP002_B_CANDIDATES
    ):
        raise ValueError("summaries must be in the exact frozen candidate order")
    for summary, candidate in zip(summaries, EXP002_B_CANDIDATES, strict=True):
        if summary.enter_seek != candidate.enter_seek:
            raise ValueError("candidate threshold does not match frozen registry")
        if summary.n != EXP002_CALIBRATION_EPISODES_PER_CANDIDATE:
            raise ValueError("formal candidate summaries must have n=200")
        for value in (
            summary.horizon_survival_fraction,
            summary.mean_visited_cell_count,
            summary.mean_coverage_fraction,
            summary.mean_capped_lifespan,
            summary.median_capped_lifespan,
            summary.mean_explore_action_count,
            summary.mean_distance_travelled_during_explore,
            summary.mean_explore_unique_cell_count,
            summary.mean_coverage_efficiency_per_100_explore_actions,
            summary.mean_complete_recharge_cycle_count,
        ):
            if not math.isfinite(value):
                raise ValueError("candidate summary values must be finite")


def _resolve_clean_git_sha(repository: Path) -> str:
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        )
        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise RuntimeError("could not establish formal Git provenance") from error
    if status.stdout.strip():
        raise RuntimeError("refusing formal calibration: tracked worktree is dirty")
    sha = head.stdout.strip()
    if len(sha) != 40 or any(char not in "0123456789abcdef" for char in sha):
        raise RuntimeError("Git HEAD is not an exact commit SHA")
    return sha


def _acquire_reservation(
    *,
    artifact_path: Path,
    git_commit_sha: str,
    started_at: str,
) -> Path:
    reservation_path = Path(f"{artifact_path}{EXP002_CALIBRATION_RESERVATION_SUFFIX}")
    payload = (
        "status=in_progress\n"
        f"artifact_path={artifact_path}\n"
        f"git_commit_sha={git_commit_sha}\n"
        "git_status=tracked_clean\n"
        f"pid={os.getpid()}\n"
        f"started_at_utc={started_at}\n"
    ).encode("utf-8")
    try:
        descriptor = os.open(
            reservation_path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o644,
        )
    except FileExistsError as error:
        raise FileExistsError(
            f"refusing formal calibration: reservation exists at {reservation_path}"
        ) from error
    try:
        with os.fdopen(descriptor, "wb") as file:
            file.write(payload)
            file.flush()
            os.fsync(file.fileno())
    except BaseException:
        # The marker is evidence that the formal attempt reached reservation;
        # retain it even if writing its initial contents failed.
        raise
    return reservation_path


def _mark_reservation_completed(
    reservation_path: Path,
    artifact_sha256: str,
    *,
    git_commit_sha: str,
    started_at: str,
) -> None:
    artifact_path = str(reservation_path).removesuffix(
        EXP002_CALIBRATION_RESERVATION_SUFFIX
    )
    content = (
        "status=completed\n"
        f"artifact_path={artifact_path}\n"
        f"git_commit_sha={git_commit_sha}\n"
        "git_status=tracked_clean\n"
        f"pid={os.getpid()}\n"
        f"started_at_utc={started_at}\n"
        f"artifact_sha256={artifact_sha256}\n"
        f"completed_at_utc={datetime.now(timezone.utc).isoformat()}\n"
    ).encode("utf-8")
    _write_text_atomically(reservation_path, content, replace=True)


def _write_non_overwriting_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        os.link(temporary_path, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except FileExistsError as error:
        raise FileExistsError(
            f"refusing to overwrite existing artifact: {path}"
        ) from error
    finally:
        temporary_path.unlink(missing_ok=True)


def _write_text_atomically(path: Path, content: bytes, *, replace: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        if replace:
            os.replace(temporary_path, path)
        else:
            os.link(temporary_path, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temporary_path.unlink(missing_ok=True)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise RuntimeError(f"could not read frozen protocol file: {path}") from error
    return digest.hexdigest()


def _mean(values: Iterable[float]) -> float:
    collected = tuple(values)
    if not collected:
        raise ValueError("cannot calculate a mean of no values")
    return math.fsum(collected) / len(collected)


def _optional_mean(values: Iterable[float]) -> float | None:
    collected = tuple(values)
    return math.fsum(collected) / len(collected) if collected else None


def _json_value(value: object) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Execute the one-shot formal EXP-002 B-threshold calibration."
    )
    parser.add_argument("--authorization", required=True)
    args = parser.parse_args(argv)
    receipt = run_exp002_formal_calibration(args.authorization)
    print(f"artifact_path={receipt.artifact_path}")
    print(f"artifact_sha256={receipt.artifact_sha256}")
    print(f"git_commit_sha={receipt.git_commit_sha}")
    print(f"episode_count={receipt.episode_count}")
    return 0
