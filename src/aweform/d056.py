"""D-056 evaluator-only multi-cycle characterization of unchanged D-055."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Final, Sequence, cast

from . import d053, d054, d055
from .d045 import D045_BATTERY_CAPACITY_J, quantize_wheel_delta
from .exp003_seed_policy import validate_exp003_development_seeds

D056_ID: Final = "D-056"
D056_HORIZON: Final = 300_000
D056_FRESH_SEEDS: Final = tuple(range(22600, 22620))
D056_SUPPORT_SEEDS: Final = (22053, 22054, 22055, 22056, 22057)
D056_TEST_SEED: Final = 22620
D056_TEST_MAX_HORIZON: Final = 5_000
D056_MAX_EVENT_SAMPLES: Final = 256
D056_FAILURE_CLASSES: Final = frozenset(
    {"SPIN_EXHAUSTED", "WEDGED", "OTHER_NOT_DOCKED"}
)
D056_PAIRED_CLASSES: Final = (
    "NO_DIVERGENCE",
    "BOTH_DOCK",
    "U_ONLY_FAIL",
    "C_ONLY_FAIL",
    "BOTH_FAIL",
    "CENSORED",
)
D056_PROTECTED_FILES: Final = (
    "src/aweform/d045.py",
    "src/aweform/d049.py",
    "src/aweform/d050.py",
    "src/aweform/d052.py",
    "src/aweform/d053.py",
    "src/aweform/d054.py",
    "src/aweform/d055.py",
    "src/aweform/development_visualizer.py",
)


def _validate_block(
    seeds: Sequence[int], expected: tuple[int, ...], label: str
) -> tuple[int, ...]:
    validated = validate_exp003_development_seeds(seeds)
    if validated != expected:
        raise ValueError(
            f"D-056 requires exactly the frozen {label} seed block {expected}"
        )
    return validated


def validate_fresh_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    return _validate_block(seeds, D056_FRESH_SEEDS, "fresh")


def validate_support_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    return _validate_block(seeds, D056_SUPPORT_SEEDS, "support")


def validate_test_run(seed: int, horizon: int, initial_battery_fraction: float) -> None:
    if seed != D056_TEST_SEED:
        raise ValueError(f"D-056 test runs are restricted to seed {D056_TEST_SEED}")
    if not 0 < horizon <= D056_TEST_MAX_HORIZON:
        raise ValueError(f"D-056 test horizon must be in 1..{D056_TEST_MAX_HORIZON}")
    if not 0.0 <= initial_battery_fraction <= 0.21:
        raise ValueError("D-056 test initial battery fraction must be in [0, 0.21]")


def classify_episode(
    cycle: dict[str, object],
    rows: Sequence[dict[str, object]],
    *,
    lifetime_truncated: bool,
    lifetime_termination_reason: str | None,
) -> dict[str, object]:
    """Add evaluator-only terminal geometry/readouts and frozen episode class."""
    start = cast(int, cycle["start_transition"])
    final_transition = cast(int, rows[-1]["transition"])
    end = cast(int, cycle.get("end_transition", final_transition))
    segment = [r for r in rows if start <= cast(int, r["transition"]) <= end]
    if not segment:
        raise RuntimeError("RETURN episode has no trace rows")
    end_row = segment[-1]
    x, y = cast(float, end_row["x"]), cast(float, end_row["y"])
    wall_pinned = min(x, y, 1.0 - x, 1.0 - y) <= d054.D054_BOUNDARY_TOLERANCE_M
    tail = segment[-101:]
    path = sum(
        math.dist(
            (cast(float, a["x"]), cast(float, a["y"])),
            (cast(float, b["x"]), cast(float, b["y"])),
        )
        for a, b in zip(tail, tail[1:])
    )
    exhausted = any(
        bool(r.get("terminal_spin_exhausted"))
        or "TERMINAL_SPIN_EXHAUSTED" in cast(list[str], r.get("events", []))
        for r in segment
    )
    docked = cycle.get("first_charging_contact_transition") is not None
    if docked:
        label = "DOCKED"
    elif exhausted:
        label = "SPIN_EXHAUSTED"
    elif wall_pinned and path <= d054.D054_BOUNDARY_TOLERANCE_M:
        label = "WEDGED"
    elif lifetime_truncated and end == final_transition:
        label = "CENSORED_IN_PROGRESS"
    else:
        label = "OTHER_NOT_DOCKED"
    result = dict(cycle)
    result.update(
        {
            "docked": docked,
            "wall_pinned_at_end": wall_pinned,
            "final_100_centre_path_m": path,
            "class": label,
            "termination_reason": lifetime_termination_reason
            if end == final_transition
            else None,
        }
    )
    return result


def build_episodes(
    summary: dict[str, object], trace: Sequence[dict[str, object]], arm: str
) -> list[dict[str, object]]:
    cycles = cast(list[dict[str, object]], summary["cycles"])
    result: list[dict[str, object]] = []
    for cycle in cycles:
        episode = classify_episode(
            cycle,
            trace,
            lifetime_truncated=bool(summary["truncated"]),
            lifetime_termination_reason=cast(str | None, summary["termination_reason"]),
        )
        if arm == "C":
            stall_rows = [
                r for r in trace if r.get("cycle_index") == cycle["cycle_index"]
            ]
            turns = sum(r.get("command_source") == "STALL_TURN" for r in stall_rows)
            # D-055 records these exact counts in its additive per-cycle summary.
            stall_counts = cast(
                list[dict[str, object]], summary.get("stall_counts_by_cycle", [])
            )
            count_row = next(
                (r for r in stall_counts if r["cycle_index"] == cycle["cycle_index"]),
                {},
            )
            episode["stall_turn_count"] = turns
            episode["stall_detected_count"] = cast(
                int, count_row.get("stall_detected_count", 0)
            )
        result.append(episode)
    return result


def pair_episodes(
    u_episodes: Sequence[dict[str, object]],
    c_episodes: Sequence[dict[str, object]],
    first_stall_turn_transition: int | None,
) -> dict[str, object]:
    if first_stall_turn_transition is None:
        return {"divergent_episode_index": None, "paired_class": "NO_DIVERGENCE"}
    k = next(
        (
            i
            for i, ep in enumerate(c_episodes)
            if cast(int, ep["start_transition"])
            <= first_stall_turn_transition
            <= cast(int, ep.get("end_transition", first_stall_turn_transition))
        ),
        None,
    )
    if k is None or k >= len(u_episodes):
        raise RuntimeError(
            "first stall turn does not belong to a paired RETURN episode"
        )
    uc, cc = str(u_episodes[k]["class"]), str(c_episodes[k]["class"])
    if "CENSORED_IN_PROGRESS" in (uc, cc):
        label = "CENSORED"
    elif uc == "DOCKED" and cc == "DOCKED":
        label = "BOTH_DOCK"
    elif uc in D056_FAILURE_CLASSES and cc == "DOCKED":
        label = "U_ONLY_FAIL"
    elif uc == "DOCKED" and cc in D056_FAILURE_CLASSES:
        label = "C_ONLY_FAIL"
    elif uc in D056_FAILURE_CLASSES and cc in D056_FAILURE_CLASSES:
        label = "BOTH_FAIL"
    else:
        label = "CENSORED"
    return {"divergent_episode_index": k + 1, "paired_class": label}


def assert_horizon_prefix(
    short: Sequence[dict[str, object]],
    long: Sequence[dict[str, object]],
    short_horizon: int,
) -> None:
    if len(short) != short_horizon + 1 or len(long) < len(short):
        raise RuntimeError("horizon-prefix trace row count mismatch")
    normalized = [dict(row) for row in short]
    final = normalized[-1]
    if final.get("truncated") is not True:
        raise RuntimeError("short trace final row lacks horizon truncation")
    final["truncated"] = False
    events = cast(list[str], final.get("events"))
    if events.count("TRUNCATED") != 1:
        raise RuntimeError("short final row must contain exactly one TRUNCATED event")
    final["events"] = [event for event in events if event != "TRUNCATED"]
    if normalized != list(long[: len(short)]):
        raise RuntimeError("horizon-prefix identity failed")


def assert_candidate_prefix(
    u_trace: Sequence[dict[str, object]],
    c_trace: Sequence[dict[str, object]],
    first_turn: int | None,
) -> None:
    limit = len(c_trace) if first_turn is None else first_turn
    if list(u_trace[:limit]) != list(c_trace[:limit]):
        raise RuntimeError("candidate prefix identity failed")


def _summary_without_stall_fields(summary: dict[str, object]) -> dict[str, object]:
    reduced = {
        k: v
        for k, v in summary.items()
        if k
        not in {
            "stall_turn_count",
            "stall_detected_count",
            "first_stall_turn_transition",
            "stall_counts_by_cycle",
        }
    }
    reduced["command_source_counts"] = {
        k: v
        for k, v in cast(dict[str, object], reduced["command_source_counts"]).items()
        if k != "STALL_TURN"
    }
    return reduced


def assert_zero_turn_summary_identity(
    u: dict[str, object], c: dict[str, object]
) -> None:
    if d053._canonicalize(u) != d053._canonicalize(_summary_without_stall_fields(c)):
        raise RuntimeError("zero-stall summary identity failed")


def _trace_detector_audit(
    trace: Sequence[dict[str, object]], summary: dict[str, object]
) -> dict[str, object]:
    detected_scales: list[float] = []
    missed = 0
    detections = 0
    for index in range(1, len(trace)):
        previous = trace[index - 1]
        current = trace[index]
        if previous.get("active_mode") != "RETURN":
            continue
        wheels = cast(list[float], previous["wheel_command"])
        boundary_scale = cast(float, previous["boundary_scale"])
        eligible_command = (
            max(abs(wheels[0]), abs(wheels[1])) >= d055.STALL_COMMAND_FLOOR
        )
        if not eligible_command:
            continue
        zero_encoders = (
            quantize_wheel_delta(wheels[0] * boundary_scale) == 0.0
            and quantize_wheel_delta(wheels[1] * boundary_scale) == 0.0
        )
        detected = zero_encoders and current.get("active_mode") == "RETURN"
        if detected:
            detections += 1
            detected_scales.append(boundary_scale)
        elif boundary_scale <= 1e-9 and current.get("active_mode") == "RETURN":
            missed += 1
    expected_detections = cast(int, summary.get("stall_detected_count", 0))
    if detections != expected_detections:
        raise RuntimeError("reconstructed lifetime detector audit disagrees with D-055")
    turns = sum(row.get("command_source") == "STALL_TURN" for row in trace)
    detected_non_pursuit = detections - turns
    if detected_non_pursuit < 0:
        raise RuntimeError("stall-turn count exceeds detector count")
    return {
        "detection_count": detections,
        "detected_turn_count": turns,
        "non_pursuit_detection_count": detected_non_pursuit,
        "preceding_boundary_scale_maximum": max(detected_scales, default=None),
        "preceding_boundary_scale_counts": {
            "at_zero": sum(scale == 0.0 for scale in detected_scales),
            "in_0_to_1e-9": sum(0.0 < scale <= 1e-9 for scale in detected_scales),
            "above_1e-9": sum(scale > 1e-9 for scale in detected_scales),
        },
        "missed_stall_count": missed,
        "missed_stall_definition": (
            "D-055 lifetime analogue: a prior RETURN command at least the frozen "
            "stall floor with boundary_scale <= 1e-9, followed by RETURN without "
            "the reconstructed zero-encoder detection."
        ),
    }


def _lifetime_readouts(
    summary: dict[str, object], episodes: Sequence[dict[str, object]]
) -> dict[str, object]:
    return {
        "seed": summary["seed"],
        "return_activations": summary["return_activated_count"],
        "docks": sum(ep["docked"] is True for ep in episodes),
        "completed_yields": summary["completed_recovery_yield_count"],
        "termination_reason": summary["termination_reason"],
        "final_mode": summary["final_mode"],
        "minimum_observed_energy": summary["minimum_observed_energy"],
        "minimum_battery_j": summary["minimum_battery_j"],
        "preemption_count": summary["level1_preemption_count"],
        "preemption_fraction": summary["level1_preemption_fraction"],
        "boundary_scaled_transitions": summary["boundary_scaled_transition_count"],
    }


def _prior_d055_part_b() -> dict[int, dict[str, object]]:
    path = (
        Path(__file__).resolve().parents[2]
        / "development/D-055-v05-return-proprioceptive-stall-turn-candidate.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {int(row["seed"]): row for row in payload["part_b"]["pairs"]}


def run_lifetime(
    seed: int,
    *,
    horizon: int = D056_HORIZON,
    initial_battery_fraction: float = 0.80,
) -> tuple[
    dict[str, object],
    dict[str, object],
    list[dict[str, object]],
    list[dict[str, object]],
    dict[str, object],
    dict[str, object],
    tuple[dict[str, object], ...],
    tuple[dict[str, object], ...],
]:
    u = d053.run_d053_lifetime(
        seed, horizon=horizon, initial_battery_fraction=initial_battery_fraction
    )
    c = d055.run_d055_lifetime(
        seed, horizon=horizon, initial_battery_fraction=initial_battery_fraction
    )
    first_turn = cast(int | None, c.summary["first_stall_turn_transition"])
    assert_candidate_prefix(u.trace, c.trace, first_turn)
    if first_turn is None:
        assert_zero_turn_summary_identity(u.summary, c.summary)
    ue, ce = (
        build_episodes(u.summary, u.trace, "U"),
        build_episodes(c.summary, c.trace, "C"),
    )
    pair = pair_episodes(ue, ce, first_turn)
    u_summary, c_summary = dict(u.summary), dict(c.summary)
    # Bounded event summaries are already capped by the unchanged D-053/D-055 runners.
    return (
        u_summary,
        c_summary,
        ue,
        ce,
        pair,
        _trace_detector_audit(c.trace, c.summary),
        u.trace,
        c.trace,
    )


def run_test_lifetime(
    seed: int, *, horizon: int, initial_battery_fraction: float
) -> tuple[Any, ...]:
    validate_test_run(seed, horizon, initial_battery_fraction)
    return run_lifetime(
        seed, horizon=horizon, initial_battery_fraction=initial_battery_fraction
    )


def run_protocol(executed_commit_sha: str) -> dict[str, object]:
    if len(executed_commit_sha) != 40 or any(
        c not in "0123456789abcdef" for c in executed_commit_sha
    ):
        raise ValueError("executed_commit_sha must be a lowercase 40-character SHA")
    fresh = validate_fresh_seeds(D056_FRESH_SEEDS)
    support = validate_support_seeds(D056_SUPPORT_SEEDS)
    prior = _prior_d055_part_b()
    lifetimes: list[dict[str, object]] = []
    episodes_all: list[dict[str, object]] = []
    pair_rows: list[dict[str, object]] = []
    audits: list[dict[str, object]] = []
    committed_checks: list[dict[str, object]] = []
    prefix_checks: list[dict[str, object]] = []
    for block_name, seeds in (("fresh", fresh), ("support", support)):
        for seed in seeds:
            u, c, ue, ce, pair, audit, u_trace, c_trace = run_lifetime(seed)
            pair_rows.append({"seed": seed, "block": block_name, **pair})
            lifetimes.extend(
                [
                    {
                        "seed": seed,
                        "block": block_name,
                        "arm": "U",
                        "summary": u,
                        "readouts": _lifetime_readouts(u, ue),
                    },
                    {
                        "seed": seed,
                        "block": block_name,
                        "arm": "C",
                        "summary": c,
                        "readouts": _lifetime_readouts(c, ce),
                        "detector_audit": audit,
                    },
                ]
            )
            episodes_all.extend(
                {"seed": seed, "block": block_name, "arm": arm, **ep}
                for arm, eps in (("U", ue), ("C", ce))
                for ep in eps
            )
            if seed in support:
                previous = prior.get(seed)
                if previous is None:
                    raise RuntimeError(
                        f"committed D-055 pair missing support seed {seed}"
                    )
                for arm, long_summary, long_trace in (
                    ("U", u, u_trace),
                    ("C", c, c_trace),
                ):
                    short = (
                        d053.run_d053_lifetime(seed, horizon=140_000)
                        if arm == "U"
                        else d055.run_d055_lifetime(seed, horizon=140_000)
                    )
                    expected = previous["arm_u" if arm == "U" else "arm_c"]
                    if d053._canonicalize(short.summary) != d053._canonicalize(
                        expected
                    ):
                        raise RuntimeError(
                            f"committed-evidence identity failed for {arm} seed {seed}"
                        )
                    assert_horizon_prefix(short.trace, long_trace, 140_000)
                    del short, long_summary
                committed_checks.append({"seed": seed, "result": "PASS"})
                prefix_checks.append({"seed": seed, "result": "PASS"})
            audits.append({"seed": seed, "block": block_name, **audit})
            del u_trace, c_trace
    fresh_pairs = [p for p in pair_rows if p["block"] == "fresh"]
    support_pairs = [p for p in pair_rows if p["block"] == "support"]

    def pair_counts(rows: Sequence[dict[str, object]]) -> dict[str, int]:
        counts = Counter(str(r["paired_class"]) for r in rows)
        return {k: counts[k] for k in D056_PAIRED_CLASSES}

    def episode_counts(block: str, arm: str) -> dict[str, int]:
        selected = [r for r in episodes_all if r["block"] == block and r["arm"] == arm]
        counts = Counter(str(r["class"]) for r in selected)
        return dict(sorted(counts.items()))

    failed_fresh_c = sum(
        r["class"] in D056_FAILURE_CLASSES
        for r in episodes_all
        if r["block"] == "fresh" and r["arm"] == "C"
    )
    harm = any(r["paired_class"] == "C_ONLY_FAIL" for r in pair_rows)
    yields_hist = Counter(
        cast(
            int,
            cast(dict[str, object], r["summary"])["completed_recovery_yield_count"],
        )
        for r in lifetimes
        if r["block"] == "fresh" and r["arm"] == "C"
    )
    u_first_docked = sum(
        bool(
            next(
                (
                    ep["docked"]
                    for ep in episodes_all
                    if ep["seed"] == seed
                    and ep["block"] == "fresh"
                    and ep["arm"] == "U"
                ),
                False,
            )
        )
        for seed in fresh
    )
    signature = {
        "FRESH_DIVERGENT_PAIRS": pair_counts(fresh_pairs),
        "SUPPORT_DIVERGENT_PAIRS": pair_counts(support_pairs),
        "FRESH_C_FAILED_EPISODES": failed_fresh_c,
        "C_HARM": "SOME" if harm else "NONE",
        "FRESH_C_YIELDS_PER_LIFETIME": dict(sorted(yields_hist.items())),
        "FRESH_U_FIRST_EPISODE_DOCKED": f"{u_first_docked}/20",
    }
    controls = {
        "protected_source_no_diff": "PASS (test-enforced against authorized base)",
        "committed_evidence_identity_140000": committed_checks,
        "horizon_prefix_identity_140000_to_300000": prefix_checks,
        "candidate_prefix_identity": "PASS (each lifetime)",
        "zero_stall_summary_identity": "PASS (enforced whenever applicable)",
        "seed_blocks": {
            "fresh": list(fresh),
            "support": list(support),
            "test_only": D056_TEST_SEED,
        },
        "reward_exactly_zero": all(
            bool(cast(dict[str, object], r["summary"])["reward_exactly_zero"])
            for r in lifetimes
        ),
        "organism_info_exactly_empty": all(
            bool(cast(dict[str, object], r["summary"])["organism_info_exactly_empty"])
            for r in lifetimes
        ),
    }
    return {
        "schema_version": "d056-artifact-v1",
        "development_id": D056_ID,
        "protocol_version": "d056-v05-multi-cycle-stall-turn-lifetimes-v1",
        "authorized_base_sha": "1a9dee3321842230b5f5aa71423917ec79419918",
        "executed_commit_sha": executed_commit_sha,
        "execution_status": "COMPLETED",
        "result_kind": "descriptive_development",
        "claims_boundary": (
            "Descriptive Development only; no confirmatory claim, Level-1 "
            "promotion, or durable-boundary change."
        ),
        "frozen_protocol": {
            "horizon": D056_HORIZON,
            "lifetime": "one continuous lifetime per arm and seed",
            "initial_state": {
                "body_position": [0.5, 0.5],
                "station_center": [0.5, 0.5],
                "heading_rad": 0.0,
                "initial_battery_fraction": 0.8,
                "initial_battery_j": 0.8 * D045_BATTERY_CAPACITY_J,
                "ambient_temperature": True,
                "charger_latch": False,
            },
            "initial_battery_fraction": 0.8,
            "initial_battery_j": 0.8 * D045_BATTERY_CAPACITY_J,
            "arms": {
                "U": "unchanged run_d053_lifetime",
                "C": "unchanged run_d055_lifetime",
            },
            "fresh_seeds": list(fresh),
            "support_seeds": list(support),
            "excluded_seeds": list(range(22550, 22570)),
            "reward": 0.0,
            "organism_info": {},
            "event_samples_cap_per_lifetime": D056_MAX_EVENT_SAMPLES,
        },
        "controls": controls,
        "lifetimes": lifetimes,
        "episodes": episodes_all,
        "pairs": pair_rows,
        "aggregates": {
            "paired_class_counts": {
                "fresh": pair_counts(fresh_pairs),
                "support": pair_counts(support_pairs),
            },
            "episode_class_counts": {
                b: {a: episode_counts(b, a) for a in ("U", "C")}
                for b in ("fresh", "support")
            },
            "divergent_episode_index_distribution": {
                block: dict(
                    sorted(
                        Counter(
                            cast(int, row["divergent_episode_index"])
                            for row in rows
                            if row["divergent_episode_index"] is not None
                        ).items()
                    )
                )
                for block, rows in (("fresh", fresh_pairs), ("support", support_pairs))
            },
            "detector_audit_by_lifetime": audits,
            "detector_audit": {
                block: {
                    "detection_count": sum(
                        cast(int, row["detection_count"])
                        for row in audits
                        if row["block"] == block
                    ),
                    "maximum_preceding_boundary_scale": max(
                        (
                            cast(float, row["preceding_boundary_scale_maximum"])
                            for row in audits
                            if row["block"] == block
                            and row["preceding_boundary_scale_maximum"] is not None
                        ),
                        default=None,
                    ),
                    "preceding_boundary_scale_counts": {
                        key: sum(
                            cast(
                                int,
                                cast(
                                    dict[str, object],
                                    row["preceding_boundary_scale_counts"],
                                )[key],
                            )
                            for row in audits
                            if row["block"] == block
                        )
                        for key in ("at_zero", "in_0_to_1e-9", "above_1e-9")
                    },
                    "missed_stall_count": sum(
                        cast(int, row["missed_stall_count"])
                        for row in audits
                        if row["block"] == block
                    ),
                    "non_pursuit_detection_count": sum(
                        cast(int, row["non_pursuit_detection_count"])
                        for row in audits
                        if row["block"] == block
                    ),
                }
                for block in ("fresh", "support")
            },
            "arm_c_episode_stall_summary": {
                block: {
                    "episodes_with_stall_turn": sum(
                        cast(int, row.get("stall_turn_count", 0)) > 0
                        for row in episodes_all
                        if row["block"] == block and row["arm"] == "C"
                    ),
                    "maximum_stall_turns_in_episode": max(
                        (
                            cast(int, row.get("stall_turn_count", 0))
                            for row in episodes_all
                            if row["block"] == block and row["arm"] == "C"
                        ),
                        default=0,
                    ),
                }
                for block in ("fresh", "support")
            },
            "signature": signature,
        },
    }


def write_artifact(path: Path, executed_commit_sha: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            d053._canonicalize(run_protocol(executed_commit_sha)),
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--executed-commit-sha", required=True)
    args = parser.parse_args(argv)
    write_artifact(args.output, args.executed_commit_sha)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
