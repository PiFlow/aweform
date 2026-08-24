# ADR 0009 — Bounded One-Step Beacon-Trend Memory

**Status:** Proposed

**Amends:** ADR 0001 (V0.1 non-goal "memory"), narrowly and only for the single
mechanism named below.

## Context

ADR 0001 lists "memory" among V0.1's non-goals without qualification.
`AGENTS.md` excludes "memory systems" unless an explicit task and, where
appropriate, a new ADR authorise them. EXP-003's specification records the same
exclusion for its own slice, and ADR 0008 states that EXP-003 "introduces a
real docking problem before adding memory".

Development work on the localized-charging environment produced
`StationB50TrendController` (`STATION_B50_TREND`), a variant of the historical
`STATION_B50` controller that retains one scalar between decisions and uses it
for a single anticipatory guard: a strictly weakening beacon trend at moderate
energy enters SEEK earlier than the historical fixed energy threshold alone
would.

**This is memory.** A value derived from a previous observation is stored and
changes a later action. Its footprint is one float and one step, but calling it
"temporal state" is an implementation label, not an argument that the memory
exclusion is untouched. This ADR therefore does not claim the mechanism falls
outside the exclusion; it narrowly amends the exclusion to admit exactly this
mechanism, and leaves everything else excluded.

The scientific reason to admit it is specific. The roadmap's EXP-004 asks
whether closed-loop control gains value under environmental change. Answering
that requires at least one controller that can condition on a *change* in its
input rather than only its *level*. One step of beacon history is the smallest
mechanism that provides it.

## Decision

Authorised: exactly one memory variable, in one named controller.

- **Variable:** `StationB50TrendController._previous_explore_beacon_max`,
  exposed read-only as `previous_explore_beacon_max`, of type
  `float | None`. It is the only value this controller retains between
  decisions.
- **Derivation:** `max(left, forward, right)` of the controller-visible beacon
  observation at the previous ordinary EXPLORE decision. No other observation
  component, and no evaluator-only quantity, contributes to it.
- **Retention:** exactly one ordinary EXPLORE decision. Each ordinary EXPLORE
  decision overwrites it by direct assignment. It is never accumulated,
  averaged, integrated, filtered, or combined with an earlier value.
- **Use:** one comparison, `current_beacon_max < previous_explore_beacon_max`,
  as one conjunct of the anticipatory SEEK guard. It has no other effect on
  action selection.
- **Clearing points**, all four of which are part of the frozen scientific
  contract for any experiment using this controller: on `reset()`; on EXPLORE
  entering SEEK by the historical energy rule; on EXPLORE entering SEEK by the
  anticipatory guard; and on CHARGE returning to EXPLORE. Changing any clearing
  point changes the controller and invalidates prior characterization.
- **Fixed thresholds:** the `0.65` anticipatory energy threshold and `0.10`
  weak-beacon threshold remain constants declared in source. No update rule
  adjusts them from experience.

Everything else remains excluded and requires its own ADR before any
development branch may add it. In particular this ADR does **not** authorise:

- a second retained variable in this controller, or any retained variable in
  any other controller;
- retention over more than one decision, or any multi-step accumulation,
  integration, smoothing, or filtering;
- retention of anything not derived solely from the controller's own
  observation contract as fixed by ADR 0002 and ADR 0008;
- any state surviving `reset()`, an episode, a seed, or a run;
- learned, adaptive, episodic, spatial, or map-like memory, or cross-episode
  individuality. Experience-dependent regulation remains governed by the
  separate learning-transition ADR named in the research roadmap.

This ADR authorises the mechanism only. It authorises no experimental claim,
seed reservation, calibration, or confirmatory run.

## Rationale

The narrow form is deliberate. An earlier draft authorised "a fixed, enumerated
set of scalars" for any controller, which is not a bound: a controller carrying
a large bank of one-step observation-derived features satisfies that wording
while being far beyond the mechanism that motivates the decision. Independent
review identified this, and the authorisation was reduced to the one variable
the evidence actually concerns.

The one-step limit is the load-bearing restriction. Multi-step accumulation
over a monotonic, noiseless, unoccluded beacon field begins to carry range
information that ADR 0008 deliberately withholds from the controller, so
extending retention is a boundary question, not a parameter change, and belongs
in its own ADR with its own review.

Naming the mechanism as memory rather than as non-memory matters for the
project's evidence record. Reports on `STATION_B50_TREND` must describe it as a
controller with bounded one-step memory, so that any performance difference
against `STATION_B50` is attributed to that addition rather than presented as
an unexplained improvement in a memory-free organism.

## Consequences and trade-offs

V0.1 no longer has a memory-free organism as an invariant. That is a real
weakening of ADR 0001's non-goal list, and future work cannot cite "V0.1 has no
memory" without qualification.

Because the authorisation names one variable in one controller rather than a
category, every subsequent proposal to retain state requires a new ADR. This is
intentionally slow: the cost is process friction on future controllers, and the
benefit is that the boundary cannot widen by reinterpretation of a general
rule. If the project later wants a reusable class-wide authorisation, that is a
materially larger decision and needs an explicit numerical state budget and an
enforceable registration rule, not a restatement of this ADR.

A controller carrying memory is harder to reason about than a stateless one:
its behaviour depends on clearing points, so experiments using it must pin the
exact source revision, thresholds, clearing points, and state semantics they
inherited rather than tracking a branch.

Authorising the mechanism does not retroactively authorise evidence produced
before this ADR. The `18141–18180` development batch run under the earlier
scope remains exploratory and disclosed as such; it cannot be promoted into
calibration or confirmatory evidence.
