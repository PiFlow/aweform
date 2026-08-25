# EXP-004 — Ecological robustness probe

**Protocol status:** frozen design; implementation review only

**Execution status:** no calibration, characterization, confirmatory, or
acceptance execution is authorised by this document

**Protocol revision:** `EXP-004-R95-002`

**Stage:** V0.2, subject to the prerequisites below

This document freezes the EXP-004 controller, perturbation, seed, endpoint,
and analysis choices. It is a protocol, not evidence of a result. No result
may be used to change this document's mechanisms, timing, seed roles, endpoint,
or analysis rule without a named protocol revision and a fresh review.

## Prerequisites and execution gate

No reserved seed may be touched until all of the following are true:

1. ADR 0009 is merged and accepted.
2. PR #38's trend controller is merged with its exact merge SHA and frozen
   configuration recorded in the run manifest. The development source tree
   used to define the mechanism is
   `6b069f64bf239e3260ec7ae5a31979c6d85ec297`; that tree is not itself a
   substitute for the required merge-SHA pin.
3. The BOHS registry and enforcement checks required by ADR 0009 exist and
   pass, including adversarial type, path, cadence, clearing, lifetime,
   provenance, and reader checks.
4. The implementation, protocol, seed guard, and analysis artifacts have
   received independent review against exact commits.

If the T prerequisite does not land, EXP-004 is blocked. This revision does
not silently drop T after inspecting any EXP-004 data.

## Scientific question and scope

EXP-001's `C_GREATER` result was obtained in a stationary environment. EXP-004
tests whether a calibrated station-compatible fixed schedule and an
interoceptive controller behave differently when the sole charging station is
relocated once during an episode. The primary comparison is whether B's
relative advantage over the new station comparator changes between stationary
and relocation conditions. The key secondary asks the analogous question for
the one-step beacon-history controller T relative to B.

This is a difference-in-differences result inside one frozen simulator. It does
not measure general ecological robustness, biological adaptation, or learning.
The relocation is externally imposed; it is not adaptation or learning.

## Included controllers and conditions

Each master seed produces six matched cells:

| Controller | Information available | Stationary | Relocation |
|---|---|---:|---:|
| `STATION_B50_R95` (B) | normalized energy, L/F/R beacon, charging contact | yes | yes |
| calibrated station comparator (C) | L/F/R beacon, charging contact only | yes | yes |
| `STATION_B50_TREND_R95` (T) | B observations plus one registered BOHS value | yes | yes |

The station comparator never receives energy, evaluator state, coordinates,
time, relocation status, or controller state. B and T use the same
controller-visible normalized-energy recovery rule:

- leave `CHARGE` when energy is `>= 0.95`; equality triggers departure;
- immediately choose the EXPLORE action on that decision;
- record energy at the CHARGE-exit decision and energy after the exit
  transition separately;
- do not describe this rule as guaranteeing 100% charge.

These are explicit EXP-004 conditions. They do not modify EXP-003
`STATION_B50` or `StationB50Controller` defaults. The energy-blind comparator
uses its separately calibrated fixed-duration schedule instead.

The implementation must expose additive EXP-004 classes named
`StationB50R95Controller` and `StationB50TrendR95Controller`; the historical
`StationB50Controller` and `StationB50TrendController` classes remain
unchanged. Both R95 classes must use this exact frozen configuration before
any master-seed run:

| Field | Frozen value / rule |
|---|---|
| `enter_seek` | `0.50` |
| `recover` | `0.95`, with `>=` departure at the CHARGE decision |
| `exploration_hazard` | `EXP001_EXPLORER_HAZARD` |
| trend energy threshold | `0.65` (`Final[float]`) for T only |
| weak-beacon threshold | `0.10` (`Final[float]`) for T only |
| environment | `EXP003StationConfig()` defaults, including horizon `1000` |

The exact merged implementation SHA, class names, configuration serialization,
and source-tree identity must be recorded in every run manifest. A branch or
development-tree SHA is not an acceptable substitute.

T is included as the key-secondary controller, not as an optional arm in this
revision. Its inclusion is contingent on the prerequisites above, and no
partial two-arm analysis is authorised if T is unavailable.

## Environment and hidden relocation

The experiment reuses the EXP-003 localized charging-station environment and
its observation boundary. The horizon is exactly 1000 transitions, inherited
from EXP-001 through EXP-003. Controllers receive only their stated
observations; station coordinates, true distance, body position, heading,
relocation time, and future outcomes remain evaluator-only.

For every master seed, generate one hidden relocation schedule:

1. Perform one canonical `EXP003StationConfig()` reset for the master seed and
   record the resulting initial body position, heading, and initial station
   centre. This canonical reset consumes the ordinary environment stream only.
   Every one of the six cells independently resets with the same master seed
   and must reproduce that exact initial state before any relocation is
   applied; a mismatch is a deterministic execution error, not a reason to
   resample.
2. Draw an integer anchor `tau` uniformly from `400..600`, inclusive.
3. Draw one target station centre from `[0.10, 0.90] x [0.10, 0.90]` by
   rejection sampling. Accept the first candidate whose Euclidean distance
   from the initial station centre is strictly greater than `0.20`.
4. Permit exactly 10,000 target candidates. If none is valid, raise a
   deterministic error; there is no fallback or resampling policy.
5. In the relocation cell, immediately before the controller observation and
   action for transition `tau`, the old station disappears atomically and the
   target becomes the sole beacon and charger.
6. In the stationary cell, use the same `tau` as a pseudo-event anchor but do
   not move the station.

The target is generated once per master seed and reused unchanged across B, C,
and T and across both conditions. After the canonical reset, target rejection
reads only the recorded initial station centre; it does not directly read body
position, energy, mode, controller state, or any cell trajectory. A target that
happens to appear near one controller is retained; it is part of the frozen
perturbation.

The per-master-seed run manifest must record the protocol revision, exact
implementation merge SHA, all frozen controller configurations, `master_seed`,
`tau`, canonical initial body position and heading, initial station centre,
target station centre, stationary/relocation condition, controller arm, and
output-schema version. These values are recorded before the cell outcome is
summarized and are identical across the six matched cells except for the
controller/condition fields and the relocation state.

The post-anchor endpoint `tau + 399` is therefore at most transition 999.
Episodes that terminate before `tau` are retained with no replacement or
conditioning on post-event survival.

## Independent perturbation randomness

`RandomStreams.from_seed(master_seed)` and its existing environment and policy
streams remain unchanged. The relocation schedule uses a separate generator:

```python
np.random.Generator(
    np.random.PCG64(
        np.random.SeedSequence([master_seed, 0x45585034])
    )
)
```

`0x45585034` is the fixed domain tag for EXP-004. Do not use `default_rng` for
this generator and do not consume environment or policy draws. Draw order is
fixed: `tau` first with `integers(400, 601)`, then target x/y candidates in
rejection order. Derive the immutable schedule once per master seed outside
controller execution and apply it identically to every cell.

Required tests must prove replay determinism, unchanged pre-event
stationary/relocation trajectories for each controller, and no perturbation
draw consumption by the environment or policy streams.

## Station-compatible energy-blind comparator

The comparator uses the same local beacon steering, SEEK contact semantics, and
immediate contact-loss return to SEEK as B and T, but it never reads energy.
Its only calibrated parameters are:

| Parameter | Candidate values |
|---|---|
| EXPLORE duration | 20, 30, 40 transitions |
| continuous-contact CHARGE duration | 15, 18, 21 WAIT transitions |

All nine Cartesian candidates are evaluated. A candidate performs exactly N
EXPLORE actions and then enters SEEK on the next decision. On first charging
contact, the first WAIT is CHARGE action 1. After exactly M consecutive
contact-preserving WAIT transitions, the next decision starts EXPLORE. Contact
loss returns to SEEK immediately and resets the CHARGE counter; partial charge
time is never resumed. The comparator starts every cell in `EXPLORE` with a
fresh `StochasticPersistentExplorer` using that cell's policy RNG stream. Its
run-and-turn primitive, beacon steering, action tie rules, and RNG draw order
are exactly those inherited from EXP-001/EXP-003; only the N/M mode counters
are new. The EXPLORE counter starts at zero, the first N EXPLORE actions are
counted, and the next decision enters SEEK. At that fixed N-to-SEEK boundary,
call `StochasticPersistentExplorer.begin_segment()` exactly once: it sets
`_forward_actions_remaining` to `0`, `_turn_action` to `None`, and
`_turn_actions_remaining` to `0`, without reseeding or advancing the policy
RNG. A contact-preserving CHARGE WAIT increments the counter; contact loss
resets it to zero; after M such WAIT transitions the next decision starts
EXPLORE and the counter is reset. At that fixed M-to-EXPLORE boundary, call
`begin_segment()` exactly once with the same reset/no-RNG-draw semantics. No
counter or partial segment is carried across `reset()` or cells.

Calibration uses only stationary comparator outcomes on seeds `80001–80200`.
B, T, relocation outcomes, and any B/C or T/B contrast are forbidden inputs to
selection and must not be persisted in the comparator-selection artifact.

Select lexicographically by:

1. highest mean 1000-transition capped lifespan;
2. highest horizon-survival count;
3. highest evaluator-only mean minimum normalized energy;
4. smallest `abs(EXPLORE - 30) + abs(CHARGE - 18)`;
5. smaller EXPLORE duration;
6. smaller CHARGE duration.

The rule always selects one technically valid candidate, even when all
candidates are weak or close. The final three criteria are deterministic
bookkeeping tie-breakers, not scientific outcomes. The development basis for
the grid is EXP-003 evidence that departure-to-next-SEEK intervals were near
29–31 transitions and acquisition energy was near 0.242; this is not a claim
that any candidate is optimal.

## Seed roles and pre-confirmatory gate

The seed ranges are disjoint and fixed for this protocol revision:

| Role | Seeds | Use |
|---|---:|---|
| comparator calibration | `80001–80200` | select C on stationary cells only |
| development characterization | `81001–81200` | complete matched six-cell blocks |
| untouched confirmation | `90001–91000` | confirmatory analysis only |

Free debug/test seeds must be outside every EXP-000–004 reserved range. No
seed may migrate between roles. After inspecting a role's results, any change
to mechanism, grid, timing, endpoint, or analysis retires the inspected range
and requires a named protocol revision with fresh reservations. Confirmatory
seeds remain untouched until the pre-confirmatory gate passes.

All 200 characterization seeds must run as complete matched six-cell blocks.
For each included controller, at least 180/200 matched trajectories must
remain viable at the beginning of transition `tau`. This 90% relocation-
exposure threshold inherits
EXP-002's predeclared viability-eligibility convention. Failure blocks
confirmation and requires a new protocol revision and characterization range;
individual seeds may not be excluded or replaced.

Transition indices are zero-based. A transition index identifies the
pre-action observation and action decision at that index. “Viable at the
beginning of `tau`” means the cell has not terminated before the observation
for transition `tau`; if the action at `tau` terminates the cell, transition
`tau` is still counted in the endpoint window because it began viable. A cell
that terminates before the observation for `tau` is not eligible and receives
`Y=0`.

These ranges were not found in the current repository before this protocol was
written. That is repository evidence only, not proof that they were never run
externally. The implementation seed guard must make the reservation
authoritative before execution.

## Endpoint and estimands

For controller X, condition `c`, and master seed `i`, define `Y[X,c,i]` as the
number of transition records whose pre-action state is viable and whose
zero-based index lies in the fixed window `tau_i..tau_i+399`, inclusive,
capped at 400. The relocation, if any, is applied before the observation and
action at index `tau_i`. A cell that terminated before the observation at
`tau_i` has `Y=0`; a cell viable at every window start has `Y=400`; a terminal
action at index `tau_i+q` contributes that one record and no later records.
Stationary cells use the same pseudo-anchor and canonical initial state. No
seed is conditioned on post-event survival.

The primary seed-level contrast is:

```text
d_B,i = (Y[B,R,i] - Y[C,R,i]) - (Y[B,S,i] - Y[C,S,i])
```

The primary estimand is `Delta_B = mean_i(d_B,i)`. Positive `Delta_B` means
B's mean relative advantage over calibrated C is larger under relocation than
under stationarity. It does not imply that B beats C in either condition; all
four component means and both simple B-minus-C contrasts must be reported.

The key-secondary contrast is:

```text
g_T,i = (Y[T,R,i] - Y[B,R,i]) - (Y[T,S,i] - Y[B,S,i])
```

The key-secondary estimand is `Gamma_T = mean_i(g_T,i)`. Positive `Gamma_T`
means T's mean relative advantage over B is larger under relocation. It is not
co-primary and cannot rescue or negate the primary conclusion.

R95 diagnostics separately record controller-visible energy at CHARGE exit and
post-exit-transition energy. A decision-time value `>= 0.95` is not a claim of
100% charge.

## Confirmatory analysis and interpretation

The sampling unit is one matched master-seed six-cell block; cells are never
resampled independently. Initialize exactly one
`Generator(PCG64(94004))` before replicate 1 and advance it continuously
through all `100_000` paired bootstrap replicates; do not reinitialize it per
replicate or estimand. Each replicate samples 1,000 seed indices with
replacement from `[0, 1000)`, using the same sampled indices for `Delta_B` and
`Gamma_T` to preserve covariance. For each estimand, if `boot` is its 100,000
element bootstrap vector, compute the central interval as
`numpy.percentile(boot, [2.5, 97.5], method="linear")`; report those lower and
upper endpoints as the ordinary two-sided 95% interval.

No p-value, BCa interval, studentization, one-sided interval, adaptive
resampling, or post-result method change is permitted.

For either estimand:

- interval wholly above zero: support for a larger relative advantage under
  relocation;
- interval wholly below zero: support for a smaller relative advantage under
  relocation;
- interval including zero: unresolved directional change, not equality.

`Gamma_T` receives the same directional reading as a key secondary, but no
independent headline success claim. Every outcome is publishable and final for
this protocol revision. An unfavorable or unresolved result cannot trigger a
rerun, seed replacement, comparator reselection, endpoint substitution, or
threshold adjustment.

## Information boundary and provenance

The observation boundary is inherited from EXP-003 and ADR 0008. Controllers
may receive normalized energy only where this protocol names it, L/F/R beacon
values, and charging contact. They never receive station coordinates, body
position, heading, relocation time, evaluator telemetry, or future outcomes.
The comparator additionally excludes energy by design.

T's one-step state is authorized only by ADR 0009 and must be pinned to the
exact merged PR #38 implementation and configuration before execution. The
PR #38 development tree used to define T is
`6b069f64bf239e3260ec7ae5a31979c6d85ec297`; it is preparatory provenance, not
EXP-004 evidence.

This protocol cites and inherits the EXP-003 environment/interface and
development evidence, EXP-001 calibration/statistical conventions, ADR 0008's
station information boundary, ADR 0009's BOHS boundary, and the reproducibility
policy. It does not retest frozen EXP-001/EXP-002 `C_SHORT` and does not claim
that the station comparator is the historical C.
