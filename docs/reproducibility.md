# Reproducibility and Seed Policy

Aweform's experiments are simple enough that reproducibility should be treated as a hard requirement rather than a later improvement.

## Reproducibility target

For the same code revision, configuration, software environment, and master seed, a deterministic run should reproduce the same canonical trajectory and summary outputs on the same supported platform, subject only to explicitly documented numerical tolerances.

If a component is intentionally stochastic, its randomness must be owned by an explicit seeded random-number generator rather than implicit global state.

## Two seed roles at project level

Aweform distinguishes development from evidence.

### Development seeds

Development/debug seeds may be reused freely across `D-NNN` work. Reuse gives them no evidentiary status and no new reservation ceremony is required for each D-record.

A development seed must still be checked against every existing formal calibration/acceptance/confirmatory reservation. A seed already reserved for an EXP experiment may not be executed merely because the new run is labelled development.

A development audit may deliberately split legal development support into **reused** and **fresh holdout** blocks. That can strengthen hypothesis discrimination without turning the result into formal evidence. When this pattern is used:

- freeze the protocol before inspecting the fresh holdout;
- keep reused and holdout results separate in artifacts and interpretation;
- do not tune features, thresholds, anchors, horizons, or interpretation rules on the holdout;
- preserve support/null counts rather than converting missing cases to convenient values.

### Evidence seeds

An evidence experiment that involves parameter or architecture selection followed by a scientific claim must separate inspectable development/model-selection material from untouched acceptance/confirmatory seeds. Formal reservations are created when the evidence protocol is frozen, not speculatively for every development iteration.

Existing historical reservations remain unchanged. In particular, EXP-002 confirmatory seeds `50001–51000` remain untouched.

Comparator conditions in evidence experiments must be evaluated on matched acceptance seeds unless the frozen protocol explicitly justifies a different design.

Do not quietly replace acceptance seeds because they produce inconvenient outcomes. If an acceptance set or its generation rule changes after results are inspected, create a new experiment revision and report the earlier outcome.

## Continuous lifetime and harness segmentation

Within a declared organism lifetime, harness horizons, logging windows, visualization windows, storage chunks, and future checkpoint boundaries are engineering or measurement boundaries only. They are not organism events.

A segmentation boundary must not reset or reseed any causally relevant organism state, including learned/plastic state, transient controller state, circuit/filter/history state, policy or explorer phase, or organism-owned RNG state. It must not expose a segment identifier, artificial fresh-start signal, wall-clock value, or boundary-derived counter to the organism.

If checkpoint/resume or segmented-lifetime execution is implemented later, it must preserve the complete causal state needed for continuation. Deterministic implementations should add an equivalence test showing that segmented and uninterrupted execution produce the same canonical trajectory under the same supported stack and seed.

A deliberate developmental-stage reset is different: under the current V0.3 convention it is an explicit lifecycle/new-lifetime event and must be recorded as such, never disguised as harness segmentation.

## Run manifest and executable provenance

Every confirmatory run should record enough information to reconstruct what was executed, including:

- experiment identifier and revision;
- exact Git commit SHA;
- configuration values;
- master/environment seed;
- comparator condition;
- software/runtime versions;
- start time and relevant platform information;
- output schema version if one exists.

Development records remain lighter, but should retain the exact executed SHA and development seeds used so the work can be reconstructed later.

For high-leverage D-lane audits, distinguish explicitly between:

- **authorized base SHA** — the repository state from which the task was authorized;
- **clean executable/protocol SHA** — the exact committed code/schema that generated the result;
- **record-only/final PR SHA** — a later commit that may add provenance text without changing the executable protocol;
- **artifact SHA-256 and byte size** — enough to identify the exact generated result;
- **invalidated executable/artifact provenance** — preserved separately when a defect is found.

Do not cite a later record-only commit as if it were the executable tree that produced an artifact.

## Privileged evaluator state

The simulator may hold hidden ground truth needed for physics, resource generation, metrics, debugging, synthetic evaluator-only sensors, or matched counterfactual branches. That state must remain separate from the observation passed to the controller and from any plastic update.

Evaluator access to hidden position, heading, resource coordinates, docking geometry, ground-truth fields, diagnostic counters, future branch outcomes, or treatment labels does not imply organism access.

An evaluator-only synthetic sensor or diagnostic must pass a causal-inertness check when the scientific claim depends on it: canonical execution with diagnostics enabled versus disabled should remain identical on the declared causal comparable fields.

## Matched causal branches

Evaluator-only counterfactual branches are increasingly important in D-series work. When a result depends on cloning a causal state, the clone must preserve every state component relevant to future evolution, including as applicable:

- physical/environment state;
- current organism observation;
- controller mode and transient state;
- explorer/policy state;
- complete learned/plastic state;
- policy and environment RNG state;
- transition index and remaining horizon;
- any causal update-prefix state required by the learner.

Useful negative controls include:

- **OFF-vs-OFF clone identity:** two independently cloned untreated continuations should match on deterministic comparable fields;
- **branch-order invariance:** executing ON before OFF versus OFF before ON must not change either result;
- **source non-mutation:** creating or executing a branch must not mutate the anchor/source state;
- **diagnostic non-feedback:** evaluator calculations and branch outcomes must not affect the canonical controller, learner, RNG, reward, `info`, anchor selection, or pre-action feature construction.

If a branch protocol stops on an event such as reacquisition, termination, or truncation, the implementation and artifact must preserve that stopping rule exactly rather than continuing and summarizing post-event behavior as if it belonged to the frozen horizon.

## Independent validity checks and common-mode risk

Passing tests written against the same high-level helper stack that produced a scientific result does not by itself rule out a correlated implementation error.

When a conclusion is unusually load-bearing, when several successor audits reuse the same helpers, or when a later stage explicitly questions test validity, build an independent verification path from lower-level accepted components where practical. Examples include independently reconstructing:

- anchor eligibility and exact transition identity;
- canonical replay/trajectory digests;
- branch cloning and treatment semantics;
- primary causal targets;
- null/availability rules.

The independent path may reuse immutable low-level simulator/controller primitives; the point is to avoid manufacturing both the original result and its validation through the same high-level analysis helper.

D-040 is the current example of this discipline.

## Deterministic artifacts

When a D-stage or EXP-stage commits generated artifacts, prefer compact deterministic schemas over raw duplication. A useful artifact should retain enough per-seed/per-condition support, digests, null reasons, provenance, and summaries for independent audit without embedding enormous raw transition streams unless those streams are scientifically necessary.

Where deterministic regeneration is claimed:

1. generate from a clean executable SHA;
2. regenerate independently from that same SHA and command;
3. compare hashes/size and, when practical, byte identity;
4. record the regeneration result durably.

If a supposedly compact artifact becomes too large or embeds one support set inside another, treat that as an artifact-contract problem rather than merely a storage inconvenience.

## Validation claims and review evidence

A validation claim attached to an exact Git SHA requires that exact committed tree, from a clean checkout, to compile and import successfully. Results produced from a dirty working tree must disclose the dirty state and patch; they must not cite the clean commit as if it contained the source that was executed.

Reviewer language must distinguish “I inspected the tests” from “I executed the tests.” An exact-current-HEAD CI result is not transferable to a later commit unless the later commit is explicitly proven to be record-only for the relevant executable claim.

## Failed, invalidated, and exploratory runs

Exploratory and failed runs are part of the research record. They may be excluded from a final confirmatory summary only according to rules defined before the confirmatory run, such as a genuine execution failure.

Do not delete or relabel scientifically valid negative results merely because they conflict with expectations.

When a genuine software/protocol defect invalidates a run, preserve enough provenance to prevent accidental reuse:

- executable SHA;
- artifact hash and size when available;
- command/support role;
- exact defect/reason for invalidation;
- corrected executable SHA and rerun relationship.

Invalidated outputs must not be pooled into accepted interpretation.

## Versioning evidence changes

A change to any of the following after confirmatory results are viewed should normally create a new experiment revision:

- environment dynamics;
- observation or action contract;
- energy or other viability dynamics;
- comparator-controller logic;
- interoception or learning ablation method;
- primary outcome definition;
- acceptance seed set;
- interpretation/pass criteria.

Implementation bug fixes may preserve an experiment revision only when the previous results are explicitly invalidated and rerun from scratch.
