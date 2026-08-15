# ADR 0005 — EXP-000 Development Runner and Recording

**Status:** Accepted

## Decision

Add a small development/calibration runner for EXP-000. It accepts an explicit
caller-supplied seed sequence and executes conditions A, B, and C in that
order for each seed. Each condition gets an independently constructed
environment reset with the same seed and complete environment configuration,
so matched starts are deterministic without sharing mutable state.

Evaluator telemetry is privileged. It is recorded through an explicit
evaluator-side API and never enters the four-value controller observation or
Gymnasium `info`. Raw trajectories preserve initial evaluator truth and each
executed transition. Threshold-free episode summaries are recorded alongside
them.

Development artifacts include a reproducibility manifest containing the
explicit Git SHA, configurations, seeds, condition identifiers, runtime and
platform information, and UTC start time. JSON artifacts refuse to overwrite
an existing path by default.

This runner does not encode acceptance seeds, a confirmatory execution path,
scientific primary outcomes, critical thresholds, effect criteria, or final
parameter values. Adding confirmatory execution requires an explicit later
protocol-freeze step.
