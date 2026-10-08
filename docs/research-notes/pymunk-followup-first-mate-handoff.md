# Pymunk follow-up handoff (issue #220)

**Status:** coordination/handoff only; no experiment executed or new physical substrate authorized by this document.

**Task:** [Issue #220](https://github.com/PiFlow/aweform/issues/220), following [issue #217](https://github.com/PiFlow/aweform/issues/217) and [PR #219](https://github.com/PiFlow/aweform/pull/219).

## Initial decision

Preserve PR #219 as the immutable failed Tranche 1 calibration record. Its originally frozen acceptance outcomes remain FAIL for free-space calibration, known vectors, and symmetry; the post-result explanation does not turn any of them into PASS. Do not modify the frozen protocol, tests that produced the original result, or original artifacts to manufacture a passing result.

The next diagnostic is a **separate, newly frozen empty-space experiment**, not a migration recommendation. Work starts only after confirming PR #219's state, exact head and the base containing its preserved record. If not yet merged, stop and reconcile the provenance rather than silently testing against an unrelated base.

## Required follow-up

1. Fix the *new* symmetry oracle: exchanging wheel commands reverses yaw and mirrors the displacement laterally in the initial body frame; it does not preserve the Cartesian displacement of a curved arc.
2. Make new known-vector gate independent of overall free-space calibration so independent passing vectors remain visible when other cases fail.
3. Retain historic expected-failure tests with regression assertions of the preserved result and explicit test counts; green pytest does not mean historic calibration passed. New frozen acceptance failures must be reported as failures.
4. Under a new pre-execution protocol and separate results, compare minimal declared twist-update/integration candidates with the unchanged Tranche 1 implementation, using an independent analytical arc reference, with action and timing tests, symmetries, microstep convergence and deterministic repeatability.
5. Report strict mypy outcomes for experimental code separately from production-source checks, plus runtime and artifact identity.

## Execution and authority

First Mate (GPT-6.1 Sol) coordinates Second Mate (Opus 5.5, Claude Code), which delegates worker execution to GPT-6 Luna. Record actual model identities and honor AGENTS.md, ADRs and evidence governance. This handoff PR itself is not independent review of an implementation and does not substitute for any required exact-head approvals.

**Not authorized:** organism, controller, energy, docking, wall or collision integration; D-series or EXP-series work; backend migration; edits to durable boundaries; claims of hardware fidelity or Pymunk collision benefits; merging a successor implementation without Flo's authorization.

**Deliverable:** a separate implementation/results PR linked to issue #220 with frozen protocol SHA, exact tested executable SHA, unchanged original record, individual cases and gate outcomes, reproducible runtime and commands, and a recommendation to stop, revise, or request authorization for a later contact tranche.
