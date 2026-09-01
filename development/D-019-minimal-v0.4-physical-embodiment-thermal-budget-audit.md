# D-019 — Minimal V0.4 physical embodiment and thermal-budget audit

- **id:** D-019
- **date:** 2026-09-01
- **authoritative_base_sha:** `38782b7ce7d22d079d793d9662c64ed1a5601131`
- **lane:** Development / research / evaluator-only
- **disposition:** `CONTINUING`
- **implementation status:** No V0.4 implementation was made

## 1. Scientific question

Given a small approximately 122 mm circular differential-drive body, what is
the smallest physically defensible one-body energy and thermal model that could
plausibly map onto a future physical Aweform robot?

This audit evaluates physical scale, timing, power, energy, thermal capacity,
cooling, and upper-temperature choices. It does not claim that the reference
hardware is the final robot, or that a later model will behave exactly as these
estimates suggest.

## 2. Scope and non-scope

This is a research and evaluator-only step. It did not run D-014, tune any
controller, or change current behavior.

It did not modify the learner, controller, environment dynamics, thermal
dynamics, energy dynamics, action set, observations, or visualizer. It did not
add V0.4 code, a sensor, a wheel encoder, an actuator heat path, an ambient
observation, or ADR 0012.

The numerical scenarios below are engineering-budget comparisons, not
behavioral results and not evidence that any controller can regulate a future
world.

## 3. Existing historical boundary

The current historical model must remain unchanged:

- D-002 has one normalized thermal state, charging-generated heat driven by
  offered post-action station input, fixed passive cooling, and no actuator
  heat.
- D-003 demonstrates fixed thermostatic-shuttle sufficiency after evaluator
  post-contact setup; it is not a target for physical parameter tuning.
- D-011 through D-018 retain the same historical D-002/EXP-003 physical and
  observation semantics.
- ADR 0011 authorized the narrow D-002 thermal slice, including its artificial
  offered-input heat simplification. It did not authorize physical V0.4
  energy accounting, motor heat, charger topology, or ambient physics.

The reference implementation still uses `0.05` simulator units per
`MOVE_FORWARD`, `0.1` abstract energy units per movement action, `0.02` per
turn, and `0.1` basal cost per transition. These are historical constants, not
physical parameters, and were not changed here.

## 4. V0.4 design intentions supplied by Flow

These are intentions to investigate, not permissions to implement:

- Use the DFRobot miniQ 2WD platform as a scale/form-factor reference, not as
  a final hardware commitment.
- Keep a candidate control/simulation step of 0.1 s unless concrete evidence
  defeats it.
- Treat one simulator unit as approximately one metre and retain
  `MOVE_FORWARD = 0.05` for now, while allowing smaller increments in a later
  obstacle-rich ecology.
- Use 23 °C as a modifiable evaluator-side ambient default, never as an
  organism observation.
- Prefer one lumped body thermal state.
- Derive electrical energy use and heat from the same action/charging power
  event where practical.
- Do not introduce wheel, encoder, RPM, slip, or motor-current observations.
- Preserve the minimal organism-visible boundary: normalized own energy,
  normalized own body temperature, and existing beacon/contact signals only.

## 5. Research sources and source quality

The primary sources used were manufacturer pages/datasheets and government
technical references. The source links are also collected in section 26.

Important source limitations are retained explicitly:

- The DFRobot reference page says `50:1` and `260 rpm @ 6 V`, but its shipping
  list says the supplied motors are `75:1`. This is an unresolved first-party
  inconsistency, not a value silently selected for convenience.
- The DFRobot page gives no loaded motor current, torque-speed curve, exact
  chassis mass, or thermal information.
- Datasheet current and efficiency values are reference-device measurements,
  not measurements of a future Aweform assembly.
- Thermal conductance, effective thermal capacitance, loaded current, and the
  fraction of actuator heat coupled into the lumped body remain estimates that
  must eventually be measured.

## 6. Hardware reference table

| Item | First-party/reference fact | Interpretation |
|---|---|---|
| Chassis | 122 mm diameter; 15 mm ground clearance; 42 mm wheel diameter | Direct manufacturer reference |
| Motor page specification | 13,000 rpm no-load; 50:1; 260 rpm @ 6 V; 40 mA @ 6 V; 360 mA stall @ 6 V; 10 oz-in torque @ 6 V | Direct manufacturer reference; the page does not explicitly label 40 mA as no-load current and provides no loaded-current curve, so it is not treated as normal loaded operating current |
| Shipping list | Micro Metal Gear Motor with Connector `(75:1) x2` | Direct manufacturer reference conflicting with the preceding 50:1 specification |
| Separate DFRobot 50:1 motor page | 1–6 V operating range; 440 rpm @ 6 V; 30 mA rated; 350 mA stall; 0.39 kg·cm stall torque; 15 g | Useful related reference, but not proof that it is the exact motor shipped with ROB0049 |
| Complete miniQ kit | 350 g; 4.5–6 V supply; 109 × 122 mm | Manufacturer reference for a complete kit, not the bare ROB0049 chassis mass |
| Battery reference | 1S LiPo examples are 3.7 V nominal, 500 mAh / 1.9 Wh at 10.5 g, or 850 mAh at less than 20 g | Plausible battery scale; exact final pack remains open |

The bare chassis mass is **UNKNOWN / NEEDS MEASUREMENT**. A defensible early
finished-robot estimate is 125–270 g for a light shell and electronics build,
with 350 g retained as a manufacturer-referenced complete-kit comparison. This
range is an engineering estimate, not a DFRobot specification.

## 7. Physical time and world-scale analysis

### 7.1 Wheel and speed calculations

Using the DFRobot page's 42 mm wheel and 260 rpm value:

```text
wheel circumference = π × 0.042 m
                   = 0.13195 m/revolution

linear speed = 0.13195 m/rev × 260 rev/min ÷ 60 s/min
             = 0.5718 m/s

distance in 0.1 s = 0.5718 m/s × 0.1 s
                  = 0.0572 m = 5.72 cm
```

Therefore `0.05` world units mapped to 5 cm per 0.1 s implies 0.5 m/s and is
close to the page's stated no-load speed. It is physically plausible as a
starting scale only if the motor is driven near its 6 V reference condition and
loaded speed remains near no-load speed.

If the shipping-list `75:1` motor is the actual motor and the same 13,000 rpm
motor shaft figure applies, the simple ratio calculation gives:

```text
output speed ≈ 13,000 ÷ 75 = 173 rpm
linear speed ≈ 0.13195 × 173 ÷ 60 = 0.380 m/s
distance per 0.1 s ≈ 3.80 cm
```

That conflict changes the scale conclusion materially. The exact reference
motor identity must be resolved or measured before calling 5 cm/action
validated. No change to `MOVE_FORWARD` is justified by this audit.

### 7.2 Timestep assessment

`dt = 0.1 s` gives 10 control updates per second. The DRV8833 reference driver
has a wake time up to 1 ms, so driver enable latency does not by itself defeat
0.1 s. The motor's loaded acceleration, electrical time constant, gearbox
backlash, and floor traction response are not supplied by DFRobot and could not
be inferred reliably from the no-load rpm.

Assessment: **RETAIN PROVISIONALLY / NEEDS MEASUREMENT**. The timestep is
reasonable for a first control abstraction and 5 cm-scale movement, but a
future hardware test should measure step response, stopping distance, and
loaded speed. Obstacle-rich development may earn a smaller movement increment
without requiring a smaller thermal integration step.

## 8. Battery and energy budget

Two compact 1S LiPo references bound a plausible first battery scale:

| Reference | Nominal energy calculation | Physical reference |
|---|---:|---|
| Adafruit 500 mAh | `3.7 V × 0.500 Ah = 1.85 Wh = 6,660 J` | 10.5 g; 29 × 36 × 4.75 mm; protected; 3.0 V cutout; charge at 500 mA or less |
| Data Power DTP603443 850 mAh | `3.7 V × 0.850 Ah = 3.145 Wh = 11,322 J` | less than 20 g; approximately 34 × 43 × 6 mm; 1C maximum continuous charge/discharge |

The nominal usable fraction is a **DESIGN CHOICE** with an **ENGINEERING
ESTIMATE** range of 70–85%, not a battery guarantee. That gives approximately
4.7–9.6 kJ of
usable simulation energy before reserve policy and protection behavior are
specified.

A 1S pack is physically attractive, but it is below the DFRobot motor's 6 V
reference condition. A future design must choose among under-driving the motor,
using a boost stage, or selecting a different drivetrain/battery arrangement.
Adding a boost stage changes both battery power and heat and therefore must not
be hidden inside an abstract movement cost.

Recommended representation: **physical joules internally, normalized energy
organism-visible**.

```text
E_battery_next = clamp(
    E_battery
    + P_stored_charge × dt
    - P_electronics_electrical × dt
    - P_actuator_electrical(action) × dt,
    0,
    E_battery_max,
)

visible_energy = E_battery / E_battery_max
```

Do not add voltage-versus-state-of-charge curves, degradation, or battery age
until a demonstrated question requires them. Battery voltage and joules may
remain evaluator-only; the organism need not see Wh, voltage, or charger
efficiency.

## 9. Electronics power budget

The ESP32-S3 datasheet reports, at 3.3 V, radio-disabled modem-sleep current
from 13.2 mA for dual-core idle at 40 MHz to 91.7 mA for dual-core execution
at 240 MHz with clocks disabled; its corresponding 3.3 V chip power is about
44 mW to 303 mW. Peripheral-enabled values are higher. Wi-Fi transmit peaks
of roughly 283–340 mA are explicitly not a suitable baseline for this early
robot.

The DRV8833 reference reports 1.7–3 mA motor-supply current in its active
non-driving test condition and 1.6–2.5 µA in sleep at 5 V. Those values do not
include motor power.

At this abstraction, most electronics electrical consumption is treated as
local body heat, including regulator and small supporting losses. The
battery-side electrical input and the body-coupled heat remain separate terms
so a later prototype measurement can account for any power that is not
coupled into the lumped body. Candidate continuous electronics body heat, and
the corresponding electrical input estimate, is therefore:

| Mode | Candidate electronics electrical input / body heat | Status |
|---|---:|---|
| Idle/light computation, radio disabled | 0.08–0.20 W | Engineering estimate anchored to ESP32-S3 and driver references |
| Active normal computation, radio disabled | 0.12–0.35 W | Engineering estimate; exact firmware duty cycle dominates |
| Wi-Fi active | not selected as baseline; can add hundreds of mW during activity | Evaluator comparison only, not a V0.4 default |

For `dt = 0.1 s`, the electronics energy is approximately 0.008–0.020 J per
idle transition or 0.012–0.035 J per active transition. A prototype should
measure battery-side power with the actual regulator, MCU firmware, sensors,
and radio disabled/enabled states.

## 10. Actuator power and heat budget

### 10.1 Motor input

DFRobot lists 40 mA at 6 V. The page does not explicitly label that line
"no-load current" and does not provide a loaded-current curve, so this figure
is not treated as normal loaded operating current. It does not describe
mechanical output under load. The 360 mA stall figure gives 2.16 W per motor,
or 4.32 W for both, but stall is a peak/failure case and must not be used as
the normal movement cost.

The following are deliberately broad **ENGINEERING ESTIMATES** pending a
loaded current measurement:

| Action | Normal two-motor actuator electrical input | Battery electrical energy at 0.1 s | Actuator body-coupled heat | Peak/stall comparison |
|---|---:|---:|---:|---:|
| `WAIT` | 0 W | 0 J | 0 W (motors inactive) | motors inactive |
| `MOVE_FORWARD` | 0.5–1.5 W | 0.05–0.15 J | **UNKNOWN / NEEDS MEASUREMENT** | up to about 4.32 W pair at documented stall current |
| In-place `TURN` | 0.3–1.0 W | 0.03–0.10 J | **UNKNOWN / NEEDS MEASUREMENT** | depends on PWM and floor friction |

These are battery-side electrical-input ranges, not thermal heat values.
Normal, peak, and stall cases must remain separate. A future physical power
event should split actuator electrical input into mechanical output,
motor/gear losses, driver losses, and heat. Only the effective portion
thermally coupled into the lumped body belongs in
`P_actuator_body_heat(action)`.

### 10.2 Driver loss

At `VM = 5 V`, `IO = 500 mA`, and `TJ = 25 °C`, the DRV8833 datasheet gives
typical high-side and low-side FET on-resistances of 200 mΩ and 160 mΩ. For
one conducting bridge:

```text
P_driver,DC ≈ I_RMS² × (0.200 + 0.160) Ω
             = I_RMS² × 0.360 Ω
```

For two bridges at 100–200 mA per motor, this is approximately 7–29 mW total
before PWM loss. TI states that PWM switching loss is typically about 10–30%
of DC power dissipation, giving a rough normal driver-loss scale of 0.01–0.04 W
for this current range. This is small beside motor electrical input but not
necessarily zero. Actual PCB copper, temperature, PWM mode, supply voltage,
and current waveform matter.

### 10.3 What becomes body heat

Motor winding resistance, brush/gear friction, and driver conduction losses
eventually become heat. External mechanical work does not all become immediate
body heat. The fraction conducted into a single lumped body is **UNKNOWN / NEEDS
MEASUREMENT**, because it depends on motor mounting, chassis material, gearbox
coupling, duty cycle, and time scale.

The battery energy equation must therefore use
`P_actuator_electrical(action)`, while the thermal equation must use only
`P_actuator_body_heat(action)`. Do not invent a motor thermal-efficiency or
coupling fraction to populate the latter. If a numerical sensitivity envelope
is needed before measurement, sweeping `P_actuator_body_heat(action)` from
zero up to the corresponding electrical-input range is a deliberately broad
upper-envelope assumption, not an estimate of the actual body heat.

Recommendation: retain both terms in the evaluator-side physics candidate and
measure the action-class body-coupled heat. Do not expose motor power, current,
RPM, or loss decomposition to the organism.

## 11. Charging power and heat budget

### 11.1 Switching charger reference

TI's BQ25895 is a single-cell switch-mode charger reference. Its datasheet
reports 93% charge efficiency at 2 A and 91% at 3 A and includes constant-current
and constant-voltage charging with termination and thermal regulation. Those
efficiencies are not guaranteed at a small 100–500 mA robot charge current.

A reasonable first simulation estimate is 85–93% battery-charge efficiency,
classified **ENGINEERING ESTIMATE** and requiring measurement. At 0.5 A and
approximately 3.7 V battery voltage, battery-side charge power is about 1.85 W:

```text
P_input ≈ 1.85 W / η
P_charger_loss = P_input - 1.85 W

η = 0.93 → P_loss ≈ 0.14 W
η = 0.85 → P_loss ≈ 0.33 W
```

### 11.2 Linear charger reference

Microchip's MCP73831 is a single-cell linear charger that uses constant-current
followed by constant-voltage charging. Microchip explicitly warns that low
linear-charging efficiency makes thermal design important. With an approximate
5 V input and 0.1–0.5 A charge current, the idealized IC dissipation is roughly:

```text
P_linear_loss ≈ (5.0 V - 3.7 V) × I
               ≈ 0.13–0.65 W
```

The value falls as battery voltage approaches 4.2 V and current tapers. This is
an estimate, not a complete charger thermal model.

### 11.3 Termination and full-battery docking

Both charger references use a CC/CV charge process and a charge-complete or
standby state. A realistic future model should therefore distinguish:

- charger input power;
- battery energy actually stored;
- charger and battery electrical loss;
- current taper near full;
- terminated/full standby behavior.

Continued docking at full battery should not automatically apply the same
charging heat as mid-SOC charging. If the charger or power-path circuit still
supplies the robot's load, baseline electronics power can continue, but that is
not the same as continued battery charging loss. This is a direct reason not to
carry D-002's offered-input heat rule into V0.4 without evidence.

## 12. Thermal capacity estimate

NIST gives approximately 900 J/(kg·K) for wrought aluminum near 20 °C. NIST's
304 stainless database supplies temperature-dependent specific-heat data; a
room-temperature steel value near 500 J/(kg·K) is used here only as an
engineering approximation. Battery, copper, silicon, plastics, and mounting
interfaces contribute different values.

An illustrative mass build-up is:

| Component | Plausible mass | Specific heat used for estimate | Provenance |
|---|---:|---:|---|
| Chassis structure | 50–100 g | 500–900 J/(kg·K) | Engineering estimate; material not specified |
| Two motors | about 30 g | 500 J/(kg·K) | 15 g each from related DFRobot motor page; exact ROB0049 motor unresolved |
| 1S battery | 10.5–20 g | 800–1,000 J/(kg·K) | Battery references / engineering estimate |
| Electronics, regulator, driver, wiring | 15–40 g | 500–1,000 J/(kg·K) | Engineering estimate |
| Shell and mounts | 20–80 g | 800–1,500 J/(kg·K) | Engineering estimate; material unknown |

Using the displayed lower and upper component ranges gives a broad effective
lumped thermal capacitance of approximately
72–285 J/K. A narrower first candidate of **150–250 J/K**, with **180 J/K** as
an illustrative center value, is physically defensible as a simulation range
but not known hardware truth.

The effective value includes only the heat that equilibrates on the chosen
time scale. Motor and battery temperatures may lag the shell, so a one-body
capacitance is a useful abstraction, not proof that the assembly is isothermal.

## 13. Cooling estimate

The minimal passive law should be:

```text
P_cooling = G × (T_body - T_ambient)
```

with cooling clamped so it does not drive the body below ambient in the simple
first-order model.

For a 122 mm circular body, the top and bottom disk area is:

```text
A_top+bottom = 2 × π × (0.061 m)² = 0.0234 m²
```

Adding an illustrative 30 mm side wall gives approximately 0.0115 m² more,
or about 0.035 m² exposed area. The side height is an estimate because the
reference page does not specify a complete enclosure.

NASA's thermal-control guidance gives natural convection in Earth air as on
the order of 5 W/(m²·K), and describes convection plus radiation as the basic
passive heat-rejection mechanisms. Applying that order-of-magnitude coefficient
to the estimated area gives natural-convection conductance near 0.18 W/K.
Radiation and conduction through the floor/chassis can add or dominate it;
these depend strongly on finish, enclosure, contact area, floor, and mounting.

Candidate total body-to-environment conductance: **G = 0.15–0.50 W/K**.
This is an engineering estimate with low-to-medium confidence. A first center
value of 0.25 W/K is a design choice for later sensitivity work, not a measured
constant.

Useful cooling-power checks:

| Body-to-ambient difference | Cooling range at G = 0.15–0.50 W/K |
|---:|---:|
| 5 K | 0.75–2.50 W |
| 10 K | 1.50–5.00 W |
| 20 K | 3.00–10.00 W |

At the center values `C = 180 J/K`, `G = 0.25 W/K`, the time constant is 720
s and a 0.2 W idle load would settle about 0.8 K above ambient. A move-plus-
electronics load cannot be assigned one physical steady-state rise until
`P_actuator_body_heat` is measured. For sensitivity only, if 1.0 W of MOVE
electrical input plus 0.2 W of electronics heat were conservatively treated as
body heat, the result would be about 4.8 K above ambient. That is a sensitivity
calculation, not an expected thermal value.

## 14. Movement-cooling assessment

At 0.5 m/s and a 0.12 m characteristic length, a rough room-air Reynolds
number is about 4,000 using standard air-property estimates. This is a
transition-region scale check, not a validated robot aerodynamics model. NASA
gives a very broad forced-convection range of roughly 10–300 W/(m²·K), which
confirms that speed can matter but does not identify the coefficient for this
shape.

With approximately 0.035 m² exposed area, even an additional 2–5
W/(m²·K) of effective convection would add only about 0.07–0.18 W/K. At a 5 K
temperature difference that is approximately 0.35–0.90 W of extra cooling,
which could be a meaningful fraction of an as-yet-unmeasured actuator
body-heat term. At a 1 K difference it is only 0.07–0.18 W. Floor conduction
and enclosure geometry may make the movement contribution smaller or larger.

Conclusion: movement-induced cooling is **not provably negligible**, but its
uncertainty is comparable to the normal actuator budget and it is not needed to
make the smallest model conceptually coherent. **OMIT from the first V0.4
model / NEEDS MEASUREMENT**. Measure stationary versus 0.5 m/s body cooling at
several temperature differences before adding `G(action)`.

## 15. Temperature-bound assessment

The default evaluator ambient candidate is 23 °C. An initial body temperature
of 23–25 °C is a design choice for a room-temperature start, not an organism
observation.

The Data Power battery reference specifies 0–45 °C charging and −20–60 °C
discharge ranges. The ESP32-S3 and DRV8833 component ratings are substantially
higher, but component absolute maxima are not appropriate whole-body viability
thresholds. Battery charge temperature, enclosure materials, adhesives,
sensor mounting, and local hot spots are more relevant to a conservative
integrated boundary.

Candidate future whole-body upper boundary: **40–50 °C**, with **45 °C** as a
provisional design center pending prototype measurement. This is a
**DESIGN CHOICE**, not a safety certification. It should represent a
conservative integrated operating boundary, not catastrophic destruction or
the MCU absolute maximum.

The inconvenient physical implication is important. From 23 °C to a 45 °C
boundary is a 22 K rise. At `G = 0.15–0.50 W/K`, persistent net heat of
approximately 3.3–11 W would be required to reach that steady-state boundary.
Known electronics and charging-loss terms are usually below this. The
actuator contribution cannot be inferred by equating electrical input with
body heat; even a broad full-electrical sensitivity envelope is not a physical
estimate. Therefore realistic V0.4 physics may produce little or no thermal
viability pressure in an open, room-temperature 122 mm body. That result must
be preserved rather than corrected by inflating charger loss, treating all
actuator input as heat, or lowering the threshold solely to recreate D-002.

## 16. Thermal time constant and horizon

```text
seconds per 1000 transitions = 1000 × 0.1 s = 100 s
                              = 1.67 minutes

tau = C / G

minimum candidate tau = 150 J/K ÷ 0.50 W/K = 300 s
maximum candidate tau = 250 J/K ÷ 0.15 W/K = 1,667 s
center candidate tau   = 180 J/K ÷ 0.25 W/K = 720 s
```

In transitions, the candidate time constant is approximately 3,000–16,700
transitions, with a center estimate of 7,200 transitions. A 1,000-transition
run is only 100 s, or approximately 0.06–0.33 candidate time constants. It is
useful for detecting very large transients or integration errors, but it is not
a meaningful thermal steady-state horizon for this candidate body.

Suggested later V0.4 development horizon: **10,000–30,000 transitions** (1,000–
3,000 s, 16.7–50 minutes), with shorter 1,000-transition smoke tests retained
for fast checks. Existing historical horizons must not be changed by this
record.

## 17. Scenario comparison table

These scenarios use the candidate ranges above, assume the body begins near
ambient unless otherwise stated, and are non-behavioral comparisons. The
actuator electrical-input column is a battery-depletion quantity; it is not a
thermal quantity. Where actuator body-coupled heat is unknown, the net thermal
power is intentionally left symbolic rather than silently equated to
electrical input.

| Scenario | Electronics electrical input / body heat approximation | Actuator electrical input | Actuator body-coupled heat | Charging body heat | Cooling | Approx. net body thermal power |
|---|---:|---:|---:|---:|---:|---:|
| 1. `WAIT`, off charger | 0.08–0.20 W | 0 W | 0 W | 0 W | 0 W at ΔT≈0 | +0.08–+0.20 W |
| 2. `MOVE_FORWARD`, off charger | 0.12–0.35 W | 0.5–1.5 W | **UNKNOWN / NEEDS MEASUREMENT** | 0 W | 0 W at ΔT≈0 | `+0.12–+0.35 W + P_actuator_body_heat(MOVE)` |
| 3. `TURN`, off charger | 0.12–0.35 W | 0.3–1.0 W | **UNKNOWN / NEEDS MEASUREMENT** | 0 W | 0 W at ΔT≈0 | `+0.12–+0.35 W + P_actuator_body_heat(TURN)` |
| 4. Charging, low/mid SOC | 0.08–0.20 W | 0 W | 0 W | +0.05–+0.33 W switching; +0.13–+0.65 W linear | 0 W at ΔT≈0 | `+0.08–+0.20 W + charging body heat` |
| 5. Docked near full | 0.08–0.20 W | 0 W | 0 W | approximately 0–0.05 W after termination, topology-dependent | 0 W at ΔT≈0 | approximately +0.08–+0.25 W |
| 6. Moving while warm | 0.12–0.35 W | 0.5–1.5 W | **UNKNOWN / NEEDS MEASUREMENT** | 0 W | 0.75–7.50 W for ΔT=5–15 K and G=0.15–0.50 W/K | `+0.12–+0.35 W + P_actuator_body_heat(MOVE) − cooling` |

The wide range in scenario 6 is intentional: cooling is temperature-dependent,
while the action itself does not guarantee a large cooling benefit. No finite
net range is reported for scenarios 2, 3, or 6 until actuator body-coupled
heat is measured or an explicit sensitivity bound is selected. The table does
not model a controller, contact geometry, or behavioral duty cycle.

## 18. Candidate minimal V0.4 equations

The smallest coherent candidate is:

```text
P_body_heat = P_electronics_body_heat
            + P_actuator_body_heat(action)
            + P_charging_body_heat(charge_phase, SOC)

P_cooling = max(0, G × (T_body - T_ambient))

T_next = T_body + dt × (P_body_heat - P_cooling) / C_thermal
```

Candidate energy accounting is:

```text
E_next = clamp(
    E_battery
    + P_stored_charge(charge_phase, SOC) × dt
    - P_electronics_electrical × dt
    - P_actuator_electrical(action) × dt,
    0,
    E_battery_max,
)
```

The charger must be allowed to taper or terminate. `P_charging_body_heat`
(including charger loss at this abstraction) must not be a constant function
of docking contact when no energy is being accepted.
Battery internal loss may later be represented as part of the charging and
discharge power event, but adding multiple compartments or voltage curves is
not justified yet.

Term-level disposition for the smallest candidate model:

| Candidate term | Required classification | Reason |
|---|---|---|
| `P_electronics_electrical` and `P_electronics_body_heat` | **RETAIN** | Battery-side electronics consumption is physically present; at this abstraction most is treated as local body heat, with the distinction preserved for measurement |
| `P_actuator_electrical(action)` | **RETAIN** | Movement and turning draw materially more battery electrical power than the controller at the reference scale; use measured action-class values when available |
| `P_actuator_body_heat(action)` | **RETAIN IN PRINCIPLE; UNKNOWN / NEEDS MEASUREMENT** | Actuator losses can heat the body, but mechanical output is not immediate body heat and thermal coupling is unresolved |
| `P_charging_body_heat` | **RETAIN** | Charging loss exists, but must follow topology, charge phase, taper, and termination rather than D-002 offered-input heat |
| Temperature-dependent passive cooling | **RETAIN** | A body-to-ambient gradient is the minimal physically coherent cooling mechanism |
| Movement-dependent cooling | **OMIT** | It may matter, but current shape, airflow, floor, and enclosure uncertainty do not justify adding it before measurement |

The retained terms are candidate physics, not authorization to modify the
current simulator. `P_electronics_electrical`,
`P_electronics_body_heat`, `P_actuator_electrical`,
`P_actuator_body_heat`, `P_charging_body_heat`, and `G` remain **UNKNOWN / NEEDS
MEASUREMENT** at prototype-fidelity precision, except where the broad
engineering ranges above are explicitly identified as sensitivity inputs.

## 19. PROGRAMMED / ORGANISM-VISIBLE / EVALUATOR-ONLY separation

### PROGRAMMED / PHYSICS

- `dt`, action-to-power mappings, battery capacity, charge-phase rules,
  `C_thermal`, `G`, ambient default, and upper integrated temperature boundary.
- One lumped body temperature state and physical-joule battery state.
- Motor/driver electrical event and its measured or estimated losses.
- Charger input, stored energy, taper/termination, and charger/battery losses.

### ORGANISM-VISIBLE

- Normalized own battery energy.
- Normalized own current body temperature.
- Existing beacon directional values and charging contact.
- Existing action set only: `WAIT`, `TURN_LEFT`, `TURN_RIGHT`,
  `MOVE_FORWARD`.

The organism must not receive ambient temperature, body-to-ambient delta,
absolute joules/Wh, charger efficiency, motor power/current/RPM, component
temperatures, physical coordinates, world scale, or elapsed wall-clock time.

For ADR 0012, normalization of own body temperature must not secretly encode
the evaluator's ambient temperature. Ambient remains evaluator-only. Use fixed
durable physical bounds or another ambient-independent mapping unless a future
ADR explicitly authorizes otherwise; do not derive the organism-visible
normalized signal from an ambient-relative expression such as
`T_body - T_ambient`.

### EVALUATOR-ONLY

- Ambient temperature, absolute body temperature, battery joules/voltage/SOC,
  charge phase, accepted charge, charger loss, actuator electrical power,
  actuator body-coupled heat, heat-source decomposition, cooling power, and
  component or prototype measurements.
- Geometry, mass, wheel speed, motor identity, temperature sensor placement,
  and diagnostic scenario labels.

No evaluator-only quantity may be repackaged as a hidden learning target or
controller rescue signal. Future plastic updates remain subject to ADR 0010's
sensory/plasticity closure.

## 20. Parameter provenance table

The labels are intentionally separated. A manufacturer number is not upgraded
to a physical truth for a future robot merely because it is convenient.

| Parameter | Candidate value/range | Units | Provenance classification | Source | Confidence | Recommended for V0.4? |
|---|---:|---|---|---|---|---|
| Chassis diameter | 122 | mm | MANUFACTURER REFERENCE | [DFRobot ROB0049](https://www.dfrobot.com/product-367.html) | High for reference product | Retain as scale reference |
| Wheel diameter | 42 | mm | MANUFACTURER REFERENCE | [DFRobot ROB0049](https://www.dfrobot.com/product-367.html) | High for reference product | Retain as scale reference |
| Ground clearance | 15 | mm | MANUFACTURER REFERENCE | [DFRobot ROB0049](https://www.dfrobot.com/product-367.html) | High for reference product | Reference only |
| Gear ratio | 50:1 versus 75:1 | ratio | MANUFACTURER REFERENCE | [DFRobot ROB0049](https://www.dfrobot.com/product-367.html) | Low until resolved | Needs measurement/resolution |
| Motor speed | 260 at 6 V; related page 440 at 6 V | rpm | MANUFACTURER REFERENCE | [ROB0049](https://www.dfrobot.com/product-367.html), [DFRobot 50:1 motor](https://www.dfrobot.com/product-1418.html) | Low for exact shipped motor | Do not freeze |
| Motor no-load speed | 13,000 | rpm | MANUFACTURER REFERENCE | [DFRobot ROB0049](https://www.dfrobot.com/product-367.html) | Medium; condition unclear | Reference only |
| Motor current | 40 mA at 6 V; 360 mA stall | mA | MANUFACTURER REFERENCE | [DFRobot ROB0049](https://www.dfrobot.com/product-367.html) | Medium for page's motor spec; 40 mA is not explicitly labelled no-load and no loaded-current curve is provided | Keep normal/stall distinct; measure loaded current |
| Control timestep | 0.1 | s | DESIGN CHOICE | Flow brief; driver wake reference [DRV8833](https://www.ti.com/lit/ds/symlink/drv8833.pdf) | Medium | Retain provisionally |
| World scale | 1 simulator unit ≈ 1 | m | DESIGN CHOICE | Flow brief | Medium | Retain provisionally |
| Movement increment | 0.05 | m/action equivalent | DESIGN CHOICE | Flow brief; wheel calculation above | Medium-low due motor conflict/load | Do not change yet |
| Ambient | 23 | °C | DESIGN CHOICE | Flow brief | Medium | Evaluator-only default |
| Battery nominal voltage | 3.7 | V | MANUFACTURER REFERENCE | [Adafruit 500 mAh](https://www.adafruit.com/product/1578), [Data Power 850 mAh datasheet](https://cdn.sparkfun.com/datasheets/Prototyping/850mah-en-1.0ver.pdf) | High for examples | Candidate only |
| Battery capacity | 500–850 | mAh | MANUFACTURER REFERENCE | Adafruit/Data Power links above | Medium-high for examples | Candidate range |
| Battery energy | 1.85–3.145 | Wh | DERIVED | `V × Ah` from battery references | Medium | Candidate range |
| Battery energy | 6,660–11,322 | J | DERIVED | `Wh × 3600` | Medium | Candidate range |
| Usable battery fraction | 70–85 | % | DESIGN CHOICE | Reserve policy not yet specified | Low | Sensitivity only |
| Electronics electrical input / body heat approximation, idle | 0.08–0.20 | W | ENGINEERING ESTIMATE | [ESP32-S3 datasheet](https://documentation.espressif.com/esp32_s3_datasheet_en.pdf); [DRV8833](https://www.ti.com/lit/ds/symlink/drv8833.pdf) | Medium-low | Candidate, measure |
| Electronics electrical input / body heat approximation, active radio-off | 0.12–0.35 | W | ENGINEERING ESTIMATE | ESP32-S3/DRV8833 references above | Medium-low | Candidate, measure |
| Actuator electrical input, move | 0.5–1.5 | W, pair | ENGINEERING ESTIMATE | DFRobot electrical current/stall bounds; no loaded-current curve | Low | Needs measurement |
| Actuator electrical input, turn | 0.3–1.0 | W, pair | ENGINEERING ESTIMATE | DFRobot electrical current/stall bounds; no loaded-current curve | Low | Needs measurement |
| Actuator body-coupled heat | UNKNOWN | W, action class | UNKNOWN / NEEDS MEASUREMENT | No loaded thermal-coupling measurement; electrical input is not body heat | Low | Measure; do not freeze a coupling fraction |
| Driver FET resistance | 0.200 + 0.160 | Ω/bridge | DATASHEET | [TI DRV8833](https://www.ti.com/lit/ds/symlink/drv8833.pdf), `VM = 5 V`, `IO = 500 mA`, `TJ = 25 °C` | Medium | Use if driver selected |
| Driver PWM loss | 10–30 | % of DC driver loss | DATASHEET | [TI DRV8833](https://www.ti.com/lit/ds/symlink/drv8833.pdf) | Medium, reference conditions | Use as sensitivity |
| Switching charger efficiency | 85–93 | % | ENGINEERING ESTIMATE | [TI BQ25895](https://www.ti.com/lit/ds/symlink/bq25895.pdf) | Low-medium at small current | Candidate; measure |
| Linear charge current | 0.1–0.5 | A | DESIGN CHOICE | [Adafruit battery](https://www.adafruit.com/product/1578), [Microchip MCP73831](https://ww1.microchip.com/downloads/en/DeviceDoc/MCP73831-Family-Data-Sheet-DS20001984H.pdf) | Medium | Candidate only |
| Linear charger loss | 0.13–0.65 | W at 5 V, 0.1–0.5 A | DERIVED | `P=(5−3.7)V×I`; Microchip link above | Medium-low | Sensitivity only |
| Effective thermal capacity | 150–250; center 180 | J/K | ENGINEERING ESTIMATE | NIST aluminum; NIST stainless; mass build-up above | Low | Candidate range, measure |
| Natural convection coefficient | about 5 | W/(m²·K) | ENGINEERING ESTIMATE | [NASA Thermal Control Engineering Guidebook](https://ntrs.nasa.gov/api/citations/20220006584/downloads/NASA%20ThermalControlEngineeringGuidebook%20v4Public.pdf) | Medium as order of magnitude | Reference only |
| Exposed area | 0.025–0.045 | m² | DERIVED | Disc geometry; enclosure height unknown | Low-medium | Sensitivity only |
| Total conductance G | 0.15–0.50; center 0.25 | W/K | ENGINEERING ESTIMATE | NASA convection/radiation framework plus area estimate | Low | Candidate range, measure |
| Movement cooling increment | 0–0.15 | W/K | ENGINEERING ESTIMATE | NASA forced-convection range plus geometry uncertainty | Low | Omit initially |
| Upper body boundary | 40–50; center 45 | °C | DESIGN CHOICE | Battery charge range; integrated-system conservatism | Low | Candidate only, measure |
| Thermal time constant | 300–1,667; center 720 | s | DERIVED | `τ=C/G` | Low-medium | Horizon planning only |
| Development horizon | 10,000–30,000 | transitions | DESIGN CHOICE | `dt=0.1 s` and `τ` range | Medium-low | Suggest later, do not change history |

## 21. Major uncertainties and measurement plan

The quantities most likely to dominate the result are:

- exact motor ratio and motor identity;
- loaded motor current and speed on the intended floor;
- final total mass and wheel traction;
- battery voltage under load and current capability;
- whether a 1S pack needs a boost stage to approach the 6 V motor reference;
- charger topology and actual charge current;
- charger termination and full-dock power-path behavior;
- thermal coupling of motors, battery, driver, and regulator into the body;
- enclosure ventilation and exposed surface area;
- floor/chassis thermal conduction;
- thermal sensor mounting and sensor lag;
- actual cooling coefficient at stationary and moving conditions.

Can remain estimates for the first evaluator sensitivity study:

- 150–250 J/K effective thermal capacity;
- 0.15–0.50 W/K total conductance;
- 0.5–1.5 W normal paired actuator electrical input;
- 85–93% switching charge efficiency;
- 40–50 °C candidate integrated boundary.

Should be measured before a physicalized claim or tightly tuned V0.4 model:

- wheel rpm and distance per 0.1 s at several loads and battery voltages;
- battery-side current for WAIT, MOVE, and TURN;
- synchronized motor-case, driver-board, regulator, battery, and shell
  temperatures during those action classes, so effective body-coupled actuator
  heat can be estimated without equating it to battery electrical input;
- driver-board input power and temperature;
- charge input, battery acceptance, taper, and post-termination draw;
- transient temperatures at battery, motor cases, driver, regulator, and shell;
- cool-down curves at rest and approximately 0.5 m/s;
- mass and component thermal contact after assembly.

## 22. What should be retained

- Keep 0.1 s as the provisional physical control step.
- Keep the 1 m/world-unit scale and 5 cm candidate movement mapping for now,
  but resolve the first-party motor conflict and measure loaded speed before
  treating it as validated.
- Use one lumped thermal body in the first physicalized model.
- Use temperature-dependent passive cooling toward evaluator-side ambient.
- Couple battery electrical power, mechanical work, losses, and heat at the
  same physical event while keeping the accounting paths distinct:
  `P_actuator_electrical(action)` depletes the battery and
  `P_actuator_body_heat(action)` heats the body only to the measured/effective
  coupled extent.
- Use physical joules internally with normalized own-energy interoception.
- Retain a single normalized own-temperature interoceptive channel.
- Keep ambient, absolute power, component temperatures, and charge phase
  evaluator-only.
- Keep wheel sensors, motor-current sensing, SOC-voltage curves, degradation,
  and extra thermal compartments out of the smallest model.

## 23. What should remain omitted

- Do not carry D-002's constant offered-input heat into V0.4 by default.
- Do not make charging the dominant heat source without measured evidence.
- Do not inflate charger losses to preserve the D-003/D-014 shuttle.
- Do not equate actuator electrical input with actuator body-coupled heat or
  draw thermal conclusions from the full electrical-input range.
- Do not assume movement cools the robot overall; it adds motor heat and may
  add uncertain airflow cooling.
- Do not add movement-dependent cooling in the first model unless prototype
  measurements show it matters.
- Do not use motor stall power as ordinary locomotion power.
- Do not expose ambient temperature, absolute joules, power decomposition, SOC,
  motor state, or charger state to Aweform.
- Do not add battery degradation, voltage curves, multiple thermal reservoirs,
  wheel encoders, or a new learner merely because a physical robot could have
  them.

## 24. Recommended next governance step

D-019 supports preparing, but does not itself create, a new durable boundary
document such as **ADR 0012 — V0.4 minimal physical embodiment and
thermal/energy boundary**.

Implementation should wait for an appropriate ADR because the proposed next
slice changes physical energy accounting, actuator-generated heat, charging
losses and termination, temperature dynamics, ambient-temperature physics, and
the durable interpretation of organism-visible energy/temperature channels.
That ADR would require the formal exact-current-HEAD Sol and Claude Opus 5
independent review and Flow authorization specified in `AGENTS.md` before
merge. D-019 does not pre-decide ADR 0012's exact contents.

## 25. Limitations

This is a source-backed engineering audit, not a hardware test, CFD analysis,
battery safety assessment, or confirmation experiment. Several reference
products are not guaranteed to be the final assembly. Manufacturer pages may
contain stale or conflicting values, and the exact DFRobot motor shipped with
ROB0049 is unresolved. The thermal capacity and conductance ranges are broad
because body materials, floor contact, enclosure, and component mounting are
unknown.

The calculations support scale and sensitivity planning only. They do not
establish that a physical robot is safe at the proposed threshold, that a
future physical Aweform will survive a specified horizon, or that any thermal
signal will improve behavior. No claim about consciousness, emotion,
subjective experience, genuine life, metabolism, or emergent intelligence is
made.

## 26. Sources / URLs

### Hardware and battery

- [DFRobot miniQ 2WD Robot Chassis, ROB0049](https://www.dfrobot.com/product-367.html)
- [DFRobot Micro Metal Gear Motor with PH2.0 Connector, 50:1](https://www.dfrobot.com/product-1418.html)
- [DFRobot MiniQ 2WD Complete Kit v2.0](https://www.dfrobot.com/product-555.html?description=true&search=ROB0081)
- [Adafruit 3.7 V 500 mAh LiPo](https://www.adafruit.com/product/1578)
- [Data Power DTP603443 3.7 V 850 mAh battery datasheet](https://cdn.sparkfun.com/datasheets/Prototyping/850mah-en-1.0ver.pdf)

### Electronics and charging

- [TI DRV8833 datasheet](https://www.ti.com/lit/ds/symlink/drv8833.pdf)
- [Espressif ESP32-S3 Series datasheet](https://documentation.espressif.com/esp32_s3_datasheet_en.pdf)
- [TI BQ25895 switch-mode charger datasheet](https://www.ti.com/lit/ds/symlink/bq25895.pdf)
- [TI BQ2407x linear charger datasheet](https://www.ti.com/lit/ds/symlink/bq24074.pdf)
- [Microchip MCP73831/MCP73832 linear charger datasheet](https://ww1.microchip.com/downloads/en/DeviceDoc/MCP73831-Family-Data-Sheet-DS20001984H.pdf)

### Thermal properties and heat transfer

- [NIST wrought aluminum properties](https://materialsdata.nist.gov/bitstream/handle/11115/179/Properties%20of%20Wrought%20Aluminum.pdf)
- [NIST 304 stainless properties database](https://trc.nist.gov/cryogenics/materials/304Stainless/304Stainless_rev.htm)
- [NASA Thermal Control Engineering Guidebook](https://ntrs.nasa.gov/api/citations/20220006584/downloads/NASA%20ThermalControlEngineeringGuidebook%20v4Public.pdf)
