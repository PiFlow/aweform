"""D-042 founder-selected fine-turn and front-contact embodiment.

This module is deliberately isolated from the historical D-024 through D-041
modules.  It reuses the current D-030 learned SEEK steering organism over the
unchanged D-026 controller and D-027 learner, while supplying only the
accepted D-042 action/contact embodiment.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import replace
from pathlib import Path
from typing import Final, Sequence, cast

import numpy as np

from . import d025, d026, d027, d030
from .body import Coordinate
from .d020 import D020PhysicalConfig
from .env import Action
from .exp003 import EXP003_B50_ENTER_SEEK_THRESHOLD
from .exp003_seed_policy import validate_exp003_development_seeds
from .rng import RandomStreams

D042_AUTHORITATIVE_BASE_SHA: Final[str] = (
    "ad0fa81083d37cd3976e77777ffe22a04b965d59"
)
D042_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = (19042, 19043, 19044)
D042_HORIZON: Final[int] = 70_000
D042_DT_SECONDS: Final[float] = 0.1
D042_TURN_ANGLE: Final[float] = math.pi / 36.0
D042_TURN_ANGLE_DEGREES: Final[float] = 5.0
D042_BODY_LENGTH: Final[float] = 0.10
D042_BODY_WIDTH: Final[float] = 0.08
D042_FRONT_X: Final[float] = 0.05
D042_CONTACT_LATERAL_OFFSET: Final[float] = 0.025
D042_DOCK_ORIENTATION: Final[float] = 0.0
D042_CONTACT_TOLERANCE: Final[float] = 0.01
D042_STATION_CENTER: Final[Coordinate] = (0.50, 0.50)
D042_INITIAL_BODY_CENTER: Final[Coordinate] = (0.45, 0.50)
D042_INITIAL_HEADING: Final[float] = 0.0
D042_INITIAL_BATTERY_J: Final[float] = 5328.0
D042_INITIAL_TEMPERATURE_C: Final[float] = 23.0


def _rotate(offset: Coordinate, heading: float) -> Coordinate:
    cosine = math.cos(heading)
    sine = math.sin(heading)
    return (
        offset[0] * cosine - offset[1] * sine,
        offset[0] * sine + offset[1] * cosine,
    )


def _translate(origin: Coordinate, offset: Coordinate) -> Coordinate:
    return (origin[0] + offset[0], origin[1] + offset[1])


def body_front_contacts_world(
    body_center: Coordinate, body_heading: float
) -> tuple[Coordinate, Coordinate]:
    """Return corresponding front-plus and front-minus body contacts."""
    return (
        _translate(
            body_center,
            _rotate((D042_FRONT_X, D042_CONTACT_LATERAL_OFFSET), body_heading),
        ),
        _translate(
            body_center,
            _rotate((D042_FRONT_X, -D042_CONTACT_LATERAL_OFFSET), body_heading),
        ),
    )


def dock_contacts_world(
    station_center: Coordinate,
) -> tuple[Coordinate, Coordinate]:
    """Return fixed corresponding dock contacts at ``phi == 0``."""
    return (
        _translate(
            station_center,
            _rotate((0.0, D042_CONTACT_LATERAL_OFFSET), D042_DOCK_ORIENTATION),
        ),
        _translate(
            station_center,
            _rotate((0.0, -D042_CONTACT_LATERAL_OFFSET), D042_DOCK_ORIENTATION),
        ),
    )


def dual_contact_pair_errors(
    body_center: Coordinate,
    body_heading: float,
    station_center: Coordinate,
) -> tuple[float, float]:
    """Return corresponding plus/plus and minus/minus Euclidean errors."""
    body_plus, body_minus = body_front_contacts_world(body_center, body_heading)
    dock_plus, dock_minus = dock_contacts_world(station_center)
    return math.dist(body_plus, dock_plus), math.dist(body_minus, dock_minus)


def _within_contact_tolerance(error: float) -> bool:
    """Apply the literal inclusive contact tolerance."""
    return error <= D042_CONTACT_TOLERANCE


def has_dual_contact(
    body_center: Coordinate,
    body_heading: float,
    station_center: Coordinate,
) -> bool:
    """Return true only for both corresponding front contact pairs."""
    plus_error, minus_error = dual_contact_pair_errors(
        body_center, body_heading, station_center
    )
    return _within_contact_tolerance(plus_error) and _within_contact_tolerance(
        minus_error
    )


def _canonical_config(horizon: int) -> D020PhysicalConfig:
    return replace(
        D020PhysicalConfig(),
        turn_angle=D042_TURN_ANGLE,
        episode_horizon=horizon,
    )


class D042Env(d026.D026Env):
    """Current canonical organism environment with D-042 contact geometry."""

    def __init__(self, config: D020PhysicalConfig | None = None) -> None:
        super().__init__(config or _canonical_config(D042_HORIZON))

    @property
    def charging_contact(self) -> bool:
        if self.body is None or self.station_center is None:
            raise RuntimeError("environment must be reset before observing")
        return has_dual_contact(
            self.body.position,
            self.body.heading,
            self.station_center,
        )


def _validate_d042_seed(seed: int) -> None:
    validate_exp003_development_seeds((seed,))


def _validate_executed_commit_sha(value: str | None) -> str | None:
    if value is None:
        return None
    if re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise ValueError("executed_commit_sha must be a 40-character lowercase SHA")
    return value


def _controller_observation(observation: np.ndarray) -> d027.D027Observation:
    """Use the unchanged D-021/D-030 six-channel projection."""
    return d025._controller_observation(observation)


def _initial_environment(
    seed: int, horizon: int
) -> tuple[D042Env, np.ndarray, RandomStreams]:
    _validate_d042_seed(seed)
    environment = D042Env(_canonical_config(horizon))
    streams = RandomStreams.from_seed(seed)
    observation, info = environment.reset(
        options={
            "body_position": D042_INITIAL_BODY_CENTER,
            "station_center": D042_STATION_CENTER,
            "heading": D042_INITIAL_HEADING,
            "battery_j": D042_INITIAL_BATTERY_J,
            "body_temperature_c": D042_INITIAL_TEMPERATURE_C,
            "charger_termination_latched": False,
        }
    )
    if info != {}:
        raise RuntimeError("D-042 reset crossed the information boundary")
    if not environment.charging_contact:
        raise RuntimeError("D-042 exact initial pose is not in dual contact")
    return environment, observation, streams


def _termination_reason(
    environment: D042Env, terminated: bool, truncated: bool
) -> str:
    return d027._termination_reason(environment, terminated, truncated)


def _run_d042_seed(seed: int, *, horizon: int = D042_HORIZON) -> dict[str, object]:
    """Run one deterministic canonical D-042 lifetime without retaining a trace."""
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon <= 0:
        raise ValueError("horizon must be a positive integer")
    environment, observation_array, streams = _initial_environment(seed, horizon)
    controller = d026.D026Controller(streams.policy)
    controller.reset()
    learner = d027.D027ActionConsequencePredictor()
    current = _controller_observation(observation_array)

    action_counts = {action.name: 0 for action in Action}
    mode_occupancy = {mode.name: 0 for mode in d026.D026Mode}
    mode_entry_counts = {mode.name: 0 for mode in d026.D026Mode}
    mode_entry_counts[controller.mode.name] = 1
    turn_count = 0
    signed_turns = 0
    absolute_turns = 0
    turn_energy_j = 0.0
    contact_entries = 0
    contact_exits = 0
    seek_entries = 0
    physical_reacquisitions = 0
    full_recharge_events = 0
    post_recharge_redepartures = 0
    active_seek = False
    recharge_active = False
    recharge_ready = False
    initial_energy = current.energy
    initial_temperature = current.thermal
    minimum_energy = maximum_energy = current.energy
    minimum_temperature = maximum_temperature = current.thermal
    maximum_temperature_c = D042_INITIAL_TEMPERATURE_C
    transitions = 0
    terminated = False
    truncated = False

    while not (terminated or truncated):
        mode_before = controller.mode
        mode_occupancy[mode_before.name] += 1
        historical_action = controller.act(current)
        mode_after = controller.mode
        if mode_after is not mode_before:
            mode_entry_counts[mode_after.name] += 1

        # This is the unchanged D-030 LEARNED_FORWARD arbitration.  The
        # evaluator queries predictions only where D-030 does; only the
        # selected action is then executed and learned from.
        action = historical_action
        arbitration = controller.last_arbitration
        if arbitration is not None and not arbitration.delegated:
            predictions, read_only = d030._query_candidate_predictions(
                learner, current
            )
            if not read_only:
                raise RuntimeError("D-030 prediction query mutated learner state")
            action = d030._choose_steering_action(
                current, predictions, arbitration.greedy_action
            )

        action_counts[action.name] += 1
        if action is Action.TURN_LEFT:
            turn_count += 1
            signed_turns += 1
            absolute_turns += 1
        elif action is Action.TURN_RIGHT:
            turn_count += 1
            signed_turns -= 1
            absolute_turns += 1

        observation_array, reward, terminated, truncated, info = environment.step(
            action
        )
        if reward != 0.0 or info != {}:
            raise RuntimeError("D-042 transition crossed the reward/info boundary")
        telemetry = environment.last_transition
        if telemetry is None:
            raise RuntimeError("D-042 transition telemetry is unavailable")
        if action in (Action.TURN_LEFT, Action.TURN_RIGHT):
            turn_energy_j += (
                telemetry.actuator_electrical_power_w
                * environment.config.dt_seconds
            )
        next_observation = _controller_observation(observation_array)
        update = learner.observe_transition(current, action, next_observation)
        if update.action is not action:
            raise RuntimeError("D-027 learner update did not use executed action")

        transitions += 1
        if not telemetry.charging_contact_before and telemetry.charging_contact_after:
            contact_entries += 1
        if telemetry.charging_contact_before and not telemetry.charging_contact_after:
            contact_exits += 1
        entered_seek = (
            mode_before is d026.D026Mode.AWAY
            and mode_after is d026.D026Mode.SEEK
            and current.energy < EXP003_B50_ENTER_SEEK_THRESHOLD
        )
        if entered_seek:
            seek_entries += 1
            active_seek = True
        if active_seek and (
            not telemetry.charging_contact_before and telemetry.charging_contact_after
        ):
            active_seek = False
            physical_reacquisitions += 1
            recharge_active = True
        if (
            recharge_active
            and telemetry.battery_after_j >= environment.config.battery_capacity_j
            and telemetry.charger_termination_latched_after
        ):
            recharge_active = False
            recharge_ready = True
            full_recharge_events += 1
        if (
            mode_before is d026.D026Mode.CHARGE
            and mode_after is d026.D026Mode.DEPART
        ):
            if recharge_ready:
                post_recharge_redepartures += 1
                recharge_ready = False

        minimum_energy = min(minimum_energy, next_observation.energy)
        maximum_energy = max(maximum_energy, next_observation.energy)
        minimum_temperature = min(minimum_temperature, next_observation.thermal)
        maximum_temperature = max(maximum_temperature, next_observation.thermal)
        maximum_temperature_c = max(
            maximum_temperature_c, telemetry.body_temperature_after_c
        )
        current = next_observation

    if environment.last_transition is None:
        raise RuntimeError("D-042 lifetime produced no transition")
    termination_reason = _termination_reason(environment, terminated, truncated)
    if physical_reacquisitions:
        outcome = "SEEK_REACQUIRED"
    elif truncated:
        outcome = "HORIZON_CENSORED"
    else:
        outcome = "FAILED_SEEK" if seek_entries else "INITIAL_LIFETIME_ONLY"
    return {
        "seed": seed,
        "transitions": transitions,
        "physical_seconds": transitions * environment.config.dt_seconds,
        "terminated": terminated,
        "truncated": truncated,
        "termination_reason": termination_reason,
        "outcome": outcome,
        "action_counts": action_counts,
        "mode_occupancy": mode_occupancy,
        "mode_entry_counts": mode_entry_counts,
        "initial_dual_contact": True,
        "contact_entries": contact_entries,
        "contact_exits": contact_exits,
        "low_energy_seek_entries": seek_entries,
        "physical_reacquisitions": physical_reacquisitions,
        "full_recharge_events": full_recharge_events,
        "post_recharge_redepartures": post_recharge_redepartures,
        "turns": {
            "count": turn_count,
            "signed_count": signed_turns,
            "absolute_count": absolute_turns,
            "commanded_signed_angle_radians": signed_turns * D042_TURN_ANGLE,
            "commanded_absolute_angle_radians": absolute_turns * D042_TURN_ANGLE,
            "electrical_energy_j": turn_energy_j,
            "timestep_seconds": turn_count * environment.config.dt_seconds,
        },
        "battery_normalized": {
            "start": initial_energy,
            "minimum": minimum_energy,
            "final": current.energy,
            "maximum": maximum_energy,
        },
        "temperature_normalized": {
            "start": initial_temperature,
            "minimum": minimum_temperature,
            "final": current.thermal,
            "maximum": maximum_temperature,
        },
        "max_body_temperature_c": maximum_temperature_c,
    }


def _aggregate(results: Sequence[dict[str, object]]) -> dict[str, object]:
    return {
        "lifetime_count": len(results),
        "outcome_counts": {
            outcome: sum(int(result["outcome"] == outcome) for result in results)
            for outcome in (
                "SEEK_REACQUIRED",
                "HORIZON_CENSORED",
                "FAILED_SEEK",
                "INITIAL_LIFETIME_ONLY",
            )
        },
        "total_transitions": sum(
            cast(int, result["transitions"]) for result in results
        ),
        "total_contact_entries": sum(
            cast(int, result["contact_entries"]) for result in results
        ),
        "total_physical_reacquisitions": sum(
            cast(int, result["physical_reacquisitions"]) for result in results
        ),
        "total_full_recharge_events": sum(
            cast(int, result["full_recharge_events"]) for result in results
        ),
        "termination_reason_counts": {
            reason: sum(
                int(result["termination_reason"] == reason) for result in results
            )
            for reason in (
                "energy_depletion",
                "protective_thermal_shutdown",
                "emergency_hard_thermal_shutdown",
                "horizon_truncation",
            )
        },
    }


def run_d042_probe(
    seeds: Sequence[int] = D042_DEFAULT_DEVELOPMENT_SEEDS,
    *,
    horizon: int = D042_HORIZON,
    executed_commit_sha: str | None = None,
) -> dict[str, object]:
    """Run the compact, predeclared D-042 Development characterization."""
    validated_seeds = validate_exp003_development_seeds(seeds)
    if tuple(validated_seeds) != D042_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-042 characterization requires exactly the declared seeds "
            f"{D042_DEFAULT_DEVELOPMENT_SEEDS}; got {validated_seeds}"
        )
    if horizon != D042_HORIZON:
        raise ValueError("D-042 characterization requires the frozen horizon")
    executed_sha = _validate_executed_commit_sha(executed_commit_sha)
    results = [_run_d042_seed(seed, horizon=horizon) for seed in validated_seeds]
    return {
        "schema_version": 1,
        "experiment": "D-042",
        "title": "Founder-selected fine-turn and front dual-contact baseline",
        "authoritative_base_sha": D042_AUTHORITATIVE_BASE_SHA,
        "implementation_probe_sha": executed_sha,
        "development_seeds": list(validated_seeds),
        "horizon": horizon,
        "timestep_seconds": D042_DT_SECONDS,
        "lifetime": "one uninterrupted causal lifetime per seed",
        "seed_policy": {
            "canonical_validator": "validate_exp003_development_seeds",
            "formal_reservation_guard_preserved": True,
            "formal_reserved_ranges_excluded": True,
        },
        "embodiment": {
            "turn_angle_radians": D042_TURN_ANGLE,
            "turn_angle_degrees": D042_TURN_ANGLE_DEGREES,
            "turn_angle_expression": "pi / 36",
            "turn_action_seconds": D042_DT_SECONDS,
            "turn_actuator_electrical_power_w": 0.65,
            "body_length": D042_BODY_LENGTH,
            "body_width": D042_BODY_WIDTH,
            "body_front_contacts_body_frame": [
                [D042_FRONT_X, D042_CONTACT_LATERAL_OFFSET],
                [D042_FRONT_X, -D042_CONTACT_LATERAL_OFFSET],
            ],
            "dock_orientation": D042_DOCK_ORIENTATION,
            "dock_contacts_station_offsets": [
                [0.0, D042_CONTACT_LATERAL_OFFSET],
                [0.0, -D042_CONTACT_LATERAL_OFFSET],
            ],
            "contact_tolerance_inclusive": D042_CONTACT_TOLERANCE,
            "initial_station_center": list(D042_STATION_CENTER),
            "initial_body_center": list(D042_INITIAL_BODY_CENTER),
            "initial_heading": D042_INITIAL_HEADING,
        },
        "canonical_organism": {
            "controller": "unchanged d026.D026Controller / D-030 semantics",
            "learner": "unchanged d027.D027ActionConsequencePredictor",
            "steering": "unchanged D-030 LEARNED_FORWARD action arbitration",
            "de_trap": "unchanged D-026 delegation and explorer streams",
            "actions": [action.name for action in Action],
            "visible_channels": list(d027.D027_CHANNELS),
            "reward": 0.0,
            "info": {},
        },
        "historical_protection": {
            "historical_d024_through_d041_modules_untouched": True,
            "d041_receptors_exposed": False,
            "historical_d020_default_turn_preserved": True,
        },
        "organism_boundary": {
            "coordinates_heading_and_contact_errors_visible": False,
            "evaluator_only_geometry": True,
        },
        "results": results,
        "aggregate": _aggregate(results),
        "interpretation": (
            "Descriptive Development characterization only; embodiment choice "
            "is separated from observed canonical-organism behaviour."
        ),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--executed-commit-sha", required=True)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    artifact = run_d042_probe(executed_commit_sha=args.executed_commit_sha)
    args.output.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
