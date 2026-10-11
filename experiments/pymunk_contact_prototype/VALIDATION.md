# Frozen software and experiment commands

The protocol, source, cases and tests are frozen together in the result-free
commit. Tests and software validation do **not** run fixed-command measurements
or the single lifetime. Do not invoke the experiment commands as routine tests.

## Premeasurement failure and bounded repair

The initial result-free candidate `ba27168a8f2282ee5fe39556b47916c16b6c33ef`
failed during invalid-action preflight: `parse_action(True)` called `len(True)`
and raised `TypeError` before `run_suite`, any `Space.step`, or output creation.
No diagnostic result or organism lifetime ran. The original traceback was not
retained; this receipt records only the verified failure summary. The narrow
repair converts unsized scalar inputs to the contract's `ValueError` and adds
scalar/bool rejection coverage, including a check that preflight leaves physics
step counters unchanged. It does not alter valid action handling or any frozen
physics, actuator, corpus, threshold, controller, or lifetime contract. This
candidate must be committed as a new result-free freeze before measurements.

The authorized base advanced from `8188cbb2224906ccb01824f4fb75c85ac55b726e`
to `fd03776869a984eab90137fd3a0c753992605562` before this freeze. The intervening
main commit merges PR #228 and changes only
`docs/research-notes/d060-incomplete-substrate-retrospective.md`; the branch was
rebased onto that exact main, and the frozen base guard/provenance now name it.

## Optional runtime

```sh
uv sync --frozen --python 3.14.7 --group dev --group pymunk-probe
export PYMUNK_WHEEL_PATH=/private/tmp/pymunk220-wheelhouse/pymunk-7.2.0-cp314-cp314-macosx_11_0_arm64.whl
```

The runner verifies Python/Pymunk and the wheel SHA against the frozen #220
native arm64 artifact, and checks `origin/main`, branch, clean tree and exact
experiment-only diff before measurement.

## Software-only validation

```sh
uv run --frozen --group pymunk-probe pytest -q experiments/pymunk_contact_prototype/test_contact_prototype.py
uv run --frozen --group pymunk-probe ruff check experiments/pymunk_contact_prototype
MYPYPATH=src uv run --frozen --group dev --group pymunk-probe mypy --strict experiments/pymunk_contact_prototype
uv run --frozen --group pymunk-probe python -m compileall -q experiments/pymunk_contact_prototype
```

The tests inspect the fixed-case inventory, validation/geometry helpers, reset
construction, initial 8-channel wrapper boundary and one-shot gate structure.
They do not call `Space.step`, `run_suite`, `measure`, `run_once`, or
`run_reference_once`.

## Explicit measured commands — not part of routine validation

Only from the exact clean result-free freeze SHA, after independent resource
availability review, invoke the fixed diagnostics **once**:

```sh
uv run --frozen --group pymunk-probe python -m experiments.pymunk_contact_prototype.run_diagnostics \
  --measure --output experiments/pymunk_contact_prototype/results
```

The command executes the frozen 10/20-substep corpus and one fresh same-source
replay serially. It stores every outcome, including failures; it exits nonzero
on an essential B failure. Never rerun to rescue or replace a result.

Only if the committed B result says `essential_B_pass: true`, and after another
resource check, invoke the one-shot Pymunk lifetime plus its matched unchanged
D-058 reference:

```sh
uv run --frozen --group dev --group pymunk-probe python -m experiments.pymunk_contact_prototype.run_lifetime_once \
  --run-organism-once \
  --results experiments/pymunk_contact_prototype/results \
  --output experiments/pymunk_contact_prototype/lifetime
```

The marker refuses a second lifetime attempt, including after an incomplete
first attempt. A B failure means do not invoke this command. Software tests,
CI and no-mistakes validation never invoke either measured command.
