# EXP-000 — Interoception and Viability

**Status:** Proposed first experiment

## Question

In a bounded resource environment with identical external sensory access, does **informative access to internal energetic state** improve viability relative to an otherwise closely matched controller deprived of useful interoception?

## Why this comes first

Aweform begins from a minimal life-like problem rather than a task reward: maintaining an internal state within viable bounds while acting in an environment that can replenish or deplete it.

The experiment is intentionally simple. It does not test intelligence, consciousness, emotion, play, learning, biological metabolism, or Darwinian evolution.

The homeostatic policy itself is programmed. EXP-000 tests the consequence of closed-loop coupling between interoception, limited exteroception, action, and energetic viability.

## Environment constraints

The implementation should use a bounded simulated world with:

- finite episode horizon;
- finite internal energy;
- explicit energy expenditure through existence and/or action;
- one simple renewable resource field or resource source;
- only local external sensing;
- no absolute position provided to controllers unless required for simulator internals and kept hidden from agents;
- no hidden resource coordinates exposed to agents;
- matched random seeds across comparator conditions;
- no obstacles or complex physics in the first confirmatory version unless the protocol is explicitly revised before acceptance testing.

Exact world dimensions, action costs, thresholds, resource dynamics, and sensor geometry are engineering parameters to choose minimally during calibration and then freeze before confirmatory evaluation.

Energy must be causally relevant to viability. Reaching the failure bound must terminate or otherwise disable continued organism activity according to the frozen protocol; energy must not function merely as an observer score.

## Comparator conditions

### A. Random / persistent-exploration reference

The same simulated body and external sensors, using one precisely specified random or persistent-exploration policy chosen and frozen before confirmatory evaluation. It has no purposeful homeostatic behavioural switching.

This condition is primarily a reference for task difficulty and the value of any structured controller.

### B. Homeostatic controller

A transparent controller that can access the organism's actual internal energy state and uses that state to switch between simple behavioural modes such as exploration, resource seeking, or conservation.

Use hysteresis or another simple documented method to avoid unstable rapid switching around thresholds.

### C. Energy-blind ablation — primary causal control

Use the same controller structure as the homeostatic condition, but replace true energy interoception with one precisely specified non-informative signal.

The masking method must be chosen and documented before confirmatory evaluation. Fixed, shuffled, delayed, or otherwise corrupted energy signals are **not interchangeable experimental conditions**; if more than one is tested, report them separately rather than pooling them.

The ablation should preserve as much controller structure as possible so the main causal difference is access to informative internal energy state rather than unrelated policy complexity.

The primary causal contrast for EXP-000 is **B versus C**. Condition A provides an additional behavioural reference.

## Reward

Gymnasium reward, if Gymnasium is used, remains exactly `0.0` on every EXP-000 transition.

The agents are not trained to maximize a reward. Scientific outcomes are measured directly.

## Primary outcomes

Before confirmatory evaluation, freeze a small primary outcome set. It should include direct viability measures such as:

- horizon survival and/or lifespan;
- fraction of time within defined viable energetic bounds;
- energy-deficit burden or time spent below a critical threshold.

The exact primary endpoint, effect direction, and any minimum effect-size criterion must be declared before acceptance-set results are inspected.

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

These diagnostics explain behaviour; they should not be promoted post hoc into primary success criteria because the original result is disappointing.

## Calibration and confirmatory evaluation

Use a two-stage process:

1. **Calibration/development:** choose minimal world and controller parameters using designated development seeds. Failed and trivial configurations may be changed here, with changes recorded.
2. **Confirmatory evaluation:** run the frozen protocol on untouched acceptance seeds. Do not inspect or tune against these seeds beforehand.

Before the first confirmatory run, record at minimum:

- environment dimensions and resource parameters;
- observation and action contract;
- energy costs and viability thresholds;
- controller thresholds and hysteresis;
- exact ablation method;
- development/calibration seed set;
- acceptance seed set or deterministic rule that generates it;
- primary outcomes and interpretation criteria.

If any of these are changed after acceptance results are viewed, create a new experiment revision and clearly label the earlier result.

## Experimental controls

- Run comparator conditions on matched environment seeds.
- Keep body, external sensors, action limits, resource dynamics, and episode horizon identical across conditions.
- Do not tune one condition against test seeds unavailable to the others.
- Record parameters, code revision, software versions, and random seeds with results.
- Preserve unsuccessful runs rather than silently changing success criteria.
- Keep evaluator-only privileged state separate from agent observations.

## Interpretation

A result in which the intact homeostatic condition reliably improves the preregistered viability outcome relative to the energy-blind ablation would support a narrow claim:

> informative interoception can causally organise a transparent perception-action policy around energetic viability in this simulated environment.

If it also outperforms the random/persistent-exploration reference, that establishes that the structured policy is useful in the chosen environment, but this is secondary to the B-versus-C causal contrast.

It would **not** demonstrate emergent intelligence, subjective motivation, consciousness, emotion, genuine biological life, metabolism, or a general survival instinct.

A null or negative result is scientifically useful. It would indicate that the chosen coupling between interoception, sensing, environment, and behaviour is insufficient, uninformative, or poorly specified and should be investigated rather than hidden by adding complexity.

A very large positive result may also be scientifically weak if the environment is trivial or the ablation makes failure inevitable by construction. The result must therefore be interpreted together with task difficulty, behavioural diagnostics, and the exact masking protocol.

## Implementation boundary

The first implementation should remain deliberately small. Do not add neural networks, reinforcement learning, memory, curiosity, play, awe, language, social behaviour, camera vision, networking, hardware, obstacles, or complex physics as part of EXP-000.
