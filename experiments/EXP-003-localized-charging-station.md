# EXP-003 — Localized charging station and idealized IR-like beacon

**Status:** development / instrumentation only

**Protocol status:** not a formal confirmatory experiment

**Development revision:** `EXP-003-development-foundation-001`

## Primary developmental question

> Can the B50-derived homeostatic regulator maintain viability when resource
> sensing and energy acquisition are separated, such that energy is obtained
> only by physically occupying a localized charging station approached through
> simple left/forward/right beacon sensing?

This slice does not define a confirmatory hypothesis, primary statistical
endpoint, acceptance condition, or formal EXP-003 calibration. The purpose is
to make the ecological and instrumentation foundation testable before any
parameter selection or confirmatory protocol is considered.

## Developmental reason

EXP-002 selected B50 among the tested B35/B40/B45/B50 development candidates,
but B50 is not established as globally optimal: it is the upper tested
boundary. EXP-003 changes the ecological interface to separate sensing from
consumption. A station emits a local signal, while energy is acquired only
when the body centre is physically inside the station's charging circle.

The intended future hardware analogue is deliberately minimal: left, forward,
and right directional IR-like receivers plus a charging-contact/current
detector. The simulated beacon is an idealized abstraction, not a physically
accurate infrared-radiation model.

## Environment

EXP-003 is a new environment. The frozen EXP-001/EXP-002 field environment is
not changed. The following development values are preserved from that field
environment unless explicitly listed as the new station mechanism:

| Parameter | Development value |
|---|---:|
| world bounds | `[(0.0, 0.0), (1.0, 1.0)]` |
| maximum / failure energy | `10.0 / 0.0` |
| initial energy | `5.0` |
| basal cost per transition | `0.1` |
| movement distance | `0.05` |
| turn angle | `pi / 4` |
| WAIT / turn / forward cost | `0.0 / 0.02 / 0.1` |
| directional probe distance / sensor angle | `0.1 / pi / 4` |
| episode horizon | `1000` transitions |
| stochastic EXPLORE hazard | `1 / 8` |

New development values:

| Parameter | Development value |
|---|---:|
| charging radius | `0.10` |
| fixed charge input while inside | `0.5` energy units / transition |
| beacon scale | `0.25` |
| minimum initial station separation | `0.20` world units |

The station is one stationary circle per episode. Its centre is sampled from
the valid centre rectangle
`x, y in [radius, 1-radius]` using the environment RNG. Candidates are
rejected until the strict condition
`distance(body_start, station_centre) > 0.20` holds. Exactly 10,000 sampled
candidates are permitted; failure to find one raises a deterministic runtime
error. There is no fallback placement and no second RNG source. This makes the
placement reproducible and prevents a trivial initial charging state.

After each action, charging is evaluated from the body's actual post-transition
centre:

- outside or on neither side of the charging circle: harvested energy is
  exactly `0.0`;
- inside or on the circle boundary: fixed charge input is exactly `0.5`.

Ordinary basal, movement, turn, and wait costs still apply. Crossing the circle
during a forward segment does not charge if the final body centre is outside.
The contact boundary uses the same closed-circle test as charging.

## Beacon and controller observation boundary

For distance `d` from a virtual probe to the station centre:

`signal(d) = 1 / (1 + (d / beacon_scale)^2)`

The signal is deterministic, monotonic with distance, normalized to `(0, 1]`,
has no RNG, noise, occlusion, interference, depletion, or detection cutoff.

The typed STATION_B50 observation is:

```text
StationObservation(
    energy,
    BeaconObservation(left, forward, right, charging_contact),
)
```

The controller receives actual normalized energy, three directional beacon
values, and the boolean `charging_contact`. It never receives station
coordinates, true station distance, heading-to-station, coverage, or future
outcomes. `charging_contact` is controller-visible by design because it models
a future charging-current/contact sensor and is causally determined by actual
physical zone occupancy.

## STATION_B50 controller

STATION_B50 preserves the historical B50-derived thresholds and mechanism:

- enter SEEK when normalized energy is `< 0.50`;
- recover to EXPLORE when normalized energy is `> 0.85`;
- use the unchanged stochastic EXPLORE primitive and left/forward/right
  steering tie convention;
- WAIT while in CHARGE and physically on the station.

The ecological adaptation is only docking semantics. SEEK enters CHARGE only
when `charging_contact == true`; arbitrary beacon strength is insufficient.
If contact becomes false during CHARGE, the controller returns to SEEK. Thus
the thresholds are preserved, while historical external resource contact has
become actual physical charging contact because sensing and energy uptake are
separate in this environment. Historical EXP-002 B50 is not modified.

## Development comparison and diagnostics

The development runner compares matched ordinary seeds for:

1. `FIELD_B50`: the historical frozen EXP-002 B50 in the old field
   environment, executed through its existing path;
2. `STATION_B50`: the new station environment and controller.

This comparison is descriptive only and does not pool EXP-002 calibration
episodes with EXP-003 observations.

For matched ordinary seeds, the station reset preserves the historical field
environment's body-position and heading draw order. The station's own centre
is then sampled from the environment RNG after those matched body draws.

STATION_B50 evaluator-only diagnostics include capped lifespan, horizon
survival, final and minimum normalized energy, total charged energy, total
distance, 32x32 unique-cell coverage, EXPLORE action count and distance,
recharge cycles, station entries, transitions on the charger, SEEK-onset
energy and true station distance, successful-acquisition energy, SEEK attempt
count and success fraction, onset-to-acquisition transitions, and minimum
energy per SEEK attempt. Station coordinates, true distance, and coverage have
no causal path into the controller.

## Seed reservations

Existing EXP-000/EXP-001/EXP-002 reservations were inspected before adding
these unused EXP-003 reservations:

- development/calibration reservation: `60001–60200` inclusive;
- confirmatory reservation: `70001–71000` inclusive.

These reservations do not authorize execution. Development tests and visual
smoke runs use ordinary seeds outside every reserved range. No formal EXP-003
calibration or confirmation is implemented or executed in this slice. EXP-002
confirmatory seeds `50001–51000` remain untouched.

## Scope exclusions

This slice adds no memory, learning, adaptive regulator D, obstacles,
occlusion, beacon noise, charger movement or depletion, multiple stations,
maps, camera perception, Bluetooth logic, neural networks, reinforcement
learning, formal calibration, or formal confirmation.
