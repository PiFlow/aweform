"""Curated, digest-gated evaluator-only replay for accepted D-059 lifetimes."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from . import d059
from . import development_visualizer as visualizer
from .d045 import (
    D045_CONTACT_OFFSET_METRES,
    D045_CONTACT_TOLERANCE_METRES,
    D045_DT_SECONDS,
    D045_WORLD_MIN,
)
from .d052 import D052Controller, D052Mode
from .d053 import D053RoamingFixture
from .d055 import D055StallTurnCandidate
from .d058 import D058Env

VIS_D059_WARNING = (
    "CURATED ILLUSTRATIVE EXAMPLES — selected post-result for visual interest; "
    "not a representative sample; zero evidential weight; does not alter or "
    "strengthen any D-059 conclusion."
)
VIS_D059_TUPLES: tuple[tuple[int, str, str], ...] = (
    (26052, "D045_1M", "U"),
    (26002, "D045_1M", "U"),
    (26005, "D045_1M", "U"),
    (26051, "D045_1M", "C"),
    (26042, "D045_1M", "C"),
    (26000, "S1_3M", "U"),
    (26038, "S1_3M", "U"),
    (26016, "S1_3M", "U"),
    (26001, "S1_1M", "U"),
    (26035, "S1_1M", "U"),
)
VIS_D059_HORIZON = 300_000
VIS_D059_OUTPUT = Path("development/VIS-D059-curated-replay.html")


class ReplayMismatchError(RuntimeError):
    """Raised when a replay does not reproduce both accepted digests."""


def validate_allowlisted_tuple(seed: int, substrate: str, arm: str) -> None:
    """Reject every lifetime outside the exact approved ten-row selection."""
    if (
        isinstance(seed, bool)
        or not isinstance(seed, int)
        or not isinstance(substrate, str)
        or not isinstance(arm, str)
        or (seed, substrate, arm) not in VIS_D059_TUPLES
    ):
        raise ValueError(
            "VIS-D059 tuple is not allowlisted: "
            f"seed={seed}, substrate={substrate}, arm={arm}"
        )


def _accepted_digest_rows(
    path: Path,
) -> dict[tuple[int, str, str], Mapping[str, object]]:
    artifact = json.loads(path.read_text(encoding="utf-8"))
    rows = artifact["endurance"]["lifetime_summaries"]
    indexed = {
        (int(row["seed"]), str(row["substrate"]), str(row["arm"])): row for row in rows
    }
    missing = [key for key in VIS_D059_TUPLES if key not in indexed]
    if missing:
        raise ValueError(
            f"accepted D-059 artifact is missing allowlisted rows: {missing}"
        )
    return indexed


def _contact_token(env: object, boundary_scale: float) -> dict[str, object]:
    if isinstance(env, D058Env):
        contact = env.last_contact
        if contact is None:
            raise RuntimeError("D-058 contact telemetry missing")
        return {
            "pushing_x_min": contact.pushing_x_min,
            "pushing_x_max": contact.pushing_x_max,
            "pushing_y_min": contact.pushing_y_min,
            "pushing_y_max": contact.pushing_y_max,
            "unconstrained_endpoint": contact.unconstrained_endpoint,
            "executed_endpoint": contact.executed_endpoint,
            "hx_m": contact.hx_m,
            "hy_m": contact.hy_m,
            "removed_normal_displacement_m": contact.removed_normal_displacement_m,
            "slip_magnitude_m": contact.slip_magnitude_m,
        }
    return {"boundary_scale": boundary_scale}


def _has_s1_contact(env: object) -> bool:
    if not isinstance(env, D058Env) or env.last_contact is None:
        return False
    contact = env.last_contact
    return any(
        (
            contact.pushing_x_min,
            contact.pushing_x_max,
            contact.pushing_y_min,
            contact.pushing_y_max,
        )
    )


def _replay_lifetime(
    seed: int,
    substrate: str,
    arm: str,
    expected: Mapping[str, object],
) -> tuple[visualizer.DevelopmentVisualizationData, dict[str, object]]:
    """Replay one approved lifetime and keep its display trace in memory only."""
    validate_allowlisted_tuple(seed, substrate, arm)
    if (
        expected.get("trajectory_digest_sha256") is None
        or expected.get("final_causal_state_digest_sha256") is None
    ):
        raise ValueError(
            f"accepted digest row is incomplete for {(seed, substrate, arm)}"
        )

    room_side_m = 3.0 if substrate == "S1_3M" else 1.0
    env = d059._new_env(substrate, room_side_m, VIS_D059_HORIZON)
    initial_position = (room_side_m / 2.0, room_side_m / 2.0)
    observation, reset_info = env.reset(
        options=d059._reset_options(initial_position, 0.0, room_side_m, 0.80)
    )
    if reset_info != {}:
        raise RuntimeError("D-059 reset info must be exactly empty")
    controller = D052Controller()
    candidate = D055StallTurnCandidate(controller) if arm == "C" else None
    fixture = D053RoamingFixture(seed)
    digest = hashlib.sha256()
    d059._update_digest(
        digest,
        {"reset_observation": observation.tobytes().hex(), "reset_info": reset_info},
    )

    trace: list[dict[str, object]] = [
        {
            "transition": 0,
            "events": ["RESET"],
            "active_mode": D052Mode.NORMAL.value,
            "command_source": None,
            "symbolic_proposal": None,
            "d050_mode": None,
            "x": initial_position[0],
            "y": initial_position[1],
            "heading": 0.0,
            "energy": float(observation[0]),
            "thermal": float(observation[1]),
            "charging_contact": bool(observation[5]),
            "charging_contact_before": None,
            "energy_after": float(observation[0]),
            "charging_contact_after": bool(observation[5]),
            "simulated_seconds": 0.0,
            "cycle_index": 0,
            "terminated": False,
            "truncated": False,
            "boundary_scale": 1.0,
        }
    ]
    cycle_count = 0
    current_cycle: int | None = None
    terminated = truncated = False
    for _ in range(VIS_D059_HORIZON):
        energy_before = float(observation[0])
        contact_before = bool(observation[5])
        proposal = fixture.propose()
        emitted = (
            candidate.command(observation, proposal.wheel_command)
            if candidate
            else None
        )
        decision = (
            emitted.decision
            if emitted
            else controller.command(observation, proposal.wheel_command)
        )
        command_source = (
            emitted.command_source.value if emitted else decision.command_source.value
        )
        wheels = (
            emitted.wheels
            if emitted
            else (
                decision.wheel_delta_left,
                decision.wheel_delta_right,
            )
        )
        if "RETURN_ACTIVATED" in decision.events:
            cycle_count += 1
            current_cycle = cycle_count
        if "RECOVERY_YIELD" in decision.events:
            current_cycle = None

        body = env.body
        if body is None:
            raise RuntimeError("body missing before step")
        pose_before = (body.x, body.y, body.heading)
        observation_after, reward, terminated, truncated, info = env.step(wheels)
        if reward != 0.0 or info != {}:
            raise RuntimeError("D-059 reward/info contract changed")
        telemetry = env.last_transition
        if telemetry is None:
            raise RuntimeError("missing transition telemetry")
        contact_after = bool(observation_after[5])
        events = list(decision.events)
        if not contact_before and contact_after:
            events.append("PHYSICAL_CONTACT_ACQUIRED")
            if decision.active_mode is D052Mode.RETURN:
                events.append("CHARGING_CONTACT")
        elif contact_before and not contact_after:
            events.append("PHYSICAL_CONTACT_LOST")
        if telemetry.terminated or telemetry.truncated:
            events.append("TERMINATED" if terminated else "TRUNCATED")

        d050_mode = decision.d050_mode.value if decision.d050_mode else None
        contact_token = _contact_token(env, telemetry.boundary_scale)
        causal_digest_row = {
            "observation_before": observation.tobytes().hex(),
            "proposal": list(proposal.wheel_command),
            "symbolic": getattr(proposal.symbolic_action, "name", None),
            "transition_index": decision.transition_index,
            "active_mode": decision.active_mode.value,
            "command_source": command_source,
            "passed_through": decision.passed_through,
            "preempted": decision.preempted,
            "d050_mode": d050_mode,
            "terminal_spin_count": decision.terminal_spin_count,
            "terminal_spin_exhausted": decision.terminal_spin_exhausted,
            "decision_events": list(decision.events),
            "decision_wheels": list(wheels),
            "reward": reward,
            "terminated": terminated,
            "truncated": truncated,
            "observation_after": observation_after.tobytes().hex(),
            "info": info,
            "pose_before": pose_before,
            "pose_after": telemetry.position_after,
            "heading_after": telemetry.heading_after,
            "battery_after": telemetry.battery_after_j,
            "temperature_after": telemetry.body_temperature_after_c,
            "contact": contact_token,
            "requested_wheel_delta": (
                telemetry.requested_delta_left,
                telemetry.requested_delta_right,
            ),
            "clamped_wheel_delta": (
                telemetry.clamped_delta_left,
                telemetry.clamped_delta_right,
            ),
            "actual_wheel_delta": (
                telemetry.actual_delta_left,
                telemetry.actual_delta_right,
            ),
            "boundary_scale": telemetry.boundary_scale,
            "charge_phase": telemetry.charge_phase.value,
            "actuator_electrical_power_w": telemetry.actuator_electrical_power_w,
            "total_electrical_load_w": telemetry.total_electrical_load_w,
            "actual_stored_power_w": telemetry.actual_stored_power_w,
            "energy_nonviable": telemetry.energy_nonviable,
            "protective_shutdown": telemetry.protective_shutdown,
            "emergency_hard_shutdown": telemetry.emergency_hard_shutdown,
            "termination_reason": (
                telemetry.termination_reason.value
                if telemetry.termination_reason is not None
                else None
            ),
        }
        d059._update_digest(digest, causal_digest_row)
        trace.append(
            {
                "transition": decision.transition_index,
                "events": events,
                "active_mode": decision.active_mode.value,
                "command_source": command_source,
                "symbolic_proposal": getattr(proposal.symbolic_action, "name", None),
                "d050_mode": d050_mode,
                "x": telemetry.position_after[0],
                "y": telemetry.position_after[1],
                "heading": telemetry.heading_after,
                "energy_before": energy_before,
                "energy_after": float(observation_after[0]),
                "energy": float(observation_after[0]),
                "thermal": float(observation_after[1]),
                "charging_contact_before": contact_before,
                "charging_contact_after": contact_after,
                "charging_contact": contact_after,
                "simulated_seconds": decision.transition_index * D045_DT_SECONDS,
                "cycle_index": cycle_count if current_cycle is None else current_cycle,
                "terminated": terminated,
                "truncated": truncated,
                "boundary_scale": telemetry.boundary_scale,
                "wall_interaction": (
                    telemetry.boundary_scale < 1.0
                    if substrate == "D045_1M"
                    else _has_s1_contact(env)
                ),
            }
        )
        observation = observation_after
        if terminated or truncated:
            break

    final_digest, _, _ = d059._final_causal_state_digests(
        env, controller, candidate, fixture, observation
    )
    recomputed = digest.hexdigest()
    tuple_label = f"seed={seed}, substrate={substrate}, arm={arm}"
    if recomputed != expected["trajectory_digest_sha256"]:
        raise ReplayMismatchError(
            f"trajectory digest mismatch for {tuple_label}: expected "
            f"{expected['trajectory_digest_sha256']}, recomputed {recomputed}"
        )
    if final_digest != expected["final_causal_state_digest_sha256"]:
        raise ReplayMismatchError(
            f"final causal-state digest mismatch for {tuple_label}: expected "
            f"{expected['final_causal_state_digest_sha256']}, recomputed {final_digest}"
        )

    data = adapt_vis_d059_trace(trace, seed=seed, substrate=substrate, arm=arm)
    return data, {
        "seed": seed,
        "substrate": substrate,
        "arm": arm,
        "expected_trajectory_digest_sha256": expected["trajectory_digest_sha256"],
        "recomputed_trajectory_digest_sha256": recomputed,
        "expected_final_causal_state_digest_sha256": expected[
            "final_causal_state_digest_sha256"
        ],
        "recomputed_final_causal_state_digest_sha256": final_digest,
        "result": "MATCH",
    }


def select_vis_d059_replay_indices(
    trace: Sequence[Mapping[str, object]],
) -> tuple[int, ...]:
    """Use the established D-053 deterministic stride/event-window sampler."""
    return visualizer.select_d053_replay_indices(trace)


def adapt_vis_d059_trace(
    trace: Sequence[Mapping[str, object]], *, seed: int, substrate: str, arm: str
) -> visualizer.DevelopmentVisualizationData:
    """Adapt a full replay trace into the shared neutral HTML replay model."""
    validate_allowlisted_tuple(seed, substrate, arm)
    room_side = 3.0 if substrate == "S1_3M" else 1.0
    station = (room_side / 2.0, room_side / 2.0)
    frames = []
    for index in select_vis_d059_replay_indices(trace):
        row = trace[index]
        events = list(cast(Sequence[str], row["events"]))
        if row.get("wall_interaction"):
            label = (
                "D045 BOUNDARY_SCALE < 1 — WALL ANATOMY UNKNOWN"
                if substrate == "D045_1M"
                else "S1 WALL CONTACT"
            )
            events.append(label)
        source = row.get("command_source")
        action = str(row.get("symbolic_proposal") or "INITIAL")
        if arm == "C":
            action = "D055 STALL-TURN CANDIDATE / " + action
        action = f"{substrate}/{arm} / {action}"
        frames.append(
            visualizer.DevelopmentVisualizationFrame(
                transition_index=cast(int, row["transition"]),
                x=cast(float, row["x"]),
                y=cast(float, row["y"]),
                heading=cast(float, row["heading"]),
                action=action,
                decision_mode=str(row["active_mode"]),
                energy=cast(float, row["energy"]),
                thermal=cast(float, row["thermal"]),
                charging_contact=bool(row["charging_contact"]),
                terminated=bool(row["terminated"]),
                truncated=bool(row["truncated"]),
                simulated_seconds=cast(float, row["simulated_seconds"]),
                charging_contact_before=cast(
                    bool | None, row.get("charging_contact_before")
                ),
                event_label=", ".join(events) if events else None,
                command_source=cast(str | None, source),
                cycle_index=cast(int, row["cycle_index"]),
            )
        )
    return visualizer.DevelopmentVisualizationData(
        source_label="VIS-D059 curated evaluator-only replay",
        seed=seed,
        world_min=D045_WORLD_MIN,
        world_max=(room_side, room_side),
        station_center=station,
        charging_radius=None,
        energy_range=visualizer.DevelopmentVisualizationRange(0.0, 1.0),
        thermal_range=visualizer.DevelopmentVisualizationRange(0.0, 1.0),
        frames=tuple(frames),
        visibility=visualizer.DevelopmentVisualizationVisibility(
            position_heading="EVALUATOR ONLY",
            station_location="EVALUATOR ONLY",
            energy="ORGANISM-VISIBLE NORMALIZED + EVALUATOR",
            thermal="ORGANISM-VISIBLE NORMALIZED + EVALUATOR",
            charging_contact="ORGANISM-VISIBLE BINARY + EVALUATOR",
            action_decision_mode="D-052 MODE/SOURCE; D-055 CANDIDATE ON C",
        ),
        energy_thresholds=((0.20, "RETURN 20%"), (0.80, "RECOVERY 80%")),
        causal_geometry=visualizer.DevelopmentCausalGeometry(
            body_length=0.180,
            body_width=0.215,
            rear_contact_plus=(0.0, D045_CONTACT_OFFSET_METRES),
            rear_contact_minus=(0.0, -D045_CONTACT_OFFSET_METRES),
            front_midpoint=(0.0, 0.0),
            dock_orientation=0.0,
            dock_contact_plus=(station[0], station[1] + D045_CONTACT_OFFSET_METRES),
            dock_contact_minus=(station[0], station[1] - D045_CONTACT_OFFSET_METRES),
            contact_tolerance=D045_CONTACT_TOLERANCE_METRES,
            contact_label="under-body contacts",
        ),
        figure_title=f"VIS-D059 seed {seed} — {substrate}/{arm}",
    )


def build_vis_d059_html(
    data: Sequence[visualizer.DevelopmentVisualizationData],
) -> str:
    """Build deterministic shared-renderer HTML with the curation warning."""
    title = f"VIS-D059 — {VIS_D059_WARNING}"
    html_text = visualizer.build_development_html_replay(
        data,
        schema="aweform.vis-d059.curated-replay.v1",
        title=title,
        event_navigation=True,
    )
    warning = f'<p class="note warning">{html.escape(VIS_D059_WARNING)}</p>'
    return html_text.replace(
        '<div class="controls">', f'{warning}<div class="controls">', 1
    )


def export_vis_d059_html(
    *,
    artifact_path: Path = Path("development/D-059-v05-s1-level1-floor-rebaseline.json"),
    output_path: Path = VIS_D059_OUTPUT,
) -> tuple[list[dict[str, object]], int]:
    """Replay all ten allowlisted lifetimes; write only after all digests match."""
    expected_rows = _accepted_digest_rows(artifact_path)
    data = []
    digest_rows = []
    for seed, substrate, arm in VIS_D059_TUPLES:
        item, digest_row = _replay_lifetime(
            seed, substrate, arm, expected_rows[(seed, substrate, arm)]
        )
        data.append(item)
        digest_rows.append(digest_row)
    html_text = build_vis_d059_html(data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_text, encoding="utf-8", newline="\n")
    return digest_rows, output_path.stat().st_size


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=VIS_D059_OUTPUT)
    parser.add_argument(
        "--artifact",
        type=Path,
        default=Path("development/D-059-v05-s1-level1-floor-rebaseline.json"),
    )
    args = parser.parse_args(argv)
    rows, size = export_vis_d059_html(
        artifact_path=args.artifact, output_path=args.output
    )
    print(json.dumps({"digest_matches": rows, "html_size_bytes": size}, indent=2))
    return 0
