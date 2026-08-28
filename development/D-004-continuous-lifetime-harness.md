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

## Execution

The deterministic infrastructure equivalence check was run from clean
executable Commit B
`60e2b8b86d64f93819d3f3c50b38bee53874322a`, using only legal development
seeds `18141`, `18142`, and `18143`. No formal, reserved, calibration,
confirmatory, acceptance, or otherwise reserved seed was used.

The evaluator-only public seam is:

```python
environment.evaluator_set_geometry_and_observe(
    body_position=...,
    station_center=...,
    heading=None,
) -> np.ndarray
```

It is implemented on `D002ThermalStationEnv`. It positions evaluator geometry,
preserves the current heading when `heading=None`, optionally sets an explicit
diagnostic heading, and returns the current six-channel observation. It does
not execute a transition, create reward, reset or reseed, touch controller
state, or change energy, thermal state, transition index, or environment RNG.

D-003 optionally collects one evaluator-only `D003TraceEntry` per existing
transition. The trace contains transition index, action, post-transition
position and heading, energy, thermal state, charging contact, controller mode,
and termination flags. `partition_trace` slices the completed trace into
post-hoc windows; it does not execute, reset, reseed, or expose window metadata
to the controller.

## Direct observations

- The evaluator setup seam tests changed only requested geometry, preserved
  heading with `None`, preserved energy, thermal state, transition index, and
  RNG state, executed no action, and matched the legacy six-channel
  observation exactly.
- The refactored D-003 CLI output was an exact JSON match to the pre-change
  D-003 baseline for all three development seeds.
- Each seed produced 1000 transitions, no termination, horizon truncation, and
  13 completed shuttle cycles.
- Each uninterrupted trace contained 1000 entries. Partitioning into 100-step
  windows produced 10 windows; partitioning into 137-step windows produced 8
  windows. Flattening either partition reproduced the original trace exactly,
  including action, controller mode, energy, thermal, contact, and terminal
  fields.
- Trace collection and post-hoc windowing caused one ordinary environment reset
  and one ordinary controller reset at lifetime start, with no additional
  reset/reseed at logging or window boundaries.

The known floating-point sensitivity around the inclusive `0.10` charging
radius after nominally two `0.05` moves is retained as part of the existing
D-003 regression target. D-004 does not change charging radius, movement
distance, contact comparison, geometry, or thresholds.

## Engineering inference

The exact CLI match and trace flattening checks show that the seam and
post-hoc presentation partitions are causally inert relative to the existing
D-003 execution. The trace is a compact evaluator representation suitable for
future development-only visualization without adding a new organism channel,
action, dynamic, learner, or checkpoint boundary.

The initial implementation draft attempted to read position from D-002
telemetry, which intentionally does not expose position. The draft failed its
focused test, was corrected to read the already-validated evaluator body
position after the transition, and was not included in Commit B. No mechanism
or result was changed by that correction.

## Scientific implication

The V0.3 development harness can now position and observe the current ecology
through an explicit evaluator-only seam, and evaluator logging/visualization
windows can be derived from one continuous lifetime without altering organism
causality.

This is infrastructure equivalence, not confirmatory evidence. The result
does not establish learning, plasticity, thermal-interoception necessity,
generalization, consciousness, emotion, subjective experience, genuine life,
or biological equivalence.

## Disposition

`CONTINUING`.
