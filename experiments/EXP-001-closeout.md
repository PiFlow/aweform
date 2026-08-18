# EXP-001 — Formal Closeout

**Status:** CLOSED

**Protocol revision:** `EXP-001-precalibration-003`

**Execution Git SHA:** `940e355bd16a28b372bd042de931c3a57366599b`

**Confirmatory artifact SHA-256:**
`b93958d173eaf80eb83a1c6dde485390d7b222d9cd0007837bf71952873b4627`

**Calibration artifact SHA-256:**
`1fe4ce9217d93b70c94a7a81dbe949f971d95401e83d7056b5bd8374696f17e4`

The completed confirmatory artifact, analysis JSON, analysis Markdown report,
and completed reservation marker are preserved under `artifacts/`. The
reservation marker remains intentionally present with status `completed` so
the formal execution remains visibly consumed and cannot be rerun.

## A. Confirmed result

The formal result is **`C_GREATER`**.

- Primary estimand: mean paired `B - C` capped lifespan
- Mean paired B−C capped lifespan: **`-125.765` transitions**
- 95% paired percentile-bootstrap interval:
  **`[-142.812125, -108.906000]` transitions**
- Matched pairs: **`n = 1000`**
- Confirmatory seeds: **30001–31000 inclusive**
- Conditions: `A_PERSISTENT_EXPLORATION`,
  `B_INTEROCEPTIVE_HOMEOSTASIS`, and `C_ENERGY_BLIND_HOMEOSTASIS`
- Calibrated C: **SHORT**, EXPLORE `10`, CHARGE `5`

Inference is limited to the frozen 1000-transition EXP-001 simulator
environment. The endpoint is capped at that horizon and does not establish
anything about lifetime beyond 1000 transitions.

## B. Descriptive observations

These observations are descriptive and do not replace the primary B−C
estimand.

| Condition | Mean capped lifespan | Horizon survivors | Mean minimum normalized energy | Mean complete cycles |
| --- | ---: | ---: | ---: | ---: |
| A_PERSISTENT_EXPLORATION | 69.343 | 0 / 1000 | — | 0.000 |
| B_INTEROCEPTIVE_HOMEOSTASIS | 848.047 | 735 / 1000 | 0.068013 | 5.943 |
| C_ENERGY_BLIND_HOMEOSTASIS | 973.812 | 973 / 1000 | 0.314640 | 43.925 |

The A minimum-energy value is not required for the closeout result and is not
reported here. The recorded A, B, and C horizon-survival counts are
descriptive only.

## C. Hypothesis for later experiments

Visual observations together with the descriptive diagnostics are consistent
with the hypothesis that B's `SEEK_RESOURCE` transition at energy below `0.35`
may occur too late to leave sufficient return reserve when B has ranged far
from the resource.

EXP-001 did **not** formally measure distance to the resource at
`SEEK_RESOURCE` onset. This mechanism is therefore a follow-up hypothesis,
not a confirmed EXP-001 causal conclusion.

## D. Scientific interpretation

Within the frozen EXP-001 simulator, calibrated fixed-timing energy-blind C
had greater mean capped lifespan than interoceptive B.

This closeout does not show that interoception is generally harmful or that
fixed schedules are generally superior. It makes no claim about biological
organisms, physical Aweforms, consciousness, or lifetime beyond 1000
transitions.

The frozen pre-calibration protocol remains unchanged as a historical
preregistration artifact. EXP-001 controllers, environment, calibration,
protocol, and completed results are not modified by this closeout. EXP-002 is
not started here.
