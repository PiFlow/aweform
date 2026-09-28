from __future__ import annotations

import math

import numpy as np

from aweform.d045 import D045_AMBIENT_TEMPERATURE_C, D045_BATTERY_CAPACITY_J
from aweform.d049 import D049_TERMINAL_SPIN_MAX_STEPS
from aweform.d050 import D050ControlMode, D050Decision, D050SmoothController
from aweform.d052 import D052Controller
from aweform.d053 import run_d053_lifetime
from aweform.d054 import (
    D054_HEADINGS,
    _find_onset,
    _part_b_restore,
    _part_b_run,
    _reset_env,
    frozen_cases,
    is_absorbing_step,
    wrapped_decision,
)


def test_frozen_boundary_matrix_geometry() -> None:
    cases = frozen_cases()
    assert len(cases) == 48 * 16 == 768
    assert len({(case.inset, case.position) for case in cases}) == 48
    assert len(D054_HEADINGS) == 16
    assert all(
        math.isclose(heading, (2 * k + 1) * math.pi / 16.0, abs_tol=0.0)
        for k, heading in enumerate(D054_HEADINGS)
    )
    assert all(0.0 <= coord <= 1.0 for case in cases for coord in case.position)
    for case in cases:
        env, observation = _reset_env(
            case.position,
            case.heading,
            0.20 * D045_BATTERY_CAPACITY_J,
            D045_AMBIENT_TEMPERATURE_C,
            1000,
        )
        assert observation[5] == 0.0
        env.close()


def test_absorbing_step_requires_nonzero_zero_scale_and_bitwise_pose() -> None:
    pose = (0.0, 0.4, 0.2)
    assert is_absorbing_step(
        command=(-0.2, 0.4), boundary_scale=0.0, before=pose, after=pose
    )
    assert not is_absorbing_step(
        command=(-0.2, 0.4), boundary_scale=0.0, before=pose, after=(0.0, 0.4, 0.3)
    )
    assert not is_absorbing_step(
        command=(-0.2, 0.4), boundary_scale=0.1, before=pose, after=pose
    )
    assert not is_absorbing_step(
        command=(0.0, 0.0), boundary_scale=0.0, before=pose, after=pose
    )


def test_wrapper_contact_precedes_spin_exhaustion_and_suppresses_after_limit() -> None:
    controller = D050SmoothController()
    contact_obs = np.asarray([0.2, 0.2, 0.5, 0.5, 0.5, 1.0, 0.0, 0.0], dtype=np.float32)
    contact = wrapped_decision(controller, contact_obs, D049_TERMINAL_SPIN_MAX_STEPS)
    assert contact.mode is D050ControlMode.CONTACT
    assert not contact.executed and not contact.exhausted
    aligned_center = np.asarray(
        [0.2, 0.2, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0], dtype=np.float32
    )
    suppressed = wrapped_decision(
        controller, aligned_center, D049_TERMINAL_SPIN_MAX_STEPS
    )
    assert suppressed.exhausted and not suppressed.executed
    assert suppressed.count_after == D049_TERMINAL_SPIN_MAX_STEPS


def test_wrapper_count_is_cumulative_and_twentieth_spin_executes() -> None:
    controller = D050SmoothController()
    center = np.asarray([0.2, 0.2, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0], dtype=np.float32)
    n = 0
    for _ in range(D049_TERMINAL_SPIN_MAX_STEPS):
        decision = wrapped_decision(controller, center, n)
        assert decision.mode is D050ControlMode.TERMINAL_SPIN
        assert decision.executed and not decision.exhausted
        n = decision.count_after
    assert n == D049_TERMINAL_SPIN_MAX_STEPS
    normal_beacon = np.asarray(
        [0.2, 0.2, 0.8, 0.9, 0.7, 0.0, 0.0, 0.0], dtype=np.float32
    )
    suppressed = wrapped_decision(controller, normal_beacon, n)
    assert suppressed.exhausted and not suppressed.executed


def test_external_wrapper_spin_count_survives_interleaved_modes() -> None:
    class ScriptedController:
        def __init__(self) -> None:
            self.modes = iter(
                (
                    D050ControlMode.TERMINAL_SPIN,
                    D050ControlMode.CURVED_PURSUIT,
                    D050ControlMode.TERMINAL_SPIN,
                )
            )

        def command(self, observation: np.ndarray) -> D050Decision:
            del observation
            return D050Decision(next(self.modes), 0.1, 0.1, None)

    controller = ScriptedController()
    observation = np.zeros(8, dtype=np.float32)
    first = wrapped_decision(controller, observation, 0)
    interleaved = wrapped_decision(controller, observation, first.count_after)
    last = wrapped_decision(controller, observation, interleaved.count_after)
    assert first.count_after == 1
    assert interleaved.mode is D050ControlMode.CURVED_PURSUIT
    assert interleaved.count_after == 1
    assert last.count_after == 2


def test_external_wrapper_matches_d052_return_decisions() -> None:
    observations = [
        np.asarray([0.2, 0.2, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0], dtype=np.float32)
        for _ in range(22)
    ]
    external = D050SmoothController()
    d052 = D052Controller()
    n = 0
    for observation in observations:
        actual = d052.command(observation, (0.1, 0.1))
        expected = wrapped_decision(external, observation, n)
        assert actual.d050_mode is expected.mode
        if expected.executed:
            assert (
                actual.wheel_delta_left,
                actual.wheel_delta_right,
            ) == expected.wheels
            n = expected.count_after
        else:
            assert actual.wheel_delta_left == actual.wheel_delta_right == 0.0
            assert actual.terminal_spin_exhausted == expected.exhausted


def test_synthetic_onset_and_test_only_lifetime_fidelity() -> None:
    trace = (
        {
            "transition": 0,
            "active_mode": "NORMAL",
            "boundary_scale": 1.0,
            "x": 0.0,
            "y": 0.2,
            "heading": 0.3,
            "wheel_command": [0.0, 0.0],
            "events": [],
        },
        *(
            {
                "transition": index,
                "active_mode": "RETURN",
                "boundary_scale": 0.0,
                "x": 0.0,
                "y": 0.2,
                "heading": 0.3,
                "wheel_command": [-0.2, 0.4],
                "events": ["RETURN_ACTIVATED"] if index == 1 else [],
            }
            for index in range(1, 4)
        ),
    )
    assert _find_onset(trace) == 1
    lifetime = run_d053_lifetime(22058, horizon=5000, initial_battery_fraction=0.21)
    activation = next(
        int(row["transition"])
        for row in lifetime.trace
        if "RETURN_ACTIVATED" in row.get("events", [])
    )
    restore = _part_b_restore(lifetime.trace)
    result = _part_b_run(
        restore,
        D050SmoothController(),
        fidelity_end=activation + 20,
        official=lifetime.trace,
        official_start=activation,
        horizon=30,
    )
    assert result["fidelity_matches_bitwise"] is True
