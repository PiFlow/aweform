# Aweform Research Roadmap

## A. Purpose

Aweform develops machine-native cognition by introducing the smallest additional mechanism that a developmental environment genuinely makes useful.

The central loop remains:

`internal state → perception → action → consequence → retained internal change → changed future behaviour`

The project must distinguish programmed mechanisms, learned mechanisms, descriptive observations, hypotheses, and inferential claims. It must not equate convincing behaviour with consciousness, subjective experience, genuine life, or biological equivalence.

Historical experiment records and ADRs remain authoritative for the work performed under them. Roadmap prose must never silently overwrite historical experiment records.

## B. Process reset: development and evidence are separate lanes

The project now separates rapid development from formal evidence. The workflow is defined in [`development-evidence-workflow.md`](development-evidence-workflow.md).

### Development lane — `D-NNN`

Fast, descriptive iteration using legal development/debug seeds. Several meaningful iterations in one evening should be normal. Development may visualize, tune, abandon, or replace mechanisms freely, but it makes no confirmatory claim.

### Evidence lane — `EXP-NNN`

Reserved for important claims worth freezing. Evidence work retains untouched reserved seeds, exact-SHA reproducibility, matched controls, independent review, frozen analysis, and preservation of negative results.

Development results may motivate an EXP protocol but cannot count as confirmatory evidence for that later claim.

Historical EXP-000 through EXP-003 keep their original identifiers. They are not retroactively relabelled as D-series work.

## C. Historical evidence and development ledger

### EXP-000 — Interoception / viability

Completed evidence milestone. Canonical protocol/results remain under `experiments/` and the associated artifacts.

### EXP-001 — Persistent exploration / energetic interoception

Completed evidence milestone. Historical protocol, calibration, confirmatory run, and analysis remain authoritative.

### EXP-002 — Interoceptive seek threshold

Calibration is complete. Confirmatory execution remains specified-but-unexecuted on untouched seeds `50001–51000`.

Nothing in the developmental reset authorizes executing those seeds.

### EXP-003 — Localized charging / bounded observation history

Development-only historical work under the V0.2 permission boundary. The localized charging interface remains governed by [`ADR 0008`](adr/0008-exp-003-localized-charging-interface.md), and the bounded one-step observation-history state used in this work remains governed by ADR 0009.

EXP-003 established the current localized-charging world and bounded observation-history mechanisms used as the starting point for the new development lane. It remains historical EXP-003 and is not renamed D-000 or D-001.

The current ecology has an important verified degeneracy: a docked organism can WAIT indefinitely because charging exceeds basal cost and there is no competing internal constraint such as heat. That fact motivates D-001/D-002 development but is not itself a new evidence claim.

## D. Current developmental direction

The active work now moves through lightweight D-series development.

The sequence below is **provisional**. Development evidence can change it.

### D-001 — Current-ecology degeneracy probe

Empirically verify the already-identified trivial docking optimum and cheap constant policies in the existing EXP-003 ecology.

No thermal mechanism is added in D-001.

The aim is to establish a concrete developmental baseline before changing the world.

### D-002 — Minimal thermal ecology

Introduce a second engineered viability variable: temperature.

Candidate ingredients include:

- charging generates heat;
- actuator use generates heat;
- inactivity/off-charge state cools;
- temperature is organism-visible interoception;
- excessive heat reduces charge efficiency and/or threatens viability.

Do **not** freeze distance-dependent cooling in advance. Start with the smallest coherent dynamics and observe whether they create a degenerate boundary oscillator or a genuine competing-homeostasis problem.

Before execution, the D-record should state what regulatory conflict the ecology is intended to create. This prevents post-hoc redefinition of a successful cheap controller as a failure of the world.

A thermal implementation must explicitly declare what quantity drives heat. In particular, the current energy model distinguishes charger energy offered from battery-energy increase accepted after clipping at maximum energy. Heating only from accepted storage increase could accidentally make a full docked organism stop heating and preserve `DOCK_FOREVER`.

Likewise, charge-efficiency throttling alone removes indefinite docking only if effective charging can fall below basal cost.

These are development questions, not constants frozen by this roadmap.

### D-003 — Fixed-policy / fixed-parameter sufficiency

Characterize whether simple non-learning controllers already regulate energy and temperature coherently.

Cheap controls should include obvious cases such as stillness, docking, fixed excursions, persistent/random exploration, and a thermostatic shuttle using organism-visible temperature/contact plus minimal action-phase state.

A competent fixed feedback controller solving a coherent world is **evidence**, not a reason to make the world harder.

Do not tune ecology merely to force learning to become necessary.

### D-004 — Continuous-lifetime harness/infrastructure consolidation

Consolidate duplicated development runners or add lifetime-continuation infrastructure only where it materially improves iteration speed or causal clarity.

Do not pre-build speculative world-model, serialization, checkpoint, or learner frameworks.

A lifetime is one continuous causal trajectory. Harness, logging, visualization, storage, or future checkpoint segments are engineering boundaries only and must not create organism-visible resets or clocks.

### D-005 — Cheapest adaptive scalar learner

Test the minimum genuinely experience-dependent adaptation that can alter later behaviour while obeying V0.3 sensory/plasticity closure.

The purpose is to establish a cheap adaptive baseline, not to prove sophisticated cognition.

### D-006 — Fixed life-inspired circuits, zero plasticity

Introduce the smallest structural circuits that make sense for the current regulatory problem, but freeze their gains/parameters.

This provides a structural ablation before plasticity is credited with later effects.

### D-007 — First genuine plastic candidates

Compare minimal plastic mechanisms after the fixed structural baseline exists.

Candidate directions include:

- minimal learned gains or similarly cheap adaptive structure;
- a tiny action-conditioned predictor using controller-visible state and the organism's own action;
- a small reservoir only as a capacity diagnostic if simpler structures fail.

The exact prediction target and horizon remain unresolved. A clean initial diagnostic may be one-step prediction of `Δenergy` and `Δtemperature`, but the project must not lengthen the horizon merely to manufacture difficulty.

An on-policy action-conditioned model may be poorly supported for actions it stops taking. Before first plastic/action-conditioned runs, evaluator-side diagnostics should preserve relevant state/mode-action visitation counts so false self-reinforcing beliefs can be distinguished from well-supported learning.

Poor one-step prediction does not automatically imply that a larger learner is needed. It may expose omitted state, partial observability, genuine stochasticity, or learner-capacity limits. Development records must distinguish these possibilities before increasing model capacity.

### D-008 — Different lifetime histories → matched common probe

Raise identically initialized organisms under different closure-valid histories, then compare them in a matched common probe designed to isolate retained plastic history.

A future clean probe should equalize all non-plastic organism state and transfer the complete declared plastic state, not merely headline weights. Depending on the learner this may include optimizer/adaptation state, eligibility traces, consolidation/plasticity-modulation state, recurrent learned state, and organism-owned RNG state.

The formal probe semantics are intentionally not frozen yet.

## E. World-design discipline

Aweform must not create an ecology whose hidden purpose is to defeat simple controllers so that learning looks necessary.

Distinguish:

- **degenerate solution** — viability is maintained by bypassing the intended regulatory conflict or exploiting an accounting/interface loophole;
- **legitimate simple solution** — a fixed controller genuinely regulates the competing organism-visible constraints.

If a legitimate simple controller succeeds, preserve that result. It means the added machinery of learning has not yet earned its place for that world.

If a degenerate optimum defeats the intended ecological structure, development may revise the ecology, with the reason recorded before interpreting the next run.

## F. Candidate next evidence milestone — EXP-004

EXP-004 is reserved conceptually as the next major evidence milestone, not as the next implementation step.

The previous roadmap idea of making EXP-004 a station-relocation ecological-robustness probe is retained as historical planning context but is **no longer the active next protocol**.

The current candidate scientific direction is stronger:

> lifetime experience causally changes later homeostatic behaviour in a matched probe.

A possible formal design would compare organisms that begin identically, experience different developmental histories, then enter a common probe with non-plastic state equalized and learning frozen where appropriate.

This claim is **not frozen**. Development must first establish a coherent ecology, competent fixed controls, interpretable plasticity, and a clean transfer/probe method.

No EXP-004 seed range is reserved by this roadmap.

## G. Lifetime and developmental-stage semantics

Within one developmental stage, an organism lifetime is continuous and death is final.

Short harness horizons do not constitute rebirth and must not reset learned, transient-controller, circuit/filter, policy-phase, or organism-RNG state.

A deliberate **developmental-stage reset** is different. Under the current convention it begins a new staged lifetime and resets learned/plastic state. New sensors, internal variables, circuits, structural capabilities, or morphology may be deliberately introduced at such a stage boundary, subject to the project's durable-boundary review rules.

Cross-stage inheritance of learned state is deferred as its own future research question.

No Darwinian population selection, heredity, mutation, or evolutionary optimization is currently used to bootstrap learning.

## H. Later developmental questions

Only after lifetime plasticity is interpretable should the project progressively investigate:

- nonstationary environments;
- partial observability and memory earned by that problem;
- stronger predictive models;
- safe-surplus exploration/curiosity;
- quiescent/consolidation phases if interference or compute/thermal pressure creates a reason for them;
- richer machine-native sensing;
- safe computer-native embodiment;
- physical embodiment;
- social interaction and communication;
- longer-term value formation.

These are directions, not promises that each mechanism will be required.

## I. Evidence standard

Formal claims remain narrow and falsifiable.

A later result should say what was manipulated, what organism-visible information was available, what mechanism was programmed, what changed through experience, what comparator was used, what seeds were reserved, and what analysis was frozen.

A development observation is not promoted into evidence merely because it is interesting.

An impressive trajectory is not evidence of consciousness, emotion, genuine life, or subjective experience.
