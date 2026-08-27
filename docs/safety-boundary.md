# Safety and Experimental Boundary

This boundary was written for V0.1 and applies unchanged through V0.2 and V0.3. ADR 0009 opened V0.2 by permitting bounded one-step observation-history state inside a controller. ADR 0010 opens V0.3 by permitting bounded lifetime plastic/learned state whose causal writes obey the sensory/plasticity provenance boundary. Neither ADR changes anything this document allows or forbids.

In particular, V0.3 plasticity means bounded parameter/state adaptation inside the approved simulation. It does **not** authorize code self-modification, code generation/execution by the simulated organism, persistence outside explicitly approved experiment artifacts, networking, external APIs, replication, or physical-device control. ADR 0010 also does not authorize checkpointing or learned-state serialization merely by opening V0.3.

The project is a bounded simulation experiment. The boundary exists for both safety and scientific clarity.

## Allowed

- finite simulated worlds;
- finite simulated episodes/lifetimes;
- simulated energy and resources;
- deterministic/random-seeded experiment generation;
- local simulated sensing;
- bounded simulated actions;
- experiment logging and analysis artifacts;
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

## Scope discipline

The project should not contain hardware-control scaffolding, networking abstractions, self-updating mechanisms, or speculative future autonomy systems.

Any future expansion of these boundaries requires an explicit project decision and should be reviewed in the context of the experiment that needs it.

## Claims boundary

Experimental results may support statements about measured behaviour, viability, adaptation, prediction, or control within the defined environment.

They must not, by themselves, be described as evidence that Aweform is conscious, sentient, emotional, subjectively experiencing, or literally alive.
