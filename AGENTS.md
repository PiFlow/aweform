# Aweform Agent Instructions

Read the canonical project documents before changing code:

1. `docs/north-star.md`
2. `docs/developmental-principles.md`
3. the relevant ADR under `docs/adr/`
4. the relevant experiment specification under `experiments/`
5. `docs/reproducibility.md`
6. `docs/safety-boundary.md`

## Current scope

V0.1 is the **electronic-cell stage**. "Electronic cell" is a developmental analogy, not a claim of biological equivalence. The immediate scientific objective is EXP-000: test whether informative access to internal energetic state improves viability relative to a closely matched energy-blind ablation.

Do not reintroduce or add later-stage capabilities unless an explicit task and, where appropriate, a new ADR authorise them. This includes:

- LLMs or human-language cognition
- reinforcement learning or PPO
- JEPA or other learned world models
- camera vision
- memory systems
- curiosity/play mechanisms
- awe mechanisms
- social behaviour
- obstacles or complex physics
- networking or external APIs
- physical robot control
- self-modification or replication
- evolutionary optimisation

## Working rules

- Prefer the smallest mechanism that tests the current hypothesis.
- Do not optimize for sophistication.
- Preserve deterministic seeds, reproducibility, comparator fairness, and experimental controls.
- Keep development/calibration seeds separate from untouched acceptance seeds.
- Never give an agent hidden resource coordinates, absolute position, or other privileged world state unless an experiment explicitly requires it.
- Keep evaluator-only privileged telemetry separate from agent observations.
- Do not change acceptance conditions because results are disappointing.
- Do not tune against acceptance seeds after they have been designated.
- Keep scientific success metrics distinct from reinforcement-learning reward. EXP-000 requires reward to remain exactly `0.0` on every transition.
- Treat the V0.1 energy variable as an engineered viability state, not as biological metabolism or a reward score.
- Distinguish programmed behaviour, learned behaviour, and genuinely unexpected trajectories in reports.
- Do not claim consciousness, emotion, subjective experience, genuine life, metabolism, Darwinian evolution, or emergent intelligence from behavioural evidence alone.
- Keep code readable and testable.
- Do not add dependencies or abstractions solely for anticipated future stages.
- Make obvious minimal engineering choices independently. Ask only when a genuine project-defining ambiguity remains.

The developmental roadmap is a research direction, not a request to pre-build future modules. Do not create speculative abstractions simply to reserve future architecture.
