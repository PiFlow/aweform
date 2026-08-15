# ADR 0004 — EXP-000 Transparent Controller Contract

**Status:** Accepted

## Decision

- Condition A uses deterministic persistent exploration: a configurable number
  of `MOVE_FORWARD` actions followed by one `TURN_LEFT`, repeated.
- Conditions B and C use the same transparent homeostatic decision mechanism.
  It uses hysteresis to switch between `EXPLORE` and `SEEK_RESOURCE`.
- `EXPLORE` uses the same persistent pattern as Condition A.
- `SEEK_RESOURCE` uses only the local left, forward, and right resource
  signals. Forward wins ties for the strongest signal.
- B receives actual normalized energy from the four-value observation.
- C substitutes an explicitly configured fixed, non-informative normalized
  energy signal for mode switching.
- Controllers receive no privileged simulator state, including body position,
  heading, resource coordinates, or evaluator telemetry.
- These controllers are programmed controllers, not learned controllers.

Threshold values, persistent cadence, and the exact fixed masked-energy value
remain development parameters until the confirmatory EXP-000 protocol is
frozen. Changing to shuffled, delayed, or noisy masking would be a distinct
experimental condition and must not silently replace the fixed-mask condition.
