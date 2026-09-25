# D-048 — V0.5 extended-exposure shadow consequence-learning curve

- **id:** D-048
- **issue:** [#170](https://github.com/PiFlow/aweform/issues/170)
- **lane:** Development / shadow-learning diagnostic
- **authorized_base_sha:** `c401aaa0c6a60bf3cc13840c40951957854ef2ef`
- **frozen_executable_protocol_sha:** `502c006f7406b5676afc49a950794963c4f0c7b0`
- **artifact:** [`D-048-v05-extended-exposure-shadow-learning-curve.json`](D-048-v05-extended-exposure-shadow-learning-curve.json)
- **artifact_sha256:** `899c1443cc5eaa1c1b9772e8ce1dc04c39e190f29b6c6998d52a4333c65cd6e9`
- **artifact_size_bytes:** `3066538`
- **development_seeds:** `21046..21065`; validated by the existing formal-reservation guard
- **disposition:** `CONTINUING`

This is a descriptive Development result, not confirmatory evidence. The
corrected official artifact was generated from the pushed executable freeze
above.

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

## Observed

- All 20 legal development seeds completed one uninterrupted D-048 lifetime:
  eight passes, 564 transitions per pass, and 4,512 transitions per seed.
  Every seed reached exactly `0×`, `1×`, `2×`, `4×`, and `8×`; no termination or
  truncation occurred. Each pass had 64 contact entries, 64 contact exits,
  150 charging-positive transitions, and zero boundary events per seed.
- Every checkpoint retained 1,620 isolated candidate evaluations and 6,480
  unordered action-pair comparisons pooled across seeds, with 51,840
  channel-expanded comparisons. The artifact retains the required pooled
  strata by seed, pose, unordered action pair, boundary involvement, and
  contact-transition involvement.
- The state-only and zero-change action-indifferent contrast comparators retain
  separate aggregates for each visible channel. Their emitted metrics equal
  the corresponding channel-specific zero-prediction calculations and are not
  a channel-mixed aggregate copied across channels.
- Across-seed mean prequential full-learner MAE improved from pass 1 to pass 8
  for every channel: energy `1.024e-5 → 8.937e-6`, temperature
  `4.083e-7 → 3.672e-7`, beacon left `2.987e-3 → 1.924e-3`, beacon forward
  `2.460e-3 → 1.132e-3`, beacon right `2.961e-3 → 1.920e-3`, charging contact
  `0.2782 → 0.2570`, wheel delta left `0.05327 → 0.01433`, and wheel delta
  right `0.05660 → 0.01459`. This is a prequential training diagnostic, not a
  universal competence score.

The held-out full-learner non-tie sign-agreement rates at `1× / 2× / 4× / 8×`
were:

| channel | 1× | 2× | 4× | 8× |
|---|---:|---:|---:|---:|
| energy | 0.8144 | 0.8233 | 0.7904 | 0.7267 |
| temperature | 0.6639 | 0.6667 | 0.6667 | 0.6667 |
| beacon left | 0.6334 | 0.6342 | 0.6359 | 0.6370 |
| beacon forward | 0.5660 | 0.5666 | 0.5671 | 0.5671 |
| beacon right | 0.6045 | 0.6039 | 0.6030 | 0.6033 |
| charging contact | 0.6639 | 0.6639 | 0.6667 | 0.6667 |
| wheel delta left | 0.9865 | 0.9863 | 0.9841 | 0.9808 |
| wheel delta right | 0.9861 | 0.9878 | 0.9799 | 0.9726 |

At `0×`, all predictions are the zero-change comparator. The full learner's
absolute one-step held-out metrics show the same channel separation: by `8×`
wheel-delta MAE was `0.0757` left and `0.0840` right versus zero-change
`0.4975` and `0.5245`; temperature MAE was `7.77e-7` versus zero-change
`1.096e-6`; while energy, all three beacon channels, and charging contact
remained worse than zero-change (`0.6450` contact Brier versus `0.0741`).

## Provisional reading

- Proprioceptive wheel-delta learning continued to improve prequentially, and
  held-out direction discrimination remained very strong, although its
  direction rates declined modestly after the earlier checkpoints.
- Energy showed continued prequential improvement but a mixed held-out curve:
  sign agreement peaked near `2×` and declined by `8×`, while absolute
  one-step calibration remained worse than zero-change.
- Beacon channels improved prequentially but their held-out direction rates
  were approximately flat and their absolute one-step errors remained above
  zero-change. This is mixed local learning with held-out plateau/indeterminate
  generalization, not evidence for a larger learner.
- Temperature improved slightly in prequential and absolute MAE, but its
  held-out non-tie support is sparse and the sign curve is effectively flat.
- Charging contact remained sparse and mixed: prequential error improved only
  slightly, while held-out Brier and absolute error were worse than
  zero-change. Contact-transition support is insufficient for a strong
  capacity conclusion.

These are channel-specific descriptions of this Development execution. There
is no selected best checkpoint, no pass threshold, and no successor decision.
The result does not authorize prediction-driven behaviour, new sensors,
history, recurrence, capacity, utility, need, planning, or EXP work.

## Invalidated provenance

The first official attempt used executable SHA
`bc33a2c0cded36e6c70034e6dfce8f1778949122` and generated a scientifically
equivalent but non-compact 37,216,052-byte artifact with SHA-256
`a36e111b3f331635ecac121367717ce06adb8e0060ab596471fc2b4f300d8807`.
It was invalidated solely because redundant per-seed detailed strata violated
the compact-artifact contract. It was preserved separately and is not pooled
or interpreted. The compact serializer was frozen and pushed as
`274bfb278f3406ac235708faaacb708a9a604cd6`, after which the complete
20-seed protocol was rerun from scratch.

That compact result layer was subsequently invalidated. Executable SHA
`274bfb278f3406ac235708faaacb708a9a604cd6` generated artifact SHA-256
`ae000325425e9afdc2ed6df922c0cc51bf15f193344db5df99f7930e2fb42e9f` with
size `3,072,918` bytes. Independent review found that the action-indifferent
state-only and zero-change contrast comparators used one channel-mixed
aggregate and copied it into every channel entry. The old freeze and artifact
remain preserved in the rejected PR history and are not pooled or interpreted.
The bounded comparator correction was frozen and pushed as
`502c006f7406b5676afc49a950794963c4f0c7b0`, after which all 20 seeds were
rerun from scratch without protocol or scientific tuning.

## Reproducibility and validation

The successful command was:

```text
UV_CACHE_DIR=/private/tmp/aweform-d048-uv-cache MPLCONFIGDIR=/private/tmp/aweform-d048-mpl-cache uv run python -m aweform.d048 --executed-commit-sha 502c006f7406b5676afc49a950794963c4f0c7b0
```

Independent regeneration from the same executable SHA used the same command
with `--output /private/tmp/d048-regenerated.json`; `cmp` was byte-identical
at 3,066,538 bytes and the artifact SHA-256 above. Runtime provenance was
Python `3.14.7`, NumPy `2.5.2`, and
`macOS-26.6.2-arm64-arm-64bit-Mach-O`.

Checkpoint evaluation left the live environment, full learner, and state-only
learner unchanged at every checkpoint. The matched checkpoint-disabled replay
had identical trajectory, full-learner, state-only-learner, and final
environment fingerprints for all 20 seeds. Reward was exactly `0.0`,
organism-facing `info` was exactly `{}`, predictions remained shadow-only,
and no formal reserved seed was used.

Focused D-048 tests: `7 passed`. The full suite passed with `1,060 passed`
and 8 pre-existing Matplotlib warnings. Ruff, strict mypy, compile/import
checks, `git diff --check`, authorized-base ancestry, exact pushed-freeze
retrievability, exact support counts, seed validation, checkpoint read-only
controls, and byte-identical regeneration all passed.
