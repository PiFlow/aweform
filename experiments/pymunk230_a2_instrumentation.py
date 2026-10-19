"""Source-only A2 instrumentation contract and bounded supervisor.

The worker protocol is intentionally non-physical: this module can validate a
frozen schedule and exercise custody/watchdog plumbing, but cannot step Pymunk.
A future physics run requires a separate decision and reviewed frozen runner.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import queue
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, cast

BASE_SHA = "c9280554268a789949b73babdd40d5f363649761"
FROZEN_ATTEMPT3_HEAD = "1ab7cf43220ee9348e8d966745c93abfa346e190"
FROZEN_PROTOCOL_SHA256 = (
    "9f749b39d37da4541b8dae84c732a9e24ae271e3767906ed862c5f88a1e0fe18"
)
FROZEN_PHYSICS_SHA256 = (
    "7f2492e326a57d7ca12b65bbdb1202cb7538d5a0c4ae25dea8c7a6f809f93fd4"
)
FROZEN_PREFIX_SHA256 = (
    "e8c0aec8d82c6e79143ee70ea50519f3cf2c369e07df73795db6038a387e63c7"
)
INSTRUMENTATION_PROTOCOL = "A2-R1-v2"
MAX_SUBSTEPS = 4_800
MAX_WALL_SECONDS = 120.0
MAX_CPU_SECONDS = 120.0
MAX_OUTPUT_BYTES = 2 * 1024 * 1024
STOP_RECEIPT_RESERVE_BYTES = 4_096
MAX_EVENTS = 10_000
MAX_RSS_BYTES = 256 * 1024 * 1024
DETAIL_WINDOW = (0.85, 0.98)
EMPTY_FREE_START = (1.0, 1.0, 0.0)
EMPTY_FREE_ACTION = (0.6457718232379019, 0.6457718232379019)
FROZEN_CASES_PATH = "experiments/pymunk230_obstacles/cases.py"
FROZEN_PROTOCOL_PATH = "experiments/pymunk230_obstacles/protocol.md"
FROZEN_PROTOCOL_PREFIX_MARKER = b"## Sole conditional Level-1 lifetime"
FROZEN_CASES_SHA256 = "0007e4400511ed956f9ec1642e9c4029990afa2b95061be4ffc631e984ecbe05"
A2_CASE_ID = "A2-convex-face"
A2_START = (2.18, 1.5, 0.0)
A2_ACTION = (0.6457718232379019, 0.6457718232379019)
A2_SOURCE_COMMAND_COUNT = 4

# Normalized command progress; cmd2 N800 samples share physical time with N400.
CHECKPOINTS = (
    ("cmd1", 0.00),
    ("cmd1", 0.25),
    ("cmd1", 0.50),
    ("cmd1", 0.75),
    ("cmd1", 1.00),
    ("cmd2", 0.00),
    ("cmd2", 0.25),
    ("cmd2", 0.50),
    ("cmd2", 0.75),
    ("cmd2", 0.85),
    ("cmd2", 0.90),
    ("cmd2", 0.98),
    ("cmd2", 1.00),
)


@dataclass(frozen=True)
class RunCase:
    case_id: str
    fixture_id: str
    fixture_sha256: str
    role: str
    command_id: str
    start: tuple[float, float, float]
    action: tuple[float, float]
    microsteps: int
    substeps: int
    control_requires_no_contact: bool
    full_fixture_expected_objects: tuple[str, ...]


@dataclass(frozen=True)
class SourceIdentity:
    base_sha: str
    attempt3_head: str
    full_protocol_sha256: str
    physics_source_sha256: str
    protocol_prefix_sha256: str
    cases_source_sha256: str


FROZEN_IDENTITY = SourceIdentity(
    BASE_SHA,
    FROZEN_ATTEMPT3_HEAD,
    FROZEN_PROTOCOL_SHA256,
    FROZEN_PHYSICS_SHA256,
    FROZEN_PREFIX_SHA256,
    FROZEN_CASES_SHA256,
)


FrozenBlobReader = Callable[[str, str], bytes]


def _git_show_blob(commit: str, path: str) -> bytes:
    try:
        return subprocess.check_output(
            ["git", "show", f"{commit}:{path}"], stderr=subprocess.PIPE
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ReceiptError(f"missing frozen source blob: {path}") from exc


def verify_frozen_source_blobs(
    cases_blob: bytes, protocol_blob: bytes
) -> dict[str, str]:
    """Verify frozen authoritative fixture/protocol bytes; no simulator imports."""
    cases_digest = hashlib.sha256(cases_blob).hexdigest()
    protocol_digest = hashlib.sha256(protocol_blob).hexdigest()
    if cases_digest != FROZEN_CASES_SHA256:
        raise ReceiptError("frozen cases.py SHA-256 mismatch")
    if protocol_digest != FROZEN_PROTOCOL_SHA256:
        raise ReceiptError("frozen protocol SHA-256 mismatch")
    if FROZEN_PROTOCOL_PREFIX_MARKER not in protocol_blob:
        raise ReceiptError("frozen protocol prefix boundary is missing")
    prefix = protocol_blob.split(FROZEN_PROTOCOL_PREFIX_MARKER, 1)[0]
    prefix_digest = hashlib.sha256(prefix).hexdigest()
    if prefix_digest != FROZEN_PREFIX_SHA256:
        raise ReceiptError("frozen protocol-prefix SHA-256 mismatch")
    return {
        "cases_sha256": cases_digest,
        "protocol_sha256": protocol_digest,
        "protocol_prefix_sha256": prefix_digest,
    }


def verify_frozen_source_identity(
    reader: FrozenBlobReader = _git_show_blob,
) -> dict[str, str]:
    """Read the two immutable blobs from the pinned commit and verify custody."""
    cases_blob = reader(FROZEN_ATTEMPT3_HEAD, FROZEN_CASES_PATH)
    protocol_blob = reader(FROZEN_ATTEMPT3_HEAD, FROZEN_PROTOCOL_PATH)
    return verify_frozen_source_blobs(cases_blob, protocol_blob)


def _case(
    case_id: str,
    fixture_id: str,
    role: str,
    command_id: str,
    start: tuple[float, float, float],
    action: tuple[float, float],
    microsteps: int,
    substeps: int,
    no_contact: bool,
    fixture_objects: tuple[str, ...],
) -> RunCase:
    return RunCase(
        case_id,
        fixture_id,
        FROZEN_CASES_SHA256,
        role,
        command_id,
        start,
        action,
        microsteps,
        substeps,
        no_contact,
        fixture_objects,
    )


FROZEN_PLAN = (
    _case(
        "a2_n400_cmd1",
        A2_CASE_ID,
        "primary",
        "cmd1",
        A2_START,
        A2_ACTION,
        400,
        400,
        False,
        ("A2",),
    ),
    _case(
        "a2_n400_cmd2",
        A2_CASE_ID,
        "primary",
        "cmd2",
        A2_START,
        A2_ACTION,
        400,
        400,
        False,
        ("A2",),
    ),
    _case(
        "a2_n800_cmd1",
        A2_CASE_ID,
        "primary",
        "cmd1",
        A2_START,
        A2_ACTION,
        800,
        800,
        False,
        ("A2",),
    ),
    _case(
        "a2_n800_cmd2",
        A2_CASE_ID,
        "primary",
        "cmd2",
        A2_START,
        A2_ACTION,
        800,
        800,
        False,
        ("A2",),
    ),
    _case(
        "empty_free_n400_primary",
        "empty-free",
        "primary",
        "F×1",
        EMPTY_FREE_START,
        EMPTY_FREE_ACTION,
        400,
        400,
        True,
        (),
    ),
    _case(
        "empty_free_n400_replay",
        "empty-free",
        "fresh_replay",
        "F×1",
        EMPTY_FREE_START,
        EMPTY_FREE_ACTION,
        400,
        400,
        True,
        (),
    ),
    _case(
        "empty_free_n800_primary",
        "empty-free",
        "primary",
        "F×1",
        EMPTY_FREE_START,
        EMPTY_FREE_ACTION,
        800,
        800,
        True,
        (),
    ),
    _case(
        "empty_free_n800_replay",
        "empty-free",
        "fresh_replay",
        "F×1",
        EMPTY_FREE_START,
        EMPTY_FREE_ACTION,
        800,
        800,
        True,
        (),
    ),
)


def validate_plan(plan: tuple[RunCase, ...], identity: SourceIdentity) -> None:
    """Fail closed unless source custody, exact cases, and accounting match."""
    if identity != FROZEN_IDENTITY:
        raise ReceiptError("frozen source/protocol identity mismatch")
    if any(not case.start or not case.action for case in plan):
        raise ReceiptError("frozen case is missing start pose or action")
    if sum(case.substeps for case in plan) != MAX_SUBSTEPS:
        raise ReceiptError("frozen total substep accounting mismatch")
    if len({case.case_id for case in plan}) != len(plan):
        raise ReceiptError("duplicate frozen case")
    if sum(case.substeps for case in plan if case.fixture_id == A2_CASE_ID) != 2_400:
        raise ReceiptError("A2 target substep accounting mismatch")
    if sum(case.substeps for case in plan if case.fixture_id == "empty-free") != 2_400:
        raise ReceiptError("empty-free control substep accounting mismatch")
    if plan != FROZEN_PLAN:
        raise ReceiptError("run plan differs from the frozen fixture/commands")


def schedule() -> tuple[RunCase, ...]:
    """Return and validate the immutable model-free plan, never step physics."""
    validate_plan(FROZEN_PLAN, FROZEN_IDENTITY)
    return FROZEN_PLAN


def validate_empty_free_control(primary: bytes, replay: bytes) -> None:
    """Require exact replay identity and no contact events in the control."""
    if primary != replay:
        raise ReceiptError("empty-free primary/replay bytes differ")
    try:
        rows = [json.loads(line) for line in primary.splitlines() if line]
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReceiptError("empty-free control is not valid JSONL") from exc
    if not rows:
        raise ReceiptError("empty-free control has no records")
    if any(not isinstance(row, dict) for row in rows):
        raise ReceiptError("empty-free control rows must be JSON objects")
    if any(not isinstance(row.get("contact_events"), list) for row in rows):
        raise ReceiptError("empty-free control is missing contact-event records")
    if any(row["contact_events"] for row in rows):
        raise ReceiptError("empty-free negative control contains contact events")


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


class ReceiptError(RuntimeError):
    pass


class BoundedJournal:
    """Append-only event journal; `last_durable` describes flushed bytes only."""

    def __init__(self, directory: Path):
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=False)
        self.path = directory / "events.jsonl"
        self._file = self.path.open("xb", buffering=0)
        self._sequence = 0
        self._bytes = 0
        self._hasher = hashlib.sha256()
        self._digest = self._hasher.hexdigest()

    @property
    def last_durable(self) -> dict[str, object]:
        return {
            "sequence": self._sequence,
            "bytes": self._bytes,
            "sha256": self._digest,
        }

    def append(self, event: dict[str, object]) -> None:
        if self._sequence >= MAX_EVENTS:
            raise ReceiptError("event record limit exceeded")
        row = {"sequence": self._sequence + 1, "event": event}
        encoded = canonical_json(row) + b"\n"
        if self._bytes + len(encoded) + STOP_RECEIPT_RESERVE_BYTES > MAX_OUTPUT_BYTES:
            raise ReceiptError("inclusive output byte limit exceeded")
        self._file.write(encoded)
        os.fsync(self._file.fileno())
        self._sequence += 1
        self._bytes += len(encoded)
        self._hasher.update(encoded)
        self._digest = self._hasher.hexdigest()

    def close(self) -> None:
        if not self._file.closed:
            self._file.close()


def write_stop_receipt(
    directory: Path, *, reason: str, journal: BoundedJournal, started: float
) -> Path:
    """Atomically write and fsync a receipt with top-level durable watermark."""
    receipt = {
        "schema": "pymunk230-a2-stop-v1",
        "protocol": INSTRUMENTATION_PROTOCOL,
        "identity": {
            "base_sha": BASE_SHA,
            "attempt3_head": FROZEN_ATTEMPT3_HEAD,
            "cases_source_sha256": FROZEN_CASES_SHA256,
            "full_protocol_sha256": FROZEN_PROTOCOL_SHA256,
            "physics_sha256": FROZEN_PHYSICS_SHA256,
            "prefix_sha256": FROZEN_PREFIX_SHA256,
        },
        "status": "STOP",
        "reason": reason,
        "last_durable": journal.last_durable,
        "elapsed_wall_s": max(0.0, time.monotonic() - started),
        "event_file": journal.path.name,
    }
    encoded = canonical_json(receipt) + b"\n"
    if journal._bytes + len(encoded) > MAX_OUTPUT_BYTES:
        # Preserve the original cap reason while ensuring a minimal bounded receipt.
        receipt["reason"] = "output_limit_before_receipt"
        encoded = canonical_json(receipt) + b"\n"
    digest_bytes = (
        hashlib.sha256(encoded).hexdigest().encode("ascii") + b"  STOP.json\n"
    )
    if journal._bytes + len(encoded) + len(digest_bytes) > MAX_OUTPUT_BYTES:
        raise ReceiptError("cannot fit hashed STOP receipt within inclusive byte cap")
    final = directory / "STOP.json"
    _write_fsynced_atomic(final, encoded)
    _write_fsynced_atomic(directory / "STOP.sha256", digest_bytes)
    fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return final


def _write_fsynced_atomic(final: Path, data: bytes) -> None:
    tmp = final.with_name(final.name + ".tmp")
    with tmp.open("xb") as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())
    os.replace(tmp, final)


def _worker_command() -> list[str]:
    """Fixed module entry point; caller-supplied child commands are impossible."""
    return [sys.executable, str(Path(__file__).resolve()), "--model-free-worker"]


def _terminate_and_reap(child: subprocess.Popen[bytes], grace_s: float = 0.2) -> None:
    if child.poll() is not None:
        child.wait()
        return
    try:
        if os.name == "posix":
            os.killpg(child.pid, signal.SIGTERM)
        else:
            child.terminate()
        child.wait(timeout=grace_s)
    except ProcessLookupError, subprocess.TimeoutExpired:
        try:
            if os.name == "posix":
                os.killpg(child.pid, signal.SIGKILL)
            else:
                child.kill()
        except ProcessLookupError:
            pass
        child.wait()


def supervise(
    output: Path,
    *,
    wall_cap_s: float = MAX_WALL_SECONDS,
    cpu_cap_s: float = MAX_CPU_SECONDS,
) -> dict[str, object]:
    """Run only the fixed model-free worker and always leave a durable receipt."""
    if wall_cap_s <= 0 or cpu_cap_s <= 0:
        raise ValueError("caps must be positive")
    journal = BoundedJournal(output)
    started = time.monotonic()
    child: subprocess.Popen[bytes] | None = None
    failure = "worker_not_started"
    lines: queue.Queue[bytes | None] = queue.Queue()
    try:
        child = subprocess.Popen(
            _worker_command(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=(os.name == "posix"),
            bufsize=0,
        )
        assert child.stdout is not None
        threading.Thread(
            target=lambda: _read_lines(child.stdout, lines), daemon=True
        ).start()
        deadline = started + wall_cap_s
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                failure = "wall_cap"
                break
            try:
                line = lines.get(timeout=min(0.05, remaining))
            except queue.Empty:
                line = b""
            if line:
                journal.append(json.loads(line.decode("utf-8")))
            elif line is None:
                code = child.poll()
                if code is not None:
                    failure = "worker_exit" if code else "worker_completed"
                    break
            code = child.poll()
            if code is not None and lines.empty():
                failure = "worker_exit" if code else "worker_completed"
                break
            # CPU/RSS enforcement is based on observed process metrics. The worker
            # is a single fixed process; limits are checked at each polling interval.
            metrics = _process_metrics(child.pid)
            if metrics is None:
                failure = "resource_metrics_unavailable"
                break
            if metrics["cpu_s"] > cpu_cap_s:
                failure = "cpu_cap"
                break
            if metrics["rss_bytes"] > MAX_RSS_BYTES:
                failure = "rss_cap"
                break
        if child.poll() is None:
            _terminate_and_reap(child)
        else:
            child.wait()
        journal.close()
        receipt_path = write_stop_receipt(
            output, reason=failure, journal=journal, started=started
        )
        return cast(dict[str, object], json.loads(receipt_path.read_text("utf-8")))
    except BaseException as exc:
        if child is not None:
            _terminate_and_reap(child)
        journal.close()
        try:
            receipt_path = write_stop_receipt(
                output,
                reason=f"supervisor_error:{type(exc).__name__}",
                journal=journal,
                started=started,
            )
            return cast(dict[str, object], json.loads(receipt_path.read_text("utf-8")))
        except BaseException:
            raise


def _read_lines(stream: Any, target: queue.Queue[bytes | None]) -> None:
    try:
        for line in iter(stream.readline, b""):
            target.put(line)
    finally:
        target.put(None)
        stream.close()


def _process_metrics(pid: int) -> dict[str, float | int] | None:
    """Read child CPU/RSS, returning None rather than claiming unknown is safe."""
    if sys.platform.startswith("linux"):
        try:
            fields = Path(f"/proc/{pid}/stat").read_text().split()
            hz = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
            cpu = (int(fields[13]) + int(fields[14])) / hz
            rss = int(fields[23]) * os.sysconf("SC_PAGE_SIZE")
            return {"cpu_s": cpu, "rss_bytes": rss}
        except OSError, ValueError, IndexError:
            return None
    try:
        output = subprocess.check_output(
            ["ps", "-p", str(pid), "-o", "cputime=", "-o", "rss="],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        cpu_text, rss_text = output.split()
        parts = [float(part) for part in cpu_text.split(":")]
        if len(parts) == 3:
            cpu_s = parts[0] * 3600 + parts[1] * 60 + parts[2]
        elif len(parts) == 2:
            cpu_s = parts[0] * 60 + parts[1]
        else:
            cpu_s = float(parts[0])
        return {"cpu_s": float(cpu_s), "rss_bytes": int(rss_text) * 1024}
    except OSError, subprocess.CalledProcessError, ValueError:
        return None


def _plan_event(
    verified_sources: dict[str, str] | None = None,
) -> dict[str, object]:
    if verified_sources is None:
        verified_sources = verify_frozen_source_identity()
    plan = schedule()
    digest = hashlib.sha256(
        canonical_json([case.__dict__ for case in plan])
    ).hexdigest()
    return {
        "kind": "frozen_plan_preflight",
        "plan_sha256": digest,
        "case_count": len(plan),
        "total_substeps": sum(case.substeps for case in plan),
        "source_blobs": verified_sources,
    }


def supervise_frozen_plan(output: Path) -> dict[str, object]:
    """Supervise only the model-free frozen-plan worker; never step physics."""
    expected = _plan_event()
    receipt = supervise(output)
    records = [
        json.loads(line)
        for line in (output / "events.jsonl").read_text("utf-8").splitlines()
        if line
    ]
    expected_row = {"sequence": 1, "event": expected}
    if receipt.get("reason") != "worker_completed" or records != [expected_row]:
        raise ReceiptError("model-free supervised plan validation failed")
    return receipt


def _model_free_worker() -> int:
    """Emit the verified frozen-plan identity; no simulator calls."""
    print(canonical_json(_plan_event()).decode("utf-8"), flush=True)
    return 0


def _model_free_test_worker() -> int:
    """Synthetic test-only plan event; never used by the public preflight."""
    pinned_hashes = {
        "cases_sha256": FROZEN_CASES_SHA256,
        "protocol_sha256": FROZEN_PROTOCOL_SHA256,
        "protocol_prefix_sha256": FROZEN_PREFIX_SHA256,
    }
    print(canonical_json(_plan_event(pinned_hashes)).decode("utf-8"), flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--supervise-preflight", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--model-free-worker", action="store_true")
    parser.add_argument(
        "--test-silent-worker", action="store_true", help=argparse.SUPPRESS
    )
    parser.add_argument(
        "--test-plan-worker", action="store_true", help=argparse.SUPPRESS
    )
    args = parser.parse_args(argv)
    if args.test_silent_worker:
        time.sleep(10.0)
        return 0
    if args.test_plan_worker:
        return _model_free_test_worker()
    if args.model_free_worker:
        return _model_free_worker()
    if args.supervise_preflight:
        if args.output is None:
            parser.error("--supervise-preflight requires --output")
        print(canonical_json(supervise_frozen_plan(args.output)).decode("utf-8"))
        return 0
    if args.preflight:
        verified_sources = verify_frozen_source_identity()
        data = {
            "protocol": INSTRUMENTATION_PROTOCOL,
            "source_identity": FROZEN_IDENTITY.__dict__,
            "verified_source_blobs": verified_sources,
            "base_sha": BASE_SHA,
            "frozen_attempt3_head": FROZEN_ATTEMPT3_HEAD,
            "protocol_sha256": FROZEN_PROTOCOL_SHA256,
            "physics_sha256": FROZEN_PHYSICS_SHA256,
            "prefix_sha256": FROZEN_PREFIX_SHA256,
            "cases": [c.__dict__ for c in schedule()],
            "a2_frozen_fixture": {
                "case_id": A2_CASE_ID,
                "source_commit": FROZEN_ATTEMPT3_HEAD,
                "cases_source_sha256": FROZEN_CASES_SHA256,
                "start": A2_START,
                "source_commands": A2_SOURCE_COMMAND_COUNT,
                "instrumented_prefix": [
                    {"command_id": "cmd1", "action": A2_ACTION},
                    {"command_id": "cmd2", "action": A2_ACTION},
                ],
                "full_fixture_expected_objects": ("A2",),
            },
            "checkpoints": CHECKPOINTS,
            "detail_window": DETAIL_WINDOW,
            "prospective_total_substeps": MAX_SUBSTEPS,
            "execution_enabled": False,
        }
        print(canonical_json(data).decode())
        return 0
    parser.error(
        "only --preflight is enabled; physical execution needs fresh authorization"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
