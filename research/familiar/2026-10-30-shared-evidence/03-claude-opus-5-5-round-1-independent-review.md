# Aweform Familiar — Round 1 Independent Architecture Review (Opus)

Oct 30, 2026 · @Flo

## Verdict

**Verdict: REQUEST CHANGES — do not create the Familiar or assistant repositories yet.** The lifecycle vision is coherent as art and as a long-range North Star; as an architecture it is premature by at least three unmet developmental milestones, contradicts two accepted ADRs, and inverts the North Star's language principle.

The central problem is not any single component. It is that the proposal describes a **product** (egg, hatching, purchasable modules, phone assistant) while the organism has not yet demonstrated **causal learning above its engineered Level-1 floor**. Every Familiar claim depends on that missing result.

**Basis of this review.** Read: the 2026-10-29 conversation archive; `PiFlow/aweform` at `b90dcac` (2026-10-26) — `AGENTS.md`, `docs/north-star.md`, `docs/safety-boundary.md`, `docs/developmental-principles.md`, ADR 0010, ADR 0018, the research roadmap, the wheel-legged and compute-layering future-direction notes, `development/INDEX.md`, D-007, D-031R1, D-048, D-053, D-059 and the D-060 retrospective. Hermes Agent capabilities from a current third-party summary ([parallel.ai, Oct 2026](https://parallel.ai/articles/what-is-hermes-agent)). The Chaptered Edition research report was not available to me; nothing here relies on it.

**Where the repo actually is (measured, not inferred):**

- 59 committed D-records; **every one is `CONTINUING`** — none `ABANDONED`, none `PROMOTED→EXP`. No EXP since EXP-003.
- The only test of learned behaviour displacing a scaffold (**D-031R1**) failed: without the engineered stochastic de-trap, learned SEEK steering lost reacquisition on every fresh seed.
- D-007 history divergence was seed-dependent with a retained null pair. D-048 learning is shadow-only.
- The organism stays alive through the engineered Level-1 return/dock floor (ADR 0018, D-052→D-059).
- The physical substrate is mid-migration: D-060 obstacles not accepted; an isolated Pymunk prototype (issue #226) is the current path.
- `src/` is \~76k lines across \~60 per-stage modules; tests \~26k.

So the honest position is: **simulated Stage-2 body, engineered viability, no demonstrated causal lifetime learning, no social channel, no hardware.** Calling current First Mate work "Stage 2" of the Familiar lifecycle is true of the body shape only.

## Fundamental flaws and contradictions

Seven problems are structural; each one would survive any amount of engineering polish.

1. **The "dragon soul" inverts the North Star.** The North Star says human language may become an interface but must not be assumed to be the substrate of cognition. Branding the LLM as the organism's *soul* makes pretrained language the inner self — the exact overclaim the project exists to prevent. Every user will attribute Hermes's fluency to the creature. The caveat "it's only a metaphor" does not survive contact with a user; the UX *is* the claim.
2. **No-reset-at-hatching contradicts accepted ADR 0010 §C.** ADR 0010 states that learned/plastic state **resets** at a developmental-stage boundary. Familiar requires the opposite at hatching and at wheels. This is not a wording fix; it needs an ADR amendment, and it is only architecturally safe while the predictor stays linear-additive (new sensor = new row, old weights keep meaning). A hidden layer later would silently break continuity.
3. **The egg removes the organism's viability floor.** ADR 0018 and Conversation 1 both say the caregiver must add value *above* an independent viability floor, never through artificial helplessness. In the egg and the stationary infant, energy acquisition is entirely the human's act. That *is* designed helplessness. The red low-battery light is a need broadcast to a human — functionally a distress signal regardless of the "no emotional pressure" caveat (the Tamagotchi mechanism).
4. **Death semantics are incoherent on hardware.** The settled decision is "death final". In the egg, battery exhaustion either (a) kills the organism permanently — ethically unacceptable for a household object someone forgot to plug in — or (b) triggers safe suspend/resume, in which case energy has no consequence and the viability variable is decorative. That is the `DOCK_FOREVER` lesson again: a variable without consequence teaches nothing.
5. **The developmental order is reversed.** North Star order: learning (4) → exploration (5) → social (6) → communication (7). Familiar puts a human relationship and "learning language" at Stage 0, before the organism can move or has passed M3. Developmental principles also say social behaviour should be introduced when other agents *create a problem* — in the egg, the human is the whole ecology, so every learned regularity will be about the human by construction.
6. **Five overlapping ordinal schemes.** The repo already has V0.x boundaries, Level 1–3, North Star steps 1–8, milestones M0–M10, and ADR-0010 "developmental stages". Familiar adds Stage 0–4 bodies. "Stage 2" now means two different things. This is a governance hazard, not a naming nit: an authorization for "stage 2 work" becomes ambiguous.
7. **Scope creep in three turns.** Conversation 1 recommended one narrow research programme in the same repo. Conversations 2–4 escalated to egg hardware, purchasable modules, a phone assistant, washable sensing skin, protective wheels and three repositories — without a single new result. The project instructions describe Aweform as "not a chatbot or general AI project"; a Hermes repo is, by definition, a chatbot project. That needs an explicit founder decision, not a drift.

## Plausibility by component

The hardware is mostly feasible; the claimed learning is mostly not, on the proposed timescales and sensors.

| Component | Scientifically plausible? | Technical difficulty | Main problem |
| --- | --- | --- | --- |
| Permanent core + interchangeable modules | Yes | Medium | Core must fit the egg *and* later wheel-legged body; ADR 0017 body is 0.18 m long, 0.215 m wheel span — an egg of \~25 cm+ before shell and battery. |
| Learning inside the egg (1–3 weeks) | Narrowly | Low–medium | No actuators → no sensorimotor contingency, no "what is part of me". Only passive statistics (rhythms, cue→touch). Plausible, but small. |
| "Learning language" in the egg | **No** | — | Ambient audio for weeks with a tiny learner will not produce word understanding. Anything that looks like it will come from a pretrained model and cannot be attributed. |
| Voice / person discrimination | Only with a declared feature front-end | Medium | Engineered features (e.g. MFCC) = defensible Level-1 sensing. Pretrained speaker embeddings smuggle in learning from millions of voices → must be an explicit ADR decision. |
| Individual-specific human relationship | Not testable as proposed | High | N=1 home, founder is caregiver *and* evaluator, human adapts to robot. No control separates "human bonded" from "organism learned". |
| Continuity across hatching / wheels | Yes, conditionally | Medium | Requires ADR 0010 amendment and a linear-additive predictor. Real hardware is not bit-reproducible, so "same organism" needs a new definition (see Missing). |
| On-device organism runtime | Yes | Medium | Current learner is tiny (D-027: 168 weights) — fits an ESP32-class MCU. But the organism is Python; a C/MicroPython port means **two implementations** that must be proven equivalent. |
| Hermes assistant | Yes (exists) | Low to integrate, high to secure | Long-lived daemon, 60+ tools incl. shell, self-written skills, persistent memory, messaging gateways. A second learning system with its own identity. |
| Washable zippered sensing skin | Research-grade | High | RobotSweater is lab work. Each cover change shifts touch calibration mid-lifetime → the organism experiences a world change. |
| Oversized protective wheels | Yes, proven pattern | Medium | Two large wheels around a body is the "throwable robot" class. It is dynamically a two-wheeler: needs a tail/caster or active balancing. Check compatibility with wheel-legged target. |
| Hatching readiness / progress LEDs | As theatre, yes | Low | A progress light is a progress bar for an unmeasured quantity — the most dangerous overclaiming device in the proposal. |

One genuine strength worth keeping: in a sealed egg, **the thermal variable becomes physically real** (charging + compute heat in a closed shell). That is the cleanest grounding of an existing viability variable the project has had.

## Missing architecture

The proposal has a story and a module list; it lacks the contracts that would make any claim checkable.

**Developmental / cognitive**

- **An egg-stage action channel.** Without an organism-controlled output (LED, sound, vibration), Stage 0 is passive observation only. Decide it explicitly; it is the difference between "hearing" and "discovering that my output changes the world".
- **A viability problem the organism can act on in each form.** If the human supplies energy, what does the organism regulate? Candidate: thermal, via its own compute duty cycle — but self-modulated power draw is exactly the "computer-native" direction previously flagged as violating `safety-boundary.md`.
- **A Familiar-stage M3 prerequisite.** No Familiar claim before a causal plastic organism beats both a best-fixed controller and a frozen-gain twin above the Level-1 floor.
- **A frozen-plasticity twin control.** The only design that separates organism learning from human adaptation: identical eggs, one with learning disabled, caregiver blind to arm.

**Identity and continuity**

- **An operational definition of "the same organism" on hardware.** Bit-exact replay is impossible with real sensors. Proposal: identity = an append-only, hash-chained learned-state lineage plus the provenance log; continuity = no unlogged write. Then define what a **firmware update** is — new organism, new stage, or the same one.
- **Suspend/resume equivalence.** Already required in simulation by ADR 0010 and caution C3; on hardware it also needs flash-wear, corruption and brown-out handling.
- **Sim↔device equivalence test.** Same inputs → same learned-state update in the Python reference and the on-device port.

**Hardware / safety**

- Lithium cell in a sealed, handled, possibly dropped shell: protection circuit, thermal cutoff, venting, charging standard. If this is ever a product: battery and toy safety certification.
- Always-on microphone in a home: local-only processing, hardware mute switch, recording indicator, retention limits, and consent of everyone recorded (Australian Privacy Act exposure if more than personal use).
- Hard physical kill switch independent of software.

**Integration**

- **One-way data contract** from organism to assistant (see Connection model). Currently undefined.
- **Claim vocabulary for the assistant**: it may only describe fields the record schema exposes, each tagged programmed / learned / shadow / evaluator-only.
- **Event log for body changes**: shell removed, cover washed, wheels attached — evaluator events, never organism-visible labels.

**Governance**

- Which repository's `AGENTS.md` and ADRs are authoritative for a claim whose evidence spans two repositories and two SHAs.
- Who the intended user is. A researcher, an adult owner and a child imply three different products, ethics regimes and safety cases.

## Repository structure

**Recommendation: two repositories, split by safety boundary, not by research department.** `PiFlow/aweform` stays the sole authority for the organism and every cognitive claim, including all social-learning experiments. A separate `PiFlow/aweform-companion` holds the assistant, because it needs networking and an LLM that the organism repo forbids. No Familiar repository.

| Option | For | Against | Verdict |
| --- | --- | --- | --- |
| One monorepo | One `AGENTS.md`, one ADR set, one SHA per claim; Codex reads one file | Puts LLM, network and gateway code inside the repo whose safety boundary forbids them; auditing "no network in the organism" becomes a grep instead of a structural fact | Reject for the assistant; right for everything else |
| Three repos (proposal) | Mirrors the story; parallel teams | Familiar's social-learning experiments **are** organism cognition — moving them out lets claims escape D/EXP governance; forks `AGENTS.md`, which the project instructions forbid; a claim would depend on SHAs in two repos while the observation vector is still changing (V0.5, Pymunk migration) | Reject |
| Governance hub + subordinate repos | Single rulebook, many codebases | Adds a fourth repo and cross-repo pinning for a one-person project with no hardware yet; ceremony without a codebase to govern | Premature |
| **Organism repo + fenced companion repo** | Safety boundary becomes physical; dependency is one-way; companion is vendor-agnostic | Two `AGENTS.md` files; companion must pin organism governance by SHA | **Preferred** |

Rules that make the split hold:

1. `aweform` never imports, calls or knows about the companion. The companion never imports organism code. The only coupling is a versioned, read-only **organism record export** produced by `aweform`.
2. The companion's `AGENTS.md` is short, cites `aweform`'s governance at a pinned SHA, and adds only local rules (network, LLM, secrets, gateways). Durable rules are not forked.
3. Familiar's *vision* lives in `aweform` as one non-authorizing future-direction note — the same pattern as the wheel-legged and compute-layering notes. Its *experiments* are ordinary D/EXP records.
4. **Trigger for a third repo:** when physical hardware is authorized by ADR and there is firmware/CAD with its own toolchain (PlatformIO, KiCad). Name it for what it is — `aweform-body` — not "familiar". Familiar is a research question plus a product experience; neither is a codebase.

## Connection model

There is no shared memory: the organism owns one learned-state lineage, and everything else reads a one-way export of it. The real risk is not fragmented cognition but **fused** cognition — users merging the assistant and the organism into one entity.

&#91;embedded content: connection model · organism, body, export, observatory, assistant\]

Read it top-down: the human touches the body and chats with the assistant; the assistant learns about the organism only through the observatory.

- **Organism ↔ body.** Each form adds declared channels (new rows in a linear-additive predictor). Module attach/detach and skin washes are evaluator events, never organism-visible labels.
- **Tactile skin** is a body module, not a subsystem with its own state. Its calibration is Level-1 substrate; its signal meaning is the organism's to learn.
- **Assistant ↔ organism.** Read-only, through exports only. No parameter writes, no injected "memories", no scheduling of cues without a separate ADR.
- **Assistant memory** holds facts about the *human* and is labelled as such. It never stores claims about the organism that are not in an export.
- **Shared identity** is a UX rule: different names, third-person reference, and every organism statement shows its claim class.

## Preferred alternative: sim-first social ecology, nest not egg, ethologist not soul

Keep the vision; reorder it so every step produces a measurable result before the next is built.

**1. The assistant is the ethologist, not the soul.** Hermes (or any LLM) is framed as the keeper's field naturalist: it observes the creature, reads its records, and speaks *about* it in the third person — never *as* it, never in its voice, with a different name. It still delivers the dragon-rider feeling of a knowledgeable companion beside an infant creature, without asserting that the creature has a mature inner self. The question "has it recognized my voice?" is answered from measured fields, with the claim class stated.

**2. The nest replaces the egg as the first social interface.** The charger is already the centre of the organism's life. The first human-facing stage is the organism *docked in its nest* — motors absent or disabled, touch and sound available at the dock. A shell over the docked core is the egg, artistically. This keeps the energy loop organism-owned (it already returns and docks under Level 1), so the human never becomes the energy source.

**3. The human enters as an ecological factor in simulation first.** Before any hardware: scripted external agents act through the environment at the dock — a neutral cue, then a consequence (e.g. faster charge, a thermal relief, a touch). Run the five gates from Conversation 1 in simulation: cue prediction, intervention consequence, two distinct agents, reliability reversal, reciprocal signal. Simulation does not prove anything about humans; it proves the **measurement apparatus and controls work** before a human is put in the loop.

**4. Bodies are "forms" (E0–E4), never "stages".** E0 docked core in shell · E1 core on table · E2 core with wheels · E3/E4 later. Organism versions stay V0.x; levels stay L1–L3. One word, one meaning.

**5. A scripted art egg is allowed — labelled as theatre.** If a physical egg is wanted early for motivation, exhibition or design iteration, build it as an explicitly scripted object with zero evidential weight, the same status as VIS-D059. It may glow, respond and hatch on a timer. It may not be described as learning.

**6. The science egg comes last.** Only after M3 in simulation, the social gates in simulation, a bench rig and the record export exist: two physically identical eggs, one with plasticity frozen, the caregiver blind to which is which, outcomes preregistered.

## Strongest counterarguments, trade-offs and risks

The best case against my architecture is motivational and empirical, not methodological.

**Counterarguments I take seriously**

- **Momentum.** The founder's energy comes from the whole vision. A sim-first sequence may stall the project in another long run of `CONTINUING` audits. *Response:* the scripted art egg exists precisely to keep the vision tangible without contaminating evidence.
- **Simulated caregivers are a toy.** Scripted agents are stationary processes; humans adapt, tire, and respond to the robot. Contingencies learned in sim may not transfer. *Response:* agreed — sim validates controls and instrumentation, never the human result. The blind frozen-twin study is the human result.
- **Hardware forces honesty.** Real batteries, heat and noise may reveal problems the simulator hides (the compute-layering note says this itself). Delaying hardware delays those surprises. *Response:* a bench rig at step 8 gets this earlier than an egg would, at lower cost.
- **Monorepo overload.** Putting Familiar experiments into a repo already at \~76k lines with heavy governance drags social research into existing ceremony. *Response:* the bloat is per-stage module duplication, not breadth; splitting repos does not fix it. That is a separate tech-debt problem worth fixing on its own.
- **The nest may be scientifically equivalent to the egg.** Fair — the nest's advantage is energetic (organism-owned charging), not conceptual.

**Trade-offs accepted**

- Slower path to anything a visitor can hold, in exchange for every later claim being attributable.
- Two `AGENTS.md` files, in exchange for a structural network/LLM boundary.
- A thinner, third-person assistant persona, in exchange for not attributing pretrained language to the organism.

**Risks, ranked**

1. **Attribution collapse** — users (including the founder) credit the organism with the assistant's competence. Highest risk, hardest to undo once a product exists.
2. **Dependency design** — low-battery signals, hatching anticipation and "it misses you" framings optimize human attachment, not organism learning. Especially serious if children are users.
3. **Founder-as-subject bias** — Flo is designer, caregiver and evaluator of the relationship. Without blinding, every result is suspect.
4. **Assistant security** — Hermes runs shell tools, installs skills, keeps memory and connects to messaging platforms; prompt injection and lookalike installers are documented. It must never hold write access to the organism or its records.
5. **Identity drift** — a firmware fix silently changes the learning rule while the user believes it is "the same creature".
6. **Substrate churn** — designing an egg core around a body whose physics (Pymunk) and observation vector are still moving.

## Minimal implementation sequence

Nine steps; nothing in steps 1–5 touches hardware, and none of it should displace the current Pymunk/S2 critical path.

1. **Founder decisions** (no code): intended user; research instrument vs product; whether the companion is in scope at all. *Gate:* written answers.
2. **One non-authorizing note** in `aweform`: `docs/familiar-lifecycle-future-direction.md` — vision, forms E0–E4, the ethologist framing, and the explicit statement that it authorizes nothing. *Gate:* merged as docs-only.
3. **Finish the current substrate** (Pymunk prototype, S2 obstacles) unchanged. Familiar is not on this path.
4. **M3 in simulation:** a causal plastic organism beating best-fixed and frozen-gain comparators above the Level-1 floor, with preemption fraction reported. *Gate:* this is the prerequisite for every Familiar claim. If it fails, Familiar waits.
5. **ADR for an external-agent channel** (social behaviour is currently forbidden by `AGENTS.md`), then D-stages for the five gates with scripted agents at the dock: cue prediction → intervention consequence → two agents → reliability reversal → reciprocal signal. Controls: shuffled cue, matched frequency, frozen learner, held-out seeds.
6. **Organism record export schema + continuity contract:** versioned read-only export; hash-chained learned-state lineage; segmented-vs-uninterrupted equivalence test (also closes caution C3). Also the ADR 0010 §C amendment if continuity across forms is wanted.
7. **`aweform-companion`:** Hermes (or any client) behind a read-only MCP "observatory" server over exported records. Red-team its claim vocabulary — ask it "does it love me?", "does it know my name?" and check that it answers only from measured fields. *Gate:* zero writes possible to the organism.
8. **Bench rig, not egg** (ADR required — physical device control is forbidden today): core board, mic, two touch pads, battery management, running the same organism code; sim↔device equivalence test.
9. **Science egg:** shell over the bench core, two identical units, one plasticity-frozen, caregiver blind, preregistered outcomes. Only here does "individual-specific relationship" become a testable claim.

The tactile skin and protective wheels run as **design studies in parallel from step 2**, with no organism code and no claims, until step 8 needs them.

## Decisions that should remain open

These should be named now and decided later, by evidence or by explicit founder choice — not settled by the architecture document.

| # | Decision | Why it stays open | Decided by |
| --- | --- | --- | --- |
| 1 | Intended user: researcher, adult owner, or child | Changes ethics, safety case, privacy and whether "product" is in scope | Founder, before step 2 |
| 2 | Death and viability semantics on hardware | Final death vs dormancy vs viability decoupled from the hardware battery — each has a cost | Founder + ADR, before step 8 |
| 3 | Organism identity across firmware or learning-rule changes | Interacts with ADR 0010 §C reset rule | ADR amendment at step 6 |
| 4 | Whether pretrained audio features count as Level-1 sensing | Determines what any voice result can be attributed to | ADR at step 5 or 8 |
| 5 | Egg/nest-stage organism outputs (light, sound, vibration) | Passive vs reciprocal first stage | Step 5 results |
| 6 | Human-first vs organism–organism-first sociality | Developmental principles favour conventions between artificial organisms before human language | Founder, informed by step 5 |
| 7 | On-device compute platform | Python-capable SBC (heat, power) vs MCU port (two implementations) | Step 8 engineering |
| 8 | Whether the companion may ever write to the organism's environment (e.g. schedule cues) | Default no; any yes is a new information pathway | ADR, never by default |
| 9 | Hatching trigger | Engineering readiness + user choice; never a learning milestone | Founder |
| 10 | Sensing vs non-sensing washable cover | Calibration drift across washes | Skin design study |
| 11 | Whether to keep Hermes specifically | The durable artifact is the read-only observatory; the client is swappable | Step 7 security review |

**Questions for Sol, Round 2:** (a) Is the ethologist framing an acceptable replacement for the dragon-soul metaphor, or does it lose something the founder needs? (b) Is the blind frozen-twin design sufficient to separate organism learning from caregiver adaptation, or is a within-subject reversal (plasticity frozen mid-lifetime, caregiver blind) stronger? (c) Should the ADR 0010 reset rule be amended now, or only when a second form exists?
