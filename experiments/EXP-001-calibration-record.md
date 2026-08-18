# EXP-001 Calibration Record

**Status:** Frozen calibration/development record — not confirmatory evidence

This record documents the completed EXP-001 C-only calibration under the
frozen pre-calibration design. It is a result record, not a new protocol
revision. The historical protocol remains unchanged at
`EXP-001-precalibration-003`.

## Identity

- Experiment: `EXP-001`
- Protocol: `EXP-001-precalibration-003`
- Execution/recovery Git SHA: `2869ea2df29d5bd95bb77492cc06301c64d66b8f`
- Formal artifact: `artifacts/EXP-001-formal-calibration-precalibration-003.json`
- Artifact SHA-256: `1fe4ce9217d93b70c94a7a81dbe949f971d95401e83d7056b5bd8374696f17e4`
- Artifact schema: `exp-001-calibration-v1`
- Python: `3.14.7`
- NumPy: `2.5.2`

## Calibration boundary

- Condition: C only
- Master seeds: `20001–20200` inclusive (200 seeds)
- C episodes: 600 total — three candidates on each master seed
- A executed: no
- B executed: no
- Confirmatory seed executed: no
- Classification: calibration/development output, not confirmatory evidence

No individual-seed results, trajectories, A results, B results, B−C
comparisons, or confirmatory outcomes are included in the artifact or this
record.

## Candidate results

The following aggregate diagnostics are copied from the immutable formal
artifact.

| Candidate | EXPLORE | CHARGE | Episodes | Mean capped lifespan | Median capped lifespan | Minimum | Maximum | Horizon survival |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SHORT | 10 | 5 | 200 | 975.77 | 1000.0 | 29 | 1000 | 195/200 (0.975) |
| CURRENT | 20 | 10 | 200 | 791.555 | 1000.0 | 27 | 1000 | 157/200 (0.785) |
| LONG | 30 | 15 | 200 | 583.52 | 1000.0 | 26 | 1000 | 114/200 (0.57) |

| Candidate | Mean final normalized energy | Mean minimum normalized energy | Mean total harvested energy |
| --- | ---: | ---: | ---: |
| SHORT | 0.9706025290950991 | 0.32051516944048003 | 320.32510709074535 |
| CURRENT | 0.7535576068405362 | 0.21425733797524138 | 214.6174573068717 |
| LONG | 0.5013755308702654 | 0.1387026771692062 | 139.9644605460302 |

| Candidate | Mean EXPLORE actions | Mean SEEK_RESOURCE actions | Mean CHARGE actions | Mean complete cycles |
| --- | ---: | ---: | ---: | ---: |
| SHORT | 499.295 | 229.905 | 246.57 | 43.905 |
| CURRENT | 411.78 | 181.03 | 198.745 | 18.975 |
| LONG | 321.185 | 112.915 | 149.42 | 9.41 |

## Frozen selection

**Selected C baseline: `SHORT` — EXPLORE 10 / CHARGE 5**

The frozen selection rule selected SHORT uniquely at criterion 1, highest mean
C capped lifespan: `975.77`, compared with CURRENT at `791.555` and LONG at
`583.52`. Criteria 2–4 were not needed.

For subsequent EXP-001 work:

`CALIBRATED_C = SHORT = EXPLORE 10 / CHARGE 5`

This calibration result is not a B-versus-C result. It does not establish
whether interoception succeeds or fails and does not support a confirmatory
scientific claim.

## Persistence incident and deterministic recovery

1. The first formal execution used the correct reviewed Git SHA and completed
   all 600 C episodes.
2. Persistence then failed because the `artifacts/` parent directory did not
   exist.
3. No candidate aggregates or selected result from that first execution were
   inspected.
4. No scientific parameter, protocol, source code, seed range, or runtime
   configuration was changed.
5. The same deterministic calibration was replayed exactly once on the
   identical reviewed Git SHA solely to reconstruct the lost aggregate
   artifact.
6. Recovery succeeded.
7. The recovered artifact identified above is the artifact frozen in this
   record.
8. No additional replay is authorized.

The recovery was not a second independent calibration sample. The calibration
seeds remain development/calibration data only, and the confirmatory seeds
`30001–31000` remain untouched.

## Protocol preservation

The frozen document
[`EXP-001-precalibration-protocol.md`](EXP-001-precalibration-protocol.md)
and the frozen statistical addendum
[`EXP-001-confirmatory-statistical-addendum.md`](EXP-001-confirmatory-statistical-addendum.md)
were not revised by this record. No confirmatory runner, bootstrap analysis,
or B-versus-C execution is authorized by this record.
