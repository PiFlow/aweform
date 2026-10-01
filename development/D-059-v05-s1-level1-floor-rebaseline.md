# D-059 — V0.5 S1 Level-1 floor re-baseline (result-free candidate)

## Status and scope

This file records the result-free implementation candidate only. **No official D-059 support was executed, no official Part-A trajectory was run, and no result artifact was generated.** The implementation has not been selected as the protocol freeze. This candidate record therefore contains no scientific outcome, acceptance decision, or fabricated measurement.

- **Authorization:** #206 PROPOSAL_VERSION 2, Sol proposal PASS `5932464537`, with the binding seam ruling `5932171938`; latest seed/topology recovery ruling is #206 comment `5941551976`.
- **Frozen controlling brief:** `/private/tmp/aweform-d059-bakeoff.gxVFDv/brief-v3.md`, SHA-256 `2cfcf87fa589becfefb9e5d1bcf56b6bfd8dbca9607c494e10c101cb875aade6`.
- **Authorized base:** `0f4b0ae22564293dd178567c4c745e5903256682`.
- **Lane / claim boundary:** descriptive Development only; no confirmatory or EXP claim, no P mechanism authorization, no D-055 promotion, and no successor work.
- **Implementation:** `src/aweform/d059.py` is the D-059-local runner; `tests/test_d059.py` uses only bounded test-only validation and synthetic inputs; this record and JSON manifest are result-free.
- **Selected freeze SHA:** not yet selected/frozen. The current implementation commit is a bake-off candidate, not permission to execute support.

## Frozen design implemented

The accepted comparison remains unchanged U versus unchanged C on canonical `S1_3M`, diagnostic `S1_1M`, and matched `D045_1M`. Only U first RETURNs on canonical S1_3M enter the primary exact-binomial sample. C is a structural identity control on S1, never a second statistical sample. Part B uses the unchanged seeded D-053 proposal fixture once per decision; Part A uses zero wheel proposals. The controller receives only the existing observation and wheel proposal; reward is checked as exactly zero and organism `info` as exactly empty.

- **Primary:** one first RETURN per seed, seeds `26000–26319`; `H_PRIMARY=140000`, `W_C=2000`; censoring is not a failure and never replaced.
- **Endurance:** one continuous 300,000-decision lifetime for seeds `26000–26059` on each required arm/substrate. The online primary snapshot is passive and immutable; post-boundary continuation of a primary-censored first RETURN and later cycles remain secondary.
- **Primary-only remainder:** seeds `26060–26319`, stopping after the first primary record freezes.
- **Part A:** 1,248 enumerated legal starts per substrate, classified orthogonally for terminal outcome and full-RETURN wall exposure. U and C are run on every state only by the official CLI.
- **Statistics/decision:** one-sided 95% Clopper–Pearson bounds from actual integer `F3,N3`; `P_BRANCH` and `FLOOR_S1_3M` remain separate; 1 m failures produce an explicit diagnostic alert and never enter P.
- **Substrate seam:** the local D-058 factory changes only `episode_horizon`; D-058 source is protected byte-for-byte. Part A uses 2,000, primary-only uses 140,000, and endurance uses 300,000.
- **Artifact design:** streaming per-decision digests, bounded event/tail/episode buffers, deterministic order, canonical float normalization, and sorted aggregation; no raw transition traces, HTML, or visualization are retained. The CLI runs serially in ascending declared order; `--jobs` is accepted for regeneration parity but does not alter execution or artifact bytes.

D-058 remains the accepted endpoint-only kinematic wall-contact idealization. No continuous-contact, force/slip realism, hardware-fidelity, or component-specific causal wall-attribution claim is made.

## Invalidated exposure and operational provenance

The following provenance is retained without reconstructing or interpreting any outcome:

1. Two inherited pre-freeze D-059 launches on the now-retired `23000–23319` allocation were interrupted and invalidated. Their outcomes contribute zero evidence.
2. A pre-freeze Part-A matrix execution is invalidated validation-only exposure. It is not evidence and its outcomes are not reconstructed.
3. Candidate C (GLM-5.3-Flash) was disqualified for a recorded result-free/isolation constraint violation under ruling `5941551976`. Its session is retained only as a boundary-compliance failure; **no code-quality inference is made**.
4. Candidate C exposed the formerly proposed `24000–24319` block and test-only `24320`; both are retired for final D-059 evidence. No outcomes are reconstructed.
5. Prior GPT-6 Luna provider rate-limit failures are recorded separately as an operational availability observation. The existing assigned model/context resumed after provider failure; no substitution was made.

The only forward block is primary `26000–26319`, endurance `26000–26059`, primary-only `26060–26319`, and bounded test-only `26320`. The older blocks, retired allocations, and any other seed must not be executed for this task. The D-045 harness identity controls retain `22053–22057` solely as the frozen control-only block and run only in post-freeze official CLI execution.

## Result-free validation boundary and candidate checks

Candidate tests may enumerate/check the fixed Part-A geometry but do not execute it. All test trajectories require seed `26320`, horizon at most 5,000, initial battery fraction at most 0.21, and a constructed off-matrix state. Synthetic classification, statistics, aggregation, and artifact-writer tests are not D-059 evidence. Full 300,000-decision D-045 harness identity controls are implemented for selected post-freeze execution and are not run by this candidate.

Validation was run under locked CPython 3.14.7 with `PYTHONHASHSEED=0`:

- Full repository `pytest -q`: **1187 passed**, with 8 Matplotlib animation-lifetime warnings from visualization tests.
- Targeted D-059 suite: **11 passed**; its only trajectories used test-only seed `26320`, off-matrix states, horizon 500, and battery fraction 0.20.
- `ruff check .`: PASS.
- `ruff format --check src/aweform/d059.py tests/test_d059.py`: PASS.
- `mypy src --strict`: PASS; `mypy tests/test_d059.py --strict`: PASS.
- `python -m compileall -q src` and `import aweform`: PASS.
- A repository-wide `ruff format --check src tests` was also attempted; it reports existing formatting drift in unchanged, out-of-scope files (55 under `src`, 102 across `src` and `tests`). Those files were not reformatted because the frozen diff permits exactly five paths; changed D-059 files pass format check.

These are code-validation results only. **No official support seeds `26000–26319`, retired blocks `23000–23319` / `24000–24319`, test-only seeds `23320` / `24320`, official Part-A trajectory, full D-045 harness identity control, official CLI, or D-059 scientific result was executed or generated by this candidate.**

## Post-selection freeze, control, and execution commands

These are instructions for First Mate/Flow after candidate selection; **they were not executed by this candidate**. First Mate must first re-check the exact current repository and GitHub issue/PR/commit exposure/reservation evidence for `26000–26319` and `26320`. Any new collision or exposure stops for a new seed ruling. Archive the full re-check and compute its SHA-256 for the required CLI argument.

```bash
# In the selected, exact-base checkout, after the external seed/exposure re-check:
git rev-parse HEAD
git status --short
rg -n '26000|26320|23000|23320|24000|24320' src tests development
# Search current repository code, then GitHub issues/PRs, commits, and code.
# Archive all results outside the repository; no allocation can be substituted.
rg -n '26000|26320' src tests development > /tmp/d059-local-search.txt
gh api search/issues -f q='repo:PiFlow/aweform 26000' > /tmp/d059-issues-26000.json
gh api search/issues -f q='repo:PiFlow/aweform 26320' > /tmp/d059-issues-26320.json
gh api search/commits -f q='repo:PiFlow/aweform 26000' > /tmp/d059-commits-26000.json
gh api search/commits -f q='repo:PiFlow/aweform 26320' > /tmp/d059-commits-26320.json
gh api search/code -f q='repo:PiFlow/aweform 26000' > /tmp/d059-code-26000.json
gh api search/code -f q='repo:PiFlow/aweform 26320' > /tmp/d059-code-26320.json
tar -cf /tmp/d059-reservation-recheck.tar -C /tmp \
  d059-local-search.txt d059-issues-26000.json d059-issues-26320.json \
  d059-commits-26000.json d059-commits-26320.json \
  d059-code-26000.json d059-code-26320.json
export D059_RESERVATION_RECHECK_SHA256="$(shasum -a 256 /tmp/d059-reservation-recheck.tar | awk '{print $1}')"

# Result-free freeze validation, with no official support command:
PYTHONHASHSEED=0 uv run --locked pytest -q
PYTHONHASHSEED=0 uv run --locked ruff check src tests
PYTHONHASHSEED=0 uv run --locked ruff format --check src/aweform/d059.py tests/test_d059.py
PYTHONHASHSEED=0 uv run --locked mypy src --strict

git add src/aweform/d059.py tests/test_d059.py \
  development/D-059-v05-s1-level1-floor-rebaseline.md \
  development/D-059-v05-s1-level1-floor-rebaseline.json development/INDEX.md
git commit -m 'Implement result-free D-059 S1 re-baseline'
git push  # Flow/First Mate only after selection and freeze authorization
```

The selected freeze must be clean, based on the exact authorized base, and contain exactly the five authorized paths. The CLI enforces exact HEAD SHA, clean tree, ancestry/base, five-path scope, all protected source hashes, `PYTHONHASHSEED=0`, and the local horizon seam. The required current external seed-reservation re-check is separately archived and bound by its SHA-256.

```bash
# Official support is CLI-only and is permitted only after selection, freeze,
# push, and every pre-execution STOP control passes:
PYTHONHASHSEED=0 uv run --locked python -m aweform.d059 \
  --output development/D-059-v05-s1-level1-floor-rebaseline.json \
  --executed-commit-sha "$(git rev-parse HEAD)" \
  --reservation-recheck-sha256 "$D059_RESERVATION_RECHECK_SHA256" \
  --jobs 1

# Independent fresh-archive regeneration must use the exact same frozen SHA,
# reservation-recheck SHA, and original runtime value, but a different jobs
# setting. The supplied runtime freezes that nondeterministic field:
TMPDIR=$(mktemp -d)
git archive --format=tar "$FROZEN_SHA" | tar -xf - -C "$TMPDIR"
cd "$TMPDIR"
PYTHONHASHSEED=0 uv run --locked python -m aweform.d059 \
  --output /tmp/d059-independent.json \
  --executed-commit-sha "$FROZEN_SHA" \
  --archive-source-sha "$FROZEN_SHA" \
  --reservation-recheck-sha256 "$D059_RESERVATION_RECHECK_SHA256" \
  --runtime-seconds "$D059_OFFICIAL_RUNTIME_SECONDS" \
  --jobs 2
cmp /path/to/official.json /tmp/d059-independent.json
```

The current committed JSON file is only a result-free protocol manifest with `execution_status=NOT_EXECUTED_RESULT_FREE_IMPLEMENTATION_CANDIDATE`; it is not an official result artifact. No official command above was run.
