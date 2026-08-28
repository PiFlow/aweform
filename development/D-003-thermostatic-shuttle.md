# D-003 — Fixed non-learning thermostatic shuttle

- **id:** D-003
- **date:** 2026-08-28
- **exact_sha:** `34310d2c3f4198aadd74d030b610142d23d99e24`
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

## Executed result

The substantive probe was run exactly once from the clean executable Commit B
`34310d2c3f4198aadd74d030b610142d23d99e24`, using only development seeds
`18141`, `18142`, and `18143` at the fixed 1000-transition horizon. No
reserved/formal seed was executed.

### Direct observations

All three seeds reached the 1000-transition horizon without energy or thermal
termination and therefore ended by truncation. Each completed 13 shuttle
cycles under the declared cycle definition.

| Seed | Min/final energy | Max/final thermal state | Charging/off-contact transitions | Cycles |
|---|---:|---:|---:|---:|
| 18141 | `5.0 / 9.52000000000002` | `0.6300000000000002 / 0.33999999999999997` | `507 / 493` | 13 |
| 18142 | `5.0 / 10.0` | `0.6200000000000002 / 0.6000000000000002` | `520 / 480` | 13 |
| 18143 | `5.0 / 9.52000000000002` | `0.6300000000000002 / 0.33999999999999997` | `507 / 493` | 13 |

The minimum thermal state was `0.20000000298023224` for every seed. Maximum
energy was `10.0` for every seed. Mode entry counts were `CHARGE: 14`,
`DEPART: 13`, `COOL: 13`, `TURN_RETURN: 13`, and `RETURN: 13` for every seed.

The evaluator positioned body and station centre at `(0.5, 0.5)` and preserved
the seeded reset heading. The observed seeded headings were approximately
`6.2517569980776315`, `0.376285001824293`, and `5.593233811248814` for the
three seeds respectively. These headings were evaluator-only and never
entered the controller observation.

### Mechanical/arithmetic inference

The result is consistent with the existing D-002 ecology: charging contact
raises thermal state through offered station input, off-contact allows passive
cooling, and the fixed four-turn half-turn plus the current movement geometry
returns the body to contact. The small seed-dependent differences in contact
duty cycle and final state are consistent with different preserved initial
headings; no stochastic controller behaviour is present.

### Hypothesis

Under the fixed D-002 ecology and this evaluator-side post-contact setup, a
very small fixed non-learning feedback mechanism using thermal interoception,
charging contact, and bounded own-action phase state is sufficient to sustain
repeated regulation through the tested development horizon.

This remains descriptive development work. It does not show that learning is
unnecessary in general, that thermal interoception is necessary, that the
controller can acquire the station, or that the result applies to arbitrary
environments. D-002 already showed that an open-loop evaluator-side schedule
can survive, so this result demonstrates fixed-feedback sufficiency rather
than thermal-signal necessity.

### Surprises and disposition

No implementation surprise or failure occurred. The controller reached 13
cycles on every legal seed despite preserving different seeded headings. Seed
`18142` ended at a hotter phase (`0.6000000000000002`) while still surviving
the full horizon, illustrating phase alignment rather than a changed ecology.

**Disposition:** `CONTINUING`.
