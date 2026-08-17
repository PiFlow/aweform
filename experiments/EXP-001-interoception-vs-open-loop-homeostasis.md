# EXP-001 — Interoception versus Open-Loop Homeostasis

**Status:** Pre-calibration design — not preregistered

The formal pre-calibration design is recorded in
[`EXP-001-precalibration-protocol.md`](EXP-001-precalibration-protocol.md).
That protocol contains no calibration or confirmatory results.

## Provisional scientific question

> Does closed-loop regulation using actual internal energy improve viability
> relative to a competent energy-blind controller using a calibrated fixed
> temporal regulation schedule?

EXP-001 is a pre-calibration design, not yet a preregistered causal claim.
Calibration and confirmatory execution remain pending independent review.

## Difference from EXP-000

EXP-000 C received a fixed non-informative energy mask of `0.5`. That was a
valid information-blind ablation, but it was not a natural model of an
organism with no internal-energy sensor.

EXP-001 C receives **no energy value at its decision boundary at all**. It is
not implemented by replacing energy with `0`, replacing it with `0.5`, masking
it, adding noise, calculating an estimated battery, or passing the full
four-value observation and promising not to inspect index `0`.

C may nevertheless behave competently using external left/forward/right
resource sensing and fixed temporal rules. EXP-001 therefore compares
energy-aware closed-loop homeostasis with energy-blind open-loop homeostasis.
Because the policies differ specifically in how homeostatic mode timing is
regulated, EXP-001 must not be described as isolating “information alone”.

EXP-000 remains historical scientific work. Its controllers, records, result
record, calibration records, and frozen confirmatory protocol are not changed
by EXP-001 development.

## Development conditions

### A — stochastic persistent exploration reference

A receives only external left/forward/right resource signals and remains in
`EXPLORE` forever. Its shared run-and-turn explorer ignores those signals and
uses the policy RNG for stochastic persistent exploration. A has no deliberate
recharge behaviour and no energy sensor.

### B — interoceptive closed-loop homeostasis

B receives actual normalized internal energy plus the exact same external
left/forward/right resource signals as C. It starts in `EXPLORE` and uses the
following programmed modes:

- `EXPLORE` → `SEEK_RESOURCE` when actual energy falls below `0.35`;
- `SEEK_RESOURCE` → `CHARGE` on a configurable external resource-contact
  criterion, using the shared local resource steering logic otherwise;
- `CHARGE` uses `WAIT` until actual energy rises above `0.85`, then returns to
  `EXPLORE` with a new stochastic run.

The pre-calibration protocol holds `enter_seek = 0.35` and `recover = 0.85`.
These values are not tuned from C calibration outcomes.

### C — genuinely energy-blind conservative homeostasis

C receives only external left/forward/right resource signals. It has no energy
field, fixed or otherwise, and no estimated-energy state. It starts in
`EXPLORE` and uses fixed timers:

- `EXPLORE` → `SEEK_RESOURCE` when the blind exploration timer expires;
- `SEEK_RESOURCE` → `CHARGE` on the same external resource-contact criterion
  used by B, using the same local steering logic otherwise;
- `CHARGE` uses `WAIT` until the blind charging timer expires, then returns to
  `EXPLORE`.

Timers count environment transitions/actions, including turns and `WAIT`, not
only forward movement. C never knows that it is fully charged; it only knows
how long it has spent charging. C does not maintain an energy model.

Its provisional conceptual strategy is:

> I cannot sense my stored energy. I recharge for a conservative fixed period,
> explore for a conservative fixed period, then return to recharge.

## Shared stochastic exploration primitive

EXP-001 A, B, and C use one shared persistent run-and-turn implementation.
Each run samples its consecutive forward-action count from a geometric
distribution with hazard `p = 1/8`, so runs are always at least one action and
have mean eight actions. At a run boundary, direction is sampled left/right
with probability `0.5/0.5` and magnitude is sampled as `45°/90°` with
probability `0.5/0.5`. A 45° turn uses one existing turn action; a 90° turn
uses two consecutive existing turn actions. No 90-degree environment action is
added.

This is biologically inspired by run-and-tumble exploration. It is not
intended or documented as a quantitative model of *E. coli*. EXPLORE does not
compare current resource concentration with a previous concentration and
contains no temporal chemotaxis or memory.

Each condition receives a fresh policy generator derived deterministically from
the same master seed through the repository's separate `RandomStreams.policy`
stream. Conditions never share a mutable generator. A mode change does not
reseed the explorer. Re-entering `EXPLORE` starts a new stochastic run from
the next values of the existing policy stream rather than resuming a partial
run or restarting the seed.

The hazard `p = 1/8` is a fixed part of this EXP-001 mechanism, not a
development configuration parameter. Changing it requires an explicit
scientific-design change.

## True sensory boundary

The controller-facing boundary is explicit:

- A and C receive only `left_resource, forward_resource, right_resource`;
- B receives `actual_energy` plus the exact same three external signals.

Environment and evaluator code may retain actual energy for viability,
termination, and scientific telemetry. That privileged state is not a C
contact sensor and does not enter A or C actions.

## Development execution boundary

The development runner is separate from the historical EXP-000 runner. For
each caller-supplied development seed it constructs and resets a fresh
environment for A, B, and C with the same environment configuration and seed.
It derives a fresh policy generator for each condition from that same master
seed through the existing policy stream derivation; the generators are never
shared or reseeded during an episode. EXP-001 execution rejects any
environment configuration whose turn angle is not exactly `π / 4`.

The runner owns one explicit adapter from the generic simulator observation
`[normalized_energy, left_resource, forward_resource, right_resource]` to the
typed controller boundary. It constructs `ExternalObservation(left, forward,
right)` for A and C, and constructs
`InteroceptiveObservation(actual_normalized_energy, external)` for B. The raw
four-value array and privileged evaluator state are not passed to controllers.
Episode records keep controller-visible observations separate from privileged
evaluator telemetry such as position, actual energy, harvested energy, action
costs, and termination state.

This runner is a deterministic development instrument only. It does not
execute formal calibration or confirmatory seeds, perform statistical
analysis, or make a scientific claim. Development observations are not
scientific evidence.

## Resource-contact semantics

The current development resource-contact criterion is exactly:

`max(left_resource, forward_resource, right_resource) >= resource_contact_threshold`

It is derived only from B/C's external L/F/R directional resource signals. It
receives no energy, evaluator telemetry, body coordinates, source coordinates,
harvested-energy value, or hidden resource truth. Because directional probes
can be spatially displaced from the body, this is an externally detectable
resource-contact/proximity proxy, not a claim of literal physical body
contact.

The pre-calibration protocol holds the numerical threshold at `0.8`. Its
meaning remains an externally detectable contact/proximity proxy rather than a
claim of literal physical docking or body contact. This foundation does not
add a privileged contact sensor.

## Programmed mechanism

The A/B/C policies, the shared stochastic explorer, local resource steering,
resource-contact test, mode transitions, timers, and `WAIT` charging action are
programmed mechanisms. They are not learned behaviour. Development behaviour
must not be presented as experimental evidence.

## Development parameters

The development implementation keeps the external resource-contact threshold,
blind exploration duration, blind charging duration, B energy thresholds, and
environment/body/resource values as explicit configuration inputs. The
pre-calibration protocol freezes the EXP-001 values and candidate grid used for
formal design; it does not add production defaults to the development API.
Explorer hazard is not in this list: `p = 1/8` is structurally fixed by the
mechanism.

## Calibration and confirmatory inference

Calibration and confirmatory inference are specified at the pre-calibration
design level in the linked protocol. The exact calibration seeds are
`20001–20200` inclusive and the untouched confirmatory seeds are
`30001–31000` inclusive. Neither set has been executed in this slice. The
formal episode horizon is 1000 transitions, the C selection rule is C-only,
and the planned primary confirmatory endpoint is paired capped lifespan; no
confirmatory analysis or scientific claim has been made.

## Scientific claim

None yet. EXP-001 development establishes a transparent behavioural foundation
for deciding whether a later, properly designed experiment is scientifically
interpretable. It makes no claim about consciousness, emotion, subjective
experience, genuine life, biological metabolism, intelligence, learning, or
emergent behaviour.
