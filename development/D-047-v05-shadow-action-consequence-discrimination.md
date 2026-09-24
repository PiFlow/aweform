# D-047 — V0.5 shadow action-consequence discrimination

- **id:** D-047
- **issue:** [#168](https://github.com/PiFlow/aweform/issues/168)
- **lane:** Development / evaluator-only readiness audit
- **date:** 2026-09-25
- **authorized_base_sha:** `a265bf1b2932d9af1dfa9719d53e42dfef688ce3`
- **frozen_executable_protocol_sha:** `41e86c0e514629e3ca67c3efadf5255a1c12244d`
- **final_pr_head_sha:** recorded in the exact-HEAD handoff
- **development_seeds:** D-046's existing `21046..21065`; no new seed
- **disposition:** `CONTINUING`

The compact deterministic artifact is
[`D-047-v05-shadow-action-consequence-discrimination.json`](D-047-v05-shadow-action-consequence-discrimination.json).
It is descriptive Development output, not confirmatory evidence.

## Question and frozen boundary

D-047 asks whether the frozen D-046 action-conditioned predictor preserves the
direction and relative magnitude of real one-step consequence differences
between alternative raw wheel commands from the same organism-visible state.
It does not choose or rank actions and creates no lived organism trajectory.

Following issue #168's `[SOL-AUTHORIZATION-AMENDMENT]`, the committed D-046
artifact—not cross-platform calibration replay—is the canonical learned-state
source. Before evaluation, D-047 verifies its exact `2,927,125`-byte size and
SHA-256
`71741b2a6a1f95e9904bbbedd28575e14d477d4fcb4e1a2cf598badefe5a003d`,
task/schema/executable provenance, ordered seeds, and all 20 per-seed weight
digests. It loads exactly 528 finite full-learner weights per seed and reuses
the unchanged D-046 state transform, action normalization, 66-feature map,
bounds, and prediction arithmetic read-only. It neither reconstructs nor
claims absolute predictions for the unavailable state-only weight vectors;
state-only and zero-change pairwise contrasts are structural zero because both
are action-indifferent at a fixed state.

## Frozen evaluation

The audit uses only D-046 poses `H0..H8`, actions `A0..A8`, and seed-specific
full learners `21046..21065`. Every candidate executes in its own freshly
reset, unchanged D-045 one-step branch. All 9 actions for a seed/pose receive
the identical eight-channel starting observation. Fixed ascending action-ID
orientation produces exactly 1,620 candidate evaluations, 6,480 unordered
pairs, and 51,840 channel-expanded comparisons.

The artifact retains contrast MAE, exact negative/zero/positive sign agreement,
actual and predicted ties, non-tie sign agreement, and support. It reports
each of the eight channels separately and stratifies by seed, action pair,
pose, boundary involvement, and contact-transition involvement. The channel
families remain separate; no scalar competence, desirability, utility, need,
reward, or action ranking is constructed.

## Observed

Pooled non-tie sign agreement for the full learner was approximately 81.44%
for energy; 63.34%, 56.60%, and 60.45% for left, forward, and right beacon;
66.39% for temperature and charging contact, each with only 360 non-tie pairs
and 6,120 actual ties; and 98.65% and 98.61% for left and right wheel delta.
Contrast MAE was approximately 0.0000116 (energy), 4.93e-7 (temperature),
0.0449, 0.0431, and 0.0449 (left, forward, and right beacon), 0.3474
(charging contact), and 0.1291 and 0.1438 (left and right wheel delta).
Boundary-involved and contact-transition-involved strata retained 840 and 660
pairs respectively; exact null/tie support was not smoothed away.

This is channel-specific and mixed rather than a universal success result.
The frozen learner strongly preserves wheel consequence direction and shows
some energy/beacon discrimination, but contact and temperature consequence
support is sparse and exact-tie behavior is weak. The output does not by
itself justify prediction-driven behavior and does not select a successor.

## Causal isolation and preservation

Forward and reverse candidate iteration produced identical per-candidate
outcomes and predictions. Each candidate branch began from the same visible
observation within its seed/pose set; independent branches did not mutate a
source environment. The loaded weights' canonical digests were identical
before and after all queries, and there were zero learner updates. Reward
remained exactly `0.0`, organism-facing `info` remained exactly `{}`, no
formal reserved seed was used, and evaluator metadata never entered model
input.

D-045/D-046 source, artifacts, records, physics, learner arithmetic, and
calibration remain unchanged. D-047 adds no history, recurrence, sensor,
organism-visible state, predictor capacity, retraining, utility, need,
planner, policy, behavioral influence, EXP work, or D-048 work.

## Invalidated provenance preserved

The prior PR result claimed execution from
`5aff6fecf26d76c11f71d6066129e3b188f85135` and artifact SHA-256
`96590d10ccc7c17557e2c957490384b5007e54d2d627fa88c1c0eaa6595cc41f`
(`198,698` bytes). That executable commit is not retrievable from GitHub.
This provenance and artifact are invalidated and are not the official D-047
result.

The earlier candidate executable
`27c52bd388c09efd024dd1ad079e63220cba5118` and artifact
`e115aee3633b203be00308020173563fe414036298ecd972fa47039320cbaa0c`
(`198,698` bytes) were also invalidated when strict mypy found the
NumPy next-observation type defect. Neither invalidated output is interpreted
as the official result.

## Reproducibility and validation

The executable-only freeze was committed as
`41e86c0e514629e3ca67c3efadf5255a1c12244d`, pushed to the existing PR
branch, and verified retrievable from GitHub before execution. It is a direct
child of the authorized base and contains only the runner, focused tests, and
this result-free protocol record; it contains neither the official artifact
nor the D-047 ledger row.

The official artifact was generated from that exact pushed SHA with:

```text
UV_CACHE_DIR=/private/tmp/aweform-d047-uv-cache uv run python -m aweform.d047 --executed-commit-sha 41e86c0e514629e3ca67c3efadf5255a1c12244d
```

A first attempt without the task-local cache setting exited before runner
initialization because the manager home cache was not writable; it produced
no artifact. The successful execution produced an artifact of 198,712 bytes
with SHA-256
`7c3b255b304a64ae8dd35e4a88d447a0f8c9dea43e5a38686afb8e58cd1a4e6e`.
The recorded runtime was Python 3.14.7, NumPy 2.5.2, and
`macOS-26.6.2-arm64-arm-64bit-Mach-O`.

Independent regeneration from the same frozen SHA used:

```text
UV_CACHE_DIR=/private/tmp/aweform-d047-uv-cache MPLCONFIGDIR=/private/tmp/aweform-d047-mpl-cache uv run python -m aweform.d047 --executed-commit-sha 41e86c0e514629e3ca67c3efadf5255a1c12244d --output /private/tmp/d047-regenerated.json
cmp --silent /private/tmp/d047-regenerated.json development/D-047-v05-shadow-action-consequence-discrimination.json
```

The comparison exited 0 and was byte-identical: 198,712 bytes and the same
SHA-256 `7c3b255b304a64ae8dd35e4a88d447a0f8c9dea43e5a38686afb8e58cd1a4e6e`.

Validation outcomes before the result-layer commit:

- `UV_CACHE_DIR=/private/tmp/aweform-d047-uv-cache uv run pytest -q tests/test_d047.py`: 4 passed.
- `UV_CACHE_DIR=/private/tmp/aweform-d047-uv-cache uv run pytest -q`: 1,053 passed, 8 warnings.
- `UV_CACHE_DIR=/private/tmp/aweform-d047-uv-cache uv run ruff check .`: all checks passed.
- `UV_CACHE_DIR=/private/tmp/aweform-d047-uv-cache uv run mypy src --strict`: success, no issues in 77 source files.
- `UV_CACHE_DIR=/private/tmp/aweform-d047-uv-cache uv run python -m compileall -q src tests` and the D-045/D-046/D-047 import check: passed; `IMPORT_OK`.
- `git diff --check`: passed.
- Authorized-base ancestry, exact D-046 artifact/weight identity gates, deterministic branch-order control, and exact-current-HEAD CI are archived in the correction handoff.

No scientific, organism, learner, sensory/plasticity, information, safety,
seed, or protocol boundary changed during this provenance correction. No merge
was performed and D-048 was not started.
