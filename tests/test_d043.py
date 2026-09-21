from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from aweform import d026, d027, d042, d043
from aweform.development_visualizer import (
    adapt_d043_trace,
    build_d043_development_visualization,
    build_d043_html_replay,
    d043_replay_event_steps,
    select_d043_replay_indices,
)
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


def test_d043_visualization_trace_instrumentation_is_causally_inert() -> None:
    baseline = d043._run_d043_seed(19045, horizon=300)
    trace: list[d043.D043TransitionTrace] = []
    instrumented = d043._run_d043_seed(19045, horizon=300, trace=trace)
    assert instrumented == baseline
    assert len(trace) == 300
    assert all(record.reward == 0.0 and record.info == {} for record in trace)


def test_d043_artifact_payload_is_compact_json_serializable() -> None:
    result = d043._run_d043_seed(19045, horizon=200)
    payload = json.dumps(result, sort_keys=True)
    assert json.loads(payload) == result
    assert isinstance(result["contact_entries"], list)
    assert isinstance(result["contact_exits"], list)


def test_d043_display_sampling_keeps_event_steps() -> None:
    trace: list[d043.D043TransitionTrace] = []
    d043._run_d043_seed(19045, horizon=300, trace=trace)
    selected = set(select_d043_replay_indices(trace))
    assert {
        step for step in d043_replay_event_steps(trace).values() if step != 0
    } <= selected


def test_d043_visualization_examples_match_merged_artifact() -> None:
    artifact = json.loads(
        Path("development/D-043-d042-embodiment-robustness.json").read_text()
    )
    results = {result["seed"]: result for result in artifact["results"]}
    assert d043.D043_CANONICAL_VISUALIZATION_SEED == 19045
    assert d043.D043_FAILURE_VISUALIZATION_SEED == 19048
    assert results[19045]["outcome"] == "REPEATED_CYCLE"
    assert results[19045]["completed_autonomous_recharge_cycles"] == 2
    assert results[19048]["termination_reason"] == "energy_depletion"
    assert results[19048]["outcome"] == "SEEK_UNRESOLVED"

    success_trace = d043.run_d043_lifetime_trace(19045)
    success_data = adapt_d043_trace(success_trace, seed=19045)
    assert success_data.frames[-1].transition_index == 140_000
    assert success_data.causal_geometry is not None
    assert success_data.causal_geometry.front_contact_plus == (0.05, 0.025)
    assert sum(
        "FULL RECHARGE" in (frame.event_label or "")
        for frame in success_data.frames
    ) == 2

    failure_trace = d043.run_d043_lifetime_trace(19048)
    failure_data = build_d043_development_visualization(seed=19048)
    assert failure_data.frames[-1].transition_index == len(failure_trace)
    assert failure_data.frames[-1].terminated is True
    assert failure_data.frames[-1].event_label == "ENERGY DEPLETION"
    assert d043_replay_event_steps(failure_trace)["final"] == len(failure_trace)


def test_d043_html_export_is_deterministic_and_local() -> None:
    trace_records: list[d043.D043TransitionTrace] = []
    d043._run_d043_seed(19045, horizon=300, trace=trace_records)
    trace = tuple(trace_records)
    data = adapt_d043_trace(trace, seed=19045)
    html = build_d043_html_replay((data,))

    assert html == build_d043_html_replay((data,))
    assert 'window.__AWEFORM_D043_REPLAYS__ = ' in html
    assert 'window.__AWEFORM_D043_REPLAYS__.replays' in html
    assert 'fetch(' not in html
    assert 'src="http' not in html
    assert 'href="http' not in html
    assert '"schema":"aweform.d043.offline-replay.v1"' in html
    assert '"seed":19045' in html
    assert '"event":"INITIAL FRONT DUAL CONTACT"' in html
