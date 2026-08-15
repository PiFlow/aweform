"""Development-only deterministic execution and recording for EXP-000."""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import sys
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from importlib.metadata import PackageNotFoundError, version
from numbers import Integral
from pathlib import Path
from typing import Any, Mapping, Sequence

import gymnasium
import numpy as np

from .controllers import (
    ControllerMode,
    EnergyBlindController,
    HomeostaticConfig,
    HomeostaticController,
    PersistentExplorationController,
)
from .env import Action, AweformEnv, AweformEnvConfig, TransitionTelemetry

ARTIFACT_SCHEMA_VERSION = "exp-000-development-v2"
MANIFEST_SCHEMA_VERSION = "exp-000-development-manifest-v2"


class Condition(Enum):
    """The three matched EXP-000 development conditions."""

    A_PERSISTENT = "A_PERSISTENT_EXPLORATION"
    B_HOMEOSTATIC = "B_HOMEOSTATIC"
    C_ENERGY_BLIND = "C_ENERGY_BLIND"


@dataclass(frozen=True, slots=True)
class EvaluatorInitialState:
    """Privileged simulator state captured before the first action."""

    x: float
    y: float
    heading: float
    energy: float
    source_positions: tuple[tuple[float, float], ...]


@dataclass(frozen=True, slots=True)
class TransitionRecord:
    """One raw evaluator-side transition, including the controller input."""

    step_index: int
    x: float
    y: float
    heading: float
    energy: float
    action: Action
    observation: tuple[float, float, float, float]
    harvested_energy: float
    basal_cost: float
    action_cost: float
    energy_before: float
    energy_after: float
    terminated: bool
    truncated: bool
    mode: ControllerMode | None


@dataclass(frozen=True, slots=True)
class EpisodeTrajectory:
    """Initial evaluator truth plus every executed transition."""

    condition: Condition
    environment_seed: int
    initial_state: EvaluatorInitialState
    transitions: tuple[TransitionRecord, ...]


@dataclass(frozen=True, slots=True)
class EpisodeSummary:
    """Threshold-free diagnostics for one development episode."""

    condition: Condition
    environment_seed: int
    steps_executed: int
    terminated_viability_failure: bool
    truncated_at_horizon: bool
    horizon_survival: bool
    initial_normalized_energy: float
    final_normalized_energy: float
    minimum_normalized_energy: float
    total_harvested_energy: float
    total_basal_energy_cost: float
    total_action_energy_cost: float
    total_distance_travelled: float
    explore_steps: int | None
    seek_resource_steps: int | None
    mode_transitions: int | None


@dataclass(frozen=True, slots=True)
class EpisodeRecord:
    """The summary and raw trajectory for one condition/seed pair."""

    summary: EpisodeSummary
    trajectory: EpisodeTrajectory


@dataclass(frozen=True, slots=True)
class DevelopmentManifest:
    """Runtime and configuration provenance for a development batch."""

    schema_version: str
    experiment: str
    purpose: str
    git_commit_sha: str
    environment_config: Mapping[str, Any]
    homeostatic_config: Mapping[str, Any]
    energy_blind_masked_energy: float
    environment_seeds: tuple[int, ...]
    conditions: tuple[str, ...]
    python_version: str
    numpy_version: str
    gymnasium_version: str
    aweform_package_version: str | None
    platform: Mapping[str, str]
    run_started_at_utc: str
    metadata: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class DevelopmentBatchResult:
    """Complete deterministic development output, before optional writing."""

    manifest: DevelopmentManifest
    episodes: tuple[EpisodeRecord, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return the stable JSON-shaped representation of this batch."""
        return {
            "schema_version": ARTIFACT_SCHEMA_VERSION,
            "manifest": _to_json_value(self.manifest),
            "episode_summaries": [
                _to_json_value(record.summary) for record in self.episodes
            ],
            "raw_trajectories": [
                _to_json_value(record.trajectory) for record in self.episodes
            ],
        }


def run_development_batch(
    seeds: Sequence[int],
    env_config: AweformEnvConfig,
    homeostatic_config: HomeostaticConfig,
    masked_energy: float,
    git_sha: str,
    metadata: Mapping[str, Any] | None = None,
) -> DevelopmentBatchResult:
    """Run A, B, and C in caller-supplied seed order.

    The caller controls the seed sequence; this API is development-only. Every
    condition receives a freshly constructed environment reset with the exact
    same seed and configuration for each caller-supplied seed.
    """
    validated_seeds = _validate_seeds(seeds)
    if not isinstance(git_sha, str) or not git_sha.strip():
        raise ValueError("git_sha must be a non-empty string")
    if metadata is not None and not isinstance(metadata, Mapping):
        raise ValueError("metadata must be a mapping when supplied")

    # Constructing this controller validates the explicit mask before any
    # episode starts and keeps the runner's C condition unambiguous.
    EnergyBlindController(masked_energy=masked_energy, config=homeostatic_config)

    run_started_at_utc = datetime.now(timezone.utc).isoformat()
    episodes: list[EpisodeRecord] = []
    for seed in validated_seeds:
        for condition in Condition:
            episodes.append(
                _run_episode(
                    condition=condition,
                    environment_seed=seed,
                    env_config=env_config,
                    homeostatic_config=homeostatic_config,
                    masked_energy=masked_energy,
                )
            )

    manifest = DevelopmentManifest(
        schema_version=MANIFEST_SCHEMA_VERSION,
        experiment="EXP-000",
        purpose="development",
        git_commit_sha=git_sha,
        environment_config=_to_json_value(env_config),
        homeostatic_config=_to_json_value(homeostatic_config),
        energy_blind_masked_energy=masked_energy,
        environment_seeds=tuple(validated_seeds),
        conditions=tuple(condition.value for condition in Condition),
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
        run_started_at_utc=run_started_at_utc,
        metadata=dict(metadata or {}),
    )
    return DevelopmentBatchResult(manifest=manifest, episodes=tuple(episodes))


def write_development_json(
    result: DevelopmentBatchResult,
    output_path: str | os.PathLike[str],
) -> Path:
    """Write one development artifact without ever overwriting an existing file."""
    path = Path(output_path)
    serialized = (
        json.dumps(
            result.to_dict(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
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


def _run_episode(
    *,
    condition: Condition,
    environment_seed: int,
    env_config: AweformEnvConfig,
    homeostatic_config: HomeostaticConfig,
    masked_energy: float,
) -> EpisodeRecord:
    env = AweformEnv(env_config)
    controller = _make_controller(condition, homeostatic_config, masked_energy)
    controller.reset()
    observation, info = env.reset(seed=environment_seed)
    if info != {}:
        raise RuntimeError(
            "environment reset crossed the evaluator information boundary"
        )
    initial_state = _initial_state(env)
    transitions: list[TransitionRecord] = []
    total_distance = 0.0
    previous_position = (initial_state.x, initial_state.y)
    mode_counts = {mode: 0 for mode in ControllerMode}
    mode_transitions = 0
    previous_mode = _controller_mode(controller)

    terminated = False
    truncated = False
    while not (terminated or truncated):
        controller_observation = _observation_tuple(observation)
        action = controller.act(controller_observation)
        mode = _controller_mode(controller)
        if mode is not None:
            mode_counts[mode] += 1
            if previous_mode is not None and mode is not previous_mode:
                mode_transitions += 1
            previous_mode = mode

        next_observation, reward, terminated, truncated, info = env.step(action)
        if reward != 0.0:
            raise RuntimeError("EXP-000 reward must remain exactly 0.0")
        if info != {}:
            raise RuntimeError(
                "environment step crossed the evaluator information boundary"
            )
        telemetry = env.last_transition
        if telemetry is None:
            raise RuntimeError(
                "environment did not expose evaluator transition telemetry"
            )
        if telemetry.action is not action:
            raise RuntimeError(
                "environment telemetry action disagrees with controller action"
            )
        if env.body is None:
            raise RuntimeError("environment body disappeared during episode")
        position = env.body.position
        total_distance += math.dist(previous_position, position)
        previous_position = position
        transitions.append(
            _transition_record(
                telemetry=telemetry,
                observation=controller_observation,
                x=env.body.x,
                y=env.body.y,
                heading=env.body.heading,
                energy=env.body.energy,
                mode=mode,
            )
        )
        observation = next_observation

    trajectory = EpisodeTrajectory(
        condition=condition,
        environment_seed=environment_seed,
        initial_state=initial_state,
        transitions=tuple(transitions),
    )
    summary = _summarize(
        trajectory=trajectory,
        env_config=env_config,
        mode_counts=mode_counts,
        mode_transitions=mode_transitions,
        total_distance=total_distance,
    )
    return EpisodeRecord(summary=summary, trajectory=trajectory)


def _make_controller(
    condition: Condition,
    config: HomeostaticConfig,
    masked_energy: float,
) -> PersistentExplorationController | HomeostaticController | EnergyBlindController:
    if condition is Condition.A_PERSISTENT:
        return PersistentExplorationController(config.exploration_steps)
    if condition is Condition.B_HOMEOSTATIC:
        return HomeostaticController(config)
    return EnergyBlindController(masked_energy=masked_energy, config=config)


def _controller_mode(
    controller: PersistentExplorationController
    | HomeostaticController
    | EnergyBlindController,
) -> ControllerMode | None:
    if isinstance(controller, PersistentExplorationController):
        return None
    return controller.mode


def _initial_state(env: AweformEnv) -> EvaluatorInitialState:
    if env.body is None or env.resource_field is None:
        raise RuntimeError("environment did not initialize evaluator state")
    return EvaluatorInitialState(
        x=env.body.x,
        y=env.body.y,
        heading=env.body.heading,
        energy=env.body.energy,
        source_positions=env.resource_field.source_positions,
    )


def _transition_record(
    *,
    telemetry: TransitionTelemetry,
    observation: tuple[float, float, float, float],
    x: float,
    y: float,
    heading: float,
    energy: float,
    mode: ControllerMode | None,
) -> TransitionRecord:
    return TransitionRecord(
        step_index=telemetry.step_index,
        x=x,
        y=y,
        heading=heading,
        energy=energy,
        action=telemetry.action,
        observation=observation,
        harvested_energy=telemetry.harvested_energy,
        basal_cost=telemetry.basal_cost,
        action_cost=telemetry.action_cost,
        energy_before=telemetry.energy_before,
        energy_after=telemetry.energy_after,
        terminated=telemetry.terminated,
        truncated=telemetry.truncated,
        mode=mode,
    )


def _summarize(
    *,
    trajectory: EpisodeTrajectory,
    env_config: AweformEnvConfig,
    mode_counts: Mapping[ControllerMode, int],
    mode_transitions: int,
    total_distance: float,
) -> EpisodeSummary:
    transitions = trajectory.transitions
    energy_values = [trajectory.initial_state.energy]
    energy_values.extend(transition.energy_after for transition in transitions)

    def normalize(energy: float) -> float:
        return (energy - env_config.energy.failure_boundary) / (
            env_config.energy.maximum_energy - env_config.energy.failure_boundary
        )

    final_energy = transitions[-1].energy_after
    last_transition = transitions[-1]
    return EpisodeSummary(
        condition=trajectory.condition,
        environment_seed=trajectory.environment_seed,
        steps_executed=len(transitions),
        terminated_viability_failure=last_transition.terminated,
        truncated_at_horizon=last_transition.truncated,
        horizon_survival=last_transition.truncated,
        initial_normalized_energy=normalize(trajectory.initial_state.energy),
        final_normalized_energy=normalize(final_energy),
        minimum_normalized_energy=min(normalize(energy) for energy in energy_values),
        total_harvested_energy=sum(
            transition.harvested_energy for transition in transitions
        ),
        total_basal_energy_cost=sum(
            transition.basal_cost for transition in transitions
        ),
        total_action_energy_cost=sum(
            transition.action_cost for transition in transitions
        ),
        total_distance_travelled=total_distance,
        explore_steps=(
            mode_counts[ControllerMode.EXPLORE]
            if trajectory.condition is not Condition.A_PERSISTENT
            else None
        ),
        seek_resource_steps=(
            mode_counts[ControllerMode.SEEK_RESOURCE]
            if trajectory.condition is not Condition.A_PERSISTENT
            else None
        ),
        mode_transitions=(
            mode_transitions
            if trajectory.condition is not Condition.A_PERSISTENT
            else None
        ),
    )


def _observation_tuple(
    observation: np.ndarray[Any, Any],
) -> tuple[float, float, float, float]:
    if len(observation) != 4:
        raise RuntimeError("environment observation no longer has four values")
    return (
        float(observation[0]),
        float(observation[1]),
        float(observation[2]),
        float(observation[3]),
    )


def _validate_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    if isinstance(seeds, (str, bytes)):
        raise ValueError("seeds must be a non-empty sequence of non-negative integers")
    try:
        supplied_seeds = tuple(seeds)
    except TypeError as error:
        raise ValueError(
            "seeds must be a non-empty sequence of non-negative integers"
        ) from error
    if not supplied_seeds:
        raise ValueError("seeds must not be empty")
    validated: list[int] = []
    for seed in supplied_seeds:
        if isinstance(seed, bool) or not isinstance(seed, Integral) or seed < 0:
            raise ValueError("seeds must contain only non-negative integer values")
        validated.append(int(seed))
    return tuple(validated)


def _package_version() -> str | None:
    try:
        return version("aweform")
    except PackageNotFoundError:
        return None


def _to_json_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {
            field.name: _to_json_value(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Mapping):
        return {str(key): _to_json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_to_json_value(item) for item in value]
    if isinstance(value, np.generic):
        return value.item()
    return value


def main(argv: Sequence[str] | None = None) -> int:
    """Run the intentionally small development artifact CLI."""
    default_environment_config = AweformEnvConfig()
    parser = argparse.ArgumentParser(
        description="Generate an EXP-000 development run artifact."
    )
    parser.add_argument("--seed", nargs="+", type=int, required=True)
    parser.add_argument("--masked-energy", type=float, required=True)
    parser.add_argument("--resource-count", type=int, default=1)
    parser.add_argument(
        "--episode-horizon",
        type=_positive_int_argument,
        default=default_environment_config.episode_horizon,
    )
    parser.add_argument(
        "--resource-length-scale",
        type=_positive_finite_float_argument,
        default=default_environment_config.resource_length_scale,
    )
    parser.add_argument("--git-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = run_development_batch(
        seeds=args.seed,
        env_config=AweformEnvConfig(
            resource_count=args.resource_count,
            episode_horizon=args.episode_horizon,
            resource_length_scale=args.resource_length_scale,
        ),
        homeostatic_config=HomeostaticConfig(),
        masked_energy=args.masked_energy,
        git_sha=args.git_sha,
    )
    write_development_json(result, args.output)
    return 0


def _positive_int_argument(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a positive integer") from error
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _positive_finite_float_argument(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a positive finite float") from error
    if not math.isfinite(parsed) or parsed <= 0.0:
        raise argparse.ArgumentTypeError("must be a positive finite float")
    return parsed


if __name__ == "__main__":
    sys.exit(main())
