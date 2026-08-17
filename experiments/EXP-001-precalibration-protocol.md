# EXP-001 — Pre-calibration Protocol

**Design status:** pre-calibration design; not preregistered

**Design revision:** `EXP-001-precalibration-003`

**Formal calibration status:** not executed

**Confirmatory status:** not executed

This document freezes the EXP-001 pre-calibration design. It contains no
calibration results, confirmatory results, inferential claim, or candidate
value selected from observed outcomes. EXP-000 remains permanently closed and
frozen.

## Scientific question

> Does closed-loop regulation using actual internal energy improve viability
> relative to a competent energy-blind controller using a calibrated fixed
> temporal regulation schedule?

The intended causal comparison is B versus calibrated C. This is not described
as isolating “information alone”. B and C differ specifically in how
homeostatic mode timing is regulated: B uses actual internal energy, while C
uses fixed temporal rules. Both retain the same external L/F/R resource sensing
and the same resource-directed steering and contact criterion.

## Scope and non-goals

This protocol is for formal EXP-001 pre-calibration design only. It does not
authorize or execute either formal calibration or confirmatory seeds. It does
not change the controllers, the environment implementation, EXP-000, or the
development visualizer.

The following are out of scope for this experiment: learning, temporal
chemotaxis, energy prediction, memory, adaptive timers, reinforcement-learning
reward, a composite efficiency score, narrowed resource geometry, and any
later-stage Aweform capability.

The environment reward remains exactly `0.0` on every transition. The energy
variable remains an engineered viability state, not biological metabolism and
not a reward score.

## Fixed EXP-001 mechanism and environment

The formal design retains the merged EXP-001 development foundation:

- The existing smooth renewable circular resource field is unchanged. The
  field is not narrowed for EXP-001; narrower resource geometry is deferred to
  a later experiment such as EXP-002.
- Existing external left/forward/right resource sensing is retained.
- Resource contact is the existing external criterion
  `max(left_resource, forward_resource, right_resource) >=
  resource_contact_threshold`.
- `resource_contact_threshold = 0.8`.
- The contact criterion is an externally detectable resource
  contact/proximity proxy, not literal physical docking or body contact.
- B uses `enter_seek = 0.35` and `recover = 0.85`.
- The stochastic EXPLORE geometric hazard is fixed at `p = 1/8`.
- One turn action remains 45° (`pi / 4`); two same-direction turn actions
  produce 90°. No 90° environment action is added.
- No learning, temporal chemotaxis, energy prediction, memory, or adaptive
  timers are introduced.
- The formal episode horizon is 1000 transitions. Lifespan is capped at this
  horizon for calibration and the planned confirmatory endpoint.

The remaining environment values are fixed to the merged foundation defaults,
with only the horizon changed to the value above:

| Parameter | Value |
| --- | ---: |
| world bounds | `[(0.0, 0.0), (1.0, 1.0)]` |
| maximum / failure energy | `10.0 / 0.0` |
| initial energy | `5.0` |
| basal cost per transition | `0.1` |
| forward movement distance | `0.05` |
| `WAIT` / turn / forward action cost | `0.0 / 0.02 / 0.1` |
| directional probe distance / sensor angle | `0.1 / pi / 4` |
| harvest rate | `0.5` |
| resource peak / length scale / source count | `1.0 / 0.25 / 1` |

These values must not be changed after calibration seeds are inspected without
declaring a new experiment revision.

### Conditions

#### A — stochastic persistent-exploration reference

A receives only external L/F/R signals and remains in `EXPLORE`. It uses the
shared stochastic run-and-turn explorer and ignores the resource signals for
exploration action selection. A is a descriptive behavioural reference, not
part of the primary causal comparison.

#### B — interoceptive closed-loop homeostasis

B receives actual normalized internal energy plus the same external L/F/R
signals as C. It starts in `EXPLORE` and uses the fixed programmed modes:

- `EXPLORE` → `SEEK_RESOURCE` when actual energy is below `0.35`;
- `SEEK_RESOURCE` → `CHARGE` when the shared external contact criterion is met,
  otherwise use the shared local resource steering logic;
- `CHARGE` uses `WAIT` until actual normalized energy is above `0.85`, then
  returns to `EXPLORE` with a new stochastic run.

#### C — energy-blind open-loop homeostasis

C receives only external L/F/R signals. It receives no energy value, fixed or
otherwise, and maintains no estimated-energy state. It uses one of the three
fixed timer candidates below:

- `EXPLORE` → `SEEK_RESOURCE` after the candidate's blind exploration duration;
- `SEEK_RESOURCE` → `CHARGE` on the same external contact criterion as B,
  otherwise use the same local steering logic;
- `CHARGE` uses `WAIT` for the candidate's blind charging duration, then
  returns to `EXPLORE`.

Timers count environment transitions/actions, including turns and `WAIT`, not
only forward movement. C never knows that it is fully charged.

## C calibration candidates

Exactly these three candidates are permitted:

| Candidate | Blind EXPLORE duration | Blind CHARGE duration |
| --- | ---: | ---: |
| `SHORT` | 10 | 5 |
| `CURRENT` | 20 | 10 |
| `LONG` | 30 | 15 |

The candidates all preserve the 2:1 EXPLORE:CHARGE ratio while varying the
overall timescale. No additional candidate may be added after calibration data
are seen. B thresholds, contact threshold, resource geometry, and the
environment must not be tuned from calibration outcomes.

## Seed reservation and separation

### Calibration/development seeds

The formal C calibration seed set is exactly **20001–20200 inclusive** (200
seeds). The same seed is used across all three C candidates. These seeds are
calibration/development data and are not confirmatory evidence.

Previously used debug seeds, including seed `42` and the `701` series, are not
part of formal calibration.

### Untouched confirmatory seeds

The confirmatory seed set is exactly **30001–31000 inclusive** (1000 matched
seeds). These seeds must not be executed, visualized, summarized, inspected,
used in tests, used for debugging, used for calibration, or replaced because
their results are inconvenient.

No confirmatory command is provided by this pre-calibration slice.

## Calibration objective and selection rule

Calibration exists only to select a competent C open-loop baseline. Selection
must use C outcomes exclusively.

For each candidate, calculate mean capped lifespan over the 200 calibration
seeds. The frozen deterministic selection rule is applied in this order:

1. retain candidate(s) with the highest C mean capped lifespan;
2. among those still tied, retain candidate(s) with the higher C
   horizon-survival count;
3. among those still tied, retain candidate(s) with the higher C mean minimum
   normalized energy;
4. if more than one candidate is still exactly tied after criteria 1–3, use
   the fixed canonical tie priority `CURRENT` > `SHORT` > `LONG` and select
   the highest-priority remaining candidate.

The final priority applies only among candidates still tied after criteria 1–3.
For example:

- `CURRENT` and `SHORT` tied after criteria 1–3 → select `CURRENT`;
- `CURRENT` and `LONG` tied → select `CURRENT`;
- `SHORT` and `LONG` tied, with `CURRENT` already eliminated → select `SHORT`;
- all three exactly tied → select `CURRENT`.

This final priority is a deterministic bookkeeping convention only. It does
not express a scientific claim that one timer schedule is intrinsically
preferable.

If the calibration run is technically valid, this rule always selects exactly
one of the three predeclared candidates. The result must not be rejected
because the candidates appear close, weak, surprising, or inconvenient.

A calibration run may be rejected only for a genuine technical-validity
failure, such as a wrong seed set, wrong configuration or protocol revision,
incomplete execution, determinism or replay failure, corrupted or malformed
artifacts, or an implementation mismatch with this frozen protocol. Scientific
dissatisfaction with candidate performance is not a technical-validity
failure.

The selection artifact/process must not use, persist, summarize, or display as
selection inputs:

- any B−C difference;
- B mean lifespan or whether B beats C;
- A performance;
- B effect size;
- favourable or unfavourable individual seeds;
- confirmatory results; or
- visual attractiveness of trajectories.

The preferred calibration artifact exposes only one row per C candidate and
the C diagnostics defined below. If implementation reuse executes A or B
internally, their outcomes must remain transient and must not be persisted,
summarized, displayed, or passed into selection.

## Calibration-seed retirement after protocol revision

If any formal calibration result from seeds `20001–20200` has been inspected
and the scientific protocol is subsequently revised, those seeds become
retired development/calibration data. They must not be reused to select
parameters for the revised protocol.

Any revised design requiring new calibration must declare a new
experiment/protocol revision and reserve a new, previously unexecuted
calibration seed set before execution. The existing confirmatory seeds
`30001–31000` remain untouched unless an independent protocol revision
explicitly replaces them before any of them have ever been executed. No
replacement calibration range is reserved by this document.

## Permitted C calibration diagnostics

These are descriptive calibration diagnostics only; no inferential scientific
claim is made from them:

- episode count;
- mean, median, minimum, and maximum capped lifespan;
- horizon-survival count and fraction;
- mean final normalized energy;
- mean minimum normalized energy;
- mean total harvested energy;
- time/actions in `EXPLORE`, `SEEK_RESOURCE`, and `CHARGE`; and
- number of complete `EXPLORE` → `SEEK_RESOURCE` → `CHARGE` → `EXPLORE`
  cycles.

`Capped lifespan` is the number of completed environment transitions before
termination, capped at 1000. A horizon survivor reaches 1000 transitions
without terminating for loss of viability. Minimum normalized energy includes
the initial normalized energy and the post-transition normalized energies.
Mode time counts transitions under the controller mode recorded immediately
before each action. A complete cycle requires the ordered mode sequence shown
above and a return to `EXPLORE` after `CHARGE`.

## Planned confirmatory comparison

After C calibration is complete and the final protocol is frozen, the primary
causal comparison is B versus the calibrated C on the 1000 untouched matched
seeds. A remains descriptive only.

For matched seed `i`, define the primary per-seed endpoint:

`D_i = capped_lifespan_B_i - capped_lifespan_C_i`

The planned aggregate is the mean paired `D_i` across all 1000 confirmatory
seeds. The prespecified paired percentile-bootstrap interval and confirmatory
interpretation are frozen in
[`EXP-001-confirmatory-statistical-addendum.md`](EXP-001-confirmatory-statistical-addendum.md).
Formal calibration execution must not be authorized until that addendum has
received independent review and has been merged. No confirmatory analysis is
executed or finalized here.

Possible post-confirmation descriptive diagnostics are limited to B>C / B=C /
B<C counts, survival fractions, final and minimum energy, harvested energy,
action energy costs, distance, controller-mode time, and completed recharge
cycles. These diagnostics are not a composite score and do not replace the
primary paired lifespan endpoint.

## Reproducibility and reporting boundary

Formal runs must preserve deterministic seeds, matched environment generation,
separate policy streams, the explicit A/B/C observation boundary, and a run
manifest containing the experiment revision, Git commit SHA, configuration,
seed, condition, runtime information, and output schema version if present.

The calibration record must state the candidate-selection rule, exact seed
range, diagnostics, and selected candidate without including prohibited A/B or
confirmatory selection inputs. The confirmatory record must remain separate
from calibration data.

This protocol makes no claim about consciousness, emotion, subjective
experience, genuine life, biological metabolism, intelligence, learning, or
emergent behaviour.
