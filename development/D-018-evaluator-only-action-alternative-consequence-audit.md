# D-018 — Evaluator-only action-alternative consequence audit

- **id:** D-018
- **date:** 2026-09-01
- **authoritative_base_sha:** `3ad3d93ad7764f938e16fefc8e1536a414b7d9bc`
- **accepted_executable_sha:** `ab0868db89f3b22d84b0d5016f14b806df013bc5`
- **development_seeds:** `18359, 18360, 18361`
- **horizon:** `1000` transitions per uninterrupted lifetime
- **disposition:** `CONTINUING`

The machine-readable JSON artifact is the numerical source for this record:
[`D-018-evaluator-only-action-alternative-consequence-audit.json`](D-018-evaluator-only-action-alternative-consequence-audit.json).

## Question and scope

D-018 asks how accurately the unchanged D-013 84-weight action-conditioned
consequence learner predicts one-step visible consequences for all four action
alternatives at organism-visible states visited by the unchanged D-014
autonomous regulation loop. The real D-014 action remains selected first and
remains the only physical action. The three unselected actions are evaluated
only by isolated simulator branches.

This is ordinary D-lane descriptive work. It does not establish counterfactual
knowledge, a world model, planning, action-selection benefit, intelligence,
consciousness, emotion, subjective experience, genuine life, or biological
metabolism. No learned prediction influenced behaviour.

## Provenance and accepted execution

The synchronization gate verified both `origin/main` and live GitHub
`refs/heads/main` at the authoritative base SHA before implementation. The
existing D-017 branch was not reused. The fresh branch started from that
exact main commit.

Before execution, the canonical `validate_exp003_development_seeds` guard
accepted exactly `(18359, 18360, 18361)`. The D-018 guard accepts no other
development seed and preserves the formal reservation guard. No formal seed
was used.

The implementation and focused tests were first committed at
`99c1625683c2c03cace89d57766bbc8320da7936`. Its substantive artifact was
invalidated before any corrected rerun because a reporting field counted the
84-weight snapshot as 63. The invalidated artifact was preserved unchanged at
`/private/tmp/aweform-d018-invalidated-99c1625.json` with SHA-256
`9a5bad9a41d1fbfa7d64e5ce8ed07abb139d02859b3e75fd110e1b636b167de6`.

The reporting correction was committed at the accepted executable SHA
`ab0868db89f3b22d84b0d5016f14b806df013bc5`. It did not change the learner,
controller, ecology, seeds, horizon, support definition, branch procedure,
metrics, or interpretation rules. After a clean validation and a repeated
seed-policy check, the corrected substantive probe was executed once:

```text
MPLCONFIGDIR=/private/tmp/aweform-mpl UV_CACHE_DIR=/private/tmp/aweform-uv-cache \
uv run python -m aweform.d018 \
  --seeds 18359 18360 18361 \
  --horizon 1000 \
  --executed-commit-sha ab0868db89f3b22d84b0d5016f14b806df013bc5 \
  --output development/D-018-evaluator-only-action-alternative-consequence-audit.json
```

The accepted artifact is the corrected run only. No learner, seed, support,
procedure, or metric tuning occurred after inspecting the substantive result.

## Causal and provenance boundary

### PROGRAMMED

- Unchanged `D014Controller`, including inherited D-011 modes and policy RNG
  semantics.
- Unchanged `D002ThermalStationEnv` and EXP-003 ecology, energy/thermal
  dynamics, beacon, contact semantics, action costs, and horizon handling.
- Unchanged `d013.D013ActionConsequencePredictor`, zero initialization,
  normalized-LMS rule, learning rate `0.5`, and exactly 84 scalar weights.
- Unchanged action set: `WAIT`, `TURN_LEFT`, `TURN_RIGHT`, `MOVE_FORWARD`.
- Exact evaluator branch cloning and one canonical `D002ThermalStationEnv.step`
  call per candidate action.

### ORGANISM-VISIBLE

- Normalized energy.
- Beacon left, forward, and right.
- Physical `charging_contact`.
- Normalized thermal state.
- The organism's own physically executed action for the real learner update.
- The actual next observation after the real transition.

No coordinates, heading, distance, dock geometry, new sensor, future
observation, seed identity, horizon, evaluator label, or branch outcome was
provided to the organism or learner features.

### LEARNED

Only the unchanged 84 D-013 weights were learned. At each real transition,
the learner updated exactly once from the current real `D011Observation`, the
physically executed action, and the actual real next `D011Observation`.
Alternative outcomes never entered the learner update, features, retained
state, controller, policy RNG, or real environment.

### EVALUATOR-ONLY

- Four pre-update predictions from the same current visible observation.
- Isolated one-step alternative observations, deltas, and
  termination/truncation labels.
- Per-candidate errors, zero-change comparator errors, action/contact/support
  stratification, raw rows, exact support registry, and event classes.
- Coordinates, headings, real/reference traces, RNG-state comparisons, and
  equality checks.

The exact prior support key is the complete current visible state values in
Python float order `(energy, beacon.left, beacon.forward, beacon.right,
charging_contact, thermal)` plus the candidate action. There is no rounding,
epsilon, distance, nearest-neighbour radius, or similarity matching. Only a
physically executed current-state/action pair is added after the real
transition. Counterfactual branches never add support.

## Exact isolation checks

For every seed, the reference is an otherwise identical D-014 plus D-013
shadow run without counterfactual branches. The accepted artifact reports
`true` for every seed and pooled equality field:

- exact transition count and termination/truncation;
- exact actions and action counts;
- exact controller modes and mode entries;
- exact positions and headings on every recorded real frame;
- exact energy, thermal, and charging contact values;
- exact departures, exits, SEEK/reacquisition summaries, and completed cycles;
- exact final 84 predictor weights;
- exact final real RNG states;
- unchanged real RNG state before and after every isolated branch;
- exact equality between the selected-action branch and the real next visible
  observation, termination, and truncation.

The accepted run therefore reports:

```text
all_seeds_trajectory_exact_equal = true
all_seeds_relevant_summary_fields_exact_equal = true
all_seeds_final_84_weights_exact_equal = true
all_seeds_real_rng_state_exact_equal = true
all_alternative_branch_rng_checks_unchanged = true
all_executed_action_clone_checks_match = true
```

## Behaviour and support counts

All three lifetimes reached horizon truncation at 1,000 transitions. No
lifetime terminated for energy or thermal failure.

| Seed | MOVE / LEFT / RIGHT / WAIT | Min / final energy | Max / final thermal | Departures | Exits | SEEK / reacquisitions | Cycles |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 18359 | 530 / 96 / 89 / 285 | 0.076000 / 0.302000 | 0.340000 / 0.000000 | 15 | 16 | 15 / 14 | 14 |
| 18360 | 533 / 85 / 83 / 299 | 0.152000 / 0.980000 | 0.340000 / 0.220000 | 16 | 16 | 15 / 15 | 15 |
| 18361 | 542 / 79 / 98 / 281 | 0.108000 / 0.170000 | 0.340000 / 0.010000 | 15 | 16 | 15 / 15 | 15 |

The audit contains 12,000 candidate rows: 3,000 physically executed and 9,000
unexecuted. The pooled exact prior-support distribution is:

| Prior exact support count | Raw candidate rows |
|---:|---:|
| 0 | 11,982 |
| 1 | 14 |
| 2 | 4 |

The support categories used for metrics are overlapping: `zero` means exactly
zero, `>=1` means at least one, and `>=2` means at least two. The pooled
`>=1` category contains 14 rows and `>=2` contains 4 rows. Per-seed
distributions were `18359: 0=4000`, `18360: 0=3993, 1=7`, and
`18361: 0=3989, 1=7, 2=4`. No unexecuted candidate had prior support >=2.

The per-seed final exact real state/action pair counts were 1,000, 994, and
992; pooled across the three independent lifetime registries this is 2,986.

## Prediction results

All values below are evaluator-only pre-update MAE in the form
`unchanged D-013 learned / zero-change comparator`. Raw candidate counts are
shown first. The comparator predicts zero for every visible delta; it is not a
reward and did not affect learning or behaviour.

### Physically executed versus unexecuted candidates

| Candidate class | Raw count | Delta energy MAE | Delta thermal MAE | Delta charging-contact MAE |
|---|---:|---:|---:|---:|
| Physically executed | 3,000 | 0.00343670 / 0.02338400 | 0.00198865 / 0.00701000 | 0.05905902 / 0.03133333 |
| Unexecuted | 9,000 | 0.01907705 / 0.01791267 | 0.00740946 / 0.00689778 | 0.02645105 / 0.00355556 |

The executed-action result reproduces the prior narrow pattern: lower energy
and thermal MAE than zero-change, but worse overall contact MAE. For
unexecuted actions, all three learned pooled MAEs are higher than the
zero-change comparator. This is a descriptive failure of useful pooled
alternative prediction on this support; it is not evidence that the learner
should influence action selection.

### Candidate action

Every candidate action is scored once at each of the 3,000 real states, so
each action has 3,000 rows.

| Candidate | Delta energy MAE | Delta thermal MAE | Delta charging-contact MAE |
|---|---:|---:|---:|
| `MOVE_FORWARD` | 0.01165150 / 0.02216000 | 0.00422407 / 0.00711333 | 0.13841218 / 0.04200000 |
| `TURN_LEFT` | 0.01634503 / 0.01857400 | 0.00687348 / 0.00686333 | 0.00000000 / 0.00000000 |
| `TURN_RIGHT` | 0.01639667 / 0.01857400 | 0.00669121 / 0.00686333 | 0.00000000 / 0.00000000 |
| `WAIT` | 0.01627464 / 0.01781400 | 0.00642828 / 0.00686333 | 0.00000000 / 0.00000000 |

The exact action/context and full per-seed values remain in the JSON artifact.
The zero contact comparator for turns and WAIT reflects no contact changes in
those candidate rows on this visited support; it does not establish general
contact sufficiency.

### Current contact

| Current contact | Raw count | Delta energy MAE | Delta thermal MAE | Delta charging-contact MAE |
|---|---:|---:|---:|---:|
| `False` | 7,860 | 0.00713429 / 0.01359924 | 0.00461333 / 0.00530662 | 0.02115936 / 0.00992366 |
| `True` | 4,140 | 0.03041739 / 0.03006667 | 0.00878994 / 0.01000000 | 0.06012657 / 0.01159420 |

### Prior exact support

| Support class | Raw count | Delta energy MAE | Delta thermal MAE | Delta charging-contact MAE |
|---|---:|---:|---:|---:|
| `zero` | 11,982 | 0.01518130 / 0.01929478 | 0.00605146 / 0.00692122 | 0.03428402 / 0.01026540 |
| `>=1` | 14 | 0.00569863 / 0.01114286 | 0.00708735 / 0.01000000 | 0.21679291 / 0.14285714 |
| `>=2` | 4 | 0.00535085 / 0.00500000 | 0.01081170 / 0.01000000 | 0.35256858 / 0.25000000 |

The `>=1` and `>=2` rows are tiny and overlapping support strata, not
independent evidence of stable competence. The `>=2` cell is untested for
seeds 18359 and 18360; no empty cell is assigned a performance value.

### Contact target classes

Contact target classes are exact visible deltas: `exit = -1`,
`unchanged = 0`, and `entry = +1`.

| Contact target | Raw count | Delta energy MAE | Delta thermal MAE | Delta charging-contact MAE |
|---|---:|---:|---:|---:|
| Exit | 48 | 0.01407059 / 0.01999998 | 0.01578755 / 0.01000000 | 0.84059941 / 1.00000000 |
| Unchanged | 11,874 | 0.01497525 / 0.01920718 | 0.00599340 / 0.00689321 | 0.02558878 / 0.00000000 |
| Entry | 78 | 0.04502631 / 0.03000000 | 0.00933003 / 0.01000000 | 0.91085452 / 1.00000000 |

For executed versus unexecuted event counts, executed candidates contained 46
entries, 48 exits, and 2,906 unchanged outcomes. Unexecuted candidates
contained 32 entries, no exits, and 8,968 unchanged outcomes. The unexecuted
entry-only contact subset had contact MAE `0.91302869 / 1.00000000`; its
absence of exits and small size prevent a balanced event claim. The large
unchanged class is retained explicitly and does not substitute for exit/entry
performance.

## Direct observations and conservative interpretation

Direct observations from the accepted artifact:

- The evaluator successfully scored all four actions at all 3,000 real states
  through exact isolated one-step branches.
- The real trajectory, all relevant real fields, final 84 weights, and RNG
  states matched the no-branch D-014+D-013 reference exactly.
- Only 18 of 9,000 unexecuted candidate rows had any prior exact support, and
  only 4 candidate rows had support count >=2; none of those were unexecuted
  support >=2 rows.
- The unchanged D-013 learner was better than zero-change for executed energy
  and thermal deltas, but worse for executed contact overall.
- The unchanged learner was worse than zero-change for all three pooled
  unexecuted targets. The unexecuted contact result is especially sensitive to
  the overwhelmingly unchanged class, so the entry/exit counts are reported
  separately.
- Contact events were sparse: 78 entries and 48 exits among 12,000 candidate
  rows. Unexecuted branches had no exit events on these trajectories.

The conservative interpretation is that this D-013 learner did not show
useful pooled numerical prediction of unexecuted action alternatives on this
on-policy D-014 support. The tiny exact-support strata do not rescue that
conclusion or establish a stable supported subset. The result does not decide
whether the limiting factor is experience acquisition, action/context support,
online-LMS interference, representation, omitted state, or the lack of a
distance-like support relation. D-018 did not test any such new mechanism.

The evaluator's numerical accuracy does not become learned counterfactual
knowledge merely because a value is close. Conversely, poor alternative
prediction does not authorize model-guided control, forced exploration,
action substitution, a larger learner, history, a new sensor, reverse motion,
physical morphology, altered charging semantics, or planning.

## Surprised by

The strongest surprise was the clean separation between the real on-policy
learner fit and alternative scoring: the executed rows retained the earlier
energy/thermal advantage, while the unexecuted rows were worse than the
zero-change comparator for every target despite using the same current visible
features. The exact support result was also sparse—only 18 unexecuted rows had
any prior exact state/action support and none had two or more prior examples.
The unexecuted branches produced entries but no exits, exposing a further
action/event imbalance rather than a balanced counterfactual test.

## Limitations

- One deterministic D-002/EXP-003 ecology, three development seeds, and a
  1,000-transition horizon.
- Exact support matching is intentionally strict and should not be generalized
  to a claim about nearby continuous states.
- The reference and audit runs are matched deterministic development runs,
  not independent physical systems or noisy environments.
- The 84-weight linear learner has no history and is trained on executed
  actions only; D-018 does not distinguish partial observability, omitted
  state, model capacity, or online interference.
- Contact targets are sparse and the unchanged class is large. Event counts
  and untested cells must be considered with the raw rows.
- A numerically useful unexecuted prediction, if observed in another probe,
  would still be descriptive generalization rather than supported
  counterfactual knowledge under this procedure.

## Validation

Before the accepted executable commit and corrected substantive execution:

- `uv run pytest -q`: **737 passed**, 8 existing Matplotlib warnings;
- `uv run ruff check .`: **clean**;
- `uv run mypy src --strict`: **clean**;
- `git diff --check`: **clean**.

The focused D-018 suite contains 12 tests covering the exact seed and formal
reservation guards, non-mutating alternative prediction, environment and RNG
branch isolation, selected-action clone fidelity, executed-action-only
learning, counterfactual non-entry into plasticity, exact support semantics,
reward/info boundaries, reference trajectory/weight equality, and untested
empty cells. No production visualizer or visualizer adapter was added.

No dependency changed, no existing D-014/D-013/D-002 implementation was
modified, and no durable information, sensory/plasticity, action, morphology,
charging, architecture, or safety boundary changed. No ADR was added.

## Disposition

**CONTINUING.** D-018 closes the requested evaluator audit but does not close
the counterfactual-competence gap. On the tested support, the unchanged
learner's alternative predictions were generally not useful relative to the
zero-change comparator, with sparse exact prior support and no unexecuted
support >=2. Preserve this negative result. Any future step must separately
earn an explicitly scoped experience-acquisition, learner-interference, or
representation diagnostic before learned predictions are allowed to affect
behaviour.
