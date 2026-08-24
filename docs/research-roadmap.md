# Aweform Research Roadmap

## A. Purpose

Aweform is being developed from minimal self-maintenance toward adaptive,
machine-native cognition and eventual physical embodiment. The project’s
long-term orientation and humility boundaries are defined in the
[`North Star`](north-star.md); this document adds chronological context and
decision memory without replacing the North Star, developmental principles, or
ADRs.

## B. Completed / evidence ledger

### EXP-000 — Interoception and viability

The question was whether informative access to internal energetic state
improves viability relative to a closely matched fixed-mask, energy-blind
controller in the frozen simulator. EXP-000 is completed with confirmatory
support. Its narrow result concerns the programmed homeostatic mechanism and
that specific ablation in that specific capped simulator; it makes no claim
about consciousness, biological life, intelligence, or general artificial
life. See the canonical [`EXP-000 final result record`](../experiments/EXP-000-final-result-record.md).

### EXP-001 — Interoception versus open-loop homeostasis

EXP-001 is **CLOSED**. Its formal confirmatory result is `C_GREATER`: calibrated
energy-blind C had greater mean capped lifespan than interoceptive B in the
frozen 1000-transition EXP-001 simulator. This is a narrow result for the
specified programmed controllers and environment, not evidence that
interoception is generally harmful or that fixed schedules are generally
superior. See the canonical [`EXP-001 closeout`](../experiments/EXP-001-closeout.md)
and [`EXP-001 calibration record`](../experiments/EXP-001-calibration-record.md).

### EXP-002 — Interoceptive SEEK-entry threshold

EXP-002 asked how the interoceptive SEEK-entry threshold trades off viability
and spatial exploration. Formal calibration completed among the frozen
candidates B35/B40/B45/B50 and selected **B50** using the recorded rule.
B50 is not established as globally optimal: it is the upper tested boundary,
selected for maximum spatial coverage among viability-eligible candidates, not
for competitiveness against C. Confirmatory execution was deliberately
deferred at calibration time. It is now specified but not yet executed: a
confirmatory statistical addendum (separate from, and not modifying, the
frozen pre-calibration protocol below, following the same pattern
[`EXP-001's confirmatory addendum`](../experiments/EXP-001-confirmatory-statistical-addendum.md)
established) freezes B50 vs. the frozen EXP-001 `C_SHORT` comparator as the
primary confirmatory contrast — does calibrating B change, reverse, or narrow
EXP-001's `C_GREATER` result — and B50 vs. B35 as a preregistered key
secondary — does calibrating the SEEK threshold improve B's own mechanism
independent of C. Both are evaluated as a matched triple per seed on the
untouched seeds `50001–51000`, with their own frozen bootstrap convention
(not inherited from EXP-000 or EXP-001). This confirmatory question was
formulated after viewing EXP-002's calibration evidence but before any
confirmatory seed was touched; it was not preregistered before calibration.
See the canonical
[`EXP-002 protocol`](../experiments/EXP-002-interoceptive-seek-threshold.md),
[`EXP-002 calibration evidence`](../experiments/EXP-002-calibration-result.md),
and the [`EXP-002 confirmatory statistical addendum`](../experiments/EXP-002-confirmatory-statistical-addendum.md).

## C. Active

### EXP-003 — Localized charging station + IR-like beacon

EXP-003 is development / instrumentation only. It separates sensing from
energy acquisition, requires physical station occupancy to recharge, maps the
simulation interface toward plausible future robot sensors, and creates a
stronger ecological problem before introducing memory. The active specification
is [`EXP-003 localized charging station`](../experiments/EXP-003-localized-charging-station.md),
and its durable interface decision is [`ADR 0008`](adr/0008-exp-003-localized-charging-interface.md).

## D. Provisional future experiments

These are **PROVISIONAL DEVELOPMENTAL DIRECTIONS**, not frozen protocols or
preregistered experiment numbers. Their exact numbering and order may change.

### EXP-004 — Ecological robustness probe

EXP-001's `C_GREATER` result is consistent with more than one explanation:
that B was never calibrated while C was (EXP-002, above, addresses this
directly); that closed-loop control can exploit per-episode realized state a
fixed timer cannot; or that a fixed schedule may have an advantage in a
stationary environment because it can be calibrated to that fixed
distribution. EXP-004 tests the third explanation directly rather than
assuming it. It replaces the previous provisional EXP-004 ("adaptive
homeostatic regulator") and EXP-005 ("ecological change") with a single
combined design, since the beacon-history mechanism envisioned for the former
is already prototyped (`STATION_B50_TREND`) and can be tested directly under
the latter's perturbation rather than staged separately. That prototype was
built during EXP-003 development work; EXP-003 is closed to further scope
additions (Flow, 2026-08-24), so it is carried forward as EXP-004 preparatory
controller development rather than as an addition to EXP-003. The EXP-003
specification and its existing development records remain canonical as
written.

Reuses EXP-003's station/beacon environment with one hidden perturbation —
station relocation at a seed-determined, hidden time within a preregistered
window — evaluated for `STATION_B50` and a newly-calibrated station-compatible
energy-blind fixed-schedule regulator. `STATION_B50_TREND` is a candidate third
controller only if ADR 0009 (bounded one-step beacon-trend memory) is accepted
and the trend controller development work is independently approved and
merged. Once that happens, it is pinned to an exact, named inheritance from
its development branch (merge SHA, and its exact thresholds, clearing points,
and one-scalar state semantics, all specified in the EXP-004 protocol) rather
than a silently-updated version. If it is not merged in time,
EXP-004 proceeds with `STATION_B50` and the station-compatible regulator, with
the third arm decided separately. The station-compatible regulator uses fixed
mode timing only — it still steers locally via the same L/F/R beacon signal
during SEEK as B and T, and returns to SEEK immediately if charging contact is
lost, including from relocation, rather than blindly waiting out a fixed timer
at a station that no longer exists. Each included controller runs in a
stationary and a one-hidden-relocation condition; the three-controller version
therefore has six matched cells per seed.
The relocation schedule is generated once per master seed from a dedicated
perturbation RNG, independent of environment/policy RNG streams and of
controller behavior, and applied identically across the included controllers;
with T included, this means all three, otherwise both.

The primary question is whether B's advantage over the station-compatible
regulator changes between the relocation and stationary conditions. If T is
included, the key secondary is the same question for T's advantage over B —
whether one-step beacon history gains relative value under relocation beyond
what plain energy feedback already provides. The station-compatible regulator
is a different controller in a different (station) environment from frozen
EXP-001/002 `C_SHORT`, so this does not directly retest `C_GREATER`; it tests
whether a similar fixed-schedule-advantage pattern reappears in the new
environment. The formal estimand definition (endpoint, contrast, sign
convention, and interpretation rule) is deferred to the EXP-004 protocol
document and is not fixed by this roadmap entry.
Pre-formal work uses separate seed roles — station-compatible regulator
calibration, then development characterization of the included controller
cells (including horizon-adequacy and relocation-exposure-adequacy checks),
then untouched confirmatory seeds — reserved in the EXP-004 protocol rather
than in this roadmap.

### Learning-transition ADR

A parallel work item, not a numbered provisional experiment: before any
experience-dependent or learned regulation is roadmapped, an ADR specifies a
three-tier seed discipline — free design/development seeds; a finite,
enumerated, pre-frozen model-selection/hyperparameter grid; untouched
confirmatory seeds, with any post-freeze architecture change requiring a new
named experiment revision rather than reopening the current one — and treats
organism/lifetime definition, learned-state persistence, reset semantics, the
inheritance-versus-learning boundary, and update timing as part of the frozen
scientific contract, not implementation detail. Whether the experiment after
EXP-004 is a learning experiment or EXP-006 (below) is an evidence-based
choice made once EXP-004 and this ADR both land, not a pre-committed number.

### EXP-006 — Occlusion / obstacles

Allow beacon evidence to become unavailable or misleading through walls or
geometry, creating a genuine need for spatial memory, prediction, or a
primitive world model. Its position directly after EXP-004 is not fixed: a
learning-transition experiment may be inserted before it, numbered at that
time, if the ADR above resolves its methodology in time.

### Later directions

Later developmental directions include learned adaptation rather than fully
hand-designed regulation; persistent memory and individuality through
experience; prediction/world models; play and curiosity when viability permits
surplus exploration; social interaction and machine-native communication; and
eventual physical embodiment. These remain aligned with the
[`North Star`](north-star.md) and [`developmental principles`](developmental-principles.md).
The learning-transition ADR above begins scoping the first item in this list;
it does not by itself authorize implementation.

Future roadmap items are hypotheses and developmental directions. They are
allowed to change when evidence creates a better next question.

## E. Decision-log convention

- Experiment-specific frozen decisions live in `experiments/`.
- Durable architecture and information-boundary decisions live in `docs/adr/`.
- This roadmap gives chronological context and provisional future direction.
- Result artifacts remain canonical evidence.
- Roadmap prose must never silently overwrite historical experiment records.
