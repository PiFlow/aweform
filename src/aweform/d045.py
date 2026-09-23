"""D-045 deterministic V0.5 embodiment and bookkeeping probe.

This module is intentionally additive.  It is an evaluator-scripted physical
substrate only: it contains no controller, learner, calibration routine, or
organism-side action selection.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Final, SupportsFloat, cast

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from .body import Body, Coordinate
from .exp003 import sample_directional_beacon

D045_DT_SECONDS: Final[float] = 0.1
D045_WHEEL_TRACK_WIDTH_METRES: Final[float] = 0.185
D045_WHEEL_RADIUS_METRES: Final[float] = 0.045
D045_MAX_WHEEL_DELTA_RAD: Final[float] = 0.6457718232379019
D045_ENCODER_QUANTUM_RAD: Final[float] = math.pi / 180.0
D045_CONTACT_OFFSET_METRES: Final[float] = 0.05
D045_CONTACT_TOLERANCE_METRES: Final[float] = 0.01
D045_BEACON_SCALE_METRES: Final[float] = 0.25
D045_BEACON_PROBE_DISTANCE_METRES: Final[float] = 0.1
D045_BEACON_SENSOR_ANGLE_RAD: Final[float] = math.pi / 4.0
D045_BATTERY_CAPACITY_J: Final[float] = 5328.0
D045_INITIAL_BATTERY_J: Final[float] = 2664.0
D045_ELECTRONICS_POWER_W: Final[float] = 0.15
D045_ELECTRONICS_BODY_HEAT_W: Final[float] = 0.15
D045_WHEEL_POWER_SCALE_W: Final[float] = 1.0
D045_WHEEL_BODY_HEAT_SCALE_W: Final[float] = 0.0
D045_CHARGE_EFFICIENCY: Final[float] = 0.90
D045_THERMAL_CAPACITANCE_J_PER_K: Final[float] = 180.0
D045_THERMAL_CONDUCTANCE_W_PER_K: Final[float] = 0.25
D045_AMBIENT_TEMPERATURE_C: Final[float] = 23.0
D045_VISIBLE_TEMPERATURE_MIN_C: Final[float] = 0.0
D045_VISIBLE_TEMPERATURE_MAX_C: Final[float] = 80.0
D045_PREFERRED_TEMPERATURE_C: Final[float] = 45.0
D045_PROTECTIVE_TEMPERATURE_C: Final[float] = 60.0
D045_HARD_TEMPERATURE_C: Final[float] = 65.0
D045_WORLD_MIN: Final[Coordinate] = (0.0, 0.0)
D045_WORLD_MAX: Final[Coordinate] = (1.0, 1.0)
D045_CHARGE_BULK_POWER_W: Final[float] = 1.85
D045_CHARGE_TAPER_1_POWER_W: Final[float] = 0.925
D045_CHARGE_TAPER_2_POWER_W: Final[float] = 0.37
D045_CHARGE_BULK_SOC_UPPER: Final[float] = 0.90
D045_CHARGE_TAPER_1_SOC_UPPER: Final[float] = 0.95
D045_CHARGE_RESUME_SOC: Final[float] = 0.98
D045_PROBE_HORIZON: Final[int] = 30_000
_BOUNDARY_BISECTION_ITERATIONS: Final[int] = 64
_STRAIGHT_EPSILON: Final[float] = 1e-12


class D045ChargePhase(Enum):
    """Evaluator-side retained charger state."""

    OFF = "OFF"
    BULK = "BULK"
    TAPER_1 = "TAPER_1"
    TAPER_2 = "TAPER_2"
    STANDBY = "STANDBY"


class D045TerminationReason(Enum):
    """Evaluator-only termination precedence."""

    EMERGENCY_HARD_THERMAL_SHUTDOWN = "EMERGENCY_HARD_THERMAL_SHUTDOWN"
    PROTECTIVE_THERMAL_SHUTDOWN = "PROTECTIVE_THERMAL_SHUTDOWN"
    ENERGY_DEPLETION = "ENERGY_DEPLETION"


@dataclass(frozen=True, slots=True)
class D045PhysicalConfig:
    """Frozen D-045 physical parameterization."""

    dt_seconds: float = D045_DT_SECONDS
    world_min: Coordinate = D045_WORLD_MIN
    world_max: Coordinate = D045_WORLD_MAX
    wheel_track_width_m: float = D045_WHEEL_TRACK_WIDTH_METRES
    wheel_radius_m: float = D045_WHEEL_RADIUS_METRES
    max_wheel_delta_rad: float = D045_MAX_WHEEL_DELTA_RAD
    encoder_quantum_rad: float = D045_ENCODER_QUANTUM_RAD
    contact_offset_m: float = D045_CONTACT_OFFSET_METRES
    contact_tolerance_m: float = D045_CONTACT_TOLERANCE_METRES
    beacon_scale_m: float = D045_BEACON_SCALE_METRES
    beacon_probe_distance_m: float = D045_BEACON_PROBE_DISTANCE_METRES
    beacon_sensor_angle_rad: float = D045_BEACON_SENSOR_ANGLE_RAD
    battery_capacity_j: float = D045_BATTERY_CAPACITY_J
    initial_battery_j: float = D045_INITIAL_BATTERY_J
    electronics_power_w: float = D045_ELECTRONICS_POWER_W
    electronics_body_heat_w: float = D045_ELECTRONICS_BODY_HEAT_W
    wheel_power_scale_w: float = D045_WHEEL_POWER_SCALE_W
    wheel_body_heat_scale_w: float = D045_WHEEL_BODY_HEAT_SCALE_W
    charge_efficiency: float = D045_CHARGE_EFFICIENCY
    bulk_charge_power_w: float = D045_CHARGE_BULK_POWER_W
    taper_1_charge_power_w: float = D045_CHARGE_TAPER_1_POWER_W
    taper_2_charge_power_w: float = D045_CHARGE_TAPER_2_POWER_W
    bulk_soc_upper: float = D045_CHARGE_BULK_SOC_UPPER
    taper_1_soc_upper: float = D045_CHARGE_TAPER_1_SOC_UPPER
    resume_soc: float = D045_CHARGE_RESUME_SOC
    thermal_capacitance_j_per_k: float = D045_THERMAL_CAPACITANCE_J_PER_K
    thermal_conductance_w_per_k: float = D045_THERMAL_CONDUCTANCE_W_PER_K
    ambient_temperature_c: float = D045_AMBIENT_TEMPERATURE_C
    initial_body_temperature_c: float = D045_AMBIENT_TEMPERATURE_C
    preferred_temperature_c: float = D045_PREFERRED_TEMPERATURE_C
    protective_temperature_c: float = D045_PROTECTIVE_TEMPERATURE_C
    hard_temperature_c: float = D045_HARD_TEMPERATURE_C
    visible_temperature_min_c: float = D045_VISIBLE_TEMPERATURE_MIN_C
    visible_temperature_max_c: float = D045_VISIBLE_TEMPERATURE_MAX_C
    episode_horizon: int = D045_PROBE_HORIZON

    def __post_init__(self) -> None:
        for name in (
            "dt_seconds",
            "wheel_track_width_m",
            "wheel_radius_m",
            "max_wheel_delta_rad",
            "encoder_quantum_rad",
            "contact_offset_m",
            "contact_tolerance_m",
            "beacon_scale_m",
            "beacon_probe_distance_m",
            "beacon_sensor_angle_rad",
            "battery_capacity_j",
            "initial_battery_j",
            "electronics_power_w",
            "electronics_body_heat_w",
            "wheel_power_scale_w",
            "wheel_body_heat_scale_w",
            "charge_efficiency",
            "bulk_charge_power_w",
            "taper_1_charge_power_w",
            "taper_2_charge_power_w",
            "thermal_capacitance_j_per_k",
            "thermal_conductance_w_per_k",
            "ambient_temperature_c",
            "initial_body_temperature_c",
            "preferred_temperature_c",
            "protective_temperature_c",
            "hard_temperature_c",
            "visible_temperature_min_c",
            "visible_temperature_max_c",
        ):
            _require_finite(name, getattr(self, name))
        for name in (
            "dt_seconds",
            "wheel_track_width_m",
            "wheel_radius_m",
            "max_wheel_delta_rad",
            "encoder_quantum_rad",
            "beacon_scale_m",
            "thermal_capacitance_j_per_k",
        ):
            _require_positive(name, getattr(self, name))
        if not 0.0 <= self.initial_battery_j <= self.battery_capacity_j:
            raise ValueError("initial_battery_j must be within battery capacity")
        if self.battery_capacity_j <= 0.0:
            raise ValueError("battery_capacity_j must be positive")
        if not 0.0 < self.charge_efficiency <= 1.0:
            raise ValueError("charge_efficiency must be in (0, 1]")
        for name in (
            "electronics_power_w",
            "electronics_body_heat_w",
            "wheel_power_scale_w",
            "wheel_body_heat_scale_w",
            "bulk_charge_power_w",
            "taper_1_charge_power_w",
            "taper_2_charge_power_w",
            "thermal_conductance_w_per_k",
            "contact_offset_m",
            "contact_tolerance_m",
            "beacon_probe_distance_m",
        ):
            _require_non_negative(name, getattr(self, name))
        if (
            not 0.0
            < self.bulk_soc_upper
            < self.taper_1_soc_upper
            < self.resume_soc
            <= 1.0
        ):
            raise ValueError("charger SOC thresholds must be strictly ordered")
        if not (
            self.preferred_temperature_c
            < self.protective_temperature_c
            < self.hard_temperature_c
        ):
            raise ValueError("thermal thresholds must be strictly ordered")
        if not self.visible_temperature_min_c < self.visible_temperature_max_c:
            raise ValueError("visible temperature bounds must be ordered")
        _validate_bounds(self.world_min, self.world_max)
        if (
            isinstance(self.episode_horizon, bool)
            or not isinstance(self.episode_horizon, int)
            or self.episode_horizon <= 0
        ):
            raise ValueError("episode_horizon must be a positive integer")


@dataclass(frozen=True, slots=True)
class D045Observation:
    """The exact eight organism-visible channels, in boundary order."""

    energy_normalized: float
    temperature_normalized: float
    beacon_left: float
    beacon_forward: float
    beacon_right: float
    charging_contact: bool
    wheel_delta_left: float
    wheel_delta_right: float

    def __post_init__(self) -> None:
        for name in (
            "energy_normalized",
            "temperature_normalized",
            "beacon_left",
            "beacon_forward",
            "beacon_right",
        ):
            value = getattr(self, name)
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be finite and within [0, 1]")
        if not isinstance(self.charging_contact, bool):
            raise ValueError("charging_contact must be a bool")
        for name in ("wheel_delta_left", "wheel_delta_right"):
            if not math.isfinite(getattr(self, name)):
                raise ValueError(f"{name} must be finite")

    def as_array(self) -> np.ndarray:
        """Return only the eight organism-visible numeric channels."""
        return np.asarray(
            (
                self.energy_normalized,
                self.temperature_normalized,
                self.beacon_left,
                self.beacon_forward,
                self.beacon_right,
                float(self.charging_contact),
                self.wheel_delta_left,
                self.wheel_delta_right,
            ),
            dtype=np.float32,
        )


@dataclass(frozen=True, slots=True)
class D045TransitionTelemetry:
    """Evaluator-only data for one completed transition."""

    step_index: int
    requested_delta_left: float
    requested_delta_right: float
    clamped_delta_left: float
    clamped_delta_right: float
    actual_delta_left: float
    actual_delta_right: float
    boundary_scale: float
    position_before: Coordinate
    position_after: Coordinate
    heading_before: float
    heading_after: float
    station_center: Coordinate
    charging_contact_before: bool
    charging_contact_after: bool
    dock_plus_error_m: float
    dock_minus_error_m: float
    battery_before_j: float
    battery_after_j: float
    body_temperature_before_c: float
    body_temperature_after_c: float
    actuator_electrical_power_w: float
    electronics_electrical_power_w: float
    total_electrical_load_w: float
    charge_phase: D045ChargePhase
    requested_stored_power_w: float
    actual_stored_power_w: float
    charger_input_power_w: float
    charging_body_heat_w: float
    actuator_body_heat_w: float
    electronics_body_heat_w: float
    environmental_exchange_power_w: float
    charger_termination_latched_after: bool
    preferred_ceiling_crossed: bool
    above_preferred_ceiling: bool
    energy_nonviable: bool
    protective_shutdown: bool
    emergency_hard_shutdown: bool
    terminated: bool
    truncated: bool
    termination_reason: D045TerminationReason | None


@dataclass(frozen=True, slots=True)
class _ChargeDecision:
    phase: D045ChargePhase
    requested_stored_power_w: float
    termination_latched_after: bool


class D045Env(gym.Env[np.ndarray, np.ndarray]):
    """Deterministic V0.5 body with evaluator-only physical telemetry."""

    metadata: dict[str, object] = {"render_modes": []}

    def __init__(self, config: D045PhysicalConfig | None = None) -> None:
        self.config = config or D045PhysicalConfig()
        wheel_low = np.full(2, -self.config.max_wheel_delta_rad, dtype=np.float64)
        wheel_high = np.full(2, self.config.max_wheel_delta_rad, dtype=np.float64)
        self.action_space = spaces.Box(low=wheel_low, high=wheel_high, dtype=np.float64)
        observation_low = np.asarray(
            (
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                -self.config.max_wheel_delta_rad,
                -self.config.max_wheel_delta_rad,
            ),
            dtype=np.float32,
        )
        observation_high = np.asarray(
            (
                1.0,
                1.0,
                1.0,
                1.0,
                1.0,
                1.0,
                self.config.max_wheel_delta_rad,
                self.config.max_wheel_delta_rad,
            ),
            dtype=np.float32,
        )
        self.observation_space = spaces.Box(
            low=observation_low, high=observation_high, dtype=np.float32
        )
        self.body: Body | None = None
        self.station_center: Coordinate | None = None
        self.body_temperature_c: float | None = None
        self._battery_j = 0.0
        self._charger_termination_latched = False
        self._previous_wheel_delta = (0.0, 0.0)
        self._step_count = 0
        self._episode_done = True
        self.last_transition: D045TransitionTelemetry | None = None

    @property
    def battery_j(self) -> float:
        """Evaluator-only current battery energy."""
        return self._battery_j

    @property
    def charging_contact(self) -> bool:
        """Return the post-state corresponding dual-contact predicate."""
        if self.body is None or self.station_center is None:
            raise RuntimeError("environment must be reset before observing")
        return _dock_contact(
            self.body.position,
            self.body.heading,
            self.station_center,
            self.config,
        )[0]

    @property
    def charger_termination_latched(self) -> bool:
        """Return evaluator-side charger latch state."""
        return self._charger_termination_latched

    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict[str, object] | None = None,
    ) -> tuple[np.ndarray, dict[str, object]]:
        """Reset from explicit evaluator setup values.

        ``seed`` is accepted for Gymnasium compatibility but no D-045 actuator
        or placement RNG is created or consumed.
        """
        super().reset(seed=seed)
        setup = options or {}
        position = _coordinate_option(setup, "body_position", (0.25, 0.25))
        station = _coordinate_option(setup, "station_center", (0.75, 0.75))
        heading = _float_option("heading", setup.get("heading", 0.0))
        battery = _float_option(
            "battery_j", setup.get("battery_j", self.config.initial_battery_j)
        )
        temperature = _float_option(
            "body_temperature_c",
            setup.get("body_temperature_c", self.config.initial_body_temperature_c),
        )
        latched = setup.get("charger_termination_latched", False)
        if not isinstance(latched, bool):
            raise ValueError("charger_termination_latched must be a bool")
        if not 0.0 <= battery <= self.config.battery_capacity_j:
            raise ValueError("battery_j must be within battery capacity")
        _validate_coordinate("station_center", station)
        self.body = Body(x=position[0], y=position[1], heading=heading, energy=0.0)
        self.station_center = station
        self.body_temperature_c = temperature
        self._battery_j = battery
        self._charger_termination_latched = latched
        self._previous_wheel_delta = (0.0, 0.0)
        self._step_count = 0
        self._episode_done = False
        self.last_transition = None
        return self._observation().as_array(), {}

    def step(
        self, action: np.ndarray | list[float] | tuple[float, float]
    ) -> tuple[np.ndarray, float, bool, bool, dict[str, object]]:
        """Apply one desired bilateral wheel-delta command."""
        if self._episode_done:
            raise RuntimeError("episode is over; call reset() before step()")
        requested = _action_pair(action)
        if (
            self.body is None
            or self.station_center is None
            or self.body_temperature_c is None
        ):
            raise RuntimeError("environment must be reset before step()")

        requested_left, requested_right = requested
        clamped_left = _clamp(
            requested_left,
            -self.config.max_wheel_delta_rad,
            self.config.max_wheel_delta_rad,
        )
        clamped_right = _clamp(
            requested_right,
            -self.config.max_wheel_delta_rad,
            self.config.max_wheel_delta_rad,
        )
        position_before = self.body.position
        heading_before = self.body.heading
        battery_before = self._battery_j
        temperature_before = self.body_temperature_c
        contact_before = self.charging_contact
        boundary_scale = _boundary_scale(
            position_before,
            heading_before,
            clamped_left,
            clamped_right,
            self.config,
        )
        actual_left = clamped_left * boundary_scale
        actual_right = clamped_right * boundary_scale
        position_after, heading_after = integrate_differential_drive(
            position_before,
            heading_before,
            actual_left,
            actual_right,
            track_width_m=self.config.wheel_track_width_m,
            wheel_radius_m=self.config.wheel_radius_m,
        )
        position_after = _bound_position(position_after, self.config)
        self.body.x, self.body.y = position_after
        self.body.heading = heading_after
        contact_after, plus_error, minus_error = _dock_contact(
            position_after, heading_after, self.station_center, self.config
        )

        effort = wheel_effort(
            actual_left, actual_right, self.config.max_wheel_delta_rad
        )
        actuator_power = self.config.wheel_power_scale_w * effort
        actuator_heat = self.config.wheel_body_heat_scale_w * effort
        total_electrical = self.config.electronics_power_w + actuator_power
        load_energy = total_electrical * self.config.dt_seconds
        charge = self._charge_decision(contact_after, battery_before)
        requested_charge_energy = (
            charge.requested_stored_power_w * self.config.dt_seconds
        )
        accepted_charge_energy = min(
            requested_charge_energy,
            max(0.0, self.config.battery_capacity_j - battery_before + load_energy),
        )
        actual_stored_power = accepted_charge_energy / self.config.dt_seconds
        battery_after = min(
            self.config.battery_capacity_j,
            max(0.0, battery_before + accepted_charge_energy - load_energy),
        )
        latched_after = charge.termination_latched_after
        if (
            charge.phase
            in (D045ChargePhase.BULK, D045ChargePhase.TAPER_1, D045ChargePhase.TAPER_2)
            and battery_after >= self.config.battery_capacity_j
        ):
            latched_after = True
        charger_input = (
            actual_stored_power / self.config.charge_efficiency
            if actual_stored_power > 0.0
            else 0.0
        )
        charging_heat = (
            charger_input - actual_stored_power if actual_stored_power > 0.0 else 0.0
        )
        total_body_heat = (
            self.config.electronics_body_heat_w + actuator_heat + charging_heat
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
        self._charger_termination_latched = latched_after
        energy_nonviable = battery_after <= 0.0
        protective = (
            temperature_after >= self.config.protective_temperature_c
            and temperature_after < self.config.hard_temperature_c
        )
        emergency = temperature_after >= self.config.hard_temperature_c
        reason = _termination_reason(emergency, protective, energy_nonviable)
        terminated = reason is not None
        self._step_count += 1
        truncated = not terminated and self._step_count >= self.config.episode_horizon
        self._episode_done = terminated or truncated
        self._previous_wheel_delta = (actual_left, actual_right)
        self.last_transition = D045TransitionTelemetry(
            step_index=self._step_count,
            requested_delta_left=requested_left,
            requested_delta_right=requested_right,
            clamped_delta_left=clamped_left,
            clamped_delta_right=clamped_right,
            actual_delta_left=actual_left,
            actual_delta_right=actual_right,
            boundary_scale=boundary_scale,
            position_before=position_before,
            position_after=position_after,
            heading_before=heading_before,
            heading_after=heading_after,
            station_center=self.station_center,
            charging_contact_before=contact_before,
            charging_contact_after=contact_after,
            dock_plus_error_m=plus_error,
            dock_minus_error_m=minus_error,
            battery_before_j=battery_before,
            battery_after_j=battery_after,
            body_temperature_before_c=temperature_before,
            body_temperature_after_c=temperature_after,
            actuator_electrical_power_w=actuator_power,
            electronics_electrical_power_w=self.config.electronics_power_w,
            total_electrical_load_w=total_electrical,
            charge_phase=charge.phase,
            requested_stored_power_w=charge.requested_stored_power_w,
            actual_stored_power_w=actual_stored_power,
            charger_input_power_w=charger_input,
            charging_body_heat_w=charging_heat,
            actuator_body_heat_w=actuator_heat,
            electronics_body_heat_w=self.config.electronics_body_heat_w,
            environmental_exchange_power_w=environmental_exchange,
            charger_termination_latched_after=latched_after,
            preferred_ceiling_crossed=(
                temperature_before
                < self.config.preferred_temperature_c
                <= temperature_after
            ),
            above_preferred_ceiling=temperature_after
            >= self.config.preferred_temperature_c,
            energy_nonviable=energy_nonviable,
            protective_shutdown=protective,
            emergency_hard_shutdown=emergency,
            terminated=terminated,
            truncated=truncated,
            termination_reason=reason,
        )
        return self._observation().as_array(), 0.0, terminated, truncated, {}

    def _charge_decision(
        self, contact_after: bool, battery_before: float
    ) -> _ChargeDecision:
        if not contact_after:
            return _ChargeDecision(D045ChargePhase.OFF, 0.0, False)
        soc = battery_before / self.config.battery_capacity_j
        if self._charger_termination_latched:
            if soc > self.config.resume_soc:
                return _ChargeDecision(D045ChargePhase.STANDBY, 0.0, True)
            self._charger_termination_latched = False
        if battery_before >= self.config.battery_capacity_j:
            return _ChargeDecision(D045ChargePhase.STANDBY, 0.0, True)
        if soc < self.config.bulk_soc_upper:
            return _ChargeDecision(
                D045ChargePhase.BULK, self.config.bulk_charge_power_w, False
            )
        if soc < self.config.taper_1_soc_upper:
            return _ChargeDecision(
                D045ChargePhase.TAPER_1, self.config.taper_1_charge_power_w, False
            )
        return _ChargeDecision(
            D045ChargePhase.TAPER_2, self.config.taper_2_charge_power_w, False
        )

    def _observation(self) -> D045Observation:
        if (
            self.body is None
            or self.station_center is None
            or self.body_temperature_c is None
        ):
            raise RuntimeError("environment must be reset before observing")
        beacon = sample_directional_beacon(
            self.body,
            self.station_center,
            probe_distance=self.config.beacon_probe_distance_m,
            sensor_angle=self.config.beacon_sensor_angle_rad,
            beacon_scale=self.config.beacon_scale_m,
        )
        return D045Observation(
            energy_normalized=_normalize(
                self._battery_j, 0.0, self.config.battery_capacity_j
            ),
            temperature_normalized=_normalize(
                self.body_temperature_c,
                self.config.visible_temperature_min_c,
                self.config.visible_temperature_max_c,
            ),
            beacon_left=beacon.left,
            beacon_forward=beacon.forward,
            beacon_right=beacon.right,
            charging_contact=self.charging_contact,
            wheel_delta_left=quantize_wheel_delta(
                self._previous_wheel_delta[0], self.config.encoder_quantum_rad
            ),
            wheel_delta_right=quantize_wheel_delta(
                self._previous_wheel_delta[1], self.config.encoder_quantum_rad
            ),
        )


def integrate_differential_drive(
    position: Coordinate,
    heading: float,
    delta_left: float,
    delta_right: float,
    *,
    track_width_m: float = D045_WHEEL_TRACK_WIDTH_METRES,
    wheel_radius_m: float = D045_WHEEL_RADIUS_METRES,
) -> tuple[Coordinate, float]:
    """Integrate one exact differential-drive arc with a straight limit."""
    d_left = wheel_radius_m * delta_left
    d_right = wheel_radius_m * delta_right
    d_s = (d_left + d_right) / 2.0
    d_theta = (d_right - d_left) / track_width_m
    if abs(d_theta) < _STRAIGHT_EPSILON:
        return (
            (
                position[0] + d_s * math.cos(heading),
                position[1] + d_s * math.sin(heading),
            ),
            heading + d_theta,
        )
    radius = d_s / d_theta
    next_heading = heading + d_theta
    return (
        (
            position[0] + radius * (math.sin(next_heading) - math.sin(heading)),
            position[1] - radius * (math.cos(next_heading) - math.cos(heading)),
        ),
        next_heading,
    )


def wheel_effort(
    actual_left: float, actual_right: float, max_delta: float = D045_MAX_WHEEL_DELTA_RAD
) -> float:
    """Return continuous bilateral sign-agnostic effort in [0, 1]."""
    if max_delta <= 0.0 or not math.isfinite(max_delta):
        raise ValueError("max_delta must be finite and positive")
    effort = (abs(actual_left) + abs(actual_right)) / (2.0 * max_delta)
    return _clamp(effort, 0.0, 1.0)


def quantize_wheel_delta(
    actual_delta: float, quantum: float = D045_ENCODER_QUANTUM_RAD
) -> float:
    """Quantize signed rotation to nearest count, with ties away from zero."""
    if not math.isfinite(actual_delta) or not math.isfinite(quantum) or quantum <= 0.0:
        raise ValueError("actual_delta must be finite and quantum must be positive")
    magnitude = math.floor(abs(actual_delta) / quantum + 0.5)
    return math.copysign(magnitude * quantum, actual_delta) if magnitude else 0.0


def run_d045_probe_suite() -> dict[str, object]:
    """Run the frozen seedless evaluator-scripted D-045 probe table."""
    config = D045PhysicalConfig()
    kinematics_commands: dict[str, tuple[float, float]] = {
        "ZERO": (0.0, 0.0),
        "FORWARD_MAX": (config.max_wheel_delta_rad, config.max_wheel_delta_rad),
        "REVERSE_MAX": (-config.max_wheel_delta_rad, -config.max_wheel_delta_rad),
        "IN_PLACE_LEFT": (-config.max_wheel_delta_rad, config.max_wheel_delta_rad),
        "IN_PLACE_RIGHT": (config.max_wheel_delta_rad, -config.max_wheel_delta_rad),
        "ARC_LEFT": (config.max_wheel_delta_rad, 0.0),
        "ARC_RIGHT": (0.0, config.max_wheel_delta_rad),
        "QUANTUM_SCALE": (config.encoder_quantum_rad, -config.encoder_quantum_rad),
        "OVER_RANGE_CLAMP": (
            2.0 * config.max_wheel_delta_rad,
            -2.0 * config.max_wheel_delta_rad,
        ),
    }
    kinematics = {
        name: _single_transition(
            config,
            command,
            options={
                "body_position": (0.4, 0.4),
                "station_center": (0.9, 0.9),
                "heading": 0.0,
            },
        )
        for name, command in kinematics_commands.items()
    }

    boundary_commands = (
        (
            "RIGHT_EDGE",
            (0.99, 0.5),
            0.0,
            (config.max_wheel_delta_rad, config.max_wheel_delta_rad),
        ),
        (
            "LEFT_EDGE",
            (0.01, 0.5),
            math.pi,
            (config.max_wheel_delta_rad, config.max_wheel_delta_rad),
        ),
        (
            "TOP_EDGE",
            (0.5, 0.99),
            math.pi / 2.0,
            (config.max_wheel_delta_rad, config.max_wheel_delta_rad),
        ),
        (
            "BOTTOM_EDGE",
            (0.5, 0.01),
            -math.pi / 2.0,
            (config.max_wheel_delta_rad, config.max_wheel_delta_rad),
        ),
        (
            "TOP_RIGHT_CORNER",
            (0.99, 0.99),
            math.pi / 4.0,
            (config.max_wheel_delta_rad, config.max_wheel_delta_rad),
        ),
    )
    boundaries = {
        name: _single_transition(
            config,
            command,
            options={
                "body_position": position,
                "station_center": (0.5, 0.5),
                "heading": heading,
            },
        )
        for name, position, heading, command in boundary_commands
    }

    dock_cases = {
        "EXACT_ALIGNED": _single_transition(
            config,
            (0.0, 0.0),
            options={
                "body_position": (0.5, 0.5),
                "station_center": (0.5, 0.5),
                "heading": 0.0,
            },
        ),
        "JUST_INSIDE": _single_transition(
            config,
            (0.0, 0.0),
            options={
                "body_position": (0.5 + 0.0099, 0.5),
                "station_center": (0.5, 0.5),
                "heading": 0.0,
            },
        ),
        "JUST_OUTSIDE": _single_transition(
            config,
            (0.0, 0.0),
            options={
                "body_position": (0.5 + 0.0101, 0.5),
                "station_center": (0.5, 0.5),
                "heading": 0.0,
            },
        ),
        "POLARITY_MISALIGNED": _single_transition(
            config,
            (0.0, 0.0),
            options={
                "body_position": (0.5, 0.5),
                "station_center": (0.5, 0.5),
                "heading": math.pi,
            },
        ),
    }
    through_center = _run_through_center(config)
    charging = _run_charge_probe(config)
    accounting = _run_accounting_probe(config)
    observation = _run_observation_probe(config)
    replay = _run_replay_probe(config)
    structural = _run_structural_feasibility(config)
    return {
        "artifact_schema_version": "D045-1",
        "identifier": "D-045",
        "lane": "Development",
        "seed_status": "seedless fixed-state evaluator probes",
        "config": _config_record(config),
        "quantization": {
            "quantum_rad": config.encoder_quantum_rad,
            "provenance": "ENGINEERING ESTIMATE",
            "tie_rule": "nearest count; exact half-count ties away from zero",
        },
        "probes": {
            "kinematics_action_semantics": kinematics,
            "world_boundary_common_scaling": boundaries,
            "dock_contact": dock_cases,
            "translation_through_station_centre": through_center,
            "charging_retained_semantics": charging,
            "continuous_bookkeeping": accounting,
            "observation_information_boundary": observation,
            "deterministic_replay": replay,
            "structural_feasibility": structural,
        },
        "actuator_rng": {
            "new_actuator_rng": False,
            "reset_seed_consumed_by_actuator": False,
        },
        "claims_boundary": (
            "descriptive deterministic substrate validation; no confirmatory claim"
        ),
    }


def write_d045_probe_json(path: Path) -> Path:
    """Write the deterministic compact D-045 artifact."""
    payload = run_d045_probe_suite()
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=_json_default) + "\n",
        encoding="utf-8",
    )
    return path


def _single_transition(
    config: D045PhysicalConfig,
    command: tuple[float, float],
    *,
    options: dict[str, object],
) -> dict[str, object]:
    environment = D045Env(config)
    environment.reset(options=options)
    observation, reward, terminated, truncated, info = environment.step(command)
    if environment.last_transition is None:
        raise RuntimeError("D-045 transition telemetry was not recorded")
    transition = environment.last_transition
    return {
        "requested": [command[0], command[1]],
        "actual": [transition.actual_delta_left, transition.actual_delta_right],
        "boundary_scale": transition.boundary_scale,
        "position_after": transition.position_after,
        "heading_after": transition.heading_after,
        "charging_contact_after": transition.charging_contact_after,
        "dock_pair_errors_m": [
            transition.dock_plus_error_m,
            transition.dock_minus_error_m,
        ],
        "visible_observation": [float(value) for value in observation],
        "reward": reward,
        "terminated": terminated,
        "truncated": truncated,
        "info": info,
        "actuator_electrical_power_w": transition.actuator_electrical_power_w,
    }


def _run_through_center(config: D045PhysicalConfig) -> dict[str, object]:
    command_value = 0.4 / (14.0 * config.wheel_radius_m)
    environment = D045Env(config)
    environment.reset(
        options={
            "body_position": (0.3, 0.5),
            "station_center": (0.5, 0.5),
            "heading": 0.0,
        }
    )
    contacts: list[bool] = []
    for _ in range(14):
        environment.step((command_value, command_value))
        contacts.append(environment.charging_contact)
    if environment.last_transition is None:
        raise RuntimeError("translation probe produced no transition")
    return {
        "command": [command_value, command_value],
        "contact_steps": [index + 1 for index, value in enumerate(contacts) if value],
        "final_position": environment.last_transition.position_after,
        "no_swept_contact": contacts.count(True) == 1,
    }


def _run_charge_probe(config: D045PhysicalConfig) -> dict[str, object]:
    environment = D045Env(config)
    environment.reset(
        options={
            "body_position": (0.5, 0.5),
            "station_center": (0.5, 0.5),
            "heading": 0.0,
            "battery_j": config.initial_battery_j,
            "body_temperature_c": config.initial_body_temperature_c,
        }
    )
    phases: dict[str, int] = {phase.value: 0 for phase in D045ChargePhase}
    first_latch: int | None = None
    max_temperature = -math.inf
    for _ in range(config.episode_horizon):
        _, _, terminated, truncated, _ = environment.step((0.0, 0.0))
        if environment.last_transition is None:
            raise RuntimeError("charge probe produced no transition")
        transition = environment.last_transition
        phases[transition.charge_phase.value] += 1
        max_temperature = max(max_temperature, transition.body_temperature_after_c)
        if first_latch is None and transition.charger_termination_latched_after:
            first_latch = transition.step_index
        if terminated or truncated:
            break
    return {
        "transitions": environment.last_transition.step_index
        if environment.last_transition
        else 0,
        "battery_start_j": config.initial_battery_j,
        "battery_end_j": environment.battery_j,
        "body_temperature_end_c": environment.body_temperature_c,
        "body_temperature_max_c": max_temperature,
        "phase_counts": phases,
        "first_full_latch_step": first_latch,
        "termination_latched": environment.charger_termination_latched,
    }


def _run_accounting_probe(config: D045PhysicalConfig) -> dict[str, object]:
    commands = {
        "zero": (0.0, 0.0),
        "reverse": (-config.max_wheel_delta_rad, -config.max_wheel_delta_rad),
        "swap": (config.max_wheel_delta_rad, 0.0),
        "swap_reversed": (0.0, config.max_wheel_delta_rad),
        "full": (config.max_wheel_delta_rad, config.max_wheel_delta_rad),
        "half": (config.max_wheel_delta_rad, 0.0),
    }
    powers: dict[str, float] = {}
    heat: dict[str, float] = {}
    for name, command in commands.items():
        result = _single_transition(
            config,
            command,
            options={"body_position": (0.4, 0.4), "station_center": (0.9, 0.9)},
        )
        powers[name] = cast(float, result["actuator_electrical_power_w"])
        environment = D045Env(config)
        environment.reset(
            options={"body_position": (0.4, 0.4), "station_center": (0.9, 0.9)}
        )
        environment.step(command)
        if environment.last_transition is None:
            raise RuntimeError("accounting probe produced no transition")
        heat[name] = environment.last_transition.actuator_body_heat_w
    reduced = _single_transition(
        config,
        (config.max_wheel_delta_rad, config.max_wheel_delta_rad),
        options={"body_position": (0.99, 0.5), "station_center": (0.9, 0.9)},
    )
    return {
        "actuator_power_w": powers,
        "actuator_body_heat_w": heat,
        "boundary_reduced_power_w": reduced["actuator_electrical_power_w"],
        "invariants": {
            "zero_is_zero": powers["zero"] == 0.0,
            "sign_symmetric": powers["reverse"] == powers["full"],
            "wheel_swap_symmetric": powers["swap"] == powers["swap_reversed"],
            "full_is_one_watt": powers["full"] == 1.0,
            "one_saturated_wheel_is_half_watt": powers["half"] == 0.5,
            "actuator_body_heat_zero": all(value == 0.0 for value in heat.values()),
        },
    }


def _run_observation_probe(config: D045PhysicalConfig) -> dict[str, object]:
    environment = D045Env(config)
    initial, initial_info = environment.reset(
        options={"body_position": (0.4, 0.4), "station_center": (0.9, 0.9)}
    )
    next_observation, reward, terminated, truncated, info = environment.step(
        (config.encoder_quantum_rad, -config.encoder_quantum_rad)
    )
    return {
        "channel_order": [
            "energy_normalized",
            "temperature_normalized",
            "beacon_left",
            "beacon_forward",
            "beacon_right",
            "charging_contact",
            "wheel_delta_left",
            "wheel_delta_right",
        ],
        "initial_shape": list(initial.shape),
        "post_action_shape": list(next_observation.shape),
        "initial_observation": [float(value) for value in initial],
        "post_action_observation": [float(value) for value in next_observation],
        "initial_info": initial_info,
        "reward": reward,
        "terminated": terminated,
        "truncated": truncated,
        "info": info,
        "observation_space_contains": bool(
            environment.observation_space.contains(next_observation)
        ),
    }


def _run_replay_probe(config: D045PhysicalConfig) -> dict[str, object]:
    commands = (
        (0.0, 0.0),
        (config.max_wheel_delta_rad, 0.0),
        (-config.max_wheel_delta_rad, config.max_wheel_delta_rad),
        (config.encoder_quantum_rad, -config.encoder_quantum_rad),
    )

    def trace() -> list[dict[str, object]]:
        environment = D045Env(config)
        environment.reset(
            options={"body_position": (0.4, 0.4), "station_center": (0.9, 0.9)}
        )
        values: list[dict[str, object]] = []
        for command in commands:
            observation, _, _, _, _ = environment.step(command)
            if environment.last_transition is None:
                raise RuntimeError("replay probe produced no telemetry")
            values.append(
                {
                    "observation": [float(value) for value in observation],
                    "position": environment.last_transition.position_after,
                    "heading": environment.last_transition.heading_after,
                    "battery": environment.battery_j,
                    "temperature": environment.body_temperature_c,
                }
            )
        return values

    first = trace()
    second = trace()
    encoded_first = json.dumps(first, sort_keys=True, separators=(",", ":"))
    encoded_second = json.dumps(second, sort_keys=True, separators=(",", ":"))
    return {
        "byte_identical_trace": encoded_first == encoded_second,
        "trace_sha256": hashlib.sha256(encoded_first.encode("utf-8")).hexdigest(),
        "transition_count": len(first),
    }


def _run_structural_feasibility(config: D045PhysicalConfig) -> dict[str, object]:
    start = (0.3, 0.5)
    station = (0.5, 0.5)
    command_value = 0.2 / (7.0 * config.wheel_radius_m)
    commands = tuple((command_value, command_value) for _ in range(7))
    environment = D045Env(config)
    environment.reset(
        options={
            "body_position": start,
            "station_center": station,
            "heading": 0.0,
            "battery_j": config.initial_battery_j,
            "body_temperature_c": config.initial_body_temperature_c,
        }
    )
    for command in commands:
        environment.step(command)
    telemetry = environment.last_transition
    if telemetry is None:
        raise RuntimeError("structural feasibility sequence produced no telemetry")
    feasible = (
        telemetry.charging_contact_after
        and environment.battery_j > 0.0
        and (environment.body_temperature_c or math.inf)
        < config.protective_temperature_c
        and not telemetry.terminated
    )
    return {
        "feasible": feasible,
        "method": "fixed evaluator-scripted raw wheel-command sequence",
        "start_position": start,
        "station_center": station,
        "battery_start_j": config.initial_battery_j,
        "temperature_start_c": config.initial_body_temperature_c,
        "command_sequence_length": len(commands),
        "command": [command_value, command_value],
        "final_position": telemetry.position_after,
        "final_contact": telemetry.charging_contact_after,
        "battery_end_j": environment.battery_j,
        "temperature_end_c": environment.body_temperature_c,
        "termination": telemetry.termination_reason,
    }


def _config_record(config: D045PhysicalConfig) -> dict[str, object]:
    return {
        "dt_seconds": config.dt_seconds,
        "world_min": config.world_min,
        "world_max": config.world_max,
        "wheel_track_width_m": config.wheel_track_width_m,
        "wheel_radius_m": config.wheel_radius_m,
        "max_wheel_delta_rad": config.max_wheel_delta_rad,
        "contact_offset_m": config.contact_offset_m,
        "contact_tolerance_m": config.contact_tolerance_m,
        "battery_capacity_j": config.battery_capacity_j,
        "initial_battery_j": config.initial_battery_j,
        "electronics_power_w": config.electronics_power_w,
        "electronics_body_heat_w": config.electronics_body_heat_w,
        "wheel_power_scale_w": config.wheel_power_scale_w,
        "wheel_body_heat_scale_w": config.wheel_body_heat_scale_w,
        "charge_efficiency": config.charge_efficiency,
        "bulk_charge_power_w": config.bulk_charge_power_w,
        "taper_1_charge_power_w": config.taper_1_charge_power_w,
        "taper_2_charge_power_w": config.taper_2_charge_power_w,
        "bulk_soc_upper": config.bulk_soc_upper,
        "taper_1_soc_upper": config.taper_1_soc_upper,
        "resume_soc": config.resume_soc,
        "thermal_capacitance_j_per_k": config.thermal_capacitance_j_per_k,
        "thermal_conductance_w_per_k": config.thermal_conductance_w_per_k,
        "ambient_temperature_c": config.ambient_temperature_c,
        "preferred_temperature_c": config.preferred_temperature_c,
        "protective_temperature_c": config.protective_temperature_c,
        "hard_temperature_c": config.hard_temperature_c,
        "visible_temperature_bounds_c": (
            config.visible_temperature_min_c,
            config.visible_temperature_max_c,
        ),
        "beacon_scale_m": config.beacon_scale_m,
        "beacon_probe_distance_m": config.beacon_probe_distance_m,
        "beacon_sensor_angle_rad": config.beacon_sensor_angle_rad,
        "episode_horizon": config.episode_horizon,
    }


def _dock_contact(
    position: Coordinate,
    heading: float,
    station_center: Coordinate,
    config: D045PhysicalConfig,
) -> tuple[bool, float, float]:
    plus = _body_contact_point(position, heading, (0.0, config.contact_offset_m))
    minus = _body_contact_point(position, heading, (0.0, -config.contact_offset_m))
    station_plus = (station_center[0], station_center[1] + config.contact_offset_m)
    station_minus = (station_center[0], station_center[1] - config.contact_offset_m)
    plus_error = math.dist(plus, station_plus)
    minus_error = math.dist(minus, station_minus)
    return (
        plus_error <= config.contact_tolerance_m
        and minus_error <= config.contact_tolerance_m,
        plus_error,
        minus_error,
    )


def _body_contact_point(
    position: Coordinate, heading: float, local: Coordinate
) -> Coordinate:
    cosine = math.cos(heading)
    sine = math.sin(heading)
    return (
        position[0] + cosine * local[0] - sine * local[1],
        position[1] + sine * local[0] + cosine * local[1],
    )


def _boundary_scale(
    position: Coordinate,
    heading: float,
    delta_left: float,
    delta_right: float,
    config: D045PhysicalConfig,
) -> float:
    full_position, _ = integrate_differential_drive(
        position,
        heading,
        delta_left,
        delta_right,
        track_width_m=config.wheel_track_width_m,
        wheel_radius_m=config.wheel_radius_m,
    )
    if _inside_world(full_position, config):
        return 1.0
    low = 0.0
    high = 1.0
    for _ in range(_BOUNDARY_BISECTION_ITERATIONS):
        middle = (low + high) / 2.0
        candidate, _ = integrate_differential_drive(
            position,
            heading,
            delta_left * middle,
            delta_right * middle,
            track_width_m=config.wheel_track_width_m,
            wheel_radius_m=config.wheel_radius_m,
        )
        if _inside_world(candidate, config):
            low = middle
        else:
            high = middle
    return low


def _inside_world(position: Coordinate, config: D045PhysicalConfig) -> bool:
    return all(
        lower <= value <= upper
        for value, lower, upper in zip(position, config.world_min, config.world_max)
    )


def _bound_position(position: Coordinate, config: D045PhysicalConfig) -> Coordinate:
    return tuple(
        _clamp(value, lower, upper)
        for value, lower, upper in zip(position, config.world_min, config.world_max)
    )  # type: ignore[return-value]


def _action_pair(
    action: np.ndarray | list[float] | tuple[float, float],
) -> tuple[float, float]:
    values = np.asarray(action, dtype=np.float64)
    if values.shape != (2,) or not np.all(np.isfinite(values)):
        raise ValueError("action must contain exactly two finite wheel deltas")
    return float(values[0]), float(values[1])


def _coordinate_option(
    setup: dict[str, object], name: str, default: Coordinate
) -> Coordinate:
    value = setup.get(name, default)
    try:
        coordinate = (float(value[0]), float(value[1]))  # type: ignore[index]
    except IndexError, KeyError, TypeError, ValueError:
        raise ValueError(f"{name} must contain two finite coordinates") from None
    _validate_coordinate(name, coordinate)
    return coordinate


def _float_option(name: str, value: object) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be finite")
    try:
        result = float(cast(SupportsFloat, value))
    except TypeError, ValueError:
        raise ValueError(f"{name} must be finite") from None
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _validate_bounds(world_min: Coordinate, world_max: Coordinate) -> None:
    _validate_coordinate("world_min", world_min)
    _validate_coordinate("world_max", world_max)
    if not all(lower < upper for lower, upper in zip(world_min, world_max)):
        raise ValueError("world_min must be strictly below world_max")


def _validate_coordinate(name: str, coordinate: Coordinate) -> None:
    if len(coordinate) != 2 or not all(
        math.isfinite(float(value)) for value in coordinate
    ):
        raise ValueError(f"{name} must contain two finite coordinates")


def _normalize(value: float, lower: float, upper: float) -> float:
    return _clamp((value - lower) / (upper - lower), 0.0, 1.0)


def _clamp(value: float, lower: float, upper: float) -> float:
    return min(max(value, lower), upper)


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


def _termination_reason(
    emergency: bool, protective: bool, energy_nonviable: bool
) -> D045TerminationReason | None:
    if emergency:
        return D045TerminationReason.EMERGENCY_HARD_THERMAL_SHUTDOWN
    if protective:
        return D045TerminationReason.PROTECTIVE_THERMAL_SHUTDOWN
    if energy_nonviable:
        return D045TerminationReason.ENERGY_DEPLETION
    return None


def _json_default(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"cannot serialize {type(value).__name__}")


def main() -> None:
    """CLI entry point for the fixed D-045 artifact."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_d045_probe_json(args.output)


if __name__ == "__main__":
    main()
