# D-031R1 — Clean frozen rerun of learned SEEK scaffold displacement

- **id:** D-031R1
- **lane:** Development
- **issue:** [#113](https://github.com/PiFlow/aweform/issues/113)
- **authoritative_base_sha:** `b05d1ee094d999c0acf13126b7374ed11966e3f9`
- **base_tree_sha:** `ceed52790b1fa3726fe2e44a28c6c56f10272258`
- **development_seeds:** `18468..18487` inclusive (20 seeds, ordered)
- **horizon:** `70,000` real transitions per uninterrupted lifetime and arm
- **status:** protocol frozen; substantive output complete
- **disposition:** `CONTINUING`

The machine-readable substantive artifact will be
[`D-031R1-learned-seek-scaffold-displacement-clean-rerun.json`](D-031R1-learned-seek-scaffold-displacement-clean-rerun.json).

## Replacement scope and provenance boundary

D-031R1 is the clean replacement for protocol-invalidated PR #112. PR #112
was not merged and is not a base or accepted result. Its already-reviewed
mechanism was used only as a bounded implementation reference; its artifact,
result record, seed block `18448..18467`, and substantive output are not
imported or pooled here.

This is an ordinary Development-lane probe inside the accepted ADR 0010,
V0.4, and ADR 0015 boundaries. It makes no confirmatory claim and authorizes
no D-032 or successor task.

## Scientific question and frozen protocol

D-031R1 asks whether the unchanged D-030 learned SEEK steering can maintain
resource reacquisition and full-cycle viability when the engineered `1/3`
false-contact SEEK stochastic de-trapping delegation is causally disabled,
and whether any success is attributable to learned steering rather than only
to removing the stochastic scaffold.

Each seed runs three separate matched uninterrupted lifetimes from the same
seed-derived initial state and a fresh zero-initialized D-027 learner:

1. **`LEARNED_WITH_DETRAP`** preserves D-030 exactly: one legacy policy-RNG
   delegation draw per false-contact SEEK decision, delegation probability
   `1/3`, unchanged `StochasticPersistentExplorer` behavior and hazard `1/8`,
   and D-030 learned selection on non-delegated SEEK from the unique maximum
   raw `delta_beacon_forward` prediction over `TURN_LEFT`, `TURN_RIGHT`, and
   `MOVE_FORWARD`.
2. **`LEARNED_NO_DETRAP`** consumes the same one legacy draw, records
   `delegated = false` always, never calls the explorer from false-contact
   SEEK, and applies the unchanged D-030 learned selection rule.
3. **`GREEDY_NO_DETRAP`** has the same zero-delegation/one-draw semantics,
   fixes the false-contact SEEK action to historical greedy
   `seek_beacon_action`, and keeps the unchanged D-027 learner shadow-updated
   once per physically executed transition.

The inherited D-024 finite-body dual-contact geometry, D-020/D-021 physical
semantics, four actions, six visible channels, reward `0.0`, empty organism
`info`, D-027 `4 × 6 × 7 = 168` weights, learning rate `0.5`, executed-action-
only updates, D-030 candidate/score/tie rule, and evaluator-only state remain
unchanged. `WAIT` is excluded from learned steering and learned choice adds
no RNG. `begin_segment()` remains once on SEEK entry with no reseed.

After causal action selection, evaluator-only diagnostics record the three
candidate branch deltas, exact truth argmax, causal/greedy/learned fidelity,
score margin, lifetime quarter, MOVE_FORWARD boundary class, branch
consistency, and isolation checks. They cannot reach action selection,
plasticity, reward, or retained causal state. The artifact retains per-seed
and pooled classifications, SEEK latency and reacquisition energy summaries,
recharge/redeparture/cycle counts, energy/thermal terminations, action and
mode counts, delegation/effective-perturbation counts, learned-vs-greedy
agreement and branch-truth fidelity, boundary and quarter strata, paired
B−A/B−C differences, and the required lost/rescue/all-success/all-failure
seed lists. Raw branch rows are not serialized.

## Freeze-before-output gate

The complete implementation, guards, diagnostics, metrics, interpretation
rules, focused tests, artifact generator, and this protocol record are
committed before any substantive execution or inspection of seeds
`18468..18487`. Only bounded implementation/unit/regression checks are run
before the clean protocol-only freeze commit. The exact 40-character
`implementation_probe_sha` below must be the clean executable SHA used for
the substantive artifact.

- **protocol_only_freeze_sha:** `dc9a0c3d0b15d040b21aa52f133a4d1dacb41fb2`
- **implementation_probe_sha:** `dc9a0c3d0b15d040b21aa52f133a4d1dacb41fb2`
- **artifact_sha256:** `ae5095135f4a9618fb81b815bd201312a7c2bc979eca88499f7b097dc8905b61`
- **artifact_size_bytes:** `2,097,014`

If a genuine implementation or reporting defect invalidates a frozen run,
the invalidated executable SHA, artifact checksum, outputs, and exact defect
reason remain recorded, and all three arms rerun from scratch only from a
fresh clean executable SHA. No protocol or mechanism tuning against output is
permitted.

## Frozen interpretation

Any B failure where matched A succeeds means the stochastic scaffold remains
functionally important at current learned competence. Similar B/C outcomes
do not earn learning-specific displacement credit. If B preserves A-level
competence while C fails, the result is the strongest scaffold-transfer
pattern only when diagnostics are directionally consistent with learned
steering. If both no-detrap arms resolve all matched seeds, learning-specific
benefit additionally requires favorable resolved B−C latency without a
compensating viability loss. Boundary failures remain valid evidence; no
privileged rescue guard or tuning is allowed. Positive D-031R1 output
authorizes no successor automatically.

## Substantive output

The first and second generations from the exact frozen executable were
byte-for-byte identical. Both used only the ordered seed block `18468..18487`
and horizon `70,000`; no pre-freeze substantive execution on that block
occurred. No result from PR #112 was pooled with this run.

Every seed produced the same classification pattern: Arm A
`LEARNED_WITH_DETRAP` was `FULL_CYCLE`, while Arms B and C were
`FAILED_SEEK` with energy depletion. Arm A had `20/20` reacquisitions, full
recharges, and post-recharge redepartures. Its resolved SEEK latency
mean/median/P90/P95/maximum was `943.85 / 715.5 / 2113 / 2221 / 2369`
transitions; reacquisition energy mean/median/minimum was
`0.4839815333485603 / 0.48781953752040863 / 0.45983201265335083`.

Arm-A false-contact SEEK had `18,897` decisions, `6,296` delegated decisions,
and `4,565` effective perturbations. Arm B had `665,928` false-contact SEEK
decisions and exactly `665,928` retained legacy draws; Arm C had `611,811`
of each. B and C both recorded zero delegation and zero false-contact SEEK
explorer calls. B/C branch-enabled versus branch-disabled comparisons were
exact for real summaries, visible trajectories, termination, executed-action
updates, complete 168-weight states, and policy/environment RNG states for
all 20 seeds. Selected branch consistency was exact for all recorded
diagnostic decisions, and the Arm-C extreme-prediction isolation test passed.

The pooled paired B−A and B−C latency and reacquisition-energy contrasts are
unresolved because neither no-detrap arm reacquired. The artifact retains
all per-seed and pooled descriptive metrics, action/mode occupancy, quarter
and MOVE_FORWARD boundary strata, learned/greedy and branch-truth fidelity,
termination counts, and explicit comparison lists: `20` lost seeds, `0`
learned-rescue seeds, `0` all-three-success seeds, and `20` seeds where both
no-detrap arms failed.

This is a Development-lane negative result at the tested competence: the
stochastic de-trapping scaffold remained functionally important on all 20
matched seeds. It does not authorize rescue tuning, a new sensor or learner,
D-032, or any successor.

**surprised_by:** Removing the stochastic delegation caused both no-detrap
arms to lose reacquisition and deplete energy on every fresh seed, while the
unchanged Arm A completed all 20 full cycles. This is preserved as a negative
result, not rescued or retuned.

**disposition:** `CONTINUING`.
