# D-003 — Fixed non-learning thermostatic shuttle

- **id:** D-003
- **date:** 2026-08-28
- **exact_sha:** `PENDING` — no substantive D-003 execution yet
- **development_seeds:** `18141, 18142, 18143`
- **disposition:** `CONTINUING`
- **horizon:** `1000`

## Question

After genuine charging contact has already been established, can a minimal
fixed non-learning feedback controller using only thermal interoception,
charging contact, and tiny own-action phase state repeatedly regulate the D-002
energy/thermal ecology to the existing 1000-transition development horizon?

This is a post-acquisition development probe. It does not ask whether the
controller can discover the charger, whether thermal interoception is
necessary, or whether learning is necessary. It makes no confirmatory claim.

## Predeclared controller

The controller is a deterministic `ThermostaticShuttleController` with no RNG,
learner, reward, adaptation, or tunable behaviour. Its fixed constants are:

```text
hot_depart_threshold = 0.60
cool_return_threshold = 0.30
return_half_turn_steps = 4
```

These thresholds apply to the normalized authorized thermal interoceptive
channel and are frozen before substantive behavioural execution.

The controller-visible observation is structurally limited to:

```text
thermal_interoception
charging_contact
```

plus bounded phase/counter state derived only from its own actions within the
current lifetime. It must not receive energy, beacon values, coordinates,
station coordinates, true distance, heading, seed, step index, remaining
lifetime, thermal evaluator telemetry, or success/failure labels.

The evaluator and harness may observe privileged fields for measurement and
setup, but those fields are outside the controller input boundary.

## Scope and setup

D-003 consumes the existing `D002ThermalStationEnv` unchanged. It adds no
sensor, thermal mechanism, actuator heat, distance cooling, charging throttle,
lower thermal boundary, environment noise, reward, or learning.

For each legal development seed, the harness performs a normal D-002 reset,
then evaluator-side places both body and station centre at `(0.5, 0.5)` before
the first controller decision. The seeded body heading from reset is
preserved. Initial energy and thermal state remain D-002's `5.0` and `0.20`.

The existing 1000-transition horizon is used exactly.

## Measurement declaration

The evaluator will report seed, transitions, termination/truncation causes,
energy and thermal ranges/finals, completed shuttle cycles, charging-contact
and off-contact transitions, and controller-mode occupancy or entry counts.

A completed shuttle cycle means a return to `CHARGE` after completing
`DEPART → COOL → TURN_RETURN → RETURN`. Cycle count is evaluator telemetry and
is never exposed to the controller.

This record is a pre-execution declaration. Results, the exact executed
implementation SHA, and direct observations will be added after the clean
Commit-B probe.
