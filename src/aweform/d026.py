"""D-026 one-third false-contact SEEK delegation development probe.

This module reuses the D-025 runner and diagnostics while changing exactly one
programmed parameter: false-contact SEEK delegation to the existing stochastic
explorer is fixed at one third.  The explorer's internal hazard, environment,
observation/action boundary, and all non-SEEK behavior remain unchanged.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Final, Sequence, cast

from . import d024, d025
from .d020 import D020PhysicalConfig
from .exp001 import EXP001_EXPLORER_HAZARD
from .exp003_seed_policy import validate_exp003_development_seeds

D026_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = tuple(range(18368, 18388))
D026_CANONICAL_VISUALIZATION_SEED: Final[int] = D026_DEFAULT_DEVELOPMENT_SEEDS[0]
D026_HORIZON: Final[int] = 70_000
D026_SEEK_DELEGATION_PROBABILITY: Final[float] = 1.0 / 3.0
D026_AUTHORITATIVE_BASE_SHA: Final[str] = (
    "355e8add42e54db28f0a69af1cf750a442c5d480"
)
D024_COMPARATOR_IMPLEMENTATION_SHA: Final[str] = (
    d025.D024_COMPARATOR_IMPLEMENTATION_SHA
)

D026Mode = d025.D025Mode
D026Observation = d025.D025Observation
D026TransitionTrace = d025.D025TransitionTrace


class D026Controller(d025.D025Controller):
    """D-025 controller with only the authorized one-third delegation rate."""

    seek_delegation_probability = D026_SEEK_DELEGATION_PROBABILITY


class D026Env(d025.D025Env):
    """D-024 environment with unchanged physical and contact semantics."""


def _validate_d026_development_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    """Apply the canonical reservation guard and exact D-026 seed guard."""
    validated = validate_exp003_development_seeds(seeds)
    if validated != D026_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-026 requires exactly the frozen development seeds "
            f"{D026_DEFAULT_DEVELOPMENT_SEEDS}; got {validated}"
        )
    return validated


def _validate_d026_seed(seed: int) -> None:
    validated = validate_exp003_development_seeds((seed,))
    if validated[0] not in D026_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-026 may execute only predeclared development seeds "
            f"{D026_DEFAULT_DEVELOPMENT_SEEDS}; got {validated}"
        )


def _compact_result(result: dict[str, object]) -> dict[str, object]:
    """Retain D-025 diagnostics while omitting the unneeded raw draw log."""
    compact = dict(result)
    arbitration = dict(cast(dict[str, object], compact["seek_arbitration"]))
    records = arbitration.pop("decision_records")
    arbitration.update(
        {
            "delegation_probability": D026_SEEK_DELEGATION_PROBABILITY,
            "delegation_probability_expression": "1.0 / 3.0",
            "decision_record_count": len(cast(list[object], records)),
            "decision_records_retained": False,
        }
    )
    compact["seek_arbitration"] = arbitration
    compact["explorer_internal_hazard"] = EXP001_EXPLORER_HAZARD
    compact["explorer_internal_hazard_expression"] = "1.0 / 8.0"
    return compact


def _run_d026_seed(
    seed: int,
    *,
    horizon: int = D026_HORIZON,
    trace: list[D026TransitionTrace] | None = None,
) -> dict[str, object]:
    """Run one exact-pose, uninterrupted D-026 lifetime."""
    _validate_d026_seed(seed)
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon <= 0:
        raise ValueError("horizon must be a positive integer")
    result = d025._run_d025_seed(
        seed,
        horizon=horizon,
        trace=trace,
        seed_validator=_validate_d026_seed,
        controller_factory=D026Controller,
        comparator_seed_validator=_validate_d026_seed,
    )
    return _compact_result(result)


def _nearest_rank(values: Sequence[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(percentile * len(ordered)))
    return ordered[rank - 1]


def _aggregate_results(results: Sequence[dict[str, object]]) -> dict[str, object]:
    counts = {
        classification: sum(
            int(result["outcome_classification"] == classification)
            for result in results
        )
        for classification in (
            "SEEK_REACQUIRED",
            "FULL_CYCLE",
            "FAILED_SEEK",
            "HORIZON_CENSORED",
        )
    }
    resolved_latencies: list[float] = []
    reacquisition_energies: list[float] = []
    for result in results:
        for episode in cast(list[dict[str, object]], result["seek_episodes"]):
            if episode["outcome"] != "reacquired":
                continue
            resolved_latencies.append(
                cast(float, episode["transitions_since_seek_entry"])
            )
            reacquisition_energies.append(
                cast(float, episode["energy_at_reacquisition"])
            )
    thermal_or_energy_reasons = {
        "energy_depletion",
        "protective_thermal_shutdown",
        "emergency_hard_thermal_shutdown",
    }
    termination_count = sum(
        int(result["termination_reason"] in thermal_or_energy_reasons)
        for result in results
    )
    return {
        "classification_counts": counts,
        "resolved_seek_count": len(resolved_latencies),
        "resolved_seek_latency_decisions": {
            "mean": statistics.fmean(resolved_latencies)
            if resolved_latencies
            else None,
            "median": statistics.median(resolved_latencies)
            if resolved_latencies
            else None,
            "p90_nearest_rank": _nearest_rank(resolved_latencies, 0.90),
            "p95_nearest_rank": _nearest_rank(resolved_latencies, 0.95),
            "maximum": max(resolved_latencies, default=None),
            "percentile_method": "nearest-rank",
        },
        "energy_at_reacquisition": {
            "mean": statistics.fmean(reacquisition_energies)
            if reacquisition_energies
            else None,
            "median": statistics.median(reacquisition_energies)
            if reacquisition_energies
            else None,
            "minimum": min(reacquisition_energies, default=None),
        },
        "energy_or_thermal_termination_count": termination_count,
        "outlier_handling": {
            "excluded_seed_count": 0,
            "statement": (
                "All per-seed outcomes are retained; no outlier is discarded "
                "from the descriptive aggregate."
            ),
        },
    }


def run_d026_lifetime_trace(
    seed: int = D026_CANONICAL_VISUALIZATION_SEED,
    *,
    horizon: int = D026_HORIZON,
) -> tuple[D026TransitionTrace, ...]:
    """Run one exact-horizon D-026 lifetime for deterministic replay."""
    _validate_d026_seed(seed)
    if horizon != D026_HORIZON:
        raise ValueError(
            "D-026 visualization requires the frozen 70,000-transition horizon"
        )
    trace: list[D026TransitionTrace] = []
    _run_d026_seed(seed, horizon=horizon, trace=trace)
    if not trace:
        raise RuntimeError("D-026 lifetime trace contains no completed transitions")
    return tuple(trace)


def run_d026_probe(executed_commit_sha: str | None = None) -> dict[str, object]:
    """Run exactly the 20 frozen D-026 development lifetimes."""
    seeds = _validate_d026_development_seeds(D026_DEFAULT_DEVELOPMENT_SEEDS)
    executed_sha = d025._validate_executed_commit_sha(executed_commit_sha)
    results = [_run_d026_seed(seed, horizon=D026_HORIZON) for seed in seeds]
    return {
        "schema_version": 1,
        "experiment": "D-026",
        "title": "One-third SEEK delegation stabilization",
        "authoritative_base_sha": D026_AUTHORITATIVE_BASE_SHA,
        "implementation_probe_sha": executed_sha,
        "development_seeds": list(seeds),
        "horizon": D026_HORIZON,
        "timestep_seconds": D020PhysicalConfig().dt_seconds,
        "simulated_duration_seconds": D026_HORIZON * D020PhysicalConfig().dt_seconds,
        "lifetime": "one uninterrupted causal lifetime per seed",
        "seed_policy": {
            "canonical_validator": "validate_exp003_development_seeds",
            "exact_declared_seeds": list(D026_DEFAULT_DEVELOPMENT_SEEDS),
            "formal_reservation_guard_preserved": True,
        },
        "freeze": {
            "controller": (
                "D021Controller semantics outside authorized false-contact SEEK "
                "arbitration"
            ),
            "environment": "D024Env and D-024 exact initial state unchanged",
            "horizon": D026_HORIZON,
            "initial_station_center": list(d024.D024_STATION_CENTER),
            "initial_body_center": list(d024.D024_INITIAL_BODY_CENTER),
            "initial_heading": d024.D024_INITIAL_HEADING,
            "initial_battery_j": d024.D024_INITIAL_BATTERY_J,
            "initial_temperature_c": d024.D024_INITIAL_TEMPERATURE_C,
            "initial_latch": False,
            "initial_controller_mode": D026Mode.CHARGE.name,
            "body_length": d024.D024_BODY_LENGTH,
            "body_width": d024.D024_BODY_WIDTH,
            "body_rear_contacts_body_frame": [
                [d024.D024_REAR_X, d024.D024_CONTACT_LATERAL_OFFSET],
                [d024.D024_REAR_X, -d024.D024_CONTACT_LATERAL_OFFSET],
            ],
            "dock_orientation": d024.D024_DOCK_ORIENTATION,
            "dock_contacts_station_offsets": [
                [0.0, d024.D024_CONTACT_LATERAL_OFFSET],
                [0.0, -d024.D024_CONTACT_LATERAL_OFFSET],
            ],
            "contact_tolerance_inclusive": d024.D024_CONTACT_TOLERANCE,
            "delegation_probability": D026_SEEK_DELEGATION_PROBABILITY,
            "delegation_probability_expression": "1.0 / 3.0",
            "explorer_internal_hazard": EXP001_EXPLORER_HAZARD,
            "explorer_internal_hazard_expression": "1.0 / 8.0",
            "one_policy_rng_draw_per_false_contact_seek_decision": True,
            "policy_rng": (
                "RandomStreams.from_seed(seed).policy, continuous; no reseed/new "
                "stream"
            ),
            "begin_segment": "once on SEEK entry; no reseed and no RNG consumption",
            "event_definitions_frozen": True,
        },
        "programmed": {
            "controller_modes": [mode.name for mode in D026Mode],
            "controller": (
                "fixed non-learning D-021 controller with D-026 SEEK arbitration"
            ),
            "non_seek_behavior": "D-021 unchanged",
            "greedy_default": "existing seek_beacon_action",
            "delegation": (
                "false-contact SEEK only; existing StochasticPersistentExplorer"
            ),
            "learning": False,
        },
        "organism_visible": {
            "observation_type": "D011Observation projection of D020's six channels",
            "channels": [
                "normalized own battery energy",
                "beacon left",
                "beacon forward",
                "beacon right",
                "charging_contact as binary dual-contact predicate",
                "normalized own body temperature",
            ],
            "temperature_used_for_behavior": False,
        },
        "evaluator_only": {
            "fields": [
                "pose, heading, station/dock geometry, pair errors",
                "greedy and actual arbitration labels and RNG draws",
                "delegation/effective-perturbation labels",
                "charger telemetry and event classifications",
                "prefix comparisons and scientific metrics",
            ],
            "passed_to_controller_except_visible_beacon_and_policy_rng": False,
        },
        "learned": {"status": "none"},
        "inferred": {
            "interpretation": "descriptive bounded-development observation only",
            "no_pass_threshold": True,
            "no_claim_of_robustness_or_general_sufficiency": True,
            "no_claim_that_one_third_is_optimal": True,
        },
        "organism_boundary": {"reward": 0.0, "info": {}},
        "aggregate": _aggregate_results(results),
        "results": results,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the D-026 one-third SEEK delegation probe."
    )
    parser.add_argument("--executed-commit-sha")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    payload = json.dumps(
        run_d026_probe(executed_commit_sha=args.executed_commit_sha),
        indent=2,
        sort_keys=True,
    )
    if args.output is None:
        print(payload)
    else:
        args.output.write_text(payload + "\n", encoding="utf-8")
        print(f"D-026 result written to {args.output}")


if __name__ == "__main__":
    main()
