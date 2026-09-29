# D-057 — V0.5 boundary-rule counterfactual diagnostic

## Frozen protocol (result-free)

- **ID:** D-057; **lane:** ordinary descriptive Development; **authorized base:** `c11022ad167ac7bfb17748bc8e1de3463b1aa61d`.
- **Question:** on already-observed D-054/D-055 wall and corner states and D-056 lifetime RETURN-activation states, does unchanged D-052→D-050 return dock under evaluator-only yaw-free boundary reductions, do those rules harm states canonical R0 docks, and does unchanged D-055 detect stalls?
- **Arms:** U is unchanged D052Controller; C is unchanged D055StallTurnCandidate around a fresh D052Controller. Both receive `(0,0)` proposals; RETURN preempts them.
- **R0:** unchanged canonical D045Env. **R1:** execute clamped wheel deltas and full yaw; if the full endpoint leaves `[0,1]^2`, stop translation at the first boundary intersection along the chord. **R2:** execute clamped wheel deltas and full yaw, then componentwise clamp the full endpoint. R2 is an endpoint-clamped tangential-retention counterfactual, not a physical slide/contact model.
- **Evaluator seam:** R1/R2 instantiate unchanged D045Env with widened `world_min=(-1,-1)`, `world_max=(2,2)`, and the stage horizon. After each step, the D-057 harness reduces only body centre, leaves heading unchanged, and recomputes the observation through `_observation().as_array()`. Post-reduction pose is authoritative for every branch geometry calculation. No module monkeypatching or controller changes.
- **Part A:** all 768 `d054.frozen_cases()` using D-055 Part-A reset semantics (station centre, 20% battery, ambient temperature, false charger latch, zero previous wheel delta), horizon 1,000; 4,608 arm/rule runs.
- **Part B:** unchanged `run_d053_lifetime(seed, horizon=300_000)` sequentially on `22600–22619` and `22053–22057`; retain all RETURN activation states restored from transition `activation-1` (exact x/y/heading/battery; temperature is declared approximate as thermal×80 C), then branch each arm/rule for at most 1,000 transitions. No new seed and no lifetime under R1/R2.
- **Outcomes:** DOCKED, TERMINAL_SPIN_EXHAUSTED, INVALID_BEACON, TERMINATED_*, HORIZON_CENSORED. WEDGED is post-hoc: non-docked, centre within `1e-9 m` of a bound at end, and final-100 centre path ≤`1e-9 m`.
- **STOP controls:** unchanged protected files; R0 compact per-run identity against committed D-055 Part A; widened-bound scale always 1; prefix identity through before R0 first scaling (or full identity if no scale); exact post-reduction pose continuity; off-contact isolation and no stale charge consequence at every changed centre; Part-B D-053 summary identity and U-R0 replay fidelity, C-R0 wedge-state dock/stall-turn identity; reward exactly zero and organism info empty; exact Part-B seed blocks and test-only seed 22620 limits (≤5,000 horizon and ≤0.21 initial battery fraction).
- **Frozen readouts:** per arm/rule outcome and wedge counts and R0 paired cross-tabs; U and C resolution/harm; residual failure anatomy (station distance, wall pinning, reduction count, path and final-100 path, inset×wall/corner); paired docking-transition and actuator-energy differences; C stall detections/turns and trace identity; reduction count by run.
- **Signature:** per R1/R2: A/B U resolution ALL/PARTIAL/NONE; A/B U harm NONE/SOME; C dormancy YES/NO.
- **Interpretation:** `BOUNDARY_RULE_ARTIFACT_SUPPORTED` only if at least one counterfactual has ALL U-resolution and NONE U-harm in both parts. Otherwise `STRONG_ARTIFACT_CRITERION_NOT_MET`; this is not evidence that R0 is non-causal. R1/R2 are not S1 and do not validate physical wall contact or sliding.
- **Artifact:** deterministic `development/D-057-v05-boundary-rule-counterfactual.json`; floats are output-only quantized to 12 decimals, round-half-even, normalize negative zero, reject nonfinite. No per-transition trace or visualization.
- **Pre-freeze exposure:** no official D-057 state, seed or matrix case was run. Permitted short R0-only unit-test exposure: `bottom_wall-i0.00-p0.10-0.00-h00` at horizon 20. R1/R2 tests use constructed non-official poses only. The onset arithmetic and one constructed seam-feasibility check disclosed in authorized issue #198 are the only proposal-stage exposure.

**surprised_by:** pending official execution.

**disposition:** pending official execution.
