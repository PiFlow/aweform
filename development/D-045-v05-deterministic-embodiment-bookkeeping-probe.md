# D-045 — V0.5 deterministic differential-drive embodiment and bookkeeping probe

- **id:** D-045
- **issue:** [#161](https://github.com/PiFlow/aweform/issues/161)
- **lane:** Development / evaluator-scripted substrate validation
- **date:** 2026-09-23
- **authorized_base_sha:** `3cefcc0c613c1cc7fffaa3217a7666010e7af449`
- **exact_sha:** `7faa86a7f32ec6a77ed08d26ce23977d88831067` (frozen executable/protocol)
- **final_pr_head_sha:** recorded in the handoff after record/artifact commit
- **development_seeds:** seedless fixed-state probes; no formal reservation used
- **disposition:** `CONTINUING`

The compact machine-readable artifact is
[`D-045-v05-deterministic-embodiment-bookkeeping-probe.json`](D-045-v05-deterministic-embodiment-bookkeeping-probe.json).
It is a descriptive Development artifact, not confirmatory evidence.

## Question and frozen boundary

D-045 asks whether the accepted ADR 0017 first-slice V0.5 substrate is
deterministic and internally consistent before any learner is introduced.
The additive implementation provides one bilateral desired wheel-delta action,
exact differential-drive arc integration, deterministic common-scaling body
centre boundary reduction, a centred corresponding dual-contact dock, retained
station-centred L/F/R beacon semantics, two signed finite-resolution completed
wheel-delta channels, and continuous actuator bookkeeping.

The frozen action envelope is independently clamped to
`[-0.6457718232379019, +0.6457718232379019]` radians per wheel per `0.1 s`.
The wheel track width is `0.185 m`, wheel radius is `0.045 m`, world bounds are
`[0, 1] × [0, 1]`, and no collision or swept-path semantics are added.  The
dock contacts are body/station frame `(0, +0.050)` and `(0, -0.050)` with
corresponding inclusive `0.010 m` errors only.  The encoder quantum is
`pi/180 rad`, labelled an **ENGINEERING ESTIMATE**, with nearest-count ties
rounded away from zero.

The eight visible channels, in order, are normalized electrical energy,
normalized body temperature, beacon left/forward/right, binary physical
dual-contact, and quantized signed completed left/right wheel deltas.
Continuous actual deltas, pose, heading, pair errors, boundary scale, battery,
charger, thermal, and termination diagnostics remain evaluator-only.  Every
transition returns reward `0.0` and `info == {}`.  There is no learner,
controller, calibration curriculum, semantic action, planner, reward shaping,
or new actuator RNG.

Wheel electrical power is the frozen continuous `1.0 W × effort`, where effort
is the mean absolute actual wheel magnitude divided by the maximum magnitude.
Wheel actuator body heat is `0.0 W`; retained electronics, charger, battery,
thermal, and ADR 0014 threshold semantics remain separate and unchanged.

## Frozen evaluator probes

The executable freeze contains the exact numeric table and compact schemas for
kinematics/action semantics (zero, bilateral forward/reverse, both in-place
rotations, both one-wheel arcs, encoder-scale commands, and over-range
clamping), all four world edges plus a corner, exact/inside/outside/polarity
docking, a translation through station centre, retained charging/taper/latch,
observation closure, continuous bookkeeping invariants, deterministic replay,
and structural feasibility.  The structural check uses the fixed raw sequence
of seven equal-wheel commands from `(0.30, 0.50)` to station `(0.50, 0.50)`;
it is not a controller or search procedure.

## Observed

- The official artifact was generated from the frozen executable/protocol SHA
  above and is `21,223` bytes with SHA-256
  `833f1f60edef06ecfcefcad1ba5b8ac9fdcc5a9cac531bacbd8f41ffe71315fe`.
- Independent regeneration with the same module command was byte-identical,
  with the same size and hash.  The replay probe also produced a byte-identical
  four-transition trace.
- The structural-feasibility result is `true`: the fixed seven-command path
  establishes dual contact at `(0.50, 0.50)`, ends at `23.000697287864895 C`,
  and retains `2663.391762408252 J` from a below-full `2664.0 J` start.
- The retained docked zero-wheel charge probe ran `30,000` transitions without
  termination.  The battery ended at `5299.214999999372 J`; the first full
  latch occurred at step `28,081`; maximum temperature was
  `24.172935197773615 C`; phase counts are BULK `12,537`, TAPER_1 `3,437`,
  TAPER_2 `12,107`, STANDBY `1,919`, OFF `0`.
- The continuous bookkeeping invariants passed: zero command has zero actuator
  power, sign reversal and wheel swap are symmetric, full bilateral magnitude
  is `1.0 W`, one saturated wheel is `0.5 W`, and actuator body heat is zero.
- No new actuator RNG exists or is consumed.  No organism-visible evaluator
  pose, heading, geometry, pair error, saturation, or success label is present.

## Surprised by

Nothing invalidated the frozen substrate.  The retained V0.4 charge/thermal
values reproduce the prior fixed-state accounting scale while the new wheel
load remains continuous and boundary-reduced.  This is a substrate result,
not evidence that a later learner can solve docking.

## Provisional reading and next

The implementation is descriptively internally consistent for the declared
first slice and passes its structural-feasibility gate.  The result does not
establish hardware performance, metabolism, learning, intelligence,
consciousness, or a behavioural docking capability.  The next permitted work
is governed by a separate authorization; this record does not start D-046.

## Validation

Focused D-045 tests: `18 passed`.  Strict mypy, Ruff, compile/import checks,
and `git diff --check` passed.  Historical D-020 through D-044 source,
records, artifacts, and replay semantics were not modified.
