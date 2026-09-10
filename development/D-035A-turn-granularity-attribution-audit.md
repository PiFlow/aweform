# D-035A — Evaluator-only turn-granularity attribution audit

- **id:** D-035A
- **issue:** [#122](https://github.com/PiFlow/aweform/issues/122)
- **lane:** Development
- **authoritative_base_sha:** `d40681d25cd4cc67e359004ffcd63819e40b42a4`
- **base_tree_sha:** `50510ba772a1d53960f7f5870feb6b7b510cacf4`
- **development_seeds:** `18468..18487` inclusive, reused exactly
- **underlying lifetime horizon:** `70,000` transitions
- **counterfactual branch horizon:** at most `4,096` transitions from each anchor
- **status:** protocol frozen; substantive output recorded after execution
- **disposition:** `CONTINUING`

The machine-readable result is
[`D-035A-turn-granularity-attribution-audit.json`](D-035A-turn-granularity-attribution-audit.json).

## Question and boundary

D-035A asks whether the observed `LEARNED_NO_DETRAP` left/right oscillation is
partly attributable to the physical `45°` turn quantum. It changes only the
physical angular displacement of an already-selected turn action in isolated
evaluator counterfactual continuations. The accepted Arm-B organism remains
unchanged.

The canonical `D020PhysicalConfig.turn_angle`, `Action` identities, four-action
candidate set, sensor geometry, six visible channels, controller, D-027 learner,
energy/time accounting, environment, reward, `info`, RNG streams, and default
runtimes are not changed. The 5°, 2°, and 1° values are not organism actions,
continuous control, interpolation, or a hardware-energy claim. Turn timestep
and turn-energy accounting intentionally remain canonical and are reported as
an explicit confound.

No D-035B, D-036, EXP work, fresh seed, new sensor, learner, history,
planning/world model, ecology, physics, reward, or organism-facing diagnostic
is implemented.

## Frozen protocol

For every reused seed, the executable protocol first runs
`LEARNED_NO_DETRAP` with the accepted D-031R1 runner and requires exact
identity against the accepted D-031R1 Arm-B artifact. The gate checks all
available D-032 causal identity fields plus the complete private 168-weight
state, including outcome/termination, action and visible-trajectory digest,
executed-update digest, mode/action summaries, false-contact SEEK counts,
policy/environment RNG digests, zero false-contact SEEK explorer calls, and
one retained policy-RNG arbitration draw per false-contact SEEK decision.

Two evaluator-selected pre-action Arm-B anchors are used:

1. `FIRST_FALSE_CONTACT_SEEK`: the first pre-action state with Arm-B controller
   mode `SEEK` and false charging contact, immediately before ordinary no-de-
   trap arbitration. If the accepted replay terminates before such a state,
   the anchor is retained as unavailable rather than substituted.
2. `ALT8_ESTABLISHED`: the exact D-033 first pre-action state immediately after
   eight completed false-contact SEEK actions that are exclusively strict
   alternating `TURN_LEFT`/`TURN_RIGHT`, with no contact, `MOVE_FORWARD`, or
   `WAIT`. Its transition and complete anchor identity are checked against the
   accepted D-033 artifact. Unavailable seeds remain unavailable.

At each available anchor, clone the complete causal continuation state:
environment/physical state, current six-channel observation, controller mode
and transient/explorer state, complete D-027 weights, policy and environment
RNG state, transition index and inherited horizon, and the executed-update
provenance digest. Branch creation must not mutate the Arm-B source state.

Run exactly these four conditions from each available anchor:

| condition | turn angle |
|---|---:|
| `TURN_45_CONTROL` | `math.pi / 4.0` = 45° |
| `TURN_5` | `math.pi / 36.0` = 5° |
| `TURN_2` | `math.pi / 90.0` = 2° |
| `TURN_1` | `math.pi / 180.0` = 1° |

The controller chooses only existing action identities through the unchanged
Arm-B pipeline. The branch applies the condition angle only when the selected
action is a turn. Every condition retains the one policy-RNG draw at the
accepted timing, zero false-contact SEEK explorer calls, unchanged
`MOVE_FORWARD` and `WAIT`, one real transition, reward `0.0`, organism-facing
`info == {}`, and exactly one unchanged executed-action D-027 update from the
actual next six-channel observation. Branches stop at dual-contact
reacquisition, inherited termination/truncation, or 4,096 transitions.

`TURN_45_CONTROL` must equal the accepted D-033 Arm-B baseline continuation
from every available anchor on the comparable causal trace, summary, learner,
update, and RNG identity fields. Canonical/reverse condition order and
canonical/reverse read-only truth-branch order must be invariant.

## Frozen diagnostics

For each branch, retain pre-update predictions and actual visible deltas for
every executed action. Report prequential MAE for all six outputs, the same
MAE restricted to turns, forward-delta MAE separately for left and right turns,
and exact support in fixed windows `1..16`, `17..64`, `65..256`, `257..1024`,
and `1025..4096`. When a branch stops early, also report first/second-half
support without padding or imputation.

At each false-contact SEEK decision, evaluate read-only one-step truth for
`TURN_LEFT`, `TURN_RIGHT`, and `MOVE_FORWARD` under that branch's own angle.
Record truth argmax membership for the causal learned-selected action, truth
and learned score margins, and actual-versus-predicted forward deltas. These
branches cannot change controller, learner, RNG, or environment state.

Also report, separately for each seed, anchor, and angle:

- false-contact SEEK decisions; all four action counts; strict L/R alternation
  run count, lengths, and maximum; next-eligible opposite-turn count/fraction;
- visible side reversal after turns, with pre-action ties and post-action ties
  retained separately;
- beacon-forward before/after/change by turn direction;
- commanded signed/absolute angle, turn count, turn time, and turn actuator
  energy exposure;
- reacquisition, latency, stop/termination/truncation reason, contact events,
  energy and normalized-temperature start/minimum/maximum/final/reacquisition;
- path length, net displacement, visible beacon-forward start/maximum/final/
  change, forward nominal/clipped/stall counts;
- evaluator-only distance, pose/heading, and corresponding rear-contact pair
  errors at start, minimum distance, final, and reacquisition;
- final learner/update/RNG digests and all isolation checks.

Pooled summaries remain separate for every angle and anchor. Nulls and
unavailable anchors are preserved. No outliers are discarded and no universal
pass threshold is used.

## Freeze and provenance

The complete executable module, replay and anchor gates, four conditions,
clone and branch runner, diagnostics, interpretation rules, tests, and writer
are committed before official non-45° D-035A treatment output is executed or
inspected. The clean executable SHA is copied below after that freeze commit
and is also stored in the JSON artifact.

- **protocol_only_freeze_sha:** `fa36c8097364e224be8442f1b302656e52d21db6`
- **implementation_probe_sha:** `fa36c8097364e224be8442f1b302656e52d21db6`
- **artifact_sha256:** to be recorded after official deterministic generation
- **artifact_size_bytes:** to be recorded after official deterministic generation

If a genuine implementation defect invalidates an official run, its executable
SHA, artifact checksum (if any), command, reason, and provenance remain
recorded. Only the defect is fixed; the angles, anchors, horizon, metrics, and
interpretation are not tuned from output, and the official support is rerun
from a new clean executable SHA.

## Interpretation discipline

These are descriptive Development observations from evaluator interventions,
not confirmatory evidence. Finer-angle improvement in oscillation,
reacquisition, prediction, or truth fidelity can support the corresponding
predeclared granularity hypotheses, but cannot authorize changing canonical
action semantics. Behavioural improvement without prediction improvement is
consistent with a geometric/kinematic account; prediction improvement without
reacquisition is not sufficient for docking. If no finer angle helps, the
coarse-quantization hypothesis is insufficient on this support. Any failed
45° identity invalidates treatment interpretation.

**surprised_by:** to be recorded from the frozen official output without
changing the protocol.

**disposition:** `CONTINUING`.
