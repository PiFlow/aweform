from __future__ import annotations

import math
import subprocess
from pathlib import Path

import numpy as np
import pytest

from aweform import d058
from aweform.d045 import (
    D045_MAX_WHEEL_DELTA_RAD,
    D045Env,
    D045Observation,
    D045PhysicalConfig,
    integrate_differential_drive,
    quantize_wheel_delta,
    wheel_effort,
)

BASE = d058.BASE_SHA


def test_config_is_limited_to_authorized_room_sizes_and_hides_bounds() -> None:
    assert d058.D058PhysicalConfig().room_side_m == 3.0
    assert d058.D058PhysicalConfig(1.0).room_side_m == 1.0
    for value in (0.5, 2.0, True, float("nan")):
        with pytest.raises(ValueError):
            d058.D058PhysicalConfig(value)
    assert not hasattr(d058.D058PhysicalConfig(), "world_min")
    assert not hasattr(d058.D058PhysicalConfig(), "world_max")


def test_reset_contract_and_observation_information_boundary() -> None:
    for length in (3.0, 1.0):
        env = d058.D058Env(d058.D058PhysicalConfig(length))
        observation, info = env.reset()
        assert env.station_center == (length / 2, length / 2)
        assert env.body.position == (length / 4, length / 4)
        assert env.body.heading == 0.0
        assert observation.dtype == np.float32 and observation.shape == (8,)
        assert info == {}
        with pytest.raises(ValueError):
            env.reset(options={"station_center": (length / 2 + 0.01, length / 2)})
        with pytest.raises(ValueError):
            env.reset(options={"mystery": 1})
        for heading in (0.0, math.pi / 4, math.pi / 2, math.pi):
            hx = 0.09 * abs(math.cos(heading)) + 0.1075 * abs(math.sin(heading))
            hy = 0.09 * abs(math.sin(heading)) + 0.1075 * abs(math.cos(heading))
            for point in (
                (hx - 0.001, length / 2),
                (length - hx + 0.001, length / 2),
                (length / 2, hy - 0.001),
                (length / 2, length - hy + 0.001),
                (hx - 0.001, hy - 0.001),
                (length - hx + 0.001, hy - 0.001),
                (hx - 0.001, length - hy + 0.001),
                (length - hx + 0.001, length - hy + 0.001),
            ):
                with pytest.raises(ValueError):
                    env.reset(options={"body_position": point, "heading": heading})


def test_clamp_full_yaw_projection_slip_and_private_telemetry() -> None:
    m = D045_MAX_WHEEL_DELTA_RAD
    env = d058.D058Env()
    env.reset(
        options={
            "body_position": (0.09, 1.5),
            "station_center": (1.5, 1.5),
            "heading": 0.0,
        }
    )
    obs, reward, terminated, truncated, info = env.step((-m, m))
    transition, contact = env.last_transition, env.last_contact
    assert transition is not None and contact is not None
    assert (
        transition.heading_after
        == integrate_differential_drive((0.09, 1.5), 0.0, -m, m)[1]
    )
    assert transition.actual_delta_left == -m and transition.actual_delta_right == m
    assert transition.boundary_scale == 1.0
    assert contact.unconstrained_endpoint != contact.executed_endpoint
    assert contact.slip_magnitude_m == math.dist(
        contact.unconstrained_endpoint, contact.executed_endpoint
    )
    assert reward == 0.0 and info == {} and not terminated and not truncated
    assert obs.shape == (8,) and isinstance(env._observation(), D045Observation)
    assert "last_contact" not in info
    assert env.observation_space.contains(obs)
    assert transition.actuator_electrical_power_w == wheel_effort(-m, m, m)
    assert env._previous_wheel_delta == (-m, m)
    assert env._observation().wheel_delta_left == quantize_wheel_delta(-m)
    assert env._observation().wheel_delta_right == quantize_wheel_delta(m)


def test_free_space_matches_d045_oracle_for_representative_state() -> None:
    for length in (3.0, 1.0):
        options = {
            "body_position": (length / 2, length / 2),
            "station_center": (length / 2, length / 2),
            "heading": 0.3,
            "battery_j": 1065.6,
            "body_temperature_c": 23.0,
            "charger_termination_latched": False,
        }
        actual = d058.D058Env(d058.D058PhysicalConfig(length))
        oracle = D045Env(
            D045PhysicalConfig(world_min=(0.0, 0.0), world_max=(length, length))
        )
        actual.reset(options=options)
        oracle.reset(options=options)
        a, b = actual.step((0.2, 0.1)), oracle.step((0.2, 0.1))
        assert actual.body.position == oracle.body.position
        assert actual.body.heading == oracle.body.heading
        assert a[0].tobytes() == b[0].tobytes()
        assert actual.battery_j == oracle.battery_j
        assert actual.body_temperature_c == oracle.body_temperature_c


def test_probe_sets_have_frozen_order_and_dimensions() -> None:
    u9, u10, headings = d058._probe_sets()
    m = D045_MAX_WHEEL_DELTA_RAD
    assert u9 == (
        (-m, -m),
        (-m, 0.0),
        (-m, m),
        (0.0, -m),
        (0.0, m),
        (m, -m),
        (m, 0.0),
        (m, m),
        d058.U_ONSET,
    )
    assert u10 == u9 + ((0.0, 0.0),)
    assert len(headings) == 32 and headings[:24] == tuple(
        k * math.pi / 12 for k in range(24)
    )


def test_protected_sources_unchanged() -> None:
    root = Path(__file__).resolve().parents[1]
    if subprocess.run(
        ["git", "cat-file", "-e", f"{BASE}^{{commit}}"], cwd=root, capture_output=True
    ).returncode:
        pytest.skip("authorized base commit object is unavailable")
    result = subprocess.run(
        ["git", "diff", "--exit-code", BASE, "--", *d058.PROTECTED],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
