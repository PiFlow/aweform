# D-032 — D-031R1 de-trap function attribution audit

- **id:** D-032
- **lane:** Development
- **issue:** [#115](https://github.com/PiFlow/aweform/issues/115)
- **authoritative_base_sha:** `b25fe711549ba4e98f9759f8358316b94712ca64`
- **base_tree_sha:** `4940d5fcaf82ef498db6fc58d8eadc23f5724d0c`
- **development_seeds:** `18468..18487` inclusive (20 seeds, ordered and reused from D-031R1)
- **horizon:** `70,000` real transitions per uninterrupted lifetime and arm
- **implementation_probe_sha:** `348aa2d4a8dd8684dc3a6506edfcfb752395594c`
- **artifact_sha256:** `6ffe5f1b29ced5b6df5bf206ad69b9293805a8db6bd4cffbb6b29254deef64da`
- **artifact_size_bytes:** `13,664,002`
- **status:** evaluator output complete
- **disposition:** `CONTINUING`

The machine-readable result is
[`D-032-detrap-function-attribution-audit.json`](D-032-detrap-function-attribution-audit.json).

## Question and boundary

D-032 asks which descriptive functions are consistent with the accepted
D-031R1 finding that the stochastic false-contact SEEK de-trapping scaffold
remained necessary. It reuses the direct D-031R1 runner and all three causal
arms exactly:

1. `LEARNED_WITH_DETRAP`
2. `LEARNED_NO_DETRAP`
3. `GREEDY_NO_DETRAP`

The implementation adds evaluator-only capture and post-hoc summaries. It
does not add organism-visible history or recurrence, a sensor, learner
capacity, rescue, retuned delegation, reward or value, planning, curiosity,
physics, or any later-stage mechanism. Reward remains `0.0`; the causal
controller, learner, sensors, actions, ecology, and RNG use remain D-031R1's.
No fresh Development seed was allocated or inspected.

## Provenance and replay gate

The audit was generated from the clean executable SHA above with the accepted
D-031R1 artifact
`D-031R1-learned-seek-scaffold-displacement-clean-rerun.json` as its replay
reference. Every one of the 20 seeds and three arms passed exact comparison
between the instrumented run and a direct D-031R1 run, and between that direct
run and the accepted artifact. The comparison includes outcomes,
termination, real trajectory and update digests, complete final D-027
weights, policy/environment RNG digests, and the D-031R1 identity counters.

At the first Arm-A delegated false-contact SEEK decision, all 20 seeds passed
the mandatory A/B pre-treatment match: real trajectory prefix, six-channel
observation, evaluator body state, mode, learner weights/state digest, policy
RNG state before the delegation draw, environment RNG state, and executed
update-prefix digest. The delegation draw matched exactly; Arm B made no
explorer call. Branch-truth evaluation left its isolated evaluator
environment unchanged for all 20 matched onsets.

## Direct observations

These are descriptive measurements from the generated artifact, not
confirmatory evidence:

- Arm A was `FULL_CYCLE` on `20/20` seeds; Arms B and C were `FAILED_SEEK` on
  `20/20` seeds.
- Arm A recorded `6,296` delegated decisions and `4,565` effective delegated
  perturbations, where effective means the delegated action differed from
  the historical greedy action. Its delegated action totals were
  `MOVE_FORWARD 5,365`, `TURN_LEFT 480`, and `TURN_RIGHT 451`.
- At the matched first-delegation onset, A's explorer action was in the
  exact one-step truth argmax on `7/20` seeds, B's learned action was in the
  argmax on `14/20`, and the delegation changed the action on `17/20`.
  A/B candidate predictions were exactly equal on `20/20` onsets.
- After matched treatment onset, A moved materially farther and reached
  `20/20` reacquisitions by the `4096`-step window, while B reached `0/20`.
- Whole-SEEK boundary counts were A: `9` clipped, `6` stalled, `5,637`
  nominal; B: `0`, `0`, `163`; C: `0`, `0`, `123,856`. Thus B had zero
  clipped/stalled forward events while its failure was dominated by extreme
  left/right alternation: `35,969` alternation runs, with a longest run of
  `33,297`.
- Maximal left/right alternation runs were A: `1,926` with longest length
  `26`; C: `0`. This is a behavioural description, not proof that symmetry
  breaking is the sole function of delegation.

The pooled first-onset window summaries below report means across the 20
matched seeds. Distance change is final minus onset evaluator distance to the
station; negative values are closer. A window stops at SEEK reacquisition or
the end of the relevant SEEK episode.

| window | A path length | B path length | A distance change | B distance change | A reacquisitions | B reacquisitions |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.04384 | 0.00750 | -0.02392 | -0.00729 | 0 | 0 |
| 4 | 0.11987 | 0.04250 | -0.07868 | -0.04102 | 0 | 0 |
| 16 | 0.50598 | 0.31000 | -0.39719 | -0.29050 | 0 | 0 |
| 64 | 1.18348 | 0.39500 | -0.43849 | -0.37187 | 1 | 0 |
| 256 | 3.70598 | 0.39500 | -0.46585 | -0.37187 | 4 | 0 |
| 1024 | 10.07098 | 0.39750 | -0.47669 | -0.37435 | 14 | 0 |
| 4096 | 14.09848 | 0.39750 | -0.47611 | -0.37435 | 20 | 0 |

The pooled existing D-031 one-step fidelity summaries, with Arm C's learned
choice treated as evaluator-only shadow information, were:

- A non-delegated SEEK: causal `0.8792`, greedy `0.7981`, learned `0.8792`.
- B non-delegated SEEK: causal `0.8042`, greedy `0.5439`, learned `0.8042`.
- C non-delegated SEEK: causal/greedy `0.7978`, shadow learned `0.9610`.

The artifact retains the delegated-event timing per seed and the complete
effective-versus-ineffective fixed-window family pooled across Arm-A events
at windows `1, 4, 16, 64, 256, 1024, 4096`, including event counts,
motion/distance/beacon/heading/energy summaries, action and boundary counts,
and reacquisition counts. These comparisons are explicitly state-confounded
and descriptive, not matched causal effects.

## Interpretation and limitations

Observed: the unchanged stochastic scaffold is associated with the only arm
that completed the accepted 20-seed full-cycle support, while both no-detrap
arms failed SEEK on every reused seed. B had no clipped/stalled forward
events but exhibited the extreme left/right alternation described above. A's
matched-onset continuation moved farther and reacquired on all 20 seeds by
the 4096-step window, while B reacquired on none. At the exact matched onset,
B was one-step truth-optimal on `14/20` seeds versus A on `7/20`.

Supported inference, without a unique attribution: temporal persistence /
sequence generation and symmetry-breaking/non-myopic diversification are
better supported by this audit than a simple boundary-stall concentration
account or a claim that the explorer wins mainly by choosing the immediately
best one-step action. The absence of B boundary stalls argues against the
first account, while B's stronger exact-onset one-step truth membership argues
against the second. Prediction/selection deficiency remains partly unresolved
because later SEEK fidelity is imperfect. The separate contributions of
temporal persistence, symmetry breaking, non-myopic benefit, and experience
diversification also remain unresolved. Event-centred
effective-versus-ineffective comparisons are explicitly state-confounded and
must not be read as randomized attribution of effectiveness.

This is a Development-lane descriptive result. It makes no confirmatory
claim, does not change any durable boundary, and authorizes no rescue, new
learner, new sensor, EXP execution, D-033, or successor task. An independent
GPT-5.6 Sol review of the exact current candidate remains required before
Flow considers merge; no independent review is claimed here.

**surprised_by:** The first matched branch truth was often different from the
Arm-A explorer action (`7/20` truth membership), while the learned Arm-B
choice was in truth on `14/20`; at the same time, the no-detrap arm still
failed on every reused seed. This keeps prediction/selection deficiency and
longer-horizon or experience-diversification explanations open rather than
turning the one-step result into a forced causal conclusion.

**disposition:** `CONTINUING`.
