# D-047 — V0.5 shadow action-consequence discrimination (frozen protocol)

- **id:** D-047
- **issue:** [#168](https://github.com/PiFlow/aweform/issues/168)
- **lane:** Development / evaluator-only readiness audit
- **date:** 2026-09-25
- **authorized_base_sha:** `a265bf1b2932d9af1dfa9719d53e42dfef688ce3`
- **frozen_executable_protocol_sha:** recorded in the post-execution result layer
- **development_seeds:** D-046's existing `21046..21065`; no new seed
- **disposition:** `CONTINUING`

This file records the frozen D-047 protocol before execution. The completed
record, official artifact, result layer, exact executable SHA, and validation
provenance are added only after execution from that exact pushed SHA.

## Question and frozen boundary

D-047 asks whether the frozen D-046 action-conditioned predictor preserves the
direction and relative magnitude of real one-step consequence differences
between alternative raw wheel commands from the same organism-visible state.
It does not choose or rank actions and creates no lived organism trajectory.

The amendment to issue #168 makes the committed D-046 artifact the canonical
learned-state source. D-047 verifies that artifact's exact size, SHA-256,
task/schema/executable provenance, ordered seeds, and all 20 per-seed full
learner weight digests. It loads exactly 528 finite full-learner weights per
seed and reuses the unchanged D-046 state transform, action normalization,
66-feature map, bounds, and prediction arithmetic read-only. It neither
reconstructs nor claims absolute predictions for unavailable state-only
weights; state-only and zero-change pairwise contrasts are structural zero
because both are action-indifferent at a fixed state.

## Frozen evaluation

The audit uses only D-046 poses `H0..H8`, actions `A0..A8`, and seed-specific
full learners `21046..21065`. Every candidate executes in its own freshly
reset, unchanged D-045 one-step branch. All 9 actions for a seed/pose receive
the identical eight-channel starting observation. Fixed ascending action-ID
orientation produces exactly 1,620 candidate evaluations, 6,480 unordered
pairs, and 51,840 channel-expanded comparisons.

The artifact will retain contrast MAE, exact negative/zero/positive sign
agreement, actual and predicted ties, non-tie sign agreement, and support.
It will report all eight channels separately and stratify by seed, action
pair, pose, boundary involvement, and contact-transition involvement. Channel
families remain separate; no scalar competence, desirability, utility, need,
reward, or action ranking is constructed.

## Causal-isolation controls

The runner requires:

- exact canonical D-046 artifact and per-seed full-weight digest identity;
- read-only learner weights and zero updates;
- identical source observation for all candidates within each seed/pose;
- fresh isolated unchanged D-045 branch per candidate;
- forward/reverse branch-order invariance;
- reward exactly `0.0` and organism-facing `info == {}`;
- no evaluator metadata reaching model input;
- no formal reserved seed.

## Required validation

Before handoff, the correction will record focused D-047 tests, full
`pytest -q`, `ruff check .`, strict `mypy src --strict`, Python
compile/import checks, `git diff --check`, authorized-base ancestry,
exact-current-HEAD CI, and byte-identical independent regeneration.

## Explicit non-goals

D-047 adds no history, recurrence, sensor, organism-visible state, predictor
capacity, retraining, utility, need, planner, policy, behavioral influence,
EXP work, or D-048 work. It does not modify D-045/D-046 source, physics,
learner arithmetic, calibration, historical artifacts, records, or
reservations.


