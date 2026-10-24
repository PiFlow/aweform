"""Synthetic fidelity checks for the offline actual-data paired renderer."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from experiments.pymunk230_obstacles.render_paired_replay import LABEL, render


def _dump(path: Path, value: object) -> bytes:
    data = json.dumps(value, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    path.write_bytes(data)
    return data


def _row(index: int, resolution: int) -> dict[str, object]:
    return {
        "index": index,
        "position_m": [1.0 + index / 1000 + resolution / 100000, 1.25],
        "heading_rad": 0.01 * index,
        "energy_j": 2600.0 - index,
        "temperature_c": 23.0,
        "max_penetration_m": 0.0001,
        "minimum_clearance_m": 0.012,
        "commanded_wheels_rad": [0.1, 0.2],
        "contact_event_runs": [{"shape_pair": ["A1_03", "hull"], "callback_count": 1}],
    }


def test_renderer_uses_exact_contiguous_actual_traces_and_emits_offline_html(
    tmp_path: Path,
) -> None:
    arms = {}
    for resolution in (400, 800):
        rows = [_row(1, resolution), _row(2, resolution)]
        raw = b"".join(
            json.dumps(row, sort_keys=True, separators=(",", ":")).encode() + b"\n"
            for row in rows
        )
        name = f"arm-N{resolution}.jsonl"
        (tmp_path / name).write_bytes(raw)
        arms[str(resolution)] = {
            "trace_file": name,
            "trace_sha256": hashlib.sha256(raw).hexdigest(),
            "transitions": len(rows),
        }
    result = {
        "safety_pass": True,
        "head": "a" * 40,
        "declaration": {"source_tree_sha": "b" * 40, "protocol_sha256": "c" * 64},
        "safety_space_steps": 10,
        "paired_space_steps": 6,
        "total_space_steps": 16,
        "paired_convergence": {"interpretation": "descriptive"},
        "paired": {
            "seed": 23002,
            "initial_state": {"body_position": [0.75, 0.75]},
            "arms": {
                key: {**value, "trace_file": value["trace_file"]}
                for key, value in arms.items()
            },
        },
    }
    _dump(tmp_path / "result.json", result)
    (tmp_path / "SHA256SUMS").write_text("synthetic test receipt\n")
    page = render(tmp_path)
    text = page.read_text(encoding="utf-8")
    assert LABEL in text
    assert "N400" in text and "N800" in text
    assert "Play" in text and "Pause" in text and "slider" in text
    assert "position difference" in text
    assert "A1_03" in text
    assert "https://" not in text
    if node := shutil.which("node"):
        script = text.split("<script>", 1)[1].split("</script>", 1)[0]
        script_path = tmp_path / "renderer.js"
        script_path.write_text(script, encoding="utf-8")
        subprocess.run(
            [node, "--check", str(script_path)], check=True, capture_output=True
        )
    receipt = json.loads((tmp_path / "visualization.json").read_text())
    assert receipt["offline"] is True and receipt["interpolation"] is False
    assert receipt["transitions"] == 2


def test_renderer_refuses_trace_digest_mismatch(tmp_path: Path) -> None:
    raw = _dump(tmp_path / "arm-N400.jsonl", _row(1, 400))
    arm = {
        "trace_file": "arm-N400.jsonl",
        "trace_sha256": "0" * 64,
        "transitions": 1,
    }
    with pytest.raises(ValueError, match="digest mismatch"):
        from experiments.pymunk230_obstacles.render_paired_replay import _load_trace

        _load_trace(tmp_path, arm)
    assert hashlib.sha256(raw).hexdigest() != arm["trace_sha256"]
