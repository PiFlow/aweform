from __future__ import annotations

import math
import subprocess
from pathlib import Path

import numpy as np
import pytest

from aweform import d060
from aweform.d045 import D045_MAX_WHEEL_DELTA_RAD, integrate_differential_drive
from aweform.d060_oracle import ORACLE_LAYOUT, _edge_curve_distance, workspace_gap


def test_contact_count_serialization_accepts_numeric_command_index() -> None:
    counts = {("A2", "arc-convex", "Q1", 5): 1}
    assert d060._serialize_count_keys(counts) == {"A2|arc-convex|Q1|5": 1}


def test_h4_projection_summary_persists_required_aggregates() -> None:
    summary = d060._h4_projection_summary(
        {"exact": 7, "within_tau_c": 9},
        {("A2", "arc-convex", "Q1", 5): 9},
        {"minimum_no_cross_margin_m": 0.02, "largest_arc_push_out_m": 0.03},
    )
    assert summary == {
        "obstacle_resolved_steps": 9,
        "idempotence_exact_count": 7,
        "idempotence_within_tau_c_count": 9,
        "minimum_no_cross_margin_m": 0.02,
        "largest_arc_push_out_m": 0.03,
    }


def test_fixed_config_and_frozen_layout_are_independent() -> None:
    assert d060.D060PhysicalConfig().room_side_m == 3.0
    for invalid in (1.0, 2.0, True, float("nan")):
        with pytest.raises(ValueError):
            d060.D060PhysicalConfig(invalid)
    assert not hasattr(d060.D060PhysicalConfig(), "world_min")
    assert not hasattr(d060.D060PhysicalConfig(), "world_max")
    assert tuple(d060.FROZEN_LAYOUT) == ORACLE_LAYOUT


def test_closed_segment_intersection_respects_finite_bounds() -> None:
    # Regression for S1's y=.55 centre-line and a disjoint collinear hull edge.
    assert not d060._segments_cross((2.0, .55), (2.5, .55), (1.175, .55), (1.825, .55))
    # Collinear overlap and endpoint contact are intersections.
    assert d060._segments_cross((1.5, .55), (2.0, .55), (1.175, .55), (1.825, .55))
    assert d060._segments_cross((1.825, .55), (2.0, .55), (1.175, .55), (1.825, .55))
    # Ordinary proper crossing remains an intersection.
    assert d060._segments_cross((0.0, 0.0), (1.0, 1.0), (0.0, 1.0), (1.0, 0.0))
    assert not d060._segments_cross((0.0, 0.0), (1.0, 0.0), (2.0, -1.0), (2.0, 1.0))


def test_oracle_finite_arc_edge_distance_uses_real_sweep_intersections() -> None:
    obstacle = ORACLE_LAYOUT[0]
    # This exact legal endpoint was the H.4 STOP case. Rectangle/arc geometry
    # has positive clearance; entering the full arc circle is not intersection
    # with the finite A1 sweep.
    pose = (1.5858398934902447, 2.199011989198904)
    assert workspace_gap(pose, 0.0, obstacle) == pytest.approx(
        0.021631541213240534, abs=1e-15
    )

    # A segment through the top of A1 genuinely intersects its 30°..150° arc.
    assert _edge_curve_distance((1.2, 2.4), (1.8, 2.4), obstacle) == 0.0
    # This segment crosses the supporting circle only at angles 0 and pi,
    # outside A1's finite sweep, so its distance to the arc is positive.
    assert _edge_curve_distance((1.0, 2.0), (2.0, 2.0), obstacle) > 0.0


def test_oracle_arc_caps_measure_distance_to_edge_interiors() -> None:
    obstacle = ORACLE_LAYOUT[0]
    # The A1 30° cap is (1.8464101615137756, 2.2). Its projection onto
    # this horizontal edge is interior and exactly 0.04 m away.
    edge = ((1.71, 2.16), (1.89, 2.16))
    assert _edge_curve_distance(*edge, obstacle) == pytest.approx(0.04, abs=1e-15)

    # Captured O1 ray endpoint: the same cap projects onto hull edge 0 at
    # distance 0.024316968189213115 m, inside the 0.025 m obstacle radius.
    illegal_point = (1.7075857012126152, 2.1279412153893746)
    illegal_heading = 2.6179938779914944
    assert workspace_gap(illegal_point, illegal_heading, obstacle) == pytest.approx(
        -0.0006830318107868862, abs=5e-16
    )

    # At this independent pose the cap projects onto the top edge at 0.04 m,
    # leaving 0.015 m positive clearance after the 0.025 m obstacle radius.
    legal_pose = (1.8, 2.0525)
    assert workspace_gap(legal_pose, 0.0, obstacle) == pytest.approx(0.015, abs=1e-15)


def test_active_contact_witnesses_canonicalize_only_exact_shared_geometry() -> None:
    obstacle = d060.FROZEN_LAYOUT[0]
    selected = (1.7578254243912743, 2.4979607879517336)
    measured, canonical = d060._active_contact_witnesses(selected, 0.0, obstacle)
    assert [item["hull_feature"] for item in measured] == ["vertex-0", "edge-0", "edge-3"]
    assert len(canonical) == 1
    assert canonical[0]["obstacle_feature"] == "outer-surface"
    assert all(item["hull_witness"] == measured[0]["hull_witness"] for item in measured)
    assert all(item["boundary_witness"] == measured[0]["boundary_witness"] for item in measured)

    # Equal clearance alone is insufficient: two separate S1 face witnesses
    # remain distinct even though their scalar distances are exactly equal.
    segment = d060.FROZEN_LAYOUT[3]
    position = (1.5, .55 + d060.C + segment[3])
    measured, canonical = d060._active_contact_witnesses(position, 0.0, segment)
    vertices = [item for item in canonical if item["hull_feature"].startswith("vertex-")]
    assert len(vertices) == 2
    assert vertices[0]["distance_m"] == vertices[1]["distance_m"]
    assert abs(vertices[0]["distance_m"] - segment[3]) <= d060.TAU_C
    assert vertices[0]["hull_witness"] != vertices[1]["hull_witness"]
    assert vertices[0]["boundary_witness"] != vertices[1]["boundary_witness"]


def test_two_distinct_inner_arc_pocket_contacts_are_retained() -> None:
    obstacle = d060.FROZEN_LAYOUT[0]
    cx, cy, r0, _, _ = obstacle[2]
    y = cy + math.sqrt((r0 - obstacle[3]) ** 2 - d060.A**2) - d060.C
    measured, canonical = d060._active_contact_witnesses((cx, y), 0.0, obstacle)
    assert len(canonical) == 2
    assert {item["obstacle_feature"] for item in canonical} == {"inner-surface"}
    assert canonical[0]["hull_witness"] != canonical[1]["hull_witness"]
    assert canonical[0]["boundary_witness"] != canonical[1]["boundary_witness"]


def test_reset_boundary_and_private_telemetry() -> None:
    env = d060.make_d060_env()
    observation, info = env.reset()
    assert observation.dtype == np.float32 and observation.shape == (8,)
    assert info == {} and env.body.position == (.75, .75)
    assert env.station_center == (1.5, 1.5)
    assert env.last_room_stage is env.last_obstacle_stage is env.last_step_contact is None
    assert not hasattr(env, "last_contact")
    with pytest.raises(ValueError):
        env.reset(options={"station_center": (1.4, 1.5)})
    with pytest.raises(ValueError):
        env.reset(options={"unknown": 1})
    with pytest.raises(ValueError):
        env.reset(options={"body_position": (1.5, 1.5), "charger_termination_latched": 1})


def test_no_contact_step_matches_d058_bit_for_bit() -> None:
    options = {"body_position": (.75, .75), "station_center": (1.5, 1.5),
               "heading": .2, "battery_j": 1065.6,
               "body_temperature_c": 23.0, "charger_termination_latched": False}
    actual, control = d060.D060Env(), d060.D058Env(d060.D058PhysicalConfig())
    actual.reset(options=options); control.reset(options=options)
    cmd = (D045_MAX_WHEEL_DELTA_RAD, 0.0)
    oa, *_ = actual.step(cmd); ob, *_ = control.step(cmd)
    assert actual.body.position == control.body.position
    assert actual.body.heading == control.body.heading
    assert oa.tobytes() == ob.tobytes()
    assert actual.battery_j == control.battery_j
    assert actual.body_temperature_c == control.body_temperature_c
    assert actual.last_transition == control.last_transition
    assert actual.last_room_stage == control.last_contact
    assert actual.last_step_contact.executed_endpoint == control.body.position
    assert actual.last_obstacle_stage is None


def test_obstacle_endpoint_projection_and_yaw_are_exact() -> None:
    obstacle = d060.FROZEN_LAYOUT[0]
    cx, cy, r0, a0, a1 = obstacle[2]
    angle = a0 + (a1 - a0) / 4
    anchor = (cx + r0 * math.cos(angle), cy + r0 * math.sin(angle))
    u = (math.cos(angle), math.sin(angle))
    start = (anchor[0] + (obstacle[3] + d060.R_H + .005) * u[0],
             anchor[1] + (obstacle[3] + d060.R_H + .005) * u[1])
    env = d060.D060Env()
    env.reset(options={"body_position": start, "heading": angle})
    before, heading = env.body.position, env.body.heading
    env.step((-D045_MAX_WHEEL_DELTA_RAD, -D045_MAX_WHEEL_DELTA_RAD))
    env.step((-D045_MAX_WHEEL_DELTA_RAD, 0.0))
    before, heading = env.body.position, env.body.heading
    env.step((0.0, -D045_MAX_WHEEL_DELTA_RAD))
    contact = env.last_obstacle_stage
    assert contact is not None and contact.obstacle_id == "A1"
    assert env.last_transition.heading_after == integrate_differential_drive(
        before, heading, 0.0, -D045_MAX_WHEEL_DELTA_RAD
    )[1]
    assert all(workspace_gap(env.body.position, env.body.heading, item) >= -d060.TAU_C
               for item in ORACLE_LAYOUT)
    assert env.last_room_stage.pushing_x_min is False
    assert env.last_step_contact.resolved_by == "obstacle"
    assert env.last_step_contact.removed_displacement == (
        env.body.position[0] - env.last_step_contact.unconstrained_endpoint[0],
        env.body.position[1] - env.last_step_contact.unconstrained_endpoint[1],
    )


def test_conformance_oracle_uses_unified_unconstrained_endpoint() -> None:
    obstacle = d060.FROZEN_LAYOUT[0]
    cx, cy, r0, a0, a1 = obstacle[2]
    angle = a0 + (a1 - a0) / 4
    anchor = (cx + r0 * math.cos(angle), cy + r0 * math.sin(angle))
    u = (math.cos(angle), math.sin(angle))
    start = (anchor[0] + (obstacle[3] + d060.R_H + .005) * u[0],
             anchor[1] + (obstacle[3] + d060.R_H + .005) * u[1])
    env = d060.D060Env()
    env.reset(options={"body_position": start, "heading": angle})
    env.step((-D045_MAX_WHEEL_DELTA_RAD, -D045_MAX_WHEEL_DELTA_RAD))
    env.step((-D045_MAX_WHEEL_DELTA_RAD, 0.0))
    env.step((0.0, -D045_MAX_WHEEL_DELTA_RAD))
    assert env.last_obstacle_stage is not None
    expected_p_full = env.last_step_contact.unconstrained_endpoint
    assert env.last_obstacle_stage.p_room == expected_p_full

    class Oracle:
        def oracle_best_free_distance(self, point, theta, target):
            assert point == expected_p_full
            assert theta == env.last_transition.heading_after
            assert target == obstacle
            return .125, 7

    assert d060._oracle_best_for_obstacle_step(
        env, env.last_transition.heading_after, obstacle, Oracle(),
        {"family": "unit", "command": (0.0, -D045_MAX_WHEEL_DELTA_RAD), "p0": start},
    ) == (.125, 7)


@pytest.mark.parametrize(
    ("lockstep", "obstacle_violations", "expected"),
    ((True, [], False), (True, [0], False), (False, [0], False), (False, [], True)),
)
def test_h2b_fresh_control_only_covers_steps_after_lockstep(
    lockstep: bool, obstacle_violations: list[int], expected: bool,
) -> None:
    assert d060._h2b_requires_fresh_control(lockstep, obstacle_violations) is expected


def test_h2_boundary_sign_disagreement_and_h2b_eligibility_at_captured_one_ulp_case() -> None:
    # Frozen A2/ray12/arc-convex/H32[15]/Q1 command 5 from the approved STOP.
    options = {
        "body_position": (2.2232031986427216, 1.7182063797369498),
        "station_center": (1.5, 1.5),
        "heading": 3.926990816987241,
        "battery_j": 2664.0,
        "body_temperature_c": 23.0,
        "charger_termination_latched": False,
    }
    command = (-D045_MAX_WHEEL_DELTA_RAD, -D045_MAX_WHEEL_DELTA_RAD)
    env = d060.D060Env()
    env.reset(options=options)
    for _ in range(5):
        env.step(command)

    p_full, theta_full = integrate_differential_drive(
        env.body.position, env.body.heading, *command,
        track_width_m=d060.D045_WHEEL_TRACK_WIDTH_METRES,
        wheel_radius_m=d060.D045_WHEEL_RADIUS_METRES,
    )
    production_gaps = tuple(d060._gap(p_full, theta_full, obstacle)
                            for obstacle in d060.FROZEN_LAYOUT)
    oracle_gaps = tuple(workspace_gap(p_full, theta_full, obstacle)
                        for obstacle in ORACLE_LAYOUT)
    production_violations = [i for i, gap in enumerate(production_gaps) if gap < 0.0]

    assert production_gaps[1] == -5.204170427930421e-17
    assert oracle_gaps[1] == 1.0755285551056204e-16
    assert d060._h2_boundary_sign_disagreements(production_gaps, oracle_gaps) == (
        (1, production_gaps[1], oracle_gaps[1]),
    )
    assert not d060._h2b_requires_fresh_control(False, production_violations)
    assert not d060._h2b_requires_fresh_control(
        False, production_violations,
        d060._h2_boundary_sign_disagreements(production_gaps, oracle_gaps),
    )
    opposite_sign = ((1, 1.0e-16, -1.0e-16),)
    assert not d060._h2a_requires_lockstep_comparison(True, [], opposite_sign)
    assert not d060._h2b_requires_fresh_control(False, [], opposite_sign)
    assert d060._h2a_requires_lockstep_comparison(True, [], ())

    env.step(command)
    contact = env.last_obstacle_stage
    assert contact is not None and contact.obstacle_id == "A2"
    assert contact.push_out_magnitude_m == 2.220446049250313e-16
    assert env.last_step_contact.resolved_by == "obstacle"


def test_h2_exact_failure_context_keeps_case_geometry_and_outputs() -> None:
    options = {"body_position": (.75, .75), "station_center": (1.5, 1.5),
               "heading": .2, "battery_j": 2000., "body_temperature_c": 23.,
               "charger_termination_latched": False}
    actual, control = d060.D060Env(), d060.D058Env(d060.D058PhysicalConfig())
    actual.reset(options=options); control.reset(options=options)
    actual_observation, *_ = actual.step((0.0, 0.0))
    control_observation, *_ = control.step((0.0, 0.0))
    control.body.x = math.nextafter(control.body.x, math.inf)
    case = {"family": "ray", "ray_index": 12, "heading_index": 15,
            "sequence": "Q1", "command_index": 5, "reset": options}
    context = {**case, "command": (0.0, 0.0), "p0": (.75, .75),
               "p_full": (.75, .75), "theta_full": .2}

    message = d060._h2_comparison_failure_context(
        case, context, actual, control, actual_observation, control_observation,
        True, [{"field": "position", "actual": actual.body.position,
                "control": control.body.position}],
    )

    assert "H.2 exact comparison failed" in message
    assert "ray_index" in message and "command_index" in message
    assert "p_full" in message and "theta_full" in message
    assert "actual_observation_hex" in message and "control_observation_hex" in message
    assert "last_transition" in message and "mismatches" in message


def test_h4_step_kind_bound_uses_only_authorized_evaluator_allowance() -> None:
    p0 = (1.9885184987839886, 2.4938083338286465)
    p_full = (2.0175782308296943, 2.4938083338286465)
    d_max = d060.D045_WHEEL_RADIUS_METRES * D045_MAX_WHEEL_DELTA_RAD
    raw = d060._h4_step_kind_displacement(math.dist(p0, p_full), d_max)
    assert raw == {
        "measured_displacement_m": 0.029059732045705777,
        "analytic_bound_m": 0.029059732045705586,
        "excess_m": 1.9081958235744878e-16,
        "tau_eval_m": 4.263256414560601e-14,
        "passes": True,
    }
    allowance = 64 * (2.0**-52) * 3.0
    assert d060._h4_step_kind_displacement(d_max + allowance / 2, d_max)["passes"]
    assert not d060._h4_step_kind_displacement(d_max + 2 * allowance, d_max)["passes"]


def test_h2b_heading_restore_changes_only_exact_equivalent_heading() -> None:
    raw_heading = -0.052359877559829904
    control = d060.D058Env(d060.D058PhysicalConfig(room_side_m=3.0))
    control.reset(options={"body_position": (.75, .75), "station_center": (1.5, 1.5),
                           "heading": raw_heading, "battery_j": 2000.,
                           "body_temperature_c": 23., "charger_termination_latched": False})
    reset_heading = control.body.heading
    before = (control.body.position, control.battery_j, control.body_temperature_c,
              control.station_center, control._previous_wheel_delta, control._step_count)

    actual_reset, restored = d060._restore_h2b_heading(control, raw_heading)

    assert actual_reset == reset_heading and restored == raw_heading
    assert raw_heading % (2 * math.pi) == reset_heading % (2 * math.pi)
    assert (control.body.position, control.battery_j, control.body_temperature_c,
            control.station_center, control._previous_wheel_delta, control._step_count) == before
    with pytest.raises(AssertionError, match="changed heading beyond its 2π representation"):
        d060._restore_h2b_heading(control, raw_heading + 1e-6)


def test_protected_sources_match_authorized_base() -> None:
    root = Path(__file__).resolve().parents[1]
    for path in (
        "src/aweform/d045.py", "src/aweform/d049.py", "src/aweform/d050.py",
        "src/aweform/d052.py", "src/aweform/d053.py", "src/aweform/d054.py",
        "src/aweform/d055.py", "src/aweform/d056.py", "src/aweform/d057.py",
        "src/aweform/d058.py", "src/aweform/d059.py", "src/aweform/vis_d059.py",
        "src/aweform/development_visualizer.py", "src/aweform/body.py",
        "src/aweform/env.py", "src/aweform/exp001.py", "src/aweform/exp003.py",
        "src/aweform/exp003_seed_policy.py",
    ):
        current = (root / path).read_bytes()
        base = subprocess.run(["git", "show", f"{d060.BASE_SHA}:{path}"],
                              cwd=root, check=True, capture_output=True).stdout
        assert current == base, path
