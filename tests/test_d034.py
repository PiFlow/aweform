"""Focused pre-freeze tests for the D-034 evaluator-only history audit."""

from __future__ import annotations

from typing import cast

import pytest

from aweform import d030, d033, d034
from aweform.d020 import ChargePhase, D020TransitionTelemetry
from aweform.d021 import D021TransitionTrace
from aweform.d026 import D026Mode
from aweform.env import Action


def _row(
    transition: int,
    action: Action,
    before_forward: float,
    after_forward: float,
    *,
    mode_before: D026Mode = D026Mode.SEEK,
    mode_after: D026Mode = D026Mode.SEEK,
    before_contact: float = 0.0,
    after_contact: float = 0.0,
) -> D021TransitionTrace:
    observation_before = (0.25, 0.1, before_forward, 0.1, before_contact, 0.3)
    observation_after = (0.249, 0.1, after_forward, 0.1, after_contact, 0.3)
    telemetry = D020TransitionTelemetry(
        step_index=transition,
        action=action,
        position_before=(0.0, 0.0),
        position_after=(0.0, 0.0),
        heading=0.0,
        station_center=(1.0, 1.0),
        battery_before_j=1.0,
        battery_after_j=0.9,
        energy_normalized_before=0.25,
        energy_normalized_after=0.249,
        body_temperature_before_c=25.0,
        body_temperature_after_c=25.0,
        temperature_normalized_before=0.3,
        temperature_normalized_after=0.3,
        charging_contact_before=before_contact == 1.0,
        charging_contact_after=after_contact == 1.0,
        electronics_electrical_power_w=0.0,
        actuator_electrical_power_w=0.0,
        total_electrical_load_w=0.0,
        charge_phase=ChargePhase.OFF,
        requested_stored_power_w=0.0,
        actual_stored_power_w=0.0,
        charger_input_power_w=0.0,
        charging_body_heat_w=0.0,
        electronics_body_heat_w=0.0,
        actuator_body_heat_w=0.0,
        total_body_heat_w=0.0,
        environmental_exchange_power_w=0.0,
        charger_termination_latched_after=False,
        preferred_ceiling_crossed=False,
        above_preferred_ceiling=False,
        energy_nonviable=False,
        protective_shutdown=False,
        emergency_hard_shutdown=False,
        terminated=False,
        truncated=False,
        termination_reason=None,
    )
    return D021TransitionTrace(
        transition_index=transition,
        mode_before=mode_before,
        mode_after=mode_after,
        action=action,
        observation_before=observation_before,
        observation=observation_after,
        telemetry=telemetry,
        reward=0.0,
        info={},
    )


def test_d034_freeze_and_seed_guard() -> None:
    assert d034.D034_HORIZON == 70_000
    assert d034.D034_BRANCH_HORIZON == 4096
    assert d034.D034_LENGTHS == (4, 8, 16)
    assert d034.D034_TRIGGER_FAMILIES == ("ALT", "NO_FORWARD_PROGRESS")
    assert d034.D034_DEFAULT_DEVELOPMENT_SEEDS == tuple(range(18468, 18488))
    assert (
        d034._validate_d034_development_seeds(d034.D034_DEFAULT_DEVELOPMENT_SEEDS)
        == d034.D034_DEFAULT_DEVELOPMENT_SEEDS
    )
    with pytest.raises(ValueError, match="exactly"):
        d034._validate_d034_development_seeds((18468, 18469))
    with pytest.raises(ValueError, match="reserved"):
        d034._validate_d034_development_seeds((50001, 50002))
    with pytest.raises(ValueError, match="only the reused"):
        d034._validate_d034_seed(18467)
    with pytest.raises(ValueError, match="70,000"):
        d034.run_d034_audit(
            seeds=d034.D034_DEFAULT_DEVELOPMENT_SEEDS,
            horizon=1,
            executed_commit_sha="0" * 40,
        )


def test_d034_trigger_predicates_are_exact_and_preserve_unavailable_anchor() -> None:
    alternating = tuple(
        _row(
            index,
            Action.TURN_LEFT if index % 2 == 0 else Action.TURN_RIGHT,
            before_forward=0.5,
            after_forward=0.5,
        )
        for index in range(1, 6)
    )
    selected = d034._find_trigger(alternating, "ALT", 4)
    assert selected is not None
    assert selected.transition == 5
    assert (
        d034._trigger_history(selected)[
            "uses_only_executed_actions_and_six_channel_observations"
        ]
        is True
    )

    progress = tuple(
        _row(index, Action.MOVE_FORWARD, 0.5, 0.4 - index * 0.01)
        for index in range(1, 6)
    )
    no_progress = d034._find_trigger(progress, "NO_FORWARD_PROGRESS", 4)
    assert no_progress is not None
    assert no_progress.transition == 5
    unavailable = d034._find_trigger(alternating[:4], "ALT", 4)
    assert unavailable is None


def test_d034_trigger_predicates_do_not_relax_false_contact_or_alternation() -> None:
    bad_contact = tuple(
        _row(
            index,
            Action.TURN_LEFT if index % 2 == 0 else Action.TURN_RIGHT,
            0.5,
            0.5,
            after_contact=1.0 if index == 4 else 0.0,
        )
        for index in range(1, 6)
    )
    assert d034._find_trigger(bad_contact, "ALT", 4) is None
    non_alternating = tuple(
        _row(index, Action.TURN_LEFT, 0.5, 0.5) for index in range(1, 6)
    )
    assert d034._find_trigger(non_alternating, "ALT", 4) is None
    with pytest.raises(ValueError, match="unknown"):
        d034._find_trigger(non_alternating, "ORACLE", 4)


def test_d034_bounded_on_off_branch_preserves_state_and_update_contract() -> None:
    # Historical D-030 support is intentionally used before the D-034 freeze;
    # this does not execute or inspect the authorized 18468..18487 output.
    result, trace, instrumentation = d033._run_capture(
        18428,
        role="B",
        horizon=70_000,
        target_transition=24_326,
        seed_validator=d030._validate_d030_seed,
    )
    del result
    capture = instrumentation.capture
    assert capture is not None
    anchor = d033._anchor_from_capture(18428, "PRE_FREEZE", capture)
    off, off_trace = d034._run_branch(
        anchor,
        condition="DETRAP_OFF",
        full_b_trace=trace,
    )
    on, on_trace = d034._run_branch(
        anchor,
        condition="DETRAP_ON",
        full_b_trace=trace,
    )
    assert len(off_trace) == 4096
    assert 1 <= len(on_trace) <= 4096
    assert off["off_arm_b_continuation_exact"] is True
    assert off["executed_action_update_count"] == 4096
    assert on["executed_action_update_count"] == len(on_trace)
    off_state = cast(dict[str, object], off["branch_state"])
    on_state = cast(dict[str, object], on["branch_state"])
    assert off_state["branch_start_exact"] is True
    assert on_state["branch_start_exact"] is True
    assert off_state["branch_did_not_mutate_anchor"] is True
    assert on_state["branch_did_not_mutate_anchor"] is True
    assert off_state["reward_zero_every_transition"] is True
    assert on_state["organism_info_empty_every_transition"] is True
    assert off_state["no_false_contact_seek_explorer_call"] is True
    assert cast(dict[str, object], on["delegation"])["delegation_probability"] == (
        1.0 / 3.0
    )


def test_d034_requires_clean_executable_sha_for_official_output() -> None:
    with pytest.raises(ValueError, match="exact clean executable"):
        d034.run_d034_audit(
            seeds=d034.D034_DEFAULT_DEVELOPMENT_SEEDS,
            executed_commit_sha=None,
        )
