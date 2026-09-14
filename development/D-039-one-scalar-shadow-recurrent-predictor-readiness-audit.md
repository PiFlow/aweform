# D-039 — One-scalar shadow recurrent predictor readiness audit

- **id:** D-039
- **issue:** [#135](https://github.com/PiFlow/aweform/issues/135)
- **lane:** Development
- **authorized_base_sha:** `2736bf2982812a52a7123b19a114dec07f80a70f`
- **development_seeds:** `18468..18487` inclusive, reused exactly
- **lifetime horizon:** `70,000` real transitions per uninterrupted Arm-B lifetime
- **status:** protocol frozen; official output below
- **disposition:** `CONTINUING`

The machine-readable result is
[`D-039-one-scalar-shadow-recurrent-predictor-readiness-audit.json`](D-039-one-scalar-shadow-recurrent-predictor-readiness-audit.json).

## Question and boundary

D-039 asks whether exactly one shadow-only recurrent scalar, learned from
ordinary experienced `delta_beacon_forward` prediction error, adds temporal
predictive information beyond the unchanged current observation and D-027
predictor, and descriptively localizes D-034 recruitment-relevant or D-037
oscillatory states. It is a readiness audit only.

The causal path is the accepted D-031R1 `LEARNED_NO_DETRAP` Arm-B lifetime.
The scalar cannot reach action selection, controller mode, scaffold
delegation, explorer state, D-027 weights/update, environment, RNG, reward, or
organism-facing `info`. The four actions, six visible channels, D-027 168
weights and update rule, D-024/D-020 physics, reward `0.0`, and `info == {}`
remain unchanged.

## Frozen scalar and provenance

At lifetime start, `h_0 = 0.0`. Before each real action, `p_t` is the
unchanged D-027 pre-update prediction of `delta_beacon_forward` for the action
actually executed. After the real next visible observation occurs, `y_t` is
the visible forward-channel delta and the evaluator computes:

```text
p_recurrent_t = p_t + h_t
h_(t+1) = h_t + 0.5 * (y_t - p_recurrent_t)
         = (1 - 0.5) * h_t + 0.5 * (y_t - p_t)
```

The `0.5` is exactly `D027_LEARNING_RATE`; no alternate or tuned alpha exists.
The scalar is initialized once and never reset at mode transitions, SEEK entry,
logging windows, anchors, or analysis windows. It uses no RNG and no evaluator
geometry, labels, outcomes, seed identity, future observation, or Arm-A value.

The clean executable protocol SHA is
`eb462805be013131cfc9fe844c1ded0b2e81179c` and is passed unchanged to the
official artifact writer. No official output was executed before that clean
freeze. The official artifact
hash and size, exact replay gate, validation log, and descriptive output are
the authoritative machine-readable record below.

## Frozen analyses

1. Prequential baseline versus recurrent forward-prediction signed/absolute
   errors: pooled, per seed, false-contact SEEK, controller mode, lifetime
   quarter, all four actions, and finite `h` range/final summaries. All 20
   within-seed MAE directions are retained.
2. Exact D-036 pre-action eligibility and target/null semantics at horizons
   `64`, `256`, and `1024`. Strict deterministic leave-one-seed-out ridge uses
   intercept plus S0 or S0 plus current pre-action `h`, with fixed alpha
   `0.01`, identical support, per-fold counts/MAE/correlation, paired MAE
   deltas, and null/untestable all-negative binary support.
3. Exact D-034 `ALT_4/8/16` and
   `NO_FORWARD_PROGRESS_4/8/16` anchors. Each available anchor reads
   contemporaneous pre-action `h` and is matched within seed to the nearest
   ordinary non-anchor eligible state by S0-only squared distance, with
   smallest trace index as tie-break. Every anchor is excluded from controls.
4. Exact D-037 first contiguous eligible false-contact SEEK strict left/right
   alternating run of at least 16 decisions. Before/at/after 16-decision
   windows and one same-seed S0-only non-onset control preserve boundary nulls.

No p-value, universal pass percentage, hidden detector, threshold, or causal
recruitment rule is introduced. The only interpretation categories are the
seven predeclared categories in issue #135, retained in the JSON artifact.

## Freeze and validation provenance

The complete executable module, focused tests, this protocol record, and the
index entry were committed before official execution or inspection of the
reused support. The bounded pre-freeze replay regression used only legal seed
`18468` for 32 transitions and verified canonical Arm-B identity against an
uninstrumented run; it was not an official result.

Official output was generated from the clean protocol SHA above using only
`18468..18487`. If a protocol defect is found, this record must preserve the
invalidated SHA/artifact/hash/size/reason and require a clean rerun without
tuning from output.

## Official output

The exact current results, support/null statuses, replay gates, validation
commands, artifact provenance, interpretation category, and all required
summary tables are recorded in the JSON artifact. This record makes no
confirmatory claim and does not authorize D-040, EXP work, causal scaffold
recruitment, or a larger recurrent mechanism.

**surprised_by:** To be filled only from the frozen official artifact; no
pre-output expectation is treated as a result.
