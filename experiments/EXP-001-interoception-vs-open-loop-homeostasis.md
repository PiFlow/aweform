# EXP-001 — Interoception versus Open-Loop Homeostasis

**Status:** Development — not preregistered

## Provisional scientific question

> In a matched energetic environment, does direct access to actual internal
> energy improve viability and adaptive resource use relative to a competent
> energy-blind controller using a conservative fixed recharge/exploration
> schedule?

EXP-001 is a development investigation, not yet a preregistered causal claim.
No confirmatory protocol, acceptance seeds, calibration grid, inferential
procedure, success threshold, or frozen timer/contact value has been selected.

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
energy-aware closed-loop homeostasis with conservative energy-blind open-loop
homeostasis. Because the policies differ in their transition trigger, EXP-001
must not be overstated as isolating information alone unless the final design
justifies that interpretation.

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

- `EXPLORE` → `SEEK_RESOURCE` when actual energy falls below the inherited
  development threshold;
- `SEEK_RESOURCE` → `CHARGE` on a configurable external resource-contact
  criterion, using the shared local resource steering logic otherwise;
- `CHARGE` uses `WAIT` until actual energy rises above the inherited recovery
  threshold, then returns to `EXPLORE` with a new stochastic run.

The initial development values `0.35` and `0.85` are inherited EXP-000
development thresholds, not frozen EXP-001 protocol values.

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

## True sensory boundary

The controller-facing boundary is explicit:

- A and C receive only `left_resource, forward_resource, right_resource`;
- B receives `actual_energy` plus the exact same three external signals.

Environment and evaluator code may retain actual energy for viability,
termination, and scientific telemetry. That privileged state is not a C
contact sensor and does not enter A or C actions.

## Programmed mechanism

The A/B/C policies, the shared stochastic explorer, local resource steering,
resource-contact test, mode transitions, timers, and `WAIT` charging action are
programmed mechanisms. They are not learned behaviour. Development behaviour
must not be presented as experimental evidence.

## Development parameters

The following remain explicit, changeable development parameters: explorer
hazard, external resource-contact threshold, blind exploration duration, blind
charging duration, inherited B energy thresholds, and environment/body/resource
values. The numeric contact threshold and blind timer values are intentionally
required configuration inputs rather than frozen production protocol defaults.

## Calibration and confirmatory inference

Calibration is not yet designed. Confirmatory inference is not yet designed.
No acceptance seeds are created or executed in this development slice. No
formal EXP-001 success threshold, horizon, primary endpoint, effect-size rule,
or statistical analysis is defined here.

## Scientific claim

None yet. EXP-001 development establishes a transparent behavioural foundation
for deciding whether a later, properly designed experiment is scientifically
interpretable. It makes no claim about consciousness, emotion, subjective
experience, genuine life, biological metabolism, intelligence, learning, or
emergent behaviour.
