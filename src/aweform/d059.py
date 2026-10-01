"""D-059 result-free implementation and frozen S1 re-baseline runner.

The official protocol is deliberately reachable only through this module's CLI.
Unit tests use ``run_test_lifetime`` with test-only seed 26320 and constructed
starts outside the frozen Part-A matrix.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from collections import Counter, deque
from dataclasses import dataclass, field, replace
from decimal import Decimal
from pathlib import Path
from typing import Any, Final, Sequence, cast

import numpy as np

from . import d053, d054, d058
from .d045 import (
    D045_AMBIENT_TEMPERATURE_C,
    D045_BATTERY_CAPACITY_J,
    D045_DT_SECONDS,
    D045Env,
    D045PhysicalConfig,
)
from .d050 import D050ControlMode
from .d052 import D052CommandSource, D052Controller, D052Mode
from .d053 import D053Proposal, D053RoamingFixture
from .d055 import D055StallTurnCandidate
from .d058 import D058Env, D058PhysicalConfig
from .exp003_seed_policy import validate_exp003_development_seeds

D059_ID: Final = "D-059"
PROTOCOL_VERSION: Final = "d059-v05-s1-level1-floor-rebaseline-v2"
BASE_SHA: Final = "0f4b0ae22564293dd178567c4c745e5903256682"
FROZEN_BRIEF_SHA256: Final = (
    "2cfcf87fa589becfefb9e5d1bcf56b6bfd8dbca9607c494e10c101cb875aade6"
)
PRIMARY_SEEDS: Final = tuple(range(26000, 26320))
ENDURANCE_SEEDS: Final = tuple(range(26000, 26060))
PRIMARY_ONLY_SEEDS: Final = tuple(range(26060, 26320))
TEST_SEED: Final = 26320
D045_SUPPORT_SEEDS: Final = (22053, 22054, 22055, 22056, 22057)
H_PRIMARY: Final = 140_000
W_C: Final = 2_000
H_ENDURANCE: Final = 300_000
H_PART_A: Final = 2_000
ALPHA: Final = 0.05
P_STAR: Final = 0.01
ARTIFACT_QUANTUM: Final = Decimal("1e-12")
MAX_EVENT_ROWS: Final = 4096
ROOMS: Final = {"S1_3M": 3.0, "S1_1M": 1.0, "D045_1M": 1.0}
ARMS: Final = ("U", "C")
PART_A_SETS: Final = ("A1_WALL_CORNER", "A2_ROOM_RANGE")
FAILURE_OUTCOMES: Final = frozenset(
    {"SPIN_EXHAUSTED", "INVALID_BEACON", "RETURN_TIMEOUT_FAILURE"}
)
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
    "src/aweform/d058.py",
    "src/aweform/development_visualizer.py",
    "src/aweform/exp001.py",
    "src/aweform/exp003.py",
    "src/aweform/body.py",
    "src/aweform/env.py",
    "src/aweform/exp003_seed_policy.py",
)
PROTECTED_SHA256: Final[dict[str, str]] = dict(
    zip(
        PROTECTED,
        (
            "b137b80df53894d96684e6a2513d33f4b6bc39c23dfeeba0476d2949387ca774",
            "85253a9277523f8ca689638b2720fd582f6b43650be2eb0cb4fcbb8af7d3921a",
            "c9a031545a5a6dcbe732994f7d3c3534d4d1b22ec1b82c78e7d9f98e74666358",
            "4c93a3dd8171380370e212547c8ed90dad5359477fb685489e33fbcaa00d09a4",
            "45754c9e4536370f5e969cca6e4e3f59232d435ba289abf7efd82fa965b868e7",
            "d3664b318a42a53b6f524449c12337096999bbd42eb1d27a6d3da4aeca6b7313",
            "2ced64b2c524f542f8cb83f2c3dafeb526dd37d8533eba298ea15bb268703693",
            "8bf7370f86cac5ed8a580d0456cd7111f90f1108994de1b64761e69cc95ca518",
            "ceb93c5fb930d5fb8ee25448fbcd272408b327a532cc60317430d34662602ca8",
            "8ee22b6185114ef200604671bfcaf61efc728b665d69ca2ded18ba948fb1d9ee",
            "11073ae8f30a561b7760b8a4939e9cf7b68bd60b1cc86b29845178be42558ca5",
            "f644cb14ae56446af5ad2ca8d8d61eef5c8a9d1d6c18fdaf4362ca7441c71be7",
            "72f3d67651b95df6d395dc9f57f49b20bf92dc8c28603941fe0b89121b9cb9f2",
            "3d5d1bfd6b231591bb1515dc495f5dbb743b0dda1e8a8adcbc1414ff93a94236",
            "c61832671a3dd5e3d40435304153a521bf925d4be24c964984e157c429d2cb19",
            "b624a117ef947f41a3c494d017d398dd0212a0f7975698922f0f455a87ea0f8d",
        ),
        strict=True,
    )
)

_INVALIDATED_PROVENANCE: Final = (
    {
        "kind": "interrupted_pre_freeze_launch",
        "allocation": "retired 23000-23319",
        "count": 2,
        "status": "INVALIDATED_ZERO_EVIDENCE",
        "outcome_reconstruction": "PROHIBITED_AND_NOT_PERFORMED",
    },
    {
        "kind": "pre_freeze_part_a_execution",
        "allocation": "fixed D-059 Part-A matrix",
        "status": "INVALIDATED_VALIDATION_ONLY_ZERO_EVIDENCE",
        "outcome_reconstruction": "PROHIBITED_AND_NOT_PERFORMED",
    },
    {
        "kind": "disqualified_candidate",
        "candidate": "C / GLM-5.3-Flash",
        "reason": "frozen result-free/isolation constraint violation",
        "status": "DISQUALIFIED_BOUNDARY_COMPLIANCE_FAILURE",
        "code_quality_inference": "NONE",
        "outcome_reconstruction": "PROHIBITED_AND_NOT_PERFORMED",
    },
    {
        "kind": "exposed_allocation",
        "allocation": "retired 24000-24319; test-only 24320",
        "status": "RETIRED_NO_FINAL_EVIDENCE_USE",
        "outcome_reconstruction": "PROHIBITED_AND_NOT_PERFORMED",
    },
)


@dataclass(frozen=True, slots=True)
class _ZeroProposal:
    symbolic_action: None
    wheel_command: tuple[float, float] = (0.0, 0.0)


@dataclass(frozen=True, slots=True)
class D059Start:
    """Explicit evaluator reset state; never passed to organism code."""

    case_id: str
    support_set: str
    position: tuple[float, float]
    heading: float
    boundary_class: str
    clearance_m: float | None = None
    along_wall_fraction: float | None = None


@dataclass(frozen=True, slots=True)
class D059PhysicalConfig:
    """D-059-local copy of the D-058 config with only horizon overridden."""

    room_side_m: float
    episode_horizon: int
    _base: D045PhysicalConfig = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if isinstance(self.room_side_m, bool) or self.room_side_m not in (1.0, 3.0):
            raise ValueError("D-059 room side must be exactly 1.0 or 3.0")
        if (
            isinstance(self.episode_horizon, bool)
            or not isinstance(self.episode_horizon, int)
            or self.episode_horizon <= 0
        ):
            raise ValueError("episode_horizon must be positive")
        accepted = D058PhysicalConfig(room_side_m=self.room_side_m)._base
        object.__setattr__(
            self, "_base", replace(accepted, episode_horizon=self.episode_horizon)
        )

    def __getattr__(self, name: str) -> Any:
        if name in ("world_min", "world_max"):
            raise AttributeError(name)
        return getattr(self._base, name)


def make_d059_s1_env(room_side_m: float, episode_horizon: int) -> D058Env:
    """Create unchanged D-058 with the local episode-horizon-only seam."""
    config = D059PhysicalConfig(room_side_m, episode_horizon)
    return D058Env(cast(D058PhysicalConfig, config))


def _extent(heading: float) -> tuple[float, float]:
    a, c = d058.D058_HULL_HALF_LENGTH_METRES, d058.D058_HULL_HALF_WIDTH_METRES
    return (
        a * abs(math.cos(heading)) + c * abs(math.sin(heading)),
        a * abs(math.sin(heading)) + c * abs(math.cos(heading)),
    )


def _legal_s1(position: tuple[float, float], heading: float, length: float) -> bool:
    hx, hy = _extent(heading)
    return hx <= position[0] <= length - hx and hy <= position[1] <= length - hy


def _reset_options(
    position: tuple[float, float],
    heading: float,
    room_side_m: float,
    battery_fraction: float,
) -> dict[str, object]:
    return {
        "body_position": position,
        "station_center": (room_side_m / 2.0, room_side_m / 2.0),
        "heading": heading,
        "battery_j": battery_fraction * D045_BATTERY_CAPACITY_J,
        "body_temperature_c": D045_AMBIENT_TEMPERATURE_C,
        "charger_termination_latched": False,
    }


def validate_primary_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    checked = validate_exp003_development_seeds(seeds)
    if checked != PRIMARY_SEEDS:
        raise ValueError("D-059 primary seeds must be exactly 26000-26319")
    return checked


def validate_endurance_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    checked = validate_exp003_development_seeds(seeds)
    if checked != ENDURANCE_SEEDS:
        raise ValueError("D-059 endurance seeds must be exactly 26000-26059")
    return checked


def validate_primary_only_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    checked = validate_exp003_development_seeds(seeds)
    if checked != PRIMARY_ONLY_SEEDS:
        raise ValueError("D-059 primary-only seeds must be exactly 26060-26319")
    return checked


def validate_test_run(seed: int, horizon: int, battery_fraction: float) -> None:
    if isinstance(seed, bool) or not isinstance(seed, int) or seed != TEST_SEED:
        raise ValueError(f"D-059 test runs are restricted to seed {TEST_SEED}")
    if isinstance(horizon, bool) or not 0 < horizon <= 5_000:
        raise ValueError("D-059 test horizon must be in 1..5000")
    if not 0.0 <= battery_fraction <= 0.21:
        raise ValueError("D-059 test battery fraction must be in [0, 0.21]")


def _wall_starts(length: float) -> list[D059Start]:
    starts: list[D059Start] = []
    fractions = (0.20, 0.35, 0.50, 0.65, 0.80)
    for heading_index in range(16):
        heading = (2 * heading_index + 1) * math.pi / 16.0
        hx, hy = _extent(heading)
        for clearance in (0.0, 0.05):
            for fraction in fractions:
                along = fraction * length
                for wall, position in (
                    ("bottom", (along, hy + clearance)),
                    ("top", (along, length - hy - clearance)),
                    ("left", (hx + clearance, along)),
                    ("right", (length - hx - clearance, along)),
                ):
                    starts.append(
                        D059Start(
                            f"{wall}-c{clearance:.2f}-f{fraction:.2f}-h{heading_index:02d}",
                            "A1_WALL_CORNER",
                            position,
                            heading,
                            wall,
                            clearance,
                            fraction,
                        )
                    )
        for clearance in (0.0, 0.05):
            corners = (
                ("x_min_y_min", (hx + clearance, hy + clearance)),
                ("x_max_y_min", (length - hx - clearance, hy + clearance)),
                ("x_min_y_max", (hx + clearance, length - hy - clearance)),
                ("x_max_y_max", (length - hx - clearance, length - hy - clearance)),
            )
            for corner, position in corners:
                starts.append(
                    D059Start(
                        f"{corner}-c{clearance:.2f}-h{heading_index:02d}",
                        "A1_WALL_CORNER",
                        position,
                        heading,
                        corner,
                        clearance,
                        None,
                    )
                )
    return starts


def _range_starts(length: float) -> list[D059Start]:
    fractions = (0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85)
    centres = [
        (x, y)
        for x in fractions
        for y in fractions
        if not (x in (0.45, 0.55) and y in (0.45, 0.55))
    ]
    starts: list[D059Start] = []
    for xi, (x, y) in enumerate(centres):
        for k in range(8):
            starts.append(
                D059Start(
                    f"range-x{xi:02d}-h{k}",
                    "A2_ROOM_RANGE",
                    (x * length, y * length),
                    k * math.pi / 4.0,
                    "room_range",
                )
            )
    return starts


def part_a_starts(length: float) -> tuple[D059Start, ...]:
    """Return the fixed matrix without running an environment trajectory."""
    if length not in (1.0, 3.0):
        raise ValueError("Part A room size must be 1.0 or 3.0")
    starts = (*_wall_starts(length), *_range_starts(length))
    if len(starts) != 1248:
        raise RuntimeError(f"Part-A matrix must have 1248 states, got {len(starts)}")
    if any(not _legal_s1(s.position, s.heading, length) for s in starts):
        raise RuntimeError("Part-A S1 start violates exact hull legality")
    if length == 1.0 and any(
        not (0.0 <= s.position[0] <= 1.0 and 0.0 <= s.position[1] <= 1.0)
        for s in starts
    ):
        raise RuntimeError("matched 1 m start is outside D-045 legacy bounds")
    return starts


def _official_matrix_membership(start: D059Start, room_side_m: float) -> bool:
    return any(
        s.position == start.position and s.heading == start.heading
        for s in part_a_starts(room_side_m)
    )


def _float_token(value: float) -> str:
    if not math.isfinite(value):
        raise ValueError("non-finite value in trajectory digest")
    return value.hex()


def _digest_token(value: object) -> object:
    if isinstance(value, float):
        return _float_token(value)
    if isinstance(value, np.ndarray):
        return [_digest_token(cast(object, x)) for x in value.tolist()]
    if isinstance(value, dict):
        return {str(k): _digest_token(v) for k, v in sorted(value.items())}
    if isinstance(value, (tuple, list)):
        return [_digest_token(v) for v in value]
    if isinstance(value, np.generic):
        return _digest_token(value.item())
    return value


def _update_digest(digest: Any, value: object) -> None:
    digest.update(
        json.dumps(
            _digest_token(value), sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    )
    digest.update(b"\n")


def _active_walls(
    env: D045Env | D058Env, room_side_m: float, boundary_scaled: bool
) -> tuple[str, ...]:
    if isinstance(env, D058Env):
        contact = env.last_contact
        if contact is None:
            return ()
        pairs = (
            ("x_min", contact.pushing_x_min),
            ("x_max", contact.pushing_x_max),
            ("y_min", contact.pushing_y_min),
            ("y_max", contact.pushing_y_max),
        )
        return tuple(name for name, active in pairs if active)
    if not boundary_scaled or env.body is None:
        return ()
    x, y = env.body.position
    flags = []
    if x <= 0.0:
        flags.append("x_min")
    if x >= room_side_m:
        flags.append("x_max")
    if y <= 0.0:
        flags.append("y_min")
    if y >= room_side_m:
        flags.append("y_max")
    return tuple(flags)


def _static_walls(env: D045Env | D058Env, room_side_m: float) -> tuple[str, ...]:
    if env.body is None:
        return ()
    x, y = env.body.position
    if isinstance(env, D058Env):
        hx, hy = _extent(env.body.heading)
        edges = (
            ("x_min", x == hx),
            ("x_max", x == room_side_m - hx),
            ("y_min", y == hy),
            ("y_max", y == room_side_m - hy),
        )
    else:
        edges = (
            ("x_min", x == 0.0),
            ("x_max", x == room_side_m),
            ("y_min", y == 0.0),
            ("y_max", y == room_side_m),
        )
    return tuple(name for name, active in edges if active)


def _corner_ids(walls: Sequence[str]) -> tuple[str, ...]:
    values = set(walls)
    corners = (
        ("x_min", "y_min", "x_min_y_min"),
        ("x_max", "y_min", "x_max_y_min"),
        ("x_min", "y_max", "x_min_y_max"),
        ("x_max", "y_max", "x_max_y_max"),
    )
    return tuple(name for x, y, name in corners if x in values and y in values)


@dataclass(slots=True)
class _ReturnEpisode:
    cycle_index: int
    start_transition: int
    first_return: bool
    primary_first: bool
    decisions: int = 0
    wall_any_count: int = 0
    wall_final_100_count: int = 0
    walls: set[str] = field(default_factory=set)
    corners: set[str] = field(default_factory=set)
    static_walls: set[str] = field(default_factory=set)
    final_samples: deque[
        tuple[tuple[float, float], tuple[str, ...], tuple[str, ...]]
    ] = field(init=False)
    classified: bool = False
    primary_censored: bool = False

    def __post_init__(self) -> None:
        self.final_samples = deque(maxlen=100)


def _path_length(points: Sequence[tuple[float, float]]) -> float:
    return sum(math.dist(a, b) for a, b in zip(points, points[1:]))


def _episode_fields(
    episode: _ReturnEpisode,
    outcome: str,
    boundary: str,
    transition: int,
) -> dict[str, object]:
    samples = tuple(episode.final_samples)
    final_walls = sorted({wall for _, walls, _ in samples for wall in walls})
    final_static = sorted({wall for _, _, walls in samples for wall in walls})
    final_corners = sorted(_corner_ids(final_walls))
    tail_positions = tuple(point for point, _, _ in samples)
    final_exposed_count = sum(bool(walls) for _, walls, _ in samples)
    return {
        "cycle_index": episode.cycle_index,
        "start_transition": episode.start_transition,
        "end_transition": transition,
        "return_decisions": episode.decisions,
        "outcome": outcome,
        "classification_boundary": boundary,
        "wall_exposed_any": episode.wall_any_count > 0,
        "wall_exposed_any_transition_count": episode.wall_any_count,
        "wall_exposed_final_100": final_exposed_count > 0,
        "wall_exposed_final_100_transition_count": final_exposed_count,
        "final_100_centre_path_m": _path_length(tail_positions),
        "active_wall_ids": sorted(episode.walls),
        "active_corner_ids": sorted(episode.corners),
        "final_100_dynamic_wall_ids": final_walls,
        "final_100_dynamic_corner_ids": final_corners,
        "final_100_static_wall_ids": final_static,
        "static_wall_ids": sorted(episode.static_walls),
        "anatomy_definition": (
            "dynamic=projection flags (D-058), or boundary_scale<1 (D-045); "
            "static=executed centre on the corresponding legal wall boundary"
        ),
    }


def _failure(outcome: str) -> bool:
    return (
        outcome != "DOCKED"
        and not outcome.startswith("CENSORED_")
        and outcome != "HORIZON_CENSORED"
    )


def _new_env(substrate: str, room_side_m: float, horizon: int) -> D045Env | D058Env:
    if substrate == "D045_1M":
        return D045Env(
            D045PhysicalConfig(
                world_min=(0.0, 0.0),
                world_max=(1.0, 1.0),
                episode_horizon=horizon,
            )
        )
    if substrate in ("S1_1M", "S1_3M"):
        return make_d059_s1_env(room_side_m, horizon)
    raise ValueError(f"unknown D-059 substrate {substrate!r}")


def _legacy_episode_class(
    cycle: dict[str, object],
    cycle_centres: Sequence[tuple[float, float]],
    final_position: tuple[float, float],
    lifetime_truncated: bool,
    final_transition: int,
    spin_exhausted: bool,
) -> str:
    wall_pinned = (
        min(
            final_position[0],
            final_position[1],
            1.0 - final_position[0],
            1.0 - final_position[1],
        )
        <= d054.D054_BOUNDARY_TOLERANCE_M
    )
    path = _path_length(cycle_centres)
    exhausted = spin_exhausted
    docked = cycle.get("first_charging_contact_transition") is not None
    end = cast(int, cycle.get("end_transition", final_transition))
    if docked:
        return "DOCKED"
    if exhausted:
        return "SPIN_EXHAUSTED"
    if wall_pinned and path <= d054.D054_BOUNDARY_TOLERANCE_M:
        return "WEDGED"
    if lifetime_truncated and end == final_transition:
        return "CENSORED_IN_PROGRESS"
    return "OTHER_NOT_DOCKED"


def _derive_prefix_record(
    return_records: Sequence[dict[str, object]],
    no_return_record: dict[str, object],
) -> dict[str, object]:
    """Derive the primary snapshot from compact records frozen on its prefix."""
    primary_rows = [
        row for row in return_records if row.get("measurement_role") == "primary"
    ]
    return dict(primary_rows[0]) if primary_rows else dict(no_return_record)


def _summary_lifetime(
    seed: int | None,
    substrate: str,
    room_side_m: float,
    arm: str,
    horizon: int,
    battery_fraction: float,
    start: D059Start | None,
    primary_horizon: int | None,
    stop_at_primary: bool,
    measure_primary: bool,
    monitor_enabled: bool,
    use_fixture: bool = False,
) -> dict[str, object]:
    """Run one streaming lifetime; no per-transition trace is retained."""
    if not _CLI_OFFICIAL_EXECUTION:
        if seed != TEST_SEED:
            raise RuntimeError(
                "non-CLI trajectory runs are restricted to test seed 26320"
            )
        if horizon > 5_000 or battery_fraction > 0.21:
            raise RuntimeError("non-CLI trajectory exceeds bounded test limits")
        if start is None or _official_matrix_membership(start, room_side_m):
            raise RuntimeError(
                "non-CLI trajectory requires a constructed off-matrix start"
            )
    env = _new_env(substrate, room_side_m, horizon)
    initial_position = (
        (room_side_m / 2.0, room_side_m / 2.0) if start is None else start.position
    )
    initial_heading = 0.0 if start is None else start.heading
    if substrate != "D045_1M" and not _legal_s1(
        initial_position, initial_heading, room_side_m
    ):
        raise ValueError("S1 reset start is not hull-legal")
    observation, reset_info = env.reset(
        options=_reset_options(
            initial_position, initial_heading, room_side_m, battery_fraction
        )
    )
    if reset_info != {}:
        raise RuntimeError("reset info must be exactly empty")
    controller = D052Controller()
    candidate = D055StallTurnCandidate(controller) if arm == "C" else None
    fixture: D053RoamingFixture | None = None
    if start is None or use_fixture:
        if seed is None:
            raise ValueError("seeded fixture run requires an explicit seed")
        fixture = D053RoamingFixture(seed)
    primary_cut = H_PRIMARY if primary_horizon is None else primary_horizon
    digest = hashlib.sha256()
    prefix_digest = hashlib.sha256()
    _update_digest(
        digest,
        {"reset_observation": observation.tobytes().hex(), "reset_info": reset_info},
    )
    _update_digest(
        prefix_digest,
        {"reset_observation": observation.tobytes().hex(), "reset_info": reset_info},
    )

    modes: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    all_events: list[dict[str, object]] = []
    cycles: list[dict[str, object]] = []
    return_records: list[dict[str, object]] = []
    current_cycle: dict[str, object] | None = None
    cycle_tail: deque[tuple[float, float]] = deque(maxlen=101)
    legacy_cycle_tails: dict[int, tuple[tuple[float, float], ...]] = {}
    legacy_cycle_positions: dict[int, tuple[float, float]] = {}
    exhausted_cycles: set[int] = set()
    current_return: _ReturnEpisode | None = None
    return_count = 0
    normal_roam_since_yield = 0
    incidental_acquisitions: list[dict[str, object]] = []
    incidental_contact_steps = 0
    initial_energy_observation = float(observation[0])
    initial_contact = bool(observation[5])
    if start is not None and initial_contact:
        raise RuntimeError("Part-A/test RETURN start has charging contact at reset")
    min_observation = initial_energy_observation
    min_battery_j = env.battery_j
    boundary_scaled_count = 0
    invalid_beacon_count = 0
    exhausted_transitions: list[int] = []
    spin_max = 0
    return_starts: list[dict[str, object]] = []
    stall_detected_by_cycle: Counter[int] = Counter()
    stall_turns_by_cycle: Counter[int] = Counter()
    previous_mode: D052Mode | None = None
    previous_source: str | None = None
    previous_d050_mode: D050ControlMode | None = None
    terminated = False
    truncated = False
    termination_reason: str | None = None
    rewards_zero = True
    infos_empty = True
    primary_record: dict[str, object] | None = None
    primary_mirror: dict[str, object] | None = None
    primary_prefix_record: dict[str, object] | None = None
    transitions = 0

    def freeze_primary(record: dict[str, object]) -> None:
        nonlocal primary_record, primary_mirror
        if primary_record is None:
            primary_record = dict(record)
            # Independent measurement mirror: a pure copy of the frozen causal prefix.
            primary_mirror = dict(record)

    for _ in range(horizon):
        energy_before = float(observation[0])
        contact_before = bool(observation[5])
        proposal: D053Proposal | _ZeroProposal = (
            fixture.propose() if fixture is not None else _ZeroProposal(None)
        )
        emitted = (
            candidate.command(observation, proposal.wheel_command)
            if candidate
            else None
        )
        decision = (
            emitted.decision
            if emitted is not None
            else controller.command(observation, proposal.wheel_command)
        )
        if (
            start is not None
            and transitions == 0
            and (
                "RETURN_ACTIVATED" not in decision.events
                or decision.active_mode is not D052Mode.RETURN
            )
        ):
            raise RuntimeError("Part-A/test start must activate RETURN on decision 1")
        command_source = (
            emitted.command_source.value if emitted else decision.command_source.value
        )
        wheels = (
            emitted.wheels
            if emitted
            else (decision.wheel_delta_left, decision.wheel_delta_right)
        )
        modes[decision.active_mode.value] += 1
        sources[command_source] += 1
        spin_max = max(spin_max, decision.terminal_spin_count)
        if "INVALID_BEACON" in decision.events:
            invalid_beacon_count += 1
        if "TERMINAL_SPIN_EXHAUSTED" in decision.events:
            exhausted_transitions.append(decision.transition_index)
        if (
            current_cycle is None
            and decision.active_mode is D052Mode.NORMAL
            and "RECOVERY_YIELD" not in decision.events
        ):
            normal_roam_since_yield += 1
        if "RETURN_ACTIVATED" in decision.events:
            body = env.body
            if body is None or env.station_center is None:
                raise RuntimeError("body/station missing at RETURN activation")
            dx = env.station_center[0] - body.x
            dy = env.station_center[1] - body.y
            if len(cycles) >= 4096:
                raise RuntimeError("bounded D-059 lifetime episode buffer overflow")
            current_cycle = {
                "cycle_index": len(cycles) + 1,
                "start_transition": decision.transition_index,
                "normal_roam_length": normal_roam_since_yield,
                "return_length": 0,
                "charge_length": 0,
                "energy_at_return_activation": energy_before,
                "energy_after_first_charging_contact": None,
                "energy_at_recovery_yield": None,
                "maximum_terminal_spin_count": 0,
                "outcome": None,
            }
            cycles.append(current_cycle)
            cycle_tail.clear()
            return_starts.append(
                {
                    "transition": decision.transition_index,
                    "station_distance_m": math.hypot(dx, dy),
                    "station_bearing_rad": math.atan2(dy, dx),
                }
            )
            normal_roam_since_yield = 0
            first_return = return_count == 0
            primary_first = (
                first_return
                and measure_primary
                and primary_record is None
                and transitions < primary_cut
            )
            return_count += 1
            current_return = _ReturnEpisode(
                cycle_index=len(cycles),
                start_transition=decision.transition_index,
                first_return=first_return,
                primary_first=primary_first,
            )
        cycle_for_transition = current_cycle
        if current_cycle is not None:
            if decision.active_mode is D052Mode.RETURN:
                current_cycle["return_length"] = (
                    cast(int, current_cycle["return_length"]) + 1
                )
            elif decision.active_mode is D052Mode.CHARGE:
                current_cycle["charge_length"] = (
                    cast(int, current_cycle["charge_length"]) + 1
                )
            elif "RECOVERY_YIELD" not in decision.events:
                current_cycle["normal_roam_length"] = (
                    cast(int, current_cycle["normal_roam_length"]) + 1
                )
            current_cycle["maximum_terminal_spin_count"] = max(
                cast(int, current_cycle["maximum_terminal_spin_count"]),
                decision.terminal_spin_count,
            )
            if "RECOVERY_YIELD" in decision.events:
                current_cycle["energy_at_recovery_yield"] = energy_before
                current_cycle["end_transition"] = decision.transition_index
                current_cycle["outcome"] = "YIELDED"
                current_cycle = None
                normal_roam_since_yield = 0

        body = env.body
        if body is None:
            raise RuntimeError("body missing before step")
        pose_before = (body.x, body.y, body.heading)
        observation_after, reward, terminated, truncated, info = env.step(wheels)
        if reward != 0.0 or info != {}:
            raise RuntimeError("organism reward/info contract changed")
        telemetry = env.last_transition
        if telemetry is None:
            raise RuntimeError("missing transition telemetry")
        transitions += 1
        rewards_zero = rewards_zero and reward == 0.0
        infos_empty = infos_empty and info == {}
        min_observation = min(min_observation, float(observation_after[0]))
        min_battery_j = min(min_battery_j, telemetry.battery_after_j)
        boundary_scaled_count += int(telemetry.boundary_scale < 1.0)
        contact_after = bool(observation_after[5])
        event_labels = list(decision.events)
        if not contact_before and contact_after:
            event_labels.append("PHYSICAL_CONTACT_ACQUIRED")
            if (
                decision.active_mode is D052Mode.RETURN
                and current_cycle is not None
                and current_cycle["energy_after_first_charging_contact"] is None
            ):
                current_cycle["energy_after_first_charging_contact"] = float(
                    observation_after[0]
                )
                current_cycle["first_charging_contact_transition"] = (
                    decision.transition_index
                )
            elif (
                decision.command_source is D052CommandSource.PASS_THROUGH
                and decision.active_mode is D052Mode.NORMAL
            ):
                if len(incidental_acquisitions) >= MAX_EVENT_ROWS:
                    raise RuntimeError("bounded incidental-contact buffer overflow")
                incidental_acquisitions.append(
                    {
                        "transition": decision.transition_index,
                        "energy": float(observation_after[0]),
                    }
                )
        elif contact_before and not contact_after:
            event_labels.append("PHYSICAL_CONTACT_LOST")
        if decision.active_mode is D052Mode.NORMAL and contact_after:
            incidental_contact_steps += 1
        if telemetry.terminated or telemetry.truncated:
            event_labels.append("TERMINATED" if terminated else "TRUNCATED")
            termination_reason = (
                telemetry.termination_reason.value
                if telemetry.termination_reason
                else None
            )
            if current_cycle is not None:
                current_cycle["end_transition"] = decision.transition_index
                current_cycle["outcome"] = (
                    f"TERMINATED_{termination_reason}"
                    if terminated
                    else f"TRUNCATED_IN_{decision.active_mode.value}"
                )

        dynamic_walls = _active_walls(env, room_side_m, telemetry.boundary_scale < 1.0)
        static_walls = _static_walls(env, room_side_m)
        if (
            current_return is not None
            and not current_return.classified
            and decision.active_mode is D052Mode.RETURN
        ):
            current_return.decisions += 1
            current_return.walls.update(dynamic_walls)
            current_return.corners.update(_corner_ids(dynamic_walls))
            current_return.static_walls.update(static_walls)
            current_return.wall_any_count += int(bool(dynamic_walls))
            current_return.final_samples.append(
                (telemetry.position_after, dynamic_walls, static_walls)
            )
            current_return.wall_final_100_count += int(bool(dynamic_walls))
        if cycle_for_transition is not None:
            cycle_tail.append(telemetry.position_after)

        transition_row: dict[str, object] = {
            "transition": decision.transition_index,
            "events": event_labels,
            "active_mode": decision.active_mode.value,
            "command_source": command_source,
            "passed_through": decision.passed_through,
            "preempted": decision.preempted,
            "wheel_command": list(wheels),
            "proposed_wheel_command": list(proposal.wheel_command),
            "symbolic_proposal": getattr(
                getattr(proposal, "symbolic_action", None), "name", None
            ),
            "d050_mode": decision.d050_mode.value if decision.d050_mode else None,
            "terminal_spin_count": decision.terminal_spin_count,
            "terminal_spin_exhausted": decision.terminal_spin_exhausted,
            "energy_before": energy_before,
            "energy_after": float(observation_after[0]),
            "battery_before_j": telemetry.battery_before_j,
            "battery_after_j": telemetry.battery_after_j,
            "charging_contact_before": contact_before,
            "charging_contact_after": contact_after,
            "x": telemetry.position_after[0],
            "y": telemetry.position_after[1],
            "heading": telemetry.heading_after,
            "thermal": float(observation_after[1]),
            "boundary_scale": telemetry.boundary_scale,
            "simulated_seconds": decision.transition_index * D045_DT_SECONDS,
            "cycle_index": len(cycles)
            if current_cycle is None
            else cast(int, current_cycle["cycle_index"]),
            "terminated": terminated,
            "truncated": truncated,
        }
        if isinstance(env, D058Env):
            contact = env.last_contact
            if contact is None:
                raise RuntimeError("D-058 contact telemetry missing")
            contact_token: dict[str, object] = {
                "pushing_x_min": contact.pushing_x_min,
                "pushing_x_max": contact.pushing_x_max,
                "pushing_y_min": contact.pushing_y_min,
                "pushing_y_max": contact.pushing_y_max,
                "unconstrained_endpoint": contact.unconstrained_endpoint,
                "executed_endpoint": contact.executed_endpoint,
                "hx_m": contact.hx_m,
                "hy_m": contact.hy_m,
                "removed_normal_displacement_m": contact.removed_normal_displacement_m,
                "slip_magnitude_m": contact.slip_magnitude_m,
            }
        else:
            contact_token = {"boundary_scale": telemetry.boundary_scale}
        causal_digest_row = {
            "observation_before": observation.tobytes().hex(),
            "proposal": transition_row["proposed_wheel_command"],
            "symbolic": transition_row["symbolic_proposal"],
            "transition_index": decision.transition_index,
            "active_mode": decision.active_mode.value,
            "command_source": command_source,
            "passed_through": decision.passed_through,
            "preempted": decision.preempted,
            "d050_mode": decision.d050_mode.value if decision.d050_mode else None,
            "terminal_spin_count": decision.terminal_spin_count,
            "terminal_spin_exhausted": decision.terminal_spin_exhausted,
            "decision_events": list(decision.events),
            "decision_wheels": list(wheels),
            "reward": reward,
            "terminated": terminated,
            "truncated": truncated,
            "observation_after": observation_after.tobytes().hex(),
            "info": info,
            "pose_before": pose_before,
            "pose_after": telemetry.position_after,
            "heading_after": telemetry.heading_after,
            "battery_after": telemetry.battery_after_j,
            "temperature_after": telemetry.body_temperature_after_c,
            "contact": contact_token,
            "requested_wheel_delta": (
                telemetry.requested_delta_left,
                telemetry.requested_delta_right,
            ),
            "clamped_wheel_delta": (
                telemetry.clamped_delta_left,
                telemetry.clamped_delta_right,
            ),
            "actual_wheel_delta": (
                telemetry.actual_delta_left,
                telemetry.actual_delta_right,
            ),
            "boundary_scale": telemetry.boundary_scale,
            "charge_phase": telemetry.charge_phase.value,
            "actuator_electrical_power_w": telemetry.actuator_electrical_power_w,
            "total_electrical_load_w": telemetry.total_electrical_load_w,
            "actual_stored_power_w": telemetry.actual_stored_power_w,
            "energy_nonviable": telemetry.energy_nonviable,
            "protective_shutdown": telemetry.protective_shutdown,
            "emergency_hard_shutdown": telemetry.emergency_hard_shutdown,
            "termination_reason": (
                telemetry.termination_reason.value
                if telemetry.termination_reason is not None
                else None
            ),
        }
        _update_digest(digest, causal_digest_row)
        if transitions <= primary_cut:
            _update_digest(prefix_digest, causal_digest_row)

        if emitted is not None and emitted.stall_detected:
            stall_detected_by_cycle[cast(int, transition_row["cycle_index"])] += 1
        if emitted is not None and emitted.stall_turned:
            stall_turns_by_cycle[cast(int, transition_row["cycle_index"])] += 1
        if "TERMINAL_SPIN_EXHAUSTED" in decision.events:
            exhausted_cycles.add(cast(int, transition_row["cycle_index"]))
        if cycle_for_transition is not None:
            cycle_index_for_transition = cast(int, cycle_for_transition["cycle_index"])
            if "RECOVERY_YIELD" in decision.events or terminated or truncated:
                legacy_cycle_tails[cycle_index_for_transition] = tuple(cycle_tail)
                legacy_cycle_positions[cycle_index_for_transition] = (
                    telemetry.position_after
                )

        if (
            event_labels
            or decision.active_mode is not previous_mode
            or command_source != previous_source
            or decision.d050_mode is not previous_d050_mode
            or contact_before != contact_after
        ):
            keys = (
                "transition",
                "events",
                "active_mode",
                "command_source",
                "passed_through",
                "preempted",
                "wheel_command",
                "proposed_wheel_command",
                "symbolic_proposal",
                "d050_mode",
                "terminal_spin_count",
                "terminal_spin_exhausted",
                "energy_before",
                "energy_after",
                "charging_contact_before",
                "charging_contact_after",
            )
            if len(all_events) >= MAX_EVENT_ROWS:
                raise RuntimeError("bounded D-059 event buffer overflow")
            all_events.append({key: transition_row[key] for key in keys})
        previous_mode, previous_source, previous_d050_mode = (
            decision.active_mode,
            command_source,
            decision.d050_mode,
        )

        if current_return is not None and not current_return.classified:
            terminal: tuple[str, str] | None = None
            if decision.active_mode is D052Mode.RETURN and contact_after:
                terminal = ("DOCKED", "CHARGING_CONTACT")
            elif "TERMINAL_SPIN_EXHAUSTED" in decision.events:
                terminal = ("SPIN_EXHAUSTED", "TERMINAL_SPIN_EXHAUSTION")
            elif (
                "INVALID_BEACON" in decision.events
                or decision.d050_mode is D050ControlMode.INVALID_BEACON
            ):
                terminal = ("INVALID_BEACON", "INVALID_BEACON")
            elif terminated:
                terminal = (
                    f"TERMINATED_{termination_reason or 'UNKNOWN'}",
                    "ENVIRONMENT_TERMINATION",
                )
            elif current_return.decisions >= W_C:
                terminal = ("RETURN_TIMEOUT_FAILURE", "RETURN_WINDOW_2000")
            if terminal is not None:
                current_return.classified = True
                row = _episode_fields(
                    current_return, terminal[0], terminal[1], transitions
                )
                row["measurement_role"] = (
                    "primary"
                    if current_return.primary_first
                    and not current_return.primary_censored
                    else "secondary"
                )
                return_records.append(row)
                if current_return.primary_first and measure_primary:
                    freeze_primary(row)
            if (
                current_return.primary_first
                and measure_primary
                and primary_record is None
                and transitions >= primary_cut
                and not current_return.classified
            ):
                row = _episode_fields(
                    current_return,
                    "CENSORED_IN_PROGRESS",
                    "PRIMARY_HORIZON",
                    transitions,
                )
                row["measurement_role"] = "primary"
                return_records.append(row)
                current_return.primary_censored = True
                freeze_primary(row)

        if measure_primary and primary_record is None and transitions >= primary_cut:
            if current_return is None:
                primary_record = {
                    "outcome": "CENSORED_NO_RETURN",
                    "classification_boundary": "PRIMARY_HORIZON_NO_RETURN",
                    "wall_exposed_any": False,
                    "wall_exposed_any_transition_count": 0,
                    "wall_exposed_final_100": False,
                    "wall_exposed_final_100_transition_count": 0,
                    "measurement_role": "primary",
                }
                primary_mirror = dict(primary_record)
            elif not current_return.classified:
                row = _episode_fields(
                    current_return,
                    "CENSORED_IN_PROGRESS",
                    "PRIMARY_HORIZON",
                    transitions,
                )
                row["measurement_role"] = "primary"
                return_records.append(row)
                current_return.primary_censored = True
                freeze_primary(row)

        observation = observation_after
        if terminated or truncated:
            break
        if start is not None and stop_at_primary and return_records:
            break
        if stop_at_primary and measure_primary and primary_record is not None:
            break

    final_transition = transitions
    final_position = env.body.position if env.body is not None else initial_position
    if current_return is not None and not current_return.classified:
        already_frozen = any(
            row.get("cycle_index") == current_return.cycle_index
            and row.get("classification_boundary") == "PRIMARY_HORIZON"
            for row in return_records
        )
        after_primary_seam = (
            measure_primary
            and current_return.primary_censored
            and final_transition > primary_cut
        )
        if after_primary_seam or not already_frozen:
            censored_outcome = (
                "CENSORED_IN_PROGRESS"
                if after_primary_seam or start is None
                else "HORIZON_CENSORED"
            )
            boundary = (
                "ENDURANCE_HORIZON" if after_primary_seam else "EXECUTION_HORIZON"
            )
            row = _episode_fields(
                current_return,
                censored_outcome,
                boundary,
                final_transition,
            )
            row["measurement_role"] = (
                "primary"
                if current_return.primary_first
                and measure_primary
                and not current_return.primary_censored
                else "secondary"
            )
            return_records.append(row)
    if current_cycle is not None and current_cycle["outcome"] is None:
        current_cycle["outcome"] = f"TRUNCATED_IN_{controller.mode.value}"
        current_cycle["end_transition"] = final_transition
        cycle_index = cast(int, current_cycle["cycle_index"])
        legacy_cycle_tails[cycle_index] = tuple(cycle_tail)
        legacy_cycle_positions[cycle_index] = final_position
    if measure_primary and primary_record is None:
        outcome = (
            "CENSORED_IN_PROGRESS"
            if current_return is not None
            else "CENSORED_NO_RETURN"
        )
        if current_return is None:
            primary_record = {
                "outcome": outcome,
                "classification_boundary": "EXECUTION_END_NO_RETURN",
                "wall_exposed_any": False,
                "wall_exposed_any_transition_count": 0,
                "wall_exposed_final_100": False,
                "wall_exposed_final_100_transition_count": 0,
                "measurement_role": "primary",
            }
        else:
            primary_record = _episode_fields(
                current_return, outcome, "EXECUTION_END", final_transition
            )
            primary_record["measurement_role"] = "primary"
        primary_mirror = dict(primary_record)
    if measure_primary and primary_record is not None:
        primary_prefix_record = _derive_prefix_record(return_records, primary_record)
        if primary_mirror is None or d053._canonicalize(
            primary_mirror
        ) != d053._canonicalize(primary_record):
            raise RuntimeError("primary online/prefix snapshot identity failed")

    reset_sample: dict[str, object] = {
        "transition": 0,
        "events": ["RESET"],
        "active_mode": D052Mode.NORMAL.value,
        "command_source": None,
        "energy_before": initial_energy_observation,
        "charging_contact_before": initial_contact,
    }
    samples = d053._bounded_samples([reset_sample, *all_events])
    counts = {mode.value: modes[mode.value] for mode in D052Mode}
    source_counts = {
        source.value: sources[source.value] for source in D052CommandSource
    }
    if candidate is not None:
        source_counts["STALL_TURN"] = sources["STALL_TURN"]
    total = sum(modes.values())
    summary: dict[str, object] = {
        "seed": seed,
        "total_transitions": total,
        "termination_reason": termination_reason,
        "terminated": terminated,
        "truncated": truncated,
        "final_mode": controller.mode.value,
        "final_cycle_index": len(cycles),
        "mode_transition_counts": counts,
        "command_source_counts": source_counts,
        "level1_preemption_count": controller.preemption_transition_count,
        "level1_preemption_fraction": controller.preemption_transition_count / total
        if total
        else 0.0,
        "pass_through_count": sources[D052CommandSource.PASS_THROUGH.value],
        "return_activated_count": sum(
            "RETURN_ACTIVATED" in cast(list[str], item["events"]) for item in all_events
        ),
        "return_dock_acquisition_count": sum(
            "CHARGING_CONTACT" in cast(list[str], item["events"]) for item in all_events
        ),
        "completed_recovery_yield_count": sum(
            "RECOVERY_YIELD" in cast(list[str], item["events"]) for item in all_events
        ),
        "contact_lost_count": sum(
            "CHARGING_CONTACT_LOST" in cast(list[str], item["events"])
            for item in all_events
        ),
        "contact_reacquired_count": sum(
            "CHARGING_CONTACT_REACQUIRED" in cast(list[str], item["events"])
            for item in all_events
        ),
        "invalid_beacon_decision_count": invalid_beacon_count,
        "terminal_spin_maximum": spin_max,
        "terminal_spin_exhaustion_count": len(exhausted_transitions),
        "terminal_spin_exhaustion_transitions": exhausted_transitions,
        "incidental_normal_contact_acquisition_count": len(incidental_acquisitions),
        "incidental_normal_contact_acquisitions": incidental_acquisitions,
        "normal_transitions_in_contact": incidental_contact_steps,
        "minimum_observed_energy": min_observation,
        "minimum_battery_j": min_battery_j,
        "boundary_scaled_transition_count": boundary_scaled_count,
        "return_start_pose_evaluator_only": return_starts,
        "cycles": cycles,
        "event_row_count": len(all_events) + 1,
        "retained_sample_count": len(samples),
        "samples_truncated": len(samples) < len(all_events) + 1,
        "event_samples": samples,
        "reward_exactly_zero": rewards_zero,
        "organism_info_exactly_empty": infos_empty,
        "trajectory_digest_sha256": digest.hexdigest(),
        "primary_prefix_digest_sha256": prefix_digest.hexdigest(),
        "fixture_decision_count": fixture.decision_count if fixture is not None else 0,
    }
    if (
        sum(counts.values()) != total
        or controller.preemption_transition_count
        + sources[D052CommandSource.PASS_THROUGH.value]
        != total
    ):
        raise RuntimeError("D-059 lifetime counters are inconsistent")
    if fixture is not None and fixture.decision_count != total:
        raise RuntimeError("D-053 fixture was not queried exactly once per decision")
    if candidate is not None:
        summary["stall_turn_count"] = candidate.stall_turn_count
        summary["stall_detected_count"] = candidate.stall_detected_count
        summary["first_stall_turn_transition"] = candidate.first_stall_turn_transition
        summary["stall_counts_by_cycle"] = [
            {
                "cycle_index": cycle["cycle_index"],
                "stall_turn_count": stall_turns_by_cycle[
                    cast(int, cycle["cycle_index"])
                ],
                "stall_detected_count": stall_detected_by_cycle[
                    cast(int, cycle["cycle_index"])
                ],
            }
            for cycle in cycles
        ]
        source_counts["STALL_TURN"] = candidate.stall_turn_count
    # Reconstruct only D-056's compact episode readouts from bounded tail buffers.
    legacy_episodes: list[dict[str, object]] = []
    for cycle in cycles:
        cycle_index = cast(int, cycle["cycle_index"])
        end_transition = cast(int, cycle.get("end_transition", final_transition))
        end_position = legacy_cycle_positions.get(cycle_index, final_position)
        tail_positions = legacy_cycle_tails.get(cycle_index, ())
        wall_pinned = (
            min(
                end_position[0],
                end_position[1],
                1.0 - end_position[0],
                1.0 - end_position[1],
            )
            <= d054.D054_BOUNDARY_TOLERANCE_M
        )
        legacy_episodes.append(
            {
                "cycle_index": cycle_index,
                "start_transition": cycle["start_transition"],
                "end_transition": end_transition,
                "docked": cycle.get("first_charging_contact_transition") is not None,
                "wall_pinned_at_end": wall_pinned,
                "final_100_centre_path_m": _path_length(tail_positions),
                "class": _legacy_episode_class(
                    cycle,
                    tail_positions,
                    end_position,
                    truncated,
                    final_transition,
                    cycle_index in exhausted_cycles,
                ),
                "termination_reason": (
                    termination_reason if end_transition == final_transition else None
                ),
            }
        )
    # Caller-facing rows contain only frozen RETURN records and bounded summaries.
    return {
        "seed": seed,
        "substrate": substrate,
        "room_side_m": room_side_m,
        "arm": arm,
        "initial_battery_fraction": battery_fraction,
        "horizon": horizon,
        "transitions": transitions,
        "terminated": terminated,
        "truncated": truncated,
        "final_position": final_position,
        "primary_record": primary_record,
        "primary_prefix_record": primary_prefix_record,
        "return_records": return_records,
        "summary": summary,
        "legacy_episodes": legacy_episodes,
        "measurement_enabled": monitor_enabled,
        "reward_exactly_zero": rewards_zero,
        "organism_info_exactly_empty": infos_empty,
    }


def run_test_lifetime(
    seed: int,
    *,
    horizon: int,
    initial_battery_fraction: float,
    substrate: str = "S1_3M",
    room_side_m: float = 3.0,
    arm: str = "U",
    start: D059Start,
    measure_primary: bool = True,
    fixture_stream: bool = False,
) -> dict[str, object]:
    """Bounded test-only trajectory helper; rejects every frozen Part-A state."""
    validate_test_run(seed, horizon, initial_battery_fraction)
    if arm not in ARMS or substrate not in ROOMS:
        raise ValueError("invalid test arm or substrate")
    if _official_matrix_membership(start, room_side_m):
        raise ValueError("test trajectory must use a constructed off-matrix start")
    result = _summary_lifetime(
        seed,
        substrate,
        room_side_m,
        arm,
        horizon,
        initial_battery_fraction,
        start,
        min(horizon, H_PRIMARY),
        False,
        measure_primary,
        measure_primary,
        fixture_stream,
    )
    return result


def clopper_pearson_one_sided(
    failures: int, n: int, alpha: float = ALPHA
) -> tuple[float | None, float | None]:
    """Return exact one-sided lower/upper Clopper-Pearson bounds."""
    if (
        isinstance(failures, bool)
        or isinstance(n, bool)
        or not isinstance(failures, int)
        or not isinstance(n, int)
        or not 0 <= failures <= n
    ):
        raise ValueError("require integer counts 0 <= failures <= n")
    if alpha <= 0.0 or alpha >= 1.0:
        raise ValueError("alpha must be in (0,1)")
    if n == 0:
        return None, None

    def cdf(k: int, p: float) -> float:
        if k < 0:
            return 0.0
        if k >= n:
            return 1.0
        total = 0.0
        for i in range(k + 1):
            if p == 0.0:
                term = 1.0 if i == 0 else 0.0
            elif p == 1.0:
                term = 1.0 if i == n else 0.0
            else:
                term = math.exp(
                    math.lgamma(n + 1)
                    - math.lgamma(i + 1)
                    - math.lgamma(n - i + 1)
                    + i * math.log(p)
                    + (n - i) * math.log1p(-p)
                )
            total += term
        return min(1.0, max(0.0, total))

    def sf_from(k: int, p: float) -> float:
        total = 0.0
        for i in range(k, n + 1):
            if p == 0.0:
                term = 1.0 if i == 0 else 0.0
            elif p == 1.0:
                term = 1.0 if i == n else 0.0
            else:
                term = math.exp(
                    math.lgamma(n + 1)
                    - math.lgamma(i + 1)
                    - math.lgamma(n - i + 1)
                    + i * math.log(p)
                    + (n - i) * math.log1p(-p)
                )
            total += term
        return min(1.0, max(0.0, total))

    if failures == 0:
        lower = 0.0
    else:
        lo, hi = 0.0, 1.0
        for _ in range(80):
            mid = (lo + hi) / 2.0
            if sf_from(failures, mid) < alpha:
                lo = mid
            else:
                hi = mid
        lower = (lo + hi) / 2.0
    if failures == n:
        upper = 1.0
    else:
        lo, hi = 0.0, 1.0
        for _ in range(80):
            mid = (lo + hi) / 2.0
            if cdf(failures, mid) > alpha:
                lo = mid
            else:
                hi = mid
        upper = (lo + hi) / 2.0
    return lower, upper


def exact_mcnemar_two_sided(b: int, c: int) -> float:
    """Exact two-sided conditional McNemar p-value using discordant pairs."""
    if min(b, c) < 0:
        raise ValueError("discordant counts must be non-negative")
    discordant = b + c
    if discordant == 0:
        return 1.0
    k = min(b, c)
    tail: float = sum(math.comb(discordant, i) / (2**discordant) for i in range(k + 1))
    return float(min(1.0, 2.0 * tail))


def primary_counts(records: Sequence[dict[str, object]]) -> dict[str, int]:
    n = f = g = 0
    for record in records:
        outcome = str(record["outcome"])
        if outcome.startswith("CENSORED_") or outcome == "HORIZON_CENSORED":
            continue
        n += 1
        if _failure(outcome):
            if bool(record["wall_exposed_any"]):
                f += 1
            else:
                g += 1
    return {"N3": n, "F3": f, "G3": g}


def decide_branches(
    counts: dict[str, int],
    part_a_canonical: Sequence[dict[str, object]],
    secondary_canonical: Sequence[dict[str, object]],
    controls_clean: bool,
    canonical_protocol_defect: bool = False,
) -> dict[str, object]:
    n, f, g = counts["N3"], counts["F3"], counts["G3"]
    lower, upper = clopper_pearson_one_sided(f, n)
    if not controls_clean:
        return {
            "P_BRANCH": "STOP",
            "FLOOR_S1_3M": "NOT_SETTLED",
            "reason": "control failure",
            "N3": n,
            "F3": f,
            "G3": g,
            "cp_lower": lower,
            "cp_upper": upper,
        }
    if lower is not None and lower >= P_STAR:
        p_branch = "P_JUSTIFIED"
    elif upper is None or upper >= P_STAR:
        p_branch = "P_UNRESOLVED"
    else:
        targeted_wall_failure = any(
            _failure(str(row.get("outcome", "CENSORED")))
            and bool(row.get("wall_exposed_any"))
            for row in part_a_canonical
        ) or any(
            _failure(str(row.get("outcome", "CENSORED")))
            and bool(row.get("wall_exposed_any"))
            for row in secondary_canonical
        )
        p_branch = "P_UNRESOLVED" if targeted_wall_failure else "P_NOT_JUSTIFIED"
    part_a_all_docked = all(row.get("outcome") == "DOCKED" for row in part_a_canonical)
    secondary_failure = any(
        _failure(str(row.get("outcome", "CENSORED"))) for row in secondary_canonical
    )
    floor_reasons: list[str] = []
    if p_branch != "P_NOT_JUSTIFIED":
        floor_reasons.append("P branch is not P_NOT_JUSTIFIED")
    if g != 0:
        floor_reasons.append("primary non-contact failures G3 > 0")
    if not part_a_all_docked:
        floor_reasons.append("not every canonical Part-A U state docked")
    if secondary_failure:
        floor_reasons.append("canonical S1_3M secondary failure exists")
    if canonical_protocol_defect:
        floor_reasons.append(
            "canonical invalid-beacon/termination/protocol defect exists"
        )
    floor = "SETTLED" if not floor_reasons else "NOT_SETTLED"
    return {
        "P_BRANCH": p_branch,
        "FLOOR_S1_3M": floor,
        "floor_reasons": floor_reasons,
        "N3": n,
        "F3": f,
        "G3": g,
        "cp_lower": lower,
        "cp_upper": upper,
        "p_star": P_STAR,
    }


def _canonical_json_bytes(payload: object) -> bytes:
    return (
        json.dumps(
            d053._canonicalize(payload),
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def write_artifact(path: Path, payload: dict[str, object]) -> Path:
    """Write canonical JSON and an integrity digest excluding its own field."""
    canonical = cast(dict[str, object], d053._canonicalize(payload))
    base = dict(canonical)
    base.pop("artifact_integrity", None)
    body = _canonical_json_bytes(base)
    canonical["artifact_integrity"] = {
        "sha256_canonical_payload_excluding_integrity_field": hashlib.sha256(
            body
        ).hexdigest(),
        "canonical_payload_bytes_excluding_integrity_field": len(body),
        "definition": (
            "canonical UTF-8 JSON plus newline before artifact_integrity is added"
        ),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_json_bytes(canonical))
    return path


def protocol_manifest() -> dict[str, object]:
    """Result-free JSON committed with the implementation candidate."""
    return {
        "schema_version": "d059-protocol-manifest-v1",
        "development_id": D059_ID,
        "protocol_version": PROTOCOL_VERSION,
        "execution_status": "NOT_EXECUTED_RESULT_FREE_IMPLEMENTATION_CANDIDATE",
        "authorized_base_sha": BASE_SHA,
        "frozen_brief_sha256": FROZEN_BRIEF_SHA256,
        "latest_authorizing_ruling_comment": "5941551976",
        "selected_freeze_sha": None,
        "seed_contract": {
            "primary": list(PRIMARY_SEEDS),
            "endurance_subset": list(ENDURANCE_SEEDS),
            "primary_only": list(PRIMARY_ONLY_SEEDS),
            "test_only": TEST_SEED,
            "retired_exposed_allocations": [
                "23000-23319",
                "23320",
                "24000-24319",
                "24320",
            ],
            "d045_harness_identity_support": list(D045_SUPPORT_SEEDS),
        },
        "horizons": {
            "primary": H_PRIMARY,
            "return_classification_window": W_C,
            "endurance": H_ENDURANCE,
            "part_a": H_PART_A,
        },
        "invalidated_and_exposed_provenance": list(_INVALIDATED_PROVENANCE),
        "model_availability_note": (
            "GPT-6 Luna rate limits are operational availability observations; "
            "no model substitution is made."
        ),
        "part_a_matrix": {
            "state_count_per_room": 1248,
            "trajectory_execution": "NOT_RUN",
            "canonical_support": "1.0 m and 3.0 m; explicit reset options only",
        },
        "runtime_plan_seconds": {
            "expected_approximate": 7200,
            "conservative_capped_approximate": 11160,
            "actual": None,
        },
        "artifact": {
            "official_result_artifact_generated": False,
            "raw_transition_traces_retained": False,
            "float_canonicalization": (
                "exact-binary Decimal quantize 1e-12 ROUND_HALF_EVEN; normalize -0; "
                "reject non-finite"
            ),
        },
        "official_execution_gate": {
            "cli_only": True,
            "requires_clean_checkout_at_executed_commit_sha": True,
            "fresh_archive_requires_archive_source_sha_attestation": True,
            "requires_protected_source_hashes_equal_base": True,
            "requires_pyhashseed_0": True,
            "requires_external_seed_collision_exposure_recheck_before_freeze": True,
            "official_execution_performed": False,
        },
    }


def _git_output(args: Sequence[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout.strip()


def verify_protected_sources() -> dict[str, str]:
    """Require protected mechanisms/dependencies to match authorized-base hashes."""
    repo = Path(__file__).resolve().parents[2]
    if set(PROTECTED_SHA256) != set(PROTECTED):
        raise RuntimeError("protected source hash table does not cover the frozen list")
    hashes: dict[str, str] = {}
    mismatches: list[str] = []
    for relative in PROTECTED:
        current_digest = hashlib.sha256((repo / relative).read_bytes()).hexdigest()
        hashes[relative] = current_digest
        if current_digest != PROTECTED_SHA256[relative]:
            mismatches.append(relative)
    if mismatches:
        raise RuntimeError(f"protected source differs from base: {mismatches}")
    return hashes


def verify_clean_frozen_checkout(
    executed_commit_sha: str, archive_source_sha: str | None = None
) -> dict[str, object]:
    """Verify a clean freeze checkout or an externally attested git archive."""
    archive_mode = False
    try:
        head = _git_output(("rev-parse", "HEAD"))
    except OSError, subprocess.CalledProcessError:
        if archive_source_sha != executed_commit_sha:
            raise RuntimeError("archive_source_sha must equal the frozen commit SHA")
        head = executed_commit_sha
        archive_mode = True
    if archive_mode:
        if (
            archive_source_sha is None
            or len(archive_source_sha) != 40
            or any(c not in "0123456789abcdef" for c in archive_source_sha)
        ):
            raise RuntimeError("invalid fresh archive source SHA")
    else:
        if archive_source_sha is not None and archive_source_sha != executed_commit_sha:
            raise RuntimeError("archive_source_sha must equal executed_commit_sha")
        if head != executed_commit_sha:
            raise RuntimeError("executed_commit_sha must equal current HEAD")
        status = _git_output(("status", "--porcelain=v1"))
        if status:
            raise RuntimeError("official execution requires a clean checkout")
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", BASE_SHA, "HEAD"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        changed_paths = set(
            _git_output(("diff", "--name-only", BASE_SHA, "HEAD")).splitlines()
        )
        allowed_paths = {
            "src/aweform/d059.py",
            "tests/test_d059.py",
            "development/D-059-v05-s1-level1-floor-rebaseline.md",
            "development/D-059-v05-s1-level1-floor-rebaseline.json",
            "development/INDEX.md",
        }
        if changed_paths != allowed_paths:
            raise RuntimeError("official execution requires the exact five-path diff")
        if _git_output(("rev-parse", "HEAD^{tree}")) == "":
            raise RuntimeError("could not determine frozen source tree")
    if os.environ.get("PYTHONHASHSEED") != "0":
        raise RuntimeError("official execution requires PYTHONHASHSEED=0")
    protected_hashes = verify_protected_sources()
    return {
        "head": head,
        "clean_checkout": True,
        "protected_source_hashes_match_base": True,
        "protected_file_sha256": protected_hashes,
        "pyhashseed": "0",
    }


def verify_horizon_seams() -> dict[str, object]:
    """Mechanically prove only episode_horizon differs from accepted D-058."""
    fields = D045PhysicalConfig.__dataclass_fields__
    records: dict[str, object] = {}
    for name, length in (("S1_1M", 1.0), ("S1_3M", 3.0)):
        accepted = D058PhysicalConfig(room_side_m=length)._base
        horizon_checks: list[dict[str, object]] = []
        for horizon in (H_PRIMARY, H_ENDURANCE, H_PART_A):
            local = D059PhysicalConfig(length, horizon)._base
            differences = {
                field_name: (getattr(accepted, field_name), getattr(local, field_name))
                for field_name in fields
                if getattr(accepted, field_name) != getattr(local, field_name)
            }
            if set(differences) != {"episode_horizon"}:
                raise RuntimeError(
                    f"D-059 horizon seam changed physical fields: {differences}"
                )
            if local.episode_horizon != horizon:
                raise RuntimeError("D-059 local horizon was not applied")
            horizon_checks.append(
                {
                    "accepted_horizon": accepted.episode_horizon,
                    "d059_horizon": horizon,
                    "only_differing_field": "episode_horizon",
                }
            )
        records[name] = horizon_checks
    return records


def _episode_class_rows(run: dict[str, object]) -> list[dict[str, object]]:
    legacy = cast(list[dict[str, object]], run["legacy_episodes"])
    fields = (
        "cycle_index",
        "class",
        "docked",
        "start_transition",
        "end_transition",
        "wall_pinned_at_end",
        "final_100_centre_path_m",
        "termination_reason",
    )
    return [{key: row.get(key) for key in fields} for row in legacy]


def _d056_identity_fields(summary: dict[str, object]) -> dict[str, object]:
    """Remove only D-059-added digest/gate fields before exact D-056 comparison."""
    extra = {
        "trajectory_digest_sha256",
        "primary_prefix_digest_sha256",
        "fixture_decision_count",
    }
    return {key: value for key, value in summary.items() if key not in extra}


def _prior_d056() -> dict[str, object]:
    path = (
        Path(__file__).resolve().parents[2]
        / "development/D-056-v05-multi-cycle-stall-turn-lifetimes.json"
    )
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def _run_support_identity() -> dict[str, object]:
    """Full D-045 identity guard for the five committed D-056 support seeds."""
    prior = _prior_d056()
    prior_lifetimes = cast(list[dict[str, object]], prior["lifetimes"])
    prior_episodes = cast(list[dict[str, object]], prior["episodes"])
    expected = {
        (row["seed"], str(row["arm"])): cast(dict[str, object], row["summary"])
        for row in prior_lifetimes
        if row["seed"] in D045_SUPPORT_SEEDS
    }
    expected_episode_classes = {
        (row["seed"], str(row["arm"])): [
            {
                "cycle_index": episode["cycle_index"],
                "class": episode["class"],
                "docked": episode["docked"],
                "start_transition": episode["start_transition"],
                "end_transition": episode.get("end_transition"),
                "wall_pinned_at_end": episode["wall_pinned_at_end"],
                "final_100_centre_path_m": episode["final_100_centre_path_m"],
                "termination_reason": episode.get("termination_reason"),
            }
            for episode in prior_episodes
            if episode["seed"] == row["seed"] and episode["arm"] == row["arm"]
        ]
        for row in prior_lifetimes
        if row["seed"] in D045_SUPPORT_SEEDS
    }
    checked = 0
    for seed in D045_SUPPORT_SEEDS:
        u = _summary_lifetime(
            seed,
            "D045_1M",
            1.0,
            "U",
            H_ENDURANCE,
            0.80,
            None,
            None,
            False,
            False,
            False,
        )
        c = _summary_lifetime(
            seed,
            "D045_1M",
            1.0,
            "C",
            H_ENDURANCE,
            0.80,
            None,
            None,
            False,
            False,
            False,
        )
        for arm, run in (("U", u), ("C", c)):
            got = _d056_identity_fields(cast(dict[str, object], run["summary"]))
            want = expected[(seed, arm)]
            if d053._canonicalize(got) != d053._canonicalize(want):
                raise RuntimeError(
                    f"D-056 summary identity failed seed={seed} arm={arm}"
                )
            if d053._canonicalize(_episode_class_rows(run)) != d053._canonicalize(
                expected_episode_classes[(seed, arm)]
            ):
                raise RuntimeError(
                    f"D-056 episode class identity failed seed={seed} arm={arm}"
                )
        assert_candidate_identity(u, c)
        checked += 1
    return {
        "support_seeds": list(D045_SUPPORT_SEEDS),
        "paired_lifetimes_checked": checked,
        "result": "PASS",
    }


def assert_candidate_identity(u: dict[str, object], c: dict[str, object]) -> None:
    us = cast(dict[str, object], u["summary"])
    cs = cast(dict[str, object], c["summary"])
    u_digest = us["trajectory_digest_sha256"]
    c_digest = cs["trajectory_digest_sha256"]
    if cs.get("stall_detected_count", 0) == 0:
        if u_digest != c_digest:
            raise RuntimeError("zero-stall U/C per-decision digest identity failed")
        stall_fields = {
            "stall_turn_count",
            "stall_detected_count",
            "first_stall_turn_transition",
            "stall_counts_by_cycle",
        }
        reduced_candidate = {
            key: value for key, value in cs.items() if key not in stall_fields
        }
        candidate_sources = cast(
            dict[str, object], reduced_candidate["command_source_counts"]
        )
        reduced_candidate["command_source_counts"] = {
            key: value
            for key, value in candidate_sources.items()
            if key != "STALL_TURN"
        }
        if d053._canonicalize(us) != d053._canonicalize(reduced_candidate):
            raise RuntimeError("zero-stall U/C summary identity failed")


def _first_return(run: dict[str, object]) -> dict[str, object]:
    primary = run.get("primary_record")
    if isinstance(primary, dict):
        return primary
    rows = cast(list[dict[str, object]], run["return_records"])
    if rows:
        return rows[0]
    return {
        "outcome": "CENSORED_NO_RETURN",
        "wall_exposed_any": False,
        "wall_exposed_any_transition_count": 0,
        "wall_exposed_final_100": False,
        "wall_exposed_final_100_transition_count": 0,
    }


def _common_outcome(outcome: str) -> str:
    if outcome == "DOCKED":
        return "DOCKED"
    if outcome.startswith("CENSORED_") or outcome == "HORIZON_CENSORED":
        return "CENSORED"
    return "FAILED"


def _cross_tab(pairs: Sequence[tuple[str, str]]) -> dict[str, int]:
    counts: Counter[str] = Counter(f"{left} x {right}" for left, right in pairs)
    return dict(sorted(counts.items()))


def _matched_contrast(
    pairs: Sequence[dict[str, object]], left_field: str, right_field: str
) -> dict[str, object]:
    outcomes = [(str(pair[left_field]), str(pair[right_field])) for pair in pairs]
    left_only = sum(a == "FAIL" and b != "FAIL" for a, b in outcomes)
    right_only = sum(a != "FAIL" and b == "FAIL" for a, b in outcomes)
    binary_outcomes = [
        (
            "FAIL" if left == "FAIL" else "NOT_FAIL",
            "FAIL" if right == "FAIL" else "NOT_FAIL",
        )
        for left, right in outcomes
    ]
    return {
        "by_seed": [
            {"seed": pair["seed"], "left": pair[left_field], "right": pair[right_field]}
            for pair in pairs
        ],
        "common_outcome_crosstab": _cross_tab(outcomes),
        "failed_not_failed_crosstab": _cross_tab(binary_outcomes),
        "exact_two_sided_mcnemar": {
            "left_only_failure": left_only,
            "right_only_failure": right_only,
            "p_value": exact_mcnemar_two_sided(left_only, right_only),
        },
    }


def _aggregate_part_a(rows: Sequence[dict[str, object]]) -> dict[str, object]:
    by: dict[str, Any] = {}
    for substrate in ROOMS:
        by[substrate] = {}
        for arm in ARMS:
            by[substrate][arm] = {}
            for support_set in PART_A_SETS:
                selected = [
                    row
                    for row in rows
                    if row["substrate"] == substrate
                    and row["arm"] == arm
                    and row["support_set"] == support_set
                ]
                by[substrate][arm][support_set] = {
                    "outcome_counts": dict(
                        sorted(Counter(str(row["outcome"]) for row in selected).items())
                    ),
                    "wall_exposed_failure_count": sum(
                        _failure(str(row["outcome"])) and bool(row["wall_exposed_any"])
                        for row in selected
                    ),
                    "non_contact_failure_count": sum(
                        _failure(str(row["outcome"]))
                        and not bool(row["wall_exposed_any"])
                        for row in selected
                    ),
                    "state_count": len(selected),
                }
    matched = {}
    for support_set in PART_A_SETS:
        for arm in ARMS:
            one = {
                str(row["case_id"]): row
                for row in rows
                if row["substrate"] == "S1_1M"
                and row["arm"] == arm
                and row["support_set"] == support_set
            }
            d045 = {
                str(row["case_id"]): row
                for row in rows
                if row["substrate"] == "D045_1M"
                and row["arm"] == arm
                and row["support_set"] == support_set
            }
            three = {
                str(row["case_id"]): row
                for row in rows
                if row["substrate"] == "S1_3M"
                and row["arm"] == arm
                and row["support_set"] == support_set
            }
            if set(one) != set(d045) or set(one) != set(three):
                raise RuntimeError("Part-A matched substrate state sets differ")
            keys = sorted(one)
            d045_pairs = [
                (
                    _common_outcome(str(one[key]["outcome"])),
                    _common_outcome(str(d045[key]["outcome"])),
                )
                for key in keys
            ]
            room_pairs = [
                (
                    _common_outcome(str(three[key]["outcome"])),
                    _common_outcome(str(one[key]["outcome"])),
                )
                for key in keys
            ]
            matched[f"{support_set}:{arm}:S1_1M_vs_D045_1M"] = {
                "by_case_id": [
                    {
                        "case_id": key,
                        "left": one[key]["outcome"],
                        "right": d045[key]["outcome"],
                    }
                    for key in keys
                ],
                "common_outcome_crosstab": _cross_tab(d045_pairs),
            }
            matched[f"{support_set}:{arm}:S1_3M_vs_S1_1M"] = {
                "by_case_id": [
                    {
                        "case_id": key,
                        "left": three[key]["outcome"],
                        "right": one[key]["outcome"],
                    }
                    for key in keys
                ],
                "common_outcome_crosstab": _cross_tab(room_pairs),
            }
    return {"by_substrate_arm_set": by, "matched_part_a_contrasts": matched}


def _compact_endurance_readout(run: dict[str, object]) -> dict[str, object]:
    """Retain bounded per-lifetime fields without event or transition traces."""
    summary = cast(dict[str, object], run["summary"])
    fields = (
        "total_transitions",
        "termination_reason",
        "terminated",
        "truncated",
        "final_mode",
        "final_cycle_index",
        "mode_transition_counts",
        "command_source_counts",
        "level1_preemption_count",
        "level1_preemption_fraction",
        "return_activated_count",
        "return_dock_acquisition_count",
        "completed_recovery_yield_count",
        "invalid_beacon_decision_count",
        "terminal_spin_maximum",
        "terminal_spin_exhaustion_count",
        "minimum_observed_energy",
        "minimum_battery_j",
        "boundary_scaled_transition_count",
        "reward_exactly_zero",
        "organism_info_exactly_empty",
        "trajectory_digest_sha256",
        "primary_prefix_digest_sha256",
        "fixture_decision_count",
    )
    row: dict[str, object] = {
        "seed": run["seed"],
        "substrate": run["substrate"],
        "arm": run["arm"],
        "return_record_count": len(
            cast(list[dict[str, object]], run["return_records"])
        ),
        **{key: summary[key] for key in fields},
    }
    for key in (
        "stall_turn_count",
        "stall_detected_count",
        "first_stall_turn_transition",
        "stall_counts_by_cycle",
    ):
        if key in summary:
            row[key] = summary[key]
    return row


def _official_protocol(
    executed_commit_sha: str,
    jobs: int,
    reservation_recheck_sha256: str,
    archive_source_sha: str | None = None,
) -> dict[str, object]:
    if not _CLI_OFFICIAL_EXECUTION:
        raise RuntimeError("official D-059 execution is CLI-only")
    if len(executed_commit_sha) != 40 or any(
        c not in "0123456789abcdef" for c in executed_commit_sha
    ):
        raise ValueError("executed_commit_sha must be a lowercase 40-character SHA")
    if len(reservation_recheck_sha256) != 64 or any(
        c not in "0123456789abcdef" for c in reservation_recheck_sha256
    ):
        raise ValueError("reservation recheck must be a lowercase SHA-256")
    seed_validation = {
        "primary": list(validate_primary_seeds(PRIMARY_SEEDS)),
        "endurance": list(validate_endurance_seeds(ENDURANCE_SEEDS)),
        "primary_only": list(validate_primary_only_seeds(PRIMARY_ONLY_SEEDS)),
        "test_only": TEST_SEED,
        "d045_support": list(validate_exp003_development_seeds(D045_SUPPORT_SEEDS)),
    }
    freeze_control = verify_clean_frozen_checkout(
        executed_commit_sha, archive_source_sha
    )
    horizon_control = verify_horizon_seams()
    identity_control = _run_support_identity()

    primary_rows: list[dict[str, object]] = []
    primary_prefix_controls: list[dict[str, object]] = []
    endurance_secondary: list[dict[str, object]] = []
    endurance_lifetime_summaries: list[dict[str, object]] = []
    endurance_episode_records: list[dict[str, object]] = []
    s1_identity_rows: list[dict[str, object]] = []
    s1_endurance: dict[tuple[int, str, str], dict[str, object]] = {}
    matched_1m: dict[tuple[int, str, str], dict[str, object]] = {}
    for seed in PRIMARY_SEEDS:
        endurance = seed in ENDURANCE_SEEDS
        run_horizon = H_ENDURANCE if endurance else H_PRIMARY
        u_run_for_seed: dict[str, object] | None = None
        for arm in ARMS:
            run = _summary_lifetime(
                seed,
                "S1_3M",
                3.0,
                arm,
                run_horizon,
                0.80,
                None,
                H_PRIMARY,
                not endurance,
                True,
                True,
            )
            if endurance:
                endurance_lifetime_summaries.append(_compact_endurance_readout(run))
                endurance_episode_records.extend(
                    {"seed": seed, "substrate": "S1_3M", "arm": arm, **episode}
                    for episode in cast(list[dict[str, object]], run["return_records"])
                )
            if arm == "C":
                if u_run_for_seed is None:
                    raise RuntimeError("canonical U run missing before C comparator")
                u_run = u_run_for_seed
                assert_candidate_identity(u_run, run)
                u_summary = cast(dict[str, object], u_run["summary"])
                c_summary = cast(dict[str, object], run["summary"])
                s1_identity_rows.append(
                    {
                        "scope": "S1_3M_PRIMARY_OR_ENDURANCE",
                        "seed": seed,
                        "u_digest": u_summary["trajectory_digest_sha256"],
                        "c_digest": c_summary["trajectory_digest_sha256"],
                        "u_primary_record": u_run["primary_record"],
                        "c_primary_record": run["primary_record"],
                        "c_stall_detections": c_summary.get("stall_detected_count", 0),
                    }
                )
                if (
                    cast(dict[str, object], run["summary"]).get(
                        "stall_detected_count", 0
                    )
                    != 0
                ):
                    raise RuntimeError("S1 C stall predicate was not dormant")
            else:
                u_run_for_seed = run
                if endurance:
                    s1_endurance[(seed, "S1_3M", arm)] = run
                primary = cast(dict[str, object], run["primary_record"])
                prefix = cast(dict[str, object], run["primary_prefix_record"])
                if d053._canonicalize(primary) != d053._canonicalize(prefix):
                    raise RuntimeError("online primary and causal-prefix record differ")
                summary = cast(dict[str, object], run["summary"])
                primary_rows.append(
                    {
                        "seed": seed,
                        "role": "endurance" if endurance else "primary_only",
                        "lifetime_terminated": summary["terminated"],
                        "lifetime_termination_reason": summary["termination_reason"],
                        "primary_prefix_digest_sha256": summary[
                            "primary_prefix_digest_sha256"
                        ],
                        **primary,
                    }
                )
                if endurance:
                    primary_prefix_controls.append(
                        {
                            "seed": seed,
                            "online_prefix_record": primary,
                            "derived_prefix_record": prefix,
                            "prefix_digest_sha256": summary[
                                "primary_prefix_digest_sha256"
                            ],
                            "result": "PASS",
                        }
                    )
                if endurance:
                    for episode in cast(list[dict[str, object]], run["return_records"]):
                        # Do not repeat a classifiable primary RETURN as secondary.
                        if episode.get("measurement_role") == "secondary":
                            endurance_secondary.append({"seed": seed, **episode})
        if endurance:
            for substrate in ("S1_1M", "D045_1M"):
                for arm in ARMS:
                    run = _summary_lifetime(
                        seed,
                        substrate,
                        1.0,
                        arm,
                        H_ENDURANCE,
                        0.80,
                        None,
                        None,
                        False,
                        False,
                        False,
                    )
                    matched_1m[(seed, substrate, arm)] = run
                    endurance_lifetime_summaries.append(_compact_endurance_readout(run))
                    endurance_episode_records.extend(
                        {
                            "seed": seed,
                            "substrate": substrate,
                            "arm": arm,
                            **episode,
                        }
                        for episode in cast(
                            list[dict[str, object]], run["return_records"]
                        )
                    )
                    if substrate == "S1_1M" and arm == "C":
                        u_run = matched_1m[(seed, substrate, "U")]
                        assert_candidate_identity(u_run, run)
                        u_summary = cast(dict[str, object], u_run["summary"])
                        c_summary = cast(dict[str, object], run["summary"])
                        s1_identity_rows.append(
                            {
                                "scope": "S1_1M_ENDURANCE",
                                "seed": seed,
                                "u_digest": u_summary["trajectory_digest_sha256"],
                                "c_digest": c_summary["trajectory_digest_sha256"],
                                "c_stall_detections": c_summary.get(
                                    "stall_detected_count", 0
                                ),
                            }
                        )
                        if (
                            cast(dict[str, object], run["summary"]).get(
                                "stall_detected_count", 0
                            )
                            != 0
                        ):
                            raise RuntimeError(
                                "S1_1M C stall predicate was not dormant"
                            )
    if len(primary_rows) != 320:
        raise RuntimeError("primary allocation did not produce exactly 320 records")

    part_a_rows: list[dict[str, object]] = []
    for substrate, length in ROOMS.items():
        for start in part_a_starts(length):
            for arm in ARMS:
                run = _summary_lifetime(
                    None,
                    substrate,
                    length,
                    arm,
                    H_PART_A,
                    0.20,
                    start,
                    None,
                    True,
                    False,
                    False,
                )
                primary_like = cast(list[dict[str, object]], run["return_records"])
                if not primary_like:
                    outcome = "HORIZON_CENSORED"
                    record: dict[str, object] = {
                        "outcome": outcome,
                        "wall_exposed_any": False,
                        "wall_exposed_any_transition_count": 0,
                        "wall_exposed_final_100": False,
                        "wall_exposed_final_100_transition_count": 0,
                    }
                else:
                    record = primary_like[0]
                    outcome = str(record["outcome"])
                    if (
                        outcome.startswith("CENSORED_")
                        and cast(int, record["return_decisions"]) >= W_C
                    ):
                        outcome = "RETURN_TIMEOUT_FAILURE"
                    elif outcome.startswith("CENSORED_"):
                        outcome = "HORIZON_CENSORED"
                row = {
                    "case_id": start.case_id,
                    "support_set": start.support_set,
                    "substrate": substrate,
                    "arm": arm,
                    "position": list(start.position),
                    "heading": start.heading,
                    "boundary_class": start.boundary_class,
                    "clearance_m": start.clearance_m,
                    "along_wall_fraction": start.along_wall_fraction,
                    "lifetime_terminated": cast(dict[str, object], run["summary"])[
                        "terminated"
                    ],
                    "lifetime_termination_reason": cast(
                        dict[str, object], run["summary"]
                    )["termination_reason"],
                    **record,
                    "outcome": outcome,
                    "trajectory_digest_sha256": cast(dict[str, object], run["summary"])[
                        "trajectory_digest_sha256"
                    ],
                }
                part_a_rows.append(row)
                if substrate.startswith("S1_") and arm == "C":
                    u_row = next(
                        item
                        for item in part_a_rows
                        if item["case_id"] == start.case_id
                        and item["substrate"] == substrate
                        and item["arm"] == "U"
                    )
                    s1_identity_rows.append(
                        {
                            "scope": "PART_A_" + substrate,
                            "case_id": start.case_id,
                            "arm_u_digest": u_row["trajectory_digest_sha256"],
                            "arm_c_digest": row["trajectory_digest_sha256"],
                            "c_stall_detections": cast(
                                dict[str, object], run["summary"]
                            ).get("stall_detected_count", 0),
                        }
                    )
                    if (
                        row["trajectory_digest_sha256"]
                        != u_row["trajectory_digest_sha256"]
                        or cast(dict[str, object], run["summary"]).get(
                            "stall_detected_count", 0
                        )
                        != 0
                    ):
                        raise RuntimeError("Part-A S1 C≡U identity failed")

    counts = primary_counts(primary_rows)
    canonical_part_a_u = [
        row for row in part_a_rows if row["substrate"] == "S1_3M" and row["arm"] == "U"
    ]
    canonical_protocol_defect = any(
        str(row["outcome"]).startswith("INVALID_BEACON")
        or str(row["outcome"]).startswith("TERMINATED_")
        or bool(row.get("lifetime_terminated"))
        or row.get("lifetime_termination_reason") is not None
        for row in [*primary_rows, *canonical_part_a_u, *endurance_secondary]
    )
    branches = decide_branches(
        counts,
        canonical_part_a_u,
        endurance_secondary,
        True,
        canonical_protocol_defect,
    )
    s1_alert = any(
        _failure(str(row["outcome"]))
        for row in part_a_rows
        if row["substrate"] == "S1_1M" and row["arm"] == "U"
    ) or any(
        _failure(str(episode["outcome"]))
        for (seed, substrate, arm), run in matched_1m.items()
        if substrate == "S1_1M" and arm == "U"
        for episode in cast(list[dict[str, object]], run["return_records"])
    )

    first_pairs_1m: dict[str, list[dict[str, object]]] = {
        "S1_1M_vs_D045_1M": [],
        "S1_3M_vs_S1_1M": [],
    }
    lifetime_pairs_1m: dict[str, list[dict[str, object]]] = {
        "S1_1M_vs_D045_1M": [],
        "S1_3M_vs_S1_1M": [],
    }
    for seed in ENDURANCE_SEEDS:
        s1_1 = matched_1m[(seed, "S1_1M", "U")]
        d045 = matched_1m[(seed, "D045_1M", "U")]
        s1_3 = s1_endurance[(seed, "S1_3M", "U")]
        for label, left, right in (
            ("S1_1M_vs_D045_1M", s1_1, d045),
            ("S1_3M_vs_S1_1M", s1_3, s1_1),
        ):
            left_first = _common_outcome(str(_first_return(left)["outcome"]))
            right_first = _common_outcome(str(_first_return(right)["outcome"]))
            first_pairs_1m[label].append(
                {"seed": seed, "left": left_first, "right": right_first}
            )
            left_fail = any(
                _failure(str(ep["outcome"]))
                for ep in cast(list[dict[str, object]], left["return_records"])
            )
            right_fail = any(
                _failure(str(ep["outcome"]))
                for ep in cast(list[dict[str, object]], right["return_records"])
            )
            lifetime_pairs_1m[label].append(
                {
                    "seed": seed,
                    "left": "FAIL" if left_fail else "NO_FAILURE",
                    "right": "FAIL" if right_fail else "NO_FAILURE",
                }
            )
    attribution = {
        "first_return": {
            key: _matched_contrast(rows, "left", "right")
            for key, rows in first_pairs_1m.items()
        },
        "lifetime_any_failure_300000": {
            key: _matched_contrast(rows, "left", "right")
            for key, rows in lifetime_pairs_1m.items()
        },
        "attribution_boundary": "whole D-045 to D-058 wall-rule package only",
    }
    if len(primary_prefix_controls) != len(ENDURANCE_SEEDS):
        raise RuntimeError("primary prefix control did not cover all endurance seeds")
    if len(endurance_lifetime_summaries) != len(ENDURANCE_SEEDS) * 6:
        raise RuntimeError("endurance artifact lacks a required arm/substrate lifetime")
    if len(s1_identity_rows) != 320 + 60 + 2 * 1248:
        raise RuntimeError("S1 C identity control did not cover every required pair")
    s1_identity_sha256 = hashlib.sha256(
        _canonical_json_bytes(s1_identity_rows)
    ).hexdigest()
    controls = {
        "freeze_clean_protected_seed_gates": freeze_control,
        "horizon_seam": horizon_control,
        "d045_harness_identity": identity_control,
        "primary_snapshot_online_prefix_nonfeedback": {
            "result": "PASS",
            "endurance_prefix_records": primary_prefix_controls,
            "monitor_changes_causal_digest": False,
        },
        "s1_c_identity": {
            "result": "PASS",
            "paired_runs": len(s1_identity_rows),
            "all_zero_stall_asserted": True,
            "paired_digest_rows_sha256": s1_identity_sha256,
        },
        "part_a_legality": {
            "result": "PASS",
            "state_count_per_substrate": 1248,
            "all_resets_and_decision_1_return_checked": True,
            "matched_1m_bounds_checked": True,
        },
        "information_boundary": {
            "reward_zero": all(
                bool(cast(dict[str, object], row["summary"])["reward_exactly_zero"])
                for row in [*s1_endurance.values(), *matched_1m.values()]
            ),
            "organism_info_empty": all(
                bool(
                    cast(dict[str, object], row["summary"])[
                        "organism_info_exactly_empty"
                    ]
                )
                for row in [*s1_endurance.values(), *matched_1m.values()]
            ),
        },
        "determinism": {
            "ordered": True,
            "raw_transition_traces_retained": False,
            "jobs_setting_in_artifact": False,
        },
        "external_seed_reservation_recheck_sha256": reservation_recheck_sha256,
    }
    payload: dict[str, object] = {
        "schema_version": "d059-result-v1",
        "development_id": D059_ID,
        "protocol_version": PROTOCOL_VERSION,
        "authorized_base_sha": BASE_SHA,
        "frozen_brief_sha256": FROZEN_BRIEF_SHA256,
        "latest_authorizing_ruling_comment": "5941551976",
        "executed_commit_sha": executed_commit_sha,
        "execution_status": "COMPLETED",
        "result_kind": "descriptive_development_not_confirmatory",
        "claims_boundary": (
            "Programmed Level-1 descriptive Development only; D-058 is endpoint-only "
            "not hardware fidelity or continuous contact validation."
        ),
        "invalidated_and_exposed_provenance": list(_INVALIDATED_PROVENANCE),
        "seed_contract": seed_validation,
        "environment": {
            "python_version": sys.version.split()[0],
            "pyhashseed": os.environ.get("PYTHONHASHSEED"),
            "jobs_policy": (
                "single-process ascending execution; jobs option does not affect bytes"
            ),
            "expected_runtime_seconds": {
                "approximate": 7200,
                "conservative_capped_approximate": 11160,
            },
            "runtime_seconds": None,
        },
        "frozen_protocol": {
            "primary_horizon": H_PRIMARY,
            "return_classification_window": W_C,
            "endurance_horizon": H_ENDURANCE,
            "part_a_horizon": H_PART_A,
            "primary_unit": "one classifiable U first RETURN per fresh seed",
            "primary_seeds": list(PRIMARY_SEEDS),
            "endurance_subset": list(ENDURANCE_SEEDS),
            "primary_only": list(PRIMARY_ONLY_SEEDS),
            "substrates": ROOMS,
            "arms": list(ARMS),
            "reward": 0.0,
            "organism_info": {},
            "primary_boundary_order": [
                "DOCKED",
                "SPIN_EXHAUSTED",
                "INVALID_BEACON",
                "TERMINATED",
                "RETURN_TIMEOUT_FAILURE_2000",
                "CENSORED_AT_140000",
            ],
            "wall_exposure_boundary": (
                "per-RETURN frozen outcome boundary; primary and secondary snapshots "
                "remain distinct"
            ),
            "part_a_start_count_per_substrate": 1248,
            "official_part_a_rows": len(part_a_rows),
        },
        "controls": controls,
        "primary": {
            "records": primary_rows,
            "counts": counts,
            "cp_one_sided_95": {
                "lower": branches["cp_lower"],
                "upper": branches["cp_upper"],
            },
            "decision": branches,
        },
        "endurance": {
            "lifetime_summaries": endurance_lifetime_summaries,
            "return_records": endurance_episode_records,
            "canonical_s1_3m_u_secondary_for_decisions": endurance_secondary,
        },
        "endurance_secondary_s1_3m_u": endurance_secondary,
        "part_a": {
            "records": part_a_rows,
            "aggregates": _aggregate_part_a(part_a_rows),
        },
        "attribution": attribution,
        "alerts": {"S1_1M_ALERT": s1_alert},
        "signatures": {
            "primary_records_sha256": hashlib.sha256(
                _canonical_json_bytes(primary_rows)
            ).hexdigest(),
            "part_a_records_sha256": hashlib.sha256(
                _canonical_json_bytes(part_a_rows)
            ).hexdigest(),
            "endurance_secondary_sha256": hashlib.sha256(
                _canonical_json_bytes(endurance_secondary)
            ).hexdigest(),
            "endurance_return_records_sha256": hashlib.sha256(
                _canonical_json_bytes(endurance_episode_records)
            ).hexdigest(),
            "endurance_lifetime_summaries_sha256": hashlib.sha256(
                _canonical_json_bytes(endurance_lifetime_summaries)
            ).hexdigest(),
        },
    }
    return payload


_CLI_OFFICIAL_EXECUTION = False


def main(argv: Sequence[str] | None = None) -> int:
    """Execute official D-059 support; never call this before selected freeze."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--executed-commit-sha", required=True)
    parser.add_argument(
        "--jobs",
        type=int,
        default=1,
        help="accepted for regeneration parity; execution remains ordered and serial",
    )
    parser.add_argument(
        "--archive-source-sha",
        default=None,
        help="attest an immutable git archive when no .git directory is available",
    )
    parser.add_argument(
        "--runtime-seconds",
        type=float,
        default=None,
        help="frozen original-run runtime for deterministic archive regeneration",
    )
    parser.add_argument(
        "--reservation-recheck-sha256",
        required=True,
        help="SHA-256 of the required pre-freeze repository/GitHub allocation audit",
    )
    args = parser.parse_args(argv)
    if args.jobs <= 0:
        raise ValueError("jobs must be positive")
    if args.runtime_seconds is not None and (
        not math.isfinite(args.runtime_seconds) or args.runtime_seconds < 0.0
    ):
        raise ValueError("runtime-seconds must be finite and non-negative")
    global _CLI_OFFICIAL_EXECUTION
    _CLI_OFFICIAL_EXECUTION = True
    started = time.perf_counter()
    payload = _official_protocol(
        args.executed_commit_sha,
        args.jobs,
        args.reservation_recheck_sha256,
        args.archive_source_sha,
    )
    elapsed = time.perf_counter() - started
    environment = cast(dict[str, object], payload["environment"])
    environment["runtime_seconds"] = (
        elapsed if args.runtime_seconds is None else args.runtime_seconds
    )
    write_artifact(args.output, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
