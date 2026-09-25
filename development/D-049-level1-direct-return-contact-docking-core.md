# D-049 — Level-1 direct return and contact-seeking docking core

- **id:** D-049
- **status:** executable/protocol freeze; official result pending
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

## Result provenance

The official artifact and completed record are intentionally absent from this
result-free freeze. They must be generated only from the pushed executable
commit, with failures retained per case and byte-identical regeneration from
that same executable SHA.

## Validation at freeze

Focused tests and the full repository checks must be run before the executable
freeze is accepted: D-049 tests, `uv run pytest -q`, `uv run ruff check .`,
`uv run mypy src --strict`, compile/import checks, and `git diff --check`.
