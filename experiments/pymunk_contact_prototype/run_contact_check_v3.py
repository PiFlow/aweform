"""One predeclared v3 focused falsifier or full fixed-command contact check."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import cast

from .cases import Case, fixed_cases
from .fixture import COLLISION_BIAS_10MS
from .run_diagnostics import (
    _canonical,
    _number,
    _runtime_manifest,
    _single_case,
    sha256,
    validate_action_and_encoder_contract,
)

BASE_SHA = "abba4b8bb568ba13ccc5cc87740b87c6c2630ada"
EXPECTED_BRANCH = "fm/pymunk226-contact-prototype"
PRIMARY = 400
FINE = 800
PROTOCOL = Path(__file__).with_name("protocol-v3.md")
FOCUSED_OUTPUT = Path(
    "experiments/pymunk_contact_prototype/results-v3/focused-probe"
)
EXPECTED_OUTPUT = Path(
    "experiments/pymunk_contact_prototype/results-v3/contact-check"
)
FULL_ENGINE_STEPS = 1_912_800
FOCUSED_ENGINE_STEPS = 132_000
CASE_RUNTIME_RESERVE_S = 10.0
FOCUSED_CASE_IDS = (
    "wall-west-head-on",
    "wall-west-turn-0",
    "wall-south-turn-0",
    "wall-south-glance",
    "corner-se",
    "post-wall-adjacent",
    "post-tangent",
)
EXPECTED_NO_CONTACT = frozenset(
    {
        "wall-west-turn-2",
        "wall-east-turn-2",
        "wall-south-turn-2",
        "wall-north-turn-2",
    }
)
CONTACT_FAMILIES = frozenset(
    {
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
)


class BudgetExceeded(RuntimeError):
    """A frozen wall-clock cap expired between complete cases."""


def check_frozen_tree(*, allow_outputs: tuple[Path, ...] = ()) -> str:
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
    prefixes = tuple(f"{path.as_posix()}/" for path in allow_outputs)
    unexpected = [
        line
        for line in dirty
        if not (
            line.startswith("?? ")
            and any(line[3:].startswith(prefix) for prefix in prefixes)
        )
    ]
    if main != BASE_SHA:
        raise RuntimeError("origin/main differs from the accepted v3 base")
    if branch != EXPECTED_BRANCH or head == BASE_SHA or unexpected:
        raise RuntimeError("v3 check requires the exact clean frozen branch/source")
    if not changed or any(
        not path.startswith("experiments/pymunk_contact_prototype/")
        for path in changed
    ):
        raise RuntimeError("v3 frozen diff escapes the optional experiment namespace")
    return head


def preflight_output(output: Path, expected: Path) -> None:
    if output.resolve() != expected.resolve():
        raise RuntimeError(f"v3 output must be exactly {expected}")
    if output.exists():
        raise FileExistsError(
            f"one-shot v3 output exists; refuse before stepping: {output}"
        )


def planned_engine_steps(cases: tuple[Case, ...], resolutions: tuple[int, ...]) -> int:
    logical_commands = sum(len(case.commands) for case in cases)
    return logical_commands * sum(resolutions)


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


def _write_json(path: Path, value: object) -> None:
    path.write_bytes(_safe_canonical(value) + b"\n")


def expected_contacts_pass(
    cases: list[dict[str, object]], *, require_no_contact_controls: bool
) -> bool:
    by_id = {str(case["case_id"]): case for case in cases}
    if require_no_contact_controls and not EXPECTED_NO_CONTACT <= by_id.keys():
        return False
    for case in cases:
        case_id = str(case["case_id"])
        if case_id in EXPECTED_NO_CONTACT:
            if bool(case["any_contact"]) or _number(
                case["minimum_trajectory_clearance_m"]
            ) <= 0.0:
                return False
        elif str(case["family"]) in CONTACT_FAMILIES and not bool(
            case["any_contact"]
        ):
            return False
    if require_no_contact_controls:
        return all(
            str(by_id[case_id]["family"]) == "wall-turn"
            and not bool(by_id[case_id]["any_contact"])
            and _number(by_id[case_id]["minimum_trajectory_clearance_m"]) > 0.0
            for case_id in EXPECTED_NO_CONTACT
        )
    return True


def _step_contacts(case: dict[str, object], index: int) -> set[str]:
    steps = cast(list[dict[str, object]], case["steps"])
    return set(cast(list[str], steps[index]["contact_identities"]))


def _step_clearances(case: dict[str, object], index: int) -> dict[str, float]:
    steps = cast(list[dict[str, object]], case["steps"])
    raw = cast(
        dict[str, object],
        steps[index]["minimum_trajectory_clearance_by_shape_m"],
    )
    return {str(name): _number(value) for name, value in raw.items()}


def compare_resolutions(
    primary: list[dict[str, object]], fine: list[dict[str, object]]
) -> tuple[list[dict[str, object]], bool, bool]:
    """Return comparisons plus independent contact-state and clearance aggregates."""
    comparisons: list[dict[str, object]] = []
    contact_state_pass = True
    per_shape_clearance_pass = True
    for case_primary, case_fine in zip(primary, fine, strict=True):
        if case_primary["case_id"] != case_fine["case_id"]:
            raise RuntimeError("400/800 case identities or order differ")
        steps_primary = cast(list[dict[str, object]], case_primary["steps"])
        steps_fine = cast(list[dict[str, object]], case_fine["steps"])
        mins_primary = {
            str(name): _number(value)
            for name, value in cast(
                dict[str, object],
                case_primary["minimum_trajectory_clearance_by_shape_m"],
            ).items()
        }
        mins_fine = {
            str(name): _number(value)
            for name, value in cast(
                dict[str, object],
                case_fine["minimum_trajectory_clearance_by_shape_m"],
            ).items()
        }
        clearance_differences = {
            name: abs(mins_primary[name] - mins_fine[name])
            for name in sorted(mins_primary.keys() | mins_fine.keys())
            if name in mins_primary and name in mins_fine
        }
        clearance_case_pass = (
            mins_primary.keys() == mins_fine.keys()
            and all(delta <= 0.0005 for delta in clearance_differences.values())
        )
        per_shape_clearance_pass &= clearance_case_pass
        contact_disagreements: list[dict[str, object]] = []
        for index, _pair in enumerate(
            zip(steps_primary, steps_fine, strict=True)
        ):
            identities_primary = _step_contacts(case_primary, index)
            identities_fine = _step_contacts(case_fine, index)
            if identities_primary == identities_fine:
                continue
            affected_shapes = {
                shape
                for identity in identities_primary.symmetric_difference(
                    identities_fine
                )
                for shape in identity.split("|")
                if shape != "hull"
            }
            near_values = [
                abs(clearance[shape])
                for clearance in (
                    _step_clearances(case_primary, index),
                    _step_clearances(case_fine, index),
                )
                for shape in affected_shapes
                if shape in clearance
            ]
            nearest = min(near_values, default=None)
            allowed = nearest is not None and nearest <= 0.0005
            contact_state_pass &= allowed
            contact_disagreements.append(
                {
                    "logical_step": index,
                    "contact_identities_400": sorted(identities_primary),
                    "contact_identities_800": sorted(identities_fine),
                    "nearest_independent_clearance_m": nearest,
                    "allowed_boundary_disagreement": allowed,
                }
            )
        comparisons.append(
            {
                "case_id": case_primary["case_id"],
                "position_difference_m": math.dist(
                    tuple(cast(list[float], case_primary["final_position_m"])),
                    tuple(cast(list[float], case_fine["final_position_m"])),
                ),
                "yaw_difference_rad": abs(
                    _number(case_primary["final_yaw_rad"])
                    - _number(case_fine["final_yaw_rad"])
                ),
                "per_shape_minimum_clearance_difference_m": clearance_differences,
                "per_shape_clearance_pass": clearance_case_pass,
                "contact_state_disagreements": contact_disagreements,
                "contact_state_pass": all(
                    bool(row["allowed_boundary_disagreement"])
                    for row in contact_disagreements
                ),
            }
        )
    return comparisons, contact_state_pass, per_shape_clearance_pass


def _case_records(
    cases: tuple[Case, ...],
    microsteps: int,
    *,
    output: Path,
    progress_name: str,
    deadline: float,
) -> list[dict[str, object]]:
    """Use unchanged _single_case physics one case at a time to enforce the cap."""
    result: list[dict[str, object]] = []
    progress = output / progress_name
    with progress.open("xb") as stream:
        for index, case in enumerate(cases):
            if deadline - time.monotonic() < CASE_RUNTIME_RESERVE_S:
                raise BudgetExceeded(
                    f"insufficient cap reserve before case {index + 1}/"
                    f"{len(cases)} at {microsteps}"
                )
            record = _single_case(replace(case, microsteps=microsteps))
            encoded = _safe_canonical(record) + b"\n"
            stream.write(encoded)
            stream.flush()
            result.append(record)
            if time.monotonic() >= deadline:
                raise BudgetExceeded(
                    f"time cap reached after case {index + 1}/{len(cases)} "
                    f"at {microsteps}"
                )
    return result


def _planned_primary_cases(cases: tuple[Case, ...]) -> int:
    return planned_engine_steps(cases, (PRIMARY, FINE))


def _sampled_penetration(case: dict[str, object], command_index: int) -> float:
    steps = cast(list[dict[str, object]], case["steps"])
    return _number(steps[command_index]["sampled_trajectory_penetration_m"])


def _runtime_pass(runtime: dict[str, object]) -> bool:
    return (
        runtime.get("python_version") == "3.14.7"
        and runtime.get("pymunk") == "7.2.0"
        and runtime.get("wheel_sha256")
        == "497c4a919fc7f03882cb9796b132ab3b5fcc4c4af9ead08e9631b6a9fb2da29c"
    )


def _case_gate_status(cases: list[dict[str, object]]) -> dict[str, bool]:
    return {
        "case_penetration": all(
            _number(case["max_penetration_m"]) <= 0.001 for case in cases
        ),
        "clearance_sampling_bound": all(
            _number(case["max_clearance_sampling_bound_m"]) <= 0.0002
            for case in cases
        ),
        "no_swept_crossing": not any(bool(case["substep_crossing"]) for case in cases),
        "reset": all(bool(case["reset_pass"]) for case in cases),
        "stuck_release": all(
            bool(case["released_after_stuck"])
            for case in cases
            if str(case["family"]).endswith("release")
        ),
        "contact_identity_complete": all(
            "unknown" not in identity
            for case in cases
            for step in cast(list[dict[str, object]], case["steps"])
            for identity in cast(list[str], step["contact_identities"])
        ),
        "nonnegative_impulse": all(
            _number(case["max_impulse"]) >= 0.0 for case in cases
        ),
        "finite_outputs": _finite_values(cases),
    }


def _comparison_gates(
    comparisons: list[dict[str, object]],
    contact_state_pass: bool,
    per_shape_clearance_pass: bool,
) -> dict[str, bool]:
    return {
        "position_convergence": all(
            _number(item["position_difference_m"]) <= 0.0005
            for item in comparisons
        ),
        "yaw_convergence": all(
            _number(item["yaw_difference_rad"]) <= 0.001
            for item in comparisons
        ),
        "per_shape_clearance_convergence": per_shape_clearance_pass
        and all(bool(item["per_shape_clearance_pass"]) for item in comparisons),
        "contact_state_convergence": contact_state_pass
        and all(bool(item["contact_state_pass"]) for item in comparisons),
    }


def _mark_incomplete(output: Path, head: str, reason: str, elapsed: float) -> None:
    marker = output / "FAILED-INCOMPLETE"
    marker.write_text(
        f"head={head}\nreason={reason}\nelapsed_s={elapsed:.6f}\n",
        encoding="utf-8",
    )
    (output / "RUN_STATUS.md").write_text(
        "# v3 run incomplete\n\n"
        "The frozen wall-clock cap or a runner error stopped this one-shot run. "
        "Partial progress files are preserved; do not rerun this output path.\n\n"
        f"Reason: `{reason}`\n",
        encoding="utf-8",
    )
    _write_hash_manifest(output)


def _write_hash_manifest(output: Path) -> None:
    manifest = output / "SHA256SUMS"
    files = sorted(
        path
        for path in output.iterdir()
        if path.is_file() and path.name not in {"SHA256SUMS", "MEASUREMENT_STARTED"}
    )
    lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}"
        for path in files
    ]
    started = output / "MEASUREMENT_STARTED"
    if started.is_file():
        lines.append(f"{sha256(started)}  MEASUREMENT_STARTED")
    manifest.write_text("\n".join(lines) + "\n", encoding="ascii")


def _write_summary(
    output: Path,
    *,
    title: str,
    head: str,
    gates: dict[str, bool],
    elapsed: float,
    status_label: str = "Essential B",
) -> None:
    lines = [
        f"# {title}",
        "",
        f"Executable SHA: `{head}`",
        f"Protocol SHA-256: `{sha256(PROTOCOL)}`",
        f"Measured wall time: {elapsed:.6f} s",
        "",
        f"{status_label}: **{'PASS' if all(gates.values()) else 'FAIL'}**",
        "",
        "| Gate | Result |",
        "|---|---|",
        *(
            f"| {name} | {'PASS' if passed else 'FAIL'} |"
            for name, passed in gates.items()
        ),
    ]
    (output / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _gates_for_results(
    primary: list[dict[str, object]],
    fine: list[dict[str, object]],
    comparisons: list[dict[str, object]],
    contact_state_pass: bool,
    clearance_pass: bool,
    runtime: dict[str, object],
    action_contract: dict[str, object],
    replay_ok: bool | None,
    actual_engine_steps: int,
) -> dict[str, bool]:
    all_cases = primary + fine
    case_counts_ok = (
        len(primary) == len(fine) == 255
        and sum(cast(int, case["commands"]) for case in primary) == 797
        and sum(cast(int, case["commands"]) for case in fine) == 797
        and all(
            cast(int, case["engine_steps"])
            == cast(int, case["commands"]) * cast(int, case["microsteps"])
            for case in all_cases
        )
    )
    calibration = [case for case in all_cases if case["family"] == "calibration"]
    free_position = [
        _number(step["free_arc_difference_m"])
        for case in calibration
        for step in cast(list[dict[str, object]], case["steps"])
    ]
    free_yaw = [
        _number(step["free_arc_yaw_difference_rad"])
        for case in calibration
        for step in cast(list[dict[str, object]], case["steps"])
    ]
    gates = {
        "runtime_and_pin": _runtime_pass(runtime),
        "action_shaft_encoder": bool(action_contract.get("pass")),
        "case_inventory_and_engine_steps": case_counts_ok
        and actual_engine_steps == FULL_ENGINE_STEPS,
        "logical_time": all(
            cast(int, case["logical_steps"]) == cast(int, case["commands"])
            and math.isclose(
                _number(case["elapsed_s"]),
                cast(int, case["commands"]) * 0.1,
                abs_tol=1e-12,
            )
            for case in all_cases
        ),
        "free_space_calibration_position": max(free_position, default=math.inf)
        <= 1e-5,
        "free_space_calibration_yaw": max(free_yaw, default=math.inf) <= 1e-5,
    }
    gates.update(_case_gate_status(all_cases))
    gates["expected_contacts_L1"] = expected_contacts_pass(
        all_cases, require_no_contact_controls=True
    )
    gates.update(
        _comparison_gates(comparisons, contact_state_pass, clearance_pass)
    )
    gates["fresh_process_replay"] = replay_ok is True
    gates["finite_outputs"] &= _finite_values(
        {"comparisons": comparisons, "runtime": runtime, "action": action_contract}
    )
    gates["essential_B"] = all(gates.values())
    return gates


def _run_suite_capped(
    cases: tuple[Case, ...],
    microsteps: int,
    *,
    output: Path,
    progress_name: str,
    deadline: float,
) -> list[dict[str, object]]:
    expected_steps = sum(len(case.commands) for case in cases) * microsteps
    records = _case_records(
        cases,
        microsteps,
        output=output,
        progress_name=progress_name,
        deadline=deadline,
    )
    actual_steps = sum(cast(int, case["engine_steps"]) for case in records)
    if actual_steps != expected_steps:
        raise RuntimeError(
            "resolution step count mismatch: "
            f"expected {expected_steps}, got {actual_steps}"
        )
    return records


def run_focused(output: Path) -> dict[str, object]:
    preflight_output(output, FOCUSED_OUTPUT)
    cases_all = fixed_cases()
    by_id = {case.case_id: case for case in cases_all}
    if not set(FOCUSED_CASE_IDS) <= by_id.keys():
        raise RuntimeError("frozen focused case IDs are missing")
    cases = tuple(by_id[case_id] for case_id in FOCUSED_CASE_IDS)
    planned = planned_engine_steps(cases, (PRIMARY, FINE))
    if planned != FOCUSED_ENGINE_STEPS:
        raise RuntimeError(
            "focused pre-step budget mismatch: "
            f"expected {FOCUSED_ENGINE_STEPS}, got {planned}"
        )
    head = check_frozen_tree()
    runtime = _runtime_manifest()
    output.mkdir(parents=True, exist_ok=False)
    (output / "MEASUREMENT_STARTED").write_text(
        f"head={head}\nmode=focused-probe\nplanned_engine_steps={planned}\n",
        encoding="ascii",
    )
    started = time.monotonic()
    deadline = started + 180.0
    try:
        action_contract = validate_action_and_encoder_contract()
        primary = _run_suite_capped(
            cases,
            PRIMARY,
            output=output,
            progress_name="primary-progress.jsonl",
            deadline=deadline,
        )
        fine = _run_suite_capped(
            cases,
            FINE,
            output=output,
            progress_name="fine-progress.jsonl",
            deadline=deadline,
        )
        if time.monotonic() >= deadline:
            raise BudgetExceeded("3-minute focused-probe cap reached")
        comparisons, contact_state_pass, clearance_pass = compare_resolutions(
            primary, fine
        )
        case_gates = _case_gate_status(primary + fine)
        comparisons_gates = _comparison_gates(
            comparisons, contact_state_pass, clearance_pass
        )
        gates = {
            **case_gates,
            **comparisons_gates,
            "expected_contacts_L1": expected_contacts_pass(
                primary + fine, require_no_contact_controls=False
            ),
            "action_shaft_encoder": bool(action_contract.get("pass")),
            "runtime_and_pin": _runtime_pass(runtime),
            "focused_case_inventory": len(primary) == len(fine) == 7
            and all(
                sum(cast(int, case["commands"]) for case in suite) == 110
                for suite in (primary, fine)
            ),
            "logical_time_and_step_count": all(
                cast(int, case["logical_steps"]) == cast(int, case["commands"])
                and cast(int, case["engine_steps"])
                == cast(int, case["commands"]) * cast(int, case["microsteps"])
                and math.isclose(
                    _number(case["elapsed_s"]),
                    cast(int, case["commands"]) * 0.1,
                    abs_tol=1e-12,
                )
                for case in primary + fine
            ),
            "head_on_falsifier_400": abs(
                _sampled_penetration(primary[0], 18) - 0.0002115
            )
            <= 0.0002115 * 0.10,
            "head_on_falsifier_800": abs(
                _sampled_penetration(fine[0], 18) - 0.0001558
            )
            <= 0.0001558 * 0.10,
            "focused_engine_step_count": (
                sum(cast(int, case["engine_steps"]) for case in primary + fine)
                == planned
                == FOCUSED_ENGINE_STEPS
            ),
            "finite_comparison_outputs": _finite_values(comparisons),
        }
        gates["essential_stage1"] = all(gates.values())
        if time.monotonic() >= deadline:
            raise BudgetExceeded(
                "3-minute focused-probe cap reached before result write"
            )
        result: dict[str, object] = {
            "schema_version": 3,
            "mode": "focused-falsifier-nonacceptance",
            "base_sha": BASE_SHA,
            "executable_sha": head,
            "protocol_sha256": sha256(PROTOCOL),
            "runtime": runtime,
            "planned_engine_steps": planned,
            "actual_engine_steps": sum(
                cast(int, case["engine_steps"]) for case in primary + fine
            ),
            "elapsed_s": time.monotonic() - started,
            "action_contract": action_contract,
            "gates": {
                name: "PASS" if passed else "FAIL"
                for name, passed in gates.items()
            },
            "predicted_head_on_sampled_penetration_m": {
                "400": 0.0002115,
                "800": 0.0001558,
            },
            "cases_400": primary,
            "cases_800": fine,
            "comparisons": comparisons,
            "full_stage2_authorized_by_probe": gates["essential_stage1"],
        }
        _write_json(output / "focused-results.json", result)
        _write_summary(
            output,
            title="v3 focused contact falsifier (not essential B)",
            head=head,
            gates=gates,
            elapsed=time.monotonic() - started,
            status_label="Stage 1 probe",
        )
        (output / "primary-progress.jsonl").unlink(missing_ok=True)
        (output / "fine-progress.jsonl").unlink(missing_ok=True)
        if time.monotonic() >= deadline:
            raise BudgetExceeded("3-minute focused-probe cap reached before finalizing")
        (output / "MEASUREMENT_STARTED").write_text(
            f"head={head}\nmode=focused-probe\nplanned_engine_steps={planned}\ncompleted=1\n",
            encoding="ascii",
        )
        _write_hash_manifest(output)
        return result
    except Exception as exc:
        _mark_incomplete(output, head, repr(exc), time.monotonic() - started)
        raise


def replay_worker(
    output: Path,
    expected_head: str,
    deadline: float,
) -> dict[str, object]:
    if output.resolve() != EXPECTED_OUTPUT.resolve():
        raise RuntimeError(
            f"replay output must be the v3 contact path {EXPECTED_OUTPUT}"
        )
    replay_path = output / "fresh-process-replay.json"
    preflight_output(replay_path, EXPECTED_OUTPUT / "fresh-process-replay.json")
    marker = output / "MEASUREMENT_STARTED"
    if not marker.is_file():
        raise RuntimeError("fresh replay requires an active primary v3 measurement")
    marker_text = marker.read_text(encoding="ascii")
    primary_trace_path = output / "primary-trace.json"
    primary_digest = hashlib.sha256(primary_trace_path.read_bytes()).hexdigest()
    if (
        f"head={expected_head}\n" not in marker_text
        or "phase=replay" not in marker_text
        or f"primary_trace_sha256={primary_digest}\n" not in marker_text
        or "completed=1" in marker_text
    ):
        raise RuntimeError("fresh replay marker/source/phase mismatch")
    head = check_frozen_tree(allow_outputs=(FOCUSED_OUTPUT, output))
    if head != expected_head:
        raise RuntimeError("fresh replay executable SHA differs from primary")
    _runtime_manifest()
    cases = fixed_cases()
    planned_primary = _planned_primary_cases(cases)
    if planned_primary * 2 != FULL_ENGINE_STEPS:
        raise RuntimeError("fresh replay planned engine-step count differs from freeze")
    if deadline <= time.monotonic():
        raise BudgetExceeded("15-minute cap expired before fresh replay")
    primary = _run_suite_capped(
        cases,
        PRIMARY,
        output=output,
        progress_name="replay-progress-400.jsonl",
        deadline=deadline,
    )
    fine = _run_suite_capped(
        cases,
        FINE,
        output=output,
        progress_name="replay-progress-800.jsonl",
        deadline=deadline,
    )
    replay_payload = _safe_canonical(
        {"cases_400": primary, "cases_800": fine}
    )
    replay_path.write_bytes(replay_payload)
    return {
        "process_id": os.getpid(),
        "executable_sha": head,
        "case_counts": [len(primary), len(fine)],
        "engine_steps": sum(
            cast(int, case["engine_steps"]) for case in primary + fine
        ),
        "trace_sha256": hashlib.sha256(replay_payload).hexdigest(),
    }


def validate_stage1_result(output: Path, head: str) -> dict[str, object]:
    result_path = output / "focused-results.json"
    marker_path = output / "MEASUREMENT_STARTED"
    if not result_path.is_file() or not marker_path.is_file():
        raise RuntimeError("Stage 2 requires a completed saved Stage 1 probe")
    marker = marker_path.read_text(encoding="ascii")
    result = cast(
        dict[str, object], json.loads(result_path.read_text(encoding="utf-8"))
    )
    gates = cast(dict[str, object], result.get("gates", {}))
    if (
        "completed=1" not in marker
        or result.get("executable_sha") != head
        or result.get("protocol_sha256") != sha256(PROTOCOL)
        or gates.get("essential_stage1") != "PASS"
        or result.get("full_stage2_authorized_by_probe") is not True
        or result.get("actual_engine_steps") != FOCUSED_ENGINE_STEPS
    ):
        raise RuntimeError("saved Stage 1 gates/source/count do not authorize Stage 2")
    return result


def run_full(output: Path) -> dict[str, object]:
    preflight_output(output, EXPECTED_OUTPUT)
    cases = fixed_cases()
    planned_primary = _planned_primary_cases(cases)
    planned_total = planned_primary * 2
    if planned_total != FULL_ENGINE_STEPS:
        raise RuntimeError(
            "full pre-step budget mismatch: "
            f"expected {FULL_ENGINE_STEPS}, got {planned_total}"
        )
    head = check_frozen_tree(allow_outputs=(FOCUSED_OUTPUT,))
    stage1 = validate_stage1_result(FOCUSED_OUTPUT, head)
    stage1_sha = sha256(FOCUSED_OUTPUT / "focused-results.json")
    runtime = _runtime_manifest()
    output.mkdir(parents=True, exist_ok=False)
    marker = output / "MEASUREMENT_STARTED"
    marker.write_text(
        f"head={head}\nmode=full-v3\nplanned_engine_steps={planned_total}\nphase=primary\n",
        encoding="ascii",
    )
    started = time.monotonic()
    deadline = started + 900.0
    try:
        action_contract = validate_action_and_encoder_contract()
        primary = _run_suite_capped(
            cases,
            PRIMARY,
            output=output,
            progress_name="primary-progress-400.jsonl",
            deadline=deadline,
        )
        fine = _run_suite_capped(
            cases,
            FINE,
            output=output,
            progress_name="primary-progress-800.jsonl",
            deadline=deadline,
        )
        primary_trace = _safe_canonical(
            {"cases_400": primary, "cases_800": fine}
        )
        primary_trace_path = output / "primary-trace.json"
        primary_trace_path.write_bytes(primary_trace)
        primary_digest = hashlib.sha256(primary_trace).hexdigest()
        marker.write_text(
            f"head={head}\nmode=full-v3\nplanned_engine_steps={planned_total}\n"
            f"phase=replay\nprimary_trace_sha256={primary_digest}\n",
            encoding="ascii",
        )
        remaining = deadline - time.monotonic()
        if remaining <= 1.0:
            raise BudgetExceeded("15-minute cap leaves no fresh replay budget")
        child = subprocess.run(
            [
                sys.executable,
                "-m",
                "experiments.pymunk_contact_prototype.run_contact_check_v3",
                "--replay-worker",
                "--output",
                str(output),
                "--expected-head",
                head,
                "--deadline-monotonic",
                f"{deadline:.6f}",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=remaining + 1.0,
        )
        if child.returncode != 0:
            raise RuntimeError(
                f"fresh replay failed ({child.returncode}): {child.stderr.strip()}"
            )
        if time.monotonic() >= deadline:
            raise BudgetExceeded("15-minute cap reached after replay")
        replay_meta = cast(dict[str, object], json.loads(child.stdout))
        replay_path = output / "fresh-process-replay.json"
        replay_trace = replay_path.read_bytes()
        replay_equal = primary_trace == replay_trace
        comparisons, contact_state_pass, clearance_pass = compare_resolutions(
            primary, fine
        )
        actual_steps = sum(
            cast(int, case["engine_steps"]) for case in primary + fine
        )
        actual_total_steps = actual_steps + cast(int, replay_meta["engine_steps"])
        gates = _gates_for_results(
            primary,
            fine,
            comparisons,
            contact_state_pass,
            clearance_pass,
            runtime,
            action_contract,
            replay_equal
            and cast(int, replay_meta["process_id"]) != os.getpid()
            and replay_meta["executable_sha"] == head
            and cast(int, replay_meta["engine_steps"]) == planned_primary,
            actual_total_steps,
        )
        result: dict[str, object] = {
            "schema_version": 3,
            "mode": "full-v3-contact-check",
            "base_sha": BASE_SHA,
            "executable_sha": head,
            "protocol_sha256": sha256(PROTOCOL),
            "stage1_result_sha256": stage1_sha,
            "runtime": runtime,
            "numerical_choice": {
                "primary_microsteps_per_0.1s": PRIMARY,
                "fine_microsteps_per_0.1s": FINE,
                "collision_bias": COLLISION_BIAS_10MS,
                "actuator_contact_response": "v2 rule unchanged",
            },
            "inventory": {
                "cases_each_resolution": [len(primary), len(fine)],
                "logical_commands_each_resolution": [
                    sum(cast(int, case["commands"]) for case in primary),
                    sum(cast(int, case["commands"]) for case in fine),
                ],
                "planned_engine_steps_primary_plus_replay": planned_total,
                "actual_engine_steps_primary": actual_steps,
                "actual_engine_steps_replay": replay_meta["engine_steps"],
                "total_scientific_engine_steps": planned_total,
            },
            "elapsed_s": time.monotonic() - started,
            "action_contract": action_contract,
            "thresholds": {
                "penetration_max_m": 0.001,
                "clearance_sample_bound_max_m": 0.0002,
                "free_space_error_m_rad": 1e-5,
                "400_vs_800_position_m": 0.0005,
                "400_vs_800_clearance_m": 0.0005,
                "400_vs_800_yaw_rad": 0.001,
                "contact_state_clearance_tolerance_m": 0.0005,
            },
            "gates": {
                name: "PASS" if passed else "FAIL"
                for name, passed in gates.items()
            },
            "essential_B_pass": gates["essential_B"],
            "fresh_process_replay": {
                "byte_identical": replay_equal,
                "primary_process_id": os.getpid(),
                "replay_process_id": replay_meta["process_id"],
                "primary_trace_sha256": primary_digest,
                "replay_trace_sha256": hashlib.sha256(replay_trace).hexdigest(),
            },
            "comparisons_400_vs_800": comparisons,
            "cases_400": primary,
            "cases_800": fine,
            "lifetime_authorized": False,
            "stage1_passed": cast(dict[str, object], stage1["gates"])[
                "essential_stage1"
            ]
            == "PASS",
        }
        _write_json(output / "results.json", result)
        _write_summary(
            output,
            title="Aweform Pymunk v3 full fixed-command contact check",
            head=head,
            gates=gates,
            elapsed=time.monotonic() - started,
        )
        for progress_name in (
            "primary-progress-400.jsonl",
            "primary-progress-800.jsonl",
            "replay-progress-400.jsonl",
            "replay-progress-800.jsonl",
        ):
            (output / progress_name).unlink(missing_ok=True)
        if time.monotonic() >= deadline:
            raise BudgetExceeded("15-minute cap reached before finalizing artifacts")
        marker.write_text(
            f"head={head}\nmode=full-v3\nplanned_engine_steps={planned_total}\n"
            f"phase=complete\ncompleted=1\nprimary_trace_sha256={primary_digest}\n",
            encoding="ascii",
        )
        _write_hash_manifest(output)
        return result
    except Exception as exc:
        _mark_incomplete(output, head, repr(exc), time.monotonic() - started)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--focused-probe", action="store_true")
    modes.add_argument("--measure", action="store_true")
    modes.add_argument("--replay-worker", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-head")
    parser.add_argument("--deadline-monotonic", type=float)
    args = parser.parse_args()
    if args.focused_probe:
        if args.expected_head or args.deadline_monotonic is not None:
            parser.error("replay-worker arguments are invalid for the focused probe")
        result = run_focused(args.output)
    elif args.measure:
        if args.expected_head or args.deadline_monotonic is not None:
            parser.error("replay-worker arguments are invalid for the primary run")
        result = run_full(args.output)
    else:
        if not args.expected_head or args.deadline_monotonic is None:
            parser.error(
                "replay worker requires --expected-head and --deadline-monotonic"
            )
        result = replay_worker(
            args.output, args.expected_head, args.deadline_monotonic
        )
    print(json.dumps(_json_safe(result), sort_keys=True))
    if args.focused_probe and not cast(
        bool, cast(dict[str, object], result["gates"])["essential_stage1"]
    ):
        raise SystemExit(1)
    if args.measure and not cast(bool, result["essential_B_pass"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
