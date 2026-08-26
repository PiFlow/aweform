"""EXP-003 localized charging station environment and controller boundary.

This module is intentionally additive.  The historical EXP-001/EXP-002 field
environment and controllers remain in their original modules.  EXP-003 uses a
station beacon for sensing and a separate physical-zone test for charging.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar, Final

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from .body import Body, Coordinate
from .energy import EnergyConfig, advance_energy
from .env import Action
from .exp001 import (
    EXP001_EXPLORER_HAZARD,
    ExternalObservation,
    StochasticPersistentExplorer,
)
from .rng import RandomStreams

EXP003_CHARGING_RADIUS: Final[float] = 0.10
EXP003_CHARGE_RATE: Final[float] = 0.5
EXP003_BEACON_SCALE: Final[float] = 0.25
EXP003_INITIAL_STATION_MIN_SEPARATION: Final[float] = 0.20
EXP003_STATION_PLACEMENT_MAX_ATTEMPTS: Final[int] = 10_000
EXP003_HORIZON: Final[int] = 1000
EXP003_COVERAGE_GRID_WIDTH: Final[int] = 32
EXP003_COVERAGE_GRID_HEIGHT: Final[int] = 32
EXP003_B50_ENTER_SEEK_THRESHOLD: Final[float] = 0.50
EXP003_TREND_ANTICIPATORY_ENERGY_THRESHOLD: Final[float] = 0.65
EXP003_TREND_WEAK_BEACON_THRESHOLD: Final[float] = 0.10


@dataclass(frozen=True, slots=True)
class BeaconObservation:
    """Controller-visible idealized station-beacon and contact readings."""

    left: float
    forward: float
    right: float
    charging_contact: bool

    def __post_init__(self) -> None:
        for name in ("left", "forward", "right"):
            _validate_beacon_component(name, getattr(self, name))
        if not isinstance(self.charging_contact, bool):
            raise ValueError("charging_contact must be a bool")

    def as_tuple(self) -> tuple[float, float, float]:
        """Return only the directional beacon values."""
        return (self.left, self.forward, self.right)


@dataclass(frozen=True, slots=True)
class StationObservation:
    """Complete STATION_B50 controller observation.

    Station coordinates, true distance, coverage, and all other evaluator
    diagnostics are deliberately absent from this type.
    """

    energy: float
    beacon: BeaconObservation

    def __post_init__(self) -> None:
        _validate_normalized_value("energy", self.energy)
        if not isinstance(self.beacon, BeaconObservation):
            raise ValueError("beacon must be a BeaconObservation")


@dataclass(frozen=True, slots=True)
class EXP003StationConfig:
    """EXP-003 development configuration.

    The values inherited from the field environment are repeated explicitly
    so the new ecological mechanism cannot silently inherit later changes.
    """

    world_min: Coordinate = (0.0, 0.0)
    world_max: Coordinate = (1.0, 1.0)
    energy: EnergyConfig = field(
        default_factory=lambda: EnergyConfig(maximum_energy=10.0, basal_cost=0.1)
    )
    initial_energy: float = 5.0
    movement_distance: float = 0.05
    turn_angle: float = math.pi / 4.0
    wait_cost: float = 0.0
    turn_cost: float = 0.02
    movement_cost: float = 0.1
    probe_distance: float = 0.1
    sensor_angle: float = math.pi / 4.0
    charging_radius: float = EXP003_CHARGING_RADIUS
    charge_rate: float = EXP003_CHARGE_RATE
    beacon_scale: float = EXP003_BEACON_SCALE
    initial_station_min_separation: float = EXP003_INITIAL_STATION_MIN_SEPARATION
    station_placement_max_attempts: int = EXP003_STATION_PLACEMENT_MAX_ATTEMPTS
    episode_horizon: int = EXP003_HORIZON

    def __post_init__(self) -> None:
        _validate_bounds(self.world_min, self.world_max)
        _require_finite("initial_energy", self.initial_energy)
        if not (
            self.energy.failure_boundary
            < self.initial_energy
            <= self.energy.maximum_energy
        ):
            raise ValueError(
                "initial_energy must be above failure_boundary and at most "
                "maximum_energy"
            )
        for name in (
            "movement_distance",
            "turn_angle",
            "wait_cost",
            "turn_cost",
            "movement_cost",
            "probe_distance",
            "sensor_angle",
            "charging_radius",
            "charge_rate",
            "initial_station_min_separation",
        ):
            _require_non_negative(name, getattr(self, name))
        _require_finite("beacon_scale", self.beacon_scale)
        if self.beacon_scale <= 0:
            raise ValueError("beacon_scale must be positive")
        width = self.world_max[0] - self.world_min[0]
        height = self.world_max[1] - self.world_min[1]
        if self.charging_radius > min(width, height) / 2.0:
            raise ValueError("charging_radius must fit inside the world")
        if self.initial_station_min_separation < self.charging_radius:
            raise ValueError(
                "initial_station_min_separation must be at least charging_radius"
            )
        _require_positive_int(
            "station_placement_max_attempts", self.station_placement_max_attempts
        )
        _require_positive_int("episode_horizon", self.episode_horizon)


@dataclass(frozen=True, slots=True)
class EXP003TransitionTelemetry:
    """Evaluator-only telemetry for one station-environment transition."""

    step_index: int
    action: Action
    position_before: Coordinate
    position_after: Coordinate
    energy_before: float
    harvested_energy: float
    basal_cost: float
    action_cost: float
    energy_after: float
    charging_contact_before: bool
    charging_contact_after: bool
    terminated: bool
    truncated: bool


class LocalizedChargingStationEnv(gym.Env[np.ndarray, int]):
    """Bounded body with a stationary physical charging zone and beacon."""

    metadata: dict[str, object] = {"render_modes": []}

    def __init__(self, config: EXP003StationConfig | None = None) -> None:
        self.config = config or EXP003StationConfig()
        self.action_space = spaces.Discrete(len(Action))
        self.observation_space = spaces.Box(
            low=np.zeros(5, dtype=np.float32),
            high=np.ones(5, dtype=np.float32),
            dtype=np.float32,
        )
        self.body: Body | None = None
        self.station_center: Coordinate | None = None
        self.random_streams: RandomStreams | None = None
        self._step_count = 0
        self._episode_done = True
        self.last_transition: EXP003TransitionTelemetry | None = None

    @property
    def charging_contact(self) -> bool:
        """Return physical zone occupancy from evaluator-side state."""
        if self.body is None or self.station_center is None:
            raise RuntimeError("environment must be reset before observing")
        return _charging_contact(
            self.body.position,
            self.station_center,
            self.config.charging_radius,
        )

    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict[str, object] | None = None,
    ) -> tuple[np.ndarray, dict[str, object]]:
        """Create a seeded body and station, initially separated by policy."""
        del options
        super().reset(seed=seed)
        environment_seed = (
            int(self.np_random.integers(0, np.iinfo(np.uint64).max, dtype=np.uint64))
            if seed is None
            else seed
        )
        self.random_streams = RandomStreams.from_seed(environment_seed)
        environment_rng = self.random_streams.environment
        # The historical field environment draws one two-coordinate source
        # position before drawing the body start.  Consume the same
        # compatibility draw so FIELD_B50 and STATION_B50 share body position
        # and heading for a matched ordinary seed; the value is not retained.
        environment_rng.uniform(
            low=np.asarray(self.config.world_min, dtype=float),
            high=np.asarray(self.config.world_max, dtype=float),
        )
        position_array = environment_rng.uniform(
            low=np.asarray(self.config.world_min, dtype=float),
            high=np.asarray(self.config.world_max, dtype=float),
        )
        position = (float(position_array[0]), float(position_array[1]))
        heading = float(environment_rng.uniform(0.0, math.tau))
        station_center = _sample_station_center(
            environment_rng,
            body_position=position,
            config=self.config,
        )
        self.body = Body(
            x=position[0],
            y=position[1],
            heading=heading,
            energy=self.config.initial_energy,
        )
        self.station_center = station_center
        self._step_count = 0
        self._episode_done = False
        self.last_transition = None
        return self._observation(), {}

    def step(
        self, action: int
    ) -> tuple[np.ndarray, float, bool, bool, dict[str, object]]:
        """Apply one action and charge only at the post-transition position."""
        if self._episode_done:
            raise RuntimeError("episode is over; call reset() before step()")
        if not self.action_space.contains(action):
            raise ValueError(f"action must be one of {list(Action)}")
        if self.body is None or self.station_center is None:
            raise RuntimeError("environment must be reset before step()")

        selected_action = Action(int(action))
        position_before = self.body.position
        energy_before = self.body.energy
        charging_contact_before = self.charging_contact
        if selected_action is Action.TURN_LEFT:
            self.body.turn(self.config.turn_angle)
            action_cost = self.config.turn_cost
        elif selected_action is Action.TURN_RIGHT:
            self.body.turn(-self.config.turn_angle)
            action_cost = self.config.turn_cost
        elif selected_action is Action.MOVE_FORWARD:
            self.body.move_forward(
                self.config.movement_distance,
                world_min=self.config.world_min,
                world_max=self.config.world_max,
            )
            action_cost = self.config.movement_cost
        else:
            action_cost = self.config.wait_cost

        charging_contact_after = self.charging_contact
        harvested_energy = self.config.charge_rate if charging_contact_after else 0.0
        next_energy = advance_energy(
            self.body.energy,
            harvested_energy=harvested_energy,
            config=self.config.energy,
            action_cost=action_cost,
        )
        self.body.energy = next_energy.energy
        self._step_count += 1
        terminated = not next_energy.viable
        truncated = not terminated and self._step_count >= self.config.episode_horizon
        self._episode_done = terminated or truncated
        self.last_transition = EXP003TransitionTelemetry(
            step_index=self._step_count,
            action=selected_action,
            position_before=position_before,
            position_after=self.body.position,
            energy_before=energy_before,
            harvested_energy=harvested_energy,
            basal_cost=self.config.energy.basal_cost,
            action_cost=action_cost,
            energy_after=next_energy.energy,
            charging_contact_before=charging_contact_before,
            charging_contact_after=charging_contact_after,
            terminated=terminated,
            truncated=truncated,
        )
        return self._observation(), 0.0, terminated, truncated, {}

    def _observation(self) -> np.ndarray:
        if self.body is None or self.station_center is None:
            raise RuntimeError("environment must be reset before observing")
        energy_range = (
            self.config.energy.maximum_energy - self.config.energy.failure_boundary
        )
        energy_signal = (
            self.body.energy - self.config.energy.failure_boundary
        ) / energy_range
        beacon = sample_directional_beacon(
            self.body,
            self.station_center,
            probe_distance=self.config.probe_distance,
            sensor_angle=self.config.sensor_angle,
            beacon_scale=self.config.beacon_scale,
        )
        return np.asarray(
            (
                energy_signal,
                beacon.left,
                beacon.forward,
                beacon.right,
                float(self.charging_contact),
            ),
            dtype=np.float32,
        )


@dataclass(frozen=True, slots=True)
class DirectionalBeacon:
    """Pure evaluator calculation for the three virtual directional probes."""

    left: float
    forward: float
    right: float

    def as_tuple(self) -> tuple[float, float, float]:
        return (self.left, self.forward, self.right)


def beacon_signal(distance: float, beacon_scale: float = EXP003_BEACON_SCALE) -> float:
    """Return the deterministic idealized IR-like signal at ``distance``."""
    _require_finite("distance", distance)
    _require_finite("beacon_scale", beacon_scale)
    if distance < 0:
        raise ValueError("distance must be non-negative")
    if beacon_scale <= 0:
        raise ValueError("beacon_scale must be positive")
    return 1.0 / (1.0 + (distance / beacon_scale) ** 2)


def sample_directional_beacon(
    body: Body,
    station_center: Coordinate,
    *,
    probe_distance: float,
    sensor_angle: float,
    beacon_scale: float = EXP003_BEACON_SCALE,
) -> DirectionalBeacon:
    """Sample deterministic L/F/R beacon values without consuming RNG."""
    _require_finite("probe_distance", probe_distance)
    _require_finite("sensor_angle", sensor_angle)
    if probe_distance < 0:
        raise ValueError("probe_distance must be non-negative")
    _validate_coordinate("station_center", station_center)

    def sample(direction: float) -> float:
        probe = (
            body.x + probe_distance * math.cos(direction),
            body.y + probe_distance * math.sin(direction),
        )
        return beacon_signal(math.dist(probe, station_center), beacon_scale)

    return DirectionalBeacon(
        left=sample(body.heading + sensor_angle),
        forward=sample(body.heading),
        right=sample(body.heading - sensor_angle),
    )


class EXP003Mode(Enum):
    """STATION_B50 modes."""

    EXPLORE = "EXPLORE"
    SEEK = "SEEK"
    CHARGE = "CHARGE"


class EXP003SeekTrigger(Enum):
    """Controller-visible reason for entering SEEK from EXPLORE."""

    HISTORICAL_ENERGY = "HISTORICAL_ENERGY_BELOW_0.50"
    ANTICIPATORY_TREND = "ANTICIPATORY_BEACON_TREND"


@dataclass(frozen=True, slots=True)
class EXP003ControllerDecision:
    """Visible-signal decision trace retained for evaluator diagnostics only.

    The trace is not an additional observation.  Its optional beacon values
    are copied from the current decision's controller-visible L/F/R values and
    the controller's one previous EXPLORE maximum.
    """

    seek_trigger: EXP003SeekTrigger | None = None
    anticipatory_current_max_beacon: float | None = None
    anticipatory_previous_max_beacon: float | None = None


@dataclass(frozen=True, slots=True)
class EXP003ControllerConfig:
    """B50-derived station controller thresholds."""

    enter_seek: float = EXP003_B50_ENTER_SEEK_THRESHOLD
    recover: float = 0.85
    exploration_hazard: float = EXP001_EXPLORER_HAZARD

    def __post_init__(self) -> None:
        _validate_normalized_value("enter_seek", self.enter_seek)
        _validate_normalized_value("recover", self.recover)
        if not self.enter_seek < self.recover:
            raise ValueError("enter_seek must be less than recover")
        if self.exploration_hazard != EXP001_EXPLORER_HAZARD:
            raise ValueError("EXP-003 must use the historical exploration hazard")


class StationB50Controller:
    """B50-derived controller adapted to physical charging contact."""

    # ``config`` is exposed as a read-only property backed by the ``_config``
    # slot, so the construction-invariant binding cannot be rebound by
    # assignment, ``del``, OR by direct mutation of ``vars(self)["config"]``
    # (the property data-descriptor shadows any ``__dict__`` entry).  The
    # backing ``_config`` slot is itself frozen by ``__setattr__``/``__delattr__``
    # below, so a caller cannot ``del c._config`` then ``c._config = adv`` to
    # swap in a branch-dependent configuration through the read-only property.
    # The remaining attrs live in the normal ``__dict__``.
    __slots__ = ("_config", "__dict__")
    # Typed slot so mypy resolves the ``config`` property's return and the
    # ``__setattr__``/``__delattr__`` guards against the backing storage.
    _config: EXP003ControllerConfig

    # ADR 0009 Section D retained-state declaration.  Each controller declares
    # its own entries; ``docs/adr/0009-bohs-registry.md`` is the union of
    # these declarations plus the nested retained state of the objects named
    # here (``explorer.policy_rng`` and the segment counters).  The values are
    # registry classifications, not runtime data.
    RETAINED_STATE: ClassVar[dict[str, str]] = {
        "_mode": "causal-inherited: EXP-003 three-mode form",
        "config": (
            "causal-inherited: construction-invariant EXP003ControllerConfig; "
            "controller-visible binding is a read-only property (no setter/"
            "deleter) backed by the _config slot, and both the property and "
            "the backing _config slot are frozen for the run"
        ),
        "explorer": (
            "causal-inherited: EXP-001 run-and-turn primitive; nested "
            "policy_rng, _forward_actions_remaining, _turn_action, "
            "_turn_actions_remaining"
        ),
        "_last_decision": "diagnostic: no action-selection reads",
    }

    def __setattr__(self, name: str, value: object) -> None:
        # ADR 0009 B.5: ``config`` must be construction-invariant — initialized
        # before the first act(), immutable for the run, independent of
        # observations/history, and unable to encode a branch bit.  The frozen
        # EXP003ControllerConfig value alone is insufficient: the public
        # ``config`` binding on the controller had to be frozen as well, or a
        # caller could swap in a branch-dependent configuration between act()
        # calls and C2/E1 would read through that binding.  Both ``config`` and
        # its backing ``_config`` slot are rejected so no assignment (including
        # ``del c._config`` then ``c._config = adv``) can swap the value the
        # read-only property returns; construction writes the ``_config`` slot
        # directly via ``object.__setattr__`` in ``__init__``.
        if name in ("config", "_config"):
            raise AttributeError(
                "config is construction-invariant and immutable for the run"
            )
        object.__setattr__(self, name, value)

    def __delattr__(self, name: str) -> None:
        # ADR 0009 B.5 (cont.): reject deletion of the ``config`` binding AND
        # its backing ``_config`` slot, so the construction write is the only
        # write across the controller's lifetime.  A binding a caller could
        # remove with ``del`` (then re-create through a rebound ``__setattr__``)
        # is not read-only — and with the property reading ``_config``, an
        # unguarded ``del c._config`` would be the same swap through a different
        # door.
        if name in ("config", "_config"):
            raise AttributeError(
                "config is construction-invariant and immutable for the run"
            )
        object.__delattr__(self, name)

    @property
    def config(self) -> EXP003ControllerConfig:
        """The construction-invariant configuration (read-only binding)."""
        return self._config

    def __init__(
        self,
        policy_rng: np.random.Generator,
        config: EXP003ControllerConfig | None = None,
    ) -> None:
        # Write the backing slot directly: the ``_config`` name is frozen by
        # ``__setattr__``, so the construction value is the only write allowed,
        # performed here via ``object.__setattr__``.
        object.__setattr__(self, "_config", config or EXP003ControllerConfig())
        self.explorer = StochasticPersistentExplorer(policy_rng)
        self._mode = EXP003Mode.EXPLORE
        self._last_decision = EXP003ControllerDecision()

    @property
    def mode(self) -> EXP003Mode:
        return self._mode

    @property
    def last_decision(self) -> EXP003ControllerDecision:
        """Return the visible-signal trace for the most recent decision."""
        return self._last_decision

    def act(self, observation: StationObservation) -> Action:
        """Choose using energy, L/F/R beacon, and causal contact only."""
        if not isinstance(observation, StationObservation):
            raise ValueError("observation must be a StationObservation")
        self._last_decision = EXP003ControllerDecision()
        if self._mode is EXP003Mode.EXPLORE:
            if observation.energy < self.config.enter_seek:
                self._last_decision = EXP003ControllerDecision(
                    seek_trigger=EXP003SeekTrigger.HISTORICAL_ENERGY
                )
                self._mode = EXP003Mode.SEEK
            else:
                return self._explore_action(observation.beacon)

        if self._mode is EXP003Mode.SEEK:
            if observation.beacon.charging_contact:
                self._mode = EXP003Mode.CHARGE
                return Action.WAIT
            return seek_beacon_action(observation.beacon)

        if not observation.beacon.charging_contact:
            self._mode = EXP003Mode.SEEK
            return seek_beacon_action(observation.beacon)
        if observation.energy > self.config.recover:
            self._mode = EXP003Mode.EXPLORE
            self.explorer.begin_segment()
            return self._explore_action(observation.beacon)
        return Action.WAIT

    def reset(self) -> None:
        self._mode = EXP003Mode.EXPLORE
        self.explorer.begin_segment()
        self._last_decision = EXP003ControllerDecision()

    def _explore_action(self, beacon: BeaconObservation) -> Action:
        """Reuse the historical stochastic primitive through an internal adapter."""
        return self.explorer.act(
            ExternalObservation(beacon.left, beacon.forward, beacon.right)
        )


class StationB50FullController(StationB50Controller):
    """Additive B50 variant that remains docked until normalized energy is 1.0."""

    def act(self, observation: StationObservation) -> Action:
        """Use the historical policy with full-recovery CHARGE semantics."""
        if not isinstance(observation, StationObservation):
            raise ValueError("observation must be a StationObservation")
        self._last_decision = EXP003ControllerDecision()
        if self._mode is EXP003Mode.EXPLORE:
            if observation.energy < self.config.enter_seek:
                self._last_decision = EXP003ControllerDecision(
                    seek_trigger=EXP003SeekTrigger.HISTORICAL_ENERGY
                )
                self._mode = EXP003Mode.SEEK
            else:
                return self._explore_action(observation.beacon)

        if self._mode is EXP003Mode.SEEK:
            if observation.beacon.charging_contact:
                self._mode = EXP003Mode.CHARGE
                return Action.WAIT
            return seek_beacon_action(observation.beacon)

        if not observation.beacon.charging_contact:
            self._mode = EXP003Mode.SEEK
            return seek_beacon_action(observation.beacon)
        if observation.energy >= 1.0:
            self._mode = EXP003Mode.EXPLORE
            self.explorer.begin_segment()
            return self._explore_action(observation.beacon)
        return Action.WAIT


class StationB50TrendController(StationB50Controller):
    """Development-only B50 variant with one-step beacon-trend memory.

    The only persistent temporal state is the previous EXPLORE decision's
    maximum of the visible left/forward/right beacon values.  The 0.65 energy
    and 0.10 beacon thresholds are provisional development hypotheses, not
    calibrated scientific values.
    """

    # ADR 0009 Section D: the one authorised BOHS field added by this class.
    # The manifest (docs/adr/0009-bohs-registry.md) is the union of this
    # declaration and the base class's.
    RETAINED_STATE: ClassVar[dict[str, str]] = {
        "_previous_explore_beacon_max": (
            "bohs; type float|None; write = max of current beacon L/F/R "
            "(B.2); clears at init, E1, E2, C2, reset (B.3); readers = the "
            "EXPLORE-entry snapshot (loaded into previous_max on every "
            "EXPLORE path before any guard), the E2 navigation guard, and the "
            "previous_explore_beacon_max property; budget 1"
        ),
    }

    def __init__(
        self,
        policy_rng: np.random.Generator,
        config: EXP003ControllerConfig | None = None,
    ) -> None:
        super().__init__(policy_rng, config)
        self._previous_explore_beacon_max: float | None = None

    @property
    def previous_explore_beacon_max(self) -> float | None:
        """Return the one previous EXPLORE beacon maximum, if one exists."""
        return self._previous_explore_beacon_max

    def act(self, observation: StationObservation) -> Action:
        """Apply historical B50 plus the one-step anticipatory guard."""
        if not isinstance(observation, StationObservation):
            raise ValueError("observation must be a StationObservation")
        self._last_decision = EXP003ControllerDecision()
        if self._mode is EXP003Mode.EXPLORE:
            current_max = max(observation.beacon.as_tuple())
            previous_max = self._previous_explore_beacon_max
            if observation.energy < self.config.enter_seek:
                self._last_decision = EXP003ControllerDecision(
                    seek_trigger=EXP003SeekTrigger.HISTORICAL_ENERGY
                )
                self._previous_explore_beacon_max = None
                self._mode = EXP003Mode.SEEK
            elif (
                observation.energy < EXP003_TREND_ANTICIPATORY_ENERGY_THRESHOLD
                and current_max < EXP003_TREND_WEAK_BEACON_THRESHOLD
                and previous_max is not None
                and current_max < previous_max
            ):
                self._last_decision = EXP003ControllerDecision(
                    seek_trigger=EXP003SeekTrigger.ANTICIPATORY_TREND,
                    anticipatory_current_max_beacon=current_max,
                    anticipatory_previous_max_beacon=previous_max,
                )
                self._previous_explore_beacon_max = None
                self._mode = EXP003Mode.SEEK
            else:
                self._previous_explore_beacon_max = current_max
                return self._explore_action(observation.beacon)

        if self._mode is EXP003Mode.SEEK:
            if observation.beacon.charging_contact:
                self._mode = EXP003Mode.CHARGE
                return Action.WAIT
            return seek_beacon_action(observation.beacon)

        if not observation.beacon.charging_contact:
            self._mode = EXP003Mode.SEEK
            return seek_beacon_action(observation.beacon)
        if observation.energy > self.config.recover:
            self._mode = EXP003Mode.EXPLORE
            self.explorer.begin_segment()
            self._previous_explore_beacon_max = None
            return self._explore_action(observation.beacon)
        return Action.WAIT

    def reset(self) -> None:
        super().reset()
        self._previous_explore_beacon_max = None


def seek_beacon_action(observation: BeaconObservation) -> Action:
    """Use the historical L/F/R steering tie convention on beacon values."""
    if not isinstance(observation, BeaconObservation):
        raise ValueError("observation must be a BeaconObservation")
    left, forward, right = observation.as_tuple()
    if left == forward == right:
        return Action.TURN_LEFT
    if forward >= left and forward >= right:
        return Action.MOVE_FORWARD
    if left > right:
        return Action.TURN_LEFT
    return Action.TURN_RIGHT


def _sample_station_center(
    rng: np.random.Generator,
    *,
    body_position: Coordinate,
    config: EXP003StationConfig,
) -> Coordinate:
    """Reject candidates at or within the configured initial separation.

    Candidates are sampled uniformly from the valid centre rectangle.  The
    first candidate with ``distance(body, station) > minimum_separation`` is
    selected.  Exactly ``station_placement_max_attempts`` candidates are
    allowed before a deterministic runtime error; no fallback or extra RNG
    source is used.
    """
    low = np.asarray(
        (
            config.world_min[0] + config.charging_radius,
            config.world_min[1] + config.charging_radius,
        ),
        dtype=float,
    )
    high = np.asarray(
        (
            config.world_max[0] - config.charging_radius,
            config.world_max[1] - config.charging_radius,
        ),
        dtype=float,
    )
    for _ in range(config.station_placement_max_attempts):
        candidate_array = rng.uniform(low=low, high=high)
        candidate = (float(candidate_array[0]), float(candidate_array[1]))
        if math.dist(body_position, candidate) > config.initial_station_min_separation:
            return candidate
    raise RuntimeError(
        "station placement exceeded the deterministic rejection-attempt limit"
    )


def _charging_contact(
    body_position: Coordinate,
    station_center: Coordinate,
    radius: float,
) -> bool:
    return math.dist(body_position, station_center) <= radius


def _validate_bounds(world_min: Coordinate, world_max: Coordinate) -> None:
    _validate_coordinate("world_min", world_min)
    _validate_coordinate("world_max", world_max)
    if not all(lower < upper for lower, upper in zip(world_min, world_max)):
        raise ValueError("world_min must be strictly below world_max")


def _validate_coordinate(name: str, coordinate: Coordinate) -> None:
    try:
        valid = len(coordinate) == 2 and all(
            math.isfinite(float(value)) for value in coordinate
        )
    except (TypeError, ValueError):
        valid = False
    if not valid:
        raise ValueError(f"{name} must contain two finite coordinates")


def _require_finite(name: str, value: float) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


def _require_non_negative(name: str, value: float) -> None:
    _require_finite(name, value)
    if value < 0:
        raise ValueError(f"{name} must be non-negative")


def _require_positive_int(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")


def _validate_normalized_value(name: str, value: float) -> float:
    _require_finite(name, value)
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be finite and within [0, 1]")
    return value


def _validate_beacon_component(name: str, value: float) -> float:
    """Reject every non-built-in-float L/F/R adversary at the boundary.

    Only an exact built-in ``float`` is accepted.  ``int`` and ``bool``
    (Python integers are arbitrary-precision, unlike the IEEE-754 double the
    observation contract uses, and ``bool`` is an ``int`` subclass) and any
    non-built-in numeric such as ``numpy.float64`` are rejected so the value
    passed to ``max`` in the trend controller's observation write is a genuine
    built-in float (ADR 0009 B.1).
    """
    if type(value) is not float:
        raise ValueError(f"{name} must be a built-in float")
    return _validate_normalized_value(name, value)
