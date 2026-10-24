"""Render saved actual N400/N800 data as a self-contained synchronized HTML."""

# HTML and embedded JavaScript are emitted as readable browser source.
# ruff: noqa: E501

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
from pathlib import Path
from typing import Any

from .geometry import ARCS, POSTS, SEGMENTS

LABEL = "EXPLORATORY / UNVALIDATED PHYSICS"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_trace(result_dir: Path, arm: dict[str, Any]) -> list[dict[str, Any]]:
    name = str(arm["trace_file"])
    path = result_dir / name
    if path.parent.resolve() != result_dir.resolve() or not path.is_file():
        raise ValueError("paired trace path is missing or escapes result directory")
    raw = path.read_bytes()
    if _sha(raw) != arm["trace_sha256"]:
        raise ValueError(f"trace digest mismatch: {name}")
    rows = [json.loads(line) for line in raw.splitlines() if line]
    if len(rows) != arm["transitions"] or not rows:
        raise ValueError(f"trace count mismatch: {name}")
    for index, row in enumerate(rows, 1):
        if row.get("index") != index:
            raise ValueError(f"non-contiguous actual transition in {name}")
        if not all(
            math.isfinite(float(value))
            for value in (
                *row["position_m"],
                row["heading_rad"],
                row["energy_j"],
                row["temperature_c"],
                row["max_penetration_m"],
            )
        ):
            raise ValueError(f"non-finite saved observation in {name}")
        if "commanded_wheels_rad" not in row or "contact_event_runs" not in row:
            raise ValueError(f"missing action/contact data in {name}")
    return rows


def _visual_frame(row: dict[str, Any]) -> dict[str, Any]:
    identities = sorted(
        {
            identity
            for state in row.get("contact_state_runs", [])
            for identity in state.get("identities", [])
        }
        | {
            "|".join(event["shape_pair"])
            for event in row.get("contact_event_runs", [])
        }
    )
    return {
        "index": row["index"],
        "position_m": row["position_m"],
        "heading_rad": row["heading_rad"],
        "energy_j": row["energy_j"],
        "temperature_c": row["temperature_c"],
        "commanded_wheels_rad": row["commanded_wheels_rad"],
        "minimum_clearance_m": row["minimum_clearance_m"],
        "max_penetration_m": row["max_penetration_m"],
        "contact_identities": identities,
    }


def _arc_path(center: tuple[float, float], start: float, end: float) -> str:
    x1 = center[0] + 0.4 * math.cos(math.radians(start))
    y1 = 3 - center[1] - 0.4 * math.sin(math.radians(start))
    x2 = center[0] + 0.4 * math.cos(math.radians(end))
    y2 = 3 - center[1] - 0.4 * math.sin(math.radians(end))
    return f"M{x1} {y1} A0.4 0.4 0 0 0 {x2} {y2}"


def _arena_markup() -> str:
    arcs = "".join(
        f'<path d="{_arc_path(a.center, a.start_deg, a.end_deg)}" '
        'fill="none" stroke="#526b83" stroke-width=".05" stroke-linecap="round"/>'
        for a in ARCS
    )
    segments = "".join(
        f'<line x1="{s.start[0]}" y1="{3 - s.start[1]}" '
        f'x2="{s.end[0]}" y2="{3 - s.end[1]}" stroke="#526b83" '
        'stroke-width=".05" stroke-linecap="round"/>'
        for s in SEGMENTS
    )
    posts = "".join(
        f'<circle cx="{p.center[0]}" cy="{3 - p.center[1]}" r=".05" '
        f'fill="#526b83"/><text x="{p.center[0] + 0.06}" y="{3 - p.center[1]}">{p.name}</text>'
        for p in POSTS
    )
    labels = "".join(
        f'<text x="{a.center[0]}" y="{3 - a.center[1]}">{a.name}</text>' for a in ARCS
    ) + "".join(
        f'<text x="{s.start[0]}" y="{3 - s.start[1] - 0.04}">{s.name}</text>'
        for s in SEGMENTS
    )
    return (
        arcs
        + segments
        + posts
        + labels
        + '<circle cx="1.5" cy="1.5" r=".10" fill="#33a982" opacity=".5"/>'
        + '<text x="1.52" y="1.48">dock</text>'
        + '<path d="M0 0H3V3H0Z" fill="none" stroke="#222" stroke-width=".01"/>'
    )


def render(result_dir: Path) -> Path:
    result_path = result_dir / "result.json"
    result_bytes = result_path.read_bytes()
    result = json.loads(result_bytes)
    paired = result["paired"]
    arm400 = paired["arms"]["400"]
    arm800 = paired["arms"]["800"]
    n400, n800 = _load_trace(result_dir, arm400), _load_trace(result_dir, arm800)
    if len(n400) != len(n800):
        raise ValueError("paired arms do not have common actual transition support")
    if result["safety_pass"] is not True:
        raise ValueError("visualization withheld because safety probes did not pass")
    frames = {
        "400": [_visual_frame(row) for row in n400],
        "800": [_visual_frame(row) for row in n800],
    }
    payload = json.dumps(frames, separators=(",", ":"), allow_nan=False)
    provenance = {
        "head": result["head"],
        "source_tree_sha": result["declaration"]["source_tree_sha"],
        "protocol_sha256": result["declaration"]["protocol_sha256"],
        "seed": paired["seed"],
        "transitions_per_arm": len(n400),
        "initial_state": paired["initial_state"],
        "safety_space_steps": result["safety_space_steps"],
        "paired_space_steps": result["paired_space_steps"],
        "total_space_steps": result["total_space_steps"],
        "arm_trace_sha256": {
            "400": arm400["trace_sha256"],
            "800": arm800["trace_sha256"],
        },
        "result_sha256": _sha(result_bytes),
        "paired_convergence": result["paired_convergence"],
    }
    escaped_provenance = html.escape(json.dumps(provenance, sort_keys=True, indent=2))
    arena = _arena_markup()
    page = f'''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Aweform #230 paired actual N400/N800 playback</title>
<style>
body{{font:15px system-ui,sans-serif;color:#182230;margin:1.2rem;background:#f7f8fa}}main{{max-width:1400px;margin:auto}}.warning{{color:#9b1c1c;font-weight:800;font-size:1.2rem}}.arms{{display:grid;grid-template-columns:1fr 1fr;gap:1rem}}svg{{width:100%;background:white;border:1px solid #abb}}.robot{{fill:#dc5b42;stroke:#621;stroke-width:.006}}.heading{{stroke:#111;stroke-width:.009}}.energy{{height:180px}}button,input{{font:inherit}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}@media(max-width:850px){{.arms{{grid-template-columns:1fr}}}}
</style><main><h1>Aweform #230 — paired physics resolution replay</h1>
<p class="warning">{LABEL}</p><p>Actual recorded trajectories only; no interpolation or forced action matching. N400 and N800 each use 400/800 physics substeps per same 0.1 s organism command.</p>
<div><button id="play">Play</button> <button id="pause">Pause</button> <label>Shared transition <input id="slider" type="range" min="1" max="{len(n400)}" value="1"></label> <span id="index"></span></div>
<div class="arms"><section><h2>N400</h2><svg viewBox="0 0 3 3" aria-label="N400 actual trajectory">{arena}<rect id="r400" class="robot" x="0" y="0" width=".18" height=".215" rx=".008"/><line id="h400" class="heading" x1="0" y1="0" x2="0" y2="-.13"/></svg><p id="m400"></p></section>
<section><h2>N800</h2><svg viewBox="0 0 3 3" aria-label="N800 actual trajectory">{arena}<rect id="r800" class="robot" x="0" y="0" width=".18" height=".215" rx=".008"/><line id="h800" class="heading" x1="0" y1="0" x2="0" y2="-.13"/></svg><p id="m800"></p></section></div>
<h2>Recorded energy trend</h2><svg class="energy" id="energy" viewBox="0 0 800 180" role="img" aria-label="Actual energy over transitions"><path d="M40 10V145H790" fill="none" stroke="#333"/><polyline id="e400" fill="none" stroke="#1769aa" stroke-width="2"/><polyline id="e800" fill="none" stroke="#c44" stroke-width="2"/><circle id="c400" r="4" fill="#1769aa"/><circle id="c800" r="4" fill="#c44"/><text x="45" y="170" fill="#1769aa">N400 energy</text><text x="160" y="170" fill="#c44">N800 energy</text></svg>
<p id="diff"></p><p id="contact"></p><details><summary>Exact source/run provenance</summary><pre>{escaped_provenance}</pre></details></main>
<script>
const data={payload},slider=document.querySelector('#slider'),N=data['400'].length;
const allEnergy=[...data['400'],...data['800']].map(x=>x.energy_j),energyHi=Math.max(...allEnergy),energyLo=Math.min(...allEnergy),energySpan=Math.max(1,energyHi-energyLo);
function energyPath(k){{const values=data[k].map(x=>x.energy_j);return values.map((v,i)=>`${{40+i*750/Math.max(1,N-1)}},${{145-(v-energyLo)*125/energySpan}}`).join(' ')}}
document.querySelector('#e400').setAttribute('points',energyPath('400'));document.querySelector('#e800').setAttribute('points',energyPath('800'));
function show(i){{i=Math.max(1,Math.min(N,Number(i)));const a=data['400'][i-1],b=data['800'][i-1];for(const [k,f] of [['400',a],['800',b]]){{const p=f.position_m,x=p[0],y=3-p[1],r=document.querySelector('#r'+k),h=document.querySelector('#h'+k);r.setAttribute('x',x-.09);r.setAttribute('y',y-.1075);r.setAttribute('transform',`rotate(${{-f.heading_rad*180/Math.PI}} ${{x}} ${{y}})`);h.setAttribute('x1',x);h.setAttribute('y1',y);h.setAttribute('x2',x+.13);h.setAttribute('y2',y);h.setAttribute('transform',`rotate(${{-f.heading_rad*180/Math.PI}} ${{x}} ${{y}})`);document.querySelector('#m'+k).textContent=`Transition ${{f.index}} · energy ${{Number(f.energy_j).toFixed(1)}} J · heading ${{Number(f.heading_rad).toFixed(4)}} rad · commanded wheels ${{f.commanded_wheels_rad.map(x=>Number(x).toFixed(3)).join(', ')}} rad · penetration upper bound ${{(1000*f.max_penetration_m).toFixed(3)}} mm · clearance ${{(1000*f.minimum_clearance_m).toFixed(2)}} mm`}}
const dx=(b.position_m[0]-a.position_m[0])*1000,dy=(b.position_m[1]-a.position_m[1])*1000,dh=Math.atan2(Math.sin(b.heading_rad-a.heading_rad),Math.cos(b.heading_rad-a.heading_rad))*1000;
document.querySelector('#diff').textContent=`N800 − N400 position difference: ${{Math.hypot(dx,dy).toFixed(2)}} mm (Δx ${{dx.toFixed(2)}}, Δy ${{dy.toFixed(2)}}); wrapped heading difference: ${{dh.toFixed(2)}} mrad.`;
function ids(f){{return f.contact_identities}}
document.querySelector('#contact').textContent=`Contact identities — N400: ${{ids(a).join(', ')||'none'}}; N800: ${{ids(b).join(', ')||'none'}}. `+`Clearance/penetration and action values are per-arm actual measurements; organism actions are not synchronized after observations diverge.`;
slider.value=i;document.querySelector('#index').textContent=`${{i}} / ${{N}}`;const ex=document.querySelector('#e400').getAttribute('points').split(' ')[i-1].split(','),ey=document.querySelector('#e800').getAttribute('points').split(' ')[i-1].split(',');for(const [id,v] of [['c400',ex],['c800',ey]]){{document.querySelector('#'+id).setAttribute('cx',v[0]);document.querySelector('#'+id).setAttribute('cy',v[1])}}}}
slider.addEventListener('input',()=>show(slider.value));let timer=null;document.querySelector('#play').onclick=()=>{{if(timer)return;timer=setInterval(()=>{{if(Number(slider.value)>=N){{clearInterval(timer);timer=null;return}}show(Number(slider.value)+1)}},180)}};document.querySelector('#pause').onclick=()=>{{clearInterval(timer);timer=null}};show(1);
</script></html>'''
    rendered = page.encode("utf-8")
    destination = result_dir / "paired-n400-n800.html"
    receipt = result_dir / "visualization.json"
    if destination.exists() or receipt.exists():
        raise ValueError("refusing to overwrite paired visualization")
    receipt_data = {
        "label": LABEL,
        "html_sha256": _sha(rendered),
        "html_bytes": len(rendered),
        "renderer_source_sha256": _sha(Path(__file__).read_bytes()),
        "source_trace_sha256": provenance["arm_trace_sha256"],
        "result_sha256": provenance["result_sha256"],
        "transitions": len(n400),
        "offline": True,
        "interpolation": False,
    }
    receipt_bytes = json.dumps(receipt_data, sort_keys=True, indent=2).encode() + b"\n"
    existing_bytes = sum(
        path.stat().st_size for path in result_dir.iterdir() if path.is_file()
    )
    sums_path = result_dir / "SHA256SUMS"
    if not sums_path.exists():
        raise ValueError("run checksum ledger is missing")
    sum_lines = (
        f"{_sha(rendered)}  {destination.name}\n{_sha(receipt_bytes)}  {receipt.name}\n"
    ).encode("utf-8")
    additional_bytes = len(rendered) + len(receipt_bytes) + len(sum_lines)
    if existing_bytes + additional_bytes > 32 * 1024 * 1024:
        raise ValueError("paired visualization would exceed the 32 MiB run cap")
    destination.write_bytes(rendered)
    receipt.write_bytes(receipt_bytes)
    with sums_path.open("a", encoding="utf-8") as sums:
        sums.write(sum_lines.decode("utf-8"))
    return destination


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("result_dir", type=Path)
    args = parser.parse_args()
    print(render(args.result_dir))


if __name__ == "__main__":
    main()
