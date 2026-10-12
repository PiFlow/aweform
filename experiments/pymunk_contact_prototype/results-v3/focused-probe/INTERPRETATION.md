# Interpretation — v3 focused contact falsifier

**Disposition: Stage 1 PASS; proceed-to-full-probe condition met.** This was a non-acceptance falsifier, not Essential B. It did not authorize a lifetime.

## Provenance and execution

- Frozen executable: `a0f3b3f4fac58d88a9ea0b1b706583ce3865639d`
- Frozen protocol SHA-256: `6db905f6e6cd1501829ddb7e2f7f72bb9fc35ed1ea037ba9e12231ef1b455162`
- Focused result SHA-256: `6e0e4c0b7a1d99262d472eda4ee8897b7fc3943f3a46ed81f089fb3fd4945afb`
- Exactly 132,000/132,000 engine steps ran in 26.598 s. All predeclared Stage-1 gates passed.

## Outcomes

The 19th `wall-west-head-on` command's sampled penetration was 0.207045 mm at 400 microsteps versus the 0.2115 mm forecast, and 0.149655 mm at 800 versus the 0.1558 mm forecast. Both are within the frozen ±10% falsifier bands. Maximum conservative penetration in the probe was 0.212671 mm at 400 and 0.156330 mm at 800; both are below the unchanged 1 mm limit. The focused contact cases, convergence, reset, sampling-bound, crossing, identity, and finite-output checks passed.

These results met the predeclared condition to run the one full fixed-command check. They are not, by themselves, acceptance evidence. The full result and its interpretation are recorded separately. V1 and v2 results remain preserved and unchanged. No lifetime ran.
