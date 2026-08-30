# D-011 — Fixed non-learning thermal-beacon autonomous reacquisition

- **id:** D-011
- **date:** 2026-08-30
- **authoritative_base_sha:** `e4e5dbf776bbd9bb72420b8bd60d3e8ba1468b58`
- **commit_a_sha:** `18a9ea38bb0bd62e9e952348e6f5f195c3cc0d6d`
- **executed_commit_sha:** `18a9ea38bb0bd62e9e952348e6f5f195c3cc0d6d`
- **commit_b_sha:** pending until this record is committed
- **development_seeds:** `18141, 18142, 18143`
- **horizon:** `1000` transitions per lifetime
- **disposition:** `CONTINUING`

## Question and authorization

D-011 asks whether the existing authorized sensory interface and D-002
thermal/energy ecology can support a complete closed regulatory loop under a
fixed reference controller:

```text
charge → become thermally hot → leave charger → spend time away
→ energy falls → seek with L/F/R beacon → physical reacquisition → repeat
```

This is ordinary developmental work, not a learning experiment and not a
confirmatory claim. ADR 0008 already authorizes controller-visible idealized
left/forward/right beacon values and physical charging contact while keeping
station coordinates, true distance, and heading-to-station evaluator-only.
ADR 0011 authorizes the normalized thermal interoceptive channel. D-002's six
channels are projected into D-011 without changing historical EXP-003, D-002,
D-003, D-008, D-009, or D-010 behavior.

The L/F/R beacon is an already authorized external sensory source deliberately
omitted from the reduced D-003/D-008 observations. This result does not claim
that the beacon resolves every partial-observability problem.

## Fixed reference controller

**PROGRAMMED**

- `D011Controller`, with phases `CHARGE`, `DEPART`, `AWAY`, and `SEEK`.
- Existing D-003 `HOT_DEPART_THRESHOLD` (`0.60`) causes departure; energy
  fullness does not.
- Existing EXP-003 B50 low-energy threshold (`0.50`) enters SEEK from AWAY.
- Existing `seek_beacon_action` supplies the exact historical L/F/R steering
  convention.
- Existing `StochasticPersistentExplorer` supplies AWAY movement and its
  explicit organism-owned policy RNG stream.
- One post-contact setup per seed: body and station are placed at `(0.5, 0.5)`
  while the seeded heading and initial D-002 energy/thermal state are kept.
- One continuous lifetime per seed; no cycle reset, reseeding, or hidden rescue
  controller; horizon `1000`.

In `AWAY`, a contact that occurs while energy is still above the historical
seek threshold is recorded as an accidental AWAY contact and the explorer
continues. It is not converted into a permanent docking solution. Physical
contact during SEEK, rather than beacon strength, is the only reacquisition
event.

**ORGANISM-VISIBLE**

The typed D-011 observation contains exactly:

```text
energy
beacon.left
beacon.forward
beacon.right
charging_contact
thermal
```

The controller also has its own declared phase state and the explorer's own
policy RNG state. Coordinates, distance, heading, seed identity, cycle labels,
transition telemetry, horizon, reward, and future observations are absent.

**LEARNED**

None. D-008 was not involved. No prediction, reward, plastic state, or model
output influenced action selection.

**EVALUATOR-ONLY**

The runner recorded body/station positions, true distance, heading, distance
at SEEK entry, SEEK distance trajectories, mode/cycle summaries, and viability
telemetry only after action selection and the physical transition. These fields
were not controller inputs. Every transition preserved `reward == 0.0` and
`info == {}`.

## Cycle definition

A completed autonomous regulation cycle is counted only when all of these
occur in order within one lifetime:

1. a thermal-triggered CHARGE departure;
2. a physical contact-boundary exit and off-contact interval;
3. a later low-energy SEEK entry while contact is false; and
4. a subsequent post-action transition with physical `charging_contact=True`.

Beacon strength alone never counts. SEEK latency is the reacquisition
transition index minus the low-energy SEEK-entry transition index, so an entry
action that immediately makes contact has latency `0`.

## Execution provenance and repair history

The first Commit-A candidate, `50f50260b307e48a0b650674630cb080853208de`, was
fully validated and executed, but its evaluator exit counter counted the
boundary-crossing transition and the following off-contact DEPART decision.
That execution is invalidated.

The repaired candidate, `5b1fba84b287e81975595674aebe662a2492a87a`, counted only
`charging_contact_before=True → charging_contact_after=False`, but its primary
energy summaries mixed normalized and raw units. That execution is also
invalidated.

The final candidate `18a9ea38bb0bd62e9e952348e6f5f195c3cc0d6d` reports raw energy
in the primary energy fields and explicitly labeled normalized energy fields.
It passed clean validation before the accepted substantive execution below.
No executable changes were made after that execution. The JSON artifact
contains the exact result plus the executed SHA provenance field.

## Validation before accepted execution

From clean `18a9ea38bb0bd62e9e952348e6f5f195c3cc0d6d`:

- `uv run pytest -q`: **595 passed**, 8 existing matplotlib warnings.
- `uv run ruff check .`: **clean**.
- `uv run mypy src --strict`: **clean**.
- `git diff --check`: **clean**.

## Observed results

**Direct observations from**
[`D-011-fixed-non-learning-thermal-beacon-autonomous-reacquisition.json`](D-011-fixed-non-learning-thermal-beacon-autonomous-reacquisition.json):

| Seed | Survival / termination | Min / max / final energy (raw) | Min / max / final thermal | Thermal departures | Physical exits | AWAY entries | Low-energy SEEK | Reacquisitions | Completed cycles | Failed SEEK | Accidental AWAY contacts |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 18141 | horizon truncation | 2.08 / 10.0 / 10.0 | 0.1800000072 / 0.6299999952 / 0.4800000000 | 12 | 13 | 12 | 12 | 12 | 12 | 0 | 3 |
| 18142 | horizon truncation | 0.20 / 10.0 / 8.6 | 0.0500000007 / 0.6299999952 / 0.5600000000 | 12 | 13 | 12 | 11 | 11 | 11 | 0 | 4 |
| 18143 | horizon truncation | 1.60 / 10.0 / 9.8 | 0.1500000059 / 0.6299999952 / 0.6200000000 | 12 | 12 | 11 | 11 | 11 | 11 | 0 | 0 |

The corresponding minimum/maximum/final normalized energy values were
`0.2080000043 / 1.0 / 1.0`, `0.0199999996 / 1.0 / 0.8600000143`, and
`0.1599999964 / 1.0 / 0.9800000191`. Action counts and mode occupancy/entry
counts are preserved in the artifact:

| Seed | MOVE_FORWARD / TURN_LEFT / TURN_RIGHT / WAIT | Mode occupancy `AWAY / CHARGE / DEPART / SEEK` | Mode entries `AWAY / CHARGE / DEPART / SEEK` |
|---:|---:|---:|---:|
| 18141 | 440 / 53 / 40 / 467 | 321 / 467 / 44 / 168 | 12 / 13 / 12 / 12 |
| 18142 | 399 / 73 / 56 / 472 | 309 / 473 / 43 / 175 | 12 / 12 / 12 / 11 |
| 18143 | 398 / 64 / 62 / 476 | 290 / 477 / 45 / 188 | 11 / 12 / 12 / 11 |

SEEK latencies, in episode order, were:

- seed 18141: `11, 15, 15, 15, 15, 15, 15, 15, 16, 14, 6, 4`
- seed 18142: `11, 22, 8, 24, 30, 11, 9, 17, 2, 12, 18`
- seed 18143: `19, 20, 7, 18, 16, 18, 7, 18, 21, 19, 14`

All low-energy SEEK episodes began off-contact and all recorded episodes
reacquired contact before the horizon. The extra physical exits on seeds
18141 and 18142 reflect leaving accidental AWAY contacts; they are not extra
completed regulation cycles.

## Navigation diagnostics

These are evaluator-only descriptive fields, not controller inputs. Distance
at low-energy SEEK entry ranged from:

| Seed | SEEK-entry distance range | SEEK trajectory distance range |
|---:|---:|---:|
| 18141 | `0.182787–0.707107` | `0.056922–0.707107` |
| 18142 | `0.194947–0.707107` | `0.053938–0.707107` |
| 18143 | `0.279308–0.707107` | `0.062385–0.707107` |

The artifact preserves every evaluator-only position, heading, station
position, and distance sample during SEEK. No distance-based decision or
threshold was added.

## Reading and decision gate

**Direct observation:** Every seed repeatedly became thermally hot, departed,
spent an interval off-contact, entered low-energy SEEK, and physically
reacquired the charger. The complete loop was observed 12 times for seed
18141 and 11 times for seeds 18142 and 18143. No SEEK episode failed before
horizon truncation, and no lifetime died from energy or thermal failure.

**Inference:** Under this fixed D-002 ecology, post-contact setup, and fixed
reference controller, the authorized L/F/R signal plus contact is behaviorally
sufficient for repeated physical reacquisition. This is a narrow composition
result, not a proof of universal observability or necessity of the beacon.

**Supported branch:** **A — repeated autonomous departure and reacquisition
succeeds.** The next developmental question should put learning back in the
foreground as a shadow consequence learner receiving the full legitimate
`energy + thermal + L/F/R + contact + own action` information. The fixed
controller should remain the behavioral reference; D-011 does not authorize
learned action selection.

## Surprised by

The simple historical explorer repeatedly reacquired the stationary charger
from evaluator distances up to approximately `0.7071` on all three seeded
headings without any failure episode. Seeds 18141 and 18142 also made several
accidental contacts during AWAY; the explicit continuation rule preserved the
intended distinction between accidental contact and low-energy SEEK
reacquisition.

## Limitations

- This is descriptive D-lane work, not confirmatory evidence.
- It covers three legal development seeds, one horizon, one idealized beacon,
  and one evaluator-side post-contact setup.
- The fixed explorer/controller composition is not evidence that an eventual
  adaptive organism should use this exact FSM or that learning is unnecessary.
- It does not test initial charger discovery from a random position, noise,
  occlusion, moving/depleting stations, or arbitrary headings.
- Distance diagnostics are evaluator-only and were not used to tune or rescue
  behavior.
- No claim about consciousness, emotion, subjective experience, biological
  metabolism, genuine life, intelligence, or a general world model is made.
