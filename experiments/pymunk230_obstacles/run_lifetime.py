"""One-shot, physics-gated 2,000-transition Level-1 obstacle lifetime.

This module only defines the future measurement. Importing it never steps the
organism or constructs a physics Space.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import resource
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, cast

import pymunk

from aweform.d053 import D053RoamingFixture  # type: ignore[import-untyped]
from experiments.pymunk_contact_prototype.organism_lifetime import (
    START_OPTIONS,
    PymunkPhysiologyAdapter,
)

from .run_physics import (
    _aggregate_contact_states,
    _aggregate_event_runs,
    _physics_protocol_sha256,
    _physics_source_sha256,
    _source_tree_clean_except_attempt_artifacts,
)
from .world import ObstacleContactWorld

SEED = 23001
HORIZON = 2_000
MICROSTEPS = 400
MAX_WALL_CPU_SECONDS = 600
MAX_RSS_BYTES = 256 * 1024 * 1024
MAX_OUTPUT_BYTES = 10 * 1024 * 1024
MAX_FINALIZATION_RESERVE_BYTES = 64 * 1024
MAX_FRAMES = 2_001
MAX_RAW_CALLBACKS = 1_000_000
MAX_AGGREGATE_ROWS = 4_000
MAX_AGGREGATE_ROW_BYTES = 512
EXPECTED_PYTHON = "3.14.7"
EXPECTED_PYMUNK = "7.2.0"
DEFAULT_PHYSICS_PASS = Path(
    "experiments/pymunk230_obstacles/results/attempt-1/results.json"
)
DEFAULT_OUTPUT = Path("experiments/pymunk230_obstacles/results/lifetime-1")


class LifetimeBudgetExceeded(RuntimeError):
    """A frozen lifetime resource ceiling was reached."""


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require_physics_pass(path: Path, head: str) -> dict[str, Any]:
    result = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
    source_sha = _physics_source_sha256()
    physics_protocol_sha = _physics_protocol_sha256()
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", str(result.get("head", "")), head],
        check=False,
        capture_output=True,
    )
    if (
        ancestor.returncode != 0
        or result.get("physics_source_sha256") != source_sha
        or result.get("physics_protocol_sha256") != physics_protocol_sha
        or result.get("essential_physics_pass") is not True
        or result.get("replay_identical") is not True
        or result.get("fresh_process_distinct") is not True
    ):
        raise RuntimeError(
            "physics PASS is absent or its frozen physics source/protocol changed"
        )
    return result


def _check_budget(start: float, output: Path) -> None:
    if time.monotonic() - start >= MAX_WALL_CPU_SECONDS:
        raise LifetimeBudgetExceeded("600-second lifetime wall-clock cap reached")
    if time.process_time() >= MAX_WALL_CPU_SECONDS:
        raise LifetimeBudgetExceeded("600-second lifetime process-CPU cap reached")
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_bytes = int(peak if sys.platform == "darwin" else peak * 1024)
    if peak_bytes > MAX_RSS_BYTES:
        raise LifetimeBudgetExceeded("256 MiB lifetime RSS cap reached")
    output_bytes = sum(p.stat().st_size for p in output.glob("*") if p.is_file())
    if output_bytes > MAX_OUTPUT_BYTES:
        raise LifetimeBudgetExceeded("10 MiB lifetime output cap reached")


def run(output: Path, physics_pass: Path) -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    branch = subprocess.check_output(
        ["git", "branch", "--show-current"], text=True
    ).strip()
    if (
        branch != "fm/pymunk230-seven-obstacle"
        or not _source_tree_clean_except_attempt_artifacts()
    ):
        raise RuntimeError(
            "lifetime requires committed source and only frozen attempt artifacts"
        )
    protocol_path = Path(__file__).with_name("protocol.md")
    protocol_sha = _sha(protocol_path.read_bytes())
    physics_pass_result = _require_physics_pass(physics_pass, head)
    if (
        physics_pass.name != "results.json"
        or not physics_pass.parent.name.startswith("attempt-")
        or physics_pass.parent.name
        != f"attempt-{int(physics_pass.parent.name.removeprefix('attempt-'))}"
    ):
        raise RuntimeError(
            "physics PASS must come from a canonical attempt-N results.json"
        )
    if sys.version.split()[0] != EXPECTED_PYTHON or pymunk.version != EXPECTED_PYMUNK:
        raise RuntimeError("runtime differs from the frozen Python/Pymunk identity")
    if output != DEFAULT_OUTPUT:
        raise RuntimeError("the single lifetime output path is frozen")
    if output.exists():
        raise RuntimeError(f"refusing existing one-shot output path: {output}")
    output.mkdir(parents=True)
    start = time.monotonic()
    start_cpu = time.process_time()
    signal.signal(
        signal.SIGALRM,
        lambda *_: (_ for _ in ()).throw(
            LifetimeBudgetExceeded("600-second lifetime wall-clock timeout")
        ),
    )
    signal.setitimer(signal.ITIMER_REAL, MAX_WALL_CPU_SECONDS)
    resource.setrlimit(
        resource.RLIMIT_CPU, (MAX_WALL_CPU_SECONDS, MAX_WALL_CPU_SECONDS)
    )
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_OUTPUT_BYTES, MAX_OUTPUT_BYTES))
    if hasattr(resource, "RLIMIT_RSS"):
        resource.setrlimit(resource.RLIMIT_RSS, (MAX_RSS_BYTES, MAX_RSS_BYTES))

    # Reuse the inherited unchanged physiology/controller adapter, replacing
    # only its pose integrator with this successor's static-object world.
    adapter = PymunkPhysiologyAdapter(microsteps=MICROSTEPS)
    adapter.world = ObstacleContactWorld(microsteps=MICROSTEPS)
    adapter.proposals = D053RoamingFixture(SEED)
    observation, reset_info = adapter.physiology.reset(seed=SEED, options=START_OPTIONS)
    if reset_info != {}:
        raise RuntimeError("D-058 reset info contract changed")
    assert adapter.physiology.body is not None
    adapter.world.body.position = adapter.physiology.body.position
    adapter.world.body.angle = adapter.physiology.body.heading
    adapter.observation = observation
    if observation.shape != (8,) or str(observation.dtype) != "float32":
        raise RuntimeError("initial organism observation contract changed")
    frame_path = output / "frames.jsonl"
    summary_path = output / "transitions.jsonl"
    frame_count = 0
    contact_steps = 0
    event_count = 0
    aggregate_count = 0
    max_penetration = 0.0
    started_record = {
        "schema": "pymunk230-lifetime-v1",
        "head": head,
        "protocol_sha256": protocol_sha,
        "physics_result_sha256": _sha(physics_pass.read_bytes()),
        "physics_head": physics_pass_result["head"],
        "physics_source_sha256": physics_pass_result["physics_source_sha256"],
        "physics_protocol_sha256": physics_pass_result["physics_protocol_sha256"],
        "seed": SEED,
        "horizon": HORIZON,
        "horizon_semantics": (
            "administrative harness stop; not D058 truncation or termination"
        ),
        "microsteps": MICROSTEPS,
        "initial_state": START_OPTIONS,
        "resource_caps": {
            "wall_seconds": MAX_WALL_CPU_SECONDS,
            "process_cpu_seconds": MAX_WALL_CPU_SECONDS,
            "rss_bytes": MAX_RSS_BYTES,
            "output_bytes": MAX_OUTPUT_BYTES,
            "frames": MAX_FRAMES,
            "raw_callbacks": MAX_RAW_CALLBACKS,
            "aggregate_rows": MAX_AGGREGATE_ROWS,
            "aggregate_row_bytes": MAX_AGGREGATE_ROW_BYTES,
            "transition_row_bytes": 3 * 1024,
        },
    }
    (output / "manifest.json").write_bytes(_canonical(started_record))
    termination = "harness_horizon"
    with frame_path.open("xb") as frames, summary_path.open("xb") as summaries:
        for index in range(1, HORIZON + 1):
            _check_budget(start, output)
            row: dict[str, Any] = adapter.step()
            if row["reward"] != 0.0 or row["info"] != {}:
                raise RuntimeError("organism reward/info contract violation")
            if not all(
                math.isfinite(float(value))
                for value in (
                    row["energy_j"],
                    row["temperature_c"],
                    row["yaw_rad"],
                    *row["position_m"],
                    row["max_penetration_m"],
                )
            ):
                raise RuntimeError("non-finite lifetime telemetry")
            raw_events = cast(list[dict[str, Any]], row.pop("contact_events"))
            event_rows = [
                {
                    "substep": int(event["substep_index"]),
                    "shape_pair": list(event["shape_pair"]),
                    "contact_points": int(event["contact_points"]),
                    "impulse": float(event["impulse"]),
                    "penetration_m": float(event["maximum_contact_penetration_m"]),
                }
                for event in raw_events
            ]
            event_runs = _aggregate_event_runs(event_rows)
            states = tuple(
                tuple(state)
                for state in cast(
                    list[list[str]], row.pop("simultaneous_contact_identities")
                )
            )
            state_runs = _aggregate_contact_states(states)
            aggregate_rows = len(event_runs) + len(state_runs)
            if any(
                len(_canonical(item)) > MAX_AGGREGATE_ROW_BYTES
                for item in event_runs + state_runs
            ):
                raise LifetimeBudgetExceeded("lifetime aggregate row exceeds 512 bytes")
            row["raw_callback_count"] = len(raw_events)
            row["contact_event_runs"] = event_runs
            row["contact_state_runs"] = state_runs
            row["index"] = index
            encoded = _canonical(row) + b"\n"
            if len(encoded) > 3 * 1024:
                raise LifetimeBudgetExceeded("lifetime transition row exceeds 3 KiB")
            contact_steps += int(bool(raw_events))
            event_count += len(raw_events)
            if event_count > MAX_RAW_CALLBACKS:
                raise LifetimeBudgetExceeded("lifetime raw callback cap reached")
            aggregate_count += aggregate_rows
            if aggregate_count > MAX_AGGREGATE_ROWS:
                raise LifetimeBudgetExceeded("lifetime aggregate-row cap reached")
            max_penetration = max(max_penetration, float(row["max_penetration_m"]))
            # Bounded replay contains sampled actual values only; no interpolation.
            frame_encoded = b""
            sampled = index == 1 or index % 10 == 0 or row["terminated"]
            if sampled:
                if frame_count + 1 > MAX_FRAMES:
                    raise LifetimeBudgetExceeded("2,001-frame replay cap reached")
                frame = {
                    "index": index,
                    "position_m": row["position_m"],
                    "yaw_rad": row["yaw_rad"],
                    "energy_j": row["energy_j"],
                    "temperature_c": row["temperature_c"],
                    "contact_event_runs": event_runs,
                }
                frame_encoded = _canonical(frame) + b"\n"
            current_bytes = sum(
                path.stat().st_size for path in output.iterdir() if path.is_file()
            )
            if (
                current_bytes
                + len(encoded)
                + len(frame_encoded)
                + MAX_FINALIZATION_RESERVE_BYTES
                > MAX_OUTPUT_BYTES
            ):
                raise LifetimeBudgetExceeded("lifetime output reserve/cap reached")
            summaries.write(encoded)
            summaries.flush()
            if sampled:
                frames.write(frame_encoded)
                frames.flush()
                frame_count += 1
            if row["terminated"]:
                termination = str(row["termination_reason"])
                break
            if frame_count > MAX_FRAMES:
                raise LifetimeBudgetExceeded("2,001-frame replay cap reached")
            _check_budget(start, output)
        frames.flush()
        summaries.flush()
        os.fsync(frames.fileno())
        os.fsync(summaries.fileno())
    if frame_count > MAX_FRAMES:
        raise LifetimeBudgetExceeded("2,001-frame replay cap reached")
    _check_budget(start, output)
    frame_bytes = frame_path.read_bytes()
    transition_bytes = summary_path.read_bytes()
    result = {
        **started_record,
        "frames_sha256": _sha(frame_bytes),
        "frames_bytes": len(frame_bytes),
        "transitions_sha256": _sha(transition_bytes),
        "transitions_bytes": len(transition_bytes),
        "transitions": index,
        "actual_engine_steps": index * MICROSTEPS,
        "termination": termination,
        "contact_steps": contact_steps,
        "raw_callback_count": event_count,
        "stored_aggregate_rows": aggregate_count,
        "aggregate_row_cap": MAX_AGGREGATE_ROWS,
        "raw_callback_cap": MAX_RAW_CALLBACKS,
        "max_penetration_m": max_penetration,
        "final_position_m": row["position_m"],
        "final_energy_j": row["energy_j"],
        "final_temperature_c": row["temperature_c"],
        "replay_frame_count": frame_count,
        "elapsed_wall_s": time.monotonic() - start,
        "process_cpu_s": time.process_time() - start_cpu,
    }
    result_bytes = _canonical(result)
    current_bytes = sum(
        path.stat().st_size for path in output.iterdir() if path.is_file()
    )
    if current_bytes + len(result_bytes) + 4096 > MAX_OUTPUT_BYTES:
        raise LifetimeBudgetExceeded("insufficient output reserve for result/checksums")
    (output / "result.json").write_bytes(result_bytes)
    _check_budget(start, output)
    files = sorted(p for p in output.iterdir() if p.is_file())
    (output / "SHA256SUMS").write_text(
        "".join(f"{_sha(path.read_bytes())}  {path.name}\n" for path in files),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--physics-pass", type=Path, default=DEFAULT_PHYSICS_PASS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        run(args.output, args.physics_pass)
    except BaseException as error:
        if args.output.is_dir() and not (args.output / "SHA256SUMS").exists():
            marker = args.output / "FAILED-INCOMPLETE"
            if not marker.exists():
                marker.write_text(
                    f"reason={type(error).__name__}: {error}\n", encoding="utf-8"
                )
        raise


if __name__ == "__main__":
    main()
