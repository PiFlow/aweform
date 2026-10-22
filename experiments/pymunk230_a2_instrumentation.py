"""A2 instrumentation contract and bounded supervisor.

Normal plan/preflight paths are model-free. A separate A2 physics child is
available only through the exact-HEAD/environment-gated supervisor API; this
preparation task never invoked that path.
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
MAX_STDOUT_LINE_BYTES = 64 * 1024
STDOUT_QUEUE_RECORDS = 8
DETAIL_WINDOW = (0.85, 0.98)
EMPTY_FREE_START = (1.0, 1.0, 0.0)
EMPTY_FREE_ACTION = (0.6457718232379019, 0.6457718232379019)
FROZEN_CASES_PATH = "experiments/pymunk230_obstacles/cases.py"
FROZEN_PROTOCOL_PATH = "experiments/pymunk230_obstacles/protocol.md"
FROZEN_PROTOCOL_PREFIX_MARKER = b"## Sole conditional Level-1 lifetime"
FROZEN_CASES_SHA256 = "0007e4400511ed956f9ec1642e9c4029990afa2b95061be4ffc631e984ecbe05"
FROZEN_CASES_BLOB_OID = "550b9fc56949f0ccdc4bf08924591bf92b666f15"
FROZEN_PROTOCOL_BLOB_OID = "326551fb49259c42d26a911b2df8208f80255631"
FROZEN_CASES_BYTES = 7_947
FROZEN_PROTOCOL_BYTES = 24_592
FROZEN_EXECUTABLE_SOURCES = (
    (
        "experiments/pymunk_contact_prototype/fixture.py",
        16_275,
        "36522c9b528bd8e94fcc8da69c78a92d2a3840a2",
        "63127723dae68ebf9a2113cd1d9827925871e8d595557522f5cc9b4ee47f72f0",
    ),
    (
        "experiments/pymunk230_obstacles/audit.py",
        9_983,
        "29e91624817e99d07e2341c43af616dcb95724e3",
        "5fb6d7110013cfcbfd88d74f08660aaef9977031931fe0cd3d1445cc87395318",
    ),
    (
        FROZEN_CASES_PATH,
        FROZEN_CASES_BYTES,
        FROZEN_CASES_BLOB_OID,
        FROZEN_CASES_SHA256,
    ),
    (
        "experiments/pymunk230_obstacles/geometry.py",
        5_411,
        "fc68d338b79c115743983c6bccabf06a77c10674",
        "be9f9816762f86b156d96c36501f1ab02c2bb044a1468f2f9bb9b776dff2f7a7",
    ),
    (
        "experiments/pymunk230_obstacles/run_physics.py",
        61_121,
        "6d354ea6a333471c2c55a994ecc05a53a5290034",
        "3721a813138a78e29775e2654c03b1b448a02df6e980ba0b93b7f5af069e6b26",
    ),
    (
        "experiments/pymunk230_obstacles/world.py",
        7_857,
        "fc038967b3e3b41b4759071b7981911a90756127",
        "ce9918ba9b6acf531a72150e3cb3f07beed8c60b2f1812b653897b97a88bb34c",
    ),
)
HISTORICAL_PROVENANCE = "historical_commit"
DETACHED_PROVENANCE = "detached_content"
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


def _git_blob_oid(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def verify_detached_source_identity(root: Path = Path.cwd()) -> dict[str, str]:
    """Verify disclosed source bytes without asserting historical ancestry."""
    paths = (FROZEN_CASES_PATH, FROZEN_PROTOCOL_PATH)
    expected = (
        (FROZEN_CASES_BYTES, FROZEN_CASES_SHA256, FROZEN_CASES_BLOB_OID),
        (FROZEN_PROTOCOL_BYTES, FROZEN_PROTOCOL_SHA256, FROZEN_PROTOCOL_BLOB_OID),
    )
    contents: list[bytes] = []
    identities: dict[str, str] = {}
    for path, (size, sha256, blob_oid) in zip(paths, expected, strict=True):
        try:
            data = (root / path).read_bytes()
        except OSError as exc:
            raise ReceiptError(f"missing detached source file: {path}") from exc
        if len(data) != size:
            raise ReceiptError(f"detached source size mismatch: {path}")
        if hashlib.sha256(data).hexdigest() != sha256:
            raise ReceiptError(f"detached source SHA-256 mismatch: {path}")
        if _git_blob_oid(data) != blob_oid:
            raise ReceiptError(f"detached source Git blob OID mismatch: {path}")
        contents.append(data)
        key = "cases" if path == FROZEN_CASES_PATH else "protocol"
        identities[f"{key}_blob_oid"] = blob_oid
        identities[f"{key}_bytes"] = str(size)
    identities.update(verify_frozen_source_blobs(*contents))
    identities["provenance_mode"] = DETACHED_PROVENANCE
    identities["historical_ancestry_proven"] = "false"
    return identities


def verify_frozen_source_identity(
    reader: FrozenBlobReader = _git_show_blob,
) -> dict[str, str]:
    """Read the two immutable blobs from the pinned historical commit."""
    cases_blob = reader(FROZEN_ATTEMPT3_HEAD, FROZEN_CASES_PATH)
    protocol_blob = reader(FROZEN_ATTEMPT3_HEAD, FROZEN_PROTOCOL_PATH)
    verified = verify_frozen_source_blobs(cases_blob, protocol_blob)
    verified["provenance_mode"] = HISTORICAL_PROVENANCE
    verified["historical_commit_content_verified"] = "true"
    return verified


def verify_candidate_source_identity(root: Path = Path.cwd()) -> dict[str, object]:
    """Bind authored child/supervisor bytes to one clean exact Git HEAD."""
    try:
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.PIPE
        ).strip()
        dirty = subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=root,
            text=True,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ReceiptError("cannot verify candidate source HEAD") from exc
    if len(head) != 40 or dirty.strip():
        raise ReceiptError("candidate source is not a clean exact HEAD")
    files = (
        "experiments/pymunk230_a2_instrumentation.py",
        "experiments/pymunk230_a2_diagnostic.py",
    )
    contents: list[dict[str, object]] = []
    for relative in files:
        try:
            data = (root / relative).read_bytes()
        except OSError as exc:
            raise ReceiptError(f"missing candidate source file: {relative}") from exc
        contents.append(
            {
                "path": relative,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    return {"candidate_head": head, "authored_sources": contents}


def verify_a2_executable_identity(root: Path = Path.cwd()) -> dict[str, object]:
    """Verify exact six-file content custody without importing physics code."""
    detached = verify_detached_source_identity(root)
    digest = hashlib.sha256()
    sources: list[dict[str, object]] = []
    for relative, size, blob_oid, sha256 in FROZEN_EXECUTABLE_SOURCES:
        try:
            data = (root / relative).read_bytes()
        except OSError as exc:
            raise ReceiptError(f"missing frozen executable source: {relative}") from exc
        actual_oid = _git_blob_oid(data)
        actual_sha = hashlib.sha256(data).hexdigest()
        if len(data) != size or actual_oid != blob_oid or actual_sha != sha256:
            raise ReceiptError(
                f"frozen executable source identity mismatch: {relative}"
            )
        digest.update(relative.encode("utf-8") + b"\0" + bytes.fromhex(actual_sha))
        sources.append(
            {
                "path": relative,
                "bytes": size,
                "blob_oid": blob_oid,
                "sha256": sha256,
            }
        )
    physics_sha256 = digest.hexdigest()
    if physics_sha256 != FROZEN_PHYSICS_SHA256:
        raise ReceiptError("frozen physics content digest mismatch")
    return {
        "provenance_mode": DETACHED_PROVENANCE,
        "historical_ancestry_proven": False,
        "detached_inputs": detached,
        "physics_sha256": physics_sha256,
        "sources": sources,
    }


def verify_source_identity(
    provenance_mode: str = HISTORICAL_PROVENANCE, root: Path = Path.cwd()
) -> dict[str, str]:
    if provenance_mode == HISTORICAL_PROVENANCE:
        return verify_frozen_source_identity()
    if provenance_mode == DETACHED_PROVENANCE:
        return verify_detached_source_identity(root)
    raise ReceiptError(f"unknown source provenance mode: {provenance_mode}")


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


@dataclass
class _ReaderStatus:
    done: threading.Event
    error: str | None = None


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
        start = self._bytes
        try:
            view = memoryview(encoded)
            written = 0
            while written < len(encoded):
                count = self._file.write(view[written:])
                if count is None or count <= 0:
                    raise OSError("journal write made no progress")
                written += count
            os.fsync(self._file.fileno())
        except BaseException:
            self._file.seek(start)
            self._file.truncate(start)
            os.fsync(self._file.fileno())
            raise
        self._sequence += 1
        self._bytes += len(encoded)
        self._hasher.update(encoded)
        self._digest = self._hasher.hexdigest()

    def close(self) -> None:
        if not self._file.closed:
            self._file.close()


def write_stop_receipt(
    directory: Path,
    *,
    reason: str,
    journal: BoundedJournal,
    started: float,
    resource_usage: dict[str, object] | None = None,
    provenance_mode: str = HISTORICAL_PROVENANCE,
) -> Path:
    """Atomically write and fsync a receipt with top-level durable watermark."""
    receipt = {
        "schema": "pymunk230-a2-stop-v1",
        "protocol": INSTRUMENTATION_PROTOCOL,
        "provenance_mode": provenance_mode,
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
        "resource_usage": resource_usage or {},
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
    if len(encoded) + len(digest_bytes) > STOP_RECEIPT_RESERVE_BYTES:
        receipt["reason"] = str(receipt["reason"])[:96]
        receipt["resource_usage"] = {}
        encoded = canonical_json(receipt) + b"\n"
        digest_bytes = (
            hashlib.sha256(encoded).hexdigest().encode("ascii") + b"  STOP.json\n"
        )
    if (
        len(encoded) + len(digest_bytes) > STOP_RECEIPT_RESERVE_BYTES
        or journal._bytes + len(encoded) + len(digest_bytes) > MAX_OUTPUT_BYTES
    ):
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


def _a2_worker_command() -> list[str]:
    """Fixed child entry point; callable only after the external GO guard."""
    return [
        sys.executable,
        str(Path(__file__).with_name("pymunk230_a2_diagnostic.py").resolve()),
        "--diagnostic-child",
    ]


def _worker_command(
    provenance_mode: str = HISTORICAL_PROVENANCE,
    source_root: Path = Path.cwd(),
) -> list[str]:
    """Fixed module entry point; caller-supplied child commands are impossible."""
    return [
        sys.executable,
        str(Path(__file__).resolve()),
        "--model-free-worker",
        "--source-provenance",
        provenance_mode,
        "--source-root",
        str(source_root.resolve()),
    ]


def _terminate_and_reap(child: subprocess.Popen[bytes], grace_s: float = 0.2) -> bool:
    """Stop the isolated process group even if its direct child already exited."""
    try:
        if os.name == "posix":
            os.killpg(child.pid, signal.SIGTERM)
        elif child.poll() is None:
            child.terminate()
    except ProcessLookupError:
        pass
    deadline = time.monotonic() + grace_s
    while time.monotonic() < deadline:
        if child.poll() is None:
            try:
                child.wait(timeout=min(0.02, max(0.0, deadline - time.monotonic())))
            except subprocess.TimeoutExpired:
                pass
        if os.name != "posix" or not _process_group_alive(child.pid):
            break
        time.sleep(0.01)
    try:
        if os.name == "posix":
            os.killpg(child.pid, signal.SIGKILL)
        elif child.poll() is None:
            child.kill()
    except ProcessLookupError:
        pass
    try:
        child.wait(timeout=0.5)
    except subprocess.TimeoutExpired:
        return False
    return True


def _process_group_alive(pgid: int) -> bool:
    if os.name != "posix":
        return False
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _read_lines(stream: Any, target: queue.Queue[bytes], status: _ReaderStatus) -> None:
    """Read bounded lines without allowing a child to grow parent memory."""
    try:
        while True:
            line = stream.readline(MAX_STDOUT_LINE_BYTES + 1)
            if not line:
                break
            if len(line) > MAX_STDOUT_LINE_BYTES:
                status.error = "stdout_line_limit"
                break
            try:
                target.put_nowait(line)
            except queue.Full:
                status.error = "stdout_queue_overflow"
                break
    except OSError:
        status.error = "stdout_reader_error"
    finally:
        status.done.set()
        stream.close()


def _parent_rss_bytes() -> int:
    """Return process high-water RSS in bytes (not current resident pages)."""
    import resource

    maximum = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return maximum if sys.platform == "darwin" else maximum * 1024


def _reaped_children_cpu_seconds() -> float:
    """CPU used by completed direct children, including metric helper processes."""
    import resource

    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return usage.ru_utime + usage.ru_stime


def supervise(
    output: Path,
    *,
    wall_cap_s: float = MAX_WALL_SECONDS,
    cpu_cap_s: float = MAX_CPU_SECONDS,
    validator: Callable[[Path], None] | None = None,
    provenance_mode: str = HISTORICAL_PROVENANCE,
    source_root: Path = Path.cwd(),
    _diagnostic_worker: bool = False,
) -> dict[str, object]:
    """Run only the fixed model-free worker and always leave a durable receipt."""
    if wall_cap_s <= 0 or cpu_cap_s <= 0:
        raise ValueError("caps must be positive")
    journal = BoundedJournal(output)
    started = time.monotonic()
    parent_cpu_started = time.process_time()
    children_cpu_started = _reaped_children_cpu_seconds()
    child: subprocess.Popen[bytes] | None = None
    failure = "worker_not_started"
    usage: dict[str, object] = {
        "aggregate_cpu_s": 0.0,
        "parent_cpu_s": 0.0,
        "child_cpu_s": 0.0,
        "rss_high_water_bytes": 0,
        "rss_measurement": (
            "sampled parent high-water plus live process group; platform-dependent; "
            "not hard aggregate enforcement"
        ),
        "cpu_measurement": (
            "parent plus sampled live process group and reaped direct-child usage; "
            "sampling may miss short-lived descendants"
        ),
    }
    lines: queue.Queue[bytes] = queue.Queue(maxsize=STDOUT_QUEUE_RECORDS)
    reader_status = _ReaderStatus(done=threading.Event())
    reader: threading.Thread | None = None
    live_child_cpu = 0.0
    try:
        command = (
            _a2_worker_command()
            if _diagnostic_worker
            else (
                _worker_command()
                if provenance_mode == HISTORICAL_PROVENANCE
                and source_root == Path.cwd()
                else _worker_command(provenance_mode, source_root)
            )
        )
        child = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=source_root,
            start_new_session=(os.name == "posix"),
            bufsize=0,
        )
        assert child.stdout is not None
        reader = threading.Thread(
            target=_read_lines, args=(child.stdout, lines, reader_status), daemon=True
        )
        reader.start()
        deadline = started + wall_cap_s
        while True:
            now = time.monotonic()
            remaining = deadline - now
            if remaining <= 0:
                failure = "wall_cap"
                break
            if reader_status.error is not None:
                failure = reader_status.error
                break
            try:
                line = lines.get(timeout=min(0.05, remaining))
            except queue.Empty:
                line = None
            if line is not None:
                journal.append(json.loads(line.decode("utf-8")))

            code = child.poll()
            if reader_status.error is not None:
                failure = reader_status.error
                break
            if code is not None and reader_status.done.is_set() and lines.empty():
                failure = "worker_exit" if code else "worker_completed"
                break

            metrics = _process_metrics(child.pid)
            parent_cpu = max(0.0, time.process_time() - parent_cpu_started)
            reaped_cpu = max(0.0, _reaped_children_cpu_seconds() - children_cpu_started)
            if metrics is None and code is None:
                failure = "resource_metrics_unavailable"
                break
            if metrics is not None:
                live_child_cpu = float(metrics["cpu_s"])
                observed_rss = int(metrics["rss_bytes"]) + _parent_rss_bytes()
                usage["rss_high_water_bytes"] = max(
                    cast(int, usage["rss_high_water_bytes"]), observed_rss
                )
            child_cpu = reaped_cpu + live_child_cpu
            aggregate_cpu = parent_cpu + child_cpu
            usage.update(
                {
                    "aggregate_cpu_s": aggregate_cpu,
                    "parent_cpu_s": parent_cpu,
                    "child_cpu_s": child_cpu,
                }
            )
            if aggregate_cpu > cpu_cap_s:
                failure = "cpu_cap"
                break
            if cast(int, usage["rss_high_water_bytes"]) > MAX_RSS_BYTES:
                failure = "rss_cap"
                break

        if not _terminate_and_reap(child):
            failure = "child_reap_timeout"
        if reader is not None:
            reader.join(timeout=max(0.2, min(1.0, wall_cap_s)))
            if reader.is_alive():
                failure = "stdout_reader_reap_timeout"
        journal.close()

        if failure == "worker_completed" and validator is not None:
            try:
                validator(output)
            except Exception as exc:
                failure = f"post_validation_error:{type(exc).__name__}"

        parent_cpu = max(0.0, time.process_time() - parent_cpu_started)
        reaped_cpu = max(0.0, _reaped_children_cpu_seconds() - children_cpu_started)
        child_cpu = max(reaped_cpu, live_child_cpu)
        aggregate_cpu = parent_cpu + child_cpu
        usage.update(
            {
                "aggregate_cpu_s": aggregate_cpu,
                "parent_cpu_s": parent_cpu,
                "child_cpu_s": child_cpu,
            }
        )
        if aggregate_cpu > cpu_cap_s and failure in {"worker_completed", "worker_exit"}:
            failure = "cpu_cap"
    except BaseException as exc:
        failure = f"supervisor_error:{type(exc).__name__}"
        if child is not None and not _terminate_and_reap(child):
            failure = "child_reap_timeout"
        if reader is not None:
            reader.join(timeout=1.0)
        journal.close()
        parent_cpu = max(0.0, time.process_time() - parent_cpu_started)
        reaped_cpu = max(0.0, _reaped_children_cpu_seconds() - children_cpu_started)
        usage.update(
            {
                "aggregate_cpu_s": parent_cpu + max(reaped_cpu, live_child_cpu),
                "parent_cpu_s": parent_cpu,
                "child_cpu_s": max(reaped_cpu, live_child_cpu),
            }
        )

    receipt_path = write_stop_receipt(
        output,
        reason=failure,
        journal=journal,
        started=started,
        resource_usage=usage,
        provenance_mode=provenance_mode,
    )
    return cast(dict[str, object], json.loads(receipt_path.read_text("utf-8")))


def _process_metrics(pid: int) -> dict[str, float | int] | None:
    """Sample CPU/RSS for the live child tree; this is not hard enforcement."""
    if sys.platform.startswith("linux"):
        try:
            rows: dict[int, tuple[int, float, int]] = {}
            for stat_path in Path("/proc").glob("[0-9]*/stat"):
                try:
                    raw = stat_path.read_text()
                    process_id = int(raw[: raw.find(" ")])
                    fields = raw[raw.rfind(")") + 2 :].split()
                    process_group = int(fields[2])
                    hz = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
                    cpu = (int(fields[11]) + int(fields[12])) / hz
                    rss = int(fields[21]) * os.sysconf("SC_PAGE_SIZE")
                    rows[process_id] = (process_group, cpu, rss)
                except OSError, ValueError, IndexError:
                    continue
            selected = [
                row
                for process_id, row in rows.items()
                if process_id == pid or row[0] == pid
            ]
            if not selected:
                return None
            return {
                "cpu_s": sum(row[1] for row in selected),
                "rss_bytes": sum(row[2] for row in selected),
            }
        except OSError, ValueError, IndexError:
            return None
    try:
        completed = subprocess.run(
            ["ps", "-axo", "pid=,ppid=,pgid=,rss=,cputime="],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=0.5,
            check=True,
        )
        rows: dict[int, tuple[int, int, float]] = {}
        for line in completed.stdout.splitlines():
            fields = line.split()
            if len(fields) != 5:
                continue
            process_id, _parent_id, process_group, rss_kib = map(int, fields[:4])
            if process_id == pid or process_group == pid:
                rows[process_id] = (
                    process_group,
                    rss_kib * 1024,
                    _parse_cpu_text(fields[4]),
                )
        selected = list(rows.values())
        if not selected:
            return None
        return {
            "rss_bytes": sum(row[1] for row in selected),
            "cpu_s": sum(row[2] for row in selected),
        }
    except (
        OSError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        ValueError,
    ):
        return None


def _parse_cpu_text(value: str) -> float:
    """Parse ps cputime with the frozen runner's day/hour/minute formats."""
    days = 0
    if "-" in value:
        day_text, value = value.split("-", 1)
        days = int(day_text)
    parts = [float(part) for part in value.split(":")]
    if len(parts) == 3:
        return days * 86400 + parts[0] * 3600 + parts[1] * 60 + parts[2]
    if len(parts) == 2:
        return days * 86400 + parts[0] * 60 + parts[1]
    if len(parts) == 1:
        return days * 86400 + parts[0]
    raise ValueError("unrecognized ps cputime")


def _plan_event(
    verified_sources: dict[str, str] | None = None,
    provenance_mode: str = HISTORICAL_PROVENANCE,
    source_root: Path = Path.cwd(),
) -> dict[str, object]:
    if verified_sources is None:
        verified_sources = verify_source_identity(provenance_mode, source_root)
    plan = schedule()
    digest = hashlib.sha256(
        canonical_json([case.__dict__ for case in plan])
    ).hexdigest()
    return {
        "kind": "frozen_plan_preflight",
        "provenance_mode": provenance_mode,
        "plan_sha256": digest,
        "case_count": len(plan),
        "total_substeps": sum(case.substeps for case in plan),
        "source_blobs": verified_sources,
    }


def validate_a2_diagnostic_output(
    directory: Path,
    expected_candidate_identity: dict[str, object] | None = None,
) -> None:
    """Fail closed on incomplete identities, controls, schema, or event stream."""
    path = directory / "events.jsonl"
    data = path.read_bytes()
    if len(data) + STOP_RECEIPT_RESERVE_BYTES > MAX_OUTPUT_BYTES:
        raise ReceiptError("diagnostic inclusive output cap exceeded")
    lines = data.splitlines()
    if not lines or len(lines) > MAX_EVENTS:
        raise ReceiptError("diagnostic record count is empty or over cap")
    try:
        rows = [json.loads(line) for line in lines]
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReceiptError("diagnostic JSONL is malformed") from exc
    if any(
        not isinstance(row, dict) or not isinstance(row.get("event"), dict)
        for row in rows
    ):
        raise ReceiptError("diagnostic event record is missing")
    events = [cast(dict[str, object], row["event"]) for row in rows]
    if [row.get("sequence") for row in rows] != list(range(1, len(rows) + 1)):
        raise ReceiptError("diagnostic sequence is incomplete")
    if any(event.get("schema") != "pymunk230-a2-first-event-v1" for event in events):
        raise ReceiptError("diagnostic schema identity mismatch")
    if events[0].get("kind") != "diagnostic_manifest":
        raise ReceiptError("diagnostic manifest is missing")
    manifest = events[0]
    if (
        manifest.get("fixture_id") != A2_CASE_ID
        or manifest.get("start") != list(A2_START)
        or manifest.get("action") != list(A2_ACTION)
        or manifest.get("resolutions") != [400, 800]
        or manifest.get("detail_window_inclusive") != list(DETAIL_WINDOW)
        or manifest.get("planned_substeps") != MAX_SUBSTEPS
        or manifest.get("cases_source_sha256") != FROZEN_CASES_SHA256
        or manifest.get("physics_source_sha256") != FROZEN_PHYSICS_SHA256
        or manifest.get("retry_policy") != "none"
    ):
        raise ReceiptError("diagnostic manifest identity mismatch")
    candidate_identity = manifest.get("candidate_source_identity")
    if (
        not isinstance(candidate_identity, dict)
        or not isinstance(candidate_identity.get("candidate_head"), str)
        or len(cast(str, candidate_identity.get("candidate_head"))) != 40
        or not isinstance(candidate_identity.get("authored_sources"), list)
        or (
            expected_candidate_identity is not None
            and candidate_identity != expected_candidate_identity
        )
    ):
        raise ReceiptError("diagnostic candidate identity mismatch")
    source_identity = manifest.get("source_content_identity")
    expected_sources = [
        {"path": path, "bytes": size, "blob_oid": oid, "sha256": sha256}
        for path, size, oid, sha256 in FROZEN_EXECUTABLE_SOURCES
    ]
    if (
        not isinstance(source_identity, dict)
        or source_identity.get("physics_sha256") != FROZEN_PHYSICS_SHA256
        or source_identity.get("historical_ancestry_proven") is not False
        or source_identity.get("sources") != expected_sources
        or not isinstance(source_identity.get("detached_inputs"), dict)
    ):
        raise ReceiptError("diagnostic manifest identity mismatch")
    if any(event.get("kind") == "diagnostic_child_error" for event in events):
        raise ReceiptError("diagnostic child reported an error")
    complete = [event for event in events if event.get("kind") == "diagnostic_complete"]
    if len(complete) != 1 or events[-1] is not complete[0]:
        raise ReceiptError("diagnostic completion record is missing or duplicated")
    if complete[0].get("total_substeps") != MAX_SUBSTEPS:
        raise ReceiptError("diagnostic completion accounting mismatch")
    summaries = [event for event in events if event.get("kind") == "command_summary"]
    if len(summaries) != 4:
        raise ReceiptError("A2 command summaries are incomplete")
    expected = {"a2_n400_cmd1", "a2_n400_cmd2", "a2_n800_cmd1", "a2_n800_cmd2"}
    if {event.get("case_id") for event in summaries} != expected:
        raise ReceiptError("A2 command identity mismatch")
    matched = [
        event
        for event in events
        if event.get("kind") == "matched_checkpoint_comparison"
    ]
    if len(matched) != len(CHECKPOINTS) * 2:
        raise ReceiptError("equal-time coarse checkpoint comparisons are incomplete")
    detailed_matches = [
        event for event in events if event.get("kind") == "matched_detail_comparison"
    ]
    expected_detail_matches = sum(
        1 for index in range(400) if DETAIL_WINDOW[0] <= index / 400 < DETAIL_WINDOW[1]
    )
    if len(detailed_matches) != expected_detail_matches:
        raise ReceiptError("equal-time detailed cmd2 comparisons are incomplete")
    if not any(event.get("kind") == "first_divergences" for event in events):
        raise ReceiptError("first divergence attribution is missing")
    controls = [event for event in events if event.get("kind") == "control_summary"]
    if len(controls) != 4 or any(
        event.get("contact_events") != [] for event in controls
    ):
        raise ReceiptError("empty-free controls are incomplete or contacted")
    for resolution in (400, 800):
        pair = [
            {
                key: value
                for key, value in event.items()
                if key not in {"case_id", "role"}
            }
            for event in controls
            if event.get("resolution") == resolution
        ]
        if len(pair) != 2 or pair[0] != pair[1]:
            raise ReceiptError("empty-free primary/fresh replay mismatch")


def supervise_a2_diagnostic(output: Path, *, approved_head: str) -> dict[str, object]:
    """Supervise the physics child only with an externally installed exact-SHA GO.

    This preparation task never sets the environment gate or calls this method.
    A later explicit Flow GO must be archived first and bound to the exact HEAD.
    """
    try:
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.PIPE
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ReceiptError("cannot verify exact execution candidate HEAD") from exc
    if (
        approved_head != head
        or os.environ.get("AWEFORM_A2_EXECUTION_GO_SHA") != head
        or len(head) != 40
    ):
        raise ReceiptError("fresh exact-HEAD A2 execution GO is absent")
    try:
        candidate_identity = verify_candidate_source_identity()
        if candidate_identity.get("candidate_head") != head:
            raise ReceiptError("candidate identity HEAD differs from approved HEAD")
        verify_a2_executable_identity()
    except ReceiptError as exc:
        started = time.monotonic()
        journal = BoundedJournal(output)
        journal.close()
        receipt_path = write_stop_receipt(
            output,
            reason=f"source_identity_error:{type(exc).__name__}",
            journal=journal,
            started=started,
            provenance_mode=DETACHED_PROVENANCE,
        )
        return cast(dict[str, object], json.loads(receipt_path.read_text("utf-8")))
    return supervise(
        output,
        validator=lambda directory: validate_a2_diagnostic_output(
            directory, candidate_identity
        ),
        provenance_mode=DETACHED_PROVENANCE,
        _diagnostic_worker=True,
    )


def supervise_frozen_plan(
    output: Path,
    provenance_mode: str = HISTORICAL_PROVENANCE,
    source_root: Path = Path.cwd(),
) -> dict[str, object]:
    """Supervise only the model-free frozen-plan worker; never step physics."""
    started = time.monotonic()
    try:
        expected = _plan_event(provenance_mode=provenance_mode, source_root=source_root)
    except ReceiptError as exc:
        # Source custody can fail before a child exists (for example, a shallow
        # or otherwise incomplete checkout). Still leave a hashed STOP receipt.
        journal = BoundedJournal(output)
        journal.close()
        receipt_path = write_stop_receipt(
            output,
            reason=f"preflight_error:{type(exc).__name__}",
            journal=journal,
            started=started,
            provenance_mode=provenance_mode,
        )
        return cast(dict[str, object], json.loads(receipt_path.read_text("utf-8")))

    expected_row = {"sequence": 1, "event": expected}

    def validate_plan_output(directory: Path) -> None:
        records = [
            json.loads(line)
            for line in (directory / "events.jsonl").read_text("utf-8").splitlines()
            if line
        ]
        if records != [expected_row]:
            raise ReceiptError("model-free supervised plan validation failed")

    return supervise(
        output,
        validator=validate_plan_output,
        provenance_mode=provenance_mode,
        source_root=source_root,
    )


def _model_free_worker(
    provenance_mode: str = HISTORICAL_PROVENANCE,
    source_root: Path = Path.cwd(),
) -> int:
    """Emit the verified frozen-plan identity; no simulator calls."""
    event = _plan_event(provenance_mode=provenance_mode, source_root=source_root)
    print(canonical_json(event).decode("utf-8"), flush=True)
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
        "--source-provenance",
        choices=(HISTORICAL_PROVENANCE, DETACHED_PROVENANCE),
        default=HISTORICAL_PROVENANCE,
    )
    parser.add_argument("--source-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--test-silent-worker", action="store_true", help=argparse.SUPPRESS
    )
    parser.add_argument(
        "--test-plan-worker", action="store_true", help=argparse.SUPPRESS
    )
    parser.add_argument(
        "--test-bad-plan-worker", action="store_true", help=argparse.SUPPRESS
    )
    parser.add_argument(
        "--test-flood-worker", action="store_true", help=argparse.SUPPRESS
    )
    args = parser.parse_args(argv)
    if args.test_silent_worker:
        time.sleep(10.0)
        return 0
    if args.test_plan_worker:
        return _model_free_test_worker()
    if args.test_bad_plan_worker:
        print(canonical_json({"kind": "wrong_plan"}).decode(), flush=True)
        return 0
    if args.test_flood_worker:
        sys.stdout.write("".join(f'{{"n":{index}}}\n' for index in range(100)))
        sys.stdout.flush()
        return 0
    if args.model_free_worker:
        return _model_free_worker(args.source_provenance, args.source_root)
    if args.supervise_preflight:
        if args.output is None:
            parser.error("--supervise-preflight requires --output")
        receipt = supervise_frozen_plan(
            args.output, args.source_provenance, args.source_root
        )
        print(canonical_json(receipt).decode("utf-8"))
        return 0 if receipt.get("reason") == "worker_completed" else 1
    if args.preflight:
        verified_sources = verify_source_identity(
            args.source_provenance, args.source_root
        )
        data = {
            "protocol": INSTRUMENTATION_PROTOCOL,
            "provenance_mode": args.source_provenance,
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
