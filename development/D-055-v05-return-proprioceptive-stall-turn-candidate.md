# D-055 — V0.5 RETURN proprioceptive stall-turn candidate

## Frozen protocol (result-free)

- **id:** D-055
- **lane:** Development; paired causal candidate intervention, not a Level-1 promotion or confirmatory claim
- **authorized_base_sha:** `f16a676bd60e0f92cbfaee36b54c6145b0d85706`
- **status:** executable/protocol freeze; official execution is not part of this commit
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

The single deterministic JSON has no transition traces or visualization. Artifact floats use output-only `Decimal(x).quantize(Decimal('1e-12'), ROUND_HALF_EVEN)`, normalize negative zero, and reject non-finite values. Official output and independent byte-identical regeneration must be attributed to the pushed clean executable/protocol freeze SHA. After that freeze only this completed record, its JSON artifact, and one index row may change.

### Validation and claim boundary

This is an exploratory descriptive Development intervention. It does not promote the candidate to `D052Controller` or the constitutive Level-1 floor, change D-045 contact/boundary physics, make an EXP claim, or authorize a successor. Evaluator scale/position/telemetry are post-hoc diagnostics only. The programmed return behaviour remains engineered competence; no learning, consciousness, emotion, subjective experience, or genuine-life claim follows.

**surprised_by:** Pending the frozen official comparison; no candidate pilot is authorized before the executable/protocol freeze.

**disposition:** Pending execution. Preserve any null, negative, or surprising result as observed; Flow decides whether any later action is warranted.
