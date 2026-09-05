# D-027 — Shadow sensorimotor consequence learning

- **id:** D-027
- **lane:** Development
- **authoritative_base_sha:** `1059b7a02cf7964f1f1bf48c39db20e1f3a1edc9`
- **development_seeds:** `18388..18407` inclusive (20 seeds)
- **horizon:** `70,000` transitions per uninterrupted lifetime
- **learning rate:** `0.5`
- **plastic state:** `168` weights (`4 × 6 × 7`)
- **disposition:** `CONTINUING`

The machine-readable numerical source is
[`D-027-shadow-sensorimotor-consequence-learning.json`](D-027-shadow-sensorimotor-consequence-learning.json).

## Scientific question and frozen scope

D-027 asks whether a deliberately small shadow learner can acquire one-step
changes across all six existing organism-visible channels from the current
visible state and the physically executed action, while the unchanged D-026
controller retains every behavioural decision. This is descriptive
Development-lane work. It is not a confirmatory claim.

D-026 behaviour is retained exactly: its `1/3` false-contact SEEK delegation,
the existing explorer hazard `1/8`, policy RNG continuity and segment
semantics, D-024 finite-body dual-contact physics, D-020 energy/thermal
bookkeeping, four actions, six channels, reward `0.0`, and `info == {}`.
No visualizer, sensor, collision mechanic, wall contact, action, reward,
history, recurrence, replay, counterfactual query, planning, RL, world model,
EXP work, or D-028 work is included.

## Frozen learner and causal order

The current feature vector is exactly:

```text
[1.0, energy, beacon.left, beacon.forward, beacon.right,
 float(charging_contact), thermal]
```

The six outputs are `delta_energy`, `delta_beacon_left`,
`delta_beacon_forward`, `delta_beacon_right`, `delta_charging_contact`, and
`delta_thermal`. Four action-specific sets contain seven features for each
output, for exactly 168 scalar weights. They begin at zero once per deliberate
new lifetime and are the only retained learned state. There is no optimizer
state, buffer, history, recurrence, adaptive rate, confidence state, or RNG.

For every transition the order is:

1. construct the current typed six-channel observation;
2. let unchanged D-026 select the one real action;
3. compute the executed-action pre-update prediction;
4. execute one real environment transition;
5. construct the actual next typed six-channel observation;
6. apply normalized LMS with `weights += 0.5 * error * x / dot(x, x)`;
7. compute evaluator-only diagnostics.

Only the physically executed action updates. The learner receives no evaluator
truth, pose, displacement, label, mode, seed, horizon, RNG, reward, or future
observation, and its output has no path to action selection or viability.

## Boundary diagnostic

For executed `MOVE_FORWARD`, evaluator-only realized centre displacement is
classified with tolerance `1e-12`: `FULL_NOMINAL_FORWARD` is equal to `0.05`,
`BOUNDARY_CLIPPED_FORWARD` is less than `0.05 - 1e-12`, and
`FULL_STALL_FORWARD` is additionally counted when displacement is at most
`1e-12`. A displacement above `0.05 + 1e-12` is a consistency failure. These
labels do not alter the existing centre-clamp physics and never enter learning
or control.

## Provenance and execution

The exact executable freeze SHA is recorded in the JSON artifact as
`implementation_probe_sha`. The substantive command is:

```text
UV_CACHE_DIR=/private/tmp/aweform-uv-cache uv run python -m aweform.d027 \
  --seeds 18388 18389 18390 18391 18392 18393 18394 18395 18396 18397 \
  18398 18399 18400 18401 18402 18403 18404 18405 18406 18407 \
  --horizon 70000 --executed-commit-sha <freeze-sha> \
  --output development/D-027-shadow-sensorimotor-consequence-learning.json
```

The canonical `validate_exp003_development_seeds` guard and the exact D-027
guard accept only the ordered seed block above. No formal reservation is
touched. If a genuine defect invalidates a substantive run, its executable
SHA and artifact provenance must be retained and the corrected run must start
from scratch; no outcome-driven tuning is permitted.

## Required reporting

The compact artifact reports per-seed and pooled behaviour, action and target
support, contact-delta event counts, full/clipped/stall support, learned versus
zero-change MAE for all six outputs overall/by action/by Q1–Q4, boundary-
stratified overall and Q4 metrics with observed/predicted delta vectors and
beacon-delta magnitudes, complete final 168-weight snapshots, and exact
per-transition trajectory-digest isolation against a matched no-learner D-026
replay. Empty support is `untested`.

## Provenance categories

**PROGRAMMED:** unchanged D-026/D-024/D-020 scaffold; the fixed 168-weight
linear normalized-LMS learner; evaluator-only boundary classifier and metrics.

**ORGANISM-VISIBLE / PLASTIC UPDATE INPUTS:** only the six current channels,
the own executed action, and the six actual next channels after the transition.

**LEARNED:** exactly 168 action/output/feature weights.

**EVALUATOR-ONLY:** pose, heading, displacement, bounds, boundary labels,
telemetry, mode/outcome labels, transition windows, error metrics, and
isolation digests.

**INFERRED:** only cautious descriptive observations about experienced
one-step prediction in this exact fixed ecology.

## Results

Results are populated only from the clean frozen executable SHA and retained
in the JSON artifact. They do not establish wall awareness, self-protection,
counterfactual competence, planning, a world model, intelligence,
consciousness, emotion, subjective experience, genuine life, metabolism, or
hardware autonomy.

## Validation and disposition

The final record names the focused/full tests, Ruff, strict mypy, compileall,
whitespace, deterministic replay, shadow-isolation, artifact regeneration, and
exact-current-HEAD CI results. D-027 has no binary success threshold; null,
mixed, and negative observations remain valid. Disposition is `CONTINUING`.
