# D-023 — Repeated-cycle V0.4 energy-regulation endurance probe

- **id:** D-023
- **lane:** Development
- **date:** 2026-09-03
- **authoritative_base_sha:** `a7c66a8bc096baf61b50bc3963b6cf19a6d38f83`
- **implementation_probe_sha:** `87fa6192556b51bab4b0aa138ecb3a39be104abc`
- **development_seeds:** `18365, 18366, 18367`
- **horizon:** `210,000` transitions per uninterrupted lifetime (`21,000.0 s`)
- **disposition:** `CONTINUING`
- **learned mechanism:** none

## Scientific question and scope

D-023 asks whether the unchanged D-020 V0.4 physical body and unchanged
D-021 fixed non-learning controller continue regulating energy across several
consecutive cycles in one uninterrupted lifetime. It is descriptive
Development-lane work and makes no confirmatory claim.

The exact frozen observation window is `D023_HORIZON = 3 * D021_HORIZON =
210,000` transitions. The only execution-window change is the D-021 runner
horizon. The exact already-used development seeds are reused; no formal
reservation or new seed is introduced.

## PROGRAMMED

- `D021Controller` modes `CHARGE`, `DEPART`, `AWAY`, and `SEEK`, unchanged.
- Full departure at normalized energy `>= 1.0` while in physical contact.
- Low-energy SEEK entry below inherited `0.50`.
- Existing `StochasticPersistentExplorer` with fixed `1/8` hazard.
- Existing `seek_beacon_action`.
- D-020 physical bookkeeping, charger/contact semantics, battery accounting,
  thermal accounting, and shutdown thresholds, unchanged.
- No learner, predictor, planning, reward shaping, curiosity, play, or
  plastic state.

## ORGANISM-VISIBLE

Exactly six channels are passed through the existing D-021 projection:

1. normalized own battery energy;
2. beacon left;
3. beacon forward;
4. beacon right;
5. binary physical charging contact;
6. normalized own current body temperature.

Temperature has zero programmed behavioural influence. Every transition retains
`reward == 0.0` and organism-facing `info == {}`.

## EVALUATOR-ONLY

The runner may inspect inherited D-020/D-021 evaluator state after action
selection and stepping: position/heading, station location and true distance,
battery joules, absolute Celsius, charger phase/latch and telemetry, mode and
action traces, contact transitions, cycle events, SEEK timing/outcomes,
termination reason, and inherited incidental AWAY contact counts. None enters
action selection or a learning signal. There is no D-022 counterfactual audit.

## LEARNED

None. This is a fixed-controller endurance probe.

## Frozen validation and provenance

Before substantive output inspection, the executable specification, fixed
horizon, metrics, and implementation are committed. For each seed, the first
`70,000` completed transitions are compared against the accepted D-021 trace
for exact actions, modes, six-channel observations, reward/info, and complete
D-020 telemetry, exempting only D-021's final horizon-derived `truncated`
label. Same-seed replay, seed/reservation guards, and the existing D-020/D-021
boundary tests are retained.

The machine-readable artifact records the exact executed SHA and compact
per-seed/per-cycle summaries. No raw 210,000-transition trace is stored.

## Direct observations

The frozen artifact reports the following compact per-seed results:

| Seed | Completed cycles | Full departures | Cycle exits | SEEK / reacquisition | Full recharge / re-departure | Final mode | Min / final battery (J) | Max / final body temperature (°C) | Incidental AWAY contacts |
|---:|---:|---:|---:|---|---|---|---:|---:|---:|
| 18365 | 3 | 4 | 4 | 4 / 4 (`5, 16, 16, 16` transitions) | 3 / 3 | CHARGE | 2662.2925 / 5311.2545 | 24.280806 / 23.850058 | 196 |
| 18366 | 3 | 4 | 4 | 4 / 4 (`14, 12, 29, 23` transitions) | 3 / 3 | CHARGE | 2661.1260 / 5307.8980 | 24.280950 / 23.851843 | 197 |
| 18367 | 3 | 4 | 4 | 4 / 4 (`21, 19, 13, 15` transitions) | 3 / 3 | CHARGE | 2661.8715 / 5305.7475 | 24.281013 / 23.853111 | 225 |

Each lifetime completed `210,000` transitions / `21,000.0 s` and ended by
horizon truncation in `CHARGE`. Each had four low-energy SEEK entries and
four physical reacquisitions; the fourth reacquisition was horizon-censored
before full recharge and re-departure. No lifetime depleted energy, reached
the preferred `45 °C` ceiling, or underwent protective or emergency thermal
shutdown. All prefix controls matched the accepted D-021 first `70,000`
transitions with zero mismatches, ignoring only the D-021 final
horizon-derived `telemetry.truncated` label. No mode/event inconsistencies
were reported.

The four cycle summaries per seed preserve the entry, cycle-relevant charger
exit, SEEK entry, reacquisition, full-recharge, and post-recharge departure
transition indices in the JSON artifact. The fourth summary is explicitly
`horizon_censored`.

No result magnitude was used to select the horizon, seeds, controller,
physical values, or interpretation criteria.

## Cautious inference

Under these three declared development lifetimes, the unchanged fixed D-021
controller completed three full repeated regulation cycles without energy
depletion or thermal shutdown. The narrow inference is repeated-cycle
endurance of this exact fixed V0.4 baseline on these three lifetimes only. It
does not establish broad robustness, optimality, learning, intelligence,
metabolism, consciousness, emotion, subjective experience, genuine life, or
hardware autonomy.

## Surprises / nulls

The near-ambient thermal result remains a legitimate null if it occurs. Any
failed reacquisition, depletion, stuck behaviour, or thermal shutdown remains
part of the valid descriptive result. A 210,000-transition window that yields
too little repeated-cycle evidence is reported as a limitation; the horizon is
not extended after inspection.

## Invalidated attempts

The first artifact-writing invocation used the incorrect manually supplied SHA
`87fa619d46d7c4df4c0e4cf45e9ca2f3c4d8410b`, which did not equal the frozen
commit; its measurements were not used as a separate scientific attempt. The
artifact was deterministically regenerated with the exact frozen
implementation SHA above. No controller, horizon, physical value, seed, or
interpretation criterion changed.

## Disposition

`CONTINUING`. D-023 does not authorize an EXP protocol, a learner, ecology or
physics changes, visualization tooling, or later developmental work.
