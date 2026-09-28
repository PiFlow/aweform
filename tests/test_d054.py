from __future__ import annotations

import math

import numpy as np
import pytest

from aweform.d045 import (
    D045_AMBIENT_TEMPERATURE_C,
    D045_BATTERY_CAPACITY_J,
    D045_MAX_WHEEL_DELTA_RAD,
)
from aweform.d049 import D049_TERMINAL_SPIN_MAX_STEPS
from aweform.d050 import (
    D050BaselineController,
    D050ControlMode,
    D050Decision,
    D050SmoothController,
)
from aweform.d052 import D052Controller
from aweform.d053 import D053Lifetime, run_d053_lifetime
from aweform.d054 import (
    D054_HEADINGS,
    D054Restore,
    _find_onset,
    _part_a,
    _part_b_restore,
    _part_b_run,
    _reset_env,
    _run_classified,
    frozen_cases,
    is_absorbing_step,
    wrapped_decision,
)

ARMS = (D050SmoothController, D050BaselineController)
CENTER = np.asarray([0.2, 0.2, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0], dtype=np.float32)
BATTERY = 0.20 * D045_BATTERY_CAPACITY_J


class ScriptedController:
    def __init__(self, mode: D050ControlMode, wheels: tuple[float, float]) -> None:
        self.mode, self.wheels = mode, wheels

    def command(self, observation: np.ndarray) -> D050Decision:
        del observation
        return D050Decision(self.mode, *self.wheels, None)


@pytest.fixture(scope="module")
def lifetime_22058() -> D053Lifetime:
    return run_d053_lifetime(22058, horizon=5000, initial_battery_fraction=0.21)


def _classified(
    controller: object,
    position: tuple[float, float],
    heading: float,
    *,
    battery_j: float = BATTERY,
    horizon: int = 1000,
) -> dict[str, object]:
    return _run_classified(
        "test",
        position,
        heading,
        battery_j,
        D045_AMBIENT_TEMPERATURE_C,
        controller,
        0.0,
        "wall",
        horizon,
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


@pytest.mark.parametrize("arm", ARMS)
def test_wrapper_contact_precedes_spin_exhaustion_and_suppresses_after_limit(
    arm: type,
) -> None:
    controller = arm()
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


@pytest.mark.parametrize("arm", ARMS)
def test_wrapper_count_is_cumulative_and_twentieth_spin_executes(arm: type) -> None:
    controller = arm()
    n = 0
    for _ in range(D049_TERMINAL_SPIN_MAX_STEPS):
        decision = wrapped_decision(controller, CENTER, n)
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


@pytest.mark.parametrize("arm", ARMS)
def test_wrapper_executes_invalid_beacon_zero_command(arm: type) -> None:
    invalid = np.asarray([0.2, 0.2, 0.5, 0.5, 0.5, 0.5, 0.0, 0.0], dtype=np.float32)
    decision = wrapped_decision(arm(), invalid, 3)
    assert decision.mode is D050ControlMode.INVALID_BEACON
    assert decision.executed and not decision.exhausted
    assert decision.wheels == (0.0, 0.0)
    assert decision.count_after == 3


def test_baseline_wrapper_ignores_d049_terminal_spin_bookkeeping() -> None:
    controller = D050BaselineController()
    delegate = controller._delegate
    n = 0
    for _ in range(D049_TERMINAL_SPIN_MAX_STEPS):
        delegate.terminal_spin_steps = 10_000
        decision = wrapped_decision(controller, CENTER, n)
        assert decision.mode is D050ControlMode.TERMINAL_SPIN
        assert decision.executed
        n = decision.count_after
    delegate.terminal_spin_steps = 0
    assert wrapped_decision(controller, CENTER, n).exhausted


def test_classified_absorbing_labels_wall_pinned_bisection_residual() -> None:
    record = _classified(D050SmoothController(), (0.3593765988002574, 5.12e-23), -1.1)
    assert record["outcome"] == "ABSORBING_ZERO_MOTION"
    diagnostic = record["diagnostic"]
    assert isinstance(diagnostic, dict)
    assert 0.0 < diagnostic["position"][1] < 1e-9
    assert diagnostic["wall_or_corner"] == "bottom_wall"
    assert diagnostic["outward_normal_component"] > 0.0
    assert diagnostic["proprioceptive_stall_visible"] is True


def test_absorbing_detector_on_constructed_wall_states() -> None:
    maximum = D045_MAX_WHEEL_DELTA_RAD
    outward = _classified(
        ScriptedController(D050ControlMode.CURVED_PURSUIT, (maximum, maximum)),
        (0.3, 0.0),
        -math.pi / 2,
    )
    assert outward["outcome"] == "ABSORBING_ZERO_MOTION"
    assert outward["outcome_transition"] == 1
    env, _ = _reset_env((0.3, 0.0), -1.1, BATTERY, D045_AMBIENT_TEMPERATURE_C, 10)
    env.step((-maximum, maximum))
    spin = env.last_transition
    assert spin is not None
    assert not is_absorbing_step(
        command=(-maximum, maximum),
        boundary_scale=spin.boundary_scale,
        before=(*spin.position_before, spin.heading_before),
        after=(*spin.position_after, spin.heading_after),
    )
    spinning = _classified(
        ScriptedController(D050ControlMode.CURVED_PURSUIT, (-maximum, maximum)),
        (0.3, 0.0),
        -1.1,
        horizon=5,
    )
    assert spinning["outcome"] == "HORIZON_CENSORED"


def test_classified_stop_rule_precedence() -> None:
    maximum = D045_MAX_WHEEL_DELTA_RAD
    forward = (maximum, maximum)
    docked = _classified(
        ScriptedController(D050ControlMode.INVALID_BEACON, forward),
        (0.48, 0.5),
        0.0,
    )
    assert docked["outcome"] == "DOCKED"
    assert docked["outcome_transition"] == 1
    absorbing = _classified(
        ScriptedController(D050ControlMode.INVALID_BEACON, forward),
        (0.3, 0.0),
        -math.pi / 2,
    )
    assert absorbing["outcome"] == "ABSORBING_ZERO_MOTION"
    exhausted = _classified(
        ScriptedController(D050ControlMode.TERMINAL_SPIN, (-maximum, maximum)),
        (0.3, 0.3),
        0.0,
    )
    assert exhausted["outcome"] == "TERMINAL_SPIN_EXHAUSTED"
    assert exhausted["diagnostic"] == {
        "terminal_spin_count": D049_TERMINAL_SPIN_MAX_STEPS,
        "suppressed_mode": "TERMINAL_SPIN",
    }
    invalid = _classified(
        ScriptedController(D050ControlMode.INVALID_BEACON, (0.0, 0.0)),
        (0.3, 0.3),
        0.0,
        battery_j=0.01,
    )
    assert invalid["outcome"] == "INVALID_BEACON"
    terminated = _classified(
        ScriptedController(D050ControlMode.CURVED_PURSUIT, (0.0, 0.0)),
        (0.3, 0.3),
        0.0,
        battery_j=0.01,
    )
    assert terminated["outcome"] == "TERMINATED_ENERGY_DEPLETION"
    censored = _classified(
        ScriptedController(D050ControlMode.CURVED_PURSUIT, (0.0, 0.0)),
        (0.3, 0.3),
        0.0,
        horizon=5,
    )
    assert censored["outcome"] == "HORIZON_CENSORED"
    assert censored["outcome_transition"] == 5


def test_part_a_identity_and_onset_on_test_only_lifetime(
    lifetime_22058: D053Lifetime,
) -> None:
    summary = lifetime_22058.summary
    part_a = _part_a(lifetime_22058, summary)
    onset = _find_onset(lifetime_22058.trace)
    assert part_a["identity_control"] == "PASS"
    assert part_a["absorbing_onset_found"] is (onset is not None)
    if onset is not None:
        assert part_a["absorbing_onset_transition"] == onset
    mismatched = {
        **summary,
        "boundary_scaled_transition_count": summary["boundary_scaled_transition_count"]
        + 1,
    }
    with pytest.raises(RuntimeError, match="identity control failed"):
        _part_a(lifetime_22058, mismatched)


def test_part_b_fidelity_and_classified_restart_on_test_only_lifetime(
    lifetime_22058: D053Lifetime,
) -> None:
    trace = lifetime_22058.trace
    activation = next(
        int(row["transition"])
        for row in trace
        if "RETURN_ACTIVATED" in row.get("events", [])
    )
    onset = _find_onset(trace)
    end = onset + 10 if onset is not None else activation + 999
    restore = _part_b_restore(trace)
    assert restore["transition"] == activation - 1
    result = _part_b_run(
        restore, D050SmoothController(), fidelity_end=end, official=trace
    )
    assert result["fidelity_matches_bitwise"] is True
    assert result["window_completed"] is True
    assert result["stopped_by"] == "FIDELITY_WINDOW_END"
    assert result["executed_transitions"] == end - restore["transition"]
    classified = _run_classified(
        "test",
        restore["position"],
        restore["heading"],
        restore["battery_j"],
        restore["temperature_c_approximate"],
        D050SmoothController(),
        0.0,
        "restored_activation_state",
    )
    if onset is not None:
        assert classified["outcome"] == "ABSORBING_ZERO_MOTION"
        assert classified["outcome_transition"] == onset - restore["transition"]


def _d052_reference(
    position: tuple[float, float], heading: float, steps: int
) -> tuple[dict[str, object], ...]:
    env, observation = _reset_env(
        position, heading, BATTERY, D045_AMBIENT_TEMPERATURE_C, steps + 1
    )
    controller = D052Controller()
    rows: list[dict[str, object]] = [
        {"transition": 0, "x": position[0], "y": position[1], "heading": heading}
    ]
    for transition in range(1, steps + 1):
        decision = controller.command(observation, (0.0, 0.0))
        observation, *_ = env.step(
            (decision.wheel_delta_left, decision.wheel_delta_right)
        )
        telemetry = env.last_transition
        assert telemetry is not None
        rows.append(
            {
                "transition": transition,
                "events": list(decision.events),
                "command_source": decision.command_source.value,
                "x": telemetry.position_after[0],
                "y": telemetry.position_after[1],
                "heading": telemetry.heading_after,
            }
        )
    return tuple(rows)


def test_part_b_fidelity_steps_charge_hold_instead_of_stopping() -> None:
    position, heading, steps = (0.53, 0.5), math.pi, 25
    official = _d052_reference(position, heading, steps)
    assert any(row.get("command_source") == "CHARGE_HOLD" for row in official[:-1])
    restore: D054Restore = {
        "transition": 0,
        "position": position,
        "heading": heading,
        "battery_j": BATTERY,
        "temperature_c_approximate": D045_AMBIENT_TEMPERATURE_C,
    }
    result = _part_b_run(
        restore, D050SmoothController(), fidelity_end=steps, official=official
    )
    assert result["fidelity_matches_bitwise"] is True
    assert result["window_completed"] is True
    assert result["executed_transitions"] == steps
    diverged = tuple(
        {**row, "heading": float(row["heading"]) + 1e-12}
        if row["transition"] == steps
        else row
        for row in official
    )
    mismatch = _part_b_run(
        restore, D050SmoothController(), fidelity_end=steps, official=diverged
    )
    assert mismatch["fidelity_matches_bitwise"] is False
    gapped = tuple(row for row in official if row["transition"] != 3)
    with pytest.raises(RuntimeError, match="missing an official trace row"):
        _part_b_run(
            restore, D050SmoothController(), fidelity_end=steps, official=gapped
        )
