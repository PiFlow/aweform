# D-034 — Closure-valid history-triggered de-trap recruitment audit

- **id:** D-034
- **issue:** [#120](https://github.com/PiFlow/aweform/issues/120)
- **lane:** Development
- **authoritative_base_sha:** `594a8a26a7c0e220c51f44fd1a3d477956d99414`
- **base_tree_sha:** `b8fb30224c3bf881fa4c4685926c29bcbf31b8b3`
- **development_seeds:** `18468..18487` inclusive, reused exactly
- **underlying lifetime horizon:** `70,000` transitions
- **delayed branch horizon:** at most `4,096` transitions from each anchor
- **status:** protocol frozen; official output pending execution
- **disposition:** `CONTINUING`

The machine-readable result will be
[`D-034-history-triggered-detrap-recruitment-audit.json`](D-034-history-triggered-detrap-recruitment-audit.json).

## Question and boundary

D-034 asks whether a short piece of closure-valid causal history can time
recruitment of the existing stochastic false-contact SEEK scaffold. It is an
evaluator-only matched branch audit. It does not claim that the organism can
learn either trigger.

The accepted D-031R1 Arm A (`LEARNED_WITH_DETRAP`) and Arm B
(`LEARNED_NO_DETRAP`) are replayed exactly. D-034 changes no organism-visible
channel, action, controller architecture, learner, reward, `info`, physics,
RNG stream, or plasticity boundary. The trigger label, family, length,
history, and branch condition are evaluator-only.

Only the ordered reused Development seeds `18468..18487` are permitted. No
fresh seed block, EXP execution, rescue, retuning, or D-035 work is authorized.

## Frozen protocol

For every seed, the executable protocol first requires exact accepted replay
of both D-031R1 arms. Identity includes outcomes and termination, action and
visible-trajectory digest, executed-update digest, full final D-027 state,
policy/environment RNG digests, mode/action summaries, and SEEK/delegation
counters. Instrumented replay must also match direct replay.

The D-032 matched first-delegation pre-action reference is reconstructed from
Arm A and Arm B. Prefix equality includes the completed trajectory, current
six-channel observation, physical evaluator state, controller/transient state,
complete learner state, policy RNG before the delegation draw, environment RNG,
and executed-update prefix digest. The matched Arm-B state is then used for a
reference `DETRAP_OFF` continuation and a `DETRAP_ON` continuation. OFF must
reproduce Arm B and ON must reproduce Arm A over the comparable continuation.

On the accepted Arm-B causal trace, the first available post-action anchor is
selected independently for each family and each length in exactly
`{4, 8, 16}`:

1. `ALT_k`: `k` completed false-contact SEEK actions, all turns, with strict
   left/right alternation, no contact/reacquisition, and no forward or wait
   action.
2. `NO_FORWARD_PROGRESS_k`: `k` completed false-contact SEEK transitions with
   `b0` equal to visible `beacon.forward` before the window and
   `max(b1..bk) <= b0` exactly, using only the visible six-channel history.

Unavailable anchors remain unavailable; no relaxation or substitution is
allowed. Trigger detection uses completed executed actions and six-channel
observations, with the replayed false-contact SEEK eligibility guard. It does
not use hidden pose, heading, distance, geometry, future outcome, seed
identity, or Arm-A results.

From every available delayed anchor, a complete cloned Arm-B causal state is
used for exactly two branches:

- `DETRAP_OFF` keeps inherited Arm-B behavior and must match the accepted B
  continuation exactly.
- `DETRAP_ON` changes only false-contact SEEK delegation eligibility from `0`
  to the inherited `1/3`. It keeps one policy-RNG arbitration draw at the same
  decision timing, the inherited explorer state, hazard `1/8`, the same learned
  steering when nondelegated, no `begin_segment()` or reseed, no new RNG
  stream, ordinary physical action execution, reward `0.0`, empty organism
  `info`, and one unchanged D-027 executed-action update from the actual next
  six-channel observation. Delegation remains available until reacquisition,
  termination, or truncation.

Branch-order invariance and anchor immutability are checked. Branches stop at
reacquisition, inherited termination/truncation, or the 4,096-transition
horizon.

## Required reporting

The JSON artifact retains, per seed/family/length, availability and exact
anchor transition; the complete closure-valid trigger history and digest;
anchor energy, thermal/contact state, and causal-state digests; OFF/ON
reacquisition, latency, stop reason, energy, path/displacement, visible
beacon, evaluator distance, heading, actions, forward-boundary classes,
alternation runs, delegation/effective-perturbation/action counts, first
delegation latency, explorer calls, learner/update/RNG digests, and exact
paired ON-minus-OFF signs. It preserves nulls and unavailable seeds.

Pooled summaries remain separate for `ALT_4`, `ALT_8`, `ALT_16`,
`NO_FORWARD_PROGRESS_4`, `_8`, and `_16`. Interpretation categories are
predeclared for broad delayed-recruitment sufficiency, action-pattern
specificity, visible-progress sufficiency, timing sensitivity, no delayed
trigger sufficiency, and reference-equivalence failure. There is no universal
pass threshold and no output-dependent protocol tuning.

## Freeze gate and provenance

The complete implementation, accepted A/B replay gates, reference controls,
frozen predicates and lengths, cloned-state runner, exact ON/OFF semantics,
metrics, categories, tests, and artifact writer must be committed cleanly
before official delayed-recruitment output on `18468..18487` is executed or
inspected.

- **protocol_only_freeze_sha:** `0e5405230ed9e78416426187a415392661b51a2a`
- **implementation_probe_sha:** `0e5405230ed9e78416426187a415392661b51a2a`
- **artifact_sha256:** to be recorded after official artifact generation
- **artifact_size_bytes:** to be recorded after official artifact generation

The exact 40-character clean executable SHA will be copied into this record
and the JSON artifact. If a genuine defect invalidates an official run, the
invalidated SHA, checksum, reason, and provenance remain recorded; only the
defect is fixed and the official protocol is rerun from a new clean SHA.

## Interpretation discipline

Observed branch outcomes are descriptive evaluator interventions. A positive
ON-versus-OFF pattern supports only that the tested bounded causal history was
sufficient to time recruitment of the existing scaffold on this Development
support. It does not establish a learned trigger, generic failure awareness,
consciousness, emotion, subjective experience, genuine life, or metabolism.

**surprised_by:** pending frozen execution; no output has been used to tune the
protocol.

**disposition:** `CONTINUING`.

## Invalidated official execution

The first official execution was invalidated before artifact serialization.

- **invalidated_executable_sha:** `0e5405230ed9e78416426187a415392661b51a2a`
- **artifact_sha256:** unavailable; the writer aborted before writing the JSON
- **artifact_size_bytes:** unavailable; no artifact was serialized
- **provenance:** `uv run python -m aweform.d034 --executed-commit-sha 0e5405230ed9e78416426187a415392661b51a2a --output development/D-034-history-triggered-detrap-recruitment-audit.json`, official seed `18468`, first delayed anchor `ALT_4`
- **reason:** the trigger-capture replay comparison passed the accepted Arm-B artifact directly to the private-weight identity comparison instead of adding the artifact's flattened `_weights` field. This caused a false identity mismatch at `ALT_4`; no delayed outcome was interpreted.

Only this provenance-comparison defect is corrected. The frozen trigger
definitions, lengths, branch horizon, branch semantics, metrics, and
interpretation rules are unchanged. The corrected protocol will receive a new
clean executable SHA and the official support will be rerun from scratch.
