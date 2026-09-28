"""D-054 evaluator-only diagnosis of D-053's boundary-adjacent return failure.

Both controller arms and the physical substrate are imported unchanged. This
module owns only the frozen evaluator harness and its post-hoc analysis.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Final, TypedDict, cast

import numpy as np

from .d045 import (
    D045_AMBIENT_TEMPERATURE_C,
    D045_BATTERY_CAPACITY_J,
    D045_DT_SECONDS,
    D045_ELECTRONICS_POWER_W,
    D045Env,
    D045PhysicalConfig,
)
from .d049 import D049_STATION_CENTER, D049_TERMINAL_SPIN_MAX_STEPS
from .d050 import (
    D050BaselineController,
    D050ControlMode,
    D050SmoothController,
)
from .d053 import _canonicalize, run_d053_lifetime

D054_ID: Final[str] = "D-054"
D054_PROTOCOL_VERSION: Final[str] = "d054-v05-return-boundary-wedge-diagnosis-v1"
D054_ARTIFACT_FLOAT_QUANTUM: Final[Decimal] = Decimal("1e-12")
D054_HORIZON: Final[int] = 1000
D054_MATRIX_INSETS: Final[tuple[float, ...]] = (0.0, 0.05)
D054_ALONG_WALL: Final[tuple[float, ...]] = (0.10, 0.30, 0.50, 0.70, 0.90)
D054_HEADINGS: Final[tuple[float, ...]] = tuple(
    (2 * k + 1) * math.pi / 16.0 for k in range(16)
)
D054_STATION: Final[tuple[float, float]] = D049_STATION_CENTER


@dataclass(frozen=True, slots=True)
class D054Case:
    case_id: str
    inset: float
    boundary_class: str
    position: tuple[float, float]
    heading: float


class D054Restore(TypedDict):
    transition: int
    position: tuple[float, float]
    heading: float
    battery_j: float
    temperature_c_approximate: float


def frozen_cases() -> tuple[D054Case, ...]:
    """Return 48 geometry-fixed positions crossed with 16 headings."""
    positions: list[tuple[str, float, tuple[float, float]]] = []
    for inset in D054_MATRIX_INSETS:
        for along in D054_ALONG_WALL:
            positions.extend(
                (
                    ("bottom_wall", inset, (along, inset)),
                    ("top_wall", inset, (along, 1.0 - inset)),
                    ("left_wall", inset, (inset, along)),
                    ("right_wall", inset, (1.0 - inset, along)),
                )
            )
        positions.extend(
            (
                ("corner_bottom_left", inset, (inset, inset)),
                ("corner_bottom_right", inset, (1.0 - inset, inset)),
                ("corner_top_left", inset, (inset, 1.0 - inset)),
                ("corner_top_right", inset, (1.0 - inset, 1.0 - inset)),
            )
        )
    return tuple(
        D054Case(
            case_id=f"{kind}-i{inset:.2f}-p{position[0]:.2f}-{position[1]:.2f}-h{index:02d}",
            inset=inset,
            boundary_class="corner" if kind.startswith("corner") else "wall",
            position=position,
            heading=heading,
        )
        for kind, inset, position in positions
        for index, heading in enumerate(D054_HEADINGS)
    )


def _wall_label(position: tuple[float, float]) -> str:
    x, y = position
    edges: list[str] = []
    if y == 0.0:
        edges.append("bottom")
    if y == 1.0:
        edges.append("top")
    if x == 0.0:
        edges.append("left")
    if x == 1.0:
        edges.append("right")
    if len(edges) > 1:
        return "corner_" + "_".join(edges)
    return f"{edges[0]}_wall" if edges else "inset"


def _bearing_error(position: tuple[float, float], heading: float) -> float:
    dx, dy = D054_STATION[0] - position[0], D054_STATION[1] - position[1]
    bearing = math.atan2(dy, dx)
    return math.atan2(math.sin(bearing - heading), math.cos(bearing - heading))


def _outward_component(position: tuple[float, float], heading: float) -> float:
    x, y = position
    components: list[float] = []
    if x == 0.0:
        components.append(-math.cos(heading))
    if x == 1.0:
        components.append(math.cos(heading))
    if y == 0.0:
        components.append(-math.sin(heading))
    if y == 1.0:
        components.append(math.sin(heading))
    return max(components, default=0.0)


def is_absorbing_step(
    *,
    command: tuple[float, float],
    boundary_scale: float,
    before: tuple[float, float, float],
    after: tuple[float, float, float],
) -> bool:
    """Classify only an executed non-zero command with exact zero-motion scale."""
    return (
        command != (0.0, 0.0)
        and boundary_scale == 0.0
        and all(a.hex() == b.hex() for a, b in zip(before, after))
    )


@dataclass(frozen=True, slots=True)
class WrappedDecision:
    mode: D050ControlMode
    wheels: tuple[float, float]
    executed: bool
    exhausted: bool
    count_after: int


def wrapped_decision(
    controller: object, observation: np.ndarray, spin_count: int
) -> WrappedDecision:
    """Externally emulate the D-052 RETURN ordering for one decision."""
    command_method = getattr(controller, "command")
    decision = command_method(observation)
    mode = cast(D050ControlMode, decision.mode)
    wheels = (float(decision.wheel_delta_left), float(decision.wheel_delta_right))
    if mode is D050ControlMode.CONTACT:
        return WrappedDecision(mode, (0.0, 0.0), False, False, spin_count)
    if spin_count >= D049_TERMINAL_SPIN_MAX_STEPS:
        return WrappedDecision(mode, (0.0, 0.0), False, True, spin_count)
    return WrappedDecision(
        mode,
        wheels,
        True,
        False,
        spin_count + int(mode is D050ControlMode.TERMINAL_SPIN),
    )


def _reset_env(
    position: tuple[float, float],
    heading: float,
    battery_j: float,
    temperature_c: float,
    horizon: int,
) -> tuple[D045Env, np.ndarray]:
    env = D045Env(D045PhysicalConfig(episode_horizon=horizon))
    obs, info = env.reset(
        options={
            "body_position": position,
            "station_center": D054_STATION,
            "heading": heading,
            "battery_j": battery_j,
            "body_temperature_c": temperature_c,
            "charger_termination_latched": False,
        }
    )
    if info != {}:
        raise RuntimeError("D-045 organism-facing reset info was not empty")
    # Body construction wraps headings; restore the trace's exact evaluator
    # heading so replay compares the same floating-point state, not an angle
    # differing by an integer multiple of 2π.
    if env.body is None:
        raise RuntimeError("D-045 body unavailable after reset")
    env.body.heading = heading
    obs = env._observation().as_array()
    return env, obs


def _run_classified(
    case_id: str,
    position: tuple[float, float],
    heading: float,
    battery_j: float,
    temperature_c: float,
    controller: object,
    inset: float,
    boundary_class: str,
    horizon: int = D054_HORIZON,
) -> dict[str, object]:
    env, observation = _reset_env(position, heading, battery_j, temperature_c, horizon)
    spins = transitions = boundary_count = 0
    first_boundary: int | None = None
    minimum_scale = 1.0
    path_length = actuator_energy = 0.0
    outcome = "HORIZON_CENSORED"
    terminal_details: dict[str, object] | None = None
    while transitions < horizon:
        wrapped = wrapped_decision(controller, observation, spins)
        if wrapped.mode is D050ControlMode.CONTACT:
            outcome = "DOCKED"
            break
        if wrapped.exhausted:
            outcome = "TERMINAL_SPIN_EXHAUSTED"
            terminal_details = {
                "terminal_spin_count": spins,
                "suppressed_mode": wrapped.mode.value,
            }
            transitions += 1
            break
        before = (float(env.body.x), float(env.body.y), float(env.body.heading))  # type: ignore[union-attr]
        observation_after, reward, terminated, truncated, info = env.step(
            wrapped.wheels
        )
        transitions += 1
        if reward != 0.0 or info != {}:
            raise RuntimeError("D-045 reward/info contract changed")
        telemetry = env.last_transition
        if telemetry is None:
            raise RuntimeError("D-045 transition telemetry missing")
        observation = observation_after
        spins = wrapped.count_after
        path_length += math.dist(telemetry.position_before, telemetry.position_after)
        actuator_energy += telemetry.actuator_electrical_power_w * D045_DT_SECONDS
        minimum_scale = min(minimum_scale, telemetry.boundary_scale)
        if telemetry.boundary_scale < 1.0:
            boundary_count += 1
            if first_boundary is None:
                first_boundary = transitions
        after = (*telemetry.position_after, telemetry.heading_after)
        if observation[5] == 1.0:
            outcome = "DOCKED"
        elif is_absorbing_step(
            command=wrapped.wheels,
            boundary_scale=telemetry.boundary_scale,
            before=before,
            after=after,
        ):
            outcome = "ABSORBING_ZERO_MOTION"
            x, y, theta = after
            beta = _bearing_error((x, y), theta)
            terminal_details = {
                "position": [x, y],
                "heading": theta,
                "wall_or_corner": _wall_label((x, y)),
                "command": list(wrapped.wheels),
                "beta_eval_rad": beta,
                "outward_normal_component": _outward_component((x, y), theta),
                "observation_wheel_delta_left": float(observation[6]),
                "observation_wheel_delta_right": float(observation[7]),
                "proprioceptive_stall_visible": bool(
                    observation[6] == 0.0
                    and observation[7] == 0.0
                    and wrapped.wheels != (0.0, 0.0)
                ),
            }
        elif wrapped.mode is D050ControlMode.INVALID_BEACON:
            outcome = "INVALID_BEACON"
        elif terminated:
            reason = telemetry.termination_reason
            outcome = f"TERMINATED_{reason.value if reason else 'UNKNOWN'}"
        elif truncated:
            outcome = "HORIZON_CENSORED"
        if outcome != "HORIZON_CENSORED":
            break
    final_position = env.body.position if env.body is not None else position
    final_heading = env.body.heading if env.body is not None else heading
    record: dict[str, object] = {
        "case_id": case_id,
        "inset_m": inset,
        "boundary_class": boundary_class,
        "outcome": outcome,
        "outcome_transition": transitions,
        "first_boundary_scaled_transition": first_boundary,
        "boundary_scaled_transition_count": boundary_count,
        "minimum_boundary_scale": minimum_scale,
        "path_length_m": path_length,
        "actuator_energy_j": actuator_energy,
        "final_position": list(final_position),
        "final_heading": final_heading,
    }
    if terminal_details is not None:
        record["diagnostic"] = terminal_details
    env.close()
    return record


def _find_onset(trace: tuple[dict[str, object], ...]) -> int | None:
    by_transition = {cast(int, row["transition"]): row for row in trace}
    final_transition = max(by_transition)
    for transition in sorted(by_transition):
        row = by_transition[transition]
        if row.get("active_mode") != "RETURN" or transition == 0:
            continue
        command = row.get("wheel_command")
        if not isinstance(command, list) or command == [0.0, 0.0]:
            continue
        valid = True
        for index in range(transition, final_transition + 1):
            current, previous = by_transition.get(index), by_transition.get(index - 1)
            if current is None or previous is None:
                valid = False
                break
            if (
                current.get("boundary_scale") != 0.0
                or current.get("wheel_command") != command
            ):
                valid = False
                break
            if any(
                cast(float, current[key]).hex() != cast(float, previous[key]).hex()
                for key in ("x", "y", "heading")
            ):
                valid = False
                break
        if valid:
            return transition
    return None


def _part_a(lifetime: object, committed_record: dict[str, object]) -> dict[str, object]:
    summary = cast(dict[str, object], getattr(lifetime, "summary"))
    trace = cast(tuple[dict[str, object], ...], getattr(lifetime, "trace"))
    matches = _canonicalize(summary) == _canonicalize(committed_record)
    if not matches:
        raise RuntimeError("D-053 seed-22053 identity control failed")
    onset = _find_onset(trace)
    if onset is None:
        return {
            "identity_control": "PASS",
            "absorbing_onset_found": False,
            "h1_supported_for_seed": False,
            "trace_description": (
                "No transition met the frozen absorbing-onset definition; "
                "the official trace does not support a persistent zero-motion "
                "fixed point under the declared criterion."
            ),
        }
    rows = {cast(int, row["transition"]): row for row in trace}
    sample = rows[onset]
    previous = rows[onset - 1]
    pose = (
        cast(float, sample["x"]),
        cast(float, sample["y"]),
        cast(float, sample["heading"]),
    )
    dx, dy = D054_STATION[0] - pose[0], D054_STATION[1] - pose[1]
    bearing = math.atan2(dy, dx)
    beta = math.atan2(math.sin(bearing - pose[2]), math.cos(bearing - pose[2]))
    command = cast(list[float], sample["wheel_command"])
    start_return = next(
        cast(int, row["transition"])
        for row in trace
        if "RETURN_ACTIVATED" in cast(list[str], row.get("events", []))
    )
    drops: list[float] = []
    for transition in range(onset, max(rows) + 1):
        current = rows[transition]
        prior = rows[transition - 1]
        battery_drop = cast(float, prior["battery_after_j"]) - cast(
            float, current["battery_after_j"]
        )
        drops.append(abs(battery_drop - D045_ELECTRONICS_POWER_W * D045_DT_SECONDS))
    return {
        "identity_control": "PASS",
        "absorbing_onset_found": True,
        "h1_supported_for_seed": True,
        "absorbing_onset_transition": onset,
        "transitions_after_return_activated": onset - start_return,
        "return_activated_transition": start_return,
        "position": [pose[0], pose[1]],
        "heading": pose[2],
        "wall_or_corner": _wall_label((pose[0], pose[1])),
        "command": command,
        "beta_eval_rad": beta,
        "outward_normal_component": _outward_component((pose[0], pose[1]), pose[2]),
        "max_abs_battery_drop_deviation_from_electronics_j": max(drops, default=0.0),
        "transition_count_from_onset_to_end": len(drops),
        "pre_onset_pose": [previous["x"], previous["y"], previous["heading"]],
    }


def _part_b_restore(trace: tuple[dict[str, object], ...]) -> D054Restore:
    activated = next(
        cast(int, row["transition"])
        for row in trace
        if "RETURN_ACTIVATED" in cast(list[str], row.get("events", []))
    )
    row = next(item for item in trace if cast(int, item["transition"]) == activated - 1)
    temperature = cast(float, row["thermal"]) * 80.0
    return {
        "transition": activated - 1,
        "position": (cast(float, row["x"]), cast(float, row["y"])),
        "heading": cast(float, row["heading"]),
        "battery_j": cast(float, row["battery_after_j"]),
        "temperature_c_approximate": temperature,
    }


def _part_b_run(
    restore: D054Restore,
    controller: object,
    *,
    fidelity_end: int | None,
    official: tuple[dict[str, object], ...] | None,
    official_start: int | None,
    horizon: int,
) -> dict[str, object]:
    position = restore["position"]
    heading, battery = restore["heading"], restore["battery_j"]
    env, observation = _reset_env(
        position,
        heading,
        battery,
        restore["temperature_c_approximate"],
        horizon,
    )
    spins = transitions = 0
    outcome = "HORIZON_CENSORED"
    fidelity_matches = True
    while transitions < horizon:
        wrapped = wrapped_decision(controller, observation, spins)
        if wrapped.mode is D050ControlMode.CONTACT:
            outcome = "DOCKED"
            break
        if wrapped.exhausted:
            outcome = "TERMINAL_SPIN_EXHAUSTED"
            break
        observation, reward, terminated, truncated, info = env.step(wrapped.wheels)
        if reward != 0.0 or info != {}:
            raise RuntimeError("D-045 reward/info contract changed")
        telemetry = env.last_transition
        if telemetry is None:
            raise RuntimeError("D-045 telemetry missing")
        transitions += 1
        spins = wrapped.count_after
        if official is not None:
            expected = next(
                (
                    x
                    for x in official
                    if cast(int, x["transition"])
                    == cast(int, official_start) + transitions - 1
                ),
                None,
            )
            if expected is None:
                fidelity_matches = False
            else:
                fidelity_matches = fidelity_matches and all(
                    cast(float, expected[key]).hex() == float(actual).hex()
                    for key, actual in (
                        ("x", telemetry.position_after[0]),
                        ("y", telemetry.position_after[1]),
                        ("heading", telemetry.heading_after),
                    )
                )
        if fidelity_end is None and is_absorbing_step(
            command=wrapped.wheels,
            boundary_scale=telemetry.boundary_scale,
            before=(*telemetry.position_before, telemetry.heading_before),
            after=(*telemetry.position_after, telemetry.heading_after),
        ):
            outcome = "ABSORBING_ZERO_MOTION"
            break
        if wrapped.mode is D050ControlMode.INVALID_BEACON:
            outcome = "INVALID_BEACON"
            break
        if terminated:
            reason = (
                telemetry.termination_reason.value
                if telemetry.termination_reason
                else "UNKNOWN"
            )
            outcome = f"TERMINATED_{reason}"
            break
        if truncated:
            outcome = "HORIZON_CENSORED"
            break
        if (
            fidelity_end is not None
            and transitions + restore["transition"] >= fidelity_end
        ):
            break
    env.close()
    return {
        "outcome": outcome,
        "outcome_transition": transitions,
        "fidelity_matches_bitwise": fidelity_matches if official is not None else None,
        "executed_transitions": transitions,
    }


def _run_matrix_case(case: D054Case, arm: str) -> dict[str, object]:
    controller: object = (
        D050SmoothController() if arm == "S" else D050BaselineController()
    )
    return _run_classified(
        case.case_id,
        case.position,
        case.heading,
        0.20 * D045_BATTERY_CAPACITY_J,
        D045_AMBIENT_TEMPERATURE_C,
        controller,
        case.inset,
        case.boundary_class,
    )


def _aggregates(records: list[dict[str, object]]) -> dict[str, object]:
    by_arm: dict[str, Counter[str]] = {"S": Counter(), "B": Counter()}
    by_group: dict[str, Counter[str]] = {}
    paired: dict[tuple[str, str], int] = Counter()
    lookup: dict[tuple[str, str], str] = {}
    for row in records:
        arm = cast(str, row["arm"])
        outcome = cast(str, row["outcome"])
        by_arm[arm][outcome] += 1
        group = f"{arm}|inset={row['inset_m']}|{row['boundary_class']}"
        by_group.setdefault(group, Counter())[outcome] += 1
        lookup[(cast(str, row["case_id"]), arm)] = outcome
    for case in sorted({key[0] for key in lookup}):
        paired[(lookup[(case, "S")], lookup[(case, "B")])] += 1
    smooth_absorbing = [
        cast(dict[str, object], r["diagnostic"])
        for r in records
        if r["arm"] == "S" and r["outcome"] == "ABSORBING_ZERO_MOTION"
    ]
    betas = [abs(cast(float, r["beta_eval_rad"])) for r in smooth_absorbing]
    outward = [cast(float, r["outward_normal_component"]) for r in smooth_absorbing]
    return {
        "outcome_counts_by_arm": {
            arm: dict(sorted(counts.items())) for arm, counts in by_arm.items()
        },
        "outcome_counts_by_arm_inset_boundary_class": {
            k: dict(sorted(v.items())) for k, v in sorted(by_group.items())
        },
        "paired_smooth_by_baseline_outcomes": {
            f"{a} x {b}": n for (a, b), n in sorted(paired.items())
        },
        "smooth_absorbing_beta_eval_abs_range_rad": [min(betas), max(betas)]
        if betas
        else None,
        "smooth_absorbing_outward_component_range": [min(outward), max(outward)]
        if outward
        else None,
        "smooth_absorbing_proprioceptive_stall_visible_count": sum(
            bool(r["proprioceptive_stall_visible"]) for r in smooth_absorbing
        ),
    }


def run_d054_protocol(
    executed_commit_sha: str, committed_artifact: Path | None = None
) -> dict[str, object]:
    """Run official D-054 protocol; only CLI calls this for official support."""
    if len(executed_commit_sha) != 40 or any(
        c not in "0123456789abcdef" for c in executed_commit_sha
    ):
        raise ValueError("executed_commit_sha must be a lowercase 40-character SHA")
    committed_path = (
        committed_artifact
        or Path(__file__).resolve().parents[2]
        / "development/D-053-v05-continuous-lifetime-return-charge-recovery.json"
    )
    committed = json.loads(committed_path.read_text(encoding="utf-8"))
    committed_seed = next(item for item in committed["seeds"] if item["seed"] == 22053)
    lifetime = run_d053_lifetime(22053)
    part_a = _part_a(lifetime, committed_seed)
    trace = lifetime.trace
    onset = cast(int | None, part_a.get("absorbing_onset_transition"))
    restore = _part_b_restore(trace)
    activated = next(
        cast(int, row["transition"])
        for row in trace
        if "RETURN_ACTIVATED" in cast(list[str], row.get("events", []))
    )
    end = onset + 10 if onset is not None else activated + 999
    fidelity_count = end - activated + 1
    fidelity = _part_b_run(
        restore,
        D050SmoothController(),
        fidelity_end=end,
        official=trace,
        official_start=activated,
        horizon=fidelity_count + 1,
    )
    if fidelity["fidelity_matches_bitwise"] is not True:
        raise RuntimeError("D-054 Part B fidelity control failed")
    classified_s = _run_classified(
        "part-b-return-activation",
        restore["position"],
        restore["heading"],
        restore["battery_j"],
        restore["temperature_c_approximate"],
        D050SmoothController(),
        0.0,
        "restored_activation_state",
        D054_HORIZON,
    )
    classified_b = _run_classified(
        "part-b-return-activation",
        restore["position"],
        restore["heading"],
        restore["battery_j"],
        restore["temperature_c_approximate"],
        D050BaselineController(),
        0.0,
        "restored_activation_state",
        D054_HORIZON,
    )
    # Temperature inversion is approximate, and only Part B uses restored energy.
    records: list[dict[str, object]] = []
    cases = frozen_cases()
    if len(cases) != 768:
        raise RuntimeError("frozen D-054 matrix cardinality changed")
    for case in cases:
        for arm in ("S", "B"):
            records.append({"arm": arm, **_run_matrix_case(case, arm)})
    aggregates = _aggregates(records)
    signatures = Counter(
        (cast(str, r["arm"]), cast(str, r["outcome"])) for r in records
    )
    signature_text = json.dumps(
        {f"{a}:{o}": n for (a, o), n in sorted(signatures.items())},
        sort_keys=True,
        separators=(",", ":"),
    )
    return {
        "schema_version": "d054-artifact-v1",
        "development_id": D054_ID,
        "protocol_version": D054_PROTOCOL_VERSION,
        "authorized_base_sha": "968d5917215ba974031f555cfbea0350ddb6d74f",
        "executed_commit_sha": executed_commit_sha,
        "result_kind": "development_evaluator_only_diagnostic",
        "claims_boundary": (
            "descriptive only; not confirmatory evidence; no mechanism change"
        ),
        "execution_status": "COMPLETED",
        "part_a": part_a,
        "part_b": {
            "restored_state": restore,
            "temperature_approximate": True,
            "arm_s_fidelity_replay": fidelity,
            "fidelity_control": "PASS",
            "arm_s_classified": classified_s,
            "arm_b_classified": classified_b,
        },
        "part_c": {
            "state_count": len(cases),
            "per_run": records,
            "aggregates": aggregates,
        },
        "discrete_outcome_signature": hashlib.sha256(
            signature_text.encode()
        ).hexdigest(),
        "protocol": {
            "matrix_positions": 48,
            "headings_per_position": 16,
            "states": 768,
            "arms": ["S", "B"],
            "horizon": D054_HORIZON,
            "insets_m": list(D054_MATRIX_INSETS),
            "headings_rad": list(D054_HEADINGS),
            "wrapper_spin_limit": D049_TERMINAL_SPIN_MAX_STEPS,
            "energy_fraction": 0.20,
            "reward": 0.0,
            "organism_info": {},
        },
    }


def write_d054_artifact(path: Path, executed_commit_sha: str) -> Path:
    artifact = _canonicalize(run_d054_protocol(executed_commit_sha))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(artifact, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--executed-commit-sha", required=True)
    args = parser.parse_args()
    write_d054_artifact(args.output, args.executed_commit_sha)


if __name__ == "__main__":
    main()
