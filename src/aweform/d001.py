"""D-001 current EXP-003 ecology degeneracy probe.

This development-only probe isolates the post-acquisition charging state. It
places the simulator-side body at the already-existing station centre, then
applies a constant action. The placement is an explicit evaluator/harness
intervention; it is not an organism observation or learned capability.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, replace
from enum import Enum
from typing import Sequence

from .env import Action
from .exp003 import EXP003_HORIZON, EXP003StationConfig, LocalizedChargingStationEnv
from .exp003_seed_policy import validate_exp003_development_seeds

D001_DEFAULT_DEVELOPMENT_SEEDS = (18141, 18142, 18143)


class D001Policy(str, Enum):
    """Trivial constant policies used after the harness establishes contact."""

    DOCK_WAIT = "DOCK_WAIT"
    DOCK_TURN_LEFT = "DOCK_TURN_LEFT"


@dataclass(frozen=True, slots=True)
class D001ProbeResult:
    """Evaluator-side descriptive result for one development probe run."""

    environment_seed: int
    policy: D001Policy
    horizon: int
    transitions: int
    initial_energy: float
    final_energy: float
    minimum_energy: float
    first_full_energy_step: int | None
    charging_contact_preserved: bool
    position_preserved: bool
    terminated: bool
    truncated: bool

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-safe representation for lightweight run capture."""
        return {
            "environment_seed": self.environment_seed,
            "policy": self.policy.value,
            "horizon": self.horizon,
            "transitions": self.transitions,
            "initial_energy": self.initial_energy,
            "final_energy": self.final_energy,
            "minimum_energy": self.minimum_energy,
            "first_full_energy_step": self.first_full_energy_step,
            "charging_contact_preserved": self.charging_contact_preserved,
            "position_preserved": self.position_preserved,
            "terminated": self.terminated,
            "truncated": self.truncated,
        }


def run_d001_probe(
    seeds: Sequence[int] = D001_DEFAULT_DEVELOPMENT_SEEDS,
    *,
    horizon: int = EXP003_HORIZON,
) -> tuple[D001ProbeResult, ...]:
    """Run the D-001 constant-action docked-state probe on legal dev seeds."""
    development_seeds = validate_exp003_development_seeds(seeds)
    config = replace(EXP003StationConfig(), episode_horizon=horizon)
    results: list[D001ProbeResult] = []
    for seed in development_seeds:
        for policy in D001Policy:
            results.append(_run_docked_policy(seed, policy, config))
    return tuple(results)


def d001_contact_net_energy(config: EXP003StationConfig) -> dict[D001Policy, float]:
    """Return the pre-clipping net energy change while contact is retained."""
    return {
        D001Policy.DOCK_WAIT: (
            config.charge_rate - config.energy.basal_cost - config.wait_cost
        ),
        D001Policy.DOCK_TURN_LEFT: (
            config.charge_rate - config.energy.basal_cost - config.turn_cost
        ),
    }


def _run_docked_policy(
    environment_seed: int,
    policy: D001Policy,
    config: EXP003StationConfig,
) -> D001ProbeResult:
    environment = LocalizedChargingStationEnv(config)
    _, info = environment.reset(seed=environment_seed)
    if info != {}:
        raise RuntimeError("D-001 reset crossed the evaluator boundary")
    if environment.body is None or environment.station_center is None:
        raise RuntimeError("D-001 environment did not initialize evaluator state")

    # Explicit D-001 harness intervention: isolate the ecological question
    # after charger acquisition by beginning the probe in genuine contact.
    environment.body.x = environment.station_center[0]
    environment.body.y = environment.station_center[1]
    if not environment.charging_contact:
        raise RuntimeError("D-001 harness failed to establish charging contact")

    initial_position = environment.body.position
    initial_energy = environment.body.energy
    minimum_energy = initial_energy
    first_full_energy_step: int | None = None
    charging_contact_preserved = True
    position_preserved = True
    transitions = 0
    terminated = False
    truncated = False
    action = (
        Action.WAIT
        if policy is D001Policy.DOCK_WAIT
        else Action.TURN_LEFT
    )

    while not (terminated or truncated):
        _, reward, terminated, truncated, step_info = environment.step(action)
        if reward != 0.0:
            raise RuntimeError("D-001 reward must remain exactly 0.0")
        if step_info != {}:
            raise RuntimeError("D-001 step crossed the evaluator boundary")
        telemetry = environment.last_transition
        if telemetry is None:
            raise RuntimeError("D-001 transition telemetry is unavailable")
        transitions += 1
        minimum_energy = min(minimum_energy, telemetry.energy_after)
        charging_contact_preserved = charging_contact_preserved and (
            telemetry.charging_contact_before and telemetry.charging_contact_after
        )
        position_preserved = position_preserved and (
            telemetry.position_before == initial_position
            and telemetry.position_after == initial_position
        )
        if first_full_energy_step is None and math.isclose(
            telemetry.energy_after,
            config.energy.maximum_energy,
        ):
            first_full_energy_step = transitions

    if environment.body is None:
        raise RuntimeError("D-001 body disappeared after probe")
    return D001ProbeResult(
        environment_seed=environment_seed,
        policy=policy,
        horizon=config.episode_horizon,
        transitions=transitions,
        initial_energy=initial_energy,
        final_energy=environment.body.energy,
        minimum_energy=minimum_energy,
        first_full_energy_step=first_full_energy_step,
        charging_contact_preserved=charging_contact_preserved,
        position_preserved=position_preserved,
        terminated=terminated,
        truncated=truncated,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the D-001 current-ecology docked-state degeneracy probe."
    )
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=list(D001_DEFAULT_DEVELOPMENT_SEEDS),
        help="Legal development seeds only.",
    )
    parser.add_argument(
        "--horizon",
        type=int,
        default=EXP003_HORIZON,
        help="Finite development-probe horizon.",
    )
    return parser.parse_args()


def main() -> None:
    """Run the probe and print a compact JSON record for the D-file."""
    args = _parse_args()
    config = replace(EXP003StationConfig(), episode_horizon=args.horizon)
    net_energy = d001_contact_net_energy(config)
    results = run_d001_probe(args.seeds, horizon=args.horizon)
    payload = {
        "development_seeds": list(validate_exp003_development_seeds(args.seeds)),
        "horizon": args.horizon,
        "contact_net_energy_before_clipping": {
            policy.value: value for policy, value in net_energy.items()
        },
        "results": [result.as_dict() for result in results],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
