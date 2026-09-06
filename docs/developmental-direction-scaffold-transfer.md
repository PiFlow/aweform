# Developmental Direction — Scaffold Transfer, Dormancy, and Multi-Timescale Learning

**Status:** non-authorizing developmental direction.

This document records a long-range scientific direction for Aweform. It does **not** authorize a new sensor, causal state, learner, controller, dormancy mechanism, planning mechanism, evolutionary mechanism, evidence protocol, reserved seed, or next `D-NNN` implementation. Any durable architecture, information, sensory/plasticity, or safety-boundary change still requires the governance defined in `AGENTS.md` and the relevant ADRs.

## 1. Core direction: engineer learning conditions, not mature behavioural solutions

Aweform currently relies on an engineered behavioural scaffold for regulation and navigation. That scaffold has been scientifically useful because it establishes viable control conditions and exposes new developmental problems. It should not silently become the permanent cognition architecture.

The long-range direction is to move engineering progressively downward:

- engineer physiology, embodiment, sensors, actions, bounded memory/plasticity machinery, and explicit safety/information boundaries;
- let experience increasingly determine task-specific behavioural competence;
- when evidence permits, replace task-specific engineered behavioural rules with experience-dependent mechanisms rather than adding another fixed rule on top.

This is **scaffold transfer**, not a requirement to remove all engineered structure. Physiology and substrate remain engineered. The developmental question is which behavioural knowledge can be transferred from fixed rules into learning without losing provenance or viability.

A useful recurring question for future milestones is:

> **What information can this organism construct from experience, and when can that learned information legitimately take over something currently engineered?**

## 2. Examples of scaffold that may later become learnable

The current system contains explicit behavioural knowledge that may eventually become targets for scaffold transfer. Examples include:

- the fixed energy condition that triggers `SEEK`;
- the rule that full charge permits departure;
- hand-written beacon steering during reacquisition;
- stochastic false-contact `SEEK` delegation used for de-trapping;
- discrete controller phase structure itself.

These are not errors. They are declared developmental scaffolds and valid controls. Future work should not remove them merely because learned behaviour would look more interesting. A scaffold component should be displaced only after a smaller experience-dependent mechanism has earned that role experimentally.

Replacing a fixed constant with a fitted constant is not automatically a meaningful developmental advance. For example, replacing `energy <= 0.50 -> SEEK` with a learned scalar threshold can still preserve almost the entire engineered decomposition. A stronger result would be experience causing the organism to learn the consequences of continuing versus reacquiring under different internal states, so that an effective transition toward seeking changes with competence and history.

## 3. Physiology versus behavioural knowledge

Aweform does not need to learn every fact about its own existence.

Examples of engineered physiology may legitimately include:

- finite stored energy;
- energy costs and resource uptake;
- thermal dynamics;
- physical action/sensing constraints;
- a future critically low-energy shutdown boundary, if separately authorized;
- a future minimal protected reserve supporting only essential continuity functions, if separately authorized.

These are substrate conditions, not mature behavioural knowledge.

Behavioural knowledge concerns what the organism learns to do because of those conditions: when to conserve, when to seek, how to reacquire energy, when to leave a resource, how much reserve is prudent, and how behaviour should change when its competence or environment changes.

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

## 10. Near-term directional implications after D-028

D-028 diagnosed a residual-prediction problem but did not authorize a new causal state or sensor. The next learning-oriented work should continue the same attribution discipline.

A plausible non-authorizing sequence is:

1. **causal-history sufficiency:** evaluator-only test whether short observation/action history or other closure-valid causal history explains part of the D-028 residual without privileged world-frame heading;
2. **smallest justified retained state:** only if history proves informative, test the minimum organism-owned recurrent/internal state needed to retain it;
3. **first causal learned influence:** allow one learned prediction to modulate one existing decision under matched no-influence and shuffled controls;
4. **scaffold displacement:** test whether learned competence can replace or outperform one engineered compensation such as stochastic docking de-trapping;
5. **controlled non-stationarity:** introduce one world change that creates a genuine reason for plasticity and test history-conditioned adaptation;
6. **short-horizon internal prediction:** only after one-step prediction has demonstrated behavioural usefulness, test whether composed near-future prediction adds capability.

This ordering is provisional. Repository evidence at the exact future HEAD outranks this roadmap suggestion.

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
