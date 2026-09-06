# D-029 — Action-alternative consequence readiness audit

- **id:** D-029
- **lane:** Development
- **authoritative_base_sha:** `91342dc68144dc2364f90b4c3847d79a4e3e7a8d`
- **base_tree_sha:** `6d91c5ce67b138298b9e416ba557a66f07b37f42`
- **development_seeds:** `18408..18427` inclusive (20 seeds)
- **horizon:** `70,000` real transitions per uninterrupted lifetime
- **status:** protocol frozen; substantive output complete
- **disposition:** `CONTINUING`

The machine-readable substantive artifact is
[`D-029-action-alternative-readiness-audit.json`](D-029-action-alternative-readiness-audit.json).

## Question and frozen scope

D-029 asks whether the unchanged D-027 online predictor, after a long current
V0.4 lifetime, predicts the one-step visible consequences of all four candidate
actions from the same visited current state, including the three actions not
physically executed. It is an evaluator-only readiness audit. It does not use
predictions for action selection, add a value or reward rule, or introduce a
sensor, learner, action, controller state, or physical mechanism.

The unchanged D-026 controller selects the one real action. The unchanged
D-027 learner has exactly `4 × 6 × 7 = 168` zero-initialized weights, learning
rate `0.5`, no extra retained state or RNG, and updates exactly once from the
physically executed action and actual next six-channel observation.

The exact ordered Development seeds are `18408..18427`; the horizon is exactly
`70,000` real transitions. The complete ordered set is passed through
`validate_exp003_development_seeds` and the exact D-029 guard before execution.

## Frozen causal and evaluator order

For each real transition:

1. construct the ordinary typed D-027 six-channel observation;
2. let unchanged D-026 select one real action;
3. query the existing D-027 predictor once read-only for each of `WAIT`,
   `TURN_LEFT`, `TURN_RIGHT`, and `MOVE_FORWARD`;
4. deep-copy the current environment and execute one action in each isolated
   branch, without updating the learner or controller;
5. verify real environment, controller, policy RNG, and learner weights are
   unchanged by the evaluator work;
6. execute the selected action in the real environment;
7. construct the actual next visible observation and perform exactly one
   unchanged D-027 executed-action update;
8. record only evaluator-side aggregate diagnostics.

The selected-action branch must exactly match the real next visible
observation, termination/truncation, and transition telemetry. Reversing the
four branch iteration order must leave branch outcomes and the real lifetime
unchanged.

## Frozen diagnostics

The exact prior-support key is the six ordinary visible Python values derived
from float32 channels plus the candidate action. The registry contains only
prior physically executed state/action pairs from the same lifetime. No
rounding, epsilon, similarity radius, branch row, future row, pose, heading,
seed, mode, or transition index enters the key. Support reports exact counts,
`0`, `>=1`, and `>=2` overlapping categories, and per-action cumulative real
updates without describing that cumulative count as local support.

Each candidate branch records support by executed/unexecuted candidate, action,
`Q1..Q4`, current contact, candidate contact delta `-1/0/+1`, branch
termination/truncation class, and for `MOVE_FORWARD` full-nominal,
boundary-clipped, and nested full-stall labels using the unchanged `0.05`
nominal distance and `1e-12` tolerance.

For all six outputs, the artifact reports online-predictor and zero-change MAE,
ratios, and counts for all candidates, executed/unexecuted candidates, action,
quarter, exact support category, current contact, contact delta, branch
termination class, and MOVE_FORWARD boundary class overall/Q4 where supported.

For each unordered action pair and output, the artifact reports
`predicted_delta(A) - predicted_delta(B)` versus the corresponding branch
contrast: MAE, exact three-way sign agreement, actual-tie count, and non-tie
sign-agreement rate, pooled, per seed, by pair, and Q1/Q4.

## Provenance and interpretation boundary

No raw candidate rows are serialized. The compact artifact retains per-seed and
pooled aggregate metrics, support distributions, pairwise diagnostics,
isolation checks, trajectory/update/weight/RNG digests, and frozen provenance.
The ordinary reference is an unbranched D-027-compatible lifetime with the
same seed, horizon, controller, environment, and learner order. It performs no
D-029 alternative-prediction queries or branch evaluations; the artifact
records zero of each for every reference comparison.

The first complete artifact from executable SHA
`3dbccc5ee42a123d8c2b92f463e5a9fc5955813f` was invalidated before acceptance.
Its SHA-256 was
`da05f15d0ac6f8d1adebbac4f83e6f51773a649c2dd09b6d8d86d8ba4590c205`.
Branch-level policy/environment RNG checks passed, but the compact matched-
reference report omitted the explicit final environment-RNG equality required
by the authorization. No outcome was accepted from that artifact; the learner,
controller, protocol, seeds, horizon, and measured values were not tuned or
changed because of the defect. The corrected executable is rerun from scratch.

The prior accepted compact artifact from clean executable SHA
`f4c90e2cd7cecc64c1843eb5aa1d42499aa80084` is invalidated by correction round
1. Sol found that full-stall rows were counted under the clipped metric and
that the matched reference still performed all alternative prediction
queries. No outcome from that artifact is accepted; only the two defects and
their focused coverage were changed.

The correction-round artifact was generated from clean executable SHA
`91ff47c41a7c596e9956e9c29a418bcaaba37a3e`. Its SHA-256 is
`490d64626b42bf0efe2e03f63a20fa4aa6f424f27acfc0909b5acd6f342d0210` and its
size is 1,471,142 bytes. A full regeneration from the same executable SHA was
byte-for-byte identical.

## Accepted substantive results

The exact ordered seed set produced 20 uninterrupted 70,000-transition
lifetimes: 1,400,000 real transitions and 5,600,000 candidate branch rows.
All four candidate actions were visited on every lifetime. All branch-level
read-only prediction, real environment/controller/RNG isolation, selected
branch consistency, executed-action-only update, and matched-reference checks
were true for all 20 seeds. Each audited lifetime recorded `280,000`
alternative prediction queries and `280,000` isolated branch evaluations; each
ordinary reference recorded zero of both. The matched ordinary D-027-compatible
reference also had exact real visible trajectory, executed pre-update
prediction/update digest, complete 168-weight snapshot, policy-RNG, and
environment-RNG equality over the complete 70,000-transition lifetime.

The exact prior-support registry recorded `0` support for all 5,600,000
candidate rows; no `>=1` or `>=2` cells were visited. This is a direct sparse
support result, not a reason to add a similarity radius. The final cumulative
physically executed update counts by action are retained per seed in the JSON
artifact.

Pooled candidate-row MAE (learned / zero-change comparator) was:

| Output | All candidates | Unexecuted candidates | Unexecuted Q4 |
|---|---:|---:|---:|
| `delta_energy` | `2.064e-6 / 1.514e-5` | `2.740e-6 / 1.370e-5` | `9.443e-7 / 1.362e-5` |
| `delta_beacon_left` | `0.02210 / 0.03135` | `0.02710 / 0.03880` | `0.01157 / 0.01845` |
| `delta_beacon_forward` | `0.01447 / 0.02781` | `0.01709 / 0.03412` | `0.00909 / 0.01748` |
| `delta_beacon_right` | `0.02129 / 0.03118` | `0.02602 / 0.03857` | `0.01150 / 0.01852` |
| `delta_charging_contact` | `0.3351 / 0.3039` | `0.4468 / 0.4052` | `0.03292 / 0.02982` |
| `delta_thermal` | `3.571e-7 / 4.179e-7` | `4.718e-7 / 4.419e-7` | `5.109e-8 / 1.701e-7` |

The boundary branch support was `876,576` full-nominal, `227,118`
boundary-clipped, and `296,306` full-stall `MOVE_FORWARD` rows. The full-stall
category is now recorded separately at both overall and Q4 levels; its
learned/zero-change metrics, like every sparse cell, remain in the artifact.
In full-nominal support, learned energy/beacon MAE was lower while thermal and
charging-contact MAE was higher. These are output/context-specific descriptive
observations, not a scalar competence score.

For the six unordered action pairs, pooled Q4 pairwise non-tie sign-agreement
rates in output order `(energy, beacon L, beacon F, beacon R, contact, thermal)`
were approximately
`(0.984, 0.836, 0.851, 0.836, 0.0088, 0.00077)`. The artifact retains exact
per-pair, per-output, pooled, per-seed, Q1, and Q4 MAE/sign/tie counts. The
stronger energy or beacon directions do not establish a desirable consequence,
utility, or learned action-selection readiness; contact and thermal contrast
direction remained weak in Q4.

These results preserve the D-018 blocker for any future learned-control claim:
exact prior support was entirely sparse, and competence varied by output,
action context, and boundary/contact stratum. D-029 remains Development-lane
descriptive work and does not authorize D-030 or any causal controller use.

D-029 has no binary scientific pass threshold. Weak late-lifetime alternative
prediction, output/context-specific competence, sparse exact support, and null
cells remain valid descriptive results. A positive result could motivate only
D-030 pre-development review; it does not authorize learned control. No claim
about planning, a world model, counterfactual reasoning in general,
intelligence, consciousness, emotion, subjective experience, genuine life,
biological metabolism, or hardware autonomy is made.

Required validation includes focused D-029 tests, deterministic replay and
artifact regeneration from the clean executable SHA, full pytest, Ruff, strict
mypy, compileall, `git diff --check`, and exact-current-HEAD CI.
