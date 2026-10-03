# D-059 — V0.5 S1 Level-1 floor re-baseline

## Status, authority, and separation of roles

**FIRST EXECUTION INVALIDATED FOR FINAL D-059 ACCEPTANCE — CORRECTED RESULT-FREE FREEZE.** Sol's binding ruling `5968523256` found that D-045 whole-RETURN exposure in the completed execution was inferred from endpoint wall IDs instead of being counted directly from `boundary_scale < 1`. The official result artifact from freeze `d7258046735e6c32ce865c03183e41c6d6fbad1f` is preserved as historical provenance, but is not conformant evidence for final acceptance. Corrected source has passed pre-freeze QA; this record-only commit establishes the corrected result-free freeze. No corrected execution or corrected results exist at this freeze. Historical execution, QA and result statements below the corrected section describe only the superseded run and do not establish final acceptance.

The bounded source repair separates D-045 exposure from wall/corner anatomy in both online and independent prefix reducers. Every scaled D-045 transition has unknown active wall/corner identity because accepted telemetry does not expose its limiting constraint; static endpoint membership remains separate. The canonical result-free manifest's pending-QA label describes the worker handoff. The subsequent manager QA and freeze gate are recorded here; source, tests and manifest are unchanged from the reviewed worker commit.

## Corrected freeze and rerun authorization

- **Controlling authority:** [Sol ruling 5968523256](https://github.com/PiFlow/aweform/issues/206#issuecomment-5968523256), disposition B required; no record-only waiver. Live issue comments were rechecked immediately before this freeze with `gh-axi`; no newer ruling was present.
- **Corrected source/test commit:** `cb65b097dfc822d664fdbac59059b4b9ebd1064a`, clean at handoff and manager QA. This freeze adds only this record and its INDEX status; source, tests, canonical result-free manifest, protected files and approved CI workflow are byte-identical to that commit.
- **Implementer separation and route:** exactly one saved GPT-6 Luna/high actor implemented the correction through native Codex/OpenAI, following Flow's instruction “For any new luna worker, please use codex/openai-codex”. Saved thread `01a101cc-aec2-7ec2-a1e1-2967085d7212` was resumed for a manager-reported anatomy defect. The earlier Pi/OpenCode Go attempt failed on HTTP 429 before edits. Firstmate authored no source/test repair and independently inspected the final changes.
- **Pre-freeze exact-HEAD manager QA: PASS on `cb65b097…`.** Independently executed all 20 focused D-059 tests and a 103-transition synthetic telemetry reduction (not physical environment steps): two scaled transitions followed by 101 unscaled transitions give whole count 2/exposed true, final-100 count 0/exposed false and unknown count 2 in both reducers. Verified clean imported-tree provenance, canonical manifest, all 16 protected hashes, exact six-path scope and the narrowly approved workflow insertion. AST comparison and manual patch inspection found only passive diagnostics, manifest metadata and provenance gate changes. External evidence: `/private/tmp/aweform-d059-bakeoff.gxVFDv/corrected-cb65b09-manager-qa.md`, `corrected-cb65b09-manager-pure-qa.json` and `corrected-cb65b09-manager-pytest.log`.
- **Inspected worker validation:** final full suite 1196 passed with 8 existing Matplotlib warnings; 20 focused tests, Ruff, changed-file format, strict mypy, compile/import and provenance/manifest checks passed. Earlier interrupted attempts are not completed validation. Pre-freeze D-059 trajectories used only bounded off-matrix test seed 26320; no corrected official forward or Part-A support ran during QA.
- **Immediate allocation/provenance audit: PASS.** Main remains `0f4b0ae22564293dd178567c4c745e5903256682`. Exact seed-field scans of all 56 main Development JSONs, issue/commit/code searches and a fully paginated 129-branch inventory found no separate reservation of this allocation. Searches cannot prove absence of hidden or unindexed use. The prior authorized invalidated execution is explicitly disclosed. Canonical external audit: `/private/tmp/aweform-d059-bakeoff.gxVFDv/corrected-reservation-recheck-cb65b09.json`, SHA-256 `806441eca0203c4d47668d1aac215233fb37213fe5aaa5228f50e185e40d290b`.
- **New freeze:** this record-only commit above `cb65b097…`, to be pushed as `codex/d059-corrected-freeze`. Its exact SHA is recorded in the external execution checkpoint and later artifact's executable provenance; it cannot self-embed its own commit SHA. PR #208 stays at its existing remote HEAD until corrected regeneration succeeds and the stable corrected result layer is ready.
- **Explicit lineage:** invalidated executable `d7258046735e6c32ce865c03183e41c6d6fbad1f` → invalidated result layer `f4b0df7523dc0bd3d29a8a0bf393d2c1cf3769b4` and artifact (17,163,237 bytes; SHA-256 `685526fc9d74cb8dabe7b676676d9e8adcdbdc2012a4c8a499a2ec49e007b8bb`) → endpoint-dependent exposure/ambiguous anatomy defect → repaired source `cb65b097…` → this corrected result-free freeze → pending complete corrected rerun and independent regeneration. Old bytes/history remain preserved; the explicitly named external copy is `invalidated-first-execution-d725804-685526fc.json`.

The corrected execution must reuse the **same Development allocation**: primary 26000–26319, endurance 26000–26059, bounded test-only 26320 (horizon ≤5000, initial battery ≤0.21) and unchanged control-only D-045 support 22053–22057. This is the authorized deterministic bug-fix rerun, not untouched evidence; old and new results must not be pooled. Inherited protocol wording “fresh seed” names the original allocation unit and does not assert that this reused support was never previously executed.

Execute the entire unchanged official protocol once from a fresh archive of this pushed freeze, then exactly one independent regeneration from a separate fresh archive with the same executable SHA, audit hash and pinned official runtime. Preserve artifacts and logs externally. Compare old invalidated and corrected outcomes and diagnostics transparently; explain corrected D-045 diagnostics and any unexpected differences outside them. New descriptive anatomy fields also occur in S1 records and may change byte signatures without changing trajectories or outcomes.

Only after byte-identical corrected regeneration succeeds may Firstmate update PR #208 to its stable corrected result-layer HEAD, perform new exact-HEAD manager QA, and request designated GPT-5.6 Sol and GLM-5.3-Flash reviews and green checks on that same HEAD. No merge, VIS-D059, P, D-060, S2 or successor science is authorized.

## Historical first-execution provenance (invalidated)

- **Repair authorization:** #206 comment `5943123218`; frozen repair brief `/private/tmp/aweform-d059-bakeoff.gxVFDv/repair-brief-b-v1.md`, SHA-256 `fb1d7778e9e7e2f75da2e0f7a5bbf350f182576235dfe70817ba0a506ff878ce`.
- **Unchanged scientific authority:** #206 PROPOSAL_VERSION 2, Sol PASS `5932464537`, seam ruling `5932171938`, and controlling brief-v3 SHA-256 `2cfcf87fa589becfefb9e5d1bcf56b6bfd8dbca9607c494e10c101cb875aade6`.
- **Authorized project base:** `0f4b0ae22564293dd178567c4c745e5903256682`.
- **Repair base:** exact raw B HEAD `63ba49d4ce4f10fe4d630248c873b5a1fca27390`.
- **Repair branch:** `codex/d059-repair-b`.
- **Historical implementer / reviewer separation:** candidate source/tests were authored by isolated workers; Firstmate performed selection and manager QA without authoring candidate source/tests. The initial blinded A/B technical comparison and separate axis reviews are preserved in `/private/tmp/aweform-d059-bakeoff.gxVFDv/technical-comparison.md`. Raw A remains unchanged and no A code was imported. C remains disqualified by ruling `5941551976`, is not scored, and receives no code-quality verdict. Raw A and raw B both failed conformance; B was chosen only as the repair base, not for raw correctness or model superiority. GPT-6 Luna repaired B in two bounded iterations; the first was rejected at `364598b6a993c85c4b5bef8f74d7902f9555c04c`. The then-QA-passed repair HEAD `7f940a222618e4b5f8eb48c235c3419dca9197d4` and resulting execution are superseded by ruling `5968523256`.
- **Bake-off limits:** A and B used identical frozen brief SHA-256 `2cfcf87fa589becfefb9e5d1bcf56b6bfd8dbca9607c494e10c101cb875aade6`, same authorized base, high reasoning, and Pi → OpenCode Go. Exact routed model IDs and blind-first technical comparison are in the external comparison record. The two eligible raw candidates do not establish a general model winner. Provider/context interruptions and shared-host contention make runtime comparisons unsuitable as a model speed score.
- **Invalidated freeze SHA:** `d7258046735e6c32ce865c03183e41c6d6fbad1f`, one record-only commit above then-QA-passed source/test HEAD `7f940a222618e4b5f8eb48c235c3419dca9197d4`. This source SHA produced the superseded result and byte-identical independent regeneration; ruling `5968523256` invalidates both for final acceptance.

## Bake-off comparison and selection

The three workers received the same base and frozen implementation brief through Pi → OpenCode Go. C is excluded from candidate comparison under ruling `5941551976`. The blinded A/B first-pass standards/spec reviews and post-review reveal are retained in the external bake-off archive. Both raw implementations were rejected for correctness/boundary defects despite passing their own tests; test counts were not treated as acceptance evidence. A used `opencode-go/deepseek-v4.1-flash`; B used `opencode-go/gpt-6-luna`; C used `opencode-go/glm-5.3-flash` before disqualification.

| Candidate | Raw technical strengths | Raw defects / disposition |
| --- | --- | --- |
| A — DeepSeek V4.1 Flash, `05e13e67441141c351855adbe7a940b2f07ddac4` | Broader statistics/classification and branch tests; deterministic work items; both-arm attribution. | Historical D-056 identity and stop propagation gaps; censor-prefix and archive/seed/hash-seed gates were insufficient. Rejected; no code used for B repair. |
| B — GPT-6 Luna, `63ba49d4ce4f10fe4d630248c873b5a1fca27390` | More complete historical D-056 summaries/class comparators; archive/execution scaffolding. | Copied-prefix/non-feedback defect; production failure mapping and C-attribution gaps; caller-CWD/source provenance, archive attestation and censor-control defects. Rejected raw; used only as the authorized repair base. |
| C — GLM-5.3-Flash | Not scored. | Disqualified by `5941551976` after prohibited retired-seed exposure and reading unmerged prior candidate material. No restart or model ranking. |

Historical repair selection was a manager engineering judgment after exact repaired-HEAD QA, not a scientific result or vendor/model benchmark. Root-cause findings, synthetic reproductions, and the complete comparison are preserved in the external archive. Historical exposure of the retired `23000–23319` block remains invalidated provenance and contributes zero evidence. The pre-correction official execution used frozen SHA `d725804…`; ruling `5968523256` invalidates it for final D-059 acceptance. It remains diagnostic provenance only until a complete corrected rerun.

The implementation source/test/record changes stay within their authorized paths. The already-approved sixth path, `.github/workflows/reproducibility.yml`, retains `fetch-depth: 0` for provenance checks; no other workflow change is part of this repair. The correction preserves #206's scientific protocol, seed allocation, substrates, U/C, D-053 fixture/RNG, horizons, classifiers, statistics, branch logic, information boundary, and durable safety boundary. No P/D-060/S2/successor work is included.

## B-specific repairs

1. **Actual imported-tree and provenance binding.** Git commands are anchored to the root containing the imported `src/aweform` module, never caller CWD. Normal execution checks that exact module root is the clean Git worktree, HEAD, ancestry, and an exact authorized base diff. The historical `d725804…` freeze has the five D-059 source/test/record paths; the corrected candidate must also include the already-approved reproducibility workflow path, whose only permitted change is inserting `fetch-depth: 0` under the checkout step. The gate checks the workflow bytes against that exact insertion. It compares imported source files/modes against the verified commit's Git tree and verifies protected file hashes from the authorized base. Literal fresh `git archive` extraction remains supported: the runner requires an external local Git object directory outside the extracted tree, verifies the commit object, ancestry and allowed path diff, and compares every extracted path, mode and Git blob ID against the expected commit tree. An arbitrary SHA string is not treated as executable-source proof. No signing, network access, dependency, or general security framework was added.
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

Two earlier full-suite attempts timed out before completion; a final full run completed with the result above. This describes the superseded pre-freeze QA candidate only. The repository suite includes pre-existing historical D-stage tests; the D-059-specific trajectories remained bounded to seed `26320`. At that pre-freeze QA stage no official D-059 support, official Part-A trajectory, official CLI or full 300,000-decision D-045 identity control had run. The later official execution and reproduction recorded below are now invalidated for final acceptance.

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

The historical `d725804…` frozen-checkout CLI required clean exact HEAD, actual module-root provenance, its exact five-path diff, protected byte identities, local horizon seam, external re-check SHA, and `PYTHONHASHSEED=0`:

```bash
PYTHONHASHSEED=0 uv run --locked python -m aweform.d059 \
  --output development/D-059-v05-s1-level1-floor-rebaseline.json \
  --executed-commit-sha "$(git rev-parse HEAD)" \
  --reservation-recheck-sha256 "$D059_RESERVATION_RECHECK_SHA256" \
  --jobs 1
```

For literal fresh-archive regeneration of that historical freeze, extract a `git archive` of the exact freeze SHA and supply the external local Git object directory. The historical runner verified the five-path scope; the corrected candidate's scope adds only the specifically approved `fetch-depth: 0` workflow insertion. The runner verifies the commit object/tree, ancestry, path scope, and every extracted file/mode/blob ID against that tree; no SHA text alone attests the source. The object directory must be outside the extracted source tree. Supply the original runtime so regeneration is byte-identical while using a different jobs setting:

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

At historical freeze commit `d7258046735e6c32ce865c03183e41c6d6fbad1f`, the JSON was the result-free protocol manifest. It was subsequently replaced in the result layer by the now-invalidated official artifact. Both prior states remain recoverable in Git history; this repair restores a result-free manifest and retains the old artifact bytes in verified external copies.

## Invalidated historical execution and artifact

The superseded CLI ran from a fresh literal archive of freeze SHA `d7258046735e6c32ce865c03183e41c6d6fbad1f`, with external Git object directory `/Users/flow/Dev/firstmate-homes/aweform/projects/aweform/.git/worktrees/B`, reservation re-check SHA-256 `8f7cea7c9966159f53f81f36b15f1ea5f01a16a8a13476d4771de2747749827a`, `PYTHONHASHSEED=0`, locked CPython 3.14.7, and `--jobs 1`. Runtime was `10611.133005790995` seconds. This was the only pre-correction official support execution and it is invalidated for final acceptance. An earlier CLI attempt omitted `--source-git-dir` and stopped at the provenance gate before seed checks or trajectories; it produced no result artifact.

The invalidated artifact `D-059-v05-s1-level1-floor-rebaseline.json` had schema `d059-result-v1`, size 17,163,237 bytes, whole-file SHA-256 `685526fc9d74cb8dabe7b676676d9e8adcdbdc2012a4c8a499a2ec49e007b8bb`, and canonical-payload SHA-256 excluding its integrity field `eb91c98e4b4de3ff44008290f1d9a817f3ae9e7048e1ea137527657af343ae7c`. Its bytes are retained in both verified external copies and the prior result-layer commit.

## Superseded diagnostic readouts — not corrected results

Every count, outcome, interval, attribution, and control statement in this section is copied from the invalidated first execution. These readouts are retained to preserve chronology and do not establish the corrected D-059 outcome. The corrected allocation must be rerun from its own freeze before any result is reported.

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

The invalidated execution's controls were recorded as passed: S1 C≡U identity over 2,876 paired executions with zero stalls; five D045 harness identity pairs on seeds `22053–22057`; 60 online primary-prefix records matching their independently derived records; bounded monitor on/off causal, fixture and RNG digests; all Part-A reset/legality checks; protected-source provenance, horizon seam, seed gates and deterministic source. The exposure-classification defect makes this execution nonconformant for final D-059 acceptance despite those other recorded checks. D-058 remains an endpoint-only kinematic idealization, not continuous contact or hardware fidelity.

## Invalidated-run reproducibility provenance

The first independent regeneration was interrupted by a Firstmate restart and wrote no artifact; it contributes no evidence and did not rerun official support. A replacement regeneration ran from another fresh literal archive of the same freeze, with the same external Git object directory, audit SHA, Python 3.14.7, `PYTHONHASHSEED=0`, and runtime fixed to the official recorded value; `--jobs 2` was supplied. This implementation executes serially in ascending order, so jobs=2 verifies byte invariance and is not a parallel-speed result. `cmp` returned 0: the independent artifact is byte-identical to official output, with size 17,163,237 bytes and SHA-256 `685526fc9d74cb8dabe7b676676d9e8adcdbdc2012a4c8a499a2ec49e007b8bb`.

A separate read-only manager audit recomputed artifact integrity and row signatures, verified primary seed order and outcome counts, Part-A coverage and outcomes, frozen branch labels, and the zero-failure CP bound independently. It also checked S1 U/C trajectory and final-state digest identity per seed for both room sizes and rechecked stored online/independent prefix records. All passed.

Planning runtime was approximately 7,200 seconds, with a conservative cap estimate of 11,160 seconds; the official runtime was 10,611.133 seconds. The independent job setting and this elapsed time do not form a model-speed comparison.

## Final review gate

The historical result-layer review gate did not pass and is superseded by ruling `5968523256`. After the corrected rerun, Firstmate must perform fresh exact-HEAD QA and request the required independent reviews and green checks against that same corrected candidate. No prior review qualifies the corrected candidate. No P, D-060, S2, successor or visualizer work is included here.
