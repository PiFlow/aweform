# Development and Evidence Workflow

Aweform uses two deliberately different research lanes so exploratory iteration can be fast without weakening formal evidence.

## Development lane — `D-NNN`

Development work asks what mechanism, information boundary, world change, or scientific diagnosis is worth trying next. It is exploratory and descriptive, not confirmatory.

Normal development may:

- use legal development/debug seeds;
- visualize trajectories and inspect internal traces;
- tune, replace, or abandon mechanisms;
- compare cheap alternatives;
- preserve null and negative outcomes;
- run several meaningful iterations in one evening;
- use evaluator-only causal branches, shadow analyses, or diagnostics when their information boundary is explicit and causally inert.

Each meaningful development experiment receives a lightweight record under `development/`. The record must preserve enough context to reconstruct what happened. `surprised_by` and `disposition` are required because they capture what changed the project’s understanding and what happened next.

Approximately 60 lines is a useful default when sufficient, not a hard limit or merge gate. Later audits may legitimately require longer records when exact causal semantics, invalidated provenance, or support/null structure must be preserved.

A D-result may motivate an evidence protocol and may be cited as developmental context. It does **not** count as confirmatory evidence for a later claim.

There is no universal numeric graduation rule. Promotion to evidence is a scientific judgment about whether an important claim is mature enough to justify freezing its mechanism, environment, controls, analysis, and untouched seeds.

## Evidence lane — `EXP-NNN`

Evidence experiments are reserved for claims important enough to justify formal cost.

Before untouched evidence seeds are executed, the relevant protocol freezes the claim-bearing elements needed for valid inference, including as applicable:

- mechanism and comparator;
- environment and perturbations;
- observation/action and plasticity boundaries;
- seed reservation;
- primary outcomes and contrasts;
- analysis and interpretation rules.

Evidence execution requires exact-SHA reproducibility, matched controls appropriate to the claim, independent review, and preservation of negative results.

Historical EXP-000 through EXP-003 retain their existing identifiers and records. The D-series does not retroactively relabel earlier development work.

## Review proportionality

Ordinary D-lane work does not require dual exact-SHA review-of-record when it makes no evidence claim and does not alter a durable architecture, information, sensory/plasticity, safety, frozen-evidence, or reserved-seed boundary.

Formal independent review remains required for evidence-lane claims/executions and durable boundary changes under `AGENTS.md` and ADR 0013. Flow retains merge authorization.

## Development evidence classes must stay distinct

Development records increasingly use several different kinds of evidence. Do not collapse them into one category merely because they appear in one D-record.

- **Causal organism intervention** — the organism/controller actually differs between matched runs.
- **Shadow learning or readout** — state is learned or analyzed but has zero behavioral influence.
- **Evaluator-only counterfactual branch** — an isolated clone is used to ask what another action or intervention would have caused; it is not part of the organism's experience.
- **Post-hoc analysis** — completed trajectories are analyzed after execution.
- **Evaluator upper bound / privileged diagnostic** — hidden simulator state may be used to diagnose what information would be sufficient, but must not be interpreted as organism access.
- **Identity or validity control** — checks that instrumentation, cloning, branch order, or alternate implementation did not change the canonical causal path.

Every record should state which class supports each important conclusion.

## World design discipline

Do not make an ecology harder merely because a competent simple controller succeeds.

Before running a new ecology-development record, state what regulatory conflict or capability the world is intended to create. Then distinguish:

- **degenerate solution** — viability is maintained by bypassing the intended conflict through an accounting loophole, indefinite stillness, meaningless edge oscillation, or similar shortcut;
- **legitimate simple solution** — a fixed controller genuinely regulates the intended competing constraints using organism-visible information.

A legitimate simple solution is evidence that learning has not yet earned additional machinery. Preserve it rather than designing it away.

## Developmental stage versus lifetime segment

A lifetime is one continuous causal trajectory. A harness/storage/logging/checkpoint segment is not an organism event and must be invisible to the organism.

A deliberate developmental-stage reset is different. Under the current V0.3 convention it is explicitly recorded as a lifecycle/new-lifetime event; learned state resets there for now. Cross-stage inherited learned state is a later research question, not a side effect of infrastructure.

## Current development state

The original provisional D-001→D-008 sequence in this document has been superseded by executed development and is intentionally **not** maintained here.

The canonical committed development ledger is [`development/INDEX.md`](../development/INDEX.md). At the time of this update, committed development extends through **D-045**. Current authorized-but-not-yet-committed work is tracked by the relevant GitHub authorization issue/PR rather than predicted in this workflow document; D-046 is currently authorized by issue #165 and is not yet a committed D-record.

This document defines **how** development and evidence are conducted. It should not duplicate a growing list of D-records or predict a future sequence that repository evidence may immediately overturn.

## Durable cautions carried forward

These are process lessons, not implementation requirements for any successor stage:

- **Physical/accounting semantics must be explicit.** When a causal variable can be clipped, saturated, delayed, or thresholded, record what underlying physical quantity drives energy, heat, contact, or failure. Otherwise a bookkeeping choice can silently create a behavioral loophole.
- **On-policy support matters for counterfactual interpretation.** Before trusting an action-conditioned model on unexecuted actions, record suitable support/visitation diagnostics. Sparse action experience can create apparently confident but unsupported counterfactuals.
- **Prediction failure is not automatically a capacity failure.** It may indicate partial observability, omitted permitted state, stochasticity, data coverage, experience-distribution collapse, intervention timing, or model-capacity failure. Diagnose these separately before enlarging a learner.
- **Matched probes must transplant the complete declared causal/plastic state.** Equalize non-plastic state and RNG semantics where the question requires it; do not compare only headline weights.
- **Evaluator information must never leak causally.** Hidden geometry, future branch outcomes, treatment labels, anchor outcomes, and post-action information may diagnose a problem but cannot silently become organism inputs.
- **Critical causal claims need independent validity checks when helpers are shared.** D-040 showed why a chain of analyses that reuses common high-level helpers can carry correlated mistakes. For high-leverage conclusions, independently reconstruct anchor semantics, clone state, branch behavior, and identity gates from lower-level accepted components where practical.
- **Branching audits need causal-state and order controls.** A matched evaluator counterfactual should preserve all relevant physical, controller, learner, RNG, and transient state; OFF-vs-OFF clone identity and branch-order invariance are useful negative controls.
- **Invalidated runs remain part of provenance.** Preserve the exact executable SHA, artifact hash/size when available, defect, and rerun relationship. Do not pool invalidated outputs into accepted interpretation.
- **Fresh holdout development support can still be useful without becoming evidence.** When a D-audit uses reused support plus a frozen fresh holdout, keep their roles separate and do not tune the frozen protocol after viewing the holdout.
