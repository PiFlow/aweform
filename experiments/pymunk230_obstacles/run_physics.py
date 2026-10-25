"""One-shot bounded physics suite plus a fresh-process canonical replay."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import resource
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, cast

import pymunk

from experiments.pymunk_contact_prototype.fixture import (
    ContactWorld,
    clearances_by_shape,
)

from .audit import clearances_by_object, free_path_minimum_clearances
from .cases import (
    EMPTY_FREE_COMMANDS,
    EMPTY_WALL_COMMANDS,
    PRIMARY_CASES,
    PRIMARY_ENGINE_STEPS,
    PRIMARY_LOGICAL_COMMANDS,
    TOTAL_ENGINE_STEPS_WITH_REPLAY,
)
from .world import ObstacleContactWorld

MAX_WALL_SECONDS = 20 * 60
MAX_CPU_SECONDS = 20 * 60
MAX_RSS_BYTES = 256 * 1024 * 1024
MAX_OUTPUT_BYTES = 10 * 1024 * 1024
MAX_RAW_CALLBACKS = 1_000_000
MAX_AGGREGATE_ROWS = 4_000
MAX_AGGREGATE_ROWS_PER_RESOLUTION = 1_000
MAX_AGGREGATE_ROW_BYTES = 512
MAX_COMMAND_ENVELOPE_BYTES = 2 * 1024
MAX_CASE_SUMMARY_BYTES = 2 * 1024
MAX_COMPARISON_BYTES = 1024
MAX_PROGRESS_BYTES = 1536 * 1024
MAX_EMPTY_PROGRESS_BYTES = 64 * 1024
MAX_CANONICAL_BYTES = 4 * 1024 * 1024
EXPECTED_PYTHON = "3.14.7"
EXPECTED_PYMUNK = "7.2.0"
EXPECTED_WHEEL_SHA256 = (
    "497c4a919fc7f03882cb9796b132ab3b5fcc4c4af9ead08e9631b6a9fb2da29c"
)
DEFAULT_OUTPUT = Path("experiments/pymunk230_obstacles/results/attempt-3")


class BudgetExceeded(RuntimeError):
    """A prospective attempt resource ceiling was reached."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _valid_identity(identity: str) -> bool:
    if identity in {
        "hull",
        "wall_west",
        "wall_east",
        "wall_south",
        "wall_north",
        "S1",
        "S2",
        "P1",
        "P2",
    }:
        return True
    for arc_name, maximum in (("A1", 30), ("A2", 23), ("A3", 23)):
        prefix = f"{arc_name}_"
        if identity.startswith(prefix):
            suffix = identity[len(prefix) :]
            return suffix.isdigit() and int(suffix) < maximum
    return False


def _parse_cpu_time(value: str) -> float:
    value = value.strip()
    days = 0
    if "-" in value:
        day_text, value = value.split("-", 1)
        days = int(day_text)
    parts = value.split(":")
    if len(parts) == 3:
        hours, minutes, seconds = int(parts[0]), int(parts[1]), float(parts[2])
    elif len(parts) == 2:
        hours, minutes, seconds = 0, int(parts[0]), float(parts[1])
    elif len(parts) == 1:
        hours, minutes, seconds = 0, 0, float(parts[0])
    else:
        raise ValueError(f"unrecognized ps cputime format: {value!r}")
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def _process_cpu_seconds(pid: int) -> float:
    value = subprocess.check_output(["ps", "-o", "cputime=", "-p", str(pid)], text=True)
    return _parse_cpu_time(value)


def _terminate_and_reap(proc: subprocess.Popen[bytes]) -> None:
    """Terminate only this runner's child and always wait it out."""
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def _aggregate_event_runs(events: list[dict[str, object]]) -> list[dict[str, object]]:
    """Run-length aggregate consecutive callbacks by exact shape-pair identity."""
    runs: list[dict[str, object]] = []
    by_pair: dict[tuple[str, ...], dict[str, object]] = {}
    for event in events:
        pair = tuple(cast(list[str], event["shape_pair"]))
        substep = int(cast(int, event["substep"]))
        previous = by_pair.get(pair)
        if previous is None or int(cast(int, previous["last_substep"])) + 1 != substep:
            row: dict[str, object] = {
                "shape_pair": list(pair),
                "first_substep": substep,
                "last_substep": substep,
                "callback_count": 1,
                "max_contact_points": int(cast(int, event["contact_points"])),
                "max_penetration_m": float(cast(float, event["penetration_m"])),
                "impulse_sum": float(cast(float, event["impulse"])),
                "impulse_max": float(cast(float, event["impulse"])),
            }
            runs.append(row)
            by_pair[pair] = row
        else:
            previous["last_substep"] = substep
            previous["callback_count"] = int(cast(int, previous["callback_count"])) + 1
            previous["max_contact_points"] = max(
                int(cast(int, previous["max_contact_points"])),
                int(cast(int, event["contact_points"])),
            )
            previous["max_penetration_m"] = max(
                float(cast(float, previous["max_penetration_m"])),
                float(cast(float, event["penetration_m"])),
            )
            previous["impulse_sum"] = float(
                cast(float, previous["impulse_sum"])
            ) + float(cast(float, event["impulse"]))
            previous["impulse_max"] = max(
                float(cast(float, previous["impulse_max"])),
                float(cast(float, event["impulse"])),
            )
    return runs


def _aggregate_contact_states(
    states: tuple[tuple[str, ...], ...],
) -> list[dict[str, object]]:
    """RLE exact per-substep simultaneous contact sets, including empty runs."""
    output: list[dict[str, object]] = []
    for substep, state in enumerate(states):
        identities = list(state)
        if output and output[-1]["identities"] == identities:
            output[-1]["last_substep"] = substep
            output[-1]["substep_count"] = (
                int(cast(int, output[-1]["substep_count"])) + 1
            )
        else:
            output.append(
                {
                    "first_substep": substep,
                    "last_substep": substep,
                    "substep_count": 1,
                    "identities": identities,
                }
            )
    return output


def _normalize_object(identity: str) -> str:
    if identity.startswith("A1_"):
        return "A1"
    if identity.startswith("A2_"):
        return "A2"
    if identity.startswith("A3_"):
        return "A3"
    return identity


def _event_dict(event: Any) -> dict[str, object]:
    return {
        "substep": event.substep_index,
        "shape_pair": list(event.shape_pair),
        "contact_points": event.contact_points,
        "impulse": event.impulse,
        "penetration_m": event.maximum_contact_penetration,
    }


def _one_case(
    case: Any,
    microsteps: int,
    callback_counter: list[int],
    callback_cap: int,
    aggregate_counter: list[int],
    aggregate_cap: int,
    resolution_aggregate_counter: list[int],
) -> dict[str, object]:
    world = ObstacleContactWorld(microsteps=microsteps)
    x, y, angle = case.start
    if case.reset_count:
        for _ in range(case.reset_count):
            world.reset((x, y), angle)
    else:
        world.body.position = (x, y)
        world.body.angle = angle
    start_clearances = clearances_by_object((x, y), angle)
    if min(start_clearances.values()) <= 0.0:
        raise RuntimeError(f"frozen start pose penetrates geometry: {case.case_id}")
    reset_contract_pass = case.reset_count == 0 or (
        (float(world.body.position.x), float(world.body.position.y)) == (x, y)
        and float(world.body.angle) == angle
        and world.body.velocity.length == 0.0
        and world.body.angular_velocity == 0.0
        and world.logical_steps == 0
        and world.engine_steps == 0
        and world.elapsed == 0.0
        and not world._contact_seen_this_command
        and not world._contact_events
    )
    commands: list[dict[str, object]] = []
    all_events: list[dict[str, object]] = []
    max_penetration = 0.0
    max_sampling_bound = 0.0
    max_substep_path_bound = 0.0
    crossed = False
    for index, command in enumerate(case.commands):
        record = world.advance(command)
        audit = world.last_audit
        events = [_event_dict(event) for event in record.contact_events]
        event_runs = _aggregate_event_runs(events)
        state_runs = _aggregate_contact_states(record.simultaneous_contact_identities)
        if any(
            len(_canonical_bytes(row)) > MAX_AGGREGATE_ROW_BYTES
            for row in event_runs + state_runs
        ):
            raise BudgetExceeded("aggregate row exceeds frozen 512-byte bound")
        callback_counter[0] += len(events)
        row_count = len(event_runs) + len(state_runs)
        aggregate_counter[0] += row_count
        resolution_aggregate_counter[0] += row_count
        if callback_counter[0] > callback_cap:
            raise BudgetExceeded("cumulative raw callback cap reached")
        if aggregate_counter[0] > aggregate_cap:
            raise BudgetExceeded("cumulative aggregate-row cap reached")
        if resolution_aggregate_counter[0] > MAX_AGGREGATE_ROWS_PER_RESOLUTION:
            raise BudgetExceeded("per-resolution aggregate-row cap reached")
        all_events.extend(event_runs)
        max_penetration = max(max_penetration, record.max_penetration)
        max_sampling_bound = max(max_sampling_bound, audit.clearance_sampling_bound_m)
        max_substep_path_bound = max(
            max_substep_path_bound, audit.maximum_substep_path_bound_m
        )
        crossed |= audit.crossing_detected
        command_row: dict[str, object] = {
            "index": index,
            "request_rad": list(record.request),
            "shaft_rad": list(record.shaft),
            "start_m": list(record.start),
            "start_yaw_rad": record.start_angle,
            "end_m": list(record.end),
            "end_yaw_rad": record.end_angle,
            "velocity_mps": list(record.velocity),
            "angular_velocity_rps": record.angular_velocity,
            "contact_seen": record.contact_seen,
            "max_penetration_m": record.max_penetration,
            "body_shaft_mismatch_m": record.body_shaft_mismatch,
            "minimum_clearance_by_object_m": dict(audit.minimum_clearance_by_object_m),
            "sampling_bound_m": audit.clearance_sampling_bound_m,
            "crossed": audit.crossing_detected,
            "raw_callback_count": len(events),
            "contact_event_runs": event_runs,
            "contact_state_runs": state_runs,
        }
        envelope = {
            key: value
            for key, value in command_row.items()
            if key not in {"contact_event_runs", "contact_state_runs"}
        }
        if len(_canonical_bytes(envelope)) > MAX_COMMAND_ENVELOPE_BYTES:
            raise BudgetExceeded("command envelope exceeds frozen 2 KiB bound")
        commands.append(command_row)
    observed_objects = {
        _normalize_object(name)
        for event in all_events
        for name in cast(list[str], event["shape_pair"])
        if name != "hull"
    }
    expected = set(case.expected_objects)
    contacts_expected = case.expect_contact
    final_position = (float(world.body.position.x), float(world.body.position.y))
    final_yaw = float(world.body.angle)
    end_clearances = clearances_by_object(final_position, final_yaw)
    classification_ok = (
        observed_objects == expected
        if contacts_expected
        else not all_events
        and min(end_clearances.values()) > 0.0
        and min(start_clearances.values()) > 0.0
    )
    if contacts_expected and not expected:
        classification_ok = bool(all_events)
    release_ok = True
    release_clearance_delta = 0.0
    if "release" in case.case_id:
        reverse_index = next(
            i
            for i, action in enumerate(case.commands)
            if action[0] < 0.0 and action[1] < 0.0
        )
        target = case.expected_objects[0]
        reverse_position = cast(list[float], commands[reverse_index]["start_m"])
        reversal_start = clearances_by_object(
            (reverse_position[0], reverse_position[1]),
            float(cast(float, commands[reverse_index]["start_yaw_rad"])),
        )[target]
        final_position_value = cast(list[float], commands[-1]["end_m"])
        final_position = (final_position_value[0], final_position_value[1])
        final_yaw = float(cast(float, commands[-1]["end_yaw_rad"]))
        release_clearance_delta = (
            clearances_by_object(final_position, final_yaw)[target] - reversal_start
        )
        release_ok = release_clearance_delta >= 0.01

    summary: dict[str, object] = {
        "case_id": case.case_id,
        "start": list(case.start),
        "start_min_clearance_m": min(start_clearances.values()),
        "expected_contact": contacts_expected,
        "expected_objects": sorted(expected),
        "observed_objects": sorted(observed_objects),
        "contact_classification_pass": classification_ok,
        "reset_count": case.reset_count,
        "reset_contract_pass": reset_contract_pass,
        "identity_pair": case.identity_pair,
        "max_penetration_m": max_penetration,
        "max_sampling_bound_m": max_sampling_bound,
        "max_substep_path_bound_m": max_substep_path_bound,
        "max_body_shaft_mismatch_m": max(
            (float(cast(float, row["body_shaft_mismatch_m"])) for row in commands),
            default=0.0,
        ),
        "crossing": crossed,
        "release_clearance_delta_m": release_clearance_delta,
        "release_pass": release_ok,
        "end_clearance_by_object_m": end_clearances,
        "minimum_clearance_by_object_m": dict(
            world.last_audit.minimum_clearance_by_object_m
        ),
        "commands": commands,
    }
    case_envelope = {key: value for key, value in summary.items() if key != "commands"}
    if len(_canonical_bytes(case_envelope)) > MAX_CASE_SUMMARY_BYTES:
        raise BudgetExceeded("case summary exceeds frozen 2 KiB bound")
    return summary


def _one_empty_case(
    case_id: str,
    start: tuple[float, float, float],
    commands: tuple[tuple[float, float], ...],
    microsteps: int,
) -> dict[str, object]:
    world = ContactWorld(microsteps=microsteps)
    world.body.position = (start[0], start[1])
    world.body.angle = start[2]
    rows: list[dict[str, object]] = []
    for index, command in enumerate(commands):
        record = world.advance(command)
        raw_events = [_event_dict(event) for event in record.contact_events]
        event_runs = _aggregate_event_runs(raw_events)
        state_runs = _aggregate_contact_states(record.simultaneous_contact_identities)
        if any(
            len(_canonical_bytes(row)) > MAX_AGGREGATE_ROW_BYTES
            for row in event_runs + state_runs
        ):
            raise BudgetExceeded("aggregate row exceeds frozen 512-byte bound")
        command_row: dict[str, object] = {
            "index": index,
            "start_m": list(record.start),
            "end_m": list(record.end),
            "end_yaw_rad": record.end_angle,
            "max_penetration_m": record.max_penetration,
            "minimum_clearance_m": record.minimum_clearance_m,
            "start_clearance_by_object_m": clearances_by_shape(
                record.start, record.start_angle
            ),
            "end_clearance_by_object_m": dict(record.end_clearance_by_shape),
            "sampling_bound_m": record.clearance_sampling_bound_m,
            "crossed": record.crossed_wall_or_post,
            "raw_callback_count": len(raw_events),
            "contact_event_runs": event_runs,
            "contact_state_runs": state_runs,
            "body_shaft_mismatch_m": record.body_shaft_mismatch,
        }
        envelope = {
            key: value
            for key, value in command_row.items()
            if key not in {"contact_event_runs", "contact_state_runs"}
        }
        if len(_canonical_bytes(envelope)) > MAX_COMMAND_ENVELOPE_BYTES:
            raise BudgetExceeded("empty command envelope exceeds 2 KiB bound")
        rows.append(command_row)
    wall_contact = any(
        "wall_west" in identity
        for row in rows
        for event in cast(list[dict[str, object]], row["contact_event_runs"])
        for identity in cast(list[str], event["shape_pair"])
    )
    release_clearance_delta = 0.0
    if case_id == "empty-room-west-wall-release":
        reverse_start = cast(dict[str, float], rows[5]["start_clearance_by_object_m"])[
            "wall_west"
        ]
        release_clearance_delta = (
            cast(dict[str, float], rows[-1]["end_clearance_by_object_m"])["wall_west"]
            - reverse_start
        )
    summary: dict[str, object] = {
        "case_id": case_id,
        "commands": rows,
        "west_wall_contact": wall_contact,
        "release_clearance_delta_m": release_clearance_delta,
    }
    if (
        len(
            _canonical_bytes(
                {key: value for key, value in summary.items() if key != "commands"}
            )
        )
        > MAX_CASE_SUMMARY_BYTES
    ):
        raise BudgetExceeded("empty-case summary exceeds 2 KiB bound")
    return summary


def _run_empty_regression(microsteps: int) -> list[dict[str, object]]:
    cases = [
        _one_empty_case(
            "empty-room-free-space", (1.0, 1.0, 0.0), EMPTY_FREE_COMMANDS, microsteps
        ),
        _one_empty_case(
            "empty-room-west-wall-release",
            (0.11, 1.5, math.pi),
            EMPTY_WALL_COMMANDS,
            microsteps,
        ),
    ]
    _check_runtime_budgets()
    return cases


def _run_resolution(
    microsteps: int,
    progress: Path | None = None,
    callback_counter: list[int] | None = None,
    callback_cap: int = MAX_RAW_CALLBACKS,
    aggregate_counter: list[int] | None = None,
    aggregate_cap: int = MAX_AGGREGATE_ROWS,
) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    callbacks = callback_counter if callback_counter is not None else [0]
    aggregates = aggregate_counter if aggregate_counter is not None else [0]
    resolution_aggregates = [0]
    for index, case in enumerate(PRIMARY_CASES):
        row = _one_case(
            case,
            microsteps,
            callbacks,
            callback_cap,
            aggregates,
            aggregate_cap,
            resolution_aggregates,
        )
        output.append(row)
        _check_runtime_budgets()
        if progress is not None:
            payload = _canonical_bytes(
                {"microsteps": microsteps, "completed": index + 1, "cases": output}
            )
            if len(payload) > MAX_PROGRESS_BYTES:
                raise BudgetExceeded("1.5 MiB case-progress cap reached")
            progress.write_bytes(payload)
            if (
                progress.parent.exists()
                and _directory_bytes(progress.parent) > MAX_OUTPUT_BYTES
            ):
                raise BudgetExceeded("10 MiB aggregate output cap reached")
        if time.monotonic() >= _deadline:
            raise BudgetExceeded("20-minute wall-clock cap reached")
    return output


def _peak_rss_bytes() -> int:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == "darwin" else value * 1024)


def _check_runtime_budgets() -> None:
    if time.process_time() > MAX_CPU_SECONDS:
        raise BudgetExceeded("20-minute aggregate process CPU-time cap reached")
    if _peak_rss_bytes() > MAX_RSS_BYTES:
        raise BudgetExceeded("256 MiB peak RSS cap reached")


def _directory_bytes(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _reset_identity(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    pairs: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        pair = row["identity_pair"]
        if isinstance(pair, str):
            pairs.setdefault(pair, []).append(row)
    output = []
    for key, pair_rows in sorted(pairs.items()):
        if len(pair_rows) != 2:
            output.append({"pair": key, "pass": False, "reason": "pair count"})
            continue
        reset_row = next(
            row for row in pair_rows if int(cast(int, row["reset_count"])) > 0
        )
        control_row = next(
            row for row in pair_rows if int(cast(int, row["reset_count"])) == 0
        )
        reset_commands = cast(list[dict[str, object]], reset_row["commands"])
        control_commands = cast(list[dict[str, object]], control_row["commands"])
        same = (
            [item["contact_event_runs"] for item in reset_commands]
            == [item["contact_event_runs"] for item in control_commands]
            and [item["contact_state_runs"] for item in reset_commands]
            == [item["contact_state_runs"] for item in control_commands]
            and [item["end_m"] for item in reset_commands]
            == [item["end_m"] for item in control_commands]
            and [item["contact_seen"] for item in reset_commands]
            == [item["contact_seen"] for item in control_commands]
            and [item["velocity_mps"] for item in reset_commands]
            == [item["velocity_mps"] for item in control_commands]
            and reset_row["observed_objects"] == control_row["observed_objects"]
        )
        output.append({"pair": key, "pass": same})
    return output


def _gate_resolution(rows: list[dict[str, object]]) -> dict[str, bool]:
    return {
        "contact_classifications": all(
            bool(row["contact_classification_pass"]) for row in rows
        ),
        "penetration_1mm": all(
            float(cast(float, row["max_penetration_m"])) <= 0.001 for row in rows
        ),
        "sampling_bound_0_2mm": all(
            float(cast(float, row["max_sampling_bound_m"])) <= 0.0002 for row in rows
        ),
        "substep_path_bound_0_2mm": all(
            float(cast(float, row["max_substep_path_bound_m"])) <= 0.0002
            for row in rows
        ),
        "no_tunneling": not any(bool(row["crossing"]) for row in rows),
        "release": all(bool(row["release_pass"]) for row in rows),
        "start_and_reset_clearance": all(
            float(cast(float, row["start_min_clearance_m"])) > 0.0
            and bool(row["reset_contract_pass"])
            for row in rows
        ),
        "positive_no_contact_end_clearance": all(
            bool(row["expected_contact"])
            or min(cast(dict[str, float], row["end_clearance_by_object_m"]).values())
            > 0.0
            for row in rows
        ),
        "known_contact_identity": all(
            _valid_identity(name)
            for row in rows
            for command in cast(list[dict[str, object]], row["commands"])
            for event in cast(list[dict[str, object]], command["contact_event_runs"])
            for name in cast(list[str], event["shape_pair"])
        ),
        "finite": all(
            math.isfinite(float(cast(float, row["max_penetration_m"]))) for row in rows
        ),
        "body_shaft_slip_bounded": all(
            float(cast(float, row["max_body_shaft_mismatch_m"])) <= 0.22 for row in rows
        ),
    }


def _count_events(canonical: bytes) -> int:
    value = cast(dict[str, object], json.loads(canonical))
    total = 0
    for resolution in ("400", "800"):
        rows = cast(
            list[dict[str, object]],
            cast(dict[str, object], value["resolution_summaries"])[resolution],
        )
        total += sum(
            int(cast(int, command["raw_callback_count"]))
            for row in rows
            for command in cast(list[dict[str, object]], row["commands"])
        )
    for resolution in ("400", "800"):
        cases = cast(
            list[dict[str, object]],
            cast(dict[str, object], value["empty_room_summaries"])[resolution],
        )
        for case in cases:
            for command in cast(list[dict[str, object]], case["commands"]):
                total += int(cast(int, command["raw_callback_count"]))
    return total


def _count_aggregate_rows(canonical: bytes) -> int:
    value = cast(dict[str, object], json.loads(canonical))
    total = 0
    for resolution in ("400", "800"):
        rows = cast(
            list[dict[str, object]],
            cast(dict[str, object], value["resolution_summaries"])[resolution],
        )
        total += sum(
            len(cast(list[object], command["contact_event_runs"]))
            + len(cast(list[object], command["contact_state_runs"]))
            for case in rows
            for command in cast(list[dict[str, object]], case["commands"])
        )
        empty = cast(
            list[dict[str, object]],
            cast(dict[str, object], value["empty_room_summaries"])[resolution],
        )
        total += sum(
            len(cast(list[object], command["contact_event_runs"]))
            + len(cast(list[object], command["contact_state_runs"]))
            for case in empty
            for command in cast(list[dict[str, object]], case["commands"])
        )
    return total


def _canonical_suite(
    rows400: list[dict[str, object]],
    rows800: list[dict[str, object]],
    empty400: list[dict[str, object]],
    empty800: list[dict[str, object]],
) -> dict[str, object]:
    comparisons: list[dict[str, object]] = []
    for first, second in zip(rows400, rows800):
        first_commands = cast(list[dict[str, object]], first["commands"])
        second_commands = cast(list[dict[str, object]], second["commands"])
        for index, (a, b) in enumerate(zip(first_commands, second_commands)):
            position_delta = math.dist(
                cast(list[float], a["end_m"]), cast(list[float], b["end_m"])
            )
            yaw_delta = abs(
                float(cast(float, a["end_yaw_rad"]))
                - float(cast(float, b["end_yaw_rad"]))
            )
            gaps_a = cast(dict[str, float], a["minimum_clearance_by_object_m"])
            gaps_b = cast(dict[str, float], b["minimum_clearance_by_object_m"])
            gap_delta = max(abs(gaps_a[name] - gaps_b[name]) for name in gaps_a)

            def object_ids(command: dict[str, object]) -> set[str]:
                return {
                    _normalize_object(name)
                    for event in cast(
                        list[dict[str, object]], command["contact_event_runs"]
                    )
                    for name in cast(list[str], event["shape_pair"])
                    if name != "hull"
                }

            ids_a, ids_b = object_ids(a), object_ids(b)
            disagreement = ids_a.symmetric_difference(ids_b)
            near_zero = bool(disagreement) and all(
                min(abs(gaps_a[name]), abs(gaps_b[name])) <= 0.0005
                for name in disagreement
            )
            comparison_row: dict[str, object] = {
                "case_id": first["case_id"],
                "command": index,
                "position_difference_m": position_delta,
                "yaw_difference_rad": yaw_delta,
                "clearance_difference_m": gap_delta,
                "contact_state_disagreement": ids_a != ids_b,
                "contact_disagreement_near_boundary": ids_a == ids_b or near_zero,
                "contact_object_ids_400": sorted(ids_a),
                "contact_object_ids_800": sorted(ids_b),
            }
            if len(_canonical_bytes(comparison_row)) > MAX_COMPARISON_BYTES:
                raise BudgetExceeded("resolution comparison exceeds frozen 1 KiB bound")
            comparisons.append(comparison_row)
    gates = {
        "400": _gate_resolution(rows400),
        "800": _gate_resolution(rows800),
        "position_convergence_0_5mm": all(
            cast(float, item["position_difference_m"]) <= 0.0005 for item in comparisons
        ),
        "yaw_convergence_0_001rad": all(
            cast(float, item["yaw_difference_rad"]) <= 0.001 for item in comparisons
        ),
        "clearance_convergence_0_5mm": all(
            cast(float, item["clearance_difference_m"]) <= 0.0005
            for item in comparisons
        ),
        "contact_state_convergence": all(
            bool(item["contact_disagreement_near_boundary"]) for item in comparisons
        ),
        "reset_behavioral_identity": all(
            bool(item["pass"]) for item in _reset_identity(rows400)
        )
        and all(bool(item["pass"]) for item in _reset_identity(rows800)),
    }
    empty_comparisons: list[dict[str, object]] = []
    for case400, case800 in zip(empty400, empty800):
        commands400 = cast(list[dict[str, object]], case400["commands"])
        commands800 = cast(list[dict[str, object]], case800["commands"])
        for command400, command800 in zip(commands400, commands800):

            def wall_contact_ids(command: dict[str, object]) -> list[str]:
                return sorted(
                    {
                        name
                        for event in cast(
                            list[dict[str, object]], command["contact_event_runs"]
                        )
                        for name in cast(list[str], event["shape_pair"])
                        if name != "hull"
                    }
                )

            ids400 = wall_contact_ids(command400)
            ids800 = wall_contact_ids(command800)
            seen400 = int(cast(int, command400["raw_callback_count"])) > 0
            seen800 = int(cast(int, command800["raw_callback_count"])) > 0
            empty_comparison: dict[str, object] = {
                "case_id": case400["case_id"],
                "position_difference_m": math.dist(
                    cast(list[float], command400["end_m"]),
                    cast(list[float], command800["end_m"]),
                ),
                "yaw_difference_rad": abs(
                    float(cast(float, command400["end_yaw_rad"]))
                    - float(cast(float, command800["end_yaw_rad"]))
                ),
                "clearance_difference_m": abs(
                    float(cast(float, command400["minimum_clearance_m"]))
                    - float(cast(float, command800["minimum_clearance_m"]))
                ),
                "penetration_m": max(
                    float(cast(float, command400["max_penetration_m"])),
                    float(cast(float, command800["max_penetration_m"])),
                ),
                "crossed": bool(command400["crossed"]) or bool(command800["crossed"]),
                "contact_object_ids_400": ids400,
                "contact_object_ids_800": ids800,
                "contact_state_equal": ids400 == ids800 and seen400 == seen800,
            }
            if len(_canonical_bytes(empty_comparison)) > MAX_COMPARISON_BYTES:
                raise BudgetExceeded("empty comparison exceeds frozen 1 KiB bound")
            empty_comparisons.append(empty_comparison)
    free = next(case for case in empty400 if case["case_id"] == "empty-room-free-space")
    free_command = cast(list[dict[str, object]], free["commands"])[0]
    free_position_error = math.dist(
        cast(list[float], free_command["end_m"]),
        (1.0 + 0.045 * 0.6457718232379019, 1.0),
    )
    free_yaw_error = abs(float(cast(float, free_command["end_yaw_rad"])))
    empty_wall400 = next(
        case for case in empty400 if case["case_id"] == "empty-room-west-wall-release"
    )
    empty_wall800 = next(
        case for case in empty800 if case["case_id"] == "empty-room-west-wall-release"
    )
    obstacle_free_rows = [
        next(row for row in rows if row["case_id"] == "empty-free")
        for rows in (rows400, rows800)
    ]
    expected_free_position = (1.0 + 0.045 * 0.6457718232379019, 1.0)
    obstacle_free_errors = [
        (
            math.dist(
                cast(
                    list[float],
                    cast(list[dict[str, object]], row["commands"])[0]["end_m"],
                ),
                expected_free_position,
            ),
            abs(
                float(
                    cast(
                        float,
                        cast(list[dict[str, object]], row["commands"])[0][
                            "end_yaw_rad"
                        ],
                    )
                )
            ),
        )
        for row in obstacle_free_rows
    ]
    empty_free_yaw_errors = [
        abs(
            float(
                cast(
                    float,
                    cast(list[dict[str, object]], case["commands"])[0]["end_yaw_rad"],
                )
            )
        )
        for case in (
            next(
                item for item in empty400 if item["case_id"] == "empty-room-free-space"
            ),
            next(
                item for item in empty800 if item["case_id"] == "empty-room-free-space"
            ),
        )
    ]
    empty_control_gates = {
        "free_space_calibration_position_yaw_1e-5": free_position_error <= 1e-5
        and free_yaw_error <= 1e-5
        and all(
            position <= 1e-5 and yaw <= 1e-5 for position, yaw in obstacle_free_errors
        )
        and all(yaw <= 1e-5 for yaw in empty_free_yaw_errors),
        "free_space_end_clearance_positive": all(
            min(cast(dict[str, float], row["end_clearance_by_object_m"]).values()) > 0.0
            for row in obstacle_free_rows
        )
        and all(
            min(
                cast(
                    dict[str, float],
                    cast(list[dict[str, object]], case["commands"])[0][
                        "end_clearance_by_object_m"
                    ],
                ).values()
            )
            > 0.0
            for case in (
                next(
                    item
                    for item in empty400
                    if item["case_id"] == "empty-room-free-space"
                ),
                next(
                    item
                    for item in empty800
                    if item["case_id"] == "empty-room-free-space"
                ),
            )
        ),
        "free_space_position_error_1e-5": free_position_error <= 1e-5,
        "wall_contact_both_resolutions": bool(empty_wall400["west_wall_contact"])
        and bool(empty_wall800["west_wall_contact"]),
        "reverse_release_both_resolutions": float(
            cast(float, empty_wall400["release_clearance_delta_m"])
        )
        >= 0.01
        and float(cast(float, empty_wall800["release_clearance_delta_m"])) >= 0.01,
        "penetration_1mm": all(
            float(cast(float, item["penetration_m"])) <= 0.001
            for item in empty_comparisons
        ),
        "sampling_bound_0_2mm": all(
            float(cast(float, command["sampling_bound_m"])) <= 0.0002
            for case in (empty400 + empty800)
            for command in cast(list[dict[str, object]], case["commands"])
        ),
        "no_tunneling": not any(bool(item["crossed"]) for item in empty_comparisons),
        "contact_state_convergence": all(
            bool(item["contact_state_equal"]) for item in empty_comparisons
        ),
        "body_shaft_slip_bounded": all(
            float(cast(float, command["body_shaft_mismatch_m"])) <= 0.22
            for case in (empty400 + empty800)
            for command in cast(list[dict[str, object]], case["commands"])
        ),
        "positive_free_end_clearance": all(
            case["case_id"] != "empty-room-free-space"
            or min(
                cast(
                    dict[str, float],
                    cast(list[dict[str, object]], case["commands"])[0][
                        "end_clearance_by_object_m"
                    ],
                ).values()
            )
            > 0.0
            for case in (empty400 + empty800)
        ),
        "position_convergence_0_5mm": all(
            float(cast(float, item["position_difference_m"])) <= 0.0005
            for item in empty_comparisons
        ),
        "yaw_convergence_0_001rad": all(
            float(cast(float, item["yaw_difference_rad"])) <= 0.001
            for item in empty_comparisons
        ),
        "clearance_convergence_0_5mm": all(
            float(cast(float, item["clearance_difference_m"])) <= 0.0005
            for item in empty_comparisons
        ),
    }
    gates["empty_room_regression"] = empty_control_gates
    gates["essential_pass"] = all(
        value if isinstance(value, bool) else all(cast(dict[str, bool], value).values())
        for value in gates.values()
    )
    return {
        "schema": "pymunk230-physics-v1",
        "case_count": len(PRIMARY_CASES),
        "logical_commands_per_resolution": PRIMARY_LOGICAL_COMMANDS,
        "engine_steps_by_resolution": {
            "400": PRIMARY_LOGICAL_COMMANDS * 400,
            "800": PRIMARY_LOGICAL_COMMANDS * 800,
        },
        "primary_engine_steps": PRIMARY_ENGINE_STEPS,
        "total_engine_steps_including_replay": TOTAL_ENGINE_STEPS_WITH_REPLAY,
        "resolution_summaries": {"400": rows400, "800": rows800},
        "empty_room_summaries": {"400": empty400, "800": empty800},
        "empty_room_comparisons": empty_comparisons,
        "comparisons": comparisons,
        "reset_identity": {
            "400": _reset_identity(rows400),
            "800": _reset_identity(rows800),
        },
        "gates": gates,
    }


_deadline = math.inf


def _rss_limit_target(
    inherited: tuple[int, int], cap: int = MAX_RSS_BYTES
) -> tuple[int, int]:
    """Lower only the RSS soft limit; never raise or lower an inherited hard limit."""
    soft, hard = inherited
    infinity = resource.RLIM_INFINITY
    if hard != infinity and (soft == infinity or soft > hard):
        raise ValueError("inherited RLIMIT_RSS soft limit exceeds its hard limit")
    target_soft = cap
    if soft != infinity:
        target_soft = min(target_soft, soft)
    if hard != infinity:
        target_soft = min(target_soft, hard)
    return target_soft, hard


def _rss_enforcement_mode() -> str:
    if not hasattr(resource, "RLIMIT_RSS"):
        return "high-water checks only; RLIMIT_RSS unavailable"
    if sys.platform == "darwin":
        return "high-water checks only; Darwin rejects finite RLIMIT_RSS limits"
    return "RLIMIT_RSS soft limit plus high-water checks"


def _apply_rss_limit() -> None:
    if not hasattr(resource, "RLIMIT_RSS") or sys.platform == "darwin":
        return
    inherited = resource.getrlimit(resource.RLIMIT_RSS)
    target = _rss_limit_target(inherited)
    resource.setrlimit(resource.RLIMIT_RSS, target)
    effective = resource.getrlimit(resource.RLIMIT_RSS)
    if effective[0] > MAX_RSS_BYTES:
        raise RuntimeError("effective RLIMIT_RSS soft limit exceeds frozen 256 MiB cap")


def _resource_limits(budget_seconds: int = MAX_WALL_SECONDS) -> None:
    signal.signal(
        signal.SIGALRM,
        lambda *_: (_ for _ in ()).throw(BudgetExceeded("wall-clock timeout")),
    )
    signal.setitimer(signal.ITIMER_REAL, budget_seconds)
    resource.setrlimit(resource.RLIMIT_CPU, (MAX_CPU_SECONDS, MAX_CPU_SECONDS))
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_OUTPUT_BYTES, MAX_OUTPUT_BYTES))
    _apply_rss_limit()


PHYSICS_SOURCE_FILES = (
    "experiments/pymunk_contact_prototype/fixture.py",
    "experiments/pymunk230_obstacles/audit.py",
    "experiments/pymunk230_obstacles/cases.py",
    "experiments/pymunk230_obstacles/geometry.py",
    "experiments/pymunk230_obstacles/run_physics.py",
    "experiments/pymunk230_obstacles/world.py",
)


def _physics_source_sha256() -> str:
    digest = hashlib.sha256()
    for relative in PHYSICS_SOURCE_FILES:
        path = Path(relative)
        digest.update(relative.encode("utf-8") + b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def _physics_protocol_sha256() -> str:
    text = Path(__file__).with_name("protocol.md").read_text(encoding="utf-8")
    physics_text = text.split("## Sole conditional Level-1 lifetime", 1)[0]
    return hashlib.sha256(physics_text.encode("utf-8")).hexdigest()


def _preflight(*, require_wheel: bool = False) -> dict[str, object]:
    if sys.version.split()[0] != EXPECTED_PYTHON:
        raise RuntimeError(f"expected Python {EXPECTED_PYTHON}")
    if pymunk.version != EXPECTED_PYMUNK:
        raise RuntimeError(f"expected Pymunk {EXPECTED_PYMUNK}")
    wheel_path_value = os.environ.get("PYMUNK_WHEEL_PATH")
    wheel_sha = None
    if wheel_path_value:
        wheel_path = Path(wheel_path_value)
        if not wheel_path.is_file():
            raise RuntimeError("PYMUNK_WHEEL_PATH is not a file")
        wheel_sha = hashlib.sha256(wheel_path.read_bytes()).hexdigest()
        if wheel_sha != EXPECTED_WHEEL_SHA256:
            raise RuntimeError("Pymunk wheel SHA-256 differs from frozen v3 pin")
    elif require_wheel:
        raise RuntimeError("PYMUNK_WHEEL_PATH must identify the frozen Pymunk wheel")
    start_clearances = {
        case.case_id: min(
            clearances_by_object((case.start[0], case.start[1]), case.start[2]).values()
        )
        for case in PRIMARY_CASES
    }
    if any(value <= 0.0 for value in start_clearances.values()):
        raise RuntimeError("frozen case table lacks positive initial clearance")
    reachability = {
        case.case_id: free_path_minimum_clearances(case.start, case.commands)
        for case in PRIMARY_CASES
    }
    unreachable = [
        case.case_id
        for case in PRIMARY_CASES
        if case.expect_contact
        and not any(
            reachability[case.case_id][name] <= 0.0 for name in case.expected_objects
        )
    ]
    if unreachable:
        raise RuntimeError(f"contact cases miss expected geometry: {unreachable}")
    free_bytes = shutil.disk_usage(Path.cwd()).free
    if free_bytes < 20 * 1024 * 1024:
        raise RuntimeError("less than 20 MiB free disk before measurement")
    return {
        "python": sys.version.split()[0],
        "pymunk": pymunk.version,
        "pymunk_wheel_sha256": wheel_sha,
        "formal_seed_23001_unreserved": True,
        "minimum_case_start_clearance_m": min(start_clearances.values()),
        "case_start_clearance_m": start_clearances,
        "case_expected_free_path_min_clearance_m": {
            case.case_id: min(
                (reachability[case.case_id][name] for name in case.expected_objects),
                default=None,
            )
            for case in PRIMARY_CASES
        },
        "free_disk_bytes": free_bytes,
        "cases": len(PRIMARY_CASES),
        "logical_commands_per_resolution": PRIMARY_LOGICAL_COMMANDS,
        "engine_steps_by_resolution": {
            "400": PRIMARY_LOGICAL_COMMANDS * 400,
            "800": PRIMARY_LOGICAL_COMMANDS * 800,
        },
        "primary_engine_steps": PRIMARY_ENGINE_STEPS,
        "measured_resolutions": [400, 800],
        "fresh_process_replay_resolutions": [400, 800],
        "total_engine_steps_including_replay": TOTAL_ENGINE_STEPS_WITH_REPLAY,
        "wall_clock_cap_s": MAX_WALL_SECONDS,
        "cpu_time_cap_s": MAX_CPU_SECONDS,
        "rss_cap_bytes": MAX_RSS_BYTES,
        "rss_enforcement_mode": _rss_enforcement_mode(),
        "output_cap_bytes": MAX_OUTPUT_BYTES,
        "raw_callback_cap": MAX_RAW_CALLBACKS,
        "aggregate_row_cap": MAX_AGGREGATE_ROWS,
        "aggregate_row_cap_per_resolution": MAX_AGGREGATE_ROWS_PER_RESOLUTION,
        "progress_cap_bytes": MAX_PROGRESS_BYTES,
        "empty_progress_cap_bytes": MAX_EMPTY_PROGRESS_BYTES,
        "canonical_cap_bytes": MAX_CANONICAL_BYTES,
        "physics_source_sha256": _physics_source_sha256(),
        "physics_protocol_sha256": _physics_protocol_sha256(),
    }


def _run(
    output: Path,
    *,
    worker: bool,
    callback_cap: int,
    aggregate_cap: int,
    budget_seconds: int,
) -> bytes:
    global _deadline
    _resource_limits(budget_seconds)
    _deadline = time.monotonic() + budget_seconds
    progress = output / ("replay-progress.json" if worker else "primary-progress.json")
    empty_progress = output / (
        "replay-empty-progress.json" if worker else "primary-empty-progress.json"
    )
    callback_counter = [0]
    aggregate_counter = [0]
    rows400 = _run_resolution(
        400,
        progress,
        callback_counter,
        callback_cap,
        aggregate_counter,
        aggregate_cap,
    )
    rows800 = _run_resolution(
        800,
        progress,
        callback_counter,
        callback_cap,
        aggregate_counter,
        aggregate_cap,
    )
    empty400 = _run_empty_regression(400)
    empty800 = _run_empty_regression(800)
    for cases in (empty400, empty800):
        for case in cases:
            for command in cast(list[dict[str, object]], case["commands"]):
                callback_counter[0] += int(cast(int, command["raw_callback_count"]))
                aggregate_counter[0] += len(
                    cast(list[object], command["contact_event_runs"])
                ) + len(cast(list[object], command["contact_state_runs"]))
    for primary_rows, empty_rows in ((rows400, empty400), (rows800, empty800)):
        per_resolution_rows = sum(
            len(cast(list[object], command["contact_event_runs"]))
            + len(cast(list[object], command["contact_state_runs"]))
            for case in primary_rows
            for command in cast(list[dict[str, object]], case["commands"])
        ) + sum(
            len(cast(list[object], command["contact_event_runs"]))
            + len(cast(list[object], command["contact_state_runs"]))
            for case in empty_rows
            for command in cast(list[dict[str, object]], case["commands"])
        )
        if per_resolution_rows > MAX_AGGREGATE_ROWS_PER_RESOLUTION:
            raise BudgetExceeded("per-resolution aggregate-row cap reached")
    empty_progress.write_bytes(
        _canonical_bytes({"empty400": empty400, "empty800": empty800})
    )
    if empty_progress.stat().st_size > MAX_EMPTY_PROGRESS_BYTES:
        raise BudgetExceeded("64 KiB empty-room progress cap reached")
    if callback_counter[0] > callback_cap:
        raise BudgetExceeded("cumulative raw callback cap reached")
    if aggregate_counter[0] > aggregate_cap:
        raise BudgetExceeded("cumulative aggregate-row cap reached")
    if _directory_bytes(output) > MAX_OUTPUT_BYTES:
        raise BudgetExceeded("10 MiB aggregate output cap reached")
    canonical = _canonical_bytes(_canonical_suite(rows400, rows800, empty400, empty800))
    if len(canonical) > MAX_CANONICAL_BYTES:
        raise BudgetExceeded("4 MiB canonical suite cap reached")
    return canonical


def _source_tree_clean_except_attempt_artifacts() -> bool:
    if subprocess.run(["git", "diff", "--quiet"], check=False).returncode != 0:
        return False
    if (
        subprocess.run(["git", "diff", "--cached", "--quiet"], check=False).returncode
        != 0
    ):
        return False
    status = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=all"], text=True
    ).splitlines()
    for line in status:
        if not line.startswith("?? experiments/pymunk230_obstacles/results/attempt-"):
            return False
        relative = line[3:]
        parts = Path(relative).parts
        if len(parts) < 5 or parts[:3] != (
            "experiments",
            "pymunk230_obstacles",
            "results",
        ):
            return False
        attempt_name = parts[3]
        if not attempt_name.startswith("attempt-"):
            return False
        try:
            attempt = int(attempt_name.removeprefix("attempt-"))
        except ValueError:
            return False
        if not 1 <= attempt <= 4 or attempt_name != f"attempt-{attempt}":
            return False
    return True


def _validate_attempt_output(
    output: Path,
    head: str,
    protocol_sha: str,
    physics_source_sha: str,
    physics_protocol_sha: str,
) -> int:
    root = Path("experiments/pymunk230_obstacles/results")
    if output.parent != root or not output.name.startswith("attempt-"):
        raise RuntimeError("measurement output must be results/attempt-N")
    try:
        attempt = int(output.name.removeprefix("attempt-"))
    except ValueError as error:
        raise RuntimeError("attempt directory must use canonical attempt-N") from error
    if not 1 <= attempt <= 4 or output.name != f"attempt-{attempt}":
        raise RuntimeError("attempt number must be canonical and within 1..4")
    existing = []
    for path in root.glob("attempt-*"):
        try:
            number = int(path.name.removeprefix("attempt-"))
        except ValueError as error:
            raise RuntimeError(
                f"noncanonical prior attempt directory: {path}"
            ) from error
        existing.append(number)
        marker = path / "MEASUREMENT_STARTED"
        if marker.is_file():
            fields = dict(
                line.split("=", 1)
                for line in marker.read_text(encoding="utf-8").splitlines()
                if "=" in line
            )
            same_frozen_physics = (
                fields.get("physics_source_sha256") == physics_source_sha
                and fields.get("physics_protocol_sha256") == physics_protocol_sha
            )
            if same_frozen_physics or (
                fields.get("head") == head
                and fields.get("protocol_sha256") == protocol_sha
            ):
                raise RuntimeError("source/protocol pair already has an attempt")
    if attempt != max(existing, default=0) + 1:
        raise RuntimeError("attempt directory must be the next consecutive attempt")
    if output.exists():
        raise RuntimeError(f"refusing existing one-shot output path: {output}")
    return attempt


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--measure", action="store_true")
    mode.add_argument("--fresh-replay-worker", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--callback-cap", type=int, default=MAX_RAW_CALLBACKS)
    parser.add_argument("--aggregate-cap", type=int, default=MAX_AGGREGATE_ROWS)
    parser.add_argument("--budget-seconds", type=int, default=MAX_WALL_SECONDS)
    args = parser.parse_args()
    if args.preflight:
        print(json.dumps(_preflight(), sort_keys=True, indent=2))
        return
    output: Path = args.output
    if args.fresh_replay_worker:
        if not output.is_dir():
            raise RuntimeError("replay worker requires existing attempt directory")
        marker_path = output / "MEASUREMENT_STARTED"
        primary_path = output / "primary-canonical.json"
        if not marker_path.is_file() or not primary_path.is_file():
            raise RuntimeError("replay worker requires a started, completed primary")
        marker = dict(
            line.split("=", 1)
            for line in marker_path.read_text(encoding="utf-8").splitlines()
            if "=" in line
        )
        current_head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip()
        current_protocol = hashlib.sha256(
            Path(__file__).with_name("protocol.md").read_bytes()
        ).hexdigest()
        if (
            marker.get("head") != current_head
            or marker.get("protocol_sha256") != current_protocol
        ):
            raise RuntimeError(
                "replay worker source/protocol differs from attempt freeze"
            )
        if not 1 <= args.budget_seconds <= MAX_WALL_SECONDS:
            raise RuntimeError("replay worker wall budget exceeds the frozen maximum")
        if primary_path.stat().st_size > MAX_CANONICAL_BYTES:
            raise RuntimeError("primary canonical input exceeds the frozen size cap")
        primary_bytes = primary_path.read_bytes()
        remaining_callbacks = MAX_RAW_CALLBACKS - _count_events(primary_bytes)
        remaining_rows = MAX_AGGREGATE_ROWS - _count_aggregate_rows(primary_bytes)
        if (
            not 0 <= args.callback_cap <= remaining_callbacks
            or not 0 <= args.aggregate_cap <= remaining_rows
        ):
            raise RuntimeError("replay worker caps exceed the remaining attempt budget")
        replay_path = output / "fresh-process-canonical.json"
        replay_progress = output / "replay-progress.json"
        empty_progress = output / "replay-empty-progress.json"
        if replay_path.exists() or replay_progress.exists() or empty_progress.exists():
            raise RuntimeError("refusing replay-worker output overwrite")
        canonical = _run(
            output,
            worker=True,
            callback_cap=args.callback_cap,
            aggregate_cap=args.aggregate_cap,
            budget_seconds=args.budget_seconds,
        )
        if len(canonical) > MAX_CANONICAL_BYTES:
            raise BudgetExceeded("4 MiB canonical output cap reached")
        if _directory_bytes(output) + len(canonical) > MAX_OUTPUT_BYTES:
            raise BudgetExceeded("10 MiB aggregate output cap reached")
        replay_path.write_bytes(canonical)
        return
    if not args.measure:
        raise RuntimeError("select exactly one execution mode")
    if (
        args.callback_cap != MAX_RAW_CALLBACKS
        or args.aggregate_cap != MAX_AGGREGATE_ROWS
        or args.budget_seconds != MAX_WALL_SECONDS
    ):
        raise RuntimeError("measurement does not permit non-frozen cap overrides")
    preflight = _preflight(require_wheel=True)
    branch = subprocess.check_output(
        ["git", "branch", "--show-current"], text=True
    ).strip()
    if (
        branch != "fm/pymunk230-seven-obstacle"
        or not _source_tree_clean_except_attempt_artifacts()
    ):
        raise RuntimeError(
            "measurement requires committed source and only prior attempt artifacts"
        )
    source_head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()
    protocol_sha = hashlib.sha256(
        Path(__file__).with_name("protocol.md").read_bytes()
    ).hexdigest()
    attempt = _validate_attempt_output(
        output,
        source_head,
        protocol_sha,
        str(preflight["physics_source_sha256"]),
        str(preflight["physics_protocol_sha256"]),
    )
    output.mkdir(parents=True)
    started = time.monotonic()
    attempt_cpu_started = time.process_time()
    (output / "MEASUREMENT_STARTED").write_text(
        "\n".join(
            [
                f"head={source_head}",
                f"protocol_sha256={protocol_sha}",
                f"physics_source_sha256={preflight['physics_source_sha256']}",
                f"physics_protocol_sha256={preflight['physics_protocol_sha256']}",
                f"attempt={attempt}",
                "effective_caps="
                + json.dumps(preflight, sort_keys=True, separators=(",", ":")),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    proc: subprocess.Popen[bytes] | None = None
    try:
        primary = _run(
            output,
            worker=False,
            callback_cap=MAX_RAW_CALLBACKS,
            aggregate_cap=MAX_AGGREGATE_ROWS,
            budget_seconds=MAX_WALL_SECONDS,
        )
        primary_path = output / "primary-canonical.json"
        if _directory_bytes(output) + len(primary) > MAX_OUTPUT_BYTES:
            raise BudgetExceeded("10 MiB aggregate output cap reached")
        primary_path.write_bytes(primary)
        (output / "primary-progress.json").unlink(missing_ok=True)
        (output / "primary-empty-progress.json").unlink(missing_ok=True)
        replay_path = output / "fresh-process-canonical.json"
        remaining_wall = max(1, int(MAX_WALL_SECONDS - (time.monotonic() - started)))
        command = [
            sys.executable,
            "-m",
            "experiments.pymunk230_obstacles.run_physics",
            "--fresh-replay-worker",
            "--output",
            str(output),
            "--callback-cap",
            str(MAX_RAW_CALLBACKS - _count_events(primary)),
            "--aggregate-cap",
            str(MAX_AGGREGATE_ROWS - _count_aggregate_rows(primary)),
            "--budget-seconds",
            str(remaining_wall),
        ]
        proc = subprocess.Popen(command)
        replay_pid = proc.pid
        try:
            while proc.poll() is None:
                if time.monotonic() - started >= MAX_WALL_SECONDS:
                    raise BudgetExceeded("20-minute aggregate wall-clock cap reached")
                try:
                    rss_kib = int(
                        subprocess.check_output(
                            ["ps", "-o", "rss=", "-p", str(replay_pid)], text=True
                        ).strip()
                    )
                    if rss_kib * 1024 > MAX_RSS_BYTES:
                        raise BudgetExceeded("fresh replay exceeded 256 MiB RSS cap")
                    aggregate_cpu = time.process_time() - attempt_cpu_started
                    aggregate_cpu += _process_cpu_seconds(replay_pid)
                    if aggregate_cpu > MAX_CPU_SECONDS:
                        raise BudgetExceeded("20-minute aggregate CPU-time cap reached")
                except subprocess.CalledProcessError:
                    if proc.poll() is not None:
                        break
                    raise
                time.sleep(0.25)
        finally:
            _terminate_and_reap(proc)
        if proc.returncode != 0:
            raise RuntimeError(f"fresh-process replay exit={proc.returncode}")
        fresh = replay_path.read_bytes()
        (output / "replay-progress.json").unlink(missing_ok=True)
        (output / "replay-empty-progress.json").unlink(missing_ok=True)
        if _directory_bytes(output) > MAX_OUTPUT_BYTES:
            raise BudgetExceeded("10 MiB aggregate output cap reached")
        replay_identical = fresh == primary
        physics_gates = cast(dict[str, object], json.loads(primary))["gates"]
        result = {
            "schema": "pymunk230-attempt-v1",
            "head": source_head,
            "protocol_sha256": protocol_sha,
            "physics_source_sha256": preflight["physics_source_sha256"],
            "physics_protocol_sha256": preflight["physics_protocol_sha256"],
            "counts": preflight,
            "effective_caps": {
                "wall_seconds": MAX_WALL_SECONDS,
                "aggregate_cpu_seconds": MAX_CPU_SECONDS,
                "rss_bytes_per_process": MAX_RSS_BYTES,
                "rss_enforcement_mode": preflight["rss_enforcement_mode"],
                "total_output_bytes": MAX_OUTPUT_BYTES,
                "raw_callback_rows": MAX_RAW_CALLBACKS,
                "stored_aggregate_rows": MAX_AGGREGATE_ROWS,
                "stored_rows_per_resolution": MAX_AGGREGATE_ROWS_PER_RESOLUTION,
            },
            "raw_callback_count": _count_events(primary) + _count_events(fresh),
            "aggregate_row_count": _count_aggregate_rows(primary)
            + _count_aggregate_rows(fresh),
            "replay_identical": replay_identical,
            "fresh_process_pid": replay_pid,
            "fresh_process_distinct": replay_pid != os.getpid(),
            "aggregate_cpu_seconds": time.process_time()
            - attempt_cpu_started
            + resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime
            + resource.getrusage(resource.RUSAGE_CHILDREN).ru_stime,
            "primary_sha256": _sha(primary),
            "fresh_process_sha256": _sha(fresh),
            "elapsed_wall_s": time.monotonic() - started,
            "physics_gates": physics_gates,
            "essential_physics_pass": replay_identical
            and bool(cast(dict[str, object], physics_gates)["essential_pass"]),
        }
        result_bytes = _canonical_bytes(result)
        if len(result_bytes) + len(primary) + len(fresh) > MAX_OUTPUT_BYTES:
            raise BudgetExceeded("10 MiB combined output cap reached")
        (output / "results.json").write_bytes(result_bytes)
        if _directory_bytes(output) > MAX_OUTPUT_BYTES:
            raise BudgetExceeded("10 MiB aggregate output cap reached")
        (output / "SHA256SUMS").write_text(
            "".join(
                f"{_sha(path.read_bytes())}  {path.name}\n"
                for path in sorted(output.iterdir())
                if path.is_file() and path.name != "SHA256SUMS"
            ),
            encoding="utf-8",
        )
    except BaseException as error:
        if proc is not None:
            _terminate_and_reap(proc)
        (output / "FAILED-INCOMPLETE").write_text(
            f"head={source_head}\nprotocol_sha256={protocol_sha}\n"
            f"reason={type(error).__name__}: {error}\n"
            f"elapsed_wall_s={time.monotonic() - started:.6f}\n",
            encoding="utf-8",
        )
        raise


if __name__ == "__main__":
    main()
