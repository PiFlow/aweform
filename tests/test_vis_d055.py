from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from aweform.development_visualizer import (
    _d055_adapt_lifetime,
    _d055_require_fidelity,
    _development_html_frame_payload,
    select_d055_replay_examples,
)

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = (
    ROOT / "development/D-055-v05-return-proprioceptive-stall-turn-candidate.json"
)


def _trace_row(
    transition: int, *, source: str | None, events: list[str]
) -> dict[str, object]:
    return {
        "transition": transition,
        "events": events,
        "active_mode": "RETURN" if transition else "NORMAL",
        "command_source": source,
        "d050_mode": "CURVED_PURSUIT" if transition else None,
        "symbolic_proposal": "MOVE_FORWARD",
        "x": 0.5,
        "y": 0.5,
        "heading": 0.0,
        "energy": 0.8,
        "energy_after": 0.799,
        "thermal": 0.2,
        "charging_contact": True,
        "charging_contact_after": False,
        "charging_contact_before": True,
        "terminated": False,
        "truncated": False,
        "simulated_seconds": float(transition),
        "cycle_index": 1,
        "wheel_command": [0.1, -0.1],
    }


def test_d055_adapter_marks_stall_turn_in_shared_neutral_frame() -> None:
    data = _d055_adapt_lifetime(
        (_trace_row(0, source=None, events=["RESET"]),
         _trace_row(1, source="STALL_TURN", events=[])),
        seed=22570,
        arm_c=True,
    )
    marked = next(frame for frame in data.frames if frame.transition_index == 1)
    assert marked.command_source == "STALL_TURN"
    assert marked.event_label == "STALL_TURN"
    assert _development_html_frame_payload(marked)["event"] == "STALL_TURN"


def test_d055_example_selection_matches_committed_result() -> None:
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert select_d055_replay_examples(cast(dict[str, object], artifact)) == (
        "bottom_wall-i0.00-p0.10-0.00-h10",
        "seed-22053",
        "seed-22554",
        "seed-22054",
    )


def test_d055_fidelity_gate_rejects_tampered_record() -> None:
    with pytest.raises(ValueError, match="fidelity mismatch"):
        _d055_require_fidelity(
            {"seed": 22053, "total_transitions": 140000},
            {"seed": 22053, "total_transitions": 139999},
            context="test-only tamper",
        )
