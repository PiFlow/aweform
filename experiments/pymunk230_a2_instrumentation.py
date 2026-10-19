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
from typing import Any, cast

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
EMPTY_FREE_ACTION = "F×1"

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
    fixture: str
    role: str
    command: str
    start: tuple[float, float, float] | None
    action: str | None
    microsteps: int
    substeps: int


A2_CASES = (
    RunCase(
        "a2_n400_cmd1", "frozen_a2_convex", "primary", "cmd1", None, None, 400, 400
    ),
    RunCase(
        "a2_n400_cmd2", "frozen_a2_convex", "primary", "cmd2", None, None, 400, 400
    ),
    RunCase(
        "a2_n800_cmd1", "frozen_a2_convex", "primary", "cmd1", None, None, 800, 800
    ),
    RunCase(
        "a2_n800_cmd2", "frozen_a2_convex", "primary", "cmd2", None, None, 800, 800
    ),
    RunCase(
        "empty_free_n400_primary",
        "empty-free",
        "primary",
        "F×1",
        EMPTY_FREE_START,
        EMPTY_FREE_ACTION,
        400,
        400,
    ),
    RunCase(
        "empty_free_n400_replay",
        "empty-free",
        "fresh_replay",
        "F×1",
        EMPTY_FREE_START,
        EMPTY_FREE_ACTION,
        400,
        400,
    ),
    RunCase(
        "empty_free_n800_primary",
        "empty-free",
        "primary",
        "F×1",
        EMPTY_FREE_START,
        EMPTY_FREE_ACTION,
        800,
        800,
    ),
    RunCase(
        "empty_free_n800_replay",
        "empty-free",
        "fresh_replay",
        "F×1",
        EMPTY_FREE_START,
        EMPTY_FREE_ACTION,
        800,
        800,
    ),
)


def schedule() -> tuple[RunCase, ...]:
    """Return the immutable three-case schedule; never executes a transition."""
    if sum(c.substeps for c in A2_CASES) != MAX_SUBSTEPS:
        raise RuntimeError("frozen total substep accounting mismatch")
    if len({c.case_id for c in A2_CASES}) != len(A2_CASES):
        raise RuntimeError("duplicate frozen case")
    return A2_CASES


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
    if any(row.get("contact_events") for row in rows):
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
            "attempt3_head": FROZEN_ATTEMPT3_HEAD,
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
    except (ProcessLookupError, subprocess.TimeoutExpired):
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
        except (OSError, ValueError, IndexError):
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
    except (OSError, subprocess.CalledProcessError, ValueError):
        return None


def _model_free_worker() -> int:
    """Emit a model-free marker only; deliberately contains no simulator calls."""
    print(json.dumps({"kind": "model_free_worker_ready"}), flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--model-free-worker", action="store_true")
    parser.add_argument(
        "--test-silent-worker", action="store_true", help=argparse.SUPPRESS
    )
    args = parser.parse_args(argv)
    if args.test_silent_worker:
        time.sleep(10.0)
        return 0
    if args.model_free_worker:
        return _model_free_worker()
    if args.preflight:
        data = {
            "protocol": INSTRUMENTATION_PROTOCOL,
            "base_sha": BASE_SHA,
            "frozen_attempt3_head": FROZEN_ATTEMPT3_HEAD,
            "protocol_sha256": FROZEN_PROTOCOL_SHA256,
            "physics_sha256": FROZEN_PHYSICS_SHA256,
            "prefix_sha256": FROZEN_PREFIX_SHA256,
            "cases": [c.__dict__ for c in schedule()],
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
