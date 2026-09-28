from __future__ import annotations

import numpy as np

from aweform.d045 import D045_ENCODER_QUANTUM_RAD
from aweform.d050 import D050ControlMode, D050SmoothController
from aweform.d052 import D052CommandSource, D052Decision, D052Mode
from aweform.d053 import _canonicalize, run_d053_lifetime
from aweform.d054 import D054Case, _run_classified
from aweform.d055 import (
    D055StallTurnCandidate,
    _prefix_identical,
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
                _decision(2),
                _decision(3, wheels=(-0.2, 0.6)),
            ]
        )
    )  # type: ignore[arg-type]
    observation = np.zeros(8, dtype=np.float32)
    first = candidate.command(observation, (0.0, 0.0))
    assert first.wheels == (-0.4, 0.5)
    assert candidate.prior_return_command is None
    second = candidate.command(observation, (0.0, 0.0))
    assert not second.stall_detected
    third = candidate.command(observation, (0.0, 0.0))
    assert third.stall_detected and third.stall_turned
    assert third.wheels == (-0.4, 0.4)
    assert third.command_source.value == "STALL_TURN"


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
