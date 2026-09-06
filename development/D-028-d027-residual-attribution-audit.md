# D-028 — D-027 residual-attribution audit

- **id:** D-028
- **lane:** Development
- **authoritative_base_sha:** `19cb4ebd8c6f2df7013865087689cff3d3803a33`
- **development_seeds:** `18388..18407` inclusive (the already-observed D-027 support)
- **horizon:** `70,000` transitions per uninterrupted lifetime
- **status before execution:** protocol frozen; substantive output pending
- **disposition:** `CONTINUING`

The machine-readable numerical source is
[`D-028-d027-residual-attribution-audit.json`](D-028-d027-residual-attribution-audit.json).
The reused D-027 reference artifact is
[`D-027-shadow-sensorimotor-consequence-learning.json`](D-027-shadow-sensorimotor-consequence-learning.json).

## Question and scope

D-028 asks why the unchanged D-027 shadow learner was weak on charging-contact
and boundary-clipped beacon consequences: online normalized-LMS dynamics,
linear visible representation, or omitted world-frame state / partial
observability. This is an evaluator-only Development-lane diagnosis of
already-observed D-027 support. It is not fresh evidence and does not alter
the organism, controller, learner, sensors, actions, ecology, physics, reward,
or behaviour.

The causal replay is the exact D-027 `d027._run_lifetime` path: D-026 one-third
SEEK delegation, explorer hazard one-eighth, D-024 dual-contact geometry,
D-020 bookkeeping, six visible channels, four actions, zero reward, empty
`info`, and the 168-weight executed-action normalized-LMS learner. New work is
performed only after completed D-027 traces are available.

## Frozen protocol

Before substantive output, the following definitions were committed in the
D-028 executable source and focused tests:

- exact ordered seeds `18388..18407`, canonical development-seed guard, and
  exact horizon `70_000`;
- exact visible-key alias census using Python float values from the six
  ordinary float32 channels plus exact executed action; no rounding, epsilon,
  binning, hidden state, mode, seed, or transition index; a singleton is
  `untested`, never stable;
- linear batch OLS basis
  `[1.0, energy, beacon.left, beacon.forward, beacon.right,
  float(charging_contact), thermal]`, dimension `7`;
- quadratic basis with bias, the six channels, then `v[i] * v[j]` for
  `0 <= i <= j < 6` in lexicographic order, dimension `28`;
- deterministic two-fold seed-parity cross-fitting: fit EVEN and score ODD,
  then fit ODD and score EVEN; no leakage, weighting, standardization,
  regularization, tuning, or randomness; `numpy.linalg.lstsq(..., rcond=None)`;
- boundary tolerance `1e-12`, with full nominal, boundary-clipped, and nested
  full-stall `MOVE_FORWARD` labels;
- D-016 inverse `d = beacon_scale * sqrt(1 / signal - 1)` and its exact
  current beacon constants; nominal beacon-only no-clamp forward oracle;
- heading-augmented wall-aware oracle using only decoded current relative
  geometry, current pre-action true heading, fixed station/bounds/kinematics,
  and D-024 contact geometry; post-action truth is scoring data only;
- MAE as the primary continuity metric, with support, contact-event,
  geometry, oracle, coefficient, rank, singular-value, and conditioning
  diagnostics retained compactly; no binary scientific pass threshold;
- interpretation order: online-learning dynamics, linear representation,
  omitted-state/partial-observability, then unresolved ambiguity. A result
  does not authorize a new sensor, history, larger learner, or behaviour
  control.

No substantive D-028 output was inspected when this protocol was frozen.

The first substantive run from frozen executable SHA
`b4f8845799f8dd90af71924ad41d63e63260b33b` was invalidated after inspection
found a reporting defect: the alias serializer retained every exact-key record,
including approximately 1.4 million singleton/non-aliased records, producing a
4.3 GiB artifact. The invalidated artifact SHA-256 is
`010f635f618c9c4ae6519a1d9c7dbf086a70f58665e72d84c1a16ce112524ac7`.
No replay semantics, frozen diagnostic definition, or measured outcome was
accepted from that artifact. The correction retains the required exact records
for aliased repeated keys and compact support counts for all other keys; the
substantive audit is rerun from the corrected executable SHA.

That compact rerun from executable SHA
`1e51f267db19aec90bd2c18f07ea0addaa78a584` was also invalidated during the
final reporting audit because it did not explicitly serialize the policy-RNG
isolation digest or heading-oracle realized-displacement error required by the
authorization. Its artifact SHA-256 is
`0f5f13c602bd01c3ff0d25aebd3f8779ca1b5a13175339f09287f08396438222`.
The evaluator-only reporting correction is committed at the final executable
SHA used for the accepted rerun; no causal replay, seed, fit, oracle input, or
interpretation definition was changed.

## Required provenance and validation

The accepted artifact will record the clean executable SHA, exact D-027
trajectory-digest and final-weight equality for all 20 seeds, exact action and
mode support, all four actions, contact deltas, boundary strata, alias
coverage, cross-fit diagnostics, geometry reconstruction, both oracles,
surprises, and cautious attribution. It will not serialize raw transition
rows. Any genuine defect would invalidate its run and preserve the invalidated
SHA/provenance before a correction and exact rerun; outcome-driven tuning is
not permitted.

Required checks are focused D-028 tests, full pytest, Ruff, strict mypy,
compileall, `git diff --check`, deterministic artifact regeneration, and
exact-current-HEAD CI. D-028 remains descriptive Development-lane work;
development-seed reuse has no evidentiary status.

## Accepted substantive results

The accepted compact artifact was generated from clean executable SHA
`8000b325d9429c674cfff3ea18edf331ede5f4a0` using exactly the frozen 20 seeds
and `70,000` transitions per uninterrupted lifetime. Its SHA-256 is
`4d5cfa0aced828aea7cc638f480d5aa4420642ac6454f1e2d5620490b8cce3a0` and its
size is approximately 2.1 MB; raw transition rows are not serialized.

### Support and D-027 isolation

The run contains 1,400,000 transitions. All four actions were visited:
`MOVE_FORWARD=692,563`, `TURN_LEFT=68,240`, `TURN_RIGHT=68,910`, and
`WAIT=570,287`. Contact deltas were `+1=33`, `-1=53`, and `0=1,399,914`.
`MOVE_FORWARD` support was `255,220` full-nominal, `189,541`
boundary-clipped, and `247,802` full-stall transitions. All 20 seeds report
exact trajectory-digest, behavioural-summary, policy-RNG-state, and final
168-weight equality against the matched D-027 comparator/reference checks.

The exact visible-key census found `1,399,033` unique keys,
`802` repeated keys, `1,398,231` singletons, and only `1,769` transitions in
repeated keys (`0.1264%` coverage). It found no aliased repeated key. This is
not evidence that the visible state is sufficient: visited repeat support is
extremely sparse, and singleton keys remain untested for aliasing. The compact
artifact retains every aliased key if present and the exact support counts.

### Cross-fit prediction results

Pooled MAE, in output order, is shown below. Q1–Q4, per-seed, per-action,
boundary, and contact-event values are retained in the JSON artifact; Q3
boundary strata were untested because the frozen quarter support is empty.

| Reference | energy | beacon L | beacon F | beacon R | contact | thermal |
|---|---:|---:|---:|---:|---:|---:|
| zero-change | 1.9488e-5 | 9.1687e-3 | 9.0623e-3 | 9.1793e-3 | 6.1429e-5 | 3.4664e-7 |
| D-027 online | 3.7823e-8 | 7.1447e-3 | 6.6290e-3 | 7.1624e-3 | 1.6728e-4 | 1.2715e-8 |
| batch linear | 1.3659e-6 | 4.7418e-3 | 4.1349e-3 | 4.7664e-3 | 9.1125e-5 | 6.1946e-8 |
| quadratic | 1.0964e-6 | 2.6316e-3 | 1.8989e-3 | 2.6300e-3 | 9.5355e-5 | 5.0955e-8 |

The batch fits used the exact parity folds, dimensions 7 and 28, and
`numpy.linalg.lstsq(rcond=None)`. Rank deficiency was preserved: linear rank
was 6–7 by action/fold and quadratic rank was 20–27; no regularization or
tuning was added. The pattern is mixed: cross-fit batch references improve
substantially over the D-027 online learner for beacon deltas and charging
contact, while the online learner remains lower-error for energy and thermal.
Quadratic features materially improve beacon prediction over linear, but do
not improve pooled charging-contact MAE.

For the problematic boundary-clipped stratum, pooled beacon MAE was
`0.00560/0.00625/0.00560` for D-027 online (L/F/R),
`0.00625/0.00596/0.00626` for linear, and
`0.00511/0.00459/0.00511` for quadratic, against
`0.00517/0.00455/0.00515` for zero-change. Full-stall deltas are zero by
construction, while all learned references retain nonzero error there.
Charging-contact event support is only 86 nonzero rows, so event-stratum
values are descriptive and sparse.

### Geometry and oracle results

The D-016 inverse matched evaluator station-relative body-frame geometry with
mean absolute error `x=1.48e-7`, `y=2.55e-8`, radial `1.14e-7`, maxima below
`8.6e-7`, and zero geometry consistency failures. The beacon-only nominal
oracle had L/F/R MAE `5.67e-8/5.51e-8/5.67e-8` on full-nominal moves, but
`0.01190/0.01093/0.01190` on clipped moves and
`0.01161/0.01066/0.01157` on full stalls.

The privileged heading-augmented wall-aware oracle had beacon MAE
`5.54e-8/5.23e-8/5.55e-8` and exact charging-contact agreement on all
1,400,000 transitions. Its realized-displacement MAE was `1.27e-7` with
maximum `7.24e-7`; boundary prediction matched all `189,541` clipped rows and
`253,961` of `255,220` nominal rows, but classified all `247,802` true stalls
as clipped because the inverse-derived pose is slightly inside the bound.
This numerical boundary-class mismatch is retained and reported; no tolerance
was tuned after output inspection. It does not alter the oracle's near-exact
beacon/contact result.

### Cautious attribution, surprises, and blockers

Directly observed: the online-learning-dynamics branch is implicated for
beacon/contact residuals because cross-fit references outperform the online
learner on those outputs, and the linear-representation branch is implicated
for beacon residuals because the fixed quadratic basis improves held-out MAE.
The omitted-state/partial-observability branch is not demonstrated by exact
aliasing on this sparse repeat support, but the accurate beacon inverse and
heading-augmented oracle resolving visible beacon/contact consequences make
world-frame heading/wall relation a plausible attribution for clipping and
stall residuals. These explanations may coexist and do not authorize a new
sensor, history, larger learner, or behaviour control.

The main surprises are no exact alias on 1.4 million transitions despite weak
online contact performance, extremely sparse repeated-key support, and the
privileged oracle's exact contact prediction alongside its expected
float-reconstruction stall-label mismatch. No blocker remains.

Disposition is `CONTINUING`. This is descriptive Development-lane output, not
fresh evidence. No consciousness, emotion, subjective experience, genuine
life, biological metabolism, intelligence, world-model, or hardware-autonomy
claim is made. D-029 is not authorized by this record.
