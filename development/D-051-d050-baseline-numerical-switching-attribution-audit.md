# D-051 — D-050 baseline numerical switching attribution audit

- **id:** D-051
- **status:** v2 protocol executed from frozen executable SHA; prior execution invalidated; cross-platform replay blocker open
- **lane:** Development / evaluator-led Level-1 numerical attribution audit
- **issue:** [#180](https://github.com/PiFlow/aweform/issues/180)
- **authorized_base_sha:** `0a273f6e10c9dff155d4ade15e04684d674b60fd`
- **invalidated_protocol_freeze_sha:** `98b9ca83c86b5b5ab55049cc8ad818801222d1ab`
- **invalidated_artifact_bytes:** `55956563`
- **invalidated_artifact_sha256:** `3abbf9c8c3cbaf495269df2228086a2365cd29228fecd52cb4538feb90f79904`
- **invalidated_executed_commit_sha:** `0a6277a62087141d228d65902c0ef55c6b61040b`
- **clean_executable_sha:** `48a8021a869c42e066a2d2a82fed24c65213a8f3`
- **artifact:** [`D-051-d050-baseline-numerical-switching-attribution-audit.json`](D-051-d050-baseline-numerical-switching-attribution-audit.json)
- **artifact_bytes:** `57203363`
- **artifact_sha256:** `131f2137cc83bd695c3b85bb322dcd6c01617e5aa2a0da70dc40d1b0571bc7f8`
- **disposition:** BLOCKED (correction pass complete except cross-platform replay validation; see *Cross-platform exact-replay blocker*)

## Invalidated prior execution (provenance preserved)

The v1 D-051 execution recorded in the artifact above is **INVALIDATED** by a
protocol defect and is not accepted as D-051 evidence:

- The per-transition counterfactual diagnostic
  `original_threshold_turn_uncertainty_treatment_straight` read the acting
  arm's own effective angular tolerance. On Arm A this compared
  `abs(beta)` against the original `1e-6 rad` rule on both sides of the
  conjunction and could never fire, so Arm A recorded zero counterfactual
  transitions despite `5582` historical and `5869` fresh
  `abs(beta) <= epsilon_float32` transitions in the same artifact. The
  issue-defined counterfactual is arm-independent, so the invalidated
  artifact's Arm-A diagnostic layer is defective and both supports' recorded
  counterfactual counts are meaningless as executed.
- The protocol validation block additionally presented three design
  declarations (Arm-B causal-input compliance, evaluator geometry isolation,
  seedless fresh support) as computed booleans, and the diagnostic-on/off
  instrumentation identity check covered only one case and only Arms A/B.
- GitHub CI on Linux re-deriving the committed D-050 smooth reference failed
  exact behavioral identity (`historical_smooth_behavioral_identity == False`)
  while the macOS generation environment passed. The root cause is diagnosed
  below; it is a property of the historical D-050 artifact, not of the D-051
  correction, and it blocks the required cross-platform replay validation.

No invalidated result is pooled into any corrected interpretation. The matrix,
horizon, arms, tolerances, wheel laws, and summaries are unchanged; the
protocol version is raised to `d051-d050-baseline-numerical-switching-audit-v2`
for the corrected counterfactual and validation restructure only.

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

## Official result (v2 correction rerun)

The v2 official run was generated from the exact corrected
executable/protocol SHA `48a8021a869c42e066a2d2a82fed24c65213a8f3` after
GitHub verification. Independent regeneration from that SHA was
byte-identical with the same `57,203,363` bytes and SHA-256. The committed
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
- With the corrected arm-independent counterfactual, the historical support
  records `3848` Arm-A and `40` Arm-B
  `original_threshold_turn_uncertainty_treatment_straight` transitions, of
  which `3824` fall on the 16 Arm-A censored cases themselves. The v1 zero
  Arm-A counts were the diagnostic defect recorded above.

On the fresh seedless 80-case support:

- Arm A had `60/80` `DOCKED_AND_CHARGING` and `20/80`
  `RETURN_HORIZON_CENSORED`.
- Arm B had `80/80` `DOCKED_AND_CHARGING`.
- Arm C had `80/80` `DOCKED_AND_CHARGING`.
- With the corrected arm-independent counterfactual, the fresh support records
  `5055` Arm-A and `35` Arm-B counterfactual transitions.

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
Arm-A/Arm-C behavioral identity, diagnostic-on/off causal identity across all
three arms over a deterministic three-case subset, fresh-environment arm-order
independence across all six execution-order permutations over the same subset,
legal float32 candidate construction, reward `0.0`, `info == {}`, and Level-1
authority. Design invariants that are not computed by the run (Arm-B
causal-input compliance, evaluator geometry isolation, seedless fresh support)
are recorded in the artifact's `declared_boundaries` block with their
executable test coverage, not as computed booleans. The result-free v2 freeze
passed focused D-051 tests (`13 passed`), strict mypy, Ruff, compile/import
checks, and `git diff --check`.

## Cross-platform exact-replay blocker

**Symptom.** GitHub CI (Ubuntu 24.04, CPython 3.14.7) re-derives the committed
D-050 smooth reference through the unchanged D-050/D-045 code path and fails
`historical_smooth_behavioral_identity == True` while the macOS generation
environment passes. An isolated Linux replay (arm64 Docker, Debian trixie,
same CPython 3.14.7 and numpy 2.5.2 pins) shows `43/96` smooth cases
diverging with zero Arm-A baseline mismatches; the first diverging case is
`direct-r0.15-p022.5-e01`, whose first divergences are single-ULP float64
differences in `contact_pair_error_at_first_contact_m[0]`
(`0.00910133809394045` vs `0.00910133809394044`, `-1.04e-17`) and in
`trace[2].y` (`0x1.1955e1644bc99p-1` vs `0x1.1955e1644bc9ap-1`). The fresh
support is computed anew everywhere and is self-consistent per platform.

**Root cause (empirically isolated).** The divergence is not in D-051's replay
wiring: feeding bit-identical state, bit-identical wheel deltas, and
bit-identical float32 beacon observations into the unchanged D-045 physics on
both platforms produces the one-ULP divergence inside
`integrate_differential_drive` itself. The step-2 headings
`3.3975333431794668` and `3.6288780102417246` are points where Apple's macOS
libm and glibc disagree in the last bit of `cos`/`sin`
(`cos(h)`: `-0x1.ef5267f030906p-1` vs `-0x1.ef5267f030905p-1`; `sin(nh)`:
`-0x1.df77681eff6f4p-2` vs `-0x1.df77681eff6f3p-2`); the difference propagates
through the exact-arc integration into the recorded position. Against a
correctly-rounded reference, macOS `sin`/`cos` deviate in the last bit for
roughly 4–5% of probed arguments, so trajectories that re-derive the recorded
float64 trace bits can only reproduce the artifact exactly on the platform
whose libm generated it.

**Consequence.** The issue-defined exact historical replay contract
(Arm A and Arm C behavioral identity with the committed D-050 artifact on all
96 cases) is a property of the generation platform for the float64 trace
fields. No D-051-only deterministic correction can make it hold across
supported environments: any repair either relaxes exact equality (rounded or
tolerant comparison, discrete-only projection — forbidden without
authorization) or re-anchors the historical numbers by regenerating the
committed D-050 artifact and/or altering D-045/D-050 source (forbidden:
historical immutability). The blocker is therefore reported for an explicit
Flow/ADR decision (e.g. authorizing a regenerated D-050 artifact under a
platform-independent numeric contract, or a separately declared
platform-scoped replay rule). No workaround was applied and no tolerance was
introduced; on the generation platform the exact checks pass and are recorded
as true in the v2 artifact.
