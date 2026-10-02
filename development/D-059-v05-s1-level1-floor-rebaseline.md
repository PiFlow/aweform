# D-059 — bounded repair of selected raw B (result-free)

## Status, authority, and separation of roles

This is the selected, result-free bounded repair of raw B, **not** a raw-candidate PASS and not an official D-059 result. Raw B was nonconformant before repair and is preserved unchanged at `63ba49d4ce4f10fe4d630248c873b5a1fca27390`. The selected implementation passed exact-HEAD manager QA and the immediate pre-freeze collision/exposure audit. This result-free freeze contains no scientific outcomes or acceptance decision.

- **Repair authorization:** #206 comment `5943123218`; frozen repair brief `/private/tmp/aweform-d059-bakeoff.gxVFDv/repair-brief-b-v1.md`, SHA-256 `fb1d7778e9e7e2f75da2e0f7a5bbf350f182576235dfe70817ba0a506ff878ce`.
- **Unchanged scientific authority:** #206 PROPOSAL_VERSION 2, Sol PASS `5932464537`, seam ruling `5932171938`, and controlling brief-v3 SHA-256 `2cfcf87fa589becfefb9e5d1bcf56b6bfd8dbca9607c494e10c101cb875aade6`.
- **Authorized project base:** `0f4b0ae22564293dd178567c4c745e5903256682`.
- **Repair base:** exact raw B HEAD `63ba49d4ce4f10fe4d630248c873b5a1fca27390`.
- **Repair branch:** `codex/d059-repair-b`.
- **Implementer / reviewer separation:** this is worker-authored repair. Firstmate is the manager/spec owner and QA reviewer; Firstmate did not author source/tests. The initial blinded A/B technical comparison is preserved in `/private/tmp/aweform-d059-bakeoff.gxVFDv/technical-comparison.md`; anonymous axis reviews and model reveal are preserved separately. Raw A remains unchanged as benchmark provenance, and none of its implementation was imported into this repair. Candidate C remains disqualified under #206 ruling `5941551976`; it is neither scored nor ranked. Sol corrected the manager-session label: Firstmate's actual manager session is user-requested GPT-6.1 Sol/Codex. Manager/reviewer separation remains binding.
- **Bake-off decision:** raw A (DeepSeek V4.1 Flash) and raw B (GPT-6 Luna) both failed conformance and neither raw commit was eligible. B was selected only as the repair base because it had more complete historical D-056 and archive/execution scaffolding; it was not selected for raw correctness or model superiority. The sole GPT-6 Luna repair at `7f940a222618e4b5f8eb48c235c3419dca9197d4` closes the reproduced attribution/identity defects and passes bounded exact-HEAD manager QA. The repaired B is selected for the one D-059 result-free freeze. C (GLM-5.3-Flash) was disqualified for prohibited exposure and source access; no code-quality conclusion is drawn. This single task and the two eligible candidate attempts support no general model ranking. Provider limits, context recovery, and elapsed time are operational provenance, not a quality score.
- **Selected freeze SHA:** assigned by the result-free freeze commit below; it is the only source SHA permitted for official execution and independent regeneration. No D-059 support execution has yet occurred.

## Bake-off comparison and selection

The three workers received the same base and frozen implementation brief through Pi → OpenCode Go. C is excluded from candidate comparison under ruling `5941551976`. The blinded A/B first-pass standards/spec reviews and post-review reveal are retained in the external bake-off archive. Both raw implementations were rejected for correctness/boundary defects despite passing their own tests; test counts were not treated as acceptance evidence.

| Candidate | Raw technical strengths | Raw defects / disposition |
| --- | --- | --- |
| A — DeepSeek V4.1 Flash, `05e13e67441141c351855adbe7a940b2f07ddac4` | More complete pure-statistics/classification and branch tests; deterministic multiprocess work items; both-arm attribution. | Incomplete historic D-056 identity and stop propagation; censor-prefix and archive/seed/hash-seed gates were insufficient. Rejected; not used as repair source. |
| B — GPT-6 Luna, `63ba49d4ce4f10fe4d630248c873b5a1fca27390` | More complete historical D-056 summary/class comparators and concise tests; original archive/execution guards. | Fake copied-prefix/non-feedback evidence; production `FAILED` mapping and missing C attribution; caller-CWD/source provenance, archive proof, and censor controls were insufficient. Rejected as raw implementation; used only as the authorized repair base. |
| C — GLM-5.3-Flash | Not scored. | Disqualified by `5941551976` after prohibited retired-seed exposure and reading unmerged prior candidate material. No restart or model ranking. |

Repair selection is a manager engineering judgment after exact repaired-HEAD QA, not a scientific result or vendor/model benchmark. Root-cause findings, synthetic reproductions, and the complete comparison are preserved in the external archive. Historical exposure of the retired `23000–23319` block remains invalidated provenance and contributes zero evidence; no current official `26000–26319` support trajectory has been run.

Only the five authorized paths are changed. The repair preserves #206's scientific protocol, seed allocation, substrates, U/C, D-053 fixture/RNG, horizons, classifiers, statistics, branch logic, information boundary, and durable safety boundary. No P/D-060/S2/successor work is included.

## B-specific repairs

1. **Actual imported-tree and provenance binding.** Git commands are anchored to the root containing the imported `src/aweform` module, never caller CWD. Normal execution checks that exact module root is the clean Git worktree, HEAD, ancestry, and exact five-path diff. It compares the imported source files/modes against the verified commit's Git tree, and verifies protected file hashes from the authorized base. Literal fresh `git archive` extraction remains supported: the runner requires an external local Git object directory outside the extracted tree, verifies the commit object, ancestry and allowed path diff, and compares every extracted path, mode and Git blob ID against the expected commit tree. An arbitrary SHA string is not treated as executable-source proof. No signing, network access, dependency, or general security framework was added.
2. **Independent primary-prefix audit.** The online primary tracker and a separate streaming `_PrimaryPrefixAudit` independently derive the primary record from the same causal decisions and post-step telemetry. The prefix auditor reads D052 decision/event fields, charging-contact status, termination status, and evaluator-only D045/D058 contact/pose telemetry to calculate outcome, exposure, tail and anatomy. It has separate counters and stop-boundary logic; it neither copies nor selects the online record, retains no raw transition trace, and its output is never passed to the controller or fixture. Every measured U/C primary snapshot is compared with the independent prefix record; mismatch stops before scientific interpretation. A bounded test-only monitor-on/off pair compares full per-decision trajectory digests and read-only final digests of controller, environment, observation and fixture RNG/phase state. The monitor/control performs no writes and does not affect action selection, state, RNG, reward or `info`.
3. **Production failure mapping and censoring.** The production common-outcome mapper emits `FAIL`, matching McNemar's failure mapping. Censored pairs remain explicitly `CENSORED` and are excluded from the exact McNemar comparable-pair count; counts and p-values are reported, including when no pairs are comparable. Per-seed output preserves substrate-specific terminal and lifetime termination details. A termination before first RETURN remains a censored first-RETURN unit (no fabricated RETURN); it is retained with its termination reason and prevents protocol-clean/floor-success claims. Lifetime-any-failure attribution treats environment termination as failure rather than silently reporting no failure.
4. **Both-arm matched endurance attribution.** Matched U **and** C readouts now cover S1_1M–D045_1M and S1_3M–S1_1M first-RETURN and 300,000-decision lifetime-any-failure contrasts, by seed, with exact descriptive McNemar tests and explicit censor counts/details. C remains paired comparator information and is never added to canonical primary N3/F3/G3. Prior Part-A and room-size readouts are preserved.
5. **Adversarial tests.** Synthetic Git-archive fixtures exercise correct and mismatched source/commit trees; changed caller-CWD and protected-source checks are covered. Synthetic prefix tests exercise horizon-seam censoring, timeout followed by later contact, exposure immutability, no-return censoring, both failure directions, agreeing pairs, and censored/no-comparable McNemar cases. Bounded test-only trajectories exercise monitor-on/off causal digests and final state/RNG equality. An intentionally corrupted independent snapshot must fail. Synthetic attribution tests require both arms and ensure termination-before-RETURN is retained rather than silently counted as success.

## Frozen scientific and exposure boundaries

Forward identifiers remain primary `26000–26319`, endurance `26000–26059`, primary-only `26060–26319`, and bounded test-only `26320` (horizon ≤5,000 and battery fraction ≤0.21). D-045 identity support remains control-only `22053–22057`. No replacement or extension is allowed.

Preserved invalidated provenance, without reconstructing outcomes: two interrupted inherited launches on retired `23000–23319`; one pre-freeze Part-A matrix execution invalidated as validation-only exposure; C's disqualified session and exposure of retired `24000–24319`/`24320`; and earlier GPT-6 Luna provider rate-limit failures as an operational availability observation. These contribute zero evidence. No conclusion is drawn from C's code quality. The current bounded tests use only seed `26320`, off-matrix states and the declared limits; they are not D-059 evidence.

## Candidate validation

Final repair validation ran under locked CPython 3.14.7 with `PYTHONHASHSEED=0`:

- Full repository `pytest -q`: **1193 passed**, with 8 Matplotlib animation-lifetime warnings from visualization tests.
- Targeted D-059 suite: **17 passed**. D-059 trajectories used only test-only seed `26320`, constructed off-matrix states, horizon ≤5000 and battery fraction 0.20.
- `ruff check .`: PASS; format check on both changed Python files: PASS.
- `mypy src --strict` and `mypy tests/test_d059.py --strict`: PASS.
- `compileall -q src` and `import aweform`: PASS.
- Repository-wide `ruff format --check src tests` reports pre-existing format drift in unchanged files (55 under `src`, 102 across `src` and `tests`); no out-of-scope files were reformatted. Repository CI requires `ruff check .`, not the full-repo format check.

Two earlier full-suite attempts timed out before completion; a final full run completed with the result above. The repository suite includes pre-existing historical D-stage tests; the D-059-specific trajectories remained bounded to seed `26320`. No official D-059 support, official Part-A trajectory, official CLI, or full 300,000-decision D-045 identity control was run, and no scientific result was generated.

The immediate fresh pre-freeze collision/exposure audit passed after this QA. Its exact record is `/private/tmp/aweform-d059-bakeoff.gxVFDv/collision-exposure-recheck-7f940a2.md`, SHA-256 `8f7cea7c9966159f53f81f36b15f1ea5f01a16a8a13476d4771de2747749827a`. GitHub issue/PR/commit/code queries and exact structured seed-field scans found no current-allocation collision; the inherited retired `23000–23319` branch was recognized as invalidated provenance. No official support trajectory was produced. This audit clears only the result-free freeze gate.

## Post-selection freeze, controls, and execution

These are instructions for Firstmate/Flow after repair QA and selection; **they are not authorization to execute support from this repair branch**. Immediately before freezing, re-check current repository and GitHub issue/PR/commit exposure for `26000–26319` and `26320`; archive that re-check and hash it. Any collision/exposure stops for a new ruling.

```bash
# After manager selection and the immediate external reservation/exposure audit:
git rev-parse HEAD
git status --short
rg -n '26000|26320|23000|23320|24000|24320' src tests development
gh api search/issues -f q='repo:PiFlow/aweform 26000' > /tmp/d059-issues-26000.json
gh api search/issues -f q='repo:PiFlow/aweform 26320' > /tmp/d059-issues-26320.json
gh api search/commits -f q='repo:PiFlow/aweform 26000' > /tmp/d059-commits-26000.json
gh api search/commits -f q='repo:PiFlow/aweform 26320' > /tmp/d059-commits-26320.json
gh api search/code -f q='repo:PiFlow/aweform 26000' > /tmp/d059-code-26000.json
gh api search/code -f q='repo:PiFlow/aweform 26320' > /tmp/d059-code-26320.json
# Archive/hash the full local+GitHub re-check outside the repository.
export D059_RESERVATION_RECHECK_SHA256="$(shasum -a 256 /path/to/d059-recheck-archive | awk '{print $1}')"

# Result-free freeze validation:
PYTHONHASHSEED=0 uv run --locked pytest -q
PYTHONHASHSEED=0 uv run --locked ruff check .
PYTHONHASHSEED=0 uv run --locked ruff format --check src/aweform/d059.py tests/test_d059.py
PYTHONHASHSEED=0 uv run --locked mypy src --strict
PYTHONHASHSEED=0 uv run --locked mypy tests/test_d059.py --strict
PYTHONHASHSEED=0 uv run --locked python -m compileall -q src
PYTHONHASHSEED=0 uv run --locked python -c 'import aweform'
# Commit/push of the selected result-free freeze is manager-authorized only.
```

Normal frozen-checkout official execution is CLI-only and requires clean exact HEAD, actual module-root provenance, exact five-path diff, protected byte identities, local horizon seam, external re-check SHA, and `PYTHONHASHSEED=0`:

```bash
PYTHONHASHSEED=0 uv run --locked python -m aweform.d059 \
  --output development/D-059-v05-s1-level1-floor-rebaseline.json \
  --executed-commit-sha "$(git rev-parse HEAD)" \
  --reservation-recheck-sha256 "$D059_RESERVATION_RECHECK_SHA256" \
  --jobs 1
```

For literal fresh-archive regeneration, extract a `git archive` of that exact freeze SHA and supply the external local Git object directory. The runner verifies the commit object/tree, ancestry, five-path scope, and every extracted file/mode/blob ID against that tree; no SHA text alone attests the source. The object directory must be outside the extracted source tree. Supply the original runtime so regeneration is byte-identical while using a different jobs setting:

```bash
FROZEN_SHA=<exact-selected-freeze-sha>
D059_GIT_DIR=<absolute-git-object-directory-outside-extracted-archive>
git archive --format=tar "$FROZEN_SHA" > /tmp/d059-freeze.tar
TMPDIR=$(mktemp -d)
tar -xf /tmp/d059-freeze.tar -C "$TMPDIR"
cd "$TMPDIR"
PYTHONHASHSEED=0 uv run --locked python -m aweform.d059 \
  --output /tmp/d059-independent.json \
  --executed-commit-sha "$FROZEN_SHA" \
  --source-git-dir "$D059_GIT_DIR" \
  --reservation-recheck-sha256 "$D059_RESERVATION_RECHECK_SHA256" \
  --runtime-seconds "$D059_OFFICIAL_RUNTIME_SECONDS" \
  --jobs 2
cmp /path/to/official.json /tmp/d059-independent.json
```

The JSON committed with the repair is a repair-specific result-free manifest with `execution_status=NOT_EXECUTED_BOUNDED_REPAIR_CANDIDATE`; it is not an official result artifact. Firstmate reviews this exact repaired HEAD and may reject/iterate. This worker stops at clean handoff.
