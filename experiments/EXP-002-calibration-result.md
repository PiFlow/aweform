# EXP-002 formal calibration evidence

## Provenance and hashes

- Artifact: `artifacts/EXP-002-formal-calibration-precalibration-001.json`
- Artifact SHA-256: `43297b1ac65af2b88ddf9f763506e9bd310e8bac866d3652db397815eda15e25`
- Reservation: `artifacts/EXP-002-formal-calibration-precalibration-001.json.reservation`; status `completed`
- Reservation artifact SHA-256: `43297b1ac65af2b88ddf9f763506e9bd310e8bac866d3652db397815eda15e25`
- Execution Git SHA: `513a7271caf3fd57591a27ccc7477a06c0ab8802`
- Schema: `exp-002-formal-calibration-v1`
- Protocol: `experiments/EXP-002-interoceptive-seek-threshold.md`
- Protocol SHA-256: `18875e9e97221db0dcb7acb1ee50d9dc6546dd619d9f871430801335455f77d1`
- Scientific-contract SHA-256: `cc982be0da525aafdab478442d753a3132bf6b006ee524e40e9f740a720637c6`
- Episode count: `800` (`200` per candidate)
- Calibration seeds: `40001–40200` inclusive
- Candidate set: `B35`, `B40`, `B45`, `B50`
- Raw trajectories persisted: `false`

## Per-candidate aggregate results

Selection variables:

| Candidate | SEEK threshold | Horizon survival | Survival fraction | Mean visited cells / 1024 |
|---|---:|---:|---:|---:|
| B35 | 0.35 | 151 / 200 | 0.755 (75.5%) | 417.305 / 1024 |
| B40 | 0.4 | 175 / 200 | 0.875 (87.5%) | 447.855 / 1024 |
| B45 | 0.45 | 191 / 200 | 0.955 (95.5%) | 464.355 / 1024 |
| B50 | 0.5 | 196 / 200 | 0.98 (98%) | 471.0 / 1024 |

Descriptive diagnostics:

| Candidate | Mean coverage fraction (%) | Mean explore actions | Mean explore distance | Mean explore unique cells | Coverage efficiency / 100 explore actions | Mean capped lifespan | Median capped lifespan | Min capped lifespan | Max capped lifespan | Complete recharge-cycle mean | SEEK attempts | Reached-CHARGE count | Reached-CHARGE fraction | Mean SEEK-onset energy | Mean source distance at SEEK onset | Mean minimum energy during SEEK |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| B35 | 0.4075244140625 (40.75244140625%) | 565.975 | 15.755358059199708 | 345.115 | 66.79231398547171 | 852.82 | 1000.0 | 29 | 1000 | 6.07 | 1311 | 1242 | 0.9473684210526315 | 0.3414512365128462 | 0.7459838626947682 | 0.19190832950292064 |
| B40 | 0.4373583984375 (43.73583984375%) | 616.195 | 17.023595558410406 | 366.69 | 62.48084103568912 | 937.57 | 1000.0 | 31 | 1000 | 7.12 | 1495 | 1457 | 0.974581939799331 | 0.3911843362181966 | 0.7478159843792109 | 0.23913724401787206 |
| B45 | 0.4534716796875 (45.34716796875%) | 642.625 | 17.838420551019684 | 379.07 | 60.81212330935128 | 972.51 | 1000.0 | 34 | 1000 | 7.655 | 1599 | 1564 | 0.9781113195747342 | 0.4413907748494612 | 0.7510658391403917 | 0.2873259064822415 |
| B50 | 0.4599609375 (45.99609375%) | 649.24 | 18.067621232701953 | 378.145 | 59.03678572141274 | 988.395 | 1000.0 | 124 | 1000 | 8.415 | 1759 | 1725 | 0.9806708357021034 | 0.49078628144107184 | 0.7421869573900701 | 0.34083822246785195 |

## Frozen-rule selection

- Eligibility: `horizon_survival_count >= 180 / 200`.
- If any candidate is eligible, choose the eligible candidate with greatest `mean_visited_cell_count`.
- If none is eligible, choose the candidate with greatest `horizon_survival_count`.
- Tie-break: greater `mean_visited_cell_count`, then lower SEEK threshold.
- Eligible candidates: `B45`, `B50`.
- Independent recomputation from the persisted aggregates selects `B50` through `eligible_max_coverage`; the stored selection is also `B50`.

This is development/calibration evidence, not confirmatory evidence. Confirmatory seeds `50001–51000` remain untouched.
