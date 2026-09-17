# D-041 — Front-beacon sensory sufficiency audit

- **id:** D-041
- **issue:** [#140](https://github.com/PiFlow/aweform/issues/140)
- **lane:** Development
- **authorized_base_sha:** `8b51d6e143a906a83f1fd8d760aace5ed46abb9e`
- **status:** completed; support and holdout results recorded
- **disposition:** `CONTINUING`

## Question and boundary

D-041 tests whether two minimal front-facing charging-beacon receptors contain
enough information to improve charger reacquisition/front docking from matched
D-040 failure states. This is an evaluator-only sufficiency audit. It does not
add a sensor to Aweform, change S0, alter D-027/D-030, or authorize D-042.

The accepted D-040 Arm-B replay supplies the anchor states. D-040's exact
canonical organism behaviour remains the comparator; all receptor values and
branch geometry remain evaluator-only. The D-040 reused artifact is referenced
by SHA-256 `764c1b09f18c250cb55682d434c2b6f372a9e66d82380b88c0bc08ab85cd495d`.

## Frozen protocol

The declared support is reused Development seeds `18468..18487` and fresh
Development holdout seeds `18488..18507`. D-040's accepted Arm-B lifetime is
70,000 transitions; D-041 replays each seed through that complete lifetime for
anchor capture. The following eight anchor IDs are predeclared:

`OFFSET_0`, `OFFSET_15`, `OFFSET_63`, `OFFSET_255`, `OFFSET_1023`,
`OFFSET_4095`, `ALT_16`, and `NO_FORWARD_PROGRESS_16`.

The receptor pair is attached to the body front face at body-frame positions
`(+0.05,+0.025)` (left) and `(+0.05,-0.025)` (right), with both normals along
body-frame `+X`. The beacon is an isotropic point emitter at the existing D-024
station centre. For receptor distance `d` and front cosine `c`, the response is
`clip(max(0,c) * max(0,1-d/0.35), 0, 1)`. Range is `0.35`; noise and occlusion
are omitted explicitly. Out-of-range and rear-facing responses are zero.

The primary fixed readout uses only the instantaneous pair: left greater than
right turns left, right greater than left turns right, equal positive values
move forward, and equal zero values wait. No receptor history is used. The
4,096-transition matched branch stops at first dual-contact reacquisition,
termination, truncation, or horizon. It reports horizons 64, 256, 1,024, and
4,096.

Controls are frozen as `S0_READOUT` (current visible left/right beacon rule),
`LEFT_ONLY`, `RIGHT_ONLY`, `SWAP`, `NULL`, `OUT_OF_RANGE`, canonical diagnostic
ON/OFF identity, source-anchor immutability, branch-order invariance, reward
zero/info empty, and no receptor feedback into canonical state. The primary
outcome is matched pair-only versus S0-readout reacquisition/contact; latency,
path/action effects, separability buckets, and nulls are descriptive.

## Interpretation categories

The artifact preserves `SUFFICIENT`, `PARTIAL`, `NULL/INSUFFICIENT`, and
`INVALID`. `SUFFICIENT` is not a sensory authorization: it would only motivate
a separate boundary proposal. The implementation reports `PARTIAL` only when
pair-only support is reproducible on at least two seeds and two frozen anchor
regimes, with a broader boundary decision still required.

## Observed result

Both declared supports were executed with the frozen protocol. Reused support
produced 157 available anchors from 20 seeds; fresh holdout produced 154
available anchors from 20 seeds. Across every available anchor, the `PAIR`,
`S0_READOUT`, one-receptor, swap, null, and out-of-range branches had zero
reacquisitions. Pair-only support was therefore `0` on both supports, and both
artifacts classify the result as `NULL/INSUFFICIENT`.

The canonical diagnostic ON/OFF identity, source-anchor immutability, branch
order, evaluator-only, reward-zero, and info-empty controls passed for all 311
available anchors. At the frozen 0.001 S0 bucket width, neither support had an
ambiguous S0 anchor group separated by the receptor pair. These are
descriptive development results only; they do not prove that every possible
beacon model is insufficient.

The compact artifacts are:

- [reused support](D-041-front-beacon-sensory-sufficiency-audit-reused.json),
  SHA-256 `f1bfc39175a153312f88f77b30803f6826d64c8ea1f0335ecb8f801a09ae7f7a`,
  4,660,980 bytes, executed at exact clean commit
  `f1eac015e886616ff04657230d56a2dc0df66e2e`;
- [fresh holdout](D-041-front-beacon-sensory-sufficiency-audit-holdout.json),
  SHA-256 `387c139c81c45d6b57c9f55f1ec5e83ec0ddfdb420a223a1aa3eb7a5e1a3be43`,
  4,568,471 bytes, executed at exact clean commit
  `94c43f2646c2f8f890c6f7d58ccc65bc0b0652b0`.

The holdout artifact was regenerated from the same clean exact commit and was
byte-identical. The result remains evaluator-only. No receptor value was
exposed to Aweform, and D-041 authorizes neither a sensory-boundary change nor
D-042; stop here pending Flow/Sol interpretation.

## Provenance and validation

The executable protocol SHA is the exact clean commit recorded in each compact
artifact. Artifacts contain per-seed/per-anchor/per-control summaries and
digests, not raw transition dumps. The protocol is frozen before designated
support outcome inspection. Focused D-041 tests, full tests, Ruff, strict
mypy, compile/import checks, `git diff --check`, and byte-identical artifact
regeneration are required before handoff.

**surprised_by:** The null result was consistent across both supports: no
available anchor showed pair-only reacquisition, and the frozen receptor pair
did not separate any ambiguous S0 bucket at the declared resolution. The
receptor measurements were also zero at many early anchors because the
declared physical range/front-facing model placed the station outside the
candidate response regime; this is a property of the frozen model, not a
post-hoc exclusion.

**disposition:** `CONTINUING`.

## Invalidated pre-artifact execution

The first frozen implementation attempt was started from executable SHA
`fa6ea7e0495d7706319c2eb7d03c790545f94b78` with the reused-support command but
was interrupted before any artifact was written or any result was inspected.
It redundantly reran all seven branches in both orders for every anchor. This
was a control-cost defect, not a scientific result. The corrected protocol
checks branch-order invariance by running the S0 comparator before the primary
pair branch on a second pass per anchor; the
scientific branch set and outcome definitions are unchanged. The interrupted
attempt is not D-041 evidence and will not be pooled.

The second attempt used the corrected primary-branch order control from
executable SHA `491acd1a562ee3a949ec1afc8c352093dc838c50` but was also
interrupted before artifact writing or outcome inspection while replaying the
full 70,000 transitions for every seed. It produced no D-041 evidence.

The third attempt used executable SHA `e104869f7ef05df44d6a0ff08045fbbdddd99377`
with the complete eight-anchor capture request. It was interrupted before
artifact writing or outcome inspection after the accepted D-040 runner exposed
an avoidable quadratic prefix-trigger scan while looking for the frozen
`ALT_16` and `NO_FORWARD_PROGRESS_16` anchors. The incremental boundary check
is a replay-mechanics correction: it is equivalent to the prior completed-row
selection rule and does not change any anchor, branch, seed, or outcome
definition. Results from all three interrupted attempts are excluded.
