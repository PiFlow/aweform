# Developmental Direction — Scaffold Transfer, Dormancy, and Multi-Timescale Learning

**Status:** non-authorizing developmental direction.

This document records a long-range scientific direction for Aweform. It does **not** authorize a new sensor, causal state, learner, controller, dormancy mechanism, planning mechanism, evolutionary mechanism, evidence protocol, reserved seed, or next `D-NNN` implementation. Any durable architecture, information, sensory/plasticity, or safety-boundary change still requires the governance defined in `AGENTS.md` and the relevant ADRs.

## 1. Core direction: engineer learning conditions, not mature behavioural solutions

The historical V0.4 lineage relied on an engineered behavioural scaffold for regulation and navigation. That scaffold was scientifically useful because it established viable control conditions and exposed developmental problems. ADR 0017 deliberately retired the D-026/D-027/D-030 V0.4 scaffold stack from the V0.5 organism. ADR 0018 prospectively re-scopes only the **function** of basic energetic return: a newly implemented constitutive Level-1 return/reacquisition/docking mechanism may belong to the V0.5+ innate viability floor, while the historical V0.4 controller stack, modes, tuned constants, learned weights, and stochastic de-trap mechanisms remain retired and are not ported.

This distinction is a declared project architecture/provenance classification, not proof of an intrinsic computational difference between an old scaffold and an innate mechanism. Scaffold transfer applies above the declared innate viability floor.

The long-range direction is to move engineering progressively downward:

- engineer physiology, embodiment, sensors, actions, bounded memory/plasticity machinery, and explicit safety/information boundaries;
- let experience increasingly determine task-specific behavioural competence;
- when evidence permits, replace task-specific engineered behavioural rules with experience-dependent mechanisms rather than adding another fixed rule on top.

This is **scaffold transfer**, not a requirement to remove all engineered structure. Physiology and substrate remain engineered. The developmental question is which behavioural knowledge can be transferred from fixed rules into learning without losing provenance or viability.

A useful recurring question for future milestones is:

> **What information can this organism construct from experience, and when can that learned information legitimately take over something currently engineered?**

## 2. Historical scaffold examples and ADR 0018 re-scoping

The historical V0.4 system contained explicit behavioural knowledge that remains useful as scaffold-transfer evidence. Historical examples include:

- the fixed energy condition that triggered `SEEK`;
- the rule that full charge permitted departure;
- hand-written beacon steering during reacquisition;
- stochastic false-contact `SEEK` delegation used for de-trapping;
- discrete controller phase structure itself.

Those historical mechanisms remain scaffolds under their original records; ADR 0018 does not relabel or port them. Prospectively, however, a **new** V0.5+ basic return trigger, beacon-guided reacquisition, organism-visible terminal docking/charging, and fixed baseline return-budget sizing may be classified as **constitutive Level-1 mechanisms** rather than temporary scaffolds awaiting displacement.

Elective departure, adaptive reserve strategy above the fixed floor, efficiency/robustness improvements, changed-environment handling, and competence-dependent behaviour remain above-floor developmental targets. A developmental scaffold in those domains should be displaced only after an experience-dependent mechanism has earned the role experimentally.

Replacing a fixed constant with a fitted constant is not automatically a meaningful developmental advance. For example, replacing `energy <= 0.50 -> SEEK` with a learned scalar threshold can still preserve almost the entire engineered decomposition. A stronger result would be experience causing the organism to learn the consequences of continuing versus reacquiring under different internal states, so that an effective transition toward seeking changes with competence and history.

## 3. Physiology, constitutive viability, and behavioural knowledge

Aweform does not need to learn every fact about its own existence, and ADR 0018 adds a second engineered category above substrate physiology: **constitutive Level-1 viability mechanisms**.

Examples of engineered physiology may legitimately include:

- finite stored energy;
- energy costs and resource uptake;
- thermal dynamics;
- physical action/sensing constraints;
- a future critically low-energy shutdown boundary, if separately authorized;
- a future minimal protected reserve supporting only essential continuity functions, if separately authorized.

These are substrate conditions, not mature behavioural knowledge.

Under ADR 0018, not all energy-regulation behaviour remains above the learning floor. Basic return initiation, basic beacon-guided reacquisition, organism-visible terminal docking/charging, and fixed baseline return-budget sizing may be constitutive Level-1 mechanisms. Behavioural knowledge above that floor includes elective departure, adaptive reserve strategy, improved efficiency/robustness, adaptation to changed environments, and how behaviour should change when competence or history changes.

Constitutive Level-1 competence is engineered baseline capability, not learned evidence. Learned Level-2/3 improvements must be measured and attributed above that baseline.

## 4. Future hypothesis: reversible energetic dormancy rather than automatic organismic death

A future physical embodiment may distinguish **loss of active function** from irreversible organismic termination.

One plausible machine-native analogue is a protected ultra-low-power subsystem, conceptually similar to a tiny backup battery or always-on clock/memory domain. At critically low main energy, active sensing, movement, and learning could stop while only explicitly defined continuity functions persist. If energy later returns, the organism could resume with retained state and detect that external time advanced during a period in which it had no active sensory experience.

The scientifically interesting signal would not be a supplied label saying `low energy is bad`. It would be an experienced temporal discontinuity: the organism can know that its active history contains a gap, without knowing what occurred during the gap.

This remains only a hypothesis. A future implementation would need to declare at minimum:

- what reserve powers the continuity subsystem;
- exactly which state survives shutdown;
- whether the timebase is organism-visible and why;
- the threshold and wake semantics;
- what counts as one lifetime versus a new lifetime;
- how deterministic replay treats dormant intervals;
- how recovery avoids becoming hidden rescue.

A critical constraint is that power loss away from a resource must not automatically transport the organism to safety. Passive recovery should occur only when the physical world actually supplies energy. Human intervention may be used for research or hardware maintenance, but it must be recorded as external rescue/failure rather than autonomous regulation.

No current lifetime or death semantics are changed by this document. ADR 0010 remains authoritative until separately amended.

## 5. Candidate future lifecycle terminology

If dormancy and inheritance are later introduced, the project should distinguish these concepts explicitly rather than overloading `lifetime` or `death`:

- **lifetime** — one continuing organism identity with its permitted persistent learned/causal state;
- **active bout** — one uninterrupted interval of active sensing, learning, and action;
- **dormancy / functional blackout** — a reversible gap in active experience caused by insufficient usable energy, if later authorized;
- **generation** — a new organism initialized from an inherited structure under an explicit heredity/evolution experiment.

Under the current accepted architecture, a lifetime remains the continuous causal trajectory defined by ADR 0010 and death is final for that lifetime.

## 6. Learning that a resource is saturated does not by itself create a reason to leave

A future learner may be able to discover from ordinary interoceptive consequences that waiting at a resource initially increases energy and later produces approximately zero additional stored energy. This could allow the organism to learn that the resource has become locally saturated without being given an explicit `FULL -> DEPART` behavioural rule.

However, saturation alone does not create a reason to depart. If staying is safe, costless, and no other opportunity matters, remaining indefinitely may be the coherent outcome.

Therefore a later departure mechanism should not be smuggled back in as a hidden objective. The project must eventually create or discover a second legitimate opportunity/pressure that can compete with continued exploitation of a secure resource.

## 7. Safe-surplus information seeking as a later hypothesis

A promising later candidate is that energetic/safety surplus permits the organism to spend capacity on interactions that improve its predictive or sensorimotor competence.

This should not be implemented automatically as `if full: EXPLORE` or as arbitrary curiosity reward. Possible future mechanisms include learning progress, reducible prediction uncertainty, controllability, or other measurable opportunities to improve a model of action-consequence structure.

A useful qualitative distinction is:

- low viability margin -> prefer behaviour with well-understood viability consequences;
- high viability margin -> tolerate more information-gathering or competence-building interaction.

If this later produced repeated interaction with learnable structures after immediate energetic need was satisfied, it could become evidence relevant to the project's play/exploration hypothesis. It would not by itself establish subjective curiosity or play.

## 8. Three learning timescales must remain distinct

Future Aweform research may eventually contain three different adaptation timescales. They must not be conflated.

### A. Within-lifetime learning / ontogeny

One organism changes retained state from its own causal experience. This is the current V0.3 plasticity direction and should remain the primary route for establishing that experience can reorganize behaviour.

### B. Across-generation inheritance / evolution

Simulation may eventually permit many generations. If introduced, selection should preferentially investigate the evolution of **learning capacity, plasticity, priors, or morphology** rather than simply optimizing a mature fixed task solution.

Directly evolving a controller that encodes `low energy -> seek` may be useful engineering, but it does not answer the same developmental question as an organism learning regulation during its own life.

Heredity, mutation, population selection, and evolutionary optimisation remain explicitly unauthorized under current governance.

### C. Within-decision internal simulation / imagination

A learned predictive model may eventually support internal rollouts of possible action consequences before one real action is executed. This is a planning/world-model hypothesis, not the same thing as lifetime learning or evolution.

Prediction alone does not define which imagined future is preferable. Before model-based action selection is authorized, the project must separately identify what organism-internal criterion legitimately makes one predicted future matter more than another. Evaluator success metrics, distance-to-goal labels, or human task rewards must not be smuggled in through the planner.

No planning or counterfactual action selection is authorized by this document.

## 9. Scaffold dissolution should be measurable

Future developmental reviews should keep a **scaffold ledger** distinguishing at least:

1. engineered physiology/substrate;
2. engineered behavioural scaffold;
3. learned/experience-dependent state;
4. behaviour causally influenced by learned state;
5. engineered mechanisms displaced by learned competence;
6. descriptive emergent interactions that were not directly specified.

A milestone becomes especially strong when learned competence removes the need for a task-specific engineered behaviour without replacing it with another hidden teacher.

This does not imply that lower engineered-scaffold count is always better. A simple fixed controller that genuinely solves the intended problem remains valid evidence. The purpose of the ledger is attribution, not aesthetic minimalism.

## 10. What D-029→D-050 changed about the near-term direction

The earlier version of this document proposed, immediately after D-028, a provisional sequence from causal-history sufficiency toward a smallest retained state, first causal learned influence, scaffold displacement, non-stationarity, and eventually short-horizon prediction. Repository evidence has now executed, stress-tested, and then deliberately reset that line.

The durable lessons are more specific:

1. **First causal learned influence was achieved narrowly in historical V0.4.** D-030 showed that the D-027 learned consequence predictor could causally influence one bounded SEEK steering decision under matched controls. This was genuine experience-dependent behavioural influence, but not general planning or a mature world model.
2. **Scaffold displacement was not achieved.** D-031R1 showed that learned SEEK steering could not replace the engineered stochastic de-trapping scaffold on the tested fresh seeds.
3. **Do not interpret that failure as permission to add capacity.** D-032→D-039 separately tested de-trap function, short action sequences, closure-valid history, turn granularity, interpolation, reverse motion, short-history learnability, predictor-state signals, combined physical/action alternatives, and one-scalar recurrence. Several were locally informative; none established a stable organism-available replacement for the scaffold.
4. **Useful scaffold intervention can be strongly causal without implying a simple learnable trigger.** D-034 identified history-defined states where enabling the existing scaffold had strong matched causal benefit, but this was evaluator-side sufficiency, not a learned stuck detector.
5. **The causal/test machinery itself required auditing.** D-040 independently rebuilt critical replay/branch semantics, reproduced the accepted causal path and positive control, added identity/clone/order controls, and preserved invalidated provenance.
6. **The simplest proposed extra sensor did not solve the problem.** D-041's evaluator-only pair of front-facing candidate beacon receptors returned **NULL/INSUFFICIENT** on both reused support and fresh holdout and never became organism-visible.
7. **The V0.4 docking line was closed rather than endlessly patched.** D-042→D-044 characterized the founder-selected front-contact embodiment and separated strong coarse homing from fragile terminal docking.
8. **V0.5 is a fresh sensorimotor lineage, not a port of the old scaffold.** ADR 0017 retired the V0.4 D-026/D-027/D-030 stack from the V0.5 organism, and D-045 committed the deterministic wheel-command/body/sensor substrate with no behavioural controller or learner.
9. **D-046→D-048 established prediction competence without causal control.** D-046 introduced the fresh shadow-only V0.5 consequence learner after the authorized calibration curriculum; D-047 audited held-out discrimination; D-048 tested extended exposure. Predictions remained causally inert throughout that lineage.
10. **D-049 established the first V0.5 constitutive Level-1 return/docking baseline.** It revalidated the organism-visible beacon inverse, used it as an explicitly programmed engineered prior, and completed return/contact/charging on its frozen ideal deterministic matrix without claiming learning.
11. **D-050 compared two programmed homing laws before return-margin design.** With the same reconstruction and terminal docking semantics, the unchanged stop-turn-straight baseline reached charging in 80/96 fresh paired cases within the frozen horizon while smooth curved pursuit reached 96/96. This remains a descriptive Level-1 controller comparison, not learned competence or physical-hardware robustness.

The resulting near-term principle is:

> **Before transferring behavioural responsibility into learning, establish that the current organism has a legitimate sensorimotor substrate, enough experience to learn its consequences, and demonstrable predictive competence before granting predictions any causal control role.**

This does not supersede the longer-term scaffold-transfer direction. It strengthens attribution discipline: learned competence can displace engineered competence only when the information, action affordances, experience distribution, predictive competence, and causal learning mechanism required for that role have each been earned.

## 11. Anti-shortcuts

Do not interpret this direction as permission to:

- add a larger learner merely because the current learner fails;
- give true heading, wall state, pose, odometry, or evaluator geometry to the organism;
- add hidden rescue when learned control harms viability;
- introduce curiosity/play simply to force departure from a charger;
- evolve task-specific solutions before within-lifetime learning is understood;
- introduce planning before prediction has demonstrated causal usefulness;
- call dormancy, temporal continuity, or persistent state consciousness or selfhood;
- rewrite historical results to fit the new direction.

The long-range aim is not to make Aweform look intelligent sooner. It is to make the provenance of increasingly adaptive behaviour more convincing as task-specific scaffold is progressively transferred to experience-dependent competence.
