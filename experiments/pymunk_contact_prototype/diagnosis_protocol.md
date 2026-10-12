# Iteration 2 — contact-cause diagnostic probe freeze

**Purpose:** distinguish (1) the original west-wall penetration trigger, (2) solver/contact correction and visible geometry, and (3) a measurement/control artifact before selecting any corrected acceptance candidate. This is a bounded diagnostic probe only; it cannot PASS essential B and does not authorize an organism lifetime.

**Authority:** Flow's corrected-iteration authorization in `iteration2-founder-authorization.txt`, Firstmate inbox message 009, and issue #226 as amended by the latest Firstmate disposition. The authorized main/base is `48b18209a69d18841166bc8a00b56d00815e3b5b`.

**Preservation:** The v1 source, protocol, original `results/results.json` bytes and SHA-256 `8937854444fb02f1e19597741db42528f7bdc476f684ed6daa4489e44bb4a522`, and original failed record remain unchanged in history. Probe artifacts use only the new `results-v2/diagnosis/` path. The historical west-wall head-on case is read as a baseline reference; it is not re-executed.

## Diagnostic hypotheses and discriminators

- **H1 — contact-trigger hypothesis:** repeating the C2 prescribed world-velocity assignment after a contact callback overwrites the solver's contact-modified velocity within each logical interval and drives the hull farther into the wall. One counterfactual disables only subsequent velocity refreshes after the first contact in that logical interval. No-contact steps retain the original C2 update at every microstep.
- **H2 — solver-correction hypothesis:** the frozen 100 Hz substep uses the inherited Chipmunk collision-bias value (derived for its conventional 60 Hz step), which may not correct the initial discrete contact overlap quickly enough. One counterfactual changes only `collision_bias` to `0.9**100`, preserving 10% bias-correction retention per 0.01 s step as the numerical comparison. This is a diagnostic mapping, not a tuned acceptance setting.
- **H3 — passive-control/disconfirmation:** with zero actuation at the frozen west-wall flush pose, the body should not acquire growing penetration; in free space the contact-gated refresh counterfactual should not activate and the independent C2 arc should remain unchanged. These controls can disconfirm attributing all overlap to passive geometry or to free-space actuator integration.

These hypotheses are not assumed true. A probe may support, weaken, or leave each unresolved. The probe does not claim hardware motor/contact behavior.

## Frozen probe schedule

Exactly four fresh-space cases, run serially, each with ten microsteps per 0.1 s logical step. No RNG, parameter sweep, retries, or organism imports/lifetime.

1. `wall_refresh_suppressed_after_contact`: start `(0.5,1.5,pi)`, command `(A,A)` for 20 logical steps, frozen geometry and solver values except the single contact-triggered velocity-refresh rule.
2. `wall_bias_rate_counterfactual`: same start/commands, original every-microstep C2 refresh, with only `collision_bias=0.9**100` instead of `0.9**60`.
3. `free_space_refresh_disconfirmation`: start `(1.5,1.5,0)`, command `(A,H)` for 20 logical steps, refresh-suppression rule enabled but no intended contact; compare each endpoint against an independent analytic differential-drive arc.
4. `passive_wall_contact_control`: start `(0.095,1.5,pi)`, zero command for 20 logical steps with baseline solver and actuator update; record overlap, contact callback activity, impulse and pose changes.

`A=0.6457718232379019`, `H=A/2`; body, room, post-free geometry, mass/moment, friction, slop, damping, solver iterations, collision persistence, C2 kinematics, and all other values remain as the v1 protocol. The planned probe is 4 cases × 20 logical steps × 10 substeps = **800 Pymunk engine steps** (80 logical steps), in four new spaces. The stored v1 baseline references west-head-on penetration `0.04150745507058784 m` at 10 substeps and `0.04078590798872191 m` at 20; its result file is read-only.

## Record and interpretation

Record exact source/protocol SHA, runtime/wheel manifest, case starts/commands, per-logical-step and maximum substep penetration, final penetration, contact callback/impulse indication, pose/yaw, elapsed/logical/engine steps, free-space arc residuals, and output artifact digests. Output-directory existence is refused before constructing a physics space or stepping. The probe has no pass threshold and cannot be used to declare the 1 mm requirement met. Preserve every result, including unexpected or invalid probe outcomes. Any acceptance run requires a later separately frozen corrected source, protocol, case inventory, and new result path.

**Resource budget:** four fresh spaces, 80 logical steps, 800 engine steps, serial; expected under 1 minute, hard stop/report at 2 minutes or if host resources become contested. No lifetime is part of this budget.
