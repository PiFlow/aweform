# D-014 — Full-charge-or-thermal departure scaffold correction

- **id:** D-014
- **date:** 2026-08-31
- **authoritative_base_sha:** `8a62f0931de40dc85d26ec1ddbd3c1003fa1b723`
- **accepted_executable_sha:** `6e552dc40610d789dc0b54384c594d6ac029233f`
- **record_commit_sha:** pending until this record and artifact are committed
- **development_seeds:** `18347, 18348, 18349`
- **horizon:** `1000` transitions per lifetime
- **disposition:** `CONTINUING`

## Question and motivation

D-014 asks whether the established D-011 autonomous regulation scaffold
retains its repeated charge → depart → explore → low-energy SEEK → beacon
reacquisition loop when charger departure begins at the first of:

```text
full normalized energy OR existing hot thermal threshold
```

The motivation was post-hoc observation in the canonical visualizer: D-011's
fixed CHARGE phase could remain on the charger after full energy until the
thermal threshold was reached. Repository inspection confirmed that this was
programmed D-011 behaviour, not a consequence of D-013 learning.

This is ordinary developmental work, not a learning experiment or a
confirmatory claim. D-014 does not invalidate or rewrite D-011, D-012, or
D-013. Those remain historical completed developmental observations under
their exact old scaffolds.

## Mechanism and boundaries

**PROGRAMMED**

- `D014Controller` inherits `D011Controller`.
- The only controller override is: while in `CHARGE`, with physical charging
  contact true, if `D011Observation.energy >= 1.0`, set mode to `DEPART` and
  return `MOVE_FORWARD`.
- Otherwise action selection delegates to unchanged `D011Controller.act`, so
  the existing `HOT_DEPART_THRESHOLD == 0.60` thermal route, lost-contact
  transition to `SEEK`, `DEPART`, `AWAY`, and `SEEK` behaviour remain inherited.
- The D-002 thermal station ecology, energy/thermal dynamics, charging radius,
  beacon, action definitions, post-contact setup, policy RNG semantics, and
  horizon are unchanged.

**ORGANISM-VISIBLE**

- normalized energy;
- normalized thermal state;
- beacon left / forward / right;
- physical charging contact;
- inherited D-011 controller phase and explorer-owned policy RNG state.

No new sensory input, coordinates, true distance, heading-to-station, horizon,
seed identity, evaluator telemetry, or future information was added.

**LEARNED**

None. D-014 has no learner, predictor, plastic state, retained history,
reward-driven action selection, or model-guided action selection.

**EVALUATOR-ONLY**

Per-seed run summaries, action/mode counts, departure-event summaries,
termination flags, SEEK outcome classifications, and controller-visible
departure context copied for audit. Departure context was not passed back to
the controller.

Every transition retained `reward == 0.0` and `info == {}`.

## Seed policy and provenance

The D-014 guard first calls the canonical
`validate_exp003_development_seeds`, then accepts only the exact declared
development seeds `(18347, 18348, 18349)`. Formal reservations remain guarded;
no formal reserved seed was used.

The executable implementation was validated and committed cleanly at
`6e552dc40610d789dc0b54384c594d6ac029233f`. `git status --porcelain` was empty
before execution. The accepted substantive run was then executed once from
that exact SHA with:

```text
uv run python -m aweform.d014 \
  --seeds 18347 18348 18349 \
  --horizon 1000 \
  --executed-commit-sha 6e552dc40610d789dc0b54384c594d6ac029233f \
  --output development/D-014-full-charge-or-thermal-departure.json
```

The machine-readable result is preserved in
[`D-014-full-charge-or-thermal-departure.json`](D-014-full-charge-or-thermal-departure.json).

## Accepted observations

All three lifetimes reached horizon truncation at 1000 transitions. None
terminated for energy or thermal failure. Values below are descriptive copies
of the accepted artifact; normalized energy and thermal values are shown to
six decimal places for readability.

| Seed | Termination | Min / final normalized energy | Max / final thermal | Departure triggers `full / thermal / both` | Physical exits | SEEK entries / reacquisitions | Completed cycles | Failed / censored SEEK |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 18347 | horizon truncation | 0.116000 / 0.568000 | 0.350000 / 0.020000 | 15 / 0 / 0 | 15 | 14 / 14 | 14 | 0 / 0 |
| 18348 | horizon truncation | 0.036000 / 0.920000 | 0.340000 / 0.180000 | 15 / 0 / 0 | 16 | 14 / 14 | 14 | 0 / 0 |
| 18349 | horizon truncation | 0.172000 / 0.908000 | 0.350000 / 0.170000 | 16 / 0 / 0 | 16 | 15 / 15 | 15 | 0 / 0 |

Aggregate descriptive counts were 46 `full_only`, 0 `thermal_only`, and 0
`both` departures; 47 physical charger exits; 43 low-energy SEEK entries; 43
successful reacquisitions; 43 completed autonomous regulation cycles; 0
demonstrated failed SEEK episodes; and 0 horizon-censored SEEK episodes. The
lowest observed normalized energy was `0.0359999985`, and the highest observed
thermal state was `0.3499999940`.

Pooled action counts were `MOVE_FORWARD 1588`, `TURN_LEFT 259`, `TURN_RIGHT
274`, and `WAIT 879`. Pooled mode occupancy was `AWAY 1168`, `CHARGE 882`,
`DEPART 172`, and `SEEK 778`. Mode entries were `AWAY 46`, `CHARGE 46`,
`DEPART 46`, and `SEEK 43`.

For every recorded CHARGE → DEPART decision, the artifact records the decision
and transition index, current normalized energy and thermal signal, contact,
both condition booleans, and the non-exclusive category. In this run all 46
departures were `full_only`; no thermal-only or both-condition departure was
observed. Seed 18348 had one additional physical contact-boundary exit beyond
its 15 D-014 departures, a descriptive accidental AWAY contact consistent with
the inherited D-011 distinction between accidental contact and SEEK
reacquisition.

## Reading and limitations

**Direct observation:** On these three declared development seeds and this
horizon, the corrected scaffold repeatedly departed at full normalized energy,
reacquired the charger after low-energy SEEK, and completed 14, 14, and 15
cycles without viability termination. The thermal route was not exercised in
this particular run because full energy was reached first on every departure.

**Inference:** The additive full-energy correction is compatible with coherent
repeated autonomous regulation under this fixed D-002 ecology and D-011
post-contact setup. This is a narrow developmental observation, not evidence
that the organism has intelligence, motivation, preference, subjective state,
consciousness, emotion, genuine life, biological metabolism, or general
robustness. It does not establish that the thermal route is unnecessary; the
thermal route remains part of the programmed rule and was not tested as the
first condition on these three trajectories.

No binary success threshold was imposed after inspecting the results. Negative
or surprising future D-014 runs remain valid developmental outcomes.

## Validation

From the clean executable implementation commit:

- `uv run pytest -q`: **662 passed**, 7 existing Matplotlib warnings.
- `uv run ruff check .`: **clean**.
- `uv run mypy src --strict`: **clean**.
- `git diff --check`: **clean**.

The headless canonical visualizer smoke built successfully for `d014`, `d011`,
`d012`, `d013-reference`, and `d013`. D-014 produced the ordinary two-panel
layout with no learner/consequence panel; the historical D-013 source retained
its five-panel shadow-learning layout.

The D-014 visualization command is:

```text
uv run aweform-visualize \
  --source d014 \
  --seed 18347 \
  --horizon 1000 \
  --interval-ms 60
```
