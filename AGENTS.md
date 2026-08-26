# Aweform Agent Instructions

Read the canonical project documents before changing code:

1. `docs/north-star.md`
2. `docs/developmental-principles.md`
3. `docs/development-evidence-workflow.md`
4. the relevant ADR under `docs/adr/`
5. the relevant development record or experiment specification
6. `docs/reproducibility.md`
7. `docs/safety-boundary.md`

## Current scope

Aweform now uses two research lanes:

- **Development (`D-NNN`)** for fast, descriptive, exploratory iteration on legal development seeds.
- **Evidence (`EXP-NNN`)** for important claims that justify frozen protocols, untouched reserved seeds, exact-SHA reproducibility, and independent review.

The current developmental permission boundary is **V0.3 — lifetime plasticity / sensory-plasticity closure**, opened by ADR 0010. ADR 0009 remains the valid historical authorization for V0.2 work performed under it and is not rewritten by V0.3.

V0.3 permits bounded persistent plastic/learned state within a continuous organism lifetime when every causal write obeys the declared sensory/plasticity provenance boundary. It does not pre-authorize a particular learner, world model, thermal ecology, predictor horizon, or arbitration architecture.

Historical EXP-000 through EXP-003 retain their original identifiers and records. EXP-002 confirmatory execution remains specified-but-unexecuted on untouched seeds `50001–51000`.

Do not reintroduce later-stage capabilities merely because they are plausible future directions. In particular, no task implicitly authorizes LLM cognition, PPO/deep RL, JEPA-scale models, curiosity/play, social behaviour, networking, external APIs, physical robot control, self-modification, replication, heredity, population selection, or evolutionary optimisation.

## Working rules

- Prefer the smallest mechanism that tests the current developmental question.
- Do not optimize for sophistication.
- Do not make an ecology harder merely because a competent simple controller succeeds; simple success is evidence.
- Keep evaluator-only privileged state separate from organism-visible observations and plastic updates.
- Never give an organism hidden coordinates, true distance, coverage, lifespan, experiment labels, reserved-seed identity, evaluator success labels, future information, or human task reward unless a future explicit scientific boundary says otherwise.
- Keep development seeds separate from every existing formal reservation.
- Do not change formal acceptance conditions because results are disappointing.
- Treat energy and future internal variables as engineered viability states, not biological claims or reward scores.
- Distinguish programmed mechanisms, learned mechanisms, descriptive observations, hypotheses, and inferential claims.
- Preserve negative and null results.
- Do not claim consciousness, emotion, subjective experience, genuine life, metabolism, or emergent intelligence from behavioural evidence alone.
- Do not add dependencies or abstractions solely for anticipated future stages.
- Make obvious minimal engineering choices independently. Ask only when a genuine project-defining ambiguity remains.

## Development lane

Ordinary `D-NNN` work is intentionally lightweight. Several meaningful iterations in one evening should be normal.

A development iteration may:

- use legal development/debug seeds;
- visualize and inspect behaviour;
- tune or discard mechanisms;
- record descriptive observations and surprises;
- end as `ABANDONED`, `CONTINUING`, or `PROMOTED→EXP-NNN`.

It makes **no confirmatory claim**. A D-result may motivate a later EXP protocol but cannot count as confirmatory evidence for that claim.

Development work does not require dual Sol + Opus exact-SHA review for every iteration when it makes no evidence claim and does not change a durable architecture/information/safety boundary, frozen evidence, or reserved-seed contract. Normal tests still apply and Flow controls merges.

## Evidence and durable-boundary review

Formal independent review remains mandatory for:

- evidence-lane EXP claims/executions;
- new or changed durable architecture, sensory/plasticity, information, or safety boundaries;
- modifications to frozen evidence or reserved-seed contracts.

For those reviews:

- Luna/Codex may implement, but its own summary is not independent evidence.
- GPT-5.6 Sol performs the first independent implementation/scientific review.
- Claude Opus 5 performs the final independent review.
- Each review of record must identify the exact reviewed HEAD SHA and state `PASS` or `REQUEST CHANGES`.
- A later commit invalidates the prior exact-SHA pass and requires review of the new HEAD.
- Repository evidence outranks agent summaries.
- Flow authorises merges.

The developmental-reset foundation itself changes durable governance and therefore remains subject to this rigorous review before merge.
