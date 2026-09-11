# D-036 — Shadow short-history scaffold-recruitment learnability audit

- **id:** D-036
- **lane:** Development
- **authoritative base:** `911acc5daefe2b1e3fcc7a683e9056740c6bca29`
- **development seeds:** `18468..18487` inclusive, reused exactly
- **status:** protocol frozen before official output; execution follows the
  executable SHA recorded in the artifact
- **disposition:** `CONTINUING`

## Question and boundary

D-036 asks whether a transparent shadow learner can use a bounded recent
history of information available to the organism to predict productive versus
unproductive false-contact SEEK continuations. It is an evaluator-only
learnability/readiness audit. It does not add causal organism memory or learned
scaffold recruitment.

The canonical four actions, six visible channels, D-027 learner/controller,
scaffold semantics, physics, RNG streams, reward `0.0`, and `info == {}` are
unchanged. D-035A/B/C treatment mechanics are not imported; they remain
candidate later re-tests only after a learned temporal recruitment mechanism
exists.

## Frozen protocol

For each reused seed, the accepted D-034 replay path reproduces Arm-A
`LEARNED_WITH_DETRAP` and Arm-B `LEARNED_NO_DETRAP`, including the complete
learner state, RNG checks, no-de-trap isolation, reward/info boundary, and
executed-action update semantics. Ordinary Arm-B traces are then inspected
post-hoc. Eligible samples are completed false-contact SEEK transitions whose
before/after decision observations have no charging contact.

Features are direct flattened rows of six visible channels (energy, beacon
left/forward/right, charging contact, thermal) followed by a one-hot executed
logical action. H1 is the current completed decision row; H4, H8, and H16 are
the last 4, 8, or 16 completed rows. Prefixes without enough completed rows
are unavailable and are counted, never padded. No pose, geometry, distance,
heading, station state, seed/arm/branch label, future outcome, or D-034
predicate enters a feature.

For horizons exactly 64, 256, and 1024 transitions, the target is derived from
the unchanged continuation after the completed decision: whether dual-contact
reacquisition occurs and the change in visible beacon-forward. Windows that
reach termination, truncation, or the lifetime boundary are retained as
explicit null statuses and excluded only from the affected fit/metric.

Each history/horizon uses ridge linear regression for continuous progress and
a ridge linear classifier transformed by a sigmoid for reacquisition only when
the training fold contains both classes. The predeclared alpha grid is
`[1e-6, 1e-4, 1e-2, 1.0]`; the frozen value is `0.01`, selected before official
output, so no held-out tuning occurs. Evaluation is deterministic
leave-one-seed-out over all 20 seeds. Per-fold reports retain held-out seed,
sample counts, class balance, feature dimensions, selected alpha, MAE,
correlation, Brier score, balanced accuracy, AUROC where defined, and exact
same-sample H4/H8/H16 versus H1 comparisons. Pooled summaries and all seeds,
including null/untestable supports, are retained.

After cross-validation, full-support shadow fits are queried read-only at the
D-034 `ALT_4/8/16` and `NO_FORWARD_PROGRESS_4/8/16` anchors. Predictions and
actual continuation values are descriptive bridge diagnostics only; D-034
labels and ON/OFF outcomes are not training inputs.

## Predeclared interpretation

1. **History adds learnable information:** a bounded history consistently
   improves held-out prediction over H1 without a single-seed driver.
2. **Current state is sufficient:** H1 matches bounded histories within
   ordinary sampling variation.
3. **History signal exists but is too weak/unstable:** some folds improve but
   pooled/generalization evidence is inconsistent.
4. **Target unsupported:** class balance or causal support is insufficient;
   report null/untestable rather than manufacture labels.
5. **Bridge coherence:** successful-recruitment anchors descriptively fall in
   a learned high-risk/low-progress region more often than matched non-anchor
   states.
6. **No bridge coherence:** learnability exists but does not align with D-034
   recruitment-success states.

There is no universal pass threshold and no confirmatory claim. A positive
result cannot authorize causal history; it can only motivate the smallest
future ADR/governance change and independently reviewed follow-on task.

## Provenance and validation

The complete executable protocol, focused tests, and artifact writer were
committed before official held-out output. The exact clean executable protocol
SHA, deterministic artifact hash/size, official results, and validation log
are recorded in the machine-readable artifact and handoff. No fresh
Development or EXP seeds are used.

`surprised_by` and final disposition are updated after the official artifact
is generated without changing the executable protocol.
