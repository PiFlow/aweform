# Aweform Agent Instructions

Read the canonical project documents before changing code:

1. `docs/north-star.md`
2. `docs/developmental-principles.md`
3. `docs/development-evidence-workflow.md`
4. the relevant ADR under `docs/adr/`
5. the relevant development record or experiment specification
6. `docs/reproducibility.md`
7. `docs/safety-boundary.md`

For current development status, also inspect [`development/INDEX.md`](development/INDEX.md) and the exact current authorization issue/PR. Do not infer the next stage from stale roadmap prose or conversation memory.

## Current scope

Aweform uses two research lanes:

- **Development (`D-NNN`)** for fast, descriptive, exploratory iteration on legal development seeds.
- **Evidence (`EXP-NNN`)** for important claims that justify frozen protocols, untouched reserved seeds, exact-SHA reproducibility, and independent review.

The accepted lifetime-plasticity / sensory-plasticity closure is **V0.3**, opened by [`ADR 0010`](docs/adr/0010-v0.3-lifetime-plasticity.md). [`ADR 0009`](docs/adr/0009-v0.2-bounded-observation-history-state.md) remains the valid historical authorization for V0.2 work performed under it and is not rewritten by V0.3.

[`ADR 0012`](docs/adr/0012-v0.4-minimal-physical-energy-thermal-boundary.md) opens the accepted V0.4 physical embodiment, energy, and thermal boundary; it supplements rather than replaces the V0.3 provenance closure. [`ADR 0014`](docs/adr/0014-v0.4-thermal-operating-and-failure-thresholds.md) defines the accepted V0.4 thermal operating/failure thresholds, and [`ADR 0015`](docs/adr/0015-v0.4-finite-body-dual-contact-docking-boundary.md) defines the finite-body dual-contact docking boundary. [`ADR 0013`](docs/adr/0013-model-agnostic-independent-review-governance.md) governs model-agnostic independent reviewer selection and records the review-provenance ratification for ADR 0012.

V0.3 permits bounded persistent plastic/learned state within a continuous organism lifetime when every causal write obeys the declared sensory/plasticity provenance boundary. It does not pre-authorize a particular learner, world model, thermal ecology, predictor horizon, arbitration architecture, sensor, memory mechanism, or planner.

Historical EXP-000 through EXP-003 retain their original identifiers and records. EXP-002 confirmatory execution remains specified-but-unexecuted on untouched seeds `50001–51000`.

Committed D-series development currently extends through D-040. The exact committed ledger is [`development/INDEX.md`](development/INDEX.md). Work that is authorized but not yet committed as a D-record must be read from its GitHub authorization issue/PR; at this documentation refresh D-041 is authorized by issue #140 as an evaluator-only sensory-sufficiency audit. That authorization does not expose the candidate beacon receptors to Aweform.

Do not reintroduce or add later-stage capabilities merely because they are plausible future directions. An explicit task is required, and any new or changed **durable architecture, sensory/plasticity, information, or safety permission boundary** requires an appropriate new ADR or explicit ADR amendment plus the formal independent review defined below before merge. Ordinary mechanism choices that stay within an already authorized durable boundary do not require a new ADR merely because they are development work.

In particular, no task implicitly authorizes:

- LLMs or human-language cognition;
- reinforcement learning, PPO, or deep RL;
- JEPA-scale or other learned world-model architectures not otherwise authorized;
- camera vision;
- organism-visible candidate beacon receptors merely because evaluator-only D-041 models them;
- curiosity or play mechanisms;
- awe mechanisms;
- social behaviour;
- obstacles or complex physics;
- networking or external APIs;
- physical robot control;
- self-modification or replication;
- heredity, population selection, or evolutionary optimisation.

## Working rules

- Prefer the smallest mechanism that tests the current developmental question.
- Do not optimize for sophistication.
- Do not make an ecology harder merely because a competent simple controller succeeds; simple success is evidence.
- Preserve deterministic seeds, reproducibility, comparator fairness, and experimental controls.
- Keep evaluator-only privileged state separate from organism-visible observations and plastic updates.
- Treat evaluator-only candidate sensors as diagnostics until a separate sensory-boundary change is explicitly authorized.
- Never give an organism hidden coordinates, true distance, true heading, docking geometry, coverage, lifespan, experiment labels, reserved-seed identity, evaluator success labels, future information, or human task reward unless a future explicit scientific boundary says otherwise.
- Keep development seeds separate from every existing formal reservation.
- Do not change formal acceptance conditions because results are disappointing.
- Do not tune against designated acceptance/confirmatory seeds after they have been reserved for evidence.
- Keep scientific success metrics distinct from organism learning signals or reward. Historical EXP-000's frozen reward requirement remains exactly `0.0` on every transition.
- Treat energy and future internal variables as engineered viability states, not biological claims or reward scores.
- Distinguish programmed mechanisms, learned mechanisms, descriptive observations, hypotheses, causal interventions, shadow/post-hoc analyses, evaluator-only upper bounds, and inferential claims.
- Preserve negative, null, and invalidated results with their provenance.
- Do not claim consciousness, emotion, subjective experience, genuine life, metabolism, or emergent intelligence from behavioural evidence alone.
- Keep code readable and testable.
- Do not add dependencies or abstractions solely for anticipated future stages.
- Make obvious minimal engineering choices independently. Ask only when a genuine project-defining ambiguity remains.

## Canonical development visualizer

`src/aweform/development_visualizer.py` is the canonical reusable post-hoc visualizer for Aweform developmental stages that materially benefit from visualization. Its intended architecture is:

`development-specific runner/adapter -> DevelopmentVisualizationData -> shared Matplotlib renderer`

When Flow or a reviewer asks to visualize a current or future `D-NNN` stage:

- first inspect and reuse `development_visualizer.py` and the existing shared-renderer CLIs;
- add or patch the smallest stage adapter and, only when needed, generic optional fields in the neutral visualization model/shared renderer;
- preserve existing source adapters and their rendering semantics unless the task explicitly requires a compatible shared improvement;
- do **not** create a new stage-specific renderer merely because the new stage has additional diagnostics;
- do not assume every D-stage needs visualization; evaluator audits may be better represented by compact artifacts and records;
- create a separate renderer only if the canonical architecture genuinely cannot represent the requested view and the task explicitly authorizes that architectural exception.

The generic `aweform-visualize --source ...` registry and specialized shared-renderer entry points are documented in [`docs/development-visualizer.md`](docs/development-visualizer.md). The live source/CLI implementation is authoritative over manually copied lists.

Historical experiment-specific visualizers may remain for reproducibility, but they are not the default pattern for new D-lane visualization work.

## Development lane

Ordinary `D-NNN` work is intentionally lightweight. Several meaningful iterations in one evening should be normal.

A development iteration may:

- use legal development/debug seeds;
- visualize and inspect behaviour;
- tune or discard mechanisms;
- record descriptive observations and surprises;
- run causally isolated evaluator branches or shadow analyses when explicitly authorized;
- end as `ABANDONED`, `CONTINUING`, or `PROMOTED→EXP-NNN`.

It makes **no confirmatory claim**. A D-result may motivate a later EXP protocol but cannot count as confirmatory evidence for that claim.

Development work does not require the formal two-reviewer exact-SHA gate for every iteration when it makes no evidence claim and does not change a durable architecture/information/sensory-plasticity/safety boundary, frozen evidence, or reserved-seed contract. Normal tests still apply and Flow controls merges.

High-leverage D-lane causal audits may still require independent replay/identity/clone/order controls when shared-helper or common-mode error could undermine the scientific interpretation. This is a scientific validity requirement, not automatically the ADR-0013 formal two-reviewer gate.

## Evidence and durable-boundary review

Formal independent review remains mandatory for:

- evidence-lane EXP claims/executions;
- new or changed durable architecture, sensory/plasticity, information, or safety boundaries;
- modifications to frozen evidence or reserved-seed contracts.

Reviewer selection and provenance follow [`ADR 0013`](docs/adr/0013-model-agnostic-independent-review-governance.md).

For those reviews:

- Luna/Codex may implement, but its own summary is not independent evidence.
- Flow designates at least two independent high-capability reviewers for the exact candidate; no particular vendor or model is permanently required.
- The second reviewer should, whenever practical, be from a different model family/provider from the first to increase error diversity.
- Each independent review of record must identify the reviewer/model, `PASS` or `REQUEST CHANGES`, and the exact reviewed HEAD SHA, with enough substantive reasoning to show what was checked.
- The review of record must be archived on the relevant GitHub PR. If an external terminal reviewer cannot post directly, Flow or a maintainer may archive a faithful transcript or concise provenance-preserving summary, clearly labelled so no reviewer is impersonated.
- Only `PASS` against the exact current HEAD qualifies. Any later commit invalidates that `PASS` and requires review of the new HEAD.
- Repository evidence outranks agent summaries, and no actor treats its own implementation as independent approval.
- Flow authorises merges. Merge only after at least **two qualifying independent reviewers pass the exact current candidate** and Flow authorises it.

Changes to this review governance require an explicit Flow decision and a durable repository record; reviewer unavailability alone must not be hidden by pretending a review occurred.
