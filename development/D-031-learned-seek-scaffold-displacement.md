# D-031 — Learned SEEK scaffold displacement

- **id:** D-031
- **lane:** Development
- **authoritative_base_sha:** `b05d1ee094d999c0acf13126b7374ed11966e3f9`
- **base_tree_sha:** `ceed52790b1fa3726fe2e44a28c6c56f10272258`
- **development_seeds:** `18448..18467` inclusive (20 seeds, ordered)
- **horizon:** `70,000` real transitions per uninterrupted lifetime and arm
- **status:** protocol frozen; substantive execution pending
- **disposition:** `CONTINUING`

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

**surprised_by:** Substantive output is pending at protocol freeze; no result
or surprise is asserted.

**disposition:** `CONTINUING` pending the authorized descriptive run. A later
result will preserve null and negative outcomes and cannot authorize D-032.
