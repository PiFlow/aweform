# D-048 — V0.5 extended-exposure shadow consequence-learning curve

- **id:** D-048
- **issue:** [#170](https://github.com/PiFlow/aweform/issues/170)
- **lane:** Development / shadow-learning diagnostic
- **authorized_base_sha:** `c401aaa0c6a60bf3cc13840c40951957854ef2ef`
- **development_seeds:** `21046..21065`; validated by the existing formal-reservation guard
- **disposition:** `CONTINUING`

The result artifact and completed observations are added only after the
official run from the pushed executable freeze. This initial protocol record
intentionally contains no result, interpretation, artifact hash, or ledger row.

## Question and frozen boundary

D-048 asks whether the unchanged D-046 shadow consequence learner continues
improving, plateaus, deteriorates, or remains indeterminate when the exact
seed-specific 564-transition curriculum is repeated for eight consecutive
passes in one continuous D-045 lifetime.

Each seed starts a fresh D-045 environment, a fresh zero-initialized full
D-046 learner, and a fresh zero-initialized matched state-only learner. The
environment and both learners continue across all passes without reset. The
planned exposure is `8 × 564 = 4,512` transitions per completed seed.

Read-only snapshots are evaluated at exactly `0×`, `1×`, `2×`, `4×`, and `8×`
exposure using the unchanged D-046/D-047 held-out `H0..H8 × A0..A8` matrix.
Each candidate is an isolated D-045 branch. Evaluation does not update the
live learners or environment and all predictions remain shadow-only.

The artifact retains channel-specific D-047 action-pair discrimination,
D-046-style absolute one-step metrics, per-pass prequential diagnostics, and
compact weight digest/norm/change diagnostics. No scalar competence score,
best checkpoint, universal threshold, or successor choice is defined.

## Protocol controls

- The exact D-046 curriculum builder and seed-specific block order are reused;
  curriculum metadata is evaluator-side and never a learner input.
- The exact eight D-045 visible channels, 66-feature quadratic map, 528
  weights, NLMS step `0.5`, update timing, raw-wheel action envelope, reward
  `0.0`, and organism-facing `info == {}` remain unchanged.
- Held-out outcomes never enter later training. Checkpoint evaluation records
  live environment and learner identity before/after evaluation.
- A matched run with checkpoint evaluation disabled compares trajectory,
  full-learner, state-only-learner, and final environment fingerprints.
- Genuine D-045 termination/truncation is preserved; no reset, battery repair,
  skipped transition, or altered physics is used to reach a checkpoint.
- No D-045, D-046, or D-047 source, artifact, record, seed reservation,
  observation/action boundary, learner capability, or successor task is
  changed.

## Reproducibility and result-layer plan

The executable/protocol freeze consists of `src/aweform/d048.py`,
`tests/test_d048.py`, and this result-free record. It must be committed and
pushed before the official artifact is generated. The official artifact must
record the exact pushed executable SHA and be regenerated independently from
that SHA byte-identically. The completed record and one `development/INDEX.md`
row are result-layer changes after execution.
