# EXP-002 — Interoceptive SEEK-entry threshold and spatial exploration

**Status:** pre-calibration planning/instrumentation only

**Protocol revision:** `EXP-002-precalibration-001`

**Calibration status:** not executed

**Confirmatory status:** not executed

This document freezes the EXP-002 pre-calibration design. It authorizes no
calibration, candidate selection, or confirmatory execution in this slice.

## Scientific motivation and question

EXP-001 confirmed `C_GREATER`: calibrated energy-blind C SHORT 10/5 had a
greater mean capped lifespan than interoceptive B35 in the frozen
1000-transition simulator. EXP-001 descriptive observations and visual
inspection suggested the follow-up hypothesis that B35 may enter
`SEEK_RESOURCE` too late, leaving insufficient energetic return reserve after
ranging far from a resource. This is a hypothesis, not a causal conclusion
from EXP-001, because EXP-001 did not measure source distance at SEEK onset.

The EXP-002 question is:

> How does the interoceptive SEEK-entry energy threshold trade off viability
> against spatial exploration?

The candidates are B35 (0.35), B40 (0.40), B45 (0.45), and B50 (0.50), where
the value is the normalized-energy threshold below which B enters
`SEEK_RESOURCE`. B35 is the historical EXP-001 mechanism and remains
available unchanged.

## Frozen mechanism and environment

EXP-002 retains the EXP-001 frozen environment and all mechanisms except B's
SEEK-entry threshold:

- A behaviour is unchanged.
- C is unchanged: calibrated SHORT `EXPLORE 10 / CHARGE 5`.
- B recovery remains `energy > 0.85`.
- Resource contact remains `max(left, forward, right) >= 0.8`.
- The stochastic EXPLORE primitive, hazard, SEEK steering, and CHARGE
  behaviour remain unchanged.
- World, resource field, movement, energy physics, 1000-transition horizon,
  and sensory boundaries remain unchanged.
- No source coordinate, source distance, coverage, success state, or future
  outcome is exposed to B (or to A/C).
- The transition reward remains exactly `0.0`.

The evaluator may retain hidden position and source coordinates for metrics.
Those values remain outside controller observations and Gymnasium `info`.

## Evaluator-only spatial coverage

The evaluator uses a fixed 32×32 grid over the 1×1 world, for exactly 1024
cells. The start body position is marked before the first action. On each
`MOVE_FORWARD` transition, every grid cell intersected by the actual straight
segment from the pre-transition body position to the post-transition position
is marked. A turn or `WAIT` does not add path distance; it only marks the
occupied post-transition cell. A cell is counted once per episode.

The episode record reports `visited_cell_count`, `remaining_cell_count`, and
`coverage_fraction`. The grid is evaluator-only, deterministic, and consumes
no environment or policy RNG. A future visualizer may render it, but no
visualizer work is part of this slice.

## Evaluator-only return-reserve diagnostics

At every transition into `SEEK_RESOURCE`, the evaluator records:

- normalized energy immediately before the SEEK action;
- actual Euclidean distance to the nearest resource source immediately before
  that action;
- whether the SEEK attempt subsequently reaches `CHARGE` before termination;
- minimum normalized energy observed from SEEK onset through the attempt's
  terminal transition.

The episode summary also retains total EXPLORE action count, distance
travelled during EXPLORE, total unique coverage, unique cells reached during
EXPLORE, coverage efficiency per 100 EXPLORE actions, and complete recharge
cycles. Coverage efficiency is defined as
`100 × EXPLORE-only unique cells / EXPLORE action count`, and is zero when the
denominator is zero. A complete recharge cycle is the ordered mode sequence
`EXPLORE → SEEK_RESOURCE → CHARGE → EXPLORE`.

## Candidate-selection rule, frozen before simulation

No weighted viability/exploration score will be invented. For each candidate
on the same fresh matched calibration seeds:

1. A candidate is viability-eligible if at least 90% of episodes reach the
   1000-transition horizon.
2. If one or more candidates are eligible, select the eligible candidate with
   greatest mean unique spatial coverage.
3. If no candidate is eligible, select the candidate with highest
   horizon-survival fraction.
4. Tie-break in either selection path: greater mean unique spatial coverage,
   then lower SEEK-entry threshold.

This rule is declarative in this planning slice. No candidate is calibrated or
selected here.

## Seed reservations

The proposed seed reservations are new and distinct from EXP-001:

- calibration/development: **40001–40200 inclusive** (200 matched seeds);
- confirmatory: **50001–51000 inclusive** (1000 matched seeds).

These ranges are reserved in code and must remain untouched until the protocol
and instrumentation pass independent review. EXP-001 formal calibration seeds
20001–20200 and confirmatory seeds 30001–31000 are not EXP-002 calibration
evidence and are rejected by the EXP-002 development seed guard.

No reserved EXP-002 seed was executed in this slice.
