# ADR 0008 — EXP-003 Localized Charging Interface

**Status:** Accepted for EXP-003 development foundation

## Context

The earlier field environment couples local resource sensing with energetic
uptake through a broad resource field. EXP-003 needs a more physical ecological
problem: a body should be able to sense evidence of a station without receiving
energy until it actually occupies the charging zone.

## Decision

EXP-003 decouples beacon sensing from energy acquisition.

- The station is one stationary circular charging zone per episode.
- Energy is acquired only when the body's actual centre is inside the zone;
  beacon strength alone never grants energy.
- The controller receives left, forward, and right idealized IR-like beacon
  values from virtual directional probes.
- `charging_contact` is controller-visible and is true exactly when the body
  occupies the physical charging zone.
- Station coordinates, true distance, heading-to-station, coverage, and other
  ground truth remain evaluator-only.
- The initial beacon is deterministic, monotonic, noiseless, unoccluded, and
  has no finite cutoff. It is an idealized signal abstraction, not an accurate
  physical IR radiometry model.
- A future physical mapping may use three simple directional IR receivers and
  an electrical/contact charging detector.
- Bluetooth RSSI, camera/vision, SLAM, coordinates, and mapping are not
  required for this initial interface.

## Rationale

This boundary creates the distinction `sensing a resource != consuming a
resource` with a controller contract that is small enough to inspect. It
introduces a real docking problem before adding memory: beacon readings can
guide steering, but only physical occupancy changes energy. A contact/current
sensor is a plausible causal hardware analogue without granting privileged
navigation state.

## Consequences and trade-offs

The interface is easier to reason about and more readily mapped to simple
hardware than a coordinate- or camera-based navigation API. It also makes
SEEK failures diagnostically meaningful: a controller can detect a signal yet
fail to acquire the charger. The idealized beacon is intentionally less
physically realistic than radiometric IR, so later hardware work must validate
the mapping rather than treating simulation performance as hardware evidence.
The current station is static, noiseless, unoccluded, and non-depleting; those
simplifications defer ecological change and genuine partial observability to
later experiments. Charging radius, beacon scale, and charge rate are
development values, not calibrated optima.
