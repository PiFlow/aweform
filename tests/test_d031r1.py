"""Focused tests for the D-031R1 learned SEEK scaffold-displacement probe."""

from __future__ import annotations

from typing import cast

import numpy as np
import pytest

from aweform import d026, d027, d030, d031r1
from aweform.env import Action
from aweform.exp003 import BeaconObservation
from aweform.exp003_seed_policy import validate_exp003_development_seeds


def observation() -> d027.D027Observation:
    return d027.D027Observation(
        energy=0.25,
        beacon=BeaconObservation(0.1, 0.2, 0.3, False),
        thermal=0.2875,
    )


def prediction(forward_delta: float) -> d027.D027Prediction:
    values = [0.0] * len(d031r1.D031R1_OUTPUTS)
    values[d031r1.D031R1_FORWARD_OUTPUT_INDEX] = forward_delta
    return d027.D027Prediction(tuple(values))


def test_d031r1_freeze_and_exact_seed_guard() -> None:
    assert d031r1.D031R1_HORIZON == 70_000
    assert d031r1.D031R1_DEFAULT_DEVELOPMENT_SEEDS == tuple(range(18468, 18488))
    assert validate_exp003_development_seeds(
        d031r1.D031R1_DEFAULT_DEVELOPMENT_SEEDS
    ) == (
        d031r1.D031R1_DEFAULT_DEVELOPMENT_SEEDS
    )
    assert (
        d031r1._validate_d031r1_development_seeds(d031r1.D031R1_DEFAULT_DEVELOPMENT_SEEDS)
        == d031r1.D031R1_DEFAULT_DEVELOPMENT_SEEDS
    )
    with pytest.raises(ValueError, match="requires exactly"):
        d031r1._validate_d031r1_development_seeds((18468,))
    with pytest.raises(ValueError, match="reserved"):
        d031r1._validate_d031r1_development_seeds((50001, 50002))
    with pytest.raises(ValueError, match="only predeclared"):
        d031r1._validate_d031r1_seed(18447)


def test_d031r1_reuses_exact_d030_steering_rule() -> None:
    current = observation()
    predictions = {
        Action.TURN_LEFT: prediction(0.01),
        Action.TURN_RIGHT: prediction(0.03),
        Action.MOVE_FORWARD: prediction(0.02),
    }
    assert d031r1.D031R1_STEERING_ACTIONS == (
        Action.TURN_LEFT,
        Action.TURN_RIGHT,
        Action.MOVE_FORWARD,
    )
    assert Action.WAIT not in d031r1.D031R1_STEERING_ACTIONS
    assert d031r1._choose_steering_action(current, predictions, Action.TURN_LEFT) is (
        Action.TURN_RIGHT
    )
    tied = {action: prediction(0.0) for action in d031r1.D031R1_STEERING_ACTIONS}
    assert d031r1._choose_steering_action(current, tied, Action.MOVE_FORWARD) is (
        Action.MOVE_FORWARD
    )


def test_short_matched_replay_is_deterministic_and_branch_disabled_is_exact() -> None:
    # This bounded pre-freeze check uses a historical D-030 seed.  It must not
    # execute any part of the newly authorized D-031R1 seed block.
    first = {
        arm: d031r1._run_arm(
            18428,
            arm=arm,
            horizon=20,
            evaluator_diagnostics=True,
            seed_validator=d030._validate_d030_seed,
        )
        for arm in d031r1.D031R1_ARM_NAMES
    }
    second = {
        arm: d031r1._run_arm(
            18428,
            arm=arm,
            horizon=20,
            evaluator_diagnostics=True,
            seed_validator=d030._validate_d030_seed,
        )
        for arm in d031r1.D031R1_ARM_NAMES
    }
    assert first == second
    first_arms = first
    for arm in d031r1.D031R1_ARM_NAMES:
        result = first_arms[arm]
        assert result["transitions"] == 20
        isolation = cast(dict[str, object], result["isolation"])
        assert isolation["real_updates_executed_action_only"] is True
    for arm in d031r1.D031R1_NO_DETRAP_ARMS:
        result = first_arms[arm]
        control = d031r1._run_arm(
            18428,
            arm=arm,
            horizon=20,
            evaluator_diagnostics=False,
            seed_validator=d030._validate_d030_seed,
        )
        assert d031r1._compare_branch_disabled(result, control)[
            "real_summary_exact_equal"
        ] is True


def test_no_detrap_arm_retains_one_draw_and_never_calls_seek_explorer() -> None:
    controller = d031r1.D031R1NoDetrapController(np.random.default_rng(0))
    controller.reset()
    controller.mode = d026.D026Mode.AWAY
    action = controller.act(observation())
    arbitration = controller.last_arbitration
    assert action in d031r1.D031R1_STEERING_ACTIONS
    assert arbitration is not None
    assert arbitration.delegated is False
    assert controller.seek_segment_starts == 1
    assert controller.false_contact_seek_explorer_calls == 0
    assert d031r1.D031R1NoDetrapController.seek_delegation_probability == 0.0


def test_greedy_arm_prediction_values_are_evaluator_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ordinary = d031r1._run_arm(
        18428,
        arm="GREEDY_NO_DETRAP",
        horizon=d031r1.D031R1_HORIZON,
        evaluator_diagnostics=True,
        seed_validator=d030._validate_d030_seed,
    )

    def extreme_predictions(
        _learner: d027.D027ActionConsequencePredictor,
        _current: d027.D027Observation,
    ) -> tuple[dict[Action, d027.D027Prediction], bool]:
        return (
            {
                action: prediction(
                    1e300 if action is Action.TURN_LEFT else -1e300
                )
                for action in d031r1.D031R1_STEERING_ACTIONS
            },
            True,
        )

    monkeypatch.setattr(d031r1, "_query_candidate_predictions", extreme_predictions)
    extreme = d031r1._run_arm(
        18428,
        arm="GREEDY_NO_DETRAP",
        horizon=d031r1.D031R1_HORIZON,
        evaluator_diagnostics=True,
        seed_validator=d030._validate_d030_seed,
    )
    for field in (
        "outcome_classification",
        "transitions",
        "termination_reason",
        "action_counts",
        "trajectory_digest",
        "executed_update_digest",
        "final_weight_digest",
        "final_policy_rng_digest",
        "final_environment_rng_digest",
    ):
        assert extreme[field] == ordinary[field]
    assert extreme["seek_arbitration"] == ordinary["seek_arbitration"]
    assert cast(dict[str, object], extreme["isolation"])[
        "branch_outcomes_causal"
    ] is False


def test_arm_a_matches_merged_d030_on_a_historical_seed() -> None:
    historical = d030._run_arm(
        18428,
        arm="LEARNED_FORWARD",
        horizon=d030.D030_HORIZON,
        evaluator_diagnostics=True,
    )
    current = d031r1._run_arm(
        18428,
        arm="LEARNED_WITH_DETRAP",
        horizon=d031r1.D031R1_HORIZON,
        evaluator_diagnostics=True,
        seed_validator=d030._validate_d030_seed,
    )
    for field in (
        "outcome_classification",
        "transitions",
        "physical_seconds",
        "terminated",
        "truncated",
        "termination_reason",
        "final_mode",
        "action_counts",
        "mode_occupancy",
        "mode_entry_counts",
        "full_departures",
        "physical_charger_exits",
        "low_energy_seek_entries",
        "physical_reacquisitions",
        "full_recharge_events",
        "post_recharge_redepartures",
        "completed_energy_regulation_cycles",
        "seek_episodes",
        "trajectory_digest",
        "executed_update_digest",
        "_weights",
        "final_policy_rng_digest",
        "final_environment_rng_digest",
    ):
        assert current[field] == historical[field]
    current_arbitration = cast(dict[str, object], current["seek_arbitration"])
    historical_arbitration = cast(dict[str, object], historical["seek_arbitration"])
    assert current_arbitration["false_contact_seek_decisions"] == (
        historical_arbitration["false_contact_seek_decisions"]
    )
    assert current_arbitration["stochastic_delegation_decisions"] == (
        historical_arbitration["stochastic_delegation_decisions"]
    )
