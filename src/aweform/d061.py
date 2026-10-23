"""D-061 bounded causal action-consequence intervention in V0.5."""

from __future__ import annotations

import argparse
import hashlib
import json
import resource
import signal
from collections import Counter
from pathlib import Path
from typing import Final, Sequence

import numpy as np

from .d045 import (
    D045_AMBIENT_TEMPERATURE_C,
    D045_BATTERY_CAPACITY_J,
    D045_MAX_WHEEL_DELTA_RAD,
    D045Env,
    D045PhysicalConfig,
)
from .d046 import D046ConsequencePredictor
from .d049 import D049_STATION_CENTER
from .d052 import D052Controller, D052Mode
from .d053 import D053RoamingFixture
from .env import Action
from .exp003_seed_policy import validate_exp003_development_seeds

D061_SEEDS: Final = (22053, 22054, 22055)
D061_HORIZON: Final = 120_000
D061_WARMUP: Final = 564
D061_INTERVAL: Final = 4
D061_TRACE_STRIDE: Final = 100
D061_WALL_GUARD_SECONDS: Final = 600
D061_CPU_GUARD_SECONDS: Final = 600
D061_CANDIDATES: Final = (
    (Action.MOVE_FORWARD, (D045_MAX_WHEEL_DELTA_RAD, D045_MAX_WHEEL_DELTA_RAD)),
    (Action.TURN_LEFT, (-D045_MAX_WHEEL_DELTA_RAD, D045_MAX_WHEEL_DELTA_RAD)),
    (Action.TURN_RIGHT, (D045_MAX_WHEEL_DELTA_RAD, -D045_MAX_WHEEL_DELTA_RAD)),
)
D061_ARMS: Final = ("U", "L", "P")


def validate_d061_seeds(
    seeds: Sequence[int] = (22053,),
) -> tuple[int, ...]:
    validated = validate_exp003_development_seeds(seeds)
    if not validated or len(set(validated)) != len(validated):
        raise ValueError("D-061 requires a non-empty, unique legal seed set")
    if any(seed not in D061_SEEDS for seed in validated):
        raise ValueError(f"D-061 supports only {D061_SEEDS}")
    return validated


def _sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def run_d061_lifetime(
    seed: int, arm: str, *, horizon: int = D061_HORIZON
) -> dict[str, object]:
    if (
        seed not in D061_SEEDS
        or arm not in D061_ARMS
        or horizon <= 0
        or horizon > D061_HORIZON
    ):
        raise ValueError("invalid D-061 seed, arm, or horizon")
    env = D045Env(D045PhysicalConfig(episode_horizon=horizon))
    observation, info = env.reset(
        options={
            "body_position": D049_STATION_CENTER,
            "station_center": D049_STATION_CENTER,
            "heading": 0.0,
            "battery_j": 0.80 * D045_BATTERY_CAPACITY_J,
            "body_temperature_c": D045_AMBIENT_TEMPERATURE_C,
            "charger_termination_latched": False,
        }
    )
    if info != {}:
        raise RuntimeError("D-045 reset info must be empty")
    controller, fixture, learner = (
        D052Controller(),
        D053RoamingFixture(seed),
        D046ConsequencePredictor(),
    )
    trace: list[dict[str, object]] = []
    modes: Counter[str] = Counter()
    updates = 0
    nonzero_updates = 0
    intervention_eligible = eligible_since_warmup = 0
    attempted = selected_differs = selected_supported = 0
    action_changes = 0
    previous_action: tuple[float, float] | None = None
    min_energy = float(observation[0])
    initial_energy = env.battery_j
    initial_observation = tuple(float(value) for value in observation)
    initial_body = env.body
    if initial_body is None:
        raise RuntimeError("missing D-045 body after reset")
    initial_position = tuple(float(value) for value in initial_body.position)
    initial_heading = float(initial_body.heading)
    locomotor_distance = 0.0
    charging_contacts = charge_cycles = 0
    charge_steps = 0
    candidate_experience: Counter[tuple[float, float]] = Counter()
    contact_before = bool(observation[5])
    rewards_ok = infos_ok = legal_ok = float32_ok = True
    terminated = truncated = False
    for step in range(1, horizon + 1):
        proposal = fixture.propose()
        proposed = proposal.wheel_command
        visible = tuple(float(value) for value in observation)
        can_intervene = (
            arm != "U"
            and controller.mode is D052Mode.NORMAL
            and float(observation[0]) > 0.20
        )
        if can_intervene and step > D061_WARMUP:
            intervention_eligible += 1
            eligible_since_warmup += 1
        intervention = (
            can_intervene
            and step > D061_WARMUP
            and eligible_since_warmup % D061_INTERVAL == 0
        )
        if intervention:
            attempted += 1
            scored: list[tuple[float, tuple[float, float]]] = []
            perm = (1, 2, 0) if arm == "P" else (0, 1, 2)
            for candidate_index, (_, candidate) in enumerate(D061_CANDIDATES):
                pred = learner.predict(visible, candidate)
                associate = perm[candidate_index]
                score = pred.delta[3]
                if arm == "P":
                    # Fixed cyclic permutation of prediction/action associations.
                    score = learner.predict(
                        visible, D061_CANDIDATES[associate][1]
                    ).delta[3]
                scored.append((score, candidate))
            values = [score for score, _ in scored]
            if max(values) - min(values) > 1e-12:
                chosen = scored[max(range(3), key=lambda index: values[index])][1]
                selected_differs += int(chosen != proposed)
                selected_supported += int(candidate_experience[chosen] > 0)
                proposed = chosen
        decision = controller.command(observation, proposed)
        modes[decision.active_mode.value] += 1
        wheels = (decision.wheel_delta_left, decision.wheel_delta_right)
        action_changes += int(previous_action is not None and wheels != previous_action)
        previous_action = wheels
        prediction = learner.predict(visible, wheels)
        candidate_experience[wheels] += 1
        body_before = env.body
        if body_before is None:
            raise RuntimeError("missing D-045 body before transition")
        position_before = tuple(float(value) for value in body_before.position)
        next_observation, reward, terminated, truncated, info = env.step(wheels)
        if next_observation.shape != (8,) or next_observation.dtype != np.float32:
            raise RuntimeError("D-061 requires eight float32 observation channels")
        float32_ok &= (
            next_observation.dtype == np.float32 and observation.dtype == np.float32
        )
        rewards_ok &= reward == 0.0
        infos_ok &= info == {}
        legal_ok &= all(
            abs(value) <= D045_MAX_WHEEL_DELTA_RAD + 1e-15 for value in wheels
        )
        update = learner.update_from_transition(
            visible,
            wheels,
            tuple(float(value) for value in next_observation),
            prediction,
        )
        updates += 1
        nonzero_updates += int(any(error != 0.0 for error in update.errors))
        telemetry = env.last_transition
        if telemetry is None:
            raise RuntimeError("missing D-045 telemetry")
        body_after = env.body
        if body_after is None:
            raise RuntimeError("missing D-045 body after transition")
        locomotor_distance += float(
            np.linalg.norm(
                np.asarray(body_after.position) - np.asarray(position_before)
            )
        )
        acquired = not contact_before and bool(next_observation[5])
        charging_contacts += int(acquired)
        charge_cycles += int(acquired and decision.active_mode is D052Mode.RETURN)
        charge_steps += int(decision.active_mode is D052Mode.CHARGE)
        min_energy = min(min_energy, float(next_observation[0]))
        if (
            step % D061_TRACE_STRIDE == 0
            or step == 1
            or step == horizon
            or acquired
            or decision.events
        ):
            body = env.body
            if body is None:
                raise RuntimeError("missing D-045 body")
            trace.append(
                {
                    "transition": step,
                    "x": float(body.position[0]),
                    "y": float(body.position[1]),
                    "heading": float(body.heading),
                    "energy": float(observation[0]),
                    "energy_after": float(next_observation[0]),
                    "thermal": float(next_observation[1]),
                    "charging_contact": bool(observation[5]),
                    "charging_contact_after": bool(next_observation[5]),
                    "charging_contact_before": contact_before,
                    "active_mode": decision.active_mode.value,
                    "command_source": decision.command_source.value,
                    "d050_mode": decision.d050_mode.value
                    if decision.d050_mode
                    else None,
                    "symbolic_proposal": proposal.symbolic_action.name,
                    "events": list(decision.events),
                    "terminated": bool(terminated),
                    "truncated": bool(truncated),
                    "simulated_seconds": step * 0.1,
                    "cycle_index": charge_cycles,
                    "action": list(wheels),
                    "reward": reward,
                    "info": info,
                }
            )
        contact_before = bool(next_observation[5])
        observation = next_observation
        if terminated or truncated:
            break
    final_body = env.body
    if final_body is None:
        raise RuntimeError("missing D-045 body at lifetime end")
    return {
        "seed": seed,
        "arm": arm,
        "horizon": horizon,
        "transitions": controller.transition_count,
        "initial_battery_j": initial_energy,
        "final_battery_j": env.battery_j,
        "initial_state": {
            "position": initial_position,
            "heading": initial_heading,
            "energy_fraction": 0.80,
            "temperature_channel": initial_observation[1],
            "charging_contact": bool(initial_observation[5]),
            "temperature_c": D045_AMBIENT_TEMPERATURE_C,
            "charging_latch": False,
        },
        "final_state": {
            "position": tuple(float(value) for value in final_body.position),
            "heading": float(final_body.heading),
            "energy_fraction": float(observation[0]),
            "temperature_channel": float(observation[1]),
            "charging_contact": bool(observation[5]),
        },
        "locomotor_distance_m": locomotor_distance,
        "minimum_energy_fraction": min_energy,
        "final_energy_fraction": float(observation[0]),
        "mode_durations": dict(sorted(modes.items())),
        "preemptions": controller.preemption_transition_count,
        "charging_contact_acquisitions": charging_contacts,
        "charge_cycles": charge_cycles,
        "charging_steps": charge_steps,
        "termination": bool(terminated),
        "horizon_censored": bool(truncated),
        "intervention_eligible": intervention_eligible,
        "intervention_attempts": attempted,
        "selected_action_differs_from_U_proposal": selected_differs,
        "selected_action_in_candidate_support": selected_supported,
        "action_change_rate": action_changes / max(1, controller.transition_count - 1),
        "learner_updates": updates,
        "learner_nonzero_weight_updates": nonzero_updates,
        "learner_final_weight_digest": learner.weight_digest(),
        "reward_zero": rewards_ok,
        "info_empty": infos_ok,
        "float32_eight_channels": float32_ok,
        "legal_wheels": legal_ok,
        "trace": trace,
    }


def write_d061_artifact(
    output: Path,
    *,
    horizon: int = D061_HORIZON,
    seeds: Sequence[int] = (22053,),
) -> Path:
    seeds = validate_d061_seeds(seeds)
    results = [
        run_d061_lifetime(seed, arm, horizon=horizon)
        for seed in seeds
        for arm in D061_ARMS
    ]
    payload = {
        "schema": "aweform.d061.execution.v1",
        "horizon": horizon,
        "seeds": seeds,
        "execution_guard": {
            "wall_seconds": D061_WALL_GUARD_SECONDS,
            "cpu_seconds": D061_CPU_GUARD_SECONDS,
        },
        "intervention_schedule": {
            "warmup": D061_WARMUP,
            "eligible_interval": D061_INTERVAL,
        },
        "results": results,
    }
    payload["sha256_without_self"] = _sha(payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n",
        encoding="utf-8",
    )
    return output


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run bounded D-061 causal wheel-action experiment"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--horizon", type=int, default=D061_HORIZON)
    parser.add_argument(
        "--seed",
        type=int,
        action="append",
        dest="seeds",
        help="Legal D-053 development seed; repeat for additional seeds.",
    )
    args = parser.parse_args(argv)

    def wall_timeout(_signum: int, _frame: object) -> None:
        raise TimeoutError("D-061 exceeded its fixed wall-time guard")

    resource.setrlimit(
        resource.RLIMIT_CPU,
        (D061_CPU_GUARD_SECONDS, D061_CPU_GUARD_SECONDS),
    )
    signal.signal(signal.SIGALRM, wall_timeout)
    signal.alarm(D061_WALL_GUARD_SECONDS)
    write_d061_artifact(
        args.output,
        horizon=args.horizon,
        seeds=tuple(args.seeds) if args.seeds else (22053,),
    )
    return 0
