# D-022 — Incidental charging contribution audit

- **id:** D-022
- **lane:** Development
- **date:** 2026-09-02
- **authoritative_base_sha:** `4a51abe2c9f7338b25636ee059a976e21f5b0eda`
- **implementation_audit_sha:** `d7b8585bd6a730faae480d2650544d7669e2e001`
- **development_seeds:** `18365, 18366, 18367` (the accepted D-021 set; no new seeds)
- **source_horizon:** `70,000` transitions per lifetime
- **disposition:** `CONTINUING`
- **learned mechanism:** none

## Question and scope

D-022 asks how much physical stored battery energy D-021 received from
incidental charger contact while its programmed controller was in `AWAY`, and
how much earlier the inherited `< 0.50` threshold would be crossed in a
narrow, evaluator-only open-loop ledger shadow if that already-accepted charge
were removed.

This is a post-hoc evaluator accounting audit, not a new behavioural
experiment. Each source lifetime was replayed with the existing
`run_d021_lifetime_trace(...)`, using the exact D-021 seeds and
`D021_HORIZON == 70_000`. The completed traces were then analyzed. D-021's
controller, actions, initial state, RNG streams, D-020 physics, observations,
reward, and info were unchanged.

The machine-readable artifact is the numerical source for this record:
[`D-022-v04-incidental-charging-contribution-audit.json`](D-022-v04-incidental-charging-contribution-audit.json).
It contains compact episode summaries rather than raw transitions.

## Frozen audit definitions

An incidental `AWAY` contact episode starts on a transition satisfying all of:

1. `mode_before == AWAY`;
2. ordinary pre-action normalized energy `>= 0.50`;
3. `telemetry.charging_contact_before == False`;
4. `telemetry.charging_contact_after == True`.

This is the accepted D-021 `accidental_away_contacts` entry definition.

Once started, contact-active accounting includes only transitions belonging to
the active episode with `mode_before == AWAY` and
`telemetry.charging_contact_after == True`. Thus the entry transition is
counted, as required by D-020's post-action charging semantics. A normal exit
is the first subsequent `True -> False` contact transition; it is recorded but
not counted as contact-active time. Lifetime termination while contact remains
true and controller departure from `AWAY` are classified explicitly. All 275
observed episodes ended by normal contact exit.

For every contact-active transition, the audit uses exact D-020 telemetry:

```text
accepted_stored_charge_j = telemetry.actual_stored_power_w * dt_seconds
electrical_load_energy_j = telemetry.total_electrical_load_w * dt_seconds
```

Gross accepted stored charge is not inferred from battery delta. Episode net
battery change is compared with gross accepted stored charge minus electrical
load, and the residual is retained. The explicit reconciliation tolerance is
`1e-9 J`; all source lifetime and episode reconciliations passed. No
headroom/battery clamp occurred in an incidental episode.

The secondary shadow considers the realized history only through the actual
first low-energy `SEEK` entry. Before each transition it computes:

```text
shadow_battery_before_j = telemetry.battery_before_j
                           - cumulative_prior_incidental_accepted_j
```

The earliest realized `AWAY` decision state with shadow normalized energy
strictly below `0.50` is reported. Current-transition incidental charge is
added only after that state is checked. The shadow stops at the conceptual
policy-divergence boundary and is not a rerun with charging disabled, a policy
counterfactual, or a claim about later actions.

## Programmed / organism-visible / evaluator-only / learned

**PROGRAMMED:** no new organism behaviour. The accepted D-021 controller and
D-020 physics were replayed unchanged; only evaluator audit definitions and
post-hoc arithmetic were added.

**ORGANISM-VISIBLE:** unchanged D-021 six channels: normalized battery,
beacon-left, beacon-forward, beacon-right, charging contact, and normalized own
temperature.

**EVALUATOR-ONLY:** completed mode/action trace, absolute joules and power,
charger phase, physical contact transitions, episode classifications, charge
attribution, residuals, optional charging heat totals, and the open-loop ledger
shadow. None was passed to the controller.

**LEARNED:** none. Reward remains `0.0` and organism-facing info remains `{}`.

No D-020 or D-021 source, controller, physics, ecology, threshold, seed, or
horizon value changed. No visualizer, learning mechanism, new sensor, formal
EXP evidence, or D-023 authorization was added.

## Per-seed direct accounting

Values below are rounded for readability; the JSON retains the computed
floating-point values and every compact episode summary.

| Seed | Episodes | Active seconds | Accepted incidental J | Mean / max episode J | Total lifetime accepted J | Incidental / all accepted | Incidental / capacity | Net battery change J | Charging heat J |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 18365 | 88 | 33.1 | 48.5440 | 0.551636 / 1.4800 | 3134.4335 | 1.5487% | 0.9111% | 12.4740 | 5.3938 |
| 18366 | 92 | 37.5 | 60.5875 | 0.658560 / 1.6650 | 3147.4650 | 1.9250% | 1.1372% | 20.2625 | 6.7319 |
| 18367 | 95 | 33.9 | 51.4485 | 0.541563 / 1.2950 | 3139.1020 | 1.6390% | 0.9656% | 14.0035 | 5.7165 |

Episode durations were:

| Seed | Mean seconds | Median seconds | Maximum seconds | Ending classifications |
|---:|---:|---:|---:|---|
| 18365 | 0.376136 | 0.4 | 0.8 | 88 normal contact exits |
| 18366 | 0.407609 | 0.4 | 0.9 | 92 normal contact exits |
| 18367 | 0.356842 | 0.4 | 0.7 | 95 normal contact exits |

Accepted stored charge grouped by `mode_before`:

| Seed | CHARGE J | DEPART J | AWAY J | SEEK J | Mode sum vs lifetime |
|---:|---:|---:|---:|---:|---|
| 18365 | 3085.5195 | 0.0000 | 48.5440 | 0.3700 | pass, residual `1.05e-11 J` |
| 18366 | 3086.5075 | 0.0000 | 60.5875 | 0.3700 | pass, residual `1.73e-11 J` |
| 18367 | 3087.2835 | 0.0000 | 51.4485 | 0.3700 | pass, residual `1.64e-11 J` |

All `AWAY` accepted charge was classified inside an incidental episode:
unmatched `AWAY` accepted charge was `0.0 J` for every seed. Classified
incidental charge plus unmatched `AWAY` charge reconciled to total `AWAY`
charge within `1e-9 J`. Maximum absolute per-episode bookkeeping residuals
were approximately `4.66e-12 J`, `4.98e-12 J`, and `4.04e-12 J` for the three
seeds respectively.

## D-021 event and shadow timing

| Seed | Actual first low-energy SEEK entry | First physical SEEK reacquisition | Completed cycles | Final normalized energy | Termination |
|---:|---:|---:|---:|---:|---|
| 18365 | 24,570 | 24,575 | 1 | 0.648307 | horizon truncation |
| 18366 | 24,618 | 24,632 | 1 | 0.649966 | horizon truncation |
| 18367 | 24,621 | 24,642 | 1 | 0.648339 | horizon truncation |

| Seed | Open-loop no-incidental crossing | Shift transitions | Shift seconds | Shift / actual time-to-SEEK | Prior incidental J at shadow crossing | Prior incidental J at actual SEEK |
|---:|---:|---:|---:|---:|---:|---:|
| 18365 | 24,331 | 239 | 23.9 | 0.9727% | 26.3255 | 26.3255 |
| 18366 | 24,310 | 308 | 30.8 | 1.2511% | 33.0225 | 33.5775 |
| 18367 | 24,326 | 295 | 29.5 | 1.1982% | 32.1715 | 32.1715 |

No shadow battery clamp was required in any source lifetime. Exact capacity
fractions of incidental charge before the shadow crossing were approximately
`0.4941%`, `0.6198%`, and `0.6038%`; before actual `SEEK` entry they were
`0.4941%`, `0.6302%`, and `0.6038%`.

The shadow values describe the earliest crossing along the fixed realized
history. Once that ledger would have crossed the inherited threshold, the
actual controller could have selected different actions; no later realized
trajectory is claimed as a no-charge autonomous outcome.

## Aggregate summary

Across the three accepted D-021 lifetimes:

- `275` incidental episodes;
- `104.5 s` contact-active time;
- `160.58 J` accepted stored charge;
- per-seed incidental fraction of all accepted charge: mean `1.7042%`, median
  `1.6390%`, range `1.5487–1.9250%`;
- per-seed incidental charge as a battery-capacity fraction: mean `1.0046%`,
  median `0.9656%`, range `0.9111–1.1372%`;
- open-loop threshold-shift range: `23.9–30.8 s` (`239–308` transitions);
- all three seeds show the same qualitative pattern: non-zero but small
  incidental contribution relative to total accepted charging and battery
  capacity, with a measurable roughly 24–31 second shadow shift.

This is a descriptive three-seed development result, not a population claim
and not an arbitrary materiality test. It distinguishes many brief contacts
from zero contribution: contacts were short and individually small, but their
aggregate contribution was measurable and delayed the fixed-ledger threshold
by tens of simulated seconds. It does not establish that the charger ecology
is invalid or that charger geometry should change.

## Surprised by

The contact count of `88–95` did not translate into a large battery
replenishment: the accepted incidental contribution was `48.5440–60.5875 J`
per seed, or `1.5487–1.9250%` of accepted lifetime charge. Nevertheless, the
accumulation shifted the limited open-loop threshold by `23.9–30.8 s` in all
three fixed histories. No unmatched `AWAY` charge or clamp anomaly appeared.

## Provisional reading

**Direct observation:** incidental `AWAY` charging was quantitatively small
relative to the `5328 J` battery capacity and total lifetime accepted charge,
but non-zero. It contributed `160.58 J` across these three lifetimes and
shifted the fixed realized ledger threshold by `23.9–30.8 s`.

**Cautious inference:** within these three accepted D-021 lifetimes, incidental
charging is a measurable but modest confound for the timing of the inherited
`SEEK` transition. The result is not enough to determine whether the ecology
needs modification, and the open-loop shadow is not evidence of behaviour with
charging disabled.

The optional thermal bookkeeping records `5.3938–6.7319 J` of charging body
heat per seed attributable to these episodes. This retains D-021's thermal
null; it does not introduce thermal behaviour or establish a thermal problem.

No substantive D-022 audit was invalidated. No definition, physics value,
controller value, seed, or horizon changed after the contribution output was
first inspected.

## Next

Preserve the current D-021 ecology and treat this result as a quantitative
diagnostic input to Flow's next explicitly authorized developmental question.
Do not pre-authorize D-023 here. Any future ecology change should be justified
by a separate question rather than by an arbitrary percentage cutoff or by
this three-seed result alone.

## Validation and provenance

The implementation and tests were frozen and committed at
`d7b8585bd6a730faae480d2650544d7669e2e001` before substantive D-022 magnitude
output was inspected. The final PR HEAD is recorded in the handoff after PR
creation. D-020/D-021 behaviour and physics remain unchanged; this record and
artifact are Development-lane descriptive outputs only.
