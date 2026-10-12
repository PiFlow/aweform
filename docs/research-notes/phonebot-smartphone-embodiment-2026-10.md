# PhoneBot (UCLA, October 2026) — non-authorizing embodiment research note

**Status:** Exploratory research / future interpretation only. **Not a design decision, ADR, implementation task, experiment authorization, roadmap commitment, or evidence claim.**  
**Recorded:** 12 October 2026. **Aweform comparison base:** `48b18209a69d18841166bc8a00b56d00815e3b5b`.  
**Sources:** [Hou et al., *PhoneBot: A Low-Cost Open Humanoid Robot Platform Reusing Smartphones*, arXiv:2610.08737 (preprint, 6 Oct 2026)](https://arxiv.org/abs/2610.08737); [authors' project website](https://phonebot.dev); [independent reporting (not independent experimental replication)](https://bigchange.ai/blog/phonebot-smartphone-humanoid-robot-platform).  
**Source availability caveat:** The project website did not load during this review; a complete official repository, downloadable source/CAD/firmware/asset set, exact licensing, and reproducible build were **not independently verified**. The authors' open-source claim must not be treated as an audited license or ready-to-reuse implementation. An unrelated, older `jgrizou/phonebot` smartphone-driving robot repository is *not* the UCLA humanoid.

## Author-reported PhoneBot system (not independent replication)

- An approximately 48-cm, 1.8-kg, arm-less humanoid using a torso-mounted Android smartphone for camera, IMU, compute, connectivity, and user-facing interaction; 13 low-cost actuators in the articulated lower body / torso.
- A separate embedded actuation/control electronics path is required; a phone is not itself a deterministic low-level motor driver. Precise firmware, motor interface and real-time guarantees remain unaudited here.
- Authors describe physics-simulation-trained walking, sim-to-real deployment, vision-based human following, conversation, filming and telepresence. These are supplied/learned **task policies**, not evidence of an agent inventing its own viability goals.
- Approximately **US$400 excluding smartphone** is an author-reported hardware estimate, *not* a verified complete build cost or cost for Aweform.
- Reported left/right mirrored training addresses gait asymmetry and training distribution; applicability to other bodies/learning rules is an **experimental hypothesis**, not an established transfer result.
- Paper and project make open-source claims; until code/license/files are accessible, reuse is **conceptual/reference only**.

## Aweform baseline and governance

At the comparison base, [`README.md`](../../README.md), [`AGENTS.md`](../../AGENTS.md), [`development/INDEX.md`](../../development/INDEX.md), [ADR 0017](../adr/0017-v0.5-direct-differential-drive-centered-dock-boundary.md), [ADR 0018](../adr/0018-three-layer-developmental-architecture-and-innate-viability-floor.md), and [D-060 archive](d060-incomplete-substrate-retrospective.md) are authoritative over speculative future directions.

- Committed D-lane extends through **D-059**; D-060 interior-obstacle attempt was incomplete/unaccepted. Isolated **Pymunk evaluation** is a candidate exploratory path, not an adopted physics engine.
- Current V0.5 signed bilateral wheel-rotation commands and quantized wheel-delta observations operate in a deterministic differential-drive abstraction. ADR 0019 / D-058 add a 3-m physical-wall *endpoint-only kinematic* contact boundary, not verified real-world contact dynamics.
- The organism's permitted channels include energy/temperature interoception, charging beacon L/F/R, dock-contact feedback, and wheel-delta proprioception. Extra phone camera, inertial, GPS, network, semantic recognizer, and other channels are **not** presently organism-visible permissions.
- Under ADR 0018, the bounded engineered Level-1 energetic return/dock/recovery floor must remain distinct from Level-2/3 learned competence. Learned contributions require matched attribution above the floor.
- No pretrained walking, following, visual recognizer, language agent, reward scheme, scripted task goal, privileged simulator geometry, or outcome label may silently enter the organism via an engineering adapter.

## Ranked *possible* future opportunities (qualitative inference)

| Rank | Concept | Value | Complexity | Fit / limitation |
|---|---|---|---|---|
| 1 | Compare ideal wheel commands with physical actuator limits (response delay, saturation, slip, acceleration, motor energy) | High | Low–medium per isolated effect | Relevant to Pymunk/contact investigation; avoid bundling effects, don't claim PhoneBot code reuse |
| 2 | Separately specify simulated vs physical observation/action adapter, with timestamps, quantization, command/achieved-motion distinction | High | Medium | Strong eventual differential-drive transfer value; **no current physical control authorization** |
| 3 | Reuse an affordable Android phone for *off-organism bench* sensing/compute | Potentially high | Medium | IMU, camera, power and timing need measurement; phone battery/thermal budget complicates Aweform viability bookkeeping |
| 4 | Study mirrored/balanced sensorimotor *experience distribution* as evaluator-side learning comparison | Medium–high | Low–medium | Only with causally legitimate experience and matched controls; augmentation is not equivalent to lived experience |
| 5 | Characterize visual/inertial sensor latency, calibration, drift and missing samples | Medium | Medium | Requires independent sensory-boundary review before organism exposure |
| 6 | Modular articulated chassis / later wheel-leg morphology | Medium/uncertain | High | Humanoid biped is not a direct equivalent of two articulated legs ending in wheels; power, stability and added action dimensions may dominate |
| 7 | Import task-pretrained walking or human-following policies | Low / scientifically conflicting | High | **Do not import as developmental competence**; any purely constitutive stabilizer would require explicit bounded Level-1 architecture review and separate attribution |

Rankings reflect potential scientific or engineering value, **not** authorization, urgency, a promise of superior results, or established PhoneBot–Aweform compatibility.

## Infrastructure versus behaviour boundary

**Potential engineering inspiration:** open mechanical assemblies; phone-camera/IMU APIs; clock synchronization; transport/telemetry; motor firmware protocols; calibration fixtures; actuator saturation/latency models; simulator and physical interface contracts; documented failure modes.

**Not transferable as Aweform-acquired intelligence:** pretrained walking/gait, visual following, speech/chat interaction, curated high-level navigation, reward/goal shaping, privileged pose/heading/dock information, or controller outputs whose origin in pretrained behaviour is obscured. An engineering stabilizer could be considered only by an explicit future ADR with Level-1 definition and matched learned-versus-innate attribution; it must not be described as discovered.

**Physical energy caution:** a separate smartphone battery, processor load, camera duty cycle, radio and thermal throttling all matter to eventual causally grounded energy/interoception. A phone's own power supply cannot silently provide “free” cognition or sensing while measuring only motor battery energy.

## Suggested hypotheses for future *separately authorized* experiments

1. **Motor-model sensitivity:** under paired legal seeds and controllers, does progressively less ideal actuation change docking, viability, and prediction? Measure command/achieved deltas, energy, collisions, terminal outcomes and preemption fraction. Introduce one physical effect at a time.
2. **Experience symmetry:** with learner and opportunity fixed, does balancing left/right action–consequence exposure improve *held-out* predictions versus unmodified experience? Keep mirrored evaluator-generated comparators distinct from organism-lived experience; avoid leaking unavailable states, labels or future outcomes.
3. **Phone bench feasibility:** measure Android IMU/camera timing, drift, dropped frames, transport jitter, idle/sensing/computation energy and thermal behavior **without** attaching the phone to an autonomous organism or changing its sensors.
4. **Later morphologies:** first compare fixed-articulation wheel-leg geometry against current differential drive; only then isolate new joint degrees of freedom, control burden, mass, balance and charging consequences.

Before any of these can become a task: inspect current `development/INDEX.md`, relevant ADRs, and exact authorization; freeze hypothesis and controls, keep evaluator-only data segregated, preserve seed reservations, and seek required independent reviews for any durable information/sensory/body/physics/safety change.

## Non-conclusions and revisit triggers

- Neither walking demonstration nor claimed open sourcing proves PhoneBot's code is available, maintained, licensable, reproducible, suited to wheels, or sim-to-real transferable to Aweform.
- No PhoneBot result demonstrates spontaneous needs, developmental self-maintenance, generalized intelligence, or Aweform's desired learning trajectory.
- Investigate further **only** when: (a) official source/hardware files and license become verifiable; (b) physical embodiment is specifically authorized; or (c) a precise current simulator/learning experiment benefits from one isolated PhoneBot-inspired test.
- **No authorized next action follows from this note.** No changes to `AGENTS.md`, ADRs, `development/INDEX.md`, reserved seeds, source, dependencies, or experiments.
