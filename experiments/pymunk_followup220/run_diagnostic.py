"""Execute the frozen, empty-space Pymunk #220 candidate matrix."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import os
import platform
import shlex
import subprocess
import sys
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast

import pymunk

from experiments.pymunk_followup220.oracle import (
    body_frame_displacement,
    differential_drive_arc,
    rotate_displacement,
)
from experiments.pymunk_followup220.probe import (
    BODY_LENGTH_M,
    BODY_WIDTH_M,
    CANDIDATES,
    DT_SECONDS,
    ENCODER_QUANTUM_RAD,
    FIXTURE_MASS_KG,
    FIXTURE_MOMENT_KG_M2,
    MAX_WHEEL_DELTA_RAD,
    TRACK_WIDTH_M,
    WHEEL_RADIUS_M,
    CandidateId,
    PymunkFollowupProbe,
    quantize_encoder,
)

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_DIR = ROOT / "experiments/pymunk_followup220"
PROTOCOL_PATH = ROOT / "docs/pymunk-followup220-protocol.md"
PROTOCOL_SHA = "7044e37b1259698f9277b9eae2224da64ba63a64"
BASE_SHA = "ce4f4943f6d8fcd84c723a151b15178f3856e098"
AUTHORIZED_BRANCH = "codex/pymunk220-corrected-empty-space-calibration"

A = MAX_WHEEL_DELTA_RAD
B = A / 2.0
HEADINGS = (0.0, math.pi / 2.0, -math.pi / 2.0, math.pi)
AMPLITUDES = (0.25, 0.5, 1.0)
CORE_ACTIONS: tuple[tuple[str, tuple[float, float]], ...] = (
    ("ZERO", (0.0, 0.0)),
    ("FORWARD", (A, A)),
    ("REVERSE", (-A, -A)),
    ("SPIN_POSITIVE", (-A, A)),
    ("SPIN_NEGATIVE", (A, -A)),
    ("ARC_NEGATIVE_YAW", (A, B)),
    ("ARC_POSITIVE_YAW", (B, A)),
    ("ONE_WHEEL_LEFT", (A, 0.0)),
    ("ONE_WHEEL_RIGHT", (0.0, A)),
)
SCHEDULE_ACTIONS = CORE_ACTIONS[:7]
CLIPPING_ACTIONS: tuple[tuple[str, tuple[float, float]], ...] = (
    ("CLIP_LEFT_POSITIVE_RIGHT_NEGATIVE", (2.0 * A, -3.0 * A)),
    ("CLIP_LEFT_NEGATIVE_RIGHT_POSITIVE", (-3.0 * A, 2.0 * A)),
)
TINY_ACTIONS: tuple[tuple[str, tuple[float, float]], ...] = (
    ("TINY_POSITIVE_NEGATIVE", (1e-15, -1e-15)),
    ("TINY_NEGATIVE_POSITIVE", (-1e-15, 1e-15)),
    ("TINY_LEFT_ONLY", (1e-15, 0.0)),
    ("TINY_RIGHT_ONLY", (0.0, -1e-15)),
)
CANONICAL_TRACE_FIELDS = (
    "action_index",
    "candidate_id",
    "requested_wheel_deltas_rad",
    "clipped_actual_shaft_deltas_rad",
    "endpoint_x_m",
    "endpoint_y_m",
    "unwrapped_heading_rad",
    "endpoint_vx_m_s",
    "endpoint_vy_m_s",
    "endpoint_angular_velocity_rad_s",
)

HISTORICAL_FILE_HASHES = {
    "docs/pymunk-tranche1-protocol.md": (
        "2fb94c15d13f19fcf96ee5234a26598b60bf29cc1893a7b2dda49ed39ebe0254"
    ),
    "experiments/pymunk_tranche1/RESULTS.original.md": (
        "f8310ee8b7f1b26567d891b4bc7f2e0391d15030b4620209aa325ef105a9d715"
    ),
    "experiments/pymunk_tranche1/RESULTS.md": (
        "3b74666271da3e4bcc3db1d8545b247eedecad951502ec02e8c573726a69f169"
    ),
    "experiments/pymunk_tranche1/ADDENDUM.md": (
        "e6e76d77b0358c7dd658bc0c8a3122000cca8b908f6d5d54717cfc32c9bac187"
    ),
    "experiments/pymunk_tranche1/SHA256SUMS": (
        "4d561164383594fbbca3a8d2b0fc0fcacea3c3f256425ea61e71f9895bc41a5c"
    ),
    "experiments/pymunk_tranche1/results.json": (
        "4a0a0c5c1bef6602553971a9745274c649c56a70e394cde285e5cbf3d6f428e2"
    ),
    "experiments/pymunk_tranche1/probe.py": (
        "ce971b6d7f9ceb7fbce4b48774beebb80002a335cb497800fcc383b4de15c132"
    ),
    "experiments/pymunk_tranche1/oracle.py": (
        "e5e5979e28f11fa26253cf7fc8e487fff6515adbce4b1f5aca392f7485f6ba2b"
    ),
    "experiments/pymunk_tranche1/run_calibration.py": (
        "36e74110132188c9b26825b798b01f836e4b51a8f4eebef530495eade5818bc2"
    ),
    "experiments/pymunk_tranche1/test_probe.py": (
        "ced382b1f76be894c2d019732186f1b3687226041626129b350b12182bb1b710"
    ),
}
HISTORICAL_GATE_STATUS = {
    "headless-runtime": "PASS",
    "action-timing": "PASS",
    "free-space-calibration": "FAIL",
    "known-vectors": "FAIL",
    "symmetry": "FAIL",
    "microstep-convergence": "PASS",
    "reset-repeatability": "PASS",
    "encoder-quantization": "PASS",
}
HISTORICAL_MAX_POSITION_ERROR_M = 0.00011400040559442288
HISTORICAL_WHEEL_SWAP_POSITION_MISMATCH_M = 0.0015398709610861183
POSITION_TOLERANCE_M = 1e-5
YAW_TOLERANCE_RAD = 1e-5
CLIP_TOLERANCE_RAD = 1e-12
CONVERGENCE_POSITION_TOLERANCE_M = 1e-4
CONVERGENCE_YAW_TOLERANCE_RAD = 1e-4
FORBIDDEN_SOURCE_MODULE_ROOTS = frozenset(
    {"pygame", "pygame_gui", "tkinter", "random", "secrets", "time"}
)
FORBIDDEN_SOURCE_DOTTED_NAMES = frozenset(
    {
        "pymunk.pygame_util",
        "time.sleep",
        "time.time",
        "time.perf_counter",
        "time.monotonic",
    }
)


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    candidate_id: str
    command_label: str
    requested_wheel_deltas_rad: tuple[float, float]
    clipped_actual_shaft_deltas_rad: tuple[float, float]
    heading_start_rad: float
    amplitude: float
    microsteps: int
    dt_seconds: float
    elapsed_seconds: float
    expected_position_m: tuple[float, float]
    expected_unwrapped_heading_rad: float
    actual_position_m: tuple[float, float]
    actual_unwrapped_heading_rad: float
    position_error_m: float
    yaw_error_rad: float
    endpoint_velocity_m_s: tuple[float, float]
    endpoint_angular_velocity_rad_s: float
    engine_step_count: int
    status: str


@dataclass(frozen=True)
class GateResult:
    gate_id: str
    threshold: str
    status: str
    case_ids: tuple[str, ...]
    metrics: dict[str, str | int | float | bool]


@dataclass(frozen=True)
class CheckResult:
    check_id: str
    status: str
    measurements: dict[str, str | int | float | bool]


@dataclass(frozen=True)
class RepeatabilityResult:
    schedule: str
    intervals: int
    independent_runs: int
    trace_sha256: tuple[str, ...]
    byte_identical: bool


@dataclass(frozen=True)
class CandidateResult:
    candidate_id: CandidateId
    cases: tuple[CaseResult, ...]
    metamorphic_checks: tuple[CheckResult, ...]
    known_vector_checks: tuple[CheckResult, ...]
    clipping_checks: tuple[CheckResult, ...]
    tiny_input_checks: tuple[CheckResult, ...]
    invalid_input_checks: tuple[CheckResult, ...]
    encoder_checks: tuple[CheckResult, ...]
    convergence_checks: tuple[CheckResult, ...]
    repeatability: RepeatabilityResult
    gates: tuple[GateResult, ...]


@dataclass(frozen=True)
class WheelIdentity:
    path: str
    filename: str
    sha256: str
    lock_sha256: str
    lock_size_bytes: int
    lock_url: str
    matches_lock: bool


@dataclass(frozen=True)
class RuntimeManifest:
    uname: str
    os_version: str
    architecture: str
    native_arm64: bool
    rosetta_translated: bool
    python_vv: str
    python_executable: str
    pymunk_version: str
    chipmunk_version: str
    pymunk_module_path: str
    wheel: WheelIdentity
    uv_version: str
    uv_lock_sha256: str
    pygame_imported: bool


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _dotted_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def runtime_source_violations() -> tuple[str, ...]:
    """Audit implementation imports/calls for forbidden runtime coupling."""
    violations: set[str] = set()
    source_paths = (
        EXPERIMENT_DIR / "probe.py",
        EXPERIMENT_DIR / "oracle.py",
        EXPERIMENT_DIR / "run_diagnostic.py",
    )
    for path in source_paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            imported_names: tuple[str, ...] = ()
            if isinstance(node, ast.Import):
                imported_names = tuple(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported_names = (node.module,)
            for imported_name in imported_names:
                root = imported_name.split(".", maxsplit=1)[0]
                if root in FORBIDDEN_SOURCE_MODULE_ROOTS:
                    violations.add(f"{path.name}:forbidden-import:{imported_name}")
                if imported_name in FORBIDDEN_SOURCE_DOTTED_NAMES:
                    violations.add(f"{path.name}:forbidden-import:{imported_name}")
            if isinstance(node, ast.Attribute):
                dotted = _dotted_name(node)
                if dotted in FORBIDDEN_SOURCE_DOTTED_NAMES:
                    violations.add(f"{path.name}:forbidden-reference:{dotted}")
            if isinstance(node, ast.Call):
                dotted = _dotted_name(node.func)
                if dotted in FORBIDDEN_SOURCE_DOTTED_NAMES or dotted in {
                    "sleep",
                    "time",
                    "perf_counter",
                    "monotonic",
                }:
                    violations.add(f"{path.name}:forbidden-call:{dotted}")
    return tuple(sorted(violations))


def experiment_production_imports() -> tuple[str, ...]:
    """Return any direct imports of production Aweform modules in this experiment."""
    imports: set[str] = set()
    for path in EXPERIMENT_DIR.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            module_names: tuple[str, ...] = ()
            if isinstance(node, ast.Import):
                module_names = tuple(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                module_names = (node.module,)
            for module_name in module_names:
                if module_name == "aweform" or module_name.startswith("aweform."):
                    imports.add(f"{path.name}:{module_name}")
    return tuple(sorted(imports))


def independent_clipped_action(
    requested: tuple[float, float],
) -> tuple[float, float]:
    """Calculate clamp expectations independently of the candidate actuator."""
    return (
        max(-A, min(A, requested[0])),
        max(-A, min(A, requested[1])),
    )


def git_text(*arguments: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), *arguments], text=True
    ).strip()


def require_clean_frozen_checkout(*, replay_frozen: bool = False) -> str:
    head = git_text("rev-parse", "HEAD")
    branch = git_text("branch", "--show-current")
    status = git_text("status", "--porcelain=v1", "--untracked-files=all")
    main_sha = git_text("rev-parse", "origin/main")
    remote_branch_sha = git_text("rev-parse", f"origin/{AUTHORIZED_BRANCH}")
    if replay_frozen:
        if branch not in ("", AUTHORIZED_BRANCH):
            raise RuntimeError(
                "STOP: replay must use a detached checkout or the authorized "
                f"branch, got {branch}"
            )
        pushed_ancestor = subprocess.run(
            [
                "git",
                "-C",
                str(ROOT),
                "merge-base",
                "--is-ancestor",
                head,
                remote_branch_sha,
            ],
            check=False,
        )
        if pushed_ancestor.returncode != 0:
            raise RuntimeError(
                "STOP: replay SHA is not present in the pushed authorized branch"
            )
    else:
        if head != remote_branch_sha:
            raise RuntimeError(
                "STOP: first execution requires the pushed executable freeze at "
                f"branch HEAD (local={head}, remote={remote_branch_sha})"
            )
        if branch != AUTHORIZED_BRANCH:
            raise RuntimeError(
                f"STOP: expected authorized branch {AUTHORIZED_BRANCH}, got {branch}"
            )
    if main_sha != BASE_SHA:
        raise RuntimeError(
            "STOP: origin/main moved from exact authorized base "
            f"{BASE_SHA} to {main_sha}"
        )
    if status:
        raise RuntimeError(f"STOP: executable checkout is not clean: {status}")
    if git_text("merge-base", "HEAD", BASE_SHA) != BASE_SHA:
        raise RuntimeError("STOP: executable HEAD is not based on the authorized SHA")
    protocol_diff = subprocess.run(
        [
            "git",
            "-C",
            str(ROOT),
            "diff",
            "--quiet",
            PROTOCOL_SHA,
            "HEAD",
            "--",
            str(PROTOCOL_PATH),
        ],
        check=False,
    )
    if protocol_diff.returncode != 0:
        raise RuntimeError("STOP: frozen protocol differs from its protocol commit")
    immutable_paths = (
        "src",
        "tests",
        "pyproject.toml",
        "uv.lock",
        "experiments/pymunk_tranche1",
    )
    diff = subprocess.run(
        [
            "git",
            "-C",
            str(ROOT),
            "diff",
            "--quiet",
            BASE_SHA,
            "HEAD",
            "--",
            *immutable_paths,
        ],
        check=False,
    )
    if diff.returncode != 0:
        raise RuntimeError(
            "STOP: protected production, dependency, or Tranche 1 files "
            "differ from base"
        )
    if (EXPERIMENT_DIR / "results.json").exists():
        raise RuntimeError("STOP: result artifact exists before the frozen first run")
    if (EXPERIMENT_DIR / "RESULTS.md").exists():
        raise RuntimeError("STOP: result summary exists before the frozen first run")
    subprocess.run(
        [
            "git",
            "-C",
            str(ROOT),
            "cat-file",
            "-e",
            f"{PROTOCOL_SHA}:docs/pymunk-followup220-protocol.md",
        ],
        check=True,
    )
    return head


def locked_pymunk_wheel() -> tuple[str, str, int, str]:
    lock_data = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    package_records = cast(list[dict[str, object]], lock_data["package"])
    pymunk_record = next(
        record
        for record in package_records
        if record.get("name") == "pymunk" and record.get("version") == "7.2.0"
    )
    wheel_records = cast(list[dict[str, object]], pymunk_record["wheels"])
    wheel_record = next(
        record
        for record in wheel_records
        if "macosx_11_0_arm64.whl" in str(record["url"])
    )
    url = str(wheel_record["url"])
    filename = url.rsplit("/", maxsplit=1)[-1]
    locked_sha = str(wheel_record["hash"]).removeprefix("sha256:")
    size = int(cast(int, wheel_record["size"]))
    return filename, locked_sha, size, url


def runtime_manifest() -> RuntimeManifest:
    wheel_path_value = os.environ.get("PYMUNK_WHEEL_PATH")
    if not wheel_path_value:
        raise RuntimeError(
            "STOP: PYMUNK_WHEEL_PATH must name the exact locked wheel file"
        )
    wheel_path = Path(wheel_path_value).expanduser().resolve()
    if not wheel_path.is_file():
        raise RuntimeError(f"STOP: locked Pymunk wheel is missing: {wheel_path}")
    expected_filename, expected_sha, expected_size, expected_url = locked_pymunk_wheel()
    actual_sha = sha256_file(wheel_path)
    lock_match = (
        wheel_path.name == expected_filename
        and actual_sha == expected_sha
        and wheel_path.stat().st_size == expected_size
    )
    wheel = WheelIdentity(
        path=str(wheel_path),
        filename=wheel_path.name,
        sha256=actual_sha,
        lock_sha256=expected_sha,
        lock_size_bytes=expected_size,
        lock_url=expected_url,
        matches_lock=lock_match,
    )
    translated = False
    if sys.platform == "darwin":
        translated_process = subprocess.run(
            ["sysctl", "-in", "sysctl.proc_translated"],
            check=False,
            capture_output=True,
            text=True,
        )
        translated = translated_process.stdout.strip() == "1"
    version_is_pinned = (
        sys.version_info[:3] == (3, 14, 7) and pymunk.version == "7.2.0" and lock_match
    )
    native_arm64 = platform.machine() == "arm64" and not translated
    if not version_is_pinned or not native_arm64:
        raise RuntimeError(
            "STOP: pinned runtime check failed; expected Python 3.14.7, "
            "Pymunk 7.2.0, the locked arm64 wheel, and native arm64 macOS"
        )
    uv_version = subprocess.check_output(["uv", "--version"], text=True).strip()
    sw_vers = subprocess.check_output(["sw_vers"], text=True).strip()
    return RuntimeManifest(
        uname=" ".join(platform.uname()),
        os_version=sw_vers,
        architecture=platform.machine(),
        native_arm64=native_arm64,
        rosetta_translated=translated,
        python_vv=sys.version,
        python_executable=sys.executable,
        pymunk_version=pymunk.version,
        chipmunk_version=pymunk.chipmunk_version,
        pymunk_module_path=str(Path(pymunk.__file__).resolve()),
        wheel=wheel,
        uv_version=uv_version,
        uv_lock_sha256=sha256_file(ROOT / "uv.lock"),
        pygame_imported="pygame" in sys.modules,
    )


def historical_c0_record() -> dict[str, object]:
    actual_hashes: dict[str, str] = {}
    for relative_path, expected_hash in HISTORICAL_FILE_HASHES.items():
        path = ROOT / relative_path
        actual_hash = sha256_file(path)
        actual_hashes[relative_path] = actual_hash
        if actual_hash != expected_hash:
            raise RuntimeError(
                "STOP: historical Tranche 1 file changed: "
                f"{relative_path} expected={expected_hash} actual={actual_hash}"
            )

    artifact_path = ROOT / "experiments/pymunk_tranche1/results.json"
    historical_results = cast(
        dict[str, object], json.loads(artifact_path.read_text(encoding="utf-8"))
    )
    historical_gates = cast(list[dict[str, object]], historical_results["gates"])
    recorded_statuses = {
        str(gate["id"]): str(gate["status"]) for gate in historical_gates
    }
    if recorded_statuses != HISTORICAL_GATE_STATUS:
        raise RuntimeError(
            "STOP: historical C0 gate statuses differ from frozen record"
        )
    historical_cases = cast(list[dict[str, object]], historical_results["cases"])
    case_failures = sum(case.get("status") == "FAIL" for case in historical_cases)
    if len(historical_cases) != 92 or case_failures != 24:
        raise RuntimeError("STOP: historical C0 case counts differ from frozen record")
    return {
        "candidate_id": "C0_T1_HISTORICAL",
        "rerun": False,
        "protocol_sha": "89de47de86aea43d30e7dc5147c51ed5d1263b1d",
        "executable_sha": "2ba46e1dd2ab3e812ab2afaa5791521b8c48ae24",
        "results_json_sha256": HISTORICAL_FILE_HASHES[
            "experiments/pymunk_tranche1/results.json"
        ],
        "recorded_gates": recorded_statuses,
        "case_count": len(historical_cases),
        "case_failures": case_failures,
        "max_position_error_m": HISTORICAL_MAX_POSITION_ERROR_M,
        "unreflected_wheel_swap_position_mismatch_m": (
            HISTORICAL_WHEEL_SWAP_POSITION_MISMATCH_M
        ),
        "suite_count_discrepancy": {
            "RESULTS.md": "88 passed / 25 failed",
            "historical_PR_description": "87 passed / 26 xfailed",
            "status": "UNKNOWN_UNRECONCILED",
        },
        "file_sha256": actual_hashes,
    }


def evaluate_case(
    candidate_id: CandidateId,
    label: str,
    command: tuple[float, float],
    heading: float,
    amplitude: float,
    microsteps: int,
) -> CaseResult:
    request = (amplitude * command[0], amplitude * command[1])
    probe = PymunkFollowupProbe(
        candidate_id, microsteps=microsteps, heading_rad=heading
    )
    endpoint = probe.advance(request)
    expected_position, expected_heading = differential_drive_arc(
        (0.0, 0.0),
        heading,
        endpoint.actual_shaft_deltas_rad[0],
        endpoint.actual_shaft_deltas_rad[1],
    )
    position_error = math.dist(endpoint.position_m, expected_position)
    yaw_error = abs(endpoint.heading_rad - expected_heading)
    passed = position_error <= POSITION_TOLERANCE_M and yaw_error <= YAW_TOLERANCE_RAD
    return CaseResult(
        case_id=(
            f"{candidate_id}:{label}:h={heading:.17g}:"
            f"amp={amplitude:.2f}:n={microsteps}"
        ),
        candidate_id=candidate_id,
        command_label=label,
        requested_wheel_deltas_rad=request,
        clipped_actual_shaft_deltas_rad=endpoint.actual_shaft_deltas_rad,
        heading_start_rad=heading,
        amplitude=amplitude,
        microsteps=microsteps,
        dt_seconds=DT_SECONDS,
        elapsed_seconds=probe.elapsed_seconds,
        expected_position_m=expected_position,
        expected_unwrapped_heading_rad=expected_heading,
        actual_position_m=endpoint.position_m,
        actual_unwrapped_heading_rad=endpoint.heading_rad,
        position_error_m=position_error,
        yaw_error_rad=yaw_error,
        endpoint_velocity_m_s=endpoint.velocity_m_s,
        endpoint_angular_velocity_rad_s=endpoint.angular_velocity_rad_s,
        engine_step_count=endpoint.engine_step_count,
        status="PASS" if passed else "FAIL",
    )


def evaluate_core_matrix(candidate_id: CandidateId) -> tuple[CaseResult, ...]:
    cases: list[CaseResult] = []
    for microsteps in (10, 20):
        for label, command in CORE_ACTIONS:
            for heading in HEADINGS:
                for amplitude in AMPLITUDES:
                    cases.append(
                        evaluate_case(
                            candidate_id,
                            label,
                            command,
                            heading,
                            amplitude,
                            microsteps,
                        )
                    )
    return tuple(cases)


def case_index(
    cases: tuple[CaseResult, ...],
) -> dict[tuple[str, float, float, int], CaseResult]:
    return {
        (
            case.command_label,
            case.heading_start_rad,
            case.amplitude,
            case.microsteps,
        ): case
        for case in cases
    }


def _check(
    check_id: str,
    position_error_m: float,
    yaw_error_rad: float,
    *,
    include_position: bool = True,
    include_yaw: bool = True,
) -> CheckResult:
    passed = (not include_position or position_error_m <= POSITION_TOLERANCE_M) and (
        not include_yaw or yaw_error_rad <= YAW_TOLERANCE_RAD
    )
    return CheckResult(
        check_id=check_id,
        status="PASS" if passed else "FAIL",
        measurements={
            "position_error_m": position_error_m,
            "yaw_error_rad": yaw_error_rad,
        },
    )


def evaluate_metamorphic_checks(
    cases: tuple[CaseResult, ...],
) -> tuple[CheckResult, ...]:
    indexed = case_index(cases)
    checks: list[CheckResult] = []
    for microsteps in (10, 20):
        for heading in HEADINGS:
            for amplitude in AMPLITUDES:
                forward = indexed[("FORWARD", heading, amplitude, microsteps)]
                reverse = indexed[("REVERSE", heading, amplitude, microsteps)]
                reverse_error = math.dist(
                    reverse.actual_position_m,
                    (-forward.actual_position_m[0], -forward.actual_position_m[1]),
                )
                reverse_yaw_error = abs(
                    (reverse.actual_unwrapped_heading_rad - heading)
                    + (forward.actual_unwrapped_heading_rad - heading)
                )
                checks.append(
                    _check(
                        f"equal-wheel-reversal:n={microsteps}:h={heading:.17g}:a={amplitude:.2f}",
                        reverse_error,
                        reverse_yaw_error,
                    )
                )

                negative_yaw = indexed[
                    ("ARC_NEGATIVE_YAW", heading, amplitude, microsteps)
                ]
                positive_yaw = indexed[
                    ("ARC_POSITIVE_YAW", heading, amplitude, microsteps)
                ]
                negative_local = body_frame_displacement(
                    heading, negative_yaw.actual_position_m
                )
                positive_local = body_frame_displacement(
                    heading, positive_yaw.actual_position_m
                )
                swap_reflection_error = math.hypot(
                    negative_local[0] - positive_local[0],
                    negative_local[1] + positive_local[1],
                )
                swap_yaw_error = abs(
                    (negative_yaw.actual_unwrapped_heading_rad - heading)
                    + (positive_yaw.actual_unwrapped_heading_rad - heading)
                )
                checks.append(
                    _check(
                        f"wheel-swap-body-reflection:n={microsteps}:h={heading:.17g}:a={amplitude:.2f}",
                        swap_reflection_error,
                        swap_yaw_error,
                    )
                )

                for spin_label in ("SPIN_POSITIVE", "SPIN_NEGATIVE"):
                    spin = indexed[(spin_label, heading, amplitude, microsteps)]
                    checks.append(
                        _check(
                            f"{spin_label.lower()}-center:n={microsteps}:h={heading:.17g}:a={amplitude:.2f}",
                            math.hypot(*spin.actual_position_m),
                            0.0,
                            include_yaw=False,
                        )
                    )

        for label, _ in CORE_ACTIONS:
            for amplitude in AMPLITUDES:
                base = indexed[(label, 0.0, amplitude, microsteps)]
                base_displacement = base.actual_position_m
                base_yaw_delta = base.actual_unwrapped_heading_rad
                for heading in HEADINGS[1:]:
                    rotated = indexed[(label, heading, amplitude, microsteps)]
                    expected_displacement = rotate_displacement(
                        heading, base_displacement
                    )
                    position_error = math.dist(
                        rotated.actual_position_m, expected_displacement
                    )
                    yaw_error = abs(
                        (rotated.actual_unwrapped_heading_rad - heading)
                        - base_yaw_delta
                    )
                    checks.append(
                        _check(
                            f"rotated-heading:{label}:n={microsteps}:h={heading:.17g}:a={amplitude:.2f}",
                            position_error,
                            yaw_error,
                        )
                    )
    return tuple(checks)


def evaluate_known_vectors(
    cases: tuple[CaseResult, ...],
) -> tuple[CheckResult, ...]:
    indexed = case_index(cases)
    tolerance = POSITION_TOLERANCE_M
    forward = indexed[("FORWARD", 0.0, 1.0, 10)]
    expected_travel = WHEEL_RADIUS_M * MAX_WHEEL_DELTA_RAD
    forward_position_error = math.hypot(
        forward.actual_position_m[0] - expected_travel,
        forward.actual_position_m[1],
    )
    forward_yaw_error = abs(forward.actual_unwrapped_heading_rad)

    positive_spin = indexed[("SPIN_POSITIVE", 0.0, 1.0, 10)]
    negative_spin = indexed[("SPIN_NEGATIVE", 0.0, 1.0, 10)]
    expected_spin_yaw = WHEEL_RADIUS_M * (2.0 * MAX_WHEEL_DELTA_RAD) / TRACK_WIDTH_M
    spin_checks = (
        _check(
            "known-positive-spin",
            math.hypot(*positive_spin.actual_position_m),
            abs(positive_spin.actual_unwrapped_heading_rad - expected_spin_yaw),
        ),
        _check(
            "known-negative-spin",
            math.hypot(*negative_spin.actual_position_m),
            abs(negative_spin.actual_unwrapped_heading_rad + expected_spin_yaw),
        ),
    )
    zero = indexed[("ZERO", 0.0, 1.0, 10)]
    zero_check = _check(
        "known-zero",
        math.hypot(*zero.actual_position_m),
        abs(zero.actual_unwrapped_heading_rad),
    )
    forward_check = _check(
        "known-full-forward",
        forward_position_error,
        forward_yaw_error,
    )
    if tolerance != POSITION_TOLERANCE_M:
        raise AssertionError("known-vector position tolerance drifted")
    return (forward_check, *spin_checks, zero_check)


def evaluate_clipping_checks(candidate_id: CandidateId) -> tuple[CheckResult, ...]:
    checks: list[CheckResult] = []
    for label, command in CLIPPING_ACTIONS:
        expected = independent_clipped_action(command)
        for heading in HEADINGS:
            probe = PymunkFollowupProbe(
                candidate_id, microsteps=10, heading_rad=heading
            )
            endpoint = probe.advance(command)
            clip_error = max(
                abs(endpoint.actual_shaft_deltas_rad[0] - expected[0]),
                abs(endpoint.actual_shaft_deltas_rad[1] - expected[1]),
            )
            passed = (
                clip_error <= CLIP_TOLERANCE_RAD
                and endpoint.engine_step_count == 10
                and probe.elapsed_seconds == DT_SECONDS
            )
            checks.append(
                CheckResult(
                    check_id=f"{candidate_id}:{label}:h={heading:.17g}",
                    status="PASS" if passed else "FAIL",
                    measurements={
                        "max_clip_error_rad": clip_error,
                        "engine_step_count": endpoint.engine_step_count,
                        "elapsed_seconds": probe.elapsed_seconds,
                    },
                )
            )
    return tuple(checks)


def evaluate_tiny_checks(candidate_id: CandidateId) -> tuple[CheckResult, ...]:
    checks: list[CheckResult] = []
    for label, command in TINY_ACTIONS:
        for heading in HEADINGS:
            probe = PymunkFollowupProbe(
                candidate_id, microsteps=10, heading_rad=heading
            )
            endpoint = probe.advance(command)
            exact_actual = endpoint.actual_shaft_deltas_rad == command
            finite_endpoint = all(
                math.isfinite(value)
                for value in (
                    *endpoint.position_m,
                    endpoint.heading_rad,
                    *endpoint.velocity_m_s,
                    endpoint.angular_velocity_rad_s,
                )
            )
            passed = (
                exact_actual
                and finite_endpoint
                and endpoint.engine_step_count == 10
                and probe.elapsed_seconds == DT_SECONDS
            )
            checks.append(
                CheckResult(
                    check_id=f"{candidate_id}:{label}:h={heading:.17g}",
                    status="PASS" if passed else "FAIL",
                    measurements={
                        "shaft_deltas_exact": exact_actual,
                        "endpoint_finite": finite_endpoint,
                        "engine_step_count": endpoint.engine_step_count,
                        "elapsed_seconds": probe.elapsed_seconds,
                    },
                )
            )
    return tuple(checks)


def _invalid_actions() -> tuple[object, ...]:
    return (
        (),
        (1.0,),
        (1.0, 2.0, 3.0),
        "12",
        b"12",
        ("bad", 0.0),
        (True, 0.0),
        (0.0, False),
        (math.nan, 0.0),
        (0.0, math.nan),
        (math.inf, 0.0),
        (0.0, math.inf),
        (-math.inf, 0.0),
        (0.0, -math.inf),
    )


def evaluate_invalid_checks(candidate_id: CandidateId) -> tuple[CheckResult, ...]:
    checks: list[CheckResult] = []
    for index, raw_action in enumerate(_invalid_actions()):
        probe = PymunkFollowupProbe(candidate_id, microsteps=10)
        try:
            probe.advance(cast(tuple[object, ...], raw_action))
        except ValueError:
            rejected = True
        else:
            rejected = False
        unchanged = (
            probe.elapsed_seconds == 0.0
            and probe.engine_step_count == 0
            and tuple(probe.body.position) == (0.0, 0.0)
            and float(probe.body.angle) == 0.0
        )
        checks.append(
            CheckResult(
                check_id=f"{candidate_id}:invalid-{index}:{type(raw_action).__name__}",
                status="PASS" if rejected and unchanged else "FAIL",
                measurements={
                    "input_repr": repr(raw_action),
                    "rejected": rejected,
                    "unchanged_without_engine_step": unchanged,
                },
            )
        )
    return tuple(checks)


def evaluate_encoder_checks(candidate_id: CandidateId) -> tuple[CheckResult, ...]:
    quantum = ENCODER_QUANTUM_RAD
    half_inputs = (
        math.nextafter(0.5 * quantum, 0.0),
        math.nextafter(0.5 * quantum, math.inf),
        0.5 * quantum,
        math.nextafter(-0.5 * quantum, 0.0),
        math.nextafter(-0.5 * quantum, -math.inf),
        -0.5 * quantum,
    )
    expected = (0.0, quantum, quantum, 0.0, -quantum, -quantum)
    return tuple(
        CheckResult(
            check_id=f"{candidate_id}:encoder-half-quantum:{index}",
            status="PASS" if quantize_encoder(value) == expected[index] else "FAIL",
            measurements={
                "input_rad": value,
                "output_rad": quantize_encoder(value),
                "expected_rad": expected[index],
            },
        )
        for index, value in enumerate(half_inputs)
    )


def evaluate_convergence_checks(
    cases: tuple[CaseResult, ...],
) -> tuple[CheckResult, ...]:
    indexed = case_index(cases)
    checks: list[CheckResult] = []
    for label, _ in CORE_ACTIONS:
        for heading in HEADINGS:
            for amplitude in AMPLITUDES:
                ten = indexed[(label, heading, amplitude, 10)]
                twenty = indexed[(label, heading, amplitude, 20)]
                position_difference = math.dist(
                    ten.actual_position_m, twenty.actual_position_m
                )
                yaw_difference = abs(
                    ten.actual_unwrapped_heading_rad
                    - twenty.actual_unwrapped_heading_rad
                )
                passed = (
                    position_difference <= CONVERGENCE_POSITION_TOLERANCE_M
                    and yaw_difference <= CONVERGENCE_YAW_TOLERANCE_RAD
                )
                checks.append(
                    CheckResult(
                        check_id=(
                            f"{ten.candidate_id}:microstep-convergence:{label}:"
                            f"h={heading:.17g}:a={amplitude:.2f}"
                        ),
                        status="PASS" if passed else "FAIL",
                        measurements={
                            "position_difference_m": position_difference,
                            "yaw_difference_rad": yaw_difference,
                        },
                    )
                )
    return tuple(checks)


def canonical_trace(candidate_id: CandidateId) -> bytes:
    schedule = tuple(command for _, command in SCHEDULE_ACTIONS) * 142 + tuple(
        command for _, command in SCHEDULE_ACTIONS[:6]
    )
    probe = PymunkFollowupProbe(candidate_id, microsteps=10)
    rows: list[dict[str, object]] = []
    for index, command in enumerate(schedule):
        endpoint = probe.advance(command)
        rows.append(
            {
                "action_index": index,
                "candidate_id": candidate_id,
                "requested_wheel_deltas_rad": list(command),
                "clipped_actual_shaft_deltas_rad": list(
                    endpoint.actual_shaft_deltas_rad
                ),
                "endpoint_x_m": endpoint.position_m[0],
                "endpoint_y_m": endpoint.position_m[1],
                "unwrapped_heading_rad": endpoint.heading_rad,
                "endpoint_vx_m_s": endpoint.velocity_m_s[0],
                "endpoint_vy_m_s": endpoint.velocity_m_s[1],
                "endpoint_angular_velocity_rad_s": (endpoint.angular_velocity_rad_s),
            }
        )
    return json.dumps(
        rows,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def evaluate_repeatability(candidate_id: CandidateId) -> RepeatabilityResult:
    traces = tuple(canonical_trace(candidate_id) for _ in range(10))
    hashes = tuple(sha256_bytes(trace) for trace in traces)
    return RepeatabilityResult(
        schedule=(
            "(ZERO, FORWARD, REVERSE, SPIN_POSITIVE, SPIN_NEGATIVE, "
            "ARC_NEGATIVE_YAW, ARC_POSITIVE_YAW)*142 + first 6"
        ),
        intervals=1000,
        independent_runs=len(traces),
        trace_sha256=hashes,
        byte_identical=all(trace == traces[0] for trace in traces[1:]),
    )


def _gate(
    gate_id: str,
    threshold: str,
    statuses: tuple[str, ...],
    case_ids: tuple[str, ...] = (),
    metrics: dict[str, str | int | float | bool] | None = None,
) -> GateResult:
    return GateResult(
        gate_id=gate_id,
        threshold=threshold,
        status="PASS" if all(status == "PASS" for status in statuses) else "FAIL",
        case_ids=case_ids,
        metrics={} if metrics is None else metrics,
    )


def _max_case_errors(cases: tuple[CaseResult, ...]) -> tuple[float, float]:
    return (
        max((case.position_error_m for case in cases), default=0.0),
        max((case.yaw_error_rad for case in cases), default=0.0),
    )


def evaluate_candidate(candidate_id: CandidateId) -> CandidateResult:
    cases = evaluate_core_matrix(candidate_id)
    metamorphic = evaluate_metamorphic_checks(cases)
    known_vectors = evaluate_known_vectors(cases)
    clipping = evaluate_clipping_checks(candidate_id)
    tiny = evaluate_tiny_checks(candidate_id)
    invalid = evaluate_invalid_checks(candidate_id)
    encoder = evaluate_encoder_checks(candidate_id)
    convergence = evaluate_convergence_checks(cases)
    repeatability = evaluate_repeatability(candidate_id)

    max_position_error, max_yaw_error = _max_case_errors(cases)
    free_space_gate = _gate(
        "free-space-calibration",
        "all 216 N=10/N=20 base cells: position <=1e-5 m and unwrapped yaw <=1e-5 rad",
        tuple(case.status for case in cases),
        tuple(case.case_id for case in cases),
        {
            "case_count": len(cases),
            "failed_case_count": sum(case.status == "FAIL" for case in cases),
            "max_position_error_m": max_position_error,
            "max_yaw_error_rad": max_yaw_error,
        },
    )
    known_gate = _gate(
        "known-vectors",
        (
            "dedicated full forward, both full spins, and zero: position/yaw "
            "<=1e-5 in declared units; independent of free-space gate"
        ),
        tuple(check.status for check in known_vectors),
        tuple(
            case.case_id
            for case in cases
            if case.microsteps == 10
            and case.heading_start_rad == 0.0
            and case.amplitude == 1.0
            and case.command_label
            in ("ZERO", "FORWARD", "SPIN_POSITIVE", "SPIN_NEGATIVE")
        ),
        {
            "dedicated_check_count": len(known_vectors),
            "passed_check_count": sum(
                check.status == "PASS" for check in known_vectors
            ),
        },
    )
    metamorphic_gate = _gate(
        "symmetry",
        (
            "reversal, wheel-swap body-frame reflection/opposite yaw, rotated "
            "heading, and spin-centre errors <=1e-5 m/rad as applicable"
        ),
        tuple(check.status for check in metamorphic),
        tuple(case.case_id for case in cases),
        {
            "check_count": len(metamorphic),
            "failed_check_count": sum(check.status == "FAIL" for check in metamorphic),
        },
    )
    convergence_gate = _gate(
        "microstep-convergence",
        "all 108 paired base cells: N=10 vs N=20 position <=1e-4 m and yaw <=1e-4 rad",
        tuple(check.status for check in convergence),
        tuple(case.case_id for case in cases if case.microsteps == 10),
        {
            "check_count": len(convergence),
            "failed_check_count": sum(check.status == "FAIL" for check in convergence),
        },
    )
    core_timing_statuses = tuple(
        "PASS"
        if case.engine_step_count == case.microsteps
        and case.elapsed_seconds == DT_SECONDS
        else "FAIL"
        for case in cases
    )
    action_gate = _gate(
        "action-timing",
        (
            "accepted command: exact N engine steps and 0.1 s; independent "
            "clipping <=1e-12 rad; malformed/non-finite inputs reject before steps"
        ),
        (
            *core_timing_statuses,
            *(check.status for check in clipping),
            *(check.status for check in tiny),
            *(check.status for check in invalid),
        ),
        tuple(case.case_id for case in cases),
        {
            "core_case_count": len(cases),
            "clipping_check_count": len(clipping),
            "tiny_check_count": len(tiny),
            "invalid_check_count": len(invalid),
            "clip_tolerance_rad": CLIP_TOLERANCE_RAD,
        },
    )
    repeatability_gate = _gate(
        "reset-repeatability",
        (
            "10 independently reset 1000-command traces have byte-identical "
            "canonical JSON bytes and equal SHA-256"
        ),
        ("PASS" if repeatability.byte_identical else "FAIL",),
        (),
        {
            "intervals_per_run": repeatability.intervals,
            "independent_runs": repeatability.independent_runs,
            "byte_identical": repeatability.byte_identical,
        },
    )
    encoder_gate = _gate(
        "encoder-quantization",
        (
            "six q=pi/180 half-quantum below/above/exact cases round nearest; "
            "exact ties away from zero"
        ),
        tuple(check.status for check in encoder),
        (),
        {"check_count": len(encoder)},
    )
    runtime_violations = runtime_source_violations()
    pygame_imported = "pygame" in sys.modules
    gates = (
        GateResult(
            gate_id="headless-runtime",
            threshold=(
                "Python 3.14.7; Pymunk 7.2.0 and locked native arm64 wheel; "
                "no Pygame/GUI/event/sleep/wall-clock/RNG coupling"
            ),
            status=(
                "PASS" if not pygame_imported and not runtime_violations else "FAIL"
            ),
            case_ids=(),
            metrics={
                "pygame_imported": pygame_imported,
                "source_violations": ", ".join(runtime_violations),
            },
        ),
        action_gate,
        free_space_gate,
        known_gate,
        metamorphic_gate,
        convergence_gate,
        repeatability_gate,
        encoder_gate,
    )
    return CandidateResult(
        candidate_id=candidate_id,
        cases=cases,
        metamorphic_checks=metamorphic,
        known_vector_checks=known_vectors,
        clipping_checks=clipping,
        tiny_input_checks=tiny,
        invalid_input_checks=invalid,
        encoder_checks=encoder,
        convergence_checks=convergence,
        repeatability=repeatability,
        gates=gates,
    )


def evaluate_preservation_gate(c0: dict[str, object]) -> GateResult:
    project_data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project_section = cast(dict[str, object], project_data["project"])
    direct_dependencies = cast(list[str], project_section.get("dependencies", []))
    dependency_groups = cast(
        dict[str, list[str]], project_data.get("dependency-groups", {})
    )
    pymunk_is_optional = not any(
        dependency.lower().startswith("pymunk") for dependency in direct_dependencies
    ) and "pymunk==7.2.0" in dependency_groups.get("pymunk-probe", [])
    c0_hashes = cast(dict[str, str], c0["file_sha256"])
    c0_files_match = c0_hashes == HISTORICAL_FILE_HASHES
    protected_diff = subprocess.run(
        [
            "git",
            "-C",
            str(ROOT),
            "diff",
            "--quiet",
            BASE_SHA,
            "HEAD",
            "--",
            "src",
            "tests",
            "pyproject.toml",
            "uv.lock",
            "experiments/pymunk_tranche1",
        ],
        check=False,
    )
    production_unchanged = protected_diff.returncode == 0
    production_imports = experiment_production_imports()
    passed = (
        pymunk_is_optional
        and c0_files_match
        and production_unchanged
        and not production_imports
    )
    return GateResult(
        gate_id="preservation-and-isolation",
        threshold=(
            "Tranche 1 frozen hashes unchanged; production src/tests, pyproject.toml, "
            "and uv.lock byte-identical to base; Pymunk only in optional pymunk-probe"
        ),
        status="PASS" if passed else "FAIL",
        case_ids=(),
        metrics={
            "c0_files_match": c0_files_match,
            "production_unchanged": production_unchanged,
            "pymunk_is_optional": pymunk_is_optional,
            "direct_production_imports": ", ".join(production_imports),
        },
    )


def _all_gate_statuses(
    candidates: tuple[CandidateResult, ...], global_gate: GateResult
) -> tuple[str, ...]:
    candidate_statuses = tuple(
        gate.status for candidate in candidates for gate in candidate.gates
    )
    return (global_gate.status, *candidate_statuses)


def _summary_markdown(
    *,
    executable_sha: str,
    runtime: RuntimeManifest,
    c0: dict[str, object],
    candidates: tuple[CandidateResult, ...],
    global_gate: GateResult,
    verdict: str,
    results_json_sha256: str,
) -> str:
    c0_cases = cast(int, c0["case_count"])
    c0_failures = cast(int, c0["case_failures"])
    c0_max_position = cast(float, c0["max_position_error_m"])
    replay_worktree = f"/tmp/pymunk220-reproduction-{executable_sha[:12]}"
    replay_results = f"{replay_worktree}-results"
    wheel_path = shlex.quote(runtime.wheel.path)
    wheel_directory = shlex.quote(str(Path(runtime.wheel.path).parent))
    lines = [
        "# Pymunk #220 corrected empty-space calibration results",
        "",
        f"- Authorized base SHA: `{BASE_SHA}`",
        f"- Protocol SHA: `{PROTOCOL_SHA}`",
        f"- Result-free executable/run SHA: `{executable_sha}`",
        (
            "- Scope: isolated, headless empty-space engineering diagnostic; "
            "no organism, production, or contact run."
        ),
        (
            f"- Runtime: Python `{runtime.python_vv.splitlines()[0]}`, "
            f"Pymunk `{runtime.pymunk_version}`, "
            f"Chipmunk `{runtime.chipmunk_version}`."
        ),
        (
            f"- Platform: `{runtime.uname}`; architecture "
            f"`{runtime.architecture}`; native arm64 `{runtime.native_arm64}`; "
            f"Rosetta `{runtime.rosetta_translated}`."
        ),
        (
            f"- Wheel: `{runtime.wheel.path}`; SHA-256 "
            f"`{runtime.wheel.sha256}`; lock match `{runtime.wheel.matches_lock}`."
        ),
        f"- uv: `{runtime.uv_version}`; `uv.lock` SHA-256 `{runtime.uv_lock_sha256}`.",
        f"- `results.json` SHA-256: `{results_json_sha256}`.",
        "",
        "## Candidate comparison",
        "",
        (
            "| Candidate | Role | Cases | Case FAIL | Maximum position error (m) | "
            "Maximum yaw error (rad) | Result |"
        ),
        "|---|---|---:|---:|---:|---:|---|",
        (
            "| C0_T1_HISTORICAL | Recorded-only immutable comparator | "
            f"{c0_cases} | {c0_failures} | {c0_max_position:.17g} | "
            "not recomputed | historical FAIL preserved |"
        ),
    ]
    for candidate in candidates:
        max_position_error, max_yaw_error = _max_case_errors(candidate.cases)
        fail_count = sum(case.status == "FAIL" for case in candidate.cases)
        gate_failure = any(gate.status == "FAIL" for gate in candidate.gates)
        lines.append(
            (
                f"| {candidate.candidate_id} | New fixed candidate | "
                f"{len(candidate.cases)} | {fail_count} | "
                f"{max_position_error:.17g} | {max_yaw_error:.17g} | "
                f"{'FAIL' if gate_failure else 'PASS'} |"
            )
        )
    lines.extend(
        [
            "",
            (
                "C0 was not re-executed. Its three failed gates, 24 failed "
                "position cases, original known-vectors aggregate FAIL, and "
                "erroneous unreflected wheel-swap comparison remain historical."
            ),
            "",
            "## Frozen gate results",
            "",
            f"| Global gate | {global_gate.status} | {global_gate.threshold} |",
            "|---|---|---|",
        ]
    )
    for candidate in candidates:
        lines.append("")
        lines.append(f"### {candidate.candidate_id}")
        lines.append("")
        lines.extend(
            [
                "| Gate | Result | Frozen criterion |",
                "|---|---|---|",
            ]
        )
        for gate in candidate.gates:
            lines.append(f"| {gate.gate_id} | {gate.status} | {gate.threshold} |")
        lines.append(
            f"Individual base matrix: {len(candidate.cases)} cases; "
            f"{sum(case.status == 'PASS' for case in candidate.cases)} PASS / "
            f"{sum(case.status == 'FAIL' for case in candidate.cases)} FAIL."
        )
        lines.append(
            (
                f"Repeatability: "
                f"{'PASS' if candidate.repeatability.byte_identical else 'FAIL'}; "
                f"{candidate.repeatability.independent_runs} resets x "
                f"{candidate.repeatability.intervals} commands; "
                f"trace SHA-256 `{candidate.repeatability.trace_sha256[0]}`."
            )
        )
    lines.extend(
        [
            "",
            "## Independent vector and symmetry definitions",
            "",
            (
                "Analytic position errors are Euclidean norms in metres; yaw "
                "errors are absolute unwrapped differences in radians. Wheel "
                "exchange is checked in the initial body frame: forward "
                "component preserved, lateral component negated, yaw increment "
                "negated. The known-vector gate uses only its dedicated "
                "forward/spin/zero measurements and is independent of the global "
                "free-space gate."
            ),
            "",
            "## Claims and limitations",
            "",
            (
                "- **VERIFIED:** only the two declared kinematic update candidates, "
                "listed fixed commands, pinned runtime, and frozen numerical gates."
            ),
            (
                "- **INFERENCE:** centered velocity updates change the numerical "
                "actuator/engine coupling examined here; no physical motor, "
                "traction, collision, or contact model was tested."
            ),
            (
                "- **UNKNOWN:** hardware fidelity, collision/contact behavior, "
                "engineering savings, other platforms, and production performance."
            ),
            "",
            f"## Verdict: {verdict}",
            "",
            (
                "No contact/room work, migration, D/EXP record, or successor task "
                "is authorized. Passing empty-space calibration alone does not "
                "establish that a later contact tranche is warranted."
            ),
            "",
            "## Reproduction",
            "",
            "```sh",
            (f"git worktree add --detach {replay_worktree} {executable_sha}"),
            f"cd {replay_worktree}",
            f"mkdir -p {wheel_directory}",
            (
                f"curl --fail --location {shlex.quote(runtime.wheel.lock_url)} "
                f"--output {wheel_path}"
            ),
            (
                f"printf '%s  %s\\n' {shlex.quote(runtime.wheel.sha256)} "
                f"{wheel_path} | shasum -a 256 -c -"
            ),
            "uv sync --frozen --python 3.14.7 --group pymunk-probe",
            (
                f"PYMUNK_WHEEL_PATH={wheel_path} uv run --frozen "
                "--group pymunk-probe python -m "
                "experiments.pymunk_followup220.run_diagnostic "
                f"--replay-frozen --output-dir {replay_results}"
            ),
            (
                f"PYMUNK_WHEEL_PATH={wheel_path} uv run --frozen "
                "--group pymunk-probe pytest -q "
                "experiments/pymunk_followup220/test_followup.py"
            ),
            "```",
            "",
            (
                "The runner requires a clean checkout at the result-free "
                "executable SHA, on the authorized branch, with unchanged "
                "`origin/main`; `PYMUNK_WHEEL_PATH` must name the exact arm64 "
                "wheel in `uv.lock`. All per-case rows, checks, trace hashes, "
                "and detached checksums are in adjacent artifacts."
            ),
            "",
            "## Artifacts",
            "",
            (
                "- `experiments/pymunk_followup220/results.json` — complete "
                "candidate, case, and gate records."
            ),
            (
                "- `experiments/pymunk_followup220/SHA256SUMS` — detached "
                "JSON/Markdown hashes."
            ),
            (
                "- `experiments/pymunk_followup220/VALIDATION.md` — test, "
                "lint, and typing commands/results."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def run_diagnostic(
    output_dir: Path, *, replay_frozen: bool = False
) -> dict[str, object]:
    executable_sha = require_clean_frozen_checkout(replay_frozen=replay_frozen)
    runtime = runtime_manifest()
    c0 = historical_c0_record()
    global_gate = evaluate_preservation_gate(c0)
    candidate_results = tuple(evaluate_candidate(candidate) for candidate in CANDIDATES)
    statuses = _all_gate_statuses(candidate_results, global_gate)
    verdict = "REVISE" if any(status == "FAIL" for status in statuses) else "STOP"

    output: dict[str, object] = {
        "schema_version": 1,
        "protocol_sha": PROTOCOL_SHA,
        "authorized_base_sha": BASE_SHA,
        "executable_sha": executable_sha,
        "runtime_manifest": asdict(runtime),
        "fixture": {
            "units": {"length": "m", "time": "s", "angle": "rad"},
            "body_type": "dynamic",
            "body_dimensions_m": [BODY_LENGTH_M, BODY_WIDTH_M],
            "fixture_mass_kg": FIXTURE_MASS_KG,
            "fixture_moment_kg_m2": FIXTURE_MOMENT_KG_M2,
            "wheel_radius_m": WHEEL_RADIUS_M,
            "track_width_m": TRACK_WIDTH_M,
            "action_interval_seconds": DT_SECONDS,
            "maximum_signed_wheel_delta_rad": MAX_WHEEL_DELTA_RAD,
            "microsteps": {"N10_h_seconds": 0.01, "N20_h_seconds": 0.005},
            "space_settings": {
                "threaded": False,
                "gravity": [0.0, 0.0],
                "damping": 1.0,
                "iterations": 10,
                "collision_slop_m": 0.0001,
                "collision_bias": 0.001797010299914434,
                "collision_persistence": 3,
                "sleep_time_threshold": "infinity",
                "idle_speed_threshold": 0.0,
                "shapes": 0,
            },
            "engine_actuator_ownership": (
                "ideal clipped shaft deltas determine requested body twist; "
                "candidate sets velocity only; Pymunk Space.step advances body pose"
            ),
        },
        "historical_C0_comparator": c0,
        "global_gates": [asdict(global_gate)],
        "candidates": [asdict(candidate) for candidate in candidate_results],
        "verdict": verdict,
        "verdict_rule": (
            "REVISE if any frozen new/global gate fails; otherwise STOP after "
            "this authorized diagnostic with no inferred successor authority"
        ),
        "claims": {
            "VERIFIED": (
                "only listed candidate fixtures, measurements, runtime, and gates"
            ),
            "INFERENCE": (
                "the comparison diagnoses actuator/update-order integration "
                "behavior in empty space"
            ),
            "UNKNOWN": (
                "contact behavior, hardware fidelity, engineering savings, "
                "other platforms, production performance"
            ),
        },
        "artifact_paths": {
            "json": "experiments/pymunk_followup220/results.json",
            "markdown": "experiments/pymunk_followup220/RESULTS.md",
            "sha256sums": "experiments/pymunk_followup220/SHA256SUMS",
            "validation": "experiments/pymunk_followup220/VALIDATION.md",
        },
        "canonical_trace_fields": list(CANONICAL_TRACE_FIELDS),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "results.json"
    markdown_path = output_dir / "RESULTS.md"
    sums_path = output_dir / "SHA256SUMS"
    json_text = json.dumps(output, indent=2, sort_keys=True, allow_nan=False) + "\n"
    json_path.write_text(json_text, encoding="utf-8")
    json_sha = sha256_file(json_path)
    markdown = _summary_markdown(
        executable_sha=executable_sha,
        runtime=runtime,
        c0=c0,
        candidates=candidate_results,
        global_gate=global_gate,
        verdict=verdict,
        results_json_sha256=json_sha,
    )
    markdown_path.write_text(markdown, encoding="utf-8")
    sums_path.write_text(
        f"{json_sha}  experiments/pymunk_followup220/results.json\n"
        f"{sha256_file(markdown_path)}  experiments/pymunk_followup220/RESULTS.md\n",
        encoding="utf-8",
    )
    output["generated_artifact_hashes"] = {
        "results_json_sha256": json_sha,
        "results_markdown_sha256": sha256_file(markdown_path),
        "sha256sums_sha256": sha256_file(sums_path),
    }
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=EXPERIMENT_DIR,
        help="directory for result artifacts (default: this experiment directory)",
    )
    parser.add_argument(
        "--replay-frozen",
        action="store_true",
        help=(
            "reproduce an explicitly selected result-free commit that remains "
            "an ancestor of the pushed authorized branch"
        ),
    )
    args = parser.parse_args()
    try:
        output = run_diagnostic(
            args.output_dir.expanduser().resolve(), replay_frozen=args.replay_frozen
        )
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"STOP before candidate evaluation: {error}", file=sys.stderr)
        return 2
    candidate_records = cast(list[dict[str, object]], output["candidates"])
    summary = {
        "executable_sha": output["executable_sha"],
        "protocol_sha": output["protocol_sha"],
        "verdict": output["verdict"],
        "candidate_gates": {
            str(candidate["candidate_id"]): {
                str(gate["gate_id"]): str(gate["status"])
                for gate in cast(list[dict[str, object]], candidate["gates"])
            }
            for candidate in candidate_records
        },
        "generated_artifact_hashes": output["generated_artifact_hashes"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 1 if output["verdict"] == "REVISE" else 0


if __name__ == "__main__":
    raise SystemExit(main())
