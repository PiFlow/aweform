"""D-041 evaluator-only front-beacon sensory-sufficiency audit.

This module creates synthetic measurements from the existing D-024 physical
geometry.  The measurements are consumed only by evaluator-side cloned
branches; they never enter the canonical controller, learner, environment,
RNG, reward, or ``info`` path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

from . import d025, d026, d031r1, d040
from .d026 import D026Observation
from .env import Action
from .exp003_seed_policy import validate_exp003_development_seeds

D041_AUTHORITATIVE_BASE_SHA: Final[str] = (
    "8b51d6e143a906a83f1fd8d760aace5ed46abb9e"
)
D041_D040_REUSED_ARTIFACT_SHA256: Final[str] = (
    "764c1b09f18c250cb55682d434c2b6f372a9e66d82380b88c0bc08ab85cd495d"
)
D041_REUSED_SEEDS: Final[tuple[int, ...]] = d040.D040_REUSED_SEEDS
D041_HOLDOUT_SEEDS: Final[tuple[int, ...]] = d040.D040_HOLDOUT_SEEDS
D041_HORIZON: Final[int] = d040.D040_HORIZON
D041_ANCHOR_REPLAY_HORIZON: Final[int] = 40_000
D041_BRANCH_HORIZON: Final[int] = d040.D040_BRANCH_HORIZON
D041_HORIZONS: Final[tuple[int, ...]] = d040.D040_HORIZONS
D041_IDENTITY_HORIZON: Final[int] = 128
D041_S0_BUCKET_WIDTH: Final[float] = 1e-3

# The D-040 failure-state families are frozen before D-041 outcome inspection.
D041_ANCHOR_IDS: Final[tuple[str, ...]] = (
    "OFFSET_0",
    "OFFSET_15",
    "OFFSET_63",
    "OFFSET_255",
    "OFFSET_1023",
    "OFFSET_4095",
    "ALT_16",
    "NO_FORWARD_PROGRESS_16",
)
D041_BRANCHES: Final[tuple[str, ...]] = (
    "PAIR",
    "S0_READOUT",
    "LEFT_ONLY",
    "RIGHT_ONLY",
    "SWAP",
    "NULL",
    "OUT_OF_RANGE",
)
D041_PRIMARY_BRANCH: Final[str] = "PAIR"
D041_COMPARISON_BRANCH: Final[str] = "S0_READOUT"
D041_NULL_BRANCHES: Final[tuple[str, ...]] = ("NULL", "OUT_OF_RANGE")
D041_PROTOCOL_VERSION: Final[str] = "d041-front-beacon-v1"

D041_RECEPTOR_LEFT_BODY: Final[tuple[float, float]] = (0.05, 0.025)
D041_RECEPTOR_RIGHT_BODY: Final[tuple[float, float]] = (0.05, -0.025)
D041_RECEPTOR_NORMAL_BODY: Final[tuple[float, float]] = (1.0, 0.0)
D041_BEACON_RANGE: Final[float] = 0.35
D041_RESPONSE_CLIP: Final[tuple[float, float]] = (0.0, 1.0)


@dataclass(frozen=True, slots=True)
class ReceptorPair:
    """Evaluator-only left/right front-receptor measurements."""

    left: float
    right: float

    def as_tuple(self) -> tuple[float, float]:
        return self.left, self.right


@dataclass(frozen=True, slots=True)
class _BranchRun:
    result: dict[str, object]
    trace: tuple[d025.D025TransitionTrace, ...]


def _validate_seed_block(
    seeds: Sequence[int], expected: tuple[int, ...], label: str
) -> tuple[int, ...]:
    validated = validate_exp003_development_seeds(seeds)
    if validated != expected:
        raise ValueError(f"D-041 requires exactly the frozen {label} seeds {expected}")
    return validated


def _validate_seed(seed: int, *, holdout: bool) -> None:
    expected = D041_HOLDOUT_SEEDS if holdout else D041_REUSED_SEEDS
    validated = validate_exp003_development_seeds((seed,))
    if validated[0] not in expected:
        label = "holdout" if holdout else "reused"
        raise ValueError(f"D-041 {label} seed is outside the declared block: {seed}")


def _validate_executed_commit_sha(value: str | None) -> str:
    if value is None or len(value) != 40 or any(
        c not in "0123456789abcdef" for c in value
    ):
        raise ValueError("D-041 requires an exact clean executable SHA")
    return value


def _rotate(point: tuple[float, float], heading: float) -> tuple[float, float]:
    cosine = math.cos(heading)
    sine = math.sin(heading)
    return (
        point[0] * cosine - point[1] * sine,
        point[0] * sine + point[1] * cosine,
    )


def _translate(
    origin: tuple[float, float], offset: tuple[float, float]
) -> tuple[float, float]:
    return origin[0] + offset[0], origin[1] + offset[1]


def receptor_positions_world(
    body_center: tuple[float, float], body_heading: float
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Return left/right receptor positions from the body frame."""
    return (
        _translate(body_center, _rotate(D041_RECEPTOR_LEFT_BODY, body_heading)),
        _translate(body_center, _rotate(D041_RECEPTOR_RIGHT_BODY, body_heading)),
    )


def _receptor_response(
    receptor: tuple[float, float],
    normal: tuple[float, float],
    source: tuple[float, float],
) -> float:
    dx = source[0] - receptor[0]
    dy = source[1] - receptor[1]
    distance = math.hypot(dx, dy)
    if distance == 0.0:
        return 1.0
    if distance > D041_BEACON_RANGE:
        return 0.0
    cosine = (dx * normal[0] + dy * normal[1]) / distance
    if cosine <= 0.0:
        return 0.0
    response = cosine * (1.0 - distance / D041_BEACON_RANGE)
    return min(D041_RESPONSE_CLIP[1], max(D041_RESPONSE_CLIP[0], response))


def front_beacon_receptors(
    body_center: tuple[float, float],
    body_heading: float,
    station_center: tuple[float, float],
) -> ReceptorPair:
    """Compute the two deterministic front-facing beacon responses.

    The beacon is an isotropic point emitter at the existing station centre.
    Each receptor has a body-attached +X normal.  Response is the clipped
    product of the front-facing cosine and a linear in-range falloff.  There
    is no occlusion, noise, hidden state, or signal clipping beyond [0, 1].
    """
    positions = receptor_positions_world(body_center, body_heading)
    normal = _rotate(D041_RECEPTOR_NORMAL_BODY, body_heading)
    return ReceptorPair(
        left=_receptor_response(positions[0], normal, station_center),
        right=_receptor_response(positions[1], normal, station_center),
    )


def front_beacon_receptors_from_environment(environment: object) -> ReceptorPair:
    """Read evaluator geometry only to create a synthetic receptor pair."""
    body = getattr(environment, "body", None)
    station_center = getattr(environment, "station_center", None)
    if body is None or station_center is None:
        raise RuntimeError("D-041 requires initialized evaluator geometry")
    return front_beacon_receptors(body.position, body.heading, station_center)


def _validate_pair(pair: ReceptorPair) -> None:
    if not all(
        math.isfinite(value) and 0.0 <= value <= 1.0
        for value in pair.as_tuple()
    ):
        raise ValueError("receptor values must be finite and within [0, 1]")


def receptor_readout(pair: ReceptorPair, *, condition: str = "PAIR") -> Action:
    """Apply the frozen pair-only evaluator steering rule."""
    if condition not in D041_BRANCHES:
        raise ValueError(f"unknown D-041 branch condition: {condition}")
    _validate_pair(pair)
    left, right = pair.as_tuple()
    if condition in ("NULL", "OUT_OF_RANGE"):
        left = right = 0.0
    elif condition == "LEFT_ONLY":
        right = 0.0
    elif condition == "RIGHT_ONLY":
        left = 0.0
    elif condition == "SWAP":
        left, right = right, left
    if left > right:
        return Action.TURN_LEFT
    if right > left:
        return Action.TURN_RIGHT
    return Action.MOVE_FORWARD if left > 0.0 else Action.WAIT


def _s0_readout(current: D026Observation) -> Action:
    """Use only the current visible left/right S0 beacon channels."""
    left = current.beacon.left
    right = current.beacon.right
    if left > right:
        return Action.TURN_LEFT
    if right > left:
        return Action.TURN_RIGHT
    return Action.MOVE_FORWARD if left > 0.0 else Action.WAIT


def _trace_digest(trace: Sequence[d025.D025TransitionTrace]) -> str:
    return d040._digest(
        tuple(
            (
                row.action.name,
                row.observation_before,
                row.observation,
                row.telemetry,
                row.reward,
                row.info,
            )
            for row in trace
        )
    )


def _action_counts(trace: Sequence[d025.D025TransitionTrace]) -> dict[str, int]:
    counts = {action.name: 0 for action in Action}
    for row in trace:
        counts[row.action.name] += 1
    return counts


def _summary_for_horizon(
    anchor: d040._Anchor,
    trace: Sequence[d025.D025TransitionTrace],
    result: dict[str, object],
    horizon: int,
) -> dict[str, object]:
    latency = cast(int | None, result["reacquisition_latency"])
    if latency is not None and latency <= horizon:
        rows = tuple(trace[:latency])
        status = "reacquired"
    elif len(trace) >= horizon:
        rows = tuple(trace[:horizon])
        status = "available"
    else:
        rows = tuple(trace)
        status = "null"
    if not rows:
        return {
            "status": status,
            "reacquired": False,
            "reacquisition_latency": None,
            "transitions": 0,
        }
    if anchor.environment.body is None:
        raise RuntimeError("D-041 anchor lacks body geometry")
    first_position = anchor.environment.body.position
    last = rows[-1]
    path_length = sum(
        math.dist(row.telemetry.position_before, row.telemetry.position_after)
        for row in rows
    )
    return {
        "status": status,
        "reacquired": status == "reacquired",
        "reacquisition_latency": latency if status == "reacquired" else None,
        "transitions": len(rows),
        "visible_beacon_forward_progress": (
            last.observation[2] - anchor.current.beacon.forward
        ),
        "net_displacement": math.dist(first_position, last.telemetry.position_after),
        "path_displacement": path_length,
        "heading_change": last.telemetry.heading - anchor.environment.body.heading,
        "energy_change": last.observation[0] - anchor.current.energy,
        "thermal_change": last.observation[5] - anchor.current.thermal,
        "action_counts": _action_counts(rows),
        "front_docking_contact": status == "reacquired",
    }


def _run_branch(
    anchor: d040._Anchor, *, condition: str, horizon: int = D041_BRANCH_HORIZON
) -> _BranchRun:
    if condition not in D041_BRANCHES:
        raise ValueError(f"unknown D-041 branch condition: {condition}")
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon <= 0:
        raise ValueError("D-041 branch horizon must be a positive integer")
    environment = d040._clone_environment(anchor.environment)
    current = anchor.current
    trace: list[d025.D025TransitionTrace] = []
    signal_digest = hashlib.sha256()
    terminated = truncated = False
    reacquisition: int | None = None
    reward_zero = True
    info_empty = True
    for local in range(1, horizon + 1):
        pair = front_beacon_receptors_from_environment(environment)
        if condition == "S0_READOUT":
            action = _s0_readout(current)
        else:
            action = receptor_readout(pair, condition=condition)
        signal_digest.update(
            (
                json.dumps(
                    {"left": pair.left, "right": pair.right, "action": action.name},
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            ).encode()
        )
        observation_array, reward, terminated, truncated, info = environment.step(
            action
        )
        reward_zero &= reward == 0.0
        info_empty &= info == {}
        telemetry = environment.last_transition
        if telemetry is None:
            raise RuntimeError("D-041 branch produced no telemetry")
        next_visible = d040._next_visible(observation_array)
        trace.append(
            d025._make_trace(
                transition_index=anchor.transition + local - 1,
                mode_before=d026.D026Mode.SEEK,
                mode_after=d026.D026Mode.SEEK,
                action=action,
                current=current,
                observation=observation_array,
                telemetry=telemetry,
                reward=reward,
                info=info,
            )
        )
        if not telemetry.charging_contact_before and telemetry.charging_contact_after:
            reacquisition = local
        current = next_visible
        if reacquisition is not None or terminated or truncated:
            break
    if reacquisition is not None:
        outcome = "REACQUIRED"
    elif terminated:
        outcome = "TERMINATED"
    elif truncated:
        outcome = "TRUNCATED"
    else:
        outcome = "HORIZON_CENSORED"
    result: dict[str, object] = {
        "condition": condition,
        "transitions": len(trace),
        "outcome": outcome,
        "reacquired": reacquisition is not None,
        "reacquisition_latency": reacquisition,
        "terminated": terminated,
        "truncated": truncated,
        "reward_zero_every_transition": reward_zero,
        "organism_info_empty_every_transition": info_empty,
        "action_counts": _action_counts(trace),
        "trajectory_digest": _trace_digest(trace),
        "signal_digest": signal_digest.hexdigest(),
        "evaluator_only": True,
        "organism_state_changed": False,
    }
    result["horizons"] = {
        str(limit): _summary_for_horizon(anchor, trace, result, limit)
        for limit in D041_HORIZONS
    }
    return _BranchRun(result=result, trace=tuple(trace))


def _branch_projection(result: dict[str, object]) -> dict[str, object]:
    return {
        key: result[key]
        for key in (
            "outcome",
            "transitions",
            "reacquired",
            "reacquisition_latency",
            "terminated",
            "truncated",
            "action_counts",
            "trajectory_digest",
            "signal_digest",
            "horizons",
        )
    }


def _pair_effect(
    pair: dict[str, object], comparator: dict[str, object]
) -> dict[str, object]:
    pair_success = bool(pair["reacquired"])
    comparator_success = bool(comparator["reacquired"])
    return {
        "classification": (
            "PAIR_ONLY"
            if pair_success and not comparator_success
            else "S0_ONLY"
            if comparator_success and not pair_success
            else "BOTH"
            if pair_success and comparator_success
            else "NEITHER"
        ),
        "pair_latency_minus_s0_latency": (
            int(cast(int, pair["reacquisition_latency"]))
            - int(cast(int, comparator["reacquisition_latency"]))
            if pair_success and comparator_success
            else None
        ),
    }


def _anchor_record(anchor: d040._Anchor) -> dict[str, object]:
    if anchor.environment.body is None or anchor.environment.station_center is None:
        raise RuntimeError("D-041 anchor lacks evaluator geometry")
    pair = front_beacon_receptors_from_environment(anchor.environment)
    current = anchor.current
    return {
        "anchor_id": anchor.anchor_id,
        "transition": anchor.transition,
        "state_digest": anchor.state_digest,
        "s0": [
            current.energy,
            current.beacon.left,
            current.beacon.forward,
            current.beacon.right,
            float(current.charging_contact),
            current.thermal,
        ],
        "receptor_pair": list(pair.as_tuple()),
        "evaluator_geometry": {
            "body_center": list(anchor.environment.body.position),
            "body_heading": anchor.environment.body.heading,
            "station_center": list(anchor.environment.station_center),
        },
    }


def _run_anchor(anchor: d040._Anchor) -> dict[str, object]:
    source_digest = anchor.state_digest
    branch_runs = {
        condition: _run_branch(anchor, condition=condition)
        for condition in D041_BRANCHES
    }
    # The order-invariance control is run for the primary branch only.  The
    # other controls are independent pure clones, so repeating all seven would
    # add cost without testing a different shared-state path.
    reversed_pair = _run_branch(anchor, condition=D041_PRIMARY_BRANCH)
    order_passed = all(
        _branch_projection(branch_runs[D041_PRIMARY_BRANCH].result)
        == _branch_projection(reversed_pair.result)
        for _ in (D041_PRIMARY_BRANCH,)
    )
    pair_result = branch_runs[D041_PRIMARY_BRANCH].result
    comparator_result = branch_runs[D041_COMPARISON_BRANCH].result
    record = _anchor_record(anchor)
    record.update(
        {
            "branches": {
                condition: branch_runs[condition].result for condition in D041_BRANCHES
            },
            "pair_effect_vs_s0": _pair_effect(pair_result, comparator_result),
            "controls": {
                "branch_order_invariant": order_passed,
                "branch_order_checked_conditions": [D041_PRIMARY_BRANCH],
                "source_anchor_unchanged": anchor.state_digest == source_digest,
                "all_branches_reward_zero": all(
                    bool(run.result["reward_zero_every_transition"])
                    for run in branch_runs.values()
                ),
                "all_branches_info_empty": all(
                    bool(run.result["organism_info_empty_every_transition"])
                    for run in branch_runs.values()
                ),
                "all_branches_evaluator_only": all(
                    bool(run.result["evaluator_only"])
                    and bool(run.result["organism_state_changed"] is False)
                    for run in branch_runs.values()
                ),
            },
        }
    )
    return record


def _bucket(values: Sequence[float]) -> tuple[int, ...]:
    return tuple(round(value / D041_S0_BUCKET_WIDTH) for value in values)


def _separability(records: Sequence[dict[str, object]]) -> dict[str, object]:
    s0_groups: dict[tuple[int, ...], set[tuple[int, ...]]] = {}
    pair_groups: dict[tuple[int, ...], set[tuple[int, ...]]] = {}
    for record in records:
        s0 = tuple(cast(list[float], record["s0"]))
        pair = tuple(cast(list[float], record["receptor_pair"]))
        s0_groups.setdefault(_bucket(s0), set()).add(_bucket(pair))
        pair_groups.setdefault(_bucket(pair), set()).add(_bucket(s0))
    ambiguous_s0 = [values for values in s0_groups.values() if len(values) > 1]
    return {
        "bucket_width": D041_S0_BUCKET_WIDTH,
        "anchor_count": len(records),
        "s0_bucket_count": len(s0_groups),
        "receptor_pair_bucket_count": len(pair_groups),
        "s0_ambiguous_group_count": len(ambiguous_s0),
        "s0_ambiguous_groups_separated_by_pair": sum(
            int(len(values) > 1) for values in ambiguous_s0
        ),
        "s0_and_pair_bucket_collisions": sum(
            int(len(values) > 1) for values in pair_groups.values()
        ),
    }


def _canonical_identity(seed: int) -> dict[str, object]:
    off = d031r1._run_arm(
        seed,
        arm="LEARNED_NO_DETRAP",
        horizon=D041_IDENTITY_HORIZON,
        evaluator_diagnostics=False,
        seed_validator=lambda value: _validate_seed(
            value, holdout=value in D041_HOLDOUT_SEEDS
        ),
    )
    on = d031r1._run_arm(
        seed,
        arm="LEARNED_NO_DETRAP",
        horizon=D041_IDENTITY_HORIZON,
        evaluator_diagnostics=True,
        seed_validator=lambda value: _validate_seed(
            value, holdout=value in D041_HOLDOUT_SEEDS
        ),
    )
    identity = d040.compare_identity_fields(off, on)
    return {
        "diagnostic_off_vs_on": identity,
        "passed": bool(identity["all_identity_fields_exact"]),
        "horizon": D041_IDENTITY_HORIZON,
    }


def _seed_result(seed: int) -> dict[str, object]:
    _validate_seed(seed, holdout=seed in D041_HOLDOUT_SEEDS)
    _, _, anchors = d040._independent_arm_b(
        seed, horizon=D041_ANCHOR_REPLAY_HORIZON, capture_anchors=True
    )
    records = []
    for anchor_id in D041_ANCHOR_IDS:
        anchor = anchors[anchor_id]
        if anchor is not None:
            records.append(_run_anchor(anchor))

    def branch_reacquired(record: dict[str, object], condition: str) -> bool:
        branches = cast(dict[str, object], record["branches"])
        branch = cast(dict[str, object], branches[condition])
        return bool(branch["reacquired"])

    return {
        "seed": seed,
        "seed_role": (
            "fresh_holdout" if seed in D041_HOLDOUT_SEEDS else "reused_support"
        ),
        "canonical_identity": _canonical_identity(seed),
        "anchor_count": len(records),
        "anchors": records,
        "separability": _separability(records),
        "support_and_null_counts": {
            "anchors_available": len(records),
            "anchors_unavailable": len(D041_ANCHOR_IDS) - len(records),
            "pair_reacquired": sum(
                int(branch_reacquired(record, D041_PRIMARY_BRANCH))
                for record in records
            ),
            "s0_reacquired": sum(
                int(branch_reacquired(record, D041_COMPARISON_BRANCH))
                for record in records
            ),
        },
    }


def _support_summary(results: Sequence[dict[str, object]]) -> dict[str, object]:
    anchors = [
        anchor
        for result in results
        for anchor in cast(list[dict[str, object]], result["anchors"])
    ]
    classifications: dict[str, int] = {}
    for anchor in anchors:
        effect = cast(dict[str, object], anchor["pair_effect_vs_s0"])
        classification = str(effect["classification"])
        classifications[classification] = classifications.get(classification, 0) + 1
    identity_pass = all(
        bool(cast(dict[str, object], result["canonical_identity"])["passed"])
        for result in results
    )
    branch_controls_pass = all(
        bool(cast(dict[str, object], anchor["controls"])["branch_order_invariant"])
        and bool(cast(dict[str, object], anchor["controls"])["source_anchor_unchanged"])
        for anchor in anchors
    )
    pair_only = classifications.get("PAIR_ONLY", 0)
    pair_only_regimes = {
        str(anchor["anchor_id"])
        for anchor in anchors
        if str(cast(dict[str, object], anchor["pair_effect_vs_s0"])["classification"])
        == "PAIR_ONLY"
    }
    robust_pair = (
        pair_only >= 2
        and len({str(result["seed"]) for result in results}) >= 2
        and len(pair_only_regimes) >= 2
    )
    if not identity_pass or not branch_controls_pass:
        interpretation = "INVALID"
    elif robust_pair:
        interpretation = "PARTIAL"
    else:
        interpretation = "NULL/INSUFFICIENT"
    return {
        "anchor_count": len(anchors),
        "pair_effect_classifications": classifications,
        "canonical_identity_all_passed": identity_pass,
        "branch_controls_all_passed": branch_controls_pass,
        "pair_only_support": pair_only,
        "interpretation": interpretation,
        "interpretation_rule": (
            "D-041 does not call pair-only improvement SUFFICIENT unless it is "
            "reproducible across at least two seeds and two frozen anchor regimes; "
            "this implementation reports PARTIAL pending broader boundary review."
        ),
    }


def build_artifact(
    results: Sequence[dict[str, object]],
    *,
    support: str,
    executed_commit_sha: str,
) -> dict[str, object]:
    if support not in ("reused", "holdout"):
        raise ValueError("support must be reused or holdout")
    seeds = D041_REUSED_SEEDS if support == "reused" else D041_HOLDOUT_SEEDS
    return {
        "schema_version": 1,
        "experiment": "D-041",
        "protocol_version": D041_PROTOCOL_VERSION,
        "authorized_base_sha": D041_AUTHORITATIVE_BASE_SHA,
        "clean_executable_protocol_sha": executed_commit_sha,
        "support_executed": support,
        "seed_role": (
            "fresh_development_holdout"
            if support == "holdout"
            else "reused_development_support"
        ),
        "ordered_seeds": list(seeds),
        "lifetime_horizon": D041_HORIZON,
        "anchor_replay_horizon": D041_ANCHOR_REPLAY_HORIZON,
        "branch_horizon": D041_BRANCH_HORIZON,
        "branch_horizons": list(D041_HORIZONS),
        "anchor_ids": list(D041_ANCHOR_IDS),
        "receptor_model": {
            "placement_body_frame": {
                "left": list(D041_RECEPTOR_LEFT_BODY),
                "right": list(D041_RECEPTOR_RIGHT_BODY),
            },
            "normal_body_frame": list(D041_RECEPTOR_NORMAL_BODY),
            "beacon_source": "D-024 station centre point emitter",
            "response": (
                "clip(max(0, cosine_front) * max(0, 1 - distance / range), 0, 1)"
            ),
            "range": D041_BEACON_RANGE,
            "occlusion": False,
            "noise": False,
            "out_of_range_signal": 0.0,
        },
        "readout": {
            "primary": "PAIR",
            "rule": (
                "left>right TURN_LEFT; right>left TURN_RIGHT; equal positive "
                "MOVE_FORWARD; equal zero WAIT"
            ),
            "uses_only_receptor_pair": True,
            "uses_distance_bearing_pose_heading": False,
            "history": "none",
        },
        "branches": list(D041_BRANCHES),
        "source_artifacts": {
            "d040_reused_artifact_sha256": D041_D040_REUSED_ARTIFACT_SHA256,
            "d040_anchor_runner": "aweform.d040._independent_arm_b",
        },
        "canonical_boundary": {
            "organism_observation_changed": False,
            "controller_changed": False,
            "learner_changed": False,
            "action_space_changed": False,
            "energy_thermal_reward_info_rng_changed": False,
            "receptor_values_reach_organism": False,
        },
        "results": list(results),
        "separability": _separability(
            [
                anchor
                for result in results
                for anchor in cast(list[dict[str, object]], result["anchors"])
            ]
        ),
        "support_summary": _support_summary(results),
        "interpretation_categories": [
            "SUFFICIENT",
            "PARTIAL",
            "NULL/INSUFFICIENT",
            "INVALID",
        ],
        "evaluator_only": True,
        "reward": 0.0,
        "info": {},
        "working_tree_clean_at_execution": True,
    }


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def run_d041_audit(
    *,
    support: str = "reused",
    executed_commit_sha: str | None = None,
) -> dict[str, object]:
    sha = _validate_executed_commit_sha(executed_commit_sha)
    if support == "reused":
        seeds = _validate_seed_block(D041_REUSED_SEEDS, D041_REUSED_SEEDS, "reused")
    elif support == "holdout":
        seeds = _validate_seed_block(D041_HOLDOUT_SEEDS, D041_HOLDOUT_SEEDS, "holdout")
    else:
        raise ValueError("support must be reused or holdout")
    results = [_seed_result(seed) for seed in seeds]
    return build_artifact(results, support=support, executed_commit_sha=sha)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the D-041 sensory audit")
    parser.add_argument("--support", choices=("reused", "holdout"), default="reused")
    parser.add_argument("--executed-commit-sha", required=True)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    payload = run_d041_audit(
        support=args.support, executed_commit_sha=args.executed_commit_sha
    )
    if args.output is None:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        write_json(args.output, payload)
        print(f"D-041 result written to {args.output}")


if __name__ == "__main__":
    main()
