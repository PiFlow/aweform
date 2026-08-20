# EXP-003 lethal-SEEK characterization

> **DEVELOPMENT / DESCRIPTIVE CHARACTERIZATION ONLY**
>
> This is not a formal EXP-003 protocol, not formal calibration, not
> confirmatory evidence, and contains no preregistered statistical claim.

## Purpose

This development slice asks whether the lethal STATION_B50 SEEK attempts in
the existing localized-charging environment are already energetically
infeasible at SEEK onset under an optimistic straight-line lower bound, or
whether they remain unexplained by the available reserve and geometric
distance.

The existing controller, environment, contact and charging dynamics, beacon,
parameters, observations, and RNG ownership were unchanged. No parameter was
tuned in response to these observations.

## Reproducibility and scope

- Ordinary development seeds used: `18021–18040` inclusive.
- Source SHA used for the characterization execution:
  `19e89372d423fb50226f244e767732b16dbb1c7f`.
- No EXP-002 confirmatory seed `50001–51000` was executed.
- No EXP-003 reserved seed `60001–60200` or `70001–71000` was executed.
- No formal result artifact, formal calibration, confirmatory execution, or
  EXP-004 work was started.

## Evaluator-only definitions

For each SEEK attempt, all values in this section are derived from privileged
telemetry and are not present in the controller observation.

Let `r` be the unchanged development charging radius, `d_onset` the true
station distance at SEEK onset, `m` the unchanged movement distance, `b` the
basal cost, and `c` the movement cost.

```text
distance_to_charging_boundary = max(0, d_onset - r)
minimum_forward_transitions = ceil(distance_to_charging_boundary / m)
optimistic_forward_only_energy_lower_bound
    = minimum_forward_transitions * (b + c)
available_onset_energy_above_failure
    = actual_energy_at_onset - failure_boundary
optimistic_reserve_margin
    = available_onset_energy_above_failure
      - optimistic_forward_only_energy_lower_bound
```

The bound assumes every forward transition makes full progress toward the
charging boundary. It ignores turning, beacon-steering inefficiency,
unnecessary travel, boundary interactions, and all other realised path
costs. It is therefore an optimistic lower bound, not a realistic required-
energy estimate. A negative margin means the attempt could not reach contact
under this favourable approximation. A non-negative margin does not prove
that the realised controller can reach contact.

Per-attempt action counts and actual expenditure are also evaluator-only:
MOVE_FORWARD, TURN_LEFT, TURN_RIGHT, and WAIT counts; basal expenditure;
action-cost expenditure; their sum; terminal distance; boundary-clamp
diagnostics; and outside-to-outside charger pass-through count.

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

| Condition | Horizon survivors | Capped lifespan | Final normalized energy | Minimum normalized energy | Coverage | Distance | EXPLORE actions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| FIELD_B50 | 19/20 | 990.400 | — | — | 0.466406 | 18.223644 | 659.500 |
| STATION_B50 | 11/20 | 848.250 | 0.335700 | 0.033000 | 0.426709 | 19.940223 | 399.600 |

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

`available` and `lower_bound` are actual energy units. `actions` are ordered
as `MOVE_FORWARD / TURN_LEFT / TURN_RIGHT / WAIT`. `expenditure` is ordered
as `basal / action-cost / combined`, also in actual energy units. Clamp and
pass-through columns are evaluator-only.

| Seed | Onset step | Onset E | Onset dist | Boundary dist | Min fwd | Lower bound | Available | Margin | Duration | Min E | Terminal dist | Actions | Expenditure | Clamps / longest streak | Pass-through |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- | :--- | ---: | ---: |
| 18022 | 604 | 0.484 | 1.088751 | 0.988751 | 20 | 4.000 | 4.840 | 0.840 | 30 | 0.000 | 0.295150 | 17/8/5/0 | 3.000/1.960/4.960 | 0/0 | 0 |
| 18024 | 696 | 0.492 | 0.846571 | 0.746571 | 15 | 3.000 | 4.920 | 1.920 | 31 | 0.000 | 0.104004 | 16/9/6/0 | 3.100/1.900/5.000 | 0/0 | 0 |
| 18027 | 862 | 0.480 | 0.859724 | 0.759724 | 16 | 3.200 | 4.800 | 1.600 | 31 | 0.000 | 0.166572 | 15/10/6/0 | 3.100/1.820/4.920 | 0/0 | 0 |
| 18030 | 543 | 0.490 | 0.819981 | 0.719981 | 15 | 3.000 | 4.900 | 1.900 | 31 | 0.000 | 0.126857 | 15/10/6/0 | 3.100/1.820/4.920 | 0/0 | 0 |
| 18033 | 813 | 0.492 | 0.934473 | 0.834473 | 17 | 3.400 | 4.920 | 1.520 | 32 | 0.000 | 0.194436 | 16/6/10/0 | 3.200/1.920/5.120 | 0/0 | 0 |
| 18034 | 917 | 0.480 | 1.045154 | 0.945154 | 19 | 3.800 | 4.800 | 1.000 | 28 | 0.000 | 0.135463 | 19/3/6/0 | 2.800/2.080/4.880 | 0/0 | 0 |
| 18035 | 112 | 0.498 | 0.796044 | 0.696044 | 14 | 2.800 | 4.980 | 2.180 | 32 | 0.000 | 0.104160 | 15/10/7/0 | 3.200/1.840/5.040 | 0/0 | 0 |
| 18036 | 433 | 0.492 | 0.895871 | 0.795871 | 16 | 3.200 | 4.920 | 1.720 | 32 | 0.000 | 0.154647 | 16/6/10/0 | 3.200/1.920/5.120 | 0/0 | 0 |
| 18038 | 717 | 0.484 | 0.862742 | 0.762742 | 16 | 3.200 | 4.840 | 1.640 | 30 | 0.000 | 0.118819 | 16/9/5/0 | 3.000/1.880/4.880 | 0/0 | 0 |

Across lethal attempts:

- Negative optimistic reserve margins: `0`.
- Non-negative optimistic reserve margins: `9`.
- Margin range and median: `0.840` to `2.180`, median `1.640`.
- Onset station-distance range: `0.796044` to `1.088751`.
- Terminal station-distance range: `0.104004` to `0.295150`.
- Action totals: MOVE_FORWARD `145`, TURN_LEFT `71`, TURN_RIGHT `61`, WAIT
  `0`.
- Actual expenditure totals: basal `27.700`, action-cost `17.140`, combined
  `44.840`.
- Boundary clamps: `0` in all nine attempts; pass-through: `0` in all nine.

## Descriptive interpretation and limitations

Factually, the lethal attempts did not have negative margins under this bound;
all reached terminal energy after 28–32 SEEK transitions, and all had zero
boundary clamps. They therefore are not explained by the tested optimistic
forward-only energy lower bound or by recorded boundary-clamp events.

As an observational inference only, the lethal group has higher onset distance
and much longer SEEK duration than the acquired group while starting at nearly
the same normalized energy. The positive margins show that realised steering,
turning, and path efficiency remain relevant candidates; they do not establish
which mechanism caused any individual death. The batch contains one
pass-through event overall and no lethal pass-through, so this characterization
does not support a pass-through or incidental-charging explanation for the
lethal attempts.

The next developmental question should be to characterize realised SEEK path
efficiency and geometric progress relative to this optimistic bound, including
turning and distance-to-contact over time, before considering any controller or
parameter change. This is a proposed next question, not a formal protocol.
