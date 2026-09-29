from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from aweform import d053, d055
from aweform.d056 import (
    D056_FRESH_SEEDS,
    D056_PROTECTED_FILES,
    D056_SUPPORT_SEEDS,
    D056_TEST_SEED,
    assert_candidate_prefix,
    assert_horizon_prefix,
    classify_episode,
    pair_episodes,
    run_test_lifetime,
    validate_fresh_seeds,
    validate_support_seeds,
)

BASE = "1a9dee3321842230b5f5aa71423917ec79419918"


def _cycle(*, docked: bool = False, start: int = 1, end: int = 4) -> dict[str, object]:
    return {
        "cycle_index": 1,
        "start_transition": start,
        "end_transition": end,
        "normal_roam_length": 0,
        "return_length": end - start + 1,
        "charge_length": 0,
        "energy_at_return_activation": 0.2,
        "energy_after_first_charging_contact": 0.3 if docked else None,
        "energy_at_recovery_yield": None,
        "maximum_terminal_spin_count": 0,
        "outcome": "YIELDED" if docked else "TRUNCATED_IN_RETURN",
        "first_charging_contact_transition": start + 1 if docked else None,
    }


def _rows(
    end: int = 4, *, x: float = 0.5, exhausted: bool = False
) -> list[dict[str, object]]:
    rows = [
        {
            "transition": i,
            "x": x,
            "y": 0.5,
            "events": ["TERMINAL_SPIN_EXHAUSTED"] if exhausted and i == 2 else [],
            "terminal_spin_exhausted": exhausted and i == 2,
        }
        for i in range(end + 1)
    ]
    return rows


def test_protected_sources_unchanged() -> None:
    root = Path(__file__).resolve().parents[1]
    changed = subprocess.run(
        ["git", "diff", "--name-only", BASE, "--", *D056_PROTECTED_FILES],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert changed == []


def test_seed_guards_are_exact() -> None:
    assert validate_fresh_seeds(D056_FRESH_SEEDS) == D056_FRESH_SEEDS
    assert validate_support_seeds(D056_SUPPORT_SEEDS) == D056_SUPPORT_SEEDS
    with pytest.raises(ValueError):
        validate_fresh_seeds(D056_FRESH_SEEDS[:-1])
    with pytest.raises(ValueError):
        validate_support_seeds((22600,))


def test_episode_classifier_precedence_and_terminal_cases() -> None:
    base = classify_episode(
        _cycle(docked=True),
        _rows(),
        lifetime_truncated=True,
        lifetime_termination_reason=None,
    )
    assert base["class"] == "DOCKED"
    spin = classify_episode(
        _cycle(),
        _rows(exhausted=True),
        lifetime_truncated=True,
        lifetime_termination_reason=None,
    )
    assert spin["class"] == "SPIN_EXHAUSTED"
    wedged_rows = _rows(x=0.0)
    wedged = classify_episode(
        _cycle(), wedged_rows, lifetime_truncated=True, lifetime_termination_reason=None
    )
    assert wedged["class"] == "WEDGED"
    censored = classify_episode(
        _cycle(), _rows(), lifetime_truncated=True, lifetime_termination_reason=None
    )
    assert censored["class"] == "CENSORED_IN_PROGRESS"
    terminated = classify_episode(
        _cycle(end=2),
        _rows(end=2),
        lifetime_truncated=False,
        lifetime_termination_reason="ENERGY_DEPLETED",
    )
    assert terminated["class"] == "OTHER_NOT_DOCKED"
    assert terminated["termination_reason"] == "ENERGY_DEPLETED"


def test_pairing_classes_and_no_divergence() -> None:
    def ep(label: str, start: int = 1, end: int = 10) -> dict[str, object]:
        return {"start_transition": start, "end_transition": end, "class": label}

    u = [
        ep("DOCKED", 1, 10),
        ep("WEDGED", 11, 20),
        ep("DOCKED", 21, 30),
        ep("WEDGED", 31, 40),
    ]
    c = [
        ep("DOCKED", 1, 10),
        ep("DOCKED", 11, 20),
        ep("WEDGED", 21, 30),
        ep("OTHER_NOT_DOCKED", 31, 40),
    ]
    assert pair_episodes(u, c, None)["paired_class"] == "NO_DIVERGENCE"
    assert pair_episodes(u, c, 15)["paired_class"] == "U_ONLY_FAIL"
    assert pair_episodes(u, c, 25)["paired_class"] == "C_ONLY_FAIL"
    assert pair_episodes(u, c, 35)["paired_class"] == "BOTH_FAIL"
    assert (
        pair_episodes([ep("CENSORED_IN_PROGRESS", 1, 10)], [ep("DOCKED", 1, 10)], 2)[
            "paired_class"
        ]
        == "CENSORED"
    )
    assert (
        pair_episodes([ep("DOCKED", 1, 10)], [ep("DOCKED", 1, 10)], 2)["paired_class"]
        == "BOTH_DOCK"
    )


def test_horizon_prefix_on_test_only_seed() -> None:
    short = d053.run_d053_lifetime(
        D056_TEST_SEED, horizon=300, initial_battery_fraction=0.21
    )
    long = d053.run_d053_lifetime(
        D056_TEST_SEED, horizon=600, initial_battery_fraction=0.21
    )
    assert_horizon_prefix(short.trace, long.trace, 300)
    short_c = d055.run_d055_lifetime(
        D056_TEST_SEED, horizon=300, initial_battery_fraction=0.21
    )
    long_c = d055.run_d055_lifetime(
        D056_TEST_SEED, horizon=600, initial_battery_fraction=0.21
    )
    assert_horizon_prefix(short_c.trace, long_c.trace, 300)


def test_horizon_prefix_rejects_nonmetadata_mismatches() -> None:
    a = [
        {"transition": 0, "events": ["RESET"], "truncated": False},
        {"transition": 1, "events": ["TRUNCATED"], "truncated": True, "x": 0.0},
    ]
    b = [
        {"transition": 0, "events": ["RESET"], "truncated": False},
        {"transition": 1, "events": [], "truncated": False, "x": 0.0},
    ]
    assert_horizon_prefix(a, b, 1)
    for key, value in (
        ("x", 1.0),
        ("active_mode", "RETURN"),
        ("events", ["OTHER", "TRUNCATED"]),
    ):
        altered = [dict(r) for r in b]
        altered[1][key] = value
        with pytest.raises(RuntimeError):
            assert_horizon_prefix(a, altered, 1)
    altered_early = [dict(r) for r in b]
    altered_early[0]["transition"] = 99
    with pytest.raises(RuntimeError):
        assert_horizon_prefix(a, altered_early, 1)


def test_candidate_prefix_on_test_only_seed() -> None:
    u = d053.run_d053_lifetime(
        D056_TEST_SEED, horizon=5000, initial_battery_fraction=0.21
    )
    c = d055.run_d055_lifetime(
        D056_TEST_SEED, horizon=5000, initial_battery_fraction=0.21
    )
    assert_candidate_prefix(u.trace, c.trace, c.summary["first_stall_turn_transition"])
    result = run_test_lifetime(
        D056_TEST_SEED, horizon=5000, initial_battery_fraction=0.21
    )
    assert len(result) == 8
    assert result[0]["reward_exactly_zero"] is True
    assert result[0]["organism_info_exactly_empty"] is True
