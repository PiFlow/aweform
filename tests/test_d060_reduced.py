from __future__ import annotations

import math
from collections import Counter

import pytest

from aweform import d060, d060_oracle, d060_reduced


def test_protocol_identity_and_frozen_selection_cardinalities() -> None:
    assert d060_reduced.PROTOCOL_ID == "D060-REDUCED-v1"
    assert len(d060_reduced.RAY_IDENTITIES) == 19
    assert len(set(d060_reduced.RAY_IDENTITIES)) == 19
    sequences = dict(d060_reduced._commands())
    assert (
        sum(len(sequences[name]) for _, _, name in d060_reduced.RAY_IDENTITIES) == 204
    )
    assert len(d060_oracle._feature_rays()) == 76
    assert len(d060_reduced._headings()) == 32
    assert d060_reduced.H2C_HEADINGS == (0, 1, 24, 28)
    m = d060.D045_MAX_WHEEL_DELTA_RAD
    expected_u10 = tuple(
        (left, right)
        for left in (-m, 0.0, m)
        for right in (-m, 0.0, m)
        if (left, right) != (0.0, 0.0)
    ) + ((-0.565040862351, 0.645771823238), (0.0, 0.0))
    assert d060_reduced._u10_commands() == expected_u10
    assert len(d060_reduced._u10_commands()) == 10


def test_rotated_corner_reconstruction_is_four_corners_at_exact_yaw() -> None:
    position = (1.25, 2.0)
    yaw = math.pi / 2
    corners = d060_reduced._corners(position, yaw)
    assert len(corners) == 4
    expected = (
        (position[0] + d060.C, position[1] - d060.A),
        (position[0] + d060.C, position[1] + d060.A),
        (position[0] - d060.C, position[1] + d060.A),
        (position[0] - d060.C, position[1] - d060.A),
    )
    assert all(
        actual == pytest.approx(want, abs=1e-15)
        for actual, want in zip(corners, expected, strict=True)
    )


def test_room_allowance_is_inherited_verification_only_value() -> None:
    assert d060_reduced.TAU_ROOM == 4.263256414560601e-14


def test_low_energy_h2c_value_and_complete_reset_options_are_frozen() -> None:
    options = d060_reduced._options((0.75, 2.25), 1.0, d060_reduced.H2C_LOW_BATTERY_J)
    assert options == {
        "body_position": (0.75, 2.25),
        "station_center": (1.5, 1.5),
        "heading": 1.0,
        "battery_j": 1065.6,
        "body_temperature_c": 23.0,
        "charger_termination_latched": False,
    }


def test_sign_disagreement_records_link_both_directions_to_executed_witness() -> None:
    rays = d060_oracle._feature_rays()
    headings = d060_reduced._headings()
    q1 = dict(d060_reduced._commands())["Q1"]
    records = []
    expected_directions = (
        (12, 15, "penetrating", "clear"),
        (22, 21, "clear", "penetrating"),
    )
    for (
        ray_index,
        heading_index,
        expected_production,
        expected_oracle,
    ) in expected_directions:
        obstacle_index, anchor, direction, feature_class = rays[ray_index]
        obstacle = d060.FROZEN_LAYOUT[obstacle_index]
        radius = obstacle[3] + d060.R_H + 0.005
        position = (
            anchor[0] + radius * direction[0],
            anchor[1] + radius * direction[1],
        )
        heading = headings[heading_index]
        actual = d060.D060Env()
        actual.reset(options=d060_reduced._options(position, heading))
        for command_index, command in enumerate(q1):
            assert actual.body is not None
            p_full, theta_full = d060_reduced.integrate_differential_drive(
                actual.body.position,
                actual.body.heading,
                *command,
                track_width_m=d060.D045_WHEEL_TRACK_WIDTH_METRES,
                wheel_radius_m=d060.D045_WHEEL_RADIUS_METRES,
            )
            production_gaps = tuple(
                d060._gap(p_full, theta_full, item) for item in d060.FROZEN_LAYOUT
            )
            oracle_gaps = tuple(
                d060_oracle.workspace_gap(p_full, theta_full, item)
                for item in d060_oracle.ORACLE_LAYOUT
            )
            actual.step(command)
            if command_index != 5:
                continue
            disagreements = d060._h2_boundary_sign_disagreements(
                production_gaps, oracle_gaps
            )
            match = next(
                item
                for item in disagreements
                if ("penetrating" if item[1] < 0.0 else "clear")
                == expected_production
                and ("penetrating" if item[2] < 0.0 else "clear") == expected_oracle
            )
            case = {
                "family": "ray",
                "ray_index": ray_index,
                "heading_index": heading_index,
                "sequence": "Q1",
                "command_index": command_index,
                "feature_class": feature_class,
            }
            assert actual.last_step_contact is not None
            assert actual.last_transition is not None
            assert actual.body is not None
            records.append(
                (
                    d060_reduced._sign_case_record(
                        env=actual,
                        case=case,
                        command=command,
                        obstacle=d060.FROZEN_LAYOUT[match[0]][0],
                        production_gap=match[1],
                        oracle_gap=match[2],
                    ),
                    actual.last_step_contact,
                    actual.last_transition,
                    actual.last_obstacle_stage,
                    actual.body.heading,
                )
            )
    assert [
        (record["production_classification"], record["oracle_classification"])
        for record, _, _, _, _ in records
    ] == [("penetrating", "clear"), ("clear", "penetrating")]
    for record, step, transition, contact, executed_heading in records:
        witness = record["execution_witness"]
        assert witness["case"] == record["case"]
        assert witness["command"] == record["command"]
        assert witness["resolved_by"] == step.resolved_by
        assert witness["obstacle_id"] == (contact.obstacle_id if contact else None)
        assert witness["p0"] == transition.position_before
        assert witness["theta0"] == transition.heading_before
        assert witness["p_full"] == step.unconstrained_endpoint
        assert witness["theta_full"] == transition.heading_after
        assert witness["p_exec"] == step.executed_endpoint
        assert witness["theta_exec"] == executed_heading
        assert witness["last_step_contact"]["resolved_by"] == step.resolved_by
        assert (
            witness["last_step_contact"]["unconstrained_endpoint"]
            == step.unconstrained_endpoint
        )
        assert (
            witness["last_step_contact"]["executed_endpoint"]
            == step.executed_endpoint
        )
        assert witness["removed_displacement"] == step.removed_displacement
        assert witness["removed_displacement_magnitude_m"] == (
            step.removed_displacement_magnitude_m
        )
        if contact is not None:
            assert witness["obstacle_contact"]["obstacle_id"] == contact.obstacle_id


def test_exact_h2_mismatch_retains_reset_pre_post_and_observation_context() -> None:
    options = d060_reduced._options((0.75, 0.75), 0.25, 1065.6)
    actual, control = d060.D060Env(), d060_reduced.D058Env(
        d060_reduced.D058PhysicalConfig(3.0)
    )
    actual.reset(options=options)
    control.reset(options=options)
    case = {
        "family": "h2c-single",
        "label": "low-energy:(0.75,0.75)",
        "heading_index": 1,
        "command_index": 2,
    }
    command = (d060.D045_MAX_WHEEL_DELTA_RAD, d060.D045_MAX_WHEEL_DELTA_RAD)
    context = d060_reduced._comparison_context(
        case, command, options, actual, control
    )
    observation_a = actual.step(command)[0]
    observation_b = control.step((-command[0], command[1]))[0]
    with pytest.raises(AssertionError) as failure:
        d060_reduced._compare(
            actual,
            control,
            observation_a,
            observation_b,
            False,
            case,
            context,
            Counter(),
        )
    message = str(failure.value)
    for evidence_key in (
        "reset_options",
        "pre_step_states",
        "actual_state",
        "control_state",
        "actual_observation_hex",
        "control_observation_hex",
        "mismatches",
        "compared_fields",
        "ignore_step_index",
        "command_index",
    ):
        assert evidence_key in message
    assert "1065.6" in message
    assert "low-energy:(0.75,0.75)" in message


def test_successful_h2_comparison_counts_direct_d058_reconstruction() -> None:
    options = d060_reduced._options((0.75, 0.75), 0.0)
    actual, control = d060.D060Env(), d060_reduced.D058Env(
        d060_reduced.D058PhysicalConfig(3.0)
    )
    actual.reset(options=options)
    control.reset(options=options)
    case = {"family": "ray", "ray_index": 0, "sequence": "Q1", "command_index": 0}
    command = (0.0, 0.0)
    context = d060_reduced._comparison_context(
        case, command, options, actual, control
    )
    observation_a = actual.step(command)[0]
    observation_b = control.step(command)[0]
    counters: Counter[str] = Counter()
    d060_reduced._compare(
        actual,
        control,
        observation_a,
        observation_b,
        False,
        case,
        context,
        counters,
    )
    assert counters["d058_reconstruction_checks"] == 1
