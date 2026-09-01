# D-021 — Minimal autonomous V0.4 energy-regulation baseline

- **id:** D-021
- **lane:** Development
- **date:** 2026-09-02
- **authoritative_base_sha:** `eb632767bc2fedf2465e8b24b6b3395841b9b54a`
- **implementation_probe_sha:** `0dd310cf1324319bb64a603f3a293b70db4ecbd2`
- **development_seeds:** `18365, 18366, 18367`
- **horizon:** `70,000` transitions per lifetime (`7,000.0 s`, approximately `116.67` simulated minutes)
- **disposition:** `CONTINUING`
- **learned mechanism:** none

## Question and scope

D-021 asks what happens when the smallest historical-style fixed energy-
regulation scaffold is coupled directly to the accepted D-020 V0.4 physical
body:

```text
full battery → depart → explore → low battery → SEEK
→ physical contact reacquisition → recharge → depart again
```

This is ordinary Development-lane descriptive work. It makes no confirmatory
claim and does not establish learning, predictive control, optimality, final
robot autonomy, hardware truth, metabolism, emotion, consciousness, sentience,
subjective experience, genuine life, or general intelligence.

D-020 was reused unchanged. Only its `episode_horizon` was set to the frozen
D-021 horizon. No visualizer, learner, reward, new sensor, physical parameter,
thermal parameter, charging rule, beacon rule, or D-022 work was added.

## Programmed / organism-visible / evaluator-only / learned

**PROGRAMMED**

- `D021Controller` with modes `CHARGE`, `DEPART`, `AWAY`, and `SEEK`.
- Full departure at normalized own energy `>= 1.0`, classified as the physical
  full-capacity fraction.
- Low-energy SEEK entry at inherited `EXP003_B50_ENTER_SEEK_THRESHOLD == 0.50`.
  This is a programmed historical baseline threshold, not learned or optimized
  for V0.4; D-021 tests whether it still functions under physical battery
  dynamics.
- Existing `StochasticPersistentExplorer` with its fixed `1/8` hazard and
  existing persistent state semantics.
- Existing `seek_beacon_action` steering.
- Seed-derived initial heading from the environment RNG stream.

**ORGANISM-VISIBLE**

Exactly D-020's six channels, projected into the existing `D011Observation`:

- normalized own battery energy;
- beacon left, forward, and right;
- binary physical `charging_contact`;
- normalized own current body temperature.

Temperature is organism-visible but has **zero programmed behavioural
influence** in D-021. No controller branch reads thermal state.

**EVALUATOR-ONLY**

- position and heading after initial setup;
- station location and true distance;
- battery joules and absolute Celsius;
- charger phase and termination latch;
- transition telemetry, event summaries, cycle metrics, and shutdown reason.

Evaluator telemetry is read only after action selection and the physical step;
it is never passed to the next controller decision. `reward == 0.0` and
`info == {}` on every transition.

**LEARNED**

None. There is no learner, predictor, model-guided action selection, planning,
RL, reward shaping, utility, valence, or plastic state.

## Exact controller state machine

The controller uses only the current ordinary observation and its finite mode
state. In `CHARGE`, loss of contact enters `SEEK`; contact with normalized
energy `>= 1.0` enters `DEPART` and returns `MOVE_FORWARD`; otherwise it
returns `WAIT`. `DEPART` continues `MOVE_FORWARD` while contact remains, or
enters `AWAY` and executes the AWAY rule in the same decision after exit.
`AWAY` enters `SEEK` only when energy is strictly below `0.50`; otherwise it
calls the historical persistent explorer. `SEEK` enters `CHARGE` and returns
`WAIT` on visible contact, otherwise it calls `seek_beacon_action`.

The SEEK/contact `WAIT` decision preserves D-020's post-action contact and
same-transition charging semantics. The controller does not anticipate the
45, 60, or 65 °C evaluator thresholds and contains no thermal action rule.

## Frozen setup and seed policy

Each lifetime begins with:

- body position `(0.5, 0.5)`;
- station center `(0.5, 0.5)`;
- battery `5328.0 J`, exactly `D020PhysicalConfig().battery_capacity_j`;
- body temperature `23.0 °C`;
- charger termination latch `False`;
- controller mode `CHARGE`;
- heading `RandomStreams.from_seed(seed).environment.uniform(0.0, 2π)`.

The policy uses `RandomStreams.from_seed(seed).policy`. No RNG is reseeded or
reset within a lifetime or on a mode transition. The runner first calls
`validate_exp003_development_seeds(...)`, then rejects every seed except the
exact declared set `(18365, 18366, 18367)`. The canonical formal reservation
guard remains active; no formal EXP reservation was created and no reserved
seed was used.

`D020PhysicalConfig()` is unchanged in every physical value. The sole runner
override is `episode_horizon=70000`. The accepted D-020 timestep remains
`0.1 s`, so the frozen horizon is `7,000.0 s`.

## Execution provenance and repair history

The first frozen substantive execution used implementation SHA
`ee8e59530726c54a69a8c8ec934f0d4edbcde754`. It completed all three lifetimes,
but the evaluator ledger incorrectly labelled expected exits from accidental
AWAY contacts as mode/event inconsistencies. That artifact is invalidated.

Only that evaluator classification defect was fixed. No controller threshold,
exploration hazard, physical parameter, initial condition, seed, horizon, or
event definition changed. The corrected implementation SHA
`0dd310cf1324319bb64a603f3a293b70db4ecbd2` passed focused tests and clean
validation before all three seeds were rerun. The final machine-readable
artifact is [`D-021-v04-autonomous-energy-regulation-baseline.json`](D-021-v04-autonomous-energy-regulation-baseline.json).

No scientific, controller, or physical value changed after substantive output
was first inspected. The invalidated attempt is preserved here as provenance,
and the final artifact contains only the corrected rerun.

## Corrected descriptive results

All three lifetimes reached the frozen horizon without energy depletion or
thermal shutdown. Each completed one conservative energy-regulation cycle:
initial full departure, physical charger exit, low-energy SEEK entry, physical
reacquisition, full recharge, and post-recharge departure. The horizon then
censored the next incomplete cycle; this is not treated as demonstrated
failure.

| Seed | Heading (rad) | Final mode | Min / final normalized energy | Min / final battery (J) | Max temperature (°C) | Full departures | Exits | SEEK / reacq. | Recharge / re-depart. | Completed cycles | Accidental AWAY contacts |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 18365 | 5.7452131874 | AWAY | 0.499903 / 0.648307 | 2663.4855 / 3454.1785 | 24.275449 | 2 | 90 | 1 / 1 | 1 / 1 | 1 | 88 |
| 18366 | 1.1544805814 | AWAY | 0.499732 / 0.649966 | 2662.5725 / 3463.0200 | 24.275840 | 2 | 94 | 1 / 1 | 1 / 1 | 1 | 92 |
| 18367 | 5.6984393743 | AWAY | 0.499600 / 0.648339 | 2661.8715 / 3454.3520 | 24.276077 | 2 | 97 | 1 / 1 | 1 / 1 | 1 | 95 |

Every seed started at normalized energy `1.0` and normalized temperature
approximately `0.2875`. Every run lasted `70,000` transitions / `7,000.0 s`
and ended by `horizon_truncation`. None had an unresolved SEEK episode at the
horizon, a demonstrated failed SEEK, reacquisition followed by termination
before recharge, or full recharge without re-departure. The compact SEEK
episodes are preserved in JSON: reacquisition occurred after 5, 14, and 21
transitions for seeds 18365, 18366, and 18367 respectively.

The extra physical charger exits beyond the two full departures per seed were
not missing cycles: they were contact exits after accidental AWAY contacts,
which were separately counted. No mode/event inconsistencies remained after
the accounting repair.

## Thermal null and interpretation

The maximum absolute temperatures were `24.275449 °C`, `24.275840 °C`, and
`24.276077 °C`. The maximum normalized temperatures were approximately
`0.303443`, `0.303448`, and `0.303451`; final temperatures were approximately
`23.628244 °C`, `23.629791 °C`, and `23.627894 °C`. No seed reached the
evaluator-only preferred `45 °C` ceiling, `60 °C` protective shutdown, or
`65 °C` emergency shutdown.

**Direct observation:** Under these three declared development seeds and the
frozen 70,000-transition horizon, the fixed programmed controller completed
one full energy-regulation cycle per lifetime and physically reacquired the
charger once per lifetime. All runs survived to horizon truncation.

**Inference:** This narrow D-021 composition is compatible with a fixed
programmed energy-regulation baseline under D-020 bookkeeping. It does not
show that the inherited `0.50` threshold is optimal, that the controller is
robust outside these seeds/setup, or that thermal regulation has been earned.
The near-ambient thermal result is retained as a null rather than engineered
away.

## Validation and disposition

Before the corrected substantive rerun, the exact implementation SHA passed:

- `uv run python -m compileall -q src` — clean;
- `uv run pytest -q tests/test_d021.py` — **20 passed**;
- `uv run ruff check .` — clean;
- `uv run mypy src --strict` — clean;
- `git diff --check` — clean.

The final artifact is development evidence only. The narrow disposition is
**CONTINUING**: preserve this fixed baseline and the negative/null thermal
finding while Flow decides the next explicitly authorized developmental
question. No D-022 is started or proposed by this record.
