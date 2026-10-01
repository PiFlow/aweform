"""D-059 S1 Level-1 floor re-baseline on the accepted D-058 substrate.

This module is an evaluator-only Development harness.  U and C are the
unchanged D-052 floor and D-055 candidate; neither arm receives evaluator
telemetry.  The only environment seam owned here is the episode horizon.
Official generation is intentionally available only through this module's
CLI, after the result-free executable/protocol freeze.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, fields, replace
from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path
from typing import Any, Callable, Final, Sequence, cast

import numpy as np

from . import d053, d055, d058
from .d045 import (
    D045_AMBIENT_TEMPERATURE_C,
    D045_BATTERY_CAPACITY_J,
    D045Env,
    D045PhysicalConfig,
)
from .d052 import (
    D052CommandSource,
    D052Controller,
    D052Mode,
)
from .d053 import D053Proposal, D053RoamingFixture
from .exp003_seed_policy import validate_exp003_development_seeds

D059_ID: Final = "D-059"
PROTOCOL_VERSION: Final = "d059-v05-s1-level1-floor-rebaseline-v2"
ARTIFACT_SCHEMA_VERSION: Final = "D059-1"
BASE_SHA: Final = "0f4b0ae22564293dd178567c4c745e5903256682"
PRIMARY_SEEDS: Final = tuple(range(23000, 23320))
ENDURANCE_SEEDS: Final = tuple(range(23000, 23060))
PRIMARY_ONLY_SEEDS: Final = tuple(range(23060, 23320))
TEST_SEED: Final = 23320
SUPPORT_SEEDS: Final = (22053, 22054, 22055, 22056, 22057)
H_PRIMARY: Final = 140_000
W_C: Final = 2_000
H_ENDURANCE: Final = 300_000
H_PART_A: Final = 2_000
MATERIALITY: Final = 0.01
CP_CONFIDENCE: Final = 0.95
ARTIFACT_FLOAT_QUANTUM: Final = Decimal("1e-12")
D059_MAX_EVENT_SAMPLES: Final = 256
D059_TEST_MAX_HORIZON: Final = 5_000
D059_PROTECTED_FILES: Final = (
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

_OFFICIAL_CLI_GUARD = False


@dataclass(frozen=True, slots=True)
class D059Start:
    """One deterministic, hull-legal Part-A start."""

    start_id: str
    start_set: str
    room_side_m: float
    body_position: tuple[float, float]
    heading_rad: float


@dataclass(frozen=True, slots=True)
class _EpisodeState:
    """Internal immutable description is not used; state is kept in dicts."""

    unused: int = 0


# The class exists only to make the evaluator's state boundary explicit to
# readers and type checkers; all mutable episode fields are local dictionaries.


def _validate_sha(value: str) -> None:
    if len(value) != 40 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("executed_commit_sha must be a lowercase 40-character SHA")


def validate_primary_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    checked = validate_exp003_development_seeds(seeds)
    if checked != PRIMARY_SEEDS:
        raise ValueError("D-059 primary seeds must equal 23000-23319")
    return checked


def validate_endurance_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    checked = validate_exp003_development_seeds(seeds)
    if checked != ENDURANCE_SEEDS:
        raise ValueError("D-059 endurance seeds must equal 23000-23059")
    return checked


def validate_primary_only_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    checked = validate_exp003_development_seeds(seeds)
    if checked != PRIMARY_ONLY_SEEDS:
        raise ValueError("D-059 primary-only seeds must equal 23060-23319")
    return checked


def validate_support_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    checked = validate_exp003_development_seeds(seeds)
    if checked != SUPPORT_SEEDS:
        raise ValueError("D-059 support seeds must equal 22053-22057")
    return checked


def validate_test_run(seed: int, horizon: int, initial_battery_fraction: float) -> None:
    if seed != TEST_SEED:
        raise ValueError(f"D-059 test runs are restricted to seed {TEST_SEED}")
    if isinstance(horizon, bool) or not 0 < horizon <= D059_TEST_MAX_HORIZON:
        raise ValueError("D-059 test horizon must be in 1..5000")
    if not 0.0 <= initial_battery_fraction <= 0.21:
        raise ValueError("D-059 test initial battery fraction must be in [0, 0.21]")


def _room_extent(heading: float) -> tuple[float, float]:
    a, c = d058.D058_HULL_HALF_LENGTH_METRES, d058.D058_HULL_HALF_WIDTH_METRES
    return (
        a * abs(math.cos(heading)) + c * abs(math.sin(heading)),
        a * abs(math.sin(heading)) + c * abs(math.cos(heading)),
    )


def _d058_config(room_side_m: float, horizon: int) -> d058.D058PhysicalConfig:
    """D-059-local Option-B horizon seam; no D-058 source is changed."""
    if room_side_m not in (1.0, 3.0):
        raise ValueError("D-059 room side must be exactly 1.0 or 3.0")
    if isinstance(horizon, bool) or horizon <= 0:
        raise ValueError("D-059 horizon must be positive")
    config = d058.D058PhysicalConfig(room_side_m)
    object.__setattr__(config, "_base", replace(config._base, episode_horizon=horizon))
    return config


def make_d059_env(substrate: str, horizon: int) -> D058EnvOrD045:
    """Construct one accepted substrate with only the local horizon seam."""
    if substrate == "S1_3M":
        return d058.D058Env(_d058_config(3.0, horizon))
    if substrate == "S1_1M":
        return d058.D058Env(_d058_config(1.0, horizon))
    if substrate == "D045_1M":
        return D045Env(
            D045PhysicalConfig(
                world_min=(0.0, 0.0), world_max=(1.0, 1.0), episode_horizon=horizon
            )
        )
    raise ValueError(f"unknown D-059 substrate {substrate!r}")


# A small protocol type alias avoids importing a third-party Gym protocol.
D058EnvOrD045 = d058.D058Env | D045Env


def _substrate_room(substrate: str) -> float:
    return 3.0 if substrate == "S1_3M" else 1.0


def _is_s1(substrate: str) -> bool:
    return substrate in {"S1_3M", "S1_1M"}


def _env_config(env: D058EnvOrD045) -> D045PhysicalConfig:
    if isinstance(env, d058.D058Env):
        return env.config._base
    return env.config


def _env_body(env: D058EnvOrD045) -> tuple[float, float, float]:
    if env.body is None:
        raise RuntimeError("environment body unavailable")
    return env.body.x, env.body.y, env.body.heading


def _wall_ids(env: D058EnvOrD045, substrate: str, pushing: bool) -> tuple[str, ...]:
    if not pushing:
        return ()
    if isinstance(env, d058.D058Env):
        contact = env.last_contact
        if contact is None:
            return ()
        return tuple(
            name
            for name, value in (
                ("x_min", contact.pushing_x_min),
                ("x_max", contact.pushing_x_max),
                ("y_min", contact.pushing_y_min),
                ("y_max", contact.pushing_y_max),
            )
            if value
        )
    if env.last_transition is None:
        return ()
    x, y = env.last_transition.position_after
    epsilon = 1e-12
    length = _substrate_room(substrate)
    return tuple(
        name
        for name, value in (
            ("x_min", x <= epsilon),
            ("x_max", x >= length - epsilon),
            ("y_min", y <= epsilon),
            ("y_max", y >= length - epsilon),
        )
        if value
    )


def _wall_event(env: D058EnvOrD045, substrate: str) -> tuple[bool, tuple[str, ...]]:
    if isinstance(env, d058.D058Env):
        contact = env.last_contact
        if contact is None:
            return False, ()
        ids = _wall_ids(env, substrate, True)
        return bool(ids), ids
    telemetry = env.last_transition
    if telemetry is None or telemetry.boundary_scale >= 1.0:
        return False, ()
    ids = _wall_ids(env, substrate, True)
    return True, ids


def _fresh_hash() -> hashlib._Hash:
    return hashlib.sha256()


def _hash_update(hasher: hashlib._Hash, row: object) -> None:
    encoded = json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False)
    hasher.update(encoded.encode("utf-8"))
    hasher.update(b"\n")


def _trace_row(
    decision: object,
    proposal: D053Proposal,
    observation_before: np.ndarray,
    observation_after: np.ndarray,
    telemetry: object,
    wheels: tuple[float, float],
) -> dict[str, object]:
    # The digest is a causal identity check, not an artifact trace.  It
    # includes all controller/environment fields used by the accepted runners.
    d = decision
    t = telemetry
    return {
        "transition": int(getattr(d, "transition_index")),
        "events": list(getattr(d, "events")),
        "active_mode": getattr(getattr(d, "active_mode"), "value"),
        "command_source": getattr(getattr(d, "command_source"), "value"),
        "wheel_command": list(wheels),
        "proposed_wheel_command": list(proposal.wheel_command),
        "symbolic_proposal": proposal.symbolic_action.name,
        "d050_mode": (
            getattr(getattr(d, "d050_mode"), "value")
            if getattr(d, "d050_mode") is not None
            else None
        ),
        "terminal_spin_count": int(getattr(d, "terminal_spin_count")),
        "terminal_spin_exhausted": bool(getattr(d, "terminal_spin_exhausted")),
        "observation_before": observation_before.tobytes().hex(),
        "observation_after": observation_after.tobytes().hex(),
        "reward": 0.0,
        "info": {},
        "position_before": list(getattr(t, "position_before")),
        "position_after": list(getattr(t, "position_after")),
        "heading_before": getattr(t, "heading_before"),
        "heading_after": getattr(t, "heading_after"),
        "battery_before_j": getattr(t, "battery_before_j"),
        "battery_after_j": getattr(t, "battery_after_j"),
        "body_temperature_before_c": getattr(t, "body_temperature_before_c"),
        "body_temperature_after_c": getattr(t, "body_temperature_after_c"),
        "actual_delta_left": getattr(t, "actual_delta_left"),
        "actual_delta_right": getattr(t, "actual_delta_right"),
        "boundary_scale": getattr(t, "boundary_scale"),
        "charging_contact_before": bool(getattr(t, "charging_contact_before")),
        "charging_contact_after": bool(getattr(t, "charging_contact_after")),
        "terminated": bool(getattr(t, "terminated")),
        "truncated": bool(getattr(t, "truncated")),
        "termination_reason": (
            getattr(getattr(t, "termination_reason"), "value")
            if getattr(t, "termination_reason") is not None
            else None
        ),
    }


def _d059_reset_options(
    substrate: str,
    position: tuple[float, float],
    heading: float,
    initial_battery_fraction: float,
) -> dict[str, object]:
    room = _substrate_room(substrate)
    return {
        "body_position": position,
        "station_center": (room / 2.0, room / 2.0),
        "heading": heading,
        "battery_j": initial_battery_fraction * D045_BATTERY_CAPACITY_J,
        "body_temperature_c": D045_AMBIENT_TEMPERATURE_C,
        "charger_termination_latched": False,
    }


def _event_sample(
    decision: object,
    proposal: D053Proposal,
    observation_before: np.ndarray,
    observation_after: np.ndarray,
    telemetry: object,
    events: list[str],
    wheels: tuple[float, float],
    cycle_index: int,
) -> dict[str, object]:
    d = decision
    t = telemetry
    d050 = getattr(d, "d050_mode")
    return {
        "transition": int(getattr(d, "transition_index")),
        "events": events,
        "active_mode": getattr(getattr(d, "active_mode"), "value"),
        "command_source": getattr(getattr(d, "command_source"), "value"),
        "passed_through": bool(getattr(d, "passed_through")),
        "preempted": bool(getattr(d, "preempted")),
        "wheel_command": list(wheels),
        "proposed_wheel_command": list(proposal.wheel_command),
        "symbolic_proposal": proposal.symbolic_action.name,
        "d050_mode": d050.value if d050 is not None else None,
        "terminal_spin_count": int(getattr(d, "terminal_spin_count")),
        "terminal_spin_exhausted": bool(getattr(d, "terminal_spin_exhausted")),
        "energy_before": float(observation_before[0]),
        "energy_after": float(observation_after[0]),
        "battery_before_j": getattr(t, "battery_before_j"),
        "battery_after_j": getattr(t, "battery_after_j"),
        "charging_contact_before": bool(getattr(t, "charging_contact_before")),
        "charging_contact_after": bool(getattr(t, "charging_contact_after")),
        "x": getattr(t, "position_after")[0],
        "y": getattr(t, "position_after")[1],
        "heading": getattr(t, "heading_after"),
        "thermal": float(observation_after[1]),
        "boundary_scale": getattr(t, "boundary_scale"),
        "simulated_seconds": int(getattr(d, "transition_index")) * 0.1,
        "cycle_index": cycle_index,
        "terminated": bool(getattr(t, "terminated")),
        "truncated": bool(getattr(t, "truncated")),
    }


def _episode_tail_path(centres: Sequence[tuple[float, float]]) -> float:
    tail = list(centres)[-101:]
    return sum(math.dist(a, b) for a, b in zip(tail, tail[1:]))


def _episode_anatomy(ep: dict[str, Any]) -> dict[str, object]:
    final_contacts = cast(
        list[tuple[int, tuple[str, ...], tuple[float, float]]], ep["final_contacts"]
    )
    ids = sorted({wall for _, walls, _ in final_contacts for wall in walls})
    path = _episode_tail_path(cast(list[tuple[float, float]], ep["centres"]))
    if not final_contacts:
        anatomy = "NONE"
    elif path <= 1e-9:
        anatomy = "STATIC"
    else:
        anatomy = "DYNAMIC"
    return {
        "wall_exposed_final_100": bool(final_contacts),
        "wall_exposed_final_100_transition_count": len(final_contacts),
        "final_100_centre_path_m": path,
        "final_100_active_wall_ids": ids,
        "final_100_contact_anatomy": anatomy,
    }


def _measurement_record(
    ep: dict[str, Any],
    *,
    substrate: str,
    arm: str,
    seed: int | None,
    role: str,
    outcome: str,
    boundary: str,
    boundary_transition: int,
) -> dict[str, object]:
    anatomy = _episode_anatomy(ep)
    classifiable = outcome not in {"CENSORED_NO_RETURN", "CENSORED_IN_PROGRESS"}
    failed = classifiable and outcome != "DOCKED"
    record: dict[str, object] = {
        "seed": seed,
        "substrate": substrate,
        "arm": arm,
        "role": role,
        "cycle_index": ep["cycle_index"],
        "return_activation_transition": ep["start_transition"],
        "classification_boundary": boundary,
        "classification_transition": boundary_transition,
        "terminal_outcome": outcome,
        "classifiable": classifiable,
        "failed": failed,
        "wall_exposed_any": bool(ep["wall_exposed_any"]),
        "wall_exposed_transition_count": int(ep["wall_exposed_transition_count"]),
        "wall_exposed_final_100": anatomy["wall_exposed_final_100"],
        "wall_exposed_final_100_transition_count": anatomy[
            "wall_exposed_final_100_transition_count"
        ],
        "final_100_centre_path_m": anatomy["final_100_centre_path_m"],
        "final_100_active_wall_ids": anatomy["final_100_active_wall_ids"],
        "final_100_contact_anatomy": anatomy["final_100_contact_anatomy"],
        "wall_exposed_failure": bool(failed and ep["wall_exposed_any"]),
        "noncontact_failure": bool(failed and not ep["wall_exposed_any"]),
        "return_decision_count": ep["return_decision_count"],
        "termination_reason": ep.get("termination_reason"),
    }
    return record


def _classify_during_step(
    decision: object,
    telemetry: object,
    *,
    episode: dict[str, Any] | None,
    return_decisions: int,
    classification_window: int,
) -> tuple[str, str] | None:
    if episode is None:
        return None
    events = cast(tuple[str, ...], getattr(decision, "events"))
    if "CHARGING_CONTACT" in events:
        return "DOCKED", "FIRST_CHARGING_CONTACT"
    if "TERMINAL_SPIN_EXHAUSTED" in events:
        return "SPIN_EXHAUSTED", "TERMINAL_SPIN_EXHAUSTED"
    if "INVALID_BEACON" in events:
        return "INVALID_BEACON", "INVALID_BEACON"
    if bool(getattr(telemetry, "terminated")):
        reason = getattr(telemetry, "termination_reason")
        return (
            f"TERMINATED_{reason.value if reason is not None else 'UNKNOWN'}",
            "ENVIRONMENT_TERMINATION",
        )
    if return_decisions >= classification_window:
        return "RETURN_TIMEOUT_FAILURE", "RETURN_CLASSIFICATION_WINDOW"
    return None


def _finalize_episode_outcome(
    cycle: dict[str, Any], terminated: bool, truncated: bool, reason: str | None
) -> None:
    if cycle.get("outcome") is not None:
        return
    if terminated:
        cycle["outcome"] = f"TERMINATED_{reason or 'UNKNOWN'}"
    elif truncated:
        cycle["outcome"] = "TRUNCATED_IN_RETURN"
    else:
        cycle["outcome"] = "INCOMPLETE"


def _run_lifetime(
    seed: int | None,
    *,
    substrate: str,
    arm: str,
    horizon: int,
    primary_horizon: int,
    classification_window: int,
    initial_battery_fraction: float,
    start: D059Start | None = None,
    zero_proposals: bool = False,
    measurement_enabled: bool = True,
    continue_full: bool = False,
) -> dict[str, object]:
    if arm not in {"U", "C"}:
        raise ValueError("D-059 arm must be U or C")
    room = _substrate_room(substrate)
    position = start.body_position if start is not None else (room / 2.0, room / 2.0)
    heading = start.heading_rad if start is not None else 0.0
    env = make_d059_env(substrate, horizon)
    observation, reset_info = env.reset(
        options=_d059_reset_options(
            substrate, position, heading, initial_battery_fraction
        )
    )
    if start is not None and bool(observation[5]):
        raise RuntimeError(
            f"Part-A start is charging-contacting at reset: {start.start_id}"
        )
    if reset_info != {}:
        raise RuntimeError("D-059 reset info must remain empty")
    controller: D052Controller | d055.D055StallTurnCandidate
    controller = (
        D052Controller()
        if arm == "U"
        else d055.D055StallTurnCandidate(D052Controller())
    )
    fixture = None if zero_proposals else D053RoamingFixture(cast(int, seed))
    trace_digest = _fresh_hash()
    modes: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    all_events: list[dict[str, object]] = []
    cycles: list[dict[str, Any]] = []
    episodes: list[dict[str, object]] = []
    current_cycle: dict[str, Any] | None = None
    current_ep: dict[str, Any] | None = None
    normal_roam_since_yield = 0
    incidental_acquisitions: list[dict[str, object]] = []
    incidental_contact_steps = 0
    min_observation = float(observation[0])
    min_battery_j = env.battery_j
    boundary_scaled = 0
    invalid_beacon_count = 0
    exhausted_transitions: list[int] = []
    spin_max = 0
    return_starts: list[dict[str, object]] = []
    terminated = truncated = False
    termination_reason: str | None = None
    rewards_zero = True
    infos_empty = True
    previous_mode: D052Mode | None = None
    previous_source: object = None
    previous_d050_mode: object = None
    first_return_seen = False
    primary_record: dict[str, object] | None = None
    primary_seed_boundary = False
    primary_snapshot_digest = _fresh_hash()
    transition_count = 0

    reset_row = {
        "transition": 0,
        "events": ["RESET"],
        "active_mode": "NORMAL",
        "command_source": None,
        "energy_before": float(observation[0]),
        "charging_contact_before": bool(observation[5]),
    }
    _hash_update(trace_digest, reset_row)
    stall_detected_by_cycle: Counter[int] = Counter()

    def append_secondary(
        ep: dict[str, Any], outcome: str, boundary: str, index: int
    ) -> None:
        episodes.append(
            _measurement_record(
                ep,
                substrate=substrate,
                arm=arm,
                seed=seed,
                role="SECONDARY",
                outcome=outcome,
                boundary=boundary,
                boundary_transition=index,
            )
        )

    for _ in range(horizon):
        energy_before = float(observation[0])
        contact_before = bool(observation[5])
        if zero_proposals:
            # The symbolic label is evaluator-only and deterministic for Part A.
            action = cast(Any, type("PartAAction", (), {"name": "ZERO"})())
            proposal = D053Proposal(action, (0.0, 0.0))
        else:
            if fixture is None:
                raise RuntimeError("D-059 fixture was not initialized")
            proposal = fixture.propose()
        decision = controller.command(observation, proposal.wheel_command)
        if (
            start is not None
            and zero_proposals
            and transition_count == 0
            and "RETURN_ACTIVATED" not in getattr(decision, "events")
        ):
            raise RuntimeError(
                f"Part-A start did not activate RETURN: {start.start_id}"
            )
        modes[getattr(getattr(decision, "active_mode"), "value")] += 1
        sources[getattr(getattr(decision, "command_source"), "value")] += 1
        spin_max = max(spin_max, int(getattr(decision, "terminal_spin_count")))
        events_from_decision = list(cast(tuple[str, ...], getattr(decision, "events")))
        if "INVALID_BEACON" in events_from_decision:
            invalid_beacon_count += 1
        if "TERMINAL_SPIN_EXHAUSTED" in events_from_decision:
            exhausted_transitions.append(int(getattr(decision, "transition_index")))
        active_mode = getattr(decision, "active_mode")
        if (
            current_cycle is None
            and active_mode is D052Mode.NORMAL
            and "RECOVERY_YIELD" not in events_from_decision
        ):
            normal_roam_since_yield += 1
        if "RETURN_ACTIVATED" in events_from_decision:
            if current_cycle is not None:
                raise RuntimeError("D-059 observed overlapping RETURN cycles")
            body_x, body_y, _ = _env_body(env)
            station_x, station_y = room / 2.0, room / 2.0
            current_cycle = {
                "cycle_index": len(cycles) + 1,
                "start_transition": int(getattr(decision, "transition_index")),
                "normal_roam_length": normal_roam_since_yield,
                "return_length": 0,
                "charge_length": 0,
                "energy_at_return_activation": energy_before,
                "energy_after_first_charging_contact": None,
                "energy_at_recovery_yield": None,
                "maximum_terminal_spin_count": 0,
                "outcome": None,
            }
            current_ep = {
                "cycle_index": len(cycles) + 1,
                "start_transition": int(getattr(decision, "transition_index")),
                "wall_exposed_any": False,
                "wall_exposed_transition_count": 0,
                "final_contacts": deque(maxlen=100),
                "centres": deque(maxlen=4000),
                "return_decision_count": 0,
                "primary_boundary": None,
                "secondary_boundary": None,
                "secondary_eligible": True,
                "primary_recorded": False,
                "termination_reason": None,
            }
            current_ep["centres"].append((body_x, body_y))
            cycles.append(current_cycle)
            return_starts.append(
                {
                    "transition": int(getattr(decision, "transition_index")),
                    "station_distance_m": math.hypot(
                        station_x - body_x, station_y - body_y
                    ),
                    "station_bearing_rad": math.atan2(
                        station_y - body_y, station_x - body_x
                    ),
                }
            )
            normal_roam_since_yield = 0
            first_return_seen = True
        if current_cycle is not None:
            if active_mode is D052Mode.RETURN:
                current_cycle["return_length"] = int(current_cycle["return_length"]) + 1
                if current_ep is not None:
                    current_ep["return_decision_count"] = (
                        int(current_ep["return_decision_count"]) + 1
                    )
            elif active_mode is D052Mode.CHARGE:
                current_cycle["charge_length"] = int(current_cycle["charge_length"]) + 1
            elif "RECOVERY_YIELD" not in events_from_decision:
                current_cycle["normal_roam_length"] = (
                    int(current_cycle["normal_roam_length"]) + 1
                )
            current_cycle["maximum_terminal_spin_count"] = max(
                int(current_cycle["maximum_terminal_spin_count"]),
                int(getattr(decision, "terminal_spin_count")),
            )

        wheels = (
            float(getattr(decision, "wheel_delta_left")),
            float(getattr(decision, "wheel_delta_right")),
        )
        observation_after, reward, terminated, truncated, info = env.step(wheels)
        telemetry = env.last_transition
        if telemetry is None:
            raise RuntimeError("D-059 environment did not provide transition telemetry")
        transition_count += 1
        rewards_zero = rewards_zero and reward == 0.0
        infos_empty = infos_empty and info == {}
        min_observation = min(min_observation, float(observation_after[0]))
        min_battery_j = min(min_battery_j, env.battery_j)
        boundary_scaled += int(float(getattr(telemetry, "boundary_scale")) < 1.0)
        contact_after = bool(observation_after[5])
        events = list(events_from_decision)
        if not contact_before and contact_after:
            events.append("PHYSICAL_CONTACT_ACQUIRED")
            if (
                active_mode is D052Mode.RETURN
                and current_cycle is not None
                and current_cycle["energy_after_first_charging_contact"] is None
            ):
                current_cycle["energy_after_first_charging_contact"] = float(
                    observation_after[0]
                )
                current_cycle["first_charging_contact_transition"] = int(
                    getattr(decision, "transition_index")
                )
            elif (
                getattr(getattr(decision, "command_source"), "value")
                == D052CommandSource.PASS_THROUGH.value
                and active_mode is D052Mode.NORMAL
            ):
                incidental_acquisitions.append(
                    {
                        "transition": int(getattr(decision, "transition_index")),
                        "energy": float(observation_after[0]),
                    }
                )
        elif contact_before and not contact_after:
            events.append("PHYSICAL_CONTACT_LOST")
        if active_mode is D052Mode.NORMAL and contact_after:
            incidental_contact_steps += 1
        wall_active, wall_ids = _wall_event(env, substrate)
        if wall_active:
            boundary_scaled += 0  # retain the explicit D-045 counter above
        if current_ep is not None:
            current_ep["centres"].append(tuple(getattr(telemetry, "position_after")))
            if wall_active:
                current_ep["wall_exposed_any"] = True
                current_ep["wall_exposed_transition_count"] = (
                    int(current_ep["wall_exposed_transition_count"]) + 1
                )
            if wall_active:
                cast(
                    deque[tuple[int, tuple[str, ...], tuple[float, float]]],
                    current_ep["final_contacts"],
                ).append(
                    (
                        int(getattr(decision, "transition_index")),
                        wall_ids,
                        tuple(getattr(telemetry, "position_after")),
                    )
                )
        if bool(getattr(telemetry, "terminated")):
            events.append("TERMINATED")
            termination_reason = (
                getattr(getattr(telemetry, "termination_reason"), "value")
                if getattr(telemetry, "termination_reason") is not None
                else None
            )
            if current_cycle is not None:
                current_cycle["end_transition"] = int(
                    getattr(decision, "transition_index")
                )
                _finalize_episode_outcome(
                    current_cycle, terminated, truncated, termination_reason
                )
            if current_ep is not None:
                current_ep["termination_reason"] = termination_reason
        if bool(getattr(telemetry, "truncated")):
            events.append("TRUNCATED")
            if current_cycle is not None:
                current_cycle["end_transition"] = int(
                    getattr(decision, "transition_index")
                )
                _finalize_episode_outcome(
                    current_cycle, terminated, truncated, termination_reason
                )

        if (
            isinstance(controller, d055.D055StallTurnCandidate)
            and bool(getattr(decision, "stall_detected"))
            and current_cycle is not None
        ):
            stall_detected_by_cycle[int(current_cycle["cycle_index"])] += 1

        if current_ep is not None and current_cycle is not None:
            candidate = _classify_during_step(
                decision,
                telemetry,
                episode=current_ep,
                return_decisions=int(current_ep["return_decision_count"]),
                classification_window=classification_window,
            )
            if candidate is not None and measurement_enabled:
                outcome, boundary = candidate
                boundary_transition = int(getattr(decision, "transition_index"))
                if current_ep["primary_boundary"] is None and not primary_seed_boundary:
                    snapshot = _measurement_record(
                        current_ep,
                        substrate=substrate,
                        arm=arm,
                        seed=seed,
                        role="PRIMARY",
                        outcome=outcome,
                        boundary=boundary,
                        boundary_transition=boundary_transition,
                    )
                    primary_record = snapshot
                    primary_seed_boundary = True
                    current_ep["primary_boundary"] = boundary
                    current_ep["secondary_eligible"] = outcome.startswith("CENSORED")
                    current_ep["primary_recorded"] = True
                    _hash_update(primary_snapshot_digest, snapshot)
                elif (
                    primary_seed_boundary
                    and bool(current_ep["secondary_eligible"])
                    and current_ep["secondary_boundary"] is None
                ):
                    append_secondary(current_ep, outcome, boundary, boundary_transition)
                    current_ep["secondary_boundary"] = boundary
        # The primary measurement cap is a diagnostic boundary, never a causal one.
        if (
            measurement_enabled
            and primary_record is None
            and transition_count >= primary_horizon
        ):
            if current_ep is None:
                outcome = "CENSORED_NO_RETURN"
                boundary = "PRIMARY_HORIZON_NO_RETURN"
            else:
                outcome = "CENSORED_IN_PROGRESS"
                boundary = "PRIMARY_HORIZON"
            ep_for_snapshot = current_ep or {
                "cycle_index": None,
                "start_transition": None,
                "wall_exposed_any": False,
                "wall_exposed_transition_count": 0,
                "final_contacts": deque(maxlen=100),
                "centres": deque(maxlen=4000),
                "return_decision_count": 0,
                "primary_boundary": None,
                "secondary_boundary": None,
                "secondary_eligible": True,
                "primary_recorded": False,
                "termination_reason": None,
            }
            primary_record = _measurement_record(
                ep_for_snapshot,
                substrate=substrate,
                arm=arm,
                seed=seed,
                role="PRIMARY",
                outcome=outcome,
                boundary=boundary,
                boundary_transition=transition_count,
            )
            if current_ep is not None:
                current_ep["primary_boundary"] = boundary
                current_ep["secondary_eligible"] = outcome.startswith("CENSORED")
            primary_seed_boundary = True
            _hash_update(primary_snapshot_digest, primary_record)
        sample_cycle_index = (
            len(cycles)
            if "RECOVERY_YIELD" in events_from_decision
            else int(current_cycle["cycle_index"])
            if current_cycle is not None
            else len(cycles)
        )
        sample = _event_sample(
            decision,
            proposal,
            observation,
            observation_after,
            telemetry,
            events,
            wheels,
            sample_cycle_index,
        )
        _hash_update(
            trace_digest,
            _trace_row(
                decision, proposal, observation, observation_after, telemetry, wheels
            ),
        )
        mode_changed = active_mode is not previous_mode
        source = getattr(decision, "command_source")
        d050_mode = getattr(decision, "d050_mode")
        source_changed = source is not previous_source
        d050_changed = d050_mode is not previous_d050_mode
        if (
            events
            or mode_changed
            or source_changed
            or d050_changed
            or contact_before != contact_after
        ):
            all_events.append(
                {
                    key: sample[key]
                    for key in (
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
                }
            )
        previous_mode, previous_source, previous_d050_mode = (
            active_mode,
            source,
            d050_mode,
        )
        observation = observation_after

        if "RECOVERY_YIELD" in events_from_decision and current_cycle is not None:
            current_cycle["energy_at_recovery_yield"] = energy_before
            current_cycle["end_transition"] = int(getattr(decision, "transition_index"))
            current_cycle["outcome"] = "YIELDED"
            if current_ep is not None:
                if (
                    primary_seed_boundary
                    and bool(current_ep["secondary_eligible"])
                    and current_ep["secondary_boundary"] is None
                ):
                    append_secondary(
                        current_ep,
                        "DOCKED",
                        "FIRST_CHARGING_CONTACT",
                        int(getattr(decision, "transition_index")),
                    )
                    current_ep["secondary_boundary"] = "FIRST_CHARGING_CONTACT"
                current_ep = None
            current_cycle = None
            normal_roam_since_yield = 0
        elif current_cycle is not None and (terminated or truncated):
            if current_ep is not None:
                current_ep = None
            current_cycle = None

        if terminated or truncated:
            break
        if (
            not zero_proposals
            and primary_record is not None
            and not continue_full
            and seed not in ENDURANCE_SEEDS
            and measurement_enabled
        ):
            # Primary-only runs stop after the immutable record, not after a
            # result-dependent outcome; the stop is the frozen measurement rule.
            break

    if primary_record is None and measurement_enabled:
        ep_for_snapshot = current_ep or {
            "cycle_index": None,
            "start_transition": None,
            "wall_exposed_any": False,
            "wall_exposed_transition_count": 0,
            "final_contacts": deque(maxlen=100),
            "centres": deque(maxlen=4000),
            "return_decision_count": 0,
            "primary_boundary": None,
            "secondary_boundary": None,
            "secondary_eligible": True,
            "primary_recorded": False,
            "termination_reason": termination_reason,
        }
        primary_record = _measurement_record(
            ep_for_snapshot,
            substrate=substrate,
            arm=arm,
            seed=seed,
            role="PRIMARY",
            outcome="CENSORED_IN_PROGRESS"
            if first_return_seen
            else "CENSORED_NO_RETURN",
            boundary="LIFETIME_END",
            boundary_transition=transition_count,
        )
        primary_seed_boundary = True
        _hash_update(primary_snapshot_digest, primary_record)

    if current_cycle is not None:
        _finalize_episode_outcome(
            current_cycle, terminated, truncated, termination_reason
        )
    # A classifiable secondary episode may still be open at a genuine lifetime
    # end; retain only its frozen measurement, never infer a failure from censoring.
    total = transition_count
    d052_sources = {source.value: sources[source.value] for source in D052CommandSource}
    summary: dict[str, object] = {
        "seed": seed,
        "total_transitions": total,
        "termination_reason": termination_reason,
        "terminated": terminated,
        "truncated": truncated,
        "final_mode": getattr(getattr(controller, "mode"), "value"),
        "final_cycle_index": len(cycles),
        "mode_transition_counts": {mode.value: modes[mode.value] for mode in D052Mode},
        "command_source_counts": d052_sources,
        "level1_preemption_count": int(
            getattr(controller, "preemption_transition_count")
        ),
        "level1_preemption_fraction": int(
            getattr(controller, "preemption_transition_count")
        )
        / total
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
        "boundary_scaled_transition_count": boundary_scaled,
        "return_start_pose_evaluator_only": return_starts,
        "cycles": cycles,
        "event_row_count": len(all_events) + 1,
        "retained_sample_count": len(_bounded_event_samples([reset_row, *all_events])),
        "samples_truncated": len(_bounded_event_samples([reset_row, *all_events]))
        < len(all_events) + 1,
        "event_samples": _bounded_event_samples([reset_row, *all_events]),
        "reward_exactly_zero": rewards_zero,
        "organism_info_exactly_empty": infos_empty,
        "causal_digest_sha256": trace_digest.hexdigest(),
        "primary_snapshot_digest_sha256": primary_snapshot_digest.hexdigest(),
    }
    if isinstance(controller, d055.D055StallTurnCandidate):
        summary["stall_turn_count"] = controller.stall_turn_count
        summary["stall_detected_count"] = controller.stall_detected_count
        summary["first_stall_turn_transition"] = controller.first_stall_turn_transition
        summary["stall_counts_by_cycle"] = [
            {
                "cycle_index": cycle["cycle_index"],
                "stall_turn_count": sum(
                    1
                    for item in all_events
                    if item["command_source"] == "STALL_TURN"
                    and item["transition"] >= cycle["start_transition"]
                    and item["transition"]
                    <= cycle.get("end_transition", item["transition"])
                ),
                "stall_detected_count": stall_detected_by_cycle[
                    int(cycle["cycle_index"])
                ],
            }
            for cycle in cycles
        ]
        cast(dict[str, int], summary["command_source_counts"])["STALL_TURN"] = (
            controller.stall_turn_count
        )
    if total <= 0:
        raise RuntimeError("D-059 lifetime executed no transitions")
    if (
        int(cast(int, summary["level1_preemption_count"]))
        + int(cast(int, summary["pass_through_count"]))
        != total
    ):
        raise RuntimeError("D-059 lifetime counters are inconsistent")
    return {
        "summary": summary,
        "primary": primary_record,
        "episodes": episodes,
        "causal_digest_sha256": trace_digest.hexdigest(),
        "primary_snapshot_digest_sha256": primary_snapshot_digest.hexdigest(),
    }


def _bounded_event_samples(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    # Reuse the accepted deterministic D-053 event sampling implementation.
    return d053._bounded_samples(rows)


def run_test_lifetime(
    seed: int = TEST_SEED,
    *,
    horizon: int = 5_000,
    initial_battery_fraction: float = 0.21,
    measurement_enabled: bool = True,
) -> dict[str, object]:
    """Run only the bounded test-only fixture; never an official seed."""
    validate_test_run(seed, horizon, initial_battery_fraction)
    return _run_lifetime(
        seed,
        substrate="S1_3M",
        arm="U",
        horizon=horizon,
        primary_horizon=horizon,
        classification_window=W_C,
        initial_battery_fraction=initial_battery_fraction,
        measurement_enabled=measurement_enabled,
    )


def _headings() -> tuple[float, ...]:
    return tuple((2 * k + 1) * math.pi / 16.0 for k in range(16))


def part_a_starts(room_side_m: float) -> tuple[D059Start, ...]:
    if room_side_m not in (1.0, 3.0):
        raise ValueError("Part-A room side must be 1.0 or 3.0")
    starts: list[D059Start] = []
    for h_index, heading in enumerate(_headings()):
        hx, hy = _room_extent(heading)
        for clearance in (0.0, 0.05):
            for fraction in (0.20, 0.35, 0.50, 0.65, 0.80):
                along = fraction * room_side_m
                positions = (
                    ("bottom", (along, hy + clearance)),
                    ("top", (along, room_side_m - hy - clearance)),
                    ("left", (hx + clearance, along)),
                    ("right", (room_side_m - hx - clearance, along)),
                )
                for label, position in positions:
                    starts.append(
                        D059Start(
                            f"A1-{label}-c{clearance:.2f}-f{fraction:.2f}-h{h_index:02d}",
                            "A1_wall",
                            room_side_m,
                            position,
                            heading,
                        )
                    )
            corners = (
                ("bottom_left", (hx + clearance, hy + clearance)),
                ("bottom_right", (room_side_m - hx - clearance, hy + clearance)),
                ("top_left", (hx + clearance, room_side_m - hy - clearance)),
                (
                    "top_right",
                    (room_side_m - hx - clearance, room_side_m - hy - clearance),
                ),
            )
            for label, position in corners:
                starts.append(
                    D059Start(
                        f"A1-{label}-c{clearance:.2f}-h{h_index:02d}",
                        "A1_corner",
                        room_side_m,
                        position,
                        heading,
                    )
                )
    fractions = (0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85)
    for xi, x_fraction in enumerate(fractions):
        for yi, y_fraction in enumerate(fractions):
            if x_fraction in {0.45, 0.55} and y_fraction in {0.45, 0.55}:
                continue
            for hi in range(8):
                heading = hi * math.pi / 4.0
                starts.append(
                    D059Start(
                        f"A2-x{xi:02d}-y{yi:02d}-h{hi:02d}",
                        "A2_lattice",
                        room_side_m,
                        (x_fraction * room_side_m, y_fraction * room_side_m),
                        heading,
                    )
                )
    expected = 1248
    if len(starts) != expected:
        raise RuntimeError(f"D-059 Part-A cardinality changed: {len(starts)}")
    return tuple(starts)


def _start_is_legal(start: D059Start) -> bool:
    hx, hy = _room_extent(start.heading_rad)
    length = start.room_side_m
    x, y = start.body_position
    return hx <= x <= length - hx and hy <= y <= length - hy


def run_part_a_case(start: D059Start, substrate: str, arm: str) -> dict[str, object]:
    if substrate not in {"S1_3M", "S1_1M", "D045_1M"}:
        raise ValueError("invalid Part-A substrate")
    expected_room = _substrate_room(substrate)
    if start.room_side_m != expected_room:
        raise ValueError("Part-A start room does not match substrate")
    if not _start_is_legal(start):
        raise ValueError("Part-A start is not hull legal")
    run = _run_lifetime(
        None,
        substrate=substrate,
        arm=arm,
        horizon=H_PART_A,
        primary_horizon=H_PART_A,
        classification_window=W_C,
        initial_battery_fraction=0.20,
        start=start,
        zero_proposals=True,
    )
    primary = cast(dict[str, object], run["primary"])
    return {
        "start_id": start.start_id,
        "start_set": start.start_set,
        "room_side_m": start.room_side_m,
        "body_position": list(start.body_position),
        "heading_rad": start.heading_rad,
        "substrate": substrate,
        "arm": arm,
        "primary": primary,
        "causal_digest_sha256": run["causal_digest_sha256"],
        "summary_readout": _summary_readout(cast(dict[str, object], run["summary"])),
    }


def _summary_readout(summary: dict[str, object]) -> dict[str, object]:
    return {
        key: summary[key]
        for key in (
            "seed",
            "total_transitions",
            "termination_reason",
            "terminated",
            "truncated",
            "final_mode",
            "return_activated_count",
            "return_dock_acquisition_count",
            "completed_recovery_yield_count",
            "terminal_spin_maximum",
            "terminal_spin_exhaustion_count",
            "minimum_observed_energy",
            "minimum_battery_j",
            "boundary_scaled_transition_count",
            "reward_exactly_zero",
            "organism_info_exactly_empty",
            "causal_digest_sha256",
        )
    }


def _first_return_failure(record: dict[str, object] | None) -> bool | None:
    if record is None or not bool(record["classifiable"]):
        return None
    return bool(record["failed"])


def _run_ordered(
    fn: Callable[[Any], dict[str, object]], values: Sequence[Any], jobs: int
) -> list[dict[str, object]]:
    if jobs <= 0:
        raise ValueError("jobs must be positive")
    if jobs == 1:
        return [fn(value) for value in values]
    with ThreadPoolExecutor(max_workers=jobs) as executor:
        # executor.map preserves the declared input order.
        return list(executor.map(fn, values))


def _cp_beta_cdf(x: float, a: float, b: float) -> float:
    """Regularized incomplete beta, Numerical Recipes continued fraction."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    ln_beta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)

    def fraction(xx: float, aa: float, bb: float) -> float:
        qab, qap, qam = aa + bb, aa + 1.0, aa - 1.0
        c = 1.0
        d = 1.0 - qab * xx / qap
        d = 1e-300 if abs(d) < 1e-300 else d
        d = 1.0 / d
        h = d
        for m in range(1, 10_000):
            m2 = 2 * m
            aa_m = m * (bb - m) * xx / ((qam + m2) * (aa + m2))
            d = 1.0 + aa_m * d
            d = 1e-300 if abs(d) < 1e-300 else d
            c = 1.0 + aa_m / c
            c = 1e-300 if abs(c) < 1e-300 else c
            d = 1.0 / d
            h *= d * c
            aa_m = -(aa + m) * (qab + m) * xx / ((aa + m2) * (qap + m2))
            d = 1.0 + aa_m * d
            d = 1e-300 if abs(d) < 1e-300 else d
            c = 1.0 + aa_m / c
            c = 1e-300 if abs(c) < 1e-300 else c
            d = 1.0 / d
            delta = d * c
            h *= delta
            if abs(delta - 1.0) < 3.0e-14:
                break
        return h

    front = math.exp(a * math.log(x) + b * math.log1p(-x) - ln_beta)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * fraction(x, a, b) / a
    return 1.0 - front * fraction(1.0 - x, b, a) / b


def _beta_quantile(probability: float, a: float, b: float) -> float:
    if probability <= 0.0:
        return 0.0
    if probability >= 1.0:
        return 1.0
    low, high = 0.0, 1.0
    for _ in range(120):
        middle = (low + high) / 2.0
        if _cp_beta_cdf(middle, a, b) < probability:
            low = middle
        else:
            high = middle
    return (low + high) / 2.0


def clopper_pearson(
    failures: int, trials: int, confidence: float = CP_CONFIDENCE
) -> dict[str, float | int]:
    if (
        isinstance(failures, bool)
        or isinstance(trials, bool)
        or not 0 <= failures <= trials
        or trials <= 0
    ):
        raise ValueError("invalid exact-binomial counts")
    alpha = 1.0 - confidence
    lower = (
        0.0 if failures == 0 else _beta_quantile(alpha, failures, trials - failures + 1)
    )
    upper = (
        1.0
        if failures == trials
        else _beta_quantile(confidence, failures + 1, trials - failures)
    )
    return {
        "failures": failures,
        "trials": trials,
        "confidence": confidence,
        "lower": lower,
        "upper": upper,
    }


def _mcnemar_exact(discordant_a: int, discordant_b: int) -> dict[str, int | float]:
    total = discordant_a + discordant_b
    if total == 0:
        return {
            "a_only": discordant_a,
            "b_only": discordant_b,
            "discordant": 0,
            "two_sided_exact_p": 1.0,
        }
    tail = sum(
        math.comb(total, k) for k in range(0, min(discordant_a, discordant_b) + 1)
    ) / (2.0**total)
    return {
        "a_only": discordant_a,
        "b_only": discordant_b,
        "discordant": total,
        "two_sided_exact_p": min(1.0, 2.0 * tail),
    }


def _protected_sources_pass() -> dict[str, object]:
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        ["git", "diff", "--exit-code", BASE_SHA, "--", *D059_PROTECTED_FILES],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "protected source check failed: " + result.stdout + result.stderr
        )
    return {"status": "PASS", "files": list(D059_PROTECTED_FILES), "base": BASE_SHA}


def _horizon_seam_record() -> dict[str, object]:
    rows: list[dict[str, object]] = []
    for room in (3.0, 1.0):
        accepted = d058.D058PhysicalConfig(room)
        extended = _d058_config(room, H_ENDURANCE)
        changed = []
        for item in fields(D045PhysicalConfig):
            name = item.name
            if name == "episode_horizon":
                continue
            if getattr(accepted._base, name) != getattr(extended._base, name):
                changed.append(name)
        rows.append(
            {
                "room_side_m": room,
                "changed_fields_except_episode_horizon": changed,
                "status": "PASS" if not changed else "STOP",
            }
        )
    return {
        "status": "PASS"
        if all(not row["changed_fields_except_episode_horizon"] for row in rows)
        else "STOP",
        "rooms": rows,
        "allowed_difference": "episode_horizon only",
    }


def _record_primary_aggregates(
    records: Sequence[dict[str, object]],
) -> dict[str, object]:
    classifiable = [row for row in records if bool(row["classifiable"])]
    failures = [row for row in classifiable if bool(row["failed"])]
    wall_failures = [row for row in failures if bool(row["wall_exposed_any"])]
    noncontact_failures = [row for row in failures if not bool(row["wall_exposed_any"])]
    outcomes = Counter(cast(str, row["terminal_outcome"]) for row in records)
    cp = (
        clopper_pearson(len(wall_failures), len(classifiable)) if classifiable else None
    )
    return {
        "allocated": len(records),
        "classifiable_N3": len(classifiable),
        "wall_exposed_failures_F3": len(wall_failures),
        "noncontact_failures_G3": len(noncontact_failures),
        "censored": len(records) - len(classifiable),
        "outcome_counts": dict(sorted(outcomes.items())),
        "clopper_pearson_one_sided_95": cp,
        "wall_exposed_failure_seed_ids": [row["seed"] for row in wall_failures],
        "noncontact_failure_seed_ids": [row["seed"] for row in noncontact_failures],
    }


def _decision_branch(
    primary: dict[str, object],
    part_a: Sequence[dict[str, object]],
    secondary: Sequence[dict[str, object]],
) -> tuple[str, str, list[str]]:
    reasons: list[str] = []
    aggregate = _record_primary_aggregates(
        cast(Sequence[dict[str, object]], primary["U_records"])
    )
    cp = cast(
        dict[str, float | int] | None,
        aggregate["clopper_pearson_one_sided_95"],
    )
    if cp is None:
        return "STOP", "STOP", ["no classifiable canonical primary records"]
    lower = float(cast(float, cp["lower"]))
    upper = float(cast(float, cp["upper"]))
    canonical_a = [
        cast(dict[str, object], row["primary"])
        for row in part_a
        if row["substrate"] == "S1_3M" and row["arm"] == "U"
    ]
    targeted_wall = any(bool(row["wall_exposed_failure"]) for row in canonical_a)
    secondary_wall = any(bool(row["wall_exposed_failure"]) for row in secondary)
    secondary_noncontact = any(bool(row["noncontact_failure"]) for row in secondary)
    if lower >= MATERIALITY:
        p_branch = "P_JUSTIFIED"
    elif upper >= MATERIALITY:
        p_branch = "P_UNRESOLVED"
    elif targeted_wall or secondary_wall:
        p_branch = "P_UNRESOLVED"
        if targeted_wall:
            reasons.append("canonical Part-A wall-exposed classifiable failure")
        if secondary_wall:
            reasons.append("canonical secondary wall-exposed classifiable failure")
    else:
        p_branch = "P_NOT_JUSTIFIED"
    if (
        p_branch == "P_NOT_JUSTIFIED"
        and int(cast(int, aggregate["noncontact_failures_G3"])) == 0
        and not any(row["terminal_outcome"] != "DOCKED" for row in canonical_a)
        and not secondary_wall
        and not secondary_noncontact
    ):
        floor = "SETTLED"
    else:
        floor = "NOT_SETTLED"
        if int(cast(int, aggregate["noncontact_failures_G3"])):
            reasons.append("canonical primary non-contact failure")
        if any(row["terminal_outcome"] != "DOCKED" for row in canonical_a):
            reasons.append("canonical Part-A non-dock")
        if secondary_noncontact:
            reasons.append("canonical secondary non-contact failure")
        if secondary_wall:
            reasons.append("canonical secondary wall-exposed failure")
        if p_branch != "P_NOT_JUSTIFIED":
            reasons.append("P branch is not P_NOT_JUSTIFIED")
    return p_branch, floor, sorted(set(reasons))


def _run_endurance_seed(seed: int, substrate: str, arm: str) -> dict[str, object]:
    return _run_lifetime(
        seed,
        substrate=substrate,
        arm=arm,
        horizon=H_ENDURANCE,
        primary_horizon=H_PRIMARY,
        classification_window=W_C,
        initial_battery_fraction=0.80,
    )


def _run_primary_seed(seed: int, arm: str) -> dict[str, object]:
    return _run_lifetime(
        seed,
        substrate="S1_3M",
        arm=arm,
        horizon=H_PRIMARY,
        primary_horizon=H_PRIMARY,
        classification_window=W_C,
        initial_battery_fraction=0.80,
    )


def _run_support_control(seed: int, arm: str) -> dict[str, object]:
    return _run_lifetime(
        seed,
        substrate="D045_1M",
        arm=arm,
        horizon=H_ENDURANCE,
        primary_horizon=H_ENDURANCE,
        classification_window=W_C,
        initial_battery_fraction=0.80,
        continue_full=True,
    )


def _identity_fields(summary: dict[str, object]) -> dict[str, object]:
    return {
        key: value
        for key, value in summary.items()
        if key not in {"causal_digest_sha256", "primary_snapshot_digest_sha256"}
    }


def _load_d056_reference() -> dict[tuple[int, str], dict[str, object]]:
    path = (
        Path(__file__).resolve().parents[2]
        / "development/D-056-v05-multi-cycle-stall-turn-lifetimes.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        (int(row["seed"]), str(row["arm"])): row
        for row in payload["lifetimes"]
        if row["arm"] in {"U", "C"}
    }


def _support_identity(
    support_runs: Sequence[dict[str, object]],
) -> dict[str, object]:
    reference = _load_d056_reference()
    checked: list[dict[str, object]] = []
    for run in support_runs:
        seed = int(cast(int, cast(dict[str, object], run["summary"])["seed"]))
        arm = cast(str, run["arm"])
        ref = reference.get((seed, arm))
        if ref is None:
            raise RuntimeError(f"D-056 reference missing support seed {seed}")
        expected = cast(dict[str, object], ref["summary"])
        actual = cast(dict[str, object], run["summary"])
        if d053._canonicalize(_identity_fields(actual)) != d053._canonicalize(
            _identity_fields(expected)
        ):
            raise RuntimeError(f"D-056 summary identity failed for {arm} seed {seed}")
        checked.append({"seed": seed, "arm": arm, "status": "PASS"})
    return {"status": "PASS", "runs": checked}


def _s1_identity(
    runs: Sequence[dict[str, object]],
) -> dict[str, object]:
    by_seed: dict[int, dict[str, object]] = {}
    for run in runs:
        summary = cast(dict[str, object], run["summary"])
        seed = int(cast(int, summary["seed"]))
        arm = cast(str, run["arm"])
        if arm == "U":
            by_seed[seed] = run
        else:
            u = by_seed.get(seed)
            if u is None or run["causal_digest_sha256"] != u["causal_digest_sha256"]:
                raise RuntimeError(f"C identity failed for S1 seed {seed}")
    return {
        "status": "PASS",
        "checked_runs": len(runs),
        "identity": "C causal digest equals U",
    }


def _protocol_record(jobs: int) -> dict[str, object]:
    return {
        "primary_seeds": list(PRIMARY_SEEDS),
        "endurance_subset": list(ENDURANCE_SEEDS),
        "primary_only": list(PRIMARY_ONLY_SEEDS),
        "test_only": TEST_SEED,
        "support_control": list(SUPPORT_SEEDS),
        "h_primary": H_PRIMARY,
        "return_classification_window": W_C,
        "endurance_horizon": H_ENDURANCE,
        "part_a_horizon": H_PART_A,
        "materiality_threshold": MATERIALITY,
        "confidence": CP_CONFIDENCE,
        "arms": {
            "U": "unchanged D052Controller",
            "C": "unchanged D055StallTurnCandidate",
        },
        "substrates": {
            "S1_3M": "unchanged D058Env room_side_m=3.0",
            "S1_1M": "unchanged D058Env room_side_m=1.0",
            "D045_1M": "unchanged D045Env explicit world [0,1]^2",
        },
        "initial_state": {
            "body_at_station": True,
            "heading_rad": 0.0,
            "initial_battery_fraction": 0.8,
            "initial_battery_j": 0.8 * D045_BATTERY_CAPACITY_J,
            "ambient_temperature": True,
            "charger_termination_latched": False,
        },
        "part_a": {
            "starts_per_substrate": 1248,
            "a1_states": 768,
            "a2_states": 480,
            "clearances_m": [0.0, 0.05],
            "headings": "(2k+1)pi/16, k=0..15 for A1; k*pi/4 for A2",
            "proposal": "zero wheel command",
        },
        "fixture": {
            "mechanism": "unchanged D053RoamingFixture / EXP-001 proposal stream",
            "queried_once_per_decision_including_preempted_decisions": True,
            "organism_observation": "fixed ExternalObservation(0,0,0)",
        },
        "primary_boundary": [
            "DOCKED",
            "SPIN_EXHAUSTED",
            "INVALID_BEACON",
            "TERMINATED_<reason>",
            "RETURN_TIMEOUT_FAILURE",
            "CENSORED_NO_RETURN or CENSORED_IN_PROGRESS at H_PRIMARY",
        ],
        "endurance_seam": {
            "one_continuous_300k_lifetime": True,
            "primary_snapshot_immutable": True,
            "timeout_is_evaluator_only": True,
            "late_first_return_secondary_only": True,
            "primary_exposure_spans_to_primary_boundary": True,
            "secondary_exposure_spans_original_activation_to_secondary_boundary": True,
            "final_100_is_descriptive_only": True,
            "measurement_non_feedback": True,
        },
        "jobs": jobs,
        "pyhashseed": "0",
        "reward": 0.0,
        "organism_info": {},
        "artifact_float_canonicalization": (
            "serialization only: float(Decimal(x).quantize(Decimal('1e-12'), "
            "ROUND_HALF_EVEN)); exact from binary float; normalize -0.0; "
            "reject non-finite"
        ),
    }


def run_protocol(executed_commit_sha: str, *, jobs: int = 1) -> dict[str, object]:
    """Run the complete official D-059 protocol; CLI guard is mandatory."""
    if not _OFFICIAL_CLI_GUARD:
        raise RuntimeError("official D-059 execution is CLI-guarded")
    _validate_sha(executed_commit_sha)
    if os.environ.get("PYTHONHASHSEED") != "0":
        raise RuntimeError("D-059 official execution requires PYTHONHASHSEED=0")
    if jobs <= 0:
        raise ValueError("jobs must be positive")
    # The canonical 3 m endurance runs are also the primary runs for the
    # first 60 seeds.  This is one continuous causal lifetime, not a 140k
    # primary rerun followed by a separate 300k endurance rerun.
    endurance_runs: list[dict[str, object]] = []
    for substrate in ("S1_3M", "S1_1M"):
        endurance_runs.extend(
            _run_ordered(
                lambda item: {
                    "seed": item[0],
                    "substrate": item[1],
                    "arm": item[2],
                    **_run_endurance_seed(item[0], item[1], item[2]),
                },
                [
                    (seed, substrate, arm)
                    for seed in ENDURANCE_SEEDS
                    for arm in ("U", "C")
                ],
                jobs,
            )
        )
    canonical_endurance = [run for run in endurance_runs if run["substrate"] == "S1_3M"]
    primary_only_runs = _run_ordered(
        lambda item: {
            "seed": item[0],
            "arm": item[1],
            "substrate": "S1_3M",
            **_run_primary_seed(item[0], item[1]),
        },
        [(seed, arm) for seed in PRIMARY_ONLY_SEEDS for arm in ("U", "C")],
        jobs,
    )
    primary_runs = [*canonical_endurance, *primary_only_runs]
    support_runs = _run_ordered(
        lambda item: {
            "seed": item[0],
            "substrate": "D045_1M",
            "arm": item[1],
            **_run_support_control(item[0], item[1]),
        },
        [(seed, arm) for seed in SUPPORT_SEEDS for arm in ("U", "C")],
        jobs,
    )
    part_a_jobs: list[tuple[D059Start, str, str]] = []
    for substrate in ("S1_3M", "S1_1M", "D045_1M"):
        starts = part_a_starts(3.0 if substrate == "S1_3M" else 1.0)
        part_a_jobs.extend(
            (start, substrate, arm) for start in starts for arm in ("U", "C")
        )
    part_a_runs = _run_ordered(lambda item: run_part_a_case(*item), part_a_jobs, jobs)

    primary_u = [
        cast(dict[str, object], run["primary"])
        for run in primary_runs
        if run["arm"] == "U"
    ]
    primary_c = [
        cast(dict[str, object], run["primary"])
        for run in primary_runs
        if run["arm"] == "C"
    ]
    primary_records: dict[str, object] = {
        "U_records": primary_u,
        "C_records": primary_c,
    }
    s1_endurance = [run for run in endurance_runs if run["substrate"] == "S1_3M"]
    s1_secondary = [
        episode
        for run in s1_endurance
        for episode in cast(list[dict[str, object]], run["episodes"])
    ]
    part_a_aggregate = {
        substrate: {
            arm: _record_primary_aggregates(
                [
                    cast(dict[str, object], row["primary"])
                    for row in part_a_runs
                    if row["substrate"] == substrate and row["arm"] == arm
                ]
            )
            for arm in ("U", "C")
        }
        for substrate in ("S1_3M", "S1_1M", "D045_1M")
    }
    p_branch, floor, floor_reasons = _decision_branch(
        primary_records,
        part_a_runs,
        s1_secondary,
    )
    s1_1m_failures = [
        row["primary"]
        for row in part_a_runs
        if row["substrate"] == "S1_1M"
        and row["arm"] == "U"
        and cast(dict[str, object], row["primary"])["terminal_outcome"] != "DOCKED"
    ]
    if s1_1m_failures:
        s1_alert = "S1_1M_ALERT"
    else:
        s1_alert = "NONE"

    attribution: dict[str, object] = {}
    for substrate, label in (("S1_1M", "S1_1M"), ("D045_1M", "D045_1M")):
        by_seed = {
            int(cast(int, cast(dict[str, object], run["primary"])["seed"])): cast(
                dict[str, object], run["primary"]
            )
            for run in endurance_runs
            if run["substrate"] == substrate and run["arm"] == "U"
        }
        attribution[label] = by_seed
    s1_by_seed = cast(dict[int, dict[str, object]], attribution["S1_1M"])
    d045_by_seed = cast(dict[int, dict[str, object]], attribution["D045_1M"])
    first_cross: Counter[str] = Counter()
    lifetime_cross: Counter[str] = Counter()
    d045_only = s1_only = 0
    for seed in ENDURANCE_SEEDS:
        sr = s1_by_seed[seed]
        dr = d045_by_seed[seed]
        sf, df = _first_return_failure(sr), _first_return_failure(dr)
        first_cross[f"S1_1M_{sf}_x_D045_1M_{df}"] += 1
        if sf is True and df is False:
            s1_only += 1
        if sf is False and df is True:
            d045_only += 1
        s1_life = any(
            bool(ep["failed"])
            for run in endurance_runs
            if run["substrate"] == "S1_1M"
            and run["arm"] == "U"
            and int(cast(int, run["seed"])) == seed
            for ep in cast(list[dict[str, object]], run["episodes"])
        )
        d_life = any(
            bool(ep["failed"])
            for run in endurance_runs
            if run["substrate"] == "D045_1M"
            and run["arm"] == "U"
            and int(cast(int, run["seed"])) == seed
            for ep in cast(list[dict[str, object]], run["episodes"])
        )
        lifetime_cross[f"S1_1M_{s1_life}_x_D045_1M_{d_life}"] += 1
    attribution["matched_first_return_cross_tab"] = dict(sorted(first_cross.items()))
    attribution["matched_lifetime_any_failure_cross_tab"] = dict(
        sorted(lifetime_cross.items())
    )
    attribution["first_return_mcnemar_two_sided_exact"] = _mcnemar_exact(
        s1_only, d045_only
    )

    _s1_identity(
        [run for run in endurance_runs if run["substrate"] in {"S1_3M", "S1_1M"}]
    )
    protected = _protected_sources_pass()
    seam = _horizon_seam_record()
    support_identity = _support_identity(support_runs)
    primary_measurement_control = {
        "status": "PASS",
        "method": (
            "online snapshot is read-only; bounded test-only measurement-on/off "
            "causal digest equality is test-enforced"
        ),
        "primary_snapshot_is_diagnostic_not_organism_event": True,
        "timeout_does_not_stop_endurance": True,
        "primary_censor_does_not_change_primary_label": True,
    }
    controls = {
        "protected_sources": protected,
        "horizon_seam": seam,
        "d045_1m_support_identity": support_identity,
        "primary_snapshot_non_feedback": primary_measurement_control,
        "s1_c_identity": "PASS (C causal digest equals U on every S1 run)",
        "part_a_legality": {"status": "PASS", "starts_per_substrate": 1248},
        "seed_guards": {
            "primary": list(validate_primary_seeds(PRIMARY_SEEDS)),
            "endurance": list(validate_endurance_seeds(ENDURANCE_SEEDS)),
            "primary_only": list(validate_primary_only_seeds(PRIMARY_ONLY_SEEDS)),
            "support": list(validate_support_seeds(SUPPORT_SEEDS)),
            "test_only": TEST_SEED,
            "superseded_v1_block": "22700-22760 unexecuted",
        },
        "information_boundary": {
            "reward_exactly_zero": all(
                bool(cast(dict[str, object], run["summary"])["reward_exactly_zero"])
                for run in [*primary_runs, *endurance_runs, *support_runs]
            ),
            "organism_info_exactly_empty": all(
                bool(
                    cast(dict[str, object], run["summary"])[
                        "organism_info_exactly_empty"
                    ]
                )
                for run in [*primary_runs, *endurance_runs, *support_runs]
            ),
            "evaluator_geometry_to_controller": False,
        },
        "determinism": {
            "status": "PASS",
            "pyhashseed": "0",
            "declared_order": True,
            "sorted_aggregation": True,
        },
        "classification_integrity": {
            "primary_and_secondary_not_pooled": True,
            "censored_not_failures": True,
            "wall_exposure_orthogonal_to_terminal_outcome": True,
            "final_100_descriptive_only": True,
        },
    }
    endurance_artifact = [
        {
            "seed": run["seed"],
            "substrate": run["substrate"],
            "arm": run["arm"],
            "primary": run["primary"],
            "secondary_episodes": run["episodes"],
            "summary": run["summary"],
            "causal_digest_sha256": run["causal_digest_sha256"],
            "primary_snapshot_digest_sha256": run["primary_snapshot_digest_sha256"],
        }
        for run in endurance_runs
    ]
    return {
        "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
        "schema_version": "d059-artifact-v1",
        "development_id": D059_ID,
        "protocol_version": PROTOCOL_VERSION,
        "authorized_base_sha": BASE_SHA,
        "executed_commit_sha": executed_commit_sha,
        "protocol_sha": executed_commit_sha,
        "result_kind": "descriptive_development_rebaseline",
        "claims_boundary": (
            "Development characterization only; no confirmatory claim, P promotion, "
            "ADR amendment, S2, learning or visualizer."
        ),
        "execution_status": "COMPLETED",
        "frozen_protocol": _protocol_record(jobs),
        "pre_freeze_exposure": {
            "official_seeds_executed_before_freeze": False,
            "test_only_seed": TEST_SEED,
            "test_only_runs_bounded": True,
            "construction_only_checks_before_freeze": True,
            "v1_seed_block_22700_22760": "superseded and unexecuted",
        },
        "invalidated_candidate_provenance": [],
        "validation": controls,
        "primary": {
            "U": primary_u,
            "C": primary_c,
            "aggregates_U": _record_primary_aggregates(primary_u),
            "aggregates_C": _record_primary_aggregates(primary_c),
        },
        "endurance": endurance_artifact,
        "support_control": [
            {
                "seed": run["seed"],
                "arm": run["arm"],
                "summary": run["summary"],
                "primary": run["primary"],
                "secondary_episodes": run["episodes"],
                "causal_digest_sha256": run["causal_digest_sha256"],
            }
            for run in support_runs
        ],
        "part_a": {
            "runs": part_a_runs,
            "aggregates": part_a_aggregate,
            "run_count": len(part_a_runs),
        },
        "attribution": attribution,
        "decision": {
            "P_BRANCH": p_branch,
            "FLOOR_S1_3M": floor,
            "FLOOR_S1_3M_reasons": floor_reasons,
            "S1_1M_ALERT": s1_alert,
            "P_scope": "canonical S1_3M only",
            "materiality_is_operational_development_trigger_only": True,
            "C_structural_dormancy": (
                "C≡U on S1; no D-055 stall detection is interpreted as evidence"
            ),
        },
        "discrete_signature": {
            "N3": _record_primary_aggregates(primary_u)["classifiable_N3"],
            "F3": _record_primary_aggregates(primary_u)["wall_exposed_failures_F3"],
            "G3": _record_primary_aggregates(primary_u)["noncontact_failures_G3"],
            "P_BRANCH": p_branch,
            "FLOOR_S1_3M": floor,
            "S1_1M_ALERT": s1_alert,
        },
    }


def _canonicalize(value: object) -> object:
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite artifact float")
        rounded = float(
            Decimal(value).quantize(ARTIFACT_FLOAT_QUANTUM, rounding=ROUND_HALF_EVEN)
        )
        return 0.0 if rounded == 0.0 else rounded
    if isinstance(value, dict):
        return {key: _canonicalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    return value


def write_artifact(path: Path, executed_commit_sha: str, *, jobs: int = 1) -> Path:
    if not _OFFICIAL_CLI_GUARD:
        raise RuntimeError("official D-059 artifact generation is CLI-guarded")
    payload = _canonicalize(run_protocol(executed_commit_sha, jobs=jobs))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return path


def main(argv: Sequence[str] | None = None) -> int:
    global _OFFICIAL_CLI_GUARD
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--executed-commit-sha", required=True)
    parser.add_argument("--jobs", type=int, default=1)
    args = parser.parse_args(argv)
    if os.environ.get("PYTHONHASHSEED") != "0":
        raise SystemExit("D-059 requires PYTHONHASHSEED=0")
    _OFFICIAL_CLI_GUARD = True
    write_artifact(args.output, args.executed_commit_sha, jobs=args.jobs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
