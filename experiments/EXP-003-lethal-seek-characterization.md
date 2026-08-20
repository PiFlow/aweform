# EXP-003 lethal-SEEK characterization

> **DEVELOPMENT / DESCRIPTIVE CHARACTERIZATION ONLY**
>
> This is not a formal EXP-003 protocol, not formal calibration, not
> confirmatory evidence, and contains no preregistered statistical claim.

## Purpose

This development slice asks whether the lethal STATION_B50 SEEK attempts in
the existing localized-charging environment are already infeasible at SEEK
onset under an optimistic, charge-aware straight-line reserve threshold, or
whether they remain unexplained by the available reserve and geometric
distance.

The existing controller, environment, contact and charging dynamics, beacon,
parameters, observations, and RNG ownership were unchanged. No parameter was
tuned in response to these observations.

## Reproducibility and scope

- Ordinary development seeds used: `18021–18040` inclusive.
- Source SHA used for the characterization execution:
  `71e2e19`.
- No EXP-002 confirmatory seed `50001–51000` was executed.
- No EXP-003 reserved seed `60001–60200` or `70001–71000` was executed.
- No formal result artifact, formal calibration, confirmatory execution, or
  EXP-004 work was started.

## Evaluator-only definitions

For each SEEK attempt, all values in this section are derived from privileged
telemetry and are not present in the controller observation.

Let `r` be the unchanged development charging radius, `d_onset` the true
station distance at SEEK onset, `m` the unchanged movement distance, `b` the
basal cost, `c` the movement cost, `q = b + c`, and `h` the unchanged charge
rate.

```text
distance_to_charging_boundary = max(0, d_onset - r)
optimistic_minimum_forward_transitions
    = ceil(distance_to_charging_boundary / m)
optimistic_onset_reserve_threshold
    = 0,                                  if n == 0
    = (n - 1) * q + max(0, q - h),         if n >= 1
available_onset_energy_above_failure
    = actual_energy_at_onset - failure_boundary
optimistic_reserve_margin
    = available_onset_energy_above_failure
      - optimistic_onset_reserve_threshold
```

Here `n` is `optimistic_minimum_forward_transitions`. Under this approximation,
the attempt is feasible only when
`available_onset_energy_above_failure > optimistic_onset_reserve_threshold`.
A zero margin is not viable because the simulator requires energy strictly
above the failure boundary. For `n == 0`, the body is already within charging
contact and the threshold is zero. For `n >= 1`, the first `n - 1` forward
transitions occur outside the charger, while the final transition receives
`h` on that same transition before basal/action costs and viability are
evaluated.

This remains an optimistic evaluator-only geometric bound. It assumes perfect
straight-line progress, ignores turning and steering inefficiency, and does
include the existing same-transition acquisition-charge semantics. A positive
margin does not prove that the real controller will acquire.

Per-attempt action counts and nominal configured cost sums are also
evaluator-only: MOVE_FORWARD, TURN_LEFT, TURN_RIGHT, and WAIT counts; nominal
basal cost sum; nominal action-cost sum; nominal total cost sum; terminal
distance; boundary-clamp diagnostics; and outside-to-outside charger
pass-through count. These are scheduled/configured cost demands, not a
decomposition of realised state-energy loss.

## Batch results

The outcome totals were:

| Outcome | Count |
| --- | ---: |
| ACQUIRED | 281 |
| TERMINATED_BEFORE_ACQUISITION | 9 |
| HORIZON_CENSORED | 3 |
| Resolved-only acquisition fraction | `281 / 290 = 0.968965517` |

Horizon-censored attempts are excluded from the resolved denominator.

For descriptive context, the matched batch had the following means:

| Condition | Horizon survivors | Capped lifespan | Final normalized energy | Minimum normalized energy | Coverage | EXPLORE distance | EXPLORE actions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| FIELD_B50 | 19/20 | 990.400 | — | — | 0.466406 | 18.223644 | 659.500 |
| STATION_B50 | 11/20 | 848.250 | 0.335700 | 0.033000 | 0.426709 | 12.985263 | 399.600 |

Both distance values are EXPLORE-only distance: `distance_travelled_during_explore`
for FIELD_B50 and `explore_distance_travelled` for STATION_B50. No total-distance
value is mixed into this comparison.

The FIELD_B50 diagnostics do not expose the same final/minimum energy fields;
those entries are intentionally not reconstructed from another mechanism.

Outcome-group summaries for STATION_B50 were:

| Outcome | n | Onset energy mean (range) | Onset distance mean (range) | Duration mean (range) | Minimum energy mean (range) | Clamp count total | Attempts with clamp |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ACQUIRED | 281 | 0.488804 (0.480–0.498) | 0.518728 (0.153740–0.989504) | 15.979 (3–32) | 0.242669 (0.004–0.464) | 3 | 1 |
| TERMINATED_BEFORE_ACQUISITION | 9 | 0.488000 (0.480–0.498) | 0.905479 (0.796044–1.088751) | 30.778 (28–32) | 0.000000 (0–0) | 0 | 0 |
| HORIZON_CENSORED | 3 | 0.488667 (0.486–0.492) | 0.770075 (0.652071–0.842764) | 13.333 (12–15) | 0.264667 (0.228–0.288) | 0 | 0 |

Whole-batch evaluator classifications:

- Boundary-clamped MOVE_FORWARD: `2800 / 9562 = 0.292825769`.
- Clamping by controller mode: EXPLORE `2797`, SEEK `3`, CHARGE `0`.
- Outside-to-outside charger pass-through: `1` (zero harvest).
- EXPLORE-mode station entries: `10`.
- EXPLORE-mode harvested energy: `487.0` across `974` EXPLORE-mode
  transitions that harvested energy.

## Terminated-before-acquisition attempts

`available`, `threshold`, and `margin` are energy units. `actions` are ordered
as `MOVE_FORWARD / TURN_LEFT / TURN_RIGHT / WAIT`. `nominal costs` is ordered
as `basal / action-cost / combined`; it is a sum of configured transition
costs, not realised state-energy loss. Energy clipping at the failure boundary
can make nominal cost demand exceed the available reserve on the terminal
transition. Clamp and pass-through columns are evaluator-only.

| Seed | Onset step | Onset E | Onset dist | Boundary dist | Min fwd | Onset threshold | Available | Margin | Duration | Min E | Terminal dist | Actions | Nominal costs | Clamps / longest streak | Pass-through |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- | :--- | ---: | ---: |
| 18022 | 604 | 0.484 | 1.088751 | 0.988751 | 20 | 3.800 | 4.840 | 1.040 | 30 | 0.000 | 0.295150 | 17/8/5/0 | 3.000/1.960/4.960 | 0/0 | 0 |
| 18024 | 696 | 0.492 | 0.846571 | 0.746571 | 15 | 2.800 | 4.920 | 2.120 | 31 | 0.000 | 0.104004 | 16/9/6/0 | 3.100/1.900/5.000 | 0/0 | 0 |
| 18027 | 862 | 0.480 | 0.859724 | 0.759724 | 16 | 3.000 | 4.800 | 1.800 | 31 | 0.000 | 0.166572 | 15/10/6/0 | 3.100/1.820/4.920 | 0/0 | 0 |
| 18030 | 543 | 0.490 | 0.819981 | 0.719981 | 15 | 2.800 | 4.900 | 2.100 | 31 | 0.000 | 0.126857 | 15/10/6/0 | 3.100/1.820/4.920 | 0/0 | 0 |
| 18033 | 813 | 0.492 | 0.934473 | 0.834473 | 17 | 3.200 | 4.920 | 1.720 | 32 | 0.000 | 0.194436 | 16/6/10/0 | 3.200/1.920/5.120 | 0/0 | 0 |
| 18034 | 917 | 0.480 | 1.045154 | 0.945154 | 19 | 3.600 | 4.800 | 1.200 | 28 | 0.000 | 0.135463 | 19/3/6/0 | 2.800/2.080/4.880 | 0/0 | 0 |
| 18035 | 112 | 0.498 | 0.796044 | 0.696044 | 14 | 2.600 | 4.980 | 2.380 | 32 | 0.000 | 0.104160 | 15/10/7/0 | 3.200/1.840/5.040 | 0/0 | 0 |
| 18036 | 433 | 0.492 | 0.895871 | 0.795871 | 16 | 3.000 | 4.920 | 1.920 | 32 | 0.000 | 0.154647 | 16/6/10/0 | 3.200/1.920/5.120 | 0/0 | 0 |
| 18038 | 717 | 0.484 | 0.862742 | 0.762742 | 16 | 3.000 | 4.840 | 1.840 | 30 | 0.000 | 0.118819 | 16/9/5/0 | 3.000/1.880/4.880 | 0/0 | 0 |

Across lethal attempts:

- Negative optimistic reserve margins: `0`.
- Zero optimistic reserve margins: `0`.
- Positive optimistic reserve margins: `9`.
- Margin range and median: `1.040` to `2.380`, median `1.840`.
- Onset station-distance range: `0.796044` to `1.088751`.
- Terminal station-distance range: `0.104004` to `0.295150`.
- Action totals: MOVE_FORWARD `145`, TURN_LEFT `71`, TURN_RIGHT `61`, WAIT
  `0`.
- Nominal cost sums totals: basal `27.700`, action-cost `17.140`, combined
  `44.840`.
- Boundary clamps: `0` in all nine attempts; pass-through: `0` in all nine.

## Descriptive interpretation and limitations

Factually, after recomputing with the charge-aware definition, all nine lethal
attempts had positive optimistic reserve margins and were therefore
optimistically feasible at onset. All reached terminal energy after 28–32
SEEK transitions, and all had zero boundary clamps. They therefore are not
explained by the tested optimistic geometric threshold or by recorded
boundary-clamp events.

As an observational inference only, the lethal group has higher onset distance
and much longer SEEK duration than the acquired group while starting at nearly
the same normalized energy. The positive margins show that realised steering,
turning, and path efficiency remain candidate mechanisms; they do not establish
that steering inefficiency caused any individual death. The batch contains one
pass-through event overall and no lethal pass-through, so this characterization
does not support a pass-through or incidental-charging explanation for the
lethal attempts.

The next developmental question should be to characterize realised SEEK path
efficiency and geometric progress relative to this optimistic threshold, including
turning and distance-to-contact over time, before considering any controller or
parameter change. This is a proposed next question, not a formal protocol.
