"""D-057 evaluator-only boundary-rule counterfactual diagnostic.

The canonical D-045 substrate and all controller implementations are imported
unchanged. R1/R2 exist only as post-step reductions in this harness.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path
from typing import Any, Final

import numpy as np

from . import d053, d054, d055, d056
from .d045 import (
    D045_AMBIENT_TEMPERATURE_C,
    D045_BATTERY_CAPACITY_J,
    D045_DT_SECONDS,
    D045ChargePhase,
    D045Env,
    D045PhysicalConfig,
)
from .d049 import D049_STATION_CENTER
from .d050 import D050ControlMode
from .d052 import D052CommandSource, D052Controller, D052Mode
from .d055 import D055StallTurnCandidate

D057_ID: Final = "D-057"
PROTOCOL_VERSION: Final = "d057-v05-boundary-rule-counterfactual-v1"
BASE_SHA: Final = "c11022ad167ac7bfb17748bc8e1de3463b1aa61d"
PART_A_HORIZON: Final = 1000
PART_B_HORIZON: Final = 1000
RULES: Final = ("R0", "R1", "R2")
ARMS: Final = ("U", "C")
FRESH: Final = tuple(range(22600, 22620))
SUPPORT: Final = (22053, 22054, 22055, 22056, 22057)
TEST_SEED: Final = 22620
PROTECTED: Final = tuple(
    f"src/aweform/{n}"
    for n in (
        "d045.py",
        "d049.py",
        "d050.py",
        "d052.py",
        "d053.py",
        "d054.py",
        "d055.py",
        "d056.py",
        "development_visualizer.py",
    )
)


def _inside(p: tuple[float, float]) -> bool:
    return 0.0 <= p[0] <= 1.0 and 0.0 <= p[1] <= 1.0


def _clamp(p: tuple[float, float]) -> tuple[float, float]:
    return min(1.0, max(0.0, p[0])), min(1.0, max(0.0, p[1]))


def reduce_r1(
    p0: tuple[float, float], pfull: tuple[float, float]
) -> tuple[float, float]:
    """Yaw-free chord stop: stop translation at the first arena boundary."""
    if _inside(pfull):
        return pfull
    fractions: list[float] = []
    for i in (0, 1):
        if pfull[i] < 0.0 or pfull[i] > 1.0:
            bound = 0.0 if pfull[i] < 0.0 else 1.0
            den = pfull[i] - p0[i]
            if den == 0.0:
                raise RuntimeError("violated endpoint has zero displacement")
            fractions.append((bound - p0[i]) / den)
    if not fractions:
        raise RuntimeError("outside endpoint without violated axis")
    s = min(1.0, max(0.0, min(fractions)))
    return _clamp((p0[0] + s * (pfull[0] - p0[0]), p0[1] + s * (pfull[1] - p0[1])))


def reduce_r2(pfull: tuple[float, float]) -> tuple[float, float]:
    """Endpoint-clamped tangential-retention counterfactual; not physical sliding."""
    return _clamp(pfull)


def _reset(
    position: tuple[float, float],
    heading: float,
    battery: float,
    temperature: float,
    horizon: int,
    rule: str,
) -> tuple[D045Env, np.ndarray]:
    config = D045PhysicalConfig(
        episode_horizon=horizon,
        **(
            {"world_min": (-1.0, -1.0), "world_max": (2.0, 2.0)} if rule != "R0" else {}
        ),
    )
    env = D045Env(config)
    obs, info = env.reset(
        options={
            "body_position": position,
            "station_center": D049_STATION_CENTER,
            "heading": heading,
            "battery_j": battery,
            "body_temperature_c": temperature,
            "charger_termination_latched": False,
        }
    )
    if info != {} or env.body is None:
        raise RuntimeError("reset/info/body contract failed")
    env.body.heading = heading
    return env, env._observation().as_array()


def _controller(arm: str) -> tuple[D052Controller, D055StallTurnCandidate | None]:
    base = D052Controller()
    return (base, None) if arm == "U" else (base, D055StallTurnCandidate(base))


def _run(
    case_id: str,
    position: tuple[float, float],
    heading: float,
    battery: float,
    temperature: float,
    inset: float,
    boundary_class: str,
    arm: str,
    rule: str,
    horizon: int,
    *,
    capture: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    env, obs = _reset(position, heading, battery, temperature, horizon, rule)
    base, wrapped = _controller(arm)
    transitions = scaled = reductions = 0
    first_scaled: int | None = None
    minimum_scale = 1.0
    path = energy = 0.0
    centres: list[tuple[float, float]] = []
    trace: list[dict[str, Any]] = []
    detections = turns = 0
    outcome = "HORIZON_CENSORED"
    prev_pose: tuple[float, float, float] | None = None
    while transitions < horizon:
        emitted = wrapped.command(obs, (0.0, 0.0)) if wrapped else None
        decision = emitted.decision if emitted else base.command(obs, (0.0, 0.0))
        if transitions == 0 and "RETURN_ACTIVATED" not in decision.events:
            raise RuntimeError("RETURN activation required on first decision")
        if (
            transitions
            and decision.active_mode is not D052Mode.RETURN
            and "CHARGING_CONTACT" not in decision.events
        ):
            raise RuntimeError("unexpected non-RETURN decision")
        wheels = (
            emitted.wheels
            if emitted
            else (decision.wheel_delta_left, decision.wheel_delta_right)
        )
        if decision.command_source is D052CommandSource.RETURN_HOLD:
            outcome = "TERMINAL_SPIN_EXHAUSTED"
            transitions += 1
            break
        if decision.command_source is D052CommandSource.CHARGE_HOLD:
            outcome = "DOCKED"
            break
        if env.body is None:
            raise RuntimeError("body missing")
        before = (env.body.x, env.body.y, env.body.heading)
        obs_step, reward, terminated, truncated, info = env.step(wheels)
        t = env.last_transition
        if t is None or reward != 0.0 or info != {}:
            raise RuntimeError("step contract/info boundary failed")
        if rule != "R0" and t.boundary_scale != 1.0:
            raise RuntimeError("control 3 widened bounds bound")
        if rule != "R0" and prev_pose is not None:
            if (
                tuple(t.position_before) != prev_pose[:2]
                or t.heading_before != prev_pose[2]
            ):
                raise RuntimeError("control 4b pose discontinuity")
        raw_after = (env.body.x, env.body.y)
        pfull = raw_after
        if rule == "R1":
            reduced = reduce_r1((before[0], before[1]), pfull)
        elif rule == "R2":
            reduced = reduce_r2(pfull)
        else:
            reduced = raw_after
        changed = reduced != raw_after
        if changed:
            if (
                t.charging_contact_before
                or t.charging_contact_after
                or env.charging_contact
            ):
                raise RuntimeError("control 5 contact changed/active at reduction")
            if obs_step[5] != float(env.charging_contact):
                raise RuntimeError("contact observation mismatch")
            no_contact = env._charge_decision(False, t.battery_before_j)
            if (
                t.charge_phase is not no_contact.phase
                or t.charge_phase is not D045ChargePhase.OFF
                or t.actual_stored_power_w != 0.0
                or t.charger_input_power_w != 0.0
                or t.charging_body_heat_w != 0.0
                or t.charger_termination_latched_after
            ):
                raise RuntimeError("control 5b stale charge consequence")
            env.body.x, env.body.y = reduced
            reductions += 1
        obs = env._observation().as_array() if rule != "R0" else obs_step
        if rule != "R0" and not np.array_equal(obs, env._observation().as_array()):
            raise RuntimeError("post-reduction observation mismatch")
        transitions += 1
        actual_pose = (env.body.x, env.body.y, env.body.heading)
        prev_pose = actual_pose
        delta = math.dist(before[:2], actual_pose[:2])
        path += delta
        centres.append(actual_pose[:2])
        energy += t.actuator_electrical_power_w * D045_DT_SECONDS
        minimum_scale = min(minimum_scale, t.boundary_scale)
        if t.boundary_scale < 1.0:
            scaled += 1
            if first_scaled is None:
                first_scaled = transitions
        if emitted:
            detections += int(emitted.stall_detected)
            turns += int(emitted.stall_turned)
        if capture:
            trace.append(
                {
                    "command": list(wheels),
                    "pose_before": list(before),
                    "pose_after": list(actual_pose),
                    "battery": t.battery_after_j,
                    "observation": obs.tolist(),
                    "scale": t.boundary_scale,
                    "changed": changed,
                    "transition": transitions,
                }
            )
        if obs[5] == 1.0:
            outcome = "DOCKED"
        elif decision.d050_mode is D050ControlMode.INVALID_BEACON:
            outcome = "INVALID_BEACON"
        elif terminated:
            outcome = "TERMINATED_" + (
                t.termination_reason.value if t.termination_reason else "UNKNOWN"
            )
        elif truncated:
            outcome = "HORIZON_CENSORED"
        if outcome != "HORIZON_CENSORED":
            break
    pos = env.body.position if env.body else position
    theta = env.body.heading if env.body else heading
    pinned = (
        min(pos[0], pos[1], 1 - pos[0], 1 - pos[1]) <= d054.D054_BOUNDARY_TOLERANCE_M
    )
    tail = centres[-101:]
    tail_path = sum(math.dist(a, b) for a, b in zip(tail, tail[1:]))
    record: dict[str, Any] = {
        "case_id": case_id,
        "inset_m": inset,
        "boundary_class": boundary_class,
        "outcome": outcome,
        "outcome_transition": transitions,
        "first_boundary_scaled_transition": first_scaled,
        "boundary_scaled_transition_count": scaled,
        "minimum_boundary_scale": minimum_scale,
        "counterfactual_centre_reduction_count": reductions,
        "path_length_m": path,
        "actuator_energy_j": energy,
        "final_position": list(pos),
        "final_heading": theta,
        "final_station_distance_m": math.dist(pos, D049_STATION_CENTER),
        "wall_pinned_at_end": pinned,
        "final_100_centre_path_m": tail_path,
        "WEDGED": outcome != "DOCKED" and pinned and tail_path <= 1e-9,
    }
    if wrapped:
        record.update(
            stall_detected_count=detections,
            stall_turn_count=turns,
            stall_detected_non_pursuit_count=wrapped.stall_detected_non_pursuit_count,
            first_stall_turn_transition=wrapped.first_stall_turn_transition,
        )
    env.close()
    return record, trace


def validate_test_run(seed: int, horizon: int, battery_fraction: float) -> None:
    if (
        seed != TEST_SEED
        or not 0 < horizon <= 5000
        or not 0 <= battery_fraction <= 0.21
    ):
        raise ValueError(
            "D-057 test runs restricted to seed 22620, horizon <=5000, battery <=0.21"
        )


def _canon(x: object) -> object:
    if isinstance(x, dict):
        return {k: _canon(v) for k, v in sorted(x.items())}
    if isinstance(x, (list, tuple)):
        return [_canon(v) for v in x]
    return d053._canonicalize(x)


def _prior_json(name: str) -> dict[str, Any]:
    return json.loads(
        (Path(__file__).resolve().parents[2] / "development" / name).read_text()
    )


def _part_a() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cases = d054.frozen_cases()
    previous = _prior_json("D-055-v05-return-proprioceptive-stall-turn-candidate.json")
    prior = {(r["arm"], r["case_id"]): r for r in previous["part_a"]["per_run"]}
    rows: list[dict[str, Any]] = []
    traces: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for case in cases:
        for arm in ARMS:
            for rule in RULES:
                row, trace = _run(
                    case.case_id,
                    case.position,
                    case.heading,
                    0.20 * D045_BATTERY_CAPACITY_J,
                    D045_AMBIENT_TEMPERATURE_C,
                    case.inset,
                    case.boundary_class,
                    arm,
                    rule,
                    PART_A_HORIZON,
                    capture=True,
                )
                row.update(arm=arm, rule=rule, part="A")
                if rule == "R0":
                    old = prior[(arm, case.case_id)]
                    shared = set(row) & set(old)
                    if _canon({k: row[k] for k in shared}) != _canon(
                        {k: old[k] for k in shared}
                    ):
                        raise RuntimeError("control 2 D-055 per-run identity failed")
                traces[(case.case_id, arm, rule)] = trace
                rows.append(row)
    for case in cases:
        for arm in ARMS:
            baseline = traces[(case.case_id, arm, "R0")]
            first_scaled = next(
                (i for i, t in enumerate(baseline) if t["scale"] < 1.0), None
            )
            limit = len(baseline) if first_scaled is None else first_scaled
            for rule in ("R1", "R2"):
                candidate = traces[(case.case_id, arm, rule)]
                if len(candidate) < limit or baseline[:limit] != candidate[:limit]:
                    raise RuntimeError("control 4 R1/R2 prefix identity failed")
            ctrace = traces[(case.case_id, "C", "R0")]
            utr = traces[(case.case_id, "U", "R0")]
            crow = next(
                r
                for r in rows
                if r["case_id"] == case.case_id
                and r["arm"] == "C"
                and r["rule"] == "R0"
            )
            if crow["stall_detected_count"] == 0 and ctrace != utr:
                raise RuntimeError("control 2 no-detection C/U trace identity failed")
    controls = {
        "r0_committed_identity": "PASS",
        "widened_bounds_inertness": "PASS",
        "r1_r2_prefix_identity": "PASS",
        "pose_continuity": "PASS",
        "contact_isolation": "PASS",
        "no_stale_charge_consequence": "PASS",
        "no_detection_trace_identity": "PASS",
    }
    return rows, controls


def _round(value: Any) -> Any:
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("nonfinite artifact float")
        result = float(
            Decimal(value).quantize(Decimal("1e-12"), rounding=ROUND_HALF_EVEN)
        )
        return 0.0 if result == 0.0 else result
    if isinstance(value, dict):
        return {k: _round(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_round(v) for v in value]
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--executed-commit-sha", required=True)
    args = parser.parse_args()
    if len(args.executed_commit_sha) != 40:
        raise ValueError("expected exact commit SHA")
    payload = run_protocol(args.executed_commit_sha)
    Path(args.output).write_text(
        json.dumps(_round(payload), sort_keys=True, indent=2) + "\n"
    )


def run_protocol(executed_commit_sha: str) -> dict[str, Any]:
    """Official runner; every STOP control raises before artifact writing."""
    if len(executed_commit_sha) != 40 or any(
        c not in "0123456789abcdef" for c in executed_commit_sha
    ):
        raise ValueError("executed_commit_sha must be a lowercase 40-character SHA")
    part_a, controls = _part_a()
    # Part B is appended by the frozen lifetime-state extractor below.
    part_b, bcontrols = _part_b()
    controls.update(bcontrols)
    signature, aggregates = _readouts(part_a, part_b)
    return {
        "schema_version": "d057-v1",
        "development_id": D057_ID,
        "protocol_version": PROTOCOL_VERSION,
        "authorized_base_sha": BASE_SHA,
        "executed_commit_sha": executed_commit_sha,
        "execution_status": "COMPLETED",
        "result_kind": "descriptive evaluator-only counterfactual Development",
        "constants": {
            "world_min": [0.0, 0.0],
            "world_max": [1.0, 1.0],
            "counterfactual_world_min": [-1.0, -1.0],
            "counterfactual_world_max": [2.0, 2.0],
            "station_center": list(D049_STATION_CENTER),
            "part_a_initial_battery_fraction": 0.20,
            "part_a_temperature_c": D045_AMBIENT_TEMPERATURE_C,
            "boundary_tolerance_m": d054.D054_BOUNDARY_TOLERANCE_M,
            "wheel_delta_floor_rad": d055.STALL_COMMAND_FLOOR,
            "float_quantum": "1e-12",
            "float_rounding": "ROUND_HALF_EVEN",
        },
        "frozen_protocol": {
            "part_a_horizon": PART_A_HORIZON,
            "part_b_horizon": PART_B_HORIZON,
            "rules": list(RULES),
            "arms": list(ARMS),
            "fresh_seeds": list(FRESH),
            "support_seeds": list(SUPPORT),
            "r2_label": (
                "yaw-free endpoint-clamped tangential-retention counterfactual; "
                "not physical sliding"
            ),
        },
        "controls": controls,
        "part_a": {"per_run": part_a, "aggregates": aggregates["A"]},
        "part_b": {"per_run": part_b, "aggregates": aggregates["B"]},
        "discrete_signature": signature,
        "interpretation": aggregates["interpretation"],
        "claims_boundary": (
            "No confirmatory claim, physical-contact or sliding model, substrate "
            "change, or organism-visible evaluator information."
        ),
    }


def _replay_window_end(activation: int, end: int) -> int:
    """Inclusive last official transition replayed by a Part-B branch.

    Branch step k replays official transition ``activation + k - 1``, so a
    ``PART_B_HORIZON``-step branch covers at most ``activation`` through
    ``activation + PART_B_HORIZON - 1``.
    """
    return min(end, activation + PART_B_HORIZON - 1)


def _part_b() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    # Full extractor and replay controls are implemented here to keep lifetime
    # execution delegated to the unchanged D-053 runner.
    prior = _prior_json("D-056-v05-multi-cycle-stall-turn-lifetimes.json")
    summaries = {
        (x["seed"]): x["summary"] for x in prior["lifetimes"] if x["arm"] == "U"
    }
    episodes = {
        (x["seed"], x["cycle_index"]): x for x in prior["episodes"] if x["arm"] == "U"
    }
    c_episodes = {
        (x["seed"], x["cycle_index"]): x for x in prior["episodes"] if x["arm"] == "C"
    }
    rows = []
    replay_checked = wedged_checked = 0
    d056.validate_fresh_seeds(FRESH)
    d056.validate_support_seeds(SUPPORT)
    activation_total = fresh_activations = support_activations = 0
    for seed in (*FRESH, *SUPPORT):
        lifetime = d053.run_d053_lifetime(seed, horizon=300_000)
        if _canon(lifetime.summary) != _canon(summaries[seed]):
            raise RuntimeError(f"6a summary mismatch seed {seed}")
        activation_rows = [
            r for r in lifetime.trace if "RETURN_ACTIVATED" in r.get("events", [])
        ]
        activation_total += len(activation_rows)
        if seed in FRESH:
            fresh_activations += len(activation_rows)
        else:
            support_activations += len(activation_rows)
        for cycle_index, activation_row in enumerate(activation_rows, start=1):
            activation = int(activation_row["transition"])
            restore_row = lifetime.trace[activation - 1]
            pos = (float(restore_row["x"]), float(restore_row["y"]))
            heading = float(restore_row["heading"])
            battery = float(restore_row["battery_after_j"])
            temperature = float(restore_row["thermal"]) * 80.0
            episode = episodes[(seed, cycle_index)]
            end = int(
                episode.get("first_charging_contact_transition")
                or episode.get("end_transition", activation + PART_B_HORIZON)
            )
            compare_end = _replay_window_end(activation, end)
            expected = {
                int(r["transition"]): r
                for r in lifetime.trace
                if activation <= int(r["transition"]) <= compare_end
            }
            branch_traces: dict[tuple[str, str], list[dict[str, Any]]] = {}
            # Process one activation's bounded trace window, then release it.
            for arm in ARMS:
                for rule in RULES:
                    r, trace = _run(
                        f"seed-{seed}-activation-{activation}",
                        pos,
                        heading,
                        battery,
                        temperature,
                        0.0,
                        "lifetime",
                        arm,
                        rule,
                        PART_B_HORIZON,
                        capture=True,
                    )
                    if arm == "U" and rule == "R0":
                        branch_class = (
                            "DOCKED"
                            if r["outcome"] == "DOCKED"
                            else ("WEDGED" if r["WEDGED"] else r["outcome"])
                        )
                        if branch_class != episode["class"]:
                            raise RuntimeError("6b restored branch class mismatch")
                        for step in trace:
                            official = expected.get(step["transition"] + activation - 1)
                            if official is None:
                                raise RuntimeError(
                                    "6b replay window missing lifetime row"
                                )
                            cmd = official["wheel_command"]
                            actual = step["command"]
                            if any(
                                float(a).hex() != float(b).hex()
                                for a, b in zip(cmd, actual)
                            ):
                                raise RuntimeError("6b wheel command replay mismatch")
                            for key, val in (
                                ("x", step["pose_after"][0]),
                                ("y", step["pose_after"][1]),
                                ("heading", step["pose_after"][2]),
                                ("battery_after_j", step["battery"]),
                            ):
                                if float(official[key]).hex() != float(val).hex():
                                    raise RuntimeError(f"6b {key} replay mismatch")
                        if len(trace) != len(expected):
                            raise RuntimeError("6b replay transition count mismatch")
                        replay_checked += 1
                    if arm == "C" and rule == "R0" and episode["class"] == "WEDGED":
                        ce = c_episodes[(seed, cycle_index)]
                        if r["outcome"] != "DOCKED" or r.get(
                            "stall_turn_count"
                        ) != ce.get("stall_turn_count"):
                            raise RuntimeError(
                                "6c candidate wedge-state docking/stall count mismatch"
                            )
                        wedged_checked += 1
                    r.update(
                        seed=seed,
                        block="fresh" if seed in FRESH else "support",
                        activation_transition=activation,
                        cycle_index=cycle_index,
                        arm=arm,
                        rule=rule,
                        part="B",
                        committed_class=episode["class"],
                    )
                    rows.append(r)
                    branch_traces[(arm, rule)] = trace
            for arm in ARMS:
                baseline = branch_traces[(arm, "R0")]
                first_scaled = next(
                    (i for i, t in enumerate(baseline) if t["scale"] < 1.0), None
                )
                limit = len(baseline) if first_scaled is None else first_scaled
                for rule in ("R1", "R2"):
                    candidate = branch_traces[(arm, rule)]
                    if len(candidate) < limit or candidate[:limit] != baseline[:limit]:
                        raise RuntimeError(
                            "control 4 Part-B R1/R2 prefix identity failed"
                        )
            for rule in RULES:
                c_row = next(
                    r
                    for r in rows
                    if r.get("seed") == seed
                    and r.get("activation_transition") == activation
                    and r.get("arm") == "C"
                    and r.get("rule") == rule
                )
                if (
                    c_row.get("stall_detected_count", 0) == 0
                    and branch_traces[("C", rule)] != branch_traces[("U", rule)]
                ):
                    raise RuntimeError(
                        "control 4 Part-B dormant C/U trace identity failed"
                    )
            del branch_traces
        del lifetime
    if (activation_total, fresh_activations, support_activations) != (50, 39, 11):
        raise RuntimeError("Part-B activation-state count control failed")
    return rows, {
        "lifetime_summary_identity": "PASS",
        "u_r0_replay_fidelity": "PASS",
        "c_r0_wedged_episode_identity": "PASS",
        "u_r0_replay_count": replay_checked,
        "c_r0_wedged_count": wedged_checked,
    }


def _readouts(
    a: list[dict[str, Any]], b: list[dict[str, Any]]
) -> tuple[dict[str, str], dict[str, Any]]:
    parts = {"A": a, "B": b}
    agg = {}
    sig = {}
    for part, rows in parts.items():
        agg[part] = {}
        for arm in ARMS:
            for rule in RULES:
                group = [r for r in rows if r["arm"] == arm and r["rule"] == rule]
                agg[part][f"{arm}_{rule}"] = {
                    "outcomes": dict(
                        sorted(Counter(r["outcome"] for r in group).items())
                    ),
                    "wedged": sum(bool(r["WEDGED"]) for r in group),
                    "counterfactual_reductions": sum(
                        r["counterfactual_centre_reduction_count"] for r in group
                    ),
                }
    for rule in ("R1", "R2"):
        for part in ("A", "B"):
            rows = parts[part]
            for arm in ARMS:
                base = {
                    r["case_id"]
                    if part == "A"
                    else (r["seed"], r["activation_transition"]): r
                    for r in rows
                    if r["arm"] == arm and r["rule"] == "R0"
                }
                alt = {
                    r["case_id"]
                    if part == "A"
                    else (r["seed"], r["activation_transition"]): r
                    for r in rows
                    if r["arm"] == arm and r["rule"] == rule
                }
                keys = base.keys() & alt.keys()
                resolution = sum(
                    base[k]["outcome"] != "DOCKED" and alt[k]["outcome"] == "DOCKED"
                    for k in keys
                )
                harm = sum(
                    base[k]["outcome"] == "DOCKED" and alt[k]["outcome"] != "DOCKED"
                    for k in keys
                )
                denominator = sum(base[k]["outcome"] != "DOCKED" for k in keys)
                docked = sum(base[k]["outcome"] == "DOCKED" for k in keys)
                pair_counts = Counter(
                    f"{base[k]['outcome']}__{alt[k]['outcome']}" for k in keys
                )
                docked_deltas = [
                    alt[k]["outcome_transition"] - base[k]["outcome_transition"]
                    for k in keys
                    if base[k]["outcome"] == alt[k]["outcome"] == "DOCKED"
                ]
                energy_deltas = [
                    alt[k]["actuator_energy_j"] - base[k]["actuator_energy_j"]
                    for k in keys
                    if base[k]["outcome"] == alt[k]["outcome"] == "DOCKED"
                ]
                agg[part].setdefault("paired", {})[f"{arm}_{rule}"] = {
                    "resolution_count": resolution,
                    "resolution_denominator": denominator,
                    "harm_count": harm,
                    "harm_denominator": docked,
                    "cross_tab": dict(sorted(pair_counts.items())),
                    "both_docked_transition_delta": docked_deltas,
                    "both_docked_actuator_energy_delta_j": energy_deltas,
                }
                if arm == "U":
                    sig[f"{part}_U_{rule}_RESOLUTION"] = (
                        "ALL"
                        if resolution == denominator and denominator
                        else "NONE"
                        if resolution == 0
                        else "PARTIAL"
                    )
                    sig[f"{part}_U_{rule}_HARM"] = "NONE" if harm == 0 else "SOME"
            c = [r for r in rows if r["arm"] == "C" and r["rule"] == rule]
            agg[part].setdefault("candidate_diagnostics", {})[rule] = {
                "stall_detections": sum(r.get("stall_detected_count", 0) for r in c),
                "stall_turns": sum(r.get("stall_turn_count", 0) for r in c),
                "non_pursuit_detections": sum(
                    r.get("stall_detected_non_pursuit_count", 0) for r in c
                ),
            }
        detections = sum(
            agg[part]["candidate_diagnostics"][rule]["stall_detections"]
            for part in ("A", "B")
        )
        sig[f"C_{rule}_DORMANT"] = "YES" if detections == 0 else "NO"
    supported = any(
        all(
            sig[f"{p}_U_{r}_RESOLUTION"] == "ALL" and sig[f"{p}_U_{r}_HARM"] == "NONE"
            for p in ("A", "B")
        )
        for r in ("R1", "R2")
    )
    agg["interpretation"] = (
        "BOUNDARY_RULE_ARTIFACT_SUPPORTED"
        if supported
        else "STRONG_ARTIFACT_CRITERION_NOT_MET"
    )
    return sig, agg


if __name__ == "__main__":
    main()
