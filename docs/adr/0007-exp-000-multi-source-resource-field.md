# ADR 0007 — EXP-000 Multi-Source Resource Field

**Status:** Accepted for development

## Decision

The EXP-000 development environment may contain a configurable positive number
of static renewable resource sources. The default remains `resource_count=1`.
All sources share the configured peak intensity and length scale. At each
position, local intensity is the maximum contribution from any source, not the
sum. This keeps intensity bounded on the existing scale while allowing
overlapping resource patches.

Source positions are generated deterministically from the explicit environment
seed and are matched across A/B/C. Changing resource count does not change the
initial body position, heading, or energy for the same seed, and the first
resource source remains stable across resource-count changes. Source coordinates
remain privileged evaluator state; controllers continue to receive only the
same four-value observation.

`resource_count` remains an unfrozen development/calibration parameter. This
slice introduces no depletion, resource competition, heterogeneous resource
types, or ecological dynamics.
