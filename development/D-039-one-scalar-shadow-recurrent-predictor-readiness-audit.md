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
`c864f57dd1458d139bea2882bfac06ed8334fa52` and is passed unchanged to the
official artifact writer. No official output was executed before that clean
freeze. The artifact hash and size, exact replay gate, validation log, and
descriptive output are
the authoritative machine-readable record below.

## Frozen analyses

1. Prequential baseline versus recurrent forward-prediction signed/absolute
   errors: pooled, per seed, false-contact SEEK, controller mode, lifetime
   quarter, all four actions, and finite `h` range/final summaries. Pooled
   overall, false-contact SEEK, and per-action summaries are serialized. All
   20 within-seed MAE directions are retained.
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

Recruitment/oscillation coherence is reported only when one predeclared pooled
bridge or onset contrast has a single direction with no opposing paired signs;
a bare majority is retained as mixed and cannot receive the coherence
category.

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

### Invalidated official attempt

The first official attempt used executable SHA
`eb462805be013131cfc9fe844c1ded0b2e81179c` and produced no artifact
(checksum and size unavailable). Its provenance was:

```text
uv run python -m aweform.d039 --executed-commit-sha eb462805be013131cfc9fe844c1ded0b2e81179c --output development/D-039-one-scalar-shadow-recurrent-predictor-readiness-audit.json
```

It was invalidated before any result was interpreted because the shadow
wrapper initially retained the controller proposal rather than the actual
executed Arm-B action after D-031R1 learned steering replaced that proposal.
The recurrence was therefore not evaluated from the declared executed-action
prediction. The correction binds `p_t` at the real D-027
`observe_transition(action=...)` call; the scalar, analysis rules, support,
and interpretation categories are unchanged. The corrected protocol receives
a new clean executable SHA and reruns the complete support from scratch.

### Invalidated completed artifact

The next official execution used corrected executable SHA
`5a9ccb952ef6fd074a678e5221a907370422ab32` and produced
`development/D-039-one-scalar-shadow-recurrent-predictor-readiness-audit.json`
with SHA-256
`989545b6086ae12be14106b8665ec3832885502ad780fcbd30f91f31064f4b10` and
size `501391` bytes. It is invalidated before interpretation. Replay gates
passed, but the artifact did not serialize the required top-level pooled
false-contact SEEK summary, and its automatic coherence classification treated
the mixed `9/17` onset sign split as coherent. The fixed protocol serializes
the pooled strata and reserves coherence for a genuinely same-direction
contrast; it reruns the same support from scratch.

### Latest invalidated completed artifact

The next official execution used executable SHA
`c9fd57b31881124bdbcc67afd6f121a972959bd7` and produced
`development/D-039-one-scalar-shadow-recurrent-predictor-readiness-audit.json`
with SHA-256
`6f6a2f9c1475ab6b22c510499a4b015f34b3acf37dc17ce43e9179a9eec6ad70` and
size `505355` bytes. It is invalidated before interpretation because
`_pooled_error_summary()` concatenated per-seed local index arrays and then
used those reset indices on the already-concatenated prediction/target arrays.
Later seeds therefore repeatedly selected the beginning of the pooled arrays,
so the serialized pooled one-step MAE and support multiset were wrong despite
the total sample count being correct. The bounded fix aggregates the already
concatenated arrays directly, adds a two-seed regression, and reruns the exact
same support without changing the recurrence, analyses, matching/null rules,
interpretation categories, alpha values, or scientific scope.

## Official output

The corrected official artifact was generated from clean executable protocol
SHA `c864f57dd1458d139bea2882bfac06ed8334fa52` using only the exact reused
seeds `18468..18487`. Its SHA-256 is
`c1733686a038a193223c61d6259169ce46bd05838f04540ffb7706c2a2e87cca` and its
size is `505829` bytes. A second generation to `/private/tmp/d039-regenerated.json`
was byte-identical (`cmp` exit `0`, same SHA and size).

All `20/20` accepted Arm-B replay gates passed on outcome/termination, action
and visible trajectory, complete D-027 update/state digest, policy and
environment RNG digests, mode/arbitration counters, zero false-contact SEEK
explorer calls, one legacy policy draw per false-contact SEEK decision, reward
`0.0`, and `info == {}`. All scalar updates were finite, used the actual
executed action's pre-update D-027 prediction, and matched both recurrence
forms at every transition.

Pooled one-step forward prediction used `1,152,541` transitions: baseline MAE
`0.00593019`, recurrent MAE `0.00466482`, delta `-0.00126537`. Every seed
improved (`20/20`, `0` worsened, `0` ties). On the exact false-contact SEEK
support (`665,908` transitions), baseline MAE was `0.00090611` versus
recurrent `0.00114207`, delta `+0.00023596`; the scalar worsened this
recruitment-relevant stratum. Pooled per-action summaries, mode/quarter
strata, per-seed MAE signs, and finite `h` ranges are retained in JSON.

The exact D-036 LOSO S0 versus S0+H results were:

| horizon | S0 MAE / correlation | S0+H MAE / correlation | mean paired MAE delta | improved / worsened |
|---:|---:|---:|---:|---:|
| 64 | `0.00069746 / 0.06450` | `0.00090057 / 0.16852` | `+0.00020311` | `7 / 13` |
| 256 | `0.00070086 / 0.06537` | `0.00088451 / 0.16196` | `+0.00018365` | `7 / 13` |
| 1024 | `0.00072163 / 0.06612` | `0.00087543 / 0.14795` | `+0.00015380` | `7 / 13` |

Support was identical for S0 and S0+H at every fold and horizon. The binary
reacquisition target was all-negative/untestable and is reported null.

The D-034 bridge had `112/120` available anchors and `112/112` matched controls
across `ALT_4/8/16` and `NO_FORWARD_PROGRESS_4/8/16`. Pooled anchor-minus-
control `h` was mixed: `50` positive, `62` negative, `0` ties; mean delta
`-0.00068449`. Per-family/per-length availability and distributions are
retained in JSON.

The exact D-037 oscillation onset was available on `17/20` seeds, with `17/17`
same-seed controls. The before window was available on `9/17`; at and after
windows were `17/17`. Onset-minus-control `h` was mixed: `9` positive,
`8` negative, `0` ties; mean delta `+0.00079130`. Window summaries and nulls
are retained in JSON.

Interpretation: **Predictive but not recruitment-coherent**. The one-step
reduction is descriptive predictive support on this replay, but the
recruitment-relevant false-contact SEEK error worsened, S0+H held-out
future-progress MAE worsened at all three horizons, and both bridge contrasts
were mixed. This is not confirmatory evidence and does not authorize a
threshold, causal scaffold recruitment, D-040, EXP work, or a larger recurrent
mechanism.

The scalar remained shadow-only. Canonical Arm-B behavior, D-027 weights and
update semantics, four actions, six visible channels, physics, RNG, reward,
and organism-facing `info` were unchanged. No D-040, EXP, or causal
recruitment work was started.

**surprised_by:** The scalar improved one-step MAE on every seed and raised
future-progress correlation, yet worsened the exact false-contact SEEK
one-step MAE and held-out future-progress MAE. This separates generic
prequential residual correction from a recruitment-coherent temporal signal.
