from __future__ import annotations

import hashlib
import io
import json
import subprocess
import tarfile
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from aweform import d059  # type: ignore[import-untyped]
from aweform.d050 import D050ControlMode  # type: ignore[import-untyped]
from aweform.d052 import (  # type: ignore[import-untyped]
    D052CommandSource,
    D052Decision,
    D052Mode,
)
from aweform.d058 import D058Env  # type: ignore[import-untyped]

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
    assert manifest["execution_status"] == "NOT_EXECUTED_BOUNDED_REPAIR_CANDIDATE"
    assert manifest["candidate_status"] == "RAW_B_NOT_CONFORMANT_NOT_PASS"
    assert manifest["repair_base_sha"] == d059.REPAIR_BASE_SHA
    assert manifest["repair_ruling_comment"] == "5943123218"
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


def test_exact_mcnemar_uses_production_mapping_and_retains_censors() -> None:
    assert d059.exact_mcnemar_two_sided(0, 0) == 1.0
    left_failure = d059._common_outcome("SPIN_EXHAUSTED")
    right_success = d059._common_outcome("DOCKED")
    assert left_failure == "FAIL"
    pairs = [
        {"seed": 26000 + i, "left": left_failure, "right": right_success}
        for i in range(5)
    ]
    contrast = d059._matched_contrast(pairs, "left", "right")
    mcnemar = cast(dict[str, object], contrast["exact_two_sided_mcnemar"])
    assert mcnemar["left_only_failure"] == 5
    assert mcnemar["right_only_failure"] == 0
    assert mcnemar["p_value"] == pytest.approx(0.0625)
    assert contrast["failed_not_failed_crosstab"] == {"FAIL x NOT_FAIL": 5}

    reverse = [
        {"seed": 26000 + i, "left": right_success, "right": left_failure}
        for i in range(5)
    ]
    reverse_mcnemar = cast(
        dict[str, object],
        d059._matched_contrast(reverse, "left", "right")["exact_two_sided_mcnemar"],
    )
    assert reverse_mcnemar["left_only_failure"] == 0
    assert reverse_mcnemar["right_only_failure"] == 5
    assert reverse_mcnemar["p_value"] == pytest.approx(0.0625)

    censored = [
        {"seed": 26000, "left": "CENSORED", "right": "FAIL"},
        {"seed": 26001, "left": "CENSORED", "right": "DOCKED"},
    ]
    censored_result = d059._matched_contrast(censored, "left", "right")
    censor_test = cast(dict[str, object], censored_result["exact_two_sided_mcnemar"])
    assert censor_test["comparable_pair_count"] == 0
    assert censor_test["censored_pair_count"] == 2
    assert censor_test["p_value"] == 1.0
    assert censored_result["failed_not_failed_crosstab"] == {
        "CENSORED x FAIL": 1,
        "CENSORED x NOT_FAIL": 1,
    }
    agreeing = [
        {"seed": 26002, "left": "DOCKED", "right": "DOCKED"},
        {"seed": 26003, "left": "FAIL", "right": "FAIL"},
    ]
    agreeing_test = cast(
        dict[str, object],
        d059._matched_contrast(agreeing, "left", "right")["exact_two_sided_mcnemar"],
    )
    assert agreeing_test["comparable_pair_count"] == 2
    assert agreeing_test["censored_pair_count"] == 0
    assert agreeing_test["p_value"] == 1.0


def test_matched_attribution_includes_both_arms_and_terminal_censors() -> None:
    def run(outcome: str, *, terminated: bool = False) -> dict[str, object]:
        record = {
            "outcome": outcome,
            "wall_exposed_any": outcome == "SPIN_EXHAUSTED",
            "wall_exposed_any_transition_count": int(outcome == "SPIN_EXHAUSTED"),
        }
        return {
            "primary_record": record,
            "return_records": [] if outcome == "CENSORED_NO_RETURN" else [record],
            "summary": {
                "terminated": terminated,
                "termination_reason": "ENERGY_DEPLETION" if terminated else None,
            },
        }

    s1_runs: dict[tuple[int, str, str], dict[str, object]] = {}
    matched_1m: dict[tuple[int, str, str], dict[str, object]] = {}
    seeds = (26000, 26001)
    for seed in seeds:
        for arm in d059.ARMS:
            s1_runs[(seed, "S1_3M", arm)] = run(
                "DOCKED" if seed == 26000 else "CENSORED_NO_RETURN"
            )
            matched_1m[(seed, "S1_1M", arm)] = run(
                "DOCKED" if seed == 26000 else "CENSORED_NO_RETURN",
                terminated=seed == 26001,
            )
            matched_1m[(seed, "D045_1M", arm)] = run(
                "SPIN_EXHAUSTED" if seed == 26000 else "CENSORED_NO_RETURN",
                terminated=seed == 26001,
            )
    result = d059._build_matched_endurance_attribution(s1_runs, matched_1m, seeds)
    by_arm = cast(dict[str, object], result["by_arm"])
    assert set(by_arm) == {"U", "C"}
    u = cast(dict[str, object], by_arm["U"])
    first = cast(dict[str, object], u["first_return"])
    one_meter = cast(dict[str, object], first["S1_1M_vs_D045_1M"])
    seed_rows = cast(list[dict[str, object]], one_meter["by_seed"])
    assert len(seed_rows) == 2
    assert seed_rows[0]["left"] == "DOCKED"
    assert seed_rows[0]["right"] == "FAIL"
    assert seed_rows[1]["left"] == "CENSORED"
    left_detail = cast(dict[str, object], seed_rows[1]["left_detail"])
    assert left_detail["environment_termination_reason"] == "ENERGY_DEPLETION"
    lifetime = cast(dict[str, object], u["lifetime_any_failure_300000"])
    lifetime_pair = cast(dict[str, object], lifetime["S1_1M_vs_D045_1M"])
    assert cast(list[dict[str, object]], lifetime_pair["by_seed"])[1]["left"] == (
        "FAIL"
    )
    with pytest.raises(RuntimeError, match="missing seed"):
        d059._build_matched_endurance_attribution(
            {key: value for key, value in s1_runs.items() if key[2] != "C"},
            matched_1m,
            seeds,
        )


def test_exact_mcnemar_and_jobs_invariant_synthetic_aggregation() -> None:
    assert d059.exact_mcnemar_two_sided(0, 0) == 1.0
    assert d059.exact_mcnemar_two_sided(3, 0) == pytest.approx(0.25)

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


def _audit_decision(transition: int, events: tuple[str, ...]) -> D052Decision:
    return D052Decision(
        transition_index=transition,
        active_mode=D052Mode.RETURN,
        command_source=D052CommandSource.D050_SMOOTH,
        wheel_delta_left=0.1,
        wheel_delta_right=0.1,
        passed_through=False,
        preempted=True,
        d050_mode=D050ControlMode.CURVED_PURSUIT,
        terminal_spin_count=0,
        terminal_spin_exhausted=False,
        events=events,
    )


def _observe_prefix_audit(
    audit: d059._PrimaryPrefixAudit,
    transition: int,
    *,
    event: bool = False,
    wall: bool = False,
    contact: bool = False,
    active_mode: D052Mode = D052Mode.RETURN,
) -> None:
    decision = _audit_decision(transition, ("RETURN_ACTIVATED",) if event else ())
    if not event:
        decision = D052Decision(
            transition_index=transition,
            active_mode=active_mode,
            command_source=D052CommandSource.D050_SMOOTH,
            wheel_delta_left=0.1,
            wheel_delta_right=0.1,
            passed_through=False,
            preempted=True,
            d050_mode=D050ControlMode.CURVED_PURSUIT,
            terminal_spin_count=0,
            terminal_spin_exhausted=False,
            events=(),
        )
    env = SimpleNamespace(
        last_contact=SimpleNamespace(
            pushing_x_min=wall,
            pushing_x_max=False,
            pushing_y_min=False,
            pushing_y_max=False,
        )
    )
    telemetry = SimpleNamespace(
        boundary_scale=1.0,
        position_after=(1.1, 1.2),
        heading_after=0.3,
    )
    audit.observe(
        transition=transition,
        decision=decision,
        contact_after=contact,
        terminated=False,
        termination_reason=None,
        env=cast(D058Env, env),
        telemetry=telemetry,
    )


def test_primary_prefix_audit_seam_and_frozen_timeout_are_immutable() -> None:
    seam = d059._PrimaryPrefixAudit("S1_3M", 3.0, horizon=3)
    _observe_prefix_audit(seam, 1, event=True, wall=True)
    _observe_prefix_audit(seam, 2)
    _observe_prefix_audit(seam, 3)
    seam_record = seam.finish(3)
    assert seam_record["outcome"] == "CENSORED_IN_PROGRESS"
    assert seam_record["wall_exposed_any"] is True
    assert seam_record["wall_exposed_any_transition_count"] == 1
    _observe_prefix_audit(seam, 4, wall=True, contact=True)
    assert seam.finish(4) == seam_record

    timeout = d059._PrimaryPrefixAudit("S1_3M", 3.0, horizon=3000)
    for transition in range(1, d059.W_C + 1):
        _observe_prefix_audit(
            timeout,
            transition,
            event=transition == 1,
            wall=transition == 1,
        )
    timeout_record = timeout.finish(d059.W_C)
    assert timeout_record["outcome"] == "RETURN_TIMEOUT_FAILURE"
    assert timeout_record["wall_exposed_any_transition_count"] == 1
    _observe_prefix_audit(timeout, d059.W_C + 1, wall=True, contact=True)
    assert timeout.finish(d059.W_C + 1) == timeout_record

    no_return = d059._PrimaryPrefixAudit("S1_3M", 3.0, horizon=2)
    _observe_prefix_audit(no_return, 1, active_mode=D052Mode.NORMAL)
    _observe_prefix_audit(no_return, 2, active_mode=D052Mode.NORMAL)
    assert no_return.finish(2)["outcome"] == "CENSORED_NO_RETURN"


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
    assert (
        observed_summary["final_causal_state_digest_sha256"]
        == unmonitored_summary["final_causal_state_digest_sha256"]
    )
    assert (
        observed_summary["final_fixture_state_digest_sha256"]
        == unmonitored_summary["final_fixture_state_digest_sha256"]
    )
    assert observed["primary_record"] == observed["primary_prefix_record"]
    evidence = d059._assert_nonfeedback_runs(observed, unmonitored)
    assert evidence["result"] == "PASS"
    altered_summary = dict(unmonitored_summary)
    altered_summary["final_fixture_state_digest_sha256"] = "f" * 64
    with pytest.raises(RuntimeError, match="causal continuation"):
        d059._assert_nonfeedback_runs(
            observed, {**unmonitored, "summary": altered_summary}
        )

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
    assert candidate_summary["final_candidate_wrapper_state_digest_sha256"] is not None
    assert (
        candidate_summary["trajectory_digest_sha256"]
        == observed_summary["trajectory_digest_sha256"]
    )
    d059.assert_candidate_identity(observed, candidate)

    bad_trace_summary = dict(candidate_summary)
    bad_trace_summary["trajectory_digest_sha256"] = "f" * 64
    with pytest.raises(RuntimeError, match="per-decision digest"):
        d059.assert_candidate_identity(
            observed, {**candidate, "summary": bad_trace_summary}
        )
    bad_summary = dict(candidate_summary)
    bad_summary["minimum_observed_energy"] = -1.0
    with pytest.raises(RuntimeError, match="summary identity"):
        d059.assert_candidate_identity(observed, {**candidate, "summary": bad_summary})
    bad_fixture_summary = dict(candidate_summary)
    bad_fixture_summary["final_fixture_state_digest_sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="summary identity"):
        d059.assert_candidate_identity(
            observed, {**candidate, "summary": bad_fixture_summary}
        )


def test_false_prefix_snapshot_fails_bounded_production_control(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_finish = d059._PrimaryPrefixAudit.finish

    def corrupt_snapshot(
        audit: d059._PrimaryPrefixAudit, transition: int
    ) -> dict[str, object]:
        record = cast(dict[str, object], original_finish(audit, transition))
        record["classification_boundary"] = "CORRUPTED_BOUNDARY"
        return record

    monkeypatch.setattr(d059._PrimaryPrefixAudit, "finish", corrupt_snapshot)
    with pytest.raises(RuntimeError, match="independent primary-prefix"):
        d059.run_test_lifetime(
            26320,
            horizon=100,
            initial_battery_fraction=0.20,
            start=OFF_MATRIX_START,
            fixture_stream=True,
        )


def _git_commit(repository: Path, content: str, *, initialize: bool = False) -> str:
    if initialize:
        repository.mkdir(parents=True)
        subprocess.run(["git", "-C", str(repository), "init", "-q"], check=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "config",
                "user.email",
                "d059-test@example.invalid",
            ],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(repository), "config", "user.name", "D059 Test"],
            check=True,
        )
    (repository / "payload.txt").write_text(content, encoding="utf-8")
    subprocess.run(["git", "-C", str(repository), "add", "payload.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(repository), "commit", "-q", "-m", "synthetic source"],
        check=True,
    )
    commit_sha = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return commit_sha


def test_git_provenance_uses_imported_root_not_caller_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    imported_root = d059._module_root().resolve()
    decoy = tmp_path / "clean-caller-checkout"
    _git_commit(decoy, "unrelated caller tree", initialize=True)
    monkeypatch.chdir(decoy)
    reported_root = Path(d059._git_output(("rev-parse", "--show-toplevel"))).resolve()
    assert reported_root == imported_root
    with pytest.raises(RuntimeError, match="imported tree's HEAD"):
        d059.verify_clean_frozen_checkout("0" * 40)


def test_repair_base_git_archive_passes_full_provenance_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_root = d059._module_root().resolve()
    object_dir = Path(d059._git_output(("rev-parse", "--absolute-git-dir"))).resolve()
    archive_bytes = subprocess.run(
        [
            "git",
            "-C",
            str(original_root),
            "archive",
            "--format=tar",
            d059.REPAIR_BASE_SHA,
        ],
        check=True,
        capture_output=True,
    ).stdout
    extracted = tmp_path / "repair-base-source"
    extracted.mkdir()
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:") as archive:
        archive.extractall(extracted, filter="data")
    monkeypatch.setattr(d059, "_module_root", lambda: extracted)
    monkeypatch.setenv("PYTHONHASHSEED", "0")
    control = d059.verify_clean_frozen_checkout(d059.REPAIR_BASE_SHA, object_dir)
    expected_tree = subprocess.run(
        [
            "git",
            f"--git-dir={object_dir}",
            "rev-parse",
            f"{d059.REPAIR_BASE_SHA}^{{tree}}",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert control["head"] == d059.REPAIR_BASE_SHA
    assert control["source_tree_sha"] == expected_tree
    assert control["clean_checkout"] is True

    source_module = extracted / "src/aweform/d059.py"
    source_module.write_text(
        source_module.read_text(encoding="utf-8") + "# synthetic mismatch\\n",
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="frozen tree"):
        d059.verify_clean_frozen_checkout(d059.REPAIR_BASE_SHA, object_dir)


def test_fresh_git_archive_is_bound_to_external_commit_tree(tmp_path: Path) -> None:
    object_repo = tmp_path / "object-repository"
    commit_a = _git_commit(object_repo, "frozen A", initialize=True)
    archive_bytes = subprocess.run(
        ["git", "-C", str(object_repo), "archive", "--format=tar", commit_a],
        check=True,
        capture_output=True,
    ).stdout
    source_root = tmp_path / "fresh-source-archive"
    source_root.mkdir()
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:") as archive:
        archive.extractall(source_root, filter="data")

    tree_sha, file_count = d059._verify_git_tree_matches_source(
        source_root, commit_a, object_repo / ".git", archive_mode=True
    )
    expected_tree_sha = subprocess.run(
        ["git", "-C", str(object_repo), "rev-parse", f"{commit_a}^{{tree}}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert tree_sha == expected_tree_sha
    assert file_count == 1

    # A genuine but mismatched frozen commit must not certify another archive.
    commit_b = _git_commit(object_repo, "frozen B")
    with pytest.raises(RuntimeError, match="frozen tree"):
        d059._verify_git_tree_matches_source(
            source_root, commit_b, object_repo / ".git", archive_mode=True
        )

    (source_root / "payload.txt").write_text("tampered", encoding="utf-8")
    with pytest.raises(RuntimeError, match="frozen tree"):
        d059._verify_git_tree_matches_source(
            source_root, commit_a, object_repo / ".git", archive_mode=True
        )

    embedded_git = source_root / ".git"
    embedded_git.mkdir()
    with pytest.raises(RuntimeError, match="embedded .git"):
        d059._verify_git_tree_matches_source(
            source_root, commit_a, object_repo / ".git", archive_mode=True
        )


def test_test_helper_rejects_part_a_state_and_official_protocol_is_cli_only() -> None:
    with pytest.raises(RuntimeError, match="imported tree's HEAD"):
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
