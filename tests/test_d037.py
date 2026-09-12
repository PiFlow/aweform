"""Focused tests for the D-037 evaluator-only signal definitions."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from aweform import d037
from aweform.d011 import D011Observation
from aweform.env import Action
from aweform.exp003 import BeaconObservation


def _observation() -> D011Observation:
    return D011Observation(
        energy=0.4,
        beacon=BeaconObservation(
            left=0.1,
            forward=0.2,
            right=0.3,
            charging_contact=False,
        ),
        thermal=0.5,
    )


def _capture(weights: tuple[float, ...], action: Action) -> SimpleNamespace:
    predictions = {
        candidate: tuple(
            0.0 if output != 2 else weights[list(Action).index(candidate) * 42 + 14]
            for output in range(6)
        )
        for candidate in d037.D037_CANDIDATE_ACTIONS
    }
    return SimpleNamespace(
        learner_weights=weights,
        current=_observation(),
        historical_action=action,
        predictions=predictions,
        prediction_query_read_only=True,
    )


def test_d037_signal_formulas_are_fixed_and_use_candidate_actions() -> None:
    weights = [0.0] * 168
    for action, value in zip(d037.D037_CANDIDATE_ACTIONS, (1.0, 3.0, 2.0), strict=True):
        action_index = list(Action).index(action)
        weights[action_index * 42 + 2 * 7] = value
    signals = d037._signals_for_capture(_capture(tuple(weights), Action.TURN_LEFT))
    assert signals[0] == pytest.approx(1.0)
    assert signals[1] == pytest.approx(3.0)
    assert signals[2] == pytest.approx(1.0)
    assert signals[3] == pytest.approx(np.sqrt(2.0 / 3.0))
    assert signals[4] == pytest.approx(np.sqrt(2.0))
    assert signals[5] == pytest.approx(np.sqrt(14.0))


def test_d037_oscillation_onset_is_first_long_strict_alternating_run() -> None:
    actions = [Action.MOVE_FORWARD] + [
        Action.TURN_LEFT if index % 2 == 0 else Action.TURN_RIGHT for index in range(16)
    ]
    trace = tuple(
        SimpleNamespace(action=action, transition_index=index + 1)
        for index, action in enumerate(actions)
    )
    data = d037._DecisionData(
        seed=18468,
        trace=trace,
        visible_before=np.zeros((len(trace), 6)),
        eligible_indices=np.arange(1, len(trace), dtype=np.int64),
        signals_by_index=np.zeros((len(trace), len(d037.D037_SIGNALS))),
    )
    assert d037._oscillation_onset(data) == (1, 16)


def test_d037_seed_and_protocol_guards_are_frozen() -> None:
    assert d037.D037_DEFAULT_DEVELOPMENT_SEEDS == tuple(range(18468, 18488))
    assert d037.D037_TARGET_HORIZONS == (64, 256, 1024)
    assert d037.D037_CANDIDATE_ACTIONS == (
        Action.TURN_LEFT,
        Action.TURN_RIGHT,
        Action.MOVE_FORWARD,
    )
    with pytest.raises(ValueError, match="exactly"):
        d037._validate_seeds([18468, 18469])
    with pytest.raises(ValueError, match="only the reused"):
        d037._validate_seed(18467)
    with pytest.raises(ValueError, match="exact clean"):
        d037.run_d037_audit(executed_commit_sha=None)
