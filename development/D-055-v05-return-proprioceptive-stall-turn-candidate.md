# D-055 — V0.5 RETURN proprioceptive stall-turn candidate

## Frozen protocol (result-free)

- **id:** D-055
- **lane:** Development; paired causal candidate intervention, not a Level-1 promotion or confirmatory claim
- **authorized launch base:** `f16a676bd60e0f92cbfaee36b54c6145b0d85706`
- **rebased execution base:** `45e946fb295b594954542e5f31fd54b9d15ec107`; docs-only PR #190 merged after launch, changing no D-055 source, tests, or protocol
- **corrected executable/protocol freeze:** the exact pushed SHA passed as the artifact's `executed_commit_sha`; the completed results section records it
- **status:** corrected executable/protocol freeze; official execution is not part of this commit
- **disposition:** pending official descriptive outcome

### Question

On the frozen D-054 wall/corner support and on seeded continuous lifetimes, does the one-decision RETURN stall-turn candidate, which reads only the prior RETURN command and existing wheel-delta channels, remove the unchanged D-050 wall wedge without harming states the unchanged floor already docks? Where it intervenes, what does it change?

### Candidate and boundary

Arm U is unchanged `D052Controller` / `run_d053_lifetime`. Arm C is `D055StallTurnCandidate`, an external wrapper around a fresh unchanged D-052 controller. After every decision whose D-052 active mode is RETURN, including the `RETURN_ACTIVATED` decision, it stores the wheel pair it emitted; after any NORMAL or CHARGE decision the register is `None`. The check on the `RETURN_ACTIVATED` decision itself therefore sees no prior RETURN command, and the activation command is checked on the next decision. A stall is detected when that register exists, its maximum absolute wheel value is at least `D045_ENCODER_QUANTUM_RAD` (one encoder count), and observation channels 6 and 7 are exactly zero. Only a RETURN / `D050_SMOOTH` / `CURVED_PURSUIT` decision is replaced, with `(-u,+u)` where `u=(R-L)/2` from the current D-052 command. The next decision is unchanged D-050. Other detected stalls are counted and not acted on. There is no latch, cap, learning, RNG, evaluator input, extra sensor, or accepted-path integration.

D-045 physics and the eight-channel observation, D-049, D-050, D-052, D-053, D-054, and the shared visualizer are unchanged. Reward remains zero and organism-facing `info` remains empty.

### Frozen supports and execution

Part A uses `d054.frozen_cases()` (768 positions/headings), D-054 Part C reset semantics, 20% battery and horizon 1,000. Both arms receive `(0,0)` proposals. RETURN activation is required on the first decision, and subsequent decisions remain RETURN through terminal contact. There is no absorbing-motion early stop. Outcomes follow DOCKED, first RETURN_HOLD/terminal-spin exhaustion, INVALID_BEACON after its executed decision, D-045 termination, then horizon censoring. The artifact retains both arms' compact D-054 fields, post-hoc wall-pinned/WEDGED classification and Arm-C stall counts/audit.

Part B follows the continuous D-053 lifetime protocol at 140,000 transitions, with the D-053 roaming fixture queried once per decision. Support is seeds `22053–22057`; fresh legal Development support is exactly `22550–22569`, checked by `validate_exp003_development_seeds` and an exact-block guard. Arm U calls unchanged `run_d053_lifetime`; Arm C uses the injected-controller replication and D-053 summary schema plus stall-count fields. Test-only seed `22570` is permitted only at horizon <=5,000 and initial battery fraction <=0.21. Tests do not run official seeds, the official matrix, or the official horizon.

### Frozen controls, readouts, and output

Required controls are D-054 Arm-S identity on the 640 docked states and non-docked status on the other 128; Arm-C no-intervention/prefix identity; D-053 committed-record identity on its five support seeds; Arm-C prefix identity before the first stall turn; and unchanged-summary identity when no stall turn occurs. A failed control invalidates/stops the official execution. No mechanism, threshold, gating, support, horizon, stop rule, or interpretation is changed after official output.

Pre-declared Part A readouts are the paired outcome cross-tab, docked/wedged/rescued/harmed counts, non-docked inset × wall/corner breakdown, intervention-conditioned paired docking-transition differences, stall counts, and detector audit (preceding boundary scale, scale strata, missed stalls). Part B reports paired first-RETURN-episode classes and per-seed pairs, separately for support and fresh blocks. Signature fields are `A_WEDGE_RESOLUTION` (`ALL`/`PARTIAL`/`NONE`), `A_HARM` (`NONE`/`SOME`), `B_SUPPORT`, and `B_FRESH`. A fresh block with no Arm-U failures is uninformative about rescue but remains informative about harm; harm/candidate-only failures are negative evidence and are not repaired in this stage.

The single deterministic JSON has no transition traces or visualization. Artifact floats use output-only `Decimal(x).quantize(Decimal('1e-12'), ROUND_HALF_EVEN)`, normalize negative zero, and reject non-finite values. The corrected artifact includes the invalidated first-run provenance and does not pool that output into interpretation. That first official run executed the complete protocol, including all 25 lifetimes and the 768-state matrix, but reversed the U_ONLY_FAIL/C_ONLY_FAIL labels and omitted the pre-declared per-cycle `stall_detected_count` readout; the corrected freeze changes only that label mapping, that readout, provenance, and tests. Official output and independent byte-identical regeneration are attributed to the corrected pushed freeze via `executed_commit_sha`; `authorized_base_sha` remains the launch base above, and `execution_base_sha` identifies the documentation-only rebased base. After the corrected freeze only this completed record, its JSON artifact, and one index row may change.

### Pre-freeze exposure

The artifact's top-level `pre_freeze_exposure` record discloses that a candidate unit test observed Part A state `bottom_wall-i0.00-p0.10-0.00-h14` for 2 decisions before the first official run, so 767 of the 768 Part A states were unexposed before official execution. No parameter was selected or modified from that observation. The frozen 768-state aggregate and signature are reported exactly as predeclared; this exposure is a provenance limitation, and the state is not excluded or replaced. The invalidated official run had also already executed fresh seeds `22550–22569` before the corrected freeze.

### Validation and claim boundary

This is an exploratory descriptive Development intervention. It does not promote the candidate to `D052Controller` or the constitutive Level-1 floor, change D-045 contact/boundary physics, make an EXP claim, or authorize a successor. Evaluator scale/position/telemetry are post-hoc diagnostics only. The programmed return behaviour remains engineered competence; no learning, consciousness, emotion, subjective experience, or genuine-life claim follows.

**surprised_by:** Pending the frozen official comparison; no candidate pilot is authorized before the executable/protocol freeze.

**disposition:** Pending execution. Preserve any null, negative, or surprising result as observed; Flow decides whether any later action is warranted.

## Official corrected results

The complete corrected official protocol ran from executable/protocol freeze `598c0677ff7a8c1ed16601dea634f3bb63c6c128` on execution base `45e946fb295b594954542e5f31fd54b9d15ec107`; the authorized launch base remains `f16a676bd60e0f92cbfaee36b54c6145b0d85706`. The invalidated first run was executed from `1a5bc2aecf708288ae55aa3da4529baaa96a4385`; its 1,722,930-byte artifact (`12059a2b9d2e61b25dae0ec708b8c8626a688863c5b01975137bf5c002b23b17`) is preserved separately and excluded from interpretation. It completed all 25 lifetimes and the 768-state matrix, but reversed `U_ONLY_FAIL`/`C_ONLY_FAIL` and omitted the frozen per-cycle `stall_detected_count` readout. The corrected rerun changes no causal mechanism or protocol parameter.

All frozen controls passed: Part A D-054 identity and no-intervention identity; Part B D-053 identity and candidate prefix identity. The five support and 20 allocated fresh-block paired lifetimes completed the 140,000-transition protocol. Across the 25 pairs, organism-facing info remained empty, reward was exactly zero, and there were no invalid-beacon decisions or terminal-spin exhaustion. Corrected artifact SHA-256 is `6a291b6377c95bd1afab9c485a779619f180be16bc5893c5d4c4bdfed1cabaea` (1,725,902 bytes). An independent complete regeneration produced the same SHA-256 and size and was byte-identical (`cmp` PASS).

**Part A (768 frozen states).** Paired outcomes were 640 `DOCKED × DOCKED` and 128 `HORIZON_CENSORED × DOCKED` (U × C). U had 640 docked and 128 wedged; C had 768 docked and zero wedged: 128 rescued, zero harmed. The inset/boundary non-docked cross-tab was U: 48 corners and 80 walls; C: zero in either class. The candidate emitted 224 stall turns. Detector audit: 224 detections, zero missed stalls, maximum preceding boundary scale `1e-12`; 112 scales were zero, 112 positive through `1e-9`, and zero exceeded `1e-9`. The frozen signature is `A_WEDGE_RESOLUTION=ALL`, `A_HARM=NONE`.

**Part B (first RETURN episode).** On support seeds `22053–22057`, paired classes were 4 `BOTH_DOCK` and 1 `U_ONLY_FAIL`; on allocated block `22550–22569`, they were 11 `BOTH_DOCK` and 9 `U_ONLY_FAIL`. `BOTH_FAIL`, `C_ONLY_FAIL`, and `NO_RETURN` were zero in both blocks. Under the frozen definitions, `U_ONLY_FAIL` means U failed while C docked (rescue); thus the descriptive counts are one support rescue and nine block rescues, with no harms. Arm C recorded 17 stall detections/turns across the 25 lifetimes.

**Provenance limits and interpretation.** Before the first official run, the candidate's first two decisions were observed on Part A state `bottom_wall-i0.00-p0.10-0.00-h14`; 767/768 states were unexposed. The state remains in the matrix, and no parameter was adapted from that observation. The `B_FRESH` block `22550–22569` was predeclared and frozen before its first execution, but was already executed and observed in the invalidated `1a5bc2ae` run. Its corrected rerun is a correction rerun of a previously observed predeclared out-of-support block, not a second prospective holdout; “fresh” names the originally allocated block, not untouched status. No mechanism, constant, stall predicate or gating, seed, matrix, horizon, stop rule, controller semantics, or interpretation rule was tuned from any observation. These are descriptive Development results only, with no confirmatory or untouched-evidence claim.
