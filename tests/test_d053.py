from __future__ import annotations

import pytest

from aweform.d045 import D045_MAX_WHEEL_DELTA_RAD, integrate_differential_drive
from aweform.d052 import D052CommandSource, D052Mode, _legal_wheel_pair
from aweform.d053 import (
    D053_DEVELOPMENT_SEEDS,
    D053RoamingFixture,
    run_d053_lifetime,
    validate_d053_development_seeds,
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

    assert stream(22053) == stream(22053)
    assert stream(22053) != stream(22054)


def test_short_low_energy_lifetime_runs_through_yield_and_resumes_roaming() -> None:
    life = run_d053_lifetime(22053, horizon=20_000, initial_battery_fraction=0.19)
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


def test_d053_visualizer_retains_required_windows_and_is_deterministic() -> None:
    from aweform.development_visualizer import (
        adapt_d053_trace,
        build_development_html_replay,
    )

    short = run_d053_lifetime(22053, horizon=8)
    data = adapt_d053_trace(short.trace, seed=short.seed)
    html = build_development_html_replay(
        (data,), schema="aweform.d053.offline-replay.v1", title="test"
    )
    assert html == build_development_html_replay(
        (data,), schema="aweform.d053.offline-replay.v1", title="test"
    )
    assert "RETURN 20%" in html and "RECOVERY 80%" in html
    assert "command_source" in html and "cycle" in html
    assert "fetch(" not in html and 'src="http' not in html and 'href="http' not in html
