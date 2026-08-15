import pytest

from aweform import EnergyConfig, EnergyState, advance_energy


def test_basal_cost_reduces_energy() -> None:
    config = EnergyConfig(maximum_energy=10.0, basal_cost=1.5)

    assert advance_energy(6.0, harvested_energy=0.0, config=config) == EnergyState(
        energy=4.5,
        viable=True,
    )


def test_action_cost_and_resource_gain_are_accounted_for() -> None:
    config = EnergyConfig(maximum_energy=10.0, basal_cost=1.0)

    result = advance_energy(
        4.0,
        harvested_energy=3.0,
        action_cost=0.5,
        config=config,
    )

    assert result == EnergyState(energy=5.5, viable=True)


def test_energy_is_clamped_at_the_upper_bound() -> None:
    config = EnergyConfig(maximum_energy=10.0, basal_cost=0.0)

    assert advance_energy(9.0, harvested_energy=4.0, config=config).energy == 10.0


def test_reaching_failure_boundary_makes_state_non_viable() -> None:
    config = EnergyConfig(maximum_energy=10.0, basal_cost=1.0)

    exact = advance_energy(1.0, harvested_energy=0.0, config=config)
    above = advance_energy(1.1, harvested_energy=0.0, config=config)

    assert exact == EnergyState(energy=0.0, viable=False)
    assert above.energy == pytest.approx(0.1)
    assert above.viable is True


def test_invalid_energy_configuration_and_inputs_are_rejected() -> None:
    with pytest.raises(ValueError):
        EnergyConfig(maximum_energy=0.0, basal_cost=1.0)
    with pytest.raises(ValueError):
        EnergyConfig(maximum_energy=10.0, basal_cost=-1.0)

    config = EnergyConfig(maximum_energy=10.0, basal_cost=1.0)
    with pytest.raises(ValueError):
        advance_energy(-0.1, harvested_energy=0.0, config=config)
    with pytest.raises(ValueError):
        advance_energy(1.0, harvested_energy=-0.1, config=config)
    with pytest.raises(ValueError):
        advance_energy(1.0, harvested_energy=0.0, action_cost=-0.1, config=config)
