"""Unexecuted A2 first-event child; imported only inside its supervised child.

This module has no top-level Pymunk imports. The preparation parent must never
call ``run_a2_diagnostic`` without a separate exact-HEAD execution GO.
"""

from __future__ import annotations

import hashlib
import math
import os
import subprocess
import sys
from collections.abc import Callable, Sequence
from typing import Any, cast

from experiments.pymunk230_a2_instrumentation import (
    A2_ACTION,
    A2_CASE_ID,
    A2_START,
    CHECKPOINTS,
    DETAIL_WINDOW,
    EMPTY_FREE_ACTION,
    EMPTY_FREE_START,
    FROZEN_CASES_SHA256,
    FROZEN_PHYSICS_SHA256,
    MAX_SUBSTEPS,
    canonical_json,
    verify_a2_executable_identity,
)

SCHEMA = "pymunk230-a2-first-event-v1"
MATCH_RULE = "N800 even substeps match N400 at equal physical time"


def _emit(emit: Callable[[dict[str, object]], None], row: dict[str, object]) -> None:
    emit(row)


def _step_observer(
    world: Any, command_id: str, command_index: int
) -> list[dict[str, object]]:
    """Wrap Space.step to retain true pre/post state and callback deltas.

    Assignment is validated before the first engine step. If this Pymunk build
    does not permit an instance-level step wrapper, the child fails closed.
    """
    samples: list[dict[str, object]] = []
    space = world.space
    original_step = space.step
    if not callable(original_step):
        raise RuntimeError("space_step_not_callable")

    def observed_step(dt: float) -> None:
        body = world.body
        before = {
            "position_m": [float(body.position.x), float(body.position.y)],
            "heading_rad": float(body.angle),
            "velocity_mps": [float(body.velocity.x), float(body.velocity.y)],
            "angular_velocity_rps": float(body.angular_velocity),
        }
        refresh_suppressed = bool(
            world.suppress_velocity_refresh_after_contact
            and world._contact_seen_this_command
        )
        event_count_before = len(world._contact_events)
        seen_before = bool(world._contact_seen_this_command)
        original_step(dt)
        new_events = world._contact_events[event_count_before:]
        samples.append(
            {
                "command_id": command_id,
                "command_index": command_index,
                "substep": len(samples),
                "dt_s": dt,
                "motor_refresh_applied": not refresh_suppressed,
                "motor_velocity_before_step_mps": before["velocity_mps"],
                "motor_angular_velocity_before_step_rps": before[
                    "angular_velocity_rps"
                ],
                "contact_seen_before_step": seen_before,
                "contact_seen_after_step": bool(world._contact_seen_this_command),
                "callbacks": [
                    {
                        "shape_pair": list(event.shape_pair),
                        "contact_points": int(event.contact_points),
                        "impulse": float(event.impulse),
                        "penetration_m": float(event.maximum_contact_penetration),
                    }
                    for event in new_events
                ],
                "contact_set": sorted(
                    {"|".join(event.shape_pair) for event in new_events}
                ),
                "cumulative_contact_set": sorted(
                    {"|".join(event.shape_pair) for event in world._contact_events}
                ),
                "before": before,
                "after": {
                    "position_m": [float(body.position.x), float(body.position.y)],
                    "heading_rad": float(body.angle),
                    "velocity_mps": [float(body.velocity.x), float(body.velocity.y)],
                    "angular_velocity_rps": float(body.angular_velocity),
                },
            }
        )

    try:
        space.step = observed_step
        if space.step is not observed_step:
            raise RuntimeError("space_step_observer_not_installed")
    except (AttributeError, TypeError) as exc:
        raise RuntimeError("space_step_observer_unavailable") from exc
    world._a2_original_space_step = original_step
    return samples


def _restore_step_observer(world: Any) -> None:
    original_step = getattr(world, "_a2_original_space_step", None)
    if original_step is None:
        raise RuntimeError("space_step_observer_original_missing")
    world.space.step = original_step
    del world._a2_original_space_step


def _checkpoint_indices(count: int, command_id: str) -> dict[int, tuple[str, float]]:
    return {
        int(round(progress * count)): (command_id, progress)
        for checkpoint_command, progress in CHECKPOINTS
        if checkpoint_command == command_id
    }


def _squared_delta(a: Sequence[float], b: Sequence[float]) -> float:
    av = list(a)
    bv = list(b)
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(av, bv, strict=True)))


def _run_target_resolution(
    microsteps: int,
    *,
    emit: Callable[[dict[str, object]], None],
) -> tuple[int, dict[tuple[str, float], dict[str, object]], list[dict[str, object]]]:
    # Delayed import is intentional: importing the preparation/test surface
    # never imports or executes Pymunk. Only the explicitly supervised child
    # enters this function.
    from experiments.pymunk230_obstacles.cases import frozen_cases
    from experiments.pymunk230_obstacles.world import ObstacleContactWorld

    frozen = next(case for case in frozen_cases() if case.case_id == A2_CASE_ID)
    if frozen.start != A2_START or frozen.commands[:1] != (A2_ACTION,):
        raise RuntimeError("frozen_A2_case_identity_mismatch")
    world = ObstacleContactWorld(microsteps=microsteps)
    world.body.position = (A2_START[0], A2_START[1])
    world.body.angle = A2_START[2]
    total_samples = 0
    checkpoints: dict[tuple[str, float], dict[str, object]] = {}
    detailed_cmd2: list[dict[str, object]] = []
    for command_index, command_id in enumerate(("cmd1", "cmd2")):
        samples = _step_observer(world, command_id, command_index)
        try:
            result = world.advance(A2_ACTION)
        finally:
            _restore_step_observer(world)
        expected = microsteps
        if len(samples) != expected:
            raise RuntimeError("engine_step_observer_count_mismatch")
        total_samples += len(samples)
        command_checkpoints = _checkpoint_indices(microsteps, command_id)
        for progress_index, identity in command_checkpoints.items():
            if progress_index == 0:
                sample = samples[0]
                state = sample["before"]
                substep = 0
            else:
                sample = samples[progress_index - 1]
                state = sample["after"]
                substep = progress_index
            checkpoint_row: dict[str, object] = {
                "kind": "checkpoint",
                "schema": SCHEMA,
                "case_id": f"a2_n{microsteps}_{command_id}",
                "fixture_id": A2_CASE_ID,
                "resolution": microsteps,
                "command_id": command_id,
                "command_progress": identity[1],
                "substep": substep,
                "global_substep": (command_index * microsteps) + substep,
                "state": state,
                "shaft_rad": list(result.shaft),
                "contact_seen": bool(result.contact_seen),
                "motor_refresh_suppressed": not bool(sample["motor_refresh_applied"]),
                "total_callbacks": len(result.contact_events),
                "contact_set": [] if progress_index == 0 else sample["contact_set"],
                "callbacks": [] if progress_index == 0 else sample["callbacks"],
                "motor_refresh_applied": sample["motor_refresh_applied"],
                "motor_velocity_before_step_mps": sample[
                    "motor_velocity_before_step_mps"
                ],
                "motor_angular_velocity_before_step_rps": sample[
                    "motor_angular_velocity_before_step_rps"
                ],
            }
            checkpoints[(command_id, identity[1])] = checkpoint_row
            _emit(emit, checkpoint_row)
        if command_id == "cmd2":
            lower, upper = DETAIL_WINDOW
            for sample in samples:
                progress = cast(int, sample["substep"]) / microsteps
                if lower <= progress < upper:
                    detail_row: dict[str, object] = {
                        "kind": "detail",
                        "schema": SCHEMA,
                        "case_id": f"a2_n{microsteps}_cmd2",
                        "fixture_id": A2_CASE_ID,
                        "resolution": microsteps,
                        "command_id": command_id,
                        "command_progress": progress,
                        "command_end_progress": min(progress + 1 / microsteps, upper),
                        **sample,
                    }
                    detailed_cmd2.append(detail_row)
                    _emit(emit, detail_row)
        _emit(
            emit,
            {
                "kind": "command_summary",
                "schema": SCHEMA,
                "case_id": f"a2_n{microsteps}_{command_id}",
                "fixture_id": A2_CASE_ID,
                "resolution": microsteps,
                "command_id": command_id,
                "requested_action_rad": list(result.request),
                "shaft_rad": list(result.shaft),
                "start_m": list(result.start),
                "start_heading_rad": result.start_angle,
                "end_m": list(result.end),
                "end_heading_rad": result.end_angle,
                "velocity_mps": list(result.velocity),
                "angular_velocity_rps": result.angular_velocity,
                "contact_seen": bool(result.contact_seen),
                "callback_count": len(result.contact_events),
                "contact_events": [
                    {
                        "substep": int(event.substep_index),
                        "shape_pair": list(event.shape_pair),
                        "contact_points": int(event.contact_points),
                        "impulse": float(event.impulse),
                        "penetration_m": float(event.maximum_contact_penetration),
                    }
                    for event in result.contact_events
                ],
                "refresh_suppressed_any": bool(
                    world.suppress_velocity_refresh_after_contact
                    and any(bool(row["contact_seen_before_step"]) for row in samples)
                ),
            },
        )
    return total_samples, checkpoints, detailed_cmd2


def _run_empty_control(
    microsteps: int,
    role: str,
    *,
    emit: Callable[[dict[str, object]], None],
) -> bytes:
    from experiments.pymunk_contact_prototype.fixture import ContactWorld

    world = ContactWorld(microsteps=microsteps)
    world.body.position = (EMPTY_FREE_START[0], EMPTY_FREE_START[1])
    world.body.angle = EMPTY_FREE_START[2]
    samples = _step_observer(world, "F×1", 0)
    try:
        result = world.advance(EMPTY_FREE_ACTION)
    finally:
        _restore_step_observer(world)
    if len(samples) != microsteps:
        raise RuntimeError("control_step_observer_count_mismatch")
    if result.contact_events:
        raise RuntimeError("empty_free_control_contact")
    summary = {
        "kind": "control_summary",
        "schema": SCHEMA,
        "case_id": f"empty_free_n{microsteps}_{role}",
        "fixture_id": "empty-free",
        "role": role,
        "resolution": microsteps,
        "start": list(EMPTY_FREE_START),
        "action": list(EMPTY_FREE_ACTION),
        "end_m": list(result.end),
        "end_heading_rad": result.end_angle,
        "velocity_mps": list(result.velocity),
        "angular_velocity_rps": result.angular_velocity,
        "contact_events": [],
        "step_count": len(samples),
    }
    _emit(emit, summary)
    return canonical_json(
        {key: value for key, value in summary.items() if key not in {"case_id", "role"}}
    )


def _compare_states(
    left: dict[str, object], right: dict[str, object]
) -> dict[str, object]:
    left_state = cast(dict[str, object], left["state"])
    right_state = cast(dict[str, object], right["state"])
    left_pose = cast(list[float], left_state["position_m"])
    right_pose = cast(list[float], right_state["position_m"])
    left_velocity = cast(list[float], left_state["velocity_mps"])
    right_velocity = cast(list[float], right_state["velocity_mps"])
    yaw_delta = math.atan2(
        math.sin(
            float(cast(float, left_state["heading_rad"]))
            - float(cast(float, right_state["heading_rad"]))
        ),
        math.cos(
            float(cast(float, left_state["heading_rad"]))
            - float(cast(float, right_state["heading_rad"]))
        ),
    )
    position_delta = _squared_delta(left_pose, right_pose)
    velocity_delta = _squared_delta(left_velocity, right_velocity)
    contact_left = set(cast(list[str], left["contact_set"]))
    contact_right = set(cast(list[str], right["contact_set"]))
    callbacks_differ = left["callbacks"] != right["callbacks"]
    refresh_differs = left["motor_refresh_applied"] != right["motor_refresh_applied"]
    left_motor_velocity = cast(list[float], left["motor_velocity_before_step_mps"])
    right_motor_velocity = cast(list[float], right["motor_velocity_before_step_mps"])
    motor_velocity_delta = _squared_delta(left_motor_velocity, right_motor_velocity)
    motor_angular_delta = float(
        cast(float, left["motor_angular_velocity_before_step_rps"])
    ) - float(cast(float, right["motor_angular_velocity_before_step_rps"]))
    categories: list[str] = []
    if contact_left != contact_right:
        categories.append("contact_or_chord_set")
    if callbacks_differ:
        categories.append("callback_values")
    if refresh_differs:
        categories.append("motor_refresh_decision")
    if motor_velocity_delta != 0.0 or motor_angular_delta != 0.0:
        categories.append("motor_state")
    if position_delta != 0.0 or yaw_delta != 0.0 or velocity_delta != 0.0:
        categories.append("pose_heading_or_velocity")
    return {
        "categories": categories,
        "n400": left,
        "n800": right,
        "contact_set_added_at_n800": sorted(contact_right - contact_left),
        "contact_set_missing_at_n800": sorted(contact_left - contact_right),
        "callback_values_differ": callbacks_differ,
        "motor_refresh_decision_differs": refresh_differs,
        "motor_velocity_before_step_n400_mps": left_motor_velocity,
        "motor_velocity_before_step_n800_mps": right_motor_velocity,
        "motor_velocity_delta_mps": motor_velocity_delta,
        "motor_angular_velocity_delta_rps": motor_angular_delta,
        "position_delta_m": position_delta,
        "heading_delta_rad_wrapped": yaw_delta,
        "velocity_delta_mps": velocity_delta,
        "angular_velocity_delta_rps": float(
            cast(float, left_state["angular_velocity_rps"])
        )
        - float(cast(float, right_state["angular_velocity_rps"])),
        "threshold_interpretation": (
            "descriptive exact numeric differences; no acceptance threshold"
        ),
    }


def _emit_comparisons(
    checkpoints_by_resolution: dict[int, dict[tuple[str, float], dict[str, object]]],
    detail_by_resolution: dict[int, list[dict[str, object]]],
    *,
    emit: Callable[[dict[str, object]], None],
) -> None:
    first: dict[str, dict[str, object] | None] = {
        "contact_or_chord_set": None,
        "callback_values": None,
        "motor_refresh_decision": None,
        "motor_state": None,
        "pose_heading_or_velocity": None,
    }
    for command_id, progress in CHECKPOINTS:
        left = checkpoints_by_resolution[400][(command_id, progress)]
        right = checkpoints_by_resolution[800][(command_id, progress)]
        comparison = _compare_states(left, right)
        for category in cast(list[str], comparison["categories"]):
            if first[category] is None:
                first[category] = {
                    "command_id": command_id,
                    "command_progress": progress,
                    "comparison": comparison,
                }
        _emit(
            emit,
            {
                "kind": "matched_checkpoint_comparison",
                "schema": SCHEMA,
                "command_id": command_id,
                "command_progress": progress,
                "n800_even_substep_match": True,
                **comparison,
            },
        )
    high_detail = {cast(int, row["substep"]): row for row in detail_by_resolution[800]}
    for low in detail_by_resolution[400]:
        low_index = cast(int, low["substep"])
        high = high_detail.get(low_index * 2)
        if high is None:
            raise RuntimeError("equal_time_detailed_match_missing")

        def state_row(row: dict[str, object]) -> dict[str, object]:
            state = cast(dict[str, object], row["after"])
            return {
                "state": state,
                "contact_set": row["contact_set"],
                "callbacks": row["callbacks"],
                "motor_refresh_applied": row["motor_refresh_applied"],
                "motor_velocity_before_step_mps": row["motor_velocity_before_step_mps"],
                "motor_angular_velocity_before_step_rps": row[
                    "motor_angular_velocity_before_step_rps"
                ],
            }

        comparison = _compare_states(state_row(low), state_row(high))
        _emit(
            emit,
            {
                "kind": "matched_detail_comparison",
                "schema": SCHEMA,
                "command_id": "cmd2",
                "command_progress": low["command_progress"],
                "n800_even_substep_match": True,
                **comparison,
            },
        )
    _emit(emit, {"kind": "first_divergences", "schema": SCHEMA, "by_category": first})


def run_a2_diagnostic(emit: Callable[[dict[str, object]], None]) -> None:
    """Emit one fixed A2 diagnostic stream; caller must provide a bounded parent."""
    from experiments.pymunk230_a2_instrumentation import (
        verify_candidate_source_identity,
    )

    candidate_identity = verify_candidate_source_identity()
    executable_identity = verify_a2_executable_identity()
    _emit(
        emit,
        {
            "kind": "diagnostic_manifest",
            "schema": SCHEMA,
            "status": "diagnostic_execution_in_progress",
            "fixture_id": A2_CASE_ID,
            "start": list(A2_START),
            "action": list(A2_ACTION),
            "resolutions": [400, 800],
            "checkpoints": [[command, progress] for command, progress in CHECKPOINTS],
            "detail_window_inclusive": list(DETAIL_WINDOW),
            "matching": MATCH_RULE,
            "controls": ["empty-free primary/fresh replay at N400/N800"],
            "planned_substeps": MAX_SUBSTEPS,
            "cases_source_sha256": FROZEN_CASES_SHA256,
            "physics_source_sha256": FROZEN_PHYSICS_SHA256,
            "source_content_identity": executable_identity,
            "candidate_source_identity": candidate_identity,
            "retry_policy": "none",
        },
    )
    checkpoints_by_resolution: dict[
        int, dict[tuple[str, float], dict[str, object]]
    ] = {}
    detail_by_resolution: dict[int, list[dict[str, object]]] = {}
    target_steps = 0
    for resolution in (400, 800):
        steps, checkpoints, details = _run_target_resolution(resolution, emit=emit)
        target_steps += steps
        checkpoints_by_resolution[resolution] = checkpoints
        detail_by_resolution[resolution] = details
    _emit_comparisons(checkpoints_by_resolution, detail_by_resolution, emit=emit)
    control_streams: list[bytes] = []
    control_steps = 0
    for n in (400, 800):
        primary = _run_empty_control(n, "primary", emit=emit)
        replay = _run_empty_control(n, "fresh_replay", emit=emit)
        control_streams.extend((primary, replay))
        control_steps += n * 2
        if primary != replay:
            raise RuntimeError("empty_free_primary_replay_mismatch")
    if target_steps != 2_400 or control_steps != 2_400:
        raise RuntimeError("total_substep_accounting_mismatch")
    _emit(
        emit,
        {
            "kind": "diagnostic_complete",
            "schema": SCHEMA,
            "target_substeps": target_steps,
            "control_substeps": control_steps,
            "total_substeps": target_steps + control_steps,
            "control_stream_sha256": hashlib.sha256(
                b"\n".join(control_streams)
            ).hexdigest(),
            "scientific_result": "not_an_acceptance_run",
        },
    )


def child_main() -> int:
    """Internal child entry; no CLI routes here from the preparation parent."""

    def emit(row: dict[str, object]) -> None:
        sys.stdout.buffer.write(canonical_json(row) + b"\n")
        sys.stdout.buffer.flush()

    try:
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.PIPE
        ).strip()
        if os.environ.get("AWEFORM_A2_EXECUTION_GO_SHA") != head:
            emit(
                {
                    "kind": "diagnostic_child_error",
                    "schema": SCHEMA,
                    "error_type": "ExecutionGateClosed",
                    "error": "fresh exact-HEAD execution GO is absent",
                }
            )
            return 2
        run_a2_diagnostic(emit)
    except Exception as exc:
        emit(
            {
                "kind": "diagnostic_child_error",
                "schema": SCHEMA,
                "error_type": type(exc).__name__,
                "error": str(exc)[:512],
            }
        )
        return 1
    return 0


if __name__ == "__main__":
    if sys.argv[1:] != ["--diagnostic-child"]:
        raise SystemExit(
            "diagnostic child is internal and requires supervisor execution"
        )
    raise SystemExit(child_main())
