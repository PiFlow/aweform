# EXP-003 one-step beacon-trend memory development characterization

> **DEVELOPMENT / DESCRIPTIVE ONLY**
>
> This is not formal EXP-003 calibration, confirmation, causal evidence, a
> frozen protocol, or EXP-004. No EXP-004 work was started.

## Base and implementation

- PR #37 was merged into `main` at
  `84712aab80e96ab1306d696e0c7800851d0a7a89`.
- The feature branch is `codex/exp-003-beacon-trend-memory`.
- Source/tests commit:
  `15fbfafd0758c2139b89a3783516181df2748496`.
- The final head is the commit containing this record; its exact SHA is
  reported in the handoff after commit creation.
- No historical experiment evidence was modified.
- The existing `STATION_B50_FULL` implementation and characterization record
  remain intact. It was not included in this quantitative comparison.

The additive controller is `StationB50TrendController`. It reuses the
historical `STATION_B50` mode structure, stochastic explorer, beacon steering,
charging-contact semantics, costs, movement, horizon, and policy RNG
convention. Its only persistent temporal policy state is:

```text
previous_explore_beacon_max: float | None
```

On reset and at the start of each fresh EXPLORE segment it is `None`. On an
ordinary EXPLORE decision, the controller computes
`current_beacon_max = max(left, forward, right)`, compares it with the one
previous EXPLORE maximum when one exists, then stores the current maximum for
the next EXPLORE decision. It clears the value when EXPLORE enters SEEK and
when CHARGE returns to EXPLORE. It stores no trajectory, coordinates,
positions, actions-as-map, distance, or long history.

The historical rule remains exactly:

```text
normalized energy < 0.50 -> SEEK
```

The additional development-only guard is exactly:

```text
0.50 <= normalized energy < 0.65
and current_beacon_max < 0.10
and previous_explore_beacon_max exists
and current_beacon_max < previous_explore_beacon_max
-> SEEK
```

The `0.65` anticipatory energy threshold and `0.10` weak-beacon threshold are
provisional development hypotheses, not calibrated scientific values. No
epsilon or smoothing was used. Equal beacon maxima do not trigger. CHARGE
recovery remains strictly `energy > 0.85`; this controller is not combined
with `STATION_B50_FULL`.

## Sensory and evaluator boundary

The controller receives only normalized energy, left/forward/right beacon
values, and charging contact. It never receives or stores station coordinates,
body coordinates, true station distance, evaluator coverage, evaluator SEEK
feasibility, or hidden resource truth.

The decision trace used for diagnostics records only values copied from the
controller-visible beacon observation and the controller's one previous
visible maximum. Evaluator-only station distance is calculated after/beside
the controller decision from evaluator telemetry. The ordinary environment
reset and step `info` objects remain empty, and evaluator diagnostics have no
feedback path into policy action selection.

## Seeds and execution boundary

The quantitative comparison used exactly 40 matched ordinary development
seeds, `18141–18180` inclusive. The development validator accepted all 40;
the range was contiguous and had no overlap with EXP-001, EXP-002, or EXP-003
formal/reserved ranges.

Only these conditions were executed in the quantitative batch:

1. `STATION_B50`
2. `STATION_B50_TREND`

Both conditions used the same environment seed, environment configuration,
initial body draw, station, policy RNG ownership/convention, explorer, beacon,
charger, movement, costs, and horizon. No calibration, confirmatory, or
reserved seeds were executed. No `STATION_B50_FULL` batch was run here.

For transparency, seeds `18141` and `18142` were also used earlier in focused
non-quantitative diagnostic tests before the source/tests commit; the matched
40-seed quantitative batch itself was run only after commit
`15fbfafd0758c2139b89a3783516181df2748496`.

## Matched descriptive results

Values are means across the 40 episodes unless stated otherwise. Energy is
normalized to the configured failure-to-maximum interval. These are measured
batch differences, not causal estimates.

| Metric | `STATION_B50` | `STATION_B50_TREND` |
| --- | ---: | ---: |
| Horizon survivors | 19/40 | 38/40 |
| Mean capped lifespan | 710.950 | 951.600 |
| Mean final normalized energy | 0.278400 | 0.577200 |
| Mean minimum normalized energy | 0.020050 | 0.094750 |
| Mean coverage | 0.373364 | 0.431006 |
| Mean total distance | 16.937067 | 22.588742 |
| Mean EXPLORE distance | 10.959570 | 14.637499 |
| SEEK attempts | 495 | 680 |
| Historical-energy SEEK entries | 495 | 535 |
| Anticipatory SEEK entries | 0 | 145 |
| Anticipatory fraction of all SEEK entries | 0.000000 | 0.213235 |
| Mean anticipatory entries per episode | 0.000 | 3.625 |
| Episodes with at least one anticipatory return | 0/40 | 38/40 |
| Lethal SEEK terminations | 21 | 2 |
| Resolved acquisition fraction | 0.957143 | 0.997015 |
| Mean evaluator-only station distance at SEEK onset | 0.545228 | 0.526553 |
| Maximum lethal SEEK-onset distance | 1.095224 | 1.073830 |
| Mean SEEK turn fraction | 0.404726 | 0.405715 |
| Mean SEEK forward/ideal-transition ratio | 1.031041 | 1.034846 |
| Mean SEEK nominal cost-demand overhead | 0.867313 | 0.846412 |

For `STATION_B50_TREND`, anticipatory entries had:

- mean evaluator-side normalized energy at entry: `0.600690`;
- mean controller-visible current maximum beacon: `0.090817`;
- mean controller-visible previous maximum beacon: `0.098985`;
- mean beacon delta (`current - previous`): `-0.008168`;
- mean evaluator-only station distance at entry: `0.746578`;
- outcomes: `145 ACQUIRED`, `0 TERMINATED_BEFORE_ACQUISITION`, and
  `0 HORIZON_CENSORED`;
- anticipatory returns with evaluator-only onset distance below `0.20`:
  `0`.

The trend policy's remaining two lethal SEEK attempts both began with onset
maximum beacon below `0.10`. The historical policy's 21 lethal attempts also
had onset maximum beacon below `0.10` in this batch. This is an evaluator
diagnostic association, not a causal explanation.

## Descriptive answers to the development questions

1. The temporal policy did trigger: 145 anticipatory returns across 38 of 40
   episodes.
2. At trigger time, the typical measured values were approximately energy
   `0.600690`, current maximum beacon `0.090817`, weakening magnitude
   `-0.008168`, and evaluator-only station distance `0.746578`.
3. Mean evaluator-only station distance at all SEEK onsets was lower for the
   trend policy (`0.526553` versus `0.545228`) in this batch.
4. Lethal SEEK terminations were lower descriptively (`2` versus `21`).
5. Resolved acquisition fraction was higher descriptively (`0.997015` versus
   `0.957143`).
6. Horizon survival and mean capped lifespan were higher descriptively for the
   trend policy (`38/40`, `951.600` versus `19/40`, `710.950`).
7. Coverage, total distance, and EXPLORE distance were all higher
   descriptively for the trend policy.
8. The policy does not appear excessively conservative in this batch based on
   the absence of anticipatory entries below evaluator-only distance `0.20`
   and the higher survival/descriptive lifespan. The higher total SEEK count
   is a real behavioural difference and should be tracked in later work.
9. No anticipatory return occurred very near the charger under the recorded
   `<0.20` evaluator-only check. This does not establish that the signal is
   noise-free.
10. Lethal SEEK attempts remained associated with weak onset beacon
    information: both remaining trend-policy lethal attempts had onset maximum
    beacon below `0.10`.
11. This batch supports further descriptive study of one-step
    temporal/context-sensitive regulation. It does not justify formalizing
    EXP-003, claiming causality, or adding a larger memory mechanism.

## Limitations

The historical controller regulates from current internal energy only. The new
controller regulates from current internal energy, current external beacon
signal, and one previous controller-visible external beacon signal. A narrow
description is “one-step controller-visible beacon history used for
context-sensitive return regulation.” It is not learning, mapping, route
memory, planning, a world model, cognition, or proven anticipation.

`max(left, forward, right)` is not a direct measurement of true station
distance. It depends partly on body orientation and directional probe geometry.
Therefore, a decrease in the maximum signal can reflect a heading/orientation
change rather than genuine movement farther from the charger. The one-step
mechanism is intentionally primitive. This record does not add moving
averages, longer windows, learned estimators, odometry, coordinates, Kalman
filters, neural networks, maps, or other compensating mechanisms.

The quantitative result is one ordinary development batch. It does not
separate the effects of anticipatory return timing from all downstream
trajectory differences and does not establish that beacon weakening measured
true distance. The observed batch improvement is descriptive only.

## Validation

- `uv sync --locked`: passed.
- Focused EXP-003 tests: `67 passed`.
- Full pytest suite: `411 passed`.
- `uv run ruff check .`: passed.
- `uv run mypy src --strict`: passed.
- `git diff --check`: passed.
- `uv run ruff format --check .`: failed on pre-existing formatting in 19
  files/sections outside the scope of this change; no unrelated historical
  files were reformatted. Task-file Ruff lint and focused tests passed.

The original `FIELD_B50` vs `STATION_B50` visualizer behavior remains unchanged. A
later post-characterization instrumentation commit adds a separate matched
`STATION_B50` vs `STATION_B50_TREND` development view that consumes only the
recorded trajectories and controller-decision traces. It does not modify
controllers, the environment, runner trajectory generation, thresholds, seed
policy, or any recorded characterization number. The 40-seed quantitative
characterization was not recomputed.

No EXP-004 work was started. No formal, confirmatory, or reserved seeds were
executed.
