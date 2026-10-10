"""Explicit, serial fixed-command experiment runner; never called by tests."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import cast

import pymunk

from .cases import Case, fixed_cases
from .fixture import (
    ENCODER_QUANTUM,
    MAX_DELTA,
    ContactWorld,
    circle_penetration,
    corners,
    parse_action,
    quantize_encoder,
    wall_penetration,
)

BASE_SHA = "8188cbb2224906ccb01824f4fb75c85ac55b726e"
EXPECTED_BRANCH = "fm/pymunk226-contact-prototype"
PROTOCOL = Path(__file__).with_name("protocol.md")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def independent_arc(
    start: tuple[float, float], heading: float, left: float, right: float
) -> tuple[tuple[float, float], float]:
    """Independent exact differential-drive arc; not used to move the body."""
    r, track = 0.045, 0.185
    dl, dr = r * left, r * right
    ds, dyaw = (dl + dr) / 2.0, (dr - dl) / track
    half = dyaw / 2
    sinc = 1.0 if half == 0.0 else math.sin(half) / half
    forward, lateral = ds * sinc * math.cos(half), ds * sinc * math.sin(half)
    x = start[0] + forward * math.cos(heading) - lateral * math.sin(heading)
    y = start[1] + forward * math.sin(heading) + lateral * math.cos(heading)
    return (x, y), heading + dyaw


def _single_case(case: Case) -> dict[str, object]:
    world = ContactWorld(microsteps=case.microsteps, posts=case.posts)
    start_position = (float(case.start[0]), float(case.start[1]))
    world.body.position = start_position
    world.body.angle = case.start[2]
    start_angle = case.start[2]
    rows: list[dict[str, object]] = []
    max_penetration = max(
        wall_penetration(start_position, start_angle),
        *(circle_penetration(start_position, start_angle, p, 0.05) for p in case.posts),
        0.0,
    )
    max_impulse = 0.0
    max_shaft_body_mismatch = 0.0
    any_cross = False
    any_contact = False
    max_contacts = 0
    previous = start_position
    stuck_steps = 0
    released = False
    for index, command in enumerate(case.commands):
        record = world.advance(command)
        max_penetration = max(max_penetration, record.max_penetration)
        max_impulse = max(max_impulse, record.total_impulse)
        max_shaft_body_mismatch = max(
            max_shaft_body_mismatch, record.body_shaft_mismatch
        )
        any_cross |= record.crossed_wall_or_post
        any_contact |= record.arbiter_count > 0
        max_contacts = max(max_contacts, record.contact_count)
        expected_position, _expected_heading = independent_arc(
            previous, record.start_angle, *record.shaft
        )
        mismatch = math.dist(expected_position, record.end)
        expected_yaw = record.start_angle + (
            0.045 * (record.shaft[1] - record.shaft[0]) / 0.185
        )
        yaw_mismatch = abs(record.end_angle - expected_yaw)
        max_shaft_body_mismatch = max(max_shaft_body_mismatch, mismatch)
        independent_clip = tuple(
            max(-MAX_DELTA, min(MAX_DELTA, x)) for x in record.request
        )
        if any(abs(record.shaft[i] - independent_clip[i]) > 1e-12 for i in range(2)):
            raise RuntimeError("shaft command differs from independent clipping")
        displacement = math.dist(record.start, record.end)
        if displacement < 1e-5 and any_contact:
            stuck_steps += 1
        elif stuck_steps and displacement >= 0.001:
            released = True
        rows.append(
            {
                "index": index,
                "request_rad": list(record.request),
                "shaft_rad": list(record.shaft),
                "position_m": list(record.end),
                "yaw_unwrapped_rad": record.end_angle,
                "velocity_m_s": list(record.velocity),
                "omega_rad_s": record.angular_velocity,
                "impulse_sum": record.total_impulse,
                "contact_points": record.contact_count,
                "arbiters": record.arbiter_count,
                "substep_penetration_m": record.max_penetration,
                "substep_crossing": record.crossed_wall_or_post,
                "free_arc_difference_m": mismatch,
                "free_arc_yaw_difference_rad": yaw_mismatch,
            }
        )
        previous = record.end
    final = rows[-1] if rows else {}
    return {
        "case_id": case.case_id,
        "family": case.family,
        "microsteps": case.microsteps,
        "start": list(case.start),
        "commands": len(case.commands),
        "posts": [list(p) for p in case.posts],
        "steps": rows,
        "final_position_m": final.get("position_m"),
        "final_yaw_rad": final.get("yaw_unwrapped_rad"),
        "elapsed_s": world.elapsed,
        "logical_steps": world.logical_steps,
        "engine_steps": world.engine_steps,
        "max_penetration_m": max_penetration,
        "max_impulse": max_impulse,
        "max_contact_points": max_contacts,
        "any_contact": any_contact,
        "substep_crossing": any_cross,
        "shaft_body_displacement_difference_m": max_shaft_body_mismatch,
        "stuck_steps": stuck_steps,
        "released_after_stuck": released or stuck_steps == 0,
        "start_wall_clearance_m": min(
            min(x for x, _ in corners(start_position, start_angle)),
            min(y for _, y in corners(start_position, start_angle)),
            min(3.0 - x for x, _ in corners(start_position, start_angle)),
            min(3.0 - y for _, y in corners(start_position, start_angle)),
        ),
        "status": "PASS"
        if max_penetration <= 0.001 and not any_cross and (released or stuck_steps == 0)
        else "FAIL",
    }


def _number(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"expected numeric result, got {type(value).__name__}")
    return float(value)


def _coordinate(value: object) -> tuple[float, float]:
    if not isinstance(value, list) or len(value) != 2:
        raise TypeError("expected serialized two-coordinate position")
    return _number(value[0]), _number(value[1])


def run_suite(microsteps: int) -> list[dict[str, object]]:
    # Explicitly serial; each case owns a fresh Space and fixed geometry.
    return [
        _single_case(replace(case, microsteps=microsteps)) for case in fixed_cases()
    ]


def validate_action_and_encoder_contract() -> dict[str, object]:
    invalid: tuple[object, ...] = (
        (),
        (1,),
        (1, 2, 3),
        "12",
        b"12",
        "1",
        True,
        (True, 0),
        ("x", 0),
        (float("nan"), 0),
        (float("inf"), 0),
        (-float("inf"), 0),
    )
    rejected = 0
    world = ContactWorld(microsteps=10)
    before = (
        world.body.position.x,
        world.body.position.y,
        world.body.angle,
        world.elapsed,
        world.engine_steps,
    )
    for action in invalid:
        try:
            world.advance(action)  # type: ignore[arg-type]
        except ValueError:
            rejected += 1
    after = (
        world.body.position.x,
        world.body.position.y,
        world.body.angle,
        world.elapsed,
        world.engine_steps,
    )
    q = ENCODER_QUANTUM
    encoder = tuple(
        quantize_encoder(value)
        for value in (
            math.nextafter(q / 2, 0.0),
            math.nextafter(q / 2, math.inf),
            q / 2,
            math.nextafter(-q / 2, 0.0),
            math.nextafter(-q / 2, -math.inf),
            -q / 2,
        )
    )
    expected = (0.0, q, q, 0.0, -q, -q)
    return {
        "invalid_count": len(invalid),
        "rejected_count": rejected,
        "invalid_no_step": before == after,
        "encoder_values": encoder,
        "encoder_expected": expected,
        "pass": rejected == len(invalid) and before == after and encoder == expected,
        "parse_valid": parse_action((0.0, 0.0)) == (0.0, 0.0),
    }


def _check_clean_frozen_tree() -> str:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    live_main = subprocess.check_output(
        ["git", "rev-parse", "origin/main"], text=True
    ).strip()
    changed_paths = subprocess.check_output(
        ["git", "diff", "--name-only", BASE_SHA, head], text=True
    ).splitlines()
    branch = subprocess.check_output(
        ["git", "branch", "--show-current"], text=True
    ).strip()
    dirty = subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()
    if live_main != BASE_SHA:
        raise RuntimeError("origin/main differs from the authorized base; STOP")
    if not changed_paths or any(
        not path.startswith("experiments/pymunk_contact_prototype/")
        for path in changed_paths
    ):
        raise RuntimeError("frozen diff escapes the isolated experiment namespace")
    if head == BASE_SHA:
        raise RuntimeError(
            "measurements require the committed result-free executable SHA, not base"
        )
    if branch != EXPECTED_BRANCH or dirty:
        raise RuntimeError(
            "measurements require the authorized clean branch and committed source"
        )
    return head


def _runtime_manifest() -> dict[str, object]:
    wheel = os.environ.get("PYMUNK_WHEEL_PATH")
    if not wheel or not Path(wheel).is_file():
        raise RuntimeError("PYMUNK_WHEEL_PATH must name the pinned Pymunk wheel")
    wheel_path = Path(wheel)
    lock = Path("uv.lock")
    manifest: dict[str, object] = {
        "python": sys.version,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "pymunk": pymunk.version,
        "munk": pymunk.chipmunk_version,
        "wheel_path": str(wheel_path.resolve()),
        "wheel_filename": wheel_path.name,
        "wheel_bytes": wheel_path.stat().st_size,
        "wheel_sha256": sha256(wheel_path),
        "uv": subprocess.check_output(["uv", "--version"], text=True).strip(),
        "uv_lock_sha256": sha256(lock),
    }
    if platform.python_version() != "3.14.7" or pymunk.version != "7.2.0":
        raise RuntimeError("runtime version differs from frozen Python/Pymunk contract")
    if (
        manifest["wheel_sha256"]
        != "497c4a919fc7f03882cb9796b132ab3b5fcc4c4af9ead08e9631b6a9fb2da29c"
    ):
        raise RuntimeError("Pymunk wheel hash does not match frozen #220 native wheel")
    return manifest


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def measure(output: Path) -> dict[str, object]:
    executable_sha = _check_clean_frozen_tree()
    runtime = _runtime_manifest()
    measurement_started = time.perf_counter()
    input_contract = validate_action_and_encoder_contract()
    cases10 = run_suite(10)
    cases20 = run_suite(20)
    # Same-source fresh check is one immediate serial replay of the same corpus.
    replay10 = run_suite(10)
    replay20 = run_suite(20)
    first_bytes, replay_bytes = (
        _canonical([cases10, cases20]),
        _canonical([replay10, replay20]),
    )
    replay_equal = first_bytes == replay_bytes
    case_comparisons: list[dict[str, object]] = []
    for c10, c20 in zip(cases10, cases20, strict=True):
        p10 = _coordinate(c10["final_position_m"])
        p20 = _coordinate(c20["final_position_m"])
        position_difference = math.dist(p10, p20)
        yaw_difference = abs(
            _number(c10["final_yaw_rad"]) - _number(c20["final_yaw_rad"])
        )
        case_comparisons.append(
            {
                "case_id": c10["case_id"],
                "position_difference_m": position_difference,
                "yaw_difference_rad": yaw_difference,
                "contact_state_same": c10["any_contact"] == c20["any_contact"],
            }
        )
    all_cases = cases10 + cases20
    calibration = [case for case in all_cases if case["family"] == "calibration"]
    free_position_errors = [
        _number(row["free_arc_difference_m"])
        for case in calibration
        for row in cast(list[dict[str, object]], case["steps"])
    ]
    free_yaw_errors = [
        _number(row["free_arc_yaw_difference_rad"])
        for case in calibration
        for row in cast(list[dict[str, object]], case["steps"])
    ]
    contact_families = {
        "wall-head-on",
        "wall-release",
        "wall-glance",
        "wall-turn",
        "corner",
        "post-head-on",
        "post-tangent",
        "post-sustained",
        "post-release",
        "post-wall-adjacent",
    }
    gates = {
        "runtime_and_pin": platform.python_version() == "3.14.7"
        and pymunk.version == "7.2.0",
        "finite_and_reset_replay": replay_equal
        and all(math.isfinite(_number(c["elapsed_s"])) for c in all_cases),
        "action_shaft_encoder": bool(input_contract["pass"]),
        "logical_time_and_shaft": all(
            c["logical_steps"] == c["commands"]
            and math.isclose(
                _number(c["elapsed_s"]), cast(int, c["commands"]) * 0.1, abs_tol=1e-12
            )
            for c in all_cases
        ),
        "free_space_calibration_position": max(free_position_errors, default=math.inf)
        <= 1e-5,
        "free_space_calibration_yaw": max(free_yaw_errors, default=math.inf) <= 1e-5,
        "contact_penetration": all(
            _number(c["max_penetration_m"]) <= 0.001 for c in all_cases
        ),
        "expected_contacts_observed": all(
            bool(c["any_contact"])
            for c in all_cases
            if str(c["family"]) in contact_families
        ),
        "substep_tunneling": not any(bool(c["substep_crossing"]) for c in all_cases),
        "nonnegative_impulse": all(_number(c["max_impulse"]) >= 0.0 for c in all_cases),
        "stuck_recovery": all(
            bool(c["released_after_stuck"])
            for c in all_cases
            if str(c["family"]).endswith("release")
        ),
        "10_vs_20_position": all(
            _number(c["position_difference_m"]) <= 0.0005 for c in case_comparisons
        ),
        "10_vs_20_yaw": all(
            _number(c["yaw_difference_rad"]) <= 0.001 for c in case_comparisons
        ),
        "reset_case_inventory": len(cases10) == len(fixed_cases())
        and len(cases20) == len(fixed_cases()),
    }
    gates["essential_B"] = all(gates.values())
    measurement_seconds = time.perf_counter() - measurement_started
    result: dict[str, object] = {
        "schema_version": 1,
        "protocol_sha256": sha256(PROTOCOL),
        "base_sha": BASE_SHA,
        "executable_sha": executable_sha,
        "runtime": runtime,
        "selection": (
            "C2_MIDPOINT_ARC_AVERAGE; ex ante numerical-only rationale in protocol"
        ),
        "substeps": {"primary": 10, "comparison": 20},
        "physics_settings": {
            "space_threaded": False,
            "gravity_m_s2": [0.0, 0.0],
            "damping": 1.0,
            "iterations": 10,
            "collision_slop_m": 0.0001,
            "collision_bias": 0.001797010299914434,
            "collision_persistence": 3,
            "sleep_threshold_s": "infinity",
            "idle_speed_threshold": 0.0,
            "friction": 0.0,
            "restitution": 0.0,
            "shaft_delta_limit_rad": MAX_DELTA,
            "logical_dt_s": 0.1,
        },
        "calibration_comparator": {
            "C1_max_position_error_m": 1.4922674449837919e-7,
            "C2_max_position_error_m": 4.4026752318055749e-17,
            "C0_historical_status": (
                "FAIL preserved; 24/92 cases and 3 gates failed; not rerun"
            ),
        },
        "fixture": {
            "body_m": [0.180, 0.215],
            "mass_kg": 1.0,
            "moment_kg_m2": 1.0 * (0.180**2 + 0.215**2) / 12,
            "wall_thickness_m": 0.01,
            "post_radius_m": 0.05,
        },
        "gate_thresholds": {
            "wall_or_post_penetration_max_m": 0.001,
            "free_space_error_m_rad": 1e-5,
            "10_vs_20_position_m": 0.0005,
            "10_vs_20_yaw_rad": 0.001,
            "shaft_error_rad": 1e-12,
        },
        "measurement_wall_seconds": measurement_seconds,
        "input_contract": input_contract,
        "gates": {k: {"status": "PASS" if v else "FAIL"} for k, v in gates.items()},
        "same_source_replay": {
            "byte_identical": replay_equal,
            "trace_sha256": hashlib.sha256(first_bytes).hexdigest(),
            "replay_sha256": hashlib.sha256(replay_bytes).hexdigest(),
        },
        "free_space_calibration_max_position_error_m": max(
            free_position_errors, default=math.inf
        ),
        "free_space_calibration_max_yaw_error_rad": max(
            free_yaw_errors, default=math.inf
        ),
        "10_vs_20_comparisons": case_comparisons,
        "cases_10_substeps": cases10,
        "cases_20_substeps": cases20,
        "essential_B_pass": bool(gates["essential_B"]),
        "lifetime_authorized_to_run": False,
    }
    output.mkdir(parents=True, exist_ok=False)
    json_path = output / "results.json"
    json_path.write_bytes(_canonical(result) + b"\n")
    text = [
        "# Pymunk fixed-command contact diagnostics",
        "",
        f"Executable SHA: `{executable_sha}`",
        "",
        f"Essential B: **{'PASS' if result['essential_B_pass'] else 'FAIL'}**",
        "",
        "| Gate | Result |",
        "|---|---|",
    ]
    text.extend(
        f"| {name} | {'PASS' if passed else 'FAIL'} |" for name, passed in gates.items()
    )
    text.extend(
        [
            "",
            "No organism lifetime is run by this diagnostic command.",
            "No production physics adoption or hardware-fidelity claim is made.",
        ]
    )
    md_path = output / "RESULTS.md"
    md_path.write_text("\n".join(text) + "\n", encoding="utf-8")
    sums = f"{sha256(json_path)}  results.json\n{sha256(md_path)}  RESULTS.md\n"
    (output / "SHA256SUMS").write_text(sums, encoding="ascii")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--measure",
        action="store_true",
        help="run the frozen cases once plus same-source replay",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.measure:
        parser.error("explicit --measure is required; tests never run measurements")
    result = measure(args.output)
    print(
        json.dumps(
            {
                "essential_B_pass": result["essential_B_pass"],
                "output": str(args.output),
            },
            sort_keys=True,
        )
    )
    if not result["essential_B_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
