"""One-shot staged adapter around unchanged Level-1 and D-058 physiology."""

from __future__ import annotations

from typing import Any

import numpy as np

from aweform.d045 import D045ChargePhase, _termination_reason, wheel_effort
from aweform.d052 import D052Controller
from aweform.d053 import D053RoamingFixture
from aweform.d058 import D058Env, D058PhysicalConfig

from .fixture import DT, ContactWorld

START_OPTIONS: dict[str, object] = {
    "body_position": (0.75, 0.75),
    "heading": 0.0,
    "battery_j": 2664.0,
    "body_temperature_c": 23.0,
    "charger_termination_latched": False,
}
SEED = 22571
HORIZON = 100_000


class PymunkPhysiologyAdapter:
    """Preserve D-058 state/contract while replacing only pose advancement.

    Accounting below is copied from the unchanged D058Env.step body (source
    provenance: src/aweform/d058.py lines 302-410 at the frozen base); dock,
    charging decision, observation packing, thresholds and shared helpers are
    reused directly. It runs once after each completed 0.1 s Pymunk advance.
    """

    def __init__(self) -> None:
        self.physiology = D058Env(D058PhysicalConfig(room_side_m=3.0))
        self.world = ContactWorld(microsteps=10)
        self.controller = D052Controller()
        self.proposals = D053RoamingFixture(SEED)
        self.observation: np.ndarray | None = None
        self._steps = 0
        self._done = False

    def reset(self) -> np.ndarray:
        obs, info = self.physiology.reset(seed=SEED, options=START_OPTIONS)
        if info != {}:
            raise RuntimeError("D-058 reset info contract changed")
        assert self.physiology.body is not None
        self.world.body.position = self.physiology.body.position
        self.world.body.angle = self.physiology.body.heading
        self.observation = obs
        return obs.copy()

    def step(self) -> dict[str, Any]:
        if self._done or self.observation is None:
            raise RuntimeError("adapter lifetime must be reset and still active")
        # Same fixed proposal stream/one proposal per decision as D-053; Level-1
        # arbitration is the unchanged accepted D052Controller.
        proposal = self.proposals.propose()
        decision = self.controller.command(self.observation, proposal.wheel_command)
        record = self.world.advance(
            (decision.wheel_delta_left, decision.wheel_delta_right)
        )
        env = self.physiology
        cfg = env.config._base
        if (
            env.body is None
            or env.station_center is None
            or env.body_temperature_c is None
        ):
            raise RuntimeError("D-058 physiology state was not initialized")
        env.body.x, env.body.y = record.end
        env.body.heading = record.end_angle
        contact_after = env.charging_contact
        battery_before = env._battery_j
        temperature_before = env.body_temperature_c
        left, right = record.shaft
        limit = cfg.max_wheel_delta_rad
        effort = wheel_effort(left, right, limit)
        actuator_power = cfg.wheel_power_scale_w * effort
        actuator_heat = cfg.wheel_body_heat_scale_w * effort
        total_load = cfg.electronics_power_w + actuator_power
        load_energy = total_load * DT
        charge = env._charge_decision(contact_after, battery_before)
        charge_energy = min(
            charge.requested_stored_power_w * DT,
            max(0.0, cfg.battery_capacity_j - battery_before + load_energy),
        )
        stored_power = charge_energy / DT
        battery_after = min(
            cfg.battery_capacity_j,
            max(0.0, battery_before + charge_energy - load_energy),
        )
        latched = charge.termination_latched_after
        if (
            charge.phase
            in (D045ChargePhase.BULK, D045ChargePhase.TAPER_1, D045ChargePhase.TAPER_2)
            and battery_after >= cfg.battery_capacity_j
        ):
            latched = True
        charger_input = (
            stored_power / cfg.charge_efficiency if stored_power > 0 else 0.0
        )
        charging_heat = charger_input - stored_power if stored_power > 0 else 0.0
        total_heat = cfg.electronics_body_heat_w + actuator_heat + charging_heat
        exchange = cfg.thermal_conductance_w_per_k * (
            cfg.ambient_temperature_c - temperature_before
        )
        temperature_after = (
            temperature_before
            + DT * (total_heat + exchange) / cfg.thermal_capacitance_j_per_k
        )
        env._battery_j = battery_after
        env.body_temperature_c = temperature_after
        env._charger_termination_latched = latched
        env._previous_wheel_delta = record.shaft
        self._steps += 1
        env._step_count = self._steps
        energy_nonviable = battery_after <= 0.0
        protective = (
            temperature_after >= cfg.protective_temperature_c
            and temperature_after < cfg.hard_temperature_c
        )
        emergency = temperature_after >= cfg.hard_temperature_c
        reason = _termination_reason(emergency, protective, energy_nonviable)
        terminated = reason is not None
        self._done = terminated
        obs = env._observation().as_array()
        self.observation = obs
        if obs.shape != (8,) or obs.dtype != np.float32:
            raise RuntimeError("organism observation contract violation")
        # No evaluator state, labels, reward shaping or info cross this API.
        reward = 0.0
        info: dict[str, object] = {}
        return {
            "observation": obs.tolist(),
            "reward": reward,
            "info": info,
            "terminated": terminated,
            "decision_mode": decision.active_mode.value,
            "decision_source": decision.command_source.value,
            "contact": contact_after,
            "energy_j": battery_after,
            "temperature_c": temperature_after,
            "position_m": list(record.end),
            "yaw_rad": record.end_angle,
            "impulse": record.total_impulse,
            "contact_points": record.contact_count,
            "shaft_rad": list(record.shaft),
            "transition": self._steps,
        }


def run_once() -> dict[str, object]:
    """Execute exactly one staged Pymunk lifetime; caller must gate it first."""
    import hashlib

    adapter = PymunkPhysiologyAdapter()
    adapter.reset()
    trace: list[dict[str, Any]] = []
    for _ in range(HORIZON):
        row = adapter.step()
        trace.append(row)
        if row["terminated"]:
            break
    # This is the single allowed lifetime call. The harness horizon is not
    # surfaced as an observation or passed into the controller.
    raw = json_bytes(trace)
    return {
        "seed": SEED,
        "initial_state": START_OPTIONS,
        "configured_horizon": HORIZON,
        "transitions": len(trace),
        "terminated": bool(trace[-1]["terminated"]),
        "termination_reason": "energy_or_thermal"
        if trace[-1]["terminated"]
        else "harness_horizon",
        "charging_steps": sum(bool(row["contact"]) for row in trace),
        "contact_steps": sum(int(row["contact_points"]) > 0 for row in trace),
        "max_impulse": max((float(row["impulse"]) for row in trace), default=0.0),
        "final_energy_j": trace[-1]["energy_j"],
        "final_temperature_c": trace[-1]["temperature_c"],
        "final_position_m": trace[-1]["position_m"],
        "trace_sha256": hashlib.sha256(raw).hexdigest(),
        "trace": trace,
    }


def run_reference_once() -> dict[str, object]:
    """Run one unchanged D-058 reference with the same fixed state and stream."""
    import hashlib

    env = D058Env(D058PhysicalConfig(room_side_m=3.0))
    observation, info = env.reset(seed=SEED, options=START_OPTIONS)
    if info != {}:
        raise RuntimeError("D-058 reset info contract changed")
    controller, proposals = D052Controller(), D053RoamingFixture(SEED)
    trace: list[dict[str, Any]] = []
    for index in range(HORIZON):
        proposal = proposals.propose()
        decision = controller.command(observation, proposal.wheel_command)
        observation, reward, terminated, truncated, step_info = env.step(
            (decision.wheel_delta_left, decision.wheel_delta_right)
        )
        if (
            reward != 0.0
            or step_info != {}
            or observation.shape != (8,)
            or observation.dtype != np.float32
        ):
            raise RuntimeError("D-058 reference violated the organism API contract")
        assert env.body is not None and env.body_temperature_c is not None
        trace.append(
            {
                "index": index + 1,
                "observation": observation.tolist(),
                "reward": reward,
                "info": step_info,
                "terminated": terminated,
                "truncated": truncated,
                "mode": decision.active_mode.value,
                "source": decision.command_source.value,
                "contact": env.charging_contact,
                "energy_j": env.battery_j,
                "temperature_c": env.body_temperature_c,
                "position_m": [env.body.x, env.body.y],
                "yaw_rad": env.body.heading,
            }
        )
        if terminated or truncated:
            break
    raw = json_bytes(trace)
    return {
        "seed": SEED,
        "initial_state": START_OPTIONS,
        "configured_horizon": HORIZON,
        "transitions": len(trace),
        "terminated": bool(trace[-1]["terminated"]),
        "termination_reason": "D058_termination"
        if trace[-1]["terminated"]
        else "D058_truncation_or_horizon",
        "charging_steps": sum(bool(row["contact"]) for row in trace),
        "final_energy_j": trace[-1]["energy_j"],
        "final_temperature_c": trace[-1]["temperature_c"],
        "final_position_m": trace[-1]["position_m"],
        "trace_sha256": hashlib.sha256(raw).hexdigest(),
        "trace": trace,
    }


def json_bytes(value: object) -> bytes:
    import json

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
