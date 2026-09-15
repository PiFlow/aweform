"""Focused structural and pre-freeze tests for the D-040 harness."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from aweform import d027, d031r1, d040
from aweform.d026 import D026Mode
from aweform.env import Action


def _row(
    transition: int,
    action: Action,
    before_forward: float = 0.5,
    after_forward: float = 0.5,
    *,
    mode_before: D026Mode = D026Mode.SEEK,
    mode_after: D026Mode = D026Mode.SEEK,
    before_contact: float = 0.0,
    after_contact: float = 0.0,
) -> SimpleNamespace:
    return SimpleNamespace(
        transition_index=transition,
        action=action,
        mode_before=mode_before,
        mode_after=mode_after,
        observation_before=(0.25, 0.1, before_forward, 0.1, before_contact, 0.3),
        observation=(0.249, 0.1, after_forward, 0.1, after_contact, 0.3),
    )


def test_d040_freeze_seed_blocks_offsets_and_scope() -> None:
    assert (
        d040.D040_AUTHORITATIVE_BASE_SHA == "833beeabd0d50ad94e1c265873b1c024634c87e4"
    )
    assert d040.D040_REUSED_SEEDS == tuple(range(18468, 18488))
    assert d040.D040_HOLDOUT_SEEDS == tuple(range(18488, 18508))
    assert d040.D040_ANCHOR_OFFSETS == (
        0,
        1,
        3,
        7,
        15,
        31,
        63,
        127,
        255,
        511,
        1023,
        2047,
        4095,
        8191,
    )
    assert d040.D040_BRANCHES == ("DETRAP_OFF", "DETRAP_ON")
    assert d040.D040_FEATURE_FAMILIES == (
        "F0_S0",
        "F1_S0_H4",
        "F1_S0_H8",
        "F1_S0_H16",
        "F2_S0_D027",
        "F3_S0_h",
        "F4_CLOSURE_TIMING",
        "F5_PRIVILEGED_GEOMETRY",
    )
    with pytest.raises(ValueError, match="exactly"):
        d040._validate_reused_seeds((18468, 18469))
    with pytest.raises(ValueError, match="exactly"):
        d040._validate_holdout_seeds((18488, 18489))
    with pytest.raises(ValueError, match="outside"):
        d040._validate_seed(18467)
    with pytest.raises(ValueError, match="reserved"):
        d040._validate_seed(50001)
    with pytest.raises(ValueError, match="exact clean"):
        d040.run_d040_audit(executed_commit_sha=None)


def test_d040_trigger_reconstruction_is_visible_and_exact() -> None:
    rows = tuple(
        _row(index, Action.TURN_LEFT if index % 2 else Action.TURN_RIGHT)
        for index in range(1, 6)
    )
    selection = d040._find_d034_trigger(rows, "ALT", 4)
    assert selection is not None
    assert selection.transition == 5
    history = d040._trigger_history(selection)
    assert history["uses_only_executed_actions_and_six_channel_observations"] is True
    assert history["hidden_geometry_or_future_outcome_used"] is False

    no_progress = tuple(
        _row(index, Action.MOVE_FORWARD, 0.5, 0.4 - index * 0.01)
        for index in range(1, 6)
    )
    assert d040._find_d034_trigger(no_progress, "NO_FORWARD_PROGRESS", 4) is not None
    assert d040._find_d034_trigger(rows[:4], "ALT", 4) is None


def test_d040_trigger_requires_accepted_before_and_after_eligibility() -> None:
    contact = tuple(
        _row(
            index,
            Action.TURN_LEFT if index % 2 else Action.TURN_RIGHT,
            after_contact=1.0 if index == 4 else 0.0,
        )
        for index in range(1, 6)
    )
    # Accepted D-034 closes eligibility when contact appears after an action.
    assert d040._find_d034_trigger(contact, "ALT", 4) is None
    repeated = tuple(_row(index, Action.TURN_LEFT) for index in range(1, 6))
    assert d040._find_d034_trigger(repeated, "ALT", 4) is None
    with pytest.raises(ValueError, match="unknown"):
        d040._find_d034_trigger(repeated, "ORACLE", 4)


def test_d040_trigger_rejects_mode_or_contact_transition_rows() -> None:
    rows = tuple(
        _row(
            index,
            Action.TURN_LEFT if index % 2 else Action.TURN_RIGHT,
            mode_after=D026Mode.CHARGE if index == 4 else D026Mode.SEEK,
            after_contact=1.0 if index == 4 else 0.0,
        )
        for index in range(1, 6)
    )
    assert d040._find_d034_trigger(rows, "ALT", 4) is None
    assert d040._is_false_contact_seek(rows[3]) is False


def test_d040_d034_anchor_identity_matches_every_accepted_seed() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "development"
        / "D-034-history-triggered-detrap-recruitment-audit.json"
    )
    artifact = json.loads(path.read_text(encoding="utf-8"))
    results = []
    for seed_result in artifact["results"]:
        results.append(
            {
                "seed": seed_result["seed"],
                "anchor_grid": {
                    anchor_id: (
                        None
                        if not anchor["available"]
                        else {"transition": anchor["transition"]}
                    )
                    for anchor_id, anchor in seed_result["anchors"].items()
                },
            }
        )
    control = d040._d034_anchor_identity_control(results)
    assert control["all_per_seed_anchor_identities_exact"] is True
    results[0]["anchor_grid"]["ALT_4"]["transition"] += 1
    changed = d040._d034_anchor_identity_control(results)
    assert changed["all_per_seed_anchor_identities_exact"] is False


def test_d040_critical_path_has_no_later_audit_import_coupling() -> None:
    assert not hasattr(d040, "d031r1")
    assert not hasattr(d040, "d034")
    assert not hasattr(d040, "d036")
    assert not hasattr(d040, "d037")
    assert not hasattr(d040, "d038")
    assert not hasattr(d040, "d039")


def test_d040_explicit_null_grid_does_not_substitute_nearest_anchor() -> None:
    grid = {f"OFFSET_{offset}": None for offset in d040.D040_ANCHOR_OFFSETS}
    rendered = d040._available_anchor_grid(grid)
    assert tuple(rendered) == tuple(
        f"OFFSET_{offset}" for offset in d040.D040_ANCHOR_OFFSETS
    )
    assert all(value == {"status": "unavailable"} for value in rendered.values())


def test_d040_identity_projection_ignores_noncomparable_artifact_detail() -> None:
    base = {
        "trajectory_digest": "t",
        "executed_update_digest": "u",
        "outcome_classification": "HORIZON_CENSORED",
        "transitions": 32,
        "terminated": False,
        "truncated": True,
        "termination_reason": "horizon_truncation",
        "final_mode": "SEEK",
        "action_counts": {"WAIT": 2},
        "mode_occupancy": {"SEEK": 3},
        "mode_entry_counts": {"SEEK": 1},
        "seek_arbitration": {
            "false_contact_seek_decisions": 3,
            "stochastic_delegation_decisions": 0,
            "legacy_arbitration_draw_count": 3,
            "false_contact_seek_explorer_calls": 0,
            "decision_records": ["diagnostic-only"],
        },
        "final_policy_rng_digest": "p",
        "final_environment_rng_digest": "e",
        "final_weight_digest": "w",
    }
    other = dict(base)
    other["seek_arbitration"] = dict(base["seek_arbitration"], decision_records=[])
    assert (
        d040.compare_identity_fields(base, other)["all_identity_fields_exact"] is True
    )


def test_d040_short_independent_arm_b_identity_matches_canonical() -> None:
    canonical = d031r1._run_arm(
        18468,
        arm="LEARNED_NO_DETRAP",
        horizon=32,
        evaluator_diagnostics=True,
    )
    independent = d040.run_d040_replay(18468, horizon=32)
    identity = d040.compare_identity_fields(canonical, independent)
    assert identity["all_identity_fields_exact"] is True


def test_d040_real_anchor_checks_one_draw_zero_explorer_and_branch_isolation() -> None:
    _, _, anchors = d040._independent_arm_b(18468, capture_anchors=True)
    anchor = anchors["ALT_4"]
    assert anchor is not None
    before = anchor.state_digest
    off, _ = d040._run_branch(anchor, condition="DETRAP_OFF", horizon=64)
    arbitration = off["seek_arbitration"]
    assert arbitration["legacy_arbitration_draw_count"] == arbitration[
        "false_contact_seek_decisions"
    ]
    assert arbitration["false_contact_seek_explorer_calls"] == 0
    assert off["reward_zero_every_transition"] is True
    assert off["organism_info_empty_every_transition"] is True
    assert anchor.state_digest == before


def test_d040_oscillation_onset_is_first_action_of_completed_h16_run() -> None:
    _, _, anchors = d040._independent_arm_b(18468, capture_anchors=True)
    anchor = anchors["OSCILLATION_ONSET"]
    assert anchor is not None
    trigger = anchor.trigger
    assert trigger is not None
    assert trigger["run_start_transition"] == anchor.transition
    assert trigger["completion_transition"] - anchor.transition + 1 == 16
    assert len(trigger["completed_actions"]) == 16
    actions = [Action[name] for name in trigger["completed_actions"]]
    assert d040._strict_alternation(actions)


def test_d040_off_clone_and_branch_order_controls_are_identity_invariant() -> None:
    environment, observation_array, streams = d040._initial_environment(32, 18468)
    controller = d031r1.D031R1NoDetrapController(streams.policy)
    controller.reset()
    learner = d027.D027ActionConsequencePredictor()
    anchor = d040._capture_anchor(
        18468,
        "PRE_FREEZE",
        1,
        0,
        d040._next_visible(observation_array),
        environment,
        controller,
        streams,
        learner,
        (),
        0.0,
    )
    before = anchor.state_digest
    off_a, _ = d040._run_branch(anchor, condition="DETRAP_OFF", horizon=8)
    off_b, _ = d040._run_branch(anchor, condition="DETRAP_OFF", horizon=8)
    on_after_off, _ = d040._run_branch(anchor, condition="DETRAP_ON", horizon=8)
    on_first, _ = d040._run_branch(anchor, condition="DETRAP_ON", horizon=8)
    off_after_on, _ = d040._run_branch(anchor, condition="DETRAP_OFF", horizon=8)
    assert d040._branch_identity(off_a, off_b)["all_identity_fields_exact"] is True
    assert (
        d040._branch_identity(on_after_off, on_first)["all_identity_fields_exact"]
        is True
    )
    assert (
        d040._branch_identity(off_a, off_after_on)["all_identity_fields_exact"] is True
    )
    assert anchor.state_digest == before


def test_d040_history_variants_are_separate_and_null_until_available() -> None:
    environment, observation_array, streams = d040._initial_environment(32, 18468)
    controller = d031r1.D031R1NoDetrapController(streams.policy)
    controller.reset()
    anchor = d040._capture_anchor(
        18468,
        "EMPTY_PREFIX",
        1,
        0,
        d040._next_visible(observation_array),
        environment,
        controller,
        streams,
        d027.D027ActionConsequencePredictor(),
        (),
        0.0,
    )
    features = d040.feature_families(anchor)
    assert features["F1_S0_H4"] is None
    assert features["F1_S0_H8"] is None
    assert features["F1_S0_H16"] is None
    _, _, anchors = d040._independent_arm_b(18468, capture_anchors=True)
    anchor = anchors["OFFSET_8191"]
    assert anchor is not None
    features = d040.feature_families(anchor)
    assert len(features["F1_S0_H4"] or ()) == 46
    assert len(features["F1_S0_H8"] or ()) == 86
    assert len(features["F1_S0_H16"] or ()) == 166


def test_d040_branches_stop_at_reacquisition_and_report_d027_diagnostics() -> None:
    _, _, anchors = d040._independent_arm_b(18468, capture_anchors=True)
    anchor = anchors["ALT_4"]
    assert anchor is not None
    on, on_trace = d040._run_branch(anchor, condition="DETRAP_ON")
    if on["reacquired"]:
        assert on["transitions"] == on["reacquisition_latency"]
        summary = d040._horizon_summary(anchor, on, on_trace, 4096)
        assert summary["stop_reason"] == "reacquisition"
        assert summary["stopped_before_requested_horizon"] is True
    pair = d040._anchor_pair(anchor)
    diagnostics = pair["trajectory_distribution_diagnostics"]
    if diagnostics["status"] == "available":
        assert "d027_prediction_update_summary" in diagnostics["after_16"]["on"]


def test_d040_artifact_metadata_preserves_scope_and_provenance() -> None:
    payload = d040.build_compact_artifact(
        {"seeds": [18468], "results": []},
        {"seeds": [18488], "results": []},
        executed_commit_sha="a" * 40,
        invalidated=[{"sha": "b" * 40, "reason": "test-only invalidation"}],
    )
    assert payload["authorized_base_sha"] == d040.D040_AUTHORITATIVE_BASE_SHA
    assert payload["evaluator_only"] is True
    assert payload["organism_changes"] is False
    assert payload["reward"] == 0.0
    assert payload["info"] == {}
    assert payload["invalidated_provenance"][-1] == {
        "sha": "b" * 40,
        "reason": "test-only invalidation",
    }
    assert payload["invalidated_provenance"][0]["executable_sha"] == (
        "db2facbb29a295fd00f02e5e91371bf001ed19da"
    )
    assert payload["invalidated_provenance"][1] == {
        "executable_sha": "c9b017e63d4f4b01f32afa55efab257153d1d7bb",
        "reused_artifact_sha256": (
            "a28fa81cdd6f00665b162ead6e25dc5ad3ffd8a01924d4147406f1d228bf457f"
        ),
        "reused_artifact_size_bytes": 168_791_151,
        "holdout_artifact_sha256": (
            "2458da4a3d09f86a362a6c3910d6b3bf8dd3d3ce28ac62f77f81211e9351be41"
        ),
        "holdout_artifact_size_bytes": 336_622_010,
        "status": "invalidated_by_Sol",
        "reason": "D-040 artifact contract was not compact or independently reviewable",
        "interpret_as_valid_d040_output": False,
    }


def test_d040_compact_schema_removes_raw_records_and_readout_vectors() -> None:
    reused = {
        "seed_role": "reused_development_support",
        "seeds": [18468],
        "results": [
            {
                "seed": 18468,
                "seek_arbitration": {
                    "decision_records": [
                        {"transition": index, "action": "MOVE_FORWARD"}
                        for index in range(100)
                    ]
                },
                "anchor_grid": {
                    "ALT_4": {
                        "trigger": {
                            "completed_observations": [
                                {"transition": index} for index in range(16)
                            ]
                        }
                    }
                },
            }
        ],
        "readouts": {
            "F0_S0": {
                "forward_difference_4096": {
                    "predictions": [0.1, 0.2],
                    "actual": [0.0, 0.3],
                    "status": "fit",
                    "mae": 0.1,
                }
            }
        },
    }
    payload = d040.build_compact_artifact(
        reused,
        None,
        executed_commit_sha="a" * 40,
    )
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    assert '"decision_records":' not in encoded
    assert '"completed_observations":' not in encoded
    assert '"predictions":' not in encoded
    assert '"actual":' not in encoded
    compact_result = payload["reused_support"]["results"][0]  # type: ignore[index]
    arbitration = compact_result["seek_arbitration"]  # type: ignore[index]
    assert arbitration["decision_record_count"] == 100  # type: ignore[index]
    assert arbitration["decision_records_digest"]  # type: ignore[index]
    trigger = compact_result["anchor_grid"]["ALT_4"]["trigger"]  # type: ignore[index]
    assert trigger["completed_observation_count"] == 16  # type: ignore[index]
    assert trigger["completed_observations_digest"]  # type: ignore[index]


def test_d040_holdout_artifact_links_reused_training_without_embedding_it() -> None:
    reused = {
        "seed_role": "reused_development_support",
        "seeds": [18468],
        "results": [{"seed": 18468, "large": "reused-only"}],
        "readouts": {},
    }
    holdout = {
        "seed_role": "fresh_development_holdout",
        "seeds": [18488],
        "results": [{"seed": 18488, "large": "holdout-only"}],
        "readouts": {},
    }
    payload = d040.build_compact_artifact(
        None,
        holdout,
        executed_commit_sha="a" * 40,
        reused_support_reference=d040._reused_support_reference(reused),
    )
    assert payload["reused_support"] is None
    assert payload["fresh_holdout_support"]["seeds"] == [18488]  # type: ignore[index]
    assert payload["reused_support_reference"]["embedded"] is False  # type: ignore[index]
    assert "reused-only" not in json.dumps(payload, sort_keys=True)


def test_d040_runner_arbitration_uses_digest_not_decision_records() -> None:
    result, _, _ = d040._independent_arm_b(
        18468, horizon=32, capture_anchors=False
    )
    arbitration = result["seek_arbitration"]
    assert "decision_records" not in arbitration  # type: ignore[operator]
    assert arbitration["decision_record_count"] == arbitration[  # type: ignore[index]
        "false_contact_seek_decisions"
    ]


def test_d040_holdout_run_does_not_embed_reused_support(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_seed_audit(seed: int, *, horizon: int) -> dict[str, object]:
        return {"seed": seed, "horizon": horizon}

    monkeypatch.setattr(d040, "_seed_audit", fake_seed_audit)
    monkeypatch.setattr(
        d040,
        "_arm_identity_gate",
        lambda results: {"all_seeds_exact": len(results) == 40},
    )
    monkeypatch.setattr(
        d040,
        "_d034_control",
        lambda results: {"passed": len(results) == 20},
    )
    monkeypatch.setattr(
        d040,
        "_d034_anchor_identity_control",
        lambda results: {"all_per_seed_anchor_identities_exact": True},
    )
    monkeypatch.setattr(
        d040,
        "_readout",
        lambda *args, **kwargs: {"fixed": True},
    )
    payload = d040.run_d040_audit(
        seeds=d040.D040_REUSED_SEEDS,
        holdout_seeds=d040.D040_HOLDOUT_SEEDS,
        executed_commit_sha="a" * 40,
        support="holdout",
    )
    assert payload["reused_support"] is None
    assert payload["fresh_holdout_support"]["seeds"] == list(  # type: ignore[index]
        d040.D040_HOLDOUT_SEEDS
    )
    assert payload["reused_support_reference"]["embedded"] is False  # type: ignore[index]
