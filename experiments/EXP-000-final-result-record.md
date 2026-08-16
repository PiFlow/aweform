# EXP-000 Final Result Record — Interoception and Viability

**Status:** Completed — confirmatory support obtained

This is the final research record for EXP-000. It records the frozen
confirmatory result and its interpretation boundaries. The confirmatory
artifact and generated analysis are identified by fingerprint below; neither
is regenerated or modified by this record.

## Scientific question

EXP-000 asked whether informative access to internal energetic state improves
viability relative to an otherwise closely matched fixed-mask, energy-blind
controller in the frozen simulated environment.

The primary causal contrast was `B_HOMEOSTATIC` versus `C_ENERGY_BLIND`.
Both were programmed transparent controllers; no learning or reward
optimisation occurred, and Gymnasium reward remained exactly `0.0` on every
transition. The result concerns the programmed homeostatic mechanism and
this specific fixed-mask ablation.

## Confirmatory provenance and frozen analysis

- Execution Git SHA: `acbe5feaddc6df813c0f1f6c710250d010f11c6d`
- Acceptance seeds: `10001–10100`
- Matched B/C pairs: `100`
- `resource_length_scale = 0.40`
- `resource_count = 1`
- Episode horizon: `500`
- C masked energy: `0.5`
- B enter-seek threshold: `0.35`
- B recovery threshold: `0.85`
- Persistent exploration cadence: 8 forward actions, then one left turn
- Primary endpoint: mean paired `capped_lifespan_B - capped_lifespan_C`
- Bootstrap: `100,000` paired resamples
- RNG: NumPy `default_rng(0)`
- Interval: two-sided 95% percentile bootstrap CI
- NumPy quantile method: `linear`
- Support rule: observed mean `> 0` **and** lower CI bound `> 0`

The analysis procedure and support rule were frozen before acceptance
execution.

## Immutable result fingerprints

- Confirmatory artifact: `7a56953793fa9b1da99aa01e92232ecd4ee33f1a4338134d4cdd7906983e0083`
- Confirmatory analysis: `046a2290608546ec68e0bf10329be2e1078c784105df441b5a2c382773fc7f2c`

These hashes are the repository record. The raw confirmatory JSON and
generated analysis file are not copied into this result record.

## Primary confirmatory result

- Mean paired B−C capped-lifespan difference: `145.250000` steps
- Frozen 95% bootstrap CI: `[106.109750, 185.750000]` steps
- Confirmatory support: **YES**

The preregistered criterion was met because the observed mean difference was
positive and the lower bound of the frozen 95% interval was strictly greater
than zero.

## Descriptive diagnostics

| Diagnostic | B | C |
| --- | ---: | ---: |
| Mean capped lifespan | 500.000000 | 354.750000 |
| Median capped lifespan | 500.000000 | 500.000000 |
| Horizon survival | 100/100 (1.000) | 63/100 (0.630) |
| Mean harvested energy | 106.261674 | 71.758812 |
| Mean basal energy cost | 50.000000 | 35.475000 |
| Mean action energy cost | 44.683200 | 32.363000 |
| Mean distance travelled | 20.838591 | 15.292558 |

- Paired B>C / B=C / B<C: `37 / 63 / 0`
- Median paired lifespan difference: `0.000000` steps

The zero median is explained by the 63 of 100 matched pairs in which both
conditions reached the 500-step ceiling. In the remaining 37 pairs, B
outlasted C. No pair had C outlast B. These diagnostics are descriptive only
and do not replace the primary endpoint.

## Scientific conclusion

Under the frozen EXP-000 simulated environment and fixed-mask ablation,
informative access to internal energetic state causally improved capped
500-step viability for the programmed homeostatic controller.

Within this engineered perception-action-energy system, informative energetic
interoception was causally useful: access to actual energy allowed the
programmed homeostatic mechanism to change behaviour in response to energetic
state. The positive result survived the untouched 100-seed confirmatory
evaluation under the preregistered analysis.

## Interpretation boundaries

### Horizon censoring

B reached the 500-step horizon in all 100 acceptance episodes. EXP-000
therefore does **not** estimate B's uncensored survival duration. It
establishes an effect on **capped 500-step viability**, not how long B would
survive beyond 500 steps.

### Specific ablation

C used fixed masked energy `0.5`. Under the frozen thresholds `0.35` and
`0.85`, that fixed value does not itself trigger the energy-dependent
low-energy seek transition. The result is therefore specific to actual
energetic interoception versus this frozen fixed-mask ablation. It must not be
generalised to every possible non-informative, delayed, shuffled, noisy, or
otherwise corrupted interoceptive signal.

### No broader life or intelligence claim

EXP-000 does **not** demonstrate:

- consciousness or subjective experience;
- desire to survive;
- intelligence, learning, or planning;
- curiosity or emotion;
- biological metabolism or biological life;
- general artificial life;
- evolution or a general survival instinct.

It demonstrates a narrow causal property of the engineered homeostatic
system.

## Calibration and protocol history

- [EXP-000 Calibration Round 1 Result Record](EXP-000-calibration-round-1-record.md)
- [EXP-000 Calibration Round 2 Result Record](EXP-000-calibration-round-2-record.md)
- [EXP-000 Confirmatory Protocol](EXP-000-confirmatory-protocol.md)

Round 1 had no qualifying environment. Round 2 mechanically selected
`resource_length_scale = 0.40`. The acceptance set remained untouched until
after the confirmatory protocol and analysis were frozen.
