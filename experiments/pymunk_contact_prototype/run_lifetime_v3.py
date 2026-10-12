"""Explicitly gated one-shot C1/400 Pymunk lifetime plus D-058 reference.

Importing this module and running --preflight are software-only. The lifetime
pair can start only through --run-once after an exact frozen preflight approval.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import time
from collections import Counter
from pathlib import Path
from typing import BinaryIO, Callable, cast

from aweform.d045 import (
    D045_BATTERY_CAPACITY_J,
    D045_CONTACT_TOLERANCE_METRES,
    D045_DT_SECONDS,
)

from .organism_lifetime import (
    HORIZON,
    SEED,
    START_OPTIONS,
    LifetimeBudgetExceeded,
    json_bytes,
    run_once,
    run_reference_once,
)
from .run_diagnostics import _runtime_manifest

BASE_SHA = "abba4b8bb568ba13ccc5cc87740b87c6c2630ada"
EXPECTED_BRANCH = "fm/pymunk226-contact-prototype"
V3_EXECUTABLE_SHA = "a0f3b3f4fac58d88a9ea0b1b706583ce3865639d"
V3_RESULT_COMMIT = "6ee02fd0e5b43143ec8ae944c071f089ecbfc980"
V3_PROTOCOL_SHA256 = "6db905f6e6cd1501829ddb7e2f7f72bb9fc35ed1ea037ba9e12231ef1b455162"
V3_B_RESULTS = Path(
    "experiments/pymunk_contact_prototype/results-v3/contact-check/results.json"
)
V3_B_RESULTS_SHA256 = "ab70abcb5c5906fa1285ab526148a9c5c199e874c13346e217378d18c24b7513"
V3_PRIMARY_TRACE_SHA256 = (
    "ea40109ad9b6e130aeba0296c586ba72f1914564edce17e9998324ceeff42c53"
)
V3_FOCUSED_RESULTS = Path(
    "experiments/pymunk_contact_prototype/results-v3/focused-probe/focused-results.json"
)
V3_FOCUSED_RESULTS_SHA256 = (
    "6e0e4c0b7a1d99262d472eda4ee8897b7fc3943f3a46ed81f089fb3fd4945afb"
)
V3_PROTOCOL = Path("experiments/pymunk_contact_prototype/protocol-v3.md")
LIFETIME_PROTOCOL = Path("experiments/pymunk_contact_prototype/protocol-lifetime-v3.md")
EXPECTED_OUTPUT = Path("experiments/pymunk_contact_prototype/results-v3/lifetime")
PRIMARY_MICROSTEPS = 400
MAX_TRANSITIONS = HORIZON
MAX_PYMUNK_ENGINE_STEPS = MAX_TRANSITIONS * PRIMARY_MICROSTEPS
WALL_CLOCK_CAP_S = 10_800.0
PRIMARY_STAGE_CAP_S = 9_600.0
REFERENCE_STAGE_CAP_S = 600.0
FINALIZE_RESERVE_S = 120.0
MIN_FREE_DISK_BYTES = 1_000_000_000
MIN_AVAILABLE_MEMORY_BYTES = 4_000_000_000
PENETRATION_LIMIT_M = 0.001
CLEARANCE_SAMPLE_BOUND_LIMIT_M = 0.0002

# These are the exact measured physics, corpus and controller inputs whose Git
# blobs must remain byte-identical to the v3 Essential-B executable.
FROZEN_INPUTS = (
    "experiments/pymunk_contact_prototype/fixture.py",
    "experiments/pymunk_contact_prototype/cases.py",
    "experiments/pymunk_contact_prototype/run_diagnostics.py",
    "experiments/pymunk_contact_prototype/run_contact_check_v3.py",
    "experiments/pymunk_contact_prototype/protocol-v3.md",
    "src/aweform/d045.py",
    "src/aweform/d049.py",
    "src/aweform/d050.py",
    "src/aweform/d052.py",
    "src/aweform/d053.py",
    "src/aweform/d058.py",
    "src/aweform/exp001.py",
    "src/aweform/exp003.py",
    "src/aweform/exp003_seed_policy.py",
    "pyproject.toml",
    "uv.lock",
)
LIFETIME_SOURCE_PATHS = (
    "experiments/pymunk_contact_prototype/organism_lifetime.py",
    "experiments/pymunk_contact_prototype/run_lifetime_v3.py",
    "experiments/pymunk_contact_prototype/test_contact_prototype.py",
    *FROZEN_INPUTS,
)
ALLOWED_LIFETIME_DIFF = frozenset(
    {
        "experiments/pymunk_contact_prototype/organism_lifetime.py",
        "experiments/pymunk_contact_prototype/run_lifetime_v3.py",
        "experiments/pymunk_contact_prototype/protocol-lifetime-v3.md",
        "experiments/pymunk_contact_prototype/VALIDATION-lifetime-v3.md",
        "experiments/pymunk_contact_prototype/test_contact_prototype.py",
    }
)


class LifetimeStop(RuntimeError):
    """Frozen lifetime safety, provenance, or accounting boundary failed."""


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def _git_blob(commit: str, path: str) -> str:
    return _git("rev-parse", f"{commit}:{path}")


def _assert_frozen_candidate() -> tuple[str, dict[str, dict[str, object]]]:
    head = _git("rev-parse", "HEAD")
    if _git("rev-parse", "origin/main") != BASE_SHA:
        raise RuntimeError("accepted origin/main base changed; STOP")
    if _git("branch", "--show-current") != EXPECTED_BRANCH:
        raise RuntimeError("lifetime requires the authorized isolated branch")
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", V3_RESULT_COMMIT, head],
        check=True,
        capture_output=True,
        text=True,
    )
    dirty = _git("status", "--porcelain", "--untracked-files=all")
    if dirty:
        raise RuntimeError("lifetime requires a clean committed candidate")
    changed = set(
        filter(
            None,
            _git("diff", "--name-only", V3_RESULT_COMMIT, head).splitlines(),
        )
    )
    if not changed <= ALLOWED_LIFETIME_DIFF:
        unexpected = sorted(changed - ALLOWED_LIFETIME_DIFF)
        raise RuntimeError(
            "lifetime candidate contains out-of-scope changes: "
            f"{unexpected}"
        )
    frozen_blobs: dict[str, dict[str, object]] = {}
    for path in FROZEN_INPUTS:
        source_blob = _git_blob(V3_EXECUTABLE_SHA, path)
        candidate_blob = _git_blob(head, path)
        if source_blob != candidate_blob:
            raise RuntimeError(f"measured v3/controller input changed: {path}")
        frozen_blobs[path] = {
            "v3_executable_git_blob": source_blob,
            "candidate_git_blob": candidate_blob,
            "identical": True,
        }
    return head, frozen_blobs


def preflight_output(output: Path, expected: Path | None = None) -> None:
    expected_path = EXPECTED_OUTPUT if expected is None else expected
    if output.resolve() != expected_path.resolve():
        raise RuntimeError(f"lifetime output must be exactly {expected_path}")
    if output.exists():
        raise FileExistsError(
            "one-shot lifetime output exists; refuse before constructing "
            f"a world: {output}"
        )


def validate_v3_b_result(result: dict[str, object], *, result_sha256: str) -> None:
    gates = cast(dict[str, object], result.get("gates", {}))
    inventory = cast(dict[str, object], result.get("inventory", {}))
    replay = cast(dict[str, object], result.get("fresh_process_replay", {}))
    if result_sha256 != V3_B_RESULTS_SHA256:
        raise RuntimeError("committed v3 Essential-B result hash mismatch")
    if (
        result.get("executable_sha") != V3_EXECUTABLE_SHA
        or result.get("protocol_sha256") != V3_PROTOCOL_SHA256
        or result.get("essential_B_pass") is not True
        or result.get("stage1_passed") is not True
        or gates.get("essential_B") != "PASS"
        or any(value != "PASS" for value in gates.values())
    ):
        raise RuntimeError("v3 saved Essential-B provenance/gates do not pass")
    if inventory.get("total_scientific_engine_steps") != 1_912_800:
        raise RuntimeError("v3 saved B engine-step count changed")
    if _sha256_file(V3_FOCUSED_RESULTS) != V3_FOCUSED_RESULTS_SHA256:
        raise RuntimeError("saved Stage-1 probe artifact hash mismatch")
    if result.get("stage1_result_sha256") != V3_FOCUSED_RESULTS_SHA256:
        raise RuntimeError("v3 B result does not consume the accepted Stage-1 result")
    primary = Path(
        "experiments/pymunk_contact_prototype/results-v3/contact-check/primary-trace.json"
    )
    replay_path = Path(
        "experiments/pymunk_contact_prototype/results-v3/contact-check/fresh-process-replay.json"
    )
    primary_bytes, replay_bytes = primary.read_bytes(), replay_path.read_bytes()
    if (
        primary_bytes != replay_bytes
        or _sha256_bytes(primary_bytes) != V3_PRIMARY_TRACE_SHA256
        or replay.get("byte_identical") is not True
    ):
        raise RuntimeError("saved same-source fresh-process replay is not exact")


def validate_supervisor_approval(
    *,
    candidate_head: str,
    protocol_sha256: str,
    approved_head: str | None,
    approved_protocol_sha256: str | None,
    approval_receipt_sha256: str | None,
) -> str:
    if approved_head != candidate_head or approved_protocol_sha256 != protocol_sha256:
        raise RuntimeError("supervisor acceptance does not bind the frozen candidate")
    if approval_receipt_sha256 is None or not re.fullmatch(
        r"[0-9a-f]{64}", approval_receipt_sha256
    ):
        raise RuntimeError("exact supervisor acceptance receipt SHA-256 is required")
    return approval_receipt_sha256


def _live_resources() -> dict[str, object]:
    vm_stat = subprocess.check_output(["vm_stat"], text=True)
    page_size_match = re.search(r"page size of ([\d,]+) bytes", vm_stat)
    if page_size_match is None:
        raise RuntimeError("cannot parse live vm_stat page size")
    page_size = int(page_size_match.group(1).replace(",", ""))
    page_counts: dict[str, int] = {}
    for label in ("free", "inactive", "speculative", "purgeable"):
        match = re.search(rf"^Pages {label}:\s+([\d,]+)", vm_stat, re.MULTILINE)
        if match is None:
            raise RuntimeError(f"cannot parse live vm_stat {label} pages")
        page_counts[label] = int(match.group(1).replace(",", ""))
    available = sum(
        page_counts[label] for label in ("free", "inactive", "speculative")
    ) * page_size
    if available < MIN_AVAILABLE_MEMORY_BYTES:
        raise RuntimeError("less than 4 GB reclaimable memory before lifetime")
    physical = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True))
    return {
        "physical_memory_bytes": physical,
        "vm_page_size_bytes": page_size,
        "vm_page_counts": page_counts,
        "reclaimable_memory_estimate_bytes": available,
        "minimum_reclaimable_memory_bytes": MIN_AVAILABLE_MEMORY_BYTES,
        "cpu_count": os.cpu_count(),
        "load_average_1_5_15": os.getloadavg(),
    }


def preflight(output: Path) -> dict[str, object]:
    """Verify committed provenance and plan only; never constructs a world."""
    preflight_output(output)
    head, frozen_blobs = _assert_frozen_candidate()
    if _sha256_file(V3_PROTOCOL) != V3_PROTOCOL_SHA256:
        raise RuntimeError("frozen v3 protocol content hash changed")
    result_bytes = V3_B_RESULTS.read_bytes()
    result = cast(dict[str, object], json.loads(result_bytes))
    result_sha = _sha256_bytes(result_bytes)
    validate_v3_b_result(result, result_sha256=result_sha)
    protocol_sha = _sha256_file(LIFETIME_PROTOCOL)
    runtime = _runtime_manifest()
    b_runtime = cast(dict[str, object], result["runtime"])
    for key in ("python_version", "pymunk", "wheel_sha256", "uv_lock_sha256"):
        if runtime.get(key) != b_runtime.get(key):
            raise RuntimeError(f"lifetime runtime differs from accepted B: {key}")
    disk = shutil.disk_usage(output.parent)
    if disk.free < MIN_FREE_DISK_BYTES:
        raise RuntimeError("less than 1 GB free disk for one-shot lifetime artifacts")
    live_resources = _live_resources()
    return {
        "candidate_head": head,
        "lifetime_protocol_sha256": protocol_sha,
        "v3_source_sha": V3_EXECUTABLE_SHA,
        "v3_result_commit": V3_RESULT_COMMIT,
        "v3_protocol_sha256": V3_PROTOCOL_SHA256,
        "v3_results_sha256": result_sha,
        "v3_focused_result_sha256": V3_FOCUSED_RESULTS_SHA256,
        "v3_primary_replay_sha256": V3_PRIMARY_TRACE_SHA256,
        "frozen_physics_and_controller_inputs": frozen_blobs,
        "runtime": runtime,
        "lifetime_source_paths": list(LIFETIME_SOURCE_PATHS),
        "lifetime_protocol_path": LIFETIME_PROTOCOL.as_posix(),
        "validation_record_path": (
            "experiments/pymunk_contact_prototype/VALIDATION-lifetime-v3.md"
        ),
        "output_path": output.as_posix(),
        "output_paths": [
            (output / name).as_posix()
            for name in (
                "LIFETIME_STARTED",
                "pymunk-transitions.jsonl",
                "reference-transitions.jsonl",
                "lifetime-results.json",
                "FAILED-INCOMPLETE",
                "SHA256SUMS",
            )
        ],
        "output_path_absent": True,
        "disk_free_bytes": disk.free,
        "live_resources": live_resources,
        "planned": {
            "seed": SEED,
            "initial_state": START_OPTIONS,
            "room_side_m": 3.0,
            "interior_obstacles": 0,
            "primary_microsteps_per_transition": PRIMARY_MICROSTEPS,
            "primary_transitions_max": MAX_TRANSITIONS,
            "primary_pymunk_engine_steps_max": MAX_PYMUNK_ENGINE_STEPS,
            "reference_transitions_max": MAX_TRANSITIONS,
            "reference_pymunk_engine_steps": 0,
            "paired_transition_count_max": 2 * MAX_TRANSITIONS,
            "lifetime_pair_count": 1,
            "wall_clock_cap_seconds": WALL_CLOCK_CAP_S,
        },
        "resource_estimate": {
            "pymunk_runtime_from_v3_mixed_400_800_throughput_seconds": 7797.2,
            "primary_stage_cap_seconds": PRIMARY_STAGE_CAP_S,
            "reference_stage_cap_seconds": REFERENCE_STAGE_CAP_S,
            "finalization_reserve_seconds": FINALIZE_RESERVE_S,
            "remaining_runtime_variance_reserve_seconds": (
                WALL_CLOCK_CAP_S
                - PRIMARY_STAGE_CAP_S
                - REFERENCE_STAGE_CAP_S
                - 2 * FINALIZE_RESERVE_S
            ),
            "proposed_pair_wall_clock_cap_seconds": WALL_CLOCK_CAP_S,
            "estimated_peak_disk_bytes": 500_000_000,
            "required_free_disk_bytes": MIN_FREE_DISK_BYTES,
            "estimated_peak_process_memory_bytes": 2_000_000_000,
            "required_reclaimable_memory_bytes": MIN_AVAILABLE_MEMORY_BYTES,
        },
        "execution": "preflight-only; zero lifetime transitions and zero Pymunk steps",
    }


def _finite_tree(value: object) -> bool:
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(_finite_tree(k) and _finite_tree(v) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return all(_finite_tree(item) for item in value)
    return True


def validate_pymunk_transition(row: dict[str, object]) -> None:
    if not _finite_tree(row):
        raise LifetimeStop("non-finite Pymunk transition output")
    transition = int(cast(int, row["transition"]))
    if row.get("engine_steps") != transition * PRIMARY_MICROSTEPS:
        raise LifetimeStop("Pymunk transition/engine-step count mismatch")
    if row.get("reward") != 0.0 or row.get("info") != {}:
        raise LifetimeStop("organism reward/info contract changed")
    if len(cast(list[object], row.get("observation", []))) != 8:
        raise LifetimeStop("organism observation width changed")
    if (
        float(cast(float, row["max_penetration_m"])) > PENETRATION_LIMIT_M
        or float(cast(float, row["end_penetration_m"])) > PENETRATION_LIMIT_M
        or row.get("crossed_wall_or_post") is True
        or float(cast(float, row["clearance_sampling_bound_m"]))
        > CLEARANCE_SAMPLE_BOUND_LIMIT_M
    ):
        raise LifetimeStop("per-transition contact/clearance safety gate failed")
    if float(cast(float, row["impulse"])) < 0.0:
        raise LifetimeStop("negative contact impulse")
    for event in cast(list[dict[str, object]], row["contact_events"]):
        if "unknown" in cast(list[str], event["shape_pair"]):
            raise LifetimeStop("unidentified Pymunk contact shape")
        if float(cast(float, event["impulse"])) < 0.0:
            raise LifetimeStop("negative per-contact impulse")
    _validate_charger_accounting(row)


def validate_reference_transition(row: dict[str, object]) -> None:
    if not _finite_tree(row):
        raise LifetimeStop("non-finite D-058 reference transition")
    if row.get("reward") != 0.0 or row.get("info") != {}:
        raise LifetimeStop("D-058 reference reward/info contract changed")
    if len(cast(list[object], row.get("observation", []))) != 8:
        raise LifetimeStop("D-058 reference observation width changed")
    if row.get("engine_steps") != 0:
        raise LifetimeStop("analytic D-058 reference unexpectedly reports Pymunk steps")
    _validate_charger_accounting(row)


def _validate_charger_accounting(row: dict[str, object]) -> None:
    contact = row.get("paired_dock_contact_after") is True
    energy = float(cast(float, row["charge_stored_energy_j"]))
    power = float(cast(float, row["charge_actual_stored_power_w"]))
    requested = float(cast(float, row["charge_requested_stored_power_w"]))
    before = float(cast(float, row["battery_before_j"]))
    after = float(cast(float, row["battery_after_j"]))
    load = float(cast(float, row["load_energy_j"]))
    if energy < 0.0 or power < 0.0 or requested < 0.0 or load < 0.0:
        raise LifetimeStop("negative charging/accounting quantity")
    if not math.isclose(
        energy, power * D045_DT_SECONDS, rel_tol=0.0, abs_tol=1e-9
    ):
        raise LifetimeStop("stored-energy and stored-power accounting disagree")
    if energy > requested * D045_DT_SECONDS + 1e-9:
        raise LifetimeStop("actual stored energy exceeds the constitutive request")
    if contact and requested > 0.0 and energy <= 0.0:
        raise LifetimeStop("paired dock contact requested charge but transferred none")
    expected_after = min(D045_BATTERY_CAPACITY_J, max(0.0, before + energy - load))
    if not math.isclose(after, expected_after, rel_tol=0.0, abs_tol=1e-8):
        raise LifetimeStop("battery trajectory violates frozen energy accounting")
    if not contact and (energy != 0.0 or requested != 0.0):
        raise LifetimeStop(
            "charger energy/request occurred without paired dock contact"
        )
    if row.get("contact") != row.get("paired_dock_contact_after"):
        raise LifetimeStop("legacy contact label disagrees with paired dock contact")
    if bool(row["paired_dock_contact_after"]) != (
        float(cast(float, row["dock_plus_error_m"])) <= D045_CONTACT_TOLERANCE_METRES
        and float(cast(float, row["dock_minus_error_m"]))
        <= D045_CONTACT_TOLERANCE_METRES
    ):
        raise LifetimeStop(
            "paired-dock contact disagrees with the frozen two-point predicate"
        )
    if contact and row.get("charge_phase") == "OFF":
        raise LifetimeStop("paired contact reported with charger phase OFF")


def _intervals(
    rows: list[dict[str, object]],
    predicate: Callable[[dict[str, object]], bool],
) -> list[dict[str, int]]:
    check = predicate
    intervals: list[dict[str, int]] = []
    start: int | None = None
    previous = 0
    for row in rows:
        index = int(cast(int, row.get("transition", row.get("index", 0))))
        if check(row):
            if start is None:
                start = index
            previous = index
        elif start is not None:
            intervals.append({"start_transition": start, "end_transition": previous})
            start = None
    if start is not None:
        intervals.append({"start_transition": start, "end_transition": previous})
    return intervals


def summarize_charging(rows_value: object) -> dict[str, object]:
    rows = cast(list[dict[str, object]], rows_value)
    contact_rows = [row for row in rows if row.get("paired_dock_contact_after") is True]
    supplied_rows = [
        row for row in rows if float(cast(float, row["charge_stored_energy_j"])) > 0.0
    ]
    phase_counts = Counter(str(row["charge_phase"]) for row in rows)
    latch_transitions = [
        {
            "transition": int(cast(int, row.get("transition", row.get("index", 0)))),
            "from": bool(row["charger_latch_before"]),
            "to": bool(row["charger_latch_after"]),
        }
        for row in rows
        if row["charger_latch_before"] != row["charger_latch_after"]
    ]
    stored_energy = sum(
        float(cast(float, row["charge_stored_energy_j"])) for row in rows
    )
    if not contact_rows:
        classification = "charging_not_exercised_no_paired_dock_contact"
    elif stored_energy > 0.0:
        classification = "energy_transfer_observed"
    elif any(
        float(cast(float, row["charge_requested_stored_power_w"])) > 0.0
        for row in contact_rows
    ):
        classification = "paired_contact_without_requested_energy_transfer_review"
    else:
        classification = "paired_contact_without_energy_request_not_a_fault_by_itself"
    distances = [
        float(cast(float, row["station_distance_after_m"]))
        for row in rows
        if "station_distance_after_m" in row
    ]
    return {
        "classification": classification,
        "transitions": len(rows),
        "closest_station_center_distance_m": min(distances) if distances else None,
        "paired_dock_contact_transition_count": len(contact_rows),
        "paired_dock_contact_intervals": _intervals(
            rows, lambda row: row.get("paired_dock_contact_after") is True
        ),
        "energy_transfer_transition_count": len(supplied_rows),
        "energy_transfer_intervals": _intervals(
            rows,
            lambda row: float(cast(float, row["charge_stored_energy_j"])) > 0.0,
        ),
        "charge_phase_transition_counts": dict(sorted(phase_counts.items())),
        "charge_stored_energy_total_j": stored_energy,
        "charger_latch_transition_count": len(latch_transitions),
        "charger_latch_transitions": latch_transitions,
    }


def _summary_without_trace(result: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in result.items() if key != "trace"}


def _write_manifest(output: Path) -> None:
    manifest = output / "SHA256SUMS"
    files = sorted(
        path
        for path in output.iterdir()
        if path.is_file() and path.name not in {"SHA256SUMS", "LIFETIME_STARTED"}
    )
    lines = [f"{_sha256_file(path)}  {path.name}" for path in files]
    marker = output / "LIFETIME_STARTED"
    if marker.is_file():
        lines.append(f"{_sha256_file(marker)}  LIFETIME_STARTED")
    manifest.write_text("\n".join(lines) + "\n", encoding="ascii")


def run_pair_once(
    output: Path,
    *,
    approved_head: str,
    approved_protocol_sha256: str,
    approval_receipt_sha256: str,
) -> dict[str, object]:
    started = time.monotonic()
    deadline = started + WALL_CLOCK_CAP_S
    preflight_record = preflight(output)
    head = cast(str, preflight_record["candidate_head"])
    protocol_sha = cast(str, preflight_record["lifetime_protocol_sha256"])
    receipt_sha = validate_supervisor_approval(
        candidate_head=head,
        protocol_sha256=protocol_sha,
        approved_head=approved_head,
        approved_protocol_sha256=approved_protocol_sha256,
        approval_receipt_sha256=approval_receipt_sha256,
    )
    output.mkdir(parents=True, exist_ok=False)
    marker = output / "LIFETIME_STARTED"
    marker.write_text(
        f"head={head}\nprotocol_sha256={protocol_sha}\n"
        f"approval_receipt_sha256={receipt_sha}\nphase=primary\n",
        encoding="ascii",
    )
    primary_progress = output / "pymunk-transitions.jsonl"
    reference_progress = output / "reference-transitions.jsonl"
    primary_count = 0
    reference_count = 0
    current_phase = "primary"

    def writer(
        stream: BinaryIO,
        phase: str,
        validate: Callable[[dict[str, object]], None],
    ) -> Callable[[dict[str, object]], None]:
        def write_row(row: dict[str, object]) -> None:
            nonlocal primary_count, reference_count
            try:
                validate(row)
                encoded = json_bytes(row)
            except Exception as exc:
                encoded = json_bytes(
                    {
                        "unsafe_transition_repr": repr(row),
                        "validation_or_serialization_error": repr(exc),
                    }
                )
                stream.write(encoded + b"\n")
                stream.flush()
                if phase == "primary":
                    primary_count += 1
                else:
                    reference_count += 1
                raise LifetimeStop(
                    "transition failed validation; preserved diagnostic row"
                ) from exc
            stream.write(encoded + b"\n")
            stream.flush()
            if phase == "primary":
                primary_count += 1
            else:
                reference_count += 1

        return write_row

    try:
        with primary_progress.open("xb") as primary_stream:
            primary = run_once(
                microsteps=PRIMARY_MICROSTEPS,
                on_transition=writer(
                    primary_stream, "primary", validate_pymunk_transition
                ),
                deadline_monotonic=min(
                    started + PRIMARY_STAGE_CAP_S,
                    deadline
                    - REFERENCE_STAGE_CAP_S
                    - 2 * FINALIZE_RESERVE_S,
                ),
                finalize_reserve_s=FINALIZE_RESERVE_S,
            )
        current_phase = "reference"
        marker.write_text(
            f"head={head}\nprotocol_sha256={protocol_sha}\n"
            f"approval_receipt_sha256={receipt_sha}\nphase=reference\n"
            f"primary_transitions={primary_count}\n"
            f"primary_engine_steps={primary_count * PRIMARY_MICROSTEPS}\n",
            encoding="ascii",
        )
        if deadline - time.monotonic() <= FINALIZE_RESERVE_S:
            raise LifetimeBudgetExceeded("cap reserve exhausted before D-058 reference")
        with reference_progress.open("xb") as reference_stream:
            reference = run_reference_once(
                on_transition=writer(
                    reference_stream, "reference", validate_reference_transition
                ),
                deadline_monotonic=min(
                    time.monotonic() + REFERENCE_STAGE_CAP_S, deadline
                ),
                finalize_reserve_s=FINALIZE_RESERVE_S,
            )
        if deadline - time.monotonic() <= FINALIZE_RESERVE_S:
            raise LifetimeBudgetExceeded(
                "cap reserve exhausted before final serialization"
            )
        primary_trace = cast(list[dict[str, object]], primary["trace"])
        reference_trace = cast(list[dict[str, object]], reference["trace"])
        if primary_count != len(primary_trace) or reference_count != len(
            reference_trace
        ):
            raise LifetimeStop(
                "streamed transition count differs from completed lifetime"
            )
        if primary.get("actual_engine_steps") != primary_count * PRIMARY_MICROSTEPS:
            raise LifetimeStop("primary actual engine-step accounting mismatch")
        result: dict[str, object] = {
            "schema_version": 3,
            "mode": "single-v3-pymunk-lifetime-plus-d058-reference",
            "candidate_head": head,
            "protocol_sha256": protocol_sha,
            "supervisor_approval_receipt_sha256": receipt_sha,
            "v3_executable_sha": V3_EXECUTABLE_SHA,
            "v3_result_commit": V3_RESULT_COMMIT,
            "v3_results_sha256": V3_B_RESULTS_SHA256,
            "v3_protocol_sha256": V3_PROTOCOL_SHA256,
            "runtime": preflight_record["runtime"],
            "plan": preflight_record["planned"],
            "pymunk_lifetime": _summary_without_trace(primary),
            "matched_reference_lifetime": _summary_without_trace(reference),
            "pymunk_charging": summarize_charging(primary_trace),
            "reference_charging": summarize_charging(reference_trace),
            "trajectory_match_claim": False,
            "comparison_disclosure": (
                "Same development seed, fixed initial state, 3 m centered dock and "
                "D-053 proposal stream. The substrate trajectories and subsequent "
                "D-052 actions may diverge; this is descriptive, not a matched-"
                "same-trajectory causal estimate."
            ),
            "charging_boundary": (
                "Station proximity, paired dock contact, charger latch/phase, and "
                "actual stored energy are separately recorded. If paired dock "
                "contact never occurs, report charging not exercised; do not infer "
                "charger success or failure from proximity alone."
            ),
            "trace_files": {
                "pymunk": primary_progress.name,
                "reference": reference_progress.name,
            },
            "trace_array_sha256": {
                "pymunk": primary["trace_sha256"],
                "reference": reference["trace_sha256"],
            },
            "trace_jsonl_sha256": {
                "pymunk": _sha256_file(primary_progress),
                "reference": _sha256_file(reference_progress),
            },
            "elapsed_s": time.monotonic() - started,
            "lifetime_authorized_in_v3_record": False,
        }
        if time.monotonic() >= deadline:
            raise LifetimeBudgetExceeded(
                "pair wall-clock cap reached before result write"
            )
        result_path = output / "lifetime-results.json"
        result_path.write_bytes(json_bytes(result) + b"\n")
        if time.monotonic() >= deadline:
            raise LifetimeBudgetExceeded(
                "pair wall-clock cap reached before final marker"
            )
        marker.write_text(
            f"head={head}\nprotocol_sha256={protocol_sha}\n"
            f"approval_receipt_sha256={receipt_sha}\nphase=complete\ncompleted=1\n"
            f"primary_transitions={primary_count}\n"
            f"primary_engine_steps={primary_count * PRIMARY_MICROSTEPS}\n"
            f"reference_transitions={reference_count}\nreference_engine_steps=0\n",
            encoding="ascii",
        )
        _write_manifest(output)
        return result
    except BaseException as exc:
        failure = {
            "candidate_head": head,
            "protocol_sha256": protocol_sha,
            "approval_receipt_sha256": receipt_sha,
            "phase": current_phase,
            "error": repr(exc),
            "elapsed_s": time.monotonic() - started,
            "primary_transitions_preserved": primary_count,
            "primary_engine_steps_preserved": primary_count * PRIMARY_MICROSTEPS,
            "reference_transitions_preserved": reference_count,
            "reference_engine_steps": 0,
            "resume_or_retry_authorized": False,
        }
        (output / "FAILED-INCOMPLETE.json").write_bytes(json_bytes(failure) + b"\n")
        marker.write_text(
            f"head={head}\nprotocol_sha256={protocol_sha}\n"
            f"approval_receipt_sha256={receipt_sha}\nphase=failed-incomplete\n"
            f"primary_transitions={primary_count}\n"
            f"primary_engine_steps={primary_count * PRIMARY_MICROSTEPS}\n"
            f"reference_transitions={reference_count}\nreference_engine_steps=0\n",
            encoding="ascii",
        )
        _write_manifest(output)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--preflight", action="store_true")
    modes.add_argument("--run-once", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--approval-head")
    parser.add_argument("--approval-protocol-sha256")
    parser.add_argument("--approval-receipt-sha256")
    args = parser.parse_args()
    if args.preflight:
        if any(
            value is not None
            for value in (
                args.approval_head,
                args.approval_protocol_sha256,
                args.approval_receipt_sha256,
            )
        ):
            parser.error("approval arguments are valid only for --run-once")
        result = preflight(args.output)
    else:
        if not all(
            (
                args.approval_head,
                args.approval_protocol_sha256,
                args.approval_receipt_sha256,
            )
        ):
            parser.error("--run-once requires the exact supervisor approval binding")
        result = run_pair_once(
            args.output,
            approved_head=args.approval_head,
            approved_protocol_sha256=args.approval_protocol_sha256,
            approval_receipt_sha256=args.approval_receipt_sha256,
        )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
