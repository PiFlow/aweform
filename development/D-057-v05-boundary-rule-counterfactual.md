# D-057 — V0.5 boundary-rule counterfactual diagnostic

## Frozen protocol (result-free)

- **ID:** D-057; **lane:** ordinary descriptive Development; **authorized base:** `c11022ad167ac7bfb17748bc8e1de3463b1aa61d`.
- **Question:** on already-observed D-054/D-055 wall and corner states and D-056 lifetime RETURN-activation states, does unchanged D-052→D-050 return dock under evaluator-only yaw-free boundary reductions, do those rules harm states canonical R0 docks, and does unchanged D-055 detect stalls?
- **Arms:** U is unchanged D052Controller; C is unchanged D055StallTurnCandidate around a fresh D052Controller. Both receive `(0,0)` proposals; RETURN preempts them.
- **R0:** unchanged canonical D045Env. **R1:** execute clamped wheel deltas and full yaw; if the full endpoint leaves `[0,1]^2`, stop translation at the first boundary intersection along the chord. **R2:** execute clamped wheel deltas and full yaw, then componentwise clamp the full endpoint. R2 is an endpoint-clamped tangential-retention counterfactual, not a physical slide/contact model.
- **Evaluator seam:** R1/R2 instantiate unchanged D045Env with widened `world_min=(-1,-1)`, `world_max=(2,2)`, and the stage horizon. After each step, the D-057 harness reduces only body centre, leaves heading unchanged, and recomputes the observation through `_observation().as_array()`. Post-reduction pose is authoritative for every branch geometry calculation. No module monkeypatching or controller changes.
- **Part A:** all 768 `d054.frozen_cases()` using D-055 Part-A reset semantics (station centre, 20% battery, ambient temperature, false charger latch, zero previous wheel delta), horizon 1,000; 4,608 arm/rule runs.
- **Part B:** unchanged `run_d053_lifetime(seed, horizon=300_000)` sequentially on `22600–22619` and `22053–22057`; retain all RETURN activation states restored from transition `activation-1` (exact x/y/heading/battery; temperature is declared approximate as thermal×80 C), then branch each arm/rule for at most 1,000 transitions. No new seed and no lifetime under R1/R2. Official supports are executable only through the D-057 CLI from the pushed executable/protocol freeze; `_part_a`, `_part_b`, and `run_protocol` refuse direct calls unless the CLI-set official-execution guard is active.
- **Outcomes:** DOCKED, TERMINAL_SPIN_EXHAUSTED, INVALID_BEACON, TERMINATED_*, HORIZON_CENSORED. WEDGED is post-hoc: non-docked, centre within `1e-9 m` of a bound at end, and final-100 centre path ≤`1e-9 m`.
- **STOP controls:** unchanged protected files; R0 compact per-run identity against committed D-055 Part A; widened-bound scale always 1; prefix identity through before R0 first scaling (or full identity if no scale); exact post-reduction pose continuity; off-contact isolation and no stale charge consequence at every changed centre; Part-B D-053 summary identity and U-R0 replay fidelity, C-R0 wedge-state dock/stall-turn identity; reward exactly zero and organism info empty; exact Part-B seed blocks and test-only seed 22620 limits (≤5,000 horizon and ≤0.21 initial battery fraction).
- **Frozen readouts:** per arm/rule outcome and wedge counts and R0 paired cross-tabs; U and C resolution/harm; residual failure anatomy (station distance, wall pinning, reduction count, path and final-100 path, inset×wall/corner); paired docking-transition and actuator-energy differences; C stall detections/turns and trace identity; reduction count by run.
- **Signature:** per R1/R2: A/B U resolution ALL/PARTIAL/NONE; A/B U harm NONE/SOME; C dormancy YES/NO.
- **Interpretation:** `BOUNDARY_RULE_ARTIFACT_SUPPORTED` only if at least one counterfactual has ALL U-resolution and NONE U-harm in both parts. Otherwise `STRONG_ARTIFACT_CRITERION_NOT_MET`; this is not evidence that R0 is non-causal. R1/R2 are not S1 and do not validate physical wall contact or sliding.
- **Artifact:** deterministic `development/D-057-v05-boundary-rule-counterfactual.json`; floats are output-only quantized to 12 decimals, round-half-even, normalize negative zero, reject nonfinite. No per-transition trace or visualization.
- **Pre-freeze exposure:** the initial local tests observed only constructed R1/R2 poses and one permitted R0-only D-054 test case, `bottom_wall-i0.00-p0.10-0.00-h00`, at horizon 20. The onset arithmetic and one constructed seam-feasibility check disclosed in authorized issue #198 are proposal-stage exposure. The first candidate commit `d1d098c5b2aeca920ff11cb003dfc6b60ec30548` was superseded after First Mate pre-run QA and before any official D-057 counterfactual execution.

**Pre-freeze execution-agent exposure disclosure:** The no-mistakes test agent in run `01M3PX1MEPV272JBD42760NQ1Z` executed U-R0-only replays of committed D-056 Arm-U RETURN activation states before the executable/protocol freeze. Evidence is archived under `/Users/flow/.no-mistakes/evidence/01M3PX1MEPV272JBD42760NQ1Z/`. The recorded seed/cycle/activation pairs were: 22600/1/72591 (DOCKED), 22600/2/164123 (DOCKED), 22600/3/256471 (DOCKED); 22601/1/70758 (WEDGED); 22602/1/72935 (WEDGED); 22603/1/75200 (DOCKED), 22603/2/165499 (DOCKED), 22603/3/257730 (DOCKED); 22604/1/72247 (WEDGED); 22605/1/72536 (DOCKED), 22605/2/164750 (WEDGED); 22606/1/72865 (WEDGED); 22607/1/71574 (WEDGED); 22608/1/73769 (WEDGED); 22609/1/71030 (WEDGED); 22610/1/72267 (DOCKED), 22610/2/162684 (WEDGED); and 22611/1/71923 (DOCKED), 22611/2/162372 (DOCKED), 22611/3/254884 (DOCKED). Additional partial sweep output recorded 22615/1/72537 (WEDGED) and 22053/1/71216 (WEDGED); a parallel sweep also repeated 22611 cycles 1–3. The first round-5 sequential sweep completed 20/20 replay windows across seeds 22600–22611. Three parallel U-R0-only sweeps for fresh seeds 22611–22619 and support seeds 22053–22057 were then started and killed by First Mate's abort within seconds; their results were not completely recorded, so every seed in those blocks is treated as potentially exposed under U-R0. Replays with recorded completed output matched the committed D-056 episode class and their declared trace window; the pre-fix attempt on WEDGED episodes compared all 1,000 branch transitions successfully but failed the inclusive-window row-count check, which the frozen `_replay_window_end` correction fixes. No C arm and no R1/R2 branch ran on any official state. Nothing was selected or changed from these canonical-rule replay outputs beyond the already-identified Part-B window-boundary correction; they supply no D-057 counterfactual result.

## Results (official execution from frozen SHA)

- **Executable/protocol freeze:** `31cabf1f3e3b8730728e51bdd618fc215daf6bdf`; no source or protocol code changed after this freeze.
- **Execution environment:** `PYTHONHASHSEED=0` is a declared reproducibility parameter for the official artifact. The official invocation from the clean checkout at freeze `31cabf1f3e3b8730728e51bdd618fc215daf6bdf` was `PYTHONHASHSEED=0 python -m aweform.d057 --output /tmp/d057-v05-boundary-rule-counterfactual-31cabf1f-pyhash0.json --executed-commit-sha 31cabf1f3e3b8730728e51bdd618fc215daf6bdf` (run through the repository's locked `uv` environment). After completion, that external output was copied byte-for-byte to `development/D-057-v05-boundary-rule-counterfactual.json`; the destination SHA-256 was verified against the source as `765132de95f1c21d6ed76e5457baa460e1ba7465367af7d407e648a97ccf5204`.
- **Artifact:** `development/D-057-v05-boundary-rule-counterfactual.json`; 4,562,839 bytes; SHA-256 `765132de95f1c21d6ed76e5457baa460e1ba7465367af7d407e648a97ccf5204`.
- **Hash-seed ordering disclosure:** Two exact-freeze executions without a fixed hash seed produced SHA-256 `a106bf3f5934c79b6f9cf55336f9c2d2134a0c8c2d97d9bbfe7eb595fe162d73` (official CLI) and `69ed3dd139b5f368f888c9a4d1b6f2799f4fa59006c6a49c41874bda40fa8f6d` (independent archive regeneration); `cmp` failed. In frozen `_readouts`, `keys = base.keys() & alt.keys()` iterates a set. Part-A string `case_id` keys therefore have per-process hash-seed-dependent order, which changes the element order in exactly `part_a.aggregates.paired.C_R1.both_docked_transition_delta`, `part_a.aggregates.paired.C_R2.both_docked_transition_delta`, and `part_a.aggregates.paired.C_R2.both_docked_actuator_energy_delta_j`. A parsed comparison established these were permutation-only differences: every per-run value, control, discrete signature, and interpretation was identical. No code change, normalization, or new freeze was made.
- **Seeded byte identity:** With the declared `PYTHONHASHSEED=0`, three executions of the unchanged freeze were byte-identical (`cmp` PASS), all SHA-256 `765132de95f1c21d6ed76e5457baa460e1ba7465367af7d407e648a97ccf5204`: (1) the official CLI from the clean freeze checkout, (2) the worker's regeneration from a fresh `git archive` in `/tmp/d057-archive-repro-31cabf1f.4Oa0aU`, and (3) First Mate's independent archive regeneration. The seeded artifact's per-run records, controls, signature, and interpretation also match both unseeded artifacts; only the three listed aggregate-array orderings differ.

### Control results

Every frozen control passed. Compact control values: `c_r0_wedged_episode_identity=PASS`; `c_r0_wedged_count=18`; `contact_isolation=PASS`; `lifetime_summary_identity=PASS`; `no_detection_trace_identity=PASS`; `no_stale_charge_consequence=PASS`; `pose_continuity=PASS`; `r0_committed_identity=PASS`; `r1_r2_prefix_identity=PASS`; `u_r0_replay_count=50`; `u_r0_replay_fidelity=PASS`; `widened_bounds_inertness=PASS`.

### Outcomes and paired readouts

| Part | Arm/rule | Outcomes | WEDGED | Centre reductions | Resolution | Harm |
|---|---|---|---:|---:|---:|---:|
| A | U/R0 | DOCKED 640; HORIZON_CENSORED 128 | 128 | 0 | baseline | baseline |
| A | U/R1 | DOCKED 768 | 0 | 224 | 128/128 | 0/640 |
| A | U/R2 | DOCKED 768 | 0 | 224 | 128/128 | 0/640 |
| A | C/R0 | DOCKED 768 | 0 | 0 | baseline | baseline |
| A | C/R1 | DOCKED 768 | 0 | 224 | 0/0 | 0/768 |
| A | C/R2 | DOCKED 768 | 0 | 224 | 0/0 | 0/768 |
| B | U/R0 | DOCKED 32; HORIZON_CENSORED 18 | 18 | 0 | baseline | baseline |
| B | U/R1 | DOCKED 50 | 0 | 33 | 18/18 | 0/32 |
| B | U/R2 | DOCKED 50 | 0 | 33 | 18/18 | 0/32 |
| B | C/R0 | DOCKED 50 | 0 | 0 | baseline | baseline |
| B | C/R1 | DOCKED 50 | 0 | 33 | 0/0 | 0/50 |
| B | C/R2 | DOCKED 50 | 0 | 33 | 0/0 | 0/50 |

For C, resolution denominators are zero because C/R0 had no non-docked states; the harm denominators are its R0-docked states. No R1/R2 run was non-docked, so there is no residual counterfactual failure anatomy. D-055 candidate diagnostics were zero for both rules in both parts: `stall_detections=0`, `stall_turns=0`, and `non_pursuit_detections=0` (C remained trace-identical to U when dormant). Full paired cross-tabs, docking-transition and actuator-energy deltas, and per-run records are in the artifact.

**Discrete signature:** `A_U_R1_RESOLUTION=ALL`; `A_U_R1_HARM=NONE`; `A_U_R2_RESOLUTION=ALL`; `A_U_R2_HARM=NONE`; `B_U_R1_RESOLUTION=ALL`; `B_U_R1_HARM=NONE`; `B_U_R2_RESOLUTION=ALL`; `B_U_R2_HARM=NONE`; `C_R1_DORMANT=YES`; `C_R2_DORMANT=YES`.

**Interpretation:** `BOUNDARY_RULE_ARTIFACT_SUPPORTED`. This is descriptive Development evidence on already-observed states. Under the frozen rule, the #196 S1 precondition is met descriptively; D-057 authorizes nothing. R1/R2 are not S1 and validate no physical contact or sliding model. These counts are not rate estimates, and no EXP claim follows. The earlier disclosed pre-freeze U-R0-only exposure and its provenance remain recorded above; it supplies no counterfactual D-057 result.

**surprised_by:** None; the registered expectation was met: both R1 and R2 resolved every U-R0 non-docked case with no harm in Parts A and B, and C remained dormant under both.

**disposition:** CONTINUING.
