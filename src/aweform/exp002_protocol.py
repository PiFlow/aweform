"""Frozen planning constants for the EXP-002 pre-calibration slice.

This module declares the candidate and seed reservations only.  It contains
no calibration executor and no candidate-selection call, so importing it
cannot execute an EXP-002 seed.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final

from .exp001 import EXP001DevelopmentConfig

EXP002_PROTOCOL_REVISION: Final = "EXP-002-precalibration-001"
EXP002_PROTOCOL_FILE_SHA256: Final = (
    "18875e9e97221db0dcb7acb1ee50d9dc6546dd619d9f871430801335455f77d1"
)
EXP002_HORIZON: Final = 1000
EXP002_COVERAGE_GRID_WIDTH: Final = 32
EXP002_COVERAGE_GRID_HEIGHT: Final = 32

EXP002_CALIBRATION_SEEDS: Final = tuple(range(40001, 40201))
EXP002_CONFIRMATORY_SEEDS: Final = tuple(range(50001, 51001))


class EXP002BCandidate(Enum):
    """Predeclared B interoceptive SEEK-entry candidates."""

    B35 = "B35"
    B40 = "B40"
    B45 = "B45"
    B50 = "B50"

    @property
    def enter_seek(self) -> float:
        return {
            EXP002BCandidate.B35: 0.35,
            EXP002BCandidate.B40: 0.40,
            EXP002BCandidate.B45: 0.45,
            EXP002BCandidate.B50: 0.50,
        }[self]


EXP002_B_CANDIDATES: Final = tuple(EXP002BCandidate)
EXP002_CALIBRATION_MINIMUM_SURVIVAL_FRACTION: Final = 0.90
EXP002_CALIBRATION_MINIMUM_SURVIVAL_COUNT: Final = 180
EXP002_SELECTION_RULE_IDENTIFIER: Final = (
    "EXP-002-VIABILITY-ELIGIBILITY-MEAN-UNIQUE-COVERAGE"
)
EXP002_SELECTION_RULE: Final = (
    "eligibility: horizon survival fraction >= 0.90; if any candidate is "
    "eligible, select greatest mean unique spatial coverage; otherwise select "
    "highest horizon-survival fraction; ties: greater mean unique spatial "
    "coverage, then lower SEEK-entry threshold"
)


@dataclass(frozen=True, slots=True)
class EXP002SharedControllerValues:
    """The EXP-001-frozen controller values shared by EXP-002."""

    resource_contact_threshold: float = 0.8
    blind_explore_duration: int = 10
    blind_charge_duration: int = 5
    recover: float = 0.85

    def for_b_candidate(self, candidate: EXP002BCandidate) -> EXP001DevelopmentConfig:
        """Build B's config, varying only its SEEK-entry threshold."""
        return EXP001DevelopmentConfig(
            resource_contact_threshold=self.resource_contact_threshold,
            blind_explore_duration=self.blind_explore_duration,
            blind_charge_duration=self.blind_charge_duration,
            enter_seek=candidate.enter_seek,
            recover=self.recover,
        )

    def for_a_or_c(self) -> EXP001DevelopmentConfig:
        """Build the unchanged A/C configuration, including historical B35."""
        return EXP001DevelopmentConfig(
            resource_contact_threshold=self.resource_contact_threshold,
            blind_explore_duration=self.blind_explore_duration,
            blind_charge_duration=self.blind_charge_duration,
            enter_seek=EXP002BCandidate.B35.enter_seek,
            recover=self.recover,
        )


EXP002_SHARED_CONTROLLER_VALUES: Final = EXP002SharedControllerValues()
