# D-002 — Minimal thermal ecology

- **id:** D-002
- **date:** 2026-08-27
- **exact_sha:** `328a8471d39aaca923f3217b0513f871b9633255`
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

## Execution

The substantive probe was executed from the clean implementation commit
`328a8471d39aaca923f3217b0513f871b9633255` on development seeds `18141`,
`18142`, and `18143`. No formal, calibration, confirmatory, acceptance, or
otherwise reserved seed was used.

The executed constants were exactly:

```text
ambient_thermal_state = 0.0
initial_thermal_state = 0.20
upper_thermal_failure_boundary = 1.0
charging_heat_per_offered_energy = 0.04
passive_cooling_per_transition = 0.01
```

The physical alternating-schedule witness was the following evaluator-side
open-loop action sequence, repeated from body/station centre with initial
heading zero:

```text
WAIT x3
MOVE_FORWARD x4
TURN_LEFT x4
WAIT x3
MOVE_FORWARD x4
```

It uses actual EXP-003 movement, turning, post-action contact, charging
radius, offered input, basal cost, and action costs. It does not teleport
during the schedule or use organism feedback.

## Observed

Direct observations from the machine-readable probe were identical across all
three development seeds:

- Permanent dock with constant `WAIT`: 80 transitions, thermal termination,
  final energy `10.0`, final thermal state `1.0`, and no truncation.
- Permanent off-dock with constant `WAIT`: 51 transitions, energetic
  termination, final energy `0.0`, final thermal state `0.0`, and no thermal
  termination.
- Alternating physical witness: all 1000 transitions, no energy or thermal
  termination, horizon truncation, minimum energy `4.7200000000000095`, final
  energy `9.240000000000004`, maximum thermal state `0.23999999999999994`, and
  final thermal state `0.01999999999999997`. The schedule recorded 389
  post-action contact transitions per seed.

The complete JSON emitted by `uv run python -m aweform.d002` is the execution
artifact returned with this development result.

## Surprised by

The suggested 18-action schedule was physically valid without adjustment and
remained viable for the full 1000-transition horizon. Its thermal state
settled near ambient rather than approaching the upper boundary. The docked
probe also reached thermal failure at a stable, interpretable point while the
energy store was already full, demonstrating that offered-input heating does
not disappear at the battery clip.

## Provisional reading

**Direct observations:** The implementation produces a genuine competing
viability ecology under the declared constants: continuous contact is
thermally non-viable, continuous non-contact is energetically non-viable, and
at least one physically realizable alternating schedule is viable over the
tested development horizon.

**Arithmetic/mechanical inference:** With contact net energy positive before
clipping for `WAIT` and with the witness's repeated contact/off-contact
geometry, the observed energy trajectory is consistent with the unchanged
EXP-003 energy update plus the actual schedule costs. The thermal trajectory is
consistent with the deterministic leaky offered-input integral and its
clamping rule.

**Hypothesis:** The smallest authorized second viability pressure is sufficient
to create a regulation problem worth examining in D-003. This does not show
that learning is necessary, does not establish organism competence, and is not
confirmatory evidence. Because thermal state is a deterministic leaky integral
of contact history, a later controller using thermal interoception would show
sufficiency for that tested mechanism, not automatically necessity.

## Next

Retain these constants and use D-003, if authorized, to examine a simple
fixed/non-learning regulation mechanism. Do not interpret this D-002 probe as
controller evaluation or as evidence for an EXP protocol.
