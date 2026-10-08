# Independent audit: RoboSim as Aweform's physical simulation layer

- **status:** research input only; non-authorizing
- **date recorded:** 2026-10-08
- **repository base:** `e11ad91b3b7c649185bd1298ad5f3a791be571f8`
- **scope:** independent source audit and bounded engineering probes, subsequently archived in a documentation PR at Flow's request

The original audit was read-only; neither target repository was changed during its execution. This record adds documentation only. It is not an accepted ADR, migration authorization, new D-stage, formal evidence claim, or independent review of record under ADR 0013. It does not change existing physics, dependencies, sensors, learner/controller roles, roadmap, or reserved-seed contracts.

See the [proposed direct-Pymunk conformance tests](pymunk-conformance-test-proposal.md) for the staged next experiment, and the [archived audit probe methods and outputs](robosim-pymunk-audit-evidence.md) for executable-probe provenance. The proposed tests have not been implemented or run.

## 1. Executive verdict

**REJECT RoboSim as Aweform's production simulation dependency at this revision.**

**INFERENCE — recommended direction:** preserve the current simulator and consider a separately authorized, very small **direct-Pymunk adapter experiment**. This is a conditional recommendation to investigate a substrate, not to migrate now. The broader organism/physical-world separation is sound. RoboSim contributes too little suitable architecture to justify its extra dependency and adaptation burden.

**Confidence: HIGH** in rejecting unchanged RoboSim and in the identified boundary conflicts; **MODERATE** that direct Pymunk will reduce total engineering effort; **UNKNOWN / NEEDS TESTING** for hardware fidelity, Apple Silicon runtime behaviour, and the net cost of a complete migration.

The decisive findings are:

1. **VERIFIED:** RoboSim accepts normalized bilateral commands, then applies **chassis forward-velocity and yaw-rate P controllers**. It does not simulate independent rotating wheels. Its command is not Aweform's desired wheel radians per 0.1 s.
2. **VERIFIED:** its encoders reconstruct wheel speeds from post-step chassis motion, assume a unit-radius wheel in pixel coordinates, and accumulate truncated counts. This conflicts with Aweform's authorized shaft-delta measurements and wall-slip semantics.
3. **VERIFIED:** RoboSim core classes run headless without importing Pygame. Compute throughput is ample. Its interactive CLI is rendering-coupled and capped.
4. **VERIFIED:** the audited RoboSim tree contains no license file or declared project license; GitHub metadata reports `license: null`. This is a dependency/reuse permission blocker pending explicit licensing, not a claim that all inspection is prohibited.
5. **VERIFIED:** its noisy sensors use global `random.gauss`; unrelated RNG consumption changes the observation trace. Fresh independent noisy episodes require adapter work or sensor replacement.
6. **VERIFIED:** Pymunk supplies geometry and rigid-body collision mechanics, not a ready differential-drive traction model. It also does not automatically preserve Aweform's endpoint-only, full-yaw wall law.
7. **VERIFIED:** current `D058Env` already achieves approximately **40,583 complete transitions/s** in the bounded component benchmark. No simulation-throughput bottleneck was demonstrated.

**Answer to the primary question:** yes, a Pymunk physical backend can remain outside Aweform's organism. That boundary must be imposed by Aweform. RoboSim does not enforce it and is not the cleanest backend to retain.

## 2. Evidence, exact revisions, and limitations

| Source | Exact audited revision |
|---|---|
| PiFlow/aweform `main` | `e11ad91b3b7c649185bd1298ad5f3a791be571f8` |
| AnwarMP/RoboSim `main` | `86971d67a1eb0049653ebe842507a4ff30cb338d` |
| Pymunk 7.2.0 source | `3ef8f6e304fdc09e16c8ca2cfb1a3aa88a9399bc` |
| Bundled Munk2D 2.0.1 source | `ade7ed72849e60289eefb7a41e79ae6322fefaf3` |

All Aweform and RoboSim file references below refer to these revisions. Pymunk 7.2.0 matches RoboSim's lockfile. The installed runtime identifies its C engine as `2.0.1-ade7ed72849e60289eefb7a41e79ae6322fefaf3`: this is **Munk2D, Pymunk's Chipmunk2D fork**, not an unspecified current Chipmunk build.

Labels:

- **VERIFIED:** inspected source, repository/API metadata, or an executed probe; the nearby text distinguishes these.
- **INFERENCE:** interpretation, architecture recommendation, or engineering estimate.
- **UNKNOWN / NEEDS TESTING:** not established by this audit.

Current repository source and its committed development ledger take precedence over earlier roadmap or conversation summaries. Background robotics literature does not establish software compatibility and is not used to infer it.

This was not a formal ADR-0013 review-of-record for an implementation candidate. No historical official Aweform protocol, reserved-seed experiment, or new controller/learner lifetime study was executed. The complete Aweform suite was not run; focused tests were run. Benchmarks are small single-process workloads on one Linux VM, not hardware or production workload validation.

## 3. Current Aweform architecture reconstructed from main

### Governance and scientific lanes

**VERIFIED — repository:** `AGENTS.md`, `docs/north-star.md`, `docs/developmental-principles.md`, `docs/development-evidence-workflow.md`, `docs/reproducibility.md`, and `docs/safety-boundary.md` establish:

- D-series work is descriptive development; important EXP claims require frozen protocols, exact-SHA provenance, untouched reserved support, matched controls, and independent review.
- ADR 0002 separates simulator/evaluator truth from authorized observations.
- ADR 0010 permits bounded lifetime plasticity subject to recursive write provenance. Evaluator pose, success labels, future consequences, or hidden geometry cannot become training targets.
- ADR 0013 governs independent review of durable boundaries. A physics, sensor, or architecture boundary change is not an ordinary convenience refactor.
- ADR 0017 specifies V0.5 wheels, centered contacts, eight observations, and actuator accounting; ADR 0018 defines the Level-1 viability floor and its attribution boundary.
- ADR 0019/D-058 introduce the rectangular room-contact substrate. ADR 0020 is merged documentation for a prospective frozen obstacle room; there is **no `src/aweform/d060.py` in this main**.
- Hardware control is outside the current authorization. Designing a simulation interface compatible in shape with later hardware does not authorize a hardware driver.

**VERIFIED — source/status discrepancy:** `AGENTS.md` still says committed development extends through D-058. `development/INDEX.md` and the tree contain D-059 and VIS-D059. D-059's record still says final reviews pending, although GitHub reports PR #208 merged on 4 October 2026 at `0c6019012831de2dd9207f68384ecbb779e9a540`. ADR 0020's header says proposed/pending, although PR #212 merged on 5 October and is current main. These stale status fields should be reconciled later; they do not create executable D-060 physics. This audit made no corrections.

### Implemented embodiment and interfaces

| Aspect | VERIFIED current implementation |
|---|---|
| Historical V0.5 substrate | `aweform.d045.D045Env` |
| New physical-room substrate | `aweform.d058.D058Env`, `D058PhysicalConfig` |
| Canonical room | 3 m × 3 m; 1 m attribution arm also legal |
| Hull | Rectangle: length 0.180 m, width 0.215 m; half extents 0.090 and 0.1075 m |
| Drive geometry | Wheel radius 0.045 m; center-to-center track 0.185 m |
| Action | Two signed desired wheel increments in radians for one 0.1 s transition |
| Envelope | Each increment independently clipped to ±0.6457718232379019 rad |
| Derived maxima | Straight 0.290597320457 m/s; in-place yaw π rad/s, 18° per transition |
| Observation | `float32[8]`: energy, temperature, beacon L/F/R, dual charging-contact bit, left/right quantized wheel deltas |
| Gym return | Observation, reward `0.0`, terminated, truncated, `info == {}` |
| Proprioception | Previous interval's signed shaft deltas, rounded to nearest 1°; ties away from zero |
| Reset | Evaluator setup options, not controller observations; D-058 rejects unknown keys, illegal hull poses and a non-centered station |
| Pose/telemetry | Simulator/evaluator-only `Body`, station, heading, transition/contact records |

The public conceptual action is written `wheel_motors_lr(desired_delta_left, desired_delta_right)` in ADR 0017. The executable environment receives a bilateral array/list/tuple through `step(action)`; there is no required API function literally named `wheel_motorsLR`.

**VERIFIED — dynamics:** `d045.integrate_differential_drive()` uses the exact differential-drive arc, with a straight limit. D-045 scales both wheel increments when its body-center endpoint would leave the 1 m world, reducing yaw, encoder motion, and energetic effort together. D-058 instead:

1. clamps wheel increments;
2. integrates the complete arc;
3. retains complete unwrapped yaw;
4. projects the endpoint center into a heading-dependent legal rectangle;
5. records removed translation as evaluator-only slip.

At D-058 walls, wheels execute their full clipped command. Encoders still report that rotation, and pushing consumes full wheel effort. There is no mass, inertia, force, torque, traction coefficient, restitution, acceleration, stall-current, wall-heating, or swept contact model. Mid-transition penetration is disclosed. This is an explicit kinematic idealization, not validated hardware contact.

### Dock, beacon, and metabolism

**VERIFIED — contacts:** `d045._dock_contact()` transforms local body contacts `(0,+0.05)` and `(0,-0.05)` to world positions, then checks corresponding dock contacts at the same offsets about the room-center station. Both errors must be ≤0.01 m. Polarity matters: exchanging corresponding contacts at a 180° heading is not equivalent. Contact is sampled at the completed transition endpoint; crossing the dock between endpoints does not grant charge.

**VERIFIED — beacon:** `exp003.beacon_signal()` computes `1 / (1 + (d/0.25)^2)`. `sample_directional_beacon()` samples probe points 0.10 m out along heading and heading ±45°. It is noiseless, unoccluded, has no finite cutoff, and is independent of electrical uptake. ADR 0020 explicitly retains this model even inside/behind obstacles. The simulator uses pose and dock truth to generate local signals; the controller does not receive those truth inputs.

**VERIFIED — accounting:** both `D045Env.step()` and `D058Env.step()` implement the constitutive battery/thermal update; organism-level action selection is elsewhere. Thus the proposed boundary is partly a **future code separation**, not an already fully extracted metabolism module.

- Capacity 5,328 J; default energy 2,664 J.
- `wheel_effort = (abs(deltaL)+abs(deltaR))/(2*delta_max)`, clipped to [0,1].
- Electronics 0.15 W; wheel electrical effort scale 1 W; wheel-to-body heat scale 0 W.
- Load per full-effort transition: `(0.15+1)*0.1 = 0.115 J`; zero wheels still cost 0.015 J.
- `_charge_decision()` uses **post-step physical contact** and pre-step stored energy/latch state. Requested stored powers are 1.85 W, 0.925 W, and 0.37 W across bulk/taper regions below 90%/95%/full charge.
- Stored energy saturates at capacity; charger efficiency is 0.90; charger-input minus stored power becomes charging heat. Full-charge latch resumes at or below 98% SOC; leaving contact clears the charging latch.
- Temperature update uses 180 J/K capacitance, 0.25 W/K ambient exchange, ambient 23°C, electronics heat 0.15 W, and charging losses.
- Energy depletion terminates; protective thermal threshold is 60°C and hard threshold 65°C. A 45°C preferred ceiling is diagnostic, not termination.
- **Fainting at 5% is not implemented.** ADR 0018 explicitly lists fainting/dormancy as a non-goal. Death/failure and harness truncation must remain distinct.

### Controller, learner, and evidence separation

**VERIFIED — code:** `d052.D052Controller.command(observation, proposed_wheel_command)` passes proposals through in NORMAL, preempts locomotion at normalized energy ≤0.20, delegates return to `d050.D050SmoothController`, holds zero wheels in CHARGE, and yields at energy ≥0.80. Reacquisition/terminal-spin limits are programmed. `d049.reconstruct_source()` reconstructs station-relative geometry from **visible beacon measurements**, which is different from receiving hidden station coordinates. Terminal alignment relies on local contact/search, not hidden dock orientation.

`d046.D046ConsequencePredictor` contains 528 fresh learned scalars in a 66×8 quadratic predictor, with normalized LMS updates from visible observation/action/next-observation transitions. D-046 through D-048 remain shadow-only; they do not select, rank, veto or change the viability controller's actions. ADR 0018 forbids Level-1 decisions reading higher-level learned state by default. A backend must not blur these lineages.

`rng.RandomStreams.from_seed()` derives environment/policy NumPy generators through `SeedSequence.spawn`. D-046 uses an explicit local `random.Random(seed)` for external curriculum shuffling. D-045/D-058 themselves consume no placement/actuation RNG despite accepting Gym reset seeds. Seeds can affect the harness/policy while the physical backend is deterministic. Reproducibility includes causal-state cloning, branch-order invariance, diagnostic non-feedback, and no reseeding at invisible lifetime segmentation boundaries.

**VERIFIED — record inspection, not replay:** corrected D-059 records 320 classifiable S1_3M/U primary returns, all docked, `P_NOT_JUSTIFIED` and `FLOOR_S1_3M=SETTLED`. This is descriptive, programmed Level-1 performance in its frozen substrate. The corrected artifact was reported byte-identical after regeneration; the record explicitly warns that byte reproduction alone did not establish evaluator-definition validity. These results do not transfer to Pymunk contact dynamics.

## 4. RoboSim control path: what is bypassable and what remains

**VERIFIED — complete high-level bypass:** do not call `robosim.main.main()`. Instantiate `PhysicsWorld(config)` and `Robot(world)` and call `Robot.update(DriveCommand(left_power,right_power))` directly. Keyboard handling and `user_script.run()` then never execute. There is no internal navigation planner or homeostatic controller in the core.

**VERIFIED — low-level controller remains:** `Robot.apply_drive()` does all of the following on each tick:

```text
left/right = clamp(command, -1, +1)
desired_forward = (left + right)/2 * max_speed_px_s
desired_omega = (right - left) * max_speed_px_s / wheel_base_px
force = (desired_forward - chassis_forward_velocity) * drive_gain
torque = (desired_omega - chassis_angular_velocity) * torque_gain
lateral impulse = -lateral_velocity * mass * lateral_friction
```

It applies force at the chassis center, torque to the chassis, then steps Pymunk once. Default `drive_gain=50`; `torque_gain=10*body.moment`; full lateral-velocity cancellation per tick. There is P feedback, no integral/derivative term, no motor torque ceiling, no measured wheel-shaft state, no wheel radius, no separate left/right motor inertia, and no wheel contact patches.

**INFERENCE — approximate command mapping:** for an interval ΔT=0.1, one can map `u_i = delta_i / delta_max`, use `max_speed = r*delta_max/ΔT`, and hold the pair for six 1/60 s microsteps. This matches the **desired steady-state chassis twist**, not the actual wheel rotation or first-interval displacement. Feedback lag and damping remain. Calling this exact `wheel_motors_lr` compatibility would be false.

A physical motor servo is not automatically an illicit organism controller. It can legitimately belong to an actuator model if declared and calibrated. RoboSim's servo is an unvalidated **body-twist controller** masquerading as motor power. Its semantics must not silently enter Aweform.

To bypass that servo entirely, avoid `Robot.apply_drive()` and use `PhysicsWorld.space`/body directly with a separately defined actuator model. That discards RoboSim's main robot functionality. The surviving space/body/arena setup is small enough to implement directly against Pymunk, without retaining RoboSim's internal objects or licensing ambiguity.

## 5. Physics: simulated mechanics versus approximations

| Feature | VERIFIED RoboSim/Pymunk behaviour | Scientific implication versus D-058 |
|---|---|---|
| Chassis | One dynamic rectangular polygon | Finite mass/contact impulses are new assumptions |
| Mass/inertia | Shape mass 5; rectangle-derived moment, default 2166.6667 in mass×pixel² units | Aweform has no corresponding mass/inertia calibration |
| Drive | Chassis force and yaw torque from P error | Adds response lag/feedback; not independently rotating wheels |
| Acceleration | Force/mass and torque/inertia integrated by engine | Current free motion has no acceleration state |
| Floor friction | No floor contact geometry; global damping plus manually canceled lateral velocity | Not Coulomb wheel traction or a slip-ratio model |
| Wall friction | Robot shape 0.7, wall 0.5; engine default product 0.35 | Current walls are frictionless tangential constraints |
| Restitution | Robot 0.4, wall 0.6; default product 0.24 | Adds bounce absent from D-058 |
| Lateral slip | Fraction of chassis lateral speed canceled once per tick | Artificial, timestep-dependent suppression, not resolved wheel slip |
| Wheel geometry | Track scalar only; no wheel shapes or radius | Cannot establish wheel-ground interaction or shaft motion |
| World | Four static thick boundary segments; grid is visual | Interior obstacles require additional Pymunk shapes/layout work |
| Contact | Engine collision manifolds/impulse correction | Can alter yaw, preserve velocity state, and permit overlap |
| Integration | Position update, collision discovery/prestep, velocity update, cached impulses, iterative solver | Not exact differential-drive arc integration |
| Rendering | Rectangle/collision walls drawn separately | Drawn wall line width differs from collision capsule thickness |

Source: `physics.PhysicsWorld._create_robot/step`, `robot.Robot.apply_drive/_apply_lateral_friction`, `field.Arena._create_boundary_walls`, and Munk2D `src/cpBody.c:cpBodyUpdatePosition/cpBodyUpdateVelocity`, `src/cpSpaceStep.c:cpSpaceStep`.

**VERIFIED — integration detail:** Munk2D advances positions with existing velocities before integrating that tick's applied force into velocity. This explains zero first-step displacement from rest with nonzero post-step velocity. Forces/torques clear after the velocity update. RoboSim's encoders then integrate the **new endpoint velocity across the just-completed dt**, rather than measuring a simulated shaft or the body's actual integrated displacement.

**VERIFIED — units:** `PX_PER_CM=1.2` means 120 px/m. Defaults correspond to a 5.4 m arena, a 0.50×0.333 m body, a 0.333 m track, and nominal speed 1.667 m/s; these do not resemble the present Aweform embodiment. Configurable resizing is possible but does not calibrate physics. A matching visual scale would use 360 px arena, body `(21.6,25.8)` px, track 22.2 px, and speed approximately 34.8717 px/s.

**VERIFIED — engine defaults:** single-threaded `Space`, 10 solver iterations, collision slop about 0.1 **length units**. In default pixel units that is ≈0.833 mm; in an SI-meter adapter the same default would allow **10 cm overlap**. Slop, collision bias/persistence, restitution, damping, force limits, and timestep must be explicit scientific parameters, not inherited convenience defaults.

**INFERENCE:** Pymunk improves reuse of collision detection and response machinery; it does not automatically improve the model's biological relevance or hardware accuracy. A top-down Pymunk model also does not supply articulated wheel-leg suspension, jumping, height, gravity-supported floor loads, or 3D stairs.

## 6. Executed probes, headless compute, and repeatability

### Tests executed

| Run | VERIFIED result |
|---|---|
| RoboSim full suite, Python 3.12.14, Pymunk 7.2.0, Pygame 2.6.1, dummy SDL | 104 passed; measured statement coverage 81% (585 statements); renderer 33%, main 82% |
| RoboSim suite excluding renderer/main, Python 3.14.7, Pymunk 7.2.0 | 87 passed without Pygame installed/imported |
| Aweform `test_d045.py`, `test_d052.py`, `test_d058.py`, Python 3.14.7 | 47 passed; relevant D-058 base commit was fetched, so protected-source check was not skipped |

Final focused Aweform run used its locked top-level runtime versions: NumPy 2.5.2, Gymnasium 1.3.0, Matplotlib 3.11.1, pytest 8.4.2. This is not a claim that every transitive dependency or the full suite matched the official evidence environment. RoboSim benchmarks used source imports instead of installing the package, because its declared dependency forces Pygame installation even when core physics does not need it.

### Headless behaviour and benchmark method

**VERIFIED:** importing/constructing/updating `PhysicsWorld`, `Robot`, and sensors does not import Pygame, initialize a display, require events, or sleep. `main.main()` always calls `pygame.init()`, constructs a display, pumps events, draws, and `Renderer.tick(fps)` caps the loop (default 60 fps). It exposes no headless CLI/reset/episode runner.

Benchmarks used one process on Linux x86_64/glibc 2.39, AMD EPYC 9V74 VM with nine visible virtual CPUs. No parallel solver or GPU. Three trials per case, no simulation-time sleeping; reported medians. RoboSim used a deterministic 2,000-command repeated schedule producing wall contacts and turns. Core/all-sensor cases used 30,000 microsteps per trial at 1/60 s. Dummy-render cases used 1,000 frames per trial without `tick`. Aweform used 20,000 fixed wheel-command transitions per trial, initial full battery, no controller/learner, no seed selection, standard observation/accounting/telemetry.

| Workload | Median updates/s | Meaning |
|---|---:|---|
| RoboSim drive + physics, Python 3.14.7 / CFFI 2.0.0 | 91,714 | ≈1,529 simulated seconds per wall second at 60 Hz |
| RoboSim drive + all ideal sensors, same stack | 34,039 | ≈567× real time; ≈5,673 groups of six microsteps/s |
| RoboSim drive + physics, Python 3.12.14 / CFFI 2.1.1 | 97,875 | Separate runtime measurement |
| RoboSim drive + all sensors, Python 3.12.14 | 34,731 | Separate runtime measurement |
| RoboSim physics + sensors + actual renderer, SDL dummy, uncapped, Python 3.12.14 | 1,043 | Software/offscreen proxy; not a real-window/display benchmark |
| D045Env complete 0.1 s transitions, Python 3.14.7 | 14,997 | Includes boundary bisection, sensors, battery/thermal and telemetry |
| D058Env complete 0.1 s transitions, Python 3.14.7 | 40,583 | Includes endpoint projection, sensors, battery/thermal and telemetry |

RoboSim also reconstructed 1,000 fresh world/robot/sensor sets in approximately 0.057 s. This establishes cheap resets for its small default world, not a benchmark of 1,000 full scientific lifetimes.

**INFERENCE:** thousands of small episodes are feasible computationally. Ten million RoboSim core microsteps would be roughly 109 s at this median; with all sensors roughly 294 s. These extrapolations exclude learning, manifests, logging, checkpointing, richer collision scenes and memory growth. A complete Aweform/Pymunk adapter has not been benchmarked. The raw rates are **not equivalent workloads** and do not establish that Pymunk would accelerate current Aweform.

### Control/timestep observations

**VERIFIED — unchanged default RoboSim:** after one `dt=0.1` forward command `(1,1)` from rest, chassis displacement was exactly zero, endpoint forward velocity 200 px/s, and both encoders reported 1,711 counts. After six `dt=1/60` steps spanning 0.1 s, displacement was 6.666125 px and encoders reported 758 counts. For `(-1,+1)`, the respective headings were 0 and 0.333306 rad. These are different actuator/integration responses, not interchangeable stepping strategies.

**VERIFIED — resized config only, not an integration prototype:** with Aweform body/track/speed scaled to RoboSim pixels, six steps of `(1,1)` produced 0.009685790 m translation; exact current full-command expectation is 0.029059732 m. `(-1,+1)` produced 0.104711246 rad instead of π/10 = 0.314159265 rad. Resizing the drawing and using the normalized ratio leaves about a threefold first-interval response discrepancy.

**VERIFIED — wall push:** after 2,000 default forward steps, chassis velocity and yaw rate were effectively zero and cumulative encoders stopped advancing. This is ground-motion-inferred odometry; a wheel spinning against a wall is not represented. D-058's shaft readings and energetic effort deliberately remain nonzero under that condition.

### Determinism scope

**VERIFIED — limited binary identity:** five fresh, identically initialized 2,000-step runs per tested runtime produced identical SHA-256 hashes over 14 sampled numeric fields per step (pose, velocities, cumulative encoders, IMU and ranges). Ideal hash:

`f94865888687b32d73548bbcffbdfc6fb61cbae71fe78074ddb9525795e5cb6c`

With the caller resetting global `random.seed(771)` before each noisy run, all five hashes also matched:

`e050ad4a3704b1068bda3152be2cba9f5de35c20a247e0ad150a695dce22a047`

Those hashes matched across the tested 3.12/3.14 Linux processes as well. This demonstrates binary identity of the **sampled traces under these conditions**, not a general bitwise determinism guarantee for all scenes, machines, versions, or hidden engine state.

Consuming one unrelated `random.gauss` before every noisy step changed the trace to:

`0694de467a1a3b65ccdcd46141cf731b01c2a7067f1bb7370221ecb4032327dd`

**VERIFIED:** RoboSim noise pipelines share Python's module RNG, including Gaussian cached state. RoboSim uses no NumPy RNG in its core; Pymunk's deterministic numerical solver does not thereby provide independent sensor streams. Initial pose and topology are configuration-defined, not seed-defined. Fixed stepping removes wall-clock dependence from core physics; interactive human commands and callback failures remain different control inputs.

**VERIFIED — reset defect:** `WheelEncoder.reset()` zeros the count accumulator but does not call its noise pipeline's reset. A sampled nonzero bias of `0.00035219491030817607` survived reset unchanged. IMU/range resets do reset their bias, but none rewinds a dedicated RNG because there is none. Fresh construction is safer than reusing these sensors under a promised seeded reset.

**VERIFIED — cloning warning:** Pymunk `space.py` explicitly documents that collision-cache data and post-step callbacks are not fully copied. A small loaded-wall continuation probe showed a maximum sampled original/copy difference of approximately `3.3e-18`, numerically negligible but nonzero. Copying visible body state or using `Space.copy()` is not sufficient evidence for Aweform's exact OFF-vs-OFF branch continuation contract. Replay from a verified prefix is a possible alternative; its cost and equivalence need tests.

**INFERENCE — required reproducibility contract:** pin Python, backend wheel/build/hash, Munk version, numeric/solver/contact configuration and schema; stable ordered geometry construction; `Space(threaded=False)`; fixed microstep count; independent named RNG streams for policy, world and each sensor; fresh/reset-complete filters; no policy seed identifier in observations; trace digests and non-feedback/order/clone controls. Avoid shared global RNG reseeding as an adapter fix. Cross-platform agreement should have separately frozen tolerance rules; it must not be assumed from these Linux results.

## 7. Sensor and observation boundary

| RoboSim output | VERIFIED origin/model | Decision for current Aweform |
|---|---|---|
| `enc_left/right` | Inverse chassis kinematics, integrated endpoint velocity, unit-radius pixel-wheel, 537.7 ticks/revolution, cumulative integer truncation; optional count noise | **Reject unchanged.** Preserve actual shaft increments and current 1° per-interval quantization |
| `heading_deg` | Ideal mode reads exact body angle minus initial angle; noisy mode integrates noisy yaw velocity | Keep evaluator-only; no authorized organism IMU channel |
| `angular_vel_deg` | Exact simulated yaw rate converted to degrees plus optional noise | Exclude from organism absent a new ADR |
| Four ranges | Face-mounted capsule raycasts, self-filtered; px-to-cm conversion, clamp 5–200 cm, additive noise | Valid synthetic sensor concept, but currently unauthorized; do not instantiate/expose by default |
| `timestamp` | Harness simulation time | Exclude from current eight-channel observation; no new clock merely because packet contains it |
| Robot pose/velocity/world | Direct public properties and `robot.world.space` graph | Trusted backend/evaluator only |
| Dock/contact/beacon | Not provided | Preserve/build in Aweform's authorized physical transducer layer |

Noise uses the same numeric sigma across unlike units (encoder count increments, degrees/sec, cm); only bias drift scales with √dt. Encoder white-noise accumulation also changes with update rate. These presets are illustrative, not measured physical calibration. `RangefinderArray` changes the robot shape's collision filter group to 1 to exclude self; enabling extra sensors can therefore mutate world configuration. In multi-robot scenes a shared nonzero group could suppress unintended interactions. Geometry/query hit positions, shape identities and range-ray endpoints must remain evaluator-only even if a scalar range later becomes authorized.

The default `SensorPacket` is not an authorized Aweform observation. Allow-list construction should instantiate only the exact eight-channel DTO/array after combining six authorized external physical readings with energy/temperature. Do not pass a backend/env/Robot handle to the controller or learner. A typed DTO is a reviewable software boundary, not a Python security sandbox against hostile reflective code; that is not the threat model here.

## 8. Energy, charging, dock, and beacon ownership

**VERIFIED:** RoboSim contains no battery, energetic cost, charging, metabolism, viability, fainting or death logic in its executable source. There is no conflicting energy controller to disable. Pymunk mechanical work/kinetic energy does not define electrical draw or stored battery energy.

**INFERENCE — clean separation:** the physical backend produces unquantized actual shaft increments, any explicitly modeled actuator/consequence telemetry, and the **physical connection predicate**. Aweform's trusted constitutive layer computes electrical load, charge acceptance/taper/latch, temperature, internal observations and termination. Controller/learner receive only the resulting authorized observation.

For the existing D-058 model, the physical shaft model remains ideal: executed shaft deltas equal clipped requested deltas, even when chassis travel is blocked. Energy accounting therefore continues from these deltas, not body distance or RoboSim's inferred encoder counts. If later actuators can stall, actual shaft rotation alone is not enough to model electrical load: zero motion can consume power. Current effort-based energy remains an explicit engineered abstraction until a separately reviewed current/torque/loss model replaces it.

**INFERENCE — retain exact timing first:** one logical 0.1 s action; complete physical advancement; sample post-state contacts/beacon/shaft deltas; apply one constitutive energy/thermal update using the current pre-energy and post-contact rule; expose the next observation. Do not silently integrate charge over microstep contact duration, grant charge on any transient collision, or multiply energy by the microstep count. Those would be charger/timing changes.

**INFERENCE — dock representation:** a centered, traversable floor pad with paired local contact markers. Pose transformations and corresponding-pair distances are trusted physical-transducer calculations; individual errors and dock orientation never cross upward. Non-solid sensor shapes can provide overlap diagnostics, but collision of the whole hull with a pad is not an electrical connection. Preserve the current distance/polarity predicate initially; contact area/compliance/electrical resistance are separate future models.

Beacon generation can reuse the exact field/probe transformation from `exp003`. It uses backend truth internally and exports only L/F/R. Do not add range-to-dock, occlusion, attenuation, IMU, map or RoboSim navigation. A 2D floor pad can remain traversable while wall/obstacle shapes are solid.

## 9. Smallest recommended adapter boundary

**INFERENCE — interface design derived from the existing atomic Gym step:** retain a single authoritative logical advance rather than exposing a public `apply_action()` plus `step()` sequence that callers can accidentally reorder or repeat.

```python
# Conceptual sketch only; not implemented by this audit.
class PhysicalBackend:
    def reset(self, setup: PhysicalSetup, rngs: PhysicalRngs) -> PhysicalSample: ...
    def advance(self, command: WheelDeltaCommand) -> PhysicalSample: ...

# WheelDeltaCommand: desired signed delta L/R in radians, interval fixed at 0.1 s.
# PhysicalSample (trusted constitutive side):
#   actual shaft_delta L/R, beacon L/F/R, paired electrical-contact condition.
# Optional physical effort telemetry remains trusted/evaluator-only.

class EvaluatorView:
    def snapshot(self) -> PhysicalGroundTruth: ...
```

The backend configuration freezes `dt=0.1` and an internal substep count. Internal `Space.step(h)` is not a second organism action. Reset setup contains evaluator pose/world parameters; seed/geometry are not included in organism observations. Existing legality checks and zero previous-wheel observation at reset must survive.

The Aweform wrapper retains `reset(*,seed,options)` and `step(action)`; it owns lifecycle, normalized physiology, eight-channel float32 packing, zero reward, empty info, termination versus truncation, and logging attribution. A separate evaluator capability reads pose, velocity, contacts, world geometry and solver state. The controller and learner never receive that capability or callbacks that close over it.

Rendering consumes evaluator snapshots after the transition and remains causally inert. Reuse Aweform's canonical `development_visualizer.py` data adapter; do not adopt RoboSim's game loop/HUD as the experiment scheduler.

This shape can later be matched by a hardware implementation reporting actual measured interval shaft deltas and authorized signals. Simulated perfect wheel increments are not a claim that hardware can reproduce exact open-loop motion. Hardware latency, zero-command braking/coasting, actuator feedback, and physical energy calibration would need their own contract and authorization.

## 10. Compatibility matrix

| Requirement | RoboSim unchanged | Thin adapted RoboSim | Direct Pymunk adapter | Evidence/status |
|---|---|---|---|---|
| Bypass keyboard/example autonomy | Yes via core classes | Yes | No such autonomy | VERIFIED |
| External bilateral input each step | Normalized power-like inputs | Yes, with mapping | Yes with defined actuator | VERIFIED core / INFERENCE adapter |
| Exact current rad/0.1 s semantics | No | Replace actuator path | Must implement explicitly | VERIFIED mismatch |
| No hidden navigation/energy policy | Core has neither | Yes | Yes | VERIFIED |
| No undeclared actuator feedback | No: chassis P control | Must declare/replace | Must define | VERIFIED |
| Eight observations, no privileged leakage | Default packet fails | Allow-list wrapper | Allow-list wrapper | INFERENCE feasible |
| Current shaft/slip observation | No | Replace encoders | Own shaft model required | VERIFIED mismatch |
| Rigid hull/collisions | Yes | Configurable | Native engine primitive | VERIFIED |
| Real wheel-floor traction/slip | No | Significant new model | Significant new model | VERIFIED absence / UNKNOWN fidelity |
| D-058 full-yaw endpoint wall identity | No | Own wall law or new ADR | Own wall law or new ADR | VERIFIED incompatibility |
| Headless/no Pygame initialization | Core yes; CLI no | Yes | Yes | VERIFIED core and Pymunk |
| No mandatory graphics dependency | Package declares Pygame | Packaging change needed | Pygame optional | VERIFIED metadata |
| Faster than real time | Yes, tested | Integrated workload untested | Integrated workload untested | VERIFIED / UNKNOWN |
| Owned sensor RNGs/seeded reset | No | Replace/inject RNG models | Can design explicit streams | VERIFIED / INFERENCE |
| Exact branch-copy continuation | Not established | Must prove | Must prove/replay | UNKNOWN / NEEDS TESTING |
| Aweform physiology ownership | No built-in conflict | Straightforward separation | Straightforward separation | VERIFIED absence / INFERENCE |
| Existing beacon/paired dock | Absent | Custom transducers | Custom transducers | VERIFIED |
| Python 3.14.7 | Core executed; full package install untested | Pygame issue remains | Pymunk executed | VERIFIED limited |
| Native Apple Silicon | Pygame cp314 wheel absent | Source build/packaging tests | Pymunk cp314 arm64 wheel listed | VERIFIED artifacts / UNKNOWN runtime |
| Clear reusable project license | No | Requires licensing | MIT Pymunk/Munk2D | VERIFIED blocker |
| Historical experiment continuity | No automatic transfer | New substrate/version | New substrate/version | INFERENCE required |

## 11. Software quality, dependencies, maintenance and licensing

**VERIFIED — RoboSim:** 585 executable statements measured by coverage; a small readable dataclass-based package, ten test modules, separated renderer/core imports. Full tests passed, but scientific properties are not covered by that fact: encoder tests validate the chosen formula, turn tests sometimes check only that angle is nonzero, and no tests establish measured motor dynamics, seeded independent episodes, current Aweform information closure or backend interchangeability. No tracked CI workflow, LICENSE, changelog or API compatibility promise appears in the audited tree. Config dataclasses perform no comprehensive physical/finite-value validation comparable to Aweform's configs.

GitHub's inspected main history comprises 23 commits from 24–25 March 2026. Main's latest commit is 25 March; repository metadata reports last push 26 March. This is a short initial development burst with no later main commits observed, not proof the maintainer has abandoned it. Version is 0.1.0; `pymunk>=7.0` and `pygame>=2.5` have no upper bounds. Its lockfile freezes Pymunk 7.2.0/Pygame 2.6.1/CFFI 2.0.0, but consumers do not inherit those locks automatically.

**VERIFIED — Pymunk:** MIT license, compiled Munk2D MIT code, CFFI direct dependency, source tests/CI/release machinery, established external engine API. Current PyPI metadata inspected on the audit date reports Pymunk 7.3.0, with CPython 3.14 macOS arm64 wheels. This audit intentionally executed 7.2.0, which also has cp314 arm64 artifacts in RoboSim's lockfile. Any 7.3 migration requires its own version-pinned conformance, not reliance on `>=7.0`.

**VERIFIED — platform constraint:** Aweform requires exactly Python 3.14.7. RoboSim allows ≥3.11, so source-language compatibility is not the issue. Pygame's inspected current 2.6.1 artifact set includes arm64 macOS wheels through cp313, **none for cp314**. A source build may work but was not tested; do not call the full RoboSim package plug-and-play on Flo's canonical stack. Direct Pymunk was installed and executed on 3.14.7 Linux. macOS/Apple Silicon execution remains untested here.

Installed Linux 3.12 sizes were approximately 4.5 MB for Pymunk, versus 22 MB Pygame plus 15 MB bundled Pygame native libraries, excluding shared CFFI and metadata. This is a platform-specific footprint observation, not a universal package-size claim. Pygame's LGPL-2.1 licensing is separate from RoboSim's missing license and irrelevant if not depended on.

**INFERENCE — maintenance verdict:** RoboSim can technically be wrapped without a fork if one keeps its public core classes, accepts its servo and replaces observations externally. But exact actuator/shaft semantics, per-sensor RNG injection and mandatory Pygame packaging require replacement/subclassing or upstream changes. Once those are removed, almost all reused value is a thin Pymunk space/body/arena constructor. A long-lived RoboSim fork offers little advantage. Prefer direct Pymunk and a small owned scientific adapter; do not copy unlicensed RoboSim source into Aweform.

## 12. Scientific risks and preservation obligations

| Change axis | RoboSim default/adapted migration could change | Required treatment |
|---|---|---|
| Embodiment | Hull size/orientation, default track, absent versus scalar wheels, mass/inertia | Freeze current morphology; label mass/inertia estimates separately |
| Physics/actuation | Exact arc → feedback/inertia; wall projection → impulses; friction/bounce; timestep lag | New substrate ID and parameter contract; free/contact calibration gates |
| Sensors | Shaft increments → body odometry; added heading/range/time; noise/quantization | Preserve eight channels and semantics; explicit ADR for any sensor change |
| Controller | Example AUTO code; terminal overshoot; zero-command braking; emergency fallback | Bypass demo/CLI; hold Aweform controller bytes fixed for re-baseline |
| Learner/memory | New plant distribution, hidden velocity/contact cache, different observation consequences | Keep mechanism fixed and attribution explicit; retraining is a separate change |
| Ecology | Different arena size, thick walls, dock defaults, added obstacles/occlusion | Match room/dock/layout independently from physics changes |
| Physiology | Use chassis travel/kinetic work for load; microstep uptake; altered stopping | Preserve current energy/thermal formula and timing before separate changes |

**INFERENCE — particularly important risks:**

- Replacing shaft deltas with RoboSim odometry can awaken D-055's zero-encoder stall predicate at walls. An apparent controller improvement/failure would then be a sensor/actuator semantic change, not the same floor on better physics.
- Chassis inertia and velocity persist across transitions. The current eight channels do not directly expose them. This can create a new partially observable prediction problem; a larger learner's apparent necessity could be simulator-induced state aliasing.
- Full Pymunk contacts can alter yaw and trap/pivot the body differently from D-058's full-yaw projection. Old homing success rates do not establish the new floor.
- Solver slop, initialization overlap, collision ordering, warm-start caches and curved-obstacle tessellation can create threshold/contact artifacts. Reproducibility can faithfully reproduce a modeling error.
- Changing all physics, encoder semantics, noise, room geometry and controller gains together cannot support single-factor attribution.

**Invariants that should survive:** no hidden truth or evaluator labels in policy/plastic updates; exact authorized channel schema; zero reward/empty info; continuous lifetime state; explicit seeded ownership; physiology/viability ownership; learner–Level-1 separation; negative-result preservation; stage/executable SHA and artifact provenance; appropriate matched controls.

**Invariants that do not survive automatically:** exact trajectories, old wheel/body boundary response, full-yaw contact, D-055 dormancy, docking timing, energy draw over a different trajectory, support/aliasing of the shadow predictor, old calibrated return margins and branch-clone identity.

All D-045…D-059 and historical EXP results stay bound to their original sources/substrates. Retain those modules and replays. No retrospective Pymunk rerun or relabeling creates historical continuity. If physics changes, new re-baseline records precede scientific claims; changes to controller, learner, sensors or ecology are independently identified or factored.

## 13. Alternatives and migration effort

| Option | Strength | Cost/risk | Recommendation |
|---|---|---|---|
| A. Current custom Aweform | Exact declared semantics, fast, small, strong provenance; D-058 already sufficient for room walls | Bespoke curved-obstacle/contact projection and conformance can become expensive; limited physical fidelity | Keep as current reference and historical oracle |
| B. Aweform + RoboSim + Pymunk | Ready interactive demo, rectangle, wall arena, sensor examples; headless core possible | Unlicensed project; actuator/encoder mismatch; global noise; mandatory Pygame; replace much of useful code | Reject as production dependency at this revision |
| C. Aweform + Pymunk directly | Licensed collision engine; no obligatory renderer/controller/sensor suite; explicit owned boundary | Still requires actuator model, shaft state, transducers, energy split, reproducibility and calibration | Conditional candidate for a small conformance experiment |

**INFERENCE — scope estimate, experienced engineer, not an observed schedule:**

| Work | Indicative effort |
|---|---|
| Tiny direct-Pymunk fixed-vector conformance prototype and report | 1–3 focused engineer-days |
| Reviewable prospective substrate ADR/adapter contract and scientific attribution | 1–2 days, potentially longer for independent reviews |
| Additive production adapter/wrapper and matched floor re-baseline | Approximately 1–2 engineer-weeks after gates pass |
| Robust force/traction/motor-current/real-hardware calibration or exact causal snapshots | Several additional weeks or unknown; outside the tiny prototype |

RoboSim adaptation might make a demo quicker, but no evidence shows it reduces the production work above. Maintaining both old/new substrates adds cost initially.

**Custom code potentially retired from the active future backend:** D-045's boundary bisection, D-058 endpoint room projection, future bespoke general collision detection/response, some obstacle contact geometry and contact-manifold telemetry construction. Retain historical source for reproduction. The exact free-space differential-drive equations may remain as an actuator/oracle even with Pymunk. Beacon, paired electrical-contact semantics, shaft quantization, energy/thermal/charger rules, controllers, learners, provenance and visualization data adapters remain custom by design. Direct Pymunk does not remove them.

If the requirement is **exact ADR-0019/0020 yaw-dominant endpoint projection**, using Pymunk only for geometry queries still leaves a bespoke projection/contact solver. A `KINEMATIC` body is not a shortcut to wall response: it does not react to static-wall collision forces. A dynamic Pymunk collision model may retire more custom collision code, but requires acknowledging changed contact physics. There is no verified path that simultaneously eliminates all custom contact logic and preserves every current contact invariant.

## 14. Smallest proof of concept — design only, not implemented

**INFERENCE — recommendation:** direct Pymunk first. RoboSim-specific PoC is not justified before its license is clarified and its actuator semantics deliberately accepted. The audit's RoboSim probes are tests of unchanged software/configuration, not an Aweform adapter or migration implementation.

Pre-register one tiny **engineering conformance** protocol, not an autonomy or learning study. Use explicit fixed starts and commands with no official evidence seeds. No obstacle curriculum, controller, learner, visualizer rewrite, or new organism sensor.

### Frozen fixture

1. A 3 m room, 0.180×0.215 m rectangle, r=0.045 m, b=0.185 m, current command envelope, fixed 0.1 s logical interval. Pymunk 7.2.0 and Python 3.14.7 initially because those were executed here; changing that pin is a separate conformance condition.
2. Explicit SI length/time units, fixed ordered static geometry, `Space(threaded=False)`, gravity zero, restitution and tangential wall friction zero; explicitly freeze collision slop/bias/iterations. Suggested first engineering slop 0.0001 m; this is a proposed tolerance choice, not a measured physical property.
3. **Declare the actuator before coding:** preserve ideal velocity-controlled wheel shafts, so actual shaft increments are the clipped commands independent of chassis slip. Ten fixed microsteps per interval initially. A drive model imposing chassis twist is an idealized actuator, not a claimed torque/traction model. If using a dynamic collision body, freeze a fixture mass/inertia and clearly label those as engineering test parameters; do not borrow RoboSim's 5-unit mass as a measured Aweform value.
4. No inherited RoboSim P controller, IMU, ranges, clock channel or global sensor RNG. Beacon and paired contact transformations unchanged; energy/thermal update external.
5. One command advance produces one next eight-channel observation. Ground-truth pose/contact manifold/velocities and comparison errors are evaluator-only.

**Important scope fork:** ordinary impulse-resolved Pymunk contact can change yaw. That prototype is a proposed **new contact substrate**, even when shafts and sensing remain unchanged. If exact full-yaw endpoint projection is mandatory, use the existing law with Pymunk geometry queries and report that the hoped-for solver retirement was not achieved. Never treat failure to reproduce D-058 contact as a harmless numerical tolerance.

### Predefined gates

All numerical gates below are proposed engineering criteria to freeze before execution, not established scientific constants.

| Gate | Pass criterion | Fail consequence |
|---|---|---|
| Headless installation | Native canonical Python import/run with no Pygame dependency, display/event initialization or sleeping; also test Flo's macOS arm64 before adoption | Keep current backend |
| Action/unit fidelity | Finite commands; independent clipping; exactly one 0.1 s logical interval; actual shaft deltas match declared ideal response to 1e-12 rad | No compatibility claim |
| Calibration vectors | `(+a,+a)`, `(-a,-a)`, `(-a,+a)`, `(+a,-a)`, `(+a,+b)` plus zero, over-range and near-quantum inputs; a=delta_max, b=a/2; headings 0, ±π/2, π | Stop for sign/scaling/timing defect |
| Free-space body consequence | Against `integrate_differential_drive`, one-interval position ≤1e-5 m error, yaw ≤1e-5 rad; symmetry and no spin translation beyond tolerance | Reject actuator/integrator candidate or explicitly propose a different response model; no post-result tolerance widening |
| Interval convergence | Compare ten versus twenty microsteps: ≤0.1 mm free-space and ≤0.5 mm contact pose differences on the frozen table; contact-state disagreement outside a declared 0.5 mm threshold band is failure | Numerical model not ready |
| Contacts | Fixed head-on, oblique, corner and spin-at-wall cases; no tunneling; endpoint penetration ≤0.5 mm; finite states; evaluator discloses any yaw suppression versus D-058 | Fail geometry/numerics or require explicit new contact boundary |
| Shaft/slip semantics | Wall push retains clipped shaft deltas and current encoder quantization while body travel is constrained; no body-derived encoder cue | Reject current-contract compatibility |
| Dock predicate | Aligned, just-inside/outside, ±polarity, and between-endpoint crossing cases match existing paired predicate away from frozen numerical tolerance bands | Reject transducer |
| Physiology isolation | Identical injected shaft/contact sample sequences produce identical battery, heat, latch and failure updates to existing equations; zero wheels still pay electronics load; connection alone does not force energy increase | Reject organism boundary |
| Information closure | Exact eight float32 channels, zero reward, empty info; no simulator/evaluator handle, pose, heading, pad coordinates, timestamp or contact manifold in controller/learner inputs | Stop; boundary breach |
| Seed/reset ownership | Same declared setup/streams reproduce ten fresh-reset traces; independent stream draws cannot alter each other; reordered episode/diagnostic execution does not change traces | Reject reproducibility contract |
| Branching | Either replay-from-prefix continuation or approved complete clone passes OFF-vs-OFF/order/source-nonmutation; `Space.copy()` alone is not accepted | No causal-branch experiments on backend |
| Scale/compute | 1,000 independent reset-plus-fixed-command episodes; no retained old bodies/filters; suggested throughput ≥10,000 microsteps/s and ≥1,000 complete logical transitions/s including physiology | Treat as an engineering failed candidate pending cause; thresholds are proposed, not proof of scientific superiority |
| Engineering value | At most one small backend module and one wrapper seam; no RoboSim fork, no new navigation/learning/sensor stack; document which bespoke collision work was actually avoided | Prefer current substrate if effort does not decrease |

The first fixture can remain deterministic/seedless because current transducers are noiseless; the adapter must still provide owned reset streams without leaking seed IDs. A future noise condition would require dedicated streams and separately frozen distributions, not merely varying seeds and pretending the world is stochastic.

Passing these gates authorizes considering a substrate decision, not transferring old performance claims. Follow with a fresh, matched **unchanged Level-1 floor** re-baseline on new legal development support after governance approval. Retain room/dock/observations/accounting, report collision/actuator changes explicitly, keep the learner shadow-only, and measure any new floor failures before proposing controller fixes. Full contact identity with D-058 is a different, stricter requirement and may remove the reason to migrate.

## 15. Recommended next Aweform development step

**INFERENCE:** before spending on S2-B's bespoke curved-obstacle projection implementation, make a narrow substrate decision: is the next question specifically about the frozen yaw-dominant kinematic world, or does it need a reusable collision-resolving rigid-body world? The existing obstacle ADR cannot silently authorize force/torque/friction/contact changes.

If the frozen kinematic question remains the priority, continue on the current substrate. If reducing general collision engineering is the priority, approve the small direct-Pymunk conformance protocol above, additively and with the existing simulator kept as reference. Do not migrate controllers/learning, add sensors, build a RoboSim fork, or claim improved realism. A prospective ADR/amendment and independent exact-candidate review precede adoption of any changed durable physical boundary.

This audit's recommendation is therefore: **keep Aweform; reject RoboSim dependency adoption; test direct Pymunk only against an explicit engineering/scientific contract.** The claim that this will save total engineering effort remains conditional on that experiment.

## Source index

### Aweform — all links pinned to audited main

- [AGENTS.md](https://github.com/PiFlow/aweform/blob/e11ad91b3b7c649185bd1298ad5f3a791be571f8/AGENTS.md)
- [Development index](https://github.com/PiFlow/aweform/blob/e11ad91b3b7c649185bd1298ad5f3a791be571f8/development/INDEX.md)
- [ADR 0017](https://github.com/PiFlow/aweform/blob/e11ad91b3b7c649185bd1298ad5f3a791be571f8/docs/adr/0017-v0.5-direct-differential-drive-centered-dock-boundary.md)
- [ADR 0018](https://github.com/PiFlow/aweform/blob/e11ad91b3b7c649185bd1298ad5f3a791be571f8/docs/adr/0018-three-layer-developmental-architecture-and-innate-viability-floor.md)
- [ADR 0019](https://github.com/PiFlow/aweform/blob/e11ad91b3b7c649185bd1298ad5f3a791be571f8/docs/adr/0019-v0.5-physical-arena-wall-contact-boundary.md)
- [ADR 0020](https://github.com/PiFlow/aweform/blob/e11ad91b3b7c649185bd1298ad5f3a791be571f8/docs/adr/0020-v0.5-round-interior-obstacle-room.md)
- [D045Env and physical/bookkeeping functions](https://github.com/PiFlow/aweform/blob/e11ad91b3b7c649185bd1298ad5f3a791be571f8/src/aweform/d045.py)
- [D058Env](https://github.com/PiFlow/aweform/blob/e11ad91b3b7c649185bd1298ad5f3a791be571f8/src/aweform/d058.py)
- [D046ConsequencePredictor](https://github.com/PiFlow/aweform/blob/e11ad91b3b7c649185bd1298ad5f3a791be571f8/src/aweform/d046.py)
- [D050SmoothController](https://github.com/PiFlow/aweform/blob/e11ad91b3b7c649185bd1298ad5f3a791be571f8/src/aweform/d050.py)
- [D052Controller](https://github.com/PiFlow/aweform/blob/e11ad91b3b7c649185bd1298ad5f3a791be571f8/src/aweform/d052.py)
- [Beacon transducer](https://github.com/PiFlow/aweform/blob/e11ad91b3b7c649185bd1298ad5f3a791be571f8/src/aweform/exp003.py)
- [D059 record](https://github.com/PiFlow/aweform/blob/e11ad91b3b7c649185bd1298ad5f3a791be571f8/development/D-059-v05-s1-level1-floor-rebaseline.md)
- [Reproducibility contract](https://github.com/PiFlow/aweform/blob/e11ad91b3b7c649185bd1298ad5f3a791be571f8/docs/reproducibility.md)

### RoboSim — all links pinned to audited main

- [Robot.apply_drive/update](https://github.com/AnwarMP/RoboSim/blob/86971d67a1eb0049653ebe842507a4ff30cb338d/src/robosim/robot.py)
- [PhysicsWorld](https://github.com/AnwarMP/RoboSim/blob/86971d67a1eb0049653ebe842507a4ff30cb338d/src/robosim/physics.py)
- [Configuration](https://github.com/AnwarMP/RoboSim/blob/86971d67a1eb0049653ebe842507a4ff30cb338d/src/robosim/config.py)
- [EncoderPair/WheelEncoder](https://github.com/AnwarMP/RoboSim/blob/86971d67a1eb0049653ebe842507a4ff30cb338d/src/robosim/sensors/encoders.py)
- [IMU](https://github.com/AnwarMP/RoboSim/blob/86971d67a1eb0049653ebe842507a4ff30cb338d/src/robosim/sensors/imu.py)
- [Rangefinders](https://github.com/AnwarMP/RoboSim/blob/86971d67a1eb0049653ebe842507a4ff30cb338d/src/robosim/sensors/rangefinder.py)
- [NoisePipeline](https://github.com/AnwarMP/RoboSim/blob/86971d67a1eb0049653ebe842507a4ff30cb338d/src/robosim/sensors/noise.py)
- [Interactive main loop](https://github.com/AnwarMP/RoboSim/blob/86971d67a1eb0049653ebe842507a4ff30cb338d/src/robosim/main.py)
- [Package metadata](https://github.com/AnwarMP/RoboSim/blob/86971d67a1eb0049653ebe842507a4ff30cb338d/pyproject.toml)
- [Lockfile](https://github.com/AnwarMP/RoboSim/blob/86971d67a1eb0049653ebe842507a4ff30cb338d/uv.lock)

### Engine and distribution sources

- [Pymunk 7.2.0 Space implementation: stepping/copy caveats](https://github.com/viblo/pymunk/blob/3ef8f6e304fdc09e16c8ca2cfb1a3aa88a9399bc/pymunk/space.py)
- [Pymunk 7.2.0 license](https://github.com/viblo/pymunk/blob/3ef8f6e304fdc09e16c8ca2cfb1a3aa88a9399bc/LICENSE.txt)
- [Munk2D position/velocity integration](https://github.com/viblo/Munk2D/blob/ade7ed72849e60289eefb7a41e79ae6322fefaf3/src/cpBody.c)
- [Munk2D collision/impulse stepping](https://github.com/viblo/Munk2D/blob/ade7ed72849e60289eefb7a41e79ae6322fefaf3/src/cpSpaceStep.c)
- [Munk2D license](https://github.com/viblo/Munk2D/blob/ade7ed72849e60289eefb7a41e79ae6322fefaf3/LICENSE.txt)
- [Official Pymunk overview](https://www.pymunk.org/en/latest/overview.html)
- [Official Pymunk API](https://www.pymunk.org/en/latest/pymunk.html)
- [Pymunk distribution/artifacts](https://pypi.org/project/pymunk/)
- [Pygame distribution/artifacts](https://pypi.org/project/pygame/)

The linked live docs/distribution metadata can change; the source commits and executed versions above are the audit's physical-code authority.
