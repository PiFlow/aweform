# D-037 — Endogenous prediction-state recruitment-signal audit

- **id:** D-037
- **lane:** Development
- **authorized base:** `3b93a42e03894ffd71744f53462a23cc6ff8d497`
- **development seeds:** `18468..18487` inclusive, reused exactly
- **status:** protocol frozen; official output pending
- **disposition:** `CONTINUING` pending descriptive output

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

- S1: chosen-action predicted `delta_beacon_forward`;
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
categories are committed before official output. The exact clean executable
protocol SHA and artifact SHA-256/size will be recorded after the official run.

Canonical organism behavior is required to remain unchanged. No fresh
Development or EXP seed is permitted, and the D-035A/B/C combined interaction
test described as a Flow contingency is not authorized by this record.

## Official output

Pending execution from the clean protocol SHA. This section will preserve the
observed scalar, held-out, bridge, and onset results and a descriptive
interpretation without converting them into a causal claim.
