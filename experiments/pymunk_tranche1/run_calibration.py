from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

import pymunk

from aweform.d045 import integrate_differential_drive
from experiments.pymunk_tranche1.oracle import differential_drive_arc
from experiments.pymunk_tranche1.probe import (
    DT_SECONDS,
    ENCODER_QUANTUM_RAD,
    MAX_WHEEL_DELTA_RAD,
    PymunkProbe,
    quantize_encoder,
)

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_SHA = "89de47de86aea43d30e7dc5147c51ed5d1263b1d"
BASE_SHA = "fd68c46d2cd75c46dd0eb824b8360f36f1de6cf8"
EXECUTABLE_SHA = subprocess.check_output(
    ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
).strip()
A = MAX_WHEEL_DELTA_RAD
B = A / 2.0
HEADINGS = (0.0, math.pi / 2.0, -math.pi / 2.0, math.pi)
COMMANDS: tuple[tuple[str, tuple[float, float]], ...] = (
    ("ZERO", (0.0, 0.0)),
    ("FORWARD", (A, A)),
    ("REVERSE", (-A, -A)),
    ("SPIN_POSITIVE", (-A, A)),
    ("SPIN_NEGATIVE", (A, -A)),
    ("ARC_NEGATIVE_YAW", (A, B)),
    ("ARC_POSITIVE_YAW", (B, A)),
)
CANONICAL_FIELDS = (
    "action_index",
    "requested_wheel_deltas_rad",
    "clipped_shaft_deltas_rad",
    "endpoint_x_m",
    "endpoint_y_m",
    "unwrapped_heading_rad",
    "endpoint_vx_m_s",
    "endpoint_vy_m_s",
    "endpoint_angular_velocity_rad_s",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def runtime_manifest() -> dict[str, Any]:
    wheel_path = os.environ.get("PYMUNK_WHEEL_PATH")
    wheel: dict[str, str] | None = None
    if wheel_path:
        path = Path(wheel_path)
        wheel = {"filename": path.name, "sha256": sha256(path)}
    try:
        translated = (
            subprocess.check_output(
                ["sysctl", "-in", "sysctl.proc_translated"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            == "1"
        )
    except OSError, subprocess.CalledProcessError:
        translated = False
    try:
        sw_vers = subprocess.check_output(["sw_vers"], text=True).strip()
    except OSError, subprocess.CalledProcessError:
        sw_vers = "unavailable"
    lock_path = ROOT / "uv.lock"
    return {
        "uname_a": " ".join(platform.uname()),
        "sw_vers": sw_vers,
        "architecture": platform.machine(),
        "python_vv": sys.version,
        "python_executable": sys.executable,
        "rosetta_translated": translated,
        "native_arm64": platform.machine() == "arm64" and not translated,
        "pymunk_version": pymunk.version,
        "munk_engine_version": pymunk.chipmunk_version,
        "pymunk_wheel": wheel,
        "uv_lock_sha256": sha256(lock_path),
        "uv_version": subprocess.check_output(["uv", "--version"], text=True).strip(),
        "pymunk_imported_headless": "pygame" not in sys.modules,
    }


def oracle_pair(
    heading: float, request: tuple[float, float], actual: tuple[float, float]
) -> tuple[tuple[float, float], float, tuple[float, float], float]:
    expected_position, expected_heading = differential_drive_arc(
        (0.0, 0.0), heading, *actual
    )
    helper_position, helper_heading = integrate_differential_drive(
        (0.0, 0.0), heading, *actual
    )
    del request
    return expected_position, expected_heading, helper_position, helper_heading


def evaluate_case(
    label: str,
    command: tuple[float, float],
    heading: float,
    amplitude: float,
    microsteps: int = 10,
) -> dict[str, Any]:
    request = (amplitude * command[0], amplitude * command[1])
    probe = PymunkProbe(microsteps=microsteps)
    endpoint = probe.advance(request, heading=heading)
    expected_position, expected_heading, helper_position, helper_heading = oracle_pair(
        heading, request, endpoint.shaft_deltas
    )
    position_error = math.dist(endpoint.position, expected_position)
    yaw_error = abs(endpoint.heading - expected_heading)
    helper_position_error = math.dist(expected_position, helper_position)
    helper_yaw_error = abs(expected_heading - helper_heading)
    return {
        "case_id": f"{label}:h={heading:.17g}:amp={amplitude:.2f}:n={microsteps}",
        "command_label": label,
        "requested_wheel_deltas_rad": list(request),
        "clipped_actual_shaft_deltas_rad": list(endpoint.shaft_deltas),
        "heading_start_rad": heading,
        "amplitude": amplitude,
        "microsteps": microsteps,
        "dt_seconds": DT_SECONDS,
        "expected_position_m": list(expected_position),
        "expected_unwrapped_heading_rad": expected_heading,
        "actual_position_m": list(endpoint.position),
        "actual_unwrapped_heading_rad": endpoint.heading,
        "position_error_m": position_error,
        "yaw_error_rad": yaw_error,
        "endpoint_velocity_m_s": list(endpoint.velocity),
        "endpoint_angular_velocity_rad_s": endpoint.angular_velocity,
        "independent_oracle": (
            "experiments.pymunk_tranche1.oracle.differential_drive_arc"
        ),
        "aweform_helper_crosscheck": {
            "position_m": list(helper_position),
            "heading_rad": helper_heading,
            "position_difference_m": helper_position_error,
            "yaw_difference_rad": helper_yaw_error,
        },
        "status": "PASS" if position_error <= 1e-5 and yaw_error <= 1e-5 else "FAIL",
    }


def canonical_trace() -> bytes:
    commands = [command for _, command in COMMANDS]
    schedule = commands * 142 + commands[:6]
    probe = PymunkProbe()
    rows: list[dict[str, Any]] = []
    for index, command in enumerate(schedule):
        endpoint = probe.advance(command)
        rows.append(
            {
                "action_index": index,
                "requested_wheel_deltas_rad": list(command),
                "clipped_shaft_deltas_rad": list(endpoint.shaft_deltas),
                "endpoint_x_m": endpoint.position[0],
                "endpoint_y_m": endpoint.position[1],
                "unwrapped_heading_rad": endpoint.heading,
                "endpoint_vx_m_s": endpoint.velocity[0],
                "endpoint_vy_m_s": endpoint.velocity[1],
                "endpoint_angular_velocity_rad_s": endpoint.angular_velocity,
            }
        )
    return json.dumps(
        rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def main() -> None:
    cases: list[dict[str, Any]] = []
    for name, command in COMMANDS:
        for heading in HEADINGS:
            for amplitude in (0.25, 0.5, 1.0):
                cases.append(evaluate_case(name, command, heading, amplitude))
    for name, command in (("ONE_WHEEL_LEFT", (A, 0.0)), ("ONE_WHEEL_RIGHT", (0.0, A))):
        for heading in HEADINGS:
            cases.append(evaluate_case(name, command, heading, 1.0))

    clipped_cases = []
    for command in ((2 * A, -3 * A), (-3 * A, 2 * A)):
        endpoint = PymunkProbe().advance(command)
        expected = tuple(min(A, max(-A, v)) for v in command)
        clipped_cases.append(
            {
                "requested": list(command),
                "actual_shaft_deltas": list(endpoint.shaft_deltas),
                "expected_clipped": list(expected),
                "status": "PASS" if endpoint.shaft_deltas == expected else "FAIL",
            }
        )

    tiny = PymunkProbe().advance((1e-15, -1e-15))
    invalid = [
        (),
        (1.0,),
        (1.0, 2.0, 3.0),
        "12",
        ("bad", 0.0),
        (True, 0.0),
        (math.nan, 0.0),
        (0.0, math.inf),
        (-math.inf, 0.0),
    ]
    invalid_results = []
    for item in invalid:
        probe = PymunkProbe()
        try:
            probe.advance(item)  # type: ignore[arg-type]
        except ValueError:
            rejected = probe.elapsed_seconds == 0.0
        else:
            rejected = False
        invalid_results.append(
            {"input_repr": repr(item), "rejected_no_advance": rejected}
        )

    q = ENCODER_QUANTUM_RAD
    half_inputs = [
        math.nextafter(0.5 * q, 0.0),
        math.nextafter(0.5 * q, math.inf),
        0.5 * q,
        math.nextafter(-0.5 * q, 0.0),
        math.nextafter(-0.5 * q, -math.inf),
        -0.5 * q,
    ]
    quantization = [
        {"input_rad": x, "output_rad": quantize_encoder(x)} for x in half_inputs
    ]

    convergence = []
    for name, command in COMMANDS:
        ten = evaluate_case(name, command, 0.0, 1.0, 10)
        twenty = evaluate_case(name, command, 0.0, 1.0, 20)
        position_difference = math.dist(
            ten["actual_position_m"], twenty["actual_position_m"]
        )
        yaw_difference = abs(
            ten["actual_unwrapped_heading_rad"] - twenty["actual_unwrapped_heading_rad"]
        )
        convergence.append(
            {
                "command_label": name,
                "position_difference_m": position_difference,
                "yaw_difference_rad": yaw_difference,
                "status": "PASS"
                if position_difference <= 1e-4 and yaw_difference <= 1e-4
                else "FAIL",
            }
        )

    forward = PymunkProbe().advance((A, A))
    reverse = PymunkProbe().advance((-A, -A))
    left_arc = PymunkProbe().advance((A, B))
    right_arc = PymunkProbe().advance((B, A))
    rotated_arc = PymunkProbe().advance((A, B), heading=math.pi / 2.0)
    symmetry_errors = {
        "reverse_position_m": math.dist(
            reverse.position, (-forward.position[0], -forward.position[1])
        ),
        "wheel_swap_position_m": math.dist(left_arc.position, right_arc.position),
        "wheel_swap_yaw_rad": abs(left_arc.heading + right_arc.heading),
        "rotated_displacement_m": math.dist(
            rotated_arc.position, (-left_arc.position[1], left_arc.position[0])
        ),
        "rotated_heading_rad": abs(
            rotated_arc.heading - (left_arc.heading + math.pi / 2)
        ),
    }
    symmetry_ok = (
        symmetry_errors["reverse_position_m"] <= 1e-5
        and symmetry_errors["wheel_swap_position_m"] <= 1e-5
        and symmetry_errors["wheel_swap_yaw_rad"] <= 1e-5
        and symmetry_errors["rotated_displacement_m"] <= 1e-5
        and symmetry_errors["rotated_heading_rad"] <= 1e-5
    )
    trace_bytes = [canonical_trace() for _ in range(10)]
    trace_hashes = [hashlib.sha256(value).hexdigest() for value in trace_bytes]
    repeatable = all(value == trace_bytes[0] for value in trace_bytes[1:])
    manifest = runtime_manifest()
    cal_ok = all(case["status"] == "PASS" for case in cases)
    gates = [
        {
            "id": "headless-runtime",
            "threshold": "canonical Python; no Pygame import or "
            "graphics/wall-clock coupling",
            "status": "PASS" if manifest["pymunk_imported_headless"] else "FAIL",
        },
        {
            "id": "action-timing",
            "threshold": "one 0.1 s interval/action; clipped shaft deltas "
            "within 1e-12 rad; invalid inputs reject without advancement",
            "status": "PASS"
            if all(item["status"] == "PASS" for item in clipped_cases)
            and tiny.shaft_deltas == (1e-15, -1e-15)
            and all(item["rejected_no_advance"] for item in invalid_results)
            else "FAIL",
        },
        {
            "id": "free-space-calibration",
            "threshold": "position <=1e-5 m; yaw <=1e-5 rad; "
            "spin-center translation <=1e-5 m",
            "status": "PASS" if cal_ok else "FAIL",
            "case_ids": [case["case_id"] for case in cases],
        },
        {
            "id": "known-vectors",
            "threshold": "r*a=0.029059732045705586 m; opposed-wheel yaw "
            "+/-pi/10; zero stationary",
            "status": "PASS"
            if cal_ok
            and all(
                c["status"] == "PASS"
                for c in cases
                if c["command_label"]
                in ("ZERO", "FORWARD", "SPIN_POSITIVE", "SPIN_NEGATIVE")
            )
            else "FAIL",
        },
        {
            "id": "symmetry",
            "threshold": "equal-wheel reversal, wheel-swap yaw mirror, and "
            "rotated-heading displacement rotation within calibration tolerances",
            "status": "PASS" if symmetry_ok else "FAIL",
            "measurements": symmetry_errors,
        },
        {
            "id": "microstep-convergence",
            "threshold": "10 versus 20 steps: position <=0.1 mm and yaw <=1e-4 rad",
            "status": "PASS"
            if all(item["status"] == "PASS" for item in convergence)
            else "FAIL",
        },
        {
            "id": "reset-repeatability",
            "threshold": "10 independent 1000-interval fixed schedules have "
            "identical canonical trace bytes",
            "status": "PASS" if repeatable else "FAIL",
            "trace_sha256": trace_hashes,
        },
        {
            "id": "encoder-quantization",
            "threshold": "one-degree nearest quantum; ties away from zero",
            "status": "PASS"
            if [quantize_encoder(x) for x in half_inputs] == [0.0, q, q, 0.0, -q, -q]
            else "FAIL",
        },
    ]
    output = {
        "schema_version": 1,
        "protocol_sha": PROTOCOL_SHA,
        "base_sha": BASE_SHA,
        "executable_sha": EXECUTABLE_SHA,
        "runtime_manifest": manifest,
        "fixture": {
            "units": {"length": "m", "time": "s", "angle": "rad"},
            "body_type": "dynamic",
            "body_dimensions_m": [0.180, 0.215],
            "fixture_mass_kg": 1.0,
            "fixture_moment_kg_m2": 1.0 * (0.180**2 + 0.215**2) / 12,
            "wheel_radius_m": 0.045,
            "track_width_m": 0.185,
            "dt_seconds": DT_SECONDS,
            "microsteps": 10,
            "space_settings": {
                "threaded": False,
                "gravity": [0, 0],
                "damping": 1.0,
                "iterations": 10,
                "collision_slop_m": 0.0001,
                "collision_bias": 0.001797010299914434,
                "collision_persistence": 3,
                "sleep_time_threshold": "infinity",
                "idle_speed_threshold": 0.0,
            },
            "actuator": (
                "ideal clipped shaft deltas; derived imposed chassis twist; "
                "no PID/traction/torque model"
            ),
        },
        "gates": gates,
        "cases": cases,
        "additional_checks": {
            "symmetry_errors": symmetry_errors,
            "independent_clipping": clipped_cases,
            "invalid_input_rejection": invalid_results,
            "tiny_signed_command": {
                "shaft_deltas": list(tiny.shaft_deltas),
                "position_m": list(tiny.position),
                "heading_rad": tiny.heading,
            },
            "encoder_half_quantum": quantization,
            "microstep_convergence": convergence,
            "canonical_trace_fields": list(CANONICAL_FIELDS),
        },
        "repeatability": {
            "schedule": (
                "(ZERO, FORWARD, REVERSE, SPIN_POSITIVE, SPIN_NEGATIVE, "
                "ARC_NEGATIVE_YAW, ARC_POSITIVE_YAW)*142 + first 6"
            ),
            "intervals": 1000,
            "independent_runs": 10,
            "trace_sha256": trace_hashes,
            "byte_identical": repeatable,
        },
        "artifacts": {
            "json": "experiments/pymunk_tranche1/results.json",
            "markdown": "experiments/pymunk_tranche1/RESULTS.md",
            "sha256sums": "experiments/pymunk_tranche1/SHA256SUMS",
        },
    }
    result_path = ROOT / "experiments/pymunk_tranche1/results.json"
    result_path.write_text(
        json.dumps(output, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    markdown_path = ROOT / "experiments/pymunk_tranche1/RESULTS.md"
    gate_rows = "\n".join(
        f"| {gate['id']} | {gate['status']} | {gate['threshold']} |" for gate in gates
    )
    markdown_path.write_text(
        "# Direct-Pymunk Tranche 1 results\n\n"
        f"- Base SHA: `{BASE_SHA}`\n"
        f"- Protocol SHA: `{PROTOCOL_SHA}`\n"
        f"- Executable SHA: `{EXECUTABLE_SHA}`\n"
        "- Scope: isolated empty-space calibration; no organism/controller/learner "
        "execution.\n"
        "- Platform: `"
        + str(manifest["architecture"])
        + "`; native arm64: `"
        + str(manifest["native_arm64"])
        + "`; Python `"
        + str(manifest["python_vv"]).splitlines()[0]
        + "`; Pymunk `"
        + str(manifest["pymunk_version"])
        + "`; Munk `"
        + str(manifest["munk_engine_version"])
        + "`.\n\n"
        "## Frozen gate results\n\n"
        "| Gate | Result | Frozen criterion |\n|---|---|---|\n" + gate_rows + "\n\n"
        f"Evaluated calibration cases: {len(cases)}. Repeatability: "
        f"{'PASS' if repeatable else 'FAIL'} ({len(trace_hashes)} runs, "
        f"trace SHA-256 `{trace_hashes[0]}`).\n\n"
        "## Claims and limitations\n\n"
        "- **VERIFIED:** only the listed fixture, fixed commands, pinned runtime "
        "and numerical gates in this artifact.\n"
        "- **INFERENCE:** the isolated direct-Pymunk probe is a plausible bounded "
        "candidate for future evaluation; no engineering-savings conclusion "
        "follows from this tranche.\n"
        "- **UNKNOWN / NEEDS TESTING:** collision-engineering savings, contact "
        "behavior, hardware fidelity, other platforms and any production integration.\n"
        "- Pose and velocity are evaluator-only. No controller or organism was "
        "routed through Pymunk.\n"
        "- Ten-run trace identity is specific to this tested stack; it is not "
        "cross-platform or universal bitwise determinism. Numerical tolerances "
        "are those frozen in the protocol.\n\n"
        "## Recommendation\n\n"
        "Stop after Tranche 1. A passing calibration is not grounds for "
        "migration; any later tranche needs separate authorization.\n"
    )
    sums_path = ROOT / "experiments/pymunk_tranche1/SHA256SUMS"
    sums_path.write_text(
        f"{sha256(result_path)}  experiments/pymunk_tranche1/results.json\n"
        f"{sha256(markdown_path)}  experiments/pymunk_tranche1/RESULTS.md\n"
    )
    print(
        json.dumps(
            {
                "result": str(result_path),
                "executable_sha": EXECUTABLE_SHA,
                "gates": gates,
            },
            indent=2,
        )
    )
    if any(gate["status"] != "PASS" for gate in gates):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
