# POST-RESULT ANALYSIS — not part of the acceptance record

Written after the frozen Tranche 1 results were inspected. This is not a protocol revision, does not alter any frozen result or acceptance condition, and adds no gate result. The original protocol outcome remains: free-space calibration, known-vectors, and symmetry FAIL; the remaining recorded gates PASS. No additional probe, calibration, or diagnostic simulation was run for this addendum. A candidate diagnostic was run under the earlier instruction before it was superseded; it is excluded entirely, and none of its values or conclusions appear here. Numeric cross-checks below use only committed `results.json`, Git history, and arithmetic on those recorded values.

## Protocol and execution provenance

The protocol was first committed as `96d0012fff375f9f653ad9f0664a0143a7963b97` at `2026-10-08T23:56:25+10:00`, then amended to `89de47de86aea43d30e7dc5147c51ed5d1263b1d` at `2026-10-08T23:57:45+10:00` — 80 seconds later, before probe code existed or any gate ran. The only amendment changed the output-contract wording below; `89de47d` is the protocol of record. An earlier progress status reported the first, subsequently amended SHA (`96d0012f`).

```diff
-`artifacts` records path and SHA-256 for JSON and Markdown files.
+`artifacts` records the JSON, Markdown, and detached `SHA256SUMS` paths. The detached checksum file contains SHA-256 entries for both JSON and Markdown outputs; this avoids an impossible self-referential hash cycle inside the JSON.
```

The executable/result-producing commit is `2ba46e1dd2ab3e812ab2afaa5791521b8c48ae24`; record-only results were committed later. Frozen protocol and result files remain byte-identical to the recorded versions.

## Known-vectors gate

All 48 individual `ZERO`, `FORWARD`, `SPIN_POSITIVE`, and `SPIN_NEGATIVE` cases passed their case-level position/yaw checks. Across those cases, maximum position error was `6.938893903907228e-18 m`, and maximum yaw error was `1.7763568394002505e-15 rad`. The aggregate `known-vectors` gate is nevertheless `FAIL` in the frozen artifact because `run_calibration.py` additionally requires the complete free-space gate (`cal_ok`) to pass. That is its implementation reading of the protocol wording “subject to the calibration tolerances above.” The aggregate FAIL stands as executed; the case results do not rewrite it.

## Symmetry gate and oracle limitation

The frozen metamorphic oracle says swapping wheel requests “preserves predicted center displacement.” That is physically incorrect for an asymmetric arc: swapping wheels mirrors the path across the initial-heading axis, so lateral displacement changes sign. Issue #217 itself requires only that “swapping wheels mirrors yaw.” The recorded `0.0015398709610861183 m` wheel-swap position discrepancy is the unmirrored comparison made by the frozen gate.

As a **post-hoc arithmetic diagnostic only**, the recorded `ARC_NEGATIVE_YAW` and `ARC_POSITIVE_YAW` endpoints were paired at each of the 12 identical heading/amplitude combinations and reflected about the initial-heading axis. The maximum mirrored-position discrepancy is `2.168404344971009e-19 m` (rounding level). Recorded reversal-position, rotated-displacement, wheel-swap-yaw, and rotated-heading errors are respectively `0`, `3.144186300207963e-18 m`, `0`, and `4.440892098500626e-16 rad`. This diagnoses the frozen oracle comparison; it does not alter the executed symmetry FAIL or establish a new acceptance result. The oracle defect is a protocol error, not evidence of an engine defect.

## Free-space failures and causal limit

All 24 case-level free-space failures are unequal-wheel `ARC_*` and `ONE_WHEEL_*` cases. Position error increases with curvature; yaw remains within rounding error (largest overall yaw error `1.7763568394002505e-15 rad`). The maximum position error is `0.00011400040559442288 m`.

**INFERENCE, not independently isolated evidence:** the declared actuator sets world velocity along the body heading at the start of each microstep. Under this update order, the resulting first-order chord approximation can account for the curvature-dependent position residual. The pattern is consistent with actuator/update-order discretization; this result does not isolate Pymunk's engine integrator as the cause. No alternative integration/update order is being evaluated or substituted in this addendum. Any alternative actuator update requires a separately authorized task and a new frozen protocol before execution; it cannot be represented as Tranche 1 acceptance.

## Remaining checks

- The frozen `run_calibration.py` has two mypy diagnostics when checked as an experiment module (gate rendering and final gate-status indexing). They remain unfixed so the executable that produced the result remains unchanged.
- The repository's CI check `mypy src --strict` passed with no issues in 89 source files; this is separate from the two diagnostics in the experiment runner.
- Full root pytest with the optional Pymunk group synced: `1298 passed, 26 xfailed` (7 warnings). Without that optional group: `1211 passed, 1 skipped` (8 warnings); the skip is the import-guarded probe module. Both commands exited 0. The 26 strict xfails are the frozen failed cases/gates; no assertion was removed or weakened.
- Runtime was native Apple Silicon arm64, macOS 26.6.2, Python 3.14.7, Pymunk 7.2.0, Munk 2.0.1. The installed wheel identity and result artifact hashes are in `results.json` and `SHA256SUMS`.

## Recommendation

**Revise the candidate** is the recommendation, not advance or migrate it. Tranche 1 did **not** pass under its frozen protocol. A future candidate would need a corrected wheel-swap oracle and a separately frozen actuator/update-order choice before any new evaluation. Both require separate authorization; this addendum changes neither the failed acceptance outcome nor the task scope. No Tranche 2, organism execution, migration, or successor D-number is authorized here.
