# D-030 — Bounded learned SEEK steering causal influence

- **id:** D-030
- **lane:** Development
- **authoritative_base_sha:** `44db3b7750b8b74eb4930ade9ba4c620d0a36ba6`
- **base_tree_sha:** `6cbad6863b931aec7ac56f8b8094ab2f0ff825c2`
- **development_seeds:** `18428..18447` inclusive (20 seeds)
- **horizon:** `70,000` real transitions per uninterrupted lifetime and arm
- **status:** protocol frozen; substantive output complete
- **disposition:** `CONTINUING`

The machine-readable compact artifact is
[`D-030-bounded-learned-seek-steering.json`](D-030-bounded-learned-seek-steering.json).

## Question and frozen scope

D-030 asks whether the unchanged D-027 one-step visible-consequence learner
can make a first causal contribution to false-contact SEEK steering. Only the
prediction of the next forward-beacon consequence may replace the existing
non-delegated greedy steering choice. D-026 stochastic de-trapping, all
non-SEEK behaviour, D-024/D-020 physics, the six-channel observation, reward,
info, and the D-027 learner remain unchanged.

Each seed runs three separate matched lifetimes from the same seed-derived
initial state:

1. **REFERENCE_NO_INFLUENCE** — unchanged D-026 action; predictions are
   shadow-only.
2. **LEARNED_FORWARD** — on non-delegated false-contact SEEK only, query the
   unchanged predictor for `TURN_LEFT`, `TURN_RIGHT`, and `MOVE_FORWARD`, and
   select the unique maximum of
   `current_beacon_forward + raw delta_beacon_forward prediction`.
3. **PERMUTED_FORWARD** — the same intervention with fixed cyclic relabeling:
   left receives right's score, right receives forward's score, and forward
   receives left's score.

`WAIT` is excluded. Exact floating-point ties fall back to the historical
greedy action. Learned and permuted steering consume no additional RNG. The
ordinary D-026 delegation draw remains exactly one per false-contact SEEK
decision at probability `1/3`, and the explorer hazard remains `1/8`.

At every non-delegated intervention decision, exact isolated branches for the
three candidate actions are executed only after causal action selection.
Branch truth, boundary class, fidelity, margins, and selected-branch
consistency are evaluator-only and cannot reach action selection, the learner,
reward, or retained state. The real transition is followed by exactly one
executed-action-only D-027 update from the actual next visible observation.

## Causal-isolation requirements

The reference arm must match an ordinary D-027-compatible lifetime in its
real trajectory, summaries, complete 168 weights, and update behaviour.
Learned and permuted arms must each exactly match their own branch-disabled
causal replay in real actions, visible trajectory, update digest, complete
weights, termination, and policy/environment RNG state. Prediction queries
must be read-only, and branch evaluation must not mutate environment,
controller, learner, or RNG state. No raw candidate branch rows are retained
in the compact artifact.

## Outcomes and interpretation

The artifact retains per-seed and pooled classification, resolved SEEK
latency, reacquisition-energy, recharge/redeparture/cycle, termination,
action/mode, delegation, steering-disagreement, branch-truth fidelity, score
margin, quarter, and `MOVE_FORWARD` boundary summaries, plus paired latency
contrasts for Arm B − Arm A and Arm B − Arm C.

D-030 is descriptive Development-lane work with no confirmatory p-value or
automatic promotion threshold. Any additional Arm-B energy/thermal
termination, `FAILED_SEEK`, loss of reacquisition/full cycles, or equality of
Arm C's apparent benefit is preserved as a negative result. Fidelity explains
outcomes but is not a reward or control signal. Sparse prior support does not
become exact-revisit knowledge, general counterfactual reasoning, planning, or
a world model. A positive signal could motivate only a fresh review of a
future bounded scaffold-displacement question; it does not authorize D-031.

## Substantive output

The exact ordered seed set produced 20 three-arm lifetimes from one clean
executable SHA. Arm A completed all 20 lifetimes as `FULL_CYCLE`. Arm B also
completed all 20 as `FULL_CYCLE`, with no additional energy/thermal termination
or loss of reacquisition relative to Arm A. Arm C produced `FAILED_SEEK` on all
20 seeds. This is a direct negative result for the fixed-permutation control
and is retained without rescue or retuning.

Arm B and Arm C branch-disabled matched controls passed exact trajectory,
termination, executed-update, complete-weight, policy-RNG, and
environment-RNG comparisons for every seed. Arm A matched the ordinary D-027
reference in real summaries, trajectory, executed-action update digest, and
the complete 168-weight state. All enabled evaluator branch checks, read-only
prediction checks, and selected-branch consistency checks passed.

The artifact retains the complete per-seed and pooled descriptive summaries;
these results are not confirmatory evidence and do not authorize D-031.

## Provenance

The executable probe SHA and regenerated artifact checksum are recorded below
after the clean frozen implementation is committed. The artifact is generated
only with the exact ordered seed block above, after validation through
`validate_exp003_development_seeds` and the D-030 guard. No seed, horizon,
learner, steering criterion, permutation, delegation probability, metric, or
interpretation rule may be changed in response to substantive output.

- **implementation_probe_sha:** `c3a2a0d4c05f99c90adf39cb4e86a75a10c61cca`
- **artifact_sha256:** `9770b027db3091371aebac57d7815f27d847030794d1f44c377baa0a84543f1b`
- **artifact_size_bytes:** `1876381`
