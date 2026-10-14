"""One bounded, serial v2 contact check plus one fresh-process replay."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import cast

from .fixture import COLLISION_BIAS_10MS, MAX_DELTA
from .run_diagnostics import (
    BASE_SHA,
    EXPECTED_BRANCH,
    EXPECTED_OUTPUT,
    PROTOCOL,
    _canonical,
    _number,
    _runtime_manifest,
    sha256,
    validate_action_and_encoder_contract,
)

REPLAY_PATH = EXPECTED_OUTPUT / "fresh-process-replay.json"
CONTACT_FAMILIES = {
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


def check_frozen_tree(*, allow_output: bool = False) -> str:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    main = subprocess.check_output(
        ["git", "rev-parse", "origin/main"], text=True
    ).strip()
    branch = subprocess.check_output(
        ["git", "branch", "--show-current"], text=True
    ).strip()
    changed = subprocess.check_output(
        ["git", "diff", "--name-only", BASE_SHA, head], text=True
    ).splitlines()
    dirty = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=all"], text=True
    ).splitlines()
    output_prefix = EXPECTED_OUTPUT.as_posix() + "/"
    unexpected = [
        line
        for line in dirty
        if not (
            allow_output
            and line.startswith("?? ")
            and line[3:].startswith(output_prefix)
        )
    ]
    if main != BASE_SHA:
        raise RuntimeError("origin/main differs from the authorized v2 base")
    if branch != EXPECTED_BRANCH or head == BASE_SHA or unexpected:
        raise RuntimeError("v2 measurement requires its exact clean branch/source")
    if not changed or any(
        not path.startswith("experiments/pymunk_contact_prototype/")
        for path in changed
    ):
        raise RuntimeError("v2 frozen diff escapes the optional experiment namespace")
    return head


def preflight_output(output: Path) -> None:
    if output.resolve() != EXPECTED_OUTPUT.resolve():
        raise RuntimeError(f"v2 output must be the new path {EXPECTED_OUTPUT}")
    if output.exists():
        raise FileExistsError(
            f"v2 output already exists; refusing before stepping: {output}"
        )


def _finite_values(value: object) -> bool:
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(_finite_values(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return all(_finite_values(item) for item in value)
    return True


def _json_safe(value: object) -> object:
    if isinstance(value, float) and not math.isfinite(value):
        return "NaN" if math.isnan(value) else "Infinity" if value > 0 else "-Infinity"
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _safe_canonical(value: object) -> bytes:
    return _canonical(_json_safe(value))


def _case_contact_ids(case: dict[str, object], step_index: int) -> set[str]:
    steps = cast(list[dict[str, object]], case["steps"])
    return set(cast(list[str], steps[step_index]["contact_identities"]))


def _step_clearance(case: dict[str, object], step_index: int) -> dict[str, float]:
    steps = cast(list[dict[str, object]], case["steps"])
    raw = cast(
        dict[str, object],
        steps[step_index]["minimum_trajectory_clearance_by_shape_m"],
    )
    return {name: _number(value) for name, value in raw.items()}


def _contact_state_comparisons(
    cases10: list[dict[str, object]], cases20: list[dict[str, object]]
) -> tuple[list[dict[str, object]], bool]:
    comparisons: list[dict[str, object]] = []
    passed = True
    for c10, c20 in zip(cases10, cases20, strict=True):
        steps10 = cast(list[dict[str, object]], c10["steps"])
        steps20 = cast(list[dict[str, object]], c20["steps"])
        # Compare the per-case minimum against every named fixed shape.
        case_min10 = {
            str(name): _number(value)
            for name, value in cast(
                dict[str, object],
                c10["minimum_trajectory_clearance_by_shape_m"],
            ).items()
        }
        case_min20 = {
            str(name): _number(value)
            for name, value in cast(
                dict[str, object],
                c20["minimum_trajectory_clearance_by_shape_m"],
            ).items()
        }
        clearance_differences = {
            name: abs(case_min10[name] - case_min20[name])
            for name in sorted(case_min10.keys() | case_min20.keys())
            if name in case_min10 and name in case_min20
        }
        clearance_pass = (
            case_min10.keys() == case_min20.keys()
            and all(value <= 0.0005 for value in clearance_differences.values())
        )
        passed &= clearance_pass
        disagreements: list[dict[str, object]] = []
        for index, _ in enumerate(zip(steps10, steps20, strict=True)):
            ids10, ids20 = _case_contact_ids(c10, index), _case_contact_ids(c20, index)
            if ids10 == ids20:
                continue
            clearances10 = _step_clearance(c10, index)
            clearances20 = _step_clearance(c20, index)
            affected_shapes = {
                part
                for pair in ids10.symmetric_difference(ids20)
                for part in pair.split("|")
                if part != "hull"
            }
            nearest_candidates = [
                abs(clearances[name])
                for clearances in (clearances10, clearances20)
                for name in affected_shapes
                if name in clearances
            ]
            nearest = min(nearest_candidates, default=None)
            within_boundary_tolerance = (
                nearest is not None and nearest <= 0.0005
            )
            passed &= within_boundary_tolerance
            disagreements.append(
                {
                    "step": index,
                    "contact_ids_10": sorted(ids10),
                    "contact_ids_20": sorted(ids20),
                    "nearest_independent_clearance_m": nearest,
                    "within_0.5mm_boundary_tolerance": within_boundary_tolerance,
                }
            )
        comparisons.append(
            {
                "case_id": c10["case_id"],
                "position_difference_m": math.dist(
                    tuple(cast(list[float], c10["final_position_m"])),
                    tuple(cast(list[float], c20["final_position_m"])),
                ),
                "yaw_difference_rad": abs(
                    _number(c10["final_yaw_rad"]) - _number(c20["final_yaw_rad"])
                ),
                "per_shape_minimum_clearance_difference_m": clearance_differences,
                "per_shape_clearance_pass": clearance_pass,
                "contact_state_disagreements": disagreements,
                "contact_state_pass": all(
                    bool(item["within_0.5mm_boundary_tolerance"])
                    for item in disagreements
                ),
            }
        )
    return comparisons, passed


def _trace_bytes(
    cases10: list[dict[str, object]], cases20: list[dict[str, object]]
) -> bytes:
    return _safe_canonical(
        {"cases_10_substeps": cases10, "cases_20_substeps": cases20}
    )


def replay_worker(output: Path, expected_head: str) -> dict[str, object]:
    if output.resolve() != REPLAY_PATH.resolve():
        raise RuntimeError(f"fresh replay path must be {REPLAY_PATH}")
    if output.exists():
        raise FileExistsError(
            "fresh-process replay output exists; refusing before stepping"
        )
    marker = EXPECTED_OUTPUT / "MEASUREMENT_STARTED"
    if not marker.is_file():
        raise RuntimeError("fresh replay is only allowed inside an active primary run")
    marker_text = marker.read_text(encoding="ascii")
    if (
        f"head={expected_head}\n" not in marker_text
        or "completed=1" in marker_text
    ):
        raise RuntimeError(
            "fresh replay marker/source mismatch or primary already complete"
        )
    head = check_frozen_tree(allow_output=True)
    if head != expected_head:
        raise RuntimeError("fresh-process replay source SHA differs from primary")
    _runtime_manifest()
    # The frozen suite runner replaces only the microstep count per full corpus.
    from .run_diagnostics import run_suite

    cases10 = run_suite(10)
    cases20 = run_suite(20)
    payload = _trace_bytes(cases10, cases20)
    output.write_bytes(payload)
    return {
        "process_id": os.getpid(),
        "executable_sha": head,
        "trace_sha256": hashlib.sha256(payload).hexdigest(),
        "case_count_per_resolution": [len(cases10), len(cases20)],
    }


def measure(output: Path) -> dict[str, object]:
    # This refusal is intentionally first: no Space construction or stepping.
    preflight_output(output)
    head = check_frozen_tree()
    runtime = _runtime_manifest()
    output.mkdir(parents=True, exist_ok=False)
    (output / "MEASUREMENT_STARTED").write_text(f"head={head}\n", encoding="ascii")
    started = time.perf_counter()
    input_contract = validate_action_and_encoder_contract()
    from .run_diagnostics import run_suite

    cases10 = run_suite(10)
    cases20 = run_suite(20)
    primary_bytes = _trace_bytes(cases10, cases20)
    replay_proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "experiments.pymunk_contact_prototype.run_corrected_contact_check",
            "--replay-worker",
            "--output",
            str(REPLAY_PATH),
            "--expected-head",
            head,
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=600,
    )
    replay_meta = cast(dict[str, object], json.loads(replay_proc.stdout))
    replay_bytes = REPLAY_PATH.read_bytes()
    replay_equal = primary_bytes == replay_bytes
    comparisons, contact_state_pass = _contact_state_comparisons(cases10, cases20)
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
    command_counts = [cast(int, case["commands"]) for case in cases10]
    case_counts = [len(cases10), len(cases20)]
    gates: dict[str, bool] = {
        "runtime_and_pin": runtime["python_version"] == "3.14.7"
        and runtime["pymunk"] == "7.2.0"
        and runtime["wheel_sha256"]
        == "497c4a919fc7f03882cb9796b132ab3b5fcc4c4af9ead08e9631b6a9fb2da29c",
        "action_shaft_encoder": bool(input_contract["pass"]),
        "logical_time_and_shaft": all(
            case["logical_steps"] == case["commands"]
            and math.isclose(
                _number(case["elapsed_s"]),
                cast(int, case["commands"]) * 0.1,
                abs_tol=1e-12,
            )
            and case["engine_steps"]
            == cast(int, case["commands"]) * cast(int, case["microsteps"])
            for case in all_cases
        ),
        "free_space_calibration_position": max(free_position_errors, default=math.inf)
        <= 1e-5,
        "free_space_calibration_yaw": max(free_yaw_errors, default=math.inf) <= 1e-5,
        "contact_penetration": all(
            _number(case["max_penetration_m"]) <= 0.001 for case in all_cases
        ),
        "trajectory_clearance_sampling_bound": all(
            _number(case["max_clearance_sampling_bound_m"]) <= 0.0002
            for case in all_cases
        ),
        "expected_contacts_observed": all(
            any(str(case["family"]) == family for case in all_cases)
            and all(
                bool(case["any_contact"])
                for case in all_cases
                if str(case["family"]) == family
            )
            for family in CONTACT_FAMILIES
        ),
        "substep_tunneling": not any(
            bool(case["substep_crossing"]) for case in all_cases
        ),
        "contact_identity_complete": all(
            all(
                pair != "unknown|hull" and "unknown" not in pair
                for row in cast(list[dict[str, object]], case["steps"])
                for pair in cast(list[str], row["contact_identities"])
            )
            for case in all_cases
        ),
        "nonnegative_impulse": all(
            _number(case["max_impulse"]) >= 0.0 for case in all_cases
        ),
        "stuck_recovery": all(
            bool(case["released_after_stuck"])
            for case in all_cases
            if str(case["family"]).endswith("release")
        ),
        "10_vs_20_position": all(
            _number(case["position_difference_m"]) <= 0.0005
            for case in comparisons
        ),
        "10_vs_20_per_shape_clearance": all(
            bool(case["per_shape_clearance_pass"]) for case in comparisons
        ),
        "10_vs_20_yaw": all(
            _number(case["yaw_difference_rad"]) <= 0.001 for case in comparisons
        ),
        "contact_state_convergence": contact_state_pass,
        "reset_and_inventory": case_counts == [255, 255]
        and all(bool(case["reset_pass"]) for case in all_cases),
        "fresh_process_replay": replay_equal
        and cast(int, replay_meta["process_id"]) != os.getpid()
        and replay_meta["executable_sha"] == head,
        "finite_outputs": _finite_values(
            {"cases": all_cases, "comparisons": comparisons, "input": input_contract}
        ),
    }
    gates["essential_B"] = all(gates.values())
    primary_sha = hashlib.sha256(primary_bytes).hexdigest()
    replay_sha = hashlib.sha256(replay_bytes).hexdigest()
    elapsed = time.perf_counter() - started
    result: dict[str, object] = {
        "schema_version": 2,
        "protocol_sha256": sha256(PROTOCOL),
        "base_sha": BASE_SHA,
        "executable_sha": head,
        "runtime": runtime,
        "selection": (
            "C2 midpoint arc-average; numerical-only basis inherited from v1/#220"
        ),
        "substeps": {"primary": 10, "comparison": 20},
        "actuator_contact_response": (
            "solver-modified velocity persists after first contact callback "
            "within a logical step"
        ),
        "physics_settings": {
            "space_threaded": False,
            "gravity_m_s2": [0.0, 0.0],
            "damping": 1.0,
            "iterations": 10,
            "collision_slop_m": 0.0001,
            "collision_bias": COLLISION_BIAS_10MS,
            "collision_persistence": 3,
            "sleep_threshold_s": "infinity",
            "idle_speed_threshold": 0.0,
            "friction": 0.0,
            "restitution": 0.0,
            "shaft_delta_limit_rad": MAX_DELTA,
            "logical_dt_s": 0.1,
        },
        "fixture": {
            "body_m": [0.180, 0.215],
            "mass_kg": 1.0,
            "moment_kg_m2": (0.180**2 + 0.215**2) / 12.0,
            "wall_thickness_m": 0.01,
            "wall_inner_faces_m": [0.0, 3.0],
            "post_radius_m": 0.05,
        },
        "case_inventory": {
            "case_count_per_resolution": case_counts,
            "logical_commands_per_resolution": command_counts,
            "logical_commands_total_including_replay": 4 * sum(command_counts),
            "engine_steps_total_including_replay": 2
            * sum(
                cast(int, case["commands"]) * cast(int, case["microsteps"])
                for case in cases10 + cases20
            ),
        },
        "gate_thresholds": {
            "penetration_max_m": 0.001,
            "clearance_sample_path_bound_max_m": 0.0002,
            "free_space_error_m_rad": 1e-5,
            "10_vs_20_position_m": 0.0005,
            "10_vs_20_per_shape_clearance_difference_m": 0.0005,
            "10_vs_20_yaw_rad": 0.001,
            "contact_state_clearance_tolerance_m": 0.0005,
            "shaft_error_rad": 1e-12,
        },
        "measurement_wall_seconds": elapsed,
        "input_contract": input_contract,
        "gates": {
            name: {"status": "PASS" if passed else "FAIL"}
            for name, passed in gates.items()
        },
        "fresh_process_replay": {
            "byte_identical": replay_equal,
            "primary_process_id": os.getpid(),
            "replay_process_id": replay_meta["process_id"],
            "primary_sha256": primary_sha,
            "replay_sha256": replay_sha,
        },
        "free_space_calibration_max_position_error_m": max(
            free_position_errors, default=math.inf
        ),
        "free_space_calibration_max_yaw_error_rad": max(
            free_yaw_errors, default=math.inf
        ),
        "10_vs_20_comparisons": comparisons,
        "cases_10_substeps": cases10,
        "cases_20_substeps": cases20,
        "essential_B_pass": gates["essential_B"],
        "lifetime_authorized_to_run": False,
    }
    json_path = output / "results.json"
    json_path.write_bytes(_safe_canonical(result) + b"\n")
    summary = [
        "# Corrected Pymunk fixed-command contact check",
        "",
        f"Executable SHA: `{head}`",
        f"Protocol SHA-256: `{result['protocol_sha256']}`",
        "",
        f"Essential B: **{'PASS' if gates['essential_B'] else 'FAIL'}**",
        "",
        "| Gate | Result |",
        "|---|---|",
        *(
            f"| {name} | {'PASS' if passed else 'FAIL'} |"
            for name, passed in gates.items()
        ),
        "",
        "No lifetime ran in the fixed-command diagnostic runner.",
        "No production physics or hardware-fidelity claim is made.",
    ]
    report = output / "RESULTS.md"
    report.write_text("\n".join(summary) + "\n", encoding="utf-8")
    (output / "MEASUREMENT_STARTED").write_text(
        f"head={head}\ncompleted=1\n", encoding="ascii"
    )
    (output / "SHA256SUMS").write_text(
        f"{sha256(json_path)}  results.json\n{sha256(report)}  RESULTS.md\n"
        f"{replay_sha}  fresh-process-replay.json\n",
        encoding="ascii",
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--measure", action="store_true")
    mode.add_argument("--replay-worker", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-head")
    args = parser.parse_args()
    if args.replay_worker:
        if not args.expected_head:
            parser.error("--expected-head is required for the fresh replay worker")
        metadata = replay_worker(args.output, args.expected_head)
        print(json.dumps(metadata, sort_keys=True))
        return
    if args.expected_head:
        parser.error("--expected-head is only valid for the replay worker")
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
