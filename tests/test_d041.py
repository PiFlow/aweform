"""Focused D-041 geometry, control, and protocol tests."""

from __future__ import annotations

import json

import pytest

from aweform import d041
from aweform.env import Action


def test_d041_front_receptor_geometry_and_null_semantics() -> None:
    centered = d041.front_beacon_receptors((0.45, 0.50), 0.0, (0.55, 0.50))
    assert centered.left == pytest.approx(centered.right)
    assert centered.left > 0.0

    behind = d041.front_beacon_receptors((0.55, 0.50), 0.0, (0.50, 0.50))
    assert behind == d041.ReceptorPair(0.0, 0.0)

    out_of_range = d041.front_beacon_receptors((0.0, 0.5), 0.0, (1.0, 0.5))
    assert out_of_range == d041.ReceptorPair(0.0, 0.0)


def test_d041_left_right_mirror_swaps_receptors() -> None:
    left = d041.front_beacon_receptors((0.45, 0.48), 0.0, (0.50, 0.50))
    mirrored = d041.front_beacon_receptors((0.45, 0.52), 0.0, (0.50, 0.50))
    assert left.left == pytest.approx(mirrored.right)
    assert left.right == pytest.approx(mirrored.left)


def test_d041_pair_readout_has_only_declared_signal_semantics() -> None:
    assert d041.receptor_readout(d041.ReceptorPair(0.8, 0.2)) is Action.TURN_LEFT
    assert d041.receptor_readout(d041.ReceptorPair(0.2, 0.8)) is Action.TURN_RIGHT
    assert d041.receptor_readout(d041.ReceptorPair(0.4, 0.4)) is Action.MOVE_FORWARD
    assert d041.receptor_readout(d041.ReceptorPair(0.0, 0.0)) is Action.WAIT
    assert (
        d041.receptor_readout(d041.ReceptorPair(0.8, 0.2), condition="SWAP")
        is Action.TURN_RIGHT
    )
    assert d041.receptor_readout(
        d041.ReceptorPair(0.8, 0.2), condition="NULL"
    ) is Action.WAIT
    assert d041.receptor_readout(
        d041.ReceptorPair(0.8, 0.2), condition="OUT_OF_RANGE"
    ) is Action.WAIT
    with pytest.raises(ValueError, match="within"):
        d041.receptor_readout(d041.ReceptorPair(1.1, 0.0))


def test_d041_protocol_freezes_authority_seeds_and_no_history() -> None:
    assert d041.D041_AUTHORITATIVE_BASE_SHA == (
        "8b51d6e143a906a83f1fd8d760aace5ed46abb9e"
    )
    assert d041.D041_REUSED_SEEDS == tuple(range(18468, 18488))
    assert d041.D041_HOLDOUT_SEEDS == tuple(range(18488, 18508))
    assert d041.D041_HORIZON == 70_000
    assert d041.D041_ANCHOR_REPLAY_HORIZON == d041.D041_HORIZON
    assert d041.D041_BRANCH_HORIZON == 4096
    assert d041.D041_ANCHOR_IDS == (
        "OFFSET_0",
        "OFFSET_15",
        "OFFSET_63",
        "OFFSET_255",
        "OFFSET_1023",
        "OFFSET_4095",
        "ALT_16",
        "NO_FORWARD_PROGRESS_16",
    )
    with pytest.raises(ValueError, match="exactly"):
        d041._validate_seed_block((18468,), d041.D041_REUSED_SEEDS, "reused")
    with pytest.raises(ValueError, match="reserved"):
        d041._validate_seed(50001, holdout=False)
    with pytest.raises(ValueError, match="exact clean"):
        d041.run_d041_audit(executed_commit_sha=None)


def test_d041_capture_filter_preserves_anchor_contract() -> None:
    _, _, anchors = d041.d040._independent_arm_b(
        18468,
        horizon=1,
        capture_anchor_ids=d041.D041_ANCHOR_IDS,
    )
    assert tuple(anchors) == (
        *(f"OFFSET_{offset}" for offset in d041.d040.D040_ANCHOR_OFFSETS),
        *(
            f"{family}_{length}"
            for family in d041.d040.D040_D034_FAMILIES
            for length in d041.d040.D040_D034_LENGTHS
        ),
        "OSCILLATION_ONSET",
    )
    with pytest.raises(ValueError, match="unknown D-040 anchor IDs"):
        d041.d040._independent_arm_b(
            18468, horizon=1, capture_anchor_ids=("NOT_ANCHOR",)
        )


def test_d041_empty_artifact_serialization_is_byte_deterministic() -> None:
    payload = d041.build_artifact(
        [], support="reused", executed_commit_sha="a" * 40
    )
    first = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    second = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    assert first == second
    assert payload["canonical_boundary"] == {
        "organism_observation_changed": False,
        "controller_changed": False,
        "learner_changed": False,
        "action_space_changed": False,
        "energy_thermal_reward_info_rng_changed": False,
        "receptor_values_reach_organism": False,
    }
