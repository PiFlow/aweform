"""One-use guarded safety-probe plus paired N400/N800 exploratory replay."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import numbers
import os
import resource
import shutil
import signal
import subprocess
import sys
import time
from enum import Enum
from pathlib import Path
from typing import Any, cast

import pymunk

from aweform.d052 import D052Controller
from aweform.d053 import D053RoamingFixture
from aweform.d058 import D058Env, D058PhysicalConfig
from aweform.exp003_seed_policy import validate_exp003_development_seeds
from experiments.pymunk_contact_prototype.fixture import DT
from experiments.pymunk_contact_prototype.organism_lifetime import (
    START_OPTIONS,
    PymunkPhysiologyAdapter,
)

from .audit import clearances_by_object
from .cases import FORWARD, REVERSE, SPIN_CW
from .run_physics import _aggregate_contact_states, _aggregate_event_runs
from .world import ObstacleContactWorld

SEED = 23002
HORIZON = 1_800
RESOLUTIONS = (400, 800)
MAX_SPACE_STEPS = 2_400_000
SAFETY_CASES = (
    ("straight-forward", (1.0, 1.0, 0.0), (FORWARD,)),
    ("straight-reverse", (1.0, 1.0, 0.0), (REVERSE,)),
    ("pure-spin", (1.5, 1.5, 0.0), (SPIN_CW,)),
    ("mixed-wheel-curve", (1.5, 1.5, 0.0), ((FORWARD[0], FORWARD[1] / 2),)),
    ("mixed-wheel-reverse-curve", (1.5, 1.5, 0.0), ((REVERSE[0], REVERSE[1] / 2),)),
    ("west-wall-release", (0.11, 1.5, math.pi), (FORWARD,) * 5 + (REVERSE,) * 5),
    ("A1-oblique-slide", (1.5, 2.24, math.radians(70)), (FORWARD,) * 8),
    ("A2-convex-slide", (2.18, 1.5, 0.0), (FORWARD,) * 4),
    ("P1-push-release", (2.19, 0.60, 0.0), (FORWARD,) * 20 + (REVERSE,) * 9),
)
SAFETY_CALLS = sum(len(case[2]) for case in SAFETY_CASES) * sum(RESOLUTIONS)
PAIR_CALLS = HORIZON * sum(RESOLUTIONS)
PLANNED_CALLS = SAFETY_CALLS + PAIR_CALLS
MAX_WALL_SECONDS = 3_600
MAX_CPU_SECONDS = 3_600
MAX_RSS_BYTES = 512 * 1024 * 1024
MAX_OUTPUT_BYTES = 32 * 1024 * 1024
MIN_FREE_DISK_BYTES = 128 * 1024 * 1024
MAX_PENETRATION_M = 0.001
MAX_POSITION_CONVERGENCE_M = 0.0005
MAX_HEADING_CONVERGENCE_RAD = 0.001
MAX_CLEARANCE_CONVERGENCE_M = 0.0005
MAX_FREE_SPACE_POSITION_ERROR_M = 0.00001
MAX_FREE_SPACE_HEADING_ERROR_RAD = 0.00001
EXECUTABLE_PATHS = (
    "experiments/pymunk_contact_prototype/fixture.py",
    "experiments/pymunk_contact_prototype/fixture_v4.py",
    "experiments/pymunk_contact_prototype/motor.py",
    "experiments/pymunk_contact_prototype/organism_lifetime.py",
    "experiments/pymunk230_obstacles/world.py",
    "experiments/pymunk230_obstacles/geometry.py",
    "experiments/pymunk230_obstacles/audit.py",
    "experiments/pymunk230_obstacles/cases.py",
    "experiments/pymunk230_obstacles/run_exploratory_pair.py",
    "experiments/pymunk230_obstacles/test_motor_schedule.py",
    "experiments/pymunk230_obstacles/test_paired_replay.py",
    "experiments/pymunk230_obstacles/render_paired_replay.py",
    "experiments/pymunk230_obstacles/attempt-4-manifest.json",
    "experiments/pymunk230_obstacles/exploratory-run-declaration.json",
    "src/aweform/d045.py",
    "src/aweform/exp001.py",
    "src/aweform/exp001_seed_policy.py",
    "src/aweform/exp002_protocol.py",
    "src/aweform/exp003_seed_policy.py",
    "src/aweform/d052.py",
    "src/aweform/d053.py",
    "src/aweform/d058.py",
)
WHEEL_PATH = Path(
    "/tmp/a230-pymunk-wheel/pymunk-7.2.0-cp314-cp314-macosx_11_0_arm64.whl"
)
EXPECTED_WHEEL_SHA256 = (
    "497c4a919fc7f03882cb9796b132ab3b5fcc4c4af9ead08e9631b6a9fb2da29c"
)
PRIVATE_ROOT = Path(
    "/Users/flow/Dev/firstmate-homes/aweform/data/a230-attempt4-motor-implementation"
)
DEFAULT_OUTPUT = PRIVATE_ROOT / "exploratory-run-1"
LEDGER = PRIVATE_ROOT / "exploratory-run-1.started.json"


class GuardStop(RuntimeError):
    pass


def canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _source_digests(root: Path) -> dict[str, str]:
    return {
        relative: sha((root / relative).read_bytes()) for relative in EXECUTABLE_PATHS
    }


def _install_cpu_limit() -> tuple[int, int]:
    soft, hard = resource.getrlimit(resource.RLIMIT_CPU)
    infinity = resource.RLIM_INFINITY
    target_soft = MAX_CPU_SECONDS if soft == infinity else min(MAX_CPU_SECONDS, soft)
    target_hard = (
        MAX_CPU_SECONDS + 1 if hard == infinity else min(MAX_CPU_SECONDS + 1, hard)
    )
    target_soft = min(target_soft, target_hard)
    resource.setrlimit(resource.RLIMIT_CPU, (target_soft, target_hard))
    signal.signal(
        signal.SIGXCPU,
        lambda *_: (_ for _ in ()).throw(
            GuardStop("process-CPU resource limit reached")
        ),
    )
    return target_soft, target_hard


def _rss_bytes() -> int:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(peak if sys.platform == "darwin" else peak * 1024)


def _tree_bytes(path: Path) -> int:
    return (
        sum(p.stat().st_size for p in path.rglob("*") if p.is_file())
        if path.exists()
        else 0
    )


def _resource_guard(start_wall: float, start_cpu: float, output: Path) -> None:
    if shutil.disk_usage(PRIVATE_ROOT).free < MIN_FREE_DISK_BYTES:
        raise GuardStop("128 MiB private-volume free-space reserve crossed")
    if time.monotonic() - start_wall > MAX_WALL_SECONDS:
        raise GuardStop("wall-clock cap exceeded")
    if time.process_time() - start_cpu > MAX_CPU_SECONDS:
        raise GuardStop("process-CPU cap exceeded")
    if _rss_bytes() > MAX_RSS_BYTES:
        raise GuardStop("RSS cap exceeded")
    if _tree_bytes(output) > MAX_OUTPUT_BYTES:
        raise GuardStop("private output cap exceeded")


def _wheel_provenance() -> dict[str, object]:
    data = WHEEL_PATH.read_bytes()
    digest = sha(data)
    if digest != EXPECTED_WHEEL_SHA256:
        raise RuntimeError(f"pinned legal wheel SHA-256 mismatch: {digest}")
    if sys.version.split()[0] != "3.14.7" or pymunk.version != "7.2.0":
        raise RuntimeError("Python/Pymunk runtime differs from approved pinned stack")
    return {
        "path": str(WHEEL_PATH),
        "bytes": len(data),
        "sha256": digest,
        "python": sys.version.split()[0],
        "pymunk": pymunk.version,
    }


def _command_row(record: Any) -> dict[str, object]:
    return {
        "start_m": list(record.start),
        "start_heading_rad": record.start_angle,
        "end_m": list(record.end),
        "end_heading_rad": record.end_angle,
        "velocity_m_s": list(record.velocity),
        "angular_velocity_rad_s": record.angular_velocity,
        "shaft_rad": list(record.shaft),
        "contact_seen": record.contact_seen,
        "contact_events": [
            {
                "substep": event.substep_index,
                "shapes": list(event.shape_pair),
                "points": event.contact_points,
                "impulse": event.impulse,
                "penetration_m": event.maximum_contact_penetration,
            }
            for event in record.contact_events
        ],
        "simultaneous_contact_ids": [
            list(ids) for ids in record.simultaneous_contact_identities
        ],
        "minimum_clearance_by_shape_m": dict(record.minimum_clearance_by_shape),
        "minimum_clearance_m": record.minimum_clearance_m,
        "penetration_upper_bound_m": record.max_penetration,
        "crossed": record.crossed_wall_or_post,
        "sampling_bound_m": record.clearance_sampling_bound_m,
        "engine_steps": record.step_count,
    }


def _guard_callback(start_wall: float, start_cpu: float, output: Path) -> Any:
    checks = 0

    def guard() -> None:
        nonlocal checks
        checks += 1
        if checks % 100 == 0:
            _resource_guard(start_wall, start_cpu, output)

    return guard


def _run_safety_cases(
    start_wall: float, start_cpu: float, output: Path
) -> tuple[list[dict[str, Any]], bool, int]:
    outputs: list[dict[str, Any]] = []
    progress_path = output / "safety-progress.jsonl"
    progress_path.touch(exist_ok=False)
    by_case_resolution: dict[tuple[str, int], list[dict[str, object]]] = {}
    calls = 0
    safe = True
    expected_ids = {
        "west-wall-release": "wall_west",
        "A1-oblique-slide": "A1",
        "A2-convex-slide": "A2",
        "P1-push-release": "P1",
    }
    for name, start, commands in SAFETY_CASES:
        for resolution in RESOLUTIONS:
            world = ObstacleContactWorld(microsteps=resolution)
            world.reset((start[0], start[1]), start[2])
            world.execution_guard = _guard_callback(start_wall, start_cpu, output)
            rows: list[dict[str, object]] = []
            for action in commands:
                _resource_guard(start_wall, start_cpu, DEFAULT_OUTPUT)
                steps_before = world.engine_steps
                record = world.advance(action)
                actual_steps = world.engine_steps - steps_before
                if actual_steps != resolution:
                    raise GuardStop(
                        "safety adapter executed unexpected Space.step count"
                    )
                calls += actual_steps
                row = _command_row(record)
                row["action_rad"] = list(action)
                if name in {
                    "straight-forward",
                    "straight-reverse",
                    "pure-spin",
                    "mixed-wheel-curve",
                    "mixed-wheel-reverse-curve",
                }:
                    left, right = record.shaft
                    distance = 0.045 * (left + right) / 2.0
                    yaw = 0.045 * (right - left) / 0.185
                    speed, omega = distance / DT, yaw / DT
                    if omega == 0.0:
                        expected = (
                            start[0] + distance * math.cos(start[2]),
                            start[1] + distance * math.sin(start[2]),
                        )
                    else:
                        arc_distance = speed * math.sin(yaw) / omega
                        side_distance = speed * (1.0 - math.cos(yaw)) / omega
                        expected = (
                            start[0]
                            + arc_distance * math.cos(start[2])
                            - side_distance * math.sin(start[2]),
                            start[1]
                            + arc_distance * math.sin(start[2])
                            + side_distance * math.cos(start[2]),
                        )
                    arc_error = math.dist(record.end, expected)
                    heading_error = abs(record.end_angle - (start[2] + yaw))
                    row["free_space_position_error_m"] = arc_error
                    row["free_space_heading_error_rad"] = heading_error
                    if (
                        arc_error > MAX_FREE_SPACE_POSITION_ERROR_M
                        or heading_error > MAX_FREE_SPACE_HEADING_ERROR_RAD
                    ):
                        safe = False
                rows.append(row)
                _append_json_line(
                    progress_path,
                    {
                        "case": name,
                        "resolution": resolution,
                        "command": len(rows),
                        "row": row,
                    },
                )
                finite_fields = (*record.end, record.end_angle, record.max_penetration)
                if (
                    not all(math.isfinite(float(x)) for x in finite_fields)
                    or record.max_penetration > MAX_PENETRATION_M
                    or record.clearance_sampling_bound_m > 0.0002
                    or world.last_audit.maximum_substep_path_bound_m > 0.0002
                    or record.crossed_wall_or_post
                ):
                    safe = False
            if name in expected_ids:
                observed = {
                    label
                    for row in rows
                    for event in cast(list[dict[str, object]], row["contact_events"])
                    for label in cast(list[str], event["shapes"])
                    if label == expected_ids[name]
                    or label.startswith(expected_ids[name] + "_")
                }
                if not observed:
                    safe = False
            if name in {"west-wall-release", "P1-push-release"}:
                reverse_start = 5 if name == "west-wall-release" else 20
                object_id = expected_ids[name]
                initial_row = rows[reverse_start - 1]
                final_row = rows[-1]
                start_clearance = clearances_by_object(
                    cast(tuple[float, float], tuple(initial_row["end_m"])),
                    float(initial_row["end_heading_rad"]),
                )[object_id]
                final_clearance = clearances_by_object(
                    cast(tuple[float, float], tuple(final_row["end_m"])),
                    float(final_row["end_heading_rad"]),
                )[object_id]
                delta = final_clearance - start_clearance
                rows[-1]["release_clearance_delta_m"] = delta
                if delta < 0.01:
                    safe = False
            by_case_resolution[(name, resolution)] = rows
            case_record = {"case": name, "resolution": resolution, "commands": rows}
            outputs.append(case_record)
            _write_json(output / f"probe-{name}-N{resolution}.json", case_record)
    for name, _, _ in SAFETY_CASES:
        left = by_case_resolution[(name, 400)]
        right = by_case_resolution[(name, 800)]
        for a, b in zip(left, right, strict=True):
            position_gap = math.dist(
                cast(list[float], a["end_m"]), cast(list[float], b["end_m"])
            )
            heading_gap = abs(float(a["end_heading_rad"]) - float(b["end_heading_rad"]))
            ca = cast(dict[str, float], a["minimum_clearance_by_shape_m"])
            cb = cast(dict[str, float], b["minimum_clearance_by_shape_m"])
            clearance_gap = max((abs(ca[key] - cb[key]) for key in ca), default=0.0)
            if (
                position_gap > MAX_POSITION_CONVERGENCE_M
                or heading_gap > MAX_HEADING_CONVERGENCE_RAD
                or clearance_gap > MAX_CLEARANCE_CONVERGENCE_M
            ):
                safe = False
    return outputs, safe, calls


def _initialize_arm(resolution: int, guard: Any) -> PymunkPhysiologyAdapter:
    adapter = PymunkPhysiologyAdapter(microsteps=resolution, seed=SEED)
    adapter.world = ObstacleContactWorld(microsteps=resolution)
    adapter.world.execution_guard = guard
    adapter.proposals = D053RoamingFixture(SEED)
    adapter.reset()
    return adapter


def _json_state(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _json_state(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_state(item) for item in value]
    if hasattr(value, "__dict__"):
        return {
            "type": f"{type(value).__module__}.{type(value).__qualname__}",
            "state": _json_state(vars(value)),
        }
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, numbers.Integral):
        return int(value)
    if isinstance(value, numbers.Real):
        return float(value)
    raise TypeError(f"unsupported initial causal-state value: {type(value).__name__}")


def _causal_state_snapshot(
    seed: int,
    organism_rng: Any,
    environment_rng: Any,
    controller: D052Controller,
    observation: Any,
    physiology: Any,
) -> dict[str, Any]:
    body = physiology.body
    if body is None or physiology.body_temperature_c is None:
        raise RuntimeError("paired physiological initial state is absent")
    return {
        "seed": seed,
        "organism_rng": _json_state(organism_rng),
        "environment_rng": _json_state(environment_rng),
        "controller_state": _json_state(vars(controller)),
        "observation": observation.tolist(),
        "position_m": [body.x, body.y],
        "heading_rad": body.heading,
        "station_m": list(physiology.station_center),
        "battery_j": physiology.battery_j,
        "temperature_c": physiology.body_temperature_c,
        "charger_latched": physiology.charger_termination_latched,
    }


def _prospective_initial_state() -> dict[str, Any]:
    physiology = D058Env(D058PhysicalConfig(room_side_m=3.0))
    observation, info = physiology.reset(seed=SEED, options=START_OPTIONS)
    if info != {} or observation.shape != (8,):
        raise RuntimeError("preflight D-058 initial-state contract changed")
    proposal = D053RoamingFixture(SEED)
    return _causal_state_snapshot(
        SEED,
        proposal._explorer.policy_rng.bit_generator.state,
        physiology.np_random.bit_generator.state,
        D052Controller(),
        observation,
        physiology,
    )


def _arm_start_signature(adapter: PymunkPhysiologyAdapter) -> str:
    snapshot = _causal_state_snapshot(
        adapter.seed,
        adapter.proposals._explorer.policy_rng.bit_generator.state,
        adapter.physiology.np_random.bit_generator.state,
        adapter.controller,
        adapter.observation,
        adapter.physiology,
    )
    return sha(canonical(snapshot))


def _paired_playback(
    start_wall: float,
    start_cpu: float,
    output: Path,
    prospective_state: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    arms: dict[str, dict[str, Any]] = {}
    adapters = {
        str(n): _initialize_arm(n, _guard_callback(start_wall, start_cpu, output))
        for n in RESOLUTIONS
    }
    signatures = {
        key: _arm_start_signature(adapter) for key, adapter in adapters.items()
    }
    expected_signature = sha(canonical(prospective_state))
    if (
        len(set(signatures.values())) != 1
        or next(iter(signatures.values())) != expected_signature
    ):
        raise RuntimeError(
            "paired starts differ from each other or frozen preflight state"
        )
    if tuple(adapters["400"].world.body.position) != tuple(
        adapters["800"].world.body.position
    ):
        raise RuntimeError("paired start positions differ")
    active = {key: True for key in adapters}
    counts = {key: 0 for key in adapters}
    last_rows: dict[str, dict[str, object]] = {}
    arm_paths = {key: output / f"arm-N{key}.jsonl" for key in adapters}
    for path in arm_paths.values():
        path.touch(exist_ok=False)
    calls = 0
    for index in range(1, HORIZON + 1):
        _resource_guard(start_wall, start_cpu, output)
        for key in ("400", "800"):
            if not active[key]:
                continue
            world = adapters[key].world
            steps_before = world.engine_steps
            row = adapters[key].step()
            actual_steps = world.engine_steps - steps_before
            if actual_steps != int(key):
                raise GuardStop("paired adapter executed unexpected Space.step count")
            if row["reward"] != 0.0 or row["info"] != {}:
                raise RuntimeError("organism reward/info contract changed")
            if (
                row["max_penetration_m"] > MAX_PENETRATION_M
                or row["clearance_sampling_bound_m"] > 0.0002
                or adapters[key].world.last_audit.maximum_substep_path_bound_m > 0.0002
                or row["crossed_wall_or_post"]
            ):
                raise GuardStop(
                    f"paired arm N{key} failed contact safety at transition {index}"
                )
            raw_events = cast(list[dict[str, Any]], row.pop("contact_events"))
            event_runs = _aggregate_event_runs(
                [
                    {
                        "substep": event["substep_index"],
                        "shape_pair": event["shape_pair"],
                        "contact_points": event["contact_points"],
                        "impulse": event["impulse"],
                        "penetration_m": event["maximum_contact_penetration_m"],
                    }
                    for event in raw_events
                ]
            )
            states = cast(list[list[str]], row.pop("simultaneous_contact_identities"))
            row["contact_event_runs"] = event_runs
            row["contact_state_runs"] = _aggregate_contact_states(
                tuple(tuple(x) for x in states)
            )
            row["index"] = index
            row["commanded_wheels_rad"] = row.get("commanded_wheels_rad")
            row["raw_callback_count"] = len(raw_events)
            row["position_m"] = list(world.body.position)
            row["heading_rad"] = float(world.body.angle)
            row["observation"] = row["observation"]
            _append_json_line(arm_paths[key], row)
            counts[key] += 1
            last_rows[key] = row
            calls += actual_steps
            if row["terminated"]:
                active[key] = False
        # Same logical horizon for the pair; if either terminates, no arm is
        # driven farther than the common observed support.
        if not all(active.values()):
            break
        if index % 25 == 0:
            _resource_guard(start_wall, start_cpu, output)
    arms = {
        key: {
            "resolution": int(key),
            "transitions": counts[key],
            "termination": (
                last_rows[key]["termination_reason"]
                if last_rows.get(key, {}).get("terminated")
                else "administrative_horizon_or_paired_stop"
            ),
            "final_position_m": last_rows.get(key, {}).get("position_m"),
            "final_heading_rad": last_rows.get(key, {}).get("heading_rad"),
            "final_energy_j": last_rows.get(key, {}).get("energy_j"),
            "final_temperature_c": last_rows.get(key, {}).get("temperature_c"),
            "trace_file": arm_paths[key].name,
            "trace_sha256": sha(arm_paths[key].read_bytes()),
        }
        for key in adapters
    }
    return {
        "seed": SEED,
        "horizon_cap": HORIZON,
        "initial_state": START_OPTIONS,
        "initial_rng_observation_signature": signatures,
        "arms": arms,
    }, calls


def _paired_convergence_summary(output: Path) -> dict[str, object]:
    arms = {
        key: [
            json.loads(line)
            for line in (output / f"arm-N{key}.jsonl").read_text().splitlines()
            if line
        ]
        for key in ("400", "800")
    }
    if len(arms["400"]) != len(arms["800"]):
        raise GuardStop("paired arms have unequal recorded transition support")
    max_position = 0.0
    max_heading = 0.0
    max_clearance = 0.0
    action_divergence: int | None = None
    contact_disagreements = 0
    for left, right in zip(arms["400"], arms["800"], strict=True):
        max_position = max(
            max_position, math.dist(left["position_m"], right["position_m"])
        )
        heading_gap = math.atan2(
            math.sin(right["heading_rad"] - left["heading_rad"]),
            math.cos(right["heading_rad"] - left["heading_rad"]),
        )
        max_heading = max(max_heading, abs(heading_gap))
        max_clearance = max(
            max_clearance,
            abs(left["minimum_clearance_m"] - right["minimum_clearance_m"]),
        )
        if (
            action_divergence is None
            and left["commanded_wheels_rad"] != right["commanded_wheels_rad"]
        ):
            action_divergence = int(left["index"])
        left_ids = {tuple(run["shape_pair"]) for run in left["contact_event_runs"]}
        right_ids = {tuple(run["shape_pair"]) for run in right["contact_event_runs"]}
        contact_disagreements += left_ids != right_ids
    return {
        "interpretation": (
            "descriptive convergence/difference only; not a safety or acceptance gate"
        ),
        "common_transitions": len(arms["400"]),
        "maximum_position_difference_m": max_position,
        "maximum_wrapped_heading_difference_rad": max_heading,
        "maximum_minimum_clearance_difference_m": max_clearance,
        "transitions_with_contact_identity_set_disagreement": contact_disagreements,
        "first_command_divergence_transition": action_divergence,
    }


def _write_json(path: Path, value: object) -> None:
    encoded = canonical(value) + b"\n"
    if path.parent == DEFAULT_OUTPUT:
        current = _tree_bytes(DEFAULT_OUTPUT)
        existing = path.stat().st_size if path.exists() else 0
        if current - existing + len(encoded) > MAX_OUTPUT_BYTES:
            raise GuardStop("private output cap would be exceeded")
    path.write_bytes(encoded)


def _append_json_line(path: Path, value: object) -> None:
    encoded = canonical(value) + b"\n"
    if _tree_bytes(DEFAULT_OUTPUT) + len(encoded) > MAX_OUTPUT_BYTES:
        raise GuardStop("private output cap would be exceeded")
    with path.open("ab") as stream:
        stream.write(encoded)
        stream.flush()


def run(output: Path) -> None:
    if output != DEFAULT_OUTPUT or output.exists() or LEDGER.exists():
        raise RuntimeError(
            "one-use private output/ledger already exists or path differs"
        )
    if (
        Path(__file__).resolve().parents[2]
        / "experiments/pymunk230_obstacles/results/attempt-4"
    ).exists():
        raise RuntimeError(
            "formal attempt-4 output exists; refusing shared attempt namespace"
        )
    root = Path(__file__).resolve().parents[2]
    branch = subprocess.check_output(
        ["git", "-C", str(root), "branch", "--show-current"], text=True
    ).strip()
    head = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()
    tree_sha = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD^{tree}"], text=True
    ).strip()
    dirty = subprocess.check_output(
        ["git", "-C", str(root), "status", "--porcelain"], text=True
    ).strip()
    if branch != "fm/a230-attempt4-review-candidate" or dirty:
        raise RuntimeError("run requires the clean committed public review vehicle")
    validate_exp003_development_seeds([SEED])
    wheel = _wheel_provenance()
    output.mkdir(parents=True)
    start_wall, start_cpu = time.monotonic(), time.process_time()
    declaration = {
        "schema": "a230-exploratory-pair-v1",
        "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "machine": subprocess.check_output(["uname", "-a"], text=True).strip(),
        "pid": os.getpid(),
        "seed": SEED,
        "horizon_cap_per_arm": HORIZON,
        "resolutions": list(RESOLUTIONS),
        "dt_s": DT,
        "safety_case_commands_per_resolution": sum(
            len(case[2]) for case in SAFETY_CASES
        ),
        "safety_space_steps": SAFETY_CALLS,
        "paired_space_steps_cap": PAIR_CALLS,
        "total_planned_space_steps": PLANNED_CALLS,
        "absolute_space_step_cap": MAX_SPACE_STEPS,
        "wall_seconds": MAX_WALL_SECONDS,
        "process_cpu_seconds": MAX_CPU_SECONDS,
        "rss_bytes": MAX_RSS_BYTES,
        "private_output_bytes": MAX_OUTPUT_BYTES,
        "minimum_free_disk_bytes": MIN_FREE_DISK_BYTES,
        "wheel": wheel,
        "source_head": head,
        "source_tree_sha": tree_sha,
        "executable_file_sha256": _source_digests(root),
        "protocol_sha256": sha(
            (root / "experiments/pymunk230_obstacles/protocol.md").read_bytes()
        ),
        "initial_state": START_OPTIONS,
        "exact_initial_causal_state": _prospective_initial_state(),
        "motor_law": (
            "command-boundary velocity/yaw plus held centripetal force F=m*omega*J(v)"
        ),
    }
    if PLANNED_CALLS > MAX_SPACE_STEPS:
        raise RuntimeError("planned engine calls exceed hard total cap")
    cpu_limit = _install_cpu_limit()
    declaration["effective_process_cpu_rlimit_seconds"] = list(cpu_limit)
    fd = os.open(LEDGER, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(
            canonical({"state": "started", "declaration": declaration}) + b"\n"
        )
        stream.flush()
        os.fsync(stream.fileno())
    signal.signal(
        signal.SIGALRM, lambda *_: (_ for _ in ()).throw(GuardStop("wall cap elapsed"))
    )
    signal.setitimer(signal.ITIMER_REAL, MAX_WALL_SECONDS)
    try:
        probe_rows, safety_pass, safety_calls = _run_safety_cases(
            start_wall, start_cpu, output
        )
        _write_json(
            output / "safety-probes.json",
            {"pass": safety_pass, "space_steps": safety_calls, "cases": probe_rows},
        )
        _resource_guard(start_wall, start_cpu, output)
        if not safety_pass:
            raise GuardStop(
                "one or more physical safety probes failed; paired playback withheld"
            )
        paired, paired_calls = _paired_playback(
            start_wall,
            start_cpu,
            output,
            cast(dict[str, Any], declaration["exact_initial_causal_state"]),
        )
        total_calls = safety_calls + paired_calls
        if total_calls > MAX_SPACE_STEPS:
            raise GuardStop("actual Space.step count exceeds hard cap")
        result = {
            "declaration": declaration,
            "head": head,
            "safety_pass": safety_pass,
            "safety_space_steps": safety_calls,
            "paired_space_steps": paired_calls,
            "total_space_steps": total_calls,
            "elapsed_wall_s": time.monotonic() - start_wall,
            "elapsed_process_cpu_s": time.process_time() - start_cpu,
            "peak_rss_bytes": _rss_bytes(),
            "paired": paired,
            "paired_convergence": _paired_convergence_summary(output),
        }
        _write_json(output / "result.json", result)
        sums = []
        for path in sorted(output.iterdir()):
            if path.is_file():
                sums.append(f"{sha(path.read_bytes())}  {path.name}")
        sums_data = ("\n".join(sums) + "\n").encode("utf-8")
        if _tree_bytes(output) + len(sums_data) > MAX_OUTPUT_BYTES:
            raise GuardStop("private output cap would be exceeded by checksum ledger")
        (output / "SHA256SUMS").write_bytes(sums_data)
        _write_json(
            LEDGER,
            {
                "state": "complete",
                "result_sha256": sha((output / "result.json").read_bytes()),
                "total_space_steps": total_calls,
            },
        )
    except BaseException as exc:
        _write_json(
            output / "failure.json",
            {
                "error": type(exc).__name__,
                "message": str(exc),
                "elapsed_wall_s": time.monotonic() - start_wall,
                "elapsed_cpu_s": time.process_time() - start_cpu,
                "peak_rss_bytes": _rss_bytes(),
            },
        )
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if args.preflight:
        root = Path(__file__).resolve().parents[2]
        branch = subprocess.check_output(
            ["git", "-C", str(root), "branch", "--show-current"], text=True
        ).strip()
        dirty = subprocess.check_output(
            ["git", "-C", str(root), "status", "--porcelain"], text=True
        ).strip()
        if branch != "fm/a230-attempt4-review-candidate" or dirty:
            raise RuntimeError("preflight requires the clean committed review vehicle")
        validate_exp003_development_seeds([SEED])
        initial_state = _prospective_initial_state()
        wheel = _wheel_provenance()
        if DEFAULT_OUTPUT.exists() or LEDGER.exists():
            raise RuntimeError("one-use output or execution ledger already exists")
        if shutil.disk_usage(PRIVATE_ROOT).free < MIN_FREE_DISK_BYTES:
            raise RuntimeError("less than 128 MiB free on the private evidence volume")
        if PLANNED_CALLS > MAX_SPACE_STEPS:
            raise RuntimeError("planned engine calls exceed hard total cap")
        print(
            json.dumps(
                {
                    "seed": SEED,
                    "initial_causal_state_sha256": sha(canonical(initial_state)),
                    "safety_space_steps": SAFETY_CALLS,
                    "paired_space_steps_cap": PAIR_CALLS,
                    "planned_space_steps": PLANNED_CALLS,
                    "hard_space_step_cap": MAX_SPACE_STEPS,
                    "wheel": wheel,
                    "source_file_hashes": _source_digests(root),
                    "protocol_sha256": sha(
                        (
                            root / "experiments/pymunk230_obstacles/protocol.md"
                        ).read_bytes()
                    ),
                    "output_does_not_exist": not DEFAULT_OUTPUT.exists(),
                    "one_use_ledger_does_not_exist": not LEDGER.exists(),
                },
                sort_keys=True,
            )
        )
        return
    run(DEFAULT_OUTPUT)


if __name__ == "__main__":
    main()
