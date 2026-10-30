# Aweform Familiar — Investigation A: External-Agent Information, Safety and Research-Authority Boundary

**Status:** DRAFT RESEARCH / NON-AUTHORIZING — not an ADR, accepted interface or implementation specification.  
**Founder authorization:** [Issue #243 — decision comment](https://github.com/PiFlow/aweform/issues/243#issuecomment-6513908796), 30 Oct 2026.  
**Audited baseline:** `main` at `b90dcace58ec42f7245c922b4ad1c94c12db399b`.  
**Related:** [Investigation B — H2 protocol](2026-10-30-h2-shadow-prediction-investigation.md); existing independent [#240](https://github.com/PiFlow/aweform/issues/240) and [#242](https://github.com/PiFlow/aweform/issues/242) are unaffected.

## Purpose, scope, and authority

**[FOUNDER DECISION]** Option D is the *provisional working direction*: `PiFlow/aweform` remains the sole organism/science/lifetime authority across egg, stationary and wheeled forms; Familiar is a non-authorizing research programme in this repo; a vendor-neutral assistant and separate physical/firmware workstreams are extractable **only when concrete operational boundaries justify them**. No new repo or approved ADR follows from this direction. The founder's same-battery-powered-core and removable-shell vision is a target, not current hardware permission.

This document investigates the **minimal external causal interaction** required to test whether an Aweform learner can make a prospective prediction about an external event. It does **not** implement the event, channel, intervention, state schema, social output, assistant, user study, physical egg, charger or learned policy. It must not grant any new permission merely by being merged as research.

### Sources and evidence hierarchy

1. Authoritative: [`AGENTS.md`](../../AGENTS.md), [North Star](../../docs/north-star.md), [Developmental Principles](../../docs/developmental-principles.md), [Development/Evidence workflow](../../docs/development-evidence-workflow.md), [Safety Boundary](../../docs/safety-boundary.md), [Reproducibility](../../docs/reproducibility.md), accepted [ADR 0010](../../docs/adr/0010-v0.3-lifetime-plasticity.md), [ADR 0017](../../docs/adr/0017-v0.5-direct-differential-drive-centered-dock-boundary.md), [ADR 0018](../../docs/adr/0018-three-layer-developmental-architecture-and-innate-viability-floor.md) and [ADR 0019](../../docs/adr/0019-v0.5-physical-arena-wall-contact-boundary.md). ADR 0020 remains proposed; it is not an implicit Familiar permission.
2. Canonical committed D status: [`development/INDEX.md`](../../development/INDEX.md); `CONTINUING` is a scientific-thread disposition, not an incomplete run. D-046–D-048 represent **shadow prediction** on V0.5 channels; do not mislabel their learned weights as organism-controlled social behaviour. [D-030](../../development/D-030-bounded-learned-seek-steering.md) is bounded causal steering with no benefit over reference. [D-061 PR #237](https://github.com/PiFlow/aweform/pull/237) remains an unmerged descriptive candidate, not committed evidence.
3. Founder-shared research at immutable `5338c2890ccbbe2b05e08c01de804190240ce7df`: [Chaptered Familiar research](https://github.com/PiFlow/aweform/blob/5338c2890ccbbe2b05e08c01de804190240ce7df/research/familiar/2026-10-30-shared-evidence/01-aweform-familiar-deep-research-chaptered.md), [post-research conversation](https://github.com/PiFlow/aweform/blob/5338c2890ccbbe2b05e08c01de804190240ce7df/research/familiar/2026-10-30-shared-evidence/02-aweform-familiar-conversation-2026-10-29.md), [Opus R1](https://github.com/PiFlow/aweform/blob/5338c2890ccbbe2b05e08c01de804190240ce7df/research/familiar/2026-10-30-shared-evidence/03-claude-opus-5-5-round-1-independent-review.md), plus [source manifest](https://github.com/PiFlow/aweform/blob/5338c2890ccbbe2b05e08c01de804190240ce7df/research/familiar/2026-10-30-shared-evidence/README.md). These are **research inputs**, not decisions.
4. The converged [Sol ↔ Opus issue #243](https://github.com/PiFlow/aweform/issues/243): Opus [Round 3](https://github.com/PiFlow/aweform/issues/243#issuecomment-6513551694), Sol [preceding response](https://github.com/PiFlow/aweform/issues/243#issuecomment-6513522007). Reviewer statements are proposals unless founder-adopted.

## What is actually allowed now

**[VERIFIED REPOSITORY FACT]** The current simulated organism may use only the specifically accepted organism-visible channels and actions in its authorised substrate. V0.5 first-slice observations are **exactly eight**: energy, temperature, three station-beacon measurements, charging contact and two wheel-delta signals ([ADR 0017 §F](../../docs/adr/0017-v0.5-direct-differential-drive-centered-dock-boundary.md)); its compound wheel commands have a 0.1 s control interval. There is **no accepted external-agent identity, nonsemantic cue, socially controlled heat intervention or social-output channel**. Existing physical-world/safety work remains simulator-only.

**[VERIFIED REPOSITORY FACT]** [ADR 0010 §D–E](../../docs/adr/0010-v0.3-lifetime-plasticity.md) requires every plastic causal write to depend only on lawful organism-visible input, the organism's actual actions/consequences, retained causal state and declared RNG. Hidden future outcomes, evaluator geometry, condition labels, synthetic partner identity, human reward and retrospective intervention labels are **not** available to the learner. Evaluator-only truth may be logged for diagnosis without entering organism causal state. [ADR 0018](../../docs/adr/0018-three-layer-developmental-architecture-and-innate-viability-floor.md) protects constitutive Level-1 viability from Level-2/3 learned-state writes and read-based control.

**[VERIFIED REPOSITORY FACT]** [`docs/safety-boundary.md`](../../docs/safety-boundary.md) prohibits networking, external APIs, secret/user-data access, real physical-device control and uncontrolled persistence by the simulated organism. A separate assistant must not become a route around those prohibitions.

## Minimal H2 causal boundary to investigate (NOT APPROVED)

**[DESIGN HYPOTHESIS]** For a first simulated H2 experiment only, consider:

- A **neutral, nonsemantic, bounded external cue** `cue_t` observable at current time (e.g., a binary signal, not `caregiver_A`, `helpful`, `partner_trust`, experiment-arm ID, countdown or evaluator truth). Whether it is the least invasive sensory choice must be established in the *sensor-sufficiency audit*, not assumed.
- An **external environment intervention** `cooling_t`: bounded, transient, nonessential assistance to thermal dynamics while the organism remains safely viable without it. It is deliberately **not** emergency energy rescue, demand for human care or an organism-supplied task reward. An intervention is a world event; it must not be silently mapped to `reward`, `info`, or hidden teaching labels.
- A **causally available thermal consequence**, read as the already-authorised temperature channel *after it occurs*. The experimenter knows the intervention cause; the organism may only predict experienced temperature changes from visible history. The cue may precede an unpredictable or variable delay; no future intervention metadata may enter a predictor.
- **Shadow learner only** for the first H2 trial: predictor updates may observe actual lawful transitions; predictions may not influence organism control, Level 1, event schedules, action choices or assistant output. No genuine human participant, physical microphone/camera or device control.

These are candidate source-level contracts for independent review, *not* a claim that the current V0.5 eight-channel sensor boundary already includes the proposed cue.

### Information-flow / permissions matrix

| Producer → consumer | Candidate content | Authority now | Boundary to enforce |
|---|---|---|---|
| Existing physical simulator → organism | Eight already accepted V0.5 channels | Existing substrate only | Current observation contract and causality |
| Proposed external process → world physics | Bounded nonessential cooling; neutral external cue schedule | **Research proposal only** | Environment schedule explicit, deterministic/seeded; no viability rescue or covert task objective |
| Proposed world → organism | Neutral current cue receptor | **Requires reviewed sensory/info permission before any implementation** | No partner name, clock/phase label, future event or hidden condition |
| Real past organism observations/actions → shadow learner | Causal experience, after outcome | Conditional on an independently approved experiment | Complete plastic-state declarations and write closure |
| Evaluator → research logs | True intervention times, source ID, event schedule, ground-truth labels | Evaluator diagnostics under separately authorised protocol | Strict one-way audit path; no leakage to organism or readout selector |
| Learner → actuator/Level 1/assistant | Learned prediction or social preference | **Not authorised** | Disconnected in H2; separate later ADR, review and comparator gates |
| Hermes/LLM → organism | Tool instructions, human language, learned-state edits, reward | **Not authorised** | No direct network/write access or attribution of LLM competence to organism |
| Future assistant ← published export | Least-privilege observable/provenance summary | **Not yet implemented or authorised** | Distinct assistant memory/identity; a reviewed export schema and permissions |
| Future caregiver/device → world | Charger, shell, skin, microphone, physical robot control | **Not authorised** | Separate physical/ethics/safety approvals; not part of first H2 |

### Attribution and provenance separation

An eventual evaluator event log (not organism observation) should distinguish: `event_source_kind` = environment process / scripted agent / human / assistant; externally stable `source_id`, `planned_at` and `actual_at` timestamps, action duration/intensity, physics variables changed, cue schedule provenance, and independent RNG streams. These fields **must never be encoded as organism-facing teacher labels**. If an assistant ever causes a world event, record its actual causal identity; do not count that event as a human partner response.

The planned H2 'agent' is **an experimental external process**, not an identified social partner. Partner recognition, reliability, trust, care and attachment are **not** outcomes of H2. External-event observability should be checked *before* any claim that the organism learned an 'agent' rather than time or physical dynamics.

## Confounds and safety obligations for later phases (not first H2)

- **Human-charged portable egg:** manual charging couples energy rise with handling, vibration, presence and sound. Randomized *times* do not by themselves remove handling confounding. Battery interoception may still be studied, but human-specific causal claims require isolation or counterbalancing; a scheduled, person-independent base is cleaner for those studies. A docked nest or charging base is engineered power availability, **not demonstrated autonomous return-to-charge**. Preserve the founder's portable egg and the optional controlled-base comparator; do not construct either here.
- **Modular shell/skin/microphone:** sensor removal is not numerical zero; an explicit availability mask would itself be a new organism-visible channel requiring reviewed authority. Replacing a module can change gain, delay, noise and consequence statistics; log intervention in evaluator provenance. The one organism may retain continuous identity only through a separately justified state/interface migration. See [ADR 0010 §B–C](../../docs/adr/0010-v0.3-lifetime-plasticity.md); no implicit cross-stage inherited weights.
- **Continuity / restore:** exact deterministic checkpoint-resume, rollback that loses intervening experience, and two concurrent hardware instances are different causal situations. Neither a hash chain nor a lease by itself proves unique physical identity. Treat lineage/fork semantics as a **third future document**, not authorisation to implement persistence now.
- **Human safety/privacy:** no unconsented recording, collection of partner identifiers/biometrics or reliance on a public Git repo for human-subject audio/events. Any human-facing signal or physical device requires its own consent, privacy, child-safety, electrical/thermal and device-control review. Do not anthropomorphise failure as distress or battery dependence as affection.

## Required governance delta before any H2 execution

| Surface | Current constraint / research gap | Proposed future action **(requires separate founder permission, review and merge)** |
|---|---|---|
| ADR 0010 (plasticity closure/lifetime) | No external cue as approved organism input; complete write provenance and no stealth resets | Add precise lawful cue semantics and retained temporal-history declarations if needed; keep no evaluator future/labels |
| ADR 0017 (V0.5 observation and action) | Exactly eight first-slice observations; no social/thermal-intervention receptor | New or amended sensory boundary: cue range, timing, missingness, normalization, transition sampling; clarify target ecology |
| ADR 0018 (innate viability) | Level 1 not controlled by learned state | Establish nonessential/viable cooling bounds and demonstrate floor remains unchanged with intervention ON/OFF |
| ADR 0019 / accepted world physics | Physical room/wall contract; no generic authority for arbitrary external effects | Explicit, narrow world-intervention contract, if applicable; do not silently change motor, wall or obstacle physics |
| Safety boundary | No physical device, network, external API or real human interaction | Preserve simulator-only H2; any assistant or hardware route requires independent permission |
| Reproducibility + D/EXP workflow | Fresh reserved evidence seeds and exact-SHA protocols are separately gated | Specify independent intervention/learner RNG and no leakage; new D task before runs, and later separate EXP approval |
| AGENTS.md / reference classification | Existing `research/` material should not become normative by proximity | **Propose one non-authorizing sentence below**, but **do not edit AGENTS.md under this task** |

**Proposed later governance sentence (NOT APPLIED):** “Files under `research/` are non-authorizing research inputs and proposals; they do not extend organism capabilities, amend accepted ADRs or grant implementation/experiment permission absent the normal task-specific authorization and review.”

No prior ADR or safety restriction is waived by writing or later merging these research documents. Formal review of any new durable boundary is governed by [ADR 0013](../../docs/adr/0013-model-agnostic-independent-review-governance.md) and `AGENTS.md`.

## Decisions, falsifiers, and stop points

1. **Observability gate:** Can a prospective current cue plus lawful history improve prediction of a future lawful consequence beyond time/temperature/action alone? If not, *stop*: do not introduce an organism-facing partner label to rescue the result.
2. **Causal isolation gate:** Are all model inputs and state writes traceable to lawful past/current observations or actions, with evaluator labels excluded? If not, stop before any run.
3. **Level-1 gate:** Is the thermal intervention bounded and nonessential, with no dependence of survival on its occurrence and no changed return/docking policy? If not, reject the proposed ecology.
4. **Authority gate:** Is there an explicit, independently reviewed and founder-approved information/sensory/experimental boundary before implementation? If not, no D-stage run.
5. **Progression gate:** H2 held-out success is cue-to-consequence prediction only. Partner identity H3, adaptive reliability, social action, assistant writes and human/physical embodiment require new questions and permission.

## Open questions for founder/reviewers — do not silently decide

- Does the minimal external cue genuinely need an added receptor, or can a lawful existing-signal perturbation test external causation without adding organism-visible labels? Test information sufficiency first.
- Exactly which constant thermal ranges, delays and baseline comparators remain causally informative *and* nonessential? Set values prospectively in an authorised protocol, not by this document.
- When a future removable sensor changes the observation schema, is state projection sufficient, or is a formal new-lifetime event required? Address in the later continuity contract.
- Which private data-handling and assistant integration boundaries become necessary **only** when real users or networked deployments are separately authorised?

**Deliverable boundary:** Research investigation A is completed as a **draft for independent scientific/governance review**. It provides no accepted ADR, code, sensor, executive decision, merged file or approved experiment.
