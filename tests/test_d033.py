"""Focused tests for the D-033 evaluator-only sequence audit."""

from __future__ import annotations

from typing import cast

import pytest

from aweform import d030, d033
from aweform.env import Action


def test_d033_freeze_and_reused_seed_guard() -> None:
    assert d033.D033_HORIZON == 70_000
    assert d033.D033_BRANCH_HORIZON == 4096
    assert d033.D033_LENGTHS == (2, 4, 8, 16)
    assert d033.D033_DEFAULT_DEVELOPMENT_SEEDS == tuple(range(18468, 18488))
    assert (
        d033._validate_d033_development_seeds(d033.D033_DEFAULT_DEVELOPMENT_SEEDS)
        == d033.D033_DEFAULT_DEVELOPMENT_SEEDS
    )
    with pytest.raises(ValueError, match="exactly"):
        d033._validate_d033_development_seeds((18468, 18469))
    with pytest.raises(ValueError, match="reserved"):
        d033._validate_d033_development_seeds((50001, 50002))
    with pytest.raises(ValueError, match="reused development seeds"):
        d033._validate_d033_seed(18467)
    with pytest.raises(ValueError, match="70,000"):
        d033.run_d033_audit(
            seeds=d033.D033_DEFAULT_DEVELOPMENT_SEEDS,
            horizon=1,
        )


def test_d033_sequence_library_is_exact_and_does_not_add_families() -> None:
    kwargs = {"b_proposed": Action.MOVE_FORWARD, "a_first": Action.TURN_RIGHT}
    assert d033._sequence("REPEAT_B_PROPOSED", 4, **kwargs) == (
        Action.MOVE_FORWARD,
        Action.MOVE_FORWARD,
        Action.MOVE_FORWARD,
        Action.MOVE_FORWARD,
    )
    assert d033._sequence("REPEAT_A_FIRST", 4, **kwargs) == (
        Action.TURN_RIGHT,
        Action.TURN_RIGHT,
        Action.TURN_RIGHT,
        Action.TURN_RIGHT,
    )
    assert d033._sequence("ALTERNATE_LR", 4, **kwargs) == (
        Action.TURN_LEFT,
        Action.TURN_RIGHT,
        Action.TURN_LEFT,
        Action.TURN_RIGHT,
    )
    assert d033._sequence("ALTERNATE_RL", 4, **kwargs) == (
        Action.TURN_RIGHT,
        Action.TURN_LEFT,
        Action.TURN_RIGHT,
        Action.TURN_LEFT,
    )
    with pytest.raises(ValueError, match="unknown"):
        d033._sequence("ORACLE", 4, **kwargs)
    with pytest.raises(ValueError, match="requires the matched"):
        d033._sequence("REPEAT_A_FIRST", 4, b_proposed=Action.WAIT, a_first=None)


def test_d033_bounded_clone_runs_exactly_one_update_per_transition() -> None:
    # Historical D-030 support is deliberately used for this bounded mechanics
    # test; it does not execute or inspect the official D-033 seed block.
    result, trace, instrumentation = d033._run_capture(
        18428,
        role="B",
        horizon=20,
        target_transition=1,
        seed_validator=d030._validate_d030_seed,
    )
    capture = instrumentation.capture
    assert capture is not None
    assert result["transitions"] == len(trace) == 20
    anchor = d033._anchor_from_capture(18428, d033.D033_ANCHOR_B, capture)
    baseline = d033._run_branch(
        anchor,
        family="BASELINE_B",
        requested_length=0,
        sequence=(),
    )
    forced = d033._run_branch(
        anchor,
        family="TURN_LEFT_RUN",
        requested_length=2,
        sequence=(Action.TURN_LEFT, Action.TURN_LEFT),
    )
    assert forced.output["actual_forced_steps"] == 2
    assert forced.output["executed_action_update_count"] == 20
    assert forced.output["forced_step_executed_actions"] == [
        "TURN_LEFT",
        "TURN_LEFT",
    ]
    branch_state = cast(dict[str, object], forced.output["branch_state"])
    assert branch_state["branch_start_exact"] is True
    assert branch_state["branch_did_not_mutate_anchor"] is True
    assert branch_state["reward_zero_every_transition"] is True
    assert branch_state["organism_info_empty_every_transition"] is True
    assert branch_state["executed_action_only_updates"] is True
    assert baseline.output["branch_transition_count"] == 20


def test_d033_one_step_repeat_matches_baseline_causally() -> None:
    result, _, instrumentation = d033._run_capture(
        18428,
        role="B",
        horizon=20,
        target_transition=1,
        seed_validator=d030._validate_d030_seed,
    )
    del result
    capture = instrumentation.capture
    assert capture is not None
    anchor = d033._anchor_from_capture(18428, d033.D033_ANCHOR_B, capture)
    baseline = d033._run_branch(
        anchor,
        family="BASELINE_B",
        requested_length=0,
        sequence=(),
    )
    equivalence = d033._equivalence_regression(anchor, baseline)
    assert equivalence["passed"] is True
