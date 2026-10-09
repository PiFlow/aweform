# D-060 — V0.5 round interior-obstacle substrate conformance

## Frozen protocol and provenance

- **Lane / scope:** Development, evaluator-only D-060 substrate conformance under ADR-0020. No seeded lifetimes, Level-1 floor, D-055 execution, five-seed study, visualizer, controller, sensor, learner, planner, or world-model changes.
- **Authorization:** #213 PROPOSAL_VERSION 1, Part A; Sol PASS at [#213 comment 5993909367](https://github.com/PiFlow/aweform/issues/213#issuecomment-5993909367), with the exact-base handoff at [#197 comment 5993914622](https://github.com/PiFlow/aweform/issues/197#issuecomment-5993914622).
- **Authorized base:** `e11ad91b3b7c649185bd1298ad5f3a791be571f8`.
- **Protocol:** `d060-v05-round-interior-obstacle-substrate-v1`; schema `d060-v1`; artifact schema `D060-1`.
- **Executed source/protocol SHA:** `beb9012b0fa604fef4dc7b126a171f9a8baf8ee0` (implementation, evaluator, and tests; record and artifact are generated afterward).
- **Official generation command:** `uv run python -m aweform.d060 --output development/D-060-v05-round-interior-obstacle-substrate.json --executed-commit-sha beb9012b0fa604fef4dc7b126a171f9a8baf8ee0`.
- **Artifact:** `development/D-060-v05-round-interior-obstacle-substrate.json`; 132,389 bytes; SHA-256 `6c16982186dd9fd588012f1c0a552ef001e5acfbc34a0a923b194ae64c76479f`.
- **Determinism / H.7:** fresh `git archive` regeneration of the executed SHA, using the same Python and NumPy environment, compared byte-for-byte with the official artifact. The archive regeneration wrapper exited 0; an independent `cmp -s` also exited 0. Both files have SHA-256 `6c16982186dd9fd588012f1c0a552ef001e5acfbc34a0a923b194ae64c76479f` and are 132,389 bytes.
- **Environment:** recorded in the conformance JSON (`environment.python`, `environment.numpy`, and `environment.platform`).
- **Frozen execution:** no RNG; all headings, features, commands, obstacle order, and probe iterations follow the exact order in the approved proposal. The dense oracle uses 3,600 directions, march floor `1e-13 m`, and fixed `ε_o = 1e-4 m`.

## Implementation boundary

D-060 is a declared **endpoint-only kinematic idealization** with frictionless rigid obstacle projection. It keeps the D-045/D-058 observation, action envelope, energy and thermal bookkeeping, full unwrapped yaw, and room stage. An obstacle correction projects the unconstrained endpoint at the executed heading using the finite candidate construction in ADR-0020 §C.1. The three contact records are evaluator-only and absent from the observation and `info`.

Intermediate penetration between endpoints is disclosed and characterized with the frozen `k/64` arc samples. This does not establish continuous collision freedom or hardware contact fidelity. The D-055 stall predicate remains structurally dormant at obstacles under wheel-slip semantics. Evidence from D-045 through D-059 remains bound to its original substrates.

The approved `τ_c = 1e-12 m` and the inherited room-corner verification allowance `tau(3.0) = 4.263256414560601e-14 m` are used only in their declared checks. The finite candidate distance filter from ADR-0020 Lemma 2 is used to discard candidates farther than `R_h + r_i + τ_c` from the unconstrained endpoint before gap evaluation; no other numerical accommodation is used.

## Results

**Record verdict: `D060_SUBSTRATE_CONFORMANT`.** H.1–H.8, O1/O2, pocket coverage, and H.7 byte identity pass. The conformance JSON contains the full precision layout metrics, per-obstacle/per-class/per-sequence/per-command contact counts, H.2 boundary cases, H.2(c) rejected-start list, H.6 maxima and attaining cases, and H.4 projection summary.

1. **H.1 protected byte identity — PASS.** All 18 protected modules match the authorized base byte-for-byte. Their SHA-256 digests are included in the artifact.
2. **H.2 obstacle-free identity — PASS.** Ray/pocket lockstep and fresh-reset single-step comparisons match D-058 exactly on their eligible steps. H.2(c) reports accepted transplanted starts, single-step and 64-step lockstep comparison counts, and each rejected D-058 start with its independent oracle gaps. A production/oracle strict-sign disagreement is recorded with its raw gaps and executed classification and is excluded only from H.2 eligibility; it remains subject to H.4 and O1/O2. The artifact lists every such case.
3. **H.3 layout invariants — PASS.** The artifact records the frozen layout equality and full-precision dock, wall, pairwise, default-pose, hull, opening, inner-radius, and diagonal metrics. Every pairwise and room-wall gap exceeds `2R_h`; the default pose is legal.
4. **H.4 contact conformance — PASS.** Every obstacle-resolved step passes endpoint legality against all seven obstacles, the inherited room-corner allowance, exact yaw, wheel/encoder/effort/energy identities, idempotence within `τ_c`, the single-constraint check, no-crossing geometry, step-kind displacement bounds, universal push-out, and convex push-out where required. The artifact reports exact and within-`τ_c` idempotence counts, the minimum no-crossing margin, descriptive largest arc push-out, and contact counts by obstacle, class, sequence, and command index. O1 passes; O2's worst excess is within the frozen `1e-4 m` bound. The dense-sample oracle is a check, not a proof.
5. **H.5 reset — PASS.** All 2,432 ring starts and all 4,864 frozen penetrating reset starts have the required outcomes. The default pose and the D-058 reset-option rejection cases pass.
6. **H.6 intermediate penetration — PASS.** The artifact reports maxima by obstacle and contact class, each attaining case, and nonzero-sample step counts. Every sample is within the frozen bound `B = 0.07292419035931953 m`.
7. **H.7 determinism — PASS.** The corrected source was archived with `git archive --format=tar beb9012b0fa604fef4dc7b126a171f9a8baf8ee0 | tar -xf - -C .d060-h7-scratch/beb9012`. From the worktree root, with `scratch=.d060-h7-scratch/beb9012` and `git_dir=$(git rev-parse --absolute-git-dir)`, the archive run was `PYTHONPATH="$scratch/src" GIT_DIR="$git_dir" uv run python -m aweform.d060 --output "$scratch/regenerated.json" --executed-commit-sha beb9012b0fa604fef4dc7b126a171f9a8baf8ee0`, with stdout/stderr redirected to `$scratch/logs/stdout.log` and `$scratch/logs/stderr.log`; its wrapper returned exit code 0. Independent `cmp -s development/D-060-v05-round-interior-obstacle-substrate.json .d060-h7-scratch/beb9012/regenerated.json` returned exit code 0. Both outputs are 132,389 bytes and have SHA-256 `6c16982186dd9fd588012f1c0a552ef001e5acfbc34a0a923b194ae64c76479f`. The JSON retains `H.7_determinism: REGENERATION_REQUIRED`, the deterministic pre-comparison marker emitted by the runner; the completed H.7 acceptance result and evidence are recorded here. Python 3.14.7, NumPy 2.5.2, and platform `macOS-26.6.2-arm64-arm-64bit-Mach-O` were used for both runs.
8. **H.8 numerical residual — PASS.** The artifact records the worst accepted-candidate residual, including idempotence re-applications; it is no greater than `τ_c`.

## Claims and disposition

No sensor, observation, controller, energy, thermal, or D-055 change was made. No Level-1, D-055, lifetime, five-seed, or behavioural evidence was produced. The oracle is a dense-sample check rather than a proof. This conformance record characterizes an endpoint-only substrate and makes no claim of continuous collision fidelity or hardware-valid contact.

**disposition:** CONTINUING.
