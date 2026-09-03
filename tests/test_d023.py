from __future__ import annotations

import inspect
from dataclasses import replace

import numpy as np
import pytest

from aweform import d021, d023
from aweform.d020 import D020PhysicalConfig
from aweform.d021 import D021Mode, D021TransitionTrace
from aweform.env import Action


def _trace_record(*, truncated: bool) -> D021TransitionTrace:
    environment = d023.d021.D020Env()
    environment.reset(
        options={"body_position": (0.1, 0.1), "station_center": (0.9, 0.9)}
    )
    environment.step(Action.WAIT)
    assert environment.last_transition is not None
    telemetry = replace(environment.last_transition, truncated=truncated)
    return D021TransitionTrace(
        transition_index=1,
        mode_before=D021Mode.AWAY,
        mode_after=D021Mode.AWAY,
        action=Action.WAIT,
        observation_before=(0.75, 0.0, 0.0, 0.0, 0.0, 0.2875),
        observation=(0.75, 0.0, 0.0, 0.0, 0.0, 0.2875),
        telemetry=telemetry,
        reward=0.0,
        info={},
    )


def test_d023_freeze_and_exact_seed_guard() -> None:
    assert d023.D023_HORIZON == 210_000
    assert d023.D023_HORIZON == 3 * d021.D021_HORIZON
    assert d023.D023_DEFAULT_DEVELOPMENT_SEEDS == (18365, 18366, 18367)
    assert d023._validate_d023_development_seeds(
        d023.D023_DEFAULT_DEVELOPMENT_SEEDS
    ) == d023.D023_DEFAULT_DEVELOPMENT_SEEDS
    with pytest.raises(ValueError, match="requires exactly"):
        d023._validate_d023_development_seeds((18365,))
    with pytest.raises(ValueError, match="reserved for a formal experiment"):
        d023._validate_d023_development_seeds((50001, 50002, 50003))


def test_d023_runner_reuses_d021_and_only_replaces_horizon() -> None:
    source = inspect.getsource(d023._run_d023_seed)
    assert "d021._run_seed" in source
    assert "D020PhysicalConfig" not in source
    config = replace(D020PhysicalConfig(), episode_horizon=d023.D023_HORIZON)
    assert config.dt_seconds == D020PhysicalConfig().dt_seconds
    assert config.battery_capacity_j == D020PhysicalConfig().battery_capacity_j
    assert config.protective_shutdown_c == D020PhysicalConfig().protective_shutdown_c


def test_public_runner_has_fixed_seed_and_horizon_surface() -> None:
    signature = inspect.signature(d023.run_d023_probe)
    assert tuple(signature.parameters) == ("executed_commit_sha",)
    assert d023.D023_AUTHORITATIVE_BASE_SHA == (
        "a7c66a8bc096baf61b50bc3963b6cf19a6d38f83"
    )


def test_prefix_comparator_ignores_only_d021_final_truncation_label() -> None:
    reference = _trace_record(truncated=True)
    actual = _trace_record(truncated=False)
    reference = replace(
        reference,
        transition_index=d021.D021_HORIZON,
        telemetry=replace(reference.telemetry, step_index=d021.D021_HORIZON),
    )
    actual = replace(
        actual,
        transition_index=d021.D021_HORIZON,
        telemetry=replace(actual.telemetry, step_index=d021.D021_HORIZON),
    )
    assert d023._same_causal_transition(actual, reference)
    assert not d023._same_causal_transition(
        replace(actual, action=Action.MOVE_FORWARD), reference
    )


def test_d023_short_same_seed_replay_and_boundary() -> None:
    first = d023._run_d023_seed(18365, horizon=200)
    second = d023._run_d023_seed(18365, horizon=200)
    assert first == second
    assert first["transitions"] == 200
    assert first["seek_episodes"] == []
    assert first["cycle_summaries"]
    assert first["cycle_summaries"][0]["status"] == "horizon_censored"
    assert first["failure_and_censoring"]["horizon_truncation"] is True


def test_d023_has_no_new_observation_or_learning_path() -> None:
    assert len(D020PhysicalConfig().__dataclass_fields__) > 0
    assert d021.D021Observation.__dataclass_fields__.keys() == {
        "energy",
        "beacon",
        "thermal",
    }
    assert d021.D021_FULL_ENERGY_THRESHOLD == 1.0
    assert d021.EXP003_B50_ENTER_SEEK_THRESHOLD == 0.50
    assert d021._controller_observation(
        np.asarray([1.0, 0.0, 0.0, 0.0, 1.0, 0.2875], dtype=np.float32)
    ).thermal == pytest.approx(0.2875)
