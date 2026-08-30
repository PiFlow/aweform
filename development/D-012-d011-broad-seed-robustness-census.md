# D-012 — D-011 broad-seed robustness census

- **id:** D-012
- **date:** 2026-08-30
- **authoritative_base_sha:** `f39cd664896008e856a2a8b132437a914235f980`
- **commit_a_sha:** `fe15dea90dc71fd9990ee66332254ffa408a62fc`
- **executed_commit_sha:** `fe15dea90dc71fd9990ee66332254ffa408a62fc`
- **commit_b_sha:** pending until this record is committed
- **development_seeds:** `18144–18343` (exactly 200 seeds)
- **horizon:** `1000` transitions per lifetime
- **disposition:** `CONTINUING`

## Question

Across a substantially broader legal development block, how often does the
unchanged D-011 fixed controller maintain viability and repeatedly complete
thermal departure → physical charger exit → away/exploration → low-energy
SEEK → beacon-guided physical charger reacquisition → recharge in one
continuous lifetime?

This is development-only descriptive work. It makes no confirmatory claim and
does not test or add learning.

## Seed declaration and execution

The exact nearby block `18144–18343` was checked programmatically through the
canonical `validate_exp003_development_seeds` validator before declaration.
It excludes D-011's `18141–18143` and every formal EXP-000 through EXP-003
reservation. D-012's own validator accepts only this exact 200-seed tuple and
does not weaken the canonical formal-reservation guard.

The accepted executable was Commit A
`fe15dea90dc71fd9990ee66332254ffa408a62fc`. The full block was executed once,
at horizon `1000`, with no resets or reseeding within a lifetime. The generated
machine-readable artifact preserves all per-seed D-011 records, including
termination state, viability extrema, event counts, action counts, mode
occupancy/entries, and D-011 SEEK episode/evaluator-only summaries.

## World and mechanism

**PROGRAMMED:** D-002 thermal/energy ecology, EXP-003 beacon/contact
semantics, post-contact setup, and the fixed `D011Controller` were reused
unchanged through `d011._run_seed`. No thresholds, action logic, explorer,
charging radius, horizon semantics, or thermal/energy logic were changed.

**ORGANISM-VISIBLE:** the inherited D-011 channels remain energy,
`beacon.left`, `beacon.forward`, `beacon.right`, physical charging contact,
and thermal state, plus the controller's own phase and policy-RNG state.

**EVALUATOR-ONLY:** aggregation, true geometry, transition telemetry, and
SEEK navigation summaries. No evaluator aggregation or geometry was passed to
the controller. Reward remained `0.0` and `info` remained `{}`.

**LEARNED:** none. D-008, model predictions, reward, and plastic state were
not used.

## Aggregate observations

Direct observations from
[`D-012-d011-broad-seed-robustness-census.json`](D-012-d011-broad-seed-robustness-census.json):

| Measure | Result |
|---|---:|
| Lifetimes | `200` |
| Survived to horizon | `200/200` (`1.0000`) |
| Energy failures | `0` |
| Thermal failures | `0` |
| Combined viability failures (either) | `0` |
| Seeds with ≥1 completed cycle | `200/200` (`1.0000`) |
| Completed cycles, min / median / mean / max | `9 / 11 / 10.865 / 12` |
| Low-energy SEEK entries | `2218` |
| Successful reacquisitions | `2173` |
| Reacquisition rate where SEEK occurred | `2173/2218` (`0.979711`) |
| Seeds with failed SEEK episodes | `45` |
| Total failed SEEK episodes | `45` |
| Minimum of minimum raw energy | `0.160000` |
| Median minimum raw energy | `1.160000` |
| Minimum of minimum normalized energy | `0.016000` |
| Median minimum normalized energy | `0.116000` |
| Maximum observed thermal state | `0.630000` |

Completed-cycle frequencies were: `9` cycles on 1 seed, `10` on 41 seeds,
`11` on 142 seeds, and `12` on 16 seeds.

Successful SEEK-to-reacquisition latency had `2173` observations: minimum
`1`, median `16`, mean `16.584906`, and maximum `30` transitions. The full
frequency distribution is preserved in the JSON artifact.

Pooled action totals were `MOVE_FORWARD 81,141` (`0.405705`), `TURN_LEFT
12,523` (`0.062615`), `TURN_RIGHT 12,790` (`0.063950`), and `WAIT 93,546`
(`0.467730`). Pooled mode occupancy was `AWAY 59,502` (`0.297510`), `CHARGE
93,657` (`0.468285`), `DEPART 8,310` (`0.041550`), and `SEEK 38,531`
(`0.192655`). Mode-entry totals were `AWAY 2,276`, `CHARGE 2,371`, `DEPART
2,282`, and `SEEK 2,218`.

## Surprised by and near-failures

The fixed loop survived every seed, but 45 seeds reached the horizon during
an unresolved final SEEK episode. All 45 were horizon-truncated, with no
energy or thermal termination; each had exactly one failed/censored SEEK
episode. This makes the `97.9711%` reacquisition rate materially different
from a claim that every entered SEEK episode reacquired before the fixed
horizon.

The lowest raw-energy minimum was `0.16` (normalized `0.016`), yet that seed
also survived without viability termination. These are descriptive edge
observations, not evidence that the controller is universally robust or that
the ecology is safe under other setups.

## Provisional reading

**Direct observation:** The controller is highly viable across this declared
block and repeatedly completes the intended loop at least once on every seed.
It also shows seed-dependent variation in cycle count, SEEK latency, and
horizon-censored final SEEK episodes.

**Inference:** This is best classified as **B — mixed**, because meaningful
seed-dependent incomplete SEEK episodes remain even though no lifetime dies.
The immediate next step is to preserve and inspect the smallest causal reason
for those censored episodes before adding learned control; D-012 does not
automatically justify tuning D-011.

No claim is made about universal robustness, learned navigation, optimality,
arbitrary initial charger discovery, noise/occlusion robustness, consciousness,
emotion, genuine life, or evidence-lane confirmation.

## Next

Inspect the 45 horizon-censored SEEK trajectories and their terminal
controller/environment state as a descriptive causal audit. Keep the D-011
controller as the fixed reference if a later shadow-learning experiment is
explicitly authorized; do not implement that learner in D-012.
