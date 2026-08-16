"""Dedicated, frozen execution and artifact-only analysis for EXP-000."""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import re
import statistics
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Final, Literal, Mapping, Sequence

import gymnasium
import numpy as np

from .controllers import HomeostaticConfig
from .energy import EnergyConfig
from .env import AweformEnvConfig
from .runner import (
    Condition,
    EpisodeRecord,
    _run_episode,
    _to_json_value,
)

CONFIRMATORY_ARTIFACT_SCHEMA_VERSION = "exp-000-confirmatory-v1"
CONFIRMATORY_MANIFEST_SCHEMA_VERSION = "exp-000-confirmatory-manifest-v1"
ACCEPTANCE_SEEDS = tuple(range(10001, 10101))
CONFIRMATORY_CONDITIONS = (
    Condition.B_HOMEOSTATIC,
    Condition.C_ENERGY_BLIND,
)
CONFIRMATORY_RESOURCE_LENGTH_SCALE = 0.40
CONFIRMATORY_RESOURCE_COUNT = 1
CONFIRMATORY_EPISODE_HORIZON = 500
CONFIRMATORY_MASKED_ENERGY = 0.5
BOOTSTRAP_RESAMPLES = 100_000
BOOTSTRAP_RNG_SEED = 0
BOOTSTRAP_QUANTILE_METHOD: Final[Literal["linear"]] = "linear"
CONFIRMATORY_ENV_CONFIG = AweformEnvConfig(
    world_min=(0.0, 0.0),
    world_max=(1.0, 1.0),
    energy=EnergyConfig(maximum_energy=10.0, basal_cost=0.1, failure_boundary=0.0),
    initial_energy=5.0,
    movement_distance=0.05,
    turn_angle=math.pi / 4.0,
    wait_cost=0.0,
    turn_cost=0.02,
    movement_cost=0.1,
    probe_distance=0.1,
    sensor_angle=math.pi / 4.0,
    harvest_rate=0.5,
    episode_horizon=CONFIRMATORY_EPISODE_HORIZON,
    resource_peak_intensity=1.0,
    resource_length_scale=CONFIRMATORY_RESOURCE_LENGTH_SCALE,
    resource_count=CONFIRMATORY_RESOURCE_COUNT,
)
CONFIRMATORY_HOMEOSTATIC_CONFIG = HomeostaticConfig(
    enter_seek=0.35,
    recover=0.85,
    exploration_steps=8,
)
CONFIRMATORY_ANALYSIS_CONFIG = {
    "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
    "bootstrap_rng": "numpy.default_rng",
    "bootstrap_rng_seed": BOOTSTRAP_RNG_SEED,
    "confidence_level": 0.95,
    "quantile_method": BOOTSTRAP_QUANTILE_METHOD,
    "primary_difference": "capped_lifespan_B_minus_capped_lifespan_C",
}
_GIT_SHA_PATTERN = re.compile(r"^[0-9a-fA-F]{40}$")
_SUMMARY_FIELDS = (
    "condition",
    "environment_seed",
    "steps_executed",
    "terminated_viability_failure",
    "truncated_at_horizon",
    "horizon_survival",
    "initial_normalized_energy",
    "final_normalized_energy",
    "minimum_normalized_energy",
    "total_harvested_energy",
    "total_basal_energy_cost",
    "total_action_energy_cost",
    "total_distance_travelled",
    "explore_steps",
    "seek_resource_steps",
    "mode_transitions",
)
_SUMMARY_BOOLEAN_FIELDS = {
    "terminated_viability_failure",
    "truncated_at_horizon",
    "horizon_survival",
}
_SUMMARY_MODE_COUNT_FIELDS = {
    "explore_steps",
    "seek_resource_steps",
    "mode_transitions",
}
_INITIAL_STATE_FIELDS = {"x", "y", "heading", "energy", "source_positions"}


class ConfirmatoryValidationError(ValueError):
    """Raised when a confirmatory artifact violates the frozen contract."""


class GitProvenanceError(ValueError):
    """Raised when the confirmatory CLI cannot establish clean Git provenance."""


@dataclass(frozen=True, slots=True)
class ConfirmatoryExecutionReservation:
    """Exclusive marker preventing an automatic confirmatory rerun."""

    output_path: Path
    reservation_path: Path

    def release(self) -> None:
        """Remove the reservation only after the final artifact is complete."""
        self.reservation_path.unlink()


@dataclass(frozen=True, slots=True)
class ConfirmatoryManifest:
    """Complete execution provenance for a confirmatory batch."""

    schema_version: str
    experiment: str
    purpose: str
    protocol_revision: str
    git_commit_sha: str
    environment_config: Mapping[str, Any]
    homeostatic_config: Mapping[str, Any]
    energy_blind_masked_energy: float
    environment_seeds: tuple[int, ...]
    conditions: tuple[str, ...]
    analysis_config: Mapping[str, Any]
    python_version: str
    numpy_version: str
    gymnasium_version: str
    aweform_package_version: str | None
    platform: Mapping[str, str]
    run_started_at_utc: str


@dataclass(frozen=True, slots=True)
class ConfirmatoryBatchResult:
    """Complete confirmatory output before optional non-overwriting write."""

    manifest: ConfirmatoryManifest
    episodes: tuple[EpisodeRecord, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": CONFIRMATORY_ARTIFACT_SCHEMA_VERSION,
            "manifest": _to_json_value(self.manifest),
            "episode_summaries": [
                _to_json_value(record.summary) for record in self.episodes
            ],
            "raw_trajectories": [
                _to_json_value(record.trajectory) for record in self.episodes
            ],
        }


@dataclass(frozen=True, slots=True)
class ConfirmatoryAnalysis:
    """Frozen primary analysis and descriptive diagnostics."""

    git_commit_sha: str
    seeds: tuple[int, ...]
    differences: tuple[float, ...]
    mean_difference: float
    median_difference: float
    ci_lower: float
    ci_upper: float
    support: bool
    by_condition: Mapping[str, tuple[Mapping[str, Any], ...]]

    def to_markdown(self) -> str:
        b = self.by_condition[Condition.B_HOMEOSTATIC.value]
        c = self.by_condition[Condition.C_ENERGY_BLIND.value]
        b_lifespans = tuple(int(summary["steps_executed"]) for summary in b)
        c_lifespans = tuple(int(summary["steps_executed"]) for summary in c)
        b_survival = sum(bool(summary["horizon_survival"]) for summary in b)
        c_survival = sum(bool(summary["horizon_survival"]) for summary in c)
        b_gt_c = sum(difference > 0 for difference in self.differences)
        b_eq_c = sum(difference == 0 for difference in self.differences)
        b_lt_c = sum(difference < 0 for difference in self.differences)

        lines = [
            "# EXP-000 Confirmatory Analysis",
            "",
            "This report is generated only from an already-written confirmatory "
            "artifact. It does not execute the simulator.",
            "",
            f"- Git SHA: `{self.git_commit_sha}`",
            f"- Acceptance seeds: `{self.seeds[0]}–{self.seeds[-1]}` "
            f"({len(self.seeds)} matched B/C pairs)",
            "",
            "## Primary result",
            "",
            "The primary endpoint is the mean of paired "
            "`capped_lifespan_B - capped_lifespan_C` differences.",
            "",
            f"- Mean paired difference: `{self.mean_difference:.6f}` steps",
            f"- Frozen two-sided 95% bootstrap CI: "
            f"`[{self.ci_lower:.6f}, {self.ci_upper:.6f}]` steps",
            "- Bootstrap: 100,000 paired resamples; "
            "NumPy `default_rng(0)`; quantile method `linear`",
            f"- Confirmatory support: `{'YES' if self.support else 'NO'}`",
            "",
            "Support is obtained if and only if the observed mean is strictly "
            "positive and the lower bound of the frozen CI is strictly greater "
            "than zero. No secondary metric can rescue the primary endpoint.",
            "",
            "## Descriptive diagnostics",
            "",
            "| Diagnostic | B | C |",
            "| :--- | ---: | ---: |",
            f"| Mean capped lifespan | {statistics.fmean(b_lifespans):.6f} | "
            f"{statistics.fmean(c_lifespans):.6f} |",
            f"| Median capped lifespan | {statistics.median(b_lifespans):.6f} | "
            f"{statistics.median(c_lifespans):.6f} |",
            f"| Horizon survival | {b_survival}/{len(b)} "
            f"({b_survival / len(b):.3f}) | {c_survival}/{len(c)} "
            f"({c_survival / len(c):.3f}) |",
            f"| Mean harvested energy | "
            f"{_mean_optional(b, 'total_harvested_energy')} | "
            f"{_mean_optional(c, 'total_harvested_energy')} |",
            f"| Mean basal energy cost | "
            f"{_mean_optional(b, 'total_basal_energy_cost')} | "
            f"{_mean_optional(c, 'total_basal_energy_cost')} |",
            f"| Mean action energy cost | "
            f"{_mean_optional(b, 'total_action_energy_cost')} | "
            f"{_mean_optional(c, 'total_action_energy_cost')} |",
            f"| Mean distance travelled | "
            f"{_mean_optional(b, 'total_distance_travelled')} | "
            f"{_mean_optional(c, 'total_distance_travelled')} |",
            "",
            f"- Paired B>C / B=C / B<C counts: `{b_gt_c} / {b_eq_c} / {b_lt_c}`",
            f"- Median paired lifespan difference: "
            f"`{self.median_difference:.6f}` steps",
            "",
            "The 500-step ceiling means this analysis concerns capped 500-step "
            "viability. It does not establish uncensored survival duration beyond "
            "the episode horizon.",
            "",
        ]
        return "\n".join(lines)


def run_confirmatory_batch(git_sha: str) -> ConfirmatoryBatchResult:
    """Run the deliberate frozen B/C path on the hardcoded acceptance seeds."""
    _validate_git_sha(git_sha)
    started_at = datetime.now(timezone.utc).isoformat()
    episodes: list[EpisodeRecord] = []
    for seed in ACCEPTANCE_SEEDS:
        for condition in CONFIRMATORY_CONDITIONS:
            episodes.append(
                _run_episode(
                    condition=condition,
                    environment_seed=seed,
                    env_config=CONFIRMATORY_ENV_CONFIG,
                    homeostatic_config=CONFIRMATORY_HOMEOSTATIC_CONFIG,
                    masked_energy=CONFIRMATORY_MASKED_ENERGY,
                )
            )
    manifest = ConfirmatoryManifest(
        schema_version=CONFIRMATORY_MANIFEST_SCHEMA_VERSION,
        experiment="EXP-000",
        purpose="confirmatory",
        protocol_revision="EXP-000-confirmatory-v1",
        git_commit_sha=git_sha,
        environment_config=_to_json_value(CONFIRMATORY_ENV_CONFIG),
        homeostatic_config=_to_json_value(CONFIRMATORY_HOMEOSTATIC_CONFIG),
        energy_blind_masked_energy=CONFIRMATORY_MASKED_ENERGY,
        environment_seeds=ACCEPTANCE_SEEDS,
        conditions=tuple(condition.value for condition in CONFIRMATORY_CONDITIONS),
        analysis_config=CONFIRMATORY_ANALYSIS_CONFIG,
        python_version=platform.python_version(),
        numpy_version=np.__version__,
        gymnasium_version=gymnasium.__version__,
        aweform_package_version=_package_version(),
        platform={
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python_implementation": platform.python_implementation(),
        },
        run_started_at_utc=started_at,
    )
    return ConfirmatoryBatchResult(manifest=manifest, episodes=tuple(episodes))


def run_confirmatory_batch_from_git() -> ConfirmatoryBatchResult:
    """Run the frozen batch using the clean checkout's actual HEAD SHA."""
    return run_confirmatory_batch(resolve_git_provenance())


def execute_confirmatory_to_path(output_path: str | os.PathLike[str]) -> Path:
    """Reserve an output, execute once, and publish without overwriting.

    The reservation intentionally remains when execution or final writing
    fails. If confirmatory execution is interrupted after acceptance begins,
    do not rerun automatically; preserve the marker and stop for protocol
    review before deciding any recovery action.
    """
    path = Path(output_path)
    git_sha = resolve_git_provenance()
    reservation = acquire_confirmatory_reservation(path)
    result = run_confirmatory_batch(git_sha)
    write_confirmatory_json(result, path)
    reservation.release()
    return path


def acquire_confirmatory_reservation(
    output_path: str | os.PathLike[str],
) -> ConfirmatoryExecutionReservation:
    """Acquire an exclusive in-progress marker before any episode starts."""
    path = Path(output_path)
    reservation_path = Path(f"{path}.in-progress")
    try:
        descriptor = os.open(
            reservation_path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o644,
        )
    except FileExistsError as error:
        raise FileExistsError(
            f"refusing to run: confirmatory reservation exists at "
            f"{reservation_path}"
        ) from error

    try:
        if path.exists():
            raise FileExistsError(
                f"refusing to run: confirmatory artifact already exists at {path}"
            )
        file = os.fdopen(descriptor, "w", encoding="utf-8")
        descriptor = -1
        with file:
            file.write(
                "EXP-000 CONFIRMATORY EXECUTION IN PROGRESS\n"
                f"output={path}\n"
                f"pid={os.getpid()}\n"
                f"started_at_utc={datetime.now(timezone.utc).isoformat()}\n"
            )
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        reservation_path.unlink(missing_ok=True)
        raise
    return ConfirmatoryExecutionReservation(path, reservation_path)


def write_confirmatory_json(
    result: ConfirmatoryBatchResult,
    output_path: str | os.PathLike[str],
) -> Path:
    """Write a confirmatory artifact without ever overwriting an existing file."""
    path = Path(output_path)
    serialized = (
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    )
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError as error:
        raise FileExistsError(
            f"refusing to overwrite existing confirmatory artifact: {path}"
        ) from error
    with os.fdopen(descriptor, "w", encoding="utf-8") as file:
        file.write(serialized)
    return path


def analyze_confirmatory_artifact(
    artifact_path: str | os.PathLike[str],
) -> ConfirmatoryAnalysis:
    """Validate and analyze an existing artifact without executing the simulator."""
    path = Path(artifact_path)
    try:
        with path.open(encoding="utf-8") as file:
            payload = json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        raise ConfirmatoryValidationError(
            f"could not read valid confirmatory JSON artifact {path}: {error}"
        ) from error
    root = _mapping(payload, "artifact root")
    manifest = _validate_manifest(root, path)
    summaries = _validate_records(root.get("episode_summaries"), "episode summaries")
    trajectories = _validate_records(root.get("raw_trajectories"), "raw trajectories")
    summary_map = _record_map(summaries, "summary")
    trajectory_map = _record_map(trajectories, "trajectory")
    expected_keys = {
        (condition.value, seed)
        for seed in ACCEPTANCE_SEEDS
        for condition in CONFIRMATORY_CONDITIONS
    }
    if set(summary_map) != expected_keys:
        raise ConfirmatoryValidationError(
            "episode summaries must contain exactly one B and one C record for "
            "each acceptance seed"
        )
    if set(trajectory_map) != expected_keys:
        raise ConfirmatoryValidationError(
            "raw trajectories must contain exactly one B and one C record for "
            "each acceptance seed"
        )
    for key in expected_keys:
        summary = summary_map[key]
        trajectory = trajectory_map[key]
        steps = summary["steps_executed"]
        transitions = trajectory.get("transitions")
        if not isinstance(transitions, list) or len(transitions) != steps:
            raise ConfirmatoryValidationError(
                f"trajectory length does not match summary lifespan for {key}"
            )
        if (
            trajectory.get("condition") != summary["condition"]
            or trajectory.get("environment_seed") != summary["environment_seed"]
        ):
            raise ConfirmatoryValidationError(f"summary/trajectory mismatch for {key}")
    for seed in ACCEPTANCE_SEEDS:
        b_initial = trajectory_map[(Condition.B_HOMEOSTATIC.value, seed)][
            "initial_state"
        ]
        c_initial = trajectory_map[(Condition.C_ENERGY_BLIND.value, seed)][
            "initial_state"
        ]
        for field in _INITIAL_STATE_FIELDS:
            if b_initial[field] != c_initial[field]:
                raise ConfirmatoryValidationError(
                    f"matched B/C initial state diverges for seed {seed}: {field}"
                )

    by_condition = {
        condition.value: tuple(
            summary_map[(condition.value, seed)] for seed in ACCEPTANCE_SEEDS
        )
        for condition in CONFIRMATORY_CONDITIONS
    }
    b_lifespans = np.asarray(
        [
            summary["steps_executed"]
            for summary in by_condition[Condition.B_HOMEOSTATIC.value]
        ],
        dtype=np.float64,
    )
    c_lifespans = np.asarray(
        [
            summary["steps_executed"]
            for summary in by_condition[Condition.C_ENERGY_BLIND.value]
        ],
        dtype=np.float64,
    )
    differences = b_lifespans - c_lifespans
    bootstrap_rng = np.random.default_rng(BOOTSTRAP_RNG_SEED)
    indices = bootstrap_rng.integers(
        0, len(differences), size=(BOOTSTRAP_RESAMPLES, len(differences))
    )
    bootstrap_means = differences[indices].mean(axis=1)
    quantiles = np.quantile(
        bootstrap_means,
        np.asarray((0.025, 0.975), dtype=np.float64),
        method=BOOTSTRAP_QUANTILE_METHOD,
    )
    ci_lower = float(quantiles[0])
    ci_upper = float(quantiles[1])
    mean_difference = float(differences.mean())
    return ConfirmatoryAnalysis(
        git_commit_sha=str(manifest["git_commit_sha"]),
        seeds=ACCEPTANCE_SEEDS,
        differences=tuple(float(value) for value in differences),
        mean_difference=mean_difference,
        median_difference=float(np.median(differences)),
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        support=mean_difference > 0.0 and ci_lower > 0.0,
        by_condition=by_condition,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the frozen confirmatory simulation path."""
    parser = argparse.ArgumentParser(description="Run frozen EXP-000 confirmation.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        execute_confirmatory_to_path(args.output)
    except (FileExistsError, GitProvenanceError, OSError) as error:
        parser.exit(2, f"confirmatory execution error: {error}\n")
    return 0


def resolve_git_provenance(repository_path: Path | None = None) -> str:
    """Resolve a full HEAD SHA and require a clean tracked checkout."""
    working_directory = repository_path or Path.cwd()
    repository_root = Path(
        _git_stdout(["rev-parse", "--show-toplevel"], working_directory)
    )
    git_sha = _git_stdout(["rev-parse", "HEAD"], repository_root)
    _validate_git_sha(git_sha)
    for diff_args in (
        ["diff", "--quiet", "--no-ext-diff"],
        ["diff", "--cached", "--quiet"],
    ):
        result = subprocess.run(
            ["git", *diff_args],
            cwd=repository_root,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise GitProvenanceError(
                "tracked working tree is not clean; confirmatory execution aborted"
            )
    return git_sha


def _git_stdout(arguments: Sequence[str], working_directory: Path) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=working_directory,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or "git command failed"
        raise GitProvenanceError(detail)
    output = result.stdout.strip()
    if not output:
        raise GitProvenanceError("git command returned no output")
    return output


def analysis_main(argv: Sequence[str] | None = None) -> int:
    """Analyze one existing confirmatory artifact."""
    parser = argparse.ArgumentParser(
        description="Analyze an existing EXP-000 confirmatory artifact."
    )
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        report = analyze_confirmatory_artifact(args.artifact).to_markdown()
        if args.output is None:
            sys.stdout.write(report)
        else:
            _write_without_overwrite(args.output, report)
    except (ConfirmatoryValidationError, OSError) as error:
        parser.exit(2, f"confirmatory validation error: {error}\n")
    return 0


def _validate_manifest(root: Mapping[str, Any], path: Path) -> Mapping[str, Any]:
    if root.get("schema_version") != CONFIRMATORY_ARTIFACT_SCHEMA_VERSION:
        raise ConfirmatoryValidationError(
            f"{path}: unsupported artifact schema version"
        )
    manifest = _mapping(root.get("manifest"), f"{path}: manifest")
    if manifest.get("schema_version") != CONFIRMATORY_MANIFEST_SCHEMA_VERSION:
        raise ConfirmatoryValidationError(
            f"{path}: unsupported manifest schema version"
        )
    if (
        manifest.get("experiment") != "EXP-000"
        or manifest.get("purpose") != "confirmatory"
    ):
        raise ConfirmatoryValidationError(
            f"{path}: manifest must identify EXP-000 confirmatory purpose"
        )
    git_sha = manifest.get("git_commit_sha")
    if not isinstance(git_sha, str) or not _GIT_SHA_PATTERN.fullmatch(git_sha):
        raise ConfirmatoryValidationError(
            f"{path}: git_commit_sha must be a full 40-hex Git SHA"
        )
    if manifest.get("protocol_revision") != "EXP-000-confirmatory-v1":
        raise ConfirmatoryValidationError(f"{path}: incorrect protocol revision")
    if manifest.get("environment_config") != _to_json_value(CONFIRMATORY_ENV_CONFIG):
        raise ConfirmatoryValidationError(f"{path}: environment configuration differs")
    if manifest.get("homeostatic_config") != _to_json_value(
        CONFIRMATORY_HOMEOSTATIC_CONFIG
    ):
        raise ConfirmatoryValidationError(f"{path}: controller configuration differs")
    if manifest.get("energy_blind_masked_energy") != CONFIRMATORY_MASKED_ENERGY:
        raise ConfirmatoryValidationError(f"{path}: masked energy differs")
    if manifest.get("environment_seeds") != list(ACCEPTANCE_SEEDS):
        raise ConfirmatoryValidationError(f"{path}: exact acceptance seed set required")
    if manifest.get("conditions") != [
        condition.value for condition in CONFIRMATORY_CONDITIONS
    ]:
        raise ConfirmatoryValidationError(f"{path}: exact B/C condition set required")
    if manifest.get("analysis_config") != CONFIRMATORY_ANALYSIS_CONFIG:
        raise ConfirmatoryValidationError(
            f"{path}: frozen analysis configuration differs"
        )
    for field in (
        "python_version",
        "numpy_version",
        "gymnasium_version",
        "run_started_at_utc",
    ):
        if not isinstance(manifest.get(field), str) or not manifest[field]:
            raise ConfirmatoryValidationError(
                f"{path}: missing runtime provenance {field}"
            )
    return manifest


def _validate_records(value: Any, label: str) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, list) or len(value) != len(ACCEPTANCE_SEEDS) * 2:
        raise ConfirmatoryValidationError(f"{label} must contain exactly 200 records")
    records: list[Mapping[str, Any]] = []
    for index, item in enumerate(value):
        record = _mapping(item, f"{label}[{index}]")
        if label == "episode summaries":
            for field in _SUMMARY_FIELDS:
                if field not in record:
                    raise ConfirmatoryValidationError(
                        f"{label}[{index}] missing field {field}"
                    )
            condition = record["condition"]
            seed = record["environment_seed"]
            steps = record["steps_executed"]
            if condition not in {item.value for item in CONFIRMATORY_CONDITIONS}:
                raise ConfirmatoryValidationError(
                    f"{label}[{index}] has invalid condition"
                )
            if (
                not isinstance(seed, int)
                or isinstance(seed, bool)
                or seed not in ACCEPTANCE_SEEDS
            ):
                raise ConfirmatoryValidationError(f"{label}[{index}] has invalid seed")
            if (
                not isinstance(steps, int)
                or isinstance(steps, bool)
                or not 0 < steps <= CONFIRMATORY_EPISODE_HORIZON
            ):
                raise ConfirmatoryValidationError(
                    f"{label}[{index}] has invalid capped lifespan"
                )
            for field in _SUMMARY_BOOLEAN_FIELDS:
                if not isinstance(record[field], bool):
                    raise ConfirmatoryValidationError(
                        f"{label}[{index}] {field} must be boolean"
                    )
            terminated = record["terminated_viability_failure"]
            truncated = record["truncated_at_horizon"]
            horizon_survival = record["horizon_survival"]
            if terminated and truncated:
                raise ConfirmatoryValidationError(
                    f"{label}[{index}] cannot be both terminated and truncated"
                )
            if horizon_survival != (truncated and not terminated and steps == 500):
                raise ConfirmatoryValidationError(
                    f"{label}[{index}] has inconsistent horizon-survival flags"
                )
            for field in _SUMMARY_MODE_COUNT_FIELDS:
                value = record[field]
                if (
                    not isinstance(value, int)
                    or isinstance(value, bool)
                    or value < 0
                ):
                    raise ConfirmatoryValidationError(
                        f"{label}[{index}] {field} must be a non-negative integer"
                    )
            for field in _SUMMARY_FIELDS[3:]:
                if field in _SUMMARY_BOOLEAN_FIELDS or (
                    field in _SUMMARY_MODE_COUNT_FIELDS
                ):
                    continue
                if not isinstance(record[field], (int, float)) or not math.isfinite(
                    float(record[field])
                ):
                    raise ConfirmatoryValidationError(
                        f"{label}[{index}] has invalid numeric field {field}"
                    )
        else:
            condition = record.get("condition")
            seed = record.get("environment_seed")
            if condition not in {item.value for item in CONFIRMATORY_CONDITIONS}:
                raise ConfirmatoryValidationError(
                    f"{label}[{index}] has invalid condition"
                )
            if (
                not isinstance(seed, int)
                or isinstance(seed, bool)
                or seed not in ACCEPTANCE_SEEDS
            ):
                raise ConfirmatoryValidationError(f"{label}[{index}] has invalid seed")
            if not isinstance(record.get("transitions"), list):
                raise ConfirmatoryValidationError(
                    f"{label}[{index}] transitions must be a list"
                )
            _validate_initial_state(record, label, index)
        records.append(record)
    return tuple(records)


def _validate_initial_state(
    record: Mapping[str, Any], label: str, index: int
) -> None:
    initial_state = _mapping(
        record.get("initial_state"), f"{label}[{index}].initial_state"
    )
    if set(initial_state) != _INITIAL_STATE_FIELDS:
        raise ConfirmatoryValidationError(
            f"{label}[{index}] initial_state has an invalid structure"
        )
    for field in ("x", "y", "heading", "energy"):
        value = initial_state[field]
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ConfirmatoryValidationError(
                f"{label}[{index}] initial_state {field} must be numeric"
            )
        if not math.isfinite(float(value)):
            raise ConfirmatoryValidationError(
                f"{label}[{index}] initial_state {field} must be finite"
            )
    source_positions = initial_state["source_positions"]
    if (
        not isinstance(source_positions, list)
        or len(source_positions) != CONFIRMATORY_RESOURCE_COUNT
    ):
        raise ConfirmatoryValidationError(
            f"{label}[{index}] initial_state source_positions are invalid"
        )
    for position in source_positions:
        if (
            not isinstance(position, list)
            or len(position) != 2
            or any(
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(float(value))
                for value in position
            )
        ):
            raise ConfirmatoryValidationError(
                f"{label}[{index}] initial_state source position is invalid"
            )


def _record_map(
    records: Sequence[Mapping[str, Any]], label: str
) -> dict[tuple[str, int], Mapping[str, Any]]:
    result: dict[tuple[str, int], Mapping[str, Any]] = {}
    for record in records:
        key = (str(record["condition"]), int(record["environment_seed"]))
        if key in result:
            raise ConfirmatoryValidationError(f"duplicate {label} record for {key}")
        result[key] = record
    return result


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ConfirmatoryValidationError(f"{label} must be an object")
    return value


def _validate_git_sha(git_sha: str) -> None:
    if not isinstance(git_sha, str) or not _GIT_SHA_PATTERN.fullmatch(git_sha):
        raise ValueError("git_sha must be a full 40-hex Git SHA")


def _mean_optional(records: Sequence[Mapping[str, Any]], field: str) -> str:
    values = [float(record[field]) for record in records]
    return f"{statistics.fmean(values):.6f}"


def _package_version() -> str | None:
    try:
        return version("aweform")
    except PackageNotFoundError:
        return None


def _write_without_overwrite(path: Path, content: str) -> None:
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError as error:
        raise FileExistsError(
            f"refusing to overwrite existing report: {path}"
        ) from error
    with os.fdopen(descriptor, "w", encoding="utf-8") as file:
        file.write(content)


if __name__ == "__main__":
    sys.exit(main())
