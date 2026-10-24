"""Render only saved actual lifetime frames as a self-contained static HTML file."""

# HTML and embedded JavaScript are emitted as readable browser source.
# ruff: noqa: E501

from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
from typing import Any

from .geometry import ARCS, POSTS, SEGMENTS


def render(result_dir: Path, destination: Path) -> None:
    if not destination.resolve().is_relative_to(result_dir.resolve()):
        raise ValueError("replay HTML must remain inside its result namespace")
    if (
        destination.exists()
        or destination.with_name(destination.name + ".sha256").exists()
    ):
        raise ValueError("refusing to overwrite an existing replay artifact")
    manifest = json.loads((result_dir / "manifest.json").read_text(encoding="utf-8"))
    result = json.loads((result_dir / "result.json").read_text(encoding="utf-8"))
    frame_bytes = (result_dir / "frames.jsonl").read_bytes()
    frames: list[dict[str, Any]] = [
        json.loads(line) for line in frame_bytes.splitlines() if line
    ]
    if len(frames) != result["replay_frame_count"] or not frames:
        raise ValueError("saved replay frame count is inconsistent or empty")
    if (
        manifest["head"] != result["head"]
        or manifest["protocol_sha256"] != result["protocol_sha256"]
        or manifest["seed"] != result["seed"]
        or hashlib.sha256(frame_bytes).hexdigest() != result["frames_sha256"]
        or len(frame_bytes) != result["frames_bytes"]
    ):
        raise ValueError("lifetime replay provenance or digest does not match")
    if any(frame["index"] > result["transitions"] for frame in frames):
        raise ValueError("replay contains a frame beyond the measured lifetime")
    provenance = {
        "head": manifest["head"],
        "protocol_sha256": manifest["protocol_sha256"],
        "physics_result_sha256": manifest["physics_result_sha256"],
        "manifest_sha256": hashlib.sha256(
            (result_dir / "manifest.json").read_bytes()
        ).hexdigest(),
        "lifetime_result_sha256": hashlib.sha256(
            (result_dir / "result.json").read_bytes()
        ).hexdigest(),
        "frames_sha256": hashlib.sha256(frame_bytes).hexdigest(),
        "frame_count": len(frames),
        "transitions": result["transitions"],
        "seed": result["seed"],
    }
    arcs = []
    for arc in ARCS:
        arcs.append(
            f'<path d="{_arc_path(arc.center, arc.start_deg, arc.end_deg, 0.40)}" '
            'fill="none" stroke="#526b83" stroke-width="0.05" stroke-linecap="round" />'
        )
    segments = [
        f'<line x1="{s.start[0]}" y1="{3 - s.start[1]}" x2="{s.end[0]}" '
        f'y2="{3 - s.end[1]}" stroke="#526b83" stroke-width="0.05" '
        'stroke-linecap="round" />'
        for s in SEGMENTS
    ]
    posts = [
        f'<circle cx="{p.center[0]}" cy="{3 - p.center[1]}" r="0.05" fill="#526b83" />'
        for p in POSTS
    ]
    frames_json = json.dumps(frames, separators=(",", ":"), allow_nan=False)
    metadata = html.escape(json.dumps(provenance, sort_keys=True))
    body = f'''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Aweform #230 measured obstacle replay</title>
<style>body{{font:16px system-ui;margin:2rem;color:#182230}}main{{max-width:850px;margin:auto}}svg{{width:min(80vw,650px);background:#f6f8fa;border:1px solid #99a}}code{{font-size:.8rem}}#robot{{fill:#dc5b42;stroke:#621;stroke-width:.006}}#dock{{fill:#4b8;opacity:.45}}.wall{{stroke:#333;stroke-width:.01}}pre{{white-space:pre-wrap}}</style>
<main><h1>Measured seven-object lifetime replay</h1>
<p>This visualization uses sampled actual transitions only; skipped transitions are not interpolated.</p>
<svg viewBox="0 0 3 3" role="img" aria-label="Arena and sampled measured robot position">{"".join(arcs)}{"".join(segments)}{"".join(posts)}<circle id="dock" cx="1.5" cy="1.5" r="0.10"/><path class="wall" d="M0 0H3V3H0Z" fill="none"/><rect id="robot" x="-.09" y="-.1075" width=".18" height=".215" rx=".008"/></svg>
<p>Sample <span id="counter"></span> / {len(frames)}; transition <span id="transition"></span></p>
<input id="slider" type="range" min="0" max="{len(frames) - 1}" value="0" aria-label="Replay frame">
<details><summary>Provenance</summary><pre>{metadata}</pre></details></main>
<script>const frames={frames_json};const robot=document.querySelector('#robot'),slider=document.querySelector('#slider');function show(i){{const f=frames[Number(i)],p=f.position_m;robot.setAttribute('x',p[0]-.09);robot.setAttribute('y',3-p[1]-.1075);robot.setAttribute('transform',`rotate(${{-f.yaw_rad*180/Math.PI}} ${{p[0]}} ${{3-p[1]}})`);document.querySelector('#counter').textContent=Number(i)+1;document.querySelector('#transition').textContent=f.index}}slider.addEventListener('input',()=>show(slider.value));show(0);</script></html>'''
    rendered = body.encode("utf-8")
    digest = hashlib.sha256(rendered).hexdigest()
    sidecar = destination.with_name(destination.name + ".sha256")
    checksum_file = result_dir / "SHA256SUMS"
    prior = checksum_file.read_text(encoding="utf-8")
    line_bytes = f"{digest}  {destination.name}\n".encode("utf-8")
    additional_bytes = len(rendered) + 2 * len(line_bytes)
    existing_bytes = sum(
        path.stat().st_size for path in result_dir.iterdir() if path.is_file()
    )
    if existing_bytes + additional_bytes > 10 * 1024 * 1024:
        raise ValueError("rendered lifetime artifacts would exceed the 10 MiB cap")
    destination.write_bytes(rendered)
    sidecar.write_text(line_bytes.decode("utf-8"), encoding="utf-8")
    checksum_file.write_text(prior + line_bytes.decode("utf-8"), encoding="utf-8")


def _arc_path(
    center: tuple[float, float], start_deg: float, end_deg: float, radius: float
) -> str:
    import math

    x1 = center[0] + radius * math.cos(math.radians(start_deg))
    y1 = 3 - center[1] - radius * math.sin(math.radians(start_deg))
    x2 = center[0] + radius * math.cos(math.radians(end_deg))
    y2 = 3 - center[1] - radius * math.sin(math.radians(end_deg))
    large = int(end_deg - start_deg > 180)
    return f"M{x1} {y1} A{radius} {radius} 0 {large} 0 {x2} {y2}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("result_dir", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    render(args.result_dir, args.destination)


if __name__ == "__main__":
    main()
