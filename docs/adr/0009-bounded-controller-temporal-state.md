# ADR 0009 — Bounded Controller-Visible Temporal State

**Status:** Proposed

## Context

`AGENTS.md` excludes "memory systems" from the current scope unless an
explicit task and, where appropriate, a new ADR authorise them. EXP-003's
specification records the same exclusion for its own slice ("adds no memory"),
and ADR 0008 states that EXP-003 "introduces a real docking problem before
adding memory".

Development work on the localized-charging environment produced
`StationB50TrendController` (`STATION_B50_TREND`), a variant of the historical
`STATION_B50` controller that retains exactly one scalar between decisions:
the maximum of the previous EXPLORE step's controller-visible left/forward/
right beacon values. It uses that scalar for a single anticipatory guard — a
strictly weakening beacon trend at moderate energy enters SEEK earlier than the
historical fixed energy threshold alone would.

That controller cannot be reviewed, merged, or considered as an EXP-004
controller arm while the memory exclusion stands unqualified, because the
exclusion as written does not distinguish between:

- a **memory system** — an accumulating, structured, or learned store the
  organism builds over time (trajectory history, maps, learned parameters,
  episodic recall, persistence across episodes); and
- **bounded within-episode temporal state** — a fixed, small number of scalars
  a controller carries between consecutive decisions in order to compute a
  first difference of its own sensory input.

The second is the minimum any controller needs to react to *change* rather than
*level*. Without this ADR the project cannot test whether change-sensitivity
adds anything beyond level-sensitivity, which is a question the roadmap's
EXP-004 explicitly poses.

## Decision

Bounded controller-visible temporal state is authorised for development and
for experiment arms, subject to all of the following constraints. State outside
these constraints remains excluded and requires its own ADR.

1. **Bounded size.** The persistent policy state is a fixed, enumerated set of
   scalars, declared in the controller's docstring and in the experiment
   document that uses it. It does not grow with episode length. For
   `STATION_B50_TREND` the set is exactly one optional float,
   `previous_explore_beacon_max`.
2. **Controller-visible provenance only.** Every retained value is derived
   solely from the controller's own observation contract as fixed by ADR 0002
   and ADR 0008 — normalized energy, the left/forward/right beacon values, and
   `charging_contact`. Station coordinates, body coordinates, true distance,
   headings, coverage, evaluator feasibility, and any other evaluator-only
   telemetry may never be retained, and retaining a derived quantity may never
   become a route to reconstructing them.
3. **Within-episode only.** State is cleared on `reset()`. Nothing is carried
   across episodes, across seeds, or across runs. No file, checkpoint, or
   process-level store persists it.
4. **Not learned.** Values are overwritten by direct assignment from the
   current observation. No update rule adjusts a parameter from experience, no
   objective is optimised, and no threshold changes as a function of history.
   All thresholds remain fixed constants declared in source. Experience-
   dependent or learned regulation remains out of scope and is governed by the
   separate learning-transition ADR named in the research roadmap.
5. **Declared clearing semantics.** The experiment document states exactly when
   state is set, read, and cleared. Clearing points are part of the frozen
   scientific contract for any experiment that uses the controller, not an
   implementation detail: changing them changes the controller.
6. **No privileged-state laundering.** A retained scalar may not be combined
   across steps to recover information the observation contract withholds. The
   one-step first difference authorised here is the current limit; multi-step
   accumulation, integration, or filtering requires a new ADR because it begins
   to approximate a positional or map-like estimate.

This ADR authorises the mechanism. It does not authorise any specific
experimental claim, seed reservation, calibration, or confirmatory run.

## Rationale

The exclusion list in `AGENTS.md` exists to stop later-stage cognitive
architecture from arriving early and unexamined. A single scalar holding the
previous step's own sensor maximum is not that architecture; it is the smallest
mechanism that lets a controller condition on a derivative of its input. The
project's own working rule is to "prefer the smallest mechanism that tests the
current hypothesis", and the roadmap's EXP-004 asks whether closed-loop control
gains value under environmental change — a question that is not fully testable
if every controller is restricted to instantaneous levels.

Drawing the boundary at *bounded, within-episode, unlearned, observation-
derived* state keeps the load-bearing prohibitions intact. Maps, trajectory
stores, world models, learned parameters, and cross-episode individuality all
remain excluded, and each would require its own authorisation. The constraints
are stated so that a reviewer can check them mechanically against a diff rather
than judging "is this memory?" case by case.

The restriction to a one-step difference (constraint 6) is deliberately tighter
than the other constraints require. Multi-step accumulation over a monotonic
beacon field starts to carry range information the observation contract is
designed to withhold, so it is held back for separate review rather than
granted here by implication.

## Consequences and trade-offs

Reviewers gain an explicit, checkable test for controller state instead of an
unqualified prohibition, and `STATION_B50_TREND` becomes reviewable on its
mechanics rather than blocked on authorisation. The cost is that the memory
exclusion is no longer absolute, so every future controller carrying state must
be checked against the six constraints above; a controller that satisfies them
is authorised, and one that does not is blocked until its own ADR exists. The
boundary between "bounded state" and "memory system" is a judgement the project
now has to maintain deliberately, and constraint 6 in particular will need
revisiting the first time an experiment has a genuine reason to filter or
integrate a signal over more than one step.

Any controller carrying state is harder to reason about than a stateless one:
its behaviour depends on clearing points, so a change to clearing semantics is
a change to the controller and invalidates prior characterization. Experiments
using such controllers must pin the exact source revision, thresholds, and
state semantics they inherited rather than tracking a branch.

Authorising the mechanism does not retroactively authorise evidence produced
before this ADR. Development batches run under the earlier scope remain
exploratory and disclosed as such; they cannot be promoted into calibration or
confirmatory evidence.
