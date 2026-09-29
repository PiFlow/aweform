from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import cast

import pytest

from aweform.development_visualizer import (
    DevelopmentCausalGeometry,
    DevelopmentVisualizationData,
    DevelopmentVisualizationFrame,
    DevelopmentVisualizationRange,
    DevelopmentVisualizationVisibility,
    _d055_adapt_lifetime,
    _d055_require_fidelity,
    _development_html_frame_payload,
    build_development_html_replay,
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


def test_shared_single_replay_html_matches_main_golden() -> None:
    """A non-paired neutral replay retains the main-branch HTML bytes."""
    data = DevelopmentVisualizationData(
        source_label="single replay regression fixture",
        seed=7,
        world_min=(0.0, 0.0),
        world_max=(1.0, 1.0),
        station_center=(0.5, 0.5),
        charging_radius=0.0,
        energy_range=DevelopmentVisualizationRange(0.0, 1.0),
        thermal_range=DevelopmentVisualizationRange(0.0, 1.0),
        frames=(
            DevelopmentVisualizationFrame(
                transition_index=0,
                x=0.5,
                y=0.5,
                heading=0.0,
                action="INITIAL",
                decision_mode="NORMAL",
                energy=0.8,
                thermal=0.2,
                charging_contact=False,
                terminated=False,
                truncated=False,
            ),
        ),
        visibility=DevelopmentVisualizationVisibility(
            position_heading="EVALUATOR ONLY",
            station_location="EVALUATOR ONLY",
            energy="EVAL",
            thermal="EVAL",
            charging_contact="EVAL",
            action_decision_mode="EVAL",
        ),
        causal_geometry=DevelopmentCausalGeometry(
            body_length=0.18,
            body_width=0.215,
            rear_contact_plus=(0.0, 0.03),
            rear_contact_minus=(0.0, -0.03),
            front_midpoint=(0.0, 0.0),
            dock_orientation=0.0,
            dock_contact_plus=(0.5, 0.53),
            dock_contact_minus=(0.5, 0.47),
            contact_tolerance=0.01,
        ),
    )
    output = build_development_html_replay(
        [data], schema="fixture.v1", title="fixture replay"
    )
    assert hashlib.sha256(output.encode("utf-8")).hexdigest() == (
        "e93529d75f22e4e999aab83e2acb0e63868018f9e20076d4eca670cbb9feb5f2"
    )


def test_d055_fidelity_gate_rejects_tampered_record() -> None:
    with pytest.raises(ValueError, match="fidelity mismatch"):
        _d055_require_fidelity(
            {"seed": 22053, "total_transitions": 140000},
            {"seed": 22053, "total_transitions": 139999},
            context="test-only tamper",
        )
