# D-033 — Short-horizon sequence sufficiency audit

- **id:** D-033
- **date:** 2026-09-10
- **exact_sha:** `fdb1e6b4ffba26d656936936ca7fb72bf34a98aa` (clean executable protocol freeze; substantive output is executed from this SHA)
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

The frozen executable protocol ran on all 20 reused seeds from
`fdb1e6b4ffba26d656936936ca7fb72bf34a98aa`. The resulting artifact is
`development/D-033-short-horizon-sequence-sufficiency-audit.json`, SHA-256
`882808043cf080c33b8fbb1e968472ff67ffb4f9ee67522e8c314ecaac77829e`.

All 20 Arm-B `LEARNED_NO_DETRAP` replays matched the accepted identity fields,
including the complete learner state; all instrumented replays were exact.
All 20 matched first-delegation anchors were reconstructed. The first
`ALT8_ESTABLISHED` anchor was available for 17 seeds; it was unavailable at
the lifetime boundary for `18471`, `18473`, and `18478`. No seed was
discarded.

All available anchors passed the exact baseline-continuation, one-step
equivalence, branch-order, and baseline-creation-order checks. Every branch
preserved the evaluator-only boundary checks, ran the unchanged B selection
pipeline once per forced step, and performed exactly one executed-action
D-027 update per completed transition.

| Anchor | Baseline reacquisitions | `REPEAT_B_PROPOSED` (2/4/8/16) | Other reacquisitions |
| --- | ---: | ---: | --- |
| `MATCHED_FIRST_DELEGATION` (20 seeds) | 0/20 | 0/20, 0/20, 0/20, 0/20 | `TURN_RIGHT_RUN:2` 1/20; `ALTERNATE_RL:16` 1/20 |
| `ALT8_ESTABLISHED` (17 seeds) | 0/17 | 0/17, 0/17, 0/17, 0/17 | 0/17 for every frozen control |

Both matched-anchor reacquisitions occurred on seed `18474`, after release:
`TURN_RIGHT_RUN:2` reacquired at branch transition 15 and
`ALTERNATE_RL:16` at branch transition 27. No reacquisition occurred during
an intervention prefix. The hindsight `REPEAT_A_FIRST` reference produced
0/20 reacquisitions at every length.

## Surprised by

The repeated B-proposed-action family produced no reacquisition at either
anchor, while two directional controls succeeded on the same matched-anchor
seed. Also, three seeds reached lifetime end without an eight-action strict
alternating B run, so the ALT8 anchor has a smaller available support.

## Provisional reading

These are descriptive Development-lane outcomes, not confirmatory evidence.
On this support, short same-action persistence matching B's proposed action
did not break the observed oscillation. The two isolated directional-control
reacquisitions on one matched-anchor seed are consistent with action-direction
and local geometry effects, but do not establish a persistence mechanism or
general sufficiency. The ALT8 results provide no positive reacquisition
outcome at the available anchor states. The result does not distinguish the
causal contributions of persistence, symmetry breaking, learned action
selection, and non-myopic benefit.

Nothing here authorizes organism history, persistence, multi-step policy,
planning, a world model, or D-034.

## Next

Preserve the nulls and competing explanations above. Flow controls any later
decision; no successor task is authorized by this record.
