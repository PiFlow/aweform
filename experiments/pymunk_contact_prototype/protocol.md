# Issue #226 — isolated Pymunk contact/body prototype protocol

- **Status:** result-free experimental contract; frozen before measured cases.
- **Authorization:** [issue #226](https://github.com/PiFlow/aweform/issues/226), founder routing [#197 comment 6097534147](https://github.com/PiFlow/aweform/issues/197#issuecomment-6097534147).
- **Base:** `fd03776869a984eab90137fd3a0c753992605562` (main advanced from `8188cbb2224906ccb01824f4fb75c85ac55b726e` via documentation-only PR #228; the only added path is `docs/research-notes/d060-incomplete-substrate-retrospective.md`).
- **Scope:** optional `experiments/pymunk_contact_prototype/` only. No production runtime, active/default environment, controller, learner, ADR, dependency policy, existing development/evidence, #219/#220 result, #222/#224 implementation, or accepted D-record changes.
- **Scientific class:** engineering Development diagnostic; not EXP evidence and no hardware-fidelity claim.

## Question and boundary

Can a small, directly implemented Pymunk dynamic rigid-body fixture exercise useful geometric and actual collision-response mechanics for the declared Aweform-sized rectangular body, with fixed signed shaft commands, in a 3 m room with walls and separately defined circular posts? If the frozen essential fixture/contact/time/shaft/numerical/reset gates all pass, can one unmodified existing Level-1 Aweform lifetime run through a staged wrapper in a 3 m **empty** room while retaining the exact organism-facing contract?

Only the experimental fixtures have Pymunk collision dynamics. This does not adopt Pymunk as Aweform's production simulator or amend ADR 0017/0019/0020. The fixed-circle diagnostics are not part of the organism lifetime. The lifetime contains only the 3 m walls and canonical centered dock; there are zero interior obstacles.

ADR-0019 defines the accepted production wall law and ADR-0020 is not accepted. Neither is edited or reinterpreted here. This experiment's finite-mass impulse-resolved contacts are a separately named test-only dynamic law. The staged wrapper is an isolated experiment adapter, not a durable permission/default-environment change. No new observation, plasticity write, reward, info, controller behavior, sensor, planner, learning, or hardware interface is introduced. Existing D-045/D-058 remain reference implementations and are not modified.

## Frozen geometry, actuator and update law

Units are metres, seconds and radians; world +x right, +y up; local +x is forward; positive yaw is counter-clockwise. The dynamic robot is a rigid 0.180 m (forward length) × 0.215 m rectangle, mass 1.0 kg and uniform-rectangle moment `m*(0.180**2 + 0.215**2)/12 kg m²`. Mass/moment are fixture engineering choices, not hardware claims. Wheel radius 0.045 m, track 0.185 m, logical interval 0.1 s, maximum signed wheel shaft delta `0.6457718232379019 rad` each, independently clipped. One-degree shaft encoder quantization uses nearest count, ties away from zero. The body never supplies encoder values.

The actuator is ideal shaft-velocity drive: the clipped shaft deltas are delivered uniformly across the logical interval regardless of body contact. They are not inferred from chassis movement. Use candidate `C2_MIDPOINT_ARC_AVERAGE` from the merged #220 protocol: for each microstep, set forward velocity to `v*sinc(omega*h/2)` along `theta+omega*h/2`, angular velocity `omega`, then call `Space.step(h)`. Select C2 ex ante because its #220 numerical free-space residual was smaller (C2 `4.4026752318055749e-17 m`; C1 `1.4922674449837919e-7 m`) against an independent analytic arc. This is a numerical-only choice, not evidence of better traction/contact physics. Preserve both prior calibration measurements unchanged and link `docs/pymunk-followup220-protocol.md`, `experiments/pymunk_followup220/RESULTS.md`, and the exact [#225 PR handoff](https://github.com/PiFlow/aweform/pull/225). Historical C0/#219 remains the immutable failed record: 24/92 fixed cases and three gates failed; no C0 replay or recalculation is permitted.

Each accepted action is parsed as exactly two finite non-boolean numeric values and clipped independently. `dL=r*left`, `dR=r*right`, `ds=(dL+dR)/2`, `dtheta=(dR-dL)/b`, `v=ds/0.1`, `omega=dtheta/0.1`. Exactly 10 substeps of 0.01 s are the primary update. A separate fresh 20-substep run is a sensitivity comparison. Space is `threaded=False`, zero gravity, damping 1.0, 10 solver iterations, collision slop 0.0001 m, collision bias 0.001797010299914434, collision persistence 3, sleep threshold infinity and idle speed threshold 0.0. Friction and restitution are zero. Record the pinned Python 3.14.7, Pymunk 7.2.0, native runtime, actual Pymunk wheel SHA-256 checked against `uv.lock`, Munk version, uv version and lock SHA-256. Pymunk stays in the existing optional `pymunk-probe` group; no dependency/lock edit.

The 3×3 m room has four static boundary wall segments at x/y=0 and 3 m, each declared 0.01 m thick. The dock is evaluator geometry at (1.5,1.5), not a colliding shape. Circular diagnostic posts are fixed static circles, radius 0.05 m; centered post `(1.5,1.5)` and wall-adjacent post `(0.15,1.5)` are used in separate fresh scenes. Their centers/radii and wall placement are frozen and never varied. Post geometries exist only in the fixed-command diagnostic fixtures. Hull and posts are not softened or position-corrected by custom endpoint code: Pymunk's impulse solver advances the dynamic body and resolves contact. No endpoint pose is assigned analytically. Numerical oracle is independent geometry/kinematics, not a dynamic-law must-match comparator.

## Frozen fixed-command case schedule (before organism)

Every case starts from a fresh space and records the initial and final float64 position/yaw, wheel request and clipped shaft deltas, body displacement, shaft/body displacement mismatch, collision impulses and contact counts, minimum hull-to-wall/post clearance, maximum penetration, tunneling/swept-path indicator, termination/stuck classification, step count, microsteps, and reset digest. Commands are signed radians per 0.1 s; `A=0.6457718232379019`, `H=A/2`. Each repeated push is exactly 20 logical steps; other cases use one step except turn/spin (10 steps) and corner sequence (20 steps). Starts must be legal and fixed below; all initial velocities are zero.

| Family | Frozen start (x,y,heading) | Commands / repetitions |
|---|---|---|
| Original #220 calibrated vectors (no shapes; 10/20 substeps) | `(1.5,1.5,heading)`, headings `0, +pi/2, -pi/2, pi` | ZERO, `(A,A)`, `(-A,-A)`, `(-A,A)`, `(A,-A)`, `(A,H)`, `(H,A)`, `(A,0)`, `(0,A)`; amplitudes `0.25, 0.5, 1.0`; one step each |
| Each wall head-on sustained | `(0.5,1.5,0)` east, `(2.5,1.5,pi)` west, `(1.5,0.5,pi/2)` north, `(1.5,2.5,-pi/2)` south | `(A,A)` ×20; fresh start per wall |
| Wall release | same fresh wall head-on start | `(A,A)` ×20 then `(-A,-A)` ×10; verify release after contact |
| Each wall reverse-away | Same starts as wall head-on | `(-A,-A)` ×1 |
| Each wall shallow/glancing | bottom `(1.0,0.25,-65°)`, right `(2.75,1.0,25°)`, top `(2.0,2.75,115°)`, left `(0.25,2.0,205°)`; 0.25 m normal offset | `(A,A)` ×10 |
| Wall turning/spin | one fresh flush legal start per wall (including 0.005 m wall radius): left `(0.095,1.5,0)`, right `(2.905,1.5,pi)`, bottom `(1.5,0.1125,pi/2)`, top `(1.5,2.8875,-pi/2) | `(-A,A)` ×10, `(A,-A)` ×10, `(A,H)` ×10; each command sequence starts fresh |
| Near-corner and corner | `(0.25,0.25,5pi/4)`, `(0.25,2.75,3pi/4)`, `(2.75,0.25,-pi/4)`, `(2.75,2.75,pi/4)` | `(A,A)` ×10 then `(A,-A)` ×10 |
| Center-post head-on | `(1.0,1.5,0)`, centered post | `(A,A)` ×15 |
| Tangent/glancing post | `(1.0,1.65,0)`; near-tangent side pass by the declared circle | `(A,A)` ×20 |
| Sustained post push | `(1.0,1.5,0)`, centered post | `(A,A)` ×20 |
| Post release | same fresh centered-post start at `(1.0,1.5,0)` | `(A,A)` ×20 then `(-A,-A)` ×10; verify release after contact |
| Turn near post | `(1.25,1.5,0)` with centered post; legal non-overlapping initial hull | `(-A,A)` ×10, `(A,H)` ×10 |
| Multi-command near-miss | `(1.0,1.82,0)`; no intended circle overlap | `(A,A)` ×5, `(0,H)` ×2, `(A,A)` ×5 |
| Wall-adjacent post | post `(0.15,1.5)`, start `(0.55,1.5,pi)` facing toward both post and west wall | `(A,A)` ×20; record simultaneous wall/post contact manifolds if they occur |

Material multi-contact is frozen as any step with >1 simultaneous arbiter/contact point or simultaneous wall-and-post shape contacts. Count/record all, report geometry and impulses; do not discard or relabel such steps. If actual frozen placements never yield them, report zero observed and no claim of multi-contact coverage. No added/tuned geometry is allowed to force an example.

For every eligible fixed-command case compare shaft-derived expected free-space pose and independent rectangle/circle/wall geometry. Execute every frozen case in separate fresh 10- and 20-substep spaces, compare final position/yaw and contact-state classification. Replay the full 10/20 corpus once in a fresh same-source process and compare canonical serialized traces byte-for-byte. Track Pymunk physical swept penetration/tunneling by independently checking intermediate engine-substep poses against geometric boundaries; a final legal pose does not erase intermediate violation. `docs/pymunk-followup220-protocol.md`/D-058 endpoint dynamics are attribution context only; they are not an acceptance oracle for dynamic impulse contact.

### Frozen essential B gates (no tuning/rescue)

- runtime/pinning/headless: Python 3.14.7, Pymunk 7.2.0/wheel hash match, no GUI/Pygame/RNG, pinned solver values;
- input, shaft and logical timing: exact clipping, shaft increments within `1e-12 rad`, one `0.1 s` logical action, 10/20 exact microsteps, encoder quantization and no chassis-derived encoders;
- numerical/reset: finite outputs; independent free-space vector position/yaw residual `<=1e-5 m/rad`; reset/replay byte identity; fresh initialization restores body, velocities, contact caches and elapsed/step counters;
- endpoint contact: hull penetration `<=0.001 m` (declared 10× slop engineering threshold), final wall/post legality, contact observed in all frozen wall-head-on/release/glancing/turn/corner and post-head-on/tangent/sustained/release/wall-adjacent cases, finite nonnegative impulses, no NaN/inf; no measured crossing/tunneling through a wall/post between engine substeps;
- convergence: 10-vs-20 substep pose difference `<=0.0005 m` and yaw `<=0.001 rad` for corresponding frozen cases; contact state may differ only if independent clearance lies within `0.0005 m` of zero, and any such case is expressly reported;
- stuck/release: sustained pushes may stall against geometry; the frozen reverse-away or turn-away sequence must release any case labelled stuck within its declared 10-step follow-up, with body movement `>=0.001 m`; no unclassified persistent overlap;
- each case and aggregate gate individually PASS/FAIL. Any failure/instability/ambiguity is preserved and means STOP; do not run the organism lifetime.

A swept-intermediate violation, unresolved penetration >0.001 m, failed reset/replay, shaft inconsistency, failed free-space essentials, substep instability or numerical non-finiteness stops before C. The full diagnostics still report each frozen case failure; no gate tuning or rescue.

## C. One controlled Level-1 lifetime, only if every essential B gate passes

One and only one continuous lifetime, executed once by an explicit `--run-organism-once` action after the result-free executable SHA is verified and B has passed. Use an unchanged existing Level-1 `D052Controller` / accepted return-charge viability logic, exact 3 m walls and centered dock, and zero interior obstacles. The wrapper starts from one predeclared legal fixed state `(body_position=(0.75,0.75), heading=0, battery_j=2664.0, body_temperature_c=23.0, charger_termination_latched=False)` and the deterministic existing D-053 proposal stream at development seed `22571` (not among formal reservations or D-059 support `22053–22057`); horizon at most 100,000 logical transitions, stopping on existing termination/truncation only. Stop once at first boundary, do not restart or resume as another run. Run a matched reference lifetime once with same initial state, horizon and action source using unchanged `D058Env`; disclose that substrate trajectories diverge and that the controller may generate different subsequent actions. This is descriptive comparison only, not a matched same-trajectory causal estimate.

The Pymunk wrapper is staged around the existing backend and constitutive code. Preserve the exact eight float32 channels (energy, temperature, beacon L/F/R, binary paired-contact signal, quantized previous left/right shaft deltas), `reward == 0.0`, `info == {}`, and current dock, charger, battery/thermal constants, per-logical-step accounting and viability termination thresholds. Controller receives only that observation. Evaluator pose/yaw/velocity/solver contact manifold/geometry, backend handle and labels are confined to evaluator traces; no such value can enter observations or controller/learner updates. No controller tuning, learning/training, energy bonuses, sensors, behavior, altered hull, or changes to energy/temperature rules.

Record descriptive movement/contact/stall, return/reacquisition/dock/paired charging, energy/temperature, and termination traces. A charging step must be evaluated at the Pymunk pose. Preserve all reported divergence from reference; D-058 is not a must-match dynamic-law oracle. Stop immediately on any observation/reward/info/information-boundary violation. If B fails, C is not run.

Optional visualization may only consume the committed trace outputs, is offline, illustrative and not needed for the result. Do not build a stage-specific renderer.

## Frozen artifacts, comparisons and execution discipline

Protocol, all source, fixed cases, thresholds, serialization, and test plan must be committed result-free at one SHA before any measured case. Measured runner refuses dirty/incorrect SHA and writes outcomes only to an explicitly supplied output directory. Canonical JSON uses UTF-8, sorted keys, compact separators and finite values only; detached SHA-256 manifest covers JSON/Markdown and trace bytes. Frozen outputs preserve all failures. Tests must not invoke scientific measurements, the fixed-case runner, or the one lifetime; they check parsers, pure geometry/analytic calculations, case inventory/thresholds, trace schemas, and wrapper boundaries only. Do not run production/full validation in a way that invokes the measurement runner/lifetime.

Before launching measurement, independently check CPU and memory/process availability, confirm no competing required compute is active, and disclose the planned serial budget. No duplicate runs, parallel measured execution, external-worker interference, or kill. Estimate fixed diagnostics <5 minutes total at 10/20 step settings, fresh same-source replay <5 minutes; the one allowed 100,000-step reference and Pymunk lifetime may each take up to 2 minutes, serially. Pause if observed workload materially exceeds the budget or resources become contested. Validate ordinary software checks separately without rerunning the frozen science or lifetime. Do not edit measured source after freeze and silently reuse results; any result-affecting fix stops for supervisor disposition/new provenance.

## Result interpretation and STOP

Classify each statement VERIFIED (directly measured in the frozen fixture), INFERENCE, or UNKNOWN. Report whether the collision solver replaced bespoke collision/contact geometry handling and what actuator/world/wrapper/physiology code remains. No claim of hardware fidelity, production adoption, accepted ADR revision, obstacle lifetime, formal EXP evidence, or developmental promotion. Preserve historical #219 FAIL exactly and cite #220 C1/C2 as numerical calibration evidence only.

No PR merge without separate explicit Flow authorization. Do not start any successor.
