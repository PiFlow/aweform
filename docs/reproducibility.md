# Reproducibility and Seed Policy

Aweform's early experiments are simple enough that reproducibility should be treated as a hard requirement rather than a later improvement.

## Reproducibility target

For the same code revision, configuration, software environment, and master seed, a deterministic run should reproduce the same canonical trajectory and summary outputs on the same supported platform, subject only to explicitly documented numerical tolerances.

If a component is intentionally stochastic, its randomness must be owned by an explicit seeded random-number generator rather than implicit global state.

## Seed separation

Experiments that involve parameter calibration followed by a scientific claim must separate seeds into at least two roles:

- **development/calibration seeds** — may be inspected and used to choose parameters;
- **acceptance/confirmatory seeds** — must remain untouched until the experiment contract is frozen.

Comparator conditions must be evaluated on matched acceptance seeds.

Do not quietly replace acceptance seeds because they produce inconvenient outcomes. If the acceptance set or its generation rule changes after results are inspected, create a new experiment revision and report the earlier outcome.

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

The exact artifact format can remain minimal in V0.1, but the information must not depend on memory or manual reconstruction.

## Privileged evaluator state

The simulator may hold hidden ground truth needed for physics, resource generation, metrics, or debugging. That state must remain separate from the observation passed to the controller.

Evaluator access to hidden position, resource coordinates, or ground-truth fields does not imply agent access.

## Validation claims and review evidence

A validation claim attached to an exact Git SHA requires that exact committed
tree, from a clean checkout, to compile and import successfully. Results
produced from a dirty working tree must disclose the dirty state and patch;
they must not cite the clean commit as if it contained the source that was
executed. Reviewer language must distinguish “I inspected the tests” from “I
executed the tests.”

## Failed and exploratory runs

Exploratory and failed runs are part of the research record. They may be excluded from the final confirmatory summary only according to rules defined before the confirmatory run, such as a genuine execution failure.

Do not delete or relabel scientifically valid negative results merely because they conflict with expectations.

## Versioning experiment changes

A change to any of the following after confirmatory results are viewed should normally create a new experiment revision:

- environment dynamics;
- observation or action contract;
- energy model or viability thresholds;
- comparator-controller logic;
- interoception ablation method;
- primary outcome definition;
- acceptance seed set;
- interpretation/pass criteria.

Implementation bug fixes may preserve an experiment revision only when the previous results are explicitly invalidated and rerun from scratch.
