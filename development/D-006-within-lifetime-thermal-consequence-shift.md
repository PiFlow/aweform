# D-006 — Within-lifetime thermal consequence-shift adaptation

- **id:** D-006
- **date:** 2026-08-28
- **exact_sha:** `645a915bf8eaee37ee27055afb13b961b3b785d0`
- **development_seeds:** `18141, 18142, 18143`
- **horizon:** `1000`
- **disposition:** `CONTINUING`

## Question

Can the existing minimal lifetime-plastic thermal predictor update when the
causal thermal consequence of charging changes during one uninterrupted
lifetime, without an explicit regime signal, and can the updated learned state
alter later CHARGE action timing?

This is ordinary D-lane developmental work. It is not a confirmatory result.

## Programmed scaffold

D-006 retains the D-003 phase scaffold and the D-005 controller:

```text
CHARGE → DEPART → COOL → TURN_RETURN → RETURN → CHARGE
```

The controller-visible observation remains exactly normalized thermal
interoception plus charging contact. It has no RNG and receives no energy,
coordinates, station location, distance, heading, transition counter, clock,
horizon, seed, regime identity, reward, info, or evaluator telemetry.

The only persistent learned state is D-005's
`predicted_departure_thermal_overshoot`, initialized to `0.0`. The fixed update
rate remains `alpha = 0.5`; CHARGE departs when:

```text
thermal + predicted_departure_thermal_overshoot >= 0.60
```

The phase logic, movement, energy accounting, passive cooling, thermal
failure boundary, post-contact setup, and 1000-transition horizon are otherwise
unchanged from D-002 through D-005. A lifetime is one continuous run; there is
no reset at transition 500 or 501.

## Learned state and update provenance

During DEPART, the reused D-005 controller retains only its own departure-start
and departure-peak thermal state. After each environment transition it receives
the next narrow observation. On the first observed contact loss it computes the
overshoot from those organism-visible thermal/contact observations and its own
departure state, then writes the scalar update before the runner reads evaluator
telemetry. The update is:

```text
prediction_after = prediction_before
                  + 0.5 * (observed_overshoot - prediction_before)
```

The D-006 result records the update transition index for evaluator inspection;
that index is not passed to the controller. The comparator uses the unchanged
D-003 non-learning thermostatic controller and has no prediction state.

## Evaluator-induced environmental perturbation

D-006 adds one environment/evaluator-side physical schedule:

```text
charging heat per offered energy = 0.04 through transition 500
charging heat per offered energy = 0.06 beginning with transition 501
```

The regime schedule is implemented by a narrow D-002 coefficient seam whose
default path remains exactly the historical `0.04` behaviour. It is not an
organism observation and is not a plasticity input. Both predictive and
comparator conditions use the same schedule and the same seeded initial
heading after matched evaluator placement.

The complete machine-readable output is preserved in
[`D-006-within-lifetime-thermal-consequence-shift.json`](D-006-within-lifetime-thermal-consequence-shift.json).

## Execution

Commit A was clean and passed the full repository checks before the substantive
run: `538 passed`, Ruff clean, and mypy clean. The intended command was:

```text
uv run python -m aweform.d006 --seeds 18141 18142 18143 --horizon 1000
```

The first execution exited successfully, but the application output transport
truncated the captured stdout and inserted a truncation marker into the local
artifact. No source, configuration, or constants changed. Two unchanged
capture-recovery executions were then made to obtain a valid exact stdout
artifact; the final valid artifact is the output of the last recovery
execution. This is a documented execution-discipline deviation from the
requested one-execution capture rule, not a hidden rerun or a tuned result.

No formal, calibration, confirmatory, acceptance, or otherwise reserved seed
was used.

## Direct observations

All six matched runs reached 1000 transitions, ended by horizon truncation, and
did not terminate for energy or thermal failure. The predictive condition
recorded 16 adaptive updates per seed; the comparator recorded none.

| Seed | Condition | Contact / off | Cycles | Min / final energy | Max / final thermal | Prediction before 501 → final |
|---|---|---:|---:|---:|---:|---:|
| 18141 | D-006 predictive | `426 / 574` | 15 | `5.0 / 7.500000000000009` | `0.6500000000000002 / 0.37` | `0.029687529429793358 → 0.05994079833544674` |
| 18142 | D-006 predictive | `422 / 578` | 15 | `5.0 / 6.5800000000000125` | `0.6300000000000002 / 0.2799999999999999` | `0.019765663892030716 → 0.039960501228051726` |
| 18143 | D-006 predictive | `426 / 574` | 15 | `5.0 / 7.500000000000009` | `0.6500000000000002 / 0.37` | `0.029687529429793358 → 0.05994079833544674` |
| 18141 | D-003 comparator | `438 / 562` | 14 | `5.0 / 9.600000000000001` | `0.6700000000000003 / 0.6400000000000002` | not applicable |
| 18142 | D-003 comparator | `423 / 577` | 14 | `5.0 / 5.9400000000000155` | `0.6500000000000002 / 0.2599999999999999` | not applicable |
| 18143 | D-003 comparator | `438 / 562` | 14 | `5.0 / 9.600000000000001` | `0.6700000000000003 / 0.6400000000000002` | not applicable |

Before transition 501, the predictive runs followed the baseline thermal
consequence. For seed 18141 and 18143, the update at transition 482 observed
overshoot `0.030000030994415283` and moved prediction from
`0.029375027865171432` to `0.029687529429793358`. For seed 18142, the
pre-change prediction immediately before transition 501 was
`0.019765663892030716`.

After transition 501, the first predictive updates were at transition 538 for
18141/18143 and transition 531 for 18142. The observed post-change overshoot
was `0.06000000238418579` for 18141/18143 and `0.04000002145767212` for
18142. Subsequent alpha updates moved the persistent prediction toward those
observed values. The full per-update before/after values and the complete
post-change prediction trajectory are in the JSON artifact.

The D-003 comparator had no plastic update. Its evaluator-only overshoot
diagnostic nevertheless changed after the regime shift: its later departure
starts were approximately `0.61` and its observed overshoots were approximately
`0.06` for seeds 18141/18143 and `0.04` for seed 18142. This comparator result
is descriptive and is not a D-006 success criterion.

## Mechanical inference

The transition-index schedule and the recorded thermal inputs are consistent
with an environment-side coefficient change only at 501. The predictive
controller's pre-change scalar is present at transition 501 rather than being
reset. Later contact-loss observations produce larger post-change overshoot
targets, and the declared alpha equation changes the persistent prediction.

Later CHARGE records use nonzero prediction values in the action-selection
trace. This is consistent with the causal sequence:

```text
changed environment consequence
→ narrow thermal/contact observation
→ persistent D-005 prediction update
→ later CHARGE threshold evaluation
```

This is a mechanical reading of the instrumented trajectory. The programmed
phase scaffold remains the dominant controller structure; the scalar predictor
is the learned component. The result does not establish that learning was
necessary or that the predictive condition was superior to D-003.

## Hypothesis

Within this fixed post-acquisition ecology, the existing bounded D-005 scalar
is a plausible minimal mechanism for within-lifetime consequence-shift
adaptation: it can retain pre-shift state, incorporate later organism-visible
thermal consequences, and alter later departure timing without an explicit
regime signal.

This remains a developmental hypothesis. It does not establish generalization,
learning necessity, thermal-signal necessity, intelligence, consciousness,
subjective experience, biological life, or biological equivalence.

## Surprised by

The perturbation did not cause viability failure in any of the six matched
development runs. The shifted coefficient instead produced a readable change
in overshoot targets and prediction trajectories while all runs still reached
the horizon. The predictive condition also completed 15 cycles versus 14 for
the comparator on these development seeds, but that descriptive difference is
not treated as a success claim because the conditions have different learned
departure timing and the probe was not designed or powered as a performance
comparison.

## Limitations

- This is one three-seed development probe with evaluator-side post-contact
  setup and a fixed 1000-transition horizon.
- The comparator is matched on seed, geometry, and thermal regime, but D-006
  does not define success as outperforming it.
- The design does not isolate learning necessity, thermal-interoception
  necessity, station acquisition, or transfer to another ecology or lifetime.
- The environment changes a deterministic charging coefficient; it does not
  test stochastic change, delayed sensing, noise, thermal gradients, actuator
  heat, or new viability variables.
- The output-capture failure and unchanged recovery executions are recorded
  above; the result should not be described as a pristine single-execution
  artifact under the requested discipline.

## Next

Retain the null viability result and the mechanical adaptation trace. If this
thread continues, the cheapest next step is an explicitly predeclared probe
that separates timing change from other descriptive trajectory differences,
without adding sensors, reward, or a broader thermal-ecology abstraction.

**Disposition:** `CONTINUING`.
