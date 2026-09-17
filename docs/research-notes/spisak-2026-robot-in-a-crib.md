# Research note — Spisak et al. (2026), “Robot in a crib”

- **status:** research input only; non-authorizing
- **date recorded:** 2026-09-03
- **repository base:** `a7c66a8bc096baf61b50bc3963b6cf19a6d38f83`
- **paper:** Spisak et al., “Robot in a crib: How a playing robot helps us understand sensorimotor contingency learning,” *Science Robotics* (2026)
- **DOI / original paper:** https://doi.org/10.1126/scirobotics.aed4106

## Scope

This note records potentially useful scientific ideas for future Aweform development. It does **not** change Aweform’s architecture, roadmap, sensory/plasticity boundary, safety boundary, current D-lane sequence, or permission set. In particular, it does not authorize curiosity, play, reinforcement learning, model-guided control, camera vision, a larger world model, or any other mechanism currently outside the accepted boundary.

The paper studies an embodied iCub robot learning sensorimotor contingencies through prediction and curiosity-related exploration. The important distinction for Aweform is that the **form of exploratory behaviour can emerge from experience**, while the mechanisms that create prediction pressure, curiosity/interest, motor variation, and the available sensorimotor substrate are architecturally supplied.

## Scientific conclusion for Aweform

**Scientific relevance: HIGH**  
**Experimental-method relevance: VERY HIGH**  
**Immediate architectural relevance: LOW**  
**Evidence for adding curiosity now: NONE**

The paper is useful to Aweform in three main ways:

1. **Predictive sensorimotor development.** It provides strong precedent that learning action-conditioned sensory consequences is a meaningful developmental primitive. This is conceptually close to Aweform’s D-008/D-013 lineage, where a small organism-owned learner predicts visible one-step consequences from the current observation and the organism’s own executed action.
2. **Embodied emergence.** It shows that the same learning machinery interacting with a body and environment can produce multiple exploratory strategies rather than one simple increase in action frequency. The emergent object is therefore the structured strategy or trajectory, not the existence of the curiosity mechanism itself.
3. **Experimental design.** It warns against equating developmental competence with a single behavioural scalar. More movement, more charging, lower prediction error, or greater coverage should not automatically be interpreted as “better development.” Qualitatively distinct strategies can produce the same or different aggregate scores.

The most useful general lesson is:

> A small number of engineered learning pressures interacting with embodiment can produce behavioural strategies that were not individually programmed. Aweform should therefore continue to separate what is programmed, what is learned, and what genuinely emerges from their interaction.

For Aweform’s particular research question, the stricter developmental approach remains appropriate: do not assume that an explicit curiosity objective is necessary merely because it is useful in another developmental-robotics architecture. Where possible, first test whether useful exploratory organisation can arise from viability, predictive learning, embodiment, and already-authorized mechanisms.

## What is supplied, learned, and emergent

### Architecturally supplied in the Spisak research lineage

The following are not spontaneous emergent capabilities in the strong sense:

- the robot body and morphology;
- available motor commands and sensory channels;
- a prediction-learning mechanism and prediction-error objective;
- a curiosity / interest mechanism that treats prediction failure or novelty as behaviourally significant;
- the representation used to retain action-interest or novelty state;
- motor variability/noise used to expose the system to different sensorimotor outcomes;
- the rule by which curiosity/interest affects subsequent action generation.

Therefore, it would be scientifically misleading to summarize the result as “curiosity emerged.” The mechanism creating curiosity-like exploratory pressure was supplied.

### Learned from experience

What is genuinely learned includes the experienced mapping between action and sensory consequence. The robot is not simply told which limb or movement produces the relevant environmental consequence; this relation is acquired through embodied interaction. Predictor parameters and experience-dependent action-interest states change as a consequence of that history.

### Genuinely emergent behavioural organisation

The most interesting emergent result is that the robot does not converge on one trivial strategy such as “move the connected limb more.” Multiple exploratory strategies can appear. A robot may change amount of movement, spatial pattern, or effectiveness of movement in ways shaped by body mechanics and environmental dynamics.

For Aweform, this supports treating **strategy form, trajectory structure, mode transitions, action/context usage, and organism-environment coupling** as potentially important evaluator-side observations rather than collapsing all development into one scalar score.

## How sensorimotor contingencies should be interpreted

The relevant representation is best understood as an experience-shaped predictive mapping from sensorimotor state and action toward expected sensory consequence, plus an experience-shaped exploratory/interest state. This is weaker and more precise than claiming that the robot acquires an explicit symbolic causal model such as “my left arm causes the mobile to move.”

Aweform should preserve the same conservative distinction in its own language:

- useful action-conditioned prediction is not automatically causal understanding;
- an external evaluator’s classification of strategies is not necessarily an organism-internal representation;
- successful prediction on visited state/action support is not automatically counterfactual competence outside that support;
- behavioural organisation is not evidence of consciousness, subjective agency, or biological life.

## Relevance to Aweform’s existing developmental lineage

Aweform has already developed a much smaller primitive in the same broad scientific family.

D-008 introduced an action-conditioned one-step consequence predictor receiving organism-visible state plus the organism’s executed action while leaving behaviour under the existing controller. D-013 expanded this to the full legitimate current observation and predicted visible energy, thermal, and charging-contact consequences. These are small, transparent mechanisms rather than general world models.

The Spisak paper therefore does **not** imply that Aweform needs a deep neural world model. It strengthens the scientific legitimacy of asking whether action-conditioned prediction can become developmentally useful while keeping the mechanism as small and causally interpretable as possible.

## Important caution from Aweform D-018

Aweform’s D-018 evaluator-only alternative-action audit is particularly relevant before considering curiosity based on prediction error.

D-018 found that the current small consequence learner performed usefully on some physically executed energy/thermal consequences but did not demonstrate useful pooled prediction for unexecuted action alternatives. Almost all exact alternative state/action pairs lacked prior support, and pooled learned error for unexecuted alternatives was worse than the zero-change comparator.

This creates a direct technical warning against importing a rule of the form:

```text
large prediction error
    -> interesting / curious
    -> execute that action more often
```

At Aweform’s current stage, large prediction error could simply mean **unsupported extrapolation or insufficient experience**, not a genuinely informative environmental novelty. Converting that error directly into motivation would risk engineering attraction to model incompetence.

A future curiosity-like mechanism, if ever considered, should therefore not be justified merely by the existence of prediction error. It would first require a separately authorized developmental question about what signal is legitimate, whether its support is sufficient, how it interacts with viability, and how to distinguish learnable novelty from representational failure.

## Potentially useful future implementation ideas

These are **research prompts for later consideration, not implementation instructions**.

### 1. Analyse emergent strategy diversity before adding new cognition

When future Aweform lifetimes begin to show heterogeneous behaviour, evaluate whether distinct strategies already arise from the same minimal mechanism. Candidate evaluator-side analyses could include:

- action/context transition structure;
- dwell-time and mode-transition patterns;
- trajectory geometry;
- resource-contact approach and departure structure;
- repeated action motifs;
- energy/thermal regulation cycle shapes;
- whether different lifetimes solve the same viability problem through different behavioural organisations.

The purpose would be description and hypothesis generation, not feeding evaluator-derived strategy labels back into the organism.

### 2. Prefer embodiment-generated behavioural richness over premature cognitive modules

The iCub study illustrates that environmental and mechanical consequences can create behavioural complexity without requiring a new symbolic cognitive layer. For Aweform, when richer behaviour is scientifically needed, first ask whether a modest change in physically consequential embodiment/ecology can expose an already-authorized learner to richer relationships before adding a planner, intrinsic-reward system, or larger model.

This principle should not be abused to make the ecology harder simply because a simple controller succeeds. Any environmental change must answer a specific developmental question.

### 3. Preserve the action -> consequence learning primitive

The basic relation

```text
(current organism-visible state, own action)
    -> predicted next visible consequence
```

remains a strong candidate developmental primitive. Future stages may test whether such predictions can become causally useful for behaviour only after support, observability, aliasing, and counterfactual validity are demonstrated sufficiently for the intended use.

### 4. Separate novelty from ignorance

If Aweform ever studies intrinsic exploration, useful candidate research questions include:

- Does prediction error fall with repeated exposure in the same supported context?
- Can the organism distinguish persistent unpredictability from learnable novelty using only permitted history?
- Does learning progress provide a cleaner signal than raw error?
- Can exploratory pressure be modulated by viability without hard-coding a complete behavioural solution?
- Does exploratory behaviour add anything beyond stochastic persistent exploration and ordinary viability regulation?

These questions should be tested one at a time and would require explicit authorization if they change the durable plasticity/behaviour boundary.

### 5. Keep strategy classification evaluator-side

Clustering or classifying different exploratory styles may become scientifically useful. Such classification should remain evaluator-only unless a future explicit scientific question requires an organism-visible internal abstraction and the relevant boundary is independently reviewed.

## What should explicitly NOT be imported from this paper

Do not import the following merely because the paper reports interesting behaviour:

- prediction-error curiosity as an automatic intrinsic drive;
- a play objective;
- an activity-interest map or novelty table;
- a fixed novelty/surprise threshold;
- intrinsic reward for prediction error;
- model-guided action selection before supported counterfactual competence is established;
- a large neural controller or deep world model;
- camera vision;
- hundreds of artificial motor outputs intended to mimic infant motor redundancy;
- tuned motor noise as an unexplained developmental ingredient;
- externally discovered strategy labels as organism inputs;
- claims that curiosity, causal understanding, agency, consciousness, or life emerged merely from the observed exploratory behaviour.

## Durable interpretation for future reviewers

When this paper is cited in future Aweform design discussion, its strongest legitimate use is:

> Evidence that action-conditioned prediction and embodied interaction can support the emergence of multiple behavioural strategies, and that developmental evaluation should distinguish engineered learning pressures from learned contingencies and emergent behavioural organisation.

It should **not** be cited as evidence that Aweform should add curiosity, play, intrinsic reward, deep neural architecture, or model-based planning.

Any future proposal using this paper to justify a new organism-facing curiosity/play signal, changed plasticity rule, model-guided control, new observation channel, or larger world-model architecture must still pass Aweform’s normal developmental and durable-boundary process independently of this research note.

## Primary reference

Spisak et al. (2026), “Robot in a crib: How a playing robot helps us understand sensorimotor contingency learning,” *Science Robotics*. DOI: **10.1126/scirobotics.aed4106**.

Original paper: https://doi.org/10.1126/scirobotics.aed4106
