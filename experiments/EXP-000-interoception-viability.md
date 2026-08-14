# EXP-000 — Interoception and Viability

**Status:** Proposed first experiment

## Question

In a bounded resource environment with identical external sensory access, does access to an organism's own internal energetic state causally reorganize behaviour in a way that improves viability?

## Why this comes first

Aweform begins from a minimal life-like problem rather than a task reward: maintaining an internal state within viable bounds while acting in an environment that can replenish or deplete it.

The experiment is intentionally simple. It does not test intelligence, consciousness, emotion, play, or learning.

## Environment constraints

The implementation should use a bounded simulated world with:

- finite episode horizon;
- finite internal energy;
- energy expenditure through existence and/or action;
- one simple renewable resource field or resource source;
- only local external sensing;
- no absolute position provided to controllers unless required for simulator internals and kept hidden from agents;
- no hidden resource coordinates exposed to agents;
- matched random seeds across comparator conditions.

Exact world dimensions, action costs, thresholds, and resource dynamics are engineering parameters to choose minimally and document before running confirmatory experiments.

## Comparator conditions

### A. Random / persistent exploration control

The same simulated body and external sensors, using a simple random or persistent-exploration policy. It has no purposeful homeostatic behavioural switching.

### B. Homeostatic controller

A transparent controller that can access the organism's actual internal energy state and uses that state to switch between simple behavioural modes such as exploration, resource seeking, or conservation.

Use hysteresis or another simple method to avoid unstable rapid switching around thresholds.

### C. Energy-blind ablation

Use the same controller structure as the homeostatic condition, but replace true energy interoception with a masked, fixed, shuffled, or otherwise non-informative signal chosen before the experiment.

The ablation should preserve as much controller structure as possible so the causal difference is access to informative internal energy state rather than unrelated policy complexity.

## Reward

Gymnasium reward, if Gymnasium is used, remains `0.0` for EXP-000.

The agents are not trained to maximize a reward. Scientific outcomes are measured directly.

## Primary outcomes

Prefer a small preregistered set of primary outcomes before large experiment runs, likely including:

- horizon survival / lifespan;
- fraction of time within defined viable energetic bounds;
- energy-deficit burden or time spent below a critical threshold.

## Secondary diagnostics

Useful diagnostics may include:

- minimum energy;
- energy harvested;
- energy consumed;
- time to first resource discovery;
- latency from low-energy state to resource-seeking/recharge;
- distance travelled;
- spatial coverage/exploration;
- number and duration of behavioural-mode transitions.

## Experimental controls

- Run comparator conditions on matched environment seeds.
- Keep body, external sensors, action limits, resource dynamics, and episode horizon identical across conditions.
- Do not tune one condition against test seeds unavailable to the others.
- Separate exploratory parameter tuning from confirmatory evaluation when practical.
- Record parameters and random seeds with results.
- Preserve unsuccessful runs rather than silently changing success criteria.

## Interpretation

A result in which the homeostatic condition reliably improves viability relative to both controls would support a narrow claim:

> informative interoception can causally organize a perception-action policy around energetic viability in this simulated environment.

It would **not** demonstrate emergent intelligence, subjective motivation, consciousness, emotion, genuine biological life, or a general survival instinct.

A null or negative result is also scientifically useful. It would indicate that the chosen coupling between interoception, sensing, environment, and behaviour is insufficient or poorly specified and should be investigated rather than hidden by adding complexity.

## Implementation boundary

The first implementation should remain deliberately small. Do not add neural networks, reinforcement learning, memory, curiosity, play, awe, language, social behaviour, camera vision, networking, or hardware as part of EXP-000.
