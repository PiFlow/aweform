# ADR 0009 — BOHS Registry

**Status:** In effect for controllers carrying bounded one-step
observation-history state (BOHS), as required by
[`0009-v0.2-bounded-observation-history-state.md`](0009-v0.2-bounded-observation-history-state.md)
Section D.

**Covered controllers:** `StationB50Controller` and its subclass
`StationB50TrendController` in `src/aweform/exp003.py`. `StationB50FullController`
inherits the base rows below; it carries no BOHS field of its own.

This manifest classifies **all** retained action-relevant and diagnostic state
of each covered controller, not only its BOHS fields — a registry with BOHS
rows alone cannot express that `_last_decision` is diagnostic-only, which is
the claim Section E of ADR 0009 depends on. It includes retained root objects
and their nested action state; transient locals of `act()` are not fields and
are not listed.

The manifest is the union of the per-controller declarations emitted in source
(`RETAINED_STATE` on `StationB50Controller` and
`StationB50TrendController`) plus the nested retained state of the root
objects they name. The checks in
`tests/test_exp003_bohs_enforcement.py` validate that this manifest is
complete against the live instances and that every named attribute exists.

## Classifications

- **`bohs`** — an authorised observation-history field. Requires: declared
  type; the fixed observation function of ADR 0009 B.2; every registered
  clearing point; the complete reader set; budget consumption (always 1).
- **`causal-inherited`** — retained state on the action path that ADR 0009 does
  not authorise and does not modify. Requires: the source that governs it.
  `config`, `explorer`, `_mode`, the explorer segment counters, and
  `policy_rng` are these.
- **`diagnostic`** — retained state with **no action-selection reads**.
  Requires: the complete reader set, all of which must be external inspection.
  `_last_decision` is this.

## Registry

### `StationB50Controller`

| Attribute | Classification | Required fields / notes |
|---|---|---|
| `_mode` | `causal-inherited` | Governed by the EXP-003 specification and ADR 0008 (three-mode `EXPLORE`/`SEEK`/`CHARGE`). Retained across decisions; influences action selection and mode transitions. |
| `config` | `causal-inherited` | Construction-invariant `EXP003ControllerConfig` (`enter_seek`, `recover`, `exploration_hazard`). Governed by the EXP-003 specification and ADR 0008. Meets the five ADR 0009 B.5 properties, all verified by the checks: initialized before the first `act()`; underlying value immutable for the run (frozen dataclass); controller-visible binding read-only after initialization — `config` is a read-only property (no setter/deleter) backed by the `_config` slot, so it cannot be rebound by assignment, `del`, or direct `vars(self)["config"]` mutation (the property data-descriptor shadows any `__dict__` entry); and the backing `_config` slot is itself frozen, so `del c._config` then `c._config = adversarial` cannot swap the value the property returns; independent of observations/history; and unable to encode a branch bit. A frozen dataclass value alone proves none of these — the binding freeze and the readonly property do. |
| `explorer` | `causal-inherited` | Retained EXP-001 run-and-turn primitive (`StochasticPersistentExplorer`). Governed by the EXP-001 specification and ADR 0004. Nested retained action state below. |
| `_last_decision` | `diagnostic` | Decision trace (`EXP003ControllerDecision`). Complete reader set (ADR 0009 E): the `last_decision` property and other **external inspection only** — no action-selection branch reads it. No BOHS budget consumed (ADR 0009 E). |

Nested retained state of `explorer`:

| Attribute | Classification | Required fields / notes |
|---|---|---|
| `explorer.policy_rng` | `causal-inherited` | `numpy.random.Generator`. Governed by the experiments' seed and RNG-stream conventions. Advances on every run-length sample. |
| `explorer._forward_actions_remaining` | `causal-inherited` | Run-and-turn primitive counter. Governed by EXP-001 and ADR 0004. |
| `explorer._turn_action` | `causal-inherited` | Run-and-turn primitive turn choice (`None` or `Action`). Governed by EXP-001 and ADR 0004. |
| `explorer._turn_actions_remaining` | `causal-inherited` | Run-and-turn primitive counter. Governed by EXP-001 and ADR 0004. |

### `StationB50TrendController`

Adds one BOHS field on top of the base rows above.

| Attribute | Classification | Required fields / notes |
|---|---|---|
| `_previous_explore_beacon_max` | `bohs` | Declared type `float \| None`. Fixed observation function (ADR 0009 B.2): `max` over the current observation's beacon `left`/`forward`/`right` — a copy of one controller-visible selection, applied unconditionally at the single observation-write point. Registered clearing points (ADR 0009 B.3): construction (`__init__`), `E1`, `E2`, `C2`, and `reset`. Complete reader set (ADR 0009 B.4): the EXPLORE-entry snapshot (the field is loaded into `previous_max` on **every** EXPLORE path before any guard runs, so the E2 navigation guard reads that snapshot of the immediately preceding value) and the `previous_explore_beacon_max` property (external inspection). Budget consumption: 1 (ADR 0009 C). Uniquely among the covered state, it is `bohs`; the only observation-write value the controller ever stores. |

## Notes

- **Write cadence.** `_previous_explore_beacon_max` is written at most once per
  `act()` (ADR 0009 B.7) and never by any writer outside the controller.
- **Lifetime.** Cleared by `reset()` and by every registered clearing point;
  never survives a `reset()`, episode, seed, or run (ADR 0009 B.8).
- **Threshold governance (ADR 0009 B.9).** The BOHS-specific thresholds
  (`EXP003_TREND_ANTICIPATORY_ENERGY_THRESHOLD` and
  `EXP003_TREND_WEAK_BEACON_THRESHOLD`) are `Final[float]` constants in
  `exp003.py`; the inherited `EXP003ControllerConfig` fields are set once at
  construction and never adjusted from experience.
- **Provenance (ADR 0009 B.10).** The BOHS value derives solely from the
  controller's own observation contract (`observation.beacon.as_tuple()`) as
  fixed by ADR 0002 and ADR 0008. No evaluator-only or privileged simulator
  state.
- **Boundary guarantee (ADR 0009 B.1).** `BeaconObservation` rejects every
  non-built-in-float `left`/`forward`/`right` value (int, bool, and non-built-in
  numerics such as `numpy.float64`), so `max` over the observation triple always
  produces a genuine built-in `float`; `_previous_explore_beacon_max` is thus
  `float` after an observation write and `None` otherwise. This is enforced at
  the observation boundary and verified by the checks and the adversarial
  integer/boolean tests.
