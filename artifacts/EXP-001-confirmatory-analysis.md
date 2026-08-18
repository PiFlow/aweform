# EXP-001 Confirmatory Analysis

This report was generated from an already-persisted confirmatory artifact. It did not execute the simulator.

- Source artifact SHA-256: `b93958d173eaf80eb83a1c6dde485390d7b222d9cd0007837bf71952873b4627`
- Git SHA recorded in artifact: `940e355bd16a28b372bd042de931c3a57366599b`
- Source execution NumPy: `2.5.2`
- Analysis/bootstrap NumPy: `2.5.2`
- Matched pairs: `n = 1000`
- A status: descriptive reference only; excluded from the primary difference, bootstrap, and interpretation

## Primary endpoint

The frozen primary estimand is the mean paired `capped_lifespan_B - capped_lifespan_C` difference.

- Mean paired B−C difference: `-125.765000` transitions
- 95% paired percentile-bootstrap interval: `[-142.812125, -108.906000]` transitions
- Interpretation: `C_GREATER`
- Bootstrap: `50,000` paired-difference resamples; `Generator(PCG64(91001))`; percentile method `linear`
- No primary p-value is calculated.

## Descriptive diagnostics

The following are descriptive only and cannot replace or reinterpret the B−C primary endpoint.

- Matched B>C / B=C / B<C counts: `22 / 734 / 244`

| Condition | Mean lifespan | Median lifespan | Horizon survivors | Mean final energy | Mean minimum energy | Mean harvested | Mean basal cost | Mean action cost | Mean distance | Mean EXPLORE | Mean SEEK_RESOURCE | Mean CHARGE | Mean complete cycles |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A_PERSISTENT_EXPLORATION | 69.343 | 43.000 | 0 (0.000) | 0.000000 | 0.000000 | 8.424231 | 6.934300 | 6.062540 | 1.938746 | 69.343 | 0.000 | 0.000 | 0.000 |
| B_INTEROCEPTIVE_HOMEOSTASIS | 848.047 | 1000.000 | 735 (0.735) | 0.510608 | 0.068013 | 163.579301 | 84.804700 | 56.994080 | 18.930118 | 563.944 | 111.056 | 173.047 | 5.943 |
| C_ENERGY_BLIND_HOMEOSTASIS | 973.812 | 1000.000 | 973 (0.973) | 0.969137 | 0.314640 | 320.378549 | 97.381200 | 55.166080 | 23.634484 | 500.850 | 225.618 | 247.344 | 43.925 |

Inference is limited to the frozen 1000-transition simulator environment. It is not evidence about biological organisms, a physical Aweform, consciousness, or lifetime beyond 1000 transitions.
