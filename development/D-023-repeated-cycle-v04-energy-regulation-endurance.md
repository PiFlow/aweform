# D-023 — Repeated-cycle V0.4 energy-regulation endurance probe

- **id:** D-023
- **lane:** Development
- **date:** 2026-09-03
- **authoritative_base_sha:** `a7c66a8bc096baf61b50bc3963b6cf19a6d38f83`
- **implementation_probe_sha:** `TO_BE_FILLED_AFTER_FREEZE`
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

To be completed from the frozen exact-SHA artifact after implementation
validation. No result magnitude was used to select the horizon, seeds,
controller, physical values, or interpretation criteria.

## Cautious inference

If the lifetimes complete several coherent cycles without depletion or thermal
shutdown, the narrow inference is repeated-cycle endurance of this exact fixed
V0.4 baseline on these three declared development lifetimes only. It does not
establish robustness, optimality, learning, intelligence, metabolism,
consciousness, emotion, subjective experience, genuine life, or hardware
autonomy.

## Surprises / nulls

The near-ambient thermal result remains a legitimate null if it occurs. Any
failed reacquisition, depletion, stuck behaviour, or thermal shutdown remains
part of the valid descriptive result. A 210,000-transition window that yields
too little repeated-cycle evidence is reported as a limitation; the horizon is
not extended after inspection.

## Invalidated attempts

None known at freeze time. Any genuine implementation/reporting defect will be
recorded here with its exact SHA and invalidated output before a corrected
rerun; scientific retuning is not permitted.

## Disposition

`CONTINUING`. D-023 does not authorize an EXP protocol, a learner, ecology or
physics changes, visualization tooling, or later developmental work.
