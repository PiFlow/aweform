# Aweform — Future Physical Embodiment Direction: Wheel-Legged Body

**Status:** non-authorizing future embodiment note  
**Recorded:** 2026-09-22  
**Repository context:** originally recorded from main at 02a3b60d30080e010c28cd37cc1f12286a15155d after D-044; refreshed after acceptance of ADR 0017. ADR 0017 is authoritative for the prospective V0.5 wheel-command, differential-drive, centred-dock, wheel-delta proprioceptive, and actuator-bookkeeping boundaries.  
**Purpose:** preserve the additional long-range wheel-legged physical-body direction and engineering implications worth keeping compatible with future Aweform development, without changing ADR 0017, the developmental sequence, or authorizing physical implementation.

## Founder-selected direction

The current preferred long-range body concept is a compact bilateral **wheel-legged morphology**:

- two articulated left/right legs;
- one independently driven wheel at the end of each leg;
- wheels capable of signed bidirectional continuous rotation;
- a central body containing energy storage, computation, power electronics, and core sensing;
- future leg articulation capable of changing body posture and wheel placement;
- eventual capability, if justified by later experiments and hardware, for rough-terrain traversal, stair/curb negotiation, self-righting, and high-energy manoeuvres such as jumping;
- a future top-mounted wide-field or approximately panoramic vision system remains a candidate richer perceptual layer, not a present sensor commitment.

This is a provisional long-range morphology target, not a frozen final-hardware specification. ADR 0017 separately freezes first-slice V0.5 morphology references (`0.180 m` body length, `0.215 m` outside wheel span, `b = 0.185 m`, `r = 0.045 m`) for prospective simulator work. Final physical dimensions, degrees of freedom, joint topology, actuator models, suspension/compliance, materials, camera design, and charging hardware remain open.

## External mechanical inspiration — Mondo Robotics Beni

A useful current reference for the broad morphology is **Mondo Robotics' Beni**:

- Website: https://www.mondorobotics.com/

Mondo presents Beni as a compact all-terrain camera robot that uses wheeled locomotion and can negotiate obstacles with jumping capability. Aweform is **not** intended to copy Beni as a product or inherit its control architecture. The reference is retained because it demonstrates a compact physical design space in which efficient wheeled locomotion can coexist with more articulated, high-mobility behaviour.

The project-specific design questions below are Aweform proposals/inferences, not claims about Beni's internal engineering.

## Why this morphology is attractive for Aweform

A wheel-legged body creates two useful energetic regimes:

1. **Routine locomotion:** wheels provide relatively efficient, precise movement for ordinary navigation and docking.
2. **Exceptional mobility:** articulated legs can spend more energy when terrain or body recovery requires it.

This is particularly relevant to Aweform because physical actions should eventually carry real energetic consequences. A future embodied agent may therefore encounter meaningful trade-offs such as:

> Is a costly leg manoeuvre or jump worth the energy, or is a longer wheeled route preferable?

That trade-off should emerge from measured physical consequences when hardware exists, not from arbitrary reward shaping.

## Provisional actuator decomposition

### Wheel drive

The current preferred engineering direction for the final wheel drives is:

> **encoder-equipped geared DC or BLDC motors with closed-loop bidirectional control**

rather than continuous-rotation hobby servos as the default assumption.

Reasons to preserve this option include:

- direct signed bidirectional wheel actuation;
- compatibility with precise low-speed docking motion;
- wheel rotation/velocity measurement;
- future odometry and slip experiments if separately authorized;
- better separation between drive actuation and leg articulation.

This is an engineering preference, not a hardware selection. Motor type, gearbox, encoder resolution, controller electronics, torque/speed envelope, and wheel diameter must be selected from future measured requirements.

### Leg articulation

The articulated legs will likely require actuators designed for controlled joint position and/or torque, for example suitable servo-class or compact BLDC joint actuators.

Wheel drive and leg articulation should remain conceptually separate:

- wheel motors control continuous rolling motion;
- leg joints control body posture, ground clearance, wheel placement, obstacle manoeuvres, and later dynamic behaviours.

## Relationship to the accepted V0.5 wheel interface

ADR 0017 accepted exactly one continuous compound organism-facing wheel action, and D-045 has now committed the first deterministic V0.5 implementation of that interface:

~~~text
wheel_motors_lr(desired_delta_left, desired_delta_right)
~~~

Each value is a **desired incremental wheel rotation in radians during the next `dt = 0.1 s` control interval**. The pair is one action and one transition; the two values are independently signed and reversible.

This future-direction note therefore explicitly defers to ADR 0017. It must **not** reinterpret that accepted interface as a wheel-velocity command. A physical motor controller may eventually use lower-level velocity, current, torque, or position loops beneath the organism-facing interface, but those implementation details do not change the accepted V0.5 command semantics unless a later reviewed boundary explicitly amends them.

A later articulated-leg interface could remain separate, for example conceptually:

~~~text
leg_joints_lr(left_configuration, right_configuration)
~~~

No leg API, joint count, units, action range, leg proprioceptive channel, or controller semantics are authorized by this note.

## Energy and viability implications

Future physicalization should distinguish at least:

- electronics/background power;
- wheel-drive electrical power;
- leg-actuation electrical power;
- sensing/computation power;
- docking/charging power flow.

Dynamic actions such as jumping, aggressive self-righting, or rapid posture changes should not be represented as arbitrary action penalties. Their energetic and thermal costs should ultimately be based on measured or provenance-labelled physical estimates and later real hardware measurements.

The body should therefore remain compatible with Aweform's existing principle that energy is an engineered viability state with causal consequences, not a reward score.

## Low-level bodily competence

A future physical body will probably need a safety/reflex layer below developmental cognition. Candidate responsibilities include:

- motor current/torque protection;
- joint limits;
- IMU-based fall/orientation detection;
- emergency actuator shutdown;
- low-level wheel-speed regulation;
- basic self-righting safety sequences if required;
- charging-contact verification;
- local docking reflexes or beacon/proximity handling.

This is consistent with [low-level-autonomy-and-sensor-layering-future-question.md](low-level-autonomy-and-sensor-layering-future-question.md): richer cognition need not replace every economical, viability-critical local control loop.

Such low-level mechanisms must remain distinguishable from organism-visible cognition and learning. Future work must state explicitly which bodily variables and low-level states Aweform itself can sense.

## Perception direction

The central body should remain physically compatible with a future top-mounted wide-field or approximately 360-degree camera/perception module.

That possibility does **not** make current beacon/docking work obsolete. A future division may be:

~~~text
richer perception / navigation
        ↓
station or route approximately located
        ↓
local low-power docking competence
        ↓
physical contact and verified charging
~~~

Camera vision remains explicitly unauthorized under the current repository boundary.

## Developmental staging

Do **not** import the full wheel-legged body into the simulator merely because it is a plausible final morphology.

ADR 0017 made the V0.5 first-slice decisions for bilateral wheel-delta commands, minimal differential-drive kinematics, and exactly two quantized signed wheel-delta proprioceptive channels. D-045 has now implemented and descriptively validated that deterministic substrate. This note does not extend it.

A disciplined later sequence could be:

1. preserve D-045 as the minimal validated wheel/body/proprioceptive substrate while the separately authorized D-046 prediction question is tested;
2. introduce articulated leg posture only when terrain/body configuration creates a real developmental problem;
3. introduce obstacles, stairs, compliance, contact physics, self-righting, or jumping only when those questions become scientifically necessary;
4. introduce richer visual perception only when the developmental problem earns it;
5. move to a more detailed physics simulator only when simple kinematics can no longer answer the question.

Each step should retain simple baselines and avoid adding capabilities merely because a mature final robot might eventually need them.

## Relationship to historical V0.4 / D-044 and current V0.5

This note does not reinterpret the historical V0.4 finite-body simulator as a literal wheel-legged robot.

D-042, D-043, and D-044 remain historical V0.4 Development results with their original four-action, six-channel, front-contact, learner/controller, beacon, energy/thermal, and charging semantics.

For current and future V0.5 work, ADR 0017 is authoritative, with D-045 as its first committed substrate implementation. ADR 0017 supersedes only the surfaces it explicitly lists, including the semantic V0.4 action vocabulary, point-centre movement/turn kinematics, wheel-proprioception exclusion, six-channel observation boundary, action-class actuator bookkeeping, and front-contact dock geometry. It also keeps the V0.4 D-026/D-027/D-030 mechanisms historical rather than silently porting them into V0.5.

The wheel-legged morphology recorded here remains a longer-range compatibility target beyond that deliberately minimal V0.5 first slice.

## Guards

This note does **not** authorize:

- physical robot control;
- purchase or selection of any specific motor, servo, battery, camera, computer, or robot platform;
- odometry, motor-current sensing, leg proprioception, or organism-visible proprioception beyond the two quantized signed wheel-delta channels accepted by ADR 0017 and implemented in D-045;
- articulated-leg simulation or control;
- obstacles, stairs, rigid-body/contact physics, jumping, self-righting, or balance learning;
- camera vision or panoramic sensing;
- any organism-facing wheel-action semantics that contradict or extend ADR 0017 without a later reviewed boundary;
- a new learner, planner, reward, world model, or reinforcement-learning mechanism;
- changes to accepted historical D/EXP results or existing ADR boundaries.

Any future durable action, sensory, physical, information, or safety boundary change must follow repository governance and the applicable ADR/review process.

## Bottom line

The project should keep future embodiment compatible with a **small two-wheel, two-articulated-leg body** in which:

- wheels handle most efficient everyday locomotion and precise docking;
- articulated legs provide posture and exceptional terrain mobility;
- the body can eventually self-right and, if justified, perform high-energy dynamic manoeuvres;
- energy, actuator state, charging, and thermal consequences remain physically grounded;
- richer perception can later sit above low-level bodily and docking competence.

The morphology is a long-range engineering direction, not a reason to complicate the current developmental experiment.
