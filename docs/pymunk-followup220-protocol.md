# Pymunk #220 corrected empty-space calibration protocol

- **Status:** new frozen exploratory engineering protocol; no organism study,
  production integration, evidence claim, or migration authorization.
- **Authorization:** issue [#220](https://github.com/PiFlow/aweform/issues/220).
- **Authorized base:** `ce4f4943f6d8fcd84c723a151b15178f3856e098`.
- **Scope:** headless, isolated, empty-space Pymunk calibration only.
- **Protocol SHA:** the commit that adds this file. The executable/test-plan SHA
  is a later clean commit that adds only the new experiment implementation.
  Neither SHA may be changed after any candidate is measured.

## Question and interpretation

Does changing only the actuator's per-microstep world-velocity update from the
historical start-heading direction to a centered-heading direction remove the
recorded empty-space pose residual, and does arc-averaging the centered velocity
change that result? Pymunk remains a pose integrator in both new candidates.
This design compares update rules; it does not establish which rule represents
real wheel traction or hardware.

Candidate outcomes are descriptive. No candidate is selected for production,
contact, a room, a dock, a controller, or any later tranche. A calibration PASS
does not establish engineering savings or hardware fidelity.

## Fixture and runtime, frozen before execution

Use metres, seconds, radians; world `+x` right and `+y` up; local body `+x`
forward; positive heading counter-clockwise. A fresh dynamic body starts at
`(0, 0)`, at the requested finite initial heading, with zero linear and angular
velocity. The body has fixture mass `1 kg` and uniform-rectangle moment
`1*(0.180**2 + 0.215**2)/12 kg m^2`; its declared dimensions are `0.180 x
0.215 m`. No shape or other body is added.

Retain the Tranche 1 values: wheel radius `r=0.045 m`, track `b=0.185 m`,
logical interval `dt=0.1 s`, and independent signed wheel-delta clipping at
`a=0.6457718232379019 rad`. The body uses unquantized clipped shaft deltas.
One-degree nearest-count encoder quantization, with ties away from zero, is a
separate diagnostic only.

Use Python `3.14.7`, optional Pymunk `7.2.0`, and the native macOS arm64 wheel
when available. Record Python build/executable, OS/build, architecture and
Rosetta status, Pymunk and Chipmunk versions, actual wheel path/name/SHA-256,
`uv` version and `uv.lock` SHA-256. A run must STOP before stepping if the
runtime version, optional dependency, platform identity, or actual wheel hash
cannot be recorded and checked against the lock. No project dependency or lock
change is authorized.

Configure `Space(threaded=False)`, gravity `(0,0)`, damping `1.0`, iterations
`10`, collision slop `0.0001 m`, collision bias `0.001797010299914434`,
collision persistence `3`, sleep threshold `inf`, and idle speed threshold
`0.0`. These settings match Tranche 1; collision settings are inactive because
the space has no shapes. Use exactly `N=10` microsteps (`h=0.01 s`) and
separately reset `N=20` microsteps (`h=0.005 s`). Each accepted logical action
calls `Space.step(h)` exactly `N` times.

## Actuator and engine ownership

For each action, first reject inputs unless they contain exactly two finite,
non-boolean numeric values. Then independently clip each requested wheel delta
to `[-a,+a]`. The ideal shaft actuator reports those clipped values as actual;
there is no slip, torque, traction, motor, chassis PID, stochasticity, or
wheel/body collision model. Derive, without calling Pymunk or the Aweform
helper:

```text
dL = r * actual_left                 dR = r * actual_right
ds = (dL + dR) / 2                    dtheta = (dR - dL) / b
v = ds / dt                           omega = dtheta / dt
h = dt / N
```

Pymunk owns body position/angle advancement only: the candidate sets linear and
angular velocity, then `Space.step(h)` changes the dynamic body. Candidate
code must never assign an analytic/oracle endpoint to body position or angle.
Evaluator pose, velocity, and errors are not organism observations.

### Frozen candidate matrix

| ID | Status | Per microstep, before `Space.step(h)` |
|---|---|---|
| `C0_T1_HISTORICAL` | Read-only comparator; **do not rerun** | Historical Tranche 1 used `v*(cos(theta), sin(theta))`, `omega`, then `Space.step(h)`; its source, artifact, and failures remain byte-identical. Import only its recorded outcome/status for comparison. |
| `C1_MIDPOINT_NOMINAL_SPEED` | New candidate | Let `theta` be the current engine body angle. Set velocity to `v*(cos(theta + omega*h/2), sin(theta + omega*h/2))`; set angular velocity to `omega`; call `Space.step(h)`. |
| `C2_MIDPOINT_ARC_AVERAGE` | New candidate | Set velocity to `v*sinc(omega*h/2)*(cos(theta + omega*h/2), sin(theta + omega*h/2))`; set angular velocity to `omega`; call `Space.step(h)`, where `sinc(x)=sin(x)/x` and `sinc(0)=1`. |

`C1` changes only the sampled velocity direction relative to the historical
start-heading update. `C2` uses the same centered direction and additionally
sets the per-step mean world velocity that corresponds to the constant-twist
arc chord. This is a declared actuator/update convention, not evidence of a
physical motor model. Evaluate both candidates; do not choose, tune, or drop one
based on observed results. C0 is represented only by its committed Tranche 1
protocol/results and recorded hashes; this protocol does not change its
historical acceptance outcome.

## Independent analytic and metamorphic oracles

The analytic oracle uses only the frozen wheel equations above. For `dtheta`
near or equal to zero, use the stable `sinc` form; otherwise the equivalent
constant-curvature radius is `rho=ds/dtheta`:

```text
dx_body = ds*sinc(dtheta/2)*cos(dtheta/2)
dy_body = ds*sinc(dtheta/2)*sin(dtheta/2)
dx_world = dx_body*cos(theta0) - dy_body*sin(theta0)
dy_world = dx_body*sin(theta0) + dy_body*cos(theta0)
theta_expected = theta0 + dtheta        # unwrapped
```

The oracle module must not call candidate update functions, Pymunk, or
`aweform.d045.integrate_differential_drive`. A D-045 helper comparison may be
reported only as a secondary cross-check.

For actual endpoint `(x,y,theta)`, calculate position error as
`hypot(x-x_expected, y-y_expected)` in metres and yaw error as the absolute
unwrapped difference in radians. No angle normalization may hide a turn error.

Metamorphic checks are evaluated in the initial body frame. With
`dx_b=dx*cos(theta0)+dy*sin(theta0)` and
`dy_b=-dx*sin(theta0)+dy*cos(theta0)`, swapping wheels must preserve `dx_b`,
negate `dy_b`, and negate yaw increment. It must **not** compare the two world
displacements as identical. Equal-wheel reversal must negate displacement;
rotating the initial heading by `phi` must rotate displacement by `phi` and
add `phi` to the unwrapped endpoint heading; equal/opposite wheel spin must
have zero centre translation.

The known-vector oracle is independently calculated from the declared fixture,
not gated by the all-case calibration result:

```text
full equal-wheel travel = r*a = 0.029059732045705586 m
full opposed-wheel yaw = r*(2*a)/b = pi/10 rad
zero wheel deltas leave position and heading unchanged
```

The `known-vectors` gate reads only its dedicated forward, positive/negative
spin, and zero measurements. It must not depend on `free-space-calibration` or
any other aggregate gate.

## Frozen action and reset matrix

For both new candidates, both `N=10` and `N=20`, each of headings
`0, +pi/2, -pi/2, pi`, and each amplitude `0.25, 0.5, 1.0`, independently
reset and evaluate:

```text
ZERO                 (0, 0)
FORWARD              (+a, +a)
REVERSE              (-a, -a)
SPIN_POSITIVE        (-a, +a)
SPIN_NEGATIVE        (+a, -a)
ARC_NEGATIVE_YAW     (+a, +a/2)
ARC_POSITIVE_YAW     (+a/2, +a)
ONE_WHEEL_LEFT       (+a, 0)
ONE_WHEEL_RIGHT      (0, +a)
```

This is 108 base action/heading/amplitude cells per candidate and microstep
count. Also run both independent-over-range commands `(2a,-3a)` and `(-3a,2a)`
from each listed heading; tiny signed pairs `(1e-15,-1e-15)` and
`(-1e-15,1e-15)` plus one-wheel tiny values `(1e-15,0)` and `(0,-1e-15)` from
each heading; and reject empty, one-value, three-value, string, bytes,
non-numeric, boolean, NaN, positive-infinity, and negative-infinity actions.
Invalid actions must raise `ValueError`, leave time and pose unchanged, and
call `Space.step` zero times. Accepted actions must advance exactly one
`0.1 s` logical interval. Each clipped actual shaft delta must match the
independent clamp within `1e-12 rad`.

For every base action/heading/amplitude cell, compare independently reset
`N=10` and `N=20` endpoints. For each candidate, create ten new spaces and run
the exact 1,000-command schedule `(ZERO, FORWARD, REVERSE, SPIN_POSITIVE,
SPIN_NEGATIVE, ARC_NEGATIVE_YAW, ARC_POSITIVE_YAW)*142 + first 6`, at `N=10`,
from `(0,0,0)`. There is no RNG or seed.

For `q=pi/180 rad`, test encoder inputs immediately below, immediately above,
and exactly at `+q/2` and `-q/2` using `math.nextafter`; exact ties round away
from zero. Quantization never changes the body commands or pose.

## Frozen metrics and gates

Every applicable case receives an individual PASS/FAIL. A gate is PASS only
when every measurement named by that gate meets its threshold. A failed gate
must remain visibly FAIL in JSON/Markdown and make the runner exit nonzero.
There are no retries, changed samples, post-result threshold changes, or
candidate omissions.

| Gate | Frozen rule for each new candidate |
|---|---|
| `headless-runtime` | Python `3.14.7`, Pymunk `7.2.0`, checked wheel hash, no Pygame import, GUI/event setup, sleep, wall-clock stepping, or RNG. |
| `action-timing` | Exactly `N` engine steps and `0.1 s` per accepted command; independent clipping error `<=1e-12 rad`; invalid inputs reject before stepping. |
| `free-space-calibration` | All 108 base cells at `N=10`: position error `<=1e-5 m` and unwrapped yaw error `<=1e-5 rad`; includes zero/spin centre translation. `N=20` is recorded and compared under the same numerical thresholds. |
| `known-vectors` | Dedicated full forward, both full spins, and zero each meet position/yaw error `<=1e-5` in their declared units; independent of the global calibration gate. |
| `symmetry` | Reversal, wheel-swap body-frame reflection/opposite yaw, rotated-heading displacement, and spin-centre translation errors each `<=1e-5 m` or `<=1e-5 rad`, as applicable. |
| `microstep-convergence` | For all base cells, the `N=10` vs `N=20` endpoint difference is `<=1e-4 m` and unwrapped yaw difference `<=1e-4 rad`. |
| `reset-repeatability` | Ten independently reset 1,000-command traces per candidate have byte-identical canonical JSON bytes and equal SHA-256. |
| `encoder-quantization` | All six half-quantum cases equal `[0,+q,+q,0,-q,-q] rad` for inputs below/above/at positive then negative half quantum. |
| `preservation-and-isolation` | C0 historical hashes/statuses match the committed files; production `src/` and `tests/` are unchanged from base; Pymunk remains optional in `pymunk-probe`; new experiment does not import production/controller runtime except for optional secondary oracle cross-check. |

The 10-vs-20 comparison is an endpoint convergence check, not a hardware
accuracy claim. `C2` is mathematically designed to integrate the declared
constant-twist arc by engine-advanced chords; that design property does not
validate a physical actuator.

## C0 historical comparator and preservation

Treat the merged Tranche 1 record as historical, immutable C0. Its frozen
protocol SHA is `89de47de86aea43d30e7dc5147c51ed5d1263b1d`, executable SHA is
`2ba46e1dd2ab3e812ab2afaa5791521b8c48ae24`, original result text SHA-256 is
`f8310ee8b7f1b26567d891b4bc7f2e0391d15030b4620209aa325ef105a9d715`, and
`results.json` SHA-256 is
`4a0a0c5c1bef6602553971a9745274c649c56a70e394cde285e5cbf3d6f428e2`.
Recorded C0 gates remain PASS for headless/runtime, action/timing,
microstep-convergence, reset-repeatability, and encoder-quantization, and FAIL
for free-space-calibration, known-vectors, and symmetry. Its 92 one-interval
cases include 24 failed position cases. The recorded maximum position error is
`0.00011400040559442288 m`; the recorded wheel-swap position mismatch is
`0.0015398709610861183 m` under the erroneous unreflected comparison. The
known-vector aggregate FAIL and the incorrect wheel-swap comparison remain
historical outcomes; post-hoc arithmetic in the Tranche 1 addendum is not a
rerun or acceptance result.

Do not run the C0 executable or rewrite, normalize, relabel, or regenerate any
Tranche 1 file. Regress only the historical hash/status manifest. The old
`RESULTS.md` reports `88 passed / 25 failed` for its probe suite, while the
historical PR description reports `87 passed / 26 xfailed`; retain that
unreconciled reporting difference as UNKNOWN rather than changing either
record.

## Result contract and provenance

The executable must refuse to evaluate candidates unless the worktree is clean
at its committed executable SHA, on the authorized branch, and the optional
wheel hash matches `uv.lock`. Record the exact protocol SHA, base SHA,
result-free executable/run SHA, and later record/final PR SHA as separate
provenance roles. No measured artifact may be present in the freeze commit.

`results.json` schema version `1` records: protocol/base/executable SHAs;
runtime manifest and wheel identity; fixture and engine settings; the complete
C0/C1/C2 matrix with C0 marked recorded-only; all requested/clipped deltas,
start headings, amplitudes, microsteps, analytic and engine endpoints, units,
per-case errors/statuses; every gate's exact threshold, measurements, and
status; all metamorphic/known-vector/clipping/invalid/quantization results;
the ten trace hashes/byte identity per candidate; and artifact paths/hashes.
Serialize only finite JSON numbers. Canonical trace keys, in order, are action
index, candidate, request, clipped shaft deltas, endpoint position, unwrapped
heading, endpoint velocity, and angular velocity. Canonical JSON uses UTF-8,
sorted keys, compact separators, and `allow_nan=False`. `SHA256SUMS` is detached
and lists JSON and Markdown hashes, avoiding self-hashing.

Commit and push the protocol first; commit and push the result-free executable
and test plan second. Only after both exact commits are clean on the authorized
branch may the fixed cases run. Commit all result artifacts in one later
record commit. Record the final PR HEAD in the GitHub `[LUNA-HANDOFF]`, not by
self-referencing a commit inside itself.

Reproduction commands must use the frozen executable SHA and locked optional
group. Report `ruff check .`, source-only strict mypy, experimental-module
mypy separately, new and historical isolated pytest counts separately, and
the existing production suite separately. Historical strict xfails or failures
must be counted conspicuously; a green test command must never imply C0 passed.

## STOP conditions and limitations

STOP before execution if the base changes, the required Python/Pymunk/wheel
identity cannot be established, the worktree is not clean at the executable
SHA, any candidate/matrix field is missing, or a necessary scientific choice
is still unresolved. STOP after execution on any missing/changed case,
non-finite result, artifact/hash mismatch, production-source change, or failed
gate; preserve the result and report the single recommendation `STOP`, `REVISE`,
or `CONSIDER SEPARATELY AUTHORIZED CONTACT TRANCHE` without widening scope.

This protocol authorizes no wall, collision, obstacle, room, dock/charger,
sensor, energy/thermal state, controller, learner, organism lifetime, reserved
seed, D/EXP identifier, backend migration, contact tranche, or hardware claim.
