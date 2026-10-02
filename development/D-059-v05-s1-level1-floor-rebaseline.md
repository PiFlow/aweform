# D-059 — V0.5 S1 Level-1 floor re-baseline

## Status, authority, and separation of roles

This descriptive Development execution is complete; `CONTINUING` describes the broader scientific thread. Raw candidate B failed conformance and was repaired under the bounded GPT-6 Luna repair ruling. The resulting implementation passed exact-HEAD manager QA, the pre-freeze collision/exposure audit, and a result-free freeze. The sole official support execution and independent byte-identical regeneration are complete. D-059 remains subject to the same-HEAD final review and CI gate; the measured branch labels below are not final PR acceptance.

- **Repair authorization:** #206 comment `5943123218`; frozen repair brief `/private/tmp/aweform-d059-bakeoff.gxVFDv/repair-brief-b-v1.md`, SHA-256 `fb1d7778e9e7e2f75da2e0f7a5bbf350f182576235dfe70817ba0a506ff878ce`.
- **Unchanged scientific authority:** #206 PROPOSAL_VERSION 2, Sol PASS `5932464537`, seam ruling `5932171938`, and controlling brief-v3 SHA-256 `2cfcf87fa589becfefb9e5d1bcf56b6bfd8dbca9607c494e10c101cb875aade6`.
- **Authorized project base:** `0f4b0ae22564293dd178567c4c745e5903256682`.
- **Repair base:** exact raw B HEAD `63ba49d4ce4f10fe4d630248c873b5a1fca27390`.
- **Repair branch:** `codex/d059-repair-b`.
- **Implementer / reviewer separation:** candidate source/tests were authored by isolated workers; Firstmate performed selection and manager QA without authoring candidate source/tests. The initial blinded A/B technical comparison and separate axis reviews are preserved in `/private/tmp/aweform-d059-bakeoff.gxVFDv/technical-comparison.md`. Raw A remains unchanged and no A code was imported. C remains disqualified by ruling `5941551976`, is not scored, and receives no code-quality verdict. Raw A and raw B both failed conformance; B was chosen only as the repair base, not for raw correctness or model superiority. GPT-6 Luna repaired B in two bounded iterations; the first was rejected at `364598b6a993c85c4b5bef8f74d7902f9555c04c`, and the conformant repair is `7f940a222618e4b5f8eb48c235c3419dca9197d4`.
- **Bake-off limits:** A and B used identical frozen brief SHA-256 `2cfcf87fa589becfefb9e5d1bcf56b6bfd8dbca9607c494e10c101cb875aade6`, same authorized base, high reasoning, and Pi → OpenCode Go. Exact routed model IDs and blind-first technical comparison are in the external comparison record. The two eligible raw candidates do not establish a general model winner. Provider/context interruptions and shared-host contention make runtime comparisons unsuitable as a model speed score.
- **Selected freeze SHA:** `d7258046735e6c32ce865c03183e41c6d6fbad1f`, one record-only commit above QA-passed source/test HEAD `7f940a222618e4b5f8eb48c235c3419dca9197d4`. This exact source SHA produced the official result and independent regeneration.

## Bake-off comparison and selection

The three workers received the same base and frozen implementation brief through Pi → OpenCode Go. C is excluded from candidate comparison under ruling `5941551976`. The blinded A/B first-pass standards/spec reviews and post-review reveal are retained in the external bake-off archive. Both raw implementations were rejected for correctness/boundary defects despite passing their own tests; test counts were not treated as acceptance evidence. A used `opencode-go/deepseek-v4.1-flash`; B used `opencode-go/gpt-6-luna`; C used `opencode-go/glm-5.3-flash` before disqualification.

| Candidate | Raw technical strengths | Raw defects / disposition |
| --- | --- | --- |
| A — DeepSeek V4.1 Flash, `05e13e67441141c351855adbe7a940b2f07ddac4` | Broader statistics/classification and branch tests; deterministic work items; both-arm attribution. | Historical D-056 identity and stop propagation gaps; censor-prefix and archive/seed/hash-seed gates were insufficient. Rejected; no code used for B repair. |
| B — GPT-6 Luna, `63ba49d4ce4f10fe4d630248c873b5a1fca27390` | More complete historical D-056 summaries/class comparators; archive/execution scaffolding. | Copied-prefix/non-feedback defect; production failure mapping and C-attribution gaps; caller-CWD/source provenance, archive attestation and censor-control defects. Rejected raw; used only as the authorized repair base. |
| C — GLM-5.3-Flash | Not scored. | Disqualified by `5941551976` after prohibited retired-seed exposure and reading unmerged prior candidate material. No restart or model ranking. |

Repair selection is a manager engineering judgment after exact repaired-HEAD QA, not a scientific result or vendor/model benchmark. Root-cause findings, synthetic reproductions, and the complete comparison are preserved in the external archive. Historical exposure of the retired `23000–23319` block remains invalidated provenance and contributes zero evidence. The only valid forward official execution used frozen SHA `d725804…`; no other forward support is counted.

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

Two earlier full-suite attempts timed out before completion; a final full run completed with the result above. The repository suite includes pre-existing historical D-stage tests; the D-059-specific trajectories remained bounded to seed `26320`. At this pre-freeze QA stage no official D-059 support, official Part-A trajectory, official CLI or full 300,000-decision D-045 identity control had run. The one authorized official support and its reproduction are recorded below.

The immediate fresh pre-freeze collision/exposure audit passed after this QA. Its exact record is `/private/tmp/aweform-d059-bakeoff.gxVFDv/collision-exposure-recheck-7f940a2.md`, SHA-256 `8f7cea7c9966159f53f81f36b15f1ea5f01a16a8a13476d4771de2747749827a`. GitHub issue/PR/commit/code queries and exact structured seed-field scans found no current-allocation collision; the inherited retired `23000–23319` branch was recognized as invalidated provenance. This audit cleared the result-free freeze gate only.

## Frozen execution procedure

This section preserves the procedure followed for the selected freeze. The recorded forward re-check was run immediately before freezing, and the official CLI was run once only after the pushed freeze and Sol's execution-gate PASS.

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

The JSON at the result-free freeze commit `d7258046735e6c32ce865c03183e41c6d6fbad1f` was the result-free protocol manifest. It was subsequently replaced in the working branch by the single official result artifact; both states remain recoverable from Git history.

## Official execution and artifact

The valid CLI ran from a fresh literal archive of freeze SHA `d7258046735e6c32ce865c03183e41c6d6fbad1f`, with external Git object directory `/Users/flow/Dev/firstmate-homes/aweform/projects/aweform/.git/worktrees/B`, reservation re-check SHA-256 `8f7cea7c9966159f53f81f36b15f1ea5f01a16a8a13476d4771de2747749827a`, `PYTHONHASHSEED=0`, locked CPython 3.14.7, and `--jobs 1`. Runtime was `10611.133005790995` seconds. This was the sole valid official support execution. An earlier CLI attempt omitted `--source-git-dir` and stopped at the provenance gate before seed checks or trajectories; it produced no result artifact.

Artifact `D-059-v05-s1-level1-floor-rebaseline.json` has schema `d059-result-v1`, size 17,163,237 bytes, whole-file SHA-256 `685526fc9d74cb8dabe7b676676d9e8adcdbdc2012a4c8a499a2ec49e007b8bb`, and canonical-payload SHA-256 excluding its integrity field `eb91c98e4b4de3ff44008290f1d9a817f3ae9e7048e1ea137527657af343ae7c`.

## Results and interpretation

The ordered primary block `26000–26319` produced 320 classifiable first RETURNs on S1_3M; all docked. `N3=320`, `F3=0`, and `G3=0`. The one-sided exact 95% Clopper–Pearson interval is `[0, 0.009317979409]` after the declared 12-place artifact canonicalization; its unrounded upper bound is `0.00931797940888407`. It lies below the frozen 1% operational trigger. The frozen rules therefore yield `P_BRANCH=P_NOT_JUSTIFIED`, `FLOOR_S1_3M=SETTLED`, and `S1_1M_ALERT=false`. These are descriptive Development decisions, not EXP evidence or safety, hardware, lifetime-reliability, or biological-adequacy claims.

All 7,488 Part-A rows docked: 768 wall/corner and 480 room-range starts per each of 3 substrates and 2 arms. Among primary successes, 209 RETURNs had at least one wall exposure; exposure is not itself a failure or causal attribution. The 60-seed S1_3M/U endurance lifetimes contributed 300 nonduplicate later RETURN records, all docked; they do not add independent primary observations. Each S1_3M and S1_1M U/C lifetime completed six dock/recovery cycles without termination.

Matched 60-seed `S1_1M` versus `D045_1M` attribution:

| Arm / readout | S1-only failures | D045-only failures | Neither fails | Exact two-sided McNemar p |
| --- | ---: | ---: | ---: | ---: |
| U first RETURN | 0 | 32 | 28 | 4.66×10⁻¹⁰ |
| U lifetime-any-failure | 0 | 53 | 7 | 2⁻⁵² ≈ 2.2204×10⁻¹⁶ |
| C first RETURN | 0 | 0 | 60 | 1 |
| C lifetime-any-failure | 0 | 0 | 60 | 1 |

No pairs were censored or failed in both arms. The artifact rounds the U lifetime p-value to `0.0` at 12 decimal places; the exact count-based value is `2⁻⁵²`, not zero. Attribute these paired outcomes to the whole D-045→D-058 wall-rule package, not a single wall-law component. D045_1M U recorded 45 eventual lifetime terminations; those remain distinct from the first-RETURN contrast.

Across 18,000,000 endurance decisions per S1 substrate/arm, Level-1 preemption occurred on 6,812,086 decisions on S1_3M (37.8449%) and 6,789,858 on S1_1M (37.7214%). The D045_1M U arm recorded 4,503,845 preemptions over 12,136,195 executed decisions (37.1108%); D045_1M C recorded 3,395,435 over 18,000,000 (18.8635%). The shorter U denominator reflects the 45 terminated lifetimes. Reward remained exactly zero and organism-facing `info` empty.

Required controls passed: S1 C≡U identity over 2,876 paired executions with zero stalls; five D045 harness identity pairs on seeds `22053–22057`; 60 online primary-prefix records matching their independently derived records; bounded monitor on/off causal, fixture and RNG digests; all Part-A reset/legality checks; protected-source provenance, horizon seam, seed gates and clean deterministic source. D-058 remains an endpoint-only kinematic idealization, not continuous contact or hardware fidelity.

## Reproducibility

The first independent regeneration was interrupted by a Firstmate restart and wrote no artifact; it contributes no evidence and did not rerun official support. A replacement regeneration ran from another fresh literal archive of the same freeze, with the same external Git object directory, audit SHA, Python 3.14.7, `PYTHONHASHSEED=0`, and runtime fixed to the official recorded value; `--jobs 2` was supplied. This implementation executes serially in ascending order, so jobs=2 verifies byte invariance and is not a parallel-speed result. `cmp` returned 0: the independent artifact is byte-identical to official output, with size 17,163,237 bytes and SHA-256 `685526fc9d74cb8dabe7b676676d9e8adcdbdc2012a4c8a499a2ec49e007b8bb`.

A separate read-only manager audit recomputed artifact integrity and row signatures, verified primary seed order and outcome counts, Part-A coverage and outcomes, frozen branch labels, and the zero-failure CP bound independently. It also checked S1 U/C trajectory and final-state digest identity per seed for both room sizes and rechecked stored online/independent prefix records. All passed.

Planning runtime was approximately 7,200 seconds, with a conservative cap estimate of 11,160 seconds; the official runtime was 10,611.133 seconds. The independent job setting and this elapsed time do not form a model-speed comparison.

## Final review gate

The final artifact/Development record PR requires Firstmate QA, independent GPT-5.6 Sol review, independent GLM-5.3-Flash (Z.ai via OpenCode Go) review, and green required checks on the same current PR HEAD. A later commit invalidates those SHA-specific passes. Flow comment `5951589600`, clarified by Sol `5951967721`, authorizes Sol to merge only after all three reviews and checks pass on that same HEAD and a guarded re-fetch confirms current HEAD/base/checks. Firstmate does not merge. No P, D-060, S2, successor or visualizer work is included here.
