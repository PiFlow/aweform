# Isolated direct-Pymunk Tranche 1 calibration prototype

Refs #217

## Scope and provenance

- Authorized base: `fd68c46d2cd75c46dd0eb824b8360f36f1de6cf8` (origin/main was this SHA at task start).
- Protocol of record: `89de47de86aea43d30e7dc5147c51ed5d1263b1d` (`docs/pymunk-tranche1-protocol.md`). It was committed before implementation or gate evaluation. It had been initially committed as `96d0012fff375f9f653ad9f0664a0143a7963b97` and amended 80 seconds later; the sole amendment replaced an impossible self-referential in-JSON artifact hash with detached `SHA256SUMS` hashes. The earlier progress status reporting `96d0012f` is superseded by `89de47d`.
- Result-producing executable SHA: `2ba46e1dd2ab3e812ab2afaa5791521b8c48ae24`.
- Result artifacts: `experiments/pymunk_tranche1/results.json` — SHA-256 `4a0a0c5c1bef6602553971a9745274c649c56a70e394cde285e5cbf3d6f428e2`; `experiments/pymunk_tranche1/RESULTS.md` — SHA-256 `f8310ee8b7f1b26567d891b4bc7f2e0391d15030b4620209aa325ef105a9d715`; the original RESULTS.md (SHA-256 `f8310ee8…a9d715`) is preserved as `RESULTS.original.md`; all are listed in `experiments/pymunk_tranche1/SHA256SUMS`.
- `experiments/pymunk_tranche1/ADDENDUM.md` is explicitly post-result analysis, not a protocol revision or part of the acceptance record.

## Frozen per-gate outcome

| Gate | Result |
|---|---|
| Headless/runtime | PASS |
| Action/timing | PASS |
| Free-space calibration | **FAIL** |
| Known vectors | **FAIL** |
| Symmetry | **FAIL** |
| Microstep convergence | PASS |
| Reset repeatability | PASS |
| Encoder quantization | PASS |

The frozen protocol outcome is not a pass. All 24 case-level free-space failures are unequal-wheel arc or one-wheel cases: max position error `0.00011400040559442288 m`, with yaw error remaining at rounding level. The known-vector gate is recorded FAIL although all 48 individual ZERO/FORWARD/opposed-wheel vector cases passed (maximum position error `6.938893903907228e-18 m`, maximum yaw error `1.7763568394002505e-15 rad`), because the runner made that aggregate gate conditional on all free-space cases passing. That FAIL stands as executed.

The frozen symmetry oracle's swapped-wheel position comparison is wrong: swapping the wheel pair reflects an asymmetric path across the initial heading axis rather than preserving the same world endpoint. Issue #217 requires swapped-wheel yaw mirroring. The raw unmirrored endpoint difference was `0.0015398709610861183 m`; reflecting the recorded endpoints arithmetically gives maximum discrepancy `2.168404344971009e-19 m` across 12 cases. The frozen symmetry FAIL stands; this is a protocol-oracle defect, not engine evidence.

**INFERENCE:** curvature-dependent position residual with near-zero yaw error is consistent with the frozen actuator's start-of-microstep body-heading velocity direction producing a first-order chord approximation. It is not an independently isolated engine-integrator result. No endpoint pose was overwritten, and no acceptance thresholds/oracles/update order were changed after execution.

## Runtime and reproduction

- Native Apple Silicon `arm64`, Rosetta: false; macOS `26.6.2` (`25G83`).
- `uname -a`: `Darwin MacBookPro 25.6.0 Darwin Kernel Version 25.6.0: Fri Jul 31 19:18:49 PDT 2026; root:xnu-12377.161.14~5/RELEASE_ARM64_T6000 arm64 arm`.
- Python `3.14.7 (main, Aug 14 2026, 15:24:10) [Clang 22.1.3 ]`; uv `0.12.5`.
- Pymunk `7.2.0`; Munk engine `2.0.1-ade7ed72849e60289eefb7a41e79ae6322fef3`.
- Installed wheel `pymunk-7.2.0-cp314-cp314-macosx_11_0_arm64.whl`, SHA-256 `497c4a919fc7f03882cb9796b132ab3b5fcc4c4af9ead08e9631b6a9fb2da29c`; uv.lock SHA-256 `512f300c3850f348f0690c0f4c3164a403c72c54f7fd97fb8fd43d8b9fdaf148`.

Reproduction commands:

```sh
uv sync --python 3.14.7 --group pymunk-probe
uv run --python 3.14.7 pytest -q
PYMUNK_WHEEL_PATH=/path/to/pymunk-7.2.0-cp314-cp314-macosx_11_0_arm64.whl uv run --python 3.14.7 python -m experiments.pymunk_tranche1.run_calibration
uv run --python 3.14.7 ruff check .
uv run --python 3.14.7 mypy src --strict
```

The normal existing suite is also checked with `uv sync --python 3.14.7 --group dev --no-group pymunk-probe`, then `uv run --python 3.14.7 pytest -q`; it passed with 1211 passed / 1 skipped (8 warnings). With the optional group synced, root pytest passed with 1298 passed / 26 xfailed (7 warnings). `pytest.importorskip("pymunk")` skips the isolated test module when the optional dependency is absent. The probe test's strict xfails preserve the failed frozen cases and gate outcome in CI. The frozen experiment runner has two mypy diagnostics; they were intentionally left unfixed to preserve executable provenance. A broader `mypy src tests` run reports 658 diagnostics across 67 unchanged test files; the repository CI check `mypy src --strict` passes.

## Verification and claims

**VERIFIED**

- On the specified native MacBook/Python/Pymunk stack, headless operation, action/timing, 10-vs-20-microstep convergence, repeated 1,000-action trace identity, and the separated encoder quantization checks passed their frozen gates.
- The direct Pymunk body was stepped by `Space.step`; no controller or organism was routed through it.
- Production dependency declarations and `src/aweform`/existing tests are unchanged from the authorized base. Pymunk is only in optional group `pymunk-probe`; no Pygame or RoboSim dependency/import was added.
- Repository checks: `ruff check .` PASS; repository CI `mypy src --strict` PASS (89 source files); existing root pytest suite PASS with and without the optional Pymunk group (see CI checks for exact counts). The isolated pytest suite retains expected strict xfails for the frozen failures.

**INFERENCE**

- The asymmetric-arc position residual is consistent with the declared first-order actuator/update discretization. A revised candidate may warrant a new, separately authorized protocol with a corrected wheel-swap oracle and a newly frozen update order.

**UNKNOWN / NEEDS TESTING**

- Collision-engineering savings, room/contact behavior, hardware fidelity, and any production integration are untested. This empty-space result cannot establish them.
- Native Apple Silicon was tested only on the pinned stack. Trace identity does not establish cross-platform or universal bitwise determinism. Numerical bounds and all failures are in the frozen artifacts.

## Disclosures, limitations, and decision

The earlier stopped attempt is not reused. Its only disclosed information is an unverified prior observation: unequal-wheel arcs and one-wheel cases were reported failing while seven other gates were reported passing. It is not acceptance evidence and did not relax any gate.

Implementation worker: **Pi `openai-codex/gpt-6-luna`**. Supervising second mate: **Claude Code `claude-opus-5-5`** from task intake through pre-validation analysis/instructions; **Claude Code `claude-sonnet-5-5`** from approximately `2026-10-08T14:29Z` (2026-10-09 00:29 AEST) through remaining validation/PR delivery. The change was made on the captain's instruction at about `2026-10-08T14:29Z`; issue #217 had named Opus 5.5 for the role, and the Opus-attributed analysis and the Sonnet-attributed delivery are labelled separately. Supervisor verification is not an independent review of record under ADR 0013. Any required independent review must be completed against the exact PR HEAD; no implementation or supervisor summary substitutes for it.

**Recommendation: revise the candidate, but only after separate authorization.** Tranche 1 did not pass the frozen protocol. Any actuator/update-order revision or corrected symmetry oracle needs a new protocol frozen before execution. No migration, Tranche 2, organism study, or successor D-number is authorized by this PR. D-060 remains untouched. No merge or scope expansion is requested.

RESULTS.md provenance: the original RESULTS.md lives at commit `b72c79a` (SHA-256 `f8310ee8b7f1b26567d891b4bc7f2e0391d15030b4620209aa325ef105a9d715`, preserved byte-identically as `RESULTS.original.md`); the revised RESULTS.md lives at the commit that introduces `RESULTS.original.md` (SHA-256 `3b74666271da3e4bcc3db1d8545b247eedecad951502ec02e8c573726a69f169`). `results.json` SHA-256 `4a0a0c5c1bef6602553971a9745274c649c56a70e394cde285e5cbf3d6f428e2` is unchanged, and all executed gate outcomes are unchanged. The exact SHA of the revised commit will be added after the pipeline's final push.
