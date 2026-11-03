# ruff: noqa: E402

from __future__ import annotations

import os
import resource
import subprocess
import sys

import pytest

pytest.importorskip("pymunk")

from experiments.pymunk230_obstacles.cases import PRIMARY_CASES  # noqa: E402
from experiments.pymunk230_obstacles.run_physics import (  # noqa: E402
    MAX_AGGREGATE_ROW_BYTES,
    MAX_CASE_SUMMARY_BYTES,
    MAX_COMMAND_ENVELOPE_BYTES,
    MAX_COMPARISON_BYTES,
    MAX_RSS_BYTES,
    _aggregate_contact_states,
    _aggregate_event_runs,
    _apply_rss_limit,
    _canonical_bytes,
    _parse_cpu_time,
    _process_cpu_seconds,
    _rss_enforcement_mode,
    _rss_limit_target,
    _terminate_and_reap,
    main,
)


def test_darwin_and_elapsed_cpu_time_formats_parse_fractional_seconds() -> None:
    assert _parse_cpu_time("0:00.01") == pytest.approx(0.01)
    assert _parse_cpu_time("1:02.75") == pytest.approx(62.75)
    assert _parse_cpu_time("2:03:04.50") == pytest.approx(7384.5)
    assert _parse_cpu_time("1-02:03:04.50") == pytest.approx(93784.5)


def test_measure_mode_rejects_nonfrozen_cap_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_physics", "--measure", "--callback-cap", "1000001"],
    )
    with pytest.raises(RuntimeError, match="does not permit non-frozen cap overrides"):
        main()


def test_ps_cpu_time_parser_accepts_live_darwin_output() -> None:
    assert _process_cpu_seconds(os.getpid()) >= 0.0


def test_callback_aggregation_preserves_counts_identity_and_impulse_statistics() -> (
    None
):
    rows = [
        {
            "substep": index,
            "shape_pair": ["A1_00", "hull"],
            "contact_points": 2,
            "impulse": float(index + 1),
            "penetration_m": index / 10_000,
        }
        for index in range(3)
    ]
    rows.append(
        {
            "substep": 4,
            "shape_pair": ["A1_00", "hull"],
            "contact_points": 1,
            "impulse": 0.5,
            "penetration_m": 0.0002,
        }
    )
    runs = _aggregate_event_runs(rows)
    assert len(runs) == 2
    assert [row["shape_pair"] for row in runs] == [
        ["A1_00", "hull"],
        ["A1_00", "hull"],
    ]
    assert [row["callback_count"] for row in runs] == [3, 1]
    assert runs[0]["first_substep"] == 0 and runs[0]["last_substep"] == 2
    assert runs[0]["max_contact_points"] == 2
    assert runs[0]["max_penetration_m"] == pytest.approx(0.0002)
    assert runs[0]["impulse_sum"] == pytest.approx(6.0)
    assert runs[0]["impulse_max"] == pytest.approx(3.0)


def test_contact_state_rle_preserves_all_identity_transitions() -> None:
    states = ((), (), ("hull|A1_00",), ("hull|A1_00",), (), ("hull|A1_01",))
    assert _aggregate_contact_states(states) == [
        {"first_substep": 0, "last_substep": 1, "substep_count": 2, "identities": []},
        {
            "first_substep": 2,
            "last_substep": 3,
            "substep_count": 2,
            "identities": ["hull|A1_00"],
        },
        {"first_substep": 4, "last_substep": 4, "substep_count": 1, "identities": []},
        {
            "first_substep": 5,
            "last_substep": 5,
            "substep_count": 1,
            "identities": ["hull|A1_01"],
        },
    ]


def test_exception_cleanup_kills_and_reaps_only_owned_child() -> None:
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    _terminate_and_reap(child)
    assert child.poll() is not None


def test_synthetic_worst_case_records_fit_every_frozen_record_limit() -> None:
    """Exercise JSON byte envelopes without constructing or stepping a Space."""
    long_float = 0.12345678901234566
    object_names = [
        "wall_west",
        "wall_east",
        "wall_south",
        "wall_north",
        "A1",
        "A2",
        "A3",
        "S1",
        "S2",
        "P1",
        "P2",
    ]
    clearances = {name: long_float for name in object_names}
    case_id = max((case.case_id for case in PRIMARY_CASES), key=len)
    assert len(case_id) == 32

    aggregate_row = {
        "shape_pair": ["A3_22", "hull"],
        "first_substep": 799,
        "last_substep": 799,
        "callback_count": 800,
        "max_contact_points": 2,
        "max_penetration_m": long_float,
        "impulse_sum": long_float,
        "impulse_max": long_float,
    }
    state_row = {
        "first_substep": 799,
        "last_substep": 799,
        "substep_count": 1,
        "identities": ["A3_22|hull", "wall_west|hull"],
    }
    assert len(_canonical_bytes(aggregate_row)) <= MAX_AGGREGATE_ROW_BYTES
    assert len(_canonical_bytes(state_row)) <= MAX_AGGREGATE_ROW_BYTES

    command_envelope = {
        "index": 307,
        "request_rad": [long_float, -long_float],
        "shaft_rad": [long_float, -long_float],
        "start_m": [long_float, long_float],
        "start_yaw_rad": long_float,
        "end_m": [long_float, long_float],
        "end_yaw_rad": long_float,
        "velocity_mps": [long_float, -long_float],
        "angular_velocity_rps": long_float,
        "contact_seen": True,
        "max_penetration_m": long_float,
        "body_shaft_mismatch_m": long_float,
        "minimum_clearance_by_object_m": clearances,
        "sampling_bound_m": long_float,
        "crossed": False,
        "raw_callback_count": 800,
    }
    assert len(_canonical_bytes(command_envelope)) <= MAX_COMMAND_ENVELOPE_BYTES

    empty_command_envelope = {
        "index": 10,
        "start_m": [long_float, long_float],
        "end_m": [long_float, long_float],
        "end_yaw_rad": long_float,
        "max_penetration_m": long_float,
        "minimum_clearance_m": long_float,
        "start_clearance_by_object_m": clearances,
        "end_clearance_by_object_m": clearances,
        "sampling_bound_m": long_float,
        "crossed": False,
        "raw_callback_count": 800,
        "body_shaft_mismatch_m": long_float,
    }
    assert len(_canonical_bytes(empty_command_envelope)) <= MAX_COMMAND_ENVELOPE_BYTES

    case_summary = {
        "case_id": case_id,
        "start": [long_float, long_float, long_float],
        "start_min_clearance_m": long_float,
        "expected_contact": True,
        "expected_objects": object_names,
        "observed_objects": object_names,
        "contact_classification_pass": True,
        "reset_count": 2,
        "reset_contract_pass": True,
        "identity_pair": "constructed-wall-release-control",
        "max_penetration_m": long_float,
        "max_sampling_bound_m": long_float,
        "max_substep_path_bound_m": long_float,
        "max_body_shaft_mismatch_m": long_float,
        "crossing": False,
        "release_clearance_delta_m": long_float,
        "release_pass": True,
        "end_clearance_by_object_m": clearances,
        "minimum_clearance_by_object_m": clearances,
    }
    case_summary_bytes = len(_canonical_bytes(case_summary))
    assert 1024 < case_summary_bytes <= MAX_CASE_SUMMARY_BYTES

    empty_case_summary = {
        "case_id": "empty-room-west-wall-release",
        "west_wall_contact": True,
        "release_clearance_delta_m": long_float,
    }
    assert len(_canonical_bytes(empty_case_summary)) <= MAX_CASE_SUMMARY_BYTES

    comparison = {
        "case_id": case_id,
        "command": 307,
        "position_difference_m": long_float,
        "yaw_difference_rad": long_float,
        "clearance_difference_m": long_float,
        "contact_state_disagreement": True,
        "contact_disagreement_near_boundary": True,
        "contact_object_ids_400": object_names,
        "contact_object_ids_800": object_names,
    }
    assert len(_canonical_bytes(comparison)) <= MAX_COMPARISON_BYTES

    empty_comparison = {
        "case_id": "empty-room-west-wall-release",
        "position_difference_m": long_float,
        "yaw_difference_rad": long_float,
        "clearance_difference_m": long_float,
        "penetration_m": long_float,
        "crossed": False,
        "contact_object_ids_400": object_names,
        "contact_object_ids_800": object_names,
        "contact_state_equal": True,
    }
    assert len(_canonical_bytes(empty_comparison)) <= MAX_COMPARISON_BYTES


def test_rss_limit_target_preserves_finite_and_infinite_hard_limits() -> None:
    infinity = resource.RLIM_INFINITY
    mib = 1024 * 1024
    assert _rss_limit_target((infinity, infinity)) == (MAX_RSS_BYTES, infinity)
    assert _rss_limit_target((512 * mib, infinity)) == (MAX_RSS_BYTES, infinity)
    assert _rss_limit_target((128 * mib, 512 * mib)) == (128 * mib, 512 * mib)
    assert _rss_limit_target((64 * mib, 64 * mib)) == (64 * mib, 64 * mib)
    with pytest.raises(ValueError, match="soft limit exceeds its hard limit"):
        _rss_limit_target((512 * mib, 128 * mib))
    with pytest.raises(ValueError, match="soft limit exceeds its hard limit"):
        _rss_limit_target((infinity, 128 * mib))


@pytest.mark.parametrize(
    ("inherited", "expected"),
    [
        (
            (resource.RLIM_INFINITY, resource.RLIM_INFINITY),
            (MAX_RSS_BYTES, resource.RLIM_INFINITY),
        ),
        (
            (512 * 1024 * 1024, 1024 * 1024 * 1024),
            (MAX_RSS_BYTES, 1024 * 1024 * 1024),
        ),
        (
            (128 * 1024 * 1024, 512 * 1024 * 1024),
            (128 * 1024 * 1024, 512 * 1024 * 1024),
        ),
    ],
)
def test_apply_rss_limit_preserves_inherited_hard_limit(
    monkeypatch: pytest.MonkeyPatch,
    inherited: tuple[int, int],
    expected: tuple[int, int],
) -> None:
    current = [inherited]
    calls: list[tuple[int, int]] = []

    def set_limit(_kind: int, limits: tuple[int, int]) -> None:
        calls.append(limits)
        current[0] = limits

    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(resource, "getrlimit", lambda _kind: current[0])
    monkeypatch.setattr(resource, "setrlimit", set_limit)
    _apply_rss_limit()
    assert calls == [expected]
    assert current[0] == expected


def test_darwin_rss_mode_uses_existing_detection_without_setrlimit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(resource, "setrlimit", lambda *args: calls.append(args))
    assert _rss_enforcement_mode() == (
        "high-water checks only; Darwin rejects finite RLIMIT_RSS limits"
    )
    _apply_rss_limit()
    assert calls == []


def test_darwin_rlimit_rss_failure_and_valid_controls_in_disposable_child() -> None:
    if sys.platform != "darwin":
        pytest.skip("reproduces the Darwin-specific RLIMIT_RSS behavior")
    child = """
import resource
rss = resource.RLIMIT_RSS
cap = 256 * 1024 * 1024
for name, target in (
    ("hard-finite", (cap, cap)),
    ("soft-only", (cap, resource.RLIM_INFINITY)),
):
    inherited = resource.getrlimit(rss)
    try:
        resource.setrlimit(rss, target)
    except ValueError as error:
        print(name, inherited, target, type(error).__name__, str(error))
    else:
        raise AssertionError(f"{name} unexpectedly accepted: {resource.getrlimit(rss)}")
assert resource.getrlimit(rss) == (resource.RLIM_INFINITY, resource.RLIM_INFINITY)
resource.setrlimit(rss, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
for key, limit in (
    (resource.RLIMIT_CPU, 1200),
    (resource.RLIMIT_FSIZE, 10 * 1024 * 1024),
):
    resource.setrlimit(key, (limit, limit))
    assert resource.getrlimit(key) == (limit, limit)
print("infinity-noop and finite CPU/FSIZE controls pass")
"""
    result = subprocess.run(
        [sys.executable, "-c", child], text=True, capture_output=True, check=False
    )
    assert result.returncode == 0, result.stderr
    inherited_infinity = f"({resource.RLIM_INFINITY}, {resource.RLIM_INFINITY})"
    assert f"hard-finite {inherited_infinity}" in result.stdout
    assert f"soft-only {inherited_infinity}" in result.stdout
    assert "ValueError current limit exceeds maximum limit" in result.stdout
    assert "infinity-noop and finite CPU/FSIZE controls pass" in result.stdout
