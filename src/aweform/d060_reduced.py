"""Frozen, evaluator-only D060-REDUCED-v1 diagnostic.

The adapter deliberately reuses the pinned D-060/D-058 environments and the
independent D-060 oracle. Its small orchestration/check layer is maintained
separately because the original full runner has no selected-case interface.
It does not modify organism-visible state or the substrate law.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
from collections import Counter
from dataclasses import fields
from pathlib import Path
from typing import Any, Callable, Final, cast

import numpy as np

from . import d060
from . import d060_oracle as oracle
from .d045 import (
    D045_AMBIENT_TEMPERATURE_C,
    D045_INITIAL_BATTERY_J,
    D045_MAX_WHEEL_DELTA_RAD,
    D045_WHEEL_RADIUS_METRES,
    D045_WHEEL_TRACK_WIDTH_METRES,
    integrate_differential_drive,
    quantize_wheel_delta,
    wheel_effort,
)
from .d058 import D058Env, D058PhysicalConfig, _start_position

PROTOCOL_ID: Final = "D060-REDUCED-v1"
SCHEMA_VERSION: Final = "d060-reduced-v1"
BASE_SHA: Final = "039d0a4810aaffb6671f968a82fb6850b1596659"
MAIN_SHA: Final = "ce4f4943f6d8fcd84c723a151b15178f3856e098"
RAY_IDENTITIES: Final = (
    (12, 15, "Q1"),
    (22, 21, "Q1"),
    (22, 21, "Q11"),
    (22, 25, "Q8"),
    (22, 27, "Q1"),
    (24, 24, "Q8"),
    (28, 15, "Q8"),
) + tuple((ray, 0, "Q10") for ray in (0, 1, 6, 13, 25, 30, 36, 42, 48, 54, 60, 68))
H2C_HEADINGS: Final = (0, 1, 24, 28)
H2C_LOW_BATTERY_J: Final = 1065.6
TAU_ROOM: Final = 64 * (2.0**-52) * 3.0
_workspace_gap = cast(Callable[[Any, float, Any], float], oracle.workspace_gap)
_chord_crosses = cast(Callable[[Any, Any, Any], bool], oracle.chord_crosses_centerline)
_feature_rays = cast(Callable[[], tuple[Any, ...]], oracle._feature_rays)
_point_seg = cast(Callable[[Any, Any, Any], float], oracle._point_seg)
_point_arc_dist = cast(Callable[[Any, Any], float], oracle._point_arc_dist)


def _step(env: Any, command: tuple[float, float]) -> Any:
    return cast(Callable[[Any], Any], env.step)(command)


def _observation(env: Any) -> Any:
    return cast(Callable[[], Any], env._observation)().as_array()


def _headings() -> tuple[float, ...]:
    phi = math.atan(d060.C / d060.A)
    return tuple(k * math.pi / 12 for k in range(24)) + (
        phi,
        math.pi - phi,
        math.pi + phi,
        2 * math.pi - phi,
        math.pi / 2 - phi,
        math.pi / 2 + phi,
        3 * math.pi / 2 - phi,
        3 * math.pi / 2 + phi,
    )


def _commands() -> tuple[tuple[str, tuple[tuple[float, float], ...]], ...]:
    m = D045_MAX_WHEEL_DELTA_RAD
    vals = (-m, 0.0, m)
    u9 = tuple(
        (left, right) for left in vals for right in vals if (left, right) != (0.0, 0.0)
    ) + ((-0.565040862351, 0.645771823238),)
    return tuple((f"Q{i + 1}", (command,) * 8) for i, command in enumerate(u9)) + (
        ("Q10", ((m, m),) * 4 + ((m, -m),) * 8),
        ("Q11", ((-m, -m),) * 4 + ((-m, m),) * 8),
    )


def _u10_commands() -> tuple[tuple[float, float], ...]:
    m = D045_MAX_WHEEL_DELTA_RAD
    u9 = tuple(
        (left, right)
        for left in (-m, 0.0, m)
        for right in (-m, 0.0, m)
        if (left, right) != (0.0, 0.0)
    ) + ((-0.565040862351, 0.645771823238),)
    return u9 + ((0.0, 0.0),)


def _options(
    position: tuple[float, float],
    heading: float,
    battery: float = D045_INITIAL_BATTERY_J,
) -> dict[str, object]:
    return {
        "body_position": position,
        "station_center": (1.5, 1.5),
        "heading": heading,
        "battery_j": battery,
        "body_temperature_c": D045_AMBIENT_TEMPERATURE_C,
        "charger_termination_latched": False,
    }


def _corners(
    position: tuple[float, float], yaw: float
) -> tuple[tuple[float, float], ...]:
    co, si = math.cos(yaw), math.sin(yaw)
    return tuple(
        (
            position[0] + sx * d060.A * co - sy * d060.C * si,
            position[1] + sx * d060.A * si + sy * d060.C * co,
        )
        for sx, sy in ((-1.0, -1.0), (1.0, -1.0), (1.0, 1.0), (-1.0, 1.0))
    )


def _comparison_state(env: Any) -> dict[str, Any]:
    if env.body is None:
        raise AssertionError("H.2 comparison context lacks a body")
    return {
        "position": env.body.position,
        "heading": env.body.heading,
        "battery_j": env.battery_j,
        "body_temperature_c": env.body_temperature_c,
        "charger_termination_latched": env.charger_termination_latched,
        "energy": env.body.energy,
        "last_transition": env.last_transition,
        "last_room_stage": getattr(env, "last_room_stage", None),
        "last_step_contact": getattr(env, "last_step_contact", None),
        "last_contact": getattr(env, "last_contact", None),
    }


def _comparison_context(
    case: dict[str, Any],
    command: tuple[float, float],
    reset_options: dict[str, Any],
    actual: d060.D060Env,
    control: D058Env,
) -> dict[str, Any]:
    return {
        "case": case,
        "command": command,
        "reset_options": dict(reset_options),
        "pre_step_states": {
            "actual": _comparison_state(actual),
            "control": _comparison_state(control),
        },
    }


def _sign_case_record(
    *,
    env: d060.D060Env,
    case: dict[str, Any],
    command: tuple[float, float],
    obstacle: str,
    production_gap: float,
    oracle_gap: float,
) -> dict[str, Any]:
    if env.body is None or env.last_transition is None or env.last_step_contact is None:
        raise AssertionError(
            f"sign disagreement lacks executed D-060 telemetry: {case!r}"
        )
    step = env.last_step_contact
    contact = env.last_obstacle_stage
    return {
        "case": case,
        "command": command,
        "obstacle": obstacle,
        "production_gap_m": production_gap,
        "oracle_gap_m": oracle_gap,
        "production_classification": "penetrating" if production_gap < 0.0 else "clear",
        "oracle_classification": "penetrating" if oracle_gap < 0.0 else "clear",
        "execution_witness": {
            "case": case,
            "command": command,
            "resolved_by": step.resolved_by,
            "obstacle_id": contact.obstacle_id if contact is not None else None,
            "p0": env.last_transition.position_before,
            "theta0": env.last_transition.heading_before,
            "p_full": step.unconstrained_endpoint,
            "theta_full": env.last_transition.heading_after,
            "p_exec": step.executed_endpoint,
            "theta_exec": env.body.heading,
            "last_step_contact": {
                "resolved_by": step.resolved_by,
                "unconstrained_endpoint": step.unconstrained_endpoint,
                "executed_endpoint": step.executed_endpoint,
                "removed_displacement": step.removed_displacement,
                "removed_displacement_magnitude_m": (
                    step.removed_displacement_magnitude_m
                ),
            },
            "removed_displacement": step.removed_displacement,
            "removed_displacement_magnitude_m": step.removed_displacement_magnitude_m,
            "obstacle_contact": (
                None
                if contact is None
                else {
                    "obstacle_id": contact.obstacle_id,
                    "primitive": contact.primitive,
                    "p_room": contact.p_room,
                    "p_exec": contact.p_exec,
                    "push_out_vector": contact.push_out_vector,
                    "push_out_magnitude_m": contact.push_out_magnitude_m,
                    "unconstrained_gap_m": contact.unconstrained_gap_m,
                }
            ),
        },
    }


def _compare(
    actual: d060.D060Env,
    control: D058Env,
    obs_a: Any,
    obs_b: Any,
    ignore_index: bool,
    case: dict[str, Any],
    comparison_context: dict[str, Any],
    counters: Counter[str],
) -> None:
    if (
        actual.body is None
        or control.body is None
        or actual.last_step_contact is None
        or control.last_contact is None
    ):
        raise AssertionError(f"H.2 comparison lacks state: {case!r}")
    tr_a: Any = actual.last_transition
    tr_b: Any = control.last_transition
    if ignore_index:
        tr_a = tuple(
            (f.name, getattr(tr_a, f.name))
            for f in fields(tr_a)
            if f.name != "step_index"
        )
        tr_b = tuple(
            (f.name, getattr(tr_b, f.name))
            for f in fields(tr_b)
            if f.name != "step_index"
        )
    pairs = (
        ("position", actual.body.position, control.body.position),
        ("heading", actual.body.heading, control.body.heading),
        ("observation_bytes", obs_a.tobytes(), obs_b.tobytes()),
        ("battery_j", actual.battery_j, control.battery_j),
        ("temperature", actual.body_temperature_c, control.body_temperature_c),
        ("energy", actual.body.energy, control.body.energy),
        ("transition", tr_a, tr_b),
        ("room", actual.last_room_stage, control.last_contact),
        (
            "endpoint",
            actual.last_step_contact.executed_endpoint,
            control.last_contact.executed_endpoint,
        ),
        ("obstacle_stage", actual.last_obstacle_stage, None),
    )
    mismatch = [
        {"field": key, "actual": a, "control": b} for key, a, b in pairs if a != b
    ]
    failure_context = {
        **comparison_context,
        "compared_fields": tuple(name for name, _, _ in pairs),
        "ignore_step_index": ignore_index,
    }
    if mismatch:
        raise AssertionError(
            d060._h2_comparison_failure_context(
                case,
                failure_context,
                actual,
                control,
                obs_a,
                obs_b,
                ignore_index,
                mismatch,
            )
        )
    contact = control.last_contact
    wall_delta = (
        contact.executed_endpoint[0] - contact.unconstrained_endpoint[0],
        contact.executed_endpoint[1] - contact.unconstrained_endpoint[1],
    )
    direct_delta = (
        control.body.position[0] - contact.unconstrained_endpoint[0],
        control.body.position[1] - contact.unconstrained_endpoint[1],
    )
    reconstructed_endpoint = (
        contact.unconstrained_endpoint[0] + wall_delta[0],
        contact.unconstrained_endpoint[1] + wall_delta[1],
    )
    if (
        control.body.position != contact.executed_endpoint
        or wall_delta != direct_delta
        or reconstructed_endpoint != contact.executed_endpoint
    ):
        raise AssertionError(
            "D-058 H.2 wall reconstruction mismatch "
            f"case={case!r} reset_options={comparison_context['reset_options']!r} "
            f"contact={contact!r} control_position={control.body.position!r} "
            f"wall_delta={wall_delta!r} direct_delta={direct_delta!r}"
        )
    counters["d058_reconstruction_checks"] += 1


def _check_endpoint(
    env: d060.D060Env,
    command: tuple[float, float],
    case: dict[str, Any],
    counters: Counter[str],
    h6_stats: dict[str, Any] | None,
    *,
    lockstep: bool,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Selected-case analogue of D-060's nested check_one, without law duplication."""
    assert env.body is not None
    start, heading = env.body.position, env.body.heading
    was_reset = env._step_count == 0
    m = D045_MAX_WHEEL_DELTA_RAD
    left, right = min(max(command[0], -m), m), min(max(command[1], -m), m)
    full, full_yaw = integrate_differential_drive(
        start,
        heading,
        left,
        right,
        track_width_m=D045_WHEEL_TRACK_WIDTH_METRES,
        wheel_radius_m=D045_WHEEL_RADIUS_METRES,
    )
    oracle_gaps = tuple(
        _workspace_gap(full, full_yaw, item) for item in oracle.ORACLE_LAYOUT
    )
    production_gaps = tuple(
        d060._gap(full, full_yaw, item) for item in d060.FROZEN_LAYOUT
    )
    production_obstacle_violations = [
        index for index, gap in enumerate(production_gaps) if gap < 0.0
    ]
    sign_disagreements = d060._h2_boundary_sign_disagreements(
        production_gaps, oracle_gaps
    )
    fresh_control: D058Env | None = None
    fresh_result: Any = None
    fresh_comparison_context: dict[str, Any] | None = None
    if d060._h2b_requires_fresh_control(
        lockstep, production_obstacle_violations, sign_disagreements
    ):
        fresh_control = D058Env(D058PhysicalConfig(3.0))
        fresh_options = {
            "body_position": start,
            "station_center": env.station_center,
            "heading": heading,
            "battery_j": env.battery_j,
            "body_temperature_c": env.body_temperature_c,
            "charger_termination_latched": env.charger_termination_latched,
        }
        fresh_control.reset(options=fresh_options)
        reset_heading, _ = d060._restore_h2b_heading(fresh_control, heading)
        if heading != reset_heading:
            counters["h2b_heading_representation_restorations"] += 1
        counters["h2b_fresh_control_eligible"] += 1
        fresh_comparison_context = _comparison_context(
            case, command, fresh_options, env, fresh_control
        )
        fresh_result = _step(fresh_control, command)
    room_bad = any(
        x < 0.0 or x > 3.0 or y < 0.0 or y > 3.0 for x, y in _corners(full, full_yaw)
    )
    if sum(gap < 0.0 for gap in oracle_gaps) + int(room_bad) > 1:
        raise AssertionError(f"H.4 multiple constraints at endpoint {case!r}")
    stepper: Any = env.step
    transition_result = stepper(command)
    observation = transition_result[0]
    counters["transitions_executed"] += 1
    if (
        env.last_transition is None
        or env.last_step_contact is None
        or env.last_room_stage is None
    ):
        raise AssertionError(f"missing frozen telemetry: {case!r}")
    assert env.last_transition.heading_after == full_yaw
    assert env.last_transition.actual_delta_left == left
    assert env.last_transition.actual_delta_right == right
    assert env._previous_wheel_delta == (left, right)
    assert observation[6] == quantize_wheel_delta(left, env.config.encoder_quantum_rad)
    assert observation[7] == quantize_wheel_delta(right, env.config.encoder_quantum_rad)
    telemetry = env.last_transition
    config = env.config._base
    effort = wheel_effort(left, right, m)
    assert telemetry.actuator_electrical_power_w == config.wheel_power_scale_w * effort
    assert telemetry.total_electrical_load_w == (
        telemetry.electronics_electrical_power_w + telemetry.actuator_electrical_power_w
    )
    assert telemetry.battery_after_j == min(
        config.battery_capacity_j,
        max(
            0.0,
            telemetry.battery_before_j
            + telemetry.actual_stored_power_w * config.dt_seconds
            - telemetry.total_electrical_load_w * config.dt_seconds,
        ),
    )
    counters["actuator_bookkeeping_checks"] += 1
    if fresh_control is not None:
        assert fresh_result is not None and fresh_comparison_context is not None
        _compare(
            env,
            fresh_control,
            observation,
            fresh_result[0],
            True,
            case,
            fresh_comparison_context,
            counters,
        )
        counters["h2b_fresh_control_compared"] += 1

    # Independent room-wall check: reconstruct all four rotated corners, never
    # using production _extent as the verifier.
    corners = _corners(env.body.position, full_yaw)
    room_violation = max(
        0.0,
        *(-x for x, _ in corners),
        *(x - 3.0 for x, _ in corners),
        *(-y for _, y in corners),
        *(y - 3.0 for _, y in corners),
    )
    counters["h4_corner_checks"] += 4
    if room_violation > TAU_ROOM:
        raise AssertionError(
            f"H.4 rotated-corner violation {case!r}: {room_violation!r}"
        )
    for item, gap in zip(
        oracle.ORACLE_LAYOUT,
        (
            _workspace_gap(env.body.position, full_yaw, item)
            for item in oracle.ORACLE_LAYOUT
        ),
        strict=True,
    ):
        if gap < -d060.TAU_C:
            raise AssertionError(
                f"H.4 endpoint obstacle violation {case!r}: "
                f"obstacle={item[0]} gap={gap!r}"
            )
    room = env.last_room_stage
    total = env.last_step_contact
    wall_delta = (
        room.executed_endpoint[0] - room.unconstrained_endpoint[0],
        room.executed_endpoint[1] - room.unconstrained_endpoint[1],
    )
    obstacle_delta = (
        total.executed_endpoint[0] - room.executed_endpoint[0],
        total.executed_endpoint[1] - room.executed_endpoint[1],
    )
    direct = (
        total.executed_endpoint[0] - total.unconstrained_endpoint[0],
        total.executed_endpoint[1] - total.unconstrained_endpoint[1],
    )
    if (wall_delta[0] + obstacle_delta[0], wall_delta[1] + obstacle_delta[1]) != direct:
        raise AssertionError(f"H.2c wall/obstacle decomposition mismatch: {case!r}")
    counters["reconstruction_checks"] += 1
    if h6_stats is not None:
        h6_stats["h4_endpoint_checks"].append(
            {
                "case": case,
                "unconstrained_endpoint": total.unconstrained_endpoint,
                "executed_position": env.body.position,
                "executed_yaw": full_yaw,
                "corners": corners,
                "room_violation_m": room_violation,
                "oracle_obstacle_gaps_m": oracle_gaps,
                "production_obstacle_gaps_m": production_gaps,
                "wall_delta": wall_delta,
                "obstacle_delta": obstacle_delta,
                "direct_delta": direct,
            }
        )
    for target in oracle.ORACLE_LAYOUT:
        if target[1] in ("arc", "segment") and _chord_crosses(
            start, env.body.position, target
        ):
            raise AssertionError(f"H.4 chord crossed {target[0]} in {case!r}")
    contact = env.last_obstacle_stage
    displacement = math.dist(start, env.body.position)
    wheel_delta = D045_WHEEL_RADIUS_METRES * m
    theta_max = 2 * D045_WHEEL_RADIUS_METRES * m / D045_WHEEL_TRACK_WIDTH_METRES
    h6_bound = 2 * d060.R_H * math.sin(theta_max / 2) + wheel_delta
    if contact is not None:
        bound = (
            wheel_delta
            + d060.R_H
            + next(
                item[3] for item in d060.FROZEN_LAYOUT if item[0] == contact.obstacle_id
            )
        )
    elif env.last_step_contact.resolved_by == "room":
        bound = wheel_delta + math.sqrt(2.0) * h6_bound
    else:
        bound = wheel_delta
    if not d060._h4_step_kind_displacement(displacement, bound)["passes"]:
        raise AssertionError(f"H.4 step displacement bound failed {case!r}")
    counters["h4_step_displacement_checks"] += 1
    if contact is not None:
        room_stage = env.last_room_stage
        if (
            room_stage.pushing_x_min
            or room_stage.pushing_x_max
            or room_stage.pushing_y_min
            or room_stage.pushing_y_max
            or room_stage.removed_normal_displacement_m != 0.0
            or room_stage.slip_magnitude_m != 0.0
            or room_stage.executed_endpoint != full
            or room_stage.unconstrained_endpoint != full
        ):
            raise AssertionError(f"H.4 obstacle step has room projection {case!r}")
        obstacle = next(
            item for item in d060.FROZEN_LAYOUT if item[0] == contact.obstacle_id
        )
        if contact.active_contact_count not in (
            1,
            2,
        ) or contact.active_contact_count != len(contact.active_features):
            raise AssertionError(f"H.4 contact telemetry mismatch {case!r}")
        if contact.residual_m > d060.TAU_C:
            raise AssertionError(
                f"H.8 residual failure {case!r}: {contact.residual_m!r}"
            )
        allowed_features = {"centre-line", "inner-surface", "outer-surface", "end-cap"}
        if any(
            feature not in allowed_features for _, feature in contact.active_features
        ):
            raise AssertionError(f"H.4 non-normative contact feature {case!r}")
        projected, residual, _, _ = d060._project(env.body.position, full_yaw, obstacle)
        if math.dist(projected, env.body.position) > d060.TAU_C:
            raise AssertionError(f"H.4 idempotence failure {case!r}")
        if residual > d060.TAU_C:
            raise AssertionError(f"H.8 reapplication residual failure {case!r}")
        counters["h4_idempotence_checks"] += 1
        if contact.push_out_magnitude_m > d060.R_H + obstacle[3]:
            raise AssertionError(f"H.4 universal push-out bound failure {case!r}")
        if obstacle[1] in ("post", "segment") and contact.push_out_magnitude_m > (
            h6_bound + (d060.TAU_C if not was_reset else 0.0)
        ):
            raise AssertionError(f"H.4 convex push-out bound failure {case!r}")
        counters["obstacle_resolved_steps"] += 1
        best, no_free = d060._oracle_best_for_obstacle_step(
            env, full_yaw, obstacle, oracle, {**case, "command": command, "p0": start}
        )
        counters["oracle_rays"] += oracle.PHI_COUNT
        counters["oracle_no_free_rays"] += no_free
        if (
            contact.push_out_magnitude_m > best + d060.TAU_C
            or best - contact.push_out_magnitude_m > oracle.EPSILON
        ):
            raise AssertionError(
                f"O1/O2 failure {case!r}: push={contact.push_out_magnitude_m!r} "
                f"best={best!r}"
            )
    else:
        counters["non_obstacle_steps"] += 1

    if h6_stats is not None:
        bound = h6_bound

        def centerline_distance(point: tuple[float, float], item: Any) -> float:
            if item[1] == "post":
                return math.dist(point, item[2])
            if item[1] == "segment":
                return _point_seg(
                    point, (item[2][0], item[2][1]), (item[2][2], item[2][3])
                )
            return _point_arc_dist(point, item)

        nearby = [
            item
            for item in oracle.ORACLE_LAYOUT
            if centerline_distance(start, item) <= d060.R_H + item[3] + wheel_delta
        ]
        for k in range(1, 64):
            sample, _ = integrate_differential_drive(
                start,
                heading,
                left * k / 64,
                right * k / 64,
                track_width_m=D045_WHEEL_TRACK_WIDTH_METRES,
                wheel_radius_m=D045_WHEEL_RADIUS_METRES,
            )
            yaw = heading + (full_yaw - heading) * k / 64
            for item in nearby:
                penetration = max(0.0, -_workspace_gap(sample, yaw, item))
                h6_stats["samples"] += 1
                if penetration > bound:
                    raise AssertionError(
                        f"H.6 penetration exceeds frozen B in {case!r}, k={k}: "
                        f"{penetration!r}>{bound!r}"
                    )
                h6_stats["max_penetration_m"] = max(
                    h6_stats["max_penetration_m"], penetration
                )
    return oracle_gaps, production_gaps


def _record_checks(*, preflight: bool = False) -> dict[str, Any]:
    """Execute the fixed inventory and return deterministic results."""
    counters: Counter[str] = Counter()
    h6: dict[str, Any] = {
        "samples": 0,
        "max_penetration_m": 0.0,
        "h4_endpoint_checks": [],
    }
    identities: list[dict[str, Any]] = []
    rays = _feature_rays()
    headings = _headings()
    sequences = dict(_commands())
    m = D045_MAX_WHEEL_DELTA_RAD
    disagreements: Counter[str] = Counter()
    sign_cases: list[dict[str, Any]] = []
    ray_cases: list[tuple[int, int, str]] = []
    for ri, hi, qname in RAY_IDENTITIES:
        identity = (ri, hi, qname)
        if identity not in ray_cases:
            ray_cases.append(identity)
    for ray_index, heading_index, qname in ray_cases:
        oi, anchor, direction, feature_class = rays[ray_index]
        obstacle = d060.FROZEN_LAYOUT[oi]
        theta = headings[heading_index]
        radius = obstacle[3] + d060.R_H + 0.005
        position = (
            anchor[0] + radius * direction[0],
            anchor[1] + radius * direction[1],
        )
        reset = _options(position, theta)
        actual, control = d060.D060Env(), D058Env(D058PhysicalConfig(3.0))
        actual.reset(options=reset)
        control.reset(options=reset)
        lockstep = True
        commands = sequences[qname]
        for ci, command in enumerate(commands):
            case = {
                "family": "ray",
                "ray_index": ray_index,
                "heading_index": heading_index,
                "sequence": qname,
                "command_index": ci,
                "feature_class": feature_class,
            }
            comparison_context = _comparison_context(
                case, command, reset, actual, control
            )
            gaps_o, gaps_p = _check_endpoint(
                actual, command, case, counters, h6, lockstep=lockstep
            )
            for oi_gap, (pg, og) in enumerate(zip(gaps_p, gaps_o, strict=True)):
                if (pg < 0.0) != (og < 0.0):
                    direction_name = (
                        "production_penetrating_oracle_clear"
                        if pg < 0.0
                        else "production_clear_oracle_penetrating"
                    )
                    disagreements[direction_name] += 1
                    sign_cases.append(
                        _sign_case_record(
                            env=actual,
                            case=case,
                            command=command,
                            obstacle=d060.FROZEN_LAYOUT[oi_gap][0],
                            production_gap=pg,
                            oracle_gap=og,
                        )
                    )
            boundary_disagreements = d060._h2_boundary_sign_disagreements(
                gaps_p, gaps_o
            )
            counters["h2_boundary_sign_disagreements"] += len(boundary_disagreements)
            counters["h2_sign_disagreement_exclusions"] += len(boundary_disagreements)
            if d060._h2a_requires_lockstep_comparison(
                lockstep,
                [i for i, g in enumerate(gaps_p) if g < 0.0],
                d060._h2_boundary_sign_disagreements(gaps_p, gaps_o),
            ):
                control_result = _step(control, command)
                _compare(
                    actual,
                    control,
                    _observation(actual),
                    control_result[0],
                    False,
                    case,
                    comparison_context,
                    counters,
                )
                counters["h2_lockstep_steps_compared"] += 1
            elif lockstep and any(g < 0.0 for g in gaps_p):
                counters["h2_lockstep_excluded"] += 1
            if actual.last_obstacle_stage is not None:
                lockstep = False
        identities.append(
            {
                "family": "ray",
                "ray_index": ray_index,
                "heading_index": heading_index,
                "sequence": qname,
                "commands": len(commands),
            }
        )

    # All frozen pocket cases, in original obstacle/j/sign ordering.
    for oi, arc_obstacle in enumerate(d060.FROZEN_LAYOUT):
        if arc_obstacle[1] != "arc":
            continue
        geometry: Any = arc_obstacle[2]
        cx, cy, radius, a0, a1 = geometry
        for j in range(1 if preflight else 9):
            alpha = a0 + j * (a1 - a0) / 8
            for sign, heading, commands in (
                ("+", alpha, ((m, m),) * 16 + ((m, -m),) * 8 + ((-m, m),) * 8),
                (
                    "-",
                    alpha + math.pi,
                    ((-m, -m),) * 16 + ((-m, m),) * 8 + ((m, -m),) * 8,
                ),
            ):
                position = (cx, cy)
                reset = _options(position, heading)
                actual, control = d060.D060Env(), D058Env(D058PhysicalConfig(3.0))
                actual.reset(options=reset)
                control.reset(options=reset)
                lockstep = True
                two_inner = 0
                for ci, command in enumerate(commands):
                    case = {
                        "family": "pocket",
                        "obstacle": arc_obstacle[0],
                        "pocket_index": j,
                        "sign": sign,
                        "command_index": ci,
                    }
                    comparison_context = _comparison_context(
                        case, command, reset, actual, control
                    )
                    gaps_o, gaps_p = _check_endpoint(
                        actual, command, case, counters, h6, lockstep=lockstep
                    )
                    disagreements["production_penetrating_oracle_clear"] += sum(
                        pg < 0 <= og for pg, og in zip(gaps_p, gaps_o, strict=True)
                    )
                    disagreements["production_clear_oracle_penetrating"] += sum(
                        og < 0 <= pg for pg, og in zip(gaps_p, gaps_o, strict=True)
                    )
                    for gap_index, (pg, og) in enumerate(
                        zip(gaps_p, gaps_o, strict=True)
                    ):
                        if (pg < 0.0) != (og < 0.0):
                            sign_cases.append(
                                _sign_case_record(
                                    env=actual,
                                    case=case,
                                    command=command,
                                    obstacle=d060.FROZEN_LAYOUT[gap_index][0],
                                    production_gap=pg,
                                    oracle_gap=og,
                                )
                            )
                    boundary_disagreements = d060._h2_boundary_sign_disagreements(
                        gaps_p, gaps_o
                    )
                    counters["h2_boundary_sign_disagreements"] += len(
                        boundary_disagreements
                    )
                    counters["h2_sign_disagreement_exclusions"] += len(
                        boundary_disagreements
                    )
                    if (
                        actual.last_obstacle_stage is not None
                        and actual.last_obstacle_stage.active_contact_count == 2
                        and any(
                            feature == "inner-surface"
                            for _, feature in actual.last_obstacle_stage.active_features
                        )
                    ):
                        two_inner += 1
                    if d060._h2a_requires_lockstep_comparison(
                        lockstep,
                        [i for i, g in enumerate(gaps_p) if g < 0.0],
                        d060._h2_boundary_sign_disagreements(gaps_p, gaps_o),
                    ):
                        control_result = _step(control, command)
                        _compare(
                            actual,
                            control,
                            _observation(actual),
                            control_result[0],
                            False,
                            case,
                            comparison_context,
                            counters,
                        )
                        counters["h2_lockstep_steps_compared"] += 1
                    if actual.last_obstacle_stage is not None:
                        lockstep = False
                counters[f"pocket_two_inner_{arc_obstacle[0]}_{sign}"] += two_inner
                identities.append(
                    {
                        "family": "pocket",
                        "obstacle": arc_obstacle[0],
                        "j": j,
                        "sign": sign,
                        "commands": 32,
                    }
                )

    # H.5 exact selected reset triples for unique selected ray/heading pairs.
    reset_pairs = sorted({(ri, hi) for ri, hi, _ in ray_cases})
    for ray_index, heading_index in reset_pairs:
        oi, anchor, direction, _ = rays[ray_index]
        obstacle = d060.FROZEN_LAYOUT[oi]
        theta = headings[heading_index]
        for name, distance in (
            ("ring", obstacle[3] + d060.R_H + 0.005),
            ("near_penetrating", d060.A + obstacle[3] - 0.001),
            ("centre", 0.0),
        ):
            position = (
                anchor[0] + distance * direction[0],
                anchor[1] + distance * direction[1],
            )
            gaps = tuple(
                _workspace_gap(position, theta, item) for item in oracle.ORACLE_LAYOUT
            )
            should_reject = any(gap < 0.0 for gap in gaps)
            try:
                d060.D060Env().reset(
                    options={"body_position": position, "heading": theta}
                )
            except ValueError:
                accepted = False
            else:
                accepted = True
            if accepted == should_reject:
                raise AssertionError(
                    f"H.5 reset legality mismatch "
                    f"{(ray_index, heading_index, name)!r} gaps={gaps!r}"
                )
            counters["reset_attempts"] += 1
            identities.append(
                {
                    "family": "reset",
                    "ray_index": ray_index,
                    "heading_index": heading_index,
                    "kind": name,
                    "accepted": accepted,
                    "oracle_legal": not should_reject,
                }
            )

    # H.2(c): fixed wall/corner configurations and separately specified low-energy grid.
    starts: list[tuple[str, int, tuple[float, float], float, float]] = []
    for kind, labels in (
        ("wall", ("x_min", "x_max", "y_min", "y_max")),
        ("corner", ("x_min_y_min", "x_max_y_min", "x_min_y_max", "x_max_y_max")),
    ):
        for label in labels:
            for variant in ("flush", "near"):
                for hi in H2C_HEADINGS:
                    theta = headings[hi]
                    starts.append(
                        (
                            f"{kind}:{label}:{variant}",
                            hi,
                            _start_position(kind, label, variant, theta, 3.0),
                            theta,
                            D045_INITIAL_BATTERY_J,
                        )
                    )
    for x, y in ((0.75, 0.75), (2.25, 0.75), (0.75, 2.25), (2.25, 2.25)):
        for hi in H2C_HEADINGS:
            starts.append(
                (f"low-energy:{x}:{y}", hi, (x, y), headings[hi], H2C_LOW_BATTERY_J)
            )
    u10_commands = _u10_commands()
    counters["h2c_candidates_selected"] = len(starts) * len(u10_commands)
    for label, hi, position, theta, battery in starts:
        options = _options(position, theta, battery)
        gaps = tuple(
            _workspace_gap(position, theta, item) for item in oracle.ORACLE_LAYOUT
        )
        oracle_penetrates = any(gap < 0.0 for gap in gaps)
        try:
            d060.D060Env().reset(options=options)
        except ValueError:
            if not oracle_penetrates:
                raise AssertionError(
                    f"H.2(c) rejected oracle-legal reset {label} {hi} {gaps!r}"
                )
            counters["h2c_rejected"] += 1
            counters["h2c_candidates_excluded_reset"] += len(u10_commands)
            identities.append(
                {
                    "family": "h2c-start",
                    "label": label,
                    "heading_index": hi,
                    "position": position,
                    "battery_j": battery,
                    "reset_accepted": False,
                    "oracle_reset_gaps_m": gaps,
                    "excluded_candidate_indices": list(range(len(u10_commands))),
                }
            )
            continue
        if oracle_penetrates:
            raise AssertionError(
                f"H.2(c) accepted oracle-penetrating reset {label} {hi} {gaps!r}"
            )
        counters["h2c_eligible_starts"] += 1
        for ci, command in enumerate(u10_commands):
            actual, control = d060.D060Env(), D058Env(D058PhysicalConfig(3.0))
            actual.reset(options=options)
            control.reset(options=options)
            pfull, yaw_full = integrate_differential_drive(
                position,
                theta,
                *command,
                track_width_m=D045_WHEEL_TRACK_WIDTH_METRES,
                wheel_radius_m=D045_WHEEL_RADIUS_METRES,
            )
            gaps_p = tuple(
                d060._gap(pfull, yaw_full, item) for item in d060.FROZEN_LAYOUT
            )
            gaps_o = tuple(
                _workspace_gap(pfull, yaw_full, item) for item in oracle.ORACLE_LAYOUT
            )
            counters["h2c_candidates_attempted"] += 1
            oracle_eligible = all(gap >= 0.0 for gap in gaps_o)
            disagreements_here = d060._h2_boundary_sign_disagreements(gaps_p, gaps_o)
            if oracle_eligible:
                counters["h2c_candidate_oracle_eligible"] += 1
            for _, production_gap, oracle_gap in disagreements_here:
                direction_key = (
                    "h2c_sign_production_penetrating_oracle_clear"
                    if production_gap < 0.0
                    else "h2c_sign_production_clear_oracle_penetrating"
                )
                counters[direction_key] += 1
            compared = oracle_eligible and not disagreements_here
            if compared:
                counters["h2c_candidate_eligible"] += 1
                candidate_status = "eligible_and_compared"
                case = {
                    "family": "h2c-single",
                    "label": label,
                    "heading": hi,
                    "command": ci,
                }
                comparison_context = _comparison_context(
                    case, command, options, actual, control
                )
                _check_endpoint(actual, command, case, counters, h6, lockstep=True)
                control_result = _step(control, command)
                _compare(
                    actual,
                    control,
                    _observation(actual),
                    control_result[0],
                    False,
                    case,
                    comparison_context,
                    counters,
                )
                counters["h2c_single_compared"] += 1
            else:
                if not oracle_eligible:
                    counters["h2c_candidate_excluded_oracle"] += 1
                    candidate_status = "excluded_oracle_penetration"
                else:
                    counters["h2c_candidate_excluded_sign_disagreement"] += 1
                    candidate_status = "excluded_sign_disagreement"
                counters["h2c_single_ineligible"] += 1
            identities.append(
                {
                    "family": "h2c-single-candidate",
                    "label": label,
                    "heading_index": hi,
                    "command_index": ci,
                    "command": command,
                    "status": candidate_status,
                    "oracle_gaps_m": gaps_o,
                    "production_gaps_m": gaps_p,
                    "sign_disagreements": [
                        {
                            "obstacle": d060.FROZEN_LAYOUT[index][0],
                            "production_gap_m": production_gap,
                            "oracle_gap_m": oracle_gap,
                            "production_classification": "penetrating"
                            if production_gap < 0.0
                            else "clear",
                            "oracle_classification": "penetrating"
                            if oracle_gap < 0.0
                            else "clear",
                        }
                        for index, production_gap, oracle_gap in disagreements_here
                    ],
                }
            )
        identities.append(
            {
                "family": "h2c-start",
                "label": label,
                "heading_index": hi,
                "position": position,
                "battery_j": battery,
                "reset_accepted": True,
                "oracle_reset_gaps_m": gaps,
            }
        )

    # One frozen 64-command schedule; D-060 runs all 64 while D-058 follows
    # only eligible lockstep transitions as in original H.2(c).
    options = _options((0.75, 0.75), 0.0)
    actual, control = d060.D060Env(), D058Env(D058PhysicalConfig(3.0))
    actual.reset(options=options)
    control.reset(options=options)
    u10 = u10_commands
    lockstep = True
    for si in range(64):
        command = u10[si % 10]
        case = {"family": "h2c-64", "index": si}
        comparison_context = _comparison_context(
            case, command, options, actual, control
        )
        gaps_o, gaps_p = _check_endpoint(
            actual, command, case, counters, h6, lockstep=lockstep
        )
        oracle_eligible = all(gap >= 0.0 for gap in gaps_o)
        sign_disagreement = bool(d060._h2_boundary_sign_disagreements(gaps_p, gaps_o))
        if oracle_eligible:
            counters["h2c_64_oracle_eligible"] += 1
        if lockstep and oracle_eligible and not sign_disagreement:
            control_result = _step(control, command)
            _compare(
                actual,
                control,
                _observation(actual),
                control_result[0],
                False,
                case,
                comparison_context,
                counters,
            )
            counters["h2c_64_compared"] += 1
        else:
            if not oracle_eligible:
                counters["h2c_64_oracle_ineligible"] += 1
            elif sign_disagreement:
                counters["h2c_64_sign_excluded"] += 1
            else:
                counters["h2c_64_lockstep_excluded"] += 1
            lockstep = False
    identities.append(
        {
            "family": "h2c-64",
            "commands": 64,
            "schedule": "U10[i % 10]",
            "u10": u10,
        }
    )

    expected = {
        "ray_sequences": 19,
        "ray_transitions": 204,
        "pocket_sequences": 6 if preflight else 54,
        "pocket_transitions": 192 if preflight else 1728,
        "reset_attempts": 54,
        "h2c_single_candidates": 800,
        "h2c_64_commands": 64,
    }
    actual_selection = {
        "ray_sequences": len(ray_cases),
        "ray_transitions": sum(len(sequences[q]) for _, _, q in ray_cases),
        "pocket_sequences": sum(item["family"] == "pocket" for item in identities),
        "pocket_transitions": sum(
            item["commands"] for item in identities if item["family"] == "pocket"
        ),
        "reset_attempts": counters["reset_attempts"],
        "h2c_single_candidates": len(starts) * 10,
        "h2c_64_commands": 64,
    }
    if actual_selection != expected:
        raise AssertionError(
            "frozen inventory mismatch "
            f"expected={expected!r} actual={actual_selection!r}"
        )
    for obstacle_id in ("A1", "A2", "A3"):
        for pocket_sign in ("+", "-"):
            if (
                not preflight
                and counters[f"pocket_two_inner_{obstacle_id}_{pocket_sign}"] == 0
            ):
                raise AssertionError(
                    f"pocket two-inner-contact missing {obstacle_id}/{pocket_sign}"
                )
    result = {
        "schema_version": SCHEMA_VERSION,
        "protocol_id": PROTOCOL_ID,
        "outcome": (
            "D060_REDUCED_PREFLIGHT_ONLY"
            if preflight
            else "D060_REDUCED_DIAGNOSTIC_COMPLETE"
        ),
        "base_sha": BASE_SHA,
        "selection": actual_selection,
        "omitted_ray_sequences": 26733,
        "ray_pocket_transition_fraction": 1932 / 235200,
        "sign_disagreement_counts": dict(sorted(disagreements.items())),
        "sign_disagreement_cases": sign_cases,
        "counters": dict(sorted(counters.items())),
        "h4_endpoint_checks": h6["h4_endpoint_checks"],
        "h6": {
            "samples": h6["samples"],
            "max_penetration_m": h6["max_penetration_m"],
        },
        "expected_historical_disagreements": {
            "production_penetrating_oracle_clear": 7,
            "production_clear_oracle_penetrating": 7,
        },
        "inventory": identities,
    }
    if (
        disagreements["production_penetrating_oracle_clear"] != 7
        or disagreements["production_clear_oracle_penetrating"] != 7
    ):
        raise AssertionError(
            f"historical sign directions not both 7: {dict(disagreements)!r}"
        )
    return result


def run(executed_sha: str, output: Path, *, preflight: bool = False) -> None:
    try:
        result = _record_checks(preflight=preflight)
    except Exception as error:
        result = {
            "schema_version": SCHEMA_VERSION,
            "protocol_id": PROTOCOL_ID,
            "outcome": "D060_REDUCED_DIAGNOSTIC_STOP",
            "base_sha": BASE_SHA,
            "executed_sha": executed_sha,
            "failure_type": type(error).__name__,
            "failure": str(error),
        }
    result["executed_sha"] = executed_sha
    result["run_role"] = (
        "resource_preflight_only" if preflight else "full_reduced_result"
    )
    result["source_sha256"] = {
        "d060.py": hashlib.sha256(Path("src/aweform/d060.py").read_bytes()).hexdigest(),
        "d060_oracle.py": hashlib.sha256(
            Path("src/aweform/d060_oracle.py").read_bytes()
        ).hexdigest(),
        "d060_reduced.py": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    result["runtime"] = {
        "python": sys.version,
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "numpy": np.__version__,
    }
    payload = (
        json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload, encoding="utf-8")
    if result["outcome"] == "D060_REDUCED_DIAGNOSTIC_STOP":
        raise RuntimeError(
            f"{PROTOCOL_ID} stopped: {result['failure_type']}: {result['failure']}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executed-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    run(args.executed_sha, args.output, preflight=args.preflight)


if __name__ == "__main__":
    main()
