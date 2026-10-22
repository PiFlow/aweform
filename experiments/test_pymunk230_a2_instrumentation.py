"""Model-free regression tests for A2-R1 custody and supervision only."""

from __future__ import annotations

import hashlib
import importlib.metadata
import io
import json
import os
import platform
import queue
import shutil
import signal
import subprocess
import sys
import threading
import time
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from experiments import pymunk230_a2_diagnostic as diagnostic
from experiments import pymunk230_a2_instrumentation as instrument


def _synthetic_frozen_blobs(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[bytes, bytes]:
    cases_blob = b"frozen cases fixture bytes\\n"
    prefix = b"frozen protocol prefix\\n"
    protocol_blob = (
        prefix + instrument.FROZEN_PROTOCOL_PREFIX_MARKER + b"\\nprotocol suffix\\n"
    )
    monkeypatch.setattr(
        instrument, "FROZEN_CASES_SHA256", hashlib.sha256(cases_blob).hexdigest()
    )
    monkeypatch.setattr(
        instrument, "FROZEN_PROTOCOL_SHA256", hashlib.sha256(protocol_blob).hexdigest()
    )
    monkeypatch.setattr(
        instrument, "FROZEN_PREFIX_SHA256", hashlib.sha256(prefix).hexdigest()
    )
    return cases_blob, protocol_blob


def _pinned_hash_claims() -> dict[str, str]:
    return {
        "cases_sha256": instrument.FROZEN_CASES_SHA256,
        "protocol_sha256": instrument.FROZEN_PROTOCOL_SHA256,
        "protocol_prefix_sha256": instrument.FROZEN_PREFIX_SHA256,
    }


def test_source_blobs_with_exact_hashes_are_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cases_blob, protocol_blob = _synthetic_frozen_blobs(monkeypatch)
    verified = instrument.verify_frozen_source_blobs(cases_blob, protocol_blob)
    assert verified == {
        "cases_sha256": instrument.FROZEN_CASES_SHA256,
        "protocol_sha256": instrument.FROZEN_PROTOCOL_SHA256,
        "protocol_prefix_sha256": instrument.FROZEN_PREFIX_SHA256,
    }


def test_frozen_source_blob_mismatch_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cases_blob, protocol_blob = _synthetic_frozen_blobs(monkeypatch)
    with pytest.raises(instrument.ReceiptError, match="cases.py SHA-256 mismatch"):
        instrument.verify_frozen_source_blobs(cases_blob + b"changed", protocol_blob)
    with pytest.raises(instrument.ReceiptError, match="protocol SHA-256 mismatch"):
        instrument.verify_frozen_source_blobs(cases_blob, protocol_blob + b"changed")


def _copy_disclosed_sources(root: Path) -> None:
    for relative in (instrument.FROZEN_CASES_PATH, instrument.FROZEN_PROTOCOL_PATH):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path.cwd() / relative, target)


def test_detached_clean_copy_preflight_receipts_content_provenance(
    tmp_path: Path,
) -> None:
    public_copy = tmp_path / "public-only-copy"
    _copy_disclosed_sources(public_copy)
    assert not (public_copy / ".git").exists()

    receipt = instrument.supervise_frozen_plan(
        tmp_path / "detached-preflight",
        instrument.DETACHED_PROVENANCE,
        public_copy,
    )

    assert receipt["reason"] == "worker_completed"
    assert receipt["status"] == "STOP"
    assert receipt["provenance_mode"] == instrument.DETACHED_PROVENANCE
    rows = [
        json.loads(line)
        for line in (tmp_path / "detached-preflight" / "events.jsonl")
        .read_text("utf-8")
        .splitlines()
    ]
    event = rows[0]["event"]
    assert event["provenance_mode"] == instrument.DETACHED_PROVENANCE
    assert event["total_substeps"] == 4_800
    sources = event["source_blobs"]
    assert sources["cases_blob_oid"] == instrument.FROZEN_CASES_BLOB_OID
    assert sources["protocol_blob_oid"] == instrument.FROZEN_PROTOCOL_BLOB_OID
    assert sources["cases_bytes"] == str(instrument.FROZEN_CASES_BYTES)
    assert sources["protocol_bytes"] == str(instrument.FROZEN_PROTOCOL_BYTES)
    assert sources["cases_sha256"] == instrument.FROZEN_CASES_SHA256
    assert sources["protocol_sha256"] == instrument.FROZEN_PROTOCOL_SHA256
    assert sources["protocol_prefix_sha256"] == instrument.FROZEN_PREFIX_SHA256
    assert sources["historical_ancestry_proven"] == "false"
    durable = cast(dict[str, int | str], receipt["last_durable"])
    assert durable["sequence"] == 1
    assert (
        durable["sha256"]
        == hashlib.sha256(
            (tmp_path / "detached-preflight" / "events.jsonl").read_bytes()
        ).hexdigest()
    )


def test_detached_source_rejects_substitution_and_missing_file(
    tmp_path: Path,
) -> None:
    public_copy = tmp_path / "public-only-copy"
    _copy_disclosed_sources(public_copy)
    cases = public_copy / instrument.FROZEN_CASES_PATH
    original = cases.read_bytes()
    cases.write_bytes(b"X" + original[1:])
    with pytest.raises(instrument.ReceiptError, match="SHA-256 mismatch"):
        instrument.verify_detached_source_identity(public_copy)

    cases.unlink()
    with pytest.raises(instrument.ReceiptError, match="missing detached source file"):
        instrument.verify_detached_source_identity(public_copy)
    receipt = instrument.supervise_frozen_plan(
        tmp_path / "missing-detached-source",
        instrument.DETACHED_PROVENANCE,
        public_copy,
    )
    assert receipt["status"] == "STOP"
    assert receipt["reason"] == "preflight_error:ReceiptError"
    assert receipt["provenance_mode"] == instrument.DETACHED_PROVENANCE
    durable = cast(dict[str, object], receipt["last_durable"])
    assert durable["sequence"] == 0


def test_missing_authoritative_frozen_blob_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subprocess,
        "check_output",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            subprocess.CalledProcessError(128, "git show")
        ),
    )
    with pytest.raises(instrument.ReceiptError, match="missing frozen source blob"):
        instrument.verify_frozen_source_identity()


def test_frozen_plan_accounts_for_exact_substeps_without_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = instrument.schedule()
    assert [case.case_id for case in plan] == [
        "a2_n400_cmd1",
        "a2_n400_cmd2",
        "a2_n800_cmd1",
        "a2_n800_cmd2",
        "empty_free_n400_primary",
        "empty_free_n400_replay",
        "empty_free_n800_primary",
        "empty_free_n800_replay",
    ]
    assert all(case.fixture_id == "A2-convex-face" for case in plan[:4])
    assert all(case.fixture_id == "empty-free" for case in plan[4:])
    assert [case.command_id for case in plan[:4]] == ["cmd1", "cmd2", "cmd1", "cmd2"]
    assert [case.start for case in plan[:4]] == [instrument.A2_START] * 4
    assert [case.action for case in plan[:4]] == [instrument.A2_ACTION] * 4
    assert [case.start for case in plan[4:]] == [(1.0, 1.0, 0.0)] * 4
    assert [case.role for case in plan[4:]] == [
        "primary",
        "fresh_replay",
        "primary",
        "fresh_replay",
    ]
    assert sum(case.substeps for case in plan) == 4_800
    assert instrument.CHECKPOINTS == (
        ("cmd1", 0.0),
        ("cmd1", 0.25),
        ("cmd1", 0.5),
        ("cmd1", 0.75),
        ("cmd1", 1.0),
        ("cmd2", 0.0),
        ("cmd2", 0.25),
        ("cmd2", 0.5),
        ("cmd2", 0.75),
        ("cmd2", 0.85),
        ("cmd2", 0.9),
        ("cmd2", 0.98),
        ("cmd2", 1.0),
    )
    assert instrument.DETAIL_WINDOW == (0.85, 0.98)
    assert instrument.EMPTY_FREE_START == (1.0, 1.0, 0.0)
    assert instrument.EMPTY_FREE_ACTION == (0.6457718232379019, 0.6457718232379019)
    assert all(case.control_requires_no_contact for case in plan[4:])
    assert all(case.full_fixture_expected_objects == ("A2",) for case in plan[:4])
    instrument.validate_plan(plan, instrument.FROZEN_IDENTITY)
    monkeypatch.setattr(
        instrument, "verify_frozen_source_identity", lambda: _pinned_hash_claims()
    )
    assert instrument.main(["--preflight"]) == 0


def test_preflight_refuses_identity_command_and_accounting_mismatch() -> None:
    plan = instrument.schedule()
    with pytest.raises(instrument.ReceiptError, match="identity mismatch"):
        instrument.validate_plan(
            plan,
            replace(instrument.FROZEN_IDENTITY, cases_source_sha256="0" * 64),
        )
    with pytest.raises(instrument.ReceiptError, match="accounting mismatch"):
        instrument.validate_plan(
            (replace(plan[0], substeps=plan[0].substeps + 1), *plan[1:]),
            instrument.FROZEN_IDENTITY,
        )
    with pytest.raises(instrument.ReceiptError, match="fixture/commands"):
        instrument.validate_plan(
            (replace(plan[0], action=(0.0, 0.0)), *plan[1:]),
            instrument.FROZEN_IDENTITY,
        )


def test_missing_frozen_blob_preflight_writes_durable_stop_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "missing-source"
    monkeypatch.setattr(
        instrument,
        "verify_frozen_source_identity",
        lambda: (_ for _ in ()).throw(
            instrument.ReceiptError("missing frozen source blob: protocol.md")
        ),
    )

    receipt = instrument.supervise_frozen_plan(output)

    assert receipt["status"] == "STOP"
    assert receipt["reason"] == "preflight_error:ReceiptError"
    assert receipt["last_durable"] == {
        "sequence": 0,
        "bytes": 0,
        "sha256": hashlib.sha256(b"").hexdigest(),
    }
    path = output / "STOP.json"
    checksum = (output / "STOP.sha256").read_text("ascii")
    assert checksum == f"{hashlib.sha256(path.read_bytes()).hexdigest()}  STOP.json\n"
    assert (
        sum(item.stat().st_size for item in output.iterdir())
        <= instrument.MAX_OUTPUT_BYTES
    )


def test_cli_supervised_preflight_binds_plan_without_physics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "preflight"
    monkeypatch.setattr(
        instrument, "verify_frozen_source_identity", lambda: _pinned_hash_claims()
    )
    monkeypatch.setattr(
        instrument,
        "_worker_command",
        lambda: [
            sys.executable,
            str(Path(instrument.__file__).resolve()),
            "--test-plan-worker",
        ],
    )
    assert instrument.main(["--supervise-preflight", "--output", str(output)]) == 0
    receipt = json.loads((output / "STOP.json").read_text("utf-8"))
    rows = [
        json.loads(line) for line in (output / "events.jsonl").read_text().splitlines()
    ]
    assert receipt["reason"] == "worker_completed"
    assert rows[0]["event"]["kind"] == "frozen_plan_preflight"
    assert rows[0]["event"]["total_substeps"] == 4_800


def test_preflight_waits_for_reader_eof_and_drains_trailing_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        instrument, "verify_frozen_source_identity", lambda: _pinned_hash_claims()
    )
    monkeypatch.setattr(
        instrument,
        "_worker_command",
        lambda: [
            sys.executable,
            str(Path(instrument.__file__).resolve()),
            "--test-plan-worker",
        ],
    )
    read_lines = instrument._read_lines

    def delayed_reader(
        stream: object, target: queue.Queue[bytes], status: object
    ) -> None:
        time.sleep(0.05)
        read_lines(stream, target, status)  # type: ignore[arg-type]

    monkeypatch.setattr(instrument, "_read_lines", delayed_reader)

    receipt = instrument.supervise_frozen_plan(tmp_path / "eof-race")

    assert receipt["reason"] == "worker_completed"
    durable = cast(dict[str, int | str], receipt["last_durable"])
    assert durable["sequence"] == 1


def test_post_validation_failure_is_receipted_as_stop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "invalid-plan"
    monkeypatch.setattr(
        instrument, "verify_frozen_source_identity", lambda: _pinned_hash_claims()
    )
    monkeypatch.setattr(
        instrument,
        "_worker_command",
        lambda: [
            sys.executable,
            str(Path(instrument.__file__).resolve()),
            "--test-bad-plan-worker",
        ],
    )

    receipt = instrument.supervise_frozen_plan(output)

    assert receipt["status"] == "STOP"
    assert receipt["reason"] == "post_validation_error:ReceiptError"
    durable = cast(dict[str, int | str], receipt["last_durable"])
    assert durable["sequence"] == 1
    assert (
        durable["sha256"]
        == hashlib.sha256((output / "events.jsonl").read_bytes()).hexdigest()
    )
    checksum = (output / "STOP.sha256").read_text("ascii")
    receipt_hash = hashlib.sha256((output / "STOP.json").read_bytes()).hexdigest()
    assert checksum == f"{receipt_hash}  STOP.json\n"


def test_reader_queue_overflow_is_bounded_and_reported() -> None:
    target: queue.Queue[bytes] = queue.Queue(maxsize=1)
    status = instrument._ReaderStatus(done=threading.Event())

    instrument._read_lines(io.BytesIO(b'{"n":1}\n{"n":2}\n'), target, status)

    assert status.done.is_set()
    assert status.error == "stdout_queue_overflow"
    assert target.qsize() == 1


def test_supervisor_receipts_stdout_queue_overflow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(instrument, "STDOUT_QUEUE_RECORDS", 1)
    monkeypatch.setattr(
        instrument,
        "_worker_command",
        lambda: [
            sys.executable,
            str(Path(instrument.__file__).resolve()),
            "--test-flood-worker",
        ],
    )
    append = instrument.BoundedJournal.append

    def slow_append(self: instrument.BoundedJournal, event: dict[str, object]) -> None:
        time.sleep(0.05)
        append(self, event)

    monkeypatch.setattr(instrument.BoundedJournal, "append", slow_append)
    receipt = instrument.supervise(tmp_path / "queue-overflow", wall_cap_s=2.0)

    assert receipt["reason"] == "stdout_queue_overflow"
    usage = cast(dict[str, float | int], receipt["resource_usage"])
    assert usage["rss_high_water_bytes"] <= instrument.MAX_RSS_BYTES


def test_legacy_eight_record_queue_reproduces_legitimate_burst_overflow() -> None:
    target: queue.Queue[bytes] = queue.Queue(maxsize=8)
    status = instrument._ReaderStatus(done=threading.Event())
    burst = b"".join(instrument.canonical_json({"i": i}) + b"\n" for i in range(113))
    instrument._read_lines(io.BytesIO(burst), target, status)
    assert status.error == "stdout_queue_overflow"
    assert target.qsize() == 8


def test_supervisor_drains_prescribed_bursts_at_default_bounded_capacity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert instrument.STDOUT_QUEUE_RECORDS == 128
    assert instrument.MAX_EVENTS == 10_000
    assert instrument.MAX_OUTPUT_BYTES == 2 * 1024 * 1024
    monkeypatch.setattr(
        instrument, "_process_metrics", lambda _pid: {"cpu_s": 0.0, "rss_bytes": 1}
    )
    for count in (61, 113, 66):
        output = tmp_path / f"burst-{count}"
        script = (
            "import json,sys; "
            "sys.stdout.write(''.join(json.dumps({'i':i},separators=(',',':'))+'\\n' "
            f"for i in range({count}))); sys.stdout.flush()"
        )
        monkeypatch.setattr(
            instrument,
            "_worker_command",
            lambda script=script: [sys.executable, "-c", script],
        )
        receipt = instrument.supervise(output, wall_cap_s=5.0)
        assert receipt["reason"] == "worker_completed"
        assert cast(dict[str, object], receipt["last_durable"])["sequence"] == count
        assert len((output / "events.jsonl").read_bytes().splitlines()) == count


def test_supervisor_event_cap_preserves_partial_flood_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(instrument, "MAX_EVENTS", 10)
    script = (
        "import json,sys; "
        "sys.stdout.write(''.join(json.dumps({'i':i})+'\\n' for i in range(100))); "
        "sys.stdout.flush()"
    )
    monkeypatch.setattr(
        instrument, "_worker_command", lambda: [sys.executable, "-c", script]
    )
    receipt = instrument.supervise(tmp_path / "event-cap", wall_cap_s=5.0)
    assert receipt["reason"] == "supervisor_error:ReceiptError"
    assert cast(dict[str, object], receipt["last_durable"])["sequence"] == 10
    digest = hashlib.sha256(
        (tmp_path / "event-cap" / "STOP.json").read_bytes()
    ).hexdigest()
    assert (tmp_path / "event-cap" / "STOP.sha256").read_text(
        "ascii"
    ) == f"{digest}  STOP.json\n"


def test_aggregate_cpu_cap_includes_parent_and_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        instrument,
        "_worker_command",
        lambda: [
            sys.executable,
            str(Path(instrument.__file__).resolve()),
            "--test-silent-worker",
        ],
    )
    monkeypatch.setattr(
        instrument, "_process_metrics", lambda _pid: {"cpu_s": 0.4, "rss_bytes": 1}
    )
    monkeypatch.setattr(instrument, "_reaped_children_cpu_seconds", lambda: 0.0)
    calls = 0

    def parent_cpu() -> float:
        nonlocal calls
        calls += 1
        return 10.0 if calls == 1 else 10.8

    monkeypatch.setattr(time, "process_time", parent_cpu)
    receipt = instrument.supervise(
        tmp_path / "aggregate-cpu", wall_cap_s=2.0, cpu_cap_s=1.0
    )

    assert receipt["reason"] == "cpu_cap"
    usage = cast(dict[str, float | int], receipt["resource_usage"])
    assert usage["parent_cpu_s"] == pytest.approx(0.8)
    assert usage["child_cpu_s"] == 0.4
    assert usage["aggregate_cpu_s"] == pytest.approx(1.2)


def test_stop_receipt_exposes_durable_watermark_and_hash(tmp_path: Path) -> None:
    output = tmp_path / "result"
    journal = instrument.BoundedJournal(output)
    journal.append({"kind": "checkpoint", "case": "cmd1", "progress": 0.0})
    durable = journal.last_durable
    journal.close()

    path = instrument.write_stop_receipt(
        output, reason="test_stop", journal=journal, started=0.0
    )
    receipt = json.loads(path.read_text("utf-8"))
    assert receipt["last_durable"] == durable
    assert receipt["identity"]["cases_source_sha256"] == instrument.FROZEN_CASES_SHA256
    assert "payload" not in receipt
    checksum = (output / "STOP.sha256").read_text("ascii")
    assert checksum == f"{hashlib.sha256(path.read_bytes()).hexdigest()}  STOP.json\n"
    assert (
        durable["sha256"]
        == hashlib.sha256((output / "events.jsonl").read_bytes()).hexdigest()
    )
    assert (
        sum(path.stat().st_size for path in output.iterdir())
        <= instrument.MAX_OUTPUT_BYTES
    )


def test_silent_child_wall_cap_kills_reaps_and_writes_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        instrument,
        "_worker_command",
        lambda: [
            sys.executable,
            str(Path(instrument.__file__).resolve()),
            "--test-silent-worker",
        ],
    )
    monkeypatch.setattr(
        instrument, "_process_metrics", lambda _pid: {"cpu_s": 0.0, "rss_bytes": 0}
    )
    started = time.monotonic()
    receipt = instrument.supervise(tmp_path / "result", wall_cap_s=0.15)
    elapsed = time.monotonic() - started
    assert receipt["status"] == "STOP"
    assert receipt["reason"] == "wall_cap"
    assert elapsed < 2.0
    receipt_path = tmp_path / "result" / "STOP.json"
    checksum = (tmp_path / "result" / "STOP.sha256").read_text("ascii")
    assert (
        checksum
        == f"{hashlib.sha256(receipt_path.read_bytes()).hexdigest()}  STOP.json\n"
    )
    assert isinstance(receipt["last_durable"], dict)
    assert receipt["last_durable"]["sequence"] == 0


def test_cpu_cap_is_parent_observed_and_receipted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        instrument,
        "_worker_command",
        lambda: [
            sys.executable,
            str(Path(instrument.__file__).resolve()),
            "--test-silent-worker",
        ],
    )
    monkeypatch.setattr(
        instrument, "_process_metrics", lambda _pid: {"cpu_s": 2.0, "rss_bytes": 1}
    )
    receipt = instrument.supervise(tmp_path / "result", wall_cap_s=2.0, cpu_cap_s=1.0)
    assert receipt["reason"] == "cpu_cap"
    assert (tmp_path / "result" / "STOP.sha256").is_file()


def test_rss_cap_is_parent_observed_and_receipted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        instrument,
        "_worker_command",
        lambda: [
            sys.executable,
            str(Path(instrument.__file__).resolve()),
            "--test-silent-worker",
        ],
    )
    monkeypatch.setattr(
        instrument,
        "_process_metrics",
        lambda _pid: {"cpu_s": 0.0, "rss_bytes": instrument.MAX_RSS_BYTES + 1},
    )
    receipt = instrument.supervise(tmp_path / "result", wall_cap_s=2.0)
    assert receipt["reason"] == "rss_cap"


def test_unavailable_resource_metrics_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        instrument,
        "_worker_command",
        lambda: [
            sys.executable,
            str(Path(instrument.__file__).resolve()),
            "--test-silent-worker",
        ],
    )
    monkeypatch.setattr(instrument, "_process_metrics", lambda _pid: None)
    receipt = instrument.supervise(tmp_path / "result", wall_cap_s=2.0)
    assert receipt["reason"] == "resource_metrics_unavailable"


def test_writer_error_preserves_durable_stop_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        instrument,
        "_worker_command",
        lambda: [
            sys.executable,
            str(Path(instrument.__file__).resolve()),
            "--test-plan-worker",
        ],
    )
    monkeypatch.setattr(
        instrument.BoundedJournal,
        "append",
        lambda _self, _event: (_ for _ in ()).throw(OSError("disk full")),
    )
    receipt = instrument.supervise(tmp_path / "result", wall_cap_s=2.0)
    assert receipt["status"] == "STOP"
    assert receipt["reason"] == "supervisor_error:OSError"
    assert isinstance(receipt["last_durable"], dict)
    assert receipt["last_durable"]["sequence"] == 0
    assert (tmp_path / "result" / "STOP.sha256").is_file()


def test_partial_journal_write_is_truncated_before_stop_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "partial-write"
    journal = instrument.BoundedJournal(output)
    import os

    real_fsync = os.fsync
    calls = 0

    def fail_once(fd: int) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("synthetic fsync failure")
        real_fsync(fd)

    monkeypatch.setattr(os, "fsync", fail_once)
    with pytest.raises(OSError, match="synthetic fsync failure"):
        journal.append({"payload": "complete-or-truncate"})
    assert journal.last_durable["sequence"] == 0
    assert (output / "events.jsonl").read_bytes() == b""
    journal.close()
    receipt = instrument.write_stop_receipt(
        output, reason="writer_failure", journal=journal, started=0.0
    )
    assert json.loads(receipt.read_text())["last_durable"]["sequence"] == 0
    checksum = (output / "STOP.sha256").read_text("ascii")
    assert (
        checksum == f"{hashlib.sha256(receipt.read_bytes()).hexdigest()}  STOP.json\n"
    )


def test_event_record_and_inclusive_byte_caps_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "records"
    journal = instrument.BoundedJournal(output)
    monkeypatch.setattr(instrument, "MAX_EVENTS", 1)
    journal.append({"n": 1})
    with pytest.raises(instrument.ReceiptError, match="record limit"):
        journal.append({"n": 2})
    journal.close()
    receipt_path = instrument.write_stop_receipt(
        output, reason="event_limit", journal=journal, started=0.0
    )
    assert json.loads(receipt_path.read_text())["last_durable"]["sequence"] == 1

    output2 = tmp_path / "bytes"
    journal2 = instrument.BoundedJournal(output2)
    monkeypatch.setattr(instrument, "MAX_EVENTS", 10)
    monkeypatch.setattr(instrument, "MAX_OUTPUT_BYTES", 4_120)
    with pytest.raises(instrument.ReceiptError, match="byte limit"):
        journal2.append({"payload": "x" * 100})
    journal2.close()
    receipt_path2 = instrument.write_stop_receipt(
        output2, reason="output_limit", journal=journal2, started=0.0
    )
    assert json.loads(receipt_path2.read_text())["status"] == "STOP"
    assert (
        sum(path.stat().st_size for path in output2.iterdir())
        <= instrument.MAX_OUTPUT_BYTES
    )


def test_empty_free_control_requires_replay_identity_and_zero_contacts() -> None:
    empty = b'{"contact_events":[]}\n'
    instrument.validate_empty_free_control(empty, empty)
    with pytest.raises(instrument.ReceiptError, match="bytes differ"):
        instrument.validate_empty_free_control(empty, b'{"contact_events":[]}\n{}\n')
    with pytest.raises(instrument.ReceiptError, match="contact events"):
        instrument.validate_empty_free_control(
            b'{"contact_events":[{"shape":"wall"}]}\n',
            b'{"contact_events":[{"shape":"wall"}]}\n',
        )
    with pytest.raises(instrument.ReceiptError, match="missing contact-event"):
        instrument.validate_empty_free_control(b'{"progress":1}\n', b'{"progress":1}\n')


def test_a2_frozen_six_file_content_identity_is_recomputed_model_free() -> None:
    identity = instrument.verify_a2_executable_identity()
    assert identity["physics_sha256"] == instrument.FROZEN_PHYSICS_SHA256
    assert identity["historical_ancestry_proven"] is False
    assert len(identity["sources"]) == 6  # type: ignore[arg-type]


def test_diagnostic_module_import_is_model_free() -> None:
    assert "pymunk" not in sys.modules
    assert diagnostic.SCHEMA == "pymunk230-a2-first-event-v2"


def test_worker_launch_import_topology_fails_old_script_and_passes_closed_module() -> (
    None
):
    root = Path(__file__).resolve().parents[1]
    environment = dict(os.environ)
    environment.pop("AWEFORM_A2_EXECUTION_GO_SHA", None)
    old_script = subprocess.run(
        [
            sys.executable,
            str(Path(diagnostic.__file__).resolve()),
            "--diagnostic-child",
        ],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert old_script.returncode != 0
    assert "No module named 'experiments'" in old_script.stderr

    command = instrument._a2_worker_command()
    assert command[1:3] == ["-m", "experiments.pymunk230_a2_diagnostic"]
    repaired = subprocess.run(
        command,
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=5,
    )
    row = json.loads(repaired.stdout)
    assert repaired.returncode == 2
    assert row["error_type"] == "ExecutionGateClosed"
    assert row["pymunk_module_loaded"] is False


def test_runtime_identity_is_verified_from_metadata_without_pymunk_import(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wheel = tmp_path / "pymunk.whl"
    wheel.write_bytes(b"synthetic wheel identity")
    sha256 = hashlib.sha256(wheel.read_bytes()).hexdigest()
    monkeypatch.setattr(sys, "version", f"{instrument.EXPECTED_PYTHON} test")
    monkeypatch.setattr(importlib.metadata, "version", lambda name: "7.2.0")
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    monkeypatch.setattr(platform, "machine", lambda: "arm64")
    monkeypatch.setattr(instrument, "EXPECTED_PYMUNK_WHEEL_SHA256", sha256)
    monkeypatch.setenv("PYMUNK_WHEEL_PATH", str(wheel))
    identity = instrument.verify_runtime_identity()
    assert identity == {
        "python": "3.14.7",
        "pymunk": "7.2.0",
        "platform": "darwin",
        "machine": "arm64",
        "pymunk_wheel_sha256": sha256,
    }
    assert "pymunk" not in sys.modules

    monkeypatch.setattr(importlib.metadata, "version", lambda _name: "9.9")
    with pytest.raises(instrument.ReceiptError, match="expected Pymunk"):
        instrument.verify_runtime_identity()
    monkeypatch.setattr(importlib.metadata, "version", lambda _name: "7.2.0")
    monkeypatch.setattr(platform, "machine", lambda: "x86_64")
    with pytest.raises(instrument.ReceiptError, match="unsupported runtime platform"):
        instrument.verify_runtime_identity()
    monkeypatch.setattr(platform, "machine", lambda: "arm64")
    monkeypatch.setattr(instrument, "EXPECTED_PYMUNK_WHEEL_SHA256", "0" * 64)
    with pytest.raises(instrument.ReceiptError, match="wheel SHA-256"):
        instrument.verify_runtime_identity()
    monkeypatch.delenv("PYMUNK_WHEEL_PATH")
    with pytest.raises(instrument.ReceiptError, match="PYMUNK_WHEEL_PATH"):
        instrument.verify_runtime_identity()


def test_a2_output_must_not_dirty_the_candidate_tree(tmp_path: Path) -> None:
    with pytest.raises(
        instrument.ReceiptError, match="outside the clean candidate tree"
    ):
        instrument._validate_a2_output_location(tmp_path / "out", tmp_path)
    instrument._validate_a2_output_location(tmp_path.parent / "outside", tmp_path)


def test_step_observer_captures_numeric_state_and_restores_wrapper() -> None:
    class Vector:
        x = 1.0
        y = 2.0

    class Body:
        position = Vector()
        angle = 0.25
        velocity = Vector()
        angular_velocity = 0.5

    class Space:
        def __init__(self, body: object) -> None:
            self.body = body

        def step(self, _dt: float) -> None:
            self.body.position.x += 0.1  # type: ignore[attr-defined]
            self.body.angle += 0.2  # type: ignore[attr-defined]

    class World:
        body = Body()
        space = Space(body)
        suppress_velocity_refresh_after_contact = True
        _contact_seen_this_command = False
        _contact_events: list[object] = []

    world = World()
    original = world.space.step
    samples = diagnostic._step_observer(world, "cmd2", 1)
    world.space.step(0.01)
    diagnostic._restore_step_observer(world)
    assert world.space.step == original
    assert samples[0]["command_id"] == "cmd2"
    assert samples[0]["before"]["position_m"] == [1.0, 2.0]  # type: ignore[index]
    assert samples[0]["after"]["position_m"] == [1.1, 2.0]  # type: ignore[index]
    assert samples[0]["motor_refresh_applied"] is True


def _write_synthetic_diagnostic_stream(
    path: Path, *, bad_control: bool = False
) -> None:
    events: list[dict[str, object]] = [
        {
            "kind": "diagnostic_manifest",
            "schema": diagnostic.SCHEMA,
            "fixture_id": instrument.A2_CASE_ID,
            "start": list(instrument.A2_START),
            "action": list(instrument.A2_ACTION),
            "resolutions": [400, 800],
            "detail_window_inclusive": list(instrument.DETAIL_WINDOW),
            "planned_substeps": instrument.MAX_SUBSTEPS,
            "cases_source_sha256": instrument.FROZEN_CASES_SHA256,
            "physics_source_sha256": instrument.FROZEN_PHYSICS_SHA256,
            "source_content_identity": instrument.verify_a2_executable_identity(),
            "candidate_source_identity": {
                "candidate_head": "a" * 40,
                "authored_sources": [],
            },
            "runtime_identity": {
                "python": instrument.EXPECTED_PYTHON,
                "pymunk": instrument.EXPECTED_PYMUNK,
                "platform": instrument.EXPECTED_PLATFORM[0],
                "machine": instrument.EXPECTED_PLATFORM[1],
                "pymunk_wheel_sha256": instrument.EXPECTED_PYMUNK_WHEEL_SHA256,
            },
            "retry_policy": "none",
        }
    ]
    for resolution in (400, 800):
        for command in ("cmd1", "cmd2"):
            events.append(
                {
                    "kind": "command_summary",
                    "schema": diagnostic.SCHEMA,
                    "case_id": f"a2_n{resolution}_{command}",
                    "substeps": resolution,
                }
            )

    def state(progress: float) -> dict[str, object]:
        return {
            "position_m": [progress, 0.0],
            "heading_rad": 0.0,
            "velocity_mps": [1.0, 0.0],
            "angular_velocity_rps": 0.0,
        }

    def sample(index: int, resolution: int) -> dict[str, object]:
        return {
            "substep": index,
            "before": state(index / resolution),
            "after": state((index + 1) / resolution),
            "contact_set": [],
            "callbacks": [],
            "motor_refresh_applied": True,
            "motor_velocity_before_step_mps": [1.0, 0.0],
            "motor_angular_velocity_before_step_rps": 0.0,
        }

    for resolution in (400, 800):
        for command in ("cmd1", "cmd2"):
            for checkpoint_command, progress in instrument.CHECKPOINTS:
                if checkpoint_command != command:
                    continue
                endpoint = int(round(progress * resolution))
                width = resolution // 400
                interval = (
                    []
                    if endpoint == 0
                    else [
                        sample(index, resolution)
                        for index in range(endpoint - width, endpoint)
                    ]
                )
                last = interval[-1] if interval else sample(0, resolution)
                events.append(
                    {
                        "kind": "checkpoint",
                        "schema": diagnostic.SCHEMA,
                        "case_id": f"a2_n{resolution}_{command}",
                        "fixture_id": instrument.A2_CASE_ID,
                        "resolution": resolution,
                        "command_id": command,
                        "command_progress": progress,
                        "substep": endpoint,
                        "state": state(progress),
                        "interval_samples": interval,
                        "contact_set": last["contact_set"],
                        "callbacks": last["callbacks"],
                        "motor_refresh_applied": last["motor_refresh_applied"],
                        "motor_velocity_before_step_mps": last[
                            "motor_velocity_before_step_mps"
                        ],
                        "motor_angular_velocity_before_step_rps": last[
                            "motor_angular_velocity_before_step_rps"
                        ],
                    }
                )
        for index in range(resolution):
            progress = index / resolution
            end = (index + 1) / resolution
            if instrument.DETAIL_WINDOW[0] <= progress < instrument.DETAIL_WINDOW[1]:
                events.append(
                    {
                        "kind": "detail",
                        "schema": diagnostic.SCHEMA,
                        "case_id": f"a2_n{resolution}_cmd2",
                        "fixture_id": instrument.A2_CASE_ID,
                        "resolution": resolution,
                        "command_id": "cmd2",
                        "command_progress": progress,
                        "command_end_progress": end,
                        **sample(index, resolution),
                    }
                )

    for command, progress in instrument.CHECKPOINTS:
        low_index = int(round(progress * 400))
        high_index = 2 * low_index
        checkpoint_rows = {
            (row["resolution"], row["command_id"], row["command_progress"]): row
            for row in events
            if row.get("kind") == "checkpoint"
        }
        low = checkpoint_rows[(400, command, progress)]
        high = checkpoint_rows[(800, command, progress)]
        events.append(
            {
                "kind": "matched_checkpoint_comparison",
                "schema": diagnostic.SCHEMA,
                "command_id": command,
                "command_progress": progress,
                "n400_endpoint_substep": low_index,
                "n800_endpoint_substep": high_index,
                "n800_interval_substeps": []
                if low_index == 0
                else [2 * low_index - 2, 2 * low_index - 1],
                "equal_physical_endpoint": True,
                "n400": low,
                "n800": high,
            }
        )
    for index in range(400):
        start = index / 400
        if instrument.DETAIL_WINDOW[0] <= start < instrument.DETAIL_WINDOW[1]:
            raw_details = {
                (row["resolution"], row["substep"]): row
                for row in events
                if row.get("kind") == "detail"
            }
            low = raw_details[(400, index)]
            high_first = raw_details[(800, index * 2)]
            high_second = raw_details[(800, index * 2 + 1)]
            events.append(
                {
                    "kind": "matched_detail_comparison",
                    "schema": diagnostic.SCHEMA,
                    "interval_start_progress": start,
                    "interval_end_progress": (index + 1) / 400,
                    "n800_interval_substeps": [index * 2, index * 2 + 1],
                    "equal_physical_endpoint": True,
                    "n400": {"state": low["after"], "interval_samples": [low]},
                    "n800": {
                        "state": high_second["after"],
                        "interval_samples": [high_first, high_second],
                    },
                }
            )
    events.append(
        {
            "kind": "first_divergences",
            "schema": diagnostic.SCHEMA,
            "by_category": {
                name: None
                for name in (
                    "contact_or_chord_set",
                    "callback_values",
                    "motor_refresh_decision",
                    "motor_state_above_roundoff_floor",
                    "pose_heading_or_velocity_above_roundoff_floor",
                )
            },
        }
    )
    for resolution in (400, 800):
        for role in ("primary", "fresh_replay"):
            events.append(
                {
                    "kind": "control_summary",
                    "schema": diagnostic.SCHEMA,
                    "case_id": f"empty_free_n{resolution}_{role}",
                    "role": role,
                    "resolution": resolution,
                    "fixture_id": "empty-free",
                    "start": list(instrument.EMPTY_FREE_START),
                    "action": list(instrument.EMPTY_FREE_ACTION),
                    "end_m": [1.1, 1.0],
                    "end_heading_rad": 0.0,
                    "velocity_mps": [1.0, 0.0],
                    "angular_velocity_rps": 0.0,
                    "contact_events": [{"bad": True}]
                    if bad_control and role == "fresh_replay"
                    else [],
                    "step_count": resolution,
                }
            )
    events.append(
        {
            "kind": "diagnostic_complete",
            "schema": diagnostic.SCHEMA,
            "target_substeps": 2_400,
            "control_substeps": 2_400,
            "total_substeps": instrument.MAX_SUBSTEPS,
            "control_stream_sha256": hashlib.sha256(
                b"\n".join(
                    instrument.canonical_json(
                        {
                            key: value
                            for key, value in event.items()
                            if key not in {"case_id", "role"}
                        }
                    )
                    for event in events
                    if event.get("kind") == "control_summary"
                )
            ).hexdigest(),
        }
    )
    path.mkdir()
    with (path / "events.jsonl").open("wb") as output:
        for sequence, event in enumerate(events, 1):
            output.write(
                instrument.canonical_json({"sequence": sequence, "event": event})
                + b"\n"
            )


def test_checkpoint_schedule_and_equal_time_numeric_attribution() -> None:
    assert diagnostic._checkpoint_indices(400, "cmd1")[100] == ("cmd1", 0.25)
    left = {
        "state": {
            "position_m": [1.0, 2.0],
            "heading_rad": 0.1,
            "velocity_mps": [3.0, 4.0],
            "angular_velocity_rps": 0.5,
        },
        "contact_set": ["hull|A2_03"],
        "callbacks": [{"impulse": 1.0}],
        "motor_refresh_applied": True,
        "motor_velocity_before_step_mps": [1.0, 0.0],
        "motor_angular_velocity_before_step_rps": 0.5,
    }
    right = {
        "state": {
            "position_m": [1.3, 2.4],
            "heading_rad": 0.2,
            "velocity_mps": [3.0, 4.5],
            "angular_velocity_rps": 0.25,
        },
        "contact_set": ["hull|A2_04"],
        "callbacks": [{"impulse": 2.0}],
        "motor_refresh_applied": False,
        "motor_velocity_before_step_mps": [0.0, 1.0],
        "motor_angular_velocity_before_step_rps": 0.25,
    }
    comparison = diagnostic._compare_states(left, right)
    assert comparison["categories"] == [
        "contact_or_chord_set",
        "callback_values",
        "motor_refresh_decision",
        "motor_state_above_roundoff_floor",
        "pose_heading_or_velocity_above_roundoff_floor",
    ]
    assert comparison["position_delta_m"] == pytest.approx(0.5)
    assert comparison["velocity_delta_mps"] == pytest.approx(0.5)
    assert cast(str, comparison["threshold_interpretation"]).startswith("descriptive")


def test_interval_alignment_uses_both_high_halves_and_keeps_real_differences() -> None:
    def state(progress: float) -> dict[str, object]:
        return {
            "position_m": [progress, 0.0],
            "heading_rad": 0.0,
            "velocity_mps": [1.0, 0.0],
            "angular_velocity_rps": 0.0,
        }

    def sample(
        index: int, resolution: int, *, divergent: bool = False
    ) -> dict[str, object]:
        return {
            "substep": index,
            "before": state(index / resolution),
            "after": state((index + 1) / resolution),
            "contact_set": ["hull|A2_03"] if divergent else [],
            "callbacks": [{"impulse": 1.0}] if divergent else [],
            "motor_refresh_applied": not divergent,
            "motor_velocity_before_step_mps": [0.5, 0.5] if divergent else [1.0, 0.0],
            "motor_angular_velocity_before_step_rps": 0.0,
        }

    checkpoints: dict[int, dict[tuple[str, float], dict[str, object]]] = {}
    for resolution in (400, 800):
        rows: dict[tuple[str, float], dict[str, object]] = {}
        for command, progress in instrument.CHECKPOINTS:
            endpoint = int(round(progress * resolution))
            width = resolution // 400
            interval = (
                []
                if endpoint == 0
                else [
                    sample(index, resolution)
                    for index in range(endpoint - width, endpoint)
                ]
            )
            rows[(command, progress)] = {
                "state": state(progress),
                "substep": endpoint,
                "interval_samples": interval,
                "contact_set": [],
                "callbacks": [],
                "motor_refresh_applied": True,
                "motor_velocity_before_step_mps": [1.0, 0.0],
                "motor_angular_velocity_before_step_rps": 0.0,
            }
        checkpoints[resolution] = rows

    low_details = [
        {
            "substep": index,
            "command_progress": index / 400,
            "command_end_progress": (index + 1) / 400,
            "after": state((index + 1) / 400),
            **sample(index, 400),
        }
        for index in range(340, 392)
    ]
    high_details = [
        {
            "substep": index,
            "command_progress": index / 800,
            "command_end_progress": (index + 1) / 800,
            "after": state((index + 1) / 800),
            **sample(index, 800, divergent=index == 701),
        }
        for index in range(680, 784)
    ]
    output: list[dict[str, object]] = []
    diagnostic._emit_comparisons(
        checkpoints,
        {400: low_details, 800: high_details},
        emit=output.append,
    )
    comparisons = [
        event for event in output if event["kind"] == "matched_detail_comparison"
    ]
    assert len(comparisons) == 52
    assert all(
        event["n800_interval_substeps"]
        == [
            2 * int(cast(float, event["interval_start_progress"]) * 400),
            2 * int(cast(float, event["interval_start_progress"]) * 400) + 1,
        ]
        for event in comparisons
    )
    assert all(event["position_delta_m"] == 0.0 for event in comparisons)
    assert all(
        "pose_heading_or_velocity_above_roundoff_floor"
        not in cast(list[str], event["categories"])
        for event in comparisons
    )
    target = next(
        event for event in comparisons if event["interval_start_progress"] == 350 / 400
    )
    target_categories = cast(list[str], target["categories"])
    assert "contact_or_chord_set" in target_categories
    assert "callback_values" in target_categories
    assert "motor_refresh_decision" in target_categories
    assert (
        len(
            cast(
                list[object],
                cast(dict[str, object], target["n800"])["interval_samples"],
            )
        )
        == 2
    )
    legacy_wrong_endpoint = high_details[20]["after"]
    aligned_endpoint = high_details[21]["after"]
    low_endpoint = low_details[10]["after"]
    assert (
        diagnostic._squared_delta(
            cast(
                list[float],
                cast(dict[str, object], legacy_wrong_endpoint)["position_m"],
            ),
            cast(list[float], cast(dict[str, object], low_endpoint)["position_m"]),
        )
        > 0.001
    )
    assert (
        diagnostic._squared_delta(
            cast(list[float], cast(dict[str, object], aligned_endpoint)["position_m"]),
            cast(list[float], cast(dict[str, object], low_endpoint)["position_m"]),
        )
        == 0.0
    )


def test_a2_output_validator_accepts_complete_synthetic_stream(tmp_path: Path) -> None:
    output = tmp_path / "valid"
    _write_synthetic_diagnostic_stream(output)
    instrument.validate_a2_diagnostic_output(output)


def test_a2_output_validator_rejects_missing_raw_detail_and_false_completion(
    tmp_path: Path,
) -> None:
    output = tmp_path / "missing-raw-detail"
    _write_synthetic_diagnostic_stream(output)
    event_path = output / "events.jsonl"
    rows = [json.loads(line) for line in event_path.read_text().splitlines()]
    rows.pop(
        next(i for i, row in enumerate(rows) if row["event"].get("kind") == "detail")
    )
    event_path.write_text(
        "".join(
            instrument.canonical_json({"sequence": i, "event": row["event"]}).decode()
            + "\n"
            for i, row in enumerate(rows, 1)
        )
    )
    with pytest.raises(instrument.ReceiptError, match="raw detail coverage"):
        instrument.validate_a2_diagnostic_output(output)

    output = tmp_path / "false-completion"
    _write_synthetic_diagnostic_stream(output)
    event_path = output / "events.jsonl"
    rows = [json.loads(line) for line in event_path.read_text().splitlines()]
    completion = next(
        row["event"]
        for row in rows
        if row["event"].get("kind") == "diagnostic_complete"
    )
    completion["total_substeps"] = 4_799
    event_path.write_text(
        "".join(
            instrument.canonical_json({"sequence": i, "event": row["event"]}).decode()
            + "\n"
            for i, row in enumerate(rows, 1)
        )
    )
    with pytest.raises(instrument.ReceiptError, match="recomputed substep accounting"):
        instrument.validate_a2_diagnostic_output(output)


def test_a2_output_validator_rejects_non_object_raw_interval_sample(
    tmp_path: Path,
) -> None:
    output = tmp_path / "malformed-raw-sample"
    _write_synthetic_diagnostic_stream(output)
    event_path = output / "events.jsonl"
    rows = [json.loads(line) for line in event_path.read_text().splitlines()]
    checkpoint = next(
        row["event"]
        for row in rows
        if row["event"].get("kind") == "checkpoint"
        and row["event"].get("interval_samples")
    )
    checkpoint["interval_samples"][0] = "not-an-object"
    event_path.write_text(
        "".join(
            instrument.canonical_json({"sequence": i, "event": row["event"]}).decode()
            + "\n"
            for i, row in enumerate(rows, 1)
        )
    )
    with pytest.raises(instrument.ReceiptError, match="raw checkpoint content"):
        instrument.validate_a2_diagnostic_output(output)


def test_a2_output_validator_rejects_control_step_count_mismatch(
    tmp_path: Path,
) -> None:
    output = tmp_path / "wrong-control-count"
    _write_synthetic_diagnostic_stream(output)
    event_path = output / "events.jsonl"
    rows = [json.loads(line) for line in event_path.read_text().splitlines()]
    control = next(
        row["event"] for row in rows if row["event"].get("kind") == "control_summary"
    )
    control["step_count"] -= 1
    event_path.write_text(
        "".join(
            instrument.canonical_json({"sequence": i, "event": row["event"]}).decode()
            + "\n"
            for i, row in enumerate(rows, 1)
        )
    )
    with pytest.raises(instrument.ReceiptError, match="controls are malformed"):
        instrument.validate_a2_diagnostic_output(output)


def test_candidate_source_identity_requires_clean_exact_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_paths = (
        "experiments/pymunk230_a2_instrumentation.py",
        "experiments/pymunk230_a2_diagnostic.py",
    )
    payloads = (b"instrumentation\n", b"diagnostic\n")
    for relative, payload in zip(source_paths, payloads, strict=True):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)

    def git_output(command: list[str], **kwargs: object) -> str:
        assert kwargs["cwd"] == tmp_path
        return "a" * 40 if command[1:3] == ["rev-parse", "HEAD"] else ""

    monkeypatch.setattr(subprocess, "check_output", git_output)
    identity = instrument.verify_candidate_source_identity(tmp_path)
    assert identity["candidate_head"] == "a" * 40
    authored = cast(list[dict[str, object]], identity["authored_sources"])
    assert [row["path"] for row in authored] == list(source_paths)
    assert [row["sha256"] for row in authored] == [
        hashlib.sha256(payload).hexdigest() for payload in payloads
    ]

    monkeypatch.setattr(
        subprocess,
        "check_output",
        lambda command, **_kwargs: (
            "a" * 40 if command[1:3] == ["rev-parse", "HEAD"] else " M dirty.py\n"
        ),
    )
    with pytest.raises(instrument.ReceiptError, match="clean exact HEAD"):
        instrument.verify_candidate_source_identity(tmp_path)


def test_a2_output_validator_requires_expected_candidate_identity(
    tmp_path: Path,
) -> None:
    output = tmp_path / "candidate-mismatch"
    _write_synthetic_diagnostic_stream(output)
    expected: dict[str, object] = {
        "candidate_head": "b" * 40,
        "authored_sources": [],
    }
    with pytest.raises(instrument.ReceiptError, match="candidate identity mismatch"):
        instrument.validate_a2_diagnostic_output(output, expected)


def test_a2_output_validator_rejects_missing_manifest_identity(tmp_path: Path) -> None:
    output = tmp_path / "missing-identity"
    _write_synthetic_diagnostic_stream(output)
    event_path = output / "events.jsonl"
    rows = [json.loads(line) for line in event_path.read_text().splitlines()]
    rows[0]["event"].pop("cases_source_sha256")
    event_path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    with pytest.raises(instrument.ReceiptError, match="manifest identity mismatch"):
        instrument.validate_a2_diagnostic_output(output)


def test_a2_output_validator_rejects_contacting_control(tmp_path: Path) -> None:
    output = tmp_path / "invalid"
    _write_synthetic_diagnostic_stream(output, bad_control=True)
    with pytest.raises(instrument.ReceiptError, match="controls.*contacted"):
        instrument.validate_a2_diagnostic_output(output)


def test_a2_supervisor_requires_external_exact_head_go(tmp_path: Path) -> None:
    with pytest.raises(instrument.ReceiptError, match="execution GO is absent"):
        instrument.supervise_a2_diagnostic(
            tmp_path / "must-not-start", approved_head="0" * 40
        )
    assert not (tmp_path / "must-not-start").exists()


def test_reader_rejects_oversized_no_newline_record() -> None:
    status = instrument._ReaderStatus(done=threading.Event())
    target: queue.Queue[bytes] = queue.Queue(maxsize=1)
    instrument._read_lines(
        io.BytesIO(b"x" * (instrument.MAX_STDOUT_LINE_BYTES + 1)), target, status
    )
    assert status.done.is_set()
    assert status.error == "stdout_line_limit"
    assert target.empty()


def test_reader_descendant_holding_pipe_is_killed_after_direct_child_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    grandchild = (
        "import subprocess,sys; "
        "subprocess.Popen([sys.executable,'-c','import time; time.sleep(20)'])"
    )
    monkeypatch.setattr(
        instrument,
        "_worker_command",
        lambda: [sys.executable, "-c", grandchild],
    )
    monkeypatch.setattr(
        instrument, "_process_metrics", lambda _pid: {"cpu_s": 0.0, "rss_bytes": 0}
    )
    started = time.monotonic()
    receipt = instrument.supervise(tmp_path / "descendant-eof", wall_cap_s=0.15)
    elapsed = time.monotonic() - started
    assert receipt["reason"] == "wall_cap"
    assert elapsed < 2.0
    receipt_path = tmp_path / "descendant-eof" / "STOP.json"
    checksum = (tmp_path / "descendant-eof" / "STOP.sha256").read_text("ascii")
    assert (
        checksum
        == f"{hashlib.sha256(receipt_path.read_bytes()).hexdigest()}  STOP.json\n"
    )


def test_darwin_eprem_after_exit_is_reaped_and_receipt_remains_hashed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if os.name != "posix":
        pytest.skip("isolated process groups are POSIX-only")
    original_killpg = os.killpg
    permission_once = True

    def darwin_eprem_once(pgid: int, sig: int) -> None:
        nonlocal permission_once
        if sig == signal.SIGTERM and permission_once:
            permission_once = False
            raise PermissionError(1, "simulated Darwin exited-unreaped EPERM")
        original_killpg(pgid, sig)

    original_reader = instrument._read_lines

    def delayed_reader(
        stream: object, target: queue.Queue[bytes], status: object
    ) -> None:
        time.sleep(0.1)
        original_reader(stream, target, status)  # type: ignore[arg-type]

    monkeypatch.setattr(os, "killpg", darwin_eprem_once)
    monkeypatch.setattr(instrument, "_read_lines", delayed_reader)
    monkeypatch.setattr(
        instrument,
        "_worker_command",
        lambda: [sys.executable, "-c", "import sys;sys.stdout.write('not-json\\n')"],
    )
    monkeypatch.setattr(
        instrument, "_process_metrics", lambda _pid: {"cpu_s": 0.0, "rss_bytes": 1}
    )
    output = tmp_path / "darwin-eprem"
    receipt = instrument.supervise(output, wall_cap_s=2.0)
    assert permission_once is False
    assert receipt["reason"] == "stdout_invalid_json"
    usage = cast(dict[str, object], receipt["resource_usage"])
    assert usage["cleanup_status"] == "stale_group_after_reap"
    assert usage["cleanup_succeeded"] is True
    digest = hashlib.sha256((output / "STOP.json").read_bytes()).hexdigest()
    assert (output / "STOP.sha256").read_text("ascii") == f"{digest}  STOP.json\n"


def test_macos_process_metrics_sum_live_descendant_tree_with_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Result:
        stdout = (
            "10 1 10 100 00:01:00\n"
            "11 10 10 50 00:00:10\n"
            "12 11 10 25 00:00:05\n"
            "20 1 20 999 00:30:00\n"
        )

    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: Result())
    metrics = instrument._process_metrics(10)
    assert metrics == {"rss_bytes": 175 * 1024, "cpu_s": 75.0}

    def timed_out(*_args: object, **_kwargs: object) -> object:
        raise subprocess.TimeoutExpired("ps", 0.5)

    monkeypatch.setattr(subprocess, "run", timed_out)
    assert instrument._process_metrics(10) is None


def test_output_directory_is_one_shot(tmp_path: Path) -> None:
    output = tmp_path / "existing"
    output.mkdir()
    with pytest.raises(FileExistsError):
        instrument.BoundedJournal(output)
