# EXP-001 — Confirmatory Statistical Addendum

**Status:** frozen statistical convention; formal calibration remains
unauthorized until this addendum is independently reviewed and merged

This addendum freezes the remaining EXP-001 confirmatory statistical
convention. It does not execute or analyze calibration or confirmatory seeds,
and it does not change the controllers, environment, candidate grid, seed
ranges, or EXP-000. The formal calibration seeds are `20001–20200`; the
confirmatory seeds are `30001–31000`. Both sets remain unexecuted in this
documentation-only slice.

## Primary estimand

The primary causal comparison is B versus calibrated C on the 1000 untouched
matched confirmatory seeds `30001–31000`.

For matched seed `i`, define:

`D_i = capped_lifespan_B_i - capped_lifespan_C_i`

where capped lifespan is the number of completed transitions before
loss-of-viability termination, capped at the frozen horizon of 1000
transitions. The primary aggregate estimand is:

`mean(D_i)`

over all 1000 matched confirmatory seeds. This is a **1000-transition
restricted/capped viability endpoint**. An episode reaching the horizon has an
observed capped lifespan of 1000, but its possible survival beyond 1000 is
unknown. EXP-001 therefore makes no claim about expected lifetime beyond the
frozen horizon.

## Paired bootstrap convention

The resampling unit is the matched seed pair, represented by one paired
difference `D_i`. B and C episodes must never be resampled independently.

The fixed procedure is:

- number of confirmatory pairs: `1000`;
- bootstrap replicates: `50_000`;
- deterministic bootstrap RNG seed: `91001`;
- for each replicate, sample `1000` indices with replacement from the `1000`
  paired `D_i` values;
- calculate the replicate mean paired difference;
- use a `95%` confidence level; and
- use an ordinary two-sided **percentile bootstrap** interval, with the lower
  bound equal to the empirical 2.5th percentile and the upper bound equal to
  the empirical 97.5th percentile.

EXP-001 does not use BCa, studentized bootstrap, one-sided intervals, or
adaptive resampling. The interval convention must not be selected after
confirmatory data are observed.

## Primary interpretation

The interpretation is fixed before confirmatory execution:

- If the interval is entirely above zero, interpret the result as support for:
  **B has greater mean capped lifespan than calibrated C within the frozen
  1000-transition environment.** This does not generalize beyond that
  environment or horizon.
- If the interval is entirely below zero, interpret the result as support for:
  **calibrated C has greater mean capped lifespan than B within the frozen
  1000-transition environment.** This is a scientifically valid outcome and
  must not trigger redesign or rerunning EXP-001.
- If the interval includes zero, interpret the result as: **EXP-001 does not
  resolve a directional difference in mean capped lifespan between B and
  calibrated C within the frozen 1000-transition environment.** This is not
  proof of equality.

## Primary reporting and descriptive diagnostics

EXP-001 has no primary null-hypothesis p-value. The primary reported
quantities are:

- mean paired capped-lifespan difference;
- two-sided 95% paired percentile-bootstrap interval; and
- number of matched confirmatory seeds.

The existing protocol's secondary/descriptive diagnostics remain descriptive
only. After confirmatory execution, they may include B>C / B=C / B<C
paired-seed counts; horizon-survival fractions; final energy; minimum energy;
harvested energy; action costs; distance travelled; time in `EXPLORE`,
`SEEK_RESOURCE`, and `CHARGE`; and completed recharge cycles.

These diagnostics must not replace or redefine the primary endpoint. EXP-001
does not create a composite exploration/efficiency score or promote a
secondary diagnostic to primary after results are observed.

## Calibration boundary and prior expectation

This addendum makes no use of calibration outcomes. Formal calibration remains
limited to the already frozen C-only candidate-selection protocol and seeds
`20001–20200`; those seeds must not be executed in this PR. After this
addendum is independently reviewed and merged, formal calibration may be
authorized under that protocol. The confirmatory seeds `30001–31000` remain
completely untouched until the full EXP-001 contract is authorized.

Any informal development expectation that conservative C may survive well in
this stationary environment is only a qualitative pre-result expectation. It
must not alter the bootstrap, interval interpretation, candidate selection,
confirmatory endpoint, or reporting threshold. No expected winner is encoded
in the formal statistical decision rule.
