# Aweform Research Roadmap

## A. Purpose

Aweform is being developed from minimal self-maintenance toward adaptive, machine-native cognition and eventual physical embodiment. The project’s long-term orientation and humility boundaries are defined in the [`North Star`](north-star.md); this document adds chronological context and decision memory without replacing the North Star, developmental principles, ADRs, development records, or frozen experiment protocols.

Aweform now operates with two research lanes described in [`development-evidence-workflow.md`](development-evidence-workflow.md): fast descriptive `D-NNN` development and formal `EXP-NNN` evidence.

## B. Completed / evidence ledger

### EXP-000 — Interoception and viability

EXP-000 is completed with confirmatory support. Its narrow result concerns the programmed homeostatic mechanism and that specific ablation in that specific capped simulator; it makes no claim about consciousness, biological life, intelligence, or general artificial life. See the canonical [`EXP-000 final result record`](../experiments/EXP-000-final-result-record.md).

### EXP-001 — Interoception versus open-loop homeostasis

EXP-001 is **CLOSED**. Its formal confirmatory result is `C_GREATER`: calibrated energy-blind C had greater mean capped lifespan than interoceptive B in the frozen 1000-transition EXP-001 simulator. This is a narrow result for the specified programmed controllers and environment, not evidence that interoception is generally harmful or that fixed schedules are generally superior. See the canonical [`EXP-001 closeout`](../experiments/EXP-001-closeout.md).

### EXP-002 — Interoceptive SEEK-entry threshold

Formal calibration completed and selected B50 under the recorded rule. Confirmatory execution remains deliberately unexecuted on untouched seeds `50001–51000`. See the canonical [`EXP-002 protocol`](../experiments/EXP-002-interoceptive-seek-threshold.md), [`calibration evidence`](../experiments/EXP-002-calibration-result.md), and [`confirmatory statistical addendum`](../experiments/EXP-002-confirmatory-statistical-addendum.md).

## C. Historical development foundation

### EXP-003 — Localized charging station + IR-like beacon

EXP-003 is development/instrumentation only. It separates sensing from energy acquisition, requires physical station occupancy to recharge, and established the station/beacon interface used by the current development substrate. Its historical records remain canonical under the EXP-003 identifier; they are not retrospectively renamed into the new D-series. The localized-charging interface remains governed by [`ADR 0008`](adr/0008-exp-003-localized-charging-interface.md).

ADR 0009 subsequently opened V0.2 bounded observation-history state and remains the valid historical authorization for the V0.2 work performed under it.

## D. Developmental process reset

The previous roadmap treated most developmental changes as if they were approaching formal evidence. That preserved rigor but created too much ceremony for exploratory iteration.

The project now separates:

- **D-series:** rapid descriptive development on legal development seeds;
- **EXP-series:** important claims worth freezing and testing on untouched reserved seeds with exact-SHA review.

Development results may motivate evidence experiments but cannot count as confirmatory evidence for their claims.

## E. Active provisional D-sequence

The sequence below is intentionally provisional. Development evidence may reorder, split, merge, or abandon items.

### D-001 — Current ecology degeneracy probe

Empirically verify the already-identified current EXP-003 ecological degeneracy and cheap constant policies before changing the world.

The current source arithmetic predicts that a docked organism can `WAIT` indefinitely while gaining energy until clipping at maximum. D-001 should establish the actual behavioural consequence using development seeds and lightweight descriptive records.

No thermal mechanism is required for D-001.

### D-002 — Minimal thermal ecology

Introduce temperature as a second interoceptive viability dimension with the smallest coherent dynamics needed to study energy/heat coupling.

Candidate ingredients include charging heat, actuator heat, passive cooling, thermal interoception, and thermal consequences such as reduced charge efficiency and/or viability threat.

**Distance-dependent cooling is not pre-frozen.** Start with the smallest coherent thermal world and let development reveal whether station-local heat or distance-dependent cooling is needed.

Before execution, the D-record should state what regulatory conflict the ecology is intended to create so a degenerate shortcut can be distinguished from a legitimate simple solution without post-hoc reinterpretation.

Thermal implementation must explicitly declare what physical quantity drives heat. In the existing energy system, charger input can be offered while realized stored-energy increase is zero at the energy ceiling. Tying heat only to accepted storage increase could silently re-admit indefinite docking. Charge-efficiency throttling alone may also fail to remove docking if effective charging remains above basal cost.

### D-003 — Fixed-policy / fixed-parameter sufficiency

Characterize whether cheap non-learning policies already regulate the thermal ecology.

Useful controls include obvious degeneracies, fixed excursion patterns, random walk, and a non-learning `THERMOSTATIC_SHUTTLE`-type controller using organism-visible temperature/contact plus minimal phase state.

A competent fixed feedback controller solving a coherent world is **evidence**, not a reason to make the world harder. Do not redesign the ecology merely to force learning to become necessary.

### D-004 — Continuous-lifetime harness / infrastructure consolidation

Consolidate duplicated development infrastructure only where doing so materially increases iteration speed or is required for continuous lifetime execution.

Do not pre-build speculative world-model, serialization, checkpoint, or learner frameworks. Harness segmentation remains invisible to the organism under ADR 0010.

### D-005 — Cheapest adaptive scalar learner

Introduce the smallest genuinely experience-dependent scalar adaptation worth testing. Preserve inspectability and lifetime continuity.

The goal is to determine whether plasticity changes future behaviour through organism-visible consequences, not to maximize benchmark performance.

### D-006 — Fixed life-inspired circuits, zero plasticity

Introduce the structural computation needed for a fair ablation before the first richer plastic candidate. Candidate circuits may include delay-and-compare temporal beacon processing plus energy and thermal feedback, but exact structure remains developmental rather than frozen here.

### D-007 — First plastic candidates

Compare small plastic candidates only after D-006 supplies the zero-plasticity structural control.

Current candidates include:

- minimal learned/adaptive gains;
- a tiny action-conditioned predictor;
- a tiny reservoir/readout only as a capacity diagnostic if useful.

The first prediction target and horizon remain unresolved. A clean starting diagnostic may be one-step action-conditioned prediction of `Δenergy` and `Δtemperature` from controller-visible state plus the organism’s own action. If one-step prediction is trivial, that is information rather than a reason to manufacture a harder horizon.

Poor prediction must not automatically be interpreted as evidence that a larger learner is required. It may instead reflect omitted organism-visible state, partial observability, stochasticity, retained-state insufficiency, or true model-capacity failure.

Before interpreting action-conditioned counterfactual queries, record suitable evaluator-side state/mode-action visitation diagnostics. On-policy learning can otherwise lock in false beliefs about rarely sampled actions.

### D-008 — Different histories → matched common probe

Give identically initialized organisms different lifetime histories, then compare them under a common matched probe to ask whether retained experience is behaviourally load-bearing.

A future clean probe should equalize non-plastic state, match the probe world/RNG, freeze learning where appropriate, and inject the **complete declared plastic state** rather than only headline weights.

## F. Candidate EXP-004 evidence milestone

`EXP-004` is reserved conceptually as the next major evidence milestone, not as the next implementation step. No EXP-004 seed range is reserved by this roadmap.

The previous provisional roadmap described EXP-004 as an ecological-robustness/station-relocation experiment. That proposal remains part of project history but is no longer the active next protocol after the developmental-process reset.

The current candidate direction is stronger and later: **does lifetime experience causally alter later homeostatic behaviour?** A particularly sharp candidate is history-conditioned behavioural divergence in a matched common probe world between identically initialized organisms.

This claim is not frozen. D-development must establish the mechanism, appropriate matched controls, complete plastic-state semantics, and a useful probe before an evidence protocol is opened.

## G. Durable scientific rules for development

### Do not design worlds to require the capability you want to celebrate

A simple controller that genuinely regulates the intended competing constraints is a legitimate result.

Distinguish it from a **degenerate solution** that maintains viability by bypassing the intended regulatory problem through an accounting loophole, indefinite docking/stillness, meaningless boundary oscillation, or similar shortcut.

### Learning is not the default explanation for prediction failure

When a predictive mechanism fails, development records should distinguish partial observability, omitted state, stochasticity, causal mis-specification, data coverage, and learner capacity before increasing model size.

### Continuous lifetime is causal, not merely a logging convention

Within a developmental stage, short harness horizons do not reset the organism. A deliberate stage reset is an explicit lifecycle/new-lifetime event under ADR 0010.

## H. Later directions

Later developmental directions include nonstationarity, partial observability that earns memory, stronger prediction and planning, safe-surplus exploration, quiescent consolidation when its function is justified, sandboxed computer-native embodiment, and eventual physical embodiment.

Darwinian evolution, heredity, and cross-stage inherited learned state remain separate later research questions rather than shortcuts for finding the first learner.

## I. Decision-log convention

- Lightweight development records live in `development/`.
- Experiment-specific frozen evidence decisions live in `experiments/`.
- Durable architecture and information-boundary decisions live in `docs/adr/`.
- This roadmap gives chronological context and provisional future direction.
- Result artifacts remain canonical evidence.
- Roadmap prose must never silently overwrite historical experiment records.
