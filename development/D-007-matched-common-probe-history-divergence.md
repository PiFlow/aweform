# D-007 — Matched common-probe history divergence

- **id:** D-007
- **date:** 2026-08-29
- **exact_sha:** `db5037c6761d43bf801d920378cee777d64bfd6f`
- **development_seeds:** `18141, 18142, 18143`
- **disposition:** `CONTINUING`

## Scientific question

Can two initially identical D-005 predictive controllers acquire different
persistent plastic states solely from different legitimate thermal histories,
and then select different actions when given the same later controller-visible
observation and equalized non-plastic controller state?

This is a narrow causal development probe. It is not a claim about
consciousness, personality, individuality in a biological or psychological
sense, general intelligence, biological life, or subjective experience.

## Programmed scaffold

D-007 reused the D-003 phase scaffold and the unchanged D-005
`PredictiveThermalOvershootController`:

```text
CHARGE → DEPART → COOL → TURN_RETURN → RETURN → CHARGE
```

The hot threshold was `0.60`, the cool-return threshold was `0.30`, the
half-turn was four 45-degree left turns, and `alpha` was `0.5`. Each history
used a fresh controller with initial prediction exactly `0.0`, the seeded reset
heading, and evaluator-side body/station placement at `(0.5, 0.5)`. The two
histories for each seed had identical declared setup and differed only in the
fixed charging heat coefficient:

| History | Charging heat per offered energy |
|---|---:|
| mild | `0.04` |
| strong | `0.06` |

The coefficient was supplied through a D-007-specific override of the narrow
D-002 coefficient hook. D-002, D-005, and D-006 historical mechanisms were
not changed.

## Organism-visible information and plastic state

The controller-visible observation remained exactly:

```text
thermal interoception
charging contact
```

The only declared persistent plastic state was
`predicted_departure_thermal_overshoot`. The only transient departure fields
were `departure_start_thermal` and `departure_peak_thermal`; they were cleared
when each consequence update was applied. The controller had no RNG,
optimizer, eligibility trace, recurrent learned state, adaptive learning-rate
state, experience buffer, or other hidden plastic object.

The history condition, energy, coordinates, geometry, heading, transition
index, target update count, horizon, reward, info, and evaluator telemetry were
not supplied to `act()` or `observe_consequence()`. Reward remained exactly
`0.0` and info remained `{}` during history execution.

## Common-probe intervention

Each history ran until exactly seven D-005 departure-consequence learning
updates had occurred. The evaluator then allowed the active programmed
`COOL`/`TURN_RETURN`/`RETURN` sequence to complete and stopped at:

```text
mode = CHARGE
turns_remaining = 0
departure_start_thermal = None
departure_peak_thermal = None
```

The exact shared typed probe observation was frozen before execution:

```text
D003ThermostaticObservation(thermal=0.56, charging_contact=True)
```

The actual trained controller received that observation, and its normal
`act()` method was called exactly once. No reset, learned-state overwrite,
consequence update, or environment transition occurred between presenting the
common observation and recording the action. This is an evaluator
controller-level causal diagnostic, not an uninterrupted natural physical
transition that placed two organisms in a common world state.

## Direct observations

The exact compact machine-readable output is preserved in
[`D-007-matched-common-probe-history-divergence.json`](D-007-matched-common-probe-history-divergence.json).

All six histories reached probe readiness without energy or thermal failure.
Every history retained exactly seven updates. The evaluator-only final state
after history preparation was energy `6.920000000000016`; thermal was
`0.2699999999999999` for mild histories and `0.29000000000000004` for strong
histories.

| Seed | History | Updates | Learned prediction | Transitions to probe-ready | Common-probe action |
|---|---|---:|---:|---:|---|
| 18141 | mild | 7 | `0.029687529429793358` | 519 | `WAIT` |
| 18141 | strong | 7 | `0.059375002048909664` | 396 | `MOVE_FORWARD` |
| 18142 | mild | 7 | `0.019765663892030716` | 513 | `WAIT` |
| 18142 | strong | 7 | `0.039531270042061806` | 393 | `WAIT` |
| 18143 | mild | 7 | `0.029687529429793358` | 519 | `WAIT` |
| 18143 | strong | 7 | `0.059375002048909664` | 396 | `MOVE_FORWARD` |

At every probe, the mode before action was `CHARGE`, turns remaining was `0`,
and both departure transient fields were `None`. The common observation was
field-for-field identical: thermal `0.56`, charging contact `True`. The strong
probe changed controller mode to `DEPART` when its retained prediction crossed
the threshold condition; the mild probe remained in `CHARGE`.

## Mechanical inference

**Source:** exact JSON emitted by the clean Commit A executable and the source
declarations above. Different fixed charging consequences produced different
organism-visible thermal/contact update targets and therefore different
retained prediction scalars. At the later identical typed probe, those retained
states produced different action selection for seeds `18141` and `18143`, but
not for seed `18142`.

This supports the narrow descriptive statement that different legitimate
thermal histories produced different persistent D-005 prediction states, and
that under an identical later controller-visible probe those states produced
different action selection on two of these three development seeds. The
`18142` same-action result is retained as a valid null action contrast.

## Surprised by

The stronger history reached probe readiness in fewer transitions on all three
seeds, but the action-level contrast was seed-dependent: two pairs diverged
and one pair remained `WAIT`. The design therefore produced both a readable
common-probe divergence and a same-action case without tuning the probe to
force divergence.

## Limitations

- This is one three-seed D-lane development probe, not evidence-lane
  confirmation.
- The histories use evaluator-side post-contact setup and a fixed D-002
  ecology; station acquisition, other geometry, other lifetimes, and other
  ecologies were not tested.
- The two histories differ in a deterministic charging coefficient. This does
  not test stochastic change, delayed sensing, noise, thermal gradients,
  actuator heat, or a larger learner.
- The common probe equalizes controller state and observation at the
  controller-level diagnostic only. It does not establish whole-organism
  common-probe equivalence because evaluator-side energy and thermal states
  remain history measurements.
- The result does not establish personality, biological or psychological
  individuality, consciousness, subjective experience, emotion, desire,
  intelligence, agency beyond the implemented mechanism, generalization,
  learning necessity, superiority over D-003, biological life, biological
  equivalence, or an evidence-lane claim.

## Disposition

`CONTINUING`. Retain the compact history/update/probe artifact and the null
same-action pair. Any later formal claim would require a separately frozen
protocol, controls, untouched seeds, and the applicable independent review.
