# Reproducibility and Seed Policy

Aweform's early experiments are simple enough that reproducibility should be treated as a hard requirement rather than a later improvement.

## Reproducibility target

For the same code revision, configuration, software environment, and master seed, a deterministic run should reproduce the same canonical trajectory and summary outputs on the same supported platform, subject only to explicitly documented numerical tolerances.

If a component is intentionally stochastic, its randomness must be owned by an explicit seeded random-number generator rather than implicit global state.

## Two seed roles at project level

Aweform now distinguishes development from evidence.

### Development seeds

Development/debug seeds may be reused freely across `D-NNN` work. Reuse gives them no evidentiary status and no new reservation ceremony is required for each D-record.

A development seed must still be checked against every existing formal calibration/acceptance/confirmatory reservation. A seed already reserved for an EXP experiment may not be executed merely because the new run is labelled development.

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

## Run manifest

Every confirmatory run should record enough information to reconstruct what was executed, including:

- experiment identifier and revision;
- Git commit SHA;
- configuration values;
- master/environment seed;
- comparator condition;
- software/runtime versions;
- start time and relevant platform information;
- output schema version if one exists.

Development records remain lighter, but should retain the exact executed SHA and the development seeds used so the work can be reconstructed later.

## Privileged evaluator state

The simulator may hold hidden ground truth needed for physics, resource generation, metrics, or debugging. That state must remain separate from the observation passed to the controller and from any plastic update.

Evaluator access to hidden position, resource coordinates, ground-truth fields, or diagnostic counters does not imply organism access.

## Validation claims and review evidence

A validation claim attached to an exact Git SHA requires that exact committed tree, from a clean checkout, to compile and import successfully. Results produced from a dirty working tree must disclose the dirty state and patch; they must not cite the clean commit as if it contained the source that was executed. Reviewer language must distinguish “I inspected the tests” from “I executed the tests.”

## Failed and exploratory runs

Exploratory and failed runs are part of the research record. They may be excluded from a final confirmatory summary only according to rules defined before the confirmatory run, such as a genuine execution failure.

Do not delete or relabel scientifically valid negative results merely because they conflict with expectations.

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
