"""D-020 V0.4 physical bookkeeping and fixed-action development probes.

This module is additive.  It deliberately does not call the historical
EXP-003 environment: that environment applies the abstract energy ledger, and
layering a physical ledger on top would double-count it.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any, Final, Mapping

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from .body import Body, Coordinate
from .env import Action
from .exp003 import (
    EXP003_BEACON_SCALE,
    EXP003_CHARGING_RADIUS,
    DirectionalBeacon,
    _charging_contact,
    sample_directional_beacon,
)

D020_PROBE_HORIZON: Final[int] = 30_000
D020_MIXED_ACTIONS: Final[tuple[Action, ...]] = (
    Action.WAIT,
    Action.TURN_LEFT,
    Action.TURN_RIGHT,
    Action.MOVE_FORWARD,
    Action.MOVE_FORWARD,
    Action.MOVE_FORWARD,
    Action.WAIT,
    Action.MOVE_FORWARD,
    Action.MOVE_FORWARD,
    Action.MOVE_FORWARD,
    Action.MOVE_FORWARD,
)


class ChargePhase(Enum):
    """Evaluator-side charger state for one transition."""

    OFF = "OFF"
    BULK = "BULK"
    TAPER_1 = "TAPER_1"
    TAPER_2 = "TAPER_2"
    STANDBY = "STANDBY"


class D020TerminationReason(Enum):
    """Evaluator-only reason classification with declared precedence."""

    EMERGENCY_HARD_THERMAL_SHUTDOWN = "EMERGENCY_HARD_THERMAL_SHUTDOWN"
    PROTECTIVE_THERMAL_SHUTDOWN = "PROTECTIVE_THERMAL_SHUTDOWN"
    ENERGY_DEPLETION = "ENERGY_DEPLETION"


@dataclass(frozen=True, slots=True)
class D020PhysicalConfig:
    """Frozen first-slice D-020 physical parameterization."""

    dt_seconds: float = 0.1
    world_scale_metres_per_unit: float = 1.0
    movement_distance_world_units: float = 0.05
    turn_angle: float = math.pi / 4.0
    world_min: Coordinate = (0.0, 0.0)
    world_max: Coordinate = (1.0, 1.0)
    charging_radius: float = EXP003_CHARGING_RADIUS
    beacon_scale: float = EXP003_BEACON_SCALE
    probe_distance: float = 0.1
    sensor_angle: float = math.pi / 4.0
    battery_capacity_j: float = 5328.0
    initial_battery_j: float = 2664.0
    electronics_electrical_power_w: float = 0.15
    electronics_body_heat_w: float = 0.15
    wait_actuator_electrical_power_w: float = 0.0
    move_actuator_electrical_power_w: float = 1.0
    turn_actuator_electrical_power_w: float = 0.65
    wait_actuator_body_heat_w: float = 0.0
    move_actuator_body_heat_w: float = 0.0
    turn_actuator_body_heat_w: float = 0.0
    charge_efficiency: float = 0.90
    bulk_charge_power_w: float = 1.85
    taper_1_charge_power_w: float = 0.925
    taper_2_charge_power_w: float = 0.37
    bulk_soc_upper: float = 0.90
    taper_1_soc_upper: float = 0.95
    resume_soc: float = 0.98
    thermal_capacitance_j_per_k: float = 180.0
    thermal_conductance_w_per_k: float = 0.25
    ambient_temperature_c: float = 23.0
    initial_body_temperature_c: float = 23.0
    preferred_operating_ceiling_c: float = 45.0
    protective_shutdown_c: float = 60.0
    hard_shutdown_c: float = 65.0
    visible_temperature_min_c: float = 0.0
    visible_temperature_max_c: float = 80.0
    episode_horizon: int = D020_PROBE_HORIZON

    def __post_init__(self) -> None:
        for name in (
            "dt_seconds",
            "world_scale_metres_per_unit",
            "battery_capacity_j",
            "initial_battery_j",
            "electronics_electrical_power_w",
            "electronics_body_heat_w",
            "wait_actuator_electrical_power_w",
            "move_actuator_electrical_power_w",
            "turn_actuator_electrical_power_w",
            "wait_actuator_body_heat_w",
            "move_actuator_body_heat_w",
            "turn_actuator_body_heat_w",
            "charge_efficiency",
            "bulk_charge_power_w",
            "taper_1_charge_power_w",
            "taper_2_charge_power_w",
            "thermal_capacitance_j_per_k",
            "thermal_conductance_w_per_k",
            "ambient_temperature_c",
            "initial_body_temperature_c",
            "preferred_operating_ceiling_c",
            "protective_shutdown_c",
            "hard_shutdown_c",
            "visible_temperature_min_c",
            "visible_temperature_max_c",
        ):
            _require_finite(name, getattr(self, name))
        _require_positive("dt_seconds", self.dt_seconds)
        _require_positive(
            "world_scale_metres_per_unit", self.world_scale_metres_per_unit
        )
        _require_positive("battery_capacity_j", self.battery_capacity_j)
        if not 0.0 <= self.initial_battery_j <= self.battery_capacity_j:
            raise ValueError("initial_battery_j must be within battery capacity")
        for name in (
            "electronics_electrical_power_w",
            "electronics_body_heat_w",
            "wait_actuator_electrical_power_w",
            "move_actuator_electrical_power_w",
            "turn_actuator_electrical_power_w",
            "wait_actuator_body_heat_w",
            "move_actuator_body_heat_w",
            "turn_actuator_body_heat_w",
            "bulk_charge_power_w",
            "taper_1_charge_power_w",
            "taper_2_charge_power_w",
            "thermal_conductance_w_per_k",
        ):
            _require_non_negative(name, getattr(self, name))
        if not 0.0 < self.charge_efficiency <= 1.0:
            raise ValueError("charge_efficiency must be in (0, 1]")
        for name in ("bulk_soc_upper", "taper_1_soc_upper", "resume_soc"):
            if not 0.0 < getattr(self, name) <= 1.0:
                raise ValueError(f"{name} must be in (0, 1]")
        if not self.bulk_soc_upper < self.taper_1_soc_upper <= 1.0:
            raise ValueError("SOC taper thresholds must be strictly ordered")
        if not self.taper_1_soc_upper < self.resume_soc <= 1.0:
            raise ValueError("resume_soc must exceed taper_1_soc_upper")
        _require_positive(
            "thermal_capacitance_j_per_k", self.thermal_capacitance_j_per_k
        )
        if not (
            self.preferred_operating_ceiling_c
            < self.protective_shutdown_c
            < self.hard_shutdown_c
        ):
            raise ValueError("thermal thresholds must be strictly ordered")
        if not self.visible_temperature_min_c < self.visible_temperature_max_c:
            raise ValueError("temperature normalization bounds must be ordered")
        _validate_bounds(self.world_min, self.world_max)
        _require_non_negative(
            "movement_distance_world_units", self.movement_distance_world_units
        )
        _require_non_negative("turn_angle", self.turn_angle)
        _require_non_negative("charging_radius", self.charging_radius)
        _require_positive("beacon_scale", self.beacon_scale)
        _require_non_negative("probe_distance", self.probe_distance)
        _require_non_negative("sensor_angle", self.sensor_angle)
        if (
            self.charging_radius
            > min(
                self.world_max[0] - self.world_min[0],
                self.world_max[1] - self.world_min[1],
            )
            / 2.0
        ):
            raise ValueError("charging_radius must fit inside the world")
        if (
            isinstance(self.episode_horizon, bool)
            or not isinstance(self.episode_horizon, int)
            or self.episode_horizon <= 0
        ):
            raise ValueError("episode_horizon must be a positive integer")


@dataclass(frozen=True, slots=True)
class D020Observation:
    """The six and only six organism-visible D-020 channels."""

    energy_normalized: float
    beacon_left: float
    beacon_forward: float
    beacon_right: float
    charging_contact: bool
    temperature_normalized: float

    def __post_init__(self) -> None:
        for name in (
            "energy_normalized",
            "beacon_left",
            "beacon_forward",
            "beacon_right",
            "temperature_normalized",
        ):
            value = getattr(self, name)
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be finite and within [0, 1]")
        if not isinstance(self.charging_contact, bool):
            raise ValueError("charging_contact must be a bool")

    def as_array(self) -> np.ndarray:
        """Return the Gymnasium observation without evaluator telemetry."""
        return np.asarray(
            (
                self.energy_normalized,
                self.beacon_left,
                self.beacon_forward,
                self.beacon_right,
                float(self.charging_contact),
                self.temperature_normalized,
            ),
            dtype=np.float32,
        )


@dataclass(frozen=True, slots=True)
class D020TransitionTelemetry:
    """Evaluator-only ledger and viability data for one transition."""

    step_index: int
    action: Action
    position_before: Coordinate
    position_after: Coordinate
    heading: float
    station_center: Coordinate
    battery_before_j: float
    battery_after_j: float
    energy_normalized_before: float
    energy_normalized_after: float
    body_temperature_before_c: float
    body_temperature_after_c: float
    temperature_normalized_before: float
    temperature_normalized_after: float
    charging_contact_before: bool
    charging_contact_after: bool
    electronics_electrical_power_w: float
    actuator_electrical_power_w: float
    total_electrical_load_w: float
    charge_phase: ChargePhase
    requested_stored_power_w: float
    actual_stored_power_w: float
    charger_input_power_w: float
    charging_body_heat_w: float
    electronics_body_heat_w: float
    actuator_body_heat_w: float
    total_body_heat_w: float
    environmental_exchange_power_w: float
    charger_termination_latched_after: bool
    preferred_ceiling_crossed: bool
    above_preferred_ceiling: bool
    energy_nonviable: bool
    protective_shutdown: bool
    emergency_hard_shutdown: bool
    terminated: bool
    truncated: bool
    termination_reason: D020TerminationReason | None


@dataclass(frozen=True, slots=True)
class _ChargeDecision:
    phase: ChargePhase
    requested_stored_power_w: float
    termination_latched_after: bool


class D020Env(gym.Env[np.ndarray, int]):
    """Minimal V0.4 physical bookkeeping environment for D-020."""

    metadata: dict[str, object] = {"render_modes": []}

    def __init__(self, config: D020PhysicalConfig | None = None) -> None:
        self.config = config or D020PhysicalConfig()
        self.action_space = spaces.Discrete(len(Action))
        self.observation_space = spaces.Box(
            low=np.zeros(6, dtype=np.float32),
            high=np.ones(6, dtype=np.float32),
            dtype=np.float32,
        )
        self.body: Body | None = None
        self.station_center: Coordinate | None = None
        self.body_temperature_c: float | None = None
        self._battery_j = 0.0
        self._charger_termination_latched = False
        self._step_count = 0
        self._episode_done = True
        self.last_transition: D020TransitionTelemetry | None = None

    @property
    def battery_j(self) -> float:
        """Evaluator-only current battery energy."""
        return self._battery_j

    @property
    def charging_contact(self) -> bool:
        """Return post-state contact from evaluator geometry."""
        if self.body is None or self.station_center is None:
            raise RuntimeError("environment must be reset before observing")
        return _charging_contact(
            self.body.position,
            self.station_center,
            self.config.charging_radius,
        )

    @property
    def charger_termination_latched(self) -> bool:
        """Return evaluator-side continuous-contact termination state."""
        return self._charger_termination_latched

    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict[str, object] | None = None,
    ) -> tuple[np.ndarray, dict[str, object]]:
        """Reset, accepting only explicit evaluator setup options.

        The options are evaluator inputs used by fixed-state probes; none are
        returned to the organism.  With no options, seeded deterministic body
        and station placement is used.
        """
        super().reset(seed=seed)
        setup = options or {}
        position = _coordinate_option(setup, "body_position", default=None)
        station = _coordinate_option(setup, "station_center", default=None)
        if position is None:
            position = (0.25, 0.25)
        if station is None:
            station = (0.75, 0.75)
        heading_value = setup.get("heading", 0.0)
        heading = _float_option("heading", heading_value)
        battery = _float_option(
            "battery_j", setup.get("battery_j", self.config.initial_battery_j)
        )
        temperature = _float_option(
            "body_temperature_c",
            setup.get("body_temperature_c", self.config.initial_body_temperature_c),
        )
        latched_value = setup.get("charger_termination_latched", False)
        if not isinstance(latched_value, bool):
            raise ValueError("charger_termination_latched must be a bool")
        if not 0.0 <= battery <= self.config.battery_capacity_j:
            raise ValueError("battery_j must be within battery capacity")
        self.body = Body(
            x=position[0],
            y=position[1],
            heading=heading,
            energy=0.0,
        )
        self.station_center = station
        self._battery_j = battery
        self.body_temperature_c = temperature
        self._charger_termination_latched = latched_value
        self._step_count = 0
        self._episode_done = False
        self.last_transition = None
        return self._observation().as_array(), {}

    def step(
        self, action: int
    ) -> tuple[np.ndarray, float, bool, bool, dict[str, object]]:
        """Apply one physical transition and return only ordinary observation."""
        if self._episode_done:
            raise RuntimeError("episode is over; call reset() before step()")
        if not self.action_space.contains(action):
            raise ValueError(f"action must be one of {list(Action)}")
        if (
            self.body is None
            or self.station_center is None
            or self.body_temperature_c is None
        ):
            raise RuntimeError("environment must be reset before step()")

        selected_action = Action(int(action))
        position_before = self.body.position
        battery_before = self._battery_j
        temperature_before = self.body_temperature_c
        contact_before = self.charging_contact
        energy_before = _normalize(battery_before, 0.0, self.config.battery_capacity_j)
        temperature_normalized_before = _normalize(
            temperature_before,
            self.config.visible_temperature_min_c,
            self.config.visible_temperature_max_c,
        )

        self._apply_action(selected_action)
        contact_after = self.charging_contact
        actuator_electrical = self._actuator_electrical_power(selected_action)
        actuator_body_heat = self._actuator_body_heat(selected_action)
        total_electrical = (
            self.config.electronics_electrical_power_w + actuator_electrical
        )
        load_energy = total_electrical * self.config.dt_seconds
        charge = self._charge_decision(contact_after, battery_before)
        requested_charge_energy = (
            charge.requested_stored_power_w * self.config.dt_seconds
        )
        max_accepted_charge_energy = max(
            0.0,
            self.config.battery_capacity_j - battery_before + load_energy,
        )
        actual_charge_energy = min(requested_charge_energy, max_accepted_charge_energy)
        actual_stored_power = actual_charge_energy / self.config.dt_seconds
        battery_after = min(
            self.config.battery_capacity_j,
            max(0.0, battery_before + actual_charge_energy - load_energy),
        )
        termination_latched_after = charge.termination_latched_after
        if (
            charge.phase
            in (
                ChargePhase.BULK,
                ChargePhase.TAPER_1,
                ChargePhase.TAPER_2,
            )
            and battery_after >= self.config.battery_capacity_j
        ):
            termination_latched_after = True

        charger_input = (
            actual_stored_power / self.config.charge_efficiency
            if actual_stored_power > 0.0
            else 0.0
        )
        charging_heat = (
            charger_input - actual_stored_power if actual_stored_power > 0.0 else 0.0
        )
        total_body_heat = (
            self.config.electronics_body_heat_w + actuator_body_heat + charging_heat
        )
        environmental_exchange = self.config.thermal_conductance_w_per_k * (
            self.config.ambient_temperature_c - temperature_before
        )
        temperature_after = temperature_before + (
            self.config.dt_seconds
            * (total_body_heat + environmental_exchange)
            / self.config.thermal_capacitance_j_per_k
        )
        self._battery_j = battery_after
        self.body_temperature_c = temperature_after
        self._charger_termination_latched = termination_latched_after
        energy_nonviable = battery_after <= 0.0
        protective = (
            temperature_after >= self.config.protective_shutdown_c
            and temperature_after < self.config.hard_shutdown_c
        )
        emergency = temperature_after >= self.config.hard_shutdown_c
        reason = _termination_reason(
            emergency=emergency,
            protective=protective,
            energy_nonviable=energy_nonviable,
        )
        terminated = reason is not None
        self._step_count += 1
        truncated = not terminated and self._step_count >= self.config.episode_horizon
        self._episode_done = terminated or truncated
        energy_after = _normalize(battery_after, 0.0, self.config.battery_capacity_j)
        temperature_normalized_after = _normalize(
            temperature_after,
            self.config.visible_temperature_min_c,
            self.config.visible_temperature_max_c,
        )
        self.last_transition = D020TransitionTelemetry(
            step_index=self._step_count,
            action=selected_action,
            position_before=position_before,
            position_after=self.body.position,
            heading=self.body.heading,
            station_center=self.station_center,
            battery_before_j=battery_before,
            battery_after_j=battery_after,
            energy_normalized_before=energy_before,
            energy_normalized_after=energy_after,
            body_temperature_before_c=temperature_before,
            body_temperature_after_c=temperature_after,
            temperature_normalized_before=temperature_normalized_before,
            temperature_normalized_after=temperature_normalized_after,
            charging_contact_before=contact_before,
            charging_contact_after=contact_after,
            electronics_electrical_power_w=self.config.electronics_electrical_power_w,
            actuator_electrical_power_w=actuator_electrical,
            total_electrical_load_w=total_electrical,
            charge_phase=charge.phase,
            requested_stored_power_w=charge.requested_stored_power_w,
            actual_stored_power_w=actual_stored_power,
            charger_input_power_w=charger_input,
            charging_body_heat_w=charging_heat,
            electronics_body_heat_w=self.config.electronics_body_heat_w,
            actuator_body_heat_w=actuator_body_heat,
            total_body_heat_w=total_body_heat,
            environmental_exchange_power_w=environmental_exchange,
            charger_termination_latched_after=termination_latched_after,
            preferred_ceiling_crossed=(
                temperature_before
                < self.config.preferred_operating_ceiling_c
                <= temperature_after
            ),
            above_preferred_ceiling=temperature_after
            >= self.config.preferred_operating_ceiling_c,
            energy_nonviable=energy_nonviable,
            protective_shutdown=protective,
            emergency_hard_shutdown=emergency,
            terminated=terminated,
            truncated=truncated,
            termination_reason=reason,
        )
        return self._observation().as_array(), 0.0, terminated, truncated, {}

    def _apply_action(self, action: Action) -> None:
        if self.body is None:
            raise RuntimeError("environment must be reset before acting")
        if action is Action.TURN_LEFT:
            self.body.turn(self.config.turn_angle)
        elif action is Action.TURN_RIGHT:
            self.body.turn(-self.config.turn_angle)
        elif action is Action.MOVE_FORWARD:
            self.body.move_forward(
                self.config.movement_distance_world_units,
                world_min=self.config.world_min,
                world_max=self.config.world_max,
            )

    def _actuator_electrical_power(self, action: Action) -> float:
        if action is Action.MOVE_FORWARD:
            return self.config.move_actuator_electrical_power_w
        if action in (Action.TURN_LEFT, Action.TURN_RIGHT):
            return self.config.turn_actuator_electrical_power_w
        return self.config.wait_actuator_electrical_power_w

    def _actuator_body_heat(self, action: Action) -> float:
        if action is Action.MOVE_FORWARD:
            return self.config.move_actuator_body_heat_w
        if action in (Action.TURN_LEFT, Action.TURN_RIGHT):
            return self.config.turn_actuator_body_heat_w
        return self.config.wait_actuator_body_heat_w

    def _charge_decision(
        self, contact_after: bool, battery_before: float
    ) -> _ChargeDecision:
        if not contact_after:
            return _ChargeDecision(ChargePhase.OFF, 0.0, False)
        soc = battery_before / self.config.battery_capacity_j
        if self._charger_termination_latched:
            if soc > self.config.resume_soc:
                return _ChargeDecision(ChargePhase.STANDBY, 0.0, True)
            self._charger_termination_latched = False
        if battery_before >= self.config.battery_capacity_j:
            return _ChargeDecision(ChargePhase.STANDBY, 0.0, True)
        if soc < self.config.bulk_soc_upper:
            return _ChargeDecision(
                ChargePhase.BULK, self.config.bulk_charge_power_w, False
            )
        if soc < self.config.taper_1_soc_upper:
            return _ChargeDecision(
                ChargePhase.TAPER_1, self.config.taper_1_charge_power_w, False
            )
        return _ChargeDecision(
            ChargePhase.TAPER_2, self.config.taper_2_charge_power_w, False
        )

    def _observation(self) -> D020Observation:
        if (
            self.body is None
            or self.station_center is None
            or self.body_temperature_c is None
        ):
            raise RuntimeError("environment must be reset before observing")
        beacon: DirectionalBeacon = sample_directional_beacon(
            self.body,
            self.station_center,
            probe_distance=self.config.probe_distance,
            sensor_angle=self.config.sensor_angle,
            beacon_scale=self.config.beacon_scale,
        )
        return D020Observation(
            energy_normalized=_normalize(
                self._battery_j, 0.0, self.config.battery_capacity_j
            ),
            beacon_left=beacon.left,
            beacon_forward=beacon.forward,
            beacon_right=beacon.right,
            charging_contact=self.charging_contact,
            temperature_normalized=_normalize(
                self.body_temperature_c,
                self.config.visible_temperature_min_c,
                self.config.visible_temperature_max_c,
            ),
        )


@dataclass(frozen=True, slots=True)
class D020ProbeResult:
    """Machine-readable descriptive result for one fixed-action probe."""

    name: str
    seed_status: str
    transitions: int
    physical_seconds: float
    battery_start_j: float
    battery_end_j: float
    battery_min_j: float
    battery_max_j: float
    energy_normalized_start: float
    energy_normalized_end: float
    energy_normalized_min: float
    energy_normalized_max: float
    body_temperature_start_c: float
    body_temperature_end_c: float
    body_temperature_min_c: float
    body_temperature_max_c: float
    temperature_normalized_start: float
    temperature_normalized_end: float
    temperature_normalized_min: float
    temperature_normalized_max: float
    preferred_ceiling_reached: bool
    protective_shutdown: bool
    emergency_hard_shutdown: bool
    termination_reason: str | None
    charge_phase_counts: dict[str, int]
    first_phase_steps: dict[str, int | None]
    first_full_latch_step: int | None
    cumulative_actual_stored_energy_j: float
    cumulative_requested_stored_energy_j: float
    cumulative_charger_input_energy_j: float
    cumulative_charging_loss_heat_energy_j: float
    cumulative_electronics_electrical_energy_j: float
    cumulative_actuator_electrical_energy_j: float
    cumulative_electronics_body_heat_energy_j: float
    cumulative_environmental_exchange_energy_j: float
    headroom_limited_charge_event_count: int
    charging_heat_zero_after_termination: bool
    no_charging_occurred: bool
    boundary_clamped_transition_count: int
    limitation: str | None = None
    transitions_table: tuple[dict[str, object], ...] = ()


def run_d020_probe_suite() -> dict[str, object]:
    """Run the three predeclared seedless fixed-state D-020 probes."""
    config = D020PhysicalConfig()
    docked = _run_fixed_probe(
        "DOCKED_WAIT_CHARGE",
        config,
        options={
            "body_position": (0.5, 0.5),
            "station_center": (0.5, 0.5),
            "heading": 0.0,
            "battery_j": config.initial_battery_j,
            "body_temperature_c": config.initial_body_temperature_c,
        },
        action_policy=lambda _step: Action.WAIT,
    )
    off_dock = _run_fixed_probe(
        "OFF_DOCK_MOVE_ENERGY",
        config,
        options={
            "body_position": (0.1, 0.1),
            "station_center": (0.9, 0.9),
            "heading": 0.0,
            "battery_j": config.initial_battery_j,
            "body_temperature_c": config.initial_body_temperature_c,
        },
        action_policy=lambda _step: Action.MOVE_FORWARD,
        limitation=(
            "The repeated MOVE command keeps incurring a fixed action-class "
            "electrical load after the body reaches the world boundary; this "
            "is not realistic wheel or motor mechanics."
        ),
    )
    mixed = _run_fixed_probe(
        "MIXED_ACTION_CAUSAL_ACCOUNTING",
        config,
        options={
            "body_position": (0.26, 0.5),
            "station_center": (0.5, 0.5),
            "heading": 0.0,
            "battery_j": config.initial_battery_j,
            "body_temperature_c": config.initial_body_temperature_c,
        },
        action_policy=lambda step: D020_MIXED_ACTIONS[step],
        horizon=len(D020_MIXED_ACTIONS),
    )
    return {
        "identifier": "D-020",
        "lane": "Development",
        "seed_status": "seedless fixed-state evaluator probes",
        "config": _config_record(config),
        "probes": {
            "DOCKED_WAIT_CHARGE": asdict(docked),
            "OFF_DOCK_MOVE_ENERGY": asdict(off_dock),
            "MIXED_ACTION_CAUSAL_ACCOUNTING": asdict(mixed),
        },
    }


def write_d020_probe_json(path: Path) -> Path:
    """Run the frozen suite and write a deterministic JSON artifact."""
    payload = run_d020_probe_suite()
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=_json_default) + "\n",
        encoding="utf-8",
    )
    return path


def _run_fixed_probe(
    name: str,
    config: D020PhysicalConfig,
    *,
    options: dict[str, object],
    action_policy: Any,
    horizon: int | None = None,
    limitation: str | None = None,
) -> D020ProbeResult:
    probe_config = (
        config if horizon is None else replace(config, episode_horizon=horizon)
    )
    environment = D020Env(probe_config)
    environment.reset(options=options)
    battery_start = environment.battery_j
    temperature_start = environment.body_temperature_c
    if temperature_start is None:
        raise RuntimeError("probe reset did not initialize temperature")
    observations = [environment._observation()]
    telemetry: list[D020TransitionTelemetry] = []
    terminated = False
    truncated = False
    while not (terminated or truncated):
        action = action_policy(len(telemetry))
        _, reward, terminated, truncated, info = environment.step(action)
        if reward != 0.0 or info != {}:
            raise RuntimeError("D-020 reward or info crossed the organism boundary")
        if environment.last_transition is None:
            raise RuntimeError("D-020 transition telemetry is unavailable")
        telemetry.append(environment.last_transition)
        observations.append(environment._observation())
    if environment.body_temperature_c is None:
        raise RuntimeError("probe ended without temperature")
    all_battery = [battery_start, *(item.battery_after_j for item in telemetry)]
    all_energy = [item.energy_normalized_before for item in telemetry]
    all_energy.extend(item.energy_normalized_after for item in telemetry[-1:])
    all_temperature = [
        temperature_start,
        *(item.body_temperature_after_c for item in telemetry),
    ]
    all_temperature_normalized = [
        _normalize(
            value,
            config.visible_temperature_min_c,
            config.visible_temperature_max_c,
        )
        for value in all_temperature
    ]
    phase_counts = {phase.value: 0 for phase in ChargePhase}
    first_phase_steps: dict[str, int | None] = {
        phase.value: None for phase in ChargePhase
    }
    first_latch: int | None = None
    headroom_events = 0
    charging_heat_zero_after_termination = True
    for item in telemetry:
        phase_counts[item.charge_phase.value] += 1
        if first_phase_steps[item.charge_phase.value] is None:
            first_phase_steps[item.charge_phase.value] = item.step_index
        if item.charger_termination_latched_after and first_latch is None:
            first_latch = item.step_index
        requested_energy = item.requested_stored_power_w * config.dt_seconds
        actual_energy = item.actual_stored_power_w * config.dt_seconds
        if actual_energy + 1e-12 < requested_energy:
            headroom_events += 1
        if (
            first_latch is not None
            and item.step_index > first_latch
            and item.charging_body_heat_w != 0.0
        ):
            charging_heat_zero_after_termination = False
    table = tuple(_telemetry_table_row(item) for item in telemetry)
    return D020ProbeResult(
        name=name,
        seed_status="seedless fixed-state evaluator probe",
        transitions=len(telemetry),
        physical_seconds=len(telemetry) * config.dt_seconds,
        battery_start_j=battery_start,
        battery_end_j=environment.battery_j,
        battery_min_j=min(all_battery),
        battery_max_j=max(all_battery),
        energy_normalized_start=all_energy[0],
        energy_normalized_end=all_energy[-1],
        energy_normalized_min=min(all_energy),
        energy_normalized_max=max(all_energy),
        body_temperature_start_c=temperature_start,
        body_temperature_end_c=environment.body_temperature_c,
        body_temperature_min_c=min(all_temperature),
        body_temperature_max_c=max(all_temperature),
        temperature_normalized_start=all_temperature_normalized[0],
        temperature_normalized_end=all_temperature_normalized[-1],
        temperature_normalized_min=min(all_temperature_normalized),
        temperature_normalized_max=max(all_temperature_normalized),
        preferred_ceiling_reached=any(
            item.above_preferred_ceiling for item in telemetry
        ),
        protective_shutdown=any(item.protective_shutdown for item in telemetry),
        emergency_hard_shutdown=any(item.emergency_hard_shutdown for item in telemetry),
        termination_reason=(
            telemetry[-1].termination_reason.value
            if telemetry[-1].termination_reason is not None
            else None
        ),
        charge_phase_counts=phase_counts,
        first_phase_steps=first_phase_steps,
        first_full_latch_step=first_latch,
        cumulative_actual_stored_energy_j=sum(
            item.actual_stored_power_w * config.dt_seconds for item in telemetry
        ),
        cumulative_requested_stored_energy_j=sum(
            item.requested_stored_power_w * config.dt_seconds for item in telemetry
        ),
        cumulative_charger_input_energy_j=sum(
            item.charger_input_power_w * config.dt_seconds for item in telemetry
        ),
        cumulative_charging_loss_heat_energy_j=sum(
            item.charging_body_heat_w * config.dt_seconds for item in telemetry
        ),
        cumulative_electronics_electrical_energy_j=sum(
            item.electronics_electrical_power_w * config.dt_seconds
            for item in telemetry
        ),
        cumulative_actuator_electrical_energy_j=sum(
            item.actuator_electrical_power_w * config.dt_seconds for item in telemetry
        ),
        cumulative_electronics_body_heat_energy_j=sum(
            item.electronics_body_heat_w * config.dt_seconds for item in telemetry
        ),
        cumulative_environmental_exchange_energy_j=sum(
            item.environmental_exchange_power_w * config.dt_seconds
            for item in telemetry
        ),
        headroom_limited_charge_event_count=headroom_events,
        charging_heat_zero_after_termination=charging_heat_zero_after_termination,
        no_charging_occurred=all(
            item.actual_stored_power_w == 0.0 for item in telemetry
        ),
        boundary_clamped_transition_count=sum(
            item.position_after == item.position_before
            and item.action is Action.MOVE_FORWARD
            for item in telemetry
        ),
        limitation=limitation,
        transitions_table=table,
    )


def classify_thermal_safety(
    temperature_c: float,
    config: D020PhysicalConfig | None = None,
) -> tuple[bool, bool, D020TerminationReason | None]:
    """Classify evaluator thermal safety using 65 °C before 60 °C."""
    selected = config or D020PhysicalConfig()
    _require_finite("temperature_c", temperature_c)
    emergency = temperature_c >= selected.hard_shutdown_c
    protective = temperature_c >= selected.protective_shutdown_c and not emergency
    reason = _termination_reason(
        emergency=emergency, protective=protective, energy_nonviable=False
    )
    return protective, emergency, reason


def _termination_reason(
    *, emergency: bool, protective: bool, energy_nonviable: bool
) -> D020TerminationReason | None:
    if emergency:
        return D020TerminationReason.EMERGENCY_HARD_THERMAL_SHUTDOWN
    if protective:
        return D020TerminationReason.PROTECTIVE_THERMAL_SHUTDOWN
    if energy_nonviable:
        return D020TerminationReason.ENERGY_DEPLETION
    return None


def _config_kwargs(config: D020PhysicalConfig) -> dict[str, object]:
    return {
        item.name: getattr(config, item.name)
        for item in config.__dataclass_fields__.values()
    }


def _config_record(config: D020PhysicalConfig) -> dict[str, object]:
    values = _config_kwargs(config)
    values["provenance"] = {
        "dt_seconds": "DESIGN CHOICE / PROVISIONAL PHYSICALIZATION",
        "world_scale_metres_per_unit": "DESIGN CHOICE / PROVISIONAL PHYSICALIZATION",
        "movement_distance_world_units": (
            "HISTORICAL SEMANTICS + PROVISIONAL PHYSICAL MAPPING"
        ),
        "battery_capacity_j": (
            "DERIVED from 3.7 V * 0.500 Ah * 3600 * 0.80; "
            "engineering estimate for usable fraction"
        ),
        "initial_battery_j": "DESIGN CHOICE",
        "electronics_electrical_power_w": "ENGINEERING ESTIMATE",
        "electronics_body_heat_w": (
            "ENGINEERING ESTIMATE / first lumped radio-disabled "
            "local-heat approximation"
        ),
        "actuator_electrical_power_w": "ACTION SEMANTICS / engineering estimate",
        "actuator_body_heat_w": (
            "LOWER-BOUND SENSITIVITY ASSUMPTION / UNKNOWN — NEEDS MEASUREMENT"
        ),
        "charge_efficiency": "ENGINEERING ESTIMATE",
        "charge_taper_and_restart": "DESIGN CHOICE / first-slice simple SOC rule",
        "thermal_capacitance_j_per_k": (
            "ENGINEERING ESTIMATE / D-019 illustrative centre"
        ),
        "thermal_conductance_w_per_k": "ENGINEERING ESTIMATE / D-019 candidate centre",
        "ambient_temperature_c": "DESIGN CHOICE / evaluator-only",
        "initial_body_temperature_c": "DESIGN CHOICE",
        "preferred_operating_ceiling_c": (
            "ADR 0014 / conservative preferred operating ceiling"
        ),
        "protective_shutdown_c": "ADR 0014 / protective simulator thermal shutdown",
        "hard_shutdown_c": "ADR 0014 / emergency hard simulator shutdown",
        "visible_temperature_bounds": (
            "ADR 0014 / fixed first-slice normalization bounds"
        ),
    }
    return values


def _telemetry_table_row(item: D020TransitionTelemetry) -> dict[str, object]:
    return {
        "step": item.step_index,
        "action": item.action.name,
        "position_before": list(item.position_before),
        "position_after": list(item.position_after),
        "charging_contact_before": item.charging_contact_before,
        "charging_contact_after": item.charging_contact_after,
        "battery_before_j": item.battery_before_j,
        "battery_after_j": item.battery_after_j,
        "charge_phase": item.charge_phase.value,
        "requested_stored_power_w": item.requested_stored_power_w,
        "actual_stored_power_w": item.actual_stored_power_w,
        "charging_body_heat_w": item.charging_body_heat_w,
        "body_temperature_after_c": item.body_temperature_after_c,
    }


def _json_default(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    raise TypeError(f"cannot serialize {type(value).__name__}")


def _normalize(value: float, lower: float, upper: float) -> float:
    return min(1.0, max(0.0, (value - lower) / (upper - lower)))


def _coordinate_option(
    options: Mapping[str, object], name: str, *, default: Coordinate | None
) -> Coordinate | None:
    value = options.get(name, default)
    if value is None:
        return None
    if not isinstance(value, tuple) or len(value) != 2:
        raise ValueError(f"{name} must be a two-item tuple")
    coordinate = (float(value[0]), float(value[1]))
    _validate_coordinate(name, coordinate)
    return coordinate


def _float_option(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    _require_finite(name, result)
    return result


def _validate_bounds(world_min: Coordinate, world_max: Coordinate) -> None:
    _validate_coordinate("world_min", world_min)
    _validate_coordinate("world_max", world_max)
    if not all(lower < upper for lower, upper in zip(world_min, world_max)):
        raise ValueError("world_min must be strictly below world_max")


def _validate_coordinate(name: str, coordinate: Coordinate) -> None:
    if len(coordinate) != 2 or not all(math.isfinite(value) for value in coordinate):
        raise ValueError(f"{name} must contain two finite coordinates")


def _require_finite(name: str, value: float) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


def _require_positive(name: str, value: float) -> None:
    _require_finite(name, value)
    if value <= 0.0:
        raise ValueError(f"{name} must be positive")


def _require_non_negative(name: str, value: float) -> None:
    _require_finite(name, value)
    if value < 0.0:
        raise ValueError(f"{name} must be non-negative")


def main() -> None:
    """Generate the frozen D-020 machine-readable probe artifact."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_d020_probe_json(args.output)


if __name__ == "__main__":
    main()
