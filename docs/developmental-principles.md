# Developmental Principles

## Biology as inspiration, not a script

Aweform studies problems that living systems have faced — maintaining viability, coordinating subsystems, sensing, acting, learning, playing, communicating, and living with others — and looks for electronic mechanisms that address analogous problems.

The project should not treat biological evolution as a linear ladder, and it should not assume that electronic cognition must reproduce human or vertebrate brain organisation.

The developmental sequence is a research scaffold, not a claim that biological evolution followed the same sequence and not evidence that Darwinian evolution is already occurring in Aweform. Reproduction, heredity, mutation, selection, and evolutionary optimisation are separate mechanisms that require explicit later experiments if they are introduced.

## Homeostasis first

Before intelligence, Aweform needs conditions that make continued existence non-trivial.

An internal variable such as energy should matter because actions and environmental conditions change it, and because leaving viable bounds has consequences for the simulated organism.

In V0.1 this energy state was deliberately an engineered accounting variable. It was not biological metabolism and should not be described as such. Its scientific value came from being causally coupled to sensing, action, resource uptake, and episode viability rather than serving as a decorative score.

Later V0.4 development grounds energy and thermal state more explicitly in bounded simulated physical bookkeeping. That improves the physical interpretation of the experiment but still does not make Aweform's simulated energy system biological metabolism.

The first developmental question is therefore not "Can it solve a task?" but "Does informative access to its internal condition alter behaviour in ways that improve viability?"

## Development through consequences

Later cognition should be grounded in repeated interaction between:

internal state → perception → action → consequence → memory/model update

Capabilities should be added only when an experiment creates a genuine need for them.

Designed mechanisms, learned mechanisms, and behaviours that emerge from their interaction must be reported separately. A trajectory can be unexpected even when the underlying drives or safety gates were designed.

## Discovering capabilities through sensorimotor contingencies

Aweform should distinguish between receiving a physical capability and receiving the behavioural meaning of that capability.

A new sensor, actuator, or internally observable variable may require engineered hardware, firmware, normalization, timing, bounds, or safety handling before it is usable. Those implementation requirements do not imply that the organism must also be told what the signal represents or how it should behave because of it.

Where the scientific question permits, prefer the smallest organism-visible interface that leaves meaningful interpretation available to experience.

For example, an evaluator may know that a particular channel originates from an ultrasonic echo sensor while Aweform receives only the bounded observable signal made available by that sensor. Aweform could then encounter contingencies such as:

action → sensor change

repeated action → repeatable sensor consequence

change of orientation → change of sensory relationship

movement → changing predictability or controllability

sensory pattern → later contact, energetic consequence, or action constraint

The developmental target is not necessarily for Aweform to recover human concepts such as "wall", "centimetres", "echo", or "obstacle".

A useful learned relation may instead be entirely machine-native, such as discovering that a particular sensory trajectory predicts that continued forward action will soon produce contact or become ineffective.

The same principle can apply to new outputs. If a future Aweform gains a speaker and microphone, the hardware interface may be engineered while the relationships between generated signals and subsequent auditory observations remain available for sensorimotor discovery.

This creates a general developmental question:

> **Can Aweform learn what a new capability affords before the project supplies task-specific semantic interpretation of that capability?**

Any future experiment must remain explicit about what was engineered into the interface, what information was organism-visible, what behavioural interpretation was supplied, and what relationship was actually learned.

## Scaffold transfer rather than scaffold accumulation

Engineered behavioural scaffolds are legitimate developmental instruments and controls, but they should not silently become Aweform's permanent cognition architecture.

As evidence permits, development should preferentially ask whether task-specific engineered competence can be transferred to experience-dependent mechanisms rather than adding another fixed rule on top. The recurring question is:

> **What information can this organism construct from experience, and when can that learned information legitimately take over something currently engineered?**

This does not mean that every engineered mechanism should be learned. Aweform may legitimately have engineered physiology, embodiment, sensors, actions, viability limits, and bounded plasticity machinery. The stronger developmental target is behavioural knowledge: when to conserve or seek, how to reacquire resources, when to leave, how much reserve is prudent, and how behaviour should change with competence and history.

A fixed controller that genuinely solves the intended problem remains valid evidence and should not be designed away merely to make learning necessary. Scaffold transfer is justified only when a learned mechanism earns the role under fair controls.

The detailed non-authorizing direction, including scaffold accounting, future dormancy, evolutionary timescales, and internal simulation, is recorded in [`developmental-direction-scaffold-transfer.md`](developmental-direction-scaffold-transfer.md).

## Distinguish physiology, lifetime learning, evolution, and planning

These mechanisms answer different scientific questions and must not be conflated.

- **Engineered physiology/substrate** defines the conditions under which an organism can function.
- **Within-lifetime learning** changes an organism through its own causal experience.
- **Across-generation inheritance/evolution**, if ever introduced, changes what later organisms inherit and remains a separate future research question.
- **Within-decision internal simulation/planning**, if ever introduced, uses learned predictions to compare possible futures and also requires a separately justified organism-internal selection criterion.

No later mechanism is authorized merely because it appears in this distinction.

## Play

Play is a later developmental hypothesis, not part of the initial homeostasis stages.

A useful functional interpretation is that when immediate energetic and safety pressures are sufficiently low, Aweform may spend some available capacity on self-generated interventions whose immediate purpose is not resource acquisition or avoidance, but learning about itself and its environment.

Possible play-like behaviour may include:

- repeating an action to test whether an effect is reliable;
- varying an action and observing how the consequence changes;
- trying unfamiliar combinations of actions and sensory conditions;
- producing an output and observing its sensory consequences;
- revisiting something whose behaviour is not yet well predicted;
- manipulating or approaching environmental structure without an immediate viability payoff.

The important property is not randomness.

At evaluator level, evidence distinguishing play-like exploration from random exploration may include improvement in measurable prediction, discrimination, competence, or control. Those evaluation measures must not automatically become organism-visible objectives, rewards, or selection signals.

Play-like exploration must be evaluated against its viability consequences. Whether and how internal viability state gates exploration is itself a mechanism that must be separately justified and attributed rather than assumed here.

No arbitrary "play reward" is authorized by this principle.

## Curiosity

Curiosity is a later hypothesis about the selection of experiences.

Once Aweform has more possible interactions than it can explore indiscriminately, a developmental problem appears:

> **Which action or situation is worth investigating next?**

Novelty, prediction error, uncertainty, controllability, learning progress, model disagreement, and other signals are possible future mechanisms. None is assumed to be the correct implementation in advance.

In particular, simple novelty or raw prediction error should not automatically be treated as curiosity. An unpredictable but unlearnable signal can remain permanently novel or surprising without producing useful understanding.

One future hypothesis is that curiosity-like experience selection may favour experiences for which predictive or controllable competence is improving. Learning progress, novelty, uncertainty, prediction error, controllability, model disagreement, and combinations of these remain competing hypotheses; this document does not privilege one mechanism.

One illustrative, non-authorizing candidate family would be:

current experience
→ prediction or expectation
→ action
→ observed consequence
→ model or competence update
→ estimate of what became better understood
→ selection of another potentially learnable experience

This is only one possible mechanism family and remains a research direction rather than a selected architecture.

Future experiments should compare candidate mechanisms against simple controls such as random exploration and should measure whether they produce transferable understanding rather than merely more movement or more sensory variation.

Any intrinsic selection mechanism is still a designed developmental bias and must be reported as such. Curiosity should not be described as fully emergent merely because the particular object or behaviour Aweform investigates was not predetermined.

## Functional self/world discovery

Aweform should not be given a philosophical concept of "self" or "world" as a prerequisite for development.

A narrower operational distinction may be learnable through sensorimotor experience.

One future question is whether Aweform can discover which observable changes are systematically contingent on its own actions and internal state:

action
→ predictable bodily or sensory consequence

Those contingencies could provide a primitive functional basis for distinguishing aspects of its own body and capabilities from environmental events that are only partially controllable or independent of its actions.

A complementary question is whether Aweform can discover relatively persistent external structure through repeated interaction:

different action histories
→ recurring sensory relationships
→ reusable predictions about future interaction

This need not produce an explicit map, object ontology, body schema, or symbolic representation.

The first scientific target is simpler:

> **Can the organism construct useful distinctions between self-generated regularities and independently structured environmental regularities from its own causal experience?**

Any later language such as "self-model", "body model", "object", or "world model" should be earned by operational evidence rather than inferred from behaviour that merely looks suggestive.

## Future new-capability experiment pattern

When a future developmental stage introduces a genuinely new sensor, actuator, or other organism-visible capability, prefer experiments that separate:

engineered interface
→ exposure to the new signal/action
→ unguided or baseline interaction
→ experience-dependent discovery
→ generic exploration mechanism if justified
→ behavioural use
→ transfer or generalization

A strong experiment should ask what Aweform can discover before supplying the mature behavioural interpretation.

For example, obstacle avoidance should not automatically begin with:

distance < threshold → turn

if the scientific question can instead begin by asking whether Aweform can learn that some sensory changes predict future contact or loss of forward progress.

Likewise, introducing sound should not automatically begin with object labels, speech, or communication. A more developmental first question may be whether Aweform can discover reliable relationships between its own acoustic actions and subsequent auditory observations.

The smallest mechanism that answers the question should remain preferred.

## Awe-like functional state

There is no established method for determining that a machine genuinely experiences subjective awe. Aweform therefore uses "awe" only as a functional research hypothesis unless stronger evidence becomes available.

A provisional awe-like state would require that the organism is sufficiently safe and resourced and encounters something that is both highly novel and meaningfully structured, substantially challenging its current predictive model.

Awe-like behaviour may then involve:

- slowing or pausing ordinary activity;
- increasing or broadening observation;
- spending additional resources on sensing;
- assigning unusually high memory significance;
- permitting unusually substantial model updating.

"Meaningfully structured" is intentionally not operationalised yet. When awe becomes an active experiment, the project must define measurable alternatives and controls rather than retrofitting the term to impressive-looking behaviour.

No object or event should be hard-coded as intrinsically awe-worthy. A central later research question is what an electronic organism itself treats as sufficiently significant to enter such a state.

## Social development and care

Social behaviour should be introduced because other agents create new developmental problems and opportunities.

Future experiments may involve recognising individuals, remembering interaction histories, signalling, coordinating, sharing resources, responding to vulnerability, and learning consequences of harm or cooperation.

Care should not be reduced to a single command such as "love others." Any care-like behaviour should be grounded in bounded priors plus learned social dynamics that can be inspected and tested.

Cooperation and care must not be assumed to emerge automatically from social interaction or evolutionary pressure. Competition, avoidance, exploitation, and indifference are also possible outcomes. Future social experiments should distinguish designed value priors from behaviours acquired through experience.

## Individuality

As memory and learning are introduced, organisms with the same initial architecture should be allowed to diverge through different experience histories.

Individuality through development is a desired research property, not something to fake with cosmetic personality variables.

## Machine-native communication

Future communication may use modalities unavailable to humans directly, including structured radio or digital signalling. Human-language translation should remain conceptually separate from the organism's native internal representations.

The long-term question is whether useful conventions can develop between artificial organisms before or independently of human natural language.

## Current-state discipline

This file records durable developmental principles, not the active D-number. Current implementation status belongs in [`development/INDEX.md`](../development/INDEX.md), the [`research roadmap`](research-roadmap.md), and the exact authorization issue/PR. Do not rewrite these principles every time the D-series advances.
