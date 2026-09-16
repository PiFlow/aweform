# D-040 — Causal problem-identification and test-validity audit

- **id:** D-040
- **issue:** [#137](https://github.com/PiFlow/aweform/issues/137)
- **date:** 2026-09-14
- **lane:** Development
- **authorized_base_sha:** `833beeabd0d50ad94e1c265873b1c024634c87e4`
- **reused_development_seeds:** `18468..18487` inclusive, in order
- **fresh_development_holdout:** `18488..18507` inclusive, in order
- **lifetime_horizon:** `70,000` real transitions
- **branch_horizon:** at most `4,096` real transitions from an anchor
- **status:** protocol frozen; compact artifacts committed; final-run provenance recorded
- **disposition:** `CONTINUING`

The intended compact artifacts are
[`D-040-causal-problem-identification-test-validity-audit-reused.json`](D-040-causal-problem-identification-test-validity-audit-reused.json)
and
[`D-040-causal-problem-identification-test-validity-audit-holdout.json`](D-040-causal-problem-identification-test-validity-audit-holdout.json).
This record is the durable executable-protocol specification. No substantive
D-040 causal-map output is reported here.

The authorization gate is the issue-#137 task body and its authorized base
SHA above. Before integration, record that the candidate executable tree is
descended from that SHA (`git merge-base --is-ancestor`), and that no
unrelated base or branch is substituted.

## Purpose and non-solution boundary

D-040 audits whether the recent D-028→D-039 tests and causal interventions
were valid, and maps when and where the already-existing de-trap scaffold has
causal benefit along the failed Arm-B trajectory. It tests whether the
underlying bottleneck is timing, partial observability, deterministic policy
collapse, counterfactual grounding, or experience-distribution change rather
than assuming that “learn when to recruit the de-trap scaffold” is the right
problem.

This is evaluator-only Development work. It authorizes no new organism
mechanism, causal memory, recurrence, stuck detector, counter, meta-controller,
scaffold-recruitment rule, sensor, action, learner, reward, physics, ecology,
planning, world model, intrinsic objective, networking, physical control, EXP
execution, D-041, or successor task. The canonical organism, four actions, six
visible channels, D-027 168-weight learner and executed-action update, D-030
learned steering and tie rule, D-026 delegation probability `1/3`, explorer
hazard `1/8`, D-024/D-020 physical semantics, reward `0.0`, and
organism-facing `info == {}` remain unchanged.

All positions, headings, distances, contact geometry, wall/boundary truth,
trajectory labels, treatment labels, branch outcomes, and causal-benefit
targets are evaluator-only. They may be recorded or used in read-only branch
diagnostics, but may not reach action selection, learner updates, RNG,
environment transitions, reward, `info`, or retained organism state.

## Questions and historical/common-mode audit

The audit asks:

1. Can a task-local runner, intentionally independent of the common high-level
   D-034/D-036/D-037/D-038/D-039 analysis stack, reproduce the accepted Arm-B
   causal path and D-034 scaffold effect?
2. When does enabling the existing scaffold first become beneficial relative
   to the exact same no-de-trap state?
3. Do current observation, completed closure-valid history, D-027/D-030
   predictor state, the exact D-039 scalar, or simple diagnostic histories
   predict that benefit without privileged geometry?
4. Does the scaffold act as a localized rescue, or primarily change the future
   action/trajectory distribution in a way a static pre-action trigger misses?
5. Are prior negative results studying a collapsed no-de-trap distribution
   rather than proving that temporal information is irrelevant?

Before interpreting any D-040 treatment, the implementation must produce a
claim→implementation→evidence→assumption matrix for D-028 through D-039.
The following inventory is the frozen audit scope. It preserves distinctions
between causal interventions, shadow/post-hoc analyses, and evaluator upper
bounds; it is not a reclassification of predecessor results.

| record | accepted executable/result provenance | question and evidence class | dependency/common-mode risk to check | accepted limitation or result not established |
|---|---|---|---|---|
| D-028 | executable `8000b325d9429c674cfff3ea18edf331ede5f4a0`; artifact `4d5cfa0aced828aea7cc638f480d5aa4420642ac6454f1e2d5620490b8cce3a0`, `2,161,581` bytes | D-027 residual attribution; shadow cross-fit/oracles | `d028` over D-016/D-024–D-027; keep learning, representation, and privileged geometry paths distinct | did not establish a new sensor, history, learner, or control rule |
| D-029 | executable `7db4ccccb28e895c4d9c81f177b3460b632156e4`; artifact `d584fb8352fa28cb255c44359c5f0bf071dd9f705efd7ddaa29e608369378896`, `1,732,798` bytes | all-action consequence readiness; evaluator-only unexecuted queries | `d029` over D-024–D-027; check exact prior support and final environment-RNG retention | sparse, output/context-specific prediction did not authorize learned action selection |
| D-030 | executable `c3a2a0d4c05f99c90adf39cb4e86a75a10c61cca`; artifact `9770b027db3091371aebac57d7815f27d847030794d1f44c377baa0a84543f1b`, `1,876,381` bytes | first causal learned SEEK steering comparison; three-arm replay | `d030` over D-026/D-027/D-029; check read-only prediction and selected-branch isolation | did not establish general counterfactual reasoning, planning, or a world model |
| D-031R1 | executable `dc9a0c3d0b15d040b21aa52f133a4d1dacb41fb2`; artifact `ae5095135f4a9618fb81b815bd201312a7c2bc979eca88499f7b097dc8905b61`, `2,097,014` bytes | clean Arm-A/Arm-B/C scaffold-displacement rerun; causal matched lifetimes | `d031r1` over D-030/D-026/D-027; check exact Arm-B identity, one draw, and no-de-trap semantics | scaffold function was not uniquely attributed |
| D-032 | executable `a02630e1f40686c45479ce9f303d89c813fa2b94`; artifact `9cabd7d2725f015cacc86fe1d3378584915a48eb605734d596ba3a81e4d58000`, `13,746,074` bytes | de-trap function attribution; matched-onset and shadow diagnostics | `d032` directly reuses D-031R1; do not treat event-centred comparisons as randomized causal effects | persistence, symmetry breaking, non-myopic benefit, and diversification remained unresolved |
| D-033 | executable `fdb1e6b4ffba26d656936936ca7fb72bf34a98aa`; artifact `882808043cf080c33b8fbb1e968472ff67ffb4f9ee67522e8c314ecaac77829e`, `14,165,237` bytes | short forced sequence sufficiency; evaluator-only cloned branches | `d033` over D-031R1/D-032; check anchor capture and forced-action update timing independently | same-action persistence did not resolve the tested support |
| D-034 | executable `17abb0050c563aec070b46df6a026a6f93c8b9ef`; artifact `e0d5cbdffc4e3fb429eddcbcf5af0ff4f6772eaca0368459acc1e90ed6680e1d`, `3,252,808` bytes | closure-valid history-triggered de-trap recruitment; matched OFF/ON intervention | `d034` over D-031R1–D-033; this is the positive control, not the independent implementation | evaluator history sufficiency did not establish learned triggering or a stuck detector |
| D-035A | executable `fa36c8097364e224be8442f1b302656e52d21db6`; artifact `c9acba47fbc8f322c494b4114feeb3012e7a9e867b0eab29ba0dc22fc7e5aab9`, `12,762,450` bytes | turn-quantum attribution; physical evaluator counterfactual | `d035a` over D-031R1/D-032/D-033; keep logical actions and evaluator angles separate | did not establish organism-side fine control or docking recovery |
| D-035B | executable `30dfdfc98c287ded46f0992ffb11a31bb6b48dee`; artifact `019a318a8c052d98a33cfc0825287199c51334d409a1cacfd050c727add38f9c`, `99,075,876` bytes | L/F/R interpolation attribution; evaluator-only interpolation | `d035b` over D-031R1/D-032/D-033; interpolation is not an action or sensor | no reacquisition or organism interpolation was established |
| D-035C | executable `ea36b078e262a68e5c2fa6ad63325da4762a3468`; artifact `7a4a462da68346fedd9a78028c99c8d58aa5d1e0f8c2c8f95bee75105c0ba584`, `2,375,030` bytes | reverse-translation sufficiency; evaluator upper-bound branch | `d035c` over D-031R1/D-032/D-033; reverse must not update D-027 or enter logical-action counts | local geometry benefit did not establish recovery or authorize reverse motion |
| D-036 | executable `661e310887ac2ffef0b52df7defa8ea6cc2a66b8`; artifact `ce767536a9002d0b605cf60df15a1f77a58d61864a8e6c986576e20e887e03d6`, `936,914` bytes | shadow H1/H4/H8/H16 learnability; post-hoc readout/bridge | `d036` over D-032–D-034; check pre-action eligibility excludes mode-after/post-action outcome and own action | all-negative binary target was untestable; history did not yield stable held-out error improvement |
| D-037 | executable `0013596bf404f85c3e8acb7b565953977890ae7b`; artifact `db7da49b59b920235159c6ab35f71e78224412affd2f0d03aba4a5fa276f1e6b`, `597,425` bytes | shadow D-027/D-030 predictor-state signals; post-hoc readout | `d037` over D-031R1–D-034/D-036; check S1 indexes exact learned executed action and pooled supports | no stable error improvement or recruitment coherence |
| D-038 | executable `79c7cef9da5f5772752406357367e4b6a3f113d5`; artifact `4e5f0ca22b7583029d76c32d557d5edbf9bac9d9ad4347a999f4c873d7de25a3`, `103,496,012` bytes | combined fine-turn/interpolation/reverse sufficiency; evaluator interaction branches | `d038` over D-035A/B/C and D-031R1/D-033; keep reverse diagnostics separate from canonical actions | combined evaluator treatment did not restore recovery |
| D-039 | executable `c864f57dd1458d139bea2882bfac06ed8334fa52`; artifact `c1733686a038a193223c61d6259169ce46bd05838f04540ffb7706c2a2e87cca`, `505,829` bytes | one-scalar shadow recurrence; post-hoc prediction/bridge/onset | `d039` over D-031R1–D-034/D-036; check executed-action prediction, recurrence timing, and no causal feedback | one-step improvement did not produce recruitment-coherent held-out benefit |

Known invalidated provenance is preserved, never pooled as evidence: D-028
`b4f8845799f8dd90af71924ad41d63e63260b33b` / artifact
`010f635f618c9c4ae6519a1d9c7dbf086a70f58665e72d84c1a16ce112524ac7` was a
4.3 GiB singleton-heavy serialization, and `1e51f267db19aec90bd2c18f07ea0addaa78a584`
/ `0f5f13c602bd01c3ff0d25aebd3f8779ca1b5a13175339f09287f08396438222` lacked
required policy-RNG and heading-oracle fields. D-029
`3dbccc5ee42a123d8c2b92f463e5a9fc5955813f` / `da05f15d0ac6f8d1adebbac4f83e6f51773a649c2dd09b6d8d86d8ba4590c205`
omitted final environment-RNG equality; its earlier
`f4c90e2cd7cecc64c1843eb5aa1d42499aa80084` /
`84690ef766d27efd293a9ea7c80958dc03a98eeec6ffd3f6a050898c379401de`
omitted joint unexecuted-Q4 retention. D-034
`0e5405230ed9e78416426187a415392661b51a2a` falsely mismatched private
weights, while `b58771b06086888908fe3da2dc94b8f25f656218` rejected the valid
`AWAY` matched-reference state. D-036
`3675be49a640b519ac42d956692b93778362bf60` /
`81260bf42f80bf42204939dbf19c304e69d131576a0803f43c53bb78ba63e343` leaked
the scored action and lacked deterministic bridge matching, and
`ae1b47e3d35b6198143a2138a00ac081fd62db1a` /
`32df6a73953b90e109fcccf11de42bbfda63c3da5b1be846081039c91f053366` used
mode-after/post-action eligibility. D-037
`b0d8d1ef315f66503742d2ac2ceb0ab47effc52` /
`cc3cad6739c9242176ced06bed63601a7396bd3c568222993ab95f8e1579bf49` omitted
pooled correlations/class counts, and `51c5f5867d4bd7aac2fac3544b4c62c73a21dd4c`
/ `7247c012487673a0125723313863df91829d62abe0abc335096222b7e391019c` used
the historical/greedy action instead of the exact learned action. D-038’s
recorded invalidation chain includes oversized artifacts and conflated
evaluator/canonical logical-action diagnostics. D-031R1’s unmerged PR #112
and seeds `18448..18467` are not imported. The D-040 implementation must
verify all hashes against repository evidence before using this inventory.

If D-040 finds a reproducible contradiction, it must stop headline
interpretation, identify the exact common-mode defect, and preserve rather
than rewrite predecessor records.

## Independent replay identity gates

The task-local runner must re-derive anchor eligibility, causal-state cloning,
branch execution, primary target computation, and headline interpretation from
lower-level accepted components and frozen records. It may reuse immutable
low-level environment, body, controller, learner, and RNG primitives. It must
not call high-level private helpers from `d034`, `d036`, `d037`, `d038`, or
`d039` for any critical validity claim. D-031R1 may be a comparator, not the
sole independent implementation. Tests and artifact metadata must expose this
boundary.

For every reused and holdout seed, independent Arm-B must match the canonical
current `LEARNED_NO_DETRAP` path from the same initial condition on action and
visible-trajectory digests; termination/truncation/outcome; controller mode
and arbitration counters; D-027 executed-action update, complete 168-weight
state, and final digest; policy/environment RNG states/digests; zero
false-contact SEEK explorer/delegation calls; exactly one legacy policy draw
per false-contact SEEK decision; reward `0.0`; and `info == {}`. It must also
match accepted D-031R1 fields on reused support, and instrumented and
uninstrumented independent replays must agree. Any mismatch blocks treatment
interpretation.

## Sol-requested protocol corrections

The initial executable candidate `db2facbb29a295fd00f02e5e91371bf001ed19da`
was invalidated by Sol before its outputs could be interpreted. The bounded
correction freezes the following details:

1. D-034 comparison anchors use the accepted eligibility predicate on every
   completed row: `mode_before == SEEK`, `mode_after == SEEK`, pre-contact
   false, and post-contact false. The runner checks availability and anchor
   transition identity for every reused seed against the hash-verified
   accepted D-034 record.
2. `OSCILLATION_ONSET` is the pre-action state at the first action of the
   first contiguous eligible strict L/R alternating run that reaches length
   16. The completion transition is recorded separately and cannot select the
   anchor.
3. Each branch stops immediately after first reacquisition, termination, or
   truncation. Fixed later horizons retain explicit stop/null metadata and do
   not include charging or departure transitions after reacquisition.
4. Official execution runs the exact configured 70,000-transition Arm-B
   protocol for every reused seed through both the independent and canonical
   comparator paths, and compares independent versus canonical for every
   holdout seed. The gate includes action/visible-trajectory, outcome,
   termination, mode/arbitration, D-027 update and final-weight, both RNG,
   zero explorer/delegation, one legacy draw, reward, and empty-info fields.
5. F1 is reported as separate fixed `H4`, `H8`, and `H16` families. Prefixes
   that are unavailable remain null; all three use the same target semantics.
6. Trajectory-distribution windows include evaluator-only D-027
   prediction/update summaries before and after first ON delegation. These
   summaries never enter the controller, learner, RNG, environment, reward,
   or `info`.

## D-034 positive control and negative controls

Independently reconstruct exact pre-action D-034 `ALT_4/8/16` and
`NO_FORWARD_PROGRESS_4/8/16` anchors, including availability/null status,
transition, causal digest, and branch semantics. The accepted D-034 artifact
is a historical positive-control fixture, not D-040 output. Its predeclared
aggregate reproduction target is:

| anchor | available | historical OFF reacquired | historical ON reacquired |
|---|---:|---:|---:|
| `ALT_4` | 18 | 0 | 18 |
| `ALT_8` | 17 | 0 | 17 |
| `ALT_16` | 17 | 0 | 16 |
| `NO_FORWARD_PROGRESS_4` | 20 | 0 | 20 |
| `NO_FORWARD_PROGRESS_8` | 20 | 0 | 20 |
| `NO_FORWARD_PROGRESS_16` | 20 | 0 | 20 |

A material contradiction in identity, availability, branch outcome, or
semantics—including any per-seed mismatch against the accepted control
artifact—blocks downstream interpretation until explained. At selected
anchors, independently cloned `OFF_A` and `OFF_B` must be identical on
deterministic comparable fields; branch execution order must not change
outcomes, digests, support, or summaries. Cloning preserves physical state,
observation, controller/transient and explorer state, learner state, both RNG
states, transition index, horizon, and update-prefix digest, and does not
mutate the source. Diagnostics are read-only and cannot affect controller,
learner, RNG, environment, reward, `info`, anchor selection, or features.

## Frozen causal-benefit map

For each reused seed, identify the first false-contact SEEK episode under exact
Arm-B. An eligible decision is pre-action `mode == SEEK` with false visible
charging contact immediately before ordinary no-de-trap arbitration. Anchor
ordinal zero is the first such decision in that episode. Use exactly the
outcome-independent eligible ordinal offsets:

`0, 1, 3, 7, 15, 31, 63, 127, 255, 511, 1023, 2047, 4095, 8191`.

Unavailable offsets are explicit nulls with reasons, never nearest-state
substitutions or outcome-based replacements. Retain separately labelled exact
D-034 anchors and exact D-037 first `>=16` strict L/R oscillation onset where
available; none is selected by later branch outcome.

From every available anchor run exactly matched clones:

- `DETRAP_OFF`: accepted Arm-B continuation, zero delegation, one inherited
  legacy arbitration draw at each false-contact SEEK decision.
- `DETRAP_ON`: restore only existing D-030/D-026 false-contact SEEK delegation
  eligibility at probability `1/3`; retain `StochasticPersistentExplorer`
  hazard `1/8`, inherited explorer/RNG state, no reseed/new stream, no second
  `begin_segment()`, unchanged nondelegated learned steering, and unchanged
  transition/update semantics.

Branches run at most `4,096` real transitions, stopping on reacquisition,
termination, or truncation. At `64`, `256`, `1024`, and `4096`, report OFF/ON
reacquisition; ON-only/OFF-only/both/neither paired counts; latency where
defined; visible forward progress; net/path displacement; heading and
boundary diagnostics; energy/thermal change; action counts; strict alternation
persistence; first delegated action and latency; and evaluator-only one-step
truth around the first ON intervention. The primary causal target is the
paired effect of enabling the existing scaffold from the same exact state,
not a hand-labelled “stuck” state.

## Feature families and fixed readouts

Features are constructed only from the anchor pre-action state, after branch
generation, and never affect trajectories. Families are reported separately.

- **F0 / S0:** six visible channels: normalized own energy, beacon L/F/R,
  binary physical charging contact, and normalized own temperature.
- **F1 / S0+H4, H8, H16:** exact D-036 closure-valid completed histories,
  prior after-observations plus one-hot executed-action pairs; exclude the
  scored action. Preserve frozen dimensions `46/86/166` separately;
  insufficient prefixes are null, never padded or imputed.
- **F2 / S0+D027:** exact D-037 pre-action S1–S6: predicted forward delta
  for the exact executed learned action; max forward delta; largest-minus-
  second; population SD of the three forward deltas; centered 3×6 predicted
  consequence-matrix Frobenius norm; and 3×6×7 candidate-head weight-tensor
  Frobenius norm.
- **F3 / S0+h:** exact D-039 sequential shadow scalar: `h_0=0`, `p_t` is
  pre-update D-027 prediction for the actual action, and
  `h_(t+1)=h_t+0.5*(y_t-(p_t+h_t))` after visible delta `y_t`; never feed back.
- **F4 / closure-valid diagnostics:** elapsed false-contact SEEK decisions,
  current strict L/R alternation-run length, and current no-forward-progress
  run length from completed own actions/visible observations only. Diagnostic
  features do not authorize an organism detector or counter.
- **F5 / privileged geometry:** evaluator-only true pose/heading, world-frame
  boundary clearance, station-relative geometry, and dual-contact/docking
  geometry; forbidden from organism causal use.

At minimum predict binary ON-only 4096-step reacquisition benefit when support
exists, paired ON-minus-OFF forward-progress difference, and paired
reacquisition-latency difference where both latencies exist. Reused support
uses deterministic leave-one-seed-out fits. Holdout readouts are fit once on
reused support and scored on fresh seeds without fitting or tuning on them.
Use ridge alpha `0.01` for continuous targets and the same fixed transparent
binary readout convention: a ridge linear classifier with sigmoid-transformed
output, with no post hoc threshold tuning. Keep family supports equal for each comparison;
binary metrics are null when training or scoring support lacks both classes.

## Trajectory-distribution diagnostics

These are evaluator-only diagnostics, not objectives. Around the first actual
ON delegation, compare ON with matched OFF on fixed before/after windows
`16`, `64`, `256`, and `1024` where available: action distribution; longest
strict L/R run; cumulative absolute heading change; net displacement and path
length; six-channel visible-state variance/dispersion using one declared
simple statistic; and existing D-027 prediction/update summaries. Retain
whether ON’s first deviating action is locally truth-better or truth-worse
than OFF while its longer-horizon outcome is better or worse. Missing windows
remain nulls. No entropy, curiosity, intrinsic reward, exploration score, or
trajectory-distribution objective is introduced.

## Support, interpretation, and holdout freeze

Anchor-unavailable, insufficient-history, early-termination, and missing-
latency cases remain explicit statuses. Exclude a value only from its affected
metric/readout when its support condition fails; never convert it to zero.
When both branch outcomes are defined at a horizon, status is `ON_ONLY`,
`OFF_ONLY`, `BOTH`, or `NEITHER`. The ON-only binary label is `1` only for
`ON_ONLY` and `0` for the other paired statuses; it is null for absent or
one-class support. A continuous difference is null unless both values exist.

The complete runner, gates, grid, branches, features, readouts, categories,
tests, artifact schema, and this record are committed from a clean tree before
substantive reused output is inspected. Reused support runs first; the exact
holdout then runs on `18488..18507` from the same clean executable SHA. Results
remain separate Development observations before any optional pooled summary.
Defect correction preserves invalidated SHA/hash/size/command/reason and
requires a new clean SHA plus both-support rerun. No result-driven tuning,
seed substitution, protocol relaxation, or acceptance-condition change is
allowed.

Use only these headline categories, with multiple allowed: (1) validation
contradiction — prior interpretation blocked; (2) scaffold benefit is
early/widespread; (3) scaffold benefit is late/regime-localized; (4)
organism-available state/history predicts benefit; (5) privileged geometry
dominates — partial observability remains plausible; (6) trajectory-
distribution/diversification role supported descriptively; (7) static
recruitment formulation unsupported; (8) no stable scaffold-benefit structure
on tested support; (9) ambiguous/multiple bottlenecks remain. Categories cite
support, nulls, matched contrasts, and readout separation. None authorizes a
mechanism or a consciousness, emotion, genuine-life, metabolism, or
confirmatory claim.

## Compact artifact and provenance schema

Each artifact is deterministic compact JSON with no raw transition dump,
per-decision arbitration records, completed history observations, or readout
prediction/actual vectors. It retains their deterministic digests/counts and
contains:

```text
schema_version, experiment=D-040, protocol_version
authorized_base_sha, clean_executable_protocol_sha, working_tree_clean, command
runtime_and_platform, seed_role, ordered_seeds, lifetime_horizon, branch_horizon
anchor_offsets, comparison_anchor_definitions, arm_identity_gate_definition
branch_semantics, feature_family_definitions, readout_definition_and_fixed_alpha
control_results_and_control_gate, per_seed_identity_and_anchor_summaries
per_seed_branch_outcome_summaries, pooled_summaries_by_horizon_and_family
trajectory_distribution_diagnostics, support_and_null_counts
interpretation_categories_and_selected_categories, invalidated_runs
artifact_sha256, artifact_size_bytes, validation
```

Per-seed records retain compact action/visible-trajectory/update/RNG digests,
outcome/termination, mode/arbitration/delegation counts, anchor availability
and causal-state digest, branch outcomes at every frozen horizon, latencies,
paired signs, readout support, null reasons, and evaluator-only diagnostics.
Use a declared codebook and store derivable values once. Keep reused and
holdout sections separate; a holdout artifact may link the separate reused
training artifact by digest but must not embed its results. Include
D-031R1/D-034 source artifact hashes.

The prior corrected implementation and support runs are preserved as invalidated
provenance, not as usable D-040 output:

- **clean executable protocol SHA:** `c9b017e63d4f4b01f32afa55efab257153d1d7bb` (invalidated for artifact contract)
- **reused artifact SHA-256 / size:** `a28fa81cdd6f00665b162ead6e25dc5ad3ffd8a01924d4147406f1d228bf457f` / `168,791,151`
- **holdout artifact SHA-256 / size:** `2458da4a3d09f86a362a6c3910d6b3bf8dd3d3ce28ac62f77f81211e9351be41` / `336,622,010`
- **invalidated reason:** Sol found the artifacts non-compact and not independently reviewable; the full reused support was embedded in the holdout artifact.
- **manager-integrated clean executable/schema SHA:** `bfeef5bb72deb78182d08069d359d497452a9363`
  (the worker-local `29a4fb19d6d3853e1dcb79cfc62aed86fac6b0c3` SHA is not official
  provenance)
- **final reused artifact SHA-256 / size:**
  `764c1b09f18c250cb55682d434c2b6f372a9e66d82380b88c0bc08ab85cd495d` /
  `19,502,181` bytes
- **final holdout artifact SHA-256 / size:**
  `c31edd4c919f7cf6713feb59cd49b32dd69c38180bd26f65c0fab5d279d55f98` /
  `18,761,262` bytes
- **final deterministic regeneration checks:** reused regeneration hash and size
  matched exactly with `cmp PASS`; holdout regeneration hash and size are recorded
  above, but the independent `cmp` remains pending manager verification.
- **invalidated D-040 run:** executable SHA
  `db2facbb29a295fd00f02e5e91371bf001ed19da`; reused artifact SHA-256
  `88cf8d0872f966e4f867ab236e9b991c6508c9489d25e8d100c1dec3ca96d113`
  (`162,684,976` bytes); holdout artifact SHA-256
  `05da0c2728e7c009520a0b1d5002a8cc021ae2a90b30423c00858f991b9052c5`
  (`324,675,921` bytes). Status: invalidated by Sol. Reasons: the six
  bounded protocol defects corrected above (D-034 eligibility/identity,
  delayed oscillation onset capture, post-reacquisition branch continuation,
  incomplete official Arm-B identity gate, collapsed F1 history reporting,
  and missing D-027 trajectory summaries). These artifacts are not valid
  D-040 output and are never pooled or interpreted.
- **exact final local provenance-record commit:** this local commit; no PR is opened
  or pushed by this worker

Any invalidated run records executable SHA, artifact hash/size when written,
command, seed role/support, write status, and exact defect. A record-only edit
does not change the executable protocol SHA; executable correction requires a
new clean SHA and both-support rerun.

## Final compact-artifact provenance

The official committed D-040 support artifacts were generated from the
manager-integrated clean executable/schema SHA
`bfeef5bb72deb78182d08069d359d497452a9363`. The worker-local correction SHA
`29a4fb19d6d3853e1dcb79cfc62aed86fac6b0c3` is not used for this provenance.
The reused support contains official seeds `18468..18487` inclusive; the fresh
holdout contains official seeds `18488..18507` inclusive. Both artifacts use
compact schema v2. Their raw-transition, raw-arbitration, raw-trigger-observation,
and raw-readout-prediction/actual flags are all `false`. The holdout has no
embedded reused support result arrays and carries only a separate reused-support
reference with `embedded: false`.

The exact official generation commands were:

```text
uv run python -m aweform.d040 --support reused --executed-commit-sha bfeef5bb72deb78182d08069d359d497452a9363 --output development/D-040-causal-problem-identification-test-validity-audit-reused.json
uv run python -m aweform.d040 --support holdout --executed-commit-sha bfeef5bb72deb78182d08069d359d497452a9363 --output development/D-040-causal-problem-identification-test-validity-audit-holdout.json
```

The manager independently regenerated the reused artifact with:

```text
uv run python -m aweform.d040 --support reused --executed-commit-sha bfeef5bb72deb78182d08069d359d497452a9363 --output /private/tmp/aweform-d040-compact-reused-regenerated.json
cmp development/D-040-causal-problem-identification-test-validity-audit-reused.json /private/tmp/aweform-d040-compact-reused-regenerated.json
```

The regenerated reused file had SHA-256
`764c1b09f18c250cb55682d434c2b6f372a9e66d82380b88c0bc08ab85cd495d` and size
`19,502,181` bytes; `cmp` passed. The corresponding holdout regeneration
command is:

```text
uv run python -m aweform.d040 --support holdout --executed-commit-sha bfeef5bb72deb78182d08069d359d497452a9363 --output /private/tmp/aweform-d040-compact-holdout-regenerated.json
cmp development/D-040-causal-problem-identification-test-validity-audit-holdout.json /private/tmp/aweform-d040-compact-holdout-regenerated.json
```

The holdout artifact has SHA-256
`c31edd4c919f7cf6713feb59cd49b32dd69c38180bd26f65c0fab5d279d55f98` and size
`18,761,262` bytes. Its regeneration `cmp` remains pending manager verification;
no holdout regeneration PASS is claimed here.

This is compact, reviewer-accessible committed support only. It makes no
substantive causal interpretation and authorizes neither D-041 nor any EXP
execution.

## Required validation

Before substantive output, focused tests cover independent eligibility/anchor
reconstruction and log-spaced nulls; independent/canonical Arm-B identity;
D-034 positive control; OFF-vs-OFF clone identity; branch-order invariance;
no-evaluator-feedback/leakage; legal seed blocks; fixed-feature support and
null handling; and deterministic artifact regeneration. Record:

```text
uv run pytest -q tests/test_d040.py
git merge-base --is-ancestor 833beeabd0d50ad94e1c265873b1c024634c87e4 HEAD
uv run pytest -q
uv run ruff check .
uv run mypy src --strict
uv run python -m compileall -q src tests
git diff --check
uv run python -m aweform.d040 --support reused --executed-commit-sha bfeef5bb72deb78182d08069d359d497452a9363 --output development/D-040-causal-problem-identification-test-validity-audit-reused.json
uv run python -m aweform.d040 --support holdout --executed-commit-sha bfeef5bb72deb78182d08069d359d497452a9363 --output development/D-040-causal-problem-identification-test-validity-audit-holdout.json
cmp development/D-040-causal-problem-identification-test-validity-audit-reused.json /private/tmp/aweform-d040-compact-reused-regenerated.json
cmp development/D-040-causal-problem-identification-test-validity-audit-holdout.json /private/tmp/aweform-d040-compact-holdout-regenerated.json
```

Also record exact-current-HEAD GitHub CI. A SHA-tied validation claim requires
a clean checkout and exact committed tree; dirty/pre-freeze runs are disclosed
and are not official output.

## Organism boundary and disposition

The audit remains causally inert. It does not make D-039 `h` causal, add a
history buffer, alter D-027/D-030, expose F5 geometry, change action
granularity, add reverse/interpolation, change ecology/physics, add reward or
`info`, touch formal EXP reservations, or start a successor.

**surprised_by:** Not yet observed. This record intentionally freezes the
question and validity machinery before substantive causal-map output.

**disposition:** `CONTINUING`.

## Next

After the clean executable protocol SHA is recorded, run reused support and
its validity gates, then run the exact fresh holdout from that same SHA. Report
reused and holdout observations separately. Flow controls any later decision;
no mechanism follows automatically.
