# D060-REDUCED-v1 frozen protocol

**Status:** Frozen diagnostic protocol; exploratory/evaluator-only, not full D-060 conformance.
**Protocol ID:** `D060-REDUCED-v1`; artifact schema `d060-reduced-v1`.
**Authorization:** Issue https://github.com/PiFlow/aweform/issues/223, following Flow direction and Sol proposal PASS recorded on issue 197.
**Base:** `039d0a4810aaffb6671f968a82fb6850b1596659`, descending from main `ce4f4943f6d8fcd84c723a151b15178f3856e098`.
**Pinned original blobs at base:** `src/aweform/d060.py` SHA-256 `6391de1f383968a6369870dc54665a79defacd374c8a418707ba768ea7e7cf98`; `src/aweform/d060_oracle.py` SHA-256 `ea50718f855e2e934177e2889dd5ef520020fee2953e6a956229dd1b7c0684c2`; `tests/test_d060.py` SHA-256 `12761052e15419eb9d27fb05404c35bac066798478d4c71569cdf986cc6f8773`. The dedicated adapter and this protocol must be committed and the exact executable SHA recorded before any benchmark or result run.

## Boundary and implementation

Only the separate adapter `src/aweform/d060_reduced.py`, its focused tests, this protocol, and the later result record may change. The original D-060 implementation, independent oracle, tests, configuration, ADRs, historical artifact and original record remain byte-for-byte unchanged. Do not modify/push/accept the original candidate. The original full `run_d060_conformance` remains unexecuted in this task: its full matrix is not this diagnostic.

The original runner has no selected-case interface. As explicitly clarified by Main, the adapter carries only the bounded evaluator orchestration/check layer needed for these frozen selected families. It reuses `D060Env`, `D058Env`, the pinned production signed-gap helper/classification, `_h2*` comparison eligibility helpers, differential-drive primitive, the independent `d060_oracle` workspace-gap/3,600-ray/chord primitives, D-058 start generator, and the original obstacle/layout constants. It does **not** reimplement or change production contact/projection law, oracle numerical geometry/ray march, tolerances, physical dynamics, or organism inputs. Review the adapter against the original nested `check_one` in `d060.py` (base lines 661–855), original ray/pocket generation and H.5/H.2(c) loops (base lines 859–944), and oracle implementation in `d060_oracle.py`. This is maintained evaluator duplication, disclosed for independent Sol review; it is not a production/oracle API change.

The artifact may report only `D060_REDUCED_DIAGNOSTIC_COMPLETE` or `D060_REDUCED_DIAGNOSTIC_STOP`. It must never emit `D060_SUBSTRATE_CONFORMANT`. This finite diagnostic cannot meet #213, satisfy omitted H.1–H.8 coverage, alter the old artifact/review history, authorize merge/ADR completion, authorize S2-C, or establish Pymunk replacement/fidelity.

## Frozen case selection and order

Use the exact existing constants/layout, H32, U9/U10, D-045/D-058 dynamics, production and oracle laws, strict `g < 0` classification, `τ_c`, O1/O2 limits, full 3,600-direction oracle scans, 63 ordered H.6 samples, original D-058 lockstep/reset-option fields, and exact comparison/STOP semantics. Preserve first-in-order behavior. Keep accepted, rejected, eligible, excluded, compared, and executed counts distinct. No postselection, truncated sequence, reduced ray scan, tolerance adjustment, or result-directed tuning.

### Ray sequences: 19 / 26,752; 204 transitions

Exact `(ray_index, H32_heading_index, sequence)` identities, using original `_feature_rays()` and heading ordering:

- Historical sign-disagreement trajectories: `(12,15,Q1)`, `(22,21,Q1)`, `(22,21,Q11)`, `(22,25,Q8)`, `(22,27,Q1)`, `(24,24,Q8)`, `(28,15,Q8)`. Execute every original command in each sequence (7 sequences, 60 transitions). The retained historical cases are assertions/diagnostics from the old artifact, not selected from this run; record each raw gap and strict production classification. Require/report both directions separately (historical 7 production-penetrating/oracle-clear and 7 production-clear/oracle-penetrating). Exclude disagreement steps from H.2 identity totals, not from H.4/O1/O2.
- Geometry representatives: at H32 index 0, full Q10 for rays `{0,1,6,13,25,30,36,42,48,54,60,68}` (12 sequences, 144 transitions). Feature coverage includes arc convex/concave/cap across A1/A2/A3 in combination with the historical cases, both segment faces/caps and both posts.

These are targeted probes, not a probability sample. Total: 19 sequences/204 transitions.

### Pockets: all 54 sequences / 1,728 transitions

Original pocket family in original order: arcs A1/A2/A3, every `j=0…8`, both `P+` and `P−`, each complete 32-command sequence. Preserve the requirement/diagnostic for two distinct inner-surface contacts per arc. Missing contact coverage is reported as the frozen failure/limitation; do not change `j`, sign or sequence.

### Resets: 54 attempts

For the 18 unique `(ray_index,H32_heading_index)` pairs in the ray list, run all three original H.5 probes: ring at `r_i + R_h + 0.005 m`, near-penetrating at `A + r_i − 0.001 m`, centre start. Check reset legality independently with the oracle. Do not change offsets. Record all attempts and outcomes.

### H.2(c): 800 single-step candidates plus one complete 64-command schedule

- Walls/corners: all four wall labels and four corner labels, `flush` and `near`, at H32 indices `{0,1,24,28}` = 64 reset configurations × every U10 command = 640 candidates.
- Low-energy grid: `(0.75,0.75)`, `(2.25,0.75)`, `(0.75,2.25)`, `(2.25,2.25)` at H32 indices `{0,1,24,28}`, exactly `battery_j=1065.6 J`, all ten U10 candidates = 160. Every reset supplies all six original D-058 options: position, station centre, heading, battery, temperature, charger latch. Use the unchanged oracle reset legality/production reset outcome.
- One full sequence of 64 commands `U10[i % 10]` from `(0.75,0.75)`, heading 0, with all six frozen default reset options. Keep D-060 execution and inherited D-058 lockstep eligibility/comparison/STOP semantics distinct. Independently check endpoint wall-plus-obstacle displacement decomposition at every executed D-060 transition and each compared D-058 transition. Report actual counts; do not call fewer than 64 comparisons “64-step identity.”

Denominators are 800 candidate probes and 64 scheduled commands before reset rejection, eligibility and identity exclusions; do not imply full H.2(c) coverage.

### Required selected-case checks

For every selected D-060 endpoint (ray, pocket, single-step and 64-command work):

- Independently compute all four rotated rectangle corners at the exact executed yaw and check all room walls using only `τ(3.0)=64·2⁻⁵²·3 = 4.263256414560601e-14 m`. Never use production `_extent` as sole verification, repair corners, or modify room law.
- Independently reconstruct wall-stage plus obstacle-stage endpoint displacement and compare with the total D-060 displacement; preserve reconstruction identities.
- Retain original H.2 identities, strict production-vs-oracle boundary-sign accounting, original D-058 comparator fields/eligibility, and reset legality.
- For obstacle-resolved steps, retain the independent full 3,600-direction oracle scan and unchanged O1/O2 thresholds. Retain frozen H.6's 63 ordered samples against original symbolic `B`; no reduction, vectorization, tolerance change or sample skipping.
- Retain H.4 endpoint legality, chord/no-crossing, contact/push-out/residual and H.2c checks where applicable. Exact counts and exclusions must appear in the result.

The exact A1 cap/witness, equal-clearance S1 witnesses, and two-distinct-inner-arc-contact fixtures remain in focused software tests where defined. They are not additional official trajectory identities or proof of full H.4/H.6 coverage.

## Coverage and interpretation limits

Original ray matrix: `76 × 32 × 11 = 26,752` ray sequences (233,472 transitions). This protocol runs 19 and omits **26,733**. It runs all 54 pockets (1,728 transitions); selected ray/pocket work is 1,932/235,200 = **0.8214% of transition count**, not runtime or failure-detection probability. Also run 800 H.2(c) candidates, one 64-command schedule and 54 resets; report these separate denominators. Most full H.2(c), H.1–H.8/O1/O2 breadth is omitted. Results cannot establish universal contact behavior, rare failure rates, full conformance or acceptance.

## Timing and two-copy plan

Before timing, freeze/commit protocol and adapter; execute software tests, independent strict typing, protected-source/hash checks, and isolated-environment checks. One fixed, non-result-tuning preflight only: seven historical ray trajectories, twelve full Q10 geometry trajectories, six `j=0` pocket trajectories (both signs on each arc), and the entire reduced H.2(c) bundle including the 64-command sequence. This is 396 ray/pocket transitions plus fixed transplant/reset cases. Invoke the adapter with `--preflight`; output must say `D060_REDUCED_PREFLIGHT_ONLY` and must not assert full pocket coverage. Preserve any selected-check failure; no result-directed modification. Record wall/CPU/RSS, runtime, dependencies, platform and exact commands. Estimate each full copy as `10 ×` preflight duration plus 25% concurrency margin. If over two hours per copy or unsafe memory, STOP and report; do not shrink the protocol.

Run both complete copies only if resources are safe: independent internally serial official checkout and fresh `git archive` of the exact same committed source SHA, same Python/NumPy/platform and immutable locked dependencies; each has separate source tree, output, log, temp and cache. No concurrent environment sync, threads, worker pool, shared mutable Git/cache writes, Pymunk competition, or in-trajectory refactor. Require at least two CPU slots and available memory comfortably exceeding twice measured peak RSS plus a 4 GB system reserve. Recheck host/load and isolation immediately before launch. If concurrency is unsafe or source/environment differs, STOP/report; sequential only within the same agreed overnight budget. No guaranteed morning finish.

Keep both JSONs, raw archive extraction, exact commands, stdout/stderr, host/environment snapshots, timing, counters, case inventory, exit statuses, sizes and SHA-256 receipts in the task evidence directory. Compare JSONs with bytewise `cmp`; retain both through independent review. Any failure, missing case/output, source mismatch, non-finite value, archive mismatch, environment drift, byte difference or unsafe resources is retained and escalated, with no rescue rerun or tolerance/sample changes.

## Known limitations to disclose

The underlying candidate carries a broad mypy `ignore_errors` override for exactly `aweform.d060` and `aweform.d060_oracle`; old green CI does not establish strict typing for those modules. Do not alter that inherited override here. The new adapter must independently pass `mypy --strict src/aweform/d060_reduced.py` without new suppression. The old full matrix, artifact, protected bytes and CHANGES REQUIRED history remain unchanged.
