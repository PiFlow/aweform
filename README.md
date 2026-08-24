# Aweform

Aweform is an open research project exploring the development of an electronic artificial life-form from homeostasis toward adaptive cognition.

The project does **not** begin with a chatbot, LLM, human-like psychology, or a claim of machine consciousness. It starts with the smallest viable developmental problem: an electronic organism with an inside and an outside, finite energy, limited sensing, simple action, and a need to remain within viable energetic bounds.

Here, **electronic cell** is a developmental analogy for that minimal inside/outside viability problem. V0.1 does not claim to reproduce biological cells or biological metabolism.

## Current stage: V0.2 — Memory-Capable Electronic Cell

V0.2 was opened by [`ADR 0009`](docs/adr/0009-v0.2-bounded-observation-history-state.md). It changes exactly one thing from V0.1: a controller may add bounded one-step observation-history state to its causal action path, within a defined budget and registration rule. The substrate, environment, and observation/action contract are unchanged, and every other V0.1 non-goal still stands.

V0.1 is not closed. EXP-002's confirmatory execution remains specified but unexecuted on untouched seeds `50001–51000`. EXP-000 through EXP-003 were specified and run under V0.1.

The stage remains intentionally minimal. EXP-004 is the first V0.2 experiment. V0.1's first experiment, EXP-000, asked whether access to an organism's own internal energetic state can causally reorganize its behaviour in ways that improve viability.

The active foundation contains no learning model. In particular, neither V0.1 nor V0.2 includes PPO, JEPA, an LLM, camera vision, a learned world model, social behaviour, play, awe, networking, or physical robotics. V0.2's bounded observation history is not learning: nothing is adjusted from experience.

EXP-000 and EXP-001 are completed. EXP-002 calibration is complete, with B50
selected among the tested thresholds for development. EXP-003 localized
charging-station development is beginning. See the
[`research roadmap`](docs/research-roadmap.md) for the chronological ledger.

## Developmental approach

Aweform uses biology and evolution as inspiration for **problems and principles**, not as a literal ladder or neurological blueprint. Capabilities should be introduced only when the organism's developmental environment creates a problem for which that capability is useful.

The long-term direction includes homeostasis, coordinated subsystems, sensorimotor survival, learning, play and curiosity, social interaction, machine-native communication, richer cognition, and eventually physical embodiment.

Read:

- [`docs/north-star.md`](docs/north-star.md) — what Aweform is trying to become
- [`docs/developmental-principles.md`](docs/developmental-principles.md) — evolution-inspired development, play, curiosity, and awe
- [`docs/adr/0001-v0.1-electronic-cell.md`](docs/adr/0001-v0.1-electronic-cell.md) — the V0.1 scope decision
- [`docs/adr/0009-v0.2-bounded-observation-history-state.md`](docs/adr/0009-v0.2-bounded-observation-history-state.md) — the V0.2 scope decision
- [`docs/reproducibility.md`](docs/reproducibility.md) — seed separation and confirmatory-run discipline
- [`docs/safety-boundary.md`](docs/safety-boundary.md) — experimental boundary, written for V0.1 and applying unchanged to V0.2
- [`experiments/EXP-000-interoception-viability.md`](experiments/EXP-000-interoception-viability.md) — first experiment specification

## Scientific humility

Behavioural evidence alone does not establish that Aweform is alive, conscious, emotional, or experiencing anything subjectively. Terms such as "awe", "care", and "curiosity" are used as functional research hypotheses unless stronger evidence ever becomes available.

## Status

Foundation phase. EXP-000 and EXP-001 are completed, EXP-002 calibration is
complete with B50 selected for development, and EXP-003 localized charging
station instrumentation is underway. The project is within the V0.2
electronic-cell stage; no later-stage cognition or physical control is implied.

## License

Apache-2.0.
