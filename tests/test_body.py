import math

import pytest

from aweform import Body


def test_turning_wraps_and_moves_forward() -> None:
    body = Body(x=0.5, y=0.5, heading=0.0, energy=1.0)

    body.turn(-math.pi / 2)
    assert body.heading == pytest.approx(3 * math.pi / 2)
    body.turn(math.pi / 2)
    assert body.heading == pytest.approx(0.0)
    body.move_forward(
        0.2,
        world_min=(0.0, 0.0),
        world_max=(1.0, 1.0),
    )

    assert body.position == pytest.approx((0.7, 0.5))


def test_forward_movement_is_clamped_to_world_bounds() -> None:
    body = Body(x=0.95, y=0.5, heading=0.0, energy=1.0)

    body.move_forward(
        0.2,
        world_min=(0.0, 0.0),
        world_max=(1.0, 1.0),
    )

    assert body.position == (1.0, 0.5)
