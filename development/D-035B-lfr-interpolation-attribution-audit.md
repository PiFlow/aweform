# D-035B — L/F/R interpolation attribution audit

- **id:** D-035B
- **issue:** [#123](https://github.com/PiFlow/aweform/issues/123)
- **lane:** Development
- **authoritative_base_sha:** `d40681d25cd4cc67e359004ffcd63819e40b42a4`
- **base_tree_sha:** `50510ba772a1d53960f7f5870feb6b7b510cacf4`
- **development_seeds:** `18468..18487` inclusive, reused exactly
- **underlying lifetime horizon:** `70,000` transitions
- **branch horizon:** `4,096` transitions from each isolated anchor
- **status:** protocol frozen; substantive output complete
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

The complete executable protocol, exact Arm-B replay gate, exact anchor
reconstruction, LFR formula/cap semantics, isolated branch runner, metrics,
interpretation rules, artifact writer, and focused tests were committed before
official output on `18468..18487`.

- **protocol_only_freeze_sha:** `8a0e23fbee23f3c47a6111dd3e23882f2402b176`
- **implementation_probe_sha:** `8a0e23fbee23f3c47a6111dd3e23882f2402b176`
- **artifact_sha256:** `877c7355d62a5254442fa3bcb3599c251c6800a7b616442421082661151d1086`
- **artifact_size_bytes:** `3,491,326`

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

1. `FIRST_FALSE_CONTACT_SEEK` is the first completed transition whose
   post-controller mode is SEEK and whose visible and evaluator contact bits
   are false before and after the transition. This includes the inherited
   AWAY-to-SEEK entry decision when it is the first qualifying decision.
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
boundary classes, strict alternation and side reversals, LFR directional
interpolation error against evaluator station bearing, cap saturation, and
D-027 prediction compatibility with executed actions and actual next visible
observations. No seed or null is discarded.

The result is descriptive Development evidence only. It cannot establish a
learned interpolation, consciousness, emotion, subjective experience,
genuine life, metabolism, or a confirmatory claim.

## Substantive output

The official artifact was generated from clean executable SHA
`8a0e23fbee23f3c47a6111dd3e23882f2402b176` using only the 20 authorized
reused seeds. Its SHA-256 is
`877c7355d62a5254442fa3bcb3599c251c6800a7b616442421082661151d1086` and its
size is `3,491,326` bytes.

All 20 accepted Arm-B replays and instrumented replays matched the frozen
identity fields, including the complete D-027 state and RNG digests. The
`FIRST_FALSE_CONTACT_SEEK` anchor was available for `20/20` seeds. The exact
D-033 `ALT8_ESTABLISHED` anchor was available for `17/20`; it remained
unavailable at the lifetime boundary for `18471`, `18473`, and `18478`. No
seed or null was discarded. All available `BASELINE_B`, fixed-cap, and
interpolated-cap branches passed branch-order, baseline-creation-order,
reward/info/update, no-de-trap, canonical turn time/energy, logical-action,
and anchor-isolation checks.

No branch reacquired dual contact within the frozen 4,096-transition window.
This held for `BASELINE_B` and all six LFR branches at both available anchor
families. The LFR branches did produce descriptive geometry changes: they
generally moved toward a small final evaluator distance while consuming the
canonical turn energy, but did not convert that geometry into contact
reacquisition on this support. Interpolated branches retained the same
discrete seek direction and reported their evaluator-only directional error,
saturation, side-reversal, alternation, and D-027 prediction-compatibility
diagnostics in the artifact.

This is a Development-lane descriptive result. The null reacquisition result
does not authorize rescue tuning, a new action or sensor, organism-side
interpolation, a larger learner, planning, reward/RL, or a successor task.

**surprised_by:** The capped LFR branches changed evaluator geometry
substantially relative to the frozen Arm-B continuation, yet none reacquired
dual contact within the branch horizon. The exact ALT8 anchor remained
unavailable for the same three lifetime-boundary seeds as D-033, and those
nulls are retained.

**disposition:** `CONTINUING`.
