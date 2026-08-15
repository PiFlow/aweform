import math

import pytest

from aweform import Body, ResourceField, sample_directional_resources


def test_source_ahead_is_stronger_than_side_signals() -> None:
    body = Body(x=0.2, y=0.5, heading=0.0, energy=1.0)
    field = ResourceField(
        world_min=(0.0, 0.0),
        world_max=(1.0, 1.0),
        source_positions=((0.4, 0.5),),
        length_scale=0.08,
    )

    signals = sample_directional_resources(
        body,
        field,
        probe_distance=0.2,
        sensor_angle=math.pi / 2,
    )

    assert signals.forward > signals.left
    assert signals.forward > signals.right


def test_left_and_right_orientation_is_relative_to_heading() -> None:
    body = Body(x=0.5, y=0.5, heading=math.pi / 2, energy=1.0)
    field = ResourceField(
        world_min=(0.0, 0.0),
        world_max=(1.0, 1.0),
        source_positions=((0.4, 0.5),),
        length_scale=0.08,
    )

    signals = sample_directional_resources(
        body,
        field,
        probe_distance=0.1,
        sensor_angle=math.pi / 2,
    )

    assert signals.left > signals.right


def test_out_of_bounds_probes_return_zero() -> None:
    body = Body(x=0.02, y=0.5, heading=math.pi, energy=1.0)
    field = ResourceField(source_positions=((0.0, 0.5),), length_scale=0.1)

    signals = sample_directional_resources(
        body,
        field,
        probe_distance=0.1,
        sensor_angle=math.pi / 2,
    )

    assert signals.forward == 0.0
    assert signals.left > 0.0


def test_directional_signals_do_not_contain_coordinates() -> None:
    signals = sample_directional_resources(
        Body(x=0.5, y=0.5, heading=0.0, energy=1.0),
        ResourceField(),
        probe_distance=0.1,
        sensor_angle=math.pi / 4,
    )

    assert signals.as_tuple() == pytest.approx(
        (signals.left, signals.forward, signals.right)
    )


def test_directional_sensing_uses_multi_source_max_field() -> None:
    body = Body(x=0.5, y=0.5, heading=0.0, energy=1.0)
    field = ResourceField(
        source_positions=((0.5, 0.7), (0.7, 0.5)),
        length_scale=0.05,
    )

    signals = sample_directional_resources(
        body,
        field,
        probe_distance=0.2,
        sensor_angle=math.pi / 2,
    )

    assert signals.left == pytest.approx(1.0)
    assert signals.forward == pytest.approx(1.0)
    assert signals.right < signals.left
