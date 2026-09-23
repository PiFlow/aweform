# D-046 — one-time raw-wheel calibration and fresh V0.5 shadow consequence learning

- **id:** D-046
- **issue:** [#165](https://github.com/PiFlow/aweform/issues/165)
- **lane:** Development / shadow-only prediction-competence probe
- **date:** 2026-09-23
- **authorized_base_sha:** `4b32e49997cba6b223057b7e1946a97ba6fe9235`
- **frozen_executable_protocol_sha:** `19cae43c324cc5e5c06ee717a8091d4d63f20165`
- **final_pr_head_sha:** recorded in the exact-HEAD handoff
- **development_seeds:** `21046..21065`; validated by the existing formal-reservation guard
- **disposition:** `CONTINUING`

The compact deterministic artifact is
[`D-046-v05-calibration-shadow-consequence-learning.json`](D-046-v05-calibration-shadow-consequence-learning.json).
It is descriptive Development output, not confirmatory evidence.

## Question and frozen boundary

D-046 asks whether a fresh, small V0.5 learner can acquire useful
action-conditioned one-step and short-rollout predictions of the eight
organism-visible channels from one externally selected, non-semantic raw-wheel
calibration curriculum, before any prediction is allowed to influence action
selection.

The implementation reuses `D045Env` without source changes. It adds a fresh
zero-initialized `66 × 8` continuous-action predictor: the eight visible
channels and the two normalized desired wheel-command coordinates form ten
scalars, mapped by the generic constant/linear/quadratic feature map to exactly
66 features and 528 learned weights. The post-consequence update is the
authorized multi-output NLMS rule with step size `0.5`. There is no replay,
recurrent state, optimizer state, uncertainty state, learner RNG, reward
signal, semantic action head, planner, need mechanism, or behavioural policy.

The learner sees only the current/next eight visible channels and the
causally executed desired command. External curriculum block identity,
ordering, pose, heading, geometry, contact errors, boundary scale, continuous
wheel truth, seed, lesson phase, and evaluator labels remain outside the
learner. The matched state-only comparator uses the same feature map/update
with both action coordinates forced to zero; the zero-change comparator is
evaluator-only.

## Frozen calibration and evaluation

Each lifetime starts at body/station centre `(0.50, 0.50)`, heading `0`,
`2664.0 J`, `23.0 C`, and an unlatched charger. The one-time curriculum has
16 zero commands, 72 externally seed-shuffled inverse-paired blocks, and 8
final zero commands: 564 causal transitions total, including 540 non-zero
commands. The only seeded operation is the external block-order shuffle.

After calibration, each frozen learner is evaluated read-only on the exact
`9 × 9 = 81` held-out pose/action matrix and the fixed `R0..R3` rollout
sequences at horizons `1, 2, 4, 8`, and final. Full per-seed and pooled
prequential, held-out, contact/Brier, boundary, action, pose, and rollout
metrics are retained in the artifact without a raw transition log.

## Observed

- All 20 lifetimes completed all 564 transitions: pooled support is `11,280`.
  Current-contact support is `3,000` contact-on and `8,280` contact-off
  transitions; contact entry and exit support are `1,280` each; charging was
  positive on `3,000` transitions. All commands stayed inside the D-045
  envelope, reward was exactly `0.0`, and organism-facing `info` was exactly
  `{}`.
- On the pooled 81-probe-per-seed held-out matrix, the full learner has lower
  MAE than the matched state-only comparator for all eight delta targets, with
  the same direction for all `20 × 8 = 160` per-seed target comparisons.
  Against zero-change, full-model MAE is lower for temperature and both wheel
  deltas, but higher for energy, all three beacon deltas, and contact. The
  pooled contact Brier scores are `0.2812` full, `0.6245` state-only, and
  `0.0741` zero-change; contact remains a weak/mixed target under this
  descriptive comparison.
- In frozen rollouts the full model stayed finite and bounded on all `80`
  scored trajectories at every reported horizon. Full-model pooled beacon
  MAE grows from approximately `0.06`–`0.07` at horizon 1 to
  `0.34`–`0.40` at the final horizon. Wheel-delta MAE remains approximately
  `0.07`–`0.18`; contact Brier is `0.0847`, `0.0370`, `0.0193`, `0.0068`,
  and `0.2502` at horizons `1`, `2`, `4`, `8`, and final respectively.

These are descriptive summaries, not a binary success decision or a
confirmatory claim. The result is mixed: action-conditioned learning adds
clear held-out support beyond state-only prediction and improves wheel
consequences, while zero-change remains competitive for several slowly
changing channels and contact, and multi-step beacon error degrades quickly.
This is consistent with local-only competence plus contact-learning and
partial-observability weaknesses; it does not authorize a larger model,
history, recurrence, new sensor, changed learning rate, planner, reward, or
D-047.

## Causal isolation and preservation

For every seed, the learner-attached and no-learner replay trajectories have
identical digests. Predictions are computed for diagnostics only and never
select, rank, gate, veto, modify, or terminate commands. Plasticity is updated
only after the real D-045 consequence and held-out/rollout evaluation leaves
both frozen predictors unchanged. D-045 pose/geometry and telemetry are used
only to instantiate or stratify evaluator probes. No D-027, D-030, or V0.4
learner/controller state is imported, and no new learner RNG exists.

Historical D-001 through D-045 source, records, artifacts, replay meanings,
formal reservations, ADR 0017, reward semantics, and D-045 source semantics
were not changed. D-046 is Development work only; D-047 is not started or
implicitly authorized.

## Surprised by

The fresh quadratic predictor learned useful action-conditioned wheel and
state-only-disambiguating structure without changing the physical trajectory,
but its held-out full model did not beat the deliberately strong zero-change
baseline on beacon, energy, or contact MAE. Contact-event prequential error
improved over zero-change while the pooled held-out contact Brier remained
weaker than zero-change, illustrating why the event and non-event strata are
retained separately rather than collapsed into a success label.

## Reproducibility and validation

The official artifact was generated once from the frozen executable/protocol
SHA above. It is `2,927,125` bytes with SHA-256
`71741b2a6a1f95e9904bbbedd28575e14d477d4fcb4e1a2cf598badefe5a003d`.
Independent regeneration from the same frozen SHA was byte-identical with the
same size and hash.

Focused D-046 tests, the full suite (`1049 passed`), Ruff, strict mypy,
Python 3.14.7 compile/import checks, and `git diff --check` passed. The
implementation/protocol freeze preceded official execution; the later commit
adds only this record, the generated artifact, and the development-index row.
