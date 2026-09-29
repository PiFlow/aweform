from __future__ import annotations

import math
import subprocess
from pathlib import Path

import pytest

from aweform import d053, d054, d055, d057
from aweform.d045 import D045_BATTERY_CAPACITY_J

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


def test_test_only_lifetime_runs_at_guarded_horizon() -> None:
    d057.validate_test_run(22620, 20, 0.2)
    result = d053.run_d053_lifetime(22620, horizon=20, initial_battery_fraction=0.2)
    assert result.seed == 22620 and len(result.trace) <= 21


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
