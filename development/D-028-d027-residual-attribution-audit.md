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

## Results and disposition

To be completed from the frozen executable artifact after the substantive
replay. No consciousness, emotion, subjective experience, genuine life,
biological metabolism, intelligence, world-model, or hardware-autonomy claim
is made.
