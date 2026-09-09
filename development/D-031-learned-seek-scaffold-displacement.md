# D-031 — Learned SEEK scaffold displacement

- **id:** D-031
- **lane:** Development
- **authoritative_base_sha:** `b05d1ee094d999c0acf13126b7374ed11966e3f9`
- **base_tree_sha:** `ceed52790b1fa3726fe2e44a28c6c56f10272258`
- **development_seeds:** `18448..18467` inclusive (20 seeds, ordered)
- **horizon:** `70,000` real transitions per uninterrupted lifetime and arm
- **status:** protocol frozen; substantive output complete
- **disposition:** `CONTINUING`
- **implementation_probe_sha:** `676499fe59d1ed45b4c2a414d4f7db207ff86ced`
- **artifact_sha256:** `30dfa4e97909da929bf6450f8a95c7e9642f4c5196b356e28f667ee14f4179ce`
- **artifact_size_bytes:** `2097702`

The machine-readable substantive artifact will be
[`D-031-learned-seek-scaffold-displacement.json`](D-031-learned-seek-scaffold-displacement.json).

## Scientific question and frozen scope

D-031 asks whether the merged D-030 learned SEEK steering can maintain
resource reacquisition and full-cycle viability after the inherited stochastic
false-contact SEEK de-trapping delegation is disabled, and whether any
survival of competence is specifically attributable to learned steering rather
than only to removing that scaffold.

This is a narrow scaffold-displacement probe. It adds no sensor, action,
reward, learner capacity, retained state, physical rule, or safety permission.
Historical D-024 through D-030 source, artifacts, results, and interpretations
remain unchanged.

## Three-arm protocol

Each seed runs three separate matched uninterrupted lifetimes from the same
seed-derived initial environment/policy state and a fresh zero-initialized
D-027 learner.

1. **`LEARNED_WITH_DETRAP`** reproduces merged D-030 learned forward steering:
   false-contact SEEK delegation is exactly `1/3`, the existing explorer has
   hazard `1/8`, and non-delegated SEEK selects the unique maximum raw
   `delta_beacon_forward` prediction among `TURN_LEFT`, `TURN_RIGHT`, and
   `MOVE_FORWARD`. Exact ties fall back to historical `seek_beacon_action`.

2. **`LEARNED_NO_DETRAP`** keeps the same learned selection rule but sets only
   the false-contact SEEK delegation probability to exactly `0.0`. The
   inherited arbitration path still consumes exactly one ordinary policy-RNG
   draw per decision and records it; `StochasticPersistentExplorer.act()` is
   not called from false-contact SEEK. `begin_segment()` and all AWAY and
   non-SEEK behavior remain inherited and unchanged.

3. **`GREEDY_NO_DETRAP`** uses the same zero-delegation and one-draw semantics
   as Arm B, but fixes every false-contact SEEK action to historical greedy
   `seek_beacon_action`. The unchanged 168-weight D-027 learner remains
   present and updates once after every real transition as a shadow learner.
   Candidate predictions and branch truth are evaluator-only in this arm.

Across all arms, D-024 finite-body dual-contact geometry, D-020/D-021 physics
and controller semantics, four actions, six visible channels, reward `0.0`,
organism-facing `info == {}`, D-027 features/outputs/168 weights, learning
rate `0.5`, executed-action-only update, and zero additional RNG from learned
selection are frozen.

## Frozen causal and evaluator order

The current visible observation is passed through inherited D-026 mode logic,
which computes historical greedy action and consumes the one legacy arbitration
draw on every false-contact SEEK decision. Arm A/B may then use only the
unchanged D-027 raw forward-delta prediction for causal selection; Arm C has
already fixed its greedy action. After causal selection, the runner may query
the three candidate predictions and execute isolated D-029 steering branches.
Those branches, exact truth argmax, boundary class, quarter, pose, mode,
termination, delegation labels, and all isolation digests are evaluator-only.
The real transition is then followed by the actual next six-channel
observation and exactly one executed-action D-027 update.

The artifact retains compact per-seed and pooled summaries for classifications,
reacquisition latency and energy, recharge/redeparture/cycle counts,
energy/thermal terminations, actions and modes, delegation and effective
perturbations, learned/greedy agreement and branch-truth fidelity, boundary
and quarter strata, paired B−A and B−C contrasts, lost seeds, learned-rescue
seeds, all-three-success seeds, and all-no-de-trap-fail seeds. Raw branch rows
are not serialized.

## Isolation and interpretation rules

Arm A is regression-checked against the merged D-030 learned arm on a
historical D-030 seed, including real summary, trajectory, update digest,
complete weights, and both RNG digests. Arms B/C diagnostics-enabled runs are
matched against branch-disabled runs for exact real actions/trajectory,
termination, update digest, complete weights, and policy/environment RNG.
Arm C also has an adversarial extreme-prediction isolation test. The retained
counter and checks demonstrate zero false-contact SEEK delegation and no SEEK
explorer call in Arms B/C while preserving AWAY explorer behavior.

Viability and reacquisition are interpreted first. Any B failure where matched
A succeeds is retained as evidence that the scaffold remains functionally
important. Similar B/C outcomes do not credit learning with displacement. A
stronger developmental pattern is B preserving A competence while C fails,
with branch-truth diagnostics directionally consistent with learned steering.
No p-value, scalar reward, universal graduation threshold, exact-revisit,
planning, world-model, intelligence, consciousness, emotion, subjective
experience, genuine-life, metabolism, or hardware-autonomy claim is authorized.
No positive result authorizes D-032 or any successor.

## Substantive output

The corrected clean execution used the exact ordered seeds `18448..18467`,
horizon `70,000`, and five lifetimes per seed: the three diagnostics-enabled
arms plus matched branch-disabled runs for Arms B/C. The final artifact was
regenerated a second time from the same executable SHA and compared byte for
byte; both copies have SHA-256
`30dfa4e97909da929bf6450f8a95c7e9642f4c5196b356e28f667ee14f4179ce` and size
`2,097,702` bytes.

Arm A completed `20/20 FULL_CYCLE` lifetimes with `20` reacquisitions, `20`
full recharges, and `20` post-recharge redepartures. Its resolved SEEK latency
mean/median/P90/P95/maximum was `1473.8 / 954.5 / 3785 / 4826 / 5477`
transitions. Arm-A false-contact SEEK delegation was `9,768` of `29,496`
decisions, with `7,130` effective perturbations.

Arm B produced `20/20 FAILED_SEEK` outcomes, zero reacquisitions, and 20
energy-depletion terminations. Arm C produced the same `20/20 FAILED_SEEK`,
zero reacquisition, and 20 energy-depletion pattern. Arms B/C recorded zero
false-contact SEEK delegation, exactly one retained legacy arbitration draw per
false-contact SEEK decision (`665,926` B decisions/draws and `612,074` C
decisions/draws pooled), and zero false-contact SEEK explorer calls. Their
branch-enabled versus branch-disabled real summaries, visible trajectories,
termination, executed-update digests, complete 168-weight states, and both
RNG states were exactly equal for every seed. Arm C's adversarial extreme
prediction isolation also preserved the real trajectory and update state.

The pooled paired B−A and B−C latency and reacquisition-energy contrasts are
unresolved because neither no-detrap arm reacquired on any seed. The artifact
retains all null paired fields, all per-seed outcomes, branch-truth and
learned/greedy diagnostics, boundary/quarter strata, and explicit counts and
lists: `20` lost seeds, `0` learned-rescue seeds, `0` all-three-success seeds,
and `20` seeds where both no-detrap arms failed.

This is a direct Development-lane negative result for scaffold displacement at
the current competence: the retained stochastic de-trapping scaffold remained
functionally important on every matched seed. It does not justify a confidence
gate, new sensor, larger learner, tuned delegation, rescue heuristic, or
successor task. It does not establish planning, a world model, general
counterfactual reasoning, intelligence, consciousness, emotion, subjective
experience, genuine life, metabolism, or hardware autonomy.

## Provenance and freeze

The exact ordered seed block is validated through
`validate_exp003_development_seeds` and the exact D-031 guard before execution.
The protocol-only executable freeze is committed before substantive output;
the artifact records that exact `implementation_probe_sha`. If a genuine
implementation or reporting defect invalidates a run, its executable SHA,
artifact checksum, and reason remain recorded and all three arms rerun from
scratch after the correction. No tuning against substantive output is allowed.

### Invalidated pre-freeze smoke execution

Before this protocol-only freeze commit, full-horizon D-031 executions were
accidentally included in implementation smoke/focused-test runs while checking
that the SEEK path was exercised. They are invalid under the frozen-protocol
rule. No artifact checksum was generated, no substantive value from those
executions is accepted or used, and no clean executable SHA exists for them;
the repository was still at the authorized base with uncommitted D-031 changes.
The clean freeze SHA below supersedes those invalid smoke executions, and the
authorized three-arm block is rerun from scratch from that SHA.

### Invalidated clean execution

The first clean substantive execution was produced from executable SHA
`cfe79df70e75d568288c015e37d51ec83349e619`. Its artifact SHA-256 was
`1ed28106fddeca06e542ec20ef70c03d51fc02c0ea30c136e5b49b3edcf894d4` and its
size was `1,850,885` bytes. That artifact is invalidated before acceptance
because its pooled compact report omitted the required effective-perturbation
and delegated-action Arm-A aggregates, explicit comparison counts, and
boundary-stratified fidelity fields. The protocol, implementation mechanism,
seeds, horizon, and measured outcomes were not tuned or changed in response;
the reporting-only correction is followed by a complete three-arm rerun from
scratch.

## Validation and disposition

Focused D-031 tests pass (`6 passed`); the full suite passes (`915 passed`,
`7 warnings`), Ruff is clean, strict mypy is clean, compileall is clean, and
`git diff --check` is clean. The canonical reservation validator and exact
D-031 seed guard accepted the ordered block. The deterministic second artifact
regeneration was byte-for-byte identical. Exact-current-HEAD GitHub CI/checks
remain required before handoff.

**surprised_by:** Removing the stochastic delegation was not enough for either
no-detrap arm: both lost resource reacquisition and depleted energy on all 20
fresh seeds, while the unchanged D-030 learned-with-de-trapping comparator
completed every lifetime. This is retained as a negative result, not rescued.

**disposition:** `CONTINUING`. The result is descriptive Development-lane
context only and cannot authorize D-032.
