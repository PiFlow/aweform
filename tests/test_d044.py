from __future__ import annotations

import inspect

import pytest

from aweform import d042, d043, d044
from aweform.env import Action


def test_d044_freezes_d043_support_and_horizon() -> None:
    assert d044.D044_DEFAULT_DEVELOPMENT_SEEDS == tuple(range(19045, 19065))
    with pytest.raises(ValueError, match="exactly the declared fresh seeds"):
        d044.run_d044_probe(seeds=(19045,), horizon=d044.D044_HORIZON)
    with pytest.raises(ValueError, match="frozen 140,000-transition horizon"):
        d044.run_d044_probe(horizon=d044.D044_HORIZON - 1)


def test_d044_seek_replay_and_branch_isolation_are_non_vacuous() -> None:
    result = d044._run_d044_seed(19045, horizon=30_000)
    assert result["transitions"] == 30_000
    assert result["truncated"] is True
    assert result["action_counts"] == d043._run_d043_seed(
        19045, horizon=30_000
    )["action_counts"]
    diagnostics = result["d044_diagnostics"]
    assert diagnostics["d043_replay_identity"]["match"] is True
    assert diagnostics["d043_replay_identity"]["trajectory_digest_match"] is True
    assert diagnostics["d043_replay_identity"]["update_digest_match"] is True
    assert (
        diagnostics["d043_replay_identity"]["final_learner_weights_digest_match"]
        is True
    )
    assert result["seek_episodes"]
    assert (
        sum(
            episode["action_counts_by_source"]["d026_delegated_stochastic"]
            for episode in result["seek_episodes"]
        )
        > 0
    )
    assert diagnostics["source_environment_checks"] is True
    assert diagnostics["source_controller_checks"] is True
    assert diagnostics["source_learner_checks"] is True
    assert diagnostics["source_rng_checks"] is True
    assert diagnostics["prediction_queries_read_only"] is True
    assert diagnostics["branch_order_checks"] > 0
    assert diagnostics["branch_order_mismatches"] == 0
    assert diagnostics["real_move_forward_distance_world_units"] == pytest.approx(
        0.05
    )
    assert diagnostics["real_move_distance_violations"] == 0
    assert set(result["action_counts"]) == {action.name for action in Action}


def test_d044_kinematic_branch_is_geometry_only_and_canonical() -> None:
    station = d042.D042_STATION_CENTER
    position = (0.40, 0.50)
    post, clipped, stalled = d044._geometry_branch(
        position=position,
        heading=0.0,
        station=station,
        distance=0.05,
        world_min=(0.0, 0.0),
        world_max=(1.0, 1.0),
    )
    assert clipped is False
    assert stalled is False
    assert post["station_distance"] == pytest.approx(0.05)
    assert post["accepted_dual_contact"] is True
    assert "energy" not in post
    assert "thermal" not in post


def test_d044_does_not_add_organism_mechanisms_or_call_historical_mutations() -> None:
    source = inspect.getsource(d044)
    assert "MOVE_FORWARD(distance)" not in source
    assert "front_beacon_receptors" not in source
    assert "controller.reset()" in source
    assert d044.d042.D042_TURN_ANGLE_DEGREES == 5.0
    assert d044.d042.D042_CONTACT_TOLERANCE == 0.01
