"""Run only the four predeclared iteration-2 diagnostic probes."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
from pathlib import Path
from typing import cast

from .fixture import MAX_DELTA, ContactWorld
from .run_diagnostics import _canonical, _runtime_manifest, independent_arc, sha256

BASE_SHA = "48b18209a69d18841166bc8a00b56d00815e3b5b"
BRANCH = "fm/pymunk226-contact-prototype"
PROTOCOL = Path(__file__).with_name("diagnosis_protocol.md")
EXPECTED_OUTPUT = Path("experiments/pymunk_contact_prototype/results-v2/diagnosis")
A = MAX_DELTA
H = A / 2.0
ADJUSTED_BIAS_100_HZ = 0.9**100


def _check_frozen_tree() -> str:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    live_main = subprocess.check_output(
        ["git", "rev-parse", "origin/main"], text=True
    ).strip()
    branch = subprocess.check_output(
        ["git", "branch", "--show-current"], text=True
    ).strip()
    dirty = subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()
    changed = subprocess.check_output(
        ["git", "diff", "--name-only", BASE_SHA, head], text=True
    ).splitlines()
    if live_main != BASE_SHA:
        raise RuntimeError("origin/main differs from authorized iteration-2 base")
    if branch != BRANCH or dirty:
        raise RuntimeError("diagnostic probe requires the clean authorized branch")
    if head == BASE_SHA or not changed or any(
        not path.startswith("experiments/pymunk_contact_prototype/")
        for path in changed
    ):
        raise RuntimeError("diagnostic freeze must be committed and experiment-only")
    return head


def _run_case(
    *,
    case_id: str,
    start: tuple[float, float, float],
    command: tuple[float, float],
    repeat: int,
    suppress: bool = False,
    collision_bias: float = 0.001797010299914434,
) -> dict[str, object]:
    world = ContactWorld(
        microsteps=10,
        collision_bias=collision_bias,
        suppress_velocity_refresh_after_contact=suppress,
    )
    world.body.position = (start[0], start[1])
    world.body.angle = start[2]
    rows: list[dict[str, object]] = []
    max_penetration = 0.0
    max_arc_error = 0.0
    for index in range(repeat):
        record = world.advance(command)
        max_penetration = max(max_penetration, record.max_penetration)
        expected, expected_yaw = independent_arc(
            record.start, record.start_angle, *record.shaft
        )
        arc_error = math.dist(expected, record.end)
        max_arc_error = max(max_arc_error, arc_error)
        rows.append(
            {
                "index": index,
                "position_m": list(record.end),
                "yaw_unwrapped_rad": record.end_angle,
                "max_substep_penetration_m": record.max_penetration,
                "end_penetration_m": record.end_penetration,
                "contact_callback_seen": record.contact_seen,
                "post_solve_contact_points_sum": record.contact_count,
                "post_solve_callback_count": record.arbiter_count,
                "post_solve_impulse_sum": record.total_impulse,
                "free_arc_error_m": arc_error,
                "free_arc_yaw_error_rad": abs(record.end_angle - expected_yaw),
                "engine_steps": record.step_count,
            }
        )
    final = rows[-1]
    return {
        "case_id": case_id,
        "start": list(start),
        "command_rad_per_logical_step": list(command),
        "logical_steps": repeat,
        "microsteps_per_logical_step": 10,
        "total_engine_steps": world.engine_steps,
        "elapsed_s": world.elapsed,
        "collision_bias": collision_bias,
        "suppress_velocity_refresh_after_contact": suppress,
        "max_substep_penetration_m": max_penetration,
        "final_penetration_m": final["end_penetration_m"],
        "max_free_arc_error_m": max_arc_error,
        "final_position_m": final["position_m"],
        "final_yaw_rad": final["yaw_unwrapped_rad"],
        "any_contact_callback": any(bool(row["contact_callback_seen"]) for row in rows),
        "steps": rows,
    }


def run_probe(output: Path) -> dict[str, object]:
    expected = EXPECTED_OUTPUT.resolve()
    if output.resolve() != expected:
        raise RuntimeError(f"diagnostic output must be the new path {expected}")
    if output.exists():
        raise FileExistsError(f"diagnostic output already exists: {output}")
    head = _check_frozen_tree()
    runtime = _runtime_manifest()
    # Claim the unique output path before constructing a Space or stepping.
    output.mkdir(parents=True, exist_ok=False)
    (output / "PROBE_STARTED").write_text(f"head={head}\n", encoding="ascii")

    cases = [
        _run_case(
            case_id="wall_refresh_suppressed_after_contact",
            start=(0.5, 1.5, math.pi),
            command=(A, A),
            repeat=20,
            suppress=True,
        ),
        _run_case(
            case_id="wall_bias_rate_counterfactual",
            start=(0.5, 1.5, math.pi),
            command=(A, A),
            repeat=20,
            collision_bias=ADJUSTED_BIAS_100_HZ,
        ),
        _run_case(
            case_id="free_space_refresh_disconfirmation",
            start=(1.5, 1.5, 0.0),
            command=(A, H),
            repeat=20,
            suppress=True,
        ),
        _run_case(
            case_id="passive_wall_contact_control",
            start=(0.095, 1.5, math.pi),
            command=(0.0, 0.0),
            repeat=20,
        ),
    ]
    if len(cases) != 4 or sum(
        cast(int, case["total_engine_steps"]) for case in cases
    ) != 800:
        raise RuntimeError("probe inventory/count differs from frozen four-case budget")
    result: dict[str, object] = {
        "schema_version": 1,
        "protocol_sha256": sha256(PROTOCOL),
        "probe_executable_sha": head,
        "authorized_base_sha": BASE_SHA,
        "historical_v1_result_sha256": (
            "8937854444fb02f1e19597741db42528f7bdc476f684ed6daa4489e44bb4a522"
        ),
        "runtime": runtime,
        "probe_count": len(cases),
        "logical_steps": sum(cast(int, case["logical_steps"]) for case in cases),
        "engine_steps": sum(
            cast(int, case["total_engine_steps"]) for case in cases
        ),
        "cases": cases,
        "essential_B_pass": False,
        "lifetime_authorized_to_run": False,
        "interpretation_boundary": (
            "diagnostic probes only; not acceptance measurements"
        ),
    }
    json_path = output / "diagnosis.json"
    payload = _canonical(result) + b"\n"
    json_path.write_bytes(payload)
    markdown = [
        "# Iteration 2 bounded contact-cause diagnostic probes",
        "",
        f"Probe executable SHA: `{head}`",
        "",
        f"Protocol SHA-256: `{result['protocol_sha256']}`",
        "",
        "Diagnostic probes only; no essential-B pass or lifetime authorization.",
        "",
        "| Probe | Max penetration (m) | Final penetration (m) | Contact callback |",
        "|---|---:|---:|---|",
    ]
    markdown.extend(
        f"| {case['case_id']} | {case['max_substep_penetration_m']:.12g} | "
        f"{case['final_penetration_m']:.12g} | {case['any_contact_callback']} |"
        for case in cases
    )
    report_path = output / "DIAGNOSIS.md"
    report_path.write_text("\n".join(markdown) + "\n", encoding="utf-8")
    (output / "SHA256SUMS").write_text(
        f"{sha256(json_path)}  diagnosis.json\n{sha256(report_path)}  DIAGNOSIS.md\n",
        encoding="ascii",
    )
    (output / "PROBE_STARTED").write_text(
        f"head={head}\ncompleted=1\n", encoding="ascii"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-bounded-probes", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.run_bounded_probes:
        parser.error("explicit --run-bounded-probes is required")
    result = run_probe(args.output)
    print(
        json.dumps(
            {
                "probe_count": result["probe_count"],
                "engine_steps": result["engine_steps"],
                "output": str(args.output),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
