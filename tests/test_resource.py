import numpy as np
import pytest

from aweform import RandomStreams, ResourceField


def test_resource_is_strongest_near_source_and_smoothly_decays() -> None:
    field = ResourceField(
        world_min=(0.0, 0.0),
        world_max=(1.0, 1.0),
        source_positions=((0.5, 0.5),),
        peak_intensity=2.0,
        length_scale=0.2,
    )

    at_source = field.intensity((0.5, 0.5))
    nearby = field.intensity((0.6, 0.5))
    far = field.intensity((1.0, 1.0))

    assert at_source == pytest.approx(field.peak_intensity)
    assert at_source > nearby > far >= 0.0


def test_multiple_sources_use_the_strongest_local_contribution() -> None:
    field = ResourceField(
        world_min=(0.0, 0.0),
        world_max=(1.0, 1.0),
        source_positions=((0.35, 0.5), (0.65, 0.5)),
        peak_intensity=2.0,
        length_scale=0.1,
    )

    midpoint = field.intensity((0.5, 0.5))
    one_source_contribution = 2.0 * np.exp(-0.5 * (0.15 / 0.1) ** 2)

    assert field.source_positions == ((0.35, 0.5), (0.65, 0.5))
    assert field.intensity((0.35, 0.5)) == pytest.approx(2.0)
    assert field.intensity((0.65, 0.5)) == pytest.approx(2.0)
    assert midpoint == pytest.approx(one_source_contribution)
    assert midpoint < 2.0 * one_source_contribution
    assert 0.0 <= midpoint <= field.peak_intensity


def test_seeded_source_generation_is_reproducible_and_stream_owned() -> None:
    first = RandomStreams.from_seed(2001)
    second = RandomStreams.from_seed(2001)
    third = RandomStreams.from_seed(2002)

    first_field = ResourceField.from_rng(first.environment)
    second_field = ResourceField.from_rng(second.environment)
    third_field = ResourceField.from_rng(third.environment)

    assert first_field.source_positions == second_field.source_positions
    assert first_field.source_positions != third_field.source_positions

    multi_source = ResourceField.from_rng(
        RandomStreams.from_seed(2001).environment,
        resource_count=3,
    )
    assert len(multi_source.source_positions) == 3
    assert all(
        all(0.0 <= coordinate <= 1.0 for coordinate in position)
        for position in multi_source.source_positions
    )


def test_boundaries_are_valid_and_out_of_bounds_positions_are_rejected() -> None:
    field = ResourceField(
        world_min=(-2.0, -1.0),
        world_max=(3.0, 4.0),
        source_positions=((0.0, 1.0),),
    )

    assert field.intensity((-2.0, 4.0)) >= 0.0
    assert field.intensity(np.array([3.0, -1.0])) >= 0.0
    with pytest.raises(ValueError):
        field.intensity((-2.1, 0.0))
    with pytest.raises(ValueError):
        field.intensity((0.0, 4.1))


def test_invalid_field_configuration_is_rejected() -> None:
    with pytest.raises(ValueError):
        ResourceField(world_min=(0.0, 0.0), world_max=(0.0, 1.0))
    with pytest.raises(ValueError):
        ResourceField(source_positions=((1.1, 0.5),))
    with pytest.raises(ValueError):
        ResourceField(source_positions=())
    with pytest.raises(ValueError):
        ResourceField(source_positions=((float("nan"), 0.5),))
    with pytest.raises(ValueError):
        ResourceField(length_scale=0.0)


@pytest.mark.parametrize("resource_count", [True, 0, -1, 1.5, "3"])
def test_invalid_resource_count_is_rejected(resource_count: object) -> None:
    with pytest.raises(ValueError):
        ResourceField.from_rng(
            RandomStreams.from_seed(2001).environment,
            resource_count=resource_count,  # type: ignore[arg-type]
        )
