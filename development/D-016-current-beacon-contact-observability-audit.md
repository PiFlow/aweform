# D-016 — Current-beacon contact-transition observability audit

- **id:** D-016
- **date:** 2026-08-31
- **authoritative_base_sha:** `185c480f34bea3db536fd80a95dea9603f5e0d1f`
- **accepted_executable_sha:** `ccbfe7d60afde0653a49905028450a537770802f`
- **development_seeds:** `18353, 18354, 18355`
- **horizon:** `1000` transitions per lifetime
- **disposition:** `CONTINUING`

## Provenance and accepted execution

PR #69 was verified merged before D-016 work began. Its reviewed HEAD
`16ff205984f0f1b7f88e349144fa15b346dd8eee` is an ancestor of the merge commit
`185c480f34bea3db536fd80a95dea9603f5e0d1f`, which is D-016's authoritative
post-merge main base. The D-016 branch was created from that base, not from
the D-015 feature branch.

The canonical validator was rerun before implementation with:

```text
UV_CACHE_DIR=/private/tmp/aweform-uv-cache uv run python -c 'from aweform.exp003_seed_policy import validate_exp003_development_seeds; seeds=(18353,18354,18355); print(validate_exp003_development_seeds(seeds))'
```

It accepted exactly `(18353, 18354, 18355)`. The exact D-016 guard accepts no
other seed and preserves the formal reservation guard.

The execution-affecting implementation and tests were committed cleanly at
`ccbfe7d60afde0653a49905028450a537770802f`. The accepted substantive run was
then executed once from that SHA with:

```text
MPLCONFIGDIR=/private/tmp/aweform-mpl UV_CACHE_DIR=/private/tmp/aweform-uv-cache uv run python -m aweform.d016 --seeds 18353 18354 18355 --horizon 1000 --executed-commit-sha ccbfe7d60afde0653a49905028450a537770802f --output development/D-016-current-beacon-contact-observability-audit.json
```

The pre-commit smoke runs and implementation-test failures were engineering
checks only and are not included as substantive evidence. The machine-readable
artifact is the source for the results below.

## Scientific question and scope

D-016 asks whether the existing directional station beacon contains enough
information, in the deterministic D-014 ecology, to reconstruct current
station-relative body-frame geometry and determine the next charging-contact
state after the already executed action.

This is an observability/representation diagnostic. It adds no organism
learner, sensor, proprioception, controller, action-selection logic, charger
mechanic, reward, or evidence-lane claim. D-016 does not test longer learning
or a 10,000-transition horizon.

## Provenance categories

### PROGRAMMED

- Unchanged `D014Controller`, including unchanged D-011 DEPART/AWAY/SEEK logic.
- Unchanged D-002/EXP-003 ecology, post-contact setup, directional beacon,
  charging radius, movement distance, action costs, energy/thermal dynamics,
  and policy RNG semantics.
- Evaluator-only analytic inverse of the existing beacon equations:
  `d = beacon_scale * sqrt(1 / signal - 1)`,
  `y = (dR² - dL²) / (4*r*sin(a))`, and
  `x = (((dL² + dR²)/2) - dF²) / (2*r*(1-cos(a)))`.
- Evaluator-only nominal contact decoder: WAIT and turns preserve current
  contact; MOVE_FORWARD applies `(x-m, y)` and tests the charging radius.
- Pre-action prediction, post-action contact/event scoring, raw signed boundary
  margins, and engineering-only motion comparison tolerance `1e-12`.
- Geometry numerical classification tolerance `1e-6`, used only to identify
  float-representation reconstruction effects, not as a scientific bin or
  acceptance threshold.

### ORGANISM-VISIBLE

- Normalized energy.
- Normalized thermal state.
- Directional beacon `L/F/R` values.
- Current physical `charging_contact`.
- The organism's own executed action, used by the evaluator to stratify the
  already selected transition.

Energy and thermal remain in the ordinary D-011 observation, but neither is
used by the station-relative analytic decoder.

### LEARNED

None. D-016 instantiates no D-013 or D-015 predictor and has no plastic state,
history, model-guided action path, or learner update.

### EVALUATOR-ONLY

- Reconstructed relative geometry and its comparison with actual evaluator
  geometry.
- Actual coordinates, used only after reconstruction for scoring/verification.
- Actual displacement and forward displacement after each physical move.
- Reduced/clipped-motion classification.
- Actual next-contact event label (`-1` exit, `0` unchanged, `+1` entry).
- Confusion/error metrics, signed margins, viability/cycle summaries, exact
  visible-state aliasing, and the post-hoc achieved-displacement check.

The reconstruction does **not** mean Aweform currently computes
station-relative coordinates. It tests what information is latent in the
existing sensory signal; reconstructed geometry never enters `D014Controller`,
D-011, any learner, policy RNG, or environment action selection.

## Viability and behaviour

All three lifetimes ran 1000 transitions, truncated at the horizon, and had no
energy or thermal termination. The accepted artifact reports:

| Seed | Minimum normalized energy | Final normalized energy | Maximum thermal | Final thermal | MOVE / LEFT / RIGHT / WAIT | Exits | Low-energy SEEK / reacquisitions | Completed cycles |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 18353 | 0.1519999951 | 0.7480000257 | 0.3499999940 | 0.0900000036 | 541 / 69 / 95 / 295 | 16 | 15 / 15 | 15 |
| 18354 | 0.1199999973 | 0.9259999990 | 0.3400000036 | 0.1800000072 | 544 / 80 / 78 / 298 | 15 | 15 / 15 | 15 |
| 18355 | 0.0240000002 | 1.0000000000 | 0.3400000036 | 0.2399999946 | 508 / 91 / 105 / 296 | 14 | 14 / 14 | 14 |

Pooled: 3000 transitions, 45 physical charger exits, 44 completed cycles,
44 successful reacquisitions, no demonstrated failed SEEK episodes, and no
horizon-censored SEEK episode. The one-exit difference is the final
horizon-censored regulation cycle on seed 18353.

## A. Beacon reconstruction accuracy

Absolute error between the beacon-only reconstruction and actual evaluator
geometry in the same pre-action body frame:

| Seed | x mean / median / max | y mean / median / max | radial mean / median / max |
|---:|---:|---:|---:|
| 18353 | 8.28e-8 / 3.74e-8 / 5.62e-7 | 1.96e-8 / 1.00e-8 / 1.36e-7 | 6.46e-8 / 2.89e-8 / 4.72e-7 |
| 18354 | 8.92e-8 / 4.16e-8 / 7.05e-7 | 2.19e-8 / 1.14e-8 / 1.45e-7 | 6.74e-8 / 3.41e-8 / 6.88e-7 |
| 18355 | 8.75e-8 / 3.68e-8 / 7.48e-7 | 2.01e-8 / 9.56e-9 / 1.48e-7 | 7.19e-8 / 2.92e-8 / 6.86e-7 |

Across all 3000 transitions, weighted mean absolute errors were `8.65e-8`
for x, `2.05e-8` for y, and `6.79e-8` radially. Global maxima were
`7.48e-7`, `1.48e-7`, and `6.88e-7` respectively. These are consistent with
recovering geometry from the current float32 organism-visible beacon values,
not exact double-precision evaluator coordinates.

## B. Nominal pre-action next-contact prediction

Pooled actual event counts were 44 entries, 45 exits, and 2911 unchanged
transitions. The nominal decoder predicted 2998 of 3000 next contacts exactly
(99.9333%):

| Actual \\ Predicted | Entry | Exit | Unchanged |
|---|---:|---:|---:|
| Entry | 44 | 0 | 0 |
| Exit | 0 | 45 | 0 |
| Unchanged | 0 | 2 | 2909 |

Entry accuracy was `44/44 = 100%`. Exit accuracy was `45/45 = 100%`.
Unchanged accuracy was `2909/2911 = 99.9313%`. There were no missed entries,
missed exits, or false-entry predictions; the two errors were false exits.

### Action × current-contact breakdown

| Current contact | Action | Count | Correct | Errors | Accuracy |
|---|---|---:|---:|---:|---:|
| false | MOVE_FORWARD | 1427 | 1427 | 0 | 100% |
| false | TURN_LEFT | 240 | 240 | 0 | 100% |
| false | TURN_RIGHT | 278 | 278 | 0 | 100% |
| false | WAIT | 0 | 0 | 0 | untested |
| true | MOVE_FORWARD | 166 | 164 | 2 | 98.7952% |
| true | TURN_LEFT | 0 | 0 | 0 | untested |
| true | TURN_RIGHT | 0 | 0 | 0 | untested |
| true | WAIT | 889 | 889 | 0 | 100% |

The event-specific and per-seed versions of these metrics are preserved in the
JSON artifact. The large unchanged class is not being used to conceal the
entry/exit result: both event classes were predicted exactly on every visited
event.

## C. Signed contact-boundary margins

The recorded margin is `nominal predicted post-action distance - charging
radius`. Values are raw; no hand-tuned near-boundary bin was used.

| Seed | Actual event | Count | Mean | Median | Min | Max |
|---:|---|---:|---:|---:|---:|---:|
| 18353 | entry | 15 | -0.0242852 | -0.0220494 | -0.0491207 | -0.00285536 |
| 18353 | exit | 16 | 0.0290612 | 0.0358801 | 0.00198469 | 0.0499999 |
| 18353 | unchanged | 969 | 0.1925450 | 0.1625881 | -0.1000000 | 0.6570288 |
| 18354 | entry | 15 | -0.0208740 | -0.0209027 | -0.0430375 | -0.00181549 |
| 18354 | exit | 15 | 0.0262373 | 0.0301759 | 1.64036e-8 | 0.0426417 |
| 18354 | unchanged | 970 | 0.20946097 | 0.1785031 | -0.1000000 | 0.6499535 |
| 18355 | entry | 14 | -0.0268667 | -0.0329116 | -0.0376377 | -2.48640e-9 |
| 18355 | exit | 14 | 0.0286390 | 0.0351103 | 1.64036e-8 | 0.0499999 |
| 18355 | unchanged | 972 | 0.2061604 | 0.1674426 | -0.1000000 | 0.6539453 |

Weighted pooled means were `-0.0239436` for entry, `0.0279885` for exit,
and `0.2027280` for unchanged. The two mismatches occurred at a positive
margin of `1.64036e-8`, making the float32 inverse representation issue
visible without inventing a scientific threshold.

## D. Realized motion and mismatch attribution

The nominal MOVE_FORWARD distance was `0.05`. Across the run there were 1593
MOVE_FORWARD transitions: 1198 full nominal moves and 395 reduced/clipped
moves. Per-seed actual Euclidean displacement distributions were:

| Seed | Mean | Median | Min | Max | Full | Clipped/reduced |
|---:|---:|---:|---:|---:|---:|---:|
| 18353 | 0.0431606 | 0.0500000 | 0.0000000 | 0.0500000 | 397 | 144 |
| 18354 | 0.0428869 | 0.0500000 | 0.0000000 | 0.0500000 | 421 | 123 |
| 18355 | 0.0428431 | 0.0500000 | 0.0000000 | 0.0500000 | 380 | 128 |

The accepted artifact also preserves forward-axis displacement statistics.
Clipping was evaluator-only and was never fed back into action choice or
learning.

There were two nominal prediction mismatches, both on un-clipped
`MOVE_FORWARD` transitions while already in charging contact:

| Seed | Transition | Predicted | Actual | Margin | Clipped | Actual-geometry nominal prediction | Post-hoc achieved prediction | Attribution |
|---:|---:|---|---|---:|---|---|---|---|
| 18353 | 15 | false | true | 1.64036e-8 | no | true | false | reconstruction numerical error |
| 18355 | 65 | false | true | 1.64036e-8 | no | true | false | reconstruction numerical error |

Thus mismatches with clipping: `0`; mismatches without clipping: `2`;
reconstruction-numerical classifications: `2`; other-cause mismatches: `0`;
post-hoc achieved-displacement substitutions resolving a mismatch: `0`.
No mismatch supports the clipped-realized-motion explanation on this run.

## E. Exact visible-state aliasing

The exact key was the current float L/F/R beacon triple, exact boolean contact,
and action. No quantization or arbitrary binning was used. One aliased key was
found on seed `18355`:

```text
beacon.left    = 0.761535108089447
beacon.forward = 0.7352941036224365
beacon.right   = 0.761535108089447
contact        = True
action         = MOVE_FORWARD
outcomes       = next contact False x1, True x1
```

This is a direct visited-support aliasing observation. The artifact does not
assign a hidden cause to that alias; D-016 measures it rather than repairing
it. Exact absence of aliases would not have proved universal sufficiency, and
their presence does not justify adding a sensor in D-016.

## Interpretation

The narrow result is mixed rather than a pass/fail claim:

- The existing idealized beacon is highly informative: the analytic inverse
  reconstructs current relative geometry to sub-micro-unit absolute error on
  the visited support, and the nominal kinematic decoder predicts 2998/3000
  transitions, including every visited entry and exit.
- The result is not exact sufficiency. Two false exits arise from float32
  reconstruction at a raw margin of `1.64e-8`, and one exact visible-state
  key/action alias has two next-contact outcomes.
- The two observed prediction mismatches are not concentrated on clipped
  movement; post-hoc achieved displacement did not resolve them. Therefore
  this run does not support attributing the observed mismatch to missing
  realized self-motion information.
- The aliasing is consistent with a hidden world-boundary/realized-motion
  variable, but that is an inference, not established by the stored alias
  record. The current evidence is insufficient to claim universal
  observability, real-world IR sufficiency, noise robustness, robot sufficiency,
  or that the D-013 learner should learn the exact inverse.

The appropriate developmental disposition is to preserve the representation
diagnostic and its numerical/aliasing limitations. D-016 does not add
proprioception, a larger learner, a new sensor, or model-guided behaviour.
No consciousness, emotion, subjective-experience, biological-metabolism,
genuine-life, or emergent-intelligence claim is made.

## Validation and integrity

- `uv run pytest -q`: `702 passed`, 8 existing Matplotlib warnings.
- `uv run ruff check .`: clean.
- `uv run mypy src --strict`: clean.
- `git diff --check`: clean at validation checkpoints.
- No dependency changes.
- `d011.py`, `d013.py`, `d014.py`, and `d015.py` are unchanged.
- No D-016 visualizer or CLI was added; the module's diagnostic CLI is a
  runner output path, not a visualizer.
- The accepted artifact records exact executable SHA
  `ccbfe7d60afde0653a49905028450a537770802f`.
