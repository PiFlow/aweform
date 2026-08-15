# ADR 0002 — Agent–Environment Information Boundary

**Status:** Accepted

## Context

The simulator may need privileged world truth to generate dynamics and evaluate
experiments. That truth can include absolute position, resource-source
coordinates, the exact resource field, and evaluator telemetry.

## Decision

Controllers may receive only observations explicitly exposed by the experiment
contract. Simulator knowledge must not be treated as an agent observation by
default.

For EXP-000, future agent-visible observations are expected to include internal
energy and limited local environmental sensing. The exact observation contract
will be specified before confirmatory evaluation. This ADR does not implement
that observation API.

## Consequence

Resource-field internals and evaluator telemetry remain simulator-side state.
Later environment and controller code must make any information crossing the
boundary explicit and reviewable.
