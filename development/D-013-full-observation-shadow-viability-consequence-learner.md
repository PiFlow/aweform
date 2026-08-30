# D-013 — Full-observation shadow viability consequence learner

- **id:** D-013
- **date:** 2026-08-30
- **authoritative_base_sha:** \`539d91dfaf6b881b398d06c4637eb1c91f7a2174\`
- **prior_executed_commit_sha:** \`f208b91d372307ea8e647e67ba5480c06b37a480\`
- **accepted_executable_commit_sha:** \`b41c4424ff3b6bb257cbd3a1b9fa8d5daf4a32cf\`
- **accepted_executed_commit_sha:** \`b41c4424ff3b6bb257cbd3a1b9fa8d5daf4a32cf\`
- **development_seeds:** \`18344, 18345, 18346\`
- **horizon:** \`1000\` transitions per lifetime
- **disposition:** \`CONTINUING\`

## Scientific question

Can a very small action-conditioned learner acquire useful one-step
predictions of visible energy, thermal, and charging-contact consequences
across the complete autonomous D-011 regulation loop when it receives the
complete current D-011 observation plus its own executed action, while the
unchanged D-011 controller retains all behavioural control?

This is development-only descriptive work. The learner is shadow-only. It is
not model-guided control, counterfactual action selection, confirmatory
evidence, or authorization for a larger/world-model architecture.

## Provenance and execution

The prior record incorrectly named the nonexistent SHA
\`f208b916b4551d405d41e738f82d9609d3c40af6\`. The actual prior executable
commit was \`f208b91d372307ea8e647e67ba5480c06b37a480\`. Its Git parent was PR
#65 HEAD \`0d7ce425f9fac937ddc0891cde6bea0d29060a35\`, while the authoritative
base was \`539d91dfaf6b881b398d06c4637eb1c91f7a2174\`. Those two parent trees
were identical at \`0d69456d72de65a11e85db7faec876aa2df82526\`; history was not
rewritten.

The prior artifact is invalidated only because of reporting/provenance
defects: its executed SHA did not exist, its SEEK summary counted a final
horizon-censored SEEK as failure, and its geometry field used overly broad
terminology. The learner, controller, ecology, thresholds, features, targets,
LMS rule, seeds, horizon, action selection, prediction metrics, and scientific
hypothesis were not changed. The repair executable commit was made only after
the reporting fix and focused regression test passed. The accepted rerun was
then executed from that clean commit exactly once using the three declared
seeds and horizon above; its exact SHA is recorded in this record and the JSON
artifact:

[D-013-full-observation-shadow-viability-consequence-learner.json](D-013-full-observation-shadow-viability-consequence-learner.json)

The prior execution remains preserved by the prior record commit
\`68c29ec58cb6a776c22cf8603a5e903d03672036\` and Git history; it is not hidden
or rewritten. Before the repair executable commit, focused tests also
exercised shorter and one-seed diagnostic runs. Those produced no artifact and
were not used as the accepted substantive result.

## Programmed scaffold

D-013 reuses the actual D-011 mechanism without copying its action logic:

- unchanged \`D011Controller\`, including \`CHARGE\`, \`DEPART\`, \`AWAY\`, and \`SEEK\`;
- unchanged \`HOT_DEPART_THRESHOLD\`, B50 low-energy SEEK threshold,
  \`StochasticPersistentExplorer\`, policy RNG semantics, action costs, energy
  and thermal dynamics, contact radius, and horizon semantics;
- unchanged post-contact setup and physical charging-contact definition;
- existing \`d011._controller_observation\` and
  \`d011._prepare_post_contact_setup\` helpers;
- one continuous lifetime per seed, with no reset or reseeding within a
  lifetime.

The D-011 controller alone selected every physical action. The learner's
predictions were never consulted by the controller, explorer, policy RNG,
environment, viability logic, termination logic, or plasticity schedule.
No action was forced for coverage. Reward remained exactly \`0.0\` and
\`info\` remained exactly \`{}\` on every transition.

## Organism-visible and learned state

The learner received a typed \`D011Observation\` and the organism's own
executed \`Action\`. Its current feature vector was exactly:

\`\`\`text
x = [
    1.0,
    energy,
    beacon.left,
    beacon.forward,
    beacon.right,
    float(charging_contact),
    thermal,
]
\`\`\`

It predicted only the physically executed action's one-step visible deltas:

\`\`\`text
delta_energy           = next.energy - current.energy
delta_thermal          = next.thermal - current.thermal
delta_charging_contact = float(next.charging_contact)
                         - float(current.charging_contact)
\`\`\`

There were independent linear weight vectors for the four actions
\`WAIT\`, \`TURN_LEFT\`, \`TURN_RIGHT\`, and \`MOVE_FORWARD\`, and the three outputs
above. The complete plastic state was exactly
\`4 × 3 × 7 = 84\` scalar weights, initialized to zero. The stable state order
was action, output, feature. The learner had no optimizer state, RNG, hidden
units, recurrent/history state, eligibility traces, adaptive learning state,
replay/experience buffer, or other retained plastic object. A deliberate
new-lifetime reset sets all 84 weights to zero; the runner did not reset
within a lifetime.

For each output, the normalized LMS update used learning rate \`0.5\`:

\`\`\`text
prediction = dot(weights[action], x)
error = observed_delta - prediction
normalizer = dot(x, x)
weights_new = weights_old + 0.5 * error * x / normalizer
\`\`\`

Only the three output vectors for the physically executed action updated.
Predictions were formed before \`environment.step(action)\`, scored against the
typed next observation after the transition, and then used for the visible
transition update. Inherited evaluator-side post-contact setup / seeded
geometry was established before the lifetime loop and none of it entered the
learner. Per-transition evaluator telemetry used for summaries was read only
after the learner update. No per-transition geometry trajectory was collected
for D-013.

Controller mode, policy RNG state, evaluator coordinates, true distance,
heading, station position, seed identity, transition index, horizon, reward,
\`info\`, termination labels, success/failure labels, and future observations
were absent from learner inputs and learned state.

## Direct observations

**Source:** exact JSON artifact generated from the accepted repaired executable
commit and rerun.

All three lifetimes reached 1000 transitions and ended by horizon truncation;
none terminated for energy or thermal failure. Maximum thermal was
\`0.6299999952\` for every seed. The minimum normalized energies were
\`0.0480000004\`, \`0.1560000032\`, and \`0.1599999964\`; final normalized energies
were \`0.5419999957\`, \`0.5239999890\`, and \`0.3319999874\` for seeds 18344,
18345, and 18346 respectively. Completed regulation cycles were 11 on each
seed. Low-energy SEEK entries/reacquisitions were \`11/11\`, \`11/11\`, and
\`12/11\`; seed 18346 therefore ended with one horizon-censored final SEEK
episode.

The action counts were:

| Seed | MOVE_FORWARD | TURN_LEFT | TURN_RIGHT | WAIT |
|---:|---:|---:|---:|---:|
| 18344 | 388 | 64 | 83 | 465 |
| 18345 | 402 | 68 | 63 | 467 |
| 18346 | 417 | 69 | 55 | 459 |

All four actions were visited in every lifetime. Contact/context support was
uneven: \`WAIT\` occurred only with current contact true (\`465\`, \`467\`, \`459\`),
\`TURN_LEFT\` and \`TURN_RIGHT\` occurred only with current contact false, and
\`MOVE_FORWARD\` had 40, 43, and 45 current-contact-true samples. The exact
per-action six-channel ranges, contact target counts, context cells, Q1–Q4
metrics, checkpoints, and final 84-weight snapshots are preserved in the
artifact. Zero-observation context cells are marked \`untested\`; no performance
value is fabricated for them. The repaired SEEK semantics report zero
demonstrated failed SEEK episodes and one horizon-censored SEEK episode for
seed 18346.

Pooled contact-delta target counts were \`33\` for \`+1\`, \`35\` for \`-1\`, and
\`2932\` for \`0\`, out of 3000 transitions. Thus contact-change learning was
supported by relatively few non-zero examples.

## Prediction performance

**Source:** exact artifact; all values are evaluator-only pre-update MAE
summaries. The zero-change comparator predicts delta \`0.0\` on every
transition. It is not reward and did not affect plasticity or behaviour.

| Seed | Target | Overall learned / zero-change MAE | Q4 learned / zero-change MAE |
|---:|---|---:|---:|
| 18344 | delta_energy | \`0.00357679 / 0.01749000\` | \`0.00349831 / 0.01714400\` |
| 18344 | delta_thermal | \`0.00121837 / 0.01000000\` | \`0.00125383 / 0.01000000\` |
| 18344 | delta_charging_contact | \`0.03982432 / 0.02200000\` | \`0.05138185 / 0.02400000\` |
| 18345 | delta_energy | \`0.00373027 / 0.01756800\` | \`0.00388511 / 0.01808000\` |
| 18345 | delta_thermal | \`0.00126556 / 0.01000000\` | \`0.00128498 / 0.01000000\` |
| 18345 | delta_charging_contact | \`0.04167267 / 0.02300000\` | \`0.05189084 / 0.02400000\` |
| 18346 | delta_energy | \`0.00373507 / 0.01772800\` | \`0.00310993 / 0.01601600\` |
| 18346 | delta_thermal | \`0.00126161 / 0.01000000\` | \`0.00116539 / 0.01000000\` |
| 18346 | delta_charging_contact | \`0.04274977 / 0.02300000\` | \`0.04653518 / 0.02000000\` |

Energy and thermal learned MAE were below the zero-change comparator overall
and in Q4 for every seed. Charging-contact learned MAE was above the
zero-change comparator overall and in Q4 for every seed. This is a mixed
descriptive result, not a binary benchmark or a pass threshold.

## Behavioural shadow isolation

Using the unchanged internal \`d011._run_seed\` as the reference on each D-013
seed and horizon, D-013 matched exactly on:

- transitions and horizon truncation;
- action counts;
- D-011 mode occupancy and mode-entry counts;
- minimum/final normalized energy and minimum/maximum thermal summaries;
- energy/thermal termination flags;
- low-energy SEEK entries and physical reacquisitions;
- completed autonomous regulation cycles.

This establishes shadow isolation for the tested seeds/horizon. It does not
show that the learner is necessary for viability; the unchanged controller
still generated the trajectory.

## Direct observation versus inference

**Direct observation:** Supplying the complete current D-011 sensory context to
the small linear learner produced lower prequential energy and thermal errors
than the zero-change comparator on all three seeds, while contact-delta error
was consistently worse than the comparator. The complete D-011 scaffold
continued to produce the same behaviour as unchanged D-011.

**Conservative inference:** The richer legitimate current observation appears
useful for these simple on-policy energy and thermal delta fits in this fixed
deterministic ecology. It was not sufficient for useful contact-delta fitting
under this run's support and linear online update. The contact result may
reflect sparse non-zero contact transitions, action/context imbalance, hidden
state or consequence aliasing, representation limits, or online-LMS
interference. The run does not distinguish those causes.

No counterfactual competence, general world model, learned navigation,
planning, action-selection benefit, intelligence, consciousness, emotion,
subjective experience, genuine life, or biological metabolism is inferred.

## Limitations

- One three-seed development probe and one 1000-transition horizon.
- All support was on-policy; the contact-true \`TURN_LEFT\`/\`TURN_RIGHT\` and
  contact-false \`WAIT\` context cells were unvisited on every seed.
- Non-zero contact deltas were rare relative to unchanged contact transitions.
- The linear learner had no history, so this result does not test whether
  closure-valid retained history would reduce residual aliasing.
- The fixed D-011 controller and deterministic ecology do not test noise,
  delayed sensing, another geometry, another ecology, or model-guided use.
- A singleton or unvisited support cell is not evidence of stable or accurate
  prediction.

## Surprised by

The complete current observation improved energy and thermal prediction
reliably, but did not improve charging-contact prediction even though all four
actions were visited. The contact target was dominated by zero changes and
the non-zero contact support was small, making the negative contact result a
useful warning against treating full current observation as automatic causal
sufficiency. The D-011 policy also visited \`TURN_RIGHT\` in this seed block,
unlike the narrower D-008/D-009 development trajectories, while still leaving
several action/context cells untested.

## Disposition

**CONTINUING.** Retain the mixed result and the complete artifact. D-013
supports a narrow descriptive conclusion that the smallest full-current-
observation linear learner can fit energy and thermal consequences better than
zero-change on this fixed D-011 trajectory, but not charging-contact
consequences under the observed support. It does not authorize model-guided
action selection, counterfactual queries, a larger learner, recurrence,
history, or a world model. Any next developmental step should first inspect
support and residual aliasing/omitted state before increasing capacity.
