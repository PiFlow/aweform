"""Focused pre-freeze tests for the D-039 shadow-only scalar audit."""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

from aweform import d027, d031r1, d036, d039
from aweform.d011 import D011Observation
from aweform.d026 import D026Mode
from aweform.env import Action
from aweform.exp003 import BeaconObservation


def _observation(forward: float = 0.2, contact: bool = False) -> D011Observation:
    return D011Observation(
        energy=0.4,
        beacon=BeaconObservation(
            left=0.1,
            forward=forward,
            right=0.3,
            charging_contact=contact,
        ),
        thermal=0.5,
    )


def _data(length: int = 20) -> d039._TraceData:
    visible = np.asarray(
        [[0.4, 0.1, 0.2 + index * 0.01, 0.3, 0.0, 0.5] for index in range(length)]
    )
    trace = tuple(
        SimpleNamespace(
            transition_index=index + 1,
            action=(Action.TURN_LEFT if index % 2 == 0 else Action.TURN_RIGHT),
            mode_before=D026Mode.SEEK,
        )
        for index in range(length)
    )
    return d039._TraceData(
        seed=18468,
        trace=trace,
        trace_digest="digest",
        visible_before=visible,
        visible_after=visible.copy(),
        visible_after_forward=visible[:, 2] + 0.01,
        actions=np.asarray(
            [list(Action).index(row.action) for row in trace], dtype=np.int8
        ),
        eligible=np.ones(length, dtype=bool),
        reacquisition=np.zeros(length, dtype=bool),
        terminated=False,
        truncated=False,
        h_before=np.linspace(0.0, 0.19, length),
        h_after=np.linspace(0.01, 0.20, length),
        baseline_prediction=np.zeros(length),
        recurrent_prediction=np.zeros(length),
        observed_delta=np.full(length, 0.01),
    )


def test_d039_freeze_seed_alpha_and_boundary_guards() -> None:
    assert d039.D039_DEFAULT_DEVELOPMENT_SEEDS == tuple(range(18468, 18488))
    assert d039.D039_HORIZON == 70_000
    assert d039.D039_TARGET_HORIZONS == (64, 256, 1024)
    assert d039.D039_FIXED_ALPHA == 0.01
    assert d039.D039_RECURRENCE_ALPHA == d027.D027_LEARNING_RATE == 0.5
    with pytest.raises(ValueError, match="exactly"):
        d039._validate_seeds([18468, 18469])
    with pytest.raises(ValueError, match="only the reused"):
        d039._validate_seed(18467)
    with pytest.raises(ValueError, match="exact clean"):
        d039.run_d039_audit(executed_commit_sha=None)


def test_d039_initialization_timing_and_two_recurrence_forms_match() -> None:
    instrumentation = d039._Instrumentation()
    assert instrumentation.h == 0.0
    assert instrumentation.initialization_count == 1
    d039._D039Learner.instrumentation = instrumentation
    try:
        learner = d039._D039Learner()
        current = _observation()
        next_observation = _observation(forward=0.25)
        instrumentation.begin_decision(SimpleNamespace(mode=D026Mode.SEEK), current)
        instrumentation.finish_decision(Action.TURN_LEFT)
        update = learner.observe_transition(current, Action.TURN_LEFT, next_observation)
    finally:
        d039._D039Learner.instrumentation = None
    assert update.prediction[d027.D027_OUTPUTS.index("delta_beacon_forward")] == 0.0
    assert instrumentation.steps[0].h_before == 0.0
    assert instrumentation.steps[0].observed_delta == pytest.approx(0.05)
    assert instrumentation.steps[0].h_after == pytest.approx(0.025)
    assert instrumentation.recurrence_equivalence_checks == 1
    assert instrumentation.h == instrumentation.steps[0].h_after


def test_d039_uses_preupdate_executed_prediction_and_d027_updates_once() -> None:
    instrumentation = d039._Instrumentation()
    d039._D039Learner.instrumentation = instrumentation
    try:
        learner = d039._D039Learner()
        current = _observation()
        first_next = _observation(forward=0.3)
        second_next = _observation(forward=0.3)
        instrumentation.begin_decision(SimpleNamespace(mode=D026Mode.CHARGE), current)
        instrumentation.finish_decision(Action.TURN_RIGHT)
        first_update = learner.observe_transition(
            current, Action.TURN_RIGHT, first_next
        )
        instrumentation.begin_decision(SimpleNamespace(mode=D026Mode.SEEK), first_next)
        instrumentation.finish_decision(Action.TURN_RIGHT)
        second_update = learner.observe_transition(
            first_next, Action.TURN_RIGHT, second_next
        )
    finally:
        d039._D039Learner.instrumentation = None
    assert instrumentation.initialization_count == 1
    assert instrumentation.steps[1].h_before == pytest.approx(
        instrumentation.steps[0].h_after
    )
    assert instrumentation.update_count == 2
    assert first_update.action is Action.TURN_RIGHT
    assert second_update.action is Action.TURN_RIGHT
    assert instrumentation.steps[1].baseline_prediction == pytest.approx(
        second_update.prediction[d027.D027_OUTPUTS.index("delta_beacon_forward")]
    )


def test_d039_shadow_replay_preserves_short_arm_b_identity() -> None:
    shadow_trace: list[object] = []
    shadow, _, _ = d039._run_shadow_arm(18468, horizon=32, trace=shadow_trace)
    direct_trace: list[object] = []
    direct = d031r1._run_arm(
        18468,
        arm="LEARNED_NO_DETRAP",
        horizon=32,
        evaluator_diagnostics=True,
        trace_sink=direct_trace,
    )
    assert shadow["trajectory_digest"] == direct["trajectory_digest"]
    assert shadow["executed_update_digest"] == direct["executed_update_digest"]
    assert shadow["_weights"] == direct["_weights"]
    assert shadow["final_policy_rng_digest"] == direct["final_policy_rng_digest"]
    assert (
        shadow["final_environment_rng_digest"] == direct["final_environment_rng_digest"]
    )
    assert shadow["isolation"] == direct["isolation"]
    assert shadow["seek_arbitration"] == direct["seek_arbitration"]
    assert shadow_trace == direct_trace


def test_d039_s0_plus_h_and_d036_preaction_target_null_rules() -> None:
    data = _data(6)
    features = d039._feature_rows(data, np.asarray([2]), with_h=False)
    augmented = d039._feature_rows(data, np.asarray([2]), with_h=True)
    assert features.shape == (1, 6)
    assert augmented.shape == (1, 7)
    assert augmented[0, :6].tolist() == pytest.approx(features[0].tolist())
    assert augmented[0, 6] == pytest.approx(data.h_before[2])
    base = d036._TraceData(
        seed=data.seed,
        trace_digest=data.trace_digest,
        visible_before=data.visible_before,
        actions=data.actions,
        visible_after_forward=data.visible_after_forward,
        reacquisition=data.reacquisition,
        eligible=data.eligible,
        terminated=False,
        truncated=False,
        visible_after=data.visible_after,
    )
    target = d036._target_data(base, history=1, horizon=4)
    assert target.status_counts["available"] == 3
    assert target.status_counts["null_lifetime_boundary"] == 3
    assert target.indices.tolist() == [0, 1, 2]


def test_d039_pooled_error_summary_uses_each_seed_once() -> None:
    first = replace(
        _data(2),
        baseline_prediction=np.zeros(2),
        recurrent_prediction=np.zeros(2),
        observed_delta=np.zeros(2),
    )
    second = replace(
        _data(2),
        seed=18469,
        baseline_prediction=np.full(2, 10.0),
        recurrent_prediction=np.full(2, 10.0),
        observed_delta=np.zeros(2),
    )

    pooled = d039._pooled_error_summary({first.seed: first, second.seed: second})

    assert pooled["sample_count"] == 4
    assert pooled["baseline_mae"] == pytest.approx(5.0)
    assert pooled["recurrent_mae"] == pytest.approx(5.0)
    assert pooled["recurrent_minus_baseline_mae"] == pytest.approx(0.0)


def test_d039_s0_matching_ignores_h_and_excludes_anchor_candidates() -> None:
    data = _data()
    matched = d039._matched_index(data, 4, {4, 5})
    assert matched not in {4, 5}
    changed = replace(data, h_before=np.full(len(data.trace), 999.0))
    assert matched == d039._matched_index(changed, 4, {4, 5})


def test_d039_oscillation_definition_and_boundary_nulls_are_exact() -> None:
    data = _data(20)
    onset = d039._oscillation_onset(data)
    assert onset == (0, 20)
    assert d039._window_record(data, 0, -16)["status"] == "unavailable"
    assert d039._window_record(data, 0, 0)["status"] == "available"
    for row in data.trace:
        row.action = Action.TURN_LEFT
    assert d039._oscillation_onset(data) is None
