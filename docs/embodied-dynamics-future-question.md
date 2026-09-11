# Aweform — Future Research Question: Embodied Dynamics Before Explicit Memory

**Status:** non-authorizing future research note  
**Recorded:** 2026-09-11  
**Repository context:** recorded against `PiFlow/aweform` `main` at `f694d47eb2c94cf3afbf07f327036234faceacea`  
**Purpose:** preserve a future scientific question about physical/dynamical memory without authorizing reservoir computing, explicit memory, new sensors, body redesign, a new D-stage, or any current implementation.

## Research reference

A relevant 2026 *Nature Communications* study is:

**Autonomous robotic operation controlled by wave-based neuromorphic hardware**  
https://www.nature.com/articles/s41467-026-77661-3

The study experimentally uses interacting water waves as a physical reservoir for autonomous robotic control. Sensor-driven disturbances alter an ongoing dynamical physical system; the evolving wave state carries temporally extended information that a trained readout can use for control. The work also presents a simulated nanoscale spin-wave analogue.

The important principle for Aweform is not "add reservoir computing." It is that information about previous events can sometimes remain physically present in the current dynamics of a system rather than being represented only as explicit software memory variables.

This paper does **not** demonstrate developmental emergence. The substrate, experimental task, and readout arrangement are externally designed, and useful control depends on a trained readout. It therefore serves as research inspiration and a future testable question, not as an architecture recommendation.

## Future Aweform question

> **How much useful memory, representation, and apparent computation can arise naturally from the ongoing dynamics of Aweform's body and its interaction with the environment before explicit memory or additional cognitive architecture is introduced?**

A broader formulation is:

> **Can cognition partly arise from the dynamics of the organism itself, rather than every cognitive function being implemented as explicit computational state?**

This direction complements the project's existing principle of minimal cognition and the partial-observability/memory gate in [`world-model-developmental-direction.md`](world-model-developmental-direction.md).

## Why this may matter later

A future physical Aweform may have state whose present dynamics naturally depend on recent history: actuator transients, electrical currents, battery response, temperature, vibration, elastic/mechanical settling, sensor adaptation, radio/electromagnetic state, or other organism-visible physical variables. Such state could potentially carry traces of prior actions and events without an explicit history buffer.

That does not mean memory has disappeared. The information would still be embodied in physical state. The scientific question is whether those naturally persistent dynamics contain **usable** history, whether Aweform can learn to exploit it from its own experience, and how long that usefulness persists.

The desired developmental ordering is therefore:

```text
partial observability first demonstrates a real memory problem
        ↓
test whether existing embodied dynamics already carry enough usable history
        ↓
if insufficient, add the smallest explicit memory mechanism that the problem earns
```

## Possible future scientific test

If this question becomes developmentally relevant, begin with evaluator-side measurement rather than giving Aweform a reservoir or memory system.

1. **Passive information audit.** Test whether present organism-visible physical state contains decodable information about earlier events across increasing lags.
2. **Fading-memory curve.** Measure how quickly that information degrades with lag rather than assuming persistence equals useful memory.
3. **Causal destruction control.** Damp, reset, scramble, or otherwise remove the suspected persistence and test whether the lagged information disappears. Correlation alone is not sufficient.
4. **Experience-dependent use.** Only after causal attribution ask whether an Aweform learner can discover and exploit that information from lived sensorimotor consequences without privileged labels.
5. **Explicit-memory comparator.** Compare embodied dynamics against the smallest explicit history mechanism. If physical continuity is sufficient, do not add recurrence merely because conventional architectures contain it.
6. **Much later, separate question:** if heredity/evolution is ever authorized, test whether body/substrate properties that preserve useful history can themselves become selectable traits. Do not conflate this with within-lifetime learning.

## Guards

- Do **not** introduce a physical or simulated reservoir merely to demonstrate reservoir computing.
- Do **not** add explicit memory because memory is expected in a mature cognitive architecture; first demonstrate the developmental problem.
- Do **not** call ordinary physical persistence "memory," "representation," or "computation" without operational and causal evidence.
- Do **not** leak evaluator-only lag labels, hidden state, retrospective targets, coordinates, or future information into organism learning or control.
- Do **not** interpret a supervised/readout-trained reservoir result as developmental emergence.
- Preserve the distinction between programmed body dynamics, naturally persistent physical state, lifetime-learned use of that state, and evaluator-only interpretation.

## Connection to the world-model direction

A future world model need not receive temporal context only from an explicit recurrent memory. Part of the effective state presented to a predictor may already contain traces of past interaction because the physical organism has continuity.

Conceptually:

```text
past sensorimotor events
        ↓
ongoing body/environment dynamics
        ↓
present organism-visible embodied state
        ↓
learned consequence prediction
```

This creates a future question before explicit memory is introduced:

> **Before engineering temporal context inside the cognitive architecture, how much temporal context already exists in the thing being modeled?**

If embodied dynamics prove insufficient, that negative result would be equally useful: it would provide evidence that explicit memory has genuinely earned a role.

## Bottom line

The aim is not to make Aweform a physical reservoir computer. The aim is to discover how much adaptive competence can arise from the causal continuity of being an embodied physical system before additional cognitive machinery is engineered.

This note authorizes **no current implementation** and should not alter the present D-development sequence. Revisit it only when a future exact-current-HEAD developmental problem makes memory, partial observability, embodiment, or temporal representation scientifically relevant.
