import dataclasses
import inspect
from dataclasses import fields

import numpy as np
import pytest

from aweform import (
    Action,
    EXP001AController,
    EXP001BController,
    EXP001CController,
    EXP001DevelopmentConfig,
    EXP001Mode,
    ExternalObservation,
    InteroceptiveObservation,
    RandomStreams,
    StochasticPersistentExplorer,
    has_resource_contact,
    policy_rng_from_seed,
    seek_resource_action,
)


class FakePolicyRNG:
    def __init__(self, runs: list[int], random_values: list[float]) -> None:
        self.runs = iter(runs)
        self.random_values = iter(random_values)

    def geometric(self, probability: float) -> int:
        assert probability == pytest.approx(1.0 / 8.0)
        return next(self.runs)

    def random(self) -> float:
        return next(self.random_values)


def _config(
    *,
    contact: float = 0.8,
    explore: int = 3,
    charge: int = 2,
) -> EXP001DevelopmentConfig:
    return EXP001DevelopmentConfig(
        resource_contact_threshold=contact,
        blind_explore_duration=explore,
        blind_charge_duration=charge,
    )


def _external(
    left: float = 0.0,
    forward: float = 0.0,
    right: float = 0.0,
) -> ExternalObservation:
    return ExternalObservation(left, forward, right)


def _actions(seed: int, count: int = 256) -> list[Action]:
    explorer = StochasticPersistentExplorer(policy_rng_from_seed(seed))
    observation = _external(0.2, 0.7, 0.1)
    return [explorer.act(observation) for _ in range(count)]


def test_same_seed_reproduces_stochastic_exploration() -> None:
    assert _actions(101) == _actions(101)


def test_separate_policy_generators_from_same_master_seed_match() -> None:
    first = RandomStreams.from_seed(102)
    second = RandomStreams.from_seed(102)
    first_explorer = StochasticPersistentExplorer(first.policy)
    second_explorer = StochasticPersistentExplorer(second.policy)
    observation = _external()

    assert [first_explorer.act(observation) for _ in range(128)] == [
        second_explorer.act(observation) for _ in range(128)
    ]


def test_different_seeds_eventually_change_exploration_sequence() -> None:
    assert _actions(103) != _actions(104)


def test_geometric_runs_are_positive_and_turns_use_existing_actions() -> None:
    rng = FakePolicyRNG(
        runs=[1, 3, 2],
        random_values=[0.1, 0.1, 0.9, 0.1, 0.1, 0.1],
    )
    explorer = StochasticPersistentExplorer(rng)  # type: ignore[arg-type]
    actions = [explorer.act(_external()) for _ in range(8)]

    assert actions[:4] == [
        Action.MOVE_FORWARD,
        Action.TURN_LEFT,
        Action.MOVE_FORWARD,
        Action.MOVE_FORWARD,
    ]
    assert all(action in Action for action in actions)
    forward_runs: list[int] = []
    current_run = 0
    for action in actions:
        if action is Action.MOVE_FORWARD:
            current_run += 1
        elif current_run:
            forward_runs.append(current_run)
            current_run = 0
    if current_run:
        forward_runs.append(current_run)
    assert forward_runs
    assert all(run_length >= 1 for run_length in forward_runs)


def test_ninety_degree_reorientation_is_two_same_existing_turn_actions() -> None:
    rng = FakePolicyRNG(runs=[1, 1], random_values=[0.9, 0.9, 0.1, 0.1])
    explorer = StochasticPersistentExplorer(rng)  # type: ignore[arg-type]

    assert [explorer.act(_external()) for _ in range(4)] == [
        Action.MOVE_FORWARD,
        Action.TURN_RIGHT,
        Action.TURN_RIGHT,
        Action.MOVE_FORWARD,
    ]
    assert len(Action) == 4


def test_explorer_does_not_advance_environment_rng() -> None:
    actual = RandomStreams.from_seed(105)
    expected = RandomStreams.from_seed(105)
    explorer = StochasticPersistentExplorer(actual.policy)

    for _ in range(128):
        explorer.act(_external())

    np.testing.assert_array_equal(
        actual.environment.random(16),
        expected.environment.random(16),
    )


def test_exp001_boundary_has_external_only_and_interoceptive_types() -> None:
    assert {field.name for field in fields(ExternalObservation)} == {
        "left_resource",
        "forward_resource",
        "right_resource",
    }
    assert {field.name for field in fields(InteroceptiveObservation)} == {
        "energy",
        "external",
    }
    assert list(inspect.signature(EXP001AController.act).parameters) == [
        "self",
        "observation",
    ]
    assert list(inspect.signature(EXP001CController.act).parameters) == [
        "self",
        "observation",
    ]
    assert not hasattr(
        EXP001CController(policy_rng_from_seed(106), _config()),
        "energy",
    )


def test_a_and_c_accept_external_observation_b_accepts_actual_energy() -> None:
    config = _config()
    external = _external(0.1, 0.2, 0.3)
    a = EXP001AController(policy_rng_from_seed(107), config)
    b = EXP001BController(policy_rng_from_seed(107), config)
    c = EXP001CController(policy_rng_from_seed(107), config)

    assert a.act(external) in Action
    assert c.act(external) in Action
    assert b.act(InteroceptiveObservation(energy=0.9, external=external)) in Action
    with pytest.raises(ValueError):
        c.act(InteroceptiveObservation(energy=0.1, external=external))  # type: ignore[arg-type]


def test_c_actions_do_not_depend_on_evaluator_energy() -> None:
    config = _config(explore=2, charge=2)
    external = _external()
    first = EXP001CController(policy_rng_from_seed(108), config)
    second = EXP001CController(policy_rng_from_seed(108), config)
    evaluator_energies = [0.0, 0.35, 0.85, 1.0]

    first_actions = [first.act(external) for _ in evaluator_energies]
    second_actions = [second.act(external) for _ in evaluator_energies]

    assert first_actions == second_actions
    assert first.mode is second.mode
    assert first.mode_actions == second.mode_actions


def test_each_condition_uses_shared_explorer_configuration() -> None:
    config = _config()
    controllers: list[
        EXP001AController | EXP001BController | EXP001CController
    ] = [
        EXP001AController(policy_rng_from_seed(109), config),
        EXP001BController(policy_rng_from_seed(109), config),
        EXP001CController(policy_rng_from_seed(109), config),
    ]

    assert all(
        isinstance(controller.explorer, StochasticPersistentExplorer)
        for controller in controllers
    )
    assert [controller.explorer.hazard for controller in controllers] == [
        config.explorer_hazard
    ] * 3


def test_b_and_c_share_external_steering_contact_and_wait_charge_action() -> None:
    config = _config(contact=0.8, explore=1, charge=2)
    no_contact = _external(left=0.7, forward=0.1, right=0.2)
    contact = _external(left=0.8)
    b = EXP001BController(policy_rng_from_seed(110), config)
    c = EXP001CController(policy_rng_from_seed(110), config)

    assert seek_resource_action(no_contact) is Action.TURN_LEFT
    assert b.act(InteroceptiveObservation(0.2, no_contact)) is Action.TURN_LEFT
    c.act(no_contact)
    assert c.act(contact) is Action.WAIT
    assert b.act(InteroceptiveObservation(0.2, contact)) is Action.WAIT
    assert b.mode.value == EXP001Mode.CHARGE.value
    assert c.mode is EXP001Mode.CHARGE
    assert b.act(InteroceptiveObservation(0.2, no_contact)) is Action.WAIT
    assert c.act(no_contact) is Action.WAIT


def test_b_state_machine_uses_energy_for_transitions_only() -> None:
    config = _config(contact=0.9)
    no_contact = _external(right=0.2)
    contact = _external(forward=0.9)
    b = EXP001BController(policy_rng_from_seed(111), config)

    b.act(InteroceptiveObservation(0.34, no_contact))
    assert b.mode is EXP001Mode.SEEK_RESOURCE
    b.act(InteroceptiveObservation(0.34, contact))
    assert b.mode.value == EXP001Mode.CHARGE.value
    assert b.act(InteroceptiveObservation(0.84, no_contact)) is Action.WAIT
    assert b.mode.value == EXP001Mode.CHARGE.value
    b.act(InteroceptiveObservation(0.86, no_contact))
    assert b.mode.value == EXP001Mode.EXPLORE.value


def test_c_timers_count_forward_turn_and_wait_actions() -> None:
    config = _config(contact=1.0, explore=2, charge=2)
    no_contact = _external()
    contact = _external(left=1.0)
    rng = FakePolicyRNG(
        runs=[1, 1],
        random_values=[0.1, 0.1, 0.1, 0.1],
    )
    c = EXP001CController(rng, config)  # type: ignore[arg-type]

    c.act(no_contact)
    assert c.act(no_contact) is Action.TURN_LEFT
    assert c.mode is EXP001Mode.EXPLORE
    assert c.mode_actions == 2
    assert c.act(no_contact) is Action.TURN_LEFT
    assert c.mode.value == EXP001Mode.SEEK_RESOURCE.value
    assert c.act(contact) is Action.WAIT
    assert c.mode.value == EXP001Mode.CHARGE.value
    assert c.mode_actions == 1
    assert c.act(no_contact) is Action.WAIT
    assert c.mode.value == EXP001Mode.CHARGE.value
    assert c.act(no_contact) in (
        Action.MOVE_FORWARD,
        Action.TURN_LEFT,
        Action.TURN_RIGHT,
    )
    assert c.mode is EXP001Mode.EXPLORE


def test_resource_contact_is_explicit_shared_external_criterion() -> None:
    observation = _external(left=0.2, forward=0.7, right=0.3)
    assert has_resource_contact(observation, 0.7)
    assert not has_resource_contact(observation, 0.71)


def test_timer_and_contact_parameters_have_no_production_defaults() -> None:
    config_fields = {field.name: field for field in fields(EXP001DevelopmentConfig)}
    assert config_fields["resource_contact_threshold"].default is dataclasses.MISSING
    assert config_fields["blind_explore_duration"].default is dataclasses.MISSING
    assert config_fields["blind_charge_duration"].default is dataclasses.MISSING
    with pytest.raises(TypeError):
        EXP001DevelopmentConfig()  # type: ignore[call-arg]


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "resource_contact_threshold": 0.5,
            "blind_explore_duration": 0,
            "blind_charge_duration": 1,
        },
        {
            "resource_contact_threshold": 0.5,
            "blind_explore_duration": 1,
            "blind_charge_duration": 0,
        },
        {
            "resource_contact_threshold": 0.5,
            "blind_explore_duration": 1,
            "blind_charge_duration": 1,
            "explorer_hazard": 0.0,
        },
        {
            "resource_contact_threshold": 0.5,
            "blind_explore_duration": 1,
            "blind_charge_duration": 1,
            "enter_seek": 0.9,
            "recover": 0.8,
        },
    ],
)
def test_development_parameters_are_validated(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        EXP001DevelopmentConfig(**kwargs)  # type: ignore[arg-type]
