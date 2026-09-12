# D-037 — Endogenous prediction-state recruitment-signal audit

- **id:** D-037
- **lane:** Development
- **authorized base:** `3b93a42e03894ffd71744f53462a23cc6ff8d497`
- **development seeds:** `18468..18487` inclusive, reused exactly
- **earlier invalidated protocol SHA:** `b0d8d1ef315f66503742d2ac2ceb0ab47effc52f`
- **earlier invalidated artifact SHA-256:** `cc3cad6739c9242176ced06bed63601a7396bd3c568222993ab95f8e1579bf49`
- **earlier invalidated artifact size:** `587491` bytes
- **earlier invalidated-output reason:** required pooled scalar correlations and numeric per-fold target class counts were not serialized; no signal definition or outcome was changed
- **prior invalidated protocol SHA:** `51c5f5867d4bd7aac2fac3544b4c62c73a21dd4c`
- **prior invalidated artifact SHA-256:** `7247c012487673a0125723313863df91829d62abe0abc335096222b7e391019c`
- **prior invalidated artifact size:** `597339` bytes
- **prior invalidated-output reason:** S1 indexed the historical/greedy action rather than the exact learned Arm-B action selected for execution
- **corrected protocol freeze SHA:** `0013596bf404f85c3e8acb7b565953977890ae7b`
- **artifact:** `D-037-endogenous-prediction-state-recruitment-signal-audit.json`
- **artifact SHA-256:** `db7da49b59b920235159c6ab35f71e78224412affd2f0d03aba4a5fa276f1e6b`
- **artifact size:** `597425` bytes
- **status:** official output complete
- **disposition:** `CONTINUING`

## Question and boundary

D-037 asks whether quantities already available at the current pre-action
decision from the unchanged D-027/D-030 predictor localize unproductive
false-contact SEEK regimes or D-034 recruitment states better than the current
six-channel observation. It is evaluator/shadow-only. It adds no organism
memory, detector, meta-controller, action, sensor, learner mechanism, reward,
planning, physics, D-035A/B/C treatment, or EXP work.

## Frozen executable protocol

The accepted D-031R1 Arm-A `LEARNED_WITH_DETRAP` and Arm-B
`LEARNED_NO_DETRAP` replays are run through the existing D-033 instrumentation
and must match the accepted identity fields, including final weights and RNG
digests. Only Arm-B eligible decisions are retained. Eligibility is evaluated
before the scored action executes and is exactly `mode_before == SEEK` plus
current visible `charging_contact == false`; `mode_after`, post-action contact,
and all transition outcomes are ignored.

At each eligible decision, the existing predictor's read-only predictions for
the canonical D-030/D-031R1 steering set `(TURN_LEFT, TURN_RIGHT,
MOVE_FORWARD)` and the existing pre-action 168-weight state are captured by
evaluator instrumentation. The six visible channels are the S0 baseline.
The scalar family is exactly:

- S1: the predicted `delta_beacon_forward` for the exact final learned Arm-B
  `capture.proposed_action` selected immediately before execution; the capture
  path asserts this equals the real executed trace action for every eligible
  decision;
- S2: maximum predicted `delta_beacon_forward`;
- S3: largest minus second-largest predicted `delta_beacon_forward`;
- S4: population standard deviation of the three predicted forward deltas;
- S5: Frobenius norm of the centered 3-by-6 predicted consequence matrix;
- S6: Frobenius norm of the 3-by-6-by-7 candidate-action weight tensor.

S4 is `sqrt(mean((x - mean(x))^2))`. S5 is
`sqrt(sum((P[a,c] - mean_a(P[a,c]))^2))`. S6 is `sqrt(sum(w^2))` over the
three candidate-action heads, all six outputs, and seven predictor features.
No learned embedding or tuned weighting is used. These quantities are
computed post-hoc from captured pre-action state and read-only predictions;
none reaches the organism.

For horizons exactly `64`, `256`, and `1024`, the target is the unchanged
continuation's final visible `beacon_forward` minus the current pre-action
visible `beacon_forward`; reacquisition is any false-to-true charging-contact
transition in that window. Termination, truncation, and lifetime-boundary
windows remain explicit nulls and are excluded only from affected metrics.
Scalar signals receive per-seed distributions, pooled summaries, and Pearson
correlations with available progress targets. A secondary ridge comparison
uses intercept plus S0 versus intercept plus S0 and S1..S6, fixed alpha `0.01`
from the predeclared grid `[1e-6, 1e-4, 1e-2, 1.0]`, with strict
leave-one-seed-out evaluation and identical held-out support. Binary metrics
remain null when training or held-out support lacks both classes.

The D-034 bridge queries `ALT_4`, `ALT_8`, `ALT_16`, and
`NO_FORWARD_PROGRESS_4`, `_8`, `_16` after ordinary-support analysis. Each
available anchor is paired within seed to the nearest eligible ordinary
non-anchor state using squared distance on current S0 only, with smallest trace
index as tie-break. Anchor labels, ON/OFF outcomes, targets, hidden geometry,
and future quantities are not matching features. The bridge is descriptive.

The oscillation onset is the first contiguous ordinary Arm-B run whose
decisions are all eligible false-contact SEEK decisions and whose actions
strictly alternate left/right, with minimum length `16`; onset is the first
action of that run. Fixed 16-decision windows are measured before, at, and
after onset. A same-seed ordinary non-onset control is matched on current S0
only. The evaluator-only onset label is never a signal or organism state.

No arbitrary significance threshold or bootstrap is introduced. All seeds,
nulls, and unavailable anchors are retained. Interpretation categories are:
useful endogenous signal; current observation already explains it; weak or
unstable endogenous signal; no supported endogenous signal; and target
unsupported. A result cannot authorize causal recruitment or organism memory.

## Provenance gate

The complete executable protocol, capture support, focused tests, artifact
writer, matching rules, onset definition, null policy, and interpretation
categories were committed before official output. The exact clean executable
protocol SHA and corrected artifact SHA-256/size are recorded above.

The first official output was invalidated before corrected rerun because the
artifact omitted pooled scalar correlations and numeric per-fold target class
counts required by this record. Its protocol SHA, artifact hash, size, and
reason remain preserved above. The next official output was also invalidated:
its protocol SHA, artifact hash, size, and reason remain preserved above because
S1 used the historical/greedy action instead of `capture.proposed_action`. The
current corrected protocol changes only that S1 indexing and its focused
regression guard/tests; all other frozen choices remain unchanged.

Canonical organism behavior is required to remain unchanged. No fresh
Development or EXP seed is permitted, and the D-035A/B/C combined interaction
test described as a Flow contingency is not authorized by this record.

## Official output

All 40 accepted Arm-A/Arm-B replay identity gates passed, including complete
final learner weights, trajectory/update digests, and RNG digests. The
unchanged Arm-B trace supplied `665908` eligible false-contact SEEK decisions,
and the S1 regression guard passed for every captured eligible decision: each
`capture.proposed_action` matched the real executed Arm-B trace action. No fresh
Development or EXP seeds were used. The corrected artifact was regenerated
byte-identically.

The reacquisition target was all-negative at every horizon: pooled support was
`664648`, `660808`, and `645448` at horizons `64`, `256`, and `1024`, with zero
positive labels. Binary metrics are therefore explicitly untestable/null.
Pooled scalar Pearson correlations with continuous future progress were small
and inconsistent in sign: for S1 through S6 respectively they were
`0.018254, 0.018254, -0.005808, -0.011279, -0.026035, -0.003557` at horizon
`64`, `0.019548, 0.019548, -0.004661, -0.009609, -0.026816, -0.002807` at
`256`, and `0.021560, 0.021560, -0.002758, -0.007558, -0.027344, -0.001433`
at `1024`.

The strict leave-one-seed-out S0 baseline versus S0+S1..S6 comparison was:

| horizon | S0 MAE / correlation | S0+S1..S6 MAE / correlation | mean augmented-minus-baseline MAE |
|---:|---:|---:|---:|
| 64 | `0.0006975 / 0.0645` | `0.0018562 / 0.1116` | `+0.0011587` |
| 256 | `0.0007009 / 0.0654` | `0.0018631 / 0.1137` | `+0.0011622` |
| 1024 | `0.0007216 / 0.0661` | `0.0018621 / 0.1121` | `+0.0011405` |

The augmented model's higher correlation did not translate into lower error:
the augmented MAE was worse on 18/20 held-out seeds at horizon 64, 18/20 at
256, and 18/20 at 1024. This is not a stable improvement over S0.

The D-034 bridge had `112/120` available anchors and `112/112` matched ordinary
controls. Anchor-minus-control signal signs were mixed: S1 `52/112` positive,
S2 `48/112`, S3 `46/112`, S4 `44/112`, S5 `61/112`, and S6 `61/112`, with no
systematic separation rule asserted. The oscillation-onset diagnostic found
`17/20` onset states and `17/17` matched controls. The fixed before window was
available for `9/17` due to trace-boundary nulls; at/after windows were
available for `17/17`. Onset contrasts were not coherent across the scalar
family.

Descriptive interpretation: **current observation already explains it / no
supported stable endogenous signal** on this Development support. Predictor
state quantities show small associations and a correlation-only gain in the
secondary fit, but no stable same-support error improvement or coherent bridge
and onset separation. The reacquisition target is **unsupported/untestable**.
This result is not causal evidence and does not authorize organism memory,
recruitment, D-038, or any combined D-035A/B/C treatment.
