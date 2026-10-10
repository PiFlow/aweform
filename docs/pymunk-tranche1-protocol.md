# Direct-Pymunk Tranche 1 calibration protocol

- **Status:** frozen engineering protocol; no organism study or migration authorization
- **Authorized base:** `fd68c46d2cd75c46dd0eb824b8360f36f1de6cf8`
- **Issue:** [#217](https://github.com/PiFlow/aweform/issues/217)
- **Scope:** isolated empty-space calibration of a direct Pymunk body; no controller, organism, room, dock, energy, learner, or sensor integration.
- **Protocol freeze:** commit this document before running any gate/calibration evaluation. The commit SHA is the protocol SHA.

## Question and interpretation

Can a small direct-Pymunk body reproduce the declared ideal free-space wheel response, run headlessly on the supported Python runtime, and reset reproducibly without controller or organism coupling? This only evaluates a bounded prototype. Collision-engineering savings and hardware fidelity remain **UNKNOWN / NEEDS TESTING**.

The shaft actuator is idealized: each action sets actual left/right shaft increments to independently clipped requests exactly. Chassis motion is imposed by setting body twist from the differential-drive equations at each microstep; this is not wheel traction, a torque/motor model, or a hidden chassis PID. Pymunk's `Space.step` advances the dynamic body's pose; the endpoint pose is never assigned from the analytic oracle. Pymunk provides the body integration/engine step, while the declared ideal actuator refreshes body-frame forward velocity and yaw rate before each microstep. No collision shapes or other bodies exist.

## Frozen fixture and runtime

- Length, time, angle: metres, seconds, radians. World axes: +x right, +y up. Body local +x forward; positive angle counter-clockwise.
- Dynamic Pymunk body, initially stationary; engineering fixture mass 1 kg and uniform-rectangle moment `1*(0.180**2 + 0.215**2)/12 kg m²`. These are fixture parameters, not measured Aweform properties.
- Body rectangle dimensions for fixture metadata: length 0.180 m × width 0.215 m. No collision shape is attached in this empty-space tranche.
- Wheel radius `r=0.045 m`; track `w=0.185 m`; action interval `dt=0.1 s`; max signed wheel delta `a=0.6457718232379019 rad`; `b=a/2`.
- Shaft response: `actual=(clip(request_L,-a,a), clip(request_R,-a,a))`; exact command deltas distributed uniformly over the logical interval for actuator twist. Body uses unquantized shaft deltas.
- Exact update order for each action: validate two finite wheel deltas; independently clip; compute shaft distances `sL=r*actualL`, `sR=r*actualR`; compute forward speed `v=(sL+sR)/(2*dt)` and yaw rate `omega=(sR-sL)/(w*dt)`; for each of the fixed microsteps set world velocity `(v*cos(body.angle), v*sin(body.angle))` and angular velocity `omega`; call `space.step(h)` once. Read evaluator-only endpoint pose and velocities after all steps. The first protocol setting is ten microsteps of `h=0.01 s`; convergence compares twenty microsteps of `h=0.005 s` in separately reset spaces.
- Every case starts from body center `(0,0)`, requested heading, and zero linear/angular velocity, in empty space. Each calibration command is one action only.
- `Space(threaded=False)`, gravity `(0,0)`, damping `1.0`, iterations `10`, collision slop `0.0001 m`, collision bias `0.001797010299914434` (one-percent error per 0.1 s), collision persistence `3` frames, sleep-time threshold `inf`, idle-speed threshold `0`; no collision handlers, constraints, shapes, or static geometry. These values are set explicitly, including inactive contact settings.
- Pinned environment: Python `3.14.7`; Pymunk `7.2.0`; record exact installed wheel filename and SHA-256, `pymunk.version`, `pymunk.chipmunk_version`, uv version/lock state, architecture, macOS, and Python build. No Pygame or RoboSim dependency/import.
- Shaft encoder quantization is a separate diagnostic only: quantum `pi/180 rad`, nearest integer count, ties away from zero. It does not modify body integration or shaft deltas.

## Frozen cases and action validation

For each listed command, evaluate initial headings `0`, `pi/2`, `-pi/2`, `pi`, with amplitudes `0.25`, `0.5`, and `1.0` multiplying the command pair. Each starts independently at the same origin and zero velocity. Commands:

1. `ZERO=(0,0)`
2. `FORWARD=(+a,+a)`
3. `REVERSE=(-a,-a)`
4. `SPIN_POSITIVE=(-a,+a)`
5. `SPIN_NEGATIVE=(+a,-a)`
6. `ARC_NEGATIVE_YAW=(+a,+b)`
7. `ARC_POSITIVE_YAW=(+b,+a)`

Also evaluate: one stationary wheel `(+a,0)` and `(0,+a)` at the same headings; independent clipping `(+2a,-3a)` and `(-3a,+2a)`; tiny signed requests `(+1e-15,-1e-15)`; malformed shape, wrong length, strings/non-numeric values, NaN, and both infinities; encoder inputs immediately below/above `+0.5q` and `-0.5q` (`nextafter` on either side, plus exact ties). Invalid action inputs raise `ValueError`, consistent with D-045 `_parse_wheel_action`; invalid actions do not advance the space. No boolean command values are accepted as numbers.

Repeatability schedule: the exact seven-command sequence above without amplitude scaling, repeated 142 times (994 actions), followed by the first six commands (1000 actions). Run ten independent fixture constructions from initial pose `(0,0,0)` and compare the complete declared canonical trace, byte-for-byte after canonical JSON encoding. No random seeds or RNG are used.

## Independent oracles and comparisons

The independent oracle is derived directly from wheel path lengths and constant-curvature integration, not by calling the probe update function or the existing Aweform helper. For each action, `dL=r*actualL`, `dR=r*actualR`, `ds=(dL+dR)/2`, `dtheta=(dR-dL)/w`. If `|dtheta|<1e-15`, expected displacement is `ds*(cos(theta),sin(theta))`; otherwise `rho=ds/dtheta`, `x+=rho*(sin(theta+dtheta)-sin(theta))`, `y+=-rho*(cos(theta+dtheta)-cos(theta))`. Expected heading is unwrapped `theta+dtheta`. Compare probe endpoint position by Euclidean norm and yaw by absolute unwrapped difference; no normalization hides turn errors. Also compare independently to `aweform.d045.integrate_differential_drive` as a secondary cross-check, never as the sole oracle.

Metamorphic oracles: equal-wheel reversal negates displacement and preserves zero yaw; swapping wheel requests preserves predicted center displacement for equal initial pose and negates yaw; rotating initial heading by `phi` rotates displacement by `phi` and adds `phi` to heading; opposed equal wheels have zero center translation. The known vectors at heading 0 are `r*a = 0.029059732045705586 m` equal-wheel travel and `+/-pi/10 rad` opposed-wheel yaw; zero commands leave pose stationary.

## Frozen gates (not adjustable after execution)

- **Headless/runtime:** run using canonical Python; no Pygame import/dependency, display/event initialization, sleeping, interactive input, or wall-clock stepping. Record native `arm64` and Rosetta status. Native Apple Silicon is untested if unavailable.
- **Action/timing:** each accepted command advances exactly one `0.1 s` logical interval; actuator shaft deltas equal independently clipped requests within `1e-12 rad`; malformed/non-finite inputs reject without advancement.
- **Free-space calibration:** each applicable one-interval position error `<=1e-5 m`; yaw error `<=1e-5 rad`; spin-center translation within the position tolerance.
- **Known vectors:** full equal-wheel travel `r*a = 0.029059732045705586 m`; opposed full wheels yield `+/-pi/10 rad`; zero remains stationary, subject to the calibration tolerances above.
- **Symmetry:** reversal, wheel-swap yaw mirror, and rotated-start displacement rotation all satisfy the stated metamorphic oracle to the same position/yaw tolerances.
- **Microstep convergence:** ten versus twenty microsteps differ by `<=0.1 mm` position and `<=1e-4 rad` yaw in empty space.
- **Reset repeatability:** ten independently constructed runs of the frozen 1,000-interval schedule yield equal declared canonical traces on the pinned supported stack.
- **Quantization diagnostics:** 1-degree quantization is evaluated separately with ties away from zero; include below/at/above positive and negative half-quantum; exact ties quantize away from zero.

Every individual case and each gate receives PASS/FAIL; failures remain failures. This is not a universal or cross-platform bitwise-determinism claim. No acceptance result may be manufactured by assigning oracle pose into the Pymunk body.

## Output contract

Commit a JSON result artifact and short Markdown summary. JSON schema version `1`; top-level fields: `protocol_sha`, `base_sha`, `executable_sha`, `runtime_manifest`, `fixture`, `gates`, `cases`, `repeatability`, `artifacts`. Every case includes stable `case_id`, command label, requested and clipped wheel deltas, heading, amplitude, microsteps, `dt`, expected and actual position/heading, position/yaw error, actual shaft deltas, endpoint linear/angular velocity, oracle names/results, and `status`. Every gate includes `id`, verbatim threshold/description, `status`, and supporting case IDs/measurements. Repeatability includes schedule definition, run count, per-run canonical-trace SHA-256, and byte-identity result. Canonical trace fields in order: action index, requested wheel deltas, clipped/actual shaft deltas, endpoint x/y, unwrapped heading, endpoint vx/vy, endpoint angular velocity. Floats are serialized as finite JSON numbers; canonical trace encoding uses sorted keys, compact separators, UTF-8, no NaN/Infinity, and fixed declared field order; exact float representations are retained. `artifacts` records the JSON, Markdown, and detached `SHA256SUMS` paths. The detached checksum file contains SHA-256 entries for both JSON and Markdown outputs; this avoids an impossible self-referential hash cycle inside the JSON.

## Reproduction and preservation

Run on native MacBook Apple Silicon when available with Python `3.14.7`, in the isolated optional `pymunk-probe` dependency group and a clean checkout of the committed executable SHA. The report must include runnable commands for installing the optional group, running isolated tests, executing the frozen evaluator, regenerating artifacts, and running ruff, strict mypy, and the complete pre-existing pytest suite without importing Pymunk into production modules. Hash every committed result artifact. Do not change `[project].dependencies` or active production runtime dependencies.

This protocol does not authorize Tranche 2, room/contact behavior, migration, a D-series record/number, an EXP claim, a changed accepted boundary, or any organism/controller/learner execution. Passing calibration alone is not grounds for migration. Recommendation must be stop, revise candidate, or consider a separately authorized next tranche. Keep the stopped prior attempt's reported failures out of acceptance evidence; the only disclosed information is the unverified observation described by the task authorization.
