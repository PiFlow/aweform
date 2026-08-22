# EXP-002 — Confirmatory Statistical Addendum

**Status:** frozen statistical convention; EXP-002 confirmatory execution
remains unauthorized until this addendum is independently reviewed and merged

This addendum freezes the EXP-002 confirmatory statistical convention. It does
not execute or analyze confirmatory seeds, and it does not modify the frozen
[`EXP-002 precalibration protocol`](EXP-002-interoceptive-seek-threshold.md)
(protocol SHA-256 `18875e9e97221db0dcb7acb1ee50d9dc6546dd619d9f871430801335455f77d1`,
as recorded in [`EXP-002 calibration evidence`](EXP-002-calibration-result.md))
or the completed calibration artifact it governs. The protocol's own "Calibration
status: not executed" / "Confirmatory status: not executed" wording is
historical preregistration-time state, as of that document's freeze; it is
not current project status. Calibration has since completed and selected
**B50**; this addendum specifies the confirmatory design that follows from
that result. The confirmatory seeds are `50001–51000`, unexecuted in this
documentation-only slice.

## Calibration and confirmatory boundary

Unlike `EXP-001-confirmatory-statistical-addendum.md`, which froze EXP-001's
statistical convention before calibration had run, this addendum is written
**after** EXP-002 calibration completed and B50 was selected, and **before**
any EXP-002 confirmatory seed has been touched. The confirmatory primary
contrast below (B50 vs. `C_SHORT`) is therefore a **post-calibration
confirmatory question**: it uses the calibration outcome (which candidate was
selected) as an input, but was not preregistered before calibration ran, and
this addendum does not retroactively imply that it was. The key secondary
contrast (B50 vs. B35) is added for the same reason and under the same
disclosure.

B50 was selected by EXP-002's frozen rule for maximum mean spatial coverage
among viability-eligible candidates (`horizon_survival_count >= 180/200`),
not for competitiveness against C. It is the upper tested boundary of the
four-point grid (B35/B40/B45/B50), not an exhaustive search. Whatever this
confirmatory comparison finds is a statement about that specific,
coverage-selected candidate, not about the best possible B threshold.

## Primary and key-secondary estimands

The primary causal comparison is B50 versus the frozen EXP-001 `C_SHORT`
comparator (calibrated SHORT, EXPLORE `10`, CHARGE `5`) on the 1000 untouched
matched confirmatory seeds `50001–51000`. The key secondary is B50 versus
historical B35 on the same seeds. Every confirmatory seed produces a matched
**triple**: B50, `C_SHORT`, and B35, executed under the frozen EXP-002
environment and mechanism (identical to EXP-001's except B's SEEK-entry
threshold).

For matched seed `i`, define:

```
D_primary_i   = capped_lifespan_B50_i - capped_lifespan_C_i
D_secondary_i = capped_lifespan_B50_i - capped_lifespan_B35_i
```

where capped lifespan is the number of completed transitions before
loss-of-viability termination, capped at the frozen 1000-transition horizon.
The primary aggregate estimand is `mean(D_primary_i)`; the key-secondary
aggregate estimand is `mean(D_secondary_i)`, both over the 1000 matched
confirmatory seeds. As in EXP-001, an episode reaching the horizon has an
observed capped lifespan of 1000 with unknown survival beyond it; EXP-002
makes no claim about expected lifetime beyond the frozen horizon, and no
claim beyond the frozen 1000-transition EXP-002 environment.

The primary estimand answers whether calibrating B changes, reverses, or
narrows EXP-001's `C_GREATER` result. The key secondary answers whether
calibrating the SEEK-entry threshold improved B's own mechanism, independent
of how it compares to C. The key secondary does not redefine, replace, or
average into the primary result, and does not become a second co-primary
success criterion.

## Paired bootstrap convention

The resampling unit is the matched seed, represented by one triple of
outcomes (B50, `C_SHORT`, B35). No condition within a seed is ever resampled
independently of the other two. This addendum freezes its own bootstrap
convention rather than inheriting EXP-000's (100,000 replicates,
`numpy.random.default_rng(0)`) or EXP-001's (50,000 replicates,
`numpy.random.Generator(numpy.random.PCG64(91001))`) — those conventions are
specific to their own experiments and must not be assumed to transfer.

The bootstrap generator is `numpy.random.Generator(numpy.random.PCG64(50101))`.
It is initialized once for the entire bootstrap and continuously advances
across all `100_000` replicates. EXP-002 must not rely on an unnamed
implementation default such as `numpy.random.default_rng(50101)` without
naming its `BitGenerator`.

The fixed procedure is:

- number of confirmatory seeds: `1000`;
- bootstrap replicates: `100_000`;
- deterministic bootstrap RNG seed: `50101`, using the generator specified
  above;
- for each replicate, using that one continuously advancing generator, draw
  exactly `1000` integer indices uniformly from `[0, 1000)` with replacement
  (equivalently, `rng.integers(0, 1000, size=1000)`);
- use the **same sampled indices, for that replicate, to select both**
  `D_primary_i` **and** `D_secondary_i` for the selected seeds — the two
  bootstrap distributions are computed from one shared resampled sequence of
  seed indices, not independently, so the estimated covariance between the
  two estimands is preserved;
- calculate that replicate's arithmetic mean of each of `D_primary` and
  `D_secondary`;
- use a `95%` confidence level; and
- use an ordinary two-sided **percentile bootstrap** interval for each
  estimand, with the lower bound computed as
  `numpy.percentile(bootstrap_means, 2.5, method="linear")` and the upper
  bound computed as `numpy.percentile(bootstrap_means, 97.5, method="linear")`.

Exactly equivalent `numpy.quantile` calls with `method="linear"` are also
permitted. No other percentile or quantile interpolation method may be
selected after confirmatory data are observed. EXP-002 does not use BCa,
studentized bootstrap, one-sided intervals, or adaptive resampling. The
interval convention must not be selected after confirmatory data are
observed.

## Primary interpretation

Fixed before confirmatory execution, for the primary estimand only:

- If the interval is entirely above zero, interpret as support for: **B50 has
  greater mean capped lifespan than calibrated `C_SHORT` within the frozen
  1000-transition EXP-002 environment.**
- If the interval is entirely below zero, interpret as support for:
  **calibrated `C_SHORT` has greater mean capped lifespan than B50 within the
  frozen 1000-transition EXP-002 environment.** This is a scientifically
  valid outcome and must not trigger redesign or rerunning EXP-002.
- If the interval includes zero, interpret as: **EXP-002 does not resolve a
  directional difference in mean capped lifespan between B50 and calibrated
  `C_SHORT` within the frozen 1000-transition environment.** This is not
  proof of equality.

None of these three outcomes is presupposed. In particular, a below-zero or
zero-including interval is not evidence that calibration "failed" — it is
information about whether B calibration alone explains EXP-001's result,
which is exactly the open question this addendum exists to close.

## Key-secondary reporting

The key-secondary estimand (`mean(D_secondary_i)`) is reported with its own
effect estimate and the same 95% percentile-bootstrap interval convention
above. It receives a descriptive directional reading (B50 above/below/
indistinguishable from B35) but no independent headline support rule of its
own — the primary interpretation above is the only formal confirmatory
conclusion this addendum authorizes. The key secondary must not be promoted
to co-primary or used to override the primary reading after data are
observed.

## Primary reporting and descriptive diagnostics

EXP-002 has no primary null-hypothesis p-value. The primary reported
quantities are: mean paired capped-lifespan difference for `D_primary`; its
95% paired percentile-bootstrap interval; the same two quantities for
`D_secondary`; and the number of matched confirmatory seeds. Existing
protocol diagnostics (horizon-survival fractions, spatial coverage,
SEEK-onset energy and source distance, complete recharge cycles, and the
other fields already recorded by EXP-002's episode instrumentation) remain
descriptive only and must not replace or redefine the primary or key-secondary
endpoint, and must not be promoted to primary after results are observed.

## Scope

This addendum makes no use of the confirmatory seeds `50001–51000`; they
remain untouched until this addendum is independently reviewed and merged.
It does not change the EXP-002 environment, controllers, candidate grid, or
calibration result. It does not authorize execution by itself — a separate
execution/analysis implementation (an `exp002_confirmatory` module analogous
to `exp001_confirmatory`) is required before these seeds may be run.
