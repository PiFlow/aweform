"""D-012 bounded robustness census of the fixed D-011 controller.

This module runs the unchanged D-011 controller and D-002/EXP-003 ecology on
one predeclared block of development seeds.  It adds no organism capability:
the census is evaluator-side aggregation of the per-seed records already
produced by D-011.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from statistics import mean, median
from typing import Final, Sequence, cast

from . import d011
from .exp003_seed_policy import validate_exp003_development_seeds

D012_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = tuple(
    range(18144, 18344)
)
D012_DEVELOPMENT_SEED_RANGE: Final[tuple[int, int]] = (
    D012_DEFAULT_DEVELOPMENT_SEEDS[0],
    D012_DEFAULT_DEVELOPMENT_SEEDS[-1],
)
D012_SEED_COUNT: Final[int] = 200
D012_HORIZON: Final[int] = 1000
D012_AUTHORITATIVE_BASE_SHA: Final[str] = (
    "f39cd664896008e856a2a8b132437a914235f980"
)


def _validate_d012_development_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    """Validate the exact declared D-012 block after the canonical guard."""
    validated = validate_exp003_development_seeds(seeds)
    if validated != D012_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-012 may execute only its exact predeclared 200-seed range "
            f"{D012_DEVELOPMENT_SEED_RANGE}; got {validated}"
        )
    return validated


def _mapping(value: object, *, name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise RuntimeError(f"D-011 field {name} is not a mapping")
    return cast(dict[str, object], value)


def _list(value: object, *, name: str) -> list[object]:
    if not isinstance(value, list):
        raise RuntimeError(f"D-011 field {name} is not a list")
    return value


def _int_field(run: dict[str, object], name: str) -> int:
    value = run.get(name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise RuntimeError(f"D-011 field {name} is not an integer")
    return value


def _bool_field(run: dict[str, object], name: str) -> bool:
    value = run.get(name)
    if not isinstance(value, bool):
        raise RuntimeError(f"D-011 field {name} is not a boolean")
    return value


def _float_field(run: dict[str, object], name: str) -> float:
    value = run.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"D-011 field {name} is not numeric")
    result = float(value)
    if not math.isfinite(result):
        raise RuntimeError(f"D-011 field {name} is not finite")
    return result


def _distribution(values: Sequence[int | float]) -> dict[str, object]:
    if not values:
        return {
            "count": 0,
            "min": None,
            "median": None,
            "mean": None,
            "max": None,
            "frequency": {},
        }
    ordered = sorted(values)
    frequencies: dict[str, int] = {}
    for value in ordered:
        key = str(value)
        frequencies[key] = frequencies.get(key, 0) + 1
    return {
        "count": len(ordered),
        "min": ordered[0],
        "median": float(median(ordered)),
        "mean": float(mean(ordered)),
        "max": ordered[-1],
        "frequency": frequencies,
    }


def _seek_latencies(run: dict[str, object]) -> list[int]:
    latencies: list[int] = []
    for item in _list(run.get("seek_episodes"), name="seek_episodes"):
        episode = _mapping(item, name="seek episode")
        latency = episode.get("transitions_to_reacquisition")
        if latency is None:
            continue
        if isinstance(latency, bool) or not isinstance(latency, int):
            raise RuntimeError("D-011 SEEK latency is not an integer or null")
        if latency < 0:
            raise RuntimeError("D-011 SEEK latency is negative")
        latencies.append(latency)
    return latencies


def _seek_outcome_summary(run: dict[str, object]) -> dict[str, int]:
    """Classify SEEK episodes without treating horizon censoring as failure."""
    resolved = 0
    horizon_censored = 0
    demonstrated_failure = 0
    horizon_censored_lifetime = _bool_field(
        run, "truncated"
    ) and not _bool_field(run, "terminated")
    for item in _list(run.get("seek_episodes"), name="seek_episodes"):
        episode = _mapping(item, name="seek episode")
        reacquisition_transition = episode.get("reacquisition_transition")
        if reacquisition_transition is not None:
            resolved += 1
        elif horizon_censored_lifetime:
            horizon_censored += 1
        else:
            demonstrated_failure += 1
    return {
        "resolved": resolved,
        "horizon_censored": horizon_censored,
        "demonstrated_failure": demonstrated_failure,
    }


def _compact_d011_result(run: dict[str, object]) -> dict[str, object]:
    """Keep D-011 summaries while omitting its large per-transition geometry log."""
    compacted = dict(run)
    navigation = _mapping(
        run.get("evaluator_only_navigation"),
        name="evaluator_only_navigation",
    )
    compact_navigation = dict(navigation)
    compact_navigation.pop("seek_distance_trajectory", None)
    compacted["evaluator_only_navigation"] = compact_navigation
    compacted["seek_outcome_summary"] = _seek_outcome_summary(run)
    return compacted


def _aggregate(results: Sequence[dict[str, object]]) -> dict[str, object]:
    seed_count = len(results)
    transitions = [_int_field(run, "transitions") for run in results]
    surviving = [
        _bool_field(run, "truncated") and not _bool_field(run, "terminated")
        for run in results
    ]
    energy_failures = sum(
        _bool_field(run, "energy_termination") for run in results
    )
    thermal_failures = sum(
        _bool_field(run, "thermal_termination") for run in results
    )
    any_failures = sum(
        _bool_field(run, "energy_termination")
        or _bool_field(run, "thermal_termination")
        for run in results
    )
    both_failures = sum(
        _bool_field(run, "energy_termination")
        and _bool_field(run, "thermal_termination")
        for run in results
    )
    cycle_counts = [
        _int_field(run, "completed_autonomous_regulation_cycles")
        for run in results
    ]
    low_energy_seek_entries = [
        _int_field(run, "low_energy_seek_entries") for run in results
    ]
    successful_reacquisitions = [
        _int_field(run, "successful_charging_contact_reacquisitions")
        for run in results
    ]
    minimum_raw_energy = [
        _float_field(run, "minimum_energy") for run in results
    ]
    minimum_normalized_energy = [
        _float_field(run, "minimum_normalized_energy") for run in results
    ]
    maximum_thermal = [
        _float_field(run, "maximum_thermal_state") for run in results
    ]

    action_totals: dict[str, int] = {}
    mode_totals: dict[str, int] = {}
    mode_entry_totals: dict[str, int] = {}
    all_seek_latencies: list[int] = []
    seek_outcome_totals = {
        "resolved": 0,
        "horizon_censored": 0,
        "demonstrated_failure": 0,
    }
    for run in results:
        action_counts = _mapping(run.get("action_counts"), name="action_counts")
        for name, value in action_counts.items():
            if isinstance(value, bool) or not isinstance(value, int):
                raise RuntimeError("D-011 action count is not an integer")
            action_totals[name] = action_totals.get(name, 0) + value
        for source, target in (
            ("mode_occupancy", mode_totals),
            ("mode_entry_counts", mode_entry_totals),
        ):
            for name, value in _mapping(run.get(source), name=source).items():
                if isinstance(value, bool) or not isinstance(value, int):
                    raise RuntimeError(f"D-011 {source} value is not an integer")
                target[name] = target.get(name, 0) + value
        all_seek_latencies.extend(_seek_latencies(run))
        for outcome, count in _seek_outcome_summary(run).items():
            seek_outcome_totals[outcome] += count

    total_transitions = sum(transitions)
    total_low_energy_seek_entries = sum(low_energy_seek_entries)
    total_successful_reacquisitions = sum(successful_reacquisitions)
    resolved_seek_episode_count = (
        seek_outcome_totals["resolved"]
        + seek_outcome_totals["demonstrated_failure"]
    )
    resolved_seek_success_rate: float | None = None
    if resolved_seek_episode_count:
        resolved_seek_success_rate = (
            total_successful_reacquisitions / resolved_seek_episode_count
        )

    return {
        "seed_count": seed_count,
        "surviving_to_horizon_count": sum(surviving),
        "surviving_to_horizon_proportion": (
            sum(surviving) / seed_count if seed_count else 0.0
        ),
        "energy_failure_count": energy_failures,
        "thermal_failure_count": thermal_failures,
        "combined_failure_count": any_failures,
        "both_energy_and_thermal_failure_count": both_failures,
        "completed_cycles": _distribution(cycle_counts),
        "seeds_with_at_least_one_completed_cycle": sum(
            count >= 1 for count in cycle_counts
        ),
        "proportion_with_at_least_one_completed_cycle": (
            sum(count >= 1 for count in cycle_counts) / seed_count
            if seed_count
            else 0.0
        ),
        "low_energy_seek_entry_count": total_low_energy_seek_entries,
        "successful_reacquisition_count": total_successful_reacquisitions,
        "horizon_censored_seek_seed_count": sum(
            _seek_outcome_summary(run)["horizon_censored"] > 0
            for run in results
        ),
        "total_horizon_censored_seek_episodes": seek_outcome_totals[
            "horizon_censored"
        ],
        "demonstrated_failed_seek_seed_count": sum(
            _seek_outcome_summary(run)["demonstrated_failure"] > 0
            for run in results
        ),
        "total_demonstrated_failed_seek_episodes": seek_outcome_totals[
            "demonstrated_failure"
        ],
        "resolved_seek_episode_count": resolved_seek_episode_count,
        "resolved_seek_success_count": total_successful_reacquisitions,
        "resolved_seek_success_rate": resolved_seek_success_rate,
        "minimum_of_minimum_raw_energy": min(minimum_raw_energy),
        "minimum_of_minimum_normalized_energy": min(minimum_normalized_energy),
        "median_minimum_raw_energy": float(median(minimum_raw_energy)),
        "median_minimum_normalized_energy": float(
            median(minimum_normalized_energy)
        ),
        "maximum_observed_thermal_state": max(maximum_thermal),
        "seek_to_reacquisition_transition_counts": _distribution(
            all_seek_latencies
        ),
        "total_transitions": total_transitions,
        "action_totals": action_totals,
        "action_proportions": {
            name: count / total_transitions
            for name, count in action_totals.items()
        },
        "mode_occupancy_totals": mode_totals,
        "mode_occupancy_proportions": {
            name: count / total_transitions
            for name, count in mode_totals.items()
        },
        "mode_entry_totals": mode_entry_totals,
    }


def _validate_executed_commit_sha(value: str | None) -> str | None:
    if value is None:
        return None
    if re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise ValueError("executed_commit_sha must be a 40-character lowercase SHA")
    return value


def run_d012_census(
    seeds: Sequence[int] = D012_DEFAULT_DEVELOPMENT_SEEDS,
    *,
    horizon: int = D012_HORIZON,
    executed_commit_sha: str | None = None,
) -> dict[str, object]:
    """Run the unchanged D-011 full loop once per declared development seed."""
    development_seeds = _validate_d012_development_seeds(seeds)
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon <= 0:
        raise ValueError("horizon must be a positive integer")
    executed_sha = _validate_executed_commit_sha(executed_commit_sha)
    results = [
        d011._run_seed(seed, horizon=horizon) for seed in development_seeds
    ]
    return {
        "schema_version": 1,
        "experiment": "D-012",
        "title": "D-011 broad-seed robustness census",
        "authoritative_base_sha": D012_AUTHORITATIVE_BASE_SHA,
        "executed_commit_sha": executed_sha,
        "development_seeds": list(development_seeds),
        "development_seed_range": list(D012_DEVELOPMENT_SEED_RANGE),
        "horizon": horizon,
        "lifetime": "one uninterrupted lifetime per seed",
        "seed_policy": {
            "canonical_validator": "validate_exp003_development_seeds",
            "exact_declared_seed_count": D012_SEED_COUNT,
            "formal_reservation_guard_preserved": True,
        },
        "programmed": {
            "controller": "unchanged D011Controller",
            "runner": "reused d011._run_seed",
            "d011_thresholds_and_action_logic_unchanged": True,
            "no_learning": True,
            "no_d008": True,
            "no_model_predictions": True,
            "no_reward": True,
            "no_resets_within_lifetime": True,
        },
        "organism_visible": {
            "inherited_from_d011": True,
            "no_evaluator_aggregation_passed_to_controller": True,
            "reward": 0.0,
            "info": {},
        },
        "evaluator_only": {
            "aggregation": True,
            "per_seed_d011_summary_records": True,
            "omits_per_transition_seek_geometry": True,
            "passed_to_controller": False,
        },
        "results": [_compact_d011_result(run) for run in results],
        "aggregate": _aggregate(results),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the D-012 D-011 robustness census."
    )
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=list(D012_DEFAULT_DEVELOPMENT_SEEDS),
    )
    parser.add_argument("--horizon", type=int, default=D012_HORIZON)
    parser.add_argument("--executed-commit-sha")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    """Run D-012 and print or write its machine-readable result."""
    args = _parse_args()
    payload = json.dumps(
        run_d012_census(
            tuple(args.seeds),
            horizon=args.horizon,
            executed_commit_sha=args.executed_commit_sha,
        ),
        indent=2,
        sort_keys=True,
    )
    if args.output is None:
        print(payload)
    else:
        args.output.write_text(payload + "\n", encoding="utf-8")
        print(f"D-012 result written to {args.output}")


if __name__ == "__main__":
    main()
