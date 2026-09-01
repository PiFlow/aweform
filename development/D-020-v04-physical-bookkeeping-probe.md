# D-020 — V0.4 physical bookkeeping and fixed-action probe

- **identifier:** D-020
- **lane:** Development
- **date:** 2026-09-02
- **authoritative_base_sha:** `7c13142dff433e39ca08f99ecbd3198e21d8e57d`
- **implementation_probe_sha:** `e06c01f`
- **final_pr_head_sha:** recorded in the handoff after PR creation
- **disposition:** `CONTINUING`
- **learned mechanism:** none

## Scientific question and historical boundary

D-020 asks whether the accepted V0.4 physical model produces internally coherent,
deterministic, dimensionally consistent bookkeeping for battery energy,
electronics and action-dependent actuator load, charging acceptance/taper/
termination, charging loss/body heat, signed passive exchange, one lumped body
temperature, energy viability, and staged thermal shutdown under fixed actions.

This is an implementation/accounting probe. It does not test regulation,
learning, historical-weight transfer, a thermal controller, realistic robotics,
or whether a thermal challenge exists.

The implementation is additive in `src/aweform/d020.py`. Historical D-002,
D-003, D-011, D-013, D-014, D-018, and EXP-003 source and semantics were not
changed. D-020 does not call `LocalizedChargingStationEnv.step()` and therefore
does not layer physical bookkeeping over historical abstract energy accounting.

The first substantive run from `2e4ab56` was invalidated because its writer
retained every transition row for both long probes, producing an unnecessarily
large 33 MB artifact. No physical parameter or probe definition changed. The
writer was corrected to retain rows only for the short mixed probe; focused
tests passed, and the frozen suite was rerun from `e06c01f`. This invalidated
attempt is preserved rather than hidden.

Artifact command:

```text
uv run python -m aweform.d020 --output development/D-020-v04-physical-bookkeeping-probe.json
```

The command emits a benign `runpy` warning because the package exports D-020
before `-m` executes it. The corrected artifact is 16,568 bytes.

## Exact frozen first-slice parameters

These values were frozen before substantive output was inspected and were
unchanged for the corrected rerun.

| Parameter | Value | Provenance / classification |
|---|---:|---|
| `dt_seconds` | `0.1 s` | DESIGN CHOICE / PROVISIONAL PHYSICALIZATION |
| world scale / movement | `1.0 m/unit` / `0.05 unit` | DESIGN CHOICE; historical movement mapped provisionally |
| turn | `π/4` | Historical action geometry |
| battery capacity / initial | `5328.0 / 2664.0 J` | `3.7 V × 0.500 Ah × 3600 × 0.80`; initial is a design choice |
| electronics electrical / body heat | `0.15 / 0.15 W` | ENGINEERING ESTIMATE; separate causal terms |
| actuator electrical WAIT / MOVE / TURN | `0.0 / 1.0 / 0.65 W` | Action semantics / ENGINEERING ESTIMATE |
| actuator body heat, all actions | `0.0 W` | LOWER-BOUND SENSITIVITY ASSUMPTION / UNKNOWN — NEEDS MEASUREMENT |
| charge efficiency | `0.90` | ENGINEERING ESTIMATE |
| bulk / taper 1 / taper 2 | `1.85 / 0.925 / 0.37 W` | DESIGN CHOICE / first-slice SOC rule |
| SOC bands / restart | `<0.90`, `<0.95`, `<1.0` / `0.98` | DESIGN CHOICE |
| thermal capacitance / conductance | `180.0 J/K` / `0.25 W/K` | ENGINEERING ESTIMATE / D-019 centres |
| ambient / initial temperature | `23.0 / 23.0 °C` | DESIGN CHOICE; ambient evaluator-only |
| preferred / protective / hard | `45.0 / 60.0 / 65.0 °C` | ADR 0014; preferred is non-terminal |
| temperature normalization | `[0.0, 80.0] °C` | ADR 0014 / fixed first-slice bounds |

The existing charging radius (`0.10`), beacon scale (`0.25`), probe distance
(`0.10`), and sensor angle (`π/4`) are also frozen and reused.

## Boundary classification

**PROGRAMMED / PHYSICS:** physical time, provisional world/movement mapping,
one battery scalar in joules, continuous electronics load/heat, action-class
actuator load and separate body heat, the piecewise charger, charging loss, one
absolute lumped body temperature, signed ambient exchange, and staged safety.

**ORGANISM-VISIBLE:** exactly six channels: normalized own energy, existing
beacon left/forward/right, binary charging contact, and normalized current own
body temperature. No absolute joules, SOC, watts, Celsius, ambient, threshold,
charger state, coordinates, or telemetry is exposed.

**EVALUATOR-ONLY:** absolute energy and temperature, geometry, station
coordinates, contact before/after, action loads, heat decomposition, charger
phase/latch, requested/accepted charge, charger input/loss, signed exchange,
threshold diagnostics, viability flags, and termination reason.

**LEARNED:** none. There is no learner, controller, reward shaping, utility,
valence, HOT/DANGER signal, or model-guided action selection. Every transition
returns `reward == 0.0` and organism-facing `info == {}`.

## Equations, causal order, and charger state machine

```text
P_load = P_electronics_electrical + P_actuator_electrical(action)
max_accepted = max(0, capacity - battery_before + P_load × dt)
actual_stored = min(requested_stored_power × dt, max_accepted)
battery_next = clamp(battery_before + actual_stored - P_load × dt, 0, capacity)
charger_input = actual_stored_power / charge_efficiency
charging_body_heat = charger_input - actual_stored_power

P_body_heat = electronics_body_heat + actuator_body_heat(action)
              + charging_body_heat
P_environment = G × (ambient_temperature - body_temperature)
T_next = T_body + dt × (P_body_heat + P_environment) / C_thermal
```

Charging heat is zero when actual stored power is zero; rejected charge cannot
create stored energy or heat. No contact is `OFF` and clears the latch. Contact
selects `BULK`, `TAPER_1`, or `TAPER_2` at the frozen SOC bands. Filling capacity
completes the current transition and latches termination for the next one.
Latched contact is `STANDBY` while pre-transition SOC is `> 0.98`, with zero
stored power and charging heat while electronics continue. At SOC `≤ 0.98`,
charging restarts in that transition. Full re-contact enters standby.

The causal order is current ordinary observation; caller action; movement;
post-action contact; action load; charger state; accepted charge; battery;
body heat; signed exchange; temperature; viability; next ordinary observation.
`T_next >= 65 °C` is emergency shutdown, otherwise `T_next >= 60 °C` is
protective shutdown; `45 °C` is only an evaluator preferred-ceiling diagnostic.
Simultaneous flags are preserved with reason precedence emergency, protective,
then energy depletion.

## Frozen probes and seed status

All probes are seedless fixed-state evaluator probes. No reset RNG affects the
state, no development seed was used, and no formal reservation was created.

`DOCKED_WAIT_CHARGE`: body/station `(0.5, 0.5)`, heading `0`, battery `2664 J`,
temperature `23 °C`, `WAIT`, maximum `30,000` transitions.

`OFF_DOCK_MOVE_ENERGY`: body `(0.1, 0.1)`, station `(0.9, 0.9)`, heading `0`,
battery `2664 J`, temperature `23 °C`, repeated `MOVE_FORWARD` until
termination or `30,000` transitions. Boundary-clamped MOVE continues to incur
the fixed action-class load; this is a declared limitation, not wheel mechanics.

`MIXED_ACTION_CAUSAL_ACCOUNTING`: body `(0.26, 0.5)`, station `(0.5, 0.5)`,
heading `0`, battery `2664 J`, temperature `23 °C`, sequence:

```text
WAIT, TURN_LEFT, TURN_RIGHT, MOVE_FORWARD, MOVE_FORWARD, MOVE_FORWARD,
WAIT, MOVE_FORWARD, MOVE_FORWARD, MOVE_FORWARD, MOVE_FORWARD
```

The compact JSON table records contact entry at step 6 and exit at step 11.

## Substantive results

### DOCKED_WAIT_CHARGE

`30,000` transitions / `3,000.0 s`, no termination. Battery:
`2664.0 → 5299.214999999372 J` (maximum `5328.0 J`). Temperature:
`23.0 → 23.775429720091857 °C` (maximum `24.172935197773615 °C`). `45 °C`
was not reached; neither thermal shutdown occurred. Phase counts were
`BULK 12,537`, `TAPER_1 3,437`, `TAPER_2 12,107`, `STANDBY 1,919`, `OFF 0`.
Full latch was first set at step `28,081`; standby began at `28,082`.
Actual/requested stored energy was `3085.2150000018814 / 3085.2265 J`, with
one headroom-limited event. Charger input was `3428.0166666687574 J`, charging
loss/body heat `342.8016666668759 J`, electronics electrical/body heat
`450.0 / 450.0 J`, actuator electrical `0.0 J`, and signed exchange
`-653.2243170503959 J`. Charging heat was zero after standby.

### OFF_DOCK_MOVE_ENERGY

`23,166` transitions / `2316.6 s`, terminated by `ENERGY_DEPLETION`. Battery:
`2664.0 → 0.0 J`. Electronics energy was `347.49 J`; actuator electrical
energy was `2316.6 J`, matching the `1.15 W × 0.1 s` ledger until the final
clamp. Temperature was `23.0 → 23.57597232725832 °C`; no threshold was reached
and no charging occurred. All phases were `OFF`; `23,148` transitions were
boundary-clamped.

### MIXED_ACTION_CAUSAL_ACCOUNTING

`11` transitions / `1.1 s`, no termination. Battery:
`2664.0 → 2663.9300000000017 J`. There were six `OFF` and five `BULK`
transitions. Step 6 entered contact and charged immediately at `1.85 W`; step
11 left contact and had `OFF`, zero accepted charge, and zero charging heat.
Actuator electrical energy was `0.83 J`; accepted/requested stored energy was
`0.925 / 0.925 J`. Temperature ended at `23.001486780144614 °C`.

## Validation, interpretation, and disposition

Focused `tests/test_d020.py` covers the freeze, validation, analytic
WAIT/MOVE/TURN accounting, separate test-only actuator heat, contact causality,
all charge phases, headroom/standby/restart/contact loss, signed exchange,
normalization, 45/60/65 semantics, simultaneous flags, observation/info
closure, telemetry separation, terminal observation, and determinism. It
passed `34` tests before `e06c01f`; the corrected rerun used the same frozen
parameters and probes. Full validation and CI are reported in the handoff.

D-020 supports the descriptive conclusion that the declared equations, units,
causal order, charger state machine, threshold classification, observation
closure, and deterministic fixed-action traces are internally coherent at this
abstraction level. It does not establish hardware truth, measured actuator
heat, certification, a thermal challenge, need for a controller, learning,
transfer, metabolism, consciousness, emotion, subjective experience, genuine
life, or general intelligence.

The null finding is retained: fixed WAIT and MOVE remain far below `45 °C`.
The boundary-clamped off-dock segment is not realistic wheel/motor mechanics;
the charger is not an electrochemical model; and actuator body coupling remains
unmeasured. No physical parameter or probe definition changed after substantive
results were first inspected. Disposition is **CONTINUING**, with no
confirmatory claim.
