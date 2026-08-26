# Aweform Agent Instructions

Read the canonical project documents before changing code:

1. `docs/north-star.md`
2. `docs/developmental-principles.md`
3. the relevant ADR under `docs/adr/`
4. the relevant experiment specification under `experiments/`
5. `docs/reproducibility.md`
6. `docs/safety-boundary.md`

## Current scope

V0.2 is the **BOHS-authorized electronic-cell stage**, opened by [`ADR 0009`](docs/adr/0009-v0.2-bounded-observation-history-state.md). "Electronic cell" is a developmental analogy, not a claim of biological equivalence. V0.2 changes exactly one permission boundary from V0.1: controllers may add bounded one-step observation-history state to the causal action path, within ADR 0009's conditions, budget, and registration rule. The substrate, environment, and observation/action contract are unchanged, and every other V0.1 non-goal still stands. V0.1 is not closed: EXP-002's confirmatory execution remains specified but unexecuted on untouched seeds `50001–51000`.

Do not reintroduce or add later-stage capabilities unless an explicit task and, where appropriate, a new ADR authorise them. This includes:

- LLMs or human-language cognition
- reinforcement learning or PPO
- JEPA or other learned world models
- camera vision
- memory systems beyond the bounded one-step observation-history state authorised by ADR 0009 — that authorisation caps a controller at **one** such value, forbids retained state from determining an observation-write's value, function, or input components, and gates merging on the registry and executable checks required by ADR 0009
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
- Treat the energy variable as an engineered viability state, not as biological metabolism or a reward score.
- Distinguish programmed behaviour, learned behaviour, and genuinely unexpected trajectories in reports.
- Do not claim consciousness, emotion, subjective experience, genuine life, metabolism, Darwinian evolution, or emergent intelligence from behavioural evidence alone.
- Keep code readable and testable.
- Do not add dependencies or abstractions solely for anticipated future stages.
- Make obvious minimal engineering choices independently. Ask only when a genuine project-defining ambiguity remains.

The developmental roadmap is a research direction, not a request to pre-build future modules. Do not create speculative abstractions simply to reserve future architecture.

## Review workflow

- Luna/Codex is the primary implementation agent.
- GPT-5.6 Sol performs the first independent implementation/scientific review; Claude Opus 5 performs the final independent review.
- Each independent review of record must be posted as a comment on the relevant GitHub PR and must contain the reviewer identity, `PASS` or `REQUEST CHANGES`, and the exact reviewed HEAD SHA. Only `PASS` against the current HEAD qualifies. Any later commit invalidates that `PASS` and requires review of the new HEAD.
- Repository evidence outranks agent summaries, and no actor treats its own implementation as independent approval.
- Flow authorises merges. Merge only after both Sol and Opus pass the exact current candidate and Flow authorises it.
