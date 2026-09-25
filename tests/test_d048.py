"""Focused D-048 extended-exposure protocol and isolation tests."""

from __future__ import annotations

import math

import pytest

from aweform.d046 import (
    D046_CALIBRATION_TRANSITIONS,
    D046_DEFAULT_SEEDS,
    D046_HOLDOUT_ACTIONS,
    D046_HOLDOUT_POSES,
    D046ConsequencePredictor,
    build_d046_curriculum,
    validate_d046_development_seeds,
)
from aweform.d048 import (
    D048_CHANNELS,
    D048_CHECKPOINTS,
    D048_HOLDOUT_CANDIDATE_COUNT,
    D048_HOLDOUT_PAIR_COUNT,
    D048_PASS_COUNT,
    D048_TOTAL_TRANSITIONS,
    _candidate,
    _ContrastAggregate,
    _evaluate_checkpoint,
    _execute_seed,
    _FrozenPredictor,
    _seed_payload,
)


def test_protocol_constants_and_exact_heldout_support() -> None:
    assert D048_CHECKPOINTS == (0, 1, 2, 4, 8)
    assert D048_PASS_COUNT == 8
    assert D048_TOTAL_TRANSITIONS == 8 * D046_CALIBRATION_TRANSITIONS == 4512
    assert len(D046_HOLDOUT_POSES) == 9
    assert len(D046_HOLDOUT_ACTIONS) == 9
    assert D048_HOLDOUT_CANDIDATE_COUNT == 81
    assert D048_HOLDOUT_PAIR_COUNT == 324


def test_d046_curriculum_is_reused_unchanged_for_all_passes() -> None:
    curriculum = build_d046_curriculum(21046)
    repeated = tuple(curriculum.steps) * D048_PASS_COUNT
    assert len(curriculum.steps) == D046_CALIBRATION_TRANSITIONS
    assert len(repeated) == D048_TOTAL_TRANSITIONS
    assert all(
        repeated[offset : offset + D046_CALIBRATION_TRANSITIONS]
        == tuple(curriculum.steps)
        for offset in range(0, D048_TOTAL_TRANSITIONS, D046_CALIBRATION_TRANSITIONS)
    )


def test_seed_guard_is_exact_and_rejects_non_authorized_block() -> None:
    assert validate_d046_development_seeds(D046_DEFAULT_SEEDS) == D046_DEFAULT_SEEDS
    with pytest.raises(ValueError, match="exactly seeds"):
        validate_d046_development_seeds(D046_DEFAULT_SEEDS[:-1])


def test_fresh_d046_predictors_are_zero_initialized() -> None:
    full = D046ConsequencePredictor()
    state_only = D046ConsequencePredictor(state_only=True)
    assert full.weights == (0.0,) * 528
    assert state_only.weights == (0.0,) * 528


def test_one_seed_runs_eight_continuous_passes_and_all_checkpoints() -> None:
    execution = _execute_seed(21046, evaluate_checkpoints=True)

    assert execution.transitions == D048_TOTAL_TRANSITIONS
    assert execution.completed_passes == D048_PASS_COUNT
    assert execution.environment_reset_count == 1
    assert tuple(execution.checkpoint_evaluations) == D048_CHECKPOINTS
    assert [row["transition_count"] for row in execution.pass_payloads] == [
        D046_CALIBRATION_TRANSITIONS
    ] * D048_PASS_COUNT
    assert all(row["complete"] is True for row in execution.pass_payloads)
    assert all(
        row["evaluation"]["support"]["candidate_action_evaluations"] == 81
        and row["evaluation"]["support"]["unordered_action_pair_comparisons"]
        == 324
        for row in execution.checkpoint_payloads
    )
    assert execution.full_digest
    assert execution.state_only_digest
    assert math.isfinite(
        execution.checkpoint_payloads[-1]["weights"]["full"]["l2_norm"]
    )


def test_checkpoint_evaluation_is_read_only_and_shadow_identity_holds() -> None:
    execution = _execute_seed(21046, evaluate_checkpoints=True)
    control = _execute_seed(21046, evaluate_checkpoints=False)
    payload = _seed_payload(execution, control)
    controls = payload["lifetime_controls"]

    assert all(
        row["causal_isolation"]["live_environment_unchanged"] is True
        and row["causal_isolation"]["full_digest_unchanged"] is True
        and row["causal_isolation"]["state_only_digest_unchanged"] is True
        for row in execution.checkpoint_payloads
    )
    assert controls["instrumented_vs_uninstrumented"] == {
        "trajectory_digest_equal": True,
        "full_learner_digest_equal": True,
        "state_only_learner_digest_equal": True,
        "final_environment_fingerprint_equal": True,
        "checkpoint_controls": {
            str(checkpoint): execution.checkpoint_payloads[index][
                "causal_isolation"
            ]
            for index, checkpoint in enumerate(D048_CHECKPOINTS)
        },
    }
    for row in execution.checkpoint_payloads:
        comparators = row["evaluation"]["action_pair_discrimination"][
            "action_indifferent_comparators"
        ]
        assert comparators["state_only"]["contrast"] == "structural zero"
        assert comparators["zero_change"]["contrast"] == "structural zero"


def test_action_indifferent_comparators_are_channel_specific_zero_metrics() -> None:
    zero = _FrozenPredictor((0.0,) * 528, state_only=False)
    evaluation = _evaluate_checkpoint(21046, zero, zero)
    payload = evaluation.payload()
    discrimination = payload["action_pair_discrimination"]
    comparators = discrimination["action_indifferent_comparators"]
    expected = {channel: _ContrastAggregate() for channel in D048_CHANNELS}

    for pose in D046_HOLDOUT_POSES:
        candidates = [
            _candidate(zero, zero, pose, action)[1]
            for action in D046_HOLDOUT_ACTIONS
        ]
        for index, first in enumerate(candidates):
            for second in candidates[index + 1 :]:
                for channel_index, channel in enumerate(D048_CHANNELS):
                    expected[channel].add(
                        0.0,
                        first.actual[channel_index] - second.actual[channel_index],
                    )

    state_metrics = comparators["state_only"]["pooled_by_channel"]
    zero_metrics = comparators["zero_change"]["pooled_by_channel"]
    for channel in D048_CHANNELS:
        assert state_metrics[channel] == expected[channel].payload()
        assert zero_metrics[channel] == expected[channel].payload()
    assert len({tuple(sorted(metric.items())) for metric in state_metrics.values()}) > 1
