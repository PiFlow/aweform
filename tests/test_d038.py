"""Focused D-038 protocol and evaluator-boundary tests."""

from __future__ import annotations

import math
from typing import cast

import pytest

from aweform import d026, d027, d029, d035b, d038
from aweform.env import Action
from aweform.exp003 import BeaconObservation


def _environment() -> d026.D026Env:
    environment = d026.D026Env()
    observation, info = environment.reset(
        options={
            "body_position": (0.40, 0.40),
            "station_center": (0.50, 0.50),
            "heading": 0.37,
            "battery_j": 2000.0,
            "body_temperature_c": 23.0,
            "charger_termination_latched": False,
        }
    )
    assert observation.shape == (6,)
    assert info == {}
    return environment


def _observation() -> d027.D027Observation:
    return d027.D027Observation(
        energy=0.5,
        beacon=BeaconObservation(
            left=0.8, forward=0.2, right=0.1, charging_contact=False
        ),
        thermal=0.3,
    )


def test_protocol_guards_and_exact_treatment_matrix() -> None:
    assert d038.D038_DEFAULT_DEVELOPMENT_SEEDS == tuple(range(18468, 18488))
    assert d038.D038_BRANCH_HORIZON == 4096
    assert d038.D038_TREATMENTS == (
        "T0_BASELINE_B",
        "T1_FINE_5_FIXED",
        "T2_FINE_5_INTERP",
        "T3_FULL_COMBINED_5",
        "T4_FULL_COMBINED_2",
    )
    with pytest.raises(ValueError, match="exactly"):
        d038._validate_seeds((18468, 18469))
    with pytest.raises(ValueError, match="reserved"):
        d038._validate_seed(50001)
    with pytest.raises(ValueError, match="70,000"):
        d038.run_d038_audit(seeds=d038.D038_DEFAULT_DEVELOPMENT_SEEDS, horizon=1)


def test_lfr_formula_and_zero_vector_are_exact() -> None:
    vector = d035b._lfr_vector(_observation())
    assert vector.x == pytest.approx(0.2 + math.cos(math.pi / 4) * 0.9)
    assert vector.y == pytest.approx(math.sin(math.pi / 4) * 0.7)
    assert vector.theta_hat == pytest.approx(math.atan2(vector.y, vector.x))
    zero = d035b._lfr_vector(
        d027.D027Observation(
            energy=0.5,
            beacon=BeaconObservation(
                left=0.0, forward=0.0, right=0.0, charging_contact=False
            ),
            thermal=0.3,
        )
    )
    assert zero.zero_vector is True
    assert zero.theta_hat == 0.0
    shallow = d027.D027Observation(
        energy=0.5,
        beacon=BeaconObservation(
            left=1.0, forward=0.99, right=1.0, charging_contact=False
        ),
        thermal=0.3,
    )
    assert d038._lfr_magnitude(shallow, 5.0, "LFR_INTERP") < math.pi / 36


def test_five_and_two_degree_turns_preserve_action_identity_and_bookkeeping() -> None:
    five = _environment()
    _, reward, terminated, truncated, info = d035b._step_with_turn_angle(
        five, Action.TURN_LEFT, math.pi / 36
    )
    assert reward == 0.0
    assert info == {}
    assert not terminated and not truncated
    assert five.body is not None
    assert five.body.heading == pytest.approx(0.37 + math.pi / 36)
    assert five.last_transition is not None
    assert five.last_transition.action is Action.TURN_LEFT

    two = _environment()
    d035b._step_with_turn_angle(two, Action.TURN_LEFT, math.pi / 90)
    assert two.body is not None
    assert two.body.heading == pytest.approx(0.37 + math.pi / 90)
    assert [action.name for action in Action] == [
        "WAIT",
        "TURN_LEFT",
        "TURN_RIGHT",
        "MOVE_FORWARD",
    ]


def test_reverse_strict_better_rule_rejects_ties_and_has_no_action_identity() -> None:
    labels = {action.name: 1.0 for action in Action}
    labels[d038.d035c.D035C_REVERSE_LABEL] = 1.0
    selected, reverse, canonical, tie = d038._reverse_selection(labels)
    assert selected is False
    assert reverse == canonical == 1.0
    assert tie is True
    labels[d038.d035c.D035C_REVERSE_LABEL] = 1.01
    selected, _, _, tie = d038._reverse_selection(labels)
    assert selected is True
    assert tie is False
    assert d038.d035c.D035C_REVERSE_LABEL not in [action.name for action in Action]


def test_candidate_evaluation_is_read_only_and_order_invariant() -> None:
    environment = _environment()
    current = d029._next_visible(environment._observation().as_array())
    labels = tuple(action.name for action in Action) + (d038.d035c.D035C_REVERSE_LABEL,)
    before = d029._environment_state(environment)
    first, first_check = d038._candidate_outcomes(environment, current, 5.0, labels)
    second, second_check = d038._candidate_outcomes(
        environment, current, 5.0, tuple(reversed(labels))
    )
    assert first_check["source_environment_unchanged"] is True
    assert second_check["source_environment_unchanged"] is True
    assert d029._environment_state(environment) == before
    assert all(
        d038.d035c._candidate_identity(first[label])
        == d038.d035c._candidate_identity(second[label])
        for label in labels
    )


def test_reverse_physical_operation_preserves_reward_info_and_learner_boundary() -> (
    None
):
    environment = _environment()
    before = d029._environment_state(environment)
    _, reward, terminated, truncated, info = d038.d035c._reverse_step(environment)
    assert reward == 0.0
    assert info == {}
    assert isinstance(terminated, bool)
    assert isinstance(truncated, bool)
    assert d029._environment_state(environment) != before
    assert d038.d035c.D035C_REVERSE_LABEL not in [action.name for action in Action]
    assert (
        len(cast(tuple[float, ...], d027.D027ActionConsequencePredictor().weights))
        == 168
    )
