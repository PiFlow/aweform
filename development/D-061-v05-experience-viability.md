---
type: Development Record
id: D-061
lane: Development
status: complete
---

# D-061 — V0.5 experience-driven elective wheel behaviour

**Question.** Can a fresh, zero-weight D-046 action-consequence model, updated only from actual within-lifetime observations and executed wheel commands, alter elective Level-1-NORMAL behaviour and the resulting trajectory/energy/charging outcomes in the unchanged V0.5 world?

**Classification.** Descriptive causal organism intervention with a shadow-learning baseline and a fixed-association negative control. This is Development, not confirmatory evidence. No consciousness, emotion, subjective experience, biological life, or generalized competence is inferred.

## Frozen execution

- Authorized base: `c9280554268a789949b73babdd40d5f363649761` (`origin/main` read before work). Executed runner/protocol SHA: `0b96d83c0bf5cbd1fbf07066bdd993eee08c05b3`.
- Legal reused D-053 development seeds: `22053, 22054, 22055`; validated against the formal-reservation guard. Each arm ran 120,000 transitions per seed (1,080,000 total). Every run was horizon-censored, not organism-terminated.
- Each independent arm/lifetime reset to body/station `(0.5, 0.5)`, heading `0`, 80% battery, ambient temperature and false charger latch, with fresh D-052 and fresh 528-weight D-046 predictor initialized to zero. Physical initial contact at the centered dock was present; this initial condition was not counted as a contact acquisition or D-052 charging cycle. D-045 physics, D-052 Level-1 logic and D-053 seeded proposal stream were unchanged.
- **U:** unchanged D-053 proposal → D-052 arbitration; D-046 shadow model updated on each actual transition but had zero influence. **L:** same updates and action candidates; on scheduled query slots, rank candidates by predicted `delta_beacon_forward` and use the maximum only when D-052 is NORMAL and energy is above its unchanged return condition. **P:** same predictor, update schedule, query slots and candidate set as L, but score/action associations use the fixed cyclic permutation `(1, 2, 0)`.
- All arms used the exact D-053 legal action alphabet: forward `(+M,+M)`, left `(-M,+M)`, right `(+M,-M)`, `M=0.6457718232379019 rad`. The first 564 actual transitions were warm-up. L/P queried all three candidates every fourth subsequent actual transition (29,859 slots; 89,577 candidate predictions per arm, exactly equal); actions were applied only when Level 1 was NORMAL. L/P realized different numbers of NORMAL interventions because their trajectories and Level-1 mode opportunities diverged. A maximum score spread `<=1e-12` deterministically fell back to the exact U proposal; no added RNG.
- Every plastic update used only prior actual 8-channel observation, actual D-052-executed wheel pair, and next actual visible observation. The D-046 frozen transform and NLMS update were reused. No retained replay/buffer, reward, evaluator truth, coordinates, contact diagnostics, or future values entered the learner or score. D-052 remains the sole unchanged Level-1 return/charge controller and cannot read learner state.
- Per-transition checks passed for all nine runs: `reward == 0.0`, `info == {}`, eight `float32` channels, and legal bilateral wheels. Each learner performed 120,000 updates and 120,000 non-zero updates. Candidate action support was present for every selected intervention. Wall and CPU guards were each fixed at 600 seconds; all nine runs completed within the guard.

## Results

Energy is normalized battery fraction. “Cycles/charge steps” are D-052 charging cycles and transitions in CHARGE mode; those are innate Level-1 behaviour, not learned competence. Movement is evaluator-only accumulated body-centre displacement. Mode counts, state digests, complete sparse saved frames, intervention counts and checks are in the compact JSON artifact.

| Seed | Arm | NORMAL / RETURN / CHARGE transitions | Level-1 preemptions | Min → final energy | D-052 cycles / CHARGE steps | Movement (m) | Action-change rate | Scheduled NORMAL interventions / differed from U proposal |
|---:|:---:|---:|---:|---:|---:|---:|---:|---:|
| 22053 | U | 71,215 / 48,785 / 0 | 48,785 | .0626 → .0626 | 0 / 0 | 291.7 | .1244 | 0 / 0 |
| 22053 | L | 82,303 / 54 / 37,643 | 37,697 | .1994 → .2880 | 2 / 37,643 | 1,438.3 | .3765 | 20,435 / 18,187 |
| 22053 | P | 86,582 / 33,418 / 0 | 33,418 | .1058 → .1058 | 0 / 0 | 204.6 | .1528 | 21,504 / 4,618 |
| 22054 | U | 101,133 / 38 / 18,829 | 18,867 | .1992 → .5322 | 1 / 18,829 | 433.7 | .1792 | 0 / 0 |
| 22054 | L | 82,310 / 50 / 37,640 | 37,690 | .1995 → .2966 | 2 / 37,640 | 1,424.8 | .3784 | 20,436 / 18,141 |
| 22054 | P | 84,839 / 35,161 / 0 | 35,161 | .1009 → .1009 | 0 / 0 | 217.7 | .1513 | 21,068 / 4,580 |
| 22055 | U | 101,144 / 32 / 18,824 | 18,856 | .1994 → .5596 | 1 / 18,824 | 391.9 | .1791 | 0 / 0 |
| 22055 | L | 82,333 / 36 / 37,631 | 37,667 | .1994 → .2881 | 2 / 37,631 | 1,433.0 | .3789 | 20,441 / 18,262 |
| 22055 | P | 101,130 / 40 / 18,830 | 18,870 | .1992 → .6969 | 1 / 18,830 | 246.2 | .1769 | 25,141 / 5,266 |

L changed the selected U proposal on 18,141–18,262 of its 20,435–20,441 realized interventions; P did so on 4,580–5,266 of 21,068–25,141. Every selected action in both arms was in prior executed-action support. Physical contact-acquisition counts (including incidental NORMAL contacts) were U `0/1/2`, L `9/6/6`, and P `0/0/1` for seeds 22053/22054/22055; these are distinct from completed D-052 charging cycles. L had 2 D-052 charging cycles on each seed; U had 0/1/1 and P had 0/0/1. All nine runs were censored at 120,000 transitions, with no D-045 termination.

**Surprised by.** L produced a large, repeatable action/trajectory divergence and two Level-1 charging cycles on each seed, including seed 22053 where unchanged U and permuted P reached RETURN but failed to dock. Yet this was not a uniform final-energy advantage: on seeds 22054–22055 U ended at .5322/.5596 versus L .2966/.2881, while P ended at .6969 on seed 22055. L also moved roughly 1.4 km per run versus 0.2–0.4 km for U/P and spent about twice as many transitions in CHARGE. The result is a real model-mediated behavioural/viability trade-off, not evidence that L learned a generally superior energy strategy. Innate return/docking/charging remains Level 1 throughout.

**Limitations.** Three reused development seeds and one fixed horizon are descriptive support only. No fresh holdout, inferential test, or EXP claim. L's single organism-visible score channel (`delta_beacon_forward`) is an explicitly designed selection rule; the result concerns learned predictions used under that rule, not autonomous goal formation. L/P intervention counts naturally differ with NORMAL eligibility despite identical fixed candidate-query and update budgets. Support means that the exact selected legal wheel pair occurred previously in the same lifetime; it does not establish accurate counterfactual predictions. The 120k administrative horizon is not death and does not characterize later cycles. Evaluator movement/pose and returned simulator summaries are diagnostics only.

## Artifacts and provenance

- Official compact execution artifact: [`D-061-v05-experience-viability.json`](D-061-v05-experience-viability.json), 5,848,171 bytes, SHA-256 `b9a93ff4ce2436255b61890b3b12b146f28bb72e366d40e4965833fde12122a2`; embedded SHA-256 excluding its self-hash field: `f4241bfb99b8cc7a0bf148051e4fc6aae48417ad8d57238d08932e8e84150ab6`. All committed D-061 execution, preserved invalidated execution, replay, and baseline-identity artifacts total 9,483,929 bytes (<20 MiB).
- Side-by-side seed-22053 saved-frame replay entry: [`D-061-v05-experience-viability-replay.html`](D-061-v05-experience-viability-replay.html), 1,190 bytes, SHA-256 `8cc98ae87a073db170599d41160a84abcd4b6af68948a8d8ae27bdfdb2c5b9b8`. Open with `open development/D-061-v05-experience-viability-replay.html`. It places U/L/P independently playable offline renderings beside each other. The three arm pages were generated from saved frames through `aweform.d061_visualizer.adapt_d061_trace` and the canonical shared HTML renderer; they do not rerun the organism. The evaluator-only poses are presentation diagnostics.
- Independent unchanged-baseline identity audit: [`D-061-v05-experience-viability-u-identity-audit.json`](D-061-v05-experience-viability-u-identity-audit.json), 620 bytes, SHA-256 `625d09d65a4dbab5480eba43104f7ce6f54bb89b79dbb97df7cc2886c6124463`. A separate `run_d053_lifetime` replay matched all saved U-arm action proposals, executed wheel pairs, modes, energy, contacts, positions and headings at 1,202/1,205/1,206 retained frames for seeds 22053/22054/22055; mode counts and preemptions also matched exactly.
- Exact executed SHA `0b96d83c0bf5cbd1fbf07066bdd993eee08c05b3` is in branch history. An earlier completed seed-22053 run at `1b5ae406ca45291c807e8b45b863c8530d728e35` is preserved as [`D-061-v05-experience-viability-invalidated-read-budget.json`](D-061-v05-experience-viability-invalidated-read-budget.json), SHA-256 `039d4af8229dc259791444f1d6ac4f90b776364d812c973e83ac617208740559`. It is excluded: audit found a redundant extra P scoring read and a per-arm eligible-decision schedule that did not equalize realized candidate-query budgets. The corrected fixed-slot protocol above was then executed at the official SHA; no superseded output is pooled into this result. An earlier all-seed trial at `696a72ebbf06c9a675ab6c9ee66dbadae543195b` was interrupted before completion and before producing an artifact; no result from it was used.

**`surprised_by`:** Experience-informed actions materially changed the trajectory and enabled repeated Level-1 charging on all three seeds, but with much greater movement/charging expenditure and lower final energy than U on two seeds. The permuted control also retained innate baseline charging on seed 22055.

## Validation

`ruff check` and strict mypy passed for the runner and saved-frame adapter. Focused D-061 plus shared-visualizer tests passed (`95 passed`); the four D-056–D-059 protected-source guard tests also passed on the final renderer-preserving tree. A full-suite run reached `1,213 passed, 3 skipped` but reported four protected-source guard failures while a temporary D-061 adapter had been placed in the protected shared renderer; that change was reverted and the adapter moved to `aweform.d061_visualizer`. The four guards and focused suite passed after correction; the full suite was not rerun after that correction. CI remains pending.

**`disposition`:** `CONTINUING` — preserve the positive causal divergence and mixed viability trade-off; no tuning or EXP promotion is authorized by this record.
