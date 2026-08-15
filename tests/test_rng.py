import numpy as np

from aweform import RandomStreams


def test_same_master_seed_reproduces_both_streams() -> None:
    first = RandomStreams.from_seed(1001)
    second = RandomStreams.from_seed(1001)

    np.testing.assert_array_equal(
        first.environment.integers(0, 10_000, size=8),
        second.environment.integers(0, 10_000, size=8),
    )
    np.testing.assert_array_equal(
        first.policy.random(8),
        second.policy.random(8),
    )


def test_different_master_seeds_change_derived_streams() -> None:
    first = RandomStreams.from_seed(1001)
    second = RandomStreams.from_seed(1002)

    assert not np.array_equal(
        first.environment.integers(0, 10_000, size=8),
        second.environment.integers(0, 10_000, size=8),
    )


def test_advancing_environment_does_not_advance_policy() -> None:
    streams = RandomStreams.from_seed(1003)
    expected = RandomStreams.from_seed(1003)

    streams.environment.random(32)

    np.testing.assert_array_equal(
        streams.policy.random(8),
        expected.policy.random(8),
    )
