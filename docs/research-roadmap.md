# Aweform Research Roadmap

## A. Purpose

Aweform is being developed from minimal self-maintenance toward adaptive, machine-native cognition and eventual physical embodiment. The project’s long-term orientation and humility boundaries are defined in the [`North Star`](north-star.md); this document adds chronological context and decision memory without replacing the North Star, developmental principles, ADRs, committed development records, or frozen experiment protocols.

Aweform uses two research lanes described in [`development-evidence-workflow.md`](development-evidence-workflow.md): fast descriptive `D-NNN` development and formal `EXP-NNN` evidence.

This roadmap summarizes developmental **arcs**. The canonical per-record D-series ledger is [`development/INDEX.md`](../development/INDEX.md). Current authorized work that has not yet become a committed D-record is tracked by its GitHub issue/PR rather than predicted here.

## B. Completed / evidence ledger

### EXP-000 — Interoception and viability

EXP-000 is completed with confirmatory support. Its narrow result concerns the programmed homeostatic mechanism and that specific ablation in that specific capped simulator; it makes no claim about consciousness, biological life, intelligence, or general artificial life. See the canonical [`EXP-000 final result record`](../experiments/EXP-000-final-result-record.md).

### EXP-001 — Interoception versus open-loop homeostasis

EXP-001 is **CLOSED**. Its formal confirmatory result is `C_GREATER`: calibrated energy-blind C had greater mean capped lifespan than interoceptive B in the frozen 1000-transition EXP-001 simulator. This is a narrow result for the specified programmed controllers and environment, not evidence that interoception is generally harmful or that fixed schedules are generally superior. See the canonical [`EXP-001 closeout`](../experiments/EXP-001-closeout.md).

### EXP-002 — Interoceptive SEEK-entry threshold

Formal calibration completed and selected B50 under the recorded rule. Confirmatory execution remains deliberately unexecuted on untouched seeds `50001–51000`. See the canonical [`EXP-002 protocol`](../experiments/EXP-002-interoceptive-seek-threshold.md), [`calibration evidence`](../experiments/EXP-002-calibration-result.md), and [`confirmatory statistical addendum`](../experiments/EXP-002-confirmatory-statistical-addendum.md).

## C. Historical development foundation

### EXP-003 — Localized charging station + bounded observation history

EXP-003 is historical development/instrumentation rather than confirmatory evidence. It separates sensing from energy acquisition, requires physical station occupancy to recharge, and established the station/beacon interface used by later development. Its historical records retain the EXP-003 identifier; they are not retrospectively renamed into the D-series.

The localized-charging interface remains governed by [`ADR 0008`](adr/0008-exp-003-localized-charging-interface.md). [`ADR 0009`](adr/0009-v0.2-bounded-observation-history-state.md) subsequently opened V0.2 bounded one-step observation-history state and remains the valid authorization for the V0.2 work performed under it.

## D. Developmental process reset

The previous roadmap treated most developmental changes as if they were approaching formal evidence. That preserved rigor but created too much ceremony for exploratory iteration.

The project now separates:

- **D-series:** rapid descriptive development on legal development seeds;
- **EXP-series:** important claims worth freezing and testing on untouched reserved seeds with exact-SHA review.

Development results may motivate evidence experiments but cannot count as confirmatory evidence for their claims.

## E. Executed D-series development arcs

The earlier predicted D-001→D-008 sequence has been superseded by actual development. The summary below is retrospective and deliberately coarser than the canonical ledger.

### D-001→D-004 — remove ecological degeneracy and establish continuous lifetime

This arc began by testing the inherited localized-charging ecology rather than assuming it created a meaningful regulatory problem. D-001 exposed the post-contact ecological degeneracy. D-002 introduced the minimal thermal ecology. D-003 established a fixed non-learning thermostatic shuttle as a legitimate simple control. D-004 consolidated continuous-lifetime execution so harness segmentation would remain invisible to the organism.

This established a durable rule: a competent simple controller solving the intended conflict is a result, not a reason to redesign the world merely to force learning.

### D-005→D-010 — first within-lifetime adaptation and predictive-support diagnostics

D-005 and D-006 tested small experience-dependent thermal consequence mechanisms. D-007 used matched common probes to ask whether different lifetime histories could leave load-bearing retained state. D-008 introduced a tiny action-conditioned one-step consequence model. D-009 deliberately acquired overlapping action experience before asking unsupported counterfactual questions. D-010 then audited visited-support consequence aliasing.

This arc established the project's current discipline that prediction quality cannot be interpreted without state/action support, and that poor prediction may reflect partial observability, omitted state, data coverage, or causal aliasing rather than insufficient model size.

### D-011→D-018 — autonomous thermal-beacon reacquisition and consequence diagnostics

D-011 established a fixed non-learning thermal-beacon reacquisition controller; D-012 broadened its seed robustness. D-013 attached a full-observation shadow viability-consequence learner with zero behavioral influence. D-014 corrected the full-charge-or-thermal departure scaffold. D-015 audited consequence support under that corrected scaffold. D-016 tested current-beacon contact observability, D-017 decomposed rear-docking pose information in shadow, and D-018 compared action alternatives through evaluator-only causal branches.

The result was not a mature world model. It was a progressively better map of what the current closure could predict and where docking/contact consequences remained ambiguous.

### D-019→D-026 — V0.4 physicalization, finite-body docking, and de-trapping

D-019 audited the smallest physically grounded V0.4 embodiment/thermal budget before causal adoption. D-020 introduced physical bookkeeping and a fixed-action probe. D-021 established an autonomous energy-regulation baseline; D-022 measured incidental charging contribution; D-023 tested repeated-cycle endurance.

D-024 then introduced the causal finite body with a dual-contact docking boundary. D-025 added bounded stochastic SEEK de-trapping, and D-026 stabilized it as one-third false-contact SEEK delegation. These stages produced the physical/controller scaffold on which the subsequent learning questions depend.

Accepted durable physical boundaries are recorded in [`ADR 0012`](adr/0012-v0.4-minimal-physical-energy-thermal-boundary.md), [`ADR 0014`](adr/0014-v0.4-thermal-operating-and-failure-thresholds.md), and [`ADR 0015`](adr/0015-v0.4-finite-body-dual-contact-docking-boundary.md).

### D-027→D-031R1 — learned sensorimotor prediction becomes causal, then fails scaffold displacement

D-027 introduced a 168-weight action-conditioned linear predictor over the six organism-visible channels. It learned only from physically executed actions and remained behaviorally shadow-only at first.

D-028 audited residual attribution. D-029 asked read-only alternative-action questions and measured support/readiness. D-030 then allowed one narrow learned prediction — predicted next forward-beacon consequence — to influence one narrow false-contact SEEK steering decision under matched controls. This was the first bounded causal use of learned consequence prediction.

D-031R1 tested whether that learned SEEK steering could displace the engineered stochastic de-trapping scaffold. It could not: the learned-with-de-trapping arm retained full-cycle competence, while the no-de-trapping arms failed SEEK across the fresh support. This negative result became the central diagnostic problem for the next arc.

### D-032→D-040 — diagnose why learned steering cannot replace the scaffold

Rather than immediately adding a larger learner, the project decomposed the failure.

D-032 attributed what the de-trap scaffold actually does. D-033 tested short forced action sequences. D-034 demonstrated that closure-valid history-defined anchors could identify states where enabling the existing de-trap scaffold had strong causal benefit, without establishing a learned trigger. D-035A/B/C separately audited turn granularity, L/F/R interpolation, and reverse-translation sufficiency. D-036 tested short-history recruitment learnability; D-037 tested endogenous D-027/D-030 predictor-state signals; D-038 combined several physical/action-space evaluator interventions; D-039 tested one-scalar shadow recurrence.

The important pattern was repeated: several proposed explanations were informative locally but did not establish a stable organism-available trigger or a sufficient replacement for the scaffold. D-039 improved one-step shadow prediction in a bounded sense but did not produce recruitment-coherent held-out benefit.

D-040 therefore stopped proposing mechanisms and audited the causal/test machinery itself. It independently reconstructed the recent Arm-B path and D-034 effect, added exact identity/clone/order controls, preserved invalidated provenance, and mapped scaffold benefit under reused and fresh development support. The accepted review concluded that the causal machinery was valid enough for the audit, that **partial observability remains plausible**, and that **privileged geometry is strongly informative** in the tested regime. Those findings are diagnostic only: D-040 does not authorize privileged organism inputs, a new memory mechanism, a stuck detector, recurrence, or any successor architecture.

## F. D-041→D-044 closeout and accepted V0.5 reset

D-041 completed the evaluator-only front-beacon sensory-sufficiency audit. Its minimal two-receptor pair returned **NULL/INSUFFICIENT** on both reused support and fresh holdout: the candidate signals were diagnostically evaluated but never exposed to Aweform and never became part of the organism's sensory boundary.

D-042 then opened and implemented the founder-selected V0.4 fine-turn/front-contact boundary: 5° turns, the existing 0.1 s action interval and power semantics, front dual charging contacts, and otherwise preserved V0.4 organism/controller/learner boundaries. D-043 characterized that accepted embodiment on fresh Development seeds. It showed that front docking and recharge were physically possible but not robust across repeated cycles.

D-044 kept the organism unchanged and separated **coarse station homing** from **terminal dual-contact docking**. It found descriptively that station-centred L/F/R signals already contain accurate station-relative information on visited support, that the body can approach the station closely while terminal pose remains fragile, and that shorter forward-step and de-trap alternatives produce mixed/local evidence rather than a robust solution.

That sequence motivated a developmental reset rather than another patch to the V0.4 controller scaffold. Accepted [`ADR 0017`](adr/0017-v0.5-direct-differential-drive-centered-dock-boundary.md) now defines the prospective V0.5 first slice:

- one continuous compound `wheel_motors_lr(desired_delta_left, desired_delta_right)` action using signed per-interval wheel-rotation increments;
- deterministic minimal differential-drive kinematics;
- founder-selected first-slice wheel/body geometry;
- a centred under-body dual-contact dock;
- exactly two quantized signed wheel-delta proprioceptive channels;
- continuous wheel-command/response-dependent energy and heat bookkeeping;
- retirement of the V0.4 D-026/D-027/D-030 behavioural/learning scaffold stack from the prospective V0.5 organism.

ADR 0017 is a durable boundary, **not D-045 implementation authorization**. D-045 is the prospective evaluator-scripted deterministic embodiment/bookkeeping probe described by the ADR, but whether it is currently authorized must be read from the exact current GitHub authorization issue/PR.

A separate future note, [`low-level-autonomy-and-sensor-layering-future-question.md`](low-level-autonomy-and-sensor-layering-future-question.md), preserves the broader question of economical low-level bodily competence beneath richer future perception; it remains non-authorizing.

## G. Candidate EXP-004 evidence milestone

`EXP-004` remains a conceptual placeholder for a future major evidence milestone, not an implementation task and not a reserved seed range.

The older provisional proposal described EXP-004 as an ecological-robustness/station-relocation experiment. That remains project history, not the active protocol.

A stronger later evidence direction may ask whether lifetime experience causally alters later homeostatic behavior under a frozen matched probe. That claim is **not frozen**. Current D-development must first establish a mechanism and a scientifically useful question worth the cost of formal evidence.

## H. Durable scientific rules for development

### Do not design worlds to require the capability you want to celebrate

A simple controller that genuinely regulates the intended competing constraints is a legitimate result. Distinguish it from a degenerate solution that bypasses the intended regulatory problem through an accounting loophole, indefinite docking/stillness, meaningless boundary oscillation, or similar shortcut.

### Learning is not the default explanation for prediction failure

When prediction or learned control fails, distinguish partial observability, omitted permitted state, stochasticity, causal mis-specification, support/data coverage, collapsed experience distribution, intervention timing, and learner capacity before increasing model size.

### Evaluator sufficiency is not organism permission

Privileged geometry, counterfactual branches, shadow sensors, and post-hoc labels may diagnose what information could solve a problem. They do not become organism inputs without a separately authorized information/sensory boundary change.

### Continuous lifetime is causal, not merely a logging convention

Within a developmental stage, harness horizons do not reset the organism. A deliberate stage reset is an explicit lifecycle/new-lifetime event under ADR 0010.

### Validate high-leverage causal machinery independently when necessary

If a chain of developmental analyses shares high-level helpers, a later audit may need an independently implemented replay/branch path to rule out correlated common-mode error. D-040 is the current example of this discipline.

## I. Later directions

Later developmental directions include nonstationarity, partial observability that genuinely earns memory, stronger prediction and bounded planning, safe-surplus exploration, quiescent consolidation when its function is justified, sandboxed computer-native embodiment, and eventual physical embodiment.

The non-authorizing [`World-Model Research Direction`](world-model-developmental-direction.md) preserves current JEPA/world-model research, a strict Aweform world-model definition, qualification levels, and developmental gates for future reference. It does not pre-authorize a world-model architecture, planner, learned representation, D-stage, ADR, or dependency.

The non-authorizing [`Embodied Dynamics Before Explicit Memory`](embodied-dynamics-future-question.md) note preserves the question of whether useful temporal information can already exist in ongoing body/environment dynamics before explicit memory machinery is added.

The non-authorizing [`Wheel-Legged Physical Embodiment Direction`](wheel-legged-physical-embodiment-future-direction.md) preserves the long-range articulated wheel-leg morphology and physical-engineering context that remains outside ADR 0017's deliberately minimal V0.5 first slice. ADR 0017 remains authoritative for prospective V0.5 wheel-command, differential-drive, centred-dock, wheel-delta proprioceptive, and actuator-bookkeeping semantics.

Darwinian evolution, heredity, and cross-stage inherited learned state remain separate later research questions rather than shortcuts for finding the first learner.

## J. Decision-log convention

- Lightweight development records live in `development/`.
- The committed D-series ledger lives in [`development/INDEX.md`](../development/INDEX.md).
- Experiment-specific frozen evidence decisions live in `experiments/`.
- Durable architecture and information-boundary decisions live in `docs/adr/`.
- Dated research notes preserve non-authorizing research questions and should not be silently rewritten as if they were current protocols.
- This roadmap summarizes chronological arcs and the current scientific frontier; it does not duplicate every D-record.
- Result artifacts and exact committed records remain authoritative over roadmap prose.
