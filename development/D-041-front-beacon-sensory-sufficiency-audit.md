# D-041 — Front-beacon sensory sufficiency audit

- **id:** D-041
- **issue:** [#140](https://github.com/PiFlow/aweform/issues/140)
- **lane:** Development
- **authorized_base_sha:** `8b51d6e143a906a83f1fd8d760aace5ed46abb9e`
- **status:** protocol frozen; substantive support pending
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
Development holdout seeds `18488..18507`, with the D-040 70,000-transition
Arm-B lifetime and the following predeclared anchor IDs:

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

## Provenance and validation

The executable protocol SHA is the exact clean commit recorded in each compact
artifact. Artifacts contain per-seed/per-anchor/per-control summaries and
digests, not raw transition dumps. The protocol is frozen before designated
support outcome inspection. Focused D-041 tests, full tests, Ruff, strict
mypy, compile/import checks, `git diff --check`, and byte-identical artifact
regeneration are required before handoff.

**surprised_by:** Not yet observed; the question and controls are frozen before
support inspection.

**disposition:** `CONTINUING`.

## Invalidated pre-artifact execution

The first frozen implementation attempt was started from executable SHA
`fa6ea7e0495d7706319c2eb7d03c790545f94b78` with the reused-support command but
was interrupted before any artifact was written or any result was inspected.
It redundantly reran all seven branches in both orders for every anchor. This
was a control-cost defect, not a scientific result. The corrected protocol
checks branch-order invariance on the primary pair branch per anchor; the
scientific branch set and outcome definitions are unchanged. The interrupted
attempt is not D-041 evidence and will not be pooled.
