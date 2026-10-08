# Direct-Pymunk Tranche 1 results

- Base SHA: `fd68c46d2cd75c46dd0eb824b8360f36f1de6cf8`
- Protocol SHA: `89de47de86aea43d30e7dc5147c51ed5d1263b1d`
- Executable SHA: `2ba46e1dd2ab3e812ab2afaa5791521b8c48ae24`
- Scope: isolated empty-space calibration; no organism/controller/learner execution.
- Platform: `arm64`; native arm64: `True`; Python `3.14.7 (main, Aug 14 2026, 15:24:10) [Clang 22.1.3 ]`; Pymunk `7.2.0`; Munk `2.0.1-ade7ed72849e60289eefb7a41e79ae6322fefaf3`.

## Frozen gate results

| Gate | Result | Frozen criterion |
|---|---|---|
| headless-runtime | PASS | canonical Python; no Pygame import or graphics/wall-clock coupling |
| action-timing | PASS | one 0.1 s interval/action; clipped shaft deltas within 1e-12 rad; invalid inputs reject without advancement |
| free-space-calibration | FAIL | position <=1e-5 m; yaw <=1e-5 rad; spin-center translation <=1e-5 m |
| known-vectors | FAIL | r*a=0.029059732045705586 m; opposed-wheel yaw +/-pi/10; zero stationary |
| symmetry | FAIL | equal-wheel reversal, wheel-swap yaw mirror, and rotated-heading displacement rotation within calibration tolerances |
| microstep-convergence | PASS | 10 versus 20 steps: position <=0.1 mm and yaw <=1e-4 rad |
| reset-repeatability | PASS | 10 independent 1000-interval fixed schedules have identical canonical trace bytes |
| encoder-quantization | PASS | one-degree nearest quantum; ties away from zero |

Evaluated calibration cases: 92. Repeatability: PASS (10 runs, trace SHA-256 `ae9feaf9469138ef512dd8f44049b9a05b063cb907c6d26781f2a9391d80282e`). The isolated pytest suite reported 88 passed and 25 failed. Those failures are retained; they are consistent with the 24 failed pose cases and the symmetry assertion recorded in JSON.

The largest observed position error was 0.00011400040559442288 m (one-stationary-wheel full command); the largest yaw error was 1.7763568394002505e-15 rad. Unequal-wheel arcs and one-wheel cases miss the frozen 1e-5 m position gate while yaw remains within tolerance. **INFERENCE (cause):** the actuator reorients forward velocity to the body's heading at the beginning of each microstep, and the engine integrates the resulting finite-step chord; this first-order microstep position integration does not reproduce the analytic constant-curvature arc at the frozen 10-step resolution. No endpoint pose was overwritten. No threshold, oracle or update order was changed after these failures.

The symmetry gate also fails its recorded wheel-swap position comparison (0.0015398709610861183 m); its wheel-swap yaw error is 0. The strict comparison is preserved as executed.

## Claims and limitations

- **VERIFIED:** only the listed fixture, fixed commands, pinned runtime and numerical gates in this artifact.
- **INFERENCE:** the isolated direct-Pymunk probe is a plausible bounded candidate for future evaluation; no engineering-savings conclusion follows from this tranche.
- **UNKNOWN / NEEDS TESTING:** collision-engineering savings, contact behavior, hardware fidelity, other platforms and any production integration.
- Pose and velocity are evaluator-only. No controller or organism was routed through Pymunk.
- Ten-run trace identity is specific to this tested stack; it is not cross-platform or universal bitwise determinism. Numerical tolerances are those frozen in the protocol.

## Repository checks and reproduction

- `ruff check .`: PASS.
- `mypy src/aweform` (strict settings): PASS, 89 source files.
- `mypy experiments/pymunk_tranche1` with `MYPYPATH=src`: FAIL, two `object` indexing diagnostics in gate rendering/final gate status. No production source is affected.
- `mypy src tests`: FAIL, 658 existing test-file diagnostics across 67 files; these files are unchanged by this branch. The production-source mypy check above is clean.
- Existing production suite `pytest -q tests`: PASS, 1211 passed (8 warnings).
- Isolated probe suite `pytest -q experiments/pymunk_tranche1/test_probe.py`: FAIL, 88 passed / 25 failed as described above.
- `src/aweform` and `tests` have no changes from the authorized base. `[project].dependencies` remains unchanged; Pymunk is only in the optional `pymunk-probe` group.

Reproduce on the pinned native stack:

```sh
uv sync --python 3.14.7 --group pymunk-probe
uv run --python 3.14.7 pytest -q experiments/pymunk_tranche1/test_probe.py
PYMUNK_WHEEL_PATH=/path/to/pymunk-7.2.0-cp314-cp314-macosx_11_0_arm64.whl uv run --python 3.14.7 python -m experiments.pymunk_tranche1.run_calibration
uv run --python 3.14.7 ruff check .
uv run --python 3.14.7 mypy src/aweform
uv run --python 3.14.7 pytest -q tests
```

Stop after Tranche 1. The measured calibration and symmetry failures make the recommendation **stop / do not advance this candidate**. A passing calibration alone is not grounds for migration; any later tranche needs separate authorization.
