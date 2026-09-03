"""D-023 repeated-cycle V0.4 energy-regulation endurance probe.

This module reuses the D-021 fixed controller and lifetime runner unchanged.
It only freezes a three-times-longer observation window and adds compact
evaluator-side cycle and prefix-invariance reporting.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import replace
from pathlib import Path
from typing import Final, Sequence, cast

from . import d021
from .d020 import D020PhysicalConfig
from .d021 import D021Mode, D021TransitionTrace
from .exp003 import EXP003_B50_ENTER_SEEK_THRESHOLD
from .exp003_seed_policy import validate_exp003_development_seeds

D023_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = (
    18365,
    18366,
    18367,
)
D023_HORIZON: Final[int] = 3 * d021.D021_HORIZON
D023_AUTHORITATIVE_BASE_SHA: Final[str] = (
    "a7c66a8bc096baf61b50bc3963b6cf19a6d38f83"
)
D023_SCHEMA_VERSION: Final[int] = 1


def _validate_d023_development_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    """Apply the canonical reservation guard and frozen D-023 seed set."""
    validated = validate_exp003_development_seeds(seeds)
    if validated != D023_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-023 requires exactly the frozen development seeds "
            f"{D023_DEFAULT_DEVELOPMENT_SEEDS}; got {validated}"
        )
    return validated


def _validate_executed_commit_sha(value: str | None) -> str | None:
    if value is None:
        return None
    if re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise ValueError("executed_commit_sha must be a 40-character lowercase SHA")
    return value


def _same_causal_transition(
    d023_record: D021TransitionTrace,
    d021_record: D021TransitionTrace,
) -> bool:
    """Compare all causal trace fields, exempting only D-021 final truncation."""
    if d021_record.transition_index != d021.D021_HORIZON:
        return d023_record == d021_record

    # D-021's 70,000-transition harness labels its final step truncated.  The
    # uninterrupted D-023 lifetime necessarily continues at that same step.
    expected_telemetry = replace(d021_record.telemetry, truncated=False)
    actual_telemetry = replace(d023_record.telemetry, truncated=False)
    return replace(d021_record, telemetry=expected_telemetry) == replace(
        d023_record, telemetry=actual_telemetry
    )


def _prefix_invariance_report(
    d023_trace: Sequence[D021TransitionTrace],
    d021_trace: Sequence[D021TransitionTrace],
) -> dict[str, object]:
    """Return a compact exact causal comparison for the required prefix."""
    if len(d023_trace) < d021.D021_HORIZON:
        raise RuntimeError("D-023 trace is shorter than the required D-021 prefix")
    if len(d021_trace) != d021.D021_HORIZON:
        raise RuntimeError("D-021 reference trace did not reach its frozen horizon")

    mismatches: list[int] = []
    for d023_record, d021_record in zip(
        d023_trace[: d021.D021_HORIZON], d021_trace, strict=True
    ):
        if not _same_causal_transition(d023_record, d021_record):
            mismatches.append(d021_record.transition_index)

    return {
        "matched": not mismatches,
        "compared_transitions": d021.D021_HORIZON,
        "mismatch_count": len(mismatches),
        "mismatch_transition_indices": mismatches[:5],
        "ignored_only": ["D-021 final telemetry.truncated harness label"],
    }


def _cycle_summaries(trace: Sequence[D021TransitionTrace]) -> list[dict[str, object]]:
    """Summarize complete and horizon-censored regulation cycles."""
    cycles: list[dict[str, object]] = []
    active: dict[str, object] | None = None
    stage = 0
    previous_latched = False
    battery_capacity_j = D020PhysicalConfig().battery_capacity_j

    for record in trace:
        telemetry = record.telemetry
        if (
            record.mode_before is D021Mode.CHARGE
            and record.mode_after is D021Mode.DEPART
        ):
            if active is not None and stage == 5:
                active["post_recharge_redeparture_transition"] = (
                    record.transition_index
                )
                active["status"] = "completed"
                cycles.append(active)
                active = None
                stage = 0
            elif active is not None:
                active["status"] = "unexpected_departure"
                cycles.append(active)
            if active is None:
                active = {
                    "cycle_index": len(cycles) + 1,
                    "status": "horizon_censored",
                    "initial_or_post_recharge_departure_transition": (
                        record.transition_index
                    ),
                    "cycle_relevant_charger_exit_transition": None,
                    "low_energy_seek_entry_transition": None,
                    "physical_seek_reacquisition_transition": None,
                    "full_recharge_transition": None,
                    "post_recharge_redeparture_transition": None,
                }
                stage = 1

        if active is not None:
            if (
                stage == 1
                and telemetry.charging_contact_before
                and not telemetry.charging_contact_after
            ):
                active["cycle_relevant_charger_exit_transition"] = (
                    record.transition_index
                )
                stage = 2
            elif (
                stage == 2
                and record.mode_before is D021Mode.AWAY
                and record.mode_after is D021Mode.SEEK
            ):
                active["low_energy_seek_entry_transition"] = record.transition_index
                stage = 3
            elif (
                stage == 3
                and record.mode_before is D021Mode.SEEK
                and not telemetry.charging_contact_before
                and telemetry.charging_contact_after
            ):
                active["physical_seek_reacquisition_transition"] = (
                    record.transition_index
                )
                stage = 4
            elif (
                stage == 4
                and not previous_latched
                and telemetry.charger_termination_latched_after
                and telemetry.battery_after_j >= battery_capacity_j
            ):
                active["full_recharge_transition"] = record.transition_index
                stage = 5

        previous_latched = telemetry.charger_termination_latched_after

    if active is not None:
        cycles.append(active)
    return cycles


def _run_d023_seed(
    seed: int,
    *,
    horizon: int = D023_HORIZON,
    verify_prefix: bool = False,
) -> dict[str, object]:
    """Run one continuous D-021 lifetime at the D-023 observation window."""
    trace: list[D021TransitionTrace] = []
    result = d021._run_seed(seed, horizon=horizon, trace=trace)
    cycles = _cycle_summaries(trace)
    seek_episodes = cast(list[dict[str, object]], result["seek_episodes"])
    seek_by_entry = {
        cast(int, episode["seek_entry_transition"]): episode
        for episode in seek_episodes
    }
    for cycle in cycles:
        seek_entry = cast(int | None, cycle["low_energy_seek_entry_transition"])
        cycle["seek_episode"] = (
            seek_by_entry.get(seek_entry) if seek_entry is not None else None
        )

    result["completed_cycle_count"] = result["completed_energy_regulation_cycles"]
    result["cycle_relevant_charger_exits"] = sum(
        cycle["cycle_relevant_charger_exit_transition"] is not None
        for cycle in cycles
    )
    result["cycle_summaries"] = cycles
    if verify_prefix:
        prefix = _prefix_invariance_report(
            trace,
            d021.run_d021_lifetime_trace(seed=seed),
        )
        if not prefix["matched"]:
            raise RuntimeError(f"D-023 prefix invariance failed for seed {seed}")
        result["d021_prefix_invariance"] = prefix
    return result


def run_d023_probe(executed_commit_sha: str | None = None) -> dict[str, object]:
    """Run the exact three uninterrupted D-023 development lifetimes."""
    seeds = _validate_d023_development_seeds(D023_DEFAULT_DEVELOPMENT_SEEDS)
    implementation_sha = _validate_executed_commit_sha(executed_commit_sha)
    results = [
        _run_d023_seed(seed, verify_prefix=True)
        for seed in seeds
    ]
    return {
        "schema_version": D023_SCHEMA_VERSION,
        "experiment": "D-023",
        "title": "Repeated-cycle V0.4 energy-regulation endurance probe",
        "lane": "Development",
        "authoritative_base_sha": D023_AUTHORITATIVE_BASE_SHA,
        "implementation_probe_sha": implementation_sha,
        "development_seeds": list(seeds),
        "horizon": D023_HORIZON,
        "timestep_seconds": D020PhysicalConfig().dt_seconds,
        "simulated_duration_seconds": D023_HORIZON * D020PhysicalConfig().dt_seconds,
        "lifetime": "one uninterrupted lifetime per seed",
        "seed_policy": {
            "canonical_validator": "validate_exp003_development_seeds",
            "exact_declared_seeds": list(D023_DEFAULT_DEVELOPMENT_SEEDS),
            "formal_reservation_guard_preserved": True,
        },
        "freeze": {
            "horizon": "3 * D021_HORIZON",
            "controller": "D021Controller unchanged",
            "physical_config": "D020PhysicalConfig unchanged except episode_horizon",
            "full_energy_threshold": d021.D021_FULL_ENERGY_THRESHOLD,
            "low_energy_seek_threshold": EXP003_B50_ENTER_SEEK_THRESHOLD,
            "exploration_hazard": 1.0 / 8.0,
            "initial_body_position": [0.5, 0.5],
            "initial_station_center": [0.5, 0.5],
            "initial_battery": "D020PhysicalConfig.battery_capacity_j",
            "initial_body_temperature_c": 23.0,
            "initial_charger_termination_latched": False,
            "initial_heading": (
                "RandomStreams.from_seed(seed).environment.uniform(0.0, 2*pi)"
            ),
            "event_definitions_frozen": True,
        },
        "programmed": {
            "controller_modes": [mode.name for mode in D021Mode],
            "controller": "fixed non-learning D021Controller",
            "full_departure_rule": "CHARGE contact and normalized energy >= 1.0",
            "low_energy_seek_rule": "AWAY normalized energy < inherited 0.50 threshold",
            "exploration": "StochasticPersistentExplorer with EXP001 hazard 1/8",
            "seek": "existing seek_beacon_action",
            "thermal_behavioral_influence": "zero",
            "learning": False,
        },
        "organism_visible": {
            "observation_type": "D011Observation projection of D020's six channels",
            "channels": [
                "normalized own battery energy",
                "beacon left",
                "beacon forward",
                "beacon right",
                "charging_contact",
                "normalized own body temperature",
            ],
            "temperature_used_for_behavior": False,
        },
        "evaluator_only": {
            "fields": [
                "x/y/heading after initial setup",
                "station location",
                "true distance",
                "battery joules",
                "absolute Celsius",
                "charger phase/latch",
                "telemetry and event summaries",
                "shutdown reason",
            ],
            "passed_to_controller": False,
        },
        "learned": {"status": "none"},
        "organism_boundary": {"reward": 0.0, "info": {}},
        "results": results,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the D-023 repeated-cycle V0.4 endurance probe."
    )
    parser.add_argument("--executed-commit-sha")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    payload = json.dumps(
        run_d023_probe(executed_commit_sha=args.executed_commit_sha),
        indent=2,
        sort_keys=True,
    )
    if args.output is None:
        print(payload)
    else:
        args.output.write_text(payload + "\n", encoding="utf-8")
        print(f"D-023 result written to {args.output}")


if __name__ == "__main__":
    main()
