"""One-shot staged adapter around unchanged Level-1 and D-058 physiology."""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from typing import Any

import numpy as np

from aweform.d045 import (
    D045ChargePhase,
    _dock_contact,
    _termination_reason,
    wheel_effort,
)
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


class LifetimeBudgetExceeded(RuntimeError):
    """The frozen wall-clock budget expired between logical transitions."""


class PymunkPhysiologyAdapter:
    """Preserve D-058 state/contract while replacing only pose advancement.

    Accounting below is copied from the unchanged D058Env.step body (source
    provenance: src/aweform/d058.py lines 302-410 at the frozen base); dock,
    charging decision, observation packing, thresholds and shared helpers are
    reused directly. It runs once after each completed 0.1 s Pymunk advance.
    """

    def __init__(self, *, microsteps: int = 10) -> None:
        self.physiology = D058Env(D058PhysicalConfig(room_side_m=3.0))
        self.world = ContactWorld(microsteps=microsteps)
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
        position_before = (env.body.x, env.body.y)
        station_center = env.station_center
        charging_contact_before = env.charging_contact
        latch_before = env.charger_termination_latched
        env.body.x, env.body.y = record.end
        env.body.heading = record.end_angle
        contact_after, dock_plus_error, dock_minus_error = _dock_contact(
            record.end, record.end_angle, station_center, cfg
        )
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
            "proposal_wheels_rad": list(proposal.wheel_command),
            "commanded_wheels_rad": [
                decision.wheel_delta_left,
                decision.wheel_delta_right,
            ],
            "contact": contact_after,
            "paired_dock_contact_before": charging_contact_before,
            "paired_dock_contact_after": contact_after,
            "dock_plus_error_m": dock_plus_error,
            "dock_minus_error_m": dock_minus_error,
            "charger_latch_before": latch_before,
            "charger_latch_after": latched,
            "charge_phase": charge.phase.value,
            "charge_requested_stored_power_w": charge.requested_stored_power_w,
            "charge_stored_energy_j": charge_energy,
            "charge_actual_stored_power_w": stored_power,
            "charger_input_power_w": charger_input,
            "battery_before_j": battery_before,
            "battery_after_j": battery_after,
            "load_energy_j": load_energy,
            "energy_j": battery_after,
            "temperature_c": temperature_after,
            "station_distance_before_m": math.dist(position_before, station_center),
            "station_distance_after_m": math.dist(record.end, station_center),
            "position_m": list(record.end),
            "yaw_rad": record.end_angle,
            "impulse": record.total_impulse,
            "contact_points": record.contact_count,
            "contact_events": [
                {
                    "substep_index": event.substep_index,
                    "shape_pair": list(event.shape_pair),
                    "contact_points": event.contact_points,
                    "impulse": event.impulse,
                    "maximum_contact_penetration_m": event.maximum_contact_penetration,
                }
                for event in record.contact_events
            ],
            "simultaneous_contact_identities": [
                list(identities)
                for identities in record.simultaneous_contact_identities
            ],
            "minimum_clearance_m": record.minimum_clearance_m,
            "clearance_sampling_bound_m": record.clearance_sampling_bound_m,
            "minimum_clearance_by_shape_m": dict(record.minimum_clearance_by_shape),
            "end_clearance_by_shape_m": dict(record.end_clearance_by_shape),
            "max_penetration_m": record.max_penetration,
            "end_penetration_m": record.end_penetration,
            "crossed_wall_or_post": record.crossed_wall_or_post,
            "shaft_rad": list(record.shaft),
            "engine_steps": record.step_count,
            "transition": self._steps,
            "termination_reason": reason.value if reason else None,
        }


def run_once(
    *,
    microsteps: int = 10,
    on_transition: Callable[[dict[str, Any]], None] | None = None,
    transition_guard: Callable[[dict[str, Any]], None] | None = None,
    deadline_monotonic: float | None = None,
    finalize_reserve_s: float = 0.0,
) -> dict[str, object]:
    """Execute one staged Pymunk lifetime; caller must gate it first."""
    import hashlib

    adapter = PymunkPhysiologyAdapter(microsteps=microsteps)
    adapter.reset()
    trace: list[dict[str, Any]] = []
    for _ in range(HORIZON):
        if deadline_monotonic is not None and time.monotonic() >= deadline_monotonic:
            raise LifetimeBudgetExceeded("lifetime wall-clock cap reached")
        row = adapter.step()
        trace.append(row)
        if on_transition is not None:
            on_transition(row)
        if transition_guard is not None:
            transition_guard(row)
        if row["terminated"]:
            break
    if (
        deadline_monotonic is not None
        and deadline_monotonic - time.monotonic() <= finalize_reserve_s
    ):
        raise LifetimeBudgetExceeded("insufficient cap reserve for trace finalization")
    # This is the single allowed lifetime call. The harness horizon is not
    # surfaced as an observation or passed into the controller.
    raw = json_bytes(trace)
    return {
        "seed": SEED,
        "initial_state": START_OPTIONS,
        "configured_horizon": HORIZON,
        "microsteps_per_transition": microsteps,
        "planned_engine_steps": HORIZON * microsteps,
        "actual_engine_steps": len(trace) * microsteps,
        "transitions": len(trace),
        "terminated": bool(trace[-1]["terminated"]),
        "termination_reason": trace[-1]["termination_reason"]
        if trace[-1]["terminated"]
        else "harness_horizon",
        "charging_steps": sum(bool(row["contact"]) for row in trace),
        "charge_stored_energy_j": sum(
            float(row["charge_stored_energy_j"]) for row in trace
        ),
        "contact_steps": sum(int(row["contact_points"]) > 0 for row in trace),
        "max_impulse": max((float(row["impulse"]) for row in trace), default=0.0),
        "final_energy_j": trace[-1]["energy_j"],
        "final_temperature_c": trace[-1]["temperature_c"],
        "final_position_m": trace[-1]["position_m"],
        "trace_sha256": hashlib.sha256(raw).hexdigest(),
        "trace": trace,
    }


def run_reference_once(
    *,
    on_transition: Callable[[dict[str, Any]], None] | None = None,
    transition_guard: Callable[[dict[str, Any]], None] | None = None,
    deadline_monotonic: float | None = None,
    finalize_reserve_s: float = 0.0,
) -> dict[str, object]:
    """Run one unchanged D-058 reference with the same fixed state and stream."""
    import hashlib

    env = D058Env(D058PhysicalConfig(room_side_m=3.0))
    observation, info = env.reset(seed=SEED, options=START_OPTIONS)
    if info != {}:
        raise RuntimeError("D-058 reset info contract changed")
    controller, proposals = D052Controller(), D053RoamingFixture(SEED)
    trace: list[dict[str, Any]] = []
    for index in range(HORIZON):
        if deadline_monotonic is not None and time.monotonic() >= deadline_monotonic:
            raise LifetimeBudgetExceeded("paired lifetime wall-clock cap reached")
        proposal = proposals.propose()
        decision = controller.command(observation, proposal.wheel_command)
        charging_contact_before = env.charging_contact
        latch_before = env.charger_termination_latched
        position_before = (env.body.x, env.body.y) if env.body is not None else None
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
        telemetry = env.last_transition
        if telemetry is None or position_before is None:
            raise RuntimeError("D-058 transition telemetry is missing")
        row = {
            "index": index + 1,
            "observation": observation.tolist(),
            "reward": reward,
            "info": step_info,
            "terminated": terminated,
            "truncated": truncated,
            "mode": decision.active_mode.value,
            "source": decision.command_source.value,
            "proposal_wheels_rad": list(proposal.wheel_command),
            "commanded_wheels_rad": [
                decision.wheel_delta_left,
                decision.wheel_delta_right,
            ],
            "contact": telemetry.charging_contact_after,
            "paired_dock_contact_before": charging_contact_before,
            "paired_dock_contact_after": telemetry.charging_contact_after,
            "dock_plus_error_m": telemetry.dock_plus_error_m,
            "dock_minus_error_m": telemetry.dock_minus_error_m,
            "charger_latch_before": latch_before,
            "charger_latch_after": telemetry.charger_termination_latched_after,
            "charge_phase": telemetry.charge_phase.value,
            "charge_requested_stored_power_w": telemetry.requested_stored_power_w,
            "charge_stored_energy_j": (
                telemetry.actual_stored_power_w * env.config._base.dt_seconds
            ),
            "charge_actual_stored_power_w": telemetry.actual_stored_power_w,
            "charger_input_power_w": telemetry.charger_input_power_w,
            "battery_before_j": telemetry.battery_before_j,
            "battery_after_j": telemetry.battery_after_j,
            "load_energy_j": (
                telemetry.total_electrical_load_w * env.config._base.dt_seconds
            ),
            "energy_j": env.battery_j,
            "temperature_c": env.body_temperature_c,
            "station_distance_before_m": math.dist(
                position_before, telemetry.station_center
            ),
            "station_distance_after_m": math.dist(
                (env.body.x, env.body.y), telemetry.station_center
            ),
            "position_m": [env.body.x, env.body.y],
            "yaw_rad": env.body.heading,
            "termination_reason": (
                telemetry.termination_reason.value
                if telemetry.termination_reason
                else None
            ),
            "transition": index + 1,
            "engine_steps": 0,
        }
        trace.append(row)
        if on_transition is not None:
            on_transition(row)
        if transition_guard is not None:
            transition_guard(row)
        if terminated or truncated:
            break
    if (
        deadline_monotonic is not None
        and deadline_monotonic - time.monotonic() <= finalize_reserve_s
    ):
        raise LifetimeBudgetExceeded(
            "insufficient cap reserve for reference finalization"
        )
    raw = json_bytes(trace)
    return {
        "seed": SEED,
        "initial_state": START_OPTIONS,
        "configured_horizon": HORIZON,
        "planned_transitions": HORIZON,
        "planned_engine_steps": 0,
        "actual_engine_steps": 0,
        "transitions": len(trace),
        "terminated": bool(trace[-1]["terminated"]),
        "termination_reason": trace[-1]["termination_reason"]
        if trace[-1]["termination_reason"]
        else "D058_truncation_or_horizon",
        "charging_steps": sum(bool(row["contact"]) for row in trace),
        "charge_stored_energy_j": sum(
            float(row["charge_stored_energy_j"]) for row in trace
        ),
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
