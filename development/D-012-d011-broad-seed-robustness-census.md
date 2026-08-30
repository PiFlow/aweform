# D-012 — D-011 broad-seed robustness census

- **id:** D-012
- **date:** 2026-08-30
- **authoritative_base_sha:** `f39cd664896008e856a2a8b132437a914235f980`
- **prior_executed_commit_sha:** `fe15dea90dc71fd9990ee66332254ffa408a62fc` (superseded)
- **commit_a_sha:** `30ab6bfe57982aa019ee023b43e0bf2588614cd3`
- **executed_commit_sha:** `30ab6bfe57982aa019ee023b43e0bf2588614cd3`
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

The prior artifact was generated from
`fe15dea90dc71fd9990ee66332254ffa408a62fc`; its D-012 reporting semantics
were repaired before this rerun. The accepted repaired executable was Commit A
`30ab6bfe57982aa019ee023b43e0bf2588614cd3`. The full block was rerun once from
that exact SHA, at horizon `1000`, with no resets or reseeding within a
lifetime. The generated machine-readable artifact preserves per-seed D-011
summary records, including termination state, viability extrema, event counts,
action counts, mode occupancy/entries, and SEEK episode summaries, while
omitting the full per-transition SEEK geometry trajectories.

## World and mechanism

**PROGRAMMED:** D-002 thermal/energy ecology, EXP-003 beacon/contact
semantics, post-contact setup, and the fixed `D011Controller` were reused
unchanged through `d011._run_seed`. No thresholds, action logic, explorer,
charging radius, horizon semantics, or thermal/energy logic were changed.

**ORGANISM-VISIBLE:** the inherited D-011 channels remain energy,
`beacon.left`, `beacon.forward`, `beacon.right`, physical charging contact,
and thermal state, plus the controller's own phase and policy-RNG state.

**EVALUATOR-ONLY:** runtime aggregation, true geometry, transition telemetry,
and SEEK navigation summaries. The compact D-012 artifact stores bounded
per-seed summaries and omits full per-transition SEEK geometry. No evaluator
aggregation or geometry was passed to the controller. Reward remained `0.0`
and `info` remained `{}`.

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
| Resolved SEEK episodes | `2173` |
| Resolved SEEK successes | `2173/2173` (`1.000000`) |
| Horizon-censored SEEK episodes | `45` |
| Seeds with horizon-censored SEEK episodes | `45` |
| Demonstrated failed SEEK episodes | `0` |
| Raw reacquisitions / all SEEK entries | `2173/2218` (`0.979711`) |
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
energy or thermal termination; each had exactly one horizon-censored SEEK
episode and zero demonstrated SEEK failures. Therefore the raw
`2173/2218` fraction is not the definitive-outcome success rate: among the
`2173` resolved SEEK episodes, success was `2173/2173`.

The lowest raw-energy minimum was `0.16` (normalized `0.016`), yet that seed
also survived without viability termination. These are descriptive edge
observations, not evidence that the controller is universally robust or that
the ecology is safe under other setups.

## Provisional reading

**Direct observation:** The controller is highly viable across this declared
block and repeatedly completes the intended loop at least once on every seed.
It also shows seed-dependent variation in cycle count, SEEK latency, and
horizon-censored final SEEK episodes.

**Inference:** This is best classified as **A — broadly robust within this
200-seed development block**, with a censoring caveat. Every lifetime survived,
every seed completed at least one cycle, and every resolved SEEK episode
reacquired the charger (`2173/2173`); 45 final SEEK episodes were censored by
the finite horizon rather than demonstrated failures. This does not establish
universal robustness or success beyond the declared horizon. D-012 does not
authorize learned action selection, model-guided control, counterfactual
action choice, or a larger learner. It does support using unchanged D-011 as
the fixed behavioural scaffold for the next explicitly authorized
SHADOW-ONLY learning stage.

No claim is made about universal robustness, learned navigation, optimality,
arbitrary initial charger discovery, noise/occlusion robustness, consciousness,
emotion, genuine life, or evidence-lane confirmation.

## Next

Use unchanged D-011 as the fixed behavioural scaffold for the next
SHADOW-ONLY learning stage, if that stage is explicitly authorized. D-012
does not authorize learned action selection, model-guided control,
counterfactual action choice, or a larger learner. Inspection of the 45
horizon-censored terminal states remains optional diagnostic work; ordinary
endpoint censoring is not a required causal-audit gate before shadow learning.
