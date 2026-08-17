"""C-only calibration instrumentation for frozen EXP-001 protocol revision 003."""

from __future__ import annotations

import json
import math
import os
import platform
import statistics
import subprocess
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from numbers import Integral
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from .energy import EnergyConfig
from .env import AweformEnvConfig
from .exp001 import EXP001DevelopmentConfig, EXP001Mode
from .exp001_runner import (
    EXP001Condition,
    EXP001EpisodeRecord,
    run_exp001_c_episode,
)

EXP001_PROTOCOL_REVISION = "EXP-001-precalibration-003"
FORMAL_CALIBRATION_SEEDS = tuple(range(20001, 20201))
CONFIRMATORY_SEEDS = tuple(range(30001, 31001))
EXP001_CALIBRATION_HORIZON = 1000
FORMAL_EXECUTION_AUTHORIZATION = EXP001_PROTOCOL_REVISION
EXP001_CALIBRATION_ARTIFACT_SCHEMA_VERSION = "exp-001-calibration-v1"
EXP001_CALIBRATION_MANIFEST_SCHEMA_VERSION = "exp-001-calibration-manifest-v1"
EXP001_SELECTION_RULE_IDENTIFIER = "EXP-001-C-MEAN-LIFESPAN-3STEP-CANONICAL-TIE"
EXP001_SELECTION_RULE_TEXT = (
    "highest C mean capped lifespan; then highest C horizon-survival count; "
    "then highest C mean minimum normalized energy; then CURRENT > SHORT > LONG "
    "among exact remaining ties"
)


FROZEN_EXP001_CALIBRATION_ENV_CONFIG = AweformEnvConfig(
    world_min=(0.0, 0.0),
    world_max=(1.0, 1.0),
    energy=EnergyConfig(
        maximum_energy=10.0,
        basal_cost=0.1,
        failure_boundary=0.0,
    ),
    initial_energy=5.0,
    movement_distance=0.05,
    turn_angle=math.pi / 4.0,
    wait_cost=0.0,
    turn_cost=0.02,
    movement_cost=0.1,
    probe_distance=0.1,
    sensor_angle=math.pi / 4.0,
    harvest_rate=0.5,
    episode_horizon=EXP001_CALIBRATION_HORIZON,
    resource_peak_intensity=1.0,
    resource_length_scale=0.25,
    resource_count=1,
)


@dataclass(frozen=True, slots=True)
class EXP001CandidateDefinition:
    """One of the three protocol-frozen C timer candidates."""

    candidate: str
    explore_duration: int
    charge_duration: int


FORMAL_CANDIDATES = (
    EXP001CandidateDefinition("SHORT", 10, 5),
    EXP001CandidateDefinition("CURRENT", 20, 10),
    EXP001CandidateDefinition("LONG", 30, 15),
)
_CANDIDATE_NAMES = frozenset(candidate.candidate for candidate in FORMAL_CANDIDATES)
_TIE_PRIORITY = {"LONG": 0, "SHORT": 1, "CURRENT": 2}


@dataclass(frozen=True, slots=True)
class EXP001SharedControllerConfig:
    """Shared frozen controller values passed to every C candidate.

    C receives only external resource observations.  ``enter_seek`` and
    ``recover`` remain structurally frozen because they are part of the shared
    development configuration, but C's energy-blind policy does not read
    either field.
    """

    resource_contact_threshold: float
    enter_seek: float
    recover: float

    def for_candidate(
        self,
        candidate: EXP001CandidateDefinition,
    ) -> EXP001DevelopmentConfig:
        """Build the complete immutable development config for one candidate."""
        return EXP001DevelopmentConfig(
            resource_contact_threshold=self.resource_contact_threshold,
            blind_explore_duration=candidate.explore_duration,
            blind_charge_duration=candidate.charge_duration,
            enter_seek=self.enter_seek,
            recover=self.recover,
        )


FROZEN_EXP001_SHARED_CONTROLLER_CONFIG = EXP001SharedControllerConfig(
    resource_contact_threshold=0.8,
    enter_seek=0.35,
    recover=0.85,
)
EXP001_C_ENERGY_BLIND_CONFIG_NOTE = (
    "C receives only ExternalObservation(L/F/R); enter_seek and recover are "
    "frozen structural fields and are unused by C's energy-blind policy."
)


@dataclass(frozen=True, slots=True)
class EXP001CEpisodeDiagnostics:
    """Evaluator-only diagnostics derived from one C episode."""

    capped_lifespan: int
    horizon_survivor: bool
    final_normalized_energy: float
    minimum_normalized_energy: float
    total_harvested_energy: float
    explore_actions: int
    seek_resource_actions: int
    charge_actions: int
    complete_cycle_count: int


@dataclass(frozen=True, slots=True)
class EXP001CandidateSummary:
    """The aggregate C diagnostics permitted in a calibration result."""

    candidate: str
    explore_duration: int
    charge_duration: int
    episode_count: int
    mean_capped_lifespan: float
    median_capped_lifespan: float
    minimum_capped_lifespan: int
    maximum_capped_lifespan: int
    horizon_survival_count: int
    horizon_survival_fraction: float
    mean_final_normalized_energy: float
    mean_minimum_normalized_energy: float
    mean_total_harvested_energy: float
    mean_explore_actions: float
    mean_seek_resource_actions: float
    mean_charge_actions: float
    mean_complete_cycle_count: float


@dataclass(frozen=True, slots=True)
class EXP001CalibrationResult:
    """Immutable aggregate result with no per-seed outcomes or trajectories."""

    schema_version: str
    experiment: str
    purpose: str
    protocol_revision: str
    git_commit_sha: str | None
    python_version: str
    numpy_version: str
    horizon: int
    environment_config: AweformEnvConfig
    shared_controller_config: EXP001SharedControllerConfig
    candidate_definitions: tuple[EXP001CandidateDefinition, ...]
    formal_calibration_seed_start: int
    formal_calibration_seed_end: int
    formal_calibration_seed_count: int
    executed_seed_count: int
    candidate_summaries: tuple[EXP001CandidateSummary, ...]
    selected_candidate: str
    selection_rule_identifier: str
    selection_rule: str

    def to_dict(self) -> dict[str, Any]:
        """Return a stable JSON-shaped representation of aggregate output."""
        return {
            "schema_version": self.schema_version,
            "manifest": {
                "schema_version": EXP001_CALIBRATION_MANIFEST_SCHEMA_VERSION,
                "experiment": self.experiment,
                "purpose": self.purpose,
                "result_classification": (
                    "calibration/development output — not confirmatory evidence"
                ),
                "protocol_revision": self.protocol_revision,
                "git_commit_sha": self.git_commit_sha,
                "python_version": self.python_version,
                "numpy_version": self.numpy_version,
                "horizon": self.horizon,
                "environment_config": _json_value(asdict(self.environment_config)),
                "shared_controller_config": asdict(self.shared_controller_config),
                "c_energy_blind_config_note": EXP001_C_ENERGY_BLIND_CONFIG_NOTE,
                "candidate_definitions": [
                    asdict(candidate) for candidate in self.candidate_definitions
                ],
                "formal_calibration_seed_range": {
                    "start": self.formal_calibration_seed_start,
                    "end": self.formal_calibration_seed_end,
                    "count": self.formal_calibration_seed_count,
                },
                "seed_reservations": {
                    "calibration": {
                        "start": FORMAL_CALIBRATION_SEEDS[0],
                        "end": FORMAL_CALIBRATION_SEEDS[-1],
                        "count": len(FORMAL_CALIBRATION_SEEDS),
                    },
                    "confirmatory": {
                        "start": CONFIRMATORY_SEEDS[0],
                        "end": CONFIRMATORY_SEEDS[-1],
                        "count": len(CONFIRMATORY_SEEDS),
                    },
                },
                "executed_seed_count": self.executed_seed_count,
                "selection_rule_identifier": self.selection_rule_identifier,
                "selection_rule": self.selection_rule,
            },
            "candidate_summaries": [
                asdict(summary) for summary in self.candidate_summaries
            ],
            "selected_candidate": self.selected_candidate,
        }

    def to_json(self) -> str:
        """Serialize the result deterministically without timestamps."""
        return (
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)
            + "\n"
        )


def frozen_exp001_calibration_environment_config() -> AweformEnvConfig:
    """Return the immutable environment configuration frozen by EXP-001."""
    return FROZEN_EXP001_CALIBRATION_ENV_CONFIG


def validate_debug_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    """Validate non-reserved debug seeds before any environment is created."""
    validated = _validate_seed_sequence(seeds)
    reserved = set(FORMAL_CALIBRATION_SEEDS) | set(CONFIRMATORY_SEEDS)
    overlap = tuple(seed for seed in validated if seed in reserved)
    if overlap:
        raise ValueError(
            "debug seeds overlap reserved EXP-001 seed ranges: "
            + ", ".join(str(seed) for seed in sorted(set(overlap)))
        )
    return validated


def run_exp001_c_debug_calibration(
    seeds: Sequence[int],
) -> EXP001CalibrationResult:
    """Run all three frozen C candidates on caller-supplied debug seeds."""
    validated_seeds = validate_debug_seeds(seeds)
    return _run_c_calibration(
        seeds=validated_seeds,
        purpose="debug",
    )


def run_exp001_formal_calibration(
    authorization: str,
) -> EXP001CalibrationResult:
    """Run formal C calibration only with explicit protocol authorization.

    This entry point is intentionally not called by tests or development
    tooling in this PR.
    """
    if authorization != FORMAL_EXECUTION_AUTHORIZATION:
        raise PermissionError(
            "formal EXP-001 calibration requires authorization "
            f"{FORMAL_EXECUTION_AUTHORIZATION!r}"
        )
    return _run_c_calibration(
        seeds=FORMAL_CALIBRATION_SEEDS,
        purpose="calibration",
    )


def summarize_exp001_c_episode(
    episode: EXP001EpisodeRecord,
) -> EXP001CEpisodeDiagnostics:
    """Aggregate permitted evaluator diagnostics for one C episode."""
    if episode.condition is not EXP001Condition.C:
        raise ValueError("calibration diagnostics require an EXP-001 C episode")
    transitions = episode.transitions
    if not transitions:
        raise ValueError("C episode must contain at least one completed transition")

    config = FROZEN_EXP001_CALIBRATION_ENV_CONFIG
    capped_lifespan = min(len(transitions), config.episode_horizon)
    final_transition = transitions[-1].privileged_evaluator
    horizon_survivor = (
        len(transitions) == config.episode_horizon
        and final_transition.truncated
        and not final_transition.terminated
    )
    energy_values = [
        _normalize_energy(episode.initial_state.actual_energy, config),
        *(_normalize_energy(
            transition.privileged_evaluator.actual_energy,
            config,
        ) for transition in transitions),
    ]
    mode_sequence = [
        transition.privileged_evaluator.controller_mode
        for transition in transitions
    ]
    return EXP001CEpisodeDiagnostics(
        capped_lifespan=capped_lifespan,
        horizon_survivor=horizon_survivor,
        final_normalized_energy=energy_values[-1],
        minimum_normalized_energy=min(energy_values),
        total_harvested_energy=math.fsum(
            transition.privileged_evaluator.harvested_energy
            for transition in transitions
        ),
        explore_actions=sum(mode is EXP001Mode.EXPLORE for mode in mode_sequence),
        seek_resource_actions=sum(
            mode is EXP001Mode.SEEK_RESOURCE for mode in mode_sequence
        ),
        charge_actions=sum(mode is EXP001Mode.CHARGE for mode in mode_sequence),
        complete_cycle_count=_count_complete_cycles(mode_sequence),
    )


def select_exp001_candidate(
    summaries: Sequence[EXP001CandidateSummary],
) -> str:
    """Select a candidate using the frozen pure C-only selection rule."""
    candidates = tuple(summaries)
    _validate_candidate_summaries(candidates)

    remaining = candidates
    highest_mean = max(summary.mean_capped_lifespan for summary in remaining)
    remaining = tuple(
        summary
        for summary in remaining
        if summary.mean_capped_lifespan == highest_mean
    )
    highest_survival = max(summary.horizon_survival_count for summary in remaining)
    remaining = tuple(
        summary
        for summary in remaining
        if summary.horizon_survival_count == highest_survival
    )
    highest_minimum = max(
        summary.mean_minimum_normalized_energy for summary in remaining
    )
    remaining = tuple(
        summary
        for summary in remaining
        if summary.mean_minimum_normalized_energy == highest_minimum
    )
    return max(
        remaining,
        key=lambda summary: _TIE_PRIORITY[summary.candidate],
    ).candidate


def write_exp001_calibration_json(
    result: EXP001CalibrationResult,
    output_path: str | os.PathLike[str],
) -> Path:
    """Write one deterministic calibration artifact without overwriting."""
    if not isinstance(result, EXP001CalibrationResult):
        raise ValueError("result must be an EXP001CalibrationResult")
    path = Path(output_path)
    serialized = result.to_json()
    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o644,
        )
    except FileExistsError as error:
        raise FileExistsError(
            f"refusing to overwrite existing artifact: {path}"
        ) from error
    with os.fdopen(descriptor, "w", encoding="utf-8") as file:
        file.write(serialized)
    return path


def _run_c_calibration(
    *,
    seeds: Sequence[int],
    purpose: str,
) -> EXP001CalibrationResult:
    validated_seeds = _validate_calibration_execution_request(seeds, purpose)
    git_commit_sha = _current_git_sha() if purpose == "calibration" else None
    environment_config = frozen_exp001_calibration_environment_config()
    summaries: list[EXP001CandidateSummary] = []
    for candidate in FORMAL_CANDIDATES:
        development_config = FROZEN_EXP001_SHARED_CONTROLLER_CONFIG.for_candidate(
            candidate
        )
        episodes = tuple(
            run_exp001_c_episode(
                environment_seed=seed,
                env_config=environment_config,
                development_config=development_config,
            )
            for seed in validated_seeds
        )
        summaries.append(_summarize_candidate(candidate, episodes))

    immutable_summaries = tuple(summaries)
    return EXP001CalibrationResult(
        schema_version=EXP001_CALIBRATION_ARTIFACT_SCHEMA_VERSION,
        experiment="EXP-001",
        purpose=purpose,
        protocol_revision=EXP001_PROTOCOL_REVISION,
        git_commit_sha=git_commit_sha,
        python_version=platform.python_version(),
        numpy_version=np.__version__,
        horizon=EXP001_CALIBRATION_HORIZON,
        environment_config=environment_config,
        shared_controller_config=FROZEN_EXP001_SHARED_CONTROLLER_CONFIG,
        candidate_definitions=FORMAL_CANDIDATES,
        formal_calibration_seed_start=FORMAL_CALIBRATION_SEEDS[0],
        formal_calibration_seed_end=FORMAL_CALIBRATION_SEEDS[-1],
        formal_calibration_seed_count=len(FORMAL_CALIBRATION_SEEDS),
        executed_seed_count=len(validated_seeds),
        candidate_summaries=immutable_summaries,
        selected_candidate=select_exp001_candidate(immutable_summaries),
        selection_rule_identifier=EXP001_SELECTION_RULE_IDENTIFIER,
        selection_rule=EXP001_SELECTION_RULE_TEXT,
    )


def _summarize_candidate(
    candidate: EXP001CandidateDefinition,
    episodes: Sequence[EXP001EpisodeRecord],
) -> EXP001CandidateSummary:
    diagnostics = tuple(summarize_exp001_c_episode(episode) for episode in episodes)
    if not diagnostics:
        raise ValueError("candidate calibration requires at least one episode")
    lifespan_values = [diagnostic.capped_lifespan for diagnostic in diagnostics]
    return EXP001CandidateSummary(
        candidate=candidate.candidate,
        explore_duration=candidate.explore_duration,
        charge_duration=candidate.charge_duration,
        episode_count=len(diagnostics),
        mean_capped_lifespan=_mean(lifespan_values),
        median_capped_lifespan=float(statistics.median(lifespan_values)),
        minimum_capped_lifespan=min(lifespan_values),
        maximum_capped_lifespan=max(lifespan_values),
        horizon_survival_count=sum(
            diagnostic.horizon_survivor for diagnostic in diagnostics
        ),
        horizon_survival_fraction=(
            sum(diagnostic.horizon_survivor for diagnostic in diagnostics)
            / len(diagnostics)
        ),
        mean_final_normalized_energy=_mean(
            diagnostic.final_normalized_energy for diagnostic in diagnostics
        ),
        mean_minimum_normalized_energy=_mean(
            diagnostic.minimum_normalized_energy for diagnostic in diagnostics
        ),
        mean_total_harvested_energy=_mean(
            diagnostic.total_harvested_energy for diagnostic in diagnostics
        ),
        mean_explore_actions=_mean(
            diagnostic.explore_actions for diagnostic in diagnostics
        ),
        mean_seek_resource_actions=_mean(
            diagnostic.seek_resource_actions for diagnostic in diagnostics
        ),
        mean_charge_actions=_mean(
            diagnostic.charge_actions for diagnostic in diagnostics
        ),
        mean_complete_cycle_count=_mean(
            diagnostic.complete_cycle_count for diagnostic in diagnostics
        ),
    )


def _count_complete_cycles(mode_sequence: Sequence[EXP001Mode]) -> int:
    compressed: list[EXP001Mode] = []
    for mode in mode_sequence:
        if not compressed or compressed[-1] is not mode:
            compressed.append(mode)
    cycle = (
        EXP001Mode.EXPLORE,
        EXP001Mode.SEEK_RESOURCE,
        EXP001Mode.CHARGE,
        EXP001Mode.EXPLORE,
    )
    return sum(
        tuple(compressed[index : index + len(cycle)]) == cycle
        for index in range(len(compressed) - len(cycle) + 1)
    )


def _normalize_energy(energy: float, config: AweformEnvConfig) -> float:
    energy_range = (
        config.energy.maximum_energy - config.energy.failure_boundary
    )
    return (energy - config.energy.failure_boundary) / energy_range


def _mean(values: Iterable[float]) -> float:
    collected = tuple(values)
    if not collected:
        raise ValueError("cannot calculate a mean of no values")
    return math.fsum(collected) / len(collected)


def _validate_candidate_summaries(
    summaries: Sequence[EXP001CandidateSummary],
) -> None:
    if {summary.candidate for summary in summaries} != _CANDIDATE_NAMES:
        raise ValueError("summaries must contain exactly SHORT, CURRENT, and LONG")
    if len(summaries) != len(_CANDIDATE_NAMES):
        raise ValueError("summaries must contain one row per candidate")
    for summary in summaries:
        if summary.episode_count <= 0:
            raise ValueError("candidate summaries must contain at least one episode")
        for value in (
            summary.mean_capped_lifespan,
            summary.median_capped_lifespan,
            summary.horizon_survival_fraction,
            summary.mean_final_normalized_energy,
            summary.mean_minimum_normalized_energy,
            summary.mean_total_harvested_energy,
            summary.mean_explore_actions,
            summary.mean_seek_resource_actions,
            summary.mean_charge_actions,
            summary.mean_complete_cycle_count,
        ):
            if not math.isfinite(value):
                raise ValueError("candidate summary values must be finite")


def _validate_seed_sequence(seeds: Sequence[int]) -> tuple[int, ...]:
    if isinstance(seeds, (str, bytes)):
        raise ValueError("seeds must be a non-empty sequence of non-negative integers")
    try:
        supplied = tuple(seeds)
    except TypeError as error:
        raise ValueError(
            "seeds must be a non-empty sequence of non-negative integers"
        ) from error
    if not supplied:
        raise ValueError("seeds must not be empty")
    validated: list[int] = []
    for seed in supplied:
        if isinstance(seed, bool) or not isinstance(seed, Integral) or seed < 0:
            raise ValueError("seeds must contain only non-negative integer values")
        validated.append(int(seed))
    return tuple(validated)


def _validate_calibration_execution_request(
    seeds: Sequence[int],
    purpose: str,
) -> tuple[int, ...]:
    """Enforce seed reservations at the lowest calibration execution layer."""
    if purpose not in {"debug", "calibration"}:
        raise ValueError("calibration purpose must be 'debug' or 'calibration'")
    validated = _validate_seed_sequence(seeds)
    supplied = set(validated)
    formal = set(FORMAL_CALIBRATION_SEEDS)
    confirmatory = set(CONFIRMATORY_SEEDS)
    if purpose == "debug":
        overlap = supplied & (formal | confirmatory)
        if overlap:
            raise ValueError(
                "debug calibration seeds overlap reserved EXP-001 seed ranges: "
                + ", ".join(str(seed) for seed in sorted(overlap))
            )
        return validated
    if validated != FORMAL_CALIBRATION_SEEDS:
        raise ValueError(
            "formal calibration requires exactly FORMAL_CALIBRATION_SEEDS in "
            "canonical order"
        )
    if supplied & confirmatory:
        raise ValueError("formal calibration cannot accept confirmatory seeds")
    return validated


def _current_git_sha() -> str:
    repository = _resolve_aweform_checkout()
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
        raise RuntimeError(
            "could not establish clean Git provenance for the Aweform source checkout"
        ) from error
    if status.stdout.strip():
        raise RuntimeError(
            "refusing formal calibration: tracked Aweform source checkout is dirty"
        )
    sha = head.stdout.strip()
    if len(sha) != 40 or any(character not in "0123456789abcdef" for character in sha):
        raise RuntimeError("Aweform source checkout returned an invalid Git HEAD SHA")
    return sha


def _resolve_aweform_checkout() -> Path:
    """Resolve the source checkout containing this running implementation."""
    module_path = Path(__file__).resolve()
    for parent in (module_path.parent, *module_path.parents):
        git_marker = parent / ".git"
        if (parent / "pyproject.toml").is_file() and git_marker.exists():
            return parent
    raise RuntimeError(
        "could not resolve an Aweform source checkout for formal Git provenance"
    )


def _json_value(value: object) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    return value
