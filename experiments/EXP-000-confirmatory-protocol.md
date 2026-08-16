# EXP-000 Confirmatory Protocol

**Status:** Frozen before the first confirmatory acceptance run.

This protocol tests the narrow question whether informative access to the
engineered internal energy state improves capped viability relative to the
closely matched fixed-mask ablation. It does not test learning, intelligence,
consciousness, emotion, biological metabolism, genuine life, or evolution.

## Frozen execution contract

- `resource_length_scale = 0.40`
- `resource_count = 1`
- episode horizon: `500` transitions
- C `masked_energy = 0.5`
- B uses the unchanged transparent `HomeostaticConfig`.
- C uses the unchanged transparent controller configuration and replaces only
  the true normalized energy signal with the fixed mask above.
- B and C use the same environment seed and complete environment
  configuration for each matched pair.
- acceptance seeds are exactly `10001–10100`, yielding 100 matched B/C
  environments.
- No seed may be excluded or replaced based on its outcome.
- Once acceptance begins, there is no visualization, tuning using acceptance
  results, or additional calibration.

The complete environment configuration is: world bounds `(0.0, 0.0)` to
`(1.0, 1.0)`; maximum energy `10.0`; failure boundary `0.0`; initial energy
`5.0`; basal cost `0.1`; movement distance `0.05`; movement cost `0.1`;
turn angle `π/4`; turn cost `0.02`; wait cost `0.0`; probe distance `0.1`;
sensor angle `π/4`; harvest rate `0.5`; resource peak intensity `1.0`;
resource count `1`; resource length scale `0.40`; and horizon `500`.

The unchanged homeostatic controller configuration is:

- enter seek below normalized energy `0.35`;
- recover above normalized energy `0.85`;
- persistent exploration cadence of 8 forward actions followed by a left turn.

The observation/action boundary and evaluator-only telemetry remain those
defined by the accepted EXP-000 ADRs. Reward remains exactly `0.0` on every
transition.

## Primary endpoint and support criterion

For acceptance seed `i`, define:

`D_i = capped_lifespan_B_i − capped_lifespan_C_i`

where each lifespan is the number of executed transitions, capped by the
500-step horizon. The primary estimate is the arithmetic mean of the 100
paired differences.

The primary uncertainty procedure is fixed:

1. Resample the 100 complete matched B/C seed pairs with replacement.
2. Calculate the mean paired difference for each resample.
3. Use exactly 100,000 resamples.
4. Use NumPy `default_rng(0)` for resampling.
5. Form the two-sided 95% percentile interval from the 2.5th and 97.5th
   percentiles using NumPy quantile method `linear`.

EXP-000 obtains confirmatory support if and only if both conditions hold:

- the observed mean B−C difference is strictly greater than `0`; and
- the lower bound of the frozen two-sided 95% bootstrap interval is strictly
  greater than `0`.

If either condition fails, EXP-000 does not obtain confirmatory support in
this run. No secondary metric may rescue the primary endpoint.

## Descriptive-only diagnostics

The report may include, without changing support status:

- median paired lifespan difference;
- counts of B>C, B=C, and B<C seed pairs;
- B and C mean and median capped lifespan;
- horizon-survival counts and fractions;
- energy, harvest, and movement diagnostics already present in the artifact.

These diagnostics explain the primary result but are not alternate primary
outcomes.

## Interpretation limit

The ceiling at 500 limits interpretation to capped 500-step viability. A
horizon-surviving episode does not establish an uncensored survival duration
beyond the horizon.
