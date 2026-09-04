# D-024 — Causal finite-body dual-contact docking probe

- **id:** D-024
- **lane:** Development
- **date:** 2026-09-04
- **authoritative_base_sha:** `c0ce8182d0fba97035d76899e5b188ca7f171b05`
- **implementation_probe_sha:** `d29d65aca4542c341404216f691b53ed15720b51`
- **development_seeds:** `18365, 18366, 18367`
- **horizon:** `70,000` transitions per uninterrupted causal lifetime
- **disposition:** `CONTINUING`
- **learned mechanism:** none

The machine-readable numerical source is
[`D-024-causal-finite-body-dual-contact-docking-probe.json`](D-024-causal-finite-body-dual-contact-docking-probe.json).

## Scientific question and scope

D-024 asks what happens when the unchanged D-021 fixed non-learning
controller is exposed to one causal finite-body rear dual-contact charging
predicate. This is descriptive Development-lane work and makes no
confirmatory claim. No remediation, tuning, learner, reverse action, new
sensor, planning, visualization, or later-task work is included.

## Frozen protocol and provenance

The executable implementation was frozen at
`d29d65aca4542c341404216f691b53ed15720b51`, from the exact authorized base.
The exact seeds, horizon, metrics, and interpretation below were committed
before inspecting the canonical result magnitude. Each seed is one
uninterrupted causal lifetime with no reset or reseed.

The canonical reservation validator is
`validate_exp003_development_seeds`; D-024 accepts exactly `18365, 18366,
18367`. Existing formal reservations, including EXP-002 `50001–51000`, remain
guarded. The implementation artifact records the exact executed SHA and
compact per-seed summaries; it stores no raw transition trace.

## PROGRAMMED

- `D024Env` changes only D-020's causal `charging_contact` property.
- Body length is `0.10`, width is `0.08`, with `+X` forward and `+Y` left.
- Corresponding rear body contacts are `(-0.05,+0.025)` and
  `(-0.05,-0.025)` in the body frame.
- The dock is fixed at `phi=0` with corresponding station-centred contacts
  `(0,+0.025)` and `(0,-0.025)`.
- Charging requires both corresponding pair errors to satisfy inclusive
  `<=0.01`; pair correspondence is never swapped.
- Initial pose is station `(0.50,0.50)`, body centre `(0.55,0.50)`, heading
  `0`, full `5328.0 J`, `23.0 °C`, latch false, and controller mode `CHARGE`.
  Initial dual contact is true; the first `MOVE_FORWARD` loses it.
- D-020 equations, transition order, parameters, charger state machine,
  four-action point-centre kinematics, world clamping, and station-centred
  beacon are inherited unchanged.
- The actual `D021Controller` is reused unchanged. There is no learner or
  plastic state, and temperature has zero programmed behavioural influence.

## ORGANISM-VISIBLE

Exactly six channels are retained: normalized own battery energy, beacon left,
beacon forward, beacon right, binary dual charging contact, and normalized own
body temperature. Reward is exactly `0.0` and organism-facing `info` is `{}`
on every transition.

## EVALUATOR-ONLY

Diagnostics record dual-contact entries, individual plus/minus pair errors,
minimum maximum pair error during SEEK, one-pair-only tolerance events,
legacy circular-contact-without-dual events, SEEK outcomes, charger exits,
reacquisition, recharge/redeparture, energy/thermal outcome, and termination
or horizon censoring. Coordinates, geometry, errors, legacy contact, telemetry,
and labels never enter action selection.

## Interpretation rules

Full-cycle success requires full docked departure → low-energy SEEK → valid
dual-contact charging → full recharge → post-recharge re-departure. A SEEK
episode entering with contact already true is reported as provenance, not as a
docking solution. One-pair tolerance, small pair error, and legacy circular
contact without dual contact are partial/near-approach diagnostics only.
Termination after SEEK begins with contact false and before dual reacquisition
is demonstrated failure for that episode. Unresolved state at transition
`70,000` is horizon-censored, not failure. Null and negative outcomes are
preserved without tuning.

## Direct observations

The exact per-seed observations are in the JSON artifact and were generated
after the frozen implementation/protocol commit. They report the number and
outcome of each SEEK episode, dual-contact/pair-error diagnostics, inherited
D-020 energy/thermal outcome, and recharge/redeparture state.

| Seed | Transitions | Outcome | Dual entries | SEEK / reacquisition | Full recharge / re-departure | Min battery (J) | Max body temperature (°C) |
|---:|---:|---|---:|---:|---:|---:|---:|
| 18365 | 54,949 | energy depletion | 0 | 1 / 0 | 0 / 0 | 0.0 | 23.599709 |
| 18366 | 54,928 | energy depletion | 0 | 1 / 0 | 0 / 0 | 0.0 | 23.599708 |
| 18367 | 54,945 | energy depletion | 1 | 1 / 0 | 0 / 0 | 0.0 | 23.599711 |

All three SEEK episodes began with contact false and ended as demonstrated
failures before dual reacquisition. The single seed-18367 dual entry occurred
at transition `23,798`, before its low-energy SEEK entry at `24,327`, so it is
an AWAY incidental dual-contact event rather than a SEEK docking solution. Its
corresponding plus and minus pair errors were both approximately `0.00355339`.
Minimum maximum pair errors during SEEK were approximately `0.043183`,
`0.029015`, and `0.055563` for seeds 18365, 18366, and 18367 respectively.
Seed 18366 also recorded `3,061` one-pair-only tolerance events. Legacy
circular-contact-without-dual events occupied `30,790`, `30,783`, and `30,798`
transitions respectively, but never granted charging. No thermal threshold was
reached and no full-cycle success occurred.

No run was invalidated and no scientific retuning or remediation was applied.

## Cautious inference

The narrow inference is limited to these three exact development lifetimes,
this frozen implementation, and this horizon. The result does not establish
robustness, optimality, learning, intelligence, metabolism, consciousness,
emotion, subjective experience, genuine life, or hardware autonomy.

## Disposition

`CONTINUING`. D-024 does not authorize an EXP protocol, a new durable
boundary, or D-025/later development.
