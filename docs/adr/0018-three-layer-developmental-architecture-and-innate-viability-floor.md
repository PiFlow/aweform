# ADR 0018 — Three-Layer Developmental Architecture and Innate Viability Floor

## Status

Accepted. Flow merged PR #173 on 2026-09-25 after the ADR-0013 independent exact-HEAD review gate passed at `47a6adb1cc0b6efa7685f2e1ef2f4d77143938da`; merge commit `a375de54722c3bfc09634a3685c4558a7a9f917f`.

This ADR defines a durable developmental architecture. Acceptance does not itself implement a Level-1 controller, add an observation channel, change D-045 physics, change D-046/D-047/D-048 learning mechanisms, execute a new D-stage, or authorize physical hardware.

## Context

Aweform's existing North Star already distinguishes engineered substrate from learned behavioural meaning and progresses from homeostasis and sensorimotor survival toward learning, play, sociality, and richer cognition.

The historical development process has nevertheless treated several elementary viability behaviours—especially energy reacquisition and docking—as behaviours that might eventually be displaced by learning. That was scientifically useful during V0.4/V0.5 diagnosis, but it risks making open-ended learning responsible for prerequisites that a viable artificial organism may reasonably possess innately.

The project now explicitly distinguishes:

1. constitutive innate viability and embodiment;
2. sensorimotor skill integration and automation;
3. open-ended adaptive learning and higher developmental cognition.

This is a functional architecture, not a literal biological or neurological layering claim.

## Decision A — Three functional developmental levels

### Level 1 — Innate Viability & Embodiment

Level 1 contains declared engineered mechanisms with which Aweform is initialized because they are necessary for basic bodily function, baseline viability, or the possibility of later development.

Candidate/authorized categories under this architecture include:

- physical energy and thermal bookkeeping;
- sensor and actuator interfaces, normalization, calibration, and bounded low-level control;
- proprioceptive/body-state access already authorized by the applicable embodiment boundary;
- motor primitives;
- declared critical safety/reflex functions;
- basic energetic self-maintenance;
- low-energy return-to-charge behaviour using authorized organism-visible information;
- terminal docking and charging behaviour constrained to organism-visible feedback;
- later separately authorized viability mechanisms such as fainting/dormancy continuity or self-righting/fall recovery.

Level 1 is not required to be learned or displaced merely to make later cognition appear emergent.

Level 1 must be explicit, inspectable, testable, causally attributed, and bounded. It must not become hidden rescue.

### Level 2 — Sensorimotor Skills & Integration

Level 2 composes Level-1 capabilities into reusable behavioural skills.

Its intended functions include:

- sensorimotor arbitration;
- action sequences and routines;
- reusable skills;
- habits and procedural competence;
- local predictive or adaptive mechanisms where separately authorized;
- automation/consolidation of competencies discovered through Level 3.

Level 2 may contain a mixture of initialized structure and learned/consolidated skill state. Each retained causal object must declare its write provenance, read access, dimensions, update timing, retention/reset semantics, and RNG use as required by ADR 0010.

### Level 3 — Adaptive Learning & Open-Ended Development

Level 3 is the primary arena for progressively open-ended development, including where separately authorized:

- action-consequence learning;
- richer predictive/world models;
- discovery of new affordances and skills;
- curiosity and information-seeking;
- play;
- self/world functional differentiation;
- object/environment structure;
- other-agent interaction;
- social learning and communication;
- later planning or richer cognition.

Level 3 does not receive permission to bypass or rewrite Level-1 viability/safety invariants merely because it is more cognitively sophisticated.

## Decision B — Direction of competence transfer

The preferred long-term developmental flow is:

`Level 3 discovers → Level 2 consolidates/automates → Level 1 underwrites baseline viability`

This does **not** mean Level 3 may rewrite Level 1.

A competency may become a Level-2 procedural skill only through an explicitly defined consolidation interface with declared provenance, validation, retention, and reset semantics.

Promoting, replacing, or changing a constitutive Level-1 mechanism remains a deliberate architecture/design decision subject to the applicable durable-boundary governance rather than silent self-modification.

## Decision C — Memory is typed by provenance and access, not merely by layer name

ADR 0018 recognizes two useful organizational categories:

### Procedural / Skill Memory

Usually associated with Level 2 and potentially containing, when separately authorized:

- learned skill parameters;
- routines;
- action-sequence competence;
- calibrated sensorimotor mappings;
- other compact state needed to execute consolidated skills.

### Experiential / Model Memory

Usually associated with Level 3 and potentially containing, when separately authorized:

- retained experience-derived representations;
- predictive/model state;
- interaction history;
- world/agent regularities;
- other developmentally acquired knowledge.

These names are not themselves permission boundaries.

Every retained Level-2/Level-3 causal memory/plastic object remains under ADR 0010 recursive sensory/plasticity provenance closure and must declare at minimum:

- write provenance;
- permitted readers;
- dimensions/representation;
- update timing;
- persistence/retention;
- reset semantics;
- organism-owned RNG where applicable.

By default, Level-1 viability decisions may **not** read Level-2/Level-3 learned, plastic, consolidated, confidence, prediction-error, model, or memory state. A future specific cross-level pathway requires a separately reviewed durable boundary.

## Decision D — Read-only upward visibility and bounded command interfaces

Level 1 may expose a deliberately bounded read-only organism-facing state upward while retaining private implementation details required for substrate operation.

Examples of potentially upward-visible state are existing authorized interoceptive, exteroceptive, and proprioceptive channels.

Private Level-1 implementation details need not become organism-visible merely because they exist.

Higher levels may invoke declared Level-1/Level-2 capabilities through bounded command interfaces. They do not obtain arbitrary write access to Level-1 physiology, actuator firmware, safety thresholds, or protected viability mechanisms.

ADR 0018 does not by itself add a ninth observation channel or otherwise amend the exact currently accepted V0.5 eight-channel observation vector. Any new upward-visible variable must be separately and explicitly authorized if it changes that durable information boundary.

## Decision E — Level-1 energetic viability preemption is narrow and attributable

ADR 0018 prospectively permits one narrow class of Level-1 preemption for the Innate Autonomous Viability milestone:

> **Energetic return mode may take temporary authority over the bilateral wheel-command locomotor pathway when the declared Level-1 return condition is active, and may retain that authority through beacon-guided reacquisition, terminal docking, and charging until a declared baseline recovery condition is reached.**

At that recovery condition, Level 1 yields locomotor authority upward. It does not itself require an elective departure action.

No broader preemption over future actuators, cognition, memory, exploration, communication, or other action pathways is authorized by this ADR.

Level-1 energetic preemption must:

- depend only on authorized Level-1 state, existing organism-visible channels available to Level 1, and declared fixed structural/engineering constants;
- **not** be causally dependent on Level-2/Level-3 learned, plastic, consolidated, confidence, prediction-error, model, or memory state unless a future separately reviewed boundary explicitly authorizes that pathway;
- be deterministic or explicitly declare any organism-owned RNG;
- be logged on every transition on which it changes, constrains, or replaces a higher-level locomotor command;
- report the fraction/count of transitions under Level-1 preemption in every affected D-record;
- never use hidden evaluator geometry, future outcomes, experiment labels, success labels, or external reward;
- never transport/rescue the body or inject energy;
- remain distinguishable from learned competence in every scientific claim.

**Anti-laundering rule:** a mechanism/state written or modified through learning, consolidation, evaluator information, or another Level-2/Level-3 pathway cannot be relabelled as “Level 1” to evade provenance or attribution rules. Moving such a mechanism into the constitutive Level-1 floor requires an explicit separately reviewed architecture decision.

Outside the declared energetic preemption condition, viability loss and death/termination remain genuine simulated consequences under the applicable lifecycle boundary.

Any scientific claim about learned regulation, navigation, energy management, or docking while Level-1 energetic preemption is active must include an appropriate matched attribution control—such as an evaluator-side innate/preemption-ablated comparator—sufficient to separate learned contribution from the constitutive Level-1 baseline. A claim unrelated to those behaviours need not add an irrelevant ablation.

## Decision F — Exact extent of the initial innate energetic floor

For the initial **Innate Autonomous Viability** milestone, the following are reclassified as constitutive Level-1 mechanisms rather than developmental targets that must be discovered from scratch:

1. **When to initiate basic return:** a fixed/engineered Level-1 return condition derived from current energy and authorized beacon/body information.
2. **How to perform basic reacquisition:** a bounded beacon-guided homing behaviour using only authorized organism-visible channels and declared body/sensor constants.
3. **How to perform terminal docking:** a bounded local search/alignment behaviour using only organism-visible beacon L/F/R, charging contact, wheel-delta proprioception, energy where relevant, and declared body/sensor constants.
4. **How to establish and maintain charging until baseline recovery:** remain in the declared Level-1 charging/recovery state until a fixed baseline recovery condition is met, then yield authority upward.
5. **Baseline return-budget/reserve sizing:** an engineered assumption-bounded return-safety calculation or threshold sufficient for the first Level-1 mechanism; its exact formula remains mechanism-level work.

The following remain **above the innate floor** and are not solved by ADR 0018:

- elective departure from the charger after Level 1 has yielded control;
- how much surplus energy is worth accumulating for future optional behaviour;
- adaptive or experience-dependent reserve strategy beyond the fixed baseline floor;
- improved route choice, efficiency, shortcuts, obstacle handling, changed environments, degraded sensors, or uncertain charger availability;
- learning when/how to explore, play, or pursue non-viability opportunities;
- learned improvements to homing/docking beyond the innate baseline;
- any world-model, planning, curiosity, or social decision.

### Terminal-docking information constraint

The innate docking mechanism must **not** encode evaluator-only dock orientation, exact target heading, heading acceptance window, hidden pose, station coordinates, true distance, or other privileged geometry.

In the current centred-dock V0.5 boundary, terminal alignment must be achieved through permitted organism-visible sensory/contact/proprioceptive consequences and declared body/sensor constants. Rotational symmetry at/near the station centre is therefore a real information constraint, not something Level 1 may bypass with hidden orientation knowledge.

The beacon-guided homing relationship is not required to be rediscovered from scratch by Level 3 before Aweform can remain energetically autonomous. Later learning may improve it, but those improvements must be attributed above the innate baseline.

## Decision G — Energy-efficient implementation is a design requirement

Viability-critical Level-1 functions should be implementable on the smallest practical compute/control substrate consistent with correctness and safety.

When main energy is low, maintaining a large open-ended learner solely to execute an elementary return-to-charge behaviour is undesirable when a bounded lower-level mechanism can perform that constitutive function.

This is an engineering objective, not evidence that biological nervous systems use the same architecture.

## Decision H — Return-safety requirement; exact mathematics remain non-normative

ADR 0018 establishes only the architectural requirement that Level 1 may use a **return-safety / return-margin mechanism** to decide when basic energetic return should take priority.

Normative requirements are:

- inputs must be limited to authorized Level-1 state, existing organism-visible beacon/body signals available to Level 1, and declared fixed structural/engineering constants;
- no evaluator coordinates, hidden pose, true distance, future branch result, success label, or learned Level-2/Level-3 state may enter the Level-1 trigger by default;
- cost/reserve assumptions must be provenance-labelled as derived, measured, manufacturer-sourced, engineering estimates, or founder design choices as appropriate;
- parameters must not be tuned post hoc merely to manufacture desired autonomy;
- uncertainty/validity assumptions must be explicit;
- any implementing D-record must define numerical handling of weak/near-zero/saturated beacon readings, quantization/float effects, out-of-support geometry, invalid/missing beacon conditions, and any fallback/termination semantics;
- “safe return” or “sufficient reserve” claims are valid only under the declared environmental, actuator, sensing, charger-availability, and model-error assumptions.

The exact equation, cost decomposition, safety factor, trigger hysteresis, and recovery threshold are **not frozen by ADR 0018**.

A separate non-authorizing research note should preserve candidate mathematics for later mechanism design:

`docs/return-reserve-margin-future-question.md`

### D-016 provenance/category promotion

D-016 demonstrated an evaluator-only analytic inverse of the historical idealized directional beacon and explicitly did **not** make that reconstruction organism-side.

If a future Level-1 implementation uses the same or related analytic inversion, that is an intentional category promotion:

> **evaluator-only diagnostic → designed constitutive Level-1 prior**

It must be reported as designed prior knowledge, not discovered competence.

Before such an inverse is used causally in V0.5, the implementing stage must revalidate it against the exact current V0.5 beacon channel definitions, numerical precision/quantization, retained point-beacon identity, body/probe geometry, and edge behaviour. D-016's V0.4 result is supporting precedent, not automatic V0.5 organism permission.

The return-safety “reserve” in this section is a **decision-budget margin**, not the protected continuity reserve discussed in the future dormancy/fainting direction. Dormancy/fainting remain unauthorized by ADR 0018.

## Decision I — Constitutive innate mechanism versus developmental scaffold

Update project terminology:

### Constitutive innate mechanism

A declared engineered mechanism intentionally supplied as part of the minimum viable organism/body architecture. It need not be displaced by learning.

### Developmental scaffold

A temporary engineered behavioural aid used to create a developmental condition or support a higher-level skill that the project may later test for transfer into learned competence.

“Lower scaffold count” is not itself a scientific objective.

Scaffold transfer applies **above the declared innate viability floor**.

The distinction is a project design/governance classification, not proof that the two mechanism classes differ intrinsically in computational form. A constitutive innate mechanism may perform a function similar to a historical scaffold; what changes is the project's explicit decision that the function belongs to the organism's inherited baseline rather than being temporary competence awaiting displacement.

## Decision J — Claims and attribution boundary

Every result must distinguish:

- Level-1 engineered viability contribution;
- Level-2 initialized versus learned/consolidated skill contribution;
- Level-3 learned/open-ended contribution;
- evaluator-only diagnostic information.

Innate competence is not evidence of learning.

When a learned mechanism is evaluated on a behaviour already supported by Level 1, the experimental design must measure improvement/contribution **above the innate baseline**, using appropriate matched controls where the scientific claim depends on attribution.

No result may describe baseline return-to-charge competence as learned merely because Level 2/3 was active during the same lifetime.

## Decision K — Governance follows existing AGENTS.md / ADR 0013; no new review tier

ADR 0018 does not create a bespoke governance tier and does not permanently name a reviewer/model.

After ADR 0018 is accepted:

- ordinary Level-1 or Level-2 mechanism work that stays entirely within already accepted architecture/information/safety boundaries follows the ordinary Development lane: appropriate implementation tests/validation, descriptive D-record where applicable, and Flow merge authorization; no formal two-reviewer exact-SHA gate is required merely because the mechanism is Level 1 or Level 2;
- Flow may request additional independent review for any ordinary D-stage when scientific or implementation risk warrants it, but that is not a new durable mandatory tier;
- any new or changed durable architecture, sensory/plasticity, information, safety, or Level-1 preemption boundary follows the full ADR-0013 independent-review requirements;
- evidence-lane EXP claims/executions continue to follow the formal evidence/review requirements;
- Level-3 open-ended learning work should retain proportionate causal controls, held-outs, ablations, attribution controls, and EXP promotion where the claim justifies formal evidence.

## Decision L — Explicit reconciliation / prospective supersession

ADR 0018 does not rewrite historical records. It prospectively changes specific future-facing project boundaries.

| Existing accepted/prospective text | ADR 0018 prospective disposition |
|---|---|
| ADR 0017 §I: V0.4 behavioural control/learning scaffold stack is not ported by default to V0.5, including D-011 reacquisition and historical mode/controller semantics | **Partially superseded for function, not implementation.** V0.5 may now receive a newly implemented constitutive Level-1 energetic return/reacquisition/docking mechanism. No historical V0.4 controller code, modes, state, tuned constants, learned weights, stochastic de-trap machinery, or action semantics are silently ported. The new mechanism must be built against the accepted V0.5 wheel-action/body/sensory boundary. |
| ADR 0017 §I: D-025/D-026/D-027/D-030 and V0.4 CHARGE/DEPART/AWAY/SEEK semantics retired from prospective V0.5 organism | **Retained.** ADR 0018 does not restore those mechanisms. A new Level-1 energetic return state is not authorization to resurrect the historical mode stack. |
| ADR 0010 §H: no controller-side hard viability override whose frequent intervention could make plasticity decorative | **Narrow prospective exception with attribution safeguards.** The declared Level-1 energetic locomotor preemption in Decision E is permitted as constitutive baseline architecture. The functional concern of §H remains active: intervention rate must be reported, learned-regulation/navigation claims require matched attribution controls, and outside the declared condition viability loss remains genuine. |
| developmental-principles.md: stronger learned behavioural target includes when to conserve/seek, how to reacquire, when to leave, how much reserve is prudent | **Re-scoped.** Basic return initiation, basic reacquisition, terminal docking/charging, and fixed baseline return-budget sizing move below the innate viability floor. Elective departure, adaptive reserve strategy beyond the floor, improved efficiency/robustness, and behaviour changing with competence/history remain above-floor developmental targets. |
| developmental-direction-scaffold-transfer.md §§1–3: fixed SEEK trigger and hand-written beacon steering are canonical examples of scaffold that may later become learnable | **Re-scoped prospectively.** Historical V0.4 mechanisms remain valid scaffold examples, but future V0.5+ basic energetic return may be constitutive Level 1 rather than temporary scaffold. Scaffold-transfer logic applies above the declared innate floor. |
| D-016 evaluator-only beacon inverse | **Historical diagnostic remains unchanged.** Any causal Level-1 use is a new designed-prior category promotion requiring current-boundary validation and explicit implementation authorization. |

No historical D-stage, EXP-stage, artifact, or accepted ADR result is relabelled or rewritten by this table.

## Non-goals

ADR 0018 does not itself authorize:

- source/runtime implementation;
- a specific return-to-charge controller equation or implementation;
- a new organism-visible observation;
- camera vision;
- obstacle navigation;
- physical robot actuation;
- self-righting or fall recovery implementation;
- fainting/dormancy implementation;
- a new memory implementation;
- Level-3-to-Level-2 consolidation code;
- self-modification;
- heredity/evolution;
- a teacher model or distillation mechanism;
- curiosity/play implementation;
- planning/MPC/RL;
- D-049 or any successor Development stage.

## Relationship to existing records

- Historical D/EXP results remain unchanged.
- ADR 0010 remains historical authority for V0.3 lifetime plasticity and sensory/plasticity closure. ADR 0018 prospectively creates only the narrow, explicitly bounded constitutive Level-1 energetic preemption described in Decisions E/L; it does not erase ADR 0010's provenance or attribution protections.
- ADR 0017 remains authoritative for the current V0.5 differential-drive body, centred dock, existing beacon, exact eight-channel observation vector, and actuator bookkeeping except for the narrow future-facing scaffold-retirement surface explicitly superseded in Decision L.
- `docs/low-level-autonomy-and-sensor-layering-future-question.md` should be retained as historical provenance but marked as promoted/superseded by ADR 0018 once accepted.
- D-016 remains an evaluator-only historical diagnostic unless and until a separately authorized Level-1 mechanism deliberately promotes part of its mathematics as designed prior knowledge.
- No existing learner result is reinterpreted as Level-1 evidence.

## Review provenance

Because ADR 0018 creates a durable architecture/behavioural-boundary distinction, changes the prospective status of basic energetic return competence, and introduces a narrow Level-1 preemption permission, ADR-0013 formal review was required before acceptance.

PR #173 received independent exact-HEAD PASS reviews from GPT-5.6 Sol and GLM-5.3-Flash (Z.ai model family) at `47a6adb1cc0b6efa7685f2e1ef2f4d77143938da`, after which Flow authorized and completed the merge. Any future substantive change to this durable boundary remains subject to the applicable ADR-0013 review requirements.
