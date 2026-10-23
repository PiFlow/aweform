"""D-061 saved-frame adapter for the canonical shared renderer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Mapping, Sequence, cast

from .d045 import (
    D045_CONTACT_OFFSET_METRES,
    D045_CONTACT_TOLERANCE_METRES,
    D045_WORLD_MAX,
    D045_WORLD_MIN,
)
from .d049 import D049_STATION_CENTER
from .development_visualizer import (
    DevelopmentCausalGeometry,
    DevelopmentVisualizationData,
    DevelopmentVisualizationFrame,
    DevelopmentVisualizationRange,
    DevelopmentVisualizationVisibility,
    build_development_html_replay,
)

D061_BODY_LENGTH_M = 0.180
D061_BODY_WIDTH_M = 0.215


def adapt_d061_trace(
    trace: Sequence[Mapping[str, object]],
    *,
    seed: int,
    arm: str,
    initial_state: Mapping[str, object],
) -> DevelopmentVisualizationData:
    """Adapt actual saved D-061 frames; do not rerun the organism."""
    position = cast(Sequence[float], initial_state["position"])
    frames = [
        DevelopmentVisualizationFrame(
            transition_index=0,
            x=float(position[0]),
            y=float(position[1]),
            heading=cast(float, initial_state["heading"]),
            action="INITIAL",
            decision_mode="NORMAL",
            energy=cast(float, initial_state["energy_fraction"]),
            thermal=cast(float, initial_state["temperature_channel"]),
            charging_contact=cast(bool, initial_state["charging_contact"]),
            terminated=False,
            truncated=False,
            simulated_seconds=0.0,
        )
    ]
    for row in trace:
        events = cast(list[str], row["events"])
        frames.append(
            DevelopmentVisualizationFrame(
                transition_index=cast(int, row["transition"]),
                x=cast(float, row["x"]),
                y=cast(float, row["y"]),
                heading=cast(float, row["heading"]),
                action=f"{arm}: {row['symbolic_proposal']}",
                decision_mode=cast(str, row["active_mode"]),
                energy=cast(float, row["energy_after"]),
                thermal=cast(float, row["thermal"]),
                charging_contact=cast(bool, row["charging_contact_after"]),
                terminated=cast(bool, row["terminated"]),
                truncated=cast(bool, row["truncated"]),
                simulated_seconds=cast(float, row["simulated_seconds"]),
                charging_contact_before=cast(bool, row["charging_contact_before"]),
                event_label=", ".join(events) if events else None,
                command_source=cast(str, row["command_source"]),
                cycle_index=cast(int, row["cycle_index"]),
            )
        )
    station = D049_STATION_CENTER
    return DevelopmentVisualizationData(
        source_label="D-061 saved evaluator-side trace",
        seed=seed,
        world_min=D045_WORLD_MIN,
        world_max=D045_WORLD_MAX,
        station_center=station,
        charging_radius=None,
        energy_range=DevelopmentVisualizationRange(0.0, 1.0),
        thermal_range=DevelopmentVisualizationRange(0.0, 1.0),
        frames=tuple(frames),
        visibility=DevelopmentVisualizationVisibility(
            position_heading="EVALUATOR ONLY",
            station_location="EVALUATOR ONLY",
            energy="ORGANISM-VISIBLE NORMALIZED + EVALUATOR",
            thermal="ORGANISM-VISIBLE NORMALIZED + EVALUATOR",
            charging_contact="ORGANISM-VISIBLE BINARY + EVALUATOR",
            action_decision_mode="SAVED D-061 ARM AND D-052 MODE",
        ),
        energy_thresholds=((0.20, "RETURN 20%"), (0.80, "RECOVERY 80%")),
        energy_label="ENERGY",
        causal_geometry=DevelopmentCausalGeometry(
            body_length=D061_BODY_LENGTH_M,
            body_width=D061_BODY_WIDTH_M,
            rear_contact_plus=(0.0, D045_CONTACT_OFFSET_METRES),
            rear_contact_minus=(0.0, -D045_CONTACT_OFFSET_METRES),
            front_midpoint=(0.0, 0.0),
            dock_orientation=0.0,
            dock_contact_plus=(station[0], station[1] + D045_CONTACT_OFFSET_METRES),
            dock_contact_minus=(station[0], station[1] - D045_CONTACT_OFFSET_METRES),
            contact_tolerance=D045_CONTACT_TOLERANCE_METRES,
            contact_label="under-body contacts",
        ),
        figure_title=f"D-061 seed {seed} — {arm}",
    )


def _comparison_html(title: str, arms: Sequence[tuple[str, str]]) -> str:
    panels = "".join(
        (
            f'<section><h2>Arm {arm}</h2><iframe title="D-061 seed 22053 arm {arm}" '
            f'src="{filename}"></iframe></section>'
        )
        for arm, filename in arms
    )
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{title}</title>"
        "<style>body{font:14px system-ui;margin:1rem;color:#17202a}"
        "h1{font-size:1.4rem}main{display:grid;"
        "grid-template-columns:repeat(3,minmax(0,1fr));gap:.65rem}"
        "section{min-width:0}h2{font-size:1rem;margin:.3rem}"
        "iframe{width:100%;height:760px;border:1px solid #8795a1;"
        "border-radius:5px}@media(max-width:900px){main{grid-template-columns:1fr}"
        "iframe{height:760px}}</style>"
        f"<h1>{title}</h1>"
        "<p>U, L, and P are independently playable offline renderings of actual "
        "saved frames through the canonical shared renderer. Evaluator poses "
        "are replay diagnostics, not organism inputs.</p>"
        f"<main>{panels}</main></html>"
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Create three shared-renderer arm pages and one side-by-side index page."""
    parser = argparse.ArgumentParser(description="Render saved D-061 replay frames")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    if payload.get("schema") != "aweform.d061.execution.v1":
        raise ValueError("input is not a D-061 execution artifact")
    results = cast(list[Mapping[str, object]], payload["results"])
    selected = {
        cast(str, result["arm"]): result
        for result in results
        if result.get("seed") == 22053 and result.get("arm") in {"U", "L", "P"}
    }
    if set(selected) != {"U", "L", "P"}:
        raise ValueError("saved artifact must contain seed-22053 U/L/P frames")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    base = args.output.name.removesuffix("-replay.html")
    arms: list[tuple[str, str]] = []
    for arm in ("U", "L", "P"):
        result = selected[arm]
        data = adapt_d061_trace(
            cast(Sequence[Mapping[str, object]], result["trace"]),
            seed=22053,
            arm=arm,
            initial_state=cast(Mapping[str, object], result["initial_state"]),
        )
        filename = f"{base}-{arm}.html"
        arm_html = build_development_html_replay(
            (data,),
            schema=f"aweform.d061.arm-{arm.lower()}.v1",
            title=f"Aweform D-061 — seed 22053 — arm {arm}",
            event_navigation=True,
        )
        (args.output.parent / filename).write_text(
            arm_html, encoding="utf-8", newline="\n"
        )
        arms.append((arm, filename))
    args.output.write_text(
        _comparison_html("Aweform D-061 — seed 22053 saved-frame comparison", arms),
        encoding="utf-8",
        newline="\n",
    )
    return 0
