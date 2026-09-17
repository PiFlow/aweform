# Aweform

Aweform is an open research project exploring the development of an electronic artificial life-form from homeostasis toward adaptive cognition.

The project does **not** begin with a chatbot, LLM, human-like psychology, or a claim of machine consciousness. It starts with the smallest viable developmental problem: an electronic organism with an inside and an outside, finite energy, limited sensing, simple action, and a need to remain within viable energetic and thermal bounds.

Here, **electronic cell** is a developmental analogy for that minimal inside/outside viability problem. It does not claim to reproduce biological cells or biological metabolism.

## Current research state

Aweform currently combines two accepted boundaries:

- **V0.3 lifetime plasticity / sensory-plasticity closure**, opened by [`ADR 0010`](docs/adr/0010-v0.3-lifetime-plasticity.md), permits bounded persistent learned state within one continuous lifetime when every causal write obeys the declared sensory/plasticity provenance boundary.
- **V0.4 minimal physical energy / thermal embodiment**, opened by [`ADR 0012`](docs/adr/0012-v0.4-minimal-physical-energy-thermal-boundary.md), adds a physically grounded simulated battery, power/thermal bookkeeping, and later finite-body docking constraints. [`ADR 0014`](docs/adr/0014-v0.4-thermal-operating-and-failure-thresholds.md) and [`ADR 0015`](docs/adr/0015-v0.4-finite-body-dual-contact-docking-boundary.md) define accepted thermal and docking boundaries.

These layers supplement rather than replace earlier V0.1/V0.2 work. Historical experiments and ADRs remain part of the record.

The development lane has progressed from D-001 through committed **D-040**. The canonical ledger is [`development/INDEX.md`](development/INDEX.md); detailed records live under [`development/`](development/).

Important current milestones include:

- D-024–D-026 established the finite-body dual-contact docking substrate and a bounded stochastic de-trapping scaffold.
- D-027 introduced a small, experience-learned action-conditioned sensorimotor consequence predictor in shadow.
- D-030 demonstrated the first narrow causal use of learned one-step prediction in SEEK steering under matched controls.
- D-031R1 showed that this learned steering was not yet sufficient to displace the engineered de-trapping scaffold.
- D-032–D-040 audited why that displacement failed, including action alternatives, history, predictor state, recurrence, intervention timing, causal validity, and partial-observability hypotheses. D-040 independently revalidated the recent causal machinery; its accepted interpretation keeps partial observability plausible and reports privileged geometry as strongly informative, without authorizing privileged organism inputs or a successor mechanism.

The current authorized-but-not-yet-committed development question is **D-041 — Front-beacon sensory sufficiency audit** ([issue #140](https://github.com/PiFlow/aweform/issues/140)). It is evaluator-only: it asks whether a minimal pair of physically realizable front-facing charging-beacon receptors contains sufficient information to resolve relevant reacquisition/front-docking ambiguity. It does **not** expose those signals to Aweform or change the sensory boundary.

Current authorized work should be read from the repository's accepted records and GitHub authorization issue/PR, not inferred from a predicted future D-sequence in prose documentation.

## Evidence lane

Aweform separates fast descriptive development from formal evidence:

- **Development (`D-NNN`)** is exploratory and descriptive on legal development seeds.
- **Evidence (`EXP-NNN`)** is reserved for claims important enough to justify frozen protocols, untouched reserved seeds, exact-SHA reproducibility, and independent review.

EXP-000 and EXP-001 have completed evidence records. EXP-002 calibration is complete, while its confirmatory execution remains deliberately unexecuted on untouched seeds `50001–51000`. EXP-003 remains the historical localized-charging / bounded-observation-history development foundation and keeps its original identifier.

No D-series result becomes confirmatory evidence merely because it is detailed or causally informative.

## Developmental approach

Aweform uses biology and evolution as inspiration for **problems and principles**, not as a literal ladder or neurological blueprint. Capabilities should be introduced only when the organism's developmental environment creates a problem for which that capability is useful.

The long-term direction includes homeostasis, coordinated subsystems, sensorimotor survival, learning, play and curiosity, social interaction, machine-native communication, richer cognition, and eventually physical embodiment.

The project already contains bounded lifetime learning, but it does **not** thereby contain PPO, deep RL, JEPA-scale cognition, an LLM controller, camera vision, a mature learned world model, social behaviour, play, awe, networking, or physical robot control. Those remain separately governed future questions.

Read:

- [`docs/north-star.md`](docs/north-star.md) — what Aweform is trying to become
- [`docs/developmental-principles.md`](docs/developmental-principles.md) — evolution-inspired development, scaffold transfer, play, curiosity, and awe
- [`docs/development-evidence-workflow.md`](docs/development-evidence-workflow.md) — fast development versus formal evidence lanes
- [`development/INDEX.md`](development/INDEX.md) — canonical committed D-series ledger
- [`docs/research-roadmap.md`](docs/research-roadmap.md) — chronological development arcs and current frontier
- [`docs/adr/README.md`](docs/adr/README.md) — ADR index and durable-boundary map
- [`docs/reproducibility.md`](docs/reproducibility.md) — seed separation, causal replay, and evidence-run discipline
- [`docs/safety-boundary.md`](docs/safety-boundary.md) — simulation and experimental safety boundary

## Scientific humility

Behavioural evidence alone does not establish that Aweform is alive, conscious, emotional, or experiencing anything subjectively. Terms such as "awe", "care", and "curiosity" are used as functional research hypotheses unless stronger evidence ever becomes available.

## Status-source hierarchy

For current-state questions, prefer sources in this order:

1. accepted ADRs and exact repository source for durable boundaries;
2. committed `development/D-NNN` and `experiments/EXP-NNN` records and artifacts;
3. [`development/INDEX.md`](development/INDEX.md) for the committed development ledger;
4. the current GitHub authorization issue/PR for work not yet committed;
5. roadmap and README summaries.

Repository evidence outranks conversational summaries and stale roadmap prose.

## License

Apache-2.0.
