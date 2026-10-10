# D060-REDUCED-v1 — bounded selected-case diagnostic

- **id:** D060-REDUCED-v1 (separate exploratory diagnostic; not a substitute for D-060)
- **date:** 2026-10-10
- **exact_sha:** `29ced9f52d3bafb38886a76ad232e00f10388b81` (frozen executable/protocol source; this result record is a later record-only commit)
- **development_seeds:** none; deterministic evaluator cases, no organism or seed execution
- **disposition:** CONTINUING

## Question

Did the separately frozen finite sample of D-060 substrate trajectories and H.2(c) transplant probes pass the unchanged selected-case checks, including both original H.2 comparator branches, and did an official-source run reproduce byte-for-byte from a fresh archive of the same executable SHA?

## World and mechanism

D-060's fixed V0.5 3 m room, round interior obstacles, D-045 dynamics and D-058 wall comparator. No controller or organism execution was involved. The evaluator-only adapter reuses the pinned D-060/D-058 environments and independent oracle. It carries only the approved selected-case evaluator orchestration and independent rotated-corner checks; it does not alter or duplicate production contact law or oracle numerical mechanics. Its maintained evaluator duplication and provenance mapping are documented in [`D060-REDUCED-v1-protocol.md`](D060-REDUCED-v1-protocol.md).

The original pinned substrate/oracle/test SHA-256s are `6391de1f383968a6369870dc54665a79defacd374c8a418707ba768ea7e7cf98`, `ea50718f855e2e934177e2889dd5ef520020fee2953e6a956229dd1b7c0684c2`, and `12761052e15419eb9d27fb05404c35bac066798478d4c71569cdf986cc6f8773`. The executable adapter SHA-256 at the frozen SHA is `43e69f7f477e494f33e25fc2815af3dad22f383df192cc3d7bf3bfb6f82f726c`; the protocol-document SHA-256 is `284d44f3be360177e6d5408b123a16730fa28580c51a1ab7ff2ea6243db8ba25`; `uv.lock` SHA-256 is `512f300c3850f348f0690c0f4c3164a403c72c54f7fd97fb8fd43d8b9fdaf148`.

## Observed

The official-source and fresh-archive copies both emitted `D060_REDUCED_DIAGNOSTIC_COMPLETE`, exited 0, and compared byte-identically. Each JSON is 2,764,472 bytes with SHA-256 `f45d5ca93a20e511c39caf82f5c820b29472d944a0bb2ed61c7236c4ed61ab1e`. Both report executed SHA `29ced9f52d3bafb38886a76ad232e00f10388b81`, Python 3.14.7, NumPy 2.5.2, macOS 26.6.2 arm64, and identical pinned D-060/oracle hashes.

- **Rays:** all 19 frozen complete trajectories, 204 transitions. **Pockets:** all 54 complete trajectories, 1,728 transitions. **Resets:** all 54 attempts completed.
- **H.2(a):** 577 lockstep comparisons; 12 lockstep exclusions. The 14 historical strict production/oracle sign disagreements remain split 7 production-penetrating/oracle-clear and 7 production-clear/oracle-penetrating, with all 14 excluded from H.2 identity totals.
- **H.2(b):** 718 fresh-control eligible steps and all 718 compared using the pinned `_h2b_requires_fresh_control`, explicit current-state reset options, `_restore_h2b_heading`, and the original comparison with `ignore_index=True`. Exact modulo-2π heading representation restoration occurred 189 times. No H.2(b) comparison failed.
- **H.2(c) single steps:** 800 selected candidates. Five starts were rejected by the unchanged reset-legality rule, excluding 50 slots; all five rejected starts were in the 1065.6 J low-energy family. The remaining 750 candidates were attempted; 747 eligible candidates were compared and 3 oracle-ineligible candidates were excluded. All 640 wall/corner candidates were compared. In the low-energy family, 11/16 starts were accepted, 107/160 candidates were compared, 50 slots were excluded by reset rejection and 3 candidates were oracle-ineligible. The 107 compared low-energy endpoints had minimum oracle and production obstacle gap `0.0016542709538479167 m`; no low-energy candidate reached an obstacle-resolved step. The full inventory records each start/candidate identity and status.
- **H.2(c) schedule:** all 64 scheduled D-060 commands executed and all 64 eligible D-058 lockstep comparisons completed. Wall-plus-obstacle displacement decomposition was checked for every executed D-060 transition and compared D-058 transition; the new direct D-058 reconstruction counter records 2,106 compared-transition checks.
- **Selected endpoint checks:** 2,743 endpoints received 10,972 independent rotated-corner checks, 2,743 displacement checks and 2,743 total wall/obstacle reconstruction checks. The explicit D-058 reconstruction counter is 2,106 compared transitions. The 630 obstacle-resolved steps each received the full 3,600-direction oracle scan: **2,268,000 directions total**; 1,263,118 produced no free ray. H.6 retained 92,358 ordered samples; maximum penetration was 0.025 m, below frozen `B = 0.07292419035931953 m`.
- Frozen two-distinct-inner-contact coverage was A1 `41/41`, A2 `37/35`, and A3 `37/39` by sign. No selected check failed.

**Resource and reproduction record:** the one authorized fixed preflight at this exact SHA exited 0 in 177.24 s, maximum RSS 92,176,384 bytes; the prescribed `10×` estimate plus 25% margin was 2,215.5 s (36.9 min) per copy. The single official/archive pair ran as two separate internally serial processes. Official elapsed 703.89 s (user 697.47 s, sys 1.56 s), maximum RSS 92,782,592 bytes; archive elapsed 703.33 s (user 696.85 s, sys 1.55 s), maximum RSS 99,975,168 bytes. Both completed within the 2-hour cap using Python 3.14.7/NumPy 2.5.2 and separate source/output/log/temp/cache roots. The independently generated archive tars were byte-identical (SHA-256 `955699e8a7e243c4c83055d7201d8548ada3c979357b3da9edd642bb18c68c84`); all 395 extracted tracked blobs matched the committed tree, and the copy outputs matched byte-for-byte.

Luna Manager’s explicit #220 resource-release receipt is https://github.com/PiFlow/aweform/issues/197#issuecomment-6097037227; it confirms the measured worker is gone, no #220 calibration/validation worker or scheduled run remains, and the CPU reservation is released. The independent immediate pre-launch snapshot at 2026-10-10T11:41:56Z reported 8 CPUs, 32 GiB physical memory, load averages 2.32/2.41/2.34, 65% system memory free, and no D060/Pymunk/calibration process. After the pair, the host reported load 3.98/4.35/3.57, 63% memory free, and no such process remaining. No source or protocol changes were made after the frozen SHA before either copy.

The earlier `4a9a0a3` copies are retained unchanged as **superseded, incomplete selected-check evidence**: that adapter omitted H.2(b), overstated the oracle-ray denominator, and did not disclose the low-energy family split. The manager-QA report for the old PR head is preserved at `/Users/flow/Dev/firstmate-homes/aweform/data/d060-reduced-manager-qa/report.md`; it is not approval of this corrected SHA. The earlier `29c8e265…` preflight also remains historical and was not pooled with this execution.

## Provisional reading and limits

The fixed finite selected inventory passed the recorded checks, including the restored H.2(b) comparator, and reproduced byte-for-byte from a fresh archive. This does **not** complete, waive or replace original #213 full D-060 conformance: 26,733 of 26,752 original ray sequences remain omitted, and selected ray/pocket work is 0.8214% of transition count (not a runtime or failure-detection fraction). It does not establish omitted H.1–H.8 breadth, universal or rare-case behavior, acceptance, merge authority, ADR completion, S2-C authorization, or Pymunk replacement/fidelity. The original full matrix, source, oracle, tests, artifact, record and CHANGES REQUIRED history remain unchanged.

Both JSONs, raw logs, exit statuses, the preflight, source archives and extracted tree, commands, host/environment snapshots, timings, case inventory, counters and SHA-256 receipts are retained at `/Users/flow/Dev/firstmate-homes/aweform/data/d060-reduced-v1/evidence/29ced9f52d3bafb38886a76ad232e00f10388b81/`. The prior `8d62074` pair and evidence remain immutable at `/Users/flow/Dev/firstmate-homes/aweform/data/d060-reduced-v1/evidence/8d620748f52db64e52bab4f8eb96fed05d0cfc20/`; the prior `4a9a0a3` outputs and receipts also remain immutable at their original evidence path.

Software validation before freezing the corrected executable: `uv run --frozen pytest -q` — 1,240 passed, 1 skipped; `uv run --frozen ruff check .` — passed; `uv run --frozen mypy src` — passed; `uv run --frozen mypy --strict src/aweform/d060_reduced.py` — passed without new suppression. The inherited broad `ignore_errors` override for original `aweform.d060` and `aweform.d060_oracle` is unchanged and does not establish strict typing for those modules.

## Next

The result record is now being added after the frozen source run. Obtain fresh manager QA, independent Sol review of the exact resulting HEAD, and applicable CI; earlier QA/review do not transfer. Flow directs that PR #224 remain OPEN and UNMERGED. Do not retarget, create an archival landing branch, modify #222 or `main`, or merge; await a new explicit founder disposition. This remains a bounded exploratory sample, not full #213 conformance or acceptance.
