from __future__ import annotations

import inspect
import json

import pytest

from aweform import d026, d027, d042, d043
from aweform.env import Action


def test_d043_freezes_fresh_seed_support_and_horizon() -> None:
    assert d043.D043_DEFAULT_DEVELOPMENT_SEEDS == tuple(range(19045, 19065))
    with pytest.raises(ValueError, match="exactly the declared fresh seeds"):
        d043.run_d043_probe(seeds=(19045,), horizon=d043.D043_HORIZON)
    with pytest.raises(ValueError, match="frozen horizon"):
        d043.run_d043_probe(horizon=d043.D043_HORIZON - 1)


def test_d043_reuses_d042_embodiment_and_organism_contracts() -> None:
    assert d042.D042_TURN_ANGLE_DEGREES == 5.0
    assert d042.D042_FRONT_X == 0.05
    assert d042.D042_CONTACT_TOLERANCE == 0.01
    assert d043.d026.D026Controller is d026.D026Controller
    assert (
        d043.d027.D027ActionConsequencePredictor
        is d027.D027ActionConsequencePredictor
    )
    assert "front_beacon_receptors" not in inspect.getsource(d043)


def test_d043_short_deterministic_lifetime_preserves_visible_contract() -> None:
    first = d043._run_d043_seed(19045, horizon=300)
    second = d043._run_d043_seed(19045, horizon=300)
    assert first == second
    assert first["transitions"] == 300
    assert first["truncated"] is True
    assert first["initial_dual_contact"] is True
    assert set(first["action_counts"]) == {action.name for action in Action}
    assert first["low_energy_seek_entries"] == len(first["seek_episodes"])
    assert first["physical_reacquisitions"] <= len(first["seek_episodes"])


def test_d043_telemetry_is_causally_inert_against_d042_runner() -> None:
    d042_result = d042._run_d042_seed(19045, horizon=300)
    d043_result = d043._run_d043_seed(19045, horizon=300)
    for field in (
        "transitions",
        "terminated",
        "truncated",
        "termination_reason",
        "action_counts",
        "mode_occupancy",
        "mode_entry_counts",
        "battery_normalized",
        "temperature_normalized",
        "max_body_temperature_c",
        "turns",
    ):
        assert d043_result[field] == d042_result[field]


def test_d043_artifact_payload_is_compact_json_serializable() -> None:
    result = d043._run_d043_seed(19045, horizon=200)
    payload = json.dumps(result, sort_keys=True)
    assert json.loads(payload) == result
    assert isinstance(result["contact_entries"], list)
    assert isinstance(result["contact_exits"], list)
