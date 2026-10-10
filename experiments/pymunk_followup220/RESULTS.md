# Pymunk #220 corrected empty-space calibration results

- Authorized base SHA: `ce4f4943f6d8fcd84c723a151b15178f3856e098`
- Protocol SHA: `7044e37b1259698f9277b9eae2224da64ba63a64`
- Result-free executable/run SHA: `744afa5596db89afb1d6bb80685698ea254b800c`
- Scope: isolated, headless empty-space engineering diagnostic; no organism, production, or contact run.
- Runtime: Python `3.14.7 (main, Aug 14 2026, 15:24:10) [Clang 22.1.3 ]`, Pymunk `7.2.0`, Chipmunk `2.0.1-ade7ed72849e60289eefb7a41e79ae6322fefaf3`.
- Platform: `Darwin Flows-M1-pro.local 25.6.0 Darwin Kernel Version 25.6.0: Fri Jul 31 19:18:49 PDT 2026; root:xnu-12377.161.14~5/RELEASE_ARM64_T6000 arm64 arm`; architecture `arm64`; native arm64 `True`; Rosetta `False`.
- Wheel: `/private/tmp/pymunk220-wheelhouse/pymunk-7.2.0-cp314-cp314-macosx_11_0_arm64.whl`; SHA-256 `497c4a919fc7f03882cb9796b132ab3b5fcc4c4af9ead08e9631b6a9fb2da29c`; lock match `True`.
- uv: `uv 0.12.5 (210d1f678 2026-08-14 aarch64-apple-darwin)`; `uv.lock` SHA-256 `512f300c3850f348f0690c0f4c3164a403c72c54f7fd97fb8fd43d8b9fdaf148`.
- `results.json` SHA-256: `8ff9b3d6209b4aac7f9df5a452126bb41f5c53c1a1b7043ec370d7e96e5c32b0`.

## Candidate comparison

| Candidate | Role | Cases | Case FAIL | Maximum position error (m) | Maximum yaw error (rad) | Result |
|---|---|---:|---:|---:|---:|---|
| C0_T1_HISTORICAL | Recorded-only immutable comparator | 92 | 24 | 0.00011400040559442288 | not recomputed | historical FAIL preserved |
| C1_MIDPOINT_NOMINAL_SPEED | New fixed candidate | 216 | 0 | 1.4922674449837919e-07 | 3.9968028886505635e-15 | PASS |
| C2_MIDPOINT_ARC_AVERAGE | New fixed candidate | 216 | 0 | 4.4026752318055749e-17 | 3.9968028886505635e-15 | PASS |

C0 was not re-executed. Its three failed gates, 24 failed position cases, original known-vectors aggregate FAIL, and erroneous unreflected wheel-swap comparison remain historical.

## Frozen gate results

| Global gate | PASS | Tranche 1 frozen hashes unchanged; production src/tests, pyproject.toml, and uv.lock byte-identical to base; Pymunk only in optional pymunk-probe |
|---|---|---|

### C1_MIDPOINT_NOMINAL_SPEED

| Gate | Result | Frozen criterion |
|---|---|---|
| headless-runtime | PASS | Python 3.14.7; Pymunk 7.2.0 and locked native arm64 wheel; no Pygame/GUI/event/sleep/wall-clock/RNG coupling |
| action-timing | PASS | accepted command: exact N engine steps and 0.1 s; independent clipping <=1e-12 rad; malformed/non-finite inputs reject before steps |
| free-space-calibration | PASS | all 216 N=10/N=20 base cells: position <=1e-5 m and unwrapped yaw <=1e-5 rad |
| known-vectors | PASS | dedicated full forward, both full spins, and zero: position/yaw <=1e-5 in declared units; independent of free-space gate |
| symmetry | PASS | reversal, wheel-swap body-frame reflection/opposite yaw, rotated heading, and spin-centre errors <=1e-5 m/rad as applicable |
| microstep-convergence | PASS | all 108 paired base cells: N=10 vs N=20 position <=1e-4 m and yaw <=1e-4 rad |
| reset-repeatability | PASS | 10 independently reset 1000-command traces have byte-identical canonical JSON bytes and equal SHA-256 |
| encoder-quantization | PASS | six q=pi/180 half-quantum below/above/exact cases round nearest; exact ties away from zero |
Individual base matrix: 216 cases; 216 PASS / 0 FAIL.
Repeatability: PASS; 10 resets x 1000 commands; trace SHA-256 `e315a5f1c9dd8dcce10dc67cda0213dfd51ec449a25a1977ac60761d00272adc`.

### C2_MIDPOINT_ARC_AVERAGE

| Gate | Result | Frozen criterion |
|---|---|---|
| headless-runtime | PASS | Python 3.14.7; Pymunk 7.2.0 and locked native arm64 wheel; no Pygame/GUI/event/sleep/wall-clock/RNG coupling |
| action-timing | PASS | accepted command: exact N engine steps and 0.1 s; independent clipping <=1e-12 rad; malformed/non-finite inputs reject before steps |
| free-space-calibration | PASS | all 216 N=10/N=20 base cells: position <=1e-5 m and unwrapped yaw <=1e-5 rad |
| known-vectors | PASS | dedicated full forward, both full spins, and zero: position/yaw <=1e-5 in declared units; independent of free-space gate |
| symmetry | PASS | reversal, wheel-swap body-frame reflection/opposite yaw, rotated heading, and spin-centre errors <=1e-5 m/rad as applicable |
| microstep-convergence | PASS | all 108 paired base cells: N=10 vs N=20 position <=1e-4 m and yaw <=1e-4 rad |
| reset-repeatability | PASS | 10 independently reset 1000-command traces have byte-identical canonical JSON bytes and equal SHA-256 |
| encoder-quantization | PASS | six q=pi/180 half-quantum below/above/exact cases round nearest; exact ties away from zero |
Individual base matrix: 216 cases; 216 PASS / 0 FAIL.
Repeatability: PASS; 10 resets x 1000 commands; trace SHA-256 `56f478b43865048084f9629325240f31c2a0efdd472555777c701070882ee34a`.

## Independent vector and symmetry definitions

Analytic position errors are Euclidean norms in metres; yaw errors are absolute unwrapped differences in radians. Wheel exchange is checked in the initial body frame: forward component preserved, lateral component negated, yaw increment negated. The known-vector gate uses only its dedicated forward/spin/zero measurements and is independent of the global free-space gate.

## Claims and limitations

- **VERIFIED:** only the two declared kinematic update candidates, listed fixed commands, pinned runtime, and frozen numerical gates.
- **INFERENCE:** centered velocity updates change the numerical actuator/engine coupling examined here; no physical motor, traction, collision, or contact model was tested.
- **UNKNOWN:** hardware fidelity, collision/contact behavior, engineering savings, other platforms, and production performance.

## Verdict: STOP

No contact/room work, migration, D/EXP record, or successor task is authorized. Passing empty-space calibration alone does not establish that a later contact tranche is warranted.

## Reproduction

```sh
git worktree add --detach /tmp/pymunk220-reproduction-744afa5596db 744afa5596db89afb1d6bb80685698ea254b800c
cd /tmp/pymunk220-reproduction-744afa5596db
mkdir -p /private/tmp/pymunk220-wheelhouse
curl --fail --location https://files.pythonhosted.org/packages/6d/e7/c36c2df4582bd7b515d49f91e171ef841dc1ae038e50c3faf412157b4d12/pymunk-7.2.0-cp314-cp314-macosx_11_0_arm64.whl --output /private/tmp/pymunk220-wheelhouse/pymunk-7.2.0-cp314-cp314-macosx_11_0_arm64.whl
printf '%s  %s\n' 497c4a919fc7f03882cb9796b132ab3b5fcc4c4af9ead08e9631b6a9fb2da29c /private/tmp/pymunk220-wheelhouse/pymunk-7.2.0-cp314-cp314-macosx_11_0_arm64.whl | shasum -a 256 -c -
uv sync --frozen --python 3.14.7 --group pymunk-probe
PYMUNK_WHEEL_PATH=/private/tmp/pymunk220-wheelhouse/pymunk-7.2.0-cp314-cp314-macosx_11_0_arm64.whl uv run --frozen --group pymunk-probe python -m experiments.pymunk_followup220.run_diagnostic --replay-frozen --output-dir /tmp/pymunk220-reproduction-744afa5596db-results
PYMUNK_WHEEL_PATH=/private/tmp/pymunk220-wheelhouse/pymunk-7.2.0-cp314-cp314-macosx_11_0_arm64.whl uv run --frozen --group pymunk-probe pytest -q experiments/pymunk_followup220/test_followup.py
```

First execution requires a clean checkout at the pushed authorized-branch tip and unchanged `origin/main`. The reproduction command uses `--replay-frozen` from a clean detached worktree at the recorded executable SHA, which must remain reachable from the pushed authorized branch; `origin/main` must still equal the authorized base. `PYMUNK_WHEEL_PATH` must name the exact arm64 wheel in `uv.lock`. All per-case rows, checks, trace hashes, and detached checksums are in adjacent artifacts.

## Artifacts

- `experiments/pymunk_followup220/results.json` — complete candidate, case, and gate records.
- `experiments/pymunk_followup220/SHA256SUMS` — detached hashes for JSON,
  Markdown, and the validation record.
- `experiments/pymunk_followup220/VALIDATION.md` — test, lint, and typing commands/results.
