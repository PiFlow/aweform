# ADR 0006 — EXP-000 Development Visualization

**Status:** Accepted

The EXP-000 visualizer is an evaluator-side development and debugging tool
only. It consumes in-memory development runner results and displays privileged
trajectory telemetry, including positions, heading, and resource-source
location, that is not available to controllers. Artifact replay is deliberately
deferred to keep this first visualizer slice small.

The canonical human-facing view is one selected seed with matched A/B/C panels
for persistent exploration, homeostatic, and energy-blind conditions. The
visualizer does not modify the environment, controller observations, actions,
reward, or seed semantics.

The evaluator-side visualizer may display controller-visible resource signals,
the recorded chosen action, and the actual versus masked mode-energy input.
Privileged evaluator position and resource information remains visually
distinct from those controller-visible diagnostics. This display does not alter
controller observations, recompute actions, or constitute scientific evidence
by itself.

No confirmatory execution, scientific interpretation, statistical analysis, or
outcome definition is added. Visual appearance is for inspection and
debugging, not proof of a scientific claim.
