# D-033 — Short-horizon sequence sufficiency audit

- **id:** D-033
- **date:** 2026-09-10
- **exact_sha:** `<protocol freeze SHA; substantive output is executed from this clean SHA>`
- **development_seeds:** `18468..18487` inclusive, reused exactly from accepted D-031R1/D-032 support
- **disposition:** `CONTINUING`

## Question

Is a short, bounded temporal action commitment sufficient to break the
`LEARNED_NO_DETRAP` oscillation and enable resource reacquisition, or is the
useful stochastic-scaffold function richer than simple persistence?

This is evaluator-only Development work. It does not change the organism.

## Provenance and freeze gate

The authorized base is
`0e6fae6201ea7e36c04d4319bfbe536523c9f066` with tree
`cc5bf1fc86c29c5910c7bb9d840485957ee6c6f7`. The accepted D-031R1 artifact is
the only substantive support artifact reused. The D-031R1/D-032 lifetime
horizon remains `70_000` transitions.

The complete executable protocol, anchor reconstruction, causal-state clone,
branch runner, metrics, interpretation categories, focused tests, artifact
writer, and this record are committed before any substantive D-033 branch
output on the official seeds. The exact clean executable SHA is recorded in
the machine-readable artifact after that freeze and is the SHA used for the
substantive run. A later record/artifact-only commit does not change the
executable protocol; a source defect would invalidate the prior run and
require a fresh clean SHA and rerun.

## Frozen protocol

For each seed, first reproduce accepted Arm-B `LEARNED_NO_DETRAP` exactly on
the required identity fields, including the complete 168-weight state and
RNG digests, zero false-contact SEEK explorer calls, and one policy-RNG draw
per false-contact SEEK decision.

Reconstruct two evaluator-selected pre-action anchors:

1. `MATCHED_FIRST_DELEGATION`: the exact D-032 matched first-delegation state,
   with all pre-treatment prefix, observation, environment, controller,
   learner, RNG, and update-prefix checks.
2. `ALT8_ESTABLISHED`: the first B pre-action state immediately after eight
   completed false-contact SEEK actions that are exclusively strict alternating
   left/right turns, with no contact, forward, or wait action. Missing anchors
   remain explicitly unavailable.

From isolated clones of each available B anchor, run `BASELINE_B` and, at
lengths exactly `2, 4, 8, 16`, run:

`REPEAT_B_PROPOSED`, `TURN_LEFT_RUN`, `TURN_RIGHT_RUN`, `MOVE_FORWARD_RUN`,
`WAIT_RUN`, `ALTERNATE_LR`, and `ALTERNATE_RL`. At the matched anchor only,
`REPEAT_A_FIRST` is a hindsight/scaffold-action reference. It is not an
organism policy. A one-step repeat of B's proposed action is an equivalence
regression only, not a substantive treatment.

Every forced step runs the unchanged B controller/action-selection pipeline,
records the proposed action, replaces only the physical action, performs one
real transition, requires reward `0.0` and `info == {}`, and updates unchanged
D-027 exactly once from the physical action and actual next six-channel
observation. After the requested prefix, the unchanged B behavior resumes.
Branches stop at reacquisition, inherited termination/truncation, or 4096
branch transitions from the anchor. All geometry, distances, anchor labels,
sequence labels, and outcome metrics remain evaluator-only.

## Organism boundary

The inherited four actions, six visible channels, D-027 168-weight learner,
executed-action update, D-031R1 no-de-trap controller, reward, information
boundary, D-024 contact geometry, and D-020 physical semantics are unchanged.
No history, persistence bit, action macro, new sensor/physics, larger learner,
rollout, world model, planner, rescue rule, reward/value, or successor task is
introduced.

## Required reporting

Per-branch records retain forced proposals/actions, reacquisition and latency,
stop/termination reason, energy, path/displacement/visible-beacon metrics,
release and total action counts, forward-boundary counts, exact alternating
runs and recurrence, learner/update/RNG digests, and isolation checks. Pooled
records retain all available seeds, direct summaries, intervention timing,
matched per-seed signs against baseline, seed lists, and zero discarded
outliers. There is no weighted sequence score or universal pass threshold.

## Observed

Pending the clean protocol freeze and authorized substantive execution. No
official D-033 intervention outcome is recorded in this protocol-only commit.

## Surprised by

Pending substantive execution.

## Provisional reading

The frozen interpretation distinguishes measured outcomes from inference. A
positive result can support only a bounded Development-lane component-level
inference at the observed anchors; it cannot authorize organism persistence,
history, recurrence, planning, world-model capacity, or D-034.

## Next

Execute the frozen artifact on the exact reused support after the freeze gate,
then preserve nulls and competing explanations in the final record. Flow
controls any later decision.
