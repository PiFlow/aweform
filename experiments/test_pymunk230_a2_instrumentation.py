"""Model-free regression tests for A2-R1 custody and supervision only."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path

import pytest

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
    with pytest.raises(instrument.ReceiptError, match="missing contact-event"):
        instrument.validate_empty_free_control(b'{"progress":1}\n', b'{"progress":1}\n')


def test_output_directory_is_one_shot(tmp_path: Path) -> None:
    output = tmp_path / "existing"
    output.mkdir()
    with pytest.raises(FileExistsError):
        instrument.BoundedJournal(output)
