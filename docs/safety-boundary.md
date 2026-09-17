# Safety and Experimental Boundary

This boundary was written for V0.1 and applies unchanged through V0.2, V0.3, and V0.4.

- ADR 0009 opened V0.2 by permitting bounded one-step observation-history state inside a controller.
- ADR 0010 opened V0.3 by permitting bounded lifetime plastic/learned state whose causal writes obey the sensory/plasticity provenance boundary.
- ADR 0012 opened V0.4 by permitting a bounded physically grounded simulator energy/thermal model.
- ADR 0014 defines the accepted V0.4 thermal operating/failure thresholds.
- ADR 0015 defines the accepted V0.4 finite-body dual-contact docking boundary.

None of those ADRs changes anything this document allows or forbids.

In particular, V0.3 plasticity means bounded parameter/state adaptation inside the approved simulation, and V0.4 physicalization remains simulator physics only. Neither authorizes code self-modification, code generation/execution by the simulated organism, persistence outside explicitly approved experiment artifacts, networking, external APIs, replication, or physical-device control. ADR 0010 also does not authorize checkpointing or learned-state serialization merely by opening V0.3.

The project is a bounded simulation experiment. The boundary exists for both safety and scientific clarity.

## Allowed

- finite simulated worlds;
- finite simulated episodes/lifetimes;
- simulated energy and resources;
- deterministic/random-seeded experiment generation;
- local simulated sensing;
- bounded simulated actions;
- experiment logging and analysis artifacts;
- evaluator-only diagnostics and matched counterfactual branches that are causally isolated from the organism;
- evaluator-only synthetic candidate-sensor calculations used to test sensory sufficiency before any organism-facing sensory-boundary change;
- offline development tools required to build and test the simulator.

## Not allowed for the simulated organism

- network access;
- external APIs;
- process spawning;
- self-modification;
- code generation or code execution;
- replication;
- persistence outside explicitly approved experiment artifacts;
- control of physical devices;
- real-world resource acquisition;
- access to secrets or user data;
- background autonomous daemon behaviour.

## Evaluator-only work is not organism permission

The evaluator may use hidden simulator truth for physics, metrics, debugging, causal branches, or candidate-sensor sufficiency audits. This can include position, heading, geometry, contact truth, station-relative quantities, and synthetic measurements derived from physical simulated geometry.

That access does **not** authorize the organism to receive those values.

In particular:

- a successful evaluator-only counterfactual does not add an action;
- a useful privileged readout does not add a sensor or memory variable;
- a synthetic candidate receptor used in an audit does not become an organism-visible receptor;
- a shadow learner/readout does not become causal merely because it predicts something useful;
- evaluator labels, treatment identity, future branch outcomes, and success/failure labels must not feed back into organism control or plastic updates.

Any change that exposes new information to Aweform, changes the durable sensory/plasticity or information boundary, or makes a previously evaluator-only mechanism causal requires separate authorization under `AGENTS.md` and the relevant ADR/review process.

## Scope discipline

The project should not contain hardware-control scaffolding, networking abstractions, self-updating mechanisms, or speculative future autonomy systems merely because later physical embodiment is a long-term goal.

Any future expansion of these boundaries requires an explicit project decision and should be reviewed in the context of the experiment that needs it.

## Claims boundary

Experimental results may support statements about measured behaviour, viability, adaptation, prediction, sensing sufficiency, or control within the defined environment.

They must not, by themselves, be described as evidence that Aweform is conscious, sentient, emotional, subjectively experiencing, or literally alive.
