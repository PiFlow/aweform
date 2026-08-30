# D-010 — Visited-support consequence-aliasing census

- **id:** D-010
- **date:** 2026-08-30
- **authoritative_base_sha:** `e7e3fc0d5245d08c1c297ce96cb3a6b501d42da4`
- **commit_a_sha:** `ce49f799ec0137f531c9d093a44c9d3abc1ce7c2`
- **executed_commit_sha:** `ce49f799ec0137f531c9d093a44c9d3abc1ce7c2`
- **development_seeds:** `18141, 18142, 18143`
- **horizon:** `1000` transitions per lifetime
- **disposition:** `CONTINUING`

## Scientific question

Across the full visited support of the D-009 overlap sampler, does an exact
organism-visible `(thermal, charging_contact, action)` key ever lead to more
than one exact next-visible `(next_thermal, next_charging_contact)` outcome?

This is an evaluator-side consequence-aliasing census, not a learning
experiment. The D-009 sampler was used because the unresolved prediction
mismatch belongs to the learner trained under that condition. No baseline was
repeated, and no organism capability was added.

## Provenance and invalidated execution

The first Commit-A candidate was `e9f5cbc2b6f5077157bd821bfc90b5453d6bbae6`.
Its 1,000-transition run was invalidated after inspection found a real defect
in the derived per-action summaries: Python `IntEnum` action values compare
equal to `False` and `True`, so `WAIT` and `TURN_LEFT` could be misclassified
as contact groups. The exact-key records were not used as final evidence.

The corrected Commit A is `ce49f799ec0137f531c9d093a44c9d3abc1ce7c2`, with a
regression test for this collision. The accepted substantive execution was
rerun exactly once on the three declared seeds and produced the JSON artifact
at this SHA. No executable or test files changed after that accepted
execution.

## Programmed

- unchanged D-002 thermal ecology and evaluator-side D-003 post-contact setup;
- unchanged D-009 `EARLY`/`LATE` sampling controller;
- fixed development seeds and 1,000-transition horizon;
- no forced actions, model-guided control, sensors, history, recurrent state,
  capacity increase, reward, or new organism capability.

The run used only the D-009 overlap-sampler condition. Each lifetime started
in `EARLY`; the phase toggled only when the natural D-009 return completed at
charging contact. All three lifetimes completed 13 shuttle cycles, with 7
`EARLY` and 6 `LATE` cycles, and truncated at the horizon without energy or
thermal failure.

## Learned

The unchanged D-008 24-scalar normalized-LMS action-conditioned consequence
predictor ran shadow-only. It received the same organism-visible current and
next thermal/contact observations and own action as D-009. Its prediction had
zero influence on action choice, environment execution, or the census.

Reward remained exactly `0.0` and Gymnasium `info` remained exactly `{}` on
every transition.

## Evaluator-only census

For every physically executed transition, the evaluator formed an exact key
from the Python `float` derived from the organism-visible `np.float32`
thermal channel, the exact boolean charging-contact channel, and the executed
`Action`. No rounding, binning, epsilon matching, nominal decimal substitution,
or seed/heading field was used in the key.

Each key record in the machine-readable artifact preserves its exact current
thermal, contact, action, sample count, repeated flag, aliasing-tested flag,
every exact next-visible outcome and count, distinct next-thermal count,
distinct next-contact count, and aliased flag. A key is repeated only at two or
more samples. A singleton is marked untested for aliasing; it is never called
stable. The pooled census intentionally omits seed identity from its key.

**Source:** complete exact-key records and summaries in
[`D-010-visited-support-consequence-aliasing.json`](D-010-visited-support-consequence-aliasing.json).

## Results

### Overall census

| Scope | Transitions | Unique keys | Repeated keys | Singleton keys | Transitions in repeated keys | Fraction | Aliased keys |
|---|---:|---:|---:|---:|---:|---:|---:|
| 18141 | 1000 | 86 | 80 | 6 | 994 | 0.994 | 2 |
| 18142 | 1000 | 84 | 78 | 6 | 994 | 0.994 | 2 |
| 18143 | 1000 | 86 | 80 | 6 | 994 | 0.994 | 2 |
| pooled | 3000 | 86 | 86 | 0 | 3000 | 1.000 | 4 |

### Per-action census

| Scope | Action | Transitions | Unique keys | Repeated keys | Aliased keys |
|---|---|---:|---:|---:|---:|
| 18141 | `WAIT` | 884 | 75 | 69 | 0 |
| 18141 | `TURN_LEFT` | 52 | 4 | 4 | 0 |
| 18141 | `TURN_RIGHT` | 0 | 0 | 0 | 0 |
| 18141 | `MOVE_FORWARD` | 64 | 7 | 7 | 2 |
| 18142 | `WAIT` | 896 | 74 | 68 | 0 |
| 18142 | `TURN_LEFT` | 52 | 4 | 4 | 0 |
| 18142 | `TURN_RIGHT` | 0 | 0 | 0 | 0 |
| 18142 | `MOVE_FORWARD` | 52 | 6 | 6 | 2 |
| 18143 | `WAIT` | 884 | 75 | 69 | 0 |
| 18143 | `TURN_LEFT` | 52 | 4 | 4 | 0 |
| 18143 | `TURN_RIGHT` | 0 | 0 | 0 | 0 |
| 18143 | `MOVE_FORWARD` | 64 | 7 | 7 | 2 |
| pooled | `WAIT` | 2664 | 75 | 75 | 0 |
| pooled | `TURN_LEFT` | 156 | 4 | 4 | 0 |
| pooled | `TURN_RIGHT` | 0 | 0 | 0 | 0 |
| pooled | `MOVE_FORWARD` | 180 | 7 | 7 | 4 |

### Charging-contact context

The pooled off-contact support had 1,463 transitions, 39 unique/repeated
keys, and 0 aliased keys. The pooled charging-contact support had 1,537
transitions, 47 unique/repeated keys, and 4 aliased keys. Per-seed charging
contact transitions were 508, 521, and 508 for seeds 18141, 18142, and 18143;
each had 2 aliased charging-contact keys. Per-seed off-contact transitions
were 492, 479, and 492; none were aliased.

### MOVE_FORWARD/contact=True repeat coverage

| Scope | Transitions | Unique keys | Repeated keys | Aliased keys |
|---|---:|---:|---:|---:|
| 18141 | 51 | 6 | 6 | 2 |
| 18142 | 39 | 5 | 5 | 2 |
| 18143 | 51 | 6 | 6 | 2 |
| pooled | 141 | 6 | 6 | 4 |

Thus the relevant `MOVE_FORWARD`/charging-contact support was not singleton-
dominated: every such key in every scope was repeated, and every transition
in that pooled context belonged to a repeated key.

### Aliased exact keys

All aliased keys were `MOVE_FORWARD` with `charging_contact=True`; no `WAIT`,
`TURN_LEFT`, off-contact, or exact `0.5899999737739563` charging key was
aliased.

The pooled aliased keys were:

| Current thermal | Samples | Exact next-visible outcomes (count) |
|---:|---:|---|
| `0.6000000238418579` | 21 | `(0.5899999737739563, False)` × 1; `(0.6100000143051147, True)` × 20 |
| `0.6100000143051147` | 39 | `(0.6000000238418579, False)` × 8; `(0.6200000047683716, True)` × 31 |
| `0.6200000047683716` | 30 | `(0.6100000143051147, False)` × 12; `(0.6299999952316284, True)` × 18 |
| `0.6299999952316284` | 18 | `(0.6200000047683716, False)` × 6; `(0.6399999856948853, True)` × 12 |

Per-seed aliasing was already present without pooling: seed 18141 and 18143
had exact current thermal keys `0.6100000143051147` and
`0.6200000047683716`; seed 18142 had `0.6000000238418579` and
`0.6100000143051147`. Pooling additionally combined the repeated exact keys
across lifetimes, as specified.

## Interpretation

**Direct observation, source:** repeated exact visible state/action keys
produced multiple exact next-visible outcomes. This directly demonstrates
consequence aliasing within the visited D-009 support, especially for
`MOVE_FORWARD` from charging contact. The result is consistent with broader
observation aliasing/partial observability, but this census does not identify
which hidden simulator variable causes it.

**Inference:** D-009's stable exact `0.5899999737739563` charging observation
does not generalize to the other visited charging temperatures. The D-008
`MOVE_FORWARD` contact-prediction mismatch therefore has a directly observed
aliasing explanation available within the model's training support; increasing
predictor capacity is not the justified next step for this question.

This supports the aliasing branch of the decision gate. The next developmental
question should concern the smallest closure-valid retained history/internal
state that can disambiguate these consequences. Model-guided control remains
not authorized.

## surprised_by

The D-009 exact target near nominal thermal `0.59` was stable for both sampled
actions, but the full visited support contained repeated aliasing immediately
above it. The aliasing was not a rare singleton artifact: all pooled
`MOVE_FORWARD/contact=True` keys were repeated, and four exact keys had two
distinct next-visible outcomes.

## limitations

- This is descriptive D-lane evidence, not confirmatory evidence.
- It covers only three legal development seeds, one horizon, and the support
  visited by the D-009 sampler.
- A non-aliased singleton would be untested, not stable; the per-seed census
  contains six singleton keys, all in charging-contact support.
- The deterministic result demonstrates observed consequence variability under
  identical visible key/action, but does not establish stochasticity or the
  hidden cause of the variability.
- `TURN_RIGHT` was not visited, so no conclusion is available for it.
- No claim about consciousness, emotion, subjective experience, biological
  metabolism, genuine life, intelligence, or a general world model is made.

## Tests and disposition

Focused synthetic tests cover identical repeated consequences, two-consequence
aliasing, action separation, exact float32 separation, singleton handling,
cross-lifetime pooling, D-009 sampler use, D-008 shadow-only isolation,
reward/info preservation, and seed boundaries. The corrected Commit A passed
the full repository validation before execution: `578 passed`, ruff clean,
strict mypy clean, and `git diff --check` clean.

The diagnostic is `CONTINUING`. The evidence supports investigating minimal
closure-valid retained state/history, not adding predictor capacity and not
introducing model-guided control.
