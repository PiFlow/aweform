"""D-022 evaluator-only audit of incidental D-021 charger contact.

This module does not run a changed controller or environment.  It replays the
accepted D-021 lifetimes through ``run_d021_lifetime_trace`` and performs all
accounting after each complete trace has been produced.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean, median
from typing import Final, Sequence

from .d020 import ChargePhase, D020PhysicalConfig, D020TransitionTelemetry
from .d021 import (
    D021_DEFAULT_DEVELOPMENT_SEEDS,
    D021_HORIZON,
    D021Mode,
    D021TransitionTrace,
    run_d021_lifetime_trace,
)
from .env import Action
from .exp003 import EXP003_B50_ENTER_SEEK_THRESHOLD

D022_AUTHORITATIVE_BASE_SHA: Final[str] = (
    "4a51abe2c9f7338b25636ee059a976e21f5b0eda"
)
D022_SCHEMA_VERSION: Final[int] = 1
D022_CHARGE_TOLERANCE_J: Final[float] = 1.0e-9
D022_ACCEPTED_D021_AWAY_CONTACT_COUNTS: Final[dict[int, int]] = {
    18365: 88,
    18366: 92,
    18367: 95,
}


@dataclass(slots=True)
class _ActiveEpisode:
    """Mutable evaluator accumulator for one classified contact episode."""

    episode_index: int
    entry: D021TransitionTrace
    active_records: list[D021TransitionTrace] = field(default_factory=list)
    exit_transition: int | None = None
    ending_transition: int | None = None
    ending_classification: str | None = None

    def add(self, record: D021TransitionTrace) -> None:
        self.active_records.append(record)

    def finish(
        self,
        classification: str,
        record: D021TransitionTrace | None = None,
    ) -> None:
        self.ending_classification = classification
        if record is not None:
            self.ending_transition = record.transition_index
            if classification == "normal_contact_exit":
                self.exit_transition = record.transition_index

    def as_record(self, dt_seconds: float) -> dict[str, object]:
        if not self.active_records:
            raise RuntimeError("incidental episode has no contact-active records")
        if self.ending_classification is None:
            raise RuntimeError("incidental episode has no ending classification")
        entry_telemetry = self.entry.telemetry
        final_telemetry = self.active_records[-1].telemetry
        accepted_charge_j = sum(
            _accepted_stored_charge_j(record.telemetry, dt_seconds)
            for record in self.active_records
        )
        electrical_load_j = sum(
            _electrical_load_energy_j(record.telemetry, dt_seconds)
            for record in self.active_records
        )
        contact_active_seconds = len(self.active_records) * dt_seconds
        net_battery_change_j = (
            final_telemetry.battery_after_j - entry_telemetry.battery_before_j
        )
        expected_net_battery_change_j = accepted_charge_j - electrical_load_j
        phase_counts = {phase.name: 0 for phase in ChargePhase}
        action_counts = {action.name: 0 for action in Action}
        for record in self.active_records:
            phase_counts[record.telemetry.charge_phase.name] += 1
            action_counts[record.action.name] += 1
        accepted_powers = tuple(
            record.telemetry.actual_stored_power_w for record in self.active_records
        )
        return {
            "episode_index": self.episode_index,
            "entry_transition": self.entry.transition_index,
            "final_contact_active_transition": (
                final_telemetry.step_index
            ),
            "exit_transition": self.exit_transition,
            "ending_transition": self.ending_transition,
            "ending_classification": self.ending_classification,
            "contact_active_transitions": len(self.active_records),
            "contact_active_seconds": contact_active_seconds,
            "normalized_battery_before_entry": (
                entry_telemetry.energy_normalized_before
            ),
            "normalized_battery_after_final_contact_active": (
                final_telemetry.energy_normalized_after
            ),
            "battery_before_entry_j": entry_telemetry.battery_before_j,
            "battery_after_final_contact_active_j": final_telemetry.battery_after_j,
            "gross_accepted_stored_charge_j": accepted_charge_j,
            "total_electrical_load_energy_j": electrical_load_j,
            "net_battery_change_j": net_battery_change_j,
            "expected_net_battery_change_j": expected_net_battery_change_j,
            "bookkeeping_residual_j": (
                net_battery_change_j - expected_net_battery_change_j
            ),
            "mean_accepted_stored_power_w": (
                accepted_charge_j / contact_active_seconds
            ),
            "maximum_accepted_stored_power_w": max(accepted_powers),
            "charger_phase_counts": phase_counts,
            "action_counts": action_counts,
            "headroom_or_battery_clamp_transition_count": sum(
                _charge_or_battery_clamp(record.telemetry, dt_seconds)
                for record in self.active_records
            ),
            "charging_body_heat_energy_j": sum(
                record.telemetry.charging_body_heat_w * dt_seconds
                for record in self.active_records
            ),
        }


def _accepted_stored_charge_j(
    telemetry: D020TransitionTelemetry, dt_seconds: float
) -> float:
    """Use exact D-020 accepted stored power, never a battery delta."""
    return telemetry.actual_stored_power_w * dt_seconds


def _electrical_load_energy_j(
    telemetry: D020TransitionTelemetry, dt_seconds: float
) -> float:
    """Use exact D-020 total electrical load telemetry."""
    return telemetry.total_electrical_load_w * dt_seconds


def _charge_or_battery_clamp(
    telemetry: D020TransitionTelemetry, dt_seconds: float
) -> int:
    requested_j = telemetry.requested_stored_power_w * dt_seconds
    accepted_j = _accepted_stored_charge_j(telemetry, dt_seconds)
    unconstrained_battery_after = (
        telemetry.battery_before_j
        + accepted_j
        - _electrical_load_energy_j(telemetry, dt_seconds)
    )
    return int(
        accepted_j + D022_CHARGE_TOLERANCE_J < requested_j
        or abs(telemetry.battery_after_j - unconstrained_battery_after)
        > D022_CHARGE_TOLERANCE_J
    )


def _is_incidental_entry(record: D021TransitionTrace) -> bool:
    telemetry = record.telemetry
    return (
        record.mode_before is D021Mode.AWAY
        and telemetry.energy_normalized_before >= EXP003_B50_ENTER_SEEK_THRESHOLD
        and not telemetry.charging_contact_before
        and telemetry.charging_contact_after
    )


def _is_contact_active(record: D021TransitionTrace) -> bool:
    telemetry = record.telemetry
    return (
        record.mode_before is D021Mode.AWAY
        and telemetry.charging_contact_after
    )


def _validate_trace(trace: Sequence[D021TransitionTrace]) -> None:
    if not trace:
        raise ValueError("D-021 trace must not be empty")
    for expected_index, record in enumerate(trace, start=1):
        if record.transition_index != expected_index:
            raise ValueError("D-021 trace transition indices must be sequential")
        if len(record.observation_before) != 6 or len(record.observation) != 6:
            raise ValueError("D-021 trace observations must contain six channels")
        if record.reward != 0.0 or record.info != {}:
            raise ValueError("D-021 trace crossed the reward/info boundary")


def _finish_episode(
    episodes: list[_ActiveEpisode], active: _ActiveEpisode
) -> None:
    if active.ending_classification is None:
        raise RuntimeError("cannot finish an unclassified incidental episode")
    episodes.append(active)


def _classify_episodes(
    trace: Sequence[D021TransitionTrace],
) -> tuple[tuple[dict[str, object], ...], set[int]]:
    episodes: list[_ActiveEpisode] = []
    active: _ActiveEpisode | None = None
    active_transition_indices: set[int] = set()
    for record in trace:
        telemetry = record.telemetry
        if active is None and _is_incidental_entry(record):
            active = _ActiveEpisode(
                episode_index=len(episodes) + 1,
                entry=record,
            )

        if active is None:
            continue

        if _is_contact_active(record):
            active.add(record)
            active_transition_indices.add(record.transition_index)
            if record.mode_after is not D021Mode.AWAY:
                active.finish("mode_departure_while_active", record)
                _finish_episode(episodes, active)
                active = None
        elif telemetry.charging_contact_before and not telemetry.charging_contact_after:
            active.finish("normal_contact_exit", record)
            _finish_episode(episodes, active)
            active = None
        elif record.mode_before is not D021Mode.AWAY:
            active.finish("mode_departure_while_active", record)
            _finish_episode(episodes, active)
            active = None
        else:
            active.finish("contact_state_discontinuity", record)
            _finish_episode(episodes, active)
            active = None

    if active is not None:
        if trace[-1].telemetry.charging_contact_after:
            active.finish("lifetime_end_while_contacting", trace[-1])
        else:
            active.finish("lifetime_end_without_contact_exit", trace[-1])
        _finish_episode(episodes, active)

    return (
        tuple(
            episode.as_record(D020PhysicalConfig().dt_seconds)
            for episode in episodes
        ),
        active_transition_indices,
    )


def _first_seek_entry(trace: Sequence[D021TransitionTrace]) -> int | None:
    for record in trace:
        if (
            record.mode_before is D021Mode.AWAY
            and record.mode_after is D021Mode.SEEK
            and record.observation_before[0] < EXP003_B50_ENTER_SEEK_THRESHOLD
        ):
            return record.transition_index
    return None


def _first_reacquisition(trace: Sequence[D021TransitionTrace]) -> int | None:
    for record in trace:
        telemetry = record.telemetry
        if (
            record.mode_before is D021Mode.SEEK
            and not telemetry.charging_contact_before
            and telemetry.charging_contact_after
        ):
            return record.transition_index
    return None


def _completed_cycles(trace: Sequence[D021TransitionTrace], capacity_j: float) -> int:
    recharge_ready = False
    completed = 0
    for record in trace:
        telemetry = record.telemetry
        if (
            telemetry.charger_termination_latched_after
            and telemetry.battery_after_j >= capacity_j
        ):
            recharge_ready = True
        if (
            recharge_ready
            and record.mode_before is D021Mode.CHARGE
            and record.mode_after is D021Mode.DEPART
        ):
            completed += 1
            recharge_ready = False
    return completed


def _termination_reason(trace: Sequence[D021TransitionTrace]) -> str:
    final = trace[-1].telemetry
    if final.termination_reason is not None:
        return final.termination_reason.value
    if final.truncated:
        return "horizon_truncation"
    return "incomplete"


def _float_value(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"D-022 field {name} is not numeric")
    return float(value)


def _int_value(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RuntimeError(f"D-022 field {name} is not an integer")
    return value


def _mapping_value(value: object, name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise RuntimeError(f"D-022 field {name} is not an object")
    return value


def _shadow_metrics(
    trace: Sequence[D021TransitionTrace],
    active_transition_indices: set[int],
    actual_seek_entry: int | None,
    capacity_j: float,
    dt_seconds: float,
) -> dict[str, object]:
    cumulative_incidental_j = 0.0
    first_crossing: int | None = None
    cumulative_before_crossing: float | None = None
    clamp_required = False
    clamp_count = 0
    cumulative_before_actual: float | None = None
    if actual_seek_entry is None:
        limit = len(trace)
    else:
        limit = actual_seek_entry

    for record in trace[:limit]:
        telemetry = record.telemetry
        shadow_battery_raw = telemetry.battery_before_j - cumulative_incidental_j
        shadow_battery = min(capacity_j, max(0.0, shadow_battery_raw))
        if shadow_battery != shadow_battery_raw:
            clamp_required = True
            clamp_count += 1
        if (
            first_crossing is None
            and record.mode_before is D021Mode.AWAY
            and shadow_battery / capacity_j < EXP003_B50_ENTER_SEEK_THRESHOLD
        ):
            first_crossing = record.transition_index
            cumulative_before_crossing = cumulative_incidental_j
        if actual_seek_entry == record.transition_index:
            cumulative_before_actual = cumulative_incidental_j
        if record.transition_index in active_transition_indices:
            cumulative_incidental_j += _accepted_stored_charge_j(
                telemetry, dt_seconds
            )

    if actual_seek_entry is None:
        cumulative_before_actual = None
    if first_crossing is None:
        delay_transitions: int | None = None
        delay_seconds: float | None = None
        delay_fraction: float | None = None
    else:
        if actual_seek_entry is None:
            delay_transitions = None
            delay_seconds = None
            delay_fraction = None
        else:
            delay_transitions = actual_seek_entry - first_crossing
            delay_seconds = delay_transitions * dt_seconds
            actual_seconds = actual_seek_entry * dt_seconds
            delay_fraction = delay_seconds / actual_seconds
    return {
        "actual_first_low_energy_seek_entry_transition": actual_seek_entry,
        "open_loop_no_incidental_threshold_crossing_transition": first_crossing,
        "threshold_shift_transitions": delay_transitions,
        "threshold_shift_seconds": delay_seconds,
        "threshold_shift_fraction_of_actual_time_to_seek": delay_fraction,
        "cumulative_incidental_accepted_charge_before_shadow_crossing_j": (
            cumulative_before_crossing
        ),
        "cumulative_incidental_accepted_charge_before_actual_seek_entry_j": (
            cumulative_before_actual
        ),
        "cumulative_incidental_charge_fraction_of_capacity_before_shadow_crossing": (
            None
            if cumulative_before_crossing is None
            else cumulative_before_crossing / capacity_j
        ),
        "cumulative_incidental_charge_fraction_of_capacity_before_actual_seek_entry": (
            None
            if cumulative_before_actual is None
            else cumulative_before_actual / capacity_j
        ),
        "shadow_clamp_required": clamp_required,
        "shadow_clamp_transition_count": clamp_count,
        "shadow_validity": (
            "earliest threshold crossing along the fixed realized history "
            "through the actual first SEEK entry; not an autonomous counterfactual"
        ),
    }


def analyze_d021_trace(
    trace: Sequence[D021TransitionTrace],
    *,
    seed: int,
    expected_d021_accidental_away_contacts: int | None = None,
) -> dict[str, object]:
    """Analyze one completed D-021 trace without changing or rerunning it."""
    _validate_trace(trace)
    config = D020PhysicalConfig()
    episodes, active_transition_indices = _classify_episodes(trace)
    mode_charge_totals = {mode.name: 0.0 for mode in D021Mode}
    total_lifetime_charge_j = 0.0
    for record in trace:
        accepted_j = _accepted_stored_charge_j(record.telemetry, config.dt_seconds)
        mode_charge_totals[record.mode_before.name] += accepted_j
        total_lifetime_charge_j += accepted_j

    incidental_charge_j = sum(
        _float_value(episode["gross_accepted_stored_charge_j"], "episode charge")
        for episode in episodes
    )
    incidental_contact_transitions = sum(
        _int_value(episode["contact_active_transitions"], "active transitions")
        for episode in episodes
    )
    durations = [
        _float_value(episode["contact_active_seconds"], "active seconds")
        for episode in episodes
    ]
    away_charge_j = mode_charge_totals[D021Mode.AWAY.name]
    unmatched_away_charge_j = sum(
        _accepted_stored_charge_j(record.telemetry, config.dt_seconds)
        for record in trace
        if record.mode_before is D021Mode.AWAY
        and record.transition_index not in active_transition_indices
    )
    mode_charge_sum_j = sum(mode_charge_totals.values())
    actual_seek_entry = _first_seek_entry(trace)
    shadow = _shadow_metrics(
        trace,
        active_transition_indices,
        actual_seek_entry,
        config.battery_capacity_j,
        config.dt_seconds,
    )
    episode_count_matches_source = (
        expected_d021_accidental_away_contacts is None
        or len(episodes) == expected_d021_accidental_away_contacts
    )
    return {
        "seed": seed,
        "total_lifetime_transitions": len(trace),
        "total_simulated_seconds": len(trace) * config.dt_seconds,
        "number_of_incidental_away_contact_episodes": len(episodes),
        "d021_accepted_accidental_away_contacts": (
            expected_d021_accidental_away_contacts
        ),
        "incidental_contact_active_transitions": incidental_contact_transitions,
        "incidental_contact_active_seconds": sum(durations),
        "mean_episode_duration_seconds": mean(durations) if durations else 0.0,
        "median_episode_duration_seconds": median(durations) if durations else 0.0,
        "maximum_episode_duration_seconds": max(durations) if durations else 0.0,
        "total_incidental_accepted_stored_charge_j": incidental_charge_j,
        "mean_incidental_accepted_charge_per_episode_j": (
            incidental_charge_j / len(episodes) if episodes else 0.0
        ),
        "maximum_incidental_accepted_charge_per_episode_j": max(
            (
                _float_value(
                    episode["gross_accepted_stored_charge_j"], "episode charge"
                )
                for episode in episodes
            ),
            default=0.0,
        ),
        "total_lifetime_accepted_stored_charge_j": total_lifetime_charge_j,
        "incidental_fraction_of_all_accepted_stored_charge": (
            incidental_charge_j / total_lifetime_charge_j
            if total_lifetime_charge_j > 0.0
            else 0.0
        ),
        "incidental_charge_fraction_of_battery_capacity": (
            incidental_charge_j / config.battery_capacity_j
        ),
        "accepted_stored_charge_j_by_mode_before": mode_charge_totals,
        "total_net_battery_change_across_incidental_contact_active_portions_j": sum(
            _float_value(episode["net_battery_change_j"], "episode net change")
            for episode in episodes
        ),
        "unmatched_away_accepted_charge_j": unmatched_away_charge_j,
        "away_accepted_charge_j": away_charge_j,
        "total_incidental_charging_body_heat_energy_j": sum(
            _float_value(episode["charging_body_heat_energy_j"], "episode heat")
            for episode in episodes
        ),
        "actual_first_low_energy_seek_entry_transition": actual_seek_entry,
        "actual_first_physical_seek_reacquisition_transition": _first_reacquisition(
            trace
        ),
        "completed_cycle_count": _completed_cycles(
            trace, config.battery_capacity_j
        ),
        "final_normalized_energy": trace[-1].observation[0],
        "termination_or_truncation_reason": _termination_reason(trace),
        "episode_lifetime_reconciliation": {
            "mode_charge_sum_j": mode_charge_sum_j,
            "total_lifetime_charge_j": total_lifetime_charge_j,
            "difference_j": mode_charge_sum_j - total_lifetime_charge_j,
            "tolerance_j": D022_CHARGE_TOLERANCE_J,
            "matches_within_tolerance": math.isclose(
                mode_charge_sum_j,
                total_lifetime_charge_j,
                rel_tol=0.0,
                abs_tol=D022_CHARGE_TOLERANCE_J,
            ),
        },
        "away_reconciliation": {
            "classified_incidental_away_charge_j": incidental_charge_j,
            "unmatched_away_charge_j": unmatched_away_charge_j,
            "sum_of_categories_j": incidental_charge_j + unmatched_away_charge_j,
            "total_away_charge_j": away_charge_j,
            "difference_j": (
                incidental_charge_j + unmatched_away_charge_j - away_charge_j
            ),
            "tolerance_j": D022_CHARGE_TOLERANCE_J,
            "matches_within_tolerance": math.isclose(
                incidental_charge_j + unmatched_away_charge_j,
                away_charge_j,
                rel_tol=0.0,
                abs_tol=D022_CHARGE_TOLERANCE_J,
            ),
        },
        "d021_contact_count_reconciliation": {
            "derived_episode_count": len(episodes),
            "accepted_d021_count": expected_d021_accidental_away_contacts,
            "matches": episode_count_matches_source,
        },
        "shadow": shadow,
        "episodes": list(episodes),
    }


def _validate_sha(value: str | None) -> str | None:
    if value is None:
        return None
    if re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise ValueError(
            "implementation_audit_sha must be a 40-character lowercase SHA"
        )
    return value


def run_d022_audit(implementation_audit_sha: str | None = None) -> dict[str, object]:
    """Replay exactly the accepted D-021 lifetimes and return compact audits."""
    implementation_sha = _validate_sha(implementation_audit_sha)
    results: list[dict[str, object]] = []
    for seed in D021_DEFAULT_DEVELOPMENT_SEEDS:
        trace = run_d021_lifetime_trace(seed=seed, horizon=D021_HORIZON)
        result = analyze_d021_trace(
            trace,
            seed=seed,
            expected_d021_accidental_away_contacts=(
                D022_ACCEPTED_D021_AWAY_CONTACT_COUNTS[seed]
            ),
        )
        reconciliation = result["d021_contact_count_reconciliation"]
        if not isinstance(reconciliation, dict) or not reconciliation["matches"]:
            raise RuntimeError(
                "D-022 episode count does not reconcile with accepted D-021 "
                f"accidental_away_contacts for seed {seed}"
            )
        results.append(result)

    incidental_fractions = [
        _float_value(
            result["incidental_fraction_of_all_accepted_stored_charge"],
            "incidental fraction",
        )
        for result in results
    ]
    capacity_fractions = [
        _float_value(
            result["incidental_charge_fraction_of_battery_capacity"],
            "capacity fraction",
        )
        for result in results
    ]
    shifts = [
        _float_value(shadow["threshold_shift_seconds"], "threshold shift")
        for result in results
        for shadow in [_mapping_value(result["shadow"], "shadow")]
        if shadow["threshold_shift_seconds"] is not None
    ]
    return {
        "schema_version": D022_SCHEMA_VERSION,
        "experiment": "D-022",
        "title": "Incidental charging contribution audit",
        "lane": "Development",
        "authoritative_base_sha": D022_AUTHORITATIVE_BASE_SHA,
        "implementation_audit_sha": implementation_sha,
        "source_experiment": "D-021",
        "source_seeds": list(D021_DEFAULT_DEVELOPMENT_SEEDS),
        "source_horizon": D021_HORIZON,
        "source_trace_runner": "run_d021_lifetime_trace",
        "timestep_seconds": D020PhysicalConfig().dt_seconds,
        "programmed": {
            "new_organism_behavior": False,
            "accepted_d021_controller_and_d020_physics_replayed_unchanged": True,
            "evaluator_audit_definitions_only": True,
        },
        "organism_visible": {
            "unchanged_d021_six_channels": [
                "normalized battery",
                "beacon left",
                "beacon forward",
                "beacon right",
                "charging contact",
                "normalized own temperature",
            ]
        },
        "evaluator_only": {
            "fields": [
                "completed mode/action trace",
                "absolute joules and electrical power",
                "charger phase",
                "physical contact transitions",
                "episode classifications",
                "charge attribution",
                "open-loop ledger shadow",
                "charging body heat decomposition",
            ],
            "passed_to_controller": False,
        },
        "learned": {"status": "none"},
        "organism_boundary": {"reward": 0.0, "info": {}},
        "freeze": {
            "source_seeds": list(D021_DEFAULT_DEVELOPMENT_SEEDS),
            "source_horizon": D021_HORIZON,
            "episode_entry": (
                "mode_before == AWAY; ordinary pre-action normalized energy >= "
                "0.50; charging_contact_before == False; "
                "charging_contact_after == True"
            ),
            "contact_active_transition": (
                "active episode and mode_before == AWAY and "
                "charging_contact_after == True"
            ),
            "normal_episode_exit": (
                "charging_contact_before == True and "
                "charging_contact_after == False; exit transition recorded but "
                "not counted as active"
            ),
            "accepted_stored_charge_formula": (
                "telemetry.actual_stored_power_w * dt_seconds"
            ),
            "electrical_load_formula": (
                "telemetry.total_electrical_load_w * dt_seconds"
            ),
            "reconciliation_tolerance_j": D022_CHARGE_TOLERANCE_J,
            "shadow": (
                "before each realized transition subtract cumulative prior "
                "classified incidental accepted charge from telemetry battery "
                "before; find earliest realized AWAY state below 0.50; stop "
                "at actual first low-energy SEEK entry"
            ),
        },
        "results": results,
        "aggregate": {
            "total_incidental_episode_count": sum(
                _int_value(
                    result["number_of_incidental_away_contact_episodes"],
                    "episode count",
                )
                for result in results
            ),
            "total_incidental_contact_seconds": sum(
                _float_value(
                    result["incidental_contact_active_seconds"], "active seconds"
                )
                for result in results
            ),
            "total_incidental_accepted_stored_charge_j": sum(
                _float_value(
                    result["total_incidental_accepted_stored_charge_j"],
                    "incidental charge",
                )
                for result in results
            ),
            "mean_per_seed_incidental_fraction_of_all_accepted_charge": mean(
                incidental_fractions
            ),
            "median_per_seed_incidental_fraction_of_all_accepted_charge": median(
                incidental_fractions
            ),
            "range_per_seed_incidental_fraction_of_all_accepted_charge": [
                min(incidental_fractions),
                max(incidental_fractions),
            ],
            "mean_per_seed_incidental_charge_capacity_fraction": mean(
                capacity_fractions
            ),
            "median_per_seed_incidental_charge_capacity_fraction": median(
                capacity_fractions
            ),
            "range_per_seed_incidental_charge_capacity_fraction": [
                min(capacity_fractions),
                max(capacity_fractions),
            ],
            "range_open_loop_threshold_shift_seconds": [
                min(shifts) if shifts else None,
                max(shifts) if shifts else None,
            ],
            "all_three_same_qualitative_magnitude_pattern": (
                all(value > 0.0 for value in incidental_fractions)
                and all(value is not None for value in shifts)
            ),
        },
        "interpretation_boundary": {
            "development_only": True,
            "shadow_is_not_behavioral_counterfactual": True,
            "no_ecology_or_controller_change": True,
            "no_d023_authorized": True,
        },
    }


def write_d022_json(path: Path, implementation_audit_sha: str | None = None) -> Path:
    """Write the deterministic compact D-022 audit artifact."""
    payload = run_d022_audit(implementation_audit_sha)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--implementation-audit-sha")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    write_d022_json(args.output, args.implementation_audit_sha)
    print(f"D-022 audit written to {args.output}")


if __name__ == "__main__":
    main()
