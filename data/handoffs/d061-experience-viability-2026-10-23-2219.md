# D-061 continuation handoff

**Created:** 2026-10-23 22:19 local time  
**Branch:** `fm/d061-experience-viability`  
**Implementation HEAD before this handoff-only commit:** `71f7de10bf71ebce30675452ed778014c20ed092`  
This handoff file is committed as a documentation-only follow-up; on resume, confirm the exact current HEAD with `git rev-parse HEAD`. The worktree is clean after that commit.  
**Pipeline state:** the first `done` status handoff has already been appended; no-mistakes/PR pipeline is pending Firstmate's next instruction. Do not restart implementation or amend commits before following that instruction.

## Completed work

D-061 is implemented, executed and recorded. The exact runner/protocol commit used for the official result is `0b96d83c0bf5cbd1fbf07066bdd993eee08c05b3`; later commits add only the final shared-renderer-preserving adapter/tests, artifacts, record and index entry. The official execution ran seeds `22053, 22054, 22055`, arms U/L/P, 120,000 transitions per arm (1,080,000 transitions total), under 600-second CPU and wall guards. All nine runs completed, had zero reward/empty info/eight float32 observations/legal wheels, and were horizon-censored rather than terminated.

Fixed protocol details (do not change without explicit authorization): D-045 physics and D-052 Level-1 return/charge/recovery were unchanged; each arm/lifetime had a fresh zero-weight 528-parameter D-046 learner and the same D-053 seeded proposal fixture. U is unchanged D-053→D-052 with zero-influence learner updates. L uses the maximum predicted `delta_beacon_forward` for the same three legal D-053 wheel candidates. P uses fixed cyclic prediction/action permutation `(1, 2, 0)`. Warm-up is 564 actual transitions; L/P query all three candidates every fourth later actual transition (29,859 slots / 89,577 predictions per arm), exactly matched; apply a selection only when Level 1 is NORMAL and the unchanged return condition is inactive. A score spread `<=1e-12` falls back to the exact U proposal. Updates use only prior actual visible observation, actual executed wheel pair, and next actual visible observation. No evaluator truth/reward/new sensor, extra RNG, replay buffer, or Level-1 change.

Independent U identity replay used `run_d053_lifetime` for all three seeds at 120,000 transitions. Saved U sampled frames matched D-053 proposals, executed wheels, mode, energy, contact, pose and heading exactly (1,202 / 1,205 / 1,206 frames); mode counts and preemptions also matched.

Key descriptive outcome: L had two D-052 charging cycles per seed; U had 0/1/1, P 0/0/1. L changed the U proposal on 18,141–18,262 of 20,435–20,441 realized interventions; P changed it on 4,580–5,266 of 21,068–25,141. Every selected action was in prior actual action support. L moved about 1.4 km per run and spent about 37.6k transitions in CHARGE; U/P moved less. L final energy was lower than U on seeds 22054–22055, so this is causal behavioural divergence with a viability trade-off, not a claim of general learned competence. Full details are in the D-record.

## Files in the committed branch

- `src/aweform/d061.py` — bounded runner, U/L/P mechanics, guards and compact artifact writer/CLI.
- `src/aweform/d061_visualizer.py` — D-061 saved-frame adapter and offline side-by-side index generator using the canonical shared renderer. The protected `src/aweform/development_visualizer.py` has been restored to the authorized base content; do not edit it.
- `pyproject.toml` — `aweform-run-d061` and `aweform-export-d061-html` entry points.
- `tests/test_d061.py` — seed/reservation, fresh zero initialization/update, warm-up identity, equal L/P query budget, basic per-transition guards and canonical saved-frame adapter tests.
- `development/D-061-v05-experience-viability.md` — final D-record; `development/INDEX.md` has the D-061 row, added only after real execution.
- `development/D-061-v05-experience-viability.json` — official 3-seed artifact, 5,848,171 bytes; SHA-256 `b9a93ff4ce2436255b61890b3b12b146f28bb72e366d40e4965833fde12122a2`; embedded hash excluding self-hash `f4241bfb99b8cc7a0bf148051e4fc6aae48417ad8d57238d08932e8e84150ab6`.
- `development/D-061-v05-experience-viability-invalidated-read-budget.json` — preserved but excluded earlier seed-22053 run, SHA-256 `039d4af8229dc259791444f1d6ac4f90b776364d812c973e83ac617208740559`. It used an unequal realized candidate-read budget/redundant P read; do not pool it.
- `development/D-061-v05-experience-viability-u-identity-audit.json` — compact independent D-053 U identity result, SHA-256 `625d09d65a4dbab5480eba43104f7ce6f54bb89b79dbb97df7cc2886c6124463`.
- `development/D-061-v05-experience-viability-replay.html` plus neighboring `...-U.html`, `...-L.html`, `...-P.html` — offline side-by-side replay from saved seed-22053 frames. Open with `open development/D-061-v05-experience-viability-replay.html`. Combined execution/invalidated/identity/replay artifacts are 9,390,710 bytes (<20 MiB).

An initial 9-arm attempt at `696a72ebbf06c9a675ab6c9ee66dbadae543195b` was stopped before output; it produced no result and was not used. A completed one-seed run at `1b5ae406ca45291c807e8b45b863c8530d728e35` was superseded for unequal candidate-read budgeting and preserved separately. The final official execution was rerun under the corrected fixed-slot budget at `0b96d83c0bf5cbd1fbf07066bdd993eee08c05b3`.

## Validation state

- `ruff check src/aweform/d061.py src/aweform/d061_visualizer.py tests/test_d061.py`: passed.
- `mypy src/aweform/d061.py src/aweform/d061_visualizer.py`: passed.
- Focused D-061/shared visualizer tests: `95 passed`.
- Four protected-source guards from D-056–D-059: `4 passed` after restoring the shared visualizer.
- A full pytest run before that restoration produced `1,213 passed, 3 skipped, 4 failed`; all four failures were protected-source checks against the temporary `development_visualizer.py` edits. Those edits were reverted; focused tests and all four guards then passed. Full pytest was not rerun after the correction. No-mistakes/CI remains the next validation gate.
- `no-mistakes doctor` passed at setup (daemon running). Do not start `/no-mistakes` until Firstmate instructs. When instructed, use the Firstmate contract: `--intent` is only the Captain-intent section text, never pass `--yes`, respond to gates rather than fixing during an active run, escalate all ask-user findings verbatim in the specified snapshot/status format, and do not push/merge. The pipeline owns push/PR. Firstmate/Flow controls merge.

## Remaining actions

1. Read/acknowledge any new steering inbox messages in numeric order; this message `001.msg` should be moved to the task inbox `handled/` once this handoff is saved.
2. Wait for Firstmate's next instruction and drive the no-mistakes pipeline as specified; do not create another implementation branch or alter the clean committed tree pre-pipeline.
3. After a PR is opened by the pipeline, the remaining Captain-requested issue deliverable is a comment on https://github.com/PiFlow/aweform/issues/236 with the actual run summary, exact runner SHA `0b96d83c0bf5cbd1fbf07066bdd993eee08c05b3`, official artifact SHA-256 above, and visualization entry path/command. Use `gh-axi` (not `gh`) and include the real PR URL as printed by the forge if relevant. Do not claim the PR exists until it does.
4. After CI green, follow Firstmate's exact PR/draft verification and final status protocol. Never merge; Flow alone authorizes merging.

## Boundaries that remain in force

This is Development only, not EXP evidence. Preserve the accepted ADR-0010 provenance closure, ADR-0017 eight-channel/bilateral-wheel contract and unchanged D-045 substrate, and ADR-0018's protected Level-1 preemption. Do not add a sensor, reward, new output, architecture redesign, new durable information/plasticity/safety permission, obstacle/Pymunk work, LLM/RL/PPO/JEPA, replay consolidation, learned Level-1 override, external service/networking, or changes to D-058/D-059/D-060/#232. No hidden coordinates, heading, geometry, labels, future outcome, evaluator metric or seed identity may enter learning/scoring. Preserve D-061 null/negative results and distinguish all charging/docking competence as innate Level 1. Any new durable boundary would require a stop and separate ADR/review path.

**Open scientific decisions:** none. The three-seed result is descriptive and does not authorize tuning, EXP promotion, or successor capabilities.
