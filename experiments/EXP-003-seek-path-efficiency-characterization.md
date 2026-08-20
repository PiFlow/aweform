# EXP-003 realized SEEK path-efficiency characterization

> **DEVELOPMENT / DESCRIPTIVE CHARACTERIZATION ONLY**
>
> This is not a formal EXP-003 protocol, not formal calibration, not
> confirmatory evidence, and contains no causal attribution or preregistered
> statistical claim.

## Purpose

This development slice characterizes the realized sensorimotor paths of
STATION_B50 SEEK attempts. It asks what distinguishes successful acquisition
from lethal termination, and whether the controller-visible beacon contains a
descriptive warning signal for difficult returns before death.

The controller, environment dynamics, B50 thresholds, beacon, charger,
movement/action costs, world geometry, observations, RNG ownership, and
historical EXP-001/EXP-002 material were unchanged. Diagnostics are derived
after execution from recorded trajectories and observations; they do not feed
back into the controller.

## Reproducibility and scope

- Ordinary development seeds used: `18021–18040` inclusive, and no others.
- Source SHA used for the characterization execution:
  `5a9de229ad247d770075a30ed1e127ed1052faac`.
- No EXP-002 confirmatory seed `50001–51000` was executed.
- No EXP-003 reserved seed `60001–60200` or `70001–71000` was executed.
- No formal result artifact, formal EXP-003 protocol/calibration,
  confirmation, or EXP-004 work was started.

## Evaluator-only metric definitions

A SEEK attempt begins at the recorded EXPLORE-to-SEEK transition and ends at
charging acquisition, termination before acquisition, or horizon censoring.
The `station_distance_trajectory` contains the true station distance at SEEK
onset followed by the post-transition distance for every transition in the
attempt.

For each transition, radial progress is
`station_distance_before - station_distance_after`. Positive values are
inward progress; negative values are outward movement. Cumulative inward and
outward quantities sum the positive and negative parts separately. A
MOVE_FORWARD action is classified as reducing or increasing station distance
using the same strict comparison. A transition with zero or outward radial
progress contributes to the maximum consecutive no-progress streak.

`turn_fraction` is turn count divided by total SEEK transitions. The
forward/ideal ratio is actual MOVE_FORWARD count divided by the optimistic
minimum forward-transition count. The realized path/boundary ratio is
realized forward movement distance divided by onset distance to the charging
boundary. Ratios with a zero denominator are recorded as `None`, not as zero.

The idealized nominal straight-line cost demand is
`optimistic_minimum_forward_transitions * (basal_cost + movement_cost)`. It is
a nominal scheduled-cost comparison, not the charge-aware onset-reserve
threshold and not realized state-energy loss. Nominal cost-demand overhead is
realized nominal total cost sum minus that idealized demand. Transition-demand
overhead is realized SEEK transitions minus the ideal forward-transition count.
These terms are descriptive; they are not called waste and do not imply a
causal mechanism.

Controller-visible beacon diagnostics use only the exact recorded
`StationObservation` values. At SEEK onset they include left, forward, right,
maximum, mean, and directional contrast (`max - min`). The pre-SEEK window is
the previous five decision observations when available, excluding the onset
observation. Recent mean strength is the mean of per-observation directional
means; recent maximum strength is the maximum directional value in the
window; trend is the change in per-observation mean strength from the first to
last available observation divided by the number of intervals. No true
station distance is used to construct these controller-visible features.

## Batch outcomes

| Outcome | Count |
| --- | ---: |
| ACQUIRED | 281 |
| TERMINATED_BEFORE_ACQUISITION | 9 |
| HORIZON_CENSORED | 3 |
| Resolved-only acquisition | `281 / 290 = 0.968965517` |

The diagnostics preserved the recorded actions and trajectories. All 9 lethal
attempts had zero boundary clamps and zero SEEK pass-through events. The
whole-batch pass-through count remained `1`, outside these SEEK attempts.

## Group comparisons

Values below are mean (minimum–maximum) unless stated otherwise. Distances
and radial quantities are world units; signal quantities are unitless.

### Path and transition efficiency

| Outcome | n | Ideal fwd | Actual fwd | SEEK transitions | Turns | Turn fraction | Fwd / ideal | Path / boundary | Net inward | Inward | Outward | Max no-progress |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ACQUIRED | 281 | 8.897 (2–18) | 9.299 (2–18) | 15.979 (3–32) | 6.680 (0–17) | 0.405 (0–0.667) | 1.044 (1–1.500) | 1.135 (1.010–1.861) | 0.442 (0.092–0.899) | 0.442 | 0.000 | 2.900 (0–4) |
| TERMINATED_BEFORE_ACQUISITION | 9 | 16.444 (14–20) | 16.111 (15–19) | 30.778 (28–32) | 14.667 (9–17) | 0.474 (0.321–0.531) | 0.985 (0.850–1.071) | 1.006 (0.860–1.078) | 0.750 (0.692–0.910) | 0.750 | 0.000 | 3.444 (3–4) |
| HORIZON_CENSORED | 3 | 14.000 (12–15) | 8.000 (6–10) | 13.333 (12–15) | 5.333 (4–7) | 0.402 (0.333–0.538) | 0.589 (0.400–0.833) | 0.621 (0.419–0.906) | 0.377 (0.278–0.472) | 0.377 | 0.000 | 3.000 (2–4) |

All three outcome groups had zero cumulative outward radial movement and all
MOVE_FORWARD actions reduced true station distance. The lethal attempts
therefore do not show a moving-away-from-station pattern in this batch.

### Nominal cost overhead

| Outcome | n | Ideal nominal demand | Realized nominal SEEK demand | Nominal cost overhead | Transition overhead |
| --- | ---: | ---: | ---: | ---: | ---: |
| ACQUIRED | 281 | 1.779 (0.400–3.600) | 2.661 (0.520–5.040) | 0.882 (0.000–2.240) | 7.082 (0–18) |
| TERMINATED_BEFORE_ACQUISITION | 9 | 3.289 (2.800–4.000) | 4.982 (4.880–5.120) | 1.693 (0.960–2.240) | 14.333 (9–18) |
| HORIZON_CENSORED | 3 | 2.800 (2.400–3.000) | 2.240 (2.040–2.600) | -0.560 (-0.960–0.200) | -0.667 (-3–3) |

The lethal group had higher descriptive turning and nominal transition/cost
overhead than the acquired group. This does not establish that turning caused
death; it identifies realized path inefficiency as a candidate mechanism for
further development work.

### Controller-visible onset and pre-SEEK beacon features

The pre-SEEK trend is available for 261/281 acquired attempts, 9/9 lethal
attempts, and 3/3 censored attempts; recent mean and maximum are available
whenever at least one prior observation exists.

| Outcome | n | Onset max | Onset mean | Onset contrast | Recent mean | Recent max | Recent trend |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ACQUIRED | 281 | 0.245 (0.053–0.952) | 0.211 (0.052–0.834) | 0.062 (0.003–0.335) | 0.214 (0.062–0.725) | 0.283 (0.071–0.969) | -0.00037 (-0.07584–0.08290) |
| TERMINATED_BEFORE_ACQUISITION | 9 | 0.066 (0.046–0.082) | 0.062 (0.044–0.076) | 0.006 (0.003–0.009) | 0.069 (0.053–0.084) | 0.082 (0.065–0.110) | -0.00303 (-0.00713–0.00000) |
| HORIZON_CENSORED | 3 | 0.100 (0.076–0.146) | 0.088 (0.070–0.123) | 0.020 (0.007–0.043) | 0.089 (0.079–0.107) | 0.103 (0.091–0.119) | -0.00256 (-0.00435–0.00000) |

The lethal group had weaker and less directionally contrasted beacon readings
both at SEEK onset and in the preceding recorded window. This is a plausible
controller-visible signal of high-return difficulty before death, but it is a
descriptive group difference, not a validated predictor or causal result.

## Individual lethal attempts

### Path and nominal overhead

| Seed | Ideal fwd | Actual fwd | SEEK transitions | Turns / fraction | Fwd / ideal | Path / boundary | Net inward | Max no-progress | Ideal cost | Realized cost | Cost overhead | Transition overhead |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 18022 | 20 | 17 | 30 | 13 / 0.433 | 0.850 | 0.860 | 0.794 | 4 | 4.000 | 4.960 | 0.960 | 10 |
| 18024 | 15 | 16 | 31 | 15 / 0.484 | 1.067 | 1.072 | 0.743 | 3 | 3.000 | 5.000 | 2.000 | 16 |
| 18027 | 16 | 15 | 31 | 16 / 0.516 | 0.938 | 0.987 | 0.693 | 3 | 3.200 | 4.920 | 1.720 | 15 |
| 18030 | 15 | 15 | 31 | 16 / 0.516 | 1.000 | 1.042 | 0.693 | 3 | 3.000 | 4.920 | 1.920 | 16 |
| 18033 | 17 | 16 | 32 | 16 / 0.500 | 0.941 | 0.959 | 0.740 | 3 | 3.400 | 5.120 | 1.720 | 15 |
| 18034 | 19 | 19 | 28 | 9 / 0.321 | 1.000 | 1.005 | 0.910 | 4 | 3.800 | 4.880 | 1.080 | 9 |
| 18035 | 14 | 15 | 32 | 17 / 0.531 | 1.071 | 1.078 | 0.692 | 3 | 2.800 | 5.040 | 2.240 | 18 |
| 18036 | 16 | 16 | 32 | 16 / 0.500 | 1.000 | 1.005 | 0.741 | 4 | 3.200 | 5.120 | 1.920 | 16 |
| 18038 | 16 | 16 | 30 | 14 / 0.467 | 1.000 | 1.049 | 0.744 | 4 | 3.200 | 4.880 | 1.680 | 14 |

All nine had inward forward fraction `1.000`, outward forward fraction `0.000`,
and cumulative outward radial movement `0.000`.

### Controller-visible beacon features

`L/F/R` are the recorded onset beacon values; the remaining columns are
derived from controller-visible observations only.

| Seed | Onset L/F/R | Onset max | Onset mean | Contrast | Recent mean | Recent max | Recent trend |
| ---: | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| 18022 | 0.045775 / 0.042581 / 0.043185 | 0.046 | 0.044 | 0.003 | 0.053 | 0.067 | -0.00419 |
| 18024 | 0.074442 / 0.066552 / 0.065732 | 0.074 | 0.069 | 0.009 | 0.081 | 0.097 | -0.00437 |
| 18027 | 0.071545 / 0.064510 / 0.064299 | 0.072 | 0.067 | 0.007 | 0.074 | 0.087 | -0.00317 |
| 18030 | 0.077863 / 0.069889 / 0.069573 | 0.078 | 0.072 | 0.008 | 0.084 | 0.110 | -0.00713 |
| 18033 | 0.055728 / 0.056057 / 0.061928 | 0.062 | 0.058 | 0.006 | 0.059 | 0.065 | -0.00076 |
| 18034 | 0.046913 / 0.045563 / 0.048449 | 0.048 | 0.047 | 0.003 | 0.056 | 0.070 | -0.00377 |
| 18035 | 0.081562 / 0.073277 / 0.073218 | 0.082 | 0.076 | 0.008 | 0.077 | 0.085 | -0.00000 |
| 18036 | 0.060381 / 0.059795 / 0.065396 | 0.065 | 0.062 | 0.006 | 0.066 | 0.075 | -0.00195 |
| 18038 | 0.069380 / 0.063594 / 0.064597 | 0.069 | 0.066 | 0.006 | 0.068 | 0.078 | -0.00193 |

## Descriptive conclusion and limitations

Within these 20 ordinary development seeds:

- Lethal attempts were not characterized by moving away from the station;
  every recorded forward action reduced true station distance.
- Lethal attempts had more turns, longer SEEK durations, and higher nominal
  transition/cost overhead than acquired attempts. This is a candidate
  mechanism, not a causal attribution.
- The lethal group had nearly ideal forward/path ratios once its turns were
  excluded, so the result does not support a simple insufficient-forward-step
  explanation.
- Onset and pre-SEEK beacon strength and directional contrast were much weaker
  for lethal attempts. The existing controller-visible beacon therefore
  appears to contain a plausible descriptive signal of high-return difficulty
  before death, but this slice does not establish predictive validity,
  controller awareness, or causality.

The next development step, if authorized, should test whether such
controller-visible signal summaries can be used by a context-sensitive
regulator without changing the current controller in this characterization.
This is a proposed question only. EXP-004 has not started.
