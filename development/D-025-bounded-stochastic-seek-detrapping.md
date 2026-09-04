# D-025 — Bounded stochastic SEEK de-trapping

- **id:** D-025
- **lane:** Development
- **authoritative_base_sha:** `d661029e2c9be63274cb9109a7bb6d685bc29751`
- **development_seeds:** `18365, 18366, 18367`
- **horizon:** `70,000` transitions per uninterrupted lifetime
- **delegation probability:** exactly `1/8`
- **disposition:** `CONTINUING` (pending descriptive outcome)

## Question and frozen scope

D-025 tests whether bounded stochastic delegation to the already-existing
`StochasticPersistentExplorer` can break the deterministic D-024 point-beacon
SEEK attractor and permit causal rear dual-contact reacquisition. It changes
only action arbitration in false-contact `SEEK`. The D-024 environment,
initial state, four-action set, six organism-visible channels, reward `0.0`,
and `info == {}` are inherited unchanged. No learner, plastic state, new
signal, reverse motion, oscillation detector, adaptive probability, or
ecology change is introduced.

For each false-contact SEEK decision, the runner computes the historical
`seek_beacon_action()` result, draws once from the continuous per-seed policy
RNG, and delegates exactly when the draw is below `1/8`. Delegation calls the
existing explorer with the current visible L/F/R values wrapped in its
`ExternalObservation`. Otherwise the greedy action executes. On SEEK entry,
the explorer's existing `begin_segment()` is called once, without reseeding or
advancing its RNG. The `1/8` value reuses `EXP001_EXPLORER_HAZARD` as an
engineering scale for this probe; it is not a biological claim or learned
value.

The canonical run is frozen before substantive outcomes are inspected. Each
seed starts from the exact D-024 valid docked state: station `(0.50, 0.50)`,
body centre `(0.55, 0.50)`, heading `0`, battery `5328.0 J`, temperature
`23.0 °C`, latch false, and controller mode `CHARGE`. The D-024 rear
dual-contact predicate remains corresponding pair errors inclusive `<= 0.01`.
The physical configuration and transition order are unchanged.

## Provenance and diagnostics

The executable source records the frozen base, seeds, horizon, RNG semantics,
boundary, and interpretation rules in its manifest. Every result records the
initial dual-contact validity, initial departure and first contact loss,
pre-SEEK deterministic D-024 prefix validation, SEEK arbitration records and
counts, delegated action types, effective perturbations, first effective
perturbation state, causal dual-contact entries by mode, SEEK pair-error
minima and earliest poses, one-pair tolerance events, recharge/redeparture,
thermal/energy termination, and consistency failures. Geometry, pair errors,
counterfactual greedy labels, delegation labels, RNG draws, and event
classifications are evaluator-only.

The D-024 comparator is a deterministic replay only; its historical source,
record, artifact, and interpretation are unchanged. Prefix validation compares
the completed transitions through the AWAY transition immediately before the
first D-025 SEEK decision, including the visible state and transition
telemetry. Visualization, if used, is post-hoc tooling and cannot influence a
run.

## Classification and interpretation

Each seed is classified narrowly as:

- `SEEK_REACQUIRED` — false-contact SEEK later establishes causal dual contact;
- `FULL_CYCLE` — SEEK reacquisition is followed by full recharge and
  post-recharge departure in the same lifetime;
- `FAILED_SEEK` — natural termination after false-contact SEEK begins before
  reacquisition;
- `HORIZON_CENSORED` — unresolved at transition `70,000`.

An incidental AWAY dual-contact entry is not a SEEK solution. There is no
scientific PASS threshold. Any result supports only a cautious descriptive
statement about these three declared development lifetimes and this frozen
mechanism; it does not establish robustness, optimality, learning, or general
sufficiency. Negative or null outcomes are preserved.

## Validation plan

The frozen implementation is checked for exact base ancestry, legal seeds and
horizon, D-024 initial state and contact predicate, unchanged six-channel and
reward/info boundary, D-021 non-SEEK behavior, deterministic one-draw
arbitration, fresh explorer segment without reseeding, greedy default,
evaluator-only diagnostics, natural termination versus censoring, unchanged
D-024 artifacts, focused/full tests, Ruff, strict mypy, compileall, diff
whitespace, canonical visualization replay, and exact-current-HEAD CI.

Substantive machine-readable outcomes are in
[`D-025-bounded-stochastic-seek-detrapping.json`](D-025-bounded-stochastic-seek-detrapping.json).
