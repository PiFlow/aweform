# D-042 — Founder-selected fine-turn and front-contact baseline

- **id:** D-042
- **issue:** [#147](https://github.com/PiFlow/aweform/issues/147)
- **lane:** Development
- **authorized_base_sha:** `ad0fa81083d37cd3976e77777ffe22a04b965d59`
- **implementation_probe_sha:** `26377e04c871085831726ae73a4210adc9a44ca3`
- **development_seeds:** `19042, 19043, 19044`
- **horizon:** `70,000` transitions per uninterrupted lifetime
- **disposition:** `CONTINUING`
- **learned mechanism:** existing D-030/D-027 organism reused unchanged

The compact machine-readable characterization is
[`D-042-founder-embodiment-baseline.json`](D-042-founder-embodiment-baseline.json).
It is a Development artifact, not confirmatory evidence.

## Question and boundary

D-042 Phase B implements the already accepted ADR 0016 founder embodiment:

- each `TURN_LEFT`/`TURN_RIGHT` action is `+/- pi/36` radians (`+/-5°`);
- each turn remains one `0.1 s` action with the existing `0.65 W` turn-actuator
  electrical power;
- the corresponding body charging contacts are on the front face at
  `(+0.05,+0.025)` and `(+0.05,-0.025)`;
- the fixed station-centred dock remains at `phi = 0` with contacts
  `(0,+0.025)` and `(0,-0.025)`;
- both corresponding pair errors must satisfy inclusive `<= 0.01` tolerance;
- the exact station-centred initial dock is body centre `(0.45,0.50)` and
  heading `0`.

The implementation is isolated in `src/aweform/d042.py`. Historical D-020
through D-041 source and replay semantics remain unchanged. The current
canonical organism is reused: `d026.D026Controller`, D-030 learned SEEK
steering arbitration, and `d027.D027ActionConsequencePredictor`. No D-041
receptors are exposed. Coordinates, heading, contact errors, absolute energy,
and absolute temperature remain evaluator-only.

The visible interface remains exactly six channels, the four existing actions,
reward `0.0`, and organism-facing `info == {}`. The D-020 energy/thermal
equations, timestep, movement, beacon semantics, D-026 de-trap/RNG semantics,
and D-027 update semantics are reused without tuning.

## Frozen characterization protocol

The run used only legal Development seeds `19042, 19043, 19044`, checked by
`validate_exp003_development_seeds`; no formal EXP reservation was used. Each
seed was one uninterrupted causal lifetime at `70,000` transitions. The
protocol and executable tree were cleanly committed before execution. No
controller, learner, seed, horizon, threshold, sensor, or interpretation was
changed after observing results.

Artifact provenance:

- executable/protocol SHA: `26377e04c871085831726ae73a4210adc9a44ca3`;
- artifact size: `7,693` bytes;
- artifact SHA-256: `bd4a71aee98a2f8be14a591763451af974f676425226e27f145d19b2e5752ba1`;
- regeneration from the same SHA and command was byte-identical (`cmp` pass).

## Descriptive observations

| Seed | Outcome | Transitions | Contact entries | SEEK reacquisitions | Full recharges | Turns | Turn electrical energy (J) | Max body temperature (°C) |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 19042 | SEEK reacquired; horizon-censored | 70,000 | 1 | 1 | 1 | 10,195 | 662.675 | 24.348991 |
| 19043 | SEEK reacquired; horizon-censored | 70,000 | 1 | 1 | 1 | 8,187 | 532.155 | 24.308858 |
| 19044 | SEEK reacquired; horizon-censored | 70,000 | 1 | 1 | 0 | 19,022 | 1,236.430 | 24.385502 |

Across the three lifetimes there were three dual-contact entries, three
physical SEEK reacquisitions, two full recharge events, and no energy or
thermal shutdown. All three runs remained unresolved at the declared horizon;
they are horizon-censored, not failures. The run therefore demonstrates that
the existing canonical organism executes under the new embodiment and can
reacquire on this small Development characterization. It does not establish
robustness, optimality, general docking competence, learning necessity, or any
biological claim.

The selected embodiment is a programmed physical/action change. The
reacquisition and energy/thermal observations are behaviour of the unchanged
canonical D-030/D-027 organism under that change. These categories must not be
conflated.

## Validation and preservation

- focused D-042 tests: `9 passed`;
- full repository tests: `1,010 passed, 7 warnings`;
- Ruff: passed;
- strict mypy: passed (`72` source files);
- compile/import checks: passed;
- `git diff --check`: passed;
- historical replay/default protection is covered by focused D-024/D-020
  regression assertions and the unchanged full suite.

No new sensor, action, controller, learner, memory, rescue rule, planning,
reinforcement learning, ecology, EXP execution, or D-043 work is included.
