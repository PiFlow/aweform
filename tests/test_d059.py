from __future__ import annotations

import math
import subprocess
from pathlib import Path
from typing import cast

import pytest

from aweform import d059


def test_seed_contract_and_bounded_test_guard() -> None:
    assert d059.PRIMARY_SEEDS == tuple(range(23000, 23320))
    assert d059.ENDURANCE_SEEDS == tuple(range(23000, 23060))
    assert d059.PRIMARY_ONLY_SEEDS == tuple(range(23060, 23320))
    assert d059.TEST_SEED == 23320
    assert d059.SUPPORT_SEEDS == (22053, 22054, 22055, 22056, 22057)
    d059.validate_test_run(23320, 5000, 0.21)
    with pytest.raises(ValueError):
        d059.validate_test_run(23000, 100, 0.21)
    with pytest.raises(ValueError):
        d059.validate_test_run(23320, 5001, 0.21)
    with pytest.raises(ValueError):
        d059.validate_test_run(23320, 100, 0.22)


def test_part_a_cardinality_legality_and_order() -> None:
    for room in (3.0, 1.0):
        starts = d059.part_a_starts(room)
        assert len(starts) == 1248
        assert starts[0].start_set == "A1_wall"
        assert starts[-1].start_set == "A2_lattice"
        assert all(d059._start_is_legal(start) for start in starts)
        assert all(start.room_side_m == room for start in starts)


def test_horizon_seam_changes_only_episode_horizon() -> None:
    record = d059._horizon_seam_record()
    assert record["status"] == "PASS"
    rooms = cast(list[dict[str, object]], record["rooms"])
    for room in rooms:
        assert room["changed_fields_except_episode_horizon"] == []


def test_one_sided_cp_planning_landmarks() -> None:
    zero = d059.clopper_pearson(0, 320)
    seven = d059.clopper_pearson(7, 320)
    assert math.isclose(zero["upper"], 0.0093179794, rel_tol=0.0, abs_tol=1e-10)
    assert math.isclose(seven["lower"], 0.0103105410, rel_tol=0.0, abs_tol=1e-10)


def test_measurement_is_non_feedback_on_test_only_seed() -> None:
    measured = d059._run_lifetime(
        23320,
        substrate="S1_3M",
        arm="U",
        horizon=5000,
        primary_horizon=5000,
        classification_window=d059.W_C,
        initial_battery_fraction=0.21,
        measurement_enabled=True,
        continue_full=True,
    )
    unmeasured = d059._run_lifetime(
        23320,
        substrate="S1_3M",
        arm="U",
        horizon=5000,
        primary_horizon=5000,
        classification_window=d059.W_C,
        initial_battery_fraction=0.21,
        measurement_enabled=False,
        continue_full=True,
    )
    measured_summary = cast(dict[str, object], measured["summary"])
    assert measured_summary["total_transitions"] == 5000
    assert measured["causal_digest_sha256"] == unmeasured["causal_digest_sha256"]
    assert measured_summary["reward_exactly_zero"] is True
    assert measured_summary["organism_info_exactly_empty"] is True


def test_s1_comparator_is_dormant_on_test_only_seed() -> None:
    u = d059.run_test_lifetime(horizon=5000, initial_battery_fraction=0.21)
    c = d059._run_lifetime(
        23320,
        substrate="S1_3M",
        arm="C",
        horizon=5000,
        primary_horizon=5000,
        classification_window=d059.W_C,
        initial_battery_fraction=0.21,
    )
    assert u["causal_digest_sha256"] == c["causal_digest_sha256"]
    c_summary = cast(dict[str, object], c["summary"])
    assert c_summary["stall_detected_count"] == 0
    assert c_summary["stall_turn_count"] == 0


def test_part_a_case_uses_no_seed_and_keeps_information_boundary() -> None:
    start = d059.part_a_starts(3.0)[0]
    result = d059.run_part_a_case(start, "S1_3M", "U")
    primary = cast(dict[str, object], result["primary"])
    summary_readout = cast(dict[str, object], result["summary_readout"])
    assert primary["seed"] is None
    assert primary["classifiable"] is True
    assert summary_readout["reward_exactly_zero"] is True
    assert summary_readout["organism_info_exactly_empty"] is True


def test_wall_exposure_is_orthogonal_to_terminal_outcome() -> None:
    episode = {
        "cycle_index": 1,
        "start_transition": 1,
        "wall_exposed_any": True,
        "wall_exposed_transition_count": 1,
        "final_contacts": [(2, ("x_min",), (0.14, 1.0))],
        "centres": [(0.14, 1.0), (0.14, 1.0)],
        "return_decision_count": 2,
        "termination_reason": None,
    }
    record = d059._measurement_record(
        episode,
        substrate="S1_3M",
        arm="U",
        seed=23320,
        role="PRIMARY",
        outcome="SPIN_EXHAUSTED",
        boundary="TERMINAL_SPIN_EXHAUSTED",
        boundary_transition=2,
    )
    assert record["failed"] is True
    assert record["wall_exposed_any"] is True
    assert record["wall_exposed_failure"] is True
    assert record["final_100_contact_anatomy"] == "STATIC"


def test_official_protocol_and_artifact_generation_are_cli_guarded() -> None:
    with pytest.raises(RuntimeError):
        d059.run_protocol(d059.BASE_SHA)
    with pytest.raises(RuntimeError):
        d059.write_artifact(Path("/tmp/d059-test.json"), d059.BASE_SHA)


def test_protected_sources_unchanged() -> None:
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["git", "diff", "--exit-code", d059.BASE_SHA, "--", *d059.D059_PROTECTED_FILES],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
