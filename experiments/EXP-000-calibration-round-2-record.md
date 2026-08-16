# EXP-000 Calibration Round 2 Result Record

This is an immutable development/calibration record. It is not confirmatory
evidence and does not report a B−C scientific result.

## Frozen Round-2 configuration

- `resource_count = 1`
- `episode_horizon = 500`
- `masked_energy = 0.5`
- calibration seeds: `1001–1030` (30 matched seeds)
- candidate `resource_length_scale` values: `0.35`, `0.40`, `0.45`
- C qualification: mean lifespan in the inclusive `100–400` band
- B mechanism qualification: at least `6/30` seeds with a completed
  `SEEK_RESOURCE → EXPLORE` recovery
- selection: among qualifying candidates, C mean lifespan closest to `250`
- exact tie rule: choose the smaller length scale
- B−C performance was not used for selection or interpretation

## Candidate diagnostics and selection

| Length scale | C mean capped lifespan | B recovery seeds | C qualification | Distance from 250 | Selected |
| ---: | ---: | ---: | :--- | ---: | :--- |
| 0.35 | 172.03 | 30/30 | Qualifies | 77.97 | No |
| 0.40 | 294.93 | 20/30 | Qualifies | 44.93 | **Yes** |
| 0.45 | 436.90 | 14/30 | Fails C difficulty band | 186.90 | No |

A/C matched trajectory identity was `30/30` for every candidate. At the
selected `resource_length_scale = 0.40`, B reached the 500-step horizon in
all 30 calibration episodes.

The B horizon observation is calibration/development information only. It is
not confirmatory evidence and must not be used as evidence for the B−C
confirmatory estimand.

The confirmatory estimand is the paired difference in lifespan, where lifespan
is capped at the frozen 500-step episode horizon.

The frozen rule mechanically selects `resource_length_scale = 0.40` because
it qualifies and has the smallest distance from the target C mean lifespan of
250 among qualifying candidates.

## Round-2 SHA-256 fingerprints

- 0.35 artifact: `0aa409f1c69e62994648b585c992b6d73c5442b01e5af571d13dc758387d2ad1`
- 0.40 artifact: `6f6a5304e69e2f3893b5a8524369515420bc083407dc33819b768c36730bffed`
- 0.45 artifact: `daca461093991efa90dcb3beda1bec09d7051da189387236d0d7ccafc2413535`
- Round-2 summary: `f52134dc635839d765feb995448c7cb2c064c98bb6770a04fb3e2cb0236e8d08`

The raw calibration artifacts are not copied into this record and are not
committed or changed by this preparation work.
