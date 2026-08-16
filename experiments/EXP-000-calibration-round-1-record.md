# EXP-000 Calibration Round 1 Result Record

This is an immutable research record for Calibration Round 1. It records
calibration diagnostics only; it is not a scientific B>C result and does not
support a confirmatory interpretation.

## Frozen Round-1 configuration

- `resource_count = 1`
- `episode_horizon = 500`
- `masked_energy = 0.5`
- calibration seeds: `1001–1030`
- resource length scales: `0.15`, `0.20`, `0.25`
- C qualification: mean lifespan inclusive `100–400`
- B recovery qualification: at least `6/30` seeds with a completed
  `SEEK_RESOURCE → EXPLORE` recovery
- selection: qualifying C mean lifespan closest to `250`
- exact tie: smaller length scale
- B−C advantage was not used for selection

## Candidate diagnostics and qualification

| Length scale | C mean lifespan | B recovery seeds | A/C identity | Qualified |
| ---: | ---: | ---: | :---: | :---: |
| 0.15 | 31.27 | 24/30 | 30/30 | No |
| 0.20 | 39.00 | 28/30 | 30/30 | No |
| 0.25 | 48.70 | 29/30 | 30/30 | No |

No Round-1 candidate qualified because every C mean lifespan was below 100.

## Artifact SHA-256 fingerprints

- 0.15: `9b6c5712b2c0ec294f9766e64b564286da07199866795c44168ea805dee885a8`
- 0.20: `a2dc400056254b29cf03061ccb155048c113d2fd7d20aaa4ad79c7933ac1695d`
- 0.25: `4d85f2366b425e4ebc377c860f0496ae4bda3c99139abd2b49c6f669db121685`
- Round-1 summary:
  `3a842654cd5a5cf49a61e9785a9b0e7bc7d1498d5026ca7c96522f4809aae990`

## Round-2 motivation

Round 2 was motivated solely by the too-high C baseline difficulty observed in
Round 1 and the known geometry of the existing single Gaussian-like resource
field. It was not motivated by B−C advantage. No raw trajectories are copied
into Git by this record.
