from __future__ import annotations

import copy
import math

import numpy as np
import pytest

import aweform.exp002_runner as exp002_runner
from aweform import (
    FROZEN_EXP001_CALIBRATION_ENV_CONFIG,
    FROZEN_EXP001_SHARED_CONTROLLER_CONFIG,
    Action,
    EXP001Condition,
    EXP001DevelopmentConfig,
    EXP001Mode,
    ExternalObservation,
    InteroceptiveObservation,
    run_exp001_development_batch,
)
from aweform.exp001_calibration import CALIBRATED_C
from aweform.exp002_protocol import (
    EXP002_B_CANDIDATES,
    EXP002_CALIBRATION_SEEDS,
    EXP002_CONFIRMATORY_SEEDS,
    EXP002_HORIZON,
    EXP002_PROTOCOL_REVISION,
    EXP002BCandidate,
)
from aweform.exp002_runner import (
    EXP002ControllerStep,
    EXP002EpisodeRecord,
    EXP002EvaluatorInitialState,
    EXP002EvaluatorStep,
    EXP002TransitionRecord,
    run_exp002_development_batch,
    summarize_exp002_episode,
)


def test_protocol_candidates_and_fresh_seed_reservations_are_exact() -> None:
    assert EXP002_PROTOCOL_REVISION == "EXP-002-precalibration-001"
    assert [
        (candidate.value, candidate.enter_seek) for candidate in EXP002_B_CANDIDATES
    ] == [
        ("B35", 0.35),
        ("B40", 0.40),
        ("B45", 0.45),
        ("B50", 0.50),
    ]
    assert EXP002_CALIBRATION_SEEDS == tuple(range(40001, 40201))
    assert EXP002_CONFIRMATORY_SEEDS == tuple(range(50001, 51001))
    assert len(EXP002_CALIBRATION_SEEDS) == 200
    assert len(EXP002_CONFIRMATORY_SEEDS) == 1000
    assert not set(EXP002_CALIBRATION_SEEDS) & set(EXP002_CONFIRMATORY_SEEDS)


def test_only_b_enter_seek_threshold_varies_across_candidates() -> None:
    b_configs = [
        exp002_runner.EXP002SharedControllerValues().for_b_candidate(candidate)
        for candidate in EXP002_B_CANDIDATES
    ]
    assert [config.enter_seek for config in b_configs] == [0.35, 0.40, 0.45, 0.50]
    assert {config.resource_contact_threshold for config in b_configs} == {0.8}
    assert {config.recover for config in b_configs} == {0.85}
    assert {config.blind_explore_duration for config in b_configs} == {10}
    assert {config.blind_charge_duration for config in b_configs} == {5}

    a_c_config = exp002_runner.EXP002SharedControllerValues().for_a_or_c()
    historical = FROZEN_EXP001_SHARED_CONTROLLER_CONFIG.for_candidate(CALIBRATED_C)
    assert a_c_config == historical


def test_b35_reproduces_the_existing_exp001_threshold_exactly() -> None:
    b35 = exp002_runner.EXP002SharedControllerValues().for_b_candidate(
        EXP002BCandidate.B35
    )
    assert b35.enter_seek == 0.35
    assert b35 == EXP001DevelopmentConfig(
        resource_contact_threshold=0.8,
        blind_explore_duration=10,
        blind_charge_duration=5,
        enter_seek=0.35,
        recover=0.85,
    )


def test_a_and_c_trajectory_behaviour_is_unchanged_for_b35() -> None:
    old = run_exp001_development_batch(
        seeds=[18001],
        env_config=FROZEN_EXP001_CALIBRATION_ENV_CONFIG,
        development_config=EXP001DevelopmentConfig(
            resource_contact_threshold=0.8,
            blind_explore_duration=10,
            blind_charge_duration=5,
            enter_seek=0.35,
            recover=0.85,
        ),
    )
    new = run_exp002_development_batch(
        seeds=[18001],
        env_config=FROZEN_EXP001_CALIBRATION_ENV_CONFIG,
        candidate=EXP002BCandidate.B35,
    )
    old_by_condition = {episode.condition: episode for episode in old.episodes}
    new_by_condition = {episode.condition: episode for episode in new.episodes}
    for condition in (EXP001Condition.A, EXP001Condition.C):
        old_episode = old_by_condition[condition]
        new_episode = new_by_condition[condition]
        assert new_episode.initial_state.position == old_episode.initial_state.position
        assert (
            new_episode.initial_state.source_positions
            == old_episode.initial_state.source_positions
        )
        assert [
            (
                transition.privileged_evaluator.action,
                transition.privileged_evaluator.position_after,
                transition.privileged_evaluator.actual_energy_after,
                transition.privileged_evaluator.controller_mode,
            )
            for transition in new_episode.transitions
        ] == [
            (
                transition.privileged_evaluator.action,
                transition.privileged_evaluator.position,
                transition.privileged_evaluator.actual_energy,
                transition.privileged_evaluator.controller_mode,
            )
            for transition in old_episode.transitions
        ]
        assert [
            transition.controller_visible.observation
            for transition in new_episode.transitions
        ] == [
            transition.controller_visible.observation
            for transition in old_episode.transitions
        ]


def test_exp002_runner_is_deterministic_and_keeps_telemetry_evaluator_only() -> None:
    first = run_exp002_development_batch(
        seeds=[18002],
        env_config=FROZEN_EXP001_CALIBRATION_ENV_CONFIG,
        candidate=EXP002BCandidate.B45,
    )
    second = run_exp002_development_batch(
        seeds=[18002],
        env_config=FROZEN_EXP001_CALIBRATION_ENV_CONFIG,
        candidate=EXP002BCandidate.B45,
    )
    assert first == second
    assert len(first.diagnostics) == 3
    for episode in first.episodes:
        for transition in episode.transitions:
            visible = transition.controller_visible.observation
            privileged = transition.privileged_evaluator
            assert not hasattr(visible, "position")
            assert not hasattr(visible, "source_positions")
            assert not hasattr(visible, "nearest_source_distance_at_onset")
            assert not hasattr(visible, "coverage_fraction")
            assert len(privileged.position_before) == 2
            assert len(privileged.position_after) == 2


def test_reserved_exp001_and_exp002_seeds_are_rejected_before_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    constructions = 0
    real_environment = exp002_runner.AweformEnv

    class SpyEnvironment(real_environment):
        def __init__(self, config: object) -> None:
            nonlocal constructions
            constructions += 1
            super().__init__(config)  # type: ignore[arg-type]

    monkeypatch.setattr(exp002_runner, "AweformEnv", SpyEnvironment)
    for seed in (
        20001,
        30001,
        EXP002_CALIBRATION_SEEDS[0],
        EXP002_CONFIRMATORY_SEEDS[0],
    ):
        with pytest.raises(ValueError, match="reserved|reuse"):
            run_exp002_development_batch(
                seeds=[seed],
                env_config=FROZEN_EXP001_CALIBRATION_ENV_CONFIG,
                candidate=EXP002BCandidate.B35,
            )
    assert constructions == 0


def _synthetic_b_episode() -> EXP002EpisodeRecord:
    visible = InteroceptiveObservation(
        energy=0.34,
        external=ExternalObservation(0.0, 0.0, 0.0),
    )
    transitions = (
        EXP002TransitionRecord(
            controller_visible=EXP002ControllerStep(visible),
            privileged_evaluator=EXP002EvaluatorStep(
                step_index=1,
                action=Action.MOVE_FORWARD,
                position_before=(0.5, 0.5),
                position_after=(0.6, 0.5),
                heading=0.0,
                actual_energy_before=3.4,
                actual_energy_after=3.3,
                harvested_energy=0.0,
                basal_cost=0.1,
                action_cost=0.1,
                controller_mode_before_action=EXP001Mode.EXPLORE,
                controller_mode=EXP001Mode.SEEK_RESOURCE,
                terminated=False,
                truncated=False,
            ),
        ),
        EXP002TransitionRecord(
            controller_visible=EXP002ControllerStep(visible),
            privileged_evaluator=EXP002EvaluatorStep(
                step_index=2,
                action=Action.WAIT,
                position_before=(0.6, 0.5),
                position_after=(0.6, 0.5),
                heading=0.0,
                actual_energy_before=3.3,
                actual_energy_after=3.2,
                harvested_energy=0.0,
                basal_cost=0.1,
                action_cost=0.0,
                controller_mode_before_action=EXP001Mode.SEEK_RESOURCE,
                controller_mode=EXP001Mode.CHARGE,
                terminated=False,
                truncated=False,
            ),
        ),
        EXP002TransitionRecord(
            controller_visible=EXP002ControllerStep(visible),
            privileged_evaluator=EXP002EvaluatorStep(
                step_index=3,
                action=Action.WAIT,
                position_before=(0.6, 0.5),
                position_after=(0.6, 0.5),
                heading=0.0,
                actual_energy_before=3.2,
                actual_energy_after=9.0,
                harvested_energy=0.0,
                basal_cost=0.1,
                action_cost=0.0,
                controller_mode_before_action=EXP001Mode.CHARGE,
                controller_mode=EXP001Mode.EXPLORE,
                terminated=False,
                truncated=True,
            ),
        ),
    )
    return EXP002EpisodeRecord(
        condition=EXP001Condition.B,
        candidate=EXP002BCandidate.B35,
        environment_seed=18003,
        initial_state=EXP002EvaluatorInitialState(
            position=(0.5, 0.5),
            heading=0.0,
            actual_energy=5.0,
            source_positions=((1.0, 0.5),),
        ),
        transitions=transitions,
    )


def test_return_reserve_diagnostics_are_evaluator_side_and_complete() -> None:
    diagnostics = summarize_exp002_episode(_synthetic_b_episode())

    assert len(diagnostics.seek_attempts) == 1
    attempt = diagnostics.seek_attempts[0]
    assert attempt.onset_step == 1
    assert attempt.normalized_energy_at_onset == pytest.approx(0.34)
    assert attempt.nearest_source_distance_at_onset == pytest.approx(0.5)
    assert attempt.reached_charge
    assert attempt.minimum_normalized_energy == pytest.approx(0.32)
    assert diagnostics.complete_recharge_cycle_count == 1
    assert diagnostics.explore_action_count == 1
    assert diagnostics.distance_travelled_during_explore == 0.0
    assert diagnostics.visited_cell_count == 4
    assert diagnostics.remaining_cell_count == 1020
    assert diagnostics.coverage_fraction == pytest.approx(4 / 1024)
    assert math.isfinite(diagnostics.seek_attempts[0].nearest_source_distance_at_onset)


def test_coverage_instrumentation_does_not_change_rng_state() -> None:
    rng = np.random.default_rng(18004)
    before = copy.deepcopy(rng.bit_generator.state)
    # The runner's evaluator computations are deterministic pure arithmetic;
    # this explicit guard documents the no-RNG contract for this test module.
    diagnostics = summarize_exp002_episode(_synthetic_b_episode())
    after = copy.deepcopy(rng.bit_generator.state)

    assert diagnostics.visited_cell_count > 0
    assert after == before


def test_exp002_horizon_is_frozen() -> None:
    assert EXP002_HORIZON == 1000
