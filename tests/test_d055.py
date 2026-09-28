from __future__ import annotations

import math

import numpy as np
import pytest

from aweform import d054
from aweform.d045 import (
    D045_AMBIENT_TEMPERATURE_C,
    D045_BATTERY_CAPACITY_J,
    D045_ENCODER_QUANTUM_RAD,
    D045Env,
    D045PhysicalConfig,
)
from aweform.d049 import D049_STATION_CENTER
from aweform.d050 import D050ControlMode, D050SmoothController
from aweform.d052 import D052CommandSource, D052Decision, D052Mode
from aweform.d053 import _canonicalize, run_d053_lifetime
from aweform.d054 import D054Case, _run_classified
from aweform.d055 import (
    D055_TEST_SEED,
    D055Decision,
    D055StallTurnCandidate,
    _prefix_identical,
    first_return_pair_class,
    run_d055_lifetime,
    run_matrix_case,
)


def _decision(
    index: int,
    *,
    mode: D052Mode = D052Mode.RETURN,
    source: D052CommandSource = D052CommandSource.D050_SMOOTH,
    d050: D050ControlMode = D050ControlMode.CURVED_PURSUIT,
    wheels: tuple[float, float] = (-0.4, 0.5),
    events: tuple[str, ...] = (),
) -> D052Decision:
    return D052Decision(
        index, mode, source, wheels[0], wheels[1], False, True, d050, 0, False, events
    )


class _Controller:
    def __init__(self, decisions: list[D052Decision]) -> None:
        self.decisions = iter(decisions)

    def command(self, observation: np.ndarray, proposal: object) -> D052Decision:
        return next(self.decisions)


def test_stall_turn_projects_current_command_differential() -> None:
    candidate = D055StallTurnCandidate(
        _Controller(
            [
                _decision(1, events=("RETURN_ACTIVATED",)),
                _decision(2, wheels=(-0.2, 0.6)),
            ]
        )
    )  # type: ignore[arg-type]
    observation = np.zeros(8, dtype=np.float32)
    first = candidate.command(observation, (0.0, 0.0))
    assert not first.stall_detected
    assert first.wheels == (-0.4, 0.5)
    assert candidate.prior_return_command == (-0.4, 0.5)
    second = candidate.command(observation, (0.0, 0.0))
    assert second.stall_detected and second.stall_turned
    assert second.wheels == (-0.4, 0.4)
    assert second.command_source.value == "STALL_TURN"


def test_wall_pinned_activation_pursuit_is_turned_on_second_decision() -> None:
    position, heading = (0.2, 0.0), math.radians(-20.0)
    assert all(
        (item.position, item.heading) != (position, heading)
        for item in d054.frozen_cases()
    )
    env = D045Env(D045PhysicalConfig(episode_horizon=20))
    observation, _ = env.reset(
        options={
            "body_position": position,
            "station_center": D049_STATION_CENTER,
            "heading": heading,
            "battery_j": 0.20 * D045_BATTERY_CAPACITY_J,
            "body_temperature_c": D045_AMBIENT_TEMPERATURE_C,
            "charger_termination_latched": False,
        }
    )
    candidate = D055StallTurnCandidate()
    first = candidate.command(observation, (0.0, 0.0))
    assert "RETURN_ACTIVATED" in first.events
    assert first.d050_mode is D050ControlMode.CURVED_PURSUIT
    assert not first.stall_detected
    observation, *_ = env.step(list(first.wheels))
    assert observation[6] == 0.0 and observation[7] == 0.0
    second = candidate.command(observation, (0.0, 0.0))
    assert second.stall_detected and second.stall_turned
    assert second.wheels[0] == -second.wheels[1] != 0.0
    assert candidate.first_stall_turn_transition == second.transition_index


def test_small_previous_command_does_not_trigger() -> None:
    below = D045_ENCODER_QUANTUM_RAD - 1e-12
    candidate = D055StallTurnCandidate(
        _Controller([_decision(1, wheels=(-below, 0.0)), _decision(2)])
    )  # type: ignore[arg-type]
    observation = np.zeros(8, dtype=np.float32)
    candidate.command(observation, (0.0, 0.0))
    second = candidate.command(observation, (0.0, 0.0))
    assert not second.stall_detected
    assert not second.stall_turned


def test_stall_detected_but_non_pursuit_decision_is_not_changed() -> None:
    candidate = D055StallTurnCandidate(
        _Controller(
            [
                _decision(1),
                _decision(
                    2,
                    source=D052CommandSource.RETURN_HOLD,
                    d050=D050ControlMode.CURVED_PURSUIT,
                    wheels=(0.0, 0.0),
                ),
            ]
        )
    )  # type: ignore[arg-type]
    observation = np.zeros(8, dtype=np.float32)
    candidate.command(observation, (0.0, 0.0))
    result = candidate.command(observation, (0.0, 0.0))
    assert result.stall_detected
    assert not result.stall_turned
    assert result.wheels == (0.0, 0.0)
    assert candidate.stall_detected_non_pursuit_count == 1


def test_normal_decision_clears_prior_return_register() -> None:
    normal = _decision(
        2, mode=D052Mode.NORMAL, source=D052CommandSource.PASS_THROUGH, d050=None
    )
    candidate = D055StallTurnCandidate(
        _Controller([_decision(1), normal, _decision(3)])
    )  # type: ignore[arg-type]
    observation = np.zeros(8, dtype=np.float32)
    candidate.command(observation, (0.0, 0.0))
    candidate.command(observation, (0.0, 0.0))
    assert candidate.prior_return_command is None
    assert not candidate.command(observation, (0.0, 0.0)).stall_detected


def test_nonzero_wheel_delta_prevents_detection() -> None:
    candidate = D055StallTurnCandidate(_Controller([_decision(1), _decision(2)]))  # type: ignore[arg-type]
    observation = np.zeros(8, dtype=np.float32)
    candidate.command(observation, (0.0, 0.0))
    observation[6] = D045_ENCODER_QUANTUM_RAD
    assert not candidate.command(observation, (0.0, 0.0)).stall_detected


def test_first_return_pair_classes_cover_all_five_outcomes() -> None:
    assert first_return_pair_class(None, None) == "NO_RETURN"
    assert first_return_pair_class(True, True) == "BOTH_DOCK"
    assert first_return_pair_class(False, True) == "U_ONLY_FAIL"
    assert first_return_pair_class(True, False) == "C_ONLY_FAIL"
    assert first_return_pair_class(False, False) == "BOTH_FAIL"


def test_prefix_identity_detects_synthetic_divergence() -> None:
    reference = [(0, "same"), (1, "same"), (2, "baseline")]
    matching_prefix = [(0, "same"), (1, "same"), (2, "candidate")]
    diverged_prefix = [(0, "same"), (1, "different"), (2, "candidate")]
    assert _prefix_identical(reference, matching_prefix, stop_before=3)
    assert not _prefix_identical(reference, diverged_prefix, stop_before=3)


def test_part_a_runner_matches_d054_docked_constructed_state() -> None:
    case = D054Case("test-center", 0.0, "inset", (0.5, 0.5), 0.0)
    actual = run_matrix_case(case, candidate=False, horizon=20)
    reference = _run_classified(
        case.case_id,
        case.position,
        case.heading,
        0.20 * 5328.0,
        23.0,
        D050SmoothController(),
        case.inset,
        case.boundary_class,
        20,
    )
    assert actual["outcome"] == reference["outcome"] == "DOCKED"
    for field in (
        "case_id",
        "inset_m",
        "boundary_class",
        "outcome",
        "outcome_transition",
        "first_boundary_scaled_transition",
        "boundary_scaled_transition_count",
        "minimum_boundary_scale",
        "path_length_m",
        "actuator_energy_j",
        "final_position",
        "final_heading",
    ):
        assert _canonicalize(actual[field]) == _canonicalize(reference[field])


def test_test_seed_runner_matches_unchanged_runner_prefix() -> None:
    baseline = run_d053_lifetime(22570, horizon=5000, initial_battery_fraction=0.21)
    candidate = run_d055_lifetime(22570, horizon=5000, initial_battery_fraction=0.21)
    assert baseline.trace == candidate.trace
    additive = {
        "stall_turn_count",
        "stall_detected_count",
        "first_stall_turn_transition",
        "stall_counts_by_cycle",
    }
    summary = {
        key: value for key, value in candidate.summary.items() if key not in additive
    }
    summary["command_source_counts"] = {
        key: value
        for key, value in summary["command_source_counts"].items()
        if key != "STALL_TURN"
    }
    assert _canonicalize(summary) == _canonicalize(baseline.summary)


class _ScriptedCandidate:
    def __init__(self, script: list[tuple[D052Decision, bool]]) -> None:
        self.script = iter(script)
        self.mode = D052Mode.NORMAL
        self.preemption_transition_count = 0
        self.stall_detected_count = 0
        self.stall_turn_count = 0
        self.first_stall_turn_transition: int | None = None

    def command(self, observation: np.ndarray, proposal: object) -> D055Decision:
        decision, detected = next(self.script)
        self.mode = decision.active_mode
        self.preemption_transition_count += int(decision.preempted)
        self.stall_detected_count += int(detected)
        return D055Decision(
            decision,
            decision.command_source,
            (decision.wheel_delta_left, decision.wheel_delta_right),
            detected,
            False,
        )


def test_lifetime_attributes_stall_detections_to_cycles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def hold(index: int, *events: str) -> D052Decision:
        return _decision(
            index,
            source=D052CommandSource.RETURN_HOLD,
            wheels=(0.0, 0.0),
            events=events,
        )

    def charge(index: int, *events: str) -> D052Decision:
        return D052Decision(
            index,
            D052Mode.CHARGE,
            D052CommandSource.CHARGE_HOLD,
            0.0,
            0.0,
            False,
            True,
            None,
            0,
            False,
            events,
        )

    script = [
        (hold(1, "RETURN_ACTIVATED"), False),
        (hold(2), True),
        (charge(3, "RECOVERY_YIELD"), False),
        (hold(4, "RETURN_ACTIVATED"), False),
        (hold(5), True),
        (charge(6), True),
    ]
    monkeypatch.setattr(
        "aweform.d055.D055StallTurnCandidate", lambda: _ScriptedCandidate(script)
    )
    lifetime = run_d055_lifetime(
        D055_TEST_SEED, horizon=len(script), initial_battery_fraction=0.21
    )
    assert lifetime.summary["stall_detected_count"] == 3
    assert lifetime.summary["stall_counts_by_cycle"] == [
        {"cycle_index": 1, "stall_turn_count": 0, "stall_detected_count": 1},
        {"cycle_index": 2, "stall_turn_count": 0, "stall_detected_count": 2},
    ]
