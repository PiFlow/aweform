from __future__ import annotations

import inspect
from dataclasses import replace

import pytest

from aweform import d022
from aweform.d020 import ChargePhase, D020Env, D020TransitionTelemetry
from aweform.d021 import D021Mode, D021TransitionTrace
from aweform.env import Action


def _telemetry_template() -> D020TransitionTelemetry:
    environment = D020Env()
    environment.reset(
        options={"body_position": (0.1, 0.1), "station_center": (0.9, 0.9)}
    )
    environment.step(Action.WAIT)
    assert environment.last_transition is not None
    return environment.last_transition


def _record(
    index: int,
    *,
    mode_before: D021Mode = D021Mode.AWAY,
    mode_after: D021Mode = D021Mode.AWAY,
    contact_before: bool = False,
    contact_after: bool = False,
    energy_before: float = 0.75,
    energy_after: float = 0.75,
    battery_before: float = 4000.0,
    battery_after: float = 3999.99,
    actual_stored_power: float = 0.0,
    requested_stored_power: float = 0.0,
    total_load_power: float = 0.1,
    action: Action = Action.WAIT,
) -> D021TransitionTrace:
    telemetry = replace(
        _telemetry_template(),
        step_index=index,
        action=action,
        battery_before_j=battery_before,
        battery_after_j=battery_after,
        energy_normalized_before=energy_before,
        energy_normalized_after=energy_after,
        charging_contact_before=contact_before,
        charging_contact_after=contact_after,
        total_electrical_load_w=total_load_power,
        charge_phase=(ChargePhase.BULK if contact_after else ChargePhase.OFF),
        requested_stored_power_w=requested_stored_power,
        actual_stored_power_w=actual_stored_power,
    )
    observation_before = (
        energy_before,
        0.0,
        0.0,
        0.0,
        float(contact_before),
        0.2875,
    )
    observation = (
        energy_after,
        0.0,
        0.0,
        0.0,
        float(contact_after),
        0.2875,
    )
    return D021TransitionTrace(
        transition_index=index,
        mode_before=mode_before,
        mode_after=mode_after,
        action=action,
        observation_before=observation_before,
        observation=observation,
        telemetry=telemetry,
        reward=0.0,
        info={},
    )


def _analyze(trace: list[D021TransitionTrace]) -> dict[str, object]:
    return d022.analyze_d021_trace(trace, seed=18365)


def test_source_lifetimes_are_frozen_and_trace_runner_is_reused() -> None:
    assert d022.D021_DEFAULT_DEVELOPMENT_SEEDS == (18365, 18366, 18367)
    assert d022.D021_HORIZON == 70_000
    assert d022.D022_ACCEPTED_D021_AWAY_CONTACT_COUNTS == {
        18365: 88,
        18366: 92,
        18367: 95,
    }
    source = inspect.getsource(d022.run_d022_audit)
    assert "run_d021_lifetime_trace" in source
    assert "D021_DEFAULT_DEVELOPMENT_SEEDS" in source
    assert "D021_HORIZON" in source


def test_d021_trace_boundary_is_preserved() -> None:
    record = _record(1)
    analyzed = _analyze([record])
    assert record.reward == 0.0
    assert record.info == {}
    assert len(record.observation_before) == 6
    assert len(record.observation) == 6
    assert analyzed["total_lifetime_transitions"] == 1


def test_episode_entry_requires_all_declared_conditions() -> None:
    cases = [
        _record(1, mode_before=D021Mode.CHARGE, contact_after=True),
        _record(1, energy_before=0.499999, energy_after=0.499999, contact_after=True),
        _record(1, contact_before=True, contact_after=True),
        _record(1, contact_before=False, contact_after=False),
    ]
    for record in cases:
        assert _analyze([record])["number_of_incidental_away_contact_episodes"] == 0

    qualifying = _record(1, energy_before=0.50, energy_after=0.50, contact_after=True)
    result = _analyze([qualifying])
    assert result["number_of_incidental_away_contact_episodes"] == 1


def test_contact_active_semantics_and_normal_exit() -> None:
    trace = [
        _record(
            1,
            contact_after=True,
            battery_before=3000.0,
            battery_after=3000.05,
            actual_stored_power=1.0,
            requested_stored_power=1.0,
            total_load_power=0.5,
        ),
        _record(
            2,
            contact_before=True,
            contact_after=True,
            battery_before=3000.05,
            battery_after=3000.10,
            actual_stored_power=1.0,
            requested_stored_power=1.0,
            total_load_power=0.5,
        ),
        _record(
            3,
            contact_before=True,
            contact_after=False,
            battery_before=3000.10,
            battery_after=3000.05,
        ),
    ]
    result = _analyze(trace)
    episode = result["episodes"][0]
    assert episode["entry_transition"] == 1
    assert episode["final_contact_active_transition"] == 2
    assert episode["exit_transition"] == 3
    assert episode["ending_classification"] == "normal_contact_exit"
    assert episode["contact_active_transitions"] == 2
    assert episode["contact_active_seconds"] == pytest.approx(0.2)
    assert episode["gross_accepted_stored_charge_j"] == pytest.approx(0.2)
    assert episode["total_electrical_load_energy_j"] == pytest.approx(0.1)


def test_episode_endings_are_explicit() -> None:
    horizon = _analyze([_record(1, contact_after=True)])
    horizon_episode = horizon["episodes"][0]
    assert horizon_episode["ending_classification"] == "lifetime_end_while_contacting"
    assert horizon_episode["exit_transition"] is None

    departure = _analyze(
        [_record(1, contact_after=True, mode_after=D021Mode.SEEK)]
    )
    departure_episode = departure["episodes"][0]
    assert departure_episode["ending_classification"] == "mode_departure_while_active"
    assert departure_episode["ending_transition"] == 1
    assert departure_episode["exit_transition"] is None


def test_exact_energy_accounting_does_not_use_battery_delta() -> None:
    result = _analyze(
        [
            _record(
                1,
                contact_after=True,
                battery_before=3000.0,
                battery_after=3000.0,
                actual_stored_power=2.0,
                requested_stored_power=2.0,
                total_load_power=0.5,
            )
        ]
    )
    episode = result["episodes"][0]
    assert episode["gross_accepted_stored_charge_j"] == pytest.approx(0.2)
    assert episode["total_electrical_load_energy_j"] == pytest.approx(0.05)
    assert episode["net_battery_change_j"] == pytest.approx(0.0)
    assert episode["bookkeeping_residual_j"] == pytest.approx(-0.15)


def test_mode_and_away_charge_reconciliation() -> None:
    trace = [
        _record(
            1,
            mode_before=D021Mode.AWAY,
            contact_after=True,
            actual_stored_power=1.0,
        ),
        _record(
            2,
            mode_before=D021Mode.CHARGE,
            mode_after=D021Mode.CHARGE,
            contact_before=True,
            contact_after=True,
            actual_stored_power=2.0,
        ),
        _record(3, mode_before=D021Mode.AWAY, actual_stored_power=3.0),
    ]
    result = _analyze(trace)
    mode_totals = result["accepted_stored_charge_j_by_mode_before"]
    assert mode_totals["AWAY"] == pytest.approx(0.4)
    assert mode_totals["CHARGE"] == pytest.approx(0.2)
    assert result["unmatched_away_accepted_charge_j"] == pytest.approx(0.3)
    away = result["away_reconciliation"]
    assert away["matches_within_tolerance"] is True
    assert result["episode_lifetime_reconciliation"]["matches_within_tolerance"] is True


def test_shadow_subtracts_prior_incidental_charge_only() -> None:
    result = _analyze(
        [
            _record(
                1,
                contact_after=True,
                battery_before=3000.0,
                battery_after=3000.05,
                actual_stored_power=1.0,
                requested_stored_power=1.0,
                total_load_power=0.5,
            ),
            _record(
                2,
                energy_before=0.50001,
                battery_before=2664.05,
                battery_after=2664.04,
                actual_stored_power=0.0,
            ),
            _record(
                3,
                mode_after=D021Mode.SEEK,
                energy_before=0.4999,
                battery_before=2663.9,
                battery_after=2663.89,
            ),
        ]
    )
    shadow = result["shadow"]
    assert shadow["open_loop_no_incidental_threshold_crossing_transition"] == 2
    assert shadow["actual_first_low_energy_seek_entry_transition"] == 3
    assert shadow["threshold_shift_transitions"] == 1
    assert shadow["threshold_shift_seconds"] == pytest.approx(0.1)
    assert shadow[
        "cumulative_incidental_accepted_charge_before_shadow_crossing_j"
    ] == pytest.approx(0.1)
    assert shadow[
        "cumulative_incidental_accepted_charge_before_actual_seek_entry_j"
    ] == pytest.approx(0.1)


def test_shadow_uses_strictly_less_than_half() -> None:
    result = _analyze(
        [
            _record(
                1,
                contact_after=True,
                battery_before=3000.0,
                battery_after=3000.05,
                actual_stored_power=1.0,
                requested_stored_power=1.0,
                total_load_power=0.5,
            ),
            _record(
                2,
                energy_before=0.50001,
                battery_before=2664.1,
                battery_after=2664.09,
            ),
            _record(
                3,
                mode_after=D021Mode.SEEK,
                energy_before=0.4999,
                battery_before=2663.9,
                battery_after=2663.89,
            ),
        ]
    )
    assert (
        result["shadow"]["open_loop_no_incidental_threshold_crossing_transition"]
        == 3
    )


def test_shadow_stops_at_actual_policy_divergence_and_zero_incidental_case() -> None:
    result = _analyze(
        [
            _record(
                1,
                mode_after=D021Mode.SEEK,
                energy_before=0.4999,
                battery_before=2663.9,
                battery_after=2663.89,
            ),
            _record(2, mode_before=D021Mode.SEEK, mode_after=D021Mode.CHARGE),
        ]
    )
    assert result["total_incidental_accepted_stored_charge_j"] == 0.0
    assert result["incidental_fraction_of_all_accepted_stored_charge"] == 0.0
    assert (
        result["shadow"]["open_loop_no_incidental_threshold_crossing_transition"]
        == 1
    )
    assert result["shadow"]["actual_first_low_energy_seek_entry_transition"] == 1
    assert result["shadow"]["threshold_shift_transitions"] == 0


def test_d021_contact_count_reconciliation_on_accepted_lifetimes() -> None:
    payload = d022.run_d022_audit()
    assert payload["source_seeds"] == [18365, 18366, 18367]
    assert payload["source_horizon"] == 70_000
    results = payload["results"]
    assert [
        result["number_of_incidental_away_contact_episodes"] for result in results
    ] == [88, 92, 95]
    assert all(
        result["d021_contact_count_reconciliation"]["matches"]
        for result in results
    )


def test_invalid_implementation_sha_is_rejected() -> None:
    with pytest.raises(ValueError, match="40-character lowercase SHA"):
        d022.run_d022_audit("bad")
