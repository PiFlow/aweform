# D-036 — Shadow short-history scaffold-recruitment learnability audit

- **id:** D-036
- **lane:** Development
- **authoritative base:** `911acc5daefe2b1e3fcc7a683e9056740c6bca29`
- **development seeds:** `18468..18487` inclusive, reused exactly
- **prior invalidated protocol SHA:** `3675be49a640b519ac42d956692b93778362bf60`
- **prior invalidated artifact:** `D-036-shadow-short-history-recruitment-learnability.json`
- **prior invalidated artifact SHA-256:** `81260bf42f80bf42204939dbf19c304e69d131576a0803f43c53bb78ba63e343`
- **prior invalidated artifact size:** `621472` bytes
- **prior corrected protocol freeze SHA (invalidated):** `ae1b47e3d35b6198143a2138a00ac081fd62db1a`
- **artifact:** `D-036-shadow-short-history-recruitment-learnability.json`
- **artifact SHA-256:** `32df6a73953b90e109fcccf11de42bbfda63c3da5b1be846081039c91f053366`
- **artifact size:** `936163` bytes
- **status:** correction protocol pending official rerun
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
post-hoc. Eligible samples are false-contact SEEK pre-action decision states:
`mode_before` is `SEEK` and the current visible charging-contact bit is false.
Eligibility does not consult `mode_after`, post-action contact, or any other
current-transition outcome.

Features are direct flattened rows of six visible channels (energy, beacon
left/forward/right, charging contact, thermal). H1 is the current pre-action
decision observation only; H4, H8, and H16 append the prior 4, 8, or 16
completed transition observations (the organism-visible after-observation) and
one-hot executed-action pairs. The scored decision's own executed action is
never a feature. Prefixes without enough completed rows are unavailable and
are counted, never padded. No pose, geometry, distance, heading, station
state, seed/arm/branch label, future outcome, or D-034 predicate enters a
feature.

For horizons exactly 64, 256, and 1024 transitions, the target is derived from
the unchanged continuation after the completed decision: whether dual-contact
reacquisition occurs and the change in visible beacon-forward from the current
pre-action observation to the final observation in the H-transition window.
Windows that reach termination, truncation, or the lifetime boundary are
retained as explicit null statuses and excluded only from the affected
fit/metric.

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
D-034 `ALT_4/8/16` and `NO_FORWARD_PROGRESS_4/8/16` anchors. Each available
anchor is paired within its seed to the nearest eligible ordinary-support
non-anchor state by squared distance on the same shadow feature vector, with
smallest trace index as the deterministic tie-break. Every D-034 anchor index
is excluded from the candidate pool. Predictions and actual continuation
values are descriptive bridge diagnostics only; D-034 labels and ON/OFF
outcomes are not training inputs or matching features. Availability, nulls,
per-seed pairs, and pooled progress/high-risk comparisons are retained.

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

## Invalidated official output provenance

The prior official output is invalidated provenance, not evidence. Its exact
clean executable protocol SHA was
`3675be49a640b519ac42d956692b93778362bf60`; its artifact SHA-256 was
`81260bf42f80bf42204939dbf19c304e69d131576a0803f43c53bb78ba63e343`, and its
size was `621472` bytes. Exact-current-HEAD review found that the scored
decision feature included its own executed action and that the mandatory D-034
bridge lacked a deterministic matched non-anchor comparison. The corrected
protocol freezes the current-decision indexing and the matched bridge
diagnostic before any corrected output is generated.

The prior corrected output is additionally invalidated: its exact clean
protocol SHA was `ae1b47e3d35b6198143a2138a00ac081fd62db1a`, artifact SHA-256 was
`32df6a73953b90e109fcccf11de42bbfda63c3da5b1be846081039c91f053366`, and size
was `936163` bytes. The exact conformance-defect reason was that sample
eligibility depended on the scored transition's `mode_after` and post-action
charging contact, which are unavailable at the pre-action decision state and
can censor decisions based on the predicted continuation.

The prior corrected official output was generated from the clean protocol
freeze SHA `ae1b47e3d35b6198143a2138a00ac081fd62db1a`. It is additionally
invalidated by the conformance defect recorded below. The artifact records
H1/H4/H8/H16 feature dimensions `6/46/86/166`,
per-fold held-out results, explicit nulls, and the deterministic bridge pairs.

At each requested target horizon, 112 of 120 D-034 anchor records were
available and every available anchor had a matched ordinary non-anchor state;
the eight unavailable anchor records are retained. No bridge target was null.
The continuous bridge comparison put the anchor below its matched prediction
in `13/112`, `38/112`, and `38/112` pairs for horizons `64`, `256`, and `1024`,
respectively; the pooled mean anchor-minus-match predicted progress deltas
were positive (`0.00785`, `0.00789`, `0.00775`). The binary target remained
all-negative, so high-risk/binary bridge coherence is untestable and neither
bridge-coherence category is asserted.

The new corrected protocol and official output will be recorded after the
pre-action eligibility correction is frozen and rerun. Required validation
remains focused D-036 tests, full pytest, Ruff, strict mypy, compileall, and
`git diff --check`, with deterministic artifact regeneration.

`surprised_by` and final disposition are recorded below without changing the
executable protocol.

## Observed

All 20 Arm-A/Arm-B identity replay gates passed. Arm-B produced no positive
dual-contact reacquisition labels at any requested horizon, so the binary
target is unlearnable/untestable on this support and its Brier score, balanced
accuracy, and AUROC are reported null. The continuous progress target remains
supported. H4/H8/H16 have higher pooled held-out correlation than H1, but
held-out MAE is worse on average and the per-seed MAE differences are mixed:
the descriptive reading is **history signal exists but is too weak/unstable**.

This does not authorize causal temporal memory or learned scaffold
recruitment. D-035A/B/C remain candidate later re-tests only after a learned
temporal recruitment mechanism exists. No confirmatory or consciousness,
emotion, genuine-life, or intelligence claim is made.

**surprised_by:** The all-negative reacquisition target made the requested
binary learner unsupported across every frozen horizon, while bounded-history
features still changed continuous-progress correlation; increasing history
did not improve held-out MAE on average.
