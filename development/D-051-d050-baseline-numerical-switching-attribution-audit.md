# D-051 — D-050 baseline numerical switching attribution audit

- **id:** D-051
- **status:** correction rerun pending frozen executable SHA
- **lane:** Development / evaluator-led Level-1 numerical attribution audit
- **issue:** [#180](https://github.com/PiFlow/aweform/issues/180)
- **authorized_base_sha:** `0a273f6e10c9dff155d4ade15e04684d674b60fd`
- **invalidated_clean_executable_sha:** `98b9ca83c86b5b5ab55049cc8ad818801222d1ab`
- **invalidated_artifact_bytes:** `55956563`
- **invalidated_artifact_sha256:** `3abbf9c8c3cbaf495269df2228086a2365cd29228fecd52cb4538feb90f79904`
- **correction_protocol_version:** `d051-d050-baseline-numerical-switching-attribution-audit-v2`
- **disposition:** CONTINUING

## Question and boundary

D-051 audits whether the 16 D-050 stop-turn-straight horizon-censored cases
are attributable to float32 beacon reconstruction and angular switching
uncertainty. It is a descriptive Development audit, not controller selection,
an EXP execution, or authorization for the return-energy trigger or D-052.

D-045, D-049, D-050, their artifacts and semantics, the exact eight-channel
organism boundary, reward `0.0`, and organism-facing `info == {}` remain
unchanged. Evaluator pose, heading, station geometry, true bearing, ideal
beacon values, and all attribution metrics remain causally isolated.

## Frozen arms

- **Arm A — `ORIGINAL_BASELINE`:** direct delegation to the unchanged
  `aweform.d049.D049Controller`.
- **Arm B — `FLOAT32_UNCERTAINTY_TREATMENT`:** the unchanged D-049 inverse,
  centre rule, terminal rule, wheel law, and causal observations, with only the
  angular switching tolerance replaced by the maximum wrapped bearing
  deviation over the Cartesian product of each legal previous/current/next
  float32 L/F/R value. The effective tolerance is
  `max(1e-6 rad, epsilon_float32)`. There is no multiplier, sweep, fitted
  parameter, success-based tuning, evaluator geometry, or new observation.
- **Arm C — `D050_SMOOTH_REFERENCE`:** direct delegation to the unchanged
  `aweform.d050.D050SmoothController`.

The Arm-B envelope is computed with actual float32 `nextafter` values, legal
signal clipping `0 < value <= 1`, at most 27 tuples, wrapped angular
differences, and a diagnostic fallback to the original tolerance when no valid
candidate reconstruction exists. The separate counterfactual diagnostic
applies the issue-defined original-turn versus uncertainty-straight comparison
independently of the active arm, outside the existing centre tolerance.

## Frozen support and diagnostics

The runner replays the committed D-050 96-case matrix at horizon 256 and
checks exact behavioral identity of Arms A and C against the committed
D-050 artifact. It then runs exactly 80 fresh seedless cases at horizon 256:

- radii: `0.010`, `0.025`, `0.080`, `0.300` m;
- position bearings: `13`, `79`, `151`, `233`, `317` degrees;
- source-relative initial bearing errors: `+0.17`, `-0.53`, `+1.07`,
  `pi - 0.41` rad.

Raw Arm-A and Arm-B transition diagnostics separate nominal float32 inverse
values, evaluator true body-relative station values, the local float32
uncertainty envelope, and the evaluator-only float64 ideal-beacon inverse.
They retain mode, requested and actual wheel deltas, body pose/heading,
radial progress, contact, battery, bearing-sign alternation, and the declared
summary quantities. Arm C retains the unchanged compact D-050 behavioral
trace as the descriptive reference.

## Validation and execution discipline

The corrected result-free implementation includes the issue-defined
counterfactual regression; focused ULP/candidate tests; direct delegation
tests; exact historical replay checks with first-field mismatch reporting;
diagnostic-on/off identity checks across all arms on one historical and one
fresh case; and fresh-environment branch/order checks across those same cases
and all three arms. Replay equality remains exact; no tolerance is introduced.

The clean executable/protocol SHA must be pushed and verified before rerunning
either frozen support. No results may be used to alter the matrix, horizon,
controller laws, uncertainty rule, summaries, or interpretation. The
regenerated artifact and completed record are added only after execution from
the verified corrected freeze, and independent regeneration from that exact
SHA must be byte-identical. D-045/D-049/D-050 historical source, artifacts,
and records remain untouched.

## Invalidated prior execution and defect provenance

The first D-051 result is invalidated in full and must not be pooled or cited
as accepted output:

- **executable SHA:** `98b9ca83c86b5b5ab55049cc8ad818801222d1ab`
- **artifact:** `D-051-d050-baseline-numerical-switching-attribution-audit.json`
- **artifact bytes:** `55,956,563`
- **artifact SHA-256:**
  `3abbf9c8c3cbaf495269df2228086a2365cd29228fecd52cb4538feb90f79904`
- **defect:** the diagnostic
  `original_threshold_turn_uncertainty_treatment_straight` used active Arm-A
  tolerance, so its count was zero rather than applying
  `max(D049 tolerance, epsilon_float32)` independently of active arm. CI also
  exposed a Linux exact Arm-C replay failure; first-field mismatch reporting
  is being added for diagnosis without relaxing equality.

The complete former artifact remains in Git history. The corrected run must
use a new clean executable SHA and regenerate both supports from scratch.
