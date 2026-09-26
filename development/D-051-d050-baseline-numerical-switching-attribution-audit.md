# D-051 — D-050 baseline numerical switching attribution audit

- **id:** D-051
- **status:** completed from frozen executable SHA
- **lane:** Development / evaluator-led Level-1 numerical attribution audit
- **issue:** [#180](https://github.com/PiFlow/aweform/issues/180)
- **authorized_base_sha:** `0a273f6e10c9dff155d4ade15e04684d674b60fd`
- **clean_executable_sha:** `98b9ca83c86b5b5ab55049cc8ad818801222d1ab`
- **artifact:** [`D-051-d050-baseline-numerical-switching-attribution-audit.json`](D-051-d050-baseline-numerical-switching-attribution-audit.json)
- **artifact_bytes:** `55956563`
- **artifact_sha256:** `3abbf9c8c3cbaf495269df2228086a2365cd29228fecd52cb4538feb90f79904`
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

## Official result

The official run was generated from the exact clean executable/protocol SHA
above after GitHub verification. Independent regeneration from that SHA was
byte-identical with the same `55,956,563` bytes and SHA-256. The committed
D-050 reference artifact used for replay identity was SHA-256
`28e352ad57096c5c85de8beae546b48e6041b6b0ad8bed712bcf185efb024fa5`, with
reference executable SHA `ab66eadc21c1542f508a7c078e7ebc4229b92962`.

On the historical D-050 support:

- Arm A reproduced the committed D-050 baseline exactly: `80/96`
  `DOCKED_AND_CHARGING` and `16/96` `RETURN_HORIZON_CENSORED`.
- Arm C reproduced the committed D-050 smooth reference exactly: `96/96`
  `DOCKED_AND_CHARGING`.
- Arm B had `96/96` `DOCKED_AND_CHARGING`.
- Every one of the 16 Arm-A censored cases started at radius `0.30 m`, ran
  the full 256-transition horizon, ended approximately `0.00940268 m` from
  station centre, and showed either `239` or `240` nominal-bearing sign
  alternations with longest consecutive TURN runs of `241` or `237`.
- Across those 16 Arm-A censored traces, the evaluator true bearing was inside
  the local float32 uncertainty envelope on all `4096/4096` diagnostic
  transitions. The maximum local envelope was approximately
  `3.64179e-6 rad`; the maximum nominal-minus-true bearing error was
  approximately `1.07260e-6 rad`.

On the fresh seedless 80-case support:

- Arm A had `60/80` `DOCKED_AND_CHARGING` and `20/80`
  `RETURN_HORIZON_CENSORED`.
- Arm B had `80/80` `DOCKED_AND_CHARGING`.
- Arm C had `80/80` `DOCKED_AND_CHARGING`.

These are descriptive support-specific outcomes, not a scalar controller
score or a universal winner. The fresh result is held separate from the
historical replay and was not used to change the frozen protocol.

## Attribution and limits

**Measured:** The historical censoring is a sign-alternating TURN regime with
negligible final radial progress under the unchanged D-049 baseline. The
predeclared observation-only uncertainty treatment changes the tested
outcomes on both the historical and fresh supports. The raw artifact retains
per-transition nominal, true, float32-envelope, and ideal-float64 values.

**Inference:** The results support the hypothesis that near-threshold
reconstruction/switching uncertainty materially contributes to the 16 D-050
censored cases on the tested support. They do not establish that float32
quantization is the sole causal defect: the float64 ideal-beacon diagnostic
tracks the true near-zero bearing region and the original fixed `1e-6 rad`
controller rule still encounters that switching geometry evaluator-side.

**Boundary:** Arm B remains a diagnostic comparator and is not promoted. D-051
does not rewrite D-050, select a canonical homing law, add a sensor, alter the
eight-channel boundary, add energy-trigger logic, or authorize D-052.

## Validation

The artifact validation is true for exact support cardinalities, historical
Arm-A/Arm-C behavioral identity, diagnostic-on/off causal identity, legal
float32 candidate construction, evaluator causal isolation, reward `0.0`,
`info == {}`, and Level-1 authority. The result-free freeze passed focused
D-051 tests (`6 passed`), the repository-wide suite (`1096 passed, 8
warnings`), strict mypy, Ruff, compile/import checks, and `git diff --check`.
