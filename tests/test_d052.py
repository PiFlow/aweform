"""Focused tests for the D-052 Level-1 energetic viability arbiter."""

from __future__ import annotations

import math
from decimal import ROUND_HALF_EVEN, Decimal

import numpy as np
import pytest

from aweform.d045 import (
    D045_BATTERY_CAPACITY_J,
    D045_MAX_WHEEL_DELTA_RAD,
    D045Env,
)
from aweform.d049 import D049_TERMINAL_SPIN_MAX_STEPS
from aweform.d050 import D050ControlMode, D050Decision, D050SmoothController
from aweform.d052 import (
    D052_CASE_HORIZON,
    D052_INITIAL_SOURCE_RELATIVE_HEADING_ERRORS_RAD,
    D052_PASSTHROUGH_FIXTURE,
    D052_POSITION_BEARINGS_DEG,
    D052_RECOVERY_THRESHOLD,
    D052_RETURN_RADII_M,
    D052_RETURN_THRESHOLD,
    D052CommandSource,
    D052Controller,
    D052Mode,
    _canonicalize_artifact_floats,
    frozen_cases,
    run_d052_protocol,
)


def _observation(
    energy: float = 0.5,
    left: float = 0.8,
    forward: float = 0.85,
    right: float = 0.79,
    contact: float = 0.0,
) -> np.ndarray:
    return np.asarray(
        [energy, 0.2875, left, forward, right, contact, 0.0, 0.0],
        dtype=np.float32,
    )


def _enter_charge(controller: D052Controller) -> None:
    decision = controller.command(
        _observation(energy=D052_RETURN_THRESHOLD, contact=1.0),
        D052_PASSTHROUGH_FIXTURE,
    )
    assert decision.active_mode is D052Mode.CHARGE
    assert decision.command_source is D052CommandSource.CHARGE_HOLD


def test_normal_passes_through_legal_command_without_change() -> None:
    proposed = (0.123456789012345, -0.23456789012345)
    decision = D052Controller().command(_observation(energy=0.5), proposed)
    assert (decision.wheel_delta_left, decision.wheel_delta_right) == proposed
    assert decision.active_mode is D052Mode.NORMAL
    assert decision.command_source is D052CommandSource.PASS_THROUGH
    assert decision.passed_through
    assert not decision.preempted


def test_float32_return_threshold_preempts_on_the_first_decision() -> None:
    proposed = (D045_MAX_WHEEL_DELTA_RAD, D045_MAX_WHEEL_DELTA_RAD)
    observation = _observation(energy=D052_RETURN_THRESHOLD)
    assert float(observation[0]) == D052_RETURN_THRESHOLD
    decision = D052Controller().command(observation, proposed)
    assert decision.active_mode is D052Mode.RETURN
    assert decision.command_source is D052CommandSource.D050_SMOOTH
    assert decision.preempted
    assert not decision.passed_through
    assert (decision.wheel_delta_left, decision.wheel_delta_right) != proposed
    assert "RETURN_ACTIVATED" in decision.events


def test_return_stays_latched_when_energy_fluctuates_above_threshold() -> None:
    controller = D052Controller()
    first = controller.command(
        _observation(energy=D052_RETURN_THRESHOLD), D052_PASSTHROUGH_FIXTURE
    )
    second = controller.command(
        _observation(energy=D052_RETURN_THRESHOLD + 0.01),
        D052_PASSTHROUGH_FIXTURE,
    )
    assert first.active_mode is D052Mode.RETURN
    assert second.active_mode is D052Mode.RETURN
    assert second.command_source is D052CommandSource.D050_SMOOTH
    assert second.preempted


def test_return_delegates_to_the_injected_d050_smooth_controller() -> None:
    class SpySmoothController(D050SmoothController):
        def __init__(self) -> None:
            self.observations: list[np.ndarray] = []

        def command(self, observation: np.ndarray) -> D050Decision:
            self.observations.append(observation)
            return super().command(observation)

    observation = _observation(energy=D052_RETURN_THRESHOLD)
    delegate = SpySmoothController()
    decision = D052Controller(delegate).command(
        observation, D052_PASSTHROUGH_FIXTURE
    )
    expected = D050SmoothController().command(observation)
    assert delegate.observations == [observation]
    assert decision.d050_mode is expected.mode
    assert (decision.wheel_delta_left, decision.wheel_delta_right) == (
        expected.wheel_delta_left,
        expected.wheel_delta_right,
    )


def test_d052_does_not_change_d050_smooth_command_generation() -> None:
    observation = _observation(energy=D052_RETURN_THRESHOLD)
    before = D050SmoothController().command(observation)
    D052Controller().command(observation, D052_PASSTHROUGH_FIXTURE)
    after = D050SmoothController().command(observation)
    assert before == after


def test_contact_first_enters_charge_with_zero_wheels() -> None:
    decision = D052Controller().command(
        _observation(
            energy=0.1,
            left=math.nan,
            forward=2.0,
            right=math.nan,
            contact=1.0,
        ),
        D052_PASSTHROUGH_FIXTURE,
    )
    assert decision.active_mode is D052Mode.CHARGE
    assert decision.command_source is D052CommandSource.CHARGE_HOLD
    assert (decision.wheel_delta_left, decision.wheel_delta_right) == (0.0, 0.0)
    assert decision.d050_mode is D050ControlMode.CONTACT


def test_invalid_beacon_holds_zero_and_remains_in_return() -> None:
    controller = D052Controller()
    invalid = _observation(
        energy=D052_RETURN_THRESHOLD, left=0.0, forward=0.5, right=0.5
    )
    first = controller.command(invalid, D052_PASSTHROUGH_FIXTURE)
    second = controller.command(
        _observation(energy=0.3, left=0.0, forward=0.5, right=0.5),
        D052_PASSTHROUGH_FIXTURE,
    )
    for decision in (first, second):
        assert decision.active_mode is D052Mode.RETURN
        assert decision.command_source is D052CommandSource.D050_SMOOTH
        assert decision.d050_mode is D050ControlMode.INVALID_BEACON
        assert decision.preempted
        assert (decision.wheel_delta_left, decision.wheel_delta_right) == (0.0, 0.0)
        assert "INVALID_BEACON" in decision.events


def test_contact_loss_below_recovery_reenters_return() -> None:
    controller = D052Controller()
    _enter_charge(controller)
    decision = controller.command(
        _observation(energy=0.5, contact=0.0), D052_PASSTHROUGH_FIXTURE
    )
    assert decision.active_mode is D052Mode.RETURN
    assert decision.command_source is D052CommandSource.D050_SMOOTH
    assert "CHARGING_CONTACT_LOST" in decision.events
    assert decision.terminal_spin_count == 0


def test_charge_does_not_yield_one_float32_ulp_below_recovery() -> None:
    controller = D052Controller()
    _enter_charge(controller)
    below = float(np.nextafter(np.float32(0.80), np.float32(0.0)))
    decision = controller.command(
        _observation(energy=below, contact=1.0), D052_PASSTHROUGH_FIXTURE
    )
    assert below < D052_RECOVERY_THRESHOLD
    assert decision.active_mode is D052Mode.CHARGE
    assert decision.command_source is D052CommandSource.CHARGE_HOLD
    assert decision.preempted
    assert (decision.wheel_delta_left, decision.wheel_delta_right) == (0.0, 0.0)


def test_recovery_yields_and_passes_command_through_on_same_decision() -> None:
    controller = D052Controller()
    _enter_charge(controller)
    proposed = (0.345, -0.456)
    decision = controller.command(
        _observation(energy=D052_RECOVERY_THRESHOLD, contact=1.0), proposed
    )
    assert decision.active_mode is D052Mode.NORMAL
    assert decision.command_source is D052CommandSource.PASS_THROUGH
    assert decision.passed_through
    assert not decision.preempted
    assert "RECOVERY_YIELD" in decision.events
    assert (decision.wheel_delta_left, decision.wheel_delta_right) == proposed


def test_level_one_does_not_force_departure_while_energy_is_healthy() -> None:
    for proposed in ((0.0, 0.0), (0.15, 0.15)):
        decision = D052Controller().command(
            _observation(energy=0.9, contact=1.0), proposed
        )
        assert decision.active_mode is D052Mode.NORMAL
        assert decision.command_source is D052CommandSource.PASS_THROUGH
        assert (decision.wheel_delta_left, decision.wheel_delta_right) == proposed


def test_terminal_spin_twentieth_command_executes_before_exhaustion_latches() -> None:
    controller = D052Controller()
    centered = _observation(
        energy=D052_RETURN_THRESHOLD,
        left=0.5,
        forward=0.5,
        right=0.5,
    )
    decisions = [
        controller.command(centered, D052_PASSTHROUGH_FIXTURE)
        for _ in range(D049_TERMINAL_SPIN_MAX_STEPS)
    ]
    assert all(item.d050_mode is D050ControlMode.TERMINAL_SPIN for item in decisions)
    assert all(
        item.command_source is D052CommandSource.D050_SMOOTH for item in decisions
    )
    assert decisions[-1].terminal_spin_count == D049_TERMINAL_SPIN_MAX_STEPS
    assert not decisions[-1].terminal_spin_exhausted
    assert (decisions[-1].wheel_delta_left, decisions[-1].wheel_delta_right) == (
        -D045_MAX_WHEEL_DELTA_RAD,
        D045_MAX_WHEEL_DELTA_RAD,
    )
    exhausted = controller.command(centered, D052_PASSTHROUGH_FIXTURE)
    assert exhausted.command_source is D052CommandSource.RETURN_HOLD
    assert exhausted.active_mode is D052Mode.RETURN
    assert exhausted.terminal_spin_exhausted
    assert exhausted.events == ("TERMINAL_SPIN_EXHAUSTED",)
    assert controller.terminal_spin_exhaustion_transition == exhausted.transition_index
    assert (exhausted.wheel_delta_left, exhausted.wheel_delta_right) == (0.0, 0.0)
    held = controller.command(centered, D052_PASSTHROUGH_FIXTURE)
    assert held.command_source is D052CommandSource.RETURN_HOLD
    assert held.events == ()


def test_spin_count_resets_when_contact_loss_reenters_return() -> None:
    controller = D052Controller()
    centered = _observation(
        energy=D052_RETURN_THRESHOLD,
        left=0.5,
        forward=0.5,
        right=0.5,
    )
    for _ in range(D049_TERMINAL_SPIN_MAX_STEPS):
        controller.command(centered, D052_PASSTHROUGH_FIXTURE)
    docked = controller.command(
        _observation(energy=0.3, contact=1.0), D052_PASSTHROUGH_FIXTURE
    )
    assert docked.active_mode is D052Mode.CHARGE
    lost = controller.command(
        _observation(energy=0.3, contact=0.0, left=0.5, forward=0.5, right=0.5),
        D052_PASSTHROUGH_FIXTURE,
    )
    assert lost.active_mode is D052Mode.RETURN
    assert lost.terminal_spin_count == 1
    assert not lost.terminal_spin_exhausted
    assert "CHARGING_CONTACT_LOST" in lost.events


def test_contact_while_spin_exhaustion_is_latched_enters_charge() -> None:
    controller = D052Controller()
    centered = _observation(
        energy=D052_RETURN_THRESHOLD,
        left=0.5,
        forward=0.5,
        right=0.5,
    )
    for _ in range(D049_TERMINAL_SPIN_MAX_STEPS + 1):
        controller.command(centered, D052_PASSTHROUGH_FIXTURE)
    assert controller.terminal_spin_exhausted
    contact = controller.command(
        _observation(energy=0.2, contact=1.0), D052_PASSTHROUGH_FIXTURE
    )
    assert contact.active_mode is D052Mode.CHARGE
    assert contact.command_source is D052CommandSource.CHARGE_HOLD
    assert contact.d050_mode is D050ControlMode.CONTACT
    assert (contact.wheel_delta_left, contact.wheel_delta_right) == (0.0, 0.0)


def test_preemption_transition_counts_and_fractions_are_correct() -> None:
    controller = D052Controller()
    decisions = [
        controller.command(_observation(energy=0.5), D052_PASSTHROUGH_FIXTURE),
        controller.command(
            _observation(energy=D052_RETURN_THRESHOLD), D052_PASSTHROUGH_FIXTURE
        ),
        controller.command(
            _observation(energy=0.4, contact=1.0), D052_PASSTHROUGH_FIXTURE
        ),
        controller.command(
            _observation(energy=0.79, contact=1.0), D052_PASSTHROUGH_FIXTURE
        ),
        controller.command(
            _observation(energy=D052_RECOVERY_THRESHOLD, contact=1.0),
            D052_PASSTHROUGH_FIXTURE,
        ),
    ]
    assert controller.transition_count == len(decisions) == 5
    assert controller.preemption_transition_count == 3
    assert controller.return_transition_count == 1
    assert controller.charge_transition_count == 2
    assert sum(item.preempted for item in decisions) == 3
    assert sum(item.passed_through for item in decisions) == 2


def test_causal_decisions_are_identical_for_same_observation_and_hidden_pose() -> None:
    env_a = D045Env()
    observation_a, _ = env_a.reset(
        options={
            "body_position": (0.35, 0.5),
            "station_center": (0.5, 0.5),
            "heading": 0.0,
            "battery_j": 0.20 * D045_BATTERY_CAPACITY_J,
        }
    )
    env_b = D045Env()
    observation_b, _ = env_b.reset(
        options={
            "body_position": (0.65, 0.5),
            "station_center": (0.5, 0.5),
            "heading": math.pi,
            "battery_j": 0.20 * D045_BATTERY_CAPACITY_J,
        }
    )
    assert env_a.body is not None and env_b.body is not None
    assert env_a.body.position != env_b.body.position
    assert observation_a.tobytes() == observation_b.tobytes()
    decision_a = D052Controller().command(
        observation_a, D052_PASSTHROUGH_FIXTURE
    )
    decision_b = D052Controller().command(
        observation_b, D052_PASSTHROUGH_FIXTURE
    )
    assert decision_a == decision_b


def test_frozen_matrix_has_exact_24_support_points() -> None:
    cases = frozen_cases()
    assert len(cases) == 3 * 4 * 2 == 24
    assert {case.radius_m for case in cases} == set(D052_RETURN_RADII_M)
    assert {case.position_bearing_deg for case in cases} == set(
        D052_POSITION_BEARINGS_DEG
    )
    assert {case.source_relative_heading_error_rad for case in cases} == set(
        D052_INITIAL_SOURCE_RELATIVE_HEADING_ERRORS_RAD
    )
    assert D052_CASE_HORIZON == 25_000


def test_artifact_float_canonicalization_is_exact_and_serialization_only() -> None:
    value = 1.2345678901235
    expected = float(
        Decimal(value).quantize(Decimal("1e-12"), rounding=ROUND_HALF_EVEN)
    )
    canonical = _canonicalize_artifact_floats(
        {"value": value, "negative_zero": -0.0000000000001}
    )
    assert canonical == {"value": expected, "negative_zero": 0.0}
    with pytest.raises(ValueError, match="non-finite"):
        _canonicalize_artifact_floats(math.inf)


def test_initial_battery_energy_channel_matches_float32_threshold() -> None:
    environment = D045Env()
    observation, info = environment.reset(
        options={"battery_j": 0.20 * D045_BATTERY_CAPACITY_J}
    )
    assert info == {}
    assert float(observation[0]) == D052_RETURN_THRESHOLD


def test_frozen_characterization_is_deterministic_and_keeps_boundaries() -> None:
    first = run_d052_protocol("a" * 40)
    second = run_d052_protocol("a" * 40)
    assert first["validation"]["exact_case_count"] is True
    assert first["validation"]["first_decision_preempted_in_every_case"] is True
    assert first["validation"]["reward_exactly_zero"] is True
    assert first["validation"]["organism_info_exactly_empty"] is True
    assert (
        first["validation"]["discrete_outcome_signature_sha256"]
        == second["validation"]["discrete_outcome_signature_sha256"]
    )
    assert first["aggregate"] == second["aggregate"]
    assert len(first["cases"]) == 24
    for case in first["cases"]:
        assert case["first_decision_preempted"] is True
        assert case["reward_exactly_zero"] is True
        assert case["organism_info_exactly_empty"] is True
        assert case["total_transition_count"] <= D052_CASE_HORIZON
        assert len(case["event_samples"]) <= 64
