# EXP-003 full-recharge development characterization

> **DEVELOPMENT / DESCRIPTIVE ONLY**
>
> This remains EXP-003 development. It is not formal calibration, not a
> confirmatory experiment, not a frozen EXP-003 protocol, and not causal
> evidence. No EXP-004 work was started.

## Purpose

This slice tests an additive `STATION_B50_FULL` controller suggested by direct
visualization. Historical `STATION_B50` leaves `CHARGE` when normalized energy
is strictly above `0.85`. In the localized charging ecology, that can remove
physical energy access immediately after recovery.

`STATION_B50_FULL` preserves the historical controller and all environment,
observation, action, parameter, and RNG semantics except for CHARGE recovery:

- while contact is true and normalized energy is below `1.0`, it remains in
  `CHARGE` and returns `WAIT`;
- at controller-visible normalized energy `1.0`, it leaves `CHARGE` and begins
  a fresh EXPLORE segment using the existing convention;
- contact loss before full recovery returns immediately to `SEEK`.

Historical `STATION_B50` was not modified and remains the comparison policy.
The charger remains the same forgiving physical contact abstraction with
`charging_radius = 0.10`; precision docking is a separate future development
question and was not introduced here.

## Reproducibility and scope

- Source/tests SHA used for this characterization:
  `966fe8fc7bf715641232b9aab633b908f579fb63`
- Fresh ordinary development seeds: `18101–18140` inclusive, exactly 40
  matched seeds.
- The seed guard accepted the entire block; it does not overlap existing
  formal or reserved ranges.
- Both policies used the same environment seed and matched policy-seed
  convention. Environment placement, station centre, body start, heading,
  charger, beacon, costs, movement, world bounds, and horizon were unchanged.
- No `18021–18040` seed was used for the quantitative batch. No
  `50001–51000`, `60001–60200`, or `70001–71000` seed was executed.
- No formal EXP-003 calibration or confirmation was executed or frozen.

The permanent visualizer change in the source commit only retains the
`FuncAnimation` object strongly during `plt.show()`. It does not alter frame
generation, trajectories, controller visibility, or evaluator labels.

## Matched descriptive results

Values are means across the 40 episodes unless stated otherwise. Energy is
normalized to the configured failure-to-maximum interval where noted. Total
harvested energy is configured charger input recorded by evaluator telemetry,
not realized state-energy loss.

### Viability and exploration

| Metric | STATION_B50 | STATION_B50_FULL |
| --- | ---: | ---: |
| Horizon survivors | 22/40 | 16/40 |
| Deaths before horizon | 18/40 | 24/40 |
| Mean capped lifespan | 782.325 | 685.375 |
| Mean final normalized energy | 0.320150 | 0.272400 |
| Minimum final normalized energy | 0.000000 | 0.000000 |
| Mean minimum normalized energy | 0.023300 | 0.018700 |
| Mean coverage | 0.388086 | 0.349976 |
| Mean total distance | 18.475910 | 15.398752 |
| Mean EXPLORE distance | 11.997408 | 10.041297 |
| Mean EXPLORE actions | 367.700 | 312.050 |
| EXPLORE transition fraction | 0.470009 | 0.455298 |

### Energy and charging

| Metric | STATION_B50 | STATION_B50_FULL |
| --- | ---: | ---: |
| Mean total harvested energy | 124.5375 | 118.7000 |
| Mean station entries | 13.525 | 10.700 |
| Mean completed recharge cycles | 12.800 | 10.125 |
| Mean transitions on charger | 249.075 | 237.400 |
| Mean CHARGE WAIT transitions | 192.500 | 191.225 |
| Mean normalized energy at charger acquisition | 0.241950 | 0.242442 |
| Mean normalized departure energy | 0.869789 | 1.000000 |
| Departure-energy range | 0.850000–0.888000 | 1.000000–1.000000 |
| Completed departures at normalized energy 1.0 | 0/512 | 405/405 |
| Mean charger transitions per completed cycle | 16.959 | 20.677 |
| Mean transitions from departure to next SEEK | 28.912 | 30.972 |

Full recovery did what it was designed to do: every completed departure in
the batch occurred at normalized energy `1.0`. It increased charger dwell per
completed cycle by about `3.7` transitions. Because the full-recharge policy
also completed fewer cycles and had fewer total entries, its mean total
charger transitions per episode were not higher; the relevant distinction is
longer dwell per completed cycle and later departure.

### SEEK outcomes and overhead

| Metric | STATION_B50 | STATION_B50_FULL |
| --- | ---: | ---: |
| SEEK attempts | 542 | 437 |
| ACQUIRED | 518 | 412 |
| TERMINATED_BEFORE_ACQUISITION | 18 | 24 |
| HORIZON_CENSORED SEEK attempts | 6 | 1 |
| Resolved acquisition fraction | 0.966418 | 0.944954 |
| Mean SEEK onset normalized energy | 0.488546 | 0.488050 |
| Mean true station distance at SEEK onset | 0.536382 | 0.548125 |
| Mean onset max beacon signal | 0.245584 | 0.241326 |
| Mean SEEK duration | 16.393 | 16.668 |
| Mean nominal SEEK cost-demand overhead | 0.884207 | 0.895103 |
| Mean ideal forward-transition requirement | 9.240 | 9.449 |
| Maximum lethal SEEK-onset distance | 1.028446 | 1.079481 |

The full-recharge policy did not eliminate difficult returns. It had 24 lethal
SEEK attempts in this development batch, including a lethal attempt beginning
at true station distance `1.079481`. The historical policy had 18 lethal SEEK
attempts and a maximum lethal onset distance of `1.028446`.

## Descriptive answers to the development questions

1. **Does full recharge materially improve survival?** No, not in this batch.
   Horizon survival was lower for `STATION_B50_FULL` (`16/40` versus `22/40`)
   and mean capped lifespan was lower (`685.375` versus `782.325`).

2. **Does it reduce lethal late SEEK attempts?** No. Episode deaths increased
   from `18` to `24`, and lethal SEEK terminations increased from `18` to
   `24`. The resolved acquisition fraction also decreased descriptively from
   `0.966418` to `0.944954`.

3. **How much additional time is spent charging?** Per completed recharge
   cycle, charger occupancy increased from `16.959` to `20.677` transitions,
   while mean departure-to-next-SEEK time increased from `28.912` to `30.972`
   transitions. Mean total charger transitions per episode decreased because
   the full policy completed fewer cycles.

4. **Does charging time reduce exploration?** Descriptively, yes in this
   batch: mean coverage fell from `0.388086` to `0.349976`, total distance from
   `18.475910` to `15.398752`, and EXPLORE distance from `11.997408` to
   `10.041297`. This is a measured group difference, not a causal attribution.

5. **Is the repeated cycle more stable?** The recovery segment became more
   uniform with respect to departure energy: all completed full-policy cycles
   departed at `1.0`. However, the episode-level cycle was not more viable or
   more repeatable in this batch: there were fewer completed cycles, fewer
   horizon survivors, and more lethal SEEK terminations.

6. **Is full recharge enough for the localized ecology?** No, not on these
   descriptive development results. Long-distance SEEK failures remain a
   meaningful problem, and the batch does not support treating full recharge
   as a sufficient ecological correction.

These statements describe this matched ordinary development batch only. They
do not establish optimality, causality, predictive validity, or a formal
EXP-003 conclusion. In particular, no claim is made that additional charging
time caused the observed survival difference.

## Limitations and next boundary

The comparison isolates full-recovery CHARGE semantics while retaining the
current `0.10` contact radius. It does not test precision docking, smaller
chargers, beacon retuning, movement retuning, cost changes, steering changes,
memory, learning, or context-sensitive regulation. Those would be separate
development questions. EXP-004 has not started, and the formal EXP-003
protocol remains unfrozen.
