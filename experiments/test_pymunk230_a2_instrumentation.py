"""Model-free regression tests for A2-R1 custody and supervision only."""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import pytest

from experiments import pymunk230_a2_instrumentation as instrument


def test_frozen_plan_accounts_for_exact_substeps_without_execution() -> None:
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
    assert all(case.fixture == "frozen_a2_convex" for case in plan[:4])
    assert all(case.fixture == "empty-free" for case in plan[4:])
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
    assert instrument.EMPTY_FREE_ACTION == "F×1"
    assert instrument.main(["--preflight"]) == 0


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
    assert (tmp_path / "result" / "STOP.json").is_file()
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
            "--model-free-worker",
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


def test_output_directory_is_one_shot(tmp_path: Path) -> None:
    output = tmp_path / "existing"
    output.mkdir()
    with pytest.raises(FileExistsError):
        instrument.BoundedJournal(output)
