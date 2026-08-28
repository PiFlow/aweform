# D-004 — Continuous-lifetime harness consolidation

- **id:** D-004
- **date:** 2026-08-28
- **disposition:** `CONTINUING`

## Question

Can the smallest explicit evaluator-side harness seam support continued V0.3
development while preserving D-003 behaviour and keeping logging/visualization
boundaries outside organism causality?

This is infrastructure work. It introduces no new behavioural challenge and
makes no confirmatory claim.

## Predeclared invariants

### Lifetime invariant

One organism lifetime is one uninterrupted causal trajectory. Logging, tracing,
visualization, and aggregation boundaries are evaluator-only. They cannot:

- reset the environment or controller;
- reseed anything;
- change the action sequence or future observations;
- enter controller input;
- expose a segment/window identifier or boundary-derived clock.

Trace windows are derived after the continuous lifetime has executed. They are
presentation/analysis partitions, not execution segments or checkpoint
boundaries.

### D-003 preservation invariant

The existing D-003 mechanism remains unchanged:

- thresholds `0.60` / `0.30`;
- four return turns;
- thermal plus charging-contact controller observation only;
- unchanged D-002 ecology;
- the same post-contact evaluator setup, development seeds, and horizon.

D-004 does not tune or reinterpret D-003.

### Harness-seam invariant

Evaluator positioning and current-observation refresh use one explicit,
inspectable public seam on `D002ThermalStationEnv`. The seam is evaluator-only:
it is not an organism action or observation channel, executes no transition,
and does not touch controller state.

The seam may change only evaluator-requested geometry. It preserves heading when
no heading is provided, and always preserves energy, thermal state, transition
index, and environment RNG state.

## Scope boundary

D-004 adds no learner, plasticity, adaptive gain, predictor, new sensor, new
action, thermal mechanism, reward, checkpointing, serialization, save/resume,
restart, or future-agent framework. It does not modify historical EXP-003 or
the executed D-003 record at `34310d2c3f4198aadd74d030b610142d23d99e24`.

## Execution status

Pending the clean Commit B implementation and deterministic development-seed
equivalence checks. Only legal development seeds `18141`, `18142`, and `18143`
will be used. The known floating-point sensitivity around the inclusive `0.10`
charging radius after nominally two `0.05` moves is retained as part of the
existing D-003 regression target, not fixed by D-004.

## Disposition

`CONTINUING`.
