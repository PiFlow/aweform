# D-008 — Minimal action-conditioned one-step consequence model

- **id:** D-008
- **date:** 2026-08-29
- **exact_sha:** `a22efab0abe37ebbb758308393573ad121395f31`
- **development_seeds:** `18141, 18142, 18143`
- **horizon:** `1000`
- **disposition:** `CONTINUING`

## Scientific question

Can a tiny organism-owned learner acquire one-step predictions of visible
thermal and charging-contact consequences conditioned on the current visible
state and the organism's own selected action, while leaving the D-003 policy
unchanged? This is ordinary D-lane developmental work, not a pass/fail
benchmark or evidence-lane confirmation.

## Programmed scaffold

D-008 uses the unchanged D-003 `ThermostaticShuttleController` as the complete
behaviour policy in the stationary D-002 thermal ecology. The controller alone
selects every physical action. The evaluator-side post-contact setup, charging
circle radius `0.10`, charging heat coefficient `0.04`, passive cooling,
thermal failure boundary, energy dynamics, action costs, and 1000-transition
horizon are unchanged.

The programmed elements are the D-003 controller, D-002 physics, the feature
structure, linear model form, normalized LMS rule, learning rate `0.5`, and
zero initialization. The learner's output is shadow-only and has no causal
effect on action selection, environment execution, viability, or plasticity
modulation.

## Learner architecture

`D008ActionConsequencePredictor` retains two independent three-weight vectors
for each of `WAIT`, `TURN_LEFT`, `TURN_RIGHT`, and `MOVE_FORWARD`:

```text
x = [1.0, thermal, float(charging_contact)]
predicted_delta_thermal = dot(thermal_weights[action], x)
predicted_delta_contact = dot(contact_weights[action], x)
```

This is exactly `4 × 2 × 3 = 24` learned scalar weights. All weights begin at
exactly zero. There is no RNG, hidden unit, recurrent state, optimizer state,
eligibility trace, buffer, or additional learned object. The predictor has no
transient retained state. A deliberate `reset` is the only lifetime reset and
sets all weights to zero.

## Organism-visible information

`predict` receives only the typed D-003 observation (`thermal`,
`charging_contact`) and the organism's own `Action`. After the action occurs,
the update additionally receives only the typed next D-003 observation. The
target is therefore exactly:

```text
observed_delta_thermal = next.thermal - current.thermal
observed_delta_contact = float(next.charging_contact)
                         - float(current.charging_contact)
```

Energy, coordinates, station geometry, distance, heading, controller mode,
transition index, clock, horizon, seed identity, reward, info, evaluator
telemetry, offered energy, stored energy delta, thermal-input truth,
termination metrics, future observations, and labels are outside the causal
plasticity boundary. Reward remained exactly `0.0` and info remained `{}`.

## Plastic state and update equation

For the executed action only, the normalized least-mean-squares update is:

```text
prediction = dot(weights, x)
error = observed_delta - prediction
normalizer = dot(x, x)
weights_new = weights_old + 0.5 * error * x / normalizer
```

The thermal and contact vectors are updated independently. Unexecuted action
vectors remain unchanged. The machine-readable artifact records the final 24
weights and complete snapshots after transitions `250`, `500`, `750`, and
`1000` for every seed.

## Update timing/provenance

Each transition followed this causal order: form the current typed observation;
let D-003 select the action; compute and retain the pre-update prediction;
execute the action; form the next typed observation; update from the visible
transition; then read evaluator telemetry. Errors and zero-change comparator
values were evaluator summaries only and were not learner inputs.

The substantive execution was made once from clean Commit A using the exact
declared seeds and horizon. Before Commit A, one focused engineering test
accidentally called the runner for seed `18141` at horizon `1000`; it produced
no artifact and did not cause tuning or source changes. This process deviation
is disclosed here and in the handoff; the artifact is the single direct
substantive CLI execution from clean Commit A.

## Behaviour-policy isolation

The executable constructs a `ThermostaticShuttleController` and calls it for
every action. The predictor is never consulted by `act`, and its predictions
cannot rank, veto, modify, or bias actions. A focused test also compared the
recorded D-008 action sequence with the D-003 trace for the same seed and
horizon; they were action-for-action identical. No action was forced for model
coverage.

## Visitation/support diagnostics

The exact compact support and target summaries are in
[`D-008-minimal-action-conditioned-consequence-model.json`](D-008-minimal-action-conditioned-consequence-model.json).
Action counts were:

| Seed | WAIT | TURN_LEFT | TURN_RIGHT | MOVE_FORWARD |
|---|---:|---:|---:|---:|
| 18141 | 884 | 52 | 0 | 64 |
| 18142 | 897 | 52 | 0 | 51 |
| 18143 | 884 | 52 | 0 | 64 |

Contact/action counts (`current contact=false / true`) were:

| Seed | WAIT | TURN_LEFT | TURN_RIGHT | MOVE_FORWARD |
|---|---:|---:|---:|---:|
| 18141 | 428 / 456 | 52 / 0 | 0 / 0 | 13 / 51 |
| 18142 | 415 / 482 | 52 / 0 | 0 / 0 | 13 / 38 |
| 18143 | 428 / 456 | 52 / 0 | 0 / 0 | 13 / 51 |

`TURN_RIGHT` was unvisited in both contact contexts for all seeds. No D-008
inference is made about TURN_RIGHT consequence prediction. The `WAIT` and
`TURN_LEFT` supports are also narrow: `TURN_LEFT` occurred only off contact,
and `MOVE_FORWARD` occurred in a small set of thermal/contact regions. The
weights must not be interpreted as general action models outside these
visited supports.

## Direct observations

**Source:** exact JSON artifact emitted by the clean Commit A executable.

All three runs reached 1000 transitions, truncated at the horizon, and did not
terminate for energy or thermal failure. Minimum energy was `5.0` for all
seeds; final energy was `9.52000000000002` for seeds 18141 and 18143 and
`10.0` for seed 18142. Maximum thermal was approximately `0.63`, `0.62`, and
`0.63` respectively. Seeds 18141 and 18143 produced identical aggregate
results, while seed 18142 differed in WAIT/MOVE_FORWARD support and learned
weights.

The contact target support was highly concentrated. For every seed, off-contact
MOVE_FORWARD had `13` `+1` contact changes, contact MOVE_FORWARD had `13`
`-1` changes, and all other visited contact targets were `0`. Off-contact
TURN_LEFT had `52` zero contact changes. Thermal target deltas were generally
near `±0.01`; exact per-context extrema remain in the JSON.

## Prediction metrics

**Source:** exact JSON artifact; values are evaluator summaries of pre-update
predictions.

| Seed | Q1 thermal learned / zero | Q4 thermal learned / zero | Q1 contact learned / zero | Q4 contact learned / zero |
|---|---:|---:|---:|---:|
| 18141 | `0.0011178879 / 0.0100000000` | `0.0006521346 / 0.0099999999` | `0.0251217681 / 0.024` | `0.0225286425 / 0.028` |
| 18142 | `0.0010825474 / 0.0100000002` | `0.0006005218 / 0.0100000002` | `0.0250567118 / 0.024` | `0.0204535381 / 0.024` |
| 18143 | `0.0011178879 / 0.0100000000` | `0.0006521346 / 0.0099999999` | `0.0251217681 / 0.024` | `0.0225286425 / 0.028` |

Overall learned versus zero-change MAE was:

| Seed | Thermal learned / zero | Contact learned / zero |
|---|---:|---:|
| 18141 | `0.0008015421 / 0.0099999999` | `0.0243049298 / 0.026` |
| 18142 | `0.0007646334 / 0.0100000002` | `0.0232518250 / 0.026` |
| 18143 | `0.0008015421 / 0.0099999999` | `0.0243049298 / 0.026` |

The thermal predictor was below the zero-change comparator in every reported
quarter and seed, with lower late-quarter error. Contact prediction was above
the comparator in Q1 for every seed but below it in Q4. These are descriptive
patterns, not a frozen success threshold; no hard D-008 criterion is claimed.

## Zero-change comparator

The comparator predicts `0.0` for both visible deltas on every transition. Its
errors are `abs(observed_delta_thermal)` and
`abs(observed_delta_contact)`. It is evaluator-only, is not a reward, and does
not participate in plasticity or action selection.

## Learned-state checkpoints

The artifact contains complete snapshots at `250`, `500`, `750`, and `1000`
for each seed. Final vectors are shown as `[bias, thermal, charging_contact]`
for each action:

```text
18141
delta_thermal:
  WAIT         [-0.008911151547148307, -0.006371990091666401, 0.02095871995548745]
  TURN_LEFT    [-0.009299947874776013, -0.002618853089827339, 0.0]
  TURN_RIGHT   [0.0, 0.0, 0.0]
  MOVE_FORWARD [0.010299324932923041, -0.0020026372868170634, -0.009459912556135801]
delta_charging_contact:
  WAIT         [0.0, 0.0, 0.0]
  TURN_LEFT    [0.0, 0.0, 0.0]
  TURN_RIGHT   [0.0, 0.0, 0.0]
  MOVE_FORWARD [1.0461469630574425, -0.28704978774965567, -1.3693837012524752]

18142
delta_thermal:
  WAIT         [-0.008177758687597297, -0.006044780212093712, 0.021683449502591188]
  TURN_LEFT    [-0.009299947874776013, -0.002618853089827339, 0.0]
  TURN_RIGHT   [0.0, 0.0, 0.0]
  MOVE_FORWARD [0.010232155643211999, -0.0018272038570733098, -0.010230249699380578]
delta_charging_contact:
  WAIT         [0.0, 0.0, 0.0]
  TURN_LEFT    [0.0, 0.0, 0.0]
  TURN_RIGHT   [0.0, 0.0, 0.0]
  MOVE_FORWARD [1.0411381761120277, -0.27651727066546944, -1.405610542745879]

18143
delta_thermal:
  WAIT         [-0.008911151547148307, -0.006371990091666401, 0.02095871995548745]
  TURN_LEFT    [-0.009299947874776013, -0.002618853089827339, 0.0]
  TURN_RIGHT   [0.0, 0.0, 0.0]
  MOVE_FORWARD [0.010299324932923041, -0.0020026372868170634, -0.009459912556135801]
delta_charging_contact:
  WAIT         [0.0, 0.0, 0.0]
  TURN_LEFT    [0.0, 0.0, 0.0]
  TURN_RIGHT   [0.0, 0.0, 0.0]
  MOVE_FORWARD [1.0461469630574425, -0.28704978774965567, -1.3693837012524752]
```

## Mechanical inference

**Source:** exact artifact and source implementation. The predictor updated
only action-specific weights from visible current-to-next thermal/contact
deltas. The exact action-for-action D-003 trajectory comparison establishes
shadow isolation for the tested seed/horizon. The decreasing thermal MAE and
late-quarter contact MAE below the zero-change comparator are consistent with
action-specific on-policy fitting in visited contexts.

This does not establish a general world model, counterfactual knowledge,
planning, model-based control, causal understanding in a human sense,
generalization, intelligence, agency beyond the implementation, or necessity
of learning. Because the ecology is deterministic, residual ambiguity should
be considered against insufficient visitation, partial observability, omitted
causal state, linear capacity, nonstationarity, and representation choice—not
casually called environmental stochasticity.

## Surprised by

The smallest model produced a strong thermal-error reduction despite the
natural policy spending most transitions in `WAIT`. Contact prediction began
slightly worse than zero-change in Q1 for every seed but ended below that
baseline in Q4. The complete absence of `TURN_RIGHT` visits also makes the
four-action architecture visibly broader than the data actually support.

## Limitations

- This is one three-seed D-lane probe with a fixed 1000-transition horizon.
- Visitation is entirely on-policy; `TURN_RIGHT` was never executed, and no
  counterfactual claim is made for it.
- `TURN_LEFT` and `MOVE_FORWARD` were observed only in narrow contact/thermal
  regions; weights outside those supports are not evidence of generalization.
- The deterministic D-002 ecology and fixed post-contact setup do not test
  noise, delayed sensing, another geometry, another lifetime, or another
  ecology.
- The learner is shadow-only, so this probe does not test model-based action
  selection or whether learning is necessary for viability.
- The pre-Commit-A focused test execution at seed `18141`, horizon `1000`, was
  an execution-discipline mistake and is disclosed rather than treated as a
  second substantive artifact.

## Disposition

`CONTINUING`. Retain the null TURN_RIGHT support, the early contact-error
regression, the late-quarter improvements, and the exact compact artifact.
Any future claim about action-conditioned prediction beyond visited support or
any action-selection use requires a separately scoped developmental or formal
protocol.
