"""D-044 evaluator-only homing, docking, and cycle-order audit.

The real lifetime in this module is the accepted D-043 lifetime.  Diagnostics
are collected around the unchanged D-026/D-030/D-027 decision and canonical
D-042 transition.  Geometry, beacon reconstruction, and counterfactual
branches are evaluator-only and are never supplied to the organism.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final, Sequence, cast

import numpy as np

from . import d016, d025, d026, d027, d029, d030, d042, d043
from .env import Action
from .exp003 import EXP003_B50_ENTER_SEEK_THRESHOLD

D044_AUTHORITATIVE_BASE_SHA: Final[str] = "26ef630b23af01028971cadbddbd38e79d562610"
D044_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = tuple(range(19045, 19065))
D044_HORIZON: Final[int] = 140_000
D044_FORWARD_CANDIDATES: Final[tuple[float, ...]] = (0.05, 0.01, 0.005)
D044_MAX_EXEMPLARS: Final[int] = 3


@dataclass(slots=True)
class _Distribution:
    """Compact online distribution summary; no per-transition log is kept."""

    count: int = 0
    total: float = 0.0
    minimum: float | None = None
    maximum: float | None = None
    negative: int = 0
    zero: int = 0
    positive: int = 0

    def add(self, value: float) -> None:
        self.count += 1
        self.total += value
        self.minimum = value if self.minimum is None else min(self.minimum, value)
        self.maximum = value if self.maximum is None else max(self.maximum, value)
        if value < 0.0:
            self.negative += 1
        elif value > 0.0:
            self.positive += 1
        else:
            self.zero += 1

    def as_dict(self) -> dict[str, object]:
        return {
            "count": self.count,
            "mean": self.total / self.count if self.count else None,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "negative": self.negative,
            "zero": self.zero,
            "positive": self.positive,
            "interpretation": "negative means improvement for the measured error",
        }


@dataclass(slots=True)
class _BranchSummary:
    count: int = 0
    accepted_contact: int = 0
    clipped: int = 0
    stalled: int = 0
    station_distance_change: _Distribution = field(default_factory=_Distribution)
    max_pair_error_change: _Distribution = field(default_factory=_Distribution)
    resulting_station_distance: _Distribution = field(default_factory=_Distribution)
    nominal_target_error: _Distribution = field(default_factory=_Distribution)
    resulting_front_plus_pair_error: _Distribution = field(
        default_factory=_Distribution
    )
    resulting_front_minus_pair_error: _Distribution = field(
        default_factory=_Distribution
    )
    resulting_max_pair_error: _Distribution = field(default_factory=_Distribution)

    def add(
        self,
        *,
        station_distance_change: float,
        max_pair_error_change: float,
        resulting_station_distance: float,
        nominal_target_error: float,
        resulting_front_plus_pair_error: float,
        resulting_front_minus_pair_error: float,
        resulting_max_pair_error: float,
        accepted_contact: bool,
        clipped: bool = False,
        stalled: bool = False,
    ) -> None:
        self.count += 1
        self.accepted_contact += int(accepted_contact)
        self.clipped += int(clipped)
        self.stalled += int(stalled)
        self.station_distance_change.add(station_distance_change)
        self.max_pair_error_change.add(max_pair_error_change)
        self.resulting_station_distance.add(resulting_station_distance)
        self.nominal_target_error.add(nominal_target_error)
        self.resulting_front_plus_pair_error.add(resulting_front_plus_pair_error)
        self.resulting_front_minus_pair_error.add(resulting_front_minus_pair_error)
        self.resulting_max_pair_error.add(resulting_max_pair_error)

    def as_dict(self) -> dict[str, object]:
        return {
            "count": self.count,
            "accepted_dual_contact_count": self.accepted_contact,
            "world_boundary_clipped_count": self.clipped,
            "world_boundary_stall_count": self.stalled,
            "station_distance_change": self.station_distance_change.as_dict(),
            "max_pair_error_change": self.max_pair_error_change.as_dict(),
            "resulting_station_distance": self.resulting_station_distance.as_dict(),
            "resulting_nominal_target_error": self.nominal_target_error.as_dict(),
            "resulting_front_plus_pair_error": (
                self.resulting_front_plus_pair_error.as_dict()
            ),
            "resulting_front_minus_pair_error": (
                self.resulting_front_minus_pair_error.as_dict()
            ),
            "resulting_max_pair_error": self.resulting_max_pair_error.as_dict(),
        }


@dataclass(slots=True)
class _InformationAudit:
    x: _Distribution = field(default_factory=_Distribution)
    y: _Distribution = field(default_factory=_Distribution)
    radial: _Distribution = field(default_factory=_Distribution)

    def add(
        self, decoded: d016.RelativeGeometry, actual: d016.RelativeGeometry
    ) -> None:
        self.x.add(abs(decoded.x - actual.x))
        self.y.add(abs(decoded.y - actual.y))
        self.radial.add(abs(decoded.radial_distance - actual.radial_distance))

    def as_dict(self) -> dict[str, object]:
        return {
            "sample_count": self.radial.count,
            "absolute_error": {
                "x_rel": self.x.as_dict(),
                "y_rel": self.y.as_dict(),
                "radial_distance": self.radial.as_dict(),
            },
            "decoder": "D-016 analytic inverse of current float32 L/F/R only",
            "causal": False,
        }


def _seed_guard(seeds: Sequence[int]) -> tuple[int, ...]:
    validated = d043._validate_seeds(seeds)
    if validated != D044_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-044 requires exactly the declared D-043 support "
            f"{D044_DEFAULT_DEVELOPMENT_SEEDS}; got {validated}"
        )
    return validated


def _distance(left: tuple[float, float], right: tuple[float, float]) -> float:
    return math.dist(left, right)


def _wrapped_heading_error(heading: float) -> float:
    return abs(math.atan2(math.sin(heading), math.cos(heading)))


def _geometry(
    position: tuple[float, float],
    heading: float,
    station: tuple[float, float],
) -> dict[str, float | bool]:
    plus, minus = d042.dual_contact_pair_errors(position, heading, station)
    target = (station[0] - d042.D042_FRONT_X, station[1])
    return {
        "station_distance": _distance(position, station),
        "nominal_target_center_error": _distance(position, target),
        "heading_error": _wrapped_heading_error(heading),
        "front_plus_pair_error": plus,
        "front_minus_pair_error": minus,
        "max_pair_error": max(plus, minus),
        "accepted_dual_contact": d042.has_dual_contact(position, heading, station),
    }


def _state_record(
    *,
    transition: int,
    state_kind: str,
    action: Action,
    energy: float,
    thermal: float,
    position: tuple[float, float],
    heading: float,
    station: tuple[float, float],
    observation: d027.D027Observation,
) -> dict[str, object]:
    metrics = _geometry(position, heading, station)
    return {
        "transition": transition,
        "state_kind": state_kind,
        "action": action.name,
        "energy": energy,
        "temperature_normalized": thermal,
        "body_center": list(position),
        "heading": heading,
        **metrics,
        "beacon": {
            "left": observation.beacon.left,
            "forward": observation.beacon.forward,
            "right": observation.beacon.right,
        },
    }


def _stratum(distance: float, pair_error: float) -> str:
    distance_band = (
        "<0.05" if distance < 0.05 else "0.05-0.10" if distance < 0.10 else ">=0.10"
    )
    pair_band = (
        "<0.01" if pair_error < 0.01 else "0.01-0.05" if pair_error < 0.05 else ">=0.05"
    )
    return f"station_distance:{distance_band}|max_pair_error:{pair_band}"


def _empty_source_counts() -> dict[str, int]:
    return {action.name: 0 for action in Action}


def _new_episode(
    *,
    transition: int,
    action: Action,
    energy: float,
    thermal: float,
    position: tuple[float, float],
    heading: float,
    station: tuple[float, float],
    observation: d027.D027Observation,
) -> dict[str, object]:
    entry = _state_record(
        transition=transition,
        state_kind="pre_action_entry",
        action=action,
        energy=energy,
        thermal=thermal,
        position=position,
        heading=heading,
        station=station,
        observation=observation,
    )
    return {
        "seek_entry_transition": transition,
        "seek_entry_physical_seconds": transition * d042.D042_DT_SECONDS,
        "entry_action": action.name,
        "energy_at_entry": energy,
        "temperature_normalized_at_entry": thermal,
        "entry_station_distance": entry["station_distance"],
        "entry_nominal_target_center_error": entry["nominal_target_center_error"],
        "entry_heading_error": entry["heading_error"],
        "entry_max_pair_error": entry["max_pair_error"],
        "entry_record": entry,
        "minimum_station_distance": entry["station_distance"],
        "minimum_station_distance_record": entry,
        "minimum_max_pair_error": entry["max_pair_error"],
        "minimum_max_pair_error_record": entry,
        "max_pair_error_at_minimum_station_distance": entry["max_pair_error"],
        "final_record": None,
        "reacquisition_record": None,
        "action_counts_by_source": {
            "d026_delegated_stochastic": 0,
            "d030_learned_selected": 0,
        },
        "selected_action_counts_by_source": {
            "d026_delegated_stochastic": _empty_source_counts(),
            "d030_learned_selected": _empty_source_counts(),
        },
        "historical_greedy_action_counts": _empty_source_counts(),
        "source_one_step_changes": {
            "d026_delegated_stochastic": {
                "station_distance": _Distribution(),
                "max_pair_error": _Distribution(),
            },
            "d030_learned_selected": {
                "station_distance": _Distribution(),
                "max_pair_error": _Distribution(),
            },
        },
        "outcome": "unresolved",
        "reacquisition_transition": None,
        "reacquisition_physical_seconds": None,
        "transitions_since_seek_entry": None,
        "physical_seconds_since_seek_entry": None,
        "reacquisition_action": None,
        "energy_at_reacquisition": None,
        "temperature_normalized_at_reacquisition": None,
    }


def _update_episode_state(
    episode: dict[str, object], record: dict[str, object]
) -> None:
    station_distance = cast(float, record["station_distance"])
    pair_error = cast(float, record["max_pair_error"])
    if station_distance < cast(float, episode["minimum_station_distance"]):
        episode["minimum_station_distance"] = station_distance
        episode["minimum_station_distance_record"] = record
        episode["max_pair_error_at_minimum_station_distance"] = pair_error
    if pair_error < cast(float, episode["minimum_max_pair_error"]):
        episode["minimum_max_pair_error"] = pair_error
        episode["minimum_max_pair_error_record"] = record


def _geometry_branch(
    *,
    position: tuple[float, float],
    heading: float,
    station: tuple[float, float],
    distance: float,
    world_min: tuple[float, float],
    world_max: tuple[float, float],
) -> tuple[dict[str, float | bool], bool, bool]:
    proposed = (
        position[0] + distance * math.cos(heading),
        position[1] + distance * math.sin(heading),
    )
    next_position = (
        min(world_max[0], max(world_min[0], proposed[0])),
        min(world_max[1], max(world_min[1], proposed[1])),
    )
    realized = _distance(position, next_position)
    clipped = realized < distance - 1e-12
    stalled = realized <= 1e-12
    return _geometry(next_position, heading, station), clipped, stalled


def _branch_signature(branch: d029._BranchOutcome) -> tuple[object, ...]:
    telemetry = branch.telemetry
    return (
        telemetry.position_after,
        telemetry.heading,
        telemetry.charging_contact_after,
        branch.terminated,
        branch.truncated,
        telemetry.battery_after_j,
        telemetry.body_temperature_after_c,
    )


def _state_digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def _update_trajectory_digest(digest: Any, record: object) -> None:
    """Match D-043's compact digest without retaining a raw transition log."""
    encoded = json.dumps(
        d027._jsonable(record), sort_keys=True, separators=(",", ":")
    )
    digest.update(encoded.encode("utf-8"))
    digest.update(b"\n")


def _reconstruct_d043_learner_provenance(
    trace: Sequence[d043.D043TransitionTrace],
) -> dict[str, object]:
    """Reconstruct D-027 provenance from the accepted D-043 trace only."""
    learner = d027.D027ActionConsequencePredictor()
    update_digest = hashlib.sha256()
    for record in trace:
        current = d042._controller_observation(
            np.asarray(record.observation_before, dtype=np.float64)
        )
        next_observation = d042._controller_observation(
            np.asarray(record.observation, dtype=np.float64)
        )
        update = learner.observe_transition(current, record.action, next_observation)
        d030._update_digest(
            update_digest, record.transition_index, record.action, update
        )
    return {
        "trajectory_digest": d027._trace_digest(trace),
        "update_digest": update_digest.hexdigest(),
        "final_learner_weights_digest": _state_digest(
            learner.weight_snapshot()
        ),
        "transition_count": len(trace),
    }


def _canonical_projection(result: dict[str, object]) -> dict[str, object]:
    episode_fields = (
        "seek_entry_transition",
        "seek_entry_physical_seconds",
        "entry_action",
        "energy_at_entry",
        "temperature_normalized_at_entry",
        "outcome",
        "reacquisition_transition",
        "reacquisition_physical_seconds",
        "transitions_since_seek_entry",
        "physical_seconds_since_seek_entry",
        "reacquisition_action",
        "energy_at_reacquisition",
        "temperature_normalized_at_reacquisition",
    )
    top_fields = (
        "outcome",
        "transitions",
        "physical_seconds",
        "terminated",
        "truncated",
        "termination_reason",
        "action_counts",
        "mode_occupancy",
        "mode_entry_counts",
        "initial_dual_contact",
        "contact_entries",
        "contact_exits",
        "low_energy_seek_entries",
        "unresolved_seek_episodes",
        "horizon_censored_seek_episodes",
        "terminated_unresolved_seek_episodes",
        "physical_reacquisitions",
        "full_recharge_events",
        "recharge_events",
        "post_recharge_redepartures",
        "post_recharge_departure_events",
        "completed_autonomous_recharge_cycles",
        "reacquisition_transition_spacing",
        "reacquisition_physical_spacing",
        "recharge_transition_spacing",
        "recharge_physical_spacing",
        "turns",
        "battery_j",
        "battery_normalized",
        "temperature_normalized",
        "max_body_temperature_c",
    )
    projection = {field: result[field] for field in top_fields}
    projection["seek_episodes"] = [
        {field: episode[field] for field in episode_fields}
        for episode in cast(list[dict[str, object]], result["seek_episodes"])
    ]
    return projection


def _source_delta_summary(episode: dict[str, object]) -> dict[str, object]:
    source_changes = cast(
        dict[str, dict[str, _Distribution]], episode["source_one_step_changes"]
    )
    return {
        source: {
            metric: distribution.as_dict() for metric, distribution in changes.items()
        }
        for source, changes in source_changes.items()
    }


def _json_episode(episode: dict[str, object]) -> dict[str, object]:
    result = dict(episode)
    result["source_one_step_changes"] = _source_delta_summary(episode)
    result["action_counts_by_source"] = dict(
        cast(dict[str, int], episode["action_counts_by_source"])
    )
    result["selected_action_counts_by_source"] = {
        source: dict(counts)
        for source, counts in cast(
            dict[str, dict[str, int]], episode["selected_action_counts_by_source"]
        ).items()
    }
    result["historical_greedy_action_counts"] = dict(
        cast(dict[str, int], episode["historical_greedy_action_counts"])
    )
    return result


def _record_branch_summary(
    target: dict[str, dict[str, _BranchSummary]],
    *,
    label: str,
    stratum: str,
    pre: dict[str, float | bool],
    post: dict[str, float | bool],
    clipped: bool = False,
    stalled: bool = False,
) -> None:
    summary = target.setdefault(label, {}).setdefault(stratum, _BranchSummary())
    summary.add(
        station_distance_change=cast(float, post["station_distance"])
        - cast(float, pre["station_distance"]),
        max_pair_error_change=cast(float, post["max_pair_error"])
        - cast(float, pre["max_pair_error"]),
        resulting_station_distance=cast(float, post["station_distance"]),
        nominal_target_error=cast(float, post["nominal_target_center_error"]),
        resulting_front_plus_pair_error=cast(float, post["front_plus_pair_error"]),
        resulting_front_minus_pair_error=cast(float, post["front_minus_pair_error"]),
        resulting_max_pair_error=cast(float, post["max_pair_error"]),
        accepted_contact=cast(bool, post["accepted_dual_contact"]),
        clipped=clipped,
        stalled=stalled,
    )


def _summaries_as_dict(
    value: dict[str, dict[str, _BranchSummary]],
) -> dict[str, dict[str, object]]:
    return {
        label: {stratum: summary.as_dict() for stratum, summary in strata.items()}
        for label, strata in value.items()
    }


def _run_d044_seed(seed: int, *, horizon: int = D044_HORIZON) -> dict[str, object]:
    """Run one canonical D-043 lifetime with inert D-044 measurements."""
    if seed not in D044_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(f"seed {seed} is not a declared D-044 seed")
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon <= 0:
        raise ValueError("horizon must be a positive integer")

    environment, observation_array, streams = d042._initial_environment(seed, horizon)
    config = environment.config
    controller = d026.D026Controller(streams.policy)
    controller.reset()
    learner = d027.D027ActionConsequencePredictor()
    current = d042._controller_observation(observation_array)
    update_digest = hashlib.sha256()
    action_counts = {action.name: 0 for action in Action}
    mode_occupancy = {mode.name: 0 for mode in d026.D026Mode}
    mode_entry_counts = {mode.name: 0 for mode in d026.D026Mode}
    mode_entry_counts[controller.mode.name] = 1
    contact_entries: list[dict[str, object]] = []
    contact_exits: list[dict[str, object]] = []
    seek_episodes: list[dict[str, object]] = []
    recharge_events: list[dict[str, object]] = []
    reacquisition_transitions: list[int] = []
    recharge_transitions: list[int] = []
    active_seek: dict[str, object] | None = None
    recharge_active = False
    recharge_ready_for_departure = False
    completed_cycles = 0
    post_recharge_departures: list[dict[str, object]] = []
    turn_count = 0
    signed_turns = 0
    absolute_turns = 0
    turn_energy_j = 0.0
    transitions = 0
    terminated = False
    truncated = False
    initial_energy = current.energy
    minimum_energy = maximum_energy = current.energy
    initial_battery_j = d042.D042_INITIAL_BATTERY_J
    minimum_battery_j = maximum_battery_j = initial_battery_j
    initial_temperature = current.thermal
    minimum_temperature = maximum_temperature = current.thermal
    maximum_temperature_c = d042.D042_INITIAL_TEMPERATURE_C
    lfr_audit = _InformationAudit()
    trajectory_digest = hashlib.sha256()
    forward_branches: dict[str, _BranchSummary] = {
        str(distance): _BranchSummary() for distance in D044_FORWARD_CANDIDATES
    }
    forward_exemplars: dict[str, list[dict[str, object]]] = {
        str(distance): [] for distance in D044_FORWARD_CANDIDATES
    }
    delegated_branches: dict[str, dict[str, _BranchSummary]] = {}
    delegated_exemplars: list[dict[str, object]] = []
    branch_order_checks = 0
    branch_order_mismatches = 0
    source_environment_checks = True
    source_controller_checks = True
    source_learner_checks = True
    source_rng_checks = True
    prediction_queries_read_only = True
    real_move_distance_violations = 0
    real_move_distance_max = 0.0

    while not (terminated or truncated):
        if environment.body is None or environment.station_center is None:
            raise RuntimeError("D-044 evaluator geometry disappeared")
        station = environment.station_center
        body = environment.body
        position_before = body.position
        heading_before = body.heading
        mode_before = controller.mode
        mode_occupancy[mode_before.name] += 1
        historical_action = controller.act(current)
        mode_after = controller.mode
        if mode_after is not mode_before:
            mode_entry_counts[mode_after.name] += 1
        action = historical_action
        arbitration = controller.last_arbitration
        predictions: dict[Action, d027.D027Prediction] = {}
        if arbitration is not None and not arbitration.delegated:
            predictions, read_only = d030._query_candidate_predictions(learner, current)
            prediction_queries_read_only &= read_only
            if not read_only:
                raise RuntimeError("D-044 D-030 prediction query mutated learner")
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

        entered_seek = (
            mode_before is d026.D026Mode.AWAY
            and mode_after is d026.D026Mode.SEEK
            and current.energy < EXP003_B50_ENTER_SEEK_THRESHOLD
        )
        transition = transitions + 1
        if entered_seek:
            if active_seek is not None:
                raise RuntimeError("overlapping D-044 SEEK episodes")
            active_seek = _new_episode(
                transition=transition,
                action=action,
                energy=current.energy,
                thermal=current.thermal,
                position=position_before,
                heading=heading_before,
                station=station,
                observation=current,
            )
            seek_episodes.append(active_seek)

        seek_decision = (
            arbitration is not None
            and mode_after is d026.D026Mode.SEEK
            and not current.charging_contact
        )
        source: str | None = None
        pre_geometry = _geometry(position_before, heading_before, station)
        pre_lfr_geometry = d016.reconstruct_relative_geometry(
            current.beacon,
            beacon_scale=config.beacon_scale,
            probe_distance=config.probe_distance,
            sensor_angle=config.sensor_angle,
        )
        actual_lfr_geometry = d016._world_to_body_frame(
            position_before, station, heading_before
        )
        if seek_decision:
            arbitration_value = cast(d025.D025Arbitration, arbitration)
            source = (
                "d026_delegated_stochastic"
                if arbitration_value.delegated
                else "d030_learned_selected"
            )
            if active_seek is None:
                raise RuntimeError("SEEK decision had no active D-044 episode")
            counts = cast(dict[str, int], active_seek["action_counts_by_source"])
            counts[source] += 1
            selected_counts = cast(
                dict[str, dict[str, int]],
                active_seek["selected_action_counts_by_source"],
            )
            selected_counts[source][action.name] += 1
            greedy_counts = cast(
                dict[str, int], active_seek["historical_greedy_action_counts"]
            )
            greedy_counts[arbitration_value.greedy_action.name] += 1

            if action is Action.MOVE_FORWARD:
                for distance in D044_FORWARD_CANDIDATES:
                    post, clipped, stalled = _geometry_branch(
                        position=position_before,
                        heading=heading_before,
                        station=station,
                        distance=distance,
                        world_min=config.world_min,
                        world_max=config.world_max,
                    )
                    summary = forward_branches[str(distance)]
                    summary.add(
                        station_distance_change=cast(float, post["station_distance"])
                        - cast(float, pre_geometry["station_distance"]),
                        max_pair_error_change=cast(float, post["max_pair_error"])
                        - cast(float, pre_geometry["max_pair_error"]),
                        resulting_station_distance=cast(
                            float, post["station_distance"]
                        ),
                        nominal_target_error=cast(
                            float, post["nominal_target_center_error"]
                        ),
                        resulting_front_plus_pair_error=cast(
                            float, post["front_plus_pair_error"]
                        ),
                        resulting_front_minus_pair_error=cast(
                            float, post["front_minus_pair_error"]
                        ),
                        resulting_max_pair_error=cast(float, post["max_pair_error"]),
                        accepted_contact=cast(bool, post["accepted_dual_contact"]),
                        clipped=clipped,
                        stalled=stalled,
                    )
                    examples = forward_exemplars[str(distance)]
                    if len(examples) < D044_MAX_EXEMPLARS:
                        examples.append(
                            {
                                "seed": seed,
                                "transition": transition,
                                "source": source,
                                "pre_station_distance": pre_geometry[
                                    "station_distance"
                                ],
                                "pre_max_pair_error": pre_geometry["max_pair_error"],
                                "post": post,
                                "clipped": clipped,
                                "stalled": stalled,
                            }
                        )

            if source == "d026_delegated_stochastic":
                predictions, read_only = d030._query_candidate_predictions(
                    learner, current
                )
                prediction_queries_read_only &= read_only
                if not read_only:
                    raise RuntimeError(
                        "D-044 delegated prediction query mutated learner"
                    )
                learned_action = d030._choose_steering_action(
                    current, predictions, arbitration_value.greedy_action
                )
                branch_actions = (
                    ("actual_delegated", action),
                    ("d030_learned_alternative", learned_action),
                    ("historical_greedy", arbitration_value.greedy_action),
                )
                before_environment = d029._environment_state(environment)
                before_controller = d029._controller_state(controller)
                before_learner = learner.weights
                before_rng = d029._rng_state(streams)
                first: dict[str, tuple[object, ...]] = {}
                for label, branch_action in branch_actions:
                    branch = d029._branch(environment, current, branch_action)
                    first[label] = _branch_signature(branch)
                    telemetry = branch.telemetry
                    post_branch = _geometry(
                        telemetry.position_after,
                        telemetry.heading,
                        station,
                    )
                    _record_branch_summary(
                        delegated_branches,
                        label=label,
                        stratum=_stratum(
                            cast(float, pre_geometry["station_distance"]),
                            cast(float, pre_geometry["max_pair_error"]),
                        ),
                        pre=pre_geometry,
                        post=post_branch,
                    )
                    if len(delegated_exemplars) < D044_MAX_EXEMPLARS:
                        delegated_exemplars.append(
                            {
                                "seed": seed,
                                "transition": transition,
                                "pre_station_distance": pre_geometry[
                                    "station_distance"
                                ],
                                "pre_max_pair_error": pre_geometry["max_pair_error"],
                                "actions": {
                                    "actual_delegated": action.name,
                                    "d030_learned_alternative": learned_action.name,
                                    "historical_greedy": (
                                        arbitration_value.greedy_action.name
                                    ),
                                },
                                "label": label,
                                "post": post_branch,
                                "branch_contact": telemetry.charging_contact_after,
                            }
                        )
                for label, branch_action in reversed(branch_actions):
                    branch = d029._branch(environment, current, branch_action)
                    branch_order_checks += 1
                    if _branch_signature(branch) != first[label]:
                        branch_order_mismatches += 1
                source_environment_checks &= (
                    d029._environment_state(environment) == before_environment
                )
                source_controller_checks &= (
                    d029._controller_state(controller) == before_controller
                )
                source_learner_checks &= learner.weights == before_learner
                source_rng_checks &= d029._rng_state(streams) == before_rng

        if active_seek is not None:
            lfr_audit.add(pre_lfr_geometry, actual_lfr_geometry)

        observation_array, reward, terminated, truncated, info = environment.step(
            action
        )
        if reward != 0.0 or info != {}:
            raise RuntimeError("D-044 transition crossed the reward/info boundary")
        transition_telemetry = environment.last_transition
        if transition_telemetry is None:
            raise RuntimeError("D-044 transition telemetry is unavailable")
        _update_trajectory_digest(
            trajectory_digest,
            d043.D043TransitionTrace(
                transition_index=transition,
                mode_before=mode_before,
                mode_after=mode_after,
                action=action,
                observation_before=(
                    current.energy,
                    current.beacon.left,
                    current.beacon.forward,
                    current.beacon.right,
                    float(current.charging_contact),
                    current.thermal,
                ),
                observation=tuple(float(value) for value in observation_array),
                telemetry=transition_telemetry,
                reward=reward,
                info=info,
            ),
        )
        if action is Action.MOVE_FORWARD:
            realized_distance = _distance(
                transition_telemetry.position_before,
                transition_telemetry.position_after,
            )
            real_move_distance_max = max(real_move_distance_max, realized_distance)
            if realized_distance > config.movement_distance_world_units + 1e-12:
                real_move_distance_violations += 1
                raise RuntimeError(
                    "D-044 real MOVE_FORWARD exceeded canonical 0.05 distance"
                )
        if action in (Action.TURN_LEFT, Action.TURN_RIGHT):
            turn_energy_j += (
                transition_telemetry.actuator_electrical_power_w
                * environment.config.dt_seconds
            )
        next_observation = d042._controller_observation(observation_array)
        update = learner.observe_transition(current, action, next_observation)
        if update.action is not action:
            raise RuntimeError("D-044 D-027 update did not use executed action")
        d030._update_digest(update_digest, transition, action, update)
        transitions = transition

        if (
            not transition_telemetry.charging_contact_before
            and transition_telemetry.charging_contact_after
        ):
            contact_entries.append(
                {
                    "transition": transition,
                    "physical_seconds": transition * d042.D042_DT_SECONDS,
                    "action": action.name,
                    "mode_before": mode_before.name,
                    "mode_after": mode_after.name,
                }
            )
        if (
            transition_telemetry.charging_contact_before
            and not transition_telemetry.charging_contact_after
        ):
            contact_exits.append(
                {
                    "transition": transition,
                    "physical_seconds": transition * d042.D042_DT_SECONDS,
                    "action": action.name,
                    "mode_before": mode_before.name,
                    "mode_after": mode_after.name,
                }
            )

        if active_seek is not None:
            body_after = environment.body
            station_after = environment.station_center
            if body_after is None or station_after is None:
                raise RuntimeError("D-044 post-state geometry disappeared")
            post_record = _state_record(
                transition=transition,
                state_kind="post_action",
                action=action,
                energy=next_observation.energy,
                thermal=next_observation.thermal,
                position=body_after.position,
                heading=body_after.heading,
                station=station_after,
                observation=next_observation,
            )
            _update_episode_state(active_seek, post_record)
            source_changes = cast(
                dict[str, dict[str, _Distribution]],
                active_seek["source_one_step_changes"],
            )
            if source is not None:
                source_changes[source]["station_distance"].add(
                    cast(float, post_record["station_distance"])
                    - cast(float, pre_geometry["station_distance"])
                )
                source_changes[source]["max_pair_error"].add(
                    cast(float, post_record["max_pair_error"])
                    - cast(float, pre_geometry["max_pair_error"])
                )
            active_seek["final_record"] = post_record

        if active_seek is not None and (
            not transition_telemetry.charging_contact_before
            and transition_telemetry.charging_contact_after
        ):
            latency = transition - cast(int, active_seek["seek_entry_transition"])
            active_seek.update(
                {
                    "outcome": "reacquired",
                    "reacquisition_transition": transition,
                    "reacquisition_physical_seconds": transition * d042.D042_DT_SECONDS,
                    "transitions_since_seek_entry": latency,
                    "physical_seconds_since_seek_entry": latency * d042.D042_DT_SECONDS,
                    "reacquisition_action": action.name,
                    "energy_at_reacquisition": next_observation.energy,
                    "temperature_normalized_at_reacquisition": next_observation.thermal,
                    "reacquisition_record": active_seek["final_record"],
                }
            )
            reacquisition_transitions.append(transition)
            active_seek = None
            recharge_active = True

        if recharge_active and (
            transition_telemetry.battery_after_j
            >= environment.config.battery_capacity_j
            and transition_telemetry.charger_termination_latched_after
        ):
            recharge_events.append(
                {
                    "transition": transition,
                    "physical_seconds": transition * d042.D042_DT_SECONDS,
                    "energy_j": transition_telemetry.battery_after_j,
                    "reacquisition_transition": reacquisition_transitions[-1]
                    if reacquisition_transitions
                    else None,
                }
            )
            recharge_transitions.append(transition)
            recharge_active = False
            recharge_ready_for_departure = True

        if mode_before is d026.D026Mode.CHARGE and mode_after is d026.D026Mode.DEPART:
            if recharge_ready_for_departure:
                post_recharge_departures.append(
                    {
                        "transition": transition,
                        "physical_seconds": transition * d042.D042_DT_SECONDS,
                    }
                )
                completed_cycles += 1
                recharge_ready_for_departure = False

        minimum_energy = min(minimum_energy, next_observation.energy)
        maximum_energy = max(maximum_energy, next_observation.energy)
        minimum_battery_j = min(minimum_battery_j, transition_telemetry.battery_after_j)
        maximum_battery_j = max(maximum_battery_j, transition_telemetry.battery_after_j)
        maximum_temperature = max(maximum_temperature, next_observation.thermal)
        minimum_temperature = min(minimum_temperature, next_observation.thermal)
        maximum_temperature_c = max(
            maximum_temperature_c, transition_telemetry.body_temperature_after_c
        )
        current = next_observation

    if active_seek is not None:
        active_seek["outcome"] = (
            "terminated_before_reacquisition" if terminated else "horizon_censored"
        )
    if environment.last_transition is None:
        raise RuntimeError("D-044 lifetime produced no transition")
    termination_reason = d042._termination_reason(environment, terminated, truncated)
    unresolved = sum(
        int(episode["outcome"] in ("unresolved", "horizon_censored"))
        for episode in seek_episodes
    )
    if terminated and active_seek is not None:
        unresolved = 1
    horizon_censored_seek_episodes = sum(
        int(episode["outcome"] == "horizon_censored") for episode in seek_episodes
    )
    terminated_unresolved_seek_episodes = sum(
        int(episode["outcome"] == "terminated_before_reacquisition")
        for episode in seek_episodes
    )
    if completed_cycles:
        outcome = "REPEATED_CYCLE" if completed_cycles >= 2 else "FULL_CYCLE"
    elif recharge_events:
        outcome = "RECHARGED_NOT_DEPARTED"
    elif seek_episodes:
        outcome = "SEEK_REACQUIRED" if reacquisition_transitions else "SEEK_UNRESOLVED"
    else:
        outcome = "HORIZON_CENSORED" if truncated else "INITIAL_LIFETIME_ONLY"

    result: dict[str, object] = {
        "seed": seed,
        "outcome": outcome,
        "transitions": transitions,
        "physical_seconds": transitions * d042.D042_DT_SECONDS,
        "terminated": terminated,
        "truncated": truncated,
        "termination_reason": termination_reason,
        "action_counts": action_counts,
        "mode_occupancy": mode_occupancy,
        "mode_entry_counts": mode_entry_counts,
        "initial_dual_contact": True,
        "contact_entries": contact_entries,
        "contact_exits": contact_exits,
        "low_energy_seek_entries": len(seek_episodes),
        "seek_episodes": seek_episodes,
        "unresolved_seek_episodes": unresolved,
        "horizon_censored_seek_episodes": horizon_censored_seek_episodes,
        "terminated_unresolved_seek_episodes": terminated_unresolved_seek_episodes,
        "physical_reacquisitions": len(reacquisition_transitions),
        "full_recharge_events": len(recharge_events),
        "recharge_events": recharge_events,
        "post_recharge_redepartures": len(post_recharge_departures),
        "post_recharge_departure_events": post_recharge_departures,
        "completed_autonomous_recharge_cycles": completed_cycles,
        "reacquisition_transition_spacing": [
            right - left
            for left, right in zip(
                reacquisition_transitions, reacquisition_transitions[1:], strict=False
            )
        ],
        "reacquisition_physical_spacing": [
            (right - left) * d042.D042_DT_SECONDS
            for left, right in zip(
                reacquisition_transitions, reacquisition_transitions[1:], strict=False
            )
        ],
        "recharge_transition_spacing": [
            right - left
            for left, right in zip(
                recharge_transitions, recharge_transitions[1:], strict=False
            )
        ],
        "recharge_physical_spacing": [
            (right - left) * d042.D042_DT_SECONDS
            for left, right in zip(
                recharge_transitions, recharge_transitions[1:], strict=False
            )
        ],
        "turns": {
            "count": turn_count,
            "signed_count": signed_turns,
            "absolute_count": absolute_turns,
            "commanded_signed_angle_radians": signed_turns * d042.D042_TURN_ANGLE,
            "commanded_absolute_angle_radians": absolute_turns * d042.D042_TURN_ANGLE,
            "electrical_energy_j": turn_energy_j,
            "timestep_seconds": turn_count * d042.D042_DT_SECONDS,
        },
        "battery_j": {
            "start": initial_battery_j,
            "minimum": minimum_battery_j,
            "final": environment.battery_j,
            "maximum": maximum_battery_j,
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
            "maximum": maximum_temperature,
            "final": current.thermal,
        },
        "max_body_temperature_c": maximum_temperature_c,
        "d044_diagnostics": {
            "lfr_information": lfr_audit,
            "forward_exemplars": forward_exemplars,
            "delegated_exemplars": delegated_exemplars,
            "branch_order_checks": branch_order_checks,
            "branch_order_mismatches": branch_order_mismatches,
            "source_environment_checks": source_environment_checks,
            "source_controller_checks": source_controller_checks,
            "source_learner_checks": source_learner_checks,
            "source_rng_checks": source_rng_checks,
            "prediction_queries_read_only": prediction_queries_read_only,
            "real_move_forward_distance_world_units": (
                config.movement_distance_world_units
            ),
            "real_move_distance_max": real_move_distance_max,
            "real_move_distance_violations": real_move_distance_violations,
            "trajectory_digest": trajectory_digest.hexdigest(),
            "update_digest": update_digest.hexdigest(),
            "final_learner_weights_digest": _state_digest(learner.weight_snapshot()),
        },
    }
    result["seek_episodes"] = [_json_episode(episode) for episode in seek_episodes]
    result["d044_diagnostics"] = {
        **cast(dict[str, object], result["d044_diagnostics"]),
        "lfr_information": lfr_audit.as_dict(),
        "forward_branches": {
            distance: summary.as_dict()
            for distance, summary in forward_branches.items()
        },
        "delegated_branch_attribution": _summaries_as_dict(delegated_branches),
    }
    canonical_trace: list[d043.D043TransitionTrace] = []
    canonical = d043._run_d043_seed(
        seed, horizon=horizon, trace=canonical_trace
    )
    d043_provenance = _reconstruct_d043_learner_provenance(canonical_trace)
    diagnostics = cast(dict[str, object], result["d044_diagnostics"])
    trajectory_match = (
        cast(str, diagnostics["trajectory_digest"])
        == d043_provenance["trajectory_digest"]
    )
    update_match = (
        cast(str, diagnostics["update_digest"]) == d043_provenance["update_digest"]
    )
    final_weights_match = (
        cast(str, diagnostics["final_learner_weights_digest"])
        == d043_provenance["final_learner_weights_digest"]
    )
    transition_count_match = (
        result["transitions"] == d043_provenance["transition_count"]
    )
    canonical_fields_match = _canonical_projection(result) == _canonical_projection(
        canonical
    )
    identity_match = all(
        (
            canonical_fields_match,
            trajectory_match,
            update_match,
            final_weights_match,
            transition_count_match,
        )
    )
    if not identity_match:
        raise RuntimeError(f"D-044 blocked: D-043 replay mismatch for seed {seed}")
    diagnostics["d043_replay_identity"] = {
        "match": identity_match,
        "canonical_fields_match": canonical_fields_match,
        "trajectory_digest_match": trajectory_match,
        "update_digest_match": update_match,
        "final_learner_weights_digest_match": final_weights_match,
        "transition_count_match": transition_count_match,
        "compared_fields": list(_canonical_projection(canonical)),
        "trajectory_digest": d043_provenance["trajectory_digest"],
        "update_digest": d043_provenance["update_digest"],
        "final_learner_weights_digest": d043_provenance[
            "final_learner_weights_digest"
        ],
        "transition_count": d043_provenance["transition_count"],
        "provenance_source": "D-043 trace sink replayed through unchanged D-027",
    }
    return result


def _aggregate(results: Sequence[dict[str, object]]) -> dict[str, object]:
    episodes = [
        episode
        for result in results
        for episode in cast(list[dict[str, object]], result["seek_episodes"])
    ]
    matched: list[dict[str, object]] = []
    for result in results:
        seed_episodes = cast(list[dict[str, object]], result["seek_episodes"])
        if len(seed_episodes) < 2:
            continue
        matched.append(
            {
                "seed": result["seed"],
                "first": _cycle_comparison(seed_episodes[0]),
                "second": _cycle_comparison(seed_episodes[1]),
            }
        )
    replay_identity_all_match = all(
        cast(
            bool,
            cast(
                dict[str, object],
                cast(dict[str, object], result["d044_diagnostics"])[
                    "d043_replay_identity"
                ],
            )["match"],
        )
        for result in results
    )
    branch_isolation_all_pass = all(
        all(
            cast(bool, cast(dict[str, object], result["d044_diagnostics"])[key])
            for key in (
                "source_environment_checks",
                "source_controller_checks",
                "source_learner_checks",
                "source_rng_checks",
                "prediction_queries_read_only",
            )
        )
        and cast(
            int,
            cast(dict[str, object], result["d044_diagnostics"])[
                "branch_order_mismatches"
            ],
        )
        == 0
        for result in results
    )
    forward_support: dict[str, int] = {}
    for distance in (str(value) for value in D044_FORWARD_CANDIDATES):
        forward_support[distance] = sum(
            _forward_count(result, distance) for result in results
        )
    return {
        "lifetime_count": len(results),
        "seek_episode_count": len(episodes),
        "lifetime_count_with_multiple_seek_episodes": len(matched),
        "cycle_order_matched_by_seed": matched,
        "outcome_counts": {
            outcome: sum(int(result["outcome"] == outcome) for result in results)
            for outcome in (
                "REPEATED_CYCLE",
                "FULL_CYCLE",
                "RECHARGED_NOT_DEPARTED",
                "SEEK_REACQUIRED",
                "SEEK_UNRESOLVED",
                "HORIZON_CENSORED",
                "INITIAL_LIFETIME_ONLY",
            )
        },
        "replay_identity_all_match": replay_identity_all_match,
        "branch_isolation_all_pass": branch_isolation_all_pass,
        "total_forward_branch_support": forward_support,
    }


def _cycle_comparison(episode: dict[str, object]) -> dict[str, object]:
    return {
        key: episode[key]
        for key in (
            "seek_entry_transition",
            "energy_at_entry",
            "temperature_normalized_at_entry",
            "entry_station_distance",
            "entry_nominal_target_center_error",
            "entry_heading_error",
            "entry_max_pair_error",
            "minimum_station_distance",
            "minimum_max_pair_error",
            "max_pair_error_at_minimum_station_distance",
            "outcome",
            "transitions_since_seek_entry",
            "action_counts_by_source",
            "selected_action_counts_by_source",
            "historical_greedy_action_counts",
            "source_one_step_changes",
        )
    }


def _forward_count(result: dict[str, object], distance: str) -> int:
    diagnostics = cast(dict[str, object], result["d044_diagnostics"])
    branches = cast(dict[str, object], diagnostics["forward_branches"])
    summary = cast(dict[str, object], branches[distance])
    return cast(int, summary["count"])


def run_d044_probe(
    seeds: Sequence[int] = D044_DEFAULT_DEVELOPMENT_SEEDS,
    *,
    horizon: int = D044_HORIZON,
    executed_commit_sha: str | None = None,
) -> dict[str, object]:
    """Run exactly the frozen D-043 support with the D-044 audit attached."""
    validated = _seed_guard(seeds)
    if horizon != D044_HORIZON:
        raise ValueError("D-044 requires the frozen 140,000-transition horizon")
    if executed_commit_sha is not None:
        if len(executed_commit_sha) != 40 or any(
            character not in "0123456789abcdef" for character in executed_commit_sha
        ):
            raise ValueError("executed_commit_sha must be a 40-character lowercase SHA")
    results = [_run_d044_seed(seed, horizon=horizon) for seed in validated]
    return {
        "schema_version": 1,
        "experiment": "D-044",
        "title": (
            "Coarse homing versus terminal docking and cycle-order attribution audit"
        ),
        "authoritative_base_sha": D044_AUTHORITATIVE_BASE_SHA,
        "implementation_probe_sha": executed_commit_sha,
        "development_seeds": list(validated),
        "horizon": horizon,
        "timestep_seconds": d042.D042_DT_SECONDS,
        "lifetime": "one uninterrupted causal lifetime per seed",
        "seed_policy": {
            "canonical_validator": "D-043 validate_exp003_development_seeds",
            "formal_reservation_guard_preserved": True,
            "formal_reserved_ranges_excluded": True,
            "reused_development_support_intentional": True,
        },
        "canonical_organism_unchanged": {
            "source": "D-042/D-043 real trajectory",
            "actions": [action.name for action in Action],
            "move_forward_world_units": d042._canonical_config(
                horizon
            ).movement_distance_world_units,
            "turn_angle_radians": d042.D042_TURN_ANGLE,
            "visible_channels": list(d027.D027_CHANNELS),
            "reward": 0.0,
            "info": {},
        },
        "diagnostic_boundary": {
            "geometry_and_beacon_reconstruction_evaluator_only": True,
            "counterfactual_branches_evaluator_only": True,
            "variable_distance_action_authorized": False,
            "terminal_docking_state_authorized": False,
            "diagnostic_values_reach_organism": False,
        },
        "results": results,
        "aggregate": _aggregate(results),
        "interpretation": (
            "Descriptive Development diagnostic only; no organism change or "
            "confirmatory claim."
        ),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--executed-commit-sha", required=True)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    args.output.write_text(
        json.dumps(
            run_d044_probe(executed_commit_sha=args.executed_commit_sha),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
