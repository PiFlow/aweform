# Aweform

Aweform is an open research project exploring the development of an electronic artificial life-form from homeostasis toward adaptive cognition.

The project does **not** begin with a chatbot, LLM, human-like psychology, or a claim of machine consciousness. It starts with the smallest viable developmental problem: an electronic organism with an inside and an outside, finite energy, limited sensing, simple action, and a need to remain within viable energetic and thermal bounds.

Here, **electronic cell** is a developmental analogy for that minimal inside/outside viability problem. It does not claim to reproduce biological cells or biological metabolism.

## Current research state

Aweform currently combines accepted V0.3/V0.4 boundaries with an accepted prospective V0.5 boundary:

- **V0.3 lifetime plasticity / sensory-plasticity closure**, opened by [`ADR 0010`](docs/adr/0010-v0.3-lifetime-plasticity.md), permits bounded persistent learned state within one continuous lifetime when every causal write obeys the declared sensory/plasticity provenance boundary.
- **V0.4 physical energy / thermal embodiment and historical finite-body docking**, opened by [`ADR 0012`](docs/adr/0012-v0.4-minimal-physical-energy-thermal-boundary.md) and refined by [`ADR 0014`](docs/adr/0014-v0.4-thermal-operating-and-failure-thresholds.md), [`ADR 0015`](docs/adr/0015-v0.4-finite-body-dual-contact-docking-boundary.md), and [`ADR 0016`](docs/adr/0016-v0.4-d042-founder-selected-embodiment-boundary.md), defines the historical D-019→D-044 physical-development lineage.
- **Prospective V0.5 direct differential drive**, defined by accepted [`ADR 0017`](docs/adr/0017-v0.5-direct-differential-drive-centered-dock-boundary.md), replaces only the explicitly listed future-facing V0.4 surfaces with one continuous signed bilateral wheel-delta action, minimal differential-drive kinematics, a centred under-body dock, exactly two quantized wheel-delta proprioceptive channels, and continuous wheel-dependent actuator bookkeeping. ADR 0017 does **not** itself authorize D-045 implementation.

These layers supplement rather than erase earlier work. Historical experiments, ADRs, records, source semantics, and artifacts remain part of the record.

The committed development lane now extends through **D-044**. The canonical ledger is [`development/INDEX.md`](development/INDEX.md); detailed records live under [`development/`](development/).

Important recent milestones include:

- D-024–D-026 established the V0.4 finite-body dual-contact docking substrate and bounded stochastic de-trapping scaffold.
- D-027 and D-030 established a small learned sensorimotor consequence model and its first narrow causal use in SEEK steering; D-031R1 showed that learned steering was not sufficient to replace the engineered de-trapping scaffold.
- D-032–D-040 audited that failure and the causal machinery behind it.
- D-041 completed the evaluator-only front-beacon sensory-sufficiency audit and returned a **NULL/INSUFFICIENT** result on both reused support and fresh holdout; its candidate receptors never became organism-visible sensors.
- D-042 introduced the accepted founder-selected V0.4 5° turn/front-contact embodiment, D-043 characterized fresh-seed repeated-cycle robustness, and D-044 separated strong coarse station homing from fragile terminal dual-contact docking while auditing shorter-step and de-trap alternatives without changing the organism.
- ADR 0017 then established the prospective V0.5 reset: direct continuous bilateral wheel-delta control, deterministic differential-drive kinematics, centred under-body docking, two quantized wheel-delta channels, and retirement of the V0.4 D-026/D-027/D-030 scaffold stack from the prospective V0.5 organism.

Any uncommitted next work, including D-045, must be read from the exact current GitHub authorization issue/PR. Do not infer implementation permission from ADR 0017's prospective sequence or from roadmap prose.

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
