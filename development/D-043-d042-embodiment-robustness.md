# D-043 — Fresh-seed repeated-cycle robustness of the accepted D-042 embodiment

- **id:** D-043
- **issue:** [#149](https://github.com/PiFlow/aweform/issues/149)
- **lane:** Development
- **authorized_base_sha:** `1cec3df44ff74995f10f270577d6d8aa1d08d025`
- **implementation_probe_sha:** `d2afb050366b2d074bd92e03f2faf3146989a60c`
- **development_seeds:** `19045..19064` (20 fresh legal Development seeds)
- **horizon:** `140,000` transitions per uninterrupted lifetime unless canonical termination
- **disposition:** `CONTINUING`
- **learned mechanism:** existing D-030/D-027 organism reused unchanged

The compact machine-readable characterization is
[`D-043-d042-embodiment-robustness.json`](D-043-d042-embodiment-robustness.json).
It is a descriptive Development artifact, not confirmatory evidence.

## Frozen protocol and boundary

D-043 instantiated the unchanged canonical D-042 environment from
`src/aweform/d042.py`: 5° turns, 0.1 s action timing, 0.65 W turn-actuator
power, front corresponding dual contacts, inclusive 0.01 pair tolerance,
the six visible channels, four existing actions, unchanged station-centred
L/F/R beacon, D-026 de-trap/RNG semantics, D-030 arbitration, D-027 learner,
reward `0.0`, and organism-facing `info == {}`. Each seed ran one continuous
lifetime. Event and physical geometry diagnostics were evaluator-only and
were not fed into action selection, learning, reward, or `info`.

The runner records every dual-contact entry/exit, SEEK episode and outcome,
reacquisition latency, recharge event, post-recharge departure, completed
autonomous cycle, action/turn exposure, mode occupancy/entries, energy, and
temperature. Null and censored fields are retained per episode.

## Descriptive results

| Measure | Result |
|---|---:|
| Seeds entering low-energy SEEK | 20/20 |
| Seeds reacquiring physical dual contact at least once | 11/20 |
| Seeds completing at least one full recharge after reacquisition | 11/20 |
| Seeds completing at least two autonomous recharge cycles | 1/20 |
| Physical reacquisitions / full recharge events / completed cycles | 13 / 12 / 12 |
| Reacquisition latency range | 3,657–24,587 transitions (365.7–2,458.7 s); median 11,126 transitions (1,112.6 s) |
| SEEK episodes unresolved at horizon | 0 |
| SEEK episodes unresolved at energy termination | 18 |
| Energy / thermal failure lifetimes | 18 / 0 |
| Horizon-truncated lifetimes | 2 |

The per-seed support, including transitions, physical duration, termination,
energy minima/finals, maximum temperature, action and turn counts/exposure,
mode counts, event records, cycle spacing, and null episode fields is retained
in the artifact.

Fresh support is qualitatively more fragile than the three-seed D-042
characterization: D-042 reacquired on all 3 seeds, while D-043 reacquired on
11 of 20 and produced only one seed with two completed autonomous cycles.
The dominant negative outcome was energy depletion during an unresolved SEEK
episode after the first departure/reacquisition opportunity; no thermal
failure occurred. This is a descriptive comparison, not a statistical
generalization or a universal robustness threshold.

## Provenance and validation

- artifact size: `79,704` bytes;
- artifact SHA-256: `b1bf72d6854519e8e24c1dc29970d1d008305a129418eeb661f7e56ad5e3dc4a`;
- the canonical seed validator rejected formal reservations and the exact
  declared fresh support was enforced;
- regeneration from the same executable SHA and command was byte-identical
  (`cmp` pass);
- focused D-042/D-043 tests: `14 passed`;
- full repository pytest: `1,015 passed, 7 warnings`;
- Ruff: passed;
- strict mypy for the D-043 module: passed;
- compile/import checks and `git diff --check`: passed.

No controller, learner, memory, sensor, action, reward, ecology, physical
boundary, EXP execution, or successor mechanism was added. No universal pass
threshold is proposed.
