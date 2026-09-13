# D-038 — Combined fine-turn + L/F/R interpolation + reverse sufficiency audit

- **id:** D-038
- **lane:** Development
- **authorized base:** `b49531fe29cd5c0f83cec300369d9fd9d0c64700`
- **development seeds:** `18468..18487` inclusive, reused exactly
- **earlier invalidated protocol freeze SHA:** `ac336d1406a0016c445f0b9b8db3aea6c3a46e25`
- **earlier invalidated artifact SHA-256:** `6abfe01b612f7498570851d55e5ec4eb52d875af8094fa455ab51f2db5120dc3`
- **earlier invalidated artifact size:** `102845850` bytes
- **earlier invalidated-output reason:** required T3/T4 authorization-compliance diagnostics and focused tests were missing: accepted D-035B behavior-structure reporting, canonical turn time/total and actuator-only electrical exposure with guards, and explicit baseline, isolation/RNG, reverse-no-update, and exactly-one canonical-action update tests
- **corrected protocol freeze SHA:** `83000c3764848f084d7517edfa8425b29a4b059d`
- **corrected-output invalidation reason:** Sol found that T3/T4 behavior-
  structure diagnostics conflated evaluator reverse interventions with
  canonical `MOVE_FORWARD` logical-action diagnostics; the prior output is
  preserved but not interpreted
- **latest invalidated protocol freeze SHA:** `19acce381138a600ea778f98f72d2aa2b890b964`
- **latest invalidated artifact SHA-256:** `b86e9e92650555fd95751cbfbc133e7e86bf00e95f46855f1e109f5fc43f6968`
- **latest invalidated artifact size:** `103341096` bytes
- **latest invalidated-output reason:** the required all-four logical action
  counts still omit selected Arm-B logical actions on evaluator
  reverse-intervention steps; the prior output therefore fails the declared
  selected-vs-executed logical-action diagnostic semantics and is preserved
  but not interpreted
- **latest clean protocol freeze SHA:** `79c7cef9da5f5772752406357367e4b6a3f113d5`
- **artifact:** `D-038-combined-fine-interp-reverse-sufficiency-audit.json`
- **artifact SHA-256:** `4e5f0ca22b7583029d76c32d557d5edbf9bac9d9ad4347a999f4c873d7de25a3`
- **artifact size:** `103496012` bytes
- **status:** official output complete
- **disposition:** `CONTINUING`

## Question and boundary

D-038 asks whether the joint evaluator-only treatment of finer turning,
mathematical L/F/R interpolation, and reverse translation can restore dual
charging-contact reacquisition from already-observed Arm-B trapped or docking-
relevant states. It is a counterfactual interaction audit, not a canonical
organism change.

The canonical organism remains the accepted Arm-B `LEARNED_NO_DETRAP` with its
four actions, six visible channels, D-027 168-weight state, update rule,
reward `0.0`, and organism-facing `info == {}`. Reverse has no `Action` enum
identity, no learner update, and no organism-visible state. No D-039 or EXP
work was started.

## Frozen protocol

The protocol reconstructs these pre-action anchors from the accepted replay:

1. `FIRST_FALSE_CONTACT_SEEK`: mode already `SEEK`, visible and evaluator
   charging contact false, immediately before ordinary Arm-B selection;
   AWAY-to-SEEK entry states are ineligible.
2. `ALT8_ESTABLISHED`: the exact D-033 state after eight completed strict
   alternating left/right false-contact SEEK actions without contact,
   forward, or wait interruption.
3. `FIRST_POST_CONTACT_LOSS`: the exact D-035C post-loss state; unavailable
   seeds remain null.

The fixed treatment matrix is:

- `T0_BASELINE_B`: exact canonical 45-degree Arm-B continuation.
- `T1_FINE_5_FIXED`: canonical logical actions with evaluator-only 5-degree
  physical turns.
- `T2_FINE_5_INTERP`: T1 plus
  `x=F+cos(pi/4)*(L+R)`, `y=sin(pi/4)*(L-R)`,
  `theta_hat=atan2(y,x)`, zero vector `theta_hat=0`, and turn magnitude
  `min(5 degrees, abs(theta_hat))`.
- `T3_FULL_COMBINED_5`: T2 plus evaluator-only reverse selected only when
  its rear-contact max-pair-error reduction is strictly greater than every
  treated canonical candidate.
- `T4_FULL_COMBINED_2`: T3 with a prospective 2-degree cap.

Each available branch runs for at most 4,096 real transitions and stops on
reacquisition, inherited termination, or inherited truncation. Candidate
evaluation is cloned, read-only, order-invariant, and RNG-preserving. The
artifact retains geometry, movement, contact, energy/thermal, action,
alternation, interpolation, reverse, and executed-canonical-action D-027
prequential diagnostics, including exact windows `1..16`, `17..64`,
`65..256`, `257..1024`, and `1025..4096`. Reverse steps are not scored as
canonical learner predictions.

T0-T2 per-decision L/F/R rows use the accepted D-035B lossless binary-row
encoding. T3/T4 rows use a D-038 fixed-width binary encoding that retains the
selected logical action, executed operation, nullable executed logical action,
and reverse diagnostics. Both encodings are marked complete in the artifact
and retain record counts and codebooks.

## Provenance and invalidated attempts

The official output produced from protocol SHA
`ac336d1406a0016c445f0b9b8db3aea6c3a46e25` is preserved but invalidated under
the issue #133 freeze rules. Its artifact SHA-256 is
`6abfe01b612f7498570851d55e5ec4eb52d875af8094fa455ab51f2db5120dc3` and its
size is `102845850` bytes. The exact reason is that authorization-compliance
diagnostics and focused tests were missing: T3/T4 accepted-D-035B
behavior-structure reporting (strict L/R alternation run count, length
distribution, maximum, next-eligible opposite-turn fraction, and explicit
visible-side-reversal reporting), canonical turn time/total and actuator-only
electrical exposure with guards, and explicit tests for baseline identity,
branch/source plus RNG isolation, reverse no-update, and exactly-one
executed-canonical-action D-027 update behavior. No result from that output is
used for interpretation.

The first frozen protocol was `f77b5c62521e66389c463bc903cfaf528254bd2d`.
Its official artifact was generated before inspection with SHA-256
`c73a663c49d6d9f2f7c1c8fada8d69961bddfddc9a2ad3317c4bfa40d13a62ae` and size
`2832241674` bytes. It is invalidated because verbose per-decision JSON made
the artifact nonviable; no treatment interpretation was taken from it.

The compact-JSON correction froze `550c7c279c4f54ff6f56c62d732e08b0d2706286`.
Its official rerun aborted before writing a new artifact because combined L/F/R
records omitted the required `visible_side_reversal` diagnostic. The prior
invalidated artifact remained at the path; no new output was interpreted.

The diagnostic correction froze `6016a82ec2bb8f6cc6b79cf58f406cfea657b2a4`.
Its artifact was SHA-256
`fe64df88a240732aee47e7c62c3c0f04180a124ef49f945063978580c0258a2e` and size
`257892983` bytes. It is invalidated because it remained above the normal
GitHub artifact-size limit.

The accepted D-035B encoding correction froze
`c3e627a2b2007ff7ba79e881df808443528b0fee`. Its artifact was SHA-256
`7be721a26e0437d7686c861a96d0890c156bc0ceb524842d6799c220a9f60f89` and size
`106693916` bytes. It is invalidated because it was still just above the
100-MiB file limit.

The final fixed-width reverse-record correction is the protocol recorded at
the top of this document. These corrections changed artifact representation
and required serialization, not treatment mechanics, seed support, anchors,
or interpretation rules.

The authorization-compliance correction froze protocol SHA
`83000c3764848f084d7517edfa8425b29a4b059d`. Its corrected official artifact
had SHA-256
`430e41f113dedc7e2c8b8c211263816c29af52a35638fd3eb6bfc40e039f266d` and size
`103114648` bytes. Sol later invalidated that output because T3/T4 behavior-
structure diagnostics still conflated evaluator reverse interventions with
canonical `MOVE_FORWARD` logical-action diagnostics. No result from it is used
for interpretation.

The latest bounded correction froze clean protocol SHA
`79c7cef9da5f5772752406357367e4b6a3f113d5`. Its official reused-support
artifact has SHA-256
`4e5f0ca22b7583029d76c32d557d5edbf9bac9d9ad4347a999f4c873d7de25a3` and size
`103496012` bytes. Deterministic regeneration was byte-identical. The artifact
preserves unchanged treatment mechanics, support, anchors, and interpretation
rules while making `logical_action_counts` the selected Arm-B logical-action
counts, including reverse-selected steps. It separately reports
`executed_canonical_action_counts`; reverse rows have null
`executed_logical_action` and are excluded from that executed-canonical
sequence. Strict alternation and next-eligible-opposite-turn diagnostics name
their selected-logical sequence semantics explicitly.

One predecessor helper exposed a derived `b_proposed_action` mismatch against
the accepted D-033 artifact for `ALT8_ESTABLISHED` on available seeds. The
complete causal anchor state, transition, observations, learner digest, update
prefix, and RNG digests matched exactly. D-038 therefore records the derived
proposal discrepancy explicitly and gates on the causal-state projection; it
does not treat the derived field as causal state.

## Official output

Replay/identity gates passed for all 20 reused Arm-B seed replays. There were
285 available seed+anchor treatment groups: 20 `FIRST_FALSE_CONTACT_SEEK`,
17 `ALT8_ESTABLISHED`, and 20 `FIRST_POST_CONTACT_LOSS` seeds, each with five
treatments. All 285 baseline continuation checks passed, and all isolation,
reward/info, canonical-action, learner-update, RNG, logical-action/
evaluator-operation separation, behavior-structure, and canonical turn
time/electrical semantics checks passed.

| Anchor | T0 | T1 | T2 | T3 | T4 |
|---|---:|---:|---:|---:|---:|
| `FIRST_FALSE_CONTACT_SEEK` reacquisitions | 0/20 | 0/20 | 0/20 | 0/20 | 0/20 |
| `ALT8_ESTABLISHED` reacquisitions | 0/17 | 0/17 | 0/17 | 0/17 | 0/17 |
| `FIRST_POST_CONTACT_LOSS` reacquisitions | 1/20 | 1/20 | 1/20 | 1/20 | 1/20 |

The one post-loss reacquisition had latency 555 in every treatment. Reverse
interventions occurred 48 times in T3 and 50 times in T4, all on the
false-contact SEEK support; they did not produce additional reacquisitions.
No reverse interventions occurred on the ALT8 or post-loss branches.

## Matched interpretation

These are descriptive Development observations only, using only the
predeclared categories:

- **Fine-turn contribution:** not supported on this support; T1 did not
  improve matched reacquisition over T0.
- **Interpolation adds conditional benefit:** not supported; T2 did not
  improve matched reacquisition over T1.
- **Reverse adds conditional benefit:** not supported behaviourally; T3 added
  selected evaluator interventions over T2 but produced no additional
  reacquisition.
- **2-degree sensitivity only:** not supported; T4 did not succeed where T3
  failed.
- **Joint sufficiency supported descriptively:** not supported; neither full
  combined arm recovered any additional first-contact or ALT8 branch.
- **Joint insufficiency:** supported descriptively on this reused Development
  support. The evaluator upper-bound combination did not restore recovery,
  shifting attention back toward temporal/strategy-change mechanisms or a
  different missing variable. This does not authorize any organism-side
  change.

No universal success percentage, p-value threshold, consciousness claim,
biological claim, or canonical adoption follows from this audit.
