from __future__ import annotations

import json
from typing import cast

import pytest

from aweform.d045 import D045_MAX_WHEEL_DELTA_RAD, integrate_differential_drive
from aweform.d052 import D052CommandSource, D052Mode, _legal_wheel_pair
from aweform.d053 import (
    D053_DEVELOPMENT_SEEDS,
    D053_MAX_EVENT_SAMPLES,
    D053Lifetime,
    D053RoamingFixture,
    _bounded_samples,
    run_d053_lifetime,
    validate_d053_development_seeds,
)
from aweform.development_visualizer import (
    adapt_d053_trace,
    build_development_html_replay,
    select_d053_replay_indices,
)
from aweform.env import Action
from aweform.exp001 import (
    ExternalObservation,
    StochasticPersistentExplorer,
    policy_rng_from_seed,
)


def test_exact_development_seed_block_and_reservation_guard() -> None:
    assert (
        validate_d053_development_seeds(D053_DEVELOPMENT_SEEDS)
        == D053_DEVELOPMENT_SEEDS
    )
    with pytest.raises(ValueError):
        validate_d053_development_seeds((22053,))
    with pytest.raises(ValueError):
        validate_d053_development_seeds((50001, 22054, 22055, 22056, 22057))


def test_fixture_matches_historical_explorer_and_fixed_wheel_vectors() -> None:
    seed = D053_DEVELOPMENT_SEEDS[0]
    fixture = D053RoamingFixture(seed)
    explorer = StochasticPersistentExplorer(policy_rng_from_seed(seed))
    expected = [explorer.act(ExternalObservation(0.0, 0.0, 0.0)) for _ in range(250)]
    actual = [fixture.propose() for _ in range(250)]
    assert [proposal.symbolic_action for proposal in actual] == expected
    mapping = {
        Action.MOVE_FORWARD: (D045_MAX_WHEEL_DELTA_RAD, D045_MAX_WHEEL_DELTA_RAD),
        Action.TURN_LEFT: (-D045_MAX_WHEEL_DELTA_RAD, D045_MAX_WHEEL_DELTA_RAD),
        Action.TURN_RIGHT: (D045_MAX_WHEEL_DELTA_RAD, -D045_MAX_WHEEL_DELTA_RAD),
    }
    for proposal in actual:
        assert proposal.wheel_command == mapping[proposal.symbolic_action]
        assert _legal_wheel_pair(proposal.wheel_command) == proposal.wheel_command
    _, turn = integrate_differential_drive(
        (0.5, 0.5), 0.0, *_legal_wheel_pair(mapping[Action.TURN_LEFT])
    )
    assert turn > 0.0
    with pytest.raises(ValueError):
        _legal_wheel_pair((D045_MAX_WHEEL_DELTA_RAD + 1e-5, 0.0))


def test_fixture_replays_and_varies_by_seed() -> None:
    def stream(seed: int) -> list[tuple[Action, tuple[float, float]]]:
        fixture = D053RoamingFixture(seed)
        return [
            (p.symbolic_action, p.wheel_command)
            for p in (fixture.propose() for _ in range(300))
        ]

    assert stream(22153) == stream(22153)
    assert stream(22153) != stream(22154)


@pytest.fixture(scope="module")
def low_energy_life() -> D053Lifetime:
    return run_d053_lifetime(22153, horizon=20_000, initial_battery_fraction=0.19)


def _first_transition(life: D053Lifetime, event: str) -> int:
    return next(
        cast(int, row["transition"])
        for row in life.trace
        if event in cast(list[str], row["events"])
    )


def test_short_low_energy_lifetime_runs_through_yield_and_resumes_roaming(
    low_energy_life: D053Lifetime,
) -> None:
    life = low_energy_life
    summary = life.summary
    assert summary["total_transitions"] == 20_000
    assert summary["return_activated_count"] == 1
    assert summary["completed_recovery_yield_count"] == 1
    assert summary["pass_through_count"] > 0
    assert summary["reward_exactly_zero"] is True
    assert summary["organism_info_exactly_empty"] is True
    assert sum(summary["mode_transition_counts"].values()) == 20_000
    assert summary["level1_preemption_count"] + summary["pass_through_count"] == 20_000
    yield_events = [x for x in life.trace if "RECOVERY_YIELD" in x["events"]]
    assert len(yield_events) == 1
    assert yield_events[0]["command_source"] == D052CommandSource.PASS_THROUGH.value
    assert yield_events[0]["active_mode"] == D052Mode.NORMAL.value
    assert any(
        x["transition"] > yield_events[0]["transition"]
        and x["active_mode"] == "NORMAL"
        and x["command_source"] == "PASS_THROUGH"
        for x in life.trace
    )


def test_samples_record_executed_wheels_separately_from_fixture_proposal(
    low_energy_life: D053Lifetime,
) -> None:
    summary = low_energy_life.summary
    samples = cast(list[dict[str, object]], summary["event_samples"])
    assert samples[0]["events"] == ["RESET"]
    assert "TRUNCATED" in cast(list[str], samples[-1]["events"])
    assert summary["samples_truncated"] is False
    assert summary["retained_sample_count"] == len(samples)
    assert summary["event_row_count"] == len(samples)
    assert any(
        not row["events"]
        and row["active_mode"] == previous["active_mode"]
        and row["command_source"] == previous["command_source"]
        and row["charging_contact_before"] == row["charging_contact_after"]
        and row["d050_mode"] != previous["d050_mode"]
        for previous, row in zip(samples[1:], samples[2:], strict=False)
    )
    charge_hold = next(
        row for row in samples if "CHARGING_CONTACT" in cast(list[str], row["events"])
    )
    assert charge_hold["command_source"] == D052CommandSource.CHARGE_HOLD.value
    assert charge_hold["wheel_command"] == [0.0, 0.0]
    proposed = cast(list[float], charge_hold["proposed_wheel_command"])
    assert proposed != [0.0, 0.0]
    m = D045_MAX_WHEEL_DELTA_RAD
    assert tuple(proposed) in {(m, m), (-m, m), (m, -m)}
    for row in samples[1:]:
        if row["command_source"] == D052CommandSource.PASS_THROUGH.value:
            assert row["wheel_command"] == row["proposed_wheel_command"]


def test_event_sample_cap_collapses_holds_and_keeps_priority_rows() -> None:
    def row(
        transition: int,
        events: list[str],
        source: str = "D050_SMOOTH",
        d050_mode: str | None = "INVALID_BEACON",
    ) -> dict[str, object]:
        return {
            "transition": transition,
            "events": events,
            "active_mode": "RETURN",
            "command_source": source,
            "d050_mode": d050_mode,
        }

    rows = [row(0, ["RESET"], "", None), row(1, ["RETURN_ACTIVATED"])]
    rows += [row(t, ["INVALID_BEACON"]) for t in range(2, 402)]
    rows += [row(410, ["TERMINAL_SPIN_EXHAUSTED"], "RETURN_HOLD", "TERMINAL_SPIN")]
    rows += [row(t, [], "RETURN_HOLD", "TERMINAL_SPIN") for t in range(411, 420)]
    rows += [
        row(t, ["PHYSICAL_CONTACT_ACQUIRED"], d050_mode="CONTACT")
        for t in range(500, 800)
    ]
    rows += [row(t, [], d050_mode=str(t)) for t in range(800, 1100)]
    rows += [row(1200, ["RECOVERY_YIELD"]), row(1300, ["TERMINATED"])]
    samples = _bounded_samples(rows)

    assert len(samples) == D053_MAX_EVENT_SAMPLES
    transitions = [cast(int, item["transition"]) for item in samples]
    assert transitions == sorted(transitions)
    assert transitions[0] == 0 and transitions[-1] == 1300
    assert {1, 2, 410, 1200} <= set(transitions)
    assert not set(range(3, 402)) & set(transitions)
    assert not set(range(411, 420)) & set(transitions)
    assert not set(range(800, 1100)) & set(transitions)
    contact = [t for t in transitions if 500 <= t < 800]
    assert len(contact) == D053_MAX_EVENT_SAMPLES - 6
    assert contact[0] == 500 and contact[-1] > 780

    short = [row(0, ["RESET"]), row(5, [], d050_mode="PURSUIT"), row(9, ["TRUNCATED"])]
    assert _bounded_samples(short) == short
    hold = [row(0, ["RESET"], "", None)]
    hold += [row(10, ["TERMINAL_SPIN_EXHAUSTED"], "RETURN_HOLD", "TERMINAL_SPIN")]
    hold += [row(t, [], "RETURN_HOLD", "TERMINAL_SPIN") for t in range(11, 20)]
    hold += [row(t, ["INVALID_BEACON"]) for t in range(30, 40)]
    hold += [row(99, ["TERMINATED"], "RETURN_HOLD", "TERMINAL_SPIN")]
    assert [item["transition"] for item in _bounded_samples(hold)] == [
        0,
        10,
        11,
        30,
        99,
    ]


def test_d053_selector_windows_and_stride() -> None:
    def row(
        events: list[str], mode: str = "NORMAL", source: str = "PASS_THROUGH"
    ) -> dict[str, object]:
        return {"events": events, "active_mode": mode, "command_source": source}

    trace = [row([]) for _ in range(1000)]
    trace[0] = row(["RESET"])
    trace[200] = row(["PHYSICAL_CONTACT_ACQUIRED"])
    trace[420] = row(["PHYSICAL_CONTACT_LOST"], "RETURN", "D050_SMOOTH")
    for index in range(600, 800):
        trace[index] = row(["INVALID_BEACON"], "RETURN", "D050_SMOOTH")
    trace[999] = row(["TRUNCATED"], "RETURN", "D050_SMOOTH")

    expected = (
        set(range(0, 1000, 100))
        | set(range(150, 251))
        | set(range(550, 651))
        | set(range(949, 1000))
    )
    assert set(select_d053_replay_indices(trace)) == expected

    contact_trace = list(trace)
    contact_trace[300] = row(["RETURN_ACTIVATED"], "RETURN", "D050_SMOOTH")
    contact_trace[340] = row(["CHARGING_CONTACT"], "CHARGE", "CHARGE_HOLD")
    assert set(select_d053_replay_indices(contact_trace)) == expected | set(
        range(250, 391)
    )

    invalid_trace = list(trace)
    invalid_trace[500] = row(["RETURN_ACTIVATED"], "RETURN", "D050_SMOOTH")
    assert set(select_d053_replay_indices(invalid_trace)) == expected | set(
        range(450, 651)
    )

    hold_trace = [row([]) for _ in range(1000)]
    hold_trace[0] = row(["RESET"])
    hold_trace[300] = row(["RETURN_ACTIVATED"], "RETURN", "D050_SMOOTH")
    hold_trace[420] = row(["TERMINAL_SPIN_EXHAUSTED"], "RETURN", "RETURN_HOLD")
    for index in range(421, 999):
        hold_trace[index] = row([], "RETURN", "RETURN_HOLD")
    hold_trace[999] = row(["TERMINATED"], "RETURN", "RETURN_HOLD")
    assert set(select_d053_replay_indices(hold_trace)) == (
        set(range(0, 1000, 100)) | set(range(250, 471)) | set(range(949, 1000))
    )

    open_trace = [row([]) for _ in range(1000)]
    open_trace[0] = row(["RESET"])
    open_trace[900] = row(["RETURN_ACTIVATED"], "RETURN", "D050_SMOOTH")
    open_trace[999] = row(["TRUNCATED"], "RETURN", "D050_SMOOTH")
    assert set(select_d053_replay_indices(open_trace)) == (
        set(range(0, 1000, 100)) | set(range(850, 1000))
    )

    wedge_trace = [row([], "RETURN", "D050_SMOOTH") for _ in range(6000)]
    wedge_trace[0] = row(["RESET"])
    for index in range(1, 1000):
        wedge_trace[index] = row([])
    wedge_trace[1000] = row(["RETURN_ACTIVATED"], "RETURN", "D050_SMOOTH")
    wedge_trace[4500] = row(["CHARGING_CONTACT"], "CHARGE", "CHARGE_HOLD")
    for index in range(4501, 5999):
        wedge_trace[index] = row([], "CHARGE", "CHARGE_HOLD")
    wedge_trace[5999] = row(["TRUNCATED"], "CHARGE", "CHARGE_HOLD")
    wedge = set(select_d053_replay_indices(wedge_trace))
    assert wedge == (
        set(range(0, 6000, 100))
        | set(range(950, 3001))
        | set(range(4450, 4551))
        | set(range(5949, 6000))
    )
    assert not set(range(3001, 3100)) & wedge


def _embedded_payload(html: str) -> dict[str, object]:
    prefix = "window.__AWEFORM_D043_REPLAYS__ = "
    start = html.index(prefix) + len(prefix)
    end = html.index(";\n(function", start)
    return cast(dict[str, object], json.loads(html[start:end]))


def test_d053_html_payload_retains_return_window_and_view_fields(
    low_energy_life: D053Lifetime,
) -> None:
    life = low_energy_life
    data = adapt_d053_trace(life.trace, seed=life.seed)
    html = build_development_html_replay(
        (data,),
        schema="aweform.d053.offline-replay.v1",
        title="t",
        event_navigation=True,
    )
    assert html == build_development_html_replay(
        (data,),
        schema="aweform.d053.offline-replay.v1",
        title="t",
        event_navigation=True,
    )
    assert "fetch(" not in html and 'src="http' not in html and 'href="http' not in html
    payload = _embedded_payload(html)
    assert payload["schema"] == "aweform.d053.offline-replay.v1"
    (replay,) = cast(list[dict[str, object]], payload["replays"])
    assert replay["seed"] == 22153
    assert replay["event_navigation"] is True
    assert replay["energy_strip"] == {
        "range": [0.0, 1.0],
        "thresholds": [[0.2, "RETURN 20%"], [0.8, "RECOVERY 80%"]],
    }
    frames = cast(list[dict[str, object]], replay["frames"])
    by_transition = {cast(int, frame["transition"]): frame for frame in frames}
    total = len(life.trace) - 1
    assert len(frames) < total // 2

    activated = _first_transition(life, "RETURN_ACTIVATED")
    contact = _first_transition(life, "CHARGING_CONTACT")
    recovery = _first_transition(life, "RECOVERY_YIELD")
    retained = set(range(max(0, activated - 50), contact + 51))
    retained |= set(range(recovery - 50, recovery + 51))
    retained |= set(range(0, total + 1, 100)) | {total}
    assert retained <= set(by_transition)

    for transition in range(activated, contact):
        frame = by_transition[transition]
        assert frame["mode"] == "RETURN"
        assert frame["command_source"] == "D050_SMOOTH"
        assert "/ D-050 " in cast(str, frame["action"])
    for transition, frame in by_transition.items():
        if transition == 0:
            assert "command_source" not in frame
            continue
        source = life.trace[transition]
        assert frame["command_source"] == source["command_source"]
        assert frame["cycle_index"] == source["cycle_index"]
        assert cast(str, frame["action"]).startswith(
            f"proposal {source['symbolic_proposal']}"
        )
    assert by_transition[activated]["cycle_index"] == 1
    assert "RETURN_ACTIVATED" in cast(str, by_transition[activated]["event"])
