from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Sequence, cast

import pytest

from aweform import d059  # type: ignore[import-untyped]

OFF_MATRIX_START = d059.D059Start(
    case_id="constructed-off-matrix-start",
    support_set="TEST_ONLY",
    position=(0.73, 0.81),
    heading=0.3,
    boundary_class="constructed",
)


def test_seed_contract_is_exact_and_result_free() -> None:
    assert d059.validate_primary_seeds(d059.PRIMARY_SEEDS) == tuple(range(26000, 26320))
    assert d059.validate_endurance_seeds(d059.ENDURANCE_SEEDS) == tuple(
        range(26000, 26060)
    )
    assert d059.validate_primary_only_seeds(d059.PRIMARY_ONLY_SEEDS) == tuple(
        range(26060, 26320)
    )
    d059.validate_test_run(26320, 5000, 0.21)
    for seed in (23000, 24000, 26000):
        with pytest.raises(ValueError):
            d059.validate_test_run(seed, 500, 0.20)
    with pytest.raises(ValueError):
        d059.validate_test_run(26320, 5001, 0.20)
    with pytest.raises(ValueError):
        d059.validate_test_run(26320, 500, 0.22)

    manifest = d059.protocol_manifest()
    assert manifest["execution_status"] == (
        "NOT_EXECUTED_RESULT_FREE_IMPLEMENTATION_CANDIDATE"
    )
    assert manifest["selected_freeze_sha"] is None
    artifact = cast(dict[str, object], manifest["artifact"])
    provenance = cast(list[object], manifest["invalidated_and_exposed_provenance"])
    assert artifact["official_result_artifact_generated"] is False
    assert len(provenance) >= 4


def test_part_a_matrix_enumeration_is_exact_without_running_trajectories() -> None:
    three = d059.part_a_starts(3.0)
    one = d059.part_a_starts(1.0)
    assert len(three) == len(one) == 1248
    assert sum(row.support_set == "A1_WALL_CORNER" for row in three) == 768
    assert sum(row.support_set == "A2_ROOM_RANGE" for row in three) == 480
    assert sum(row.support_set == "A1_WALL_CORNER" for row in one) == 768
    assert sum(row.support_set == "A2_ROOM_RANGE" for row in one) == 480
    assert all(d059._legal_s1(row.position, row.heading, 3.0) for row in three)
    assert all(d059._legal_s1(row.position, row.heading, 1.0) for row in one)
    assert all(
        0.0 <= row.position[0] <= 1.0 and 0.0 <= row.position[1] <= 1.0 for row in one
    )
    assert len({row.case_id for row in three}) == 1248
    assert len({row.case_id for row in one}) == 1248


def test_protected_sources_are_byte_identical_to_authorized_base() -> None:
    hashes = d059.verify_protected_sources()
    assert set(hashes) == set(d059.PROTECTED)
    assert all(len(value) == 64 for value in hashes.values())


def test_local_horizon_seam_changes_no_other_physical_field() -> None:
    result = d059.verify_horizon_seams()
    assert set(result) == {"S1_1M", "S1_3M"}
    for raw_room_checks in result.values():
        room_checks = cast(list[dict[str, object]], raw_room_checks)
        assert len(room_checks) == 3
        assert all(
            row["only_differing_field"] == "episode_horizon"
            and row["d059_horizon"] in (140000, 300000, 2000)
            for row in room_checks
        )


def test_exact_clopper_pearson_and_decision_landmarks() -> None:
    low0, high0 = d059.clopper_pearson_one_sided(0, 320)
    low7, high7 = d059.clopper_pearson_one_sided(7, 320)
    assert low0 == 0.0
    assert high0 == pytest.approx(0.0093179794, abs=1e-10)
    assert low7 == pytest.approx(0.0103105410, abs=1e-10)
    assert high7 is not None
    assert d059.clopper_pearson_one_sided(0, 0) == (None, None)
    with pytest.raises(ValueError):
        d059.clopper_pearson_one_sided(cast(int, 1.5), 320)

    all_docked = [{"outcome": "DOCKED", "wall_exposed_any": False}]
    p7 = d059.decide_branches({"N3": 320, "F3": 7, "G3": 0}, all_docked, [], True)
    assert p7["P_BRANCH"] == "P_JUSTIFIED"
    p0 = d059.decide_branches({"N3": 320, "F3": 0, "G3": 0}, all_docked, [], True)
    p0_result = p0
    assert p0_result["P_BRANCH"] == "P_NOT_JUSTIFIED"
    assert p0_result["FLOOR_S1_3M"] == "SETTLED"


def test_primary_censoring_and_orthogonal_wall_exposure_decisions() -> None:
    primary = [
        {"outcome": "DOCKED", "wall_exposed_any": False},
        {"outcome": "SPIN_EXHAUSTED", "wall_exposed_any": True},
        {"outcome": "RETURN_TIMEOUT_FAILURE", "wall_exposed_any": False},
        {"outcome": "CENSORED_IN_PROGRESS", "wall_exposed_any": True},
        {"outcome": "CENSORED_NO_RETURN", "wall_exposed_any": False},
    ]
    assert d059.primary_counts(primary) == {"N3": 3, "F3": 1, "G3": 1}
    p_not_justified = d059.decide_branches(
        {"N3": 320, "F3": 0, "G3": 0},
        [{"outcome": "DOCKED", "wall_exposed_any": False}],
        [],
        True,
    )
    assert p_not_justified["P_BRANCH"] == "P_NOT_JUSTIFIED"
    assert p_not_justified["FLOOR_S1_3M"] == "SETTLED"

    wall_targeted = d059.decide_branches(
        {"N3": 320, "F3": 0, "G3": 0},
        [{"outcome": "SPIN_EXHAUSTED", "wall_exposed_any": True}],
        [],
        True,
    )
    assert wall_targeted["P_BRANCH"] == "P_UNRESOLVED"
    assert wall_targeted["FLOOR_S1_3M"] == "NOT_SETTLED"

    secondary_noncontact = d059.decide_branches(
        {"N3": 320, "F3": 0, "G3": 0},
        [{"outcome": "DOCKED", "wall_exposed_any": False}],
        [{"outcome": "RETURN_TIMEOUT_FAILURE", "wall_exposed_any": False}],
        True,
    )
    assert secondary_noncontact["P_BRANCH"] == "P_NOT_JUSTIFIED"
    assert secondary_noncontact["FLOOR_S1_3M"] == "NOT_SETTLED"

    censored_wall_is_not_a_failure = d059.decide_branches(
        {"N3": 320, "F3": 0, "G3": 0},
        [{"outcome": "CENSORED_IN_PROGRESS", "wall_exposed_any": True}],
        [],
        True,
    )
    assert censored_wall_is_not_a_failure["P_BRANCH"] == "P_NOT_JUSTIFIED"


def test_exact_mcnemar_and_jobs_invariant_synthetic_aggregation() -> None:
    assert d059.exact_mcnemar_two_sided(0, 0) == 1.0
    assert d059.exact_mcnemar_two_sided(3, 0) == pytest.approx(0.25)
    pairs = [{"seed": 26000 + i, "left": "FAIL", "right": "DOCKED"} for i in range(3)]
    contrast = d059._matched_contrast(pairs, "left", "right")
    mcnemar = cast(dict[str, object], contrast["exact_two_sided_mcnemar"])
    assert mcnemar["p_value"] == pytest.approx(0.25)
    assert contrast["failed_not_failed_crosstab"] == {"FAIL x NOT_FAIL": 3}

    rows = [
        {
            "case_id": "constructed-1",
            "support_set": "A1_WALL_CORNER",
            "substrate": substrate,
            "arm": "U",
            "outcome": outcome,
            "wall_exposed_any": exposed,
        }
        for substrate, outcome, exposed in (
            ("S1_1M", "DOCKED", False),
            ("D045_1M", "SPIN_EXHAUSTED", True),
            ("S1_3M", "DOCKED", False),
        )
    ]
    serial = d059._aggregate_part_a(rows)
    regenerated = d059._aggregate_part_a(list(reversed(rows)))
    assert serial == regenerated


def test_bounded_test_seed_stream_snapshot_nonfeedback_and_s1_identity() -> None:
    observed = d059.run_test_lifetime(
        26320,
        horizon=500,
        initial_battery_fraction=0.20,
        start=OFF_MATRIX_START,
        measure_primary=True,
        fixture_stream=True,
    )
    unmonitored = d059.run_test_lifetime(
        26320,
        horizon=500,
        initial_battery_fraction=0.20,
        start=OFF_MATRIX_START,
        measure_primary=False,
        fixture_stream=True,
    )
    observed_summary = cast(dict[str, object], observed["summary"])
    unmonitored_summary = cast(dict[str, object], unmonitored["summary"])
    assert observed_summary["fixture_decision_count"] == observed["transitions"]
    assert observed_summary["reward_exactly_zero"] is True
    assert observed_summary["organism_info_exactly_empty"] is True
    assert (
        observed_summary["trajectory_digest_sha256"]
        == unmonitored_summary["trajectory_digest_sha256"]
    )
    assert (
        observed_summary["primary_prefix_digest_sha256"]
        == unmonitored_summary["primary_prefix_digest_sha256"]
    )
    assert observed["primary_record"] == observed["primary_prefix_record"]

    candidate = d059.run_test_lifetime(
        26320,
        horizon=500,
        initial_battery_fraction=0.20,
        arm="C",
        start=OFF_MATRIX_START,
        fixture_stream=True,
    )
    candidate_summary = cast(dict[str, object], candidate["summary"])
    assert candidate_summary["stall_detected_count"] == 0
    assert (
        candidate_summary["trajectory_digest_sha256"]
        == observed_summary["trajectory_digest_sha256"]
    )


def test_fresh_archive_gate_requires_exact_external_source_sha(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unavailable_git(args: Sequence[str]) -> str:
        raise subprocess.CalledProcessError(128, ["git", *args])

    monkeypatch.setattr(d059, "_git_output", unavailable_git)
    monkeypatch.setenv("PYTHONHASHSEED", "0")
    attested = d059.verify_clean_frozen_checkout("0" * 40, "0" * 40)
    assert attested["head"] == "0" * 40
    assert attested["clean_checkout"] is True
    with pytest.raises(RuntimeError, match="archive_source_sha"):
        d059.verify_clean_frozen_checkout("0" * 40, "1" * 40)


def test_test_helper_rejects_part_a_state_and_official_protocol_is_cli_only() -> None:
    with pytest.raises(RuntimeError, match="current HEAD"):
        d059.verify_clean_frozen_checkout("0" * 40)
    official_start = d059.part_a_starts(3.0)[0]
    with pytest.raises(ValueError, match="off-matrix"):
        d059.run_test_lifetime(
            26320,
            horizon=100,
            initial_battery_fraction=0.20,
            start=official_start,
        )
    with pytest.raises(RuntimeError, match="CLI-only"):
        d059._official_protocol("0" * 40, 1, "0" * 64)


def test_result_writer_is_deterministic_for_synthetic_input(tmp_path: Path) -> None:
    payload = {
        "schema_version": "synthetic-test-only",
        "values": [1.0 / 3.0, -0.0],
        "jobs_setting_in_artifact": False,
    }
    left = d059.write_artifact(tmp_path / "left.json", payload)
    right = d059.write_artifact(tmp_path / "right.json", payload)
    assert left.read_bytes() == right.read_bytes()
    result = cast(dict[str, object], json.loads(left.read_text(encoding="utf-8")))
    integrity = cast(dict[str, object], result.pop("artifact_integrity"))
    canonical_without_integrity = (
        json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")
    assert integrity["sha256_canonical_payload_excluding_integrity_field"] == (
        hashlib.sha256(canonical_without_integrity).hexdigest()
    )
    assert integrity["canonical_payload_bytes_excluding_integrity_field"] == len(
        canonical_without_integrity
    )
