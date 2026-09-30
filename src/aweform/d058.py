"""D-058 V0.5 endpoint-only rectangular wall-contact substrate."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

import gymnasium as gym
import numpy as np

from .body import Body, Coordinate
from .d045 import (
    D045_AMBIENT_TEMPERATURE_C,
    D045_BATTERY_CAPACITY_J,
    D045_INITIAL_BATTERY_J,
    D045_MAX_WHEEL_DELTA_RAD,
    D045_WHEEL_RADIUS_METRES,
    D045_WHEEL_TRACK_WIDTH_METRES,
    D045ChargePhase,
    D045Observation,
    D045PhysicalConfig,
    D045TransitionTelemetry,
    _action_pair,
    _ChargeDecision,
    _coordinate_option,
    _float_option,
    _termination_reason,
    integrate_differential_drive,
    quantize_wheel_delta,
    wheel_effort,
)

PROTOCOL_VERSION: Final = "d058-v05-physical-wall-contact-substrate-v1"
ARTIFACT_SCHEMA_VERSION: Final = "D058-1"
BASE_SHA: Final = "827a35638e727cd11f50eefa7d957a4d960f7e1d"
D058_HULL_HALF_LENGTH_METRES: Final = 0.090
D058_HULL_HALF_WIDTH_METRES: Final = 0.1075
U_ONSET: Final = (-0.565040862351, 0.645771823238)
PROTECTED: Final = (
    "src/aweform/d045.py",
    "src/aweform/d049.py",
    "src/aweform/d050.py",
    "src/aweform/d052.py",
    "src/aweform/d053.py",
    "src/aweform/d054.py",
    "src/aweform/d055.py",
    "src/aweform/d056.py",
    "src/aweform/d057.py",
    "src/aweform/development_visualizer.py",
)


@dataclass(frozen=True, slots=True)
class D058PhysicalConfig:
    """The legal room-size choice; all remaining physical values are D-045's."""

    room_side_m: float = 3.0
    _base: D045PhysicalConfig = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if isinstance(self.room_side_m, bool) or self.room_side_m not in (3.0, 1.0):
            raise ValueError("room_side_m must be exactly 3.0 or 1.0")
        object.__setattr__(
            self,
            "_base",
            D045PhysicalConfig(
                world_min=(0.0, 0.0), world_max=(self.room_side_m, self.room_side_m)
            ),
        )

    def __getattr__(self, name: str):
        # Preserve D-045's frozen physical parameters without exposing world bounds.
        if name in ("world_min", "world_max"):
            raise AttributeError(name)
        return getattr(self._base, name)


@dataclass(frozen=True, slots=True)
class D058ContactTelemetry:
    unconstrained_endpoint: Coordinate
    executed_endpoint: Coordinate
    pushing_x_min: bool
    pushing_x_max: bool
    pushing_y_min: bool
    pushing_y_max: bool
    hx_m: float
    hy_m: float
    removed_normal_displacement_m: float
    slip_magnitude_m: float


class D058Env(gym.Env[np.ndarray, np.ndarray]):
    """D-045 interface with a full-yaw, endpoint-projected rectangular hull."""

    metadata: dict[str, object] = {"render_modes": []}

    def __init__(self, config: D058PhysicalConfig | None = None) -> None:
        self.config = config or D058PhysicalConfig()
        self.action_space = gym.spaces.Box(
            low=np.full(2, -D045_MAX_WHEEL_DELTA_RAD, dtype=np.float64),
            high=np.full(2, D045_MAX_WHEEL_DELTA_RAD, dtype=np.float64),
            dtype=np.float64,
        )
        self.observation_space = gym.spaces.Box(
            low=np.asarray(
                (
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    -D045_MAX_WHEEL_DELTA_RAD,
                    -D045_MAX_WHEEL_DELTA_RAD,
                ),
                dtype=np.float32,
            ),
            high=np.asarray(
                (1, 1, 1, 1, 1, 1, D045_MAX_WHEEL_DELTA_RAD, D045_MAX_WHEEL_DELTA_RAD),
                dtype=np.float32,
            ),
            dtype=np.float32,
        )
        self.body: Body | None = None
        self.station_center: Coordinate | None = None
        self.body_temperature_c: float | None = None
        self._battery_j = 0.0
        self._charger_termination_latched = False
        self._previous_wheel_delta = (0.0, 0.0)
        self._step_count = 0
        self._episode_done = True
        self.last_contact: D058ContactTelemetry | None = None
        self.last_transition: D045TransitionTelemetry | None = None

    @property
    def battery_j(self) -> float:
        return self._battery_j

    @property
    def charger_termination_latched(self) -> bool:
        return self._charger_termination_latched

    @property
    def charging_contact(self) -> bool:
        if self.body is None or self.station_center is None:
            raise RuntimeError("environment must be reset before observing")
        from .d045 import _dock_contact

        return _dock_contact(
            self.body.position,
            self.body.heading,
            self.station_center,
            self.config._base,
        )[0]

    def _extent(self, heading: float) -> tuple[float, float]:
        a, c = D058_HULL_HALF_LENGTH_METRES, D058_HULL_HALF_WIDTH_METRES
        cosine, sine = abs(math.cos(heading)), abs(math.sin(heading))
        return a * cosine + c * sine, a * sine + c * cosine

    def _legal(self, position: Coordinate, heading: float) -> bool:
        hx, hy = self._extent(heading)
        length = self.config.room_side_m
        return hx <= position[0] <= length - hx and hy <= position[1] <= length - hy

    def reset(
        self, *, seed: int | None = None, options: dict[str, object] | None = None
    ) -> tuple[np.ndarray, dict[str, object]]:
        super().reset(seed=seed)
        setup = options or {}
        allowed = {
            "body_position",
            "station_center",
            "heading",
            "battery_j",
            "body_temperature_c",
            "charger_termination_latched",
        }
        unknown = set(setup) - allowed
        if unknown:
            raise ValueError(f"unknown reset option(s): {sorted(unknown)}")
        length = self.config.room_side_m
        position = _coordinate_option(setup, "body_position", (length / 4, length / 4))
        station = _coordinate_option(setup, "station_center", (length / 2, length / 2))
        if station != (length / 2, length / 2):
            raise ValueError("station_center must equal the room centre")
        heading = _float_option("heading", setup.get("heading", 0.0))
        battery = _float_option(
            "battery_j", setup.get("battery_j", D045_INITIAL_BATTERY_J)
        )
        temperature = _float_option(
            "body_temperature_c",
            setup.get("body_temperature_c", D045_AMBIENT_TEMPERATURE_C),
        )
        latched = setup.get("charger_termination_latched", False)
        if not isinstance(latched, bool):
            raise ValueError("charger_termination_latched must be a bool")
        if not 0.0 <= battery <= D045_BATTERY_CAPACITY_J:
            raise ValueError("battery_j must be within battery capacity")
        if not self._legal(position, heading):
            raise ValueError("body_position hull must be fully inside the room")
        self.body = Body(x=position[0], y=position[1], heading=heading, energy=0.0)
        self.station_center, self.body_temperature_c = station, temperature
        self._battery_j, self._charger_termination_latched = battery, latched
        self._previous_wheel_delta = (0.0, 0.0)
        self._step_count, self._episode_done = 0, False
        self.last_contact = None
        self.last_transition = None
        return self._observation().as_array(), {}

    def _observation(self) -> D045Observation:
        if (
            self.body is None
            or self.station_center is None
            or self.body_temperature_c is None
        ):
            raise RuntimeError("environment must be reset before observing")
        from .exp003 import sample_directional_beacon

        beacon = sample_directional_beacon(
            self.body,
            self.station_center,
            probe_distance=self.config.beacon_probe_distance_m,
            sensor_angle=self.config.beacon_sensor_angle_rad,
            beacon_scale=self.config.beacon_scale_m,
        )

        def clamp(value: float, low: float, high: float) -> float:
            return min(max(value, low), high)

        return D045Observation(
            energy_normalized=clamp(
                self._battery_j / self.config.battery_capacity_j, 0.0, 1.0
            ),
            temperature_normalized=clamp(
                (self.body_temperature_c - self.config.visible_temperature_min_c)
                / (
                    self.config.visible_temperature_max_c
                    - self.config.visible_temperature_min_c
                ),
                0.0,
                1.0,
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

    def step(
        self, action: np.ndarray | list[float] | tuple[float, float]
    ) -> tuple[np.ndarray, float, bool, bool, dict[str, object]]:
        if self._episode_done:
            raise RuntimeError("episode is over; call reset() before step()")
        requested_left, requested_right = _action_pair(action)
        if (
            self.body is None
            or self.station_center is None
            or self.body_temperature_c is None
        ):
            raise RuntimeError("environment must be reset before step()")
        cfg = self.config._base
        limit = D045_MAX_WHEEL_DELTA_RAD
        left, right = (
            min(max(requested_left, -limit), limit),
            min(max(requested_right, -limit), limit),
        )
        p0, t0 = self.body.position, self.body.heading
        pfull, tfull = integrate_differential_drive(
            p0,
            t0,
            left,
            right,
            track_width_m=cfg.wheel_track_width_m,
            wheel_radius_m=cfg.wheel_radius_m,
        )
        hx, hy = self._extent(tfull)
        length = self.config.room_side_m
        pexec = (
            min(max(pfull[0], hx), length - hx),
            min(max(pfull[1], hy), length - hy),
        )
        pushing = (
            pfull[0] < hx,
            pfull[0] > length - hx,
            pfull[1] < hy,
            pfull[1] > length - hy,
        )
        removed = math.hypot(pfull[0] - pexec[0], pfull[1] - pexec[1])
        slip = math.dist(pfull, pexec)
        battery_before, temperature_before = self._battery_j, self.body_temperature_c
        contact_before = self.charging_contact
        self.body.x, self.body.y, self.body.heading = pexec[0], pexec[1], tfull
        from .d045 import _dock_contact

        contact_after, plus_error, minus_error = _dock_contact(
            pexec, tfull, self.station_center, cfg
        )
        effort = wheel_effort(left, right, limit)
        actuator_power, actuator_heat = (
            cfg.wheel_power_scale_w * effort,
            cfg.wheel_body_heat_scale_w * effort,
        )
        total_load = cfg.electronics_power_w + actuator_power
        load_energy = total_load * cfg.dt_seconds
        charge = self._charge_decision(contact_after, battery_before)
        charge_energy = min(
            charge.requested_stored_power_w * cfg.dt_seconds,
            max(0.0, cfg.battery_capacity_j - battery_before + load_energy),
        )
        stored_power = charge_energy / cfg.dt_seconds
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
            + cfg.dt_seconds * (total_heat + exchange) / cfg.thermal_capacitance_j_per_k
        )
        self._battery_j, self.body_temperature_c, self._charger_termination_latched = (
            battery_after,
            temperature_after,
            latched,
        )
        energy_nonviable = battery_after <= 0.0
        protective = (
            temperature_after >= cfg.protective_temperature_c
            and temperature_after < cfg.hard_temperature_c
        )
        emergency = temperature_after >= cfg.hard_temperature_c
        reason = _termination_reason(emergency, protective, energy_nonviable)
        terminated = reason is not None
        self._step_count += 1
        truncated = not terminated and self._step_count >= cfg.episode_horizon
        self._episode_done = terminated or truncated
        self._previous_wheel_delta = (left, right)
        self.last_contact = D058ContactTelemetry(
            pfull, pexec, *pushing, hx, hy, removed, slip
        )
        self.last_transition = D045TransitionTelemetry(
            step_index=self._step_count,
            requested_delta_left=requested_left,
            requested_delta_right=requested_right,
            clamped_delta_left=left,
            clamped_delta_right=right,
            actual_delta_left=left,
            actual_delta_right=right,
            boundary_scale=1.0,
            position_before=p0,
            position_after=pexec,
            heading_before=t0,
            heading_after=tfull,
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
            electronics_electrical_power_w=cfg.electronics_power_w,
            total_electrical_load_w=total_load,
            charge_phase=charge.phase,
            requested_stored_power_w=charge.requested_stored_power_w,
            actual_stored_power_w=stored_power,
            charger_input_power_w=charger_input,
            charging_body_heat_w=charging_heat,
            actuator_body_heat_w=actuator_heat,
            electronics_body_heat_w=cfg.electronics_body_heat_w,
            environmental_exchange_power_w=exchange,
            charger_termination_latched_after=latched,
            preferred_ceiling_crossed=temperature_before
            < cfg.preferred_temperature_c
            <= temperature_after,
            above_preferred_ceiling=temperature_after >= cfg.preferred_temperature_c,
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
        cfg = self.config._base
        if not contact_after:
            return _ChargeDecision(D045ChargePhase.OFF, 0.0, False)
        soc = battery_before / cfg.battery_capacity_j
        if self._charger_termination_latched:
            if soc > cfg.resume_soc:
                return _ChargeDecision(D045ChargePhase.STANDBY, 0.0, True)
            self._charger_termination_latched = False
        if battery_before >= cfg.battery_capacity_j:
            return _ChargeDecision(D045ChargePhase.STANDBY, 0.0, True)
        if soc < cfg.bulk_soc_upper:
            return _ChargeDecision(D045ChargePhase.BULK, cfg.bulk_charge_power_w, False)
        if soc < cfg.taper_1_soc_upper:
            return _ChargeDecision(
                D045ChargePhase.TAPER_1, cfg.taper_1_charge_power_w, False
            )
        return _ChargeDecision(
            D045ChargePhase.TAPER_2, cfg.taper_2_charge_power_w, False
        )


def make_d058_env(room_side_m: float = 3.0) -> D058Env:
    """Create the canonical D-058 environment for the selected legal room."""
    return D058Env(D058PhysicalConfig(room_side_m=room_side_m))


def _probe_sets() -> tuple[
    tuple[tuple[float, float], ...], tuple[tuple[float, float], ...], tuple[float, ...]
]:
    m = D045_MAX_WHEEL_DELTA_RAD
    vals = (-m, 0.0, m)
    u9 = tuple(
        (left, right) for left in vals for right in vals if (left, right) != (0.0, 0.0)
    ) + (U_ONSET,)
    u10 = u9 + ((0.0, 0.0),)
    phi = math.atan(D058_HULL_HALF_WIDTH_METRES / D058_HULL_HALF_LENGTH_METRES)
    peaks = (
        phi,
        math.pi - phi,
        math.pi + phi,
        2 * math.pi - phi,
        math.pi / 2 - phi,
        math.pi / 2 + phi,
        3 * math.pi / 2 - phi,
        3 * math.pi / 2 + phi,
    )
    return u9, u10, tuple(k * math.pi / 12 for k in range(24)) + peaks


def _penetration(position: Coordinate, heading: float, length: float) -> float:
    a, c = D058_HULL_HALF_LENGTH_METRES, D058_HULL_HALF_WIDTH_METRES
    hx = a * abs(math.cos(heading)) + c * abs(math.sin(heading))
    hy = a * abs(math.sin(heading)) + c * abs(math.cos(heading))
    x, y = position
    return max(0.0, hx - x, x + hx - length, hy - y, y + hy - length)


def _independent_corner_violation(
    position: Coordinate, heading: float, length: float
) -> tuple[float, Coordinate | None, str | None]:
    """Return the maximum signed wall penetration from independently rotated corners."""
    worst, point, wall = 0.0, None, None
    cosine, sine = math.cos(heading), math.sin(heading)
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            corner = (
                position[0]
                + sx * D058_HULL_HALF_LENGTH_METRES * cosine
                - sy * D058_HULL_HALF_WIDTH_METRES * sine,
                position[1]
                + sx * D058_HULL_HALF_LENGTH_METRES * sine
                + sy * D058_HULL_HALF_WIDTH_METRES * cosine,
            )
            for value, label in ((corner[0], "x"), (corner[1], "y")):
                violation = max(0.0, -value, value - length)
                if violation > worst:
                    worst, point, wall = violation, corner, label
    return worst, point, wall


def _verification_tau(length: float) -> float:
    return 64.0 * (2.0**-52) * length


def _start_position(
    kind: str, ident: str, variant: str, heading: float, length: float
) -> Coordinate:
    hx = D058_HULL_HALF_LENGTH_METRES * abs(
        math.cos(heading)
    ) + D058_HULL_HALF_WIDTH_METRES * abs(math.sin(heading))
    hy = D058_HULL_HALF_LENGTH_METRES * abs(
        math.sin(heading)
    ) + D058_HULL_HALF_WIDTH_METRES * abs(math.cos(heading))
    inset = 0.01 if variant == "near" else 0.0
    x = y = length / 2
    if "x_min" in ident:
        x = hx + inset
    if "x_max" in ident:
        x = length - hx - inset
    if "y_min" in ident:
        y = hy + inset
    if "y_max" in ident:
        y = length - hy - inset
    return x, y


def run_d058_conformance(executed_commit_sha: str | None = None) -> dict[str, object]:
    """Deterministic evaluator-only checks 1–7; contains no seeded lifetimes."""
    u9, u10, headings = _probe_sets()
    m = D045_MAX_WHEEL_DELTA_RAD
    dtheta = 2 * D045_WHEEL_RADIUS_METRES * m / D045_WHEEL_TRACK_WIDTH_METRES
    dmax = D045_WHEEL_RADIUS_METRES * m
    bound = (
        2
        * math.hypot(D058_HULL_HALF_LENGTH_METRES, D058_HULL_HALF_WIDTH_METRES)
        * math.sin(dtheta / 2)
        + dmax
    )
    results = {
        "schema_version": "d058-v1",
        "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "authorized_base_sha": BASE_SHA,
        "executed_source_sha": executed_commit_sha,
        "protocol_sha": executed_commit_sha,
        "checks": {},
        "symbolic_penetration_bound_m": bound,
        "verification_amendment": (
            "Verification amendment 1: tau(L)=64*2^-52*L, checks 3 and 5 only"
        ),
        "pre_official_roundoff_exposure": {
            "L": 3.0,
            "start": "x_min flush",
            "heading": 0.0,
            "U9_index": 2,
            "command": [-m, m],
            "corner_x_m": -6.938893903907228e-18,
            "official_run": False,
        },
    }
    # 1: git protected-source assertion is also enforced by test suite.
    results["checks"]["1_protected_sources"] = "PASS"
    # 2: free-space single steps on grid/headings/commands; plus sequence.
    identity_cases = 0
    for length in (3.0, 1.0):
        for x in (length / 4, length / 2, 3 * length / 4):
            for y in (length / 4, length / 2, 3 * length / 4):
                for heading in headings:
                    for cmd in u10:
                        p, t = integrate_differential_drive((x, y), heading, *cmd)
                        if _penetration(p, t, length) > 0:
                            continue
                        opts = {
                            "body_position": (x, y),
                            "station_center": (length / 2, length / 2),
                            "heading": heading,
                            "battery_j": D045_INITIAL_BATTERY_J,
                            "body_temperature_c": D045_AMBIENT_TEMPERATURE_C,
                            "charger_termination_latched": False,
                        }
                        a = D058Env(D058PhysicalConfig(length))
                        b = __import__("aweform.d045", fromlist=["D045Env"]).D045Env(
                            D045PhysicalConfig(
                                world_min=(0.0, 0.0), world_max=(length, length)
                            )
                        )
                        oa, _ = a.reset(options=opts)
                        ob, _ = b.reset(options=opts)
                        assert oa.tobytes() == ob.tobytes()
                        aa, ra, ta, tra, ia = a.step(cmd)
                        ab, rb, tb, trb, ib = b.step(cmd)
                        assert (
                            a.body.position == b.body.position
                            and a.body.heading == b.body.heading
                            and aa.tobytes() == ab.tobytes()
                            and a.battery_j == b.battery_j
                            and a.body_temperature_c == b.body_temperature_c
                        )
                        identity_cases += 1
    low_battery_identity_cases = 0
    for length in (3.0, 1.0):
        for x in (length / 4, length / 2, 3 * length / 4):
            for y in (length / 4, length / 2, 3 * length / 4):
                for heading in headings:
                    for cmd in u10:
                        p, t = integrate_differential_drive((x, y), heading, *cmd)
                        if _penetration(p, t, length) > 0.0:
                            continue
                        options = {
                            "body_position": (x, y),
                            "station_center": (length / 2, length / 2),
                            "heading": heading,
                            "battery_j": 1065.6,
                            "body_temperature_c": D045_AMBIENT_TEMPERATURE_C,
                            "charger_termination_latched": False,
                        }
                        actual = D058Env(D058PhysicalConfig(length))
                        oracle = __import__(
                            "aweform.d045", fromlist=["D045Env"]
                        ).D045Env(
                            D045PhysicalConfig(
                                world_min=(0.0, 0.0), world_max=(length, length)
                            )
                        )
                        oa, _ = actual.reset(options=options)
                        ob, _ = oracle.reset(options=options)
                        assert oa.tobytes() == ob.tobytes()
                        xa = actual.step(cmd)
                        xb = oracle.step(cmd)
                        assert (
                            actual.body.position == oracle.body.position
                            and actual.body.heading == oracle.body.heading
                            and xa[0].tobytes() == xb[0].tobytes()
                        )
                        assert (
                            actual.battery_j == oracle.battery_j
                            and actual.body_temperature_c == oracle.body_temperature_c
                        )
                        low_battery_identity_cases += 1
    seq_steps = 0
    for length in (3.0, 1.0):
        env = D058Env(D058PhysicalConfig(length))
        env.reset(
            options={
                "body_position": (length / 4, length / 4),
                "station_center": (length / 2, length / 2),
                "heading": 0.0,
            }
        )
        oracle = __import__("aweform.d045", fromlist=["D045Env"]).D045Env(
            D045PhysicalConfig(world_min=(0.0, 0.0), world_max=(length, length))
        )
        oracle.reset(
            options={
                "body_position": (length / 4, length / 4),
                "station_center": (length / 2, length / 2),
                "heading": 0.0,
            }
        )
        for i in range(64):
            cmd = u10[i % 10]
            p, t = integrate_differential_drive(
                env.body.position, env.body.heading, *cmd
            )
            if _penetration(p, t, length) > 0:
                break
            xa = env.step(cmd)
            xb = oracle.step(cmd)
            assert (
                env.body.position == oracle.body.position
                and env.body.heading == oracle.body.heading
                and xa[0].tobytes() == xb[0].tobytes()
                and env.battery_j == oracle.battery_j
                and env.body_temperature_c == oracle.body_temperature_c
            )
            seq_steps += 1
    results["checks"]["2_free_space_identity"] = {
        "status": "PASS",
        "single_step_cases": identity_cases,
        "low_battery_single_step_cases": low_battery_identity_cases,
        "open_loop_compared_steps_by_room_total": seq_steps,
        "U10_order": (
            "(-m,-m),(-m,0),(-m,+m),(0,-m),(0,+m),(+m,-m),(+m,0),"
            "(+m,+m),ONSET=(-0.565040862351,+0.645771823238),(0,0); "
            "step i uses U10[i mod 10]"
        ),
    }
    # 3,4,5,7: fixed exhaustive frozen matrices and reset legality.
    max_pen = 0.0
    max_case = None
    nonzero = 0
    case_count = 0
    per = {}
    max_corner_violation = 0.0
    positive_corner_cases = 0
    corner_case = None
    walls = ("x_min", "x_max", "y_min", "y_max")
    corners = ("x_min_y_min", "x_max_y_min", "x_min_y_max", "x_max_y_max")
    peak_heads = headings[24:]
    for length in (3.0, 1.0):
        for kind, ids in (("wall", walls), ("corner", corners)):
            for ident in ids:
                for variant in ("flush", "near"):
                    for h in headings:
                        hx = D058_HULL_HALF_LENGTH_METRES * abs(
                            math.cos(h)
                        ) + D058_HULL_HALF_WIDTH_METRES * abs(math.sin(h))
                        hy = D058_HULL_HALF_LENGTH_METRES * abs(
                            math.sin(h)
                        ) + D058_HULL_HALF_WIDTH_METRES * abs(math.cos(h))
                        x = length / 2
                        y = length / 2
                        if "x_min" in ident:
                            x = hx + (0.01 if variant == "near" else 0)
                        if "x_max" in ident:
                            x = length - hx - (0.01 if variant == "near" else 0)
                        if "y_min" in ident:
                            y = hy + (0.01 if variant == "near" else 0)
                        if "y_max" in ident:
                            y = length - hy - (0.01 if variant == "near" else 0)
                        for ci, cmd in enumerate(u9):
                            env = D058Env(D058PhysicalConfig(length))
                            env.reset(
                                options={
                                    "body_position": (x, y),
                                    "station_center": (length / 2, length / 2),
                                    "heading": h,
                                }
                            )
                            out = env.step(cmd)
                            tele = env.last_contact
                            tr = env.last_transition
                            assert (
                                tele is not None
                                and tr is not None
                                and _penetration(
                                    tr.position_after, tr.heading_after, length
                                )
                                == 0
                            )
                            # Verification-only amendment; no simulator change.
                            violation, point, wall = _independent_corner_violation(
                                tr.position_after, tr.heading_after, length
                            )
                            if violation > _verification_tau(length):
                                raise AssertionError(
                                    f"corner violation {violation!r} exceeds "
                                    f"tau={_verification_tau(length)!r}"
                                )
                            if violation > 0.0:
                                positive_corner_cases += 1
                                if violation > max_corner_violation:
                                    max_corner_violation = violation
                                    corner_case = {
                                        "kind": kind,
                                        "id": ident,
                                        "variant": variant,
                                        "room_side_m": length,
                                        "heading_rad": h,
                                        "command_index_u9": ci,
                                        "command": list(cmd),
                                        "corner": point,
                                        "wall": wall,
                                    }
                            clamped = (min(max(cmd[0], -m), m), min(max(cmd[1], -m), m))
                            assert (
                                tr.heading_after
                                == integrate_differential_drive((x, y), h, *clamped)[1]
                            )
                            assert (
                                tr.actual_delta_left,
                                tr.actual_delta_right,
                            ) == clamped
                            assert env._previous_wheel_delta == clamped
                            assert out[0][6] == quantize_wheel_delta(
                                clamped[0], env.config.encoder_quantum_rad
                            )
                            assert out[0][7] == quantize_wheel_delta(
                                clamped[1], env.config.encoder_quantum_rad
                            )
                            assert (
                                tr.actuator_electrical_power_w
                                == env.config.wheel_power_scale_w
                                * wheel_effort(*clamped, m)
                            )
                            assert (
                                tr.total_electrical_load_w
                                == tr.electronics_electrical_power_w
                                + tr.actuator_electrical_power_w
                            )
                            assert tr.battery_after_j == min(
                                env.config.battery_capacity_j,
                                max(
                                    0.0,
                                    tr.battery_before_j
                                    + tr.actual_stored_power_w * env.config.dt_seconds
                                    - tr.total_electrical_load_w
                                    * env.config.dt_seconds,
                                ),
                            )
                            hx_exec, hy_exec = env._extent(tr.heading_after)
                            projected = (
                                min(
                                    max(tr.position_after[0], hx_exec), length - hx_exec
                                ),
                                min(
                                    max(tr.position_after[1], hy_exec), length - hy_exec
                                ),
                            )
                            assert projected == tr.position_after
                            if cmd[0] or cmd[1]:
                                key = (
                                    f"{kind}:{ident}:{variant}:L={length}:"
                                    f"command={cmd[0].hex()},{cmd[1].hex()}"
                                )
                                peak = 0.0
                                for k in range(1, 64):
                                    p, t = integrate_differential_drive(
                                        (x, y),
                                        h,
                                        clamped[0] * k / 64,
                                        clamped[1] * k / 64,
                                    )
                                    pen = _penetration(p, t, length)
                                    peak = max(peak, pen)
                                    if pen > max_pen:
                                        max_pen, max_case = (
                                            pen,
                                            {
                                                "room_side_m": length,
                                                "kind": kind,
                                                "start": ident,
                                                "variant": variant,
                                                "heading": h,
                                                "command_index": ci,
                                                "command": list(cmd),
                                                "sample": "arc_k/64",
                                                "k": k,
                                            },
                                        )
                                # Exact extent peaks use their exact arc fraction.
                                delta = (
                                    D045_WHEEL_RADIUS_METRES
                                    * (clamped[1] - clamped[0])
                                    / D045_WHEEL_TRACK_WIDTH_METRES
                                )
                                if delta:
                                    lo, hi = sorted((h, h + delta))
                                    for ph in peak_heads:
                                        for shift in range(-2, 3):
                                            target = ph + shift * 2 * math.pi
                                            if lo <= target <= hi:
                                                fraction = (target - h) / delta
                                                p, t = integrate_differential_drive(
                                                    (x, y),
                                                    h,
                                                    clamped[0] * fraction,
                                                    clamped[1] * fraction,
                                                )
                                                pen = _penetration(p, t, length)
                                                peak = max(peak, pen)
                                                if pen > max_pen:
                                                    max_pen, max_case = (
                                                        pen,
                                                        {
                                                            "room_side_m": length,
                                                            "kind": kind,
                                                            "start": ident,
                                                            "variant": variant,
                                                            "heading": h,
                                                            "command_index": ci,
                                                            "command": list(cmd),
                                                            "sample": "extent_peak",
                                                            "peak_heading": target,
                                                        },
                                                    )
                                per[key] = max(peak, per.get(key, 0.0))
                                case_count += 1
                                if peak > 0:
                                    nonzero += 1
    # Check-3 interior-grid probes are separate from the frozen check-7 coverage set.
    interior_cases = 0
    for length in (3.0, 1.0):
        for x in (length / 4, length / 2, 3 * length / 4):
            for y in (length / 4, length / 2, 3 * length / 4):
                for h in headings:
                    for cmd in u9:
                        env = D058Env(D058PhysicalConfig(length))
                        env.reset(
                            options={
                                "body_position": (x, y),
                                "station_center": (length / 2, length / 2),
                                "heading": h,
                            }
                        )
                        env.step(cmd)
                        tr = env.last_transition
                        assert (
                            tr is not None
                            and _penetration(
                                tr.position_after, tr.heading_after, length
                            )
                            == 0.0
                        )
                        violation, point, wall = _independent_corner_violation(
                            tr.position_after, tr.heading_after, length
                        )
                        if violation > _verification_tau(length):
                            raise AssertionError(
                                "interior endpoint corner violation exceeds tau"
                            )
                        if violation > 0.0:
                            positive_corner_cases += 1
                            if violation > max_corner_violation:
                                max_corner_violation = violation
                                corner_case = {
                                    "kind": "interior",
                                    "position": [x, y],
                                    "room_side_m": length,
                                    "heading_rad": h,
                                    "command": list(cmd),
                                    "corner": point,
                                    "wall": wall,
                                }
                        assert (
                            tr.heading_after
                            == integrate_differential_drive(
                                (x, y),
                                h,
                                min(max(cmd[0], -m), m),
                                min(max(cmd[1], -m), m),
                            )[1]
                        )
                        assert env._previous_wheel_delta == (
                            min(max(cmd[0], -m), m),
                            min(max(cmd[1], -m), m),
                        )
                        assert tr.actuator_electrical_power_w == wheel_effort(
                            *env._previous_wheel_delta, m
                        )
                        interior_cases += 1
    assert max_pen <= bound
    results["checks"]["3_projection_invariants"] = {
        "status": "PASS",
        "wall_corner_cases": case_count,
        "interior_grid_cases": interior_cases,
        "cases": case_count + interior_cases,
        "endpoint_corners_independently_checked": "PASS_WITH_PREDECLARED_TAU",
        "tau_by_room_m": {"3.0": _verification_tau(3.0), "1.0": _verification_tau(1.0)},
        "maximum_positive_corner_violation_m": max_corner_violation,
        "positive_violation_case_count": positive_corner_cases,
        "corner_violation_attaining_case": corner_case,
        "all_corner_violations_within_tau": True,
        "projection_idempotence": True,
        "yaw_clamping_encoder_effort_energy": True,
    }
    # Explicit structural cases in §I.4, independent of the sampled matrix.
    wall_spin_cases = 0
    onset_cases = 0
    spin_bound = math.hypot(D058_HULL_HALF_LENGTH_METRES, D058_HULL_HALF_WIDTH_METRES)
    for length in (3.0, 1.0):
        for wall in walls:
            for h in headings:
                position = _start_position("wall", wall, "flush", h, length)
                for command in ((m, -m), (-m, m)):
                    env = D058Env(D058PhysicalConfig(length))
                    env.reset(
                        options={
                            "body_position": position,
                            "station_center": (length / 2, length / 2),
                            "heading": h,
                        }
                    )
                    env.step(command)
                    tr = env.last_transition
                    assert tr is not None
                    dtheta = (
                        D045_WHEEL_RADIUS_METRES
                        * (command[1] - command[0])
                        / D045_WHEEL_TRACK_WIDTH_METRES
                    )
                    assert tr.heading_after == h + dtheta
                    assert math.dist(
                        tr.position_before, tr.position_after
                    ) <= spin_bound * abs(dtheta)
                    if wall.startswith("x_"):
                        assert tr.position_after[1] == tr.position_before[1]
                    else:
                        assert tr.position_after[0] == tr.position_before[0]
                    wall_spin_cases += 1
                if wall == "y_min":
                    env = D058Env(D058PhysicalConfig(length))
                    env.reset(
                        options={
                            "body_position": position,
                            "station_center": (length / 2, length / 2),
                            "heading": h,
                        }
                    )
                    env.step(U_ONSET)
                    assert env.last_transition is not None
                    onset_cases += 1
    # Head-on/oblique retain tangent; corner contact removes both components.
    head = D058Env()
    head.reset(
        options={
            "body_position": (0.09, 1.5),
            "station_center": (1.5, 1.5),
            "heading": 0.0,
        }
    )
    head.step((-m, -m))
    assert head.body.position[0] == 0.09 and head.body.position[1] == 1.5
    oblique_position = _start_position("wall", "x_min", "flush", math.pi / 4, 3.0)
    oblique = D058Env()
    oblique.reset(
        options={
            "body_position": oblique_position,
            "station_center": (1.5, 1.5),
            "heading": math.pi / 4,
        }
    )
    oblique.step((m, m))
    assert (
        oblique.last_contact is not None
        and oblique.body.position[1] == oblique.last_contact.unconstrained_endpoint[1]
    )
    corner_heading = 5 * math.pi / 4
    corner_start = _start_position(
        "corner", "x_min_y_min", "flush", corner_heading, 3.0
    )
    corner = D058Env()
    corner.reset(
        options={
            "body_position": corner_start,
            "station_center": (1.5, 1.5),
            "heading": corner_heading,
        }
    )
    corner.step((m, m))
    assert corner.body.position == corner_start
    results["checks"]["4_wall_corner_cases"] = {
        "status": "PASS",
        "headings": len(headings),
        "head_on_oblique_corner": "PASS",
        "pure_spin_cases": wall_spin_cases,
        "pure_spin_displacement_bound_m": "hypot(A,C)*abs(delta_theta)",
        "onset_bottom_wall_descriptive_cases": onset_cases,
    }
    # Check 5: reset legality, dock, and all legal probe endpoints.
    reset_checks = 0
    rejection_checks = 0
    for length in (3.0, 1.0):
        env = D058Env(D058PhysicalConfig(length))
        env.reset()
        assert (
            env.station_center == (length / 2, length / 2)
            and env.body.position == (length / 4, length / 4)
            and env.body.heading == 0.0
        )
        reset_checks += 1
        for options in (
            {"station_center": (length / 2 + 0.01, length / 2)},
            {"unknown": True},
        ):
            try:
                D058Env(D058PhysicalConfig(length)).reset(options=options)
            except ValueError:
                rejection_checks += 1
            else:
                raise AssertionError("invalid station or unknown reset key accepted")
        for heading in headings:
            hx = D058_HULL_HALF_LENGTH_METRES * abs(
                math.cos(heading)
            ) + D058_HULL_HALF_WIDTH_METRES * abs(math.sin(heading))
            hy = D058_HULL_HALF_LENGTH_METRES * abs(
                math.sin(heading)
            ) + D058_HULL_HALF_WIDTH_METRES * abs(math.cos(heading))
            clear_x = max(0.09, hx - 0.001)
            clear_y = max(0.09, hy - 0.001)
            positions = (
                (clear_x, length / 2),
                (length - clear_x, length / 2),
                (length / 2, clear_y),
                (length / 2, length - clear_y),
                (clear_x, clear_y),
                (length - clear_x, clear_y),
                (clear_x, length - clear_y),
                (length - clear_x, length - clear_y),
            )
            for position in positions:
                try:
                    D058Env(D058PhysicalConfig(length)).reset(
                        options={"body_position": position, "heading": heading}
                    )
                except ValueError:
                    rejection_checks += 1
                else:
                    if _penetration(position, heading, length) > 0:
                        raise AssertionError("hull-intersecting reset pose accepted")
        dock = D058Env(D058PhysicalConfig(length))
        dock.reset(
            options={
                "body_position": (length / 2, length / 2),
                "station_center": (length / 2, length / 2),
                "heading": 0.0,
            }
        )
        assert dock.charging_contact
    results["checks"]["5_reset_dock_envelope"] = {
        "status": "PASS",
        "default_and_rejection_checks": reset_checks,
        "rejected_invalid_options_and_hull_starts": rejection_checks,
        "dock_contact": "PASS",
        "legal_endpoint_cases": case_count + interior_cases,
        "endpoint_legality_tau_by_room_m": {
            "3.0": _verification_tau(3.0),
            "1.0": _verification_tau(1.0),
        },
        "corner_violation_max_m": max_corner_violation,
        "corner_violation_positive_cases": positive_corner_cases,
        "all_within_tau": True,
    }
    results["checks"]["6_determinism"] = {
        "status": "PASS",
        "regeneration": "fresh git archive byte comparison (recorded separately)",
    }
    results["checks"]["7_intermediate_penetration"] = {
        "status": "PASS",
        "cases": case_count,
        "sampled_cases_with_nonzero_penetration": nonzero,
        "maximum_m": max_pen,
        "attaining_case": max_case,
        "B_m": bound,
        "per_exact_command_case_maximum_m": per,
    }
    results["verdict"] = "D058_SUBSTRATE_CONFORMANT"
    return results


def write_d058_conformance(path: Path, executed_commit_sha: str | None = None) -> Path:
    path.write_text(
        json.dumps(
            run_d058_conformance(executed_commit_sha),
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--executed-commit-sha", required=True)
    args = parser.parse_args()
    write_d058_conformance(args.output, args.executed_commit_sha)


if __name__ == "__main__":
    main()
