"""Focused pre-treatment tests for the D-035C evaluator-only protocol."""

from __future__ import annotations

import math
from typing import cast

import pytest

from aweform import d020, d026, d027, d029, d035c
from aweform.env import Action


def _environment() -> d026.D026Env:
    environment = d026.D026Env()
    observation, info = environment.reset(
        options={
            "body_position": (0.40, 0.40),
            "station_center": (0.50, 0.50),
            "heading": 0.37,
            "battery_j": 2000.0,
            "body_temperature_c": 23.0,
            "charger_termination_latched": False,
        }
    )
    assert observation.shape == (6,)
    assert info == {}
    return environment


def test_d035c_freeze_and_action_boundary() -> None:
    assert d035c.D035C_HORIZON == 70_000
    assert d035c.D035C_BRANCH_HORIZON == 256
    assert d035c.D035C_DEFAULT_DEVELOPMENT_SEEDS == tuple(range(18468, 18488))
    assert d035c.D035C_CANDIDATES == (
        "WAIT",
        "TURN_LEFT",
        "TURN_RIGHT",
        "MOVE_FORWARD",
        "REVERSE_TRANSLATION",
    )
    assert [action.name for action in Action] == [
        "WAIT",
        "TURN_LEFT",
        "TURN_RIGHT",
        "MOVE_FORWARD",
    ]
    with pytest.raises(ValueError, match="exactly"):
        d035c._validate_d035c_development_seeds((18468, 18469))
    with pytest.raises(ValueError, match="reserved"):
        d035c._validate_d035c_development_seeds((50001, 50002))
    with pytest.raises(ValueError, match="only the reused"):
        d035c._validate_d035c_seed(18467)
    with pytest.raises(ValueError, match="exact clean executable SHA"):
        d035c.run_d035c_audit(executed_commit_sha=None)


def test_reverse_is_mirrored_move_with_canonical_bookkeeping() -> None:
    forward = _environment()
    reverse = _environment()
    forward.step(Action.MOVE_FORWARD)
    _, reward, terminated, truncated, info = d035c._reverse_step(reverse)
    assert reward == 0.0
    assert info == {}
    assert not terminated
    assert not truncated
    assert reverse.body is not None
    assert reverse.last_transition is not None
    assert reverse.last_transition.action is Action.MOVE_FORWARD
    assert reverse.last_transition.heading == pytest.approx(0.37)
    assert reverse.last_transition.actuator_electrical_power_w == (
        d020.D020PhysicalConfig().move_actuator_electrical_power_w
    )
    assert reverse.last_transition.battery_after_j == pytest.approx(
        forward.last_transition.battery_after_j  # type: ignore[union-attr]
    )
    assert reverse.last_transition.body_temperature_after_c == pytest.approx(
        forward.last_transition.body_temperature_after_c  # type: ignore[union-attr]
    )
    assert reverse.body.position[0] == pytest.approx(0.40 - 0.05 * math.cos(0.37))
    assert reverse.body.position[1] == pytest.approx(0.40 - 0.05 * math.sin(0.37))


def test_candidate_branches_are_read_only_and_order_invariant() -> None:
    environment = _environment()
    current = d029._next_visible(environment._observation().as_array())
    before = d029._environment_state(environment)
    forward, checks = d035c._candidate_outcomes(environment, current)
    reverse, reverse_checks = d035c._candidate_outcomes(
        environment, current, tuple(reversed(d035c.D035C_CANDIDATES))
    )
    assert checks["source_environment_unchanged"] is True
    assert reverse_checks["source_environment_unchanged"] is True
    assert d029._environment_state(environment) == before
    for label in d035c.D035C_CANDIDATES:
        assert d035c._candidate_identity(forward[label]) == d035c._candidate_identity(
            reverse[label]
        )
    learner = d027.D027ActionConsequencePredictor()
    weights = learner.weights
    assert learner.weights == weights
    assert "REVERSE_TRANSLATION" not in [action.name for action in Action]


def test_reverse_distance_clips_at_world_boundary() -> None:
    environment = d026.D026Env()
    environment.reset(
        options={
            "body_position": (0.0, 0.0),
            "station_center": (0.5, 0.5),
            "heading": 0.0,
            "battery_j": 2000.0,
            "body_temperature_c": 23.0,
            "charger_termination_latched": False,
        }
    )
    d035c._reverse_step(environment)
    assert environment.body is not None
    assert environment.body.position == (0.0, 0.0)
    assert environment.last_transition is not None
    assert cast(float, environment.last_transition.position_before[0]) == 0.0
    assert environment.last_transition.position_after == (0.0, 0.0)
