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
B50 is not established as globally optimal because it is the upper tested
boundary, not an exhaustive search. Confirmatory execution is deliberately
deferred. Seeds `50001–51000` remain reserved and untouched. See the canonical
[`EXP-002 protocol`](../experiments/EXP-002-interoceptive-seek-threshold.md)
and [`EXP-002 calibration evidence`](../experiments/EXP-002-calibration-result.md).

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

### EXP-004 — Adaptive homeostatic regulator ("D")

Combine actual internal energy with minimal short-term history of the
controller-visible beacon: for example current/recent beacon strength, recent
trend, or time since strong charger evidence. Do not expose station
coordinates or true distance. Ask whether context-sensitive return decisions
outperform a fixed threshold. Memory is introduced only because the station
world creates a reason to use it.

### EXP-005 — Ecological change

Introduce one challenge at a time, such as charger depletion, disappearance,
or relocation, and test adaptation rather than assuming a permanently
available resource.

### EXP-006 — Occlusion / obstacles

Allow beacon evidence to become unavailable or misleading through walls or
geometry, creating a genuine need for spatial memory, prediction, or a
primitive world model.

### Later directions

Later developmental directions include learned adaptation rather than fully
hand-designed regulation; persistent memory and individuality through
experience; prediction/world models; play and curiosity when viability permits
surplus exploration; social interaction and machine-native communication; and
eventual physical embodiment. These remain aligned with the
[`North Star`](north-star.md) and [`developmental principles`](developmental-principles.md).

Future roadmap items are hypotheses and developmental directions. They are
allowed to change when evidence creates a better next question.

## E. Decision-log convention

- Experiment-specific frozen decisions live in `experiments/`.
- Durable architecture and information-boundary decisions live in `docs/adr/`.
- This roadmap gives chronological context and provisional future direction.
- Result artifacts remain canonical evidence.
- Roadmap prose must never silently overwrite historical experiment records.
