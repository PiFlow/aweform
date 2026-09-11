# D-035B — L/F/R interpolation attribution audit

- **id:** D-035B
- **issue:** [#123](https://github.com/PiFlow/aweform/issues/123)
- **lane:** Development
- **authoritative_base_sha:** `d40681d25cd4cc67e359004ffcd63819e40b42a4`
- **base_tree_sha:** `50510ba772a1d53960f7f5870feb6b7b510cacf4`
- **development_seeds:** `18468..18487` inclusive, reused exactly
- **underlying lifetime horizon:** `70,000` transitions
- **branch horizon:** `4,096` transitions from each isolated anchor
- **status:** corrected protocol frozen; corrected substantive output complete
- **disposition:** `CONTINUING`

The executable protocol is [`src/aweform/d035b.py`](../src/aweform/d035b.py).
The machine-readable output path is
[`D-035B-lfr-interpolation-attribution-audit.json`](D-035B-lfr-interpolation-attribution-audit.json).

## Question and boundary

D-035B asks whether a bounded evaluator-side interpolation of the existing
visible left/forward/right beacon values changes turn magnitude, geometry, or
reacquisition attribution around two isolated accepted Arm-B states. It is an
evaluator-only matched branch audit. It does not add an organism sensor,
action, turn primitive, memory, controller, learner, reward, or physical
mechanism.

The accepted D-031R1 `LEARNED_NO_DETRAP` Arm-B controller, D-027 learner,
D-024 contact geometry, D-020 physical transition, six visible channels,
four logical actions, reward `0.0`, and organism `info == {}` remain inherited.
False-contact SEEK de-trapping remains disabled. The inherited one policy-RNG
draw remains at its original decision timing.

## Freeze and provenance

The first official protocol/output pair was invalidated after exact-current-HEAD
review found two issue-conformance defects: its `FIRST_FALSE_CONTACT_SEEK`
selection could capture an AWAY-to-SEEK entry state, and it omitted the frozen
prediction stratification and mandatory reporting fields. The old provenance
is retained here and in the regenerated JSON as invalid, not as evidence for
the corrected protocol.

- **invalidated_protocol_only_freeze_sha:** `8a0e23fbee23f3c47a6111dd3e23882f2402b176`
- **invalidated_implementation_probe_sha:** `8a0e23fbee23f3c47a6111dd3e23882f2402b176`
- **invalidated_artifact_sha256:** `877c7355d62a5254442fa3bcb3599c251c6800a7b616442421082661151d1086`
- **invalidated_artifact_size_bytes:** `3,491,326`
- **invalidation_reason:** exact-current-HEAD review identified an invalid
  pre-action anchor identity and missing required stratified diagnostics/fields.

The immediately prior artifact was also invalidated because its clean executable
protocol SHA was a non-existent Git object. That typo and its artifact identity
are retained as invalid provenance below; it is not evidence for the corrected
protocol.

- **invalidated_protocol_only_freeze_sha:** `7fb0846f4f7f3d6c52785b5a7c96c1e99784a33f`
- **invalidated_artifact_sha256:** `f09d605e83b991381e53810635614cc9546cb3a55181881167c7037062115236`
- **invalidated_artifact_size_bytes:** `99,075,381`
- **invalidation_reason:** the recorded SHA was not an existing Git commit; repository evidence identifies `7fb08461694d838cb1333b9e3d66de8345780ac4` as the real executable protocol commit.

The corrected executable protocol was frozen at a new clean SHA before the
authorized treatment was rerun. The previously corrected protocol/output pair
was invalidated by this bounded issue-conformance correction.

- **protocol_only_freeze_sha:** `7fb08461694d838cb1333b9e3d66de8345780ac4`
- **implementation_probe_sha:** `7fb08461694d838cb1333b9e3d66de8345780ac4`
- **corrected_artifact_sha256:** `5d1471519972ee8099a211ab61f70da897eac1640d6f190c48c49a74cc2f6814`
- **corrected_artifact_size_bytes:** `99,075,876`
- **deterministic_regeneration:** byte-for-byte equal to a second clean run.
- **superseded_protocol_sha:** `2e791c84c3ad9c94c57d6dbddc283bb08ea6ff5b`
- **superseded_artifact_sha256:** `b4cded422bcdb3eadfb204473cf827f3e48b7124f5473be2447e49d3a3a1e27a`

Only bounded pre-freeze checks used a historical non-D-035B seed (`18428`).
They did not execute or inspect the official D-035B output.

## Frozen protocol

For every authorized seed, the runner first reproduces accepted D-031R1 Arm-B
exactly, including outcome/termination, visible trajectory, executed-action
update digest, complete 168-weight D-027 state, policy/environment RNG
digests, and the no-de-trap one-draw contract. Instrumented replay must match
the uninstrumented replay exactly.

Two evaluator-selected pre-action anchors are reconstructed from the Arm-B
trace and recaptured from an isolated pre-action clone:

1. `FIRST_FALSE_CONTACT_SEEK` is the first transition whose **pre-action**
   controller mode is already SEEK and whose visible and evaluator contact
   bits are false immediately before ordinary no-de-trap arbitration/action
   selection. An AWAY-to-SEEK entry transition is not eligible because its
   pre-action mode is AWAY.
2. `ALT8_ESTABLISHED` reuses D-033's exact first eight-action strict
   left/right alternation in false-contact SEEK, with no contact, forward, or
   wait action, followed by a pre-action state. Unavailable anchors remain
   unavailable.

From each available isolated anchor clone, the runner executes `BASELINE_B`
and matched `LFR_FIXED`/`LFR_INTERP` branches at exactly `5°`, `2°`, and `1°`.
The frozen interpolation is:

```text
x = F + cos(pi/4) * (L + R)
y = sin(pi/4) * (L - R)
theta_hat = atan2(y, x)
```

For the exact zero vector, `theta_hat = 0`. Existing
`seek_beacon_action` supplies the forward-versus-turn gate and discrete turn
direction. `LFR_FIXED` uses exactly the selected cap for a turn;
`LFR_INTERP` uses `min(cap, abs(theta_hat))` with the same discrete turn
direction. A sub-45° magnitude is evaluator-only: the logical action remains
the existing `WAIT`, `TURN_LEFT`, `TURN_RIGHT`, or `MOVE_FORWARD` enum.

Every branch starts from a fresh clone of the complete anchor environment,
controller, RNG streams, and D-027 state. Each branch preserves canonical
one-transition action timing and turn electrical/thermal accounting. Each
completed transition requires reward `0.0`, empty organism `info`, and exactly
one D-027 update from the physically executed logical action and actual next
six-channel observation. Branches stop at dual-contact reacquisition,
inherited termination/truncation, or `4,096` transitions. Branch-order and
baseline-creation-order invariance are checked.

## Required reporting

The artifact retains accepted replay and anchor checks, availability/nulls,
branch outcomes, reacquisition latency and energy, evaluator geometry and
viability, path/displacement, visible beacon change, action counts, forward
nominal/clipped/stall counts, strict alternation, side reversals, the
opposite-turn-next-eligible-SEEK fraction, charging/dual-contact events,
rear-contact pair-error geometry at start/minimum/final/reacquisition,
directional interpolation error against evaluator station bearing, cap
saturation, cumulative commanded signed/absolute turn angle, turn count and
canonical turn energy/time exposure, and energy/thermal values at anchor,
minimum, maximum, final, and reacquisition. Every LFR decision retains L/F/R,
theta-hat, both action identities, executed angle/heading, signed and absolute
forward change, visible L-R signs and reversal, evaluator bearing/error, and
before/after rear-contact pair-error geometry. These records use an exact
deterministic `zlib+base64-binary-rows` representation with a declared schema
and action codebook; derivable absolute-angle/forward and heading-change
aliases are declared in the artifact. Prediction compatibility reports all
six outputs, turn-only all-six-output summaries, `delta_beacon_forward`
separately for left and right turns, and exact support counts in windows
`1..16`, `17..64`, `65..256`, `257..1024`, and `1025..4096`. No seed or null
is discarded.

The result is descriptive Development evidence only. It cannot establish a
learned interpolation, consciousness, emotion, subjective experience,
genuine life, metabolism, or a confirmatory claim.

## Corrected substantive output

The corrected official artifact was generated from clean executable SHA
`7fb08461694d838cb1333b9e3d66de8345780ac4` using only the 20 authorized
reused seeds. Its SHA-256 is
`5d1471519972ee8099a211ab61f70da897eac1640d6f190c48c49a74cc2f6814` and its
size is `99,075,876` bytes. A second deterministic regeneration was
byte-for-byte identical.

All `20/20` accepted Arm-B replays and instrumented replays matched the exact
identity fields. The corrected `FIRST_FALSE_CONTACT_SEEK` anchor was available
for `20/20` seeds and each captured state was already pre-action SEEK with
false visible/evaluator contact and ordinary no-de-trap arbitration pending.
The exact D-033 `ALT8_ESTABLISHED` anchor was available for `17/20`; it
remained unavailable at the lifetime boundary for `18471`, `18473`, and
`18478`. No seed or null was discarded.

All `37` available anchor sets and their `259` branch rows passed
branch-order, baseline-creation-order, reward/info/update, no-de-trap,
canonical turn time/energy, logical-action, and anchor-isolation checks. No
branch reacquired dual contact within the frozen `4,096`-transition window.
The artifact contains `909,312` compact retained LFR decision records with the
required per-decision attribution values, plus the required prequential
all-six-output, turn-only, left/right `delta_beacon_forward`, and exact
post-anchor-window support diagnostics, opposite-turn denominator, pair-error
geometry, charging/dual-contact, forward nominal/clipped/stall, cumulative
turn-exposure, and full energy/thermal extrema/reacquisition reports.

This is a corrected Development-lane descriptive result. Its null
reacquisition result does not authorize rescue tuning, a new action or sensor,
organism-side interpolation, a larger learner, planning, reward/RL, or a
successor task.

**surprised_by:** The corrected pre-action anchor moves the treatment start
past the AWAY-to-SEEK entry state, while the corrected branch matrix still
shows no dual-contact reacquisition within the declared horizon. The three
ALT8 lifetime-boundary nulls remain explicit and unchanged.

**disposition:** `CONTINUING`.
