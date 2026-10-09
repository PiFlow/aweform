from __future__ import annotations

import math

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
