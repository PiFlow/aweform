from __future__ import annotations

import pytest

import aweform.exp001_calibration as calibration_module
import aweform.exp001_seed_policy as seed_policy
from aweform import validate_exp001_development_seeds


def test_canonical_exp001_reservations_are_shared_with_calibration() -> None:
    assert seed_policy.FORMAL_CALIBRATION_SEEDS == tuple(range(20001, 20201))
    assert seed_policy.CONFIRMATORY_SEEDS == tuple(range(30001, 31001))
    assert (
        calibration_module.FORMAL_CALIBRATION_SEEDS
        is seed_policy.FORMAL_CALIBRATION_SEEDS
    )
    assert calibration_module.CONFIRMATORY_SEEDS is seed_policy.CONFIRMATORY_SEEDS


@pytest.mark.parametrize(
    "seeds",
    [
        [seed_policy.FORMAL_CALIBRATION_SEEDS[0]],
        [seed_policy.FORMAL_CALIBRATION_SEEDS[-1]],
        [seed_policy.CONFIRMATORY_SEEDS[0]],
        [seed_policy.CONFIRMATORY_SEEDS[-1]],
        [18001, seed_policy.FORMAL_CALIBRATION_SEEDS[0]],
        [18001, seed_policy.CONFIRMATORY_SEEDS[0]],
    ],
)
def test_development_validator_rejects_any_reserved_overlap(
    seeds: list[int],
) -> None:
    with pytest.raises(ValueError, match="reserved"):
        validate_exp001_development_seeds(seeds)


def test_development_validator_returns_all_non_reserved_seeds() -> None:
    assert validate_exp001_development_seeds([18001, 18002]) == (18001, 18002)
