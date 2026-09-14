# D-040 — Historical/common-mode audit of D-028 through D-039

- **task:** `D040_CAUSAL_PROBLEM_IDENTIFICATION_TEST_VALIDITY_AUDIT`
- **scope:** historical/common-mode audit only; no D-040 causal-map execution
- **audited repository HEAD:** `833beeabd0d50ad94e1c265873b1c024634c87e4`
- **authorized base:** `833beeabd0d50ad94e1c265873b1c024634c87e4`
- **ancestry check:** `git merge-base --is-ancestor 833beeabd0d50ad94e1c265873b1c024634c87e4 HEAD` passed
- **evidence basis:** repository source, focused tests, Markdown records, JSON artifacts, Git history, and locally recomputed artifact SHA-256 values
- **status:** supporting audit for D-040; this document does not revise any predecessor record

## Executive finding

The historical sequence contains a strong accepted causal foundation for the
claim that the existing stochastic de-trap scaffold matters on the reused
support, but it does not provide an independent validity check of that claim.
The reason is structural: from D-030 onward, later audits increasingly reuse
private high-level helpers from the preceding audit stack. D-034, D-036,
D-037, D-038, and D-039 in particular share substantial replay, anchor,
identity, clone, target, and matching machinery. This is a **common-mode risk**,
not evidence that the helpers are wrong. D-040 must independently re-derive
critical validity semantics before interpreting a new causal-benefit map.

The historical records also show repeated corrections. Most were reporting,
provenance, serialization, or indexing defects rather than demonstrated
causal-mechanics failures. They are scientifically important because they show
where a superficially passing audit can fail: future/post-action leakage,
wrong executed-action binding, incomplete identity fields, invalid executable
SHAs, reverse/logical-action conflation, and pooled-index errors. The accepted
results below are the corrected results only; invalidated outputs remain listed
for provenance.

The classifications in this report use the following labels:

- **causal intervention:** the tested branch changes a causal action or physical
  continuation, even when the intervention is evaluator-only and cannot change
  the organism;
- **shadow/post-hoc:** the organism's causal trajectory is unchanged and a
  diagnostic model or signal is computed after or alongside replay;
- **evaluator upper bound:** a privileged or hypothetical branch tests physical
  capacity unavailable to the organism;
- **matched evaluator counterfactual:** an evaluator-only intervention from an
  exact cloned causal state. It is causal for the branch comparison, but not an
  organism mechanism or learning result.

All scientific interpretations below are Development-lane observations. Any
statement about what a result implies beyond its frozen support is an **audit
inference**, not a repository fact.

## Claim → implementation → evidence → assumption matrix

| Stage | Claim/question actually tested | Implementation and classification | Evidence and support | Assumptions, non-establishments, and D-040 risk to check |
|---|---|---|---|---|
| **D-028** | Why D-027's unchanged one-step learner is weak on charging-contact and boundary-clipped beacon consequences: online LMS dynamics, visible representation, or omitted state? | [`d028.py`](../src/aweform/d028.py) replays the exact D-027 lifetime, then performs exact-key alias census, cross-fit linear/quadratic OLS, and privileged geometry/oracle calculations. **Shadow/post-hoc plus evaluator upper-bound oracle**; no causal intervention. Direct dependencies: `d016`, `d024`, `d025`, `d026`, `d027`, `d020`, `exp003`, seed policy. | Seeds `18388..18407`; `70,000` uninterrupted transitions per seed; `1,400,000` transitions. Accepted executable `8000b325d9429c674cfff3ea18edf331ede5f4a0`; accepted artifact [`D-028...json`](D-028-d027-residual-attribution-audit.json), SHA-256 `4d5cfa0aced828aea7cc638f480d5aa4420642ac6454f1e2d5620490b8cce3a0`, `2,161,581` bytes. Focused tests [`test_d028.py`](../tests/test_d028.py). | Sparse repeated visible-key support (only `0.1264%` of transitions in repeated keys) does not test sufficiency or aliasing broadly. The heading/wall-aware oracle is privileged and upper-bound only. D-040 should independently check replay identity, boundary labels, geometry reconstruction, and evaluator-oracle isolation without relying on D-028's replay/reporting helpers. |
| **D-029** | Whether the unchanged D-027 predictor has one-step consequence information for all four candidate actions, including unexecuted actions, from visited states. | [`d029.py`](../src/aweform/d029.py) queries the learner read-only and executes four deep-copied one-step environment branches; the real selected action alone updates the learner. **Matched evaluator counterfactual/readiness audit**, not organism causal control. Direct dependencies: `d024`, `d025`, `d026`, `d027`, `d020`, seed policy. It establishes the shared `_branch`, `_clone_environment`, state-digest, and RNG-digest machinery later stages reuse. | Seeds `18408..18427`; `70,000` real transitions per seed; `1,400,000` real transitions and `5,600,000` candidate rows. Accepted executable `7db4ccccb28e895c4d9c81f177b3460b632156e4`; accepted artifact [`D-029...json`](D-029-action-alternative-readiness-audit.json), SHA-256 `d584fb8352fa28cb255c44359c5f0bf071dd9f705efd7ddaa29e608369378896`, `1,732,798` bytes. Focused tests [`test_d029.py`](../tests/test_d029.py). | Exact prior-support support was zero for all candidate rows; this is sparse support, not a license for similarity matching. Alternative branches are not learner experience and cannot establish counterfactual competence. D-040 should re-check branch cloning, order invariance, selected-branch equality, exact executed-action update semantics, and reference-run isolation independently. |
| **D-030** | Whether learned forward-beacon prediction can causally influence non-delegated false-contact SEEK steering, versus a fixed cyclic permutation control. | [`d030.py`](../src/aweform/d030.py) changes only the non-delegated false-contact SEEK choice in Arm B; Arm C applies a fixed cyclic prediction permutation; Arm A is unchanged reference. **Organism-causal controller intervention within the already authorized D-030 development mechanism**, with evaluator-only one-step truth branches. Critical inherited helper: `d029._branch`, plus `d029._environment_state`, `_controller_state`, `_rng_state`. | Seeds `18428..18447`; `70,000` per uninterrupted lifetime and arm; 20 three-arm lifetimes. Accepted executable `c3a2a0d4c05f99c90adf39cb4e86a75a10c61cca`; artifact [`D-030...json`](D-030-bounded-learned-seek-steering.json), SHA-256 `9770b027db3091371aebac57d7815f27d847030794d1f44c377baa0a84543f1b`, `1,876,381` bytes. Focused tests [`test_d030.py`](../tests/test_d030.py). | Arm B completed 20/20 full cycles, Arm C failed SEEK on 20/20, and all listed branch/reference isolation checks passed. This does not establish general learned steering, exact revisitation, planning, or a world model. **Common-mode:** D-030's critical branch truth and state/RNG isolation depend on D-029 private helpers; D-040 must not treat D-030's checks as independent evidence of those helper semantics. |
| **D-031R1** | Whether disabling the engineered `1/3` false-contact SEEK delegation causes learned steering to lose reacquisition, and whether a no-de-trap failure is learning-specific. | [`d031r1.py`](../src/aweform/d031r1.py) runs Arm A with inherited de-trap, Arm B learned no-de-trap, and Arm C greedy no-de-trap. **Organism-causal matched arm intervention**, with evaluator-only candidate branches. Critical inherited helpers: `d030._choose_steering_action`, `d030._trace_update_digest`; `d029._branch`, state, and RNG helpers. | Seeds `18468..18487`; `70,000` per arm and seed; 20 matched three-arm lifetimes. Accepted executable `dc9a0c3d0b15d040b21aa52f133a4d1dacb41fb2`; artifact [`D-031R1...json`](D-031R1-learned-seek-scaffold-displacement-clean-rerun.json), SHA-256 `ae5095135f4a9618fb81b815bd201312a7c2bc979eca88499f7b097dc8905b61`, `2,097,014` bytes. Focused tests [`test_d031r1.py`](../tests/test_d031r1.py). | Arm A was `FULL_CYCLE` 20/20; B and C were `FAILED_SEEK` 20/20; B/C had zero delegation and zero false-contact explorer calls, with one retained policy draw per decision. This supports scaffold importance at this competence/support, not a unique de-trap function or a learned replacement. D-040 must reproduce exact Arm-B identity and the one-draw/zero-explorer contract without using the D-031R1 runner as its sole implementation. |
| **D-032** | Which descriptive functions are consistent with the D-031R1 scaffold result: boundary stall, one-step action choice, temporal persistence, symmetry breaking, or diversification? | [`d032.py`](../src/aweform/d032.py) wraps direct D-031R1 runs with instrumentation, then performs a matched first-delegation evaluator branch and post-hoc window summaries. **Shadow/post-hoc plus matched evaluator counterfactual**, not learned recruitment. Critical dependencies: `d031r1._run_arm`; `d029._clone_environment`, state, and RNG; shared identity comparison. | Same seeds `18468..18487`; `70,000` per arm; windows `1,4,16,64,256,1024,4096`; 20 matched first-delegation onsets. Accepted executable `a02630e1f40686c45479ce9f303d89c813fa2b94`; artifact [`D-032...json`](D-032-detrap-function-attribution-audit.json), SHA-256 `9cabd7d2725f015cacc86fe1d3378584915a48eb605734d596ba3a81e4d58000`, `13,746,074` bytes. Focused tests [`test_d032.py`](../tests/test_d032.py). | Arm A moved/reacquired 20/20 after onset while B did 0/20; B's failure was dominated by long L/R alternation, not clipped/stalled forward events. The event-effective versus ineffective comparisons are state-confounded and not randomized attribution. D-040 must treat the result as a scaffold effect, not proof of temporal persistence, symmetry breaking, or diversification. **Common-mode:** the wrapper and branch checks inherit D-031R1 and D-029. |
| **D-033** | Whether a short evaluator-forced action commitment (2/4/8/16 steps) is sufficient to break the no-de-trap oscillation. | [`d033.py`](../src/aweform/d033.py) captures exact pre-action Arm-B states and clones them; each forced sequence still runs the unchanged controller pipeline and one executed-action D-027 update. **Matched evaluator counterfactual**, not organism persistence. Critical dependencies: `d032._compare_identity_fields`, `d032._left_right_alternation_runs`; `d029` clone/state/RNG; `d031r1` replay. | Seeds `18468..18487`; lifetime `70,000`; branch horizon `4,096`; first-delegation anchor available 20/20, exact `ALT8_ESTABLISHED` 17/20 (nulls `18471`, `18473`, `18478`); lengths `2,4,8,16`; artifact [`D-033...json`](D-033-short-horizon-sequence-sufficiency-audit.json), SHA-256 `882808043cf080c33b8fbb1e968472ff67ffb4f9ee67522e8c314ecaac77829e`, `14,165,237` bytes; executable/freeze `fdb1e6b4ffba26d656936936ca7fb72bf34a98aa`. Focused tests [`test_d033.py`](../tests/test_d033.py). | Repeated B-proposed actions did not reacquire at either anchor; two directional controls succeeded only on seed `18474` after release. This does not establish persistence insufficiency in general: interventions are state-local and action-direction/geometry remain confounded. **Common-mode:** anchor capture, fingerprint, branch clone, and baseline checks reuse D-032/D-029 helpers. |
| **D-034** | Whether closure-valid completed visible history—strict alternation or no forward progress—can time recruitment of the existing scaffold in matched branches. | [`d034.py`](../src/aweform/d034.py) reconstructs Arm A/B, matches first delegation, finds Arm-B history anchors, then changes only false-contact SEEK delegation from `0` to `1/3` in cloned branches. **Matched evaluator causal intervention**, not organism learning. Critical dependencies: `d033._accepted_artifact`, `_accepted_arm`, `_run_capture`, `_anchor_from_capture`, `_anchor_fingerprint`, `_expected_baseline_trace`, `_rewire_controller_rng`, `_learner_from_weights`, `_find_alt8_transition`; `d032` identity/alternation; `d029` clone/state/RNG. | Seeds `18468..18487`; lifetime `70,000`; branch horizon `4,096`; six trigger families/lengths `ALT_4/8/16` and `NO_FORWARD_PROGRESS_4/8/16`; 112 available anchor pairs. Accepted executable/freeze `17abb0050c563aec070b46df6a026a6f93c8b9ef`; artifact [`D-034...json`](D-034-history-triggered-detrap-recruitment-audit.json), SHA-256 `e0d5cbdffc4e3fb429eddcbcf5af0ff4f6772eaca0368459acc1e90ed6680e1d`, `3,252,808` bytes. Focused tests [`test_d034.py`](../tests/test_d034.py). | ON reacquired on 18/18 ALT4, 17/17 ALT8, 16/17 ALT16, and 20/20 for every no-progress length; OFF reacquired 0 for every group. This establishes only that these evaluator-selected histories were sufficient to time the existing scaffold on this support. **Known common mode:** D-034 is the exact positive control D-040 must reproduce, but D-034 itself inherits the high-level replay/anchor/branch stack. |
| **D-035A** | Whether the observed L/R oscillation is partly attributable to the canonical 45° physical turn quantum. | [`d035a.py`](../src/aweform/d035a.py) changes only cloned evaluator turn angle (`45°`, `5°`, `2°`, `1°`) while keeping action identity, controller, learner, timing, and energy semantics canonical. **Matched evaluator physical counterfactual**. Dependencies: D-033 capture/anchor/branch helpers; D-032 comparisons; D-029 branch/state/RNG. | Seeds `18468..18487`; lifetime `70,000`; branch horizon `4,096`; anchors first false-contact SEEK (20/20) and ALT8 (17/20); 148 condition branches. Accepted executable/freeze `fa36c8097364e224be8442f1b302656e52d21db6`; artifact [`D-035A...json`](D-035A-turn-granularity-attribution-audit.json), SHA-256 `c9acba47fbc8f322c494b4114feeb3012e7a9e867b0eab29ba0dc22fc7e5aab9`, `12,762,450` bytes. Focused tests [`test_d035a.py`](../tests/test_d035a.py). | Finer angles lowered alternation/error but produced zero reacquisitions; fixed timestep and energy exposure are explicit confounds. It does not authorize fine canonical turns or establish that turn quantum is necessary. **Common-mode:** 45° equivalence, anchor identity, and branch order rely on D-033/D-029 helpers. |
| **D-035B** | Whether evaluator-side L/F/R interpolation of visible beacon values changes turn magnitude, geometry, or reacquisition attribution. | [`d035b.py`](../src/aweform/d035b.py) evaluates fixed/interpolated sub-45° magnitude in cloned branches; logical actions remain the four canonical actions. **Matched evaluator physical counterfactual**. Dependencies: D-033 capture/anchor/state/branch; D-032 identity; D-029 clone/state/RNG. | Seeds `18468..18487`; lifetime `70,000`; branch horizon `4,096`; first false-contact SEEK 20/20 and ALT8 17/20; 37 anchor sets, 259 branch rows. Final accepted executable/freeze `30dfdfc98c287ded46f0992ffb11a31bb6b48dee`; artifact [`D-035B...json`](D-035B-lfr-interpolation-attribution-audit.json), SHA-256 `019a318a8c052d98a33cfc0825287199c51334d409a1cacfd050c727add38f9c`, `99,075,876` bytes. Focused tests [`test_d035b.py`](../tests/test_d035b.py). | Final corrected result had no reacquisition. It does not establish organism interpolation, a new action, or causal sufficiency. This stage has the densest provenance history and is a warning that artifact size, anchor eligibility, action semantics, and executable-SHA identity must be checked separately. Common mode is substantial: D-035B reuses D-033 and D-029 for critical branch mechanics. |
| **D-035C** | Whether evaluator-only reverse translation gives unique local geometry correction or short-horizon dual-contact recovery. | [`d035c.py`](../src/aweform/d035c.py) evaluates hypothetical reverse displacement in cloned state; reverse is not an `Action`, never updates D-027, and is selected only by a privileged rear-contact error oracle. **Evaluator upper-bound plus matched counterfactual**. Dependencies: D-033 anchor/capture/state, D-032 identity, D-029 clone/state/RNG, low-level D-020/D-024. | Seeds `18468..18487`; lifetime `70,000`; branch horizon `256`; anchors first false-contact SEEK, ALT8, and first post-contact loss; artifact [`D-035C...json`](D-035C-reverse-translation-sufficiency-audit.json), SHA-256 `7a4a462da68346fedd9a78028c99c8d58aa5d1e0f8c2c8f95bee75105c0ba584`, `2,375,030` bytes; accepted executable/freeze `ea36b078e262a68e5c2fa6ad63325da4762a3468`. Focused tests [`test_d035c.py`](../tests/test_d035c.py). | Reverse was uniquely best for one-step rear geometry on all 20 post-loss anchors, but the oracle added no short-horizon recovery; it was uniquely best on only 4/20 first-contact anchors. This does not establish that reverse is missing or sufficient. **Common-mode:** privileged selection, baseline identity, and reverse no-update guards share the same high-level stack D-040 must audit independently. |
| **D-036** | Whether bounded recent closure-valid history predicts productive versus unproductive false-contact SEEK continuations. | [`d036.py`](../src/aweform/d036.py) builds shadow H1/H4/H8/H16 features and fixed-alpha LOSO readouts from ordinary Arm-B traces; it then performs D-034 bridge matching. **Shadow/post-hoc learnability audit**. Critical dependencies: `d033._run_capture`, `_accepted_arm`, `_flatten_final_weights`; `d032._compare_identity_fields`; `d034._find_trigger`; D-036 own trace/target helpers. | Seeds `18468..18487`; lifetime `70,000`; target horizons `64,256,1024`; H dimensions `6/46/86/166`; D-034 bridge `112/120` available anchors. Corrected executable/freeze `661e310887ac2ffef0b52df7defa8ea6cc2a66b8`; artifact [`D-036...json`](D-036-shadow-short-history-recruitment-learnability.json), SHA-256 `ce767536a9002d0b605cf60df15a1f77a58d61864a8e6c986576e20e887e03d6`, `936,914` bytes. Focused tests [`test_d036.py`](../tests/test_d036.py). | Reacquisition target was all-negative and therefore binary readout was untestable; progress results were mixed/worse for history. This does not establish that memory failed, only that this shadow readout did not provide stable support. **Common-mode:** eligibility/anchor semantics directly call D-034 `_find_trigger`; replay and target semantics call D-033/D-032. D-040 must re-derive pre-action eligibility and no-future target construction. |
| **D-037** | Whether endogenous D-027/D-030 predictor-state signals S1–S6 add recruitment-relevant information beyond current visible S0. | [`d037.py`](../src/aweform/d037.py) captures pre-action D-027 state, computes read-only signals, LOSO readouts, D-034 bridge, and D-037 oscillation-onset windows. **Shadow/post-hoc signal audit**. Dependencies: D-033 capture/accepted arm/weight flattening; D-032 identity; D-034 trigger/anchor; D-036 trace/anchor/target utilities. | Seeds `18468..18487`; lifetime `70,000`; target horizons `64,256,1024`; onset available 17/20, before window 9/17, at/after 17/17. Corrected executable/freeze `0013596bf404f85c3e8acb7b565953977890ae7b`; artifact [`D-037...json`](D-037-endogenous-prediction-state-recruitment-signal-audit.json), SHA-256 `db7da49b59b920235159c6ab35f71e78224412affd2f0d03aba4a5fa276f1e6`, `597,425` bytes. Focused tests [`test_d037.py`](../tests/test_d037.py). | The corrected S1 binding is the actual learned-selected action; S0+S1..S6 did not improve held-out MAE and binary support was all-negative/untestable. This does not prove endogenous predictor state is irrelevant. **Common-mode:** D-037 uses D-036 target/trace machinery and D-034 trigger selection; D-040 should not count it as an independent test of those semantics. |
| **D-038** | Whether a joint evaluator-only combination of fine turns, L/F/R interpolation, and privileged reverse can restore recovery. | [`d038.py`](../src/aweform/d038.py) composes D-035B/C mechanics over T0 baseline, T1 fine fixed, T2 interpolation, T3 combined 5°, T4 combined 2°. **Matched evaluator counterfactual and evaluator upper-bound**. Dependencies: D-035B/C, D-033 anchors/state, D-029 clone/state/RNG, D-032 identity. | Seeds `18468..18487`; lifetime `70,000`; branch horizon `4,096`; 285 available seed+anchor treatment groups, 5 treatments each. Latest accepted executable/freeze `79c7cef9da5f5772752406357367e4b6a3f113d5`; artifact [`D-038...json`](D-038-combined-fine-interp-reverse-sufficiency-audit.json), SHA-256 `4e5f0ca22b7583029d76c32d557d5edbf9bac9d9ad4347a999f4c873d7de25a3`, `103,496,012` bytes. Focused tests [`test_d038.py`](../tests/test_d038.py). | T0–T4 added no recovery over the first-contact/ALT8 anchors; the one post-loss recovery was 1/20 in every treatment. The combination is an evaluator upper bound, not an organism capability test. **Common-mode:** D-038 is explicitly composition of predecessor mechanics and had a reverse-versus-logical-action reporting defect; D-040 must separate selected logical action, executed canonical action, and evaluator operation. |
| **D-039** | Whether one exact shadow scalar `h` from experienced forward-prediction residuals adds temporal predictive information and localizes D-034/D-037 states. | [`d039.py`](../src/aweform/d039.py) computes `h` sequentially from actual executed-action D-027 pre-update prediction and actual visible delta; it never feeds back. **Shadow/post-hoc recurrent readout**. Dependencies: D-033 accepted replay/arm/weights; D-034 trigger selection; D-036 trace/target/ridge/AUROC utilities. | Seeds `18468..18487`; `70,000` per Arm-B lifetime; 1,152,541 transitions overall and 665,908 false-contact SEEK transitions; D-034 bridge 112/120; D-037 onset 17/20. Accepted executable/freeze `c864f57dd1458d139bea2882bfac06ed8334fa52`; artifact [`D-039...json`](D-039-one-scalar-shadow-recurrent-predictor-readiness-audit.json), SHA-256 `c1733686a038a193223c61d6259169ce46bd05838f04540ffb7706c2a2e87cca`, `505,829` bytes. Focused tests [`test_d039.py`](../tests/test_d039.py). | `h` improved overall one-step MAE but worsened false-contact SEEK MAE; future-progress MAE worsened at all horizons; bridge/onset contrasts were mixed. This does not prove temporal state is irrelevant. **Common-mode:** D-039's target, bridge, trigger, and replay semantics are inherited from D-036/D-034/D-033; D-040 must recompute `h` independently and keep it shadow-only. |

## Foundational dependency ledger: D-024 through D-027

D-028–D-039 are not independent of the earlier physical/controller/learner
foundation. These records are preserved and are not re-audited as D-040
claims, but their exact scope matters for interpretation.

| Stage | Accepted executable and support | What it established | What it did not establish / D-040 consequence |
|---|---|---|---|
| D-024 | [`D-024 record`](D-024-causal-finite-body-dual-contact-docking-probe.md); executable `2b71596683b444c1fa841e1bb56f0611cc23232d`; seeds `18365,18366,18367`; `70,000`. | Finite-body corresponding-pair dual-contact predicate under unchanged D-021 fixed controller; all three SEEK episodes failed to reacquire. | No robust docking, learning, or causal de-trap claim. D-040 must preserve exact pair-contact and AWAY incidental-contact semantics. |
| D-025 | [`D-025 record`](D-025-bounded-stochastic-seek-detrapping.md); executable `621d5e77643d3919138596e387b9de5b9fe1d944`; seeds `18365..18367`; `70,000`; delegation `1/8`. | Existing stochastic explorer can permit reacquisition/full cycle on all three declared lifetimes. | No robustness or learning claim. It is the historical scaffold that D-026 stabilized; D-040 must preserve explorer hazard and segment/RNG semantics. |
| D-026 | [`D-026 record`](D-026-one-third-seek-delegation-stabilization.md); executable `831c678ee4ccaa0b31e9c28c7e88dd35edebf75e`; seeds `18368..18387`; `70,000`; delegation `1/3`, explorer hazard `1/8`. | Fixed non-learning `1/3` delegation is coherent on 20 fresh development seeds: 20/20 full cycles. | No learner or learned recruitment claim. D-040's ON branch must restore exactly this existing eligibility/probability/hazard contract, with inherited RNG state. |
| D-027 | [`D-027 record`](D-027-shadow-sensorimotor-consequence-learning.md); executable `ad6b8abff0beb9812a510cbe53e652105d8b0bed`; seeds `18388..18407`; `70,000`; 168 weights, learning rate `0.5`. Artifact SHA-256 verified locally as `4433e5abee35c1d6fbf58d266c8d486bdfb34fcf07e7b38bf379f2968143bf52`, `672,459` bytes. | Shadow-only executed-action normalized-LMS prediction over six visible channels; no observed controller influence; mixed support-dependent prediction quality. | No wall awareness, counterfactual competence, memory, or learned control. D-040 must bind every replay/update check to the executed action and actual next six-channel observation. |

## Shared-helper/common-mode map

This is the critical historical risk map. Names below are repository source
facts from static inspection of imports and call sites; the risk statements are
audit inferences.

| Layer | Reused private machinery | Stages depending on it | Common-mode failure D-040 should independently test |
|---|---|---|---|
| Low-level causal substrate | `d024` environment/contact geometry, `d025` traces/explorer semantics, `d026` controller, `d027` learner, `d020` transition telemetry, `exp003_seed_policy` | D-028 onward, directly or through D-031R1 | Observation/action boundary, transition order, contact predicate, learner update timing, policy/environment RNG ownership, and exact reward/info boundary could be consistently misimplemented. |
| D-029 evaluator branch layer | `d029._branch`, `_clone_environment`, `_environment_state`, `_controller_state`, `_rng_state`, branch outcomes | D-030, D-031R1, D-032, D-033, D-034, D-035A/B/C, D-038; some via D-033 | Clone may omit mutable state; branch truth may mutate environment/controller/RNG; selected branch may not equal real transition; branch order may alter state while local tests use the same faulty fingerprint. |
| D-030/D-031 replay layer | `d030._choose_steering_action`, `_trace_update_digest`; `d031r1._run_arm` | D-031R1 direct; D-032 onward through captures and accepted artifacts | The supposedly accepted Arm-B identity path may be reproduced by the same runner that generated the reference artifact, masking a shared action/arbitration or update-order defect. |
| D-032 identity/anchor layer | `d032._compare_identity_fields`, `_left_right_alternation_runs`, D-032 instrumentation | D-033 onward, directly or through D-034 | Incomplete identity projection can certify a non-identical anchor. Historical fixes show private-weight shape, AWAY→SEEK mode, and report-field omissions are realistic failure modes. |
| D-033 state/branch layer | `_AnchorState`, `_run_capture`, `_anchor_from_capture`, `_anchor_fingerprint`, `_state_fingerprint`, `_expected_baseline_trace`, `_rewire_controller_rng`, `_learner_from_weights`, `_find_alt8_transition`, `_accepted_arm` | D-034, D-035A/B/C, D-036, D-037, D-038, D-039 | Anchors, learner state, transient controller/explorer state, transition index, and both RNG states may be cloned or selected with a shared omission. D-040 must re-derive exact anchors and compare all causal fields. |
| D-034 trigger/bridge layer | `_find_trigger`, trigger-family/history semantics, D-034 anchor records | D-036, D-037, D-039; D-034 is also D-040's positive-control source | Future/post-action leakage or trigger censoring could be shared by every history bridge. D-036's two invalidated outputs demonstrate this exact class of risk. |
| D-036 trace/target/readout layer | `_trace_data`, `_target_data`, `_auroc`, ridge conventions and target/null handling | D-037 and D-039 | Incorrect target indexing, null handling, concatenation, or eligible-state selection can propagate to both later shadow audits. D-039's pooled-index invalidation demonstrates the danger. |
| D-035B/C and D-038 treatment composition | D-035B interpolation and D-035C reverse mechanics; D-038 combined treatment | D-038 | Reverse evaluator operations can be conflated with canonical logical actions, altering action counts and trajectory-distribution diagnostics without changing physics. D-038 had to correct this twice. |

### Independence judgment

The historical stack is **not independent enough for D-040's critical validity
claims**. Reusing immutable low-level physical/learner primitives is expected
and scientifically appropriate. Reusing high-level private functions for
critical anchor selection, branch mechanics, target construction, or headline
interpretation is the common-mode coupling D-040 must avoid. In particular:

1. D-034 is a necessary empirical positive control, but reproducing it through
   D-034/D-033 helpers would be a circular validity check.
2. D-036, D-037, and D-039 cannot be treated as three independent tests of
   temporal information because their eligibility, target, bridge, and replay
   paths overlap.
3. D-038 cannot independently validate D-035B/C treatment semantics because it
   composes those modules; its accepted result is useful descriptive context,
   not an independent falsification of their mechanics.
4. The repeated historical reporting defects do not by themselves invalidate
   the corrected scientific results, but they justify demanding exact
   artifact/provenance and no-leakage checks before any D-040 interpretation.

## Historical invalidations and corrections

The following list preserves invalidated provenance. An invalidated artifact is
not used as evidence in this report.

| Stage | Invalidated provenance and defect | Bounded correction / accepted result |
|---|---|---|
| **D-028** | Executable `b4f8845799f8dd90af71924ad41d63e63260b33b`; artifact SHA-256 `010f635f618c9c4ae6519a1d9c7dbf086a70f58665e72d84c1a16ce112524ac7`; serializer retained ~1.4M singleton records and produced a 4.3 GiB artifact. Executable `1e51f267db19aec90bd2c18f07ea0addaa78a584`; artifact SHA-256 `0f5f13c602bd01c3ff0d25aebd3f8779ca1b5a13175339f09287f08396438222`; omitted policy-RNG isolation and heading-oracle realized-displacement error. | Compact alias serialization and evaluator-only reporting corrections; accepted executable `8000b325d9429c674cfff3ea18edf331ede5f4a0`, artifact `4d5c...3a0` above. |
| **D-029** | Executable `3dbccc5ee42a123d8c2b92f463e5a9fc5955813f`; artifact `da05f15d0ac6f8d1adebbac4f83e6f51773a649c2dd09b6d8d86d8ba4590c205`; omitted explicit final environment-RNG equality. Executable `f4c90e2cd7cecc64c1843eb5aa1d42499aa80084`; artifact `84690ef766d27efd293a9ea7c80958dc03a98eeec6ffd3f6a050898c379401de`; superseded by the exact-current-HEAD finding at reviewed HEAD `37734351db79ff5ab96be41656afedba1ad0fde9`: omitted unexecuted-candidate × lifetime-quarter aggregate. Separate corrections: `e08eb3ccb147e17c6b31b380a7d7ae4fe4173a6a` (stall classification) and `91ff47c41a7c596e9956e9c29a418bcaaba37a3e` (reference isolation); the intermediate artifact still lacked the required joint retention. | Final executable `7db4ccccb28e895c4d9c81f177b3460b632156e4` retains all eight execution/quarter cells; accepted artifact `d584fb8352fa28cb255c44359c5f0bf071dd9f705efd7ddaa29e608369378896`. |
| **D-030** | No invalidated substantive run is recorded in the accepted Markdown/JSON provenance. | Accepted executable/artifact above; negative permuted-control result retained. |
| **D-031R1** | Replaced protocol-invalidated, unmerged PR #112. Its artifact, record, seed block `18448..18467`, and output were not pooled. | Clean replacement accepted at `dc9a0c3d0b15d040b21aa52f133a4d1dacb41fb2`; no PR #112 result is evidence. |
| **D-032** | No invalidated official output is recorded in the accepted result record; later source/docs commits corrected pooling/provenance while retaining the causal scope. | Accepted executable `a02630e1f40686c45479ce9f303d89c813fa2b94`; exact 20-seed replay and matched onset checks passed. |
| **D-033** | No invalidated output is recorded. | Accepted executable `fdb1e6b4ffba26d656936936ca7fb72bf34a98aa`; unavailable ALT8 states remain null. |
| **D-034** | Executable `0e5405230ed9e78416426187a415392661b51a2a`; no artifact; false mismatch because accepted artifact weights were not flattened before private-state comparison. Executable `b58771b06086888908fe3da2dc94b8f25f656218`; no artifact; incorrectly required `SEEK` at a legitimate inherited AWAY→SEEK transition. | Corrected replay-weight comparison and inherited mode handling; accepted executable/freeze `17abb0050c563aec070b46df6a026a6f93c8b9ef`. |
| **D-035A** | No invalidated output is recorded. | Accepted executable `fa36c8097364e224be8442f1b302656e52d21db6`; corrected 45° control and all nulls retained. |
| **D-035B** | Initial protocol `8a0e23fbee23f3c47a6111dd3e23882f2402b176`, artifact `877c7355...d1086`: AWAY→SEEK anchor and missing stratification/reporting. A subsequent recorded SHA `7fb0846f4f7f3d6c52785b5a7c96c1e99784a33f` was not a Git object; actual source commit was `7fb08461694d838cb1333b9e3d66de8345780ac4`. Superseded protocol `2e791c84c3ad9c94c57d6dbddc283bb08ea6ff5b`, artifact `b4cded...1e27`: anchor and reporting defects. Large artifacts were invalidated at `c3e627a2b2007ff7ba79e881df808443528b0fee` (`7be721...60f89`) and earlier compact/size corrections. Protocol `83000c3764848f084d7517edfa8425b29a4b059d`, artifact `430e41...f266d`: Sol found T3/T4 behavior diagnostics conflated evaluator reverse with canonical logical-action sequence. | Final `30dfdfc98c287ded46f0992ffb11a31bb6b48dee` separates logical and evaluator records, keeps exact canonical action semantics, and regenerates byte-identically. |
| **D-035C** | No invalidated prior treatment output is recorded in the accepted record. | Accepted evaluator-only reverse upper-bound artifact at `ea36b078e262a68e5c2fa6ad63325da4762a3468`. |
| **D-036** | Protocol `3675be49a640b519ac42d956692b93778362bf60`, artifact `81260bf42f80bf42204939dbf19c304e69d131576a0803f43c53bb78ba63e343`: scored decision feature included its own executed action and bridge lacked deterministic matched non-anchor comparison. Protocol `ae1b47e3d35b6198143a2138a00ac081fd62db1a`, artifact `32df6a73953b90e109fcccf11de42bbfda63c3da5b1be846081039c91f053366`: eligibility used `mode_after` and post-action contact, causing future/outcome-dependent censoring. | Corrected pre-action eligibility, excluded current executed action, added deterministic bridge; accepted `661e310887ac2ffef0b52df7defa8ea6cc2a66b8`, artifact `ce767536a9002d0b605cf60df15a1f77a58d61864a8e6c986576e20e887e03d6`. |
| **D-037** | Protocol `b0d8d1ef315f66503742d2ac2ceb0ab47effc52f`, artifact `cc3cad...bf49`: omitted pooled scalar correlations and numeric per-fold target class counts. Protocol `51c5f5867d4bd7aac2fac3544b4c62c73a21dd4c`, artifact `7247c0...1019`: S1 used historical/greedy action rather than actual learned Arm-B action. | Added required pooled/count retention and bound S1 to the learned-selected executed action; accepted `0013596bf404f85c3e8acb7b565953977890ae7b`, artifact `db7da...f6e1b`. |
| **D-038** | Protocol `ac336d1406a0016c445f0b9b8db3aea6c3a46e25`, artifact `6abfe0...0dc3`: missing T3/T4 conformance diagnostics/tests. Earlier verbose artifact `c73a...62ae` was `2,832,241,674` bytes and nonviable. Later corrections included missing visible-side reversal, oversized artifacts at `6016a82ec2bb8f6cc6b79cf58f406cfea657b2a4`, and oversized D-035B encoding at `c3e627...`. Protocol `83000c3764848f084d7517edfa8425b29a4b059d`, artifact `430e41...f266d`: reverse interventions still conflated with canonical logical action diagnostics. Protocol `19acce381138a600ea778f98f72d2aa2b890b964`, artifact `b86e9e...f6968`: selected Arm-B logical actions still omitted. | Final `79c7cef9da5f5772752406357367e4b6a3f113d5` records selected logical actions separately from executed canonical actions and reverse operations; accepted artifact `4e5f...25a3`. |
| **D-039** | Attempt `eb462805be013131cfc9fe844c1ded0b2e81179c`, no artifact: scalar used controller proposal rather than actual executed action. Executable `5a9ccb952ef6fd074a678e5221a907370422ab32`, artifact `989545...4b10`: missing pooled false-contact summary and incorrectly called mixed `9/17` onset signs coherent. Executable `c9fd57b31881124bdbcc67afd6f121a972959bd7`, artifact `6f6a2f...ad70`: pooled summary indexed reset per-seed local ranges into concatenated arrays. | Bound `p_t` to the actual executed-action D-027 pre-update prediction, serialized pooled strata, required same-direction coherence, and fixed pooled aggregation; accepted `c864f57dd1458d139bea2882bfac06ed8334fa52`, artifact `c173...7cca`. |

## Cross-stage findings relevant to D-040's validity checks

### 1. Exact Arm-B identity is necessary but historically not sufficient

The records generally require action/visible trajectory, termination,
controller mode/counters, complete D-027 state or update digest, policy and
environment RNG state, explorer/delegation calls, reward `0.0`, and `info == {}`.
That is the right direction. However, historical defects show that an identity
gate can still be too weak or incorrectly applied:

- D-034 compared the wrong weight representation and rejected a valid inherited
  AWAY→SEEK state;
- D-035B accepted a recorded non-existent executable SHA in one provenance
  attempt;
- D-038 needed explicit separation of selected logical action from reverse
  evaluator operation;
- D-039 used the wrong action for a recurrent prediction before correction.

D-040 should therefore compare the complete causal state at the exact anchor,
not only a trajectory digest or headline summary.

### 2. “No future leakage” must cover eligibility, not only features

D-036's corrected protocol properly defines eligible samples from pre-action
`mode_before == SEEK` and current visible false contact. Its invalidated
predecessor used post-action mode/contact, which can censor a sample using the
continuation being predicted. D-040 must apply the same scrutiny to anchor
availability, trigger windows, matched controls, and feature construction.
Unavailable offsets/states must remain explicit nulls; nearest-state
substitution is not a harmless convenience.

### 3. Positive scaffold effects are real matched interventions but not unique explanations

D-034's ON-over-OFF results are the strongest historical positive control. They
show the existing scaffold has causal value when enabled from the selected
Arm-B states. They do not identify whether the useful role is persistence,
symmetry breaking, non-myopic sequence generation, trajectory diversification,
geometry, or an experience-distribution effect. D-032's event-level
effective/ineffective comparisons are state-confounded, and D-033's forced
sequences are action-direction confounded. D-040's primary target should be the
paired ON-minus-OFF causal effect from the same exact state, not a hand-labelled
“stuck” state.

### 4. Privileged diagnostics are useful only if strictly evaluator-only

D-028, D-032–D-035, and D-038 use pose, heading, pair errors, distance, branch
truth, or other evaluator state. The records consistently declare these
diagnostics evaluator-only and preserve reward `0.0`, organism `info == {}`,
six visible channels, four canonical actions, and unchanged D-027 semantics.
That declaration is a repository fact; independent D-040 tests must verify no
diagnostic changes controller, learner, RNG, environment, reward, or `info`.

### 5. Negative and null results are informative but support-limited

D-033's unavailable ALT8 anchors, D-034's one unresolved ALT16 branch, D-035A/B
zero-recovery branches, D-035C's limited oracle interventions, D-036/D-037
all-negative binary targets, and D-039 mixed bridge signs are all preserved.
They do not establish that memory, recurrence, fine turns, reverse translation,
or geometry are irrelevant in general. They establish only what was not found
on the declared support under the declared intervention/readout.

## Scope and governance boundary preserved

Nothing in the audited predecessor sequence authorizes D-040 to change the
canonical organism, sensors, actions, D-027 weights/update rule, D-030 steering
or tie semantics, ecology, physics, reward, `info`, EXP reservations, or a
successor mechanism. In particular, no historical result authorizes organism
memory, recurrence, a stuck detector, meta-control, reverse action, fine turn,
interpolation, planning, reward/RL, curiosity, a world model, D-041, or EXP
work. D-040 remains an evaluator/audit task until any durable boundary would
need a separate governance decision.

## Reproducibility note

The accepted artifact SHA-256 values listed in the main matrix were recomputed
from the current worktree with `sha256sum`; all matched the corresponding
accepted record values. No substantive D-040 causal-map execution was run.
The report itself is the only intended file change from this worker.
