# D-002 — Minimal thermal ecology

- **id:** D-002
- **date:** 2026-08-27
- **exact_sha:** `PENDING — no substantive D-002 execution yet`
- **development_seeds:** `18141, 18142, 18143`
- **disposition:** `CONTINUING`

## Question

Does adding the smallest authorized second viability pressure create a genuine
energy/thermal regulation ecology?

This is development-only descriptive work. It does not ask whether learning is
necessary and makes no confirmatory claim.

## Pre-run parameterization

The following constants were chosen before behavioural observation. They are
initial development constants, not calibrated scientific values, and must not
be changed because a controller or policy performs well or poorly.

```text
ambient_thermal_state = 0.0
initial_thermal_state = 0.20
upper_thermal_failure_boundary = 1.0
charging_heat_per_offered_energy = 0.04
passive_cooling_per_transition = 0.01
```

For each transition, the existing EXP-003 post-action offered charging input
is used exactly as the thermal input source:

```text
thermal_raw = (
    thermal_before
    + charging_heat_per_offered_energy * offered_station_input
    - passive_cooling_per_transition
)
thermal_after = clamp(
    thermal_raw, ambient_thermal_state, upper_thermal_failure_boundary
)
thermal_failure = thermal_raw >= upper_thermal_failure_boundary
thermal_signal = (
    thermal_after - ambient_thermal_state
) / (upper_thermal_failure_boundary - ambient_thermal_state)
```

With the EXP-003 offered station input of `0.5` on genuine post-action
charging contact, contact changes thermal state by `+0.01` per transition
(`0.04 * 0.5 - 0.01`). Off-contact changes it by `-0.01` per transition until
ambient is reached. There is no lower-temperature failure.

The causal sequence is:

```text
action
→ physical movement/turn
→ post-action charging contact
→ EXP-003 offered charging input
→ unchanged EXP-003 energy update
→ D-002 thermal input + passive cooling
→ energy and thermal viability evaluation
→ next six-channel observation
```

## Coherence requirements declared before execution

1. Permanent charging contact must eventually fail thermally.
2. Permanent non-contact must eventually fail energetically.
3. At least one physically realizable alternating contact/off-contact schedule
   must be viable in principle.

The third condition requires an evaluator-side physical simulation sanity
check including actual EXP-003 movement, turn, basal, action, charging-radius,
post-action-contact, and offered-input mechanics. A duty-cycle calculation
alone is not sufficient.

## Scope boundary

D-002 is additive and development-only. It wraps the existing
`LocalizedChargingStationEnv`, adds one thermal state and one normalized
organism-visible thermal channel, and preserves EXP-003 energy dynamics and
the historical five-channel environment. It adds no learner, plasticity,
reward, controller, new evidence protocol, seed reservation, or future-stage
capability. Evaluator-only thermal transition telemetry remains outside the
organism observation.
