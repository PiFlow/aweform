# D-051 — D-050 baseline numerical switching attribution audit

- **id:** D-051
- **status:** result-free protocol freeze; official execution pending
- **lane:** Development / evaluator-led Level-1 numerical attribution audit
- **issue:** [#180](https://github.com/PiFlow/aweform/issues/180)
- **authorized_base_sha:** `0a273f6e10c9dff155d4ade15e04684d674b60fd`
- **clean_executable_sha:** to be recorded after the result-free freeze commit
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
candidate reconstruction exists.

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

The result-free implementation includes focused ULP/candidate tests, direct
delegation tests, boundary tests, exact historical A/C replay checks,
diagnostic-on/off causal identity, deterministic execution, and byte-stable
artifact generation. The official result must be generated only from the
clean pushed executable/protocol SHA recorded above, after that SHA is
verified retrievable from GitHub. Results must not change the matrix, horizon,
controller laws, uncertainty rule, summaries, or interpretation.

After official execution, only the deterministic artifact, this completed
record, and one D-051 row in `development/INDEX.md` may be added in the result
layer. Independent regeneration from the exact executable SHA must be
byte-identical. Negative and censored outcomes remain part of the raw record;
no scalar winner is selected and Arm B is not promoted by D-051.

## Result layer

To be completed only after the frozen official run. This section will record
the verified executable SHA, artifact size and SHA-256, regeneration result,
descriptive support-separated summaries, and the earliest observed causal
loss-of-progress or numerical-switching attribution without changing the
frozen protocol.
