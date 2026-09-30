from __future__ import annotations

import math
import subprocess
from pathlib import Path

import pytest

from aweform import d053, d054, d055, d057
from aweform.d045 import D045_AMBIENT_TEMPERATURE_C, D045_BATTERY_CAPACITY_J
from aweform.d052 import D052Controller

BASE = d057.BASE_SHA


def test_reductions_inside_walls_corners_and_exact_bounds() -> None:
    assert d057.reduce_r1((0.2, 0.2), (0.3, 0.3)) == (0.3, 0.3)
    assert d057.reduce_r1((0.2, 0.4), (-0.2, 0.4)) == (0.0, 0.4)
    assert d057.reduce_r1((0.2, 0.4), (1.2, 0.4)) == (1.0, 0.4)
    assert d057.reduce_r1((0.2, 0.2), (-0.2, -0.2)) == (0.0, 0.0)
    assert d057.reduce_r1((0.8, 0.8), (1.2, 1.2)) == (1.0, 1.0)
    assert d057.reduce_r1((0.3, 0.0), (0.3, 0.0)) == (0.3, 0.0)
    assert d057.reduce_r2((-1.0, 0.4)) == (0.0, 0.4)
    assert d057.reduce_r2((1.0, 0.0)) == (1.0, 0.0)


def test_r1_intersects_first_wall_and_r2_retains_tangent() -> None:
    p0, pfull = (0.8, 0.8), (1.2, 1.1)
    clipped = d057.reduce_r1(p0, pfull)
    assert clipped[0] == 1.0 and clipped[1] == pytest.approx(0.95)
    assert d057.reduce_r2(pfull) == (1.0, 1.0)


def test_constructed_prefix_identity_without_boundary_scale() -> None:
    state = ((0.4, 0.5), 0.0)
    traces = {}
    for rule in ("R0", "R1", "R2"):
        _, traces[rule] = d057._run(
            "constructed-interior",
            state[0],
            state[1],
            0.2 * D045_BATTERY_CAPACITY_J,
            23.0,
            0.1,
            "constructed",
            "U",
            rule,
            5,
            capture=True,
        )
    assert all(row["scale"] == 1.0 for row in traces["R0"])
    assert traces["R1"] == traces["R0"] == traces["R2"]


def test_replay_window_end_contact_bounded_docked_episode() -> None:
    # Branch step k replays official transition activation + k - 1, so a branch
    # that docks at contact on step 25 covers activation .. contact inclusive.
    activation = 1000
    contact = activation + 24
    end = d057._replay_window_end(activation, contact)
    assert end == contact
    assert end - activation + 1 == 25


def test_replay_window_end_horizon_bounded_wedged_episode() -> None:
    # A WEDGED episode ends ~71k transitions later; the 1,000-step branch covers
    # exactly activation .. activation + PART_B_HORIZON - 1.
    activation = 70758
    end = d057._replay_window_end(activation, activation + 71_000)
    assert end == activation + d057.PART_B_HORIZON - 1
    assert end - activation + 1 == d057.PART_B_HORIZON
    edge = activation + d057.PART_B_HORIZON - 1
    assert d057._replay_window_end(activation, edge) == edge
    assert d057._replay_window_end(activation, edge + 1) == edge


def test_official_execution_requires_cli_flag() -> None:
    with pytest.raises(RuntimeError, match="CLI-only"):
        d057._part_a()
    with pytest.raises(RuntimeError, match="CLI-only"):
        d057._part_b()
    with pytest.raises(RuntimeError, match="CLI-only"):
        d057.run_protocol("0" * 40)


def test_d055_wrapper_counts_all_decisions() -> None:
    from aweform.d055 import D055StallTurnCandidate

    env, observation = d057._reset(
        (0.5, 0.5), 0.0, 0.8 * D045_BATTERY_CAPACITY_J, 23.0, 5, "R0"
    )
    wrapper = D055StallTurnCandidate()
    wrapper.prior_return_command = (0.1, 0.1)
    emitted = wrapper.command(observation, (0.0, 0.0))
    assert emitted.stall_detected
    assert wrapper.stall_detected_count == 1
    assert wrapper.stall_turn_count == 0
    # This decision is counted even though the harness need not step it.
    assert emitted.command_source.value == "PASS_THROUGH"
    env.close()


def test_test_seed_guards() -> None:
    d057.validate_test_run(22620, 100, 0.21)
    for args in ((22600, 5, 0.2), (22620, 5001, 0.2), (22620, 2, 0.22)):
        with pytest.raises(ValueError):
            d057.validate_test_run(*args)


def test_constructed_widened_bounds_branch_and_observation() -> None:
    # Constructed non-official state; tests only the evaluator-only seam.
    env, _ = d057._reset(
        (0.0, 0.3), 0.9 * math.pi, 0.2 * D045_BATTERY_CAPACITY_J, 23.0, 5, "R1"
    )
    obs, reward, terminated, truncated, info = env.step((0.3, 0.6))
    assert reward == 0.0 and info == {} and env.last_transition is not None
    assert env.last_transition.boundary_scale == 1.0
    raw = env.body.position
    reduced = d057.reduce_r1((0.0, 0.3), raw)
    env.body.x, env.body.y = reduced
    observed = env._observation().as_array()
    assert observed.shape == (8,)
    assert env.charging_contact is False
    env.close()


def test_r0_identity_against_d055_on_one_permitted_matrix_case() -> None:
    case = d054.frozen_cases()[0]  # only R0, short horizon, one frozen case
    actual, _ = d057._run(
        case.case_id,
        case.position,
        case.heading,
        0.2 * D045_BATTERY_CAPACITY_J,
        23.0,
        case.inset,
        case.boundary_class,
        "U",
        "R0",
        20,
    )
    expected = d055.run_matrix_case(case, candidate=False, horizon=20)
    shared = set(actual) & set(expected)
    assert d057._canon({k: actual[k] for k in shared}) == d057._canon(
        {k: expected[k] for k in shared}
    )


def test_part_a_only_candidate_detection_breaks_dormancy() -> None:
    def row(part: str, arm: str, rule: str, detections: int) -> dict:
        r = {
            "arm": arm,
            "rule": rule,
            "outcome": "DOCKED",
            "WEDGED": False,
            "counterfactual_centre_reduction_count": 0,
            "outcome_transition": 10,
            "actuator_energy_j": 1.0,
        }
        if part == "A":
            r["case_id"] = "case-1"
        else:
            r["seed"], r["activation_transition"] = 22601, 100
        if arm == "C":
            r["stall_detected_count"] = detections
            r["stall_turn_count"] = detections
            r["stall_detected_non_pursuit_count"] = 0
        return r

    a = [
        row("A", arm, rule, 1 if (arm, rule) == ("C", "R1") else 0)
        for arm in d057.ARMS
        for rule in d057.RULES
    ]
    b = [row("B", arm, rule, 0) for arm in d057.ARMS for rule in d057.RULES]
    sig, agg = d057._readouts(a, b)
    assert agg["A"]["candidate_diagnostics"]["R1"]["stall_detections"] == 1
    assert agg["B"]["candidate_diagnostics"]["R1"]["stall_detections"] == 0
    assert sig["C_R1_DORMANT"] == "NO"
    assert sig["C_R2_DORMANT"] == "YES"


def test_test_only_lifetime_restoration_fidelity() -> None:
    seed, horizon, battery_fraction = 22620, 5, 0.21
    d057.validate_test_run(seed, horizon, battery_fraction)
    lifetime = d053.run_d053_lifetime(
        seed, horizon=horizon, initial_battery_fraction=battery_fraction
    )
    reset_row = lifetime.trace[0]
    env, observation = d057._reset(
        (reset_row["x"], reset_row["y"]),
        reset_row["heading"],
        battery_fraction * D045_BATTERY_CAPACITY_J,
        D045_AMBIENT_TEMPERATURE_C,
        horizon,
        "R0",
    )
    proposal = d053.D053RoamingFixture(seed).propose()
    decision = D052Controller().command(observation, proposal.wheel_command)
    wheels = (decision.wheel_delta_left, decision.wheel_delta_right)
    assert [float(v) for v in wheels] == lifetime.trace[1]["wheel_command"]
    observation, reward, terminated, truncated, info = env.step(wheels)
    telemetry = env.last_transition
    assert telemetry is not None and reward == 0.0 and info == {}
    expected = lifetime.trace[1]
    assert telemetry.position_after[0].hex() == expected["x"].hex()
    assert telemetry.position_after[1].hex() == expected["y"].hex()
    assert telemetry.heading_after.hex() == expected["heading"].hex()
    assert telemetry.battery_after_j.hex() == expected["battery_after_j"].hex()
    assert observation.shape == (8,)
    assert not terminated and not truncated
    env.close()


def test_protected_sources_unchanged() -> None:
    root = Path(__file__).resolve().parents[1]
    if (
        subprocess.run(
            ["git", "cat-file", "-e", f"{BASE}^{{commit}}"],
            cwd=root,
            capture_output=True,
        ).returncode
        != 0
    ):
        pytest.skip("authorized base commit object is unavailable")
    result = subprocess.run(
        ["git", "diff", "--exit-code", BASE, "--", *d057.PROTECTED],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
