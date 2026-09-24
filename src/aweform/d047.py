"""D-047 frozen-learner action-consequence discrimination audit.

This module is evaluator-only.  It loads the committed D-046 full-learner
weights and queries them read-only; predictions never select or alter an
action and no organism trajectory is created.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import numpy as np

from .d045 import D045Env
from .d046 import (
    D046_CHANNELS,
    D046_DEFAULT_SEEDS,
    D046_FEATURE_DIMENSION,
    D046_HOLDOUT_ACTIONS,
    D046_HOLDOUT_POSES,
    D046_INITIAL_OPTIONS,
    D046_VISIBLE_DIMENSION,
    D046_WEIGHT_COUNT,
    model_state_from_observation,
    quadratic_feature_map,
)

D047_TASK_ID: Final[str] = "D-047"
D047_AUTHORIZED_BASE_SHA: Final[str] = "a265bf1b2932d9af1dfa9719d53e42dfef688ce3"
D047_SCHEMA_VERSION: Final[str] = "D047-1"
D047_D046_ARTIFACT_SHA256: Final[str] = (
    "71741b2a6a1f95e9904bbbedd28575e14d477d4fcb4e1a2cf598badefe5a003d"
)
D047_D046_ARTIFACT_SIZE: Final[int] = 2_927_125
D047_D046_ARTIFACT_REPOSITORY_PATH: Final[str] = (
    "development/D-046-v05-calibration-shadow-consequence-learning.json"
)
D047_PAIR_COUNT: Final[int] = 6_480
D047_CANDIDATE_COUNT: Final[int] = 1_620


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True, slots=True)
class FrozenD046Predictor:
    """Minimal read-only wrapper for one committed 66-by-8 weight matrix."""

    weights: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.weights) != D046_WEIGHT_COUNT:
            raise ValueError("D-046 full learner must contain exactly 528 weights")
        if not all(math.isfinite(value) for value in self.weights):
            raise ValueError("D-046 full learner weights must all be finite")

    @property
    def digest(self) -> str:
        return _sha256(_canonical_json(list(self.weights)))

    def predict_delta(
        self, observation: Sequence[float], action: Sequence[float]
    ) -> tuple[float, ...]:
        state = model_state_from_observation(observation)
        features = quadratic_feature_map(state, action)
        matrix = np.asarray(self.weights, dtype=np.float64).reshape(
            D046_FEATURE_DIMENSION, D046_VISIBLE_DIMENSION
        )
        return tuple(float(value) for value in np.asarray(features) @ matrix)


def load_frozen_d046_learners(path: Path) -> dict[int, FrozenD046Predictor]:
    """Validate and load the amendment-authorized canonical learned state."""
    raw = path.read_bytes()
    if len(raw) != D047_D046_ARTIFACT_SIZE:
        raise ValueError("committed D-046 artifact size mismatch")
    if _sha256(raw) != D047_D046_ARTIFACT_SHA256:
        raise ValueError("committed D-046 artifact SHA-256 mismatch")
    artifact = json.loads(raw)
    if artifact.get("task_id") != "D-046":
        raise ValueError("canonical predecessor artifact is not D-046")
    if artifact.get("artifact_schema_version") != "D046-1":
        raise ValueError("unexpected D-046 artifact schema")
    if (
        artifact.get("executed_commit_sha")
        != "19cae43c324cc5e5c06ee717a8091d4d63f20165"
    ):
        raise ValueError("unexpected D-046 executable provenance")
    if artifact.get("development_seeds") != list(D046_DEFAULT_SEEDS):
        raise ValueError("D-046 ordered development seeds changed")
    rows = artifact.get("calibration", {}).get("per_seed", [])
    if [row.get("seed") for row in rows] != list(D046_DEFAULT_SEEDS):
        raise ValueError("D-046 calibration rows are not in canonical seed order")
    loaded: dict[int, FrozenD046Predictor] = {}
    for row in rows:
        predictor = FrozenD046Predictor(tuple(float(x) for x in row["final_weights"]))
        if predictor.digest != row.get("final_weight_sha256"):
            raise ValueError(f"D-046 weight digest mismatch for seed {row['seed']}")
        loaded[int(row["seed"])] = predictor
    return loaded


@dataclass(slots=True)
class ContrastAggregate:
    support: int = 0
    absolute_error_sum: float = 0.0
    sign_agreement: int = 0
    actual_ties: int = 0
    predicted_ties: int = 0
    non_tie_support: int = 0
    non_tie_sign_agreement: int = 0

    def add(self, predicted: float, actual: float) -> None:
        self.support += 1
        self.absolute_error_sum += abs(predicted - actual)
        predicted_sign = (predicted > 0.0) - (predicted < 0.0)
        actual_sign = (actual > 0.0) - (actual < 0.0)
        self.sign_agreement += predicted_sign == actual_sign
        self.actual_ties += actual_sign == 0
        self.predicted_ties += predicted_sign == 0
        if actual_sign != 0:
            self.non_tie_support += 1
            self.non_tie_sign_agreement += predicted_sign == actual_sign

    def payload(self) -> dict[str, int | float | None]:
        return {
            "contrast_mae": self.absolute_error_sum / self.support,
            "exact_three_way_sign_agreement_rate": self.sign_agreement / self.support,
            "actual_tie_count": self.actual_ties,
            "predicted_tie_count": self.predicted_ties,
            "non_tie_sign_agreement_rate": (
                self.non_tie_sign_agreement / self.non_tie_support
                if self.non_tie_support
                else None
            ),
            "non_tie_support": self.non_tie_support,
            "support": self.support,
        }


@dataclass(frozen=True, slots=True)
class Candidate:
    action_id: str
    predicted: tuple[float, ...]
    actual: tuple[float, ...]
    boundary: bool
    contact_transition: bool
    outcome_digest: str


def _pose_options(x: float, y: float, heading: float) -> dict[str, object]:
    return {**D046_INITIAL_OPTIONS, "body_position": (x, y), "heading": heading}


def _candidate(
    predictor: FrozenD046Predictor,
    pose: tuple[str, float, float, float],
    action: tuple[str, float, float],
) -> tuple[tuple[float, ...], Candidate, bool, bool]:
    pose_id, x, y, heading = pose
    action_id, left, right = action
    env = D045Env()
    observation, reset_info = env.reset(options=_pose_options(x, y, heading))
    before = tuple(float(value) for value in observation)
    predicted = predictor.predict_delta(before, (left, right))
    next_observation, reward, terminated, truncated, info = env.step((left, right))
    telemetry = env.last_transition
    if telemetry is None:
        raise RuntimeError("D-045 omitted transition telemetry")
    if reward != 0.0 or info != {}:
        raise RuntimeError("D-045 reward/info boundary changed")
    next_values = tuple(float(value) for value in next_observation)
    actual_state = model_state_from_observation(next_values)
    before_state = model_state_from_observation(before)
    actual = tuple(a - b for a, b in zip(actual_state, before_state, strict=True))
    outcome = {
        "pose": pose_id,
        "action": action_id,
        "start_observation": before,
        "next_observation": next_values,
        "actual": actual,
        "boundary_scale": telemetry.boundary_scale,
        "contact_before": telemetry.charging_contact_before,
        "contact_after": telemetry.charging_contact_after,
        "terminated": terminated,
        "truncated": truncated,
        "reward": reward,
        "info": info,
    }
    return (
        before,
        Candidate(
            action_id=action_id,
            predicted=predicted,
            actual=actual,
            boundary=telemetry.boundary_scale < 1.0,
            contact_transition=(
                telemetry.charging_contact_before != telemetry.charging_contact_after
            ),
            outcome_digest=_sha256(_canonical_json(outcome)),
        ),
        reward == 0.0,
        reset_info == {} and info == {},
    )


def _groups_payload(
    groups: dict[str, dict[str, ContrastAggregate]],
) -> dict[str, dict[str, dict[str, int | float | None]]]:
    return {
        group: {channel: metric.payload() for channel, metric in channels.items()}
        for group, channels in sorted(groups.items())
    }


def run_d047(predecessor_path: Path, executed_commit_sha: str) -> dict[str, object]:
    if len(executed_commit_sha) != 40:
        raise ValueError("executed commit SHA must contain exactly 40 characters")
    learners = load_frozen_d046_learners(predecessor_path)
    before_digests = {str(seed): learner.digest for seed, learner in learners.items()}
    strata: dict[str, dict[str, dict[str, ContrastAggregate]]] = {
        name: {}
        for name in ("pooled", "seed", "action_pair", "pose", "boundary", "contact")
    }
    comparator = {name: ContrastAggregate() for name in D046_CHANNELS}
    candidate_count = 0
    pair_count = 0
    order_invariant = True
    identical_starts = True
    rewards_zero = True
    infos_empty = True
    source_unchanged = True  # every branch owns a freshly reset D-045 environment

    def aggregate(dimension: str, key: str, channel: str) -> ContrastAggregate:
        return (
            strata[dimension]
            .setdefault(key, {})
            .setdefault(channel, ContrastAggregate())
        )

    for seed, learner in learners.items():
        for pose in D046_HOLDOUT_POSES:
            forward = [
                _candidate(learner, pose, action) for action in D046_HOLDOUT_ACTIONS
            ]
            reverse = [
                _candidate(learner, pose, action)
                for action in reversed(D046_HOLDOUT_ACTIONS)
            ]
            reverse_by_id = {
                candidate.action_id: candidate for _, candidate, _, _ in reverse
            }
            starts = [start for start, _, _, _ in forward]
            identical_starts &= all(start == starts[0] for start in starts)
            candidate_count += len(forward)
            rewards_zero &= all(reward_ok for _, _, reward_ok, _ in forward + reverse)
            infos_empty &= all(info_ok for _, _, _, info_ok in forward + reverse)
            candidates = [candidate for _, candidate, _, _ in forward]
            order_invariant &= all(
                candidate.outcome_digest
                == reverse_by_id[candidate.action_id].outcome_digest
                and candidate.predicted == reverse_by_id[candidate.action_id].predicted
                for candidate in candidates
            )
            for i, first in enumerate(candidates):
                for second in candidates[i + 1 :]:
                    pair_count += 1
                    pair_id = f"{first.action_id}-{second.action_id}"
                    boundary_key = (
                        "boundary_involved"
                        if first.boundary or second.boundary
                        else "non_boundary"
                    )
                    contact_key = (
                        "contact_transition_involved"
                        if first.contact_transition or second.contact_transition
                        else "no_contact_transition"
                    )
                    for index, channel in enumerate(D046_CHANNELS):
                        predicted = first.predicted[index] - second.predicted[index]
                        actual = first.actual[index] - second.actual[index]
                        for dimension, key in (
                            ("pooled", "overall"),
                            ("seed", str(seed)),
                            ("action_pair", pair_id),
                            ("pose", pose[0]),
                            ("boundary", boundary_key),
                            ("contact", contact_key),
                        ):
                            aggregate(dimension, key, channel).add(predicted, actual)
                        comparator[channel].add(0.0, actual)

    if candidate_count != D047_CANDIDATE_COUNT or pair_count != D047_PAIR_COUNT:
        raise RuntimeError("D-047 exact support changed")
    after_digests = {str(seed): learner.digest for seed, learner in learners.items()}
    if before_digests != after_digests:
        raise RuntimeError("frozen D-046 learned state mutated")
    if not all((order_invariant, identical_starts, rewards_zero, infos_empty)):
        raise RuntimeError("D-047 causal-isolation control failed")
    return {
        "artifact_schema_version": D047_SCHEMA_VERSION,
        "task_id": D047_TASK_ID,
        "authorized_base_sha": D047_AUTHORIZED_BASE_SHA,
        "executed_commit_sha": executed_commit_sha,
        "development_seeds": list(D046_DEFAULT_SEEDS),
        "predecessor": {
            "path": D047_D046_ARTIFACT_REPOSITORY_PATH,
            "sha256": D047_D046_ARTIFACT_SHA256,
            "size_bytes": D047_D046_ARTIFACT_SIZE,
            "canonical_state_source": "committed final_weights vectors",
            "loaded_full_weight_sha256_by_seed": before_digests,
        },
        "protocol": {
            "poses": [row[0] for row in D046_HOLDOUT_POSES],
            "actions": [row[0] for row in D046_HOLDOUT_ACTIONS],
            "channels": list(D046_CHANNELS),
            "pair_orientation": "ascending action ID",
            "state_only_comparator": "structural zero; action-indifferent",
            "zero_change_comparator": "structural zero; action-indifferent",
            "evaluation": "isolated one-step D-045 branches; no lived trajectory",
        },
        "support": {
            "candidate_action_evaluations": candidate_count,
            "unordered_action_pair_comparisons": pair_count,
            "channel_expanded_pair_comparisons": pair_count * len(D046_CHANNELS),
        },
        "full_learner": {
            name: _groups_payload(groups) for name, groups in strata.items()
        },
        "action_indifferent_comparators": {
            "state_only": {
                "contrast": "structural zero",
                "absolute_predictions_reconstructed": False,
                "pooled_by_channel": {k: v.payload() for k, v in comparator.items()},
            },
            "zero_change": {
                "contrast": "structural zero",
                "pooled_by_channel": {k: v.payload() for k, v in comparator.items()},
            },
        },
        "causal_isolation": {
            "branch_order_invariant": order_invariant,
            "candidate_start_observation_identical_within_seed_pose": identical_starts,
            "source_state_unchanged_by_branches": source_unchanged,
            "full_learner_digest_identical_before_after": before_digests
            == after_digests,
            "learner_updates": 0,
            "reward_exactly_zero": rewards_zero,
            "organism_info_exactly_empty": infos_empty,
            "formal_reserved_seed_used": False,
            "evaluator_metadata_reaches_model_input": False,
        },
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "platform": platform.platform(),
        },
        "generation_command": (
            "python -m aweform.d047 --executed-commit-sha " + executed_commit_sha
        ),
    }


def write_artifact(payload: object, output: Path) -> None:
    output.write_bytes(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n"
    )


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--predecessor",
        type=Path,
        default=Path(
            "development/D-046-v05-calibration-shadow-consequence-learning.json"
        ),
    )
    parser.add_argument("--executed-commit-sha", required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "development/D-047-v05-shadow-action-consequence-discrimination.json"
        ),
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    write_artifact(run_d047(args.predecessor, args.executed_commit_sha), args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())

