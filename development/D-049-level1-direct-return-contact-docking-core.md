# D-049 — Level-1 direct return and contact-seeking docking core

- **id:** D-049
- **status:** completed from frozen executable SHA
- **lane:** Development / Level-1 Innate Autonomous Viability diagnostic
- **authorized_base_sha:** `a375de54722c3bfc09634a3685c4558a7a9f917f`
- **disposition:** CONTINUING

## Question and boundary

If return mode is active at reset, can the unchanged D-045 V0.5 organism use
only its current float32 L/F/R beacon, contact bit, and fixed V0.5 constants to
return directly to the station centre, rotate until physical charging contact,
and establish charging? This is descriptive Development work, not an EXP claim.

The routine is **PROGRAMMED / ENGINEERED PRIOR**. It has no learned state,
reward, planner, semantic movement action, history, D-046/D-048 state, or
energy-trigger implementation. Level-1 wheel-command authority is logged on
every active diagnostic transition. Evaluator pose, heading, station geometry,
pair error, and success labels are used only for post-transition diagnostics.

## Frozen executable protocol

- Station centre: `(0.50, 0.50)`.
- Direct-return radii: `0.10`, `0.25`, `0.40` m.
- Position bearings: `0, 45, 90, 135, 180, 225, 270, 315` degrees.
- Four explicit source-relative initial-heading classes per direct case:
  `0.137`, `1.083`, `-0.971`, and `pi - 0.217` radians.
- Exact-centre terminal-only headings: `0.137`, `0.193`, `0.247`, `1.209`,
  `pi - 0.173`, `2.387`, `4.119`, and `5.711` radians.
- Cases: `96` direct-return plus `8` terminal-only, for `104` total.
- Per-case horizon: `128` transitions, frozen before execution.
- Float32 inverse revalidation limits: coordinate `1e-6` m, distance `1e-6`
  m, bearing `1e-6` rad.
- Controller centre tolerance: `1e-6` m; angular tolerance: `1e-6` rad.
- Terminal rotation: one fixed positive body rotation using `(-max, +max)`;
  maximum in-place turn is exactly `18` degrees per transition and the
  diagnostic retains the predeclared `20`-turn bound.

The controller branches contact-first to zero. Otherwise it reconstructs
body-relative source geometry from the actual observation's float32 L/F/R,
turns in place with the smallest bounded continuous bilateral command, drives
straight with equal wheel deltas scaled to reconstructed distance and capped by
the existing envelope, recomputes after every transition, then uses the fixed
terminal spin until organism-visible contact. The next contact-observing
transition commands zero and must show battery increase under D-045 charging.

## Official result

The official run was generated only after the result-free executable/protocol
freeze was pushed and verified retrievable from GitHub:

- **clean_executable_sha:** `73b0d3ccd709485c309c888927a98a7773529b6a`
- **artifact:** [`D-049-level1-direct-return-contact-docking-core.json`](D-049-level1-direct-return-contact-docking-core.json)
- **artifact_bytes:** `445239`
- **artifact_sha256:** `3d87e61e236a1e0c65d50aae65fa16ea201029e8ee20a5bb7dabd6fd88f139ec`
- **independent regeneration:** byte-identical, same size and SHA-256

All `104/104` frozen cases were classified `DOCKED_AND_CHARGING`; no case was
invalid, horizon-censored, terminated before contact, spin-exhausted, or
contact-without-charge. The inverse revalidation covered `104` valid current
float32 observation paths with maxima of `2.3311302124739974e-7` m coordinate,
`2.2699739807285901e-7` m distance, and `3.297103055022177e-7` rad bearing,
all inside the frozen `1e-6` limits.

The direct-return block had `96/96` successes, maximum coarse-return count
`24`, and maximum terminal-spin count `17`. The terminal-only block had
`8/8` successes and maximum terminal-spin count `19`, within the predeclared
`20`-turn bound. The largest evaluator-only contact pair error at first
contact was `0.0096350297699432` m, under the retained inclusive `0.010` m
tolerance. Two terminal cases began already in contact and followed the
contact-first zero rule.

Across `2314` active transitions, Level-1 authority was logged on every
transition (`100%`). The first stationary zero-wheel charging transition
showed battery increase in all cases. Reward remained exactly `0.0` and every
organism-facing `info` value remained `{}`. No learned/plastic state or
evaluator geometry entered causal behavior.

This is a descriptive Development result only. It does not establish hardware
performance, metabolism, learning, intelligence, consciousness, or a
confirmatory evidence claim.

## Validation

The executable freeze passed focused D-049 tests (`14 passed`), the full suite
(`1074 passed, 8 warnings`), `uv run ruff check .`, `uv run mypy src --strict`,
compile/import checks, and `git diff --check`. The official artifact was then
regenerated independently from the same executable SHA and compared byte for
byte before this result layer was written.
