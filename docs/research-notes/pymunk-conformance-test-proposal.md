# Proposed direct-Pymunk conformance tests for Aweform

- **status:** research proposal only; non-authorizing and unexecuted
- **date recorded:** 2026-10-08
- **reference Aweform SHA:** `e11ad91b3b7c649185bd1298ad5f3a791be571f8`
- **basis:** [RoboSim/Pymunk physical-substrate audit](robosim-pymunk-physical-substrate-audit.md)

## Recommendation and question

**INFERENCE:** test Pymunk directly, without a RoboSim dependency, before deciding whether a new physical substrate saves engineering work. Preserve the current simulator as the reference and historical executable. Start with an isolated, headless body and fixed commands; do not begin with a docking controller, learner, or full developmental episode.

**VERIFIED:** the audited RoboSim adds chassis velocity/yaw-rate P controllers and chassis-derived encoders that differ from Aweform's wheel-radian and shaft-observation contract. Its audited revision has no declared license. Pymunk supplies collision mechanics, but no ready wheel/traction model. Current D-058 already has ample component throughput; acceleration is not an established reason to migrate.

**UNKNOWN / NEEDS TESTING:** whether a small direct-Pymunk adapter can preserve Aweform's organism boundary while reducing the cost of future collision geometry and response. Passing calibration alone will not establish that benefit or hardware fidelity.

This document proposes engineering tests and decision gates. It does not authorize implementation, dependencies, changed contact physics, sensors, a D-stage, or experiments on reserved support. A later implementation task must name its exact base and freeze a concrete fixture/protocol. Adoption of changed durable physics requires the appropriate ADR/amendment and independent review under [ADR 0013](../adr/0013-model-agnostic-independent-review-governance.md). Merging this research note would not satisfy that gate.

## Ownership to preserve

| Owner | Proposed responsibilities |
|---|---|
| Physical backend | Rectangle/world geometry, declared actuator response, pose advancement, collisions, actual wheel-shaft increments, physical beacon/contact transducers |
| Aweform constitutive layer | Stored energy, electrical effort costs, charger acceptance/taper/latch, thermal state, internal observations, termination/viability |
| Aweform controller/learner | Existing action selection, Level-1 floor, memory and authorized plastic updates; no backend handles or new observations |
| Evaluator/harness | Ground-truth pose, velocities, contact manifolds, configuration/seed identity, trace errors and timing; these must not feed back |

Keep one atomic logical advance: a signed pair of desired wheel radians advances exactly one 0.1 s interval and produces a trusted physical sample. A separate Aweform wrapper applies physiology once, then builds the authorized eight-channel observation. Physical connection is an input to charging rules, not a command to increase energy. Do not expose separate public action/step calls that can accidentally be repeated or reordered.

## Resolve the contact-model fork before a room prototype

| Candidate | What the test could establish | Limitation |
|---|---|---|
| Preserve D-058 full-yaw endpoint projection; use Pymunk for geometry queries | Geometry support under the existing contact law | Bespoke projection/contact response remains; no automatic solver-retirement benefit |
| Dynamic body with Pymunk impulse-resolved contact | Reusable collision response on a proposed new substrate | Contact can change yaw and trajectories; requires a changed physical boundary and fresh baselines |

Neither a `KINEMATIC` body nor rescaling RoboSim automatically provides current wall semantics. Do not silently select the second candidate and describe it as numerical improvement. The empty-space calibration tranche below can proceed as a proposed fixture without deciding that fork; room/contact execution must freeze the choice first.

## Proposed fixture to freeze before implementation

| Parameter | Proposed initial setting |
|---|---|
| Runtime | Python 3.14.7; Pymunk 7.2.0 initially, matching the executed audit condition; record wheel/build hash and Munk engine version |
| Units/body | Metres, seconds, radians; rectangle 0.180 m long by 0.215 m wide; local +x forward; wheel radius 0.045 m, track 0.185 m |
| Action | Independent clipping to ±`0.6457718232379019` rad; no normalization to motor power; reject non-finite commands using the existing contract |
| Clock | 0.1 s logical interval, initially ten fixed 0.01 s microsteps; never use elapsed wall time |
| Shaft assumption | Ideal velocity-controlled shafts; actual per-interval shaft deltas equal clipped commands, including at a wall; not a torque/traction model |
| World | Empty space for first calibration; then 3 m square room, fixed ordered geometry, centered traversable dock markers |
| Engine | `Space(threaded=False)`; gravity zero, damping 1, restitution zero, tangential wall friction zero; explicitly set solver iterations 10 and collision slop 0.0001 m |
| Dynamic fixture, if selected | Test mass 1 kg; uniform-rectangle moment `m*(0.180**2+0.215**2)/12`; engineering parameters, not measured robot properties |
| Transducers | Existing three noiseless beacon probes, corresponding paired dock contacts, 1° shaft-delta quantization with ties away from zero; no ranges/IMU/clock channel |
| Physiology | Existing energy, thermal, charger and termination equations outside Pymunk; update once after endpoint contact sampling |

The implementation proposal must also freeze the actuator's exact microstep update order, collision bias/persistence and wall construction, initial velocity, starts, command table, run lengths, output schema, and trace comparison rules. No hidden chassis PID is permitted. Any imposed chassis twist must be declared as an idealized drive model and checked for how it interacts with collision impulses. This note does not pretend these unresolved choices are already an executable protocol.

Use independent analytical/metamorphic checks alongside the existing differential-drive helper. Reusing the same helper on both sides is insufficient protection against a common sign/unit error. Use fixed engineering fixtures first; check any subsequently selected development seed support against all existing reservations. Do not reserve new evidence seeds in this research note.

## Tranche 1: smallest useful body test

The first implementation candidate should contain only an isolated physical backend, a fixed-command probe, and evaluator output. Its deliverable is motor calibration, headless operation and a reproducibility manifest. It should not run an organism controller or learner.

Let `a = 0.6457718232379019` rad and `b = a/2`. In empty space, reset to the same stationary pose before each vector, and test headings 0, ±π/2, and π. Repeat vectors at 0.25, 0.5 and 1 times these amplitudes.

| Command | Independent expected consequence at heading 0 |
|---|---|
| `(0,0)` | No translation or yaw |
| `(+a,+a)` | Forward `r*a = 0.029059732045705586` m; no yaw |
| `(-a,-a)` | Equal reverse travel; no yaw |
| `(-a,+a)` | Positive yaw `2*r*a/track = π/10`; no center translation |
| `(+a,-a)` | Equal negative yaw; no center translation |
| `(+a,+b)` | Positive mean travel and negative yaw, following the declared differential-drive arc |
| `(+b,+a)` | Mirrored arc with positive yaw |

Also test independent over-range clipping, one stationary wheel, tiny signed inputs, and values immediately either side of ±0.5 encoder quantum. Expected body motion uses unquantized shaft rotation, not quantized observations.

All following tolerances are **proposed engineering gates**, to freeze before results are inspected:

| Test | Pass criterion | Failure interpretation |
|---|---|---|
| Headless import/run | No Pygame dependency/import, display/events, sleep or interactive input; canonical Python succeeds | Packaging/control coupling blocks the candidate |
| Action/timing | One action advances exactly 0.1 s; shaft deltas match independently clipped requests to 1e-12 rad | Unit, clipping, actuator or timing defect |
| One-interval calibration | Position error ≤1e-5 m and yaw error ≤1e-5 rad against analytic free-space arcs; spin translation within position tolerance | Reject the actuator/integrator candidate or propose a different response model explicitly |
| Symmetry | Reversing equal wheels reverses travel; swapping wheels mirrors yaw; rotated starts rotate displacement | Coordinate/sign defect, even if one helper comparison passes |
| Microstep convergence | Ten versus twenty microsteps differ by ≤0.1 mm position and ≤1e-4 rad yaw in empty space | Fixed-step numerical setup not ready |
| Fresh reset | Ten independently constructed runs of a frozen 1,000-interval vector schedule produce equal declared traces on the pinned stack | Incomplete reset or reproducibility defect |

Record every case, including failures. Do not tune a tolerance after looking at results. Trace identity on the tested stack does not imply cross-platform bitwise determinism. Test native macOS arm64 before dependency adoption; wheels being available is not runtime validation.

**Stop gate:** if this tranche fails, fix or reject the physical candidate before adding contact, physiology, or control. A successful motor demo alone is not a migration recommendation.

## Tranche 2: boundaries and physical contact

Only after freezing the contact-model choice, add room walls and the existing dock/beacon transformations. Keep fixed actions and evaluator-only diagnostics. Test physical samples and physiology separately before composing them.

| Test | Frozen cases to include | Proposed pass criterion |
|---|---|---|
| Walls | Head-on push/reverse, oblique motion, corner approach, opposed-wheel spin near each wall; replay the D-058 conformance cases | Finite state and endpoint penetration ≤0.5 mm for both candidates; for the dynamic candidate also require no hull tunneling across the declared microstep sweep checks; report yaw/travel differences from D-058 explicitly |
| Contact convergence | Repeat the fixed contact table at ten and twenty microsteps | Position difference ≤0.5 mm and yaw difference ≤5e-4 rad; no contact-predicate disagreement outside a declared 0.5 mm threshold band |
| Shaft versus body slip | Sustain a wall push while measuring body travel and wheel samples | Shaft deltas and current quantized encoders remain nonzero as commanded; no chassis-derived stall encoder is substituted |
| Electrical contact | Aligned paired contacts; corresponding errors just inside/outside 0.01 m; 180° reversed polarity; one-contact-only states; crossing the dock between sampled endpoints | Existing paired predicate matches away from the numerical threshold band; transient crossing alone does not grant endpoint charging |
| Beacon | Fixed poses/headings around the dock with contacts false/true | Existing L/F/R transformation agrees; no occlusion, ranges or cutoff added |
| Observation closure | Check controller and learner input construction and feature/update paths, not just serialization | Exactly the existing eight float32 channels; reward `0.0`, `info == {}`; no pose, heading, dock geometry, timestamp, seed or backend handle |
| Diagnostic non-feedback | Same fixed run with evaluator diagnostics on/off and in different read orders | Identical canonical observation/action/physiology traces; diagnostic queries do not mutate world, filters or RNG |
| Physiology isolation | Inject identical shaft/contact sample sequences into reference and proposed wrapper | Identical stored energy, thermal, charger-latch and termination results on the pinned stack; no duplicated microstep costs or charging updates |
| Accounting spot checks | Zero wheels off dock; full bilateral effort off dock; connected at bulk/taper/full/resume thresholds; contact loss; thermal/depletion cases | Preserve current equations: zero wheels cost 0.015 J/interval, full bilateral effort 0.115 J/interval off dock; physical connection does not bypass acceptance or heat rules |

For a dynamic-body candidate, altered yaw/contact outcomes are substrate differences, not automatically defects. They still prevent an exact D-058-equivalence claim. For an endpoint-law candidate, preserve that law exactly and separately disclose that swept collision exclusion is not part of the current law. If swept exclusion is desired, it is an additional physical-boundary change; do not retrofit it while claiming unchanged physics. In either case, inconsistent endpoint geometry, an information leak or physiology change fails this proposal's boundary gate.

## Tranche 3: scientific execution and engineering value

| Test | Proposed pass criterion |
|---|---|
| RNG ownership | Fresh reset owns explicit named streams; unrelated policy/evaluator/sensor draws and episode execution order cannot alter each other's canonical traces; no global reseed workaround |
| Branching, before causal studies | Replay from a verified prefix or an approved complete clone passes OFF-vs-OFF identity, branch-order invariance and source non-mutation; do not assume `Space.copy()` is complete |
| Scale | 1,000 independent fixed-command episodes of 100 logical intervals; bounded object counts after cleanup, no retained old callbacks/bodies/filter state |
| Throughput | Measure at least three uncapped trials; initially ≥10,000 physical microsteps/s and ≥1,000 complete logical transitions/s including observation/physiology on the declared machine |
| Engineering value | At most one small backend module plus one wrapper seam; enumerate collision code avoided/retired and code still required; no RoboSim fork, navigation, sensor or learning stack |

The throughput thresholds are proposed feasibility gates, not proof of superiority: audited D-058 achieved about 40,583 complete transitions/s on its component workload. Compare matched workloads and separately report reset, logging and learner costs. Cross-platform agreement needs a separately frozen numerical comparison contract.

## Decision after these tests

**INFERENCE:** consider adopting a physical backend only if it passes the relevant boundary/reproducibility gates and demonstrably avoids enough collision engineering to justify its dependency and ongoing tests. A direct-Pymunk prototype can pass motor tests yet fail this value test.

If adoption remains justified, freeze the changed embodiment/physics assumptions and review the exact candidate before a new development re-baseline. Run the unchanged Level-1 floor first on legal matched support, with the learner still shadow-only. Report baseline failures before changing its controller. Separate embodiment, physics, sensing, ecology, controller and learner changes; do not interpret an old/new aggregate score as a one-variable causal result.

Keep D-045/D-058 and historical evidence runnable on their original substrate. Only the active future backend's general collision/projection code could eventually be retired. Shaft bookkeeping, beacon/dock semantics, energy/thermal/charging, controller/learner provenance and historical source remain Aweform-owned.

The immediate recommendation is **Tranche 1 only after a specific implementation task**: a small headless, fixed-command direct-Pymunk calibration probe. This documentation PR implements none of the proposed tests and changes no experimental permission.
