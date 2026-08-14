# Aweform Agent Instructions

Read the canonical project documents before changing code:

1. `docs/north-star.md`
2. `docs/developmental-principles.md`
3. the relevant ADR under `docs/adr/`
4. the relevant experiment specification under `experiments/`
5. `docs/safety-boundary.md`

## Current scope

V0.1 is the **electronic-cell stage**. The immediate scientific objective is EXP-000: test whether access to internal energetic state changes behaviour in ways that improve viability.

Do not reintroduce or add later-stage capabilities unless an explicit task and, where appropriate, a new ADR authorise them. This includes:

- LLMs or human-language cognition
- reinforcement learning or PPO
- JEPA or other learned world models
- camera vision
- memory systems
- curiosity/play mechanisms
- awe mechanisms
- social behaviour
- networking or external APIs
- physical robot control
- self-modification or replication

## Working rules

- Prefer the smallest mechanism that tests the current hypothesis.
- Do not optimize for sophistication.
- Preserve deterministic seeds, reproducibility, comparator fairness, and experimental controls.
- Never give an agent hidden resource coordinates or privileged world state unless an experiment explicitly requires it.
- Do not change acceptance conditions because results are disappointing.
- Keep scientific success metrics distinct from reinforcement-learning reward. EXP-000 currently requires reward to remain `0.0`.
- Do not claim consciousness, emotion, subjective experience, genuine life, or emergent intelligence from behavioural evidence alone.
- Keep code readable and testable.
- Make obvious minimal engineering choices independently. Ask only when a genuine project-defining ambiguity remains.

The developmental roadmap is a research direction, not a request to pre-build future modules. Do not create speculative abstractions simply to reserve future architecture.
