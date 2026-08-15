import numpy as np
import pytest

from aweform import (
    Action,
    ControllerMode,
    EnergyBlindController,
    HomeostaticConfig,
    HomeostaticController,
    PersistentExplorationController,
)


def _observation(
    energy: float = 0.5,
    left: float = 0.0,
    forward: float = 0.0,
    right: float = 0.0,
) -> tuple[float, float, float, float]:
    return (energy, left, forward, right)


def test_persistent_exploration_repeats_forward_then_left() -> None:
    controller = PersistentExplorationController(exploration_steps=2)

    actions = [controller.act(_observation()) for _ in range(6)]

    assert actions == [
        Action.MOVE_FORWARD,
        Action.MOVE_FORWARD,
        Action.TURN_LEFT,
        Action.MOVE_FORWARD,
        Action.MOVE_FORWARD,
        Action.TURN_LEFT,
    ]


def test_persistent_exploration_reset_restores_initial_phase() -> None:
    controller = PersistentExplorationController(exploration_steps=2)
    controller.act(_observation())
    controller.act(_observation())
    controller.act(_observation())

    controller.reset()

    assert controller.act(_observation()) is Action.MOVE_FORWARD


def test_persistent_exploration_ignores_valid_observation_contents() -> None:
    controller = PersistentExplorationController(exploration_steps=2)
    first_actions = [
        controller.act(_observation(energy=0.1, left=1.0, forward=0.0, right=0.0))
        for _ in range(3)
    ]
    controller.reset()
    second_actions = [
        controller.act(_observation(energy=0.9, left=0.0, forward=0.0, right=1.0))
        for _ in range(3)
    ]

    assert first_actions == second_actions


def test_hysteresis_starts_exploring_and_prevents_rapid_switching() -> None:
    controller = HomeostaticController(HomeostaticConfig(exploration_steps=2))

    assert controller.mode is ControllerMode.EXPLORE
    controller.act(_observation(energy=0.5))
    assert controller.mode is ControllerMode.EXPLORE

    controller.act(_observation(energy=0.34, left=1.0))
    assert controller.mode is ControllerMode.SEEK_RESOURCE

    controller.act(_observation(energy=0.5, right=1.0))
    assert controller.mode is ControllerMode.SEEK_RESOURCE

    controller.act(_observation(energy=0.66))
    assert controller.mode is ControllerMode.EXPLORE


def test_hysteresis_reset_restores_mode_and_exploration_phase() -> None:
    controller = HomeostaticController(HomeostaticConfig(exploration_steps=2))
    controller.act(_observation(energy=0.5))
    controller.act(_observation(energy=0.34))
    controller.act(_observation(energy=0.66))

    controller.reset()

    assert controller.mode is ControllerMode.EXPLORE
    assert controller.act(_observation(energy=0.5)) is Action.MOVE_FORWARD


@pytest.mark.parametrize(
    ("left", "forward", "right", "expected"),
    [
        (0.2, 0.9, 0.4, Action.MOVE_FORWARD),
        (0.9, 0.2, 0.4, Action.TURN_LEFT),
        (0.2, 0.4, 0.9, Action.TURN_RIGHT),
        (0.7, 0.7, 0.2, Action.MOVE_FORWARD),
    ],
)
def test_resource_seeking_uses_local_signals_and_forward_tie_breaking(
    left: float,
    forward: float,
    right: float,
    expected: Action,
) -> None:
    controller = HomeostaticController()

    action = controller.act(
        _observation(energy=0.1, left=left, forward=forward, right=right)
    )

    assert controller.mode is ControllerMode.SEEK_RESOURCE
    assert action is expected


def test_energy_blind_controller_uses_fixed_mask_for_identical_external_input() -> None:
    controller = EnergyBlindController(masked_energy=0.2)
    external_signals = (0.1, 0.2, 0.9, 0.2)

    first_action = controller.act(external_signals)
    first_mode = controller.mode
    second_action = controller.act((0.9, *external_signals[1:]))

    assert (first_action, first_mode) == (
        Action.MOVE_FORWARD,
        ControllerMode.SEEK_RESOURCE,
    )
    assert (second_action, controller.mode) == (
        Action.MOVE_FORWARD,
        ControllerMode.SEEK_RESOURCE,
    )


def test_matching_actual_and_masked_energy_matches_actions_and_modes() -> None:
    config = HomeostaticConfig(exploration_steps=2)
    informative = HomeostaticController(config)
    energy_blind = EnergyBlindController(masked_energy=0.5, config=config)
    observations = [
        _observation(0.5, 0.1, 0.8, 0.1),
        _observation(0.5, 0.1, 0.8, 0.1),
        _observation(0.5, 0.8, 0.1, 0.1),
    ]

    for observation in observations:
        assert informative.act(observation) is energy_blind.act(observation)
        assert informative.mode is energy_blind.mode


def test_energy_substitution_can_diverge_at_a_mode_threshold() -> None:
    informative = HomeostaticController()
    energy_blind = EnergyBlindController(masked_energy=0.5)
    observation = _observation(energy=0.3, left=0.9, forward=0.1, right=0.1)

    informative_action = informative.act(observation)
    blind_action = energy_blind.act(observation)

    assert informative.mode is ControllerMode.SEEK_RESOURCE
    assert energy_blind.mode is ControllerMode.EXPLORE
    assert informative_action is Action.TURN_LEFT
    assert blind_action is Action.MOVE_FORWARD


@pytest.mark.parametrize(
    "observation",
    [
        (0.5, 0.5, 0.5),
        np.zeros((2, 2)),
        (0.5, 0.5, 0.5, np.nan),
        (0.5, -0.1, 0.5, 0.5),
        (0.5, 0.5, 1.1, 0.5),
    ],
)
def test_controllers_reject_malformed_observations(observation: object) -> None:
    controller = PersistentExplorationController()

    with pytest.raises(ValueError):
        controller.act(observation)  # type: ignore[arg-type]


def test_controller_api_uses_only_the_four_value_observation() -> None:
    controller = HomeostaticController()

    assert (
        controller.act(np.asarray(_observation(), dtype=np.float32))
        is Action.MOVE_FORWARD
    )


@pytest.mark.parametrize(
    ("enter_seek", "recover"),
    [(-0.1, 0.5), (0.5, 0.5), (0.8, 0.7), (0.5, 1.1)],
)
def test_homeostatic_thresholds_require_ordered_normalized_values(
    enter_seek: float, recover: float
) -> None:
    with pytest.raises(ValueError):
        HomeostaticConfig(enter_seek=enter_seek, recover=recover)


@pytest.mark.parametrize("masked_energy", [-0.1, 1.1, float("nan")])
def test_energy_blind_mask_must_be_normalized_and_finite(masked_energy: float) -> None:
    with pytest.raises(ValueError):
        EnergyBlindController(masked_energy=masked_energy)
