# Development and Evidence Workflow

Aweform uses two deliberately different research lanes so exploratory iteration can be fast without weakening formal evidence.

## Development lane — `D-NNN`

Development work asks what mechanism or world change is worth trying next. It is exploratory and descriptive, not confirmatory.

Normal development may:

- use legal development/debug seeds;
- visualize trajectories and inspect internal traces;
- tune, replace, or abandon mechanisms;
- compare cheap alternatives;
- preserve null and negative outcomes;
- run several meaningful iterations in one evening.

Each meaningful development experiment receives a lightweight record under `development/`. The record must preserve enough context to reconstruct what happened. `surprised_by` and `disposition` are required because they capture what changed the project’s understanding and what happened next.

Approximately 60 lines is a useful default when sufficient, not a hard limit or merge gate.

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

Historical EXP-000 through EXP-003 retain their existing identifiers and records. The new D-series does not retroactively relabel earlier development work.

## Review proportionality

Ordinary D-lane work does not require dual exact-SHA review-of-record when it makes no evidence claim and does not alter a durable architecture, information, sensory/plasticity, safety, frozen-evidence, or reserved-seed boundary.

Formal Sol + Opus review remains required for evidence-lane claims/executions and durable boundary changes. Flow retains merge authorization.

## World design discipline

Do not make an ecology harder merely because a competent simple controller succeeds.

Before running a new ecology-development record, state what regulatory conflict or capability the world is intended to create. Then distinguish:

- **degenerate solution** — viability is maintained by bypassing the intended conflict through an accounting loophole, indefinite stillness, meaningless edge oscillation, or similar shortcut;
- **legitimate simple solution** — a fixed controller genuinely regulates the intended competing constraints using organism-visible information.

A legitimate simple solution is evidence that learning has not yet earned additional machinery. Preserve it rather than designing it away.

## Developmental stage versus lifetime segment

A lifetime is one continuous causal trajectory. A harness/storage/logging/checkpoint segment is not an organism event and must be invisible to the organism.

A deliberate developmental-stage reset is different. Under the current V0.3 convention it is explicitly recorded as a lifecycle/new-lifetime event; learned state resets there for now. Cross-stage inherited learned state is a later research question, not a side effect of infrastructure.

## Current provisional sequence

This ordering is a working hypothesis, not a commitment:

- **D-001** — current EXP-003 ecology degeneracy probe.
- **D-002** — minimal thermal ecology.
- **D-003** — fixed-policy / fixed-parameter sufficiency characterization.
- **D-004** — continuous-lifetime harness/infrastructure consolidation only where it materially improves iteration speed.
- **D-005** — cheapest adaptive scalar learner.
- **D-006** — fixed life-inspired circuits with zero plasticity.
- **D-007** — first plastic candidates; minimal adaptive gains versus a tiny action-conditioned predictor, with reservoir only as a capacity diagnostic if useful.
- **D-008** — different lifetime histories followed by a matched common probe.

Development results may change the order.

## Cautions carried into future development

These are not implementation requirements for the reset foundation:

- **D-002 thermal:** declare whether heat tracks charging contact, charge offered, accepted storage increase, actuator work, or another quantity. Clipping at full energy can otherwise silently re-admit indefinite docking.
- **D-007 action-conditioned learning:** record suitable evaluator-side state/mode-action visitation diagnostics before interpreting counterfactual model queries; on-policy data can lock in false beliefs about rarely sampled actions.
- **Prediction failure:** poor one-step prediction may indicate partial observability, omitted state, stochasticity, or model-capacity failure. Do not automatically interpret it as evidence that a larger learner is needed.
- **Future common probe:** equalize non-plastic probe state and transplant the complete declared plastic state, not merely headline weights.
