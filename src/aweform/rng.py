"""Explicit ownership of deterministic random-number streams."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class RandomStreams:
    """Independent named generators derived from one master seed."""

    environment: np.random.Generator
    policy: np.random.Generator

    @classmethod
    def from_seed(cls, master_seed: int) -> RandomStreams:
        """Create independent environment and policy streams."""
        seed_sequence = np.random.SeedSequence(master_seed)
        environment_seed, policy_seed = seed_sequence.spawn(2)
        return cls(
            environment=np.random.default_rng(environment_seed),
            policy=np.random.default_rng(policy_seed),
        )
