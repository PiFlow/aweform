# D-005 — Minimal predictive thermal-overshoot adaptation

- **id:** D-005
- **date:** 2026-08-28
- **exact_sha:** `ab23b6a93f275bf458bb8831168da4bdd6c1078f`
- **development_seeds:** `18141, 18142, 18143`
- **horizon:** `1000`
- **disposition:** `CONTINUING`

## Question

Can the smallest inspectable lifetime-plastic mechanism demonstrate the causal
sequence:

```text
organism-visible thermal/contact experience
→ persistent learned-state change
→ changed later CHARGE action selection
```

This is ordinary D-lane mechanism work within ADR 0010 and ADR 0011. It is a
post-acquisition probe over the unchanged D-002/D-003 ecology and makes no
confirmatory claim.

## Programmed scaffold

D-005 retains the D-003 deterministic phases and physical/control scaffold:

```text
CHARGE → DEPART → COOL → TURN_RETURN → RETURN → CHARGE
```

The hot thermal target is `0.60`, the cool return threshold is `0.30`, and the
return is exactly four 45-degree left turns. The D-002 ecology is unchanged.
The evaluator reset places body and station centre at `(0.5, 0.5)` while
preserving each seed's reset heading. The controller has no RNG.

The only controller-visible inputs are normalized thermal interoception and
charging contact. Energy, beacon values, coordinates, station location, true
distance, heading, seed, clock, horizon, reward, and evaluator telemetry are
outside the controller input boundary.

## Plastic scalar

The only persistent learned parameter is
`predicted_departure_thermal_overshoot`, initialized to exactly `0.0`. The
fixed development update rate is `alpha = 0.5`.

In CHARGE, DEPART begins when:

```text
thermal + predicted_departure_thermal_overshoot >= 0.60
```

The target `0.60` itself is not learned. No backup hot threshold, emergency
override, viability rescue, reward, charger acquisition, or performance rule
was added.

## Transient causal state and update provenance

During an active DEPART bout, the controller retains only the transient
`departure_start_thermal` and `departure_peak_thermal` fields. On DEPART
initiation both are copied from the current thermal observation. After each
own DEPART action, the next narrow observation can raise the peak. On the
first narrow observation with charging contact lost, the controller computes:

```text
observed_overshoot = max(0.0, departure_peak_thermal - departure_start_thermal)
prediction_after = prediction_before
                  + 0.5 * (observed_overshoot - prediction_before)
```

It then clears both transient fields. There is no update at a trace/window
boundary and no reset during a lifetime. A deliberate controller reset starts
a new lifetime and resets the scalar and transient fields.

The update method accepts only the typed two-field organism observation. Its
target is formed from newly observed thermal/contact state and the controller's
own phase/action history. `D002TransitionTelemetry`, coordinates, energy,
distance, environment internals, and evaluator diagnostics are not supplied
to the update.

## Execution

The executable mechanism and focused tests were committed at
`ab23b6a93f275bf458bb8831168da4bdd6c1078f` (Commit A). The exact machine-
readable output from the one substantive probe is preserved in
[`D-005-minimal-predictive-thermal-overshoot.json`](D-005-minimal-predictive-thermal-overshoot.json).

The probe was run exactly once with:

```text
uv run python -m aweform.d005 --seeds 18141 18142 18143 --horizon 1000
```

No formal, calibration, confirmatory, acceptance, or reserved seed was
executed. D-002 and D-003 were not retuned.

## Direct observations

All three runs reached `1000` transitions, ended by truncation, did not
terminate for energy or thermal failure, and completed `13` shuttle cycles.
Each run recorded `14` learning updates and started with prediction `0.0`.

| Seed | Final energy | Max thermal | Final thermal | Contact/off transitions | Final prediction |
|---|---:|---:|---:|---:|---:|
| 18141 | `8.400000000000006` | `0.6300000000000002` | `0.4600000000000001` | `513 / 487` | `0.029997589575941674` |
| 18142 | `7.800000000000008` | `0.6200000000000002` | `0.4` | `510 / 490` | `0.019998209463665262` |
| 18143 | `8.400000000000006` | `0.6300000000000002` | `0.4600000000000001` | `513 / 487` | `0.029997589575941674` |

The first update observations were overshoots `0.019999980926513672`,
`0.009999990463256836`, and `0.019999980926513672` for seeds 18141, 18142,
and 18143 respectively. The corresponding first post-update predictions were
`0.009999990463256836`, `0.004999995231628418`, and
`0.009999990463256836`.

Later CHARGE departure-start thermal values were below `0.60`: seed 18141's
and 18143's later values reached `0.5799999833106995`; seed 18142's later
values were `0.5899999737739563`. These values are evaluator copies of the
controller's declared own state for diagnostics; they were not fed back from
the evaluator.

## Engineering/mechanical inference

The observed nonzero predictions and subsequent sub-`0.60` departure starts
are consistent with the declared causal order: a departure action is followed
by a newly observed contact loss and thermal peak, which updates the scalar;
the scalar is then available to a later CHARGE decision. The three seeds show
different contact duty cycles and prediction trajectories while using the same
deterministic controller and preserved seeded headings.

This is a mechanical reading of the implementation and trace, not a claim
that the whole controller is learned. The phase scaffold remains programmed;
the single scalar is the plastic component.

## Hypothesis

Within this fixed post-acquisition ecology, one bounded predictive scalar is a
cheap mechanism that can alter later departure timing after organism-visible
thermal/contact consequences. This makes D-005 a useful developmental
candidate for continued inspection.

It does not establish learning necessity, thermal-signal necessity, charger
acquisition, generalization, intelligence, consciousness, subjective
experience, biological life, or biological equivalence.

## Limitations and disposition

This was a three-seed development probe with a fixed evaluator-side
post-contact setup and a 1000-transition horizon. It does not compare
performance against D-003 as a scientific success test, and no claim of
outperformance is made. It does not isolate whether thermal interoception is
necessary, nor whether the result transfers to other geometries, lifetimes,
or ecologies. The result is descriptive development evidence only.

**Disposition:** `CONTINUING`.
