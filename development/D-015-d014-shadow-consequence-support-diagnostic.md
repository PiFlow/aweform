# D-015 — D-014 shadow consequence support diagnostic

- **id:** D-015
- **date:** 2026-08-31
- **authoritative_base_sha:** `3208f9df1b3045db080913b6c06ea859f19c73ca`
- **accepted_executable_sha:** `97a4337623fa5396294ae0e350081ef77de52f86`
- **development_seeds:** `18350, 18351, 18352`
- **horizon:** `1000` transitions per lifetime
- **disposition:** `CONTINUING`

## Question and scope

D-015 attaches the exact existing D-013 84-scalar action-conditioned
consequence predictor in shadow-only mode to the corrected D-014 behavioural
scaffold. It asks whether one-step energy and thermal consequence prediction
remains useful, whether the weak overall charging-contact result persists, and
whether contact error is concentrated differently across exact contact exit,
unchanged, and entry outcomes.

This is a development-only support/error-structure diagnostic. It is not a new
learner, a history experiment, a causal-state augmentation, a counterfactual
competence test, model-guided control, action selection, planning, reward
learning, or confirmatory evidence.

## Programmed, visible, learned, and evaluator-only state

**PROGRAMMED**

- `D014Controller` selects every physical action. Its full-energy-or-hot
  departure rule and inherited D-011 state machine are unchanged.
- `D002ThermalStationEnv`, D-002 ecology, beacon/contact semantics, action
  costs, thermal/energy dynamics, policy RNG semantics, and post-contact setup
  are unchanged.
- The evaluator uses the exact D-013 prequential MAE definitions and exact
  zero-change comparator. Contact event classes are exact visible contact
  deltas, not thresholded continuous values.

**ORGANISM-VISIBLE**

- normalized energy;
- beacon left, forward, and right;
- physical charging contact;
- normalized thermal state;
- the organism's own executed action for the action-conditioned learner;
- the actual typed one-step later observation, only after that consequence
  occurs.

**LEARNED**

The learner is `d013.D013ActionConsequencePredictor`, reused directly and
unchanged. Its features are exactly:

```text
[1.0, energy, beacon.left, beacon.forward, beacon.right,
 float(charging_contact), thermal]
```

It predicts `delta_energy`, `delta_thermal`, and
`delta_charging_contact` for the physically executed action. It has four
actions, three outputs, seven features, zero initialization, normalized LMS
with learning rate `0.5`, and exactly `4 × 3 × 7 = 84` scalar weights. It has
no history, hidden units, previous-action/contact feature, optimizer state,
buffer, replay, event balancing, confidence state, RNG, or other retained
plastic object.

**EVALUATOR-ONLY**

- exact contact event labels `-1.0` exit, `0.0` unchanged, and `+1.0` entry;
- contact-changed versus contact-unchanged grouping;
- learned/zero-change MAE summaries and mean pre-update contact predictions;
- action × current-contact and contact-target support;
- viability, mode, action, departure, SEEK, reacquisition, and cycle summaries;
- evaluator geometry used by the canonical post-hoc visualizer.

The causal order is: construct current `D011Observation`; let
`D014Controller` select the action; form the learner's pre-update prediction;
execute `environment.step(action)`; construct the typed next observation;
perform the ordinary D-013 update; then classify the observed contact delta and
collect evaluator diagnostics. The event class is never passed into
plasticity or action selection. Reward remained exactly `0.0` and `info`
remained exactly `{}`.

## Provenance and execution

The current post-merge `main` was verified at
`3208f9df1b3045db080913b6c06ea859f19c73ca`. PR #68 is merged at that tip, and
the reviewed PR #68 HEAD
`ec7d7ef561167cb6a4fe4720fb7b6a8b63ad372c` is an ancestor of it. D-015 was
implemented from that post-merge main SHA, not from the PR #68 feature branch.

The accepted executable candidate was validated cleanly and committed at
`97a4337623fa5396294ae0e350081ef77de52f86`. The substantive probe was then
run once from that exact clean executable commit with:

```text
uv run python -m aweform.d015 \
  --seeds 18350 18351 18352 \
  --horizon 1000 \
  --executed-commit-sha 97a4337623fa5396294ae0e350081ef77de52f86 \
  --output development/D-015-d014-shadow-consequence-support-diagnostic.json
```

The machine-readable result is preserved in
[`D-015-d014-shadow-consequence-support-diagnostic.json`](D-015-d014-shadow-consequence-support-diagnostic.json).
The exact D-015 guard first calls `validate_exp003_development_seeds`, then
accepts only `(18350, 18351, 18352)`. Formal reservations remain protected.

## Accepted viability and behaviour observations

All three lifetimes reached horizon truncation at 1000 transitions. Values are
copied from the accepted artifact and rounded to six decimals here.

| Seed | Min / final normalized energy | Max / final thermal | Actions MOVE / LEFT / RIGHT / WAIT | Modes AWAY / CHARGE / DEPART / SEEK | Mode entries AWAY / CHARGE / DEPART / SEEK | Departures / exits | SEEK entries / reacquisitions | Cycles | Failed / censored SEEK |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 18350 | 0.052000 / 0.328000 | 0.340000 / 0.000000 | 513 / 98 / 110 / 279 | 413 / 280 / 56 / 251 | 15 / 15 / 15 / 15 | 15 / 16 | 15 / 14 | 14 | 0 / 1 |
| 18351 | 0.128000 / 0.392000 | 0.350000 / 0.050000 | 540 / 94 / 83 / 283 | 406 / 283 / 55 / 256 | 15 / 16 / 15 / 15 | 15 / 16 | 15 / 15 | 15 | 0 / 0 |
| 18352 | 0.044000 / 0.676000 | 0.350000 / 0.070000 | 525 / 95 / 94 / 286 | 404 / 287 / 53 / 256 | 15 / 15 / 15 / 14 | 15 / 16 | 14 / 14 | 14 | 0 / 0 |

All 45 recorded departures were `full_only`; no thermal-only or both-condition
departure was observed. The highest observed thermal state was `0.35` and no
lifetime terminated for energy or thermal failure.

## Prediction performance

These are evaluator-only pre-update MAEs. Each value is `learned / zero-change
comparator`.

### Overall

| Seed | delta_energy | delta_thermal | delta_charging_contact |
|---:|---:|---:|---:|
| 18350 | 0.00337499 / 0.02298000 | 0.00205588 / 0.00696000 | 0.05895410 / 0.03100000 |
| 18351 | 0.00321572 / 0.02342000 | 0.00195494 / 0.00697000 | 0.05932694 / 0.03200000 |
| 18352 | 0.00342517 / 0.02338400 | 0.00196830 / 0.00703000 | 0.05784703 / 0.03100000 |

Energy and thermal learned MAE were below the zero-change comparator on all
three seeds. Overall contact learned MAE was above the comparator on all three
seeds.

### Q1–Q4

Each cell is `learned / zero-change comparator`.

| Seed | Window | delta_energy | delta_thermal | delta_charging_contact |
|---:|---|---:|---:|---:|
| 18350 | Q1 | 0.00371002 / 0.02298400 | 0.00221408 / 0.00732000 | 0.04519278 / 0.03200000 |
| 18350 | Q2 | 0.00339303 / 0.02348000 | 0.00224491 / 0.00752000 | 0.06052834 / 0.03600000 |
| 18350 | Q3 | 0.00300814 / 0.02208000 | 0.00190172 / 0.00588000 | 0.05848524 / 0.02400000 |
| 18350 | Q4 | 0.00338877 / 0.02337600 | 0.00186280 / 0.00712000 | 0.07161002 / 0.03200000 |
| 18351 | Q1 | 0.00293138 / 0.02364000 | 0.00197704 / 0.00756000 | 0.04537608 / 0.03200000 |
| 18351 | Q2 | 0.00288299 / 0.02312800 | 0.00190398 / 0.00684000 | 0.05172631 / 0.02800000 |
| 18351 | Q3 | 0.00323366 / 0.02388800 | 0.00196972 / 0.00696000 | 0.06867615 / 0.03200000 |
| 18351 | Q4 | 0.00381484 / 0.02302400 | 0.00196901 / 0.00652000 | 0.07152921 / 0.03600000 |
| 18352 | Q1 | 0.00281140 / 0.02336000 | 0.00214432 / 0.00744000 | 0.04080495 / 0.02800000 |
| 18352 | Q2 | 0.00304121 / 0.02424000 | 0.00174843 / 0.00672000 | 0.04743539 / 0.02800000 |
| 18352 | Q3 | 0.00367307 / 0.02291200 | 0.00202532 / 0.00732000 | 0.07325145 / 0.03600000 |
| 18352 | Q4 | 0.00417499 / 0.02302400 | 0.00195513 / 0.00664000 | 0.06989634 / 0.03200000 |

## Exact contact event diagnostics

Counts are `-1.0 = exit`, `0.0 = unchanged`, and `+1.0 = entry`. Each metric
cell is `count; learned MAE / zero-change MAE; mean pre-update predicted
contact delta`.

### Overall

| Seed | Exit (`-1.0`) | Unchanged (`0.0`) | Entry (`+1.0`) | Changed / unchanged grouping |
|---:|---:|---:|---:|---:|
| 18350 | 16; 0.836771 / 1.000000; -0.163229 | 969; 0.033038 / 0.000000; -0.001199 | 15; 0.903452 / 1.000000; 0.096548 | 31 / 969 |
| 18351 | 16; 0.837116 / 1.000000; -0.162884 | 968; 0.032420 / 0.000000; -0.001306 | 16; 0.909408 / 1.000000; 0.090592 | 32 / 968 |
| 18352 | 16; 0.835967 / 1.000000; -0.164033 | 969; 0.031847 / 0.000000; -0.002543 | 15; 0.907486 / 1.000000; 0.092514 | 31 / 969 |

The D-015 artifact retains the exact Q4 class metrics. In Q4, all three
classes were supported on all three seeds:

| Seed | Exit Q4 count; learned / baseline | Unchanged Q4 count; learned / baseline | Entry Q4 count; learned / baseline |
|---:|---:|---:|---:|
| 18350 | 4; 0.765072 / 1.000000 | 242; 0.047256 / 0.000000 | 4; 0.851571 / 1.000000 |
| 18351 | 4; 0.772860 / 1.000000 | 241; 0.043412 / 0.000000 | 5; 0.865727 / 1.000000 |
| 18352 | 4; 0.767599 / 1.000000 | 242; 0.045240 / 0.000000 | 4; 0.863896 / 1.000000 |

Pooled contact target counts across the 3000 transitions were `48` exits,
`2906` unchanged, and `46` entries. The changed/unchanged grouping counts
were `94 / 2906`.

### Action × current-contact support

The artifact retains exact per-seed support. The pooled counts below are
`MOVE_FORWARD / TURN_LEFT / TURN_RIGHT / WAIT`:

| Current contact | Pooled action support |
|---|---:|
| `False` | 1402 / 287 / 285 / 0 |
| `True` | 176 / 0 / 2 / 848 |

No action was forced to fill a missing support cell. Per-action contact-target
counts and untested cells remain in the JSON artifact.

## Shadow isolation and visualizer

The D-015 shadow path uses the same `D014Controller`, seed, horizon, ecology,
and policy RNG semantics as the D-015 reference path. Focused tests compare
exact per-frame positions, headings, actions, controller modes, energy,
thermal, contact, and termination flags. A monkeypatched predictor returning
`(1e9, -1e9, 1e9)` also leaves those physical frames unchanged. Reward/info
and learner diagnostics are not inputs to action selection.

The canonical visualizer has two new sources:

```text
uv run aweform-visualize \
  --source d015-reference \
  --seed 18350 \
  --horizon 1000 \
  --interval-ms 60
```

```text
uv run aweform-visualize \
  --source d015 \
  --seed 18350 \
  --horizon 1000 \
  --interval-ms 60
```

`d015-reference` is the ordinary two-panel view. `d015` uses the existing
five-panel D-013 shadow layout and explicitly displays
`SHADOW ONLY — ZERO BEHAVIOURAL INFLUENCE`. Both accept only D-015 seeds.

## Interpretation and limitations

**Direct observation:** On these three corrected-scaffold trajectories, the
unchanged D-013 learner retained lower pre-update energy and thermal MAE than
the zero-change comparator. It remained worse overall for contact. Event-level
contact MAE for both exits and entries was below the zero-change event
comparator, while the unchanged-contact learned MAE was nonzero and therefore
could dominate the much larger unchanged class's overall contribution.

**Conservative inference:** This pattern is compatible with the learner
extracting some event-related contact signal while sparse-event imbalance or
online interference contributes to the worse overall contact result. It does
not establish that sparsity is the only cause. Representation limits,
action/context support imbalance, hidden state, consequence aliasing, and
online-LMS interference remain unresolved alternatives.

This probe does not authorize a larger learner, retained history, a neural
network, model-guided behaviour, counterfactual action comparison, or planning.
The learner was trained only on physically executed on-policy actions, so these
results do not establish support for predictions of unexecuted alternatives.

Limitations include one three-seed development probe, one fixed 1000-transition
horizon, deterministic D-002 ecology, and on-policy support imbalance. The
thermal departure branch was not exercised as the first departure condition in
this run. Null and negative outcomes remain valid developmental results.

## Validation

At the accepted executable candidate:

- `uv run pytest -q`: **685 passed**, 8 existing Matplotlib warnings;
- focused D-015/visualizer tests: **69 passed**;
- `uv run ruff check .`: clean;
- `uv run mypy src --strict`: clean;
- `git diff --check`: clean;
- headless/Agg smoke: `d014` and `d013-reference` produced two-panel views;
  `d013` and `d015` produced five-panel shadow views; `d015-reference`
  produced a two-panel view;
- `d011.py`, `d013.py`, and `d014.py` remain unchanged.

No ADR was added: D-015 stays within the already authorized D-014 scaffold and
D-013 sensory/plasticity boundary.
