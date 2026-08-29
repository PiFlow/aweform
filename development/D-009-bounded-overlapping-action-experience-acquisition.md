# D-009 — Bounded overlapping action-experience acquisition

- **id:** D-009
- **date:** 2026-08-29
- **authoritative_base_sha:** `dd37b551fc6310b189193d34340719ef98776f06`
- **exact_sha:** `3127a70a00b67bb5d97b3852dc5615887329635e` (executable Commit A)
- **executed_commit_sha:** `3127a70a00b67bb5d97b3852dc5615887329635e`
- **development_seeds:** `18141, 18142, 18143`
- **horizon:** `1000`
- **disposition:** `CONTINUING`

## Scientific question

Can a minimal fixed sampling scaffold create direct experience of both `WAIT`
and `MOVE_FORWARD` from the same organism-visible charging observation near
nominal thermal `0.59`, allowing the unchanged D-008 learner to update from
both actions within visited support?

This is ordinary D-lane developmental work. The learned model remained
shadow-only and did not control behaviour.

## D-008 limitation motivating D-009

D-008 demonstrated useful predictive structure within the support visited by
the unchanged D-003 policy. It did not demonstrate supported comparison of
`WAIT` and `MOVE_FORWARD` at the same charging state: under D-003, `WAIT`
covered approximately `0.20` through nominal `0.59`, while `MOVE_FORWARD`
started around nominal `0.60`; `TURN_RIGHT` was unvisited. D-009 therefore
changes data acquisition, not learner capacity, and does not rewrite or label
D-008 a failure.

## Float32 representation correction

D-002 emits observations through `np.float32`. The pre-execution synthetic
test and source declarations therefore freeze both representations:

| Quantity | Nominal decimal | Organism-visible Python float |
|---|---:|---:|
| overlap | `0.59` | `0.5899999737739563` |
| late departure | `0.61` | `0.6100000143051147` |

`D009_EARLY_DEPART_THRESHOLD` equals the exact visible overlap value. The
synthetic typed observation test selects `MOVE_FORWARD` in `EARLY` and `WAIT`
in `LATE`; it executes no environment seed. This prevents a literal-Python
`0.59` comparison from silently reproducing the D-008 gap.

## Programmed sampling scaffold

The controller retains the D-003 phases `CHARGE`, `DEPART`, `COOL`,
`TURN_RETURN`, and `RETURN`, including the existing four left turns and return
mechanics. It adds exactly one controller-owned phase bit:

**PROGRAMMED**

- `EARLY` and `LATE` alternating phase;
- exact float32-visible departure thresholds;
- D-003 shuttle mechanics;
- phase starts `EARLY` for each new lifetime;
- phase toggles only when a natural `RETURN` reaches charging contact and
  emits D-003's normal `WAIT` completion action.

The completion action itself is not retroactively changed; the toggled phase
governs the next `CHARGE` decision. No transition count, energy, horizon,
seed, prediction error, or model output changes the phase.

In `EARLY`, departure occurs at or above
`D009_EARLY_DEPART_THRESHOLD`; in `LATE`, at or above
`D009_LATE_DEPART_THRESHOLD`. Baseline is the unchanged
`ThermostaticShuttleController`.

## Learner architecture

**LEARNED**

D-009 reuses `D008ActionConsequencePredictor` by import, without modifying
`src/aweform/d008.py`:

- feature vector `[1.0, thermal, charging_contact]`;
- outputs delta thermal and delta charging contact;
- actions `WAIT`, `TURN_LEFT`, `TURN_RIGHT`, `MOVE_FORWARD`;
- learning rate `0.5`;
- exactly 24 zero-initialized weights;
- unchanged normalized LMS update;
- no RNG, optimizer, buffer, recurrent state, or model-guided control.

**EVALUATOR-ONLY**

The record retains geometry, energy, mode, phase, cycle, action-visitation,
support, prediction, and termination diagnostics. These values never enter
prediction or plasticity. Reward is exactly `0.0` and info is exactly `{}`.

## Organism-visible/plasticity boundary

At prediction time the predictor receives only current thermal,
`charging_contact`, and the organism's own selected action. After the action
physically occurs, its update receives only the current typed observation,
own executed action, and next typed thermal/contact observation. It receives
no phase, controller mode, energy, coordinates, distance, heading, clock,
seed, condition identity, reward, evaluator telemetry, offered energy,
stored-energy delta, thermal-input truth, success label, or future state.

The causal order was preserved and tested:

1. current typed observation;
2. fixed controller action;
3. pre-update prediction;
4. physical environment step;
5. next typed observation;
6. plastic update;
7. evaluator telemetry read and scoring.

The final common query occurs after the lifetime, performs no step or update,
and preserves the trained weights.

## Exact overlap-support definition

Support is classified by exact equality to:

```text
D003ThermostaticObservation(
    thermal=0.5899999737739563,
    charging_contact=True,
)
```

No broad `abs(thermal - 0.59) <= 0.0001` rule is used. For each action the
artifact records sample count, exact current thermal, next thermal/contact
values, thermal/contact deltas, minima, maxima, means, contact-delta counts,
and distinct next-visible outcomes with frequencies.

## Baseline condition

Baseline uses unchanged D-003 behaviour with the unchanged D-008 shadow
predictor. Across all seeds it had direct `WAIT` support at the exact target
state (13, 14, 13 samples) and zero direct `MOVE_FORWARD` support. Its final
`MOVE_FORWARD` numerical query therefore carries the explicit label
`UNSUPPORTED AT QUERY STATE`.

## Sampler condition

The sampler uses the D-009 controller and the same D-008 predictor
initialization. Each seed completed 13 shuttle cycles, with 7 `EARLY` and 6
`LATE` cycles, starting `EARLY` and ending `LATE`. Exact target support was:

| Seed | WAIT samples | MOVE_FORWARD samples | WAIT distinct outcomes | MOVE_FORWARD distinct outcomes |
|---:|---:|---:|---:|---:|
| 18141 | 6 | 7 | 1 | 1 |
| 18142 | 7 | 7 | 1 | 1 |
| 18143 | 6 | 7 | 1 | 1 |

For every sampler support sample, the next visible consequence was thermal
`0.6000000238418579`, charging contact `True`, delta thermal
`0.010000050067901611`, and delta contact `0.0`.

## Direct observations and overlap-support results

All six lifetimes truncated at the 1000-transition horizon, with no energy or
thermal failure. `TURN_RIGHT` was never artificially forced and had zero
count in every run. The detailed action/contact counts, complete viability
telemetry, final 24-weight states, and checkpoints at 250/500/750/1000 are in
the machine-readable artifact.

| Seed | Condition | Action counts (MOVE / LEFT / RIGHT / WAIT) | Contact / off transitions | Min/final energy | Min/max/final thermal |
|---:|---|---:|---:|---:|---:|
| 18141 | baseline | 64 / 52 / 0 / 884 | 507 / 493 | 5.0 / 9.52000000000002 | 0.20000000298023224 / 0.6300000000000002 / 0.33999999999999997 |
| 18141 | sampler | 64 / 52 / 0 / 884 | 508 / 492 | 5.0 / 10.0 | 0.20000000298023224 / 0.6400000000000002 / 0.36 |
| 18142 | baseline | 51 / 52 / 0 / 897 | 520 / 480 | 5.0 / 10.0 | 0.20000000298023224 / 0.6200000000000002 / 0.6000000000000002 |
| 18142 | sampler | 52 / 52 / 0 / 896 | 521 / 479 | 5.0 / 10.0 | 0.20000000298023224 / 0.6300000000000002 / 0.6200000000000002 |
| 18143 | baseline | 64 / 52 / 0 / 884 | 507 / 493 | 5.0 / 9.52000000000002 | 0.20000000298023224 / 0.6300000000000002 / 0.33999999999999997 |
| 18143 | sampler | 64 / 52 / 0 / 884 | 508 / 492 | 5.0 / 10.0 | 0.20000000298023224 / 0.6400000000000002 / 0.36 |

## Empirical consequence stability/variability

At the exact target state, each action's sampler support had one distinct
next-visible outcome per seed. The same visible state plus the same action did
not produce observed consequence variability. This result is simulator
deterministic; it is not evidence of environmental stochasticity. The
artifact preserves the outcome counts and variability flags even though they
are all false here.

## Partial-observability diagnostic

The diagnostic did not find material same-visible-state/action variability in
this run. This is a bounded result for the sampled exact target and tested
seeds, not proof that the two-field observation is sufficient everywhere.
Evaluator geometry and heading remain hidden and were not exposed to repair
the model.

## Final common-model query

The query used the exact common typed observation and did not reset, step, or
update the predictor. Baseline `MOVE_FORWARD` support was zero on every seed
and is labelled `UNSUPPORTED AT QUERY STATE`. Sampler direct support was true
for both actions on every seed.

The sampler's final predictions were not uniformly interpretable as accurate
local consequence estimates. In particular, final `MOVE_FORWARD` contact
predictions were approximately `-0.4945` for seeds 18141/18143 and `-0.2632`
for 18142, despite direct overlap support showing contact delta `0.0` in all
cases. The numerical prediction is reported as a model output, not as
counterfactual knowledge.

## Prediction metrics

The artifact contains Q1–Q4 and overall learned-versus-zero-change MAE for
thermal and contact deltas. Representative Q1/Q4/overall learned thermal MAE
values were:

| Seed | Condition | Q1 | Q4 | Overall |
|---:|---|---:|---:|---:|
| 18141 | baseline | 0.00111789 | 0.00065213 | 0.00080154 |
| 18141 | sampler | 0.00111791 | 0.00065062 | 0.00080042 |
| 18142 | baseline | 0.00108255 | 0.00060052 | 0.00076463 |
| 18142 | sampler | 0.00108254 | 0.00064300 | 0.00077451 |
| 18143 | baseline | 0.00111789 | 0.00065213 | 0.00080154 |
| 18143 | sampler | 0.00111791 | 0.00065062 | 0.00080042 |

The corresponding contact MAE and all zero-change comparator values are in
the artifact. Overall and quarter MAE values across baseline and sampler
conditions are descriptive only and must not be interpreted as a matched
model-performance comparison because action/state visitation differs between
conditions by design.

## Mechanical inference

The fixed scaffold did what it was designed to do: alternate departure timing
after natural shuttle completion, creating direct support for both actions at
the exact target representation. The stable visible consequence at that
point is consistent with the deterministic D-002 charging transition and
does not establish a general consequence map. The poor local contact query
outputs indicate that direct support alone did not make this simple global
linear predictor reliable at the queried state.

## surprised_by

The main surprise was not support acquisition but its limited effect on the
final linear query: sampler and baseline aggregate MAE remained very similar,
while the sampler uniquely supplied direct `MOVE_FORWARD` support. The
sampler's direct local outcomes were stable, yet its final `MOVE_FORWARD`
contact estimate could remain substantially negative because the unchanged
learner also fits other action/state samples.

## limitations

- This is descriptive D-lane evidence, not confirmation or a matched
  prediction-performance comparison.
- Only three development seeds and one 1000-transition horizon were run.
- Exact support at one visible thermal/contact point does not establish global
  information sufficiency.
- No model-guided action selection was attempted.
- No counterfactual, planning, curiosity, active experimentation, world-model,
  intelligence, consciousness, emotion, subjective experience, or biological
  claim is supported.
- The complete machine artifact is authoritative for all 24 weights,
  checkpoints, Q2/Q3 metrics, support deltas, and per-run diagnostics.

## Developmental decision gate

Observed result:

- overlap acquisition succeeded for both actions on every seed;
- exact same-visible-state/action consequence variability was not observed;
- the unchanged simple predictor's local final query, especially for
  `MOVE_FORWARD` contact, was not reliably interpretable as the directly
  observed consequence.

Therefore the result does not cleanly satisfy branch A's requirement that
learned predictions be interpretable within support. It supports branch D:

> adequate support + apparently stable consequence at the sampled state + an
> inadequate simple predictor → evaluate whether model representation/capacity
> has earned expansion.

This is a candidate question, not authorization for a neural model. The next
development should first inspect the smallest representation change or
additional local diagnostic that could explain the predictor mismatch. If
future work instead finds variability at other states, branch B remains open.

## Disposition

**CONTINUING.** D-009 supports the narrow descriptive statement that a fixed
sampling scaffold created direct `WAIT` and `MOVE_FORWARD` experience from the
same controller-visible charging observation near nominal thermal `0.59`,
allowing the unchanged action-conditioned learner to update from both actions
within directly visited support. It does not support calling the numerical
outputs counterfactual knowledge. A model-guided D-010 is not preselected;
representation/capacity diagnostics are the current candidate next question.
