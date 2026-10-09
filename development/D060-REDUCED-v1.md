# D060-REDUCED-v1 — bounded selected-case diagnostic

- **id:** D060-REDUCED-v1 (separate exploratory diagnostic; not a substitute for D-060)
- **date:** 2026-10-09
- **exact_sha:** `4a9a0a32c72186bf5cfc5470584958956f8fc738` (diagnostic executable/protocol; this record is a later record-only commit)
- **development_seeds:** none; deterministic evaluator cases, no organism or seed execution
- **disposition:** CONTINUING

## Question

Did the separately frozen finite sample of D-060 substrate trajectories and H.2(c) transplant probes pass the unchanged selected-case checks, and did an official-source run reproduce byte-for-byte from a fresh archive of the same executable SHA?

## World and mechanism

D-060's fixed V0.5 3 m room, round interior obstacles, D-045 dynamics and D-058 wall comparator. No controller or organism execution was involved. An evaluator-only adapter reuses the pinned D-060/D-058 environments and independent oracle. It carries only the approved selected-case evaluator orchestration, low-battery H.2(c) identity/reconstruction, and independent rotated-corner checks. It does not alter or duplicate production contact law or oracle numerical mechanics. Its maintained evaluator duplication and provenance mapping are documented in [`D060-REDUCED-v1-protocol.md`](D060-REDUCED-v1-protocol.md).

Original pinned substrate/oracle/test SHA-256s remain `6391de1f383968a6369870dc54665a79defacd374c8a418707ba768ea7e7cf98`, `ea50718f855e2e934177e2889dd5ef520020fee2953e6a956229dd1b7c0684c2`, and `12761052e15419eb9d27fb05404c35bac066798478d4c71569cdf986cc6f8773`. The exact executable adapter SHA-256 is `63a4cfeedae96cfd5d5f4be8310449880bb208d2eedf13bbb7e03c547f2a4d40`; the frozen protocol-document blob SHA-256 at the executable SHA is `238a45fa3a1a6b2cb1f9996d717c0ba656578fbe7dd2876f4b34c482ab47aaf0`; `uv.lock` SHA-256 is `512f300c3850f348f0690c0f4c3164a403c72c54f7fd97fb8fd43d8b9fdaf148`. A post-execution whitespace-only cleanup removed trailing spaces from four protocol header lines; it changes no protocol wording, case identities, order, or rules, and the pre-execution blob remains available at the executable SHA.

## Observed

Both official and fresh-archive copies emitted `D060_REDUCED_DIAGNOSTIC_COMPLETE`, exited 0, and compared byte-identically. Each JSON is 2,751,363 bytes with SHA-256 `14411354b8f562072e57aa74878a6d3c71211cc3d45f9fadb964a56c02090068`. Both record source SHA `4a9a0a32c72186bf5cfc5470584958956f8fc738`, Python 3.14.7, NumPy 2.5.2, macOS 26.6.2 arm64, and identical original D-060/oracle hashes.

Executed/eligible/excluded inventory:

- **Rays:** all 19 frozen full trajectories, 204 transitions. **Pockets:** all 54 full trajectories, 1,728 transitions. **Resets:** 54/54 attempted and checked.
- The historical raw boundary-sign disagreements were 14 total: 7 production-penetrating/oracle-clear and 7 production-clear/oracle-penetrating. The artifact preserves per-case/command raw gaps and strict classifications; all 14 were excluded from H.2 identity totals.
- **H.2(c) single-step bundle:** 800 selected candidates; five starts were rejected by the unchanged reset legality rule, excluding 50 candidate slots. The other 750 candidates were attempted: 747 eligible and compared, 3 oracle-ineligible. The artifact preserves accepted and rejected start identities, all 800 candidate identities/statuses, command order, and raw production/oracle gaps.
- **H.2(c) schedule:** all 64 D-060 commands executed and all 64 eligible D-058 lockstep comparisons completed; wall-plus-obstacle decomposition was checked for every executed/compared transition.
- **All selected endpoints:** 2,743 transitions received 10,972 independent corner checks (four per endpoint), 2,743 displacement checks, and 2,743 independent endpoint decompositions. The 630 obstacle-resolved steps each used the full 3,600-direction scan and unchanged O1/O2 checks (15,876,000 oracle rays total). H.6 retained 92,358 ordered samples; maximum penetration was 0.025 m, below frozen `B = 0.07292419035931953 m`.
- Frozen two-distinct-inner-contact coverage was present for each arc/sign: A1 `41/41`, A2 `37/35`, A3 `37/39`.
- No selected check failed. These are descriptive outcomes for this finite targeted inventory only.

**Runtime / resource diagnostic:** fixed preflight at the same final executable SHA completed in 179.87 s with 91,111,424-byte maximum RSS. The conservative `10×` estimate plus 25% concurrency margin was about 37.5 minutes per paired copy, below the two-hour-per-copy stop limit. The full copies ran simultaneously as separate internally serial processes: official elapsed 714.64 s, CPU 699.34 s, max RSS 94,027,776 bytes; archive elapsed 713.89 s, CPU 698.65 s, max RSS 97,107,968 bytes. They used the same interpreter/locked environment and distinct source, output, log, temporary and cache paths. No Pymunk process competed for resources.

The earlier 29c8e265… preflight remains preserved as superseded timing provenance; it was not pooled with the final-SHA estimate or scientific result. The inventory-only correction at 4a9a0a32… was verified not to alter selected cases/order, transitions, endpoint execution, sign outcomes or H.6 values before the authorized final-SHA preflight.

## Surprised by

The conservative preflight estimate was much longer than the observed concurrent full-copy elapsed time. The selected inventory also contained five reset-rejected transplanted starts, so 50 of the predeclared 800 candidate slots were correctly excluded before transition execution rather than silently treated as accepted comparisons.

## Provisional reading

The frozen selected sample passed its checks and reproduced byte-for-byte under the recorded source/runtime. This does **not** complete, waive, or replace original #213 full D-060 conformance: 26,733 of 26,752 original ray sequences remain omitted, and the selected ray/pocket transition fraction is 0.8214% (not a runtime or failure-detection fraction). It does not satisfy omitted H.1–H.8 breadth, establish universal/rare-case behavior, authorize merge or an ADR change, authorize S2-C, or establish Pymunk replacement/fidelity. The original full matrix, artifact, source, review history and CHANGES REQUIRED disposition remain unchanged.

The task evidence directory is `/Users/flow/Dev/firstmate-homes/aweform/data/d060-reduced-v1/evidence/4a9a0a32c72186bf5cfc5470584958956f8fc738/`. It retains both JSONs, the raw archive tar and extraction, raw logs, exit statuses, host/environment snapshots, commands, timings, receipts, full case inventory, corner/reconstruction identities and counters. This evidence path is outside the worktree under the task's explicit exception.

Validation on the frozen executable SHA: `uv run --frozen pytest -q` — 1,237 passed, 1 skipped; `uv run --frozen ruff check .` — passed; `uv run --frozen mypy src` — passed; independent `uv run --frozen mypy --strict src/aweform/d060_reduced.py` — passed without a new suppression. The inherited broad `ignore_errors` override for original `aweform.d060` and `aweform.d060_oracle` remains unchanged; this does not establish strict typing for those original modules.

## Next

Submit the separate exact-base PR for manager QA and independent Sol exact-HEAD review. Keep all full-D-060 acceptance and merge decisions with their existing authority; do not make a successor science or Pymunk claim from this diagnostic.
