"""Focused D-047 frozen-state and causal-isolation tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aweform.d046 import D046_DEFAULT_SEEDS, D046_HOLDOUT_ACTIONS, D046_HOLDOUT_POSES
from aweform.d047 import (
    D047_CANDIDATE_COUNT,
    D047_D046_ARTIFACT_SHA256,
    D047_PAIR_COUNT,
    FrozenD046Predictor,
    _sha256,
    load_frozen_d046_learners,
    run_d047,
)

PREDECESSOR = Path("development/D-046-v05-calibration-shadow-consequence-learning.json")


def test_canonical_predecessor_and_all_weight_digests_load_exactly() -> None:
    raw = PREDECESSOR.read_bytes()
    learners = load_frozen_d046_learners(PREDECESSOR)
    artifact = json.loads(raw)

    assert _sha256(raw) == D047_D046_ARTIFACT_SHA256
    assert tuple(learners) == D046_DEFAULT_SEEDS
    assert len(learners) == 20
    assert all(len(learner.weights) == 528 for learner in learners.values())
    assert [learner.digest for learner in learners.values()] == [
        row["final_weight_sha256"] for row in artifact["calibration"]["per_seed"]
    ]


def test_frozen_predictor_rejects_wrong_or_nonfinite_state() -> None:
    with pytest.raises(ValueError, match="528"):
        FrozenD046Predictor((0.0,))
    with pytest.raises(ValueError, match="finite"):
        FrozenD046Predictor((float("nan"),) * 528)


def test_protocol_has_exact_frozen_matrix_support() -> None:
    assert len(D046_HOLDOUT_POSES) == 9
    assert len(D046_HOLDOUT_ACTIONS) == 9
    assert len(D046_DEFAULT_SEEDS) * 9 * 9 == D047_CANDIDATE_COUNT == 1_620
    assert len(D046_DEFAULT_SEEDS) * 9 * 36 == D047_PAIR_COUNT == 6_480


def test_complete_audit_is_read_only_order_invariant_and_exact_support() -> None:
    payload = run_d047(PREDECESSOR, "a" * 40)
    controls = payload["causal_isolation"]

    assert payload["support"] == {
        "candidate_action_evaluations": 1_620,
        "unordered_action_pair_comparisons": 6_480,
        "channel_expanded_pair_comparisons": 51_840,
    }
    assert controls == {
        "branch_order_invariant": True,
        "candidate_start_observation_identical_within_seed_pose": True,
        "source_state_unchanged_by_branches": True,
        "full_learner_digest_identical_before_after": True,
        "learner_updates": 0,
        "reward_exactly_zero": True,
        "organism_info_exactly_empty": True,
        "formal_reserved_seed_used": False,
        "evaluator_metadata_reaches_model_input": False,
    }
    comparators = payload["action_indifferent_comparators"]
    assert comparators["state_only"]["contrast"] == "structural zero"
    assert comparators["state_only"]["absolute_predictions_reconstructed"] is False
    assert comparators["zero_change"]["contrast"] == "structural zero"
    assert set(payload["full_learner"]) == {
        "pooled",
        "seed",
        "action_pair",
        "pose",
        "boundary",
        "contact",
    }

