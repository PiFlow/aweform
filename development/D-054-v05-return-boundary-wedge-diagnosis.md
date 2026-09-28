# D-054 — V0.5 return-boundary wedge diagnosis

- **id:** D-054
- **lane:** Development / evaluator-only Level-1 diagnostic
- **authorized_base_sha:** `968d5917215ba974031f555cfbea0350ddb6d74f`
- **disposition:** pending official execution

## Question and classification

Does the unchanged D-050 curved-pursuit law enter an absorbing zero-motion state at the D-053 seed-22053 failure, how often does that occur on a frozen wall/corner-adjacent support, does unchanged D-049 stop-turn-straight do so on the same states, and is the stall visible through existing wheel-delta channels? This is evaluator-side descriptive Development diagnosis only. D-045, D-049, D-050, D-052, and D-053 mechanisms are imported unchanged; no correction or learned capability is implemented.

## Frozen protocol

Part A replays unchanged `run_d053_lifetime(22053)` at its official 140,000-transition, docked-80%-battery protocol and requires D-053 canonical summary equality with the committed seed-22053 record. It locates the first RETURN transition whose remaining trace has exact zero boundary scale, bit-identical pose, and an identical non-zero command, then records geometric anatomy and per-transition battery-drop deviation from the 0.015 J electronics-only load.

Part B restores the post-step physical state immediately before `RETURN_ACTIVATED` from the official trace. Temperature is reconstructed from the normalized thermal channel and is explicitly approximate; the controller and kinematics do not depend on it. The unchanged smooth controller receives a separate D-052 RETURN bookkeeping fidelity replay, with no diagnostic early stop, through onset + 10 (or activation + 999 if no onset); CONTACT, exhausted, and invalid-beacon decisions step their D-052 zero-wheel holds rather than stopping the replay. Pose/heading must match the official trace bit-for-bit, the window must be completed unless the official trace ends first, and a missing official trace row fails the control. Fresh classified smooth and baseline continuations use the Part C stop rules.

Part C uses 48 positions (five along-wall coordinates on each of four walls plus four corners, at 0.00 m and 0.05 m insets) crossed with 16 absolute headings `(2k+1)π/16`, for 768 fixed states. Paired fresh D-045 environments use station `(0.50,0.50)`, 20% battery, ambient temperature, false charger latch, zero previous wheel delta, and a 1,000-transition horizon. Arm S is unchanged `D050SmoothController`; Arm B is unchanged `D050BaselineController`.

The evaluator harness emulates the D-052 RETURN branch externally for both arms: CONTACT first as a zero-wheel CHARGE hold with no step; otherwise, cumulative terminal-spin count `n >= 20` suppresses the newly generated command; otherwise execute the returned command and increment `n` on TERMINAL_SPIN. The twentieth spin executes and the count is never reset. Stop/classification precedence is DOCKED, ABSORBING_ZERO_MOTION, TERMINAL_SPIN_EXHAUSTED, INVALID_BEACON, D-045 termination, then horizon censoring. Wall/corner labels and outward-normal components treat a body centre within 1e-9 m of an arena boundary as touching it, because D-045 bisection can leave wall-pinned centres at sub-nanometre offsets. Evaluator geometry and telemetry are post-hoc only; neither controller receives them. Reward remains `0.0` and organism-facing `info` remains `{}`.

The deterministic JSON contains Part A anatomy and identity control, Part B restoration/fidelity/classified runs, all 1,536 compact Part C arm records, aggregates, and a discrete outcome signature. Artifact floats use output-only exact-binary `Decimal(x).quantize(Decimal('1e-12'), ROUND_HALF_EVEN)`, normalize negative zero, and reject non-finite values. No visualization is produced.

## Validation and provenance

Tests use constructed fixtures and only test-only D-053 seed `22058` with a horizon no greater than 5,000 and initial battery fraction 0.21. Tests do not run the official D-053 seed/protocol or official Part C matrix. Full focused and repository checks are specified by authorized issue #188. The official run and independent byte-identical regeneration must use the pushed clean executable/protocol freeze SHA; after that freeze only this completed record, its JSON artifact, and the one `development/INDEX.md` row may change.

## Results

Pending official execution from the frozen executable/protocol SHA.
