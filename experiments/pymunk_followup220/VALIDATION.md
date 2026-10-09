# Pymunk #220 validation and execution record

## Worker, worktree, and provenance

- Assigned worker role: fresh GPT-6 Luna implementation worker for issue #220.
- Runtime identity exposed to the worker: OpenAI Codex agent based on GPT-6;
  Codex runtime version `0.160.0`. The exact serving model revision and
  provider-routing identifier are unavailable. The runtime exposed session and
  thread ID `01a12116-be46-76f2-873a-c24795f9421f` for both
  `CODEX_SESSION_ID` and `CODEX_THREAD_ID`. The worker PID is not exposed by the
  available runtime API. The production pytest process used tool session
  `21175`; that process completed and is not the worker session.
- Worktree: `/private/tmp/aweform-pymunk220-corrected-empty-space-calibration`.
- Authorized branch: `codex/pymunk220-corrected-empty-space-calibration`.
- Authorized base: `ce4f4943f6d8fcd84c723a151b15178f3856e098`.
- Protocol freeze: `7044e37b1259698f9277b9eae2224da64ba63a64`.
- Result-free executable/test-plan freeze and measured-run SHA:
  `744afa5596db89afb1d6bb80685698ea254b800c`.
- Final record PR SHA is recorded by the top-level `[LUNA-HANDOFF]` on the
  issue #220 implementation/results PR. It is not self-referenced in the
  commit that contains this file.

## Runtime identity

- Python: `3.14.7 (main, Aug 14 2026, 15:24:10) [Clang 22.1.3 ]`.
- Platform: macOS `26.6.2`, Darwin `25.6.0`, native `arm64`; Rosetta: `False`.
- Pymunk: `7.2.0`; Chipmunk: `2.0.1-ade7ed72849e60289eefb7a41e79ae6322fefaf3`.
- Python executable:
  `/private/tmp/aweform-pymunk220-corrected-empty-space-calibration/.venv/bin/python3`.
- Pymunk module:
  `/private/tmp/aweform-pymunk220-corrected-empty-space-calibration/.venv/lib/python3.14/site-packages/pymunk/__init__.py`.
- Locked wheel:
  `/private/tmp/pymunk220-wheelhouse/pymunk-7.2.0-cp314-cp314-macosx_11_0_arm64.whl`,
  350532 bytes, SHA-256
  `497c4a919fc7f03882cb9796b132ab3b5fcc4c4af9ead08e9631b6a9fb2da29c`;
  exact `uv.lock` match: `True`.
- `uv`: `0.12.5 (210d1f678 2026-08-14 aarch64-apple-darwin)`.
- `uv.lock` SHA-256:
  `512f300c3850f348f0690c0f4c3164a403c72c54f7fd97fb8fd43d8b9fdaf148`.
- Result JSON SHA-256:
  `8ff9b3d6209b4aac7f9df5a452126bb41f5c53c1a1b7043ec370d7e96e5c32b0`.
- Results Markdown SHA-256 after correcting its reproduction-mode note:
  `2aea9f893b474a3b4060d92642be2379a73843a21e003ad236b1a0119dcffd16`.

The initial `uv run` attempt stopped before runner startup because the sandbox
denied access to the existing user-level uv cache. No candidate ran in that
attempt. Retrying the same command with the required cache access succeeded;
the executable freeze and measurement code were unchanged. After generation,
the results Markdown's preflight note was clarified to describe its already
implemented `--replay-frozen` reproduction path. No measurement, gate, or
candidate record was changed; the detached checksums below cover the committed
Markdown bytes.

## Measured candidate outcomes

The frozen runner exited `0`, with overall verdict `STOP`. C0 was read from
historical files only; its executable was not rerun. The preservation gate
passed, including all ten historical Tranche 1 file hashes, production source
and tests, unchanged dependency files, and optional-only Pymunk placement.

| Candidate | Matrix cases | Case failures | Maximum position error | Maximum unwrapped yaw error | Candidate gates |
|---|---:|---:|---:|---:|---|
| `C0_T1_HISTORICAL` | 92 recorded | 24 | `0.00011400040559442288 m` | not recomputed | historical FAIL: calibration, known-vectors, symmetry |
| `C1_MIDPOINT_NOMINAL_SPEED` | 216 | 0 | `1.4922674449837919e-7 m` | `3.9968028886505635e-15 rad` | 8 PASS / 0 FAIL |
| `C2_MIDPOINT_ARC_AVERAGE` | 216 | 0 | `4.4026752318055749e-17 m` | `3.9968028886505635e-15 rad` | 8 PASS / 0 FAIL |

Each new candidate passed action timing/clipping, free-space calibration,
independent known vectors, body-frame symmetry, 10-vs-20 microstep convergence,
headless runtime, reset repeatability, and encoder quantization. Each had 10
independently reset 1,000-command traces with byte-identical canonical JSON:

- C1 trace SHA-256:
  `e315a5f1c9dd8dcce10dc67cda0213dfd51ec449a25a1977ac60761d00272adc`.
- C2 trace SHA-256:
  `56f478b43865048084f9629325240f31c2a0efdd472555777c701070882ee34a`.

The C0 test suite was run separately and reports `87 passed, 26 xfailed`; the
strict xfails are intentional and prominent. This does not rewrite C0's frozen
24 calibration failures or resolve the old reporting discrepancy (`RESULTS.md`
reported `88 passed / 25 failed`, while the historical PR description reported
`87 passed / 26 xfailed`). That discrepancy remains `UNKNOWN_UNRECONCILED`.

The result JSON contains every case, requested/clipped command, analytic and
engine endpoint, error, check, gate status and threshold, runtime manifest,
repeatability hash, and historical C0 record. `SHA256SUMS` hashes the JSON and
Markdown separately; it intentionally does not self-hash.

## Validation commands and outcomes

All commands below ran after the executable freeze. The implementation was
not edited after the candidate run.

| Check | Command | Outcome |
|---|---|---|
| Frozen run | `PYMUNK_WHEEL_PATH=... uv run --frozen --group pymunk-probe python -m experiments.pymunk_followup220.run_diagnostic --output-dir /private/tmp/pymunk220-run` | exit 0; both candidates and global preservation gate PASS; verdict STOP |
| New isolated test plan | `PYMUNK_WHEEL_PATH=... uv run --frozen --group pymunk-probe pytest -q experiments/pymunk_followup220/test_followup.py` | 9 passed |
| Historical Tranche 1 tests | `PYMUNK_WHEEL_PATH=... uv run --frozen --group pymunk-probe pytest -q experiments/pymunk_tranche1/test_probe.py` | 87 passed, 26 strict xfailed |
| Production tests | `PYMUNK_WHEEL_PATH=... uv run --frozen --group pymunk-probe pytest -q tests` | 1211 passed, 8 warnings, 0 failures, 367.52 s |
| Full Ruff | `.venv/bin/ruff check .` | pass |
| Source-only strict mypy | `.venv/bin/mypy src --strict` | pass; 89 source files |
| Experimental-module strict mypy | `.venv/bin/mypy --strict experiments/pymunk_followup220` | pass; 5 files |
| Production compile | `.venv/bin/python -m compileall -q src` | pass |
| Production import | `.venv/bin/python -c 'import aweform'` | exit 0; Matplotlib used a temporary cache because its default cache directory was not writable |
| GitHub Actions | `Reproducibility / checks` | exact PR-head result is recorded in the top-level `[LUNA-HANDOFF]` after the workflow starts; this local record does not treat pending checks as PASS |

The checked-in GitHub workflow runs production `src` compilation/import, default
`pytest -q`, `ruff check .`, and source-only `mypy src --strict`. Its default
dependency sync omits the optional Pymunk group, so green CI does not imply
Tranche 1's historical calibration passed. The optional new and historical
probe tests above were run explicitly in the locked Pymunk group.

## Interpretation boundary

- **VERIFIED:** the exact fixture, two frozen update candidates, fixed empty-
  space commands, measured runtime, recorded gates, and preserved C0 artifacts.
- **INFERENCE:** midpoint arc-averaged updates produced a smaller numerical
  residual than midpoint nominal-speed updates in this empty-space fixture.
- **UNKNOWN:** physical actuator fidelity, wheel traction, contacts/collisions,
  hardware behavior, performance in another runtime/platform, and whether any
  later contact experiment is warranted.

Verdict: **STOP**. No candidate is selected for production; no contact tranche,
room, docking, migration, D/EXP identifier, or successor work is authorized.
