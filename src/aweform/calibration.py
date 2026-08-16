"""Deterministic, artifact-only summarization for EXP-000 calibration."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .controllers import HomeostaticConfig
from .env import AweformEnvConfig
from .runner import ARTIFACT_SCHEMA_VERSION, MANIFEST_SCHEMA_VERSION, Condition

CALIBRATION_SEEDS = tuple(range(1001, 1031))
CALIBRATION_ROUND_1 = "Round 1"
CALIBRATION_ROUND_2 = "Round 2"
CALIBRATION_ROUNDS = {
    CALIBRATION_ROUND_1: (0.15, 0.20, 0.25),
    CALIBRATION_ROUND_2: (0.35, 0.40, 0.45),
}
CALIBRATION_LENGTH_SCALES = tuple(
    scale for round_scales in CALIBRATION_ROUNDS.values() for scale in round_scales
)
CALIBRATION_ARTIFACT_COUNT = 3
CALIBRATION_HORIZON = 500
CALIBRATION_MASKED_ENERGY = 0.5
CALIBRATION_RESOURCE_COUNT = 1


class CalibrationValidationError(ValueError):
    """Raised when an artifact does not satisfy the calibration contract."""


@dataclass(frozen=True, slots=True)
class ConditionDiagnostics:
    """Aggregate calibration diagnostics for one condition and candidate."""

    condition: str
    episode_count: int
    mean_lifespan: float
    median_lifespan: float
    minimum_lifespan: int
    maximum_lifespan: int
    horizon_survival_count: int
    horizon_survival_fraction: float
    mean_final_normalized_energy: float
    mean_minimum_normalized_energy: float
    mean_total_harvested_energy: float
    mean_total_action_energy_cost: float
    mean_total_distance_travelled: float
    mean_seek_resource_steps: float | None = None
    mean_explore_steps: float | None = None
    mean_mode_transitions: float | None = None


@dataclass(frozen=True, slots=True)
class CandidateDiagnostics:
    """All diagnostics and frozen selection flags for one length scale."""

    resource_length_scale: float
    by_condition: Mapping[str, ConditionDiagnostics]
    b_recovery_seed_count: int
    b_total_recoveries: int
    a_c_identical_seed_count: int
    a_c_divergent_seed_count: int
    c_distance_from_midpoint: float
    c_difficulty_acceptable: bool
    b_mechanism_acceptable: bool

    @property
    def acceptable(self) -> bool:
        """Whether this candidate satisfies the preregistered rule."""
        return self.c_difficulty_acceptable and self.b_mechanism_acceptable


@dataclass(frozen=True, slots=True)
class CalibrationSummary:
    """Pure summary of exactly one complete calibration round."""

    calibration_round: str
    git_commit_sha: str
    candidates: tuple[CandidateDiagnostics, ...]
    selected_candidate: CandidateDiagnostics | None

    def to_markdown(self) -> str:
        """Render a compact deterministic Markdown calibration report."""
        lines = [
            "# EXP-000 Calibration Summary",
            "",
            "This is a development/calibration diagnostic, not a confirmatory result.",
            "",
            f"- Calibration round: `{self.calibration_round}`",
            f"- Calibration Git SHA: `{self.git_commit_sha}`",
            f"- Calibration seeds: `{CALIBRATION_SEEDS[0]}–{CALIBRATION_SEEDS[-1]}` "
            f"({len(CALIBRATION_SEEDS)} matched seeds)",
            f"- Masked energy: `{CALIBRATION_MASKED_ENERGY}`",
            f"- Episode horizon: `{CALIBRATION_HORIZON}`",
            f"- Resource count: `{CALIBRATION_RESOURCE_COUNT}`",
            "",
            "## Candidate diagnostics",
            "",
            "| Length scale | Condition | N | Mean life | Median | Min | Max | "
            "Survive | Survival fraction | Mean final energy | Mean min energy | "
            "Mean harvested | Mean action cost | Mean distance |",
            "| ---: | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | "
            "---: | ---: | ---: | ---: | ---: |",
        ]
        for candidate in self.candidates:
            for condition in (
                Condition.A_PERSISTENT.value,
                Condition.B_HOMEOSTATIC.value,
                Condition.C_ENERGY_BLIND.value,
            ):
                diagnostics = candidate.by_condition[condition]
                lines.append(
                    "| "
                    + " | ".join(
                        (
                            f"{candidate.resource_length_scale:.2f}",
                            condition,
                            str(diagnostics.episode_count),
                            f"{diagnostics.mean_lifespan:.2f}",
                            f"{diagnostics.median_lifespan:.2f}",
                            str(diagnostics.minimum_lifespan),
                            str(diagnostics.maximum_lifespan),
                            str(diagnostics.horizon_survival_count),
                            f"{diagnostics.horizon_survival_fraction:.3f}",
                            f"{diagnostics.mean_final_normalized_energy:.4f}",
                            f"{diagnostics.mean_minimum_normalized_energy:.4f}",
                            f"{diagnostics.mean_total_harvested_energy:.4f}",
                            f"{diagnostics.mean_total_action_energy_cost:.4f}",
                            f"{diagnostics.mean_total_distance_travelled:.4f}",
                        )
                    )
                    + " |"
                )

        lines.extend(
            [
                "",
                "## Selection diagnostics",
                "",
                "| Length scale | C mean lifespan | Distance from 250 | "
                "C band [100, 400] | "
                "B recovery seeds | B recovery criterion | Acceptable |",
                "| ---: | ---: | ---: | :--- | ---: | :--- | :--- |",
            ]
        )
        for candidate in self.candidates:
            lines.append(
                "| "
                + " | ".join(
                    (
                        f"{candidate.resource_length_scale:.2f}",
                        f"{candidate.by_condition[Condition.C_ENERGY_BLIND.value].mean_lifespan:.2f}",
                        f"{candidate.c_distance_from_midpoint:.2f}",
                        _yes_no(candidate.c_difficulty_acceptable),
                        str(candidate.b_recovery_seed_count),
                        _yes_no(candidate.b_mechanism_acceptable),
                        _yes_no(candidate.acceptable),
                    )
                )
                + " |"
            )

        lines.extend(
            [
                "",
                "### B recovery diagnostics",
                "",
                "| Length scale | Seeds with recovery | Total recoveries | "
                "Mean seek steps | "
                "Mean explore steps | Mean mode transitions |",
                "| ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for candidate in self.candidates:
            b = candidate.by_condition[Condition.B_HOMEOSTATIC.value]
            lines.append(
                f"| {candidate.resource_length_scale:.2f} | "
                f"{candidate.b_recovery_seed_count} | {candidate.b_total_recoveries} | "
                f"{_format_optional(b.mean_seek_resource_steps)} | "
                f"{_format_optional(b.mean_explore_steps)} | "
                f"{_format_optional(b.mean_mode_transitions)} |"
            )

        lines.extend(
            [
                "",
                "### A/C identity sanity check",
                "",
                "| Length scale | Identical matched seeds | Divergent matched seeds |",
                "| ---: | ---: | ---: |",
            ]
        )
        for candidate in self.candidates:
            lines.append(
                f"| {candidate.resource_length_scale:.2f} | "
                f"{candidate.a_c_identical_seed_count} | "
                f"{candidate.a_c_divergent_seed_count} |"
            )

        if self.selected_candidate is None:
            selection = "No calibration candidate satisfies the frozen selection rule."
        else:
            selection = (
                "Protocol-selected candidate: `resource_length_scale = "
                f"{self.selected_candidate.resource_length_scale:.2f}`."
            )
        lines.extend(
            [
                "",
                "## Frozen selection result",
                "",
                selection,
                "",
                "Environment selection does not use B-versus-C effect size.",
                "B recovery count is used only as the preregistered mechanism-"
                "exercise qualification gate. B lifespan, B−C effect size, B "
                "performance advantage, and visual appearance do not rank or "
                "select among qualifying candidates.",
                "No scientific claim is made from calibration results.",
                "",
            ]
        )
        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class _Artifact:
    path: Path
    length_scale: float
    manifest: Mapping[str, Any]
    summaries: Mapping[tuple[str, int], Mapping[str, Any]]
    trajectories: Mapping[tuple[str, int], Mapping[str, Any]]


def summarize_calibration_artifacts(
    artifact_paths: Sequence[str | Path],
) -> CalibrationSummary:
    """Validate and summarize exactly one complete calibration round."""
    if len(artifact_paths) != CALIBRATION_ARTIFACT_COUNT:
        raise CalibrationValidationError(
            "exactly three calibration artifacts are required"
        )
    artifacts = tuple(_load_artifact(Path(path)) for path in artifact_paths)
    calibration_round = _validate_artifact_set(artifacts)
    candidates = tuple(_summarize_candidate(artifact) for artifact in artifacts)
    divergent_candidates = tuple(
        candidate for candidate in candidates if candidate.a_c_divergent_seed_count > 0
    )
    if divergent_candidates:
        details = ", ".join(
            f"{candidate.resource_length_scale:.2f} "
            f"({candidate.a_c_divergent_seed_count} divergent matched seeds)"
            for candidate in divergent_candidates
        )
        raise CalibrationValidationError(
            "A/C structural sanity check failed: matched trajectories diverged "
            f"for {details}. No calibration candidate may be selected or "
            "interpreted; investigate the cause before confirmatory execution."
        )
    acceptable = [candidate for candidate in candidates if candidate.acceptable]
    selected = (
        min(
            acceptable,
            key=lambda candidate: (
                candidate.c_distance_from_midpoint,
                candidate.resource_length_scale,
            ),
        )
        if acceptable
        else None
    )
    git_sha = str(artifacts[0].manifest["git_commit_sha"])
    return CalibrationSummary(
        calibration_round=calibration_round,
        git_commit_sha=git_sha,
        candidates=candidates,
        selected_candidate=selected,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Summarize existing calibration artifacts without executing the model."""
    parser = argparse.ArgumentParser(
        description=(
            "Summarize three validated EXP-000 artifacts from one recognized "
            "calibration round."
        )
    )
    parser.add_argument("artifacts", nargs=3, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        markdown = summarize_calibration_artifacts(args.artifacts).to_markdown()
        if args.output is None:
            sys.stdout.write(markdown)
        else:
            _write_without_overwrite(args.output, markdown)
    except (CalibrationValidationError, OSError) as error:
        parser.exit(2, f"calibration validation error: {error}\n")
    return 0


def _load_artifact(path: Path) -> _Artifact:
    try:
        with path.open(encoding="utf-8") as file:
            payload = json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        raise CalibrationValidationError(
            f"could not read valid JSON artifact {path}: {error}"
        ) from error

    root = _mapping(payload, f"{path}: root")
    if root.get("schema_version") != ARTIFACT_SCHEMA_VERSION:
        raise CalibrationValidationError(
            f"{path}: unsupported artifact schema version "
            f"{root.get('schema_version')!r}; expected {ARTIFACT_SCHEMA_VERSION!r}"
        )
    manifest = _mapping(root.get("manifest"), f"{path}: manifest")
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise CalibrationValidationError(
            f"{path}: unsupported manifest schema version "
            f"{manifest.get('schema_version')!r}; expected {MANIFEST_SCHEMA_VERSION!r}"
        )
    if manifest.get("experiment") != "EXP-000":
        raise CalibrationValidationError(f"{path}: manifest experiment must be EXP-000")
    if manifest.get("purpose") != "development":
        raise CalibrationValidationError(
            f"{path}: manifest purpose must be the current development purpose"
        )
    git_sha = manifest.get("git_commit_sha")
    if not isinstance(git_sha, str) or not git_sha:
        raise CalibrationValidationError(f"{path}: git_commit_sha must be non-empty")

    environment_config = _mapping(
        manifest.get("environment_config"), f"{path}: environment_config"
    )
    if environment_config.get("resource_count") != CALIBRATION_RESOURCE_COUNT:
        raise CalibrationValidationError(f"{path}: resource_count must be 1")
    if environment_config.get("episode_horizon") != CALIBRATION_HORIZON:
        raise CalibrationValidationError(f"{path}: episode_horizon must be 500")
    length_scale = _finite_number(
        environment_config.get("resource_length_scale"),
        f"{path}: resource_length_scale",
    )
    if length_scale <= 0:
        raise CalibrationValidationError(
            f"{path}: resource_length_scale must be positive"
        )
    if not any(
        _same_float(length_scale, expected) for expected in CALIBRATION_LENGTH_SCALES
    ):
        raise CalibrationValidationError(
            f"{path}: resource_length_scale must be one of {CALIBRATION_LENGTH_SCALES}"
        )
    expected_environment_config = asdict(
        AweformEnvConfig(
            episode_horizon=CALIBRATION_HORIZON,
            resource_count=CALIBRATION_RESOURCE_COUNT,
            resource_length_scale=length_scale,
        )
    )
    actual_environment_config = dict(environment_config)
    expected_environment_config.pop("resource_length_scale")
    actual_environment_config.pop("resource_length_scale", None)
    if _canonical_json(actual_environment_config) != _canonical_json(
        expected_environment_config
    ):
        raise CalibrationValidationError(
            f"{path}: environment configuration does not match the formal protocol"
        )
    if _canonical_json(manifest.get("homeostatic_config")) != _canonical_json(
        asdict(HomeostaticConfig())
    ):
        raise CalibrationValidationError(
            f"{path}: homeostatic configuration does not match the formal protocol"
        )
    masked_energy = _finite_number(
        manifest.get("energy_blind_masked_energy"),
        f"{path}: energy_blind_masked_energy",
    )
    if not _same_float(masked_energy, CALIBRATION_MASKED_ENERGY):
        raise CalibrationValidationError(f"{path}: masked energy must be 0.5")
    environment_seeds = manifest.get("environment_seeds")
    if (
        not isinstance(environment_seeds, list)
        or tuple(environment_seeds) != CALIBRATION_SEEDS
    ):
        raise CalibrationValidationError(
            f"{path}: environment_seeds must be exactly 1001–1030; "
            "acceptance seeds are not allowed"
        )
    expected_conditions = tuple(condition.value for condition in Condition)
    conditions = manifest.get("conditions")
    if not isinstance(conditions, list) or tuple(conditions) != expected_conditions:
        raise CalibrationValidationError(
            f"{path}: conditions must be exactly {expected_conditions}"
        )

    summaries = _episode_records(root.get("episode_summaries"), path, "summary")
    trajectories = _episode_records(root.get("raw_trajectories"), path, "trajectory")
    if set(summaries) != set(trajectories):
        raise CalibrationValidationError(
            f"{path}: summary and trajectory records do not contain the same episodes"
        )
    if set(summaries) != {
        (condition, seed)
        for seed in CALIBRATION_SEEDS
        for condition in expected_conditions
    }:
        raise CalibrationValidationError(
            f"{path}: artifacts must contain A/B/C for every calibration seed"
        )
    for key, summary in summaries.items():
        _validate_summary(summary, path, key)
        _validate_trajectory(
            trajectories[key],
            path,
            key,
            expected_steps=int(summary["steps_executed"]),
        )
    return _Artifact(
        path=path,
        length_scale=length_scale,
        manifest=manifest,
        summaries=summaries,
        trajectories=trajectories,
    )


def _validate_artifact_set(artifacts: Sequence[_Artifact]) -> str:
    for index, artifact in enumerate(artifacts):
        if any(
            _same_float(artifact.length_scale, other.length_scale)
            for other in artifacts[:index]
        ):
            raise CalibrationValidationError(
                f"duplicate resource_length_scale in {artifact.path}"
            )
    artifact_scales = {
        _candidate_scale(artifact.length_scale) for artifact in artifacts
    }
    matching_rounds = [
        round_name
        for round_name, round_scales in CALIBRATION_ROUNDS.items()
        if artifact_scales == set(round_scales)
    ]
    if len(matching_rounds) != 1:
        raise CalibrationValidationError(
            "artifacts must contain exactly one complete recognized calibration "
            "round; mixed or incomplete round candidates are not allowed"
        )
    first = artifacts[0]
    first_fingerprint = _configuration_fingerprint(first.manifest)
    for artifact in artifacts[1:]:
        if artifact.manifest.get("git_commit_sha") != first.manifest.get(
            "git_commit_sha"
        ):
            raise CalibrationValidationError(
                "artifacts must use the same Git commit SHA"
            )
        if _configuration_fingerprint(artifact.manifest) != first_fingerprint:
            raise CalibrationValidationError(
                "artifacts have mismatched software-relevant configurations"
            )
    return matching_rounds[0]


def _summarize_candidate(artifact: _Artifact) -> CandidateDiagnostics:
    by_condition: dict[str, ConditionDiagnostics] = {}
    for condition in (condition.value for condition in Condition):
        summaries = [
            summary
            for (recorded_condition, _seed), summary in artifact.summaries.items()
            if recorded_condition == condition
        ]
        by_condition[condition] = _condition_diagnostics(condition, summaries)

    b_recoveries_by_seed = {
        seed: _count_recoveries(
            artifact.trajectories[(Condition.B_HOMEOSTATIC.value, seed)]
        )
        for seed in CALIBRATION_SEEDS
    }
    a_c_identical = sum(
        _behavior_signature(artifact.trajectories[(Condition.A_PERSISTENT.value, seed)])
        == _behavior_signature(
            artifact.trajectories[(Condition.C_ENERGY_BLIND.value, seed)]
        )
        for seed in CALIBRATION_SEEDS
    )
    c_mean = by_condition[Condition.C_ENERGY_BLIND.value].mean_lifespan
    return CandidateDiagnostics(
        resource_length_scale=artifact.length_scale,
        by_condition=by_condition,
        b_recovery_seed_count=sum(count > 0 for count in b_recoveries_by_seed.values()),
        b_total_recoveries=sum(b_recoveries_by_seed.values()),
        a_c_identical_seed_count=a_c_identical,
        a_c_divergent_seed_count=len(CALIBRATION_SEEDS) - a_c_identical,
        c_distance_from_midpoint=abs(c_mean - 250.0),
        c_difficulty_acceptable=100.0 <= c_mean <= 400.0,
        b_mechanism_acceptable=sum(count > 0 for count in b_recoveries_by_seed.values())
        >= 6,
    )


def _condition_diagnostics(
    condition: str,
    summaries: Sequence[Mapping[str, Any]],
) -> ConditionDiagnostics:
    lifespans = [int(summary["steps_executed"]) for summary in summaries]
    survival_count = sum(bool(summary["horizon_survival"]) for summary in summaries)
    return ConditionDiagnostics(
        condition=condition,
        episode_count=len(summaries),
        mean_lifespan=statistics.mean(lifespans),
        median_lifespan=statistics.median(lifespans),
        minimum_lifespan=min(lifespans),
        maximum_lifespan=max(lifespans),
        horizon_survival_count=survival_count,
        horizon_survival_fraction=survival_count / len(summaries),
        mean_final_normalized_energy=_mean(summaries, "final_normalized_energy"),
        mean_minimum_normalized_energy=_mean(summaries, "minimum_normalized_energy"),
        mean_total_harvested_energy=_mean(summaries, "total_harvested_energy"),
        mean_total_action_energy_cost=_mean(summaries, "total_action_energy_cost"),
        mean_total_distance_travelled=_mean(summaries, "total_distance_travelled"),
        mean_seek_resource_steps=(
            _mean(summaries, "seek_resource_steps")
            if condition == Condition.B_HOMEOSTATIC.value
            else None
        ),
        mean_explore_steps=(
            _mean(summaries, "explore_steps")
            if condition == Condition.B_HOMEOSTATIC.value
            else None
        ),
        mean_mode_transitions=(
            _mean(summaries, "mode_transitions")
            if condition == Condition.B_HOMEOSTATIC.value
            else None
        ),
    )


def _configuration_fingerprint(manifest: Mapping[str, Any]) -> str:
    environment_config = dict(
        _mapping(manifest["environment_config"], "environment_config")
    )
    environment_config.pop("resource_length_scale", None)
    comparable = {
        key: value
        for key, value in manifest.items()
        if key
        not in {
            "git_commit_sha",
            "environment_seeds",
            "run_started_at_utc",
            "environment_config",
        }
    }
    comparable["environment_config"] = environment_config
    return json.dumps(comparable, sort_keys=True, separators=(",", ":"))


def _episode_records(
    value: Any,
    path: Path,
    record_kind: str,
) -> dict[tuple[str, int], Mapping[str, Any]]:
    if not isinstance(value, list):
        raise CalibrationValidationError(
            f"{path}: {record_kind} records must be a list"
        )
    records: dict[tuple[str, int], Mapping[str, Any]] = {}
    for record in value:
        mapping = _mapping(record, f"{path}: {record_kind} record")
        condition = mapping.get("condition")
        seed = mapping.get("environment_seed")
        if (
            not isinstance(condition, str)
            or not isinstance(seed, int)
            or isinstance(seed, bool)
        ):
            raise CalibrationValidationError(
                f"{path}: {record_kind} records need a condition and integer "
                "environment_seed"
            )
        key = (condition, seed)
        if key in records:
            raise CalibrationValidationError(
                f"{path}: duplicate {record_kind} record {key}"
            )
        records[key] = mapping
    return records


def _validate_summary(
    summary: Mapping[str, Any], path: Path, key: tuple[str, int]
) -> None:
    if summary.get("condition") != key[0] or summary.get("environment_seed") != key[1]:
        raise CalibrationValidationError(f"{path}: malformed summary key {key}")
    for field in (
        "initial_normalized_energy",
        "steps_executed",
        "final_normalized_energy",
        "minimum_normalized_energy",
        "total_harvested_energy",
        "total_basal_energy_cost",
        "total_action_energy_cost",
        "total_distance_travelled",
    ):
        _finite_number(summary.get(field), f"{path}: summary {key} {field}")
    if (
        not isinstance(summary["steps_executed"], int)
        or isinstance(summary["steps_executed"], bool)
        or not 0 < summary["steps_executed"] <= CALIBRATION_HORIZON
    ):
        raise CalibrationValidationError(f"{path}: invalid lifespan for summary {key}")
    if not isinstance(summary.get("horizon_survival"), bool):
        raise CalibrationValidationError(
            f"{path}: horizon_survival must be boolean for {key}"
        )
    if not isinstance(
        summary.get("terminated_viability_failure"), bool
    ) or not isinstance(summary.get("truncated_at_horizon"), bool):
        raise CalibrationValidationError(
            f"{path}: termination flags must be boolean for {key}"
        )
    mode_fields = ("seek_resource_steps", "explore_steps", "mode_transitions")
    if key[0] == Condition.A_PERSISTENT.value:
        if any(summary.get(field) is not None for field in mode_fields):
            raise CalibrationValidationError(
                f"{path}: A mode counts must be null for {key}"
            )
    elif key[0] in (
        Condition.B_HOMEOSTATIC.value,
        Condition.C_ENERGY_BLIND.value,
    ):
        for field in mode_fields:
            _finite_number(summary.get(field), f"{path}: summary {key} {field}")


def _validate_trajectory(
    trajectory: Mapping[str, Any],
    path: Path,
    key: tuple[str, int],
    *,
    expected_steps: int,
) -> None:
    if (
        trajectory.get("condition") != key[0]
        or trajectory.get("environment_seed") != key[1]
    ):
        raise CalibrationValidationError(f"{path}: malformed trajectory key {key}")
    initial_state = _mapping(
        trajectory.get("initial_state"), f"{path}: initial state {key}"
    )
    for field in ("x", "y", "heading", "energy"):
        _finite_number(initial_state.get(field), f"{path}: trajectory {key} {field}")
    if not isinstance(initial_state.get("source_positions"), list):
        raise CalibrationValidationError(
            f"{path}: trajectory {key} needs evaluator source_positions"
        )
    transitions = trajectory.get("transitions")
    if not isinstance(transitions, list) or not transitions:
        raise CalibrationValidationError(f"{path}: trajectory {key} has no transitions")
    if len(transitions) != expected_steps:
        raise CalibrationValidationError(
            f"{path}: trajectory {key} length does not match its summary"
        )
    for transition in transitions:
        record = _mapping(transition, f"{path}: transition {key}")
        for field in ("x", "y", "heading", "energy", "harvested_energy"):
            _finite_number(record.get(field), f"{path}: transition {key} {field}")
        if not isinstance(record.get("step_index"), int) or isinstance(
            record.get("step_index"), bool
        ):
            raise CalibrationValidationError(
                f"{path}: invalid step_index in trajectory {key}"
            )
        if not isinstance(record.get("action"), int) or isinstance(
            record.get("action"), bool
        ):
            raise CalibrationValidationError(
                f"{path}: invalid action in trajectory {key}"
            )
        observation = record.get("observation")
        if (
            not isinstance(observation, list)
            or len(observation) != 4
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                for value in observation
            )
        ):
            raise CalibrationValidationError(
                f"{path}: invalid observation in trajectory {key}"
            )
        for field in ("basal_cost", "action_cost", "energy_before", "energy_after"):
            _finite_number(record.get(field), f"{path}: transition {key} {field}")
        if not isinstance(record.get("terminated"), bool) or not isinstance(
            record.get("truncated"), bool
        ):
            raise CalibrationValidationError(
                f"{path}: invalid termination flags in trajectory {key}"
            )
        mode = record.get("mode")
        if key[0] == Condition.A_PERSISTENT.value:
            if mode is not None:
                raise CalibrationValidationError(
                    f"{path}: A trajectory mode must be null"
                )
        elif mode not in {"EXPLORE", "SEEK_RESOURCE"}:
            raise CalibrationValidationError(
                f"{path}: invalid controller mode in trajectory {key}"
            )


def _behavior_signature(trajectory: Mapping[str, Any]) -> tuple[Any, ...]:
    initial = _mapping(trajectory["initial_state"], "initial_state")
    initial_signature = tuple(
        initial[field] for field in ("x", "y", "heading", "energy")
    )
    transitions = _mapping_sequence(trajectory["transitions"], "transitions")
    transition_signature = tuple(
        tuple(
            transition[field]
            for field in (
                "action",
                "x",
                "y",
                "heading",
                "energy",
                "harvested_energy",
                "terminated",
                "truncated",
            )
        )
        for transition in transitions
    )
    return (initial_signature, transition_signature)


def _count_recoveries(trajectory: Mapping[str, Any]) -> int:
    transitions = _mapping_sequence(trajectory["transitions"], "transitions")
    modes = [transition["mode"] for transition in transitions]
    return sum(
        previous == "SEEK_RESOURCE" and current == "EXPLORE"
        for previous, current in zip(modes, modes[1:])
    )


def _mean(summaries: Sequence[Mapping[str, Any]], field: str) -> float:
    return statistics.mean(
        _finite_number(summary.get(field), field) for summary in summaries
    )


def _mapping(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CalibrationValidationError(f"{context} must be an object")
    return value


def _mapping_sequence(value: Any, context: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        raise CalibrationValidationError(f"{context} must be a list")
    return [_mapping(item, context) for item in value]


def _finite_number(value: Any, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CalibrationValidationError(f"{context} must be a finite number")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise CalibrationValidationError(f"{context} must be a finite number")
    return parsed


def _same_float(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-12)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _candidate_scale(value: float) -> float:
    for candidate in CALIBRATION_LENGTH_SCALES:
        if _same_float(value, candidate):
            return candidate
    raise CalibrationValidationError(f"unsupported length scale {value}")


def _format_optional(value: float | None) -> str:
    return "—" if value is None else f"{value:.2f}"


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _write_without_overwrite(path: Path, content: str) -> None:
    try:
        descriptor = path.open("x", encoding="utf-8")
    except FileExistsError as error:
        raise OSError(f"refusing to overwrite existing summary: {path}") from error
    with descriptor:
        descriptor.write(content)


if __name__ == "__main__":
    sys.exit(main())
